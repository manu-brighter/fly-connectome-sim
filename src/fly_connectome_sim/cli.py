"""Commands for producing and verifying sealed experiment evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np

from .engine import FlyEngine, _rgb_input_sha256
from .experiment.qualification import (
    CONFIRMATION_SEEDS,
    CURRENT_MV,
    GRID,
    PULSE_DURATION_MS,
    QUALIFICATION_SEEDS,
    RESPONSE_WINDOWS,
    RETENTION_CANDIDATES_MS,
    UNPAIRED_SEPARATION_MS,
    qualify,
)
from .experiment.recorder import RunRecorder, verify_run
from .experiment.measured_replay import export_measured_replay, record_observation_run
from .experiment.video_observation import export_video_replay, record_video_observation_run
from .experiment.event_choice import export_event_plan, export_event_replay, record_event_choice_run
from .experiment.stimuli import AssayStimuli


def _qualification_metadata(identity: dict) -> dict:
    inputs = {}
    all_hashes = set()
    for seed in QUALIFICATION_SEEDS:
        stimuli = AssayStimuli(seed=seed, family="qualification")
        frames = {name: _rgb_input_sha256(stimuli.frame(name)) for name in ("A", "B", "C")}
        inputs[str(seed)] = frames
        all_hashes.update(frames.values())
    black = _rgb_input_sha256(np.zeros((32, 32, 3), dtype=np.uint8))
    all_hashes.add(black)
    confirmation_inputs = {
        str(seed): {**{name: _rgb_input_sha256(AssayStimuli(seed, "confirmation").frame(name))
                      for name in ("A", "B", "C")}, "black": black}
        for seed in CONFIRMATION_SEEDS
    }
    from .experiment.analysis import AGGREGATION, QUALIFICATION_VERSION

    return {
        "engine_identity": identity,
        "protocol_version": "qualification/v1",
        "stimulus_version": "associative-stimuli/v1",
        "family": "qualification",
        "seeds": list(QUALIFICATION_SEEDS),
        "qualification_version": QUALIFICATION_VERSION,
        "aggregation": AGGREGATION,
        "exclusions": [],
        "mbon11_population_size": len(identity["neural_groups"]["mbon11"]),
        "candidate_identity": "kc-mbon11-ppl101/v1",
        "confirmation_input_sha256": confirmation_inputs,
        "configuration": {
            "pulse_duration_ms": PULSE_DURATION_MS,
            "external_dan_current_mv": CURRENT_MV,
            "unpaired_minimum_separation_ms": UNPAIRED_SEPARATION_MS,
        },
        "factors": {
            "grid": [asdict(item) for item in GRID],
            "response_windows": [asdict(item) for item in RESPONSE_WINDOWS],
            "retention_ms": list(RETENTION_CANDIDATES_MS),
            "paired_identity": ["A", "B"],
            "presentation_order": ["AB", "BA"],
            "side": "center",
            "color_assignment": "fixed",
        },
        "rgb_input_sha256": {"stimuli": inputs, "black": black},
        "black_input": {"generator": "black-rgb/v1", "input_dtype": "uint8",
                        "input_shape": [32, 32, 3], "input_sha256": black},
        "input_sha256": sorted(all_hashes),
    }


def _verified_summary(run) -> dict:
    manifest = run.manifest
    return {
        "path": str(run.path),
        "run_kind": manifest["run_kind"],
        "family": manifest["metadata"]["family"],
        "event_count": manifest["event_count"],
        "final_scientific_sha256": manifest["final_scientific_sha256"],
        "events_sha256": manifest["events_sha256"],
        "run_metadata_sha256": manifest["run_metadata_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fly-connectome-sim")
    commands = parser.add_subparsers(dest="command", required=True)
    qualify_parser = commands.add_parser("qualify")
    qualify_parser.add_argument("--output-dir", type=Path, required=True)
    verify_parser = commands.add_parser("verify-run")
    verify_parser.add_argument("path", type=Path)
    observe_parser = commands.add_parser("observe")
    observe_parser.add_argument("--output-dir", type=Path, default=Path("runs/measured-observation"))
    observe_parser.add_argument("--seed", type=int, default=11)
    observe_parser.add_argument("--cycles", type=int, default=3)
    export_parser = commands.add_parser("export-replay")
    export_parser.add_argument("path", type=Path)
    export_parser.add_argument("--output", type=Path, default=Path("runs/measured-replay.json"))
    video_parser = commands.add_parser("observe-video")
    video_parser.add_argument("--playlist", type=Path, required=True)
    video_parser.add_argument("--profile", choices=("standard", "fast-feed"), default="standard")
    video_parser.add_argument("--output-dir", type=Path, default=Path("runs/video-observation"))
    video_export_parser = commands.add_parser("export-video-replay")
    video_export_parser.add_argument("path", type=Path)
    video_export_parser.add_argument("--output", type=Path,
                                     default=Path("runs/measured-video-replay.json"))
    event_parser = commands.add_parser("event-choice")
    event_parser.add_argument("--proposal", type=Path, required=True)
    event_parser.add_argument("--output-dir", type=Path, required=True)
    for command in ("export-event-replay", "export-event-plan"):
        event_export_parser = commands.add_parser(command)
        event_export_parser.add_argument("path", type=Path)
        event_export_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-run":
            summary = _verified_summary(verify_run(args.path))
        elif args.command == "observe":
            summary = _verified_summary(record_observation_run(
                args.output_dir, engine_factory=FlyEngine.from_prepared_graph,
                seed=args.seed, cycles=args.cycles,
            ))
        elif args.command == "export-replay":
            replay = export_measured_replay(args.path, args.output)
            summary = {"path": str(args.output), "version": replay["version"],
                       "duration_ticks": replay["duration_ticks"],
                       "segment_count": len(replay["segments"]),
                       "verification_mode": replay["source"]["verification_mode"]}
        elif args.command == "observe-video":
            summary = _verified_summary(record_video_observation_run(
                args.output_dir, playlist_path=args.playlist, profile=args.profile,
                engine_factory=FlyEngine.from_prepared_graph,
            ))
        elif args.command == "export-video-replay":
            replay = export_video_replay(args.path, args.output)
            summary = {"path": str(args.output), "version": replay["version"],
                       "duration_ticks": replay["duration_ticks"],
                       "segment_count": len(replay["segments"]),
                       "verification_mode": replay["source"]["verification_mode"]}
        elif args.command == "event-choice":
            summary = _verified_summary(record_event_choice_run(
                args.output_dir, proposal_path=args.proposal,
                engine_factory=FlyEngine.from_prepared_graph,
            ))
        elif args.command in {"export-event-replay", "export-event-plan"}:
            exporter = export_event_plan if args.command == "export-event-plan" else export_event_replay
            result = exporter(args.path, args.output)
            summary = {"path": str(args.output), "version": result["version"],
                       "verification_mode": result["source"]["verification_mode"]}
            if args.command == "export-event-plan":
                summary.update(status=result["status"], selected_option_id=result["selected_option_id"])
            else:
                summary.update(duration_ticks=result["duration_ticks"], segment_count=len(result["segments"]))
        else:
            if args.output_dir.exists() or args.output_dir.is_symlink() \
                    or args.output_dir.is_junction():
                raise FileExistsError(f"Output path already exists: {args.output_dir}")
            engine = FlyEngine.from_prepared_graph()
            with RunRecorder(
                args.output_dir,
                run_kind="qualification",
                metadata=_qualification_metadata(engine.identity()),
                root_branch_id="qualification/baseline",
            ) as recorder:
                result = qualify(lambda: engine, recorder,
                                 seeds=QUALIFICATION_SEEDS, family="qualification")
            summary = _verified_summary(verify_run(args.output_dir))
            summary.update(status=result.status, benchmark=result.benchmark)
        print(json.dumps(summary, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as error:
        print(f"fly-connectome-sim: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
