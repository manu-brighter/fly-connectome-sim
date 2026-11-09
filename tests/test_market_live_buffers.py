"""Synthetic bounded buffers/admission only; no engine, graph or runtime access."""

from copy import deepcopy
import importlib
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/market_live_buffers.py"
A, B, C = "a" * 64, "b" * 64, "c" * 64
MAX_INT = 2**63 - 1


def test_bounded_buffer_module_exists():
    assert SCRIPT.is_file(), "The bounded live buffer implementation is missing"


@pytest.fixture
def module(monkeypatch):
    assert SCRIPT.is_file(), "The bounded live buffer implementation is missing"
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    return importlib.import_module("market_live_buffers")


def row(index, **changes):
    value = {
        "observation_index": index // 50, "bin_index": index % 50,
        "start_tick": index * 100, "end_tick": (index + 1) * 100,
        "counts": [(index + cell) % 101 for cell in range(256)],
    }
    value.update(changes)
    return value


def fill(ring, start, stop):
    for index in range(start, stop):
        ring(row(index))


@pytest.mark.parametrize("total,expected", [
    (0, "d108ba5092955d173fa74e70616db16f9b0e698c875051d00b8eea8bee56e82a"),
    (1, "d5adadac8d2731c17751e54f49312cdcb7070b978de875320e9ee7d9009af402"),
    (50, "463d0b0ceaf321d91d2b61b17e8c9b2c04895ef4a7025d92037ff87535f6008e"),
    (1001, "06b991b5a631c6502bca7a146915590f01aa746e06c26d90deb131466fef2ebb"),
    (6000, "d727e669d3dcaddb82b5383789b3d5ba1c8346a2084d4c285380baaf3a73d4ae"),
])
def test_versioned_hash_matches_independent_struct_vectors(module, total, expected):
    # Literals generated before implementation using scalar struct.pack('<q')
    # for four complete chronological columns, then Python bytes for counts.
    ring = module.CellRing()
    fill(ring, 0, total)
    assert ring.ring_sha256() == expected


def test_6000_bins_wrap_fixed_arrays_and_latest_complete_export(module):
    ring = module.CellRing()
    owned = [ring._counts, ring._observation_index, ring._bin_index, ring._start_tick, ring._end_tick]
    assert [array.shape for array in owned] == [(1000, 256)] + [(1000,)] * 4
    assert [array.dtype.str for array in owned] == ["|u1"] + ["<i8"] * 4
    pointers = [array.ctypes.data for array in owned]
    for observation in range(120):
        fill(ring, observation * 50, (observation + 1) * 50)
        value = ring.export_observation(observation)
        assert value["counts"].shape == (50, 256)
        assert value["counts"].tolist() == [row(i)["counts"] for i in range(observation * 50, (observation + 1) * 50)]
        assert ring.owned_array_bytes == sum(array.nbytes for array in owned) == 288000
        assert pointers == [array.ctypes.data for array in (ring._counts, ring._observation_index, ring._bin_index, ring._start_tick, ring._end_tick)]
        total = (observation + 1) * 50
        assert ring.stats == {
            "total_bins": total, "valid_length": min(total, 1000),
            "write_position": total % 1000, "evictions": max(total - 1000, 0),
        }
    assert ring.stats == {"total_bins": 6000, "valid_length": 1000, "write_position": 0, "evictions": 5000}
    assert ring.sink_body_calls == 6000
    assert ring.sink_body_total_ns >= ring.sink_body_max_ns > 0


def test_export_is_detached_and_exact_safe_five_window_sum(module):
    ring = module.CellRing()
    for index in range(50):
        ring(row(index, counts=[100] * 256))
    result = ring.export_observation(0)
    assert result["observation_index"] == 0
    assert result["bin_index"].tolist() == list(range(50))
    assert result["observation_indices"].tolist() == [0] * 50
    assert result["start_tick"].tolist() == list(range(0, 5000, 100))
    assert result["end_tick"].tolist() == list(range(100, 5001, 100))
    assert result["window_start_tick"].tolist() == [0, 1000, 2000, 3000, 4000]
    assert result["window_end_tick"].tolist() == [1000, 2000, 3000, 4000, 5000]
    assert result["window_counts"].dtype == np.dtype("uint16")
    assert result["window_counts"].tolist() == [[1000] * 256] * 5
    saved = deepcopy(result)
    fill(ring, 50, 1100)
    for key, value in saved.items():
        np.testing.assert_equal(result[key], value)
    before = ring.ring_sha256()
    for value in result.values():
        if isinstance(value, np.ndarray):
            value.fill(0)
    assert ring.ring_sha256() == before


