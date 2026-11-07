"""The event plan is a complete sealed count-derived pilot reduction."""

from copy import deepcopy
from hashlib import sha256
import json
import os

import pytest

from replay_helpers import engine_factory
from test_event_cards import example


@pytest.fixture
def proposal_path(tmp_path):
    path = tmp_path / "options.json"
    path.write_text(json.dumps(example()), encoding="utf-8")
    return path


@pytest.mark.parametrize("left,right,population,action", [
    (0, 0, 2, "defer"), (2, 2, 2, "defer"), (0, 1, 2, "defer"),
    (1, 0, 2, "defer"), (0, 2, 2, "inspect_right"), (2, 0, 2, "inspect_left"),
    (0, 1, 3, "defer"), (0, 2, 3, "inspect_right"),
])
def test_final_choice_uses_counts_and_exact_half_second(left, right, population, action):
    from fly_connectome_sim.experiment.event_choice import count_readout

    decision = count_readout({"motor_left": left, "motor_right": right},
                             {"motor_left": population, "motor_right": population})
    assert decision["action"] == action
    assert decision["signed_difference_hz"] == right / (population * .5) - left / (population * .5)


@pytest.fixture
def recording(tmp_path, proposal_path, engine_factory):
    from fly_connectome_sim.experiment.event_choice import record_event_choice_run

    return record_event_choice_run(tmp_path / "event-run", proposal_path=proposal_path,
                                   engine_factory=engine_factory)


def test_genuine_native_deferred_roundtrip_is_bound_to_final_event(recording, tmp_path):
    from fly_connectome_sim.experiment.event_choice import export_event_plan, export_event_replay

    replay = export_event_replay(recording.path, tmp_path / "replay.json")
    plan = export_event_plan(recording.path, tmp_path / "plan.json")
    events = list(recording.iter_events())
    assert [e["type"] for e in events] == ["checkpoint", *(["observe"] * 4), "checkpoint"]
    assert [e["end_tick"] for e in events[1:5]] == [5000, 10000, 15000, 20000]
    assert all("motor_readout" not in e and "event_choice" not in e for e in events[:4])
    assert events[4]["motor_readout"]["decision"]["action"] == "defer"
    assert replay["decision"]["event_sequence"] == 4
    assert replay["decision"]["event_scientific_sha256"] == events[4]["scientific_sha256"]
    assert replay["decision"]["counts"] == {"motor_left": 0, "motor_right": 0}
    assert replay["duration_ticks"] == 20000 and len(replay["segments"]) == 4
    assert sum(len(s["bins"]) for s in replay["segments"]) == 200
    assert replay["plan"] == plan
    assert plan["status"] == "deferred" and plan["selected_option"] is None
    assert plan["selected_option_id"] is None
    assert set(plan["source"]) == {"run_kind", "schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256", "verification_mode"}
    assert json.loads((tmp_path / "replay.json").read_text()) == replay
    assert json.loads((tmp_path / "plan.json").read_text()) == plan


@pytest.mark.parametrize("export_name", ["export_event_replay", "export_event_plan"])
@pytest.mark.parametrize("field", ["max_manifest_bytes", "max_event_line_bytes", "max_events_bytes",
                                  "max_events", "max_checkpoints"])
def test_export_intake_limits_reject_before_temporary_output(recording, tmp_path, monkeypatch,
                                                            export_name, field):
    from dataclasses import replace
    from fly_connectome_sim.experiment import event_choice
    from fly_connectome_sim.experiment.recorder import RunArtifactError, verify_run

    policy = event_choice.EXPORT_READ_LIMITS
    assert (policy.max_manifest_bytes, policy.max_event_line_bytes, policy.max_events_bytes,
            policy.max_events, policy.max_checkpoints) == (2 * 1024 * 1024, 1024 * 1024,
                                                          8 * 1024 * 1024, 6, 2)
    raw = (recording.path / "events.jsonl").read_bytes()
    sizes = dict(max_manifest_bytes=len((recording.path / "run.json").read_bytes()),
                 max_event_line_bytes=max(map(len, raw.splitlines(keepends=True))),
                 max_events_bytes=len(raw), max_events=6, max_checkpoints=2)
    monkeypatch.setattr(event_choice, "EXPORT_READ_LIMITS", replace(policy, **{field: sizes[field] - 1}))
    monkeypatch.setattr(event_choice.tempfile, "NamedTemporaryFile",
                        lambda *args, **kwargs: pytest.fail("Over-limit source reached publication"))
    output = tmp_path / "not-published.json"
    with pytest.raises(RunArtifactError, match="limit"):
        getattr(event_choice, export_name)(recording.path, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".event-export-*"))
    assert len(list(verify_run(recording.path).iter_events())) == 6


