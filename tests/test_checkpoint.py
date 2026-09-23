"""Checkpoint trust-boundary tests using a four-neuron native graph."""

import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from jogge_fly_brain.neural.brain import MemoryBrain
from jogge_fly_brain.neural import checkpoint
from jogge_fly_brain.neural.visual import VisualMemoryBrain


@pytest.fixture
def brain(tmp_path):
    graph = tmp_path / "graph.npz"
    np.savez(
        graph,
        ids=np.array([10, 20, 30, 40], dtype=np.int64),
        ptr=np.array([0, 1, 2, 2, 2], dtype=np.int64),
        post=np.array([2, 2], dtype=np.int32),
        weight=np.array([0.275, 0.275], dtype=np.float32),
        retina=np.array([0], dtype=np.int32),
        uv=np.array([[0.5, 0.5]], dtype=np.float32),
        lamina=np.array([], dtype=np.int32),
        sugar=np.array([], dtype=np.int32),
        superclass=np.zeros(4, dtype=np.uint8),
    )
    return MemoryBrain(
        path=graph,
        circuit={
            "kc": np.array([0], dtype=np.int32),
            "dan": np.array([1], dtype=np.int32),
            "edges": np.array([0], dtype=np.int64),
            "pre": np.array([0], dtype=np.int32),
            "gain": np.array([[1.0]], dtype=np.float32),
            "kc_mask": np.array([1, 0, 0, 0], dtype=np.uint8),
            "dan_index": np.array([-1, 0, -1, -1], dtype=np.int8),
        },
        modulation_mask=np.array([0, 1, 0, 0], dtype=np.uint8),
    )


def state_bytes(brain):
    return {
        "arrays": {
            name: getattr(brain, name).tobytes()
            for name in ["weight", *brain.fields]
        },
        "cursor": brain.cursor,
        "sim_ms": brain.sim_ms,
        "total_spikes": brain.total_spikes,
        "weights_frozen": brain.weights_frozen,
    }


@pytest.fixture
def saved(brain, tmp_path):
    path = tmp_path / "checkpoint.npz"
    brain.checkpoint(path)
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    metadata = json.loads(str(arrays.pop("metadata")))
    brain.step(
        np.ones(1, dtype=np.float32),
        10.0,
        stimulation=(np.array([1], dtype=np.int32), 30.0),
        learning=True,
    )
    brain.weights_frozen = True
    return path, arrays, metadata


def write_checkpoint(saved):
    path, arrays, metadata = saved
    np.savez(path, metadata=json.dumps(metadata), **arrays)
    return path


def assert_rejected_without_mutation(brain, path):
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.restore(path)
    assert state_bytes(brain) == before


@pytest.mark.parametrize("field", ["cursor", "total_spikes"])
def test_malformed_scalar_does_not_partially_replace_live_state(brain, saved, field):
    saved[2][field] = "not-an-integer"
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cursor", -1),
        ("cursor", 2**63),
        ("cursor", 1.5),
        ("cursor", "1"),
        ("cursor", True),
        ("cursor", None),
        ("total_spikes", -1),
        ("total_spikes", 2**63),
        ("total_spikes", 1.5),
        ("total_spikes", "1"),
        ("total_spikes", False),
        ("total_spikes", None),
        ("weights_frozen", "false"),
        ("weights_frozen", 0),
        ("weights_frozen", 1),
        ("weights_frozen", None),
    ],
)
def test_scalar_metadata_has_strict_safe_types_and_ranges(brain, saved, field, value):
    saved[2][field] = value
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


@pytest.mark.parametrize(
    ("field", "index", "value"),
    [
        ("nactive", 0, -1),
        ("nactive", 0, 5),
        ("active", 0, -1),
        ("active", 0, 4),
        ("active_flag", 0, 2),
        ("active_flag", 0, 0),
        ("active_flag", 1, 1),
        ("queue_count", 0, -1),
        ("queue_count", 0, 5),
        ("refractory", 0, -1),
        ("counts", 0, -1),
        ("last", 0, -2),
        ("last", 0, 1),
        ("eligibility_last", 0, -1),
        ("eligibility_last", 0, 1),
        ("modulation_last", 0, -1),
        ("modulation_last", 0, 1),
    ],
)
def test_native_state_invariants_are_checked_before_copying(
    brain, saved, field, index, value,
):
    saved[1][field][index] = value
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


def test_duplicate_active_prefix_is_rejected(brain, saved):
    saved[1]["nactive"][0] = 2
    saved[1]["active"][:2] = [0, 0]
    saved[1]["active_flag"][1] = 1
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


def test_active_flags_must_match_prefix_membership_not_only_count(brain, saved):
    saved[1]["active_flag"].fill(0)
    saved[1]["active_flag"][1] = 1
    assert np.count_nonzero(saved[1]["active_flag"]) == saved[1]["nactive"][0]
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


def test_evolved_last_timestamp_must_precede_cursor(brain, saved):
    saved[2]["cursor"] = 1
    saved[1]["last"][0] = 1
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


