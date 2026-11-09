"""Synthetic bindings and harmless Windows lifecycle tests; no neural launch."""

from copy import deepcopy
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
WINDOWS = pytest.mark.skipif(sys.platform != "win32", reason="real Windows owned-process/frontend lifecycle")
FIXED = {"wall_seconds": 900, "peak_rss_bytes": 4 * 1024**3,
         "new_output_evidence_scratch_bytes": 256 * 1024**2, "poll_seconds_max": 2}


def adapter():
    assert (ROOT / "scripts/continuous_motor_supervision.py").is_file(), "continuous supervision implementation missing"
    return importlib.import_module("continuous_motor_supervision")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def workspace(tmp_path):
    # Public production paths remain confined even on CI's external pytest tmp.
    if tmp_path.is_relative_to(ROOT):
        return tmp_path
    path = ROOT / ".tools/continuous-supervisor-ci-fixtures" / uuid4().hex
    path.mkdir(parents=True)
    return path


def prepared(module, workspace, monkeypatch):
    config = {"fixture": "explicitly non-neural"}
    monkeypatch.setattr(module, "_configuration", lambda: deepcopy(config))
    output, evidence = workspace / "output", workspace / "evidence"
    output.mkdir()
    (output / "protocol.json").write_text(json.dumps({"version": "continuous-motor-probe/v1", "limits": FIXED}))
    ph = digest(output / "protocol.json")
    readiness = module.prepare(output, evidence, ph)
    return output, evidence, ph, digest(evidence / "readiness.json"), readiness, config


def test_frontend_preserves_exact_validated_ownership_and_cancel_behavior():
    expected = (ROOT / "scripts/supervise-market-response.ps1").read_bytes().replace(
        b"'market_supervision.py'", b"'continuous_motor_supervision.py'")
    assert (ROOT / "scripts/supervise-continuous-motor.ps1").is_file(), "new frontend missing"
    assert (ROOT / "scripts/supervise-continuous-motor.ps1").read_bytes() == expected


def test_configuration_separately_binds_new_sources_and_honest_legacy_snapshot(monkeypatch):
    module = adapter()
    old = {"files": {"entrypoint": {"path": "old-diagnostic.py"}}, "compiler_version_argv": ["zig", "version"]}
    monkeypatch.setattr(module, "_legacy_configuration", lambda: deepcopy(old))
    config = module._configuration()
    assert config["legacy_runtime_configuration"] == old
    for key, name in {"entrypoint": "run-continuous-motor-probe.py", "helper": "continuous_motor_supervision.py",
                      "supervisor": "supervise-continuous-motor.ps1"}.items():
        identity = config["files"][key]
        assert Path(identity["path"]) == ROOT / "scripts" / name
        assert identity["sha256"] == digest(ROOT / "scripts" / name)


def test_prepare_has_new_version_exact_limits_and_exclusive_inventories(workspace, monkeypatch):
    module = adapter()
    output, evidence, ph, rh, ready, _ = prepared(module, workspace, monkeypatch)
    assert ready["version"] == "continuous-motor-supervision/v1"
    assert ready["limits"] == FIXED
    assert module.validate_prepared(output, evidence, ph, rh) == ready
    with pytest.raises(ValueError):
        module.prepare(output, evidence, ph)
    (evidence / "partial.log").write_text("partial")
    with pytest.raises(ValueError):
        module.validate_prepared(output, evidence, ph, rh)


@pytest.mark.parametrize("problem", ["old-readiness", "configuration", "protocol-hash", "readiness-hash",
                                    "boolean-limit", "float-limit", "old-protocol", "entrypoint",
                                    "typed-config-zero", "typed-config-one"])
