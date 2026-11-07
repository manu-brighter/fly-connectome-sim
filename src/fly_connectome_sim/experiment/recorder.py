"""Streaming, integrity-checked run artifacts (hashes are not authentication)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from importlib.resources import files
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Callable, Iterator
import weakref


FORMAT_VERSION = "run-artifact/v1"
SCHEMA_VERSION = "run-schema/v1"
ASSAY_RESULT_VERSION = "mbon11-assay-result/v1"
ASSAY_ANALYSIS_VERSION = "mbon11-causal-analysis/v1"
GENESIS = "0" * 64
OWNED = {"sequence", "previous_scientific_sha256", "scientific_sha256", "run_metadata_sha256"}
REQUIRED_METADATA = {"engine_identity", "protocol_version", "stimulus_version", "family", "seeds", "factors", "input_sha256"}
CHECKPOINT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.npz$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DEVICES = ({"CON", "PRN", "AUX", "NUL"}
                   | {f"COM{number}" for number in range(1, 10)}
                   | {f"LPT{number}" for number in range(1, 10)})


class RunArtifactError(ValueError):
    """An incomplete or invalid run artifact."""


@dataclass(frozen=True)
class RunReadLimits:
    """Optional operational ceilings for complete sealed artifact intake."""
    max_manifest_bytes: int
    max_event_line_bytes: int
    max_events_bytes: int
    max_events: int
    max_checkpoints: int

    def __post_init__(self) -> None:
        for name in ("max_manifest_bytes", "max_event_line_bytes", "max_events_bytes",
                     "max_events", "max_checkpoints"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise RunArtifactError(f"Invalid run read limit: {name}")


def _canonical(value: object) -> bytes:
    def check_keys(item: object) -> None:
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise RunArtifactError("JSON object keys must be strings")
            for child in item.values():
                check_keys(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check_keys(child)

    try:
        check_keys(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except RunArtifactError:
        raise
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as error:
        raise RunArtifactError(f"Invalid strict JSON: {error}") from error


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise RunArtifactError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_load(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              RunArtifactError(f"Nonfinite JSON value: {value}")))
    except RunArtifactError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise RunArtifactError(f"Invalid JSON: {error}") from error


def _scientific(value: object) -> object:
    if isinstance(value, dict):
        return {key: _scientific(item) for key, item in value.items()
                if key not in {"compute_seconds", "kernel_seconds"}}
    if isinstance(value, list):
        return [_scientific(item) for item in value]
    return value


def _scientific_event(event: dict) -> dict:
    return _scientific({key: value for key, value in event.items()
                        if key != "scientific_sha256"})


def _metadata(metadata: dict, run_kind: str) -> dict:
    if not isinstance(metadata, dict) or not REQUIRED_METADATA <= metadata.keys():
        raise RunArtifactError("Missing run metadata declaration")
    result = _strict_load(_canonical(metadata))
    if not isinstance(result["engine_identity"], dict) or not result["engine_identity"]:
        raise RunArtifactError("Missing engine identity")
    if any(not isinstance(result[name], str) or not result[name]
           for name in ("protocol_version", "stimulus_version", "family")):
        raise RunArtifactError("Invalid protocol or stimulus declaration")
    if (not isinstance(result["seeds"], list)
            or any(type(seed) is not int or seed < 0 for seed in result["seeds"])
            or not isinstance(result["factors"], dict)
            or not isinstance(result["input_sha256"], list)
            or any(not isinstance(item, str) or not DIGEST.fullmatch(item)
                   for item in result["input_sha256"])):
        raise RunArtifactError("Invalid seeds, factors or input hash set")
    if "black_input" in result:
        from .replay import _black
        try:
            black = _black(result["black_input"])
            if black["input_sha256"] not in result["input_sha256"]:
                raise ValueError("Black input is not in the declared input set")
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
    if run_kind == "confirmation":
        digest = result.get("frozen_config_sha256")
        contract = result.get("assay_contract")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest) \
                or not isinstance(contract, dict) \
                or contract.get("analysis_version") != ASSAY_ANALYSIS_VERSION:
            raise RunArtifactError("Invalid confirmation config or analysis binding")
    return result


def _metadata_digest(run_kind: str, root_branch_id: str, metadata: dict) -> str:
    return sha256(_canonical({"run_kind": run_kind, "root_branch_id": root_branch_id,
                              "metadata": metadata})).hexdigest()


def _schema_digest() -> str:
    return sha256(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes()).hexdigest()


def _safe_name(name: object) -> str:
    if (not isinstance(name, str) or name in {".", ".."}
            or not CHECKPOINT_NAME.fullmatch(name)
            or name.split(".", 1)[0].upper() in WINDOWS_DEVICES):
        raise RunArtifactError("Unsafe checkpoint name")
    return name


def _directory_identity(path: Path) -> tuple[int, int]:
    if path.is_symlink() or path.is_junction() or not path.is_dir():
        raise RunArtifactError(f"Run directory substituted: {path}")
    state = path.stat(follow_symlinks=False)
    return state.st_dev, state.st_ino


def _walk_bindings(value: object, metadata: dict) -> None:
    if isinstance(value, dict):
        if "engine_identity" in value and value["engine_identity"] != metadata["engine_identity"]:
            raise RunArtifactError("Engine identity mismatch")
        if "input_sha256" in value and value["input_sha256"] is not None \
                and value["input_sha256"] not in metadata["input_sha256"]:
            raise RunArtifactError("Undeclared input hash")
        for item in value.values():
            _walk_bindings(item, metadata)
    elif isinstance(value, list):
        for item in value:
            _walk_bindings(item, metadata)


def _finite_number(value: object, *, positive: bool = False,
                   allow_negative: bool = False) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        number = float(value)
    except OverflowError:
        return False
    return math.isfinite(number) and (allow_negative or
                                      (number > 0 if positive else number >= 0))


def _numeric_object(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields \
        and all(_finite_number(item, allow_negative=True) for item in value.values())


def _check_motor_readout(event: dict, metadata: dict) -> None:
    from .adapter import LateralMotorAdapter

    readout = event["motor_readout"]
    telemetry = event.get("telemetry")
    if event["type"] not in {"observation", "observe"} \
            or not isinstance(telemetry, dict) \
            or not isinstance(telemetry.get("rates_hz"), dict) \
            or not _finite_number(telemetry.get("sim_ms")) \
            or telemetry["sim_ms"] != event["sim_ms"] \
            or not isinstance(telemetry.get("engine_identity"), dict) \
            or _canonical(telemetry["engine_identity"]) != _canonical(metadata["engine_identity"]):
        raise RunArtifactError("Motor readout requires same-event measured telemetry, clock and engine identity")
    if not isinstance(readout, dict) \
            or set(readout) != {"interpretation", "action_threshold_hz", "decision"} \
            or readout["interpretation"] != "engineered_unvalidated_motor_readout" \
            or not _finite_number(readout["action_threshold_hz"]):
        raise RunArtifactError("Invalid engineered motor readout declaration")
    decision = readout["decision"]
    if not isinstance(decision, dict) \
            or set(decision) != {"adapter_version", "signed_difference_hz", "evidence_strength", "action"} \
            or not isinstance(decision["adapter_version"], str) \
            or not isinstance(decision["action"], str) \
            or not _finite_number(decision["signed_difference_hz"], allow_negative=True) \
            or not _finite_number(decision["evidence_strength"]) \
            or decision["evidence_strength"] > 1:
        raise RunArtifactError("Invalid motor decision fields")
    try:
        expected = asdict(LateralMotorAdapter(
            action_threshold_hz=readout["action_threshold_hz"],
        ).adapt(telemetry))
    except ValueError as error:
        raise RunArtifactError(f"Invalid measured motor source: {error}") from error
    if _canonical(decision) != _canonical(expected):
        raise RunArtifactError("Motor decision differs from bound measured telemetry")


def _check_candidate_w_pair(projection: dict) -> None:
    """Check encoded shape only; no unauthenticated numeric bytes are decoded."""
    if (type(projection) is not dict or set(projection) != {
            "projection_version", "dtype", "shape", "maps", "original_hex", "repeat_hex"}
            or projection["projection_version"] != "selected-candidate-w-pair/v1"
            or projection["dtype"] != "<f8" or type(projection["shape"]) is not list
            or len(projection["shape"]) != 1 or type(projection["shape"][0]) is not int
            or projection["shape"][0] < 1):
        raise RunArtifactError("Invalid candidate W pair shape")
    size, maps = projection["shape"][0], projection["maps"]
    if type(maps) is not dict or set(maps) != {"target_indices", "candidate_positions", "candidate_edge_indices"}:
        raise RunArtifactError("Invalid candidate W pair maps")
    for name, values in maps.items():
        if (type(values) is not list or not values
                or any(type(value) is not int or not 0 <= value <= 9223372036854775789 for value in values)
                or len(set(values)) != len(values) or (name != "target_indices" and len(values) != size)):
            raise RunArtifactError("Invalid candidate W pair indices")
    for side in ("original", "repeat"):
        encoded = projection[side + "_hex"]
        if type(encoded) is not str or len(encoded) != 16 * size or re.fullmatch(r"[0-9a-f]+", encoded) is None:
            raise RunArtifactError("Invalid candidate W pair hex")


def _check_qualification_replay(event: dict, metadata: dict, count: int) -> None:
    """Closed structural intake, without selection authority or numerical decoding."""
    from .replay import _clock, _source

    def fields(value, expected):
        if type(value) is not dict or set(value) != expected:
            raise RunArtifactError("Invalid selected replay fields")

    def integer(value, minimum=0):
        if type(value) is not int or not minimum <= value <= 9223372036854775789:
            raise RunArtifactError("Invalid selected replay integer")

    def digest(value):
        if type(value) is not str or DIGEST.fullmatch(value) is None:
            raise RunArtifactError("Invalid selected replay digest")

    base = OWNED | {"type", "branch_id", "sim_ms", "replay_version", "replay_id", "original_branch_id",
        "physical_key", "source_occurrence", "engine_identity_sha256", "candidate_identity", "population_size",
        "input_sha256", "black_sha256", "response_window", "cs_onset_tick", "sim_tick", "operations",
        "boundaries", "candidate_projection", "response_replay_resolution_hz", "candidate_memory_w_resolution",
        "parent_branch_id"}
    if type(event) is not dict or type(metadata) is not dict or metadata.get("family") != "qualification":
        raise RunArtifactError("Selected replay requires qualification metadata")
    key = event.get("physical_key")
    if type(key) is not dict or key.get("phase") not in ("pre", "post"):
        raise RunArtifactError("Invalid selected replay physical key")
    post = key["phase"] == "post"
    fields(key, {"seed", "paired_identity", "presentation_order", "phase", "stimulus"}
           | ({"condition", "retention_ms"} if post else set()))
    fields(event, base | ({"parent_state_anchor_sha256"} if post else {
        "parent_checkpoint_name", "parent_checkpoint_sequence", "parent_checkpoint_sha256"}))
    if (type(key["seed"]) is not int or key["seed"] not in (11, 23)
            or key["paired_identity"] not in ("A", "B") or key["presentation_order"] not in ("AB", "BA")
            or key["stimulus"] not in ("A", "B", "C")):
        raise RunArtifactError("Invalid selected replay factors")
    if post:
        integer(key["retention_ms"], 10000)
        if key["condition"] not in ("paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired",
                                    "matched_reference", "necessity", "sufficiency", "sham"):
            raise RunArtifactError("Invalid selected replay condition")
        digest(event["parent_state_anchor_sha256"])
    else:
        integer(event["parent_checkpoint_sequence"])
        _safe_name(event["parent_checkpoint_name"])
        digest(event["parent_checkpoint_sha256"])
    if (event["type"] != "qualification_replay" or event["replay_version"] != "selected-response-repeat/v1"
            or type(event["original_branch_id"]) is not str or not event["original_branch_id"]
            or event["replay_id"] != event["original_branch_id"] + "/repeat"
            or event["branch_id"] != event["replay_id"]
            or type(event["parent_branch_id"]) is not str or not event["parent_branch_id"]):
        raise RunArtifactError("Invalid selected replay naming")
    integer(count)
    integer(event["sequence"])
    if event["sequence"] != count:
        raise RunArtifactError("Invalid selected replay sequence")
    for name in OWNED - {"sequence"}:
        digest(event[name])
    try:
        _source(event["source_occurrence"])
        if event["source_occurrence"]["checkpoint_sequence"] >= count:
            raise ValueError("Late selected replay source")
        identity = metadata["engine_identity"]
        inputs = metadata["rgb_input_sha256"]
        if (event["engine_identity_sha256"] != identity["sha256"]
                or event["candidate_identity"] != metadata["candidate_identity"]
                or event["candidate_identity"] != "kc-mbon11-ppl101/v1"
                or type(event["population_size"]) is not int or event["population_size"] < 1
                or type(metadata["mbon11_population_size"]) is not int
                or event["population_size"] != metadata["mbon11_population_size"]
                or event["input_sha256"] != inputs["stimuli"][str(key["seed"])][key["stimulus"]]
                or event["black_sha256"] != inputs["black"]
                or event["black_sha256"] != metadata["black_input"]["input_sha256"]):
            raise ValueError("Selected replay metadata mismatch")
        for name in ("engine_identity_sha256", "input_sha256", "black_sha256"):
            digest(event[name])
        integer(event["cs_onset_tick"], 1000)
        integer(event["sim_tick"])
        _clock(event["sim_ms"], event["sim_tick"])
    except (KeyError, TypeError, ValueError) as error:
        raise RunArtifactError("Invalid selected replay declarations") from error
    window = event["response_window"]
    fields(window, {"start_ms", "end_ms"})
    if (any(not _finite_number(value) or not math.isfinite(value * 10)
            or value * 10 != round(value * 10) for value in window.values())
            or window["start_ms"] >= window["end_ms"]):
        raise RunArtifactError("Invalid selected replay window")
    for name in ("response_replay_resolution_hz", "candidate_memory_w_resolution"):
        if not _finite_number(event[name]):
            raise RunArtifactError("Invalid selected replay resolution")
    boundaries = event["boundaries"]
    fields(boundaries, {"start", "window", "final"})
    for boundary, pair in boundaries.items():
        fields(pair, {"original", "repeat"})
        for state in pair.values():
            fields(state, {"sim_tick", "complete_state_sha256"} | ({"weights_frozen"} if boundary == "start" else {
                "candidate_memory_sha256", "noncandidate_state_sha256"}))
            integer(state["sim_tick"])
            for name in state.keys() - {"sim_tick", "weights_frozen"}:
                digest(state[name])
            if boundary == "start" and type(state["weights_frozen"]) is not bool:
                raise RunArtifactError("Invalid selected replay frozen flag")
        if _canonical(pair["original"]) != _canonical(pair["repeat"]):
            raise RunArtifactError("Selected replay boundary disagreement")
    start, stop, final = (boundaries[name]["original"]["sim_tick"] for name in ("start", "window", "final"))
    if (start != event["cs_onset_tick"] - 1000
            or stop != event["cs_onset_tick"] + round(window["end_ms"] * 10)
            or not start < stop <= final or final != event["sim_tick"]
            or (stop == final and boundaries["window"] != boundaries["final"])):
        raise RunArtifactError("Invalid selected replay boundary clocks")
    operations = event["operations"]
    fields(operations, {"original", "repeat"})
    seen = set()
    for references in operations.values():
        if type(references) is not list or not 4 <= len(references) <= 6:
            raise RunArtifactError("Invalid selected replay operation count")
        previous = -1
        for reference in references:
            fields(reference, {"sequence", "scientific_sha256"})
            integer(reference["sequence"])
            digest(reference["scientific_sha256"])
            position = reference["sequence"]
            if not previous < position < count or position in seen:
                raise RunArtifactError("Invalid selected replay operation reference")
            previous = position
            seen.add(position)
    _check_candidate_w_pair(event["candidate_projection"])


def _check_qualification_result(event: dict, metadata: dict) -> None:
    required = {"status", "family", "seeds", "selected_configuration",
                "selected_window", "selected_retention_ms", "observed_effect_sign",
                "benchmark", "compute_seconds"}
    if not required <= event.keys():
        raise RunArtifactError("Incomplete qualification result")
    if type(event["status"]) is not str \
            or event["status"] not in {"supported", "unsupported"} \
            or type(event["family"]) is not str \
            or event["family"] != metadata["family"] \
            or type(event["seeds"]) is not list \
            or any(type(seed) is not int for seed in event["seeds"]) \
            or event["seeds"] != metadata["seeds"]:
        raise RunArtifactError("Qualification result status or declaration mismatch")
    benchmark = event["benchmark"]
    counters = {"event_count", "checkpoint_bytes", "peak_event_buffer_bytes"}
    if not isinstance(benchmark, dict) or set(benchmark) != counters | {"simulated_seconds"} \
            or not _finite_number(benchmark["simulated_seconds"]) \
            or any(type(benchmark[name]) is not int or benchmark[name] < 0
                   for name in counters) \
            or not _finite_number(event["compute_seconds"]):
        raise RunArtifactError("Invalid qualification benchmark")
    selection = (event["selected_configuration"], event["selected_window"],
                 event["selected_retention_ms"], event["observed_effect_sign"])
    if event["status"] == "supported":
        if not _numeric_object(selection[0], {"cs_duration_ms", "dan_onset_ms",
                                              "post_pair_gap_ms"}) \
                or not _numeric_object(selection[1], {"start_ms", "end_ms"}) \
                or not _finite_number(selection[2], positive=True) \
                or type(selection[3]) is not int or selection[3] not in (-1, 1):
            raise RunArtifactError("Invalid supported qualification selection")
    elif any(value is not None for value in selection):
        raise RunArtifactError("Unsupported qualification cannot have a selection")


def _check_grid_binding(event: dict, checkpoints: dict, seen: set[str], count: int) -> str:
    """Structural/prior-occurrence intake; scientific ownership belongs to grid reduction."""
    fields = {"binding_version", "grid_evidence_id", "grid_index", "seed", "paired_identity",
              "presentation_order", "baseline_occurrence", "training_occurrences",
              "retained_occurrences", "observation_sequences", "failures"}
    framing = OWNED | {"type", "branch_id", "sim_ms", "parent_branch_id",
                       "parent_checkpoint_sha256", "parent_checkpoint_name", "parent_checkpoint_sequence"}
    training = {"paired", "matched_reference", "frozen_plasticity", "paired_replay"}
    retained = training - {"paired_replay"}
    times = {"10000", "20000", "30000", "60000"}

    def invalid():
        raise RunArtifactError("Invalid qualification grid binding")

    def mapping(value, keys):
        if not isinstance(value, dict) or not value.keys() <= keys:
            invalid()

    def occurrence(value):
        required = {"checkpoint_name", "checkpoint_sha256", "origin_branch_id",
                    "checkpoint_sequence", "sim_tick"}
        if not isinstance(value, dict) or value.keys() != required:
            invalid()
        name = _safe_name(value["checkpoint_name"])
        data = checkpoints.get(name)
        if type(value["checkpoint_sequence"]) is not int or not 0 <= value["checkpoint_sequence"] < count \
                or type(value["sim_tick"]) is not int or not 0 <= value["sim_tick"] <= 9223372036854775789 \
                or name not in seen or data is None \
                or value["checkpoint_sha256"] != data["sha256"] \
                or value["origin_branch_id"] != data["origin_branch_id"] \
                or value["checkpoint_sequence"] != data["checkpoint_sequence"]:
            invalid()
        from .replay import _clock
        try:
            _clock(data["sim_ms"], value["sim_tick"])
        except ValueError:
            invalid()
        if "sim_tick" in data and data["sim_tick"] != value["sim_tick"]:
            invalid()

    def sequences(value, limit):
        if not isinstance(value, list) or len(value) > limit \
                or any(type(item) is not int or not 0 <= item < count for item in value) \
                or any(a >= b for a, b in zip(value, value[1:])):
            invalid()

    if not fields <= event.keys() or not event.keys() <= fields | framing \
            or event["binding_version"] != "qualification-grid-binding/v1" \
            or type(event["grid_index"]) is not int or not 0 <= event["grid_index"] < 12 \
            or type(event["seed"]) is not int or event["seed"] not in (11, 23) \
            or event["paired_identity"] not in ("A", "B") \
            or event["presentation_order"] not in ("AB", "BA"):
        invalid()
    identifier = f"grid/{event['grid_index']}/{event['seed']}/{event['paired_identity']}/{event['presentation_order']}"
    if event["grid_evidence_id"] != identifier:
        invalid()
    occurrence(event["baseline_occurrence"])
    mapping(event["training_occurrences"], training)
    for value in event["training_occurrences"].values():
        occurrence(value)
    mapping(event["retained_occurrences"], times)
    for roles in event["retained_occurrences"].values():
        mapping(roles, retained)
        for value in roles.values():
            occurrence(value)
    observations = event["observation_sequences"]
    mapping(observations, {"pre", "pre_replay", "training", "retention", "post"})
    if not {"pre", "training", "retention", "post"} <= observations.keys():
        invalid()
    mapping(observations["pre"], {"A", "B", "C"})
    for value in observations["pre"].values():
        sequences(value, 4)
    if "pre_replay" in observations:
        sequences(observations["pre_replay"], 4)
    mapping(observations["training"], training)
    for value in observations["training"].values():
        sequences(value, 64)
    mapping(observations["retention"], times)
    for roles in observations["retention"].values():
        mapping(roles, retained)
        for value in roles.values():
            sequences(value, 120)
    mapping(observations["post"], times)
    for roles in observations["post"].values():
        mapping(roles, retained)
        for role, trials in roles.items():
            mapping(trials, {"A", "B", "C"} if role == "paired" else {event["paired_identity"]})
            for value in trials.values():
                sequences(value, 4)
    failures = event["failures"]
    if not isinstance(failures, list) or len(failures) > 4:
        invalid()
    previous_t = 0
    for failure in failures:
        if not isinstance(failure, dict) or failure.keys() != {
            "scope", "stage", "condition", "stimulus", "retention_ms", "reason",
        } or not isinstance(failure["reason"], str) or not failure["reason"].strip() \
                or failure["stimulus"] not in ("A", "B", "C", None):
            invalid()
        stage, condition = failure["stage"], failure["condition"]
        if type(stage) is not str or (condition is not None and type(condition) is not str):
            invalid()
        if failure["scope"] == "base":
            if len(failures) != 1 or failure["retention_ms"] is not None \
                    or stage not in {"pre", "pre_replay", "training", "base_validation"} \
                    or (condition not in training if stage == "training" else condition is not None):
                invalid()
        elif failure["scope"] == "retention":
            value = failure["retention_ms"]
            if type(value) is not int or str(value) not in times or value <= previous_t \
                    or stage not in {"retention_timing", "retention", "post", "measurement"} \
                    or (condition not in retained if stage in {"retention", "post"} else condition is not None):
                invalid()
            previous_t = value
        else:
            invalid()
    return identifier


def _check_assay_result(event: dict, metadata: dict) -> None:
    required = {"result_version", "analysis_version", "frozen_config_sha256",
                "status", "reasons", "report", "report_sha256",
                "evidence_event_count", "evidence_final_scientific_sha256"}
    if not required <= event.keys():
        raise RunArtifactError("Incomplete assay result")
    if event["result_version"] != ASSAY_RESULT_VERSION \
            or event["analysis_version"] != metadata["assay_contract"]["analysis_version"] \
            or event["frozen_config_sha256"] != metadata["frozen_config_sha256"]:
        raise RunArtifactError("Assay result config or analysis binding mismatch")
    status = event["status"]
    reasons = event["reasons"]
    if not isinstance(status, str) or status not in {"supported", "unsupported", "inconclusive"} \
            or not isinstance(reasons, list) \
            or any(not isinstance(reason, str) or not reason for reason in reasons) \
            or reasons != sorted(set(reasons)) \
            or (status == "supported") != (not reasons):
        raise RunArtifactError("Invalid assay status or deterministic reasons")
    report = event["report"]
    if not isinstance(report, dict) or set(report) != {"status", "values", "reasons"} \
            or not isinstance(report["values"], dict) \
            or report["status"] != status or report["reasons"] != reasons:
        raise RunArtifactError("Assay report shape or result mismatch")
    if event["report_sha256"] != sha256(_canonical(report)).hexdigest():
        raise RunArtifactError("Assay report digest mismatch")


class _Chain:
    def __init__(self, root: str, metadata: dict, checkpoints: dict, run_kind: str,
                 prefix_events: Callable[[int], Iterator[dict]] | None = None):
        self.root = root
        self.run_kind = run_kind
        self.metadata = metadata
        self.checkpoints = checkpoints
        self.seen_checkpoints: set[str] = set()
        self.branches: dict[str, tuple] = {}
        self.anchors: dict[str, dict] = {}
        self.anchor_ids: set[str] = set()
        self.prefix_events = prefix_events
        self.projection = None
        self.count = 0
        self.previous = GENESIS
        self.result_seen = False
        self.grid_ids: set[str] = set()
        self.metadata_digest = _metadata_digest(run_kind, root, metadata)

    def _parent(self, event: dict) -> tuple | None:
        fields = {"parent_branch_id", "parent_checkpoint_sha256", "parent_state_anchor_sha256",
                  "parent_checkpoint_name", "parent_checkpoint_sequence"}
        if not fields & event.keys():
            return None
        # Legacy later events may repeat only part of their established ancestry.
        # New branches still require exactly one complete, prior parent kind.
        declared = self.branches.get(event["branch_id"], (None, None))[1]
        if declared is not None:
            event = dict(event)
            event.setdefault("parent_branch_id", declared[0])
            if not {"parent_checkpoint_sha256", "parent_state_anchor_sha256"} & event.keys():
                if declared[1] == "checkpoint":
                    event["parent_checkpoint_sha256"] = declared[2][2]
                else:
                    event["parent_state_anchor_sha256"] = declared[2]
        parent = event.get("parent_branch_id")
        durable = "parent_checkpoint_sha256" in event
        anchor = "parent_state_anchor_sha256" in event
        if type(parent) is not str or not parent or durable == anchor:
            raise RunArtifactError("Exactly one nonempty parent occurrence is required")
        digest = event["parent_checkpoint_sha256" if durable else "parent_state_anchor_sha256"]
        if type(digest) is not str or not DIGEST.fullmatch(digest):
            raise RunArtifactError("Invalid parent occurrence digest")
        if parent not in self.branches or parent == event["branch_id"]:
            raise RunArtifactError("Missing, late or cyclic parent")
        if anchor:
            if {"parent_checkpoint_name", "parent_checkpoint_sequence"} & event.keys():
                raise RunArtifactError("Anchor parent cannot declare a durable occurrence")
            data = self.anchors.get(digest)
            if data is None or data["origin_branch_id"] != parent:
                raise RunArtifactError("Missing, late or wrong anchor parent")
            return parent, "anchor", digest, data["sim_tick"]
        explicit = {"parent_checkpoint_name", "parent_checkpoint_sequence"} & event.keys()
        if explicit and explicit != {"parent_checkpoint_name", "parent_checkpoint_sequence"}:
            raise RunArtifactError("Incomplete durable occurrence reference")
        if event.get("operation_version") is not None and not explicit:
            raise RunArtifactError("Replay fork requires exact durable name and sequence")
        if explicit:
            _safe_name(event["parent_checkpoint_name"])
            if type(event["parent_checkpoint_sequence"]) is not int \
                    or event["parent_checkpoint_sequence"] < 0:
                raise RunArtifactError("Invalid parent checkpoint sequence")
        candidates = [(name, data) for name, data in self.checkpoints.items()
                      if name in self.seen_checkpoints and data["sha256"] == digest
                      and data["origin_branch_id"] == parent
                      and (not explicit or (name == event["parent_checkpoint_name"]
                           and data["checkpoint_sequence"] == event["parent_checkpoint_sequence"]))]
        if len(candidates) != 1:
            raise RunArtifactError("Missing, late, wrong or ambiguous parent checkpoint")
        name, data = candidates[0]
        return parent, "checkpoint", (name, data["checkpoint_sequence"], digest), data.get("sim_tick")

    def _anchor(self, event: dict) -> dict:
        from .replay import ANCHOR_FIELDS, build_black_retention_recipe, validate_state_anchor

        framing = {"type", "branch_id", "sim_ms", "sequence", "previous_scientific_sha256",
                   "scientific_sha256"}
        try:
            if set(event) != ANCHOR_FIELDS | framing:
                raise ValueError("Invalid state anchor event fields")
            anchor = validate_state_anchor({key: event[key] for key in ANCHOR_FIELDS})
            from .replay import _clock
            _clock(event["sim_ms"], anchor["sim_tick"])
            if event["branch_id"] != anchor["origin_branch_id"] \
                    or anchor["anchor_id"] in self.anchor_ids \
                    or anchor["state_anchor_sha256"] in self.anchors:
                raise ValueError("Wrong anchor origin or duplicate occurrence")
            prefix = {"event_count": self.count, "final_sequence": self.count - 1,
                      "final_scientific_sha256": self.previous}
            black = self.metadata.get("black_input")
            if (self.prefix_events is None and self.projection is None) or black is None:
                raise ValueError("Anchor requires actual prefix and declared black input")
            if self.projection is not None:
                self.projection.check_recipe(anchor["recipe"], prefix)
            else:
                recipe = build_black_retention_recipe(
                    self.prefix_events(self.count), source_occurrence=anchor["source_occurrence"],
                    origin_branch_id=anchor["origin_branch_id"], target_tick=anchor["sim_tick"],
                    engine_identity=self.metadata["engine_identity"],
                    run_metadata_sha256=self.metadata_digest, black_input=black,
                    scientific_prefix=prefix,
                )
                if _canonical(recipe) != _canonical(anchor["recipe"]):
                    raise ValueError("Anchor recipe differs from actual completed prefix")
            return {**anchor, "event_sequence": self.count}
        except ValueError as error:
            raise RunArtifactError(f"Invalid state anchor: {error}") from error

    def check(self, event: dict) -> None:
        if self.result_seen:
            raise RunArtifactError("Result must be terminal")
        if not isinstance(event, dict) or not isinstance(event.get("type"), str) \
                or not event["type"] or not isinstance(event.get("branch_id"), str) \
                or not event["branch_id"]:
            raise RunArtifactError("Event needs a nonempty type and branch_id")
        if event["type"] == "qualification_result" and self.run_kind != "qualification":
            raise RunArtifactError("Qualification result in a non-qualification run")
        if event["type"] == "assay_result" and self.run_kind != "confirmation":
            raise RunArtifactError("Assay result in a non-confirmation run")
        if event["type"] == "qualification_replay":
            if self.run_kind != "qualification":
                raise RunArtifactError("Selected replay in a non-qualification run")
            _check_qualification_replay(event, self.metadata, self.count)
        grid_id = None
        if event["type"] == "qualification_grid_binding":
            if self.run_kind != "qualification":
                raise RunArtifactError("Grid binding in a non-qualification run")
            grid_id = _check_grid_binding(event, self.checkpoints, self.seen_checkpoints, self.count)
            if grid_id in self.grid_ids or len(self.grid_ids) >= 96:
                raise RunArtifactError("Duplicate or excessive qualification grid binding")
        branch = event["branch_id"]
        clock = event.get("sim_ms")
        if isinstance(clock, bool) or not isinstance(clock, (int, float)) or clock < 0:
            raise RunArtifactError("Invalid branch clock")
        try:
            clock_value = float(clock)
        except OverflowError as error:
            raise RunArtifactError("Invalid branch clock") from error
        if not math.isfinite(clock_value):
            raise RunArtifactError("Invalid branch clock")
        wire_clock_value = clock_value
        tick_field = ("sim_tick" if "sim_tick" in event else "end_tick"
                      if event.get("operation_version") == "black-retention-operation/v1"
                      and event["type"] == "neutral_gap_chunk" else None)
        if tick_field is not None:
            from .replay import _clock, _integer
            try:
                tick = _integer(event[tick_field])
                _clock(clock, tick)
                clock_value = tick / 10
            except (KeyError, ValueError) as error:
                raise RunArtifactError("Invalid authoritative event tick/clock") from error
        if event.get("sequence") != self.count or type(event.get("sequence")) is not int:
            raise RunArtifactError("Event sequence gap or duplicate")
        if event.get("run_metadata_sha256") != self.metadata_digest:
            raise RunArtifactError("Event metadata digest mismatch")
        if event.get("previous_scientific_sha256") != self.previous:
            raise RunArtifactError("Scientific chain break")
        ancestry = self._parent(event)
        new_branch = branch not in self.branches
        if new_branch:
            if branch == self.root:
                if ancestry is not None:
                    raise RunArtifactError("Root branch cannot have a parent")
            else:
                if ancestry is None:
                    raise RunArtifactError("Restored branch lacks parent ancestry")
                parent, kind, reference, tick = ancestry
                if tick is not None:
                    from .replay import _clock, _integer
                    try:
                        _clock(event["sim_ms"], tick)
                        if "sim_tick" in event and _integer(event["sim_tick"]) != tick:
                            raise ValueError("Fork integer clock mismatch")
                    except ValueError as error:
                        raise RunArtifactError(str(error)) from error
                elif self.checkpoints[reference[0]]["sim_ms"] != wire_clock_value:
                    raise RunArtifactError("Parent checkpoint clock mismatch")
            branch_state = (clock_value, ancestry)
        else:
            previous_clock, declared_ancestry = self.branches[branch]
            if clock_value < previous_clock or (ancestry is not None and ancestry != declared_ancestry):
                raise RunArtifactError("Branch time or ancestry changed")
            branch_state = (clock_value, declared_ancestry)
        checkpoint_name = None
        if "checkpoint_name" in event:
            name = _safe_name(event["checkpoint_name"])
            data = self.checkpoints.get(name)
            if not data or name in self.seen_checkpoints or data["origin_branch_id"] != branch \
                    or event.get("checkpoint_sha256") != data["sha256"] \
                    or event.get("checkpoint_size") != data["size"] \
                    or ("sim_ms" in data and data["sim_ms"] != wire_clock_value) \
                    or ("checkpoint_sequence" in data and data["checkpoint_sequence"] != self.count) \
                    or ("sim_tick" in data and event.get("sim_tick") != data["sim_tick"]):
                raise RunArtifactError("Checkpoint event does not match ingested file")
            if "sim_tick" in event:
                from .replay import _clock, _integer
                try:
                    _clock(event["sim_ms"], _integer(event["sim_tick"]))
                except ValueError as error:
                    raise RunArtifactError(str(error)) from error
            checkpoint_name = name
        anchor = self._anchor(event) if event["type"] == "state_anchor" else None
        if event["type"] == "qualification_result":
            _check_qualification_result(event, self.metadata)
        elif event["type"] == "assay_result":
            _check_assay_result(event, self.metadata)
            if type(event["evidence_event_count"]) is not int \
                    or event["evidence_event_count"] != self.count \
                    or event["evidence_final_scientific_sha256"] != self.previous:
                raise RunArtifactError("Assay result evidence prefix mismatch")
        if "motor_readout" in event:
            _check_motor_readout(event, self.metadata)
        _walk_bindings(event, self.metadata)
        scientific_digest = sha256(_canonical(_scientific_event(event))).hexdigest()
        if event.get("scientific_sha256") != scientific_digest:
            raise RunArtifactError("Scientific event digest mismatch")
        if self.projection is not None:
            self.projection.accept(event)
        self.branches[branch] = branch_state
        if grid_id is not None:
            self.grid_ids.add(grid_id)
        if checkpoint_name is not None:
            self.checkpoints[checkpoint_name]["sim_ms"] = wire_clock_value
            self.checkpoints[checkpoint_name]["checkpoint_sequence"] = self.count
            if "sim_tick" in event:
                self.checkpoints[checkpoint_name]["sim_tick"] = event["sim_tick"]
            self.seen_checkpoints.add(checkpoint_name)
        if anchor is not None:
            self.anchors[anchor["state_anchor_sha256"]] = anchor
            self.anchor_ids.add(anchor["anchor_id"])
        self.previous = scientific_digest
        self.count += 1
        if event["type"] in {"qualification_result", "assay_result"}:
            self.result_seen = True


class RunRecorder:
    """Own one new directory; append is flushed per event, fsync at flush/close."""

    @property
    def next_sequence(self) -> int:
        """Next global append position under this recorder's single writer."""
        return self._chain.count

    def __init__(self, path: str | Path, *, run_kind: str, metadata: dict,
                 root_branch_id: str):
        if not isinstance(run_kind, str) or run_kind not in {"pilot", "qualification", "confirmation"}:
            raise RunArtifactError("Invalid run kind")
        if not isinstance(root_branch_id, str) or not root_branch_id:
            raise RunArtifactError("Invalid root branch")
        self.metadata = _metadata(metadata, run_kind)
        self.path = Path(path)
        if any(parent.is_symlink() or parent.is_junction()
               for parent in self.path.absolute().parents):
            raise RunArtifactError("Output ancestor symlink or junction rejected")
        self.run_kind = run_kind
        self.root_branch_id = root_branch_id
        try:
            self.path.mkdir(parents=False, exist_ok=False)
            (self.path / "checkpoints").mkdir()
            self._stream = (self.path / "events.jsonl").open("xb")
        except OSError as error:
            raise RunArtifactError(f"Cannot exclusively create output directory: {error}") from error
        self._run_identity = _directory_identity(self.path)
        self._checkpoint_identity = _directory_identity(self.path / "checkpoints")
        self._checkpoints: dict[str, dict] = {}
        self._chain = _Chain(root_branch_id, self.metadata, self._checkpoints, run_kind,
                             lambda count: _raw_events(self.path, count=count))
        self._raw_digest = sha256()
        self._closed = False
        self._failed = False

    def __enter__(self) -> RunRecorder:
        return self

    def __exit__(self, error_type, error, traceback) -> None:
        if error_type is None:
            self.close()
        elif not self._closed:
            self._stream.close()
            self._closed = True

    def _assert_directories(self) -> None:
        if (_directory_identity(self.path) != self._run_identity
                or _directory_identity(self.path / "checkpoints") != self._checkpoint_identity):
            raise RunArtifactError("Run or checkpoint directory identity changed")

    def ingest_checkpoint(self, name: str, source: str | Path, *, origin_branch_id: str) -> str:
        if self._closed or self._failed:
            raise RunArtifactError("Recorder is closed or failed")
        name = _safe_name(name)
        if name in self._checkpoints or not isinstance(origin_branch_id, str) \
                or not origin_branch_id:
            raise RunArtifactError("Duplicate checkpoint or invalid origin")
        target = self.path / "checkpoints" / name
        if target.exists() or target.is_symlink():
            raise RunArtifactError("Checkpoint target already exists")
        temporary = None
        digest = sha256()
        size = 0
        try:
            with Path(source).open("rb") as reader:
                self._assert_directories()
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{name}.",
                                                 suffix=".tmp", delete=False) as writer:
                    temporary = Path(writer.name)
                    while chunk := reader.read(1024 * 1024):
                        writer.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                    writer.flush()
                    os.fsync(writer.fileno())
            self._assert_directories()
            if target.exists() or target.is_symlink():
                raise RunArtifactError("Checkpoint target already exists")
            os.replace(temporary, target)
        except (OSError, RunArtifactError) as error:
            self._failed = True
            if isinstance(error, RunArtifactError):
                raise
            raise RunArtifactError(f"Checkpoint ingest failed: {error}") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self._checkpoints[name] = {"sha256": digest.hexdigest(), "size": size,
                                   "origin_branch_id": origin_branch_id}
        return digest.hexdigest()

    def append(self, event: dict) -> None:
        if self._closed or self._failed:
            raise RunArtifactError("Recorder is closed or failed")
        if not isinstance(event, dict) or OWNED & event.keys():
            raise RunArtifactError("Recorder-owned event field supplied")
        try:
            item = _strict_load(_canonical(event))
            if "checkpoint_name" in item:
                name = _safe_name(item["checkpoint_name"])
                data = self._checkpoints.get(name)
                if data is None:
                    raise RunArtifactError("Checkpoint not ingested")
                if ("checkpoint_sha256" in item and item["checkpoint_sha256"] != data["sha256"]) \
                        or ("checkpoint_size" in item and item["checkpoint_size"] != data["size"]):
                    raise RunArtifactError("Checkpoint event conflicts with ingested file")
                item["checkpoint_sha256"] = data["sha256"]
                item["checkpoint_size"] = data["size"]
            item.update(sequence=self._chain.count,
                        previous_scientific_sha256=self._chain.previous,
                        run_metadata_sha256=self._chain.metadata_digest)
            item["scientific_sha256"] = sha256(_canonical(_scientific_event(item))).hexdigest()
            self._chain.check(item)
            line = _canonical(item) + b"\n"
            self._stream.write(line)
            self._stream.flush()
            self._raw_digest.update(line)
        except (OSError, RunArtifactError) as error:
            if isinstance(error, OSError):
                self._failed = True
                raise RunArtifactError(f"Event append failed: {error}") from error
            raise

    def _append_reference(self, event: dict) -> dict:
        """Return a claimed wire reference only after one complete successful append."""
        if self._closed or self._failed:
            raise RunArtifactError("Recorder is closed or failed")
        sequence = self.next_sequence
        if type(sequence) is not int or sequence < 0:
            raise RunArtifactError("Invalid append reference position")
        self.append(event)
        position = self.next_sequence
        if self._closed or self._failed or type(position) is not int or position != sequence + 1:
            raise RunArtifactError("Append reference boundary changed")
        return {"sequence": sequence, "scientific_sha256": self._chain.previous}

    def flush(self) -> None:
        if self._closed:
            raise RunArtifactError("Recorder is closed")
        self._stream.flush()
        os.fsync(self._stream.fileno())

    def append_state_anchor(self, anchor: dict) -> None:
        """Adapt a strict envelope without relaxing generic owned-field protection."""
        from .replay import validate_state_anchor

        try:
            data = validate_state_anchor(anchor)
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
        if data.pop("run_metadata_sha256") != self._chain.metadata_digest:
            raise RunArtifactError("Anchor metadata mismatch")
        _check_files(self.path, {"checkpoints": self._checkpoints})
        self.append({**data, "type": "state_anchor", "branch_id": data["origin_branch_id"],
                     "sim_ms": data["sim_tick"] / 10})

    def validate_prefix(self) -> ValidatedPrefix:
        """Validate a quiescent producer's durable bytes; no counters supply proof."""
        self.flush()
        self._assert_directories()
        return validate_prefix(self.path, run_kind=self.run_kind, metadata=self.metadata,
                               root_branch_id=self.root_branch_id, checkpoints=self._checkpoints)

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._failed or (self.run_kind in {"qualification", "confirmation"}
                                and not self._chain.result_seen) \
                    or not {"brain-before.npz", "brain-after.npz"} <= self._chain.seen_checkpoints \
                    or self._chain.seen_checkpoints != self._checkpoints.keys():
                raise RunArtifactError("Cannot seal incomplete checkpoint set")
            self.flush()
            manifest = {
                "format_version": FORMAT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "schema_sha256": _schema_digest(),
                "run_kind": self.run_kind,
                "root_branch_id": self.root_branch_id,
                "metadata": self.metadata,
                "run_metadata_sha256": self._chain.metadata_digest,
                "event_count": self._chain.count,
                "final_scientific_sha256": self._chain.previous,
                "events_sha256": self._raw_digest.hexdigest(),
                "checkpoints": self._checkpoints,
                "state_anchors": self._chain.anchors,
            }
            self._assert_directories()
            _check_files(self.path, manifest)
            target = self.path / "run.json"
            self._assert_directories()
            with tempfile.NamedTemporaryFile(dir=self.path, prefix=".run.", suffix=".tmp",
                                             delete=False) as writer:
                temporary = Path(writer.name)
                try:
                    writer.write(_canonical(manifest) + b"\n")
                    writer.flush()
                    os.fsync(writer.fileno())
                except Exception:
                    temporary.unlink(missing_ok=True)
                    raise
            self._assert_directories()
            os.replace(temporary, target)
        finally:
            self._stream.close()
            self._closed = True


