"""Offline and non-neural Windows supervision regressions; no simulator runs."""

from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def supervision():
    assert (ROOT / "scripts/market_supervision.py").is_file(), "supervision implementation missing"
    return importlib.import_module("market_supervision")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def test_prepare_requires_disjoint_workspace_paths_and_exact_inventories(tmp_path, monkeypatch):
    module = supervision()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "_configuration", lambda: {"fixture": "non-neural"})
    output = tmp_path / "output"
    output.mkdir()
    (output / "protocol.json").write_text('{"prepared":true}\n')
    expected = digest(output / "protocol.json")
    with pytest.raises(ValueError):
        module.prepare(output, output / "nested", expected)
    with pytest.raises(ValueError):
        module.prepare(output, tmp_path.parent / "outside", expected)
    (output / "partial.log").write_text("old")
    with pytest.raises(ValueError):
        module.prepare(output, tmp_path / "evidence", expected)
    (output / "partial.log").unlink()
    readiness = module.prepare(output, tmp_path / "evidence", expected)
    assert set(p.name for p in (tmp_path / "evidence").iterdir()) == {"readiness.json"}
    assert readiness["protocol_sha256"] == expected
    module.validate_prepared(output, tmp_path / "evidence", expected, digest(tmp_path / "evidence/readiness.json"))
    (tmp_path / "evidence/old.log").write_text("partial")
    with pytest.raises(ValueError):
        module.validate_prepared(output, tmp_path / "evidence", expected, digest(tmp_path / "evidence/readiness.json"))


def test_prepared_source_changes_and_hash_mismatches_fail_closed(tmp_path, monkeypatch):
    module = supervision()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    identity = {"fixture": "before"}
    monkeypatch.setattr(module, "_configuration", lambda: dict(identity))
    output, evidence = tmp_path / "output", tmp_path / "evidence"
    output.mkdir()
    (output / "protocol.json").write_text("{}\n")
    expected = digest(output / "protocol.json")
    module.prepare(output, evidence, expected)
    ready = digest(evidence / "readiness.json")
    with pytest.raises(ValueError):
        module.validate_prepared(output, evidence, "0" * 64, ready)
    identity["fixture"] = "after"
    with pytest.raises(ValueError):
        module.validate_prepared(output, evidence, expected, ready)


@pytest.mark.parametrize("problem", ["missing", "wrong-token", "wrong-pid", "wrong-protocol", "wrong-readiness"])
def test_worker_never_passes_missing_or_wrong_release(tmp_path, problem):
    module = supervision()
    binding = {"pid": os.getpid(), "start_token": "a" * 64,
               "protocol_sha256": "b" * 64, "readiness_sha256": "c" * 64}
    if problem != "missing":
        release = dict(binding)
        release[{"wrong-token": "start_token", "wrong-pid": "pid", "wrong-protocol": "protocol_sha256",
                 "wrong-readiness": "readiness_sha256"}[problem]] = "wrong"
        (tmp_path / "release.json").write_text(json.dumps(release))
    with pytest.raises((ValueError, TimeoutError)):
        module._wait_for_release(tmp_path, binding, timeout=0.04)
    assert json.loads((tmp_path / "worker-ready.json").read_text()) == binding


def test_worker_ready_is_exclusive_and_correct_release_passes(tmp_path):
    module = supervision()
    binding = {"pid": os.getpid(), "start_token": "a" * 64,
               "protocol_sha256": "b" * 64, "readiness_sha256": "c" * 64}
    (tmp_path / "release.json").write_text(json.dumps(binding))
    module._wait_for_release(tmp_path, binding, timeout=0.1)
    with pytest.raises(FileExistsError):
        module._wait_for_release(tmp_path, binding, timeout=0.1)


def test_process_guard_allows_exact_probe_and_denies_compile_and_shell(tmp_path):
    module = supervision()
    probe = [sys.executable, "-c", "print('version-only')"]
    with module.compiler_probe_guard(probe):
        assert subprocess.run(probe, capture_output=True, text=True, check=True).stdout.strip() == "version-only"
        with pytest.raises(RuntimeError, match="process start"):
            subprocess.run([sys.executable, "-c", "raise SystemExit('compile')"], check=True)
        with pytest.raises(RuntimeError, match="process start"):
            subprocess.run("echo shell", shell=True)
        with pytest.raises(RuntimeError, match="process start"):
            os.system("echo shell")


