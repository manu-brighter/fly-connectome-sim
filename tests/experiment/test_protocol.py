from dataclasses import asdict
import hashlib
import json
import math

import numpy as np
import pytest

from fly_connectome_sim.experiment import protocol, stimuli
from fly_connectome_sim.experiment.protocol import ProtocolSchedule
from fly_connectome_sim.experiment.stimuli import SyntheticStimuli
from fly_connectome_sim.neural.rule import PARAMETERS


# Historical asdict(ProtocolSchedule.create(condition="reversal", seed=17)) JSON.
LEGACY_V2_JSON = """{
  "version": "ab-protocol/v2", "condition": "reversal", "seed": 17,
  "steps": [
    {"timestamp_ms": 0.0, "duration_ms": 20.0, "phase": "baseline", "stimulus": "A", "stimulation": null, "learning": false},
    {"timestamp_ms": 30.0, "duration_ms": 20.0, "phase": "baseline", "stimulus": "B", "stimulation": null, "learning": false},
    {"timestamp_ms": 60.0, "duration_ms": 20.0, "phase": "pairing", "stimulus": "B", "stimulation": "pam11", "learning": true},
    {"timestamp_ms": 10080.0, "duration_ms": 20.0, "phase": "pairing", "stimulus": null, "stimulation": null, "learning": true},
    {"timestamp_ms": 20100.0, "duration_ms": 20.0, "phase": "pairing", "stimulus": "A", "stimulation": null, "learning": true},
    {"timestamp_ms": 20130.0, "duration_ms": 20.0, "phase": "reward_free_test", "stimulus": "A", "stimulation": null, "learning": false},
    {"timestamp_ms": 20160.0, "duration_ms": 20.0, "phase": "reward_free_test", "stimulus": "B", "stimulation": null, "learning": false}
  ]
}"""


def test_synthetic_v1_frames_keep_historical_bytes():
    stimuli = SyntheticStimuli(seed=17, width=8, height=6)

    assert stimuli.version == "synthetic-ab/v1"
    assert hashlib.sha256(stimuli.frame("A").tobytes()).hexdigest() == (
        "7480acaa88c004bb4dfabe5e25878ea9bd7e1de60a684e04853867d6a021f9b8"
    )
    assert hashlib.sha256(stimuli.frame("B").tobytes()).hexdigest() == (
        "bc1752ec057b13e85688d6cb0b3db3ef9871b1a28a0bdde3340e9eb50fb2fbc3"
    )


def test_legacy_v2_json_reads_its_actual_emitted_shape():
    schedule = protocol.schedule_from_json(LEGACY_V2_JSON)

    assert schedule.version == "ab-protocol/v2"
    assert schedule.condition == "reversal"
    assert schedule.seed == 17
    assert schedule.paired_identity == "B"
    assert len(schedule.steps) == 7
    assert schedule.steps[2].stimulation == "pam11"
    assert json.loads(json.dumps(asdict(schedule)))["steps"][3]["stimulus"] is None


@pytest.mark.parametrize(("condition", "paired", "pulse", "learning"), [
    ("training", "A", "pam11", True),
    ("reversal", "B", "pam11", True),
    ("frozen_plasticity", "A", "pam11", False),
    ("no_dan", "A", None, True),
    ("temporally_unpaired", "A", None, True),
])
def test_legacy_v2_reader_accepts_each_historical_condition(condition, paired, pulse, learning):
    payload = json.loads(LEGACY_V2_JSON)
    payload["condition"] = condition
    payload["steps"][2]["stimulus"] = paired
    payload["steps"][2]["stimulation"] = pulse
    payload["steps"][2]["learning"] = learning
    payload["steps"][3]["stimulation"] = "pam11" if condition == "temporally_unpaired" else None
    payload["steps"][3]["learning"] = learning
    payload["steps"][4]["stimulus"] = "A" if paired == "B" else "B"
    payload["steps"][4]["learning"] = learning

    restored = protocol.schedule_from_json(json.dumps(payload))
    assert restored.condition == condition
    assert restored.paired_identity == paired


def test_legacy_v1_json_is_not_claimed_compatible():
    with pytest.raises(ValueError, match="ab-protocol/v1"):
        protocol.schedule_from_json(LEGACY_V2_JSON.replace("ab-protocol/v2", "ab-protocol/v1"))


