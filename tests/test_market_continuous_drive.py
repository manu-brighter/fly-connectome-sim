"""Synthetic continuous-drive contracts; no measured or neural reachability claim."""

from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path

import pytest

from test_market_motor_readout import drinks


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/market_continuous_drive.py"


def test_first_observation_starts_direction_without_neutral(monkeypatch):
    assert SCRIPT.is_file(), "The continuous motor drive implementation is missing"
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    candidate = importlib.import_module("market_continuous_drive")
    _, stream = make(candidate)
    assert stream.send(0, 5) == {
        "status": "collecting", "reason": "incomplete_block", "phase": "direction",
        "interval": [0, 20], "proposal": None,
    }


@pytest.fixture
def module(monkeypatch):
    assert SCRIPT.is_file(), "The continuous motor drive implementation is missing"
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    return importlib.import_module("market_continuous_drive")


class ContinuousStream:
    def __init__(self, decoder):
        self.decoder = decoder
        self.index, self.tick, self.wall = 0, 0, 0
        self.source, self.session = "a" * 64, "synthetic-session"
        self.samples, self.results = [], []

    def sample(self, left=0, right=0, **changes):
        value = {
            "source_sha256": self.source, "session_id": self.session,
            "observation_index": self.index, "start_tick": self.tick, "end_tick": self.tick + 5000,
            "left_count": left, "right_count": right, "input_version": f"frame-{self.index}",
            "frame_sha256": sha256(str(self.index).encode()).hexdigest(),
            "wall_start_ms": self.wall, "wall_completion_ms": self.wall + 500,
        }
        value.update(changes)
        self.index = value["observation_index"] + 1
        self.tick, self.wall = value["end_tick"], value["wall_completion_ms"]
        return value

    def send(self, left=0, right=0, *, now_ms=None, **changes):
        value = self.sample(left, right, **changes)
        self.samples.append(deepcopy(value))
        result = self.decoder.consume(value, now_ms=self.wall if now_ms is None else now_ms)
        self.results.append(result)
        return result

    def block(self, counts):
        results = [self.send(left, right) for left, right in counts]
        assert [item["reason"] for item in results[:-1]] == ["incomplete_block"] * (len(counts) - 1)
        return results[-1]

    def direction(self, bit):
        return self.block([(0, 5) if bit == "1" else (5, 0)] * 4)

    def leaf(self, route="0000"):
        for bit in route:
            assert self.direction(bit)["reason"] == "direction_supported"
        assert self.results[-1]["phase"] == "price"


def make(module, config=None, *, max_sample_age_ms=5000):
    decoder = module.ContinuousMotorDrive(drinks() if config is None else config,
                                          max_sample_age_ms=max_sample_age_ms)
    return decoder, ContinuousStream(decoder)


def leaf_routes(count):
    # Construct the ordered tree independently of the decoder and its private state.
    def visit(ids, prefix):
        if len(ids) == 1:
            return [(ids[0], prefix)]
        cut = len(ids) // 2
        return visit(ids[:cut], prefix + "0") + visit(ids[cut:], prefix + "1")
    return visit(list(range(count)), "")


REACHABLE = [(count, index, route, endpoint)
             for count in range(10, 21) for index, route in leaf_routes(count)
             for endpoint in (400, 700)]


