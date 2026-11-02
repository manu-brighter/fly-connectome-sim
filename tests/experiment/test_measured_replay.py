"""Measured replay preserves real native pilot evidence and fails closed."""

import base64
from copy import deepcopy
from hashlib import sha256
import json

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment.recorder import OWNED, RunRecorder, VerifiedRun, verify_run
from fly_connectome_sim.experiment.stimuli import AssayStimuli
from replay_helpers import engine_factory


@pytest.fixture
def recording(tmp_path, engine_factory):
    from fly_connectome_sim.experiment.measured_replay import record_observation_run

    return record_observation_run(tmp_path / "observation", engine_factory=engine_factory, cycles=1)


def test_real_native_sealed_roundtrip(recording, tmp_path):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    output = tmp_path / "replay.json"
    before = {str(path): sha256(path.read_bytes()).hexdigest()
              for path in recording.path.rglob("*") if path.is_file()}
    replay = export_measured_replay(recording.path, output)
    assert json.loads(output.read_text()) == replay
    assert set(replay) == {"version", "tick_ms", "source", "groups", "inputs", "segments", "duration_ticks"}
    assert replay["version"] == "measured-replay/v1" and replay["tick_ms"] == 0.1
    assert replay["duration_ticks"] == 20000
    assert replay["groups"] == dict.fromkeys(("kc", "pam11", "ppl101", "mbon07", "mbon11", "motor_left", "motor_right"), 1)
    assert replay["source"]["verification_mode"] == "integrity-only"
    assert replay["source"]["metadata"] == recording.manifest["metadata"]
    assert recording.manifest["run_kind"] == "pilot"
    assert recording.manifest["metadata"]["family"] == "measured-observation"
    assert set(recording.manifest["checkpoints"]) == {"brain-before.npz", "brain-after.npz"}
    for name in recording.manifest["checkpoints"]:
        with np.load(recording.path / "checkpoints" / name) as checkpoint:
            assert "metadata" in checkpoint.files
    events = list(recording.iter_events())
    assert [event["type"] for event in events] == ["checkpoint", "observe", "observe", "observe", "observe", "checkpoint"]
    assert all(not any(key.startswith("parent_") for key in event) for event in events)
    assert [segment["stimulus"] for segment in replay["segments"]] == ["A", "black", "B", "black"]
    assert [segment["event_sequence"] for segment in replay["segments"]] == [1, 2, 3, 4]
    total_bins = 0
    for index, (segment, event) in enumerate(zip(replay["segments"], events[1:-1], strict=True)):
        assert set(segment) == {"event_sequence", "branch_id", "stimulus", "stimulation", "learning", "source_start_tick", "source_end_tick", "playback_start_tick", "playback_end_tick", "bins"}
        assert segment["stimulation"] is None and segment["learning"] is False
        assert segment["source_start_tick"] == segment["playback_start_tick"] == index * 5000
        assert segment["source_end_tick"] == segment["playback_end_tick"] == (index + 1) * 5000
        assert len(segment["bins"]) == 50
        total_bins += len(segment["bins"])
        for group, population in replay["groups"].items():
            spikes = sum(bin["group_spikes"][group] for bin in segment["bins"])
            assert spikes / (population * 0.5) == event["telemetry"]["rates_hz"][group]
        assert all(bin["group_spikes"]["motor_left"] == 0 for bin in segment["bins"])
        for bin in segment["bins"]:
            assert set(bin) == {"end_tick", "duration_ticks", "group_spikes"}
            assert bin["duration_ticks"] == 100
        assert [bin["group_spikes"] for bin in segment["bins"]] == [bin["group_spikes"] for bin in event["telemetry"]["bins"]]
    assert total_bins == 200
    for name, image in replay["inputs"].items():
        assert set(image) == {"sha256", "width", "height", "rgb_base64"}
        frame = np.frombuffer(base64.b64decode(image["rgb_base64"]), dtype=np.uint8).reshape(32, 32, 3)
        expected = np.zeros((32, 32, 3), dtype=np.uint8) if name == "black" else AssayStimuli(11, "qualification").frame(name, side="center", color_assignment="fixed")
        np.testing.assert_array_equal(frame, expected)
        assert image["sha256"] == _rgb_input_sha256(frame)
    assert before == {str(path): sha256(path.read_bytes()).hexdigest()
                      for path in recording.path.rglob("*") if path.is_file()}


