"""Bundle composition, genuine tiny-native baseline and declared mutation fixtures."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

import pytest

from fly_connectome_sim.experiment import feed_event_session as session
from fly_connectome_sim.experiment.recorder import RunArtifactError, VerifiedRun, _canonical, verify_run
from replay_helpers import engine_factory
from test_event_cards import example
from test_event_choice import rewrite
from test_video_observation import playlist


def test_workflow_module_exposes_both_commands():
    from fly_connectome_sim.experiment import session_workflow

    assert callable(session_workflow.run_session)
    assert callable(session_workflow.inspect_session)


@pytest.fixture(scope="module")
def genuine_bundle(tmp_path_factory):
    from fly_connectome_sim.experiment import session_workflow as workflow

    root = tmp_path_factory.mktemp("genuine-bundle")
    declaration, _ = playlist(root, count=1, frames=601)
    proposal = root / "options.json"
    proposal.write_bytes(_canonical(example()))
    calls = []
    native_factory = engine_factory.__wrapped__(root)
    def factory():
        calls.append("factory")
        engine = native_factory()
        def forbidden(*args, **kwargs):
            pytest.fail("Workflow reset or restored native state")
        engine.brain.reset = forbidden
        engine.brain.restore = forbidden
        return engine
    with pytest.MonkeyPatch.context() as patch:
        for name in ("record_feed_event_session", "export_session_replay", "export_session_plan"):
            original = getattr(session, name)
            def wrapped(*args, _name=name, _original=original, **kwargs):
                assert not (root / "bundle" / "receipt.json").exists()
                calls.append(_name)
                return _original(*args, **kwargs)
            patch.setattr(session, name, wrapped)
        summary = workflow.run_session(root / "bundle", playlist_path=declaration,
                                       proposal_path=proposal, engine_factory=factory)
    return root / "bundle", summary, calls


@pytest.fixture
def bundle(genuine_bundle, tmp_path):
    return Path(shutil.copytree(genuine_bundle[0], tmp_path / "bundle"))


def test_one_genuine_native_composition_receipt_and_summary(genuine_bundle):
    from fly_connectome_sim.experiment.session_workflow import inspect_session

    path, summary, calls = genuine_bundle
    assert calls == ["record_feed_event_session", "factory", "export_session_replay", "export_session_plan"]
    assert set(p.name for p in path.iterdir()) == {"run", "recording.json", "plan.json", "receipt.json"}
    assert summary == inspect_session(path)
    assert summary["status"] == "complete" and summary["verification_mode"] == "integrity-only"
    assert summary["plan_status"] == "deferred"
    assert summary["selected_option_id"] is summary["selected_title"] is None
    assert summary["duration_ticks"] == 60000 and summary["feed_end_tick"] == 40000
    assert summary["window_start_tick"] == 55000 and summary["window_end_tick"] == 60000
    assert summary["counts"] == {"motor_left": 0, "motor_right": 0}
    receipt = json.loads((path / "receipt.json").read_bytes())
    assert set(receipt) == {"version", "status", "source", "files"}
    assert receipt["version"] == "session-bundle/v1" and receipt["status"] == "complete"
    assert set(receipt["source"]) == {*session.cards.SOURCE_FIELDS, "verification_mode"}
    assert (path / "receipt.json").read_bytes() == _canonical(receipt) + b"\n"
    for name in ("recording.json", "plan.json"):
        raw = (path / name).read_bytes()
        assert receipt["files"][name] == {"size_bytes": len(raw), "sha256": sha256(raw).hexdigest()}


@pytest.mark.parametrize("failure", ["existing", "file", "missing-parent", "proposal", "playlist"])
def test_preflight_never_constructs_engine(tmp_path, failure):
    from fly_connectome_sim.experiment.session_workflow import run_session

    target = tmp_path / "bundle"
    if failure == "existing":
        target.mkdir()
    elif failure == "file":
        target.write_bytes(b"preserve")
    elif failure == "missing-parent":
        target = tmp_path / "absent" / "bundle"
    proposal = tmp_path / "options.json"
    proposal.write_bytes(_canonical(example()) if failure == "playlist" else b"invalid")
    calls = []
    def forbidden():
        calls.append(1)
        pytest.fail("Preflight constructed engine")
    with pytest.raises(RunArtifactError) as error:
        run_session(target, playlist_path=tmp_path / "absent.json", proposal_path=proposal,
                    engine_factory=forbidden)
    assert not calls and str(target) in str(error.value)
    assert error.value.__cause__ is not None
    if failure in {"proposal", "playlist"}:
        assert target.is_dir() and not list(target.iterdir())


@pytest.mark.parametrize("stage", ["record", "replay", "plan", "finalize", "receipt"])
def test_failures_retain_partials_and_do_not_retry(bundle, tmp_path, monkeypatch, stage):
    from fly_connectome_sim.experiment import session_workflow as workflow

    target = tmp_path / "partial"
    original_error = OSError("declared stage failure")
    calls = []
    def recorder(run, **kwargs):
        calls.append("record")
        if stage == "record":
            Path(run).mkdir()
            raise original_error
        shutil.copytree(bundle / "run", run)
        return verify_run(run)
    monkeypatch.setattr(session, "record_feed_event_session", recorder)
    def broken(*args, **kwargs):
        calls.append(stage)
        raise original_error
    if stage in {"replay", "plan"}:
        monkeypatch.setattr(session, "export_session_" + stage, broken)
    elif stage == "finalize":
        monkeypatch.setattr(workflow, "verify_run", broken)
    elif stage == "receipt":
        monkeypatch.setattr(workflow, "_publish_receipt", broken)
    with pytest.raises(RunArtifactError, match=stage) as error:
        workflow.run_session(target, playlist_path="fixture", proposal_path="fixture", engine_factory=lambda: None)
    assert error.value.__cause__ is original_error
    assert target.is_dir() and (target / "run").is_dir() and not (target / "receipt.json").exists()
    assert calls.count("record") == 1
    before = {str(p): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    with pytest.raises(RunArtifactError):
        workflow.run_session(target, playlist_path="fixture", proposal_path="fixture", engine_factory=lambda: None)
    assert before == {str(p): p.read_bytes() for p in target.rglob("*") if p.is_file()}
    assert calls.count("record") == 1


@pytest.mark.parametrize("mutation", ["missing", "truncated", "duplicate", "extra", "noncanonical", "hash", "bool-size"])
def test_receipt_corruption_rejected_without_repair(bundle, mutation):
    from fly_connectome_sim.experiment.session_workflow import inspect_session

    path = bundle / "receipt.json"
    value = json.loads(path.read_bytes())
    if mutation == "missing":
        path.unlink()
    elif mutation == "truncated":
        path.write_bytes(b'{"version":')
    elif mutation == "duplicate":
        path.write_bytes(b'{"status":"complete",' + _canonical(value)[1:] + b"\n")
    elif mutation == "noncanonical":
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    else:
        if mutation == "extra":
            value["attested"] = True
        elif mutation == "hash":
            value["files"]["plan.json"]["sha256"] = "0" * 64
        else:
            value["files"]["plan.json"]["size_bytes"] = True
        path.write_bytes(_canonical(value) + b"\n")
    before = {str(p): p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
    with pytest.raises(RunArtifactError):
        inspect_session(bundle)
    assert before == {str(p): p.read_bytes() for p in bundle.rglob("*") if p.is_file()}


@pytest.mark.parametrize("name,cap", [("receipt.json", 16 * 1024), ("recording.json", 32 * 1024 * 1024),
                                    ("plan.json", 64 * 1024)])
def test_cap_plus_one_before_json_or_raw_verification(bundle, monkeypatch, name, cap):
    from fly_connectome_sim.experiment import session_workflow as workflow

    with (bundle / name).open("wb") as output:
        output.write(b" " * (cap + 1))
    monkeypatch.setattr(workflow, "verify_run", lambda *args, **kwargs: pytest.fail("Oversize reached raw verify"))
    original = Path.open
    reads = []
    class Reader:
        def __init__(self, file):
            self.file = file
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return self.file.__exit__(*args)
        def read(self, size=-1):
            reads.append(size)
            assert size > 0
            return self.file.read(size)
    def tracked(path, *args, **kwargs):
        file = original(path, *args, **kwargs)
        return Reader(file) if path == bundle / name else file
    monkeypatch.setattr(Path, "open", tracked)
    with pytest.raises(RunArtifactError, match="bound"):
        workflow.inspect_session(bundle)
    assert reads == [cap + 1]


def test_rehashed_forged_exports_cannot_override_raw(bundle):
    from fly_connectome_sim.experiment.session_workflow import inspect_session

    receipt = json.loads((bundle / "receipt.json").read_bytes())
    plan = json.loads((bundle / "plan.json").read_bytes())
    replay = json.loads((bundle / "recording.json").read_bytes())
    plan["brief"]["title"] = "Forged title"
    replay["plan"] = plan
    for name, value in (("plan.json", plan), ("recording.json", replay)):
        raw = _canonical(value) + b"\n"
        (bundle / name).write_bytes(raw)
        receipt["files"][name] = {"size_bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    (bundle / "receipt.json").write_bytes(_canonical(receipt) + b"\n")
    with pytest.raises(RunArtifactError):
        inspect_session(bundle)


def test_actual_late_semantic_eof_error_blocks_inspection(bundle, monkeypatch):
    from fly_connectome_sim.experiment.session_workflow import inspect_session

    original = VerifiedRun.iter_events
    reached = []
    def late(self):
        yield from original(self)
        reached.append(True)
        raise OSError("genuine iterator late EOF")
    monkeypatch.setattr(VerifiedRun, "iter_events", late)
    with pytest.raises(RunArtifactError, match="late EOF") as error:
        inspect_session(bundle)
    assert reached and isinstance(error.value.__cause__, OSError)


def test_inspection_never_constructs_engine_network_or_writes(bundle, monkeypatch):
    import builtins
    import socket
    from fly_connectome_sim.engine import FlyEngine
    from fly_connectome_sim.experiment.session_workflow import inspect_session

    def forbidden(*args, **kwargs):
        pytest.fail("Inspection engine/network/write")
    original = builtins.open
    def read_only(*args, **kwargs):
        mode = args[1] if len(args) > 1 else kwargs.get("mode", "r")
        assert not any(flag in mode for flag in "wax+")
        return original(*args, **kwargs)
    monkeypatch.setattr(FlyEngine, "from_prepared_graph", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(builtins, "open", read_only)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(os, "rename", forbidden)
    monkeypatch.setattr(os, "link", forbidden)
    assert inspect_session(bundle)["status"] == "complete"


def _declared_selection(recording, target, chosen):
    """Resealed semantic fixture; selected counts are declared, not native results."""
    from dataclasses import asdict

    def mutate(event):
        if "event_choice" not in event:
            return
        name = session.cards.MOTOR_GROUPS[chosen]
        telemetry = event["telemetry"]
        telemetry["bins"][0]["group_spikes"][name] = 1
        telemetry["rates_hz"][name] = 2.0
        telemetry["turn_hz"] = -2.0 if chosen == 0 else 2.0
        telemetry["total_spikes"] += 1
        event["motor_readout"]["decision"] = asdict(session.cards.ADAPTER.adapt(telemetry))
        event["event_choice"]["selected_option_id"] = example()["options"][chosen]["id"]
    return rewrite(recording, target, mutate_event=mutate)


@pytest.mark.parametrize("chosen", [0, 1, None])
def test_declared_left_right_and_defer_preserve_exact_plan(bundle, tmp_path, monkeypatch, chosen):
    from fly_connectome_sim.experiment import session_workflow as workflow

    source = bundle / "run"
    if chosen is not None:
        source = _declared_selection(verify_run(source), tmp_path / "declared-selection", chosen)
    target = tmp_path / "declared-bundle"
    def recorder(run, **kwargs):
        shutil.copytree(source, run)
        return verify_run(run)
    monkeypatch.setattr(session, "record_feed_event_session", recorder)
    summary = workflow.run_session(target, playlist_path="fixture", proposal_path="fixture", engine_factory=lambda: None)
    plan = json.loads((target / "plan.json").read_bytes())
    assert plan["selected_option"] == (None if chosen is None else example()["options"][chosen])
    assert plan["brief"] == example()["brief"]
    assert summary["plan_status"] == ("deferred" if chosen is None else "selected")
    assert summary["selected_title"] == (None if chosen is None else example()["options"][chosen]["title"])
    assert summary == workflow.inspect_session(target)


def test_valid_source_a_to_b_swap_before_finalization_is_rejected(bundle, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import session_workflow as workflow

    # B is independently valid under the real raw/semantic verifier, with declared positive counts.
    source_b = _declared_selection(verify_run(bundle / "run"), tmp_path / "valid-b", 0)
    session._export_data(verify_run(source_b, limits=session.EXPORT_READ_LIMITS))
    target = tmp_path / "swapped"
    def recorder(run, **kwargs):
        shutil.copytree(bundle / "run", run)
        return verify_run(run)
    original = workflow._inspect
    def swap_then_inspect(path, **kwargs):
        # In-place replacement of this disposable fixture, never production cleanup/recovery.
        for source in source_b.rglob("*"):
            if source.is_file():
                shutil.copyfile(source, path / "run" / source.relative_to(source_b))
        # Replace both exports by genuine canonical B exports, not just forged hash claims.
        replay = session._export_data(verify_run(path / "run", limits=session.EXPORT_READ_LIMITS))
        (path / "recording.json").write_bytes(_canonical(replay) + b"\n")
        (path / "plan.json").write_bytes(_canonical(replay["plan"]) + b"\n")
        return original(path, **kwargs)
    monkeypatch.setattr(session, "record_feed_event_session", recorder)
    monkeypatch.setattr(workflow, "_inspect", swap_then_inspect)
    with pytest.raises(RunArtifactError, match="finalize.*source changed"):
        workflow.run_session(target, playlist_path="fixture", proposal_path="fixture", engine_factory=lambda: None)
    assert not (target / "receipt.json").exists()


def test_bool_int_permissive_export_plan_equality_is_rejected(bundle, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import session_workflow as workflow

    source = _declared_selection(verify_run(bundle / "run"), tmp_path / "declared-left", 0)
    def recorder(run, **kwargs):
        shutil.copytree(source, run)
        return verify_run(run)
    original = session.export_session_plan
    def untyped(run, output):
        plan = original(run, output)
        changed = deepcopy(plan)
        assert changed["selected_option"]["programme"][0]["start_minute"] == 0
        changed["selected_option"]["programme"][0]["start_minute"] = False
        assert changed == plan  # Python equality would silently accept this change.
        return changed
    monkeypatch.setattr(session, "record_feed_event_session", recorder)
    monkeypatch.setattr(session, "export_session_plan", untyped)
    target = tmp_path / "bool-plan"
    with pytest.raises(RunArtifactError, match="plan.*differs"):
        workflow.run_session(target, playlist_path="fixture", proposal_path="fixture", engine_factory=lambda: None)
    assert not (target / "receipt.json").exists()


@pytest.mark.parametrize("name", ["run", "receipt.json", "recording.json", "plan.json"])
def test_missing_or_nonregular_member_rejected_before_reads(bundle, monkeypatch, name):
    from fly_connectome_sim.experiment import session_workflow as workflow

    member = bundle / name
    if member.is_file():
        member.unlink()
        member.mkdir()
    else:
        member.rename(bundle / "retained-run")
        member.write_bytes(b"not a directory")
    monkeypatch.setattr(workflow, "_read", lambda *args: pytest.fail("Bad path reached bounded read"))
    with pytest.raises(RunArtifactError, match="nonregular"):
        workflow.inspect_session(bundle)


@pytest.mark.parametrize("left,right", [("receipt.json", "plan.json"), ("receipt.json", "recording.json"),
                                      ("plan.json", "recording.json")])
def test_pairwise_hardlink_alias_rejected_before_reads(bundle, monkeypatch, left, right):
    from fly_connectome_sim.experiment import session_workflow as workflow

    (bundle / right).unlink()
    try:
        os.link(bundle / left, bundle / right)
    except PermissionError as error:
        pytest.skip(f"Hardlink creation unavailable: {error}")
    monkeypatch.setattr(workflow, "_read", lambda *args: pytest.fail("Alias reached bounded read"))
    with pytest.raises(RunArtifactError, match="alias"):
        workflow.inspect_session(bundle)


def test_actual_junction_ancestor_rejected_before_factory_or_reads(bundle, tmp_path, monkeypatch):
    import subprocess
    from fly_connectome_sim.experiment import session_workflow as workflow

    if os.name != "nt":
        pytest.skip("Windows junction coverage")
    junction = tmp_path / "junction"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(bundle)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("Junction creation unavailable: " + result.stderr.strip())
    assert junction.is_junction()
    monkeypatch.setattr(workflow, "_read", lambda *args: pytest.fail("Junction reached read"))
    def forbidden():
        pytest.fail("Junction constructed engine")
    with pytest.raises(RunArtifactError, match="junction"):
        workflow.inspect_session(junction)
    with pytest.raises(RunArtifactError, match="junction"):
        workflow.run_session(junction / "new", playlist_path="fixture", proposal_path="fixture",
                             engine_factory=forbidden)
    assert not (bundle / "new").exists()


def test_receipt_publication_race_preserves_existing_receipt(bundle, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import session_workflow as workflow

    target = tmp_path / "receipt-race"
    def recorder(run, **kwargs):
        shutil.copytree(bundle / "run", run)
        return verify_run(run)
    monkeypatch.setattr(session, "record_feed_event_session", recorder)
    name = "rename" if os.name == "nt" else "link"
    original = getattr(os, name)
    def race(source, destination, *args, **kwargs):
        if Path(destination) == target / "receipt.json":
            Path(destination).write_bytes(b"preserve competing receipt")
        return original(source, destination, *args, **kwargs)
    monkeypatch.setattr(os, name, race)
    with pytest.raises(RunArtifactError, match="receipt"):
        workflow.run_session(target, playlist_path="fixture", proposal_path="fixture", engine_factory=lambda: None)
    assert (target / "receipt.json").read_bytes() == b"preserve competing receipt"
    assert (target / "recording.json").is_file() and (target / "plan.json").is_file()


def test_wrapper_additional_semantic_passes_are_bounded(bundle, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import session_workflow as workflow

    def recorder(run, **kwargs):
        shutil.copytree(bundle / "run", run)
        return verify_run(run)
    original = session._export_data
    def bounded(run):
        assert run._limits == session.EXPORT_READ_LIMITS, "Workflow added an unbounded raw pass"
        return original(run)
    monkeypatch.setattr(session, "record_feed_event_session", recorder)
    monkeypatch.setattr(session, "_export_data", bounded)
    result = workflow.run_session(tmp_path / "bounded", playlist_path="fixture", proposal_path="fixture",
                                  engine_factory=lambda: None)
    assert result["status"] == "complete"


def test_inspect_does_not_parse_a_second_full_replay(bundle, monkeypatch):
    from fly_connectome_sim.experiment import session_workflow as workflow

    original = workflow._strict_load
    def bounded_receipt(raw):
        assert len(raw) <= 16 * 1024, "Inspector added an unnecessary full replay decode"
        return original(raw)
    monkeypatch.setattr(workflow, "_strict_load", bounded_receipt)
    assert workflow.inspect_session(bundle)["status"] == "complete"
