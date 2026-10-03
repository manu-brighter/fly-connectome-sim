"""Checkpoint trust-boundary tests using a four-neuron native graph."""

import json
import hashlib
import struct
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


def test_candidate_state_digests_are_read_only(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    before = state_bytes(brain)
    result = brain.candidate_state_digests(np.array([2, 3], dtype=np.int32))
    assert set(result) == {"candidate_memory_sha256", "noncandidate_state_sha256"}
    assert all(len(value) == 64 and set(value) <= set("0123456789abcdef")
               for value in result.values())
    assert state_bytes(brain) == before


def digest_codec(metadata=None, arrays=None, **kwargs):
    return checkpoint._candidate_state_digests(
        {"cursor": 0, "total_spikes": 0, "weights_frozen": False, "dt": 0.1}
        if metadata is None else metadata,
        {"memory_u": np.array([0.0, 0.25], dtype=np.float32),
         "memory_w": np.array([0.0, -0.25], dtype=np.float32),
         "weight": np.array([-0.0, 1.0, 2.0, 3.0, 5.0], dtype=np.float32)}
        if arrays is None else arrays,
        target_indices=kwargs.pop("target_indices", np.array([2, 3])),
        candidate_positions=kwargs.pop("candidate_positions", np.array([0, 1])),
        edge_indices=kwargs.pop("edge_indices", np.array([4, 1])), **kwargs,
    )


def test_candidate_state_digests_literal_wire_vectors():
    # Literal headers/data independently specify the normative A/G/E/X framing.
    headers = {
        "circuit_positions": b'{"byteorder":"little","itemsize":8,"kind":"u","name":"circuit_positions","nbytes":16,"rank":1,"shape":[2]}',
        "edge_indices": b'{"byteorder":"little","itemsize":8,"kind":"u","name":"edge_indices","nbytes":16,"rank":1,"shape":[2]}',
        "target_indices": b'{"byteorder":"little","itemsize":8,"kind":"u","name":"target_indices","nbytes":16,"rank":1,"shape":[2]}',
        "memory_u": b'{"byteorder":"little","itemsize":4,"kind":"f","name":"memory_u","nbytes":8,"rank":1,"shape":[2]}',
        "memory_w": b'{"byteorder":"little","itemsize":4,"kind":"f","name":"memory_w","nbytes":8,"rank":1,"shape":[2]}',
        "weight_selected": b'{"byteorder":"little","itemsize":4,"kind":"f","name":"weight","nbytes":8,"rank":1,"shape":[2]}',
        "weight": b'{"byteorder":"little","itemsize":4,"kind":"f","name":"weight","nbytes":20,"rank":1,"shape":[5]}',
    }
    u64 = lambda n: struct.pack("<Q", n)
    vectors = {
        "circuit_positions": bytes.fromhex("00000000000000000100000000000000"),
        "edge_indices": bytes.fromhex("04000000000000000100000000000000"),
        "target_indices": bytes.fromhex("02000000000000000300000000000000"),
        "memory_u": bytes.fromhex("000000000000803e"),
        "memory_w": bytes.fromhex("00000000000080be"),
        "weight_selected": bytes.fromhex("0000a0400000803f"),
    }
    def record(name):
        header, data = headers[name], vectors[name]
        return b"A" + u64(len(header)) + header + u64(len(data)) + data
    group = b"G" + u64(3) + b"".join(record(name) for name in
        ("circuit_positions", "edge_indices", "target_indices"))
    immutable = b'{"dt":0.1}'
    candidate = (b"fly-connectome-candidate-memory/v1\0" + b"M"
                 + u64(len(immutable)) + immutable + group + b"C" + u64(3)
                 + b"".join(record(name) for name in
                            ("memory_u", "memory_w", "weight_selected")))
    metadata = b'{"cursor":0,"dt":0.1,"total_spikes":0,"weights_frozen":false}'
    noncandidate = (b"fly-connectome-noncandidate-state/v1\0" + b"M"
                    + u64(len(metadata)) + metadata + group + b"N" + u64(3))
    for name, indices, data in (
        ("memory_u", vectors["circuit_positions"], b""),
        ("memory_w", vectors["circuit_positions"], b""),
        ("weight", bytes.fromhex("01000000000000000400000000000000"),
         bytes.fromhex("000000800000004000004040")),
    ):
        header = headers[name]
        noncandidate += (b"E" + u64(len(header)) + header + b"X" + u64(2)
                         + indices + u64(len(data)) + data)
    expected = {"candidate_memory_sha256": hashlib.sha256(candidate).hexdigest(),
                "noncandidate_state_sha256": hashlib.sha256(noncandidate).hexdigest()}
    assert digest_codec() == expected
    for size in (8, 9, 15, 17, 64):
        assert digest_codec(chunk_bytes=size) == expected
    assert len(set(expected.values())) == 2
    arrays = {"memory_u": np.array([0, .25], dtype=np.float32),
              "memory_w": np.array([0, -.25], dtype=np.float32),
              "weight": np.array([-0., 1, 2, 3, 5], dtype=np.float32)}
    assert checkpoint.checkpoint_state_sha256(
        {"cursor": 0, "dt": .1, "total_spikes": 0, "weights_frozen": False}, arrays,
    ) not in expected.values()
    assert checkpoint.raw_array_sha256(arrays["weight"]) not in expected.values()


@pytest.mark.parametrize("branch", ["necessity", "sufficiency", "sham"])
@pytest.mark.parametrize("targets", [[2], [2, 3]])
def test_candidate_state_digests_intervention_relations(intervention_brains, branch, targets, tmp_path):
    trained, matched = intervention_brains
    targets = np.array(targets, dtype=np.int32)
    for member in (trained, matched):
        member.lock_model_provenance()
        member.cursor = 20
        member.sim_ms = 20 * member.dt
    trained.memory_u[:] = [.25, .125]
    trained.memory_w[:] = [.25, .125]
    trained.weight[trained.circuit["edges"]] = trained.baseline_plastic * (1 + trained.memory_w)
    trained.v[0] += 1
    trained.rate_kc[:] = 2
    recipient, donor = {"necessity": (trained, matched), "sufficiency": (matched, trained),
                        "sham": (trained, trained)}[branch]
    donor_digest = donor.candidate_state_digests(targets)
    snapshot = donor.candidate_memory(targets)
    before = recipient.candidate_state_digests(targets)
    recipient.replace_candidate_memory(snapshot)
    after = recipient.candidate_state_digests(targets)
    assert after["noncandidate_state_sha256"] == before["noncandidate_state_sha256"]
    assert after["candidate_memory_sha256"] == donor_digest["candidate_memory_sha256"]
    assert (after["candidate_memory_sha256"] == before["candidate_memory_sha256"]) == (branch == "sham")
    path = tmp_path / "digests.npz"
    recipient.checkpoint(path)
    recipient.v[1] += 2
    recipient.restore(path)
    assert recipient.candidate_state_digests(targets) == after


@pytest.mark.parametrize("targets", [None, [], [2], np.array([], dtype=int),
    np.array([True]), np.array([2.]), np.array([2, 2]), np.array([-1]),
    np.array([4]), np.array([0]), np.ma.array([2], mask=[False])])
def test_candidate_state_digests_reject_targets(intervention_brains, targets):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(targets)
    assert state_bytes(brain) == before


def test_candidate_state_digests_target_order_and_edge_free_target(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    first = brain.candidate_state_digests(np.array([2, 3], dtype=np.int32))
    assert all(first[key] != brain.candidate_state_digests(np.array([3, 2]))[key] for key in first)
    with_free = brain.candidate_state_digests(np.array([2, 0]))
    assert all(with_free[key] != brain.candidate_state_digests(np.array([2]))[key] for key in first)
    for dtype in ("i1", "u2", ">i4", ">u8"):
        assert brain.candidate_state_digests(np.array([2, 3], dtype=dtype)) == first


@pytest.mark.parametrize("field,value", [("memory_u", np.nan), ("memory_w", np.inf),
    ("weight", np.nan), ("memory_u", 2.), ("memory_w", -2.), ("weight", .1)])
def test_candidate_state_digests_reject_invalid_excluded(intervention_brains, field, value):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    getattr(brain, field)[0] = value
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2, 3]))
    assert state_bytes(brain) == before


