"""Exact offline arithmetic and faithful synthetic recordings; no native model."""

from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.neural.checkpoint import model_fingerprint


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/analyze-response-structure.py"
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")


def load(path, name):
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyzer():
    assert SCRIPT.is_file(), "The bounded response-structure analyzer is missing"
    return load(SCRIPT, "response_structure")


@pytest.fixture(autouse=True)
def forbid_native_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline inventory attempted native construction/replay or network")
    from fly_connectome_sim.engine import FlyEngine
    monkeypatch.setattr(FlyEngine, "__init__", forbidden)
    monkeypatch.setattr(FlyEngine, "from_prepared_graph", forbidden)
    monkeypatch.setattr(artifacts, "verify_replay_run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.mark.parametrize("left,right,relation,tv", [
    ([1, 2], [2, 4], "proportional", {"numerator": "0", "denominator": "1"}),
    ([3, 1], [1, 3], "nonproportional", {"numerator": "1", "denominator": "2"}),
    ([1, 0], [0, 1], "nonproportional", {"numerator": "1", "denominator": "1"}),
    ([0, 0], [0, 0], "both-silent", None),
    ([0, 0], [1, 0], "one-silent", None),
    ([1, 0], [0, 0], "one-silent", None),
])
def test_exact_comparison_symmetry_silence_and_reduced_fractions(left, right, relation, tv):
    module = analyzer()
    result = module.compare_vectors(left, right, composition=True)
    reverse = module.compare_vectors(right, left, composition=True)
    assert result == {"relation": relation, "left_component_sum": str(sum(left)),
                      "right_component_sum": str(sum(right)), "tv": tv,
                      "tv_decimal": None if tv is None else int(tv["numerator"]) / int(tv["denominator"])}
    assert reverse["tv"] == tv and reverse["relation"] == relation
    assert reverse["left_component_sum"] == result["right_component_sum"]
    population = module.compare_vectors(left, right, composition=False)
    assert population == {key: value for key, value in result.items() if key not in ("tv", "tv_decimal")}


def test_large_json_safe_components_keep_exact_products_and_string_sums():
    module = analyzer()
    count = 9007199254740991
    result = module.compare_vectors([count, count - 1], [count - 1, count], composition=True)
    assert result["left_component_sum"] == result["right_component_sum"] == "18014398509481981"
    assert result["relation"] == "nonproportional"
    assert result["tv"] == {"numerator": "1", "denominator": "18014398509481981"}
    assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize("left,right", [([], []), ([1], []), ([1], [1, 2]),
    ([True], [1]), ([-1], [1]), ([1.0], [1]), ([1.5], [1]), ([None], [1]),
    (["1"], [1]), ([9007199254740992], [1]), ([1], [False]), ([1], [-1])])
def test_invalid_vector_counts_and_dimensions_rejected(left, right):
    with pytest.raises(ValueError):
        analyzer().compare_vectors(left, right, composition=True)


def synthetic_header():
    # Sorted source IDs, deliberately non-slot, non-sorted model indices.
    indices = [10000 + ((slot * 73) % 256) * 7 for slot in range(256)]
    groups = {"kc": indices[:231] + [99999]}
    for name, slots in (("pam11", range(231, 236)), ("ppl101", range(236, 241)),
                        ("mbon07", range(241, 246)), ("mbon11", range(246, 251)),
                        ("motor_left", range(251, 256)), ("motor_right", range(251, 256))):
        groups[name] = [indices[slot] for slot in slots]
    groups["mbon11"].append(indices[0])  # Overlap with KC too.
    source = {name: sha256(name.encode()).hexdigest() for name in
              ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "annotations_sha256")}
    identity = {"version": "synthetic-response-structure/v1", "neural_groups": groups,
                "model_provenance": {**source, "model_fingerprint": model_fingerprint()}}
    identity["sha256"] = sha256(artifacts._canonical(identity)).hexdigest()
    cells = [{"model_index": index, "source_id": 1000 + slot,
              "groups": [name for name in GROUPS if index in groups[name]], "soma": None}
             for slot, index in enumerate(indices)]
    return {"type": "header", "version": "cell-activity-raw/v1", "engine_identity": identity,
            "selection": {"method": "mandatory-groups-kc-stride/v1", "limit": 256,
                          "group_population_counts": {name: len(groups[name]) for name in GROUPS},
                          "group_selected_counts": {name: sum(name in cell["groups"] for cell in cells)
                                                    for name in GROUPS}},
            "cells": cells, "source": source,
            "topology": {"method": "induced-directed-edge-stride/v1", "limit": 512,
                         "eligible_edges": 0, "edges": []}}


