"""Bounded exploratory PPL101/KC-to-MBON11 model qualification.

This module records model diagnostics and selects a declared assay setting. It
does not interpret the setting as biological learning or behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from typing import Literal

import numpy as np

from .executor import advance_neutral
from .stimuli import AssayStimuli


@dataclass(frozen=True)
class GridConfiguration:
    cs_duration_ms: float
    dan_onset_ms: float
    post_pair_gap_ms: float


@dataclass(frozen=True)
class ResponseWindow:
    start_ms: float
    end_ms: float


@dataclass(frozen=True)
class Segment:
    start_ms: float
    end_ms: float
    stimulus: str | None
    stimulation: str | None


GRID = tuple(
    GridConfiguration(cs, onset, gap)
    for cs in (100.0, 300.0)
    for onset in (-100.0, 0.0, 100.0)
    for gap in (500.0, 10000.0)
)
RESPONSE_WINDOWS = (
    ResponseWindow(0.0, 100.0),
    ResponseWindow(0.0, 300.0),
    ResponseWindow(100.0, 300.0),
)
RETENTION_CANDIDATES_MS = (10000.0, 20000.0, 30000.0, 60000.0)
QUALIFICATION_SEEDS = (11, 23)
CONFIRMATION_SEEDS = (101, 113)
PULSE_DURATION_MS = 100.0
CURRENT_MV = 20.0
UNPAIRED_SEPARATION_MS = 10000.0


@dataclass(frozen=True)
class ReplicateMeasurement:
    seed: int
    paired_identity: str
    presentation_order: str
    pre_mbon11: tuple[float | None, float | None, float | None]
    post_mbon11: tuple[float | None, float | None, float | None]
    pre_mbon07: tuple[float | None, float | None, float | None]
    post_mbon07: tuple[float | None, float | None, float | None]
    delta_hz: float | None
    one_spike_rate_hz: float | None
    response_replay_resolution_hz: float | None
    state_replay_resolution: float | None
    state_shift: float | None
    washout_hz: float | None
    washout_threshold_hz: float | None
    maximum_bound_hit_fraction: float | None
    modeled_drive: tuple[float | None, float | None, float | None]
    candidate_kc_vectors: tuple[tuple[int, ...], tuple[int, ...]]
    candidate_kc_ids: tuple[int, ...]
    candidate_edge_indices: tuple[int, ...]
    dan_indices: tuple[int, ...]
    rate_kc: tuple[float, ...]
    rate_dan: tuple[float, ...]
    reasons: tuple[str, ...]
    training_memory_w: tuple[float, ...] = ()
    matched_memory_w: tuple[float, ...] = ()
    replay_memory_w: tuple[float, ...] = ()
    candidate_edge_pre_source_ids: tuple[str, ...] = ()
    candidate_edge_post_source_ids: tuple[str, ...] = ()
    candidate_kc_source_ids: tuple[str, ...] = ()
    dan_source_ids: tuple[str, ...] = ()
    post_candidate_kc_vectors: tuple[tuple[int, ...], tuple[int, ...]] = ((), ())
    training_t0_ms: float | None = None
    training_end_ms: float | None = None
    test_cs_onset_ms: float | None = None
    mbon07_edge_indices: tuple[int, ...] = ()
    training_mbon07_memory_u: tuple[float, ...] = ()
    training_mbon07_memory_w: tuple[float, ...] = ()
    matched_mbon07_memory_u: tuple[float, ...] = ()
    matched_mbon07_memory_w: tuple[float, ...] = ()
    mbon07_state_shift: float | None = None
    mbon07_lower_bound_hits: int | None = None
    mbon07_upper_bound_hits: int | None = None
    mbon07_bound_hit_fraction: float | None = None
    mbon07_lower_bound: float | None = None
    mbon07_upper_bound: float | None = None
    matched_mbon07_lower_bound_hits: int | None = None
    matched_mbon07_upper_bound_hits: int | None = None
    matched_mbon07_bound_hit_fraction: float | None = None
    grid_evidence_id: str | None = None


@dataclass(frozen=True)
class QualificationPoint:
    configuration: GridConfiguration
    response_window: ResponseWindow
    retention_ms: float
    replicates: tuple[ReplicateMeasurement, ...]
    mean_delta_hz: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class _ReplicateSummary:
    """Selection inputs without candidate vectors or raw observations."""
    seed: int
    paired_identity: str
    presentation_order: str
    delta_hz: float | None
    reasons: tuple[str, ...]
    washout_hz: float | None
    washout_threshold_hz: float | None


@dataclass(frozen=True)
class _PointSummary:
    configuration: GridConfiguration
    response_window: ResponseWindow
    retention_ms: float
    mean_delta_hz: float | None
    reasons: tuple[str, ...]
    complete_factors: bool
    washout_eligible: bool


@dataclass(frozen=True)
class ControlMeasurement:
    seed: int
    paired_identity: str
    presentation_order: str
    condition: str
    elapsed_ms: float
    visual_exposure_ms: float
    unpaired_nearest_cs_boundary_ms: float | None
    mbon11_hz: float | None
    mbon07_hz: float | None
    pre_mbon11: tuple[float, float, float] = (0.0, 0.0, 0.0)
    post_mbon11: tuple[float, float, float] = (0.0, 0.0, 0.0)
    pre_mbon07: tuple[float, float, float] = (0.0, 0.0, 0.0)
    post_mbon07: tuple[float, float, float] = (0.0, 0.0, 0.0)
    delta_hz: float | None = None
    training_t0_ms: float | None = None
    test_cs_onset_ms: float | None = None
    training_mbon11_memory_w: tuple[float, ...] = ()
    matched_mbon11_memory_w: tuple[float, ...] = ()
    mbon07_edge_indices: tuple[int, ...] = ()
    training_mbon07_memory_u: tuple[float, ...] = ()
    training_mbon07_memory_w: tuple[float, ...] = ()
    matched_mbon07_memory_u: tuple[float, ...] = ()
    matched_mbon07_memory_w: tuple[float, ...] = ()
    mbon07_state_shift: float | None = None
    mbon07_lower_bound_hits: int | None = None
    mbon07_upper_bound_hits: int | None = None
    mbon07_bound_hit_fraction: float | None = None
    mbon07_lower_bound: float | None = None
    mbon07_upper_bound: float | None = None
    matched_mbon07_lower_bound_hits: int | None = None
    matched_mbon07_upper_bound_hits: int | None = None
    matched_mbon07_bound_hit_fraction: float | None = None


@dataclass(frozen=True)
class QualificationResult:
    status: Literal["supported", "unsupported"]
    family: str
    seeds: tuple[int, int]
    points: tuple[QualificationPoint, ...]
    selected_configuration: GridConfiguration | None
    selected_window: ResponseWindow | None
    selected_retention_ms: float | None
    observed_effect_sign: int | None
    controls: tuple[ControlMeasurement, ...]
    _engine_identity_json: str
    _benchmark_items: tuple[tuple[str, float | int], ...]

    @property
    def engine_identity(self) -> dict:
        return json.loads(self._engine_identity_json)

    @property
    def benchmark(self) -> dict:
        return dict(self._benchmark_items)


class _GateFailure(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _ticks(value: float) -> int:
    scaled = value * 10
    if not math.isfinite(value) or abs(scaled - round(scaled)) > 1e-7:
        raise ValueError("Timing must be finite on the 0.1 ms grid")
    return round(scaled)


def _split_intervals(
    start_ms: float,
    end_ms: float,
    visual: tuple[tuple[float, float, str], ...],
    pulse: tuple[float, float] | None,
    *,
    extra_cuts: tuple[float, ...] = (),
) -> tuple[Segment, ...]:
    """Split one gap-free timeline at every visual and DAN boundary."""
    start_tick, end_tick = _ticks(start_ms), _ticks(end_ms)
    cuts = {start_tick, end_tick}
    cuts.update(_ticks(cut) for cut in extra_cuts)
    visual_ticks = tuple((_ticks(a), _ticks(b), name) for a, b, name in visual)
    pulse_ticks = None if pulse is None else (_ticks(pulse[0]), _ticks(pulse[1]))
    for a, b, _ in visual_ticks:
        cuts.update((a, b))
    if pulse_ticks is not None:
        cuts.update(pulse_ticks)
    boundaries = sorted(cut for cut in cuts if start_tick <= cut <= end_tick)
    segments = []
    for left, right in zip(boundaries, boundaries[1:]):
        while left < right:
            stop = min(left + 5000, right)
            stimulus = next((name for a, b, name in visual_ticks if a <= left < b), None)
            stimulation = (
                "ppl101" if pulse_ticks is not None
                and pulse_ticks[0] <= left < pulse_ticks[1] else None
            )
            segments.append(Segment(left / 10, stop / 10, stimulus, stimulation))
            left = stop
    if not segments or segments[0].start_ms != start_ms or segments[-1].end_ms != end_ms:
        raise ValueError("Incomplete qualification timeline")
    return tuple(segments)


def _trial_segments(
    configuration: GridConfiguration,
    identity: str,
    *,
    paired: bool,
) -> tuple[Segment, ...]:
    cs_end = configuration.cs_duration_ms
    pulse = (
        (configuration.dan_onset_ms, configuration.dan_onset_ms + PULSE_DURATION_MS)
        if paired else None
    )
    return _split_intervals(-100.0, cs_end + 200.0, ((0.0, cs_end, identity),),
                            pulse, extra_cuts=(100.0, 300.0))


def _training_timeline(
    configuration: GridConfiguration,
    paired_identity: str,
    order: str,
    condition: str,
    *,
    controls: bool = False,
) -> tuple[tuple[Segment, ...], float, float, float]:
    first, second = order
    first_onset = (UNPAIRED_SEPARATION_MS + PULSE_DURATION_MS
                   if controls else 100.0)
    first_end = first_onset + configuration.cs_duration_ms
    first_trial_end = first_end + 200.0
    second_trial_start = (
        max(first_trial_end, first_end + configuration.post_pair_gap_ms)
        if first == paired_identity else first_trial_end
    )
    second_onset = second_trial_start + 100.0
    second_end = second_onset + configuration.cs_duration_ms
    normal_end = (
        max(second_end + 200.0, second_end + configuration.post_pair_gap_ms)
        if second == paired_identity else second_end + 200.0
    )
    visual = ((first_onset, first_end, first), (second_onset, second_end, second))
    paired_onset = first_onset if first == paired_identity else second_onset
    pulse = None
    if condition in {"paired", "frozen_plasticity"}:
        start = paired_onset + configuration.dan_onset_ms
        pulse = (start, start + PULSE_DURATION_MS)
    elif condition == "temporally_unpaired":
        pulse = ((0.0, PULSE_DURATION_MS) if controls else
                 (second_end + UNPAIRED_SEPARATION_MS,
                  second_end + UNPAIRED_SEPARATION_MS + PULSE_DURATION_MS))
    elif condition not in {"no_external_dan", "matched_reference"}:
        raise ValueError(f"Unknown qualification condition: {condition}")
    total_end = normal_end
    if pulse is not None:
        total_end = max(total_end, pulse[1])
    t0 = max(second_end, pulse[1] if pulse is not None else second_end)
    return _split_intervals(0.0, total_end, visual, pulse), second_end, total_end, t0


def _qualification_role_slots(selected_retention_ms: int) -> dict:
    """Finite future c.2/d/e role contract, not a runtime cap or legacy conformance claim.

    Slots are exact factor tuples, independent of a future producer's namespace.
    A partial route uses a subset; it cannot introduce another candidate or role.
    Relevant counts include first restores, sources, summaries and terminal; raw
    observations are separately bounded and must still be completely consumed.
    """
    if type(selected_retention_ms) is not int or selected_retention_ms not in (10000, 20000, 30000, 60000):
        raise ValueError("Selected retention must be one declared integer T")
    categories = {name: set() for name in ("grid", "selected", "replay", "shared")}
    checkpoints = set()
    events = {}
    raw = 0

    def branch(category, slot):
        categories[category].add(slot)

    def event(kind, slot):
        events.setdefault(kind, set()).add(slot)

    def source(slot):
        checkpoints.add(slot)
        event("checkpoint", slot)

    factors = [(seed, paired, order) for seed in QUALIFICATION_SEEDS
               for paired in ("A", "B") for order in ("AB", "BA")]
    acquisitions = ("paired", "matched_reference", "frozen_plasticity", "paired_replay")
    ordinary = ("paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired", "matched_reference")
    conditions = (*ordinary, "necessity", "sufficiency", "sham")
    for index, configuration in enumerate(GRID):
        trial_calls = len(_trial_segments(configuration, "A", paired=False))
        for seed, paired, order in factors:
            unit = ("grid", index, seed, paired, order)
            event("grid_binding", unit)
            for stimulus in ("A", "B", "C"):
                branch("grid", (*unit, "pre", stimulus))
            branch("grid", (*unit, "pre_replay", paired))
            raw += 4 * trial_calls
            for condition in acquisitions:
                slot = (*unit, "training", condition)
                branch("grid", slot)
                source(slot)
                schedule, _, end, t0 = _training_timeline(
                    configuration, paired, order,
                    "paired" if condition == "paired_replay" else condition, controls=True,
                )
                raw += len(schedule)
            for retention in (10000, 20000, 30000, 60000):
                gap = max(0, _ticks(t0 + retention - 100 - end))
                raw += 3 * ((gap + 4999) // 5000) + 5 * trial_calls
                for condition in ("paired", "frozen_plasticity", "matched_reference"):
                    slot = (*unit, "retention", retention, condition)
                    branch("grid", slot)
                    source(slot)
                    for stimulus in (("A", "B", "C") if condition == "paired" else (paired,)):
                        branch("grid", (*unit, "post", retention, condition, stimulus))
        for window in RESPONSE_WINDOWS:
            for retention in (10000, 20000, 30000, 60000):
                event("point", (index, window.start_ms, window.end_ms, retention))
    times = (selected_retention_ms, selected_retention_ms + 60000)
    for seed, paired, order in factors:
        unit = ("selected", seed, paired, order)
        for condition in conditions:
            slot = (*unit, "training" if condition in ordinary else "intervention", condition)
            branch("selected", slot)
            source(slot)
            event("training" if condition in ordinary else "intervention", slot)
            for retention in times:
                retained = (*unit, "retention", condition, retention)
                branch("selected", retained)
                event("anchor", retained)
                for stimulus in ("A", "B", "C"):
                    post = (*unit, "post", condition, retention, stimulus)
                    branch("selected", post)
                    branch("replay", ("replay", *post))
                    event("response", post)
                    event("response_replay", post)
        for stimulus in ("A", "B", "C"):
            pre = (*unit, "pre", stimulus)
            branch("selected", pre)
            branch("replay", ("replay", *pre))
            event("response_replay", pre)
            for condition in conditions:
                for retention in times:
                    event("response", (*pre, condition, retention))
        for condition in ordinary:
            event("control_summary", (*unit, condition))
        # Conservative selected maximum over the fixed grid, independent of selection.
        raw += max(sum(len(_training_timeline(config, paired, order, condition, controls=True)[0])
                       for condition in ordinary) for config in GRID)
        raw += 8 * sum((retention * 10 + 4999) // 5000 for retention in times)
        raw += (3 + 8 * 2 * 3) * 4 * 2  # Originals plus all physical response repeats.
    categories["shared"].update({("shared", "baseline"), ("shared", "summary")})
    source(("shared", "baseline"))
    source(("shared", "final"))
    event("terminal", ("shared", "terminal"))
    for category in ("grid", "selected", "replay"):
        for slot in categories[category]:
            event("branch_first", slot)
    # Baseline first is its checkpoint; summary first is its first grid binding.
    return {
        "branches": frozenset().union(*categories.values()),
        "checkpoints": frozenset(checkpoints),
        "branch_categories": {key: len(value) for key, value in categories.items()},
        "relevant_events": {key: len(value) for key, value in events.items()},
        "raw_observation_upper_bound": raw,
    }


def _aggregate_window(
    telemetries: list[dict] | tuple[dict, ...],
    cs_onset_ms: float,
    window: ResponseWindow,
    population: str,
    group_size: int,
) -> float:
    """Sum raw bin counts; bins crossing window edges are not observable."""
    if group_size <= 0:
        raise ValueError("Missing population observability")
    start = _ticks(cs_onset_ms + window.start_ms)
    end = _ticks(cs_onset_ms + window.end_ms)
    spikes = 0
    cursor = start
    for telemetry in telemetries:
        for bin_record in telemetry["bins"]:
            bin_end = _ticks(float(bin_record["end_ms"]))
            duration = _ticks(float(bin_record["duration_ms"]))
            bin_start = bin_end - duration
            if bin_start < end and bin_end > start:
                if bin_start < start or bin_end > end:
                    raise ValueError("Response bin crosses a half-open window boundary")
                if duration <= 0 or bin_start != cursor:
                    raise ValueError("Response window bins are not ordered and contiguous")
                spikes += int(bin_record["group_spikes"][population])
                cursor = bin_end
    if cursor != end:
        raise ValueError("Response window has missing bins")
    return _response_rate(spikes, end - start, group_size)


def _response_rate(spikes: int, duration_ticks: int, population: int) -> float:
    """Pure rate arithmetic after the extraction layer proves tick coverage."""
    if population <= 0 or duration_ticks <= 0:
        raise ValueError("Missing population or response duration")
    return spikes / (population * (duration_ticks / 10000.0))


def _replicate_summary(item: ReplicateMeasurement) -> _ReplicateSummary:
    return _ReplicateSummary(item.seed, item.paired_identity, item.presentation_order,
                             item.delta_hz, item.reasons, item.washout_hz,
                             item.washout_threshold_hz)


def _summarize_point(configuration: GridConfiguration, window: ResponseWindow,
                     retention_ms: float, replicates: tuple[_ReplicateSummary, ...]) -> _PointSummary:
    reasons = tuple(dict.fromkeys(reason for item in replicates for reason in item.reasons))
    mean = (sum(item.delta_hz for item in replicates) / len(replicates)
            if not reasons and len(replicates) == 8 else None)
    if mean == 0:
        reasons += ("zero_mean_delta",)
        mean = None
    return _selection_summary(configuration, window, retention_ms, replicates, mean, reasons)


def _selection_summary(configuration: GridConfiguration, window: ResponseWindow,
                       retention_ms: float, replicates: tuple[_ReplicateSummary, ...],
                       mean: float | None, reasons: tuple[str, ...]) -> _PointSummary:
    expected = {(seed, paired, order) for seed in QUALIFICATION_SEEDS
                for paired in ("A", "B") for order in ("AB", "BA")}
    keys = {(item.seed, item.paired_identity, item.presentation_order) for item in replicates}
    complete = keys == expected and len(replicates) == len(expected)
    washout = not any(item.washout_hz is None or item.washout_threshold_hz is None
                      or item.washout_hz > item.washout_threshold_hz for item in replicates)
    return _PointSummary(configuration, window, retention_ms, mean, reasons, complete, washout)


def _select_compact_points(points: tuple[_PointSummary, ...] | list[_PointSummary]) -> tuple | None:
    """Select from scalar point summaries; no observation/vector payload survives."""
    best = None
    for configuration in GRID:
        for window in RESPONSE_WINDOWS:
            chosen = None
            for retention in RETENTION_CANDIDATES_MS:
                point = next((point for point in points
                              if point.configuration == configuration
                              and point.response_window == window
                              and point.retention_ms == retention), None)
                if point is None or not point.complete_factors or not point.washout_eligible:
                    continue
                chosen = point
                break
            if chosen is None or chosen.reasons or chosen.mean_delta_hz in (None, 0):
                continue
            if best is None or abs(chosen.mean_delta_hz) > abs(best.mean_delta_hz):
                best = chosen
    if best is None:
        return None
    return (best.configuration, best.response_window, best.retention_ms,
            1 if best.mean_delta_hz > 0 else -1)


def _select_points(
    points: tuple[QualificationPoint, ...] | list[QualificationPoint],
) -> tuple[GridConfiguration, ResponseWindow, float, int] | None:
    compact = []
    for point in points:
        compact.append(_selection_summary(
            point.configuration, point.response_window, point.retention_ms,
            tuple(_replicate_summary(item) for item in point.replicates),
            point.mean_delta_hz, point.reasons,
        ))
    return _select_compact_points(compact)


def benchmark(
    result: QualificationResult | None = None,
    *,
    simulated_seconds: float = 0.0,
    wall_seconds: float = 0.0,
    event_count: int = 0,
    checkpoint_bytes: int = 0,
    peak_event_buffer_bytes: int = 0,
) -> dict:
    """Return measured or caller-observed resource counters, without execution."""
    values = (result.benchmark if result is not None else {
        "simulated_seconds": simulated_seconds,
        "wall_seconds": wall_seconds,
        "event_count": event_count,
        "checkpoint_bytes": checkpoint_bytes,
        "peak_event_buffer_bytes": peak_event_buffer_bytes,
    })
    if set(values) != {"simulated_seconds", "wall_seconds", "event_count",
                       "checkpoint_bytes", "peak_event_buffer_bytes"}:
        raise ValueError("Invalid benchmark fields")
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value < 0 for value in values.values()):
        raise ValueError("Benchmark values must be finite and nonnegative")
    return dict(values)


class _Run:
    def __init__(self, engine, recorder, identity: dict):
        self.engine = engine
        self.recorder = recorder
        self.identity = identity
        self.event_count = 0
        self.simulated_ms = 0.0
        self.checkpoint_bytes = 0
        self.peak_event_buffer_bytes = 0
        self.branch_id = "qualification/baseline"
        self.parent_checkpoint_sha256: str | None = None
        self.checkpoints: dict[Path, tuple[str, str, str]] = {}
        self.checkpoint_serial = 0
        self.phase = "baseline"
        self.occurrences: dict[Path, dict] = {}
        self.grid_capture: dict | None = None
        self.capture_sequences: list[int] | None = None
        self.capture_stage = "base_validation"
        self.capture_condition: str | None = None
        self.capture_stimulus: str | None = None
        self.capture_retention: int | None = None
        self.partial_base: dict = {}
        self.partial_retained: dict = {}

    def begin_grid(self, baseline: Path, index: int, seed: int, paired: str, order: str) -> None:
        self.partial_base = {}
        self.partial_retained = {}
        self.capture_sequences = None
        self.capture_stage, self.capture_condition = "base_validation", None
        self.capture_stimulus = self.capture_retention = None
        # Arithmetic/orchestration doubles without real ingest/position have no evidence refs.
        if baseline not in self.occurrences:
            self.grid_capture = None
            return
        self.grid_capture = {
            "binding_version": "qualification-grid-binding/v1",
            "grid_evidence_id": f"grid/{index}/{seed}/{paired}/{order}",
            "grid_index": index, "seed": seed, "paired_identity": paired,
            "presentation_order": order,
            "baseline_occurrence": dict(self.occurrences[baseline]),
            "training_occurrences": {}, "retained_occurrences": {},
            "observation_sequences": {"pre": {}, "training": {}, "retention": {}, "post": {}},
            "failures": [],
        }

    def enter_grid_role(self, stage: str, path: tuple[str, ...] | None = None,
                        *, condition: str | None = None, stimulus: str | None = None,
                        retention_ms: int | None = None) -> None:
        self.capture_stage, self.capture_condition = stage, condition
        self.capture_stimulus, self.capture_retention = stimulus, retention_ms
        self.capture_sequences = None
        if self.grid_capture is not None and path is not None:
            target = self.grid_capture["observation_sequences"]
            for key in path[:-1]:
                target = target.setdefault(key, {})
            target[path[-1]] = []
            self.capture_sequences = target[path[-1]]

    def grid_failure(self, reason: str) -> None:
        if self.grid_capture is not None:
            self.grid_capture["failures"].append({
                "scope": "base" if self.capture_retention is None else "retention",
                "stage": self.capture_stage, "condition": self.capture_condition,
                "stimulus": self.capture_stimulus, "retention_ms": self.capture_retention,
                "reason": reason,
            })
        self.capture_sequences = None

    def finish_grid(self, baseline: Path) -> None:
        if self.grid_capture is not None:
            self.emit({
                "type": "qualification_grid_binding", "branch_id": "qualification/summary",
                "sim_ms": 0.0, "parent_branch_id": "qualification/baseline",
                "parent_checkpoint_sha256": self.checkpoints[baseline][1],
                **self.grid_capture,
            })
        self.grid_capture = None
        self.capture_sequences = None

    def emit(self, event: dict) -> int | None:
        event = {key: value for key, value in event.items()
                 if key not in {"parent_branch_id", "parent_checkpoint_sha256"}
                 or value is not None}
        encoded = json.dumps(event, allow_nan=False, separators=(",", ":"))
        self.peak_event_buffer_bytes = max(self.peak_event_buffer_bytes,
                                           len(encoded.encode("utf-8")))
        sequence = getattr(self.recorder, "next_sequence", None)
        self.recorder.append(event)
        self.event_count += 1
        return sequence

    def checkpoint(self, path: Path, *, logical_name: str | None = None,
                   training_start_tick: int | None = None,
                   association_t0_tick: int | None = None) -> dict | None:
        self.engine.brain.checkpoint(path)
        size = path.stat().st_size
        self.checkpoint_bytes += size
        digest_state = sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest_state.update(chunk)
        digest = digest_state.hexdigest()
        if logical_name is None:
            if path.name == "baseline.npz" and not self.checkpoints:
                logical_name = "brain-before.npz"
            else:
                self.checkpoint_serial += 1
                logical_name = f"branch-{self.checkpoint_serial:08d}.npz"
        ingest = getattr(self.recorder, "ingest_checkpoint", None)
        if ingest is not None and ingest(logical_name, path, origin_branch_id=self.branch_id) != digest:
            raise _GateFailure("checkpoint_replay")
        self.checkpoints[path] = (logical_name, digest, self.branch_id)
        tick = _ticks(float(self.engine.brain.sim_ms))
        sequence = self.emit({
            "type": "qualification_checkpoint",
            "branch_id": self.branch_id,
            "parent_checkpoint_sha256": self.parent_checkpoint_sha256,
            "checkpoint_name": logical_name,
            "checkpoint_sha256": digest,
            "checkpoint_size": size,
            "sim_ms": float(self.engine.brain.sim_ms),
            "sim_tick": tick,
            **({"training_start_tick": training_start_tick,
                "association_t0_tick": association_t0_tick, "training_end_tick": tick}
               if training_start_tick is not None else {}),
        })
        if ingest is not None and sequence is not None:
            occurrence = {
                "checkpoint_name": logical_name, "checkpoint_sha256": digest,
                "origin_branch_id": self.branch_id,
                "checkpoint_sequence": sequence, "sim_tick": tick,
            }
            self.occurrences[path] = occurrence
            return dict(occurrence)
        return None

    def restore(self, path: Path) -> None:
        _, digest, parent_branch_id = self.checkpoints[path]
        if sha256(path.read_bytes()).hexdigest() != digest:
            raise _GateFailure("checkpoint_replay")
        self.engine.brain.restore(path)
        self.engine.brain.weights_frozen = False
        if self.engine.identity() != self.identity:
            raise _GateFailure("checkpoint_replay")
        self.parent_checkpoint_sha256 = digest
        self.emit({
            "type": "qualification_restore",
            "branch_id": self.branch_id,
            "parent_branch_id": parent_branch_id,
            "parent_checkpoint_sha256": digest,
            "checkpoint_sha256": digest,
            "sim_ms": float(self.engine.brain.sim_ms),
            "sim_tick": _ticks(float(self.engine.brain.sim_ms)),
            **({"parent_checkpoint_name": self.occurrences[path]["checkpoint_name"],
                "parent_checkpoint_sequence": self.occurrences[path]["checkpoint_sequence"]}
               if path in self.occurrences else {}),
        })

    def observe(self, frame, duration_ms, *, stimulation=None, learning=False,
                stimulus=None, local_start_ms=None, local_end_ms=None) -> dict:
        if self.grid_capture is not None:
            self.capture_stimulus = stimulus
        start_tick = _ticks(float(self.engine.brain.sim_ms))
        try:
            telemetry = self.engine.observe(
                frame,
                duration_ms,
                stimulation=stimulation,
                current_mv=CURRENT_MV,
                learning=learning,
                qualification_detail=True,
            )
        except ValueError as error:
            if "nonfinite" in str(error).lower():
                raise _GateFailure("nonfinite") from error
            raise
        self.simulated_ms += duration_ms
        try:
            expected_tick = start_tick + _ticks(duration_ms)
            if (_ticks(float(self.engine.brain.sim_ms)) != expected_tick
                    or _ticks(float(telemetry["sim_ms"])) != expected_tick):
                raise _GateFailure("clock_integrity")
        except (KeyError, TypeError, ValueError) as error:
            if isinstance(error, _GateFailure):
                raise
            raise _GateFailure("clock_integrity") from error
        if telemetry.get("engine_identity") != self.identity:
            raise _GateFailure("checkpoint_replay")
        try:
            json.dumps(telemetry, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise _GateFailure("nonfinite") from error
        sequence = self.emit({
            "type": "qualification_observation",
            "branch_id": self.branch_id,
            "parent_checkpoint_sha256": self.parent_checkpoint_sha256,
            "phase": self.phase,
            "sim_ms": expected_tick / 10,
            "start_ms": start_tick / 10,
            "end_ms": expected_tick / 10,
            "start_tick": start_tick,
            "end_tick": expected_tick,
            "duration_ticks": _ticks(duration_ms),
            "duration_ms": duration_ms,
            "local_start_ms": local_start_ms,
            "local_end_ms": local_end_ms,
            "stimulus": stimulus,
            "stimulation": stimulation,
            "current_mv": CURRENT_MV if stimulation else None,
            "learning": learning,
            "telemetry": telemetry,
        })
        if self.capture_sequences is not None and sequence is not None:
            self.capture_sequences.append(sequence)
        return telemetry

    def neutral(self, duration_ms: float, shape: tuple[int, int, int],
                *, detail: bool = True) -> float:
        if duration_ms <= 0:
            return 0.0
        self.engine.brain.weights_frozen = False
        if detail:
            black = np.zeros(shape, dtype=np.uint8)
            remaining = _ticks(duration_ms)
            total = remaining
            maximum_bound = 0.0
            while remaining:
                chunk = min(5000, remaining)
                telemetry = self.observe(
                    black, chunk / 10, learning=False,
                    local_start_ms=(total - remaining) / 10,
                    local_end_ms=(total - remaining + chunk) / 10,
                )
                maximum_bound = max(maximum_bound, _max_bound((telemetry,)))
                remaining -= chunk
            return maximum_bound

        start_tick = _ticks(float(self.engine.brain.sim_ms))
        try:
            advance_neutral(self, duration_ms, shape, branch_id=self.branch_id,
                            on_event=self.emit, learning=False,
                            parent_checkpoint_sha256=self.parent_checkpoint_sha256)
        except ValueError as error:
            if "nonfinite" in str(error).lower():
                raise _GateFailure("nonfinite") from error
            raise
        if self.engine.identity() != self.identity:
            raise _GateFailure("checkpoint_replay")
        if _ticks(float(self.engine.brain.sim_ms)) != start_tick + _ticks(duration_ms):
            raise _GateFailure("clock_integrity")
        return 0.0


def _observe_segments(
    run: _Run,
    segments: tuple[Segment, ...],
    frames: dict[str, np.ndarray],
    *,
    learning: bool,
) -> tuple[dict, ...]:
    black = np.zeros_like(frames["A"], dtype=np.uint8)
    records = []
    for segment in segments:
        frame = black if segment.stimulus is None else frames[segment.stimulus]
        telemetry = run.observe(
            frame, segment.end_ms - segment.start_ms,
            stimulation=segment.stimulation,
            learning=learning,
            stimulus=segment.stimulus,
            local_start_ms=segment.start_ms,
            local_end_ms=segment.end_ms,
        )
        records.append(telemetry)
    return tuple(records)


def _test_trial(run: _Run, configuration: GridConfiguration, frames: dict,
                identity: str) -> tuple[tuple[dict, ...], float]:
    run.phase = "reward_free_test"
    onset = float(run.engine.brain.sim_ms) + 100.0
    records = _observe_segments(run, _trial_segments(configuration, identity, paired=False),
                                frames, learning=False)
    return records, onset


def _training(run: _Run, configuration: GridConfiguration, paired: str,
              order: str, condition: str, frames: dict,
              *, controls: bool = False) -> tuple[tuple[dict, ...], float, float, float]:
    segments, second_end, total_end, t0 = _training_timeline(
        configuration, paired, order, condition, controls=controls,
    )
    acquisition_learning = condition in {"paired", "no_external_dan",
                                          "temporally_unpaired"}
    black = np.zeros_like(frames["A"], dtype=np.uint8)
    records = []
    for segment in segments:
        if segment.start_ms < t0 < segment.end_ms:
            raise _GateFailure("retention_timing")
        passive = segment.start_ms >= t0
        run.phase = "post_pair_passive" if passive else "pairing"
        run.engine.brain.weights_frozen = False
        records.append(run.observe(
            black if segment.stimulus is None else frames[segment.stimulus],
            segment.end_ms - segment.start_ms,
            stimulation=segment.stimulation,
            learning=(acquisition_learning and not passive
                      and (segment.stimulus is not None
                           or segment.stimulation is not None)),
            stimulus=segment.stimulus,
            local_start_ms=segment.start_ms,
            local_end_ms=segment.end_ms,
        ))
    return tuple(records), second_end, total_end, t0


def _max_bound(telemetries: tuple[dict, ...]) -> float:
    return max((float(bin_record["qualification_detail"]["bound_hit_fraction"])
                for record in telemetries for bin_record in record["bins"]), default=0.0)


def _candidate_state(run: _Run) -> tuple[tuple[int, ...], np.ndarray]:
    state = run.engine.brain.candidate_memory(run.engine.groups.mbon11)
    return tuple(int(value) for value in state.edge_indices), np.asarray(state.memory_w)


def _mbon07_state(run: _Run) -> tuple | None:
    try:
        state = run.engine.brain.candidate_memory(run.engine.groups.mbon07)
    except (AttributeError, ValueError):
        return None
    rule = run.engine.brain.rule_parameters
    return _mbon07_projection(tuple(int(value) for value in state.edge_indices),
                              state.memory_u, state.memory_w,
                              rule["minimum_fraction"], rule["maximum_fraction"])


def _mbon07_projection(edges: tuple[int, ...], memory_u: np.ndarray, memory_w: np.ndarray,
                       minimum_fraction: float, maximum_fraction: float) -> tuple | None:
    """Pure MBON07 snapshot projection using its own selected edges and rule bounds."""
    u = np.asarray(memory_u, dtype=np.float64)
    w = np.asarray(memory_w, dtype=np.float64)
    if not edges or u.shape != w.shape or len(edges) != len(w) \
            or not np.isfinite(u).all() or not np.isfinite(w).all():
        return None
    lower = float(minimum_fraction) - 1.0
    upper = float(maximum_fraction) - 1.0
    if not math.isfinite(lower) or not math.isfinite(upper):
        return None
    lower_mask = (u <= lower) | (w <= lower)
    upper_mask = (u >= upper) | (w >= upper)
    return (
        edges,
        tuple(float(value) for value in u),
        tuple(float(value) for value in w),
        int(np.count_nonzero(lower_mask)),
        int(np.count_nonzero(upper_mask)),
        float(np.count_nonzero(lower_mask | upper_mask) / len(edges)),
        lower,
        upper,
    )


def _state_difference(first: np.ndarray, second: np.ndarray) -> float:
    if first.size == 0 or first.shape != second.shape or not np.isfinite(first).all() \
            or not np.isfinite(second).all():
        raise ValueError("Missing or nonfinite candidate state")
    return float(np.abs(first - second).mean())


def _state_assessment(state: dict) -> tuple[float | None, float | None, tuple[str, ...]]:
    """Pure candidate projection arithmetic; preserve NumPy dtype until after mean."""
    state_shift = state_resolution = None
    errors = []
    if len(state) != 4:
        raise _GateFailure("missing_mbon11_observability")
    try:
        edge_order = state["paired"][0]
        if any(value[0] != edge_order or not np.isfinite(value[1]).all()
               for value in state.values()):
            raise ValueError("Candidate edge order changed")
        state_shift = _state_difference(state["paired"][1],
                                        state["matched_reference"][1])
        state_resolution = _state_difference(state["paired"][1],
                                             state["paired_replay"][1])
        if state_resolution > 0:
            errors.append("checkpoint_replay")
        if state_resolution > state_shift or state_shift <= 5 * state_resolution:
            errors.append("candidate_state_shift")
    except ValueError:
        errors.append("checkpoint_replay")
    return state_shift, state_resolution, tuple(errors)


def _base_assessment(state: dict, paths: dict, maximum_bound: float,
                      initial_reasons: tuple[str, ...]) -> tuple:
    """Pure base gates over four state projections and three compact pre pathways."""
    shift, resolution, state_reasons = _state_assessment(state)
    errors = [*initial_reasons, *state_reasons]
    if maximum_bound > 0.01:
        errors.append("candidate_saturation")
    if "A" in paths and "B" in paths \
            and paths["A"][1] != paths["B"][1]:
        errors.append("pathway_order")
    for value in paths.values():
        if not math.isfinite(value[0]) or value[0] <= 0:
            errors.append("modeled_drive")
        if state and value[3] != state["paired"][0]:
            errors.append("pathway_order")
    if paths and len({value[4] for value in paths.values()}) != 1:
        errors.append("pathway_order")
    return shift, resolution, tuple(dict.fromkeys(errors))


def _pathway(records: tuple[dict, ...], identity: str,
             window: ResponseWindow | None = None,
             cs_onset_ms: float | None = None) -> tuple:
    visual_all = [record for record in records
                  if any(float(record["pathway_detail"]["modeled_visual_drive"][name]["mean"] or 0)
                         != 0 for name in ("r1_r6", "r8"))]
    if not visual_all:
        raise ValueError("Missing modeled visual drive")
    visual = visual_all
    if window is not None:
        if cs_onset_ms is None:
            raise ValueError("Missing response-window onset")
        start = _ticks(cs_onset_ms + window.start_ms)
        end = _ticks(cs_onset_ms + window.end_ms)
        visual = []
        for record in visual_all:
            call_end = _ticks(float(record["sim_ms"]))
            call_start = call_end - _ticks(float(record["interval_ms"]))
            if call_start < end and call_end > start:
                if call_start < start or call_end > end:
                    raise ValueError("KC call crosses response-window boundary")
                visual.append(record)
    first = visual_all[0]
    detail = first["pathway_detail"]
    ids = tuple(int(value) for value in detail["candidate_kc_indices"])
    if not ids:
        raise ValueError("Missing MBON11-input KC observability")
    vector = tuple(sum(int(record["pathway_detail"]["candidate_kc_spike_counts"][i])
                       for record in visual) for i in range(len(ids)))
    edge_order = tuple(int(value) for value in detail["candidate_edge_indices"])
    dan_order = tuple(int(value) for value in first["qualification_detail"]["dan_indices"])
    edge_pre_ids = tuple(str(value) for value in detail["candidate_edge_pre_source_ids"])
    edge_post_ids = tuple(str(value) for value in detail["candidate_edge_post_source_ids"])
    kc_source_ids = tuple(str(value) for value in detail["candidate_kc_source_ids"])
    dan_source_ids = tuple(str(value) for value in
                           first["qualification_detail"]["dan_source_ids"])
    if not edge_order or not dan_order:
        raise ValueError("Missing candidate-edge or DAN order")
    if len(edge_pre_ids) != len(edge_order) or len(edge_post_ids) != len(edge_order) \
            or len(kc_source_ids) != len(ids) or len(dan_source_ids) != len(dan_order):
        raise ValueError("Candidate-edge, KC or DAN source order is incomplete")
    for record in records:
        if tuple(record["pathway_detail"]["candidate_edge_indices"]) != edge_order \
                or tuple(record["qualification_detail"]["dan_indices"]) != dan_order \
                or tuple(record["pathway_detail"]["candidate_edge_pre_source_ids"]) != edge_pre_ids \
                or tuple(record["pathway_detail"]["candidate_edge_post_source_ids"]) != edge_post_ids \
                or tuple(record["qualification_detail"]["dan_source_ids"]) != dan_source_ids:
            raise ValueError("Candidate-edge or DAN order changed")
        if (record["qualification_detail"]["rate_kc_semantics"]
                != "model_trace_state_hz"
                or record["qualification_detail"]["rate_dan_semantics"]
                != "model_trace_state_hz"):
            raise ValueError("Trace-state semantics changed")
        if tuple(record["pathway_detail"]["candidate_kc_indices"]) != ids:
            raise ValueError("MBON11-input KC order changed")
        if tuple(record["pathway_detail"]["candidate_kc_source_ids"]) != kc_source_ids:
            raise ValueError("MBON11-input KC source order changed")
        for bin_record in record["bins"]:
            detail_bin = bin_record["qualification_detail"]
            if len(detail_bin["rate_kc"]) != len(edge_order) \
                    or len(detail_bin["rate_dan"]) != len(dan_order):
                raise ValueError("Trace state is not edge/DAN aligned")
    drive = detail["modeled_visual_drive"]
    modeled_drive = sum(abs(float(drive[name]["mean"] or 0))
                        for name in ("r1_r6", "r8"))
    last_bin = visual_all[-1]["bins"][-1]["qualification_detail"]
    return (modeled_drive, ids, vector, edge_order, dan_order,
            tuple(float(value) for value in last_bin["rate_kc"]),
            tuple(float(value) for value in last_bin["rate_dan"]),
            edge_pre_ids, edge_post_ids, kc_source_ids, dan_source_ids)


def _replicate_base(run: _Run, root: Path, baseline: Path,
                    configuration: GridConfiguration, seed: int, paired: str,
                    order: str, frames: dict) -> dict:
    if len(run.engine.groups.mbon11) == 0:
        raise _GateFailure("missing_mbon11_observability")
    prefix = f"grid{GRID.index(configuration)}/seed{seed}/paired{paired}/order{order}"
    errors: list[str] = []
    pre = {}
    pre_paths = {}
    run.partial_base = {"pre": pre, "pre_paths": pre_paths}
    for identity in ("A", "B", "C"):
        run.enter_grid_role("pre", ("pre", identity), stimulus=identity)
        run.branch_id = f"{prefix}/pre/{identity}"
        run.restore(baseline)
        pre[identity] = _test_trial(run, configuration, frames, identity)
        try:
            pre_paths[identity] = _pathway(pre[identity][0], identity)
        except (KeyError, ValueError, TypeError, IndexError) as error:
            errors.append("missing_kc_observability" if "KC observability" in str(error)
                          else "modeled_drive" if "drive" in str(error)
                          else "pathway_order")
    run.enter_grid_role("pre_replay", ("pre_replay",), stimulus=paired)
    run.branch_id = f"{prefix}/pre_replay/{paired}"
    run.restore(baseline)
    replay, replay_onset = _test_trial(run, configuration, frames, paired)
    if pre[paired][1] != replay_onset:
        errors.append("checkpoint_replay")
    pre_replay = replay, replay_onset

    training = {}
    state = {}
    state07 = {}
    checkpoints = {}
    run.partial_base.update(training=training, state=state, state07=state07)
    training_t0_ms = training_end_ms = None
    for condition in ("paired", "matched_reference", "frozen_plasticity", "paired_replay"):
        run.enter_grid_role("training", ("training", condition), condition=condition)
        run.branch_id = f"{prefix}/{condition}/training"
        run.restore(baseline)
        baseline_ms = float(run.engine.brain.sim_ms)
        actual = "paired" if condition == "paired_replay" else condition
        records, _, _, t0 = _training(run, configuration, paired, order, actual, frames,
                                     controls=True)
        if condition == "paired":
            training_t0_ms = baseline_ms + t0
            training_end_ms = float(run.engine.brain.sim_ms)
            run.partial_base.update(training_t0_ms=training_t0_ms, training_end_ms=training_end_ms)
        training[condition] = records
        try:
            state[condition] = _candidate_state(run)
        except (ValueError, AttributeError):
            errors.append("missing_mbon11_observability")
        state07[condition] = _mbon07_state(run)
        path = root / f"{condition}.npz"
        occurrence = run.checkpoint(path, training_start_tick=_ticks(baseline_ms),
                                    association_t0_tick=_ticks(baseline_ms + t0))
        if run.grid_capture is not None:
            run.grid_capture["training_occurrences"][condition] = occurrence
        checkpoints[condition] = path
    run.enter_grid_role("base_validation")
    maximum_bound = max(
        *(_max_bound(records) for records in training.values()),
        *(_max_bound(trial[0]) for trial in pre.values()),
        _max_bound(pre_replay[0]),
    )
    state_shift, state_resolution, base_errors = _base_assessment(
        state, pre_paths, maximum_bound, tuple(errors),
    )
    return {
        "pre": pre, "pre_paths": pre_paths, "pre_replay": pre_replay,
        "training": training, "state_shift": state_shift,
        "state": state,
        "state07": state07,
        "training_t0_ms": training_t0_ms,
        "training_end_ms": training_end_ms,
        "prefix": prefix,
        "state_resolution": state_resolution, "maximum_bound": maximum_bound,
        "checkpoints": checkpoints, "errors": base_errors,
    }


def _retained_tests(run: _Run, root: Path, base: dict,
                    configuration: GridConfiguration, frames: dict,
                    paired: str, retention_ms: float) -> tuple[dict, float, float]:
    result = {}
    run.partial_retained = result
    retention = int(retention_ms)
    run.enter_grid_role("retention_timing", retention_ms=retention)
    maximum_bound = 0.0
    target_onset_tick = _ticks(base["training_t0_ms"]) + _ticks(retention_ms)
    remaining_ticks = target_onset_tick - 1000 - _ticks(base["training_end_ms"])
    if remaining_ticks < 0:
        raise _GateFailure("retention_timing")
    for condition in ("paired", "frozen_plasticity", "matched_reference"):
        run.enter_grid_role("retention", ("retention", str(retention), condition),
                            condition=condition, retention_ms=retention)
        run.branch_id = f"{base['prefix']}/{condition}/T{int(retention_ms)}/retention"
        run.restore(base["checkpoints"][condition])
        if _ticks(float(run.engine.brain.sim_ms)) != _ticks(base["training_end_ms"]):
            raise _GateFailure("checkpoint_replay")
        run.phase = "retention"
        maximum_bound = max(maximum_bound,
                            run.neutral(remaining_ticks / 10, frames["A"].shape))
        retained = root / f"retained-{condition}-{int(retention_ms)}.npz"
        occurrence = run.checkpoint(retained)
        if run.grid_capture is not None:
            run.grid_capture["retained_occurrences"].setdefault(str(retention), {})[condition] = occurrence
        result[condition] = {}
        identities = ("A", "B", "C") if condition == "paired" else (paired,)
        for identity in identities:
            run.enter_grid_role("post", ("post", str(retention), condition, identity),
                                condition=condition, stimulus=identity, retention_ms=retention)
            run.branch_id = (f"{base['prefix']}/{condition}/T{int(retention_ms)}"
                             f"/test/{identity}")
            run.restore(retained)
            result[condition][identity] = _test_trial(run, configuration, frames, identity)
            if _ticks(result[condition][identity][1]) != target_onset_tick:
                raise _GateFailure("retention_timing")
    run.enter_grid_role("measurement", retention_ms=retention)
    return result, maximum_bound, target_onset_tick / 10


def _one_spike_rate(population: int, window: ResponseWindow) -> float | None:
    return (1000.0 / (population * (window.end_ms - window.start_ms))
            if population else None)


def _measurement_from_compact(
    compact: ReplicateMeasurement, *, replay_pre_hz: float | None = None,
    frozen_post_hz: float | None = None, reference_post_hz: float | None = None,
    pathway_orders: tuple[tuple[int, ...], ...] = (), failure_reason: str | None = None,
) -> ReplicateMeasurement:
    """Pure gates from independently obtained scalars/vectors, never raw telemetry.

    ReplicateMeasurement is also the compact projection carrier. Derived response
    fields are overwritten here; callers supply actual rates, state projections,
    window KC counts, first drive, bounds, trace and orders. A failed prefix keeps
    its existing availability exactly and does not evaluate unavailable gates.
    """
    if failure_reason is not None:
        return replace(compact, reasons=(failure_reason,))
    reasons = list(compact.reasons)
    pre11, post11 = compact.pre_mbon11, compact.post_mbon11
    pre07, post07 = compact.pre_mbon07, compact.post_mbon07
    one_spike = compact.one_spike_rate_hz
    replay_resolution = washout = threshold = delta = None
    try:
        replay_resolution = abs(pre11[("A", "B", "C").index(compact.paired_identity)] - replay_pre_hz)
        if replay_resolution > 0:
            reasons.append("checkpoint_replay")
        washout = abs(frozen_post_hz - reference_post_hz)
        threshold = max(5 * replay_resolution, one_spike)
        plus = 0 if compact.paired_identity == "A" else 1
        minus = 1 - plus
        delta = (post11[plus] - post11[minus]) - (pre11[plus] - pre11[minus])
        if pre11[2] < one_spike or post11[2] < one_spike:
            reasons.append("c_below_floor")
        if abs(pre11[0] - pre11[1]) <= replay_resolution:
            reasons.append("mbon11_dynamic_range")
        if washout > threshold:
            reasons.append("washout")
        if not math.isfinite(delta) or any(
            not math.isfinite(value) for value in (*pre11, *post11, *pre07, *post07,
                                                   replay_resolution, washout, threshold)
        ):
            reasons.append("nonfinite")
    except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError):
        reasons.append("missing_mbon11_observability")
    try:
        if len(pathway_orders) != 4:
            raise ValueError("Missing window pathway projections")
        if len(set(pathway_orders)) != 1:
            reasons.append("pathway_order")
        vectors = (*compact.candidate_kc_vectors, *compact.post_candidate_kc_vectors)
        if any(sum(vector) == 0 for vector in vectors):
            reasons.append("missing_kc_activity")
        if (compact.candidate_kc_vectors[0] == compact.candidate_kc_vectors[1]
                or compact.post_candidate_kc_vectors[0] == compact.post_candidate_kc_vectors[1]):
            reasons.append("kc_vector_distinctness")
    except (KeyError, TypeError, ValueError, IndexError):
        reasons.append("pathway_order")
    if compact.maximum_bound_hit_fraction > 0.01:
        reasons.append("candidate_saturation")
    return replace(compact, delta_hz=delta, response_replay_resolution_hz=replay_resolution,
                   washout_hz=washout, washout_threshold_hz=threshold,
                   reasons=tuple(dict.fromkeys(reasons)))


def _measurement(run: _Run, base: dict, retained: dict,
                 retention_bound: float, test_onset_ms: float,
                 configuration: GridConfiguration, window: ResponseWindow,
                 seed: int, paired: str, order: str) -> ReplicateMeasurement:
    """Producer extraction adapter; the shared arithmetic accepts only projections."""
    one_spike = _one_spike_rate(len(run.engine.groups.mbon11), window)
    pre11 = [None, None, None]
    post11 = [None, None, None]
    pre07 = [None, None, None]
    post07 = [None, None, None]
    replay_pre = frozen_post = reference_post = None
    pathway_orders = ()
    try:
        for i, identity in enumerate(("A", "B", "C")):
            for target, trial in ((pre11, base["pre"][identity]),
                                  (post11, retained["paired"][identity])):
                target[i] = _aggregate_window(trial[0], trial[1], window,
                                              "mbon11", len(run.engine.groups.mbon11))
            for target, trial in ((pre07, base["pre"][identity]),
                                  (post07, retained["paired"][identity])):
                target[i] = _aggregate_window(trial[0], trial[1], window,
                                              "mbon07", len(run.engine.groups.mbon07))
        replay_pre = _aggregate_window(base["pre_replay"][0], base["pre_replay"][1], window,
                                       "mbon11", len(run.engine.groups.mbon11))
        frozen = retained["frozen_plasticity"][paired]
        unstimulated = retained["matched_reference"][paired]
        frozen_post = _aggregate_window(frozen[0], frozen[1], window, "mbon11",
                                        len(run.engine.groups.mbon11))
        reference_post = _aggregate_window(unstimulated[0], unstimulated[1], window,
                                           "mbon11", len(run.engine.groups.mbon11))
    except (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError):
        pass
    window_pre = ((), ())
    window_post = ((), ())
    try:
        pre_paths = [
            _pathway(base["pre"][identity][0], identity, window,
                     base["pre"][identity][1])
            for identity in ("A", "B")
        ]
        post_paths = [
            _pathway(retained["paired"][identity][0], identity, window,
                     retained["paired"][identity][1])
            for identity in ("A", "B")
        ]
        window_pre = (pre_paths[0][2], pre_paths[1][2])
        window_post = (post_paths[0][2], post_paths[1][2])
        pathway_orders = tuple(path[1] for path in (*pre_paths, *post_paths))
    except (KeyError, TypeError, ValueError, IndexError):
        pass
    maximum_bound = max(base["maximum_bound"], retention_bound,
                        *(_max_bound(trial[0]) for branch in retained.values()
                          for trial in branch.values()))
    paths = base["pre_paths"]
    first = paths.get("A")
    second = paths.get("B")
    drives = tuple(paths.get(name, (None,))[0] for name in ("A", "B", "C"))
    state = base["state"]
    trained07 = base["state07"].get("paired")
    matched07 = base["state07"].get("matched_reference")
    shift07 = (
        _state_difference(np.asarray(trained07[2]), np.asarray(matched07[2]))
        if trained07 and matched07 and trained07[0] == matched07[0] else None
    )
    final_trace = base["training"]["paired"][-1]["bins"][-1]["qualification_detail"]
    compact = ReplicateMeasurement(
        seed, paired, order, tuple(pre11), tuple(post11), tuple(pre07), tuple(post07),
        None, one_spike, None, base["state_resolution"],
        base["state_shift"], None, None, maximum_bound, drives,
        window_pre,
        first[1] if first else (), first[3] if first else (),
        first[4] if first else (),
        tuple(float(value) for value in final_trace["rate_kc"]),
        tuple(float(value) for value in final_trace["rate_dan"]),
        tuple(base["errors"]),
        training_memory_w=tuple(float(value) for value in state["paired"][1]),
        matched_memory_w=tuple(float(value) for value in state["matched_reference"][1]),
        replay_memory_w=tuple(float(value) for value in state["paired_replay"][1]),
        candidate_edge_pre_source_ids=first[7] if first else (),
        candidate_edge_post_source_ids=first[8] if first else (),
        candidate_kc_source_ids=first[9] if first else (),
        dan_source_ids=first[10] if first else (),
        post_candidate_kc_vectors=window_post,
        training_t0_ms=base["training_t0_ms"],
        training_end_ms=base["training_end_ms"],
        test_cs_onset_ms=test_onset_ms,
        mbon07_edge_indices=trained07[0] if trained07 else (),
        training_mbon07_memory_u=trained07[1] if trained07 else (),
        training_mbon07_memory_w=trained07[2] if trained07 else (),
        matched_mbon07_memory_u=matched07[1] if matched07 else (),
        matched_mbon07_memory_w=matched07[2] if matched07 else (),
        mbon07_state_shift=shift07,
        mbon07_lower_bound_hits=trained07[3] if trained07 else None,
        mbon07_upper_bound_hits=trained07[4] if trained07 else None,
        mbon07_bound_hit_fraction=trained07[5] if trained07 else None,
        mbon07_lower_bound=trained07[6] if trained07 else None,
        mbon07_upper_bound=trained07[7] if trained07 else None,
        matched_mbon07_lower_bound_hits=matched07[3] if matched07 else None,
        matched_mbon07_upper_bound_hits=matched07[4] if matched07 else None,
        matched_mbon07_bound_hit_fraction=matched07[5] if matched07 else None,
    )

    return _measurement_from_compact(compact, replay_pre_hz=replay_pre,
                                     frozen_post_hz=frozen_post, reference_post_hz=reference_post,
                                     pathway_orders=pathway_orders)


def _failed_measurement(run: _Run, window: ResponseWindow,
                        seed: int, paired: str, order: str,
                        reason: str, base: dict | None = None,
                        retained: dict | None = None) -> ReplicateMeasurement:
    one_spike = _one_spike_rate(len(run.engine.groups.mbon11), window)
    absent = (None, None, None)
    result = ReplicateMeasurement(
        seed, paired, order, absent, absent, absent, absent,
        None, one_spike, None, None, None, None, None, None,
        absent, ((), ()), (), (), (), (), (), (reason,),
        training_t0_ms=base.get("training_t0_ms") if base else None,
        training_end_ms=base.get("training_end_ms") if base else None,
    )
    # Complete prefix trials still contain real measurements when a later role failed.
    rates = {}
    for field, trials, population in (
        ("pre_mbon11", (base or {}).get("pre", {}), "mbon11"),
        ("pre_mbon07", (base or {}).get("pre", {}), "mbon07"),
        ("post_mbon11", (retained or {}).get("paired", {}), "mbon11"),
        ("post_mbon07", (retained or {}).get("paired", {}), "mbon07"),
    ):
        values = []
        for identity in ("A", "B", "C"):
            try:
                trial, onset = trials[identity]
                value = _aggregate_window(trial, onset, window, population,
                                          len(getattr(run.engine.groups, population)))
            except (KeyError, TypeError, ValueError, IndexError, AttributeError):
                value = None
            values.append(value)
        rates[field] = tuple(values)
    base = base or {}
    state = base.get("state", {})
    memories = {}
    for field, condition in (("training_memory_w", "paired"),
                             ("matched_memory_w", "matched_reference"),
                             ("replay_memory_w", "paired_replay")):
        if condition in state:
            memories[field] = tuple(float(value) for value in state[condition][1])
    paths = base.get("pre_paths", {})
    first = paths.get("A")
    known = {
        "state_shift": base.get("state_shift"),
        "state_replay_resolution": base.get("state_resolution"),
        "modeled_drive": tuple(paths[name][0] if name in paths else None for name in ("A", "B", "C")),
    }
    if first is not None:
        known.update(candidate_kc_ids=first[1], candidate_edge_indices=first[3], dan_indices=first[4],
                     candidate_edge_pre_source_ids=first[7], candidate_edge_post_source_ids=first[8],
                     candidate_kc_source_ids=first[9], dan_source_ids=first[10])
    training = base.get("training", {}).get("paired")
    if training:
        trace = training[-1]["bins"][-1]["qualification_detail"]
        known.update(rate_kc=tuple(float(value) for value in trace["rate_kc"]),
                     rate_dan=tuple(float(value) for value in trace["rate_dan"]))
    trained07 = base.get("state07", {}).get("paired")
    matched07 = base.get("state07", {}).get("matched_reference")
    if trained07:
        known.update(mbon07_edge_indices=trained07[0], training_mbon07_memory_u=trained07[1],
                     training_mbon07_memory_w=trained07[2], mbon07_lower_bound_hits=trained07[3],
                     mbon07_upper_bound_hits=trained07[4], mbon07_bound_hit_fraction=trained07[5],
                     mbon07_lower_bound=trained07[6], mbon07_upper_bound=trained07[7])
    if matched07:
        known.update(matched_mbon07_memory_u=matched07[1], matched_mbon07_memory_w=matched07[2],
                     matched_mbon07_lower_bound_hits=matched07[3], matched_mbon07_upper_bound_hits=matched07[4],
                     matched_mbon07_bound_hit_fraction=matched07[5])
    return _measurement_from_compact(replace(result, **rates, **memories, **known),
                                     failure_reason=reason)


def _selected_controls(run: _Run, baseline: Path, configuration: GridConfiguration,
                       window: ResponseWindow, retention_ms: float, frames_by_seed: dict,
                       seed: int, paired: str, order: str) -> tuple[ControlMeasurement, ...]:
    frames = frames_by_seed[seed]
    prefix = f"control/grid{GRID.index(configuration)}/seed{seed}/paired{paired}/order{order}"
    run.branch_id = f"{prefix}/baseline"
    run.restore(baseline)
    baseline_ms = float(run.engine.brain.sim_ms)
    latest_t0 = max(
        _training_timeline(configuration, paired, order, condition,
                           controls=True)[3]
        for condition in ("paired", "frozen_plasticity", "matched_reference",
                          "no_external_dan", "temporally_unpaired")
    )
    final_end_tick = (_ticks(baseline_ms + latest_t0) + _ticks(retention_ms)
                      + _ticks(configuration.cs_duration_ms + 200.0))
    pre = {}
    for identity in ("A", "B", "C"):
        run.branch_id = f"{prefix}/pre/{identity}"
        run.restore(baseline)
        trial, onset = _test_trial(run, configuration, frames, identity)
        pre[identity] = (
            _aggregate_window(trial, onset, window, "mbon11", len(run.engine.groups.mbon11)),
            _aggregate_window(trial, onset, window, "mbon07", len(run.engine.groups.mbon07)),
        )
    pre11 = tuple(pre[identity][0] for identity in ("A", "B", "C"))
    pre07 = tuple(pre[identity][1] for identity in ("A", "B", "C"))
    run.branch_id = f"{prefix}/matched_reference/state_probe"
    run.restore(baseline)
    _training(run, configuration, paired, order, "matched_reference", frames,
              controls=True)
    matched11 = _candidate_state(run)[1]
    matched07 = _mbon07_state(run)
    controls = []
    for condition in ("paired", "frozen_plasticity", "matched_reference",
                      "no_external_dan", "temporally_unpaired"):
        run.branch_id = f"{prefix}/{condition}/training"
        run.restore(baseline)
        _, _, _, condition_t0 = _training(
            run, configuration, paired, order, condition, frames, controls=True,
        )
        target_onset_tick = (_ticks(baseline_ms + condition_t0)
                             + _ticks(retention_ms))
        trained11 = _candidate_state(run)[1]
        trained07 = _mbon07_state(run)
        training_checkpoint = baseline.parent / f"control-{seed}-{paired}-{order}-{condition}.npz"
        run.checkpoint(training_checkpoint)
        run.branch_id = f"{prefix}/{condition}/T{int(retention_ms)}/retention"
        run.restore(training_checkpoint)
        remaining_ticks = target_onset_tick - 1000 - _ticks(float(run.engine.brain.sim_ms))
        if remaining_ticks < 0:
            raise _GateFailure("retention_timing")
        run.phase = "retention"
        run.neutral(remaining_ticks / 10, frames["A"].shape, detail=False)
        retained = baseline.parent / f"control-retained-{seed}-{paired}-{order}-{condition}.npz"
        run.checkpoint(retained)
        post = {}
        for identity in ("A", "B", "C"):
            run.branch_id = (f"{prefix}/{condition}/T{int(retention_ms)}"
                             f"/test/{identity}")
            run.restore(retained)
            trial, onset = _test_trial(run, configuration, frames, identity)
            if _ticks(onset) != target_onset_tick:
                raise _GateFailure("retention_timing")
            post[identity] = (
                _aggregate_window(trial, onset, window, "mbon11",
                                  len(run.engine.groups.mbon11)),
                _aggregate_window(trial, onset, window, "mbon07",
                                  len(run.engine.groups.mbon07)),
            )
            padding_ticks = final_end_tick - _ticks(float(run.engine.brain.sim_ms))
            if padding_ticks < 0:
                raise _GateFailure("retention_timing")
            run.phase = "post_measurement_padding"
            run.neutral(padding_ticks / 10, frames["A"].shape, detail=False)
        post11 = tuple(post[identity][0] for identity in ("A", "B", "C"))
        post07 = tuple(post[identity][1] for identity in ("A", "B", "C"))
        plus = 0 if paired == "A" else 1
        minus = 1 - plus
        delta = (post11[plus] - post11[minus]) - (pre11[plus] - pre11[minus])
        state_shift07 = (
            _state_difference(np.asarray(trained07[2]), np.asarray(matched07[2]))
            if trained07 and matched07 and trained07[0] == matched07[0] else None
        )
        separation = None
        if condition == "temporally_unpaired":
            segments, _, _, _ = _training_timeline(
                configuration, paired, order, condition, controls=True,
            )
            pulse_end = max(segment.end_ms for segment in segments
                            if segment.stimulation == "ppl101")
            boundaries = {boundary for segment in segments if segment.stimulus is not None
                          for boundary in (segment.start_ms, segment.end_ms)}
            separation = min(abs(pulse_end - boundary) for boundary in boundaries)
            if separation < UNPAIRED_SEPARATION_MS:
                raise _GateFailure("unpaired_separation")
        controls.append(ControlMeasurement(
            seed, paired, order, condition,
            final_end_tick / 10 - baseline_ms,
            2 * configuration.cs_duration_ms, separation,
            post11[plus], post07[plus],
            pre_mbon11=pre11, post_mbon11=post11,
            pre_mbon07=pre07, post_mbon07=post07,
            delta_hz=delta,
            training_t0_ms=baseline_ms + condition_t0,
            test_cs_onset_ms=target_onset_tick / 10,
            training_mbon11_memory_w=tuple(float(value) for value in trained11),
            matched_mbon11_memory_w=tuple(float(value) for value in matched11),
            mbon07_edge_indices=trained07[0] if trained07 else (),
            training_mbon07_memory_u=trained07[1] if trained07 else (),
            training_mbon07_memory_w=trained07[2] if trained07 else (),
            matched_mbon07_memory_u=matched07[1] if matched07 else (),
            matched_mbon07_memory_w=matched07[2] if matched07 else (),
            mbon07_state_shift=state_shift07,
            mbon07_lower_bound_hits=trained07[3] if trained07 else None,
            mbon07_upper_bound_hits=trained07[4] if trained07 else None,
            mbon07_bound_hit_fraction=trained07[5] if trained07 else None,
            mbon07_lower_bound=trained07[6] if trained07 else None,
            mbon07_upper_bound=trained07[7] if trained07 else None,
            matched_mbon07_lower_bound_hits=matched07[3] if matched07 else None,
            matched_mbon07_upper_bound_hits=matched07[4] if matched07 else None,
            matched_mbon07_bound_hit_fraction=matched07[5] if matched07 else None,
        ))
    if len({item.elapsed_ms for item in controls}) != 1 \
            or len({item.visual_exposure_ms for item in controls}) != 1:
        raise ValueError("Control conditions have unequal time or visual exposure")
    return tuple(controls)


def qualify(engine_factory, recorder, *, seeds, family) -> QualificationResult:
    """Evaluate the fixed exploratory grid and freeze one eligible model setting."""
    if family != "qualification" or type(seeds) is not tuple \
            or len(seeds) != 2 or any(type(seed) is not int for seed in seeds) \
            or seeds != QUALIFICATION_SEEDS:
        raise ValueError("Exploratory qualification requires family='qualification' and seeds=(11, 23)")
    started = time.perf_counter()
    engine = engine_factory()
    identity = engine.identity()
    json.dumps(identity, allow_nan=False)
    run = _Run(engine, recorder, identity)
    frames_by_seed = {
        seed: {name: AssayStimuli(seed=seed, family=family).frame(name)
               for name in ("A", "B", "C")}
        for seed in seeds
    }
    points = []
    with TemporaryDirectory(prefix="qualification-") as directory:
        root = Path(directory)
        baseline = root / "baseline.npz"
        run.checkpoint(baseline)
        for configuration in GRID:
            measurements = {(window, retention): [] for window in RESPONSE_WINDOWS
                            for retention in RETENTION_CANDIDATES_MS}
            for seed in seeds:
                frames = frames_by_seed[seed]
                for paired in ("A", "B"):
                    for order in ("AB", "BA"):
                        run.begin_grid(baseline, GRID.index(configuration), seed, paired, order)
                        evidence_id = (run.grid_capture["grid_evidence_id"]
                                       if run.grid_capture is not None else None)

                        def linked(measurement):
                            return replace(measurement, grid_evidence_id=evidence_id)

                        try:
                            base = _replicate_base(run, root, baseline, configuration,
                                                   seed, paired, order, frames)
                        except _GateFailure as failure:
                            run.grid_failure(failure.reason)
                            for window, retention in measurements:
                                measurements[(window, retention)].append(
                                    linked(_failed_measurement(run, window, seed, paired,
                                                               order, failure.reason, run.partial_base))
                                )
                            run.finish_grid(baseline)
                            continue
                        for retention in RETENTION_CANDIDATES_MS:
                            try:
                                retained, retention_bound, test_onset_ms = _retained_tests(
                                    run, root, base, configuration, frames, paired, retention,
                                )
                            except _GateFailure as failure:
                                run.grid_failure(failure.reason)
                                for window in RESPONSE_WINDOWS:
                                    measurements[(window, retention)].append(
                                        linked(_failed_measurement(run, window, seed, paired,
                                                                   order, failure.reason, base,
                                                                   run.partial_retained))
                                    )
                                continue
                            for index, window in enumerate(RESPONSE_WINDOWS):
                                try:
                                    measured = _measurement(run, base, retained, retention_bound,
                                                            test_onset_ms, configuration,
                                                            window, seed, paired, order)
                                except _GateFailure as failure:
                                    run.grid_failure(failure.reason)
                                    for pending in RESPONSE_WINDOWS[index:]:
                                        measurements[(pending, retention)].append(linked(
                                            _failed_measurement(run, pending, seed, paired, order,
                                                                failure.reason, base, retained),
                                        ))
                                    break
                                measurements[(window, retention)].append(linked(measured))
                        run.finish_grid(baseline)
            for window in RESPONSE_WINDOWS:
                for retention in RETENTION_CANDIDATES_MS:
                    replicates = tuple(measurements[(window, retention)])
                    summary = _summarize_point(configuration, window, retention,
                                               tuple(_replicate_summary(item) for item in replicates))
                    point = QualificationPoint(configuration, window, retention,
                                               replicates, summary.mean_delta_hz, summary.reasons)
                    points.append(point)
                    run.emit({
                        "type": "qualification_point", "branch_id": "qualification/summary",
                        "sim_ms": 0.0, "parent_branch_id": "qualification/baseline",
                        "parent_checkpoint_sha256": run.checkpoints[baseline][1],
                        "point": asdict(point),
                    })
        chosen = _select_points(points)
        controls = []
        if chosen is not None:
            configuration, window, retention_ms, _ = chosen
            for seed in seeds:
                for paired in ("A", "B"):
                    for order in ("AB", "BA"):
                        controls.extend(_selected_controls(
                            run, baseline, configuration, window, retention_ms,
                            frames_by_seed,
                            seed, paired, order,
                        ))
            for item in controls:
                run.emit({
                    "type": "qualification_control", "branch_id": "qualification/summary",
                    "sim_ms": 0.0, "parent_branch_id": "qualification/baseline",
                    "parent_checkpoint_sha256": run.checkpoints[baseline][1],
                    "control": asdict(item),
                })
        run.checkpoint(root / "final.npz", logical_name="brain-after.npz")
    metrics = benchmark(
        simulated_seconds=run.simulated_ms / 1000.0,
        wall_seconds=time.perf_counter() - started,
        event_count=run.event_count,
        checkpoint_bytes=run.checkpoint_bytes,
        peak_event_buffer_bytes=run.peak_event_buffer_bytes,
    )
    result = QualificationResult(
        "supported" if chosen is not None else "unsupported", family, seeds,
        tuple(points), chosen[0] if chosen else None,
        chosen[1] if chosen else None, chosen[2] if chosen else None,
        chosen[3] if chosen else None, tuple(controls),
        json.dumps(identity, sort_keys=True, allow_nan=False), tuple(metrics.items()),
    )
    run.emit({
        "type": "qualification_result",
        "branch_id": "qualification/summary",
        "sim_ms": 0.0,
        "parent_branch_id": "qualification/baseline",
        "parent_checkpoint_sha256": run.checkpoints[baseline][1],
        "status": result.status,
        "family": result.family,
        "seeds": list(result.seeds),
        "selected_configuration": (asdict(result.selected_configuration)
                                   if result.selected_configuration else None),
        "selected_window": (asdict(result.selected_window)
                            if result.selected_window else None),
        "selected_retention_ms": result.selected_retention_ms,
        "observed_effect_sign": result.observed_effect_sign,
        "benchmark": {key: value for key, value in result.benchmark.items()
                      if key != "wall_seconds"},
        "compute_seconds": result.benchmark["wall_seconds"],
    })
    return result
