"""Execution boundaries for scheduled training and independent retention forks."""

from hashlib import sha256
import json
import math

import numpy as np
import pytest

from jogge_fly_brain.engine import _rgb_input_sha256
from jogge_fly_brain.experiment.executor import advance_neutral, execute_schedule, retention_test
from jogge_fly_brain.experiment.protocol import ProtocolSchedule, ProtocolStep
from jogge_fly_brain.experiment.stimuli import AssayStimuli


class RecordingBrain:
    def __init__(self):
        self.sim_ms = 0.0
        self.state = []
        self.restores = []

    def checkpoint(self, path):
        path.write_bytes(json.dumps({"sim_ms": self.sim_ms, "state": self.state}).encode())

    def restore(self, path):
        data = path.read_bytes()
        saved = json.loads(data)
        self.sim_ms = saved["sim_ms"]
        self.state = saved["state"]
        self.restores.append((str(path), sha256(data).hexdigest(), self.sim_ms, tuple(self.state)))


class RecordingEngine:
    """Only the engine boundary is replaced; frames, durations and forks stay real."""

    def __init__(self):
        self.brain = RecordingBrain()
        self.calls = []

    def observe(self, frame, duration_ms, *, stimulation=None, learning=False):
        assert isinstance(frame, np.ndarray)
        self.brain.sim_ms = round(self.brain.sim_ms + duration_ms, 3)
        input_sha256 = _rgb_input_sha256(frame)
        self.brain.state.append((input_sha256, duration_ms, stimulation, learning))
        self.calls.append((frame.copy(), duration_ms, stimulation, learning, self.brain.sim_ms))
        return {"sim_ms": self.brain.sim_ms, "input_sha256": input_sha256,
                "stimulation": stimulation, "learning": learning,
                "rates_hz": {"mbon11": float(len(self.brain.state))}}


def test_neutral_gap_chunks_black_frames_and_reports_exact_branch_time():
    engine = RecordingEngine()
    events = []

    advance_neutral(engine, 1201.0, (6, 8, 3), branch_id="training", on_event=events.append)

    assert [call[1] for call in engine.calls] == [500.0, 500.0, 201.0]
    assert [call[4] for call in engine.calls] == [500.0, 1000.0, 1201.0]
    assert all(frame.shape == (6, 8, 3) and frame.dtype == np.uint8 and not frame.any()
               for frame, *_ in engine.calls)
    assert [(event["type"], event["branch_id"], event["sim_ms"], event["duration_ms"])
            for event in events] == [
                ("neutral_gap_chunk", "training", 500.0, 500.0),
                ("neutral_gap_chunk", "training", 1000.0, 500.0),
                ("neutral_gap_chunk", "training", 1201.0, 201.0),
            ]
    assert all(event["input_sha256"] == _rgb_input_sha256(np.zeros((6, 8, 3), dtype=np.uint8))
               and event["stimulation"] is None and event["learning"] is False for event in events)