@pytest.mark.parametrize("cycles", [0, 11, True, 1.0, "1"])
def test_cycle_validation_precedes_engine_and_output(tmp_path, cycles):
    from fly_connectome_sim.experiment.measured_replay import record_observation_run

    def forbidden():
        pytest.fail("invalid request constructed an engine")

    with pytest.raises(ValueError):
        record_observation_run(tmp_path / "bad", engine_factory=forbidden, cycles=cycles)
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("seed", [-1, True, 1.0, 4294967296, 9007199254740993])
def test_seed_validation_precedes_engine_and_output(tmp_path, seed):
    from fly_connectome_sim.experiment.measured_replay import record_observation_run

    def forbidden():
        pytest.fail("invalid seed constructed an engine")

    with pytest.raises(ValueError):
        record_observation_run(tmp_path / "bad-seed", engine_factory=forbidden, seed=seed)
    assert not (tmp_path / "bad-seed").exists()


def rewrite(recording, target, mutate_event=None, mutate_metadata=None):
    metadata = deepcopy(recording.manifest["metadata"])
    if mutate_metadata:
        mutate_metadata(metadata)
    with RunRecorder(target, run_kind="pilot", metadata=metadata,
                     root_branch_id=recording.manifest["root_branch_id"]) as recorder:
        for original in recording.iter_events():
            event = {key: value for key, value in original.items() if key not in OWNED}
            if "telemetry" in event:
                event["telemetry"]["engine_identity"] = deepcopy(metadata["engine_identity"])
            if mutate_event:
                mutate_event(event)
            if "checkpoint_name" in event:
                recorder.ingest_checkpoint(event["checkpoint_name"],
                                           recording.path / "checkpoints" / event["checkpoint_name"],
                                           origin_branch_id=event["branch_id"])
            recorder.append(event)
    return target


@pytest.mark.parametrize("mutation", [
    "missing_bins", "missing_group", "bool_count", "negative_count", "count_bound", "rate",
    "gap", "off_lattice", "rewind", "pixel", "learning", "stimulation", "detail", "operation", "bool_rate", "bool_clock",
])
def test_rejects_semantically_invalid_sealed_source(recording, tmp_path, mutation):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    def mutate(event):
        if event["type"] != "observe":
            return
        telemetry = event["telemetry"]
        if mutation == "missing_bins":
            telemetry.pop("bins")
        elif mutation == "missing_group":
            telemetry["bins"][0]["group_spikes"].pop("kc")
        elif mutation in {"bool_count", "negative_count", "count_bound"}:
            telemetry["bins"][0]["group_spikes"]["kc"] = {"bool_count": True, "negative_count": -1, "count_bound": 101}[mutation]
        elif mutation == "rate":
            telemetry["rates_hz"]["kc"] += 1
        elif mutation == "bool_rate":
            telemetry["rates_hz"]["motor_left"] = False
        elif mutation == "bool_clock":
            event["start_tick"] = False
        elif mutation == "gap":
            telemetry["bins"][0]["duration_ms"] = 9.9
        elif mutation == "off_lattice":
            event["start_ms"] += 0.000000001
        elif mutation == "rewind":
            event["start_ms"] = 0.0
            event["start_tick"] = 0
        elif mutation == "pixel":
            telemetry["input_sha256"] = recording.manifest["metadata"]["rgb_input_sha256"]["B"]
        elif mutation == "learning":
            event["learning"] = telemetry["learning"] = True
        elif mutation == "stimulation":
            event["stimulation"] = "ppl101"
        elif mutation == "detail":
            telemetry["qualification_detail"] = {}
        else:
            event["type"] = "restore"

    source = rewrite(recording, tmp_path / mutation, mutate_event=mutate)
    output = tmp_path / f"{mutation}.json"
    with pytest.raises(ValueError):
        export_measured_replay(source, output)
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["protocol", "recipe", "population"])
def test_rejects_unknown_metadata_and_empty_population(recording, tmp_path, mutation):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    def mutate(metadata):
        if mutation == "protocol":
            metadata["protocol_version"] = "unknown/v1"
        elif mutation == "recipe":
            metadata["stimulus_recipe"]["side"] = "left"
        else:
            metadata["engine_identity"]["neural_groups"]["kc"] = []

    source = rewrite(recording, tmp_path / mutation, mutate_metadata=mutate)
    with pytest.raises(ValueError):
        export_measured_replay(source, tmp_path / "bad.json")
    assert not (tmp_path / "bad.json").exists()


