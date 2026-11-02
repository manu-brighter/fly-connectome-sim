"""Declared, unvalidated display policy for measured lateral motor counts."""

from __future__ import annotations

from dataclasses import asdict

from .adapter import LateralMotorAdapter
from .recorder import RunArtifactError


POLICY_VERSION = "right-scroll/v1"
ADAPTER = LateralMotorAdapter()


def _profile_version(profile: str) -> str:
    if type(profile) is not str or profile not in {"standard", "fast-feed"}:
        raise RunArtifactError("Unsupported video observation profile")
    return "v1" if profile == "standard" else "v2"


def evaluate_video_policy(
    *, counts: list[dict[str, int]], populations: dict[str, int],
    clip_index: int, clip_count: int, clip_start_tick: int,
    frame_index: int, end_tick: int, session_limit_tick: int = 80000,
    profile: str = "standard",
) -> dict:
    """Evaluate after one complete 100 ms boundary using only this clip's frames."""
    version = _profile_version(profile)
    minimum_dwell_ticks = 10000 if profile == "standard" else 30000
    if (type(frame_index) is not int or not 0 <= frame_index < 120
            or frame_index % 3 != 2 or len(counts) != frame_index + 1
            or type(clip_index) is not int or type(clip_count) is not int
            or not 0 <= clip_index < clip_count <= 5
            or type(clip_start_tick) is not int or type(end_tick) is not int
            or type(session_limit_tick) is not int or session_limit_tick != 80000
            or end_tick != clip_start_tick + (frame_index + 1) * 1000 // 3
            or end_tick > session_limit_tick):
        raise RunArtifactError("Invalid video policy clock or occurrence")
    if (set(populations) != {"motor_left", "motor_right"}
            or any(type(size) is not int or size < 1 for size in populations.values())
            or any(type(row) is not dict or set(row) != set(populations)
                   or any(type(value) is not int or value < 0 for value in row.values())
                   for row in counts)):
        raise RunArtifactError("Invalid measured motor evidence")
    window = None
    readout = None
    if frame_index >= 8:
        sums = {name: sum(row[name] for row in counts[-9:]) for name in populations}
        window = {
            "start_tick": end_tick - 3000, "end_tick": end_tick,
            "frame_count": 9, "counts": sums, "populations": dict(populations),
        }
        readout = asdict(ADAPTER.adapt({"rates_hz": {
            name: sums[name] / (populations[name] * 0.3) for name in populations
        }}))
    dwell_met = end_tick - clip_start_tick >= minimum_dwell_ticks
    if end_tick == session_limit_tick:
        action, reason, trigger, next_index = "stop", "session_limit", "session_limit", None
    else:
        if frame_index == 119:
            trigger = "clip_window_end"
        elif dwell_met and readout is not None and readout["action"] == "inspect_right":
            trigger = "motor_right"
        else:
            trigger = None
        if trigger is None:
            action, next_index = "watch", clip_index
            reason = "minimum_dwell" if not dwell_met else "motor_left_or_defer"
        elif clip_index + 1 == clip_count:
            action, reason, next_index = "stop", "playlist_exhausted", None
        else:
            action, reason, next_index = "advance", trigger, clip_index + 1
    return {
        "policy_version": f"right-scroll/{version}",
        "effective_tick": end_tick,
        "window": window,
        "readout": readout,
        "minimum_dwell_met": dwell_met,
        "action": action,
        "reason": reason,
        "trigger": trigger,
        "next_clip_index": next_index,
    }
