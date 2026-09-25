"""Bounded exploratory qualification contracts."""

from dataclasses import asdict
from importlib.resources import files
import json
import math
from pathlib import Path
import re
from types import SimpleNamespace

import numpy as np
import pytest

from fly_connectome_sim.experiment.qualification import (
    GRID,
    RESPONSE_WINDOWS,
    RETENTION_CANDIDATES_MS,
    QualificationPoint,
    ReplicateMeasurement,
    _Run,
    _aggregate_window,
    _selected_controls,
    _select_points,
    _training,
    _training_timeline,
    _trial_segments,
    benchmark,
    qualify,
)
from fly_connectome_sim.experiment.stimuli import AssayStimuli


def test_declared_grid_order_and_windows_are_fixed():
    assert [(item.cs_duration_ms, item.dan_onset_ms, item.post_pair_gap_ms)
            for item in GRID] == [
                (100.0, -100.0, 500.0),
                (100.0, -100.0, 10000.0),
                (100.0, 0.0, 500.0),
                (100.0, 0.0, 10000.0),
                (100.0, 100.0, 500.0),
                (100.0, 100.0, 10000.0),
                (300.0, -100.0, 500.0),
                (300.0, -100.0, 10000.0),
                (300.0, 0.0, 500.0),
                (300.0, 0.0, 10000.0),
                (300.0, 100.0, 500.0),
                (300.0, 100.0, 10000.0),
            ]
    assert [(item.start_ms, item.end_ms) for item in RESPONSE_WINDOWS] == [
        (0.0, 100.0), (0.0, 300.0), (100.0, 300.0),
    ]
    assert RETENTION_CANDIDATES_MS == (10000.0, 20000.0, 30000.0, 60000.0)


@pytest.mark.parametrize("family,seeds", [
    ("confirmation", (101, 113)),
    ("qualification", (101, 113)),
    ("qualification", (23, 11)),
    ("qualification", (11, 11)),
    ("qualification", (True, 23)),
])
def test_family_seed_crossing_is_rejected_before_factory_call(family, seeds):
    calls = []

    def factory():
        calls.append(1)
        raise AssertionError("factory must not run")

    with pytest.raises(ValueError):
        qualify(factory, [], seeds=seeds, family=family)

    assert calls == []


def test_split_trial_covers_black_pre_and_post_with_exact_pulse():
    segments = _trial_segments(GRID[0], "A", paired=True)
    assert [(s.start_ms, s.end_ms, s.stimulus, s.stimulation)
            for s in segments] == [
                (-100.0, 0.0, None, "ppl101"),
                (0.0, 100.0, "A", None),
                (100.0, 300.0, None, None),
            ]
    assert [(s.start_ms, s.end_ms, s.stimulus) for s in
            _trial_segments(GRID[6], "A", paired=False)] == [
                (-100.0, 0.0, None),
                (0.0, 100.0, "A"),
                (100.0, 300.0, "A"),
                (300.0, 500.0, None),
            ]
    assert [(s.start_ms, s.end_ms, s.stimulus, s.stimulation)
            for s in _trial_segments(GRID[8], "B", paired=True)] == [
                (-100.0, 0.0, None, None),
                (0.0, 100.0, "B", "ppl101"),
                (100.0, 300.0, "B", None),
                (300.0, 500.0, None, None),
            ]


def test_window_rate_sums_raw_bin_spikes_at_half_open_boundaries():
    telemetry = [{"bins": [
        {"end_ms": 10.0, "duration_ms": 10.0, "group_spikes": {"mbon11": 1}},
        {"end_ms": 100.0, "duration_ms": 90.0, "group_spikes": {"mbon11": 2}},
        {"end_ms": 110.0, "duration_ms": 10.0, "group_spikes": {"mbon11": 7}},
        {"end_ms": 300.0, "duration_ms": 190.0, "group_spikes": {"mbon11": 1}},
    ]}]
    assert _aggregate_window(telemetry, 0.0, RESPONSE_WINDOWS[0], "mbon11", 2) == 15.0
    assert _aggregate_window(telemetry, 0.0, RESPONSE_WINDOWS[1], "mbon11", 2) == pytest.approx(11 / 0.6)
    assert _aggregate_window(telemetry, 0.0, RESPONSE_WINDOWS[2], "mbon11", 2) == 20.0


@pytest.mark.parametrize("configuration", GRID)
@pytest.mark.parametrize("order", ["AB", "BA"])
def test_control_timelines_have_fixed_unpaired_separation_and_equal_exposure(
    configuration, order,
):
    timelines = [
        _training_timeline(configuration, "A", order, condition, controls=True)
        for condition in ("paired", "frozen_plasticity", "no_external_dan",
                          "temporally_unpaired")
    ]
    assert len({item[2] for item in timelines}) == 1
    assert all(sum(segment.end_ms - segment.start_ms for segment in item[0]
                   if segment.stimulus is not None) == 2 * configuration.cs_duration_ms
               for item in timelines)
    pulse = [segment for segment in timelines[-1][0]
             if segment.stimulation == "ppl101"]
    assert sum(segment.end_ms - segment.start_ms for segment in pulse) == 100.0
    cs_boundaries = {segment.start_ms for segment in timelines[-1][0]
                     if segment.stimulus is not None}
    cs_boundaries.update(segment.end_ms for segment in timelines[-1][0]
                         if segment.stimulus is not None)
    assert pulse[0].start_ms == 0.0 and pulse[-1].end_ms == 100.0
    assert min(abs(pulse[-1].end_ms - boundary) for boundary in cs_boundaries) == 10000.0
    assert min(cs_boundaries) == 10100.0
    assert not any(segment.stimulus is not None for segment in timelines[-1][0]
                   if segment.end_ms <= 10100.0)


