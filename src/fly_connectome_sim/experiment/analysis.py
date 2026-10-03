"""Frozen, fail-closed MBON11 assay configuration and evidence analysis.

``reduce_assay_evidence`` is pure so an executor can run the identical checks
before sealing its event stream. Only ``analyze_assay`` accepts a VerifiedRun.
All times in response/intervention evidence use integer 0.1 ms ticks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
import json
import math
import re
from typing import Iterable, Literal

import numpy as np

from ..engine import _rgb_input_sha256
from .qualification import (GRID, RESPONSE_WINDOWS, RETENTION_CANDIDATES_MS,
                            QUALIFICATION_SEEDS, CONFIRMATION_SEEDS,
                            PULSE_DURATION_MS, CURRENT_MV,
                            UNPAIRED_SEPARATION_MS, GridConfiguration,
                            _training_timeline)
from .recorder import ValidatedPrefix, VerifiedRun
from .stimuli import AssayStimuli


class AnalysisError(ValueError):
    """A qualification or frozen-configuration contract cannot be trusted."""


CONFIG_VERSION = "mbon11-frozen-assay/v1"
ANALYSIS_VERSION = "mbon11-causal-analysis/v1"
QUALIFICATION_VERSION = "mbon11-qualification/v1"
EVIDENCE_VERSION = "mbon11-response/v1"
INTERVENTION_VERSION = "candidate-memory-replacement/v1"
TRAINING_VERSION = "associative-training/v1"
AGGREGATION = "raw-bin-mean-rate/v1"
CONDITIONS = ("paired", "frozen_plasticity", "no_external_dan",
              "temporally_unpaired", "matched_reference", "necessity",
              "sufficiency", "sham")
INTERVENTIONS = ("necessity", "sufficiency", "sham")
CONTROLS = ("matched_reference", "frozen_plasticity", "no_external_dan",
            "temporally_unpaired")
STIMULI = ("A", "B", "C")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
CONFIG_FIELDS = {
    "version", "analysis_version", "qualification_version", "aggregation",
    "qualification_artifact", "qualification_family", "qualification_seeds",
    "qualification_protocol_version", "confirmation_family", "confirmation_seeds",
    "confirmation_protocol_version", "stimulus_version", "engine_identity",
    "qualification_input_sha256", "confirmation_input_sha256", "candidate_identity",
    "mbon11_population_size", "selected_configuration", "response_window",
    "retention_ms", "retention_times_ms", "expected_effect_sign", "conditions",
    "interventions", "exclusions", "replay_resolution_hz",
    "max_abs_control_delta_hz", "dynamic_range_hz", "effect_floor_hz",
    "one_spike_floor_hz", "floor_sources", "digest",
}
ARTIFACT_FIELDS = {"schema_sha256", "run_metadata_sha256", "events_sha256",
                   "final_scientific_sha256"}
RESPONSE_FIELDS = {
    "evidence_version", "branch_id", "seed", "paired_identity", "presentation_order",
    "retention_ms", "condition", "phase", "stimulus", "candidate_identity",
    "population", "population_size", "cs_onset_tick", "bins", "rate_hz",
    "training_id", "training_start_tick", "association_t0_tick",
    "retention_reference_tick", "training_end_tick",
    "training_end_checkpoint_sha256", "retention_source_checkpoint_sha256",
    "last_visual_end_tick", "last_external_dan_end_tick",
    "training_visual_exposure_ticks", "unpaired_nearest_cs_boundary_ticks",
    "passive_decay_ticks", "input_sha256", "black_sha256",
    "endogenous_dan_spikes", "learning", "external_stimulation",
    "intervention_id",
}
INTERVENTION_FIELDS = {
    "intervention_version", "intervention_id", "seed", "paired_identity",
    "presentation_order", "condition", "candidate_identity", "donor_role",
    "recipient_role", "donor_training_end_tick", "recipient_training_end_tick",
    "donor_checkpoint_sha256", "recipient_checkpoint_sha256",
    "parent_checkpoint_sha256", "post_intervention_checkpoint_sha256",
    "donor_training_id", "recipient_training_id",
    "donor_candidate_memory_sha256", "recipient_candidate_memory_before_sha256",
    "recipient_candidate_memory_after_sha256", "noncandidate_state_before_sha256",
    "noncandidate_state_after_sha256", "replaced_components",
    "complete_replacement",
}
TRAINING_FIELDS = {
    "training_version", "training_id", "branch_id", "seed", "paired_identity",
    "presentation_order", "condition", "candidate_identity", "baseline_tick",
    "baseline_checkpoint_sha256", "training_start_tick", "association_t0_tick",
    "retention_reference_tick", "training_end_tick", "training_end_checkpoint_sha256",
    "last_visual_end_tick", "last_external_dan_end_tick",
    "training_visual_exposure_ticks", "unpaired_nearest_cs_boundary_ticks",
    "candidate_memory_sha256", "noncandidate_state_sha256", "segments",
}
ORDINARY_CONDITIONS = ("paired", "frozen_plasticity", "no_external_dan",
                       "temporally_unpaired", "matched_reference")
SEGMENT_FIELDS = {"start_tick", "end_tick", "stimulus", "external_stimulation",
                  "current_mv", "learning", "input_sha256"}
MAX_TICK = 10 ** 12


def _canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise AnalysisError("invalid_json") from error


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise AnalysisError("duplicate_json_key")
        result[key] = value
    return result


def _load(raw: str | bytes) -> object:
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              AnalysisError("nonfinite_json")))
    except AnalysisError:
        raise
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise AnalysisError("invalid_json") from error


def _number(value: object, *, minimum: float | None = None) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        finite = math.isfinite(value)
    except OverflowError:
        return False
    return finite and (minimum is None or value >= minimum)


def _int(value: object, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _digest(value: object) -> bool:
    return type(value) is str and DIGEST.fullmatch(value) is not None


def _same_number(a: object, b: object) -> bool:
    return _number(a) and _number(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def _valid_engine_identity(identity: object, population: int) -> bool:
    """Match the engine's complete nested, self-hashed identity contract."""
    if (not isinstance(identity, dict)
            or set(identity) != {"version", "model_provenance", "neural_groups", "sha256"}
            or identity["version"] != "fly-engine/v1"
            or not _digest(identity["sha256"])):
        return False
    projection = {name: value for name, value in identity.items() if name != "sha256"}
    try:
        engine_json = json.dumps(projection, sort_keys=True, separators=(",", ":"),
                                 allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    if sha256(engine_json.encode("utf-8")).hexdigest() != identity["sha256"]:
        return False
    groups = identity["neural_groups"]
    if (not isinstance(groups, dict) or not isinstance(groups.get("mbon11"), list)
            or len(groups["mbon11"]) != population
            or any(not _int(index) for index in groups["mbon11"])
            or len(set(groups["mbon11"])) != population):
        return False
    provenance = identity["model_provenance"]
    required = {"model", "model_fingerprint", "build", "eta", "parameters",
                "graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256",
                "plastic_edges_sha256", "configuration_sha256"}
    if not isinstance(provenance, dict) or set(provenance) != required \
            or not isinstance(provenance["model"], str) or not provenance["model"] \
            or not _number(provenance["eta"], minimum=0) \
            or not isinstance(provenance["parameters"], dict) \
            or not isinstance(provenance["configuration_sha256"], dict) \
            or not provenance["configuration_sha256"]:
        return False
    if any(not _digest(provenance[name]) for name in (
        "graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256",
        "plastic_edges_sha256",
    )):
        return False
    fingerprint = provenance["model_fingerprint"]
    if (not isinstance(fingerprint, dict)
            or set(fingerprint) != {"version", "sources_sha256", "sha256"}
            or fingerprint["version"] != "model-source/v1"
            or not isinstance(fingerprint["sources_sha256"], dict)
            or not fingerprint["sources_sha256"]
            or any(not _digest(value) for value in fingerprint["sources_sha256"].values())
            or not _digest(fingerprint["sha256"])):
        return False
    fingerprint_payload = {name: value for name, value in fingerprint.items() if name != "sha256"}
    try:
        fingerprint_json = json.dumps(fingerprint_payload, sort_keys=True,
                                      separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    if sha256(fingerprint_json.encode("utf-8")).hexdigest() \
            != fingerprint["sha256"]:
        return False
    build = provenance["build"]
    if (not isinstance(build, dict)
            or set(build) != {"model", "source_sha256", "compiler", "flags",
                              "library", "binary_sha256"}
            or build["model"] != provenance["model"]
            or any(not isinstance(build[name], str) or not build[name]
                   for name in ("compiler", "library"))
            or any(not _digest(build[name]) for name in ("source_sha256", "binary_sha256"))
            or not isinstance(build["flags"], list)
            or any(not isinstance(flag, str) for flag in build["flags"])):
        return False
    return True


@lru_cache(maxsize=2)
def _expected_inputs(family: str) -> dict:
    seeds = QUALIFICATION_SEEDS if family == "qualification" else CONFIRMATION_SEEDS
    black = _rgb_input_sha256(np.zeros((32, 32, 3), dtype=np.uint8))
    return {
        str(seed): {
            **{stimulus: _rgb_input_sha256(
                AssayStimuli(seed=seed, family=family).frame(stimulus))
                for stimulus in STIMULI},
            "black": black,
        }
        for seed in seeds
    }


def _qualification_factors() -> dict:
    return {
        "grid": [asdict(item) for item in GRID],
        "response_windows": [asdict(item) for item in RESPONSE_WINDOWS],
        "retention_ms": list(RETENTION_CANDIDATES_MS),
        "paired_identity": ["A", "B"],
        "presentation_order": ["AB", "BA"],
        "side": "center",
        "color_assignment": "fixed",
    }


def _validate_config(data: object) -> dict:
    if not isinstance(data, dict) or set(data) != CONFIG_FIELDS:
        raise AnalysisError("frozen_fields")
    if (data["version"] != CONFIG_VERSION or data["analysis_version"] != ANALYSIS_VERSION
            or data["qualification_version"] != QUALIFICATION_VERSION
            or data["aggregation"] != AGGREGATION
            or data["qualification_family"] != "qualification"
            or data["confirmation_family"] != "confirmation"
            or data["qualification_seeds"] != list(QUALIFICATION_SEEDS)
            or data["confirmation_seeds"] != list(CONFIRMATION_SEEDS)
            or data["qualification_protocol_version"] != "qualification/v1"
            or data["confirmation_protocol_version"] != "associative-confirmation/v1"
            or data["stimulus_version"] != "associative-stimuli/v1"
            or data["conditions"] != list(CONDITIONS)
            or data["interventions"] != list(INTERVENTIONS)
            or data["exclusions"] != []):
        raise AnalysisError("unsupported_frozen_contract")
    artifact = data["qualification_artifact"]
    if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_FIELDS \
            or not all(_digest(value) for value in artifact.values()):
        raise AnalysisError("qualification_artifact_hashes")
    engine = data["engine_identity"]
    expected_qualification = sorted({value for row in _expected_inputs("qualification").values()
                                     for value in row.values()})
    if data["qualification_input_sha256"] != expected_qualification:
        raise AnalysisError("qualification_input_hashes")
    hashes = data["confirmation_input_sha256"]
    if hashes != _expected_inputs("confirmation"):
        raise AnalysisError("confirmation_input_hashes")
    candidate = data["candidate_identity"]
    if not isinstance(candidate, str) or not re.fullmatch(r"[a-z0-9-]+/v[1-9][0-9]*", candidate):
        raise AnalysisError("candidate_identity")
    population = data["mbon11_population_size"]
    if not _int(population, minimum=1):
        raise AnalysisError("mbon11_population_size")
    if not _valid_engine_identity(engine, population):
        raise AnalysisError("engine_identity")
    configuration = data["selected_configuration"]
    valid_grid = [vars(item) for item in GRID]
    if (not isinstance(configuration, dict)
            or set(configuration) != {"cs_duration_ms", "dan_onset_ms", "post_pair_gap_ms"}
            or any(not _number(value) for value in configuration.values())
            or configuration not in valid_grid):
        raise AnalysisError("selected_configuration")
    window = data["response_window"]
    if (not isinstance(window, dict) or set(window) != {"start_ms", "end_ms"}
            or any(not _number(value) for value in window.values())
            or window not in [vars(item) for item in RESPONSE_WINDOWS]):
        raise AnalysisError("response_window")
    retention = data["retention_ms"]
    if (not _number(retention, minimum=10000) or retention not in RETENTION_CANDIDATES_MS
            or type(data["retention_times_ms"]) is not list
            or any(not _int(item, minimum=10000)
                   for item in data["retention_times_ms"])
            or data["retention_times_ms"] != [retention, retention + 60000]
            or type(data["expected_effect_sign"]) is not int
            or data["expected_effect_sign"] not in (-1, 1)):
        raise AnalysisError("selection")
    for name in ("replay_resolution_hz", "max_abs_control_delta_hz",
                 "dynamic_range_hz", "effect_floor_hz", "one_spike_floor_hz"):
        if not _number(data[name], minimum=0):
            raise AnalysisError(f"invalid_{name}")
    expected_one_spike = 1000 / (population * (window["end_ms"] - window["start_ms"]))
    if not _same_number(data["one_spike_floor_hz"], expected_one_spike):
        raise AnalysisError("one_spike_floor_mismatch")
    r = data["replay_resolution_hz"]
    c = data["max_abs_control_delta_hz"]
    d = data["dynamic_range_hz"]
    if not _same_number(data["effect_floor_hz"], max(5 * r, 2 * c, 0.05 * d)):
        raise AnalysisError("effect_floor_mismatch")
    sources = data["floor_sources"]
    if sources != {"replay_resolution_hz": "selected_paired_T_and_T_plus_60",
                   "max_abs_control_delta_hz": "selected_nonpaired_controls_T_and_T_plus_60",
                   "dynamic_range_hz": "selected_paired_pre_A_minus_pre_B",
                   "one_spike_floor_hz": "selected_response_window_and_population"}:
        raise AnalysisError("floor_sources")
    if not _digest(data["digest"]):
        raise AnalysisError("frozen_digest")
    projection = {key: value for key, value in data.items() if key != "digest"}
    if sha256(_canonical(projection).encode("utf-8")).hexdigest() != data["digest"]:
        raise AnalysisError("frozen_digest_mismatch")
    return data


@dataclass(frozen=True)
class FrozenAssayConfig:
    """Immutable canonical JSON; digest covers every other frozen field."""

    _json: str

    def __post_init__(self) -> None:
        data = _validate_config(_load(self._json))
        if self._json != _canonical(data) + "\n":
            raise AnalysisError("noncanonical_frozen_json")

    @classmethod
    def from_json(cls, raw: str | bytes) -> FrozenAssayConfig:
        data = _validate_config(_load(raw))
        canonical = _canonical(data) + "\n"
        try:
            decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        except UnicodeError as error:
            raise AnalysisError("invalid_json") from error
        if decoded != canonical:
            raise AnalysisError("noncanonical_frozen_json")
        return cls(canonical)

    @classmethod
    def from_dict(cls, data: dict) -> FrozenAssayConfig:
        return cls(_canonical(_validate_config(data)) + "\n")

    @property
    def digest(self) -> str:
        return self.to_dict()["digest"]

    def to_json(self) -> str:
        return self._json

    def to_dict(self) -> dict:
        return _load(self._json)


def _freeze(payload: dict) -> FrozenAssayConfig:
    payload = {key: value for key, value in payload.items() if key != "digest"}
    payload["digest"] = sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return FrozenAssayConfig.from_dict(payload)


@dataclass(frozen=True)
class EvidenceReduction:
    status: Literal["supported", "inconclusive"]
    rows: dict
    interventions: dict
    anchors: dict
    reasons: tuple[str, ...]
    trainings: dict | None = None
    checkpoints: dict | None = None


@dataclass(frozen=True)
class AssayReport:
    status: Literal["supported", "unsupported", "inconclusive"]
    values: dict
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"status": self.status, "values": self.values,
                "reasons": list(self.reasons)}


def _key(seed: int, identity: str, order: str, retention: int) -> str:
    return f"{seed}/{identity}/{order}/{retention}"


def _ticks(milliseconds: float) -> int:
    ticks = milliseconds * 10
    if not math.isfinite(ticks) or ticks != int(ticks):
        raise AnalysisError("nonintegral_schedule_tick")
    return int(ticks)


def _checkpoint_tick(milliseconds: object) -> int | None:
    if not _number(milliseconds):
        return None
    try:
        return _ticks(milliseconds)
    except AnalysisError:
        return None


def _training_plan(config: dict, seed: int, identity: str, order: str,
                   condition: str, family: str, baseline_tick: int) -> dict:
    configuration = GridConfiguration(**config["selected_configuration"])
    timeline, second_end, total_end, t0 = _training_timeline(
        configuration, identity, order, condition, controls=True,
    )
    _, _, paired_total_end, paired_t0 = _training_timeline(
        configuration, identity, order, "paired", controls=True,
    )
    if total_end != paired_total_end:
        raise AnalysisError("unequal_training_schedule_end")
    inputs = (_expected_inputs(family)[str(seed)] if family == "qualification"
              else config["confirmation_input_sha256"][str(seed)])
    exposure = {stimulus: sum(_ticks(part.end_ms - part.start_ms)
                              for part in timeline if part.stimulus == stimulus)
                for stimulus in STIMULI}
    segments = []
    for part in timeline:
        learning = (condition in {"paired", "no_external_dan", "temporally_unpaired"}
                    and part.start_ms < t0
                    and (part.stimulus is not None or part.stimulation is not None))
        segments.append({
            "start_tick": baseline_tick + _ticks(part.start_ms),
            "end_tick": baseline_tick + _ticks(part.end_ms),
            "stimulus": part.stimulus,
            "external_stimulation": part.stimulation,
            "current_mv": CURRENT_MV if part.stimulation is not None else None,
            "learning": learning,
            "input_sha256": inputs[part.stimulus or "black"],
        })
    dan_ends = [part.end_ms for part in timeline if part.stimulation is not None]
    unpaired = None
    if condition == "temporally_unpaired":
        visual_boundaries = [part.start_ms for part in timeline if part.stimulus]
        visual_boundaries += [part.end_ms for part in timeline if part.stimulus]
        pulse_boundaries = [part.start_ms for part in timeline if part.stimulation]
        pulse_boundaries += [part.end_ms for part in timeline if part.stimulation]
        unpaired = min(abs(_ticks(a - b)) for a in visual_boundaries
                       for b in pulse_boundaries)
    return {
        "training_start_tick": min(item["start_tick"] for item in segments
                                   if item["stimulus"] is not None),
        "association_t0_tick": baseline_tick + _ticks(t0),
        "retention_reference_tick": baseline_tick + _ticks(paired_t0),
        "training_end_tick": baseline_tick + _ticks(total_end),
        "last_visual_end_tick": baseline_tick + _ticks(second_end),
        "last_external_dan_end_tick": (baseline_tick + _ticks(max(dan_ends))
                                        if dan_ends else None),
        "training_visual_exposure_ticks": exposure,
        "unpaired_nearest_cs_boundary_ticks": unpaired,
        "segments": segments,
    }


def _validate_training(event: dict, config: dict, seeds: tuple[int, int],
                       family: str) -> None:
    if not TRAINING_FIELDS <= event.keys() or event["training_version"] != TRAINING_VERSION:
        raise ValueError("training_fields_or_version")
    if (not isinstance(event["training_id"], str) or not event["training_id"]
            or not isinstance(event["branch_id"], str) or not event["branch_id"]
            or type(event["seed"]) is not int or event["seed"] not in seeds
            or event["paired_identity"] not in ("A", "B")
            or event["presentation_order"] not in ("AB", "BA")
            or event["condition"] not in ORDINARY_CONDITIONS
            or event["candidate_identity"] != config["candidate_identity"]):
        raise ValueError("training_identity")
    if (not _int(event["baseline_tick"]) or event["baseline_tick"] > MAX_TICK
            or any(not _digest(event[name]) for name in (
                "baseline_checkpoint_sha256", "training_end_checkpoint_sha256",
                "candidate_memory_sha256", "noncandidate_state_sha256"))):
        raise ValueError("training_state")
    expected = _training_plan(config, event["seed"], event["paired_identity"],
                              event["presentation_order"], event["condition"],
                              family, event["baseline_tick"])
    for name, value in expected.items():
        if event[name] != value or (name.endswith("_tick") and value is not None
                                    and type(event[name]) is not int):
            raise ValueError("training_schedule:" + name)
    if (not isinstance(event["segments"], list)
            or any(not isinstance(item, dict) or set(item) != SEGMENT_FIELDS
                   for item in event["segments"])):
        raise ValueError("training_segments")


def _response_key(event: dict) -> tuple:
    return (event["seed"], event["paired_identity"], event["presentation_order"],
            event["retention_ms"], event["condition"], event["phase"],
            event["stimulus"])


def _validate_response(event: dict, config: dict, seeds: tuple[int, int],
                       event_type: str) -> tuple[float, str]:
    if not RESPONSE_FIELDS <= event.keys():
        raise ValueError("response_fields")
    if event["evidence_version"] != EVIDENCE_VERSION:
        raise ValueError("response_version")
    if not isinstance(event["branch_id"], str) or not event["branch_id"]:
        raise ValueError("response_branch")
    if (type(event["seed"]) is not int or event["seed"] not in seeds
            or event["paired_identity"] not in ("A", "B")
            or event["presentation_order"] not in ("AB", "BA")
            or type(event["retention_ms"]) is not int
            or event["retention_ms"] not in config["retention_times_ms"]
            or event["condition"] not in CONDITIONS
            or event["phase"] not in ("pre", "post")
            or event["stimulus"] not in STIMULI):
        raise ValueError("response_factor")
    if (event["candidate_identity"] != config["candidate_identity"]
            or event["population"] != "mbon11"
            or event["population_size"] != config["mbon11_population_size"]
            or type(event["population_size"]) is not int):
        raise ValueError("response_identity")
    if event["learning"] is not False or event["external_stimulation"] is not None:
        raise ValueError("reward_free_test")
    if (not isinstance(event["training_id"], str) or not event["training_id"]
            or not _digest(event["training_end_checkpoint_sha256"])
            or not _digest(event["retention_source_checkpoint_sha256"])
            or not _digest(event["input_sha256"])
            or not _digest(event["black_sha256"])):
        raise ValueError("response_hash")
    lineage = ("parent_checkpoint_sha256" in event) + ("parent_state_anchor_sha256" in event)
    if lineage != 1 or not _digest(event.get("parent_checkpoint_sha256",
                                                event.get("parent_state_anchor_sha256"))):
        raise ValueError("response_lineage")
    if event_type == "qualification_evidence":
        expected = _expected_inputs("qualification")[str(event["seed"])]
        if (event["input_sha256"] != expected[event["stimulus"]]
                or event["black_sha256"] != expected["black"]):
            raise ValueError("response_input_hash")
    else:
        input_hashes = config["confirmation_input_sha256"][str(event["seed"])]
        if (event["input_sha256"] != input_hashes[event["stimulus"]]
                or event["black_sha256"] != input_hashes["black"]):
            raise ValueError("response_input_hash")
    for field in ("training_start_tick", "association_t0_tick",
                  "retention_reference_tick", "training_end_tick",
                  "cs_onset_tick",
                  "passive_decay_ticks", "endogenous_dan_spikes",
                  "last_visual_end_tick"):
        if not _int(event[field]) or event[field] > MAX_TICK:
            raise ValueError("response_clock_or_count")
    dan_end = event["last_external_dan_end_tick"]
    if dan_end is not None and not _int(dan_end):
        raise ValueError("external_dan_clock")
    external_conditions = {"paired", "frozen_plasticity", "temporally_unpaired",
                           "necessity", "sham"}
    if (event["condition"] in external_conditions) != (dan_end is not None):
        raise ValueError("external_dan_declaration")
    unpaired_gap = event["unpaired_nearest_cs_boundary_ticks"]
    if event["condition"] == "temporally_unpaired":
        if not _int(unpaired_gap, minimum=100000):
            raise ValueError("unpaired_separation")
    elif unpaired_gap is not None:
        raise ValueError("unpaired_separation")
    exposure = event["training_visual_exposure_ticks"]
    if (not isinstance(exposure, dict) or set(exposure) != set(STIMULI)
            or any(not _int(value) for value in exposure.values())
            or exposure["A"] == 0 or exposure["B"] == 0):
        raise ValueError("visual_exposure")
    if event["association_t0_tick"] != max(event["last_visual_end_tick"], dan_end or 0):
        raise ValueError("association_t0")
    t0, reference, end = (event["association_t0_tick"],
                          event["retention_reference_tick"], event["training_end_tick"])
    target = reference + 10 * event["retention_ms"]
    if (not event["training_start_tick"] < event["last_visual_end_tick"] <= t0
            or t0 > reference or end < reference or end > target
            or event["passive_decay_ticks"] != target - end):
        raise ValueError("retention_clock")
    if event["phase"] == "pre" and event["cs_onset_tick"] < 1000:
        raise ValueError("pre_baseline_clock")
    if event["phase"] == "post" and event["cs_onset_tick"] != target:
        raise ValueError("test_onset_clock")
    if event["condition"] in INTERVENTIONS:
        if type(event["intervention_id"]) is not str or not event["intervention_id"]:
            raise ValueError("intervention_link")
    elif event["intervention_id"] is not None:
        raise ValueError("intervention_link")
    bins = event["bins"]
    if not isinstance(bins, list) or not bins or len(bins) > 10000:
        raise ValueError("response_bins")
    start = event["cs_onset_tick"] + int(config["response_window"]["start_ms"] * 10)
    stop = event["cs_onset_tick"] + int(config["response_window"]["end_ms"] * 10)
    cursor = start
    spikes = 0
    for item in bins:
        if not isinstance(item, dict) or set(item) != {"start_tick", "end_tick", "spikes"}:
            raise ValueError("response_bin_fields")
        if (not _int(item["start_tick"]) or not _int(item["end_tick"])
                or not _int(item["spikes"]) or item["start_tick"] != cursor
                or item["end_tick"] <= cursor or item["end_tick"] > stop
                or item["spikes"] > event["population_size"]
                * (item["end_tick"] - item["start_tick"])):
            raise ValueError("response_bin_coverage")
        cursor = item["end_tick"]
        spikes += item["spikes"]
    if cursor != stop:
        raise ValueError("response_bin_coverage")
    if _checkpoint_tick(event.get("sim_ms")) != stop:
        raise ValueError("response_event_clock")
    rate = spikes / (event["population_size"] * ((stop - start) / 10000))
    if not _number(event["rate_hz"], minimum=0) or not _same_number(event["rate_hz"], rate):
        raise ValueError("response_rate_mismatch")
    return rate, (event.get("parent_checkpoint_sha256")
                  or event["parent_state_anchor_sha256"])


def _validate_intervention(event: dict, config: dict, seeds: tuple[int, int]) -> None:
    if not INTERVENTION_FIELDS <= event.keys():
        raise ValueError("intervention_fields")
    if (event["intervention_version"] != INTERVENTION_VERSION
            or type(event["intervention_id"]) is not str or not event["intervention_id"]
            or type(event["donor_training_id"]) is not str or not event["donor_training_id"]
            or type(event["recipient_training_id"]) is not str or not event["recipient_training_id"]
            or type(event["seed"]) is not int or event["seed"] not in seeds
            or event["paired_identity"] not in ("A", "B")
            or event["presentation_order"] not in ("AB", "BA")
            or event["condition"] not in INTERVENTIONS
            or event["candidate_identity"] != config["candidate_identity"]):
        raise ValueError("intervention_identity")
    donor_role = "matched_baseline" if event["condition"] == "necessity" else "trained"
    if (event["donor_role"] != donor_role
            or event["recipient_role"] != ("untrained" if event["condition"] == "sufficiency"
                                            else "trained")
            or event["replaced_components"] != ["memory_u", "memory_w", "weight"]
            or event["complete_replacement"] is not True):
        raise ValueError("intervention_replacement")
    if (not _int(event["donor_training_end_tick"])
            or event["donor_training_end_tick"] != event["recipient_training_end_tick"]):
        raise ValueError("intervention_clock")
    for field in INTERVENTION_FIELDS:
        if field.endswith("sha256") and not _digest(event[field]):
            raise ValueError("intervention_hash")
    if (event["parent_checkpoint_sha256"] != event["recipient_checkpoint_sha256"]
            or event["noncandidate_state_before_sha256"]
            != event["noncandidate_state_after_sha256"]):
        raise ValueError("intervention_state_contamination")
    if event["recipient_candidate_memory_after_sha256"] \
            != event["donor_candidate_memory_sha256"]:
        raise ValueError("intervention_memory_replacement")
    if (event["condition"] == "sham"
            and event["recipient_candidate_memory_before_sha256"]
            != event["recipient_candidate_memory_after_sha256"]):
        raise ValueError("sham_memory_changed")


def _validate_anchor(event: dict, config: dict) -> None:
    required = {"anchor_version", "anchor_id", "state_anchor_sha256",
                "origin_branch_id", "sim_tick", "durable_ancestor_checkpoint_sha256",
                "replay_recipe_sha256", "source_identity_sha256"}
    if not required <= event.keys() or event["anchor_version"] != "state-anchor/v1":
        raise ValueError("state_anchor_fields")
    if (not isinstance(event["anchor_id"], str) or not event["anchor_id"]
            or not isinstance(event["origin_branch_id"], str)
            or not event["origin_branch_id"] or not _int(event["sim_tick"])):
        raise ValueError("state_anchor_identity")
    for name in required:
        if name.endswith("sha256") and not _digest(event[name]):
            raise ValueError("state_anchor_hash")
    expected_identity = config["engine_identity"]["sha256"]
    if event["source_identity_sha256"] != expected_identity:
        raise ValueError("state_anchor_source_identity")


def reduce_assay_evidence(
    events: Iterable[dict], frozen: FrozenAssayConfig, *,
    event_type: str = "assay_response",
    attested_state_anchors: Iterable[str] = (),
) -> EvidenceReduction:
    """Pure pre-seal reducer for versioned raw response and intervention events.

    One response per factor/condition/phase/stimulus is required. Each response
    contains contiguous half-open ``bins`` with integer 0.1 ms tick bounds and
    integer MBON11 spike counts. Intervention records are once per
    seed/identity/order/condition and link both retention copies by ID.
    """
    if not isinstance(frozen, FrozenAssayConfig) or event_type not in {
        "assay_response", "qualification_evidence",
    }:
        raise AnalysisError("invalid_reducer_contract")
    config = frozen.to_dict()
    seeds = (QUALIFICATION_SEEDS if event_type == "qualification_evidence"
             else CONFIRMATION_SEEDS)
    reasons = []
    responses = {}
    interventions = {}
    intervention_ids = set()
    trainings = {}
    training_keys = set()
    checkpoints = {}
    checkpoint_names = set()
    checkpoint_count = 0
    branches = {}
    anchors = {}
    anchor_ids = set()
    attested = frozenset(attested_state_anchors)
    if any(not _digest(item) for item in attested):
        raise AnalysisError("invalid_replay_attestation")
    relevant_count = 0
    relevant_types = {event_type, "qualification_point", "qualification_control",
                      "qualification_training", "qualification_result",
                      "assay_training", "assay_intervention",
                      "state_anchor", "branch_start"}
    for sequence, event in enumerate(events):
        if not isinstance(event, dict):
            relevant_count += 1
            if relevant_count > 10000:
                if relevant_count == 10001:
                    reasons.append("evidence_event_limit")
                continue
            reasons.append("malformed_event")
            continue
        # Terminal framing is validated by the artifact stream, not scientific evidence.
        # Keep enumerating it so later events retain their original sequence indices.
        if event.get("type") == "assay_result":
            continue
        branch = event.get("branch_id")
        new_branch = isinstance(branch, str) and branch not in branches
        if (event.get("type") not in relevant_types
                and "checkpoint_name" not in event and not new_branch):
            continue
        relevant_count += 1
        if relevant_count > 10000:
            if relevant_count == 10001:
                reasons.append("evidence_event_limit")
            continue
        if new_branch:
            if len(branches) >= 4096:
                reasons.append("branch_limit")
            else:
                branches[branch] = (event.get("parent_branch_id"),
                                    event.get("parent_checkpoint_sha256"))
        if "checkpoint_name" in event:
            digest = event.get("checkpoint_sha256")
            name = event.get("checkpoint_name")
            sim_tick = _checkpoint_tick(event.get("sim_ms"))
            if sim_tick is None:
                reasons.append("invalid_checkpoint_clock")
            if (not _digest(digest) or not isinstance(name, str)
                    or name in checkpoint_names or checkpoint_count >= 2048):
                reasons.append("duplicate_or_invalid_checkpoint")
            else:
                checkpoints.setdefault(digest, []).append({
                    "name": name,
                    "branch_id": event.get("branch_id"),
                    "sim_tick": sim_tick,
                    "parent_checkpoint_sha256": branches.get(branch, (None, None))[1],
                    "parent_branch_id": branches.get(branch, (None, None))[0],
                    "sequence": sequence,
                })
                checkpoint_names.add(name)
                checkpoint_count += 1
        if event.get("type") == ("qualification_training" if event_type == "qualification_evidence"
                                 else "assay_training"):
            try:
                _validate_training(event, config, seeds,
                                   "qualification" if event_type == "qualification_evidence"
                                   else "confirmation")
                key = (event["seed"], event["paired_identity"],
                       event["presentation_order"], event["condition"])
                if event["training_id"] in trainings or key in training_keys:
                    reasons.append("duplicate_training:" + "/".join(map(str, key)))
                else:
                    trainings[event["training_id"]] = dict(event)
                    training_keys.add(key)
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                reasons.append(f"invalid_training:{error}")
            continue
        if event.get("type") == event_type:
            try:
                rate, parent = _validate_response(event, config, seeds, event_type)
                if "parent_state_anchor_sha256" in event:
                    anchor = anchors.get(parent)
                    if anchor is None:
                        raise ValueError("missing_prior_state_anchor")
                    expected_clock = (event["retention_reference_tick"]
                                      + 10 * event["retention_ms"] - 1000
                                      if event["phase"] == "post"
                                      else event["cs_onset_tick"] - 1000)
                    if anchor["sim_tick"] != expected_clock:
                        raise ValueError("state_anchor_clock")
                    if ("parent_branch_id" in event
                            and event["parent_branch_id"] != anchor["origin_branch_id"]):
                        raise ValueError("state_anchor_origin")
                key = _response_key(event)
                if key in responses:
                    reasons.append("duplicate_response:" + "/".join(map(str, key)))
                else:
                    responses[key] = {"rate_hz": rate,
                                      "branch_id": event["branch_id"],
                                      "sequence": sequence,
                                      "training_id": event["training_id"],
                                      "endogenous_dan_spikes": event["endogenous_dan_spikes"],
                                      "association_t0_tick": event["association_t0_tick"],
                                      "retention_reference_tick": event["retention_reference_tick"],
                                      "training_start_tick": event["training_start_tick"],
                                      "training_end_tick": event["training_end_tick"],
                                      "last_visual_end_tick": event["last_visual_end_tick"],
                                      "last_external_dan_end_tick": event["last_external_dan_end_tick"],
                                      "unpaired_nearest_cs_boundary_ticks": event["unpaired_nearest_cs_boundary_ticks"],
                                      "training_visual_exposure_ticks":
                                          dict(event["training_visual_exposure_ticks"]),
                                      "training_end_checkpoint_sha256": event["training_end_checkpoint_sha256"],
                                      "retention_source_checkpoint_sha256":
                                          event["retention_source_checkpoint_sha256"],
                                      "parent_sha256": parent,
                                      "parent_kind": ("anchor" if "parent_state_anchor_sha256" in event
                                                      else "checkpoint"),
                                      "parent_branch_id": event.get("parent_branch_id"),
                                      "cs_onset_tick": event["cs_onset_tick"],
                                      "passive_decay_ticks": event["passive_decay_ticks"],
                                      "intervention_id": event["intervention_id"],
                                      "response_replay_resolution_hz": event.get("response_replay_resolution_hz"),
                                      "one_spike_rate_hz": event.get("one_spike_rate_hz")}
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                reasons.append(f"invalid_response:{error}")
        elif event.get("type") == "state_anchor":
            try:
                _validate_anchor(event, config)
                if (event["state_anchor_sha256"] in anchors
                        or event["anchor_id"] in anchor_ids):
                    reasons.append("duplicate_state_anchor:" + event["anchor_id"])
                else:
                    anchors[event["state_anchor_sha256"]] = {
                        "anchor_id": event["anchor_id"],
                        "sim_tick": event["sim_tick"],
                        "origin_branch_id": event["origin_branch_id"],
                        "durable_ancestor_checkpoint_sha256":
                            event["durable_ancestor_checkpoint_sha256"],
                        "replay_recipe_sha256": event["replay_recipe_sha256"],
                        "sequence": sequence,
                    }
                    anchor_ids.add(event["anchor_id"])
            except (KeyError, TypeError, ValueError) as error:
                reasons.append(f"invalid_state_anchor:{error}")
        elif event.get("type") == "assay_intervention":
            try:
                _validate_intervention(event, config, seeds)
                key = (event["seed"], event["paired_identity"],
                       event["presentation_order"], event["condition"])
                if key in interventions or event["intervention_id"] in intervention_ids:
                    reasons.append("duplicate_intervention:" + "/".join(map(str, key)))
                else:
                    interventions[key] = {name: event[name] for name in INTERVENTION_FIELDS}
                    interventions[key]["branch_id"] = event.get("branch_id")
                    interventions[key]["sequence"] = sequence
                    intervention_ids.add(event["intervention_id"])
            except (KeyError, TypeError, ValueError) as error:
                reasons.append(f"invalid_intervention:{error}")
    by_key = {(item["seed"], item["paired_identity"],
               item["presentation_order"], item["condition"]): item
              for item in trainings.values()}
    for seed in seeds:
        for identity in ("A", "B"):
            for order in ("AB", "BA"):
                for condition in ORDINARY_CONDITIONS:
                    if (seed, identity, order, condition) not in by_key:
                        reasons.append(f"missing_training:{seed}/{identity}/{order}/{condition}")
    for key, intervention in interventions.items():
        seed, identity, order, condition = key
        donor_condition = "matched_reference" if condition == "necessity" else "paired"
        recipient_condition = "matched_reference" if condition == "sufficiency" else "paired"
        donor = by_key.get((seed, identity, order, donor_condition))
        recipient = by_key.get((seed, identity, order, recipient_condition))
        if (donor is None or recipient is None
                or intervention["donor_training_id"] != donor["training_id"]
                or intervention["recipient_training_id"] != recipient["training_id"]
                or intervention["donor_checkpoint_sha256"]
                != donor["training_end_checkpoint_sha256"]
                or intervention["recipient_checkpoint_sha256"]
                != recipient["training_end_checkpoint_sha256"]
                or intervention["donor_candidate_memory_sha256"]
                != donor["candidate_memory_sha256"]
                or intervention["recipient_candidate_memory_before_sha256"]
                != recipient["candidate_memory_sha256"]
                or intervention["noncandidate_state_before_sha256"]
                != recipient["noncandidate_state_sha256"]
                or intervention["donor_training_end_tick"] != donor["training_end_tick"]
                or intervention["recipient_training_end_tick"] != recipient["training_end_tick"]):
            reasons.append("intervention_training:" + "/".join(map(str, key)))
    rows = {}
    for seed in seeds:
        for identity in ("A", "B"):
            for order in ("AB", "BA"):
                for retention in config["retention_times_ms"]:
                    for condition in CONDITIONS:
                        row = {}
                        for phase in ("pre", "post"):
                            for stimulus in STIMULI:
                                key = (seed, identity, order, retention, condition, phase, stimulus)
                                if key not in responses:
                                    reasons.append("missing_response:" + "/".join(map(str, key)))
                                else:
                                    row[f"{phase}_{stimulus}"] = responses[key]
                        row_key = _key(seed, identity, order, retention)
                        rows.setdefault(row_key, {})[condition] = row
                        recipient_condition = ("matched_reference" if condition == "sufficiency"
                                               else "paired" if condition in {"necessity", "sham"}
                                               else condition)
                        training = by_key.get((seed, identity, order, recipient_condition))
                        intervention = interventions.get((seed, identity, order, condition))
                        for name, item in row.items():
                            phase = "pre" if name.startswith("pre_") else "post"
                            expected_source = (intervention["post_intervention_checkpoint_sha256"]
                                               if intervention is not None
                                               else training["training_end_checkpoint_sha256"]
                                               if training is not None else None)
                            if (training is None or item["training_id"] != training["training_id"]
                                    or item["training_end_checkpoint_sha256"]
                                    != training["training_end_checkpoint_sha256"]
                                    or item["retention_source_checkpoint_sha256"] != expected_source
                                    or item["training_start_tick"] != training["training_start_tick"]
                                    or item["association_t0_tick"] != training["association_t0_tick"]
                                    or item["retention_reference_tick"]
                                    != training["retention_reference_tick"]
                                    or item["training_end_tick"] != training["training_end_tick"]
                                    or item["last_visual_end_tick"] != training["last_visual_end_tick"]
                                    or item["last_external_dan_end_tick"]
                                    != training["last_external_dan_end_tick"]
                                    or item["unpaired_nearest_cs_boundary_ticks"]
                                    != training["unpaired_nearest_cs_boundary_ticks"]
                                    or item["training_visual_exposure_ticks"]
                                    != training["training_visual_exposure_ticks"]
                                    or (phase == "pre" and (item["parent_sha256"]
                                        != training["baseline_checkpoint_sha256"]
                                        or item["cs_onset_tick"] != training["baseline_tick"] + 1000))
                                    or (condition in INTERVENTIONS and (intervention is None
                                        or item["intervention_id"] != intervention["intervention_id"]))):
                                reasons.append(f"response_training:{row_key}/{condition}/{name}")
                        if len(row) != 6:
                            continue
                        common = {(item["training_start_tick"], item["association_t0_tick"],
                                   item["retention_reference_tick"], item["training_id"],
                                   item["training_end_tick"],
                                   item["training_end_checkpoint_sha256"],
                                   item["retention_source_checkpoint_sha256"],
                                   item["passive_decay_ticks"], item["intervention_id"])
                                  for item in row.values()}
                        if len(common) != 1:
                            reasons.append(f"row_provenance:{row_key}/{condition}")
                        if len({_canonical(item["training_visual_exposure_ticks"])
                                for item in row.values()}) != 1:
                            reasons.append(f"row_exposure:{row_key}/{condition}")
                        for phase in ("pre", "post"):
                            cells = [row[f"{phase}_{stimulus}"] for stimulus in STIMULI]
                            if (len({cell["branch_id"] for cell in cells}) != len(STIMULI)
                                    or len({cell["parent_sha256"] for cell in cells}) != 1):
                                reasons.append(f"stimulus_copy:{row_key}/{condition}/{phase}")
                        if ({row[f"pre_{stimulus}"]["branch_id"] for stimulus in STIMULI}
                                & {row[f"post_{stimulus}"]["branch_id"] for stimulus in STIMULI}):
                            reasons.append(f"pre_post_copy:{row_key}/{condition}")
                        if condition in INTERVENTIONS:
                            intervention = interventions.get((seed, identity, order, condition))
                            if intervention is None:
                                reasons.append(f"missing_intervention:{seed}/{identity}/{order}/{condition}")
                            elif (row["post_A"]["intervention_id"] != intervention["intervention_id"]
                                  or row["post_A"]["training_end_tick"]
                                  != intervention["recipient_training_end_tick"]
                                  or row["post_A"]["training_end_checkpoint_sha256"]
                                  != intervention["recipient_checkpoint_sha256"]):
                                reasons.append(f"intervention_link:{row_key}/{condition}")
    for seed in seeds:
        for identity in ("A", "B"):
            for order in ("AB", "BA"):
                for condition in INTERVENTIONS:
                    if (seed, identity, order, condition) not in interventions:
                        reasons.append(f"missing_intervention:{seed}/{identity}/{order}/{condition}")
                for retention in config["retention_times_ms"]:
                    row_key = _key(seed, identity, order, retention)
                    complete = rows.get(row_key, {})
                    if (len(complete) == len(CONDITIONS)
                            and all("pre_A" in row for row in complete.values())):
                        declarations = {(
                            row["pre_A"]["training_start_tick"],
                            row["pre_A"]["retention_reference_tick"],
                            row["pre_A"]["training_end_tick"],
                            _canonical(row["pre_A"]["training_visual_exposure_ticks"]),
                        ) for row in complete.values()}
                        if len(declarations) != 1:
                            reasons.append(f"matched_exposure:{row_key}")
                early = rows.get(_key(seed, identity, order, config["retention_times_ms"][0]), {})
                late = rows.get(_key(seed, identity, order, config["retention_times_ms"][1]), {})
                for condition in set(early) & set(late):
                    for stimulus in STIMULI:
                        if (f"post_{stimulus}" not in early[condition]
                                or f"post_{stimulus}" not in late[condition]):
                            continue
                        first = early[condition][f"post_{stimulus}"]
                        second = late[condition][f"post_{stimulus}"]
                        if (first["branch_id"] == second["branch_id"]
                                or first["training_start_tick"] != second["training_start_tick"]
                                or first["association_t0_tick"] != second["association_t0_tick"]
                                or first["retention_reference_tick"]
                                != second["retention_reference_tick"]
                                or first["training_end_tick"] != second["training_end_tick"]
                                or first["training_end_checkpoint_sha256"]
                                != second["training_end_checkpoint_sha256"]):
                            reasons.append(f"retention_copy:{seed}/{identity}/{order}/{condition}/{stimulus}")
    for seed in seeds:
        for identity in ("A", "B"):
            for order in ("AB", "BA"):
                common_baselines = None
                for condition in ORDINARY_CONDITIONS:
                    training = by_key.get((seed, identity, order, condition))
                    if training is None:
                        continue
                    digest = training["baseline_checkpoint_sha256"]
                    candidates = {
                        (digest, baseline["sequence"])
                        for baseline in checkpoints.get(digest, ())
                        if baseline["sim_tick"] == training["baseline_tick"]
                        and any(
                            end["branch_id"] == training["branch_id"]
                            and end["parent_checkpoint_sha256"] == digest
                            and end["parent_branch_id"] == baseline["branch_id"]
                            and end["sequence"] > baseline["sequence"]
                            for end in checkpoints.get(training["training_end_checkpoint_sha256"], ())
                        )
                    }
                    common_baselines = (candidates if common_baselines is None
                                        else common_baselines & candidates)
                for key, response in responses.items():
                    if key[:3] != (seed, identity, order) or key[5] != "pre":
                        continue
                    digest = response["parent_sha256"]
                    candidates = {
                        (digest, baseline["sequence"])
                        for baseline in checkpoints.get(digest, ())
                        if response["parent_kind"] == "checkpoint"
                        and response["parent_branch_id"] == baseline["branch_id"]
                        and baseline["sequence"] < response["sequence"]
                    }
                    common_baselines = (candidates if common_baselines is None
                                        else common_baselines & candidates)
                if common_baselines is not None and not common_baselines:
                    reasons.append(f"cohort_baseline:{seed}/{identity}/{order}")
    for training in trainings.values():
        baselines = checkpoints.get(training["baseline_checkpoint_sha256"], ())
        ends = checkpoints.get(training["training_end_checkpoint_sha256"], ())
        if not any(
            baseline["sim_tick"] == training["baseline_tick"]
            and end["sim_tick"] == training["training_end_tick"]
            and end["branch_id"] == training["branch_id"]
            and end["parent_checkpoint_sha256"] == training["baseline_checkpoint_sha256"]
            and end["parent_branch_id"] == baseline["branch_id"]
            and end["sequence"] > baseline["sequence"]
            for baseline in baselines for end in ends
        ):
            reasons.append("training_ancestry:" + training["training_id"])
    for key, intervention in interventions.items():
        recipient = by_key.get((key[0], key[1], key[2],
                                "matched_reference" if key[3] == "sufficiency"
                                else "paired"))
        posts = checkpoints.get(intervention["post_intervention_checkpoint_sha256"], ())
        if (recipient is None or not any(
                post["sim_tick"] == recipient["training_end_tick"]
                and post["branch_id"] == intervention["branch_id"]
                and post["parent_checkpoint_sha256"]
                == recipient["training_end_checkpoint_sha256"]
                and post["parent_branch_id"] == recipient["branch_id"]
                for post in posts)):
            reasons.append("intervention_ancestry:" + "/".join(map(str, key)))
    for row_key, conditions in rows.items():
        seed, identity, order, retention = row_key.split("/")
        for condition, row in conditions.items():
            recipient_condition = ("matched_reference" if condition == "sufficiency"
                                   else "paired" if condition in {"necessity", "sham"}
                                   else condition)
            training = by_key.get((int(seed), identity, order, recipient_condition))
            intervention = interventions.get((int(seed), identity, order, condition))
            if training is None:
                continue
            source = (intervention["post_intervention_checkpoint_sha256"]
                      if intervention is not None else training["training_end_checkpoint_sha256"])
            for name, item in row.items():
                phase = "pre" if name.startswith("pre_") else "post"
                parents = ([anchors[item["parent_sha256"]]]
                           if item["parent_kind"] == "anchor"
                           and item["parent_sha256"] in anchors
                           else checkpoints.get(item["parent_sha256"], ())
                           if item["parent_kind"] == "checkpoint" else ())
                if not parents:
                    reasons.append(f"response_ancestry:{row_key}/{condition}/{name}")
                    continue
                if phase == "pre":
                    valid = (item["parent_kind"] == "checkpoint"
                             and item["parent_sha256"] == training["baseline_checkpoint_sha256"]
                             and any(parent["sim_tick"] == training["baseline_tick"]
                                     and item["parent_branch_id"] == parent["branch_id"]
                                     and parent["sequence"] < item["sequence"]
                                     for parent in parents))
                else:
                    clock = item["cs_onset_tick"] - 1000
                    sources = checkpoints.get(source, ())
                    if item["parent_kind"] == "checkpoint":
                        valid = any(
                            parent["sim_tick"] == clock
                            and parent["parent_checkpoint_sha256"] == source
                            and parent["parent_branch_id"] == source_record["branch_id"]
                            and source_record["sequence"] < parent["sequence"]
                            and item["parent_branch_id"] == parent["branch_id"]
                            and parent["sequence"] < item["sequence"]
                            for parent in parents for source_record in sources
                        )
                    else:
                        valid = any(
                            item["parent_sha256"] in attested
                            and parent["sim_tick"] == clock
                            and parent["durable_ancestor_checkpoint_sha256"] == source
                            and (origin := branches.get(parent["origin_branch_id"])) is not None
                            and origin[1] == source
                            and origin[0] == source_record["branch_id"]
                            and source_record["sequence"] < parent["sequence"]
                            and item["parent_branch_id"] == parent["origin_branch_id"]
                            and parent["sequence"] < item["sequence"]
                            for parent in parents for source_record in sources
                        )
                if not valid:
                    reasons.append(f"response_ancestry:{row_key}/{condition}/{name}")
    return EvidenceReduction("inconclusive" if reasons else "supported", rows,
                             interventions, anchors, tuple(sorted(set(reasons))),
                             trainings, checkpoints)


def _delta(row: dict, identity: str) -> float:
    other = "B" if identity == "A" else "A"
    return ((row[f"post_{identity}"]["rate_hz"] - row[f"post_{other}"]["rate_hz"])
            - (row[f"pre_{identity}"]["rate_hz"] - row[f"pre_{other}"]["rate_hz"]))


def _assess(reduction: EvidenceReduction, config: dict,
            seeds: tuple[int, int]) -> AssayReport:
    reasons = list(reduction.reasons)
    values = {"cells": {}, "effect_floor_hz": config["effect_floor_hz"],
              "replay_resolution_hz": config["replay_resolution_hz"],
              "one_spike_floor_hz": config["one_spike_floor_hz"]}
    floor = config["effect_floor_hz"]
    replay = config["replay_resolution_hz"]
    sign = config["expected_effect_sign"]
    for seed in seeds:
        for order in ("AB", "BA"):
            for retention in config["retention_times_ms"]:
                raw = {}
                for identity in ("A", "B"):
                    key = _key(seed, identity, order, retention)
                    conditions = reduction.rows.get(key, {})
                    complete = {name: row for name, row in conditions.items()
                                if len(row) == 6}
                    delta = {name: _delta(row, identity) for name, row in complete.items()}
                    cell = {
                        "rates_hz": {name: {name2: item["rate_hz"]
                                            for name2, item in row.items()}
                                     for name, row in conditions.items()},
                        "delta_hz": delta,
                        "endogenous_dan_spikes": {
                            name: sum(row[f"post_{stimulus}"]["endogenous_dan_spikes"]
                                      for stimulus in STIMULI)
                            for name, row in complete.items()},
                    }
                    if conditions:
                        values["cells"][key] = cell
                    if set(complete) != set(CONDITIONS):
                        continue
                    paired = complete["paired"]
                    pre_c = paired["pre_C"]["rate_hz"]
                    post_c = paired["post_C"]["rate_hz"]
                    cell["pre_C_hz"] = pre_c
                    cell["post_C_hz"] = post_c
                    def fail(gate: str) -> None:
                        reasons.append(f"{gate}:{key}")
                    if sign * delta["paired"] <= floor:
                        fail("paired_effect")
                    for control in ("frozen_plasticity", "no_external_dan",
                                    "temporally_unpaired"):
                        contrast = sign * (delta["paired"] - delta[control])
                        cell[f"paired_minus_{control}_hz"] = contrast
                        if contrast <= floor:
                            fail(f"control_{control}")
                    if pre_c <= config["one_spike_floor_hz"] or post_c <= config["one_spike_floor_hz"]:
                        fail("C_floor")
                        cell["global_gain_factor"] = None
                        cell["global_gain_residual_hz"] = None
                    else:
                        g = post_c / pre_c
                        other = "B" if identity == "A" else "A"
                        residual = ((paired[f"post_{identity}"]["rate_hz"]
                                     - g * paired[f"pre_{identity}"]["rate_hz"])
                                    - (paired[f"post_{other}"]["rate_hz"]
                                       - g * paired[f"pre_{other}"]["rate_hz"]))
                        cell["global_gain_factor"] = g
                        cell["global_gain_residual_hz"] = residual
                        if sign * residual <= floor:
                            fail("global_gain")
                    necessity = delta["necessity"]
                    reference = delta["matched_reference"]
                    sufficiency = delta["sufficiency"]
                    sham = delta["sham"]
                    cell["paired_minus_necessity_hz"] = sign * (delta["paired"] - necessity)
                    cell["necessity_minus_reference_hz"] = necessity - reference
                    cell["sufficiency_minus_reference_hz"] = sign * (sufficiency - reference)
                    cell["sham_minus_paired_hz"] = sham - delta["paired"]
                    if abs(necessity) > floor:
                        fail("necessity_absolute")
                    if cell["paired_minus_necessity_hz"] <= floor:
                        fail("necessity_contrast")
                    if abs(necessity - reference) > floor:
                        fail("necessity_reference")
                    if sign * sufficiency <= floor:
                        fail("sufficiency_absolute")
                    if cell["sufficiency_minus_reference_hz"] <= floor:
                        fail("sufficiency_reference")
                    if abs(sham - delta["paired"]) > replay:
                        fail("sham")
                    raw[identity] = ((paired["post_A"]["rate_hz"]
                                      - paired["post_B"]["rate_hz"])
                                     - (paired["pre_A"]["rate_hz"]
                                        - paired["pre_B"]["rate_hz"]))
                    cell["raw_A_minus_B_change_hz"] = raw[identity]
                if len(raw) == 2:
                    if sign * raw["A"] <= floor or sign * raw["B"] >= -floor:
                        reasons.append(f"reciprocal:{seed}/{order}/{retention}")
    reasons = sorted(set(reasons))
    if reduction.status == "inconclusive":
        status = "inconclusive"
    else:
        status = "unsupported" if reasons else "supported"
    return AssayReport(status, values, tuple(reasons))


def assess_assay_evidence(events: Iterable[dict],
                          frozen: FrozenAssayConfig, *,
                          attested_state_anchors: Iterable[str] = ()) -> AssayReport:
    """Pure arithmetic assessment; caller digest sets do not attest an artifact."""
    if not isinstance(frozen, FrozenAssayConfig):
        raise AnalysisError("invalid_frozen_config")
    reduced = reduce_assay_evidence(events, frozen,
                                    attested_state_anchors=attested_state_anchors)
    return _assess(reduced, frozen.to_dict(), CONFIRMATION_SEEDS)


def _verified_events(run: VerifiedRun | ValidatedPrefix) -> Iterable[dict]:
    try:
        yield from run.iter_events()
    except (OSError, ValueError) as error:
        raise AnalysisError("verified_run_changed") from error


def _verified(run: VerifiedRun) -> tuple[dict, Iterable[dict]]:
    if not isinstance(run, VerifiedRun):
        raise AnalysisError("unverified_run")
    try:
        return run.manifest, _verified_events(run)
    except (OSError, ValueError) as error:
        raise AnalysisError("verified_run_changed") from error


def _qualification_manifest(manifest: dict) -> dict:
    try:
        metadata = manifest["metadata"]
        if (manifest["run_kind"] != "qualification"
                or manifest["format_version"] != "run-artifact/v1"
                or manifest["schema_version"] != "run-schema/v1"
                or metadata["family"] != "qualification"
                or metadata["seeds"] != list(QUALIFICATION_SEEDS)
                or metadata["protocol_version"] != "qualification/v1"
                or metadata["stimulus_version"] != "associative-stimuli/v1"
                or metadata["qualification_version"] != QUALIFICATION_VERSION
                or metadata["aggregation"] != AGGREGATION
                or metadata["exclusions"] != []
                or metadata["factors"] != _qualification_factors()
                or metadata["configuration"] != {
                    "pulse_duration_ms": PULSE_DURATION_MS,
                    "external_dan_current_mv": CURRENT_MV,
                    "unpaired_minimum_separation_ms": UNPAIRED_SEPARATION_MS,
                }
                or not _int(metadata["mbon11_population_size"], minimum=1)
                or not isinstance(metadata["candidate_identity"], str)):
            raise AnalysisError("qualification_declaration")
        for field in ARTIFACT_FIELDS:
            if not _digest(manifest[field]):
                raise AnalysisError("qualification_artifact_hashes")
        if (not _valid_engine_identity(metadata["engine_identity"],
                                       metadata["mbon11_population_size"])
                or not isinstance(metadata["input_sha256"], list)
                or len(metadata["input_sha256"]) < 4
                or any(not _digest(value) for value in metadata["input_sha256"])):
            raise AnalysisError("qualification_identity")
        qualification_hashes = _expected_inputs("qualification")
        declared = metadata["rgb_input_sha256"]
        if (declared != {
                "stimuli": {seed: {stimulus: row[stimulus] for stimulus in STIMULI}
                            for seed, row in qualification_hashes.items()},
                "black": qualification_hashes[str(QUALIFICATION_SEEDS[0])]["black"],
            }
                or metadata["input_sha256"] != sorted({value for row in qualification_hashes.values()
                                                         for value in row.values()})):
            raise AnalysisError("qualification_input_hashes")
        hashes = metadata["confirmation_input_sha256"]
        if hashes != _expected_inputs("confirmation"):
            raise AnalysisError("confirmation_hashes")
        if ({row[stimulus] for row in hashes.values() for stimulus in STIMULI}
                & {row[stimulus] for row in qualification_hashes.values()
                   for stimulus in STIMULI}):
            raise AnalysisError("held_out_input_overlap")
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, AnalysisError):
            raise
        raise AnalysisError("qualification_manifest") from error
    return metadata


