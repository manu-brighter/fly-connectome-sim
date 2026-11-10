"""Bounded parent-session software evidence; no production native release."""

import importlib
import hashlib
import queue
import threading
import time

import pytest

pytestmark = pytest.mark.usefixtures("native_software_paths")

from test_native_protocol import INCARNATION, SESSION, DIGEST
from test_native_evidence import receipt_fixture
from test_native_evidence import prepared_fixtures, monitor_fixture, cleanup_fixture, write_complete_fixture
from test_native_protocol import header_fixture, full_protocol, wire_receipt_ns
from test_native_worker import FakeEngine


def api():
    return importlib.import_module("market.native_session")


def session(tmp_path, clock):
    return api().NativeSession(api().NativeConfig(INCARNATION, SESSION, DIGEST, tmp_path / "native"), clock)


def entry(receipt, operation="admit", notice_seq=None):
    return dict(receipt=receipt, cause=dict(operation=operation, target_id=receipt["id"] if isinstance(receipt, dict) else receipt.id,
                                          notice_seq=notice_seq, read_pass=0))


def test_constructor_is_declaration_only_and_snapshot_detached(tmp_path, clock):
    value = session(tmp_path, clock)
    snap = value.snapshot()
    assert snap.state == "prepared" and snap.free_observations == 40
    assert snap.latest is None and snap.boundary is None
    assert not (tmp_path / "native").exists()
    with pytest.raises((AttributeError, TypeError)):
        snap.state = "running"
    assert value.poll() == ()


@pytest.mark.parametrize("allowed", [False, 1, None, "yes"])
def test_production_start_requires_literal_true_before_any_launch(tmp_path, clock, allowed):
    value = session(tmp_path, clock)
    with pytest.raises(ValueError):
        value.start({}, allowed)
    assert not (tmp_path / "native").exists()


def test_receipt_capacity_is_reserved_before_mutation_and_publish_is_nonblocking(tmp_path, clock):
    value = session(tmp_path, clock)
    ticket = value.reserve_receipts()
    assert ticket.ticket == 1
    with pytest.raises(ValueError):
        value.reserve_receipts()
    value.publish_receipts(ticket, ())
    assert value.receipt_progress().submitted_ticket == 1
    assert value.receipt_progress().durable_ticket == 1
    value.finish_receipts()
    assert value.reserve_receipts() is None


def test_receipt_publication_validates_original_revisions_and_three_entry_cap(tmp_path, clock):
    value = session(tmp_path, clock)
    ticket = value.reserve_receipts()
    receipt = receipt_fixture()
    with pytest.raises(ValueError, match="journal_gap"):
        value.publish_receipts(ticket, (entry(dict(receipt, revision=2)),))
    assert value.snapshot().fault == "journal_gap"


def test_receipt_writer_acknowledges_only_after_actual_fsync(tmp_path, clock, monkeypatch):
    value = session(tmp_path, clock)
    gate, entered = threading.Event(), threading.Event()
    original = api().os.fsync

    def blocked(fd):
        entered.set()
        assert gate.wait(2)
        original(fd)

    value._open_test_evidence()
    monkeypatch.setattr(api().os, "fsync", blocked)
    ticket = value.reserve_receipts()
    value.publish_receipts(ticket, (entry(receipt_fixture()),))
    assert entered.wait(1)
    assert value.receipt_progress().durable_ticket == 0
    assert value.snapshot().completed_observations == 0
    gate.set()
    deadline = time.perf_counter() + 2
    while value.receipt_progress().durable_ticket != 1 and time.perf_counter() < deadline:
        time.sleep(0.005)
    assert value.receipt_progress().durable_ticket == 1
    value.finish_receipts()
    value._close_test_evidence()


def test_stale_boundary_faults_without_retry(tmp_path, clock):
    value = session(tmp_path, clock)
    with pytest.raises(ValueError):
        value.advance(0, None, None)
    assert value.snapshot().fault == "protocol"


def test_notice_overflow_preserves_eight_notices_and_one_fault(tmp_path, clock):
    value = session(tmp_path, clock)
    for _ in range(9):
        value._notice("fault", dict(code="protocol", cleanup_fault=None))
    assert value.snapshot().fault == "resource"
    assert len(value.poll()) == 8
    assert value.poll()[0].type == "fault"
    assert value.poll() == ()


def test_advance_reserves_issued_budget_atomically_before_transport(tmp_path, clock):
    value = session(tmp_path, clock)
    value._state = "running"
    value._issued = value._completed = 1
    value._latest = api().protocol.FrozenRecord(dict(observation_index=0, input_kind="black", image_id=None,
        frame_sha256=api().protocol.BLACK_SHA256, wall_completion_ns=clock.ns, model_end_tick=5000,
        group_spikes={g: 0 for g in api().protocol.GROUPS}, group_rates_hz={g: 0.0 for g in api().protocol.GROUPS}))
    value._boundary = api().protocol.FrozenRecord(dict(id=1, next_observation_index=1,
        issued_observations=1, completed_observations=1, active_dispatch_id=None,
        unissued_active_observations=0, free_observations=39, ack_deadline_ns=clock.ns + 100000))
    value.advance(1, None, None)
    snap = value.snapshot()
    assert snap.issued_observations == 2 and snap.in_flight_index == 1
    assert snap.boundary is None and snap.free_observations == 38


