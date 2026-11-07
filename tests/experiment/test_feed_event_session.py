"""Continuous genuine tiny-native session and declared semantic mutations."""

from copy import deepcopy
from hashlib import sha256
import json
import os

import numpy as np
import pytest

from replay_helpers import engine_factory, map_engine_factory
from test_event_cards import example
from test_event_choice import rewrite
from test_video_observation import playlist


@pytest.fixture
def inputs(tmp_path):
    declaration, _ = playlist(tmp_path, count=1, frames=601)
    proposal = tmp_path / "options.json"
    proposal.write_text(json.dumps(example()), encoding="utf-8")
    return declaration, proposal


@pytest.fixture
def recording(tmp_path, inputs, engine_factory):
    from fly_connectome_sim.experiment.feed_event_session import record_feed_event_session

    return record_feed_event_session(tmp_path / "session", playlist_path=inputs[0],
                                     proposal_path=inputs[1], engine_factory=engine_factory)


@pytest.mark.parametrize("export_name", ["export_session_replay", "export_session_plan"])
@pytest.mark.parametrize("field", ["max_manifest_bytes", "max_event_line_bytes", "max_events_bytes",
                                  "max_events", "max_checkpoints"])
def test_export_intake_limits_reject_before_temporary_output(recording, tmp_path, monkeypatch,
                                                            export_name, field):
    from dataclasses import replace
    from fly_connectome_sim.experiment import feed_event_session as session
    from fly_connectome_sim.experiment.recorder import RunArtifactError, verify_run

    policy = session.EXPORT_READ_LIMITS
    assert (policy.max_manifest_bytes, policy.max_event_line_bytes, policy.max_events_bytes,
            policy.max_events, policy.max_checkpoints) == (2 * 1024 * 1024, 1024 * 1024,
                                                          64 * 1024 * 1024, 246, 2)
    raw = (recording.path / "events.jsonl").read_bytes()
    count = len(raw.splitlines())
    sizes = dict(max_manifest_bytes=len((recording.path / "run.json").read_bytes()),
                 max_event_line_bytes=max(map(len, raw.splitlines(keepends=True))),
                 max_events_bytes=len(raw), max_events=count, max_checkpoints=2)
    monkeypatch.setattr(session, "EXPORT_READ_LIMITS", replace(policy, **{field: sizes[field] - 1}))
    monkeypatch.setattr(session.tempfile, "NamedTemporaryFile",
                        lambda *args, **kwargs: pytest.fail("Over-limit source reached publication"))
    output = tmp_path / "not-published.json"
    with pytest.raises(RunArtifactError, match="limit"):
        getattr(session, export_name)(recording.path, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".session-export-*"))
    assert len(list(verify_run(recording.path).iter_events())) == count


def test_actual_one_engine_continuous_inputs_clocks_and_defer(tmp_path, inputs, engine_factory):
    from fly_connectome_sim.experiment import feed_event_session as session
    from fly_connectome_sim.experiment.event_cards import render_event_cards
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    calls, engines = [], []
    def factory():
        engine = engine_factory()
        engines.append(engine)
        observe = engine.observe
        def forbidden(*args, **kwargs):
            pytest.fail("session reset or restored native state")
        engine.brain.reset = forbidden
        engine.brain.restore = forbidden
        def capture(frame, duration, **flags):
            calls.append((engine.brain.cursor, frame.copy(), duration, flags, engine.brain.weights_frozen))
            return observe(frame, duration, **flags)
        engine.observe = capture
        return engine
    result = session.record_feed_event_session(tmp_path / "session", playlist_path=inputs[0],
                                               proposal_path=inputs[1], engine_factory=factory)
    replay = session.export_session_replay(result.path, tmp_path / "replay.json")
    plan = session.export_session_plan(result.path, tmp_path / "plan.json")
    events = list(result.iter_events())
    video = [e for e in events if e.get("stimulus") == "video"]
    cards = [e for e in events if e.get("stimulus") == "options"]
    assert len(engines) == 1 and len(video) == 120 and len(cards) == 4
    assert len(calls) == 124 and len(events) == 126
    assert video[-1]["video_policy"]["action"] == "stop"
    assert replay["feed_end_tick"] == 40000 and replay["duration_ticks"] == 60000
    assert [e["start_tick"] for e in cards] == [40000, 45000, 50000, 55000]
    assert [e["sequence"] for e in cards] == [121, 122, 123, 124]
    assert events[0]["sim_tick"] == 0 and events[-1]["sim_tick"] == 60000
    prepared = prepare_playlist(inputs[0], profile="fast-feed")[0]
    for index, (start, frame, duration, flags, frozen) in enumerate(calls):
        event = events[index + 1]
        assert start == event["start_tick"] and duration * 10 == event["duration_ticks"]
        assert flags == {"stimulation": None, "learning": False,
                         "pathway_detail": False, "qualification_detail": False}
        assert frozen is False
        np.testing.assert_array_equal(frame, prepared.frames[index].rgb if index < 120 else render_event_cards(example()))
    assert set(replay) == {"version", "tick_ms", "source", "groups", "inputs", "segments",
                           "duration_ticks", "feed_end_tick", "decision", "plan"}
    assert replay["version"] == "feed-event-replay/v1" and replay["tick_ms"] == .1
    assert replay["decision"]["window_start_tick"] == 55000
    assert replay["decision"]["effective_tick"] == replay["decision"]["window_end_tick"] == 60000
    assert replay["decision"]["event_scientific_sha256"] == cards[-1]["scientific_sha256"]
    assert replay["decision"]["event_sequence"] == 124
    assert replay["decision"]["counts"] == {"motor_left": 0, "motor_right": 0}
    assert replay["plan"] == plan and plan["status"] == "deferred"
    assert plan["selected_option"] is None and plan["selected_option_id"] is None
    assert sum(len(s["bins"]) for s in replay["segments"]) == 680
    assert set(replay["inputs"]) == {"options", *(f"clip-0/frame-{i}" for i in range(120))}
    metadata = result.manifest["metadata"]
    assert metadata["choice_recipe"]["timing_origin"] == "feed-stop/v1"
    assert metadata["choice_recipe"]["window_start_tick"] == 15000
    assert metadata["input_sha256"] == sorted({metadata["input"]["sha256"],
        *(f["sha256"] for c in metadata["clips"] for f in c["frames"])})