def test_window_arithmetic_preserves_cohort_order_and_nonoverlap(module):
    ring = module.CellRing()
    for index in range(50):
        ring(row(index, counts=[index] + [index % 2] * 255))
    value = ring.export_observation(0)
    assert value["window_counts"][:, 0].tolist() == [45, 145, 245, 345, 445]
    assert value["window_counts"][:, 1:].tolist() == [[5] * 255] * 5


@pytest.mark.parametrize("count", [0, 1, 49, 51, 99])
def test_incomplete_export_is_rejected_without_consuming_future_completion(module, count):
    ring = module.CellRing()
    fill(ring, 0, count)
    with pytest.raises(ValueError):
        ring.export_observation(count // 50)
    fill(ring, count, (count // 50 + 1) * 50)
    assert ring.export_observation(count // 50)["observation_index"] == count // 50


@pytest.mark.parametrize("requested", [-1, True, 0.0, np.int64(0), 1, MAX_INT + 1])
def test_export_requires_exact_latest_observation_true_int(module, requested):
    ring = module.CellRing()
    fill(ring, 0, 50)
    with pytest.raises(ValueError):
        ring.export_observation(requested)
    assert ring.export_observation(0)["observation_index"] == 0
    with pytest.raises(ValueError):
        ring.export_observation(0)
    fill(ring, 50, 100)
    with pytest.raises(ValueError):
        ring.export_observation(0)
    assert ring.export_observation(1)["observation_index"] == 1


BAD_ROWS = [None, [], {}, {**row(0), "extra": 0}]
for field in ("observation_index", "bin_index", "start_tick", "end_tick"):
    BAD_ROWS += [{key: value for key, value in row(0).items() if key != field}]
    BAD_ROWS += [row(0, **{field: value}) for value in (True, 0.0, np.int64(0), -1, MAX_INT + 1)]
BAD_ROWS += [row(0, counts=value) for value in (None, (), [0] * 255, [0] * 257, np.zeros(256, dtype=np.uint8))]
BAD_ROWS += [row(0, counts=[0] * 255 + [value]) for value in (True, 0.0, np.int64(0), -1, 101, 256, MAX_INT + 1)]
BAD_ROWS += [row(0, end_tick=99), row(0, end_tick=101), row(0, start_tick=1), row(1), row(50)]


@pytest.mark.parametrize("payload", BAD_ROWS)
def test_malformed_callback_is_atomic_before_uint8_conversion(module, payload):
    ring = module.CellRing()
    before = ring.ring_sha256(), ring.stats, ring.sink_body_total_ns, ring.sink_body_calls
    with pytest.raises(ValueError):
        ring(payload)
    assert (ring.ring_sha256(), ring.stats, ring.sink_body_total_ns, ring.sink_body_calls) == before
    ring(row(0))
    assert ring.stats["total_bins"] == 1


@pytest.mark.parametrize("wrong", [row(48), row(50), row(49, start_tick=5000, end_tick=5100), row(49, bin_index=50)])
def test_gap_or_observation_boundary_failure_retains_existing_ring(module, wrong):
    ring = module.CellRing()
    fill(ring, 0, 49)
    before = ring.ring_sha256(), ring.stats
    with pytest.raises(ValueError):
        ring(wrong)
    assert (ring.ring_sha256(), ring.stats) == before
    ring(row(49))
    assert ring.export_observation(0)["counts"].shape == (50, 256)


def test_callback_input_mutation_cannot_rewrite_stored_counts(module):
    ring = module.CellRing()
    payload = row(0)
    ring(payload)
    before = ring.ring_sha256()
    payload["counts"][:] = [100] * 256
    payload["end_tick"] = 200
    assert ring.ring_sha256() == before


def test_invalid_counts_at_full_ring_cannot_evict_or_change_export(module):
    ring = module.CellRing()
    fill(ring, 0, 1000)
    before = ring.ring_sha256(), ring.stats
    with pytest.raises(ValueError):
        ring(row(1000, counts=[1] * 255 + [101]))
    assert (ring.ring_sha256(), ring.stats) == before
    assert ring.export_observation(19)["end_tick"][-1] == 100000
    ring(row(1000))
    assert ring.stats["evictions"] == 1


@pytest.mark.parametrize("age,status", [(299999, "handed_off"), (300000, "expired"), (300001, "expired"), (900000, "expired")])
def test_handoff_enforces_exact_five_minute_deadline_and_stalls(module, age, status):
    queue = module.ImageAdmission()
    assert queue.offer(1, A, now_ms=100)["status"] == "admitted"
    result = queue.handoff(now_ms=100 + age)
    assert result["status"] == status
    assert result["wall_ms"] == 100 + age
    assert result["request"] == {"sequence": 1, "frame_sha256": A, "offered_ms": 100}
    assert queue.pending is None
    assert queue.active == (result["request"] if status == "handed_off" else None)
    assert queue.handoff(now_ms=100 + age)["status"] in {"busy", "empty"}
    with pytest.raises(ValueError):
        queue.offer(1, A, now_ms=100 + age)


def test_one_active_one_pending_full_rejections_keep_identity_and_deadline(module):
    queue = module.ImageAdmission()
    queue.offer(1, A, now_ms=0)
    queue.handoff(now_ms=0)
    queue.offer(2, B, now_ms=500)
    for sequence, frame in ((3, A), (4, B), (5, C)):
        assert queue.offer(sequence, frame, now_ms=500) == {
            "status": "full", "wall_ms": 500,
            "request": {"sequence": sequence, "frame_sha256": frame, "offered_ms": 500},
        }
    assert queue.high_watermark == 5
    assert queue.pending == {"sequence": 2, "frame_sha256": B, "offered_ms": 500}
    assert queue.handoff(now_ms=1000)["status"] == "busy"
    assert queue.finish(1, now_ms=1001)["status"] == "completed"
    assert queue.active is None and queue.pending["sequence"] == 2
    assert queue.handoff(now_ms=300500)["status"] == "expired"
    for used in range(1, 6):
        with pytest.raises(ValueError):
            queue.offer(used, A, now_ms=300500)
    assert queue.offer(6, A, now_ms=300500)["status"] == "admitted"
    assert queue.handoff(now_ms=300500)["request"]["frame_sha256"] == A


def test_finish_is_explicit_sequence_bound_and_never_hands_off_pending(module):
    queue = module.ImageAdmission()
    queue.offer(1, A, now_ms=0)
    with pytest.raises(ValueError):
        queue.finish(1, now_ms=0)
    queue.handoff(now_ms=0)
    queue.offer(2, A, now_ms=1)
    before = queue.state
    with pytest.raises(ValueError):
        queue.finish(2, now_ms=2)
    assert queue.state == before
    result = queue.finish(1, now_ms=2)
    assert result["request"]["sequence"] == 1
    assert queue.active is None and queue.pending["sequence"] == 2
    with pytest.raises(ValueError):
        queue.finish(1, now_ms=2)
    queue.handoff(now_ms=3)
    queue.finish(2, now_ms=4)
    assert queue.active is queue.pending is None
    with pytest.raises(ValueError):
        queue.offer(2, A, now_ms=4)
    assert queue.offer(3, A, now_ms=4)["status"] == "admitted"


@pytest.mark.parametrize("bad", [True, False, 0, -1, 1.0, "1", np.int64(1), MAX_INT + 1])
def test_invalid_sequence_cannot_change_queue_or_clock(module, bad):
    queue = module.ImageAdmission()
    before = queue.state
    with pytest.raises(ValueError):
        queue.offer(bad, A, now_ms=10)
    assert queue.state == before


@pytest.mark.parametrize("bad", [None, 123, b"a" * 64, "A" * 64, "g" * 64, "a" * 63, "a" * 65, "a" * 63 + "\n"])
def test_frame_sha256_is_validated_separately_before_watermark(module, bad):
    queue = module.ImageAdmission()
    before = queue.state
    with pytest.raises(ValueError):
        queue.offer(1, bad, now_ms=10)
    assert queue.state == before
    assert queue.offer(1, A, now_ms=0)["status"] == "admitted"


@pytest.mark.parametrize("method", ["offer", "handoff", "finish"])
@pytest.mark.parametrize("bad", [True, -1, 1.0, "1", np.int64(1), MAX_INT + 1, 9])
def test_all_transitions_reject_invalid_or_regressing_clocks_atomically(module, method, bad):
    queue = module.ImageAdmission()
    queue.offer(1, A, now_ms=10)
    queue.handoff(now_ms=10)
    before = queue.state
    arguments = {"offer": (2, B), "handoff": (), "finish": (1,)}
    with pytest.raises(ValueError):
        getattr(queue, method)(*arguments[method], now_ms=bad)
    assert queue.state == before


def test_many_full_rejections_have_bounded_state_and_high_watermark(module):
    queue = module.ImageAdmission()
    queue.offer(1, A, now_ms=0)
    for sequence in range(2, 10002):
        assert queue.offer(sequence, B, now_ms=sequence)["status"] == "full"
    assert queue.high_watermark == 10001
    assert queue.pending == {"sequence": 1, "frame_sha256": A, "offered_ms": 0}
    assert queue.active is None
    # No instance dictionary/list/set can grow with completed/rejected requests.
    assert not hasattr(queue, "__dict__")
    assert all(not isinstance(getattr(queue, name), (list, dict, set)) for name in queue.__slots__)
    detached = queue.state
    detached["pending"]["sequence"] = -1
    assert queue.pending["sequence"] == 1
    assert queue.handoff(now_ms=10001)["status"] == "handed_off"
    assert queue.handoff(now_ms=10001)["status"] == "busy"


def test_empty_busy_and_full_operations_establish_clock_watermark(module):
    queue = module.ImageAdmission()
    assert queue.handoff(now_ms=5)["status"] == "empty"
    with pytest.raises(ValueError):
        queue.offer(1, A, now_ms=4)
    queue.offer(1, A, now_ms=5)
    queue.handoff(now_ms=5)
    assert queue.handoff(now_ms=6)["status"] == "busy"
    with pytest.raises(ValueError):
        queue.finish(1, now_ms=5)
    queue.offer(2, B, now_ms=6)
    assert queue.offer(3, C, now_ms=7)["status"] == "full"
    with pytest.raises(ValueError):
        queue.finish(1, now_ms=6)
    assert queue.pending["offered_ms"] == 6


def test_pending_expires_while_busy_without_terminating_active_request(module):
    queue = module.ImageAdmission()
    queue.offer(1, A, now_ms=0)
    queue.handoff(now_ms=0)
    queue.offer(2, B, now_ms=1)
    assert queue.handoff(now_ms=300001)["status"] == "expired"
    assert queue.active["sequence"] == 1
    assert queue.pending is None
    queue.finish(1, now_ms=300001)
    assert queue.handoff(now_ms=300001)["status"] == "empty"
    with pytest.raises(ValueError):
        queue.offer(2, B, now_ms=300001)


@pytest.mark.parametrize("bad_sequence", [True, 0, -1, 1.0, np.int64(1), MAX_INT + 1])
def test_finish_rejects_invalid_identity_without_clock_or_slot_changes(module, bad_sequence):
    queue = module.ImageAdmission()
    queue.offer(1, A, now_ms=0)
    queue.handoff(now_ms=0)
    before = queue.state
    with pytest.raises(ValueError):
        queue.finish(bad_sequence, now_ms=10)
    assert queue.state == before


def test_maximum_sequence_and_clock_are_valid_and_do_not_overflow(module):
    queue = module.ImageAdmission()
    queue.offer(MAX_INT, A, now_ms=MAX_INT)
    assert queue.handoff(now_ms=MAX_INT)["status"] == "handed_off"
    assert queue.finish(MAX_INT, now_ms=MAX_INT)["status"] == "completed"
    with pytest.raises(ValueError):
        queue.offer(MAX_INT, B, now_ms=MAX_INT)
