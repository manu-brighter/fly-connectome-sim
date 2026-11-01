from dataclasses import FrozenInstanceError, asdict
import json
import math

import pytest

from fly_connectome_sim.experiment import adapter as adapter_module

from fly_connectome_sim.experiment.adapter import (
    DEFAULT_PREFERENCE_ADAPTER,
    PreferenceAdapter,
)


def test_predeclared_adapter_configuration_is_versioned_and_immutable():
    assert DEFAULT_PREFERENCE_ADAPTER.version == "preference-adapter/v1"
    assert DEFAULT_PREFERENCE_ADAPTER.mbon07_field == "mbon07"
    assert DEFAULT_PREFERENCE_ADAPTER.mbon11_field == "mbon11"
    assert DEFAULT_PREFERENCE_ADAPTER.motor_left_field == "motor_left"
    assert DEFAULT_PREFERENCE_ADAPTER.motor_right_field == "motor_right"

    with pytest.raises(FrozenInstanceError):
        DEFAULT_PREFERENCE_ADAPTER.action_threshold = 2.0


@pytest.mark.parametrize(
    ("rates", "signed_preference", "confidence", "action"),
    [
        ((30.0, 10.0, 5.0, 15.0), 15.0, 0.5, "inspect_right"),
        ((10.0, 30.0, 15.0, 5.0), -15.0, 0.5, "inspect_left"),
        ((10.0, 10.0, 10.0, 10.0), 0.0, 0.0, "defer"),
        ((0.0, 0.0, 0.0, 0.0), 0.0, 0.0, "defer"),
        ((4.0, 0.0, 0.0, 0.0), 2.0, 1.0, "inspect_right"),
        ((0.0, 4.0, 0.0, 0.0), -2.0, 1.0, "inspect_left"),
        ((0.0, 0.0, 4.0, 0.0), -2.0, 1.0, "inspect_left"),
        ((0.0, 0.0, 0.0, 4.0), 2.0, 1.0, "inspect_right"),
        ((1.98, 0.0, 0.0, 0.0), 0.99, 1.0, "defer"),
        ((2.0, 0.0, 0.0, 0.0), 1.0, 1.0, "defer"),
        ((2.02, 0.0, 0.0, 0.0), 1.01, 1.0, "inspect_right"),
        ((0.0, 1.98, 0.0, 0.0), -0.99, 1.0, "defer"),
        ((0.0, 2.0, 0.0, 0.0), -1.0, 1.0, "defer"),
        ((0.0, 2.02, 0.0, 0.0), -1.01, 1.0, "inspect_left"),
    ],
)
def test_adapter_uses_only_declared_neural_rates_for_preference_and_action(
    rates, signed_preference, confidence, action
):
    adapter = PreferenceAdapter()
    neural_rates = dict(
        zip(("mbon07", "mbon11", "motor_left", "motor_right"), rates)
    )

    with_metadata = adapter.adapt(
        {
            "rates_hz": neural_rates,
            "label": "A",
            "reward": True,
            "event": {"kind": "pairing"},
        }
    )
    changed_metadata = adapter.adapt(
        {
            "rates_hz": neural_rates,
            "label": "B",
            "reward": False,
            "event": {"kind": "reward-free test"},
        }
    )

    assert with_metadata == changed_metadata
    assert with_metadata.signed_preference == signed_preference
    assert with_metadata.confidence == confidence
    assert with_metadata.action == action


def motor_adapter(**configuration):
    adapter_type = getattr(adapter_module, "LateralMotorAdapter", None)
    assert adapter_type is not None, "Missing motor-only adapter API"
    return adapter_type(**configuration)