@pytest.mark.parametrize("count,index,route,endpoint", REACHABLE)
def test_every_leaf_all_sizes_both_endpoints_has_exact_disjoint_fresh_support(module, count, index, route, endpoint):
    decoder, stream = make(module, drinks(count))
    stream.leaf(route)
    assert all(item["proposal"] is None for item in stream.results)
    result = stream.block([(5, 0) if endpoint == 400 else (0, 5)] * 4)
    proposal = result["proposal"]
    assert result["status"] == "proposal"
    assert result["interval"] == [0, count]
    assert result["phase"] == "direction"
    assert proposal["drink_id"] == f"drink-{index}"
    assert proposal["target_rappen"] == endpoint
    assert proposal["policy_version"] == "continuous-motor-drive/v1"
    assert proposal["configuration_sha256"] == decoder.configuration_sha256
    assert proposal["source_sha256"] == "a" * 64
    assert proposal["session_id"] == "synthetic-session"
    assert proposal["path_start_tick"] == proposal["path_start_wall_ms"] == 0
    assert proposal["completion_tick"] == 5000 * 4 * (len(route) + 1)
    assert proposal["completion_wall_ms"] == proposal["emitted_wall_ms"] == 500 * 4 * (len(route) + 1)
    assert proposal["input_history"] == stream.samples
    measurements = proposal["decisions"] + [proposal["price_measurement"]]
    for block_index, measurement in enumerate(measurements):
        start = block_index * 4
        assert measurement == {
            **({"direction": "upper" if route[block_index] == "1" else "lower"}
               if block_index < len(route) else {}),
            "first_observation_index": start, "last_observation_index": start + 3,
            "start_tick": start * 5000, "end_tick": (start + 4) * 5000,
            "wall_start_ms": start * 500, "wall_completion_ms": (start + 4) * 500,
            "left_count": sum(s["left_count"] for s in stream.samples[start:start + 4]),
            "right_count": sum(s["right_count"] for s in stream.samples[start:start + 4]),
            "total_count": 20,
        }
    assert not {"neutral_ready", "waiting_for_neutral"} & {item["reason"] for item in stream.results}
    assert stream.send(5, 0)["reason"] == "incomplete_block"


@pytest.mark.parametrize("pair,target,endpoint", [((5, 0), "drink-0", 400), ((0, 5), "drink-19", 700)])
def test_fresh_constant_drive_repeats_favorite_without_reusing_samples(module, pair, target, endpoint):
    _, stream = make(module)
    proposals = []
    for _ in range(72):
        result = stream.send(*pair)
        if result["proposal"]:
            proposals.append(result["proposal"])
    assert len(proposals) == 3
    seen = set()
    for proposal in proposals:
        assert (proposal["drink_id"], proposal["target_rappen"]) == (target, endpoint)
        indices = [item["observation_index"] for item in proposal["input_history"]]
        assert not seen.intersection(indices)
        seen.update(indices)
        assert indices == list(range(indices[0], indices[-1] + 1))
    assert seen == set(range(20 * len(proposals) if endpoint == 400 else 24 * len(proposals)))


@pytest.mark.parametrize("counts,accepted", [
    ([(2, 3)] * 4, True),
    ([(1, 3)] * 3 + [(4, 4)], True),
    ([(2, 3)] * 3 + [(1, 3)], False),
    ([(2, 3)] * 3 + [(3, 3)], False),
    ([(2, 3)] * 3 + [(3, 4)], False),
    ([(0, 6), (0, 6), (6, 0), (0, 0)], False),
    ([(0, 0)] * 4, False), ([(5, 5)] * 4, False),
    ([(0, 10), (10, 0)] * 2, False),
])
def test_direction_gates_apply_to_ready_consecutive_blocks(module, counts, accepted):
    _, stream = make(module)
    result = stream.block(counts)
    assert result["reason"] == ("direction_supported" if accepted else "unsupported_direction")
    assert result["interval"] == ([10, 20] if accepted else [0, 20])


def test_failed_direction_blocks_discard_without_sliding_and_history_keeps_after_anchor(module):
    _, stream = make(module)
    assert stream.block([(0, 5), (0, 5), (5, 0), (5, 0)])["reason"] == "unsupported_direction"
    assert stream.direction("0")["interval"] == [0, 10]
    assert stream.block([(5, 5)] * 4)["reason"] == "unsupported_direction"
    assert stream.direction("0")["interval"] == [0, 5]
    stream.leaf("00")
    proposal = stream.block([(5, 0)] * 4)["proposal"]
    assert proposal["input_history"] == stream.samples[4:]
    assert [item["first_observation_index"] for item in proposal["decisions"]] == [4, 12, 16, 20]
    assert proposal["price_measurement"]["first_observation_index"] == 24
    assert proposal["path_start_tick"] == 20000


