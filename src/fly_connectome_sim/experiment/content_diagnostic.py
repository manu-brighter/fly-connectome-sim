"""Bounded descriptive diagnostic; these files carry no replay attestation.

Two fixed feed prefixes branch into three probes each. The unchanged native
engine, decoder, checkpoint machinery and motor adapter own their actual work.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path
import time
from typing import Callable

import numpy as np

from ..engine import FlyEngine, _rgb_input_sha256
from ..neural.checkpoint import model_fingerprint
from .event_cards import load_proposal_with_source, render_event_cards
from .event_choice import ADAPTER, _new_output, _selected
from .recorder import DIGEST, RunArtifactError, _canonical, _strict_load
from .video_observation import _sha256_file, _telemetry_ticks, frame_tick, prepare_playlist


VERSION = "content-side-diagnostic/v1"
MOTORS = ("motor_left", "motor_right")
SOURCE_SHA256 = (
    "8cfa586a94b5e40ad00b197a57da348080bf4aa4490618ce9f5cf6778c0103fa",
    "b30f710936b4799eaf1c158f6cc83067f5d1c25ee8596ea9b663752d0f1d2401",
)
PROPOSAL_SHA256 = "ff6343b018b2043581acc915ed5699f85d3012185c061b510af78726962ff55c"


def _write_json(path: Path, value: dict) -> None:
    with path.open("xb") as stream:
        stream.write(_canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def _freeze(protocol_path: Path, freeze_path: Path) -> tuple[dict, dict, bytes]:
    frozen = _strict_load(freeze_path.read_bytes())
    protocol = protocol_path.read_bytes()
    fingerprint = model_fingerprint()
    actual = {
        "protocol_sha256": sha256(protocol).hexdigest(),
        "model_sha256": fingerprint["sha256"],
        "implementation_sha256": _sha256_file(Path(__file__)),
    }
    if frozen != actual:
        raise RunArtifactError("Protocol/model/implementation freeze drift")
    return actual, fingerprint, protocol


def _windows(bins: list[dict], *, start_tick: int, end_tick: int,
             populations: dict[str, int]) -> list[dict]:
    """Sum whole native bins; no gap, overlap or fractional count allocation."""
    if (start_tick % 5000 or end_tick <= start_tick or end_tick % 5000
            or set(populations) != set(MOTORS)
            or any(type(size) is not int or size < 1 for size in populations.values())):
        raise RunArtifactError("Invalid diagnostic window/populations")
    windows = []
    cursor = start_tick
    counts = dict.fromkeys(MOTORS, 0)
    window_end = start_tick + 5000
    for bin_ in bins:
        end = _telemetry_ticks(bin_["end_ms"])
        duration = _telemetry_ticks(bin_["duration_ms"])
        if not 0 < duration <= 100 or end != cursor + duration or end > window_end or end > end_tick:
            raise RunArtifactError("Noncontiguous or boundary-crossing native bin/window")
        for name in MOTORS:
            value = bin_["group_spikes"][name]
            if type(value) is not int or not 0 <= value <= duration * populations[name]:
                raise RunArtifactError("Invalid native bin integer motor count")
            counts[name] += value
        cursor = end
        if cursor == window_end:
            rates = {name: counts[name] / (populations[name] * 0.5) for name in MOTORS}
            windows.append({
                "start_tick": window_end - 5000, "end_tick": window_end,
                "counts": counts, "rates_hz": rates,
                "decision": asdict(ADAPTER.adapt({"rates_hz": rates})),
            })
            window_end += 5000
            counts = dict.fromkeys(MOTORS, 0)
    if cursor != end_tick or len(windows) != (end_tick - start_tick) // 5000:
        raise RunArtifactError("Incomplete native bins/windows")
    return windows


def _contrast(first: list[dict], second: list[dict]) -> dict:
    if len(first) != len(second):
        raise RunArtifactError("Unmatched comparison windows")
    windows = []
    for a, b in zip(first, second, strict=True):
        if (a["start_tick"], a["end_tick"]) != (b["start_tick"], b["end_tick"]):
            raise RunArtifactError("Unmatched comparison clocks")
        windows.append({
            "start_tick": a["start_tick"], "end_tick": a["end_tick"],
            "count_difference": {name: a["counts"][name] - b["counts"][name] for name in MOTORS},
            "rate_difference_hz": {name: a["rates_hz"][name] - b["rates_hz"][name] for name in MOTORS},
            "first_action": a["decision"]["action"], "second_action": b["decision"]["action"],
        })
    return {"subtraction": "first-minus-second", "windows": windows, "final": windows[-1]}


def run_content_diagnostic(
    output_dir: str | Path, *, playlist_path: str | Path, proposal_path: str | Path,
    protocol_path: str | Path, freeze_path: str | Path,
    engine_factory: Callable[[], FlyEngine], expected_source_sha256: tuple[str, str],
    expected_proposal_sha256: str,
) -> dict:
    """Execute exactly the declared 28s branching diagnostic, preserving partials.

    Expected input hashes are caller declarations; only the module CLI pins the
    original two reels. A summary exists exclusively after successful completion.
    External supervision owns wall/RSS/output limits, including native calls.
    """
    started = time.perf_counter()
    target = Path(output_dir)
    _new_output(None, target)
    if (len(expected_source_sha256) != 2
            or any(type(value) is not str or not DIGEST.fullmatch(value)
                   for value in (*expected_source_sha256, expected_proposal_sha256))):
        raise RunArtifactError("Diagnostic requires two source hashes and one proposal hash")
    protocol_path, freeze_path = Path(protocol_path), Path(freeze_path)
    frozen, fingerprint, protocol = _freeze(protocol_path, freeze_path)
    proposal, source = load_proposal_with_source(proposal_path)
    if source["raw_sha256"] != expected_proposal_sha256:
        raise RunArtifactError("Proposal input drift")
    clips = prepare_playlist(playlist_path, profile="fast-feed")
    if len(clips) != 2 or tuple(clip.metadata["source_sha256"] for clip in clips) != tuple(expected_source_sha256):
        raise RunArtifactError("Ordered source input drift")
    swapped = deepcopy(proposal)
    swapped["options"].reverse()
    frames = {"normal": render_event_cards(proposal), "swapped": render_event_cards(swapped),
              "black": np.zeros((216, 384, 3), dtype=np.uint8)}
    black_feed = np.zeros((160, 90, 3), dtype=np.uint8)
    frame_hashes = {name: _rgb_input_sha256(frame) for name, frame in frames.items()}
    black_feed_hash = _rgb_input_sha256(black_feed)
    # Recheck frozen source after decoding/rendering, before the sole engine.
    _freeze(protocol_path, freeze_path)
    engine = engine_factory()
    if (not isinstance(engine, FlyEngine) or engine.brain.cursor != 0 or engine.brain.sim_ms != 0
            or engine.brain.dt != 0.1 or engine.brain.weights_frozen):
        raise RunArtifactError("Diagnostic requires one fresh unfrozen 0.1ms native engine")
    identity = engine.identity()
    if identity["model_provenance"]["model_fingerprint"] != fingerprint:
        raise RunArtifactError("Engine source identity differs from frozen packaged source")
    populations = {name: len(identity["neural_groups"][name]) for name in MOTORS}
    if any(size < 1 for size in populations.values()):
        raise RunArtifactError("Diagnostic requires both motor populations")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir(exist_ok=False)
    (target / "checkpoints").mkdir()
    _write_json(target / "manifest.json", {
        "version": VERSION, "artifact_kind": "plain-descriptive-diagnostic",
        "verification": "no-native-replay-attestation", "freeze": frozen,
        "protocol_utf8": protocol.decode("utf-8"), "model_fingerprint": fingerprint,
        "engine_identity": identity, "populations": populations,
        "expected_source_sha256": list(expected_source_sha256),
        "expected_proposal_sha256": expected_proposal_sha256,
        "clips": [clip.metadata for clip in clips], "proposal": proposal,
        "proposal_source": source, "swapped_proposal": swapped,
        "probe_inputs": {name: {"sha256": frame_hashes[name], "shape": list(frame.shape),
                                "dtype": frame.dtype.name} for name, frame in frames.items()},
        "black_feed_input": {"sha256": black_feed_hash, "shape": list(black_feed.shape), "dtype": "uint8"},
        "schedule": {"feed_ticks": 80000, "probe_ticks": 20000, "observe_calls": 504,
                     "total_advanced_ticks": 280000, "adapter": asdict(ADAPTER)},
    })
    sequence = 0
    observe_calls = 0
    advanced_ticks = 0
    feeds, probes = {}, {}
    with (target / "events.jsonl").open("xb") as stream:
        def append(event: dict) -> None:
            nonlocal sequence
            stream.write(_canonical({**event, "sequence": sequence,
                                     "elapsed_seconds": time.perf_counter() - started}) + b"\n")
            stream.flush()
            sequence += 1

        def state() -> dict:
            return {"sim_tick": engine.brain.cursor,
                    "complete_state_sha256": engine.brain.checkpoint_state_sha256(),
                    "weights_frozen": engine.brain.weights_frozen}

        def save(name: str) -> dict:
            current = state()
            path = target / "checkpoints" / f"{name}.npz"
            engine.brain.checkpoint(path)
            checkpoint = {**current, "path": f"checkpoints/{name}.npz",
                          "sha256": _sha256_file(path), "size_bytes": path.stat().st_size}
            append({"type": "checkpoint", "checkpoint": name, **checkpoint})
            return checkpoint

        def restore(name: str, expected: dict, *, history: str, phase: str) -> None:
            path = target / expected["path"]
            if _sha256_file(path) != expected["sha256"]:
                raise RunArtifactError("Checkpoint file drift before restore")
            engine.brain.restore(path)
            current = state()
            if any(current[key] != expected[key] for key in current):
                raise RunArtifactError("Complete native state mismatch after restore")
            append({"type": "restore", "checkpoint": name, "history": history, "phase": phase, **current})

        def observe(frame: np.ndarray, duration: int, *, history: str, phase: str,
                    input_hash: str, source_frame: dict | None = None) -> list[dict]:
            nonlocal observe_calls, advanced_ticks
            start = engine.brain.cursor
            telemetry = engine.observe(frame, duration / 10, stimulation=None, learning=False,
                                       pathway_detail=False, qualification_detail=False)
            end = engine.brain.cursor
            if (end != start + duration or _telemetry_ticks(telemetry["sim_ms"]) != end
                    or _telemetry_ticks(telemetry["interval_ms"]) != duration
                    or telemetry["input_sha256"] != input_hash
                    or telemetry["engine_identity"] != identity
                    or telemetry["learning"] is not False or telemetry["stimulation"] is not None
                    or engine.brain.weights_frozen):
                raise RunArtifactError("Actual observation differs from fixed input/clock/flags")
            append({"type": "observe", "history": history, "phase": phase,
                    "start_tick": start, "end_tick": end, "source_frame": source_frame,
                    "telemetry": telemetry})
            observe_calls += 1
            advanced_ticks += duration
            return telemetry["bins"]

        start_checkpoint = save("start")
        for history in ("real", "black"):
            restore("start", start_checkpoint, history=history, phase="feed")
            bins = []
            for clip_index, clip in enumerate(clips):
                for index, prepared in enumerate(clip.frames):
                    expected_start = clip_index * 40000 + frame_tick(index)
                    if engine.brain.cursor != expected_start:
                        raise RunArtifactError("Noncontinuous fixed feed clock")
                    bins.extend(observe(
                        prepared.rgb if history == "real" else black_feed,
                        frame_tick(index + 1) - frame_tick(index), history=history, phase="feed",
                        input_hash=prepared.sha256 if history == "real" else black_feed_hash,
                        source_frame={"clip_id": clip.metadata["clip_id"], "frame_id": prepared.frame_id,
                                      "source_pts": prepared.source_pts,
                                      "source_time_base": prepared.source_time_base},
                    ))
            feeds[history] = _windows(bins, start_tick=0, end_tick=80000, populations=populations)
            feed_checkpoint = save(f"{history}-feed-end")
            probes[history] = {}
            for probe in ("normal", "swapped", "black"):
                restore(f"{history}-feed-end", feed_checkpoint, history=history, phase=probe)
                bins = []
                for index in range(4):
                    if engine.brain.cursor != 80000 + index * 5000:
                        raise RunArtifactError("Noncontinuous fixed probe clock")
                    bins.extend(observe(frames[probe], 5000, history=history, phase=probe,
                                        input_hash=frame_hashes[probe]))
                windows = _windows(bins, start_tick=80000, end_tick=100000, populations=populations)
                selected = None if probe == "black" else _selected(
                    windows[-1]["decision"], proposal if probe == "normal" else swapped,
                )
                terminal = state()
                append({"type": "probe_end", "history": history, "phase": probe,
                        **terminal, "selected_option_id": selected})
                probes[history][probe] = {"windows": windows, "selected_option_id": selected,
                                          "terminal_state": terminal}
        stream.flush()
        os.fsync(stream.fileno())
    if (observe_calls, advanced_ticks) != (504, 280000):
        raise RunArtifactError("Incomplete bounded diagnostic schedule")
    _freeze(protocol_path, freeze_path)
    comparisons = {"real-minus-black-feed": _contrast(feeds["real"], feeds["black"])}
    for probe in ("normal", "swapped", "black"):
        comparisons[f"real-minus-black-history/{probe}"] = _contrast(
            probes["real"][probe]["windows"], probes["black"][probe]["windows"],
        )
    for history in ("real", "black"):
        for first, second in (("normal", "black"), ("swapped", "black"), ("normal", "swapped")):
            comparisons[f"{history}/{first}-minus-{second}"] = _contrast(
                probes[history][first]["windows"], probes[history][second]["windows"],
            )
    result = {"version": VERSION, "status": "complete", "observe_calls": observe_calls,
              "advanced_ticks": advanced_ticks, "elapsed_seconds": time.perf_counter() - started,
              "feeds": feeds, "probes": probes, "comparisons": comparisons,
              "events_sha256": _sha256_file(target / "events.jsonl"),
              "manifest_sha256": _sha256_file(target / "manifest.json")}
    _write_json(target / "summary.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("playlist", "proposal", "protocol", "freeze-manifest", "output-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    result = run_content_diagnostic(
        args.output_dir, playlist_path=args.playlist, proposal_path=args.proposal,
        protocol_path=args.protocol, freeze_path=args.freeze_manifest,
        engine_factory=FlyEngine.from_prepared_graph, expected_source_sha256=SOURCE_SHA256,
        expected_proposal_sha256=PROPOSAL_SHA256,
    )
    print(f"Completed {result['observe_calls']} observations; plain diagnostic: {args.output_dir}")


if __name__ == "__main__":
    main()