@pytest.mark.parametrize("index", [-1, 4])
def test_out_of_bounds_queued_neuron_is_rejected(brain, saved, index):
    saved[1]["queue_count"][0] = 1
    saved[1]["queue"][0, 0] = index
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


@pytest.mark.parametrize("change", ["extra", "missing", "shape", "dtype", "nan"])
def test_exact_array_schema_and_finite_values_are_required(brain, saved, change):
    arrays = saved[1]
    if change == "extra":
        arrays["unknown"] = np.zeros(1)
    elif change == "missing":
        del arrays["adaptation"]
    elif change == "shape":
        arrays["adaptation"] = np.zeros(3, dtype=np.float32)
    elif change == "dtype":
        arrays["adaptation"] = arrays["adaptation"].astype(np.float64)
    else:
        arrays["adaptation"][0] = np.nan
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


def test_initial_emitted_checkpoint_preserves_lazy_sentinels(brain, saved):
    assert np.all(saved[1]["last"] == -1)
    brain.restore(saved[0])
    assert brain.cursor == 0
    assert brain.total_spikes == 0
    assert brain.weights_frozen is False
    assert np.all(brain.last == -1)


def test_evolved_emitted_checkpoint_replays_with_native_kernel(brain, tmp_path):
    light = np.ones(1, dtype=np.float32)
    brain.step(
        light,
        100.0,
        stimulation=(np.array([1], dtype=np.int32), 30.0),
        learning=True,
    )
    assert brain.total_spikes > 0
    assert np.any(brain.memory_w != 0)
    path = tmp_path / "evolved.npz"
    expected = state_bytes(brain)
    brain.checkpoint(path)
    first_counts, _ = brain.step(light, 25.3)
    continuation = state_bytes(brain)
    brain.restore(path)
    assert state_bytes(brain) == expected
    second_counts, _ = brain.step(light, 25.3)
    np.testing.assert_array_equal(second_counts, first_counts)
    assert state_bytes(brain) == continuation


@pytest.mark.parametrize(("cursor", "slot"), [(0, 18), (1, 0), (19, 18)])
def test_next_queue_write_slot_must_be_empty(brain, saved, cursor, slot):
    # The kernel appends at (clock + 18) % 19 before draining clock % 19.
    saved[2]["cursor"] = cursor
    saved[1]["queue_count"][slot] = 4
    saved[1]["queue"][slot] = [0, 1, 2, 3]
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


@pytest.mark.parametrize("cursor", [2**63 - 1, 2**63 - 18])
def test_cursor_must_leave_room_for_native_tick_and_delay_arithmetic(
    brain, saved, cursor,
):
    saved[2]["cursor"] = cursor
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


def test_native_step_rejects_exhausted_cursor_before_mutating(brain, monkeypatch):
    brain.cursor = 2**63 - 19
    brain.sim_ms = brain.cursor * brain.dt

    def unexpected_native_call(*args):
        pytest.fail("Unsafe cursor reached the native kernel")

    # Intercept the unsafe native boundary; executing signed overflow is unsafe.
    monkeypatch.setattr(brain, "advance", unexpected_native_call)
    before = state_bytes(brain)
    with pytest.raises(ValueError, match="cursor"):
        brain.step(np.ones(1, dtype=np.float32), 10.0)
    assert state_bytes(brain) == before


def test_multi_batch_step_rejects_cursor_exhaustion_before_mutating(brain):
    delay = brain.queue.shape[0] - 1
    brain.cursor = np.iinfo(np.int64).max - delay - 150
    brain.sim_ms = brain.cursor * brain.dt
    before = state_bytes(brain)
    with pytest.raises(ValueError, match="cursor"):
        brain.step(np.ones(1, dtype=np.float32), 20.0)
    assert state_bytes(brain) == before


def test_spike_limit_allows_roundtrip_then_rejects_before_mutating(
    brain, saved, tmp_path,
):
    limit = int(np.iinfo(np.int64).max)
    saved[2]["total_spikes"] = limit - brain.n
    saved[1]["v"].fill(-44.0)
    saved[1]["active"][:] = np.arange(brain.n, dtype=np.int32)
    saved[1]["active_flag"].fill(1)
    saved[1]["nactive"][0] = brain.n
    brain.restore(write_checkpoint(saved))

    counts, _ = brain.step(np.zeros(1, dtype=np.float32), brain.dt)
    assert int(counts.sum()) == brain.n
    assert brain.total_spikes == limit

    path = tmp_path / "maximum-spike-count.npz"
    expected = state_bytes(brain)
    brain.checkpoint(path)
    brain.reset()
    brain.restore(path)
    assert state_bytes(brain) == expected

    before = state_bytes(brain)
    with pytest.raises(ValueError, match="spike"):
        brain.step(np.zeros(1, dtype=np.float32), 20.0)
    assert state_bytes(brain) == before


