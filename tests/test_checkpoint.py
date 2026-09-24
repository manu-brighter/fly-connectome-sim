"""Checkpoint trust-boundary tests using a four-neuron native graph."""

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import shutil

import numpy as np
import pytest

from fly_connectome_sim.engine import FlyEngine, NeuralGroups
from fly_connectome_sim.neural.brain import MemoryBrain
from fly_connectome_sim.neural import checkpoint
from fly_connectome_sim.neural.visual import VisualMemoryBrain


def make_brain(graph):
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
    return make_brain(graph)


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
def intervention_brains(tmp_path):
    graph = tmp_path / "intervention-graph.npz"
    np.savez(
        graph,
        ids=np.array([10, 20, 30, 40], dtype=np.int64),
        ptr=np.array([0, 2, 3, 3, 3], dtype=np.int64),
        post=np.array([2, 3, 2], dtype=np.int32),
        weight=np.array([0.275, 0.3, 0.2], dtype=np.float32),
        retina=np.array([0], dtype=np.int32),
        uv=np.array([[0.5, 0.5]], dtype=np.float32),
        lamina=np.array([], dtype=np.int32),
        sugar=np.array([], dtype=np.int32),
        superclass=np.zeros(4, dtype=np.uint8),
    )

    def new_brain():
        return MemoryBrain(
            path=graph,
            circuit={
                "kc": np.array([0], dtype=np.int32),
                "dan": np.array([1], dtype=np.int32),
                "edges": np.array([1, 0], dtype=np.int64),
                "pre": np.array([0, 0], dtype=np.int32),
                "gain": np.array([[0.0, 1.0]], dtype=np.float32),
                "kc_mask": np.array([1, 0, 0, 0], dtype=np.uint8),
                "dan_index": np.array([-1, 0, -1, -1], dtype=np.int8),
            },
            modulation_mask=np.array([0, 1, 0, 0], dtype=np.uint8),
        )

    return new_brain(), new_brain()


def test_candidate_snapshot_is_ordered_copied_and_frozen(intervention_brains):
    donor, _ = intervention_brains
    targets = np.array([2], dtype=np.int32)
    snapshot = donor.candidate_memory(targets)
    np.testing.assert_array_equal(snapshot.edge_indices, [0])
    assert snapshot.edge_indices.dtype == donor.circuit["edges"].dtype
    assert snapshot.memory_u.dtype == donor.memory_u.dtype
    assert snapshot.memory_w.dtype == donor.memory_w.dtype
    assert snapshot.weight.dtype == donor.weight.dtype
    assert snapshot.cursor == donor.cursor
    assert snapshot.sim_ms == donor.sim_ms
    np.testing.assert_array_equal(snapshot.target_indices, [2])
    for field in ("target_indices", "edge_indices", "memory_u", "memory_w", "weight"):
        assert not getattr(snapshot, field).flags.writeable
        with pytest.raises(ValueError):
            getattr(snapshot, field).flags.writeable = True
    with pytest.raises(FrozenInstanceError):
        snapshot.cursor = 1
    targets[0] = 3
    np.testing.assert_array_equal(snapshot.target_indices, [2])
    donor.memory_u[1] = 0.2
    assert snapshot.memory_u[0] == 0


