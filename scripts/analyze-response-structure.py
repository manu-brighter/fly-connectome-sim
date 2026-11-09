"""Bounded historical response composition and population scaling, integrity only."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from fractions import Fraction
import importlib.util
from itertools import combinations
from pathlib import Path

from fly_connectome_sim.experiment import recorder as artifacts
from market_artifacts import _safe_directory, snapshot_recorded_run, write_json_exclusive


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "response_structure_frozen_diagnostic", ROOT / "scripts/run-market-response-diagnostic.py",
)
DIAGNOSTIC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DIAGNOSTIC)
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_COUNT = 9007199254740991
RELATIONS = ("proportional", "nonproportional", "both-silent", "one-silent")


def _count(value) -> int:
    if type(value) is not int or not 0 <= value <= MAX_COUNT:
        raise ValueError("Expected a nonnegative JSON-safe integer count")
    return value


def _fraction(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def compare_vectors(left, right, *, composition: bool) -> dict:
    """Compare exact component proportions, with undefined normalized silence."""
    if (type(left) not in (list, tuple) or type(right) not in (list, tuple)
            or not left or len(left) != len(right) or type(composition) is not bool):
        raise ValueError("Expected equally sized nonempty count vectors and boolean mode")
    left, right = [_count(value) for value in left], [_count(value) for value in right]
    x, y = sum(left), sum(right)
    tv = None
    if not x or not y:
        relation = "both-silent" if not x and not y else "one-silent"
    else:
        differences = [abs(a * y - b * x) for a, b in zip(left, right)]
        relation = "nonproportional" if any(differences) else "proportional"
        if composition:
            tv = Fraction(sum(differences), 2 * x * y)
    result = {"relation": relation, "left_component_sum": str(x), "right_component_sum": str(y)}
    if composition:
        result.update(tv=None if tv is None else _fraction(tv),
                      tv_decimal=None if tv is None else float(tv))
    return result


def _partition(header: dict, grouping: dict) -> dict:
    """Group entries are cohort slots, never neural model indices."""
    cells = header["cells"]
    groups, excluded = grouping["groups"], grouping["excluded_kc_slots"]
    if (len(cells) != 256 or type(groups) is not list or len(groups) != 20
            or type(excluded) is not list or len(excluded) != 11):
        raise ValueError("Expected 256 cohort cells, twenty groups and eleven excluded KCs")
    kc_slots = {slot for slot, cell in enumerate(cells) if "kc" in cell["groups"]}
    buckets, coverage = [], []
    for index, slots in enumerate([*groups, excluded]):
        if type(slots) is not list or len(slots) != 11:
            raise ValueError("Each of the 21 KC buckets requires eleven slots")
        if any(type(slot) is not int or slot not in kc_slots for slot in slots):
            raise ValueError("Invalid KC cohort slot")
        coverage.extend(slots)
        buckets.append({"id": f"kc-group-{index:02d}" if index < 20 else "excluded-sampled-kc",
                        "slots": slots[:], "model_indices": [cells[slot]["model_index"] for slot in slots]})
    if len(kc_slots) != 231 or len(set(coverage)) != 231 or set(coverage) != kc_slots:
        raise ValueError("KC buckets must cover all 231 sampled KCs exactly once")
    return {**grouping, "buckets": buckets}


class _InspectionView:
    """Borrow one owned snapshot iterator so inspector errors cannot retain it open.

    The frozen inspector only reads these three VerifiedRun interfaces. The
    original verified run remains the sole source for both complete scans.
    """

    def __init__(self, run, events):
        self.manifest = run.manifest
        self.verification_mode = run.verification_mode
        self.events = events

    def iter_events(self):
        return self.events


def _vectors(run, summary: dict, partition: dict) -> list[dict]:
    header = run.manifest["metadata"]["diagnostic"]["header"]
    populations = header["engine_identity"]["neural_groups"]
    arms = [arm for arm, _ in DIAGNOSTIC.ARMS]
    rows, seen = [], set()
    kc_slots = [slot for slot, cell in enumerate(header["cells"]) if "kc" in cell["groups"]]
    with closing(run.iter_events()) as events:
        for event in events:
            if event["type"] != "observe" or event["branch_id"] == "prefix":
                continue
            arm = event["branch_id"]
            start = event["start_tick"]
            window = (start - 20000) // 5000
            if arm not in arms or window not in range(8) or start != 20000 + window * 5000:
                raise ValueError("Unexpected arm/window in validated snapshot")
            key = (arm, window)
            if key in seen:
                raise ValueError("Duplicate arm/window")
            seen.add(key)
            ordinal = 4 + arms.index(arm) * 8 + window
            totals = [0] * len(header["cells"])
            for cell_bin in event["cell_bins"]:
                if cell_bin["observation_index"] != ordinal:
                    raise ValueError("Observer ordinal differs")
                for slot, count in enumerate(cell_bin["counts"]):
                    totals[slot] += _count(count)
            counts = [sum(totals[slot] for slot in bucket["slots"]) for bucket in partition["buckets"]]
            component_sum = sum(counts)
            if (counts[:20] != summary["secondary"][window]["arms"][arm]["group_counts"]
                    or component_sum != sum(totals[slot] for slot in kc_slots)):
                raise ValueError("KC vectors contradict inspector or direct sampled-KC sum")
            shares = None if component_sum == 0 else [_fraction(Fraction(count, component_sum)) for count in counts]
            population_counts = [sum(_count(row["group_spikes"][name]) for row in event["telemetry"]["bins"])
                                 for name in DIAGNOSTIC.GROUPS]
            rates = [_fraction(Fraction(2 * count, len(populations[name])))
                     for name, count in zip(DIAGNOSTIC.GROUPS, population_counts)]
            rows.append({"arm": arm, "frame": dict(DIAGNOSTIC.ARMS)[arm], "window_index": window,
                         "primary": window == 7, "observation_index": ordinal,
                         "model_start_ms": start // 10, "model_end_ms": (start + 5000) // 10,
                         "duration_ms": 500,
                         "kc": {"counts": counts, "component_sum": str(component_sum),
                                "shares": shares, "excluded_share": None if shares is None else shares[-1]},
                         "population": {"counts": population_counts,
                                        "algebraic_component_sum": str(sum(population_counts)), "rates_hz": rates}})
    if seen != {(arm, window) for arm in arms for window in range(8)}:
        raise ValueError("Expected exactly all 64 arm/windows")
    return rows


def analyze_diagnostic(output_dir: Path, *, expected_protocol_sha256: str,
                       expected_manifest_sha256: str, expected_events_sha256: str) -> dict:
    """Validate every original event before calculating from that private snapshot."""
    for expected in (expected_protocol_sha256, expected_manifest_sha256, expected_events_sha256):
        DIAGNOSTIC._hash(expected)
    output = Path(output_dir).absolute()
    protocol, protocol_hash = DIAGNOSTIC._read_protocol(output, expected_protocol_sha256)
    with snapshot_recorded_run(output / "run", limits=DIAGNOSTIC.READ_LIMITS,
                               checkpoint_byte_limit=DIAGNOSTIC.MAX_CHECKPOINT_BYTES) as snapshot:
        manifest_hash = artifacts._digest_file(snapshot / "run.json",
                                               max_bytes=DIAGNOSTIC.READ_LIMITS.max_manifest_bytes)[0]
        events_hash = artifacts._digest_file(snapshot / "events.jsonl",
                                             max_bytes=DIAGNOSTIC.READ_LIMITS.max_events_bytes)[0]
        if manifest_hash != expected_manifest_sha256 or events_hash != expected_events_sha256:
            raise ValueError("Caller-pinned manifest/events bytes differ")
        run = artifacts.verify_run(snapshot, limits=DIAGNOSTIC.READ_LIMITS)
        with closing(run.iter_events()) as events:
            summary = DIAGNOSTIC._summarize(_InspectionView(run, events), protocol, protocol_hash)
        declaration = run.manifest["metadata"]["diagnostic"]
        header = declaration["header"]
        partition = _partition(header, summary["grouping"])
        rows = _vectors(run, summary, partition)
        indexed = {(row["arm"], row["window_index"]): row for row in rows}
        comparisons = []
        for window in range(8):
            for (left, _), (right, _) in combinations(DIAGNOSTIC.ARMS, 2):
                a, b = indexed[left, window], indexed[right, window]
                comparisons.append({"left_arm": left, "right_arm": right, "window_index": window,
                                    "primary": window == 7, "repeat_check": (left, right) in DIAGNOSTIC.REPEATS,
                                    "kc": compare_vectors(a["kc"]["counts"], b["kc"]["counts"], composition=True),
                                    "population": compare_vectors(a["population"]["counts"], b["population"]["counts"],
                                                                  composition=False)})
        populations = header["engine_identity"]["neural_groups"]
        overlap = [{"groups": [left, right], "shared_members": len(set(populations[left]) & set(populations[right]))}
                   for left, right in combinations(DIAGNOSTIC.GROUPS, 2)
                   if set(populations[left]) & set(populations[right])]
        source_paths = [Path(__file__).resolve(), Path(DIAGNOSTIC.__file__).resolve(),
                        ROOT / "scripts/market_artifacts.py", ROOT / "src/fly_connectome_sim/experiment/recorder.py"]
        relation_counts = {kind: dict.fromkeys(RELATIONS, 0) for kind in ("kc", "population")}
        for kind in relation_counts:
            relation_counts[kind].update(Counter(pair[kind]["relation"] for pair in comparisons))
        return {
            "version": "market-response-structure/v1", "scope": "historical-development-response-inventory",
            "verification_mode": run.verification_mode,
            "implementation": {"files_sha256": {path.relative_to(ROOT).as_posix(): artifacts._digest_file(path)[0]
                                                  for path in source_paths}},
            "source": {"protocol_sha256": protocol_hash, "manifest_sha256": manifest_hash, "events_sha256": events_hash,
                       "validated_source": summary["source"], "protocol_source": protocol["source"],
                       "header_sha256": declaration["header_sha256"], "grouping_sha256": declaration["grouping_sha256"]},
            "cohort": header, "kc_partition": partition,
            "population_declarations": [{"id": name, "members": populations[name], "size": len(populations[name])}
                                        for name in DIAGNOSTIC.GROUPS],
            "membership_overlap": overlap, "vectors": rows, "comparisons": comparisons,
            "repeat_validation": summary["repeats"],
            "summary": {"vectors": len(rows), "comparisons": len(comparisons),
                        "primary_comparisons": sum(pair["primary"] for pair in comparisons),
                        "repeat_checks": sum(pair["repeat_check"] for pair in comparisons),
                        "kc_relations": relation_counts["kc"], "population_relations": relation_counts["population"]},
            "limitations": ["Descriptive development evidence; no significance or usefulness threshold.",
                            "Only the 231 sampled KCs are partitioned, not the full model KC population.",
                            "Overlapping population component sums are algebraic, not distinct-cell totals.",
                            "Windows and deterministic repeats are not independent biological replicates.",
                            "The primary window is part of the complete secondary course.",
                            "No decoder, price mapping, semantic understanding or biological learning claim.",
                            "Artifact integrity is not native replay attestation."],
        }


def write_report(report: dict, output_path: Path) -> None:
    output = Path(output_path).absolute()
    _safe_directory(output.parent)
    if len(artifacts._canonical(report) + b"\n") > MAX_REPORT_BYTES:
        raise ValueError("Response-structure report exceeds 4 MiB")
    write_json_exclusive(report, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic-dir", required=True, type=Path)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-events-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = analyze_diagnostic(args.diagnostic_dir, expected_protocol_sha256=args.expected_protocol_sha256,
                                    expected_manifest_sha256=args.expected_manifest_sha256,
                                    expected_events_sha256=args.expected_events_sha256)
        write_report(report, args.output)
    except (ValueError, OSError, TypeError, OverflowError, RuntimeError, KeyError, AttributeError) as error:
        parser.exit(1, f"Response inventory failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