def _measurement(seed=11, paired_identity="A", order="AB", delta=2.0,
                 washout=0.0, threshold=1.0, reasons=()):
    return ReplicateMeasurement(
        seed=seed, paired_identity=paired_identity, presentation_order=order,
        pre_mbon11=(2.0, 1.0, 1.0), post_mbon11=(4.0, 1.0, 1.0),
        pre_mbon07=(1.0, 1.0, 1.0), post_mbon07=(1.0, 1.0, 1.0),
        delta_hz=delta, one_spike_rate_hz=5.0,
        response_replay_resolution_hz=0.0, state_replay_resolution=0.0,
        state_shift=0.2, washout_hz=washout, washout_threshold_hz=threshold,
        maximum_bound_hit_fraction=0.0, modeled_drive=(1.0, 1.0, 1.0),
        candidate_kc_vectors=((2, 0), (0, 2)), candidate_kc_ids=(4, 5),
        candidate_edge_indices=(7, 2), dan_indices=(2, 1),
        rate_kc=(1.0, 2.0), rate_dan=(3.0, 4.0), reasons=reasons,
    )


def test_selection_uses_all_eight_replicates_and_fixed_tie_order():
    keys = [(seed, identity, order) for seed in (11, 23)
            for identity in ("A", "B") for order in ("AB", "BA")]
    many = tuple(_measurement(*key, delta=1.0) for key in keys)
    larger = tuple(_measurement(*key, delta=2.0) for key in keys)
    points = (
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[0], 10000.0, many, 1.0, ()),
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[1], 10000.0, larger, 2.0, ()),
        QualificationPoint(GRID[1], RESPONSE_WINDOWS[0], 10000.0, larger, 2.0, ()),
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[1], 20000.0, larger, 2.0, ()),
    )
    assert _select_points(points) == (GRID[0], RESPONSE_WINDOWS[1], 10000.0, 1)
    incomplete = (QualificationPoint(GRID[0], RESPONSE_WINDOWS[0], 10000.0,
                                     many[:-1], 1.0, ()),)
    assert _select_points(incomplete) is None


def test_benchmark_reports_strict_json_safe_nonnegative_metrics():
    value = benchmark(event_count=3, simulated_seconds=2.0,
                      wall_seconds=0.1, checkpoint_bytes=10,
                      peak_event_buffer_bytes=20)
    assert set(value) == {"simulated_seconds", "wall_seconds", "event_count",
                          "checkpoint_bytes", "peak_event_buffer_bytes"}
    assert all(isinstance(item, (int, float)) and math.isfinite(item) and item >= 0
               for item in value.values())
    json.dumps(value, allow_nan=False)


