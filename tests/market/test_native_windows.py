"""Bounded harmless Windows transport receipts; no native imports."""

import importlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import threading
import time

import pytest

from market.native_protocol import read_monitors

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/market/fixtures/native_harmless.py"
INC = "10000000-0000-0000-0000-000000000001"
SESSION = "20000000-0000-0000-0000-000000000002"
WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="actual Windows Job/handles required")


def api():
    return importlib.import_module("market.native_windows")


def binding(root):
    return dict(incarnation=INC, worker_session=SESSION, protocol_sha256="a" * 64,
                work_root=str(root), decoder_work_root=str(root / "decoder"), project_root=str(ROOT))


def message(kind="challenge", seq=0):
    return dict(schema="market-native-ipc/v1", type=kind, seq=seq, incarnation=INC,
                worker_session=SESSION, protocol_sha256="a" * 64, launch_nonce="b" * 64,
                challenge_index=0, p0_ns=1)


@pytest.fixture
def owner(tmp_path):
    module = api()
    child = module.OwnedNativeChild(binding(tmp_path))
    yield child
    if child._stderr_pipe is not None:
        child._drain_stderr()
        (tmp_path / "harmless-stderr.txt").write_bytes(child._stderr)
    child.begin_stop("shutdown")
    result = child.finish_close(evidence_files_closed=True)
    assert result.outcome == "confirmed", result


def test_module_imports_only_the_approved_stdlib_recorder_chain():
    api()
    allowed = {"fly_connectome_sim", "fly_connectome_sim.experiment", "fly_connectome_sim.experiment.recorder"}
    assert {name for name in sys.modules if name.startswith("fly_connectome_sim")} <= allowed


@WINDOWS
def test_actual_duplex_quota_monitor_and_exact_cleanup(owner):
    owner._start_test(FIXTURE, "echo")
    identity = owner.identity.to_dict()
    assert identity["pid"] > 0 and identity["creation_time_100ns"] > 0
    assert owner.commit_limit_bytes == 4294967296
    owner.send(message())
    frame = owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
    assert frame.message.child_ns == 2
    assert owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000) is None
    receipt = owner.finish_close(evidence_files_closed=True)
    assert receipt.outcome == "confirmed" and receipt.worker_exit_code == 0
    assert receipt.job_empty_confirmed and receipt.root_lock_closed
    with (owner.work_root / "monitor.bin").open("rb") as handle:
        rows = read_monitors(handle)
    assert rows[0].job_process_count == 1 and rows[-1].job_process_count == 0
    assert rows[0].sample_ns <= owner.resumed_ns <= rows[-1].sample_ns
    assert all(row.worker_pid == identity["pid"] for row in rows)
    (owner.work_root / "process-receipt.json").write_text(json.dumps(receipt.to_dict()), encoding="utf-8")


@WINDOWS
@pytest.mark.parametrize("mode,code", [("partial", "protocol"), ("oversize", "protocol"),
                                      ("midframe", "deadline"), ("nonzero", "worker_failed"),
                                      ("stderr", "resource"), ("descendant", "ownership")])
def test_actual_bad_child_is_bounded_and_leaves_empty_job(owner, mode, code):
    owner._start_test(FIXTURE, mode)
    with pytest.raises(api().NativeTransportError) as caught:
        owner.receive(deadline_ns=time.perf_counter_ns() + (3_000_000_000 if mode == "stderr" else 500_000_000))
    assert caught.value.code == code
    assert len(owner._stderr) <= 65536
    receipt = owner.finish_close(evidence_files_closed=True)
    assert receipt.worker_exit_confirmed and receipt.job_empty_confirmed
    assert receipt.first_fault == code


@WINDOWS
def test_actual_cancel_sleeping_child_preserves_unrelated_process(owner):
    import subprocess
    sentinel = subprocess.Popen([sys.executable, "-I", "-S", "-c", "import time; time.sleep(12)"])
    try:
        owner._start_test(FIXTURE, "sleep")
        owner.begin_stop("operator")
        receipt = owner.finish_close(evidence_files_closed=True)
        assert receipt.outcome == "confirmed"
        assert sentinel.poll() is None
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=3)


@WINDOWS
def test_actual_full_input_pipe_has_finite_write_deadline(owner):
    owner._start_test(FIXTURE, "sleep")
    with pytest.raises(api().NativeTransportError, match="deadline"):
        owner._write(b"x" * 65536, time.perf_counter_ns() + 150_000_000)
    assert owner.finish_close(evidence_files_closed=True).outcome == "confirmed"


