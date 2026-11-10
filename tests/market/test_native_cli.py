"""Explicit native CLI safety/lifecycle checks; all launch edges are private fakes."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from market import native_protocol as protocol
from market.native_session import NativeConfig, PreparedNative
from test_native_protocol import INCARNATION, SESSION, DIGEST


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run-market-native-service.py"


def cli():
    spec = importlib.util.spec_from_file_location("native_cli_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_help_default_and_import_cannot_load_native_or_launch(tmp_path):
    bootstrap = r'''
import importlib.abc
import runpy
import subprocess
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("fly_connectome_sim", "market.native_session", "market.native_windows", "market.image_decode")):
            raise AssertionError("unexpected native dependency")
sys.meta_path.insert(0, Block())
def forbidden(*a, **kw):
    raise AssertionError("unexpected launch")
subprocess.Popen = forbidden
sys.argv = [sys.argv[1], *sys.argv[2:]]
runpy.run_path(sys.argv[0], run_name="__main__" if len(sys.argv) > 1 else "safe_import")
'''
    executable = getattr(sys, "_base_executable", sys.executable)
    for args, expected in (([], 0), (["--help"], 0), (["start", "--help"], 0)):
        result = subprocess.run([executable, "-c", bootstrap, str(SCRIPT), *args], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == expected, result.stderr
    module = cli()
    with pytest.raises(SystemExit) as error:
        module.main([])
    assert error.value.code == 2


@pytest.mark.parametrize("extra", [[], ["--allow-native-run"], ["--prepared-sha256", DIGEST]])
def test_start_requires_both_reviewed_digest_and_authorization_before_resources(extra, tmp_path):
    module = cli()
    with pytest.raises(SystemExit) as error:
        module.main(["start", "--work-root", str(tmp_path / "native"), "--config", "missing.json",
                     "--db", str(tmp_path / "price.sqlite3"), *extra])
    assert error.value.code == 2
    assert not list(tmp_path.iterdir())


def test_prepare_prints_exact_descriptor_digest_without_start(monkeypatch, tmp_path, capsys):
    module = cli()
    from market import native_session
    declaration = {"fixture": "source-declaration"}
    events = []
    class Session:
        def __init__(self, config, clock):
            self.config = config
        def prepare(self):
            events.append("prepared")
            return PreparedNative(dict(schema="market-native-prepared/v1", protocol_sha256=self.config.protocol_sha256,
                bindings_sha256=DIGEST, incarnation=self.config.incarnation, worker_session=self.config.worker_session))
        def start(self, *args, **kwargs):
            pytest.fail("prepare launched")
    monkeypatch.setattr(native_session, "current_protocol", lambda: declaration)
    monkeypatch.setattr(native_session, "NativeSession", Session)
    monkeypatch.setattr(module, "_check_platform", lambda: None)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / ".tools").mkdir()
    assert module.main(["prepare", "--work-root", str(tmp_path / ".tools/native")]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["prepared_sha256"] == protocol.canonical_sha256(output["prepared"])
    assert output["proof"] == "bounded-image20s/v1"
    assert events == ["prepared"]


def test_inspect_reports_integrity_only_and_never_constructs_session(monkeypatch, tmp_path, capsys):
    module = cli()
    called = []
    def inspect(root):
        called.append(root)
        return protocol.FrozenRecord(dict(completed_observations=40))
    monkeypatch.setattr(protocol, "inspect_evidence", inspect)
    assert module.main(["inspect", "--work-root", str(tmp_path)]) == 0
    assert called == [tmp_path]
    output = json.loads(capsys.readouterr().out)
    assert output["integrity_only"] is True
    assert output["final"]["completed_observations"] == 40


def test_unsupported_platform_is_closed_prerequisite_without_reflected_input(monkeypatch, tmp_path, capsys):
    module = cli()
    monkeypatch.setattr(module, "_check_platform", lambda: (_ for _ in ()).throw(ValueError("secret-token")))
    assert module.main(["prepare", "--work-root", str(tmp_path / "native")]) == 1
    output = capsys.readouterr()
    assert "secret-token" not in output.err
    assert not list(tmp_path.iterdir())

@pytest.fixture
def start_fixture(monkeypatch, tmp_path):
    module = cli()
    from market import native_session, image_decode, image_intake, local_server, price_service
    project = tmp_path / "project"
    tools = project / ".tools"
    root, decoder = tools / "native", tools / "native-decoder"
    root.mkdir(parents=True)
    decoder.mkdir()
    monkeypatch.setattr(module, "ROOT", project)
    monkeypatch.setattr(module, "_check_platform", lambda: None)
    config = NativeConfig(INCARNATION, SESSION, DIGEST, root)
    monkeypatch.setattr(module, "_read_prepared_config", lambda actual: config if actual == root else pytest.fail("wrong prepared root"))
    monkeypatch.setattr(local_server, "_load_assets", lambda *a, **kw: {})
    events, shared_clocks = [], []
    behavior = SimpleNamespace(start_fault=False, load_fault=False, cleanup_fault=False, interrupt=False,
                               native_fault=False, intake_fault=False, server_fault=False)
    class Session:
        def __init__(self, config, clock):
            self.config = config
            shared_clocks.append(clock)
            self.started = False
            self.closed = False
            events.append("session")
        def load_prepared(self, digest):
            assert digest == DIGEST
            events.append("load")
            if behavior.load_fault:
                raise protocol.ProtocolError("source")
            return "exact-reviewed-prepared-object"
        def start(self, prepared, *, allow_native_run):
            assert prepared == "exact-reviewed-prepared-object" and allow_native_run is True
            events.append("start")
            if behavior.start_fault:
                raise protocol.ProtocolError("source")
            self.started = True
        def snapshot(self):
            return SimpleNamespace(state="faulted" if behavior.native_fault else "ended", fault="protocol" if behavior.native_fault else None, cleanup_fault=None)
        def begin_stop(self, reason):
            assert reason == "shutdown"
            events.append("native-stop")
        def finish_receipts(self):
            events.append("receipt-close")
        def finish_close(self):
            assert not self.closed
            events.append("native-close")
            if behavior.cleanup_fault:
                raise protocol.ProtocolError("cleanup_failed")
            self.closed = True
    class Decoder:
        def __init__(self, path, clock):
            assert path == decoder
            shared_clocks.append(clock)
            self.closed = False
            events.append("decoder")
        def close(self):
            assert not self.closed
            self.closed = True
            events.append("decoder-close")
    class Authority:
        def __init__(self):
            self.closed = False
        def close(self):
            assert not self.closed
            self.closed = True
            events.append("authority-close")
    def authority(config, path, clock):
        assert path == project / "price.sqlite3"
        shared_clocks.append(clock)
        events.append("authority")
        return Authority()
    class Intake:
        def __init__(self, admission, actual_decoder, clock, *, native_session):
            if behavior.intake_fault:
                raise ValueError("private startup detail")
            assert admission.snapshot().incarnation == INCARNATION
            assert native_session.started
            self.session, self.decoder = native_session, actual_decoder
            shared_clocks.append(clock)
            events.append("intake")
        def begin_stop(self):
            events.append("intake-stop")
        def finish_close(self):
            self.session.finish_receipts()
            self.session.finish_close()
            self.decoder.close()
            events.append("intake-close")
    class Server:
        operator_url, view_url, guest_url = "operator-opening", "view-opening", "guest-opening"
        def __init__(self, actual_authority, host, port, assets, *, image_intake):
            if behavior.server_fault:
                raise ValueError("private bind detail")
            self.authority, self.intake = actual_authority, image_intake
            self.stopped = __import__("threading").Event()
            events.append("server")
        def serve_forever(self):
            events.append("serve")
            if behavior.interrupt:
                raise KeyboardInterrupt()
            assert self.stopped.wait(4), "CLI did not stop for native end/fault"
        def shutdown(self):
            events.append("shutdown")
            self.stopped.set()
        def server_close(self):
            events.append("server-close")
            self.intake.begin_stop()
            try:
                self.authority.close()
            finally:
                self.intake.finish_close()
    monkeypatch.setattr(native_session, "NativeSession", Session)
    monkeypatch.setattr(image_decode, "ImageDecoder", Decoder)
    monkeypatch.setattr(image_intake, "ImageIntake", Intake)
    monkeypatch.setattr(price_service, "open_authority", authority)
    monkeypatch.setattr(local_server, "create_server", Server)
    args = ["start", "--work-root", str(root), "--prepared-sha256", DIGEST, "--allow-native-run",
            "--config", str(ROOT / "examples/market-synthetic.json"), "--db", str(project / "price.sqlite3")]
    return module, args, behavior, events, shared_clocks


@pytest.mark.parametrize("interrupt", [False, True])
def test_start_shares_clock_and_incarnation_and_closes_each_owner_once(start_fixture, interrupt, capsys):
    module, args, behavior, events, clocks = start_fixture
    behavior.interrupt = interrupt
    assert module.main(args) == 0
    assert len(clocks) == 4 and all(value is clocks[0] for value in clocks)
    assert events.index("load") < events.index("decoder") < events.index("start") < events.index("intake")
    assert events.count("native-close") == events.count("decoder-close") == events.count("authority-close") == 1
    assert events.count("receipt-close") == 1
    assert not module._unclosed_owners
    assert "Synthetische Preise" in capsys.readouterr().out


@pytest.mark.parametrize("phase", ["load", "start"])
def test_invalid_prepared_or_prelaunch_failure_never_serves_or_retries(start_fixture, phase, capsys):
    module, args, behavior, events, clocks = start_fixture
    setattr(behavior, phase + "_fault", True)
    assert module.main(args) == 1
    assert "serve" not in events
    assert events.count("start") == (1 if phase == "start" else 0)
    assert events.count("native-close") == (1 if phase == "start" else 0)
    assert not module._unclosed_owners
    output = capsys.readouterr()
    assert "operator-opening" not in output.out
    assert "source" in output.err


def test_native_fault_stops_service_and_returns_failure(start_fixture):
    module, args, behavior, events, clocks = start_fixture
    behavior.native_fault = True
    assert module.main(args) == 1
    assert events.count("shutdown") == 1
    assert events.count("native-close") == 1


def test_cleanup_failure_retains_exact_owner_and_fences_later_start(start_fixture, capsys):
    module, args, behavior, events, clocks = start_fixture
    behavior.interrupt = behavior.cleanup_fault = True
    assert module.main(args) == 1
    owners = module._unclosed_owners
    assert len(owners) == 1 and owners[0].intake.session.closed is False
    assert module.main(args) == 1
    assert module._unclosed_owners is owners
    assert events.count("start") == events.count("native-close") == 1
    assert "cleanup_failed" in capsys.readouterr().err


def test_fresh_database_and_decoder_checks_precede_launch(start_fixture):
    module, args, behavior, events, clocks = start_fixture
    db = Path(args[args.index("--db") + 1])
    db.write_bytes(b"existing operator data")
    assert module.main(args) == 1
    assert events == []
    assert db.read_bytes() == b"existing operator data"


def test_control_reader_rejects_duplicate_keys_and_oversized_input(tmp_path):
    module = cli()
    path = tmp_path / "control.json"
    path.write_bytes(b'{"incarnation": 1, "incarnation": 2}')
    with pytest.raises(ValueError):
        module._control(path)
    path.write_bytes(b" " * 1048577)
    with pytest.raises(ValueError):
        module._control(path)


@pytest.mark.parametrize("phase", ["intake", "server"])
def test_failure_after_release_cleans_exact_resources_before_return(start_fixture, phase, capsys):
    module, args, behavior, events, clocks = start_fixture
    setattr(behavior, phase + "_fault", True)
    assert module.main(args) == 1
    assert events.count("native-close") == events.count("decoder-close") == events.count("authority-close") == 1
    assert "serve" not in events and not module._unclosed_owners
    output = capsys.readouterr()
    assert "private" not in output.err
    assert "operator-opening" not in output.out


def test_nonempty_decoder_is_not_reused(start_fixture):
    module, args, behavior, events, clocks = start_fixture
    root = Path(args[args.index("--work-root") + 1])
    (root.parent / "native-decoder/previous-evidence").write_bytes(b"retained")
    assert module.main(args) == 1
    assert events == []


@pytest.mark.skipif(sys.platform != "win32", reason="native controls require Windows absolute path semantics")
def test_strict_controls_construct_public_config_and_exact_load_digest(monkeypatch, tmp_path):
    from market import native_session
    from test_native_evidence import prepared_fixtures
    module = cli()
    declaration, bindings = prepared_fixtures()
    def relocate(value):
        if type(value) is str:
            return value.replace("C:\\project", str(ROOT))
        if type(value) is list:
            return [relocate(item) for item in value]
        if type(value) is dict:
            return {key: relocate(item) for key, item in value.items()}
        return value
    bindings = relocate(bindings)
    root = tmp_path / "native"
    root.mkdir()
    (root / "scratch").mkdir()
    bindings.update(work_root=str(root), decoder_work_root=str(root.parent / "native-decoder"))
    bindings["environment"].update(TMP=str(root / "scratch"), TEMP=str(root / "scratch"))
    bindings["compiler_probe"]["environment_sha256"] = protocol.canonical_sha256(bindings["environment"])
    (root / "protocol.json").write_bytes(protocol.canonical_bytes(declaration))
    (root / "bindings.json").write_bytes(protocol.canonical_bytes(bindings))
    config = module._read_prepared_config(root)
    assert config.incarnation == INCARNATION and config.worker_session == SESSION and config.work_root == root
    prepared = PreparedNative(dict(schema="market-native-prepared/v1", incarnation=INCARNATION,
        worker_session=SESSION, protocol_sha256=protocol.canonical_sha256(declaration),
        bindings_sha256=protocol.canonical_sha256(bindings)))
    monkeypatch.setattr(native_session, "current_protocol", lambda: protocol.FrozenRecord(declaration))
    from conftest import FakeClock
    value = native_session.NativeSession(config, FakeClock())
    actual = value.load_prepared(protocol.canonical_sha256(prepared))
    assert actual == prepared
    assert {item.name for item in root.iterdir()} == {"protocol.json", "bindings.json", "scratch"}
    with pytest.raises(ValueError, match="source"):
        native_session.NativeSession(config, FakeClock()).load_prepared("f" * 64)
    (root / "bindings.json").write_bytes(protocol.canonical_bytes(bindings) + b"\n")
    with pytest.raises(ValueError):
        module._read_prepared_config(root)


def test_unsafe_work_root_does_not_even_read_prepare_sources(monkeypatch, tmp_path):
    module = cli()
    from market import native_session
    monkeypatch.setattr(module, "_check_platform", lambda: None)
    def forbidden():
        pytest.fail("unsafe path reached source declaration")
    monkeypatch.setattr(native_session, "current_protocol", forbidden)
    assert module.main(["prepare", "--work-root", str(tmp_path / "native")]) == 1


def test_live_start_prints_only_bound_profile_and_measured_price_labels(start_fixture,monkeypatch,capsys):
    from dataclasses import replace
    from market import price_service,local_server,native_price
    module,args,behavior,events,clocks=start_fixture
    root=Path(args[args.index('--work-root')+1])
    module._read_prepared_config=lambda actual:NativeConfig(INCARNATION,SESSION,DIGEST,root,
        profile='live-pilot/v1',duration_minutes=90,max_observations=120)
    original_authority=price_service.open_authority
    def authority(*args,mode):
        assert mode=='native'
        return original_authority(*args)
    original_server=local_server.create_server
    def server(*args,native_prices,**kwargs):
        assert native_prices=='enabled-native-feed'
        return original_server(*args,**kwargs)
    monkeypatch.setattr(price_service,'open_authority',authority)
    monkeypatch.setattr(local_server,'create_server',server)
    monkeypatch.setattr(native_price,'NativePricePump',lambda *args,**kwargs:'enabled-native-feed')
    behavior.interrupt=True
    assert module.main(args)==0
    output=capsys.readouterr().out
    assert 'live-pilot/v1' in output and '120' in output and '90' in output
    assert 'Experimentelle neuronale Preissteuerung' in output
    assert '40 Beobachtungen' not in output and '20 Modellsekunden' not in output
    assert '900 reale Sekunden' not in output and 'Synthetische Preise' not in output
