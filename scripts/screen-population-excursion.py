"""Screen fixed necessary population excursions from a pinned, bounded probe offline."""

from __future__ import annotations

import argparse
from contextlib import closing
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

from fly_connectome_sim.experiment import recorder as artifacts
from market_artifacts import _safe_directory, snapshot_recorded_run, write_json_exclusive
from market_population_state import GROUPS, screen


ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("population_screen_frozen_probe", ROOT / "scripts/run-continuous-motor-probe.py")
PROBE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(PROBE)
MAX_REPORT_BYTES = 4 * 1024**2
LIMITATIONS = [
    "Development prerequisite screen only; calibration is not independent acceptance evidence.",
    "A necessary opportunity is not a proposal, scientific pass, or authorization for Stage C or another acquisition.",
    "Integrity only; no native replay attestation or scientific support.",
    "Recorded monotonic clocks are preserved but not independently authenticated.",
    "The selected engineering contrasts do not establish biological opposition, semantics, preference, or learning.",
    "No twenty-slot neural coverage, price support, pending expiry, later anchors, freshness, or continuous operation validated.",
    "A negative screen applies only to this fixed candidate and development trace, not all possible sector grids.",
]


def analyze_probe(output_dir: Path, *, expected_protocol_sha256: str,
                  expected_manifest_sha256: str, expected_events_sha256: str) -> dict:
    """Validate v1 completely, then derive from the same private snapshot through EOF."""
    pins = {"protocol_sha256": expected_protocol_sha256, "manifest_sha256": expected_manifest_sha256,
            "events_sha256": expected_events_sha256}
    for pin in pins.values():
        PROBE._hash(pin)
    output = Path(output_dir).absolute()
    protocol, protocol_hash = PROBE._read_protocol(output, expected_protocol_sha256)
    if tuple(PROBE.GROUPS) != GROUPS:
        raise ValueError("Frozen population order differs")
    with snapshot_recorded_run(output / "run", limits=PROBE.READ_LIMITS,
                               checkpoint_byte_limit=PROBE.MAX_CHECKPOINT_BYTES) as snapshot:
        # Pins are checked against precisely the snapshot bytes used by both scans.
        if sha256((snapshot / "run.json").read_bytes()).hexdigest() != expected_manifest_sha256:
            raise ValueError("Original manifest pin differs")
        run = artifacts.verify_run(snapshot, limits=PROBE.READ_LIMITS)
        manifest = run.manifest
        if manifest["events_sha256"] != expected_events_sha256:
            raise ValueError("Original events pin differs")
        with closing(run.iter_events()) as events:
            original_summary = PROBE._summarize_events(run, protocol, protocol_hash, events)
        count_vectors, provenance = [], []
        with closing(run.iter_events()) as events:
            for event in events:
                if event["type"] != "observe":
                    continue
                count_vectors.append([sum(native["group_spikes"][name] for native in event["telemetry"]["bins"])
                                      for name in PROBE.GROUPS])
                provenance.append({key: value for key, value in event.items() if key != "telemetry"})
        result = screen(count_vectors, manifest["metadata"]["engine_identity"]["neural_groups"])
        for observation, original in zip(result["observations"], provenance, strict=True):
            observation["provenance"] = original
        source_paths = [Path(__file__).resolve(), ROOT / "scripts/market_population_state.py",
                        ROOT / "scripts/market_artifacts.py", ROOT / "scripts/run-continuous-motor-probe.py",
                        ROOT / "scripts/market_motor_readout.py", ROOT / "src/fly_connectome_sim/experiment/recorder.py"]
        result.update({
            "version": "market-population-excursion-screen/v1", "scope": "development-prerequisite-screen",
            "verification_mode": run.verification_mode, "pins": pins,
            "source": {"analyzer_files_sha256": {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
                                                for path in source_paths},
                       "original_protocol": protocol["source"],
                       "original_engine_identity": manifest["metadata"]["engine_identity"],
                       "original_run": {name: manifest[name] for name in
                                        ("schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256")}},
            "exact_counts": PROBE.EXACT_COUNTS.copy(), "original_v1_summary": original_summary,
            "limitations": LIMITATIONS.copy(),
        })
        return result


def write_report(report: dict, output_path: Path) -> None:
    """Publish at most 4 MiB including the terminal newline, exclusively."""
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8") + b"\n"
    if len(encoded) > MAX_REPORT_BYTES:
        raise ValueError("Report exceeds 4 MiB newline-inclusive limit")
    output = Path(output_path).absolute()
    _safe_directory(output.parent)
    if output.is_symlink() or output.is_junction():
        raise ValueError("Unsafe output file")
    write_json_exclusive(report, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-dir", required=True, type=Path)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-events-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = analyze_probe(args.probe_dir, expected_protocol_sha256=args.expected_protocol_sha256,
                               expected_manifest_sha256=args.expected_manifest_sha256,
                               expected_events_sha256=args.expected_events_sha256)
        write_report(report, args.output)
    except (ValueError, OSError, TypeError, OverflowError, RuntimeError, KeyError, AttributeError, ImportError) as error:
        parser.exit(1, f"Population excursion screen failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