def _selected_point(events: Iterable[dict], result: dict) -> dict:
    selected = []
    for event in events:
        if (event.get("type") == "qualification_point"
                and isinstance(event.get("point"), dict)
                and event["point"].get("configuration") == result["selected_configuration"]
                and event["point"].get("response_window") == result["selected_window"]
                and event["point"].get("retention_ms") == result["selected_retention_ms"]):
            if len(selected) < 2:
                selected.append(event["point"])
    if len(selected) != 1:
        raise AnalysisError("selected_point")
    point = selected[0]
    replicates = point.get("replicates")
    expected = {(seed, identity, order) for seed in QUALIFICATION_SEEDS
                for identity in ("A", "B") for order in ("AB", "BA")}
    if (point.get("reasons") != [] or not isinstance(replicates, list)
            or len(replicates) != 8):
        raise AnalysisError("selected_point_incomplete")
    try:
        keys = [(item["seed"], item["paired_identity"], item["presentation_order"])
                for item in replicates]
        deltas = [item["delta_hz"] for item in replicates]
        if (set(keys) != expected or len(set(keys)) != 8
                or any(not _number(value) for value in deltas)
                or not _same_number(point["mean_delta_hz"], sum(deltas) / 8)
                or result["observed_effect_sign"] * point["mean_delta_hz"] <= 0):
            raise AnalysisError("selected_point_mismatch")
    except (KeyError, TypeError) as error:
        raise AnalysisError("selected_point_incomplete") from error
    return point