def test_processed_receipt_uses_original_completed_detail_and_exact_complete_time(tmp_path, clock):
    value = session(tmp_path, clock)
    receipt = dict(receipt_fixture(), revision=6, status="processed", detail="completed",
        frame_sha256=DIGEST, preprocessing_version="market-rgb64/v1", worker_session=SESSION,
        dispatch_id="40000000-0000-0000-0000-000000000004", dispatched_ns=2, started_ns=3,
        first_observation_index=1, completed_ns=10, terminal_ns=11)
    cause = api().protocol.FrozenRecord(entry(receipt, "complete", 9)["cause"])
    value._durable_receipts[receipt["id"]] = (api().protocol.FrozenRecord(receipt), cause, 6)
    complete = api().protocol.FrozenRecord({key: receipt[key] for key in (
        "id", "incarnation", "dispatch_id", "worker_session", "frame_sha256", "completed_ns")})
    assert value._has_receipt(complete, "processed", "complete", 9)
    bad = complete.to_dict()
    bad["completed_ns"] = 9
    assert not value._has_receipt(api().protocol.FrozenRecord(bad), "processed", "complete", 9)


def test_receipt_batch_supports_actual_d1_dataclass_without_losing_fields(tmp_path, clock):
    from market.image_admission import Receipt
    value = session(tmp_path, clock)
    value._open_test_evidence()
    ticket = value.reserve_receipts()
    value.publish_receipts(ticket, (entry(Receipt(**receipt_fixture())),))
    value.finish_receipts()
    value._close_test_evidence()
    with (value.config.work_root / "events.bin").open("rb") as stream:
        rows = api().protocol.read_events(stream)
    assert rows[0].message.payload.receipt.to_dict() == receipt_fixture()


@importlib.import_module("market.native_protocol").owned
class FakeTransport:
    """Explicit software transport/cleanup evidence, no OS-process assertion."""

    def __init__(self, session, clock, *, mutate=None, eof_at=None):
        self.profile = session.profile
        self.session, self.clock = session, clock
        self.incoming, self.commands = queue.Queue(maxsize=2), queue.Queue(maxsize=1)
        self.seq = 0
        self.identity = api().protocol.FrozenRecord(cleanup_fixture()["worker"])
        self.probe = api().protocol.FrozenRecord(cleanup_fixture()["probe"])
        self.engine = FakeEngine(header_fixture())
        self.worker = self.worker_thread = None
        self.nonce = None
        self.mutate = mutate
        self.eof_at = eof_at
        self.stopped = False
        self.monitor = []
        self.sample(initial=True)

    def sample(self, initial=False):
        row = monitor_fixture()
        row.update(schema=api().protocol.schema("monitor"), sequence=len(self.monitor), previous_sha256=self.monitor[-1].sha256 if self.monitor else "0" * 64,
                   sample_ns=self.clock.sample().monotonic_ns, gap_ns=0,
                   worker_rss_bytes=100 if initial else 0, job_process_count=1 if initial else 0,
                   job_commit_bytes=300 if initial else 0, combined_output_bytes=5000000, evidence_bytes=5000000)
        if self.monitor:
            row["gap_ns"] = row["sample_ns"] - self.monitor[-1].sample_ns
        row.pop("sha256")
        self.monitor.append(api().protocol.make_monitor(row))

    def emit(self, kind, fields, binary=b"", *, deadline_ns=None):
        if self.clock.sample().monotonic_ns - self.monitor[-1].sample_ns >= 100000000:
            self.sample(initial=True)
        message = dict(schema=api().protocol.schema("ipc"), type=kind, seq=self.seq,
            incarnation=INCARNATION, worker_session=SESSION,
            protocol_sha256=self.session.config.protocol_sha256, launch_nonce=self.nonce, **fields)
        self.seq += 1
        if self.mutate:
            self.mutate(message)
        if kind == "observation" and message["observation_index"] == self.eof_at:
            self.incoming.put(None)
            raise ValueError("finite EOF injection")
        self.incoming.put(api().protocol.Frame(api().protocol.FrozenRecord(api().protocol._plain(message)), binary))

    def send(self, message, binary=b"", *, deadline_ns):
        kind = message["type"]
        self.nonce = message["launch_nonce"]
        bindings = self.session._bindings
        if kind == "hello":
            self.emit("hello", dict(bindings_sha256=self.session._prepared.bindings_sha256,
                                   worker=self.identity, worker_clock=self.clock.describe()))
        elif kind == "challenge":
            self.emit("clock", dict(challenge_index=message["challenge_index"],
                                    p0_ns=message["p0_ns"], child_ns=self.clock.sample().monotonic_ns))
        elif kind == "initialize":
            probe = bindings.compiler_probe
            self.emit("probe_request", dict(compiler_sha256=probe.executable_sha256,
                argv_sha256=api().protocol.canonical_sha256(probe.argv), environment_sha256=probe.environment_sha256))
        elif kind == "probe_allow":
            def startup_tail():
                started = self.clock.sample().monotonic_ns
                self.emit("probe_started", dict(process=self.probe, allowed_ns=message["allowed_ns"], started_ns=started))
                self.emit("probe_finished", dict(process=self.probe, started_ns=started,
                    completed_ns=self.clock.sample().monotonic_ns, exit_code=0, stdout_bytes=7, stderr_bytes=0,
                    stdout_sha256=hashlib.sha256(b"0.16.0\n").hexdigest(), stderr_sha256=hashlib.sha256(b"").hexdigest(), version="0.16.0"))
                header = header_fixture()
                self.emit("static_header", dict(header=header))
                self.emit("ready", dict(bindings_sha256=self.session._prepared.bindings_sha256,
                    header_sha256=api().protocol.canonical_sha256(header), engine_identity_sha256=header["engine_identity"]["sha256"],
                    build_sha256=api().protocol.canonical_sha256(header["engine_identity"]["model_provenance"]["build"]),
                    graph_nodes=166700, graph_edges=25582938, observation_index=0, model_tick=0,
                    ready_ns=self.clock.sample().monotonic_ns))
            threading.Thread(target=startup_tail, daemon=True).start()
        else:
            self.commands.put((message, binary))
            if kind == "release":
                self.worker = importlib.import_module("market.native_worker")._Worker(
                    self.engine, header_fixture(), self.clock, self.emit,
                    lambda **kwargs: self.commands.get(timeout=1), wall_deadline_ns=self.session._wall_deadline, profile=self.profile)

                def run():
                    try:
                        self.worker.run()
                        self.incoming.put(None)
                    except BaseException:
                        if self.eof_at is None:
                            self.incoming.put(None)
                self.worker_thread = threading.Thread(target=run, daemon=True)
                self.worker_thread.start()

    def receive(self, *, deadline_ns, max_body):
        result = self.incoming.get(timeout=max(0.001, (deadline_ns - self.clock.sample().monotonic_ns) / 1e9))
        if result is None:
            self.eof_deadline = deadline_ns
        return result

    def permit_probe(self, request):
        return self.clock.sample().monotonic_ns

    def accept_probe_started(self, message):
        assert message.process == self.probe

    def accept_probe_finished(self, message):
        assert message.process == self.probe

    def monitor_summary(self):
        raw = b"".join(api().protocol.encode_monitor(row) for row in self.monitor)
        return api().protocol.FrozenRecord(dict(records=len(self.monitor), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
            chain_sha256=self.monitor[-1].sha256, peaks={key:max(row[key] for row in self.monitor) for key in ("gap_ns", "worker_peak_rss_bytes", "probe_peak_rss_bytes", "job_peak_commit_bytes", "combined_output_bytes")}))

    def begin_stop(self, reason, *, requested_ns=None, deadline_ns=None):
        self.stopped = True
        if requested_ns is not None:
            assert requested_ns == self.session._stop_ns
        if deadline_ns is not None:
            assert deadline_ns == self.session._final_deadline

    def confirm_exit(self):
        if self.worker_thread:
            self.worker_thread.join(1)
        return api().protocol.FrozenRecord(dict(worker_exit_confirmed=True, worker_exit_code=0, job_empty_confirmed=True))

    def finish_close(self, *, evidence_files_closed):
        self.sample()
        root = self.session.config.work_root
        with (root / "monitor.bin").open("xb") as stream:
            for row in self.monitor:
                stream.write(api().protocol.encode_monitor(row))
        receipt = cleanup_fixture()
        receipt.update(requested_ns=self.session._stop_ns, finished_ns=self.clock.sample().monotonic_ns,
                       evidence_files_closed=evidence_files_closed)
        return api().protocol.validate_cleanup(receipt)


