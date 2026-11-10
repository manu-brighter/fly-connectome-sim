"""Source-bound parent session and finite durable receipt handoff.

The session never calls image admission or the price authority. Production release
requires the exact prepared declaration and literal native-run authorization.
"""

from collections import deque
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import os
from pathlib import Path
import queue
import secrets
import threading
import time

from . import native_protocol as protocol
from .native_worker import _ordinary, _require
from .price_service import SystemClock
from .native_protocol import NativeProfile, owned, scope, current_profile


ROOT = Path(__file__).absolute().parents[1]
DEPENDENCIES = dict(numpy="2.4.6", pandas="3.0.5", pyarrow="25.0.1")


@dataclass(frozen=True, slots=True)
class NativeConfig:
    incarnation: str
    worker_session: str
    protocol_sha256: str
    work_root: Path
    profile: str = "bounded-image20s/v1"
    duration_minutes: int = 480
    max_observations: int = 86400

    def __post_init__(self):
        NativeProfile(self.profile, self.duration_minutes, self.max_observations)
        protocol._uuid(self.incarnation)
        protocol._uuid(self.worker_session)
        protocol._digest(self.protocol_sha256)
        _require(isinstance(self.work_root, Path) and self.work_root.is_absolute(), "source")
        protocol._local_path(str(self.work_root))


@dataclass(frozen=True, slots=True)
class ReceiptTicket:
    ticket: int

    def __post_init__(self):
        protocol._int(self.ticket, 1, protocol.MAX_J)


class _DTO(protocol.FrozenRecord):
    def __setattr__(self, name, value):
        raise AttributeError("immutable native record")


class PreparedNative(_DTO):
    def __init__(self, value):
        value = protocol._plain(value)
        protocol._keys(value, "schema protocol_sha256 bindings_sha256 incarnation worker_session")
        protocol._literal(value["schema"], protocol.schema("prepared"))
        for key in ("protocol_sha256", "bindings_sha256"):
            protocol._digest(value[key])
        for key in ("incarnation", "worker_session"):
            protocol._uuid(value[key])
        super().__init__(value)


class ReceiptProgress(_DTO):
    def __init__(self, value):
        value = protocol._plain(value)
        protocol._keys(value, "submitted_ticket durable_ticket queued_batches emergency_pending closed fault")
        protocol._int(value["submitted_ticket"], 0, protocol.MAX_J)
        protocol._int(value["durable_ticket"], 0, value["submitted_ticket"])
        protocol._int(value["queued_batches"], 0, 32)
        protocol._bool(value["emergency_pending"])
        protocol._bool(value["closed"])
        protocol._optional(value["fault"], lambda v: protocol._literal(v, *protocol.FAULTS))
        super().__init__(value)


class Boundary(_DTO):
    def __init__(self, value):
        value = protocol._plain(value)
        protocol._keys(value, "id next_observation_index issued_observations completed_observations active_dispatch_id unissued_active_observations free_observations ack_deadline_ns")
        for key in ("id", "next_observation_index", "issued_observations", "completed_observations", "free_observations"):
            protocol._int(value[key], 0, protocol.limits()["model_observations"])
        protocol._int(value["unissued_active_observations"], 0, 7)
        protocol._int(value["ack_deadline_ns"])
        protocol._optional(value["active_dispatch_id"], protocol._uuid)
        _require(value["id"] == value["next_observation_index"] == value["issued_observations"] == value["completed_observations"])
        _require(value["free_observations"] == protocol.free_observations(value["issued_observations"], value["unissued_active_observations"]))
        _require(value["active_dispatch_id"] is not None or value["unissued_active_observations"] == 0)
        super().__init__(value)


def _measured(value):
    value = protocol._plain(value)
    protocol._keys(value, "observation_index input_kind image_id frame_sha256 wall_completion_ns model_end_tick group_spikes group_rates_hz")
    protocol._int(value["observation_index"], 0, protocol.limits()["model_observations"] - 1)
    protocol._literal(value["input_kind"], "black", "image")
    protocol._optional(value["image_id"], protocol._uuid)
    protocol._digest(value["frame_sha256"])
    protocol._int(value["wall_completion_ns"])
    _require(value["model_end_tick"] == (value["observation_index"] + 1) * 5000)
    _require((value["image_id"] is None) == (value["input_kind"] == "black"))
    if value["input_kind"] == "black":
        _require(value["frame_sha256"] == protocol.BLACK_SHA256)
    protocol._group_map(value["group_spikes"])
    protocol._group_map(value["group_rates_hz"], rates=True)
    return value


class NativeSnapshot(_DTO):
    def __init__(self, value):
        value = protocol._plain(value)
        protocol._keys(value, "schema incarnation worker_session state fault cleanup_fault issued_observations completed_observations in_flight_index active_dispatch_id unissued_active_observations free_observations boundary wall_deadline_ns startup_deadline_ns observe_deadline_ns receipt_progress latest header_sha256 engine_identity_sha256")
        protocol._literal(value["schema"], protocol.schema("session"))
        for key in ("incarnation", "worker_session"):
            protocol._uuid(value[key])
        protocol._literal(value["state"], "prepared", "starting", "running", "stopping", "ended", "faulted", "closed")
        for key in ("fault", "cleanup_fault"):
            protocol._optional(value[key], lambda v: protocol._literal(v, *protocol.FAULTS))
        for key in ("issued_observations", "completed_observations", "free_observations"):
            protocol._int(value[key], 0, protocol.limits()["model_observations"])
        protocol._int(value["unissued_active_observations"], 0, 7)
        protocol._optional(value["in_flight_index"], lambda v: protocol._int(v, 0, protocol.limits()["model_observations"] - 1))
        protocol._optional(value["active_dispatch_id"], protocol._uuid)
        _require(value["issued_observations"] - value["completed_observations"] in (0, 1))
        expected = value["completed_observations"] if value["issued_observations"] > value["completed_observations"] else None
        _require(value["in_flight_index"] == expected)
        _require(value["free_observations"] == protocol.free_observations(value["issued_observations"], value["unissued_active_observations"]))
        if value["boundary"] is not None:
            Boundary(value["boundary"])
        ReceiptProgress(value["receipt_progress"])
        for key in ("wall_deadline_ns", "startup_deadline_ns", "observe_deadline_ns"):
            protocol._optional(value[key], protocol._int)
        for key in ("header_sha256", "engine_identity_sha256"):
            protocol._optional(value[key], protocol._digest)
        _require((value["header_sha256"] is None) == (value["engine_identity_sha256"] is None))
        _require((value["latest"] is None) == (value["completed_observations"] == 0))
        if value["latest"] is not None:
            measured = _measured(value["latest"])
            _require(measured["observation_index"] == value["completed_observations"] - 1)
        if value["state"] == "ended":
            _require((current_profile().live or value["completed_observations"] == protocol.limits()["model_observations"]) and value["fault"] is None
                     and (current_profile().live or (value["in_flight_index"] is None and value["active_dispatch_id"] is None)) and value["boundary"] is None)
        if value["state"] == "faulted":
            _require(value["fault"] is not None)
        super().__init__(value)


