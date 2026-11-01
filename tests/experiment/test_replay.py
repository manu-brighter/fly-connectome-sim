"""Bounded replay trust boundary with real native visual checkpoint state."""

from copy import deepcopy
from hashlib import sha256
import importlib
import json
import os
import struct
from pathlib import Path

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from replay_helpers import engine_factory


@pytest.fixture
def map_engine_factory(tmp_path):
    """Real native topology with distinguishable, equal-length compartment maps."""
    from fly_connectome_sim.engine import FlyEngine, NeuralGroups
    from fly_connectome_sim.neural.brain import MemoryBrain
    from fly_connectome_sim.neural.visual import VisualMemoryBrain

    graph = tmp_path / "map-graph.npz"
    np.savez(graph, ids=np.array([101, 202, 303, 404, 505, 606, 707, 808], dtype=np.int64),
             ptr=np.array([0, 2, 4, 5, 6, 6, 6, 6, 6], dtype=np.int64),
             post=np.array([4, 5, 4, 5, 4, 5], dtype=np.int32),
             weight=np.array([0.125, 0.25, 0.375, 0.5, 0.625, 0.75], dtype=np.float32),
             retina=np.array([0], dtype=np.int32), uv=np.array([[0.5, 0.5]], dtype=np.float32),
             lamina=np.array([], dtype=np.int32), sugar=np.array([], dtype=np.int32),
             superclass=np.zeros(8, dtype=np.uint8))

    class MapBrain(VisualMemoryBrain):
        def __init__(self, index_dtype):
            MemoryBrain.__init__(self, path=graph, circuit={
                "kc": np.array([0, 1], dtype=index_dtype),
                "dan": np.array([3, 2], dtype=index_dtype),
                "edges": np.array([3, 0, 2, 1], dtype=np.int64),
                "pre": np.array([1, 0, 1, 0], dtype=np.int32),
                "gain": np.array([[1, 0.125, 0.25, 0.5], [0.5, 0.25, 0.125, 1]], dtype=np.float32),
                "kc_mask": np.array([1, 1, 0, 0, 0, 0, 0, 0], dtype=np.uint8),
                "dan_index": np.array([-1, -1, 1, 0, -1, -1, -1, -1], dtype=np.int8),
            }, modulation_mask=np.array([0, 0, 1, 1, 0, 0, 0, 0], dtype=np.uint8))
            self.r8 = np.array([0], dtype=np.int32)
            self.r8_uv = np.array([[0.5, 0.5]], dtype=np.float32)
            self.r8_channel = np.array([2], dtype=np.int32)
            self.corrected_edges = np.array([], dtype=np.int64)
            self.r8_light = np.zeros(1, dtype=np.float32)
            self.fields.append("r8_light")
            self.initial["r8_light"] = self.r8_light.copy()

    def factory(*, empty=0, index_dtype=np.int32, overlap=False):
        groups = {"pam11": [3] if overlap else [2], "ppl101": [3], "kc": [0, 1],
                  "mbon07": [6] if empty == 2 else [4], "mbon11": [6 if empty == 1 else 7] if empty else [5],
                  "motor_left": [6], "motor_right": [7]}
        return FlyEngine(brain=MapBrain(index_dtype), groups=NeuralGroups(**{
            name: np.array(indices, dtype=index_dtype) for name, indices in groups.items()}))
    return factory


def map_recording(factory, tmp_path, *, run_kind="qualification", anchors=0):
    """Native map/replay artifact, never a complete scientific qualification."""
    from fly_connectome_sim.experiment.recorder import RunRecorder

    engine = factory()
    black = {"generator": "black-rgb/v1", "input_shape": [2, 3, 3], "input_dtype": "uint8",
             "input_sha256": _rgb_input_sha256(np.zeros((2, 3, 3), dtype=np.uint8))}
    metadata = {"engine_identity": engine.identity(), "protocol_version": f"{run_kind}/v1",
                "stimulus_version": "associative-stimuli/v1", "family": run_kind,
                "seeds": [11, 23] if run_kind == "qualification" else [101], "factors": {},
                "input_sha256": [black["input_sha256"]], "black_input": black}
    if run_kind == "confirmation":
        # Declared route-test contract only, not purported qualification evidence.
        metadata.update(frozen_config_sha256=sha256(b"declared route contract").hexdigest(),
                        assay_contract={"analysis_version": "mbon11-causal-analysis/v1"})
    recorder = RunRecorder(tmp_path / "map-run", run_kind=run_kind,
                           metadata=metadata, root_branch_id="training")
    source = tmp_path / "map-source.npz"
    engine.brain.checkpoint(source)
    recorder.ingest_checkpoint("brain-before.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_ms": 0.0,
                     "sim_tick": 0, "checkpoint_name": "brain-before.npz"})
    if anchors:
        engine.observe(np.full((2, 3, 3), 80, dtype=np.uint8), 0.3, learning=True)
        engine.brain.weights_frozen = True
        engine.brain.checkpoint(source)
        digest = recorder.ingest_checkpoint("source.npz", source, origin_branch_id="training")
        recorder.append({"type": "checkpoint", "branch_id": "training", "sim_ms": 0.3,
                         "sim_tick": 3, "checkpoint_name": "source.npz"})
        api = replay_module()
        for number in range(anchors):
            engine.brain.restore(recorder.path / "checkpoints" / "source.npz")
            branch = f"retained-{number}"
            recorder.append({"type": "fork", "branch_id": branch, "sim_ms": 0.3, "sim_tick": 3,
                             "operation_version": api.OPERATION_VERSION, "parent_branch_id": "training",
                             "parent_checkpoint_name": "source.npz", "parent_checkpoint_sequence": 1,
                             "parent_checkpoint_sha256": digest})
            recorder.append({"type": "replay_thaw", "branch_id": branch, "sim_ms": 0.3, "sim_tick": 3,
                             "operation_version": api.OPERATION_VERSION,
                             "before_weights_frozen": True, "after_weights_frozen": False})
            engine.brain.weights_frozen = False
            telemetry = engine.observe(np.zeros((2, 3, 3), dtype=np.uint8), 0.2,
                                       current_mv=19.5, qualification_detail=True)
            recorder.append({"type": "neutral_gap_chunk", "branch_id": branch, **black,
                             "operation_version": api.OPERATION_VERSION, "start_tick": 3, "end_tick": 5,
                             "duration_ticks": 2, "duration_ms": 0.2, "sim_ms": 0.5,
                             "stimulation": None, "learning": False, "current_mv": 19.5,
                             "pathway_detail": False, "qualification_detail": True, "telemetry": telemetry})
            prefix = recorder.validate_prefix()
            recipe = api.build_black_retention_recipe(prefix.iter_events(), source_occurrence={
                "checkpoint_name": "source.npz", "checkpoint_sha256": digest,
                "origin_branch_id": "training", "checkpoint_sequence": 1, "sim_tick": 3},
                origin_branch_id=branch, target_tick=5, engine_identity=engine.identity(),
                run_metadata_sha256=prefix.manifest["run_metadata_sha256"], black_input=black,
                scientific_prefix=prefix.scientific_prefix)
            recorder.append_state_anchor(api.build_state_anchor(anchor_id=branch, recipe=recipe,
                complete_state_sha256=engine.brain.checkpoint_state_sha256()))
    return recorder, engine


def seal_map_recording(recorder, engine, tmp_path):
    """Close a real recorder with an explicitly non-supporting terminal."""
    source = tmp_path / "map-after.npz"
    engine.brain.checkpoint(source)
    recorder.ingest_checkpoint("brain-after.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_ms": engine.brain.cursor / 10,
                     "sim_tick": engine.brain.cursor, "checkpoint_name": "brain-after.npz"})
    if recorder.run_kind == "qualification":
        prefix = recorder.validate_prefix()
        recorder.append({"type": "qualification_result", "branch_id": "training",
            "sim_ms": engine.brain.cursor / 10, "status": "unsupported", "family": "qualification",
            "seeds": recorder.metadata["seeds"], "selected_configuration": None,
            "selected_window": None, "selected_retention_ms": None, "observed_effect_sign": None,
            "benchmark": {"simulated_seconds": engine.brain.sim_ms / 1000,
                          "event_count": prefix.manifest["event_count"],
                          "checkpoint_bytes": sum(row["size"] for row in prefix.manifest["checkpoints"].values()),
                          "peak_event_buffer_bytes": 0}, "compute_seconds": 0.0})
    elif recorder.run_kind == "confirmation":
        prefix = recorder.validate_prefix()
        report = {"status": "inconclusive", "values": {}, "reasons": ["map_fixture_only"]}
        recorder.append({"type": "assay_result", "branch_id": "training",
            "sim_ms": engine.brain.cursor / 10, "result_version": "mbon11-assay-result/v1",
            "analysis_version": "mbon11-causal-analysis/v1",
            "frozen_config_sha256": recorder.metadata["frozen_config_sha256"], **report,
            "report": report, "report_sha256": sha256(canonical(report)).hexdigest(),
            "evidence_event_count": prefix.manifest["event_count"],
            "evidence_final_scientific_sha256": prefix.manifest["final_scientific_sha256"]})
    recorder.close()