def software_session(tmp_path, *, mutate=None, eof_at=None, bound_fixture=False, profile=None, wall_ns=None):
    clock = api().SystemClock()
    declaration, bindings = prepared_fixtures(tmp_path, local_files=True)
    if profile is not None:
        declaration.update(schema=api().protocol.schema("protocol"), proof=profile.name, constants=api().protocol.limits())
        bindings["schema"] = api().protocol.schema("bindings")
        extra = "market/native_price.py"
        declaration["application_sources"][extra] = DIGEST
        bindings["files"][extra] = dict(bindings["files"]["market/native_worker.py"], path=bindings["files"]["market/native_worker.py"]["path"].replace("native_worker.py", "native_price.py"))
        bindings["protocol_sha256"] = api().protocol.canonical_sha256(declaration)
    fixture_source = None
    if bound_fixture:
        key = "market/native_worker.py"
        fixture_source = tmp_path / "project" / key
        fixture_source.parent.mkdir(parents=True, exist_ok=True)
        fixture_source.write_bytes(b"# private bound application-source fixture\n")
        bound = api()._binding(fixture_source, 1048576, time.perf_counter_ns() + 1000000000)
        declaration["application_sources"][key] = bound["sha256"]
        bindings["files"] = {key: bound, **{name: binding for name, binding in bindings["files"].items() if name != key}}
        bindings["protocol_sha256"] = api().protocol.canonical_sha256(declaration)
    declaration_raw = api().protocol.canonical_bytes(declaration)
    value = api().NativeSession(api().NativeConfig(INCARNATION, SESSION,
        hashlib.sha256(declaration_raw).hexdigest(), tmp_path / "native",
        **(dict(profile=profile.name, duration_minutes=profile.duration_minutes, max_observations=profile.max_observations) if profile else {})), clock)
    value.config.work_root.mkdir()
    bindings["work_root"] = str(value.config.work_root)
    bindings["environment"]["TMP"] = str(value.config.work_root / "scratch")
    bindings["environment"]["TEMP"] = str(value.config.work_root / "scratch")
    bindings["compiler_probe"]["environment_sha256"] = api().protocol.canonical_sha256(bindings["environment"])
    value._protocol = api().protocol.validate_protocol(declaration)
    value._bindings = api().protocol.validate_bindings(bindings, declaration)
    value._protocol_raw = declaration_raw
    value._bindings_raw = api().protocol.canonical_bytes(value._bindings)
    for name, raw in (("protocol.json", declaration_raw), ("bindings.json", value._bindings_raw)):
        (value.config.work_root / name).write_bytes(raw)
    value._prepared = api().protocol.FrozenRecord(dict(schema=api().protocol.schema("prepared"),
        protocol_sha256=value.config.protocol_sha256, bindings_sha256=hashlib.sha256(value._bindings_raw).hexdigest(),
        incarnation=INCARNATION, worker_session=SESSION))
    value._open_evidence()
    value._event("binding", dict(protocol_sha256=value.config.protocol_sha256, bindings_sha256=value._prepared.bindings_sha256))
    value._transport = FakeTransport(value, clock, mutate=mutate, eof_at=eof_at)
    now = clock.sample().monotonic_ns
    value._wall_deadline, value._startup_deadline = now + (wall_ns if wall_ns is not None else api().protocol.limits()["wall_ns"]), now + 180000000000
    value._nonce = "b" * 64
    value._state = "starting"
    value._thread = threading.Thread(target=value._run, daemon=True)
    value._thread.start()
    value.fixture_source = fixture_source
    return value