@WINDOWS
def test_actual_monitor_detects_disk_limit_without_large_allocation(owner, monkeypatch):
    owner._start_test(FIXTURE, "sleep")
    monkeypatch.setattr(owner, "_disk_usage", lambda: (268435457, 12))
    deadline = time.perf_counter() + 2
    while owner.fault is None and time.perf_counter() < deadline:
        time.sleep(0.01)
    assert owner.fault == "resource"
    assert owner.finish_close(evidence_files_closed=True).job_empty_confirmed


@WINDOWS
def test_not_created_failure_has_no_fake_identity_or_monitor(tmp_path, monkeypatch):
    child = api().OwnedNativeChild(binding(tmp_path))
    monkeypatch.setattr(child, "_launch", lambda *args: (_ for _ in ()).throw(OSError("injected")))
    with pytest.raises(api().NativeTransportError):
        child._start_test(FIXTURE, "echo")
    receipt = child.finish_close(evidence_files_closed=True)
    assert receipt.worker_creation == "not_created" and receipt.worker is None
    assert receipt.worker_exit_confirmed and receipt.worker_exit_code is None
    assert not (tmp_path / "monitor.bin").exists()


@WINDOWS
def test_created_unverified_retains_exact_handles_and_root_lock(tmp_path, monkeypatch):
    module = api()
    child = module.OwnedNativeChild(binding(tmp_path))
    original = child._verify
    monkeypatch.setattr(child, "_verify", lambda *args: (_ for _ in ()).throw(OSError("injected identity")))
    try:
        with pytest.raises(module.NativeTransportError):
            child._start_test(FIXTURE, "sleep")
        receipt = child.finish_close(evidence_files_closed=True)
        assert receipt.worker_creation == "created_unverified" and receipt.outcome == "unconfirmed"
        assert receipt.worker is None and child.process.handle and child.root_lock.handle
    finally:
        # Explicit test-only teardown after verifying retained ownership. No
        # normative success is invented for an identity that could not be captured.
        child._close_child_streams()
        for handle in (child._read_pipe, child._write_pipe, child._stderr_pipe, child.thread):
            if handle is not None:
                module.PRIMITIVES.K.CloseHandle(handle)
        if child.process is not None:
            child.process.close()
        if child.job is not None:
            child.job.close()
        if child.root_lock is not None:
            child.root_lock.close()


@WINDOWS
def test_confirm_exit_retains_lock_until_caller_closes_own_evidence(owner):
    owner._start_test(FIXTURE, "sleep")
    proof = owner.confirm_exit()
    assert proof.worker_exit_confirmed and proof.job_empty_confirmed
    assert owner.process.handle and owner.job.handle and owner.root_lock.handle
    receipt = owner.finish_close(evidence_files_closed=False)
    assert receipt.outcome == "unconfirmed" and not receipt.root_lock_closed
    assert owner.root_lock.handle
    assert owner.finish_close(evidence_files_closed=True).outcome == "confirmed"


@WINDOWS
def test_injected_handle_close_failure_retains_root_and_cannot_confirm(owner, monkeypatch):
    owner._start_test(FIXTURE, "sleep")
    original = owner._close_child_streams
    monkeypatch.setattr(owner, "_close_child_streams", lambda: (_ for _ in ()).throw(OSError("close failure")))
    receipt = owner.finish_close(evidence_files_closed=True)
    assert receipt.outcome == "unconfirmed" and receipt.cleanup_fault == "cleanup_failed"
    assert owner.root_lock.handle and owner.process.handle and owner.job.handle
    monkeypatch.setattr(owner, "_close_child_streams", original)
    assert owner.finish_close(evidence_files_closed=True).outcome == "confirmed"


@WINDOWS
def test_monitor_record_cap_is_independent_of_lifecycle_sequence(owner):
    owner._start_test(FIXTURE, "sleep")
    owner._monitor_stop.set()
    owner._monitor_thread.join(timeout=2)
    owner._monitor_count = 12000
    with pytest.raises(api().NativeTransportError, match="resource"):
        owner._sample()
    assert owner._receive_seq == owner._send_seq == 0
    owner._monitor_count = 1  # restore only the injected test counter for teardown


