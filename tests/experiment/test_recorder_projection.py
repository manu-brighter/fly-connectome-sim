"""Single-pass historical anchors with real recorder bytes and no attestation."""

from copy import deepcopy
from hashlib import sha256
import json
import gc
import tracemalloc

import pytest

from fly_connectome_sim.experiment import recorder as recording, replay


def identity():
    digest = "a" * 64
    data = {
        "version": "fly-engine/v1",
        "model_provenance": {
            "model": "projection-fixture", "eta": 0.1,
            "model_fingerprint": {"version": "fixture/v1", "sources_sha256": {"fixture": digest},
                                  "sha256": digest},
            "build": {"model": "fixture", "source_sha256": digest, "compiler": "fixture",
                      "flags": [], "library": "fixture", "binary_sha256": digest},
            "parameters": {"neural_dt_ms": 0.1},
            **{key: digest for key in ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256",
                                      "plastic_edges_sha256")},
            "configuration_sha256": {},
        },
        "neural_groups": {name: [0] for name in ("pam11", "ppl101", "kc", "mbon07", "mbon11",
                                               "motor_left", "motor_right")},
    }
    data["sha256"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode()).hexdigest()
    return data


def make_recorder(tmp_path):
    header = {"version": "rgb-input/v1", "dtype": "uint8", "rank": 3, "shape": [1, 1, 3]}
    black = {"generator": "black-rgb/v1", "input_shape": [1, 1, 3], "input_dtype": "uint8",
             "input_sha256": sha256(recording._canonical(header) + b"\n" + bytes(3)).hexdigest()}
    metadata = {"engine_identity": identity(), "protocol_version": "pilot/v1",
                "stimulus_version": "associative-stimuli/v1", "family": "pilot", "seeds": [101],
                "factors": {}, "input_sha256": [black["input_sha256"]], "black_input": black}
    recorder = recording.RunRecorder(tmp_path / "run", run_kind="pilot", metadata=metadata,
                                     root_branch_id="training")
    source = tmp_path / "source.npz"
    source.write_bytes(b"opaque checkpoint; ordinary integrity fixture, no native attestation")
    digest = recorder.ingest_checkpoint("brain-before.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_tick": 3,
                     "sim_ms": 0.3, "checkpoint_name": "brain-before.npz"})
    occurrence = {"checkpoint_name": "brain-before.npz", "checkpoint_sha256": digest,
                  "origin_branch_id": "training", "checkpoint_sequence": 0, "sim_tick": 3}
    return recorder, source, occurrence


def fork(recorder, occurrence, branch):
    recorder.append({"type": "fork", "branch_id": branch, "sim_tick": occurrence["sim_tick"],
                     "sim_ms": occurrence["sim_tick"] * 0.1,
                     "operation_version": replay.OPERATION_VERSION,
                     "parent_branch_id": occurrence["origin_branch_id"],
                     "parent_checkpoint_name": occurrence["checkpoint_name"],
                     "parent_checkpoint_sequence": occurrence["checkpoint_sequence"],
                     "parent_checkpoint_sha256": occurrence["checkpoint_sha256"]})


def call(recorder, branch, start=3, ticks=7, *, decimal=False, **extra):
    recorder.append({"type": "neutral_gap_chunk", "branch_id": branch,
                     "operation_version": replay.OPERATION_VERSION, **recorder.metadata["black_input"],
                     "start_tick": start, "end_tick": start + ticks, "duration_ticks": ticks,
                     "duration_ms": ticks / 10 if decimal else ticks * 0.1,
                     "sim_ms": (start + ticks) / 10 if decimal else (start + ticks) * 0.1,
                     "stimulation": None, "learning": False, "current_mv": 0,
                     "pathway_detail": False, "qualification_detail": True, **extra})


def recipe_for(recorder, occurrence, branch, tick):
    events = list(recording._raw_events(recorder.path))
    return replay.build_black_retention_recipe(
        events, source_occurrence=occurrence, origin_branch_id=branch, target_tick=tick,
        engine_identity=recorder.metadata["engine_identity"],
        run_metadata_sha256=recorder._chain.metadata_digest, black_input=recorder.metadata["black_input"],
        scientific_prefix={"event_count": len(events), "final_sequence": len(events) - 1,
                           "final_scientific_sha256": events[-1]["scientific_sha256"]},
    )


