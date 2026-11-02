"""Authenticated grid consumption; tiny native fixtures are not qualification."""

from pathlib import Path
from dataclasses import asdict, replace
from copy import deepcopy
import json
import os
import time
import gc
import weakref

import numpy as np
import pytest

from replay_helpers import map_engine_factory
from fly_connectome_sim.cli import _qualification_metadata
from fly_connectome_sim.experiment import analysis
from fly_connectome_sim.experiment import qualification as q
from fly_connectome_sim.experiment.recorder import RunRecorder, verify_replay_prefix
from fly_connectome_sim.experiment.stimuli import AssayStimuli


def _partial(factory, tmp_path, stop="call"):
    engine = factory()
    recorder = RunRecorder(tmp_path / "recording", run_kind="qualification",
                           metadata=_qualification_metadata(engine.identity()),
                           root_branch_id="qualification/baseline")
    run = q._Run(engine, recorder, engine.identity())
    frames = {name: AssayStimuli(11, "qualification").frame(name) for name in ("A", "B", "C")}
    if stop != "empty":
        baseline = tmp_path / "baseline.npz"
        run.checkpoint(baseline)
        if stop != "baseline":
            run.begin_grid(baseline, 0, 11, "A", "AB")
            run.enter_grid_role("pre", ("pre", "A"), stimulus="A")
            run.branch_id = "grid0/seed11/pairedA/orderAB/pre/A"
            run.restore(baseline)
            if stop == "call":
                run.phase = "reward_free_test"
                q._observe_segments(run, q._trial_segments(q.GRID[0], "A", paired=False)[:1],
                                    frames, learning=False)
    recorder.flush()
    return recorder, run


def test_genuine_native_mid_unit_prefix_is_validated_without_selection(map_engine_factory, tmp_path):
    recorder, run = _partial(map_engine_factory, tmp_path)
    try:
        factories = []

        def verify_factory():
            factories.append(1)
            return map_engine_factory()

        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=verify_factory)
        assert factories == [1]
        assert hasattr(analysis, "_reduce_qualification_grid"), "genuine grid reducer is missing"
        result = analysis._reduce_qualification_grid(value)
        assert result.outcome == "inconclusive"
        assert result.selection is None and result.points == () and result.unit_count == 1
        assert factories == [1]
    finally:
        recorder._stream.close()


@pytest.mark.parametrize("stop,units", [("empty", 0), ("baseline", 0), ("restore", 1)])
def test_available_native_prefix_boundaries(map_engine_factory, tmp_path, stop, units):
    recorder, run = _partial(map_engine_factory, tmp_path, stop)
    try:
        result = analysis._reduce_qualification_grid(verify_replay_prefix(
            recorder.validate_prefix(), engine_factory=map_engine_factory))
        assert result.outcome == "inconclusive" and result.selection is None
        assert result.unit_count == units and not result.points
    finally:
        recorder._stream.close()


def _all_t_unit(factory, tmp_path):
    started = time.perf_counter()
    recorder, run = _partial(factory, tmp_path, "baseline")
    baseline = tmp_path / "baseline.npz"
    frames = {name: AssayStimuli(11, "qualification").frame(name) for name in ("A", "B", "C")}
    run.begin_grid(baseline, 0, 11, "A", "AB")
    base = q._replicate_base(run, tmp_path, baseline, q.GRID[0], 11, "A", "AB", frames)
    measurements = {}
    for retention in q.RETENTION_CANDIDATES_MS:
        retained, maximum, onset = q._retained_tests(run, tmp_path, base, q.GRID[0], frames, "A", retention)
        for window in q.RESPONSE_WINDOWS:
            measurements[(window, retention)] = replace(q._measurement(
                run, base, retained, maximum, onset, q.GRID[0], window, 11, "A", "AB"),
                grid_evidence_id="grid/0/11/A/AB")
    run.finish_grid(baseline)
    recorder.flush()
    return recorder, run, measurements, time.perf_counter() - started


def test_one_real_all_T_unit_reconstructs_every_measurement(map_engine_factory, tmp_path, monkeypatch):
    """One canonical unit, all four T; actual measurement, not a grid-size override."""
    from fly_connectome_sim.experiment import qualification_grid as grid

    recorder, run, expected, producer_seconds = _all_t_unit(map_engine_factory, tmp_path)
    try:
        started = time.perf_counter()
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        verifier_seconds = time.perf_counter() - started
        assert hasattr(grid, "_measure_unit"), "raw unit arithmetic adapter is missing"
        reconstructed = []
        measure = grid._measure_unit
        archive_refs, observation_refs = [], []
        read = grid.read_checkpoint
        raw = grid._raw

        def one_archive(*args):
            gc.collect()
            assert all(reference() is None for reference in archive_refs)
            metadata, arrays = read(*args)
            archive_refs.append(weakref.ref(arrays["weight"]))
            return metadata, arrays

        class RawTelemetry(dict):
            pass

        def one_observation(event, *args):
            assert all(reference() is None for reference in observation_refs)
            event["telemetry"] = RawTelemetry(event["telemetry"])
            observation_refs.append(weakref.ref(event["telemetry"]))
            return raw(event, *args)

        def capture(*args):
            result = measure(*args)
            reconstructed.extend(result[0])
            return result

        monkeypatch.setattr(grid, "_measure_unit", capture)
        monkeypatch.setattr(grid, "read_checkpoint", one_archive)
        monkeypatch.setattr(grid, "_raw", one_observation)
        started = time.perf_counter()
        result = analysis._reduce_qualification_grid(value)
        reducer_seconds = time.perf_counter() - started
        assert result.outcome == "inconclusive" and result.unit_count == 1
        assert result.selection is None and result.points == ()
        assert [asdict(item) for item in reconstructed] == [asdict(expected[(window, retention)])
            for window in q.RESPONSE_WINDOWS for retention in q.RETENTION_CANDIDATES_MS]
        gc.collect()
        assert len(archive_refs) == 17 and all(reference() is None for reference in archive_refs)
        assert len(observation_refs) == 896 and all(reference() is None for reference in observation_refs)
        counts = {"events": 0, "observations": 0, "duration_ticks": 0}
        for event in value.iter_events():
            counts["events"] += 1
            if event["type"] == "qualification_observation":
                counts["observations"] += 1
                counts["duration_ticks"] += event["duration_ticks"]
        sizes = [item["size"] for item in value.manifest["checkpoints"].values()]
        counts.update(producer_seconds=producer_seconds, verifier_seconds=verifier_seconds,
                      reducer_seconds=reducer_seconds, event_bytes=(value.path / "events.jsonl").stat().st_size,
                      checkpoints=len(sizes), checkpoint_bytes=sum(sizes), max_checkpoint_bytes=max(sizes),
                      final_tick=run.engine.brain.cursor,
                      source_identity=run.identity["model_provenance"]["model_fingerprint"])
        (tmp_path / "unit-budget.json").write_text(json.dumps(counts, indent=2), encoding="utf8")
    finally:
        recorder._stream.close()