@pytest.mark.parametrize("failure", ["proposal", "render", "media", "existing", "file-parent"])
def test_preflight_failure_precedes_engine_and_output(tmp_path, inputs, monkeypatch, failure):
    from fly_connectome_sim.experiment import feed_event_session as session

    output = tmp_path / "not-created"
    if failure == "proposal":
        inputs[1].write_text('{"selected_option_id":"forced"}')
    elif failure == "render":
        def broken(*args):
            raise ValueError("test render failure")
        monkeypatch.setattr(session, "render_event_cards", broken)
    elif failure == "media":
        inputs[0].write_text('[{"path":"absent.mp4","source_url":"https://example.test"}]')
    elif failure == "existing":
        output.mkdir()
    else:
        parent = tmp_path / "file"
        parent.write_bytes(b"preserve")
        output = parent / "not-created"
    def forbidden():
        pytest.fail("failed preflight constructed native engine")
    with pytest.raises((ValueError, OSError)):
        session.record_feed_event_session(output, playlist_path=inputs[0], proposal_path=inputs[1],
                                           engine_factory=forbidden)
    if failure != "existing":
        assert not output.exists()


@pytest.mark.parametrize("mutation", [
    "card-before-stop", "feed-after-cards", "clock", "bin-gap", "pixel", "policy", "selection",
    "readout", "early-readout", "rate", "turn", "flags", "unknown", "checkpoint", "sequence",
])
def test_declared_resealed_mutations_rejected(recording, tmp_path, mutation):
    from fly_connectome_sim.experiment.feed_event_session import export_session_plan, export_session_replay

    def mutate(event):
        if mutation == "checkpoint" and event["type"] == "checkpoint":
            event["sim_tick"] += 1
        if event["type"] != "observe":
            return
        if mutation == "card-before-stop" and event["stimulus"] == "video":
            event["stimulus"] = "options"
        elif mutation == "feed-after-cards" and event["stimulus"] == "options":
            event["stimulus"] = "video"
        elif mutation == "clock":
            event["start_tick"] += 1
        elif mutation == "bin-gap":
            event["telemetry"]["bins"][0]["end_ms"] += .1
        elif mutation == "pixel":
            field = "video_frame" if event["stimulus"] == "video" else "event_frame"
            event[field]["sha256"] = "0" * 64
        elif mutation == "policy" and "video_policy" in event:
            event["video_policy"]["action"] = "stop"
        elif mutation == "selection" and "event_choice" in event:
            event["event_choice"]["selected_option_id"] = example()["options"][0]["id"]
        elif mutation == "readout" and "motor_readout" in event:
            event["motor_readout"]["decision"]["action"] = "inspect_left"
        elif mutation == "early-readout":
            event["motor_readout"] = {}
        elif mutation == "rate":
            event["telemetry"]["rates_hz"]["motor_left"] += 1
        elif mutation == "turn":
            event["telemetry"]["turn_hz"] += 1
        elif mutation == "flags":
            event["learning"] = True
        elif mutation == "unknown":
            event["plan"] = {"status": "selected"}
    for exporter in (export_session_plan, export_session_replay):
        output = tmp_path / (exporter.__name__ + ".json")
        with pytest.raises(ValueError):
            source = rewrite(recording, tmp_path / exporter.__name__, mutate_event=mutate,
                             drop_sequence=4 if mutation == "sequence" else None)
            exporter(source, output)
        assert not output.exists()


