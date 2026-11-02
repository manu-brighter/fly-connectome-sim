"""Hand-checked contracts for the frozen MBON11 assay boundary."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from functools import lru_cache
from hashlib import sha256
import json

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment.analysis import (
    AnalysisError,
    FrozenAssayConfig,
    analyze_assay,
    assess_assay_evidence,
    build_frozen_config,
    reduce_assay_evidence,
)
from fly_connectome_sim.experiment.recorder import RunRecorder, VerifiedRun, verify_run
from fly_connectome_sim.experiment.stimuli import AssayStimuli
from fly_connectome_sim.experiment.qualification import (
    GRID, RESPONSE_WINDOWS, RETENTION_CANDIDATES_MS, GridConfiguration,
    _training_timeline,
)
from replay_helpers import engine_factory, map_engine_factory, _declared_native_frozen_config


H = {name: sha256(name.encode()).hexdigest() for name in (
    "before", "after", "donor", "recipient", "necessity", "sufficiency",
     "sham", "input_a", "input_b", "input_c", "black", "events", "schema",
     "scientific", "metadata", "model", "memory_donor", "memory_recipient",
     "memory_after", "noncandidate", "qual_a", "qual_b", "qual_c",
     "qual_black",
)}
CONFIGURATION = {"cs_duration_ms": 100.0, "dan_onset_ms": 0.0,
                 "post_pair_gap_ms": 500.0}
WINDOW = {"start_ms": 0.0, "end_ms": 100.0}
CONDITIONS = ("paired", "frozen_plasticity", "no_external_dan",
              "temporally_unpaired", "matched_reference", "necessity",
              "sufficiency", "sham")
INTERVENTIONS = ("necessity", "sufficiency", "sham")
ORDINARY = ("paired", "frozen_plasticity", "no_external_dan",
            "temporally_unpaired", "matched_reference")
BASE_TICK = 100000


@pytest.fixture
def selected_replay_pair(engine_factory, tmp_path, request):
    """Actual tiny-native PRE consistency data, without native-history attestation."""
    from fly_connectome_sim.cli import _qualification_metadata
    from fly_connectome_sim.experiment.replay import OPERATION_VERSION, build_black_retention_recipe, build_state_anchor
    from fly_connectome_sim.experiment.analysis import _training_plan
    options = getattr(request, "param", {})
    cs = options.get("cs", 100.0)
    if options.get("ppl_tonic"):
        tonic = np.zeros(8, dtype=np.float32)
        tonic[3] = 20.0
        configured = request.getfixturevalue("map_engine_factory")
        def engine_factory():
            return configured(tonic=tonic)
    native = engine_factory()
    native.brain.weights_frozen = options.get("frozen", False)
    metadata = _qualification_metadata(native.identity())
    recorder = RunRecorder(tmp_path / "selected-replay", run_kind="qualification", metadata=metadata,
                           root_branch_id="qualification/baseline")
    path = tmp_path / "baseline.npz"
    native.brain.checkpoint(path)
    digest = recorder.ingest_checkpoint("brain-before.npz", path, origin_branch_id="qualification/baseline")
    source = {"checkpoint_name": "brain-before.npz", "checkpoint_sha256": digest,
              "checkpoint_sequence": 0, "origin_branch_id": "qualification/baseline", "sim_tick": 0}
    recorder.append({"type": "qualification_checkpoint", "branch_id": "qualification/baseline",
                     "sim_ms": 0.0, "sim_tick": 0, "checkpoint_name": "brain-before.npz"})
    parent = {"parent_branch_id": source["origin_branch_id"], "parent_checkpoint_name": source["checkpoint_name"],
              "parent_checkpoint_sequence": source["checkpoint_sequence"], "parent_checkpoint_sha256": digest}
    key = {"seed": 11, "paired_identity": "A", "presentation_order": "AB", "phase": "pre", "stimulus": "A"}
    if options.get("post"):
        configuration = {**CONFIGURATION, "cs_duration_ms": cs}
        plan = _training_plan({"selected_configuration": configuration}, 11, "A", "AB", "paired", "qualification", 0)
        branch = "selected/11/A/AB/paired/training"
        recorder.append({"type": "branch_start", "branch_id": branch, "sim_ms": 0.0, **parent})
        for segment in plan["segments"]:
            frame = (np.zeros((32, 32, 3), dtype=np.uint8) if segment["stimulus"] is None
                     else AssayStimuli(11, "qualification").frame(segment["stimulus"]))
            observed = native.observe(frame, (segment["end_tick"] - segment["start_tick"]) / 10,
                                      stimulation=segment["external_stimulation"], learning=segment["learning"])
            recorder.append({"type": "observe", "branch_id": branch, "sim_ms": native.brain.cursor / 10,
                             "telemetry": observed})
        path = tmp_path / "training-end.npz"
        native.brain.checkpoint(path)
        digest = recorder.ingest_checkpoint(path.name, path, origin_branch_id=branch)
        source = {"checkpoint_name": path.name, "checkpoint_sha256": digest, "origin_branch_id": branch,
                  "checkpoint_sequence": recorder.next_sequence, "sim_tick": native.brain.cursor}
        recorder.append({"type": "checkpoint", "branch_id": branch, "sim_ms": native.brain.cursor / 10,
                         "sim_tick": native.brain.cursor, "checkpoint_name": path.name, **parent})
        recorder.append({"type": "qualification_training", "branch_id": branch, "sim_ms": native.brain.cursor / 10,
            "training_version": "associative-training/v1", "training_id": branch, "seed": 11, "paired_identity": "A",
            "presentation_order": "AB", "condition": "paired", "candidate_identity": "kc-mbon11-ppl101/v1",
            "baseline_tick": 0, "baseline_checkpoint_sha256": parent["parent_checkpoint_sha256"],
            "training_end_checkpoint_sha256": digest, **plan, **native.brain.candidate_state_digests(native.groups.mbon11)})
        condition = options.get("condition", "paired")
        if condition == "sham":
            recipient_source = deepcopy(source)
            recipient_parent = {"parent_branch_id": source["origin_branch_id"], "parent_checkpoint_name": source["checkpoint_name"],
                "parent_checkpoint_sequence": source["checkpoint_sequence"], "parent_checkpoint_sha256": source["checkpoint_sha256"]}
            if options.get("wrong_parent_occurrence"):
                alias_digest = recorder.ingest_checkpoint("recipient-alias.npz", path, origin_branch_id=branch)
                alias_sequence = recorder.next_sequence
                recorder.append({"type": "checkpoint", "branch_id": branch, "sim_ms": native.brain.cursor / 10,
                                 "sim_tick": native.brain.cursor, "checkpoint_name": "recipient-alias.npz"})
                assert alias_digest == digest
                recipient_parent.update(parent_checkpoint_name="recipient-alias.npz", parent_checkpoint_sequence=alias_sequence)
            donor, recipient_engine = engine_factory(), engine_factory()
            assert donor.identity() == recipient_engine.identity() == metadata["engine_identity"]
            donor.brain.restore(path)
            recipient_engine.brain.restore(path)
            before = recipient_engine.brain.candidate_state_digests(recipient_engine.groups.mbon11)
            donor_state = donor.brain.candidate_state_digests(donor.groups.mbon11)
            recipient_engine.brain.replace_candidate_memory(donor.brain.candidate_memory(donor.groups.mbon11))
            after = recipient_engine.brain.candidate_state_digests(recipient_engine.groups.mbon11)
            assert before == after == donor_state
            native = recipient_engine
            branch = "selected/11/A/AB/" + ("other" if options.get("wrong_source") else "sham") + "/intervention"
            recorder.append({"type": "branch_start", "branch_id": branch, "sim_ms": native.brain.cursor / 10, **recipient_parent})
            path = tmp_path / "sham-post.npz"
            native.brain.checkpoint(path)
            digest = recorder.ingest_checkpoint(path.name, path, origin_branch_id=branch)
            source = {"checkpoint_name": path.name, "checkpoint_sha256": digest, "origin_branch_id": branch,
                      "checkpoint_sequence": recorder.next_sequence, "sim_tick": native.brain.cursor}
            recorder.append({"type": "checkpoint", "branch_id": branch, "sim_ms": native.brain.cursor / 10,
                             "sim_tick": native.brain.cursor, "checkpoint_name": path.name, **recipient_parent})
            recorder.append({"type": "assay_intervention", "branch_id": branch, "sim_ms": native.brain.cursor / 10,
                "intervention_version": "candidate-memory-replacement/v1", "intervention_id": branch,
                "seed": 11, "paired_identity": "A", "presentation_order": "AB", "condition": "sham",
                "candidate_identity": "kc-mbon11-ppl101/v1", "donor_role": "trained", "recipient_role": "trained",
                "donor_training_id": recipient_source["origin_branch_id"], "recipient_training_id": recipient_source["origin_branch_id"],
                "donor_training_end_tick": donor.brain.cursor, "recipient_training_end_tick": recipient_engine.brain.cursor,
                "donor_checkpoint_sha256": recipient_source["checkpoint_sha256"], "recipient_checkpoint_sha256": recipient_source["checkpoint_sha256"],
                "post_intervention_checkpoint_sha256": digest, "donor_candidate_memory_sha256": donor_state["candidate_memory_sha256"],
                "recipient_candidate_memory_before_sha256": before["candidate_memory_sha256"],
                "recipient_candidate_memory_after_sha256": after["candidate_memory_sha256"],
                "noncandidate_state_before_sha256": before["noncandidate_state_sha256"],
                "noncandidate_state_after_sha256": after["noncandidate_state_sha256"],
                "replaced_components": ["memory_u", "memory_w", "weight"], "complete_replacement": True, **recipient_parent})
        elif options.get("wrong_source"):
            original = source
            branch = "selected/11/A/AB/other/training"
            parent = {"parent_branch_id": original["origin_branch_id"], "parent_checkpoint_name": original["checkpoint_name"],
                      "parent_checkpoint_sequence": original["checkpoint_sequence"], "parent_checkpoint_sha256": original["checkpoint_sha256"]}
            recorder.append({"type": "branch_start", "branch_id": branch, "sim_ms": native.brain.cursor / 10, **parent})
            alias_digest = recorder.ingest_checkpoint("source-alias.npz", path, origin_branch_id=branch)
            source = {"checkpoint_name": "source-alias.npz", "checkpoint_sha256": alias_digest, "origin_branch_id": branch,
                      "checkpoint_sequence": recorder.next_sequence, "sim_tick": native.brain.cursor}
            assert alias_digest == digest
            recorder.append({"type": "checkpoint", "branch_id": branch, "sim_ms": native.brain.cursor / 10,
                             "sim_tick": native.brain.cursor, "checkpoint_name": "source-alias.npz", **parent})
            digest = alias_digest
        retention = options.get("retention", 70000)
        branch = "selected/11/A/AB/" + ("" if condition == "paired" else condition + "/") + f"retention/{retention}"
        parent = {"parent_branch_id": source["origin_branch_id"], "parent_checkpoint_name": source["checkpoint_name"],
                  "parent_checkpoint_sequence": source["checkpoint_sequence"], "parent_checkpoint_sha256": digest}
        recorder.append({"type": "fork", "operation_version": OPERATION_VERSION, "branch_id": branch,
                         "sim_tick": native.brain.cursor, "sim_ms": native.brain.cursor / 10, **parent})
        target = plan["retention_reference_tick"] + retention * 10 - 1000
        while native.brain.cursor < target:
            start = native.brain.cursor
            ticks = min(5000, target - start)
            native.observe(np.zeros((32, 32, 3), dtype=np.uint8), ticks / 10, learning=False, stimulation=None)
            recorder.append({"type": "neutral_gap_chunk", "operation_version": OPERATION_VERSION, "branch_id": branch,
                "sim_ms": native.brain.cursor / 10, "start_tick": start, "end_tick": native.brain.cursor,
                "duration_ticks": ticks, "duration_ms": ticks / 10, "stimulation": None, "learning": False,
                "current_mv": 20.0, "pathway_detail": False, "qualification_detail": False, **metadata["black_input"]})
        prefix = recorder.validate_prefix()
        recipe = build_black_retention_recipe(prefix.iter_events(), source_occurrence=source, origin_branch_id=branch,
            target_tick=target, engine_identity=native.identity(), run_metadata_sha256=prefix.manifest["run_metadata_sha256"],
            black_input=metadata["black_input"], scientific_prefix=prefix.scientific_prefix)
        anchor = build_state_anchor(anchor_id=branch, recipe=recipe, complete_state_sha256=native.brain.checkpoint_state_sha256())
        recorder.append_state_anchor(anchor)
        path = tmp_path / "retained.npz"
        native.brain.checkpoint(path)
        parent = {"parent_branch_id": branch, "parent_state_anchor_sha256": anchor["state_anchor_sha256"]}
        key.update(phase="post", condition=condition, retention_ms=retention)
    original_branch = ("selected/11/A/AB/pre/A" if key["phase"] == "pre" else "selected/11/A/AB/"
                       + ("" if key["condition"] == "paired" else key["condition"] + "/") + f"post/{key['retention_ms']}/A")
    branches = {"original": original_branch, "repeat": original_branch + "/repeat"}
    engines = {side: engine_factory() for side in branches}
    for engine in engines.values():
        engine.brain.restore(path)
    def state(engine, start=False):
        result = {"sim_tick": engine.brain.cursor, "complete_state_sha256": engine.brain.checkpoint_state_sha256()}
        if start:
            result["weights_frozen"] = engine.brain.weights_frozen
        else:
            result.update(engine.brain.candidate_state_digests(engine.groups.mbon11))
        return result
    boundaries = {"start": {side: state(engine, True) for side, engine in engines.items()}}
    operations = {side: [recorder._append_reference({"type": "branch_start", "branch_id": branch,
        "sim_ms": engine.brain.cursor / 10, **parent})] for (side, branch), engine in zip(branches.items(), engines.values())}
    for side, engine in engines.items():
        if engine.brain.weights_frozen:
            operations[side].append(recorder._append_reference({"type": "replay_thaw", "branch_id": branches[side],
                "sim_tick": engine.brain.cursor, "sim_ms": engine.brain.cursor / 10, "operation_version": OPERATION_VERSION,
                "before_weights_frozen": True, "after_weights_frozen": False}))
            engine.brain.weights_frozen = False
    window = {"start_ms": options.get("window_start", 0.0), "end_ms": options.get("window_end", 100.0)}
    onset = native.brain.cursor + 1000
    window_tick = onset + round(window["end_ms"] * 10)
    positions = native.brain._candidate_positions(native.groups.mbon11)
    maps = {"target_indices": native.groups.mbon11.tolist(), "candidate_positions": positions.tolist(),
            "candidate_edge_indices": native.brain.circuit["edges"][positions].tolist()}
    w_pair = None
    window_counts = {side: 0 for side in engines}
    window_start = onset + round(window["start_ms"] * 10)
    schedule = ((100.0, None), (100.0, "A"), (200.0, None)) if cs == 100.0 else (
        (100.0, None), (100.0, "A"), (200.0, "A"), (200.0, None))
    for duration, stimulus in schedule:
        frame = np.zeros((32, 32, 3), dtype=np.uint8) if stimulus is None else AssayStimuli(11, "qualification").frame(stimulus)
        for side, engine in engines.items():
            start = engine.brain.cursor
            observed = engine.observe(frame, duration, learning=False, stimulation=None)
            window_counts[side] += sum(item["group_spikes"]["mbon11"] for item in observed["bins"]
                if window_start < round(item["end_ms"] * 10) <= window_tick)
            operations[side].append(recorder._append_reference({"type": "observe", "branch_id": branches[side],
                "operation_version": OPERATION_VERSION, "start_tick": start, "end_tick": engine.brain.cursor,
                "duration_ticks": round(duration * 10), "duration_ms": duration, "sim_ms": engine.brain.cursor / 10,
                "stimulation": None, "learning": False, "current_mv": 20.0,
                "pathway_detail": False, "qualification_detail": False, "telemetry": observed}))
        if engines["original"].brain.cursor == window_tick:
            boundaries["window"] = {side: state(engine) for side, engine in engines.items()}
            w_pair = {side: engine.brain.memory_w[positions].copy() for side, engine in engines.items()}
    boundaries["final"] = {side: state(engine) for side, engine in engines.items()}
    projection = {"projection_version": "selected-candidate-w-pair/v1", "dtype": "<f8", "shape": [len(positions)],
                  "maps": maps, "original_hex": w_pair["original"].tobytes().hex(),
                  "repeat_hex": w_pair["repeat"].tobytes().hex()}
    diagnostic = {"type": "qualification_replay", "replay_version": "selected-response-repeat/v1",
        "replay_id": branches["repeat"], "branch_id": branches["repeat"], "original_branch_id": branches["original"],
        "physical_key": key,
        "source_occurrence": source, "engine_identity_sha256": native.identity()["sha256"],
        "candidate_identity": "kc-mbon11-ppl101/v1", "population_size": 1,
        "input_sha256": metadata["rgb_input_sha256"]["stimuli"]["11"]["A"],
        "black_sha256": metadata["rgb_input_sha256"]["black"], "response_window": window,
        "cs_onset_tick": onset, "sim_tick": native.brain.cursor, "sim_ms": native.brain.cursor / 10, "operations": operations,
        "boundaries": boundaries, "candidate_projection": projection,
        "response_replay_resolution_hz": abs(window_counts["original"] - window_counts["repeat"]) / ((window_tick - window_start) / 10000.0),
        "candidate_memory_w_resolution": float(np.abs(w_pair["original"] - w_pair["repeat"]).mean()),
        **parent}
    diagnostic.update(sim_tick=engines["repeat"].brain.cursor, sim_ms=engines["repeat"].brain.cursor / 10)
    recorder.append(diagnostic)
    prefix = recorder.validate_prefix()
    diagnostic = list(prefix.iter_events())[-1]
    execution = {"family": "qualification", "seeds": [11, 23], "engine_identity": native.identity(),
        "mbon11_population_size": 1, "candidate_identity": "kc-mbon11-ppl101/v1",
        "selected_configuration": {**CONFIGURATION, "cs_duration_ms": cs}, "response_window": window, "retention_times_ms": [10000, 70000],
        "input_sha256": {seed: {**row, "black": metadata["rgb_input_sha256"]["black"]}
                         for seed, row in metadata["rgb_input_sha256"]["stimuli"].items()}}
    arguments = {"metadata": metadata, "execution": execution, "expected_source_occurrence": source,
        "expected_start": boundaries["start"]["original"], "expected_maps": maps, "n": native.brain.n,
        "memory_count": len(native.brain.memory_w), "edge_count": len(native.brain.weight),
        "lower": native.brain.rule_parameters["minimum_fraction"] - 1,
        "upper": native.brain.rule_parameters["maximum_fraction"] - 1}
    try:
        yield recorder, prefix, diagnostic, arguments
    finally:
        recorder.__exit__(RuntimeError, RuntimeError("unsealed consistency fixture"), None)


def test_selected_replay_actual_native_pair_resolves_real_prefix(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    assert arguments["expected_source_occurrence"]["checkpoint_sha256"] != arguments["expected_start"]["complete_state_sha256"]
    result = analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)
    assert result == {"response_replay_resolution_hz": 0.0, "candidate_memory_w_resolution": 0.0}


def _rewrite_selected_replay(recorder, events, *, repair_references=True):
    """Rehash actual recorded bytes for adversarial consistency tests, not native proof."""
    from fly_connectome_sim.experiment.recorder import _canonical, _scientific_event
    from fly_connectome_sim.experiment.replay import build_black_retention_recipe, build_state_anchor
    previous = "0" * 64
    anchors = {}
    for index, item in enumerate(events):
        item.setdefault("run_metadata_sha256", events[0]["run_metadata_sha256"])
        item.update(sequence=index, previous_scientific_sha256=previous)
        if item.get("parent_state_anchor_sha256") in anchors:
            item["parent_state_anchor_sha256"] = anchors[item["parent_state_anchor_sha256"]]
        if item["type"] == "state_anchor":
            old = item["state_anchor_sha256"]
            recipe = build_black_retention_recipe(events[:index], source_occurrence=item["source_occurrence"],
                origin_branch_id=item["origin_branch_id"], target_tick=item["sim_tick"],
                engine_identity=recorder.metadata["engine_identity"], run_metadata_sha256=item["run_metadata_sha256"],
                black_input=recorder.metadata["black_input"],
                scientific_prefix={"event_count": index, "final_sequence": index - 1, "final_scientific_sha256": previous})
            item.update(build_state_anchor(anchor_id=item["anchor_id"], recipe=recipe,
                                           complete_state_sha256=item["complete_state_sha256"]))
            anchors[old] = item["state_anchor_sha256"]
        if item["type"] == "qualification_replay" and repair_references:
            for references in item["operations"].values():
                for reference in references:
                    reference["scientific_sha256"] = events[reference["sequence"]]["scientific_sha256"]
        item["scientific_sha256"] = sha256(_canonical(_scientific_event(item))).hexdigest()
        previous = item["scientific_sha256"]
    (recorder.path / "events.jsonl").write_bytes(b"".join(_canonical(item) + b"\n" for item in events))
    prefix = recorder.validate_prefix()
    return prefix, next(item for item in prefix.iter_events() if item["type"] == "qualification_replay")


@pytest.mark.parametrize("selected_replay_pair", [{"frozen": True}, {"window_end": 300.0},
    {"cs": 300.0}, {"cs": 300.0, "window_end": 300.0, "frozen": True}], indirect=True)
def test_selected_replay_native_thaw_windows_and_complete_tail(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    result = analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)
    assert result == {"response_replay_resolution_hz": 0.0, "candidate_memory_w_resolution": 0.0}
    if arguments["execution"]["selected_configuration"]["cs_duration_ms"] == 100.0 and diagnostic["response_window"]["end_ms"] == 300.0:
        assert diagnostic["boundaries"]["window"] == diagnostic["boundaries"]["final"]
    else:
        assert diagnostic["boundaries"]["window"] != diagnostic["boundaries"]["final"]


@pytest.mark.parametrize("selected_replay_pair", [{"post": True, "retention": 10000}, {"post": True, "retention": 70000}], indirect=True)
def test_selected_replay_actual_post_parent_and_training_route(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    assert diagnostic["physical_key"]["phase"] == "post"
    assert diagnostic["source_occurrence"]["sim_tick"] == 111000
    assert analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments) == {
        "response_replay_resolution_hz": 0.0, "candidate_memory_w_resolution": 0.0,
    }


@pytest.mark.parametrize("selected_replay_pair", [{"post": True}], indirect=True)
def test_selected_replay_rehashed_post_training_factor_cannot_alias_source_branch(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, prefix, _, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    training = next(item for item in events if item["type"] == "qualification_training")
    training["seed"] = 23
    training.update(analysis._training_plan(arguments["execution"], 23, "A", "AB", "paired", "qualification", 0))
    prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    with pytest.raises(AnalysisError):
        analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)


def _recorded_selected_replay_logical_pair(selected_replay_pair, mutation="valid"):
    from fly_connectome_sim.experiment.qualification import _response_rate
    recorder, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    training = next(item for item in events if item["type"] == "qualification_training")
    onset = diagnostic["cs_onset_tick"]
    window_start = onset + round(diagnostic["response_window"]["start_ms"] * 10)
    stop = diagnostic["boundaries"]["window"]["original"]["sim_tick"]
    observations = [item for item in events if item["type"] == "observe"
                    and item["branch_id"] == diagnostic["original_branch_id"] and item["end_tick"] <= stop]
    raw = [item for observation in observations for item in observation["telemetry"]["bins"]]
    bins = [{"start_tick": round(item["end_ms"] * 10) - round(item["duration_ms"] * 10),
             "end_tick": round(item["end_ms"] * 10), "spikes": item["group_spikes"]["mbon11"]}
            for item in raw if window_start < round(item["end_ms"] * 10) <= stop]
    shared = {name: deepcopy(training[name]) for name in ("training_id", "association_t0_tick", "retention_reference_tick",
        "training_start_tick", "training_end_tick", "last_visual_end_tick", "last_external_dan_end_tick",
        "unpaired_nearest_cs_boundary_ticks", "training_visual_exposure_ticks", "training_end_checkpoint_sha256")}
    response = {"type": "qualification_evidence", "branch_id": diagnostic["original_branch_id"], "sim_ms": stop / 10,
        "parent_branch_id": diagnostic["parent_branch_id"], "parent_state_anchor_sha256": diagnostic["parent_state_anchor_sha256"],
        **shared, **diagnostic["physical_key"], "evidence_version": "mbon11-response/v1",
        "candidate_identity": diagnostic["candidate_identity"], "population": "mbon11", "population_size": 1,
        "cs_onset_tick": onset, "bins": bins, "rate_hz": _response_rate(sum(item["spikes"] for item in bins), stop - window_start, 1),
        "one_spike_rate_hz": _response_rate(1, stop - window_start, 1),
        "retention_source_checkpoint_sha256": diagnostic["source_occurrence"]["checkpoint_sha256"],
        "passive_decay_ticks": training["retention_reference_tick"] + diagnostic["physical_key"]["retention_ms"] * 10 - training["training_end_tick"],
        "input_sha256": diagnostic["input_sha256"], "black_sha256": diagnostic["black_sha256"],
        "endogenous_dan_spikes": sum(item["group_spikes"]["ppl101"] for item in raw),
        "learning": False, "external_stimulation": None,
        "intervention_id": diagnostic["source_occurrence"]["origin_branch_id"] if diagnostic["physical_key"]["condition"] == "sham" else None,
        "response_replay_resolution_hz": 1.0 if mutation == "resolution" else 0.0, "replay_id": diagnostic["replay_id"]}
    if mutation == "replay_bool": response["response_replay_resolution_hz"] = False
    elif mutation == "dan": response["endogenous_dan_spikes"] += 1
    elif mutation == "one_spike": response["one_spike_rate_hz"] += 1.0
    elif mutation == "one_spike_missing": del response["one_spike_rate_hz"]
    elif mutation == "source_sha": response["retention_source_checkpoint_sha256"] = "a" * 64
    elif mutation == "training_id": response["training_id"] = "wrong/training"
    elif mutation == "training_sha": response["training_end_checkpoint_sha256"] = "b" * 64
    elif mutation == "training_clock": response["training_start_tick"] += 1
    elif mutation == "association_clock":
        response["association_t0_tick"] -= 1
        response["last_visual_end_tick"] -= 1
    elif mutation == "dan_clock": response["last_external_dan_end_tick"] += 1
    elif mutation == "exposure": response["training_visual_exposure_ticks"]["A"] += 1000
    elif mutation == "intervention_id": response["intervention_id"] = "wrong/intervention"
    window_calls = [item["sequence"] for item in events if item["type"] == "observe"
                    and item["branch_id"] in (diagnostic["original_branch_id"], diagnostic["replay_id"])
                    and item["end_tick"] == stop]
    insertion = (min(window_calls) if mutation == "early" else max(window_calls)) + 1
    events[insertion:insertion] = [response, deepcopy(response)] if mutation == "duplicate" else [response]
    positions = {item["sequence"]: index for index, item in enumerate(events) if "sequence" in item}
    for references in events[-1]["operations"].values():
        for reference in references:
            reference["sequence"] = positions[reference["sequence"]]
    prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    return prefix, diagnostic, arguments, response


@pytest.mark.parametrize("selected_replay_pair", [{"post": True, "retention": 10000}], indirect=True)
@pytest.mark.parametrize("mutation", ["valid", "duplicate", "resolution", "early", "replay_bool", "dan", "one_spike",
    "one_spike_missing", "source_sha", "training_id", "training_sha", "training_clock", "association_clock", "dan_clock", "exposure"])
def test_selected_replay_binds_actual_post_logical_window_cells(selected_replay_pair, mutation):
    import fly_connectome_sim.experiment.analysis as analysis
    prefix, diagnostic, arguments, _ = _recorded_selected_replay_logical_pair(selected_replay_pair, mutation)
    if mutation == "valid":
        assert analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)["response_replay_resolution_hz"] == 0.0
    else:
        with pytest.raises(AnalysisError):
            analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)


@pytest.mark.parametrize("selected_replay_pair", [
    {"post": True, "retention": 10000, "condition": "sham"},
    {"post": True, "retention": 10000, "condition": "sham", "wrong_source": True},
    {"post": True, "retention": 10000, "condition": "sham", "wrong_parent_occurrence": True},
    {"post": True, "retention": 10000, "wrong_source": True},
], indirect=True)
def test_selected_replay_fix1_actual_intervention_and_exact_occurrence(selected_replay_pair, request):
    import fly_connectome_sim.experiment.analysis as analysis
    prefix, diagnostic, arguments, _ = _recorded_selected_replay_logical_pair(selected_replay_pair)
    options = request.node.callspec.params["selected_replay_pair"]
    if options.get("wrong_source") or options.get("wrong_parent_occurrence"):
        with pytest.raises(AnalysisError):
            analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)
    else:
        assert analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)["candidate_memory_w_resolution"] == 0.0


@pytest.mark.parametrize("selected_replay_pair", [{"post": True, "retention": 10000, "condition": "sham"}], indirect=True)
@pytest.mark.parametrize("mutation", ["clock", "intervention_id"])
def test_selected_replay_fix1_intervention_clock_and_present_link(selected_replay_pair, mutation):
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, prefix, diagnostic, arguments = selected_replay_pair
    if mutation == "intervention_id":
        prefix, diagnostic, arguments, _ = _recorded_selected_replay_logical_pair(selected_replay_pair, mutation)
    else:
        events = list(prefix.iter_events())
        intervention = next(item for item in events if item["type"] == "assay_intervention")
        intervention["donor_training_end_tick"] += 1
        intervention["recipient_training_end_tick"] += 1
        prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    with pytest.raises(AnalysisError):
        analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)


@pytest.mark.parametrize("selected_replay_pair", [{"post": True, "retention": 10000, "window_start": 100.0,
    "window_end": 300.0, "ppl_tonic": True}], indirect=True)
def test_selected_replay_fix1_nonzero_pre_window_dan_and_third_window(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    prefix, diagnostic, arguments, response = _recorded_selected_replay_logical_pair(selected_replay_pair)
    assert len(response["bins"]) == 20
    start = diagnostic["cs_onset_tick"] + 1000
    assert response["bins"][0]["start_tick"] == start
    assert response["bins"][-1]["end_tick"] == start + 2000
    raw = [part for item in prefix.iter_events() if item["type"] == "observe" and item["branch_id"] == diagnostic["original_branch_id"]
           for part in item["telemetry"]["bins"]]
    window_dan = sum(part["group_spikes"]["ppl101"] for part in raw if start < round(part["end_ms"] * 10) <= start + 2000)
    assert response["endogenous_dan_spikes"] > window_dan > 0
    assert analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)["response_replay_resolution_hz"] == 0.0


@pytest.mark.parametrize("name", ["type", "sim_ms", "operation_version", "learning", "telemetry"])
def test_selected_replay_operation_comparison_keeps_all_scientific_fields(name):
    import fly_connectome_sim.experiment.analysis as analysis
    first = {"type": "observe", "sim_ms": 1.0, "operation_version": "v1", "learning": False,
             "telemetry": {"other_population": [1], "compute_seconds": 1.0}}
    second = deepcopy(first)
    second[name] = {"changed": True} if name == "telemetry" else "changed"
    with pytest.raises(AnalysisError):
        analysis._compare_replay_operations(first, second)
    second = {**deepcopy(first), "sequence": 99, "scientific_sha256": "a" * 64,
        "previous_scientific_sha256": "b" * 64, "run_metadata_sha256": "c" * 64, "branch_id": "different",
        "parent_branch_id": "different", "parent_checkpoint_name": "different.npz", "parent_checkpoint_sequence": 88,
        "parent_checkpoint_sha256": "d" * 64, "parent_state_anchor_sha256": "e" * 64}
    second["telemetry"]["compute_seconds"] = 999
    analysis._compare_replay_operations(first, second)


@pytest.mark.parametrize("selected_replay_pair", [{"cs": 300.0, "window_end": 300.0}], indirect=True)
def test_selected_replay_missing_both_tail_calls_cannot_hide_behind_final_hashes(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    removed = {item["sequence"] for item in events if item["type"] == "observe" and item["end_tick"] == diagnostic["sim_tick"]}
    assert len(removed) == 2
    events = [item for item in events if item["sequence"] not in removed]
    positions = {item["sequence"]: index for index, item in enumerate(events)}
    for side in ("original", "repeat"):
        references = events[-1]["operations"][side]
        references[:] = [reference for reference in references if reference["sequence"] not in removed]
        for reference in references:
            reference["sequence"] = positions[reference["sequence"]]
    prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    with pytest.raises(AnalysisError):
        analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)


@pytest.mark.parametrize("mutation", ["telemetry", "non_mbon", "input", "learning", "current", "version", "clock", "tail", "wrong_ref"])
def test_selected_replay_rehashed_operation_or_reference_tampering_fails(selected_replay_pair, mutation):
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, prefix, _, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    observed = [item for item in events if item["type"] == "observe" and not item["branch_id"].endswith("/repeat")]
    item = observed[-1] if mutation == "tail" else observed[0]
    if mutation in ("telemetry", "tail"):
        item["telemetry"]["memory"]["unexpected"] = 1
    elif mutation == "non_mbon": item["telemetry"]["rates_hz"]["mbon07"] += 1
    elif mutation == "input": item["telemetry"]["input_sha256"] = arguments["metadata"]["rgb_input_sha256"]["stimuli"]["11"]["B"]
    elif mutation == "learning": item["learning"] = True
    elif mutation == "current": item["current_mv"] = 10.0
    elif mutation == "version": item["operation_version"] = "unknown/v1"
    elif mutation == "clock": item["duration_ms"] += 0.1
    else: events[-1]["operations"]["original"][0]["scientific_sha256"] = "0" * 64
    prefix, diagnostic = _rewrite_selected_replay(recorder, events, repair_references=mutation != "wrong_ref")
    with pytest.raises(AnalysisError):
        analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)


def test_selected_replay_timing_only_change_preserves_whole_scientific_comparison(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, prefix, _, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    observed = next(item for item in events if item["type"] == "observe")
    observed["telemetry"]["compute_seconds"] += 999
    observed["telemetry"]["memory"]["kernel_seconds"] = 321
    prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    assert analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments) == {
        "response_replay_resolution_hz": 0.0, "candidate_memory_w_resolution": 0.0,
    }


@pytest.mark.parametrize("kind", ["observe", "replay_thaw", "unknown", "after_original", "after_repeat", "extra_diagnostic"])
def test_selected_replay_rejects_every_unreferenced_or_subsequent_target_event(selected_replay_pair, kind):
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, prefix, diagnostic, arguments = selected_replay_pair
    if kind.startswith("after"):
        branch = diagnostic["original_branch_id"] if kind == "after_original" else diagnostic["replay_id"]
        recorder.append({"type": "unknown_mutation", "branch_id": branch, "sim_ms": 400.0})
        prefix = recorder.validate_prefix()
    elif kind == "extra_diagnostic":
        from fly_connectome_sim.experiment.recorder import OWNED
        recorder.append({name: value for name, value in diagnostic.items() if name not in OWNED})
        prefix = recorder.validate_prefix()
    else:
        events = list(prefix.iter_events())
        extra = {"type": "unknown_mutation", "branch_id": diagnostic["original_branch_id"], "sim_ms": 400.0}
        if kind == "observe":
            extra = deepcopy(next(item for item in reversed(events) if item["type"] == "observe"))
        elif kind == "replay_thaw":
            extra.update(type="replay_thaw", sim_tick=4000, operation_version="black-retention-operation/v1",
                         before_weights_frozen=True, after_weights_frozen=False)
        events.insert(-1, extra)
        prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    with pytest.raises(AnalysisError):
        analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)


@pytest.mark.parametrize("mutation", ["metadata", "window", "cs", "retention", "source", "state", "frozen", "map", "model_bounds", "response_resolution", "w_resolution"])
def test_selected_replay_rejects_unbound_declarations_and_still_drains(selected_replay_pair, mutation):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    arguments = deepcopy(arguments)
    if mutation == "metadata": arguments["metadata"]["mbon11_population_size"] = 2
    elif mutation == "window": arguments["execution"]["response_window"] = {"start_ms": 100.0, "end_ms": 300.0}
    elif mutation == "cs": arguments["execution"]["selected_configuration"]["cs_duration_ms"] = 300.0
    elif mutation == "retention": arguments["execution"]["retention_times_ms"] = [10000, 60000]
    elif mutation == "source": arguments["expected_source_occurrence"]["checkpoint_sequence"] = 1
    elif mutation == "state": arguments["expected_start"]["complete_state_sha256"] = arguments["expected_source_occurrence"]["checkpoint_sha256"]
    elif mutation == "frozen": arguments["expected_start"]["weights_frozen"] = True
    elif mutation == "map": arguments["expected_maps"]["target_indices"] = [3]
    elif mutation == "model_bounds": arguments["lower"] -= 1.0
    elif mutation == "response_resolution": diagnostic = {**diagnostic, "response_replay_resolution_hz": 10.0}
    else: diagnostic = {**diagnostic, "candidate_memory_w_resolution": 0.5}
    visited = []
    def actual_stream():
        for item in prefix.iter_events():
            visited.append(item["sequence"])
            yield item
    with pytest.raises(AnalysisError):
        analysis._compare_selected_replay(actual_stream(), diagnostic, **arguments)
    assert visited == list(range(prefix.manifest["event_count"]))


def test_selected_replay_does_not_hide_late_file_mutation_after_semantic_error(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    from fly_connectome_sim.experiment.recorder import RunArtifactError
    recorder, prefix, diagnostic, arguments = selected_replay_pair
    path = recorder.path / "events.jsonl"
    original = path.read_bytes()
    diagnostic = {**diagnostic, "candidate_memory_w_resolution": 0.5}
    def changing():
        for item in prefix.iter_events():
            yield item
            if item["sequence"] == 0:
                path.write_bytes(original[:-1])
    try:
        with pytest.raises(RunArtifactError):
            analysis._compare_selected_replay(changing(), diagnostic, **arguments)
    finally:
        path.write_bytes(original)


def test_selected_replay_retains_no_unrelated_history(selected_replay_pair):
    import weakref
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, _, diagnostic, arguments = selected_replay_pair
    for _ in range(40):
        recorder.append({"type": "unrelated", "branch_id": "qualification/baseline", "sim_ms": 0.0,
                         "payload": list(range(100))})
    prefix = recorder.validate_prefix()
    live, visited = [], []
    class Tracked(dict):
        pass
    def bounded():
        for item in prefix.iter_events():
            live[:] = [reference for reference in live if reference() is not None]
            assert len(live) <= 2, "Unrelated history retained by pair comparison"
            if item["type"] == "unrelated":
                item = Tracked(item)
                live.append(weakref.ref(item))
                visited.append(item["sequence"])
            yield item
    analysis._compare_selected_replay(bounded(), diagnostic, **arguments)
    assert len(visited) == 40


def _bounded_selected_checker(diagnostic, arguments, *, prior_events=()):
    import fly_connectome_sim.experiment.analysis as analysis
    return analysis._SelectedReplayChecker(diagnostic["physical_key"],
        expected_anchor_sha256=diagnostic.get("parent_state_anchor_sha256"),
        prior_events=prior_events, **arguments)


def _bounded_selected_prior(events, diagnostic, arguments):
    source = arguments["expected_source_occurrence"]
    key = diagnostic["physical_key"]
    base = f"selected/{key['seed']}/{key['paired_identity']}/{key['presentation_order']}/"
    recipient = "matched_reference" if key.get("condition") == "sufficiency" else (
        "paired" if key.get("condition") in INTERVENTIONS else key.get("condition"))
    training_id = base + str(recipient) + "/training"
    return tuple(event for event in events if event["sequence"] == source["checkpoint_sequence"]
        or (key["phase"] == "post" and (
            event["type"] in ("checkpoint", "qualification_training") and event["branch_id"] == training_id
            or event["type"] == "assay_intervention" and event.get("intervention_id") == source["origin_branch_id"]
            or event["type"] == "state_anchor" and event.get("state_anchor_sha256") == diagnostic["parent_state_anchor_sha256"])))


@pytest.mark.parametrize("selected_replay_pair", [{}, {"frozen": True}, {"window_end": 300.0},
    {"cs": 300.0, "window_start": 100.0, "window_end": 300.0},
    {"post": True, "retention": 10000}, {"post": True, "condition": "sham"}], indirect=True)
def test_selected_replay_bounded_checker_seeded_streamed_equivalence(selected_replay_pair, monkeypatch):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    prior = _bounded_selected_prior(events, diagnostic, arguments)
    assert len(prior) == (1 if diagnostic["physical_key"]["phase"] == "pre" else
                          5 if diagnostic["physical_key"]["condition"] == "sham" else 3)
    decoder = analysis._decode_candidate_w_pair
    decoded = []
    def spy(*args, **kwargs):
        decoded.append(True)
        return decoder(*args, **kwargs)
    monkeypatch.setattr(analysis, "_decode_candidate_w_pair", spy)
    for seeded in ((), prior):
        checker = _bounded_selected_checker(diagnostic, arguments, prior_events=seeded)
        for event in events[:-1]:
            if not any(event is item for item in seeded):
                checker.consume(event)
        assert len(decoded) == (0 if not seeded else 1)
        result = checker.finish(diagnostic)
        assert checker._events == [] and checker._arguments is None
        assert result == {"response_replay_resolution_hz": 0.0, "candidate_memory_w_resolution": 0.0}
        with pytest.raises(AnalysisError):
            checker.finish(diagnostic)
    assert analysis._compare_selected_replay(iter(events), diagnostic, **arguments) == result


@pytest.mark.parametrize("ending", ["actual", "missing", "late_error"])
def test_selected_replay_adapter_defers_decode_until_actual_diagnostic(selected_replay_pair, monkeypatch, ending):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    decoder = analysis._decode_candidate_w_pair
    decoded, encountered = [], []
    def spy(*args, **kwargs):
        assert encountered, "Projection decoded before actual diagnostic"
        decoded.append(True)
        return decoder(*args, **kwargs)
    monkeypatch.setattr(analysis, "_decode_candidate_w_pair", spy)
    class LateFailure(RuntimeError):
        pass
    def stream():
        for event in prefix.iter_events():
            if event["type"] == "qualification_replay":
                if ending != "actual":
                    continue
                encountered.append(True)
            yield event
        if ending == "late_error":
            raise LateFailure("actual iterator final binding failure")
    if ending == "actual":
        assert analysis._compare_selected_replay(stream(), diagnostic, **arguments)["candidate_memory_w_resolution"] == 0.0
        assert decoded == [True]
    else:
        with pytest.raises(LateFailure if ending == "late_error" else AnalysisError):
            analysis._compare_selected_replay(stream(), diagnostic, **arguments)
        assert decoded == []


@pytest.mark.parametrize("selected_replay_pair", [{}, {"post": True}, {"post": True, "condition": "sham"}], indirect=True)
def test_selected_replay_bounded_checker_prior_contract_and_release(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    prior = _bounded_selected_prior(events, diagnostic, arguments)
    mutations = [list(prior), prior * 6, (prior[0], prior[0]),
        ({**prior[0], "sequence": True},), ({**prior[0], "sequence": -1},),
        ({**prior[0], "sequence": 1.5},), ({"type": "unrelated", "sequence": 999999},)]
    if len(prior) > 1:
        mutations.extend([prior[::-1], (prior[1], prior[0], *prior[2:]),
                          (prior[0], {**prior[1], "sequence": prior[0]["sequence"]}, *prior[2:])])
    for malformed in mutations:
        checker = analysis._SelectedReplayChecker.__new__(analysis._SelectedReplayChecker)
        with pytest.raises(AnalysisError):
            checker.__init__(diagnostic["physical_key"], expected_anchor_sha256=diagnostic.get("parent_state_anchor_sha256"),
                             prior_events=malformed, **arguments)
        assert checker._events == [] and checker._arguments is None and checker._key is None
        assert type(checker._error) is str and len(checker._error) <= 256
    for anchor in ({"unexpected": list(range(100))}, "wrong", None if len(prior) > 1 else "a" * 64):
        checker = analysis._SelectedReplayChecker.__new__(analysis._SelectedReplayChecker)
        with pytest.raises(AnalysisError):
            checker.__init__(diagnostic["physical_key"], expected_anchor_sha256=anchor, **arguments)
        assert checker._events == [] and checker._arguments is None
        assert checker._anchor is None or type(checker._anchor) is str


@pytest.mark.parametrize("selected_replay_pair", [{}, {"post": True}, {"post": True, "condition": "sham"}], indirect=True)
def test_selected_replay_bounded_checker_limits_order_failure_and_finish(selected_replay_pair):
    _, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    prior = _bounded_selected_prior(events, diagnostic, arguments)
    activity = [event for event in events if event["branch_id"] in (diagnostic["original_branch_id"], diagnostic["replay_id"])][:-1]
    for mutation in ("unknown", "overflow", "early_finish", "late_prior", "bool_sequence", "finish_hash", "finish_before_activity"):
        checker = _bounded_selected_checker(diagnostic, arguments, prior_events=prior)
        with pytest.raises(AnalysisError):
            if mutation == "early_finish":
                checker.finish(diagnostic)
            elif mutation == "finish_hash":
                for event in activity:
                    checker.consume(event)
                checker.finish({**diagnostic, "parent_state_anchor_sha256": "a" * 64})
            elif mutation == "finish_before_activity":
                for event in activity:
                    checker.consume(event)
                checker.finish({**diagnostic, "sequence": activity[-1]["sequence"]})
            elif mutation == "late_prior":
                checker.consume(activity[0])
                checker.consume(prior[-1])
            elif mutation == "bool_sequence":
                checker.consume({**activity[0], "sequence": True})
            elif mutation == "unknown":
                checker.consume({**activity[0], "type": "unknown"})
            else:
                for index in range(13):
                    checker.consume({**activity[0], "sequence": activity[0]["sequence"] + index})
        assert checker._events == [] and checker._arguments is None and checker._key is None
        assert type(checker._error) is str and len(checker._error) <= 256
        with pytest.raises(AnalysisError):
            checker.finish(diagnostic)


@pytest.mark.parametrize("selected_replay_pair", [{}, {"post": True}, {"post": True, "condition": "sham"}], indirect=True)
def test_selected_replay_bounded_checker_rejects_compact_late_routes(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    late = [{"type": "checkpoint", "branch_id": branch, "sequence": diagnostic["sequence"] + 1}
            for branch in (diagnostic["original_branch_id"], diagnostic["replay_id"])]
    late.append({**diagnostic, "branch_id": "changed", "sequence": diagnostic["sequence"] + 1})
    for prior in _bounded_selected_prior(events, diagnostic, arguments):
        if prior["type"] in ("qualification_training", "assay_intervention", "state_anchor"):
            late.append({**prior, "branch_id": "changed", "origin_branch_id": "changed",
                         "source_occurrence": {"changed": True}, "sequence": diagnostic["sequence"] + 1})
    for event in late:
        checker = _bounded_selected_checker(diagnostic, arguments)
        for actual in events[:-1]:
            checker.consume(actual)
        checker.finish(diagnostic)
        checker.consume({"type": "unrelated", "branch_id": "other"})
        with pytest.raises(AnalysisError):
            checker.consume(event)
        assert checker._events == [] and checker._arguments is None
        with pytest.raises(AnalysisError):
            analysis._compare_selected_replay(iter([*events, event]), diagnostic, **arguments)


@pytest.mark.parametrize("selected_replay_pair", [{"post": True}, {"post": True, "condition": "sham"}], indirect=True)
def test_selected_replay_bounded_checker_selects_all_matching_anchor_hashes(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    anchor = next(event for event in events if event["type"] == "state_anchor")
    position = events.index(anchor)
    for mutation in ("earlier_bad_route", "clock", "wrong_hash"):
        selected = deepcopy(events)
        if mutation == "earlier_bad_route":
            selected.insert(position, {**deepcopy(anchor), "origin_branch_id": "changed",
                "source_occurrence": {**anchor["source_occurrence"], "origin_branch_id": "changed"},
                "sequence": anchor["sequence"] - 1})
        elif mutation == "clock":
            selected[position]["sim_tick"] += 1
        else:
            selected[position]["state_anchor_sha256"] = "a" * 64
        checker = _bounded_selected_checker(diagnostic, arguments)
        with pytest.raises(AnalysisError):
            for event in selected[:-1]:
                checker.consume(event)
            checker.finish(diagnostic)
        assert checker._events == [] and checker._arguments is None
        with pytest.raises(AnalysisError):
            analysis._compare_selected_replay(iter(selected), diagnostic, **arguments)


@pytest.mark.parametrize("selected_replay_pair", [{"post": True}, {"post": True, "condition": "sham"}], indirect=True)
def test_selected_replay_bounded_checker_preserves_logical_row_interleaving(selected_replay_pair):
    import fly_connectome_sim.experiment.analysis as analysis
    recorder = selected_replay_pair[0]
    original = (recorder.path / "events.jsonl").read_bytes()
    for mutation in ("valid", "early", "duplicate", "resolution", "dan", "one_spike", "training_clock", "source_sha"):
        (recorder.path / "events.jsonl").write_bytes(original)
        prefix, diagnostic, arguments, _ = _recorded_selected_replay_logical_pair(selected_replay_pair, mutation)
        checker = _bounded_selected_checker(diagnostic, arguments)
        def compare():
            for event in list(prefix.iter_events())[:-1]:
                checker.consume(event)
            return checker.finish(diagnostic)
        if mutation == "valid":
            assert compare() == analysis._compare_selected_replay(prefix.iter_events(), diagnostic, **arguments)
        else:
            with pytest.raises(AnalysisError):
                compare()
            assert checker._events == [] and checker._arguments is None


def test_selected_replay_bounded_checker_projection_bits_and_existing_kernel_guards(selected_replay_pair, monkeypatch):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    original = list(prefix.iter_events())
    for mutation in ("signed_zero_equal", "signed_zero_different", "telemetry", "non_mbon", "input", "clock", "tail",
                     "state", "reference_hash", "reference_side", "reference_index", "missing_tail", "map", "bounds"):
        events = deepcopy(original)
        actual = events[-1]
        args = deepcopy(arguments)
        observations = [item for item in events if item["type"] == "observe"]
        if mutation.startswith("signed_zero"):
            zero = np.zeros(actual["candidate_projection"]["shape"][0], dtype="<f8")
            zero[0] = -0.0
            actual["candidate_projection"]["original_hex"] = zero.tobytes().hex()
            if mutation == "signed_zero_different":
                zero[0] = 0.0
            actual["candidate_projection"]["repeat_hex"] = zero.tobytes().hex()
        elif mutation in ("telemetry", "tail"):
            observations[-1 if mutation == "tail" else 0]["telemetry"]["memory"]["unexpected"] = 1
        elif mutation == "non_mbon": observations[0]["telemetry"]["rates_hz"]["mbon07"] += 1
        elif mutation == "input": observations[0]["telemetry"]["input_sha256"] = "a" * 64
        elif mutation == "clock": observations[0]["duration_ms"] += 0.1
        elif mutation == "state": actual["boundaries"]["start"]["repeat"]["complete_state_sha256"] = "a" * 64
        elif mutation == "reference_hash": actual["operations"]["original"][0]["scientific_sha256"] = "a" * 64
        elif mutation == "reference_side": actual["operations"]["original"], actual["operations"]["repeat"] = actual["operations"]["repeat"], actual["operations"]["original"]
        elif mutation == "reference_index": actual["operations"]["original"].reverse()
        elif mutation == "missing_tail": events.remove(observations[-1])
        elif mutation == "map": args["expected_maps"]["target_indices"] = [3]
        else: args["lower"] -= 1
        checker = _bounded_selected_checker(actual, args)
        for event in events[:-1]:
            checker.consume(event)
        if mutation == "signed_zero_equal":
            decoder = analysis._decode_candidate_w_pair
            decoded = []
            def spy(*args, **kwargs):
                values = decoder(*args, **kwargs)
                decoded.append(tuple(value.tobytes() for value in values))
                return values
            with monkeypatch.context() as patch:
                patch.setattr(analysis, "_decode_candidate_w_pair", spy)
                assert checker.finish(actual)["candidate_memory_w_resolution"] == 0.0
            assert decoded == [(bytes.fromhex(actual["candidate_projection"]["original_hex"]),) * 2]
        else:
            with pytest.raises(AnalysisError):
                checker.finish(actual)
        assert checker._events == [] and checker._arguments is None


@pytest.mark.parametrize("failure", ["constructor", "consume", "finish"])
def test_selected_replay_bounded_checker_semantic_failure_never_hides_late_eof(selected_replay_pair, failure):
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    if failure == "constructor": diagnostic = {**diagnostic, "physical_key": {}}
    elif failure == "finish": diagnostic = {**diagnostic, "candidate_memory_w_resolution": 0.5}
    visited = []
    class LateFailure(RuntimeError):
        pass
    def stream():
        for event in prefix.iter_events():
            if failure == "consume" and event["type"] == "branch_start":
                event = {**event, "type": "unknown"}
            visited.append(event["sequence"])
            yield event
        raise LateFailure("actual EOF binding failed")
    with pytest.raises(LateFailure):
        analysis._compare_selected_replay(stream(), diagnostic, **arguments)
    assert visited == list(range(prefix.manifest["event_count"]))


@pytest.mark.parametrize("selected_replay_pair", [{"post": True, "retention": 10000}], indirect=True)
@pytest.mark.parametrize("position", ["before", "after"])
@pytest.mark.parametrize("consumer", ["kernel", "checker", "adapter"])
def test_selected_replay_ordinary_post_source_intervention_alias(selected_replay_pair, position, consumer):
    """An actual recorded alias must reach the same rejection as the unfiltered kernel."""
    import fly_connectome_sim.experiment.analysis as analysis
    _, prefix, diagnostic, arguments = selected_replay_pair
    recorder = selected_replay_pair[0]
    baseline = next(event for event in prefix.iter_events() if event["type"] == "qualification_checkpoint")
    recorder.append({"type": "assay_intervention", "branch_id": "qualification/changed-alias", "sim_ms": 0.0,
        "origin_branch_id": "changed-origin", "intervention_id": arguments["expected_source_occurrence"]["origin_branch_id"],
        "parent_branch_id": baseline["branch_id"], "parent_checkpoint_name": baseline["checkpoint_name"],
        "parent_checkpoint_sequence": baseline["sequence"], "parent_checkpoint_sha256": baseline["checkpoint_sha256"]})
    prefix = recorder.validate_prefix()
    if position == "before":
        events = list(prefix.iter_events())
        alias = events.pop()
        insertion = next(index for index, event in enumerate(events) if event["branch_id"] == diagnostic["original_branch_id"])
        events.insert(insertion, alias)
        positions = {event["sequence"]: index for index, event in enumerate(events)}
        for references in events[-1]["operations"].values():
            for reference in references:
                reference["sequence"] = positions[reference["sequence"]]
        prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    else:
        diagnostic = next(event for event in prefix.iter_events() if event["type"] == "qualification_replay")
    assert diagnostic["physical_key"]["condition"] == "paired"
    if consumer == "checker":
        checker = _bounded_selected_checker(diagnostic, arguments)
        with pytest.raises(AnalysisError):
            for event in prefix.iter_events():
                if event["type"] == "qualification_replay":
                    checker.finish(event)
                else:
                    checker.consume(event)
        assert checker._events == [] and checker._arguments is None
    else:
        compare = analysis._compare_selected_replay_records if consumer == "kernel" else analysis._compare_selected_replay
        with pytest.raises(AnalysisError):
            compare(prefix.iter_events(), diagnostic, **arguments)


def test_selected_replay_bounded_checker_pre_sixteen_actual_window_rows(selected_replay_pair):
    """Reuse declared route rows with actual native PRE measurements; these are no proof."""
    import fly_connectome_sim.experiment.analysis as analysis
    recorder, prefix, diagnostic, arguments = selected_replay_pair
    events = list(prefix.iter_events())
    stop = diagnostic["boundaries"]["window"]["original"]["sim_tick"]
    calls = [event for event in events if event["type"] == "observe"
             and event["branch_id"] == diagnostic["original_branch_id"] and event["end_tick"] <= stop]
    bins = [{"start_tick": round(part["end_ms"] * 10) - round(part["duration_ms"] * 10),
             "end_tick": round(part["end_ms"] * 10), "spikes": part["group_spikes"]["mbon11"]}
            for event in calls for part in event["telemetry"]["bins"]
            if diagnostic["cs_onset_tick"] < round(part["end_ms"] * 10) <= stop]
    rows = [row for row in _responses("qualification") if row["type"] == "qualification_evidence"
            and all(row[name] == diagnostic["physical_key"][name] for name in diagnostic["physical_key"])]
    assert len(rows) == 16
    parent = {name: diagnostic[name] for name in ("parent_branch_id", "parent_checkpoint_name",
              "parent_checkpoint_sequence", "parent_checkpoint_sha256")}
    for row in rows:
        row.update(**parent, branch_id=diagnostic["original_branch_id"], sim_ms=stop / 10,
            population_size=diagnostic["population_size"], cs_onset_tick=diagnostic["cs_onset_tick"], bins=deepcopy(bins),
            rate_hz=analysis._response_rate(sum(part["spikes"] for part in bins), stop - diagnostic["cs_onset_tick"], 1),
            one_spike_rate_hz=analysis._response_rate(1, stop - diagnostic["cs_onset_tick"], 1),
            endogenous_dan_spikes=sum(part["group_spikes"]["ppl101"] for event in calls for part in event["telemetry"]["bins"]),
            response_replay_resolution_hz=diagnostic["response_replay_resolution_hz"], replay_id=diagnostic["replay_id"])
    insertion = max(event["sequence"] for event in events if event["type"] == "observe" and event["end_tick"] == stop) + 1
    events[insertion:insertion] = rows
    positions = {event["sequence"]: index for index, event in enumerate(events) if "sequence" in event}
    for references in events[-1]["operations"].values():
        for reference in references:
            reference["sequence"] = positions[reference["sequence"]]
    prefix, diagnostic = _rewrite_selected_replay(recorder, events)
    events = list(prefix.iter_events())
    for mutation in ("valid", "duplicate", "overflow", "early"):
        checker = _bounded_selected_checker(diagnostic, arguments)
        selected = deepcopy(events)
        actual = selected[-1]
        logical = [event for event in selected if event["type"] == "qualification_evidence"]
        if mutation == "duplicate":
            logical[-1].update(condition=logical[0]["condition"], retention_ms=logical[0]["retention_ms"])
        elif mutation == "early":
            selected.remove(logical[0])
            selected.insert(3, logical[0])
        def compare():
            for event in selected[:-1]:
                checker.consume(event)
            if mutation == "overflow":
                checker.consume({**logical[-1], "sequence": actual["sequence"]})
            return checker.finish(actual)
        if mutation == "valid":
            assert compare() == analysis._compare_selected_replay(iter(selected), actual, **arguments)
            assert checker._row_count == 16
        else:
            with pytest.raises(AnalysisError):
                compare()
        assert checker._events == [] and checker._arguments is None


def test_candidate_w_pair_nonzero_float64_math_and_signed_zero():
    import fly_connectome_sim.experiment.analysis as analysis
    from fly_connectome_sim.experiment.qualification import _state_difference, _response_rate
    maps = {"target_indices": [2], "candidate_positions": [0, 1], "candidate_edge_indices": [3, 1]}
    first, second = np.array([-0.0, 1.0], dtype="<f8"), np.array([0.5, 0.5], dtype="<f8")
    projection = analysis._encode_candidate_w_pair(first, second, maps=maps)
    assert projection["original_hex"] == "0000000000000080000000000000f03f"
    a, b = analysis._decode_candidate_w_pair(projection, expected_maps=maps, n=4, memory_count=2, edge_count=4, lower=-1.0, upper=2.0)
    assert a.dtype.str == b.dtype.str == "<f8" and a.tobytes() == first.tobytes()
    assert _state_difference(a, b) == 0.5
    assert _response_rate(abs(4 - 1), 1000, 3) == 9.999999999999998
    adjacent = np.nextafter(np.array([1.0], dtype="<f8"), np.array([2.0], dtype="<f8"))
    assert _state_difference(adjacent, np.array([1.0], dtype="<f8")) == 2.220446049250313e-16
    first[0] = 1.0
    maps["target_indices"][0] = 0
    assert projection["maps"]["target_indices"] == [2] and projection["original_hex"].startswith("0000000000000080")


@pytest.mark.parametrize("mutation", ["dtype", "rank", "shape", "nan", "infinite", "empty"])
def test_candidate_w_pair_encoder_rejects_lossy_or_invalid_arrays(mutation):
    import fly_connectome_sim.experiment.analysis as analysis
    maps = {"target_indices": [2], "candidate_positions": [0], "candidate_edge_indices": [0]}
    first, second = np.zeros(1, dtype="<f8"), np.zeros(1, dtype="<f8")
    if mutation == "dtype": first = first.astype(np.float32)
    elif mutation == "rank": first = first.reshape(1, 1)
    elif mutation == "shape": second = np.zeros(2, dtype="<f8")
    elif mutation == "nan": first[0] = np.nan
    elif mutation == "infinite": first[0] = np.inf
    else: first = second = np.zeros(0, dtype="<f8")
    with pytest.raises(ValueError):
        analysis._encode_candidate_w_pair(first, second, maps=maps)


@pytest.mark.parametrize("mutation", ["target", "order", "duplicate", "dtype", "hex", "length", "boolean", "index_bound", "layout_bool"])
def test_candidate_w_pair_rejects_maps_before_numeric_decode(monkeypatch, mutation):
    import fly_connectome_sim.experiment.analysis as analysis
    maps = {"target_indices": [2], "candidate_positions": [0, 1], "candidate_edge_indices": [3, 1]}
    projection = analysis._encode_candidate_w_pair(np.zeros(2, dtype="<f8"), np.zeros(2, dtype="<f8"), maps=maps)
    arguments = {"expected_maps": maps, "n": 4, "memory_count": 2, "edge_count": 4, "lower": -1.0, "upper": 2.0}
    if mutation == "target": projection["maps"]["target_indices"] = [1]
    elif mutation == "order": projection["maps"]["candidate_edge_indices"].reverse()
    elif mutation == "duplicate": projection["maps"]["candidate_positions"] = [0, 0]
    elif mutation == "dtype": projection["dtype"] = ">f8"
    elif mutation == "hex": projection["original_hex"] = "g" * 32
    elif mutation == "length": projection["shape"] = [1]
    elif mutation == "boolean": projection["maps"]["target_indices"] = [True]
    elif mutation == "index_bound": arguments["edge_count"] = 3
    else: arguments["n"] = True
    def forbidden(*args, **kwargs):
        pytest.fail("Numeric decode preceded expected-map/layout binding")
    monkeypatch.setattr(np, "frombuffer", forbidden)
    with pytest.raises(ValueError):
        analysis._decode_candidate_w_pair(projection, **arguments)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.01, 2.01])
def test_candidate_w_pair_decoder_checks_finiteness_and_model_bounds(value):
    import fly_connectome_sim.experiment.analysis as analysis
    maps = {"target_indices": [2], "candidate_positions": [0], "candidate_edge_indices": [0]}
    projection = analysis._encode_candidate_w_pair(np.zeros(1, dtype="<f8"), np.zeros(1, dtype="<f8"), maps=maps)
    projection["original_hex"] = np.array([value], dtype="<f8").tobytes().hex()
    with pytest.raises(ValueError):
        analysis._decode_candidate_w_pair(projection, expected_maps=maps, n=4, memory_count=1, edge_count=1, lower=-1.0, upper=2.0)


def _count_response_fixture(population, window, *, pre_c=2, post_c=2, family="confirmation"):
    """Declared arithmetic fixture with explicit raw integer counts, never native proof."""
    from fly_connectome_sim.experiment.qualification import ResponseWindow, _one_spike_rate, _response_rate
    data = build_frozen_config(_qualification()).to_dict()
    identity = data["engine_identity"]
    identity["neural_groups"]["mbon11"] = list(range(population))
    identity.pop("sha256")
    identity["sha256"] = sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    data.update(mbon11_population_size=population, response_window=window,
                one_spike_floor_hz=_one_spike_rate(population, ResponseWindow(**window)))
    data.pop("digest")
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    frozen = FrozenAssayConfig.from_dict(data)
    events = _responses(family)
    start, stop = round(window["start_ms"] * 10), round(window["end_ms"] * 10)
    for event in events:
        if event["type"] != ("qualification_evidence" if family == "qualification" else "assay_response"):
            continue
        count = ((pre_c if event["phase"] == "pre" else post_c) if event["stimulus"] == "C"
                 else event["bins"][0]["spikes"])
        event["bins"] = [{"start_tick": event["cs_onset_tick"] + start,
                          "end_tick": event["cs_onset_tick"] + stop, "spikes": count}]
        event.update(population_size=population, rate_hz=_response_rate(count, stop - start, population),
                     one_spike_rate_hz=_response_rate(1, stop - start, population),
                     sim_ms=(event["cs_onset_tick"] + stop) / 10)
    return frozen, events


def _arithmetic_declarations(family):
    """Plain arithmetic inputs; no artifact hashes, frozen config or proof."""
    result = {"engine_identity": _engine_identity(), "mbon11_population_size": 10,
              "candidate_identity": "kc-mbon11-ppl101/v1", "selected_configuration": dict(CONFIGURATION),
              "response_window": dict(WINDOW), "retention_times_ms": [10000, 70000]}
    if family == "confirmation":
        result["confirmation_input_sha256"] = deepcopy(_input_hashes("confirmation"))
    return result


@pytest.mark.parametrize("family,event_type", [("qualification", "qualification_evidence"), ("confirmation", "assay_response")])
def test_declared_reduction_matches_frozen_wrapper(family, event_type):
    import fly_connectome_sim.experiment.analysis as analysis
    frozen = build_frozen_config(_qualification())
    events = _responses(family)
    declarations = _arithmetic_declarations(family)
    before_events, before_declarations = deepcopy(events), deepcopy(declarations)
    frozen_json = frozen.to_json()
    expected = reduce_assay_evidence(iter(events), frozen, event_type=event_type, attested_state_anchors=(H["before"],))
    actual = analysis._reduce_declared_evidence(iter(events), declarations, event_type=event_type,
                                               attested_state_anchors=(H["before"],))
    assert asdict(actual) == asdict(expected)
    assert actual.status == "supported" and not actual.reasons
    assert events == before_events and declarations == before_declarations and frozen.to_json() == frozen_json


@pytest.mark.parametrize("family,event_type", [("qualification", "qualification_evidence"), ("confirmation", "assay_response")])
def test_declared_reduction_needs_no_frozen_artifact(family, event_type, monkeypatch):
    import fly_connectome_sim.experiment.analysis as analysis
    declarations = _arithmetic_declarations(family)
    events = _responses(family)
    def forbidden(*args, **kwargs):
        pytest.fail("Arithmetic declarations constructed a Frozen object")
    monkeypatch.setattr(analysis, "_freeze", forbidden)
    reduced = analysis._reduce_declared_evidence(iter(events), declarations, event_type=event_type)
    assert reduced.status == "supported" and not reduced.reasons
    assert len(reduced.rows) == 16 and len(reduced.trainings) == 40 and len(reduced.interventions) == 24


@pytest.mark.parametrize("late_error", [False, True])
def test_declared_reduction_drains_semantic_failures_and_propagates_late_eof(late_error):
    import fly_connectome_sim.experiment.analysis as analysis
    declarations = _arithmetic_declarations("confirmation")
    events = _responses("confirmation")
    next(event for event in events if event["type"] == "assay_response")["learning"] = True
    visited = []
    def stream():
        for index, event in enumerate(events):
            visited.append(index)
            yield event
        visited.append("EOF")
        if late_error:
            raise ValueError("declared late EOF failure")
    if late_error:
        with pytest.raises(ValueError, match="declared late EOF failure"):
            analysis._reduce_declared_evidence(stream(), declarations, event_type="assay_response")
    else:
        reduced = analysis._reduce_declared_evidence(stream(), declarations, event_type="assay_response")
        assert reduced.status == "inconclusive" and any("reward_free_test" in reason for reason in reduced.reasons)
    assert visited == [*range(len(events)), "EOF"]


@pytest.mark.parametrize("mutation", ["type", "missing", "extra", "family", "seeds", "artifact", "floor", "population_bool",
    "population_zero", "identity", "candidate", "configuration", "window", "window_bool", "retention", "retention_bool",
    "input", "extra_seed", "qualification_input", "event_type", "event_type_list"])
def test_declared_reduction_rejects_contract_before_iterator(mutation):
    import fly_connectome_sim.experiment.analysis as analysis
    declarations = _arithmetic_declarations("confirmation")
    event_type = "assay_response"
    if mutation == "type": declarations = []
    elif mutation == "missing": del declarations["engine_identity"]
    elif mutation == "extra": declarations["unknown"] = None
    elif mutation == "family": declarations["family"] = "confirmation"
    elif mutation == "seeds": declarations["seeds"] = [101, 113]
    elif mutation == "artifact": declarations["qualification_artifact"] = {"events_sha256": H["events"]}
    elif mutation == "floor": declarations["effect_floor_hz"] = 0.0
    elif mutation == "population_bool": declarations["mbon11_population_size"] = True
    elif mutation == "population_zero": declarations["mbon11_population_size"] = 0
    elif mutation == "identity": declarations["engine_identity"]["neural_groups"]["mbon11"].reverse()
    elif mutation == "candidate": declarations["candidate_identity"] = "unknown"
    elif mutation == "configuration": declarations["selected_configuration"]["cs_duration_ms"] = 99.0
    elif mutation == "window": declarations["response_window"]["end_ms"] = 200.0
    elif mutation == "window_bool": declarations["response_window"]["start_ms"] = False
    elif mutation == "retention": declarations["retention_times_ms"] = [10000, 60000]
    elif mutation == "retention_bool": declarations["retention_times_ms"][0] = True
    elif mutation == "input": declarations["confirmation_input_sha256"]["113"]["C"] = H["events"]
    elif mutation == "extra_seed": declarations["confirmation_input_sha256"]["11"] = declarations["confirmation_input_sha256"]["101"]
    elif mutation == "qualification_input": event_type = "qualification_evidence"
    elif mutation == "event_type": event_type = "qualification"
    else: event_type = []
    def forbidden():
        pytest.fail("Malformed declaration consumed events")
        yield
    with pytest.raises(AnalysisError):
        analysis._reduce_declared_evidence(forbidden(), declarations, event_type=event_type)


@pytest.mark.parametrize("population", [3, 13, 7])
@pytest.mark.parametrize("window", [{"start_ms": 0.0, "end_ms": 100.0},
    {"start_ms": 0.0, "end_ms": 300.0}, {"start_ms": 100.0, "end_ms": 300.0}])
@pytest.mark.parametrize("pre_c,post_c", [(pre, post) for pre in (0, 1, 2) for post in (0, 1, 2)])
def test_qualification_c_boundary_is_integer(population, window, pre_c, post_c):
    import fly_connectome_sim.experiment.analysis as analysis
    for family, event_type, seeds, strict in (("qualification", "qualification_evidence", (11, 23), False),
                                             ("confirmation", "assay_response", (101, 113), True)):
        frozen, events = _count_response_fixture(population, window, pre_c=pre_c, post_c=post_c, family=family)
        # A real arithmetic negative independent of C: this paired cell has no A change.
        pre_a = next(event for event in events if event["type"] == event_type
                     and _is_cell(event, phase="pre", stimulus="A", seed=seeds[0]))
        post_a = next(event for event in events if event["type"] == event_type
                      and _is_cell(event, phase="post", stimulus="A", seed=seeds[0]))
        post_a["bins"][0]["spikes"] = pre_a["bins"][0]["spikes"]
        post_a["rate_hz"] = pre_a["rate_hz"]
        config = frozen.to_dict()
        declarations = {name: config[name] for name in _arithmetic_declarations(family)}
        reduced = analysis._reduce_declared_evidence(events, declarations, event_type=event_type)
        assert reduced.status == "supported" and not reduced.reasons
        before = deepcopy(asdict(reduced))
        report = analysis._assess(reduced, config, seeds, strict_c=strict)
        key = f"{seeds[0]}/A/AB/10000"
        assert ("C_floor:" + key in report.reasons) is (pre_c <= int(strict) or post_c <= int(strict))
        assert report.status == "unsupported" and "paired_effect:" + key in report.reasons
        assert reduced.rows[key]["paired"]["pre_C"]["spikes"] == pre_c
        assert reduced.rows[key]["paired"]["post_C"]["spikes"] == post_c
        assert asdict(reduced) == before


@pytest.mark.parametrize("strict", [None, 0, 1, "False", np.bool_(False), np.bool_(True)])
def test_qualification_c_boundary_rejects_non_boolean_flag(strict):
    import fly_connectome_sim.experiment.analysis as analysis
    frozen, events = _count_response_fixture(13, WINDOW)
    reduced = reduce_assay_evidence(events, frozen)
    with pytest.raises(AnalysisError):
        analysis._assess(reduced, frozen.to_dict(), (101, 113), strict_c=strict)


def test_consumer_one_c_spike_is_rejected_for_upward_rounded_population_13():
    frozen, events = _count_response_fixture(13, {"start_ms": 0.0, "end_ms": 300.0}, pre_c=1, post_c=1)
    reduction = reduce_assay_evidence(events, frozen)
    assert reduction.status == "supported" and reduction.reasons == ()
    report = assess_assay_evidence(events, frozen)
    assert "C_floor:101/A/AB/10000" in report.reasons
    cell = reduction.rows["101/A/AB/10000"]["paired"]["pre_C"]
    assert cell["spikes"] == 1 and cell["rate_hz"] == 0.25641025641025644


@pytest.mark.parametrize("population,window", [
    (3, {"start_ms": 0.0, "end_ms": 100.0}),
    (13, {"start_ms": 0.0, "end_ms": 300.0}),
    (7, {"start_ms": 100.0, "end_ms": 300.0}),
])
@pytest.mark.parametrize("pre_c,post_c,failed", [
    (0, 2, True), (1, 2, True), (2, 2, False), (2, 0, True), (2, 1, True),
])
def test_consumer_retains_counts_and_confirms_strict_c_floor(population, window, pre_c, post_c, failed):
    frozen, events = _count_response_fixture(population, window, pre_c=pre_c, post_c=post_c)
    reduced = reduce_assay_evidence(events, frozen)
    assert reduced.status == "supported" and reduced.reasons == ()
    row = reduced.rows["101/A/AB/10000"]["paired"]
    assert row["pre_C"]["spikes"] == pre_c and row["post_C"]["spikes"] == post_c
    report = assess_assay_evidence(events, frozen)
    assert ("C_floor:101/A/AB/10000" in report.reasons) is failed


def test_selected_washout_reconstructs_validated_integer_difference():
    import fly_connectome_sim.experiment.analysis as analysis
    frozen, events = _count_response_fixture(3, {"start_ms": 0.0, "end_ms": 100.0})
    for condition, count in (("frozen_plasticity", 4), ("matched_reference", 3)):
        target = next(event for event in events if event["type"] == "assay_response"
                      and _is_cell(event, condition=condition))
        target["bins"][0]["spikes"] = count
        target["rate_hz"] = (13.333333333333332 if count == 4 else 9.999999999999998)
    reduced = reduce_assay_evidence(events, frozen)
    assert reduced.status == "supported" and reduced.reasons == ()
    row = reduced.rows["101/A/AB/10000"]
    assert analysis._selected_washout_hz(row, "A", 3, {"start_ms": 0.0, "end_ms": 100.0}) == 3.333333333333333
    row["frozen_plasticity"]["post_A"].pop("spikes")
    with pytest.raises(KeyError):
        analysis._selected_washout_hz(row, "A", 3, {"start_ms": 0.0, "end_ms": 100.0})


def _h(name):
    return sha256(name.encode()).hexdigest()


def _cohort(seed, identity, order):
    return f"{seed}/{identity}/{order}"


def _training_hash(seed, identity, order, condition):
    return _h(f"{_cohort(seed, identity, order)}/{condition}/training-end")


def _memory_hash(seed, identity, order, condition):
    return _h(f"{_cohort(seed, identity, order)}/{condition}/candidate")


def _baseline_hash(seed, identity, order):
    return _h(f"{_cohort(seed, identity, order)}/baseline")


def _retained_hash(seed, identity, order, condition, retention):
    return _h(f"{_cohort(seed, identity, order)}/{condition}/{retention}/retained")


def _intervention_hash(seed, identity, order, condition):
    return _h(f"{_cohort(seed, identity, order)}/{condition}/intervention")


def _checkpoint(name, digest, tick, branch, parent=None):
    event = {"type": "checkpoint", "checkpoint_name": name,
             "checkpoint_sha256": digest, "branch_id": branch,
             "sim_ms": tick / 10}
    if parent is not None:
        event["parent_branch_id"] = parent[0]
        event["parent_checkpoint_sha256"] = parent[1]
    return event


def _training(kind, seed, identity, order, condition):
    config = GridConfiguration(**CONFIGURATION)
    segments, second_end, total_end, t0 = _training_timeline(
        config, identity, order, condition, controls=True,
    )
    _, _, _, paired_t0 = _training_timeline(config, identity, order, "paired", controls=True)
    inputs = _input_hashes(kind)[str(seed)]
    rows = []
    for part in segments:
        rows.append({
            "start_tick": BASE_TICK + round(part.start_ms * 10),
            "end_tick": BASE_TICK + round(part.end_ms * 10),
            "stimulus": part.stimulus,
            "external_stimulation": part.stimulation,
            "current_mv": 20.0 if part.stimulation else None,
            "learning": (condition in {"paired", "no_external_dan", "temporally_unpaired"}
                         and part.start_ms < t0
                         and (part.stimulus is not None or part.stimulation is not None)),
            "input_sha256": inputs[part.stimulus or "black"],
        })
    pulse = [part for part in segments if part.stimulation]
    visual = [part for part in segments if part.stimulus]
    gap = (min(abs(round((a - b) * 10))
               for a in (boundary for part in pulse
                         for boundary in (part.start_ms, part.end_ms))
               for b in (boundary for part in visual
                         for boundary in (part.start_ms, part.end_ms)))
           if condition == "temporally_unpaired" else None)
    branch = f"{kind}/{_cohort(seed, identity, order)}/{condition}/training"
    return {
        "type": "qualification_training" if kind == "qualification" else "assay_training",
        "training_version": "associative-training/v1",
        "training_id": f"{kind}/{_cohort(seed, identity, order)}/{condition}",
        "branch_id": branch, "seed": seed, "paired_identity": identity,
        "presentation_order": order, "condition": condition,
        "candidate_identity": "kc-mbon11-ppl101/v1",
        "baseline_tick": BASE_TICK,
        "baseline_checkpoint_sha256": _baseline_hash(seed, identity, order),
        "training_start_tick": min(row["start_tick"] for row in rows if row["stimulus"]),
        "association_t0_tick": BASE_TICK + round(t0 * 10),
        "retention_reference_tick": BASE_TICK + round(paired_t0 * 10),
        "training_end_tick": BASE_TICK + round(total_end * 10),
        "training_end_checkpoint_sha256": _training_hash(seed, identity, order, condition),
        "last_visual_end_tick": BASE_TICK + round(second_end * 10),
        "last_external_dan_end_tick": (BASE_TICK + round(max(part.end_ms for part in pulse) * 10)
                                       if pulse else None),
        "training_visual_exposure_ticks": {
            stimulus: sum(row["end_tick"] - row["start_tick"] for row in rows
                          if row["stimulus"] == stimulus)
            for stimulus in ("A", "B", "C")},
        "unpaired_nearest_cs_boundary_ticks": gap,
        "candidate_memory_sha256": _memory_hash(seed, identity, order, condition),
        "noncandidate_state_sha256": _h(f"{_cohort(seed, identity, order)}/noncandidate"),
        "segments": rows,
        "sim_ms": (BASE_TICK + round(total_end * 10)) / 10,
    }


@lru_cache(maxsize=2)
def _input_hashes(family):
    seeds = (11, 23) if family == "qualification" else (101, 113)
    black = _rgb_input_sha256(np.zeros((32, 32, 3), dtype=np.uint8))
    return {str(seed): {**{
        stimulus: _rgb_input_sha256(AssayStimuli(seed, family).frame(stimulus))
        for stimulus in ("A", "B", "C")}, "black": black}
        for seed in seeds}


def _engine_identity():
    fingerprint = {"version": "model-source/v1", "sources_sha256": {"engine.py": H["model"]}}
    fingerprint["sha256"] = sha256(json.dumps(fingerprint, sort_keys=True,
                                              separators=(",", ":")).encode()).hexdigest()
    provenance = {
        "model": "test-model", "model_fingerprint": fingerprint,
        "build": {"model": "test-model", "source_sha256": H["model"],
                  "compiler": "test", "flags": [], "library": "test",
                  "binary_sha256": H["model"]},
        "eta": 0.1, "parameters": {"test": 1},
        "graph_ids_sha256": H["model"], "graph_ptr_sha256": H["model"],
        "graph_post_sha256": H["model"], "plastic_edges_sha256": H["model"],
        "configuration_sha256": {"initial_weight": H["model"]},
    }
    identity = {"version": "fly-engine/v1", "model_provenance": provenance,
                "neural_groups": {"mbon11": list(range(10))}}
    identity["sha256"] = sha256(json.dumps(identity, sort_keys=True,
                                           separators=(",", ":")).encode()).hexdigest()
    return identity


class FixtureRun(VerifiedRun):
    """In-memory arithmetic fixture, never evidence of actual artifact verification."""

    def __init__(self, manifest, events, attested_anchors=()):
        object.__setattr__(self, "_fixture_manifest", deepcopy(manifest))
        object.__setattr__(self, "_fixture_events", deepcopy(events))
        object.__setattr__(self, "_attested_anchors", frozenset(attested_anchors))

    @property
    def manifest(self):
        return deepcopy(self._fixture_manifest)

    def iter_events(self):
        yield from deepcopy(self._fixture_events)

    @property
    def replay_attested_state_anchors(self):
        return self._attested_anchors


def _manifest(kind, events=()):
    qualification = kind == "qualification"
    own_hashes = _input_hashes(kind)
    confirmation_hashes = _input_hashes("confirmation")
    return {
        "format_version": "run-artifact/v1",
        "schema_version": "run-schema/v1",
        "schema_sha256": H["schema"],
        "run_kind": kind,
        "run_metadata_sha256": H["metadata"],
        "events_sha256": H["events"],
        "final_scientific_sha256": H["scientific"],
        "checkpoints": {event["checkpoint_name"]: {
            "sha256": event["checkpoint_sha256"],
            "sim_ms": event["sim_ms"],
            "origin_branch_id": event["branch_id"],
            "size": 1,
        } for event in events if "checkpoint_name" in event},
        "metadata": {
            "family": "qualification" if qualification else "confirmation",
            "seeds": [11, 23] if qualification else [101, 113],
            "engine_identity": _engine_identity(),
            "protocol_version": ("qualification/v1" if qualification
                                 else "associative-confirmation/v1"),
            "stimulus_version": "associative-stimuli/v1",
            "input_sha256": sorted({value for row in own_hashes.values()
                                    for value in row.values()}),
            "rgb_input_sha256": {
                "stimuli": {seed: {stimulus: row[stimulus] for stimulus in ("A", "B", "C")}
                            for seed, row in own_hashes.items()},
                "black": next(iter(own_hashes.values()))["black"],
            },
            "confirmation_input_sha256": confirmation_hashes,
            "candidate_identity": "kc-mbon11-ppl101/v1",
            "mbon11_population_size": 10,
            "qualification_version": "mbon11-qualification/v1",
            "aggregation": "raw-bin-mean-rate/v1",
            "exclusions": [],
            "configuration": {"pulse_duration_ms": 100.0,
                              "external_dan_current_mv": 20.0,
                              "unpaired_minimum_separation_ms": 10000.0},
            "factors": {"grid": [asdict(item) for item in GRID],
                        "response_windows": [asdict(item) for item in RESPONSE_WINDOWS],
                        "retention_ms": list(RETENTION_CANDIDATES_MS),
                        "paired_identity": ["A", "B"],
                        "presentation_order": ["AB", "BA"],
                        "side": "center", "color_assignment": "fixed"},
        },
    }


def _intervention(kind, seed, identity, order, condition):
    donor_condition = "matched_reference" if condition == "necessity" else "paired"
    recipient_condition = "matched_reference" if condition == "sufficiency" else "paired"
    donor = _training_hash(seed, identity, order, donor_condition)
    recipient = _training_hash(seed, identity, order, recipient_condition)
    donor_memory = _memory_hash(seed, identity, order, donor_condition)
    before_memory = _memory_hash(seed, identity, order, recipient_condition)
    end = _training(kind, seed, identity, order, recipient_condition)["training_end_tick"]
    return {
        "type": "assay_intervention",
        "intervention_version": "candidate-memory-replacement/v1",
        "intervention_id": f"{seed}-{identity}-{order}-{condition}",
        "seed": seed, "paired_identity": identity, "presentation_order": order,
        "condition": condition, "candidate_identity": "kc-mbon11-ppl101/v1",
        "donor_role": "matched_baseline" if condition == "necessity" else "trained",
        "recipient_role": "untrained" if condition == "sufficiency" else "trained",
        "donor_training_id": f"{kind}/{_cohort(seed, identity, order)}/{donor_condition}",
        "recipient_training_id": f"{kind}/{_cohort(seed, identity, order)}/{recipient_condition}",
        "donor_training_end_tick": end, "recipient_training_end_tick": end,
        "donor_checkpoint_sha256": donor,
        "recipient_checkpoint_sha256": recipient,
        "parent_checkpoint_sha256": recipient,
        "post_intervention_checkpoint_sha256": _intervention_hash(seed, identity, order, condition),
        "donor_candidate_memory_sha256": donor_memory,
        "recipient_candidate_memory_before_sha256": before_memory,
        "recipient_candidate_memory_after_sha256": donor_memory,
        "noncandidate_state_before_sha256": _h(f"{_cohort(seed, identity, order)}/noncandidate"),
        "noncandidate_state_after_sha256": _h(f"{_cohort(seed, identity, order)}/noncandidate"),
        "replaced_components": ["memory_u", "memory_w", "weight"],
        "complete_replacement": True,
        "branch_id": f"{kind}/{_cohort(seed, identity, order)}/{condition}/intervention",
        "sim_ms": end / 10,
    }


def _responses(kind, *, sign=1):
    events = []
    seeds = (11, 23) if kind == "qualification" else (101, 113)
    for seed in seeds:
        for identity in ("A", "B"):
            for order in ("AB", "BA"):
                cohort = _cohort(seed, identity, order)
                baseline = _baseline_hash(seed, identity, order)
                baseline_branch = f"{kind}/{cohort}/baseline"
                events.append(_checkpoint(f"{kind}-{seed}-{identity}-{order}-baseline.npz",
                                          baseline, BASE_TICK, baseline_branch))
                trainings = {}
                for condition in ORDINARY:
                    training = _training(kind, seed, identity, order, condition)
                    trainings[condition] = training
                    events.append(_checkpoint(
                        f"{kind}-{seed}-{identity}-{order}-{condition}-training.npz",
                        training["training_end_checkpoint_sha256"],
                        training["training_end_tick"], training["branch_id"],
                        (baseline_branch, baseline)))
                    events.append(training)
                for condition in INTERVENTIONS:
                    intervention = _intervention(kind, seed, identity, order, condition)
                    events.append(_checkpoint(
                        f"{kind}-{seed}-{identity}-{order}-{condition}-intervention.npz",
                        intervention["post_intervention_checkpoint_sha256"],
                        intervention["recipient_training_end_tick"],
                        intervention["branch_id"],
                        (trainings["matched_reference" if condition == "sufficiency"
                                   else "paired"]["branch_id"],
                         intervention["recipient_checkpoint_sha256"])))
                    events.append(intervention)
                for retention in (10000, 70000):
                    onset = trainings["paired"]["retention_reference_tick"] + retention * 10
                    for condition in CONDITIONS:
                        recipient_condition = ("matched_reference" if condition == "sufficiency"
                                               else "paired" if condition in {"necessity", "sham"}
                                               else condition)
                        training = trainings[recipient_condition]
                        source = (_intervention_hash(seed, identity, order, condition)
                                  if condition in INTERVENTIONS
                                  else training["training_end_checkpoint_sha256"])
                        retained = _retained_hash(seed, identity, order, condition, retention)
                        retained_branch = f"{kind}/{cohort}/{condition}/{retention}/retention"
                        source_branch = (f"{kind}/{cohort}/{condition}/intervention"
                                         if condition in INTERVENTIONS
                                         else training["branch_id"])
                        events.append(_checkpoint(
                            f"{kind}-{seed}-{identity}-{order}-{condition}-{retention}-retained.npz",
                            retained, onset - 1000, retained_branch,
                            (source_branch, source)))
                        for phase in ("pre", "post"):
                            for stimulus in ("A", "B", "C"):
                                rate = ({"A": 5, "B": 3, "C": 4} if sign == 1
                                        else {"A": 8, "B": 6, "C": 4})[stimulus]
                                if phase == "post" and condition in {"paired", "sufficiency", "sham"}:
                                    if stimulus == identity:
                                        rate += sign * 4
                                cs_tick = BASE_TICK + 1000 if phase == "pre" else onset
                                parent = baseline if phase == "pre" else retained
                                events.append({
                                    "type": ("qualification_evidence" if kind == "qualification"
                                             else "assay_response"),
                                    "branch_id": (f"{kind}/{seed}/{identity}/{order}/{condition}/"
                                                  f"{retention}/{phase}/{stimulus}"),
                                    "evidence_version": "mbon11-response/v1",
                                    "seed": seed, "paired_identity": identity,
                                    "presentation_order": order, "retention_ms": retention,
                                    "condition": condition, "phase": phase,
                                    "stimulus": stimulus,
                                    "candidate_identity": "kc-mbon11-ppl101/v1",
                                    "population": "mbon11", "population_size": 10,
                                    "cs_onset_tick": cs_tick,
                                    "bins": [{"start_tick": cs_tick, "end_tick": cs_tick + 1000,
                                              "spikes": rate}],
                                    "rate_hz": float(rate),
                                    "training_id": training["training_id"],
                                    "association_t0_tick": training["association_t0_tick"],
                                    "retention_reference_tick": training["retention_reference_tick"],
                                    "training_start_tick": training["training_start_tick"],
                                    "training_end_tick": training["training_end_tick"],
                                    "last_visual_end_tick": training["last_visual_end_tick"],
                                    "last_external_dan_end_tick": training["last_external_dan_end_tick"],
                                    "unpaired_nearest_cs_boundary_ticks": training["unpaired_nearest_cs_boundary_ticks"],
                                    "training_visual_exposure_ticks": training["training_visual_exposure_ticks"],
                                    "training_end_checkpoint_sha256": training["training_end_checkpoint_sha256"],
                                    "retention_source_checkpoint_sha256": source,
                                    "parent_checkpoint_sha256": parent,
                                    "parent_branch_id": (baseline_branch if phase == "pre"
                                                         else retained_branch),
                                    "passive_decay_ticks": onset - training["training_end_tick"],
                                    "input_sha256": _input_hashes(kind)[str(seed)][stimulus],
                                    "black_sha256": _input_hashes(kind)[str(seed)]["black"],
                                    "endogenous_dan_spikes": 2 if condition == "no_external_dan" else 0,
                                    "learning": False,
                                    "external_stimulation": None,
                                    "intervention_id": (f"{seed}-{identity}-{order}-{condition}"
                                                        if condition in INTERVENTIONS else None),
                                    "response_replay_resolution_hz": 0.1,
                                    "one_spike_rate_hz": 1.0,
                                    "sim_ms": (cs_tick + 1000) / 10,
                                })
    return events


def _qualification(sign=1):
    factors = []
    for seed in (11, 23):
        for identity in ("A", "B"):
            for order in ("AB", "BA"):
                pre = [5.0, 3.0, 4.0] if sign == 1 else [8.0, 6.0, 4.0]
                post = pre.copy()
                post[0 if identity == "A" else 1] += sign * 4
                factors.append({
                    "seed": seed, "paired_identity": identity,
                    "presentation_order": order,
                    "pre_mbon11": pre, "post_mbon11": post,
                    "pre_mbon07": [2.0, 3.0, 4.0],
                    "post_mbon07": [2.0, 3.0, 4.0],
                    "delta_hz": sign * 4,
                    "response_replay_resolution_hz": 0.0,
                    "one_spike_rate_hz": 1.0,
                    "state_replay_resolution": 0.0, "state_shift": 1.0,
                    "training_memory_w": [1.0, 1.0],
                    "matched_memory_w": [0.0, 0.0],
                    "replay_memory_w": [1.0, 1.0],
                    "washout_hz": 0.0, "washout_threshold_hz": 1.0,
                    "maximum_bound_hit_fraction": 0.0,
                    "modeled_drive": [1.0, 1.0, 1.0],
                    "candidate_kc_vectors": [[1, 0], [0, 1]],
                    "post_candidate_kc_vectors": [[1, 0], [0, 1]],
                    "candidate_kc_ids": [1, 2],
                    "candidate_edge_indices": [1, 2],
                    "candidate_edge_pre_source_ids": ["101", "102"],
                    "candidate_edge_post_source_ids": ["201", "202"],
                    "candidate_kc_source_ids": ["101", "102"],
                    "dan_source_ids": ["301"],
                    "dan_indices": [3], "rate_kc": [1.0, 2.0],
                    "rate_dan": [1.0], "reasons": [],
                })
    events = [{"type": "qualification_point", "point": {
        "configuration": CONFIGURATION, "response_window": WINDOW,
        "retention_ms": 10000.0, "replicates": factors,
        "mean_delta_hz": sign * 4.0, "reasons": [],
    }}]
    events.extend(_responses("qualification", sign=sign))
    events.append({
        "type": "qualification_result", "status": "supported",
        "family": "qualification", "seeds": [11, 23],
        "selected_configuration": CONFIGURATION, "selected_window": WINDOW,
        "selected_retention_ms": 10000.0, "observed_effect_sign": sign,
    })
    return FixtureRun(_manifest("qualification", events), events)


def _confirmation(frozen, sign=1):
    events = _responses("confirmation", sign=sign)
    manifest = _manifest("confirmation", events)
    manifest["metadata"]["frozen_config_sha256"] = frozen.digest
    config = frozen.to_dict()
    manifest["metadata"]["assay_contract"] = {
        "selected_configuration": config["selected_configuration"],
        "response_window": config["response_window"],
        "retention_times_ms": config["retention_times_ms"],
        "expected_effect_sign": config["expected_effect_sign"],
        "conditions": config["conditions"],
        "interventions": config["interventions"],
        "stimuli": ["A", "B", "C"],
        "analysis_version": config["analysis_version"],
    }
    return FixtureRun(manifest, events)


def _seal(run, frozen):
    events = list(run.iter_events())
    report = assess_assay_evidence(events, frozen)
    report.values["verification_mode"] = "integrity-only"
    reduced = reduce_assay_evidence(events, frozen)
    report.values["nonmaterialized_parents"] = [
        {"parent_sha256": digest, "parent_kind": kind}
        for digest, kind in sorted({(cell["parent_sha256"], cell["parent_kind"])
                                   for rows in reduced.rows.values() for row in rows.values()
                                   for cell in row.values() if cell["parent_kind"] == "anchor"})]
    value = report.to_dict()
    digest = sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    events[-1]["scientific_sha256"] = H["events"]
    events.append({
        "type": "assay_result", "sequence": len(events),
        "previous_scientific_sha256": H["events"],
        "scientific_sha256": H["scientific"],
        "result_version": "mbon11-assay-result/v1",
        "frozen_config_sha256": frozen.digest,
        "analysis_version": "mbon11-causal-analysis/v1",
        "status": report.status, "reasons": list(report.reasons),
        "report": value, "report_sha256": digest,
        "evidence_event_count": len(events),
        "evidence_final_scientific_sha256": H["events"],
    })
    return FixtureRun(run.manifest, events, run.replay_attested_state_anchors)


def _report(run, frozen):
    return analyze_assay(_seal(run, frozen), frozen)


def _replace_response(run, predicate, **changes):
    events = list(run.iter_events())
    for event in events:
        if event["type"] in {"qualification_evidence", "assay_response"} and predicate(event):
            event.update(changes)
            break
    else:
        raise AssertionError("fixture response missing")
    return FixtureRun(run.manifest, events)


def _is_cell(event, *, condition="paired", phase="post", stimulus="A",
             seed=101, identity="A", order="AB", retention=10000):
    return all(event[key] == value for key, value in (
        ("condition", condition), ("phase", phase), ("stimulus", stimulus),
        ("seed", seed), ("paired_identity", identity),
        ("presentation_order", order), ("retention_ms", retention),
    ))


def test_complete_qualification_freezes_hand_calculated_floor_and_assay_passes():
    frozen = build_frozen_config(_qualification())
    assert frozen.to_dict()["effect_floor_hz"] == pytest.approx(0.5)
    assert frozen.to_dict()["replay_resolution_hz"] == pytest.approx(0.1)
    assert frozen.to_dict()["max_abs_control_delta_hz"] == 0
    assert frozen.to_dict()["dynamic_range_hz"] == 2
    assert frozen.to_dict()["one_spike_floor_hz"] == 1
    report = _report(_confirmation(frozen), frozen)
    assert report.status == "supported"
    assert report.reasons == ()
    cell = report.values["cells"]["101/A/AB/10000"]
    assert cell["delta_hz"]["paired"] == 4
    assert cell["delta_hz"]["no_external_dan"] == 0
    assert cell["endogenous_dan_spikes"]["no_external_dan"] == 6
    assert cell["global_gain_residual_hz"] == 4


def test_arithmetic_primary_analysis_is_independent_of_optional_motor_proposals():
    """Pure analysis fixture; this does not establish native/artifact qualification."""
    from fly_connectome_sim.experiment import adapter as adapter_module

    adapter_type = getattr(adapter_module, "LateralMotorAdapter", None)
    assert adapter_type is not None, "Missing motor-only adapter API"
    frozen = build_frozen_config(_qualification())
    confirmation = _confirmation(frozen)
    baseline = _report(confirmation, frozen)
    proposals = []
    reports = []
    for left, right in ((5.0, 15.0), (15.0, 5.0)):
        events = list(confirmation.iter_events())
        source = events[0]
        telemetry = {
            "engine_identity": confirmation.manifest["metadata"]["engine_identity"],
            "sim_ms": source["sim_ms"],
            "rates_hz": {"motor_left": left, "motor_right": right},
        }
        decision = asdict(adapter_type().adapt(telemetry))
        events.insert(1, {
            "type": "observation", "branch_id": source["branch_id"],
            "sim_ms": source["sim_ms"], "telemetry": telemetry,
            "motor_readout": {
                "interpretation": "engineered_unvalidated_motor_readout",
                "action_threshold_hz": 1.0, "decision": decision,
            },
        })
        reports.append(_report(FixtureRun(confirmation.manifest, events), frozen))
        proposals.append(decision["action"])
    assert proposals == ["inspect_right", "inspect_left"]
    assert baseline.status == "supported"
    assert baseline.reasons == ()
    assert baseline.values["cells"]["101/A/AB/10000"]["delta_hz"]["paired"] == 4
    for report in reports:
        assert report.to_dict() == baseline.to_dict()


def test_negative_expected_sign_uses_signed_effect_without_changing_floors():
    frozen = build_frozen_config(_qualification(sign=-1))
    report = _report(_confirmation(frozen, sign=-1), frozen)
    assert report.status == "supported"
    assert report.values["cells"]["101/A/AB/10000"]["delta_hz"]["paired"] == -4


@pytest.mark.parametrize("condition", ["frozen_plasticity", "no_external_dan",
                                        "temporally_unpaired"])
@pytest.mark.parametrize("retention", [10000, 70000])
def test_each_control_at_each_retention_can_independently_fail(condition, retention):
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    match = lambda event: _is_cell(event, condition=condition, retention=retention)
    run = _replace_response(run, match, rate_hz=9.0,
                            bins=[{"start_tick": 209000 + retention * 10,
                                   "end_tick": 210000 + retention * 10, "spikes": 9}])
    report = _report(run, frozen)
    assert report.status == "unsupported"
    assert any(condition in reason for reason in report.reasons)


def test_global_multiplication_has_nonzero_delta_but_fails_residual():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    for event in events:
        if event["type"] == "assay_response" and event["condition"] == "paired" \
                and event["phase"] == "post":
            original = {"A": 5, "B": 3, "C": 4}[event["stimulus"]]
            event["rate_hz"] = float(2 * original)
            event["bins"][0]["spikes"] = 2 * original
    report = _report(FixtureRun(run.manifest, events), frozen)
    assert report.status == "unsupported"
    assert report.values["cells"]["101/A/AB/10000"]["delta_hz"]["paired"] == 2
    assert report.values["cells"]["101/A/AB/10000"]["global_gain_residual_hz"] == 0
    assert any("global_gain" in reason for reason in report.reasons)


@pytest.mark.parametrize("condition", INTERVENTIONS)
def test_each_intervention_has_an_independent_scientific_gate(condition):
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    for event in events:
        if event["type"] == "assay_response" and event["condition"] == condition \
                and event["phase"] == "post" and event["stimulus"] == event["paired_identity"]:
            value = 7 if condition == "necessity" else 5
            event["rate_hz"] = float(value)
            event["bins"][0]["spikes"] = value
    report = _report(FixtureRun(run.manifest, events), frozen)
    assert report.status == "unsupported"
    assert any(condition in reason for reason in report.reasons)


def test_missing_or_duplicate_response_is_inconclusive_even_when_other_gate_fails():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    target = next(i for i, item in enumerate(events)
                  if item["type"] == "assay_response" and _is_cell(item))
    events.pop(target)
    report = _report(FixtureRun(run.manifest, events), frozen)
    assert report.status == "inconclusive"
    assert any("missing" in reason for reason in report.reasons)
    events.insert(target, deepcopy(events[target]))
    report = _report(FixtureRun(run.manifest, events), frozen)
    assert report.status == "inconclusive"


@pytest.mark.parametrize("field,value", [
    ("population_size", 11), ("learning", True), ("external_stimulation", "ppl101"),
    ("input_sha256", "f" * 64), ("parent_checkpoint_sha256", "f" * 64),
    ("rate_hz", 99.0), ("bins", [{"start_tick": 101001, "end_tick": 102001, "spikes": 5}]),
])
def test_malformed_response_is_inconclusive(field, value):
    frozen = build_frozen_config(_qualification())
    run = _replace_response(_confirmation(frozen), _is_cell, **{field: value})
    assert _report(run, frozen).status == "inconclusive"


def test_unsupported_or_incomplete_qualification_emits_no_config():
    run = _qualification()
    events = list(run.iter_events())
    events[-1]["status"] = "unsupported"
    with pytest.raises(AnalysisError):
        build_frozen_config(FixtureRun(run.manifest, events))
    events = list(run.iter_events())
    events = [event for event in events if event["type"] != "qualification_evidence"
              or event["retention_ms"] != 70000]
    with pytest.raises(AnalysisError):
        build_frozen_config(FixtureRun(run.manifest, events))


def test_qualification_intervention_failure_blocks_freeze():
    run = _qualification()
    events = list(run.iter_events())
    for event in events:
        if event["type"] == "qualification_evidence" and event["condition"] == "necessity" \
                and event["phase"] == "post" and event["stimulus"] == event["paired_identity"]:
            event["rate_hz"] = 9.0
            event["bins"][0]["spikes"] = 9
    with pytest.raises(AnalysisError, match="necessity"):
        build_frozen_config(FixtureRun(run.manifest, events))


def test_frozen_json_rejects_unknown_missing_nonfinite_bool_and_derived_mismatch():
    frozen = build_frozen_config(_qualification())
    raw = frozen.to_json()
    assert FrozenAssayConfig.from_json(raw).to_json() == raw
    for change in ({"unexpected": 1}, {"effect_floor_hz": False},
                   {"effect_floor_hz": 999}, {"analysis_version": "unknown/v1"},
                   {"effect_floor_hz": float("nan")}):
        data = frozen.to_dict()
        data.update(change)
        with pytest.raises(AnalysisError):
            FrozenAssayConfig.from_json(json.dumps(data))
    data = frozen.to_dict()
    del data["effect_floor_hz"]
    with pytest.raises(AnalysisError):
        FrozenAssayConfig.from_json(json.dumps(data))
    with pytest.raises(AnalysisError):
        FrozenAssayConfig.from_json('{"digest":"x","digest":"y"}')


def test_held_out_values_cannot_change_frozen_floor_or_digest():
    frozen = build_frozen_config(_qualification())
    digest = frozen.digest
    run = _confirmation(frozen)
    events = list(run.iter_events())
    for event in events:
        if event["type"] == "assay_response" and event["condition"] == "paired" \
                and event["phase"] == "post" and event["stimulus"] == event["paired_identity"]:
            event["rate_hz"] = 50.0
            event["bins"][0]["spikes"] = 50
    _report(FixtureRun(run.manifest, events), frozen)
    assert frozen.digest == digest
    assert frozen.to_dict()["effect_floor_hz"] == 0.5


def test_shared_reducer_is_pure_and_rejects_missing_response():
    frozen = build_frozen_config(_qualification())
    events = list(_confirmation(frozen).iter_events())
    snapshot = deepcopy(events)
    reduction = reduce_assay_evidence(events, frozen)
    assert reduction.status == "supported"
    assert events == snapshot
    del events[-1]
    assert reduce_assay_evidence(events, frozen).status == "inconclusive"


@pytest.mark.parametrize("condition", INTERVENTIONS)
def test_intervention_memory_hash_must_match_declared_atomic_replacement(condition):
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    target = next(event for event in events if event["type"] == "assay_intervention"
                  and event["condition"] == condition)
    target["recipient_candidate_memory_after_sha256"] = H["memory_after"]
    report = _report(FixtureRun(run.manifest, events), frozen)
    assert report.status == "inconclusive"
    assert any("intervention" in reason for reason in report.reasons)


def test_anchor_parent_requires_prior_complete_anchor_with_durable_ancestor():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    targets = [event for event in events if event["type"] == "assay_response"
               and event["seed"] == 101 and event["paired_identity"] == "A"
               and event["presentation_order"] == "AB"
               and event["retention_ms"] == 10000 and event["condition"] == "paired"
               and event["phase"] == "post"]
    assert len(targets) == 3
    for target in targets:
        del target["parent_checkpoint_sha256"]
        target["parent_state_anchor_sha256"] = H["memory_after"]
    assert _report(FixtureRun(run.manifest, events), frozen).status == "inconclusive"
    anchor = {
        "type": "state_anchor", "anchor_version": "state-anchor/v1",
        "anchor_id": "retained-101-A-AB-T", "state_anchor_sha256": H["memory_after"],
        "origin_branch_id": "confirmation/101/A/AB/paired/10000/retention",
        "sim_tick": 308000,
        "durable_ancestor_checkpoint_sha256": _training_hash(101, "A", "AB", "paired"),
        "replay_recipe_sha256": H["events"],
        "source_identity_sha256": frozen.to_dict()["engine_identity"]["sha256"],
    }
    position = next(i for i, event in enumerate(events) if event is targets[0])
    events.insert(position, anchor)
    assert _report(FixtureRun(run.manifest, events), frozen).status == "inconclusive"
    assert assess_assay_evidence(events, frozen,
                                attested_state_anchors=[H["memory_after"]]).status == "supported"
    assert _report(FixtureRun(run.manifest, events, [H["memory_after"]]), frozen).status == "inconclusive"
    anchor["durable_ancestor_checkpoint_sha256"] = H["memory_after"]
    assert _report(FixtureRun(run.manifest, events, [H["memory_after"]]), frozen).status == "inconclusive"


def test_arithmetic_qualification_anchor_fixture_can_freeze():
    run = _qualification()
    events = list(run.iter_events())
    targets = [event for event in events if event["type"] == "qualification_evidence"
               and event["seed"] == 11 and event["paired_identity"] == "A"
               and event["presentation_order"] == "AB"
               and event["retention_ms"] == 10000
               and event["condition"] == "paired" and event["phase"] == "post"]
    assert len(targets) == 3
    digest = H["memory_after"]
    for target in targets:
        del target["parent_checkpoint_sha256"]
        target["parent_state_anchor_sha256"] = digest
    anchor = {
        "type": "state_anchor", "anchor_version": "state-anchor/v1",
        "anchor_id": "qualification-retained-11-A-AB-T",
        "state_anchor_sha256": digest,
        "origin_branch_id": targets[0]["parent_branch_id"],
        "sim_tick": targets[0]["cs_onset_tick"] - 1000,
        "durable_ancestor_checkpoint_sha256": targets[0]["retention_source_checkpoint_sha256"],
        "replay_recipe_sha256": H["events"],
        "source_identity_sha256": run.manifest["metadata"]["engine_identity"]["sha256"],
    }
    events.insert(next(i for i, event in enumerate(events) if event is targets[0]), anchor)
    assert build_frozen_config(FixtureRun(run.manifest, events, [digest])).digest


def test_identical_sham_checkpoint_content_keeps_ancestry_valid():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    manifest = run.manifest
    old_digest = _intervention_hash(101, "A", "AB", "sham")
    new_digest = _training_hash(101, "A", "AB", "paired")
    manifest["checkpoints"]["confirmation-101-A-AB-sham-intervention.npz"]["sha256"] = new_digest
    for event in events:
        if (event.get("checkpoint_name")
                == "confirmation-101-A-AB-sham-intervention.npz"):
            event["checkpoint_sha256"] = new_digest
        elif (event.get("type") == "assay_intervention" and event["seed"] == 101
              and event["paired_identity"] == "A"
              and event["presentation_order"] == "AB"
              and event["condition"] == "sham"):
            event["post_intervention_checkpoint_sha256"] = new_digest
        elif (event.get("parent_checkpoint_sha256") == old_digest):
            event["parent_checkpoint_sha256"] = new_digest
        elif (event.get("type") == "assay_response" and event["seed"] == 101
              and event["paired_identity"] == "A"
              and event["presentation_order"] == "AB"
              and event["condition"] == "sham"):
            event["retention_source_checkpoint_sha256"] = new_digest
    report = _report(FixtureRun(manifest, events), frozen)
    assert report.status == "supported", report.reasons


def test_neutral_events_above_old_stream_limit_do_not_reject_evidence():
    qualification = _qualification()
    qualification_events = list(qualification.iter_events())
    qualification_events[-1:-1] = [{"type": "neutral"}] * 10002
    frozen = build_frozen_config(FixtureRun(_manifest("qualification", qualification_events),
                                            qualification_events))
    confirmation = _confirmation(frozen)
    confirmation_events = list(confirmation.iter_events())
    confirmation_events.extend([{"type": "neutral"}] * 10002)
    assert _report(FixtureRun(confirmation.manifest, confirmation_events), frozen).status == "supported"


def test_neutral_first_event_can_declare_relevant_branch_ancestry():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    position = next(i for i, event in enumerate(events)
                    if event.get("checkpoint_name")
                    == "confirmation-101-A-AB-paired-10000-retained.npz")
    retained = events[position]
    events.insert(position, {
        "type": "neutral", "branch_id": retained["branch_id"],
        "parent_branch_id": retained.pop("parent_branch_id"),
        "parent_checkpoint_sha256": retained.pop("parent_checkpoint_sha256"),
        "sim_ms": retained["sim_ms"],
    })
    assert _report(FixtureRun(run.manifest, events), frozen).status == "supported"


def test_relevant_event_limit_is_checked_after_stream_exhaustion():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    exhausted = False

    def events():
        nonlocal exhausted
        yield from run.iter_events()
        for _ in range(10001):
            yield {"type": "branch_start", "branch_id": "repeated-extra"}
        exhausted = True

    reduction = reduce_assay_evidence(events(), frozen)
    assert exhausted
    assert reduction.status == "inconclusive"
    assert "evidence_event_limit" in reduction.reasons


def test_confirmation_second_scan_reaches_verified_stream_eof():
    frozen = build_frozen_config(_qualification())
    run = _seal(_confirmation(frozen), frozen)

    class ChangedAtSecondEof(FixtureRun):
        def __init__(self, manifest, events):
            super().__init__(manifest, events)
            object.__setattr__(self, "_scans", 0)

        def iter_events(self):
            object.__setattr__(self, "_scans", self._scans + 1)
            yield from super().iter_events()
            if self._scans == 2:
                raise ValueError("changed at EOF")

    with pytest.raises(AnalysisError, match="verified_run_changed"):
        analyze_assay(ChangedAtSecondEof(run.manifest, list(run.iter_events())), frozen)


def test_invalid_qualification_control_still_exhausts_verified_scan():
    run = _qualification()
    events = list(run.iter_events())
    events.insert(-1, {"type": "qualification_control", "control": {}})

    class EofProbe(FixtureRun):
        def __init__(self, manifest, events):
            super().__init__(manifest, events)
            object.__setattr__(self, "eof_count", 0)

        def iter_events(self):
            yield from super().iter_events()
            object.__setattr__(self, "eof_count", self.eof_count + 1)

    probe = EofProbe(run.manifest, events)
    with pytest.raises(AnalysisError, match="qualification_control_invalid"):
        build_frozen_config(probe)
    assert probe.eof_count == 4


def test_nonintegral_checkpoint_clock_is_inconclusive_after_exhaustion():
    frozen = build_frozen_config(_qualification())
    events = list(_confirmation(frozen).iter_events())
    checkpoint = next(event for event in events if event.get("checkpoint_name")
                      == "confirmation-101-A-AB-paired-10000-retained.npz")
    checkpoint["sim_ms"] += 0.05
    exhausted = False

    def stream():
        nonlocal exhausted
        yield from events
        exhausted = True

    reduction = reduce_assay_evidence(stream(), frozen)
    assert exhausted
    assert reduction.status == "inconclusive"
    assert "invalid_checkpoint_clock" in reduction.reasons


def test_qualification_control_spread_raises_floor_from_hand_checked_one_hertz():
    run = _qualification()
    events = list(run.iter_events())
    target = next(event for event in events if event["type"] == "qualification_evidence"
                  and _is_cell(event, seed=11, condition="frozen_plasticity"))
    target["rate_hz"] = 6.0
    target["bins"][0]["spikes"] = 6
    replicate = next(item for item in events[0]["point"]["replicates"]
                     if (item["seed"], item["paired_identity"], item["presentation_order"])
                     == (11, "A", "AB"))
    replicate["washout_hz"] = 1.0
    frozen = build_frozen_config(FixtureRun(run.manifest, events))
    assert frozen.to_dict()["max_abs_control_delta_hz"] == 1
    assert frozen.to_dict()["effect_floor_hz"] == 2


@pytest.mark.parametrize("field,value", [
    ("last_visual_end_tick", 200100),
    ("last_external_dan_end_tick", 200100),
    ("training_visual_exposure_ticks", {"A": 900, "B": 1000, "C": 0}),
])
def test_t0_origin_and_matched_exposure_are_required(field, value):
    frozen = build_frozen_config(_qualification())
    run = _replace_response(_confirmation(frozen), _is_cell, **{field: value})
    assert reduce_assay_evidence(run.iter_events(), frozen).status == "inconclusive"


def test_sealed_analysis_requires_one_matching_terminal_result():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    assert analyze_assay(run, frozen).status == "inconclusive"
    sealed = _seal(run, frozen)
    events = list(sealed.iter_events())
    events[-1]["status"] = "unsupported"
    assert analyze_assay(FixtureRun(run.manifest, events), frozen).status == "inconclusive"
    events = list(sealed.iter_events())
    events[-1]["evidence_final_scientific_sha256"] = H["memory_after"]
    assert analyze_assay(FixtureRun(run.manifest, events), frozen).status == "inconclusive"


def test_direct_frozen_construction_cannot_bypass_digest_validation():
    with pytest.raises(AnalysisError):
        FrozenAssayConfig("{}\n")


def test_intervention_checkpoint_hash_must_exist_in_sealed_inventory():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    manifest = run.manifest
    del manifest["checkpoints"]["confirmation-101-A-AB-necessity-intervention.npz"]
    assert _report(FixtureRun(manifest, list(run.iter_events())), frozen).status == "inconclusive"


def test_retention_branches_must_be_distinct_copies():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    ten = next(event for event in events if event["type"] == "assay_response"
               and _is_cell(event))
    later = next(event for event in events if event["type"] == "assay_response"
                 and _is_cell(event, retention=70000))
    later["branch_id"] = ten["branch_id"]
    assert reduce_assay_evidence(events, frozen).status == "inconclusive"


@pytest.mark.parametrize("condition,field,value", [
    ("temporally_unpaired", "unpaired_nearest_cs_boundary_ticks", 99999),
    ("no_external_dan", "last_external_dan_end_tick", 1000),
    ("paired", "last_external_dan_end_tick", None),
    ("sufficiency", "last_external_dan_end_tick", 1000),
])
def test_external_dan_and_unpaired_separation_contract(condition, field, value):
    frozen = build_frozen_config(_qualification())
    run = _replace_response(_confirmation(frozen),
                            lambda event: _is_cell(event, condition=condition),
                            **{field: value})
    assert reduce_assay_evidence(run.iter_events(), frozen).status == "inconclusive"


def test_engine_identity_uses_engine_canonical_escaping_for_nonascii_fields():
    run = _qualification()
    manifest = run.manifest
    identity = manifest["metadata"]["engine_identity"]
    identity["model_provenance"]["model"] = "MäleCNS"
    identity["model_provenance"]["build"]["model"] = "MäleCNS"
    payload = {key: value for key, value in identity.items() if key != "sha256"}
    identity["sha256"] = sha256(json.dumps(payload, sort_keys=True,
                                           separators=(",", ":")).encode()).hexdigest()
    frozen = build_frozen_config(FixtureRun(manifest, list(run.iter_events())))
    assert frozen.to_dict()["engine_identity"]["model_provenance"]["model"] == "MäleCNS"


def test_qualification_requires_all_referenced_durable_checkpoints():
    run = _qualification()
    manifest = run.manifest
    del manifest["checkpoints"]["qualification-11-A-AB-matched_reference-training.npz"]
    with pytest.raises(AnalysisError, match="checkpoint"):
        build_frozen_config(FixtureRun(manifest, list(run.iter_events())))


def test_qualification_rejects_duplicate_selected_control_summary():
    run = _qualification()
    events = list(run.iter_events())
    summary = {"type": "qualification_control", "control": {
        "seed": 11, "paired_identity": "A", "presentation_order": "AB",
        "condition": "frozen_plasticity", "delta_hz": 0.0,
    }}
    events[-1:-1] = [deepcopy(summary), deepcopy(summary)]
    with pytest.raises(AnalysisError, match="control"):
        build_frozen_config(FixtureRun(run.manifest, events))


def test_selected_grid_point_can_differ_from_later_matched_raw_cohort():
    run = _qualification()
    events = list(run.iter_events())
    point = events[0]["point"]
    for replicate in point["replicates"]:
        replicate["delta_hz"] = 3.0
        replicate["post_mbon11"][0 if replicate["paired_identity"] == "A" else 1] -= 1
    point["mean_delta_hz"] = 3.0
    frozen = build_frozen_config(FixtureRun(run.manifest, events))
    assert frozen.to_dict()["effect_floor_hz"] == 0.5


def test_resigned_frozen_config_still_rejects_wrong_qualification_input_set():
    frozen = build_frozen_config(_qualification())
    data = frozen.to_dict()
    data["qualification_input_sha256"][0] = H["memory_after"]
    payload = {name: value for name, value in data.items() if name != "digest"}
    data["digest"] = sha256(json.dumps(payload, sort_keys=True,
                                       separators=(",", ":"),
                                       ensure_ascii=False).encode()).hexdigest()
    with pytest.raises(AnalysisError, match="qualification_input_hashes"):
        FrozenAssayConfig.from_dict(data)


@pytest.mark.parametrize("location", ["grid", "window"])
def test_resigned_config_rejects_boolean_nested_numeric_field(location):
    data = build_frozen_config(_qualification()).to_dict()
    if location == "grid":
        data["selected_configuration"]["dan_onset_ms"] = False
    else:
        data["response_window"]["start_ms"] = False
    payload = {name: value for name, value in data.items() if name != "digest"}
    data["digest"] = sha256(json.dumps(payload, sort_keys=True,
                                       separators=(",", ":"),
                                       ensure_ascii=False).encode()).hexdigest()
    with pytest.raises(AnalysisError):
        FrozenAssayConfig.from_dict(data)


def test_nonfinite_nested_engine_identity_uses_analysis_error():
    data = build_frozen_config(_qualification()).to_dict()
    data["engine_identity"]["model_provenance"]["eta"] = float("nan")
    with pytest.raises(AnalysisError):
        FrozenAssayConfig.from_dict(data)


def test_changed_verified_qualification_is_wrapped_as_analysis_error():
    class ChangedRun(FixtureRun):
        def iter_events(self):
            raise ValueError("changed after verification")

    run = _qualification()
    with pytest.raises(AnalysisError, match="verified_run_changed"):
        build_frozen_config(ChangedRun(run.manifest, list(run.iter_events())))


@pytest.mark.parametrize("start", [0, 150000])
def test_pre_response_must_precede_a_common_training_start(start):
    frozen = build_frozen_config(_qualification())
    run = _replace_response(_confirmation(frozen), _is_cell,
                            training_start_tick=start)
    assert reduce_assay_evidence(run.iter_events(), frozen).status == "inconclusive"


def test_each_test_stimulus_uses_a_separate_copy_of_same_retained_state():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    paired_a = next(event for event in events if event["type"] == "assay_response"
                    and _is_cell(event))
    paired_b = next(event for event in events if event["type"] == "assay_response"
                    and _is_cell(event, stimulus="B"))
    paired_b["branch_id"] = paired_a["branch_id"]
    assert reduce_assay_evidence(events, frozen).status == "inconclusive"
    paired_b["branch_id"] = "separate-test-branch"
    paired_b["parent_checkpoint_sha256"] = H["recipient"]
    assert reduce_assay_evidence(events, frozen).status == "inconclusive"


def test_confirmation_metadata_cannot_add_post_hoc_exclusions():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    manifest = run.manifest
    manifest["metadata"]["exclusions"] = ["seed-113"]
    assert _report(FixtureRun(manifest, list(run.iter_events())), frozen).status == "inconclusive"


@pytest.mark.parametrize("field,value", [
    ("selected_configuration", {"cs_duration_ms": 100.0,
                                "dan_onset_ms": 100.0, "post_pair_gap_ms": 500.0}),
    ("response_window", {"start_ms": 10.0, "end_ms": 100.0}),
    ("retention_times_ms", [10000, 80000]),
    ("expected_effect_sign", -1),
    ("stimuli", ["A", "B"]),
])
def test_confirmation_metadata_binds_frozen_protocol(field, value):
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    manifest = run.manifest
    manifest["metadata"]["assay_contract"][field] = value
    assert _report(FixtureRun(manifest, list(run.iter_events())), frozen).status == "inconclusive"


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_type"])
def test_confirmation_metadata_requires_exact_assay_contract(mutation):
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    manifest = run.manifest
    contract = manifest["metadata"]["assay_contract"]
    if mutation == "missing":
        del contract["analysis_version"]
    elif mutation == "extra":
        contract["post_hoc_override"] = True
    else:
        contract["expected_effect_sign"] = True
    assert _report(FixtureRun(manifest, list(run.iter_events())), frozen).status == "inconclusive"


def test_training_evidence_is_required_before_freeze():
    run = _qualification()
    events = list(run.iter_events())
    events.remove(next(event for event in events
                       if event["type"] == "qualification_training"))
    with pytest.raises(AnalysisError, match="qualification_evidence"):
        build_frozen_config(FixtureRun(run.manifest, events))


def test_unrelated_durable_donor_checkpoint_cannot_authorize_intervention():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    intervention = next(event for event in events if event["type"] == "assay_intervention"
                        and event["seed"] == 101 and event["condition"] == "necessity")
    intervention["donor_checkpoint_sha256"] = _training_hash(113, "A", "AB", "matched_reference")
    assert _report(FixtureRun(run.manifest, events), frozen).status == "inconclusive"


def test_retention_checkpoint_must_descend_from_its_declared_source():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    retained = next(event for event in events if event.get("checkpoint_name")
                    == "confirmation-101-A-AB-paired-10000-retained.npz")
    retained["parent_checkpoint_sha256"] = _training_hash(113, "A", "AB", "paired")
    assert _report(FixtureRun(run.manifest, events), frozen).status == "inconclusive"


def test_same_tick_alien_reference_baseline_cannot_split_cohort():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    manifest = run.manifest
    alien = _h("alien-matched-reference-baseline")
    alien_branch = "confirmation/101/A/AB/alien-baseline"
    name = "confirmation-101-A-AB-alien-baseline.npz"
    baseline = _checkpoint(name, alien, BASE_TICK, alien_branch)
    events.insert(next(i for i, event in enumerate(events)
                       if event.get("checkpoint_name")
                       == "confirmation-101-A-AB-baseline.npz") + 1, baseline)
    manifest["checkpoints"][name] = {
        "sha256": alien, "sim_ms": BASE_TICK / 10,
        "origin_branch_id": alien_branch, "size": 1,
    }
    for event in events:
        if event.get("checkpoint_name") == "confirmation-101-A-AB-matched_reference-training.npz":
            event["parent_checkpoint_sha256"] = alien
            event["parent_branch_id"] = alien_branch
        elif (event.get("seed") == 101 and event.get("paired_identity") == "A"
              and event.get("presentation_order") == "AB"):
            if event["type"] == "assay_training" and event["condition"] == "matched_reference":
                event["baseline_checkpoint_sha256"] = alien
            elif (event["type"] == "assay_response" and event["phase"] == "pre"
                  and event["condition"] in {"matched_reference", "sufficiency"}):
                event["parent_checkpoint_sha256"] = alien
                event["parent_branch_id"] = alien_branch
    assert _report(FixtureRun(manifest, events), frozen).status == "inconclusive"


def test_response_event_clock_must_cover_recorded_window():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    events = list(run.iter_events())
    response = next(event for event in events if event["type"] == "assay_response"
                    and _is_cell(event))
    response["sim_ms"] = (response["cs_onset_tick"] - 1000) / 10
    assert _report(FixtureRun(run.manifest, events), frozen).status == "inconclusive"


@pytest.mark.parametrize("field,value", [
    ("reasons", ["washout"]),
    ("washout_hz", 2.0),
    ("washout_threshold_hz", 0.5),
    ("maximum_bound_hit_fraction", 0.02),
    ("state_shift", 0.0),
    ("response_replay_resolution_hz", 0.1),
    ("pre_mbon11", [5.0, 5.0, 4.0]),
    ("candidate_kc_vectors", [[1, 0], [1, 0]]),
])
def test_selected_replicate_gate_is_recomputed(field, value):
    run = _qualification()
    events = list(run.iter_events())
    events[0]["point"]["replicates"][0][field] = value
    with pytest.raises(AnalysisError, match="selected"):
        build_frozen_config(FixtureRun(run.manifest, events))


@pytest.mark.parametrize("field,value", [
    ("candidate_kc_vectors", [[1, 0, 0], [0, 1, 0]]),
    ("post_candidate_kc_vectors", [[1, 0, 0], [0, 1, 0]]),
    ("candidate_kc_ids", [1, 1]),
    ("candidate_edge_indices", [1]),
    ("candidate_edge_indices", [2, 1]),
    ("rate_kc", [1.0]),
    ("dan_indices", [3, 3]),
    ("candidate_edge_pre_source_ids", ["101"]),
    ("candidate_edge_pre_source_ids", ["999", "102"]),
    ("candidate_edge_post_source_ids", ["202", "201"]),
    ("candidate_kc_source_ids", ["101"]),
    ("candidate_kc_source_ids", ["101", "101"]),
    ("dan_source_ids", ["301", "301"]),
])
def test_selected_replicate_observability_dimensions_and_order(field, value):
    run = _qualification()
    events = list(run.iter_events())
    events[0]["point"]["replicates"][0][field] = value
    with pytest.raises(AnalysisError, match="selected"):
        build_frozen_config(FixtureRun(run.manifest, events))


def test_selected_replicate_requires_all_producer_source_ids():
    run = _qualification()
    events = list(run.iter_events())
    for replicate in events[0]["point"]["replicates"]:
        for field in ("candidate_edge_pre_source_ids", "candidate_edge_post_source_ids",
                      "candidate_kc_source_ids", "dan_source_ids"):
            del replicate[field]
    with pytest.raises(AnalysisError, match="selected_replicate_source_order"):
        build_frozen_config(FixtureRun(run.manifest, events))


@pytest.mark.parametrize("mutation", ["zero_shift", "false_resolution", "empty",
                                      "wrong_length", "nonfinite"])
def test_selected_replicate_state_metrics_match_raw_memory(mutation):
    run = _qualification()
    events = list(run.iter_events())
    replicate = events[0]["point"]["replicates"][0]
    if mutation == "zero_shift":
        replicate["training_memory_w"] = [0.0, 0.0]
        replicate["replay_memory_w"] = [0.0, 0.0]
    elif mutation == "false_resolution":
        replicate["replay_memory_w"] = [0.5, 0.5]
    elif mutation == "empty":
        replicate["training_memory_w"] = []
    elif mutation == "wrong_length":
        replicate["matched_memory_w"] = [0.0]
    else:
        replicate["replay_memory_w"] = [float("nan"), 1.0]
    with pytest.raises(AnalysisError, match="selected_replicate_state"):
        build_frozen_config(FixtureRun(run.manifest, events))


def test_selected_replicate_washout_matches_reduced_raw_controls():
    run = _qualification()
    events = list(run.iter_events())
    events[0]["point"]["replicates"][0]["washout_hz"] = 0.5
    with pytest.raises(AnalysisError, match="selected_replicate_washout"):
        build_frozen_config(FixtureRun(run.manifest, events))


def test_absurd_spike_integer_is_inconclusive_not_an_exception():
    frozen = build_frozen_config(_qualification())
    run = _confirmation(frozen)
    huge = 10 ** 1000
    run = _replace_response(run, _is_cell, bins=[{
        "start_tick": 300000, "end_tick": 301000, "spikes": huge,
    }], rate_hz=5.0)
    assert _report(run, frozen).status == "inconclusive"


def test_real_recorder_verified_assay_roundtrip(tmp_path):
    frozen = build_frozen_config(_qualification())
    fixture = _confirmation(frozen)
    source = tmp_path / "source.npz"
    run_path = tmp_path / "recorded"
    root = "confirmation/root"
    events = []
    checkpoint_clocks = {}
    branches = {root}

    def append(recorder, event):
        branch = event["branch_id"]
        if branch not in branches:
            parent_digest = event.get("parent_checkpoint_sha256")
            parent_branch = event.get("parent_branch_id")
            if parent_digest is None:
                parent_digest = before_digest
                parent_branch = root
                event = {**event, "parent_checkpoint_sha256": parent_digest,
                         "parent_branch_id": parent_branch}
            start = {"type": "branch_start", "branch_id": branch,
                     "parent_branch_id": parent_branch,
                     "parent_checkpoint_sha256": parent_digest,
                     "sim_ms": checkpoint_clocks[parent_digest]}
            recorder.append(start)
            events.append(start)
            branches.add(branch)
        recorder.append(event)
        events.append(event)

    with RunRecorder(run_path, run_kind="confirmation", metadata=fixture.manifest["metadata"],
                     root_branch_id=root) as recorder:
        source.write_bytes(b"brain-before")
        before_digest = recorder.ingest_checkpoint("brain-before.npz", source,
                                                    origin_branch_id=root)
        before = _checkpoint("brain-before.npz", before_digest, 0, root)
        recorder.append(before)
        events.append(before)
        checkpoint_clocks[before_digest] = 0.0
        for event in fixture.iter_events():
            if "checkpoint_name" in event:
                parts = event["checkpoint_name"].removesuffix(".npz").split("-")[1:]
                seed, identity, order, *tail = parts
                suffix = ({"baseline": "baseline", "training": "training-end",
                           "intervention": "intervention", "retained": "retained"}[tail[-1]])
                preimage = "/".join((seed, identity, order, *tail[:-1], suffix))
                source.write_bytes(preimage.encode())
                assert recorder.ingest_checkpoint(event["checkpoint_name"], source,
                                                  origin_branch_id=event["branch_id"]) \
                    == event["checkpoint_sha256"]
                checkpoint_clocks[event["checkpoint_sha256"]] = event["sim_ms"]
            append(recorder, event)
        source.write_bytes(b"brain-after")
        after_digest = recorder.ingest_checkpoint("brain-after.npz", source,
                                                  origin_branch_id=root)
        after = _checkpoint("brain-after.npz", after_digest, 0, root)
        recorder.append(after)
        events.append(after)
        from fly_connectome_sim.experiment.analysis import assess_assay_prefix
        prefix = recorder.validate_prefix()
        report = assess_assay_prefix(prefix, frozen)
        assert report.status == "supported"
        value = report.to_dict()
        recorder.append({
            "type": "assay_result", "branch_id": root, "sim_ms": 0.0,
            "result_version": "mbon11-assay-result/v1",
            "frozen_config_sha256": frozen.digest,
            "analysis_version": "mbon11-causal-analysis/v1",
            "status": report.status, "reasons": list(report.reasons),
            "report": value,
            "report_sha256": sha256(json.dumps(value, sort_keys=True,
                                               separators=(",", ":"),
                                               ensure_ascii=False).encode()).hexdigest(),
            "evidence_event_count": prefix.scientific_prefix["event_count"],
            "evidence_final_scientific_sha256": prefix.scientific_prefix["final_scientific_sha256"],
        })
    assert analyze_assay(verify_run(run_path), frozen).status == "supported"




def _native_confirmation_prefix(engine_factory, tmp_path, *, timing=0.0, metadata_changes=None):
    """Retention-route integration; training descriptors are not reconstructed history."""
    from fly_connectome_sim.experiment.replay import (
        OPERATION_VERSION, build_black_retention_recipe, build_state_anchor,
    )

    producer = engine_factory()
    population = len(producer.groups.mbon11)
    frozen = _declared_native_frozen_config(producer)
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    black = {"generator": "black-rgb/v1", "input_shape": [32, 32, 3],
             "input_dtype": "uint8", "input_sha256": _rgb_input_sha256(frame)}
    metadata = {**_confirmation(frozen).manifest["metadata"],
                "engine_identity": producer.identity(),
                "mbon11_population_size": population,
                "protocol_version": "associative-confirmation/v1",
                "stimulus_version": "associative-stimuli/v1", "family": "confirmation",
                "seeds": [101, 113], "black_input": black,
                "input_sha256": sorted({digest for row in _input_hashes("confirmation").values()
                                          for digest in row.values()})}
    metadata.update(metadata_changes or {})
    training = _training("confirmation", 101, "A", "AB", "paired")
    root, branch, retained = "baseline", training["branch_id"], "retention"
    recorder = RunRecorder(tmp_path / "retained-route", run_kind="confirmation", metadata=metadata,
                           root_branch_id=root)
    snapshot = tmp_path / "durable.npz"

    def advance_to(tick):
        while producer.brain.cursor < tick:
            producer.observe(frame, min(5000, tick - producer.brain.cursor) / 10)

    def durable(name, origin):
        producer.brain.checkpoint(snapshot)
        digest = recorder.ingest_checkpoint(name, snapshot, origin_branch_id=origin)
        recorder.append({"type": "checkpoint", "branch_id": origin,
                         "sim_tick": producer.brain.cursor, "sim_ms": producer.brain.cursor / 10,
                         "checkpoint_name": name, **(source_parent if origin == branch else {})})
        return digest

    source_parent = {}
    durable("brain-before.npz", root)
    advance_to(BASE_TICK)
    baseline = durable("baseline.npz", root)
    source_parent = {"parent_branch_id": root, "parent_checkpoint_sha256": baseline,
                     "parent_checkpoint_name": "baseline.npz", "parent_checkpoint_sequence": 1}
    recorder.append({"type": "branch_start", "branch_id": branch, "sim_ms": BASE_TICK / 10,
                     **source_parent})
    advance_to(training["training_end_tick"])
    source = durable("training-end.npz", branch)
    training.update(baseline_checkpoint_sha256=baseline, training_end_checkpoint_sha256=source)
    recorder.append(training)
    source_tick = producer.brain.cursor
    recorder.append({"type": "fork", "branch_id": retained, "sim_tick": source_tick,
                     "sim_ms": source_tick / 10, "operation_version": OPERATION_VERSION,
                     "parent_branch_id": branch, "parent_checkpoint_name": "training-end.npz",
                     "parent_checkpoint_sequence": 3, "parent_checkpoint_sha256": source})
    target = training["retention_reference_tick"] + 100000 - 1000
    while producer.brain.cursor < target:
        start = producer.brain.cursor
        ticks = min(5000, target - start)
        producer.observe(frame, ticks / 10)
        recorder.append({"type": "neutral_gap_chunk", "branch_id": retained, **black,
                         "operation_version": OPERATION_VERSION, "start_tick": start,
                         "end_tick": producer.brain.cursor, "duration_ticks": ticks,
                         "duration_ms": ticks / 10, "sim_ms": producer.brain.cursor / 10,
                         "compute_seconds": timing, "kernel_seconds": timing,
                         "stimulation": None, "learning": False, "current_mv": 20.0,
                         "pathway_detail": False, "qualification_detail": False})
    prefix = recorder.validate_prefix()
    recipe = build_black_retention_recipe(prefix.iter_events(),
        source_occurrence={"checkpoint_name": "training-end.npz", "checkpoint_sha256": source,
                           "origin_branch_id": branch, "checkpoint_sequence": 3, "sim_tick": source_tick},
        origin_branch_id=retained, target_tick=target, engine_identity=producer.identity(),
        run_metadata_sha256=prefix.manifest["run_metadata_sha256"], black_input=black,
        scientific_prefix=prefix.scientific_prefix)
    anchor = build_state_anchor(anchor_id="paired-retained", recipe=recipe,
                               complete_state_sha256=producer.brain.checkpoint_state_sha256())
    recorder.append_state_anchor(anchor)
    scratch = tmp_path / "retention-scratch.npz"
    producer.brain.checkpoint(scratch)
    producer_state = producer.brain.checkpoint_state_sha256()
    siblings = []
    templates = [event for event in _responses("confirmation")
                 if event.get("type") == "assay_response" and (
                     _is_cell(event, stimulus="A") or _is_cell(event, stimulus="B"))]
    assert len(templates) == 2
    for response in templates:
        sibling = engine_factory()
        sibling.brain.restore(scratch)
        assert sibling.brain.checkpoint_state_sha256() == anchor["complete_state_sha256"]
        assert sibling.brain.cursor == target
        siblings.append(sibling)
        response_branch = response["branch_id"]
        parent = {"parent_branch_id": retained, "parent_state_anchor_sha256": anchor["state_anchor_sha256"]}
        recorder.append({"type": "branch_start", "branch_id": response_branch,
                         "sim_ms": target / 10, **parent})
        sibling.observe(frame, 100.0)
        observed = sibling.observe(AssayStimuli(101, "confirmation").frame(response["stimulus"]), 100.0)
        bins = [{"start_tick": target + 1000 + index * 100,
                 "end_tick": target + 1100 + index * 100,
                 "spikes": item["group_spikes"]["mbon11"]}
                for index, item in enumerate(observed["bins"])]
        response.pop("parent_checkpoint_sha256")
        response.update(**parent, bins=bins, population_size=population,
                        rate_hz=sum(item["spikes"] for item in bins) * 1000 / (population * 100),
                        one_spike_rate_hz=1000 / (population * 100),
                        training_end_checkpoint_sha256=source, retention_source_checkpoint_sha256=source)
        recorder.append(response)
    assert siblings[0] is not siblings[1]
    assert producer.brain.checkpoint_state_sha256() == producer_state
    durable("brain-after.npz", root)
    return recorder, frozen, training, anchor, root, target


def test_real_retention_attestation_authorizes_only_the_target_response_routes(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.recorder import verify_replay_run

    recorder, frozen, training, anchor, root, target = _native_confirmation_prefix(engine_factory, tmp_path)
    from fly_connectome_sim.experiment.analysis import build_assay_result
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    recorder.append({"type": "assay_result", "branch_id": root, "sim_ms": target / 10,
                     **build_assay_result(prefix, frozen)})
    recorder.close()
    ordinary = verify_run(recorder.path)
    formal = verify_replay_run(recorder.path, engine_factory=engine_factory)
    reductions = [reduce_assay_evidence(run.iter_events(), frozen,
                   attested_state_anchors=run.replay_attested_state_anchors)
                  for run in (ordinary, formal)]
    rejected = {"response_ancestry:101/A/AB/10000/paired/post_A",
                "response_ancestry:101/A/AB/10000/paired/post_B"}
    for reduction in reductions:
        assert training["training_id"] in reduction.trainings
        assert anchor["state_anchor_sha256"] in reduction.anchors
        row = reduction.rows["101/A/AB/10000"]["paired"]
        assert all(row[name]["parent_kind"] == "anchor" for name in ("post_A", "post_B"))
        assert reduction.status == "inconclusive"
        assert any(reason.startswith("missing_") for reason in reduction.reasons)
        assert not any(reason.startswith(("invalid_state_anchor:", "invalid_response:",
                                          "response_training:", "training_ancestry:"))
                       for reason in reduction.reasons)
    assert rejected <= set(reductions[0].reasons)
    assert not rejected & set(reductions[1].reasons)
    assert set(reductions[0].reasons) - rejected == set(reductions[1].reasons)


def test_native_prefix_shared_report_terminal_roundtrip(engine_factory, tmp_path):
    from fly_connectome_sim.experiment import analysis
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix, verify_replay_run

    recorder, frozen, training, anchor, root, target = _native_confirmation_prefix(engine_factory, tmp_path)
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    # RED reaches a genuinely recorded/replayed native confirmation before the missing API.
    assert hasattr(analysis, "assess_assay_prefix")
    report = analysis.assess_assay_prefix(prefix, frozen)
    assert prefix.verification_mode == "native-replay"
    assert report.status == "inconclusive"
    assert report.values["verification_mode"] == "native-replay"
    assert report.values["nonmaterialized_parents"] == [
        {"parent_sha256": anchor["state_anchor_sha256"], "parent_kind": "anchor"}]
    assert any(reason.startswith("missing_") for reason in report.reasons)
    assert not any(reason.startswith(("invalid_training:", "invalid_response:", "training_ancestry:",
                                     "response_ancestry:", "checkpoint_inventory", "terminal_result"))
                   for reason in report.reasons)
    reduced = reduce_assay_evidence(prefix.iter_events(), frozen,
                                   attested_state_anchors=prefix.replay_attested_state_anchors)
    assert training["training_id"] in reduced.trainings
    assert anchor["state_anchor_sha256"] in reduced.anchors
    assert set(reduced.rows["101/A/AB/10000"]["paired"]) == {"post_A", "post_B"}
    terminal = analysis.build_assay_result(prefix, frozen)
    assert set(terminal) == {"result_version", "analysis_version", "frozen_config_sha256", "status",
                             "reasons", "report", "report_sha256", "evidence_event_count",
                             "evidence_final_scientific_sha256"}
    assert terminal["evidence_event_count"] == prefix.scientific_prefix["event_count"]
    assert terminal["evidence_final_scientific_sha256"] == prefix.scientific_prefix["final_scientific_sha256"]
    recorder.append({"type": "assay_result", "branch_id": root, "sim_ms": target / 10, **terminal})
    recorder.close()
    sealed = verify_replay_run(recorder.path, engine_factory=engine_factory)
    assert sealed.verification_mode == "native-replay"
    assert analyze_assay(sealed, frozen).to_dict() == report.to_dict()
    ordinary = analyze_assay(verify_run(recorder.path), frozen)
    assert ordinary.values["verification_mode"] == "integrity-only"
    assert "response_ancestry:101/A/AB/10000/paired/post_A" in ordinary.reasons
    assert "terminal_result_mismatch" in ordinary.reasons
    assert ordinary.to_dict() != report.to_dict()


def test_ordinary_prefix_cannot_issue_native_terminal(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.analysis import assess_assay_prefix, build_assay_result

    recorder, frozen, _, _, _, _ = _native_confirmation_prefix(engine_factory, tmp_path)
    prefix = recorder.validate_prefix()
    report = assess_assay_prefix(prefix, frozen)
    assert report.values["verification_mode"] == "integrity-only"
    assert "response_ancestry:101/A/AB/10000/paired/post_A" in report.reasons
    with pytest.raises(AnalysisError, match="native_replay_required"):
        build_assay_result(prefix, frozen)
    with pytest.raises(TypeError):
        build_assay_result(prefix, frozen, attested_state_anchors=prefix.manifest["state_anchors"])


@pytest.mark.parametrize("target", ["source", "events"])
@pytest.mark.parametrize("boundary", ["prefix", "prefix-ordinary", "sealed-native", "sealed-ordinary"])
def test_report_generation_detects_mutation_during_scientific_assessment(
        engine_factory, tmp_path, monkeypatch, target, boundary):
    from fly_connectome_sim.experiment import analysis
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix, verify_replay_run

    recorder, frozen, _, _, root, tick = _native_confirmation_prefix(engine_factory, tmp_path)
    ordinary_prefix = recorder.validate_prefix()
    prefix = verify_replay_prefix(ordinary_prefix, engine_factory=engine_factory)
    if boundary.startswith("prefix"):
        value = prefix if boundary == "prefix" else ordinary_prefix
        consume = analysis.assess_assay_prefix
    else:
        recorder.append({"type": "assay_result", "branch_id": root, "sim_ms": tick / 10,
                         **analysis.build_assay_result(prefix, frozen)})
        recorder.close()
        value = (verify_replay_run(recorder.path, engine_factory=engine_factory)
                 if boundary == "sealed-native" else verify_run(recorder.path))
        consume = analyze_assay
    original = analysis._assess

    def mutate_after_reduction(*args, **kwargs):
        result = original(*args, **kwargs)
        path = (recorder.path / "checkpoints" / "training-end.npz" if target == "source"
                else recorder.path / "events.jsonl")
        raw = path.read_bytes()
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        return result

    monkeypatch.setattr(analysis, "_assess", mutate_after_reduction)
    with pytest.raises(AnalysisError, match="verified_run_changed"):
        consume(value, frozen)


@pytest.mark.parametrize("target", ["source", "events"])
def test_trusted_terminal_rejects_post_attestation_mutation(engine_factory, tmp_path, target):
    from fly_connectome_sim.experiment.analysis import build_assay_result
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix

    recorder, frozen, _, _, _, _ = _native_confirmation_prefix(engine_factory, tmp_path)
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    path = (recorder.path / "checkpoints" / "training-end.npz" if target == "source"
            else recorder.path / "events.jsonl")
    raw = path.read_bytes()
    path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(AnalysisError, match="verified_run_changed"):
        build_assay_result(prefix, frozen)


def test_timing_only_native_reports_keep_scientific_identity(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.analysis import assess_assay_prefix, build_assay_result
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix, verify_replay_run

    results = []
    for timing in (0.0, 1.25):
        location = tmp_path / str(timing)
        location.mkdir()
        recorder, frozen, _, anchor, root, tick = _native_confirmation_prefix(
            engine_factory, location, timing=timing)
        prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
        report = assess_assay_prefix(prefix, frozen)
        payload = build_assay_result(prefix, frozen)
        recorder.append({"type": "assay_result", "branch_id": root, "sim_ms": tick / 10, **payload})
        recorder.close()
        run = verify_replay_run(recorder.path, engine_factory=engine_factory)
        assert analyze_assay(run, frozen).to_dict() == report.to_dict()
        results.append((anchor, prefix, report.to_dict(), payload, run))
    first, second = results
    assert first[0]["replay_recipe_sha256"] == second[0]["replay_recipe_sha256"]
    assert first[0]["state_anchor_sha256"] == second[0]["state_anchor_sha256"]
    assert first[1].scientific_prefix == second[1].scientific_prefix
    assert first[2] == second[2]
    assert first[3] == second[3]
    assert first[1]._raw_sha256 != second[1]._raw_sha256
    assert first[1]._byte_length != second[1]._byte_length
    assert first[4].manifest["events_sha256"] != second[4].manifest["events_sha256"]
    assert first[4]._manifest_bytes != second[4]._manifest_bytes


@pytest.mark.parametrize("changes", [
    {"protocol_version": "unknown/v1"},
    {"candidate_identity": "other-candidate/v1"},
    {"mbon11_population_size": 2},
    {"assay_contract": {"analysis_version": "mbon11-causal-analysis/v1"}},
])
def test_native_prefix_provenance_mismatch_cannot_support(engine_factory, tmp_path, changes):
    from fly_connectome_sim.experiment.analysis import assess_assay_prefix, build_assay_result
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix, verify_replay_run

    recorder, frozen, _, _, root, tick = _native_confirmation_prefix(
        engine_factory, tmp_path, metadata_changes=changes)
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    report = assess_assay_prefix(prefix, frozen)
    assert report.status == "inconclusive"
    assert "manifest_provenance" in report.reasons
    payload = build_assay_result(prefix, frozen)
    recorder.append({"type": "assay_result", "branch_id": root, "sim_ms": tick / 10, **payload})
    recorder.close()
    assert analyze_assay(verify_replay_run(recorder.path, engine_factory=engine_factory), frozen).to_dict() \
        == report.to_dict()


def test_prefix_analysis_rejects_unknown_config_and_unvalidated_values(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.analysis import assess_assay_prefix, build_assay_result
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix

    recorder, frozen, _, _, _, _ = _native_confirmation_prefix(engine_factory, tmp_path)
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    for consume in (assess_assay_prefix, build_assay_result):
        with pytest.raises(AnalysisError, match="invalid_frozen_config"):
            consume(prefix, object())
        with pytest.raises(AnalysisError, match="unvalidated_prefix"):
            consume({"verification_mode": "native-replay"}, frozen)
        with pytest.raises(AnalysisError, match="unvalidated_prefix"):
            consume(FixtureRun(prefix.manifest, list(prefix.iter_events()),
                               prefix.replay_attested_state_anchors), frozen)


def test_real_nonconfirmation_zero_anchor_analysis_keeps_shared_mode_and_provenance(engine_factory, tmp_path):
    from fly_connectome_sim.experiment.recorder import verify_replay_run

    engine = engine_factory()
    frozen = _declared_native_frozen_config(engine)
    metadata = {"engine_identity": engine.identity(), "protocol_version": "pilot/v1",
                "stimulus_version": "associative-stimuli/v1", "family": "confirmation",
                "seeds": [101, 113], "factors": {},
                "input_sha256": sorted({digest for row in _input_hashes("confirmation").values()
                                          for digest in row.values()})}
    recorder = RunRecorder(tmp_path / "pilot-without-terminal", run_kind="pilot",
                           metadata=metadata, root_branch_id="root")
    snapshot = tmp_path / "actual-native.npz"
    engine.brain.checkpoint(snapshot)
    for name in ("brain-before.npz", "brain-after.npz"):
        recorder.ingest_checkpoint(name, snapshot, origin_branch_id="root")
        recorder.append({"type": "checkpoint", "branch_id": "root", "sim_ms": 0.0,
                         "checkpoint_name": name})
    recorder.close()
    ordinary = verify_run(recorder.path)
    native = verify_replay_run(recorder.path, engine_factory=engine_factory)
    assert native.replay_attested_state_anchors == frozenset()
    for run, mode in ((ordinary, "integrity-only"), (native, "native-replay")):
        report = analyze_assay(run, frozen)
        assert report.status == "inconclusive"
        assert "terminal_result_missing_or_ambiguous" in report.reasons
        assert report.values.get("verification_mode") == mode
        assert report.values["nonmaterialized_parents"] == []
        assert "manifest_provenance" in report.reasons
        assert any(reason.startswith("missing_") for reason in report.reasons)


@pytest.mark.parametrize("evidence_count", [10000, 10001])
def test_native_terminal_does_not_change_scientific_event_budget(engine_factory, tmp_path, evidence_count):
    from fly_connectome_sim.experiment.analysis import assess_assay_prefix, build_assay_result
    from fly_connectome_sim.experiment.recorder import verify_replay_prefix, verify_replay_run

    recorder, frozen, training, anchor, root, tick = _native_confirmation_prefix(engine_factory, tmp_path)
    initial_events = list(recorder.validate_prefix().iter_events())
    # Hand-counted route: four durable records, training branch/training/fork/anchor,
    # two response branches and two responses = 12 relevant scientific records.
    assert len([event for event in initial_events if event["type"] in {
        "checkpoint", "branch_start", "assay_training", "fork", "state_anchor", "assay_response"}]) == 12
    after = next(event for event in initial_events if event.get("checkpoint_name") == "brain-after.npz")
    for _ in range(evidence_count - 12):
        recorder.append({"type": "branch_start", "branch_id": root, "sim_ms": tick / 10})
    prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=engine_factory)
    report = assess_assay_prefix(prefix, frozen)
    assert report.status == "inconclusive"
    assert ("evidence_event_limit" in report.reasons) == (evidence_count == 10001)
    reduction = reduce_assay_evidence(prefix.iter_events(), frozen,
                                     attested_state_anchors=prefix.replay_attested_state_anchors)
    assert training["training_id"] in reduction.trainings
    assert anchor["state_anchor_sha256"] in reduction.anchors
    assert set(reduction.rows["101/A/AB/10000"]["paired"]) == {"post_A", "post_B"}
    payload = build_assay_result(prefix, frozen)
    assert payload["evidence_event_count"] == len(initial_events) + evidence_count - 12
    assert payload["evidence_final_scientific_sha256"] == prefix.scientific_prefix["final_scientific_sha256"]
    # A new terminal branch must not consume budget or introduce branch science.
    recorder.append({"type": "assay_result", "branch_id": "terminal-summary", "sim_ms": tick / 10,
                     "parent_branch_id": root, "parent_checkpoint_sha256": after["checkpoint_sha256"],
                     "parent_checkpoint_name": "brain-after.npz", "parent_checkpoint_sequence": after["sequence"],
                     **payload})
    recorder.close()
    sealed = verify_replay_run(recorder.path, engine_factory=engine_factory)
    final_reduction = reduce_assay_evidence(sealed.iter_events(), frozen,
                                           attested_state_anchors=sealed.replay_attested_state_anchors)
    assert final_reduction == reduction
    final = analyze_assay(sealed, frozen)
    assert "terminal_result_mismatch" not in final.reasons
    assert final.to_dict() == report.to_dict()


def test_arithmetic_terminal_exclusion_preserves_tail_sequence_and_exhaustion(engine_factory):
    """Pure stream arithmetic: a terminal does not introduce branch science."""
    frozen = _declared_native_frozen_config(engine_factory())
    exhausted = False

    def events():
        nonlocal exhausted
        yield _checkpoint("baseline.npz", H["before"], 0, "root")
        yield {"type": "assay_result", "branch_id": "child", "parent_branch_id": "alien",
               "parent_checkpoint_sha256": H["donor"]}
        yield _checkpoint("later.npz", H["after"], 0, "child", parent=("root", H["before"]))
        exhausted = True

    reduction = reduce_assay_evidence(events(), frozen)
    assert exhausted
    later = reduction.checkpoints[H["after"]][0]
    assert later["sequence"] == 2
    assert later["parent_branch_id"] == "root"
    assert later["parent_checkpoint_sha256"] == H["before"]
