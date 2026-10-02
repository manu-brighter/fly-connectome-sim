"""Bounded replay trust boundary with real native visual checkpoint state."""

from copy import deepcopy
from hashlib import sha256
import importlib
import json
import struct

import numpy as np
import pytest

from fly_connectome_sim.engine import FlyEngine, NeuralGroups, _rgb_input_sha256
from fly_connectome_sim.neural.brain import MemoryBrain
from fly_connectome_sim.neural.visual import VisualMemoryBrain


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


class TinyVisualBrain(VisualMemoryBrain):
    def __init__(self, graph):
        MemoryBrain.__init__(
            self, path=graph,
            circuit={"kc": np.array([0], dtype=np.int32),
                     "dan": np.array([1], dtype=np.int32),
                     "edges": np.array([0], dtype=np.int64),
                     "pre": np.array([0], dtype=np.int32),
                     "gain": np.array([[1.0]], dtype=np.float32),
                     "kc_mask": np.array([1, 0, 0, 0], dtype=np.uint8),
                     "dan_index": np.array([-1, 0, -1, -1], dtype=np.int8)},
            modulation_mask=np.array([0, 1, 0, 0], dtype=np.uint8),
        )
        self.r8 = np.array([0], dtype=np.int32)
        self.r8_uv = np.array([[0.5, 0.5]], dtype=np.float32)
        self.r8_channel = np.array([2], dtype=np.int32)
        self.corrected_edges = np.array([], dtype=np.int64)
        self.r8_light = np.zeros(1, dtype=np.float32)
        self.fields.append("r8_light")
        self.initial["r8_light"] = self.r8_light.copy()


@pytest.fixture
def engine_factory(tmp_path):
    graph = tmp_path / "graph.npz"
    np.savez(graph, ids=np.array([10, 20, 30, 40], dtype=np.int64),
             ptr=np.array([0, 1, 2, 2, 2], dtype=np.int64),
             post=np.array([2, 2], dtype=np.int32),
             weight=np.array([0.275, 0.275], dtype=np.float32),
             retina=np.array([0], dtype=np.int32),
             uv=np.array([[0.5, 0.5]], dtype=np.float32),
             lamina=np.array([], dtype=np.int32), sugar=np.array([], dtype=np.int32),
             superclass=np.zeros(4, dtype=np.uint8))

    def factory():
        groups = NeuralGroups(**{name: np.array([index], dtype=np.int32)
                                 for name, index in [("pam11", 1), ("ppl101", 1),
                                                     ("kc", 0), ("mbon07", 2),
                                                     ("mbon11", 2), ("motor_left", 3),
                                                     ("motor_right", 3)]})
        return FlyEngine(brain=TinyVisualBrain(graph), groups=groups)

    return factory


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