def test_schedule_stops_at_training_end_and_leaves_reward_free_tests_for_retention(tmp_path):
    engine = RecordingEngine()
    stimuli = AssayStimuli(seed=7, family="qualification", width=8, height=6)
    schedule = ProtocolSchedule(
        version="associative-protocol/v1", condition="temporally_unpaired", seed=7,
        steps=(
            ProtocolStep(0.0, 20.0, "baseline", "A", None, False, "center"),
            ProtocolStep(1221.0, 20.0, "pairing", None, "ppl101", True),
            ProtocolStep(1251.0, 20.0, "pairing", "B", None, True, "left"),
            ProtocolStep(1281.0, 20.0, "reward_free_test", "A", None, False, "center"),
            ProtocolStep(1311.0, 20.0, "reward_free_test", "B", None, False, "center"),
            ProtocolStep(1341.0, 20.0, "reward_free_test", "C", None, False, "center"),
        ),
    )
    events = []
    training_end = tmp_path / "training.npz"

    def record(event):
        events.append(event)
        if event["type"] == "step" and event["phase"] == "pairing" and event["stimulus"] == "B":
            engine.brain.checkpoint(training_end)

    execute_schedule(engine, schedule, stimuli, branch_id="training", on_event=record)

    assert [call[1] for call in engine.calls] == [20.0, 500.0, 500.0, 201.0, 20.0, 10.0,
                                                20.0]
    assert engine.brain.sim_ms == 1271.0
    assert json.loads(training_end.read_bytes())["sim_ms"] == 1271.0
    pulse = engine.calls[4]
    assert pulse[2:4] == ("ppl101", True)
    assert pulse[0].shape == (6, 8, 3) and pulse[0].dtype == np.uint8 and not pulse[0].any()
    assert [(event["type"], event["sim_ms"]) for event in events if event["type"] == "step"] == [
        ("step", 20.0), ("step", 1241.0), ("step", 1271.0),
    ]
    assert not any(event.get("phase") == "reward_free_test" for event in events)
    assert all(event["branch_id"] == "training" and event["input_sha256"]
               for event in events)


@pytest.mark.parametrize("duration", [-0.1, math.inf, math.nan, 0.15])
def test_neutral_rejects_invalid_duration_before_engine_mutation(duration):
    engine = RecordingEngine()
    events = []

    with pytest.raises(ValueError):
        advance_neutral(engine, duration, (6, 8, 3), branch_id="x", on_event=events.append)

    assert engine.calls == [] and events == []


def test_schedule_rejects_late_invalid_duration_before_first_step():
    engine = RecordingEngine()
    schedule = ProtocolSchedule(
        version="associative-protocol/v1", condition="training", seed=1,
        steps=(
            ProtocolStep(0.0, 20.0, "pairing", "A", None, True),
            ProtocolStep(30.0, 0.15, "pairing", "B", None, True),
        ),
    )
    events = []

    with pytest.raises(ValueError):
        execute_schedule(engine, schedule, AssayStimuli(seed=1, family="qualification"),
                         branch_id="training", on_event=events.append)

    assert engine.calls == [] and events == []


def test_retention_restores_training_and_each_test_parent_independently(tmp_path):
    engine = RecordingEngine()
    stimuli = AssayStimuli(seed=7, family="qualification", width=8, height=6)
    schedule = ProtocolSchedule.create(seed=7, paired_identity="A", duration_ms=20.0)
    engine.brain.sim_ms = 20150.0
    engine.brain.state = [["training-end"]]
    training = tmp_path / "training.npz"
    engine.brain.checkpoint(training)
    training_bytes = training.read_bytes()
    training_hash = sha256(training_bytes).hexdigest()
    events = []

    at_t = retention_test(engine, training, 0.0, schedule=schedule, stimuli=stimuli,
                          checkpoint_dir=tmp_path, branch_id="T", on_event=events.append)
    at_60 = retention_test(engine, training, 60000.0, schedule=schedule, stimuli=stimuli,
                           checkpoint_dir=tmp_path, branch_id="T+60", on_event=events.append)

    assert training.read_bytes() == training_bytes
    assert len(at_t) == len(at_60) == 3
    assert [item["identity"] for item in at_t] == ["A", "B", "C"]
    starts = [event for event in events if event["type"] == "retention_start"]
    ends = [event for event in events if event["type"] == "retention_end"]
    assert [(event["branch_id"], event["sim_ms"], event["parent_checkpoint_sha256"])
            for event in starts] == [
                ("T", 20150.0, training_hash), ("T+60", 20150.0, training_hash),
            ]
    assert [(event["branch_id"], event["sim_ms"]) for event in ends] == [
        ("T", 20150.0), ("T+60", 80150.0),
    ]
    assert [restore[1] for restore in engine.brain.restores if restore[0] == str(training)] == [
        training_hash, training_hash,
    ]
    for branch, expected_time in (("T", 20150.0), ("T+60", 80150.0)):
        tests = [event for event in events if event["type"] == "fork"
                 and event["branch_id"].startswith(branch + "/")]
        assert len(tests) == 3
        parent_hash = tests[0]["parent_checkpoint_sha256"]
        assert all(event["parent_checkpoint_sha256"] == parent_hash
                   and event["sim_ms"] == expected_time for event in tests)
        assert [restore[2] for restore in engine.brain.restores
                if restore[1] == parent_hash and restore[0] != str(training)] == [
            expected_time, expected_time, expected_time,
        ]
    test_calls = [call for call in engine.calls if call[0].any()]
    assert len(test_calls) == 6
    assert all(call[2] is None and call[3] is False for call in engine.calls)
    assert [call[4] for call in test_calls] == [20180.0, 20210.0, 20240.0,
                                                80180.0, 80210.0, 80240.0]
    test_gaps = [event for event in events if event["type"] == "neutral_gap_chunk"
                 and "/" in event["branch_id"]]
    assert [(event["branch_id"], event["duration_ms"]) for event in test_gaps] == [
        ("T/A", 10.0), ("T/B", 40.0), ("T/C", 70.0),
        ("T+60/A", 10.0), ("T+60/B", 40.0), ("T+60/C", 70.0),
    ]
    assert all(item["parent_checkpoint_sha256"] and item["telemetry"]["rates_hz"]["mbon11"]
               for item in (*at_t, *at_60))