@pytest.mark.parametrize("field", ["choice_recipe", "video_recipe", "factors", "input_sha256", "extra"])
def test_metadata_closed_contract(recording, tmp_path, field):
    from fly_connectome_sim.experiment.feed_event_session import export_session_plan

    def mutate(metadata):
        if field == "extra":
            metadata["selected_option_id"] = example()["options"][0]["id"]
        elif field == "input_sha256":
            metadata[field] = [metadata["input"]["sha256"]]
        else:
            metadata[field]["override"] = 1
    with pytest.raises(ValueError):
        source = rewrite(recording, tmp_path / "bad-meta", mutate_metadata=mutate)
        export_session_plan(source, tmp_path / "bad.json")
    assert not (tmp_path / "bad.json").exists()


@pytest.mark.parametrize("export_name", ["export_session_replay", "export_session_plan"])
def test_normal_eof_required(recording, tmp_path, monkeypatch, export_name):
    from fly_connectome_sim.experiment import feed_event_session as session
    from fly_connectome_sim.experiment.recorder import VerifiedRun

    output = tmp_path / "not-published.json"
    original = VerifiedRun.iter_events
    def failing(self):
        yield from original(self)
        assert not output.exists()
        raise OSError("test premature EOF")
    monkeypatch.setattr(VerifiedRun, "iter_events", failing)
    with pytest.raises(OSError, match="premature EOF"):
        getattr(session, export_name)(recording.path, output)
    assert not output.exists()


