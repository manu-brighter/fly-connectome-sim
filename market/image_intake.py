"""Bounded local image intake. Lock order is coordinator, then public D1 APIs.

D2 decode, thread joins and caller body/socket I/O never run under this lock.
Approval only queues metadata; this collaborator has no neural worker authority.
"""

from dataclasses import replace
import hashlib
import hmac
import re
import secrets
import threading
from uuid import UUID

from .image_admission import AdmissionController, AdmissionError, Receipt, MAX_NS, RETENTION_NS
from .image_decode import DecodeError, DecodeRequest, DecodedImage, ImageDecoder
from .price_service import Clock, ClockSample


_ERRORS = (
    "unauthorized", "not_found", "full", "busy", "invalid_transition",
    "idempotency_conflict", "wrong_incarnation", "rate_limited", "invalid_request",
    "capacity", "intake_fault", "stopping", "closed", "cleanup_failed",
)
_GUEST = re.compile(r"ig\.[A-Za-z0-9_-]{43}\Z", re.ASCII)
_STATUS = re.compile(r"is\.[A-Za-z0-9_-]{43}\Z", re.ASCII)
_SUFFIX = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_REJECTIONS = (
    "malformed_image", "unsupported_format", "geometry", "mode", "multiple_frames",
    "source_mismatch", "memory_limit", "child_failed", "monitor_stalled",
)
_TERMINAL = ("rejected", "expired")


class IntakeError(Exception):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _ERRORS else "invalid_request"
        super().__init__(self.code)


def _uuid(value):
    if type(value) is not str or len(value) != 36:
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _require(condition):
    if not condition:
        raise IntakeError("invalid_request")


def _mint(prefix):
    try:
        suffix = secrets.token_urlsafe(32)
        if type(suffix) is not str or _SUFFIX.fullmatch(suffix) is None:
            raise ValueError("invalid capability")
        return prefix + suffix
    except Exception:
        raise IntakeError("capacity") from None


class _Bucket:
    # Integer credit units avoid rounding and arbitrary clock-size floats.
    def __init__(self, capacity, interval):
        self.capacity = capacity * interval
        self.interval = interval
        self.balance = self.capacity
        self.last_ns = None

    def refill(self, now):
        if now is not None:
            if self.last_ns is not None:
                self.balance = min(self.capacity, self.balance + now - self.last_ns)
            self.last_ns = now

    def charge(self, now):
        self.refill(now)
        if self.balance < self.interval:
            raise IntakeError("rate_limited")
        self.balance -= self.interval