@pytest.mark.parametrize("counts,target", [
    ([(5, 0)] * 4, 400), ([(0, 5)] * 4, 700),
    ([(5, 1)] * 4, 450), ([(11, 1)] * 4, 450), ([(12, 1)] * 4, 400),
    ([(5, 5)] * 4, 550),
])
def test_price_is_separate_and_keeps_exact_grid_arithmetic(module, counts, target):
    _, stream = make(module)
    stream.leaf()
    assert stream.results[-1]["proposal"] is None
    proposal = stream.block(counts)["proposal"]
    assert proposal["target_rappen"] == target
    assert proposal["price_measurement"]["first_observation_index"] == 16


@pytest.mark.parametrize("counts", [
    [(0, 1), (0, 0), (0, 0), (0, 0)],
    [(0, 20), (0, 0), (0, 0), (0, 0)],
    [(0, 6), (0, 6), (0, 7), (0, 0)],
])
def test_unsupported_price_discards_block_without_reusing_or_losing_path(module, counts):
    _, stream = make(module)
    stream.leaf()
    assert stream.block(counts)["reason"] == "unsupported_price"
    proposal = stream.block([(0, 5)] * 4)["proposal"]
    assert proposal["price_measurement"]["first_observation_index"] == 20
    assert proposal["input_history"] == stream.samples


@pytest.mark.parametrize("pair", [(0, 0), (5, 5), (1, 0)])
def test_wall_time_silence_ambiguity_and_weak_activity_cannot_force_commands(module, pair):
    _, stream = make(module)
    for _ in range(140):
        result = stream.send(*pair, wall_completion_ms=stream.wall + 10000)
        assert result["proposal"] is None
        assert result["interval"] == [0, 20]


@pytest.mark.parametrize("kind", ["model", "wall", "delivery"])
def test_exact_expiry_is_anchored_to_first_block_and_discards_trigger(module, kind):
    decoder, stream = make(module)
    stream.direction("1")
    stream.direction("0")
    if kind == "model":
        while stream.tick < 590000:
            stream.send(5, 5)
        assert stream.send(5, 5)["reason"] != "path_expired"
        trigger = stream.send(0, 5)
    else:
        trigger = stream.send(0, 5, wall_completion_ms=299999 if kind == "delivery" else 300000,
                              now_ms=300000)
    assert trigger["reason"] == "path_expired"
    assert trigger["interval"] == [0, 20]
    assert stream.send(0, 5)["reason"] == "incomplete_block"
    assert stream.send(0, 5)["reason"] == "incomplete_block"
    assert stream.send(0, 5)["reason"] == "incomplete_block"
    assert stream.send(0, 5)["reason"] == "direction_supported"
    assert decoder._decisions[0]["first_observation_index"] == stream.index - 4


def test_first_slow_supported_block_expires_without_starting_new_evidence(module):
    decoder, stream = make(module)
    stream.send(0, 5, wall_completion_ms=298500)
    for _ in range(2):
        stream.send(0, 5)
    assert stream.send(0, 5)["reason"] == "path_expired"
    assert decoder._block == []
    assert stream.direction("0")["interval"] == [0, 10]


def test_history_guard_discards_trigger_and_preserves_ordering(module):
    decoder, stream = make(module)
    stream.direction("1")
    # 128 history samples normally meet the earlier 60s guard first. Seed only
    # this otherwise masked defensive branch, without changing frozen globals.
    decoder._history = [deepcopy(stream.samples[0])] * 128
    trigger = stream.sample(0, 5)
    assert decoder.consume(trigger, now_ms=stream.wall)["reason"] == "history_limit"
    assert decoder.consume(trigger, now_ms=stream.wall)["reason"] == "sample_out_of_order"
    assert stream.direction("0")["interval"] == [0, 10]