def _clone(recorder, tmp_path, mutate):
    """Small coherently reframed attacker artifact; never an issued proof stub."""
    events = [json.loads(line) for line in (recorder.path / "events.jsonl").read_text().splitlines()]
    mutate(events)
    clone = RunRecorder(tmp_path / "attacker", run_kind="qualification", metadata=recorder.metadata,
                        root_branch_id="qualification/baseline")
    owned = {"sequence", "previous_scientific_sha256", "scientific_sha256", "run_metadata_sha256"}
    for event in events:
        if event["type"] == "qualification_checkpoint":
            clone.ingest_checkpoint(event["checkpoint_name"],
                recorder.path / "checkpoints" / event["checkpoint_name"], origin_branch_id=event["branch_id"])
        clone.append({key: value for key, value in event.items() if key not in owned})
    clone.flush()
    return clone


@pytest.mark.parametrize("attack", ["edge_order", "compartment", "kc_order", "kc_source", "dan_order",
    "dan_source", "input", "dtype", "phase", "bin_overlap", "bound_count", "kc_counts", "bin_partition",
    "bound_summary", "overflow_trace"])
def test_rehashed_raw_tail_attacks_fail_after_genuine_native_map_issuance(map_engine_factory, tmp_path, attack):
    recorder, run = _partial(map_engine_factory, tmp_path)
    clone = None
    try:
        def mutate(events):
            event = events[-1]
            telemetry = event["telemetry"]
            path = telemetry["pathway_detail"]
            detail = telemetry["qualification_detail"]
            if attack == "edge_order":
                path["candidate_edge_indices"].reverse()
            elif attack == "compartment":
                path["candidate_edge_indices"] = [0, 2]
                path["candidate_edge_post_source_ids"] = ["505", "505"]
            elif attack == "kc_order":
                path["candidate_kc_indices"].reverse()
            elif attack == "kc_source":
                path["candidate_kc_source_ids"].reverse()
            elif attack == "dan_order":
                detail["dan_indices"].reverse()
            elif attack == "dan_source":
                detail["dan_source_ids"].reverse()
            elif attack == "input":
                telemetry["input_sha256"] = recorder.metadata["rgb_input_sha256"]["stimuli"]["11"]["A"]
            elif attack == "dtype":
                telemetry["input_dtype"] = "uint16"
            elif attack == "phase":
                event["phase"] = "pairing"
            elif attack == "bin_overlap":
                telemetry["bins"][1]["end_ms"] = telemetry["bins"][0]["end_ms"]
            elif attack == "bound_count":
                telemetry["bins"][0]["qualification_detail"]["lower_bound_hits"] = 2
            elif attack == "kc_counts":
                path["candidate_kc_spike_counts"][0] = 1
            elif attack == "bin_partition":
                bins = []
                for original in telemetry["bins"]:
                    for end in (original["end_ms"] - 5, original["end_ms"]):
                        item = deepcopy(original)
                        item.update(duration_ms=5.0, end_ms=end)
                        bins.append(item)
                telemetry["bins"] = bins
            elif attack == "bound_summary":
                telemetry["bins"][0]["qualification_detail"]["memory_u"]["maximum"] = 1.0
            elif attack == "overflow_trace":
                telemetry["bins"][0]["qualification_detail"]["rate_kc"][0] = 10 ** 400

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
        assert value.verification_mode == "native-replay"
        with pytest.raises(analysis.AnalysisError, match="grid_"):
            analysis._reduce_qualification_grid(value)
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()


def test_integrity_only_prefix_cannot_supply_native_context(map_engine_factory, tmp_path):
    recorder, run = _partial(map_engine_factory, tmp_path)
    try:
        with pytest.raises(analysis.AnalysisError):
            analysis._reduce_qualification_grid(recorder.validate_prefix())
    finally:
        recorder._stream.close()


def test_genuine_prefix_uses_two_complete_event_passes(map_engine_factory, tmp_path, monkeypatch):
    recorder, run = _partial(map_engine_factory, tmp_path)
    try:
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        passes = []
        original = type(value).iter_events

        def counted(self):
            count = 0
            for event in original(self):
                count += 1
                yield event
            passes.append(count)

        monkeypatch.setattr(type(value), "iter_events", counted)
        assert analysis._reduce_qualification_grid(value).outcome == "inconclusive"
        assert passes == [3, 3]
    finally:
        recorder._stream.close()


def _training_prefix(factory, tmp_path):
    """Actual first training checkpoint, stopped before later acquisition roles."""
    recorder, run = _partial(factory, tmp_path, "baseline")
    baseline = tmp_path / "baseline.npz"
    frames = {name: AssayStimuli(11, "qualification").frame(name) for name in ("A", "B", "C")}
    run.begin_grid(baseline, 0, 11, "A", "AB")
    for index, identity in enumerate(("A", "B", "C", "A")):
        kind = "pre_replay" if index == 3 else "pre"
        # Durable producer position, not a fake prefix marker or binding.
        path = (kind,) if kind == "pre_replay" else (kind, identity)
        run.enter_grid_role(kind, path, stimulus=identity)
        run.branch_id = f"grid0/seed11/pairedA/orderAB/{kind}/{identity}"
        run.restore(baseline)
        q._test_trial(run, q.GRID[0], frames, identity)
    run.enter_grid_role("training", ("training", "paired"), condition="paired")
    run.branch_id = "grid0/seed11/pairedA/orderAB/paired/training"
    run.restore(baseline)
    _, _, _, t0 = q._training(run, q.GRID[0], "A", "AB", "paired", frames, controls=True)
    run.checkpoint(tmp_path / "paired.npz", training_start_tick=0, association_t0_tick=q._ticks(t0))
    recorder.flush()
    return recorder, run