def _validate_selected_replicates(point: dict, population: int, window: dict) -> None:
    """Recompute the producer's selected replicate gates from declared measurements."""
    one_spike = 1000 / (population * (window["end_ms"] - window["start_ms"]))
    expected_order = None
    for item in point["replicates"]:
        try:
            pre = item["pre_mbon11"]
            post = item["post_mbon11"]
            pre07 = item["pre_mbon07"]
            post07 = item["post_mbon07"]
            replay = item["response_replay_resolution_hz"]
            state_resolution = item["state_replay_resolution"]
            state_shift = item["state_shift"]
            washout = item["washout_hz"]
            threshold = item["washout_threshold_hz"]
            vectors = item["candidate_kc_vectors"]
            post_vectors = item["post_candidate_kc_vectors"]
            if (item["reasons"] != []
                    or any(type(values) is not list or len(values) != 3
                           or any(not _number(value, minimum=0) for value in values)
                           for values in (pre, post, pre07, post07))
                    or not _same_number(item["one_spike_rate_hz"], one_spike)
                    or not _number(replay, minimum=0) or replay != 0
                    or not _number(state_resolution, minimum=0) or state_resolution != 0
                    or not _number(state_shift, minimum=0)
                    or state_shift <= 5 * state_resolution
                    or not _number(washout, minimum=0)
                    or not _same_number(threshold, max(5 * replay, one_spike))
                    or washout > threshold
                    or not _number(item["maximum_bound_hit_fraction"], minimum=0)
                    or item["maximum_bound_hit_fraction"] > 0.01
                    or pre[2] < one_spike or post[2] < one_spike
                    or abs(pre[0] - pre[1]) <= replay):
                raise AnalysisError("selected_replicate_gate")
            plus = 0 if item["paired_identity"] == "A" else 1
            minus = 1 - plus
            delta = (post[plus] - post[minus]) - (pre[plus] - pre[minus])
            if not _same_number(item["delta_hz"], delta):
                raise AnalysisError("selected_replicate_delta")
            if (any(type(item[name]) is not list or not item[name]
                    for name in ("candidate_kc_ids", "candidate_edge_indices", "dan_indices",
                                 "rate_kc", "rate_dan"))
                    or any(not _number(value) or value <= 0
                           for value in item["modeled_drive"])
                    or type(item["modeled_drive"]) is not list
                    or len(item["modeled_drive"]) != 3
                    or any(not isinstance(value, list) or not value
                           or any(not _int(count) for count in value)
                           or sum(value) == 0 for value in (*vectors, *post_vectors))
                    or len(vectors) != 2 or len(post_vectors) != 2
                    or vectors[0] == vectors[1] or post_vectors[0] == post_vectors[1]
                    or any(type(value) is not int for name in (
                        "candidate_kc_ids", "candidate_edge_indices", "dan_indices")
                        for value in item[name])
                    or any(not _number(value) for name in ("rate_kc", "rate_dan")
                           for value in item[name])):
                raise AnalysisError("selected_replicate_observability")
            kc_ids = item["candidate_kc_ids"]
            edge_indices = item["candidate_edge_indices"]
            dan_indices = item["dan_indices"]
            if (any(len(vector) != len(kc_ids) for vector in (*vectors, *post_vectors))
                    or len(set(kc_ids)) != len(kc_ids)
                    or len(edge_indices) != len(item["rate_kc"])
                    or len(set(edge_indices)) != len(edge_indices)
                    or len(dan_indices) != len(item["rate_dan"])
                    or len(set(dan_indices)) != len(dan_indices)):
                raise AnalysisError("selected_replicate_dimensions")
            memory_names = ("training_memory_w", "matched_memory_w", "replay_memory_w")
            memories = [item[name] for name in memory_names]
            if any(type(values) is not list or len(values) != len(edge_indices)
                   or any(not _number(value) for value in values) for values in memories):
                raise AnalysisError("selected_replicate_state")
            trained, matched, replayed = memories
            actual_shift = sum(abs(a - b) for a, b in zip(trained, matched)) / len(edge_indices)
            actual_resolution = sum(abs(a - b) for a, b in zip(trained, replayed)) / len(edge_indices)
            if (not _number(actual_shift, minimum=0)
                    or not _number(actual_resolution, minimum=0)
                    or not _same_number(state_shift, actual_shift)
                    or not _same_number(state_resolution, actual_resolution)):
                raise AnalysisError("selected_replicate_state")
            source_names = ("candidate_edge_pre_source_ids", "candidate_edge_post_source_ids",
                            "candidate_kc_source_ids", "dan_source_ids")
            if not all(name in item for name in source_names):
                raise AnalysisError("selected_replicate_source_order")
            edge_pre, edge_post, kc_sources, dan_sources = (item[name] for name in source_names)
            if (any(type(values) is not list or any(
                    type(value) is not str or not value for value in values
                ) for values in (edge_pre, edge_post, kc_sources, dan_sources))
                    or len(edge_pre) != len(edge_indices)
                    or len(edge_post) != len(edge_indices)
                    or len(kc_sources) != len(kc_ids)
                    or len(dan_sources) != len(dan_indices)
                    or len(set(kc_sources)) != len(kc_sources)
                    or len(set(dan_sources)) != len(dan_sources)
                    or not set(edge_pre) <= set(kc_sources)):
                raise AnalysisError("selected_replicate_source_order")
            source_order = tuple(tuple(item[name]) for name in source_names)
            order = (tuple(kc_ids), tuple(edge_indices), tuple(dan_indices), source_order)
            if expected_order is None:
                expected_order = order
            elif order != expected_order:
                raise AnalysisError("selected_replicate_order")
        except (KeyError, IndexError, TypeError, ValueError, OverflowError) as error:
            if isinstance(error, AnalysisError):
                raise
            raise AnalysisError("selected_replicate_incomplete") from error


