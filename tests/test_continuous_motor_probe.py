"""Synthetic software fixtures only; no native acquisition or neural claims."""

from copy import deepcopy
from contextlib import contextmanager
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.neural.checkpoint import model_fingerprint


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-continuous-motor-probe.py"
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
ORDER = ("S1", "S2", "S3", "S4", "S5", "S6", "S6", "S5", "S4", "S3", "S2", "S1")
HASHES = {
    "black": "aa5f1e84bc3d595d7cfa5f56d794840c0c55e6b67e5bc7a0fa976f9030e93448",
    "S1": "c1fe7a097c8ee4b8a4d71211cc638e7a3a660e5d06f335b90ea2ae61c1964761",
    "S2": "e6cbe8173a2ee4a339040e7463f73cbda6f5fd859032afdb65e0ac7d4134b029",
    "S3": "c553a2bd58cf00fe0974cdaee4cc0b9eb5ad00a0aa173ff5aad3e82d81189a51",
    "S4": "d03d741fd55ed52eff994c9f529fd74472330eb6bad8dc321e26a1ecbcfee094",
    "S5": "c30d24a55590eacdbc4eef56f38de778a015cbca30c4e0f24e2bf8337e02454b",
    "S6": "265475b42ecc0e1da35998836975864eed445e1ed12d901c832bf6d3ae46c8ae",
}