def test_actual_training_checkpoint_tail_is_validated(map_engine_factory, tmp_path):
    recorder, run = _training_prefix(map_engine_factory, tmp_path)
    try:
        result = analysis._reduce_qualification_grid(verify_replay_prefix(
            recorder.validate_prefix(), engine_factory=map_engine_factory))
        assert result.outcome == "inconclusive" and result.unit_count == 1
    finally:
        recorder._stream.close()


def test_training_passive_final_trace_cannot_be_changed_after_rehash(map_engine_factory, tmp_path):
    recorder, run = _training_prefix(map_engine_factory, tmp_path)
    clone = None
    try:
        def mutate(events):
            observation = next(event for event in reversed(events) if event["type"] == "qualification_observation")
            assert observation["phase"] == "post_pair_passive" and observation["stimulus"] is None
            observation["telemetry"]["bins"][-1]["qualification_detail"]["rate_kc"][0] += 1

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
        with pytest.raises(analysis.AnalysisError, match="grid_archive_trace"):
            analysis._reduce_qualification_grid(value)
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()


def test_semantic_failure_still_drains_both_passes(map_engine_factory, tmp_path, monkeypatch):
    recorder, run = _partial(map_engine_factory, tmp_path)
    clone = None
    try:
        def mutate(events):
            events[-1]["phase"] = "pairing"

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
        original = type(value).iter_events
        completed = []

        def counted(self):
            yield from original(self)
            completed.append(True)

        monkeypatch.setattr(type(value), "iter_events", counted)
        with pytest.raises(analysis.AnalysisError, match="grid_call_schedule"):
            analysis._reduce_qualification_grid(value)
        assert completed == [True, True]
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()


def test_malformed_prefix_drain_does_not_retain_failed_raw_event(map_engine_factory, tmp_path, monkeypatch):
    """Genuine native-issued bad prefix; a traceback must not buffer its raw call."""
    recorder, run = _partial(map_engine_factory, tmp_path)
    clone = None
    try:
        def mutate(events):
            events[-1]["phase"] = "pairing"

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
        original = type(value).iter_events
        failed_refs = []
        passes = 0

        class RawEvent(dict):
            pass

        def tracked(self):
            nonlocal passes
            passes += 1
            for event in original(self):
                if event["type"] == "qualification_observation":
                    event = RawEvent(event)
                    failed_refs.append(weakref.ref(event))
                yield event
                if passes == 2 and event["sequence"] == 0:
                    gc.collect()
                    assert failed_refs and all(reference() is None for reference in failed_refs), (
                        "semantic-error traceback retained a raw observation during drain")

        monkeypatch.setattr(type(value), "iter_events", tracked)
        with pytest.raises(analysis.AnalysisError, match="grid_call_schedule"):
            analysis._reduce_qualification_grid(value)
        assert passes == 2
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()


def test_second_pass_truncation_overrides_incomplete_prefix(map_engine_factory, tmp_path, monkeypatch):
    recorder, run = _partial(map_engine_factory, tmp_path)
    try:
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        original = type(value).iter_events
        passes = 0

        def truncate(self):
            nonlocal passes
            passes += 1
            for event in original(self):
                yield event
                if passes == 2 and event["sequence"] == 2:
                    path = value.path / "events.jsonl"
                    with path.open("r+b") as stream:
                        stream.truncate(path.stat().st_size - 1)

        monkeypatch.setattr(type(value), "iter_events", truncate)
        with pytest.raises(analysis.AnalysisError, match="grid_artifact_changed_or_unverified"):
            analysis._reduce_qualification_grid(value)
        assert passes == 2
    finally:
        recorder._stream.close()


def test_fixed_prefix_excludes_successful_later_append(map_engine_factory, tmp_path):
    recorder, run = _partial(map_engine_factory, tmp_path)
    try:
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        frames = {name: AssayStimuli(11, "qualification").frame(name) for name in ("A", "B", "C")}
        q._observe_segments(run, q._trial_segments(q.GRID[0], "A", paired=False)[1:], frames, learning=False)
        recorder.flush()
        result = analysis._reduce_qualification_grid(value)
        assert result.outcome == "inconclusive" and result.unit_count == 1
    finally:
        recorder._stream.close()


@pytest.mark.parametrize("empty", [1, 2])
def test_authentic_empty_candidate_map_keeps_available_prefix(map_engine_factory, tmp_path, empty):
    factory = lambda: map_engine_factory(empty=empty)
    recorder, run = _partial(factory, tmp_path)
    try:
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
        assert analysis._reduce_qualification_grid(value).outcome == "inconclusive"
    finally:
        recorder._stream.close()


def test_common_prefix_declarations_do_not_invent_sealed_fields(map_engine_factory, tmp_path):
    recorder, run = _partial(map_engine_factory, tmp_path, "baseline")
    try:
        manifest = recorder.validate_prefix().manifest
        assert "events_sha256" not in manifest and "format_version" not in manifest
        assert analysis._qualification_declarations(manifest) == recorder.metadata
        with pytest.raises(analysis.AnalysisError):
            analysis._qualification_manifest(manifest)
    finally:
        recorder._stream.close()


def test_pending_ingest_fails_current_prefix_but_not_older_boundary(map_engine_factory, tmp_path):
    from fly_connectome_sim.experiment.recorder import RunArtifactError

    recorder, run = _partial(map_engine_factory, tmp_path, "baseline")
    try:
        older = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        recorder.ingest_checkpoint("pending.npz", tmp_path / "baseline.npz",
                                   origin_branch_id="qualification/baseline")
        with pytest.raises(RunArtifactError):
            recorder.validate_prefix()
        assert analysis._reduce_qualification_grid(older).unit_count == 0
    finally:
        recorder._stream.close()


def test_early_actual_final_checkpoint_is_an_ownership_error(map_engine_factory, tmp_path):
    recorder, run = _partial(map_engine_factory, tmp_path)
    try:
        run.checkpoint(tmp_path / "final.npz", logical_name="brain-after.npz")
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        with pytest.raises(analysis.AnalysisError, match="grid_early_final"):
            analysis._reduce_qualification_grid(value)
    finally:
        recorder._stream.close()