def test_candidate_state_digests_readonly_and_signed_zero(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    targets = np.array([2, 3])
    first = brain.candidate_state_digests(targets)
    brain.memory_u[0] = -0.
    changed = brain.candidate_state_digests(targets)
    assert changed["candidate_memory_sha256"] != first["candidate_memory_sha256"]
    assert changed["noncandidate_state_sha256"] == first["noncandidate_state_sha256"]
    targets.flags.writeable = False
    for name in ["weight", *brain.fields]:
        getattr(brain, name).flags.writeable = False
    before = state_bytes(brain)
    assert brain.candidate_state_digests(targets, chunk_bytes=9) == changed
    assert state_bytes(brain) == before


@pytest.mark.parametrize("change", ["unlocked", "model", "duplicate", "missing", "extra",
    "shape", "dtype", "masked", "cursor", "spikes", "frozen", "sim_ms", "active",
    "queue", "trace"])
def test_candidate_state_digests_reject_invalid_live(intervention_brains, change):
    brain, _ = intervention_brains
    if change != "unlocked":
        brain.lock_model_provenance()
    if change == "model": brain.eta += .1
    elif change == "duplicate": brain.fields.append(brain.fields[0])
    elif change == "missing": brain.fields.remove(brain.fields[0])
    elif change == "extra": brain.fields.append("unexpected"); brain.unexpected = np.zeros(1)
    elif change == "shape": brain.memory_u = np.zeros((1, 2), dtype=np.float32)
    elif change == "dtype": brain.memory_u = brain.memory_u.astype(np.float32)
    elif change == "masked": brain.memory_u = np.ma.array(brain.memory_u)
    elif change == "cursor": brain.cursor = True
    elif change == "spikes": brain.total_spikes = -1
    elif change == "frozen": brain.weights_frozen = 1
    elif change == "sim_ms": brain.sim_ms = .1
    elif change == "active": brain.active_flag[0] = 0
    elif change == "queue": brain.queue_count[-1] = 1
    elif change == "trace": brain.eligibility_last[0] = 1
    before = state_bytes(brain)
    with pytest.raises(RuntimeError if change in ("unlocked", "model") else ValueError):
        brain.candidate_state_digests(np.array([2, 3]))
    assert state_bytes(brain) == before


@pytest.mark.parametrize("field", ["v", "g", "drive", "previous_drive", "refractory",
    "queue", "queue_count", "counts", "luminance", "active", "active_flag", "nactive",
    "last", "eligibility", "eligibility_last", "modulation", "modulation_last", "adaptation",
    "rate_kc", "rate_dan", "memory_u", "memory_w", "weight", "r8_light"])
def test_candidate_state_digests_untouched_field_sensitivity(intervention_brains, field):
    brain, _ = intervention_brains
    # Register the same visual storage used by VisualMemoryBrain, without anatomy mocks.
    brain.r8_light = np.zeros(2, dtype=np.float32)
    brain.fields.append("r8_light")
    brain.initial["r8_light"] = brain.r8_light.copy()
    brain.cursor = 20
    brain.sim_ms = 20 * brain.dt
    brain.lock_model_provenance()
    targets = np.array([2])
    before = brain.candidate_state_digests(targets)
    if field == "active": brain.active[-1] = 3  # Inactive backing remains in state.
    elif field == "queue": brain.queue[0, -1] = 3  # Inactive queue backing.
    elif field == "queue_count": brain.queue_count[1] = 1
    elif field == "active_flag": brain.active_flag[0] = 0  # Invalid membership rejects.
    elif field == "nactive": brain.nactive[0] = 0
    elif field in ("memory_u", "memory_w"): getattr(brain, field)[0] += .125
    elif field == "weight": brain.weight[2] += .125
    elif field == "last": brain.last[0] = 0
    else: getattr(brain, field).flat[0] += 1
    invalid = field in ("active_flag", "nactive")
    actual = state_bytes(brain)
    if invalid:
        with pytest.raises(ValueError): brain.candidate_state_digests(targets)
    else:
        after = brain.candidate_state_digests(targets)
        assert after["candidate_memory_sha256"] == before["candidate_memory_sha256"]
        assert after["noncandidate_state_sha256"] != before["noncandidate_state_sha256"]
    assert state_bytes(brain) == actual


@pytest.mark.parametrize("field", ["cursor", "total_spikes", "weights_frozen"])
def test_candidate_state_digests_mutable_metadata(intervention_brains, field):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    before = brain.candidate_state_digests(np.array([2]))
    setattr(brain, field, True if field == "weights_frozen" else 1)
    if field == "cursor": brain.sim_ms = brain.cursor * brain.dt
    after = brain.candidate_state_digests(np.array([2]))
    assert after["candidate_memory_sha256"] == before["candidate_memory_sha256"]
    assert after["noncandidate_state_sha256"] != before["noncandidate_state_sha256"]


@pytest.mark.parametrize("field,value", [("cursor", -1), ("cursor", 1.5), ("cursor", 2**63),
    ("cursor", 2**63 - 1), ("total_spikes", True), ("total_spikes", 2**63),
    ("sim_ms", np.nan), ("sim_ms", np.inf), ("sim_ms", True)])
def test_candidate_state_digests_invalid_scalars(intervention_brains, field, value):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    setattr(brain, field, value)
    if field == "cursor": brain.sim_ms = value * brain.dt
    before = state_bytes(brain)
    with pytest.raises(ValueError): brain.candidate_state_digests(np.array([2]))
    # NaN does not compare equal to itself; use unchanged scalar object identity.
    if field == "sim_ms" and np.isnan(value):
        assert brain.sim_ms is value
        before.pop("sim_ms")
        after = state_bytes(brain)
        after.pop("sim_ms")
        assert after == before
    else: assert state_bytes(brain) == before


@pytest.mark.parametrize("field,value", [("target_indices", np.array([], dtype=int)),
    ("target_indices", np.array([2, 2])), ("target_indices", np.array([-1])),
    ("target_indices", np.array([2.0])), ("candidate_positions", np.array([1, 0])),
    ("candidate_positions", np.array([0, 0])), ("candidate_positions", np.array([0, 2])),
    ("candidate_positions", np.array([0])), ("edge_indices", np.array([1, 1])),
    ("edge_indices", np.array([-1, 1])), ("edge_indices", np.array([4, 5])),
    ("edge_indices", np.array([4])), ("edge_indices", np.array([True, False]))])
def test_candidate_state_digests_codec_rejects_invalid_maps(field, value):
    with pytest.raises(ValueError): digest_codec(**{field: value})


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("field", ["memory_u", "memory_w", "weight"])
def test_candidate_state_digests_codec_rejects_excluded_nonfinite(field, value):
    arrays = {"memory_u": np.zeros(2), "memory_w": np.zeros(2), "weight": np.ones(5)}
    arrays[field][0 if field != "weight" else 4] = value
    with pytest.raises(ValueError): digest_codec(arrays=arrays, chunk_bytes=9)


def test_candidate_state_digests_codec_schema_layout_and_index_normalization():
    arrays = {"memory_u": np.zeros(2), "memory_w": np.zeros(2), "weight": np.ones(5),
              "ordinary": np.arange(12, dtype=np.int32).reshape(3, 4),
              "empty": np.zeros((0, 2), dtype=np.float32)}
    first = digest_codec(arrays=arrays)
    for ordinary in (np.asfortranarray(arrays["ordinary"]),
        arrays["ordinary"].astype(">i4"), np.repeat(arrays["ordinary"], 2, axis=1)[:, ::2]):
        assert digest_codec(arrays={**arrays, "ordinary": ordinary},
            target_indices=np.array([2, 3], dtype=">u2"),
            candidate_positions=np.array([0, 1], dtype="i1"),
            edge_indices=np.array([4, 1], dtype=">u8"), chunk_bytes=9) == first
    for changed in ({**arrays, "ordinary": arrays["ordinary"].reshape(12)},
                    {**arrays, "ordinary": arrays["ordinary"].astype(np.int64)},
                    {**arrays, "renamed": arrays["ordinary"]},
                    {**arrays, "empty": np.zeros((2, 0), dtype=np.float32)}):
        result = digest_codec(arrays=changed)
        assert result["candidate_memory_sha256"] == first["candidate_memory_sha256"]
        assert result["noncandidate_state_sha256"] != first["noncandidate_state_sha256"]
    for name in ("memory_u", "memory_w", "weight"):
        changed = {**arrays, name: arrays[name].astype(np.float32)}
        result = digest_codec(arrays=changed)
        assert all(result[key] != first[key] for key in first)
    changed = {**arrays, "weight": arrays["weight"].copy()}
    changed["weight"][0] = -0.
    negative = digest_codec(arrays=changed)
    changed["weight"][0] = 0.
    positive = digest_codec(arrays=changed)
    assert negative["candidate_memory_sha256"] == positive["candidate_memory_sha256"]
    assert negative["noncandidate_state_sha256"] != positive["noncandidate_state_sha256"]


@pytest.mark.parametrize("chunk_bytes", [True, 0, 7, 8., np.int64(8), None])
def test_candidate_state_digests_invalid_chunk_bytes(intervention_brains, chunk_bytes):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    with pytest.raises(ValueError): brain.candidate_state_digests(np.array([2]), chunk_bytes=chunk_bytes)
    with pytest.raises(ValueError): digest_codec(chunk_bytes=chunk_bytes)


def test_candidate_state_digests_hashes_accepted_weight_rounding(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    first = brain.candidate_state_digests(np.array([2]))
    brain.weight[0] = np.nextafter(brain.weight[0], np.float32(np.inf))
    after = brain.candidate_state_digests(np.array([2]))
    assert after["candidate_memory_sha256"] != first["candidate_memory_sha256"]
    assert after["noncandidate_state_sha256"] == first["noncandidate_state_sha256"]


@pytest.mark.parametrize("change", ["metadata_extra", "metadata_missing", "provenance",
    "array_extra", "array_missing", "lock_during_hash"])
def test_candidate_state_digests_validates_payload_and_rechecks_lock(intervention_brains, change, monkeypatch):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    payload = brain._checkpoint_payload
    def altered_payload():
        metadata, arrays = payload()
        if change == "metadata_extra": metadata["unknown"] = 1
        elif change == "metadata_missing": del metadata["total_spikes"]
        elif change == "provenance": metadata["eta"] += .1
        elif change == "array_extra": arrays["unknown"] = np.zeros(1)
        elif change == "array_missing": del arrays["v"]
        return metadata, arrays
    monkeypatch.setattr(brain, "_checkpoint_payload", altered_payload)
    if change == "lock_during_hash":
        original = checkpoint._candidate_state_digests
        def change_lock(*args, **kwargs):
            result = original(*args, **kwargs)
            brain.eta += .1
            return result
        monkeypatch.setattr("fly_connectome_sim.neural.brain._candidate_state_digests", change_lock)
    before = state_bytes(brain)
    with pytest.raises(RuntimeError if change == "lock_during_hash" else ValueError):
        brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


@pytest.mark.parametrize("edges", [np.array([], dtype=np.int64), np.array([0, 0]),
    np.array([-1, 0]), np.array([0, 3]), np.array([0., 1.]), np.array([[1, 0]]),
    np.ma.array([1, 0], mask=[False, False]), np.array([0])])
def test_candidate_state_digests_reject_invalid_live_circuit(intervention_brains, edges):
    brain, _ = intervention_brains
    brain.circuit["edges"] = edges
    brain.lock_model_provenance()
    before = state_bytes(brain)
    with pytest.raises(ValueError): brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


@pytest.mark.parametrize("chunk_bytes", [8, 9, 17, 64])
def test_candidate_state_digests_sparse_streaming_buffers(chunk_bytes, monkeypatch):
    # Guard encoder storage, not the separately documented map/native allocations.
    class GuardedArray(np.ndarray):
        def __getitem__(self, key):
            if isinstance(key, np.ndarray):
                assert key.dtype.kind in "iu", "Complement boolean mask"
                assert key.size * self.dtype.itemsize <= chunk_bytes, "Unbounded gather"
            return super().__getitem__(key)
        def copy(self, *args, **kwargs):
            assert self.nbytes <= chunk_bytes, "Whole-array copy"
            return super().copy(*args, **kwargs)
        def tobytes(self, *args, **kwargs):
            assert self.nbytes <= chunk_bytes, "Whole-array bytes"
            return super().tobytes(*args, **kwargs)
        def astype(self, *args, **kwargs):
            assert self.nbytes <= chunk_bytes, "Whole-array dtype conversion"
            return super().astype(*args, **kwargs)
        def byteswap(self, *args, **kwargs):
            assert self.nbytes <= chunk_bytes, "Whole-array byteswap"
            return super().byteswap(*args, **kwargs)
    arrays = {"memory_u": np.arange(12, dtype=">f8") / 100,
              "memory_w": np.zeros(12, dtype=np.float32),
              "weight": np.arange(50006, dtype=">f8")[::2],
              "ordinary": np.arange(200, dtype=">i4").reshape(20, 10).T}
    maps = {"candidate_positions": np.array([1, 5, 9]),
            "edge_indices": np.array([25002, 3, 12345]), "target_indices": np.array([2, 3])}
    expected = digest_codec(arrays=arrays, **maps)
    guarded = {name: value.view(GuardedArray) for name, value in arrays.items()}
    original_chunks = checkpoint._array_chunks
    original_finite = np.isfinite
    original_contiguous = np.ascontiguousarray
    original_sha = checkpoint.sha256
    updates = []
    def checked_chunks(value, size, **kwargs):
        for chunk in original_chunks(value, size, **kwargs):
            assert chunk.nbytes <= size, "Unbounded numeric buffer"
            yield chunk
    def checked_finite(value, *args, **kwargs):
        assert value.nbytes <= chunk_bytes, "Unbounded finite scan"
        return original_finite(value, *args, **kwargs)
    def checked_contiguous(value, *args, **kwargs):
        assert value.nbytes <= chunk_bytes, "Unbounded contiguous conversion"
        return original_contiguous(value, *args, **kwargs)
    class CheckedHash:
        def __init__(self): self.inner = original_sha()
        def update(self, value):
            assert len(value) <= chunk_bytes, "Unbounded SHA update"
            updates.append(len(value))
            self.inner.update(value)
        def hexdigest(self): return self.inner.hexdigest()
    def no_concatenate(*args, **kwargs): raise AssertionError("Encoder concatenation")
    monkeypatch.setattr(checkpoint, "_array_chunks", checked_chunks)
    monkeypatch.setattr(checkpoint.np, "isfinite", checked_finite)
    monkeypatch.setattr(checkpoint.np, "ascontiguousarray", checked_contiguous)
    monkeypatch.setattr(checkpoint.np, "concatenate", no_concatenate)
    monkeypatch.setattr(checkpoint, "sha256", CheckedHash)
    assert digest_codec(arrays=guarded, **maps, chunk_bytes=chunk_bytes) == expected
    assert max(updates) <= chunk_bytes


@pytest.mark.parametrize("dtype", ["?", "f2", "c8", "O", "U1", [("x", "i4")]])
def test_candidate_state_digests_codec_rejects_unsupported_state(dtype):
    arrays = {"memory_u": np.zeros(2), "memory_w": np.zeros(2), "weight": np.ones(5),
              "ordinary": np.zeros(2, dtype=dtype)}
    with pytest.raises(ValueError): digest_codec(arrays=arrays)


@pytest.mark.parametrize("change", ["weight_rank", "missing_memory", "masked", "bad_name",
    "metadata_object", "metadata_nan", "metadata_key"])
def test_candidate_state_digests_codec_invalid_schema_and_json(change):
    arrays = {"memory_u": np.zeros(2), "memory_w": np.zeros(2), "weight": np.ones(5)}
    metadata = {"cursor": 0, "dt": .1, "total_spikes": 0, "weights_frozen": False}
    if change == "weight_rank": arrays["weight"] = arrays["weight"].reshape(1, 5)
    elif change == "missing_memory": del arrays["memory_u"]
    elif change == "masked": arrays["memory_u"] = np.ma.array(arrays["memory_u"])
    elif change == "bad_name": arrays[1] = np.zeros(1)
    elif change == "metadata_object": metadata["bad"] = np.int64(1)
    elif change == "metadata_nan": metadata["bad"] = np.nan
    elif change == "metadata_key": metadata[1] = 1
    with pytest.raises(ValueError): digest_codec(metadata=metadata, arrays=arrays)


def test_candidate_state_digests_codec_uint64_indices_and_scalar_schema():
    max_target = np.array([2**64 - 1], dtype=np.uint64)
    first = digest_codec(target_indices=max_target)
    assert first != digest_codec(target_indices=np.array([2**63 - 1], dtype=np.int64))
    arrays = {"memory_u": np.zeros(2), "memory_w": np.zeros(2), "weight": np.ones(5),
              "ordinary": np.array(1, dtype=np.int32)}
    scalar = digest_codec(arrays=arrays)
    vector = digest_codec(arrays={**arrays, "ordinary": arrays["ordinary"].reshape(1)})
    assert scalar["candidate_memory_sha256"] == vector["candidate_memory_sha256"]
    assert scalar["noncandidate_state_sha256"] != vector["noncandidate_state_sha256"]


def test_candidate_state_digests_live_rejects_subclass_and_uint64_out_of_range(intervention_brains):
    class ArraySubclass(np.ndarray): pass
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    for targets in (np.array([2]).view(ArraySubclass), np.array([2**64 - 1], dtype=np.uint64)):
        with pytest.raises(ValueError): brain.candidate_state_digests(targets)
    brain.memory_u = brain.memory_u.view(ArraySubclass)
    with pytest.raises(ValueError): brain.candidate_state_digests(np.array([2]))


def test_candidate_state_digests_payload_cannot_substitute_actual_state(intervention_brains, monkeypatch):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    brain.memory_u[0] = np.nan
    payload = brain._checkpoint_payload
    def sanitized():
        metadata, arrays = payload()
        arrays["memory_u"] = np.zeros_like(brain.memory_u)
        return metadata, arrays
    monkeypatch.setattr(brain, "_checkpoint_payload", sanitized)
    with pytest.raises(ValueError): brain.candidate_state_digests(np.array([2, 3]))


def test_candidate_state_digests_strided_uint64_maps(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    targets = np.array([2, 99, 3, 99], dtype=np.uint64)[::2]
    assert brain.candidate_state_digests(targets) == brain.candidate_state_digests(np.array([2, 3]))
    assert digest_codec(target_indices=targets,
        candidate_positions=np.array([0, 99, 1, 99], dtype=np.uint64)[::2],
        edge_indices=np.array([4, 99, 1, 99], dtype=np.uint64)[::2], chunk_bytes=64) == digest_codec()


@pytest.fixture
def digest_visual_brain(intervention_brains, tmp_path, monkeypatch):
    # Only anatomical lookup/projection is replaced; construction/state/native API
    # remain the real VisualMemoryBrain on the existing four-neuron graph.
    import pandas as pd
    from fly_connectome_sim.neural import visual

    source, _ = intervention_brains
    monkeypatch.setattr(visual, "annotations", lambda ids: pd.DataFrame({
        "type": ["R8p", "DAN", "MBON", "MBON"],
    }))
    monkeypatch.setattr(visual, "projection", lambda brain, annotations: (
        np.array([0], dtype=np.int32), np.array([[.5, .5]], dtype=np.float32),
        np.array([1.], dtype=np.float32),
    ))
    return VisualMemoryBrain(path=tmp_path / "intervention-graph.npz",
        circuit=source.circuit, modulation_mask=source.modulation_mask)


@pytest.mark.parametrize("before_lock", [True, False])
@pytest.mark.parametrize("field", ["rate_kc", "eligibility_last"])
def test_candidate_state_digests_required_registration_removal(intervention_brains, field, before_lock):
    brain, _ = intervention_brains
    if not before_lock:
        brain.lock_model_provenance()
    brain.fields.remove(field)
    del brain.initial[field]
    if before_lock:
        brain.lock_model_provenance()
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


@pytest.mark.parametrize("before_lock", [True, False])
def test_candidate_state_digests_visual_registration_removal(digest_visual_brain, before_lock):
    brain = digest_visual_brain
    if not before_lock:
        brain.lock_model_provenance()
    brain.fields.remove("r8_light")
    del brain.initial["r8_light"]
    if before_lock:
        brain.lock_model_provenance()
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


@pytest.mark.parametrize("before_lock", [True, False])
@pytest.mark.parametrize("change", ["dtype", "shape"])
def test_candidate_state_digests_coordinated_native_schema_mutation(intervention_brains, change, before_lock):
    brain, _ = intervention_brains
    if not before_lock:
        brain.lock_model_provenance()
    brain.rate_kc = (brain.rate_kc.astype(np.float32) if change == "dtype"
                     else np.zeros(1, dtype=np.float64))
    brain.initial["rate_kc"] = brain.rate_kc.copy()
    if before_lock:
        brain.lock_model_provenance()
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


@pytest.mark.parametrize("change", ["remove", "shape", "dtype"])
def test_candidate_state_digests_registered_extension_integrity(intervention_brains, change):
    brain, _ = intervention_brains
    brain.extra_state = np.zeros(2, dtype=np.float32)
    brain.fields.append("extra_state")
    brain.initial["extra_state"] = brain.extra_state.copy()
    brain.lock_model_provenance()
    first = brain.candidate_state_digests(np.array([2]))
    brain.extra_state[0] += 1
    after = brain.candidate_state_digests(np.array([2]))
    assert first["candidate_memory_sha256"] == after["candidate_memory_sha256"]
    assert first["noncandidate_state_sha256"] != after["noncandidate_state_sha256"]
    if change == "remove":
        brain.fields.remove("extra_state")
        del brain.initial["extra_state"]
    else:
        brain.extra_state = (np.zeros(1, dtype=np.float32) if change == "shape"
                             else brain.extra_state.astype(np.float64))
        brain.initial["extra_state"] = brain.extra_state.copy()
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2]))