def test_readiness_and_protocol_contradictions_fail_before_execution(workspace, monkeypatch, problem):
    module = adapter()
    output, evidence, ph, rh, ready, config = prepared(module, workspace, monkeypatch)
    if problem in {"old-readiness", "entrypoint", "typed-config-zero", "typed-config-one"}:
        if problem == "old-readiness":
            ready["version"] = "market-supervision/v1"
        elif problem == "entrypoint":
            ready["configuration"]["files"] = {"entrypoint": "old-diagnostic.py"}
        else:
            value = 0 if problem == "typed-config-zero" else 1
            config["typed"] = value
            ready["configuration"]["typed"] = bool(value)
        (evidence / "readiness.json").write_text(json.dumps(ready))
        rh = digest(evidence / "readiness.json")
    elif problem == "configuration":
        config["fixture"] = "changed"
    elif problem == "protocol-hash":
        ph = "0" * 64
    elif problem == "readiness-hash":
        rh = "0" * 64
    else:
        protocol = json.loads((output / "protocol.json").read_text())
        if problem in {"boolean-limit", "float-limit"}:
            protocol["limits"]["poll_seconds_max"] = True if problem == "boolean-limit" else 2.0
        else:
            protocol["version"] = "market-response-diagnostic/v1"
        (output / "protocol.json").write_text(json.dumps(protocol))
        ph = digest(output / "protocol.json")
    with pytest.raises(ValueError):
        module.validate_prepared(output, evidence, ph, rh)


def test_path_confinement_and_disjointness_are_shared(workspace):
    module = adapter()
    import market_supervision as legacy
    assert module._paths is legacy._paths
    with pytest.raises(ValueError):
        module._paths(workspace, workspace / "nested")
    with pytest.raises(ValueError):
        module._paths(ROOT.parent / "outside", workspace)


@pytest.mark.parametrize("problem", ["missing", "token", "readiness", "scratch", "release", "changed-after-release"])
def test_production_guard_rejects_invalid_bindings_without_entering(workspace, monkeypatch, problem):
    module = adapter()
    output, evidence, ph, rh, _, config = prepared(module, workspace, monkeypatch)
    scratch = evidence / "scratch"
    scratch.mkdir()
    for name in ("TMP", "TEMP"):
        monkeypatch.setenv(name, str(scratch if problem != "scratch" else workspace))
    token = "a" * 64
    if problem == "missing":
        evidence = None
    elif problem == "token":
        token = "wrong"
    elif problem == "readiness":
        rh = "0" * 64
    if problem == "release":
        (evidence / "release.json").write_text(json.dumps({"pid": os.getpid(), "start_token": "b" * 64,
            "protocol_sha256": ph, "readiness_sha256": rh}))
    elif problem == "changed-after-release":
        monkeypatch.setattr(module, "_wait_for_release", lambda *args: config.update(fixture="changed"))
    with pytest.raises(ValueError):
        with module.production_start(output, ph, evidence, rh, token):
            pytest.fail("invalid authority entered production context")


@pytest.mark.parametrize("field", ["pid", "start_token", "protocol_sha256", "readiness_sha256", "missing"])
def test_shared_release_requires_every_exact_binding(workspace, field):
    module = adapter()
    binding = {"pid": os.getpid(), "start_token": "a" * 64,
               "protocol_sha256": "b" * 64, "readiness_sha256": "c" * 64}
    if field != "missing":
        release = {**binding, field: "wrong"}
        (workspace / "release.json").write_text(json.dumps(release))
    with pytest.raises((ValueError, TimeoutError)):
        module._wait_for_release(workspace, binding, timeout=0.04)
    assert json.loads((workspace / "worker-ready.json").read_text()) == binding


def test_release_pid_requires_integer_type_even_when_numeric_value_matches(workspace):
    module = adapter()
    binding = {"pid": os.getpid(), "start_token": "a" * 64,
               "protocol_sha256": "b" * 64, "readiness_sha256": "c" * 64}
    (workspace / "release.json").write_text(json.dumps({**binding, "pid": float(os.getpid())}))
    with pytest.raises(ValueError, match="release"):
        module._wait_for_release(workspace, binding, timeout=0.04)


