"""Bounded exploratory PPL101/KC-to-MBON11 model qualification.

This module records model diagnostics and selects a declared assay setting. It
does not interpret the setting as biological learning or behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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


@dataclass(frozen=True)
class QualificationPoint:
    configuration: GridConfiguration
    response_window: ResponseWindow
    retention_ms: float
    replicates: tuple[ReplicateMeasurement, ...]
    mean_delta_hz: float | None
    reasons: tuple[str, ...]


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
    covered = 0
    for telemetry in telemetries:
        for bin_record in telemetry["bins"]:
            bin_end = _ticks(float(bin_record["end_ms"]))
            duration = _ticks(float(bin_record["duration_ms"]))
            bin_start = bin_end - duration
            if bin_start < end and bin_end > start:
                if bin_start < start or bin_end > end:
                    raise ValueError("Response bin crosses a half-open window boundary")
                spikes += int(bin_record["group_spikes"][population])
                covered += duration
    if covered != end - start:
        raise ValueError("Response window has missing bins")
    return spikes / (group_size * (covered / 10000.0))


def _select_points(
    points: tuple[QualificationPoint, ...] | list[QualificationPoint],
) -> tuple[GridConfiguration, ResponseWindow, float, int] | None:
    expected = {(seed, paired, order) for seed in QUALIFICATION_SEEDS
                for paired in ("A", "B") for order in ("AB", "BA")}
    best = None
    for configuration in GRID:
        for window in RESPONSE_WINDOWS:
            chosen = None
            for retention in RETENTION_CANDIDATES_MS:
                point = next((point for point in points
                              if point.configuration == configuration
                              and point.response_window == window
                              and point.retention_ms == retention), None)
                if point is None:
                    continue
                keys = {(item.seed, item.paired_identity, item.presentation_order)
                        for item in point.replicates}
                if keys != expected or len(point.replicates) != len(expected):
                    continue
                if any(item.washout_hz is None or item.washout_threshold_hz is None
                       or item.washout_hz > item.washout_threshold_hz
                       for item in point.replicates):
                    continue
                chosen = point
                break
            if chosen is None or chosen.reasons or chosen.mean_delta_hz in (None, 0):
                continue
            if best is None or abs(chosen.mean_delta_hz) > abs(best.mean_delta_hz):
                best = chosen
    if best is None:
        return None
    return (
        best.configuration,
        best.response_window,
        best.retention_ms,
        1 if best.mean_delta_hz > 0 else -1,
    )


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
        self.phase = "baseline"

    def emit(self, event: dict) -> None:
        encoded = json.dumps(event, allow_nan=False, separators=(",", ":"))
        self.event_count += 1
        self.peak_event_buffer_bytes = max(self.peak_event_buffer_bytes,
                                           len(encoded.encode("utf-8")))
        self.recorder.append(event)

    def checkpoint(self, path: Path) -> None:
        self.engine.brain.checkpoint(path)
        self.checkpoint_bytes += path.stat().st_size
        digest = sha256(path.read_bytes()).hexdigest()
        self.emit({
            "type": "qualification_checkpoint",
            "branch_id": self.branch_id,
            "parent_checkpoint_sha256": self.parent_checkpoint_sha256,
            "checkpoint_sha256": digest,
            "sim_ms": float(self.engine.brain.sim_ms),
        })

    def restore(self, path: Path) -> None:
        digest = sha256(path.read_bytes()).hexdigest()
        self.engine.brain.restore(path)
        self.engine.brain.weights_frozen = False
        if self.engine.identity() != self.identity:
            raise _GateFailure("checkpoint_replay")
        self.parent_checkpoint_sha256 = digest
        self.emit({
            "type": "qualification_restore",
            "branch_id": self.branch_id,
            "checkpoint_sha256": digest,
            "sim_ms": float(self.engine.brain.sim_ms),
        })

    def observe(self, frame, duration_ms, *, stimulation=None, learning=False,
                stimulus=None, local_start_ms=None, local_end_ms=None) -> dict:
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
        self.emit({
            "type": "qualification_observation",
            "branch_id": self.branch_id,
            "parent_checkpoint_sha256": self.parent_checkpoint_sha256,
            "phase": self.phase,
            "start_ms": start_tick / 10,
            "end_ms": expected_tick / 10,
            "duration_ms": duration_ms,
            "local_start_ms": local_start_ms,
            "local_end_ms": local_end_ms,
            "stimulus": stimulus,
            "stimulation": stimulation,
            "current_mv": CURRENT_MV if stimulation else None,
            "learning": learning,
            "telemetry": telemetry,
        })
        return telemetry

    def neutral(self, duration_ms: float, shape: tuple[int, int, int],
                *, detail: bool = True) -> float:
        if duration_ms <= 0:
            return 0.0
        self.engine.brain.weights_frozen = False
        if detail:
            black = np.zeros(shape, dtype=np.uint8)
            remaining = _ticks(duration_ms)
            maximum_bound = 0.0
            while remaining:
                chunk = min(5000, remaining)
                telemetry = self.observe(black, chunk / 10, learning=False)
                maximum_bound = max(maximum_bound, _max_bound((telemetry,)))
                remaining -= chunk
            return maximum_bound

        start_tick = _ticks(float(self.engine.brain.sim_ms))
        try:
            advance_neutral(self, duration_ms, shape, branch_id=self.branch_id,
                            on_event=lambda event: None, learning=False)
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
    edges = tuple(int(value) for value in state.edge_indices)
    u = np.asarray(state.memory_u, dtype=np.float64)
    w = np.asarray(state.memory_w, dtype=np.float64)
    if not edges or u.shape != w.shape or len(edges) != len(w) \
            or not np.isfinite(u).all() or not np.isfinite(w).all():
        return None
    rule = run.engine.brain.rule_parameters
    lower = float(rule["minimum_fraction"]) - 1.0
    upper = float(rule["maximum_fraction"]) - 1.0
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
    for identity in ("A", "B", "C"):
        run.branch_id = f"{prefix}/pre/{identity}"
        run.restore(baseline)
        pre[identity] = _test_trial(run, configuration, frames, identity)
        try:
            pre_paths[identity] = _pathway(pre[identity][0], identity)
        except (KeyError, ValueError, TypeError, IndexError) as error:
            errors.append("missing_kc_observability" if "KC observability" in str(error)
                          else "modeled_drive" if "drive" in str(error)
                          else "pathway_order")
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
    training_t0_ms = training_end_ms = None
    for condition in ("paired", "matched_reference", "frozen_plasticity", "paired_replay"):
        run.branch_id = f"{prefix}/{condition}/training"
        run.restore(baseline)
        baseline_ms = float(run.engine.brain.sim_ms)
        actual = "paired" if condition == "paired_replay" else condition
        records, _, _, t0 = _training(run, configuration, paired, order, actual, frames)
        if condition == "paired":
            training_t0_ms = baseline_ms + t0
            training_end_ms = float(run.engine.brain.sim_ms)
        training[condition] = records
        try:
            state[condition] = _candidate_state(run)
        except (ValueError, AttributeError):
            errors.append("missing_mbon11_observability")
        state07[condition] = _mbon07_state(run)
        path = root / f"{condition}.npz"
        run.checkpoint(path)
        checkpoints[condition] = path
    state_shift = state_resolution = None
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
    maximum_bound = max(
        *(_max_bound(records) for records in training.values()),
        *(_max_bound(trial[0]) for trial in pre.values()),
        _max_bound(pre_replay[0]),
    )
    if maximum_bound > 0.01:
        errors.append("candidate_saturation")
    if "A" in pre_paths and "B" in pre_paths \
            and pre_paths["A"][1] != pre_paths["B"][1]:
        errors.append("pathway_order")
    for value in pre_paths.values():
        if not math.isfinite(value[0]) or value[0] <= 0:
            errors.append("modeled_drive")
        if state and value[3] != state["paired"][0]:
            errors.append("pathway_order")
    if pre_paths and len({value[4] for value in pre_paths.values()}) != 1:
        errors.append("pathway_order")
    return {
        "pre": pre, "pre_paths": pre_paths, "pre_replay": pre_replay,
        "training": training, "state_shift": state_shift,
        "state": state,
        "state07": state07,
        "training_t0_ms": training_t0_ms,
        "training_end_ms": training_end_ms,
        "prefix": prefix,
        "state_resolution": state_resolution, "maximum_bound": maximum_bound,
        "checkpoints": checkpoints, "errors": tuple(dict.fromkeys(errors)),
    }


def _retained_tests(run: _Run, root: Path, base: dict,
                    configuration: GridConfiguration, frames: dict,
                    paired: str, retention_ms: float) -> tuple[dict, float, float]:
    result = {}
    maximum_bound = 0.0
    target_onset_tick = _ticks(base["training_t0_ms"]) + _ticks(retention_ms)
    remaining_ticks = target_onset_tick - 1000 - _ticks(base["training_end_ms"])
    if remaining_ticks < 0:
        raise _GateFailure("retention_timing")
    for condition in ("paired", "frozen_plasticity", "matched_reference"):
        run.branch_id = f"{base['prefix']}/{condition}/T{int(retention_ms)}/retention"
        run.restore(base["checkpoints"][condition])
        if _ticks(float(run.engine.brain.sim_ms)) != _ticks(base["training_end_ms"]):
            raise _GateFailure("checkpoint_replay")
        run.phase = "retention"
        maximum_bound = max(maximum_bound,
                            run.neutral(remaining_ticks / 10, frames["A"].shape))
        retained = root / f"retained-{condition}-{int(retention_ms)}.npz"
        run.checkpoint(retained)
        result[condition] = {}
        identities = ("A", "B", "C") if condition == "paired" else (paired,)
        for identity in identities:
            run.branch_id = (f"{base['prefix']}/{condition}/T{int(retention_ms)}"
                             f"/test/{identity}")
            run.restore(retained)
            result[condition][identity] = _test_trial(run, configuration, frames, identity)
            if _ticks(result[condition][identity][1]) != target_onset_tick:
                raise _GateFailure("retention_timing")
    return result, maximum_bound, target_onset_tick / 10


def _measurement(run: _Run, base: dict, retained: dict,
                 retention_bound: float, test_onset_ms: float,
                 configuration: GridConfiguration, window: ResponseWindow,
                 seed: int, paired: str, order: str) -> ReplicateMeasurement:
    reasons = list(base["errors"])
    one_spike = 1000.0 / (len(run.engine.groups.mbon11)
                          * (window.end_ms - window.start_ms))
    pre11 = [None, None, None]
    post11 = [None, None, None]
    pre07 = [None, None, None]
    post07 = [None, None, None]
    replay_resolution = washout = threshold = delta = None
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
        replay_resolution = abs(pre11[("A", "B", "C").index(paired)] -
                                _aggregate_window(base["pre_replay"][0],
                                                  base["pre_replay"][1], window,
                                                  "mbon11", len(run.engine.groups.mbon11)))
        if replay_resolution > 0:
            reasons.append("checkpoint_replay")
        frozen = retained["frozen_plasticity"][paired]
        unstimulated = retained["matched_reference"][paired]
        washout = abs(_aggregate_window(frozen[0], frozen[1], window, "mbon11",
                                        len(run.engine.groups.mbon11)) -
                      _aggregate_window(unstimulated[0], unstimulated[1], window,
                                        "mbon11", len(run.engine.groups.mbon11)))
        threshold = max(5 * replay_resolution, one_spike)
        plus = 0 if paired == "A" else 1
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
        if len({path[1] for path in (*pre_paths, *post_paths)}) != 1:
            reasons.append("pathway_order")
        if any(sum(vector) == 0 for vector in (*window_pre, *window_post)):
            reasons.append("missing_kc_activity")
        if window_pre[0] == window_pre[1] or window_post[0] == window_post[1]:
            reasons.append("kc_vector_distinctness")
    except (KeyError, TypeError, ValueError, IndexError):
        reasons.append("pathway_order")
    maximum_bound = max(base["maximum_bound"], retention_bound,
                        *(_max_bound(trial[0]) for branch in retained.values()
                          for trial in branch.values()))
    if maximum_bound > 0.01:
        reasons.append("candidate_saturation")
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
    return ReplicateMeasurement(
        seed, paired, order, tuple(pre11), tuple(post11), tuple(pre07), tuple(post07),
        delta, one_spike, replay_resolution, base["state_resolution"],
        base["state_shift"], washout, threshold, maximum_bound, drives,
        window_pre,
        first[1] if first else (), first[3] if first else (),
        first[4] if first else (),
        tuple(float(value) for value in final_trace["rate_kc"]),
        tuple(float(value) for value in final_trace["rate_dan"]),
        tuple(dict.fromkeys(reasons)),
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


def _failed_measurement(run: _Run, window: ResponseWindow,
                        seed: int, paired: str, order: str,
                        reason: str, base: dict | None = None) -> ReplicateMeasurement:
    group_size = len(run.engine.groups.mbon11)
    one_spike = (1000.0 / (group_size * (window.end_ms - window.start_ms))
                 if group_size else None)
    absent = (None, None, None)
    return ReplicateMeasurement(
        seed, paired, order, absent, absent, absent, absent,
        None, one_spike, None, None, None, None, None, None,
        absent, ((), ()), (), (), (), (), (), (reason,),
        training_t0_ms=base["training_t0_ms"] if base else None,
        training_end_ms=base["training_end_ms"] if base else None,
    )


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
    run.branch_id = f"{prefix}/matched_reference/training"
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
                        try:
                            base = _replicate_base(run, root, baseline, configuration,
                                                   seed, paired, order, frames)
                        except _GateFailure as failure:
                            for window, retention in measurements:
                                measurements[(window, retention)].append(
                                    _failed_measurement(run, window, seed, paired,
                                                        order, failure.reason)
                                )
                            continue
                        for retention in RETENTION_CANDIDATES_MS:
                            try:
                                retained, retention_bound, test_onset_ms = _retained_tests(
                                    run, root, base, configuration, frames, paired, retention,
                                )
                            except _GateFailure as failure:
                                for window in RESPONSE_WINDOWS:
                                    measurements[(window, retention)].append(
                                        _failed_measurement(run, window, seed, paired,
                                                            order, failure.reason, base)
                                    )
                                continue
                            for window in RESPONSE_WINDOWS:
                                measurements[(window, retention)].append(
                                    _measurement(run, base, retained, retention_bound,
                                                 test_onset_ms,
                                                 configuration,
                                                 window, seed, paired, order)
                                )
            for window in RESPONSE_WINDOWS:
                for retention in RETENTION_CANDIDATES_MS:
                    replicates = tuple(measurements[(window, retention)])
                    reasons = tuple(dict.fromkeys(reason for item in replicates
                                                   for reason in item.reasons))
                    mean = (sum(item.delta_hz for item in replicates) / len(replicates)
                            if not reasons and len(replicates) == 8 else None)
                    if mean == 0:
                        reasons += ("zero_mean_delta",)
                        mean = None
                    point = QualificationPoint(configuration, window, retention,
                                               replicates, mean, reasons)
                    points.append(point)
                    run.emit({"type": "qualification_point", "point": asdict(point)})
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
                run.emit({"type": "qualification_control", "control": asdict(item)})
    metrics = benchmark(
        simulated_seconds=run.simulated_ms / 1000.0,
        wall_seconds=time.perf_counter() - started,
        event_count=run.event_count,
        checkpoint_bytes=run.checkpoint_bytes,
        peak_event_buffer_bytes=run.peak_event_buffer_bytes,
    )
    return QualificationResult(
        "supported" if chosen is not None else "unsupported", family, seeds,
        tuple(points), chosen[0] if chosen else None,
        chosen[1] if chosen else None, chosen[2] if chosen else None,
        chosen[3] if chosen else None, tuple(controls),
        json.dumps(identity, sort_keys=True, allow_nan=False), tuple(metrics.items()),
    )
