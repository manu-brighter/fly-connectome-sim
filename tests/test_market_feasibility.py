"""Synthetic sealed populations; no native model, graph, or network evidence."""

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

from fly_connectome_sim.experiment import recorder as artifacts


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/analyze-market-feasibility.py"
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")


def analyzer():
    assert SCRIPT.is_file(), "The bounded offline population analyzer is missing"
    spec = importlib.util.spec_from_file_location("market_feasibility", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observation(start, duration, spikes, *, stimulus="video"):
    bins = []
    for offset in range(0, duration, 100):
        ticks = min(100, duration - offset)
        bins.append({"end_ms": (start + offset + ticks) / 10, "duration_ms": ticks / 10,
                     "group_spikes": {name: spikes if name == "kc" and offset == 0 else 0
                                      for name in GROUPS}})
    end = start + duration
    return {"type": "observe", "branch_id": "root", "sim_ms": end / 10,
            "start_tick": start, "end_tick": end, "duration_ticks": duration,
            "start_ms": start / 10, "end_ms": end / 10,
            "duration_ms": duration / 10, "stimulus": stimulus,
            "stimulation": None, "learning": False,
            "telemetry": {"sim_ms": end / 10, "interval_ms": duration / 10,
                          "stimulation": None, "learning": False,
                          "compute_seconds": duration / 10000 * 2,
                          "kernel_seconds": duration / 10000,
                          "rates_hz": {name: spikes / (2 * duration / 10000)
                                       if name == "kc" else 0.0 for name in GROUPS},
                          "bins": bins}}


def recorded(tmp_path, *, events=None, groups=None):
    """Public recorder ingest/seal; dummy bytes never claim native checkpoints."""
    metadata = {"engine_identity": {"version": "synthetic-market-test/v1",
                                   "neural_groups": groups if groups is not None else
                                   {name: [2 * index, 2 * index + 1] for index, name in enumerate(GROUPS)}},
                "protocol_version": "synthetic-market-test/v1", "stimulus_version": "synthetic/v1",
                "family": "synthetic-market-test", "seeds": [],
                "factors": {"synthetic_fixture": True}, "input_sha256": []}
    events = events if events is not None else [observation(0, 1000, 2), observation(1000, 2000, 8, stimulus="options")]
    path = tmp_path / "run"
    with artifacts.RunRecorder(path, run_kind="pilot", metadata=metadata, root_branch_id="root") as recorder:
        for name, tick, data in (("brain-before.npz", 0, b"synthetic before"),
                                 ("brain-after.npz", events[-1]["end_tick"] if events else 0, b"synthetic after")):
            if name == "brain-after.npz":
                for event in events:
                    recorder.append(event)
            source = tmp_path / name
            source.write_bytes(data)
            recorder.ingest_checkpoint(name, source, origin_branch_id="root")
            recorder.append({"type": "checkpoint", "branch_id": "root", "sim_ms": tick / 10,
                             "checkpoint_name": name})
    return path


@pytest.fixture(autouse=True)
def forbid_native_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline analyzer attempted native construction or network")
    from fly_connectome_sim.engine import FlyEngine
    monkeypatch.setattr(FlyEngine, "__init__", forbidden)
    monkeypatch.setattr(artifacts, "verify_replay_run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_weighted_population_summary(tmp_path):
    report = analyzer().analyze_recorded_run(recorded(tmp_path))
    assert report["observations"] == 2
    assert report["bins"] == 30
    assert report["simulated_ms"] == 300
    assert report["phase_ms"] == {"video": 100, "options": 200}
    assert report["groups"]["kc"] == {"size": 2, "spikes": 10,
        "mean_rate_hz": pytest.approx(10 / (2 * 0.3)), "min_bin_rate_hz": 0.0,
        "max_bin_rate_hz": 400.0, "zero_bins": 28, "nonzero_bins": 2}
    assert report["groups"]["pam11"]["spikes"] == 0
    assert report["groups"]["pam11"]["mean_rate_hz"] == 0
    assert report["groups"]["pam11"]["zero_bins"] == 30
    assert report["timing"] == {"compute_seconds": pytest.approx(0.6), "kernel_seconds": pytest.approx(0.3),
                                "compute_per_simulated_second": pytest.approx(2.0),
                                "kernel_per_simulated_second": pytest.approx(1.0),
                                "scope": "recorded-historical-fields"}
    manifest = artifacts.verify_run(tmp_path / "run").manifest
    for name in ("schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256", "run_kind"):
        assert report["source"][name] == manifest[name]
    assert report["source"]["engine_identity"] == manifest["metadata"]["engine_identity"]
    assert json.loads(json.dumps(report, allow_nan=False)) == report


def test_overlap_is_disclosed(tmp_path):
    groups = {name: [2 * index, 2 * index + 1] for index, name in enumerate(GROUPS)}
    groups["mbon11"] = groups["kc"][:]
    events = [observation(0, 1000, 2), observation(1000, 2000, 8)]
    for event in events:
        telemetry = event["telemetry"]
        telemetry["rates_hz"]["mbon11"] = telemetry["rates_hz"]["kc"]
        for native_bin in telemetry["bins"]:
            native_bin["group_spikes"]["mbon11"] = native_bin["group_spikes"]["kc"]
    report = analyzer().analyze_recorded_run(recorded(tmp_path, groups=groups, events=events))
    assert report["membership_overlap"] == [{"groups": ["kc", "mbon11"], "shared_members": 2}]
    assert report["groups"]["mbon11"]["spikes"] == 10


@pytest.mark.parametrize("field", ["start_ms", "end_ms"])
def test_sealed_redundant_clock_contradiction_rejected(tmp_path, field):
    events = [observation(0, 1000, 2), observation(1000, 2000, 8)]
    events[1][field] += 0.1
    path = recorded(tmp_path, events=events)
    assert len(list(artifacts.verify_run(path).iter_events())) == 4
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


def test_identical_membership_cannot_have_different_bin_counts(tmp_path):
    groups = {name: [2 * index, 2 * index + 1] for index, name in enumerate(GROUPS)}
    groups["mbon11"] = list(reversed(groups["kc"]))
    path = recorded(tmp_path, groups=groups)
    assert len(list(artifacts.verify_run(path).iter_events())) == 4
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


def test_identical_membership_cannot_move_spikes_between_bins(tmp_path):
    groups = {name: [2 * index, 2 * index + 1] for index, name in enumerate(GROUPS)}
    groups["mbon11"] = list(reversed(groups["kc"]))
    event = observation(0, 1000, 2)
    event["telemetry"]["bins"][1]["group_spikes"]["mbon11"] = 2
    event["telemetry"]["rates_hz"]["mbon11"] = 10.0
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(recorded(tmp_path, groups=groups, events=[event]))


def test_subset_consistent_counts_remain_analyzable(tmp_path):
    groups = {name: [2 * index, 2 * index + 1] for index, name in enumerate(GROUPS)}
    groups["mbon11"] = [4]
    event = observation(0, 1000, 2)
    event["telemetry"]["bins"][0]["group_spikes"]["mbon11"] = 1
    event["telemetry"]["rates_hz"]["mbon11"] = 10.0
    report = analyzer().analyze_recorded_run(recorded(tmp_path, groups=groups, events=[event]))
    assert report["groups"]["mbon11"]["spikes"] == 1
    assert report["groups"]["kc"]["spikes"] == 2


@pytest.mark.parametrize("subset,superset", [("mbon11", "kc"), ("kc", "mbon11")])
def test_subset_spikes_cannot_exceed_superset_in_a_bin(tmp_path, subset, superset):
    groups = {name: [2 * index, 2 * index + 1] for index, name in enumerate(GROUPS)}
    groups[subset] = [4]
    groups[superset] = [4, 5]
    event = observation(0, 1000, 0)
    event["telemetry"]["bins"][0]["group_spikes"][subset] = 2
    event["telemetry"]["bins"][0]["group_spikes"][superset] = 1
    event["telemetry"]["rates_hz"][subset] = 20.0
    event["telemetry"]["rates_hz"][superset] = 5.0
    path = recorded(tmp_path, groups=groups, events=[event])
    assert len(list(artifacts.verify_run(path).iter_events())) == 3
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


def test_short_bins_use_their_actual_duration(tmp_path):
    events = [observation(0, 50, 1), observation(50, 25, 1)]
    report = analyzer().analyze_recorded_run(recorded(tmp_path, events=events))
    assert report["simulated_ms"] == 7.5
    assert report["groups"]["kc"]["mean_rate_hz"] == pytest.approx(2 / (2 * 0.0075))
    assert report["groups"]["kc"]["min_bin_rate_hz"] == 100
    assert report["groups"]["kc"]["max_bin_rate_hz"] == 200


def test_finite_timing_values_cannot_overflow_the_sum(tmp_path):
    events = [observation(0, 1000, 2), observation(1000, 2000, 8)]
    for event in events:
        event["telemetry"]["compute_seconds"] = 1e308
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(recorded(tmp_path, events=events))


@pytest.mark.parametrize("mutation", ["rate", "bin-gap", "bin-overlap", "coverage", "long-bin",
    "empty-bins", "count-bool", "count-negative", "count-float", "count-missing", "count-extra",
    "rate-bool", "rate-negative", "rate-missing", "rate-extra", "clock-gap", "clock-overlap",
    "duration", "long-observe", "tick-bool", "event-learning", "telemetry-learning",
    "event-stimulation", "telemetry-stimulation", "missing-stimulation", "sim-clock",
    "telemetry-clock", "interval", "compute-negative", "compute-bool", "kernel-negative", "missing-timing",
    "missing-phase", "reset", "restore"])
def test_hash_valid_incompatible_observations_rejected(tmp_path, mutation):
    events = [observation(0, 1000, 2), observation(1000, 2000, 8)]
    event, telemetry = events[1], events[1]["telemetry"]
    if mutation == "rate": telemetry["rates_hz"]["kc"] += 1
    elif mutation == "bin-gap": telemetry["bins"][1]["end_ms"] += 0.1
    elif mutation == "bin-overlap": telemetry["bins"][1]["end_ms"] -= 0.1
    elif mutation == "coverage": telemetry["bins"].pop()
    elif mutation == "long-bin": telemetry["bins"][0]["duration_ms"] = 10.1
    elif mutation == "empty-bins": telemetry["bins"] = []
    elif mutation.startswith("count-"):
        counts = telemetry["bins"][0]["group_spikes"]
        if mutation == "count-missing": counts.pop("kc")
        elif mutation == "count-extra": counts["extra"] = 0
        else: counts["kc"] = {"count-bool": True, "count-negative": -1, "count-float": 8.0}[mutation]
    elif mutation.startswith("rate-"):
        rates = telemetry["rates_hz"]
        if mutation == "rate-missing": rates.pop("kc")
        elif mutation == "rate-extra": rates["extra"] = 0
        else: rates["kc"] = {"rate-bool": True, "rate-negative": -1}[mutation]
    elif mutation == "clock-gap": event["start_tick"] += 1
    elif mutation == "clock-overlap": event["start_tick"] -= 1
    elif mutation == "duration": event["duration_ticks"] -= 1
    elif mutation == "long-observe": event["duration_ticks"] = 5001
    elif mutation == "tick-bool": event["start_tick"] = True
    elif mutation == "event-learning": event["learning"] = True
    elif mutation == "telemetry-learning": telemetry["learning"] = True
    elif mutation == "event-stimulation": event["stimulation"] = "ppl101"
    elif mutation == "telemetry-stimulation": telemetry["stimulation"] = {"current_mv": 1}
    elif mutation == "missing-stimulation": event.pop("stimulation")
    elif mutation == "sim-clock": event["sim_ms"] -= 1
    elif mutation == "telemetry-clock": telemetry["sim_ms"] += 1
    elif mutation == "interval": telemetry["interval_ms"] += 1
    elif mutation == "compute-negative": telemetry["compute_seconds"] = -1
    elif mutation == "compute-bool": telemetry["compute_seconds"] = True
    elif mutation == "kernel-negative": telemetry["kernel_seconds"] = -1
    elif mutation == "missing-timing": telemetry.pop("compute_seconds")
    elif mutation == "missing-phase": event.pop("stimulus")
    else: event["type"] = mutation
    path = recorded(tmp_path, events=events)
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


@pytest.mark.parametrize("groups", [None, {}, {"kc": []}, {"kc": [True]}, {"kc": [-1]}, {"kc": [1, 1]}])
def test_invalid_group_declarations_rejected(tmp_path, groups):
    declaration = {name: [index] for index, name in enumerate(GROUPS)}
    if groups is None: declaration.pop("kc")
    elif groups == {}: declaration["kc"] = []
    else: declaration.update(groups)
    path = recorded(tmp_path, groups=declaration)
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


def test_altered_bytes_rejected_and_full_eof_checked(tmp_path):
    path = recorded(tmp_path)
    with (path / "events.jsonl").open("ab") as stream:
        stream.write(b"{}\n")
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


@pytest.mark.parametrize("field", ["compute_seconds", "kernel_seconds"])
@pytest.mark.parametrize("literal", [b"NaN", b"Infinity", b"-Infinity", b"1e999"])
def test_nonfinite_recorded_timing_rejected(tmp_path, field, literal):
    path = recorded(tmp_path)
    raw = (path / "events.jsonl").read_bytes()
    key = ('"' + field + '":').encode()
    begin = raw.index(key) + len(key)
    end = raw.index(b",", begin)
    raw = raw[:begin] + literal + raw[end:]
    (path / "events.jsonl").write_bytes(raw)
    manifest = json.loads((path / "run.json").read_bytes())
    manifest["events_sha256"] = sha256(raw).hexdigest()
    (path / "run.json").write_bytes(artifacts._canonical(manifest) + b"\n")
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


@pytest.mark.parametrize("field,value", [("event_count", 247), ("checkpoints", "extra")])
def test_declared_limit_excess_before_payloads(tmp_path, monkeypatch, field, value):
    path = recorded(tmp_path)
    manifest = json.loads((path / "run.json").read_bytes())
    if field == "event_count": manifest[field] = value
    else: manifest[field]["extra.npz"] = deepcopy(manifest[field]["brain-before.npz"])
    (path / "run.json").write_bytes(artifacts._canonical(manifest) + b"\n")
    original = Path.open
    def opened(path, *args, **kwargs):
        if path.name == "events.jsonl" or path.suffix == ".npz":
            pytest.fail("Over-limit declaration reached payload")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(ValueError, match="limit"):
        analyzer().analyze_recorded_run(path)


def test_oversized_checkpoint_rejected_before_hashing(tmp_path, monkeypatch):
    path = recorded(tmp_path)
    with (path / "checkpoints/brain-before.npz").open("r+b") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    original = Path.open
    def opened(path, *args, **kwargs):
        if path == tmp_path / "run/checkpoints/brain-before.npz":
            pytest.fail("Oversized checkpoint was opened")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(ValueError, match="limit"):
        analyzer().analyze_recorded_run(path)


def test_zero_duration_rejected(tmp_path):
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(recorded(tmp_path, events=[]))


def test_checkpoint_read_is_bounded_despite_false_stat(tmp_path, monkeypatch):
    path = recorded(tmp_path)
    target = path / "checkpoints/brain-before.npz"
    with target.open("r+b") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    original_stat, original_digest, original_open = Path.stat, artifacts._digest_file, Path.open
    reads = []
    def stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if path == target:
            values = list(result)
            values[6] = 16
            return os.stat_result(values)
        return result
    class BoundedReader:
        def __enter__(self):
            self.stream = original_open(target, "rb")
            return self
        def read(self, size=-1):
            assert 0 < size <= 1024 * 1024
            reads.append(size)
            return self.stream.read(size)
        def fileno(self): return self.stream.fileno()
        def __exit__(self, *args): self.stream.close()
    def digest(path, *args, **kwargs):
        if path.suffix == ".npz": pytest.fail("Oversized copied checkpoint reached hashing")
        return original_digest(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", stat)
    monkeypatch.setattr(Path, "open", lambda path, *args, **kwargs:
                        BoundedReader() if path == target else original_open(path, *args, **kwargs))
    monkeypatch.setattr(artifacts, "_digest_file", digest)
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)
    assert sum(reads) <= 64 * 1024 * 1024 + 1


def test_discontinuous_branch_semantics_rejected(tmp_path):
    path = recorded(tmp_path)
    # Build an independent public-recorded fork with exact durable ancestry.
    metadata = artifacts.verify_run(path).manifest["metadata"]
    fork = tmp_path / "fork"
    with artifacts.RunRecorder(fork, run_kind="pilot", metadata=metadata, root_branch_id="root") as recorder:
        source = tmp_path / "brain-before.npz"
        digest = recorder.ingest_checkpoint("brain-before.npz", source, origin_branch_id="root")
        recorder.append({"type": "checkpoint", "branch_id": "root", "sim_ms": 0,
                         "checkpoint_name": "brain-before.npz"})
        recorder.append({"type": "branch_start", "branch_id": "fork", "sim_ms": 0,
                         "parent_branch_id": "root", "parent_checkpoint_sha256": digest})
        recorder.ingest_checkpoint("brain-after.npz", source, origin_branch_id="root")
        recorder.append({"type": "checkpoint", "branch_id": "root", "sim_ms": 0,
                         "checkpoint_name": "brain-after.npz"})
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(fork)


@pytest.mark.parametrize("name,cap", [("run.json", 2 * 1024 * 1024),
                                      ("events.jsonl", 64 * 1024 * 1024)])
def test_oversized_input_files_rejected(tmp_path, name, cap):
    path = recorded(tmp_path)
    with (path / name).open("r+b") as stream:
        stream.truncate(cap + 1)
    with pytest.raises(ValueError, match="limit"):
        analyzer().analyze_recorded_run(path)


def test_oversized_event_line_rejected(tmp_path):
    path = recorded(tmp_path)
    (path / "events.jsonl").write_bytes(b"x" * (1024 * 1024 + 1) + b"\n")
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)


@pytest.mark.parametrize("mutation", ["growth", "replacement"])
def test_checkpoint_changed_after_preflight_never_yields_report(tmp_path, monkeypatch, mutation):
    path = recorded(tmp_path)
    target = path / "checkpoints/brain-before.npz"
    original = Path.open
    changed = False
    def opened(path, *args, **kwargs):
        nonlocal changed
        if path == target and args == ("rb",) and not changed:
            changed = True
            if mutation == "replacement":
                target.rename(target.with_suffix(".old"))
                with original(target, "wb") as stream:
                    stream.write(b"replacement")
            else:
                with original(target, "r+b") as stream:
                    stream.truncate(64 * 1024 * 1024 + 1)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(path)
    assert changed


@pytest.mark.parametrize("location", ["manifest", "events", "checkpoint", "ancestor"])
def test_linked_input_never_traverses_outside_run(tmp_path, location):
    path = recorded(tmp_path)
    if location == "ancestor":
        target, original, directory = tmp_path / "linked", path, True
    else:
        target = path / {"manifest": "run.json", "events": "events.jsonl",
                         "checkpoint": "checkpoints/brain-before.npz"}[location]
        original = tmp_path / ("outside-" + target.name)
        target.rename(original)
        directory = False
    try:
        target.symlink_to(original, target_is_directory=directory)
    except OSError as error:
        pytest.skip(f"Symbolic-link privilege unavailable: {error}")
    with pytest.raises(ValueError):
        analyzer().analyze_recorded_run(target if location == "ancestor" else path)


def cli(path, output):
    guard = ("import runpy, socket, sys; from fly_connectome_sim.engine import FlyEngine; "
             "from fly_connectome_sim.experiment import recorder; "
             "def_forbidden = lambda *a, **k: (_ for _ in ()).throw(AssertionError('native/network forbidden')); "
             "FlyEngine.__init__ = def_forbidden; recorder.verify_replay_run = def_forbidden; "
             "socket.socket = def_forbidden; socket.create_connection = def_forbidden; "
             "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')")
    return subprocess.run([sys.executable, "-c", guard, str(SCRIPT), "--run-dir", str(path), "--output", str(output)],
                          capture_output=True, text=True, check=False)


def test_cli_valid_labels_and_new_output(tmp_path):
    path, output = recorded(tmp_path), tmp_path / "report.json"
    result = cli(path, output)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_bytes())
    assert report["format"] == "fly-market-feasibility/v1"
    assert report["verification_mode"] == "integrity-only"
    assert report["scope"] == "historical-population-inventory"
    assert report["limitations"] == ["No single-cell inference.", "No new learning evidence.",
        "No validated drink selection or price mapping.", "No long-run or real-time qualification.",
        "Membership overlap does not establish functional independence.",
        "Source identity describes the historical recording, not current-source equivalence.",
        "Recorded timing fields are not a new benchmark or supervisor result."]
    assert "pass" not in report


