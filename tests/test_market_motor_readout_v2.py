"""Synthetic v2 release contracts; no native or historical reachability claim."""

from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path

import pytest

from test_market_motor_readout import ROUTES, Stream, drinks


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/market_motor_readout_v2.py"


@pytest.fixture
def module(monkeypatch):
    assert SCRIPT.is_file(), "The offline v2 candidate is missing"
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    return importlib.import_module("market_motor_readout_v2")


class BalancedStream(Stream):
    def rearm(self):
        return self.block([(3, 3)] * 4)

    def direction(self, bit):
        assert self.rearm()["reason"] == "balanced_ready"
        return self.block([(2, 4) if bit == "1" else (4, 2)] * 4)


def make(module, config=None, *, max_sample_age_ms=5000):
    decoder = module.MotorReadoutV2(drinks() if config is None else config,
                                   max_sample_age_ms=max_sample_age_ms)
    return decoder, BalancedStream(decoder)


@pytest.mark.parametrize("counts,reason", [
    ([(3, 3)] * 4, "balanced_ready"),
    ([(2, 2)] * 4, "waiting_for_neutral"),
    ([(2, 2), (5, 6), (2, 2), (0, 0)], "waiting_for_neutral"),  # total19, each in band
    ([(2, 2)] * 2 + [(3, 3)] * 2, "balanced_ready"),
    ([(9, 11)] * 4, "balanced_ready"),
    ([(11, 9)] * 4, "balanced_ready"),
    ([(8, 12)] * 4, "waiting_for_neutral"),
    ([(12, 8)] * 4, "waiting_for_neutral"),
    ([(0, 0), (5, 5), (0, 0), (5, 5)], "balanced_ready"),
    ([(5, 5), (5, 5), (0, 0), (0, 0)], "neutral_ready"),
    ([(10, 0), (0, 10), (10, 0), (0, 10)], "waiting_for_neutral"),
    ([(0, 10), (10, 0), (0, 10), (10, 0)], "waiting_for_neutral"),
])
def test_exact_total_band_zero_interleaving_and_quiet_precedence(module, counts, reason):
    _, stream = make(module)
    results = [stream.send(*pair) for pair in counts]
    assert all(item["reason"] == "waiting_for_neutral" for item in results[:3])
    assert results[-1]["reason"] == reason
    assert results[-1]["status"] == ("waiting" if reason == "waiting_for_neutral" else "ready")
    assert set(results[-1]) == {"status", "reason", "phase", "interval", "proposal"}


def test_original_quiet_pair_and_partial_balance_are_consumed_only_once(module):
    decoder, stream = make(module)
    stream.send(3, 3)
    assert stream.neutral()["reason"] == "neutral_ready"
    assert decoder._balanced == []
    assert stream.block([(4, 2)] * 3)["status"] == "collecting"
    result = stream.send(4, 2)
    assert result["interval"] == [0, 10]
    assert decoder._decisions[0]["first_observation_index"] == 3
    assert stream.block([(3, 3)] * 3)["reason"] == "waiting_for_neutral"
    assert stream.send(3, 3)["reason"] == "balanced_ready"


def test_rejected_blocks_do_not_slide_or_restart_on_imbalance(module):
    _, stream = make(module)
    assert stream.block([(10, 0)] + [(3, 3)] * 3)["reason"] == "waiting_for_neutral"
    assert stream.send(3, 3)["reason"] == "waiting_for_neutral"
    assert stream.block([(10, 0)] * 3)["reason"] == "waiting_for_neutral"
    assert stream.block([(3, 3)] * 3)["reason"] == "waiting_for_neutral"
    assert stream.send(3, 3)["reason"] == "balanced_ready"


def test_quiet_pair_can_span_failed_balance_boundary(module):
    decoder, stream = make(module)
    assert stream.block([(10, 0)] * 3 + [(0, 0)])["reason"] == "waiting_for_neutral"
    assert len(decoder._neutral) == 1
    assert stream.send(0, 0)["reason"] == "neutral_ready"
    assert decoder._balanced == []


@pytest.mark.parametrize("pair", [(10, 0), (0, 10)])
def test_sustained_one_sided_activity_never_releases_or_advances(module, pair):
    decoder, stream = make(module)
    for _ in range(100):
        result = stream.send(*pair)
        assert result["reason"] == "waiting_for_neutral"
        assert result["interval"] == [0, 20]
        assert len(decoder._balanced) < 4
        assert decoder._history == []