def test_production_runner_cannot_construct_engine_without_supervision(tmp_path, monkeypatch):
    from test_market_response_diagnostic import diagnostic
    module = diagnostic()
    output = tmp_path / "prepared"
    module.prepare_diagnostic(output)
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("unsupervised engine"))
    with pytest.raises(ValueError, match="supervision"):
        module.run_diagnostic(output, expected_protocol_sha256=digest(output / "protocol.json"))


@pytest.mark.skipif(sys.platform != "win32", reason="pinned local Windows toolchain inventory")
def test_actual_preparation_binds_existing_cache_without_starting_processes():
    module = supervision()
    if not (ROOT / "data/malecns-v1.0/runtime/cache/physiology-v6/memory.dll").is_file():
        pytest.skip("private prepared native cache unavailable")
    with module.compiler_probe_guard(["never-launch"]):
        config = module._configuration()
    assert Path(config["files"]["native_source"]["path"]).name == "kernel.cpp"
    assert config["compiler_version_argv"][-1] == "version"
    assert config["files"]["native_library"]["sha256"] == digest(ROOT / "data/malecns-v1.0/runtime/cache/physiology-v6/memory.dll")


@pytest.mark.skipif(sys.platform != "win32", reason="local pinned Zig probe")
def test_actual_pinned_zig_version_allowed_but_compilation_denied(tmp_path):
    module = supervision()
    compiler = ROOT / ".tools/zig/zig-x86_64-windows-0.16.0/zig.exe"
    if not compiler.is_file():
        pytest.skip("private pinned Zig unavailable")
    with module.compiler_probe_guard([str(compiler), "version"]):
        assert subprocess.run([str(compiler), "version"], check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip() == "0.16.0"
        with pytest.raises(RuntimeError, match="process start"):
            subprocess.run([str(compiler), "c++", str(tmp_path / "never.cpp"), "-o", str(tmp_path / "never.dll")])
    assert not (tmp_path / "never.dll").exists()


@pytest.mark.parametrize("missing", ["--supervision-directory", "--expected-readiness-sha256", "--start-token"])
def test_native_cli_requires_every_supervision_binding_before_any_work(tmp_path, missing):
    arguments = {"--output-dir": str(tmp_path / "absent"), "--expected-protocol-sha256": "b" * 64,
                 "--supervision-directory": str(tmp_path / "evidence"), "--expected-readiness-sha256": "c" * 64,
                 "--start-token": "a" * 64}
    del arguments[missing]
    result = subprocess.run([sys.executable, str(ROOT / "scripts/run-market-response-diagnostic.py"), "run", "--run-native",
                             *(item for pair in arguments.items() for item in pair)], capture_output=True, text=True)
    assert result.returncode == 2
    assert missing in result.stderr
    assert not (tmp_path / "absent").exists()


WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="real Windows Job Object/PeakWorkingSet host smoke")


def _smoke(module, tmp_path, body, *, limits=None, fault=None, cancel=None):
    output, evidence = tmp_path / "output", tmp_path / "evidence"
    output.mkdir()
    evidence.mkdir()
    child = tmp_path / "non-neural-child.py"
    child.write_text(
        "import sys,os,time,json,subprocess\n"
        f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
        "from pathlib import Path\nfrom market_supervision import _wait_for_release\n"
        "evidence=Path(sys.argv[1]); output=Path(sys.argv[2])\n"
        "binding={'pid':os.getpid(),'start_token':'a'*64,'protocol_sha256':'b'*64,'readiness_sha256':'c'*64}\n"
        "_wait_for_release(evidence,binding,timeout=10)\n" + body,
        encoding="utf-8",
    )
    launcher = ROOT / ".venv/Scripts/python.exe"
    if not launcher.is_file():
        pytest.skip("local Windows virtualenv launcher unavailable")
    return module._run_owned(
        [str(launcher), str(child), str(evidence), str(output)], output, evidence,
        expected_executable=Path(sys._base_executable),
        binding={"start_token": "a" * 64, "protocol_sha256": "b" * 64, "readiness_sha256": "c" * 64},
        limits=limits or {"wall_seconds": 10, "peak_rss_bytes": 512 * 1024**2,
                          "new_output_evidence_bytes": 1024**2, "poll_seconds_max": 0.05},
        _test_fault=fault, _test_cancel=cancel,
    )


