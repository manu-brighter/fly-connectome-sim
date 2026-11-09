"""Synthetic-only fixed-input runner/auditor contracts; no native evidence."""
from contextlib import closing, contextmanager
from copy import deepcopy
from hashlib import sha256
import importlib.util
import itertools
import json
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.neural.checkpoint import raw_array_sha256
from test_continuous_motor_probe import FixtureEngine as ProbeFixtureEngine

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-drive-input-comparison.py"
ARMS = ("control-black", "image-a", "image-b", "image-a-repeat")
HASHES = {"black": "aa5f1e84bc3d595d7cfa5f56d794840c0c55e6b67e5bc7a0fa976f9030e93448",
          "A": "7c58398da961353df4ef0040261541e17bcaae7467a92a6395a0eb4f4b9d81be",
          "B": "831971b6bf50a21b29e9a369c84669aeffa3e90fd6a10278780eab05a0a34e30"}


def comparison():
    assert SCRIPT.is_file(), "The fixed input comparison implementation is missing"
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("drive_input_comparison", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FixtureEngine(ProbeFixtureEngine):
    """Reuse telemetry fixture only; JSON state is never native attestation."""
    def __init__(self, arms=None):
        counts = [(0, 0)] * 8 + [pair for arm in (arms or [[(0, 0)] * 40] * 4) for pair in arm]
        super().__init__(counts)
        self.restores, self.projections = [], []
        for name, value in {"retina": np.arange(3335, dtype=np.int32),
                            "uv": np.zeros((3335, 2), dtype=np.float32),
                            "r8": np.arange(811, dtype=np.int32),
                            "r8_uv": np.zeros((811, 2), dtype=np.float32),
                            "r8_channel": np.zeros(811, dtype=np.int32)}.items():
            setattr(self.brain, name, value)
        self._identity["model_provenance"]["configuration_sha256"] = {
            name: raw_array_sha256(getattr(self.brain, name))
            for name in ("retina", "uv", "r8", "r8_uv", "r8_channel")}
        self._identity["sha256"] = sha256(artifacts._canonical({
            key: value for key, value in self._identity.items() if key != "sha256"})).hexdigest()
        self.brain.rgb_drive = self.project
        self.brain.restore = self.restore

    def project(self, frame):
        assert not self.calls, "Projection must precede every advance"
        self.projections.append(frame.copy())
        # Deliberately different optical sampling despite equal image mean.
        value = float(frame[0, 0, 0]) / 255
        return {"r1_r6": np.full(3335, value, dtype=np.float32),
                "r8": np.full(811, value, dtype=np.float32)}

    def restore(self, path):
        self.restores.append(Path(path).read_bytes())
        self.brain.sim_ms = json.loads(self.restores[-1])["fixture_sim_ms"]


def setup(tmp_path, monkeypatch, arms=None):
    module, engine = comparison(), FixtureEngine(arms)
    locks = tmp_path / "fixture-locks"
    locks.mkdir()
    (locks / "arrays.lock.json").write_bytes(artifacts._canonical({
        name: engine._identity["model_provenance"][f"graph_{name}_sha256"] for name in ("ids", "ptr", "post")}))
    monkeypatch.setattr(module, "LOCKS", locks)
    monkeypatch.setattr(module._shared, "LOCKS", locks)
    output = tmp_path / "comparison"
    module.prepare_comparison(output)
    digest = sha256((output / "protocol.json").read_bytes()).hexdigest()
    return module, output, engine, digest


def execute(tmp_path, monkeypatch, arms=None, times=None):
    module, output, engine, digest = setup(tmp_path, monkeypatch, arms)
    timer = times or itertools.count(100000000000, 10000000)
    monkeypatch.setattr(module.time, "monotonic_ns", lambda: next(timer))
    receipt = module.run_comparison(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    return module, output, engine, receipt


def reseal(output, mutate):
    run = artifacts.verify_run(output / "run")
    metadata = deepcopy(run.manifest["metadata"])
    with closing(run.iter_events()) as stream:
        events = [{key: value for key, value in row.items() if key not in artifacts.OWNED} for row in stream]
    mutate(metadata, events)
    target = output / "altered"
    with artifacts.RunRecorder(target, run_kind="pilot", metadata=metadata, root_branch_id="prefix") as recorder:
        for row in events:
            if row["type"] == "checkpoint":
                recorder.ingest_checkpoint(row["checkpoint_name"], output / "run/checkpoints" / row["checkpoint_name"],
                                           origin_branch_id=row["branch_id"])
            recorder.append(row)
    (output / "run").rename(output / "original-run")
    target.rename(output / "run")
    (output / "summary.json").unlink()
    (output / "receipt.json").unlink()


def test_exact_frames_and_prepare_without_native(tmp_path, monkeypatch):
    module = comparison()
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("Native construction"))
    protocol = module.prepare_comparison(tmp_path / "prepared")
    frames = module.frames()
    y, x = np.indices((64, 64))
    expected = np.repeat((((x < 32) == (y < 32)) * 255).astype(np.uint8)[..., None], 3, axis=2)
    assert np.array_equal(frames["A"], expected)
    assert np.array_equal(frames["B"], 255 - expected) and not frames["black"].any()
    assert protocol["frame_sha256"] == HASHES
    assert protocol["decoder"]["configuration_sha256"] == "c02ca9be4db5198b46e718116ff80c169aa3d051f29ff7703d27f1f4fd5315c5"
    assert protocol["exact_counts"] == {"observations": 168, "native_bins": 8400, "events": 175,
                                         "checkpoints": 3, "branch_starts": 4, "actual_advance_ms": 84000,
                                         "branch_endpoint_ms": 24000}
    for relative in ("scripts/run-drive-input-comparison.py", "scripts/market_continuous_drive.py",
                     "scripts/run-continuous-motor-probe.py", "scripts/market_motor_readout.py"):
        assert protocol["source"]["files_sha256"][relative] == sha256((ROOT / relative).read_bytes()).hexdigest()
    assert "scripts/drive_input_supervision.py" not in protocol["source"]["files_sha256"]
    with pytest.raises(FileExistsError):
        module.prepare_comparison(tmp_path / "prepared")


def test_black_prefix_four_restores_fresh_decoders_real_clocks(tmp_path, monkeypatch):
    module, output, engine, receipt = execute(tmp_path, monkeypatch)
    assert len(engine.calls) == 168 and engine.brain.sim_ms == 24000
    assert len(engine.restores) == 4 and len(set(engine.restores)) == 1
    assert len(engine.projections) == 3
    run = artifacts.verify_run(output / "run")
    rows = list(run.iter_events())
    assert len(rows) == 175 and len(run.manifest["checkpoints"]) == 3
    assert [r["type"] for r in rows] == (["checkpoint"] + ["observe"] * 8 + ["checkpoint"] +
                                         (["branch_start"] + ["observe"] * 40) * 4 + ["checkpoint"])
    for row in rows[1:9]:
        assert not {"motor_sample", "readout_result", "readout_now_ms"} & row.keys()
    starts = [r for r in rows if r["type"] == "branch_start"]
    assert [r["branch_id"] for r in starts] == list(ARMS)
    assert len({r["session_id"] for r in starts}) == 4
    for arm in ARMS:
        obs = [r for r in rows if r["type"] == "observe" and r["branch_id"] == arm]
        assert [r["motor_sample"]["observation_index"] for r in obs] == list(range(40))
        assert obs[0]["start_tick"] == 40000 and obs[-1]["end_tick"] == 240000
        assert obs[0]["readout_result"]["reason"] == "incomplete_block"
    summary = module.inspect_comparison(output)
    assert summary == json.loads((output / "summary.json").read_bytes())
    assert summary["outcome"] == "functional-negative"
    assert summary["evaluation"]["repeat_exact"] is True and summary["evaluation"]["evaluable"] is True
    assert receipt["status"] == "complete" and summary["engine_mode"] == "injected-test-factory"
    assert summary["projection"]["frames"]["A"]["r1_r6"]["sum"] == 3335.0
    assert summary["projection"]["frames"]["B"]["r1_r6"]["sum"] == 0.0


@pytest.mark.parametrize("case,outcome,sensitivity", [
    ("function", "functional-input-sensitive", True),
    ("same", "functional-sensitivity-not-shown", False),
    ("none", "functional-negative", False),
    ("counts", "functional-sensitivity-not-shown", False),
    ("timing", "functional-output-timing-sensitive", True),
    ("availability", "functional-input-sensitive", True),
    ("repeat", "not-evaluable", False),
])
def test_predetermined_count_choice_price_timing_and_repeat_gates(tmp_path, monkeypatch, case, outcome, sensitivity):
    zero, lower, upper = [(0, 0)] * 40, [(5, 0)] * 40, [(0, 5)] * 40
    a, b, repeat = lower, upper, lower
    if case == "same": b = lower
    if case == "none": a = b = repeat = zero
    if case == "counts": b = [(6, 0)] * 40
    if case == "timing":
        a = [(5, 0)] * 20 + [(0, 0)] * 20
        b = [(0, 0)] * 4 + [(5, 0)] * 20 + [(0, 0)] * 16
        repeat = a
    if case == "availability": b = zero
    if case == "repeat": repeat = upper
    module, output, _, _ = execute(tmp_path, monkeypatch, [zero, a, b, repeat])
    summary = module.inspect_comparison(output)
    assert summary["outcome"] == outcome
    assert summary["evaluation"]["ab_output_sensitivity"] is sensitivity
    comparison_ab = summary["comparisons"]["A/B"]
    if case == "counts":
        assert comparison_ab["motor_counts_equal"] is False and comparison_ab["proposal_signatures_equal"] is True
    if case == "timing":
        assert comparison_ab["drink_ids_equal"] is comparison_ab["target_prices_equal"] is True
        assert comparison_ab["relative_times_equal"] is False
    if case == "availability":
        assert comparison_ab["lengths"] == [2, 0]
        assert comparison_ab["availability_count_difference"] is True
        assert comparison_ab["drink_ids_equal"] is comparison_ab["target_prices_equal"] is None
    if case == "repeat": assert summary["evaluation"]["repeat_exact"] is False


def test_stale_delivery_is_not_an_image_effect(tmp_path, monkeypatch):
    module, output, engine, digest = setup(tmp_path, monkeypatch, [[(5, 0)] * 40] * 4)
    # Actual monotonic fixture jumps before first A decoder delivery, not a model rewind.
    times = itertools.count(100000000000, 10000000)
    reads = 0
    def clock():
        nonlocal reads
        reads += 1
        return next(times) + (6000000000 if reads >= 141 else 0)
    monkeypatch.setattr(module.time, "monotonic_ns", clock)
    module.run_comparison(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    summary = module.inspect_comparison(output)
    assert summary["outcome"] == "not-evaluable"
    assert any("stale_sample" in reason for reason in summary["evaluation"]["reasons"])


@pytest.mark.parametrize("problem", ["frame", "source", "session", "sample", "rate", "count", "bin", "result",
    "clock", "rewind", "type", "branch", "checkpoint", "terminal", "extra", "metadata", "projection_hash",
    "projection_sum", "projection_order", "projection_nan", "projection_oversized", "projection_state", "missing", "eof"])
def test_resealed_semantic_tampering_cannot_become_evidence(tmp_path, monkeypatch, problem):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    def mutate(metadata, events):
        row = events[11]
        if problem == "frame": row["stimulus"] = "A"
        elif problem == "source": row["motor_sample"]["source_sha256"] = "0" * 64
        elif problem == "session": row["motor_sample"]["session_id"] = "foreign"
        elif problem == "sample": row["motor_sample"]["left_count"] = 9
        elif problem == "rate": row["telemetry"]["rates_hz"]["kc"] = 0
        elif problem == "count": row["telemetry"]["bins"][0]["group_spikes"]["motor_left"] = -1
        elif problem == "bin": row["telemetry"]["bins"][0]["end_ms"] += 1
        elif problem == "result": row["readout_result"]["reason"] = "waiting_for_neutral"
        elif problem == "clock": row["readout_now_ms"] = row["wall_completion_ms"] - 1
        elif problem == "rewind": row["wall_start_ms"] = 0
        elif problem == "type": row["start_tick"] = float(row["start_tick"])
        elif problem == "branch": events[10]["parent_checkpoint_sequence"] = 0
        elif problem == "checkpoint": events[9]["complete_state_sha256"] = "0" * 64
        elif problem == "terminal": events[-1]["complete_state_sha256"] = "0" * 64
        elif problem == "extra": row["native_replay"] = True
        elif problem == "metadata": metadata["comparison"]["protocol_sha256"] = "0" * 64
        elif problem == "missing": events.pop(20)
        elif problem == "eof": events.insert(-1, deepcopy(events[-2]))
        else:
            projection = metadata["comparison"]["projection"]
            vector = projection["frames"]["A"]["r1_r6"]
            if problem == "projection_hash": vector["sha256"] = "0" * 64
            elif problem == "projection_sum": vector["sum"] -= 1
            elif problem == "projection_order": projection["binding"]["retina"]["sha256"] = "0" * 64
            elif problem == "projection_nan": vector["values"][0] = float("nan")
            elif problem == "projection_oversized": vector["values"] = [0] * 10001
            else: projection["state_sha256_after"] = "0" * 64
    with pytest.raises((ValueError, KeyError)):
        reseal(output, mutate)
        module.inspect_comparison(output)


@pytest.mark.parametrize("problem", ["state", "clock", "identity", "length", "bound", "ordering"])
def test_projection_and_restore_failures_retain_honest_partials(tmp_path, monkeypatch, problem):
    module, output, engine, digest = setup(tmp_path, monkeypatch)
    original = engine.project
    def project(frame):
        result = original(frame)
        if problem == "state": engine.brain.checkpoint_state_sha256 = lambda: "0" * 64
        elif problem == "clock": engine.brain.sim_ms += 1
        elif problem == "identity": engine._identity["sha256"] = "0" * 64
        elif problem == "length": result["r8"] = np.zeros(812)
        elif problem == "bound": result["r8"][0] = 2
        else: engine.brain.retina[0] = 999
        return result
    monkeypatch.setattr(engine.brain, "rgb_drive", project)
    with pytest.raises(ValueError):
        module.run_comparison(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    assert not engine.calls and not (output / "receipt.json").exists()


def test_offline_reader_forbids_native_network_and_closes_iterator_on_error(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("Native execution"))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("Network access"))
    assert module.inspect_comparison(output)["outcome"] == "functional-negative"
    reseal(output, lambda meta, events: events[1].update(duration_ms=499))
    original, closed = artifacts.VerifiedRun.iter_events, []
    def tracked(run):
        try: yield from original(run)
        finally: closed.append(True)
    monkeypatch.setattr(artifacts.VerifiedRun, "iter_events", tracked)
    retained_error = None
    try: module.inspect_comparison(output)
    except ValueError as error: retained_error = error
    assert retained_error is not None and closed == [True]


@pytest.mark.parametrize("target,size", [("protocol.json", 2*1024**2+1), ("run/run.json", 2*1024**2+1),
    ("run/events.jsonl", 64*1024**2+1), ("run/checkpoints/brain-after.npz", 64*1024**2+1)])
def test_reader_caps_bytes_before_parsing(tmp_path, monkeypatch, target, size):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    with (output / target).open("wb") as stream: stream.truncate(size)
    with pytest.raises(ValueError): module.inspect_comparison(output)


def test_failure_keeps_partial_and_collision_refuses_before_engine(tmp_path, monkeypatch):
    module, output, engine, digest = setup(tmp_path, monkeypatch)
    original = engine.observe
    def fail(*args, **kwargs):
        if len(engine.calls) == 10: raise RuntimeError("synthetic failure")
        return original(*args, **kwargs)
    monkeypatch.setattr(engine, "observe", fail)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        module.run_comparison(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    assert (output / "run/events.jsonl").exists()
    assert not (output / "receipt.json").exists() and not (output / "summary.json").exists()
    with pytest.raises(ValueError):
        module.run_comparison(output, expected_protocol_sha256=digest,
                              engine_factory=lambda: pytest.fail("Collision constructed engine"))


def test_cli_and_missing_supervision_cannot_bypass_guard(tmp_path, monkeypatch):
    module, output, _, digest = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("Unguarded native"))
    with pytest.raises(ValueError): module.run_comparison(output, expected_protocol_sha256=digest)
    result = subprocess.run([sys.executable, str(SCRIPT), "run", "--help"], capture_output=True, text=True)
    assert result.returncode == 0 and "--run-native" in result.stdout and "--start-token" in result.stdout
    assert "--engine-factory" not in result.stdout and "--clock" not in result.stdout


def test_pending_route_keeps_supported_decisions_history_and_partial_block(tmp_path, monkeypatch):
    arm = [(5, 0)] * 16 + [(0, 0)] * 24
    module, output, _, _ = execute(tmp_path, monkeypatch, [arm] * 4)
    summary = module.inspect_comparison(output)
    pending = summary["arms"]["image-a"]["final_pending_state"]
    assert pending["phase"] == "price" and pending["interval"] == [0, 1]
    assert len(pending["decisions"]) == 4
    assert len(pending["input_history"]) == 40
    assert pending["partial_block"] == []
    assert summary["arms"]["image-a"]["reason_counts"]["unsupported_price"] == 6


@pytest.mark.parametrize("problem", ["state", "clock", "identity", "bytes"])
def test_restore_rejects_wrong_state_clock_identity_or_checkpoint_bytes(tmp_path, monkeypatch, problem):
    module, output, engine, digest = setup(tmp_path, monkeypatch)
    original = engine.restore
    def restore(path):
        original(path)
        if problem == "state": engine.brain.checkpoint_state_sha256 = lambda: "0" * 64
        elif problem == "clock": engine.brain.sim_ms = 0
        elif problem == "identity": engine._identity["sha256"] = "0" * 64
        else: Path(path).write_bytes(b"changed")
    monkeypatch.setattr(engine.brain, "restore", restore)
    with pytest.raises(ValueError):
        module.run_comparison(output, expected_protocol_sha256=digest, engine_factory=lambda: engine)
    assert len(engine.calls) == 8 and not (output / "receipt.json").exists()


def test_repeat_scientific_state_mismatch_is_reported_not_discarded(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    def change_a(metadata, events):
        rows = [r for r in events if r["type"] == "observe" and r["branch_id"] == "image-a"]
        rows[-1]["complete_state_sha256_after"] = "0" * 64
    reseal(output, change_a)
    summary = module.inspect_comparison(output)
    assert summary["outcome"] == "not-evaluable" and len(summary["arms"]) == 4
    assert summary["evaluation"]["repeat_exact"] is False


def test_native_factory_is_inside_lazy_adapter_context(tmp_path, monkeypatch):
    module, output, engine, digest = setup(tmp_path, monkeypatch)
    entered = []
    @contextmanager
    def start(actual_output, source, evidence, readiness, token):
        assert (actual_output, source, evidence, readiness, token) == (output.absolute(), digest,
            tmp_path / "supervision", "a" * 64, "test-token")
        entered.append(True)
        yield
        entered.pop()
    def factory():
        assert entered == [True]
        return engine
    monkeypatch.setitem(sys.modules, "drive_input_supervision", SimpleNamespace(production_start=start))
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", factory)
    receipt = module.run_comparison(output, expected_protocol_sha256=digest, supervision_directory=tmp_path / "supervision",
        expected_readiness_sha256="a" * 64, start_token="test-token")
    assert receipt["status"] == "complete" and entered == []


def test_summary_limit_rejects_before_publishing(tmp_path, monkeypatch):
    module, output, _, _ = execute(tmp_path, monkeypatch)
    protocol, digest = module._read_protocol(output)
    run = artifacts.verify_run(output / "run")
    monkeypatch.setattr(module, "MAX_SUMMARY_BYTES", 100)
    with closing(run.iter_events()) as events:
        with pytest.raises(ValueError, match="Summary exceeds"):
            module._summarize(run, protocol, digest, events)


def test_pending_direction_snapshot_is_detached_from_reconstructed_decoder(tmp_path, monkeypatch):
    arm = [(5, 0)] * 4 + [(0, 0)] * 36
    module, output, _, _ = execute(tmp_path, monkeypatch, [arm] * 4)
    original, constructed = module._decoder, []
    def decoder():
        value = original()
        constructed.append(value)
        return value
    monkeypatch.setattr(module, "_decoder", decoder)
    summary = module.inspect_comparison(output)
    pending = summary["arms"]["image-a-repeat"]["final_pending_state"]
    assert pending["interval"] == [0, 10] and pending["phase"] == "direction"
    assert len(pending["decisions"]) == 1 and len(pending["input_history"]) == 40
    assert pending["path_anchor"]["start_tick"] == 40000
    assert pending["path_anchor"]["wall_start_ms"] == pending["input_history"][0]["wall_start_ms"]
    pending["decisions"][0]["left_count"] = 999
    pending["input_history"][0]["left_count"] = 999
    assert constructed[-1]._decisions[0]["left_count"] == 20
    assert constructed[-1]._history[0]["left_count"] == 5
