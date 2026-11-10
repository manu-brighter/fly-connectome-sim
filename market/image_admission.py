"""Finite process-local image metadata admission; no decoder or worker authority."""

from dataclasses import dataclass, fields, replace
import re
import threading
from typing import Literal
from uuid import UUID, uuid4

from .price_service import Clock, ClockSample, SystemClock


MAX_NS = 2 ** 63 - 1
RESERVATION_NS = 5_000_000_000
PENDING_NS = 300_000_000_000
DECODE_NS = 10_000_000_000
MODERATION_NS = 60_000_000_000
START_RECEIPT_NS = 10_000_000_000
RETENTION_NS = 900_000_000_000
CAPACITY = 512
MAX_ENCODED_BYTES = 2_097_152
EXPOSURE_OBSERVATIONS = 8
PREPROCESSING_VERSION = "market-rgb64/v1"

Status = Literal["accepted", "queued", "processing", "processed", "rejected", "expired"]
Detail = Literal[
    "decoding", "awaiting_approval", "ready", "dispatching", "processing",
    "completed", "decode_failed", "decode_timeout", "moderation_rejected",
    "moderation_timeout", "ttl_expired", "worker_failed", "worker_outcome_unknown",
    "session_ended", "clock",
]
Fault = Literal["clock", "worker_failed", "worker_outcome_unknown", "session_ended"] | None

_STATUSES = ("accepted", "queued", "processing", "processed", "rejected", "expired")
_DETAILS = (
    "decoding", "awaiting_approval", "ready", "dispatching", "processing",
    "completed", "decode_failed", "decode_timeout", "moderation_rejected",
    "moderation_timeout", "ttl_expired", "worker_failed", "worker_outcome_unknown",
    "session_ended", "clock",
)
_STOP_REASONS = ("worker_failed", "worker_outcome_unknown", "session_ended")
_TERMINAL = ("processed", "rejected", "expired")
_ERRORS = (
    "invalid_request", "not_found", "invalid_transition", "idempotency_conflict",
    "wrong_incarnation", "wrong_worker", "wrong_dispatch", "wrong_frame", "full",
    "capacity", "clock", "stopped",
)
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_ACTION = re.compile(r"[A-Za-z0-9_-]{1,64}\Z", re.ASCII)


class AdmissionError(Exception):
    def __init__(self, code: str):
        self.code = code if type(code) is str and code in _ERRORS else "invalid_request"
        super().__init__(self.code)


def _require(condition):
    if not condition:
        raise AdmissionError("invalid_request")


def _integer(value, low=0, high=MAX_NS):
    return type(value) is int and low <= value <= high


def _uuid(value):
    if type(value) is not str or len(value) != 36:
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


class _Metadata:
    def __post_init__(self):
        _validate_metadata(self, type(self))


@dataclass(frozen=True)
class Reservation(_Metadata):
    id: str
    incarnation: str
    reserved_ns: int
    expires_ns: int


@dataclass(frozen=True)
class Receipt(_Metadata):
    id: str
    incarnation: str
    source_sha256: str
    encoded_bytes: int
    accepted_ns: int
    deadline_ns: int
    decode_deadline_ns: int
    moderation_deadline_ns: int
    status: Status
    detail: Detail
    frame_sha256: str | None
    preprocessing_version: str | None
    worker_session: str | None
    dispatch_id: str | None
    dispatched_ns: int | None
    started_ns: int | None
    first_observation_index: int | None
    completed_ns: int | None
    terminal_ns: int | None
    revision: int
    time_uncertain: bool


@dataclass(frozen=True)
class DispatchPermit(_Metadata):
    id: str
    incarnation: str
    dispatch_id: str
    worker_session: str
    frame_sha256: str
    deadline_ns: int
    exposure_observations: int


@dataclass(frozen=True)
class StartReceipt(_Metadata):
    id: str
    incarnation: str
    dispatch_id: str
    worker_session: str
    frame_sha256: str
    started_ns: int
    first_observation_index: int


@dataclass(frozen=True)
class CompletionReceipt(_Metadata):
    id: str
    incarnation: str
    dispatch_id: str
    worker_session: str
    frame_sha256: str
    observation_indices: tuple[int, ...]
    completed_ns: int


@dataclass(frozen=True)
class AdmissionSnapshot(_Metadata):
    incarnation: str
    fault: Fault
    stop_required: bool
    reservation: Reservation | None
    pending: Receipt | None
    active: Receipt | None
    terminal_count: int
    reserved_receipt_slots: int


