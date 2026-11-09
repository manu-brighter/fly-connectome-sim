"""Declared synthetic protocol fixtures, never fullgraph or scientific evidence."""

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.neural.checkpoint import model_fingerprint


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-market-response-diagnostic.py"
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
ARMS = [("control-1", "black"), ("vertical-left", "A"), ("vertical-right", "B"),
        ("vertical-left-repeat", "A"), ("control-2", "black"), ("horizontal-top", "C"),
        ("horizontal-bottom", "D"), ("horizontal-top-repeat", "C")]
sys.path.insert(0, str(ROOT / "tests/experiment"))
from replay_helpers import map_engine_factory


def diagnostic():
    assert SCRIPT.is_file(), "The matched-state diagnostic implementation is missing"
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("market_response_diagnostic", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_header():
    groups = {name: [220 + index] for index, name in enumerate(name for name in GROUPS if name != "kc")}
    groups["kc"] = list(range(220))
    source = {name: sha256(name.encode()).hexdigest() for name in
              ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "annotations_sha256")}
    identity = {"version": "synthetic-market-response/v1", "neural_groups": groups,
                "model_provenance": {**source, "model_fingerprint": model_fingerprint()}}
    identity["sha256"] = sha256(artifacts._canonical(identity)).hexdigest()
    cells = [{"model_index": index, "source_id": 1000 + index,
              "groups": [name for name in GROUPS if index in groups[name]], "soma": None}
             for index in range(226)]
    return {"type": "header", "version": "cell-activity-raw/v1", "engine_identity": identity,
            "selection": {"method": "mandatory-groups-kc-stride/v1", "limit": 256,
                          "group_population_counts": {name: len(groups[name]) for name in GROUPS},
                          "group_selected_counts": {name: len(groups[name]) for name in GROUPS}},
            "cells": cells, "source": source,
            "topology": {"method": "induced-directed-edge-stride/v1", "limit": 512,
                         "eligible_edges": 0, "edges": []}}


class SyntheticBrain:
    def __init__(self):
        self.sim_ms = 0
        self.state = "initial"
        self.restores = []

    def checkpoint(self, path):
        Path(path).write_bytes(artifacts._canonical({"sim_ms": self.sim_ms, "state": self.state}))

    def restore(self, path):
        value = json.loads(Path(path).read_bytes())
        self.sim_ms, self.state = value["sim_ms"], value["state"]
        self.restores.append((str(path), self.sim_ms, self.checkpoint_state_sha256()))

    def checkpoint_state_sha256(self):
        return sha256(artifacts._canonical({"sim_ms": self.sim_ms, "state": self.state})).hexdigest()


class SyntheticEngine:
    def __init__(self, *, early_effect=False, unequal=False, overflow=False):
        self.brain = SyntheticBrain()
        self.header = synthetic_header()
        self.calls = []
        self.callback = None
        self.early_effect, self.unequal, self.overflow = early_effect, unequal, overflow

    def identity(self):
        return deepcopy(self.header["engine_identity"])

    def configure_cell_observer(self, indices, callback):
        assert self.callback is None and not self.calls and self.brain.sim_ms == 0
        assert indices == list(range(226))
        self.callback = callback

    def observe(self, frame, duration_ms, **kwargs):
        assert self.callback is not None
        assert duration_ms == 500
        assert kwargs == {"learning": False, "stimulation": None,
                          "pathway_detail": False, "qualification_detail": False}
        ordinal, start = len(self.calls), round(self.brain.sim_ms * 10)
        self.calls.append((frame.copy(), duration_ms, kwargs))
        active = self.early_effect and start == 20000 and np.array_equal(frame[:, :32], 255 * np.ones((64, 32, 3), dtype=np.uint8))
        bins = []
        for index in range(51 if self.overflow else 50):
            counts = [int(active and slot == 0 and index == 0) for slot in range(226)]
            if self.unequal and ordinal == 35 and index == 0:
                counts[0] += 1
            population = {name: sum(counts[cell] for cell in self.header["engine_identity"]["neural_groups"][name])
                          for name in GROUPS}
            self.callback({"observation_index": ordinal, "bin_index": index,
                           "start_tick": start + 100 * index, "end_tick": start + 100 * (index + 1),
                           "counts": counts})
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


def install_synthetic_locks(module, tmp_path, monkeypatch, source):
    # Explicit synthetic source locks, frozen before any test observation.
    locks = tmp_path / "synthetic-locks"
    locks.mkdir()
    (locks / "arrays.lock.json").write_bytes(artifacts._canonical(
        {name: source[f"graph_{name}_sha256"] for name in ("ids", "ptr", "post")}))
    (locks / "sources.lock.json").write_bytes(artifacts._canonical(
        {"annotations.feather": {"sha256": source["annotations_sha256"]}}))
    monkeypatch.setattr(module, "LOCKS", locks, raising=False)


