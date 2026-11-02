"""Produce bounded selected cohorts with native retained parents."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from ..engine import _rgb_input_sha256
from .analysis import (CONDITIONS, ORDINARY_CONDITIONS, FrozenAssayConfig, AssayReport, _canonical, _training_plan,
                       assess_assay_prefix, build_assay_result, analyze_assay, _valid_engine_identity, _number)
from .qualification import (GRID, RESPONSE_WINDOWS, RETENTION_CANDIDATES_MS, QUALIFICATION_SEEDS,
                            CONFIRMATION_SEEDS, GridConfiguration, _training_timeline, _trial_segments,
                            _split_intervals, _response_rate)
from .recorder import RunRecorder, _digest_file, verify_replay_prefix, verify_replay_run
from .replay import OPERATION_VERSION, build_black_retention_recipe, build_state_anchor
from .stimuli import AssayStimuli


def _check_engine(engine, identity, population):
    for indices in vars(engine.groups).values():
        if (type(indices) is not np.ndarray or indices.ndim != 1
                or not np.issubdtype(indices.dtype, np.integer)):
            raise ValueError("Actual ordered neural groups must be integer vectors")
    groups = {name: [int(i) for i in indices] for name, indices in vars(engine.groups).items()}
    if _canonical(engine.identity()) != _canonical(identity) or groups != identity["neural_groups"]:
        raise ValueError("Actual engine identity/current groups disagree with frozen declaration")
    if len(engine.groups.mbon11) != population:
        raise ValueError("Actual MBON11 population disagrees with frozen declaration")
    if (type(engine.brain.cursor) is not int or type(engine.brain.dt) is not float
            or engine.brain.dt != 0.1 or engine.brain.sim_ms != engine.brain.cursor * engine.brain.dt):
        raise ValueError("Actual engine clock mismatch")
    engine.brain.candidate_state_digests(engine.groups.mbon11)
    return engine


def _authenticate_occurrence(prefix, occurrence, checkpoint_type, training=None, family="confirmation"):
    """Drain a fixed prefix, retaining only its exact occurrence and descriptor."""
    if (type(occurrence) is not dict or set(occurrence) != {"checkpoint_name", "checkpoint_sha256",
            "origin_branch_id", "checkpoint_sequence", "sim_tick"}
            or any(type(occurrence[key]) is not str or not occurrence[key]
                   for key in ("checkpoint_name", "checkpoint_sha256", "origin_branch_id"))
            or type(occurrence["checkpoint_sequence"]) is not int or occurrence["checkpoint_sequence"] < 0
            or type(occurrence["sim_tick"]) is not int or occurrence["sim_tick"] < 0):
        raise ValueError("Invalid exact source occurrence")
    inventory = prefix.manifest["checkpoints"].get(occurrence["checkpoint_name"])
    index = occurrence["checkpoint_sequence"]
    expected = {"sha256": occurrence["checkpoint_sha256"],
                "origin_branch_id": occurrence["origin_branch_id"],
                "checkpoint_sequence": index, "sim_tick": occurrence["sim_tick"],
                "sim_ms": occurrence["sim_tick"] / 10}
    matched, recorded, matches = None, None, 0
    training_type = "qualification_training" if family == "qualification" else "assay_training"
    for event in prefix.iter_events():
        if event["sequence"] == index:
            matched = {key: event.get(key) for key in ("type", "checkpoint_name", "checkpoint_sha256",
                                                       "branch_id", "sim_tick", "sim_ms")}
        if training is not None and event["type"] == training_type and event.get("training_id") == training["training_id"]:
            matches += 1
            recorded = {key: event.get(key) for key in training}
    if inventory is None or any(inventory.get(key) != value for key, value in expected.items()):
        raise ValueError("Source occurrence does not match authenticated inventory")
    if matched != {"type": checkpoint_type, "checkpoint_name": occurrence["checkpoint_name"],
                   "checkpoint_sha256": occurrence["checkpoint_sha256"],
                   "branch_id": occurrence["origin_branch_id"], "sim_tick": occurrence["sim_tick"],
                   "sim_ms": expected["sim_ms"]}:
        raise ValueError("Source occurrence does not match authenticated event")
    if training is not None and (matches != 1 or _canonical(recorded) != _canonical(training)
            or training["training_end_checkpoint_sha256"] != occurrence["checkpoint_sha256"]
            or training["training_end_tick"] != occurrence["sim_tick"]
            or training["branch_id"] != occurrence["origin_branch_id"]):
        raise ValueError("Training source descriptor does not match authenticated occurrence")
    return inventory


def _restore_training_source(recorder, occurrence, training, factory, identity, population, *, family="confirmation"):
    """Authenticate a precise durable training occurrence before native restore."""
    prefix = recorder.validate_prefix()
    inventory = _authenticate_occurrence(prefix, occurrence, "checkpoint", training, family)
    if _canonical(prefix.manifest["metadata"]["engine_identity"]) != _canonical(identity):
        raise ValueError("Training source descriptor engine identity mismatch")
    path = prefix.path / "checkpoints" / occurrence["checkpoint_name"]
    engine = _check_engine(factory(), identity, population)
    if _digest_file(path) != (inventory["sha256"], inventory["size"]):
        raise ValueError("Training source bytes changed before restore")
    engine.brain.restore(path)
    _check_engine(engine, identity, population)
    if (engine.brain.cursor != training["training_end_tick"]
            or engine.brain.sim_ms != training["training_end_tick"] * engine.brain.dt
            or engine.brain.candidate_state_digests(engine.groups.mbon11)
            != {key: training[key] for key in ("candidate_memory_sha256", "noncandidate_state_sha256")}):
        raise ValueError("Actual restored training source state mismatch")
    return engine


def _replace_candidate_state(donor, recipient, donor_training, recipient_training, identity, population):
    """Validate quiescent native sources and bracket only the candidate replacement."""
    for engine, training in ((donor, donor_training), (recipient, recipient_training)):
        _check_engine(engine, identity, population)
        if (engine.brain.cursor != training["training_end_tick"]
                or engine.brain.candidate_state_digests(engine.groups.mbon11)
                != {k: training[k] for k in ("candidate_memory_sha256", "noncandidate_state_sha256")}):
            raise ValueError("Actual training source state/clock mismatch")
    if (donor.brain.cursor != recipient.brain.cursor or donor.brain.sim_ms != recipient.brain.sim_ms
            or donor.brain.dt != recipient.brain.dt):
        raise ValueError("Donor and recipient training clocks differ")
    targets = donor.groups.mbon11
    donor_positions = donor.brain._candidate_positions(targets)
    recipient_positions = recipient.brain._candidate_positions(recipient.groups.mbon11)
    donor_edges = donor.brain.circuit["edges"][donor_positions]
    recipient_edges = recipient.brain.circuit["edges"][recipient_positions]
    if (not np.array_equal(targets, recipient.groups.mbon11)
            or not np.array_equal(donor_positions, recipient_positions)
            or not np.array_equal(donor_edges, recipient_edges)):
        raise ValueError("Actual candidate target/position/edge maps differ")
    donor_digests = donor.brain.candidate_state_digests(targets)
    snapshot = donor.brain.candidate_memory(targets)
    actual = {"memory_u": donor.brain.memory_u[donor_positions],
              "memory_w": donor.brain.memory_w[donor_positions], "weight": donor.brain.weight[donor_edges]}
    if (type(snapshot.cursor) is not int or type(snapshot.sim_ms) is not float
            or snapshot.cursor != donor.brain.cursor or snapshot.sim_ms != donor.brain.sim_ms
            or not np.array_equal(snapshot.target_indices, targets)
            or not np.array_equal(snapshot.edge_indices, donor_edges)
            or any(type(getattr(snapshot, name)) is not np.ndarray
                   or getattr(snapshot, name).dtype != value.dtype
                   or getattr(snapshot, name).shape != value.shape
                   or not np.array_equal(getattr(snapshot, name).view(np.uint8), value.view(np.uint8))
                   for name, value in actual.items())):
        raise ValueError("Captured candidate snapshot differs from actual donor source")
    before = recipient.brain.candidate_state_digests(recipient.groups.mbon11)
    recipient.brain.replace_candidate_memory(snapshot)
    after = recipient.brain.candidate_state_digests(recipient.groups.mbon11)
    if (before["noncandidate_state_sha256"] != after["noncandidate_state_sha256"]
            or after["candidate_memory_sha256"] != donor_digests["candidate_memory_sha256"]):
        raise ValueError("Candidate replacement changed noncandidate state or missed donor content")
    return {"donor_candidate_memory_sha256": donor_digests["candidate_memory_sha256"],
            "recipient_candidate_memory_before_sha256": before["candidate_memory_sha256"],
            "recipient_candidate_memory_after_sha256": after["candidate_memory_sha256"],
            "noncandidate_state_before_sha256": before["noncandidate_state_sha256"],
            "noncandidate_state_after_sha256": after["noncandidate_state_sha256"]}


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
    return _run_cohort(engine_factory, frozen, output_dir=output_dir, seed=seed,
                       paired_identity=paired_identity, presentation_order=presentation_order,
                       conditions=("paired",))


def run_intervention_cohort(engine_factory, frozen: FrozenAssayConfig, *, output_dir,
                            seed=101, paired_identity="A", presentation_order="AB") -> AssayReport:
    return _run_cohort(engine_factory, frozen, output_dir=output_dir, seed=seed,
                       paired_identity=paired_identity, presentation_order=presentation_order,
                       conditions=("paired", "matched_reference", "necessity", "sufficiency", "sham"))


def run_controlled_cohort(engine_factory, frozen: FrozenAssayConfig, *, output_dir,
                          seed=101, paired_identity="A", presentation_order="AB") -> AssayReport:
    return _run_cohort(engine_factory, frozen, output_dir=output_dir, seed=seed,
                       paired_identity=paired_identity, presentation_order=presentation_order,
                       conditions=CONDITIONS)


def run_controlled_cohorts(engine_factory, frozen: FrozenAssayConfig, *, output_dir,
                           cohorts) -> AssayReport:
    return _run_cohorts(engine_factory, frozen, output_dir=output_dir,
                        cohorts=cohorts, conditions=CONDITIONS, namespace=True)


def _run_cohort(engine_factory, frozen, *, output_dir, seed, paired_identity, presentation_order, conditions):
    return _run_cohorts(engine_factory, frozen, output_dir=output_dir,
                        cohorts=((seed, paired_identity, presentation_order),),
                        conditions=conditions, namespace=False)


def _execution_declarations(execution, cohorts, conditions, namespace):
    fields = {"family", "seeds", "engine_identity", "mbon11_population_size", "candidate_identity",
              "selected_configuration", "response_window", "retention_times_ms", "input_sha256"}
    if type(execution) is not dict or set(execution) != fields:
        raise ValueError("Invalid plain execution declaration fields")
    config = deepcopy(execution)
    family = config["family"]
    if type(family) is not str or family not in ("qualification", "confirmation"):
        raise ValueError("Invalid execution family")
    seeds = QUALIFICATION_SEEDS if family == "qualification" else CONFIRMATION_SEEDS
    if (type(config["seeds"]) not in (list, tuple)
            or any(type(seed) is not int for seed in config["seeds"]) or tuple(config["seeds"]) != seeds):
        raise ValueError("Invalid declared family seeds")
    config["seeds"] = list(seeds)
    population = config["mbon11_population_size"]
    if (type(population) is not int or population < 1
            or not _valid_engine_identity(config["engine_identity"], population)
            or config["candidate_identity"] != "kc-mbon11-ppl101/v1"):
        raise ValueError("Invalid execution identity, population or candidate convention")
    for key, values, expected in (
        ("selected_configuration", GRID, {"cs_duration_ms", "dan_onset_ms", "post_pair_gap_ms"}),
        ("response_window", RESPONSE_WINDOWS, {"start_ms", "end_ms"}),
    ):
        value = config[key]
        if (type(value) is not dict or set(value) != expected
                or any(not _number(item) for item in value.values()) or value not in [vars(item) for item in values]):
            raise ValueError("Invalid execution timing or response window")
    retentions = config["retention_times_ms"]
    if (type(retentions) is not list or len(retentions) != 2
            or any(type(value) is not int for value in retentions)
            or retentions[0] not in RETENTION_CANDIDATES_MS or retentions[1] != retentions[0] + 60000):
        raise ValueError("Invalid selected retention times")
    if (type(conditions) not in (tuple, list) or not conditions
            or any(type(condition) is not str for condition in conditions)
            or tuple(conditions) != tuple(condition for condition in CONDITIONS if condition in conditions)
            or "paired" not in conditions
            or (any(condition in conditions for condition in ("necessity", "sufficiency"))
                and "matched_reference" not in conditions)):
        raise ValueError("Invalid canonical conditions or intervention dependencies")
    if type(cohorts) not in (list, tuple) or not cohorts or len(cohorts) > 8:
        raise ValueError("Invalid bounded cohort request")
    declared = []
    for cohort in cohorts:
        if (type(cohort) not in (list, tuple) or len(cohort) != 3
                or type(cohort[0]) is not int or cohort[0] not in seeds
                or type(cohort[1]) is not str or cohort[1] not in ("A", "B")
                or type(cohort[2]) is not str or cohort[2] not in ("AB", "BA")):
            raise ValueError("Undeclared or malformed cohort factors")
        factors = tuple(cohort)
        if factors in declared:
            raise ValueError("Duplicate cohort factors")
        declared.append(factors)
    if (type(namespace) is not bool or (not namespace and len(declared) != 1)
            or (family == "qualification" and not namespace)):
        raise ValueError("Invalid selected namespace")
    inputs, actual = {}, {}
    for seed in seeds:
        frames = {name: AssayStimuli(seed, family).frame(name) for name in ("A", "B", "C")}
        frames["black"] = np.zeros((32, 32, 3), dtype=np.uint8)
        hashes = {name: _rgb_input_sha256(frame) for name, frame in frames.items()}
        inputs[seed] = frames, hashes
        actual[str(seed)] = hashes
    if (type(config["input_sha256"]) is not dict
            or _canonical(config["input_sha256"]) != _canonical(actual)):
        raise ValueError("Actual input hashes disagree with execution declaration")
    black = {"generator": "black-rgb/v1", "input_shape": [32, 32, 3],
             "input_dtype": "uint8", "input_sha256": actual[str(seeds[0])]["black"]}
    return config, tuple(declared), inputs, black


def _cohort_plans(config, declared, conditions, baseline_tick):
    plans = {}
    declaration = {**config, "confirmation_input_sha256": config["input_sha256"]}
    for seed, paired, order in declared:
        selected = {condition: _training_plan(declaration, seed, paired, order, condition,
                                             config["family"], baseline_tick)
                    for condition in conditions if condition in ORDINARY_CONDITIONS}
        if any(plan["retention_reference_tick"] + retention * 10 - 1000 < plan["training_end_tick"]
               for plan in selected.values() for retention in config["retention_times_ms"]):
            raise ValueError("Retained anchor precedes training-end source")
        plans[seed, paired, order] = selected
    return plans


def _matching_metadata(manifest, config, black):
    metadata = manifest["metadata"]
    family = config["family"]
    expected_inputs = (metadata.get("confirmation_input_sha256") if family == "confirmation" else {
        seed: {**values, "black": metadata.get("rgb_input_sha256", {}).get("black")}
        for seed, values in metadata.get("rgb_input_sha256", {}).get("stimuli", {}).items()
    })
    if (manifest["run_kind"] != family or metadata.get("family") != family
            or _canonical(metadata.get("seeds")) != _canonical(config["seeds"])
            or _canonical(metadata.get("engine_identity")) != _canonical(config["engine_identity"])
            or type(metadata.get("mbon11_population_size")) is not int
            or metadata.get("mbon11_population_size") != config["mbon11_population_size"]
            or metadata.get("candidate_identity") != config["candidate_identity"]
            or _canonical(metadata.get("black_input")) != _canonical(black)
            or _canonical(expected_inputs) != _canonical(config["input_sha256"])
            or metadata.get("input_sha256") != sorted({value for row in config["input_sha256"].values()
                                                      for value in row.values()})):
        raise ValueError("Caller recorder metadata disagrees with selected execution")


def _cohort_names(family, seed, paired, order, namespace):
    if family == "qualification":
        return f"selected/{seed}/{paired}/{order}/", f"selected-{seed}-{paired}-{order}-"
    return (f"{seed}/{paired}/{order}/", f"{seed}-{paired}-{order}-") if namespace else ("", "")


def _selected_branch(family, seed, paired, order, condition, role):
    if family == "qualification":
        return f"selected/{seed}/{paired}/{order}/{condition}/{role}"
    return f"{condition}/{seed}/{paired}/{order}/{role}"


def _reserve_names(prefix, config, declared, conditions, namespace):
    branches, checkpoints = set(), set()
    for seed, paired, order in declared:
        cohort, checkpoint = _cohort_names(config["family"], seed, paired, order, namespace)
        branches.update(f"{cohort}pre/{stimulus}" for stimulus in ("A", "B", "C"))
        for condition in conditions:
            ordinary = condition in ORDINARY_CONDITIONS
            branches.add(_selected_branch(config["family"], seed, paired, order, condition,
                                          "training" if ordinary else "intervention"))
            name = ({"paired": "training-end", "matched_reference": "matched-reference-training-end"}.get(
                condition, f"{condition}-training-end") if ordinary else f"{condition}-post")
            checkpoints.add(f"{checkpoint}{name}.npz")
            responses = cohort + ("" if condition == "paired" else condition + "/")
            for retention in config["retention_times_ms"]:
                branches.add(f"{responses}retention/{retention}")
                branches.update(f"{responses}post/{retention}/{stimulus}" for stimulus in ("A", "B", "C"))
    collision = bool(checkpoints & prefix.manifest["checkpoints"].keys())
    for event in prefix.iter_events():
        collision |= event["branch_id"] in branches or event.get("anchor_id") in branches
    if collision:
        raise ValueError("Selected branch or checkpoint name collides with existing prefix")


def _run_cohorts(engine_factory, frozen, *, output_dir, cohorts, conditions, namespace):
    config = FrozenAssayConfig.from_dict(frozen.to_dict()).to_dict()
    execution = {key: config[key] for key in ("engine_identity", "mbon11_population_size",
        "candidate_identity", "selected_configuration", "response_window", "retention_times_ms")}
    execution.update(family="confirmation", seeds=config["confirmation_seeds"],
                     input_sha256=config["confirmation_input_sha256"])
    execution, declared, inputs, black = _execution_declarations(execution, cohorts, conditions, namespace)
    producer = _check_engine(engine_factory(), execution["engine_identity"], execution["mbon11_population_size"])
    def verification_factory():
        return _check_engine(engine_factory(), execution["engine_identity"], execution["mbon11_population_size"])
    _cohort_plans(execution, declared, conditions, producer.brain.cursor)
    root = "baseline"
    with TemporaryDirectory(prefix="paired-cohort-") as temporary:
        scratch = Path(temporary)
        with RunRecorder(output_dir, run_kind="confirmation", metadata=_metadata(config, frozen, black),
                         root_branch_id=root) as recorder:
            def durable(engine, name):
                engine.brain.checkpoint(scratch / name)
                digest = recorder.ingest_checkpoint(name, scratch / name, origin_branch_id=root)
                sequence = recorder.next_sequence
                recorder.append({"type": "checkpoint", "branch_id": root, "sim_tick": engine.brain.cursor,
                                 "sim_ms": engine.brain.cursor / 10, "checkpoint_name": name})
                return {"checkpoint_name": name, "checkpoint_sha256": digest, "origin_branch_id": root,
                        "checkpoint_sequence": sequence, "sim_tick": engine.brain.cursor}

            durable(producer, "brain-before.npz")
            baseline = durable(producer, "baseline.npz")
            first = [producer]
            def factory():
                return first.pop() if first else engine_factory()
            producer = _produce_cohorts(factory, recorder, execution=execution, cohorts=declared,
                conditions=conditions, baseline_occurrence=baseline, namespace=namespace,
                confirmation_replay_resolution_hz=config["replay_resolution_hz"])
            durable(producer, "brain-after.npz")
            prefix = verify_replay_prefix(recorder.validate_prefix(), engine_factory=verification_factory)
            report = assess_assay_prefix(prefix, frozen)
            payload = build_assay_result(prefix, frozen)
            if _canonical(report.to_dict()) != _canonical(payload["report"]):
                raise ValueError("Prefix terminal report mismatch")
            recorder.append({"type": "assay_result", "branch_id": root,
                             "sim_ms": producer.brain.cursor / 10, **payload})
        sealed = verify_replay_run(recorder.path, engine_factory=verification_factory)
        independent = analyze_assay(sealed, frozen)
        if (_canonical(independent.to_dict()) != _canonical(report.to_dict())
                or _canonical(independent.to_dict()) != _canonical(payload["report"])):
            raise ValueError("Independent sealed report mismatch")
        return independent


def _produce_cohorts(engine_factory, recorder, *, execution, cohorts, conditions,
                     baseline_occurrence, namespace, measure_replay=False,
                     confirmation_replay_resolution_hz=None):
    """Produce selected native evidence into an authenticated caller-owned prefix."""
    if measure_replay is not False:
        raise ValueError("Selected physical replay measurement is not available")
    config, declared, inputs, black = _execution_declarations(execution, cohorts, conditions, namespace)
    conditions = tuple(conditions)
    if config["family"] == "qualification":
        if confirmation_replay_resolution_hz is not None:
            raise ValueError("Qualification response resolution is unavailable")
        resolution_fields = {}
    else:
        if not _number(confirmation_replay_resolution_hz, minimum=0):
            raise ValueError("Confirmation requires its validated replay resolution")
        resolution_fields = {"response_replay_resolution_hz": confirmation_replay_resolution_hz}
    if type(recorder) is not RunRecorder or recorder._closed or recorder._failed:
        raise ValueError("Selected recorder is closed, failed or not an owned recorder")
    prefix = recorder.validate_prefix()
    _matching_metadata(prefix.manifest, config, black)
    baseline = deepcopy(baseline_occurrence)
    inventory = _authenticate_occurrence(prefix, baseline,
        "qualification_checkpoint" if config["family"] == "qualification" else "checkpoint")
    _reserve_names(prefix, config, declared, conditions, namespace)

    def check(engine):
        return _check_engine(engine, config["engine_identity"], config["mbon11_population_size"])

    def factory():
        return check(engine_factory())

    producer = factory()
    fresh_state = producer.brain.checkpoint_state_sha256()
    baseline_tick = producer.brain.cursor
    cohort_plans = _cohort_plans(config, declared, conditions, baseline_tick)
    path = prefix.path / "checkpoints" / baseline["checkpoint_name"]
    if _digest_file(path) != (inventory["sha256"], inventory["size"]):
        raise ValueError("Baseline source bytes changed before restore")
    producer.brain.restore(path)
    check(producer)
    if (producer.brain.cursor != baseline["sim_tick"] or producer.brain.cursor != baseline_tick
            or producer.brain.checkpoint_state_sha256() != fresh_state):
        raise ValueError("Caller baseline differs from actual fresh factory baseline state")
    grid = GridConfiguration(**config["selected_configuration"])
    acquisitions = tuple(condition for condition in conditions if condition in ORDINARY_CONDITIONS)
    source_family = {"family": "qualification"} if config["family"] == "qualification" else {}
    with TemporaryDirectory(prefix="selected-cohort-") as temporary:
        scratch = Path(temporary)
        append = recorder.append
        def durable(engine, name, branch, parent=None):
            engine.brain.checkpoint(scratch / name)
            digest = recorder.ingest_checkpoint(name, scratch / name, origin_branch_id=branch)
            sequence = recorder.next_sequence
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
            engine.brain.restore(recorder.path / "checkpoints" / occ["checkpoint_name"])
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

        for seed, paired_identity, presentation_order in declared:
            frames, hashes = inputs[seed]
            plans = cohort_plans[seed, paired_identity, presentation_order]
            cohort_prefix, checkpoint_prefix = _cohort_names(config["family"], seed, paired_identity, presentation_order, namespace)
            routes = {}
            for condition in acquisitions:
                acquired = (producer if conditions == ("paired",) and producer.brain.cursor == baseline_tick
                            else restore(baseline))
                training_branch = _selected_branch(config["family"], seed, paired_identity,
                                                   presentation_order, condition, "training")
                plan = plans[condition]
                schedule, _, _, t0 = _training_timeline(grid, paired_identity, presentation_order,
                                                        condition, controls=True)
                append({"type": "branch_start", "branch_id": training_branch,
                        "sim_ms": acquired.brain.cursor / 10, **parent(baseline)})
                rows = []
                for segment in schedule:
                    start = acquired.brain.cursor
                    learning = (condition in ("paired", "no_external_dan", "temporally_unpaired")
                                and segment.start_ms < t0
                                and bool(segment.stimulus or segment.stimulation))
                    call(acquired, training_branch, round((segment.end_ms - segment.start_ms) * 10),
                         segment.stimulus, segment.stimulation, learning,
                         compact=not segment.stimulus and not segment.stimulation)
                    rows.append({"start_tick": start, "end_tick": acquired.brain.cursor,
                                 "stimulus": segment.stimulus, "external_stimulation": segment.stimulation,
                                 "learning": learning, "current_mv": 20.0 if segment.stimulation else None,
                                 "input_sha256": hashes[segment.stimulus or "black"]})
                exposure = {name: sum(row["end_tick"] - row["start_tick"] for row in rows
                                      if row["stimulus"] == name) for name in ("A", "B", "C")}
                if rows != plan["segments"] or exposure != plan["training_visual_exposure_ticks"]:
                    raise ValueError("Executed training disagrees with declared schedule")
                name = {"paired": "training-end.npz", "matched_reference": "matched-reference-training-end.npz"}.get(
                    condition, f"{condition}-training-end.npz")
                source = durable(acquired, checkpoint_prefix + name, training_branch, parent(baseline))
                training = {"type": "qualification_training" if config["family"] == "qualification" else "assay_training", "training_version": "associative-training/v1",
                            "training_id": training_branch, "branch_id": training_branch, "seed": seed,
                            "paired_identity": paired_identity, "presentation_order": presentation_order,
                            "condition": condition, "candidate_identity": config["candidate_identity"],
                            "baseline_tick": baseline_tick, "baseline_checkpoint_sha256": baseline["checkpoint_sha256"],
                            "training_end_checkpoint_sha256": source["checkpoint_sha256"], **plan,
                            **acquired.brain.candidate_state_digests(acquired.groups.mbon11),
                            "sim_ms": acquired.brain.cursor / 10}
                append(training)
                routes[condition] = {"condition": condition, "training": training, "source": source,
                                     "intervention_id": None}
                if condition == "paired":
                    producer = acquired

            for condition in conditions:
                if condition in acquisitions:
                    continue
                donor_route = routes["matched_reference" if condition == "necessity" else "paired"]
                recipient_route = routes["matched_reference" if condition == "sufficiency" else "paired"]
                donor = _restore_training_source(recorder, donor_route["source"], donor_route["training"],
                    factory, config["engine_identity"], config["mbon11_population_size"], **source_family)
                recipient = _restore_training_source(recorder, recipient_route["source"], recipient_route["training"],
                    factory, config["engine_identity"], config["mbon11_population_size"], **source_family)
                branch = _selected_branch(config["family"], seed, paired_identity, presentation_order, condition, "intervention")
                append({"type": "branch_start", "branch_id": branch,
                        "sim_ms": recipient.brain.cursor / 10, **parent(recipient_route["source"])})
                digests = _replace_candidate_state(donor, recipient, donor_route["training"],
                    recipient_route["training"], config["engine_identity"], config["mbon11_population_size"])
                if (condition == "sham" and digests["recipient_candidate_memory_before_sha256"]
                        != digests["recipient_candidate_memory_after_sha256"]):
                    raise ValueError("Sham candidate state changed")
                source = durable(recipient, f"{checkpoint_prefix}{condition}-post.npz", branch, parent(recipient_route["source"]))
                append({"type": "assay_intervention", "branch_id": branch, **parent(recipient_route["source"]),
                        "intervention_version": "candidate-memory-replacement/v1", "intervention_id": branch,
                        "seed": seed, "paired_identity": paired_identity, "presentation_order": presentation_order,
                        "condition": condition, "candidate_identity": config["candidate_identity"],
                        "donor_role": "matched_baseline" if condition == "necessity" else "trained",
                        "recipient_role": "untrained" if condition == "sufficiency" else "trained",
                        "donor_training_id": donor_route["training"]["training_id"],
                        "recipient_training_id": recipient_route["training"]["training_id"],
                        "donor_training_end_tick": donor.brain.cursor, "recipient_training_end_tick": recipient.brain.cursor,
                        "donor_checkpoint_sha256": donor_route["source"]["checkpoint_sha256"],
                        "recipient_checkpoint_sha256": recipient_route["source"]["checkpoint_sha256"],
                        "post_intervention_checkpoint_sha256": source["checkpoint_sha256"], **digests,
                        "replaced_components": ["memory_u", "memory_w", "weight"], "complete_replacement": True,
                        "sim_ms": recipient.brain.cursor / 10})
                routes[condition] = {"condition": condition, "training": recipient_route["training"],
                                     "source": source, "intervention_id": branch}

            def trial(engine, branch, binding, phase, stimulus, onset, retentions, response_routes):
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
                            for route in response_routes:
                                training, source = route["training"], route["source"]
                                shared = {k: training[k] for k in ("training_id", "association_t0_tick", "retention_reference_tick",
                                    "training_start_tick", "training_end_tick", "last_visual_end_tick", "last_external_dan_end_tick",
                                    "unpaired_nearest_cs_boundary_ticks", "training_visual_exposure_ticks", "training_end_checkpoint_sha256")}
                                for retention in retentions:
                                    append({"type": "qualification_evidence" if config["family"] == "qualification" else "assay_response", "branch_id": branch, **binding, **shared,
                                            "evidence_version": "mbon11-response/v1", "seed": seed,
                                            "paired_identity": paired_identity, "presentation_order": presentation_order,
                                            "retention_ms": retention, "condition": route["condition"], "phase": phase, "stimulus": stimulus,
                                            "candidate_identity": config["candidate_identity"], "population": "mbon11",
                                            "population_size": population, "cs_onset_tick": onset, "bins": bins,
                                            "rate_hz": _response_rate(sum(item["spikes"] for item in bins), stop - window_start, population),
                                            "one_spike_rate_hz": _response_rate(1, stop - window_start, population),
                                            "retention_source_checkpoint_sha256": source["checkpoint_sha256"],
                                            "passive_decay_ticks": training["retention_reference_tick"] + round(retention * 10) - source["sim_tick"],
                                            "input_sha256": hashes[stimulus], "black_sha256": hashes["black"],
                                            "endogenous_dan_spikes": sum(item["group_spikes"]["ppl101"] for item in measured),
                                            "learning": False, "external_stimulation": None, "intervention_id": route["intervention_id"],
                                            **resolution_fields, "sim_ms": engine.brain.cursor / 10})

            for stimulus in ("A", "B", "C"):
                trial(restore(baseline), f"{cohort_prefix}pre/{stimulus}", parent(baseline), "pre", stimulus,
                      baseline_tick + 1000, config["retention_times_ms"], tuple(routes.values()))
            for condition in conditions:
                route = routes[condition]
                source, training = route["source"], route["training"]
                prefix_name = cohort_prefix + ("" if condition == "paired" else condition + "/")
                for retention in config["retention_times_ms"]:
                    retained = restore(source)
                    branch = f"{prefix_name}retention/{retention}"
                    append({"type": "fork", "operation_version": OPERATION_VERSION, "branch_id": branch,
                            "sim_tick": retained.brain.cursor, "sim_ms": retained.brain.cursor / 10, **parent(source)})
                    onset = training["retention_reference_tick"] + round(retention * 10)
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
                    retained.brain.checkpoint(scratch / "retained.npz")
                    for stimulus in ("A", "B", "C"):
                        sibling = factory()
                        sibling.brain.restore(scratch / "retained.npz")
                        check(sibling)
                        if sibling.brain.cursor != target or sibling.brain.checkpoint_state_sha256() != anchor["complete_state_sha256"]:
                            raise ValueError("Retained sibling state mismatch")
                        trial(sibling, f"{prefix_name}post/{retention}/{stimulus}",
                              {"parent_branch_id": branch, "parent_state_anchor_sha256": anchor["state_anchor_sha256"]},
                              "post", stimulus, onset, [retention], (route,))
                    (scratch / "retained.npz").unlink()
    return producer