@pytest.mark.parametrize("anchors", [0, 1, 2])
def test_native_qualification_context_maps_and_single_factory(map_engine_factory, tmp_path, anchors):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, producer = map_recording(map_engine_factory, tmp_path, anchors=anchors)
    before = producer.brain.checkpoint_state_sha256()
    created, restores = [], []
    def factory():
        engine = map_engine_factory()
        restore = engine.brain.restore
        def traced(path):
            restores.append(Path(path).name)
            restore(path)
        engine.brain.restore = traced
        created.append(engine)
        return engine
    ordinary = recorder.validate_prefix()
    prefix = recording.verify_replay_prefix(ordinary, engine_factory=factory)
    context = recording._verified_qualification_context(prefix)
    assert len(created) == 1 and restores == ["source.npz"] * anchors
    assert set(context) == {"context_version", "engine_identity", "n", "checkpoint_schema",
                            "candidate_maps", "dan_indices", "dan_source_ids"}
    assert context["context_version"] == "qualification-map-context/v1"
    assert context["engine_identity"] == producer.identity()
    assert context["n"] == 8
    assert context["dan_indices"] == [3, 2] and context["dan_source_ids"] == ["404", "303"]
    common = {"candidate_kc_indices": [0, 1], "candidate_kc_source_ids": ["101", "202"]}
    assert context["candidate_maps"] == {
        "mbon11": {**common, "target_indices": [5], "candidate_positions": [0, 3],
                   "candidate_edge_indices": [3, 1], "candidate_edge_pre_source_ids": ["202", "101"],
                   "candidate_edge_post_source_ids": ["606", "606"], "baseline_plastic": [0.5, 0.25]},
        "mbon07": {**common, "target_indices": [4], "candidate_positions": [1, 2],
                   "candidate_edge_indices": [0, 2], "candidate_edge_pre_source_ids": ["101", "202"],
                   "candidate_edge_post_source_ids": ["505", "505"], "baseline_plastic": [0.125, 0.375]},
    }
    arrays = {name: getattr(producer.brain, name) for name in ["weight", *producer.brain.fields]}
    assert context["checkpoint_schema"] == {name: {"dtype": value.dtype.str, "shape": list(value.shape)}
                                             for name, value in arrays.items()}
    assert context["checkpoint_schema"]["r8_light"] == {"dtype": "<f4", "shape": [1]}
    assert producer.brain.checkpoint_state_sha256() == before
    with pytest.raises(recording.RunArtifactError):
        recording._verified_qualification_context(ordinary)
    seal_map_recording(recorder, producer, tmp_path)
    assert recording._verified_qualification_context(prefix) == context  # Later prefix tail is allowed.
    created.clear()
    restores.clear()
    sealed = recording.verify_replay_run(recorder.path, engine_factory=factory)
    assert len(created) == 1 and restores == ["source.npz"] * anchors
    assert recording._verified_qualification_context(sealed) == context
    assert prefix._attestation is not sealed._attestation
    context["candidate_maps"]["mbon11"]["baseline_plastic"].clear()
    assert recording._verified_qualification_context(sealed)["candidate_maps"]["mbon11"]["baseline_plastic"] == [0.5, 0.25]


@pytest.mark.parametrize("run_kind", ["pilot", "confirmation"])
@pytest.mark.parametrize("anchors", [0, 2])
def test_nonqualification_factory_counts_and_no_context(map_engine_factory, tmp_path, run_kind, anchors):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path, run_kind=run_kind, anchors=anchors)
    created = []
    def factory():
        result = map_engine_factory()
        created.append(result)
        return result
    prefix = recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
    assert len(created) == (1 if anchors else 0)
    assert prefix.verification_mode == "native-replay"
    assert prefix._attestation.qualification_context_bytes is None
    with pytest.raises(recording.RunArtifactError):
        recording._verified_qualification_context(prefix)
    seal_map_recording(recorder, engine, tmp_path)
    created.clear()
    sealed = recording.verify_replay_run(recorder.path, engine_factory=factory)
    assert len(created) == (1 if anchors else 0)
    assert sealed._attestation.qualification_context_bytes is None
    with pytest.raises(recording.RunArtifactError):
        recording._verified_qualification_context(sealed)


@pytest.mark.parametrize("empty", [1, 2])
@pytest.mark.parametrize("wide_overlap", [False, True])
def test_qualification_context_preserves_genuine_empty_maps_and_layouts(
    map_engine_factory, tmp_path, empty, wide_overlap,
):
    from fly_connectome_sim.experiment import recorder as recording

    def factory():
        return map_engine_factory(empty=empty, index_dtype=np.int64 if wide_overlap else np.int32,
                                  overlap=wide_overlap)
    recorder, engine = map_recording(factory, tmp_path)
    prefix = recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
    context = recording._verified_qualification_context(prefix)
    for name in (["mbon11"] if empty == 1 else ["mbon07", "mbon11"]):
        assert context["candidate_maps"][name] == {
            "target_indices": [6 if name == "mbon07" or empty == 1 else 7],
            **{key: [] for key in ("candidate_positions", "candidate_edge_indices",
                "candidate_edge_pre_source_ids", "candidate_edge_post_source_ids", "candidate_kc_indices",
                "candidate_kc_source_ids", "baseline_plastic")},
        }
    assert context["dan_indices"] == [3, 2]
    seal_map_recording(recorder, engine, tmp_path)


@pytest.mark.parametrize("sealed", [False, True])
@pytest.mark.parametrize("run_kind", ["qualification", "pilot", "confirmation"])
def test_native_proof_issuance_is_bound_to_exact_owner(map_engine_factory, tmp_path, sealed, run_kind):
    from copy import copy
    from dataclasses import replace
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path, run_kind=run_kind)
    ordinary = recorder.validate_prefix()
    if sealed:
        seal_map_recording(recorder, engine, tmp_path)
        ordinary = recording.verify_run(recorder.path)
        genuine = recording.verify_replay_run(recorder.path, engine_factory=map_engine_factory)
    else:
        genuine = recording.verify_replay_prefix(ordinary, engine_factory=map_engine_factory)
    assert genuine.verification_mode == "native-replay"
    binding = genuine._manifest_bytes if sealed else genuine._attestation_binding()
    constructed = recording._ReplayAttestation(binding, ())
    if run_kind == "qualification":
        object.__setattr__(constructed, "qualification_context_bytes", genuine._attestation.qualification_context_bytes)
    for proof in (constructed, genuine._attestation):
        object.__setattr__(ordinary, "_attestation", proof)
        with pytest.raises(recording.RunArtifactError):
            ordinary.replay_attested_state_anchors
        with pytest.raises(recording.RunArtifactError):
            ordinary.verification_mode
        with pytest.raises(recording.RunArtifactError):
            recording._verified_qualification_context(ordinary)
    for duplicate in (copy(genuine), replace(genuine)):
        # replace deliberately leaves init=False fields unissued.
        if duplicate._attestation is not None:
            with pytest.raises(recording.RunArtifactError):
                duplicate.verification_mode
        with pytest.raises(recording.RunArtifactError):
            recording._verified_qualification_context(duplicate)
    class Synthetic(type(genuine)):
        @property
        def verification_mode(self):
            return "native-replay"
        @property
        def replay_attested_state_anchors(self):
            return frozenset()
    fields = ({"path": genuine.path, "_manifest_bytes": genuine._manifest_bytes} if sealed else
              {key: getattr(genuine, key) for key in ("path", "_context_bytes", "_byte_length", "_raw_sha256", "_directory_ids")})
    synthetic = Synthetic(**fields)
    object.__setattr__(synthetic, "_attestation", genuine._attestation)
    with pytest.raises(recording.RunArtifactError):
        recording._verified_qualification_context(synthetic)
    if not sealed:
        seal_map_recording(recorder, engine, tmp_path)


def source_copy(monkeypatch, tmp_path):
    """Redirect only the current-source lookup to an actual byte-for-byte copy."""
    from fly_connectome_sim.neural import checkpoint

    package = Path(checkpoint.__file__).parents[1]
    copied = tmp_path / "package-source"
    actual = checkpoint.model_fingerprint
    for name in actual()["sources_sha256"]:
        target = copied / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((package / name).read_bytes())
    assert actual(root=copied) == actual()
    monkeypatch.setattr(checkpoint, "model_fingerprint", lambda root=None: actual(copied if root is None else root))
    return copied / "experiment" / "recorder.py"


