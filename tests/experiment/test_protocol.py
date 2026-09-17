from dataclasses import asdict
import json
import math

import pytest
import numpy as np

from jogge_fly_brain.experiment.protocol import ProtocolSchedule
from jogge_fly_brain.experiment.stimuli import SyntheticStimuli
from jogge_fly_brain.neural.rule import PARAMETERS


def test_synthetic_stimuli_are_seed_deterministic_and_distinct_between_a_and_b():
    first = SyntheticStimuli(seed=17, width=8, height=6)
    repeated = SyntheticStimuli(seed=17, width=8, height=6)

    assert np.array_equal(first.frame("A"), repeated.frame("A"))
    assert np.array_equal(first.frame("B"), repeated.frame("B"))
    assert first.frame("A").shape == (6, 8, 3)
    assert first.frame("A").dtype == np.uint8
    assert not np.array_equal(first.frame("A"), first.frame("B"))


def test_training_schedule_has_baseline_pairing_and_reward_free_test_steps():
    schedule = ProtocolSchedule.create(condition="training", seed=17)

    assert schedule.seed == 17
    assert [step.timestamp_ms for step in schedule.steps] == [
        0.0,
        30.0,
        60.0,
        10080.0,
        20100.0,
        20130.0,
        20160.0,
    ]
    assert [
        (step.phase, step.stimulus, step.stimulation, step.learning)
        for step in schedule.steps
    ] == [
        ("baseline", "A", None, False),
        ("baseline", "B", None, False),
        ("pairing", "A", "pam11", True),
        ("pairing", None, None, True),
        ("pairing", "B", None, True),
        ("reward_free_test", "A", None, False),
        ("reward_free_test", "B", None, False),
    ]


@pytest.mark.parametrize(
    ("condition", "pairing", "expected_learning"),
    [
        ("reversal", ("B", "pam11"), True),
        ("frozen_plasticity", ("A", "pam11"), False),
        ("no_dan", ("A", None), True),
        ("temporally_unpaired", (None, "pam11"), True),
    ],
)
def test_control_schedules_share_the_identical_baseline(
    condition, pairing, expected_learning
):
    training = ProtocolSchedule.create(condition="training", seed=17)
    control = ProtocolSchedule.create(condition=condition, seed=17)

    assert control.steps[:2] == training.steps[:2]
    paired_step = next(
        step
        for step in control.steps
        if step.phase == "pairing"
        and step.stimulus == pairing[0]
        and step.stimulation == pairing[1]
    )
    assert paired_step.phase == "pairing"
    assert paired_step.learning is expected_learning
    assert all(
        step.stimulation is None
        for step in control.steps
        if step.phase == "reward_free_test"
    )


@pytest.mark.parametrize("inter_trial_ms", [0.0, 10.0, 12000.0])
def test_unpaired_pulse_is_outside_kc_and_dan_trace_windows(inter_trial_ms):
    schedule = ProtocolSchedule.create(
        condition="temporally_unpaired",
        seed=17,
        inter_trial_ms=inter_trial_ms,
    )
    before, pulse, after = [
        step for step in schedule.steps if step.phase == "pairing"
    ]

    assert (before.stimulus, pulse.stimulus, after.stimulus) == ("A", None, "B")
    assert pulse.stimulation == "pam11"
    kc_gap_seconds = (
        pulse.timestamp_ms - before.timestamp_ms - before.duration_ms
    ) / 1000.0
    dan_gap_seconds = (
        after.timestamp_ms - pulse.timestamp_ms - pulse.duration_ms
    ) / 1000.0
    assert math.exp(-kc_gap_seconds / PARAMETERS["trace_kc_seconds"]) < 0.00005
    assert math.exp(-dan_gap_seconds / PARAMETERS["trace_dan_seconds"]) < 0.00005


@pytest.mark.parametrize(
    "condition",
    ["reversal", "frozen_plasticity", "no_dan", "temporally_unpaired"],
)
def test_control_schedules_match_training_exposure_and_elapsed_time(condition):
    training = ProtocolSchedule.create(condition="training", seed=17)
    control = ProtocolSchedule.create(condition=condition, seed=17)

    assert [
        (step.timestamp_ms, step.duration_ms, step.phase) for step in control.steps
    ] == [
        (step.timestamp_ms, step.duration_ms, step.phase) for step in training.steps
    ]
    assert sorted(step.stimulus or "" for step in control.steps) == sorted(
        step.stimulus or "" for step in training.steps
    )


@pytest.mark.parametrize("seed", [-1, True, 1.5])
def test_schedule_rejects_seeds_unsupported_by_stimuli(seed):
    with pytest.raises(ValueError):
        ProtocolSchedule.create(seed=seed)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_ms", float("nan")),
        ("duration_ms", float("inf")),
        ("duration_ms", float("-inf")),
        ("duration_ms", 0.0),
        ("duration_ms", 0.05),
        ("duration_ms", 10.05),
        ("duration_ms", 500.1),
        ("inter_trial_ms", float("nan")),
        ("inter_trial_ms", float("inf")),
        ("inter_trial_ms", float("-inf")),
        ("inter_trial_ms", -0.1),
        ("inter_trial_ms", 0.05),
        ("inter_trial_ms", 1e308),
    ],
)
def test_schedule_rejects_non_executable_timing(field, value):
    with pytest.raises(ValueError):
        ProtocolSchedule.create(seed=17, **{field: value})


@pytest.mark.parametrize(
    ("duration_ms", "inter_trial_ms"),
    [(0.1, 0.0), (500.0, 0.1), (20.0, 12000.0)],
)
def test_schedule_accepts_executable_timing_boundaries_and_zero_seed(
    duration_ms, inter_trial_ms
):
    schedule = ProtocolSchedule.create(
        seed=0,
        duration_ms=duration_ms,
        inter_trial_ms=inter_trial_ms,
    )

    assert SyntheticStimuli(seed=schedule.seed).frame("A").dtype == np.uint8
    json.dumps(asdict(schedule), allow_nan=False)
    for step in schedule.steps:
        assert step.duration_ms == duration_ms
        assert 0.1 <= step.duration_ms <= 500.0
        assert step.timestamp_ms * 10 == pytest.approx(round(step.timestamp_ms * 10))
    for before, after in zip(schedule.steps, schedule.steps[1:]):
        assert round((after.timestamp_ms - before.timestamp_ms) * 10) >= round(
            duration_ms * 10
        )