@pytest.mark.parametrize("cursor", [0, 20])
def test_candidate_state_digests_rejects_prelock_unsupported_dt(intervention_brains, cursor):
    brain, peer = intervention_brains
    brain.dt = .2
    assert brain.model_provenance() == peer.model_provenance()
    brain.lock_model_provenance()
    brain.cursor = cursor
    brain.sim_ms = cursor * brain.dt
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


def test_candidate_state_digests_rejects_postlock_dt_divergence(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    brain.dt = .2
    with pytest.raises(RuntimeError):
        brain.candidate_state_digests(np.array([2]))


@pytest.mark.parametrize("before_lock", [True, False])
@pytest.mark.parametrize("population", [5, 3, 0, -1, True, 4.0, np.int64(4)])
def test_candidate_state_digests_authenticates_population(intervention_brains, population, before_lock):
    brain, _ = intervention_brains
    if not before_lock:
        brain.lock_model_provenance()
    brain.n = population
    if before_lock:
        brain.lock_model_provenance()
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


def test_candidate_state_digests_rejects_invented_edge_free_target(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    brain.n = 5
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2, 4]))


def test_candidate_state_digests_selected_rate_kc_sensitivity(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    targets = np.array([2])  # Circuit [1, 0] selects memory/rate position 1.
    before = brain.candidate_state_digests(targets)
    brain.rate_kc[1] += 1
    after = brain.candidate_state_digests(targets)
    assert after["candidate_memory_sha256"] == before["candidate_memory_sha256"]
    assert after["noncandidate_state_sha256"] != before["noncandidate_state_sha256"]


@pytest.mark.parametrize("before_lock", [True, False])
@pytest.mark.parametrize("change", ["dtype", "shape"])
def test_candidate_state_digests_coordinated_visual_schema_mutation(digest_visual_brain, change, before_lock):
    brain = digest_visual_brain
    if not before_lock:
        brain.lock_model_provenance()
    brain.r8_light = (brain.r8_light.astype(np.float64) if change == "dtype"
                      else np.zeros(2, dtype=np.float32))
    brain.initial["r8_light"] = brain.r8_light.copy()
    if before_lock:
        brain.lock_model_provenance()
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.candidate_state_digests(np.array([2]))
    assert state_bytes(brain) == before


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


@pytest.mark.parametrize("evolved", [False, True])
def test_complete_state_hash_matches_validated_archives_without_writes(
    brain, tmp_path, evolved,
):
    if evolved:
        brain.step(np.ones(1, dtype=np.float32), 10.0, learning=True)
    before = state_bytes(brain)
    files = set(tmp_path.iterdir())
    live = brain.checkpoint_state_sha256()
    assert state_bytes(brain) == before
    assert set(tmp_path.iterdir()) == files
    metadata, arrays = brain._checkpoint_payload()
    assert set(arrays) == {"weight", *brain.fields}
    assert arrays["weight"] is brain.weight
    paths = [tmp_path / "compressed.npz", tmp_path / "plain.npz"]
    brain.checkpoint(paths[0])
    np.savez(paths[1], **dict(reversed(list(arrays.items()))), metadata=json.dumps(
        dict(reversed(list(metadata.items()))), indent=2, ensure_ascii=False,
    ))
    assert hashlib.sha256(paths[0].read_bytes()).digest() != (
        hashlib.sha256(paths[1].read_bytes()).digest()
    )
    for path in paths:
        loaded = checkpoint.load_checkpoint(path, brain.model_provenance(), arrays, brain.n)
        assert checkpoint.checkpoint_state_sha256(*loaded) == live
    assert state_bytes(brain) == before


def test_complete_hash_covers_every_array_and_mutable_scalar(brain):
    brain.r8_light = np.zeros(1, dtype=np.float32)
    brain.fields.append("r8_light")
    brain.initial["r8_light"] = brain.r8_light.copy()
    metadata, arrays = brain._checkpoint_payload()
    original = checkpoint.checkpoint_state_sha256(metadata, arrays)
    for name, value in arrays.items():
        changed = {**arrays, name: value.copy()}
        changed[name].flat[-1] += 1  # Includes inactive active/queue backing slots.
        assert checkpoint.checkpoint_state_sha256(metadata, changed) != original, name
    for name, value in [("cursor", 1), ("total_spikes", 1), ("weights_frozen", True)]:
        assert checkpoint.checkpoint_state_sha256({**metadata, name: value}, arrays) != original
    first = brain.checkpoint_state_sha256()
    brain.r8_light[0] = 0.5
    assert brain.checkpoint_state_sha256() != first


def test_visual_checkpoint_and_hash_share_all_borrowed_fields(brain, tmp_path):
    brain.r8_light = np.array([0.25, 0.75], dtype=np.float32)
    brain.fields.append("r8_light")
    brain.initial["r8_light"] = np.zeros(2, dtype=np.float32)
    metadata, arrays = brain._checkpoint_payload()
    assert all(value is getattr(brain, name) for name, value in arrays.items())
    path = tmp_path / "visual.npz"
    before = state_bytes(brain)
    brain.checkpoint(path)
    loaded_metadata, loaded_arrays = checkpoint.load_checkpoint(
        path, brain.model_provenance(), arrays, brain.n,
    )
    assert set(loaded_arrays) == set(arrays) == {"weight", *brain.fields}
    assert loaded_metadata == metadata
    np.testing.assert_array_equal(loaded_arrays["r8_light"], [0.25, 0.75])
    assert checkpoint.checkpoint_state_sha256(loaded_metadata, loaded_arrays) == (
        brain.checkpoint_state_sha256()
    )
    assert state_bytes(brain) == before


def test_canonical_hash_binds_headers_and_preserves_bits():
    encode = checkpoint.checkpoint_state_sha256
    value = np.arange(12, dtype="<i4").reshape(3, 4)
    original = encode({"unicode": "ä", "nested": {"b": 2, "a": 1}}, {"x": value})
    equivalent = [value.astype(">i4"), np.asfortranarray(value), value[:, ::-1][:, ::-1]]
    # A genuine strided view with the same logical values.
    storage = np.empty((3, 8), dtype="<i4")
    storage[:, ::2] = value
    equivalent.append(storage[:, ::2])
    for other in equivalent:
        assert encode({"nested": {"a": 1, "b": 2}, "unicode": "ä"}, {"x": other}) == original
    for arrays in [{"y": value}, {"x": value.reshape(4, 3)}, {"x": value.astype("i8")}]:
        assert encode({"unicode": "ä", "nested": {"b": 2, "a": 1}}, arrays) != original
    assert encode({}, {"x": np.array([0.0], dtype="f4")}) != (
        encode({}, {"x": np.array([-0.0], dtype="f4")})
    )


@pytest.mark.parametrize("dtype", ["i1", "u1", "i2", "u2", "i4", "u4", "i8", "u8", "f4", "f8"])
def test_complete_hash_supports_exact_numeric_widths_and_scalar_rank(dtype):
    value = np.array(1, dtype=dtype)
    scalar = checkpoint.checkpoint_state_sha256({}, {"x": value}, chunk_bytes=8)
    assert scalar == checkpoint.checkpoint_state_sha256({}, {"x": value.astype(
        value.dtype.newbyteorder(">"),
    )}, chunk_bytes=8)
    assert scalar != checkpoint.checkpoint_state_sha256({}, {"x": value.reshape(1)})


def test_complete_hash_known_independent_encoding_vector():
    # Normative v1 framing derived directly from the contract, not encoder helpers.
    metadata = b'{"a":"\xc3\xa4","b":1}'
    header = (b'{"byteorder":"little","itemsize":2,"kind":"i","name":"x",'
              b'"nbytes":4,"rank":1,"shape":[2]}')
    expected_bytes = (
        b"fly-connectome-checkpoint-state/v1\0"
        + b"M" + struct.pack("<Q", len(metadata)) + metadata
        + struct.pack("<Q", 1)
        + b"A" + struct.pack("<Q", len(header)) + header
        + struct.pack("<Q", 4) + b"\x01\x00\xfe\xff"
    )
    assert checkpoint.checkpoint_state_sha256(
        {"b": 1, "a": "ä"}, {"x": np.array([1, -2], dtype="i2")}, chunk_bytes=8,
    ) == hashlib.sha256(expected_bytes).hexdigest()


@pytest.mark.parametrize("layout", ["C", "strided", "big-endian"])
def test_bounded_legacy_digest_preserves_existing_raw_byte_identity(layout, monkeypatch):
    value = np.arange(6000, dtype="i4").reshape(100, 60)
    if layout == "strided":
        value = value[:, ::3]
    elif layout == "big-endian":
        value = value.astype(">i4")
    expected = hashlib.sha256(value.tobytes()).hexdigest()
    updates = []

    class ObservedHash:
        def __init__(self):
            self.real = hashlib.sha256()

        def update(self, data):
            updates.append(len(data))
            self.real.update(data)

        def hexdigest(self):
            return self.real.hexdigest()

    monkeypatch.setattr(checkpoint, "sha256", ObservedHash)
    assert checkpoint.raw_array_sha256(value, chunk_bytes=64) == expected
    assert len(updates) > 100
    assert max(updates) <= 64


def test_complete_hash_record_boundaries_and_empty_arrays():
    encode = checkpoint.checkpoint_state_sha256
    cases = [
        ({"a": "bc"}, {}), ({"ab": "c"}, {}), ({}, {}),
        ({}, {"a": np.empty((0,), dtype="u1")}),
        ({}, {"a": np.empty((0, 2), dtype="u1")}),
        ({}, {"ab": np.array([99], dtype="u1")}),
        ({}, {"a": np.array([98, 99], dtype="u1")}),
        ({}, {"a": np.empty(0, dtype="u1"), "b": np.empty(0, dtype="u1")}),
    ]
    assert len({encode(metadata, arrays) for metadata, arrays in cases}) == len(cases)


@pytest.mark.parametrize("dtype", ["O", "U1", "S1", "c8", "f2", "bool", "M8[ns]", [("x", "i4")]])
def test_complete_hash_rejects_unsupported_array_encodings(dtype):
    with pytest.raises(ValueError):
        checkpoint.checkpoint_state_sha256({}, {"x": np.zeros(2, dtype=dtype)})


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_complete_hash_rejects_nonfinite_arrays(value):
    with pytest.raises(ValueError, match="Nonfinite"):
        checkpoint.checkpoint_state_sha256({}, {"x": np.array([1.0, value])}, chunk_bytes=8)


@pytest.mark.parametrize("metadata", [
    {1: "key"}, {"x": {1: "key"}}, {"x": np.int64(1)}, {"x": (1, 2)},
    {"x": np.nan}, {"x": np.inf}, {"x": "\ud800"}, [],
])
def test_complete_hash_requires_strict_json_without_scalar_coercion(metadata):
    with pytest.raises(ValueError):
        checkpoint.checkpoint_state_sha256(metadata, {})


def test_complete_hash_rejects_cyclic_metadata_as_value_error():
    metadata = {}
    metadata["cycle"] = metadata
    with pytest.raises(ValueError):
        checkpoint.checkpoint_state_sha256(metadata, {})


@pytest.mark.parametrize("chunk_bytes", [0, -1, 1.5, True, "64", None, 7, 2**100])
def test_complete_hash_rejects_invalid_chunk_sizes(chunk_bytes):
    with pytest.raises(ValueError):
        checkpoint.checkpoint_state_sha256({}, {}, chunk_bytes=chunk_bytes)


def test_complete_hash_emits_bounded_chunks_with_layout_and_endian_conversion(monkeypatch):
    original_sha256 = checkpoint.sha256
    emitted = []
    finite_sizes = []
    original_isfinite = checkpoint.np.isfinite

    class ObservedHash:
        def __init__(self):
            self.real = original_sha256()

        def update(self, data):
            emitted.append(len(data))
            self.real.update(data)

        def hexdigest(self):
            return self.real.hexdigest()

    def observed_isfinite(value):
        finite_sizes.append(value.nbytes)
        return original_isfinite(value)

    value = np.arange(6000, dtype=">f8").reshape(100, 60)[:, ::3]
    expected = checkpoint.checkpoint_state_sha256({"x": "metadata" * 50}, {"strided": value})
    monkeypatch.setattr(checkpoint, "sha256", ObservedHash)
    monkeypatch.setattr(checkpoint.np, "isfinite", observed_isfinite)
    actual = checkpoint.checkpoint_state_sha256(
        {"x": "metadata" * 50}, {"strided": value}, chunk_bytes=64,
    )
    assert actual == expected
    assert len(emitted) > 100
    assert max(emitted) <= 64
    assert len(finite_sizes) > 100
    assert max(finite_sizes) <= 64


def test_complete_hash_does_not_request_full_array_bytes_or_conversion(monkeypatch):
    class GuardedArray(np.ndarray):
        def tobytes(self, *args, **kwargs):
            assert self.nbytes <= 64, "Full array bytes allocation"
            return super().tobytes(*args, **kwargs)

        def copy(self, *args, **kwargs):
            assert self.nbytes <= 64, "Full array copy"
            return super().copy(*args, **kwargs)

        def astype(self, *args, **kwargs):
            assert self.nbytes <= 64, "Full dtype conversion"
            return super().astype(*args, **kwargs)

        def byteswap(self, *args, **kwargs):
            assert self.nbytes <= 64, "Full endian conversion"
            return super().byteswap(*args, **kwargs)

    original_contiguous = np.ascontiguousarray

    def guarded_contiguous(value, *args, **kwargs):
        assert value.nbytes <= 64, "Full contiguous conversion"
        return original_contiguous(value, *args, **kwargs)

    value = np.arange(6000, dtype=">f8").reshape(100, 60)[:, ::3]
    expected = checkpoint.checkpoint_state_sha256({}, {"x": value}, chunk_bytes=64)
    guarded = value.view(GuardedArray)
    monkeypatch.setattr(checkpoint.np, "ascontiguousarray", guarded_contiguous)
    assert checkpoint.checkpoint_state_sha256({}, {"x": guarded}, chunk_bytes=64) == expected


@pytest.mark.parametrize(("field", "value"), [
    ("cursor", True), ("cursor", -1), ("cursor", 1.5),
    ("cursor", 2**63), ("cursor", 2**63 - 1),
    ("sim_ms", 0.1), ("sim_ms", np.inf),
    ("total_spikes", False), ("total_spikes", -1), ("total_spikes", 2**63),
    ("weights_frozen", 1),
])
def test_live_hash_rejects_invalid_clock_and_scalars_without_mutation(brain, field, value):
    setattr(brain, field, value)
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.checkpoint_state_sha256()
    assert state_bytes(brain) == before


@pytest.mark.parametrize("change", ["queue", "active", "nan", "shape", "dtype"])
def test_live_hash_validates_native_and_exact_array_state_without_mutation(brain, change):
    if change == "queue":
        brain.queue_count[-1] = 1
    elif change == "active":
        brain.active_flag[0] = 0
    elif change == "nan":
        brain.weight[0] = np.nan
    elif change == "shape":
        brain.v = brain.v[:1]
    else:
        brain.v = brain.v.astype("f8")
    before = state_bytes(brain)
    with pytest.raises(ValueError):
        brain.checkpoint_state_sha256()
    assert state_bytes(brain) == before


@pytest.mark.parametrize("change", ["duplicate", "nested-duplicate", "nan", "overflow"])
def test_archive_metadata_is_strict_json_before_transactional_restore(brain, saved, change):
    path, arrays, metadata = saved
    encoded = json.dumps(metadata)
    if change == "duplicate":
        encoded = encoded[:-1] + ', "cursor":0}'
    elif change == "nested-duplicate":
        encoded = encoded.replace('"model-source/v1"', '"model-source/v1", "version":"model-source/v1"')
    else:
        encoded = encoded.replace('"eta": 0.001', '"eta": ' + ("NaN" if change == "nan" else "1e999"))
    np.savez(path, metadata=encoded, **arrays)
    assert_rejected_without_mutation(brain, path)