@pytest.mark.parametrize("sealed", [False, True])
def test_qualification_context_intake_rehashes_current_sources_without_engine(
    map_engine_factory, tmp_path, monkeypatch, sealed,
):
    from fly_connectome_sim.experiment import recorder as recording
    from fly_connectome_sim.engine import FlyEngine
    from fly_connectome_sim.neural import native

    recorder, engine = map_recording(map_engine_factory, tmp_path)
    prefix = recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
    value = prefix
    if sealed:
        seal_map_recording(recorder, engine, tmp_path)
        value = recording.verify_replay_run(recorder.path, engine_factory=map_engine_factory)
    copied_source = source_copy(monkeypatch, tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("Context intake must not construct or rebuild native runtime")
    monkeypatch.setattr(FlyEngine, "__init__", forbidden)
    monkeypatch.setattr(native, "build_native", forbidden)
    assert recording._verified_qualification_context(value)["n"] == 8
    copied_source.write_bytes(copied_source.read_bytes() + b"\n# changed source bytes\n")
    with pytest.raises(recording.RunArtifactError, match="source|fingerprint"):
        recording._verified_qualification_context(value)
    if not sealed:
        seal_map_recording(recorder, engine, tmp_path)


def test_qualification_final_issuance_rehashes_source_after_replay(map_engine_factory, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path, anchors=1)
    copied_source = source_copy(monkeypatch, tmp_path)
    ordinary = recorder.validate_prefix()
    issued = []
    original = recording._replay_verified
    def trace(value, **kwargs):
        issued.append(value)
        return original(value, **kwargs)
    monkeypatch.setattr(recording, "_replay_verified", trace)
    def factory():
        fresh = map_engine_factory()
        observe = fresh.observe
        def changed(*args, **kwargs):
            result = observe(*args, **kwargs)
            copied_source.write_bytes(copied_source.read_bytes() + b"\n# changed during replay\n")
            return result
        fresh.observe = changed
        return fresh
    with pytest.raises(recording.RunArtifactError, match="source|fingerprint"):
        recording.verify_replay_prefix(ordinary, engine_factory=factory)
    assert len(issued) == 1 and issued[0]._attestation is None
    seal_map_recording(recorder, engine, tmp_path)


@pytest.mark.parametrize("mutation", ["pre", "edges", "post", "ids", "dan", "gain", "groups"])
def test_qualification_rehashes_live_maps_even_with_cached_identity(map_engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path)
    def factory():
        fresh = map_engine_factory()
        fresh.identity()
        value = (fresh.brain.circuit[mutation] if mutation in {"pre", "edges", "dan", "gain"}
                 else fresh.groups.mbon11 if mutation == "groups" else getattr(fresh.brain, mutation))
        value.flags.writeable = True
        if mutation == "gain":
            value[:] = value[::-1]
        else:
            value[:2] = value[:2][::-1] if len(value) > 1 else [4]
        value.flags.writeable = False  # Cheap lock checks alone cannot see these same-object edits.
        return fresh
    with pytest.raises(recording.RunArtifactError):
        recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
    seal_map_recording(recorder, engine, tmp_path)


@pytest.mark.parametrize("mutation", ["csr", "post_range", "pre", "duplicate_edge", "kc_mask", "kc_group",
    "dan_inverse", "dan_sentinel", "duplicate_dan", "gain_shape", "ptr_dtype", "pre_dtype", "gain_stride",
    "initial_weight", "baseline", "native_registration", "visual_registration", "clock", "counter", "frozen",
    "modulation_mask_shape", "rest_stride", "dan_baseline_shape"])
def test_qualification_rejects_self_consistent_but_invalid_native_maps(map_engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording

    def factory():
        fresh = map_engine_factory()
        brain, circuit = fresh.brain, fresh.brain.circuit
        if mutation == "csr":
            brain.ptr[1] = 5
        elif mutation == "post_range":
            brain.post[0] = brain.n
        elif mutation == "pre":
            circuit["pre"][:] = [0, 1, 0, 1]
        elif mutation == "duplicate_edge":
            circuit["edges"][0] = circuit["edges"][1]
        elif mutation == "kc_mask":
            circuit["kc_mask"][7] = 1
        elif mutation == "kc_group":
            circuit["kc"] = np.array([0, 7], dtype=np.int64)
        elif mutation == "dan_inverse":
            circuit["dan_index"][2:4] = [0, 1]
        elif mutation == "dan_sentinel":
            circuit["dan_index"][7] = 0
        elif mutation == "duplicate_dan":
            circuit["dan"][:] = [3, 3]
        elif mutation == "gain_shape":
            circuit["gain"] = np.ones((4, 2), dtype=np.float32)
        elif mutation == "ptr_dtype":
            brain.ptr = brain.ptr.astype(np.int32)
        elif mutation == "pre_dtype":
            circuit["pre"] = circuit["pre"].astype(np.int64)
        elif mutation == "gain_stride":
            circuit["gain"] = circuit["gain"][:, ::-1]
        elif mutation == "initial_weight":
            brain.weight[0] += 0.125
        elif mutation == "baseline":
            brain.baseline_plastic[0] += 0.125
        elif mutation in {"native_registration", "visual_registration"}:
            name = "memory_u" if mutation == "native_registration" else "r8_light"
            brain.fields.remove(name)
            brain.initial.pop(name)
        elif mutation == "clock":
            brain.cursor = 1
            brain.sim_ms = 0.1
        elif mutation == "counter":
            brain.total_spikes = 1
        elif mutation == "modulation_mask_shape":
            brain.modulation_mask = brain.modulation_mask[:-1].copy()
        elif mutation == "rest_stride":
            brain.rest = np.repeat(brain.rest, 2)[::2]
        elif mutation == "dan_baseline_shape":
            brain.dan_baseline_hz = brain.dan_baseline_hz[:-1].copy()
        else:
            brain.weights_frozen = True
        return fresh
    # These archives and declarations are real but do not make malformed live
    # maps safe. Neither producer nor verifier may execute them natively.
    recorder, engine = map_recording(factory, tmp_path)
    prefix = recorder.validate_prefix()
    with pytest.raises(recording.RunArtifactError):
        recording.verify_replay_prefix(prefix, engine_factory=factory)
    seal_map_recording(recorder, engine, tmp_path)


@pytest.mark.parametrize("sealed", [False, True])
@pytest.mark.parametrize("mutation", ["events", "checkpoint", "schema", "artifact"])
def test_qualification_context_intake_rechecks_bound_artifact(
    map_engine_factory, tmp_path, monkeypatch, sealed, mutation,
):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path)
    value = recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
    seal_map_recording(recorder, engine, tmp_path)
    if sealed:
        value = recording.verify_replay_run(recorder.path, engine_factory=map_engine_factory)
    if mutation == "events":
        target = recorder.path / "events.jsonl"
        target.write_bytes(target.read_bytes().replace(b'"sim_ms":0.0', b'"sim_ms":0.1', 1))
    elif mutation == "checkpoint":
        target = recorder.path / "checkpoints" / "brain-before.npz"
        target.write_bytes(target.read_bytes() + b"changed")
    elif mutation == "schema":
        from importlib.resources import files
        schema = tmp_path / "run.schema.json"
        schema.write_bytes(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes() + b"\n")
        monkeypatch.setattr(recording, "_schema_digest", lambda: sha256(schema.read_bytes()).hexdigest())
    elif sealed:
        target = recorder.path / "run.json"
        target.write_bytes(target.read_bytes() + b" ")
    else:
        # Transplant a genuine proof onto a distinct, ordinary owner for identical bytes.
        from dataclasses import replace
        other = replace(value)
        object.__setattr__(other, "_attestation", value._attestation)
        value = other
    with pytest.raises(recording.RunArtifactError):
        recording._verified_qualification_context(value)


@pytest.mark.parametrize("mutation", ["missing", "version", "canonical", "identity", "schema", "candidate", "dan"])
def test_qualification_context_rejects_missing_or_malformed_private_payload(
    map_engine_factory, tmp_path, mutation,
):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path)
    value = recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
    context = recording._verified_qualification_context(value)
    if mutation == "version":
        context["context_version"] = "unknown/v1"
    elif mutation == "identity":
        context["engine_identity"]["neural_groups"]["mbon11"] = [4]
    elif mutation == "schema":
        context["checkpoint_schema"]["weight"]["shape"] = [-1]
    elif mutation == "candidate":
        context["candidate_maps"]["mbon11"]["candidate_edge_indices"].pop()
    elif mutation == "dan":
        context["dan_source_ids"].pop()
    payload = None if mutation == "missing" else canonical(context) + (b" " if mutation == "canonical" else b"")
    # Deliberate private-state corruption checks malformed-payload failure;
    # arbitrary Python forging all private issuance state is not the threat model.
    object.__setattr__(value._attestation, "qualification_context_bytes", payload)
    with pytest.raises(recording.RunArtifactError):
        recording._verified_qualification_context(value)
    seal_map_recording(recorder, engine, tmp_path)


@pytest.mark.parametrize("mutation", ["provenance", "configuration", "native_entrypoint"])
def test_qualification_context_rejects_python_replacements_of_native_inputs(map_engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path)
    def factory():
        fresh = map_engine_factory()
        provenance = fresh.identity()["model_provenance"]
        if mutation == "provenance":
            fresh.brain.ids.flags.writeable = True
            fresh.brain.ids[:2] = fresh.brain.ids[:2][::-1]
            fresh.brain.ids.flags.writeable = False
            fresh.brain.model_provenance = lambda: deepcopy(provenance)
        elif mutation == "configuration":
            fresh.brain.circuit["gain"].flags.writeable = True
            fresh.brain.circuit["gain"][:] = fresh.brain.circuit["gain"][::-1]
            fresh.brain.circuit["gain"].flags.writeable = False
            fresh.brain.configuration_signature = lambda: deepcopy(provenance["configuration_sha256"])
        else:
            fresh.brain.advance = lambda *args: None
        return fresh
    with pytest.raises(recording.RunArtifactError):
        recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
    seal_map_recording(recorder, engine, tmp_path)


def test_native_context_schema_reads_real_registered_extension_without_engine(map_engine_factory, tmp_path):
    from fly_connectome_sim.experiment import recorder as recording
    from fly_connectome_sim.neural.checkpoint import read_checkpoint

    def factory():
        engine = map_engine_factory()
        engine.brain.registered_extension = np.arange(6, dtype=np.float64).reshape(2, 3)
        engine.brain.fields.append("registered_extension")
        engine.brain.initial["registered_extension"] = engine.brain.registered_extension.copy()
        engine.brain.registered_extension.flags.writeable = False
        return engine
    recorder, engine = map_recording(factory, tmp_path)
    value = recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
    context = recording._verified_qualification_context(value)
    assert context["checkpoint_schema"]["registered_extension"] == {"dtype": "<f8", "shape": [2, 3]}
    metadata, arrays = read_checkpoint(recorder.path / "checkpoints" / "brain-before.npz",
        context["engine_identity"]["model_provenance"], context["checkpoint_schema"], context["n"])
    assert metadata["cursor"] == 0
    np.testing.assert_array_equal(arrays["registered_extension"], [[0, 1, 2], [3, 4, 5]])
    seal_map_recording(recorder, engine, tmp_path)


@pytest.mark.parametrize("name", ["metadata", "metadata.npy"])
def test_qualification_context_rejects_reserved_checkpoint_schema_alias(map_engine_factory, tmp_path, name):
    from fly_connectome_sim.experiment import recorder as recording

    recorder, engine = map_recording(map_engine_factory, tmp_path)
    def factory():
        fresh = map_engine_factory()
        value = np.zeros(1, dtype=np.float32)
        setattr(fresh.brain, name, value)
        fresh.brain.fields.append(name)
        fresh.brain.initial[name] = value.copy()
        return fresh
    with pytest.raises(recording.RunArtifactError):
        recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
    seal_map_recording(recorder, engine, tmp_path)


@pytest.mark.skipif(os.getenv("FLY_CONNECTOME_SIM_FULL_TEST") != "1",
                    reason="full MaleCNS native map-context integration is opt-in")