def _digest_file(path: Path, *, max_bytes: int | None = None) -> tuple[str, int]:
    digest = sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024 if max_bytes is None
                                  else min(1024 * 1024, max_bytes - size + 1)):
            size += len(chunk)
            if max_bytes is not None and size > max_bytes:
                raise RunArtifactError("Event bytes exceed run read limit")
            digest.update(chunk)
    return digest.hexdigest(), size


def _read_manifest(path: Path, *, limits: RunReadLimits | None = None) -> tuple[dict, bytes]:
    if path.is_symlink() or path.is_junction() or not path.is_dir():
        raise RunArtifactError("Run path is not a sealed directory")
    manifest_path = path / "run.json"
    if manifest_path.is_symlink():
        raise RunArtifactError("Manifest symlink rejected")
    try:
        if limits is None:
            raw = manifest_path.read_bytes()
        else:
            with manifest_path.open("rb") as stream:
                raw = stream.read(limits.max_manifest_bytes + 1)
            if len(raw) > limits.max_manifest_bytes:
                raise RunArtifactError("Manifest bytes exceed run read limit")
    except OSError as error:
        raise RunArtifactError(f"Missing run seal: {error}") from error
    item = _strict_load(raw)
    if not isinstance(item, dict) or raw != _canonical(item) + b"\n":
        raise RunArtifactError("Noncanonical run manifest")
    required = {"format_version", "schema_version", "schema_sha256", "run_kind", "root_branch_id", "metadata",
                "run_metadata_sha256", "event_count", "final_scientific_sha256", "events_sha256", "checkpoints",
                "state_anchors"}
    if set(item) != required or item["format_version"] != FORMAT_VERSION \
            or item["schema_version"] != SCHEMA_VERSION \
            or item["schema_sha256"] != _schema_digest() \
            or not isinstance(item["run_kind"], str) \
            or item["run_kind"] not in {"pilot", "qualification", "confirmation"} \
            or not isinstance(item["root_branch_id"], str) or not item["root_branch_id"]:
        raise RunArtifactError("Manifest format or packaged schema mismatch")
    metadata = _metadata(item["metadata"], item["run_kind"])
    if item["run_metadata_sha256"] != _metadata_digest(item["run_kind"], item["root_branch_id"], metadata):
        raise RunArtifactError("Manifest metadata digest mismatch")
    if type(item["event_count"]) is not int or item["event_count"] < 0 \
            or any(not isinstance(item[name], str) or not DIGEST.fullmatch(item[name])
                   for name in ("final_scientific_sha256", "events_sha256")):
        raise RunArtifactError("Invalid manifest counts or digests")
    if limits is not None and item["event_count"] > limits.max_events:
        raise RunArtifactError("Declared event count exceeds run read limit")
    checkpoints = item["checkpoints"]
    if not isinstance(checkpoints, dict) or not {"brain-before.npz", "brain-after.npz"} <= checkpoints.keys():
        raise RunArtifactError("Missing reserved checkpoints")
    if limits is not None and len(checkpoints) > limits.max_checkpoints:
        raise RunArtifactError("Declared checkpoint count exceeds run read limit")
    for name, data in checkpoints.items():
        _safe_name(name)
        if not isinstance(data, dict) \
                or set(data) not in ({"sha256", "size", "origin_branch_id", "sim_ms", "checkpoint_sequence"},
                                     {"sha256", "size", "origin_branch_id", "sim_ms", "checkpoint_sequence", "sim_tick"}) \
                or not isinstance(data["sha256"], str) or not DIGEST.fullmatch(data["sha256"]) \
                or type(data["size"]) is not int or data["size"] < 0 \
                or not isinstance(data["origin_branch_id"], str) or not data["origin_branch_id"] \
                or type(data["checkpoint_sequence"]) is not int or data["checkpoint_sequence"] < 0 \
                or isinstance(data["sim_ms"], bool) or not isinstance(data["sim_ms"], (int, float)):
            raise RunArtifactError("Invalid checkpoint declaration")
        try:
            if not math.isfinite(float(data["sim_ms"])) or data["sim_ms"] < 0:
                raise RunArtifactError("Invalid checkpoint clock")
        except OverflowError as error:
            raise RunArtifactError("Invalid checkpoint clock") from error
        if "sim_tick" in data:
            from .replay import _clock, _integer
            try:
                _clock(data["sim_ms"], _integer(data["sim_tick"]))
            except ValueError as error:
                raise RunArtifactError(str(error)) from error
    _check_anchor_index(item["state_anchors"])
    return item, raw