class TinyBrain:
    def __init__(self):
        self.sim_ms = 0.0
        self.weights_frozen = False
        self.learned = {"A": 0.0, "B": 0.0}
        self.pending = False
        self.last_visual = None
        self.restores = 0
        self.baseline_restores = 0
        self.baseline_cycle = 0
        self.last_restore_name = None
        self.acute_until = {"A": 0.0, "B": 0.0}
        self.pending_acute = False
        self.mbon07_memory = 0.0
        self.visual_elapsed = 0.0
        self.rule_parameters = {"minimum_fraction": 0.1, "maximum_fraction": 2.0}

    def checkpoint(self, path):
        Path(path).write_text(json.dumps({
            "sim_ms": self.sim_ms, "learned": self.learned,
            "pending": self.pending, "last_visual": self.last_visual,
            "weights_frozen": self.weights_frozen,
            "acute_until": self.acute_until, "pending_acute": self.pending_acute,
            "mbon07_memory": self.mbon07_memory,
            "visual_elapsed": self.visual_elapsed,
        }), encoding="utf-8")

    def restore(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.sim_ms = data["sim_ms"]
        self.learned = data["learned"]
        self.pending = data["pending"]
        self.last_visual = data["last_visual"]
        self.weights_frozen = data["weights_frozen"]
        self.acute_until = data["acute_until"]
        self.pending_acute = data["pending_acute"]
        self.mbon07_memory = data["mbon07_memory"]
        self.visual_elapsed = data["visual_elapsed"]
        self.restores += 1
        self.last_restore_name = Path(path).name
        if Path(path).name == "baseline.npz":
            self.baseline_restores += 1
            self.baseline_cycle = (self.baseline_restores - 1) % 8 + 1

    def candidate_memory(self, targets):
        if getattr(self, "fault", None) == "missing_state":
            raise ValueError("No candidate edges")
        if tuple(targets) == (7,):
            return SimpleNamespace(
                edge_indices=np.array([12]),
                memory_u=np.array([self.mbon07_memory]),
                memory_w=np.array([self.mbon07_memory]),
            )
        assert tuple(targets) == (8, 9)
        return SimpleNamespace(edge_indices=np.array([7, 2]),
                               memory_u=np.array([self.learned["A"],
                                                  self.learned["B"]]),
                               memory_w=np.array([self.learned["A"],
                                                  self.learned["B"]]))


class TinyEngine:
    """Small deterministic boundary with the actual telemetry/checkpoint shape."""

    def __init__(self, *, fault=None):
        self.brain = TinyBrain()
        self.brain.fault = fault
        self.groups = SimpleNamespace(mbon11=np.array([8, 9]),
                                      mbon07=np.array([7]))
        if fault == "empty_mbon_group":
            self.groups.mbon11 = np.array([], dtype=np.int64)
        self.fault = fault
        self.calls = 0
        self.stimulated = []

    def identity(self):
        return {"version": "tiny/v1", "sha256": "tiny", "neural_groups": {
            "mbon11": [8, 9], "mbon07": [7],
        }}

    def observe(self, frame, duration_ms, *, stimulation=None, current_mv=20.0,
                learning=False, qualification_detail=False):
        assert frame.dtype == np.uint8 and frame.ndim == 3 and frame.shape[2] == 3
        assert 0.1 <= duration_ms <= 500.0 and duration_ms * 10 == round(duration_ms * 10)
        assert current_mv == 20.0
        assert qualification_detail or (stimulation is None and not learning and not frame.any())
        assert not self.brain.weights_frozen
        self.calls += 1
        marker = np.argwhere(frame[:, :, 0] == 255)
        identity = None if not len(marker) else ("A", "B", "C")[int(marker[0, 0])]
        visual_elapsed = self.brain.visual_elapsed if identity == self.brain.last_visual else 0.0
        if stimulation is not None:
            assert stimulation == "ppl101" and duration_ms == 100.0
            self.stimulated.append((identity, learning, frame.any()))
            if learning and self.fault != "no_learning":
                if identity in ("A", "B"):
                    self.brain.learned[identity] += (
                        0.3 if self.fault == "replay_state" and self.brain.baseline_cycle == 8
                        else 0.2
                    )
                elif self.brain.last_visual in ("A", "B"):
                    self.brain.learned[self.brain.last_visual] += (
                        0.3 if self.fault == "replay_state" and self.brain.baseline_cycle == 8
                        else 0.2
                    )
                else:
                    self.brain.pending = True
            elif self.fault == "washout_late":
                if identity in ("A", "B"):
                    self.brain.acute_until[identity] = self.brain.sim_ms + 15000.0
                elif self.brain.last_visual in ("A", "B"):
                    self.brain.acute_until[self.brain.last_visual] = self.brain.sim_ms + 15000.0
                else:
                    self.brain.pending_acute = True
            if learning:
                self.brain.mbon07_memory += 0.1
        if self.fault == "endogenous" and learning and stimulation is None \
                and identity in ("A", "B"):
            self.brain.learned[identity] += 0.05
            self.brain.mbon07_memory += 0.05
        if identity in ("A", "B") and self.brain.pending:
            self.brain.learned[identity] += (
                0.3 if self.fault == "replay_state" and self.brain.baseline_cycle == 8
                else 0.2
            )
            self.brain.pending = False
        if identity in ("A", "B") and self.brain.pending_acute:
            self.brain.acute_until[identity] = self.brain.sim_ms + 15000.0
            self.brain.pending_acute = False
        self.brain.last_visual = identity
        self.brain.visual_elapsed = visual_elapsed + duration_ms if identity else 0.0
        start = self.brain.sim_ms
        self.brain.sim_ms = round(start + duration_ms, 3)
        if self.fault == "clock_drift":
            self.brain.sim_ms += 0.1
        count = max(1, int(round(duration_ms / 10))) if identity else 1
        bin_ms = duration_ms / count
        bins = []
        kc_total = [0, 0]
        for index in range(count):
            base = {"A": 4, "B": 2, "C": 1, None: 0}[identity]
            if self.fault == "no_c" and identity == "C":
                base = 0
            if self.fault == "no_range" and identity in ("A", "B"):
                base = 2
            if identity in ("A", "B"):
                base += int(self.brain.learned[identity] * 10)
                if self.fault == "washout_late" and start < self.brain.acute_until[identity]:
                    base += 2
            if self.fault == "replay_response" and identity in ("A", "B") \
                    and self.brain.baseline_cycle == 4:
                base += 1
            kc = {"A": (2, 0), "B": (0, 2), "C": (1, 1), None: (0, 0)}[identity]
            if self.fault == "same_kc" and identity == "B":
                kc = (2, 0)
            if self.fault == "silent_a_kc" and identity == "A":
                kc = (0, 0)
            if self.fault == "kc_early_only" and visual_elapsed >= 100.0:
                kc = (0, 0)
            kc_total[0] += kc[0]
            kc_total[1] += kc[1]
            counts = {"mbon11": base, "mbon07": 1 if identity else 0}
            if self.fault == "no_mbon":
                del counts["mbon11"]
            bins.append({
                "end_ms": round(start + (index + 1) * bin_ms, 3),
                "duration_ms": bin_ms,
                "group_spikes": counts,
                "qualification_detail": {
                    "rate_kc": [1.0, 2.0], "rate_dan": [3.0, 4.0],
                    "bound_hit_fraction": 1.0 if (
                        self.fault == "saturated" and index == 0
                        or self.fault == "retention_saturated" and qualification_detail
                        and duration_ms == 500.0 and self.brain.last_restore_name == "paired.npz"
                        or self.fault == "baseline_saturated" and qualification_detail
                        and self.brain.last_restore_name == "baseline.npz" and index == 0
                    ) else 0.0,
                },
            })
        drive = 0.0 if self.fault == "zero_drive" else (1.0 if identity else 0.0)
        if self.fault == "nonfinite" and identity == "A":
            drive = math.nan
        r1_drive = 0.0 if self.fault == "r8_only" else drive
        return {
            "sim_ms": self.brain.sim_ms, "interval_ms": duration_ms,
            "input_sha256": "a" * 64,
            "engine_identity": self.identity(), "bins": bins,
            "pathway_detail": {
                "modeled_visual_drive": {
                    "r1_r6": {"mean": r1_drive}, "r8": {"mean": drive},
                },
                "candidate_edge_indices": [7, 2],
                "candidate_edge_pre_source_ids": ["105", "104"],
                "candidate_edge_post_source_ids": ["108", "109"],
                "candidate_kc_indices": [] if self.fault == "no_kc" else [4, 5],
                "candidate_kc_source_ids": [] if self.fault == "no_kc" else ["104", "105"],
                "candidate_kc_spike_counts": [] if self.fault == "no_kc" else kc_total,
            },
            "qualification_detail": {
                "dan_indices": [1, 2] if self.fault == "dan_order" and identity == "B"
                               else [2, 1],
                "dan_source_ids": ["102", "101"],
                "rate_kc_semantics": ("wrong" if self.fault == "trace_semantics"
                                      else "model_trace_state_hz"),
                "rate_dan_semantics": "model_trace_state_hz",
                "maximum_bound_hit_fraction": max(
                    item["qualification_detail"]["bound_hit_fraction"] for item in bins
                ),
            },
        }


class PointRecorder:
    def __init__(self, *, capture_observations=False):
        self.points = []
        self.count = 0
        self.kinds = {}
        self.samples = {}
        self.observations_no_dan = []
        self.observations = [] if capture_observations else None

    def append(self, event):
        json.dumps(event, allow_nan=False)
        self.count += 1
        kind = event.get("type")
        self.kinds[kind] = self.kinds.get(kind, 0) + 1
        self.samples.setdefault(kind, event)
        if kind == "qualification_observation" and self.observations is not None:
            self.observations.append(event)
        if kind == "qualification_observation" and "/no_external_dan/" in event["branch_id"] \
                and event["learning"] is True and event["stimulation"] is None \
                and len(self.observations_no_dan) < 20:
            self.observations_no_dan.append(event)
        if event.get("type") == "qualification_point":
            self.points.append(event)


def test_qualification_runs_fixed_grid_replicates_and_freezes_selection():
    engine = TinyEngine()
    recorder = PointRecorder()

    result = qualify(lambda: engine, recorder, seeds=(11, 23), family="qualification")

    assert result.family == "qualification" and result.seeds == (11, 23)
    assert result.status == "supported"
    assert len(result.points) == 12 * 3 * 4
    assert result.selected_configuration == GRID[0]
    assert result.selected_window == RESPONSE_WINDOWS[0]
    assert result.selected_retention_ms == 10000.0
    assert result.observed_effect_sign == 1
    assert len(result.points[0].replicates) == 8
    assert {(item.seed, item.paired_identity, item.presentation_order)
            for item in result.points[0].replicates} == {
                (seed, paired, order) for seed in (11, 23)
                for paired in ("A", "B") for order in ("AB", "BA")
            }
    assert result.points[0].mean_delta_hz == pytest.approx(100.0)
    assert all(item.state_shift == pytest.approx(0.1)
               and item.state_replay_resolution == 0.0
               and item.response_replay_resolution_hz == 0.0
               and item.washout_hz == 0.0
               for item in result.points[0].replicates)
    first = result.points[0].replicates[0]
    assert first.training_memory_w == pytest.approx((0.2, 0.0))
    assert first.matched_memory_w == pytest.approx((0.0, 0.0))
    assert first.replay_memory_w == pytest.approx((0.2, 0.0))
    assert first.candidate_edge_pre_source_ids == ("105", "104")
    assert first.candidate_edge_post_source_ids == ("108", "109")
    assert first.candidate_kc_source_ids == ("104", "105")
    assert first.dan_source_ids == ("102", "101")
    assert first.training_mbon07_memory_w == pytest.approx((0.1,))
    assert first.matched_mbon07_memory_w == pytest.approx((0.0,))
    assert first.mbon07_state_shift == pytest.approx(0.1)
    assert first.mbon07_bound_hit_fraction == 0.0
    assert (first.mbon07_lower_bound, first.mbon07_upper_bound) == (-0.9, 1.0)
    assert first.matched_mbon07_lower_bound_hits == 0
    assert first.matched_mbon07_upper_bound_hits == 0
    assert first.matched_mbon07_bound_hit_fraction == 0.0
    assert first.training_t0_ms == 900.0
    assert first.test_cs_onset_ms == 10900.0
    assert all(
        item.test_cs_onset_ms - item.training_t0_ms == point.retention_ms
        for point in result.points for item in point.replicates
        if item.test_cs_onset_ms is not None
    )
    assert len(recorder.points) == len(result.points)
    assert len(result.controls) == 2 * 2 * 2 * 5
    assert all(item.elapsed_ms >= 20000.0 for item in result.controls)
    assert {item.unpaired_nearest_cs_boundary_ms for item in result.controls
            if item.condition == "temporally_unpaired"} == {10000.0}
    control = next(item for item in result.controls
                   if (item.seed, item.paired_identity, item.presentation_order,
                       item.condition) == (11, "A", "AB", "paired"))
    assert control.pre_mbon11 == pytest.approx((200.0, 100.0, 50.0))
    assert control.post_mbon11 == pytest.approx((300.0, 100.0, 50.0))
    assert control.delta_hz == pytest.approx(100.0)
    assert control.pre_mbon07 == pytest.approx((100.0, 100.0, 100.0))
    assert control.post_mbon07 == pytest.approx((100.0, 100.0, 100.0))
    assert control.training_mbon07_memory_w == pytest.approx((0.1,))
    assert control.matched_mbon07_memory_w == pytest.approx((0.0,))
    assert (control.mbon07_lower_bound, control.mbon07_upper_bound) == (-0.9, 1.0)
    assert control.matched_mbon07_lower_bound_hits == 0
    assert control.matched_mbon07_upper_bound_hits == 0
    assert control.matched_mbon07_bound_hit_fraction == 0.0
    assert control.training_t0_ms == 10900.0
    assert control.test_cs_onset_ms == 20900.0
    assert control.elapsed_ms == 21200.0
    assert control.test_cs_onset_ms - control.training_t0_ms == 10000.0
    assert all(item.test_cs_onset_ms - item.training_t0_ms
               == result.selected_retention_ms for item in result.controls)
    assert all(
        len({item.elapsed_ms for item in result.controls
             if (item.seed, item.paired_identity, item.presentation_order)
             == (seed, paired, order)}) == 1
        for seed in (11, 23) for paired in ("A", "B")
        for order in ("AB", "BA")
    )
    assert all(
        item.delta_hz == pytest.approx(
            (item.post_mbon11[0 if item.paired_identity == "A" else 1]
             - item.post_mbon11[1 if item.paired_identity == "A" else 0])
            - (item.pre_mbon11[0 if item.paired_identity == "A" else 1]
               - item.pre_mbon11[1 if item.paired_identity == "A" else 0])
        )
        and len(item.post_mbon11) == len(item.post_mbon07) == 3
        for item in result.controls
    )
    impossible = next(point for point in result.points
                      if point.configuration == GRID[1]
                      and point.response_window == RESPONSE_WINDOWS[0]
                      and point.retention_ms == 10000.0)
    assert "retention_timing" in impossible.reasons
    later = next(point for point in result.points
                 if point.configuration == GRID[1]
                 and point.response_window == RESPONSE_WINDOWS[0]
                 and point.retention_ms == 20000.0)
    paired_last = next(item for item in later.replicates
                       if (item.seed, item.paired_identity, item.presentation_order)
                       == (11, "A", "BA"))
    assert paired_last.training_t0_ms == 600.0
    assert paired_last.test_cs_onset_ms == 20600.0
    observation = recorder.samples["qualification_observation"]
    assert observation["branch_id"] and observation["end_ms"] > observation["start_ms"]
    assert observation["telemetry"]["bins"][0]["group_spikes"]["mbon11"] >= 0
    assert observation["telemetry"]["input_sha256"]
    assert observation["telemetry"]["qualification_detail"]["dan_indices"] == [2, 1]
    assert len(recorder.samples["qualification_checkpoint"]["checkpoint_sha256"]) == 64
    assert len(recorder.samples["qualification_restore"]["checkpoint_sha256"]) == 64
    assert engine.calls > 0 and engine.brain.restores > 0
    assert all(item[0] in (None, "A", "B") for item in engine.stimulated)
    first_identity = result.engine_identity
    first_identity["neural_groups"]["mbon11"].clear()
    assert result.engine_identity["neural_groups"]["mbon11"] == [8, 9]
    first_benchmark = result.benchmark
    first_benchmark["event_count"] = -1
    assert result.benchmark["event_count"] > 0
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("fault,reason", [
    ("no_c", "c_below_floor"),
    ("no_range", "mbon11_dynamic_range"),
    ("no_kc", "missing_kc_observability"),
    ("zero_drive", "modeled_drive"),
    ("saturated", "candidate_saturation"),
    ("same_kc", "kc_vector_distinctness"),
    ("nonfinite", "nonfinite"),
    ("no_mbon", "missing_mbon11_observability"),
    ("replay_response", "checkpoint_replay"),
    ("replay_state", "checkpoint_replay"),
    ("no_learning", "candidate_state_shift"),
    ("dan_order", "pathway_order"),
    ("retention_saturated", "candidate_saturation"),
    ("baseline_saturated", "candidate_saturation"),
    ("trace_semantics", "pathway_order"),
    ("missing_state", "missing_mbon11_observability"),
    ("empty_mbon_group", "missing_mbon11_observability"),
    ("clock_drift", "clock_integrity"),
])
def test_failed_primary_gate_returns_unsupported_without_selection(fault, reason):
    result = qualify(lambda: TinyEngine(fault=fault), PointRecorder(),
                     seeds=(11, 23), family="qualification")
    assert result.status == "unsupported"
    assert (result.selected_configuration, result.selected_window,
            result.selected_retention_ms, result.observed_effect_sign) == (
                None, None, None, None,
            )
    assert any(reason in point.reasons for point in result.points)


def test_washout_selects_first_passing_retention_in_real_execution():
    result = qualify(lambda: TinyEngine(fault="washout_late"), PointRecorder(),
                     seeds=(11, 23), family="qualification")
    assert result.status == "supported"
    assert result.selected_retention_ms == 20000.0
    assert "washout" in result.points[0].reasons
    assert all(item.washout_hz > item.washout_threshold_hz
               for item in result.points[0].replicates)


def test_r8_only_modeled_drive_is_still_observable():
    result = qualify(lambda: TinyEngine(fault="r8_only"), PointRecorder(),
                     seeds=(11, 23), family="qualification")
    assert result.status == "supported"
    assert result.points[0].replicates[0].modeled_drive == (1.0, 1.0, 1.0)


def test_no_external_dan_control_keeps_learning_enabled_for_endogenous_state():
    recorder = PointRecorder()
    result = qualify(lambda: TinyEngine(fault="endogenous"), recorder,
                     seeds=(11, 23), family="qualification")
    no_dan = next(item for item in result.controls
                  if item.seed == 11 and item.paired_identity == "A"
                  and item.presentation_order == "AB"
                  and item.condition == "no_external_dan")
    matched = next(item for item in result.controls
                   if item.seed == 11 and item.paired_identity == "A"
                   and item.presentation_order == "AB"
                   and item.condition == "matched_reference")
    assert no_dan.training_mbon11_memory_w != matched.training_mbon11_memory_w
    assert no_dan.training_mbon07_memory_w != matched.training_mbon07_memory_w
    assert recorder.kinds["qualification_observation"] > recorder.kinds["qualification_point"]
    assert any(event["learning"] is True and event["stimulation"] is None
               for event in recorder.observations_no_dan)


def test_silent_a_kc_is_rejected_even_when_b_vector_is_distinct():
    result = qualify(lambda: TinyEngine(fault="silent_a_kc"), PointRecorder(),
                     seeds=(11, 23), family="qualification")
    assert result.status == "unsupported"
    assert "missing_kc_activity" in result.points[0].reasons


def test_late_kc_activity_does_not_count_in_early_response_window():
    result = qualify(lambda: TinyEngine(fault="kc_early_only"), PointRecorder(),
                     seeds=(11, 23), family="qualification")
    point = next(item for item in result.points
                 if item.configuration == GRID[6]
                 and item.response_window == RESPONSE_WINDOWS[2]
                 and item.retention_ms == 10000.0)
    assert "missing_kc_activity" in point.reasons
    assert point.replicates[0].candidate_kc_vectors[0] == (0, 0)


def test_first_washout_passing_retention_is_chosen_before_later_larger_effect():
    keys = [(seed, paired, order) for seed in (11, 23)
            for paired in ("A", "B") for order in ("AB", "BA")]
    blocked = tuple(_measurement(*key, delta=20.0, washout=6.0,
                                 threshold=5.0, reasons=("washout",)) for key in keys)
    passes = tuple(_measurement(*key, delta=1.0) for key in keys)
    later = tuple(_measurement(*key, delta=50.0) for key in keys)
    points = (
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[0], 10000.0, blocked, None,
                           ("washout",)),
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[0], 20000.0, passes, 1.0, ()),
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[0], 30000.0, later, 50.0, ()),
    )
    assert _select_points(points) == (GRID[0], RESPONSE_WINDOWS[0], 20000.0, 1)