@WINDOWS
def test_real_venv_worker_identity_and_literal_arguments(tmp_path):
    module = supervision()
    receipt = _smoke(module, tmp_path, "(output/'receipt.json').write_text('{}')\nprint('literal; $() &')\n")
    assert receipt["status"] == "completed", receipt
    assert receipt["worker"]["pid"] != receipt["launcher"]["pid"]
    assert receipt["worker"]["creation_time_100ns"] >= receipt["launcher"]["creation_time_100ns"]
    assert receipt["observed_peak_working_set_bytes"] > 0
    assert receipt["job_active_processes_after_cleanup"] == 0
    assert "literal; $() &" in (tmp_path / "evidence/stdout.log").read_text()


@WINDOWS
def test_real_diagnostic_producer_receipt_is_supervisor_completion_contract(tmp_path, monkeypatch):
    from test_market_response_diagnostic import execute
    producer = tmp_path / "synthetic-producer"
    producer.mkdir()
    _, produced, _, native_free_receipt = execute(producer, monkeypatch)
    assert native_free_receipt["status"] == "complete"
    assert (produced / "receipt.json").is_file()
    consumer = tmp_path / "supervised-consumer"
    consumer.mkdir()
    receipt = _smoke(supervision(), consumer,
                     f"import shutil\nshutil.copyfile({str(produced / 'receipt.json')!r},output/'receipt.json')\n")
    assert receipt["status"] == "completed", receipt
    assert receipt["stop_reason"] == "completed"
    assert json.loads((consumer / "output/receipt.json").read_text()) == native_free_receipt


@WINDOWS
def test_startup_python_peak_stops_before_any_worker_ready(tmp_path):
    module = supervision()
    output, evidence = tmp_path / "output", tmp_path / "evidence"
    output.mkdir()
    evidence.mkdir()
    child = tmp_path / "non-neural-startup.py"
    child.write_text("import time\nheld=bytearray(32*1024**2)\ntime.sleep(60)\n")
    receipt = module._run_owned(
        [str(ROOT / ".venv/Scripts/python.exe"), str(child)], output, evidence,
        expected_executable=Path(sys._base_executable),
        binding={"start_token": "a" * 64, "protocol_sha256": "b" * 64, "readiness_sha256": "c" * 64},
        limits={"wall_seconds": 1, "peak_rss_bytes": 24 * 1024**2,
                "new_output_evidence_bytes": 1024**2, "poll_seconds_max": 0.05})
    assert receipt["stop_reason"] == "memory-limit", receipt
    assert receipt["worker"] is None
    assert not (evidence / "release.json").exists()
    assert receipt["job_active_processes_after_cleanup"] == 0


@WINDOWS
@pytest.mark.parametrize("condition", ["wall", "memory", "disk", "monitor", "assignment", "cancel", "nonzero", "hanging-probe"])
def test_real_stop_conditions_terminate_entire_owned_job(tmp_path, condition):
    module = supervision()
    limits = {"wall_seconds": 2, "peak_rss_bytes": 512 * 1024**2,
              "new_output_evidence_bytes": 1024**2, "poll_seconds_max": 0.05}
    body = "subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
    if condition == "memory":
        limits["peak_rss_bytes"] = 1
    elif condition == "disk":
        body += "(Path(os.environ['TEMP'])/'scratch.bin').write_bytes(b'x'*2000000)\n"
    elif condition == "nonzero":
        body += "raise SystemExit(7)\n"
    elif condition == "hanging-probe":
        body += "from market_supervision import compiler_probe_guard\nprobe=[sys.executable,'-c','import time;time.sleep(60)']\nwith compiler_probe_guard(probe):\n subprocess.run(probe)\n"
    body += "time.sleep(60)\n"
    receipt = _smoke(module, tmp_path, body, limits=limits,
                     fault=condition if condition in {"monitor", "assignment"} else None,
                     cancel=(lambda: True) if condition == "cancel" else None)
    assert receipt["status"] == "failed", receipt
    expected = {"wall": "wall-limit", "memory": "memory-limit", "disk": "output-limit",
                "monitor": "monitor-failure", "assignment": "monitor-failure", "cancel": "cancelled",
                "nonzero": "child-failed", "hanging-probe": "wall-limit"}[condition]
    assert receipt["stop_reason"] == expected, receipt
    assert receipt["job_active_processes_after_cleanup"] == 0
    if condition in {"assignment", "memory"}:
        assert not (tmp_path / "evidence/release.json").exists()