def _check_anchor_index(index: object) -> None:
    from .replay import validate_state_anchor

    if type(index) is not dict:
        raise RunArtifactError("Invalid anchor inventory")
    ids = set()
    for digest, entry in index.items():
        if type(entry) is not dict or type(entry.get("event_sequence")) is not int \
                or entry["event_sequence"] < 0:
            raise RunArtifactError("Invalid anchor occurrence sequence")
        try:
            anchor = validate_state_anchor({key: value for key, value in entry.items()
                                            if key != "event_sequence"})
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
        if digest != anchor["state_anchor_sha256"] or anchor["anchor_id"] in ids:
            raise RunArtifactError("Duplicate or mismatched anchor inventory")
        ids.add(anchor["anchor_id"])


def _check_files(path: Path, manifest: dict, *, allow_later: bool = False,
                 limits: RunReadLimits | None = None) -> None:
    directory = path / "checkpoints"
    if directory.is_symlink() or directory.is_junction() or not directory.is_dir():
        raise RunArtifactError("Missing safe checkpoint directory")
    if limits is None:
        names = {entry.name for entry in directory.iterdir()}
    else:
        names = set()
        with os.scandir(directory) as entries:
            for count, entry in enumerate(entries, 1):
                if count > limits.max_checkpoints:
                    raise RunArtifactError("Checkpoint entries exceed run read limit")
                names.add(entry.name)
    if (not manifest["checkpoints"].keys() <= names if allow_later
            else names != manifest["checkpoints"].keys()):
        raise RunArtifactError("Missing or extra checkpoint file")
    for name, data in manifest["checkpoints"].items():
        target = directory / name
        if target.is_symlink() or not target.is_file() or _digest_file(target) != (data["sha256"], data["size"]):
            raise RunArtifactError(f"Checkpoint digest mismatch: {name}")