def test_actual_runner_rejects_old_readiness_before_engine(workspace, monkeypatch):
    from test_continuous_motor_probe import fixture_setup
    runner, output, _, ph = fixture_setup(workspace, monkeypatch)
    module = adapter()
    monkeypatch.setattr(module, "_configuration", lambda: {"fixture": "non-neural"})
    evidence = workspace / "evidence"
    readiness = module.prepare(output, evidence, ph)
    readiness["version"] = "market-supervision/v1"
    (evidence / "readiness.json").write_text(json.dumps(readiness))
    monkeypatch.setattr(runner.FlyEngine, "from_prepared_graph", lambda: pytest.fail("invalid readiness constructed engine"))
    with pytest.raises(ValueError, match="supervision"):
        runner.run_probe(output, expected_protocol_sha256=ph, supervision_directory=evidence,
                         expected_readiness_sha256=digest(evidence / "readiness.json"), start_token="a" * 64)


def test_cli_exposes_only_fixed_supervision_parameters():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/continuous_motor_supervision.py"), "--help"],
                            capture_output=True, text=True, check=True, timeout=5)
    options = {word for word in result.stdout.split() if word.startswith("--")}
    assert {"--mode", "--output-directory", "--evidence-directory", "--expected-protocol-sha256",
            "--expected-readiness-sha256", "--owner-pid", "--owner-created"} <= options
    assert not any(word.startswith(("--command", "--test", "--limit", "--wall", "--memory", "--compiler")) for word in options)


@WINDOWS
@pytest.mark.parametrize("problem", ["creation", "foreign"])
def test_cli_rejects_wrong_owner_identity_before_creating_evidence(workspace, problem):
    module = adapter()
    owner = module.WindowsProcess(os.getpid())
    foreign = None
    try:
        identity = owner.identity()
        if problem == "creation":
            identity["creation_time_100ns"] += 1
        else:
            foreign = subprocess.Popen([sys._base_executable, "-c", "import time;time.sleep(60)"],
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            held = module.WindowsProcess(foreign.pid)
            try:
                identity = held.identity()
            finally:
                held.close()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/continuous_motor_supervision.py"),
            "--mode", "Prepare", "--output-directory", str(workspace / "absent"),
            "--evidence-directory", str(workspace / "evidence"), "--expected-protocol-sha256", "b" * 64,
            "--owner-pid", str(identity["pid"]), "--owner-created", str(identity["creation_time_100ns"])],
            capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode != 0 and "owner" in result.stderr
        assert not (workspace / "evidence").exists()
        if foreign:
            assert foreign.poll() is None
    finally:
        owner.close()
        if foreign:
            foreign.kill()
            foreign.wait(timeout=5)


@WINDOWS
def test_actual_runtime_binds_python_worker_cache_compiler_without_native_launch(workspace):
    module = adapter()
    if not (ROOT / "data/malecns-v1.0/runtime/cache/physiology-v6/memory.dll").is_file():
        pytest.skip("private prepared native cache unavailable")
    with module.compiler_probe_guard(["never-launch"]):
        config = module._configuration()
    legacy = config["legacy_runtime_configuration"]
    for name in ("python", "worker", "python_configuration", "native_source", "native_library", "native_metadata", "compiler", "helper"):
        record = legacy["files"][name]
        assert record["sha256"] == digest(Path(record["path"]))
    assert Path(legacy["files"]["worker"]["path"]) == Path(sys._base_executable)
    assert legacy["compiler_version_argv"] == [legacy["files"]["compiler"]["path"], "version"]
    assert legacy["files"]["helper"]["sha256"] == digest(ROOT / "scripts/market_supervision.py")
    from test_continuous_motor_probe import probe
    output, evidence = workspace / "actual-prepare", workspace / "actual-evidence"
    with module.compiler_probe_guard(["never-launch"]):
        probe().prepare_probe(output)
        readiness = module.prepare(output, evidence, digest(output / "protocol.json"))
        assert readiness["configuration"] == config
        module.validate_prepared(output, evidence, digest(output / "protocol.json"), digest(evidence / "readiness.json"))
    # The sole allowed child is the exact pinned version probe, never a build.
    with module.compiler_probe_guard(legacy["compiler_version_argv"]):
        version = subprocess.run(legacy["compiler_version_argv"], check=True, capture_output=True, text=True, timeout=5)
        assert version.stdout.strip() == "0.16.0"
        with pytest.raises(RuntimeError, match="process start"):
            subprocess.run([legacy["files"]["compiler"]["path"], "c++", str(workspace / "never.cpp")])


