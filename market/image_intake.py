"""Bounded local image intake. Lock order is coordinator, then public D1 APIs.

D2 decode, thread joins and caller body/socket I/O never run under this lock.
Optional native mode composes the existing D1 lifecycle and bounded session APIs.
"""

from dataclasses import asdict, replace
import hashlib
import hmac
import re
import secrets
import threading
from uuid import UUID

from .image_admission import (
    AdmissionController, AdmissionError, AdmissionSnapshot, CompletionReceipt, DispatchPermit,
    Receipt, StartReceipt, MAX_NS, RETENTION_NS,
)
from .image_decode import DecodeError, DecodeRequest, DecodedImage, ImageDecoder
from .price_service import Clock, ClockSample
from .native_protocol import NativeProfile, owned, scope


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
_TERMINAL = ("processed", "rejected", "expired")


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


@owned
class ImageIntake:
    def __init__(self, admission: AdmissionController, decoder: ImageDecoder, clock: Clock,
                 *, native_session=None):
        config = None if native_session is None else native_session.config
        self.profile = NativeProfile() if config is None else NativeProfile(
            getattr(config, "profile", "bounded-image20s/v1"),
            getattr(config, "duration_minutes", 480), getattr(config, "max_observations", 86400),
        )
        self._observation_limit = self.profile.max_observations if self.profile.live else 40
        self._lock = threading.Lock()
        self._admission = admission
        self._decoder = decoder
        self._clock = clock
        self._native = native_session
        self._receipts = {}
        self._measured_images = {}
        self._live = set()
        self._native_fault = None
        self._native_ended = False
        self._notice_seq = 0
        self._receipt_ticket = 0
        self._dispatch_wait = None
        self._receipts_finished = False
        self._emergency_used = False
        self._native_stop_task = None
        self._native_close_deadline = None
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
        self._native_read_bucket = _Bucket(120, 500_000_000)
        self._guest = _mint("ig.")
        snapshot = admission.snapshot()
        _require(snapshot.fault is None and snapshot.reservation is None
                 and snapshot.pending is None and snapshot.active is None
                 and snapshot.terminal_count == 0 and snapshot.reserved_receipt_slots == 0)
        self._incarnation = snapshot.incarnation
        self._native_admission = snapshot
        if native_session is not None:
            from .native_protocol import ReceiptEvidence
            from .native_session import NativeSnapshot
            self._receipt_validator = ReceiptEvidence()
            with scope(self.profile):
                native = NativeSnapshot(native_session.snapshot().to_dict())
            _require(native.incarnation == self._incarnation)
            self._worker_session = native.worker_session
            self._protocol_sha256 = native_session.config.protocol_sha256
        self._sync()

    @property
    def native_enabled(self):
        return self._native is not None

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
        if self._native is not None:
            native = self._native.snapshot()
            if native.state != "running" or native.fault is not None:
                raise IntakeError("stopping")

    def _fence(self, fault, snapshot=None):
        if fault == "clock":
            self._clock_fault = True
        if self._fault is None:
            self._fault = fault
            self._generation += 1
        self._pixels = None
        self._dispatch_wait = None
        if self._cancel is not None:
            self._cancel.set()
        if self._native is None and not self._stopping and (snapshot is None or snapshot.fault != "clock"):
            self._admission.stop(reason="worker_failed")

    def _receipt_valid(self, receipt):
        if self._native is not None:
            from .native_protocol import validate_receipt
            try:
                validate_receipt(asdict(receipt))
                return type(receipt) is Receipt and receipt.incarnation == self._incarnation
            except (ValueError, TypeError):
                return False
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
                for bucket in (self._upload_bucket, self._operator_bucket, self._status_bucket,
                               self._native_read_bucket):
                    bucket.refill(now)

    def _sync(self):
        """Reconcile <=512 retained capabilities using D1's public status API."""
        if self._native is not None:
            return self._sync_native()
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

    def _capture(self, receipt, cause, entries):
        """Detached revision watermark, never a replacement for D1 state."""
        from .native_protocol import ProtocolError
        if not self._receipt_valid(receipt):
            raise ProtocolError("journal_gap")
        previous = self._receipts.get(receipt.id)
        if previous == receipt:
            return
        if (previous is None and (receipt.revision != 1 or cause["operation"] != "admit"
                                  or cause["target_id"] != receipt.id)
                or previous is not None and (previous.status in _TERMINAL
                                            or receipt.revision != previous.revision + 1)):
            raise ProtocolError("journal_gap")
        if len(entries) >= 3 or previous is None and len(self._receipts) >= 512:
            raise ProtocolError("journal_gap")
        self._receipt_validator.accept(asdict(receipt))
        self._receipts[receipt.id] = replace(receipt)
        if receipt.status in _TERMINAL:
            self._live.discard(receipt.id)
        else:
            self._live.add(receipt.id)
        entries.append({"receipt": replace(receipt), "cause": dict(cause)})

    def _reconcile(self, result, operation, target_id, notice_seq, entries):
        """At most three atomic snapshots and two disappeared-ID reads."""
        from .native_protocol import ProtocolError
        def cause(name, target, read_pass):
            return dict(operation=name, target_id=target, notice_seq=notice_seq, read_pass=read_pass)
        if type(result) is Receipt:
            self._capture(result, cause(operation, target_id, 0), entries)
        elif type(result) is AdmissionSnapshot:
            for item in (result.pending, result.active):
                if item is not None:
                    self._capture(item, cause(operation, item.id, 0), entries)
        reads = set()
        for read_pass in range(3):
            snapshot = self._admission.snapshot()
            if snapshot.incarnation != self._incarnation:
                raise ProtocolError("journal_gap")
            if (snapshot.pending is not None and snapshot.pending.status not in ("accepted", "queued")
                    or snapshot.active is not None and snapshot.active.status != "processing"
                    or snapshot.pending is not None and snapshot.active is not None
                    and snapshot.pending.id == snapshot.active.id):
                raise ProtocolError("journal_gap")
            live = {item.id for item in (snapshot.pending, snapshot.active) if item is not None}
            for item in (snapshot.pending, snapshot.active):
                if item is not None:
                    # D1.dispatch returns a permit, not its changed receipt.
                    # Bind that first public snapshot to the actual operation
                    # so the session can verify the durable dispatch cause.
                    source = operation if read_pass == 0 and type(result) is DispatchPermit and item.id == target_id else "snapshot"
                    self._capture(item, cause(source, item.id, read_pass), entries)
            disappeared = self._live - live
            if not disappeared:
                return snapshot
            for item_id in sorted(disappeared):
                if item_id in reads or len(reads) >= 2:
                    raise ProtocolError("journal_gap")
                reads.add(item_id)
                try:
                    receipt = self._admission.status(id=item_id)
                except AdmissionError:
                    raise ProtocolError("journal_gap") from None
                if receipt.status not in _TERMINAL:
                    raise ProtocolError("journal_gap")
                self._capture(receipt, cause("status", item_id, read_pass), entries)
        raise ProtocolError("journal_gap")

    def _request_native_stop(self, reason, emergency_entries=None):
        # The session may signal its transport. Keep that work outside this lock.
        if self._native_stop_task is None:
            def stop():
                try:
                    self._native.begin_stop(reason)
                    if emergency_entries is not None:
                        self._native.publish_receipts(None, emergency_entries)
                        self._native.finish_receipts()
                except Exception:
                    # The session retains failure/ownership; no successful seal
                    # is inferred from a requested stop or attempted handoff.
                    pass
            self._native_stop_task = threading.Thread(
                target=stop, daemon=True, name="market-native-stop",
            )
            self._native_stop_task.start()

    def _emergency_stop(self, fault):
        self._native_fault = self._native_fault or fault
        self._fence("clock" if fault == "clock" else "native_worker")
        emergency_entries = None
        if not self._emergency_used and not self._receipts_finished:
            self._emergency_used = True
            entries = []
            try:
                result = self._admission.stop(reason="worker_failed")
                self._native_admission = self._reconcile(result, "stop", None, None, entries)
                if len(entries) > 2 or any(entry["receipt"].status not in _TERMINAL for entry in entries):
                    raise ValueError("journal_gap")
                emergency_entries = tuple(entries)
            except Exception:
                # Preserve actual earlier receipts and incomplete evidence.
                pass
            self._receipts_finished = True
        self._request_native_stop("session_fault", emergency_entries)

    def _d1(self, operation, *, notice_seq=None, **kwargs):
        if self._native is None:
            return getattr(self._admission, operation)(**kwargs)
        if self._receipts_finished:
            # Post-stop diagnostics use the retained authoritative watermark.
            if operation == "status":
                if kwargs["id"] not in self._receipts:
                    raise AdmissionError("not_found")
                return replace(self._receipts[kwargs["id"]])
            if operation in ("maintain", "snapshot", "stop"):
                return self._native_admission
            raise AdmissionError("stopped")
        ticket = self._native.reserve_receipts()
        if ticket is None:
            self._emergency_stop(self._native.receipt_progress().fault or self._native_fault or "storage")
            raise AdmissionError("stopped")
        entries, result, error = [], None, None
        target = kwargs.get("id")
        if "receipt" in kwargs:
            target = kwargs["receipt"].id
        try:
            try:
                result = getattr(self._admission, operation)(**kwargs)
            except AdmissionError as caught:
                error = caught
            try:
                self._native_admission = self._reconcile(result, operation, target, notice_seq, entries)
            except Exception:
                # Preserve direct returns and other valid captures obtained
                # before a gap. Only this still-unsubmitted normal ticket is used.
                self._native.publish_receipts(ticket, tuple(entries))
                raise
            self._native.publish_receipts(ticket, tuple(entries))
            if entries:
                self._receipt_ticket = ticket.ticket
        except Exception:
            self._emergency_stop("journal_gap")
            raise IntakeError("intake_fault") from None
        if error is not None:
            raise error
        return result

    def _sync_native(self):
        from .native_session import NativeNotice, NativeSnapshot
        native = NativeSnapshot(self._native.snapshot().to_dict())
        if (native.incarnation != self._incarnation or native.worker_session != self._worker_session):
            self._emergency_stop("protocol")
        try:
            notices = self._native.poll()
            if type(notices) is not tuple or len(notices) > 8:
                raise ValueError("protocol")
            for raw in notices:
                notice = NativeNotice(raw.to_dict())
                if (notice.notice_seq != self._notice_seq or notice.incarnation != self._incarnation
                        or notice.worker_session != self._worker_session
                        or notice.protocol_sha256 != self._protocol_sha256):
                    raise ValueError("protocol")
                self._notice_seq += 1
                payload = notice.payload.to_dict()
                if notice.type == "start":
                    self._d1("started", receipt=StartReceipt(**payload), notice_seq=notice.notice_seq)
                elif notice.type == "complete":
                    if self._measured_images.get(payload["id"], (0, 0))[0] != 8:
                        raise ValueError("protocol")
                    payload["observation_indices"] = tuple(payload["observation_indices"])
                    self._d1("complete", receipt=CompletionReceipt(**payload), notice_seq=notice.notice_seq)
                elif notice.type == "observation" and payload["input_kind"] == "image":
                    item = self._receipts.get(payload["image_id"])
                    if (item is None or item.status != "processing" or item.worker_session != self._worker_session
                            or item.frame_sha256 != payload["frame_sha256"]):
                        raise ValueError("protocol")
                    count = self._measured_images.get(item.id, (0, 0))[0]
                    if count >= 8 or payload["observation_index"] != item.first_observation_index + count:
                        raise ValueError("protocol")
                    self._measured_images[item.id] = (count + 1, payload["observation_index"] + 1)
                elif notice.type == "fault":
                    self._native_fault = self._native_fault or payload["code"]
                    self._fence("clock" if payload["code"] == "clock" else "native_worker")
                elif notice.type == "ended":
                    self._native_ended = payload["reason"] == "model_limit" or self.profile.live and payload["reason"] == "wall_limit"
        except (ValueError, TypeError, AdmissionError, IntakeError):
            self._emergency_stop("protocol")
        # Drain already validated observation notices before a terminal stop
        # freezes per-image measurement watermarks. Each D1 mutation above still
        # samples its own authoritative clock and retains late-receipt precedence.
        try:
            self._d1("maintain")
        except AdmissionError:
            pass
        snapshot = self._native_admission
        self._sample_clock(snapshot)
        if snapshot.fault is not None and snapshot.fault != "session_ended":
            self._native_fault = self._native_fault or snapshot.fault
            self._fence("clock" if snapshot.fault == "clock" else "native_worker", snapshot)
        if native.fault is not None:
            self._native_fault = self._native_fault or native.fault
            self._fence("clock" if native.fault == "clock" else "native_worker", snapshot)
        if self._clock_fault:
            self._native_fault = self._native_fault or "clock"
        if self._fault is not None or native.state in ("ended", "faulted", "stopping", "closed"):
            if not self._receipts_finished:
                reason = "worker_outcome_unknown" if self._native_fault in ("worker_outcome_unknown", "deadline") else "worker_failed" if self._fault else "session_ended"
                try:
                    self._d1("stop", reason=reason)
                    self._native.finish_receipts()
                    self._receipts_finished = True
                except (AdmissionError, IntakeError):
                    self._emergency_stop(self._native_fault or "worker_failed")
            if self._fault:
                self._request_native_stop("session_fault")
        snapshot = self._native_admission
        if self._pixels is not None:
            pending = snapshot.pending
            if (pending is None or self._pixels[:2] != (pending.id, pending.frame_sha256)
                    or pending.detail not in ("awaiting_approval", "ready")):
                self._pixels = None
        if not self._clock_fault:
            for item_id, receipt in tuple(self._receipts.items()):
                if receipt.terminal_ns is not None and self._last_ns - receipt.terminal_ns >= RETENTION_NS:
                    del self._receipts[item_id]
                    self._capabilities.pop(item_id, None)
                    self._measured_images.pop(item_id, None)
        return snapshot

    def _native_budget(self):
        native = self._native.snapshot()
        if native.state != "running" or native.fault is not None or native.free_observations < 8:
            raise IntakeError("full")

    def _native_phase(self, native):
        if self._stopping:
            return "stopping"
        if self._fault is not None or native.fault is not None:
            return "faulted"
        if native.state == "closed":
            return "ended" if self._native_ended else "stopping"
        return "starting" if native.state == "prepared" else native.state

    def _native_intake_state(self, snapshot):
        native = self._native.snapshot()
        phase = self._native_phase(native)
        ready = phase == "running"
        return {
            "schema": "market-image-intake/v3" if self.profile.live else "market-image-intake/v2", "incarnation": self._incarnation,
            "mode": "live-pilot" if self.profile.live else "bounded-native-test", "worker_connected": ready,
            "health": "ready" if ready else "faulted" if phase == "faulted" else "stopping",
            "fault": self._fault, "receiving": ready and snapshot.reservation is not None,
            "decode_busy": self._task is not None and self._task.is_alive(),
            "pending": self._wire_status(snapshot.pending) if ready and snapshot.pending is not None else None,
            "active": self._wire_status(snapshot.active) if ready and snapshot.active is not None else None,
            "receipt_count": len(self._capabilities), "native_state": phase,
        }

    def native_state(self):
        with self._lock:
            self._open()
            if self._native is None:
                raise IntakeError("not_found")
            self._sync()
            native = self._native.snapshot()
            latest = native.latest
            uncertain = self._clock_fault or native.fault == "clock"
            if latest is not None and not uncertain and self._last_ns < latest.wall_completion_ns:
                self._emergency_stop("clock")
                uncertain = True
            fault = self._native_fault or native.fault
            if self._fault is not None and fault is None:
                fault = "worker_failed"
            value = {
                "schema": "market-native-state/v2" if self.profile.live else "market-native-state/v1", "incarnation": self._incarnation,
                "worker_session": self._worker_session, "mode": "live-pilot" if self.profile.live else "bounded-native-test",
                "state": self._native_phase(native), "fault": fault,
                "model_ms": 500 * native.completed_observations, "model_limit_ms": 500 * self._observation_limit,
                "observations_completed": native.completed_observations,
                "measurement_age_ms": None if latest is None or uncertain else (self._last_ns - latest.wall_completion_ns) // 1_000_000,
                "time_uncertain": uncertain,
                "input_kind": None if latest is None else latest.input_kind,
                "image_id": None if latest is None else latest.image_id,
                "frame_sha256": None if latest is None else latest.frame_sha256,
                "group_spikes": None if latest is None else latest.group_spikes.to_dict(),
                "group_rates_hz": None if latest is None else latest.group_rates_hz.to_dict(),
            }
            if self.profile.live:
                value["profile"] = "live-pilot/v1"
            return value

    def charge_native_read(self):
        with self._lock:
            self._open()
            if self._native is None:
                raise IntakeError("not_found")
            self._sync()
            self._native_read_bucket.charge(self._now())

    def _drive_native(self):
        if self._stopping or self._fault is not None or self._receipts_finished:
            return
        native = self._native.snapshot()
        if native.state != "running" or native.fault is not None or native.boundary is None:
            return
        if self._native.receipt_progress().durable_ticket < self._receipt_ticket:
            return
        boundary = native.boundary
        if self._dispatch_wait is not None:
            bound_id, permit, rgb = self._dispatch_wait
            if bound_id != boundary.id:
                self._emergency_stop("protocol")
                return
            self._dispatch_wait = None
        else:
            permit = rgb = None
            pending = self._native_admission.pending
            if (boundary.active_dispatch_id is None and boundary.id <= self._observation_limit - 8
                    and pending is not None and pending.detail == "ready"):
                if self._pixels is None or self._pixels[:2] != (pending.id, pending.frame_sha256):
                    self._emergency_stop("protocol")
                    return
                rgb = self._pixels[2]
                try:
                    permit = self._d1("dispatch", id=pending.id, worker_session=self._worker_session)
                except (AdmissionError, IntakeError):
                    return
                self._pixels = None
                self._dispatch_wait = (boundary.id, permit, rgb)
                # A dispatch may have expired or faulted during bounded capture.
                if self._receipts[permit.id].detail != "dispatching":
                    self._dispatch_wait = None
                    return
                if self._native.receipt_progress().durable_ticket < self._receipt_ticket:
                    return
                self._dispatch_wait = None
        if self._native_admission.fault is not None:
            return
        try:
            self._native.advance(boundary.id, permit, rgb)
        except Exception:
            self._emergency_stop("worker_failed")

    def _admission_error(self, error):
        if error.code == "clock":
            self._fence("clock", self._d1("snapshot"))
            raise IntakeError("intake_fault") from None
        if error.code == "stopped":
            self._fence("native_worker" if self._native is not None else "decoder", self._d1("snapshot"))
            raise IntakeError("stopping" if self._stopping else "intake_fault") from None
        raise IntakeError(error.code if error.code in _ERRORS else "intake_fault") from None

    def _read_status(self, item_id):
        if self._native is not None:
            receipt = self._receipts.get(item_id)
            if receipt is None:
                raise IntakeError("not_found")
            return replace(receipt)
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
        value = {
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
        if self._native is not None:
            count, revision = self._measured_images.get(receipt.id, (0, 0))
            value.update(schema="market-image-status-wire/v3" if self.profile.live else "market-image-status-wire/v2", worker_session=receipt.worker_session,
                         first_observation_index=receipt.first_observation_index,
                         completed_observations=count, observation_revision=revision)
            value["preview_available"] = (value["preview_available"] and receipt.detail in ("awaiting_approval", "ready"))
            if receipt.status == "processing" and not uncertain:
                value["remaining_handoff_ms"] = 0
        return value

    def _status(self, item_id):
        return self._wire_status(self._read_status(item_id))

    def _abandon(self, item_id):
        try:
            self._d1("cancel_reservation", id=item_id)
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
            if self._native is not None:
                self._native_budget()
            try:
                return self._d1("reserve")
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
                    if self._native is not None:
                        self._native_budget()
                    receipt = self._d1("admit", id=id, source_sha256=hashlib.sha256(payload).hexdigest(),
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
            return {"schema": "market-image-acceptance/v3" if self.profile.live else "market-image-acceptance/v2" if self._native is not None else "market-image-acceptance/v1",
                    "status_capability": capability, "image": self._status(id)}

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
                            self._d1("decode_failed", id=identity[1])
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
                receipt = self._d1("decoded", id=identity[1], frame_sha256=result.frame_sha256,
                                                  preprocessing_version=result.preprocessing_version)
                if self._native is not None:
                    receipt = self._receipts[receipt.id]
                if receipt.detail == "awaiting_approval" and receipt.status == "accepted":
                    self._pixels = (receipt.id, result.frame_sha256, result.rgb)
            except DecodeError:
                self._fence("decoder", snapshot)
            except AdmissionError as error:
                if error.code not in ("not_found", "invalid_transition"):
                    self._fence("clock" if error.code == "clock" else "decoder", self._d1("snapshot"))

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
            if self._native is not None:
                return self._native_intake_state(snapshot)
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
                self._d1("moderate", id=id, action_id=action_id, approved=approved)
            except AdmissionError as error:
                self._sync()
                self._admission_error(error)
            self._sync()
            return self._status(id)

    def maintain(self):
        with self._lock:
            self._open()
            self._sync()
            if self._native is not None:
                self._drive_native()

    def begin_stop(self):
        with self._lock:
            if self._closed or self._stopping:
                return
            if self._native is not None:
                try:
                    self._sync_native()
                except IntakeError:
                    # A bounded reconciliation failure has already fenced the
                    # session and kept evidence incomplete; continue owned stop.
                    pass
            self._stopping = True
            if self._native is not None and self._native_close_deadline is None:
                import time
                self._native_close_deadline = time.perf_counter() + 25
            self._generation += 1
            self._pixels = None
            self._dispatch_wait = None
            if self._cancel is not None:
                self._cancel.set()
            if self._native is None:
                self._admission.stop(reason="session_ended")
            else:
                if not self._receipts_finished:
                    try:
                        self._d1("stop", reason="session_ended")
                        self._native.finish_receipts()
                        self._receipts_finished = True
                    except (AdmissionError, IntakeError):
                        self._emergency_stop("worker_failed")
                self._request_native_stop("operator")

    def finish_close(self):
        self.begin_stop()
        if self._native is not None:
            self._finish_native_close()
            return
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

    def _finish_native_close(self):
        import time
        with self._lock:
            if self._closed:
                return
            task, stop_task = self._task, self._native_stop_task
            deadline = self._native_close_deadline
        try:
            for owned_task in (task, stop_task):
                if owned_task is not None:
                    owned_task.join(max(0, deadline - time.perf_counter()))
                    if owned_task.is_alive():
                        raise IntakeError("cleanup_failed")
            if time.perf_counter() >= deadline:
                raise IntakeError("cleanup_failed")
            # Decoder ownership close and native drain/join/fsync never hold the
            # coordinator lock; diagnostics remain bounded during cleanup.
            self._decoder.close()
            self._native.finish_close()
            if time.perf_counter() >= deadline:
                raise IntakeError("cleanup_failed")
        except Exception:
            with self._lock:
                self._fault = self._fault or "shutdown"
            raise IntakeError("cleanup_failed") from None
        with self._lock:
            self._closed = True
