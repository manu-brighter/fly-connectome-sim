"""Project-owned input, stimulation and telemetry boundary."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import time
from typing import Literal, TypedDict

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
            bins.append(
                {
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
            )
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
        return telemetry