def _inventory_reasons(manifest: dict, reduction: EvidenceReduction) -> tuple[str, ...]:
    checkpoints = manifest.get("checkpoints")
    if not isinstance(checkpoints, dict):
        return ("checkpoint_inventory_missing",)
    digests = {item.get("sha256") for item in checkpoints.values() if isinstance(item, dict)}
    reasons = []
    for digest, occurrences in (reduction.checkpoints or {}).items():
        for recorded in occurrences:
            declared = checkpoints.get(recorded["name"])
            declared_tick = (_checkpoint_tick(declared.get("sim_ms"))
                             if isinstance(declared, dict) else None)
            if (not isinstance(declared, dict) or declared.get("sha256") != digest
                    or declared.get("origin_branch_id") != recorded["branch_id"]
                    or declared_tick is None or declared_tick != recorded["sim_tick"]):
                reasons.append("checkpoint_inventory_mismatch:" + str(recorded["name"]))
    for key, rows in reduction.rows.items():
        for condition, row in rows.items():
            for name, cell in row.items():
                if cell["training_end_checkpoint_sha256"] not in digests:
                    reasons.append(f"training_checkpoint_missing:{key}/{condition}/{name}")
                if cell["parent_sha256"] not in digests \
                        and cell["parent_sha256"] not in reduction.anchors:
                    reasons.append(f"response_parent_missing:{key}/{condition}/{name}")
    for key, intervention in reduction.interventions.items():
        for field in ("donor_checkpoint_sha256", "recipient_checkpoint_sha256",
                      "post_intervention_checkpoint_sha256"):
            if intervention[field] not in digests:
                reasons.append("intervention_checkpoint_missing:" + "/".join(map(str, key))
                               + "/" + field)
    for digest, anchor in reduction.anchors.items():
        if anchor["durable_ancestor_checkpoint_sha256"] not in digests:
            reasons.append(f"state_anchor_ancestor_missing:{digest}")
    return tuple(sorted(set(reasons)))