def test_cli_invalid_emits_no_report(tmp_path):
    path = recorded(tmp_path)
    (path / "events.jsonl").write_bytes(b"invalid\n")
    output = tmp_path / "report.json"
    assert cli(path, output).returncode != 0
    assert not output.exists()


def test_output_collision_preserved(tmp_path):
    path, output = recorded(tmp_path), tmp_path / "report.json"
    output.write_bytes(b"preserve")
    assert cli(path, output).returncode != 0
    assert output.read_bytes() == b"preserve"


def test_dangling_output_link_preserved(tmp_path):
    path, output = recorded(tmp_path), tmp_path / "report.json"
    missing = tmp_path / "missing.json"
    try:
        output.symlink_to(missing)
    except OSError as error:
        pytest.skip(f"Symbolic-link privilege unavailable: {error}")
    assert cli(path, output).returncode != 0
    assert output.is_symlink()
    assert not missing.exists()


def test_unserializable_report_leaves_no_output(tmp_path):
    output = tmp_path / "report.json"
    with pytest.raises((TypeError, ValueError)):
        analyzer().write_report({"invalid": float("nan")}, output)
    assert not output.exists()


def test_failed_fsync_leaves_no_success_report(tmp_path, monkeypatch):
    module = analyzer()
    report = module.analyze_recorded_run(recorded(tmp_path))
    output = tmp_path / "report.json"
    before = set(tmp_path.iterdir())
    def broken(*args): raise OSError("Declared fsync failure")
    monkeypatch.setattr(module.os, "fsync", broken)
    with pytest.raises(OSError):
        module.write_report(report, output)
    assert not output.exists()
    assert set(tmp_path.iterdir()) == before