@pytest.mark.parametrize("field,value", [
    ("left_count", True), ("right_count", -1), ("left_count", 1.5),
    ("right_count", 2**53), ("start_tick", False), ("end_tick", 1),
    ("wall_completion_ms", float("inf")), ("wall_start_ms", -1),
    ("wall_start_ms", 999999), ("wall_completion_ms", 999999), ("source_sha256", "x" * 64),
    ("frame_sha256", "a" * 63), ("session_id", "bad\nidentity"),
    ("input_version", "x" * 129), ("observation_index", True),
])
def test_invalid_samples_clear_path_and_do_not_start_next_block(module, field, value):
    decoder, stream = make(module)
    stream.direction("1")
    packet = stream.sample(0, 5)
    packet[field] = value
    with pytest.raises(ValueError):
        decoder.consume(packet, now_ms=stream.wall)
    # Invalid measurements do not establish an order watermark; continue from4.
    stream.index, stream.tick = 4, 20000
    assert stream.direction("0")["interval"] == [0, 10]
    assert decoder._decisions[0]["first_observation_index"] == 4


@pytest.mark.parametrize("packet", [None, [], {}, {"extra": 1}])
def test_missing_or_extra_measurement_fields_fail_closed(module, packet):
    decoder, stream = make(module)
    stream.direction("1")
    with pytest.raises(ValueError):
        decoder.consume(packet, now_ms=stream.wall)
    assert stream.direction("0")["interval"] == [0, 10]


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_valid_measurement_cannot_omit_or_add_fields(module, change):
    decoder, stream = make(module)
    stream.direction("1")
    packet = stream.sample(0, 5)
    if change == "missing":
        del packet["input_version"]
    else:
        packet["extra"] = 1
    with pytest.raises(ValueError):
        decoder.consume(packet, now_ms=stream.wall)
    stream.index, stream.tick = 4, 20000
    assert stream.direction("0")["interval"] == [0, 10]


def test_freshness_boundary_stale_discard_and_wall_watermark_survive_reset(module):
    decoder, stream = make(module)
    first = stream.sample(0, 5)
    assert decoder.consume(first, now_ms=5500)["reason"] == "incomplete_block"
    packet = stream.sample(0, 5)
    assert decoder.consume(packet, now_ms=6001)["reason"] == "stale_sample"
    with pytest.raises(ValueError, match="now_ms"):
        decoder.consume(first, now_ms=6000)
    # Stale/invalid input has not replaced accepted index0.
    assert stream.send(0, 5, observation_index=1, start_tick=5000, end_tick=10000,
                       wall_start_ms=5500, wall_completion_ms=6001)["reason"] == "incomplete_block"
    assert decoder._block[0]["observation_index"] == 1


@pytest.mark.parametrize("change,reason", [
    ({"observation_index": 1}, "sample_out_of_order"),
    ({"start_tick": 15000, "end_tick": 20000}, "sample_out_of_order"),
    ({"wall_start_ms": 1499}, "sample_out_of_order"),
    ({"observation_index": 100}, "sample_gap"),
])
def test_order_violations_drop_trigger_and_never_carry_path(module, change, reason):
    decoder, stream = make(module)
    stream.direction("1")
    assert stream.send(0, 5, **change)["reason"] == reason
    assert decoder._block == decoder._decisions == []
    if reason != "sample_gap":
        stream.index, stream.tick = 4, 20000
    assert stream.direction("0")["interval"] == [0, 10]


def test_duplicate_cannot_become_fresh_command_after_reset_or_proposal(module):
    decoder, stream = make(module)
    stream.leaf()
    proposal = stream.block([(5, 0)] * 4)["proposal"]
    previous = proposal["input_history"][-1]
    assert decoder.consume(previous, now_ms=stream.wall)["reason"] == "sample_out_of_order"
    decoder.reset(now_ms=stream.wall)
    assert decoder.consume(previous, now_ms=stream.wall)["reason"] == "sample_out_of_order"
    assert stream.direction("1")["interval"] == [10, 20]


@pytest.mark.parametrize("field,value", [("source_sha256", "b" * 64), ("session_id", "new-session")])
def test_source_session_transition_discards_trigger_and_retains_new_watermark(module, field, value):
    decoder, stream = make(module)
    stream.direction("1")
    changes = {field: value, "observation_index": 0, "start_tick": 0, "end_tick": 5000}
    assert stream.send(0, 5, **changes)["reason"] == "source_session_changed"
    old = stream.sample(0, 5, wall_start_ms=0)
    assert decoder.consume(old, now_ms=stream.wall)["reason"] == "old_transition"
    if field == "source_sha256":
        stream.source = value
    else:
        stream.session = value
    stream.index, stream.tick = 1, 5000
    assert stream.direction("0")["interval"] == [0, 10]
    assert decoder._decisions[0]["first_observation_index"] == 1