class ImageIntake:
    def __init__(self, admission: AdmissionController, decoder: ImageDecoder, clock: Clock):
        self._lock = threading.Lock()
        self._admission = admission
        self._decoder = decoder
        self._clock = clock
        self._last_ns = None
        self._clock_fault = False
        self._fault = None
        self._stopping = self._closed = False
        self._generation = 0
        self._task = None
        self._cancel = None
        self._pixels = None
        self._capabilities = {}
        self._upload_bucket = _Bucket(1, 10_000_000_000)
        self._operator_bucket = _Bucket(120, 500_000_000)
        self._status_bucket = _Bucket(120, 500_000_000)
        self._guest = _mint("ig.")
        snapshot = admission.snapshot()
        _require(snapshot.fault is None and snapshot.reservation is None
                 and snapshot.pending is None and snapshot.active is None
                 and snapshot.terminal_count == 0 and snapshot.reserved_receipt_slots == 0)
        self._incarnation = snapshot.incarnation
        self._sync()

    @property
    def guest_capability(self):
        return self._guest

    def _open(self):
        if self._closed:
            raise IntakeError("closed")

    def _action(self):
        if self._stopping:
            raise IntakeError("stopping")
        if self._fault is not None:
            raise IntakeError("intake_fault")

    def _fence(self, fault, snapshot=None):
        if fault == "clock":
            self._clock_fault = True
        if self._fault is None:
            self._fault = fault
            self._generation += 1
        self._pixels = None
        if self._cancel is not None:
            self._cancel.set()
        if not self._stopping and (snapshot is None or snapshot.fault != "clock"):
            self._admission.stop(reason="worker_failed")

    def _receipt_valid(self, receipt):
        if type(receipt) is not Receipt or receipt.incarnation != self._incarnation:
            return False
        combinations = {
            ("accepted", "decoding"): False,
            ("accepted", "awaiting_approval"): True,
            ("queued", "ready"): True,
            ("expired", "ttl_expired"): True,
            ("rejected", "decode_failed"): False,
            ("rejected", "decode_timeout"): False,
            ("rejected", "moderation_rejected"): True,
            ("rejected", "moderation_timeout"): True,
        }
        if receipt.status == "rejected" and receipt.detail in ("worker_failed", "session_ended", "clock"):
            return True
        needs_hash = combinations.get((receipt.status, receipt.detail))
        return needs_hash is not None and (receipt.frame_sha256 is not None) == needs_hash

    def _sample_clock(self, snapshot):
        if snapshot.fault == "clock":
            self._fence("clock", snapshot)
        if not self._clock_fault:
            try:
                sample = self._clock.sample()
                now = sample.monotonic_ns
                if (type(sample) is not ClockSample or type(now) is not int
                        or not 0 <= now <= MAX_NS or self._last_ns is not None and now < self._last_ns):
                    raise ValueError("invalid clock")
            except Exception:
                self._fence("clock", snapshot)
            else:
                self._last_ns = now
                for bucket in (self._upload_bucket, self._operator_bucket, self._status_bucket):
                    bucket.refill(now)

    def _sync(self):
        """Reconcile <=512 retained capabilities using D1's public status API."""
        snapshot = self._admission.maintain()
        self._sample_clock(snapshot)
        for item_id in tuple(self._capabilities):
            try:
                receipt = self._admission.status(id=item_id)
            except AdmissionError as error:
                if error.code == "not_found":
                    del self._capabilities[item_id]
                else:
                    self._fence("decoder")
            else:
                if not self._receipt_valid(receipt):
                    self._fence("decoder")
        snapshot = self._admission.snapshot()
        if snapshot.fault == "clock":
            self._fence("clock", snapshot)
        elif snapshot.fault is not None and not self._stopping and self._fault is None:
            self._fence("decoder", snapshot)
        if snapshot.incarnation != self._incarnation or snapshot.active is not None:
            self._fence("decoder", snapshot)
        if self._pixels is not None:
            item_id, frame_hash, _ = self._pixels
            pending = snapshot.pending
            if (pending is None or pending.id != item_id or pending.frame_sha256 != frame_hash
                    or pending.detail not in ("awaiting_approval", "ready")):
                self._pixels = None
        return snapshot

    def _now(self):
        return None if self._clock_fault else self._last_ns

    def _admission_error(self, error):
        if error.code == "clock":
            self._fence("clock", self._admission.snapshot())
            raise IntakeError("intake_fault") from None
        if error.code == "stopped":
            self._fence("decoder", self._admission.snapshot())
            raise IntakeError("stopping" if self._stopping else "intake_fault") from None
        raise IntakeError(error.code if error.code in _ERRORS else "intake_fault") from None

    def _read_status(self, item_id):
        # A public D1 read/snapshot may advance a phase or prune retention.
        # Observe those real effects before rendering/auth accounting. There are
        # at most two automatic transitions: live -> terminal -> pruned. Three
        # target reads suffice; an inconsistent collaborator fails closed rather
        # than retrying indefinitely or manufacturing a terminal state.
        for _ in range(3):
            try:
                receipt = self._admission.status(id=item_id)
            except AdmissionError as error:
                if error.code == "not_found":
                    self._capabilities.pop(item_id, None)
                    if self._pixels is not None and self._pixels[0] == item_id:
                        self._pixels = None
                self._admission_error(error)
            snapshot = self._admission.snapshot()
            self._sample_clock(snapshot)
            if not self._receipt_valid(receipt):
                break
            terminal = receipt.status in _TERMINAL
            if terminal:
                if self._pixels is not None and self._pixels[0] == item_id:
                    self._pixels = None
                if (snapshot.fault is None and not self._clock_fault
                        and self._last_ns - receipt.terminal_ns >= RETENTION_NS):
                    continue
            else:
                deadline = {"decoding": receipt.decode_deadline_ns,
                            "awaiting_approval": receipt.moderation_deadline_ns,
                            "ready": receipt.deadline_ns}[receipt.detail]
                if (self._fault is not None or self._stopping or snapshot.pending is None
                        or self._last_ns >= deadline):
                    continue
            if receipt.time_uncertain:
                self._fence("clock", snapshot)
            return receipt
        self._fence("decoder")
        raise IntakeError("intake_fault")

    def _wire_status(self, receipt):
        uncertain = self._clock_fault or receipt.time_uncertain
        terminal = receipt.status in _TERMINAL
        def remaining(deadline):
            return None if uncertain else 0 if terminal else max(0, (deadline - self._last_ns + 999_999) // 1_000_000)
        return {
            "schema": "market-image-status-wire/v1", "incarnation": receipt.incarnation,
            "id": receipt.id, "revision": receipt.revision, "status": receipt.status,
            "detail": receipt.detail, "frame_sha256": receipt.frame_sha256,
            "accepted_age_ms": None if uncertain else max(0, (self._last_ns - receipt.accepted_ns) // 1_000_000),
            "remaining_decode_ms": remaining(receipt.decode_deadline_ns),
            "remaining_moderation_ms": remaining(receipt.moderation_deadline_ns),
            "remaining_handoff_ms": remaining(receipt.deadline_ns),
            "time_uncertain": uncertain,
            "preview_available": self._pixels is not None and self._pixels[:2] == (receipt.id, receipt.frame_sha256),
        }

    def _status(self, item_id):
        return self._wire_status(self._read_status(item_id))

    def _abandon(self, item_id):
        try:
            self._admission.cancel_reservation(id=item_id)
        except AdmissionError as error:
            if error.code not in ("not_found", "clock", "stopped"):
                self._admission_error(error)

    def reserve_upload(self, guest_capability):
        with self._lock:
            self._open()
            if (type(guest_capability) is not str or _GUEST.fullmatch(guest_capability) is None
                    or not hmac.compare_digest(guest_capability, self._guest)):
                raise IntakeError("unauthorized")
            self._sync()
            self._action()
            self._upload_bucket.charge(self._now())
            if self._task is not None and self._task.is_alive():
                raise IntakeError("busy")
            try:
                return self._admission.reserve()
            except AdmissionError as error:
                self._admission_error(error)

    def abandon_upload(self, id):
        with self._lock:
            self._open()
            _require(_uuid(id))
            self._abandon(id)

    def accept_upload(self, id, media_type, payload):
        with self._lock:
            self._open()
            _require(_uuid(id))
            try:
                _require(type(media_type) is str and media_type in ("image/png", "image/jpeg")
                         and type(payload) is bytes and 1 <= len(payload) <= 2_097_152)
                snapshot = self._sync()
                self._action()
                if snapshot.reservation is None or snapshot.reservation.id != id:
                    raise IntakeError("not_found")
                if self._task is not None and self._task.is_alive():
                    raise IntakeError("busy")
                if len(self._capabilities) >= 512:
                    raise IntakeError("capacity")
                capability = None
                for _ in range(4):
                    candidate = _mint("is.")
                    if not any(hmac.compare_digest(candidate, retained) for retained in self._capabilities.values()):
                        capability = candidate
                        break
                if capability is None:
                    raise IntakeError("capacity")
                try:
                    receipt = self._admission.admit(id=id, source_sha256=hashlib.sha256(payload).hexdigest(),
                                                    encoded_bytes=len(payload))
                except AdmissionError as error:
                    self._admission_error(error)
            except IntakeError:
                self._abandon(id)
                raise
            self._capabilities[id] = capability
            request = DecodeRequest(receipt.incarnation, receipt.id, receipt.source_sha256,
                                    receipt.encoded_bytes, media_type, receipt.accepted_ns, receipt.decode_deadline_ns)
            self._cancel = threading.Event()
            identity = (receipt.incarnation, receipt.id, receipt.source_sha256)
            try:
                self._task = threading.Thread(target=self._decode, args=(request, payload, self._cancel,
                                              self._generation, identity), daemon=True, name="market-image-decode")
                self._task.start()
            except Exception:
                # A failed acknowledgement may still leave a live thread.
                # Retain that exact task until its cleanup and join complete.
                if self._task is not None and not self._task.is_alive():
                    self._task = None
                self._fence("decoder")
            self._sync()
            return {"schema": "market-image-acceptance/v1", "status_capability": capability, "image": self._status(id)}

    def _decode(self, request, payload, cancel, generation, identity):
        result = None
        failure = None
        try:
            result = self._decoder.decode(request=request, payload=payload, cancel=cancel)
        except DecodeError as error:
            failure = error.code
        except BaseException:
            failure = "child_protocol"
        finally:
            # Drop encoded bytes before callback work. Thread args disappear at exit.
            payload = None
        with self._lock:
            snapshot = self._sync()
            if generation != self._generation or self._stopping or self._closed:
                return
            pending = snapshot.pending
            current = (pending is not None and (pending.incarnation, pending.id, pending.source_sha256) == identity
                       and pending.detail == "decoding")
            if failure is not None:
                if failure == "timeout" and not current:
                    return
                if failure in _REJECTIONS:
                    if current:
                        try:
                            self._admission.decode_failed(id=identity[1])
                        except AdmissionError as error:
                            if error.code not in ("not_found", "invalid_transition"):
                                self._fence("clock" if error.code == "clock" else "decoder")
                else:
                    self._fence("ownership" if failure in ("ownership", "cleanup_failed")
                                else "clock" if failure == "clock" else "decoder", snapshot)
                return
            if not current:
                return
            try:
                if type(result) is not DecodedImage:
                    raise DecodeError("child_protocol")
                result = replace(result)
                if (result.incarnation, result.id, result.source_sha256) != identity:
                    raise DecodeError("child_protocol")
                receipt = self._admission.decoded(id=identity[1], frame_sha256=result.frame_sha256,
                                                  preprocessing_version=result.preprocessing_version)
                if receipt.detail == "awaiting_approval" and receipt.status == "accepted":
                    self._pixels = (receipt.id, result.frame_sha256, result.rgb)
            except DecodeError:
                self._fence("decoder", snapshot)
            except AdmissionError as error:
                if error.code not in ("not_found", "invalid_transition"):
                    self._fence("clock" if error.code == "clock" else "decoder", self._admission.snapshot())

    def guest_status(self, id, status_capability):
        with self._lock:
            self._open()
            def authenticated():
                return (type(id) is str and type(status_capability) is str
                        and _STATUS.fullmatch(status_capability) is not None
                        and id in self._capabilities and hmac.compare_digest(status_capability, self._capabilities[id]))
            if not authenticated():
                raise IntakeError("unauthorized")
            self._sync()
            if not authenticated():
                raise IntakeError("unauthorized")
            try:
                receipt = self._read_status(id)
            except IntakeError as error:
                if error.code == "not_found":
                    raise IntakeError("unauthorized") from None
                raise
            if not authenticated():
                raise IntakeError("unauthorized")
            self._status_bucket.charge(self._now())
            return self._wire_status(receipt)

    def charge_operator(self, diagnostic):
        with self._lock:
            self._open()
            _require(type(diagnostic) is bool)
            self._sync()
            if not diagnostic:
                self._action()
            self._operator_bucket.charge(self._now())

    def operator_status(self, id):
        with self._lock:
            self._open()
            _require(_uuid(id))
            self._sync()
            return self._status(id)

    def operator_state(self):
        with self._lock:
            self._open()
            snapshot = self._sync()
            ready = not self._stopping and self._fault is None
            pending = None
            if ready and snapshot.pending is not None:
                try:
                    pending = self._status(snapshot.pending.id)
                except IntakeError as error:
                    if error.code != "not_found":
                        raise
            if pending is not None and pending["status"] in _TERMINAL:
                pending = None
            # A later D1 status clock sample may itself fence the coordinator.
            ready = not self._stopping and self._fault is None
            return {
                "schema": "market-image-intake/v1", "incarnation": self._incarnation,
                "mode": "local-intake-only", "worker_connected": False,
                "health": "stopping" if self._stopping else "faulted" if self._fault is not None else "ready",
                "fault": self._fault, "receiving": ready and snapshot.reservation is not None,
                "decode_busy": self._task is not None and self._task.is_alive(),
                "pending": pending if ready else None, "receipt_count": len(self._capabilities),
            }

    def preview(self, id, frame_sha256):
        with self._lock:
            self._open()
            _require(_uuid(id) and type(frame_sha256) is str and _DIGEST.fullmatch(frame_sha256) is not None)
            self._sync()
            self._action()
            if self._pixels is None or self._pixels[:2] != (id, frame_sha256):
                raise IntakeError("not_found")
            return self._pixels[2]

    def moderate(self, id, incarnation, action_id, approved):
        with self._lock:
            self._open()
            _require(_uuid(id) and _uuid(incarnation))
            self._sync()
            self._action()
            if incarnation != self._incarnation:
                raise IntakeError("wrong_incarnation")
            try:
                self._admission.moderate(id=id, action_id=action_id, approved=approved)
            except AdmissionError as error:
                self._sync()
                self._admission_error(error)
            self._sync()
            return self._status(id)

    def maintain(self):
        with self._lock:
            self._open()
            self._sync()

    def begin_stop(self):
        with self._lock:
            if self._closed or self._stopping:
                return
            self._stopping = True
            self._generation += 1
            self._pixels = None
            if self._cancel is not None:
                self._cancel.set()
            self._admission.stop(reason="session_ended")

    def finish_close(self):
        self.begin_stop()
        with self._lock:
            if self._closed:
                return
            task = self._task
        # One real timeout, independent of the shared clock or caller test clock.
        if task is not None:
            task.join(25)
        with self._lock:
            if self._closed:
                return
            if task is not None and task.is_alive():
                self._fault = "shutdown"
                raise IntakeError("cleanup_failed")
            try:
                self._decoder.close()
            except BaseException:
                self._fault = "shutdown"
                raise IntakeError("cleanup_failed") from None
            self._closed = True