def append_anchor(recorder, occurrence, branch, tick):
    anchor = replay.build_state_anchor(anchor_id=f"anchor-{branch}", complete_state_sha256="b" * 64,
                                       recipe=recipe_for(recorder, occurrence, branch, tick))
    recorder.append_state_anchor(anchor)
    return anchor


def context(recorder):
    return {"root_branch_id": recorder.root_branch_id, "metadata": recorder.metadata,
            "checkpoints": deepcopy(recorder._checkpoints), "run_kind": recorder.run_kind}


def drain(iterator):
    while True:
        try:
            next(iterator)
        except StopIteration as completed:
            return completed.value


def test_historical_anchors_consume_each_raw_event_once(tmp_path, monkeypatch):
    recorder, source, occurrence = make_recorder(tmp_path)
    branches = ("first", "second", "third")
    for branch in branches:
        fork(recorder, occurrence, branch)
    for branch in branches:
        call(recorder, branch, telemetry={"compute_seconds": 0.1, "bins": [{"end_tick": 10}]})
        recorder.append({"type": "observation", "branch_id": "training", "sim_ms": 0.3})
    anchors = [append_anchor(recorder, occurrence, branch, 10) for branch in branches]
    recorder.ingest_checkpoint("brain-after.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_ms": 0.3,
                     "sim_tick": 3, "checkpoint_name": "brain-after.npz"})
    recorder.close()
    manifest, _ = recording._read_manifest(recorder.path)
    counts = {"events": 0, "historical_readers": 0, "readers": 0}
    original = recording._raw_events

    def counted(*args, **kwargs):
        counts["readers"] += 1
        counts["historical_readers"] += int(kwargs.get("count") is not None)
        for event in original(*args, **kwargs):
            counts["events"] += 1
            yield event

    monkeypatch.setattr(recording, "_raw_events", counted)
    chain = drain(recording._scan_chain(recorder.path, manifest))
    assert chain.count == manifest["event_count"] == 14
    assert chain.previous == manifest["final_scientific_sha256"]
    assert chain.scanned_raw_sha256 == manifest["events_sha256"]
    assert recording._canonical(chain.anchors) == recording._canonical(manifest["state_anchors"])
    assert set(chain.anchors) == {anchor["state_anchor_sha256"] for anchor in anchors}
    assert counts == {"events": 14, "historical_readers": 0, "readers": 1}


def anchored_history(tmp_path, *, decimal=False, thaw=False, chunks=(7,)):
    recorder, source, occurrence = make_recorder(tmp_path)
    fork(recorder, occurrence, "paired")
    if thaw:
        recorder.append({"type": "replay_thaw", "branch_id": "paired", "sim_tick": 3,
                         "sim_ms": 0.3, "operation_version": replay.OPERATION_VERSION,
                         "before_weights_frozen": True, "after_weights_frozen": False})
    cursor = 3
    for ticks in chunks:
        call(recorder, "paired", cursor, ticks, decimal=decimal,
             telemetry={"nested": {"input_shape": [1, 1, 3]}, "compute_seconds": 0.1})
        cursor += ticks
    append_anchor(recorder, occurrence, "paired", cursor)
    recorder.flush()
    return recorder, list(recording._raw_events(recorder.path))