def _validate_control_summaries(events: Iterable[dict], reduction: EvidenceReduction,
                                retention: int) -> None:
    seen = set()
    failure = None
    for event in events:
        if event.get("type") != "qualification_control":
            continue
        try:
            control = event.get("control")
            if not isinstance(control, dict):
                raise AnalysisError("qualification_control_invalid")
            seed = control["seed"]
            identity = control["paired_identity"]
            order = control["presentation_order"]
            condition = control["condition"]
            key = (seed, identity, order, condition)
            if (type(seed) is not int or seed not in QUALIFICATION_SEEDS
                    or identity not in ("A", "B") or order not in ("AB", "BA")
                    or condition not in CONDITIONS or key in seen):
                raise AnalysisError("qualification_control_duplicate_or_factor")
            seen.add(key)
            row = reduction.rows[_key(seed, identity, order, retention)][condition]
            if not _same_number(control["delta_hz"], _delta(row, identity)):
                raise AnalysisError("qualification_control_mismatch")
            if "pre_mbon11" in control and any(
                not _same_number(control["pre_mbon11"][index], row[f"pre_{stimulus}"]["rate_hz"])
                for index, stimulus in enumerate(STIMULI)
            ):
                raise AnalysisError("qualification_control_mismatch")
            if "post_mbon11" in control and any(
                not _same_number(control["post_mbon11"][index], row[f"post_{stimulus}"]["rate_hz"])
                for index, stimulus in enumerate(STIMULI)
            ):
                raise AnalysisError("qualification_control_mismatch")
        except (KeyError, IndexError, TypeError):
            if failure is None:
                failure = AnalysisError("qualification_control_invalid")
        except AnalysisError as error:
            if failure is None:
                failure = error
    if failure is not None:
        raise failure