def probe():
    assert SCRIPT.is_file(), "The continuous motor probe implementation is missing"
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("continuous_motor_probe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FixtureBrain:
    """Dummy JSON checkpoints, explicitly not native complete-state evidence."""

    def __init__(self):
        self.sim_ms = 0

    def checkpoint(self, path):
        Path(path).write_bytes(artifacts._canonical({"fixture_sim_ms": self.sim_ms}))

    def checkpoint_state_sha256(self):
        return sha256(artifacts._canonical({"fixture_sim_ms": self.sim_ms})).hexdigest()


class FixtureEngine:
    def __init__(self, counts=None):
        self.brain, self.calls = FixtureBrain(), []
        self.counts = counts or [(0, 0)] * 192
        groups = {name: [index] for index, name in enumerate(GROUPS)}
        groups["kc"] = [2, 7]  # Verify rates use the actual declared population size.
        source = {f"graph_{name}_sha256": sha256(name.encode()).hexdigest() for name in ("ids", "ptr", "post")}
        self._identity = {"version": "synthetic-continuous-probe/v1", "neural_groups": groups,
                          "model_provenance": {**source, "model_fingerprint": model_fingerprint()}}
        self._identity["sha256"] = sha256(artifacts._canonical(self._identity)).hexdigest()

    def identity(self):
        return deepcopy(self._identity)

    def observe(self, frame, duration_ms, **kwargs):
        assert duration_ms == 500
        assert kwargs == {"learning": False, "stimulation": None,
                          "pathway_detail": False, "qualification_detail": False}
        index, start = len(self.calls), self.brain.sim_ms
        self.calls.append(frame.copy())
        left, right = self.counts[index]
        bins = []
        for slot in range(50):
            spikes = dict.fromkeys(GROUPS, 0)
            if slot == 0:
                spikes.update(motor_left=left, motor_right=right, kc=2)
            bins.append({"end_ms": start + (slot + 1) * 10, "duration_ms": 10, "group_spikes": spikes})
        self.brain.sim_ms += 500
        rates = {name: sum(row["group_spikes"][name] for row in bins) /
                 (0.5 * len(self._identity["neural_groups"][name])) for name in GROUPS}
        return {"sim_ms": self.brain.sim_ms, "interval_ms": 500, "learning": False, "stimulation": None,
                "compute_seconds": 0.001, "kernel_seconds": 0.0005, "rates_hz": rates,
                "bins": bins, "input_shape": [64, 64, 3], "input_dtype": "uint8",
                "input_sha256": _rgb_input_sha256(frame), "engine_identity": self.identity()}


def fixture_setup(tmp_path, monkeypatch, counts=None):
    module, engine = probe(), FixtureEngine(counts)
    locks = tmp_path / "fixture-locks"
    locks.mkdir()
    (locks / "arrays.lock.json").write_bytes(artifacts._canonical({
        name: engine._identity["model_provenance"][f"graph_{name}_sha256"] for name in ("ids", "ptr", "post")}))
    monkeypatch.setattr(module, "LOCKS", locks)
    output = tmp_path / "probe"
    module.prepare_probe(output)
    digest = sha256((output / "protocol.json").read_bytes()).hexdigest()
    return module, output, engine, digest


def execute(tmp_path, monkeypatch, counts=None, clock=None):
    module, output, engine, digest = fixture_setup(tmp_path, monkeypatch, counts)
    timer = iter(range(1000, 1000 + 192 * 3 * 10, 10))
    receipt = module.run_probe(output, expected_protocol_sha256=digest, engine_factory=lambda: engine,
                               clock_ms=clock or (lambda: next(timer)))
    return module, output, engine, receipt


def reseal(output, mutate):
    """Rebuild a valid chain around false semantics; preserve original fixtures."""
    run = artifacts.verify_run(output / "run")
    metadata = deepcopy(run.manifest["metadata"])
    events = [{key: value for key, value in row.items() if key not in artifacts.OWNED}
              for row in run.iter_events()]
    mutate(metadata, events)
    destination = output / "altered"
    with artifacts.RunRecorder(destination, run_kind="pilot", metadata=metadata,
                               root_branch_id="continuous") as recorder:
        for event in events:
            if event["type"] == "checkpoint":
                recorder.ingest_checkpoint(event["checkpoint_name"],
                    output / "run/checkpoints" / event["checkpoint_name"], origin_branch_id="continuous")
            recorder.append(event)
    (output / "run").rename(output / "original-run")
    destination.rename(output / "run")
    (output / "summary.json").unlink()
    (output / "receipt.json").unlink()


def test_exact_frames_hashes_and_prepare_without_engine(tmp_path, monkeypatch):
    module = probe()
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("Unexpected engine"))
    protocol = module.prepare_probe(tmp_path / "prepared")
    frames = module.frames()
    y, x = np.indices((64, 64))
    masks = [(x // 8) % 2 == 0, (y // 8) % 2 == 0, (x // 8 + y // 8) % 2 == 0,
             ((x + y) // 8) % 2 == 0, (16 <= x) & (x < 48), (16 <= y) & (y < 48)]
    assert list(frames) == ["black", "S1", "S2", "S3", "S4", "S5", "S6"]
    assert not frames["black"].any()
    for index, mask in enumerate(masks, 1):
        frame = frames[f"S{index}"]
        assert frame.shape == (64, 64, 3) and frame.dtype == np.uint8
        assert np.array_equal(frame, np.repeat((mask * 255).astype(np.uint8)[..., None], 3, axis=2))
        assert np.count_nonzero(frame[:, :, 0]) == 2048
    assert protocol["frame_sha256"] == HASHES
    assert {key: _rgb_input_sha256(value) for key, value in frames.items()} == HASHES
    assert len(set(HASHES.values())) == 7
    old_hashes = {"2bab35627cfde1611798b177adad84251453d15920ed0f2fa692dbb12b9cc166",
                  "b6302efedf629e2e20f933890d8a4748f904b64dfcca4672d427255f0a740ab2",
                  "cf407fa59d7028e75e8bcc8dc1f4a47aec4a8b3db60f738574c2f2cd8f451257",
                  "7f4c6c24d6ebd72dcbbdd186db8bc1ffefb9df0df2be13bcc875b0b52e9367d6"}
    assert not set(HASHES.values()) & old_hashes
    assert protocol["decoder"]["configuration"]["max_sample_age_ms"] == 5000
    assert [d["id"] for d in protocol["decoder"]["configuration"]["drinks"]] == [f"drink-{i:02d}" for i in range(20)]
    assert set(path.name for path in (tmp_path / "prepared").iterdir()) == {"protocol.json"}
    for source in ("scripts/run-continuous-motor-probe.py", "scripts/market_motor_readout.py",
                   "scripts/market_artifacts.py", "src/fly_connectome_sim/experiment/recorder.py"):
        assert protocol["source"]["files_sha256"][source] == sha256((ROOT / source).read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        module.prepare_probe(tmp_path / "prepared")


def test_complete_silent_session_is_negative_and_exactly_continuous(tmp_path, monkeypatch):
    module, output, engine, receipt = execute(tmp_path, monkeypatch)
    assert engine.brain.sim_ms == 96000 and len(engine.calls) == 192
    run = artifacts.verify_run(output / "run")
    rows = list(run.iter_events())
    assert len(rows) == 194 and len(run.manifest["checkpoints"]) == 2
    assert run.manifest["root_branch_id"] == "continuous"
    assert [row["type"] for row in rows] == ["checkpoint"] + ["observe"] * 192 + ["checkpoint"]
    for index, row in enumerate(rows[1:-1]):
        frame = "black" if index % 16 < 4 else ORDER[index // 16]
        assert row["stimulus"] == frame and row["input_sha256"] == HASHES[frame]
        assert row["input_version"] == f"episode-{index // 16 + 1:02d}-{frame}"
        assert np.array_equal(engine.calls[index], module.frames()[frame])
        assert row["start_tick"] == index * 5000 and row["end_tick"] == (index + 1) * 5000
        assert len(row["telemetry"]["bins"]) == 50
        sample = row["motor_sample"]
        assert sample["observation_index"] == index
        assert sample["left_count"] == sample["right_count"] == 0
        assert sample["source_sha256"] == receipt["protocol_sha256"]
        assert (sample["wall_start_ms"], sample["wall_completion_ms"], row["readout_now_ms"]) == (1000 + 30 * index, 1010 + 30 * index, 1020 + 30 * index)
    summary = module.inspect_probe(output)
    assert summary == json.loads((output / "summary.json").read_bytes())
    assert summary["exact_counts"] == {"episodes": 12, "observations": 192, "native_bins": 9600,
                                       "events": 194, "checkpoints": 2, "model_ms": 96000}
    assert summary["outcome"] == "negative" and summary["proposals"] == []
    assert summary["status_counts"] == {"waiting": 1, "ready": 1, "collecting": 143, "deferred": 47}
    assert summary["final_pending_state"]["status"] == "collecting"
    assert summary["latency_ms"]["processing"] == [10] * 192
    assert summary["latency_ms"]["delivery"] == [10] * 192
    assert receipt["status"] == "complete" and receipt["summary_sha256"] == sha256((output / "summary.json").read_bytes()).hexdigest()
    assert "pass" not in summary and "pass" not in receipt


def test_supported_path_crosses_order_boundary_without_reset(tmp_path, monkeypatch):
    # No neutrality until sample90; lower-lower-lower-lower + separate price.
    counts = [(5, 5)] * 90 + ([(0, 0)] * 2 + [(5, 0)] * 4) * 5
    counts += [(5, 5)] * (192 - len(counts))
    module, output, _, _ = execute(tmp_path, monkeypatch, counts)
    summary = module.inspect_probe(output)
    assert summary["outcome"] == "narrow-positive"
    proposal, = summary["proposals"]
    assert proposal["drink_id"] == "drink-00" and proposal["target_rappen"] == 400
    assert proposal["path_start_tick"] == 460000 and proposal["completion_tick"] == 600000
    assert len(proposal["decisions"]) == 4 and len(proposal["input_history"]) == 28
    assert summary["direction_counts"] == {"lower": 4, "upper": 0}
    assert summary["order_partitions"][0]["proposal_count"] == 0
    assert summary["order_partitions"][1]["proposal_count"] == 1
    assert summary["route_metrics"]["concentration"]["drink-00"]["count"] == 1
    assert summary["route_metrics"]["maximum_selected_fraction"] == 1


@pytest.mark.parametrize("problem", ["count", "float_count", "negative_count", "rate", "population", "sample", "result", "source", "session", "config", "clock", "rewind", "now", "learning", "stimulation", "detail", "frame", "input_version", "bin_gap", "duration", "extra_field", "final_state", "metadata_source"])
def test_resealed_semantic_contradictions_rejected(tmp_path, monkeypatch, problem):
    module, output, _, _ = execute(tmp_path, monkeypatch)

    def mutate(metadata, events):
        row = events[2]
        if problem == "count": row["telemetry"]["bins"][0]["group_spikes"]["motor_left"] += 1
        elif problem == "float_count": row["telemetry"]["bins"][0]["group_spikes"]["kc"] = 2.0
        elif problem == "negative_count": row["telemetry"]["bins"][0]["group_spikes"]["kc"] = -1
        elif problem == "rate": row["telemetry"]["rates_hz"]["kc"] = 0
        elif problem == "population": metadata["engine_identity"]["neural_groups"]["motor_left"].append(9)
        elif problem == "sample": row["motor_sample"]["left_count"] = 4
        elif problem == "result": row["readout_result"]["status"] = "waiting"
        elif problem == "source": row["motor_sample"]["source_sha256"] = "0" * 64
        elif problem == "session": row["motor_sample"]["session_id"] = "foreign"
        elif problem == "config": metadata["probe"]["configuration_sha256"] = "0" * 64
        elif problem == "clock": row["motor_sample"]["wall_completion_ms"] = row["motor_sample"]["wall_start_ms"] - 1
        elif problem == "rewind": row["motor_sample"]["wall_start_ms"] = 0
        elif problem == "now": row["readout_now_ms"] = 1
        elif problem == "learning": row["learning"] = True
        elif problem == "stimulation": row["telemetry"]["stimulation"] = {"population": "pam11"}
        elif problem == "detail": row["telemetry"]["qualification_detail"] = {}
        elif problem == "frame": row["stimulus"] = "S1"
        elif problem == "input_version": row["input_version"] = "episode-02-black"
        elif problem == "bin_gap": row["telemetry"]["bins"][0]["end_ms"] += 1
        elif problem == "duration": row["duration_ms"] = 499
        elif problem == "extra_field": row["operation_version"] = "restore/v1"
        elif problem == "final_state": events[-1]["complete_state_sha256"] = "0" * 64
        else: metadata["probe"]["protocol_sha256"] = "0" * 64

    # Some contradictions fail even the reused recorder's stronger intake.
    with pytest.raises((ValueError, KeyError)):
        reseal(output, mutate)
        module.inspect_probe(output)
    if (output / "original-run").exists():
        assert not (output / "summary.json").exists() and not (output / "receipt.json").exists()


@pytest.mark.parametrize("problem", ["missing", "extra", "checkpoint", "overflow_bins"])
def test_eof_checkpoint_and_bin_inventory_are_exact(tmp_path, monkeypatch, problem):
    module, output, _, _ = execute(tmp_path, monkeypatch)

    def mutate(metadata, events):
        if problem == "missing": events.pop(45)
        elif problem == "extra": events.insert(-1, deepcopy(events[-2]))
        elif problem == "checkpoint": events[-1]["sim_tick"] -= 1
        else: events[1]["telemetry"]["bins"].append(deepcopy(events[1]["telemetry"]["bins"][-1]))

    with pytest.raises(ValueError):
        reseal(output, mutate)
        module.inspect_probe(output)


def test_consistently_resealed_times_are_not_authenticated(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch)

    def mutate(metadata, events):
        for row in events[1:-1]:
            for key in ("wall_start_ms", "wall_completion_ms"):
                row["motor_sample"][key] += 100000
            row["readout_now_ms"] += 100000
    reseal(output, mutate)
    summary = module.inspect_probe(output)
    assert summary["clocks"]["first_observation_start_ms"] == 101000
    assert any("authenticated" in limitation for limitation in summary["limitations"])


def test_failure_preserves_partials_without_success(tmp_path, monkeypatch):
    module, output, engine, digest = fixture_setup(tmp_path, monkeypatch)
    original = engine.observe

    def fail(frame, duration, **kwargs):
        if len(engine.calls) == 3:
            raise RuntimeError("deliberate fixture failure")
        return original(frame, duration, **kwargs)
    monkeypatch.setattr(engine, "observe", fail)
    with pytest.raises(RuntimeError, match="deliberate"):
        module.run_probe(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    assert (output / "run/events.jsonl").is_file()
    assert not (output / "summary.json").exists() and not (output / "receipt.json").exists()
    with pytest.raises((ValueError, OSError)):
        module.inspect_probe(output)


@pytest.mark.parametrize("problem", ["extra", "hash", "protocol", "clock_without_factory", "missing_supervision"])
def test_invalid_start_fails_before_engine(tmp_path, monkeypatch, problem):
    module, output, _, digest = fixture_setup(tmp_path, monkeypatch)
    factory = lambda: pytest.fail("Engine constructed before gate")
    kwargs = {"expected_protocol_sha256": digest, "engine_factory": factory}
    if problem == "extra": (output / "old.log").write_text("partial")
    elif problem == "hash": kwargs["expected_protocol_sha256"] = "0" * 64
    elif problem == "protocol": (output / "protocol.json").write_text("{}\n")
    elif problem == "clock_without_factory": kwargs.update(engine_factory=None, clock_ms=lambda: 0)
    else: kwargs["engine_factory"] = None
    with pytest.raises((ValueError, RuntimeError)):
        module.run_probe(output, **kwargs)


def test_bounded_snapshot_and_no_engine_during_inspection(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("Inspection constructed engine"))
    assert module.inspect_probe(output)["outcome"] == "negative"
    with (output / "run/events.jsonl").open("ab") as stream:
        stream.write(b" " * (1024 * 1024 + 1))
    with pytest.raises(ValueError):
        module.inspect_probe(output)


def test_linked_input_directory_is_rejected(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    link = tmp_path / "linked"
    try:
        link.symlink_to(output, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlink unavailable on this host: {error}")
    with pytest.raises(ValueError):
        module.inspect_probe(link)


def test_cli_has_no_factory_clock_or_limit_escape():
    probe()
    result = subprocess.run([sys.executable, str(SCRIPT), "run", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--run-native" in result.stdout and "--expected-readiness-sha256" in result.stdout
    assert "--clock" not in result.stdout and "--engine-factory" not in result.stdout
    assert "--limit" not in result.stdout


def test_default_clock_reads_three_actual_monotonic_times_per_observation(tmp_path, monkeypatch):
    module, output, engine, digest = fixture_setup(tmp_path, monkeypatch)
    ticks = iter(range(321000000000, 321000000000 + 576 * 7000000, 7000000))
    monkeypatch.setattr(module.time, "monotonic_ns", lambda: next(ticks))
    module.run_probe(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    rows = list(artifacts.verify_run(output / "run").iter_events())
    assert rows[1]["motor_sample"]["wall_start_ms"] == 321000
    assert rows[1]["motor_sample"]["wall_completion_ms"] == 321007
    assert rows[1]["readout_now_ms"] == 321014
    assert rows[192]["readout_now_ms"] == 325025
    assert next(ticks, None) is None


def test_production_factory_is_inside_lazy_supervision_guard(tmp_path, monkeypatch):
    module, output, engine, digest = fixture_setup(tmp_path, monkeypatch)
    entered = []

    @contextmanager
    def start(actual_output, protocol_hash, evidence, readiness_hash, token):
        assert (actual_output, protocol_hash, evidence, readiness_hash, token) == (
            output.absolute(), digest, tmp_path / "evidence", "a" * 64, "test-token")
        entered.append(True)
        yield
        entered.pop()

    def factory():
        assert entered == [True]
        return engine
    monkeypatch.setitem(sys.modules, "continuous_motor_supervision", SimpleNamespace(production_start=start))
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", factory)
    result = module.run_probe(output, expected_protocol_sha256=digest, supervision_directory=tmp_path / "evidence",
                              expected_readiness_sha256="a" * 64, start_token="test-token")
    assert result["status"] == "complete" and entered == []


@pytest.mark.parametrize("target,size", [("protocol.json", 2 * 1024**2 + 1),
                                        ("run/run.json", 2 * 1024**2 + 1),
                                        ("run/events.jsonl", 64 * 1024**2 + 1),
                                        ("run/checkpoints/brain-after.npz", 64 * 1024**2 + 1)])
def test_reader_enforces_individual_and_total_byte_caps(tmp_path, monkeypatch, target, size):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    with (output / target).open("wb") as stream:
        stream.truncate(size)
    with pytest.raises(ValueError):
        module.inspect_probe(output)


@pytest.mark.parametrize("field", ["metadata", "telemetry"])
def test_hidden_contradictory_fields_are_not_ignored(tmp_path, monkeypatch, field):
    module, output, _, _ = execute(tmp_path, monkeypatch)

    def mutate(metadata, events):
        record = metadata if field == "metadata" else events[1]["telemetry"]
        record["restored_from_checkpoint"] = "undeclared.npz"
    reseal(output, mutate)
    with pytest.raises(ValueError):
        module.inspect_probe(output)


def test_summary_preserves_unfinished_route_and_proposal_elapsed_times(tmp_path, monkeypatch):
    # One full route then one supported lower direction ending in neutral waiting.
    counts = ([(0, 0)] * 2 + [(5, 0)] * 4) * 5
    counts += [(5, 5)] * 156 + [(0, 0)] * 2 + [(5, 0)] * 4
    module, output, _, _ = execute(tmp_path, monkeypatch, counts)
    summary = module.inspect_probe(output)
    assert summary["route_metrics"]["proposal_timings"] == [{
        "drink_id": "drink-00", "model_elapsed_ms": 14000,
        "wall_elapsed_ms": 820, "emission_delivery_ms": 10,
    }]
    pending, = summary["route_metrics"]["partial_routes"]
    assert pending["termination"] == "end-of-observation-pending"
    assert len(pending["directions"]) == 1


@pytest.mark.parametrize("case", ["no-neutrality", "unsupported-price-then-expiry"])
def test_valid_negative_distinguishes_neutral_waiting_price_and_expiry(tmp_path, monkeypatch, case):
    if case == "no-neutrality":
        counts = [(5, 5)] * 192
    else:
        counts = ([(0, 0)] * 2 + [(5, 0)] * 4) * 4
        counts += [(0, 0)] * (192 - len(counts))
    module, output, _, _ = execute(tmp_path, monkeypatch, counts)
    summary = module.inspect_probe(output)
    assert summary["outcome"] == "negative" and summary["proposals"] == []
    if case == "no-neutrality":
        assert summary["reason_counts"] == {"waiting_for_neutral": 192}
        assert summary["direction_counts"] == {"lower": 0, "upper": 0}
    else:
        assert summary["reason_counts"]["unsupported_price"] > 0
        assert summary["reason_counts"]["path_expired"] == 1
        assert summary["route_metrics"]["partial_routes"][0]["termination"] == "path_expired"
        assert len(summary["route_metrics"]["partial_routes"][0]["directions"]) == 4


@pytest.mark.parametrize("case", ["metadata-protocol-type", "telemetry-identity-type", "frame-shape-type"])
def test_resealed_equal_valued_json_type_contradictions_fail(tmp_path, monkeypatch, case):
    module, output, _, _ = execute(tmp_path, monkeypatch)

    def mutate(metadata, events):
        if case == "metadata-protocol-type":
            metadata["probe"]["protocol"]["observation"]["learning"] = 0
        elif case == "telemetry-identity-type":
            events[1]["telemetry"]["engine_identity"]["neural_groups"]["ppl101"] = [True]
        else:
            events[1]["telemetry"]["input_shape"] = [64.0, 64, 3]
    reseal(output, mutate)
    with pytest.raises(ValueError):
        module.inspect_probe(output)


def test_resealed_total_spikes_cannot_omit_disjoint_population_counts(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch, [(5, 5)] * 192)

    def mutate(metadata, events):
        # Distinct singleton motor populations alone require at least10 spikes.
        events[1]["telemetry"]["total_spikes"] = 5
    reseal(output, mutate)
    with pytest.raises(ValueError, match="Total spikes"):
        module.inspect_probe(output)
    assert not (output / "summary.json").exists() and not (output / "receipt.json").exists()


@pytest.mark.parametrize("total_spikes", [19, 20])
def test_resealed_total_spikes_uses_disjoint_subsets_without_overlap_double_count(tmp_path, monkeypatch, total_spikes):
    module, output, _, _ = execute(tmp_path, monkeypatch, [(5, 5)] * 192)

    def mutate(metadata, events):
        # Three fixture cells have counts2,3,5. Two distinct motor cells have5 each.
        # The seven population totals sum35, but the represented cells total20.
        groups = {"pam11": [2], "ppl101": [2, 3], "kc": [2, 7], "mbon07": [3],
                  "mbon11": [3, 7], "motor_left": [5], "motor_right": [6]}
        counts = {"pam11": 2, "ppl101": 5, "kc": 7, "mbon07": 3,
                  "mbon11": 8, "motor_left": 5, "motor_right": 5}
        identity = metadata["engine_identity"]
        identity["neural_groups"] = groups
        identity["sha256"] = sha256(artifacts._canonical({
            key: value for key, value in identity.items() if key != "sha256"})).hexdigest()
        for event in events[1:-1]:
            telemetry = event["telemetry"]
            telemetry["engine_identity"] = deepcopy(identity)
            telemetry["bins"][0]["group_spikes"] = deepcopy(counts)
            telemetry["rates_hz"] = {name: count / (len(groups[name]) * 0.5) for name, count in counts.items()}
            telemetry["total_spikes"] = total_spikes
    reseal(output, mutate)
    if total_spikes == 19:
        with pytest.raises(ValueError, match="Total spikes"):
            module.inspect_probe(output)
        return
    summary = module.inspect_probe(output)
    assert summary["outcome"] == "negative"
    assert summary["reason_counts"] == {"waiting_for_neutral": 192}