def rechain(events, metadata_digest, *, edit_recipe=None):
    """Adversarial coherent rehash, leaving ordinary gates genuinely exercised."""
    positions = {event["sequence"]: index for index, event in enumerate(events)
                 if event.get("sequence") is not None}
    previous = recording.GENESIS
    for sequence, event in enumerate(events):
        if event["type"] == "state_anchor":
            recipe = event["recipe"]
            recipe["scientific_prefix"] = {"event_count": sequence, "final_sequence": sequence - 1,
                                            "final_scientific_sha256": previous}
            for operation in recipe["operations"]:
                actual_sequence = positions[operation["event_sequence"]]
                operation["event_sequence"] = actual_sequence
                operation["event_scientific_sha256"] = events[actual_sequence]["scientific_sha256"]
            if edit_recipe is not None:
                edit_recipe(recipe)
            recipe["replay_recipe_sha256"] = replay._domain_sha256(
                replay.RECIPE_DOMAIN, {key: value for key, value in recipe.items()
                                       if key != "replay_recipe_sha256"})
            event.update(replay.build_state_anchor(anchor_id=event["anchor_id"], recipe=recipe,
                                                   complete_state_sha256=event["complete_state_sha256"]))
        event.update(sequence=sequence, previous_scientific_sha256=previous,
                     run_metadata_sha256=metadata_digest)
        previous = sha256(recording._canonical(recording._scientific_event(event))).hexdigest()
        event["scientific_sha256"] = previous


def write_events(recorder, events):
    recorder.path.joinpath("events.jsonl").write_bytes(
        b"".join(recording._canonical(event) + b"\n" for event in events))


def public_recipe(events, recorder, source, target):
    return replay.build_black_retention_recipe(
        events, source_occurrence=source, origin_branch_id="paired", target_tick=target,
        engine_identity=recorder.metadata["engine_identity"],
        run_metadata_sha256=recorder._chain.metadata_digest, black_input=recorder.metadata["black_input"],
        scientific_prefix={"event_count": len(events), "final_sequence": len(events) - 1,
                           "final_scientific_sha256": events[-1]["scientific_sha256"]},
    )


@pytest.mark.parametrize("decimal,thaw,chunks", [
    (False, False, ()), (True, True, ()), (False, True, (7, 2)), (True, False, (7, 2)),
])
def test_scanner_matches_public_builder_for_zero_thaw_partial_and_wire_forms(tmp_path, decimal, thaw, chunks):
    recorder, events = anchored_history(tmp_path, decimal=decimal, thaw=thaw, chunks=chunks)
    expected = events[-1]["recipe"]
    assert recording._canonical(public_recipe(events[:-1], recorder, expected["source_occurrence"],
                                              expected["target_tick"])) == recording._canonical(expected)
    chain = drain(recording._scan_chain(recorder.path, context(recorder)))
    assert chain.anchors[events[-1]["state_anchor_sha256"]]["recipe"] == expected
    assert chain.projection.branches["paired"] is None


@pytest.mark.parametrize("mutation", [
    "noncheckpoint_source", "tickless_source", "prior_event", "wrong_version", "extra_call_field",
    "unknown_call", "duplicate_thaw", "late_thaw", "gap", "telemetry", "black", "second_fork",
])
def test_replay_invalid_histories_are_deferred_until_anchor(tmp_path, mutation):
    recorder, events = anchored_history(tmp_path, thaw=True, chunks=(7, 2))
    source = deepcopy(events[-1]["source_occurrence"])
    if mutation == "noncheckpoint_source":
        events[0]["type"] = "observation"
    elif mutation == "tickless_source":
        events[0].pop("sim_tick")
        events[1]["sim_ms"] = 0.3
        recorder._checkpoints["brain-before.npz"].pop("sim_tick")
    elif mutation == "prior_event":
        prior = deepcopy(events[1])
        prior.update(type="observation", sequence=None)
        events.insert(1, prior)
    elif mutation == "wrong_version":
        events[3]["operation_version"] = "black-retention-operation/v2"
    elif mutation == "extra_call_field":
        events[3]["extra"] = True
    elif mutation == "unknown_call":
        events[3]["type"] = "observation"
    elif mutation in {"duplicate_thaw", "late_thaw"}:
        extra = deepcopy(events[2])
        extra["sequence"] = None
        if mutation == "late_thaw":
            extra.update(sim_tick=10, sim_ms=1.0)
        events.insert(3 if mutation == "duplicate_thaw" else 4, extra)
    elif mutation == "gap":
        events[4].update(start_tick=11, duration_ticks=1, duration_ms=0.1)
    elif mutation == "telemetry":
        events[3]["telemetry"]["nested"]["duration_ticks"] = 1
    elif mutation == "black":
        events[3]["input_shape"] = [1, 2, 3]
    elif mutation == "second_fork":
        extra = deepcopy(events[1])
        extra["sequence"] = None
        events.insert(2, extra)
    rechain(events, recorder._chain.metadata_digest)
    write_events(recorder, events[:-1])
    chain = drain(recording._scan_chain(recorder.path, context(recorder)))
    assert chain.count == len(events) - 1
    assert chain.anchors == {}
    assert chain.projection.branches["paired"] is None
    with pytest.raises(ValueError):
        public_recipe(events[:-1], recorder, source, 12)
    write_events(recorder, events)
    with pytest.raises(recording.RunArtifactError, match="Invalid state anchor"):
        drain(recording._scan_chain(recorder.path, context(recorder)))


