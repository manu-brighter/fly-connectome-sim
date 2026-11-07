"""Fixed diagnostic behavior with genuine decoded input and tiny native state."""

from hashlib import sha256
import importlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from replay_helpers import map_engine_factory
from test_event_cards import example
from test_video_observation import playlist


def diagnostic():
    name = "fly_connectome_sim.experiment.content_diagnostic"
    assert importlib.util.find_spec(name) is not None, "Fixed content diagnostic is not implemented"
    return importlib.import_module(name)


@pytest.fixture
def inputs(tmp_path):
    declaration, paths = playlist(tmp_path, count=2, frames=601)
    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps(example()), encoding="utf-8")
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Declared tiny-native diagnostic fixture.\n", encoding="utf-8")
    return declaration, paths, proposal, protocol


def arguments(tmp_path, inputs, factory):
    from fly_connectome_sim.neural.checkpoint import model_fingerprint

    module = diagnostic()
    declaration, paths, proposal, protocol = inputs
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps({
        "protocol_sha256": sha256(protocol.read_bytes()).hexdigest(),
        "model_sha256": model_fingerprint()["sha256"],
        "implementation_sha256": sha256(Path(module.__file__).read_bytes()).hexdigest(),
    }), encoding="utf-8")
    return dict(playlist_path=declaration, proposal_path=proposal, protocol_path=protocol,
                freeze_path=freeze, engine_factory=factory,
                expected_source_sha256=tuple(sha256(path.read_bytes()).hexdigest() for path in paths),
                expected_proposal_sha256=sha256(proposal.read_bytes()).hexdigest())


def test_fixed_native_branches_record_all_black_intervals_and_map_swapped_choice(
    tmp_path, inputs, map_engine_factory, monkeypatch,
):
    module = diagnostic()
    engine = map_engine_factory(tonic=np.array([0, 0, 0, 0, 0, 0, 20, 0], dtype=np.float32))
    actual_observe = engine.observe
    calls = []

    def observe(frame, duration_ms, **kwargs):
        calls.append((frame.copy(), duration_ms, kwargs))
        return actual_observe(frame, duration_ms, **kwargs)

    monkeypatch.setattr(engine, "observe", observe)
    factory_calls = []

    def factory():
        factory_calls.append(True)
        return engine

    output = tmp_path / "diagnostic"
    result = module.run_content_diagnostic(output, **arguments(tmp_path, inputs, factory))
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    observations = [event for event in events if event["type"] == "observe"]
    assert len(calls) == len(observations) == 504
    assert len(factory_calls) == 1
    assert round(sum(call[1] for call in calls), 7) == 28000.0
    assert all(call[2] == dict(stimulation=None, learning=False, pathway_detail=False,
                              qualification_detail=False) for call in calls)
    assert all(call[0].dtype == np.uint8 for call in calls)
    assert all(not call[0].any() for call in calls[248:252] + calls[252:492] + calls[500:504])
    assert any(call[0].any() for call in calls[:240])
    from fly_connectome_sim.experiment.event_cards import render_event_cards

    swapped = example()
    swapped["options"].reverse()
    assert np.array_equal(calls[240][0], render_event_cards(example()))
    assert np.array_equal(calls[244][0], render_event_cards(swapped))
    assert not np.array_equal(calls[240][0], calls[244][0])
    assert [event["sequence"] for event in events] == list(range(len(events)))
    restores = [event for event in events if event["type"] == "restore"]
    assert [event["sim_tick"] for event in restores] == [0, 80000, 80000, 80000, 0, 80000, 80000, 80000]
    assert restores[0]["complete_state_sha256"] == restores[4]["complete_state_sha256"]
    assert len({event["complete_state_sha256"] for event in restores[1:4]}) == 1
    assert len({event["complete_state_sha256"] for event in restores[5:]}) == 1
    assert len(list((output / "checkpoints").glob("*.npz"))) == 3
    assert len(result["feeds"]["real"]) == len(result["feeds"]["black"]) == 16
    for history in ("real", "black"):
        probes = result["probes"][history]
        assert probes["normal"]["selected_option_id"] == example()["options"][0]["id"]
        assert probes["swapped"]["selected_option_id"] == example()["options"][1]["id"]
        assert probes["black"]["selected_option_id"] is None
        assert probes["normal"]["windows"][-1]["decision"]["action"] == "inspect_left"
        for probe in probes.values():
            assert [(row["start_tick"], row["end_tick"]) for row in probe["windows"]] == [
                (80000, 85000), (85000, 90000), (90000, 95000), (95000, 100000),
            ]
    assert len(result["comparisons"]) == 10
    assert all(len(contrast["windows"]) in (4, 16) for contrast in result["comparisons"].values())
    for history in ("real", "black"):
        for phase in ("feed", "normal", "swapped", "black"):
            bins = [bin_ for event in observations
                    if event["history"] == history and event["phase"] == phase
                    for bin_ in event["telemetry"]["bins"]]
            windows = (result["feeds"][history] if phase == "feed"
                       else result["probes"][history][phase]["windows"])
            for window in windows:
                for side in ("motor_left", "motor_right"):
                    count = sum(bin_["group_spikes"][side] for bin_ in bins
                                if window["start_tick"] < round(bin_["end_ms"] * 10) <= window["end_tick"])
                    assert window["counts"][side] == count
                    assert window["rates_hz"][side] == count * 2.0  # one cell, half a second
    assert json.loads((output / "summary.json").read_text()) == result
    assert result["observe_calls"] == 504 and result["advanced_ticks"] == 280000
    assert engine.brain.cursor == 100000 and engine.brain.weights_frozen is False