def test_wrong_next_unit_is_rejected(map_engine_factory, tmp_path):
    recorder, run = _partial(map_engine_factory, tmp_path)
    clone = None
    try:
        def mutate(events):
            events[-2]["branch_id"] = "grid0/seed11/pairedA/orderBA/pre/A"
            events[-1]["branch_id"] = "grid0/seed11/pairedA/orderBA/pre/A"

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
        with pytest.raises(analysis.AnalysisError, match="grid_role_order"):
            analysis._reduce_qualification_grid(value)
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()


def test_pure_zero_retention_requires_real_occurrence_not_a_call():
    """Synthetic role mechanics only; genuine later-grid coverage is opt-in."""
    from fly_connectome_sim.experiment import qualification_grid as grid

    plan = next(plan for plan in grid._plans(42, 0)
                if plan.kind == "retention" and plan.condition == "paired" and plan.retention == 10000)
    assert plan.segments == () and plan.checkpoint and plan.start == 206000
    role = grid._Role(plan, 10, {})
    assert not role.complete
    role.occurrence = {"synthetic_mechanics": True}
    assert role.complete and role.calls == []


def _synthetic_base_inventory():
    """Hand-built cursor state only, never native evidence or accepted context."""
    from fly_connectome_sim.experiment import qualification_grid as grid

    baseline = {"checkpoint_name": "brain-before.npz", "checkpoint_sha256": "1" * 64,
                "origin_branch_id": "qualification/baseline", "checkpoint_sequence": 0, "sim_tick": 0}
    inventory = grid._Inventory({"checkpoints": {}})
    inventory.baseline = baseline
    unit = grid._Unit(0, grid._plans(0, 0))
    inventory.units.append(unit)
    for index, plan in enumerate(unit.plans[:8]):
        occurrence = ({"checkpoint_name": f"synthetic-{index}.npz", "checkpoint_sha256": "2" * 64,
                       "origin_branch_id": plan.branch, "checkpoint_sequence": 100 + index,
                       "sim_tick": grid._end(plan)} if plan.checkpoint else None)
        unit.roles[plan.branch] = grid._Role(plan, index, baseline,
            calls=list(range(len(plan.segments))), occurrence=occurrence)
    inventory.active = next(reversed(unit.roles.values()))
    return inventory, unit


def test_pure_whole_failed_T_recovery_tail_is_unresolved_not_a_role_gap():
    """Synthetic cursor mechanics; no failure or scientific negative invented."""
    inventory, unit = _synthetic_base_inventory()
    plan = next(plan for plan in unit.plans if plan.retention == 20000)
    parent = unit.roles[plan.parent].occurrence
    inventory.consume({"type": "qualification_restore", "sequence": 200, "branch_id": plan.branch,
        "parent_branch_id": parent["origin_branch_id"], "parent_checkpoint_name": parent["checkpoint_name"],
        "parent_checkpoint_sequence": parent["checkpoint_sequence"],
        "parent_checkpoint_sha256": parent["checkpoint_sha256"], "checkpoint_sha256": parent["checkpoint_sha256"],
        "sim_tick": plan.start, "sim_ms": plan.start / 10})
    assert len(inventory.units) == 1 and inventory.bound == 0


def test_pure_wire_comparison_visits_dataclass_without_vector_copy():
    """Hand data only; wire comparison is separate from native authentication."""
    from fly_connectome_sim.experiment import qualification_grid as grid

    expected = q._ResponseCounts(3, 1000, (1, 2, 3), (4, 5, 6), 1, 2, 3)
    grid._equal(asdict(expected), expected, "synthetic_wire_mismatch")


def test_pure_failure_stage_cannot_jump_over_its_partial_role():
    """Synthetic binding mechanics; inconsistent failure label must not hide gaps."""
    from fly_connectome_sim.experiment import qualification_grid as grid

    inventory, unit = _synthetic_base_inventory()
    plan = next(plan for plan in unit.plans if plan.retention == 10000)
    unit.roles[plan.branch] = grid._Role(plan, 200, unit.roles[plan.parent].occurrence, calls=[201])
    sequences = {name: {} for name in ("pre", "training", "retention", "post")}
    training = {}
    for role in unit.roles.values():
        target = sequences
        for key in role.plan.path[:-1]:
            target = target.setdefault(key, {})
        target[role.plan.path[-1]] = role.calls
        if role.occurrence:
            training[role.plan.condition] = role.occurrence
    failures = [{"scope": "retention", "stage": "post", "condition": "matched_reference",
                 "stimulus": "A", "retention_ms": 10000, "reason": "nonfinite"}]
    sequences["post"] = {"10000": {"matched_reference": {"A": []}}}
    for retention in (20000, 30000, 60000):
        failures.append({"scope": "retention", "stage": "retention", "condition": "paired",
                         "stimulus": None, "retention_ms": retention, "reason": "nonfinite"})
        sequences["retention"][str(retention)] = {"paired": []}
    binding = {"binding_version": "qualification-grid-binding/v1", "grid_evidence_id": "grid/0/11/A/AB",
               "grid_index": 0, "seed": 11, "paired_identity": "A", "presentation_order": "AB",
               "baseline_occurrence": inventory.baseline, "observation_sequences": sequences,
               "training_occurrences": training, "retained_occurrences": {}, "failures": failures}
    with pytest.raises(analysis.AnalysisError, match="grid_failure"):
        grid._binding(binding, unit, inventory.baseline)