@pytest.mark.parametrize("branch", ["necessity", "sufficiency", "sham"])
def test_candidate_intervention_preserves_non_candidate_state_and_passive_decay(
    intervention_brains, branch, tmp_path,
):
    trained, matched = intervention_brains
    for member in (trained, matched):
        member.memory_u[0] = 0.25
        member.memory_w[0] = 0.2
        member.weight[1] = member.baseline_plastic[0] * 1.2
    light = np.ones(1, dtype=np.float32)
    pulse = (np.array([1], dtype=np.int32), 30.0)
    trained.step(light, 100.0, stimulation=pulse, learning=True)
    matched.step(light, 100.0, learning=False)
    assert trained.cursor == matched.cursor
    trained_checkpoint = tmp_path / "trained-before.npz"
    matched_checkpoint = tmp_path / "matched-before.npz"
    trained.checkpoint(trained_checkpoint)
    matched.checkpoint(matched_checkpoint)
    trained_memory = trained.candidate_memory(np.array([2], dtype=np.int32))
    matched_memory = matched.candidate_memory(np.array([2], dtype=np.int32))
    assert not np.array_equal(trained_memory.memory_w, matched_memory.memory_w)

    recipient, donor_memory = {
        "necessity": (trained, matched_memory),
        "sufficiency": (matched, trained_memory),
        "sham": (trained, trained_memory),
    }[branch]
    recipient.restore(matched_checkpoint if branch == "sufficiency" else trained_checkpoint)
    before = state_bytes(recipient)
    mbon07_before = recipient.candidate_memory(np.array([3], dtype=np.int32))
    assert mbon07_before.memory_u[0] != 0
    assert mbon07_before.memory_w[0] != 0
    untouched = (
        recipient.memory_u[0:1].tobytes(),
        recipient.memory_w[0:1].tobytes(),
        recipient.weight[1:3].tobytes(),
    )
    recipient.replace_candidate_memory(donor_memory)
    after = state_bytes(recipient)
    assert (
        recipient.memory_u[0:1].tobytes(),
        recipient.memory_w[0:1].tobytes(),
        recipient.weight[1:3].tobytes(),
    ) == untouched
    for name in before["arrays"]:
        if name not in {"memory_u", "memory_w", "weight"}:
            assert after["arrays"][name] == before["arrays"][name]
    for name in ("cursor", "sim_ms", "total_spikes", "weights_frozen"):
        assert after[name] == before[name]
    after_checkpoint = tmp_path / f"{branch}-after.npz"
    recipient.checkpoint(after_checkpoint)
    recipient.restore(matched_checkpoint if branch == "sufficiency" else trained_checkpoint)
    assert state_bytes(recipient) == before
    recipient.restore(after_checkpoint)
    assert state_bytes(recipient) == after
    selected = recipient.candidate_memory(np.array([2], dtype=np.int32))
    for name in ("memory_u", "memory_w", "weight"):
        np.testing.assert_array_equal(getattr(selected, name), getattr(donor_memory, name))
        np.testing.assert_array_equal(
            getattr(recipient.candidate_memory(np.array([3], dtype=np.int32)), name),
            getattr(mbon07_before, name),
        )

    start = recipient.sim_ms
    recipient.step(np.zeros(1, dtype=np.float32), 200.0, learning=False)
    assert recipient.sim_ms - start == 200.0
    assert recipient.weights_frozen is False
    if branch != "necessity":
        assert not np.array_equal(
            recipient.candidate_memory(np.array([2], dtype=np.int32)).memory_w,
            donor_memory.memory_w,
        )


def test_aliasing_candidate_payload_is_detached_before_assignment(intervention_brains):
    recipient, _ = intervention_brains
    snapshot = recipient.candidate_memory(np.array([2, 3], dtype=np.int32))
    donor_u = np.array([0.2, 0.3], dtype=recipient.memory_u.dtype)
    aliased = replace(
        snapshot,
        memory_u=donor_u,
        memory_w=recipient.memory_u,
    )

    recipient.replace_candidate_memory(aliased)

    np.testing.assert_array_equal(recipient.memory_u, donor_u)
    np.testing.assert_array_equal(recipient.memory_w, [0.0, 0.0])
    np.testing.assert_array_equal(recipient.weight[snapshot.edge_indices], snapshot.weight)


