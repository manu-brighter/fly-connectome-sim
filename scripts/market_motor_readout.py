"""Pure offline sequential motor decoder with unvalidated engineering thresholds.

Inputs are declared measurements, not authenticated native evidence. A returned
proposal never activates a price. All wall times share the caller's monotonic
clock domain; model ticks and delivery freshness are separate clocks.
"""

from copy import deepcopy
from hashlib import sha256
import json
import re
from types import MappingProxyType


POLICY_VERSION = "sequential-motor-readout/v1"
JSON_SAFE_MAX = 2**53 - 1
POLICY = MappingProxyType({
    "sample_ticks": 5000,
    "block_samples": 4,
    "direction_total_min": 20,
    "direction_net_min": 4,
    "direction_fraction_numerator": 1,
    "direction_fraction_denominator": 5,
    "direction_sign_samples_min": 3,
    "neutral_samples": 2,
    "neutral_total_max": 2,
    "price_total_min": 20,
    "price_active_samples_min": 3,
    "path_model_ticks": 600000,
    "path_wall_ms": 300000,
    "history_samples_max": 128,
})
SAMPLE_INTEGERS = (
    "observation_index", "start_tick", "end_tick", "left_count", "right_count",
    "wall_start_ms", "wall_completion_ms",
)
DRINK_FIELDS = {"id", "minimum_rappen", "maximum_rappen", "grid_rappen"}


def _integer(value, name):
    if type(value) is not int or not 0 <= value <= JSON_SAFE_MAX:
        raise ValueError(f"{name} must be a nonnegative JSON-safe integer")
    return value


def _identity(value, name):
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", value) is None:
        raise ValueError(f"{name} must be a safe nonempty identity of at most128 characters")


def _configuration(drinks, max_sample_age_ms):
    _integer(max_sample_age_ms, "max_sample_age_ms")
    if not 1 <= max_sample_age_ms <= 300000:
        raise ValueError("max_sample_age_ms must be between1 and300000")
    if not isinstance(drinks, (list, tuple)) or not 10 <= len(drinks) <= 20:
        raise ValueError("drinks must be an ordered list of10–20 entries")
    frozen, seen = [], set()
    for drink in drinks:
        if not isinstance(drink, dict) or set(drink) != DRINK_FIELDS:
            raise ValueError("each drink must declare exactly id/minimum_rappen/maximum_rappen/grid_rappen")
        _identity(drink["id"], "drink id")
        if drink["id"] in seen:
            raise ValueError("drink IDs must be distinct")
        seen.add(drink["id"])
        for name in DRINK_FIELDS - {"id"}:
            _integer(drink[name], name)
        minimum, maximum, grid = (drink[name] for name in ("minimum_rappen", "maximum_rappen", "grid_rappen"))
        if minimum > maximum or grid == 0 or (maximum - minimum) % grid:
            raise ValueError("drink range must be ordered and divisible by its positive grid")
        frozen.append(deepcopy(drink))
    return {"policy_version": POLICY_VERSION, "policy": dict(POLICY),
            "drinks": frozen, "max_sample_age_ms": max_sample_age_ms}