@pytest.mark.parametrize("drift", ["source", "proposal", "protocol", "model", "implementation"])
def test_drift_fails_before_engine_construction(tmp_path, inputs, drift):
    module = diagnostic()

    def forbidden():
        pytest.fail("Engine must not be constructed after input/source drift")

    kwargs = arguments(tmp_path, inputs, forbidden)
    if drift == "source":
        kwargs["expected_source_sha256"] = ("0" * 64, kwargs["expected_source_sha256"][1])
    elif drift == "proposal":
        kwargs["expected_proposal_sha256"] = "0" * 64
    elif drift == "protocol":
        inputs[3].write_text("Changed protocol", encoding="utf-8")
    else:
        frozen = json.loads(kwargs["freeze_path"].read_text())
        frozen[drift + "_sha256"] = "0" * 64
        kwargs["freeze_path"].write_text(json.dumps(frozen), encoding="utf-8")
    with pytest.raises(ValueError, match="(?i)drift|differ"):
        module.run_content_diagnostic(tmp_path / "diagnostic", **kwargs)
    assert not (tmp_path / "diagnostic").exists()


def test_existing_output_and_partial_failure_never_publish_completion(tmp_path, inputs, map_engine_factory, monkeypatch):
    module = diagnostic()
    engine = map_engine_factory()
    kwargs = arguments(tmp_path, inputs, lambda: engine)
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "keep").write_text("untouched")
    with pytest.raises(FileExistsError):
        module.run_content_diagnostic(existing, **kwargs)
    assert (existing / "keep").read_text() == "untouched"
    original = engine.observe
    count = 0

    def fail(frame, duration_ms, **flags):
        nonlocal count
        count += 1
        if count == 3:
            raise RuntimeError("Deliberate native failure")
        return original(frame, duration_ms, **flags)

    monkeypatch.setattr(engine, "observe", fail)
    output = tmp_path / "partial"
    with pytest.raises(RuntimeError, match="Deliberate"):
        module.run_content_diagnostic(output, **kwargs)
    assert (output / "manifest.json").is_file()
    assert not (output / "summary.json").exists()
    assert len([json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
                if json.loads(line)["type"] == "observe"]) == 2


def test_restore_mismatch_stops_before_observation(tmp_path, inputs, map_engine_factory, monkeypatch):
    module = diagnostic()
    engine = map_engine_factory()
    restore = engine.brain.restore

    def broken_restore(path):
        restore(path)
        engine.brain.r8_light[0] = 0.5

    monkeypatch.setattr(engine.brain, "restore", broken_restore)
    monkeypatch.setattr(engine, "observe", lambda *a, **k: pytest.fail("Bad restore must stop"))
    output = tmp_path / "mismatch"
    with pytest.raises(ValueError, match="(?i)restore"):
        module.run_content_diagnostic(output, **arguments(tmp_path, inputs, lambda: engine))
    assert not (output / "summary.json").exists()


@pytest.mark.parametrize("bins", [
    [{"end_ms": 10.1, "duration_ms": 10.0, "group_spikes": {"motor_left": 2, "motor_right": 1}}],
    ([{"end_ms": (index + 1) * 10.0, "duration_ms": 10.0,
       "group_spikes": {"motor_left": 0, "motor_right": 0}} for index in range(49)]
     + [{"end_ms": 495.0, "duration_ms": 5.0, "group_spikes": {"motor_left": 0, "motor_right": 0}},
        {"end_ms": 505.0, "duration_ms": 10.0, "group_spikes": {"motor_left": 2, "motor_right": 1}}]),
])
def test_window_reducer_rejects_gaps_and_crossing_integer_bins(bins):
    with pytest.raises(ValueError, match="(?i)bin|window"):
        diagnostic()._windows(bins, start_tick=0, end_tick=5000,
                              populations={"motor_left": 2, "motor_right": 1})


def test_window_reducer_uses_population_normalized_counts_and_strict_threshold():
    bins = [{"end_ms": (index + 1) * 10.0, "duration_ms": 10.0,
             "group_spikes": {"motor_left": 4 if index == 0 else 0,
                              "motor_right": 5 if index == 0 else 0}} for index in range(50)]
    window = diagnostic()._windows(bins, start_tick=0, end_tick=5000,
                                   populations={"motor_left": 2, "motor_right": 2})[0]
    assert window["counts"] == {"motor_left": 4, "motor_right": 5}
    assert window["rates_hz"] == {"motor_left": 4.0, "motor_right": 5.0}
    assert window["decision"]["signed_difference_hz"] == 1.0
    assert window["decision"]["action"] == "defer"