def _first_unit_copy(recorder, tmp_path, mode):
    """Streaming adversarial/EOF view of actual first-unit native evidence."""
    clone = RunRecorder(tmp_path / mode, run_kind="qualification", metadata=recorder.metadata,
                        root_branch_id="qualification/baseline")
    sequence_map, branch_parents = {}, {}
    owned = {"sequence", "previous_scientific_sha256", "scientific_sha256", "run_metadata_sha256"}
    first_prefix = "grid0/seed11/pairedA/orderAB/"
    binding_seen = False
    for line in (recorder.path / "events.jsonl").open(encoding="utf8"):
        event = json.loads(line)
        if event["type"] == "qualification_grid_binding":
            binding_seen = True
            if mode != "interior_binding":
                break
            continue
        if mode == "recovery_tail" and "/T10000/" in event["branch_id"]:
            continue
        old_sequence = event["sequence"]
        if event["type"] == "qualification_checkpoint":
            source = recorder.path / "checkpoints" / event["checkpoint_name"]
            if mode == "discarded_source" and event["branch_id"] == first_prefix + "paired/training":
                source = recorder.path / "checkpoints" / "brain-before.npz"
            digest = clone.ingest_checkpoint(event["checkpoint_name"], source, origin_branch_id=event["branch_id"])
            event.update(checkpoint_sha256=digest, checkpoint_size=source.stat().st_size)
        if event["type"] == "qualification_restore":
            event["parent_checkpoint_sequence"] = sequence_map[event["parent_checkpoint_sequence"]]
            event["checkpoint_sha256"] = clone._checkpoints[event["parent_checkpoint_name"]]["sha256"]
            event["parent_checkpoint_sha256"] = event["checkpoint_sha256"]
            branch_parents[event["branch_id"]] = event["checkpoint_sha256"]
        elif "parent_checkpoint_sha256" in event:
            event["parent_checkpoint_sha256"] = branch_parents.get(event["branch_id"], event["parent_checkpoint_sha256"])
        sequence_map[old_sequence] = clone.next_sequence
        clone.append({key: value for key, value in event.items() if key not in owned})
        if binding_seen:
            break  # one later actual restore makes the omitted binding interior
    clone.flush()
    return clone


def test_one_configuration_all_factors_reconstructs_twelve_points(map_engine_factory, tmp_path, monkeypatch):
    """Root-budgeted eight factors; eleven configurations remain unmeasured."""
    started = time.perf_counter()
    recorder, run = _partial(map_engine_factory, tmp_path, "baseline")
    baseline = tmp_path / "baseline.npz"
    measurements = {(window, retention): [] for window in q.RESPONSE_WINDOWS
                    for retention in q.RETENTION_CANDIDATES_MS}
    try:
        for seed in q.QUALIFICATION_SEEDS:
            frames = {name: AssayStimuli(seed, "qualification").frame(name) for name in ("A", "B", "C")}
            for paired in ("A", "B"):
                for order in ("AB", "BA"):
                    run.begin_grid(baseline, 0, seed, paired, order)
                    base = q._replicate_base(run, tmp_path, baseline, q.GRID[0], seed, paired, order, frames)
                    for retention in q.RETENTION_CANDIDATES_MS:
                        retained, maximum, onset = q._retained_tests(
                            run, tmp_path, base, q.GRID[0], frames, paired, retention)
                        for window in q.RESPONSE_WINDOWS:
                            measurements[(window, retention)].append(replace(q._measurement(
                                run, base, retained, maximum, onset, q.GRID[0], window, seed, paired, order),
                                grid_evidence_id=f"grid/0/{seed}/{paired}/{order}"))
                    run.finish_grid(baseline)
        partial_point_prefix = None
        emitted = 0
        for window in q.RESPONSE_WINDOWS:
            for retention in q.RETENTION_CANDIDATES_MS:
                replicas = tuple(measurements[(window, retention)])
                summary = q._summarize_point(q.GRID[0], window, retention,
                                            tuple(q._replicate_summary(item) for item in replicas))
                run.emit({"type": "qualification_point", "branch_id": "qualification/summary", "sim_ms": 0.0,
                    "parent_branch_id": "qualification/baseline",
                    "parent_checkpoint_sha256": run.checkpoints[baseline][1],
                    "point": asdict(q.QualificationPoint(q.GRID[0], window, retention, replicas,
                                                         summary.mean_delta_hz, summary.reasons))})
                emitted += 1
                if emitted == 3:
                    partial_point_prefix = recorder.validate_prefix()
        recorder.flush()
        producer_seconds = time.perf_counter() - started
        started = time.perf_counter()
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        verifier_seconds = time.perf_counter() - started
        from fly_connectome_sim.experiment import qualification_grid as grid
        original_asdict = grid.asdict

        def scalar_asdict(value):
            assert isinstance(value, (q.GridConfiguration, q.ResponseWindow)), "no replica/vector deepcopy"
            return original_asdict(value)

        monkeypatch.setattr(grid, "asdict", scalar_asdict)
        unit_refs = []
        maximum_units = 0
        original_measure = grid._measure_unit

        def bounded_units(*args):
            nonlocal maximum_units
            result = original_measure(*args)
            unit_refs.append(weakref.ref(result[0][0]))
            live = sum(reference() is not None for reference in unit_refs)
            maximum_units = max(maximum_units, live)
            assert live <= 8
            return result

        monkeypatch.setattr(grid, "_measure_unit", bounded_units)
        started = time.perf_counter()
        result = analysis._reduce_qualification_grid(value)
        reducer_seconds = time.perf_counter() - started
        assert result.outcome == "inconclusive" and result.selection is None and result.unit_count == 8
        assert len(result.points) == 12
        assert maximum_units == 8 and all(reference() is None for reference in unit_refs)
        assert [point.mean_delta_hz for point in result.points] == [None] * 12
        sizes = [item["size"] for item in value.manifest["checkpoints"].values()]
        budget = {"producer_seconds": producer_seconds, "verifier_seconds": verifier_seconds,
                  "reducer_seconds": reducer_seconds, "events": value.manifest["event_count"],
                  "event_bytes": (value.path / "events.jsonl").stat().st_size,
                  "checkpoints": len(sizes), "checkpoint_bytes": sum(sizes),
                  "max_checkpoint_bytes": max(sizes), "simulated_ticks": q._ticks(run.simulated_ms),
                  "source_identity": run.identity["model_provenance"]["model_fingerprint"]}
        started = time.perf_counter()
        partial = verify_replay_prefix(partial_point_prefix, engine_factory=map_engine_factory)
        budget["partial_point_verifier_seconds"] = time.perf_counter() - started
        started = time.perf_counter()
        partial_result = analysis._reduce_qualification_grid(partial)
        budget["partial_point_reducer_seconds"] = time.perf_counter() - started
        assert partial_result.outcome == "inconclusive" and partial_result.unit_count == 8
        assert partial_result.selection is None and partial_result.points == result.points[:3]
        assert all(reference() is None for reference in unit_refs)
        budget["reused_first_unit_views"] = {}
        for mode in ("unbound_tail", "recovery_tail", "interior_binding", "discarded_source"):
            clone = _first_unit_copy(recorder, tmp_path, mode)
            try:
                started = time.perf_counter()
                view = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
                verified_seconds = time.perf_counter() - started
                started = time.perf_counter()
                if mode in ("interior_binding", "discarded_source"):
                    with pytest.raises(analysis.AnalysisError):
                        analysis._reduce_qualification_grid(view)
                else:
                    tail = analysis._reduce_qualification_grid(view)
                    assert tail.outcome == "inconclusive" and tail.selection is None and tail.unit_count == 1
                budget["reused_first_unit_views"][mode] = {"verifier_seconds": verified_seconds,
                    "reducer_seconds": time.perf_counter() - started,
                    "events": view.manifest["event_count"], "checkpoints": len(view.manifest["checkpoints"])}
            finally:
                clone._stream.close()
        (tmp_path / "configuration-budget.json").write_text(json.dumps(budget, indent=2), encoding="utf8")
    finally:
        recorder._stream.close()


