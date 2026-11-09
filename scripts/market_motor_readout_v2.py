"""Offline activity-balanced latch candidate; unvalidated engineering policy.

The frozen v1 decoder owns validation, ordering, clocks and decision support.
This subclass depends explicitly on its private _clear/_consume/_measurement,
_result and state fields. Inputs are declared measurements, not native attestation;
a returned proposal never activates a price.
"""

from types import MappingProxyType

from market_motor_readout import MotorReadout


POLICY_VERSION = "sequential-motor-readout/v2"
BALANCED_POLICY = MappingProxyType({
    "balanced_rearm_samples": 4,
    "balanced_rearm_total_min": 20,
    "balanced_rearm_fraction_numerator": 1,
    "balanced_rearm_fraction_denominator": 10,
})


class MotorReadoutV2(MotorReadout):
    """Retain quiet precedence and add non-overlapping bilateral release blocks."""

    def __init__(self, drinks, *, max_sample_age_ms):
        super().__init__(drinks, max_sample_age_ms=max_sample_age_ms)
        self._bind_identity()

    def _bind_identity(self):
        self._config["policy_version"] = POLICY_VERSION
        self._config["policy"].update(BALANCED_POLICY)

    def _clear(self):
        # The base constructor dispatches here before subclass initialization.
        super()._clear()
        self._balanced = []

    def reconfigure(self, drinks, *, max_sample_age_ms, now_ms):
        # Invalid replacement leaves the prior v2 configuration/boundary intact.
        result = super().reconfigure(drinks, max_sample_age_ms=max_sample_age_ms, now_ms=now_ms)
        self._bind_identity()
        return result

    def _consume(self, sample, now_ms):
        result = super()._consume(sample, now_ms)
        if result["reason"] == "neutral_ready":
            self._balanced.clear()
            return result
        if result["status"] != "waiting" or result["reason"] != "waiting_for_neutral":
            return result
        self._balanced.append(sample)
        if len(self._balanced) < BALANCED_POLICY["balanced_rearm_samples"]:
            return result
        block, self._balanced = self._balanced, []
        # Validate every complete block, including one failing the balance band.
        measurement = self._measurement(block)
        if (measurement["total_count"] < BALANCED_POLICY["balanced_rearm_total_min"]
                or any(abs(value["right_count"] - value["left_count"])
                       * BALANCED_POLICY["balanced_rearm_fraction_denominator"]
                       > (value["left_count"] + value["right_count"])
                       * BALANCED_POLICY["balanced_rearm_fraction_numerator"] for value in block)):
            return result
        self._armed = True
        self._neutral.clear()
        return self._result("ready", "balanced_ready")