@pytest.mark.parametrize("place", ["unrelated", "excluded_timing", "source"])
def test_global_raw_prefix_guards_include_unrelated_and_excluded_values(tmp_path, place):
    recorder, events = anchored_history(tmp_path)
    if place == "source":
        events[0]["nested"] = {"raw_prefix_future": "untrusted"}
    else:
        extra = {"type": "observation", "branch_id": "training", "sim_ms": 0.3, "sequence": None,
                 "nested": {"raw_prefix_hash": "untrusted"}}
        if place == "excluded_timing":
            extra["compute_seconds"] = extra.pop("nested")
        events.insert(2, extra)
    rechain(events, recorder._chain.metadata_digest)
    write_events(recorder, events[:-1])
    assert drain(recording._scan_chain(recorder.path, context(recorder))).count == len(events) - 1
    with pytest.raises(ValueError, match="Raw prefix"):
        public_recipe(events[:-1], recorder, events[-1]["source_occurrence"], 10)
    write_events(recorder, events)
    with pytest.raises(recording.RunArtifactError, match="Raw prefix"):
        drain(recording._scan_chain(recorder.path, context(recorder)))


def test_second_anchor_permanently_blocks_its_branch(tmp_path):
    recorder, events = anchored_history(tmp_path)
    second = deepcopy(events[-1])
    second.update(anchor_id="second-anchor", sequence=None)
    events.append(second)
    rechain(events, recorder._chain.metadata_digest)
    write_events(recorder, events)
    with pytest.raises(ValueError, match="unsupported replay operation version"):
        public_recipe(events[:-1], recorder, events[-1]["source_occurrence"], 10)
    with pytest.raises(recording.RunArtifactError, match="Unsupported earlier branch-local"):
        drain(recording._scan_chain(recorder.path, context(recorder)))