@pytest.mark.parametrize("family", ["qualification", "confirmation"])
def test_assay_patterns_are_distinct_with_identical_channel_histograms(family):
    assay = stimuli.AssayStimuli(seed=17, family=family, width=8, height=6)
    frames = [assay.frame(identity) for identity in "ABC"]

    assert assay.version == "associative-stimuli/v1"
    assert all(frame.shape == (6, 8, 3) and frame.dtype == np.uint8 for frame in frames)
    assert all(not np.array_equal(left, right) for left, right in zip(frames, frames[1:]))
    assert not np.array_equal(frames[0], frames[2])
    for channel in range(3):
        histograms = [np.bincount(frame[:, :, channel].ravel(), minlength=256) for frame in frames]
        assert all(np.array_equal(histograms[0], histogram) for histogram in histograms[1:])


def test_assay_family_seed_and_side_are_independent_of_pixel_inventory():
    qualification = stimuli.AssayStimuli(seed=17, family="qualification", width=8, height=6)
    confirmation = stimuli.AssayStimuli(seed=17, family="confirmation", width=8, height=6)
    center = qualification.frame("A", side="center")
    left = qualification.frame("A", side="left")
    right = qualification.frame("A", side="right")

    assert np.array_equal(center, qualification.frame("A", side="center"))
    assert len({hashlib.sha256(frame.tobytes()).hexdigest() for frame in (center, left, right)}) == 3
    assert not np.array_equal(center, confirmation.frame("A"))
    for channel in range(3):
        expected = np.bincount(center[:, :, channel].ravel(), minlength=256)
        assert np.array_equal(expected, np.bincount(left[:, :, channel].ravel(), minlength=256))
        assert np.array_equal(expected, np.bincount(right[:, :, channel].ravel(), minlength=256))


def test_color_assignment_can_change_without_changing_pattern_identity():
    assay = stimuli.AssayStimuli(seed=17, family="qualification", width=8, height=6)

    assert not np.array_equal(assay.frame("A"), assay.frame("A", color_assignment="rotated"))
    assert not np.array_equal(assay.frame("A", color_assignment="rotated"), assay.frame("B", color_assignment="rotated"))


@pytest.mark.parametrize("family", ["unknown", "", None])
def test_assay_requires_a_declared_family(family):
    with pytest.raises(ValueError, match="family"):
        stimuli.AssayStimuli(seed=17, family=family)


@pytest.mark.parametrize(("width", "height"), [
    (2, 3), (3, 1), (3, 2), (4, 1),
    (True, 3), (3.0, 3), (3, False), (3, 3.0),
])
def test_assay_rejects_geometry_without_guaranteed_independent_patterns(width, height):
    with pytest.raises(ValueError, match="dimensions"):
        stimuli.AssayStimuli(seed=17, family="qualification", width=width, height=height)


@pytest.mark.parametrize(("width", "height"), [(3, 3), (4, 3)])
@pytest.mark.parametrize("seed", [0, 17, 255])
def test_minimal_assay_geometries_have_nine_distinct_identity_side_frames(width, height, seed):
    assay = stimuli.AssayStimuli(seed=seed, family="qualification", width=width, height=height)
    frames = [assay.frame(identity, side=side) for identity in "ABC" for side in ("left", "center", "right")]

    assert len({frame.tobytes() for frame in frames}) == 9
    for channel in range(3):
        expected = np.bincount(frames[0][:, :, channel].ravel(), minlength=256)
        assert all(np.array_equal(expected, np.bincount(frame[:, :, channel].ravel(), minlength=256)) for frame in frames)


@pytest.mark.parametrize("family", ["qualification", "confirmation"])
def test_default_assay_identities_change_most_pixels_with_equal_histograms(family):
    assay = stimuli.AssayStimuli(seed=17, family=family)
    frames = {identity: assay.frame(identity) for identity in "ABC"}
    side_frames = [
        assay.frame(identity, side=side)
        for identity in "ABC" for side in ("left", "center", "right")
    ]

    assert len({frame.tobytes() for frame in side_frames}) == 9

    for left, right in (("A", "B"), ("A", "C"), ("B", "C")):
        changed_fraction = np.count_nonzero(np.any(frames[left] != frames[right], axis=2)) / 1024
        assert changed_fraction >= 0.5
        for channel in range(3):
            assert np.array_equal(
                np.bincount(frames[left][:, :, channel].ravel(), minlength=256),
                np.bincount(frames[right][:, :, channel].ravel(), minlength=256),
            )


def test_default_assay_side_is_a_lossless_horizontal_translation():
    assay = stimuli.AssayStimuli(seed=17, family="qualification")
    center = assay.frame("A", side="center")

    assert np.array_equal(assay.frame("A", side="left"), np.roll(center, -8, axis=1))
    assert np.array_equal(assay.frame("A", side="right"), np.roll(center, 8, axis=1))
    assert np.array_equal(center, assay.frame("A"))
    assert not np.array_equal(center, stimuli.AssayStimuli(seed=17, family="confirmation").frame("A"))