def test_first_washout_passing_t_with_zero_effect_cannot_be_skipped():
    keys = [(seed, paired, order) for seed in (11, 23)
            for paired in ("A", "B") for order in ("AB", "BA")]
    zero = tuple(_measurement(*key, delta=0.0) for key in keys)
    positive = tuple(_measurement(*key, delta=5.0) for key in keys)
    points = (
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[0], 10000.0, zero, None,
                           ("zero_mean_delta",)),
        QualificationPoint(GRID[0], RESPONSE_WINDOWS[0], 20000.0, positive, 5.0, ()),
    )
    assert _select_points(points) is None


@pytest.mark.parametrize("configuration,order,want_final_cs,want_t0,want_end", [
    (GRID[0], "AB", 900.0, 900.0, 1100.0),
    (GRID[0], "BA", 600.0, 600.0, 1100.0),
    (GRID[1], "AB", 10400.0, 10400.0, 10600.0),
    (GRID[1], "BA", 600.0, 600.0, 10600.0),
    (GRID[5], "BA", 600.0, 700.0, 10600.0),
])
def test_training_t0_excludes_reserved_tail_and_overlaps_post_pair_gap(
    configuration, order, want_final_cs, want_t0, want_end,
):
    timeline = _training_timeline(configuration, "A", order, "paired")
    assert timeline[1:] == (want_final_cs, want_end, want_t0)
    assert timeline[0][0].start_ms == 0.0
    assert timeline[0][-1].end_ms == want_end