def wait_file(path, process=None, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_text())
        if process is not None and process.poll() is not None:
            pytest.fail(f"non-neural harness exited: {process.communicate()}")
        time.sleep(0.02)
    pytest.fail(f"bounded wait expired: {path}")


def frontend_fixture(workspace, monkeypatch, body):
    """Exact new frontend, real new public prepare/run/start, synthetic config only."""
    module = adapter()
    root = workspace / "fixture ; & $() workspace"
    (root / "scripts").mkdir(parents=True)
    (root / ".venv/Scripts").mkdir(parents=True)
    for relative in (".venv/Scripts/python.exe", ".venv/pyvenv.cfg", "scripts/supervise-continuous-motor.ps1"):
        shutil.copyfile(ROOT / relative, root / relative)
    site = root / ".venv/Lib/site-packages"
    site.mkdir(parents=True)
    (site / "test-existing.pth").write_text(str(ROOT / ".venv/Lib/site-packages") + "\n" + str(ROOT / "src") + "\n")
    child = root / "scripts/non-neural-child.py"
    config_path = root / "non-neural-config.json"
    files = {"python": module._file(ROOT / ".venv/Scripts/python.exe"),
             "worker": module._file(Path(sys._base_executable)),
             "compiler": {"path": str(Path(sys._base_executable))}}
    config = {"files": {"entrypoint": {"path": str(child)}}, "legacy_runtime_configuration": {
        "files": files, "data_directory": str(root),
        "compiler_version_argv": [str(Path(sys._base_executable)), "-c", "import time;time.sleep(60)"]}}
    config_path.write_text(json.dumps(config))
    prelude = (f"import sys,os,json,time,subprocess\nsys.path.insert(0,{str(ROOT / 'scripts')!r})\n"
               "from pathlib import Path\nimport continuous_motor_supervision as m\n"
               f"m._configuration=lambda:json.loads(Path({str(config_path)!r}).read_text())\n")
    child.write_text(prelude +
        "import argparse\np=argparse.ArgumentParser()\np.add_argument('run')\n"
        "for name in ('output-dir','expected-protocol-sha256','supervision-directory','expected-readiness-sha256','start-token'): p.add_argument('--'+name,required=True)\n"
        "p.add_argument('--run-native',action='store_true'); a=p.parse_args()\n"
        "output=Path(a.output_dir); evidence=Path(a.supervision_directory)\n"
        "with m.production_start(output,a.expected_protocol_sha256,evidence,a.expected_readiness_sha256,a.start_token):\n"
        + "\n".join(" " + line for line in body.splitlines()) + "\n", encoding="utf-8")
    (root / "scripts/continuous_motor_supervision.py").write_text(prelude + "raise SystemExit(m.main())\n", encoding="utf-8")
    output, evidence = root / "output", root / "evidence"
    output.mkdir()
    (output / "protocol.json").write_text(json.dumps({"version": "continuous-motor-probe/v1", "limits": FIXED}))
    monkeypatch.setattr(module, "_configuration", lambda: deepcopy(config))
    ph = digest(output / "protocol.json")
    module.prepare(output, evidence, ph)
    rh = digest(evidence / "readiness.json")
    command = [shutil.which("pwsh"), "-NoProfile", "-File", str(root / "scripts/supervise-continuous-motor.ps1"),
               "-Mode", "Run", "-OutputDirectory", str(output), "-EvidenceDirectory", str(evidence),
               "-ExpectedProtocolSha256", ph, "-ExpectedReadinessSha256", rh]
    return module, root, output, evidence, command