_METADATA_TYPES = (Reservation, Receipt, DispatchPermit, StartReceipt, CompletionReceipt, AdmissionSnapshot)
_OPTIONAL_FIELDS = (
    "frame_sha256", "preprocessing_version", "worker_session", "dispatch_id",
    "dispatched_ns", "started_ns", "first_observation_index", "completed_ns", "terminal_ns",
)


def _validate_metadata(value, cls):
    _require(cls in _METADATA_TYPES and type(value) is cls)
    for field in fields(cls):
        name = field.name
        item = getattr(value, name)
        if cls is Receipt and name in _OPTIONAL_FIELDS and item is None:
            continue
        if name in ("id", "incarnation", "worker_session", "dispatch_id"):
            _require(_uuid(item))
        elif name in ("source_sha256", "frame_sha256"):
            _require(_digest(item))
        elif name == "preprocessing_version":
            _require(type(item) is str and item == PREPROCESSING_VERSION)
        elif name == "status":
            _require(type(item) is str and item in _STATUSES)
        elif name == "detail":
            _require(type(item) is str and item in _DETAILS)
        elif name == "fault":
            _require(item is None or type(item) is str and item in ("clock",) + _STOP_REASONS)
        elif name in ("time_uncertain", "stop_required"):
            _require(type(item) is bool)
        elif name == "observation_indices":
            _require(type(item) is tuple and len(item) <= EXPOSURE_OBSERVATIONS)
            _require(all(_integer(index) for index in item))
        elif name in ("reservation", "pending", "active"):
            expected = Reservation if name == "reservation" else Receipt
            _require(item is None or type(item) is expected)
            if item is not None:
                _validate_metadata(item, expected)
        elif name == "encoded_bytes":
            _require(_integer(item, 1, MAX_ENCODED_BYTES))
        elif name == "revision":
            _require(_integer(item, 1, 6))
        else:
            _require(_integer(item))


@dataclass
class _Record:
    receipt: Receipt
    admit: tuple
    decoded: tuple | None = None
    moderation: tuple | None = None
    dispatch: DispatchPermit | None = None
    start: StartReceipt | None = None
    completion: CompletionReceipt | None = None
    decode_failure: tuple | None = None