@pytest.mark.parametrize("field", ["memory_u", "memory_w"])
@pytest.mark.parametrize("invalid", [np.nan, -0.91])
def test_masked_invalid_candidate_payload_cannot_mutate_state(
    intervention_brains, field, invalid,
):
    recipient, _ = intervention_brains
    snapshot = recipient.candidate_memory(np.array([2, 3], dtype=np.int32))
    hidden = np.ma.array(getattr(snapshot, field).copy(), mask=[True, False])
    hidden.data[0] = invalid
    before = state_bytes(recipient)

    with pytest.raises(ValueError):
        recipient.replace_candidate_memory(replace(snapshot, **{field: hidden}))

    assert state_bytes(recipient) == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cursor", False),
        ("cursor", 0.0),
        ("sim_ms", True),
        ("sim_ms", float("nan")),
        ("sim_ms", float("inf")),
        ("sim_ms", "0"),
    ],
)
def test_candidate_snapshot_rejects_malformed_clock_scalars(
    intervention_brains, field, value,
):
    recipient, _ = intervention_brains
    if field == "sim_ms":
        recipient.step(np.zeros(1, dtype=np.float32), 1.0)
    snapshot = recipient.candidate_memory(np.array([2], dtype=np.int32))
    before = state_bytes(recipient)

    with pytest.raises(ValueError):
        recipient.replace_candidate_memory(replace(snapshot, **{field: value}))

    assert state_bytes(recipient) == before


@pytest.mark.parametrize(
    "change",
    [
        "clock", "cursor", "order", "duplicate", "missing", "edge_dtype",
        "u_dtype", "w_dtype", "weight_dtype", "u_shape", "w_shape",
        "weight_shape", "nan_u", "nan_w", "nan_weight", "low_u",
        "high_u", "low_w", "high_w", "inconsistent_weight",
    ],
)
def test_invalid_candidate_replacement_is_atomic(intervention_brains, change):
    recipient, _ = intervention_brains
    target = np.array([2, 3], dtype=np.int32)
    snapshot = recipient.candidate_memory(target)
    values = {name: getattr(snapshot, name).copy() for name in
              ("edge_indices", "memory_u", "memory_w", "weight")}
    if change == "clock":
        snapshot = replace(snapshot, sim_ms=snapshot.sim_ms + 0.1)
    elif change == "cursor":
        snapshot = replace(snapshot, cursor=snapshot.cursor + 1)
    elif change == "order":
        values["edge_indices"] = values["edge_indices"][::-1]
    elif change == "duplicate":
        values["edge_indices"][1] = values["edge_indices"][0]
    elif change == "missing":
        values["edge_indices"] = values["edge_indices"][:1]
    elif change.endswith("_dtype"):
        key = change.removesuffix("_dtype")
        key = "memory_" + key if key in {"u", "w"} else (
            "edge_indices" if key == "edge" else key
        )
        values[key] = values[key].astype(np.float64 if key == "weight" else np.float32)
    elif change.endswith("_shape"):
        key = change.removesuffix("_shape")
        key = "memory_" + key if key in {"u", "w"} else key
        values[key] = values[key][:1]
    elif change.startswith("nan_"):
        key = change.removeprefix("nan_")
        key = "memory_" + key if key in {"u", "w"} else key
        values[key][0] = np.nan
    elif change.startswith(("low_", "high_")):
        bound, key = change.split("_")
        values["memory_" + key][0] = -0.91 if bound == "low" else 1.01
    else:
        values["weight"][0] += 0.01
    if change not in {"clock", "cursor"}:
        snapshot = replace(snapshot, **values)
    before = state_bytes(recipient)
    with pytest.raises(ValueError):
        recipient.replace_candidate_memory(snapshot)
    assert state_bytes(recipient) == before


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


def test_checkpoint_and_engine_share_complete_immutable_model_provenance(brain, saved):
    provenance = brain.model_provenance()

    assert set(provenance) == {
        "model",
        "model_fingerprint",
        "build",
        "eta",
        "parameters",
        "graph_ids_sha256",
        "graph_ptr_sha256",
        "graph_post_sha256",
        "plastic_edges_sha256",
        "configuration_sha256",
    }
    assert saved[2] == {
        **provenance,
        "cursor": 0,
        "weights_frozen": False,
        "total_spikes": 0,
    }


