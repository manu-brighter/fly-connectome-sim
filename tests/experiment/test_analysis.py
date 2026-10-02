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
from replay_helpers import engine_factory


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
    """VerifiedRun-shaped in-memory stream; integrity is tested by the recorder."""

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
    report = assess_assay_evidence(
        events, frozen, attested_state_anchors=run.replay_attested_state_anchors,
    )
    value = report.to_dict()
    digest = sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False).encode()).hexdigest()
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
    assert _report(FixtureRun(run.manifest, events, [H["memory_after"]]), frozen).status == "supported"
    anchor["durable_ancestor_checkpoint_sha256"] = H["memory_after"]
    assert _report(FixtureRun(run.manifest, events, [H["memory_after"]]), frozen).status == "inconclusive"


def test_attested_qualification_anchor_can_freeze():
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
        report = assess_assay_evidence(events, frozen)
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
            "evidence_event_count": recorder._chain.count,
            "evidence_final_scientific_sha256": recorder._chain.previous,
        })
    assert analyze_assay(verify_run(run_path), frozen).status == "supported"


def test_real_retention_attestation_authorizes_only_the_target_response_routes(engine_factory, tmp_path):
    """Retention-route integration; training descriptors are not reconstructed history."""
    from fly_connectome_sim.experiment.recorder import verify_replay_run
    from fly_connectome_sim.experiment.replay import (
        OPERATION_VERSION, build_black_retention_recipe, build_state_anchor,
    )

    producer = engine_factory()
    population = len(producer.groups.mbon11)
    # An explicit valid frozen contract, without a manufactured qualification run.
    data = {
        "version": "mbon11-frozen-assay/v1", "analysis_version": "mbon11-causal-analysis/v1",
        "qualification_version": "mbon11-qualification/v1", "aggregation": "raw-bin-mean-rate/v1",
        "qualification_artifact": {name: H["schema"] for name in (
            "schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256")},
        "qualification_family": "qualification", "qualification_seeds": [11, 23],
        "qualification_protocol_version": "qualification/v1",
        "confirmation_family": "confirmation", "confirmation_seeds": [101, 113],
        "confirmation_protocol_version": "associative-confirmation/v1",
        "stimulus_version": "associative-stimuli/v1", "engine_identity": producer.identity(),
        "qualification_input_sha256": sorted({digest for row in _input_hashes("qualification").values()
                                               for digest in row.values()}),
        "confirmation_input_sha256": _input_hashes("confirmation"),
        "candidate_identity": "kc-mbon11-ppl101/v1", "mbon11_population_size": population,
        "selected_configuration": CONFIGURATION, "response_window": WINDOW,
        "retention_ms": 10000, "retention_times_ms": [10000, 70000], "expected_effect_sign": 1,
        "conditions": list(CONDITIONS), "interventions": list(INTERVENTIONS), "exclusions": [],
        "replay_resolution_hz": 0.0, "max_abs_control_delta_hz": 0.0,
        "dynamic_range_hz": 0.0, "effect_floor_hz": 0.0,
        "one_spike_floor_hz": 1000 / (population * 100),
        "floor_sources": {"replay_resolution_hz": "selected_paired_T_and_T_plus_60",
                          "max_abs_control_delta_hz": "selected_nonpaired_controls_T_and_T_plus_60",
                          "dynamic_range_hz": "selected_paired_pre_A_minus_pre_B",
                          "one_spike_floor_hz": "selected_response_window_and_population"},
    }
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()).hexdigest()
    frozen = FrozenAssayConfig.from_dict(data)
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    black = {"generator": "black-rgb/v1", "input_shape": [32, 32, 3],
             "input_dtype": "uint8", "input_sha256": _rgb_input_sha256(frame)}
    metadata = {"engine_identity": producer.identity(), "protocol_version": "pilot/v1",
                "stimulus_version": "associative-stimuli/v1", "family": "confirmation",
                "seeds": [101, 113], "factors": {}, "black_input": black,
                "input_sha256": sorted({digest for row in _input_hashes("confirmation").values()
                                          for digest in row.values()})}
    training = _training("confirmation", 101, "A", "AB", "paired")
    root, branch, retained = "baseline", training["branch_id"], "retention"
    recorder = RunRecorder(tmp_path / "retained-route", run_kind="pilot", metadata=metadata,
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