@pytest.mark.skipif(os.getenv("FLY_CONNECTOME_SIM_FULL_TEST") != "1",
                    reason="complete96-unit native grid reduction is explicitly costly opt-in")
def test_complete_native_negative_grid_prefix_and_seal(map_engine_factory, tmp_path):
    from fly_connectome_sim.experiment.recorder import verify_replay_run

    engine = map_engine_factory()
    recorder = RunRecorder(tmp_path / "complete", run_kind="qualification",
        metadata=_qualification_metadata(engine.identity()), root_branch_id="qualification/baseline")
    del engine
    budget = {"scope": "actual complete tiny-native qualification grid; not whole-assay capacity"}
    try:
        started = time.perf_counter()
        result = q.qualify(map_engine_factory, recorder, seeds=q.QUALIFICATION_SEEDS, family="qualification")
        budget["producer_seconds"] = time.perf_counter() - started
        recorder.flush()
        sizes = [item["size"] for item in recorder._checkpoints.values()]
        budget.update(events=recorder.next_sequence,
            event_bytes=(recorder.path / "events.jsonl").stat().st_size, checkpoints=len(sizes),
            checkpoint_bytes=sum(sizes), max_checkpoint_bytes=max(sizes),
            simulated_ticks=q._ticks(result.benchmark["simulated_seconds"] * 1000),
            source_identity=recorder.metadata["engine_identity"]["model_provenance"]["model_fingerprint"])
        assert result.status == "unsupported"
        started = time.perf_counter()
        prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        budget["prefix_verifier_seconds"] = time.perf_counter() - started
        started = time.perf_counter()
        reduced = analysis._reduce_qualification_grid(prefix)
        budget["prefix_reducer_seconds"] = time.perf_counter() - started
        assert reduced.outcome == "negative" and reduced.unit_count == 96 and len(reduced.points) == 144
        recorder.close()
        started = time.perf_counter()
        sealed = verify_replay_run(recorder.path, engine_factory=map_engine_factory)
        budget["sealed_verifier_seconds"] = time.perf_counter() - started
        started = time.perf_counter()
        assert analysis._reduce_qualification_grid(sealed) == reduced
        budget["sealed_reducer_seconds"] = time.perf_counter() - started
        sizes = [item["size"] for item in sealed.manifest["checkpoints"].values()]
        budget.update(events=sealed.manifest["event_count"],
            event_bytes=(sealed.path / "events.jsonl").stat().st_size, checkpoints=len(sizes),
            checkpoint_bytes=sum(sizes), max_checkpoint_bytes=max(sizes),
            simulated_ticks=q._ticks(result.benchmark["simulated_seconds"] * 1000),
            unit_count=reduced.unit_count, points=len(reduced.points),
            source_identity=recorder.metadata["engine_identity"]["model_provenance"]["model_fingerprint"])
    finally:
        (tmp_path / "complete-grid-budget.json").write_text(json.dumps(budget, indent=2), encoding="utf8")
        recorder._stream.close()


@pytest.mark.skipif(os.getenv("FLY_CONNECTOME_SIM_FULL_TEST") != "1",
                    reason="actual MaleCNS baseline decoder/projection route is opt-in")
def test_fullgraph_native_baseline_prefix_reduces_without_engine(tmp_path, monkeypatch):
    import gc
    import weakref
    from fly_connectome_sim.engine import FlyEngine
    from fly_connectome_sim.neural import native

    producer = FlyEngine.from_prepared_graph()
    recorder = RunRecorder(tmp_path / "fullgraph", run_kind="qualification",
        metadata=_qualification_metadata(producer.identity()), root_branch_id="qualification/baseline")
    try:
        run = q._Run(producer, recorder, producer.identity())
        run.checkpoint(tmp_path / "baseline.npz")
        prefix = recorder.validate_prefix()
        producer_ref = weakref.ref(producer)
        del run, producer
        gc.collect()
        assert producer_ref() is None
        verifier_refs = []

        def factory():
            engine = FlyEngine.from_prepared_graph()
            verifier_refs.append(weakref.ref(engine))
            return engine

        value = verify_replay_prefix(prefix, engine_factory=factory)
        gc.collect()
        assert len(verifier_refs) == 1 and verifier_refs[0]() is None

        def forbidden(*args, **kwargs):
            pytest.fail("grid reconstruction must remain engine-free")

        monkeypatch.setattr(FlyEngine, "from_prepared_graph", forbidden)
        monkeypatch.setattr(native, "build_native", forbidden)
        result = analysis._reduce_qualification_grid(value)
        assert result.outcome == "inconclusive" and result.unit_count == 0 and result.points == ()
    finally:
        recorder._stream.close()


