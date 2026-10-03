"""Execute one bounded paired confirmation cohort with native retained parents."""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from ..engine import _rgb_input_sha256
from .analysis import (FrozenAssayConfig, AssayReport, _canonical, _training_plan,
                       assess_assay_prefix, build_assay_result, analyze_assay)
from .qualification import GridConfiguration, _training_timeline, _trial_segments, _split_intervals
from .recorder import RunRecorder, verify_replay_prefix, verify_replay_run
from .replay import OPERATION_VERSION, build_black_retention_recipe, build_state_anchor
from .stimuli import AssayStimuli


def _metadata(config, frozen, black):
    return {
        "family": "confirmation", "seeds": config["confirmation_seeds"],
        "factors": {"paired_identity": ["A", "B"], "presentation_order": ["AB", "BA"]},
        "protocol_version": config["confirmation_protocol_version"],
        "stimulus_version": config["stimulus_version"], "engine_identity": config["engine_identity"],
        "candidate_identity": config["candidate_identity"],
        "mbon11_population_size": config["mbon11_population_size"],
        "aggregation": config["aggregation"], "exclusions": config["exclusions"],
        "frozen_config_sha256": frozen.digest, "black_input": black,
        "confirmation_input_sha256": config["confirmation_input_sha256"],
        "input_sha256": sorted({v for row in config["confirmation_input_sha256"].values() for v in row.values()}),
        "assay_contract": {**{k: config[k] for k in ("selected_configuration", "response_window",
                            "retention_times_ms", "expected_effect_sign", "conditions", "interventions",
                            "analysis_version")}, "stimuli": ["A", "B", "C"]},
    }