def _raw_events(path: Path, *, count: int | None = None,
                byte_length: int | None = None,
                limits: RunReadLimits | None = None) -> Iterator[dict]:
    """Raw bounded streaming under a validated context; never recursively scan."""
    events_path = path / "events.jsonl"
    if events_path.is_symlink() or not events_path.is_file():
        raise RunArtifactError("Missing safe event stream")
    with events_path.open("rb") as stream:
        remaining = byte_length
        emitted = 0
        consumed = 0
        while (remaining is None or remaining > 0) and (count is None or emitted < count):
            read_size = -1 if remaining is None else remaining
            if limits is not None:
                read_size = min(limits.max_event_line_bytes + 1,
                                limits.max_events_bytes - consumed + 1,
                                read_size if read_size >= 0 else limits.max_event_line_bytes + 1)
            line = stream.readline(read_size)
            if not line:
                if remaining is not None and remaining > 0 or count is not None and emitted < count:
                    raise RunArtifactError("Fixed event prefix truncated")
                break
            consumed += len(line)
            if limits is not None:
                if len(line) > limits.max_event_line_bytes:
                    raise RunArtifactError("Event line bytes exceed run read limit")
                if consumed > limits.max_events_bytes:
                    raise RunArtifactError("Event bytes exceed run read limit")
                if emitted >= limits.max_events:
                    raise RunArtifactError("Event count exceeds run read limit")
            if remaining is not None:
                remaining -= len(line)
            if not line.endswith(b"\n"):
                raise RunArtifactError("Truncated event line")
            event = _strict_load(line)
            if not isinstance(event, dict) or line != _canonical(event) + b"\n":
                raise RunArtifactError("Noncanonical event bytes")
            emitted += 1
            yield event