class SyntheticEngine:
    def __init__(self, helpers):
        self.brain = helpers.SyntheticBrain()
        self.header = synthetic_header()
        self.callback = None
        self.calls = 0

    def identity(self):
        return deepcopy(self.header["engine_identity"])

    def configure_cell_observer(self, indices, callback):
        assert indices == [cell["model_index"] for cell in self.header["cells"]]
        assert self.calls == 0 and self.callback is None
        self.callback = callback

    def observe(self, frame, duration_ms, **kwargs):
        assert duration_ms == 500
        assert kwargs == {"learning": False, "stimulation": None,
                          "pathway_detail": False, "qualification_detail": False}
        ordinal, start = self.calls, round(self.brain.sim_ms * 10)
        self.calls += 1
        counts = [0] * 256
        scale = max(0, (start - 20000) // 5000 + 1)
        if start >= 20000:
            if not frame.any(): counts[0] = scale
            elif frame[:, :32].all(): counts[0] = counts[220] = scale
            elif frame[:, 32:].all(): counts[0] = 2 * scale
            elif frame[:32].all(): counts[0], counts[1] = 3 * scale, scale
            else: counts[0], counts[1] = scale, 3 * scale
            counts[251] = scale
        bins = []
        for index in range(50):
            current = counts if index == 0 else [0] * 256
            population = {name: sum(count for count, cell in zip(current, self.header["cells"])
                                    if name in cell["groups"]) for name in GROUPS}
            if index == 0 and start >= 20000: population["kc"] += 5 * scale
            self.callback({"observation_index": ordinal, "bin_index": index,
                           "start_tick": start + 100 * index, "end_tick": start + 100 * (index + 1),
                           "counts": current[:]})
            bins.append({"end_ms": (start + 100 * (index + 1)) / 10, "duration_ms": 10,
                         "group_spikes": population})
        self.brain.sim_ms += 500
        self.brain.state = _rgb_input_sha256(frame)
        rates = {name: sum(row["group_spikes"][name] for row in bins) /
                 (len(self.header["engine_identity"]["neural_groups"][name]) * 0.5) for name in GROUPS}
        return {"sim_ms": self.brain.sim_ms, "interval_ms": 500, "learning": False, "stimulation": None,
                "compute_seconds": ordinal / 1000, "kernel_seconds": ordinal / 2000,
                "rates_hz": rates, "bins": bins, "input_shape": [64, 64, 3], "input_dtype": "uint8",
                "input_sha256": _rgb_input_sha256(frame), "engine_identity": self.identity()}


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    module = analyzer()
    diagnostic = module.DIAGNOSTIC
    helpers = load(ROOT / "tests/test_market_response_diagnostic.py", "response_fixture_helpers")
    engine = SyntheticEngine(helpers)
    helpers.install_synthetic_locks(diagnostic, tmp_path, monkeypatch, engine.header["source"])
    monkeypatch.setattr(diagnostic, "build_header", lambda identity, runtime: deepcopy(engine.header))
    output = tmp_path / "diagnostic"
    diagnostic.prepare_diagnostic(output)
    protocol = sha256((output / "protocol.json").read_bytes()).hexdigest()
    diagnostic.run_diagnostic(output, expected_protocol_sha256=protocol, engine_factory=lambda: engine)
    expected = {"expected_protocol_sha256": protocol,
                "expected_manifest_sha256": sha256((output / "run/run.json").read_bytes()).hexdigest(),
                "expected_events_sha256": sha256((output / "run/events.jsonl").read_bytes()).hexdigest()}
    return module, output, expected, helpers


def originals(output):
    return {path.relative_to(output).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in output.rglob("*") if path.is_file()}


def test_full_inventory_partition_counts_rates_and_complete_matrix(recorded):
    module, output, expected, _ = recorded
    before = originals(output)
    report = module.analyze_diagnostic(output, **expected)
    assert originals(output) == before
    assert report["version"] == "market-response-structure/v1"
    assert report["scope"] == "historical-development-response-inventory"
    assert report["verification_mode"] == "integrity-only" and "pass" not in report
    for key in ("protocol_sha256", "manifest_sha256", "events_sha256"):
        assert report["source"][key] == expected[f"expected_{key}"]
    assert report["implementation"]["files_sha256"]["scripts/analyze-response-structure.py"] == sha256(SCRIPT.read_bytes()).hexdigest()
    buckets = report["kc_partition"]["buckets"]
    assert len(buckets) == 21 and all(len(bucket["slots"]) == 11 for bucket in buckets)
    slots = [slot for bucket in buckets for slot in bucket["slots"]]
    assert sorted(slots) == list(range(231)) and len(set(slots)) == 231
    assert buckets[0]["slots"] == list(range(0, 220, 20))
    assert buckets[-1]["id"] == "excluded-sampled-kc" and buckets[-1]["slots"] == list(range(220, 231))
    assert buckets[0]["model_indices"] != buckets[0]["slots"]
    rows, comparisons = report["vectors"], report["comparisons"]
    assert len(rows) == 64 and sum(row["primary"] for row in rows) == 8
    assert len(comparisons) == 224 and sum(row["primary"] for row in comparisons) == 28
    assert sum(row["repeat_check"] for row in comparisons) == 24
    arms = [arm for arm, _ in module.DIAGNOSTIC.ARMS]
    for w in range(8):
        pairs = [row for row in comparisons if row["window_index"] == w]
        assert [(p["left_arm"], p["right_arm"]) for p in pairs] == [
            (arms[a], arms[b]) for a in range(8) for b in range(a + 1, 8)]
        assert all(p["primary"] == (w == 7) for p in pairs)
        assert sum(p["repeat_check"] for p in pairs) == 3
    assert [row["observation_index"] for row in rows] == list(range(4, 68))
    assert [row["window_index"] for row in rows] == list(range(8)) * 8
    control, vertical = rows[0], rows[8]
    assert control["kc"]["counts"] == [1] + [0] * 20
    assert vertical["kc"]["counts"] == [1] + [0] * 19 + [1]
    assert vertical["kc"]["component_sum"] == "2"
    assert vertical["kc"]["excluded_share"] == {"numerator": "1", "denominator": "2"}
    assert vertical["kc"]["shares"] == [{"numerator": "1", "denominator": "2"}] + [
        {"numerator": "0", "denominator": "1"}] * 19 + [{"numerator": "1", "denominator": "2"}]
    assert control["population"]["counts"] == [0, 0, 6, 0, 1, 1, 1]
    assert control["population"]["algebraic_component_sum"] == "9"
    assert control["population"]["rates_hz"] == [
        {"numerator": "0", "denominator": "1"}, {"numerator": "0", "denominator": "1"},
        {"numerator": "3", "denominator": "58"}, {"numerator": "0", "denominator": "1"},
        {"numerator": "1", "denominator": "3"}, {"numerator": "2", "denominator": "5"},
        {"numerator": "2", "denominator": "5"}]
    pair = comparisons[0]
    assert pair["kc"]["tv"] == {"numerator": "1", "denominator": "2"}
    assert pair["kc"]["relation"] == "nonproportional"
    assert comparisons[1]["kc"]["relation"] == "proportional"
    assert all("tv" not in pair["population"] and "shares" not in pair["population"] for pair in comparisons)
    assert all("shares" not in row["population"] and "total" not in row["population"] for row in rows)
    assert [p["id"] for p in report["population_declarations"]] == list(GROUPS)
    assert {"groups": ["kc", "mbon11"], "shared_members": 1} in report["membership_overlap"]
    assert {"groups": ["motor_left", "motor_right"], "shared_members": 5} in report["membership_overlap"]
    assert all(report["repeat_validation"].values())
    assert report["summary"]["vectors"] == 64 and report["summary"]["comparisons"] == 224
    assert sum(report["summary"]["kc_relations"].values()) == 224
    assert sum(report["summary"]["population_relations"].values()) == 224
    destination = output.parent / "structure.json"
    module.write_report(report, destination)
    assert json.loads(destination.read_bytes()) == report and originals(output) == before


@pytest.mark.parametrize("problem", ["overlap", "missing", "outside", "bool", "short", "kc-count"])
def test_partition_rejects_wrong_duplicate_missing_members(recorded, problem):
    module, output, _, _ = recorded
    declaration = artifacts.verify_run(output / "run").manifest["metadata"]["diagnostic"]
    header, grouping = deepcopy(declaration["header"]), deepcopy(declaration["grouping"])
    if problem == "overlap": grouping["excluded_kc_slots"][0] = grouping["groups"][0][0]
    elif problem == "missing": grouping["excluded_kc_slots"].pop()
    elif problem == "outside": grouping["groups"][0][0] = 255
    elif problem == "bool": grouping["groups"][0][0] = True
    elif problem == "short": grouping["groups"].pop()
    else: header["cells"][230]["groups"] = ["mbon11"]
    with pytest.raises(ValueError):
        module._partition(header, grouping)


@pytest.mark.parametrize("key", ["protocol", "manifest", "events"])
def test_wrong_caller_hash_rejected(recorded, key):
    module, output, expected, _ = recorded
    expected[f"expected_{key}_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        module.analyze_diagnostic(output, **expected)


@pytest.mark.parametrize("mutation", ["missing-window", "extra-window", "cell-bool", "cell-negative",
    "cell-fraction", "bad-rate", "observer-index", "repeat", "grouping"])
def test_resealed_invalid_input_never_produces_inventory(recorded, mutation):
    module, output, expected, helpers = recorded
    def mutate(metadata, events):
        row = events[7]
        if mutation == "missing-window": del events[8]
        elif mutation == "extra-window": events.insert(8, deepcopy(row))
        elif mutation.startswith("cell-"):
            row["cell_bins"][0]["counts"][0] = {"cell-bool": True, "cell-negative": -1, "cell-fraction": 0.5}[mutation]
        elif mutation == "bad-rate": row["telemetry"]["rates_hz"]["kc"] = 123.0
        elif mutation == "observer-index": row["cell_bins"][0]["observation_index"] = 0
        elif mutation == "repeat": events[41]["complete_state_sha256_after"] = "0" * 64
        else: metadata["diagnostic"]["grouping"]["excluded_kc_slots"].pop()
    helpers.reseal(output, mutate)
    expected["expected_manifest_sha256"] = sha256((output / "run/run.json").read_bytes()).hexdigest()
    expected["expected_events_sha256"] = sha256((output / "run/events.jsonl").read_bytes()).hexdigest()
    with pytest.raises((ValueError, artifacts.RunArtifactError)):
        module.analyze_diagnostic(output, **expected)
    assert not (output / "structure.json").exists()


def test_validated_private_snapshot_is_calculation_source(recorded, monkeypatch):
    module, output, expected, _ = recorded
    summarize = module.DIAGNOSTIC._summarize
    seen = []
    snapshot_run = module.snapshot_recorded_run
    @contextmanager
    def tracking_snapshot(*args, **kwargs):
        with snapshot_run(*args, **kwargs) as snapshot:
            seen.append(snapshot)
            yield snapshot
    monkeypatch.setattr(module, "snapshot_recorded_run", tracking_snapshot)
    def mutate_original_after_validation(run, protocol, protocol_hash):
        summary = summarize(run, protocol, protocol_hash)
        assert seen[0] != output / "run"
        (output / "run/events.jsonl").write_bytes(b"changed originals after snapshot validation\n")
        (output / "run/run.json").write_bytes(b"{}\n")
        return summary
    monkeypatch.setattr(module.DIAGNOSTIC, "_summarize", mutate_original_after_validation)
    report = module.analyze_diagnostic(output, **expected)
    assert len(report["vectors"]) == 64 and report["vectors"][0]["kc"]["counts"][0] == 1
    assert report["source"]["events_sha256"] == expected["expected_events_sha256"]
    assert not seen[0].exists()


def test_inspector_failure_cleans_snapshot_even_with_retained_traceback(recorded, monkeypatch):
    module, output, expected, _ = recorded
    paths, iterators = [], []
    snapshot_run = module.snapshot_recorded_run
    @contextmanager
    def tracking_snapshot(*args, **kwargs):
        with snapshot_run(*args, **kwargs) as snapshot:
            paths.append(snapshot)
            yield snapshot
    monkeypatch.setattr(module, "snapshot_recorded_run", tracking_snapshot)
    iter_events = artifacts.VerifiedRun.iter_events
    def tracked_events(run):
        events = iter_events(run)
        iterators.append(events)
        return events
    monkeypatch.setattr(artifacts.VerifiedRun, "iter_events", tracked_events)
    original = module.DIAGNOSTIC._summarize
    def rejecting(run, protocol, protocol_hash):
        return original(run, protocol, protocol_hash)
    monkeypatch.setattr(module.DIAGNOSTIC, "_summarize", rejecting)
    # Hash-valid malformed field reaches the frozen inspector, then cleanup.
    helpers = recorded[-1]
    helpers.reseal(output, lambda metadata, events: events[7]["cell_bins"][0].update(observation_index=0))
    expected["expected_manifest_sha256"] = sha256((output / "run/run.json").read_bytes()).hexdigest()
    expected["expected_events_sha256"] = sha256((output / "run/events.jsonl").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Cell/native bin clock/order mismatch") as retained:
        module.analyze_diagnostic(output, **expected)
    assert retained.traceback and paths and not paths[0].exists()
    assert iterators and all(events.gi_frame is None for events in iterators)


def test_second_scan_failure_closes_owned_iterator_and_cleans_snapshot(recorded, monkeypatch):
    module, output, expected, _ = recorded
    iterators = []
    original, iter_events = module.DIAGNOSTIC._summarize, artifacts.VerifiedRun.iter_events
    def wrong_summary(run, protocol, protocol_hash):
        summary = original(run, protocol, protocol_hash)
        summary["secondary"][0]["arms"]["control-1"]["group_counts"][0] += 1
        return summary
    def tracked_events(run):
        events = iter_events(run)
        iterators.append((run.path, events))
        return events
    monkeypatch.setattr(module.DIAGNOSTIC, "_summarize", wrong_summary)
    monkeypatch.setattr(artifacts.VerifiedRun, "iter_events", tracked_events)
    with pytest.raises(ValueError, match="KC vectors contradict") as retained:
        module.analyze_diagnostic(output, **expected)
    assert retained.traceback and len(iterators) == 2
    assert all(events.gi_frame is None and not path.exists() for path, events in iterators)


def test_silent_inventory_keeps_raw_zeros_and_undefined_shares(recorded):
    module, output, expected, helpers = recorded
    def silence(metadata, events):
        for event in events:
            if event["type"] != "observe": continue
            for cell_bin in event["cell_bins"]: cell_bin["counts"] = [0] * 256
            for native_bin in event["telemetry"]["bins"]: native_bin["group_spikes"] = dict.fromkeys(GROUPS, 0)
            event["telemetry"]["rates_hz"] = dict.fromkeys(GROUPS, 0.0)
    helpers.reseal(output, silence)
    expected["expected_manifest_sha256"] = sha256((output / "run/run.json").read_bytes()).hexdigest()
    expected["expected_events_sha256"] = sha256((output / "run/events.jsonl").read_bytes()).hexdigest()
    report = module.analyze_diagnostic(output, **expected)
    assert all(row["kc"] == {"counts": [0] * 21, "component_sum": "0", "shares": None,
                             "excluded_share": None} for row in report["vectors"])
    assert report["summary"]["kc_relations"]["both-silent"] == 224
    assert all(pair["kc"]["tv"] is None and pair["kc"]["tv_decimal"] is None for pair in report["comparisons"])


def test_every_kc_bucket_uses_all_eleven_members_and_correct_normalizer(recorded):
    module, output, expected, helpers = recorded
    def all_buckets(metadata, events):
        cells = metadata["diagnostic"]["header"]["cells"]
        for event in events:
            if event["type"] != "observe" or event["branch_id"] == "prefix": continue
            counts = [slot % 20 + 1 for slot in range(220)] + [21] * 11 + [0] * 25
            event["cell_bins"][0]["counts"] = counts
            populations = {name: sum(count for count, cell in zip(counts, cells) if name in cell["groups"])
                           for name in GROUPS}
            event["telemetry"]["bins"][0]["group_spikes"] = populations
            event["telemetry"]["rates_hz"] = {
                name: count / (len(metadata["engine_identity"]["neural_groups"][name]) * 0.5)
                for name, count in populations.items()}
    helpers.reseal(output, all_buckets)
    expected["expected_manifest_sha256"] = sha256((output / "run/run.json").read_bytes()).hexdigest()
    expected["expected_events_sha256"] = sha256((output / "run/events.jsonl").read_bytes()).hexdigest()
    report = module.analyze_diagnostic(output, **expected)
    for row in report["vectors"]:
        assert row["kc"]["counts"] == [11, 22, 33, 44, 55, 66, 77, 88, 99, 110,
                                         121, 132, 143, 154, 165, 176, 187, 198, 209, 220, 231]
        assert row["kc"]["component_sum"] == "2541"
        assert row["kc"]["shares"][0] == {"numerator": "1", "denominator": "231"}
        assert row["kc"]["excluded_share"] == {"numerator": "1", "denominator": "11"}


def test_event_line_limit_and_extra_checkpoint_rejected(recorded):
    module, output, expected, helpers = recorded
    helpers.reseal(output, lambda metadata, events: events[7].update(oversized="x" * (1024 * 1024)))
    expected["expected_manifest_sha256"] = sha256((output / "run/run.json").read_bytes()).hexdigest()
    expected["expected_events_sha256"] = sha256((output / "run/events.jsonl").read_bytes()).hexdigest()
    with pytest.raises(artifacts.RunArtifactError, match="line"):
        module.analyze_diagnostic(output, **expected)
    (output / "run/checkpoints/extra.npz").write_bytes(b"extra")
    with pytest.raises(ValueError, match="Checkpoint directory exceeds"):
        module.analyze_diagnostic(output, **expected)


@pytest.mark.parametrize("target,limit", [("protocol.json", 2 * 1024 * 1024),
    ("run/run.json", 2 * 1024 * 1024), ("run/events.jsonl", 64 * 1024 * 1024),
    ("run/checkpoints/brain-before.npz", 64 * 1024 * 1024)])
def test_old_read_limits_fail_before_unbounded_read(recorded, target, limit):
    module, output, expected, _ = recorded
    with (output / target).open("r+b") as stream:
        stream.truncate(limit + 1)
    with pytest.raises((ValueError, artifacts.RunArtifactError)):
        module.analyze_diagnostic(output, **expected)


def test_report_exact_newline_inclusive_limit_collision_and_no_partial(tmp_path):
    module = analyzer()
    output = tmp_path / "report.json"
    # {"x":""}\n is nine bytes; exactly 4 MiB publishes.
    payload = {"x": "a" * (4 * 1024 * 1024 - 9)}
    module.write_report(payload, output)
    assert output.stat().st_size == 4 * 1024 * 1024
    with pytest.raises(FileExistsError): module.write_report({}, output)
    oversized = tmp_path / "oversized.json"
    payload["x"] += "a"
    with pytest.raises(ValueError): module.write_report(payload, oversized)
    assert not oversized.exists()
    assert list(tmp_path.glob(".*.tmp")) == []


@pytest.mark.parametrize("kind", ["parent", "file"])
def test_linked_output_rejected(tmp_path, kind):
    module = analyzer()
    real = tmp_path / "real"
    real.mkdir()
    target = real / "report.json"
    target.write_bytes(b"preserve")
    link = tmp_path / "linked"
    try:
        link.symlink_to(real if kind == "parent" else target, target_is_directory=kind == "parent")
    except OSError as error:
        if os.name == "nt" and getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symbolic-link privilege unavailable")
        raise
    with pytest.raises((ValueError, OSError)):
        module.write_report({}, link / "new.json" if kind == "parent" else link)
    assert target.read_bytes() == b"preserve" and not (real / "new.json").exists()


@pytest.mark.parametrize("omitted", ["--diagnostic-dir", "--expected-protocol-sha256",
    "--expected-manifest-sha256", "--expected-events-sha256", "--output"])
def test_cli_requires_all_pins_and_explicit_paths(tmp_path, omitted):
    assert SCRIPT.is_file(), "The bounded response-structure analyzer is missing"
    output = tmp_path / "absent.json"
    arguments = {"--diagnostic-dir": str(tmp_path / "absent"), "--expected-protocol-sha256": "0" * 64,
                 "--expected-manifest-sha256": "0" * 64, "--expected-events-sha256": "0" * 64,
                 "--output": str(output)}
    command = [sys.executable, str(SCRIPT)]
    for name, value in arguments.items():
        if name != omitted: command.extend([name, value])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    assert result.returncode != 0 and not output.exists()