@WINDOWS
def test_injected_rss_threshold_is_sampled_not_multigig_allocation(owner, monkeypatch):
    owner._start_test(FIXTURE, "sleep")
    owner._monitor_stop.set()
    owner._monitor_thread.join(timeout=2)
    original = owner._memory
    monkeypatch.setattr(owner, "_memory", lambda process: (4294967297, 4294967297))
    owner._sample()
    assert owner.fault == "resource"
    monkeypatch.setattr(owner, "_memory", original)


@WINDOWS
def test_bound_file_mutation_is_detected_by_parent_without_runtime_read(tmp_path):
    path = tmp_path / "cache.dll"
    path.write_bytes(b"harmless declared cache")
    stat = path.stat()
    import hashlib
    binding = dict(path=str(path), bytes=stat.st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   device=stat.st_dev, file_id=stat.st_ino, mtime_ns=stat.st_mtime_ns)
    declared = {"files": {"native_library": binding, "graph": {"path": "MUST NOT READ"}}}
    api().compare_bound_files(declared, deadline_ns=time.perf_counter_ns() + 1_000_000_000)
    path.write_bytes(b"changed")
    with pytest.raises(api().NativeTransportError, match="source"):
        api().compare_bound_files(declared, deadline_ns=time.perf_counter_ns() + 1_000_000_000)


def prepare_probe(owner, mode):
    import hashlib
    module = api()
    worker = module.PRIMITIVES.WindowsProcess(os.getpid())
    try:
        executable = worker.identity()["executable"]
    finally:
        worker.close()
    cache = owner.work_root / "declared-cache.bin"
    cache.write_bytes(b"harmless cache")
    stat = cache.stat()
    command = [executable, "-I", "-S", "-B", str(ROOT / "tests/market/fixtures/native_probe_payload.py"), mode]
    probe = dict(executable_sha256=hashlib.sha256(Path(executable).read_bytes()).hexdigest(), argv=command,
                 environment_sha256="c" * 64, expected_version="0.16.0", timeout_ns=5_000_000_000,
                 stdout_limit=4096, stderr_limit=4096)
    files = {"native_library": dict(path=str(cache), bytes=stat.st_size,
             sha256=hashlib.sha256(cache.read_bytes()).hexdigest(), device=stat.st_dev,
             file_id=stat.st_ino, mtime_ns=stat.st_mtime_ns)}
    data = dict(binding(owner.work_root), compiler_probe=probe, files=files)
    (owner.work_root / "probe-binding.json").write_text(json.dumps(data), encoding="utf-8")
    owner.bindings = module.protocol.FrozenRecord(data)


@WINDOWS
@pytest.mark.parametrize("mode,expected", [("ok", None), ("timeout", "deadline"),
                                           ("flood", "resource"), ("badversion", "startup"),
                                           ("duplicate", "ownership"), ("mutate", "source"),
                                           ("unexpected", "ownership")])
def test_actual_one_shot_probe_hidden_bound_and_no_build(owner, mode, expected):
    prepare_probe(owner, mode)
    owner._start_test(FIXTURE, "probe_host")
    request = owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
    assert request.message.type == "probe_request"
    allowed = owner.permit_probe(request.message)
    owner.send(dict(schema="market-native-ipc/v1", type="probe_allow", seq=0,
                    incarnation=INC, worker_session=SESSION, protocol_sha256="a" * 64,
                    launch_nonce="b" * 64, request_seq=0, allowed_ns=allowed))
    started = owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
    assert started.message.type == "probe_started", started.message.to_dict()
    owner.accept_probe_started(started.message)
    if expected in ("deadline", "resource", "startup"):
        fault = owner.receive(deadline_ns=time.perf_counter_ns() + 7_000_000_000)
        assert fault.message.type == "fault" and fault.message.code == expected
    else:
        finished = owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
        assert finished.message.type == "probe_finished"
        owner.accept_probe_finished(finished.message)
        terminal = owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
        if expected is None:
            assert terminal is None
        else:
            assert terminal.message.type == "fault" and terminal.message.code == expected
    assert json.loads((owner.work_root / "probe-hidden.json").read_text()) == {"console_window": 0}
    receipt = owner.finish_close(evidence_files_closed=True)
    assert receipt.job_empty_confirmed and receipt.probe_exit_confirmed
    assert receipt.probe is not None and receipt.probe.pid != receipt.worker.pid



