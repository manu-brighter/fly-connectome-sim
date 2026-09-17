"""Predeclared, deterministic A/B experiment schedules."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal


Condition = Literal[
    "training",
    "reversal",
    "frozen_plasticity",
    "no_dan",
    "temporally_unpaired",
]
ProtocolPhase = Literal["baseline", "pairing", "reward_free_test"]
StimulusIdentity = Literal["A", "B"]
StimulationPopulation = Literal["pam11", "ppl101"]

# Ten time constants of both 1-second traces in neural.rule: less than 0.005%
# remains. Reserve this separation on both sides of the neutral pairing slot
# in every condition so visual exposure and total elapsed time are matched.
UNPAIRED_GAP_MS = 10000.0


@dataclass(frozen=True)
class ProtocolStep:
    """One simulated-time visual exposure and optional declared DAN pulse."""

    timestamp_ms: float
    duration_ms: float
    phase: ProtocolPhase
    stimulus: StimulusIdentity | None
    stimulation: StimulationPopulation | None
    learning: bool


@dataclass(frozen=True)
class ProtocolSchedule:
    """A seed-recorded protocol fixed before a training run begins."""

    version: str
    condition: Condition
    seed: int
    steps: tuple[ProtocolStep, ...]

    @classmethod
    def create(
        cls,
        *,
        condition: Condition = "training",
        seed: int,
        duration_ms: float = 20.0,
        inter_trial_ms: float = 10.0,
    ) -> "ProtocolSchedule":
        if condition not in {
            "training",
            "reversal",
            "frozen_plasticity",
            "no_dan",
            "temporally_unpaired",
        }:
            raise ValueError(f"Unknown protocol condition: {condition}")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("Protocol seed must be a non-negative integer")
        if (
            not math.isfinite(duration_ms)
            or duration_ms < 0.1
            or duration_ms > 500.0
            or abs(duration_ms * 10 - round(duration_ms * 10)) > 1e-7
        ):
            raise ValueError("Duration must be 0.1–500 ms in 0.1 ms increments")
        gap_ticks = inter_trial_ms * 10
        if (
            not math.isfinite(gap_ticks)
            or gap_ticks < 0
            or abs(gap_ticks - round(gap_ticks)) > 1e-7
        ):
            raise ValueError(
                "Inter-trial gap must be finite, non-negative and in 0.1 ms increments"
            )

        baseline = [
            ("baseline", "A", None, False),
            ("baseline", "B", None, False),
        ]
        pairing_by_condition: dict[Condition, list[tuple[ProtocolPhase, StimulusIdentity | None, StimulationPopulation | None, bool]]] = {
            "training": [
                ("pairing", "A", "pam11", True),
                ("pairing", None, None, True),
                ("pairing", "B", None, True),
            ],
            "reversal": [
                ("pairing", "B", "pam11", True),
                ("pairing", None, None, True),
                ("pairing", "A", None, True),
            ],
            "frozen_plasticity": [
                ("pairing", "A", "pam11", False),
                ("pairing", None, None, False),
                ("pairing", "B", None, False),
            ],
            "no_dan": [
                ("pairing", "A", None, True),
                ("pairing", None, None, True),
                ("pairing", "B", None, True),
            ],
            "temporally_unpaired": [
                ("pairing", "A", None, True),
                ("pairing", None, "pam11", True),
                ("pairing", "B", None, True),
            ],
        }
        reward_free_test = [
            ("reward_free_test", "A", None, False),
            ("reward_free_test", "B", None, False),
        ]
        trial_definitions = baseline + pairing_by_condition[condition] + reward_free_test
        timestamp_ms = 0.0
        steps = []
        for index, (phase, stimulus, stimulation, learning) in enumerate(
            trial_definitions
        ):
            steps.append(
                ProtocolStep(
                    timestamp_ms=round(timestamp_ms, 3),
                    duration_ms=float(duration_ms),
                    phase=phase,
                    stimulus=stimulus,
                    stimulation=stimulation,
                    learning=learning,
                )
            )
            # Gaps after the first two pairing slots surround the neutral slot.
            gap_ms = (
                max(inter_trial_ms, UNPAIRED_GAP_MS)
                if len(baseline) <= index < len(baseline) + 2
                else inter_trial_ms
            )
            timestamp_ms += duration_ms + gap_ms
        return cls(
            version="ab-protocol/v2",
            condition=condition,
            seed=seed,
            steps=tuple(steps),
        )
