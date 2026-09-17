"""Engineered, predeclared preference readout for neural telemetry."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Mapping


AdapterAction = Literal["inspect_left", "inspect_right", "defer"]


@dataclass(frozen=True)
class PreferenceDecision:
    """A JSON-safe decision derived exclusively from declared neural rates."""

    adapter_version: str
    signed_preference: float
    confidence: float
    action: AdapterAction


@dataclass(frozen=True)
class PreferenceAdapter:
    """Frozen v1 readout; this is an engineered adapter, not biological validation."""

    version: str = "preference-adapter/v1"
    mbon07_field: str = "mbon07"
    mbon11_field: str = "mbon11"
    motor_left_field: str = "motor_left"
    motor_right_field: str = "motor_right"
    mbon_weight: float = 0.5
    lateral_motor_weight: float = 0.5
    action_threshold: float = 1.0

    def adapt(self, telemetry: Mapping[str, object]) -> PreferenceDecision:
        """Map declared MBON and lateral motor rates to one preference action."""
        try:
            rates = telemetry["rates_hz"]
        except KeyError as error:
            raise ValueError("Telemetry must contain rates_hz") from error
        if not isinstance(rates, Mapping):
            raise ValueError("Telemetry rates_hz must be a mapping")

        mbon07 = self._rate(rates, self.mbon07_field)
        mbon11 = self._rate(rates, self.mbon11_field)
        motor_left = self._rate(rates, self.motor_left_field)
        motor_right = self._rate(rates, self.motor_right_field)

        mbon_evidence = self.mbon_weight * (mbon07 - mbon11)
        motor_evidence = self.lateral_motor_weight * (motor_right - motor_left)
        signed_preference = mbon_evidence + motor_evidence
        total_evidence = (
            self.mbon_weight * (abs(mbon07) + abs(mbon11))
            + self.lateral_motor_weight * (abs(motor_left) + abs(motor_right))
        )
        confidence = abs(signed_preference) / total_evidence if total_evidence else 0.0

        if signed_preference > self.action_threshold:
            action: AdapterAction = "inspect_right"
        elif signed_preference < -self.action_threshold:
            action = "inspect_left"
        else:
            action = "defer"

        return PreferenceDecision(
            adapter_version=self.version,
            signed_preference=signed_preference,
            confidence=confidence,
            action=action,
        )

    @staticmethod
    def _rate(rates: Mapping[object, object], name: str) -> float:
        try:
            value = float(rates[name])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Telemetry requires a finite {name} rate") from error
        if not math.isfinite(value):
            raise ValueError(f"Telemetry requires a finite {name} rate")
        return value


DEFAULT_PREFERENCE_ADAPTER = PreferenceAdapter()