def build_frozen_config(qualification: VerifiedRun) -> FrozenAssayConfig:
    """Freeze a selected qualification, never inspecting confirmation data."""
    manifest, events = _verified(qualification)
    metadata = _qualification_manifest(manifest)
    results = []
    last = None
    for event in events:
        if event.get("type") == "qualification_result":
            if len(results) < 2:
                results.append(event)
        last = event
    if len(results) != 1 or last is not results[0]:
        raise AnalysisError("qualification_terminal_result")
    result = results[0]
    try:
        if (result["status"] != "supported"
                or result["family"] != metadata["family"]
                or result["seeds"] != metadata["seeds"]
                or result["selected_configuration"] not in [vars(item) for item in GRID]
                or result["selected_window"] not in [vars(item) for item in RESPONSE_WINDOWS]
                or result["selected_retention_ms"] not in RETENTION_CANDIDATES_MS
                or type(result["observed_effect_sign"]) is not int
                or result["observed_effect_sign"] not in (-1, 1)):
            raise AnalysisError("unsupported_qualification")
    except (KeyError, TypeError) as error:
        raise AnalysisError("qualification_result") from error
    point = _selected_point(_verified_events(qualification), result)
    window = result["selected_window"]
    population = metadata["mbon11_population_size"]
    _validate_selected_replicates(point, population, window)
    one_spike = 1000 / (population * (window["end_ms"] - window["start_ms"]))
    payload = {
        "version": CONFIG_VERSION, "analysis_version": ANALYSIS_VERSION,
        "qualification_version": QUALIFICATION_VERSION, "aggregation": AGGREGATION,
        "qualification_artifact": {field: manifest[field] for field in ARTIFACT_FIELDS},
        "qualification_family": "qualification", "qualification_seeds": list(QUALIFICATION_SEEDS),
        "qualification_protocol_version": "qualification/v1",
        "confirmation_family": "confirmation", "confirmation_seeds": list(CONFIRMATION_SEEDS),
        "confirmation_protocol_version": "associative-confirmation/v1",
        "stimulus_version": metadata["stimulus_version"],
        "engine_identity": metadata["engine_identity"],
        "qualification_input_sha256": metadata["input_sha256"],
        "confirmation_input_sha256": metadata["confirmation_input_sha256"],
        "candidate_identity": metadata["candidate_identity"],
        "mbon11_population_size": population,
        "selected_configuration": result["selected_configuration"],
        "response_window": window,
        "retention_ms": int(result["selected_retention_ms"]),
        "retention_times_ms": [int(result["selected_retention_ms"]),
                               int(result["selected_retention_ms"]) + 60000],
        "expected_effect_sign": result["observed_effect_sign"],
        "conditions": list(CONDITIONS), "interventions": list(INTERVENTIONS),
        "exclusions": [], "replay_resolution_hz": 0.0,
        "max_abs_control_delta_hz": 0.0, "dynamic_range_hz": 0.0,
        "effect_floor_hz": 0.0, "one_spike_floor_hz": one_spike,
        "floor_sources": {
            "replay_resolution_hz": "selected_paired_T_and_T_plus_60",
            "max_abs_control_delta_hz": "selected_nonpaired_controls_T_and_T_plus_60",
            "dynamic_range_hz": "selected_paired_pre_A_minus_pre_B",
            "one_spike_floor_hz": "selected_response_window_and_population",
        },
    }
    provisional = _freeze(payload)
    reduced = reduce_assay_evidence(
        _verified_events(qualification), provisional,
        event_type="qualification_evidence",
        attested_state_anchors=getattr(qualification, "replay_attested_state_anchors", ()),
    )
    if reduced.status != "supported":
        raise AnalysisError("qualification_evidence:" + reduced.reasons[0])
    inventory = _inventory_reasons(manifest, reduced)
    if inventory:
        raise AnalysisError("qualification_checkpoint:" + inventory[0])
    _validate_control_summaries(_verified_events(qualification), reduced,
                                int(result["selected_retention_ms"]))
    selected_retention = int(result["selected_retention_ms"])
    for replicate in point["replicates"]:
        stimulus = replicate["paired_identity"]
        row = reduced.rows[_key(replicate["seed"], stimulus,
                                replicate["presentation_order"], selected_retention)]
        actual_washout = abs(
            row["frozen_plasticity"][f"post_{stimulus}"]["rate_hz"]
            - row["matched_reference"][f"post_{stimulus}"]["rate_hz"]
        )
        if not _same_number(replicate["washout_hz"], actual_washout):
            raise AnalysisError("selected_replicate_washout")
    replay = []
    control = []
    dynamic = []
    for key, rows in reduced.rows.items():
        identity = key.split("/")[1]
        paired = rows["paired"]
        dynamic.append(abs(paired["pre_A"]["rate_hz"] - paired["pre_B"]["rate_hz"]))
        for row in rows.values():
            for cell in row.values():
                if not _number(cell["one_spike_rate_hz"], minimum=0) \
                        or not _same_number(cell["one_spike_rate_hz"], one_spike):
                    raise AnalysisError("qualification_one_spike_semantics")
                if not _number(cell["response_replay_resolution_hz"], minimum=0):
                    raise AnalysisError("qualification_replay_resolution")
        replay.append(max(cell["response_replay_resolution_hz"] for cell in paired.values()))
        control.extend(abs(_delta(rows[name], identity)) for name in CONTROLS)
    payload["replay_resolution_hz"] = max(replay)
    payload["max_abs_control_delta_hz"] = max(control)
    payload["dynamic_range_hz"] = max(dynamic)
    payload["effect_floor_hz"] = max(5 * max(replay), 2 * max(control), 0.05 * max(dynamic))
    frozen = _freeze(payload)
    report = _assess(reduced, frozen.to_dict(), QUALIFICATION_SEEDS)
    if report.status != "supported":
        raise AnalysisError("qualification_gate:" + report.reasons[0])
    return frozen