class MotorReadout:
    """Deterministic decoder; a new object is an explicit ordering restart.

    consume() returns status/reason/phase/interval/proposal. Explicit resets clear
    decision evidence but preserve ordering watermarks. pause/resume/reset and
    reconfigure require current monotonic milliseconds to reject queued evidence.
    Validation errors clear decision evidence and raise ValueError.
    """

    def __init__(self, drinks, *, max_sample_age_ms):
        self._config = _configuration(drinks, max_sample_age_ms)
        self._now_ms = None
        self._last = None
        self._boundary_ms = 0
        self._paused = False
        self._clear()

    @property
    def configuration(self):
        return deepcopy(self._config)

    @property
    def policy_version(self):
        return self._config["policy_version"]

    @property
    def configuration_sha256(self):
        canonical = json.dumps(self._config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def _clear(self):
        self._lo, self._hi = 0, len(self._config["drinks"])
        self._phase = "direction"
        self._armed = False
        self._neutral = []
        self._block = []
        self._history = []
        self._decisions = []
        self._anchor = None

    def _result(self, status, reason, proposal=None):
        return deepcopy({"status": status, "reason": reason, "phase": self._phase,
                         "interval": [self._lo, self._hi], "proposal": proposal})

    def _drop(self, reason):
        self._clear()
        return self._result("reset", reason)

    def _wall(self, now_ms):
        try:
            _integer(now_ms, "now_ms")
            if self._now_ms is not None and now_ms < self._now_ms:
                raise ValueError("now_ms must not decrease")
        except ValueError:
            self._clear()
            raise
        self._now_ms = now_ms

    def reset(self, *, now_ms):
        self._wall(now_ms)
        self._boundary_ms = now_ms
        return self._drop("explicit_reset")

    def pause(self, *, now_ms):
        self._wall(now_ms)
        self._paused = True
        self._boundary_ms = now_ms
        self._clear()
        return self._result("paused", "paused")

    def resume(self, *, now_ms):
        self._wall(now_ms)
        self._paused = False
        self._boundary_ms = now_ms
        return self._drop("resumed")

    def reconfigure(self, drinks, *, max_sample_age_ms, now_ms):
        self._wall(now_ms)
        self._clear()
        replacement = _configuration(drinks, max_sample_age_ms)
        self._config = replacement
        self._boundary_ms = now_ms
        return self._drop("reconfigured")

    def _sample(self, sample, now_ms):
        if not isinstance(sample, dict):
            raise ValueError("sample must be a mapping")
        required = set(SAMPLE_INTEGERS) | {"source_sha256", "session_id", "input_version", "frame_sha256"}
        if set(sample) != required:
            raise ValueError("sample must declare exactly the required measurement fields")
        for name in SAMPLE_INTEGERS:
            _integer(sample[name], name)
        for name in ("session_id", "input_version"):
            _identity(sample[name], name)
        for name in ("source_sha256", "frame_sha256"):
            if not isinstance(sample[name], str) or re.fullmatch(r"[0-9a-f]{64}", sample[name]) is None:
                raise ValueError(f"{name} must be an exact lowercase SHA256")
        if sample["end_tick"] - sample["start_tick"] != POLICY["sample_ticks"]:
            raise ValueError("each sample must span exactly5000 model ticks")
        if not sample["wall_start_ms"] <= sample["wall_completion_ms"] <= now_ms:
            raise ValueError("wall clocks must satisfy start <=completion <=now_ms")
        _integer(sample["left_count"] + sample["right_count"], "sample total_count")
        return deepcopy(sample)

    def _establish(self, sample):
        self._last = {name: sample[name] for name in (
            "source_sha256", "session_id", "observation_index", "end_tick", "wall_completion_ms",
        )}

    def _order(self, sample):
        if self._last is None:
            self._establish(sample)
            return None
        last = self._last
        key = ("source_sha256", "session_id")
        if any(sample[name] != last[name] for name in key):
            if (sample["wall_start_ms"] < last["wall_completion_ms"]
                    or sample["wall_completion_ms"] <= last["wall_completion_ms"]):
                return "old_transition"
            self._establish(sample)
            return "source_session_changed"
        if (sample["observation_index"] <= last["observation_index"]
                or sample["start_tick"] < last["end_tick"]
                or sample["wall_start_ms"] < last["wall_completion_ms"]):
            return "sample_out_of_order"
        contiguous = (sample["observation_index"] == last["observation_index"] + 1
                      and sample["start_tick"] == last["end_tick"])
        self._establish(sample)
        return None if contiguous else "sample_gap"

    def _expired(self, anchor, sample, now_ms):
        return (sample["end_tick"] - anchor["start_tick"] >= POLICY["path_model_ticks"]
                or now_ms - anchor["wall_start_ms"] >= POLICY["path_wall_ms"])

    def _measurement(self, block):
        left = sum(sample["left_count"] for sample in block)
        right = sum(sample["right_count"] for sample in block)
        for name, value in (("block left_count", left), ("block right_count", right), ("block total_count", left + right)):
            _integer(value, name)
        return {"first_observation_index": block[0]["observation_index"],
                "last_observation_index": block[-1]["observation_index"],
                "start_tick": block[0]["start_tick"], "end_tick": block[-1]["end_tick"],
                "wall_start_ms": block[0]["wall_start_ms"],
                "wall_completion_ms": block[-1]["wall_completion_ms"],
                "left_count": left, "right_count": right, "total_count": left + right}

    def consume(self, sample, *, now_ms):
        self._wall(now_ms)
        try:
            sample = self._sample(sample, now_ms)
            return self._consume(sample, now_ms)
        except ValueError:
            self._clear()
            raise

    def _consume(self, sample, now_ms):
        if self._paused:
            return self._result("paused", "paused")
        if sample["wall_completion_ms"] < self._boundary_ms:
            return self._drop("before_boundary")
        if now_ms - sample["wall_completion_ms"] > self._config["max_sample_age_ms"]:
            return self._drop("stale_sample")
        reason = self._order(sample)
        if reason:
            return self._drop(reason)
        if self._anchor is not None:
            if self._expired(self._anchor, sample, now_ms):
                return self._drop("path_expired")
            if len(self._history) >= POLICY["history_samples_max"]:
                return self._drop("history_limit")
            self._history.append(sample)
        if not self._armed:
            if sample["left_count"] + sample["right_count"] <= POLICY["neutral_total_max"]:
                self._neutral.append(sample)
            else:
                self._neutral.clear()
            if len(self._neutral) == POLICY["neutral_samples"]:
                self._armed = True
                self._neutral.clear()
                return self._result("ready", "neutral_ready")
            return self._result("waiting", "waiting_for_neutral")
        self._block.append(sample)
        if len(self._block) < POLICY["block_samples"]:
            return self._result("collecting", "incomplete_block")
        block, self._block = self._block, []
        measurement = self._measurement(block)
        total = measurement["total_count"]
        if self._phase == "price":
            active = sum(value["left_count"] + value["right_count"] > 0 for value in block)
            if total < POLICY["price_total_min"] or active < POLICY["price_active_samples_min"]:
                return self._result("deferred", "unsupported_price")
            drink = self._config["drinks"][self._lo]
            steps = (drink["maximum_rappen"] - drink["minimum_rappen"]) // drink["grid_rappen"]
            k = (2 * measurement["right_count"] * steps + total) // (2 * total)
            proposal = {"policy_version": self.policy_version,
                        "configuration_sha256": self.configuration_sha256,
                        "source_sha256": sample["source_sha256"], "session_id": sample["session_id"],
                        "drink_id": drink["id"], "target_rappen": drink["minimum_rappen"] + k * drink["grid_rappen"],
                        "path_start_tick": self._anchor["start_tick"],
                        "path_start_wall_ms": self._anchor["wall_start_ms"],
                        "completion_tick": sample["end_tick"], "completion_wall_ms": sample["wall_completion_ms"],
                        "emitted_wall_ms": now_ms, "decisions": self._decisions,
                        "price_measurement": measurement, "input_history": self._history}
            self._clear()
            return self._result("proposal", "price_supported", proposal)
        net = measurement["right_count"] - measurement["left_count"]
        matching = sum((value["right_count"] - value["left_count"]) * net > 0 for value in block)
        if (total < POLICY["direction_total_min"] or abs(net) < POLICY["direction_net_min"]
                or abs(net) * POLICY["direction_fraction_denominator"] < total * POLICY["direction_fraction_numerator"]
                or matching < POLICY["direction_sign_samples_min"]):
            return self._result("deferred", "unsupported_direction")
        if self._anchor is None:
            if self._expired(block[0], sample, now_ms):
                return self._drop("path_expired")
            self._anchor = block[0]
            self._history = list(block)
        mid = (self._lo + self._hi) // 2
        if net > 0:
            self._lo = mid
        else:
            self._hi = mid
        self._decisions.append({"direction": "upper" if net > 0 else "lower", **measurement})
        self._armed = False
        if self._hi - self._lo == 1:
            self._phase = "price"
        return self._result("direction", "direction_supported")