def _digest_boundary(path: Path, byte_length: int) -> str:
    if path.is_symlink() or not path.is_file():
        raise RunArtifactError("Missing safe event stream")
    digest = sha256()
    with path.open("rb") as stream:
        remaining = byte_length
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise RunArtifactError("Fixed event prefix truncated")
            remaining -= len(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def _scan_chain(path: Path, manifest: dict, *, byte_length: int | None = None,
                limits: RunReadLimits | None = None) -> Iterator[dict]:
    from .replay import _PrefixProjection

    chain = _Chain(manifest["root_branch_id"], manifest["metadata"],
                   _strict_load(_canonical(manifest["checkpoints"])), manifest["run_kind"])
    chain.projection = _PrefixProjection(chain.metadata, chain.metadata_digest)
    raw_digest = sha256()
    for event in _raw_events(path, byte_length=byte_length, limits=limits):
        # _raw_events has already checked exact canonical bytes including LF.
        raw_digest.update(_canonical(event) + b"\n")
        chain.check(event)
        yield event
    if chain.seen_checkpoints != manifest["checkpoints"].keys():
        raise RunArtifactError("Unrepresented checkpoint inventory")
    chain.scanned_raw_sha256 = raw_digest.hexdigest()
    return chain


def _scan(path: Path, manifest: dict, *, limits: RunReadLimits | None = None) -> Iterator[dict]:
    chain = yield from _scan_chain(path, manifest, limits=limits)
    if chain.count != manifest["event_count"] or chain.previous != manifest["final_scientific_sha256"] \
            or chain.scanned_raw_sha256 != manifest["events_sha256"] \
            or (manifest["run_kind"] in {"qualification", "confirmation"} and not chain.result_seen) \
            or _canonical(chain.checkpoints) != _canonical(manifest["checkpoints"]) \
            or _canonical(chain.anchors) != _canonical(manifest["state_anchors"]):
        raise RunArtifactError("Event stream count, chain or raw digest mismatch")
    if (path / "events.jsonl").is_symlink() \
            or _digest_file(path / "events.jsonl", max_bytes=None if limits is None
                            else limits.max_events_bytes)[0] != manifest["events_sha256"]:
        raise RunArtifactError("Event stream changed during scan")


@dataclass(frozen=True)
class _ReplayAttestation:
    artifact_bytes: bytes
    occurrences: tuple[str, ...]
    qualification_context_bytes: bytes | None = field(default=None, init=False, repr=False)
    _issuer: object = field(default=None, init=False, repr=False, compare=False)
    _owner: weakref.ReferenceType | None = field(default=None, init=False, repr=False, compare=False)


_NATIVE_ISSUER = object()


def _issued_attestation(value) -> _ReplayAttestation:
    """Supported-API issuance belongs to this exact result, never equal bytes alone."""
    if type(value) not in (VerifiedRun, ValidatedPrefix):
        raise RunArtifactError("Native proof requires a genuine result object")
    proof = value._attestation
    if (type(proof) is not _ReplayAttestation or proof._issuer is not _NATIVE_ISSUER
            or type(proof._owner) is not weakref.ReferenceType or proof._owner() is not value):
        raise RunArtifactError("Native proof was not issued for this result object")
    return proof


def _qualification_context(engine, metadata: dict) -> bytes:
    """Capture checked native maps before any source restore, retaining only bytes."""
    import ctypes
    import numpy as np
    from ..engine import FlyEngine
    from ..neural.brain import MemoryBrain
    from ..neural.visual import VisualMemoryBrain
    from ..neural import checkpoint
    from .replay import _identity

    if not isinstance(engine, FlyEngine) or not isinstance(engine.brain, VisualMemoryBrain):
        raise RunArtifactError("Qualification requires a compatible isolated native visual FlyEngine")
    brain = engine.brain
    if (not isinstance(brain.library, ctypes.CDLL) or not isinstance(brain.advance, ctypes._CFuncPtr)
            or brain.advance is not brain.library.memory_advance):
        raise RunArtifactError("Qualification requires the real native memory entrypoint")
    identity = _identity(engine.identity())
    if _canonical(identity) != _canonical(metadata["engine_identity"]):
        raise RunArtifactError("Qualification engine identity mismatch")
    brain.assert_model_provenance_locked()
    # Recompute from the native implementations, not a producer's overridden
    # method returning cached declarations. Real visual subclasses/extensions
    # remain supported; their declared additional configuration is preserved.
    provenance = MemoryBrain.model_provenance(brain)
    configuration = VisualMemoryBrain.configuration_signature(brain)
    if (_canonical(provenance) != _canonical(identity["model_provenance"])
            or any(_canonical(value) != _canonical(provenance["configuration_sha256"].get(name))
                   for name, value in configuration.items())):
        raise RunArtifactError("Qualification live model provenance mismatch")
    n = brain.n
    if (type(n) is not int or n <= 0 or n != brain._native_population_size
            or n != brain._locked_population_size or type(brain.dt) is not float or brain.dt != 0.1):
        raise RunArtifactError("Qualification native population/dt mismatch")

    def array(value, name, shape, dtype=None):
        if (type(value) is not np.ndarray or value.shape != shape
                or (dtype is not None and (value.dtype != np.dtype(dtype) or not value.flags.c_contiguous))):
            raise RunArtifactError(f"Qualification native array mismatch: {name}")
        return value

    def indices(value, name, limit):
        array(value, name, (len(value),))
        if (value.dtype.kind not in "iu" or value.dtype.itemsize not in (1, 2, 4, 8)
                or np.any(value < 0) or np.any(value >= limit) or len(np.unique(value)) != len(value)):
            raise RunArtifactError(f"Qualification index map mismatch: {name}")
        return value

    ids = array(brain.ids, "ids", (n,), np.int64)
    ptr = array(brain.ptr, "ptr", (n + 1,), np.int64)
    post = array(brain.post, "post", (len(brain.post),), np.int32)
    weight = array(brain.weight, "weight", post.shape, np.float32)
    if (ptr[0] != 0 or ptr[-1] != len(post) or np.any(ptr[1:] < ptr[:-1])
            or np.any(post < 0) or np.any(post >= n)):
        raise RunArtifactError("Qualification CSR map mismatch")
    groups = vars(engine.groups)
    if set(groups) != set(identity["neural_groups"]):
        raise RunArtifactError("Qualification neural group names mismatch")
    for name, values in groups.items():
        indices(values, name, n)
        if not len(values) or values.tolist() != identity["neural_groups"][name]:
            raise RunArtifactError("Qualification live neural groups mismatch")

    circuit = brain.circuit
    edges = array(circuit["edges"], "edges", (len(circuit["edges"]),), np.int64)
    indices(edges, "edges", len(post))
    pre = array(circuit["pre"], "pre", edges.shape, np.int32)
    if not np.array_equal(pre, np.searchsorted(ptr, edges, side="right") - 1):
        raise RunArtifactError("Qualification circuit pre differs from CSR ordering")
    kc = indices(circuit["kc"], "kc", n)
    kc_mask = array(circuit["kc_mask"], "kc_mask", (n,), np.uint8)
    if (np.any(kc_mask > 1) or not np.array_equal(np.flatnonzero(kc_mask), np.sort(kc))
            or not np.array_equal(np.sort(kc), np.sort(groups["kc"])) or not np.isin(pre, kc).all()):
        raise RunArtifactError("Qualification KC group/mask/pre mismatch")
    dan = indices(circuit["dan"], "dan", n)
    inverse = array(circuit["dan_index"], "dan_index", (n,), np.int8)
    if (len(dan) > 128 or np.any(inverse < -1)
            or not np.array_equal(np.flatnonzero(inverse != -1), np.sort(dan))
            or not np.array_equal(inverse[dan], np.arange(len(dan)))
            or not np.isin(groups["pam11"], dan).all() or not np.isin(groups["ppl101"], dan).all()):
        raise RunArtifactError("Qualification ordered DAN inverse/sentinel mismatch")
    gain = array(circuit["gain"], "gain", (len(dan), len(edges)), np.float32)
    if not np.isfinite(gain).all():
        raise RunArtifactError("Qualification nonfinite DAN gains")
    modulation_mask = array(brain.modulation_mask, "modulation_mask", (n,), np.uint8)
    if np.any(modulation_mask > 1):
        raise RunArtifactError("Qualification modulation mask mismatch")
    for name, shape, dtype in (("rest", (n,), np.float32), ("tonic", (n,), np.float32),
                               ("dan_baseline_hz", dan.shape, np.float64)):
        if not np.isfinite(array(getattr(brain, name), name, shape, dtype)).all():
            raise RunArtifactError(f"Qualification nonfinite static array: {name}")
    baseline = array(brain.baseline_plastic, "baseline_plastic", edges.shape, np.float32)
    brain._validate_candidate_checkpoint_registration()
    arrays = {name: getattr(brain, name) for name in ["weight", *brain.fields]}
    # The independent native descriptors protect pointer arrays even if both
    # public registration containers were edited. Registered extensions keep
    # their real layouts, without invented destination/placeholder arrays.
    for name, shape, dtype in brain._native_checkpoint_schema:
        array(arrays[name], name, shape, dtype)
    for name in ("memory_u", "memory_w", "rate_kc"):
        array(arrays[name], name, edges.shape, np.float64)
    array(arrays["rate_dan"], "rate_dan", dan.shape, np.float64)
    checkpoint._validate_numeric_arrays(arrays, checkpoint.HASH_CHUNK_BYTES)
    if (type(brain.cursor) is not int or brain.cursor != 0
            or type(brain.total_spikes) is not int or brain.total_spikes != 0
            or type(brain.sim_ms) not in (int, float) or brain.sim_ms != 0
            or type(brain.weights_frozen) is not bool or brain.weights_frozen):
        raise RunArtifactError("Qualification context requires fresh initial clock/counters")
    checkpoint.validate_native_state(arrays, n, brain.cursor)
    if (any(np.any(arrays[name] != 0) for name in
            ("memory_u", "memory_w", "rate_kc", "rate_dan", "counts", "queue_count"))
            or checkpoint.raw_array_sha256(weight) != identity["model_provenance"]["configuration_sha256"]["initial_weight"]
            or not np.array_equal(baseline, weight[edges])):
        raise RunArtifactError("Qualification initial weights/memory/baseline mismatch")
    maps = {}
    for name in ("mbon11", "mbon07"):
        target = groups[name]
        positions = np.flatnonzero(np.isin(post[edges], target))
        selected = edges[positions]
        candidate_kc = np.unique(pre[positions])
        maps[name] = {
            "target_indices": target.tolist(), "candidate_positions": positions.tolist(),
            "candidate_edge_indices": selected.tolist(),
            "candidate_edge_pre_source_ids": [str(value) for value in ids[pre[positions]]],
            "candidate_edge_post_source_ids": [str(value) for value in ids[post[selected]]],
            "candidate_kc_indices": candidate_kc.tolist(),
            "candidate_kc_source_ids": [str(value) for value in ids[candidate_kc]],
            "baseline_plastic": baseline[positions].tolist(),
        }
    brain.assert_model_provenance_locked()
    schema = {name: {"dtype": value.dtype.str, "shape": list(value.shape)} for name, value in arrays.items()}
    checkpoint._checkpoint_schema(schema)
    return _canonical({
        "context_version": "qualification-map-context/v1", "engine_identity": identity, "n": n,
        "checkpoint_schema": schema,
        "candidate_maps": maps, "dan_indices": dan.tolist(), "dan_source_ids": [str(value) for value in ids[dan]],
    })


def _qualification_source_binding(context: dict) -> None:
    from ..neural import checkpoint

    if _canonical(checkpoint.model_fingerprint()) != _canonical(context["engine_identity"]["model_provenance"]["model_fingerprint"]):
        raise RunArtifactError("Qualification context packaged source fingerprint changed")


def _verified_qualification_context(value) -> dict:
    """Engine-free intake of immutable, owner-bound native map evidence."""
    proof = _issued_attestation(value)
    # Explicit concrete accessors preserve their different prefix/seal policies.
    if type(value) is ValidatedPrefix:
        ValidatedPrefix.replay_attested_state_anchors.fget(value)
        manifest = ValidatedPrefix.manifest.fget(value)
    else:
        VerifiedRun.replay_attested_state_anchors.fget(value)
        manifest = VerifiedRun.manifest.fget(value)
    if manifest["run_kind"] != "qualification" or type(proof.qualification_context_bytes) is not bytes:
        raise RunArtifactError("Native qualification context is unavailable")
    context = _strict_load(proof.qualification_context_bytes)
    required = {"context_version", "engine_identity", "n", "checkpoint_schema", "candidate_maps",
                "dan_indices", "dan_source_ids"}
    if (type(context) is not dict or set(context) != required
            or context["context_version"] != "qualification-map-context/v1"
            or type(context["n"]) is not int or context["n"] <= 0
            or _canonical(context) != proof.qualification_context_bytes
            or _canonical(context["engine_identity"]) != _canonical(manifest["metadata"]["engine_identity"])):
        raise RunArtifactError("Invalid qualification context identity/shape")
    from ..neural.checkpoint import _checkpoint_schema

    try:
        _checkpoint_schema(context["checkpoint_schema"])
    except (TypeError, ValueError) as error:
        raise RunArtifactError("Invalid qualification checkpoint schema") from error
    if "weight" not in context["checkpoint_schema"] or type(context["candidate_maps"]) is not dict \
            or set(context["candidate_maps"]) != {"mbon11", "mbon07"}:
        raise RunArtifactError("Invalid qualification map/schema names")
    map_keys = {"target_indices", "candidate_positions", "candidate_edge_indices", "candidate_edge_pre_source_ids",
                "candidate_edge_post_source_ids", "candidate_kc_indices", "candidate_kc_source_ids", "baseline_plastic"}
    for name, mapping in context["candidate_maps"].items():
        if (type(mapping) is not dict or set(mapping) != map_keys
                or any(type(item) is not list for item in mapping.values())
                or mapping["target_indices"] != context["engine_identity"]["neural_groups"][name]
                or any(type(index) is not int or index < 0 for key in
                    ("target_indices", "candidate_positions", "candidate_edge_indices", "candidate_kc_indices") for index in mapping[key])
                or any(type(source) is not str for key in ("candidate_edge_pre_source_ids", "candidate_edge_post_source_ids",
                    "candidate_kc_source_ids") for source in mapping[key])
                or any(not _finite_number(weight, allow_negative=True) for weight in mapping["baseline_plastic"])
                or len({len(mapping[key]) for key in ("candidate_positions", "candidate_edge_indices",
                    "candidate_edge_pre_source_ids", "candidate_edge_post_source_ids", "baseline_plastic")}) != 1
                or len(mapping["candidate_kc_indices"]) != len(mapping["candidate_kc_source_ids"])):
            raise RunArtifactError("Invalid qualification candidate map shape")
    dan, sources = context["dan_indices"], context["dan_source_ids"]
    if (type(dan) is not list or type(sources) is not list or len(dan) != len(sources)
            or any(type(index) is not int or not 0 <= index < context["n"] for index in dan)
            or len(set(dan)) != len(dan) or any(type(source) is not str for source in sources)):
        raise RunArtifactError("Invalid qualification DAN map shape")
    _qualification_source_binding(context)
    return context


@dataclass(frozen=True)
class ValidatedPrefix:
    """Fixed durable bytes, not a seal. Later bytes/files are outside its proof.

    Producers must be quiescent while validating/replaying. Rechecks bind every
    represented file and the exact first byte boundary, ignoring later tails.
    All raw integrity bindings remain private and outside scientific projections.
    """
    path: Path
    _context_bytes: bytes
    _byte_length: int
    _raw_sha256: str
    _directory_ids: tuple[tuple[int, int], tuple[int, int]]
    _attestation: _ReplayAttestation | None = field(default=None, init=False, repr=False)

    @property
    def verification_mode(self) -> str:
        if self._attestation is None:
            return "integrity-only"
        ValidatedPrefix.replay_attested_state_anchors.fget(self)
        return "native-replay"

    @property
    def manifest(self) -> dict:
        return _strict_load(self._context_bytes)

    @property
    def scientific_prefix(self) -> dict:
        context = self.manifest
        return {"event_count": context["event_count"], "final_sequence": context["event_count"] - 1,
                "final_scientific_sha256": context["final_scientific_sha256"]}

    def _check_binding(self) -> None:
        context = self.manifest
        if context["schema_sha256"] != _schema_digest():
            raise RunArtifactError("Prefix packaged schema changed")
        if (_directory_identity(self.path), _directory_identity(self.path / "checkpoints")) \
                != self._directory_ids:
            raise RunArtifactError("Prefix directory substituted")
        _check_files(self.path, context, allow_later=True)
        if _digest_boundary(self.path / "events.jsonl", self._byte_length) != self._raw_sha256:
            raise RunArtifactError("Fixed event prefix changed")

    def _attestation_binding(self) -> bytes:
        return self._context_bytes + self._byte_length.to_bytes(8, "little") + bytes.fromhex(self._raw_sha256)

    @property
    def replay_attested_state_anchors(self) -> frozenset[str]:
        if self._attestation is None:
            return frozenset()
        _issued_attestation(self)
        self._check_binding()
        if self._attestation.artifact_bytes != self._attestation_binding():
            raise RunArtifactError("Replay attestation does not bind prefix")
        return frozenset(self._attestation.occurrences)

    def iter_events(self) -> Iterator[dict]:
        self._check_binding()
        context = self.manifest
        chain = yield from _scan_chain(self.path, context, byte_length=self._byte_length)
        if chain.count != context["event_count"] or chain.previous != context["final_scientific_sha256"] \
                or chain.scanned_raw_sha256 != self._raw_sha256 \
                or _canonical(chain.anchors) != _canonical(context["state_anchors"]):
            raise RunArtifactError("Fixed prefix inventory or endpoint mismatch")
        self._check_binding()


def validate_prefix(path: str | Path, *, run_kind: str, metadata: dict,
                    root_branch_id: str, checkpoints: dict) -> ValidatedPrefix:
    """Verify the current durable prefix from disk with explicit producer context."""
    target = Path(path)
    directory_ids = (_directory_identity(target), _directory_identity(target / "checkpoints"))
    if type(run_kind) is not str or run_kind not in {"pilot", "qualification", "confirmation"} \
            or type(root_branch_id) is not str or not root_branch_id:
        raise RunArtifactError("Invalid prefix run context")
    if type(checkpoints) is not dict:
        raise RunArtifactError("Invalid prefix checkpoint inventory")
    context = {"schema_sha256": _schema_digest(), "run_kind": run_kind, "root_branch_id": root_branch_id,
               "metadata": _metadata(metadata, run_kind),
               "checkpoints": _strict_load(_canonical(checkpoints))}
    for name, data in context["checkpoints"].items():
        _safe_name(name)
        required = {"sha256", "size", "origin_branch_id"}
        optional = {"sim_ms", "checkpoint_sequence", "sim_tick"}
        if type(data) is not dict or not required <= data.keys() or set(data) - required - optional \
                or type(data.get("size")) is not int or data["size"] < 0 \
                or type(data.get("sha256")) is not str or not DIGEST.fullmatch(data["sha256"]) \
                or type(data.get("origin_branch_id")) is not str or not data["origin_branch_id"]:
            raise RunArtifactError("Invalid prefix checkpoint inventory")
        from .replay import _clock, _integer
        try:
            for key in ("checkpoint_sequence", "sim_tick"):
                if key in data:
                    _integer(data[key])
            if "sim_ms" in data and not _finite_number(data["sim_ms"]):
                raise ValueError("Invalid inventory clock")
            if "sim_tick" in data and "sim_ms" in data:
                _clock(data["sim_ms"], data["sim_tick"])
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
    _check_files(target, context)
    boundary = (target / "events.jsonl").stat().st_size
    raw_digest = _digest_boundary(target / "events.jsonl", boundary)
    iterator = _scan_chain(target, context, byte_length=boundary)
    while True:
        try:
            next(iterator)
        except StopIteration as result:
            chain = result.value
            break
    context.update(run_metadata_sha256=chain.metadata_digest, event_count=chain.count,
                   final_scientific_sha256=chain.previous, state_anchors=chain.anchors)
    # Reconstruct occurrence inventory from event bytes, never producer counters.
    context["checkpoints"] = chain.checkpoints
    result = ValidatedPrefix(target, _canonical(context), boundary, raw_digest, directory_ids)
    for _ in result.iter_events():
        pass
    return result


@dataclass(frozen=True)
class VerifiedRun:
    path: Path
    _manifest_bytes: bytes
    _limits: RunReadLimits | None = field(default=None, repr=False)
    _attestation: _ReplayAttestation | None = field(default=None, init=False, repr=False)

    @property
    def verification_mode(self) -> str:
        if self._attestation is None:
            return "integrity-only"
        VerifiedRun.replay_attested_state_anchors.fget(self)
        return "native-replay"

    @property
    def replay_attested_state_anchors(self) -> frozenset[str]:
        if self._attestation is None:
            return frozenset()
        _issued_attestation(self)
        manifest, raw = _read_manifest(self.path, limits=self._limits)
        if raw != self._manifest_bytes or self._attestation.artifact_bytes != raw:
            raise RunArtifactError("Manifest changed since replay verification")
        _check_files(self.path, manifest, limits=self._limits)
        if (self.path / "events.jsonl").is_symlink() \
                or _digest_file(self.path / "events.jsonl", max_bytes=None if self._limits is None
                                else self._limits.max_events_bytes)[0] != manifest["events_sha256"]:
            raise RunArtifactError("Events changed since replay verification")
        return frozenset(self._attestation.occurrences)

    @property
    def manifest(self) -> dict:
        return _strict_load(self._manifest_bytes)

    def iter_events(self) -> Iterator[dict]:
        manifest, raw = _read_manifest(self.path, limits=self._limits)
        if raw != self._manifest_bytes:
            raise RunArtifactError("Manifest changed since verification")
        _check_files(self.path, manifest, limits=self._limits)
        yield from _scan(self.path, manifest, limits=self._limits)
        current, raw = _read_manifest(self.path, limits=self._limits)
        if raw != self._manifest_bytes:
            raise RunArtifactError("Manifest changed during iteration")
        _check_files(self.path, current, limits=self._limits)


def verify_run(path: str | Path, *, limits: RunReadLimits | None = None) -> VerifiedRun:
    """Verify a complete artifact without retaining its events in memory."""
    if limits is not None and type(limits) is not RunReadLimits:
        raise RunArtifactError("Invalid run read limits policy")
    target = Path(path)
    try:
        manifest, raw = _read_manifest(target, limits=limits)
        _check_files(target, manifest, limits=limits)
        for _ in _scan(target, manifest, limits=limits):
            pass
        if _read_manifest(target, limits=limits)[1] != raw:
            raise RunArtifactError("Manifest changed during verification")
        _check_files(target, manifest, limits=limits)
        return VerifiedRun(target, raw, limits)
    except OSError as error:
        raise RunArtifactError(f"Unreadable run artifact: {error}") from error


def _replay_verified(value: VerifiedRun | ValidatedPrefix, *, engine_factory: Callable) -> None:
    from .replay import _replay_black_retention

    engine = None
    context_bytes = None
    manifest = value.manifest
    anchors = manifest["state_anchors"]
    try:
        if manifest["run_kind"] == "qualification":
            engine = engine_factory()
            context_bytes = _qualification_context(engine, manifest["metadata"])
        for entry in anchors.values():
            anchor = {key: item for key, item in entry.items() if key != "event_sequence"}
            # Fully restore each occurrence, even when state content digests agree.
            engine = _replay_black_retention(anchor,
                source_path=value.path / "checkpoints" / anchor["source_occurrence"]["checkpoint_name"],
                engine_factory=engine_factory, engine=engine)
        for _ in value.iter_events():
            pass
        if context_bytes is not None:
            _qualification_source_binding(_strict_load(context_bytes))
    except (ValueError, OSError, RuntimeError, TypeError, AttributeError, IndexError, KeyError) as error:
        raise RunArtifactError(f"Actual anchor replay verification failed: {error}") from error
    binding = value._manifest_bytes if isinstance(value, VerifiedRun) else value._attestation_binding()
    proof = _ReplayAttestation(binding, tuple(sorted(anchors)))
    object.__setattr__(proof, "qualification_context_bytes", context_bytes)
    object.__setattr__(proof, "_owner", weakref.ref(value))
    object.__setattr__(proof, "_issuer", _NATIVE_ISSUER)
    object.__setattr__(value, "_attestation", proof)


def verify_replay_run(path: str | Path, *, engine_factory: Callable) -> VerifiedRun:
    """Ordinary whole-artifact validation, actual isolated replay, final recheck."""
    value = verify_run(path)
    _replay_verified(value, engine_factory=engine_factory)
    return value


def verify_replay_prefix(prefix: ValidatedPrefix, *, engine_factory: Callable) -> ValidatedPrefix:
    """Validate/replay a fixed prefix and return a separately attested frozen value."""
    if type(prefix) is not ValidatedPrefix:
        raise RunArtifactError("Replay requires a validated fixed prefix")
    for _ in prefix.iter_events():
        pass
    value = ValidatedPrefix(prefix.path, prefix._context_bytes, prefix._byte_length,
                            prefix._raw_sha256, prefix._directory_ids)
    _replay_verified(value, engine_factory=engine_factory)
    return value