def test_retention_accepts_checkpoint_clock_on_same_tenth_ms_tick(tmp_path):
    engine = RecordingEngine()
    engine.brain.sim_ms = 20150.600000000002
    training = tmp_path / "training-end.npz"
    engine.brain.checkpoint(training)
    events = []

    results = retention_test(
        engine,
        training,
        0.0,
        schedule=ProtocolSchedule.create(seed=7, paired_identity="A", duration_ms=20.1),
        stimuli=AssayStimuli(seed=7, family="qualification", width=8, height=6),
        checkpoint_dir=tmp_path / "retention",
        branch_id="T",
        on_event=events.append,
    )

    assert [result["identity"] for result in results] == ["A", "B", "C"]
    assert next(event for event in events if event["type"] == "retention_start")["sim_ms"] == 20150.6


def test_retention_rejects_checkpoint_outside_schedule_t0_before_branch_output(tmp_path):
    engine = RecordingEngine()
    engine.brain.sim_ms = 20150.1
    training = tmp_path / "wrong-training-end.npz"
    engine.brain.checkpoint(training)
    checkpoint_dir = tmp_path / "retention"
    events = []

    with pytest.raises(ValueError, match="T=0"):
        retention_test(
            engine,
            training,
            0.0,
            schedule=ProtocolSchedule.create(seed=7, paired_identity="A", duration_ms=20.0),
            stimuli=AssayStimuli(seed=7, family="qualification", width=8, height=6),
            checkpoint_dir=checkpoint_dir,
            branch_id="T",
            on_event=events.append,
        )

    assert [restore[0] for restore in engine.brain.restores] == [str(training)]
    assert engine.calls == [] and events == []
    assert not checkpoint_dir.exists()


@pytest.mark.parametrize("delay", [-0.1, math.inf, math.nan, 0.15])
def test_retention_rejects_invalid_delay_before_restore(tmp_path, delay):
    engine = RecordingEngine()
    checkpoint = tmp_path / "training.npz"
    engine.brain.checkpoint(checkpoint)
    events = []

    with pytest.raises(ValueError):
        retention_test(engine, checkpoint, delay,
                       schedule=ProtocolSchedule.create(seed=1, paired_identity="A"),
                       stimuli=AssayStimuli(seed=1, family="qualification"),
                       checkpoint_dir=tmp_path, branch_id="T", on_event=events.append)

    assert engine.brain.restores == [] and engine.calls == [] and events == []