@pytest.mark.parametrize("configuration", GRID)
@pytest.mark.parametrize("order", ["AB", "BA"])
def test_every_selected_control_tests_at_its_actual_t0_plus_t(
    configuration, order, tmp_path,
):
    engine = TinyEngine()
    recorder = PointRecorder()
    run = _Run(engine, recorder, engine.identity())
    baseline = tmp_path / "baseline.npz"
    run.checkpoint(baseline)
    frames = {name: AssayStimuli(seed=11, family="qualification").frame(name)
              for name in ("A", "B", "C")}

    controls = _selected_controls(run, baseline, configuration, RESPONSE_WINDOWS[0],
                                  20000.0, {11: frames}, 11, "A", order)

    assert {item.condition for item in controls} == {
        "paired", "frozen_plasticity", "matched_reference",
        "no_external_dan", "temporally_unpaired",
    }
    assert all(item.test_cs_onset_ms - item.training_t0_ms == 20000.0
               for item in controls)
    assert len({item.elapsed_ms for item in controls}) == 1
    assert all(item.elapsed_ms >= item.test_cs_onset_ms
               + configuration.cs_duration_ms + 200.0 for item in controls)
    assert next(item for item in controls if item.condition == "temporally_unpaired") \
        .unpaired_nearest_cs_boundary_ms == 10000.0