@pytest.mark.parametrize("action", ["reset", "pause", "reconfigure"])
def test_explicit_boundaries_discard_queued_data_and_resume_ready(module, action):
    decoder, stream = make(module)
    stream.direction("1")
    queued = stream.sample(0, 5)
    now = stream.wall + 1000
    if action == "pause":
        decoder.pause(now_ms=now)
        assert decoder.consume(queued, now_ms=now)["reason"] == "paused"
        decoder.resume(now_ms=now)
    elif action == "reconfigure":
        decoder.reconfigure(drinks(10), max_sample_age_ms=5000, now_ms=now)
    else:
        decoder.reset(now_ms=now)
    assert decoder.consume(queued, now_ms=now)["reason"] == "before_boundary"
    stream.index, stream.tick, stream.wall = 4, 20000, now
    assert stream.direction("0")["interval"] == ([0, 5] if action == "reconfigure" else [0, 10])
    assert decoder._decisions[0]["first_observation_index"] == 4


def test_boundary_equality_is_accepted_but_original_order_still_applies(module):
    decoder, stream = make(module)
    decoder.reset(now_ms=500)
    assert stream.send(0, 5, now_ms=500)["reason"] == "incomplete_block"
    assert decoder.consume(stream.samples[0], now_ms=500)["reason"] == "sample_out_of_order"


def test_reconfigure_while_paused_cannot_accept_until_resume(module):
    decoder, stream = make(module)
    stream.direction("1")
    decoder.pause(now_ms=stream.wall)
    decoder.reconfigure(drinks(10), max_sample_age_ms=5000, now_ms=stream.wall)
    for _ in range(4):
        assert stream.send(0, 5)["reason"] == "paused"
    decoder.resume(now_ms=stream.wall)
    # Paused samples do not update the ordering watermark. The next gap resets
    # and is discarded; the four following samples form the first new block.
    assert stream.send(0, 5)["reason"] == "sample_gap"
    assert stream.direction("0")["interval"] == [0, 5]