def _assay_provenance(manifest: dict, frozen: FrozenAssayConfig) -> tuple[str, ...]:
    config = frozen.to_dict()
    expected_contract = {
        "selected_configuration": config["selected_configuration"],
        "response_window": config["response_window"],
        "retention_times_ms": config["retention_times_ms"],
        "expected_effect_sign": config["expected_effect_sign"],
        "conditions": config["conditions"],
        "interventions": config["interventions"],
        "stimuli": list(STIMULI),
        "analysis_version": config["analysis_version"],
    }
    try:
        metadata = manifest["metadata"]
        if (manifest["run_kind"] != "confirmation"
                or metadata["family"] != "confirmation"
                or metadata["seeds"] != list(CONFIRMATION_SEEDS)
                or metadata["protocol_version"] != config["confirmation_protocol_version"]
                or metadata["stimulus_version"] != config["stimulus_version"]
                or metadata["engine_identity"] != config["engine_identity"]
                or metadata["candidate_identity"] != config["candidate_identity"]
                or metadata["mbon11_population_size"] != config["mbon11_population_size"]
                or metadata["aggregation"] != config["aggregation"]
                or metadata["exclusions"] != config["exclusions"]
                or _canonical(metadata["assay_contract"]) != _canonical(expected_contract)
                or metadata["frozen_config_sha256"] != frozen.digest
                or metadata["confirmation_input_sha256"]
                != config["confirmation_input_sha256"]
                or metadata["input_sha256"] != sorted({
                    value for row in config["confirmation_input_sha256"].values()
                    for value in row.values()
                })):
            return ("manifest_provenance",)
    except (KeyError, TypeError, ValueError) as error:
        return (f"manifest_invalid:{error}",)
    return ()


