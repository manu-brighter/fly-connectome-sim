"""Synthetic software contract tests; no neural reachability qualification."""

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/market_motor_readout.py"
ROUTES = (
    "0000", "0001", "0010", "00110", "00111", "0100", "0101", "0110", "01110", "01111",
    "1000", "1001", "1010", "10110", "10111", "1100", "1101", "1110", "11110", "11111",
)


@pytest.fixture
def module():
    assert SCRIPT.is_file(), "The pure offline motor readout implementation is missing"
    spec = importlib.util.spec_from_file_location("market_motor_readout", SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def drinks(count=20):
    return [{"id": f"drink-{i}", "minimum_rappen": 400, "maximum_rappen": 700, "grid_rappen": 50}
            for i in range(count)]


class Stream:
    def __init__(self, decoder):
        self.decoder = decoder
        self.index = 0
        self.tick = 0
        self.wall = 0
        self.session = "synthetic-session"
        self.source = "a" * 64

    def sample(self, left=0, right=0, **changes):
        value = {"source_sha256": self.source, "session_id": self.session,
                 "observation_index": self.index, "start_tick": self.tick, "end_tick": self.tick + 5000,
                 "left_count": left, "right_count": right, "input_version": f"frame-{self.index}",
                 "frame_sha256": sha256(str(self.index).encode()).hexdigest(),
                 "wall_start_ms": self.wall, "wall_completion_ms": self.wall + 500}
        value.update(changes)
        self.index = value["observation_index"] + 1
        self.tick = value["end_tick"]
        self.wall = value["wall_completion_ms"]
        return value

    def send(self, left=0, right=0, *, now_ms=None, **changes):
        value = self.sample(left, right, **changes)
        return self.decoder.consume(value, now_ms=self.wall if now_ms is None else now_ms)

    def neutral(self):
        self.send(1, 1)
        return self.send(0, 2)

    def block(self, counts):
        results = [self.send(left, right) for left, right in counts]
        assert all(result["proposal"] is None for result in results[:-1])
        return results[-1]

    def direction(self, bit):
        self.neutral()
        return self.block([(2, 4) if bit == "1" else (4, 2)] * 4)

    def leaf(self, route="0000"):
        for bit in route:
            result = self.direction(bit)
        assert result["phase"] == "price"
        return result


def make(module, config=None, **kwargs):
    decoder = module.MotorReadout(drinks() if config is None else config,
                                 max_sample_age_ms=kwargs.pop("max_sample_age_ms", 5000), **kwargs)
    return decoder, Stream(decoder)


@pytest.mark.parametrize("index,route", list(enumerate(ROUTES)))
def test_all_twenty_literal_routes_emit_distinct_stable_ids(module, index, route):
    decoder, stream = make(module)
    stream.leaf(route)
    stream.neutral()
    result = stream.block([(5, 0)] * 4)
    proposal = result["proposal"]
    assert result["status"] == "proposal"
    assert proposal["drink_id"] == f"drink-{index}"
    assert proposal["target_rappen"] == 400
    assert len(proposal["decisions"]) == len(route)
    assert proposal["source_sha256"] == "a" * 64
    assert proposal["session_id"] == "synthetic-session"
    assert proposal["path_start_tick"] == 10000
    assert proposal["path_start_wall_ms"] == 1000
    assert proposal["completion_tick"] == stream.tick
    assert proposal["completion_wall_ms"] == stream.wall
    assert proposal["configuration_sha256"] == decoder.configuration_sha256
    assert stream.block([(0, 10)] * 4)["proposal"] is None


@pytest.mark.parametrize("counts,accepted", [
    ([(2, 3), (2, 3), (2, 3), (2, 3)], True),  # T20, net4, exact20%, 4 signs
    ([(1, 3), (1, 3), (1, 3), (4, 4)], True),  # exactly3 signs
    ([(2, 3), (2, 3), (2, 3), (1, 3)], False),  # T19
    ([(2, 3), (2, 3), (2, 3), (3, 3)], False),  # net3
    ([(2, 3), (2, 3), (2, 3), (3, 4)], False),  # net4/T22 below20%
    ([(0, 6), (0, 6), (6, 0), (0, 0)], False),  # only2 matching signs
    ([(0, 0)] * 4, False),
    ([(5, 5)] * 4, False),
    ([(0, 10), (10, 0), (0, 10), (10, 0)], False),
    ([(0, 1), (0, 0), (0, 0), (0, 0)], False),
])
def test_exact_direction_support_and_abstention(module, counts, accepted):
    _, stream = make(module)
    stream.neutral()
    result = stream.block(counts)
    assert result["status"] == ("direction" if accepted else "deferred")
    assert result["interval"] == ([10, 20] if accepted else [0, 20])


def test_neutral_is_required_and_blocks_never_overlap(module):
    _, stream = make(module)
    assert stream.block([(0, 20)] * 4)["interval"] == [0, 20]
    stream.send(0, 0)
    stream.send(1, 2)  # breaks neutral streak
    assert stream.block([(0, 20)] * 4)["interval"] == [0, 20]
    stream.neutral()
    assert stream.block([(0, 5)] * 3 + [(5, 0)])["status"] == "direction"
    assert stream.block([(0, 20)] * 4)["interval"] == [10, 20]
    stream.neutral()
    assert stream.block([(5, 0), (5, 0), (0, 5), (0, 5)])["status"] == "deferred"
    assert stream.block([(5, 0)] * 4)["interval"] == [10, 15]


@pytest.mark.parametrize("counts,target", [
    ([(0, 5)] * 4, 700),
    ([(5, 0)] * 4, 400),
    ([(5, 1)] * 4, 450),
    ([(11, 1)] * 4, 450),  # ratio1/12 *6 steps = exact half, round up
    ([(12, 1)] * 4, 400),
])
def test_separate_supported_price_endpoints_and_half_up_grid(module, counts, target):
    _, stream = make(module)
    stream.leaf()
    assert stream.block([(0, 10)] * 4)["proposal"] is None
    stream.neutral()
    result = stream.block(counts)
    assert result["proposal"]["target_rappen"] == target
    assert result["proposal"]["price_measurement"]["left_count"] == sum(x[0] for x in counts)


@pytest.mark.parametrize("counts", [[(0, 1), (0, 0), (0, 0), (0, 0)],
                                  [(0, 20), (0, 0), (0, 0), (0, 0)],
                                  [(0, 6), (0, 6), (0, 7), (0, 0)]])
def test_price_abstains_without_total_and_three_active_samples(module, counts):
    _, stream = make(module)
    stream.leaf()
    stream.neutral()
    result = stream.block(counts)
    assert result["status"] == "deferred"
    assert result["proposal"] is None
    assert result["phase"] == "price"


@pytest.mark.parametrize("kind", ["model", "wall"])
def test_path_expires_at_exact_original_clock_boundary(module, kind):
    _, stream = make(module)
    stream.direction("1")
    stream.direction("0")  # must not refresh first anchor10000/1000
    while (stream.tick + 5000 < 610000 if kind == "model" else stream.wall + 500 < 301000):
        if kind == "wall":
            stream.send(5, 5, wall_completion_ms=stream.wall + 10000)
            if stream.wall + 10000 >= 301000:
                break
        else:
            stream.send(5, 5)
    if kind == "wall":
        result = stream.send(5, 5, wall_completion_ms=301000)
    else:
        result = stream.send(5, 5)
    assert result["reason"] == "path_expired"
    assert result["interval"] == [0, 20]
    assert result["proposal"] is None


def test_first_supported_block_with_old_recorded_start_is_rejected(module):
    _, stream = make(module)
    stream.neutral()
    stream.send(0, 5, wall_completion_ms=301000)
    stream.send(0, 5)
    stream.send(0, 5)
    result = stream.send(0, 5)
    assert result["reason"] == "path_expired"
    assert result["interval"] == [0, 20]


@pytest.mark.parametrize("field,value", [
    ("left_count", True), ("right_count", -1), ("left_count", 1.5),
    ("right_count", 2**53), ("start_tick", False), ("end_tick", 4999),
    ("wall_completion_ms", float("inf")), ("wall_start_ms", -1),
    ("wall_start_ms", 501), ("wall_completion_ms", 501),
    ("source_sha256", "x" * 64), ("frame_sha256", "a" * 63),
    ("session_id", "bad\nidentity"), ("input_version", "x" * 129),
    ("observation_index", True),
])
def test_malformed_samples_raise_and_clear_pending_evidence(module, field, value):
    _, stream = make(module)
    sample = stream.sample()
    sample[field] = value
    with pytest.raises(ValueError):
        stream.decoder.consume(sample, now_ms=500)
    assert stream.direction("0")["interval"] == [0, 10]


def test_freshness_exact_limit_current_clock_and_order_watermarks(module):
    decoder, stream = make(module)
    value = stream.sample()
    assert decoder.consume(value, now_ms=5500)["reason"] == "waiting_for_neutral"
    later = stream.sample()
    assert decoder.consume(later, now_ms=6001)["reason"] == "stale_sample"
    assert decoder.consume(value, now_ms=6001)["reason"] == "stale_sample"
    with pytest.raises(ValueError, match="now_ms"):
        decoder.consume(stream.sample(), now_ms=6000)
    # Stale sample did not replace last established index0.
    fresh = stream.sample(observation_index=1, start_tick=5000, end_tick=10000,
                          wall_start_ms=5500, wall_completion_ms=6001)
    assert decoder.consume(fresh, now_ms=6001)["reason"] == "waiting_for_neutral"


@pytest.mark.parametrize("change", ["duplicate", "rewind", "model_overlap", "compute_overlap", "gap"])
def test_order_resets_drop_packet_and_require_new_neutral(module, change):
    decoder, stream = make(module)
    stream.direction("1")
    old = stream.sample(0, 0)
    decoder.consume(old, now_ms=stream.wall)
    if change == "duplicate":
        result = decoder.consume(old, now_ms=stream.wall)
    else:
        changes = {"rewind": {"observation_index": 1},
                   "model_overlap": {"start_tick": old["start_tick"], "end_tick": old["end_tick"]},
                   "compute_overlap": {"wall_start_ms": old["wall_start_ms"]},
                   "gap": {"observation_index": stream.index + 2}}[change]
        packet = stream.sample(**changes)
        result = decoder.consume(packet, now_ms=stream.wall)
    assert result["status"] == "reset"
    assert result["interval"] == [0, 20]
    assert result["proposal"] is None


def test_forward_gap_is_dropped_but_establishes_next_continuity(module):
    decoder, stream = make(module)
    stream.direction("1")
    assert stream.send(observation_index=100, start_tick=100000, end_tick=105000)["reason"] == "sample_gap"
    assert stream.send()["reason"] == "waiting_for_neutral"
    assert stream.send()["reason"] == "neutral_ready"
    assert stream.block([(5, 0)] * 4)["interval"] == [0, 10]


def test_new_session_boundary_is_dropped_and_old_transition_cannot_replace_it(module):
    decoder, stream = make(module)
    stream.direction("1")
    stream.session = "new-session"
    assert stream.send(start_tick=0, end_tick=5000, observation_index=0)["reason"] == "source_session_changed"
    old = stream.sample(session_id="synthetic-session", wall_start_ms=0)
    assert decoder.consume(old, now_ms=stream.wall)["reason"] == "old_transition"
    # Invalid old packet did not lower or replace the adopted new-session watermark.
    stream.index, stream.tick = 1, 5000
    assert stream.send()["reason"] == "waiting_for_neutral"
    assert stream.send()["reason"] == "neutral_ready"
    assert stream.block([(5, 0)] * 4)["interval"] == [0, 10]


@pytest.mark.parametrize("action", ["reset", "pause", "reconfigure"])
def test_explicit_boundaries_drop_queued_samples_and_preserve_order(module, action):
    decoder, stream = make(module)
    stream.direction("1")
    old = stream.sample()
    now = stream.wall + 1000
    if action == "pause":
        decoder.pause(now_ms=now)
        assert decoder.consume(stream.sample(), now_ms=now)["reason"] == "paused"
        decoder.resume(now_ms=now)
    elif action == "reconfigure":
        decoder.reconfigure(drinks(10), max_sample_age_ms=5000, now_ms=now)
    else:
        decoder.reset(now_ms=now)
    assert decoder.consume(old, now_ms=now)["reason"] == "before_boundary"
    stream.wall = now
    # Pending old sample indexes form a gap; drop boundary then rearm.
    stream.send()
    stream.neutral()
    result = stream.block([(5, 0)] * 4)
    assert result["interval"] == ([0, 5] if action == "reconfigure" else [0, 10])


def test_configuration_and_results_are_detached_and_digest_binds_policy(module):
    config = drinks()
    decoder, stream = make(module, config)
    digest = decoder.configuration_sha256
    config[0]["maximum_rappen"] = 999
    exposed = decoder.configuration
    exposed["drinks"][0]["id"] = "mutated"
    assert decoder.configuration_sha256 == digest
    canonical = json.dumps(decoder.configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert sha256(canonical.encode()).hexdigest() == digest
    assert decoder.configuration["max_sample_age_ms"] == 5000
    assert decoder.configuration["policy_version"] == decoder.policy_version
    stream.leaf()
    stream.neutral()
    proposal = stream.block([(0, 5)] * 4)["proposal"]
    assert proposal["input_history"][0]["observation_index"] == 2
    assert len(proposal["input_history"]) == 28
    assert [x["input_version"] for x in proposal["input_history"]] == [f"frame-{i}" for i in range(2, 30)]
    saved = deepcopy(proposal)
    proposal["input_history"].clear()
    stream.leaf()
    stream.neutral()
    second = stream.block([(0, 5)] * 4)["proposal"]
    assert second["drink_id"] == "drink-0"
    assert len(second["input_history"]) == len(saved["input_history"])
    changed, _ = make(module, max_sample_age_ms=5001)
    assert changed.configuration_sha256 != digest
    restarted, fresh = make(module)
    assert fresh.block([(0, 10)] * 4)["interval"] == [0, 20]


@pytest.mark.parametrize("mutation", ["short", "long", "duplicate", "id", "minimum", "span", "grid", "boolean", "overflow"])
def test_invalid_drink_configurations_are_rejected(module, mutation):
    config = drinks()
    if mutation == "short":
        config = config[:9]
    elif mutation == "long":
        config = drinks(21)
    elif mutation == "duplicate":
        config[1]["id"] = config[0]["id"]
    else:
        field, value = {"id": ("id", "bad\nname"), "minimum": ("minimum_rappen", 701),
                        "span": ("maximum_rappen", 701), "grid": ("grid_rappen", 0),
                        "boolean": ("minimum_rappen", False), "overflow": ("maximum_rappen", 2**53)}[mutation]
        config[0][field] = value
    with pytest.raises(ValueError):
        make(module, config)


@pytest.mark.parametrize("age", [0, -1, True, 300001, 1.5, float("nan")])
def test_invalid_freshness_is_rejected(module, age):
    with pytest.raises(ValueError):
        make(module, max_sample_age_ms=age)


def test_freshness_configuration_has_no_default(module):
    with pytest.raises(TypeError):
        module.MotorReadout(drinks())


def test_long_silence_has_bounded_storage_and_path_does_not_sustain_forever(module):
    decoder, stream = make(module)
    for _ in range(2000):
        assert stream.send()["proposal"] is None
    assert len(decoder._block) <= 4
    assert len(decoder._neutral) <= 2
    assert len(decoder._history) == 0
    stream.direction("1")
    results = [stream.send() for _ in range(130)]
    assert any(result["reason"] == "path_expired" for result in results)
    assert all(result["proposal"] is None for result in results)
    assert len(decoder._history) <= 128


def test_policy_thresholds_cannot_mutate_under_existing_configuration_digest(module):
    decoder, stream = make(module)
    with pytest.raises(TypeError):
        module.POLICY["direction_total_min"] = 1
    stream.neutral()
    assert stream.block([(0, 1)] * 4)["status"] == "deferred"
    assert decoder.configuration["policy"]["direction_total_min"] == 20


def test_proposal_records_actual_measurement_completion_and_separate_emission(module):
    _, stream = make(module)
    stream.leaf()
    stream.neutral()
    for _ in range(3):
        stream.send(0, 5)
    result = stream.send(0, 5, now_ms=stream.wall + 1000)
    proposal = result["proposal"]
    assert proposal["completion_wall_ms"] == stream.wall
    assert proposal["emitted_wall_ms"] == stream.wall + 500
    assert proposal["price_measurement"]["wall_completion_ms"] == stream.wall


def test_wall_expiry_uses_current_delivery_time_instead_of_measurement_completion(module):
    decoder, stream = make(module)
    stream.direction("1")
    # A slow but fresh observation ends just below expiry, delivery reaches it.
    packet = stream.sample(wall_completion_ms=300999)
    result = decoder.consume(packet, now_ms=301000)
    assert result["reason"] == "path_expired"
    assert result["interval"] == [0, 20]


def test_count_payload_overflow_fails_closed_but_price_intermediates_stay_exact(module):
    decoder, stream = make(module)
    stream.neutral()
    for _ in range(3):
        stream.send(0, 2**51)
    with pytest.raises(ValueError, match="JSON-safe"):
        stream.send(0, 2**51)
    stream.neutral()
    assert stream.block([(0, 5)] * 4)["interval"] == [10, 20]
    wide = drinks()
    for drink in wide:
        drink.update(minimum_rappen=0, maximum_rappen=2**53 - 1, grid_rappen=1)
    _, fresh = make(module, wide)
    fresh.leaf()
    fresh.neutral()
    # exact half of odd9007199254740991 =>4503599627370496, rounded upward
    assert fresh.block([(2**49, 2**49)] * 4)["proposal"]["target_rappen"] == 4503599627370496


@pytest.mark.parametrize("reset_kind", ["malformed", "duplicate", "explicit", "reconfigure", "proposal"])
def test_reset_never_allows_replaying_established_sample_watermarks(module, reset_kind):
    decoder, stream = make(module)
    stream.direction("1")
    previous = stream.sample()
    decoder.consume(previous, now_ms=stream.wall)
    if reset_kind == "malformed":
        with pytest.raises(ValueError):
            decoder.consume({**previous, "left_count": False}, now_ms=stream.wall)
    elif reset_kind == "duplicate":
        decoder.consume(previous, now_ms=stream.wall)
    elif reset_kind == "explicit":
        decoder.reset(now_ms=stream.wall)
    elif reset_kind == "reconfigure":
        decoder.reconfigure(drinks(), max_sample_age_ms=5000, now_ms=stream.wall)
    else:
        # First direction already1; finish fixed route1000 and price.
        for bit in "000":
            stream.direction(bit)
        stream.neutral()
        assert stream.block([(0, 5)] * 4)["proposal"] is not None
    # Previously established sample completes at the explicit boundary (not before).
    result = decoder.consume(previous, now_ms=stream.wall)
    assert result["reason"] in {"sample_out_of_order", "stale_sample"}
    assert result["interval"] == [0, 20]


def test_source_transition_uses_start_and_strict_completion_bounds(module):
    decoder, stream = make(module)
    stream.send()
    last_wall = stream.wall
    overlapping = stream.sample(source_sha256="b" * 64, wall_start_ms=last_wall - 1)
    assert decoder.consume(overlapping, now_ms=stream.wall)["reason"] == "old_transition"
    equal = {**overlapping, "wall_start_ms": last_wall, "wall_completion_ms": last_wall}
    assert decoder.consume(equal, now_ms=stream.wall)["reason"] == "old_transition"
    stream.source = "b" * 64
    assert stream.send(observation_index=0, start_tick=0, end_tick=5000)["reason"] == "source_session_changed"
    stream.neutral()
    assert stream.block([(0, 5)] * 4)["interval"] == [10, 20]


def test_source_samples_and_intermediate_results_do_not_alias_internal_state(module):
    decoder, stream = make(module)
    stream.neutral()
    first = stream.sample(5, 0)
    decoder.consume(first, now_ms=stream.wall)
    first["input_version"] = "corrupted"
    for _ in range(3):
        result = stream.send(5, 0)
    result["interval"][1] = 999
    for bit in "000":
        stream.direction(bit)
    stream.neutral()
    proposal = stream.block([(5, 0)] * 4)["proposal"]
    assert proposal["drink_id"] == "drink-0"
    assert proposal["input_history"][0]["input_version"] == "frame-2"


def test_fixed_price_grid_and_ten_drink_configuration_remain_valid(module):
    config = drinks(10)
    config[0].update(minimum_rappen=650, maximum_rappen=650, grid_rappen=50)
    _, stream = make(module, config, max_sample_age_ms=300000)
    stream.leaf("000")
    stream.neutral()
    assert stream.block([(0, 5)] * 4)["proposal"]["target_rappen"] == 650
