"""Injected synthetic software fixtures only; no native/runtime evidence."""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import importlib.util
import itertools
from dataclasses import replace
import json
from pathlib import Path
import socket
import shutil
import struct
import subprocess
import sys

import numpy as np
import pytest

from fly_connectome_sim.engine import _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.neural.checkpoint import model_fingerprint
from test_continuous_motor_probe import FixtureBrain, GROUPS

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run-live-buffer-performance.py"


def performance():
    assert SCRIPT.is_file(), "The bounded live-buffer producer/auditor is missing"
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("live_buffer_performance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FixtureEngine:
    """Synthetic callbacks/telemetry and JSON states, never a native acquisition."""
    def __init__(self):
        self.brain, self.calls, self.installs = FixtureBrain(), [], []
        locks = json.loads((ROOT / "src/fly_connectome_sim/neural/arrays.lock.json").read_bytes())
        groups = {name: [index] for index, name in enumerate(GROUPS)}
        groups["kc"] = [2, *range(7, 300)]
        self._identity = {"version": "synthetic-live-buffer/v1", "neural_groups": groups,
                          "model_provenance": {"model_fingerprint": model_fingerprint(),
                              **{f"graph_{name}_sha256": locks[name] for name in ("ids", "ptr", "post")}}}
        self._identity["sha256"] = sha256(artifacts._canonical(self._identity)).hexdigest()
        self.bad = None
        self.motor_counts = [(0, 0)] * 120

    def identity(self):
        return deepcopy(self._identity)

    def configure_cell_observer(self, indices, callback):
        assert self.brain.sim_ms == 0 and not self.calls
        self.installs.append(list(indices))
        self.callback = callback

    def observe(self, frame, duration_ms, **kwargs):
        assert duration_ms == 500
        assert kwargs == {"learning": False, "stimulation": None,
                          "pathway_detail": False, "qualification_detail": False}
        i, start = len(self.calls), int(self.brain.sim_ms * 10)
        self.calls.append(frame.copy())
        left, right = self.motor_counts[i]
        bins = []
        for j in range(50):
            counts = [0] * 256
            counts[2] = int(j == 0)
            counts[5], counts[6] = (left, right) if j == 0 else (0, 0)
            payload = {"observation_index": i, "bin_index": j, "start_tick": start + j * 100,
                       "end_tick": start + (j + 1) * 100, "counts": counts}
            if self.bad == "callback" and i == 2 and j == 3:
                payload["counts"][0] = 101
            if self.bad == "partial" and i == 2 and j == 3:
                raise RuntimeError("synthetic partial advance")
            self.callback(payload)
            bins.append({"end_ms": (start + (j + 1) * 100) / 10, "duration_ms": 10,
                         "group_spikes": {name: (left if name == "motor_left" else right if name == "motor_right" else int(name == "kc"))
                                          if j == 0 else 0 for name in GROUPS}})
        self.brain.sim_ms += 500
        result = {"sim_ms": self.brain.sim_ms, "interval_ms": 500, "learning": False, "stimulation": None,
                  "compute_seconds": .001, "kernel_seconds": .0005,
                  "rates_hz": {name: sum(b["group_spikes"][name] for b in bins) /
                               (.5 * len(self._identity["neural_groups"][name])) for name in GROUPS},
                  "bins": bins, "input_shape": [64, 64, 3], "input_dtype": "uint8",
                  "input_sha256": _rgb_input_sha256(frame), "engine_identity": self.identity(), "total_spikes": 1 + left + right}
        if self.bad == "missing_total":
            result.pop("total_spikes")
        return result


def fixture_header(identity, runtime):
    """Deliberate fake static join injected instead of reading private arrays."""
    populations = identity["neural_groups"]
    cells = [{"model_index": i, "source_id": 1000 + i,
              "groups": [name for name in GROUPS if i in populations[name]], "soma": None}
             for i in range(256)]
    sources = json.loads((ROOT / "src/fly_connectome_sim/neural/sources.lock.json").read_bytes())
    return {"type": "header", "version": "cell-activity-raw/v1", "engine_identity": identity,
            "selection": {"method": "mandatory-groups-kc-stride/v1", "limit": 256,
                "group_population_counts": {name: len(populations[name]) for name in GROUPS},
                "group_selected_counts": {name: sum(name in c["groups"] for c in cells) for name in GROUPS}},
            "cells": cells, "topology": {"method": "induced-directed-edge-stride/v1", "limit": 512,
                                         "eligible_edges": 1, "edges": [[0, 0, 1]]},
            "source": {**{name: identity["model_provenance"][name] for name in
                            ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256")},
                       "annotations_sha256": sources["annotations.feather"]["sha256"]}}


def setup(tmp_path):
    module, engine = performance(), FixtureEngine()
    output = tmp_path / "performance"
    protocol = module.prepare_performance(output)
    digest = sha256((output / "protocol.json").read_bytes()).hexdigest()
    return module, output, engine, digest, protocol


def execute(tmp_path, *, clock=None, bad=None):
    module, output, engine, digest, _ = setup(tmp_path)
    engine.bad = bad
    ticks = itertools.count(1000, 10)
    module.run_performance(output, expected_protocol_sha256=digest, engine_factory=lambda: engine,
                           header_builder=fixture_header, clock_ms=clock or (lambda: next(ticks)))
    return module, output, engine


def rows(output):
    run = artifacts.verify_run(output / "run")
    with closing(run.iter_events()) as stream:
        return list(stream)


def reseal(output, mutate):
    run = artifacts.verify_run(output / "run")
    metadata = deepcopy(run.manifest["metadata"])
    events = [{k: v for k, v in row.items() if k not in artifacts.OWNED} for row in rows(output)]
    mutate(metadata, events)
    with artifacts.RunRecorder(output / "altered", run_kind="pilot", metadata=metadata,
                               root_branch_id="continuous") as recorder:
        for event in events:
            if event["type"] == "checkpoint":
                recorder.ingest_checkpoint(event["checkpoint_name"], output / "run/checkpoints" / event["checkpoint_name"],
                                           origin_branch_id="continuous")
            recorder.append(event)
    (output / "run").rename(output / "original-run")
    (output / "altered").rename(output / "run")
    (output / "summary.json").unlink()
    (output / "receipt.json").unlink()


def test_prepare_exact_contract_and_exclusive(tmp_path):
    module, output, _, _, protocol = setup(tmp_path)
    assert protocol["version"] == "live-buffer-performance/v1"
    assert protocol["exact_counts"] == {"observations": 120, "native_bins": 6000, "windows": 600,
                                         "events": 122, "checkpoints": 2, "model_ms": 60000}
    assert protocol["decoder"]["configuration_sha256"] == "c02ca9be4db5198b46e718116ff80c169aa3d051f29ff7703d27f1f4fd5315c5"
    assert protocol["buffers"]["owned_array_bytes"] == 288000
    assert len(protocol["schedule"]) == 120
    for path in ("scripts/market_live_buffers.py", "scripts/run-live-buffer-performance.py",
                 "scripts/run-drive-input-comparison.py", "scripts/run-continuous-motor-probe.py",
                 "src/fly_connectome_sim/experiment/cell_activity.py"):
        assert protocol["source"]["files_sha256"][path] == sha256((ROOT / path).read_bytes()).hexdigest()
    assert "scripts/live_buffer_supervision.py" not in protocol["source"]["files_sha256"]
    with pytest.raises(FileExistsError):
        module.prepare_performance(output)


@pytest.fixture(scope="module")
def complete_session(tmp_path_factory):
    """One full 120-observe baseline, copied before every destructive reseal."""
    return execute(tmp_path_factory.mktemp("complete-live-buffer-synthetic"))


def test_success_exact_continuous_callback_and_queue_schedule(tmp_path):
    module, output, engine = execute(tmp_path)
    events = rows(output)
    obs = events[1:-1]
    assert len(engine.calls) == 120 and engine.brain.sim_ms == 60000
    assert engine.installs == [list(range(256))]
    assert len(events) == 122
    assert [len(row["queue_before"]) for row in obs[:2]] == [2, 0]
    assert [q["request"]["sequence"] for q in obs[0]["queue_after"]] == [2, 3, 4, 5]
    assert obs[40]["queue_after"][0]["request"]["sequence"] == 6
    assert [obs[i]["stimulus"] for i in (0, 39, 40, 79, 80, 119)] == ["A", "A", "B", "B", "black", "black"]
    assert all(len(row["cells"]["counts"]) == 50 and len(row["cells"]["window_counts"]) == 5 for row in obs)
    summary = module.inspect_performance(output)
    assert summary == json.loads((output / "summary.json").read_bytes())
    assert summary["engine_mode"] == "injected-test-factory"
    assert summary["bounds_correct"] is True and summary["observed_handoffs_before_deadline"] is True
    assert summary["resource_validity"] == "conditional-on-separately-reviewed-supervisor-receipt"
    assert summary["proposals"] == []
    assert summary["ring"] == {"total_bins": 6000, "valid_length": 1000, "write_position": 0, "evictions": 5000}
    assert summary["final_ring_sha256"] == obs[-1]["ring_sha256"]
    digest = sha256(b"market-live-cell-ring/v1\ncounts=|u1;shape=1000,256\n"
                    b"observation_index,bin_index,start_tick,end_tick=<i8;shape=1000\n")
    digest.update(struct.pack("<QQ", 1000, 0))
    for values in ([j // 50 for j in range(5000, 6000)], [j % 50 for j in range(5000, 6000)],
                   [j * 100 for j in range(5000, 6000)], [(j + 1) * 100 for j in range(5000, 6000)]):
        digest.update(struct.pack("<1000q", *values))
    for j in range(5000, 6000):
        counts = bytearray(256)
        counts[2] = int(j % 50 == 0)
        digest.update(counts)
    assert summary["final_ring_sha256"] == digest.hexdigest()
    with pytest.raises(ValueError):
        module.run_performance(output, expected_protocol_sha256=sha256((output / "protocol.json").read_bytes()).hexdigest(),
                               engine_factory=lambda: pytest.fail("Must not create another engine"),
                               header_builder=fixture_header)


@pytest.mark.parametrize("age", [299999, 300000, 300001])
def test_deadline_and_c_admitted_after_expired_b(tmp_path, age):
    # Clock call order is deliberately not assumed: engine progress drives the real-boundary fixture.
    module, output, engine, digest, _ = setup(tmp_path)
    now, offered, boundary_reads = 1000, None, 0
    def clock():
        nonlocal now, offered, boundary_reads
        now += 10
        if len(engine.calls) == 1 and offered is None:
            offered = now
        if len(engine.calls) == 40:
            boundary_reads += 1
            now = offered + age - (4 - boundary_reads) * 10
        return now
    module.run_performance(output, expected_protocol_sha256=digest, engine_factory=lambda: engine,
                           header_builder=fixture_header, clock_ms=clock)
    obs = rows(output)[1:-1]
    transition = obs[40]["queue_before"][-1]
    assert transition["status"] == ("handed_off" if age < 300000 else "expired")
    assert obs[40]["input_version"].endswith("B" if age < 300000 else "expiry-black")
    assert obs[40]["queue_after"][0]["request"]["sequence"] == 6
    assert obs[80]["queue_before"][-1]["status"] == "handed_off"
    assert module.inspect_performance(output)["observed_handoffs_before_deadline"] is (age < 300000)


@pytest.mark.parametrize("bad", ["callback", "partial", "missing_total"])
def test_invalid_observer_or_telemetry_retains_partial_attempt(tmp_path, bad):
    module, output, engine, digest, _ = setup(tmp_path)
    engine.bad = bad
    with pytest.raises((ValueError, RuntimeError)):
        module.run_performance(output, expected_protocol_sha256=digest, engine_factory=lambda: engine,
                               header_builder=fixture_header)
    assert (output / "run/events.jsonl").is_file()
    assert not (output / "receipt.json").exists()
    with pytest.raises((ValueError, FileNotFoundError)):
        module.inspect_performance(output)


@pytest.mark.parametrize("problem", ["cell", "population", "window", "ring", "queue", "sequence", "clock",
    "identity", "source", "header", "edge", "soma", "mandatory", "total", "missing_total", "driver", "sample",
    "terminal", "extra", "missing", "setup", "timing", "metadata"])
def test_resealed_false_semantics_rejected(tmp_path, problem, complete_session):
    module, original, _ = complete_session
    output = tmp_path / "mutant"
    shutil.copytree(original, output)
    def mutate(metadata, events):
        event = events[1]
        declaration = metadata["performance"]
        if problem == "cell": event["cells"]["counts"][0][0] = 1
        elif problem == "population": event["telemetry"]["bins"][0]["group_spikes"]["kc"] = 0
        elif problem == "window": event["cells"]["window_counts"][0][2] += 1
        elif problem == "ring": event["ring"]["valid_length"] += 1
        elif problem == "queue": event["queue_after"][1]["status"] = "admitted"
        elif problem == "sequence": event["queue_after"][2]["request"]["sequence"] = 3
        elif problem == "clock": event["wall_completion_ms"] = event["wall_start_ms"] - 1
        elif problem == "identity":
            metadata["engine_identity"]["sha256"] = "0" * 64
            declaration["header"]["engine_identity"] = deepcopy(metadata["engine_identity"])
            for observation in events[1:-1]:
                observation["telemetry"]["engine_identity"] = deepcopy(metadata["engine_identity"])
        elif problem == "source": declaration["header"]["source"]["annotations_sha256"] = "0" * 64
        elif problem == "header": declaration["header"]["cells"][1]["source_id"] = 1000
        elif problem == "edge": declaration["header"]["topology"]["edges"][0][1] = 256
        elif problem == "soma": declaration["header"]["cells"][0]["soma"] = [1, True, 3]
        elif problem == "mandatory": declaration["header"]["cells"][0]["groups"] = ["kc"]
        elif problem == "total": event["telemetry"]["total_spikes"] = 0
        elif problem == "missing_total": event["telemetry"].pop("total_spikes")
        elif problem == "driver": event["readout_result"]["reason"] = "fake"
        elif problem == "sample": event["motor_sample"]["session_id"] = "0" * 32
        elif problem == "terminal": events[-1]["complete_state_sha256"] = "0" * 64
        elif problem == "extra": events.insert(-1, deepcopy(events[-2]))
        elif problem == "missing": events.pop(3)
        elif problem == "setup": declaration["setup"]["header_end_ms"] = -1
        elif problem == "timing": event["sink_body"]["calls"] = 0
        elif problem == "metadata": metadata["seeds"] = [1]
        if problem in {"source", "header", "edge", "soma", "mandatory"}:
            declaration["header_sha256"] = sha256(artifacts._canonical(declaration["header"])).hexdigest()
    reseal(output, mutate)
    with pytest.raises((ValueError, StopIteration)):
        module.inspect_performance(output)


def test_native_authority_and_forbidden_inspect(tmp_path, monkeypatch):
    module, output, _ = execute(tmp_path)
    monkeypatch.setattr(module.FlyEngine, "from_prepared_graph", lambda: pytest.fail("native construction"))
    monkeypatch.setattr(module, "build_header", lambda *a: pytest.fail("header join"))
    monkeypatch.setattr(socket, "socket", lambda *a, **k: pytest.fail("network"))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("subprocess"))
    assert module.inspect_performance(output)["bounds_correct"]
    new = tmp_path / "native"
    module.prepare_performance(new)
    digest = sha256((new / "protocol.json").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="supervision"):
        module.run_performance(new, expected_protocol_sha256=digest)
    with pytest.raises(ValueError):
        module.run_performance(new, expected_protocol_sha256=digest, clock_ms=lambda: 0)


def test_protocol_strict_bounds_and_summary_cap(tmp_path, monkeypatch):
    module, output, _ = execute(tmp_path)
    assert module.READ_LIMITS.max_events == 122 and module.READ_LIMITS.max_checkpoints == 2
    assert module.READ_LIMITS.max_event_line_bytes == 1024**2
    monkeypatch.setattr(module, "MAX_SUMMARY_BYTES", 1)
    with pytest.raises(ValueError, match="summary"):
        module.inspect_performance(output)
    (output / "protocol.json").write_bytes(b" " * (2 * 1024**2 + 1))
    with pytest.raises(ValueError):
        module.inspect_performance(output)


def test_static_header_rejects_boolean_population_count_without_runtime(tmp_path):
    module, _, engine, _, protocol = setup(tmp_path)
    header = fixture_header(engine.identity(), None)
    header["selection"]["group_selected_counts"]["pam11"] = True
    with pytest.raises(ValueError):
        module._header(header, engine.identity(), protocol)


def test_event_iterator_is_closed_on_semantic_failure(complete_session, monkeypatch):
    module, output, _ = complete_session
    original_verify, streams, snapshots = artifacts.verify_run, [], []
    def verify(*args, **kwargs):
        snapshots.append(Path(args[0]))
        result = original_verify(*args, **kwargs)
        class Wrapped:
            manifest = result.manifest
            verification_mode = result.verification_mode
            def iter_events(self):
                stream = result.iter_events()
                streams.append(stream)
                return stream
        return Wrapped()
    monkeypatch.setattr(artifacts, "verify_run", verify)
    def fail(run, protocol, protocol_hash, events):
        next(events)
        raise ValueError("synthetic retained semantic exception")
    monkeypatch.setattr(module, "_summarize", fail)
    with pytest.raises(ValueError, match="retained semantic") as caught:
        module.inspect_performance(output)
    assert len(streams) == 1 and streams[0].gi_frame is None
    assert caught.value.__traceback__ is not None and all(not p.exists() for p in snapshots)


@pytest.mark.parametrize("limit", ["max_event_line_bytes", "max_events_bytes", "max_events", "max_checkpoints"])
def test_snapshot_and_stream_parser_caps_are_enforced(complete_session, monkeypatch, limit):
    module, output, _ = complete_session
    monkeypatch.setattr(module, "READ_LIMITS", replace(module.READ_LIMITS, **{limit: 1}))
    with pytest.raises(ValueError):
        module.inspect_performance(output)


def test_full_eof_garbage_rejected(tmp_path, complete_session):
    module, original, _ = complete_session
    output = tmp_path / "eof"
    shutil.copytree(original, output)
    with (output / "run/events.jsonl").open("ab") as stream:
        stream.write(b'{"trailing":"garbage"}\n')
    with pytest.raises(ValueError):
        module.inspect_performance(output)


def test_checkpoint_cap_is_enforced(complete_session, monkeypatch):
    module, output, _ = complete_session
    monkeypatch.setattr(module, "MAX_CHECKPOINT_BYTES", 1)
    with pytest.raises(ValueError):
        module.inspect_performance(output)


@pytest.mark.parametrize("cost", ["copy", "sink"])
def test_resealed_timing_cannot_exceed_enclosing_wall_interval(tmp_path, complete_session, cost):
    module, original, _ = complete_session
    output = tmp_path / "false-cost"
    shutil.copytree(original, output)
    def mutate(metadata, events):
        if cost == "copy":
            events[1]["copy_aggregation_ns"] = 2**63 - 1
        else:
            for i, event in enumerate(events[1:-1]):
                event["sink_body"].update(total_ns=(i + 1) * 10**12, max_ns=10**12)
    reseal(output, mutate)
    with pytest.raises(ValueError, match="timing|duration"):
        module.inspect_performance(output)


@pytest.mark.parametrize("case", ["delayed-support", "open-price", "reset"])
def test_pending_state_matches_actual_decoder_history_and_reset_prefix(tmp_path, case):
    module, output, engine, digest, _ = setup(tmp_path)
    if case == "delayed-support":
        engine.motor_counts[-4:] = [(5, 0)] * 4
    elif case == "open-price":
        engine.motor_counts[-16:] = [(5, 0)] * 16
    else:
        engine.motor_counts[-8:] = [(5, 0)] * 8
    ticks, reads = itertools.count(1000, 10), 0
    offset = 0
    def clock():
        nonlocal reads, offset
        if len(engine.calls) == 118:
            reads += 1
            if reads == 2 and case == "reset":
                offset = 6000
        return next(ticks) + offset
    module.run_performance(output, expected_protocol_sha256=digest, engine_factory=lambda: engine,
                           header_builder=fixture_header, clock_ms=clock)
    summary = module.inspect_performance(output)
    pending = summary["final_pending_state"]
    assert "input_history" in pending, "Full reconstructed decoder state must be detached and reported"
    observations = rows(output)[1:-1]
    decoder = module._decoder()
    before_reset = None
    for event in observations:
        state = {"decisions": deepcopy(decoder._decisions), "input_history": deepcopy(decoder._history),
                 "partial_block": deepcopy(decoder._block), "path_anchor": deepcopy(decoder._anchor), "armed": decoder._armed}
        result = decoder.consume(event["motor_sample"], now_ms=event["readout_now_ms"])
        if result["status"] == "reset" and result["reason"] == "stale_sample":
            before_reset = state
    assert pending == {**result, "decisions": decoder._decisions, "input_history": decoder._history,
                       "partial_block": decoder._block, "path_anchor": decoder._anchor, "armed": decoder._armed}
    if case == "delayed-support":
        assert [s["observation_index"] for s in pending["input_history"]] == [116, 117, 118, 119]
    elif case == "open-price":
        assert pending["phase"] == "price" and len(pending["decisions"]) == 4
        decoder._history[0]["observation_index"] = 0
        assert pending["input_history"][0]["observation_index"] == 104
    else:
        abandoned = next(p for p in summary["partial_routes"] if p["termination"] == "stale_sample")
        assert abandoned["pending_state"] == before_reset
        assert [s["observation_index"] for s in abandoned["pending_state"]["input_history"]] == list(range(112, 117))
        assert [s["observation_index"] for s in abandoned["pending_state"]["partial_block"]] == [116]
        assert summary["resets"] == [{"observation_index": 117, "reason": "stale_sample"},
                                      {"observation_index": 118, "reason": "sample_gap"}]
        assert [s["observation_index"] for s in pending["partial_block"]] == [119]


@pytest.mark.parametrize("expire_b", [False, True])
def test_c_expiry_and_both_expiry_keep_all_observations(tmp_path, expire_b):
    module, output, engine, digest, _ = setup(tmp_path)
    now, offers, visits = 1000, {}, {40: 0, 80: 0}
    def clock():
        nonlocal now
        now += 10
        calls = len(engine.calls)
        if calls in (1, 41) and calls not in offers:
            offers[calls] = now
        if calls == 80 or (calls == 40 and expire_b):
            visits[calls] += 1
            now = offers[1 if calls == 40 else 41] + 300000 - (4 - visits[calls]) * 10
        return now
    module.run_performance(output, expected_protocol_sha256=digest, engine_factory=lambda: engine,
                           header_builder=fixture_header, clock_ms=clock)
    obs = rows(output)[1:-1]
    assert len(engine.calls) == 120 and engine.brain.sim_ms == 60000
    assert obs[80]["queue_before"][-1]["status"] == "expired"
    assert obs[80]["input_version"] == "phase-3-expiry-black"
    assert all(not frame.any() for frame in engine.calls[80:])
    assert obs[119]["queue_after"] == []
    summary = module.inspect_performance(output)
    assert summary["bounds_correct"] and not summary["observed_handoffs_before_deadline"]
    assert [q["request"]["sequence"] for q in summary["queue_transitions"] if q["status"] == "expired"] == ([2, 6] if expire_b else [6])


@pytest.mark.parametrize("problem", ["source", "version", "duplicate", "extra"])
def test_altered_protocol_is_rejected_before_construction(tmp_path, problem):
    module, output, _, digest, protocol = setup(tmp_path)
    if problem == "source": protocol["source"]["files_sha256"]["scripts/market_live_buffers.py"] = "0" * 64
    elif problem == "version": protocol["version"] = "unsupported"
    raw = artifacts._canonical(protocol) + b"\n"
    if problem == "duplicate": raw = b'{"version":"fake",' + raw[1:]
    if problem == "extra": raw += b"{}"
    (output / "protocol.json").write_bytes(raw)
    with pytest.raises(ValueError):
        module.run_performance(output, expected_protocol_sha256=sha256(raw).hexdigest(),
                               engine_factory=lambda: pytest.fail("engine created"), header_builder=fixture_header)


@pytest.mark.parametrize("field", ["ids", "ptr", "post"])
def test_rehashed_engine_cannot_contradict_authoritative_graph_lock(tmp_path, field):
    module, _, engine, _, protocol = setup(tmp_path)
    identity = engine.identity()
    identity["model_provenance"][f"graph_{field}_sha256"] = "0" * 64
    identity["sha256"] = sha256(artifacts._canonical({k: v for k, v in identity.items() if k != "sha256"})).hexdigest()
    with pytest.raises(ValueError, match="lock"):
        module._header(fixture_header(identity, None), identity, protocol)