@WINDOWS
def test_accounting_failure_keeps_failed_receipt_and_terminates_owned_processes(tmp_path, monkeypatch):
    module = supervision()
    def unavailable(*directories):
        raise OSError("injected filesystem accounting failure")
    monkeypatch.setattr(module, "_new_bytes", unavailable)
    receipt = _smoke(module, tmp_path, "time.sleep(60)\n")
    assert receipt["status"] == "failed"
    assert receipt["stop_reason"] == "monitor-failure"
    assert receipt["output_accounting_complete"] is False
    assert receipt["job_active_processes_after_cleanup"] == 0
    assert json.loads((tmp_path / "evidence/supervisor-receipt.json").read_text())["status"] == "failed"


@WINDOWS
def test_higher_final_peak_cannot_leave_success_receipt(tmp_path, monkeypatch):
    module = supervision()
    finished = False
    terminate = module.WindowsJob.terminate_and_wait
    peak = module.WindowsProcess.peak
    def final_cleanup(job):
        nonlocal finished
        terminate(job)
        finished = True
    def late_peak(process):
        actual = peak(process)
        # Controlled final-counter boundary, not a claim of real memory pressure.
        return max(actual, 513 * 1024**2) if finished else actual
    monkeypatch.setattr(module.WindowsJob, "terminate_and_wait", final_cleanup)
    monkeypatch.setattr(module.WindowsProcess, "peak", late_peak)
    receipt = _smoke(module, tmp_path, "(output/'receipt.json').write_text('{}')\n")
    assert receipt["status"] == "failed", receipt
    assert receipt["stop_reason"] == "memory-limit"
    assert receipt["job_active_processes_after_cleanup"] == 0


@WINDOWS
@pytest.mark.parametrize("when", ["before-cutoff", "after-cutoff"])
def test_terminal_cancellation_cutoff_is_atomic_and_cancel_bytes_stay_counted(tmp_path, monkeypatch, when):
    module = supervision()
    terminate, measure = module.WindowsJob.terminate_and_wait, module._new_bytes
    cleaned, requested = False, []
    evidence = tmp_path / "evidence"
    def after_cleanup(job):
        nonlocal cleaned
        terminate(job)
        cleaned = True
        if when == "before-cutoff" and not requested:
            requested.append(module.request_cancellation(evidence))
    def final_accounting(*directories):
        if when == "after-cutoff" and cleaned and not requested:
            requested.append(module.request_cancellation(evidence))
        return measure(*directories)
    monkeypatch.setattr(module.WindowsJob, "terminate_and_wait", after_cleanup)
    monkeypatch.setattr(module, "_new_bytes", final_accounting)
    receipt = _smoke(module, tmp_path, "(output/'receipt.json').write_text('{}')\n")
    if when == "before-cutoff":
        assert requested == [True]
        assert receipt["status"] == "failed", receipt
        assert receipt["stop_reason"] == "cancelled"
    else:
        assert requested == [False]
        assert receipt["status"] == "completed", receipt
    assert (evidence / "cancel.signal").read_bytes() == b"2"
    assert receipt["cancellation_requested_at_cutoff"] is (when == "before-cutoff")
    assert receipt["observed_output_evidence_bytes"] == measure(tmp_path / "output", evidence)
    # Repeated late frontend cancellation cannot grow counted bytes or change state.
    assert module.request_cancellation(evidence) is False
    assert receipt["observed_output_evidence_bytes"] == measure(tmp_path / "output", evidence)
    assert json.loads((evidence / "supervisor-receipt.json").read_text()) == receipt


