"""Project-owned input, stimulation and telemetry boundary."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import time
from typing import Literal, NotRequired, TypedDict

import numpy as np

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type StimulationPopulation = Literal["pam11", "ppl101"]


class NamedRates(TypedDict):
    pam11: float
    ppl101: float
    kc: float
    mbon07: float
    mbon11: float
    motor_left: float
    motor_right: float


class NamedSpikeCounts(TypedDict):
    pam11: int
    ppl101: int
    kc: int
    mbon07: int
    mbon11: int
    motor_left: int
    motor_right: int


class StimulationRecord(TypedDict):
    population: StimulationPopulation
    current_mv: float
    duration_ms: float


class SpikeBin(TypedDict):
    end_ms: float
    duration_ms: float
    group_spikes: NamedSpikeCounts
    qualification_detail: NotRequired[dict[str, JsonValue]]


class ModelFingerprint(TypedDict):
    version: str
    sources_sha256: dict[str, str]
    sha256: str


class NativeBuildIdentity(TypedDict):
    model: str
    source_sha256: str
    compiler: str
    flags: list[str]
    library: str
    binary_sha256: str


class ModelProvenance(TypedDict):
    model: str
    model_fingerprint: ModelFingerprint
    build: NativeBuildIdentity
    eta: float
    parameters: dict[str, JsonValue]
    graph_ids_sha256: str
    graph_ptr_sha256: str
    graph_post_sha256: str
    plastic_edges_sha256: str
    configuration_sha256: dict[str, JsonValue]


class EngineIdentityPayload(TypedDict):
    version: str
    model_provenance: ModelProvenance
    neural_groups: dict[str, list[int]]


class EngineIdentity(EngineIdentityPayload):
    sha256: str


class FlyTelemetry(TypedDict):
    sim_ms: float
    interval_ms: float
    compute_seconds: float
    kernel_seconds: float
    total_spikes: int
    rates_hz: NamedRates
    turn_hz: float
    stimulation: StimulationRecord | None
    learning: bool
    input_shape: list[int]
    input_dtype: str
    input_sha256: str
    engine_identity: EngineIdentity
    spike_sha256: str
    memory: dict[str, JsonValue]
    bins: list[SpikeBin]
    pathway_detail: NotRequired[dict[str, JsonValue]]
    qualification_detail: NotRequired[dict[str, JsonValue]]


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _rgb_input_sha256(frame: np.ndarray) -> str:
    """Hash canonical JSON metadata, LF, then logical C-order RGB bytes.

    The versioned header contains the dtype name, rank and full shape. C-order
    traversal normalizes equivalent contiguous arrays and strided views.
    """
    header = {
        "version": "rgb-input/v1",
        "dtype": frame.dtype.name,
        "rank": frame.ndim,
        "shape": [int(size) for size in frame.shape],
    }
    digest = sha256(_canonical_json(header) + b"\n")
    digest.update(frame.tobytes(order="C"))
    return digest.hexdigest()


def _array_summary(values: np.ndarray) -> dict[str, JsonValue]:
    """Summarize an ordered numeric vector, hashing its float64 C-order bytes."""
    data = np.asarray(values, dtype=np.float64)
    if not np.isfinite(data).all():
        raise ValueError("Nonfinite diagnostic value")
    return {
        "count": int(data.size),
        "minimum": float(data.min()) if data.size else None,
        "mean": float(data.mean()) if data.size else None,
        "maximum": float(data.max()) if data.size else None,
        "sha256": sha256(data.tobytes(order="C")).hexdigest(),
    }


def _finite_values(values: np.ndarray) -> list[float]:
    data = np.asarray(values, dtype=np.float64)
    if not np.isfinite(data).all():
        raise ValueError("Nonfinite diagnostic value")
    return [float(value) for value in data]


@dataclass(frozen=True)
class NeuralGroups:
    pam11: np.ndarray
    ppl101: np.ndarray
    kc: np.ndarray
    mbon07: np.ndarray
    mbon11: np.ndarray
    motor_left: np.ndarray
    motor_right: np.ndarray

    @classmethod
    def from_brain(cls, brain) -> "NeuralGroups":
        from .neural.common import annotations

        cells = annotations(brain.ids)
        types = cells.type.fillna("")

        def by_type(name: str) -> np.ndarray:
            return np.flatnonzero(types.eq(name)).astype(np.int32)

        return cls(
            pam11=brain.circuit["reward"].copy(),
            ppl101=brain.circuit["aversive"].copy(),
            kc=brain.circuit["kc"].copy(),
            mbon07=by_type("MBON07"),
            mbon11=by_type("MBON11"),
            motor_left=np.flatnonzero(
                types.eq("DNa02") & cells.somaSide.eq("L")
            ).astype(np.int32),
            motor_right=np.flatnonzero(
                types.eq("DNa02") & cells.somaSide.eq("R")
            ).astype(np.int32),
        )


class FlyEngine:
    """Advance visual neural time and expose named, measured populations."""

    def __init__(self, *, brain, groups: NeuralGroups):
        self.brain = brain
        group_arrays: dict[str, np.ndarray] = {}
        for name, indices in vars(groups).items():
            values = np.asarray(indices).copy()
            if values.ndim != 1 or len(values) == 0:
                raise ValueError(f"Neural group must be nonempty: {name}")
            if np.any(values < 0) or np.any(values >= brain.n):
                raise ValueError(f"Neural group is outside graph: {name}")
            values.flags.writeable = False
            group_arrays[name] = values
        self._groups = NeuralGroups(**group_arrays)
        self._identity_json: bytes | None = None

    @property
    def groups(self) -> NeuralGroups:
        return self._groups

    @classmethod
    def from_prepared_graph(cls) -> "FlyEngine":
        from .data import verify_prepared_graph
        from .neural.common import DATA
        from .neural.visual import VisualMemoryBrain

        verify_prepared_graph(DATA)
        brain = VisualMemoryBrain()
        return cls(brain=brain, groups=NeuralGroups.from_brain(brain))

    def identity(self) -> EngineIdentity:
        """Return a defensive copy of the cached immutable-model identity."""
        if self._identity_json is None:
            self._identity_json = _canonical_json(self._create_identity())
        else:
            self.brain.assert_model_provenance_locked()
        return json.loads(self._identity_json)

    def _create_identity(self) -> EngineIdentity:
        model_provenance: ModelProvenance = json.loads(
            _canonical_json(self.brain.lock_model_provenance())
        )
        payload: EngineIdentityPayload = {
            "version": "fly-engine/v1",
            "model_provenance": model_provenance,
            "neural_groups": {
                name: [int(index) for index in indices]
                for name, indices in vars(self.groups).items()
            },
        }
        return {**payload, "sha256": sha256(_canonical_json(payload)).hexdigest()}

    def observe(
        self,
        frame: np.ndarray,
        duration_ms: float,
        *,
        stimulation: StimulationPopulation | None = None,
        current_mv: float = 20.0,
        learning: bool = False,
        pathway_detail: bool = False,
        qualification_detail: bool = False,
    ) -> FlyTelemetry:
        if (
            not isinstance(frame, np.ndarray)
            or frame.dtype != np.uint8
            or frame.ndim != 3
            or frame.shape[2] != 3
            or min(frame.shape[:2]) < 1
        ):
            raise ValueError("A nonempty RGB uint8 frame is required")
        if (
            not math.isfinite(duration_ms)
            or duration_ms < 0.1
            or duration_ms > 500.0
            or abs(duration_ms * 10 - round(duration_ms * 10)) > 1e-7
        ):
            raise ValueError("Duration must be 0.1–500 ms in 0.1 ms increments")
        if not isinstance(learning, bool):
            raise ValueError("Learning must be a boolean")
        if not isinstance(pathway_detail, bool) or not isinstance(qualification_detail, bool):
            raise ValueError("Detail flags must be boolean")

        populations: dict[StimulationPopulation, np.ndarray] = {
            "pam11": self.groups.pam11,
            "ppl101": self.groups.ppl101,
        }
        if stimulation is not None and stimulation not in populations:
            raise ValueError(f"Unknown stimulation population: {stimulation}")
        if stimulation is not None and (
            not math.isfinite(current_mv) or current_mv <= 0 or current_mv > 100
        ):
            raise ValueError("Stimulation current must be finite and within 0–100 mV")
        engine_identity = self.identity()

        pulse: tuple[np.ndarray, float] | None = None
        if stimulation is not None:
            pulse = (populations[stimulation], float(current_mv))

        brain = self.brain
        candidate_positions = np.empty(0, dtype=np.int64)
        candidate_edges = np.empty(0, dtype=np.int64)
        candidate_kcs = np.empty(0, dtype=np.int32)
        if pathway_detail or qualification_detail:
            edges = brain.circuit["edges"]
            candidate_positions = np.flatnonzero(
                np.isin(brain.post[edges], self.groups.mbon11)
            )
            candidate_edges = edges[candidate_positions]
            candidate_kcs = np.unique(brain.circuit["pre"][candidate_positions])
            drive = brain.rgb_drive(frame)
        totals = np.zeros(brain.n, dtype=np.int64)
        bins: list[SpikeBin] = []
        remaining_ticks = round(duration_ms / brain.dt)
        kernel_seconds = 0.0
        started = time.perf_counter()

        while remaining_ticks:
            ticks = min(100, remaining_ticks)
            interval_ms = ticks * brain.dt
            counts, elapsed = brain.rgb_step(
                frame,
                interval_ms,
                learning=learning,
                stimulation=pulse,
            )
            totals += counts
            kernel_seconds += elapsed
            spike_bin: SpikeBin = {
                    "end_ms": round(float(brain.sim_ms), 3),
                    "duration_ms": interval_ms,
                    "group_spikes": {
                        "pam11": int(counts[self.groups.pam11].sum()),
                        "ppl101": int(counts[self.groups.ppl101].sum()),
                        "kc": int(counts[self.groups.kc].sum()),
                        "mbon07": int(counts[self.groups.mbon07].sum()),
                        "mbon11": int(counts[self.groups.mbon11].sum()),
                        "motor_left": int(counts[self.groups.motor_left].sum()),
                        "motor_right": int(counts[self.groups.motor_right].sum()),
                    },
                }
            if qualification_detail:
                u = brain.memory_u[candidate_positions]
                w = brain.memory_w[candidate_positions]
                efficacy = brain.weight[candidate_edges] / brain.baseline_plastic[candidate_positions]
                lower = brain.rule_parameters["minimum_fraction"] - 1
                upper = brain.rule_parameters["maximum_fraction"] - 1
                lower_mask = (u <= lower) | (w <= lower)
                upper_mask = (u >= upper) | (w >= upper)
                lower_hits = int(np.count_nonzero(lower_mask))
                upper_hits = int(np.count_nonzero(upper_mask))
                spike_bin["qualification_detail"] = {
                    "rate_kc": _finite_values(brain.rate_kc[candidate_positions]),
                    "rate_dan": _finite_values(brain.rate_dan),
                    "memory_u": _array_summary(u),
                    "memory_w": _array_summary(w),
                    "efficacy": _array_summary(efficacy),
                    "lower_bound_hits": lower_hits,
                    "upper_bound_hits": upper_hits,
                    "bound_hit_fraction": (
                        int(np.count_nonzero(lower_mask | upper_mask)) / len(candidate_edges)
                        if len(candidate_edges) else 0.0
                    ),
                }
            bins.append(spike_bin)
            remaining_ticks -= ticks

        seconds = duration_ms / 1000.0

        def mean_rate(indices: np.ndarray) -> float:
            return float(totals[indices].sum() / (len(indices) * seconds))

        rates: NamedRates = {
            "pam11": mean_rate(self.groups.pam11),
            "ppl101": mean_rate(self.groups.ppl101),
            "kc": mean_rate(self.groups.kc),
            "mbon07": mean_rate(self.groups.mbon07),
            "mbon11": mean_rate(self.groups.mbon11),
            "motor_left": mean_rate(self.groups.motor_left),
            "motor_right": mean_rate(self.groups.motor_right),
        }
        stimulation_record: StimulationRecord | None = None
        if stimulation is not None:
            stimulation_record = {
                "population": stimulation,
                "current_mv": float(current_mv),
                "duration_ms": duration_ms,
            }

        telemetry: FlyTelemetry = {
            "sim_ms": round(float(brain.sim_ms), 3),
            "interval_ms": duration_ms,
            "compute_seconds": time.perf_counter() - started,
            "kernel_seconds": kernel_seconds,
            "total_spikes": int(totals.sum()),
            "rates_hz": rates,
            "turn_hz": rates["motor_right"] - rates["motor_left"],
            "stimulation": stimulation_record,
            "learning": learning,
            "input_shape": [int(size) for size in frame.shape],
            "input_dtype": frame.dtype.name,
            "input_sha256": _rgb_input_sha256(frame),
            "engine_identity": engine_identity,
            "spike_sha256": sha256(totals.tobytes()).hexdigest(),
            "memory": brain.memory(),
            "bins": bins,
        }
        if pathway_detail or qualification_detail:
            telemetry["pathway_detail"] = {
                "modeled_visual_drive": {
                    "r1_r6": _array_summary(drive["r1_r6"]),
                    "r8": _array_summary(drive["r8"]),
                },
                "candidate_edge_indices": [int(edge) for edge in candidate_edges],
                "candidate_edge_pre_source_ids": [
                    str(brain.ids[index]) for index in brain.circuit["pre"][candidate_positions]
                ],
                "candidate_edge_post_source_ids": [
                    str(brain.ids[index]) for index in brain.post[candidate_edges]
                ],
                "candidate_kc_indices": [int(index) for index in candidate_kcs],
                "candidate_kc_source_ids": [str(brain.ids[index]) for index in candidate_kcs],
                "candidate_kc_spike_counts": [int(totals[index]) for index in candidate_kcs],
                "candidate_kc_spikes_by_source_id": {
                    str(brain.ids[index]): int(totals[index]) for index in candidate_kcs
                },
            }
        if qualification_detail:
            telemetry["qualification_detail"] = {
                "dan_indices": [int(index) for index in brain.circuit["dan"]],
                "dan_source_ids": [str(brain.ids[index]) for index in brain.circuit["dan"]],
                "rate_kc_semantics": "model_trace_state_hz",
                "rate_dan_semantics": "model_trace_state_hz",
                "maximum_bound_hit_fraction": max(
                    bin["qualification_detail"]["bound_hit_fraction"] for bin in bins
                ),
            }
        return telemetry
