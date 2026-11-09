"""Offline sustained-drive candidate with unvalidated engineering thresholds.

The unchanged v1 decoder owns support, mapping, provenance and clock guards.
This subclass depends on its private _clear/_consume hooks and _armed/_config
state. Fresh sustained activity may repeat a favorite; proposals never activate
prices and do not establish biological intentions or image understanding.
"""

from market_motor_readout import MotorReadout


POLICY_VERSION = "continuous-motor-drive/v1"


class ContinuousMotorDrive(MotorReadout):
    """Consume consecutive supported blocks without a neutral rearm stage."""

    def __init__(self, drinks, *, max_sample_age_ms):
        super().__init__(drinks, max_sample_age_ms=max_sample_age_ms)
        self._bind_identity()

    def _bind_identity(self):
        self._config["policy_version"] = POLICY_VERSION
        self._config["policy"]["command_mode"] = "continuous-supported-drive"
        del self._config["policy"]["neutral_samples"]
        del self._config["policy"]["neutral_total_max"]

    def _clear(self):
        # The base constructor dispatches here before subclass initialization.
        super()._clear()
        self._armed = True

    def reconfigure(self, drinks, *, max_sample_age_ms, now_ms):
        # A failed replacement retains identity and the base wall watermark.
        result = super().reconfigure(drinks, max_sample_age_ms=max_sample_age_ms, now_ms=now_ms)
        self._bind_identity()
        return result

    def _consume(self, sample, now_ms):
        result = super()._consume(sample, now_ms)
        if result["status"] == "direction" and result["reason"] == "direction_supported":
            self._armed = True
        return result