@pytest.mark.parametrize(
    "change",
    ["eta", "compiler", "binary", "graph_ids", "graph_ptr", "graph_post"],
)
def test_engine_identity_changes_with_immutable_numerical_provenance(
    brain, tmp_path, change,
):
    groups = NeuralGroups(
        pam11=np.array([0], dtype=np.int32),
        ppl101=np.array([0], dtype=np.int32),
        kc=np.array([0], dtype=np.int32),
        mbon07=np.array([0], dtype=np.int32),
        mbon11=np.array([0], dtype=np.int32),
        motor_left=np.array([0], dtype=np.int32),
        motor_right=np.array([0], dtype=np.int32),
    )
    baseline = FlyEngine(brain=brain, groups=groups).identity()
    changed_brain = make_brain(tmp_path / "graph.npz")

    if change == "eta":
        changed_brain.eta += 0.001
    elif change == "compiler":
        changed_brain.build = {
            **changed_brain.build,
            "compiler": "different compiler",
        }
    elif change == "binary":
        changed_brain.build = {
            **changed_brain.build,
            "binary_sha256": "0" * 64,
        }
    elif change == "graph_ids":
        changed_brain.ids[0] += 1
    elif change == "graph_ptr":
        changed_brain.ptr[1] += 1
    else:
        changed_brain.post[0] += 1

    changed = FlyEngine(brain=changed_brain, groups=groups).identity()

    assert changed["sha256"] != baseline["sha256"]


def test_model_provenance_excludes_evolved_mutable_state(brain):
    before = brain.model_provenance()

    brain.step(
        np.ones(1, dtype=np.float32),
        10.0,
        stimulation=(np.array([1], dtype=np.int32), 30.0),
        learning=True,
    )

    assert brain.cursor > 0
    assert brain.total_spikes > 0
    assert brain.model_provenance() == before


def test_same_engine_rejects_eta_change_after_identity_snapshot(brain):
    groups = NeuralGroups(**{
        name: np.array([0], dtype=np.int32)
        for name in NeuralGroups.__dataclass_fields__
    })
    engine = FlyEngine(brain=brain, groups=groups)
    engine.identity()
    brain.eta += 0.001

    with pytest.raises(RuntimeError, match="provenance"):
        engine.identity()


def test_same_engine_rejects_native_build_change_after_identity_snapshot(brain):
    groups = NeuralGroups(**{
        name: np.array([0], dtype=np.int32)
        for name in NeuralGroups.__dataclass_fields__
    })
    engine = FlyEngine(brain=brain, groups=groups)
    engine.identity()
    brain.build["compiler"] = "different compiler"

    with pytest.raises(RuntimeError, match="provenance"):
        engine.identity()


def test_identity_snapshot_makes_large_graph_provenance_arrays_read_only(brain):
    groups = NeuralGroups(**{
        name: np.array([0], dtype=np.int32)
        for name in NeuralGroups.__dataclass_fields__
    })
    engine = FlyEngine(brain=brain, groups=groups)
    engine.identity()

    assert not brain.ids.flags.writeable
    assert not brain.ptr.flags.writeable
    assert not brain.post.flags.writeable
    with pytest.raises(ValueError, match="read-only"):
        brain.post[0] += 1


def test_same_engine_rejects_replaced_graph_array_after_identity_snapshot(brain):
    groups = NeuralGroups(**{
        name: np.array([0], dtype=np.int32)
        for name in NeuralGroups.__dataclass_fields__
    })
    engine = FlyEngine(brain=brain, groups=groups)
    engine.identity()
    brain.ids = brain.ids.copy()

    with pytest.raises(RuntimeError, match="provenance"):
        engine.identity()


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