@pytest.mark.parametrize("order", [("A", "B"), ("B", "A")])
@pytest.mark.parametrize("paired_identity", ["A", "B"])
def test_presentation_order_and_pairing_identity_vary_independently(order, paired_identity):
    schedule = ProtocolSchedule.create(
        condition="training", seed=17, paired_identity=paired_identity,
        presentation_order=order, training_side="left", test_side="right",
    )

    assert schedule.version == "associative-protocol/v1"
    assert schedule.paired_identity == paired_identity
    assert schedule.presentation_order == order
    assert schedule.training_side == "left"
    assert schedule.test_side == "right"
    assert [step.stimulus for step in schedule.steps if step.phase == "baseline"] == [*order, "C"]
    pairing = [step for step in schedule.steps if step.phase == "pairing"]
    assert [step.stimulus for step in pairing] == [order[0], None, order[1]]
    assert [step.stimulation for step in pairing] == [
        "ppl101" if identity == paired_identity else None
        for identity in (order[0], None, order[1])
    ]
    assert all(step.side == "left" for step in pairing if step.stimulus is not None)
    assert all(step.side == "right" for step in schedule.steps if step.phase == "reward_free_test")
    assert [step.stimulus for step in schedule.steps if step.phase == "reward_free_test"] == [*order, "C"]


def test_reciprocal_pairing_is_a_fresh_matched_schedule_with_explicit_opposite_identity():
    training = ProtocolSchedule.create(condition="training", seed=17, paired_identity="A")
    reciprocal = ProtocolSchedule.create(condition="reciprocal_pairing", seed=17, paired_identity="B")

    assert reciprocal.steps[:3] == training.steps[:3]
    assert [step.timestamp_ms for step in reciprocal.steps] == [step.timestamp_ms for step in training.steps]
    assert reciprocal.steps[-3:] == training.steps[-3:]
    assert next(step for step in reciprocal.steps if step.stimulation == "ppl101").stimulus == "B"


@pytest.mark.parametrize("condition", ["reversal", "no_dan"])
def test_renamed_condition_reports_migration(condition):
    with pytest.raises(ValueError, match="reciprocal_pairing|no_external_dan"):
        ProtocolSchedule.create(condition=condition, seed=17, paired_identity="A")


@pytest.mark.parametrize("condition", ["frozen_plasticity", "no_external_dan", "temporally_unpaired"])
def test_controls_match_exposure_and_timing_with_declared_learning(condition):
    training = ProtocolSchedule.create(condition="training", seed=17, paired_identity="A")
    control = ProtocolSchedule.create(condition=condition, seed=17, paired_identity="A")

    assert [(step.timestamp_ms, step.duration_ms, step.phase, step.stimulus, step.side) for step in control.steps] == [
        (step.timestamp_ms, step.duration_ms, step.phase, step.stimulus, step.side) for step in training.steps
    ]
    pairing = [step for step in control.steps if step.phase == "pairing"]
    assert [step.stimulation for step in pairing] == (
        ["ppl101", None, None] if condition == "frozen_plasticity"
        else [None, None, None] if condition == "no_external_dan"
        else [None, "ppl101", None]
    )
    assert [step.learning for step in pairing] == [condition != "frozen_plasticity"] * 3
    assert all(step.stimulation is None and not step.learning for step in control.steps if step.phase != "pairing")


@pytest.mark.parametrize("inter_trial_ms", [0.0, 10.0, 12000.0])
def test_unpaired_pulse_is_outside_kc_and_dan_trace_windows(inter_trial_ms):
    schedule = ProtocolSchedule.create(
        condition="temporally_unpaired", seed=17, paired_identity="A",
        inter_trial_ms=inter_trial_ms,
    )
    before, pulse, after = [step for step in schedule.steps if step.phase == "pairing"]

    assert (before.stimulus, pulse.stimulus, after.stimulus) == ("A", None, "B")
    assert pulse.stimulation == "ppl101"
    kc_gap_seconds = (pulse.timestamp_ms - before.timestamp_ms - before.duration_ms) / 1000.0
    dan_gap_seconds = (after.timestamp_ms - pulse.timestamp_ms - pulse.duration_ms) / 1000.0
    assert math.exp(-kc_gap_seconds / PARAMETERS["trace_kc_seconds"]) < 0.00005
    assert math.exp(-dan_gap_seconds / PARAMETERS["trace_dan_seconds"]) < 0.00005
    assert pulse.timestamp_ms - before.timestamp_ms - before.duration_ms >= 10000.0
    assert after.timestamp_ms - pulse.timestamp_ms - pulse.duration_ms >= 10000.0


