"""Recorded feed choices follow complete measured windows and effective ticks."""

from dataclasses import asdict

import pytest


def evidence(left=0, right=0):
    return {
        "motor_left": left,
        "motor_right": right,
    }


def evaluate(frame_index, *, counts=None, clip_index=0, clip_count=2,
             clip_start_tick=0, end_tick=None, session_limit_tick=80000):
    from fly_connectome_sim.experiment.video_policy import evaluate_video_policy

    if counts is None:
        counts = [evidence()] * (frame_index + 1)
    if end_tick is None:
        end_tick = ((frame_index + 1) * 10000 + 15) // 30
    return evaluate_video_policy(
        counts=counts,
        populations={"motor_left": 1, "motor_right": 1},
        clip_index=clip_index, clip_count=clip_count,
        clip_start_tick=clip_start_tick, frame_index=frame_index,
        end_tick=end_tick, session_limit_tick=session_limit_tick,
    )


def test_rollout_has_no_readout_before_nine_complete_frames():
    for index in (2, 5):
        result = evaluate(index, counts=[evidence(right=1)] * (index + 1))
        assert result["window"] is None
        assert result["readout"] is None
        assert result["action"] == "watch"
        assert result["reason"] == "minimum_dwell"
        assert result["effective_tick"] == ((index + 1) * 10000 + 15) // 30


def test_right_evidence_waits_for_minimum_dwell_then_advances():
    counts = [evidence(right=1)] * 30
    before = evaluate(26, counts=counts[:27])
    assert before["readout"]["action"] == "inspect_right"
    assert before["action"] == "watch" and before["reason"] == "minimum_dwell"
    at = evaluate(29, counts=counts)
    assert at["effective_tick"] == 10000
    assert at["window"] == {
        "start_tick": 7000, "end_tick": 10000, "frame_count": 9,
        "counts": {"motor_left": 0, "motor_right": 9},
        "populations": {"motor_left": 1, "motor_right": 1},
    }
    assert at["readout"] == {
        "adapter_version": "lateral-motor-adapter/v1",
        "signed_difference_hz": 30.0,
        "evidence_strength": 1.0,
        "action": "inspect_right",
    }
    assert at["action"] == "advance" and at["reason"] == "motor_right"
    assert at["next_clip_index"] == 1


@pytest.mark.parametrize("left,right,adapter_action", [
    (1, 0, "inspect_left"),
    (0, 0, "defer"),
    (1, 1, "defer"),
])
def test_left_and_defer_continue_watching(left, right, adapter_action):
    result = evaluate(29, counts=[evidence(left, right)] * 30)
    assert result["readout"]["action"] == adapter_action
    assert result["action"] == "watch"
    assert result["reason"] == "motor_left_or_defer"
    assert result["next_clip_index"] == 0


def test_clip_window_end_overrides_right_and_clears_next_window():
    result = evaluate(119, counts=[evidence(right=1)] * 120,
                      session_limit_tick=80000)
    assert result["effective_tick"] == 40000
    assert result["action"] == "advance" and result["reason"] == "clip_window_end"
    assert result["trigger"] == "clip_window_end"
    next_result = evaluate(2, counts=[evidence()] * 3,
                           clip_index=1, clip_start_tick=40000, end_tick=41000)
    assert next_result["window"] is None


def test_playlist_exhaustion_retains_motor_trigger():
    result = evaluate(29, counts=[evidence(right=1)] * 30,
                      clip_index=1, clip_count=2, clip_start_tick=40000,
                      end_tick=50000)
    assert result["action"] == "stop"
    assert result["reason"] == "playlist_exhausted"
    assert result["trigger"] == "motor_right"
    assert result["next_clip_index"] is None


def test_session_limit_has_priority_over_clip_window_and_motor():
    result = evaluate(119, counts=[evidence(right=1)] * 120,
                      clip_index=1, clip_start_tick=40000, end_tick=80000)
    assert result["action"] == "stop"
    assert result["reason"] == "session_limit"
    assert result["trigger"] == "session_limit"


@pytest.mark.parametrize("index", [0, 1, 3, 8, 29, 119])
def test_policy_only_evaluates_at_three_frame_boundaries(index):
    if index % 3 == 2:
        assert evaluate(index, counts=[evidence()] * (index + 1))
    else:
        with pytest.raises(ValueError):
            evaluate(index, counts=[evidence()] * (index + 1))