def test_invalid_proposal_precedes_engine_and_output(tmp_path, proposal_path):
    from fly_connectome_sim.experiment.event_choice import record_event_choice_run

    proposal_path.write_text('{"selected_option_id":"forced"}', encoding="utf-8")
    def forbidden():
        pytest.fail("invalid input constructed engine")
    with pytest.raises(ValueError):
        record_event_choice_run(tmp_path / "bad", proposal_path=proposal_path, engine_factory=forbidden)
    assert not (tmp_path / "bad").exists()


def rewrite(recording, target, *, mutate_event=None, mutate_metadata=None, drop_sequence=None, extra=False):
    """Reseal declared test mutations; these are not native-history attestations."""
    from fly_connectome_sim.experiment.recorder import OWNED, RunRecorder

    metadata = deepcopy(recording.manifest["metadata"])
    if mutate_metadata:
        mutate_metadata(metadata)
    with RunRecorder(target, run_kind="pilot", metadata=metadata,
                     root_branch_id=recording.manifest["root_branch_id"]) as recorder:
        for original in recording.iter_events():
            if original["sequence"] == drop_sequence:
                continue
            event = {key: deepcopy(value) for key, value in original.items() if key not in OWNED}
            if "telemetry" in event:
                event["telemetry"]["engine_identity"] = deepcopy(metadata["engine_identity"])
            if mutate_event:
                mutate_event(event)
            if "checkpoint_name" in event:
                recorder.ingest_checkpoint(event["checkpoint_name"],
                                           recording.path / "checkpoints" / event["checkpoint_name"],
                                           origin_branch_id=event["branch_id"])
            recorder.append(event)
        if extra:
            recorder.append({"type": "unsupported-operation", "branch_id": recording.manifest["root_branch_id"],
                             "sim_ms": 2000.0})
    return target


@pytest.mark.parametrize("mutation", [
    "claimed-choice", "pixel", "pixel-hash", "event-extra", "early-readout", "missing-readout",
    "clock", "off-lattice", "bin-gap", "bin-overflow", "bool-count", "missing-population",
    "raw-rate", "near-zero-drift", "turn", "detail", "learning", "stimulation", "operation",
    "branch", "checkpoint-clock", "unknown-telemetry", "no-bins",
])
def test_resealed_semantic_mutations_never_publish(recording, tmp_path, mutation):
    from fly_connectome_sim.experiment.event_choice import export_event_plan, export_event_replay

    def mutate(event):
        if mutation == "checkpoint-clock" and event["type"] == "checkpoint":
            event["sim_tick"] += 1
        if event["type"] != "observe":
            return
        telemetry = event["telemetry"]
        if mutation == "claimed-choice" and event["end_tick"] == 20000:
            event["event_choice"]["selected_option_id"] = "sunset-house"
        elif mutation == "pixel":
            raw = event["event_frame"]["rgb_base64"]
            event["event_frame"]["rgb_base64"] = ("B" if raw[0] != "B" else "C") + raw[1:]
        elif mutation == "pixel-hash":
            event["event_frame"]["sha256"] = "0" * 64
        elif mutation == "event-extra":
            event["selected_option_id"] = "sunset-house"
        elif mutation == "early-readout" and event["end_tick"] != 20000:
            event["event_choice"] = {"policy_version": "event-card-choice/v1", "selected_option_id": None}
        elif mutation == "missing-readout" and event["end_tick"] == 20000:
            event.pop("event_choice")
        elif mutation == "clock":
            event["start_tick"] += 1
        elif mutation == "off-lattice":
            event["start_ms"] += 0.000001
        elif mutation == "bin-gap":
            telemetry["bins"][0]["duration_ms"] = 9.9
        elif mutation == "bin-overflow":
            telemetry["bins"][0]["group_spikes"]["motor_left"] = 101
        elif mutation == "bool-count":
            telemetry["bins"][0]["group_spikes"]["motor_left"] = True
        elif mutation == "missing-population":
            telemetry["bins"][0]["group_spikes"].pop("motor_left")
        elif mutation == "raw-rate":
            telemetry["rates_hz"]["kc"] += 1
        elif mutation == "near-zero-drift":
            telemetry["rates_hz"]["motor_left"] = 1e-13
            telemetry["turn_hz"] = telemetry["rates_hz"]["motor_right"] - 1e-13
            if event["end_tick"] == 20000:
                from dataclasses import asdict
                from fly_connectome_sim.experiment.adapter import LateralMotorAdapter
                event["motor_readout"]["decision"] = asdict(LateralMotorAdapter().adapt(telemetry))
        elif mutation == "turn":
            telemetry["turn_hz"] = 1
        elif mutation == "detail":
            event["pathway_detail"] = True
        elif mutation == "learning":
            event["learning"] = telemetry["learning"] = True
        elif mutation == "stimulation":
            event["stimulation"] = "ppl101"
        elif mutation == "operation":
            event["type"] = "unsupported-operation"
        elif mutation == "branch":
            event["branch_id"] = "event-choice/other"
        elif mutation == "unknown-telemetry":
            telemetry["arbitrary"] = "unrecognised"
        elif mutation == "no-bins":
            telemetry["bins"] = []

    for exporter in (export_event_replay, export_event_plan):
        output = tmp_path / (exporter.__name__ + ".json")
        with pytest.raises(ValueError):
            source = rewrite(recording, tmp_path / exporter.__name__, mutate_event=mutate)
            exporter(source, output)
        assert not output.exists()