@WINDOWS
def test_actual_owner_death_kills_its_job_without_fabricated_cleanup(tmp_path):
    import subprocess
    module = api()
    directory = tmp_path / "owned"
    directory.mkdir()
    host = subprocess.Popen([sys.executable, "-I", "-S", "-B",
                             str(ROOT / "tests/market/fixtures/native_owner_death.py"), str(directory)])
    held = None
    try:
        deadline = time.perf_counter() + 3
        marker = directory / "owned-identity.json"
        while not marker.exists() and time.perf_counter() < deadline:
            time.sleep(0.01)
        identity = json.loads(marker.read_text(encoding="utf-8"))
        held = module.PRIMITIVES.WindowsProcess(identity["pid"])
        assert held.identity()["creation_time_100ns"] == identity["creation_time_100ns"]
        host.wait(timeout=4)
        assert module.PRIMITIVES.K.WaitForSingleObject(held.handle, 3000) == 0
        assert not (directory / "cleanup.json").exists() and not (directory / "final.json").exists()
    finally:
        if host.poll() is None:
            host.terminate()
            host.wait(timeout=3)
        if held is not None:
            if not held.exited():
                module.PRIMITIVES.K.TerminateProcess(held.handle, 1)
            held.close()


@WINDOWS
@pytest.mark.parametrize("index", [7, 39])
@pytest.mark.parametrize("persist_failure", [False, True])
def test_actual_ordinal7_two_frame_exchange_before_one_command(owner, index, persist_failure):
    from test_native_protocol import full_protocol
    module = api()
    records = full_protocol(image_start=index - 7)
    wanted = []
    ended = None
    for direction, value, binary in records:
        if direction != "worker":
            continue
        if ((value["type"] == "observation" and value["observation_index"] == index)
                or (value["type"] == "complete" and value["receipt"]["observation_indices"][-1] == index)):
            value["seq"] = len(wanted)
            wanted.append(module.protocol.encode_frame(value, binary, direction="worker"))
        if value["type"] == "ended":
            value["seq"] = 2
            ended = module.protocol.encode_frame(value, direction="worker")
    assert len(wanted) == 2
    (owner.work_root / "exchange-frames.bin").write_bytes(b"".join(wanted))
    if index == 39:
        (owner.work_root / "exchange-ended.bin").write_bytes(ended)
    owner._start_test(FIXTURE, "pair")
    epoch = time.perf_counter_ns() + 5_000_000_000
    observation = owner.receive(deadline_ns=epoch)
    assert observation.message.observation_index == index and observation.message.exposure_ordinal == 7
    complete = owner.receive(deadline_ns=epoch)
    assert complete.message.type == "complete"
    command = dict(schema="market-native-ipc/v1", type="ack", seq=0,
                   incarnation=INC, worker_session=SESSION, protocol_sha256="a" * 64,
                   launch_nonce="b" * 64, last_observation_index=index,
                   next_observation_index=None if index == 39 else index + 1,
                   action="end" if index == 39 else "black", permit=None,
                   dispatch_id=None, exposure_ordinal=None)
    if persist_failure:
        # The event owner has failed its durable write. Transport must not let
        # a command pass that latched failure. No fake D1 processed assertion.
        owner._latch("storage")
        with pytest.raises(module.NativeTransportError, match="storage"):
            owner.send(command, deadline_ns=epoch)
        assert not (owner.work_root / "exchange-command.json").exists()
    else:
        owner.send(command, deadline_ns=epoch)
        if index == 39:
            assert owner.receive(deadline_ns=epoch).message.type == "ended"
        assert owner.receive(deadline_ns=epoch) is None
        assert json.loads((owner.work_root / "exchange-command.json").read_text())["action"] == command["action"]
        assert owner._send_seq == 1


@WINDOWS
def test_actual_hidden_worker_does_not_inherit_unlisted_capability(owner):
    import ctypes as ct
    from ctypes import wintypes as wt
    module = api()
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateEventW
    create.argtypes = [ct.POINTER(module.SECURITY_ATTRIBUTES), wt.BOOL, wt.BOOL, wt.LPCWSTR]
    create.restype = wt.HANDLE
    security = module.SECURITY_ATTRIBUTES(ct.sizeof(module.SECURITY_ATTRIBUTES), None, True)
    capability = create(ct.byref(security), True, True, None)
    assert capability
    try:
        (owner.work_root / "unlisted-handle.txt").write_text(str(capability))
        owner._start_test(FIXTURE, "handles")
        assert owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000) is None
        proof = json.loads((owner.work_root / "handle-proof.json").read_text())
        assert proof == {"console_window": 0, "unlisted_handle_visible": False}
    finally:
        module.PRIMITIVES.K.CloseHandle(capability)