def run_paired_cohort(engine_factory, frozen: FrozenAssayConfig, *, output_dir,
                      seed=101, paired_identity="A", presentation_order="AB") -> AssayReport:
    config = FrozenAssayConfig.from_dict(frozen.to_dict()).to_dict()
    if (type(seed) is not int or seed not in config["confirmation_seeds"]
            or paired_identity not in ("A", "B") or presentation_order not in ("AB", "BA")):
        raise ValueError("Undeclared cohort factors")
    frames = {name: AssayStimuli(seed, "confirmation").frame(name) for name in ("A", "B", "C")}
    frames["black"] = np.zeros((32, 32, 3), dtype=np.uint8)
    hashes = {name: _rgb_input_sha256(frame) for name, frame in frames.items()}
    if hashes != config["confirmation_input_sha256"][str(seed)]:
        raise ValueError("Actual input hashes disagree with frozen declaration")
    black = {"generator": "black-rgb/v1", "input_shape": [32, 32, 3],
             "input_dtype": "uint8", "input_sha256": hashes["black"]}

    def check(engine):
        for indices in vars(engine.groups).values():
            if (not isinstance(indices, np.ndarray) or indices.ndim != 1
                    or not np.issubdtype(indices.dtype, np.integer)):
                raise ValueError("Actual ordered neural groups must be integer vectors")
        groups = {name: [int(i) for i in indices] for name, indices in vars(engine.groups).items()}
        if engine.identity() != config["engine_identity"] or groups != config["engine_identity"]["neural_groups"]:
            raise ValueError("Actual engine identity/current groups disagree with frozen declaration")
        if len(engine.groups.mbon11) != config["mbon11_population_size"]:
            raise ValueError("Actual MBON11 population disagrees with frozen declaration")
        if (type(engine.brain.cursor) is not int or type(engine.brain.dt) is not float
                or engine.brain.dt != 0.1 or engine.brain.sim_ms != engine.brain.cursor * engine.brain.dt):
            raise ValueError("Actual engine clock mismatch")
        engine.brain.candidate_state_digests(engine.groups.mbon11)
        return engine

    def factory():
        return check(engine_factory())

    producer = factory()
    baseline_tick = producer.brain.cursor
    root = "baseline"
    training_branch = f"paired/{seed}/{paired_identity}/{presentation_order}/training"
    grid = GridConfiguration(**config["selected_configuration"])
    schedule, _, _, t0 = _training_timeline(grid, paired_identity, presentation_order, "paired", controls=True)
    plan = _training_plan(config, seed, paired_identity, presentation_order, "paired", "confirmation", baseline_tick)
    anchor_targets = tuple(plan["retention_reference_tick"] + round(retention * 10) - 1000
                           for retention in config["retention_times_ms"])
    if any(target < plan["training_end_tick"] for target in anchor_targets):
        raise ValueError("Retained anchor precedes training-end source")
    with TemporaryDirectory(prefix="paired-cohort-") as temporary:
        scratch = Path(temporary)
        with RunRecorder(output_dir, run_kind="confirmation", metadata=_metadata(config, frozen, black),
                         root_branch_id=root) as recorder:
            sequence = 0

            def append(event):
                nonlocal sequence
                recorder.append(event)
                sequence += 1

            def durable(engine, name, branch, parent=None):
                engine.brain.checkpoint(scratch / name)
                digest = recorder.ingest_checkpoint(name, scratch / name, origin_branch_id=branch)
                occurrence = {"checkpoint_name": name, "checkpoint_sha256": digest,
                              "origin_branch_id": branch, "checkpoint_sequence": sequence,
                              "sim_tick": engine.brain.cursor}
                append({"type": "checkpoint", "branch_id": branch, "sim_tick": engine.brain.cursor,
                        "sim_ms": engine.brain.cursor / 10, "checkpoint_name": name, **(parent or {})})
                return occurrence

            def parent(occ):
                return {"parent_branch_id": occ["origin_branch_id"],
                        "parent_checkpoint_name": occ["checkpoint_name"],
                        "parent_checkpoint_sequence": occ["checkpoint_sequence"],
                        "parent_checkpoint_sha256": occ["checkpoint_sha256"]}

            def restore(occ):
                engine = factory()
                engine.brain.restore(Path(output_dir) / "checkpoints" / occ["checkpoint_name"])
                check(engine)
                if engine.brain.cursor != occ["sim_tick"]:
                    raise ValueError("Restored occurrence clock mismatch")
                return engine

            def call(engine, branch, ticks, stimulus=None, stimulation=None, learning=False, compact=False):
                if engine.brain.weights_frozen:
                    append({"type": "replay_thaw", "branch_id": branch, "operation_version": OPERATION_VERSION,
                            "sim_tick": engine.brain.cursor, "sim_ms": engine.brain.cursor / 10,
                            "before_weights_frozen": True, "after_weights_frozen": False})
                    engine.brain.weights_frozen = False
                start = engine.brain.cursor
                observed = engine.observe(frames[stimulus or "black"], ticks / 10,
                                          stimulation=stimulation, learning=learning)
                check(engine)
                if engine.brain.cursor != start + ticks or observed["sim_ms"] != round(engine.brain.sim_ms, 3):
                    raise ValueError("Observed call clock mismatch")
                if engine.brain.weights_frozen:
                    raise ValueError("Unexpected frozen weights")
                event = {"type": "neutral_gap_chunk" if compact else "observe", "branch_id": branch,
                         "operation_version": OPERATION_VERSION, "start_tick": start,
                         "end_tick": engine.brain.cursor, "duration_ticks": ticks, "duration_ms": ticks / 10,
                         "sim_ms": engine.brain.cursor / 10, "stimulation": stimulation, "learning": learning,
                         "current_mv": 20.0, "pathway_detail": False, "qualification_detail": False}
                if compact:
                    event.update(black)
                else:
                    event["telemetry"] = observed
                append(event)
                return observed

            durable(producer, "brain-before.npz", root)
            baseline = durable(producer, "baseline.npz", root)
            append({"type": "branch_start", "branch_id": training_branch,
                    "sim_ms": producer.brain.cursor / 10, **parent(baseline)})
            rows = []
            for segment in schedule:
                start = producer.brain.cursor
                learning = segment.start_ms < t0 and bool(segment.stimulus or segment.stimulation)
                call(producer, training_branch, round((segment.end_ms - segment.start_ms) * 10),
                     segment.stimulus, segment.stimulation, learning,
                     compact=not segment.stimulus and not segment.stimulation)
                rows.append({"start_tick": start, "end_tick": producer.brain.cursor,
                             "stimulus": segment.stimulus, "external_stimulation": segment.stimulation,
                             "learning": learning, "current_mv": 20.0 if segment.stimulation else None,
                             "input_sha256": hashes[segment.stimulus or "black"]})
            exposure = {name: sum(row["end_tick"] - row["start_tick"] for row in rows
                                  if row["stimulus"] == name) for name in ("A", "B", "C")}
            if rows != plan["segments"] or exposure != plan["training_visual_exposure_ticks"]:
                raise ValueError("Executed training disagrees with declared schedule")
            plan = {**plan, "segments": rows, "training_visual_exposure_ticks": exposure}
            source = durable(producer, "training-end.npz", training_branch, parent(baseline))
            training = {"type": "assay_training", "training_version": "associative-training/v1",
                        "training_id": training_branch, "branch_id": training_branch, "seed": seed,
                        "paired_identity": paired_identity, "presentation_order": presentation_order,
                        "condition": "paired", "candidate_identity": config["candidate_identity"],
                        "baseline_tick": baseline_tick, "baseline_checkpoint_sha256": baseline["checkpoint_sha256"],
                        "training_end_checkpoint_sha256": source["checkpoint_sha256"], **plan,
                        **producer.brain.candidate_state_digests(producer.groups.mbon11),
                        "sim_ms": producer.brain.cursor / 10}
            append(training)

            def trial(engine, branch, binding, phase, stimulus, onset, retentions):
                append({"type": "branch_start", "branch_id": branch, "sim_ms": engine.brain.cursor / 10, **binding})
                measured = []
                trial_schedule = _trial_segments(grid, stimulus, paired=False)
                stop = onset + round(config["response_window"]["end_ms"] * 10)
                # Preserve the shared trial timeline while splitting at the declared window stop.
                for segment in trial_schedule:
                    a, b = onset + round(segment.start_ms * 10), onset + round(segment.end_ms * 10)
                    pieces = _split_intervals(a / 10, b / 10,
                                             ((a / 10, b / 10, stimulus),) if segment.stimulus else (),
                                             None, extra_cuts=(stop / 10,))
                    for part in pieces:
                        observed = call(engine, branch, round((part.end_ms - part.start_ms) * 10), part.stimulus)
                        measured.extend(observed["bins"])
                        if engine.brain.cursor == stop:
                            window_start = onset + round(config["response_window"]["start_ms"] * 10)
                            bins = [{"start_tick": round(item["end_ms"] * 10) - round(item["duration_ms"] * 10),
                                     "end_tick": round(item["end_ms"] * 10), "spikes": item["group_spikes"]["mbon11"]}
                                    for item in measured if window_start < round(item["end_ms"] * 10) <= stop]
                            population = len(engine.groups.mbon11)
                            duration = (stop - window_start) / 10
                            shared = {k: training[k] for k in ("training_id", "association_t0_tick", "retention_reference_tick",
                                "training_start_tick", "training_end_tick", "last_visual_end_tick", "last_external_dan_end_tick",
                                "unpaired_nearest_cs_boundary_ticks", "training_visual_exposure_ticks", "training_end_checkpoint_sha256")}
                            for retention in retentions:
                                append({"type": "assay_response", "branch_id": branch, **binding, **shared,
                                        "evidence_version": "mbon11-response/v1", "seed": seed,
                                        "paired_identity": paired_identity, "presentation_order": presentation_order,
                                        "retention_ms": retention, "condition": "paired", "phase": phase, "stimulus": stimulus,
                                        "candidate_identity": config["candidate_identity"], "population": "mbon11",
                                        "population_size": population, "cs_onset_tick": onset, "bins": bins,
                                        "rate_hz": sum(item["spikes"] for item in bins) * 1000 / (population * duration),
                                        "one_spike_rate_hz": 1000 / (population * duration),
                                        "retention_source_checkpoint_sha256": source["checkpoint_sha256"],
                                        "passive_decay_ticks": plan["retention_reference_tick"] + round(retention * 10) - source["sim_tick"],
                                        "input_sha256": hashes[stimulus], "black_sha256": hashes["black"],
                                        "endogenous_dan_spikes": sum(item["group_spikes"]["ppl101"] for item in measured),
                                        "learning": False, "external_stimulation": None, "intervention_id": None,
                                        "response_replay_resolution_hz": config["replay_resolution_hz"], "sim_ms": engine.brain.cursor / 10})

            for stimulus in ("A", "B", "C"):
                trial(restore(baseline), f"pre/{stimulus}", parent(baseline), "pre", stimulus,
                      baseline_tick + 1000, config["retention_times_ms"])
            for retention in config["retention_times_ms"]:
                retained = restore(source)
                branch = f"retention/{retention}"
                append({"type": "fork", "operation_version": OPERATION_VERSION, "branch_id": branch,
                        "sim_tick": retained.brain.cursor, "sim_ms": retained.brain.cursor / 10, **parent(source)})
                onset = plan["retention_reference_tick"] + round(retention * 10)
                target = onset - 1000
                while retained.brain.cursor < target:
                    call(retained, branch, min(5000, target - retained.brain.cursor), compact=True)
                prefix = recorder.validate_prefix()
                recipe = build_black_retention_recipe(prefix.iter_events(), source_occurrence=source,
                    origin_branch_id=branch, target_tick=target, engine_identity=retained.identity(),
                    run_metadata_sha256=prefix.manifest["run_metadata_sha256"], black_input=black,
                    scientific_prefix=prefix.scientific_prefix)
                anchor = build_state_anchor(anchor_id=branch, recipe=recipe,
                                            complete_state_sha256=retained.brain.checkpoint_state_sha256())
                recorder.append_state_anchor(anchor)
                sequence += 1
                retained.brain.checkpoint(scratch / "retained.npz")
                for stimulus in ("A", "B", "C"):
                    sibling = factory()
                    sibling.brain.restore(scratch / "retained.npz")
                    check(sibling)
                    if sibling.brain.cursor != target or sibling.brain.checkpoint_state_sha256() != anchor["complete_state_sha256"]:
                        raise ValueError("Retained sibling state mismatch")
                    trial(sibling, f"post/{retention}/{stimulus}",
                          {"parent_branch_id": branch, "parent_state_anchor_sha256": anchor["state_anchor_sha256"]},
                          "post", stimulus, onset, [retention])
                (scratch / "retained.npz").unlink()
            durable(producer, "brain-after.npz", root)
            prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=factory)
            report = assess_assay_prefix(prefix, frozen)
            payload = build_assay_result(prefix, frozen)
            if _canonical(report.to_dict()) != _canonical(payload["report"]):
                raise ValueError("Prefix terminal report mismatch")
            append({"type": "assay_result", "branch_id": root, "sim_ms": producer.brain.cursor / 10, **payload})
        sealed = verify_replay_run(recorder.path, engine_factory=factory)
        independent = analyze_assay(sealed, frozen)
        if (_canonical(independent.to_dict()) != _canonical(report.to_dict())
                or _canonical(independent.to_dict()) != _canonical(payload["report"])):
            raise ValueError("Independent sealed report mismatch")
        return independent
