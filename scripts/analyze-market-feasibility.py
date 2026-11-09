"""Inventory bounded historical population counts and recorded timing offline."""

from __future__ import annotations

import argparse
from itertools import combinations
import json
import math
import os
from pathlib import Path
import tempfile

from fly_connectome_sim.experiment import recorder as artifacts
from market_artifacts import snapshot_recorded_run, write_json_exclusive


GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
READ_LIMITS = artifacts.RunReadLimits(
    max_manifest_bytes=2 * 1024 * 1024,
    max_event_line_bytes=1024 * 1024,
    max_events_bytes=64 * 1024 * 1024,
    max_events=246,
    max_checkpoints=2,
)
MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024
LIMITATIONS = [
    "No single-cell inference.",
    "No new learning evidence.",
    "No validated drink selection or price mapping.",
    "No long-run or real-time qualification.",
    "Membership overlap does not establish functional independence.",
    "Source identity describes the historical recording, not current-source equivalence.",
    "Recorded timing fields are not a new benchmark or supervisor result.",
]


def _number(value: object) -> float:
    if type(value) not in (int, float):
        raise ValueError("Expected a finite nonnegative number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError("Numeric overflow") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError("Expected a finite nonnegative number")
    return number


def _integer(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("Expected a nonnegative integer, not a boolean")
    return value


def _ticks(value: object) -> int:
    number = _number(value)
    if not math.isfinite(number * 10):
        raise ValueError("Clock overflow")
    tick = round(number * 10)
    if number not in (tick / 10, tick * 0.1):
        raise ValueError("Clock is not an exact 0.1 ms tick")
    return tick


def _groups(identity: dict) -> dict[str, list[int]]:
    groups = identity.get("neural_groups")
    if type(groups) is not dict or set(groups) != set(GROUPS):
        raise ValueError("Missing or unexpected required neural groups")
    for members in groups.values():
        if type(members) is not list or not members:
            raise ValueError("Empty or invalid required neural group")
        for member in members:
            _integer(member)
        if len(set(members)) != len(members):
            raise ValueError("Duplicate neural group member")
    return groups


def _summarize(run: artifacts.VerifiedRun) -> dict[str, object]:
    manifest = run.manifest
    groups = _groups(manifest["metadata"]["engine_identity"])
    memberships = {name: set(groups[name]) for name in GROUPS}
    subset_pairs = [(left, right) for left in GROUPS for right in GROUPS
                    if left != right and memberships[left] <= memberships[right]]
    summaries = {name: {"size": len(groups[name]), "spikes": 0, "min_bin_rate_hz": math.inf,
                        "max_bin_rate_hz": 0.0, "zero_bins": 0, "nonzero_bins": 0}
                 for name in GROUPS}
    observations = bins = duration_ticks = 0
    phase_ticks = {}
    compute, kernel = [], []
    cursor = None
    finished = False
    for event in run.iter_events():
        if (event["branch_id"] != manifest["root_branch_id"]
                or any(name.startswith("parent_") for name in event)
                or event["type"] not in {"checkpoint", "observe"} or finished):
            raise ValueError("Only one uninterrupted observation branch is supported")
        if event["type"] == "checkpoint":
            tick = _ticks(event["sim_ms"])
            if "sim_tick" in event and _integer(event["sim_tick"]) != tick:
                raise ValueError("Checkpoint clock mismatch")
            if cursor is None:
                if event["checkpoint_name"] != "brain-before.npz":
                    raise ValueError("Initial checkpoint required")
                cursor = tick
            elif event["checkpoint_name"] != "brain-after.npz" or cursor != tick:
                raise ValueError("Final checkpoint clock mismatch")
            else:
                finished = True
            continue
        start, end, duration = (_integer(event.get(name)) for name in ("start_tick", "end_tick", "duration_ticks"))
        if start != cursor or not 0 < duration <= 5000 or end - start != duration:
            raise ValueError("Discontinuous or invalid observation clock")
        if _ticks(event["sim_ms"]) != end or _ticks(event.get("duration_ms")) != duration:
            raise ValueError("Observation clock mismatch")
        for field, tick in (("start_ms", start), ("end_ms", end)):
            if field in event and _ticks(event[field]) != tick:
                raise ValueError("Redundant observation clock mismatch")
        telemetry = event.get("telemetry")
        if type(telemetry) is not dict:
            raise ValueError("Missing observation telemetry")
        for record in (event, telemetry):
            if record.get("learning") is not False or "stimulation" not in record or record["stimulation"] is not None:
                raise ValueError("Reward-free records require learning=False and no external stimulation")
        if _ticks(telemetry.get("sim_ms")) != end or _ticks(telemetry.get("interval_ms")) != duration:
            raise ValueError("Telemetry clock mismatch")
        phase = event.get("stimulus")
        if type(phase) is not str or not phase:
            raise ValueError("Missing declared stimulus phase")
        native_bins = telemetry.get("bins")
        if type(native_bins) is not list or not native_bins:
            raise ValueError("Observation requires nonempty native bins")
        totals = dict.fromkeys(GROUPS, 0)
        bin_cursor = start
        for native_bin in native_bins:
            if type(native_bin) is not dict:
                raise ValueError("Invalid native bin")
            bin_end, bin_duration = _ticks(native_bin.get("end_ms")), _ticks(native_bin.get("duration_ms"))
            if not 0 < bin_duration <= 100 or bin_end - bin_duration != bin_cursor or bin_end > end:
                raise ValueError("Native bins require contiguous <=10 ms coverage")
            counts = native_bin.get("group_spikes")
            if type(counts) is not dict or set(counts) != set(GROUPS):
                raise ValueError("Native bin group keys differ")
            counts = {name: _integer(counts[name]) for name in GROUPS}
            for subset, superset in subset_pairs:
                if counts[subset] > counts[superset]:
                    raise ValueError("Native bin counts contradict group membership inclusion")
            for name in GROUPS:
                count = counts[name]
                rate = _number(count / (len(groups[name]) * bin_duration / 10000))
                summary = summaries[name]
                totals[name] += count
                summary["spikes"] += count
                summary["min_bin_rate_hz"] = min(summary["min_bin_rate_hz"], rate)
                summary["max_bin_rate_hz"] = max(summary["max_bin_rate_hz"], rate)
                summary["zero_bins" if count == 0 else "nonzero_bins"] += 1
            bin_cursor = bin_end
            bins += 1
        if bin_cursor != end:
            raise ValueError("Native bins do not cover the observation")
        rates = telemetry.get("rates_hz")
        if type(rates) is not dict or set(rates) != set(GROUPS):
            raise ValueError("Telemetry rate group keys differ")
        for name in GROUPS:
            expected = totals[name] / (len(groups[name]) * duration / 10000)
            if not math.isclose(_number(rates[name]), expected, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError(f"Population rate/count mismatch: {name}")
        compute.append(_number(telemetry.get("compute_seconds")))
        kernel.append(_number(telemetry.get("kernel_seconds")))
        duration_ticks += duration
        phase_ticks[phase] = phase_ticks.get(phase, 0) + duration
        observations += 1
        cursor = end
    if not duration_ticks or not finished:
        raise ValueError("Positive observed duration and final checkpoint required")
    seconds = duration_ticks / 10000
    for name, summary in summaries.items():
        summary["mean_rate_hz"] = _number(summary["spikes"] / (len(groups[name]) * seconds))
    try:
        compute_sum, kernel_sum = _number(math.fsum(compute)), _number(math.fsum(kernel))
    except OverflowError as error:
        raise ValueError("Recorded timing sum overflow") from error
    overlap = []
    for left, right in combinations(GROUPS, 2):
        shared = len(memberships[left] & memberships[right])
        if shared:
            overlap.append({"groups": [left, right], "shared_members": shared})
    return {
        "format": "fly-market-feasibility/v1", "verification_mode": run.verification_mode,
        "scope": "historical-population-inventory",
        "source": {**{name: manifest[name] for name in ("schema_sha256", "run_metadata_sha256",
                    "events_sha256", "final_scientific_sha256", "run_kind")},
                   "engine_identity": manifest["metadata"]["engine_identity"]},
        "observations": observations, "bins": bins, "simulated_ms": duration_ticks / 10,
        "phase_ms": {name: ticks / 10 for name, ticks in phase_ticks.items()},
        "groups": summaries, "membership_overlap": overlap,
        "timing": {"compute_seconds": compute_sum, "kernel_seconds": kernel_sum,
                   "compute_per_simulated_second": _number(compute_sum / seconds),
                   "kernel_per_simulated_second": _number(kernel_sum / seconds),
                   "scope": "recorded-historical-fields"},
        "limitations": LIMITATIONS[:],
    }


def analyze_recorded_run(run_directory: Path) -> dict[str, object]:
    """Validate exact bounded snapshot bytes through EOF before returning data."""
    with snapshot_recorded_run(run_directory, limits=READ_LIMITS,
                               checkpoint_byte_limit=MAX_CHECKPOINT_BYTES) as snapshot:
        run = artifacts.verify_run(snapshot, limits=READ_LIMITS)
        report = _summarize(run)
        json.dumps(report, allow_nan=False)
        return report


def write_report(report: dict[str, object], output_path: Path) -> None:
    write_json_exclusive(report, output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = analyze_recorded_run(args.run_dir)
        write_report(report, args.output)
    except (ValueError, OSError, TypeError, OverflowError) as error:
        parser.exit(1, f"Market inventory failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