def test_tail_failure_never_publishes(recording, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    output = tmp_path / "bad.json"
    original = VerifiedRun.iter_events

    def failing(self):
        yield from original(self)
        assert not output.exists()
        raise OSError("tail read failed")

    monkeypatch.setattr(VerifiedRun, "iter_events", failing)
    with pytest.raises(OSError, match="tail read failed"):
        export_measured_replay(recording.path, output)
    assert not output.exists()


def test_tail_corruption_and_output_collisions(recording, tmp_path):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    output = tmp_path / "existing.json"
    output.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        export_measured_replay(recording.path, output)
    assert output.read_bytes() == b"preserve"
    with pytest.raises(ValueError):
        export_measured_replay(recording.path, recording.path / "export.json")
    assert not (recording.path / "export.json").exists()
    with (recording.path / "events.jsonl").open("ab") as stream:
        stream.write(b"corrupt tail\n")
    with pytest.raises(ValueError):
        export_measured_replay(recording.path, tmp_path / "corrupt.json")
    assert not (tmp_path / "corrupt.json").exists()


def test_publication_race_preserves_existing_file(recording, tmp_path, monkeypatch):
    import os
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    output = tmp_path / "race.json"
    name = "rename" if os.name == "nt" else "link"
    publish = getattr(os, name)

    def race(source, target):
        output.write_bytes(b"concurrent writer")
        return publish(source, target)

    monkeypatch.setattr(os, name, race)
    with pytest.raises(FileExistsError):
        export_measured_replay(recording.path, output)
    assert output.read_bytes() == b"concurrent writer"
    assert not list(tmp_path.glob(".measured-replay-*"))


def test_default_and_max_cycles_preserve_actual_call_flags_and_black(tmp_path, engine_factory):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay, record_observation_run

    calls = []

    def factory():
        engine = engine_factory()
        observe = engine.observe

        def record(frame, duration_ms, **flags):
            calls.append((frame.copy(), duration_ms, flags, engine.brain.weights_frozen))
            return observe(frame, duration_ms, **flags)

        engine.observe = record
        return engine

    default = record_observation_run(tmp_path / "default", engine_factory=factory)
    assert default.manifest["event_count"] == 14
    maximum = record_observation_run(tmp_path / "maximum", engine_factory=factory, cycles=10)
    replay = export_measured_replay(maximum.path, tmp_path / "maximum.json")
    assert len(replay["segments"]) == 40 and replay["duration_ticks"] == 200000
    assert sum(len(segment["bins"]) for segment in replay["segments"]) == 2000
    assert len(calls) == 52
    for index, (frame, duration, flags, frozen) in enumerate(calls):
        assert duration == 500.0
        assert flags == {"stimulation": None, "learning": False, "pathway_detail": False, "qualification_detail": False}
        assert frozen is False
        assert frame.dtype == np.uint8 and frame.shape == (32, 32, 3)
        if index % 2:
            assert not frame.any()


def test_benign_metadata_is_preserved(recording, tmp_path):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    source = rewrite(recording, tmp_path / "extra", mutate_metadata=lambda metadata: metadata.update(operator_note="bounded observation"))
    replay = export_measured_replay(source, tmp_path / "extra.json")
    assert replay["source"]["metadata"]["operator_note"] == "bounded observation"


def test_supported_export_rejects_actual_checkpoint_restored_branch(recording, tmp_path, engine_factory):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    source = tmp_path / "forked"
    root = recording.manifest["root_branch_id"]
    engine = engine_factory()
    before = recording.path / "checkpoints" / "brain-before.npz"
    engine.brain.restore(before)
    with RunRecorder(source, run_kind="pilot", metadata=recording.manifest["metadata"], root_branch_id=root) as recorder:
        digest = recorder.ingest_checkpoint("brain-before.npz", before, origin_branch_id=root)
        recorder.append({"type": "checkpoint", "branch_id": root, "sim_ms": 0.0,
                         "sim_tick": 0, "checkpoint_name": "brain-before.npz"})
        recorder.append({"type": "restore", "branch_id": "restored-branch", "sim_ms": 0.0,
                         "parent_branch_id": root, "parent_checkpoint_name": "brain-before.npz",
                         "parent_checkpoint_sequence": 0, "parent_checkpoint_sha256": digest})
        for original in list(recording.iter_events())[1:-1]:
            event = {key: value for key, value in original.items() if key not in OWNED}
            stimulus = event["stimulus"]
            frame = np.zeros((32, 32, 3), dtype=np.uint8) if stimulus is None else AssayStimuli(11, "qualification").frame(stimulus)
            event["telemetry"] = engine.observe(frame, 500.0, stimulation=None, learning=False,
                                                 pathway_detail=False, qualification_detail=False)
            event["branch_id"] = "restored-branch"
            recorder.append(event)
        after = tmp_path / "restored-after.npz"
        engine.brain.checkpoint(after)
        recorder.ingest_checkpoint("brain-after.npz", after, origin_branch_id="restored-branch")
        recorder.append({"type": "checkpoint", "branch_id": "restored-branch", "sim_ms": 2000.0,
                         "sim_tick": 20000, "checkpoint_name": "brain-after.npz"})
    assert verify_run(source).verification_mode == "integrity-only"
    with pytest.raises(ValueError, match="forked"):
        export_measured_replay(source, tmp_path / "forked.json")
    assert not (tmp_path / "forked.json").exists()


def test_nonfinite_telemetry_rejected_at_source_intake(recording, tmp_path):
    from fly_connectome_sim.experiment.measured_replay import export_measured_replay

    path = recording.path / "events.jsonl"
    raw = path.read_bytes()
    assert b'"turn_hz":0.0' in raw
    path.write_bytes(raw.replace(b'"turn_hz":0.0', b'"turn_hz":1e999', 1))
    with pytest.raises(ValueError):
        export_measured_replay(recording.path, tmp_path / "nonfinite.json")
    assert not (tmp_path / "nonfinite.json").exists()


def test_nonfresh_and_existing_output_rejected_without_recording(recording, tmp_path, engine_factory):
    from fly_connectome_sim.experiment.measured_replay import record_observation_run

    engine = engine_factory()
    engine.observe(np.zeros((32, 32, 3), dtype=np.uint8), 0.1)
    with pytest.raises(ValueError):
        record_observation_run(tmp_path / "nonfresh", engine_factory=lambda: engine)
    assert not (tmp_path / "nonfresh").exists()

    def forbidden():
        pytest.fail("existing output constructed an engine")

    with pytest.raises(FileExistsError):
        record_observation_run(recording.path, engine_factory=forbidden)


def test_cli_real_native_observe_export_and_verify(tmp_path, engine_factory, monkeypatch, capsys):
    from fly_connectome_sim import cli

    monkeypatch.setattr(cli.FlyEngine, "from_prepared_graph", engine_factory)
    source = tmp_path / "cli-observation"
    output = tmp_path / "cli-replay.json"
    assert cli.main(["observe", "--output-dir", str(source), "--cycles", "1"]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["run_kind"] == "pilot" and summary["event_count"] == 6
    assert cli.main(["export-replay", str(source), "--output", str(output)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["segment_count"] == 4 and summary["duration_ticks"] == 20000
    assert "rgb_base64" not in summary
    assert cli.main(["verify-run", str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["event_count"] == 6
    assert cli.main(["observe", "--output-dir", str(source)]) == 1
    assert capsys.readouterr().err