@WINDOWS
@pytest.mark.parametrize("failure", ["job", "root_lock", "fsync"])
def test_clean_eof_then_closure_failure_never_confirms_or_seals(owner, monkeypatch, failure):
    owner._start_test(FIXTURE, "echo")
    owner.send(message())
    assert owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000).message.type == "clock"
    assert owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000) is None
    def broken(*args):
        raise OSError("injected closure failure")
    if failure == "job":
        original = owner.job.pids
        monkeypatch.setattr(owner.job, "pids", broken)
    elif failure == "root_lock":
        original = owner.root_lock.close
        monkeypatch.setattr(owner.root_lock, "close", broken)
    else:
        original = os.fsync
        monkeypatch.setattr(os, "fsync", broken)
    receipt = owner.finish_close(evidence_files_closed=True)
    assert receipt.outcome == "unconfirmed" and not receipt.root_lock_closed
    assert owner.root_lock.handle and not (owner.work_root / "final.json").exists()
    if failure == "job":
        monkeypatch.setattr(owner.job, "pids", original)
    elif failure == "root_lock":
        monkeypatch.setattr(owner.root_lock, "close", original)
    else:
        monkeypatch.setattr(os, "fsync", original)
        # Caller can explicitly complete the failed monitor durable closure;
        # ownership stays retained until a subsequent actual confirmation.
        owner._write_monitors()
    assert owner.finish_close(evidence_files_closed=True).outcome == "confirmed"


@WINDOWS
def test_stalled_monitor_writer_has_32_row_cap_and_retains_incomplete_owner(owner):
    owner._start_test(FIXTURE, "sleep")
    underlying = owner._monitor_file
    unblock = threading.Event()
    class Stalled:
        def write(self, value):
            unblock.wait(timeout=6)
            return underlying.write(value)
        def fileno(self):
            return underlying.fileno()
        def close(self):
            underlying.close()
    owner._monitor_file = Stalled()
    try:
        deadline = time.perf_counter() + 4.5
        while owner.fault is None and time.perf_counter() < deadline:
            time.sleep(0.02)
        assert owner.fault == "storage" and owner._outbox.qsize() <= 32
        receipt = owner.finish_close(evidence_files_closed=True)
        assert receipt.outcome == "unconfirmed" and owner.root_lock.handle
        assert not (owner.work_root / "final.json").exists()
    finally:
        unblock.set()
        owner._writer_stop.set()
        owner._writer_thread.join(timeout=2)
    assert owner.finish_close(evidence_files_closed=True).outcome == "confirmed"

@WINDOWS
def test_creation_time_mismatch_fault_preserves_exact_worker_and_unrelated_process(owner):
    module = api()
    owner._start_test(FIXTURE, "sleep")
    owner._monitor_stop.set()
    owner._monitor_thread.join(timeout=2)
    actual = owner.identity
    changed = actual.to_dict()
    changed["creation_time_100ns"] += 1
    owner.identity = module.protocol.FrozenRecord(changed)
    try:
        with pytest.raises(module.NativeTransportError, match="ownership"):
            owner._sample()
        assert owner.process.handle and owner.root_lock.handle
    finally:
        owner.identity = actual


@WINDOWS
def test_invalid_clock_cleanup_records_null_times_and_retains_ownership(owner):
    from types import SimpleNamespace
    owner._start_test(FIXTURE, "sleep")
    original = owner.clock
    owner.clock = SimpleNamespace(sample=lambda: SimpleNamespace(monotonic_ns=-1))
    try:
        with pytest.raises(api().NativeTransportError, match="clock"):
            owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
        receipt = owner.finish_close(evidence_files_closed=True)
        assert receipt.requested_ns is None and receipt.finished_ns is None
        assert receipt.first_fault == "clock" and receipt.outcome == "unconfirmed"
        assert receipt.worker_exit_confirmed and receipt.job_empty_confirmed
        assert owner.root_lock.handle
    finally:
        owner.clock = original