@pytest.mark.parametrize("mutation", ["proposal", "hash", "mapping", "recipe", "renderer", "unknown", "source", "identity", "population"])
def test_resealed_metadata_drift_is_rejected(recording, tmp_path, mutation):
    from fly_connectome_sim.experiment.event_choice import export_event_replay

    def mutate(metadata):
        if mutation == "proposal":
            metadata["proposal"]["options"][0]["title"] = "Different title"
        elif mutation == "hash":
            metadata["proposal_sha256"] = "0" * 64
        elif mutation == "mapping":
            metadata["factors"]["left_option_id"] = metadata["factors"]["right_option_id"]
        elif mutation == "recipe":
            metadata["choice_recipe"]["action_threshold_hz"] = 0
        elif mutation == "renderer":
            metadata["renderer_recipe"]["font_size"] = 13
        elif mutation == "unknown":
            metadata["selected_option_id"] = "sunset-house"
        elif mutation == "source":
            metadata["proposal_source"]["kind"] = "live-api"
        elif mutation == "identity":
            metadata["engine_identity"]["sha256"] = "0" * 64
        else:
            metadata["engine_identity"]["neural_groups"]["motor_left"] = []

    output = tmp_path / "bad.json"
    with pytest.raises(ValueError):
        source = rewrite(recording, tmp_path / "mutated", mutate_metadata=mutate)
        export_event_replay(source, output)
    assert not output.exists()


@pytest.mark.parametrize("action,chosen", [("inspect_left", 0), ("inspect_right", 1)])
def test_declared_count_fixture_locks_exact_selected_proposal(recording, tmp_path, action, chosen):
    """Positive mapping fixtures are explicitly resealed counts, not native winners."""
    from dataclasses import asdict
    from fly_connectome_sim.experiment.adapter import LateralMotorAdapter
    from fly_connectome_sim.experiment.event_choice import export_event_plan, export_event_replay

    def mutate(event):
        if event.get("end_tick") != 20000:
            return
        name = "motor_left" if chosen == 0 else "motor_right"
        telemetry = event["telemetry"]
        telemetry["bins"][0]["group_spikes"][name] = 1
        telemetry["rates_hz"][name] = 2.0
        telemetry["turn_hz"] = -2.0 if chosen == 0 else 2.0
        telemetry["total_spikes"] += 1
        event["motor_readout"]["decision"] = asdict(LateralMotorAdapter().adapt(telemetry))
        event["event_choice"]["selected_option_id"] = example()["options"][chosen]["id"]

    source = rewrite(recording, tmp_path / "declared-count-fixture", mutate_event=mutate)
    replay = export_event_replay(source, tmp_path / "fixture-replay.json")
    plan = export_event_plan(source, tmp_path / "fixture-plan.json")
    assert replay["decision"]["readout"]["action"] == action
    assert replay["plan"] == plan
    assert plan["status"] == "selected"
    assert plan["selected_option"] == example()["options"][chosen]
    assert plan["brief"] == example()["brief"]