class NativeNotice(_DTO):
    def __init__(self, value):
        value = protocol._plain(value)
        protocol._keys(value, "notice_seq incarnation worker_session protocol_sha256 type payload")
        protocol._int(value["notice_seq"], 0, protocol.limits()["event_records"] - 1)
        protocol._uuid(value["incarnation"])
        protocol._uuid(value["worker_session"])
        protocol._digest(value["protocol_sha256"])
        kind, payload = value["type"], value["payload"]
        protocol._literal(kind, "ready", "boundary", "start", "observation", "complete", "ended", "fault")
        if kind == "ready":
            protocol._keys(payload, "header_sha256 engine_identity_sha256 ready_ns")
            protocol._digest(payload["header_sha256"])
            protocol._digest(payload["engine_identity_sha256"])
            protocol._int(payload["ready_ns"])
        elif kind == "boundary":
            Boundary(payload)
        elif kind == "start":
            protocol._start(payload)
        elif kind == "complete":
            protocol._complete(payload)
        elif kind == "observation":
            _measured(payload)
        elif kind == "ended":
            protocol._keys(payload, "reason completed")
            protocol._literal(payload["reason"], *( ("model_limit", "cancelled", "wall_limit") if current_profile().live else ("model_limit", "cancelled") ))
            protocol._int(payload["completed"], 0, protocol.limits()["model_observations"])
            _require(payload["reason"] != "model_limit" or payload["completed"] == protocol.limits()["model_observations"])
        else:
            protocol._keys(payload, "code cleanup_fault")
            protocol._literal(payload["code"], *protocol.FAULTS)
            protocol._optional(payload["cleanup_fault"], lambda v: protocol._literal(v, *protocol.FAULTS))
        if kind in ("start", "complete"):
            _require(payload["incarnation"] == value["incarnation"] and payload["worker_session"] == value["worker_session"])
        super().__init__(value)


def _binding(path, cap, deadline_ns):
    path = _ordinary(path)
    before = path.stat()
    relative_source = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else None
    minimum = 0 if protocol.PRESERVED_SOURCES.get(relative_source) == protocol.EMPTY_SHA256 else 1
    _require(path.is_file() and minimum <= before.st_size <= cap, "source")
    expected = protocol._stat_identity(before)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        _require(protocol._stat_identity(os.fstat(stream.fileno())) == expected, "source")
        remaining = before.st_size
        while remaining:
            _require(time.perf_counter_ns() < deadline_ns, "deadline")
            raw = stream.read(min(1048576, remaining))
            _require(bool(raw), "source")
            digest.update(raw)
            remaining -= len(raw)
        _require(not stream.read(1) and protocol._stat_identity(os.fstat(stream.fileno())) == expected, "source")
    _require(protocol._stat_identity(path.stat()) == expected and time.perf_counter_ns() < deadline_ns, "source")
    return dict(path=str(path), bytes=before.st_size, sha256=digest.hexdigest(),
                device=before.st_dev, file_id=before.st_ino, mtime_ns=before.st_mtime_ns)


def current_protocol(profile="bounded-image20s/v1", duration_minutes=480, max_observations=86400):
    with scope(NativeProfile(profile, duration_minutes, max_observations)):
        return _current_protocol()


def _current_protocol():
    """Read the exact reviewed source declaration; no model/cache/process work."""
    deadline = time.perf_counter_ns() + 120_000_000_000
    maps = {}
    for label, names in (("preserved_sources", protocol.PRESERVED_SOURCES),
                         ("application_sources", protocol.application_sources()),
                         ("lock_sources", protocol.LOCK_SOURCES)):
        maps[label] = {name: _binding(ROOT / name, 1048576, deadline)["sha256"] for name in names}
    return protocol.validate_protocol(dict(schema=protocol.schema("protocol"), proof=current_profile().name,
                                           constants=protocol.limits(), **maps,
                                           package_fingerprint=protocol.PACKAGE_FINGERPRINT))


def _record(value):
    return protocol.FrozenRecord(protocol._plain(value))


