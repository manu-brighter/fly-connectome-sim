"""Bounded replay trust boundary with real native visual checkpoint state."""

from copy import deepcopy
from hashlib import sha256
import importlib
import json
import struct

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from replay_helpers import engine_factory


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