def execute(tmp_path, monkeypatch, **kwargs):
    module, engine = diagnostic(), SyntheticEngine(**kwargs)
    monkeypatch.setattr(module, "build_header", lambda identity, runtime: deepcopy(engine.header))
    install_synthetic_locks(module, tmp_path, monkeypatch, engine.header["source"])
    output = tmp_path / "diagnostic"
    module.prepare_diagnostic(output)
    digest = sha256((output / "protocol.json").read_bytes()).hexdigest()
    receipt = module.run_diagnostic(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    return module, output, engine, receipt


def reseal(path, mutate):
    """Re-record altered semantics honestly; chain integrity alone is insufficient."""
    original = artifacts.verify_run(path / "run")
    metadata, root = original.manifest["metadata"], original.manifest["root_branch_id"]
    events = [{key: value for key, value in event.items() if key not in artifacts.OWNED}
              for event in original.iter_events()]
    mutate(metadata, events)
    destination = path / "altered"
    with artifacts.RunRecorder(destination, run_kind="pilot", metadata=metadata, root_branch_id=root) as recorder:
        for event in events:
            if event["type"] == "checkpoint":
                recorder.ingest_checkpoint(event["checkpoint_name"], path / "run/checkpoints" / event["checkpoint_name"],
                                           origin_branch_id=event["branch_id"])
            recorder.append(event)
    # Keep originals as declared test evidence outside inspected output.
    (path / "run").rename(path.parent / "original-run")
    destination.rename(path / "run")


def test_exact_frames_and_source_free_prepare(tmp_path, monkeypatch):
    module = diagnostic()
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("prepare constructed engine"))
    output = tmp_path / "prepared"
    manifest = module.prepare_diagnostic(output)
    assert set(p.name for p in output.iterdir()) == {"protocol.json"}
    assert json.loads((output / "protocol.json").read_bytes()) == manifest
    frames = module.frames()
    assert list(frames) == ["black", "A", "B", "C", "D"]
    assert all(frame.shape == (64, 64, 3) and frame.dtype == np.uint8 for frame in frames.values())
    assert not frames["black"].any()
    assert (frames["A"][:, :32] == 255).all() and not frames["A"][:, 32:].any()
    assert np.array_equal(frames["B"], frames["A"][:, ::-1])
    assert np.array_equal(frames["C"], frames["A"].transpose(1, 0, 2))
    assert np.array_equal(frames["D"], frames["C"][::-1])
    assert all(frame.mean() == 127.5 for key, frame in frames.items() if key != "black")
    assert manifest["frame_sha256"] == {key: _rgb_input_sha256(frame) for key, frame in frames.items()}
    assert manifest["frame_sha256"] == {
        "black": "aa5f1e84bc3d595d7cfa5f56d794840c0c55e6b67e5bc7a0fa976f9030e93448",
        "A": "2bab35627cfde1611798b177adad84251453d15920ed0f2fa692dbb12b9cc166",
        "B": "b6302efedf629e2e20f933890d8a4748f904b64dfcca4672d427255f0a740ab2",
        "C": "cf407fa59d7028e75e8bcc8dc1f4a47aec4a8b3db60f738574c2f2cd8f451257",
        "D": "7f4c6c24d6ebd72dcbbdd186db8bc1ffefb9df0df2be13bcc875b0b52e9367d6",
    }
    assert manifest["source"]["model_fingerprint"] == model_fingerprint()
    datasets = "src/fly_connectome_sim/neural/datasets.json"
    assert datasets in manifest["source"]["files_sha256"], "Packaged datasets.json is not frozen"
    assert manifest["source"]["files_sha256"][datasets] == sha256((ROOT / datasets).read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        module.prepare_diagnostic(output)


def test_exact_execution_and_sealed_forks(tmp_path, monkeypatch):
    module, output, engine, receipt = execute(tmp_path, monkeypatch)
    assert len(engine.calls) == 68 and sum(call[1] for call in engine.calls) == 34000
    assert len(engine.brain.restores) == 8
    assert {value[1] for value in engine.brain.restores} == {2000}
    assert len({value[2] for value in engine.brain.restores}) == 1
    run = artifacts.verify_run(output / "run")
    events = list(run.iter_events())
    assert len(events) == 79
    assert len(run.manifest["checkpoints"]) == 3
    observes = [event for event in events if event["type"] == "observe"]
    assert [event["cell_bins"][0]["observation_index"] for event in observes] == list(range(68))
    assert sum(len(event["cell_bins"]) for event in observes) == 3400
    forks = [event for event in events if event["type"] == "branch_start"]
    assert [event["branch_id"] for event in forks] == [arm for arm, _ in ARMS]
    for fork in forks:
        assert fork["parent_checkpoint_sequence"] == 5
        assert fork["parent_checkpoint_name"] == "black-prefix.npz"
        assert fork["parent_branch_id"] == "prefix"
        assert fork["complete_state_sha256"] == engine.brain.restores[0][2]
        assert "operation_version" not in fork
    report = module.inspect_diagnostic(output)
    assert report["observations"] == 68 and report["bins"] == 3400 and report["simulated_ms"] == 34000
    assert report["verification_mode"] == "integrity-only"
    assert report["primary"]["window_index"] == 7
    assert report["primary"]["any_difference"] is False
    assert len(report["secondary"]) == 8
    assert all(report["repeats"].values())
    assert report["grouping"]["groups"] == [list(range(rank, 220, 20)) for rank in range(20)]
    assert receipt["summary_sha256"] == sha256((output / "summary.json").read_bytes()).hexdigest()
    assert receipt["status"] == "complete"
    assert "pass" not in report and "pass" not in receipt


def test_first_window_effect_cannot_replace_null_primary(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch, early_effect=True)
    report = module.inspect_diagnostic(output)
    assert report["primary"]["any_difference"] is False
    assert report["secondary"][0]["any_difference"] is True
    assert report["secondary"][0]["comparisons"]["A-B"]["group_counts"][0] == 1


@pytest.mark.parametrize("problem", ["hash", "manifest", "extra", "source", "missing"])
def test_invalid_preparation_never_constructs_engine(tmp_path, problem):
    module, output = diagnostic(), tmp_path / "prepared"
    module.prepare_diagnostic(output)
    digest = sha256((output / "protocol.json").read_bytes()).hexdigest()
    if problem == "hash": digest = "0" * 64
    elif problem == "manifest": (output / "protocol.json").write_bytes(b"{}\n")
    elif problem == "extra": (output / "partial.log").write_bytes(b"old")
    elif problem == "source":
        data = json.loads((output / "protocol.json").read_bytes())
        data["source"]["model_fingerprint"]["sha256"] = "0" * 64
        (output / "protocol.json").write_bytes(artifacts._canonical(data) + b"\n")
        digest = sha256((output / "protocol.json").read_bytes()).hexdigest()
    else: (output / "protocol.json").unlink()
    with pytest.raises((ValueError, OSError)):
        module.run_diagnostic(output, expected_protocol_sha256=digest,
                              engine_factory=lambda: pytest.fail("invalid preflight constructed engine"))


@pytest.mark.parametrize("mode", ["unequal", "overflow"])
def test_invalid_capture_cannot_publish_completion(tmp_path, monkeypatch, mode):
    with pytest.raises(ValueError):
        execute(tmp_path, monkeypatch, **{mode: True})
    assert not (tmp_path / "diagnostic/receipt.json").exists()


@pytest.mark.parametrize("mutation", ["missing-arm", "extra-event", "reordered", "missing-bin", "cell-count",
    "rate", "frame", "frame-shape", "learning", "clock", "bin-clock", "observer-index", "cell-order",
    "grouping", "cohort", "final-state", "repeat", "header", "final-clock", "prefix-state"])
def test_sealed_but_semantically_invalid_recordings_rejected(tmp_path, monkeypatch, mutation):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    def mutate(metadata, events):
        row = events[7]  # First control observation.
        if mutation == "missing-arm": del events[6:15]
        elif mutation == "extra-event": events.insert(7, deepcopy(row))
        elif mutation == "reordered": row["stimulus"] = "A"
        elif mutation == "missing-bin": row["cell_bins"].pop()
        elif mutation == "cell-count": row["cell_bins"][0]["counts"][220] = 1
        elif mutation == "rate": row["telemetry"]["rates_hz"]["kc"] = 1.0
        elif mutation == "frame": row["input_sha256"] = "0" * 64
        elif mutation == "frame-shape": row["telemetry"]["input_shape"] = [32, 64, 3]
        elif mutation == "learning": row["telemetry"]["learning"] = True
        elif mutation == "clock": row["start_tick"] += 1
        elif mutation == "bin-clock": row["telemetry"]["bins"][0]["end_ms"] += 1
        elif mutation == "observer-index": row["cell_bins"][0]["observation_index"] = 0
        elif mutation == "cell-order": row["cell_bins"][0]["bin_index"] = 1
        elif mutation == "grouping": metadata["diagnostic"]["grouping"]["groups"][0].reverse()
        elif mutation == "cohort": metadata["diagnostic"]["header"]["cells"][0]["groups"] = ["motor_left"]
        elif mutation == "final-state": events[-1]["complete_state_sha256"] = "0" * 64
        elif mutation == "repeat": events[41]["complete_state_sha256_after"] = "0" * 64
        elif mutation == "header": metadata["diagnostic"]["header_sha256"] = "0" * 64
        elif mutation == "final-clock": events[-1]["sim_tick"] += 1
        elif mutation == "prefix-state": events[6]["complete_state_sha256"] = "0" * 64
    with pytest.raises((ValueError, OSError)):
        reseal(output, mutate)
        module.inspect_diagnostic(output)


def test_grouping_requires_220_fixed_source_ordered_kcs(tmp_path, monkeypatch):
    module, engine = diagnostic(), SyntheticEngine()
    header = deepcopy(engine.header)
    header["cells"] = header["cells"][1:]
    monkeypatch.setattr(module, "build_header", lambda identity, runtime: header)
    install_synthetic_locks(module, tmp_path, monkeypatch, engine.header["source"])
    output = tmp_path / "prepared"
    module.prepare_diagnostic(output)
    with pytest.raises(ValueError, match="220 KC"):
        module.run_diagnostic(output, expected_protocol_sha256=sha256((output / "protocol.json").read_bytes()).hexdigest(),
                              engine_factory=lambda: engine)
    assert not engine.calls


@pytest.mark.parametrize("arguments", [[], ["run"], ["run", "--run-native"], ["run", "--expected-protocol-sha256", "0" * 64]])
def test_cli_never_advances_by_default(tmp_path, arguments):
    assert SCRIPT.exists()
    result = subprocess.run([sys.executable, str(SCRIPT), *arguments, "--output-dir", str(tmp_path / "absent")],
                            text=True, capture_output=True, check=False)
    assert result.returncode != 0
    assert not (tmp_path / "absent").exists()


def test_existing_tiny_native_observer_restores_complete_state_without_resetting_indices(map_engine_factory, tmp_path):
    """Eight-cell native interface only; no diagnostic fullgraph acquisition."""
    module = diagnostic()
    engine = map_engine_factory(tonic=np.array([20, 0, 0, 0, 0, 0, 20, 0], dtype=np.float32))
    rows = []
    engine.configure_cell_observer(list(range(8)), lambda row: rows.append(deepcopy(row)))
    engine.observe(module.frames()["black"], 500, learning=False, stimulation=None,
                   pathway_detail=False, qualification_detail=False)
    common = tmp_path / "tiny-common.npz"
    engine.brain.checkpoint(common)
    common_state = engine.brain.checkpoint_state_sha256()
    projections, endings = [], []
    for _ in range(2):
        engine.brain.restore(common)
        assert engine.brain.sim_ms == 500 and engine.brain.checkpoint_state_sha256() == common_state
        before = len(rows)
        telemetry = engine.observe(module.frames()["A"], 500, learning=False, stimulation=None,
                                   pathway_detail=False, qualification_detail=False)
        current = rows[before:]
        assert len(current) == 50
        projections.append((telemetry["bins"], telemetry["rates_hz"],
                            [{key: value for key, value in row.items() if key != "observation_index"} for row in current]))
        endings.append(engine.brain.checkpoint_state_sha256())
    assert projections[0] == projections[1] and endings[0] == endings[1]
    assert [rows[index]["observation_index"] for index in (0, 50, 100)] == [0, 1, 2]
    assert rows[50]["start_tick"] == rows[100]["start_tick"] == 5000


@pytest.mark.parametrize("field", ["annotations_sha256", "graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256"])
def test_resealed_self_consistent_false_sources_rejected_by_frozen_locks(tmp_path, monkeypatch, field):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    def mutate(metadata, events):
        declaration = metadata["diagnostic"]
        header = declaration["header"]
        header["source"][field] = "0" * 64
        identity = metadata["engine_identity"]
        identity["model_provenance"][field] = "0" * 64
        identity["sha256"] = sha256(artifacts._canonical(
            {name: value for name, value in identity.items() if name != "sha256"})).hexdigest()
        header["engine_identity"] = deepcopy(identity)
        declaration["header_sha256"] = sha256(artifacts._canonical(header)).hexdigest()
        for event in events:
            if event["type"] == "observe":
                event["telemetry"]["engine_identity"] = deepcopy(identity)
    reseal(output, mutate)
    # The real verifier accepts the honestly resealed byte/chain integrity.
    assert artifacts.verify_run(output / "run").verification_mode == "integrity-only"
    with pytest.raises(ValueError, match="[Ll]ock"):
        module.inspect_diagnostic(output)