def _assay_verification(value: VerifiedRun | ValidatedPrefix) -> tuple[str, frozenset[str]]:
    # In-memory arithmetic fixtures and caller-overridden properties cannot issue trust.
    if type(value) not in (VerifiedRun, ValidatedPrefix):
        return "integrity-only", frozenset()
    try:
        return value.verification_mode, value.replay_attested_state_anchors
    except (OSError, ValueError) as error:
        raise AnalysisError("verified_run_changed") from error


def _artifact_assay_report(value: VerifiedRun | ValidatedPrefix, frozen: FrozenAssayConfig,
                           manifest: dict) -> AssayReport:
    mode, attested = _assay_verification(value)
    reduction = reduce_assay_evidence(_verified_events(value), frozen,
                                      attested_state_anchors=attested)
    reasons = reduction.reasons + _inventory_reasons(manifest, reduction) + _assay_provenance(manifest, frozen)
    if reasons:
        reduction = EvidenceReduction("inconclusive", reduction.rows,
                                      reduction.interventions, reduction.anchors,
                                      tuple(sorted(set(reasons))), reduction.trainings, reduction.checkpoints)
    report = _assess(reduction, frozen.to_dict(), CONFIRMATION_SEEDS)
    report.values["verification_mode"] = mode
    report.values["nonmaterialized_parents"] = [
        {"parent_sha256": digest, "parent_kind": kind}
        for digest, kind in sorted({(cell["parent_sha256"], cell["parent_kind"])
                                   for rows in reduction.rows.values() for row in rows.values()
                                   for cell in row.values() if cell["parent_kind"] == "anchor"})
    ]
    # Exhaust another validated scan after constructing science, also in ordinary mode.
    terminal_seen = False
    for event in _verified_events(value):
        terminal_seen |= event.get("type") == "assay_result"
    _assay_verification(value)
    if type(value) is ValidatedPrefix and terminal_seen:
        raise AnalysisError("prefix_already_terminal")
    return report


def assess_assay_prefix(prefix: ValidatedPrefix, frozen: FrozenAssayConfig) -> AssayReport:
    """Assess a fixed validated stream without requiring a terminal result."""
    if type(prefix) is not ValidatedPrefix:
        raise AnalysisError("unvalidated_prefix")
    if not isinstance(frozen, FrozenAssayConfig):
        raise AnalysisError("invalid_frozen_config")
    return _artifact_assay_report(prefix, frozen, prefix.manifest)


def _assay_result(report: AssayReport, frozen: FrozenAssayConfig, projection: dict) -> dict:
    return {
        "result_version": "mbon11-assay-result/v1",
        "frozen_config_sha256": frozen.digest,
        "analysis_version": ANALYSIS_VERSION,
        "status": report.status,
        "reasons": list(report.reasons),
        "report": report.to_dict(),
        "report_sha256": sha256(_canonical(report.to_dict()).encode("utf-8")).hexdigest(),
        "evidence_event_count": projection["event_count"],
        "evidence_final_scientific_sha256": projection["final_scientific_sha256"],
    }


def build_assay_result(prefix: ValidatedPrefix, frozen: FrozenAssayConfig) -> dict:
    """Build the terminal payload only from verifier-issued native replay proof."""
    if type(prefix) is not ValidatedPrefix:
        raise AnalysisError("unvalidated_prefix")
    if _assay_verification(prefix)[0] != "native-replay":
        raise AnalysisError("native_replay_required")
    report = assess_assay_prefix(prefix, frozen)
    payload = _assay_result(report, frozen, prefix.scientific_prefix)
    _assay_verification(prefix)
    return payload


def analyze_assay(run: VerifiedRun, frozen: FrozenAssayConfig) -> AssayReport:
    """Independently recompute scientific report and final terminal bindings."""
    if not isinstance(frozen, FrozenAssayConfig):
        raise AnalysisError("invalid_frozen_config")
    manifest, events = _verified(run)
    terminal = None
    count = 0
    last = None
    ambiguous_terminal = False
    evidence_digest = None
    for event in events:
        if event.get("type") == "assay_result":
            if terminal is not None:
                ambiguous_terminal = True
            else:
                terminal = event
        else:
            evidence_digest = event.get("scientific_sha256")
        count += 1
        last = event
    report = _artifact_assay_report(run, frozen, manifest)
    if ambiguous_terminal or terminal is None or last is not terminal:
        return AssayReport("inconclusive", report.values,
                           tuple(sorted(set(report.reasons + ("terminal_result_missing_or_ambiguous",)))))
    expected = _assay_result(report, frozen, {"event_count": count - 1,
                                             "final_scientific_sha256": evidence_digest})
    if (any(terminal.get(name) != value for name, value in expected.items())
            or type(terminal.get("evidence_event_count")) is not int
            or terminal.get("sequence") != count - 1
            or terminal.get("scientific_sha256") != manifest.get("final_scientific_sha256")
            or terminal.get("previous_scientific_sha256") != evidence_digest
            or not _digest(terminal.get("previous_scientific_sha256"))):
        return AssayReport("inconclusive", report.values,
                           tuple(sorted(set(report.reasons + ("terminal_result_mismatch",)))))
    return report