def test_fullgraph_zero_anchor_qualification_context(tmp_path, monkeypatch):
    """Map compatibility only: no training, scientific terminal, seal or config."""
    import gc
    import weakref
    from fly_connectome_sim.engine import FlyEngine
    from fly_connectome_sim.experiment import recorder as recording
    from fly_connectome_sim.neural import native

    producer = FlyEngine.from_prepared_graph()
    assert producer.brain.n == 166_700 and len(producer.brain.post) == 25_582_938
    identity = producer.identity()
    expected_schema = {name: {"dtype": getattr(producer.brain, name).dtype.str,
                              "shape": list(getattr(producer.brain, name).shape)}
                       for name in ["weight", *producer.brain.fields]}
    expected_maps = {}
    for name in ("mbon11", "mbon07"):
        target = getattr(producer.groups, name)
        positions = np.flatnonzero(np.isin(producer.brain.post[producer.brain.circuit["edges"]], target))
        selected = producer.brain.circuit["edges"][positions]
        pre = producer.brain.circuit["pre"][positions]
        kcs = np.unique(pre)
        expected_maps[name] = {
            "target_indices": target.tolist(), "candidate_positions": positions.tolist(),
            "candidate_edge_indices": selected.tolist(),
            "candidate_edge_pre_source_ids": [str(value) for value in producer.brain.ids[pre]],
            "candidate_edge_post_source_ids": [str(value) for value in producer.brain.ids[producer.brain.post[selected]]],
            "candidate_kc_indices": kcs.tolist(), "candidate_kc_source_ids": [str(value) for value in producer.brain.ids[kcs]],
            "baseline_plastic": producer.brain.baseline_plastic[positions].tolist(),
        }
    expected_dan = producer.brain.circuit["dan"].tolist()
    expected_dan_sources = [str(value) for value in producer.brain.ids[producer.brain.circuit["dan"]]]
    black = {"generator": "black-rgb/v1", "input_shape": [32, 32, 3], "input_dtype": "uint8",
             "input_sha256": _rgb_input_sha256(np.zeros((32, 32, 3), dtype=np.uint8))}
    metadata = {"engine_identity": identity, "protocol_version": "qualification/v1",
                "stimulus_version": "associative-stimuli/v1", "family": "qualification", "seeds": [11, 23],
                "factors": {}, "input_sha256": [black["input_sha256"]], "black_input": black}
    recorder = recording.RunRecorder(tmp_path / "fullgraph-map-prefix", run_kind="qualification",
                                     metadata=metadata, root_branch_id="baseline")
    try:
        source = tmp_path / "fullgraph-before.npz"
        producer.brain.checkpoint(source)
        recorder.ingest_checkpoint("brain-before.npz", source, origin_branch_id="baseline")
        recorder.append({"type": "checkpoint", "branch_id": "baseline", "sim_tick": 0,
                         "sim_ms": 0.0, "checkpoint_name": "brain-before.npz"})
        prefix = recorder.validate_prefix()
        producer_ref = weakref.ref(producer)
        del producer, target, positions, selected, pre, kcs
        gc.collect()
        assert producer_ref() is None
        factories = 0
        verifier_ref = None
        def factory():
            nonlocal factories, verifier_ref
            assert producer_ref() is None
            factories += 1
            engine = FlyEngine.from_prepared_graph()
            assert engine.brain.n == 166_700 and len(engine.brain.post) == 25_582_938
            verifier_ref = weakref.ref(engine)
            return engine
        value = recording.verify_replay_prefix(prefix, engine_factory=factory)
        gc.collect()
        assert factories == 1 and verifier_ref() is None
        assert value.replay_attested_state_anchors == frozenset()
        def forbidden(*args, **kwargs):
            pytest.fail("Decoded native context must not create/build an engine")
        monkeypatch.setattr(FlyEngine, "from_prepared_graph", forbidden)
        monkeypatch.setattr(native, "build_native", forbidden)
        context = recording._verified_qualification_context(value)
        assert context["n"] == 166_700
        assert context["checkpoint_schema"]["weight"] == {"dtype": "<f4", "shape": [25_582_938]}
        assert context["engine_identity"] == identity
        assert context["checkpoint_schema"] == expected_schema
        assert context["candidate_maps"] == expected_maps
        assert context["dan_indices"] == expected_dan and context["dan_source_ids"] == expected_dan_sources
        context["dan_indices"].clear()
        assert recording._verified_qualification_context(value)["dan_indices"] == expected_dan
        assert factories == 1 and not (recorder.path / "run.json").exists()
    finally:
        recorder._stream.close()  # Deliberately leave a prefix, never invent a terminal.


def replay_module():
    try:
        return importlib.import_module("fly_connectome_sim.experiment.replay")
    except ModuleNotFoundError:
        pytest.fail("The bounded replay primitives have not been implemented")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def scientific(value):
    if isinstance(value, dict):
        return {key: scientific(item) for key, item in value.items()
                if key not in {"compute_seconds", "kernel_seconds"}}
    if isinstance(value, list):
        return [scientific(item) for item in value]
    return value


def seal_events(events):
    previous = "0" * 64
    for sequence, event in enumerate(events):
        event.update(sequence=sequence, previous_scientific_sha256=previous,
                     run_metadata_sha256="a" * 64)
        data = {key: value for key, value in event.items() if key != "scientific_sha256"}
        previous = sha256(canonical(scientific(data))).hexdigest()
        event["scientific_sha256"] = previous
    return {"event_count": len(events), "final_sequence": len(events) - 1,
            "final_scientific_sha256": previous}


def history(engine_factory, tmp_path, *, frozen=True, thaw=True, chunks=(5000, 7),
            branch="paired", interleave=True, decimal_duration=False):
    engine = engine_factory()
    engine.observe(np.full((2, 3, 3), 80, dtype=np.uint8), 0.3, learning=True)
    engine.brain.weights_frozen = frozen
    source = tmp_path / "source.npz"
    engine.brain.checkpoint(source)
    occurrence = {"checkpoint_name": source.name,
                  "checkpoint_sha256": sha256(source.read_bytes()).hexdigest(),
                  "origin_branch_id": "training", "checkpoint_sequence": 0,
                  "sim_tick": 3}
    black = {"generator": "black-rgb/v1", "input_shape": [2, 3, 3],
             "input_dtype": "uint8",
             "input_sha256": _rgb_input_sha256(np.zeros((2, 3, 3), dtype=np.uint8))}
    events = [{"type": "checkpoint", "branch_id": "training", "sim_tick": 3,
               "sim_ms": 3 * 0.1, "checkpoint_name": source.name,
               "checkpoint_sha256": occurrence["checkpoint_sha256"]},
              {"type": "fork", "branch_id": branch, "sim_tick": 3,
               "sim_ms": 3 * 0.1, "operation_version": "black-retention-operation/v1",
               "parent_branch_id": "training", "parent_checkpoint_name": source.name,
               "parent_checkpoint_sequence": 0,
               "parent_checkpoint_sha256": occurrence["checkpoint_sha256"]}]
    if thaw:
        events.append({"type": "replay_thaw", "branch_id": branch,
                       "operation_version": "black-retention-operation/v1",
                       "sim_tick": 3, "sim_ms": 3 * 0.1,
                       "before_weights_frozen": frozen, "after_weights_frozen": False})
        engine.brain.weights_frozen = False
    for ticks in chunks:
        start = engine.brain.cursor
        duration = ticks / 10 if decimal_duration else ticks * 0.1
        telemetry = engine.observe(np.zeros((2, 3, 3), dtype=np.uint8), duration,
                                   current_mv=19.5, qualification_detail=True)
        events.append({"type": "neutral_gap_chunk", "branch_id": branch,
                       "operation_version": "black-retention-operation/v1", **black,
                       "start_tick": start, "end_tick": engine.brain.cursor,
                       "duration_ticks": ticks, "sim_ms": engine.brain.cursor * 0.1,
                       "duration_ms": duration, "stimulation": None,
                       "learning": False, "current_mv": 19.5,
                       "pathway_detail": False, "qualification_detail": True,
                       "telemetry": telemetry})
        if interleave:
            events.append({"type": "annotation", "branch_id": "training", "sim_ms": 0.3})
    prefix = seal_events(events)
    arguments = {"source_occurrence": occurrence, "origin_branch_id": branch,
                 "target_tick": engine.brain.cursor, "engine_identity": engine.identity(),
                 "run_metadata_sha256": "a" * 64, "black_input": black,
                 "scientific_prefix": prefix}
    return engine, source, events, arguments


def anchor_for(api, engine, events, arguments, *, anchor_id="retained-paired"):
    recipe = api.build_black_retention_recipe(iter(events), **arguments)
    return api.build_state_anchor(anchor_id=anchor_id,
                                  complete_state_sha256=engine.brain.checkpoint_state_sha256(),
                                  recipe=recipe)


def recorded_retention(engine_factory, tmp_path, *, seconds=0.1, paired_sham=False,
                       append_anchor=True, source_variant="valid", wrong_endpoint=False,
                       chunks=(5000, 7), mixed_wire_clocks=False):
    """Real retained source; only durable before/source/after enter the inventory."""
    from fly_connectome_sim.experiment.recorder import RunRecorder

    api = replay_module()
    producer = engine_factory()
    black = {"generator": "black-rgb/v1", "input_shape": [2, 3, 3],
             "input_dtype": "uint8",
             "input_sha256": _rgb_input_sha256(np.zeros((2, 3, 3), dtype=np.uint8))}
    metadata = {"engine_identity": producer.identity(), "protocol_version": "pilot/v1",
                "stimulus_version": "associative-stimuli/v1", "family": "pilot",
                "seeds": [101], "factors": {}, "input_sha256": [black["input_sha256"]],
                "black_input": black}
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=metadata,
                           root_branch_id="training")
    source = tmp_path / "snapshot.npz"
    producer.brain.checkpoint(source)
    before_bytes = source.read_bytes()
    recorder.ingest_checkpoint("brain-before.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_ms": 0.0,
                     "sim_tick": 0, "checkpoint_name": "brain-before.npz"})
    producer.observe(np.full((2, 3, 3), 80, dtype=np.uint8), 0.3, learning=True)
    producer.brain.weights_frozen = True
    producer.brain.checkpoint(source)
    if source_variant != "valid":
        source.write_bytes(before_bytes if source_variant == "zero_cursor" else b"invalid NPZ")
    digest = recorder.ingest_checkpoint("source.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_tick": 3,
                     "sim_ms": 0.3, "checkpoint_name": "source.npz"})
    anchors = []
    for branch in (("paired", "sham") if paired_sham else ("paired",)):
        if source_variant == "valid":
            producer.brain.restore(recorder.path / "checkpoints" / "source.npz")
        recorder.append({"type": "fork", "branch_id": branch, "sim_tick": 3,
                         "sim_ms": 3 * 0.1 if mixed_wire_clocks else 0.3,
                         "operation_version": api.OPERATION_VERSION,
                         "parent_branch_id": "training", "parent_checkpoint_name": "source.npz",
                         "parent_checkpoint_sequence": 1, "parent_checkpoint_sha256": digest})
        recorder.append({"type": "replay_thaw", "branch_id": branch, "sim_tick": 3,
                         "sim_ms": 0.3, "operation_version": api.OPERATION_VERSION,
                         "before_weights_frozen": True, "after_weights_frozen": False})
        producer.brain.weights_frozen = False
        for ticks in chunks:
            start = producer.brain.cursor
            telemetry = producer.observe(np.zeros((2, 3, 3), dtype=np.uint8), ticks / 10,
                                         current_mv=19.5, qualification_detail=True)
            telemetry = scientific(telemetry)
            telemetry.update(compute_seconds=seconds, kernel_seconds=seconds)
            recorder.append({"type": "neutral_gap_chunk", "branch_id": branch, **black,
                             "operation_version": api.OPERATION_VERSION,
                             "start_tick": start, "end_tick": producer.brain.cursor,
                             "duration_ticks": ticks, "duration_ms": ticks / 10,
                             "sim_ms": producer.brain.cursor * 0.1 if mixed_wire_clocks
                                       else producer.brain.cursor / 10, "stimulation": None,
                             "learning": False, "current_mv": 19.5, "pathway_detail": False,
                             "qualification_detail": True, "telemetry": telemetry})
        prefix = recorder.validate_prefix()
        recipe = api.build_black_retention_recipe(
            prefix.iter_events(), source_occurrence={"checkpoint_name": "source.npz",
                "checkpoint_sha256": digest, "origin_branch_id": "training",
                "checkpoint_sequence": 1, "sim_tick": 3}, origin_branch_id=branch,
            target_tick=producer.brain.cursor, engine_identity=producer.identity(),
            run_metadata_sha256=prefix.manifest["run_metadata_sha256"], black_input=black,
            scientific_prefix=prefix.scientific_prefix,
        )
        anchor = api.build_state_anchor(anchor_id=f"retained-{branch}", recipe=recipe,
            complete_state_sha256="b" * 64 if wrong_endpoint else producer.brain.checkpoint_state_sha256())
        if append_anchor:
            recorder.append_state_anchor(anchor)
        anchors.append(anchor)
    return recorder, producer, anchors