def test_new_schedule_json_round_trips_with_all_factors():
    schedule = ProtocolSchedule.create(
        condition="training", seed=17, paired_identity="B", presentation_order=("B", "A"),
        training_side="right", test_side="left", color_assignment="rotated",
    )

    restored = protocol.schedule_from_json(json.dumps(asdict(schedule), allow_nan=False))
    assert restored == schedule


@pytest.mark.parametrize(("old", "replacement"), [
    ("reversal", "reciprocal_pairing"),
    ("no_dan", "no_external_dan"),
])
def test_new_schedule_json_rejects_legacy_condition_names(old, replacement):
    schedule = ProtocolSchedule.create(seed=17, paired_identity="A")
    payload = asdict(schedule)
    payload["condition"] = old

    with pytest.raises(ValueError, match=replacement):
        protocol.schedule_from_json(json.dumps(payload))


@pytest.mark.parametrize(("path", "value"), [
    (("seed",), True),
    (("paired_identity",), "C"),
    (("paired_identity",), "B"),
    (("paired_identity",), []),
    (("presentation_order",), "AB"),
    (("presentation_order",), ["A", "A"]),
    (("presentation_order",), ["B", "A"]),
    (("presentation_order",), [["A"], "B"]),
    (("training_side",), "up"),
    (("training_side",), "right"),
    (("training_side",), []),
    (("test_side",), None),
    (("color_assignment",), "unknown"),
    (("steps", 0, "timestamp_ms"), float("nan")),
    (("steps", 0, "timestamp_ms"), 1e308),
    (("steps", 0, "timestamp_ms"), -0.1),
    (("steps", 1, "timestamp_ms"), 30.05),
    (("steps", 0, "duration_ms"), float("inf")),
    (("steps", 0, "duration_ms"), 0.05),
    (("steps", 0, "learning"), "yes"),
    (("steps", 0, "stimulation"), "ppl101"),
    (("steps", 3, "stimulation"), "pam11"),
    (("steps", 3, "stimulus"), "B"),
    (("steps", 3, "side"), "right"),
    (("steps", 4, "side"), "left"),
    (("steps", 3, "stimulation"), None),
    (("steps", 4, "timestamp_ms"), 100.0),
])
@pytest.mark.parametrize("source_kind", ["json", "mapping"])
def test_new_reader_rejects_invalid_or_tampered_payload(path, value, source_kind):
    payload = json.loads(json.dumps(asdict(ProtocolSchedule.create(seed=17, paired_identity="A"))))
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    source = json.dumps(payload) if source_kind == "json" else payload

    with pytest.raises(ValueError):
        protocol.schedule_from_json(source)


def test_new_reader_accepts_json_shaped_mapping():
    schedule = ProtocolSchedule.create(seed=17, paired_identity="A")
    payload = json.loads(json.dumps(asdict(schedule)))

    assert protocol.schedule_from_json(payload) == schedule


def test_new_reader_rejects_tuple_order_in_mapping():
    payload = json.loads(json.dumps(asdict(ProtocolSchedule.create(seed=17, paired_identity="A"))))
    payload["presentation_order"] = ("A", "B")

    with pytest.raises(ValueError, match="order"):
        protocol.schedule_from_json(payload)


@pytest.mark.parametrize("version", ["associative-protocol/v1", "ab-protocol/v2"])
@pytest.mark.parametrize("change", ["missing_top", "extra_top", "missing_step", "extra_step", "wrong_count"])
def test_reader_requires_exact_versioned_schema(version, change):
    payload = (
        json.loads(json.dumps(asdict(ProtocolSchedule.create(seed=17, paired_identity="A"))))
        if version == "associative-protocol/v1" else json.loads(LEGACY_V2_JSON)
    )
    if change == "missing_top":
        del payload["seed"]
    elif change == "extra_top":
        payload["unexpected"] = 1
    elif change == "missing_step":
        del payload["steps"][0]["learning"]
    elif change == "extra_step":
        payload["steps"][0]["unexpected"] = 1
    else:
        payload["steps"].pop()

    with pytest.raises(ValueError):
        protocol.schedule_from_json(payload)