class AdmissionController:
    def __init__(self, incarnation: str, clock: Clock | None = None):
        _require(_uuid(incarnation))
        self._incarnation = incarnation
        self._clock = SystemClock() if clock is None else clock
        self._lock = threading.Lock()
        self._last_ns = None
        self._fault = None
        self._reservation = None
        self._pending = None
        self._active = None
        self._worker_session = None
        self._records = {}

    def _change(self, record, **changes):
        record.receipt = replace(record.receipt, revision=record.receipt.revision + 1, **changes)
        return replace(record.receipt)

    def _terminal(self, record, now, *, status="rejected", detail, uncertain=False, **changes):
        item_id = record.receipt.id
        if self._pending == item_id:
            self._pending = None
        if self._active == item_id:
            self._active = None
        return self._change(record, status=status, detail=detail, terminal_ns=now,
                            time_uncertain=uncertain, **changes)

    def _latch(self, reason):
        if self._fault is not None:
            return
        self._fault = reason
        self._reservation = None
        for record in self._records.values():
            if record.receipt.status not in _TERMINAL:
                self._terminal(record, self._last_ns, detail=reason, uncertain=reason == "clock")

    def _maintain_locked(self, now):
        if self._reservation is not None and now >= self._reservation.expires_ns:
            self._reservation = None
        if self._pending is not None:
            record = self._records[self._pending]
            item = record.receipt
            if item.detail == "decoding" and now >= item.decode_deadline_ns:
                self._terminal(record, now, detail="decode_timeout")
            elif item.detail == "awaiting_approval" and now >= item.moderation_deadline_ns:
                self._terminal(record, now, detail="moderation_timeout")
            elif item.detail == "ready" and now >= item.deadline_ns:
                self._terminal(record, now, status="expired", detail="ttl_expired")
            elif item.detail == "dispatching" and now - item.dispatched_ns >= START_RECEIPT_NS:
                self._latch("worker_outcome_unknown")
        if self._fault is None:
            pruned = [item_id for item_id, record in self._records.items()
                      if record.receipt.terminal_ns is not None
                      and now - record.receipt.terminal_ns >= RETENTION_NS]
            for item_id in pruned:
                del self._records[item_id]

    def _synchronize(self, *, diagnostic=False):
        if self._fault is None:
            try:
                sample = self._clock.sample()
                if type(sample) is not ClockSample or not _integer(sample.monotonic_ns):
                    raise ValueError("clock")
                if self._last_ns is not None and sample.monotonic_ns < self._last_ns:
                    raise ValueError("clock")
            except Exception:
                self._latch("clock")
            else:
                self._last_ns = sample.monotonic_ns
                self._maintain_locked(self._last_ns)
        if self._fault is not None and not diagnostic:
            raise AdmissionError("clock" if self._fault == "clock" else "stopped")
        return self._last_ns

    def _snapshot_locked(self):
        return AdmissionSnapshot(
            self._incarnation, self._fault, self._fault is not None,
            replace(self._reservation) if self._reservation is not None else None,
            replace(self._records[self._pending].receipt) if self._pending is not None else None,
            replace(self._records[self._active].receipt) if self._active is not None else None,
            sum(record.receipt.status in _TERMINAL for record in self._records.values()),
            int(self._reservation is not None) + int(self._pending is not None) + int(self._active is not None),
        )

    def _find(self, item_id):
        if item_id not in self._records:
            raise AdmissionError("not_found")
        return self._records[item_id]

    def _retry(self, record, operation, payload):
        recorded = getattr(record, operation)
        if recorded is None:
            return None
        if recorded != payload:
            if operation == "moderation" and recorded[0] != payload[0]:
                raise AdmissionError("invalid_transition")
            raise AdmissionError("idempotency_conflict")
        return replace(record.receipt)

    def _require_detail(self, record, detail):
        if record.receipt.detail != detail or record.receipt.status in _TERMINAL:
            raise AdmissionError("invalid_transition")

    def _headroom(self, now, duration):
        if now > MAX_NS - duration:
            raise AdmissionError("capacity")

    def _retained_id(self, value):
        return value in self._records or any(
            record.dispatch is not None and record.dispatch.dispatch_id == value
            for record in self._records.values()
        )

    def reserve(self) -> Reservation:
        with self._lock:
            now = self._synchronize()
            if self._reservation is not None or self._pending is not None:
                raise AdmissionError("full")
            if len(self._records) >= CAPACITY:
                raise AdmissionError("capacity")
            self._headroom(now, RESERVATION_NS)
            item_id = str(uuid4())
            if self._retained_id(item_id):
                raise AdmissionError("capacity")
            self._reservation = Reservation(item_id, self._incarnation, now, now + RESERVATION_NS)
            return replace(self._reservation)

    def cancel_reservation(self, *, id: str) -> None:
        _require(_uuid(id))
        with self._lock:
            self._synchronize()
            if self._reservation is None or self._reservation.id != id:
                raise AdmissionError("not_found")
            self._reservation = None

    def admit(self, *, id: str, source_sha256: str, encoded_bytes: int) -> Receipt:
        _require(_uuid(id) and _digest(source_sha256) and _integer(encoded_bytes, 1, MAX_ENCODED_BYTES))
        payload = (source_sha256, encoded_bytes)
        with self._lock:
            now = self._synchronize()
            if id in self._records:
                return self._retry(self._records[id], "admit", payload)
            if self._reservation is None or self._reservation.id != id:
                raise AdmissionError("not_found")
            self._headroom(now, PENDING_NS)
            item = Receipt(
                id, self._incarnation, source_sha256, encoded_bytes, now, now + PENDING_NS,
                now + DECODE_NS, now + MODERATION_NS, "accepted", "decoding", None,
                None, None, None, None, None, None, None, None, 1, False,
            )
            self._records[id] = _Record(item, payload)
            self._reservation = None
            self._pending = id
            return replace(item)

    def decoded(self, *, id: str, frame_sha256: str, preprocessing_version: str) -> Receipt:
        _require(_uuid(id) and _digest(frame_sha256))
        _require(type(preprocessing_version) is str and preprocessing_version == PREPROCESSING_VERSION)
        payload = (frame_sha256, preprocessing_version)
        with self._lock:
            self._synchronize()
            record = self._find(id)
            retry = self._retry(record, "decoded", payload)
            if retry is not None:
                return retry
            self._require_detail(record, "decoding")
            record.decoded = payload
            return self._change(record, detail="awaiting_approval", frame_sha256=frame_sha256,
                                preprocessing_version=preprocessing_version)

    def decode_failed(self, *, id: str) -> Receipt:
        _require(_uuid(id))
        with self._lock:
            now = self._synchronize()
            record = self._find(id)
            retry = self._retry(record, "decode_failure", ())
            if retry is not None:
                return retry
            self._require_detail(record, "decoding")
            record.decode_failure = ()
            return self._terminal(record, now, detail="decode_failed")

    def moderate(self, *, id: str, action_id: str, approved: bool) -> Receipt:
        _require(_uuid(id) and type(action_id) is str and _ACTION.fullmatch(action_id) is not None)
        _require(type(approved) is bool)
        payload = (action_id, approved)
        with self._lock:
            now = self._synchronize()
            record = self._find(id)
            retry = self._retry(record, "moderation", payload)
            if retry is not None:
                return retry
            self._require_detail(record, "awaiting_approval")
            record.moderation = payload
            if not approved:
                return self._terminal(record, now, detail="moderation_rejected")
            return self._change(record, status="queued", detail="ready")

    def dispatch(self, *, id: str, worker_session: str) -> DispatchPermit:
        _require(_uuid(id) and _uuid(worker_session))
        with self._lock:
            now = self._synchronize()
            record = self._find(id)
            if record.dispatch is not None:
                if worker_session != record.dispatch.worker_session:
                    raise AdmissionError("idempotency_conflict")
                return replace(record.dispatch)
            self._require_detail(record, "ready")
            if self._active is not None:
                raise AdmissionError("full")
            if self._worker_session is not None and self._worker_session != worker_session:
                raise AdmissionError("wrong_worker")
            self._headroom(now, START_RECEIPT_NS)
            dispatch_id = str(uuid4())
            if self._retained_id(dispatch_id):
                raise AdmissionError("capacity")
            permit = DispatchPermit(id, self._incarnation, dispatch_id, worker_session,
                                    record.receipt.frame_sha256, record.receipt.deadline_ns,
                                    EXPOSURE_OBSERVATIONS)
            self._change(record, detail="dispatching", worker_session=worker_session,
                         dispatch_id=dispatch_id, dispatched_ns=now)
            record.dispatch = permit
            self._worker_session = worker_session
            return replace(permit)

    def _worker_record(self, receipt, operation):
        record = self._find(receipt.id)
        if record.receipt.status in _TERMINAL:
            retry = self._retry(record, operation, receipt)
            if retry is None:
                raise AdmissionError("invalid_transition")
            return record, retry
        return record, None

    def _identity_matches(self, record, receipt):
        item = record.receipt
        return (
            item.detail in ("dispatching", "processing")
            and receipt.incarnation == item.incarnation
            and receipt.worker_session == item.worker_session
            and receipt.dispatch_id == item.dispatch_id
            and receipt.frame_sha256 == item.frame_sha256
        )

    def started(self, *, receipt: StartReceipt) -> Receipt:
        _validate_metadata(receipt, StartReceipt)
        receipt = replace(receipt)
        with self._lock:
            now = self._synchronize()
            record, retry = self._worker_record(receipt, "start")
            if retry is not None:
                return retry
            item = record.receipt
            consistent = (
                self._identity_matches(record, receipt)
                and item.dispatched_ns <= receipt.started_ns < item.deadline_ns
                and receipt.started_ns <= now
                and receipt.first_observation_index <= MAX_NS - 7
                and (record.start is None or record.start == receipt)
            )
            if not consistent:
                self._latch("worker_outcome_unknown")
                return replace(record.receipt)
            if record.start is not None:
                return replace(record.receipt)
            self._pending = None
            self._active = item.id
            record.start = receipt
            return self._change(record, status="processing", detail="processing",
                                started_ns=receipt.started_ns,
                                first_observation_index=receipt.first_observation_index)

    def complete(self, *, receipt: CompletionReceipt) -> Receipt:
        _validate_metadata(receipt, CompletionReceipt)
        receipt = replace(receipt)
        with self._lock:
            now = self._synchronize()
            record, retry = self._worker_record(receipt, "completion")
            if retry is not None:
                return retry
            item = record.receipt
            consistent = (
                self._identity_matches(record, receipt)
                and record.start is not None
                and item.started_ns <= receipt.completed_ns <= now
                and receipt.observation_indices == tuple(range(item.first_observation_index,
                                                               item.first_observation_index + 8))
            )
            if not consistent:
                self._latch("worker_outcome_unknown")
                return replace(record.receipt)
            record.completion = receipt
            return self._terminal(record, now, status="processed", detail="completed",
                                  completed_ns=receipt.completed_ns)

    def stop(self, *, reason: Literal["worker_failed", "worker_outcome_unknown", "session_ended"]) -> AdmissionSnapshot:
        _require(type(reason) is str and reason in _STOP_REASONS)
        with self._lock:
            self._synchronize(diagnostic=True)
            self._latch(reason)
            return self._snapshot_locked()

    def maintain(self) -> AdmissionSnapshot:
        with self._lock:
            self._synchronize(diagnostic=True)
            return self._snapshot_locked()

    def status(self, *, id: str) -> Receipt:
        _require(_uuid(id))
        with self._lock:
            self._synchronize(diagnostic=True)
            return replace(self._find(id).receipt)

    def snapshot(self) -> AdmissionSnapshot:
        with self._lock:
            self._synchronize(diagnostic=True)
            return self._snapshot_locked()
