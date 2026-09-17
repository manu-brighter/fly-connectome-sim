"""Deterministic controlled RGB stimuli for the first A/B assay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


StimulusIdentity = Literal["A", "B"]


@dataclass(frozen=True)
class SyntheticStimuli:
    """JSON-safe stimulus declaration that regenerates its RGB frames on demand."""

    seed: int
    width: int = 32
    height: int = 32
    version: str = "synthetic-ab/v1"

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Stimulus seed must be a non-negative integer")
        if self.width < 2 or self.height < 1:
            raise ValueError("Stimulus dimensions must be at least 2 by 1")

    def frame(self, stimulus: StimulusIdentity) -> np.ndarray:
        """Return a fresh deterministic RGB uint8 frame for A or B."""
        if stimulus not in {"A", "B"}:
            raise ValueError(f"Unknown synthetic stimulus: {stimulus}")

        stream = 1 if stimulus == "A" else 2
        generator = np.random.default_rng(np.random.SeedSequence([self.seed, stream]))
        frame = generator.integers(
            0,
            48,
            size=(self.height, self.width, 3),
            dtype=np.uint8,
        )
        bar_width = max(1, self.width // 3)
        if stimulus == "A":
            frame[:, :bar_width] = (240, 125, 30)
        else:
            frame[:, self.width - bar_width :] = (15, 100, 230)
        return frame