def finish_recording(recorder, producer, tmp_path):
    source = tmp_path / "after.npz"
    producer.brain.checkpoint(source)
    recorder.ingest_checkpoint("brain-after.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_tick": producer.brain.cursor,
                     "sim_ms": producer.brain.cursor / 10, "checkpoint_name": "brain-after.npz"})
    recorder.close()


def test_real_recorded_prefix_and_sealed_replay_attest_all_routes(engine_factory, tmp_path):
    from dataclasses import FrozenInstanceError
    from fly_connectome_sim.experiment import recorder as recording

    recorder, producer, anchors = recorded_retention(engine_factory, tmp_path, paired_sham=True)
    snapshot = producer.brain.checkpoint_state_sha256()
    created = []
    def isolated_factory():
        result = engine_factory()
        created.append(result)
        return result
    prefix = recorder.validate_prefix()
    assert prefix.replay_attested_state_anchors == frozenset()
    attested = recording.verify_replay_prefix(prefix, engine_factory=isolated_factory)
    expected = frozenset(anchor["state_anchor_sha256"] for anchor in anchors)
    assert attested.replay_attested_state_anchors == expected
    assert len(created) == 1
    assert anchors[0]["complete_state_sha256"] == anchors[1]["complete_state_sha256"]
    assert len(expected) == 2
    assert producer.brain.checkpoint_state_sha256() == snapshot
    with pytest.raises(FrozenInstanceError):
        attested.path = tmp_path
    projected = attested.manifest
    projected["metadata"]["seeds"].append(999)
    assert attested.manifest["metadata"]["seeds"] == [101]
    assert set(attested.scientific_prefix) == {"event_count", "final_sequence", "final_scientific_sha256"}
    finish_recording(recorder, producer, tmp_path)
    # Appended complete lines do not change the immutable fixed prefix.
    assert len(list(attested.iter_events())) == prefix.scientific_prefix["event_count"]
    ordinary = recording.verify_run(recorder.path)
    assert ordinary.replay_attested_state_anchors == frozenset()
    formal = recording.verify_replay_run(recorder.path, engine_factory=isolated_factory)
    assert formal.replay_attested_state_anchors == expected
    assert len(created) == 2
    assert list(formal.iter_events()) == list(ordinary.iter_events())
    assert set(formal.manifest["checkpoints"]) == {"brain-before.npz", "source.npz", "brain-after.npz"}
    assert set(formal.manifest["state_anchors"]) == expected
    assert formal.manifest["checkpoints"]["source.npz"]["checkpoint_sequence"] == 1