@owned
class NativeSession:
    def __init__(self, config, clock):
        _require(type(config) is NativeConfig)
        self.config, self.clock = config, clock
        self.profile = NativeProfile(config.profile, config.duration_minutes, config.max_observations)
        self._readout_enabled = False
        self._readouts = deque()
        protocol._clock(clock.describe())
        self._lock = threading.RLock()
        self._changed = threading.Condition(self._lock)
        self._event_lock = threading.RLock()
        self._clock_lock = threading.Lock()
        self._last_ns = None
        self._state = "prepared"
        self._fault = self._cleanup_fault = None
        self._clock_fault = self._later_clock_notice = False
        self._prepared = self._bindings = self._protocol = None
        self._protocol_raw = self._bindings_raw = None
        self._attempted = False
        self._transport = self._thread = None
        self._stop = threading.Event()
        self._session_fault_stop = False
        self._command = self._boundary = None
        self._issued = self._completed = 0
        self._permit = self._start = self._complete = None
        self._ordinal = None
        self._latest = self._header = self._pending_header = None
        self._wall_deadline = self._startup_deadline = self._observe_deadline = None
        self._final_deadline = self._stop_ns = None
        self._notices = deque()
        self._overflow_notice = None
        self._notice_seq = 0
        self._nonce = None
        self._send_seq = 0
        self._validator = protocol.ProtocolValidator()
        self._events = None
        self._event_seq = self._event_bytes = 0
        self._event_sha = protocol.ZERO_SHA256
        self._event_digest = hashlib.sha256()
        self._receipt_validator = protocol.ReceiptEvidence()
        self._outbox = queue.Queue(maxsize=32)
        self._reservation = None
        self._ticket = self._submitted_ticket = self._durable_ticket = 0
        self._pending_batches = 0
        self._emergency_batch = None
        self._emergency_used = self._emergency_writing = False
        self._receipt_closed = False
        self._writer = None
        self._watchdog = None
        self._watchdog_stop = threading.Event()
        self._storage_started_ns = None
        self._writer_done = threading.Event()
        self._durable_receipts = {}
        self._worker_ended = self._full_eof = False
        self._terminal_reason = None
        self._last_receive_ns = None
        self._outcome = None

    def enable_readout(self):
        with self._lock:
            _require(not self._attempted and self._state == "prepared", "startup")
            self._readout_enabled = True

    def readout_identity(self):
        with self._lock:
            if self._header is None:
                return None
            identity = dict(protocol_sha256=self.config.protocol_sha256,
                engine_identity_sha256=self._header.engine_identity.sha256,
                header_sha256=protocol.canonical_sha256(self._header))
            return _record(dict(worker_session=self.config.worker_session,
                source_sha256=protocol.canonical_sha256(identity), **identity))

    def poll_readouts(self):
        with self._lock:
            return tuple(self._readouts.popleft() for _ in range(min(8, len(self._readouts))))

    def _publish_readout(self, observation):
        with self._lock:
            if not self._readout_enabled:
                return
            _require(len(self._readouts) < 8, "resource")
            identity = self.readout_identity()
            _require(identity is not None, "source")
            names = ("observation_index", "start_tick", "end_tick", "wall_start_ns",
                "wall_completion_ns", "frame_sha256", "input_kind", "dispatch_id", "group_bin_counts")
            self._readouts.append(_record(dict(
                worker_session=identity.worker_session, source_sha256=identity.source_sha256,
                header_sha256=identity.header_sha256, protocol_sha256=identity.protocol_sha256,
                **{name: observation[name] for name in names})))

    def _now(self):
        with self._clock_lock:
            try:
                value = self.clock.sample().monotonic_ns
                valid = (not self._clock_fault and type(value) is int and 0 <= value <= protocol.MAX_NS
                         and (self._last_ns is None or value >= self._last_ns))
            except BaseException:
                value, valid = None, False
            if valid:
                self._last_ns = value
        if not valid:
            self._latch("clock")
            raise protocol.ProtocolError("clock")
        return value

    def _latch(self, code):
        _require(code in protocol.FAULTS)
        with self._changed:
            new_clock = code == "clock" and not self._clock_fault
            if new_clock:
                self._clock_fault = True
            if self._fault is None:
                self._fault = code
                self._state = "faulted"
                if self._notice_seq < protocol.limits()["event_records"]:
                    notice = self._make_notice("fault", dict(code=code, cleanup_fault=self._cleanup_fault))
                    if len(self._notices) < 8:
                        self._notices.append(notice)
                    else:
                        self._overflow_notice = notice
            elif new_clock:
                if len(self._notices) < 8 and self._overflow_notice is None:
                    self._notices.append(self._make_notice("fault", dict(code="clock", cleanup_fault=self._cleanup_fault)))
                else:
                    self._later_clock_notice = True
            self._boundary = self._command = None
            self._stop.set()
            self._changed.notify_all()

    def _make_notice(self, kind, payload):
        _require(self._notice_seq < protocol.limits()["event_records"], "resource")
        notice = NativeNotice(dict(notice_seq=self._notice_seq,
            incarnation=self.config.incarnation, worker_session=self.config.worker_session,
            protocol_sha256=self.config.protocol_sha256, type=kind, payload=payload))
        self._notice_seq += 1
        return notice

    def _notice(self, kind, payload):
        with self._lock:
            if len(self._notices) >= 8 or self._notice_seq >= protocol.limits()["event_records"] - 1:
                self._latch("resource")
                return
            self._notices.append(self._make_notice(kind, payload))

    def poll(self):
        with self._lock:
            result = tuple(self._notices.popleft() for _ in range(min(8, len(self._notices))))
            if len(result) < 8 and self._overflow_notice is not None:
                result += (self._overflow_notice,)
                self._overflow_notice = None
            if len(result) < 8 and self._later_clock_notice and self._notice_seq < protocol.limits()["event_records"]:
                result += (self._make_notice("fault", dict(code="clock", cleanup_fault=self._cleanup_fault)),)
                self._later_clock_notice = False
            return result

    def receipt_progress(self):
        with self._lock:
            return ReceiptProgress(dict(submitted_ticket=self._submitted_ticket, durable_ticket=self._durable_ticket,
                queued_batches=self._pending_batches,
                emergency_pending=self._emergency_batch is not None or self._emergency_writing,
                closed=self._receipt_closed, fault=self._fault))

    def _unissued(self):
        return 7 - self._ordinal if self._permit is not None else 0

    def snapshot(self):
        with self._lock:
            return NativeSnapshot(dict(schema=protocol.schema("session"),
                incarnation=self.config.incarnation, worker_session=self.config.worker_session,
                state=self._state, fault=self._fault, cleanup_fault=self._cleanup_fault,
                issued_observations=self._issued, completed_observations=self._completed,
                in_flight_index=self._completed if self._issued == self._completed + 1 else None,
                active_dispatch_id=self._permit.dispatch_id if self._permit else None,
                unissued_active_observations=self._unissued(),
                free_observations=protocol.free_observations(self._issued, self._unissued()),
                boundary=self._boundary, wall_deadline_ns=self._wall_deadline,
                startup_deadline_ns=self._startup_deadline, observe_deadline_ns=self._observe_deadline,
                receipt_progress=self.receipt_progress(), latest=self._latest,
                header_sha256=protocol.canonical_sha256(self._header) if self._header else None,
                engine_identity_sha256=self._header.engine_identity.sha256 if self._header else None))

    def reserve_receipts(self):
        with self._lock:
            if self._fault or self._receipt_closed or self._pending_batches >= 32:
                if self._pending_batches >= 32:
                    self._latch("storage")
                return None
            _require(self._reservation is None, "journal_gap")
            if self._ticket >= protocol.MAX_J:
                self._latch("resource")
                return None
            self._ticket += 1
            self._pending_batches += 1
            self._reservation = ReceiptTicket(self._ticket)
            return self._reservation

    def publish_receipts(self, ticket, entries):
        with self._changed:
            try:
                emergency = ticket is None
                if emergency:
                    _require((self._fault is not None or self._session_fault_stop) and not self._emergency_used
                             and not self._receipt_closed, "journal_gap")
                    if self._reservation is not None:
                        _require(self._session_fault_stop, "journal_gap")
                        self._reservation = None
                        self._pending_batches -= 1
                    if self._fault is None:
                        self._latch("journal_gap")
                    _require(self._ticket < protocol.MAX_J, "resource")
                    ticket = ReceiptTicket(self._ticket + 1)
                else:
                    _require(type(ticket) is ReceiptTicket and ticket == self._reservation, "journal_gap")
                _require(type(entries) is tuple and len(entries) <= (2 if emergency else 3), "journal_gap")
                plain = []
                for entry in entries:
                    if hasattr(entry, "to_dict"):
                        entry = entry.to_dict()
                    protocol._keys(entry, "receipt cause")
                    original = entry["receipt"]
                    receipt = protocol.validate_receipt(asdict(original) if is_dataclass(original) else original)
                    protocol._cause(entry["cause"])
                    if emergency:
                        _require(receipt.terminal_ns is not None and entry["cause"]["operation"] in ("stop", "snapshot", "status")
                                 and entry["cause"]["target_id"] == receipt.id, "journal_gap")
                    if self._receipt_validator.accept(receipt):
                        plain.append(dict(receipt=receipt, cause=entry["cause"]))
                batch = _record(dict(ticket=ticket.ticket, entries=plain))
                _require(len(protocol.canonical_bytes(batch)) <= 8192, "journal_gap")
                if emergency:
                    self._emergency_used = True
                    self._ticket = ticket.ticket
                    self._emergency_batch = batch
                elif self._events is None and not plain and self._outbox.empty():
                    self._durable_ticket = ticket.ticket
                    self._pending_batches -= 1
                else:
                    self._outbox.put_nowait(batch)
                self._submitted_ticket = ticket.ticket
                self._reservation = None
                self._changed.notify_all()
            except (ValueError, queue.Full):
                self._latch("journal_gap")
                raise protocol.ProtocolError("journal_gap") from None

    def finish_receipts(self):
        with self._changed:
            _require(self._reservation is None, "journal_gap")
            self._receipt_closed = True
            self._changed.notify_all()

    def _event(self, kind, payload, binary=b"", *, recorded_ns=None):
        # Neither coordinator nor snapshot lock is held across disk IO.
        with self._event_lock:
            _require(self._events is not None, "storage")
            try:
                now = self._now() if recorded_ns is None else recorded_ns
            except protocol.ProtocolError as error:
                _require(error.code == "clock", error.code)
                now = None
            row = protocol.make_event(self._event_seq, self._event_sha, now, kind, payload, binary)
            raw = protocol.encode_event(row, binary)
            _require(self._event_seq < protocol.limits()["event_records"] and self._event_bytes + len(raw) <= protocol.limits()["event_bytes"], "resource")
            started = self._storage_started_ns = time.perf_counter_ns()
            try:
                self._events.write(raw)
                self._events.flush()
                os.fsync(self._events.fileno())
                _require(time.perf_counter_ns() - started < 5_000_000_000, "storage")
            finally:
                self._storage_started_ns = None
            self._event_seq += 1
            self._event_bytes += len(raw)
            self._event_sha = row.sha256
            self._event_digest.update(raw)
            return row

    def _write_receipts(self):
        try:
            while True:
                try:
                    batch = self._outbox.get(timeout=0.02)
                except queue.Empty:
                    with self._lock:
                        if self._emergency_batch is not None:
                            batch, self._emergency_batch = self._emergency_batch, None
                            self._emergency_writing = True
                        elif self._receipt_closed and self._outbox.empty():
                            return
                        else:
                            continue
                for entry in batch.entries:
                    self._event("receipt", dict(ticket=batch.ticket, receipt=entry.receipt, cause=entry.cause))
                with self._changed:
                    for entry in batch.entries:
                        self._durable_receipts[entry.receipt.id] = (entry.receipt, entry.cause, batch.ticket)
                    self._durable_ticket = batch.ticket
                    emergency = self._emergency_writing
                    if emergency:
                        self._emergency_writing = False
                    else:
                        self._pending_batches -= 1
                    self._changed.notify_all()
                if not emergency:
                    self._outbox.task_done()
        except BaseException as error:
            self._latch(error.code if isinstance(error, protocol.ProtocolError) else "storage")
        finally:
            self._writer_done.set()

    def _open_evidence(self):
        self._events = (self.config.work_root / "events.bin").open("xb", buffering=0)
        self._writer = threading.Thread(target=self._write_receipts, name="native-receipt-writer", daemon=True)
        self._writer.start()
        self._watchdog = threading.Thread(target=self._watch_storage, name="native-storage-watchdog", daemon=True)
        self._watchdog.start()

    def _watch_storage(self):
        while not self._watchdog_stop.wait(0.02):
            started = self._storage_started_ns
            if started is not None and time.perf_counter_ns() - started >= 5_000_000_000:
                self._latch("storage")
                self.begin_stop("session_fault")
                return

    def _open_test_evidence(self):
        self.config.work_root.mkdir()
        self._open_evidence()

    def _close_test_evidence(self):
        self._writer.join(2)
        _require(not self._writer.is_alive(), "storage")
        self._events.flush()
        os.fsync(self._events.fileno())
        self._events.close()
        self._events = None
        self._watchdog_stop.set()
        self._watchdog.join(1)

    def prepare(self):
        with self._lock:
            _require(self._state == "prepared" and not self._attempted and self._prepared is None and self._fault is None, "startup")
        deadline = time.perf_counter_ns() + 120_000_000_000
        try:
            declaration = current_protocol(self.profile.name, self.profile.duration_minutes, self.profile.max_observations) if self.profile.live else current_protocol()
            declaration_raw = protocol.canonical_bytes(declaration)
            _require(hashlib.sha256(declaration_raw).hexdigest() == self.config.protocol_sha256, "source")
            files = {name: _binding(ROOT / name, 1048576, deadline)
                     for name in (*protocol.PRESERVED_SOURCES, *protocol.application_sources(), *protocol.LOCK_SOURCES)}
            runtime = Path(os.environ.get("FLY_CONNECTOME_SIM_DATA", str(ROOT / "data/malecns-v1.0/runtime"))).absolute()
            compiler = Path(os.environ.get("FLY_CONNECTOME_SIM_CXX", str(ROOT / ".tools/zig/zig-x86_64-windows-0.16.0/zig.exe"))).absolute()
            site = ROOT / ".venv/Lib/site-packages"
            cfg_path = ROOT / ".venv/pyvenv.cfg"
            cfg = protocol._bounded_file(cfg_path, 1048576).decode("utf-8")
            settings = dict(line.split(" = ", 1) for line in cfg.splitlines() if " = " in line)
            _require(settings.get("version_info") == "3.12.14" and settings.get("include-system-site-packages") == "false", "source")
            worker_exe = Path(settings["home"]) / "python.exe"
            paths = dict(python_launcher=ROOT / ".venv/Scripts/python.exe", python_config=cfg_path,
                         worker_exe=worker_exe, compiler_exe=compiler,
                         native_library=runtime / "cache/physiology-v6/memory.dll",
                         native_metadata=runtime / "cache/physiology-v6/memory.dll.json",
                         graph=runtime / "graph.npz", normalized_neurons=runtime / "normalized/neurons.feather",
                         **{name: runtime / (name + ".feather") for name in ("annotations", "neurotransmitters", "edges")})
            for name, version in DEPENDENCIES.items():
                paths[name + "_init"] = site / name / "__init__.py"
                paths[name + "_metadata"] = site / (name + "-" + version + ".dist-info") / "METADATA"
            for name, path in paths.items():
                cap = 4294967296 if name in protocol.RUNTIME_KEYS else 536870912 if name in ("python_launcher", "worker_exe", "compiler_exe", "native_library") else 1048576
                files[name] = _binding(path, cap, deadline)
            for name, version in DEPENDENCIES.items():
                metadata = protocol._bounded_file(paths[name + "_metadata"], 1048576, binding=files[name + "_metadata"]).decode("utf-8")
                _require(metadata.count("\nVersion: " + version + "\n") == 1
                         and metadata.count("\nName: " + name + "\n") == 1, "source")
            metadata_raw = protocol._bounded_file(paths["native_metadata"], 1048576, binding=files["native_metadata"])
            native_metadata = protocol.parse_json(metadata_raw, byte_limit=1048576)
            _require(native_metadata["source_sha256"] == files["src/fly_connectome_sim/neural/kernel.cpp"]["sha256"], "source")
            root = self.config.work_root
            scratch = root / "scratch"
            windows = os.environ["SystemRoot"]
            environment = dict(SystemRoot=windows, WINDIR=windows,
                PATH=";".join((str(worker_exe.parent), str(Path(windows) / "System32"), windows)),
                TMP=str(scratch), TEMP=str(scratch), PYTHONPATH=";".join((str(ROOT), str(ROOT / "src"), str(site))),
                PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                FLY_CONNECTOME_SIM_DATA=str(runtime), FLY_CONNECTOME_SIM_CXX=str(compiler))
            binding = dict(schema=protocol.schema("bindings"), protocol_sha256=self.config.protocol_sha256,
                incarnation=self.config.incarnation, worker_session=self.config.worker_session,
                project_root=str(ROOT), work_root=str(root), decoder_work_root=str(root.parent / (root.name + "-decoder")),
                runtime_root=str(runtime), files=files, environment=environment, python_version="3.12.14",
                compiler_probe=dict(executable_sha256=files["compiler_exe"]["sha256"], argv=[str(compiler), "version"],
                    environment_sha256=protocol.canonical_sha256(environment), expected_version="0.16.0",
                    timeout_ns=5000000000, stdout_limit=4096, stderr_limit=4096),
                native_metadata=native_metadata, dependencies=dict(site_packages=str(site), **DEPENDENCIES),
                package_fingerprint=protocol.PACKAGE_FINGERPRINT, prepared_ns=self._now())
            binding = protocol.validate_bindings(binding, declaration)
            binding_raw = protocol.canonical_bytes(binding)
            _require(time.perf_counter_ns() < deadline, "deadline")
            _ordinary(root.parent)
            root.mkdir()
            scratch.mkdir()
            self._write_new(root / "protocol.json", declaration_raw, deadline)
            self._write_new(root / "bindings.json", binding_raw, deadline)
            self._protocol, self._bindings = declaration, binding
            self._protocol_raw, self._bindings_raw = declaration_raw, binding_raw
            self._prepared = PreparedNative(dict(schema=protocol.schema("prepared"),
                protocol_sha256=self.config.protocol_sha256, bindings_sha256=hashlib.sha256(binding_raw).hexdigest(),
                incarnation=self.config.incarnation, worker_session=self.config.worker_session))
            return self._prepared
        except BaseException as error:
            self._latch(error.code if isinstance(error, protocol.ProtocolError) else "source")
            raise

    def _write_new(self, path, raw, deadline):
        _require(time.perf_counter_ns() < deadline, "deadline")
        with path.open("xb", buffering=0) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        identity = protocol._stat_identity(protocol._ordinary(path))
        _require(protocol._bounded_file(path, max(1, len(raw))) == raw and time.perf_counter_ns() < deadline, "storage")
        _require(protocol._stat_identity(protocol._ordinary(path)) == identity, "source")
        return identity

    def load_prepared(self, expected_sha256):
        """Read a fresh prepared directory in a later CLI process, without launch."""
        protocol._digest(expected_sha256)
        with self._lock:
            _require(self._state == "prepared" and not self._attempted and self._prepared is None and self._fault is None, "startup")
        deadline = time.perf_counter_ns() + 120_000_000_000
        try:
            root = _ordinary(self.config.work_root)
            _require(root.is_dir() and {path.name for path in root.iterdir()} == {"protocol.json", "bindings.json", "scratch"}, "startup")
            scratch = _ordinary(root / "scratch")
            _require(scratch.is_dir() and not any(scratch.iterdir()), "startup")
            declaration_raw = protocol._bounded_file(root / "protocol.json", 1048576)
            binding_raw = protocol._bounded_file(root / "bindings.json", 1048576)
            declaration = protocol.validate_protocol(protocol.parse_json(declaration_raw, byte_limit=1048576, node_limit=20000))
            _require(declaration_raw == protocol.canonical_bytes(declaration)
                     and hashlib.sha256(declaration_raw).hexdigest() == self.config.protocol_sha256, "source")
            binding = protocol.validate_bindings(protocol.parse_json(binding_raw, byte_limit=1048576, node_limit=20000), declaration)
            _require(binding_raw == protocol.canonical_bytes(binding)
                     and binding.incarnation == self.config.incarnation and binding.worker_session == self.config.worker_session
                     and Path(binding.work_root) == root and Path(binding.project_root) == ROOT, "source")
            prepared = PreparedNative(dict(schema=protocol.schema("prepared"), protocol_sha256=self.config.protocol_sha256,
                bindings_sha256=hashlib.sha256(binding_raw).hexdigest(), incarnation=self.config.incarnation,
                worker_session=self.config.worker_session))
            _require(protocol.canonical_sha256(prepared) == expected_sha256, "source")
            _require(protocol.canonical_bytes(current_protocol(self.profile.name, self.profile.duration_minutes, self.profile.max_observations) if self.profile.live else current_protocol()) == declaration_raw, "source")
            _require(time.perf_counter_ns() < deadline, "deadline")
            self._protocol, self._bindings = declaration, binding
            self._protocol_raw, self._bindings_raw = declaration_raw, binding_raw
            self._prepared = prepared
            return prepared
        except BaseException as error:
            code = getattr(error, "code", "source")
            self._latch(code)
            raise protocol.ProtocolError(code) from None

    def _compare_controls(self, deadline):
        for name, raw in (("protocol.json", self._protocol_raw), ("bindings.json", self._bindings_raw)):
            _require(time.perf_counter_ns() < deadline, "deadline")
            _require(protocol._bounded_file(self.config.work_root / name, 1048576) == raw, "source")
            _require(time.perf_counter_ns() < deadline, "deadline")

    def start(self, prepared, allow_native_run):
        with self._lock:
            _require(self._state == "prepared" and allow_native_run is True and not self._attempted and self._prepared is not None
                     and prepared == self._prepared and self._fault is None, "startup")
            self._attempted = True
            self._state = "starting"
        from .native_windows import OwnedNativeChild, compare_bound_files
        try:
            deadline = time.perf_counter_ns() + 120_000_000_000
            self._compare_controls(deadline)
            compare_bound_files(self._bindings, deadline_ns=deadline)
            self._open_evidence()
            self._event("binding", dict(protocol_sha256=self.config.protocol_sha256,
                                        bindings_sha256=self._prepared.bindings_sha256))
            self._transport = OwnedNativeChild(self._bindings.to_dict(), self.clock)
            self._transport.start()
            released = self._transport.resumed_ns
            with self._lock:
                self._wall_deadline = released + protocol.limits()["wall_ns"]
                self._startup_deadline = released + 180_000_000_000
                self._nonce = secrets.token_hex(32)
            self._thread = threading.Thread(target=self._run, name="native-session", daemon=True)
            self._thread.start()
        except BaseException as error:
            self._latch(getattr(error, "code", "startup"))
            try:
                self.begin_stop("session_fault")
            except BaseException:
                # Keep the original start error; the bound owner and common
                # stop epoch remain available for the caller's cleanup.
                pass
            raise

    def _send(self, kind, fields, binary=b"", *, deadline):
        _require(self._fault is None, self._fault or "protocol")
        message = dict(schema=protocol.schema("ipc"), type=kind, seq=self._send_seq,
            incarnation=self.config.incarnation, worker_session=self.config.worker_session,
            protocol_sha256=self.config.protocol_sha256, launch_nonce=self._nonce, **fields)
        with self._event_lock:
            now = self._now()
            self._validator.accept(message, "parent", binary, receipt_ns=now)
            self._event("wire", protocol.wire_payload(message, "parent", binary), binary, recorded_ns=now)
        self._transport.send(message, binary, deadline_ns=min(deadline, self._wall_deadline))
        self._send_seq += 1

    def _receive(self, *, deadline, cap=4096):
        frame = self._transport.receive(deadline_ns=min(deadline, self._wall_deadline + (35_000_000_000 if self.profile.live else 0)), max_body=cap)
        _require(frame is not None)
        with self._event_lock:
            return self._accept_received(frame, deadline)

    def _accept_received(self, frame, deadline):
        received_real_ns = time.perf_counter_ns()
        now = self._now()
        self._last_receive_ns = now
        message = self._validator.accept(frame.message, "worker", frame.binary, receipt_ns=now)
        if message.type == "ended" and message.reason in ("model_limit", "wall_limit"):
            with self._lock:
                if self._stop_ns is None:
                    self._stop_ns = now
                    self._final_deadline = received_real_ns + 25_000_000_000
        if message.type == "static_header":
            arrays = protocol.parse_json(protocol._bounded_file(Path(self._bindings.files["src/fly_connectome_sim/neural/arrays.lock.json"].path), 1048576,
                binding=self._bindings.files["src/fly_connectome_sim/neural/arrays.lock.json"]), byte_limit=1048576)
            sources = protocol.parse_json(protocol._bounded_file(Path(self._bindings.files["src/fly_connectome_sim/neural/sources.lock.json"].path), 1048576,
                binding=self._bindings.files["src/fly_connectome_sim/neural/sources.lock.json"]), byte_limit=1048576)
            header = protocol.validate_header(message.header, bindings=self._bindings, arrays_lock=arrays, sources_lock=sources)
            self._write_new(self.config.work_root / "header.json", protocol.canonical_bytes(header),
                            time.perf_counter_ns() + max(0, min(deadline, self._wall_deadline) - now))
            with self._lock:
                self._pending_header = header
            self._event("header", dict(header_sha256=protocol.canonical_sha256(header),
                engine_identity_sha256=header.engine_identity.sha256, worker_seq=message.seq), recorded_ns=now)
        else:
            self._event("wire", protocol.wire_payload(message, "worker", frame.binary), frame.binary, recorded_ns=now)
        if message.type == "fault":
            raise protocol.ProtocolError(message.code)
        return message

    def _startup(self):
        deadline = self._startup_deadline
        self._send("hello", dict(bindings_sha256=self._prepared.bindings_sha256, parent_clock=self.clock.describe(),
            **(dict(wall_deadline_ns=self._wall_deadline) if self.profile.live else {})), deadline=deadline)
        hello = self._receive(deadline=deadline)
        _require(hello.worker == self._transport.identity and hello.bindings_sha256 == self._prepared.bindings_sha256, "ownership")
        brackets = []
        for index in range(3):
            p0 = self._now()
            self._send("challenge", dict(challenge_index=index, p0_ns=p0), deadline=min(deadline, p0 + 2_000_000_000))
            answer = self._receive(deadline=min(deadline, p0 + 2_000_000_000))
            p1 = self._last_receive_ns
            bracket = dict(index=index, p0_ns=p0, child_ns=answer.child_ns, p1_ns=p1)
            brackets.append(bracket)
            self._event("clock_bracket", bracket, recorded_ns=p1)
        protocol.validate_clock_brackets(brackets)
        self._send("initialize", dict(bindings_sha256=self._prepared.bindings_sha256), deadline=deadline)
        request = self._receive(deadline=deadline)
        allowed = self._transport.permit_probe(request)
        self._send("probe_allow", dict(request_seq=request.seq, allowed_ns=allowed), deadline=deadline)
        started = self._receive(deadline=min(deadline, allowed + 5_000_000_000))
        self._transport.accept_probe_started(started)
        finished = self._receive(deadline=min(deadline, allowed + 5_000_000_000))
        self._transport.accept_probe_finished(finished)
        self._receive(deadline=deadline, cap=2097152)
        ready = self._receive(deadline=deadline, cap=8192)
        with self._lock:
            self._header = self._pending_header
            self._state = "running"
        self._notice("ready", dict(header_sha256=ready.header_sha256,
                                   engine_identity_sha256=ready.engine_identity_sha256, ready_ns=ready.ready_ns))
        self._issue(dict(last_observation_index=None, next_observation_index=0, action="black",
                         permit=None, dispatch_id=None, exposure_ordinal=None), b"", deadline=deadline, initial=True)

    def _authorize(self, fields):
        self._boundary = None
        if fields["action"] != "end":
            self._issued += 1
            observe_deadline = self._now() + 35_000_000_000
            self._observe_deadline = observe_deadline if self.profile.live or self._wall_deadline is None else min(self._wall_deadline, observe_deadline)
        else:
            self._observe_deadline = None

    def _issue(self, fields, binary, *, deadline, initial=False):
        with self._lock:
            if initial or fields["action"] == "end":
                self._authorize(fields)
        self._send("release" if initial else "ack", fields, binary, deadline=deadline)

    def _has_receipt(self, value, detail, operation, notice_seq=None):
        found = self._durable_receipts.get(value.id)
        if found is None:
            return False
        receipt, cause, _ = found
        return ((receipt.status == detail if detail in ("processing", "processed") else receipt.detail == detail)
                and cause.operation == operation
                and (notice_seq is None or cause.notice_seq == notice_seq)
                and all(receipt[key] == value[key] for key in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256"))
                and all(receipt[key] == value[key] for key in ("started_ns", "first_observation_index", "completed_ns") if key in value))

    def _wait_receipt(self, value, detail, operation, deadline, notice_seq):
        with self._changed:
            while not self._has_receipt(value, detail, operation, notice_seq):
                _require(self._fault is None and not self._stop.is_set(), self._fault or "worker_outcome_unknown")
                remaining = min(deadline, self._wall_deadline) - self._now()
                _require(remaining > 0, "deadline")
                self._changed.wait(min(0.02, remaining / 1e9))

    def _run(self):
        try:
            self._startup()
            while True:
                message = self._receive(deadline=self._observe_deadline or (self._wall_deadline + (35_000_000_000 if self.profile.live else 0)), cap=32768)
                if self.profile.live and message.type == "ended" and message.reason == "wall_limit":
                    _require(message.wall_ns >= self._wall_deadline, "clock")
                    self._finish_ended(message, message.wall_ns + 5_000_000_000)
                    return
                if message.type == "start":
                    with self._lock:
                        self._start = message.receipt
                        seq = self._notice_seq
                    self._notice("start", message.receipt)
                    self._wait_receipt(message.receipt, "processing", "started", self._observe_deadline, seq)
                    continue
                _require(message.type == "observation")
                self._publish_readout(message)
                with self._lock:
                    self._completed += 1
                    self._observe_deadline = None
                    measured = dict(observation_index=message.observation_index, input_kind=message.input_kind,
                        image_id=message.image_id, frame_sha256=message.frame_sha256,
                        wall_completion_ns=message.wall_completion_ns, model_end_tick=message.end_tick,
                        group_spikes=message.group_spikes, group_rates_hz=message.group_rates_hz)
                    self._latest = _record(measured)
                self._notice("observation", measured)
                ack_deadline = message.wall_completion_ns + 5_000_000_000 if self.profile.live else min(message.wall_completion_ns + 5_000_000_000, self._wall_deadline)
                if message.exposure_ordinal == 7:
                    complete = self._receive(deadline=ack_deadline)
                    _require(complete.type == "complete")
                    with self._lock:
                        seq = self._notice_seq
                        self._complete = complete.receipt
                    self._notice("complete", complete.receipt)
                    self._wait_receipt(complete.receipt, "processed", "complete", ack_deadline, seq)
                    with self._lock:
                        self._permit = self._start = self._ordinal = None
                with self._changed:
                    _require(not self._stop.is_set() and self._fault is None, self._fault or "worker_outcome_unknown")
                    if self._completed == protocol.limits()["model_observations"]:
                        command = (dict(last_observation_index=protocol.limits()["model_observations"] - 1, next_observation_index=None, action="end",
                                        permit=None, dispatch_id=None, exposure_ordinal=None), b"")
                    else:
                        boundary = dict(id=self._completed, next_observation_index=self._completed,
                            issued_observations=self._issued, completed_observations=self._completed,
                            active_dispatch_id=self._permit.dispatch_id if self._permit else None,
                            unissued_active_observations=self._unissued(),
                            free_observations=protocol.free_observations(self._issued, self._unissued()), ack_deadline_ns=ack_deadline)
                        self._boundary = Boundary(boundary)
                        self._notice("boundary", boundary)
                        while self._command is None:
                            _require(not self._stop.is_set() and self._fault is None, self._fault or "worker_outcome_unknown")
                            if self.profile.live and self._now() >= self._wall_deadline:
                                break
                            remaining = min(ack_deadline, self._wall_deadline) - self._now()
                            _require(remaining > 0, "deadline")
                            self._changed.wait(min(0.02, remaining / 1e9))
                        command, self._command = self._command, None
                if self.profile.live and (command is None or self._now() >= self._wall_deadline):
                    continue
                self._issue(*command, deadline=ack_deadline)
                if self._completed == protocol.limits()["model_observations"]:
                    ended = self._receive(deadline=ack_deadline)
                    _require(ended.type == "ended" and ended.reason in (("model_limit", "wall_limit") if self.profile.live else ("model_limit",)))
                    self._finish_ended(ended, ack_deadline)
                    return
        except BaseException as error:
            self._latch(getattr(error, "code", "worker_failed"))
            self.begin_stop("session_fault")

    def _finish_ended(self, ended, deadline):
        self._worker_ended = True
        self._terminal_reason = ended.reason
        eof_deadline = min(deadline, self._stop_ns + 25_000_000_000)
        self._remaining()
        _require(self._transport.receive(deadline_ns=eof_deadline, max_body=4096) is None)
        self._remaining()
        self._full_eof = True
        self._validator.finish()
        with self._lock:
            self._state, self._outcome = "ended", "ended"
            self._boundary = self._command = None
        self._notice("ended", dict(reason=ended.reason, completed=self._completed))
        self.begin_stop("shutdown")

    def next_offer(self):
        with self._lock:
            return None if self._boundary is None or (self.profile.live and self._wall_deadline is not None and self._now() >= self._wall_deadline) else Boundary(self._boundary)

    def advance(self, boundary_id, permit, rgb):
        with self._changed:
            try:
                _require(type(boundary_id) is int and self._boundary is not None
                         and boundary_id == self._boundary.id and self._command is None and self._fault is None)
                boundary = self._boundary
                if self.profile.live and self._wall_deadline is not None and self._now() >= self._wall_deadline:
                    self._changed.notify_all()
                    return
                _require(self._now() < boundary.ack_deadline_ns, "deadline")
                if permit is not None:
                    if is_dataclass(permit):
                        permit = asdict(permit)
                    permit = _record(permit)
                    protocol._permit(permit.to_dict())
                    _require(self._permit is None and boundary_id <= protocol.limits()["model_observations"] - 8 and type(rgb) is bytes and len(rgb) == 12288)
                    _require(permit.incarnation == self.config.incarnation and permit.worker_session == self.config.worker_session
                             and permit.frame_sha256 == protocol.rgb_sha256(rgb) and self._now() < permit.deadline_ns)
                    _require(self._has_receipt(permit, "dispatching", "dispatch"), "journal_gap")
                    receipt = self._durable_receipts[permit.id][0]
                    _require(receipt.deadline_ns == permit.deadline_ns, "journal_gap")
                    self._permit, self._ordinal = permit, 0
                    action = "image"
                elif self._permit is not None:
                    _require(rgb is None)
                    self._ordinal += 1
                    action = "continue_image"
                else:
                    _require(rgb is None)
                    action = "black"
                fields = dict(last_observation_index=boundary_id - 1, next_observation_index=boundary_id,
                    action=action, permit=permit, dispatch_id=self._permit.dispatch_id if self._permit else None,
                    exposure_ordinal=self._ordinal)
                self._authorize(fields)
                self._command = (fields, rgb or b"")
                self._changed.notify_all()
            except BaseException as error:
                self._latch(getattr(error, "code", "protocol"))
                raise

    def begin_stop(self, reason):
        _require(reason in ("operator", "session_fault", "shutdown"))
        with self._changed:
            self._session_fault_stop = self._session_fault_stop or reason == "session_fault"
            if self._final_deadline is None:
                requested_real_ns = time.perf_counter_ns()
                try:
                    self._stop_ns = self._now()
                except protocol.ProtocolError:
                    self._fault = self._fault or "clock"
                self._final_deadline = requested_real_ns + 25_000_000_000
            self._stop.set()
            self._boundary = self._command = None
            if self._state != "ended":
                self._state = "stopping"
            self._changed.notify_all()
        if self._transport is not None:
            self._transport.begin_stop(reason, requested_ns=self._stop_ns, deadline_ns=self._final_deadline)

    def _remaining(self):
        _require(self._final_deadline is not None and time.perf_counter_ns() < self._final_deadline, "deadline")
        return (self._final_deadline - time.perf_counter_ns()) / 1e9

    def _final_source_check(self):
        from .native_windows import compare_bound_files
        self._remaining()
        started = self._now()
        compare_bound_files(self._bindings, deadline_ns=self._final_deadline)
        self._compare_controls(self._final_deadline)
        self._remaining()
        finished = self._now()
        _require(started <= finished <= self._stop_ns + 25_000_000_000, "deadline")
        subset = protocol.source_subset(self._protocol, self._bindings,
                                       self._prepared.protocol_sha256, self._prepared.bindings_sha256)
        return _record(dict(scope="prepared-source-lock-tool-cache/v1", started_ns=started,
            finished_ns=finished, file_count=subset.file_count, bindings_subset_sha256=subset.bindings_subset_sha256,
            all_match=True))

    def finish_close(self):
        self.begin_stop("shutdown")
        if self._transport is None:
            return self._finish_no_child()
        cleanup = None
        try:
            if self._thread is not None:
                self._thread.join(self._remaining())
                _require(not self._thread.is_alive(), "cleanup_failed")
            _require(self._transport is not None, "cleanup_failed")
            exits = self._transport.confirm_exit()
            self._remaining()
            with self._lock:
                _require(self._receipt_closed and self._reservation is None, "journal_gap")
            if self._writer is not None:
                self._writer.join(self._remaining())
                _require(not self._writer.is_alive() and self._outbox.empty()
                         and self._durable_ticket == self._submitted_ticket, "storage")
            _require(self._fault is None or not self._worker_ended, self._fault or "protocol")
            if self._events is not None:
                self._events.flush()
                os.fsync(self._events.fileno())
                self._events.close()
                self._events = None
            self._watchdog_stop.set()
            if self._watchdog is not None:
                self._watchdog.join(min(1, self._remaining()))
            self._remaining()
            receipts_terminal = all(receipt.terminal_ns is not None for receipt in self._receipt_validator.snapshot())
            if self._worker_ended and not receipts_terminal:
                self._latch("journal_gap")
            normal = (receipts_terminal and self._worker_ended and self._full_eof and (self._completed == protocol.limits()["model_observations"] or (self.profile.live and self._terminal_reason == "wall_limit"))
                      and exits.worker_exit_confirmed and exits.worker_exit_code == 0 and exits.job_empty_confirmed
                      and self._fault is None)
            source_check = self._final_source_check() if normal else None
            cleanup = self._transport.finish_close(evidence_files_closed=True)
            if self._fault is not None:
                combined = cleanup.to_dict()
                combined["first_fault"] = self._fault
                cleanup = protocol.validate_cleanup(combined)
            _require(cleanup.outcome == "confirmed", "cleanup_failed")
            if normal:
                _require(cleanup.requested_ns == self._stop_ns, "cleanup_failed")
            self._write_new(self.config.work_root / "cleanup.json", protocol.canonical_bytes(cleanup), self._final_deadline)
            if normal:
                self._seal(cleanup, source_check)
            elif self._fault is not None:
                self._write_failure(cleanup)
            self._remaining()
            with self._lock:
                self._state = "closed"
            return cleanup
        except BaseException as error:
            code = getattr(error, "code", "cleanup_failed")
            with self._lock:
                self._cleanup_fault = code
                self._outcome = self._outcome or "faulted"
            self._latch(self._fault or code)
            # Preserve held ownership if source/storage closure failed. An unknown
            # permitted probe identity cannot be represented by a false receipt.
            try:
                self._write_failure(cleanup)
            except BaseException:
                pass
            raise protocol.ProtocolError(code) from None

    def _finish_no_child(self):
        """Close real parent resources; not_created means no process was launched."""
        try:
            with self._changed:
                _require(self._reservation is None, "journal_gap")
                self._receipt_closed = True
                self._changed.notify_all()
            if self._writer is not None:
                self._writer.join(self._remaining())
                _require(not self._writer.is_alive(), "cleanup_failed")
            if self._events is not None:
                self._events.flush()
                os.fsync(self._events.fileno())
                self._events.close()
                self._events = None
            self._watchdog_stop.set()
            if self._watchdog is not None:
                self._watchdog.join(min(1, self._remaining()))
                _require(not self._watchdog.is_alive(), "cleanup_failed")
            self._remaining()
            try:
                finished = self._now()
            except protocol.ProtocolError:
                finished = None
            cleanup_fault = "clock" if self._stop_ns is None or finished is None else None
            cleanup = protocol.validate_cleanup(dict(schema="market-native-cleanup/v1",
                incarnation=self.config.incarnation, worker_session=self.config.worker_session,
                requested_ns=self._stop_ns, finished_ns=finished, worker_creation="not_created",
                worker=None, probe=None, worker_exit_code=None, probe_exit_code=None,
                worker_exit_confirmed=True, probe_exit_confirmed=True, job_empty_confirmed=True,
                ipc_handles_closed=True, process_handles_closed=True, job_handle_closed=True,
                root_lock_closed=True, evidence_files_closed=True, first_fault=self._fault,
                cleanup_fault=cleanup_fault, outcome="confirmed" if cleanup_fault is None else "unconfirmed"))
            self._cleanup_fault = cleanup_fault
            if self._attempted:
                self._write_new(self.config.work_root / "cleanup.json", protocol.canonical_bytes(cleanup), self._final_deadline)
                if self._fault is not None:
                    self._write_failure(cleanup)
            with self._lock:
                self._state = "closed" if cleanup.outcome == "confirmed" else "stopping"
                self._outcome = "faulted" if self._fault else "not_started"
            return cleanup
        except BaseException as error:
            code = getattr(error, "code", "cleanup_failed")
            self._cleanup_fault = code
            self._latch(self._fault or code)
            if self._attempted:
                try:
                    self._write_failure(None)
                except BaseException:
                    pass
            raise protocol.ProtocolError(code) from None

    def _write_failure(self, cleanup):
        value = dict(schema="market-native-failure/v1", incarnation=self.config.incarnation,
            worker_session=self.config.worker_session, first_fault=self._fault or "cleanup_failed",
            cleanup_fault=self._cleanup_fault, last_event_sequence=self._event_seq - 1 if self._event_seq else None,
            last_monitor_sequence=None, cleanup=cleanup)
        raw = protocol.canonical_bytes(value)
        _require(len(raw) <= 16384, "resource")
        self._write_new(self.config.work_root / "failure.json", raw, self._final_deadline)

    def _seal(self, cleanup, source_check):
        _require(all(receipt.terminal_ns is not None for receipt in self._receipt_validator.snapshot()), "journal_gap")
        self._remaining()
        root = self.config.work_root
        _ordinary(root)
        root_identity = (root.stat().st_dev, root.stat().st_ino)
        identities = {name: protocol._stat_identity(protocol._ordinary(root / name)) for name in (
            "protocol.json", "bindings.json", "header.json", "events.bin", "monitor.bin", "cleanup.json")}
        _require(protocol._bounded_file(root / "header.json", 2097152) == protocol.canonical_bytes(self._header), "source")
        _require(protocol._bounded_file(root / "cleanup.json", 16384) == protocol.canonical_bytes(cleanup), "source")
        if self.profile.live:
            # Online validators already checked each bounded record. Finalization
            # rehashes bytes in fixed chunks; full semantic replay is offline.
            def digest_file(name, cap):
                path = root / name
                before = protocol._ordinary(path)
                _require(before.st_size <= cap, "resource")
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    _require(protocol._stat_identity(os.fstat(stream.fileno())) == protocol._stat_identity(before), "source")
                    remaining = before.st_size
                    while remaining:
                        self._remaining()
                        raw = stream.read(min(1048576, remaining))
                        _require(raw, "source")
                        remaining -= len(raw)
                        digest.update(raw)
                    _require(not stream.read(1), "source")
                    _require(protocol._stat_identity(os.fstat(stream.fileno())) == protocol._stat_identity(before), "source")
                _require(protocol._stat_identity(protocol._ordinary(path)) == protocol._stat_identity(before), "source")
                return digest.hexdigest()
            events_digest = digest_file("events.bin", protocol.limits()["event_bytes"])
            _require(events_digest == self._event_digest.hexdigest(), "source")
            event_count, event_last = self._event_seq, self._event_sha
            monitor = self._transport.monitor_summary()
            monitor_digest = digest_file("monitor.bin", protocol.limits()["monitor_bytes"])
            _require(monitor_digest == monitor.sha256 and (root / "monitor.bin").stat().st_size == monitor.bytes, "source")
            monitor_count, monitor_last, peaks = monitor.records, monitor.chain_sha256, monitor.peaks
        else:
            with (root / "events.bin").open("rb") as stream:
                reader = protocol._HashReader(stream, protocol.limits()["event_bytes"])
                event_count = 0
                event_last = None
                for frame in protocol._event_iterator(reader):
                    self._remaining()
                    event_count += 1
                    event_last = frame.message.sha256
                events_digest = reader.digest.hexdigest()
            _require(events_digest == self._event_digest.hexdigest(), "source")
            with (root / "monitor.bin").open("rb") as stream:
                reader = protocol._HashReader(stream, protocol.limits()["monitor_bytes"])
                monitor_count = 0
                monitor_last = None
                peaks = dict(gap_ns=0, worker_peak_rss_bytes=0, probe_peak_rss_bytes=0, job_peak_commit_bytes=0, combined_output_bytes=0)
                for row in protocol._monitor_iterator(reader):
                    self._remaining()
                    monitor_count += 1
                    monitor_last = row.sha256
                    for key in peaks:
                        peaks[key] = max(peaks[key], row[key])
                monitor_digest = reader.digest.hexdigest()
        self._remaining()
        summary = self._validator.finish()
        final = dict(schema=protocol.schema("final"), status="complete", verification="integrity-only",
            incarnation=self.config.incarnation, worker_session=self.config.worker_session,
            protocol_sha256=self._prepared.protocol_sha256, bindings_sha256=self._prepared.bindings_sha256,
            header_sha256=protocol.canonical_sha256(self._header), event_records=event_count,
            events_sha256=events_digest, event_chain_sha256=event_last,
            monitor_records=monitor_count, monitor_sha256=monitor_digest,
            monitor_chain_sha256=monitor_last, cleanup_sha256=hashlib.sha256(protocol.canonical_bytes(cleanup)).hexdigest(),
            observations=summary.observations, model_ticks=summary.model_ticks,
            image_dispatches=summary.image_dispatches, processed_images=summary.processed_images,
            max_monitor_gap_ns=peaks["gap_ns"],
            peak_worker_rss_bytes=peaks["worker_peak_rss_bytes"],
            peak_probe_rss_bytes=peaks["probe_peak_rss_bytes"],
            peak_job_commit_bytes=peaks["job_peak_commit_bytes"],
            peak_output_bytes=peaks["combined_output_bytes"], source_unchanged=True,
            source_check=source_check, first_fault=None, cleanup_fault=None)
        if self.profile.live:
            final.update(terminal_reason=self._terminal_reason, status="partial" if self._terminal_reason == "wall_limit" else "complete")
        raw = protocol.canonical_bytes(protocol.validate_final(final))
        temporary = root / "final.json.tmp"
        temporary_identity = self._write_new(temporary, raw, self._final_deadline)
        _ordinary(root)
        _require((root.stat().st_dev, root.stat().st_ino) == root_identity and not (root / "final.json").exists(), "source")
        for name, identity in identities.items():
            _require(protocol._stat_identity(protocol._ordinary(root / name)) == identity, "source")
        _require(protocol._stat_identity(protocol._ordinary(temporary)) == temporary_identity, "source")
        self._remaining()
        temporary.rename(root / "final.json")