@pytest.mark.parametrize("configuration,order,condition,controls", [
    (GRID[0], "AB", "paired", False),
    (GRID[1], "AB", "paired", False),
    (GRID[1], "BA", "paired", False),
    (GRID[5], "BA", "paired", False),
    (GRID[1], "AB", "no_external_dan", True),
    (GRID[5], "BA", "temporally_unpaired", True),
])
def test_training_observations_use_passive_learning_after_t0_and_in_black_gaps(
    configuration, order, condition, controls,
):
    engine = TinyEngine()
    recorder = PointRecorder(capture_observations=True)
    run = _Run(engine, recorder, engine.identity())
    frames = {name: AssayStimuli(seed=11, family="qualification").frame(name)
              for name in ("A", "B", "C")}

    _, _, _, t0 = _training(run, configuration, "A", order, condition, frames,
                            controls=controls)

    assert any(event["learning"] for event in recorder.observations)
    assert all(not event["learning"] and event["stimulation"] is None
               for event in recorder.observations if event["start_ms"] >= t0)
    assert all(not event["learning"] for event in recorder.observations
               if event["stimulus"] is None and event["stimulation"] is None)
    assert any(event["start_ms"] >= t0 for event in recorder.observations)


def test_checkpoint_handoff_and_restore_ancestry(tmp_path):
    class HandoffRecorder:
        def __init__(self):
            self.events = []
            self.checkpoints = {}

        def ingest_checkpoint(self, name, source, *, origin_branch_id):
            data = Path(source).read_bytes()
            from hashlib import sha256
            digest = sha256(data).hexdigest()
            self.checkpoints[name] = (data, origin_branch_id, digest)
            return digest

        def append(self, event):
            self.events.append(event)

    engine = TinyEngine()
    recorder = HandoffRecorder()
    run = _Run(engine, recorder, engine.identity())
    baseline = tmp_path / "baseline.npz"
    run.checkpoint(baseline)
    assert recorder.checkpoints["brain-before.npz"][0] == baseline.read_bytes()
    assert recorder.events[-1]["checkpoint_name"] == "brain-before.npz"
    assert "parent_checkpoint_sha256" not in recorder.events[-1]
    assert "parent_branch_id" not in recorder.events[-1]
    run.branch_id = "qualification/pre/A"
    run.restore(baseline)
    restored = recorder.events[-1]
    assert restored["parent_branch_id"] == "qualification/baseline"
    assert restored["parent_checkpoint_sha256"] == recorder.checkpoints["brain-before.npz"][2]
    assert restored["sim_ms"] == 0.0
    run.observe(np.zeros((3, 3, 3), dtype=np.uint8), 100.0)
    assert recorder.events[-1]["sim_ms"] == recorder.events[-1]["end_ms"] == 100.0