def test_export_paths_source_and_race_preserve_bytes(recording, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment.feed_event_session import export_session_plan, export_session_replay

    before = {str(p): sha256(p.read_bytes()).hexdigest() for p in recording.path.rglob("*") if p.is_file()}
    existing = tmp_path / "existing.json"
    existing.write_bytes(b"preserve")
    for exporter in (export_session_plan, export_session_replay):
        with pytest.raises(FileExistsError):
            exporter(recording.path, existing)
        with pytest.raises(ValueError):
            exporter(recording.path, recording.path / "forbidden.json")
    assert existing.read_bytes() == b"preserve"
    assert before == {str(p): sha256(p.read_bytes()).hexdigest() for p in recording.path.rglob("*") if p.is_file()}
    output = tmp_path / "race.json"
    name = "rename" if os.name == "nt" else "link"
    publish = getattr(os, name)
    def race(source, target):
        output.write_bytes(b"concurrent")
        return publish(source, target)
    monkeypatch.setattr(os, name, race)
    with pytest.raises(FileExistsError):
        export_session_plan(recording.path, output)
    assert output.read_bytes() == b"concurrent"
    assert not list(tmp_path.glob(".session-export-*"))


@pytest.mark.parametrize("chosen", [0, 1])
def test_declared_positive_counts_bind_exact_original_option(recording, tmp_path, chosen):
    """Explicit resealed count fixture, not an actual native winning measurement."""
    from dataclasses import asdict
    from fly_connectome_sim.experiment import event_choice as cards
    from fly_connectome_sim.experiment.feed_event_session import export_session_plan, export_session_replay

    def mutate(event):
        if "event_choice" not in event:
            return
        name = cards.MOTOR_GROUPS[chosen]
        telemetry = event["telemetry"]
        telemetry["bins"][0]["group_spikes"][name] = 1
        telemetry["rates_hz"][name] = 2.0
        telemetry["turn_hz"] = -2.0 if chosen == 0 else 2.0
        telemetry["total_spikes"] += 1
        event["motor_readout"]["decision"] = asdict(cards.ADAPTER.adapt(telemetry))
        event["event_choice"]["selected_option_id"] = example()["options"][chosen]["id"]
    source = rewrite(recording, tmp_path / "declared-positive", mutate_event=mutate)
    replay = export_session_replay(source, tmp_path / "selected-replay.json")
    plan = export_session_plan(source, tmp_path / "selected-plan.json")
    assert replay["plan"] == plan and plan["status"] == "selected"
    assert plan["selected_option"] == example()["options"][chosen]
    assert plan["brief"] == example()["brief"]
    assert replay["decision"]["counts"][cards.MOTOR_GROUPS[chosen]] == 1


def test_tiny_native_declared_tonic_fixture_preserves_eight_second_stop_priority(tmp_path, map_engine_factory):
    """Declared toy tonic fixture tests flow; it is not a MaleCNS winner."""
    from fly_connectome_sim.experiment.feed_event_session import record_feed_event_session, export_session_replay

    declaration, _ = playlist(tmp_path, count=3, frames=601)
    proposal = tmp_path / "options.json"
    proposal.write_text(json.dumps(example()), encoding="utf-8")
    tonic = np.zeros(8, dtype=np.float32)
    tonic[7] = 20
    result = record_feed_event_session(tmp_path / "cap-session", playlist_path=declaration,
        proposal_path=proposal, engine_factory=lambda: map_engine_factory(tonic=tonic))
    replay = export_session_replay(result.path, tmp_path / "cap-replay.json")
    video = replay["segments"][:-4]
    advances = [s for s in video if s["video_policy"] and s["video_policy"]["action"] == "advance"]
    assert [s["source_end_tick"] for s in advances] == [30000, 60000]
    assert replay["feed_end_tick"] == 80000 and replay["duration_ticks"] == 100000
    assert len(video) == 240 and result.manifest["event_count"] == 246
    assert video[-1]["clip_id"] == "clip-2" and video[-1]["frame_index"] == 59
    assert video[-1]["video_policy"]["action"] == "stop"
    assert video[-1]["video_policy"]["reason"] == "session_limit"
    assert video[-1]["video_policy"]["minimum_dwell_met"] is False
    assert sum(len(s["bins"]) for s in replay["segments"]) == 1160


@pytest.mark.parametrize("state", ["frozen", "advanced", "wrong-dt", "not-engine"])
def test_session_rejects_nonfresh_engines(tmp_path, inputs, engine_factory, state):
    from fly_connectome_sim.experiment.feed_event_session import record_feed_event_session

    def factory():
        if state == "not-engine":
            return object()
        engine = engine_factory()
        if state == "frozen":
            engine.brain.weights_frozen = True
        elif state == "advanced":
            engine.brain.cursor = 1
        else:
            engine.brain.dt = 1
        return engine
    output = tmp_path / "bad-engine"
    with pytest.raises(ValueError, match="fresh actual"):
        record_feed_event_session(output, playlist_path=inputs[0], proposal_path=inputs[1], engine_factory=factory)
    assert not output.exists()


@pytest.mark.parametrize("drop,extra", [(120, False), (123, False), (125, False), (None, True)])
def test_incomplete_and_extra_operations_rejected(recording, tmp_path, drop, extra):
    from fly_connectome_sim.experiment.feed_event_session import export_session_plan

    with pytest.raises(ValueError):
        source = rewrite(recording, tmp_path / "incomplete", drop_sequence=drop, extra=extra)
        export_session_plan(source, tmp_path / "not-published.json")
    assert not (tmp_path / "not-published.json").exists()


@pytest.mark.parametrize("plan_only", [False, True])
def test_byte_limit_checked_before_publication(recording, tmp_path, monkeypatch, plan_only):
    from fly_connectome_sim.experiment import feed_event_session as session

    monkeypatch.setattr(session, "MAX_PLAN_BYTES" if plan_only else "MAX_REPLAY_BYTES", 1)
    exporter = session.export_session_plan if plan_only else session.export_session_replay
    with pytest.raises(ValueError, match="byte bound"):
        exporter(recording.path, tmp_path / "not-published.json")
    assert not (tmp_path / "not-published.json").exists()
    assert not list(tmp_path.glob(".session-export-*"))


def test_original_public_readers_reject_session(recording, tmp_path):
    from fly_connectome_sim.experiment.event_choice import export_event_replay
    from fly_connectome_sim.experiment.video_observation import export_video_replay

    for exporter in (export_event_replay, export_video_replay):
        with pytest.raises(ValueError):
            exporter(recording.path, tmp_path / (exporter.__name__ + ".json"))


def test_producer_rejects_final_raw_count_drift_without_rewriting(tmp_path, inputs, engine_factory):
    from fly_connectome_sim.experiment.feed_event_session import record_feed_event_session

    results = []
    def factory():
        engine = engine_factory()
        observe = engine.observe
        def drifting(frame, duration, **flags):
            telemetry = observe(frame, duration, **flags)
            if engine.brain.cursor == 60000:
                telemetry["rates_hz"]["motor_right"] = 1e-13
                telemetry["turn_hz"] = 1e-13
                results.append(telemetry)
            return telemetry
        engine.observe = drifting
        return engine
    output = tmp_path / "drifting"
    with pytest.raises(ValueError, match="count-derived"):
        record_feed_event_session(output, playlist_path=inputs[0], proposal_path=inputs[1], engine_factory=factory)
    assert results[0]["rates_hz"]["motor_right"] == 1e-13
    assert not (output / "run.json").exists()