@WINDOWS
def test_actual_probe_query_failure_throws_and_retains_exact_resources(tmp_path, monkeypatch):
    module = api()
    child = module.OwnedNativeChild(binding(tmp_path))
    prepare_probe(child, "timeout")
    original = module.PRIMITIVES.WindowsProcess.identity
    try:
        child._start_test(FIXTURE, "probe_host")
        request = child.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
        allowed = child.permit_probe(request.message)
        def failed_identity(process):
            if process.pid != child.identity.pid:
                raise OSError("injected probe GetProcessTimes/ImageName failure")
            return original(process)
        monkeypatch.setattr(module.PRIMITIVES.WindowsProcess, "identity", failed_identity)
        child.send(dict(schema="market-native-ipc/v1", type="probe_allow", seq=0,
                        incarnation=INC, worker_session=SESSION, protocol_sha256="a" * 64,
                        launch_nonce="b" * 64, request_seq=0, allowed_ns=allowed))
        try:
            started = child.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
            child.accept_probe_started(started.message)
        except (OSError, module.NativeTransportError):
            pass
        deadline = time.perf_counter() + 1
        while child.probe is None and time.perf_counter() < deadline:
            time.sleep(0.01)
        assert child.probe is not None and child.probe.handle and child.probe_identity is None
        with pytest.raises(module.NativeTransportError, match="cleanup_failed"):
            child.finish_close(evidence_files_closed=True)
        assert child.root_lock.handle and child.process.handle and child.job.handle and child.probe.handle
        assert not (tmp_path / "cleanup.json").exists() and not (tmp_path / "final.json").exists()
        (tmp_path / "queryfailure-state.json").write_text(json.dumps(dict(
            cleanup_receipt=None, cleanup_fault="cleanup_failed", exact_probe_handle_retained=True,
            exact_worker_handle_retained=True, root_lock_retained=True)))
    finally:
        monkeypatch.setattr(module.PRIMITIVES.WindowsProcess, "identity", original)
        child.confirm_exit()
        child._monitor_stop.set()
        child._writer_stop.set()
        if child._monitor_thread is not None:
            child._monitor_thread.join(timeout=2)
        if child._writer_thread is not None:
            child._writer_thread.join(timeout=2)
        child._close_child_streams()
        for handle in (child._read_pipe, child._write_pipe, child._stderr_pipe, child.thread):
            if handle is not None:
                module.PRIMITIVES.K.CloseHandle(handle)
        if child.probe is not None:
            child.probe.close()
        if child.process is not None:
            child.process.close()
        if child.job is not None:
            child.job.close()
        if child.root_lock is not None:
            child.root_lock.close()


@WINDOWS
def test_transport_refuses_wrong_envelope_before_write(owner):
    owner._start_test(FIXTURE, "sleep")
    wrong = message()
    wrong["incarnation"] = SESSION
    with pytest.raises(api().NativeTransportError, match="protocol"):
        owner.send(wrong)
    assert owner._send_seq == 0

@WINDOWS
@pytest.mark.parametrize("call", ["CreateProcessW", "UpdateProcThreadAttribute", "SetInformationJobObject"])
def test_injected_creation_os_call_failure_closes_only_created_resources(tmp_path, monkeypatch, call):
    import ctypes as ct
    module = api()
    child = module.OwnedNativeChild(binding(tmp_path))
    original = getattr(module.API, call)
    def denied(*args):
        ct.set_last_error(5)
        return 0
    monkeypatch.setattr(module.API, call, denied)
    with pytest.raises(module.NativeTransportError, match="ownership"):
        child._start_test(FIXTURE, "sleep")
    monkeypatch.setattr(module.API, call, original)
    receipt = child.finish_close(evidence_files_closed=True)
    assert receipt.worker_creation == "not_created" and receipt.worker is None
    assert receipt.worker_exit_code is None and receipt.outcome == "confirmed"
    assert not (tmp_path / "monitor.bin").exists()