def test_fix1_native_float64_lower_clamp_and_real_endpoint(map_engine_factory, tmp_path):
    """Declared stress fixture reaches a negative clamp, never scientific support."""
    factory = lambda: map_engine_factory(eta=1.0, tonic=[20, 0, 0, 0, 0, 0, 0, 0])
    recorder, run = _training_prefix(factory, tmp_path)
    try:
        assert run.engine.brain.memory_u.dtype == np.float64
        assert run.engine.brain.memory_w.dtype == np.float64
        assert run.engine.brain.weight.dtype == np.float32
        lower = run.engine.brain.rule_parameters["minimum_fraction"] - 1
        saturated = []
        for event in recorder.validate_prefix().iter_events():
            if event["type"] == "qualification_observation":
                for item in event["telemetry"]["bins"]:
                    detail = item["qualification_detail"]
                    if detail["memory_u"]["minimum"] == lower:
                        saturated.append(detail)
        assert saturated and all(detail["lower_bound_hits"] > 0 for detail in saturated)
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
        result = analysis._reduce_qualification_grid(value)
        assert result.outcome == "inconclusive" and result.unit_count == 1
    finally:
        recorder._stream.close()


def test_fix1_pure_float64_neighbor_uses_unrounded_engine_bounds():
    """Independent summary oracle, not fabricated native telemetry or context."""
    from fly_connectome_sim.experiment import qualification_grid as grid
    from fly_connectome_sim.engine import _array_summary

    parameters = {"minimum_fraction": 0.1, "maximum_fraction": 2.0}
    assert hasattr(grid, "_memory_bounds"), "raw/endpoint bounds must share the actual native dtype seam"
    lower, upper = grid._memory_bounds(parameters)
    neighbor = np.nextafter(np.float64(-0.9), np.float64(np.inf))
    assert lower == -0.9 and -0.9 < neighbor < np.float32(-0.9)
    for value in (-0.9, neighbor):
        vector = np.array([value], dtype=np.float64)
        grid._summary(_array_summary(vector), 1, "synthetic_float64_summary", lower=lower, upper=upper)
    assert np.count_nonzero(np.array([-0.9]) <= lower) == 1
    assert np.count_nonzero(np.array([neighbor]) <= lower) == 0


@pytest.mark.parametrize("known_empty", [True, False])
def test_fix1_real_bound_empty_absence_is_not_unknown_data(map_engine_factory, tmp_path, monkeypatch, known_empty):
    """Real complete base; nonempty control has an explicitly declared unknown failure."""
    from fly_connectome_sim.experiment import qualification_grid as grid

    factory = lambda: map_engine_factory(empty=1 if known_empty else 0)
    recorder, run = _partial(factory, tmp_path, "baseline")
    baseline = tmp_path / "baseline.npz"
    frames = {name: AssayStimuli(11, "qualification").frame(name) for name in ("A", "B", "C")}
    run.begin_grid(baseline, 0, 11, "A", "AB")
    try:
        try:
            q._replicate_base(run, tmp_path, baseline, q.GRID[0], 11, "A", "AB", frames)
        except q._GateFailure as failure:
            assert known_empty and failure.reason == "missing_mbon11_observability"
            reason = failure.reason
        else:
            assert not known_empty
            reason = "nonfinite"  # unknown diagnostic control; not a claimed native fault
        run.grid_failure(reason)
        expected = [replace(q._failed_measurement(run, window, 11, "A", "AB", reason, run.partial_base),
                            grid_evidence_id="grid/0/11/A/AB")
                    for window in q.RESPONSE_WINDOWS for retention in q.RETENTION_CANDIDATES_MS]
        run.finish_grid(baseline)
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
        reconstructed = []
        flags = []
        original = grid._measure_unit

        def capture(*args):
            result = original(*args)
            reconstructed.extend(result[0])
            flags.append(result[1])
            return result

        monkeypatch.setattr(grid, "_measure_unit", capture)
        result = analysis._reduce_qualification_grid(value)
        assert [asdict(item) for item in reconstructed] == [asdict(item) for item in expected]
        assert flags == [not known_empty]
        assert result.outcome == "inconclusive" and result.unit_count == 1 and result.points == ()
        assert result.reasons == (("grid_incomplete",) if known_empty else ("grid_unavailable",))
    finally:
        recorder._stream.close()


@pytest.mark.parametrize("attack", ["missing_candidate_count", "one_KC_over_call_ticks", "complement_over_call_ticks"])
def test_fix1_coherent_count_attacks_fail_native_issued_consumer(map_engine_factory, tmp_path, attack):
    from hashlib import sha256

    factory = lambda: map_engine_factory(extra_kc=attack == "complement_over_call_ticks")
    recorder, run = _partial(factory, tmp_path)
    clone = None
    try:
        def mutate(events):
            event = events[-1]
            telemetry = event["telemetry"]
            ticks = event["duration_ticks"]
            total = 1 if attack == "missing_candidate_count" else ticks + 1
            counts = [total, 0] if attack == "one_KC_over_call_ticks" else [0, 0]
            path = telemetry["pathway_detail"]
            path["candidate_kc_spike_counts"] = counts
            path["candidate_kc_spikes_by_source_id"] = dict(zip(path["candidate_kc_source_ids"], counts))
            remaining = total
            population = len(run.engine.groups.kc)
            for item in telemetry["bins"]:
                count = min(remaining, q._ticks(item["duration_ms"]) * population)
                item["group_spikes"]["kc"] = count
                remaining -= count
            assert remaining == 0
            telemetry["rates_hz"]["kc"] = q._response_rate(total, ticks, population)
            telemetry["total_spikes"] = total
            per_neuron = np.zeros(8, dtype=np.int64)
            per_neuron[6 if attack == "complement_over_call_ticks" else 0] = total
            telemetry["spike_sha256"] = sha256(per_neuron.tobytes()).hexdigest()

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=factory)
        with pytest.raises(analysis.AnalysisError, match="grid_raw_kc_(count|residual)"):
            analysis._reduce_qualification_grid(value)
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()


def test_fix1_real_strict_subset_positive_residual_is_accepted(map_engine_factory, tmp_path):
    factory = lambda: map_engine_factory(extra_kc=True)
    recorder, run = _partial(factory, tmp_path)
    try:
        event = list(recorder.validate_prefix().iter_events())[-1]
        candidate = event["telemetry"]["pathway_detail"]["candidate_kc_spike_counts"]
        total = sum(item["group_spikes"]["kc"] for item in event["telemetry"]["bins"])
        assert set(run.engine.groups.kc) - set(event["telemetry"]["pathway_detail"]["candidate_kc_indices"]) == {6}
        assert 0 < total - sum(candidate) <= event["duration_ticks"]
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
        assert analysis._reduce_qualification_grid(value).outcome == "inconclusive"
    finally:
        recorder._stream.close()