@pytest.mark.parametrize("header", ["prefix", "identity", "source", "black"])
def test_operations_cannot_authorize_wrong_independently_rehashed_headers(tmp_path, header):
    recorder, events = anchored_history(tmp_path)

    def edit(recipe):
        if header == "prefix":
            recipe["scientific_prefix"]["final_scientific_sha256"] = "c" * 64
        elif header == "identity":
            changed = recipe["engine_identity"]
            changed["neural_groups"]["kc"] = [1]
            payload = {key: value for key, value in changed.items() if key != "sha256"}
            changed["sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                                  allow_nan=False).encode()).hexdigest()
        elif header == "source":
            recipe["source_occurrence"]["checkpoint_name"] = "different.npz"
        elif header == "black":
            changed = recipe["black_input"]
            changed["input_shape"] = [1, 2, 3]
            declaration = {"version": "rgb-input/v1", "dtype": "uint8", "rank": 3, "shape": [1, 2, 3]}
            changed["input_sha256"] = sha256(recording._canonical(declaration) + b"\n" + bytes(6)).hexdigest()

    operations = deepcopy(events[-1]["recipe"]["operations"])
    rechain(events, recorder._chain.metadata_digest, edit_recipe=edit)
    assert events[-1]["recipe"]["operations"] == operations
    replay.validate_state_anchor({key: events[-1][key] for key in replay.ANCHOR_FIELDS})
    write_events(recorder, events)
    with pytest.raises(recording.RunArtifactError, match="Anchor recipe differs"):
        drain(recording._scan_chain(recorder.path, context(recorder)))


def test_yielded_nested_mutation_cannot_change_projection_or_source_proof(tmp_path):
    recorder, events = anchored_history(tmp_path, thaw=True)
    iterator = recording._scan_chain(recorder.path, context(recorder))
    while True:
        try:
            event = next(iterator)
        except StopIteration as completed:
            chain = completed.value
            break
        if event["type"] == "checkpoint":
            event.update(checkpoint_name="changed.npz", sim_tick=999)
        elif event["type"] == "neutral_gap_chunk":
            event.update(start_tick=100, current_mv=99)
            event["telemetry"]["nested"]["input_shape"].append(99)
        elif event["type"] == "state_anchor":
            event["recipe"]["operations"].clear()
    assert chain.previous == events[-1]["scientific_sha256"]
    assert chain.anchors[events[-1]["state_anchor_sha256"]]["recipe"] == events[-1]["recipe"]
    assert chain.projection.sources["brain-before.npz"]["sim_tick"] == 3


def test_rejected_events_and_anchor_do_not_poison_retry(tmp_path):
    recorder, events = anchored_history(tmp_path)
    chain = recording._Chain("training", recorder.metadata, deepcopy(recorder._checkpoints), "pilot")
    chain.projection = replay._PrefixProjection(chain.metadata, chain.metadata_digest)
    for event in events[:-2]:
        chain.check(event)
    candidate = chain.projection.branches["paired"]
    before = (chain.count, chain.previous, candidate.grammar.count, candidate.operations_sha256.digest())
    rejected = deepcopy(events[-2])
    rejected["nested"] = {"raw_prefix_invalid": True}
    with pytest.raises(recording.RunArtifactError, match="Scientific event digest"):
        chain.check(rejected)
    assert (chain.count, chain.previous, candidate.grammar.count,
            candidate.operations_sha256.digest()) == before
    assert chain.projection.raw_prefix_invalid is False
    chain.check(events[-2])
    before = (chain.count, chain.previous, candidate.grammar.count, candidate.operations_sha256.digest())
    rejected_anchor = deepcopy(events[-1])
    rejected_anchor["scientific_sha256"] = "c" * 64
    with pytest.raises(recording.RunArtifactError, match="Scientific event digest"):
        chain.check(rejected_anchor)
    assert (chain.count, chain.previous, candidate.grammar.count,
            candidate.operations_sha256.digest()) == before
    assert chain.anchors == {}
    chain.check(events[-1])
    assert chain.count == len(events)
    assert chain.projection.branches["paired"] is None


@pytest.mark.parametrize("decimal,count", [(False, 0), (False, 1), (False, 4), (True, 4)])
def test_accumulator_hashes_literal_canonical_array_framing(tmp_path, decimal, count):
    recorder, _, occurrence = make_recorder(tmp_path)
    candidate = replay._BranchProjection(occurrence)
    operations = []
    if count:
        fork(recorder, occurrence, "paired")
        for index in range(count - 1):
            call(recorder, "paired", 3 + index * 7, 7, decimal=decimal)
        for event in list(recording._raw_events(recorder.path))[1:]:
            candidate.accept(event, recorder.metadata["engine_identity"], recorder.metadata["black_input"])
            reference = {"type": event["type"], "event_sequence": event["sequence"],
                         "event_scientific_sha256": event["scientific_sha256"]}
            if event["type"] == "fork":
                operation = {**reference, "sim_tick": 3}
            else:
                operation = {**reference, "start_tick": event["start_tick"], "end_tick": event["end_tick"],
                             "duration_ticks": 7, "duration_ms": 0.7 if decimal else 7 * 0.1,
                             "sim_ms": event["end_tick"] / 10 if decimal else event["end_tick"] * 0.1,
                             "stimulation": None, "learning": False, "current_mv": 0,
                             "pathway_detail": False, "qualification_detail": True}
            operations.append(operation)
    finalized = candidate.operations_sha256.copy()
    finalized.update(b"]")
    assert finalized.digest() == sha256(recording._canonical(operations)).digest()
    assert candidate.matches_operations(operations)
    assert not candidate.matches_operations([*operations, {"extra": True}])
    if operations:
        changed = deepcopy(operations)
        changed[0]["sim_tick"] = 4
        assert not candidate.matches_operations(changed)


def test_long_never_anchored_candidate_has_constant_operation_history_memory(tmp_path):
    recorder, _, occurrence = make_recorder(tmp_path)
    fork(recorder, occurrence, "paired")
    for index in range(2000):
        call(recorder, "paired", 3 + index, 1)
    recorder.flush()
    tracemalloc.start()
    try:
        iterator = recording._scan_chain(recorder.path, context(recorder))
        baseline = None
        while True:
            try:
                event = next(iterator)
            except StopIteration as completed:
                chain = completed.value
                break
            if event["sequence"] in {100, 1900}:
                gc.collect()
                retained, _ = tracemalloc.get_traced_memory()
                if baseline is None:
                    baseline = retained
                else:
                    assert retained - baseline < 64 * 1024
    finally:
        tracemalloc.stop()
    assert chain.count == 2002
    assert chain.projection.branches["paired"].grammar.count == 2001
    assert chain.projection.branches["paired"].grammar.cursor == 2003


def test_legacy_identity_is_deferred_without_anchors(tmp_path):
    recorder, _, _ = make_recorder(tmp_path)
    occurrence = {"checkpoint_name": "brain-before.npz",
                  "checkpoint_sha256": recorder._checkpoints["brain-before.npz"]["sha256"],
                  "origin_branch_id": "training", "checkpoint_sequence": 0, "sim_tick": 3}
    fork(recorder, occurrence, "paired")
    call(recorder, "paired")
    recorder.metadata["engine_identity"] = {"version": "legacy/v1"}
    events = list(recording._raw_events(recorder.path))
    digest = recording._metadata_digest("pilot", "training", recorder.metadata)
    rechain(events, digest)
    write_events(recorder, events)
    chain = drain(recording._scan_chain(recorder.path, context(recorder)))
    assert chain.count == 3
    assert chain.anchors == {}
    assert chain.projection.branches["paired"] is None


def test_equal_byte_sources_are_bound_to_their_actual_checkpoint_events(tmp_path):
    recorder, source, first = make_recorder(tmp_path)
    digest = recorder.ingest_checkpoint("equal.npz", source, origin_branch_id="training")
    recorder.append({"type": "checkpoint", "branch_id": "training", "sim_tick": 3,
                     "sim_ms": 0.3, "checkpoint_name": "equal.npz"})
    second = {**first, "checkpoint_name": "equal.npz", "checkpoint_sequence": 1}
    assert digest == first["checkpoint_sha256"]
    fork(recorder, first, "first")
    fork(recorder, second, "second")
    anchors = [append_anchor(recorder, first, "first", 3),
               append_anchor(recorder, second, "second", 3)]
    chain = drain(recording._scan_chain(recorder.path, context(recorder)))
    assert len(chain.anchors) == 2
    assert [chain.anchors[anchor["state_anchor_sha256"]]["source_occurrence"]
            for anchor in anchors] == [first, second]


def test_yield_then_close_or_failure_does_not_reuse_projection_on_next_scan(tmp_path):
    recorder, events = anchored_history(tmp_path)
    iterator = recording._scan_chain(recorder.path, context(recorder))
    next(iterator)
    next(iterator)
    iterator.close()
    broken = deepcopy(events)
    broken[-1]["scientific_sha256"] = "c" * 64
    write_events(recorder, broken)
    with pytest.raises(recording.RunArtifactError, match="Scientific event digest"):
        drain(recording._scan_chain(recorder.path, context(recorder)))
    write_events(recorder, events)
    chain = drain(recording._scan_chain(recorder.path, context(recorder)))
    assert chain.count == len(events)
    assert set(chain.anchors) == {events[-1]["state_anchor_sha256"]}