@pytest.mark.parametrize("delta", [-1e-13, 1e-13])
def test_resealed_near_strict_threshold_drift_cannot_change_choice(recording, tmp_path, delta):
    from dataclasses import asdict
    from fly_connectome_sim.experiment.adapter import LateralMotorAdapter
    from fly_connectome_sim.experiment.event_choice import export_event_replay

    def metadata(value):
        # Explicit declared map/count fixture: population two makes one spike exactly1Hz.
        identity = value["engine_identity"]
        identity["neural_groups"]["motor_right"] = [2, 3]
        payload = {k: v for k, v in identity.items() if k != "sha256"}
        identity["sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def mutate(event):
        if event.get("end_tick") != 20000:
            return
        telemetry = event["telemetry"]
        telemetry["bins"][0]["group_spikes"]["motor_right"] = 1
        telemetry["rates_hz"]["motor_right"] = 1.0 + delta
        telemetry["turn_hz"] = 1.0 + delta
        telemetry["total_spikes"] += 1
        event["motor_readout"]["decision"] = asdict(LateralMotorAdapter().adapt(telemetry))
        event["event_choice"]["selected_option_id"] = "warehouse-techno" if delta > 0 else None

    source = rewrite(recording, tmp_path / "threshold-fixture", mutate_event=mutate, mutate_metadata=metadata)
    with pytest.raises(ValueError, match="count-derived"):
        export_event_replay(source, tmp_path / "bad.json")
    assert not (tmp_path / "bad.json").exists()


@pytest.mark.parametrize("drop_sequence,extra", [(4, False), (5, False), (None, True)])
def test_missing_interval_premature_seal_and_extra_operations_fail(recording, tmp_path, drop_sequence, extra):
    from fly_connectome_sim.experiment.event_choice import export_event_plan

    with pytest.raises(ValueError):
        source = rewrite(recording, tmp_path / "bad-source", drop_sequence=drop_sequence, extra=extra)
        export_event_plan(source, tmp_path / "bad.json")
    assert not (tmp_path / "bad.json").exists()


@pytest.mark.parametrize("export_name", ["export_event_replay", "export_event_plan"])
def test_each_export_finishes_normal_eof_before_publication(recording, tmp_path, monkeypatch, export_name):
    from fly_connectome_sim.experiment import event_choice
    from fly_connectome_sim.experiment.recorder import VerifiedRun

    output = tmp_path / "bad.json"
    original = VerifiedRun.iter_events
    def failing(self):
        yield from original(self)
        assert not output.exists()
        raise OSError("test EOF failure")
    monkeypatch.setattr(VerifiedRun, "iter_events", failing)
    with pytest.raises(OSError, match="EOF failure"):
        getattr(event_choice, export_name)(recording.path, output)
    assert not output.exists()


def test_export_never_modifies_source_or_overwrites(recording, tmp_path):
    from fly_connectome_sim.experiment.event_choice import export_event_plan, export_event_replay

    before = {str(p): sha256(p.read_bytes()).hexdigest() for p in recording.path.rglob("*") if p.is_file()}
    output = tmp_path / "preserve.json"
    output.write_bytes(b"preserve")
    for exporter in (export_event_replay, export_event_plan):
        with pytest.raises(FileExistsError):
            exporter(recording.path, output)
        with pytest.raises(ValueError):
            exporter(recording.path, recording.path / "export.json")
        exporter(recording.path, tmp_path / (exporter.__name__ + ".json"))
    assert output.read_bytes() == b"preserve"
    assert before == {str(p): sha256(p.read_bytes()).hexdigest() for p in recording.path.rglob("*") if p.is_file()}


def test_exclusive_publication_race_preserves_concurrent_writer(recording, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment.event_choice import export_event_plan

    output = tmp_path / "race.json"
    name = "rename" if os.name == "nt" else "link"
    publish = getattr(os, name)
    def race(source, target):
        output.write_bytes(b"concurrent writer")
        return publish(source, target)
    monkeypatch.setattr(os, name, race)
    with pytest.raises(FileExistsError):
        export_event_plan(recording.path, output)
    assert output.read_bytes() == b"concurrent writer"
    assert not list(tmp_path.glob(".event-export-*"))


def test_producer_uses_same_actual_image_and_fixed_flags(tmp_path, proposal_path, engine_factory):
    import numpy as np
    from fly_connectome_sim.experiment.event_cards import render_event_cards
    from fly_connectome_sim.experiment.event_choice import record_event_choice_run

    calls = []
    def factory():
        engine = engine_factory()
        observe = engine.observe
        def capture(frame, duration_ms, **flags):
            calls.append((frame.copy(), duration_ms, flags, engine.brain.weights_frozen))
            return observe(frame, duration_ms, **flags)
        engine.observe = capture
        return engine
    result = record_event_choice_run(tmp_path / "run", proposal_path=proposal_path, engine_factory=factory)
    assert result.manifest["event_count"] == 6 and len(calls) == 4
    for frame, duration, flags, frozen in calls:
        np.testing.assert_array_equal(frame, render_event_cards(example()))
        assert duration == 500.0 and frozen is False
        assert flags == {"stimulation": None, "learning": False, "pathway_detail": False, "qualification_detail": False}


@pytest.mark.parametrize("failure", ["render", "existing", "file-parent"])
def test_preflight_failures_never_construct_engine(tmp_path, proposal_path, monkeypatch, failure):
    from fly_connectome_sim.experiment import event_choice

    output = tmp_path / "run"
    if failure == "render":
        def broken(proposal):
            raise ValueError("renderer unavailable")
        monkeypatch.setattr(event_choice, "render_event_cards", broken)
    elif failure == "existing":
        output.mkdir()
    else:
        parent = tmp_path / "file"
        parent.write_text("preserve")
        output = parent / "run"
    def forbidden():
        pytest.fail("invalid render/path constructed engine")
    with pytest.raises((ValueError, OSError)):
        event_choice.record_event_choice_run(output, proposal_path=proposal_path, engine_factory=forbidden)


@pytest.mark.parametrize("bad", [True, -1, 0.5, "1", None])
def test_count_policy_rejects_noninteger_and_negative_counts(bad):
    from fly_connectome_sim.experiment.event_choice import count_readout

    with pytest.raises(ValueError):
        count_readout({"motor_left": bad, "motor_right": 0}, {"motor_left": 1, "motor_right": 1})


@pytest.mark.parametrize("bad", [True, 0, -1, 1.5, "1"])
def test_count_policy_requires_positive_integer_populations(bad):
    from fly_connectome_sim.experiment.event_choice import count_readout

    with pytest.raises(ValueError):
        count_readout({"motor_left": 0, "motor_right": 0}, {"motor_left": bad, "motor_right": 1})


@pytest.mark.parametrize("state", ["frozen", "advanced", "wrong-dt", "not-engine"])
def test_producer_rejects_nonfresh_or_synthetic_engines(tmp_path, proposal_path, engine_factory, state):
    from fly_connectome_sim.experiment.event_choice import record_event_choice_run

    def factory():
        if state == "not-engine":
            return object()
        engine = engine_factory()
        if state == "frozen":
            engine.brain.weights_frozen = True
        elif state == "advanced":
            engine.brain.cursor = 1
        else:
            engine.brain.dt = 1.0
        return engine
    output = tmp_path / "bad-engine"
    with pytest.raises(ValueError, match="fresh actual"):
        record_event_choice_run(output, proposal_path=proposal_path, engine_factory=factory)
    assert not output.exists()


def test_producer_rejects_raw_count_drift_without_rewriting_or_sealing(tmp_path, proposal_path, engine_factory):
    from fly_connectome_sim.experiment.event_choice import record_event_choice_run

    raw_results = []
    def factory():
        engine = engine_factory()
        observe = engine.observe
        def drift(frame, duration_ms, **flags):
            telemetry = observe(frame, duration_ms, **flags)
            if telemetry["sim_ms"] == 2000:
                telemetry["rates_hz"]["motor_right"] = 1e-13
                telemetry["turn_hz"] = 1e-13
                raw_results.append(telemetry)
            return telemetry
        engine.observe = drift
        return engine
    output = tmp_path / "drift"
    with pytest.raises(ValueError, match="count-derived"):
        record_event_choice_run(output, proposal_path=proposal_path, engine_factory=factory)
    assert raw_results[0]["rates_hz"]["motor_right"] == 1e-13
    assert not (output / "run.json").exists()