def _wait_file(path, process=None, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text())
        if process is not None and process.poll() is not None:
            pytest.fail(f"non-neural harness exited early: {process.communicate()}")
        time.sleep(0.02)
    pytest.fail(f"bounded wait for {path.name} expired")


def _frontend_fixture(tmp_path, *, hold_before_ready=False):
    """Exact shipped PS frontend, test-only helper harness, no neural code path."""
    root = tmp_path / "fixture ; & $() workspace"
    (root / "scripts").mkdir(parents=True)
    (root / ".venv/Scripts").mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/supervise-market-response.ps1", root / "scripts/supervise-market-response.ps1")
    shutil.copyfile(ROOT / ".venv/Scripts/python.exe", root / ".venv/Scripts/python.exe")
    shutil.copyfile(ROOT / ".venv/pyvenv.cfg", root / ".venv/pyvenv.cfg")
    site = root / ".venv/Lib/site-packages"
    site.mkdir(parents=True)
    (site / "test-existing.pth").write_text(str(ROOT / ".venv/Lib/site-packages") + "\n" + str(ROOT / "src") + "\n")
    output, evidence = root / "output", root / "evidence"
    output.mkdir()
    evidence.mkdir()
    (evidence / "readiness.json").write_text("{}\n")
    if hold_before_ready:
        (evidence / "test-hold-before-ready").write_text("non-neural fixture")
    child = root / "scripts/non-neural-child.py"
    child.write_text(
        f"import sys,os,time,json,subprocess\nsys.path.insert(0,{str(ROOT / 'scripts')!r})\n"
        "from pathlib import Path\nfrom market_supervision import _wait_for_release,write_json_exclusive\n"
        "e=Path(sys.argv[1]); b={'pid':os.getpid(),'start_token':'a'*64,'protocol_sha256':'b'*64,'readiness_sha256':'c'*64}\n"
        "write_json_exclusive({'pid':os.getpid()},e/'worker-before-ready.json')\n"
        "if (e/'test-hold-before-ready').exists(): time.sleep(60)\n"
        "_wait_for_release(e,b,timeout=10)\n"
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
        "write_json_exclusive({'pid':p.pid},e/'grandchild.json')\ntime.sleep(60)\n")
    helper = root / "scripts/market_supervision.py"
    helper.write_text(
        f"import sys\nsys.path.insert(0,{str(ROOT / 'scripts')!r})\n"
        "from pathlib import Path\nimport market_supervision as m\n"
        "def non_neural_run(output,evidence,ph,rh,*,owner):\n"
        f" return m._run_owned([{str(ROOT / '.venv/Scripts/python.exe')!r},{str(child)!r},str(evidence)],output,evidence,"
        "expected_executable=Path(sys._base_executable),binding={'start_token':'a'*64,'protocol_sha256':ph,'readiness_sha256':rh},"
        "limits={'wall_seconds':20,'peak_rss_bytes':536870912,'new_output_evidence_bytes':1048576,'poll_seconds_max':0.05},owner=owner)\n"
        "m.run=non_neural_run\nraise SystemExit(m.main())\n")
    return root, output, evidence


