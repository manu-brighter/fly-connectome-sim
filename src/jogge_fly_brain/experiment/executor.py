"""Advance a scheduled assay without hiding neutral neural time or fork history."""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
from typing import Callable

import numpy as np

from jogge_fly_brain.engine import FlyEngine

from .protocol import ProtocolSchedule, ProtocolStep
from .stimuli import AssayStimuli


EventSink = Callable[[dict], None]


def _grid_ticks(value: float, name: str, *, maximum: float | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite 0.1 ms grid duration")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} is outside finite timing range") from error
    ticks = number * 10
    if (not math.isfinite(number) or number < 0 or not math.isfinite(ticks)
            or abs(ticks - round(ticks)) > 1e-7
            or (maximum is not None and number > maximum)):
        raise ValueError(f"{name} must be a finite 0.1 ms grid duration")
    return round(ticks)


def _duration(value: float, name: str, *, maximum: float | None = None) -> float:
    return _grid_ticks(value, name, maximum=maximum) / 10


def _checkpoint_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _event(kind: str, branch_id: str, telemetry: dict | None, *, sim_ms: float,
           duration_ms: float = 0.0, parent_checkpoint_sha256: str | None = None,
           stimulation: str | None = None, learning: bool = False, **fields: object) -> dict:
    return {
        "type": kind,
        "branch_id": branch_id,
        "parent_checkpoint_sha256": parent_checkpoint_sha256,
        "input_sha256": telemetry["input_sha256"] if telemetry is not None else None,
        "sim_ms": round(float(sim_ms), 3),
        "duration_ms": duration_ms,
        "stimulation": stimulation,
        "learning": learning,
        **fields,
    }


def advance_neutral(
    engine: FlyEngine,
    duration_ms: float,
    shape: tuple[int, int, int],
    *,
    stimulation: str | None = None,
    learning: bool = False,
    branch_id: str,
    on_event: EventSink,
    parent_checkpoint_sha256: str | None = None,
) -> None:
    """Observe black RGB throughout a gap, in chunks of at most 500 ms."""
    duration = _duration(duration_ms, "Neutral duration")
    if len(shape) != 3 or min(shape[:2]) < 1 or shape[2] != 3:
        raise ValueError("Neutral shape must be nonempty RGB")
    black = np.zeros(shape, dtype=np.uint8)
    remaining_ticks = round(duration * 10)
    while remaining_ticks:
        chunk_ticks = min(5000, remaining_ticks)
        chunk_ms = chunk_ticks / 10
        telemetry = engine.observe(black, chunk_ms, stimulation=stimulation, learning=learning)
        on_event(_event(
            "neutral_gap_chunk", branch_id, telemetry, sim_ms=telemetry["sim_ms"],
            duration_ms=chunk_ms, parent_checkpoint_sha256=parent_checkpoint_sha256,
            stimulation=stimulation, learning=learning,
        ))
        remaining_ticks -= chunk_ticks


def _scheduled_steps(schedule: ProtocolSchedule) -> tuple[ProtocolStep, ...]:
    """Check the complete schedule before the first engine mutation."""
    previous_end = 0.0
    seen_test = False
    for step in schedule.steps:
        start = _duration(step.timestamp_ms, "Step timestamp")
        duration = _duration(step.duration_ms, "Step duration", maximum=500.0)
        if duration < 0.1 or start < previous_end - 1e-7:
            raise ValueError("Schedule steps must be positive and nonoverlapping")
        previous_end = round(start + duration, 3)
        if step.phase == "reward_free_test":
            seen_test = True
        elif seen_test:
            raise ValueError("Training cannot resume after reward-free tests")
    return schedule.steps


def _training_end_ms(steps: tuple[ProtocolStep, ...]) -> float:
    """Return T=0: the latest pairing presentation or external DAN end."""
    return max(
        (round(step.timestamp_ms + step.duration_ms, 3) for step in steps
         if step.phase == "pairing" or step.stimulation is not None),
        default=0.0,
    )