@WINDOWS
def test_new_public_frontend_completion_consumes_actual_synthetic_producer_receipt(workspace, tmp_path, monkeypatch):
    from test_continuous_motor_probe import execute
    producer = tmp_path / "synthetic-producer"
    producer.mkdir()
    _, produced, _, expected = execute(producer, monkeypatch)
    assert expected["status"] == "complete"
    body = f"import shutil\nshutil.copyfile({str(produced / 'receipt.json')!r},output/'receipt.json')"
    module, root, output, evidence, command = frontend_fixture(workspace, monkeypatch, body)
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, result.stderr
    receipt = wait_file(evidence / "supervisor-receipt.json")
    assert receipt["status"] == receipt["stop_reason"] == "completed", receipt
    assert receipt["job_active_processes_after_cleanup"] == 0
    assert json.loads((output / "receipt.json").read_text()) == expected
    assert receipt["worker"]["pid"] != receipt["launcher"]["pid"]
    assert receipt["observed_peak_working_set_bytes"] > 0
    assert receipt["owner"]["pid"] != receipt["supervisor"]["pid"]
    before = module._new_bytes(output, evidence)
    assert module.request_cancellation(evidence) is False
    assert module.request_cancellation(evidence) is False
    assert (evidence / "cancel.signal").read_bytes() == b"2"
    assert before == module._new_bytes(output, evidence) == receipt["observed_output_evidence_bytes"]


@WINDOWS
@pytest.mark.parametrize("interruption", ["cancel", "owner-death"])
def test_new_public_frontend_cleans_owned_tree_on_cancel_or_owner_death(workspace, monkeypatch, interruption):
    body = ("p=subprocess.Popen(m._configuration()['legacy_runtime_configuration']['compiler_version_argv'])\n"
            "m.write_json_exclusive({'pid':p.pid},evidence/'grandchild.json')\ntime.sleep(60)")
    module, root, output, evidence, command = frontend_fixture(workspace, monkeypatch, body)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    held = []
    try:
        supervisor = wait_file(evidence / "supervisor-ready.json", process)
        worker = wait_file(evidence / "worker-ready.json", process)
        child = wait_file(evidence / "grandchild.json", process)
        held = [module.WindowsProcess(record["pid"]) for record in (supervisor, worker, child)]
        started = time.monotonic()
        if interruption == "cancel":
            assert module.request_cancellation(evidence) is True
        else:
            process.kill()
        for owned in held:
            assert module._monitor.K.WaitForSingleObject(owned.handle, 5000) == 0, "owned process survived bounded cleanup"
        assert time.monotonic() - started < 6
        receipt = wait_file(evidence / "supervisor-receipt.json")
        assert receipt["status"] == "failed", receipt
        assert receipt["stop_reason"] == ("cancelled" if interruption == "cancel" else "owner-exited")
        assert receipt["job_active_processes_after_cleanup"] == 0
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
        for owned in held:
            owned.close()


@WINDOWS
def test_new_frontend_rejects_unrelated_ready_python_without_killing_it(workspace, monkeypatch):
    module, root, output, evidence, command = frontend_fixture(workspace, monkeypatch, "time.sleep(60)")
    foreign = subprocess.Popen([sys._base_executable, "-c", "import time;time.sleep(60)"], creationflags=subprocess.CREATE_NO_WINDOW)
    held = module.WindowsProcess(foreign.pid)
    identity = held.identity()
    helper = root / "scripts/continuous_motor_supervision.py"
    source = helper.read_text().replace("raise SystemExit(m.main())", "")
    helper.write_text(source +
        "def forged(output,evidence,ph,rh,*,owner):\n"
        f" ready={identity!r}\n"
        " ready.update(owner=owner.identity(),start_token='a'*64,protocol_sha256=ph,readiness_sha256=rh)\n"
        " m.write_json_exclusive(ready,evidence/'supervisor-ready.json')\n time.sleep(2)\n raise RuntimeError('non-neural forgery ends')\n"
        "m.run=forged\nraise SystemExit(m.main())\n")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode != 0
        assert not held.exited(), "foreign unvalidated Python was killed"
        assert not (evidence / "supervisor-ack.json").exists()
        module.write_json_exclusive({"foreign": identity, "foreign_survived": not held.exited(),
            "frontend_exit": result.returncode, "stderr": result.stderr}, root / "foreign-smoke.json")
    finally:
        if foreign.poll() is None:
            foreign.kill()
        foreign.wait(timeout=5)
        held.close()