@pytest.mark.parametrize("index,route", list(enumerate(ROUTES)))
@pytest.mark.parametrize("price_pair,target", [((5, 0), 400), ((0, 5), 700)])
def test_twenty_literal_routes_price_extremes_and_disjoint_support(module, index, route, price_pair, target):
    decoder, stream = make(module)
    stream.leaf(route)
    assert stream.rearm()["reason"] == "balanced_ready"
    proposal = stream.block([price_pair] * 4)["proposal"]
    assert proposal["drink_id"] == f"drink-{index}"
    assert proposal["target_rappen"] == target
    assert proposal["policy_version"] == "sequential-motor-readout/v2"
    assert proposal["configuration_sha256"] == decoder.configuration_sha256
    assert proposal["path_start_tick"] == 20000
    assert proposal["path_start_wall_ms"] == 2000
    assert len(proposal["decisions"]) == len(route)
    for offset, decision in enumerate(proposal["decisions"]):
        assert decision["first_observation_index"] == 4 + 8 * offset
        assert decision["last_observation_index"] == 7 + 8 * offset
    assert proposal["price_measurement"]["first_observation_index"] == 4 + 8 * len(route)
    assert proposal["price_measurement"]["last_observation_index"] == 7 + 8 * len(route)
    history = proposal["input_history"]
    assert [item["observation_index"] for item in history] == list(range(4, 8 + 8 * len(route)))
    assert any(item["left_count"] == item["right_count"] == 3 for item in history)
    assert decoder._balanced == decoder._history == []
    assert stream.block([price_pair] * 4)["proposal"] is None


@pytest.mark.parametrize("pair,interval,direction", [((4, 2), [0, 10], "lower"), ((2, 4), [10, 20], "upper")])
def test_symmetric_rearm_and_unchanged_supported_direction(module, pair, interval, direction):
    decoder, stream = make(module)
    assert stream.rearm()["reason"] == "balanced_ready"
    assert stream.block([pair] * 4)["interval"] == interval
    assert decoder._decisions[0]["direction"] == direction
    assert decoder._decisions[0]["total_count"] == 24


