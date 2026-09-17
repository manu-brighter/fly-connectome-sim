"""Project-owned input, stimulation and telemetry boundary."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
import time

import numpy as np


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
        self.groups = groups
        for name, indices in vars(groups).items():
            values = np.asarray(indices)
            if values.ndim != 1 or len(values) == 0:
                raise ValueError(f"Neural group must be nonempty: {name}")
            if np.any(values < 0) or np.any(values >= brain.n):
                raise ValueError(f"Neural group is outside graph: {name}")

    @classmethod
    def from_prepared_graph(cls) -> "FlyEngine":
        from .data import verify_prepared_graph
        from .neural.common import DATA
        from .neural.visual import VisualMemoryBrain

        verify_prepared_graph(DATA)
        brain = VisualMemoryBrain()
        return cls(brain=brain, groups=NeuralGroups.from_brain(brain))

    def observe(
        self,
        frame: np.ndarray,
        duration_ms: float,
        *,
        stimulation: str | None = None,
        current_mv: float = 20.0,
        learning: bool = False,
    ) -> dict[str, object]:
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

        populations = {"pam11": self.groups.pam11, "ppl101": self.groups.ppl101}
        if stimulation is not None and stimulation not in populations:
            raise ValueError(f"Unknown stimulation population: {stimulation}")
        if stimulation is not None and (
            not math.isfinite(current_mv) or current_mv <= 0 or current_mv > 100
        ):
            raise ValueError("Stimulation current must be finite and within 0–100 mV")

        pulse = None
        if stimulation is not None:
            pulse = (populations[stimulation], float(current_mv))

        brain = self.brain
        totals = np.zeros(brain.n, dtype=np.int64)
        bins: list[dict[str, object]] = []
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
                        name: int(counts[indices].sum())
                        for name, indices in vars(self.groups).items()
                    },
                }
            )
            remaining_ticks -= ticks

        seconds = duration_ms / 1000.0

        def mean_rate(indices: np.ndarray) -> float:
            return float(totals[indices].sum() / (len(indices) * seconds))

        rates = {
            name: mean_rate(indices)
            for name, indices in vars(self.groups).items()
        }
        stimulation_record = None
        if stimulation is not None:
            stimulation_record = {
                "population": stimulation,
                "current_mv": float(current_mv),
                "duration_ms": duration_ms,
            }

        return {
            "sim_ms": round(float(brain.sim_ms), 3),
            "interval_ms": duration_ms,
            "compute_seconds": time.perf_counter() - started,
            "kernel_seconds": kernel_seconds,
            "total_spikes": int(totals.sum()),
            "rates_hz": rates,
            "turn_hz": rates["motor_right"] - rates["motor_left"],
            "stimulation": stimulation_record,
            "learning": learning,
            "input_sha256": sha256(frame.tobytes()).hexdigest(),
            "spike_sha256": sha256(totals.tobytes()).hexdigest(),
            "memory": brain.memory(),
            "bins": bins,
        }