def test_rgb_step_rejects_exhausted_cursor_before_mutating_visual_state(brain):
    brain.r8 = np.array([0], dtype=np.int32)
    brain.r8_uv = np.array([[0.5, 0.5]], dtype=np.float32)
    brain.r8_channel = np.array([1], dtype=np.int32)
    brain.r8_light = np.zeros(1, dtype=np.float32)
    brain.fields.append("r8_light")
    delay = brain.queue.shape[0] - 1
    brain.cursor = np.iinfo(np.int64).max - delay
    brain.sim_ms = brain.cursor * brain.dt
    frame = np.array([[[0, 255, 0]]], dtype=np.uint8)

    before = state_bytes(brain)
    with pytest.raises(ValueError, match="cursor"):
        VisualMemoryBrain.rgb_step(brain, frame, brain.dt)
    assert state_bytes(brain) == before


def test_emitted_checkpoints_remain_valid_across_queue_rotations(brain, tmp_path):
    path = tmp_path / "rotating.npz"
    light = np.ones(1, dtype=np.float32)
    brain.step(light, 100.0)
    for _ in range(19):
        brain.step(light, 0.1)
        before = state_bytes(brain)
        brain.checkpoint(path)
        brain.restore(path)
        assert state_bytes(brain) == before


@pytest.mark.parametrize("change", ["extra", "missing", "not-an-object"])
def test_exact_metadata_fields_are_required(brain, saved, change):
    if change == "extra":
        saved[2]["unknown"] = 1
    elif change == "missing":
        del saved[2]["total_spikes"]
    else:
        saved = (*saved[:2], [])
    assert_rejected_without_mutation(brain, write_checkpoint(saved))


def test_read_only_destination_does_not_partially_commit(brain, saved):
    brain.adaptation.flags.writeable = False
    try:
        assert_rejected_without_mutation(brain, saved[0])
    finally:
        brain.adaptation.flags.writeable = True


def test_checkpoint_records_versioned_model_source_identity(brain, saved):
    fingerprint = saved[2].get("model_fingerprint")
    assert fingerprint is not None
    assert fingerprint["version"] == "model-source/v1"
    assert len(fingerprint["sha256"]) == 64
    assert {
        "neural/brain.py",
        "neural/state.py",
        "neural/circuit.py",
        "neural/rule.py",
        "neural/sensory.py",
        "neural/visual.py",
        "neural/kernel.cpp",
        "neural/checkpoint.py",
        "neural/common.py",
        "neural/native.py",
        "engine.py",
    } <= fingerprint["sources_sha256"].keys()
    assert saved[2]["build"]["binary_sha256"]
    assert saved[2]["build"]["compiler"]
    assert saved[2]["configuration_sha256"]


@pytest.mark.parametrize("change", ["missing", "version", "source", "digest"])
def test_incompatible_source_identity_is_rejected_before_arrays(brain, saved, change):
    # The corrupt late array proves that identity validation takes priority.
    saved[1]["adaptation"][0] = np.nan
    metadata = saved[2]
    fingerprint = metadata.setdefault("model_fingerprint", {})
    if change == "missing":
        del metadata["model_fingerprint"]
    elif change == "version":
        fingerprint["version"] = "incompatible/v2"
    elif change == "source":
        fingerprint.setdefault("sources_sha256", {})["neural/brain.py"] = "0" * 64
    else:
        fingerprint["sha256"] = "0" * 64
    before = state_bytes(brain)
    with pytest.raises(ValueError, match="provenance|metadata fields"):
        brain.restore(write_checkpoint(saved))
    assert state_bytes(brain) == before


def test_fingerprint_hashes_exact_bytes_without_absolute_paths(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "brain.py").write_bytes(b"abc")
    (first / "kernel.cpp").write_bytes(b"line\r\n")
    (second / "kernel.cpp").write_bytes(b"line\r\n")
    (second / "brain.py").write_bytes(b"abc")
    (second / "ignored.pyc").write_bytes(b"cache")
    a = checkpoint.model_fingerprint(first)
    b = checkpoint.model_fingerprint(second)
    assert a == b
    assert a["sources_sha256"]["brain.py"] == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    (second / "kernel.cpp").write_bytes(b"line\n")
    assert checkpoint.model_fingerprint(second)["sha256"] != a["sha256"]


@pytest.mark.parametrize(
    "source",
    [
        "neural/brain.py",
        "neural/state.py",
        "neural/circuit.py",
        "neural/rule.py",
        "neural/sensory.py",
        "neural/visual.py",
        "neural/kernel.cpp",
        "neural/checkpoint.py",
        "neural/common.py",
        "neural/native.py",
        "engine.py",
    ],
)
def test_each_continuation_source_changes_fingerprint(tmp_path, source):
    package = Path(checkpoint.__file__).parents[1]
    copied = tmp_path / "package"
    shutil.copytree(package, copied, ignore=shutil.ignore_patterns("__pycache__"))
    original = checkpoint.model_fingerprint(copied)
    changed = copied / source
    changed.write_bytes(changed.read_bytes() + b"\n")
    assert checkpoint.model_fingerprint(copied)["sha256"] != original["sha256"]