@WINDOWS
@pytest.mark.parametrize("forgery", ["wrong-start", "wrong-hash", "unrelated-same-executable"])
def test_frontend_never_promotes_or_kills_foreign_ready_candidate(tmp_path, forgery):
    module = supervision()
    foreign = subprocess.Popen([sys._base_executable, "-c", "import time;time.sleep(60)"],
                               creationflags=subprocess.CREATE_NO_WINDOW)
    held = module.WindowsProcess(foreign.pid)
    identity = held.identity()
    root, output, evidence = _frontend_fixture(tmp_path)
    helper = root / "scripts/market_supervision.py"
    helper.write_text(
        f"import sys,time\nsys.path.insert(0,{str(ROOT / 'scripts')!r})\n"
        "import market_supervision as m\n"
        "def forged_run(output,evidence,ph,rh,*,owner):\n"
        f" ready={identity!r}\n"
        " ready.update(owner=owner.identity(),start_token='a'*64,protocol_sha256=ph,readiness_sha256=rh)\n"
        + (" ready['creation_time_100ns']+=1\n" if forgery == "wrong-start" else "")
        + (" ready['readiness_sha256']='0'*64\n" if forgery == "wrong-hash" else "")
        + " m.write_json_exclusive(ready,evidence/'supervisor-ready.json')\n time.sleep(2)\n raise RuntimeError('forged non-neural harness ends')\n"
        "m.run=forged_run\nraise SystemExit(m.main())\n")
    try:
        result = subprocess.run(
            [shutil.which("pwsh"), "-NoProfile", "-File", str(root / "scripts/supervise-market-response.ps1"),
             "-Mode", "Run", "-OutputDirectory", str(output), "-EvidenceDirectory", str(evidence),
             "-ExpectedProtocolSha256", "b" * 64, "-ExpectedReadinessSha256", "c" * 64],
            capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        assert not held.exited(), "frontend killed an unvalidated unrelated process"
        assert result.returncode != 0
        assert not (evidence / "supervisor-ack.json").exists(), "unrelated candidate was acknowledged"
        module.write_json_exclusive({"forgery": forgery, "foreign": identity, "foreign_survived": not held.exited(),
                                     "frontend_exit": result.returncode, "stderr": result.stderr}, root / "foreign-smoke.json")
    finally:
        if foreign.poll() is None:
            foreign.kill()
        foreign.wait(timeout=5)
        held.close()


@WINDOWS
def test_watchdog_error_started_before_cutoff_cannot_be_lost_during_join(tmp_path):
    module = supervision()
    root, output, evidence = _frontend_fixture(tmp_path)
    child = root / "scripts/non-neural-child.py"
    child.write_text(
        f"import sys,os\nsys.path.insert(0,{str(ROOT / 'scripts')!r})\nfrom pathlib import Path\n"
        "from market_supervision import _wait_for_release\ne=Path(sys.argv[1])\n"
        "_wait_for_release(e,{'pid':os.getpid(),'start_token':'a'*64,'protocol_sha256':'b'*64,'readiness_sha256':'c'*64})\n"
        "(e.parent/'output/receipt.json').write_text('{}')\n")
    helper = root / "scripts/market_supervision.py"
    source = helper.read_text()
    injection = (
        "import threading\noriginal_cancel=m._cancel_state\ncutoff_done=threading.Event()\n"
        "class DelayedMonitorError(Exception):\n"
        " def __str__(self):\n  assert cutoff_done.wait(5)\n  return 'pre-cutoff monitor failure delivered at join'\n"
        "def delayed_cancel(evidence,**kwargs):\n"
        " if threading.current_thread().name=='market-owner-watchdog': raise DelayedMonitorError()\n"
        " value=original_cancel(evidence,**kwargs)\n"
        " if kwargs.get('terminal'): cutoff_done.set()\n return value\n"
        "m._cancel_state=delayed_cancel\n")
    helper.write_text(source.replace("m.run=non_neural_run", injection + "m.run=non_neural_run"))
    result = subprocess.run(
        [shutil.which("pwsh"), "-NoProfile", "-File", str(root / "scripts/supervise-market-response.ps1"),
         "-Mode", "Run", "-OutputDirectory", str(output), "-EvidenceDirectory", str(evidence),
         "-ExpectedProtocolSha256", "b" * 64, "-ExpectedReadinessSha256", "c" * 64],
        capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    receipt = json.loads((evidence / "supervisor-receipt.json").read_text())
    assert receipt["status"] == "failed", receipt
    assert receipt["stop_reason"] == "monitor-failure"
    assert receipt["job_active_processes_after_cleanup"] == 0
    assert result.returncode != 0


@WINDOWS
@pytest.mark.parametrize("interruption", ["cancel-before-release", "cancel-after-release", "powershell-death", "supervisor-death", "console-ctrl-c"])
def test_real_frontend_lifetime_terminates_owned_job(tmp_path, interruption):
    module = supervision()
    if not (ROOT / ".venv/Scripts/python.exe").is_file():
        pytest.skip("private virtualenv unavailable")
    root, output, evidence = _frontend_fixture(tmp_path, hold_before_ready=interruption == "cancel-before-release")
    command = [shutil.which("pwsh"), "-NoProfile", "-File", str(root / "scripts/supervise-market-response.ps1"),
               "-Mode", "Run", "-OutputDirectory", str(output), "-EvidenceDirectory", str(evidence),
               "-ExpectedProtocolSha256", "b" * 64, "-ExpectedReadinessSha256", "c" * 64]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startup,
                               creationflags=subprocess.CREATE_NEW_CONSOLE if interruption == "console-ctrl-c"
                               else subprocess.CREATE_NO_WINDOW)
    supervisor, worker, grandchild = None, None, None
    worker_identity, grandchild_identity = None, None
    try:
        ready = _wait_file(evidence / "supervisor-ready.json", process)
        supervisor = module.WindowsProcess(ready["pid"])
        assert supervisor.identity()["creation_time_100ns"] == ready["creation_time_100ns"]
        if interruption == "cancel-before-release":
            before = _wait_file(evidence / "worker-before-ready.json", process)
            worker = module.WindowsProcess(before["pid"])
            worker_identity = worker.identity()
        if interruption != "cancel-before-release":
            worker_ready = _wait_file(evidence / "worker-ready.json", process)
            worker = module.WindowsProcess(worker_ready["pid"])
            worker_identity = worker.identity()
            spawned = _wait_file(evidence / "grandchild.json", process)
            grandchild = module.WindowsProcess(spawned["pid"])
            grandchild_identity = grandchild.identity()
        begin = time.monotonic()
        if interruption.startswith("cancel"):
            # Same explicit channel used by frontend finally, while PS still lives.
            module.request_cancellation(evidence)
        elif interruption == "powershell-death":
            process.kill()
        elif interruption == "supervisor-death":
            module.K.TerminateProcess(supervisor.handle, 1)
        else:
            sender = root / "send-console-event.py"
            sender.write_text(
                "import ctypes as c,sys,time\nfrom ctypes import wintypes as w\nk=c.WinDLL('kernel32',use_last_error=True)\n"
                "k.FreeConsole()\nassert k.AttachConsole(int(sys.argv[1])),c.get_last_error()\n"
                "handler=c.WINFUNCTYPE(w.BOOL,w.DWORD)(lambda event: True)\n"
                "assert k.SetConsoleCtrlHandler(handler,True),c.get_last_error()\n"
                "assert k.GenerateConsoleCtrlEvent(0,0),c.get_last_error()\ntime.sleep(.1)\nk.FreeConsole()\n")
            sent = subprocess.run([str(ROOT / ".venv/Scripts/python.exe"), str(sender), str(process.pid)],
                                  capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
            assert sent.returncode == 0, sent.stderr
        assert module.K.WaitForSingleObject(supervisor.handle, 5000) == 0
        for child in (worker, grandchild):
            if child:
                assert module.K.WaitForSingleObject(child.handle, 5000) == 0
        assert time.monotonic() - begin < 6
        if interruption.startswith("cancel") or interruption in {"powershell-death", "console-ctrl-c"}:
            receipt = _wait_file(evidence / "supervisor-receipt.json")
            assert receipt["status"] == "failed"
            assert receipt["job_active_processes_after_cleanup"] == 0
            assert receipt["stop_reason"] in {"cancelled", "owner-exited"}
        if interruption == "cancel-before-release":
            assert not (evidence / "release.json").exists()
        if interruption == "console-ctrl-c":
            assert receipt["stop_reason"] == "cancelled", "real Ctrl+C did not execute frontend finally cancellation"
            assert receipt["cancellation_requested_at_cutoff"] is True
        module.write_json_exclusive({
            "test_scope": "exact shipped PS frontend; test-only non-neural helper harness",
            "interruption": interruption, "powershell_pid": process.pid,
            "supervisor": ready, "worker": worker_identity,
            "grandchild": grandchild_identity,
            "cleanup_seconds": time.monotonic() - begin,
            "supervisor_signaled": supervisor.exited(), "worker_signaled": worker.exited() if worker else None,
            "grandchild_signaled": grandchild.exited() if grandchild else None,
        }, root / "host-smoke.json")
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
        for child in (supervisor, worker, grandchild):
            if child:
                child.close()
