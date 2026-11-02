"""Private, engine-free reconstruction of the recorded exploratory grid.

The first pass owns references and schedule positions; the second independently
projects actual calls/archives. Neither a summary nor a failure label is proof.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from hashlib import sha256
import math

import numpy as np

from . import qualification as q
from .analysis import AnalysisError, _qualification_declarations
from .recorder import ValidatedPrefix, VerifiedRun, _verified_qualification_context
from ..neural.checkpoint import read_checkpoint
from ..engine import _array_summary


@dataclass(frozen=True)
class _GridAssessment:
    outcome: str
    reasons: tuple[str, ...]
    selection: tuple | None
    points: tuple[q._PointSummary, ...]
    unit_count: int


@dataclass(frozen=True)
class _Plan:
    branch: str
    path: tuple[str, ...]
    kind: str
    condition: str | None
    stimulus: str | None
    retention: int | None
    start: int
    segments: tuple[q.Segment, ...]
    parent: str
    checkpoint: bool = False
    association: int | None = None


@dataclass
class _Role:
    plan: _Plan
    restore: int
    parent: dict
    calls: list[int] = field(default_factory=list)
    occurrence: dict | None = None

    @property
    def complete(self):
        return (len(self.calls) == len(self.plan.segments)
                and (not self.plan.checkpoint or self.occurrence is not None))


@dataclass
class _Unit:
    index: int
    plans: tuple[_Plan, ...]
    roles: dict[str, _Role] = field(default_factory=dict)
    binding: int | None = None
    failures: tuple[dict, ...] = ()


_FACTORS = tuple((seed, paired, order) for seed in q.QUALIFICATION_SEEDS
                 for paired in ("A", "B") for order in ("AB", "BA"))
_TRAIN = ("paired", "matched_reference", "frozen_plasticity", "paired_replay")
_RETAIN = ("paired", "frozen_plasticity", "matched_reference")
_TIMES = (10000, 20000, 30000, 60000)


def _require(condition, reason):
    if not condition:
        raise AnalysisError(reason)


def _equal(actual, expected, reason):
    """Compare complete structures, allowing only the existing scalar precision."""
    if is_dataclass(expected):
        names = tuple(item.name for item in fields(expected))
        _require(type(actual) is dict and actual.keys() == set(names), reason)
        for name in names:
            _equal(actual[name], getattr(expected, name), reason)
    elif isinstance(expected, dict):
        _require(type(actual) is dict and actual.keys() == expected.keys(), reason)
        for key in expected:
            _equal(actual[key], expected[key], reason)
    elif isinstance(expected, (tuple, list)):
        _require(type(actual) in (list, tuple) and len(actual) == len(expected), reason)
        for left, right in zip(actual, expected):
            _equal(left, right, reason)
    elif isinstance(expected, float):
        _require(type(actual) in (int, float) and math.isfinite(actual)
                 and abs(actual - expected) <= 1e-12, reason)
    else:
        _require(type(actual) is type(expected) and actual == expected, reason)


def _plans(index, baseline):
    configuration = q.GRID[index // 8]
    seed, paired, order = _FACTORS[index % 8]
    prefix = f"grid{index // 8}/seed{seed}/paired{paired}/order{order}"
    result = []
    for stimulus in ("A", "B", "C", paired):
        kind = "pre" if len(result) < 3 else "pre_replay"
        path = (kind, stimulus) if kind == "pre" else (kind,)
        result.append(_Plan(f"{prefix}/{kind}/{stimulus}", path, kind, None, stimulus, None,
                            baseline, q._trial_segments(configuration, stimulus, paired=False), "baseline"))
    for condition in _TRAIN:
        segments, _, end, t0 = q._training_timeline(configuration, paired, order,
            "paired" if condition == "paired_replay" else condition, controls=True)
        result.append(_Plan(f"{prefix}/{condition}/training", ("training", condition),
                            "training", condition, None, None, baseline, segments, "baseline",
                            True, baseline + q._ticks(t0)))
    paired_plan = result[4]
    training_end = baseline + q._ticks(paired_plan.segments[-1].end_ms)
    for retention in _TIMES:
        target = paired_plan.association + retention * 10
        remaining = target - 1000 - training_end
        if remaining < 0:
            continue
        neutral = tuple(q.Segment(start / 10, min(start + 5000, remaining) / 10, None, None)
                        for start in range(0, remaining, 5000))
        for condition in _RETAIN:
            branch = f"{prefix}/{condition}/T{retention}/retention"
            result.append(_Plan(branch, ("retention", str(retention), condition), "retention",
                condition, None, retention, training_end, neutral,
                f"{prefix}/{condition}/training", True))
            for stimulus in (("A", "B", "C") if condition == "paired" else (paired,)):
                result.append(_Plan(f"{prefix}/{condition}/T{retention}/test/{stimulus}",
                    ("post", str(retention), condition, stimulus), "post", condition, stimulus,
                    retention, target - 1000, q._trial_segments(configuration, stimulus, paired=False), branch))
    return tuple(result)


def _occurrence(event):
    return {"checkpoint_name": event["checkpoint_name"],
            "checkpoint_sha256": event["checkpoint_sha256"], "origin_branch_id": event["branch_id"],
            "checkpoint_sequence": event["sequence"], "sim_tick": event["sim_tick"]}


def _end(plan):
    if not plan.segments:
        return plan.start
    return plan.start + q._ticks(plan.segments[-1].end_ms - plan.segments[0].start_ms)


class _Inventory:
    """Bounded references only: no observation or point vector payloads."""

    def __init__(self, manifest):
        self.manifest = manifest
        self.baseline = None
        self.units = []
        self.bound = 0
        self.points = 0
        self.active = None
        self.occurrences = {}
        self.references = {}
        self.final = None
        self.terminal = None
        self.last_physical = None

    def _unit(self):
        _require(self.baseline is not None and self.bound < 96
                 and self.points == (self.bound // 8) * 12, "grid_unit_order")
        if len(self.units) == self.bound:
            self.units.append(_Unit(self.bound, _plans(self.bound, self.baseline["sim_tick"])))
        return self.units[-1]

    def _shared(self, event):
        _require(event["branch_id"] == "qualification/summary" and event["sim_ms"] == 0
                 and event.get("parent_branch_id") == "qualification/baseline"
                 and event.get("parent_checkpoint_sha256") == self.baseline["checkpoint_sha256"],
                 "grid_summary_parent")

    def consume(self, event):
        kind, sequence = event["type"], event["sequence"]
        _require(self.terminal is None, "grid_after_terminal")
        if kind == "qualification_restore":
            unit = self._unit()
            plan = next((item for item in unit.plans if item.branch == event["branch_id"]), None)
            _require(plan is not None and plan.branch not in unit.roles, "grid_role_order")
            position = unit.plans.index(plan)
            if unit.roles:
                previous = next(reversed(unit.roles.values()))
                prior = unit.plans.index(previous.plan)
                recovery = (plan.kind == "retention" and plan.condition == "paired"
                            and plan.retention is not None
                            and ((previous.plan.retention is not None
                                  and plan.retention > previous.plan.retention)
                                 or (prior == 7 and previous.complete)))
                _require(position > prior and ((position == prior + 1 and previous.complete) or recovery),
                         "grid_role_gap")
            else:
                _require(position == 0, "grid_first_role")
            parent = (self.baseline if plan.parent == "baseline" else
                      unit.roles.get(plan.parent).occurrence if plan.parent in unit.roles else None)
            _require(parent is not None, "grid_restore_source")
            _equal({"checkpoint_name": event.get("parent_checkpoint_name"),
                    "checkpoint_sha256": event.get("checkpoint_sha256"),
                    "origin_branch_id": event.get("parent_branch_id"),
                    "checkpoint_sequence": event.get("parent_checkpoint_sequence"),
                    "sim_tick": event["sim_tick"]}, parent, "grid_restore_occurrence")
            _require(event.get("parent_checkpoint_sha256") == parent["checkpoint_sha256"]
                     and event["sim_tick"] == plan.start and q._ticks(event["sim_ms"]) == plan.start,
                     "grid_restore_clock")
            role = _Role(plan, sequence, parent)
            unit.roles[plan.branch] = role
            self.active = role
            self.references[sequence] = (unit.index, plan.branch)
            self.last_physical = (plan.branch, plan.start, parent["checkpoint_sha256"])
        elif kind == "qualification_observation":
            unit = self._unit()
            role = self.active
            _require(role is not None and role.plan.branch in unit.roles
                     and event["branch_id"] == role.plan.branch and role.occurrence is None,
                     "grid_observation_owner")
            _require(len(role.calls) < len(role.plan.segments), "grid_extra_call")
            _call_frame(event, role.plan, len(role.calls), role.parent)
            role.calls.append(sequence)
            self.references[sequence] = (unit.index, role.plan.branch)
            self.last_physical = (role.plan.branch, event["end_tick"], role.parent["checkpoint_sha256"])
        elif kind == "qualification_checkpoint":
            occurrence = _occurrence(event)
            name = occurrence["checkpoint_name"]
            _require(name not in self.occurrences, "grid_duplicate_occurrence")
            item = self.manifest["checkpoints"].get(name)
            _require(item is not None and item["sha256"] == occurrence["checkpoint_sha256"]
                     and item["size"] == event["checkpoint_size"], "grid_checkpoint_inventory")
            if name == "brain-before.npz":
                _require(self.baseline is None and not self.units and sequence == 0
                         and event["branch_id"] == "qualification/baseline"
                         and event.get("parent_checkpoint_sha256") is None,
                         "grid_baseline")
                self.baseline = occurrence
                self.last_physical = (event["branch_id"], event["sim_tick"], None)
            elif name == "brain-after.npz":
                _require(self.bound == 96 and self.points == 144 and len(self.units) == 96
                         and self.final is None, "grid_early_final")
                _equal((event["branch_id"], event["sim_tick"], event.get("parent_checkpoint_sha256")),
                       self.last_physical, "grid_final_branch")
                self.final = occurrence
            else:
                unit = self._unit()
                role = self.active
                _require(role is not None and role.plan.branch in unit.roles and role.plan.checkpoint
                         and role.occurrence is None and len(role.calls) == len(role.plan.segments)
                         and event["branch_id"] == role.plan.branch
                         and event["sim_tick"] == _end(role.plan)
                         and event.get("parent_checkpoint_sha256") == role.parent["checkpoint_sha256"],
                         "grid_checkpoint_owner")
                if role.plan.kind == "training":
                    _equal((event.get("training_start_tick"), event.get("association_t0_tick"),
                            event.get("training_end_tick")),
                           (role.plan.start, role.plan.association, _end(role.plan)), "grid_training_clock")
                role.occurrence = occurrence
                self.references[sequence] = (unit.index, role.plan.branch)
                self.last_physical = (role.plan.branch, event["sim_tick"], role.parent["checkpoint_sha256"])
            _require(q._ticks(event["sim_ms"]) == event["sim_tick"], "grid_checkpoint_clock")
            self.occurrences[name] = occurrence
        elif kind == "qualification_grid_binding":
            unit = self._unit()
            self._shared(event)
            _binding(event, unit, self.baseline)
            unit.binding = sequence
            unit.failures = tuple(event["failures"])
            self.bound += 1
            self.active = None
        elif kind == "qualification_point":
            _require(self.bound > 0 and self.bound % 8 == 0 and len(self.units) == self.bound
                     and self.points < (self.bound // 8) * 12, "grid_point_order")
            self._shared(event)
            point = event["point"]
            grid, offset = divmod(self.points, 12)
            _equal((point["configuration"], point["response_window"], point["retention_ms"]),
                   (asdict(q.GRID[grid]), asdict(q.RESPONSE_WINDOWS[offset // 4]),
                    float(_TIMES[offset % 4])), "grid_point_coordinates")
            self.references[sequence] = ("point", self.points)
            self.points += 1
        elif kind == "qualification_result":
            _require(self.bound == 96 and self.points == 144 and self.final is not None,
                     "grid_early_terminal")
            self._shared(event)
            self.terminal = sequence
        else:
            raise AnalysisError("grid_component_scope")

    def finish(self, value):
        _require(set(self.occurrences) == set(self.manifest["checkpoints"]), "grid_orphan_checkpoint")
        if type(value) is VerifiedRun:
            _require(len(self.units) == self.bound and self.final is not None and self.terminal is not None,
                     "grid_sealed_incomplete")


def _call_frame(event, plan, index, parent):
    segment = plan.segments[index]
    start = plan.start + q._ticks(segment.start_ms - plan.segments[0].start_ms)
    end = start + q._ticks(segment.end_ms - segment.start_ms)
    phase = "reward_free_test"
    learning = False
    if plan.kind == "training":
        passive = plan.start + q._ticks(segment.start_ms) >= plan.association
        phase = "post_pair_passive" if passive else "pairing"
        learning = (plan.condition in ("paired", "paired_replay") and not passive
                    and (segment.stimulus is not None or segment.stimulation is not None))
    elif plan.kind == "retention":
        phase = "retention"
    expected = {"start_tick": start, "end_tick": end, "duration_ticks": end - start,
                "start_ms": start / 10, "end_ms": end / 10, "sim_ms": end / 10,
                "duration_ms": (end - start) / 10, "local_start_ms": segment.start_ms,
                "local_end_ms": segment.end_ms, "stimulus": segment.stimulus,
                "stimulation": segment.stimulation, "current_mv": q.CURRENT_MV if segment.stimulation else None,
                "learning": learning, "phase": phase,
                "parent_checkpoint_sha256": parent["checkpoint_sha256"]}
    for key, expected_value in expected.items():
        _equal(event.get(key), expected_value, "grid_call_schedule")
    _require(0 < end - start <= 5000, "grid_call_duration")


def _binding(event, unit, baseline):
    seed, paired, order = _FACTORS[unit.index % 8]
    _equal((event.get("binding_version"), event.get("grid_evidence_id"), event.get("grid_index"),
            event.get("seed"), event.get("paired_identity"), event.get("presentation_order")),
           ("qualification-grid-binding/v1", f"grid/{unit.index // 8}/{seed}/{paired}/{order}",
            unit.index // 8, seed, paired, order), "grid_binding_factors")
    _equal(event["baseline_occurrence"], baseline, "grid_binding_baseline")
    failures = event["failures"]
    base = [item for item in failures if item["scope"] == "base"]
    retained = [item for item in failures if item["scope"] == "retention"]
    _require(len(base) <= 1 and (not base or not retained)
             and len({item["retention_ms"] for item in retained}) == len(retained)
             and [item["retention_ms"] for item in retained] == sorted(item["retention_ms"] for item in retained),
             "grid_failure_scopes")
    expected_sequences = {name: {} for name in ("pre", "training", "retention", "post")}
    training, retention = {}, {}
    for role in unit.roles.values():
        target = expected_sequences
        for key in role.plan.path[:-1]:
            target = target.setdefault(key, {})
        target[role.plan.path[-1]] = role.calls
        if role.occurrence is not None:
            if role.plan.kind == "training":
                training[role.plan.condition] = role.occurrence
            else:
                retention.setdefault(str(role.plan.retention), {})[role.plan.condition] = role.occurrence
    for failure in failures:
        # An entered role can fail before a successful restore/call. Only that
        # explicitly declared failure endpoint may contribute an empty list.
        endpoint = _failure_endpoint(unit, failure)
        if endpoint is not None and endpoint.branch not in unit.roles:
            target = expected_sequences
            for key in endpoint.path[:-1]:
                target = target.setdefault(key, {})
            target[endpoint.path[-1]] = []
    _equal(event["observation_sequences"], expected_sequences, "grid_binding_sequences")
    _equal(event["training_occurrences"], training, "grid_binding_training")
    _equal(event["retained_occurrences"], retention, "grid_binding_retention")
    for group in (None, *_TIMES):
        plans = [plan for plan in unit.plans if plan.retention == group]
        present = [unit.roles.get(plan.branch) for plan in plans]
        failure = next((item for item in failures if item["retention_ms"] == group), None)
        if base and group is not None:
            _require(not any(present), "grid_after_base_failure")
            continue
        if failure is None:
            _require(plans and all(role is not None and role.complete for role in present),
                     "grid_undeclared_missing_role")
        else:
            seen_gap = False
            for role in present:
                _require(not seen_gap or role is None, "grid_failure_interior_gap")
                if role is None or not role.complete:
                    seen_gap = True
            if not plans:
                _require(group is not None and failure["stage"] == "retention_timing"
                         and failure["reason"] == "retention_timing", "grid_infeasible_failure")


def _failure_endpoint(unit, failure):
    group = failure["retention_ms"]
    plans = [plan for plan in unit.plans if plan.retention == group]
    if not plans:
        _require(group in _TIMES and failure["stage"] == "retention_timing"
                 and failure["condition"] is None and failure["stimulus"] is None,
                 "grid_failure_timing")
        return None
    if group is None and not unit.roles and failure["stage"] == "base_validation":
        _require(failure["condition"] is None and failure["stimulus"] is None, "grid_failure_base")
        return None
    endpoint = next((plan for plan in plans if plan.branch not in unit.roles
                     or not unit.roles[plan.branch].complete), None)
    if endpoint is None:
        _require(failure["stage"] == ("base_validation" if group is None else "measurement")
                 and failure["condition"] is None and failure["stimulus"] is None,
                 "grid_failure_stage")
        return None
    _require(failure["stage"] == endpoint.kind and failure["condition"] == endpoint.condition,
             "grid_failure_stage")
    role = unit.roles.get(endpoint.branch)
    if role is None:
        stimulus = endpoint.stimulus  # enter_grid_role, before successful restore
    elif len(role.calls) < len(endpoint.segments):
        stimulus = endpoint.segments[len(role.calls)].stimulus  # attempted call, not a fabricated observation
    else:
        stimulus = endpoint.segments[-1].stimulus if endpoint.segments else None
    _require(failure["stimulus"] == stimulus, "grid_failure_stimulus")
    return endpoint


def _finite_vector(values, length, reason, *, integer=False, signed=False):
    _require(type(values) is list and len(values) == length, reason)
    _require(all(type(value) is int and value >= 0 if integer else
                 type(value) in (int, float) and math.isfinite(value) and (signed or value >= 0)
                 for value in values), reason)


def _memory_bounds(parameters):
    """The float64 centered-memory clamp used by rule.advance and engine masks."""
    return parameters["minimum_fraction"] - 1, parameters["maximum_fraction"] - 1


def _summary(value, count, reason, *, lower=None, upper=None):
    _require(type(value) is dict and set(value) == {"count", "minimum", "maximum", "mean", "sha256"}
             and type(value["count"]) is int and value["count"] >= 0 and value["count"] == count
             and type(value["sha256"]) is str and len(value["sha256"]) == 64
             and all(character in "0123456789abcdef" for character in value["sha256"]), reason)
    if count == 0:
        _equal((value["minimum"], value["maximum"], value["mean"]), (None, None, None), reason)
        _require(value["sha256"] == sha256(b"").hexdigest(), reason)
    else:
        numbers = [value[key] for key in ("minimum", "mean", "maximum")]
        _require(all(type(number) in (int, float) and math.isfinite(number) for number in numbers)
                 and numbers[0] <= numbers[1] <= numbers[2], reason)
        if count == 1:
            _require(numbers[0] == numbers[1] == numbers[2], reason)
        if lower is not None:
            _require(numbers[0] >= lower and numbers[2] <= upper, reason)


@dataclass
class _Projection:
    """Only bounded counts, three windows, a final trace and archive slices."""
    counts: list = field(default_factory=lambda: [[0, 0] for _ in q.RESPONSE_WINDOWS])
    coverage: list = field(default_factory=lambda: [0, 0, 0])
    kc: list = field(default_factory=list)
    drive: float | None = None
    all_kc: list = field(default_factory=list)
    maximum: float = 0.0
    trace: tuple | None = None
    endpoint: dict | None = None
    state: tuple | None = None
    secondary: tuple | None = None


def _raw(event, role, projection, context, metadata, unit):
    """Validate one complete raw call and accumulate all windows in that visit."""
    telemetry = event["telemetry"]
    mapping = context["candidate_maps"]["mbon11"]
    edges, kcs = mapping["candidate_edge_indices"], mapping["candidate_kc_indices"]
    _equal(telemetry["engine_identity"], context["engine_identity"], "grid_raw_identity")
    seed = _FACTORS[unit.index % 8][0]
    declared = metadata["rgb_input_sha256"]
    digest = declared["black"] if event["stimulus"] is None else declared["stimuli"][str(seed)][event["stimulus"]]
    _equal((telemetry["input_dtype"], telemetry["input_shape"], telemetry["input_sha256"]),
           ("uint8", [32, 32, 3], digest), "grid_raw_input")
    _equal((telemetry["interval_ms"], telemetry["sim_ms"], telemetry["learning"]),
           (event["duration_ms"], event["sim_ms"], event["learning"]), "grid_raw_call")
    stimulation = ({"population": event["stimulation"], "current_mv": q.CURRENT_MV,
                    "duration_ms": event["duration_ms"]} if event["stimulation"] else None)
    _equal(telemetry["stimulation"], stimulation, "grid_raw_stimulation")
    path, detail = telemetry["pathway_detail"], telemetry["qualification_detail"]
    for key in ("candidate_edge_indices", "candidate_edge_pre_source_ids", "candidate_edge_post_source_ids",
                "candidate_kc_indices", "candidate_kc_source_ids"):
        _equal(path[key], mapping[key], "grid_raw_map")
    _equal((detail["dan_indices"], detail["dan_source_ids"], detail["rate_kc_semantics"], detail["rate_dan_semantics"]),
           (context["dan_indices"], context["dan_source_ids"], "model_trace_state_hz", "model_trace_state_hz"),
           "grid_raw_dan_map")
    counts = path["candidate_kc_spike_counts"]
    _finite_vector(counts, len(kcs), "grid_raw_kc_counts", integer=True)
    kc_group = set(context["engine_identity"]["neural_groups"]["kc"])
    candidate_kcs = set(kcs)
    _require(len(candidate_kcs) == len(kcs) and candidate_kcs <= kc_group, "grid_raw_kc_subset")
    _require(all(count <= event["duration_ticks"] for count in counts), "grid_raw_kc_counts")
    _equal(path["candidate_kc_spikes_by_source_id"],
           dict(zip(mapping["candidate_kc_source_ids"], counts)), "grid_raw_kc_sources")
    drive = path["modeled_visual_drive"]
    for value in drive.values():
        _summary(value, value["count"], "grid_raw_drive", lower=0, upper=float("inf"))
    driven = any(float(drive[name]["mean"] or 0) != 0 for name in ("r1_r6", "r8"))
    if event["stimulus"] is None:
        _require(not driven, "grid_black_drive")
    if not projection.kc:
        projection.kc = [[0] * len(kcs) for _ in q.RESPONSE_WINDOWS]
        projection.all_kc = [0] * len(kcs)
    if driven:
        if projection.drive is None:
            projection.drive = sum(abs(float(drive[name]["mean"] or 0)) for name in ("r1_r6", "r8"))
        projection.all_kc = [left + right for left, right in zip(projection.all_kc, counts)]
    trial = role.plan.kind in ("pre", "pre_replay", "post")
    onset = role.plan.start + 1000
    windows = [(onset + q._ticks(window.start_ms), onset + q._ticks(window.end_ms))
               for window in q.RESPONSE_WINDOWS]
    if trial and driven:
        for index, (start, end) in enumerate(windows):
            if event["start_tick"] < end and event["end_tick"] > start:
                _require(event["start_tick"] >= start and event["end_tick"] <= end,
                         "grid_kc_window_crossing")
                projection.kc[index] = [left + right for left, right in zip(projection.kc[index], counts)]
    cursor = event["start_tick"]
    totals = {name: 0 for name in context["engine_identity"]["neural_groups"]}
    maximum = 0.0
    parameters = context["engine_identity"]["model_provenance"]["parameters"]
    lower, upper = _memory_bounds(parameters)
    _require(type(telemetry["bins"]) is list and telemetry["bins"], "grid_raw_bins")
    for bin_record in telemetry["bins"]:
        length = q._ticks(bin_record["duration_ms"])
        end = q._ticks(bin_record["end_ms"])
        _require(type(bin_record["duration_ms"]) in (int, float)
                 and type(bin_record["end_ms"]) in (int, float)
                 and length == min(100, event["end_tick"] - cursor)
                 and length > 0 and end == cursor + length, "grid_bin_contiguity")
        spikes = bin_record["group_spikes"]
        _require(set(spikes) == set(totals), "grid_bin_groups")
        for name, count in spikes.items():
            _require(type(count) is int and 0 <= count <= length * len(
                context["engine_identity"]["neural_groups"][name]), "grid_bin_count")
            totals[name] += count
        d = bin_record["qualification_detail"]
        _finite_vector(d["rate_kc"], len(edges), "grid_bin_kc_trace")
        _finite_vector(d["rate_dan"], len(context["dan_indices"]), "grid_bin_dan_trace", signed=True)
        for name in ("memory_u", "memory_w"):
            _summary(d[name], len(edges), "grid_bin_memory", lower=lower, upper=upper)
        _summary(d["efficacy"], len(edges), "grid_bin_efficacy", lower=0, upper=float("inf"))
        lo, hi, fraction = d["lower_bound_hits"], d["upper_bound_hits"], d["bound_hit_fraction"]
        _require(type(lo) is int and type(hi) is int and 0 <= lo <= len(edges) and 0 <= hi <= len(edges)
                 and type(fraction) in (int, float) and math.isfinite(fraction) and 0 <= fraction <= 1,
                 "grid_bin_bounds")
        union = round(fraction * len(edges))
        _require((fraction == 0 if not edges else fraction == union / len(edges))
                 and max(lo, hi) <= union <= min(len(edges), lo + hi), "grid_bin_bound_counts")
        if edges:
            summaries = (d["memory_u"], d["memory_w"])
            lower_present = any(summary["minimum"] <= lower for summary in summaries)
            upper_present = any(summary["maximum"] >= upper for summary in summaries)
            _require((lo > 0) == lower_present and (hi > 0) == upper_present,
                     "grid_bin_bound_summary")
            if any(summary["maximum"] <= lower for summary in summaries):
                _require(lo == len(edges), "grid_bin_bound_summary")
            if any(summary["minimum"] >= upper for summary in summaries):
                _require(hi == len(edges), "grid_bin_bound_summary")
        maximum = max(maximum, fraction)
        if trial:
            for index, (start, stop) in enumerate(windows):
                if cursor < stop and end > start:
                    _require(cursor >= start and end <= stop
                             and cursor == start + projection.coverage[index], "grid_window_contiguity")
                    projection.coverage[index] += length
                    projection.counts[index][0] += spikes["mbon11"]
                    projection.counts[index][1] += spikes["mbon07"]
        projection.trace = (tuple(d["rate_kc"]), tuple(d["rate_dan"]))
        projection.endpoint = {name: d[name] for name in ("memory_u", "memory_w", "efficacy")}
        cursor = end
    _require(cursor == event["end_tick"], "grid_bin_endpoint")
    _equal(detail["maximum_bound_hit_fraction"], maximum, "grid_raw_bound_maximum")
    for name, total in totals.items():
        population = len(context["engine_identity"]["neural_groups"][name])
        _equal(telemetry["rates_hz"][name], q._response_rate(total, event["duration_ticks"], population),
               "grid_raw_group_rate")
    residual = totals["kc"] - sum(counts)
    _require(0 <= residual <= event["duration_ticks"] * len(kc_group - candidate_kcs),
             "grid_raw_kc_residual")
    projection.maximum = max(projection.maximum, maximum)


def _file_digest(path):
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _archive(value, event, context, projection, *, keep_state=False):
    path = value.path / "checkpoints" / event["checkpoint_name"]
    _require(path.stat().st_size == event["checkpoint_size"]
             and _file_digest(path) == event["checkpoint_sha256"], "grid_archive_changed")
    provenance = context["engine_identity"]["model_provenance"]
    metadata, arrays = read_checkpoint(path, provenance, context["checkpoint_schema"], context["n"])
    _require(metadata["cursor"] == event["sim_tick"], "grid_archive_clock")
    parameters = provenance["parameters"]
    selected = {}
    for name, mapping in context["candidate_maps"].items():
        positions = mapping["candidate_positions"]
        edges = tuple(mapping["candidate_edge_indices"])
        u, w = arrays["memory_u"][positions].copy(), arrays["memory_w"][positions].copy()
        minimum, maximum = _memory_bounds(parameters)
        lower = np.asarray(minimum, dtype=u.dtype)
        upper = np.asarray(maximum, dtype=u.dtype)
        _require(np.all(u >= lower) and np.all(u <= upper) and np.all(w >= lower) and np.all(w <= upper),
                 "grid_archive_bounds")
        weight = arrays["weight"][list(edges)]
        baseline = np.asarray(mapping["baseline_plastic"], dtype=weight.dtype)
        expected = (baseline * (1 + w)).astype(weight.dtype)
        limit = np.finfo(weight.dtype)
        _require(np.allclose(weight, expected, rtol=2 * limit.eps, atol=limit.tiny), "grid_archive_weight")
        selected[name] = (edges, u, w)
        if name == "mbon11":
            trace = (tuple(arrays["rate_kc"][positions].tolist()), tuple(arrays["rate_dan"].tolist()))
            endpoint = {"memory_u": _array_summary(u), "memory_w": _array_summary(w),
                        "efficacy": _array_summary(weight / baseline)}
            if projection is not None and projection.trace is not None:
                _equal(trace, projection.trace, "grid_archive_trace")
                _equal(endpoint, projection.endpoint, "grid_archive_raw_endpoint")
            if projection is None:
                projection = _Projection()
            projection.trace, projection.endpoint = trace, endpoint
    if keep_state:
        edges, u, w = selected["mbon11"]
        projection.state = (edges, w) if edges else None
        edges07, u07, w07 = selected["mbon07"]
        projection.secondary = q._mbon07_projection(edges07, u07, w07,
            parameters["minimum_fraction"], parameters["maximum_fraction"])
    del arrays
    _require(_file_digest(path) == event["checkpoint_sha256"], "grid_archive_changed")
    return projection


def _measure_unit(unit, projections, context):
    """Adapter from independently streamed projections into existing pure gates."""
    seed, paired, order = _FACTORS[unit.index % 8]
    mapping = context["candidate_maps"]["mbon11"]
    population = len(mapping["target_indices"])
    population07 = len(context["candidate_maps"]["mbon07"]["target_indices"])
    roles = {role.plan.path: (role, projections[branch]) for branch, role in unit.roles.items()}

    def available(path):
        item = roles.get(path)
        return item is not None and len(item[0].calls) == len(item[0].plan.segments)

    def trial(path, window, compartment):
        if not available(path):
            return None
        projection = roles[path][1]
        ticks = q._ticks(q.RESPONSE_WINDOWS[window].end_ms - q.RESPONSE_WINDOWS[window].start_ms)
        return projection.counts[window][compartment] if projection.coverage[window] == ticks else None

    def rates(path, window, compartment):
        count = trial(path, window, compartment)
        return (q._response_rate(count, q._ticks(q.RESPONSE_WINDOWS[window].end_ms
                - q.RESPONSE_WINDOWS[window].start_ms), population if compartment == 0 else population07)
                if count is not None else None)

    paths, initial_reasons = {}, []
    for stimulus in ("A", "B", "C"):
        key = ("pre", stimulus)
        if not available(key):
            continue
        projection = roles[key][1]
        if projection.drive is None:
            initial_reasons.append("modeled_drive")
        elif not mapping["candidate_kc_indices"]:
            initial_reasons.append("missing_kc_observability")
        elif not mapping["candidate_edge_indices"] or not context["dan_indices"]:
            initial_reasons.append("pathway_order")
        else:
            paths[stimulus] = (projection.drive, tuple(mapping["candidate_kc_indices"]),
                tuple(projection.all_kc), tuple(mapping["candidate_edge_indices"]), tuple(context["dan_indices"]))
    state = {condition: roles[("training", condition)][1].state for condition in _TRAIN
             if ("training", condition) in roles and roles[("training", condition)][1].state is not None}
    base_failure = next((item for item in unit.failures if item["scope"] == "base"), None)
    known_empty = (not mapping["candidate_positions"] and not mapping["candidate_edge_indices"]
                   and not mapping["candidate_kc_indices"] and base_failure == {
                       "scope": "base", "stage": "base_validation", "condition": None,
                       "stimulus": None, "retention_ms": None, "reason": "missing_mbon11_observability",
                   } and all(plan.branch in unit.roles and unit.roles[plan.branch].complete
                             for plan in unit.plans if plan.retention is None)
                   and all(roles[("training", condition)][1].state is None for condition in _TRAIN))
    base_bound = max((projection.maximum for branch, projection in projections.items()
                      if unit.roles[branch].plan.retention is None), default=0.0)
    shift = resolution = None
    reasons = ()
    if base_failure is None:
        shift, resolution, reasons = q._base_assessment(state, paths, base_bound, tuple(initial_reasons))
    first = paths.get("A")
    trained07 = roles.get(("training", "paired"))
    matched07 = roles.get(("training", "matched_reference"))
    trained07 = trained07[1].secondary if trained07 else None
    matched07 = matched07[1].secondary if matched07 else None
    common = {"state_shift": shift, "state_replay_resolution": resolution,
              "modeled_drive": tuple(paths[name][0] if name in paths else None for name in ("A", "B", "C")),
              "training_memory_w": tuple(float(v) for v in state["paired"][1]) if "paired" in state else (),
              "matched_memory_w": tuple(float(v) for v in state["matched_reference"][1]) if "matched_reference" in state else (),
              "replay_memory_w": tuple(float(v) for v in state["paired_replay"][1]) if "paired_replay" in state else (),
              "grid_evidence_id": f"grid/{unit.index // 8}/{seed}/{paired}/{order}"}
    if first:
        common.update(candidate_kc_ids=first[1], candidate_edge_indices=first[3], dan_indices=first[4],
            candidate_edge_pre_source_ids=tuple(mapping["candidate_edge_pre_source_ids"]),
            candidate_edge_post_source_ids=tuple(mapping["candidate_edge_post_source_ids"]),
            candidate_kc_source_ids=tuple(mapping["candidate_kc_source_ids"]),
            dan_source_ids=tuple(context["dan_source_ids"]))
    if available(("training", "paired")):
        role, projection = roles[("training", "paired")]
        common.update(training_t0_ms=role.plan.association / 10, training_end_ms=_end(role.plan) / 10)
        if projection.trace:
            common.update(rate_kc=projection.trace[0], rate_dan=projection.trace[1])
    if trained07:
        common.update(mbon07_edge_indices=trained07[0], training_mbon07_memory_u=trained07[1],
            training_mbon07_memory_w=trained07[2], mbon07_lower_bound_hits=trained07[3],
            mbon07_upper_bound_hits=trained07[4], mbon07_bound_hit_fraction=trained07[5],
            mbon07_lower_bound=trained07[6], mbon07_upper_bound=trained07[7])
    if matched07:
        common.update(matched_mbon07_memory_u=matched07[1], matched_mbon07_memory_w=matched07[2],
            matched_mbon07_lower_bound_hits=matched07[3], matched_mbon07_upper_bound_hits=matched07[4],
            matched_mbon07_bound_hit_fraction=matched07[5])
    result, unavailable = [], False
    for window_index, window in enumerate(q.RESPONSE_WINDOWS):
        for retention in _TIMES:
            failure = base_failure or next((item for item in unit.failures if item["retention_ms"] == retention), None)
            failure_reason = failure["reason"] if failure else None
            infeasible = (failure is not None and failure["scope"] == "retention"
                          and failure["stage"] == "retention_timing"
                          and not any(plan.retention == retention for plan in unit.plans))
            unavailable |= failure is not None and not infeasible and not known_empty
            absent = (None, None, None)
            compact = q.ReplicateMeasurement(seed, paired, order, absent, absent, absent, absent,
                None, q._one_spike_rate(population, window), None, None, None, None, None, None,
                absent, ((), ()), (), (), (), (), (), (failure_reason,) if failure else reasons)
            updates = dict(common)
            for name, kind, compartment in (("pre_mbon11", "pre", 0), ("pre_mbon07", "pre", 1),
                                           ("post_mbon11", "post", 0), ("post_mbon07", "post", 1)):
                updates[name] = tuple(rates((kind, identity) if kind == "pre" else
                    ("post", str(retention), "paired", identity), window_index, compartment)
                    for identity in ("A", "B", "C"))
            if failure is None:
                updates["maximum_bound_hit_fraction"] = max(base_bound,
                    *(projection.maximum for branch, projection in projections.items()
                      if unit.roles[branch].plan.retention == retention))
                updates["test_cs_onset_ms"] = common["training_t0_ms"] + retention
                if trained07 and matched07 and trained07[0] == matched07[0]:
                    updates["mbon07_state_shift"] = q._state_difference(np.asarray(trained07[2]), np.asarray(matched07[2]))
                vector_paths = (("pre", "A"), ("pre", "B"),
                                ("post", str(retention), "paired", "A"),
                                ("post", str(retention), "paired", "B"))
                orders = ()
                if all(available(path) and roles[path][1].drive is not None for path in vector_paths) \
                        and mapping["candidate_kc_indices"] and mapping["candidate_edge_indices"] and context["dan_indices"]:
                    vectors = [tuple(roles[path][1].kc[window_index]) for path in vector_paths]
                    updates.update(candidate_kc_vectors=tuple(vectors[:2]), post_candidate_kc_vectors=tuple(vectors[2:]))
                    orders = (tuple(mapping["candidate_kc_indices"]),) * 4
                counts = q._ResponseCounts(population, q._ticks(window.end_ms - window.start_ms),
                    tuple(trial(("pre", identity), window_index, 0) for identity in ("A", "B", "C")),
                    tuple(trial(("post", str(retention), "paired", identity), window_index, 0)
                          for identity in ("A", "B", "C")),
                    trial(("pre_replay",), window_index, 0),
                    trial(("post", str(retention), "frozen_plasticity", paired), window_index, 0),
                    trial(("post", str(retention), "matched_reference", paired), window_index, 0))
                compact = q._measurement_from_compact(replace(compact, **updates), counts=counts, pathway_orders=orders)
            else:
                compact = q._measurement_from_compact(replace(compact, **updates), failure_reason=failure_reason)
            result.append(compact)
    return tuple(result), unavailable


def _terminal(event, selection):
    _equal((event["status"], event["selected_configuration"], event["selected_window"],
            event["selected_retention_ms"], event["observed_effect_sign"]),
           ("supported" if selection else "unsupported", asdict(selection[0]) if selection else None,
            asdict(selection[1]) if selection else None, selection[2] if selection else None,
            selection[3] if selection else None), "grid_terminal_selection")


def _reduce_qualification_grid(value):
    """Consume exactly two complete authenticated event passes, without an engine."""
    try:
        context = _verified_qualification_context(value)
        manifest = value.manifest
        metadata = _qualification_declarations(manifest)
        inventory = _Inventory(manifest)
        error = None
        for event in value.iter_events():
            if error is None:
                try:
                    inventory.consume(event)
                except (KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as failure:
                    error = str(failure) if isinstance(failure, AnalysisError) else "grid_inventory"
        if error is None:
            try:
                inventory.finish(value)
            except AnalysisError as failure:
                error = str(failure)
        current = {}
        measured = []
        points = []
        unavailable = False
        baseline_projection = last_projection = None
        for event in value.iter_events():
            if error is not None:
                continue
            try:
                kind = event["type"]
                reference = inventory.references.get(event["sequence"])
                if kind == "qualification_restore":
                    unit_index, branch = reference
                    unit = inventory.units[unit_index]
                    source = unit.roles[branch].plan.parent
                    source_projection = (baseline_projection if source == "baseline"
                                         else current[unit_index][source])
                    projection = _Projection(trace=source_projection.trace, endpoint=source_projection.endpoint)
                    current.setdefault(unit_index, {})[branch] = projection
                    last_projection = _Projection(trace=projection.trace, endpoint=projection.endpoint)
                    _require(len(current) + len(measured) <= 8, "grid_projection_bound")
                elif kind == "qualification_observation":
                    unit_index, branch = reference
                    unit = inventory.units[unit_index]
                    _raw(event, unit.roles[branch], current[unit_index][branch], context, metadata, unit)
                    projection = current[unit_index][branch]
                    last_projection = _Projection(trace=projection.trace, endpoint=projection.endpoint)
                elif kind == "qualification_checkpoint":
                    projection = None
                    keep_state = False
                    if reference is not None:
                        unit_index, branch = reference
                        projection = current[unit_index][branch]
                        keep_state = inventory.units[unit_index].roles[branch].plan.kind == "training"
                    elif event["checkpoint_name"] == "brain-after.npz":
                        projection = last_projection
                    projection = _archive(value, event, context, projection, keep_state=keep_state)
                    if event["checkpoint_name"] == "brain-before.npz":
                        baseline_projection = projection
                    last_projection = _Projection(trace=projection.trace, endpoint=projection.endpoint)
                elif kind == "qualification_grid_binding":
                    unit = inventory.units[len(measured) + (len(points) // 12) * 8]
                    unit_projections = current.pop(unit.index, {})
                    replicas, missing = _measure_unit(unit, unit_projections, context)
                    del unit_projections
                    measured.append(replicas)
                    unavailable |= missing
                    _require(len(measured) <= 8, "grid_projection_bound")
                elif kind == "qualification_point":
                    point_index = reference[1]
                    offset = point_index % 12
                    replicas = tuple(unit[offset] for unit in measured)
                    grid = point_index // 12
                    summary = q._summarize_point(q.GRID[grid], q.RESPONSE_WINDOWS[offset // 4],
                                                 float(_TIMES[offset % 4]),
                                                 tuple(q._replicate_summary(item) for item in replicas))
                    expected = q.QualificationPoint(summary.configuration, summary.response_window,
                        summary.retention_ms, replicas, summary.mean_delta_hz, summary.reasons)
                    _equal(event["point"], expected, "grid_point_mismatch")
                    points.append(summary)
                    del replicas, expected
                    if offset == 11:
                        measured.clear()
                elif kind == "qualification_result":
                    selection = q._select_compact_points(points) if not unavailable else None
                    _terminal(event, selection)
            except (OSError, KeyError, TypeError, ValueError, IndexError, AttributeError, OverflowError) as failure:
                error = str(failure) if isinstance(failure, AnalysisError) else "grid_measurement"
        _verified_qualification_context(value)
        if error is not None:
            raise AnalysisError(error)
        complete = inventory.bound == 96 and len(points) == 144 and not unavailable
        selection = q._select_compact_points(points) if complete else None
        return _GridAssessment("selected" if selection else "negative" if complete else "inconclusive",
            () if complete else ("grid_unavailable",) if unavailable else ("grid_incomplete",),
            selection, tuple(points), len(inventory.units))
    except (OSError, TypeError, ValueError, KeyError, OverflowError) as failure:
        if isinstance(failure, AnalysisError):
            raise
        raise AnalysisError("grid_artifact_changed_or_unverified") from failure