@WINDOWS
def test_actual_wrong_handle_identity_never_terminates_unrelated_sentinel(owner):
    import subprocess
    module = api()
    sentinel = subprocess.Popen([sys.executable, "-I", "-S", "-c", "import time; time.sleep(8)"])
    other = module.PRIMITIVES.WindowsProcess(sentinel.pid)
    exact = None
    try:
        owner._start_test(FIXTURE, "sleep")
        owner._monitor_stop.set()
        owner._monitor_thread.join(timeout=2)
        exact = owner.process.handle
        owner.process.handle = other.handle
        with pytest.raises(module.NativeTransportError, match="ownership"):
            owner._sample()
        assert sentinel.poll() is None
        owner.process.handle = exact
        assert owner.finish_close(evidence_files_closed=True).job_empty_confirmed
        assert sentinel.poll() is None
    finally:
        if exact is not None and owner.process is not None:
            owner.process.handle = exact
        other.close()
        sentinel.terminate()
        sentinel.wait(timeout=3)


@WINDOWS
def test_real_monitor_gap_fault_uses_high_resolution_elapsed_time(owner):
    owner._start_test(FIXTURE, "sleep")
    owner._monitor_stop.set()
    owner._monitor_thread.join(timeout=2)
    time.sleep(2.02)
    owner._sample()
    assert owner.fault == "deadline" and owner._last_monitor.gap_ns >= 2_000_000_000


@WINDOWS
def test_actual_slow_frame_progress_remains_bounded(owner):
    owner._start_test(FIXTURE, "echo_slow")
    owner.send(message())
    started = time.perf_counter_ns()
    frame = owner.receive(deadline_ns=started + 2_000_000_000)
    assert frame.message.type == "clock" and time.perf_counter_ns() - started >= 100_000_000
    assert owner.receive(deadline_ns=started + 2_000_000_000) is None




@WINDOWS
def test_root_file_close_failure_keeps_advisory_ownership_locked(owner):
    module = api()
    owner._start_test(FIXTURE, "sleep")
    actual = owner.root_lock.handle
    class FailedClose:
        def __getattr__(self, name):
            return getattr(actual, name)
        def close(self):
            raise OSError("injected file closure failure")
    owner.root_lock.handle = FailedClose()
    try:
        receipt = owner.finish_close(evidence_files_closed=True)
        assert receipt.outcome == "unconfirmed" and not receipt.root_lock_closed
        with pytest.raises(OSError):
            module._RootLock(owner.work_root)
    finally:
        owner.root_lock.handle = actual

@WINDOWS
def test_cleanup_job_inventory_loop_uses_only_remaining_common_budget(tmp_path, monkeypatch):
    module = api()
    child = module.OwnedNativeChild(binding(tmp_path))
    child.begin_stop()
    started = time.perf_counter_ns()
    child._cleanup_real_deadline = started + 20_000_000
    job = module.PRIMITIVES.WindowsJob.__new__(module.PRIMITIVES.WindowsJob)
    job.handle, job.lock, job.stopping = 1, threading.RLock(), False
    job.pids = lambda: [123] if time.perf_counter_ns() < started + 120_000_000 else []
    child.job = job
    # Inject finite inventory and OS success; elapsed time is real. No handle1
    # is accessed by Windows and no process is launched in this focused case.
    monkeypatch.setattr(module.PRIMITIVES.K, "TerminateJobObject", lambda *args: 1)
    monkeypatch.setattr(module.API, "TerminateJobObject", lambda *args: 1)
    with pytest.raises(module.NativeTransportError, match="deadline"):
        child.confirm_exit()
    assert time.perf_counter_ns() - started < 90_000_000
    assert child.job is job and child.job.handle == 1


@WINDOWS
def test_cleanup_already_terminating_worker_wait_is_clamped_to_remaining_budget(tmp_path, monkeypatch):
    import ctypes as ct
    from types import SimpleNamespace
    module = api()
    child = module.OwnedNativeChild(binding(tmp_path))
    child.process = SimpleNamespace(handle=1, exited=lambda: False)
    child.begin_stop()
    waits = []
    def terminating(*args):
        ct.set_last_error(5)
        return 0
    def wait(handle, milliseconds):
        waits.append(milliseconds)
        time.sleep(min(milliseconds / 1000, 0.12))
        return 258
    monkeypatch.setattr(module.PRIMITIVES.K, "TerminateProcess", terminating)
    monkeypatch.setattr(module.PRIMITIVES.K, "WaitForSingleObject", wait)
    started = time.perf_counter_ns()
    child._cleanup_real_deadline = started + 20_000_000
    with pytest.raises(module.NativeTransportError, match="deadline"):
        child.confirm_exit()
    assert max(waits) <= 20 and time.perf_counter_ns() - started < 90_000_000