def test_selected_controls_record_neutral_chunks_and_unique_branches(tmp_path):
    engine = TinyEngine()

    class Recorder:
        def __init__(self):
            self.events = []

        def append(self, event):
            self.events.append(event)

    recorder = Recorder()
    run = _Run(engine, recorder, engine.identity())
    baseline = tmp_path / "baseline.npz"
    run.checkpoint(baseline)
    frames = {name: AssayStimuli(seed=11, family="qualification").frame(name)
              for name in ("A", "B", "C")}
    _selected_controls(run, baseline, GRID[0], RESPONSE_WINDOWS[0], 10000.0,
                       {11: frames}, 11, "A", "AB")
    neutral = [item for item in recorder.events if item["type"] == "neutral_gap_chunk"]
    assert neutral
    assert all(0 < item["duration_ms"] <= 500.0 and item["learning"] is False
               and item["stimulation"] is None and item["input_sha256"]
               for item in neutral)
    restores = [item for item in recorder.events if item["type"] == "qualification_restore"]
    assert len({item["branch_id"] for item in restores}) == len(restores)
    assert any("matched_reference/state_probe" in item["branch_id"]
               for item in restores)


@pytest.mark.parametrize("fault,expected_status", [(None, "supported"),
                                                   ("no_learning", "unsupported")])