def test_own_identity_is_canonical_detached_and_successful_reconfigure_rebinds(module):
    config = drinks()
    decoder, stream = make(module, config)
    frozen = decoder.configuration
    base = importlib.import_module("market_motor_readout")
    expected_policy = dict(base.POLICY)
    del expected_policy["neutral_samples"], expected_policy["neutral_total_max"]
    expected_policy["command_mode"] = "continuous-supported-drive"
    assert frozen == {"policy_version": "continuous-motor-drive/v1", "policy": expected_policy,
                      "drinks": drinks(), "max_sample_age_ms": 5000}
    assert not any("balanced" in name for name in frozen["policy"])
    canonical = json.dumps(frozen, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = sha256(canonical.encode()).hexdigest()
    assert decoder.configuration_sha256 == digest
    assert digest != base.MotorReadout(drinks(), max_sample_age_ms=5000).configuration_sha256
    config[0]["maximum_rappen"] = 999
    frozen["policy"]["command_mode"] = "corrupted"
    frozen["drinks"][0]["id"] = "corrupted"
    assert decoder.configuration_sha256 == digest
    assert "neutral_samples" in base.POLICY and "command_mode" not in base.POLICY
    stream.direction("1")
    replacement = drinks(10)
    assert decoder.reconfigure(replacement, max_sample_age_ms=1000, now_ms=stream.wall)["reason"] == "reconfigured"
    replacement[0]["id"] = "corrupted"
    stream.leaf("000")
    proposal = stream.block([(5, 0)] * 4)["proposal"]
    assert proposal["drink_id"] == "drink-0"
    assert proposal["policy_version"] == "continuous-motor-drive/v1"
    assert proposal["configuration_sha256"] == decoder.configuration_sha256 != digest
    assert decoder.configuration["policy"] == expected_policy


@pytest.mark.parametrize("bad_config,age", [(drinks(9), 5000), (drinks(), 0), (drinks(), True)])
def test_failed_reconfiguration_keeps_identity_but_clears_evidence_and_advances_wall(module, bad_config, age):
    decoder, stream = make(module)
    stream.direction("1")
    old_config, digest = decoder.configuration, decoder.configuration_sha256
    now = stream.wall + 1000
    with pytest.raises(ValueError):
        decoder.reconfigure(bad_config, max_sample_age_ms=age, now_ms=now)
    assert decoder.configuration == old_config
    assert decoder.configuration_sha256 == digest
    with pytest.raises(ValueError, match="now_ms"):
        decoder.reset(now_ms=now - 1)
    # A failed replacement keeps v1's old boundary; completion before the failed
    # config clock is still accepted if fresh and delivered at that clock.
    assert stream.send(5, 0, now_ms=now)["reason"] == "incomplete_block"
    stream.wall = now
    for _ in range(3):
        result = stream.send(5, 0)
    assert result["interval"] == [0, 10]
    assert decoder._decisions[0]["first_observation_index"] == 4


def test_input_frames_and_returned_results_do_not_alias_internal_evidence(module):
    decoder, stream = make(module)
    first = stream.sample(5, 0)
    original = deepcopy(first)
    decoder.consume(first, now_ms=stream.wall)
    first["input_version"] = "mutated"
    for _ in range(3):
        result = stream.send(5, 0)
    result["interval"][1] = 999
    stream.leaf("000")
    proposal = stream.block([(5, 0)] * 4)["proposal"]
    assert proposal["drink_id"] == "drink-0"
    assert proposal["input_history"] == [original] + stream.samples
    proposal["input_history"][0]["frame_sha256"] = "f" * 64
    assert stream.direction("1")["interval"] == [10, 20]


def test_wide_price_intermediates_and_fixed_grid_remain_exact(module):
    wide = drinks()
    for drink in wide:
        drink.update(minimum_rappen=0, maximum_rappen=2**53 - 1, grid_rappen=1)
    _, stream = make(module, wide)
    stream.leaf()
    assert stream.block([(2**49, 2**49)] * 4)["proposal"]["target_rappen"] == 4503599627370496
    fixed = drinks(10)
    fixed[0].update(minimum_rappen=650, maximum_rappen=650)
    _, stream = make(module, fixed)
    stream.leaf("000")
    assert stream.block([(0, 5)] * 4)["proposal"]["target_rappen"] == 650


def test_aggregated_count_overflow_clears_and_rearms_without_reusing_trigger(module):
    decoder, stream = make(module)
    for _ in range(3):
        stream.send(0, 2**51)
    with pytest.raises(ValueError, match="JSON-safe"):
        stream.send(0, 2**51)
    assert stream.direction("0")["interval"] == [0, 10]
    assert decoder._decisions[0]["first_observation_index"] == 4


@pytest.mark.parametrize("mutation", [
    "short", "long", "duplicate", "id", "minimum", "span", "grid", "boolean", "overflow", "extra", "missing",
])
def test_subclass_constructor_keeps_base_configuration_validation(module, mutation):
    config = drinks()
    if mutation == "short":
        config = drinks(9)
    elif mutation == "long":
        config = drinks(21)
    elif mutation == "duplicate":
        config[1]["id"] = config[0]["id"]
    elif mutation == "extra":
        config[0]["extra"] = 1
    elif mutation == "missing":
        del config[0]["id"]
    else:
        field, value = {
            "id": ("id", "bad\nname"), "minimum": ("minimum_rappen", 701),
            "span": ("maximum_rappen", 701), "grid": ("grid_rappen", 0),
            "boolean": ("minimum_rappen", False), "overflow": ("maximum_rappen", 2**53),
        }[mutation]
        config[0][field] = value
    with pytest.raises(ValueError):
        make(module, config)


@pytest.mark.parametrize("age", [0, -1, True, 300001, 1.5, float("nan")])
def test_subclass_requires_valid_explicit_freshness(module, age):
    with pytest.raises(ValueError):
        make(module, max_sample_age_ms=age)
    with pytest.raises(TypeError):
        module.ContinuousMotorDrive(drinks())