def test_configuration_digest_detachment_and_base_identity_are_preserved(module):
    base = importlib.import_module("market_motor_readout")
    before_policy = dict(base.POLICY)
    original = base.MotorReadout(drinks(), max_sample_age_ms=5000)
    original_config = original.configuration
    original_digest = original.configuration_sha256
    config = drinks()
    decoder, stream = make(module, config)
    config[0]["id"] = "changed"
    declaration = decoder.configuration
    assert declaration["policy_version"] == "sequential-motor-readout/v2"
    expected_policy = {**before_policy, "balanced_rearm_samples": 4, "balanced_rearm_total_min": 20,
                       "balanced_rearm_fraction_numerator": 1, "balanced_rearm_fraction_denominator": 10}
    assert declaration["policy"] == expected_policy
    canonical = json.dumps(declaration, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert decoder.configuration_sha256 == sha256(canonical.encode()).hexdigest()
    assert decoder.configuration_sha256 != original_digest
    declaration["policy"]["balanced_rearm_total_min"] = 0
    declaration["drinks"][0]["id"] = "corrupt"
    assert decoder.configuration["policy"] == expected_policy
    assert decoder.configuration["drinks"][0]["id"] == "drink-0"
    stream.leaf()
    stream.rearm()
    result = stream.block([(5, 0)] * 4)
    result["proposal"]["input_history"][0]["left_count"] = -1
    result["interval"][1] = 999
    assert stream.send(3, 3)["interval"] == [0, 20]
    assert original.configuration == original_config
    assert original.configuration_sha256 == original_digest
    assert dict(base.POLICY) == before_policy


@pytest.mark.parametrize("kind", ["left", "right", "total", "imbalanced"])
def test_complete_block_overflow_validates_even_rejected_balance_and_clears(module, kind):
    decoder, stream = make(module)
    maximum = 2**53 - 1
    if kind == "left":
        pairs = [(maximum, 0)] * 4
    elif kind == "right":
        pairs = [(0, maximum)] * 4
    elif kind == "total":
        q = maximum // 8
        pairs = [(q, q)] * 3 + [(q + 4, q + 4)]
    else:
        pairs = [(maximum // 2, 0)] * 4
    stream.block(pairs[:3])
    with pytest.raises(ValueError, match="block .*JSON-safe"):
        stream.send(*pairs[3])
    assert decoder._balanced == decoder._neutral == decoder._history == []
    assert stream.block([(3, 3)] * 3)["reason"] == "waiting_for_neutral"
    assert stream.send(3, 3)["reason"] == "balanced_ready"


def test_exact_json_safe_aggregate_is_accepted_without_float_rounding(module):
    _, stream = make(module)
    q = (2**53 - 1) // 8
    assert stream.block([(q, q)] * 3 + [(q + 3, q + 4)])["reason"] == "balanced_ready"


@pytest.mark.parametrize("outside", [False, True])
def test_large_exact_band_boundary_uses_integer_cross_products(module, outside):
    _, stream = make(module)
    scale = (2**53 - 1) // 80
    pair = (9 * scale - int(outside), 11 * scale + int(outside))
    assert stream.block([pair] * 4)["reason"] == ("waiting_for_neutral" if outside else "balanced_ready")


@pytest.mark.parametrize("pair,target", [
    ((6, 0), 400), ((5, 1), 450), ((4, 2), 500), ((3, 3), 550),
    ((2, 4), 600), ((1, 5), 650), ((0, 6), 700),
])
def test_separate_price_support_reaches_entire_allowed_grid(module, pair, target):
    _, stream = make(module)
    stream.leaf()
    stream.rearm()
    assert stream.block([pair] * 4)["proposal"]["target_rappen"] == target


def test_supported_direction_cannot_repeat_without_release(module):
    _, stream = make(module)
    assert stream.direction("0")["interval"] == [0, 10]
    for _ in range(100):
        result = stream.send(10, 0)
        assert result["reason"] == "waiting_for_neutral"
        assert result["interval"] == [0, 10]


@pytest.mark.parametrize("field,value", [
    ("left_count", True), ("right_count", False), ("left_count", -1),
    ("right_count", 1.0), ("left_count", 2**53), ("observation_index", True),
    ("end_tick", 999), ("frame_sha256", "invalid"),
])
def test_invalid_sample_clears_partial_balance_and_preserves_order(module, field, value):
    decoder, stream = make(module)
    stream.block([(3, 3)] * 3)
    last = deepcopy(decoder._last)
    bad = stream.sample(3, 3)
    bad[field] = value
    with pytest.raises(ValueError):
        decoder.consume(bad, now_ms=stream.wall)
    assert decoder._last == last
    assert decoder._balanced == []
    # The invalid observation was never established; its successor is a gap.
    assert stream.send(3, 3)["reason"] == "sample_gap"
    assert stream.block([(3, 3)] * 3)["reason"] == "waiting_for_neutral"
    assert stream.send(3, 3)["reason"] == "balanced_ready"


@pytest.mark.parametrize("kind,reason", [
    ("stale", "stale_sample"), ("gap", "sample_gap"),
    ("overlap", "sample_out_of_order"), ("source", "source_session_changed"),
    ("session", "source_session_changed"), ("old_source", "old_transition"),
])
def test_base_dropped_samples_clear_balance_without_becoming_release_evidence(module, kind, reason):
    decoder, stream = make(module)
    stream.block([(3, 3)] * 3)
    previous = deepcopy(decoder._last)
    sample = stream.sample(3, 3)
    now = stream.wall
    if kind == "stale":
        now += 5001
    elif kind == "gap":
        sample["observation_index"] += 1
    elif kind == "overlap":
        sample["start_tick"] -= 1
        sample["end_tick"] -= 1
    elif kind == "source":
        sample["source_sha256"] = stream.source = "b" * 64
    elif kind == "session":
        sample["session_id"] = stream.session = "new-session"
    else:
        sample["source_sha256"] = "b" * 64
        sample["wall_start_ms"] -= 1
    assert decoder.consume(sample, now_ms=now)["reason"] == reason
    assert decoder._balanced == []
    if kind in {"stale", "overlap", "old_source"}:
        assert decoder._last == previous
    else:
        assert decoder._last["observation_index"] == sample["observation_index"]


def test_freshness_inclusive_boundary_still_allows_fourth_release_sample(module):
    _, stream = make(module)
    stream.block([(3, 3)] * 3)
    assert stream.send(3, 3, now_ms=7000)["reason"] == "balanced_ready"


def test_queued_before_boundary_and_replayed_sample_do_not_lower_watermarks(module):
    decoder, stream = make(module)
    stream.block([(3, 3)] * 3)
    previous = deepcopy(decoder._last)
    decoder.reset(now_ms=3000)
    queued = stream.sample(3, 3)
    assert decoder.consume(queued, now_ms=3000)["reason"] == "before_boundary"
    assert decoder._last == previous
    assert decoder._balanced == []
    stream.wall = 3000
    assert stream.send(3, 3)["reason"] == "sample_gap"
    accepted = stream.sample(3, 3)
    assert decoder.consume(accepted, now_ms=stream.wall)["reason"] == "waiting_for_neutral"
    last = deepcopy(decoder._last)
    assert decoder.consume(accepted, now_ms=stream.wall)["reason"] == "sample_out_of_order"
    assert decoder._last == last
    assert decoder._balanced == []
    assert stream.block([(3, 3)] * 3)["reason"] == "waiting_for_neutral"
    assert stream.send(3, 3)["reason"] == "balanced_ready"


@pytest.mark.parametrize("action", ["reset", "pause", "resume", "reconfigure", "failed_reconfigure", "rewind"])
def test_lifecycle_and_failed_reconfiguration_clear_balance_keep_v2_and_watermarks(module, action):
    decoder, stream = make(module)
    stream.block([(3, 3)] * 3)
    old_config = decoder.configuration
    old_digest = decoder.configuration_sha256
    old_boundary = decoder._boundary_ms
    previous = deepcopy(decoder._last)
    if action == "failed_reconfigure":
        with pytest.raises(ValueError):
            decoder.reconfigure([], max_sample_age_ms=5000, now_ms=stream.wall + 1)
        assert decoder.configuration == old_config
        assert decoder.configuration_sha256 == old_digest
        assert decoder._boundary_ms == old_boundary
        stream.wall += 1
    elif action == "rewind":
        with pytest.raises(ValueError, match="must not decrease"):
            decoder.reset(now_ms=stream.wall - 1)
    elif action == "reconfigure":
        replacement = drinks(10)
        assert decoder.reconfigure(replacement, max_sample_age_ms=6000, now_ms=stream.wall)["reason"] == "reconfigured"
        assert decoder.configuration["drinks"] == replacement
        assert decoder.configuration_sha256 != old_digest
    else:
        getattr(decoder, action)(now_ms=stream.wall)
        if action == "pause":
            assert stream.send(3, 3)["reason"] == "paused"
            assert decoder._balanced == []
            decoder.resume(now_ms=stream.wall)
    assert decoder._last == previous
    assert decoder.policy_version == "sequential-motor-readout/v2"
    assert decoder.configuration["policy"]["balanced_rearm_samples"] == 4
    assert decoder._balanced == []
    assert stream.block([(3, 3)] * 3)["reason"] in {"waiting_for_neutral", "sample_gap"}
    if action == "pause":
        # Paused input did not advance the order watermark; first resumed input drops as a gap.
        assert stream.send(3, 3)["reason"] == "waiting_for_neutral"
        assert stream.send(3, 3)["reason"] == "balanced_ready"
    else:
        assert stream.send(3, 3)["reason"] == "balanced_ready"


@pytest.mark.parametrize("kind", ["model", "wall"])
def test_original_expiry_wins_over_partial_balance_at_exact_boundary(module, kind):
    decoder, stream = make(module, max_sample_age_ms=300000)
    stream.direction("0")
    anchor = deepcopy(decoder._anchor)
    if kind == "model":
        while stream.tick + 5000 < anchor["start_tick"] + 600000:
            stream.send(10, 0)
        result = stream.send(3, 3)
        assert result["reason"] == "path_expired"
    else:
        stream.block([(3, 3)] * 3)
        result = stream.send(3, 3, now_ms=anchor["wall_start_ms"] + 300000)
        assert result["reason"] == "path_expired"
    assert decoder._anchor is None
    assert decoder._balanced == decoder._history == []
    assert not decoder._armed


def test_source_sample_mutation_cannot_change_partial_balance(module):
    decoder, stream = make(module)
    sample = stream.sample(3, 3)
    decoder.consume(sample, now_ms=stream.wall)
    sample["left_count"] = 999
    assert stream.block([(3, 3)] * 3)["reason"] == "balanced_ready"


def test_history_and_rearm_storage_remain_bounded_until_original_expiry(module):
    decoder, stream = make(module)
    stream.direction("0")
    reasons = []
    for _ in range(140):
        reasons.append(stream.send(3, 3)["reason"])
        assert len(decoder._history) <= 128
        assert len(decoder._balanced) < 4
    # Model expiry necessarily precedes the128-sample history limit for contiguous samples.
    assert reasons.count("path_expired") == 1
    assert decoder._history == []
