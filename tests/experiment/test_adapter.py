from dataclasses import FrozenInstanceError

import pytest

from jogge_fly_brain.experiment.adapter import (
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