def execute_schedule(
    engine: FlyEngine,
    schedule: ProtocolSchedule,
    stimuli: AssayStimuli,
    *,
    branch_id: str,
    on_event: EventSink,
) -> None:
    """Run baseline/pairing through T=0; retention executes declared tests."""
    steps = _scheduled_steps(schedule)
    shape = (stimuli.height, stimuli.width, 3)
    for step in steps:
        if step.phase == "reward_free_test":
            break
        gap = round(step.timestamp_ms - engine.brain.sim_ms, 3)
        if gap < 0:
            raise ValueError("Engine time is later than the scheduled step")
        advance_neutral(engine, gap, shape, branch_id=branch_id, on_event=on_event)
        frame = (np.zeros(shape, dtype=np.uint8) if step.stimulus is None else
                 stimuli.frame(step.stimulus, side=step.side or "center",
                               color_assignment=schedule.color_assignment))
        telemetry = engine.observe(frame, step.duration_ms,
                                   stimulation=step.stimulation, learning=step.learning)
        on_event(_event(
            "step", branch_id, telemetry, sim_ms=telemetry["sim_ms"],
            duration_ms=step.duration_ms, stimulation=step.stimulation,
            learning=step.learning, phase=step.phase, stimulus=step.stimulus,
        ))


def retention_test(
    engine: FlyEngine,
    training_end_checkpoint: Path,
    delay_ms: float,
    *,
    schedule: ProtocolSchedule,
    stimuli: AssayStimuli,
    checkpoint_dir: Path,
    branch_id: str,
    on_event: EventSink,
) -> tuple[dict, ...]:
    """Fork one delay from training, then fork A/B/C from its retained state."""
    delay = _duration(delay_ms, "Retention delay")
    _scheduled_steps(schedule)
    tests = tuple(step for step in schedule.steps if step.phase == "reward_free_test")
    training_end = _training_end_ms(schedule.steps)
    if len(tests) != 3 or {step.stimulus for step in tests} != {"A", "B", "C"} or any(
        step.stimulation is not None or step.learning for step in tests
    ):
        raise ValueError("Retention requires reward-free A/B/C test steps")
    training_end_checkpoint = Path(training_end_checkpoint)
    checkpoint_dir = Path(checkpoint_dir)
    training_hash = _checkpoint_hash(training_end_checkpoint)
    engine.brain.restore(training_end_checkpoint)
    restored_ticks = _grid_ticks(engine.brain.sim_ms, "Training-end checkpoint T=0")
    if restored_ticks != _grid_ticks(training_end, "Schedule T=0"):
        raise ValueError("Training-end checkpoint must be restored exactly at schedule T=0")
    on_event(_event("fork", branch_id, None, sim_ms=engine.brain.sim_ms,
                    parent_checkpoint_sha256=training_hash))
    on_event(_event("retention_start", branch_id, None, sim_ms=engine.brain.sim_ms,
                    parent_checkpoint_sha256=training_hash, delay_ms=delay))
    advance_neutral(engine, delay, (stimuli.height, stimuli.width, 3),
                    branch_id=branch_id, on_event=on_event,
                    parent_checkpoint_sha256=training_hash)
    retained_time = round(float(engine.brain.sim_ms), 3)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    retained_path = checkpoint_dir / f"retention-{sha256(branch_id.encode()).hexdigest()[:16]}.npz"
    engine.brain.checkpoint(retained_path)
    retained_hash = _checkpoint_hash(retained_path)
    on_event(_event("retention_end", branch_id, None, sim_ms=retained_time,
                    parent_checkpoint_sha256=training_hash,
                    checkpoint_sha256=retained_hash))

    results = []
    for step in tests:
        test_branch = f"{branch_id}/{step.stimulus}"
        engine.brain.restore(retained_path)
        on_event(_event("fork", test_branch, None, sim_ms=engine.brain.sim_ms,
                        parent_checkpoint_sha256=retained_hash))
        advance_neutral(engine, round(step.timestamp_ms - training_end, 3),
                        (stimuli.height, stimuli.width, 3), branch_id=test_branch,
                        on_event=on_event, parent_checkpoint_sha256=retained_hash)
        frame = stimuli.frame(step.stimulus, side=step.side or schedule.test_side,
                             color_assignment=schedule.color_assignment)
        telemetry = engine.observe(frame, step.duration_ms, learning=False)
        on_event(_event("step", test_branch, telemetry, sim_ms=telemetry["sim_ms"],
                        duration_ms=step.duration_ms,
                        parent_checkpoint_sha256=retained_hash,
                        phase="reward_free_test", stimulus=step.stimulus))
        results.append({"identity": step.stimulus, "branch_id": test_branch,
                        "parent_checkpoint_sha256": retained_hash, "telemetry": telemetry})
    return tuple(results)
