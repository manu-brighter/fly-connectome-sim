"""Versioned, deterministic associative experiment schedules."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Literal, Mapping


Condition = Literal[
    "training", "reciprocal_pairing", "frozen_plasticity",
    "no_external_dan", "temporally_unpaired",
]
ProtocolPhase = Literal["baseline", "pairing", "reward_free_test"]
StimulusIdentity = Literal["A", "B", "C"]
StimulationPopulation = Literal["pam11", "ppl101"]
StimulusSide = Literal["left", "center", "right"]
ColorAssignment = Literal["fixed", "rotated"]

# Retain the validated ten-second separation until split timing intervals exist.
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
    side: StimulusSide | None = None


@dataclass(frozen=True)
class ProtocolSchedule:
    """A seed-recorded protocol fixed before a training run begins."""

    version: str
    condition: str
    seed: int
    steps: tuple[ProtocolStep, ...]
    paired_identity: Literal["A", "B"] | None = None
    presentation_order: tuple[Literal["A", "B"], Literal["A", "B"]] = ("A", "B")
    training_side: StimulusSide = "center"
    test_side: StimulusSide = "center"
    color_assignment: ColorAssignment = "fixed"

    @classmethod
    def create(
        cls,
        *,
        condition: Condition = "training",
        seed: int,
        paired_identity: Literal["A", "B"],
        presentation_order: tuple[Literal["A", "B"], Literal["A", "B"]] = ("A", "B"),
        training_side: StimulusSide = "center",
        test_side: StimulusSide = "center",
        color_assignment: ColorAssignment = "fixed",
        duration_ms: float = 20.0,
        inter_trial_ms: float = 10.0,
    ) -> "ProtocolSchedule":
        migrated = {"reversal": "reciprocal_pairing", "no_dan": "no_external_dan"}
        if isinstance(condition, str) and condition in migrated:
            raise ValueError(f"Condition {condition!r} was renamed; use {migrated[condition]!r}")
        if not isinstance(condition, str) or condition not in {
            "training", "reciprocal_pairing", "frozen_plasticity",
            "no_external_dan", "temporally_unpaired",
        }:
            raise ValueError(f"Unknown protocol condition: {condition}")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("Protocol seed must be a non-negative integer")
        if not isinstance(paired_identity, str) or paired_identity not in {"A", "B"}:
            raise ValueError("Paired identity must be A or B")
        if (
            not isinstance(presentation_order, tuple)
            or len(presentation_order) != 2
            or not all(isinstance(item, str) for item in presentation_order)
            or presentation_order not in {("A", "B"), ("B", "A")}
        ):
            raise ValueError("Presentation order must contain A and B exactly once")
        if (
            not isinstance(training_side, str) or training_side not in {"left", "center", "right"}
            or not isinstance(test_side, str) or test_side not in {"left", "center", "right"}
        ):
            raise ValueError("Training and test side must be left, center or right")
        if not isinstance(color_assignment, str) or color_assignment not in {"fixed", "rotated"}:
            raise ValueError("Color assignment must be fixed or rotated")
        duration_ms = _grid_number(duration_ms, "Duration", minimum=0.1, maximum=500.0)
        inter_trial_ms = _grid_number(inter_trial_ms, "Inter-trial gap", minimum=0)

        order = tuple(presentation_order)
        baseline = [("baseline", identity, None, False, test_side) for identity in (*order, "C")]
        pairing: list[tuple[str, str | None, str | None, bool, str | None]] = []
        learning = condition != "frozen_plasticity"
        for identity in order:
            stimulation = (
                "ppl101"
                if identity == paired_identity and condition not in {"no_external_dan", "temporally_unpaired"}
                else None
            )
            pairing.append(("pairing", identity, stimulation, learning, training_side))
        pairing.insert(1, (
            "pairing", None,
            "ppl101" if condition == "temporally_unpaired" else None,
            learning, None,
        ))
        reward_free_test = [
            ("reward_free_test", identity, None, False, test_side)
            for identity in (*order, "C")
        ]
        timestamp_ms = 0.0
        steps = []
        for index, (phase, stimulus, stimulation, step_learning, side) in enumerate(
            baseline + pairing + reward_free_test
        ):
            steps.append(ProtocolStep(
                timestamp_ms=round(timestamp_ms, 3),
                duration_ms=float(duration_ms),
                phase=phase,
                stimulus=stimulus,
                stimulation=stimulation,
                learning=step_learning,
                side=side,
            ))
            gap_ms = (
                max(inter_trial_ms, UNPAIRED_GAP_MS)
                if len(baseline) <= index < len(baseline) + 2
                else inter_trial_ms
            )
            timestamp_ms += duration_ms + gap_ms
        return cls(
            version="associative-protocol/v1",
            condition=condition,
            seed=seed,
            steps=tuple(steps),
            paired_identity=paired_identity,
            presentation_order=order,
            training_side=training_side,
            test_side=test_side,
            color_assignment=color_assignment,
        )


def _exact_keys(value: object, expected: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{label} has missing or unknown fields")


def _grid_number(value: object, label: str, *, minimum: float, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a numeric 0.1 ms value")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{label} is outside finite timing range") from error
    scaled = number * 10
    if (
        not math.isfinite(number) or number < minimum
        or (maximum is not None and number > maximum)
        or not math.isfinite(scaled)
        or abs(scaled - round(scaled)) > 1e-7
    ):
        raise ValueError(f"{label} must be finite, in range and on the 0.1 ms grid")
    return number


def _parse_steps(raw_steps: object, *, legacy: bool) -> tuple[ProtocolStep, ...]:
    expected_count = 7 if legacy else 9
    if not isinstance(raw_steps, list) or len(raw_steps) != expected_count:
        raise ValueError(f"Protocol requires exactly {expected_count} steps")
    keys = {"timestamp_ms", "duration_ms", "phase", "stimulus", "stimulation", "learning"}
    if not legacy:
        keys.add("side")
    steps = []
    for index, raw in enumerate(raw_steps):
        _exact_keys(raw, keys, f"Step {index}")
        if not isinstance(raw["phase"], str) or raw["phase"] not in {
            "baseline", "pairing", "reward_free_test",
        }:
            raise ValueError(f"Step {index} has invalid phase")
        if raw["stimulus"] is not None and (
            not isinstance(raw["stimulus"], str)
            or raw["stimulus"] not in ({"A", "B"} if legacy else {"A", "B", "C"})
        ):
            raise ValueError(f"Step {index} has invalid stimulus")
        if raw["stimulation"] is not None and (
            not isinstance(raw["stimulation"], str)
            or raw["stimulation"] != ("pam11" if legacy else "ppl101")
        ):
            raise ValueError(f"Step {index} has invalid stimulation")
        if type(raw["learning"]) is not bool:
            raise ValueError(f"Step {index} learning must be boolean")
        if not legacy and raw["side"] is not None and (
            not isinstance(raw["side"], str) or raw["side"] not in {"left", "center", "right"}
        ):
            raise ValueError(f"Step {index} has invalid side")
        steps.append(ProtocolStep(
            timestamp_ms=_grid_number(raw["timestamp_ms"], f"Step {index} timestamp", minimum=0),
            duration_ms=_grid_number(raw["duration_ms"], f"Step {index} duration", minimum=0.1, maximum=500),
            phase=raw["phase"],
            stimulus=raw["stimulus"],
            stimulation=raw["stimulation"],
            learning=raw["learning"],
            side=None if legacy else raw["side"],
        ))
    return tuple(steps)


def _legacy_steps(condition: str, duration_ms: float, inter_trial_ms: float) -> tuple[ProtocolStep, ...]:
    paired = "B" if condition == "reversal" else "A"
    other = "A" if paired == "B" else "B"
    learning = condition != "frozen_plasticity"
    entries = [
        ("baseline", "A", None, False),
        ("baseline", "B", None, False),
        ("pairing", paired, None if condition in {"no_dan", "temporally_unpaired"} else "pam11", learning),
        ("pairing", None, "pam11" if condition == "temporally_unpaired" else None, learning),
        ("pairing", other, None, learning),
        ("reward_free_test", "A", None, False),
        ("reward_free_test", "B", None, False),
    ]
    timestamp_ms = 0.0
    steps = []
    for index, (phase, stimulus, stimulation, step_learning) in enumerate(entries):
        steps.append(ProtocolStep(round(timestamp_ms, 3), duration_ms, phase, stimulus, stimulation, step_learning))
        gap_ms = max(inter_trial_ms, UNPAIRED_GAP_MS) if 2 <= index < 4 else inter_trial_ms
        timestamp_ms += duration_ms + gap_ms
    return tuple(steps)


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"Nonfinite JSON number: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON has duplicate key: {key}")
        result[key] = value
    return result


def schedule_from_json(source: str | bytes | Mapping[str, object]) -> ProtocolSchedule:
    """Read validated emitted associative v1 or historical legacy v2 JSON."""
    if isinstance(source, (str, bytes)):
        try:
            data = json.loads(
                source,
                parse_constant=_reject_nonfinite,
                object_pairs_hook=_unique_object,
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError(f"Invalid protocol JSON: {error}") from error
    elif isinstance(source, Mapping):
        data = source
    else:
        raise ValueError("Protocol input must be JSON or a mapping")
    if not isinstance(data, Mapping):
        raise ValueError("Protocol JSON must be an object")
    version = data.get("version")
    if not isinstance(version, str) or version not in {"ab-protocol/v2", "associative-protocol/v1"}:
        raise ValueError(f"Unsupported protocol version: {version}")
    legacy = version == "ab-protocol/v2"
    top_keys = {"version", "condition", "seed", "steps"}
    if not legacy:
        top_keys.update({"paired_identity", "presentation_order", "training_side", "test_side", "color_assignment"})
    _exact_keys(data, top_keys, "Protocol")
    if isinstance(data["seed"], bool) or not isinstance(data["seed"], int) or data["seed"] < 0:
        raise ValueError("Protocol seed must be a non-negative integer")
    condition = data["condition"]
    if not isinstance(condition, str):
        raise ValueError("Protocol condition must be a string")
    steps = _parse_steps(data["steps"], legacy=legacy)
    duration_ms = steps[0].duration_ms
    inter_trial_ms = _grid_number(
        steps[1].timestamp_ms - steps[0].timestamp_ms - duration_ms,
        "Inter-trial gap", minimum=0,
    )
    if legacy:
        if condition not in {"training", "reversal", "frozen_plasticity", "no_dan", "temporally_unpaired"}:
            raise ValueError(f"Unknown legacy condition: {condition}")
        if steps != _legacy_steps(condition, duration_ms, inter_trial_ms):
            raise ValueError("Legacy protocol steps do not match declared condition and timing")
        return ProtocolSchedule(
            version=version, condition=condition, seed=data["seed"], steps=steps,
            paired_identity="B" if condition == "reversal" else "A",
        )
    if (
        not isinstance(data["presentation_order"], list)
        or len(data["presentation_order"]) != 2
        or not all(isinstance(item, str) for item in data["presentation_order"])
    ):
        raise ValueError("Presentation order must be a JSON array")
    expected = ProtocolSchedule.create(
        condition=condition,
        seed=data["seed"],
        paired_identity=data["paired_identity"],
        presentation_order=tuple(data["presentation_order"]),
        training_side=data["training_side"],
        test_side=data["test_side"],
        color_assignment=data["color_assignment"],
        duration_ms=duration_ms,
        inter_trial_ms=inter_trial_ms,
    )
    if steps != expected.steps:
        raise ValueError("Associative protocol steps do not match declared factors and timing")
    return expected