def test_fix1_real_signed_DAN_trace_is_finite_and_engine_free(map_engine_factory, tmp_path):
    import sys
    from fly_connectome_sim.engine import FlyEngine
    from fly_connectome_sim.neural import native

    factory = lambda: map_engine_factory(dan_baseline_hz=[5.0, 7.0])
    recorder, run = _partial(factory, tmp_path)
    try:
        observation = list(recorder.validate_prefix().iter_events())[-1]
        assert all(np.isfinite(value) and value < 0 for value in
                   observation["telemetry"]["bins"][-1]["qualification_detail"]["rate_dan"])
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
        forbidden = {FlyEngine.__init__.__code__, FlyEngine.observe.__code__, native.build_native.__code__}
        calls = []
        previous = sys.getprofile()

        def profile(frame, event, argument):
            if event == "call" and frame.f_code in forbidden:
                calls.append(frame.f_code.co_name)

        try:
            sys.setprofile(profile)
            result = analysis._reduce_qualification_grid(value)
        finally:
            sys.setprofile(previous)
        assert result.outcome == "inconclusive" and result.unit_count == 1
        assert calls == []
    finally:
        recorder._stream.close()


def test_fix2_negative_drive_count_rejected_after_native_issuance(map_engine_factory, tmp_path, monkeypatch):
    recorder, run = _partial(map_engine_factory, tmp_path)
    clone = None
    try:
        def mutate(events):
            summary = events[-1]["telemetry"]["pathway_detail"]["modeled_visual_drive"]["r8"]
            assert summary["minimum"] == summary["mean"] == summary["maximum"] == 0
            summary["count"] = -1

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
        completed = []
        original = type(value).iter_events

        def counted(self):
            count = 0
            for event in original(self):
                count += 1
                yield event
            completed.append(count)

        monkeypatch.setattr(type(value), "iter_events", counted)
        with pytest.raises(analysis.AnalysisError, match="^grid_raw_drive$"):
            analysis._reduce_qualification_grid(value)
        assert completed == [3, 3]
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()


def test_fix2_genuine_positive_count_zero_drive_still_accepted(map_engine_factory, tmp_path):
    recorder, run = _partial(map_engine_factory, tmp_path)
    try:
        observation = list(recorder.validate_prefix().iter_events())[-1]
        summary = observation["telemetry"]["pathway_detail"]["modeled_visual_drive"]["r8"]
        assert summary["count"] == 1 and summary["minimum"] == summary["mean"] == summary["maximum"] == 0
        value = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        assert analysis._reduce_qualification_grid(value).outcome == "inconclusive"
    finally:
        recorder._stream.close()


def test_fix2_pure_real_empty_array_summary_preserves_nulls():
    """Actual engine summary writer on an empty array; not a native prefix claim."""
    from fly_connectome_sim.engine import _array_summary
    from fly_connectome_sim.experiment import qualification_grid as grid

    summary = _array_summary(np.empty(0, dtype=np.float64))
    assert summary["count"] == 0 and all(summary[name] is None for name in ("minimum", "mean", "maximum"))
    grid._summary(summary, 0, "synthetic_empty_drive", lower=0, upper=float("inf"))
    with pytest.raises(analysis.AnalysisError, match="synthetic_empty_drive"):
        grid._summary({**summary, "mean": 0.0}, 0, "synthetic_empty_drive", lower=0, upper=float("inf"))


@pytest.mark.parametrize("count", [-1, True, 1.0])
def test_fix2_pure_summary_count_requires_nonnegative_integer(count):
    from fly_connectome_sim.engine import _array_summary
    from fly_connectome_sim.experiment import qualification_grid as grid

    summary = {**_array_summary(np.array([0.0])), "count": count}
    with pytest.raises(analysis.AnalysisError, match="synthetic_drive_count"):
        grid._summary(summary, count, "synthetic_drive_count", lower=0, upper=float("inf"))


@pytest.mark.parametrize("kind", ["empty_digest", "singleton_maximum"])
def test_fix2_native_summary_writer_invariants_reject_coherent_tamper(map_engine_factory, tmp_path, monkeypatch, kind):
    if kind == "empty_digest":
        # Test-local declaration before the first engine/identity/provenance lock.
        # Keep the independent R8 path nonempty; only R1-R6 sampling is empty.
        graph_path = tmp_path / "map-graph.npz"
        with np.load(graph_path, allow_pickle=False) as archive:
            graph = {name: archive[name] for name in archive.files}
        graph.update(retina=np.empty(0, dtype=np.int32), uv=np.empty((0, 2), dtype=np.float32))
        np.savez(graph_path, **graph)
    recorder, run = _partial(map_engine_factory, tmp_path)
    clone = None
    try:
        # Untouched real empty/singleton engine summaries remain accepted.
        control = verify_replay_prefix(recorder.validate_prefix(), engine_factory=map_engine_factory)
        assert analysis._reduce_qualification_grid(control).outcome == "inconclusive"

        def mutate(events):
            drive = events[-1]["telemetry"]["pathway_detail"]["modeled_visual_drive"]
            assert drive["r8"]["count"] == 1
            if kind == "empty_digest":
                summary = drive["r1_r6"]
                assert summary["count"] == 0 and all(summary[name] is None for name in ("minimum", "mean", "maximum"))
                summary["sha256"] = "0" * 64
            else:
                summary = drive["r8"]
                assert summary["minimum"] == summary["mean"] == summary["maximum"] == 0
                summary["maximum"] = 1.0  # mean stays0: black-drive rejection cannot mask this case

        clone = _clone(recorder, tmp_path, mutate)
        value = verify_replay_prefix(clone.validate_prefix(), engine_factory=map_engine_factory)
        original = type(value).iter_events
        completed = []

        def counted(self):
            count = 0
            for event in original(self):
                count += 1
                yield event
            completed.append(count)

        monkeypatch.setattr(type(value), "iter_events", counted)
        with pytest.raises(analysis.AnalysisError, match="^grid_raw_drive$"):
            analysis._reduce_qualification_grid(value)
        assert completed == [3, 3]
    finally:
        recorder._stream.close()
        if clone:
            clone._stream.close()
