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
    return {
        "engine_identity": identity,
        "protocol_version": "qualification/v1",
        "stimulus_version": "associative-stimuli/v1",
        "family": "qualification",
        "seeds": list(QUALIFICATION_SEEDS),
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
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-run":
            summary = _verified_summary(verify_run(args.path))
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