def test_tiny_qualification_stream_seals_with_checkpoint_ancestry(
    tmp_path, monkeypatch, fault, expected_status,
):
    import fly_connectome_sim.experiment.qualification as module
    from fly_connectome_sim.experiment.recorder import RunRecorder, verify_run

    monkeypatch.setattr(module, "GRID", GRID[:1])
    monkeypatch.setattr(module, "RESPONSE_WINDOWS", RESPONSE_WINDOWS[:1])
    monkeypatch.setattr(module, "RETENTION_CANDIDATES_MS", RETENTION_CANDIDATES_MS[:1])
    engine = TinyEngine(fault=fault)
    metadata = {
        "engine_identity": engine.identity(), "protocol_version": "qualification/v1",
        "stimulus_version": "associative-stimuli/v1", "family": "qualification",
        "seeds": [11, 23], "factors": {"grid": [asdict(GRID[0])]},
        "input_sha256": ["a" * 64],
    }
    target = tmp_path / "qualification"
    with RunRecorder(target, run_kind="qualification", metadata=metadata,
                     root_branch_id="qualification/baseline") as recorder:
        result = module.qualify(lambda: engine, recorder,
                                seeds=(11, 23), family="qualification")
    verified = verify_run(target)
    assert result.status == expected_status
    assert verified.manifest["event_count"] > 100
    assert {"brain-before.npz", "brain-after.npz"} <= set(verified.manifest["checkpoints"])
    events = list(verified.iter_events())
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json")
                        .read_text(encoding="utf-8"))["$defs"]["event"]
    assert schema["dependentRequired"]["parent_branch_id"] == ["parent_checkpoint_sha256"]
    for item in events:
        assert set(schema["required"]) <= item.keys()
        for field, dependencies in schema["dependentRequired"].items():
            if field in item:
                assert set(dependencies) <= item.keys()
        for key, rule in schema["properties"].items():
            if key not in item:
                continue
            if rule.get("type") == "string":
                assert isinstance(item[key], str)
                assert len(item[key]) >= rule.get("minLength", 0)
            elif rule.get("type") == "integer":
                assert type(item[key]) is int
            elif rule.get("type") == "number":
                assert type(item[key]) in (int, float) and math.isfinite(item[key])
            if "minimum" in rule:
                assert item[key] >= rule["minimum"]
            if "pattern" in rule:
                assert re.fullmatch(rule["pattern"], item[key])
            elif "$ref" in rule:
                assert re.fullmatch("[0-9a-f]{64}", item[key])
    root_events = [item for item in events if item["branch_id"] == "qualification/baseline"]
    assert all("parent_checkpoint_sha256" not in item and "parent_branch_id" not in item
               for item in root_events)
    first_by_branch = {}
    for item in events:
        first_by_branch.setdefault(item["branch_id"], item)
    assert all("parent_branch_id" in item and "parent_checkpoint_sha256" in item
               for branch, item in first_by_branch.items()
               if branch != "qualification/baseline")
    assert any(item["type"] == "qualification_point" for item in events)
    terminal = events[-1]
    assert terminal["type"] == "qualification_result"
    assert sum(item["type"] == "qualification_result" for item in events) == 1
    assert terminal["status"] == result.status
    assert terminal["family"] == result.family
    assert terminal["seeds"] == list(result.seeds)
    assert terminal["selected_configuration"] == (
        asdict(result.selected_configuration) if result.selected_configuration else None
    )
    assert terminal["selected_window"] == (
        asdict(result.selected_window) if result.selected_window else None
    )
    assert terminal["selected_retention_ms"] == result.selected_retention_ms
    assert terminal["observed_effect_sign"] == result.observed_effect_sign
    assert terminal["benchmark"] == {key: value for key, value in result.benchmark.items()
                                      if key != "wall_seconds"}
    assert terminal["compute_seconds"] == result.benchmark["wall_seconds"]
    assert terminal["benchmark"]["event_count"] == verified.manifest["event_count"] - 1
    assert "points" not in terminal and "controls" not in terminal