@pytest.mark.parametrize(
    ("left", "right", "difference", "strength", "action"),
    [
        (0, 0, 0, 0, "defer"),
        (5, 5, 0, 0, "defer"),
        (0, 0.99, 0.99, 1, "defer"),
        (0, 1, 1, 1, "defer"),
        (0, 1.01, 1.01, 1, "inspect_right"),
        (0.99, 0, -0.99, 1, "defer"),
        (1, 0, -1, 1, "defer"),
        (1.01, 0, -1.01, 1, "inspect_left"),
        (5, 15, 10, 0.5, "inspect_right"),
        (15, 5, -10, 0.5, "inspect_left"),
        (1e308, 1.5e308, 5e307, 0.2, "inspect_right"),
        (1.5e308, 1e308, -5e307, 0.2, "inspect_left"),
        (1.7e308, 1.7e308, 0, 0, "defer"),
    ],
)
def test_motor_only_arithmetic_thresholds_and_extreme_finite_rates(
    left, right, difference, strength, action,
):
    decision = motor_adapter().adapt({"rates_hz": {"motor_left": left, "motor_right": right}})
    assert decision.signed_difference_hz == pytest.approx(difference)
    assert decision.evidence_strength == pytest.approx(strength)
    assert decision.action == action
    assert math.isfinite(decision.signed_difference_hz)
    assert json.loads(json.dumps(asdict(decision), allow_nan=False)) == {
        "adapter_version": "lateral-motor-adapter/v1",
        "signed_difference_hz": decision.signed_difference_hz,
        "evidence_strength": decision.evidence_strength,
        "action": action,
    }


def test_motor_readout_is_independent_of_mbons_and_event_metadata():
    adapter = motor_adapter()
    original = adapter.adapt({"rates_hz": {"motor_left": 5, "motor_right": 15}})
    changed = adapter.adapt({
        "rates_hz": {"motor_left": 5, "motor_right": 15, "mbon07": -999, "mbon11": object()},
        "stimulus": "B", "condition": "paired", "external_reward": True,
        "event": {"kind": "pairing"},
    })
    assert original == changed
    assert adapter.adapt({"rates_hz": {"motor_left": 15, "motor_right": 5}}).action == "inspect_left"
    with pytest.raises(FrozenInstanceError):
        adapter.action_threshold_hz = 2
    with pytest.raises(FrozenInstanceError):
        original.action = "defer"


@pytest.mark.parametrize("bad", [True, False, "2", None, [], {}, -1, float("inf"), float("nan"), 10 ** 400])
@pytest.mark.parametrize("side", ["motor_left", "motor_right"])
def test_motor_rates_reject_boolean_nonnumeric_nonfinite_and_negative(bad, side):
    rates = {"motor_left": 2, "motor_right": 4, side: bad}
    with pytest.raises(ValueError):
        motor_adapter().adapt({"rates_hz": rates})


@pytest.mark.parametrize("telemetry", [{}, {"rates_hz": []}, {"rates_hz": {}}, {"rates_hz": {"motor_left": 1}}])
def test_motor_readout_requires_both_measured_motor_rates(telemetry):
    with pytest.raises(ValueError):
        motor_adapter().adapt(telemetry)


@pytest.mark.parametrize("bad", [True, "1", None, -1, float("inf"), float("nan"), 10 ** 400])
def test_motor_threshold_configuration_is_strict(bad):
    with pytest.raises(ValueError):
        motor_adapter(action_threshold_hz=bad)


@pytest.mark.parametrize("version", [None, True, "preference-adapter/v1", "lateral-motor-adapter/v2"])
def test_motor_configuration_requires_supported_version(version):
    with pytest.raises(ValueError):
        motor_adapter(version=version)


def test_motor_version_requires_a_json_string_instead_of_equal_nonscalar():
    class EqualVersion:
        def __eq__(self, other):
            return True

    with pytest.raises(ValueError):
        motor_adapter(version=EqualVersion())


def test_motor_custom_threshold_uses_strict_hz_boundary():
    telemetry = {"rates_hz": {"motor_left": 2, "motor_right": 4}}
    assert motor_adapter(action_threshold_hz=2).adapt(telemetry).action == "defer"
    assert motor_adapter(action_threshold_hz=0).adapt(telemetry).action == "inspect_right"