def test_recorded_timing_changes_only_raw_bindings(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.recorder import verify_run
    recordings = []
    for index, seconds in enumerate((0.1, 0.7)):
        directory = tmp_path / str(index)
        directory.mkdir()
        recorder, producer, anchors = recorded_retention(engine_factory, directory, seconds=seconds)
        prefix = recorder.validate_prefix()
        recordings.append((prefix, anchors[0]))
        finish_recording(recorder, producer, directory)
    first, second = recordings
    assert first[0].scientific_prefix == second[0].scientific_prefix
    assert first[1] == second[1]
    assert first[0] != second[0]
    assert verify_run(first[0].path).manifest["events_sha256"] != verify_run(second[0].path).manifest["events_sha256"]
    replay_module().validate_state_anchor(first[1])


@pytest.mark.parametrize("mutation", ["metadata", "input", "shape", "recipe", "prefix",
                                      "endpoint", "extra", "branch", "tick", "source"])
def test_anchor_append_checks_actual_prefix_transactionally(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment.recorder import RunArtifactError
    recorder, producer, anchors = recorded_retention(engine_factory, tmp_path, append_anchor=False)
    api = replay_module()
    bad = deepcopy(anchors[0])
    if mutation == "metadata":
        bad["run_metadata_sha256"] = "b" * 64
    elif mutation == "extra":
        bad["invented"] = True
    else:
        recipe = bad["recipe"]
        if mutation == "input":
            recipe["black_input"]["input_sha256"] = "b" * 64
        elif mutation == "shape":
            recipe["black_input"]["input_shape"] = [3, 2, 3]
            recipe["black_input"]["input_sha256"] = _rgb_input_sha256(np.zeros((3, 2, 3), dtype=np.uint8))
        elif mutation == "recipe":
            recipe["operations"][-1]["current_mv"] = 20.0
        elif mutation == "prefix":
            recipe["scientific_prefix"]["final_scientific_sha256"] = "b" * 64
        elif mutation == "endpoint":
            # A zero-length fork recipe is internally coherent but omits the actual retention.
            recipe["operations"] = recipe["operations"][:1]
            recipe["target_tick"] = 3
        elif mutation == "branch":
            recipe["origin_branch_id"] = "invented"
        elif mutation == "tick":
            recipe["operations"][0]["sim_tick"] += 1
        elif mutation == "source":
            recipe["source_occurrence"]["checkpoint_sequence"] = 0
        payload = {key: value for key, value in recipe.items() if key != "replay_recipe_sha256"}
        recipe["replay_recipe_sha256"] = api._domain_sha256(api.RECIPE_DOMAIN, payload)
        try:
            bad = api.build_state_anchor(anchor_id=bad["anchor_id"], recipe=recipe,
                                        complete_state_sha256=bad["complete_state_sha256"])
        except ValueError:
            # Malformed grammar still reaches the public adapter's strict validator.
            bad["recipe"] = recipe
    before = recorder.path.joinpath("events.jsonl").read_bytes()
    prefix = recorder.validate_prefix()
    with pytest.raises(RunArtifactError):
        recorder.append_state_anchor(bad)
    assert recorder.path.joinpath("events.jsonl").read_bytes() == before
    assert recorder.validate_prefix().manifest == prefix.manifest
    recorder.append_state_anchor(anchors[0])
    finish_recording(recorder, producer, tmp_path)


@pytest.mark.parametrize("mutation", ["both", "null", "missing", "late", "origin", "clock", "name", "sequence"])
def test_anchor_parent_is_exact_and_rejection_does_not_append(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment.recorder import RunArtifactError
    recorder, producer, anchors = recorded_retention(engine_factory, tmp_path)
    parent = {"type": "branch_start", "branch_id": "test-A", "sim_ms": 501.0,
              "parent_branch_id": "paired", "parent_state_anchor_sha256": anchors[0]["state_anchor_sha256"]}
    bad = deepcopy(parent)
    if mutation == "both":
        bad["parent_checkpoint_sha256"] = anchors[0]["durable_ancestor_checkpoint_sha256"]
    elif mutation == "null":
        bad["parent_state_anchor_sha256"] = None
    elif mutation == "missing":
        bad.pop("parent_state_anchor_sha256")
    elif mutation == "late":
        bad["parent_state_anchor_sha256"] = "b" * 64
    elif mutation == "origin":
        bad["parent_branch_id"] = "training"
    elif mutation == "clock":
        bad["sim_ms"] = 501.1
    elif mutation == "name":
        bad["parent_checkpoint_name"] = "source.npz"
    elif mutation == "sequence":
        bad["parent_checkpoint_sequence"] = 1
    before = (recorder.path / "events.jsonl").read_bytes()
    with pytest.raises(RunArtifactError):
        recorder.append(bad)
    assert (recorder.path / "events.jsonl").read_bytes() == before
    recorder.append(parent)
    with pytest.raises(RunArtifactError):
        recorder.append({**parent, "parent_state_anchor_sha256": "b" * 64})
    with pytest.raises(RunArtifactError):
        recorder.append_state_anchor(anchors[0])
    finish_recording(recorder, producer, tmp_path)


@pytest.mark.parametrize("mutation", ["overwrite", "truncate", "source", "inventory", "unknown_inventory"])
def test_fixed_prefix_rejects_mutation_and_defensively_copies_inventory(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, _ = recorded_retention(engine_factory, tmp_path)
    prefix = recorder.validate_prefix()
    path = recorder.path / "events.jsonl"
    raw = path.read_bytes()
    if mutation == "overwrite":
        path.write_bytes(raw.replace(b'"compute_seconds":0.1', b'"compute_seconds":0.7'))
    elif mutation == "truncate":
        path.write_bytes(raw[:-1])
    elif mutation == "source":
        (recorder.path / "checkpoints" / "source.npz").write_bytes(b"invalid NPZ")
    elif mutation == "inventory":
        recorder._checkpoints["source.npz"]["checkpoint_sequence"] = 0
    else:
        recorder._checkpoints["source.npz"]["invented"] = True
    if mutation in {"inventory", "unknown_inventory"}:
        with pytest.raises(recording.RunArtifactError):
            recorder.validate_prefix()
        recorder._checkpoints["source.npz"].pop("invented", None)
        recorder._checkpoints["source.npz"]["checkpoint_sequence"] = 1
    else:
        with pytest.raises(recording.RunArtifactError):
            list(prefix.iter_events())
        with pytest.raises(recording.RunArtifactError):
            recording.verify_replay_prefix(prefix, engine_factory=engine_factory)
    recorder._stream.close()


def test_fixed_prefix_ignores_later_partial_tail_but_current_validation_rejects_it(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.recorder import RunArtifactError
    recorder, producer, _ = recorded_retention(engine_factory, tmp_path)
    prefix = recorder.validate_prefix()
    with (recorder.path / "events.jsonl").open("ab") as stream:
        stream.write(b'{"partial":')
    assert len(list(prefix.iter_events())) == prefix.scientific_prefix["event_count"]
    with pytest.raises(RunArtifactError):
        recorder.validate_prefix()
    recorder._stream.close()


@pytest.mark.parametrize("sealed", [False, True])
def test_stream_validation_binds_the_raw_bytes_actually_read(engine_factory, tmp_path, monkeypatch, sealed):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, _ = recorded_retention(engine_factory, tmp_path)
    prefix = recorder.validate_prefix()
    if sealed:
        finish_recording(recorder, producer, tmp_path)
        value = recording.verify_run(recorder.path)
    else:
        value = prefix
    path = recorder.path / "events.jsonl"
    saved = path.read_bytes()
    original = recording._raw_events
    def changing_reader(*args, **kwargs):
        if kwargs.get("count") is not None:
            yield from original(*args, **kwargs)
            return
        # Real on-disk timing substitution during scan, restored before final reread.
        path.write_bytes(saved.replace(b'"compute_seconds":0.1', b'"compute_seconds":0.7'))
        try:
            yield from original(*args, **kwargs)
        finally:
            path.write_bytes(saved)
    monkeypatch.setattr(recording, "_raw_events", changing_reader)
    with pytest.raises(recording.RunArtifactError):
        list(value.iter_events())
    if not sealed:
        recorder._stream.close()


@pytest.mark.parametrize("field,value", [("sim_tick", False), ("checkpoint_sequence", False),
                                         ("sim_ms", False), ("sim_ms", "0")])
def test_prefix_inventory_declared_types_are_strict(engine_factory, tmp_path, field, value):
    from fly_connectome_sim.experiment.recorder import RunArtifactError
    recorder, _, _ = recorded_retention(engine_factory, tmp_path)
    recorder._checkpoints["brain-before.npz"][field] = value
    with pytest.raises(RunArtifactError):
        recorder.validate_prefix()
    recorder._stream.close()


def test_fixed_prefix_is_bound_to_the_packaged_schema(engine_factory, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, _, _ = recorded_retention(engine_factory, tmp_path)
    prefix = recorder.validate_prefix()
    monkeypatch.setattr(recording, "_schema_digest", lambda: "b" * 64)
    with pytest.raises(recording.RunArtifactError):
        list(prefix.iter_events())
    recorder._stream.close()


def test_recorder_orders_authoritative_ticks_across_both_permitted_wire_forms(engine_factory, tmp_path):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, anchors = recorded_retention(engine_factory, tmp_path,
        chunks=(3,), mixed_wire_clocks=True)
    events = list(recorder.validate_prefix().iter_events())
    assert events[2]["sim_ms"] == 0.30000000000000004
    assert events[3]["sim_ms"] == 0.3
    assert events[4]["sim_ms"] == 0.6000000000000001
    assert events[5]["sim_ms"] == 0.6
    finish_recording(recorder, producer, tmp_path)
    assert recording.verify_replay_run(recorder.path,
        engine_factory=engine_factory).replay_attested_state_anchors == frozenset({anchors[0]["state_anchor_sha256"]})


@pytest.mark.parametrize("mutation", ["unknown", "undeclared", "shape"])
def test_metadata_black_declaration_is_strict_before_any_anchor(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment.recorder import RunArtifactError, RunRecorder
    black = {"generator": "black-rgb/v1", "input_shape": [2, 3, 3], "input_dtype": "uint8",
             "input_sha256": _rgb_input_sha256(np.zeros((2, 3, 3), dtype=np.uint8))}
    metadata = {"engine_identity": engine_factory().identity(), "protocol_version": "pilot/v1",
                "stimulus_version": "associative-stimuli/v1", "family": "pilot",
                "seeds": [101], "factors": {}, "input_sha256": [black["input_sha256"]],
                "black_input": black}
    if mutation == "unknown":
        black["invented"] = True
    elif mutation == "undeclared":
        metadata["input_sha256"] = []
    else:
        black["input_shape"] = [True, 3, 3]
    with pytest.raises(RunArtifactError):
        RunRecorder(tmp_path / "invalid", run_kind="pilot", metadata=metadata, root_branch_id="root")


@pytest.mark.parametrize("mutation", ["events", "manifest", "source", "second_endpoint"])
def test_actual_replay_partial_failure_or_interference_issues_no_attestation(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, anchors = recorded_retention(engine_factory, tmp_path, paired_sham=True)
    finish_recording(recorder, producer, tmp_path)
    run = recording.verify_run(recorder.path)
    created = []
    def factory():
        engine = engine_factory()
        created.append(engine)
        original = engine.observe
        def observe(*args, **kwargs):
            result = original(*args, **kwargs)
            if mutation == "events":
                path = recorder.path / "events.jsonl"
                path.write_bytes(path.read_bytes().replace(b'"compute_seconds":0.1', b'"compute_seconds":0.7'))
            elif mutation == "manifest":
                path = recorder.path / "run.json"
                path.write_bytes(path.read_bytes() + b" ")
            elif mutation == "source":
                (recorder.path / "checkpoints" / "source.npz").write_bytes(b"changed")
            elif mutation == "second_endpoint" and engine.brain.cursor == 5010:
                # First reconstruction succeeds; the separately restored second route fails.
                if getattr(engine, "completed_route", False):
                    engine.brain.r8_light[0] = 0.9
                engine.completed_route = True
            return result
        engine.observe = observe
        return engine
    with pytest.raises(recording.RunArtifactError):
        recording.verify_replay_run(recorder.path, engine_factory=factory)
    assert len(created) == 1
    assert run.replay_attested_state_anchors == frozenset()


@pytest.mark.parametrize("mutation", ["events", "manifest", "source"])
def test_attested_value_rejects_later_mutation_in_public_consumption(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, _ = recorded_retention(engine_factory, tmp_path)
    prefix = recording.verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    finish_recording(recorder, producer, tmp_path)
    sealed = recording.verify_replay_run(recorder.path, engine_factory=engine_factory)
    if mutation == "manifest":
        path = recorder.path / "run.json"
    elif mutation == "source":
        path = recorder.path / "checkpoints" / "source.npz"
    else:
        path = recorder.path / "events.jsonl"
    path.write_bytes(path.read_bytes() + b"tampered")
    if mutation == "events":
        # Only later bytes changed: prefix boundary remains valid; seal fails.
        assert prefix.replay_attested_state_anchors
    elif mutation == "source":
        with pytest.raises(recording.RunArtifactError):
            list(prefix.iter_events())
    with pytest.raises(recording.RunArtifactError):
        list(sealed.iter_events())
    with pytest.raises(recording.RunArtifactError):
        sealed.replay_attested_state_anchors


@pytest.mark.parametrize("mutation", ["zero_cursor", "invalid_bytes", "endpoint", "engine_identity"])
def test_coherent_artifact_still_requires_actual_npz_cursor_state_and_identity(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, _ = recorded_retention(engine_factory, tmp_path,
        source_variant=mutation if mutation in {"zero_cursor", "invalid_bytes"} else "valid",
        wrong_endpoint=mutation == "endpoint")
    prefix = recorder.validate_prefix()
    factory = engine_factory
    if mutation == "engine_identity":
        def factory():
            other = engine_factory()
            other.brain.eta += 0.1
            return other
    with pytest.raises(recording.RunArtifactError):
        recording.verify_replay_prefix(prefix, engine_factory=factory)
    assert prefix.replay_attested_state_anchors == frozenset()
    finish_recording(recorder, producer, tmp_path)
    assert list(recording.verify_run(recorder.path).iter_events())
    with pytest.raises(recording.RunArtifactError):
        recording.verify_replay_run(recorder.path, engine_factory=factory)


@pytest.mark.parametrize("formal", [False, True])
def test_sealed_inventory_cannot_omit_the_event_bound_source_tick(engine_factory, tmp_path, formal):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, _ = recorded_retention(engine_factory, tmp_path)
    finish_recording(recorder, producer, tmp_path)
    manifest = recording.verify_run(recorder.path).manifest
    assert manifest["checkpoints"]["source.npz"].pop("sim_tick") == 3
    (recorder.path / "run.json").write_bytes(canonical(manifest) + b"\n")
    with pytest.raises(recording.RunArtifactError):
        if formal:
            recording.verify_replay_run(recorder.path, engine_factory=engine_factory)
        else:
            recording.verify_run(recorder.path)


def test_initial_prefix_derives_checkpoint_ticks_from_event_bytes(engine_factory, tmp_path):
    recorder, producer, _ = recorded_retention(engine_factory, tmp_path)
    recorder._checkpoints["source.npz"].pop("sim_tick")
    prefix = recorder.validate_prefix()
    assert prefix.manifest["checkpoints"]["source.npz"]["sim_tick"] == 3
    # Restore the recorder's declaration for its subsequent seal; the prefix already derived it.
    recorder._checkpoints["source.npz"]["sim_tick"] = 3
    finish_recording(recorder, producer, tmp_path)


def reseal_recorded(path, events, manifest):
    """Coherent scientific/raw framing for adversarial artifact tests."""
    previous = "0" * 64
    for sequence, event in enumerate(events):
        event.update(sequence=sequence, previous_scientific_sha256=previous)
        previous = sha256(canonical(scientific({key: value for key, value in event.items()
                                               if key != "scientific_sha256"}))).hexdigest()
        event["scientific_sha256"] = previous
    raw = b"".join(canonical(event) + b"\n" for event in events)
    (path / "events.jsonl").write_bytes(raw)
    manifest.update(event_count=len(events), final_scientific_sha256=previous,
                    events_sha256=sha256(raw).hexdigest())
    for event in events:
        if "checkpoint_name" in event:
            manifest["checkpoints"][event["checkpoint_name"]]["checkpoint_sequence"] = event["sequence"]
    (path / "run.json").write_bytes(canonical(manifest) + b"\n")


@pytest.mark.parametrize("mutation", ["omitted_call", "extra_thaw", "reordered_calls", "unknown",
                                      "implicit", "extra_anchor_field", "coherent_recipe",
                                      "missing_anchor", "invented_anchor", "anchor_sequence",
                                      "missing_checkpoint", "extra_checkpoint", "checkpoint_sequence"])
def test_persisted_scan_rebuilds_recipe_and_exact_inventory(engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment import recorder as recording
    recorder, producer, anchors = recorded_retention(engine_factory, tmp_path)
    finish_recording(recorder, producer, tmp_path)
    manifest = recording.verify_run(recorder.path).manifest
    events = [json.loads(line) for line in (recorder.path / "events.jsonl").read_bytes().splitlines()]
    if mutation == "omitted_call":
        events.pop(4)
    elif mutation == "extra_thaw":
        events.insert(4, deepcopy(events[3]))
    elif mutation == "reordered_calls":
        events[4], events[5] = events[5], events[4]
    elif mutation == "unknown":
        events[3]["type"] = "freeze"
    elif mutation == "implicit":
        events[3].pop("operation_version")
    elif mutation == "extra_anchor_field":
        events[6]["invented"] = True
    elif mutation == "coherent_recipe":
        api = replay_module()
        recipe = anchors[0]["recipe"]
        recipe["operations"][-1]["current_mv"] = 20.0
        recipe["replay_recipe_sha256"] = api._domain_sha256(api.RECIPE_DOMAIN,
            {key: value for key, value in recipe.items() if key != "replay_recipe_sha256"})
        anchor = api.build_state_anchor(anchor_id=anchors[0]["anchor_id"], recipe=recipe,
                                        complete_state_sha256=anchors[0]["complete_state_sha256"])
        events[6].update(anchor)
        manifest["state_anchors"] = {anchor["state_anchor_sha256"]: {**anchor, "event_sequence": 6}}
    elif mutation == "missing_anchor":
        manifest["state_anchors"] = {}
    elif mutation == "invented_anchor":
        api = replay_module()
        invented = api.build_state_anchor(anchor_id="invented", recipe=anchors[0]["recipe"],
                                          complete_state_sha256=anchors[0]["complete_state_sha256"])
        manifest["state_anchors"][invented["state_anchor_sha256"]] = {**invented, "event_sequence": 6}
    elif mutation == "anchor_sequence":
        manifest["state_anchors"][anchors[0]["state_anchor_sha256"]]["event_sequence"] = 5
    elif mutation == "missing_checkpoint":
        manifest["checkpoints"].pop("source.npz")
    elif mutation == "extra_checkpoint":
        manifest["checkpoints"]["invented.npz"] = deepcopy(manifest["checkpoints"]["source.npz"])
    elif mutation == "checkpoint_sequence":
        manifest["checkpoints"]["source.npz"]["checkpoint_sequence"] = 0
    if mutation == "checkpoint_sequence" or mutation == "missing_checkpoint":
        (recorder.path / "run.json").write_bytes(canonical(manifest) + b"\n")
    else:
        reseal_recorded(recorder.path, events, manifest)
    with pytest.raises(recording.RunArtifactError):
        recording.verify_run(recorder.path)



def test_real_partial_call_replay_matches_live_target_and_keeps_producer(engine_factory, tmp_path):
    api = replay_module()
    producer, source, events, args = history(engine_factory, tmp_path)
    before = producer.brain.checkpoint_state_sha256()
    files = {path: path.read_bytes() for path in tmp_path.iterdir()}
    anchor = anchor_for(api, producer, events, args)
    result = api.replay_black_retention(anchor, source_path=source, engine_factory=engine_factory)
    assert result is not producer
    assert result.brain.cursor == 5010
    assert result.brain.checkpoint_state_sha256() == before
    assert producer.brain.checkpoint_state_sha256() == before
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == files
    assert [op.get("duration_ticks") for op in anchor["recipe"]["operations"]] == [None, None, 5000, 7]


@pytest.mark.parametrize("frozen,thaw,chunks", [(True, True, ()), (False, False, ()),
                                              (False, False, (3,)), (False, True, (3,))])
def test_zero_retention_and_explicit_or_absent_thaw(engine_factory, tmp_path, frozen, thaw, chunks):
    api = replay_module()
    engine, source, events, args = history(engine_factory, tmp_path, frozen=frozen,
                                          thaw=thaw, chunks=chunks)
    anchor = anchor_for(api, engine, events, args)
    result = api.replay_black_retention(anchor, source_path=source, engine_factory=engine_factory)
    assert result.brain.checkpoint_state_sha256() == engine.brain.checkpoint_state_sha256()


def test_frozen_source_requires_explicit_thaw_even_at_zero_retention(engine_factory, tmp_path):
    api = replay_module()
    engine, source, events, args = history(engine_factory, tmp_path, thaw=False, chunks=())
    anchor = anchor_for(api, engine, events, args)
    with pytest.raises(ValueError):
        api.replay_black_retention(anchor, source_path=source, engine_factory=engine_factory)


@pytest.mark.parametrize("mutation", ["omit", "extra", "reorder", "silent", "duplicate_thaw",
                                      "thaw_after", "name", "sequence", "origin", "clock",
                                      "recursive", "source_after", "legacy", "telemetry"])
def test_prefix_rejects_inexact_history(engine_factory, tmp_path, mutation):
    api = replay_module()
    _, _, events, args = history(engine_factory, tmp_path)
    if mutation == "omit":
        events.pop(3)
    elif mutation == "extra":
        events.insert(4, deepcopy(events[3]))
    elif mutation == "reorder":
        events[3], events[5] = events[5], events[3]
    elif mutation == "silent":
        events.insert(3, {"type": "freeze", "branch_id": "paired", "sim_ms": 0.3})
    elif mutation == "duplicate_thaw":
        events.insert(3, deepcopy(events[2]))
    elif mutation == "thaw_after":
        events.insert(4, events.pop(2))
    elif mutation == "name":
        events[1]["parent_checkpoint_name"] = "other.npz"
    elif mutation == "sequence":
        events[1]["parent_checkpoint_sequence"] = 1
    elif mutation == "origin":
        events[1]["parent_branch_id"] = "other"
    elif mutation == "clock":
        events[3]["start_tick"] += 1
    elif mutation == "recursive":
        events[1]["parent_state_anchor_sha256"] = "1" * 64
    elif mutation == "source_after":
        events[0], events[1] = events[1], events[0]
    elif mutation == "legacy":
        events[3].pop("operation_version")
    elif mutation == "telemetry":
        events[3]["telemetry"]["input_shape"] = [3, 2, 3]
    args["scientific_prefix"] = seal_events(events)
    original = deepcopy((events, args))
    with pytest.raises(ValueError):
        api.build_black_retention_recipe(iter(events), **args)
    assert (events, args) == original


def test_equal_endpoint_changed_history_is_bound_and_routes_are_distinct(engine_factory, tmp_path):
    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, frozen=False, thaw=False, chunks=())
    paired = anchor_for(api, engine, events, args)
    changed = deepcopy(events)
    changed.append({"type": "replay_thaw", "operation_version": "black-retention-operation/v1",
                    "branch_id": "paired", "sim_tick": 3, "sim_ms": 3 * 0.1,
                    "before_weights_frozen": False, "after_weights_frozen": False})
    changed_args = {**args, "scientific_prefix": seal_events(changed)}
    explicit = anchor_for(api, engine, changed, changed_args)
    assert explicit["complete_state_sha256"] == paired["complete_state_sha256"]
    assert explicit["replay_recipe_sha256"] != paired["replay_recipe_sha256"]
    sham_events = deepcopy(events)
    sham_events[1]["branch_id"] = "sham"
    sham_args = {**args, "origin_branch_id": "sham", "scientific_prefix": seal_events(sham_events)}
    sham = anchor_for(api, engine, sham_events, sham_args, anchor_id="retained-sham")
    assert sham["complete_state_sha256"] == paired["complete_state_sha256"]
    assert sham["state_anchor_sha256"] != paired["state_anchor_sha256"]
    assert paired["state_anchor_sha256"] != paired["complete_state_sha256"]


@pytest.mark.parametrize("field,value", [("target_tick", True), ("target_tick", np.int64(3)),
                                        ("run_metadata_sha256", 5), ("origin_branch_id", "training")])
def test_recipe_scalar_types_and_direct_target_are_strict(engine_factory, tmp_path, field, value):
    api = replay_module()
    _, _, events, args = history(engine_factory, tmp_path, chunks=())
    args[field] = value
    with pytest.raises(ValueError):
        api.build_black_retention_recipe(events, **args)


@pytest.mark.parametrize("shape", [[10**12, 1, 3], [True, 2, 3], [0, 2, 3], [33, 2, 3], [2, 3, 4]])
def test_unsupported_shape_is_rejected_before_frame_allocation(engine_factory, tmp_path, monkeypatch, shape):
    api = replay_module()
    _, _, events, args = history(engine_factory, tmp_path, chunks=())
    args["black_input"]["input_shape"] = shape
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid shape allocated a black frame")
    monkeypatch.setattr(np, "zeros", forbidden)
    with pytest.raises(ValueError):
        api.build_black_retention_recipe(events, **args)


def test_scientific_timing_exclusions_and_defensive_copies(engine_factory, tmp_path):
    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, chunks=(3,))
    original = deepcopy((events, args))
    first = anchor_for(api, engine, events, args)
    timed = deepcopy(events)
    timed[3]["compute_seconds"] = 91.0
    timed[3]["telemetry"]["kernel_seconds"] = 88.0
    timed_args = {**args, "scientific_prefix": seal_events(timed)}
    second = anchor_for(api, engine, timed, timed_args)
    assert first == second
    assert (events, args) == original
    recipe = api.validate_black_retention_recipe(first["recipe"])
    recipe["black_input"]["input_shape"][0] = 1
    assert first["recipe"]["black_input"]["input_shape"] == [2, 3, 3]
    validated = api.validate_state_anchor(first)
    validated["recipe"]["operations"].clear()
    assert first["recipe"]["operations"]


@pytest.mark.parametrize("place", ["prefix", "identity", "operation", "anchor"])
def test_raw_prefix_and_unknown_typed_fields_cannot_enter_scientific_bindings(engine_factory, tmp_path, place):
    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, chunks=())
    if place == "prefix":
        args["scientific_prefix"]["raw_prefix_sha256"] = "b" * 64
    elif place == "identity":
        args["engine_identity"]["model_provenance"]["configuration_sha256"]["nested"] = {"events_sha256": "b" * 64}
    elif place == "operation":
        events[2]["nested"] = {"raw_prefix_length": 123}
        args["scientific_prefix"] = seal_events(events)
    if place == "anchor":
        anchor = anchor_for(api, engine, events, args)
        anchor["own_scientific_sha256"] = "b" * 64
        with pytest.raises(ValueError):
            api.validate_state_anchor(anchor)
    else:
        with pytest.raises(ValueError):
            api.build_black_retention_recipe(events, **args)


@pytest.mark.parametrize("mutation", ["wrong_file", "wrong_name", "cursor", "identity", "freeze", "target"])
def test_execution_rechecks_real_source_and_engine(engine_factory, tmp_path, mutation):
    api = replay_module()
    engine, source, events, args = history(engine_factory, tmp_path, chunks=(3,))
    factory = engine_factory
    if mutation == "cursor":
        replacement = engine_factory()
        replacement.brain.weights_frozen = True
        replacement.brain.checkpoint(source)
        digest = sha256(source.read_bytes()).hexdigest()
        args["source_occurrence"]["checkpoint_sha256"] = digest
        events[0]["checkpoint_sha256"] = digest
        events[1]["parent_checkpoint_sha256"] = digest
        args["scientific_prefix"] = seal_events(events)
    if mutation == "freeze":
        events[2]["before_weights_frozen"] = False
        args["scientific_prefix"] = seal_events(events)
    anchor = anchor_for(api, engine, events, args)
    if mutation == "wrong_file":
        source.write_bytes(source.read_bytes() + b"changed")
    elif mutation == "wrong_name":
        wrong = tmp_path / "other.npz"
        wrong.write_bytes(source.read_bytes())
        source = wrong
    elif mutation == "identity":
        def factory():
            other = engine_factory()
            other.brain.eta += 0.1
            return other
    elif mutation == "target":
        anchor = api.build_state_anchor(anchor_id=anchor["anchor_id"],
                                        complete_state_sha256="b" * 64, recipe=anchor["recipe"])
    before = source.read_bytes()
    with pytest.raises(ValueError):
        api.replay_black_retention(anchor, source_path=source, engine_factory=factory)
    assert source.read_bytes() == before


def test_literal_domain_and_length_framing_is_independent():
    api = replay_module()
    # A literal vector exercises shared framing, independently of recipe construction.
    encoded = b'{"x":1}'
    expected = sha256(b"fly-connectome-black-retention/v1\0" + struct.pack("<Q", 7) + encoded).hexdigest()
    assert api._domain_sha256(b"fly-connectome-black-retention/v1\0", {"x": 1}) == expected


@pytest.mark.parametrize("field,value", [("end_ms", 9.0), ("duration_ms", 9.0)])
def test_bin_clock_declarations_cannot_contradict_the_call(engine_factory, tmp_path, field, value):
    api = replay_module()
    _, _, events, args = history(engine_factory, tmp_path, chunks=(107,))
    events[3]["telemetry"]["bins"][0][field] = value
    args["scientific_prefix"] = seal_events(events)
    with pytest.raises(ValueError):
        api.build_black_retention_recipe(events, **args)


@pytest.mark.parametrize("extra", ["input_shape", "engine_identity", "start_tick", "end_tick", "sim_tick"])
def test_nested_telemetry_bindings_are_checked(engine_factory, tmp_path, extra):
    api = replay_module()
    _, _, events, args = history(engine_factory, tmp_path, chunks=(3,))
    value = {"input_shape": [3, 2, 3], "engine_identity": {},
             "start_tick": 88, "end_tick": 88, "sim_tick": 88}[extra]
    events[3]["telemetry"]["nested"] = {extra: value}
    args["scientific_prefix"] = seal_events(events)
    with pytest.raises(ValueError):
        api.build_black_retention_recipe(events, **args)


def test_execution_uses_one_real_engine_one_frame_and_exact_top_level_calls(engine_factory, tmp_path, monkeypatch):
    api = replay_module()
    producer, source, events, args = history(engine_factory, tmp_path, chunks=(101, 7))
    anchor = anchor_for(api, producer, events, args)
    engines = []
    calls = []
    frames = []
    original_zeros = np.zeros
    def zeros(shape, *args, **kwargs):
        result = original_zeros(shape, *args, **kwargs)
        if tuple(np.atleast_1d(shape)) == (2, 3, 3):
            frames.append(result)
        return result
    def factory():
        engine = engine_factory()
        engines.append(engine)
        observe = engine.observe
        def traced(frame, duration_ms, **kwargs):
            calls.append((frame, duration_ms, kwargs))
            return observe(frame, duration_ms, **kwargs)
        engine.observe = traced
        return engine
    monkeypatch.setattr(np, "zeros", zeros)
    result = api.replay_black_retention(anchor, source_path=source, engine_factory=factory)
    assert engines == [result]
    assert len(frames) == 1
    assert len(calls) == 2
    for (frame, duration, kwargs), ticks in zip(calls, (101, 7), strict=True):
        assert frame is frames[0]
        assert frame.dtype == np.uint8 and not frame.flags.writeable
        assert duration == ticks * 0.1
        assert kwargs == {"stimulation": None, "current_mv": 19.5, "learning": False,
                          "pathway_detail": False, "qualification_detail": True}


@pytest.mark.parametrize("mutation", ["source_tick", "source_name", "source_sequence", "target",
                                      "metadata", "identity", "flags", "shape", "current", "extra"])
def test_typed_recipe_tampering_fails(engine_factory, tmp_path, mutation):
    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, chunks=(3,))
    anchor = anchor_for(api, engine, events, args)
    recipe = deepcopy(anchor["recipe"])
    if mutation == "source_tick":
        recipe["source_occurrence"]["sim_tick"] = True
    elif mutation == "source_name":
        recipe["source_occurrence"]["checkpoint_name"] = "../source.npz"
    elif mutation == "source_sequence":
        recipe["source_occurrence"]["checkpoint_sequence"] = 1
    elif mutation == "target":
        recipe["target_tick"] += 1
    elif mutation == "metadata":
        recipe["run_metadata_sha256"] = "b" * 64
    elif mutation == "identity":
        recipe["engine_identity"]["neural_groups"]["kc"] = [1]
    elif mutation == "flags":
        recipe["operations"][-1]["qualification_detail"] = 1
    elif mutation == "shape":
        recipe["black_input"]["input_shape"] = [3, 2, 3]
    elif mutation == "current":
        recipe["operations"][-1]["current_mv"] += 1
    elif mutation == "extra":
        recipe["operations"][-1]["hidden_mutation"] = False
    before = deepcopy(recipe)
    with pytest.raises(ValueError):
        api.validate_black_retention_recipe(recipe)
    assert recipe == before


@pytest.mark.parametrize("field,value", [("event_count", 999), ("final_sequence", 999),
                                        ("final_scientific_sha256", "b" * 64)])
def test_completed_prefix_endpoint_is_checked(engine_factory, tmp_path, field, value):
    api = replay_module()
    _, _, events, args = history(engine_factory, tmp_path, chunks=())
    args["scientific_prefix"][field] = value
    with pytest.raises(ValueError):
        api.build_black_retention_recipe(iter(events), **args)


def test_recipe_and_anchor_domains_are_independently_recomputed(engine_factory, tmp_path):
    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, chunks=())
    anchor = anchor_for(api, engine, events, args)
    recipe = deepcopy(anchor["recipe"])
    recipe_digest = recipe.pop("replay_recipe_sha256")
    encoded = canonical(recipe)
    assert recipe_digest == sha256(b"fly-connectome-black-retention/v1\0"
                                  + struct.pack("<Q", len(encoded)) + encoded).hexdigest()
    occurrence = deepcopy(anchor)
    digest = occurrence.pop("state_anchor_sha256")
    encoded = canonical(occurrence)
    assert digest == sha256(b"fly-connectome-state-anchor/v1\0"
                           + struct.pack("<Q", len(encoded)) + encoded).hexdigest()


def test_identical_source_bytes_are_resolved_by_exact_occurrence(engine_factory, tmp_path):
    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, chunks=())
    duplicate = {**events[0], "checkpoint_name": "duplicate.npz"}
    events.insert(1, duplicate)
    args["scientific_prefix"] = seal_events(events)
    first = anchor_for(api, engine, events, args)
    events[2]["parent_checkpoint_name"] = "duplicate.npz"
    events[2]["parent_checkpoint_sequence"] = 1
    args["source_occurrence"]["checkpoint_name"] = "duplicate.npz"
    args["source_occurrence"]["checkpoint_sequence"] = 1
    args["scientific_prefix"] = seal_events(events)
    second = anchor_for(api, engine, events, args)
    assert first["complete_state_sha256"] == second["complete_state_sha256"]
    assert first["state_anchor_sha256"] != second["state_anchor_sha256"]


@pytest.mark.parametrize("field,value", [("end_tick", "6"), ("duration_ticks", "3"),
                                        ("start_tick", True), ("duration_ms", True),
                                        ("duration_ticks", 0), ("duration_ticks", 5001),
                                        ("learning", 0), ("pathway_detail", 0),
                                        ("current_mv", True), ("sim_ms", 0.6000000001)])
def test_invalid_call_scalars_fail_before_telemetry_processing(engine_factory, tmp_path, field, value):
    api = replay_module()
    _, _, events, args = history(engine_factory, tmp_path, chunks=(3,))
    events[3][field] = value
    args["scientific_prefix"] = seal_events(events)
    with pytest.raises(ValueError):
        api.build_black_retention_recipe(events, **args)


@pytest.mark.parametrize("decimal_duration", [False, True])
def test_wire_representations_preserve_call_argument_and_native_clock(engine_factory, tmp_path, decimal_duration):
    api = replay_module()
    engine, source, events, args = history(engine_factory, tmp_path, chunks=(3,),
                                          decimal_duration=decimal_duration)
    assert engine.brain.sim_ms == 6 * 0.1
    assert events[3]["telemetry"]["sim_ms"] == 0.6
    assert events[3]["telemetry"]["interval_ms"] == events[3]["duration_ms"]
    for event in events[:3]:
        event["sim_ms"] = 0.3
    events[3]["sim_ms"] = 0.6
    args["scientific_prefix"] = seal_events(events)
    anchor = anchor_for(api, engine, events, args)
    assert anchor["recipe"]["operations"][-1]["duration_ms"] == (3 / 10 if decimal_duration else 3 * 0.1)
    result = api.replay_black_retention(anchor, source_path=source, engine_factory=engine_factory)
    assert result.brain.sim_ms == 6 * 0.1
    assert result.brain.checkpoint_state_sha256() == engine.brain.checkpoint_state_sha256()


@pytest.mark.parametrize("structure", ["recipe", "anchor", "source", "prefix", "black", "operation"])
def test_typed_structures_reject_unsupported_timing_fields(engine_factory, tmp_path, structure):
    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, chunks=(3,))
    anchor = anchor_for(api, engine, events, args)
    value = {"recipe": anchor["recipe"], "anchor": anchor,
             "source": anchor["recipe"]["source_occurrence"],
             "prefix": anchor["recipe"]["scientific_prefix"],
             "black": anchor["recipe"]["black_input"],
             "operation": anchor["recipe"]["operations"][-1]}[structure]
    value["compute_seconds"] = 91.0
    with pytest.raises(ValueError):
        api.validate_state_anchor(anchor)


def test_constructed_anchor_preserves_unchanged_analyzer_identity_gate(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.analysis import _validate_anchor

    api = replay_module()
    engine, _, events, args = history(engine_factory, tmp_path, chunks=(3,))
    anchor = anchor_for(api, engine, events, args)
    config = {"engine_identity": engine.identity()}
    _validate_anchor(anchor, config)
    assert anchor["source_identity_sha256"] == config["engine_identity"]["sha256"]
    changed = deepcopy(anchor)
    changed["source_identity_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="state_anchor_source_identity"):
        _validate_anchor(changed, config)
    with pytest.raises(ValueError):
        api.validate_state_anchor(changed)