def test_replacement_before_fsync_failure_is_preserved(tmp_path, monkeypatch):
    module = analyzer()
    report = module.analyze_recorded_run(recorded(tmp_path))
    output = tmp_path / "report.json"
    replacement = tmp_path / "replacement.json"
    replacement.write_bytes(b"other process owns this")
    def broken(*args):
        os.replace(replacement, output)
        raise OSError("Declared fsync failure after path replacement")
    monkeypatch.setattr(module.os, "fsync", broken)
    with pytest.raises(OSError):
        module.write_report(report, output)
    assert output.read_bytes() == b"other process owns this"
    assert not list(tmp_path.glob(".report.json.*"))


@pytest.mark.parametrize("stage", ["write", "flush"])
def test_failed_temporary_write_never_publishes_output(tmp_path, monkeypatch, stage):
    module = analyzer()
    report = module.analyze_recorded_run(recorded(tmp_path))
    output = tmp_path / "report.json"
    original = module.tempfile.NamedTemporaryFile
    before = set(tmp_path.iterdir())
    class FailingTemporaryFile:
        def __init__(self, *args, **kwargs):
            self.stream = original(*args, **kwargs)
            self.name = self.stream.name
        def __enter__(self): return self
        def __exit__(self, *args): self.stream.close()
        def write(self, data):
            if stage == "write":
                self.stream.write(data[:5])
                raise OSError("Declared temporary write failure")
            return self.stream.write(data)
        def flush(self):
            self.stream.flush()
            raise OSError("Declared temporary flush failure")
        def fileno(self): return self.stream.fileno()
    monkeypatch.setattr(module.tempfile, "NamedTemporaryFile", FailingTemporaryFile)
    with pytest.raises(OSError):
        module.write_report(report, output)
    assert not output.exists()
    assert set(tmp_path.iterdir()) == before


def test_output_created_at_publication_wins_without_overwrite(tmp_path, monkeypatch):
    module = analyzer()
    report = module.analyze_recorded_run(recorded(tmp_path))
    output = tmp_path / "report.json"
    original = module.os.link
    def collision(source, target):
        output.write_bytes(b"other process published first")
        return original(source, target)
    monkeypatch.setattr(module.os, "link", collision)
    with pytest.raises(FileExistsError):
        module.write_report(report, output)
    assert output.read_bytes() == b"other process published first"
    assert not list(tmp_path.glob(".report.json.*"))
