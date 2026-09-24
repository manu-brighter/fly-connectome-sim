"""Deterministic controlled RGB stimuli for experiment schedules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np


StimulusIdentity = Literal["A", "B"]
AssayIdentity = Literal["A", "B", "C"]
StimulusFamily = Literal["qualification", "confirmation"]
StimulusSide = Literal["left", "center", "right"]
ColorAssignment = Literal["fixed", "rotated"]


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


@dataclass(frozen=True)
class AssayStimuli:
    """Factorized A/B/C patterns made from one RGB pixel inventory per family."""

    seed: int
    family: StimulusFamily
    width: int = 32
    height: int = 32
    version: str = "associative-stimuli/v1"

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Stimulus seed must be a non-negative integer")
        if self.family not in {"qualification", "confirmation"}:
            raise ValueError("Stimulus family must be qualification or confirmation")
        if (
            isinstance(self.width, bool) or not isinstance(self.width, int)
            or isinstance(self.height, bool) or not isinstance(self.height, int)
            or self.width < 3 or self.height < 3
        ):
            raise ValueError("Assay stimulus dimensions require width and height >= 3")
        if self.version != "associative-stimuli/v1":
            raise ValueError(f"Unsupported assay stimulus version: {self.version}")

    def frame(
        self,
        identity: AssayIdentity,
        *,
        side: StimulusSide = "center",
        color_assignment: ColorAssignment = "fixed",
    ) -> np.ndarray:
        """Return a new RGB frame; pattern, side and color mapping are independent."""
        if identity not in {"A", "B", "C"}:
            raise ValueError(f"Unknown assay stimulus: {identity}")
        if side not in {"left", "center", "right"}:
            raise ValueError(f"Unknown stimulus side: {side}")
        if color_assignment not in {"fixed", "rotated"}:
            raise ValueError(f"Unknown color assignment: {color_assignment}")

        family_code = 1 if self.family == "qualification" else 2
        inventory_rng = np.random.default_rng(np.random.SeedSequence([self.seed, family_code, 0]))
        inventory = inventory_rng.integers(
            0, 255, size=(self.width * self.height - 1, 3), dtype=np.uint8,
        )
        identity_index = {"A": 0, "B": 1, "C": 2}[identity]
        pattern_rng = np.random.default_rng(
            np.random.SeedSequence([self.seed, family_code, identity_index + 1]),
        )
        pattern = inventory[pattern_rng.permutation(len(inventory))]
        # The only R=255 pixel occupies a different row for each identity.
        # Horizontal rolls change only its column, so all nine identity/side
        # combinations remain distinct even at the 3x3 minimum geometry.
        marker_index = identity_index * self.width + self.width // 2
        pixels = np.empty((self.width * self.height, 3), dtype=np.uint8)
        pixels[:marker_index] = pattern[:marker_index]
        pixels[marker_index] = (255, family_code, self.seed % 256)
        pixels[marker_index + 1 :] = pattern[marker_index:]
        frame = pixels.reshape(self.height, self.width, 3)
        if color_assignment == "rotated":
            frame = frame[:, :, [1, 2, 0]]
        side_shift = {"left": -max(1, self.width // 4), "center": 0, "right": max(1, self.width // 4)}[side]
        return np.roll(frame, shift=side_shift, axis=1)