@WINDOWS
def test_known_probe_with_unknown_exit_returns_unconfirmed_normative_receipt(tmp_path, monkeypatch):
    module = api()
    child = module.OwnedNativeChild(binding(tmp_path))
    retained_probe, retained_root = object(), object()
    child.probe, child.root_lock = retained_probe, retained_root
    identity = module.protocol.FrozenRecord(dict(pid=123, creation_time_100ns=1,
                 executable="C:\\harmless.exe", executable_sha256="b" * 64))
    child.probe_identity = identity
    def failed_exit():
        raise module.NativeTransportError("cleanup_failed")
    monkeypatch.setattr(child, "confirm_exit", failed_exit)
    receipt = child.finish_close(evidence_files_closed=True)
    assert receipt.outcome == "unconfirmed" and receipt.cleanup_fault == "cleanup_failed"
    assert receipt.probe == identity and receipt.probe_exit_confirmed is False
    assert receipt.probe_exit_code is None and not receipt.root_lock_closed
    assert child.probe is retained_probe and child.root_lock is retained_root


@WINDOWS
def test_actual_broad_write_deadline_cannot_extend_five_second_operation_cap(owner):
    owner._start_test(FIXTURE, "sleep")
    started = time.perf_counter_ns()
    with pytest.raises(api().NativeTransportError, match="deadline"):
        owner._write(b"x" * 65536, started + 10_000_000_000)
    elapsed = time.perf_counter_ns() - started
    assert 4_800_000_000 <= elapsed < 6_000_000_000


def test_stop_adopts_original_epoch_and_existing_absolute_deadline_without_renewal(tmp_path):
    child = api().OwnedNativeChild(binding(tmp_path))
    now = time.perf_counter_ns()
    requested = now - 100_000_000
    deadline = requested + 25_000_000_000
    child.begin_stop(requested_ns=requested, deadline_ns=deadline)
    assert child._cleanup_requested_ns == requested
    assert child._cleanup_real_deadline == deadline
    child.begin_stop()
    assert child._cleanup_requested_ns == requested and child._cleanup_real_deadline == deadline
    with pytest.raises(api().NativeTransportError):
        child.begin_stop(requested_ns=requested, deadline_ns=deadline + 1)
    assert child._cleanup_real_deadline == deadline


@pytest.mark.parametrize("case", ["future_request", "over25", "expired", "bool", "missing_deadline"])
def test_stop_rejects_invalid_original_epoch_or_extended_budget(tmp_path, case):
    child = api().OwnedNativeChild(binding(tmp_path))
    now = time.perf_counter_ns()
    requested, deadline = now - 1_000_000, now + 1_000_000_000
    if case == "future_request":
        requested = now + 2_000_000_000
    elif case == "over25":
        deadline = requested + 25_000_000_001
    elif case == "expired":
        deadline = now - 1
    elif case == "bool":
        requested = True
    elif case == "missing_deadline":
        deadline = None
    with pytest.raises(api().NativeTransportError):
        child.begin_stop(requested_ns=requested, deadline_ns=deadline)


@WINDOWS
def test_actual_full_eof_then_stop_keeps_original_receipt_epoch(owner):
    owner._start_test(FIXTURE, "echo")
    owner.send(message())
    frame = owner.receive(deadline_ns=time.perf_counter_ns() + 2_000_000_000)
    assert frame.message.type == "clock"
    requested = time.perf_counter_ns()
    deadline = requested + 25_000_000_000
    assert owner.receive(deadline_ns=deadline) is None
    owner.begin_stop(requested_ns=requested, deadline_ns=deadline)
    receipt = owner.finish_close(evidence_files_closed=True)
    assert receipt.requested_ns == requested and receipt.outcome == "confirmed"


def test_supplied_stop_budget_keeps_unknown_clock_timestamp_null(tmp_path):
    from types import SimpleNamespace
    def failed_clock():
        raise ValueError("injected unavailable clock")
    child = api().OwnedNativeChild(binding(tmp_path), SimpleNamespace(sample=failed_clock))
    deadline = time.perf_counter_ns() + 1_000_000_000
    child.begin_stop(requested_ns=None, deadline_ns=deadline)
    assert child._cleanup_requested_ns is None and child._cleanup_real_deadline == deadline
    assert child.fault == "clock"
