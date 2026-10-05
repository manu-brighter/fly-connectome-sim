"""Opt-in native acceptance of every declared confirmation factor in one run."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path

import numpy as np
import pytest

from replay_helpers import engine_factory, _declared_native_frozen_config
from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment import assay
from fly_connectome_sim.experiment.analysis import analyze_assay, reduce_assay_evidence
from fly_connectome_sim.experiment.stimuli import AssayStimuli


pytestmark = pytest.mark.skipif(
    os.getenv("FLY_CONNECTOME_SIM_FULL_TEST") != "1",
    reason="complete native assay factor matrix is opt-in",
)

_COHORTS = ((101, "A", "AB"), (113, "A", "AB"), (113, "B", "AB"), (101, "B", "AB"),
            (101, "B", "BA"), (113, "B", "BA"), (113, "A", "BA"), (101, "A", "BA"))
_CONDITIONS = ("paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired",
               "matched_reference", "necessity", "sufficiency", "sham")
_SOURCE_NAMES = ("training-end", "frozen_plasticity-training-end", "no_external_dan-training-end",
                 "temporally_unpaired-training-end", "matched-reference-training-end",
                 "necessity-post", "sufficiency-post", "sham-post")


def _factors(event):
    return event["seed"], event["paired_identity"], event["presentation_order"]


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def test_real_all_declared_controlled_cohorts(engine_factory, tmp_path, monkeypatch):
    frozen = _declared_native_frozen_config(engine_factory())
    config = frozen.to_dict()
    expected_factors = {(seed, identity, order) for seed in (101, 113)
                        for identity in ("A", "B") for order in ("AB", "BA")}
    assert set(_COHORTS) == expected_factors and len(_COHORTS) == 8
    assert config["confirmation_seeds"] == [101, 113]
    assert config["conditions"] == list(_CONDITIONS)
    assert config["retention_times_ms"] == [10000, 70000]
    black = np.zeros((32, 32, 3), dtype=np.uint8)
    black_hash = _rgb_input_sha256(black)
    input_frames = {}
    for seed in (101, 113):
        frames = {name: AssayStimuli(seed, "confirmation").frame(name) for name in ("A", "B", "C")}
        frames["black"] = black.copy()
        actual = {name: _rgb_input_sha256(frame) for name, frame in frames.items()}
        assert actual == config["confirmation_input_sha256"][str(seed)]
        assert np.array_equal(frames["black"], black)
        input_frames.update({actual[name]: frame for name, frame in frames.items()})
    assert {config["confirmation_input_sha256"][str(seed)]["black"] for seed in (101, 113)} == {black_hash}

    # Retain only restore paths and input sets, not engines or full native state traces.
    records, prefixes, sealed_runs, replay_counts = [], [], [], []
    replaying = False
    producer_count = None

    def tracked_factory():
        engine = engine_factory()
        if replaying:
            replay_counts[-1] += 1
            return engine
        record = {"restores": [], "inputs": set()}
        records.append(record)
        restore, observe = engine.brain.restore, engine.observe

        def tracked_restore(path):
            restore(path)
            record["restores"].append(Path(path).name)

        def tracked_observe(frame, duration, **kwargs):
            digest = _rgb_input_sha256(frame)
            assert digest in input_frames and np.array_equal(frame, input_frames[digest])
            observed = observe(frame, duration, **kwargs)
            assert observed["input_sha256"] == digest
            record["inputs"].add(digest)
            return observed

        engine.brain.restore, engine.observe = tracked_restore, tracked_observe
        return engine

    verify_prefix, verify_sealed = assay.verify_replay_prefix, assay.verify_replay_run

    def tracked_prefix(*args, **kwargs):
        nonlocal replaying, producer_count
        producer_count = len(records)
        replaying = True
        replay_counts.append(0)
        try:
            prefix = verify_prefix(*args, **kwargs)
        finally:
            replaying = False
        prefixes.append(prefix)
        return prefix

    def tracked_sealed(*args, **kwargs):
        nonlocal replaying
        replaying = True
        replay_counts.append(0)
        try:
            run = verify_sealed(*args, **kwargs)
        finally:
            replaying = False
        sealed_runs.append(run)
        return run

    monkeypatch.setattr(assay, "verify_replay_prefix", tracked_prefix)
    monkeypatch.setattr(assay, "verify_replay_run", tracked_sealed)
    path = tmp_path / "all-factors"
    report = assay.run_controlled_cohorts(tracked_factory, frozen, output_dir=path, cohorts=_COHORTS)
    assert len(prefixes) == len(sealed_runs) == 1
    assert producer_count == len(records) == 625
    assert all(count > 0 for count in replay_counts)
    assert Counter(tuple(r["restores"]) for r in records)[()] == 1
    assert all(len(r["restores"]) <= 1 for r in records)
    baseline_trials = [r for r in records if r["restores"] == ["baseline.npz"]]
    assert len(baseline_trials) == 64
    assert Counter(len(r["inputs"] - {black_hash}) for r in baseline_trials) == {1: 24, 2: 40}
    assert sum(r["restores"] == ["retained.npz"] for r in records) == 384

    run = sealed_runs[0]
    events = list(run.iter_events())
    by_type = {kind: [e for e in events if e["type"] == kind] for kind in (
        "assay_training", "assay_intervention", "assay_response", "state_anchor", "checkpoint")}
    trainings, interventions, responses = (by_type[kind] for kind in (
        "assay_training", "assay_intervention", "assay_response"))
    anchors, checkpoint_events = by_type["state_anchor"], by_type["checkpoint"]
    calls_by_branch = defaultdict(list)
    for event in events:
        if event["type"] in ("observe", "neutral_gap_chunk"):
            calls_by_branch[event["branch_id"]].append(event)
    checkpoints = run.manifest["checkpoints"]
    assert (len(trainings), len(interventions), len(responses), len(anchors), len(checkpoints)) == (40, 24, 768, 128, 67)
    assert len(checkpoint_events) == 67
    assert [e["sequence"] for e in events] == list(range(len(events)))
    starts = {e["branch_id"]: e for e in events if e["type"] in ("branch_start", "fork")}
    assert len(starts) == sum(e["type"] in ("branch_start", "fork") for e in events)
    assert len({e["training_id"] for e in trainings}) == 40
    assert len({e["intervention_id"] for e in interventions}) == 24
    assert len({a["anchor_id"] for a in anchors}) == 128
    assert set(checkpoints) == {"brain-before.npz", "baseline.npz", "brain-after.npz"} | {
        f"{seed}-{identity}-{order}-{name}.npz" for seed, identity, order in expected_factors for name in _SOURCE_NAMES}
    assert "retained.npz" not in checkpoints
    assert run.verification_mode == prefixes[0].verification_mode == "native-replay"
    assert run.replay_attested_state_anchors == prefixes[0].replay_attested_state_anchors == frozenset(
        a["state_anchor_sha256"] for a in anchors)
    assert set(run.manifest["state_anchors"]) == set(run.replay_attested_state_anchors)

    def occurrence(event):
        return {"checkpoint_name": event["checkpoint_name"], "checkpoint_sha256": event["checkpoint_sha256"],
                "origin_branch_id": event["branch_id"], "checkpoint_sequence": event["sequence"], "sim_tick": event["sim_tick"]}

    def assert_parent(event, source):
        assert event["parent_checkpoint_name"] == source["checkpoint_name"]
        assert event["parent_checkpoint_sequence"] == source["checkpoint_sequence"]
        assert event["parent_checkpoint_sha256"] == source["checkpoint_sha256"]
        assert event["parent_branch_id"] == source["origin_branch_id"]
        assert source["checkpoint_sequence"] < event["sequence"]

    source_by_branch = {e["branch_id"]: occurrence(e) for e in checkpoint_events if e["branch_id"] != "baseline"}
    baseline = occurrence(next(e for e in checkpoint_events if e["checkpoint_name"] == "baseline.npz"))
    source_engine = engine_factory()
    source_engine.identity()
    source_digests = {}
    for checkpoint in checkpoint_events:
        name = checkpoint["checkpoint_name"]
        inventory = checkpoints[name]
        assert inventory["checkpoint_sequence"] == checkpoint["sequence"]
        assert inventory["origin_branch_id"] == checkpoint["branch_id"]
        assert inventory["sim_tick"] == checkpoint["sim_tick"]
        assert inventory["sim_ms"] == checkpoint["sim_ms"] == checkpoint["sim_tick"] / 10
        assert inventory["sha256"] == checkpoint["checkpoint_sha256"] == sha256((path / "checkpoints" / name).read_bytes()).hexdigest()
        source_engine.brain.restore(path / "checkpoints" / name)
        assert source_engine.brain.cursor == checkpoint["sim_tick"]
        assert source_engine.brain.sim_ms == checkpoint["sim_tick"] / 10
        source_digests[name] = source_engine.brain.candidate_state_digests(source_engine.groups.mbon11)

    training_by_id = {t["training_id"]: t for t in trainings}
    routes = {}
    assert [_factors(t) for t in trainings[::5]] == list(_COHORTS)
    assert Counter((_factors(t), t["condition"]) for t in trainings) == {
        (factors, condition): 1 for factors in expected_factors for condition in _CONDITIONS[:5]}
    for training in trainings:
        factors, condition = _factors(training), training["condition"]
        assert training["training_id"] == training["branch_id"] == f"{condition}/{'/'.join(map(str, factors))}/training"
        source = source_by_branch[training["branch_id"]]
        assert source["checkpoint_name"] == f"{'-'.join(map(str, factors))}-{_SOURCE_NAMES[_CONDITIONS.index(condition)]}.npz"
        assert source["sim_tick"] == training["training_end_tick"]
        assert source["checkpoint_sha256"] == training["training_end_checkpoint_sha256"]
        assert source["checkpoint_sequence"] < training["sequence"]
        assert training["baseline_checkpoint_sha256"] == baseline["checkpoint_sha256"]
        assert training["baseline_tick"] == baseline["sim_tick"]
        assert_parent(starts[training["branch_id"]], baseline)
        assert_parent(events[source["checkpoint_sequence"]], baseline)
        assert source_digests[source["checkpoint_name"]] == {
            key: training[key] for key in ("candidate_memory_sha256", "noncandidate_state_sha256")}
        calls = calls_by_branch[training["branch_id"]]
        assert len(calls) == len(training["segments"])
        for segment, call in zip(training["segments"], calls):
            expected_hash = config["confirmation_input_sha256"][str(factors[0])][segment["stimulus"] or "black"]
            assert segment["input_sha256"] == expected_hash
            assert (call["start_tick"], call["end_tick"]) == (segment["start_tick"], segment["end_tick"])
            assert (call["telemetry"]["input_sha256"] if call["type"] == "observe" else call["input_sha256"]) == expected_hash
        routes[factors, condition] = training, source, None

    assert Counter((_factors(i), i["condition"]) for i in interventions) == {
        (factors, condition): 1 for factors in expected_factors for condition in _CONDITIONS[5:]}
    for intervention in interventions:
        factors, condition = _factors(intervention), intervention["condition"]
        assert intervention["intervention_id"] == intervention["branch_id"] == f"{condition}/{'/'.join(map(str, factors))}/intervention"
        for role, expected in (("donor", "matched_reference" if condition == "necessity" else "paired"),
                               ("recipient", "matched_reference" if condition == "sufficiency" else "paired")):
            training = training_by_id[intervention[f"{role}_training_id"]]
            source = source_by_branch[training["branch_id"]]
            assert _factors(training) == factors and training["condition"] == expected
            assert intervention[f"{role}_checkpoint_sha256"] == source["checkpoint_sha256"]
            assert intervention[f"{role}_training_end_tick"] == source["sim_tick"]
        recipient = training_by_id[intervention["recipient_training_id"]]
        recipient_source = source_by_branch[recipient["branch_id"]]
        donor = training_by_id[intervention["donor_training_id"]]
        assert intervention["donor_candidate_memory_sha256"] == donor["candidate_memory_sha256"]
        assert intervention["recipient_candidate_memory_before_sha256"] == recipient["candidate_memory_sha256"]
        assert intervention["recipient_candidate_memory_after_sha256"] == intervention["donor_candidate_memory_sha256"]
        assert intervention["noncandidate_state_before_sha256"] == intervention["noncandidate_state_after_sha256"] == recipient["noncandidate_state_sha256"]
        assert intervention["donor_training_end_tick"] == intervention["recipient_training_end_tick"]
        source = source_by_branch[intervention["branch_id"]]
        assert source["checkpoint_name"] == f"{'-'.join(map(str, factors))}-{condition}-post.npz"
        assert source["sim_tick"] == recipient_source["sim_tick"]
        assert source["checkpoint_sequence"] < intervention["sequence"]
        assert source["checkpoint_sha256"] == intervention["post_intervention_checkpoint_sha256"]
        assert_parent(intervention, recipient_source)
        assert_parent(starts[intervention["branch_id"]], recipient_source)
        assert_parent(events[source["checkpoint_sequence"]], recipient_source)
        assert source_digests[source["checkpoint_name"]] == {
            "candidate_memory_sha256": intervention["recipient_candidate_memory_after_sha256"],
            "noncandidate_state_sha256": intervention["noncandidate_state_after_sha256"]}
        routes[factors, condition] = recipient, source, intervention["intervention_id"]

    anchor_by_id = {a["anchor_id"]: a for a in anchors}
    expected_anchor_ids = set()
    for (factors, condition), (training, source, _) in routes.items():
        prefix = "/".join(map(str, factors)) + "/" + ("" if condition == "paired" else condition + "/")
        for retention in (10000, 70000):
            branch = f"{prefix}retention/{retention}"
            expected_anchor_ids.add(branch)
            anchor = anchor_by_id[branch]
            assert anchor["origin_branch_id"] == branch
            assert anchor["source_occurrence"] == source == anchor["recipe"]["source_occurrence"]
            assert anchor["durable_ancestor_checkpoint_sha256"] == source["checkpoint_sha256"]
            assert anchor["sim_tick"] == training["retention_reference_tick"] + retention * 10 - 1000
            assert source["checkpoint_sequence"] < anchor["sequence"]
            assert_parent(starts[branch], source)
            assert anchor["recipe"]["engine_identity"] == config["engine_identity"]
            assert anchor["recipe"]["black_input"] == {
                "generator": "black-rgb/v1", "input_shape": [32, 32, 3], "input_dtype": "uint8", "input_sha256": black_hash}
    assert set(anchor_by_id) == expected_anchor_ids

    assert Counter((_factors(r), r["retention_ms"], r["condition"], r["phase"], r["stimulus"]) for r in responses) == {
        (factors, retention, condition, phase, stimulus): 1 for factors in expected_factors
        for retention in (10000, 70000) for condition in _CONDITIONS
        for phase in ("pre", "post") for stimulus in ("A", "B", "C")}
    for response in responses:
        factors = _factors(response)
        training, source, intervention_id = routes[factors, response["condition"]]
        assert response["training_id"] == training["training_id"]
        assert response["intervention_id"] == intervention_id
        assert response["training_end_checkpoint_sha256"] == training["training_end_checkpoint_sha256"]
        assert response["retention_source_checkpoint_sha256"] == source["checkpoint_sha256"]
        assert response["input_sha256"] == config["confirmation_input_sha256"][str(factors[0])][response["stimulus"]]
        assert response["black_sha256"] == black_hash
        assert {e["telemetry"]["input_sha256"] for e in calls_by_branch[response["branch_id"]]} == {
            black_hash, response["input_sha256"]}
        assert response["passive_decay_ticks"] == training["retention_reference_tick"] + response["retention_ms"] * 10 - source["sim_tick"]
        prefix = "/".join(map(str, factors)) + "/"
        if response["phase"] == "pre":
            assert response["branch_id"] == f"{prefix}pre/{response['stimulus']}"
            assert_parent(response, baseline)
            assert_parent(starts[response["branch_id"]], baseline)
        else:
            prefix += "" if response["condition"] == "paired" else response["condition"] + "/"
            anchor = anchor_by_id[f"{prefix}retention/{response['retention_ms']}"]
            assert response["branch_id"] == f"{prefix}post/{response['retention_ms']}/{response['stimulus']}"
            assert response["parent_branch_id"] == anchor["origin_branch_id"]
            assert response["parent_state_anchor_sha256"] == anchor["state_anchor_sha256"]
            assert response["cs_onset_tick"] - 1000 == anchor["sim_tick"]
            assert anchor["sequence"] < response["sequence"]
            assert starts[response["branch_id"]]["parent_state_anchor_sha256"] == anchor["state_anchor_sha256"]

    reduction = reduce_assay_evidence(run.iter_events(), frozen,
                                     attested_state_anchors=run.replay_attested_state_anchors)
    expected_keys = {f"{seed}/{identity}/{order}/{retention}" for seed, identity, order in expected_factors
                     for retention in (10000, 70000)}
    assert reduction.status == "supported" and reduction.reasons == ()
    assert set(reduction.rows) == set(report.values["cells"]) == expected_keys
    for rows in reduction.rows.values():
        assert set(rows) == set(_CONDITIONS)
        assert all(set(row) == {f"{phase}_{stimulus}" for phase in ("pre", "post") for stimulus in ("A", "B", "C")}
                   for row in rows.values())
    assert report.status == "unsupported" and report.reasons
    scientific_gates = {"paired_effect", "control_frozen_plasticity", "control_no_external_dan",
                        "control_temporally_unpaired", "C_floor", "global_gain", "necessity_absolute",
                        "necessity_contrast", "necessity_reference", "sufficiency_absolute", "sufficiency_reference", "sham", "reciprocal"}
    assert all(reason.split(":", 1)[0] in scientific_gates for reason in report.reasons)
    assert report.values["verification_mode"] == "native-replay"
    assert report.values["nonmaterialized_parents"] == [
        {"parent_sha256": digest, "parent_kind": "anchor"} for digest in sorted(run.replay_attested_state_anchors)]
    assert sum(e["type"] == "assay_result" for e in events) == 1 and events[-1]["type"] == "assay_result"
    assert prefixes[0].scientific_prefix == {
        "event_count": len(events) - 1, "final_sequence": len(events) - 2,
        "final_scientific_sha256": events[-1]["previous_scientific_sha256"]}
    assert events[-1]["evidence_event_count"] == len(events) - 1
    assert events[-1]["evidence_final_scientific_sha256"] == events[-1]["previous_scientific_sha256"]
    assert events[-1]["scientific_sha256"] == run.manifest["final_scientific_sha256"]
    assert _canonical(report.to_dict()) == _canonical(analyze_assay(run, frozen).to_dict())
    assert _canonical(report.to_dict()) == _canonical(assay.assess_assay_prefix(prefixes[0], frozen).to_dict())
    assert _canonical(report.to_dict()) == _canonical(events[-1]["report"])