@pytest.mark.parametrize(("path", "value"), [
    (("seed",), True),
    (("steps", 0, "timestamp_ms"), float("nan")),
    (("steps", 1, "timestamp_ms"), 30.05),
    (("steps", 2, "stimulation"), "ppl101"),
    (("steps", 2, "stimulus"), "A"),
    (("steps", 3, "learning"), "yes"),
    (("steps", 3, "timestamp_ms"), 80.0),
])
def test_legacy_reader_rejects_invalid_or_tampered_payload(path, value):
    payload = json.loads(LEGACY_V2_JSON)
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValueError):
        protocol.schedule_from_json(payload)


@pytest.mark.parametrize("version", ["associative-protocol/v1", "ab-protocol/v2"])
def test_reader_rejects_nonfinite_json_constants(version):
    payload = (
        asdict(ProtocolSchedule.create(seed=17, paired_identity="A"))
        if version == "associative-protocol/v1" else json.loads(LEGACY_V2_JSON)
    )
    payload["steps"][0]["timestamp_ms"] = float("nan")
    with pytest.raises(ValueError):
        protocol.schedule_from_json(json.dumps(payload))


def test_reader_rejects_duplicate_json_keys():
    duplicated = LEGACY_V2_JSON.replace('"seed": 17', '"seed": 17, "seed": 18')

    with pytest.raises(ValueError, match="duplicate"):
        protocol.schedule_from_json(duplicated)


def test_reader_rejects_mapping_timestamp_beyond_float_range():
    payload = json.loads(json.dumps(asdict(ProtocolSchedule.create(seed=17, paired_identity="A"))))
    payload["steps"][0]["timestamp_ms"] = 10**400

    with pytest.raises(ValueError, match="timestamp"):
        protocol.schedule_from_json(payload)


def test_create_rejects_string_presentation_order():
    with pytest.raises(ValueError, match="order"):
        ProtocolSchedule.create(seed=17, paired_identity="A", presentation_order="AB")


@pytest.mark.parametrize(("factor", "value"), [
    ("condition", []), ("paired_identity", []),
    ("presentation_order", (["A"], "B")),
    ("training_side", []), ("test_side", []),
    ("color_assignment", []),
])
def test_create_rejects_unhashable_factors_with_value_error(factor, value):
    arguments = {"seed": 17, "paired_identity": "A", factor: value}
    with pytest.raises(ValueError):
        ProtocolSchedule.create(**arguments)


@pytest.mark.parametrize("seed", [-1, True, 1.5])
def test_schedule_rejects_seeds_unsupported_by_stimuli(seed):
    with pytest.raises(ValueError):
        ProtocolSchedule.create(seed=seed, paired_identity="A")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_ms", float("nan")), ("duration_ms", float("inf")),
        ("duration_ms", float("-inf")), ("duration_ms", 0.0),
        ("duration_ms", 0.05), ("duration_ms", 10.05),
        ("duration_ms", 500.1), ("inter_trial_ms", float("nan")),
        ("inter_trial_ms", float("inf")), ("inter_trial_ms", float("-inf")),
        ("inter_trial_ms", -0.1), ("inter_trial_ms", 0.05),
        ("inter_trial_ms", 1e308),
        ("duration_ms", True), ("duration_ms", False),
        ("inter_trial_ms", True), ("inter_trial_ms", False),
        ("duration_ms", 10**400), ("inter_trial_ms", 10**400),
    ],
)
def test_schedule_rejects_non_executable_timing(field, value):
    with pytest.raises(ValueError):
        ProtocolSchedule.create(seed=17, paired_identity="A", **{field: value})


@pytest.mark.parametrize(
    ("duration_ms", "inter_trial_ms"),
    [(0.1, 0.0), (500.0, 0.1), (20.0, 12000.0)],
)
def test_schedule_accepts_executable_timing_boundaries_and_zero_seed(duration_ms, inter_trial_ms):
    schedule = ProtocolSchedule.create(
        seed=0, paired_identity="A", duration_ms=duration_ms, inter_trial_ms=inter_trial_ms,
    )

    assert stimuli.AssayStimuli(seed=schedule.seed, family="qualification").frame("A").dtype == np.uint8
    json.dumps(asdict(schedule), allow_nan=False)
    for step in schedule.steps:
        assert step.duration_ms == duration_ms
        assert 0.1 <= step.duration_ms <= 500.0
        assert step.timestamp_ms * 10 == pytest.approx(round(step.timestamp_ms * 10))
    for before, after in zip(schedule.steps, schedule.steps[1:]):
        assert round((after.timestamp_ms - before.timestamp_ms) * 10) >= round(duration_ms * 10)
