"""Native execution and fail-closed lifecycle of one paired confirmation cohort."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path

import numpy as np
import pytest

from replay_helpers import engine_factory, map_engine_factory, _declared_native_frozen_config
from fly_connectome_sim.experiment.analysis import analyze_assay, reduce_assay_evidence
from fly_connectome_sim.experiment.recorder import verify_replay_run


@pytest.fixture
def selected_caller(engine_factory, tmp_path, request):
    """Genuine caller-owned qualification prefix, without a frozen config."""
    from fly_connectome_sim.cli import _qualification_metadata
    from fly_connectome_sim.engine import _rgb_input_sha256
    from fly_connectome_sim.experiment.recorder import RunRecorder
    from fly_connectome_sim.experiment.stimuli import AssayStimuli

    native = engine_factory()
    options = getattr(request, "param", {})
    if options.get("tick"):
        native.observe(np.zeros((32, 32, 3), dtype=np.uint8), options["tick"] / 10)
    if options.get("changed_state"):
        native.brain.v[3] += 1
    if options.get("frozen"):
        native.brain.weights_frozen = True
    identity = native.identity()
    metadata = _qualification_metadata(identity)
    black = _rgb_input_sha256(np.zeros((32, 32, 3), dtype=np.uint8))
    if options.get("missing_black"):
        del metadata["black_input"]
    execution = {
        "family": "qualification", "seeds": [11, 23], "engine_identity": identity,
        "mbon11_population_size": 1, "candidate_identity": "kc-mbon11-ppl101/v1",
        "selected_configuration": {"cs_duration_ms": 100.0, "dan_onset_ms": 0.0,
                                   "post_pair_gap_ms": 500.0},
        "response_window": {"start_ms": 0.0, "end_ms": 100.0},
        "retention_times_ms": [10000, 70000],
        "input_sha256": {str(seed): {
            **{name: _rgb_input_sha256(AssayStimuli(seed, "qualification").frame(name))
               for name in ("A", "B", "C")}, "black": black,
        } for seed in (11, 23)},
    }
    recorder = RunRecorder(tmp_path / "selected", run_kind="qualification", metadata=metadata,
                           root_branch_id="qualification/baseline")
    source = tmp_path / "baseline-source.npz"
    native.brain.checkpoint(source)
    digest = recorder.ingest_checkpoint("brain-before.npz", source,
                                        origin_branch_id="qualification/baseline")
    baseline = {"checkpoint_name": "brain-before.npz", "checkpoint_sha256": digest,
                "origin_branch_id": "qualification/baseline", "checkpoint_sequence": 0,
                "sim_tick": native.brain.cursor}
    recorder.append({"type": "qualification_checkpoint", "branch_id": "qualification/baseline",
                     "sim_tick": native.brain.cursor, "sim_ms": native.brain.cursor / 10,
                     "checkpoint_name": "brain-before.npz"})
    recorder.append({"type": "prior_diagnostic", "branch_id": "qualification/baseline",
                     "sim_ms": native.brain.cursor / 10})
    recorder.append({"type": "branch_start", "branch_id": "prior-native", "sim_ms": native.brain.cursor / 10,
                     "parent_branch_id": baseline["origin_branch_id"], "parent_checkpoint_name": baseline["checkpoint_name"],
                     "parent_checkpoint_sequence": baseline["checkpoint_sequence"],
                     "parent_checkpoint_sha256": baseline["checkpoint_sha256"]})
    prior = engine_factory()
    prior.brain.restore(source)
    if options.get("frozen"):
        recorder.append({"type": "replay_thaw", "branch_id": "prior-native",
            "operation_version": "black-retention-operation/v1", "sim_tick": prior.brain.cursor,
            "sim_ms": prior.brain.cursor / 10, "before_weights_frozen": True, "after_weights_frozen": False})
        prior.brain.weights_frozen = False
    start = prior.brain.cursor
    observed = prior.observe(np.zeros((32, 32, 3), dtype=np.uint8), 10.0,
                             learning=False, pathway_detail=True, qualification_detail=True)
    recorder.append({"type": "observe", "branch_id": "prior-native",
        "operation_version": "black-retention-operation/v1", "start_tick": start,
        "end_tick": prior.brain.cursor, "duration_ticks": 100, "duration_ms": 10.0,
        "sim_ms": prior.brain.cursor / 10, "stimulation": None, "learning": False,
        "current_mv": 20.0, "pathway_detail": True, "qualification_detail": True, "telemetry": observed})
    try:
        yield recorder, execution, baseline
    finally:
        recorder.__exit__(RuntimeError, RuntimeError("intentional incomplete prefix"), None)


def test_selected_native_paired_uses_caller_baseline_and_global_positions(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    producer = assay._produce_cohorts(engine_factory, recorder, execution=execution,
        cohorts=((11, "A", "AB"),), conditions=("paired",),
        baseline_occurrence=baseline, namespace=True)
    prefix = recorder.validate_prefix()
    events = list(prefix.iter_events())
    assert producer.brain.cursor == 111000
    assert set(prefix.manifest["checkpoints"]) == {"brain-before.npz", "selected-11-A-AB-training-end.npz"}
    training = next(event for event in events if event["type"] == "qualification_training")
    checkpoint = next(event for event in events if event.get("checkpoint_name") == "selected-11-A-AB-training-end.npz")
    assert checkpoint["sequence"] > 1
    assert checkpoint["parent_checkpoint_sequence"] == baseline["checkpoint_sequence"]
    assert training["training_id"] == "selected/11/A/AB/paired/training"
    anchors = [event for event in events if event["type"] == "state_anchor"]
    assert len(anchors) == 2
    assert all(anchor["source_occurrence"]["checkpoint_sequence"] == checkpoint["sequence"] for anchor in anchors)
    responses = [event for event in events if event["type"] == "qualification_evidence"]
    assert len(responses) == 12
    assert all("response_replay_resolution_hz" not in event and "replay_id" not in event for event in responses)
    assert not any(event["type"] in {"qualification_result", "assay_result"} for event in events)
    assert not (recorder.path / "run.json").exists()


@pytest.mark.parametrize("selected_caller", [
    {"window": {"start_ms": 0.0, "end_ms": 100.0}},
    {"window": {"start_ms": 0.0, "end_ms": 300.0}, "tick": 3, "frozen": True, "cs": 300.0},
    {"window": {"start_ms": 100.0, "end_ms": 300.0}},
], indirect=True)
def test_selected_replay_native_paired_records_actual_repeats(selected_caller, engine_factory, request):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.analysis import _compare_selected_replay
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix
    recorder, execution, baseline = selected_caller
    options = request.node.callspec.params["selected_caller"]
    execution["response_window"] = options["window"]
    execution["selected_configuration"]["cs_duration_ms"] = options.get("cs", 100.0)
    records = []
    def factory():
        def native():
            engine = engine_factory()
            if options.get("tick"):
                engine.observe(np.zeros((32, 32, 3), dtype=np.uint8), options["tick"] / 10)
            engine.brain.weights_frozen = options.get("frozen", False)
            return engine
        engine = _tracked_factory(native, records, timing=len(records) + 0.25)()
        record = records[-1]
        observe = engine.observe
        def capture_boundary(*args, **kwargs):
            result = observe(*args, **kwargs)
            record["calls"][-1].update(after_state=engine.brain.checkpoint_state_sha256(),
                after_digests=engine.brain.candidate_state_digests(engine.groups.mbon11),
                candidate_w_hex=engine.brain.memory_w[engine.brain._candidate_positions(engine.groups.mbon11)].tobytes().hex())
            return result
        engine.observe = capture_boundary
        return engine
    owner = assay._produce_cohorts(factory, recorder, execution=execution,
        cohorts=((11, "A", "AB"),), conditions=("paired",),
        baseline_occurrence=baseline, namespace=True, measure_replay=True)
    assert len(records) == 21  # Production only; the independent verifier uses the raw factory.
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    events = list(prefix.iter_events())
    diagnostics = [event for event in events if event["type"] == "qualification_replay"]
    assert len(diagnostics) == 9
    originals = ["selected/11/A/AB/" + role + "/" + stimulus
                 for role in ("pre", "post/10000", "post/70000") for stimulus in ("A", "B", "C")]
    assert [event["original_branch_id"] for event in diagnostics] == originals
    assert [event["replay_id"] for event in diagnostics] == [branch + "/repeat" for branch in originals]
    responses = [event for event in events if event["type"] == "qualification_evidence"]
    assert len(responses) == 12
    assert len(records) == 21
    assert len(prefix.manifest["state_anchors"]) == 2
    assert set(prefix.manifest["checkpoints"]) == {"brain-before.npz", "selected-11-A-AB-training-end.npz"}
    assert [event["sequence"] for event in events] == list(range(len(events)))
    native_pairs = [records[index:index + 2] for index in (1, 3, 5, 8, 10, 12, 15, 17, 19)]
    for diagnostic, pair in zip(diagnostics, native_pairs):
        original, repeat = pair
        assert original["engine"] is not repeat["engine"]
        assert len(original["restores"]) == len(repeat["restores"]) == 1
        assert original["restores"][0]["state"] == repeat["restores"][0]["state"]
        if not options.get("frozen") or diagnostic["physical_key"]["phase"] == "post":
            assert original["calls"][0]["state"] == original["restores"][0]["state"]
        assert original["restores"][0]["path"].name == ("brain-before.npz" if diagnostic["physical_key"]["phase"] == "pre" else "retained.npz")
        if diagnostic["physical_key"]["phase"] == "post":
            assert not original["restores"][0]["path"].exists()
        start = {"sim_tick": original["restores"][0]["tick"],
                 "complete_state_sha256": original["restores"][0]["state"],
                 "weights_frozen": original["restores"][0]["after_clock"][-1]}
        if diagnostic["physical_key"]["phase"] == "pre":
            source = baseline
        else:
            source = prefix.manifest["state_anchors"][diagnostic["parent_state_anchor_sha256"]]["source_occurrence"]
        engine = original["engine"]
        positions = engine.brain._candidate_positions(engine.groups.mbon11)
        maps = {"target_indices": engine.groups.mbon11.tolist(), "candidate_positions": positions.tolist(),
                "candidate_edge_indices": engine.brain.circuit["edges"][positions].tolist()}
        result = _compare_selected_replay(prefix.iter_events(), diagnostic, metadata=prefix.manifest["metadata"],
            execution=execution, expected_source_occurrence=source, expected_start=start, expected_maps=maps,
            n=engine.brain.n, memory_count=len(engine.brain.memory_w), edge_count=len(engine.brain.weight),
            lower=engine.brain.rule_parameters["minimum_fraction"] - 1,
            upper=engine.brain.rule_parameters["maximum_fraction"] - 1)
        assert result == {"response_replay_resolution_hz": 0.0, "candidate_memory_w_resolution": 0.0}
        for side, record in zip(("original", "repeat"), pair):
            referenced = [events[ref["sequence"]] for ref in diagnostic["operations"][side]]
            assert [event["scientific_sha256"] for event in referenced] == [ref["scientific_sha256"] for ref in diagnostic["operations"][side]]
            assert referenced[0]["type"] == "branch_start"
            assert [event["telemetry"] for event in referenced if event["type"] == "observe"] == [call["telemetry"] for call in record["calls"]]
            assert all(call["kwargs"] == {"stimulation": None, "learning": False} for call in record["calls"])
            assert all(call["duration"] <= 500 for call in record["calls"])
            stop = diagnostic["boundaries"]["window"][side]["sim_tick"]
            window_call = next(call for call in record["calls"] if call["end"] == stop)
            assert diagnostic["candidate_projection"][side + "_hex"] == window_call["candidate_w_hex"]
            for boundary_name, call in (("window", window_call), ("final", record["calls"][-1])):
                assert diagnostic["boundaries"][boundary_name][side] == {
                    "sim_tick": call["end"], "complete_state_sha256": call["after_state"], **call["after_digests"]}
        cells = [cell for cell in responses if cell["replay_id"] == diagnostic["replay_id"]]
        assert len(cells) == (2 if diagnostic["physical_key"]["phase"] == "pre" else 1)
        assert all(cell["sim_ms"] * 10 == diagnostic["boundaries"]["window"]["original"]["sim_tick"] for cell in cells)
        window_start = diagnostic["cs_onset_tick"] + round(options["window"]["start_ms"] * 10)
        stop = diagnostic["boundaries"]["window"]["original"]["sim_tick"]
        raw = [item for call in original["calls"] for item in call["telemetry"]["bins"] if window_start < round(item["end_ms"] * 10) <= stop]
        for cell in cells:
            assert cell["bins"] == [{"start_tick": round(item["end_ms"] * 10) - round(item["duration_ms"] * 10),
                                     "end_tick": round(item["end_ms"] * 10), "spikes": item["group_spikes"]["mbon11"]} for item in raw]
            assert cell["response_replay_resolution_hz"] == result["response_replay_resolution_hz"]
        if diagnostic["physical_key"]["phase"] == "pre" and options.get("frozen"):
            assert [event["type"] for event in referenced[:2]] == ["branch_start", "replay_thaw"]
        if options["window"]["end_ms"] == 100.0 or options.get("cs") == 300.0:
            assert diagnostic["boundaries"]["window"] != diagnostic["boundaries"]["final"]
        else:
            assert diagnostic["boundaries"]["window"] == diagnostic["boundaries"]["final"]
    assert owner is records[-1]["engine"]
    assert owner.brain.cursor == diagnostics[-1]["sim_tick"]
    assert owner.brain.checkpoint_state_sha256() == diagnostics[-1]["boundaries"]["final"]["repeat"]["complete_state_sha256"]
    assert not (recorder.path / "run.json").exists()
    assert not any(event["type"] in ("qualification_result", "assay_result") for event in events)
    assert any(event["candidate_projection"]["original_hex"] != "0000000000000000" for event in diagnostics)


@pytest.mark.parametrize("value", [0, 1, None, np.bool_(False), np.bool_(True), "true"])
def test_selected_replay_exact_boolean_before_mutation(selected_caller, value):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    before = recorder.next_sequence, set(recorder._checkpoints)
    def forbidden():
        pytest.fail("Factory called for invalid replay boolean")
    with pytest.raises(ValueError, match="exact boolean"):
        assay._produce_cohorts(forbidden, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=value)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before


@pytest.mark.parametrize("family", ["confirmation", "qualification"])
def test_selected_replay_scalar_or_confirmation_true_before_mutation(selected_caller, family):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    execution["family"] = family
    before = recorder.next_sequence, set(recorder._checkpoints)
    def forbidden():
        pytest.fail("Factory called for confirmation replay request")
    with pytest.raises(ValueError, match="requires qualification|resolution is unavailable"):
        assay._produce_cohorts(forbidden, recorder, execution=execution,
            cohorts=(((101 if family == "confirmation" else 11), "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True,
            confirmation_replay_resolution_hz=0.0)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before


@pytest.mark.parametrize("execution", [None, [], "qualification", {}])
def test_selected_replay_invalid_declaration_before_factory(selected_caller, execution):
    import fly_connectome_sim.experiment.assay as assay
    recorder, _, baseline = selected_caller
    before = recorder.next_sequence
    def forbidden():
        pytest.fail("Factory called for invalid replay declaration")
    with pytest.raises(ValueError):
        assay._produce_cohorts(forbidden, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
    assert recorder.next_sequence == before


def test_selected_replay_static_native_graph_sharing_is_allowed(engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    original, repeat = engine_factory(), engine_factory()
    for name in ("post", "ptr"):
        setattr(repeat.brain, name, getattr(original.brain, name))
    repeat.brain.circuit = original.brain.circuit
    original.identity()
    repeat.identity()
    before = original.brain.checkpoint_state_sha256(), repeat.brain.checkpoint_state_sha256()
    assay._check_replay_independence(original, repeat)
    assert (original.brain.checkpoint_state_sha256(), repeat.brain.checkpoint_state_sha256()) == before


@pytest.mark.parametrize("mutation", ["order", "dtype", "empty", "bounds"])
def test_selected_replay_actual_native_maps_and_w_guard(map_engine_factory, monkeypatch, mutation):
    import fly_connectome_sim.experiment.assay as assay
    engine = map_engine_factory()
    identity = engine.identity()
    state, maps = assay._replay_boundary(engine, identity, 1, start=True)
    assert maps == {"target_indices": [5], "candidate_positions": [0, 3], "candidate_edge_indices": [3, 1]}
    assert state["complete_state_sha256"] == engine.brain.checkpoint_state_sha256()
    if mutation == "order":
        actual = engine.brain._candidate_positions
        monkeypatch.setattr(engine.brain, "_candidate_positions", lambda targets: actual(targets)[::-1])
    elif mutation == "dtype":
        engine.brain.memory_w = engine.brain.memory_w.astype(np.float32)
    elif mutation == "empty":
        object.__setattr__(engine.groups, "mbon11", np.array([], dtype=np.int32))
    else:
        engine.brain.memory_w[0] = np.nextafter(engine.brain.rule_parameters["maximum_fraction"] - 1, np.inf)
    with pytest.raises(ValueError):
        assay._replay_boundary(engine, identity, 1, maps=maps)


@pytest.mark.parametrize("collision", ["repeat_branch", "forward_id"])
def test_selected_replay_last_reserved_name_before_factory(selected_caller, collision):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    last = "selected/23/B/BA/post/70000/C/repeat"
    if collision == "repeat_branch":
        recorder.append({"type": "branch_start", "branch_id": last, "sim_ms": 0.0,
            "parent_branch_id": baseline["origin_branch_id"], "parent_checkpoint_name": baseline["checkpoint_name"],
            "parent_checkpoint_sequence": baseline["checkpoint_sequence"],
            "parent_checkpoint_sha256": baseline["checkpoint_sha256"]})
    else:
        recorder.append({"type": "prior_diagnostic", "branch_id": "qualification/baseline", "sim_ms": 0.0,
                         "replay_id": last})
    before = recorder.next_sequence, set(recorder._checkpoints)
    def forbidden():
        pytest.fail("Factory called before last repeat collision checked")
    with pytest.raises(ValueError, match="collides"):
        assay._produce_cohorts(forbidden, recorder, execution=execution, cohorts=((11, "A", "AB"), (23, "B", "BA")),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before


@pytest.mark.parametrize("alias", ["engine", "brain", "field", "cross_field"])
def test_selected_replay_alias_rejected_before_either_restore(selected_caller, engine_factory, alias):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.engine import FlyEngine
    recorder, execution, baseline = selected_caller
    created, pair_restores, states = [], [], []
    def factory():
        engine = engine_factory()
        if len(created) == 2:
            first = created[1]
            assert not pair_restores  # Both objects are acquired before either restore.
            if alias == "engine":
                engine = first
            elif alias == "brain":
                engine = FlyEngine(brain=first.brain, groups=first.groups)
            else:
                engine.brain.v = first.brain.v if alias == "field" else first.brain.adaptation
            states.extend((native, native.brain.checkpoint_state_sha256(), native.brain.cursor,
                           {name: getattr(native.brain, name).tobytes() for name in ("weight", *native.brain.fields)})
                          for native in (first, engine))
        if len(created) > 0:
            restore = engine.brain.restore
            def traced_restore(path, restore=restore):
                pair_restores.append(Path(path))
                restore(path)
            engine.brain.restore = traced_restore
        created.append(engine)
        return engine
    with pytest.raises(ValueError, match="independent native state|share mutable native state"):
        assay._produce_cohorts(factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
    assert len(created) == 3 and not pair_restores
    for native, state, tick, arrays in states:
        assert native.brain.checkpoint_state_sha256() == state and native.brain.cursor == tick
        assert {name: getattr(native.brain, name).tobytes() for name in arrays} == arrays
    events = list(recorder.validate_prefix().iter_events())
    assert not any("/pre/" in event["branch_id"] for event in events)
    assert not any(event["type"] in ("qualification_evidence", "qualification_replay") for event in events)


@pytest.mark.parametrize("alias", ["producer", "retained", "indeterminate"])
def test_selected_replay_live_owner_buffers_are_guarded(engine_factory, monkeypatch, alias):
    import fly_connectome_sim.experiment.assay as assay
    original, repeat, owner = (engine_factory() for _ in range(3))
    for engine in (original, repeat, owner):
        engine.identity()
    if alias == "producer":
        original.brain.v = owner.brain.adaptation
    elif alias == "retained":
        repeat.brain.adaptation = owner.brain.v
    else:
        def indeterminate(*args, **kwargs):
            raise np.exceptions.TooHardError("bounded alias test")
        monkeypatch.setattr(np, "shares_memory", indeterminate)
    before = [engine.brain.checkpoint_state_sha256() for engine in (original, repeat, owner)]
    with pytest.raises(ValueError, match="share mutable native state|indeterminate"):
        assay._check_replay_independence(original, repeat, owner)
    assert [engine.brain.checkpoint_state_sha256() for engine in (original, repeat, owner)] == before


@pytest.mark.parametrize("mutation", ["state", "clock", "flag", "map", "dtype"])
def test_selected_replay_second_restore_rechecks_both_before_starts(selected_caller, engine_factory, mutation):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    created, restored = [], []
    def factory():
        engine = engine_factory()
        if len(created) == 2:
            first = created[1]
            restore = engine.brain.restore
            def corrupt_first(path):
                assert len(created) == 3
                restore(path)
                restored.append(True)
                if mutation == "state": first.brain.v[3] += 1
                elif mutation == "clock":
                    first.brain.cursor += 1
                    first.brain.sim_ms = first.brain.cursor * 0.1
                elif mutation == "flag": first.brain.weights_frozen = True
                elif mutation == "map": object.__setattr__(first.groups, "mbon11", np.array([3], dtype=np.int32))
                else: first.brain.memory_w = first.brain.memory_w.astype(np.float32)
            engine.brain.restore = corrupt_first
        created.append(engine)
        return engine
    with pytest.raises(ValueError):
        assay._produce_cohorts(factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
    assert restored == [True]
    events = list(recorder.validate_prefix().iter_events())
    assert not any("/pre/" in event["branch_id"] for event in events)


@pytest.mark.parametrize("mutation", ["telemetry", "tail_state", "tail_map"])
def test_selected_replay_mismatch_never_completes_pair(selected_caller, engine_factory, mutation):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    count = 0
    def factory():
        nonlocal count
        engine = engine_factory()
        count += 1
        if count == 3:
            observe = engine.observe
            def corrupt(*args, **kwargs):
                result = observe(*args, **kwargs)
                if mutation == "telemetry": result["turn_hz"] += 1
                elif engine.brain.cursor == 4000:
                    if mutation == "tail_state": engine.brain.v[3] += 1
                    else: object.__setattr__(engine.groups, "mbon11", np.array([3], dtype=np.int32))
                return result
            engine.observe = corrupt
        return engine
    with pytest.raises(ValueError):
        assay._produce_cohorts(factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
    events = list(recorder.validate_prefix().iter_events())
    assert not any(event["type"] == "qualification_replay" for event in events)
    assert sum(event["type"] == "qualification_evidence" for event in events) == (0 if mutation == "telemetry" else 2)
    assert not (recorder.path / "run.json").exists()


@pytest.mark.parametrize("failure", ["append", "flush", "count", "diagnostic"])
def test_selected_replay_durable_failure_returns_no_owner(selected_caller, engine_factory, monkeypatch, failure):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    append = recorder.append
    stream = recorder._stream
    class FailingFlush:
        fail = False
        def __getattr__(self, name):
            return getattr(stream, name)
        def write(self, value):
            self.fail = b'/pre/A/repeat' in value and b'"type":"observe"' in value
            return stream.write(value)
        def flush(self):
            stream.flush()
            if self.fail:
                raise OSError("selected replay flush failure")
    if failure == "flush":
        monkeypatch.setattr(recorder, "_stream", FailingFlush())
    def fail(event):
        target = event["branch_id"] == "selected/11/A/AB/pre/A/repeat"
        if target and event["type"] == "observe" and failure == "append":
            raise OSError("selected replay append failure")
        if event["type"] == "qualification_replay" and failure == "diagnostic":
            raise OSError("selected replay diagnostic failure")
        result = append(event)
        if target and event["type"] == "branch_start" and failure == "count":
            append({"type": "prior_diagnostic", "branch_id": "qualification/baseline", "sim_ms": 0.0})
        return result
    monkeypatch.setattr(recorder, "append", fail)
    with pytest.raises((OSError, ValueError), match="selected replay|Event append failed|reference boundary changed"):
        assay._produce_cohorts(engine_factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
    events = [json.loads(line) for line in (recorder.path / "events.jsonl").read_bytes().splitlines()]
    assert not any(event["type"] in ("qualification_replay", "qualification_result", "assay_result") for event in events)
    assert not (recorder.path / "run.json").exists()
    if failure == "flush":
        assert recorder._failed
        assert events[-1]["branch_id"].endswith("/pre/A/repeat") and events[-1]["type"] == "observe"
        monkeypatch.setattr(recorder, "_stream", stream)


def test_selected_replay_pair_source_rehashed_after_both_factories(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    path = recorder.path / "checkpoints" / "brain-before.npz"
    original = path.read_bytes()
    count, restores = 0, []
    def factory():
        nonlocal count
        engine = engine_factory()
        count += 1
        if count == 3:
            path.write_bytes(original + b"changed")
        if count > 1:
            restore = engine.brain.restore
            def traced(path):
                restores.append(Path(path))
                restore(path)
            engine.brain.restore = traced
        return engine
    try:
        with pytest.raises(ValueError, match="Baseline source bytes changed"):
            assay._produce_cohorts(factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
                conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
        assert count == 3 and not restores
        path.write_bytes(original)
        assert not any("/pre/" in event["branch_id"] for event in recorder.validate_prefix().iter_events())
    finally:
        path.write_bytes(original)


def test_selected_replay_scratch_checkpoint_cannot_replace_anchor_parent(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    mutations, returned = [], []
    def factory():
        engine = engine_factory()
        checkpoint = engine.brain.checkpoint
        def mutate_before_scratch(path):
            if Path(path).name == "retained.npz" and not mutations:
                anchors = [event for event in recorder.validate_prefix().iter_events() if event["type"] == "state_anchor"]
                assert len(anchors) == 1
                anchor = anchors[0]
                before = engine.brain.checkpoint_state_sha256()
                clock = engine.brain.cursor, engine.brain.sim_ms
                assert before == anchor["complete_state_sha256"] and clock[0] == anchor["sim_tick"]
                engine.brain.v[3] += 1  # Valid native state, unchanged actual clock.
                engine.brain.candidate_state_digests(engine.groups.mbon11)
                after = engine.brain.checkpoint_state_sha256()
                assert after != before and (engine.brain.cursor, engine.brain.sim_ms) == clock
                mutations.append((anchor["state_anchor_sha256"], before, after, clock[0]))
            return checkpoint(path)
        engine.brain.checkpoint = mutate_before_scratch
        return engine
    with pytest.raises(ValueError, match="Retained replay parent state mismatch"):
        returned.append(assay._produce_cohorts(factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True))
        # On the unfixed producer, authenticate the actual contradictory output
        # before pytest reports DID NOT RAISE; no native-history proof is created.
        events = list(recorder.validate_prefix().iter_events())
        admitted = [event for event in events if event["type"] == "qualification_replay"
                    and event.get("parent_state_anchor_sha256") == mutations[0][0]]
        assert len(admitted) == 3
        assert all(event["boundaries"]["start"]["original"]["complete_state_sha256"] == mutations[0][2]
                   and event["boundaries"]["start"]["original"]["complete_state_sha256"] != mutations[0][1]
                   for event in admitted)
        print("admitted contradictory POST diagnostics:", len(admitted), "anchor:", mutations[0][1],
              "actual changed parent:", mutations[0][2], "unchanged tick:", mutations[0][3])
    assert len(mutations) == 1 and not returned
    events = list(recorder.validate_prefix().iter_events())
    assert len([event for event in events if event["type"] == "qualification_replay"]) == 3  # PRE only.
    assert not any("/post/" in event["branch_id"] for event in events)
    assert not (recorder.path / "run.json").exists()


def test_selected_replay_releases_obsolete_native_owners(selected_caller, engine_factory):
    import weakref
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    references = []
    def factory():
        if len(references) in (1, 3, 5, 8, 10, 12, 15, 17, 19):
            assert all(reference() is None for reference in references)
        engine = engine_factory()
        references.append(weakref.ref(engine))
        return engine
    owner = assay._produce_cohorts(factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
        conditions=("paired",), baseline_occurrence=baseline, namespace=True, measure_replay=True)
    assert len(references) == 21
    assert all(reference() is None for reference in references[:-1])
    assert references[-1]() is owner


def test_selected_replay_false_preserves_training_owner_trace(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    records = []
    owner = assay._produce_cohorts(_tracked_factory(engine_factory, records), recorder, execution=execution,
        cohorts=((11, "A", "AB"),), conditions=("paired",), baseline_occurrence=baseline,
        namespace=True, measure_replay=False)
    assert len(records) == 12 and owner is records[0]["engine"]
    assert owner.brain.cursor == 111000
    events = list(recorder.validate_prefix().iter_events())
    training = next(event for event in events if event["type"] == "qualification_training")
    assert owner.brain.candidate_state_digests(owner.groups.mbon11) == {
        name: training[name] for name in ("candidate_memory_sha256", "noncandidate_state_sha256")}
    assert len([event for event in events if event["type"] == "qualification_evidence"]) == 12
    assert not any(event["type"] == "qualification_replay" or event["branch_id"].endswith("/repeat") for event in events)
    assert all("response_replay_resolution_hz" not in event and "replay_id" not in event
               for event in events if event["type"] == "qualification_evidence")
    assert [event["sequence"] for event in events] == list(range(len(events)))
    for record in records[1:4] + records[5:8] + records[9:12]:
        assert len(record["restores"]) == 1
        assert record["calls"][0]["state"] == record["restores"][0]["state"]
        assert [call["duration"] for call in record["calls"]] == [100.0, 100.0, 200.0]
        assert all(call["kwargs"] == {"stimulation": None, "learning": False} for call in record["calls"])


@pytest.mark.parametrize("mutation", [
    "family", "seeds", "boolean_seed", "population", "candidate", "extra", "window", "retention",
    "last_input", "last_factor", "duplicates", "conditions", "dependencies", "namespace",
    "replay_numpy", "replay_lookalike", "resolution", "baseline_name", "baseline_sequence",
    "baseline_origin", "baseline_tick", "baseline_alias", "baseline_bytes", "factory_bytes",
    "black_missing", "black_hash", "late_branch_collision", "late_checkpoint_collision", "closed", "failed",
])
def test_selected_preflight_refuses_without_component_writes(selected_caller, engine_factory, monkeypatch, mutation):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    cohorts, conditions = [(11, "A", "AB"), (23, "B", "BA")], ("paired",)
    options = {"namespace": True}
    factory = engine_factory
    if mutation == "family": execution["family"] = "unknown"
    elif mutation == "seeds": execution["seeds"] = [11, 113]
    elif mutation == "boolean_seed": cohorts[-1] = (True, "B", "BA")
    elif mutation == "population": execution["mbon11_population_size"] = True
    elif mutation == "candidate": execution["candidate_identity"] = "other/v1"
    elif mutation == "extra": execution["trusted"] = True
    elif mutation == "window": execution["response_window"]["end_ms"] = True
    elif mutation == "retention": execution["retention_times_ms"] = [10000, 60000]
    elif mutation == "last_input": execution["input_sha256"]["23"]["A"] = "0" * 64
    elif mutation == "last_factor": cohorts[-1] = (23, "C", "BA")
    elif mutation == "duplicates": cohorts[-1] = cohorts[0]
    elif mutation == "conditions": conditions = ("paired", "paired")
    elif mutation == "dependencies": conditions = ("paired", "necessity")
    elif mutation == "namespace": options["namespace"] = False
    elif mutation == "replay_numpy": options["measure_replay"] = np.bool_(True)
    elif mutation == "replay_lookalike": options["measure_replay"] = 0
    elif mutation == "resolution": options["confirmation_replay_resolution_hz"] = 0.0
    elif mutation == "baseline_name": baseline["checkpoint_name"] = "missing.npz"
    elif mutation == "baseline_sequence": baseline["checkpoint_sequence"] = 1
    elif mutation == "baseline_origin": baseline["origin_branch_id"] = "other"
    elif mutation == "baseline_tick": baseline["sim_tick"] = True
    elif mutation == "baseline_alias":
        recorder.ingest_checkpoint("alias.npz", recorder.path / "checkpoints/brain-before.npz",
                                   origin_branch_id="qualification/baseline")
        recorder.append({"type": "qualification_checkpoint", "branch_id": "qualification/baseline",
                         "sim_ms": 0.0, "sim_tick": 0, "checkpoint_name": "alias.npz"})
        baseline["checkpoint_name"] = "alias.npz"
    elif mutation in ("baseline_bytes", "factory_bytes"):
        path = recorder.path / "checkpoints/brain-before.npz"
        if mutation == "baseline_bytes": path.write_bytes(path.read_bytes() + b"changed")
        else:
            def factory():
                engine = engine_factory()
                path.write_bytes(path.read_bytes() + b"changed")
                return engine
    elif mutation == "black_missing": del recorder.metadata["black_input"]
    elif mutation == "black_hash": recorder.metadata["black_input"]["input_sha256"] = "0" * 64
    elif mutation == "late_branch_collision":
        recorder.append({"type": "branch_start", "branch_id": "selected/23/B/BA/post/70000/C", "sim_ms": 0.0,
                         "parent_branch_id": baseline["origin_branch_id"],
                         "parent_checkpoint_name": baseline["checkpoint_name"],
                         "parent_checkpoint_sequence": baseline["checkpoint_sequence"],
                         "parent_checkpoint_sha256": baseline["checkpoint_sha256"]})
    elif mutation == "late_checkpoint_collision":
        name = "selected-23-B-BA-training-end.npz"
        recorder.ingest_checkpoint(name, recorder.path / "checkpoints/brain-before.npz",
                                   origin_branch_id="qualification/baseline")
        recorder.append({"type": "checkpoint", "branch_id": "qualification/baseline",
                         "sim_ms": 0.0, "sim_tick": 0, "checkpoint_name": name})
    elif mutation == "closed": recorder.__exit__(RuntimeError, RuntimeError(), None)
    elif mutation == "failed": recorder._failed = True
    before = recorder.next_sequence, set(recorder._checkpoints)
    calls = []
    def traced_factory():
        engine = factory()
        observe = engine.observe
        def traced(*args, **kwargs):
            calls.append(1)
            return observe(*args, **kwargs)
        engine.observe = traced
        return engine
    with pytest.raises(ValueError):
        assay._produce_cohorts(traced_factory, recorder, execution=execution, cohorts=cohorts,
            conditions=conditions, baseline_occurrence=baseline, **options)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before
    assert not calls


def test_source_lookup_streams_without_retaining_history(native_transfer_sources, engine_factory, monkeypatch):
    import weakref
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.recorder import ValidatedPrefix
    recorder, sources, identity = native_transfer_sources
    for _ in range(20):
        recorder.append({"type": "diagnostic", "branch_id": "root", "sim_ms": 0.3,
                         "payload": list(range(100))})
    iterate = ValidatedPrefix.iter_events
    live, visited = [], []
    class TrackedEvent(dict):
        pass
    def bounded(self):
        for event in iterate(self):
            live[:] = [item for item in live if item() is not None]
            assert len(live) <= 2, "raw prefix history retained"
            wrapped = TrackedEvent(event)
            live.append(weakref.ref(wrapped))
            visited.append(event["sequence"])
            yield wrapped
    monkeypatch.setattr(ValidatedPrefix, "iter_events", bounded)
    restored = assay._restore_training_source(recorder, *sources[0], engine_factory, identity, 1)
    assert restored.brain.cursor == 3
    # Prefix construction and source authentication each fully stream these bytes.
    assert visited == list(range(recorder.next_sequence)) * 2


def test_source_lookup_rejects_late_duplicate_descriptor(native_transfer_sources, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, sources, identity = native_transfer_sources
    recorder.append(sources[0][1])
    with pytest.raises(ValueError, match="descriptor"):
        assay._restore_training_source(recorder, *sources[0], engine_factory, identity, 1)


def _check_selected_inventory(prefix, execution, cohorts):
    """Check literal selected roles, occurrence positions and logical factor cells."""
    from fly_connectome_sim.experiment.analysis import _validate_response, _validate_training
    conditions = ("paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired",
                  "matched_reference", "necessity", "sufficiency", "sham")
    acquisitions = conditions[:5]
    events = list(prefix.iter_events())
    training = [event for event in events if event["type"] == "qualification_training"]
    interventions = [event for event in events if event["type"] == "assay_intervention"]
    responses = [event for event in events if event["type"] == "qualification_evidence"]
    anchors = [event for event in events if event["type"] == "state_anchor"]
    assert [event["sequence"] for event in events] == list(range(len(events)))
    assert (len(training), len(interventions), len(anchors), len(responses)) == tuple(
        count * len(cohorts) for count in (5, 3, 16, 96))
    checkpoint_roles = ("training-end", "frozen_plasticity-training-end", "no_external_dan-training-end",
                        "temporally_unpaired-training-end", "matched-reference-training-end",
                        "necessity-post", "sufficiency-post", "sham-post")
    assert set(prefix.manifest["checkpoints"]) == {"brain-before.npz"} | {
        f"selected-{seed}-{paired}-{order}-{role}.npz"
        for seed, paired, order in cohorts for role in checkpoint_roles}
    expected_branches = {"qualification/baseline", "prior-native"}
    for seed, paired, order in cohorts:
        base = f"selected/{seed}/{paired}/{order}"
        expected_branches.update(f"{base}/{condition}/training" for condition in acquisitions)
        expected_branches.update(f"{base}/{condition}/intervention" for condition in conditions[5:])
        expected_branches.update(f"{base}/pre/{stimulus}" for stimulus in ("A", "B", "C"))
        for condition in conditions:
            path = base if condition == "paired" else f"{base}/{condition}"
            for retention in (10000, 70000):
                expected_branches.add(f"{path}/retention/{retention}")
                expected_branches.update(f"{path}/post/{retention}/{stimulus}" for stimulus in ("A", "B", "C"))
    assert {event["branch_id"] for event in events} == expected_branches
    assert {(event["seed"], event["paired_identity"], event["presentation_order"], event["condition"])
            for event in training} == {(*cohort, condition) for cohort in cohorts for condition in acquisitions}
    assert {(event["seed"], event["paired_identity"], event["presentation_order"], event["retention_ms"],
             event["condition"], event["phase"], event["stimulus"]) for event in responses} == {
        (*cohort, retention, condition, phase, stimulus)
        for cohort in cohorts for retention in (10000, 70000) for condition in conditions
        for phase in ("pre", "post") for stimulus in ("A", "B", "C")}
    assert len({event["branch_id"] for event in responses if event["phase"] == "pre"}) == 3 * len(cohorts)
    for event in training:
        _validate_training(event, execution, (11, 23), "qualification")
    for event in responses:
        _validate_response(event, execution, (11, 23), "qualification_evidence")
        assert "response_replay_resolution_hz" not in event and "replay_id" not in event
    for event in events:
        if event["type"] == "checkpoint":
            entry = prefix.manifest["checkpoints"][event["checkpoint_name"]]
            assert entry["checkpoint_sequence"] == event["sequence"]
            assert entry["sha256"] == event["checkpoint_sha256"]
            assert entry["sim_tick"] == event["sim_tick"]
        if "parent_checkpoint_sequence" in event:
            source = events[event["parent_checkpoint_sequence"]]
            assert source["checkpoint_name"] == event["parent_checkpoint_name"]
            assert source["checkpoint_sha256"] == event["parent_checkpoint_sha256"]
        if event["type"] == "state_anchor":
            source = events[event["source_occurrence"]["checkpoint_sequence"]]
            assert source["checkpoint_sha256"] == event["source_occurrence"]["checkpoint_sha256"]
    assert not any(event["type"] in ("qualification_result", "assay_result", "qualification_replay") for event in events)
    return events


@pytest.mark.parametrize("cohort", [(11, "A", "AB"), (23, "B", "BA")])
def test_selected_complete_native_cohort_is_independent_and_owner_bounded(
        selected_caller, engine_factory, monkeypatch, cohort):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.analysis import CONDITIONS
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix
    recorder, execution, baseline = selected_caller
    def forbidden(*args, **kwargs):
        raise AssertionError("Production component crossed lifecycle/frozen boundary")
    monkeypatch.setattr(recorder, "close", forbidden)
    monkeypatch.setattr(assay.FrozenAssayConfig, "from_dict", forbidden)
    monkeypatch.setattr(assay, "build_assay_result", forbidden)
    records = []
    assay._produce_cohorts(_tracked_factory(engine_factory, records), recorder, execution=execution,
        cohorts=(cohort,), conditions=CONDITIONS, baseline_occurrence=baseline, namespace=True)
    events = _check_selected_inventory(recorder.validate_prefix(), execution, (cohort,))
    assert not (recorder.path / "run.json").exists()
    assert sum(bool(record["replacements"]) for record in records) == 3
    for record in records:
        for replacement in record["replacements"]:
            assert replacement["before_clock"] == replacement["after_clock"]
            assert np.array_equal(replacement["before"]["v"], replacement["after"]["v"])
    trials = [record for record in records if record["restores"]
              and record["restores"][0]["path"].name == "retained.npz"]
    assert len(trials) == 48
    assert len({id(record["engine"]) for record in trials}) == 48
    for record in trials:
        assert len(record["restores"]) == 1
        assert record["calls"][0]["state"] == record["restores"][0]["state"]
        assert all(call["kwargs"] == {"stimulation": None, "learning": False} for call in record["calls"])
    for event in events:
        if event["type"] == "assay_intervention":
            assert event["recipient_candidate_memory_after_sha256"] == event["donor_candidate_memory_sha256"]
            assert event["noncandidate_state_before_sha256"] == event["noncandidate_state_after_sha256"]
            if event["condition"] == "sham":
                assert event["recipient_candidate_memory_before_sha256"] == event["recipient_candidate_memory_after_sha256"]
    verified = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    assert len(verified.replay_attested_state_anchors) == 16


@pytest.mark.skipif(os.environ.get("FLY_CONNECTOME_SIM_FULL_TEST") != "1", reason="opt-in complete selected matrix")
def test_selected_all_eight_native_cohorts(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.analysis import CONDITIONS
    recorder, execution, baseline = selected_caller
    cohorts = tuple((seed, paired, order) for seed in (11, 23) for paired in ("A", "B") for order in ("AB", "BA"))
    assay._produce_cohorts(engine_factory, recorder, execution=execution, cohorts=cohorts,
        conditions=CONDITIONS, baseline_occurrence=baseline, namespace=True)
    _check_selected_inventory(recorder.validate_prefix(), execution, cohorts)
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix
    verified = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    assert len(verified.replay_attested_state_anchors) == 128
    assert not (recorder.path / "run.json").exists()


def _check_selected_replay_matrix(selected_caller, engine_factory, cohorts):
    """Test-only native/byte oracle; black-anchor attestation is not response-history proof."""
    import weakref
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.engine import _rgb_input_sha256
    from fly_connectome_sim.experiment.analysis import (
        _compare_replay_operations, _compare_selected_replay, _decode_candidate_w_pair,
        _selected_replay_observation, _validate_intervention, _validate_response, _validate_training,
    )
    from fly_connectome_sim.experiment.qualification import _response_rate
    from fly_connectome_sim.experiment.recorder import _canonical, _scientific, verify_replay_prefix

    recorder, execution, baseline = selected_caller
    conditions = ("paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired",
                  "matched_reference", "necessity", "sufficiency", "sham")
    roles = ("training-end", "frozen_plasticity-training-end", "no_external_dan-training-end",
             "temporally_unpaired-training-end", "matched-reference-training-end",
             "necessity-post", "sufficiency-post", "sham-post")
    expected_counts = {1: (51, 96, 130, 16, 9), 8: (408, 768, 1033, 128, 65)}[len(cohorts)]
    assert execution["selected_configuration"] == {
        "cs_duration_ms": 100.0, "dan_onset_ms": 0.0, "post_pair_gap_ms": 500.0}
    assert execution["response_window"] == {"start_ms": 0.0, "end_ms": 100.0}
    assert execution["retention_times_ms"] == [10000, 70000]
    physical, slots, starts, anchor_names, source_names = [], [None], [], [], {}
    for seed, paired, order in cohorts:
        base = f"selected/{seed}/{paired}/{order}"
        starts.extend(f"{base}/{condition}/training" for condition in conditions[:5])
        starts.extend(f"{base}/{condition}/intervention" for condition in conditions[5:])
        # Literal factory roles: five acquisitions, six donor/recipient restores.
        slots.extend([None] * 11)
        for condition, role in zip(conditions, roles):
            source_names[seed, paired, order, condition] = f"selected-{seed}-{paired}-{order}-{role}.npz"
        for stimulus in ("A", "B", "C"):
            branch = f"{base}/pre/{stimulus}"
            physical.append(({"seed": seed, "paired_identity": paired, "presentation_order": order,
                              "phase": "pre", "stimulus": stimulus}, branch))
            starts.extend((branch, branch + "/repeat"))
            slots.extend((branch, branch + "/repeat"))
        for condition in conditions:
            path = base if condition == "paired" else f"{base}/{condition}"
            for retention in (10000, 70000):
                anchor_names.append(f"{path}/retention/{retention}")
                starts.append(anchor_names[-1])
                slots.append(None)  # One retained owner, followed by three independent pairs.
                for stimulus in ("A", "B", "C"):
                    branch = f"{path}/post/{retention}/{stimulus}"
                    physical.append(({"seed": seed, "paired_identity": paired, "presentation_order": order,
                        "phase": "post", "condition": condition, "retention_ms": retention, "stimulus": stimulus}, branch))
                    starts.extend((branch, branch + "/repeat"))
                    slots.extend((branch, branch + "/repeat"))
    assert len(physical) == expected_counts[0] and len(slots) == expected_counts[2]
    records, baseline_record, layout = {}, {}, {}
    production_count = 0

    def factory():
        nonlocal production_count
        assert production_count < len(slots), "Unexpected extra production factory"
        branch = slots[production_count]
        production_count += 1
        engine = engine_factory()
        engine.identity()
        def capture(start=False):
            brain = engine.brain
            positions = brain._candidate_positions(engine.groups.mbon11)
            maps = {"target_indices": engine.groups.mbon11.tolist(), "candidate_positions": positions.tolist(),
                    "candidate_edge_indices": brain.circuit["edges"][positions].tolist()}
            assert maps == layout["maps"]
            assert brain.memory_w.dtype.str == "<f8" and brain.memory_w.ndim == 1
            state = {"sim_tick": brain.cursor, "complete_state_sha256": brain.checkpoint_state_sha256()}
            state.update({"weights_frozen": brain.weights_frozen} if start else brain.candidate_state_digests(engine.groups.mbon11))
            return state
        if production_count == 1:
            positions = engine.brain._candidate_positions(engine.groups.mbon11)
            layout.update(maps={"target_indices": engine.groups.mbon11.tolist(), "candidate_positions": positions.tolist(),
                "candidate_edge_indices": engine.brain.circuit["edges"][positions].tolist()},
                n=engine.brain.n, memory_count=len(engine.brain.memory_w), edge_count=len(engine.brain.weight),
                lower=engine.brain.rule_parameters["minimum_fraction"] - 1,
                upper=engine.brain.rule_parameters["maximum_fraction"] - 1)
        if branch is not None or production_count == 1:
            record = baseline_record if branch is None else {"engine": weakref.ref(engine), "calls": [], "restores": 0}
            if branch is not None:
                assert branch not in records
                records[branch] = record
            restore = engine.brain.restore
            def restored(path):
                restore(path)
                record.update(path=Path(path), start=capture(start=True))
                record["restores"] = record.get("restores", 0) + 1
                del engine.brain.restore  # Do not retain a bound wrapper/engine after this native restore.
            engine.brain.restore = restored
        if branch is not None:
            observe = engine.observe
            def observed(frame, duration, **kwargs):
                start = engine.brain.cursor
                result = observe(frame, duration, **kwargs)
                assert frame.shape == (32, 32, 3) and frame.dtype == np.uint8
                record["calls"].append({"start": start, "end": engine.brain.cursor, "duration": duration,
                    "input_sha256": _rgb_input_sha256(frame), "kwargs": dict(kwargs),
                    "telemetry_sha256": sha256(_canonical(_scientific(result))).hexdigest()})
                if engine.brain.cursor == record["start"]["sim_tick"] + 2000:
                    record["window"] = capture()
                    record["window_w_hex"] = engine.brain.memory_w[
                        engine.brain._candidate_positions(engine.groups.mbon11)].tobytes().hex()
                if engine.brain.cursor == record["start"]["sim_tick"] + 4000:
                    record["final"] = capture()
                    del engine.observe
                return result
            engine.observe = observed
        return engine

    owner = assay._produce_cohorts(factory, recorder, execution=execution, cohorts=cohorts, conditions=conditions,
        baseline_occurrence=baseline, namespace=True, measure_replay=True)
    assert production_count == expected_counts[2]  # BEFORE independent raw-factory native verification.
    assert baseline_record["restores"] == 1 and baseline_record["path"].name == "brain-before.npz"
    assert set(records) == {branch for _, original in physical for branch in (original, original + "/repeat")}
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    manifest = prefix.manifest
    attested_anchors = prefix.replay_attested_state_anchors
    events = list(prefix.iter_events())  # One test-only actual-byte lookup, not a production f evaluator.
    assert [event["sequence"] for event in events] == list(range(len(events)))
    by_branch = {}
    for event in events:
        by_branch.setdefault(event["branch_id"], []).append(event)
    diagnostics = [event for event in events if event["type"] == "qualification_replay"]
    responses = [event for event in events if event["type"] == "qualification_evidence"]
    anchors = [event for event in events if event["type"] == "state_anchor"]
    checkpoints = [event for event in events if event["type"] in ("checkpoint", "qualification_checkpoint")]
    assert (len(diagnostics), len(responses), production_count, len(anchors), len(checkpoints)) == expected_counts
    assert [event["physical_key"] for event in diagnostics] == [key for key, _ in physical]
    assert [event["original_branch_id"] for event in diagnostics] == [branch for _, branch in physical]
    assert [event["replay_id"] for event in diagnostics] == [branch + "/repeat" for _, branch in physical]
    actual_starts = [event["branch_id"] for event in events if event["type"] in ("branch_start", "fork")
                     and event["branch_id"].startswith("selected/")]
    assert actual_starts == starts and len(set(starts)) == len(starts)
    assert set(by_branch) == {"qualification/baseline", "prior-native", *starts}
    assert [event["anchor_id"] for event in anchors] == anchor_names
    assert set(attested_anchors) == set(manifest["state_anchors"])
    assert len(attested_anchors) == expected_counts[3]  # Black-retention proof only.
    assert set(manifest["checkpoints"]) == {"brain-before.npz", *source_names.values()}
    checkpoint_by_name = {event["checkpoint_name"]: event for event in checkpoints}
    assert len(checkpoint_by_name) == len(checkpoints)
    def occurrence(name):
        event = checkpoint_by_name[name]
        index = manifest["checkpoints"][name]
        assert (index["checkpoint_sequence"], index["origin_branch_id"], index["sha256"], index["sim_tick"]) == (
            event["sequence"], event["branch_id"], event["checkpoint_sha256"], event["sim_tick"])
        return {"checkpoint_name": name, "checkpoint_sha256": event["checkpoint_sha256"],
                "origin_branch_id": event["branch_id"], "checkpoint_sequence": event["sequence"], "sim_tick": event["sim_tick"]}
    def parent(source):
        return {"parent_branch_id": source["origin_branch_id"], "parent_checkpoint_name": source["checkpoint_name"],
                "parent_checkpoint_sequence": source["checkpoint_sequence"], "parent_checkpoint_sha256": source["checkpoint_sha256"]}
    assert occurrence("brain-before.npz") == baseline
    training = [event for event in events if event["type"] == "qualification_training"]
    interventions = [event for event in events if event["type"] == "assay_intervention"]
    assert len(training) == 5 * len(cohorts) and len(interventions) == 3 * len(cohorts)
    training_by_id = {event["training_id"]: event for event in training}
    intervention_by_id = {event["intervention_id"]: event for event in interventions}
    assert list(training_by_id) == [f"selected/{s}/{p}/{o}/{c}/training" for s, p, o in cohorts for c in conditions[:5]]
    assert list(intervention_by_id) == [f"selected/{s}/{p}/{o}/{c}/intervention" for s, p, o in cohorts for c in conditions[5:]]
    sources = {}
    for factors, name in source_names.items():
        seed, paired, order, condition = factors
        source = occurrence(name)
        sources[factors] = source
        base = f"selected/{seed}/{paired}/{order}"
        assert source["origin_branch_id"] == f"{base}/{condition}/" + ("training" if condition in conditions[:5] else "intervention")
        checkpoint = checkpoint_by_name[name]
        if condition in conditions[:5]:
            descriptor = training_by_id[source["origin_branch_id"]]
            _validate_training(descriptor, execution, (11, 23), "qualification")
            assert descriptor["training_end_tick"] == source["sim_tick"]
            assert descriptor["training_end_checkpoint_sha256"] == source["checkpoint_sha256"]
            binding = parent(baseline)
        else:
            descriptor = intervention_by_id[source["origin_branch_id"]]
            _validate_intervention(descriptor, execution, (11, 23))
            donor = "matched_reference" if condition == "necessity" else "paired"
            recipient = "matched_reference" if condition == "sufficiency" else "paired"
            donor_source = occurrence(source_names[seed, paired, order, donor])
            recipient_source = occurrence(source_names[seed, paired, order, recipient])
            assert descriptor["donor_training_id"] == donor_source["origin_branch_id"]
            assert descriptor["recipient_training_id"] == recipient_source["origin_branch_id"]
            assert descriptor["donor_checkpoint_sha256"] == donor_source["checkpoint_sha256"]
            assert descriptor["recipient_checkpoint_sha256"] == recipient_source["checkpoint_sha256"]
            assert descriptor["post_intervention_checkpoint_sha256"] == source["checkpoint_sha256"]
            assert descriptor["donor_training_end_tick"] == descriptor["recipient_training_end_tick"] == source["sim_tick"]
            assert source["sim_tick"] == recipient_source["sim_tick"] == donor_source["sim_tick"]
            binding = parent(recipient_source)
            assert all(descriptor[key] == value for key, value in binding.items())
        assert all(checkpoint[key] == value for key, value in binding.items())
    assert {(event["seed"], event["paired_identity"], event["presentation_order"], event["condition"],
             event["retention_ms"], event["phase"], event["stimulus"]) for event in responses} == {
        (*cohort, condition, retention, phase, stimulus) for cohort in cohorts for condition in conditions
        for retention in (10000, 70000) for phase in ("pre", "post") for stimulus in ("A", "B", "C")}
    anchor_by_name = {anchor["anchor_id"]: anchor for anchor in anchors}
    for anchor in anchors:
        manifest_anchor = manifest["state_anchors"][anchor["state_anchor_sha256"]]
        assert manifest_anchor["event_sequence"] == anchor["sequence"]
        assert all(anchor[key] == value for key, value in manifest_anchor.items() if key != "event_sequence")
    # These nine samples cover every cohort, every intervention×T combination,
    # ordinary routes and PRE. The exhaustive lookup oracle still checks ALL408.
    samples = {(11, "A", "AB", "necessity", 10000), (11, "A", "BA", "necessity", 70000),
               (11, "B", "AB", "sufficiency", 10000), (11, "B", "BA", "sufficiency", 70000),
               (23, "A", "AB", "sham", 10000), (23, "A", "BA", "sham", 70000),
               (23, "B", "AB", "paired", 10000), (23, "B", "BA", "matched_reference", 70000)}
    selected_samples = set()
    claimed_references = set()
    route_fields = ("training_id", "association_t0_tick", "retention_reference_tick", "training_start_tick",
        "training_end_tick", "last_visual_end_tick", "last_external_dan_end_tick", "unpaired_nearest_cs_boundary_ticks",
        "training_visual_exposure_ticks", "training_end_checkpoint_sha256")
    for diagnostic, (key, branch) in zip(diagnostics, physical):
        factors = key["seed"], key["paired_identity"], key["presentation_order"]
        base = "selected/" + "/".join(str(value) for value in factors)
        if key["phase"] == "pre":
            source, binding = baseline, parent(baseline)
            start = baseline_record["start"]
        else:
            source = sources[*factors, key["condition"]]
            path = base if key["condition"] == "paired" else base + "/" + key["condition"]
            anchor = anchor_by_name[f"{path}/retention/{key['retention_ms']}"]
            recipient = "matched_reference" if key["condition"] == "sufficiency" else (
                "paired" if key["condition"] in conditions[5:] else key["condition"])
            descriptor = training_by_id[f"{base}/{recipient}/training"]
            assert anchor["source_occurrence"] == source
            assert anchor["sim_tick"] == descriptor["retention_reference_tick"] + key["retention_ms"] * 10 - 1000
            start = {"sim_tick": anchor["sim_tick"], "complete_state_sha256": anchor["complete_state_sha256"], "weights_frozen": False}
            binding = {"parent_branch_id": anchor["origin_branch_id"], "parent_state_anchor_sha256": anchor["state_anchor_sha256"]}
        assert diagnostic["source_occurrence"] == source
        assert diagnostic["boundaries"]["start"] == {"original": start, "repeat": start}
        assert diagnostic["cs_onset_tick"] == start["sim_tick"] + 1000
        assert diagnostic["sim_tick"] == start["sim_tick"] + 4000
        assert all(diagnostic[name] == value for name, value in binding.items())
        assert diagnostic["response_window"] == execution["response_window"]
        assert diagnostic["engine_identity_sha256"] == execution["engine_identity"]["sha256"]
        assert diagnostic["population_size"] == execution["mbon11_population_size"]
        segments = [(start["sim_tick"], start["sim_tick"] + 1000, None),
                    (start["sim_tick"] + 1000, start["sim_tick"] + 2000, key["stimulus"]),
                    (start["sim_tick"] + 2000, start["sim_tick"] + 4000, None)]
        operations, window_bins, ppl_counts, window_sequences = {}, {}, {}, {}
        pair_references = set()
        for side, native_branch in (("original", branch), ("repeat", branch + "/repeat")):
            record = records[native_branch]
            assert record["restores"] == 1 and record["start"] == start
            assert record["path"].name == ("brain-before.npz" if key["phase"] == "pre" else "retained.npz")
            if key["phase"] == "post":
                assert not record["path"].exists()
            assert diagnostic["boundaries"]["window"][side] == record["window"]
            assert diagnostic["boundaries"]["final"][side] == record["final"]
            assert diagnostic["candidate_projection"][side + "_hex"] == record["window_w_hex"]
            references = diagnostic["operations"][side]
            assert len(references) == 4 and [ref["sequence"] for ref in references] == sorted(ref["sequence"] for ref in references)
            operations[side] = [events[ref["sequence"]] for ref in references]
            for event, reference in zip(operations[side], references):
                assert event["branch_id"] == native_branch and event["scientific_sha256"] == reference["scientific_sha256"]
                assert reference["sequence"] < diagnostic["sequence"] and reference["sequence"] not in claimed_references
                claimed_references.add(reference["sequence"])
                pair_references.add(reference["sequence"])
            first = operations[side][0]
            assert first["type"] == "branch_start" and first["sim_ms"] == start["sim_tick"] / 10
            assert all(first[name] == value for name, value in binding.items())
            assert len(record["calls"]) == 3
            window_bins[side], ppl_counts[side] = [], 0
            for event, call, segment in zip(operations[side][1:], record["calls"], segments):
                assert (call["start"], call["end"]) == segment[:2]
                assert call["duration"] == (segment[1] - segment[0]) / 10 <= 500
                assert call["kwargs"] == {"stimulation": None, "learning": False}
                assert call["input_sha256"] == execution["input_sha256"][str(key["seed"])][segment[2] or "black"]
                assert sha256(_canonical(_scientific(event["telemetry"]))).hexdigest() == call["telemetry_sha256"]
                bins, ppl = _selected_replay_observation(event, segment, diagnostic, execution, layout["n"])
                window_bins[side].extend(bins)
                ppl_counts[side] += ppl
                if event["end_tick"] == start["sim_tick"] + 2000:
                    window_sequences[side] = event["sequence"]
        for index, (original, repeated) in enumerate(zip(operations["original"], operations["repeat"])):
            _compare_replay_operations(original, repeated)
            assert original["sequence"] < repeated["sequence"]
            if index:
                assert operations["repeat"][index - 1]["sequence"] < original["sequence"]
        assert window_bins["original"] == window_bins["repeat"] and window_bins["original"]
        first, second = _decode_candidate_w_pair(diagnostic["candidate_projection"], expected_maps=layout["maps"],
            **{name: layout[name] for name in ("n", "memory_count", "edge_count", "lower", "upper")})
        assert first.tobytes() == second.tobytes()
        state_resolution = float(np.abs(first - second).mean())
        counts = {side: sum(item["spikes"] for item in bins) for side, bins in window_bins.items()}
        resolution = _response_rate(abs(counts["original"] - counts["repeat"]), 1000, diagnostic["population_size"])
        assert type(diagnostic["candidate_memory_w_resolution"]) is float and diagnostic["candidate_memory_w_resolution"] == state_resolution
        assert type(diagnostic["response_replay_resolution_hz"]) is float and diagnostic["response_replay_resolution_hz"] == resolution
        cells = [event for event in by_branch[branch] if event["type"] == "qualification_evidence"]
        expected_cells = {(condition, retention) for condition in conditions for retention in (10000, 70000)} if key["phase"] == "pre" else {
            (key["condition"], key["retention_ms"])}
        assert len(cells) == len(expected_cells) and {(cell["condition"], cell["retention_ms"]) for cell in cells} == expected_cells
        assert {event["sequence"] for event in by_branch[branch]} == {
            *(event["sequence"] for event in cells), *(event["sequence"] for event in operations["original"])}
        assert {event["sequence"] for event in by_branch[branch + "/repeat"]} == {
            diagnostic["sequence"], *(event["sequence"] for event in operations["repeat"])}
        for cell in cells:
            _validate_response(cell, execution, (11, 23), "qualification_evidence")
            assert all(cell[name] == key[name] for name in ("seed", "paired_identity", "presentation_order", "phase", "stimulus"))
            condition, retention = cell["condition"], cell["retention_ms"]
            recipient = "matched_reference" if condition == "sufficiency" else ("paired" if condition in conditions[5:] else condition)
            descriptor = training_by_id[f"{base}/{recipient}/training"]
            cell_source = sources[*factors, condition]
            assert all(cell[name] == descriptor[name] for name in route_fields)
            assert cell["retention_source_checkpoint_sha256"] == cell_source["checkpoint_sha256"]
            assert cell["passive_decay_ticks"] == descriptor["retention_reference_tick"] + retention * 10 - cell_source["sim_tick"]
            assert cell["intervention_id"] == (f"{base}/{condition}/intervention" if condition in conditions[5:] else None)
            assert cell["replay_id"] == branch + "/repeat" and all(cell[name] == value for name, value in binding.items())
            assert cell["bins"] == window_bins["original"] and cell["endogenous_dan_spikes"] == ppl_counts["original"]
            assert cell["rate_hz"] == _response_rate(counts["original"], 1000, diagnostic["population_size"])
            assert type(cell["response_replay_resolution_hz"]) is float and cell["response_replay_resolution_hz"] == resolution
            assert cell["one_spike_rate_hz"] == _response_rate(1, 1000, diagnostic["population_size"])
            assert cell["cs_onset_tick"] == diagnostic["cs_onset_tick"]
            assert cell["sim_ms"] * 10 == start["sim_tick"] + 2000
            assert max(window_sequences.values()) < cell["sequence"] < operations["original"][-1]["sequence"]
        assert max(pair_references) < diagnostic["sequence"]
        sample_key = (*factors, key.get("condition"), key.get("retention_ms"))
        sample = key["stimulus"] == "A" and (sample_key in samples or (key["phase"] == "pre" and factors == (11, "A", "AB")))
        if len(cohorts) == 1 or sample:
            result = _compare_selected_replay(prefix.iter_events(), diagnostic, metadata=manifest["metadata"],
                execution=execution, expected_source_occurrence=source, expected_start=start, expected_maps=layout["maps"],
                **{name: layout[name] for name in ("n", "memory_count", "edge_count", "lower", "upper")})
            assert result == {"response_replay_resolution_hz": resolution, "candidate_memory_w_resolution": state_resolution}
            selected_samples.add(sample_key)
    if len(cohorts) == 8:
        assert samples <= selected_samples and (11, "A", "AB", None, None) in selected_samples
        assert len(selected_samples) == 9  # Eight POSTs plus one PRE, not408 full-prefix scans.
    for diagnostic, (_, next_branch) in zip(diagnostics, physical[1:]):
        assert diagnostic["sequence"] < by_branch[next_branch][0]["sequence"]
    last = diagnostics[-1]
    assert records[last["replay_id"]]["engine"]() is owner
    assert owner.brain.cursor == last["sim_tick"]
    assert owner.brain.checkpoint_state_sha256() == last["boundaries"]["final"]["repeat"]["complete_state_sha256"]
    assert any(event["candidate_projection"]["original_hex"] != "0000000000000000" for event in diagnostics)
    assert not any(event["type"] in ("qualification_result", "assay_result") for event in events)
    assert not (recorder.path / "run.json").exists()


@pytest.mark.skipif(os.environ.get("FLY_CONNECTOME_SIM_FULL_TEST") != "1", reason="opt-in True51 selected replay matrix")
def test_selected_replay_complete_native_cohort(selected_caller, engine_factory):
    _check_selected_replay_matrix(selected_caller, engine_factory, ((11, "A", "AB"),))


@pytest.mark.skipif(os.environ.get("FLY_CONNECTOME_SIM_FULL_TEST") != "1", reason="opt-in True408 selected replay matrix")
def test_selected_replay_all_eight_native_cohorts(selected_caller, engine_factory):
    cohorts = tuple((seed, paired, order) for seed in (11, 23) for paired in ("A", "B") for order in ("AB", "BA"))
    _check_selected_replay_matrix(selected_caller, engine_factory, cohorts)


def test_selected_multiple_paired_cohorts_restore_shared_baseline(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    assay._produce_cohorts(engine_factory, recorder, execution=execution,
        cohorts=((11, "A", "AB"), (23, "B", "BA")), conditions=("paired",),
        baseline_occurrence=baseline, namespace=True)
    training = [event for event in recorder.validate_prefix().iter_events() if event["type"] == "qualification_training"]
    assert len(training) == 2
    assert [event["training_end_tick"] for event in training] == [111000, 111000]


@pytest.mark.parametrize("selected_caller", [{"tick": 3}], indirect=True)
def test_selected_accepts_exact_nonzero_factory_baseline(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    def advanced():
        engine = engine_factory()
        engine.observe(np.zeros((32, 32, 3), dtype=np.uint8), 0.3)
        return engine
    assay._produce_cohorts(advanced, recorder, execution=execution, cohorts=((11, "B", "BA"),),
        conditions=("paired",), baseline_occurrence=baseline, namespace=True)
    training = next(event for event in recorder.validate_prefix().iter_events() if event["type"] == "qualification_training")
    assert training["baseline_tick"] == 3 and training["training_end_tick"] == 111003


@pytest.mark.parametrize("selected_caller", [{"missing_black": True}], indirect=True)
def test_selected_requires_black_descriptor_declared_before_recorder(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    before = recorder.next_sequence, set(recorder._checkpoints)
    with pytest.raises(ValueError, match="metadata"):
        assay._produce_cohorts(engine_factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before


@pytest.mark.parametrize("selected_caller", [{"changed_state": True}], indirect=True)
def test_selected_authentic_checkpoint_must_equal_fresh_factory_baseline(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    before = recorder.next_sequence, set(recorder._checkpoints)
    with pytest.raises(ValueError, match="fresh factory baseline state"):
        assay._produce_cohorts(engine_factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before


def test_selected_reserves_late_anchor_ids_before_writes(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.replay import build_black_retention_recipe, build_state_anchor, OPERATION_VERSION
    recorder, execution, baseline = selected_caller
    digest = recorder.ingest_checkpoint("prior.npz", recorder.path / "checkpoints/brain-before.npz",
                                        origin_branch_id=baseline["origin_branch_id"])
    source = {**baseline, "checkpoint_name": "prior.npz", "checkpoint_sha256": digest,
              "checkpoint_sequence": recorder.next_sequence}
    recorder.append({"type": "checkpoint", "branch_id": source["origin_branch_id"],
                     "sim_ms": 0.0, "sim_tick": 0, "checkpoint_name": "prior.npz"})
    recorder.append({"type": "fork", "operation_version": OPERATION_VERSION, "branch_id": "prior-retention",
        "sim_ms": 0.0, "sim_tick": 0, "parent_branch_id": source["origin_branch_id"],
        "parent_checkpoint_name": source["checkpoint_name"],
        "parent_checkpoint_sequence": source["checkpoint_sequence"],
        "parent_checkpoint_sha256": source["checkpoint_sha256"]})
    prefix = recorder.validate_prefix()
    recipe = build_black_retention_recipe(prefix.iter_events(), source_occurrence=source,
        origin_branch_id="prior-retention", target_tick=0, engine_identity=execution["engine_identity"],
        run_metadata_sha256=prefix.manifest["run_metadata_sha256"], black_input=recorder.metadata["black_input"],
        scientific_prefix=prefix.scientific_prefix)
    recorder.append_state_anchor(build_state_anchor(anchor_id="selected/23/B/BA/retention/70000", recipe=recipe,
        complete_state_sha256=engine_factory().brain.checkpoint_state_sha256()))
    before = recorder.next_sequence, set(recorder._checkpoints)
    def factory():
        engine = engine_factory()
        def forbidden(*args, **kwargs):
            pytest.fail("Late anchor collision reached native execution")
        engine.observe = forbidden
        return engine
    with pytest.raises(ValueError, match="collides"):
        assay._produce_cohorts(factory, recorder, execution=execution,
            cohorts=((11, "A", "AB"), (23, "B", "BA")), conditions=("paired",),
            baseline_occurrence=baseline, namespace=True)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before


def test_selected_last_cohort_unreachable_plan_fails_before_writes(selected_caller, engine_factory, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    plan = assay._training_plan
    def changed(*args):
        result = plan(*args)
        if args[1] == 23:
            result["training_end_tick"] += 1000000
        return result
    monkeypatch.setattr(assay, "_training_plan", changed)
    before = recorder.next_sequence, set(recorder._checkpoints)
    with pytest.raises(ValueError, match="precedes"):
        assay._produce_cohorts(engine_factory, recorder, execution=execution,
            cohorts=((11, "A", "AB"), (23, "B", "BA")), conditions=("paired",),
            baseline_occurrence=baseline, namespace=True)
    assert (recorder.next_sequence, set(recorder._checkpoints)) == before


@pytest.mark.parametrize("mutation", ["truncate", "malformed"])
def test_source_lookup_drains_changed_late_suffix_before_factory(native_transfer_sources, engine_factory, monkeypatch, mutation):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.recorder import ValidatedPrefix
    recorder, sources, identity = native_transfer_sources
    recorder.append({"type": "late_diagnostic", "branch_id": "root", "sim_ms": 0.3})
    prefix = recorder.validate_prefix()
    path = recorder.path / "events.jsonl"
    original = path.read_bytes()
    iterate = ValidatedPrefix.iter_events
    def changed(self):
        for event in iterate(self):
            yield event
            if event["type"] == "assay_training" and event["training_id"] == "donor":
                path.write_bytes(original[:-2] if mutation == "truncate" else original[:-2] + b"!\n")
    monkeypatch.setattr(recorder, "validate_prefix", lambda: prefix)
    monkeypatch.setattr(ValidatedPrefix, "iter_events", changed)
    factories = []
    def factory():
        factories.append(1)
        return engine_factory()
    try:
        with pytest.raises(ValueError):
            assay._restore_training_source(recorder, *sources[0], factory, identity, 1)
        assert not factories
    finally:
        path.write_bytes(original)


def test_selected_equal_source_anchor_has_no_fictitious_gap(selected_caller, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    execution["selected_configuration"].update(dan_onset_ms=100.0, post_pair_gap_ms=10000.0)
    assay._produce_cohorts(engine_factory, recorder, execution=execution, cohorts=((11, "B", "AB"),),
        conditions=("paired",), baseline_occurrence=baseline, namespace=True)
    anchors = recorder.validate_prefix().manifest["state_anchors"].values()
    anchor = next(value for value in anchors if value["anchor_id"] == "selected/11/B/AB/retention/10000")
    assert anchor["sim_tick"] == anchor["source_occurrence"]["sim_tick"]
    assert [operation["type"] for operation in anchor["recipe"]["operations"]] == ["fork"]


def test_selected_append_failure_propagates_without_terminal_or_seal(selected_caller, engine_factory, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    recorder, execution, baseline = selected_caller
    append = recorder.append
    def failing(event):
        if event["type"] == "observe":
            raise OSError("selected append failure")
        return append(event)
    monkeypatch.setattr(recorder, "append", failing)
    with pytest.raises(OSError, match="selected append failure"):
        assay._produce_cohorts(engine_factory, recorder, execution=execution, cohorts=((11, "A", "AB"),),
            conditions=("paired",), baseline_occurrence=baseline, namespace=True)
    assert not (recorder.path / "run.json").exists()
    assert not any(event["type"] in ("qualification_result", "assay_result")
                   for event in recorder.validate_prefix().iter_events())


@pytest.mark.parametrize("phase", ["prefix", "sealed"])
def test_confirmation_native_verifiers_recheck_cached_identity_groups(engine_factory, tmp_path, monkeypatch, phase):
    import fly_connectome_sim.experiment.assay as assay
    frozen = _declared_native_frozen_config(engine_factory())
    active, completed = [], []
    def factory():
        engine = engine_factory()
        if active:
            engine.identity()  # Cached declared groups must not conceal the live mutation.
            object.__setattr__(engine.groups, "motor_left", np.array([2], dtype=np.int32))
        return engine
    for stage, name in (("prefix", "verify_replay_prefix"), ("sealed", "verify_replay_run")):
        native_verify = getattr(assay, name)
        def checked_boundary(value, *, engine_factory, stage=stage, native_verify=native_verify):
            if stage == phase:
                active.append(stage)
            try:
                verified = native_verify(value, engine_factory=engine_factory)
                completed.append(stage)
                return verified
            finally:
                active.clear()
        monkeypatch.setattr(assay, name, checked_boundary)
    path = tmp_path / "cached-group-verifier"
    with pytest.raises(ValueError, match="Actual engine identity/current groups"):
        assay.run_paired_cohort(factory, frozen, output_dir=path)
    events = [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]
    assert completed == ([] if phase == "prefix" else ["prefix"])
    if phase == "prefix":
        assert not (path / "run.json").exists()
        assert not any(event["type"] == "assay_result" for event in events)
    else:
        # Owner sealing precedes the independent sealed verifier; its refusal
        # leaves durable bytes, but the call must not return a successful report.
        assert (path / "run.json").is_file()
        assert sum(event["type"] == "assay_result" for event in events) == 1


def test_count_boundary_emission_matches_validated_native_bins(engine_factory, tmp_path):
    """Bounded real native emission with an explicit three-cell measured group."""
    from fly_connectome_sim.engine import FlyEngine
    from fly_connectome_sim.experiment.assay import run_paired_cohort

    def factory():
        original = engine_factory()
        return FlyEngine(brain=original.brain, groups=replace(
            original.groups, mbon11=np.array([0, 2, 3], dtype=np.int32),
        ))

    frozen = _declared_native_frozen_config(factory())
    path = tmp_path / "boundary-emission"
    run_paired_cohort(factory, frozen, output_dir=path)
    verified = verify_replay_run(path, engine_factory=factory)
    events = list(verified.iter_events())
    reduction = reduce_assay_evidence(events, frozen,
                                     attested_state_anchors=verified.replay_attested_state_anchors)
    responses = [event for event in events if event["type"] == "assay_response"]
    assert len(responses) == 12
    assert not any(reason.startswith("invalid_response") for reason in reduction.reasons)
    for event in responses:
        count = sum(item["spikes"] for item in event["bins"])
        assert event["one_spike_rate_hz"] == 3.333333333333333
        assert event["rate_hz"] == count / 0.30000000000000004
        cell = reduction.rows[f"{event['seed']}/{event['paired_identity']}/{event['presentation_order']}/{event['retention_ms']}"]["paired"][f"{event['phase']}_{event['stimulus']}"]
        assert cell["spikes"] == count and cell["rate_hz"] == event["rate_hz"]


def _tracked_factory(factory, records, *, timing=0):
    def create():
        engine = factory()
        observe = engine.observe
        restore = engine.brain.restore
        replace_memory = engine.brain.replace_candidate_memory
        candidate_memory = engine.brain.candidate_memory
        state_digests = engine.brain.candidate_state_digests
        record = {"engine": engine, "calls": [], "restores": [], "operations": [],
                  "replacements": [], "snapshots": []}
        records.append(record)

        def traced_restore(path):
            record["operations"].append("restore")
            before_state = engine.brain.checkpoint_state_sha256()
            before_clock = (engine.brain.cursor, engine.brain.sim_ms, engine.brain.dt,
                            engine.brain.total_spikes, engine.brain.weights_frozen)
            calls_before = len(record["calls"])
            restore(path)
            record["restores"].append({"path": Path(path), "tick": engine.brain.cursor,
                                       "state": engine.brain.checkpoint_state_sha256(),
                                       "before_state": before_state, "before_clock": before_clock,
                                       "after_clock": (engine.brain.cursor, engine.brain.sim_ms, engine.brain.dt,
                                                       engine.brain.total_spikes, engine.brain.weights_frozen),
                                       "calls_before": calls_before, "calls_after": len(record["calls"])})

        def traced_observe(frame, duration, **kwargs):
            record["operations"].append("observe")
            start = engine.brain.cursor
            state = engine.brain.checkpoint_state_sha256()
            weights_frozen = engine.brain.weights_frozen
            result = observe(frame, duration, **kwargs)
            result["compute_seconds"] = timing
            result["kernel_seconds"] = timing
            record["calls"].append({"start": start, "end": engine.brain.cursor,
                                    "state": state, "frame": frame.copy(), "duration": duration,
                                    "weights_frozen": weights_frozen,
                                    "after_weights_frozen": engine.brain.weights_frozen,
                                    "kwargs": kwargs, "telemetry": deepcopy(result)})
            return result

        def traced_digests(targets):
            record["operations"].append("digests")
            return state_digests(targets)

        def traced_snapshot(targets):
            record["operations"].append("snapshot")
            snapshot = candidate_memory(targets)
            record["snapshots"].append(snapshot)
            return snapshot

        def traced_replace(snapshot):
            record["operations"].append("replace")
            before = {name: getattr(engine.brain, name).copy() for name in ("weight", *engine.brain.fields)}
            clock = (engine.brain.cursor, engine.brain.sim_ms, engine.brain.dt,
                     engine.brain.total_spikes, engine.brain.weights_frozen)
            replace_memory(snapshot)
            after = {name: getattr(engine.brain, name).copy() for name in before}
            record["replacements"].append({"snapshot": snapshot, "before": before, "after": after,
                                         "before_clock": clock,
                                         "after_clock": (engine.brain.cursor, engine.brain.sim_ms, engine.brain.dt,
                                            engine.brain.total_spikes, engine.brain.weights_frozen)})

        engine.observe = traced_observe
        engine.brain.restore = traced_restore
        engine.brain.replace_candidate_memory = traced_replace
        engine.brain.candidate_memory = traced_snapshot
        engine.brain.candidate_state_digests = traced_digests
        return engine
    return create


def test_real_reciprocal_controlled_cohorts(engine_factory, tmp_path, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.engine import _rgb_input_sha256
    from fly_connectome_sim.experiment.stimuli import AssayStimuli

    native = engine_factory()
    frozen = _declared_native_frozen_config(native)
    records, producer_records, prefixes, sealed_runs = [], [], [], []
    verify_prefix, verify_sealed = assay.verify_replay_prefix, assay.verify_replay_run

    def tracked_prefix(*args, **kwargs):
        producer_records.extend(records)
        prefix = verify_prefix(*args, **kwargs)
        prefixes.append(prefix)
        return prefix

    def tracked_sealed(*args, **kwargs):
        run = verify_sealed(*args, **kwargs)
        sealed_runs.append(run)
        return run

    monkeypatch.setattr(assay, "verify_replay_prefix", tracked_prefix)
    monkeypatch.setattr(assay, "verify_replay_run", tracked_sealed)
    path = tmp_path / "reciprocal"
    report = assay.run_controlled_cohorts(_tracked_factory(engine_factory, records), frozen,
        output_dir=path, cohorts=[(101, "A", "AB"), (101, "B", "AB")])
    assert len(prefixes) == len(sealed_runs) == 1
    run = sealed_runs[0]
    events = list(run.iter_events())
    trainings = [e for e in events if e["type"] == "assay_training"]
    interventions = [e for e in events if e["type"] == "assay_intervention"]
    responses = [e for e in events if e["type"] == "assay_response"]
    anchors = list(run.manifest["state_anchors"].values())
    checkpoints = run.manifest["checkpoints"]
    conditions = ("paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired",
                  "matched_reference", "necessity", "sufficiency", "sham")
    assert len(trainings) == 10 and len(interventions) == 6
    assert len(responses) == 192 and len(anchors) == 32 and len(checkpoints) == 19
    assert len({a["anchor_id"] for a in anchors}) == 32
    starts = [e for e in events if e["type"] in ("branch_start", "fork")]
    assert len({e["branch_id"] for e in starts}) == len(starts)
    assert [e["sequence"] for e in events] == list(range(len(events)))
    assert sum(e["type"] == "assay_result" for e in events) == 1
    assert report.to_dict() == analyze_assay(run, frozen).to_dict() == events[-1]["report"]
    assert report.to_dict() == assay.assess_assay_prefix(prefixes[0], frozen).to_dict()
    assert report.status == "inconclusive" and report.values["verification_mode"] == "native-replay"
    missing = [r for r in report.reasons if r.startswith("missing_")]
    assert missing and all(":101/A/AB/" not in r and ":101/B/AB/" not in r for r in missing)
    assert any("113/" in r for r in missing) and any("101/A/BA/" in r for r in missing)
    assert {r for r in report.reasons if r.startswith("reciprocal:")} == {
        "reciprocal:101/AB/10000", "reciprocal:101/AB/70000"}
    assert any(r.startswith("paired_effect:") for r in report.reasons)
    reduction = reduce_assay_evidence(run.iter_events(), frozen,
                                     attested_state_anchors=run.replay_attested_state_anchors)
    for identity in ("A", "B"):
        assert [t["condition"] for t in trainings if t["paired_identity"] == identity] == list(conditions[:5])
        for retention in (10000, 70000):
            for condition in conditions:
                assert set(reduction.rows[f"101/{identity}/AB/{retention}"][condition]) == {
                    f"{phase}_{stimulus}" for phase in ("pre", "post") for stimulus in ("A", "B", "C")}

    baseline = engine_factory()
    baseline.brain.restore(path / "checkpoints" / "baseline.npz")
    baseline_state = baseline.brain.checkpoint_state_sha256()
    baseline_occurrence = checkpoints["baseline.npz"]
    assert set(checkpoints) == {"brain-before.npz", "baseline.npz", "brain-after.npz"} | {
        f"101-{identity}-AB-{name}.npz" for identity in ("A", "B") for name in (
            "training-end", "frozen_plasticity-training-end", "no_external_dan-training-end",
            "temporally_unpaired-training-end", "matched-reference-training-end",
            "necessity-post", "sufficiency-post", "sham-post")}
    # Native acquisition records are identified by their exact event call stream,
    # rather than inference from frozen-plasticity learning flags.
    acquisition_records = []
    for training in trainings:
        logged = [e for e in events if e["branch_id"] == training["branch_id"]
                  and e["type"] in ("observe", "neutral_gap_chunk")]
        matches = [r for r in producer_records if r["calls"] and r["restores"]
                   and r["restores"][0]["path"].name == "baseline.npz"
                   and [(c["start"], c["end"]) for c in r["calls"]] == [
                       (e["start_tick"], e["end_tick"]) for e in logged]
                   and [c["telemetry"]["input_sha256"] for c in r["calls"]] == [
                       s["input_sha256"] for s in training["segments"]]
                   and [c["kwargs"]["learning"] for c in r["calls"]] == [
                       s["learning"] for s in training["segments"]]
                   and [c["kwargs"]["stimulation"] for c in r["calls"]] == [
                       s["external_stimulation"] for s in training["segments"]]]
        # Paired reciprocal records can have identical inputs but different DAN
        # placement. No native engine may be assigned to both acquisitions.
        record = next(r for r in matches if not any(r is used for used in acquisition_records))
        acquisition_records.append(record)
        assert record["restores"][0]["state"] == record["calls"][0]["state"] == baseline_state
        branch = next(e for e in starts if e["branch_id"] == training["branch_id"])
        assert branch["parent_checkpoint_name"] == "baseline.npz"
        assert branch["parent_checkpoint_sequence"] == baseline_occurrence["checkpoint_sequence"]
        assert training["baseline_checkpoint_sha256"] == baseline_occurrence["sha256"]
        for call, segment in zip(record["calls"], training["segments"]):
            expected = (np.zeros((32, 32, 3), dtype=np.uint8) if segment["stimulus"] is None
                        else AssayStimuli(101, "confirmation").frame(segment["stimulus"]))
            assert np.array_equal(call["frame"], expected)
            assert _rgb_input_sha256(call["frame"]) == segment["input_sha256"]
            assert call["duration"] <= 500 and not call["weights_frozen"] and not call["after_weights_frozen"]
        occurrence = next(e for e in events if e["type"] == "checkpoint"
                          and e["branch_id"] == training["branch_id"])
        assert occurrence["checkpoint_name"].startswith(f"101-{training['paired_identity']}-AB-")
        inventory = checkpoints[occurrence["checkpoint_name"]]
        assert inventory["checkpoint_sequence"] == occurrence["sequence"]
        assert inventory["origin_branch_id"] == training["branch_id"]
        source = engine_factory()
        source.identity()
        source.brain.restore(path / "checkpoints" / occurrence["checkpoint_name"])
        assert source.brain.cursor == training["training_end_tick"]
        assert source.brain.candidate_state_digests(source.groups.mbon11) == {
            k: training[k] for k in ("candidate_memory_sha256", "noncandidate_state_sha256")}
        assert sha256((path / "checkpoints" / occurrence["checkpoint_name"]).read_bytes()).hexdigest() == training["training_end_checkpoint_sha256"]
    assert len({id(r["engine"]) for r in acquisition_records}) == 10
    replacements = [r for r in producer_records if r["replacements"]]
    assert len(replacements) == 6
    for record, intervention in zip(replacements, interventions):
        assert record["operations"][record["operations"].index("replace") - 1:][:3] == ["digests", "replace", "digests"]
        transfer = record["replacements"][0]
        assert transfer["before_clock"] == transfer["after_clock"]
        for role in ("donor", "recipient"):
            training = next(t for t in trainings if t["training_id"] == intervention[f"{role}_training_id"])
            assert training["paired_identity"] == intervention["paired_identity"]
            assert intervention[f"{role}_checkpoint_sha256"] == training["training_end_checkpoint_sha256"]
        assert intervention["recipient_candidate_memory_after_sha256"] == intervention["donor_candidate_memory_sha256"]
        assert intervention["noncandidate_state_before_sha256"] == intervention["noncandidate_state_after_sha256"]
        recipient_source = next(e for e in events if e["type"] == "checkpoint"
                                and e["branch_id"] == intervention["branch_id"])
        assert recipient_source["checkpoint_name"].startswith(f"101-{intervention['paired_identity']}-AB-")
        assert recipient_source["parent_branch_id"] == intervention["recipient_training_id"]
        assert recipient_source["checkpoint_sha256"] == intervention["post_intervention_checkpoint_sha256"]
    pre_records = [r for r in producer_records if r["calls"] and r["restores"]
                   and r["restores"][0]["path"].name == "baseline.npz"
                   and not any(r is acquired for acquired in acquisition_records)]
    post_records = [r for r in producer_records if r["restores"] and r["restores"][0]["path"].name == "retained.npz"]
    assert len(pre_records) == 6 and len(post_records) == 96
    assert len({id(r["engine"]) for r in pre_records + post_records}) == 102
    for record in pre_records + post_records:
        assert len(record["restores"]) == 1
        assert record["calls"][0]["state"] == record["restores"][0]["state"]
        assert all(c["kwargs"] == {"learning": False, "stimulation": None} for c in record["calls"])
    for record in pre_records:
        assert record["restores"][0]["state"] == baseline_state
    for record in post_records:
        assert not record["restores"][0]["path"].exists()
        assert record["restores"][0]["state"] in {a["complete_state_sha256"] for a in anchors}
    trial_records = {}
    for index, identity in enumerate(("A", "B")):
        trial_records.update({f"101/{identity}/AB/pre/{stimulus}": record
                              for stimulus, record in zip(("A", "B", "C"), pre_records[index * 3:index * 3 + 3])})
        trial_records.update({f"101/{identity}/AB/{'' if condition == 'paired' else condition + '/'}post/{retention}/{stimulus}": record
            for (condition, retention, stimulus), record in zip(
                ((c, t, s) for c in conditions for t in (10000, 70000) for s in ("A", "B", "C")),
                post_records[index * 48:index * 48 + 48])})
    for response in responses:
        assert response["branch_id"].startswith(f"101/{response['paired_identity']}/AB/")
        training = next(t for t in trainings if t["training_id"] == response["training_id"])
        assert training["paired_identity"] == response["paired_identity"]
        source_digest = training["training_end_checkpoint_sha256"]
        if response["intervention_id"]:
            intervention = next(i for i in interventions if i["intervention_id"] == response["intervention_id"])
            assert intervention["paired_identity"] == response["paired_identity"]
            source_digest = intervention["post_intervention_checkpoint_sha256"]
        assert response["retention_source_checkpoint_sha256"] == source_digest
        record = trial_records[response["branch_id"]]
        observations = [c["telemetry"] for c in record["calls"]]
        assert observations == [e["telemetry"] for e in events
                                if e["branch_id"] == response["branch_id"] and e["type"] == "observe"]
        start, stop = response["bins"][0]["start_tick"], response["bins"][-1]["end_tick"]
        raw = [{"start_tick": round(b["end_ms"] * 10) - round(b["duration_ms"] * 10),
                "end_tick": round(b["end_ms"] * 10), "spikes": b["group_spikes"]["mbon11"]}
               for o in observations for b in o["bins"] if start < round(b["end_ms"] * 10) <= stop]
        assert response["bins"] == raw and response["sim_ms"] == stop / 10
        assert response["rate_hz"] == sum(b["spikes"] for b in raw) * 10000 / (stop - start)
        visual = next(c for c in record["calls"] if np.any(c["frame"]))
        assert np.array_equal(visual["frame"], AssayStimuli(101, "confirmation").frame(response["stimulus"]))
        assert _rgb_input_sha256(visual["frame"]) == response["input_sha256"]
    for anchor in anchors:
        occurrence = anchor["source_occurrence"]
        inventory = checkpoints[occurrence["checkpoint_name"]]
        assert inventory["checkpoint_sequence"] == occurrence["checkpoint_sequence"]
        assert inventory["origin_branch_id"] == occurrence["origin_branch_id"]
        assert inventory["sha256"] == occurrence["checkpoint_sha256"]
        assert anchor["origin_branch_id"].startswith("101/")
        factors = anchor["origin_branch_id"].split("/")[:3]
        assert "/".join(factors) in occurrence["origin_branch_id"]
    assert "retained.npz" not in checkpoints


@pytest.mark.parametrize("cohorts", [None, [], (), {}, "101/A/AB", [(101, "A")],
    [(101, "A", "AB", "extra")], [None], [(True, "A", "AB")], [(11, "A", "AB")],
    [(101, "C", "AB")], [(101, "A", "AA")], [(101, "A", "AB"), (101, "A", "AB")],
    [([], "A", "AB")], [(101, [], "AB")], [(101, "A", [])], [(101, "A", "AB")] * 9])
def test_controlled_cohorts_invalid_request_fails_before_artifact(engine_factory, tmp_path, monkeypatch, cohorts):
    import fly_connectome_sim.experiment.assay as assay
    frozen = _declared_native_frozen_config(engine_factory())
    def unexpected_artifact(*args, **kwargs):
        pytest.fail("Scratch/recorder opened before cohort validation")
    monkeypatch.setattr(assay, "TemporaryDirectory", unexpected_artifact)
    monkeypatch.setattr(assay, "RunRecorder", unexpected_artifact)
    with pytest.raises(ValueError, match="(?i)cohort"):
        assay.run_controlled_cohorts(engine_factory, frozen, output_dir=tmp_path / "invalid", cohorts=cohorts)
    assert not (tmp_path / "invalid").exists()


@pytest.mark.parametrize("mutation", ["input_hash", "black_hash", "unreachable"])
def test_controlled_cohorts_late_preflight_fails_before_artifact(engine_factory, tmp_path, monkeypatch, mutation):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.analysis import FrozenAssayConfig
    def advanced():
        engine = engine_factory()
        engine.observe(np.zeros((32, 32, 3), dtype=np.uint8), 0.3)
        return engine
    data = _declared_native_frozen_config(advanced()).to_dict()
    plans = []
    training_plan = assay._training_plan
    def tracked_plan(*args):
        plan = training_plan(*args)
        plans.append((args[1:4], plan))
        return plan
    monkeypatch.setattr(assay, "_training_plan", tracked_plan)
    if mutation == "unreachable":
        data["selected_configuration"]["post_pair_gap_ms"] = 10000.0
        cohorts = ((101, "B", "BA"), (101, "A", "BA"))
    else:
        cohorts = ((101, "A", "AB"), (113, "B", "AB"))
    del data["digest"]
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    frozen = FrozenAssayConfig.from_dict(data)
    hashes = []
    actual_hash = assay._rgb_input_sha256
    def changed_late_input(frame):
        # Change genuine producer RGB bytes after frozen validation. The hash
        # remains the real codec, so this probes actual late-cohort inputs.
        if len(hashes) == (7 if mutation == "black_hash" else 4):
            frame[0, 0, 0] ^= np.uint8(1)
        digest = actual_hash(frame)
        hashes.append(digest)
        return digest
    if mutation != "unreachable":
        monkeypatch.setattr(assay, "_rgb_input_sha256", changed_late_input)
    def unexpected_artifact(*args, **kwargs):
        pytest.fail("Scratch/recorder opened before late-cohort preflight")
    monkeypatch.setattr(assay, "TemporaryDirectory", unexpected_artifact)
    monkeypatch.setattr(assay, "RunRecorder", unexpected_artifact)
    with pytest.raises(ValueError, match="(?i)(hash|anchor.*source)"):
        assay.run_controlled_cohorts(advanced, frozen, output_dir=tmp_path / "late", cohorts=cohorts)
    if mutation == "unreachable":
        assert len(plans) == 10
        assert all(p["training_end_tick"] <= p["retention_reference_tick"] + 99000 for _, p in plans[:5])
        assert all(p["training_end_tick"] > p["retention_reference_tick"] + 99000 for _, p in plans[5:])
        assert all(p["segments"][0]["start_tick"] == 3 for _, p in plans)
    else:
        assert len(hashes) == 8
        assert hashes[:4] == list(data["confirmation_input_sha256"]["101"].values())
    assert not (tmp_path / "late").exists()


def test_real_controlled_cohort(engine_factory, tmp_path, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.qualification import GridConfiguration, _training_timeline

    native = engine_factory()
    frozen = _declared_native_frozen_config(native)
    records, producer_records, sealed_runs = [], [], []
    verify_prefix, verify_sealed = assay.verify_replay_prefix, assay.verify_replay_run

    def tracked_prefix(*args, **kwargs):
        producer_records.extend(records)
        return verify_prefix(*args, **kwargs)

    def tracked_sealed(*args, **kwargs):
        run = verify_sealed(*args, **kwargs)
        sealed_runs.append(run)
        return run

    monkeypatch.setattr(assay, "verify_replay_prefix", tracked_prefix)
    monkeypatch.setattr(assay, "verify_replay_run", tracked_sealed)
    path = tmp_path / "controls"
    report = assay.run_controlled_cohort(_tracked_factory(engine_factory, records), frozen,
                                       output_dir=path)
    assert len(producer_records) == 79
    authentication = producer_records[0]
    assert not authentication["calls"]
    assert len(authentication["restores"]) == 1
    authenticated = authentication["restores"][0]
    assert authenticated["path"].name == "baseline.npz"
    assert authenticated["before_state"] == authenticated["state"]
    assert authenticated["before_clock"] == authenticated["after_clock"]
    assert authenticated["before_clock"][:2] == (0, 0.0)
    assert authenticated["calls_before"] == authenticated["calls_after"] == 0
    assert authentication["engine"].brain.cursor == 0
    assert authentication["engine"].brain.checkpoint_state_sha256() == authenticated["state"]
    assert len(sealed_runs) == 1
    run = sealed_runs[0]
    events = list(run.iter_events())
    trainings = [e for e in events if e["type"] == "assay_training"]
    interventions = [e for e in events if e["type"] == "assay_intervention"]
    responses = [e for e in events if e["type"] == "assay_response"]
    anchors = list(run.manifest["state_anchors"].values())
    conditions = ("paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired",
                  "matched_reference", "necessity", "sufficiency", "sham")
    assert [t["condition"] for t in trainings] == list(conditions[:5])
    assert [i["condition"] for i in interventions] == list(conditions[5:])
    assert len(responses) == 96 and len(anchors) == 16
    assert set(run.manifest["checkpoints"]) == {
        "brain-before.npz", "baseline.npz", "training-end.npz", "brain-after.npz",
        "frozen_plasticity-training-end.npz", "no_external_dan-training-end.npz",
        "temporally_unpaired-training-end.npz", "matched-reference-training-end.npz",
        "necessity-post.npz", "sufficiency-post.npz", "sham-post.npz",
    }
    assert report.status == "inconclusive"
    missing = [reason for reason in report.reasons if reason.startswith("missing_")]
    assert missing and all(":101/A/AB/" not in reason for reason in missing)
    # This tiny correctness fixture has no qualified scientific effect. Completing
    # its controls legitimately exposes effect/floor failures as well as absent factors.
    assert set(report.reasons) - set(missing) == {
        f"{gate}:101/A/AB/{retention}"
        for gate in ("C_floor", "control_frozen_plasticity", "control_no_external_dan",
                     "control_temporally_unpaired", "necessity_contrast", "paired_effect",
                     "sufficiency_absolute", "sufficiency_reference")
        for retention in (10000, 70000)}
    assert any("113/" in reason for reason in report.reasons)
    assert any("101/B/" in reason for reason in report.reasons)
    assert any("101/A/BA/" in reason for reason in report.reasons)
    assert report.values["verification_mode"] == "native-replay"
    assert sum(e["type"] == "assay_result" for e in events) == 1
    assert report.to_dict() == analyze_assay(run, frozen).to_dict() == events[-1]["report"]
    assert {r["parent_sha256"] for r in report.values["nonmaterialized_parents"]} == {
        a["state_anchor_sha256"] for a in anchors}
    reduction = reduce_assay_evidence(run.iter_events(), frozen,
                                     attested_state_anchors=run.replay_attested_state_anchors)
    for retention in (10000, 70000):
        for condition in conditions:
            assert set(reduction.rows[f"101/A/AB/{retention}"][condition]) == {
                f"{phase}_{stimulus}" for phase in ("pre", "post") for stimulus in ("A", "B", "C")}

    config = frozen.to_dict()
    grid = GridConfiguration(**config["selected_configuration"])
    baseline = engine_factory()
    baseline.brain.restore(path / "checkpoints" / "baseline.npz")
    baseline_state = baseline.brain.checkpoint_state_sha256()
    paired = trainings[0]
    for record, training in zip(producer_records[1:6], trainings):
        condition = training["condition"]
        schedule, _, total_end, t0 = _training_timeline(grid, "A", "AB", condition, controls=True)
        assert record["restores"][0]["path"].name == "baseline.npz"
        assert record["calls"][0]["state"] == record["restores"][0]["state"] == baseline_state
        assert training["baseline_tick"] == baseline.brain.cursor
        assert training["training_end_tick"] == baseline.brain.cursor + round(total_end * 10)
        assert training["association_t0_tick"] == baseline.brain.cursor + round(t0 * 10)
        assert training["retention_reference_tick"] == paired["association_t0_tick"]
        assert training["training_visual_exposure_ticks"] == {"A": 1000, "B": 1000, "C": 0}
        assert len(record["calls"]) == len(schedule) == len(training["segments"])
        actual_rows = []
        for call, segment in zip(record["calls"], schedule):
            learning = (condition in ("paired", "no_external_dan", "temporally_unpaired")
                        and segment.start_ms < t0 and bool(segment.stimulus or segment.stimulation))
            assert call["duration"] == segment.end_ms - segment.start_ms <= 500
            assert call["kwargs"] == {"stimulation": segment.stimulation, "learning": learning}
            assert call["weights_frozen"] is False and call["after_weights_frozen"] is False
            expected_pulse = {"population": "ppl101", "current_mv": 20.0,
                              "duration_ms": call["duration"]} if segment.stimulation else None
            assert call["telemetry"]["stimulation"] == expected_pulse
            if segment.stimulus is None:
                assert not np.any(call["frame"])
            else:
                from fly_connectome_sim.experiment.stimuli import AssayStimuli
                assert np.array_equal(call["frame"], AssayStimuli(101, "confirmation").frame(segment.stimulus))
            actual_rows.append({"start_tick": call["start"], "end_tick": call["end"],
                                "stimulus": segment.stimulus, "external_stimulation": call["kwargs"]["stimulation"],
                                "learning": call["kwargs"]["learning"], "current_mv": 20.0 if expected_pulse else None,
                                "input_sha256": call["telemetry"]["input_sha256"]})
        assert actual_rows == training["segments"]
        assert {name: sum(c["end"] - c["start"] for c, s in zip(record["calls"], schedule)
                          if s.stimulus == name) for name in ("A", "B", "C")} == {
            "A": 1000, "B": 1000, "C": 0}
        pulse_calls = [c for c in record["calls"] if c["kwargs"]["stimulation"]]
        pulse_end = max((c["end"] for c in pulse_calls), default=None)
        assert training["last_external_dan_end_tick"] == pulse_end
        if condition in ("paired", "frozen_plasticity", "temporally_unpaired"):
            assert sum(c["end"] - c["start"] for c in pulse_calls) == 1000
        else:
            assert not pulse_calls
        if condition == "no_external_dan":
            logged = [e["telemetry"] for e in events
                      if e["branch_id"] == training["branch_id"] and e["type"] == "observe"]
            observed = [c["telemetry"] for c in record["calls"]
                        if any(c["frame"].flat) or c["kwargs"]["stimulation"]]
            assert logged == observed
            assert [b["group_spikes"]["ppl101"] for o in logged for b in o["bins"]] == [
                b["group_spikes"]["ppl101"] for o in observed for b in o["bins"]]
        if condition == "temporally_unpaired":
            assert [(c["start"], c["end"]) for c in pulse_calls] == [(baseline.brain.cursor, baseline.brain.cursor + 1000)]
            assert all(not np.any(c["frame"]) for c in pulse_calls)
            first_cs = next(c["start"] for c, s in zip(record["calls"], schedule) if s.stimulus)
            assert first_cs == baseline.brain.cursor + 101000
            assert first_cs - pulse_end == training["unpaired_nearest_cs_boundary_ticks"] == 100000
        name = {"paired": "training-end.npz", "matched_reference": "matched-reference-training-end.npz"}.get(
            condition, f"{condition}-training-end.npz")
        source = engine_factory()
        source.identity()
        source.brain.restore(path / "checkpoints" / name)
        assert source.brain.cursor == training["training_end_tick"]
        assert source.brain.candidate_state_digests(source.groups.mbon11) == {
            k: training[k] for k in ("candidate_memory_sha256", "noncandidate_state_sha256")}
        assert sha256((path / "checkpoints" / name).read_bytes()).hexdigest() == training["training_end_checkpoint_sha256"]

    pre_records = [r for r in producer_records if r["calls"] and r["restores"]
                   and r["restores"][0]["path"].name == "baseline.npz"
                   and not any(r is t for t in producer_records[1:6])]
    post_records = [r for r in producer_records if r["restores"] and r["restores"][0]["path"].name == "retained.npz"]
    assert len(pre_records) == 3 and len(post_records) == 48
    assert len({id(r["engine"]) for r in pre_records + post_records}) == 51
    assert len([e for e in responses if e["phase"] == "pre"]) == 48
    for record in pre_records + post_records:
        restored = record["restores"][0]
        assert len(record["restores"]) == 1 and record["calls"][0]["state"] == restored["state"]
        if any(record is pre for pre in pre_records):
            assert restored["state"] == baseline_state
        else:
            assert not restored["path"].exists()
            assert restored["state"] in {a["complete_state_sha256"] for a in anchors}
        assert all(c["kwargs"] == {"learning": False, "stimulation": None}
                   and c["weights_frozen"] is False and c["after_weights_frozen"] is False for c in record["calls"])
    trial_records = {f"pre/{stimulus}": r for stimulus, r in zip(("A", "B", "C"), pre_records)}
    trial_records.update({f"{'' if condition == 'paired' else condition + '/'}post/{retention}/{stimulus}": record
                         for (condition, retention, stimulus), record in zip(
                             ((c, t, s) for c in conditions for t in (10000, 70000) for s in ("A", "B", "C")), post_records)})
    for response in responses:
        observations = [c["telemetry"] for c in trial_records[response["branch_id"]]["calls"]]
        logged = [e["telemetry"] for e in events if e["branch_id"] == response["branch_id"] and e["type"] == "observe"]
        assert observations == logged
        start, stop = response["bins"][0]["start_tick"], response["bins"][-1]["end_tick"]
        raw = [{"start_tick": round(b["end_ms"] * 10) - round(b["duration_ms"] * 10),
                "end_tick": round(b["end_ms"] * 10), "spikes": b["group_spikes"]["mbon11"]}
               for o in observations for b in o["bins"] if start < round(b["end_ms"] * 10) <= stop]
        assert raw == response["bins"]
        assert response["rate_hz"] == sum(b["spikes"] for b in raw) * 10000 / (stop - start)
        assert response["endogenous_dan_spikes"] == sum(b["group_spikes"]["ppl101"]
            for o in observations for b in o["bins"] if round(b["end_ms"] * 10) <= stop)
    retained = [r for r in producer_records if r["calls"] and r["restores"]
                and r["restores"][0]["path"].name.endswith("training-end.npz")]
    assert len(retained) == 10
    for record in retained:
        assert all(not np.any(c["frame"]) and c["kwargs"] == {"learning": False, "stimulation": None}
                   and c["weights_frozen"] is False and c["after_weights_frozen"] is False for c in record["calls"])
    assert len([r for r in producer_records if r["replacements"]]) == 3


@pytest.mark.parametrize("factor,value", [("seed", True), ("seed", 11), ("paired_identity", "C"), ("presentation_order", "AA")])
def test_controlled_undeclared_factors_fail_before_artifact(engine_factory, tmp_path, factor, value):
    import fly_connectome_sim.experiment.assay as assay
    native = engine_factory()
    frozen = _declared_native_frozen_config(native)
    with pytest.raises(ValueError, match="Undeclared"):
        assay.run_controlled_cohort(engine_factory, frozen, output_dir=tmp_path / "controls", **{factor: value})
    assert not (tmp_path / "controls").exists()


@pytest.mark.parametrize("paired_identity,presentation_order", [("B", "AB"), ("A", "BA")])
def test_controlled_unreachable_anchor_rejects_before_artifact(
        engine_factory, tmp_path, paired_identity, presentation_order, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.analysis import FrozenAssayConfig
    native = engine_factory()
    data = _declared_native_frozen_config(native).to_dict()
    data["selected_configuration"]["post_pair_gap_ms"] = 10000.0
    del data["digest"]
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    frozen = FrozenAssayConfig.from_dict(data)

    def unexpected_artifact(*args, **kwargs):
        pytest.fail("Scratch/recorder opened before training reachability preflight")

    monkeypatch.setattr(assay, "TemporaryDirectory", unexpected_artifact)
    monkeypatch.setattr(assay, "RunRecorder", unexpected_artifact)
    with pytest.raises(ValueError, match="(?i)(target|anchor).*source"):
        assay.run_controlled_cohort(engine_factory, frozen, output_dir=tmp_path / "controls",
                                   paired_identity=paired_identity, presentation_order=presentation_order)
    assert not (tmp_path / "controls").exists()


def test_real_paired_cohort(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.assay import run_paired_cohort
    from fly_connectome_sim.experiment.qualification import GridConfiguration, _training_timeline
    records = []
    factory = _tracked_factory(engine_factory, records)
    frozen = _declared_native_frozen_config(engine_factory())
    path = tmp_path / "assay"
    report = run_paired_cohort(factory, frozen, output_dir=path)
    producer_records = records[:]
    run = verify_replay_run(path, engine_factory=engine_factory)
    events = list(run.iter_events())
    trainings = [e for e in events if e["type"] == "assay_training"]
    responses = [e for e in events if e["type"] == "assay_response"]
    anchors = list(run.manifest["state_anchors"].values())
    assert len(trainings) == 1
    assert len(responses) == 12
    assert len(anchors) == 2
    assert report.to_dict() == analyze_assay(run, frozen).to_dict()
    assert report.status == "inconclusive"
    assert events[-1]["report"] == report.to_dict()
    assert sum(e["type"] == "assay_result" for e in events) == 1
    assert report.values["verification_mode"] == "native-replay"
    assert {r["parent_sha256"] for r in report.values["nonmaterialized_parents"]} == {
        a["state_anchor_sha256"] for a in anchors}
    assert all(reason.startswith(("missing_",)) for reason in report.reasons)
    assert any(reason.startswith("missing_intervention:") for reason in report.reasons)
    assert any("frozen_plasticity" in reason for reason in report.reasons)
    assert any("113/" in reason for reason in report.reasons)
    reduction = reduce_assay_evidence(run.iter_events(), frozen,
                                     attested_state_anchors=run.replay_attested_state_anchors)
    for retention in (10000, 70000):
        row = reduction.rows[f"101/A/AB/{retention}"]["paired"]
        assert len(row) == 6
    training = trainings[0]
    config = frozen.to_dict()
    segments, _, _, t0 = _training_timeline(GridConfiguration(**config["selected_configuration"]),
                                           "A", "AB", "paired", controls=True)
    calls = producer_records[0]["calls"]
    assert len(calls) == len(segments)
    for call, segment, declared in zip(calls, segments, training["segments"]):
        assert call["duration"] == segment.end_ms - segment.start_ms <= 500
        assert call["start"] == declared["start_tick"]
        assert call["end"] == declared["end_tick"]
        assert call["kwargs"]["stimulation"] == segment.stimulation
        assert call["kwargs"]["learning"] == (segment.start_ms < t0 and bool(segment.stimulus or segment.stimulation))
        assert call["telemetry"]["input_sha256"] == declared["input_sha256"]
        if segment.stimulus is None:
            assert not np.any(call["frame"])
    source = engine_factory()
    source.identity()
    source.brain.restore(path / "checkpoints" / "training-end.npz")
    assert source.brain.cursor == training["training_end_tick"]
    assert source.brain.candidate_state_digests(source.groups.mbon11) == {
        k: training[k] for k in ("candidate_memory_sha256", "noncandidate_state_sha256")}
    assert sha256((path / "checkpoints" / "training-end.npz").read_bytes()).hexdigest() == training["training_end_checkpoint_sha256"]
    baseline = engine_factory()
    baseline.brain.restore(path / "checkpoints" / "baseline.npz")
    trials = producer_records[1:4] + producer_records[5:8] + producer_records[9:12]
    assert len(trials) == 9
    for record in trials:
        assert len(record["restores"]) == 1
        assert record["calls"][0]["state"] == record["restores"][0]["state"]
        if any(record is item for item in producer_records[1:4]):
            assert record["restores"][0]["state"] == baseline.brain.checkpoint_state_sha256()
        else:
            anchor = next(a for a in anchors if a["sim_tick"] == record["restores"][0]["tick"])
            assert record["restores"][0]["state"] == anchor["complete_state_sha256"]
        assert all(c["kwargs"]["learning"] is False and c["kwargs"]["stimulation"] is None for c in record["calls"])
    trial_records = {f"pre/{name}": record for name, record in zip(("A", "B", "C"), trials[:3])}
    trial_records.update({f"post/{retention}/{name}": record
                          for retention, group in ((10000, trials[3:6]), (70000, trials[6:9]))
                          for name, record in zip(("A", "B", "C"), group)})
    for response in responses:
        observations = [call["telemetry"] for call in trial_records[response["branch_id"]]["calls"]]
        logged = [e["telemetry"] for e in events if e["branch_id"] == response["branch_id"] and e["type"] == "observe"]
        assert observations == logged
        start, stop = response["bins"][0]["start_tick"], response["bins"][-1]["end_tick"]
        raw = [{"start_tick": round(b["end_ms"] * 10) - round(b["duration_ms"] * 10),
                "end_tick": round(b["end_ms"] * 10), "spikes": b["group_spikes"]["mbon11"]}
               for o in observations for b in o["bins"] if start < round(b["end_ms"] * 10) <= stop]
        assert raw == response["bins"]
        assert response["rate_hz"] == sum(b["spikes"] for b in raw) * 10000 / (stop - start)
        assert response["sim_ms"] == stop / 10
        assert response["endogenous_dan_spikes"] == sum(b["group_spikes"]["ppl101"]
            for o in observations for b in o["bins"] if round(b["end_ms"] * 10) <= stop)
    assert set(run.manifest["checkpoints"]) == {"brain-before.npz", "baseline.npz", "training-end.npz", "brain-after.npz"}
    assert all(not restore["path"].exists() for record in trials[3:] for restore in record["restores"])


@pytest.mark.parametrize("factor,value", [("seed", True), ("seed", 11), ("paired_identity", "C"), ("presentation_order", "AA")])
def test_undeclared_factors_fail_before_artifact(engine_factory, tmp_path, factor, value):
    from fly_connectome_sim.experiment.assay import run_paired_cohort
    frozen = _declared_native_frozen_config(engine_factory())
    with pytest.raises(ValueError, match="Undeclared"):
        run_paired_cohort(engine_factory, frozen, output_dir=tmp_path / "assay", **{factor: value})
    assert not (tmp_path / "assay").exists()


@pytest.mark.parametrize("group", ["mbon11", "motor_left"])
def test_cached_identity_cannot_hide_current_group_mismatch(engine_factory, tmp_path, group):
    from fly_connectome_sim.experiment.assay import run_paired_cohort
    frozen = _declared_native_frozen_config(engine_factory())
    def stale():
        engine = engine_factory()
        engine.identity()
        object.__setattr__(engine.groups, group, np.array([3 if group == "mbon11" else 2], dtype=np.int32))
        return engine
    with pytest.raises(ValueError, match="identity/current groups"):
        run_paired_cohort(stale, frozen, output_dir=tmp_path / "assay")
    assert not (tmp_path / "assay").exists()


@pytest.mark.parametrize("mutation", ["source", "operation"])
def test_preterminal_mutation_fails_without_seal(engine_factory, tmp_path, monkeypatch, mutation):
    import fly_connectome_sim.experiment.assay as assay
    frozen = _declared_native_frozen_config(engine_factory())
    original = assay.verify_replay_prefix
    def mutate(prefix, **kwargs):
        if mutation == "source":
            path = tmp_path / "assay" / "checkpoints" / "training-end.npz"
            with path.open("ab") as stream:
                stream.write(b"changed")
        else:
            path = tmp_path / "assay" / "events.jsonl"
            events = [json.loads(line) for line in path.read_text().splitlines()]
            operation = next(e for e in events if e["type"] == "neutral_gap_chunk" and e["branch_id"].startswith("retention/"))
            operation["learning"] = True
            path.write_text("".join(json.dumps(e) + "\n" for e in events))
        return original(prefix, **kwargs)
    monkeypatch.setattr(assay, "verify_replay_prefix", mutate)
    with pytest.raises(ValueError):
        assay.run_paired_cohort(engine_factory, frozen, output_dir=tmp_path / "assay")
    assert not (tmp_path / "assay" / "run.json").exists()
    assert all(json.loads(line)["type"] != "assay_result" for line in (tmp_path / "assay" / "events.jsonl").read_text().splitlines())


def test_timing_only_real_rerun_preserves_science(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.assay import run_paired_cohort
    frozen = _declared_native_frozen_config(engine_factory())
    runs = []
    reports = []
    for timing in (0, 123):
        path = tmp_path / str(timing)
        reports.append(run_paired_cohort(_tracked_factory(engine_factory, [], timing=timing), frozen, output_dir=path).to_dict())
        runs.append(verify_replay_run(path, engine_factory=engine_factory))
    assert reports[0] == reports[1]
    assert runs[0].manifest["state_anchors"] == runs[1].manifest["state_anchors"]
    assert runs[0].manifest["final_scientific_sha256"] == runs[1].manifest["final_scientific_sha256"]
    assert runs[0].manifest["events_sha256"] != runs[1].manifest["events_sha256"]
    assert [e["scientific_sha256"] for e in runs[0].iter_events()] == [
        e["scientific_sha256"] for e in runs[1].iter_events()]


@pytest.mark.parametrize("configuration,window", [
    ({"cs_duration_ms": 100.0, "dan_onset_ms": -100.0, "post_pair_gap_ms": 500.0},
     {"start_ms": 100.0, "end_ms": 300.0}),
    ({"cs_duration_ms": 300.0, "dan_onset_ms": 100.0, "post_pair_gap_ms": 10000.0},
     {"start_ms": 0.0, "end_ms": 300.0}),
])
def test_declared_timing_and_window_edges(engine_factory, tmp_path, configuration, window):
    from fly_connectome_sim.experiment.analysis import FrozenAssayConfig
    from fly_connectome_sim.experiment.assay import run_paired_cohort
    data = _declared_native_frozen_config(engine_factory()).to_dict()
    data.update(selected_configuration=configuration, response_window=window,
                one_spike_floor_hz=1000 / (window["end_ms"] - window["start_ms"]))
    del data["digest"]
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    frozen = FrozenAssayConfig.from_dict(data)
    report = run_paired_cohort(engine_factory, frozen, output_dir=tmp_path / "assay", paired_identity="B", presentation_order="BA")
    assert all(reason.startswith("missing_") for reason in report.reasons)
    run = verify_replay_run(tmp_path / "assay", engine_factory=engine_factory)
    for response in (e for e in run.iter_events() if e["type"] == "assay_response"):
        assert response["bins"][0]["start_tick"] == response["cs_onset_tick"] + round(window["start_ms"] * 10)
        assert response["bins"][-1]["end_tick"] == response["cs_onset_tick"] + round(window["end_ms"] * 10)


def test_actual_nonzero_submillisecond_baseline(engine_factory, tmp_path, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    def advanced():
        engine = engine_factory()
        engine.observe(np.zeros((32, 32, 3), dtype=np.uint8), 0.3)
        return engine
    frozen = _declared_native_frozen_config(advanced())
    records, producer_records = [], []
    verify_prefix = assay.verify_replay_prefix
    def tracked_prefix(*args, **kwargs):
        producer_records.extend(records)
        return verify_prefix(*args, **kwargs)
    monkeypatch.setattr(assay, "verify_replay_prefix", tracked_prefix)
    report = assay.run_paired_cohort(_tracked_factory(advanced, records), frozen, output_dir=tmp_path / "assay")
    assert len(producer_records) == 12
    authentication = producer_records[0]
    assert len(authentication["restores"]) == 1
    authenticated = authentication["restores"][0]
    assert authenticated["path"].name == "baseline.npz"
    assert authenticated["before_state"] == authenticated["state"]
    assert authenticated["before_clock"] == authenticated["after_clock"]
    assert authenticated["before_clock"][:2] == (3, 3 * 0.1)
    assert authenticated["calls_before"] == authenticated["calls_after"] == 0
    assert authentication["calls"][0]["start"] == 3
    assert authentication["calls"][0]["state"] == authenticated["state"]
    assert all(reason.startswith("missing_") for reason in report.reasons)
    run = verify_replay_run(tmp_path / "assay", engine_factory=advanced)
    training = next(e for e in run.iter_events() if e["type"] == "assay_training")
    assert training["baseline_tick"] == 3


def test_prefix_terminal_equality_is_canonical(engine_factory, tmp_path, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    frozen = _declared_native_frozen_config(engine_factory())
    original = assay.build_assay_result
    def numerically_equal(prefix, config):
        payload = original(prefix, config)
        payload["report"]["values"]["effect_floor_hz"] = 0
        payload["report_sha256"] = sha256(json.dumps(payload["report"], sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        return payload
    monkeypatch.setattr(assay, "build_assay_result", numerically_equal)
    with pytest.raises(ValueError, match="Prefix terminal report mismatch"):
        assay.run_paired_cohort(engine_factory, frozen, output_dir=tmp_path / "assay")
    assert not (tmp_path / "assay" / "run.json").exists()


def test_independent_report_equality_is_canonical(engine_factory, tmp_path, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    frozen = _declared_native_frozen_config(engine_factory())
    original = assay.analyze_assay
    def numerically_equal(run, config):
        report = original(run, config)
        report.values["effect_floor_hz"] = 0
        return report
    monkeypatch.setattr(assay, "analyze_assay", numerically_equal)
    with pytest.raises(ValueError, match="Independent sealed report mismatch"):
        assay.run_paired_cohort(engine_factory, frozen, output_dir=tmp_path / "assay")


@pytest.mark.parametrize("paired_identity,presentation_order", [("B", "AB"), ("A", "BA")])
def test_late_paired_unreachable_anchor_rejects_before_artifact(
        engine_factory, tmp_path, paired_identity, presentation_order):
    from fly_connectome_sim.experiment.analysis import FrozenAssayConfig
    from fly_connectome_sim.experiment.assay import run_paired_cohort
    data = _declared_native_frozen_config(engine_factory()).to_dict()
    data["selected_configuration"]["post_pair_gap_ms"] = 10000.0
    del data["digest"]
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    frozen = FrozenAssayConfig.from_dict(data)
    path = tmp_path / "assay"
    with pytest.raises(ValueError, match="(?i)(target|anchor).*source"):
        run_paired_cohort(engine_factory, frozen, output_dir=path,
                          paired_identity=paired_identity, presentation_order=presentation_order)
    assert not path.exists()


def test_retained_anchor_equal_to_source_remains_reachable(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.analysis import FrozenAssayConfig
    from fly_connectome_sim.experiment.assay import run_paired_cohort
    data = _declared_native_frozen_config(engine_factory()).to_dict()
    data["selected_configuration"].update(dan_onset_ms=100.0, post_pair_gap_ms=10000.0)
    del data["digest"]
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    frozen = FrozenAssayConfig.from_dict(data)
    path = tmp_path / "assay"
    report = run_paired_cohort(engine_factory, frozen, output_dir=path,
                              paired_identity="B", presentation_order="AB")
    assert all(reason.startswith("missing_") for reason in report.reasons)
    run = verify_replay_run(path, engine_factory=engine_factory)
    events = list(run.iter_events())
    training = next(e for e in events if e["type"] == "assay_training")
    anchor = next(a for a in run.manifest["state_anchors"].values()
                  if a["sim_tick"] == training["training_end_tick"])
    assert anchor["origin_branch_id"] == "retention/10000"
    assert anchor["sim_tick"] == anchor["source_occurrence"]["sim_tick"]
    assert [op["type"] for op in anchor["recipe"]["operations"]] == ["fork"]
    assert len([e for e in events if e["type"] == "assay_response"]) == 12
    assert report.to_dict() == analyze_assay(run, frozen).to_dict()


def test_real_intervention_cohort(engine_factory, tmp_path):
    import fly_connectome_sim.experiment.assay as assay
    native = engine_factory()
    frozen = _declared_native_frozen_config(native)
    records = []
    path = tmp_path / "interventions"
    report = assay.run_intervention_cohort(_tracked_factory(engine_factory, records), frozen,
                                         output_dir=path)
    run = verify_replay_run(path, engine_factory=engine_factory)
    events = list(run.iter_events())
    trainings = [e for e in events if e["type"] == "assay_training"]
    interventions = [e for e in events if e["type"] == "assay_intervention"]
    responses = [e for e in events if e["type"] == "assay_response"]
    assert len(trainings) == 2
    assert len(interventions) == 3
    assert len(responses) == 60
    assert len(run.manifest["state_anchors"]) == 10
    assert len(run.manifest["checkpoints"]) == 8
    assert report.status == "inconclusive"
    assert all(reason.startswith("missing_") for reason in report.reasons)
    assert report.to_dict() == analyze_assay(run, frozen).to_dict() == events[-1]["report"]
    reduction = reduce_assay_evidence(run.iter_events(), frozen,
                                     attested_state_anchors=run.replay_attested_state_anchors)
    conditions = ("paired", "matched_reference", "necessity", "sufficiency", "sham")
    for retention in (10000, 70000):
        for condition in conditions:
            assert len(reduction.rows[f"101/A/AB/{retention}"][condition]) == 6
    paired, reference = trainings
    assert paired["condition"] == "paired" and reference["condition"] == "matched_reference"
    assert reference["last_external_dan_end_tick"] is None
    assert reference["training_end_tick"] == paired["training_end_tick"]
    assert reference["retention_reference_tick"] == paired["retention_reference_tick"]
    assert reference["training_visual_exposure_ticks"] == paired["training_visual_exposure_ticks"]
    for record, training in zip(records[1:3], trainings):
        assert record["restores"][0]["path"].name == "baseline.npz"
        assert record["calls"][0]["state"] == record["restores"][0]["state"]
        assert len(record["calls"]) == len(training["segments"])
        for call, segment in zip(record["calls"], training["segments"]):
            assert (call["start"], call["end"]) == (segment["start_tick"], segment["end_tick"])
            assert call["telemetry"]["input_sha256"] == segment["input_sha256"]
            assert call["kwargs"]["learning"] == segment["learning"]
            assert call["kwargs"]["stimulation"] == segment["external_stimulation"]
        if training is reference:
            assert all(c["kwargs"]["learning"] is False and c["kwargs"]["stimulation"] is None
                       for c in record["calls"])
    replacements = [r for r in records if r["replacements"]]
    assert len(replacements) == 3
    for record, intervention in zip(replacements, interventions):
        index = record["operations"].index("replace")
        assert record["operations"][index - 1:index + 2] == ["digests", "replace", "digests"]
        transfer = record["replacements"][0]
        assert transfer["before_clock"] == transfer["after_clock"]
        assert transfer["snapshot"].cursor == intervention["recipient_training_end_tick"]
        for field, value in transfer["before"].items():
            if field in ("memory_u", "memory_w", "weight"):
                assert np.array_equal(transfer["after"][field][1:], value[1:])
                assert np.array_equal(transfer["after"][field][:1], getattr(transfer["snapshot"], field))
            else:
                assert np.array_equal(transfer["after"][field], value)
        assert intervention["noncandidate_state_before_sha256"] == intervention["noncandidate_state_after_sha256"]
        assert intervention["recipient_candidate_memory_after_sha256"] == intervention["donor_candidate_memory_sha256"]
        recipient = reference if intervention["condition"] == "sufficiency" else paired
        assert intervention["recipient_training_id"] == recipient["training_id"]
        assert intervention["recipient_checkpoint_sha256"] == recipient["training_end_checkpoint_sha256"]
        for response in (e for e in responses if e["condition"] == intervention["condition"]):
            assert response["training_id"] == recipient["training_id"]
            assert response["intervention_id"] == intervention["intervention_id"]
            assert response["retention_source_checkpoint_sha256"] == intervention["post_intervention_checkpoint_sha256"]
    trials = [r for r in records if r["restores"] and r["restores"][0]["path"].name == "retained.npz"]
    assert len(trials) == 30
    assert len({id(r["engine"]) for r in trials}) == 30
    for trial in trials:
        assert len(trial["restores"]) == 1
        assert trial["calls"][0]["state"] == trial["restores"][0]["state"]
        assert not trial["restores"][0]["path"].exists()
        assert all(c["kwargs"]["learning"] is False and c["kwargs"]["stimulation"] is None
                   for c in trial["calls"])
    pre = [e for e in responses if e["phase"] == "pre"]
    assert len(pre) == 30 and len({e["branch_id"] for e in pre}) == 3
    assert sum(e["type"] == "assay_result" for e in events) == 1

    def timed_factory():
        engine = engine_factory()
        observe = engine.observe
        def timed(*args, **kwargs):
            observed = observe(*args, **kwargs)
            observed.update(compute_seconds=123, kernel_seconds=123)
            return observed
        engine.observe = timed
        return engine
    other = tmp_path / "timing-only"
    timed_report = assay.run_intervention_cohort(timed_factory, frozen, output_dir=other)
    from fly_connectome_sim.experiment.recorder import verify_run
    timed_run = verify_run(other)
    assert report.to_dict() == timed_report.to_dict()
    assert run.manifest["state_anchors"] == timed_run.manifest["state_anchors"]
    assert run.manifest["final_scientific_sha256"] == timed_run.manifest["final_scientific_sha256"]
    assert run.manifest["events_sha256"] != timed_run.manifest["events_sha256"]


@pytest.fixture
def native_transfer_sources(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.recorder import RunRecorder
    native = engine_factory()
    frozen = _declared_native_frozen_config(native)
    identity = frozen.to_dict()["engine_identity"]
    native.observe(np.zeros((32, 32, 3), dtype=np.uint8), 0.3)
    metadata = {"engine_identity": identity, "family": "confirmation", "seeds": [101, 113],
                "factors": {}, "protocol_version": "associative-confirmation/v1",
                "stimulus_version": "associative-stimuli/v1", "input_sha256": []}
    with RunRecorder(tmp_path / "sources", run_kind="pilot", metadata=metadata,
                     root_branch_id="root") as recorder:
        sources = []
        for name, condition in (("donor", "paired"), ("recipient", "matched_reference")):
            path = tmp_path / ("brain-before.npz" if name == "donor" else "brain-after.npz")
            native.brain.checkpoint(path)
            digest = recorder.ingest_checkpoint(path.name, path, origin_branch_id="root")
            occurrence = {"checkpoint_name": path.name, "checkpoint_sha256": digest,
                          "origin_branch_id": "root", "checkpoint_sequence": len(sources) * 2,
                          "sim_tick": 3}
            recorder.append({"type": "checkpoint", "branch_id": "root", "sim_tick": 3,
                             "sim_ms": 0.3, "checkpoint_name": path.name})
            training = {"type": "assay_training", "branch_id": "root", "training_id": name,
                        "condition": condition, "training_end_tick": 3, "sim_ms": 0.3,
                        "training_end_checkpoint_sha256": digest,
                        **native.brain.candidate_state_digests(native.groups.mbon11)}
            recorder.append(training)
            sources.append((occurrence, training))
        yield recorder, sources, identity


@pytest.mark.parametrize("field,value", [("checkpoint_name", "brain-after.npz"),
    ("checkpoint_sha256", "0" * 64), ("origin_branch_id", "other"),
    ("checkpoint_sequence", 2), ("checkpoint_sequence", False), ("sim_tick", 4), ("sim_tick", 3.0)])
def test_transfer_requires_exact_durable_source(native_transfer_sources, engine_factory, field, value):
    import fly_connectome_sim.experiment.assay as assay
    recorder, sources, identity = native_transfer_sources
    occurrence, training = sources[0]
    spoof = {**occurrence, field: value}
    with pytest.raises(ValueError, match="(?i)(occurrence|source)"):
        assay._restore_training_source(recorder, spoof, training, engine_factory, identity, 1)


@pytest.mark.parametrize("mutation", ["identity", "groups", "clock", "dt", "sim_ms", "map", "state",
    "snapshot_targets", "snapshot_edges", "snapshot_clock", "snapshot_memory", "snapshot_signed_zero"])
def test_transfer_rejects_actual_incompatibility_before_replacement(
        native_transfer_sources, engine_factory, monkeypatch, mutation):
    from dataclasses import replace
    import fly_connectome_sim.experiment.assay as assay
    recorder, sources, identity = native_transfer_sources
    donor = assay._restore_training_source(recorder, *sources[0], engine_factory, identity, 1)
    recipient = assay._restore_training_source(recorder, *sources[1], engine_factory, identity, 1)
    before = recipient.brain.checkpoint_state_sha256()
    if mutation == "identity":
        changed = deepcopy(identity)
        changed["model"] = "different"
        monkeypatch.setattr(donor, "identity", lambda: changed)
    elif mutation == "groups":
        object.__setattr__(donor.groups, "motor_left", np.array([2], dtype=np.int32))
    elif mutation == "clock":
        donor.observe(np.zeros((32, 32, 3), dtype=np.uint8), 0.1)
    elif mutation == "dt":
        donor.brain.dt = 0.2
    elif mutation == "sim_ms":
        donor.brain.sim_ms = 0.4
    elif mutation == "map":
        donor.brain.circuit["edges"] = np.array([1], dtype=np.int64)
    elif mutation == "state":
        donor.brain.v[3] += 1
    else:
        capture = donor.brain.candidate_memory
        def spoof(targets):
            snapshot = capture(targets)
            field, value = {"snapshot_targets": ("target_indices", np.array([3], dtype=np.int32)),
                            "snapshot_edges": ("edge_indices", np.array([1], dtype=np.int64)),
                            "snapshot_clock": ("cursor", 4),
                            "snapshot_memory": ("memory_u", np.array([0.01], dtype=np.float32)),
                            "snapshot_signed_zero": ("memory_u", np.array([-0.0], dtype=np.float32))}[mutation]
            return replace(snapshot, **{field: value})
        monkeypatch.setattr(donor.brain, "candidate_memory", spoof)
    replaced = []
    replace_memory = recipient.brain.replace_candidate_memory
    def trace(snapshot):
        replaced.append(True)
        replace_memory(snapshot)
    monkeypatch.setattr(recipient.brain, "replace_candidate_memory", trace)
    with pytest.raises((ValueError, RuntimeError)):
        assay._replace_candidate_state(donor, recipient, sources[0][1], sources[1][1], identity, 1)
    assert not replaced
    assert recipient.brain.checkpoint_state_sha256() == before


def test_source_is_rehashed_after_factory_before_restore(native_transfer_sources, engine_factory):
    import fly_connectome_sim.experiment.assay as assay
    recorder, sources, identity = native_transfer_sources
    path = recorder.path / "checkpoints" / sources[0][0]["checkpoint_name"]
    original = path.read_bytes()
    restored = []
    def racing_factory():
        engine = engine_factory()
        restore = engine.brain.restore
        def traced(source):
            restored.append(source)
            restore(source)
        engine.brain.restore = traced
        path.write_bytes(original + b"changed")
        return engine
    try:
        with pytest.raises(ValueError, match="bytes changed"):
            assay._restore_training_source(recorder, *sources[0], racing_factory, identity, 1)
        assert not restored
    finally:
        path.write_bytes(original)


def test_source_authentication_exhausts_final_prefix_bindings(native_transfer_sources, engine_factory, monkeypatch):
    import fly_connectome_sim.experiment.assay as assay
    from fly_connectome_sim.experiment.recorder import ValidatedPrefix
    recorder, sources, identity = native_transfer_sources
    prefix = recorder.validate_prefix()
    path = recorder.path / "events.jsonl"
    original = path.read_bytes()
    iterate = ValidatedPrefix.iter_events
    def changing(self):
        for event in iterate(self):
            yield event
            if event["type"] == "assay_training" and event["training_id"] == "recipient":
                path.write_bytes(original.replace(b"matched_reference", b"changed_reference"))
    monkeypatch.setattr(recorder, "validate_prefix", lambda: prefix)
    monkeypatch.setattr(ValidatedPrefix, "iter_events", changing)
    try:
        with pytest.raises(ValueError):
            assay._restore_training_source(recorder, *sources[0], engine_factory, identity, 1)
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize("index", [0, 1])
def test_restored_source_digests_must_match_recorded_training(native_transfer_sources, engine_factory, index):
    import fly_connectome_sim.experiment.assay as assay
    recorder, sources, identity = native_transfer_sources
    def changed_restore_factory():
        engine = engine_factory()
        restore = engine.brain.restore
        def changed(path):
            restore(path)
            engine.brain.v[3] += 1
        engine.brain.restore = changed
        return engine
    with pytest.raises(ValueError, match="source state mismatch"):
        assay._restore_training_source(recorder, *sources[index], changed_restore_factory, identity, 1)


@pytest.mark.parametrize("mutation", ["donor_source", "recipient_source", "live_state"])
def test_intervention_tampering_fails_before_terminal_or_seal(engine_factory, tmp_path, monkeypatch, mutation):
    import fly_connectome_sim.experiment.assay as assay
    frozen = _declared_native_frozen_config(engine_factory())
    original_restore = assay._restore_training_source
    count = 0
    def tampered(recorder, occurrence, *args):
        nonlocal count
        count += 1
        if count == (1 if mutation == "donor_source" else 2) and mutation != "live_state":
            with (recorder.path / "checkpoints" / occurrence["checkpoint_name"]).open("ab") as stream:
                stream.write(b"changed")
        return original_restore(recorder, occurrence, *args)
    monkeypatch.setattr(assay, "_restore_training_source", tampered)
    if mutation == "live_state":
        original_replace = assay._replace_candidate_state
        def changed(donor, *args):
            donor.brain.v[3] += 1
            return original_replace(donor, *args)
        monkeypatch.setattr(assay, "_replace_candidate_state", changed)
    path = tmp_path / "assay"
    with pytest.raises(ValueError):
        assay.run_intervention_cohort(engine_factory, frozen, output_dir=path)
    assert not (path / "run.json").exists()
    assert all(json.loads(line)["type"] != "assay_result"
               for line in (path / "events.jsonl").read_text().splitlines())