def drive_software(value, image_at=None):
    receipt = None
    started = time.perf_counter()
    while value._thread.is_alive() and time.perf_counter() - started < 12:
        for notice in value.poll():
            if notice.type == "boundary":
                boundary = notice.payload
                if boundary.id == image_at:
                    now = value.clock.sample().monotonic_ns
                    pixels = bytes([9]) * 12288
                    receipt = dict(receipt_fixture(), accepted_ns=now, deadline_ns=now + 300000000000,
                        decode_deadline_ns=now + 10000000000, moderation_deadline_ns=now + 60000000000)
                    transitions = [(receipt.copy(), "admit"),
                        (dict(receipt, revision=2, detail="awaiting_approval", frame_sha256=api().protocol.rgb_sha256(pixels),
                              preprocessing_version="market-rgb64/v1"), "decoded")]
                    receipt = dict(transitions[-1][0], revision=3, status="queued", detail="ready")
                    transitions.append((receipt.copy(), "moderate"))
                    ticket = value.reserve_receipts()
                    value.publish_receipts(ticket, tuple(entry(r, op) for r, op in transitions))
                    receipt.update(revision=4, detail="dispatching", worker_session=SESSION,
                        dispatch_id="40000000-0000-0000-0000-000000000004", dispatched_ns=value.clock.sample().monotonic_ns)
                    ticket = value.reserve_receipts()
                    value.publish_receipts(ticket, (entry(receipt.copy(), "dispatch", notice.notice_seq),))
                    while value.receipt_progress().durable_ticket < ticket.ticket:
                        time.sleep(0.001)
                    permit = {key: receipt[key] for key in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256", "deadline_ns")}
                    value.advance(boundary.id, dict(permit, exposure_observations=8), pixels)
                else:
                    value.advance(boundary.id, None, None)
            elif notice.type in ("start", "complete"):
                if notice.type == "start":
                    receipt.update(revision=5, status="processing", detail="processing",
                        started_ns=notice.payload.started_ns, first_observation_index=notice.payload.first_observation_index)
                else:
                    receipt.update(revision=6, status="processed", detail="completed",
                        completed_ns=notice.payload.completed_ns, terminal_ns=value.clock.sample().monotonic_ns)
                ticket = value.reserve_receipts()
                value.publish_receipts(ticket, (entry(receipt.copy(), "started" if notice.type == "start" else "complete", notice.notice_seq),))
        time.sleep(0.001)
    value._thread.join(1)
    assert not value._thread.is_alive()
    return receipt


@pytest.mark.parametrize("image_at", [None, 1, 32])
def test_parent_connects_real_worker_loop_with_finite_fake_transport_and_exact_receipts(tmp_path, image_at):
    value = software_session(tmp_path)
    receipt = drive_software(value, image_at)
    assert value.snapshot().fault is None
    assert value.snapshot().state == "ended"
    assert value.snapshot().completed_observations == 40
    assert len(value._transport.engine.frames) == 40
    if image_at is not None:
        assert receipt["status"] == "processed"
    value.finish_receipts()
    value._close_test_evidence()
    with (value.config.work_root / "events.bin").open("rb") as stream:
        rows = api().protocol.read_events(stream)
    assert sum(row.message.kind == "wire" and row.message.payload.message.type == "observation" for row in rows) == 40
    if image_at is not None:
        assert sum(row.message.kind == "receipt" for row in rows) == 6
    wire_clocks = [row.message for row in rows if row.message.kind == "wire" and row.message.payload.message.type == "clock"]
    brackets = [row.message for row in rows if row.message.kind == "clock_bracket"]
    assert [row.payload.p1_ns for row in brackets] == [row.recorded_ns for row in wire_clocks]
    ended = next(row.message for row in rows if row.message.kind == "wire" and row.message.payload.message.type == "ended")
    assert value._stop_ns == ended.recorded_ns


def test_parent_eof39_is_incomplete_and_never_seals(tmp_path):
    value = software_session(tmp_path, eof_at=39)
    drive_software(value)
    assert value.snapshot().fault is not None
    assert value.snapshot().completed_observations == 39
    assert not (value.config.work_root / "final.json").exists()
    value.finish_receipts()
    value._close_test_evidence()


@pytest.mark.parametrize("payload", [dict(type="made_up"), dict(notice_seq=0, incarnation=INCARNATION,
    worker_session=SESSION, protocol_sha256=DIGEST, type="ready", payload={})])
def test_public_notice_dto_rejects_arbitrary_variant_or_missing_fields(payload):
    with pytest.raises(ValueError):
        api().NativeNotice(payload)


def test_public_boundary_dto_enforces_arithmetic():
    with pytest.raises(ValueError):
        api().Boundary(dict(id=1, next_observation_index=1, issued_observations=1,
            completed_observations=1, active_dispatch_id=None, unissued_active_observations=0,
            free_observations=40, ack_deadline_ns=1))


def test_final_source_mutation_refuses_seal_preserves_real_receipts(tmp_path, monkeypatch):
    value = software_session(tmp_path, bound_fixture=True)
    receipt = drive_software(value, 32)
    assert receipt["status"] == "processed"
    value.finish_receipts()
    # This real source file was bound before readiness and is now actually
    # changed. Confirm the final check rejects it before any synthetic member.
    value.fixture_source.write_bytes(b"# changed after readiness\n")
    from market import native_windows
    original = native_windows._ordinary
    checked = []
    def record_path(path):
        checked.append(str(path))
        return original(path)
    monkeypatch.setattr(native_windows, "_ordinary", record_path)
    with pytest.raises(ValueError, match="source"):
        value.finish_close()
    assert checked == [str(value.fixture_source)]
    assert not (value.config.work_root / "final.json").exists()
    with (value.config.work_root / "events.bin").open("rb") as stream:
        rows = api().protocol.read_events(stream)
    actual = [r.message.payload.receipt for r in rows if r.message.kind == "receipt"]
    assert actual[-1].status == "processed"


def test_receipt_capacity_includes_batch_being_fsynced_and_reservation(tmp_path, clock, monkeypatch):
    value = session(tmp_path, clock)
    value._open_test_evidence()
    gate, entered = threading.Event(), threading.Event()
    original = api().os.fsync
    def blocked(fd):
        entered.set()
        assert gate.wait(2)
        original(fd)
    monkeypatch.setattr(api().os, "fsync", blocked)
    ticket = value.reserve_receipts()
    value.publish_receipts(ticket, (entry(receipt_fixture()),))
    assert entered.wait(1)
    for _ in range(31):
        ticket = value.reserve_receipts()
        assert ticket is not None
        value.publish_receipts(ticket, ())
    assert value.receipt_progress().queued_batches == 32
    assert value.reserve_receipts() is None
    assert value.snapshot().fault == "storage"
    gate.set()
    value.finish_receipts()
    value._close_test_evidence()


def test_submitted_receipt_watermark_does_not_advance_on_reservation(tmp_path, clock):
    value = session(tmp_path, clock)
    ticket = value.reserve_receipts()
    assert value.receipt_progress().submitted_ticket == 0
    value.publish_receipts(ticket, ())
    assert value.receipt_progress().submitted_ticket == 1


def test_final_source_check_rehashes_exact_subset_and_controls_under_one_budget(tmp_path, clock):
    value = session(tmp_path, clock)
    value.config.work_root.mkdir()
    source = tmp_path / "bound.py"
    source.write_bytes(b"# source fixture\n")
    binding = api()._binding(source, 1048576, time.perf_counter_ns() + 1000000000)
    names = ("one.py", *api().protocol.TOOL_KEYS, *api().protocol.DEPENDENCY_KEYS)
    value._protocol = dict(preserved_sources={"one.py": binding["sha256"]}, application_sources={}, lock_sources={})
    files = {name: binding.copy() for name in names}
    # These deliberately nonexistent large runtime files must not be read again.
    files.update({name: dict(path=str(tmp_path / (name + ".absent"))) for name in api().protocol.RUNTIME_KEYS})
    value._bindings = dict(files=files)
    value._protocol_raw, value._bindings_raw = b"protocol fixture", b"bindings fixture"
    for name, raw in (("protocol.json", value._protocol_raw), ("bindings.json", value._bindings_raw)):
        (value.config.work_root / name).write_bytes(raw)
    value._prepared = api().PreparedNative(dict(schema="market-native-prepared/v1", protocol_sha256=DIGEST,
        bindings_sha256=DIGEST, incarnation=INCARNATION, worker_session=SESSION))
    value.begin_stop("shutdown")
    check = value._final_source_check()
    assert check.file_count == len(names) + 2 and check.all_match is True
    expected = api().protocol.source_subset(value._protocol, value._bindings, DIGEST, DIGEST)
    assert check.bindings_subset_sha256 == expected.bindings_subset_sha256
    source.write_bytes(b"# changed source\n")
    with pytest.raises(ValueError):
        value._final_source_check()


def test_changed_prepared_control_bytes_fail_before_transport_creation(tmp_path, clock, monkeypatch):
    from market import native_windows
    value = session(tmp_path, clock)
    root = value.config.work_root
    root.mkdir()
    value._protocol_raw, value._bindings_raw = b"fixed protocol", b"fixed bindings"
    (root / "protocol.json").write_bytes(b"changed protocol")
    (root / "bindings.json").write_bytes(value._bindings_raw)
    value._prepared = api().PreparedNative(dict(schema="market-native-prepared/v1", protocol_sha256=DIGEST,
        bindings_sha256=DIGEST, incarnation=INCARNATION, worker_session=SESSION))
    def forbidden(*args, **kwargs):
        pytest.fail("transport construction before control verification")
    monkeypatch.setattr(native_windows, "OwnedNativeChild", forbidden)
    with pytest.raises(ValueError, match="source"):
        value.start(value._prepared, True)
    with pytest.raises(ValueError):
        value.start(value._prepared, True)
    assert not (root / "events.bin").exists()


def test_receipt_batch_cannot_link_started_to_wrong_notice(tmp_path, clock):
    value = session(tmp_path, clock)
    receipt = dict(receipt_fixture(), revision=5, status="processing", detail="processing",
        frame_sha256=DIGEST, preprocessing_version="market-rgb64/v1", worker_session=SESSION,
        dispatch_id="40000000-0000-0000-0000-000000000004", dispatched_ns=2,
        started_ns=3, first_observation_index=1)
    cause = api().protocol.FrozenRecord(entry(receipt, "started", 9)["cause"])
    value._durable_receipts[receipt["id"]] = (api().protocol.FrozenRecord(receipt), cause, 5)
    start = api().protocol.FrozenRecord({key: receipt[key] for key in (
        "id", "incarnation", "dispatch_id", "worker_session", "frame_sha256", "started_ns", "first_observation_index")})
    assert value._has_receipt(start, "processing", "started", 9)
    assert not value._has_receipt(start, "processing", "started", 8)


def test_parent_snapshot_remains_nonblocking_while_fake_observe_is_blocked(tmp_path):
    value = software_session(tmp_path)
    # Hold before the next native-style call; the worker is the only blocked
    # computation owner. Snapshot/poll use neither its call nor its transport.
    entered, release = threading.Event(), threading.Event()
    original = value._transport.engine.observe
    def blocked(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        return original(*args, **kwargs)
    value._transport.engine.observe = blocked
    assert entered.wait(1)
    started = time.perf_counter()
    snap = value.snapshot()
    value.poll()
    assert time.perf_counter() - started < 0.1
    assert snap.in_flight_index == 0
    release.set()
    drive_software(value)
    value.finish_receipts()
    value._close_test_evidence()


def test_receipt_storage_watchdog_fences_even_while_fsync_is_blocked(tmp_path, clock, monkeypatch):
    value = session(tmp_path, clock)
    value._open_test_evidence()
    gate, entered = threading.Event(), threading.Event()
    original = api().os.fsync
    def blocked(fd):
        entered.set()
        assert gate.wait(2)
        original(fd)
    monkeypatch.setattr(api().os, "fsync", blocked)
    ticket = value.reserve_receipts()
    value.publish_receipts(ticket, (entry(receipt_fixture()),))
    assert entered.wait(1)
    value._storage_started_ns = time.perf_counter_ns() - 5000000001
    until = time.perf_counter() + 0.5
    while value.snapshot().fault is None and time.perf_counter() < until:
        time.sleep(0.002)
    assert value.snapshot().fault == "storage"
    assert value.receipt_progress().durable_ticket == 0
    gate.set()
    value.finish_receipts()
    value._close_test_evidence()


def test_readiness_publishes_header_identity_together_only_after_ready(tmp_path):
    gate, waiting = threading.Event(), threading.Event()
    def hold_ready(message):
        if message["type"] == "ready":
            waiting.set()
            assert gate.wait(2)
    value = software_session(tmp_path, mutate=hold_ready)
    assert waiting.wait(1)
    # Wait for the actual static-header journal event, not a guessed sleep.
    until = time.perf_counter() + 1
    while value._header is None and getattr(value, "_pending_header", None) is None and time.perf_counter() < until:
        time.sleep(0.002)
    snap = value.snapshot()
    assert snap.state == "starting" and snap.header_sha256 is None and snap.engine_identity_sha256 is None
    gate.set()
    drive_software(value)
    value.finish_receipts()
    value._close_test_evidence()


def test_no_seal_with_cleanup_epoch_different_from_exact_ended_receipt(tmp_path, clock):
    value = session(tmp_path, clock)
    value.config.work_root.mkdir()
    value._worker_ended = value._full_eof = True
    value._completed = 40
    value._receipt_closed = True
    value.begin_stop("shutdown")
    from types import SimpleNamespace
    receipt = cleanup_fixture()
    receipt.update(requested_ns=value._stop_ns + 1, finished_ns=value._stop_ns + 100)
    value._transport = SimpleNamespace(begin_stop=lambda reason, **kwargs: None,
        confirm_exit=lambda: SimpleNamespace(worker_exit_confirmed=True, worker_exit_code=0, job_empty_confirmed=True),
        finish_close=lambda **kwargs: api().protocol.validate_cleanup(receipt))
    value._final_source_check = lambda: None
    sealed = []
    value._seal = lambda *args: sealed.append(args)
    with pytest.raises(ValueError, match="cleanup_failed"):
        value.finish_close()
    assert sealed == []


def analytical_seal_session(tmp_path):
    # Pure publication fixture: SourceCheck is analytical Task1 evidence, not an
    # execution of the source comparison or Win32 owner. No native claim follows.
    final = write_complete_fixture(tmp_path)
    (tmp_path / "final.json").unlink()
    value = api().NativeSession(api().NativeConfig(INCARNATION, SESSION, final["protocol_sha256"], tmp_path), api().SystemClock())
    value._header = api().protocol.validate_header(header_fixture())
    value._prepared = api().PreparedNative(dict(schema="market-native-prepared/v1",
        protocol_sha256=final["protocol_sha256"], bindings_sha256=final["bindings_sha256"],
        incarnation=INCARNATION, worker_session=SESSION))
    value._final_deadline = time.perf_counter_ns() + 25000000000
    value._event_digest = hashlib.sha256((tmp_path / "events.bin").read_bytes())
    for direction, message, binary in full_protocol():
        value._validator.accept(message, direction, binary, receipt_ns=wire_receipt_ns(message))
    return value, api().protocol.FrozenRecord(final["source_check"])


def test_closed_analytical_seal_is_inspectable_without_engine_or_writes_by_inspector(tmp_path):
    value, source_check = analytical_seal_session(tmp_path)
    value._seal(api().protocol.FrozenRecord(cleanup_fixture()), source_check)
    assert api().protocol.inspect_evidence(tmp_path).status == "complete"


def test_seal_refuses_changed_evidence_identity_after_verified_final_temp(tmp_path, monkeypatch):
    value, source_check = analytical_seal_session(tmp_path)
    original = value._write_new
    def change_after_temp(path, raw, deadline):
        original(path, raw, deadline)
        if path.name == "final.json.tmp":
            with (tmp_path / "events.bin").open("ab") as stream:
                stream.write(b"x")
    monkeypatch.setattr(value, "_write_new", change_after_temp)
    with pytest.raises(ValueError, match="source"):
        value._seal(api().protocol.FrozenRecord(cleanup_fixture()), source_check)
    assert not (tmp_path / "final.json").exists()


def test_confirmed_cleanup_keeps_real_parent_fault_and_writes_failure_record(tmp_path):
    value = software_session(tmp_path, eof_at=39)
    drive_software(value)
    fault = value.snapshot().fault
    value.finish_receipts()
    cleanup = value.finish_close()
    assert cleanup.outcome == "confirmed" and cleanup.first_fault == fault
    failure = api().protocol.parse_json((value.config.work_root / "failure.json").read_bytes(), byte_limit=16384)
    assert failure["first_fault"] == fault and failure["cleanup"]["first_fault"] == fault


@pytest.mark.parametrize("operation", ["stop", "snapshot", "status"])
def test_emergency_terminal_batch_has_separate_single_nonblocking_capacity(tmp_path, clock, monkeypatch, operation):
    value = session(tmp_path, clock)
    value._open_test_evidence()
    first = receipt_fixture()
    ticket = value.reserve_receipts()
    value.publish_receipts(ticket, (entry(first),))
    until = time.perf_counter() + 1
    while value.receipt_progress().durable_ticket != 1 and time.perf_counter() < until:
        time.sleep(0.001)
    gate, entered = threading.Event(), threading.Event()
    original = api().os.fsync
    def blocked(fd):
        entered.set()
        assert gate.wait(2)
        original(fd)
    monkeypatch.setattr(api().os, "fsync", blocked)
    value._latch("storage")
    terminal = dict(first, revision=2, status="rejected", detail="worker_failed", terminal_ns=clock.ns)
    value.publish_receipts(None, (entry(terminal, operation),))
    assert entered.wait(1)
    progress = value.receipt_progress()
    assert progress.emergency_pending and progress.queued_batches == 0
    assert progress.durable_ticket == 1
    assert value.reserve_receipts() is None
    with pytest.raises(ValueError):
        value.publish_receipts(None, ())
    gate.set()
    value.finish_receipts()
    value._close_test_evidence()
    assert not value.receipt_progress().emergency_pending
    with (value.config.work_root / "events.bin").open("rb") as stream:
        rows = api().protocol.read_events(stream)
    assert rows[-1].message.payload.receipt.detail == "worker_failed"


@pytest.mark.parametrize("case", ["healthy", "live", "wrong_cause", "three"])
def test_emergency_channel_rejects_normal_or_nonterminal_publication(tmp_path, clock, case):
    value = session(tmp_path, clock)
    receipt = receipt_fixture()
    if case != "healthy":
        value._latch("storage")
    receipt = dict(receipt, status="rejected", detail="worker_failed", terminal_ns=clock.ns)
    if case == "live":
        receipt = receipt_fixture()
    entries = (entry(receipt, "admit" if case == "wrong_cause" else "stop"),)
    if case == "three":
        entries *= 3
    with pytest.raises(ValueError):
        value.publish_receipts(None, entries)


def test_later_clock_notice_does_not_replace_first_fault(tmp_path, clock):
    value = session(tmp_path, clock)
    value._latch("source")
    value._latch("clock")
    notices = value.poll()
    assert value.snapshot().fault == "source"
    assert [notice.payload.code for notice in notices] == ["source", "clock"]


def loadable_prepared_fixture(tmp_path, monkeypatch):
    declaration, bindings = prepared_fixtures(tmp_path, local_files=True)
    root = tmp_path / "native"
    root.mkdir()
    (root / "scratch").mkdir()
    bindings["work_root"] = str(root)
    bindings["environment"]["TMP"] = str(root / "scratch")
    bindings["environment"]["TEMP"] = str(root / "scratch")
    bindings["compiler_probe"]["environment_sha256"] = api().protocol.canonical_sha256(bindings["environment"])
    declaration_raw = api().protocol.canonical_bytes(declaration)
    binding_raw = api().protocol.canonical_bytes(bindings)
    (root / "protocol.json").write_bytes(declaration_raw)
    (root / "bindings.json").write_bytes(binding_raw)
    prepared = api().PreparedNative(dict(schema="market-native-prepared/v1",
        protocol_sha256=hashlib.sha256(declaration_raw).hexdigest(), bindings_sha256=hashlib.sha256(binding_raw).hexdigest(),
        incarnation=INCARNATION, worker_session=SESSION))
    monkeypatch.setattr(api(), "ROOT", tmp_path / "project")
    monkeypatch.setattr(api(), "current_protocol", lambda: api().protocol.validate_protocol(declaration))
    value = api().NativeSession(api().NativeConfig(INCARNATION, SESSION, prepared.protocol_sha256, root), api().SystemClock())
    return value, prepared


def test_load_prepared_restores_exact_readonly_public_identity(tmp_path, monkeypatch):
    value, expected = loadable_prepared_fixture(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in value.config.work_root.iterdir() if p.is_file()}
    loaded = value.load_prepared(api().protocol.canonical_sha256(expected))
    assert loaded == expected
    assert value.snapshot().state == "prepared" and value._transport is None
    assert {p.name: p.read_bytes() for p in value.config.work_root.iterdir() if p.is_file()} == before


@pytest.mark.parametrize("case", ["wrongdigest", "changed_bindings", "changed_protocol", "used", "scratch_used", "source_changed"])
def test_load_prepared_rejects_wrong_or_mutated_or_used_declaration(tmp_path, monkeypatch, case):
    value, expected = loadable_prepared_fixture(tmp_path, monkeypatch)
    digest = api().protocol.canonical_sha256(expected)
    if case == "wrongdigest":
        digest = "0" * 64
    elif case == "changed_bindings":
        (value.config.work_root / "bindings.json").write_bytes(b"{}")
    elif case == "changed_protocol":
        (value.config.work_root / "protocol.json").write_bytes(b"{}")
    elif case == "used":
        (value.config.work_root / "events.bin").write_bytes(b"")
    elif case == "scratch_used":
        (value.config.work_root / "scratch" / "partial").write_bytes(b"used")
    else:
        original = api().current_protocol().to_dict()
        original["application_sources"]["market/native_session.py"] = "0" * 64
        monkeypatch.setattr(api(), "current_protocol", lambda: api().protocol.validate_protocol(original))
    with pytest.raises(ValueError):
        value.load_prepared(digest)
    assert value._transport is None


@pytest.mark.parametrize("image_at", [None, 32])
def test_fake_normal_session_closes_and_seals_with_exact_eof_epoch(tmp_path, monkeypatch, image_at):
    value = software_session(tmp_path)
    drive_software(value, image_at)
    assert value._transport.eof_deadline <= value._final_deadline
    value.finish_receipts()
    # Publication integration uses an explicitly analytical SourceCheck, as the
    # Task1 synthetic bindings are not a real installed source/tool tree. Actual
    # bounded rehash and changed-byte rejection have separate real-file tests.
    def analytical_comparison():
        started = value._now()
        subset = api().protocol.source_subset(value._protocol, value._bindings,
            value._prepared.protocol_sha256, value._prepared.bindings_sha256)
        return api().protocol.FrozenRecord(dict(scope="prepared-source-lock-tool-cache/v1", started_ns=started,
            finished_ns=value._now(), file_count=subset.file_count,
            bindings_subset_sha256=subset.bindings_subset_sha256, all_match=True))
    monkeypatch.setattr(value, "_final_source_check", analytical_comparison)
    cleanup = value.finish_close()
    assert cleanup.requested_ns == value._stop_ns and cleanup.outcome == "confirmed"
    assert value.snapshot().state == "closed" and value.snapshot().fault is None
    final = api().protocol.inspect_evidence(value.config.work_root)
    assert final.observations == 40 and final.processed_images == int(image_at is not None)


def test_no_child_cleanup_after_failed_prelaunch_closes_owned_writer_and_preserves_failure(tmp_path, clock):
    value = session(tmp_path, clock)
    value._attempted = True
    value._open_test_evidence()
    value._latch("source")
    cleanup = value.finish_close()
    assert cleanup.worker_creation == "not_created" and cleanup.worker is None
    assert cleanup.worker_exit_code is None and cleanup.worker_exit_confirmed is True
    assert cleanup.outcome == "confirmed" and cleanup.evidence_files_closed is True
    assert not value._writer.is_alive() and not value._watchdog.is_alive()
    assert value._events is None
    assert (value.config.work_root / "cleanup.json").exists()
    assert (value.config.work_root / "failure.json").exists()
    assert not (value.config.work_root / "final.json").exists()


def test_unused_prepared_cleanup_has_no_disk_or_child_side_effects(tmp_path, monkeypatch):
    value, expected = loadable_prepared_fixture(tmp_path, monkeypatch)
    value.load_prepared(api().protocol.canonical_sha256(expected))
    before = sorted(path.name for path in value.config.work_root.iterdir())
    cleanup = value.finish_close()
    assert cleanup.worker_creation == "not_created" and cleanup.outcome == "confirmed"
    assert sorted(path.name for path in value.config.work_root.iterdir()) == before
    with pytest.raises(ValueError):
        value.start(expected, True)


def test_emergency_abandons_only_unpublished_ticket_after_explicit_session_fault(tmp_path, clock):
    value = session(tmp_path, clock)
    value._open_test_evidence()
    first = receipt_fixture()
    ticket = value.reserve_receipts()
    value.publish_receipts(ticket, (entry(first),))
    until = time.perf_counter() + 1
    while value.receipt_progress().durable_ticket != ticket.ticket and time.perf_counter() < until:
        time.sleep(0.001)
    unpublished = value.reserve_receipts()
    assert unpublished.ticket == 2
    value.begin_stop("session_fault")
    terminal = dict(first, revision=2, status="rejected", detail="worker_failed", terminal_ns=clock.ns)
    value.publish_receipts(None, (entry(terminal, "stop"),))
    value.finish_receipts()
    value._close_test_evidence()
    assert value.snapshot().fault == "journal_gap"
    with (value.config.work_root / "events.bin").open("rb") as stream:
        rows = api().protocol.read_events(stream)
    assert [r.message.payload.receipt.revision for r in rows] == [1, 2]
    assert [r.message.payload.ticket for r in rows] == [1, 3]
