"""Bounded passive-cell/admission performance journal; integrity is not replay."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import re
import struct
import tempfile
import time
from uuid import uuid4

import numpy as np

from fly_connectome_sim.engine import FlyEngine
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.experiment.cell_activity import build_header, LOCKS, GROUPS
from fly_connectome_sim.neural.checkpoint import model_fingerprint
from fly_connectome_sim.neural.common import DATA
from market_artifacts import _copy_bounded, _safe_directory, snapshot_recorded_run, write_json_exclusive
from market_live_buffers import CellRing, ImageAdmission, RING_VERSION, ADMISSION_VERSION

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_live_input_helpers", ROOT / "scripts/run-drive-input-comparison.py")
_input = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_input)
frames, _decoder, _sample, _telemetry = _input.frames, _input._decoder, _input._sample, _input._telemetry
_integer, _hash, _clock, _identity = _input._integer, _input._hash, _input._clock, _input._identity
_file_digest = _input._file_digest

VERSION = "live-buffer-performance/v1"
READ_LIMITS = artifacts.RunReadLimits(max_manifest_bytes=2 * 1024**2, max_event_line_bytes=1024**2,
                                    max_events_bytes=64 * 1024**2, max_events=122, max_checkpoints=2)
MAX_CHECKPOINT_BYTES, MAX_SUMMARY_BYTES = 64 * 1024**2, 8 * 1024**2
EXACT_COUNTS = {"observations": 120, "native_bins": 6000, "windows": 600,
                "events": 122, "checkpoints": 2, "model_ms": 60000}
LIMITATIONS = [
    "Integrity-only inspection is not native replay attestation or scientific qualification.",
    "Offline inspection cannot reproduce KC stride selection, soma-data join or actual graph edges without private runtime arrays/annotations.",
    "The source-bound unchanged build_header performs the actual data join before advance; static topology is not measured transmission.",
    "Self-recorded clocks and sink-body costs are not independent clock or performance attestation.",
    "Resource validity and native throughput remain conditional on a separately reviewed supervisor receipt.",
    "Synthetic injected engines/headers provide software evidence only, never an actual acquisition.",
    "100-model-ms sums are local snapshots, not measured browser publication or 10-Hz wall updates.",
    "Correct expiry establishes bounds, not positive throughput; no admission-rate guarantee for 300 guests or 12 hours.",
    "No price activation, biological learning, semantic recognition or validated motor behavior is established.",
]


def _digest(value):
    return sha256(artifacts._canonical(value)).hexdigest()


def _schedule():
    return [{"observation_index": i, "phase": i // 40 + 1, "start_tick": i * 5000,
             "end_tick": (i + 1) * 5000, "nominal_frame": ("A", "B", "black")[i // 40]}
            for i in range(120)]


def _protocol():
    # Bind every packaged execution member, schemas/locks and imported external helper.
    package = ROOT / "src/fly_connectome_sim"
    sources = [p for p in package.rglob("*") if p.is_file() and p.suffix in (".py", ".cpp", ".json")]
    sources += [ROOT / "scripts" / name for name in (
        "run-live-buffer-performance.py", "market_live_buffers.py", "run-drive-input-comparison.py",
        "run-continuous-motor-probe.py", "market_continuous_drive.py", "market_motor_readout.py", "market_artifacts.py")]
    decoder = _decoder()
    return {"version": VERSION, "scope": "bounded-passive-cell-and-image-admission-engineering-observation",
            "source": {"model_fingerprint": model_fingerprint(), "files_sha256": {
                p.relative_to(ROOT).as_posix(): _file_digest(p) for p in sorted(sources)}},
            "frame_shape": [64, 64, 3], "frame_dtype": "uint8",
            "frame_sha256": {name: _input._rgb_input_sha256(frame) for name, frame in frames().items()},
            "schedule": _schedule(), "observation_ms": 500, "native_bin_ms": 10,
            "root_branch_id": "continuous", "exact_counts": EXACT_COUNTS,
            "decoder": {"configuration": decoder.configuration, "configuration_sha256": decoder.configuration_sha256},
            "observation": {"learning": False, "stimulation": None, "pathway_detail": False,
                            "qualification_detail": False, "passive_dynamics": "normal-engine-defaults"},
            "buffers": {"ring_version": RING_VERSION, "admission_version": ADMISSION_VERSION,
                        "owned_array_bytes": 288000, "export_array_bytes": 17040, "capacity_bins": 1000,
                        "cohort_size": 256, "pending_capacity": 1, "active_capacity": 1, "deadline_ms": 300000,
                        "max_transitions": 16, "max_transitions_per_observation": 8},
            "admission_schedule": {"before_0": ["offer-1-A", "handoff-1"],
                "after_0": ["offer-2-B", "offer-3-A-full", "offer-4-B-full", "offer-5-black-full"],
                "after_39": ["finish-1"], "before_40": ["handoff-or-expire-2"],
                "after_40": ["offer-6-black"], "after_79": ["finish-2-if-active"],
                "before_80": ["handoff-or-expire-6"], "after_119": ["finish-6-if-active"]},
            "limits": {"wall_seconds": 900, "peak_rss_bytes": 4 * 1024**3,
                       "new_output_evidence_scratch_bytes": 256 * 1024**2, "poll_seconds_max": 2,
                       "manifest_bytes": 2 * 1024**2, "metadata_bytes": 2 * 1024**2, "protocol_bytes": 2 * 1024**2,
                       "event_line_bytes": 1024**2, "events_bytes": 64 * 1024**2,
                       "events": 122, "checkpoints": 2, "checkpoint_bytes_each": MAX_CHECKPOINT_BYTES,
                       "summary_bytes_exclusive": 8 * 1024**2}, "verification_mode": "integrity-only"}


def prepare_performance(output_dir: Path):
    output = Path(output_dir).absolute()
    _safe_directory(output.parent)
    protocol = _protocol()
    if len(artifacts._canonical(protocol)) + 1 > READ_LIMITS.max_manifest_bytes:
        raise ValueError("Protocol exceeds byte limit")
    output.mkdir()
    write_json_exclusive(protocol, output / "protocol.json")
    return protocol


def _read_protocol(output, expected=None):
    _safe_directory(output)
    with tempfile.TemporaryDirectory(prefix="fly-live-protocol-") as scratch:
        copy = Path(scratch) / "protocol.json"
        _copy_bounded(output / "protocol.json", copy, READ_LIMITS.max_manifest_bytes)
        raw = copy.read_bytes()
    protocol, digest = artifacts._strict_load(raw), sha256(raw).hexdigest()
    if ((expected is not None and expected != digest) or raw != artifacts._canonical(protocol) + b"\n"
            or artifacts._canonical(protocol) != artifacts._canonical(_protocol())):
        raise ValueError("Prepared protocol/hash/current source differs")
    return protocol, digest


def _read_lock(name, protocol):
    with (LOCKS / name).open("rb") as stream:
        raw = stream.read(READ_LIMITS.max_manifest_bytes + 1)
    if (len(raw) > READ_LIMITS.max_manifest_bytes or sha256(raw).hexdigest()
            != protocol["source"]["files_sha256"].get(f"src/fly_connectome_sim/neural/{name}")):
        raise ValueError("Authoritative lock differs")
    return artifacts._strict_load(raw)


def _header(header, identity, protocol):
    """Static declarations only; no assertion that offline data joins were repeated."""
    populations = _identity(identity, protocol)
    if (type(header) is not dict or set(header) != {"type", "version", "engine_identity", "selection", "cells", "topology", "source"}
            or header["type"] != "header" or header["version"] != "cell-activity-raw/v1"
            or artifacts._canonical(header["engine_identity"]) != artifacts._canonical(identity)):
        raise ValueError("Static header/identity differs")
    source = header["source"]
    if type(source) is not dict or set(source) != {"graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "annotations_sha256"}:
        raise ValueError("Static source fields differ")
    arrays, annotations = _read_lock("arrays.lock.json", protocol), _read_lock("sources.lock.json", protocol)
    for name in ("ids", "ptr", "post"):
        field = f"graph_{name}_sha256"
        if _hash(source[field]) != arrays[name] or source[field] != identity["model_provenance"][field]:
            raise ValueError("Static graph contradicts authoritative locks/engine")
    if _hash(source["annotations_sha256"]) != annotations["annotations.feather"]["sha256"]:
        raise ValueError("Static annotations contradict authoritative lock")
    cells = header["cells"]
    if type(cells) is not list or len(cells) != 256:
        raise ValueError("Exactly 256 static cells required")
    indices, ids, selected = [], [], dict.fromkeys(GROUPS, 0)
    for cell in cells:
        if type(cell) is not dict or set(cell) != {"model_index", "source_id", "groups", "soma"}:
            raise ValueError("Static cell fields differ")
        index, source_id = _integer(cell["model_index"]), _integer(cell["source_id"])
        membership = [name for name in GROUPS if index in populations[name]]
        if not source_id or not membership or cell["groups"] != membership:
            raise ValueError("Static cell population differs")
        if cell["soma"] is not None and (type(cell["soma"]) is not list or len(cell["soma"]) != 3
                or any(type(v) is not int or abs(v) > 2**53 - 1 for v in cell["soma"])):
            raise ValueError("Static soma is not nullable finite measured coordinates")
        indices.append(index)
        ids.append(source_id)
        for name in membership:
            selected[name] += 1
    if len(set(indices)) != 256 or ids != sorted(set(ids)):
        raise ValueError("Duplicate or unsorted static cell IDs")
    _equal(header["selection"], {"method": "mandatory-groups-kc-stride/v1", "limit": 256,
        "group_population_counts": {name: len(populations[name]) for name in GROUPS}, "group_selected_counts": selected},
        "Static selection declaration/types differ")
    if any(selected[name] != len(populations[name]) for name in GROUPS if name != "kc"):
        raise ValueError("Mandatory population missing from static cohort")
    topology = header["topology"]
    if (type(topology) is not dict or set(topology) != {"method", "limit", "eligible_edges", "edges"}
            or topology["method"] != "induced-directed-edge-stride/v1" or type(topology["limit"]) is not int
            or topology["limit"] != 512 or type(topology["edges"]) is not list
            or len(topology["edges"]) != min(_integer(topology["eligible_edges"]), 512)):
        raise ValueError("Static topology declaration differs")
    edge_ids, order = [], []
    for edge in topology["edges"]:
        if type(edge) is not list or len(edge) != 3:
            raise ValueError("Invalid static edge")
        edge_id, left, right = _integer(edge[0]), _integer(edge[1], 255), _integer(edge[2], 255)
        edge_ids.append(edge_id)
        order.append((ids[left], ids[right], edge_id))
    if len(set(edge_ids)) != len(edge_ids) or order != sorted(order):
        raise ValueError("Duplicate/unsorted static edges")
    return indices


def _row(schedule, frame, expired):
    return {"observation_index": schedule["observation_index"], "start_tick": schedule["start_tick"],
            "end_tick": schedule["end_tick"], "frame": frame,
            "input_version": f"phase-{schedule['phase']}-{'expiry-black' if expired else frame}"}


def _before(queue, index, now, hashes):
    transitions = []
    if index == 0:
        transitions.append(queue.offer(1, hashes["A"], now_ms=now))
    if index in (0, 40, 80):
        transitions.append(queue.handoff(now_ms=now))
    return transitions


def _after(queue, index, now, hashes):
    if index == 0:
        return [queue.offer(sequence, hashes[frame], now_ms=now)
                for sequence, frame in ((2, "B"), (3, "A"), (4, "B"), (5, "black"))]
    if index == 40:
        return [queue.offer(6, hashes["black"], now_ms=now)]
    if index in (39, 79, 119) and queue.active is not None:
        return [queue.finish(queue.active["sequence"], now_ms=now)]
    return []


def _cell_coupling(cells, header, telemetry):
    # Group populations overlap; unique selected union is represented once by the cohort.
    total = _integer(telemetry.get("total_spikes"))
    memberships = {name: [slot for slot, cell in enumerate(header["cells"]) if name in cell["groups"]]
                   for name in GROUPS}
    for counts, group_bin in zip(cells["counts"], telemetry["bins"], strict=True):
        for name, slots in memberships.items():
            selected = sum(counts[slot] for slot in slots)
            population = group_bin["group_spikes"][name]
            full = len(slots) == len(header["engine_identity"]["neural_groups"][name])
            if selected > population or (full and selected != population):
                raise ValueError("Selected-cell/per-bin population mismatch")
    if sum(sum(counts) for counts in cells["counts"]) > total:
        raise ValueError("Selected-cell unique union exceeds required interval total_spikes")


def run_performance(output_dir: Path, *, expected_protocol_sha256: str, engine_factory=None,
                    header_builder=None, clock_ms=None, supervision_directory: Path | None = None,
                    expected_readiness_sha256: str | None = None, start_token: str | None = None):
    if engine_factory is None and (clock_ms is not None or header_builder is not None):
        raise ValueError("Injected header/clock requires an injected test engine")
    output = Path(output_dir).absolute()
    _hash(expected_protocol_sha256)
    _read_protocol(output, expected_protocol_sha256)
    if engine_factory is not None:
        if header_builder is None:
            raise ValueError("Injected tests require an explicit synthetic header builder")
        return _run(output, expected_protocol_sha256, engine_factory, header_builder, clock_ms, "injected-test-factory")
    if supervision_directory is None or expected_readiness_sha256 is None or start_token is None:
        raise ValueError("Production requires all supervision bindings")
    # Task3 supplies authority; prepare and inspect never import or enter it.
    from live_buffer_supervision import production_start

    with production_start(output, expected_protocol_sha256, supervision_directory, expected_readiness_sha256, start_token):
        return _run(output, expected_protocol_sha256, FlyEngine.from_prepared_graph, build_header, None, "native-supervised")


def _run(output, expected, engine_factory, header_builder, clock_ms, mode):
    if set(p.name for p in output.iterdir()) != {"protocol.json"}:
        raise ValueError("Run requires exactly a fresh protocol; no resume/retry")
    protocol, protocol_hash = _read_protocol(output, expected)
    clock = clock_ms if clock_ms is not None else lambda: time.monotonic_ns() // 1000000
    setup = {"engine_start_ms": _integer(clock())}
    engine = engine_factory()
    setup["engine_end_ms"] = _integer(clock())
    identity = engine.identity()
    _identity(identity, protocol)
    setup["header_start_ms"] = _integer(clock())
    header = header_builder(identity, DATA)
    setup["header_end_ms"] = _integer(clock())
    indices = _header(header, identity, protocol)
    _clock(float(engine.brain.sim_ms), 0)
    ring, queue, decoder = CellRing(), ImageAdmission(), _decoder()
    engine.configure_cell_observer(indices, ring)
    setup["observer_ready_ms"] = _integer(clock())
    if list(setup.values()) != sorted(setup.values()):
        raise ValueError("Setup wall clock regressed")
    session = uuid4().hex
    declaration = {"protocol": protocol, "protocol_sha256": protocol_hash,
        "configuration_sha256": decoder.configuration_sha256, "session_id": session, "engine_mode": mode,
        "header": header, "header_sha256": _digest(header), "setup": setup}
    metadata = {"engine_identity": identity, "protocol_version": VERSION, "stimulus_version": "continuous-motor-rgb/v1",
                "family": "bounded-live-buffer-performance", "seeds": [], "factors": {},
                "input_sha256": sorted(protocol["frame_sha256"].values()), "performance": declaration}
    if len(artifacts._canonical(metadata)) > READ_LIMITS.max_manifest_bytes:
        raise ValueError("Metadata byte limit exceeded")
    inputs, previous, expired = frames(), setup["observer_ready_ms"], False
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=output) as scratch:
        checkpoint = Path(scratch) / "state.npz"
        with artifacts.RunRecorder(output / "run", run_kind="pilot", metadata=metadata, root_branch_id="continuous") as recorder:
            def save(name, tick):
                nonlocal previous
                if artifacts._canonical(engine.identity()) != artifacts._canonical(identity):
                    raise ValueError("Engine identity changed")
                _clock(float(engine.brain.sim_ms), tick)
                engine.brain.checkpoint(checkpoint)
                if checkpoint.stat().st_size > MAX_CHECKPOINT_BYTES:
                    raise ValueError("Checkpoint byte limit exceeded")
                recorder.ingest_checkpoint(name, checkpoint, origin_branch_id="continuous")
                state = _hash(engine.brain.checkpoint_state_sha256())
                wall = _integer(clock())
                if wall < previous:
                    raise ValueError("Checkpoint wall clock regressed")
                previous = wall
                recorder.append({"type": "checkpoint", "branch_id": "continuous", "sim_ms": tick / 10,
                    "sim_tick": tick, "checkpoint_name": name, "complete_state_sha256": state, "wall_ms": wall})

            save("brain-before.npz", 0)
            for schedule in protocol["schedule"]:
                i, tick = schedule["observation_index"], schedule["start_tick"]
                if artifacts._canonical(engine.identity()) != artifacts._canonical(identity):
                    raise ValueError("Engine identity changed")
                _clock(float(engine.brain.sim_ms), tick)
                start = _integer(clock())
                if start < previous:
                    raise ValueError("Observe wall clock regressed")
                # Deadline check directly precedes dispatch; no other admission work intervenes.
                before = _before(queue, i, start, protocol["frame_sha256"])
                if i in (0, 40, 80):
                    expired = before[-1]["status"] == "expired"
                frame = "black" if expired else schedule["nominal_frame"]
                telemetry = engine.observe(inputs[frame], 500, learning=False, stimulation=None,
                                           pathway_detail=False, qualification_detail=False)
                completion = _integer(clock())
                after = _after(queue, i, completion, protocol["frame_sha256"])
                copy_start = time.perf_counter_ns()
                export = ring.export_observation(i)
                cells = {name: value.tolist() if isinstance(value, np.ndarray) else value for name, value in export.items()}
                copy_ns = time.perf_counter_ns() - copy_start
                totals = _telemetry(telemetry, start=tick, frame=frame, identity=identity, protocol=protocol)
                _cell_coupling(cells, header, telemetry)
                row = _row(schedule, frame, expired)
                sample = _sample(row, totals, protocol_hash=protocol_hash, session_id=session,
                                 wall_start=start, wall_completion=completion, protocol=protocol)
                now = _integer(clock())
                if not start <= completion <= now:
                    raise ValueError("Observation/snapshot wall clock regressed")
                result = decoder.consume(sample, now_ms=now)
                ready = _integer(clock())
                if ready < now:
                    raise ValueError("Snapshot readiness clock regressed")
                previous = ready
                event = {"type": "observe", "branch_id": "continuous", "sim_ms": row["end_tick"] / 10,
                    "observation_index": i, "phase": schedule["phase"], "stimulus": frame, "input_version": row["input_version"],
                    "start_tick": tick, "end_tick": row["end_tick"], "duration_ticks": 5000,
                    "learning": False, "stimulation": None, "pathway_detail": False, "qualification_detail": False,
                    "input_sha256": protocol["frame_sha256"][frame], "telemetry": telemetry, "cells": cells,
                    "wall_start_ms": start, "wall_completion_ms": completion, "snapshot_ready_ms": ready,
                    "copy_aggregation_ns": copy_ns, "sink_body": {"calls": ring.sink_body_calls,
                        "total_ns": ring.sink_body_total_ns, "max_ns": ring.sink_body_max_ns},
                    "ring": ring.stats, "ring_sha256": ring.ring_sha256(),
                    "queue_before": before, "queue_after": after, "queue_state": queue.state,
                    "motor_sample": sample, "readout_now_ms": now, "readout_result": result}
                if i == 119:
                    event["complete_state_sha256_after"] = _hash(engine.brain.checkpoint_state_sha256())
                if len(artifacts._canonical(event)) + 1 > READ_LIMITS.max_event_line_bytes:
                    raise ValueError("Observation event line byte limit exceeded")
                recorder.append(event)
            save("brain-after.npz", 600000)
    summary = inspect_performance(output)
    write_json_exclusive(summary, output / "summary.json")
    receipt = {"version": VERSION, "status": "complete", "verification_mode": "integrity-only",
        "scope": "execution-and-offline-integrity-bookkeeping", "protocol_sha256": protocol_hash,
        "summary_sha256": _file_digest(output / "summary.json"), "source": summary["source"],
        "exact_counts": EXACT_COUNTS, "final_state_sha256": summary["final_state_sha256"]}
    write_json_exclusive(receipt, output / "receipt.json")
    return receipt


def _checkpoint(event, name, tick):
    fields = artifacts.OWNED | {"type", "branch_id", "sim_ms", "sim_tick", "checkpoint_name",
                              "complete_state_sha256", "checkpoint_sha256", "checkpoint_size", "wall_ms"}
    if (set(event) != fields or event["type"] != "checkpoint" or event["branch_id"] != "continuous"
            or event["checkpoint_name"] != name or _integer(event["sim_tick"]) != tick):
        raise ValueError("Checkpoint order/fields differ")
    _clock(event["sim_ms"], tick)
    _integer(event["wall_ms"])
    return _hash(event["complete_state_sha256"])


class _RingAudit:
    """Independent fixed chronological storage/hash, never the producer CellRing."""
    def __init__(self):
        self.columns = [np.zeros(1000, dtype="<i8") for _ in range(4)]
        self.counts = np.zeros((1000, 256), dtype=np.uint8)
        self.total = 0

    def accept(self, cells, observation):
        required = {"observation_index", "observation_indices", "bin_index", "start_tick", "end_tick", "counts",
                    "window_counts", "window_start_tick", "window_end_tick"}
        if type(cells) is not dict or set(cells) != required or type(cells["observation_index"]) is not int or cells["observation_index"] != observation:
            raise ValueError("Raw callback batch fields/index differ")
        for key, size in (("observation_indices", 50), ("bin_index", 50), ("start_tick", 50), ("end_tick", 50),
                          ("counts", 50), ("window_counts", 5), ("window_start_tick", 5), ("window_end_tick", 5)):
            if type(cells[key]) is not list or len(cells[key]) != size:
                raise ValueError("Raw callback batch shape differs")
        for j in range(50):
            expected = (observation, j, self.total * 100, (self.total + 1) * 100)
            values = tuple(_integer(cells[key][j], 2**63 - 1) for key in ("observation_indices", "bin_index", "start_tick", "end_tick"))
            counts = cells["counts"][j]
            if values != expected or type(counts) is not list or len(counts) != 256:
                raise ValueError("Raw callback chronology/count vector differs")
            for count in counts:
                _integer(count, 100)
            position = self.total % 1000
            for column, value in zip(self.columns, values, strict=True):
                column[position] = value
            self.counts[position] = counts
            self.total += 1
        for window in range(5):
            sums = cells["window_counts"][window]
            if type(sums) is not list or len(sums) != 256:
                raise ValueError("Aggregate shape differs")
            for slot, count in enumerate(sums):
                if _integer(count, 1000) != sum(cells["counts"][j][slot] for j in range(window * 10, window * 10 + 10)):
                    raise ValueError("Aggregate count differs")
            if (_integer(cells["window_start_tick"][window]) != observation * 5000 + window * 1000
                    or _integer(cells["window_end_tick"][window]) != observation * 5000 + (window + 1) * 1000):
                raise ValueError("Aggregate model clock differs")

    def stats(self):
        return {"total_bins": self.total, "valid_length": min(self.total, 1000),
                "write_position": self.total % 1000, "evictions": max(self.total - 1000, 0)}

    def digest(self):
        # Literal versioned bytes independently specified; no imported producer prefix/digest.
        digest = sha256(b"market-live-cell-ring/v1\ncounts=|u1;shape=1000,256\n"
                        b"observation_index,bin_index,start_tick,end_tick=<i8;shape=1000\n")
        valid, position = min(self.total, 1000), self.total % 1000
        digest.update(struct.pack("<QQ", valid, position))
        start = position if self.total >= 1000 else 0
        for array in (*self.columns, self.counts):
            digest.update(array[start:valid].tobytes(order="C"))
            digest.update(array[:start].tobytes(order="C"))
        return digest.hexdigest()


class _QueueAudit:
    """Independent minimal finite schedule replay; not ImageAdmission replay."""
    def __init__(self, hashes):
        self.hashes, self.active, self.pending = hashes, None, None
        self.high, self.last, self.transitions = 0, None, []

    def action(self, action, now, sequence=None, frame=None):
        _integer(now, 2**63 - 1)
        if self.last is not None and now < self.last:
            raise ValueError("Admission wall clock regressed")
        self.last = now
        if action == "offer":
            if sequence <= self.high:
                raise ValueError("Admission sequence reused")
            self.high = sequence
            request = {"sequence": sequence, "frame_sha256": self.hashes[frame], "offered_ms": now}
            status = "full" if self.pending is not None else "admitted"
            if status == "admitted":
                self.pending = request
        elif action == "handoff":
            request = self.pending
            if request is None or self.active is not None:
                raise ValueError("Impossible fixed schedule handoff")
            status = "expired" if now - request["offered_ms"] >= 300000 else "handed_off"
            self.pending = None
            if status == "handed_off":
                self.active = request
        else:
            request, status = self.active, "completed"
            if request is None:
                raise ValueError("Impossible fixed schedule finish")
            self.active = None
        result = {"status": status, "request": request, "wall_ms": now}
        self.transitions.append(result)
        return result

    def before(self, i, now):
        result = [self.action("offer", now, 1, "A")] if i == 0 else []
        if i in (0, 40, 80):
            result.append(self.action("handoff", now))
        return result

    def after(self, i, now):
        if i == 0:
            return [self.action("offer", now, sequence, frame)
                    for sequence, frame in ((2, "B"), (3, "A"), (4, "B"), (5, "black"))]
        if i == 40:
            return [self.action("offer", now, 6, "black")]
        return [self.action("finish", now)] if i in (39, 79, 119) and self.active is not None else []

    def state(self):
        return {"active": self.active, "pending": self.pending, "high_watermark": self.high, "last_now_ms": self.last}


def _equal(left, right, message):
    if artifacts._canonical(left) != artifacts._canonical(right):
        raise ValueError(message)


def _pending_state(decoder, result=None):
    """Detach the actual unchanged decoder state, including incomplete blocks."""
    return artifacts._strict_load(artifacts._canonical({**(result or {}), "decisions": decoder._decisions,
        "input_history": decoder._history, "partial_block": decoder._block,
        "path_anchor": decoder._anchor, "armed": decoder._armed}))


def _summarize(run, protocol, protocol_hash, events):
    manifest, metadata = run.manifest, run.manifest["metadata"]
    declaration, decoder = metadata.get("performance"), _decoder()
    if (set(metadata) != artifacts.REQUIRED_METADATA | {"performance"} or manifest["run_kind"] != "pilot"
            or manifest["root_branch_id"] != "continuous" or manifest["event_count"] != 122 or manifest["state_anchors"] != {}
            or metadata["protocol_version"] != VERSION or metadata["stimulus_version"] != "continuous-motor-rgb/v1"
            or metadata["family"] != "bounded-live-buffer-performance" or metadata["seeds"] != [] or metadata["factors"] != {}
            or metadata["input_sha256"] != sorted(protocol["frame_sha256"].values())
            or type(declaration) is not dict or set(declaration) != {"protocol", "protocol_sha256", "configuration_sha256",
                "session_id", "engine_mode", "header", "header_sha256", "setup"}
            or declaration["engine_mode"] not in ("injected-test-factory", "native-supervised")
            or type(declaration["session_id"]) is not str or re.fullmatch(r"[0-9a-f]{32}", declaration["session_id"]) is None
            or declaration["protocol_sha256"] != protocol_hash or declaration["configuration_sha256"] != decoder.configuration_sha256):
        raise ValueError("Metadata/protocol/session/source differs")
    _equal(declaration["protocol"], protocol, "Metadata protocol differs")
    if set(manifest["checkpoints"]) != {"brain-before.npz", "brain-after.npz"}:
        raise ValueError("Exactly two checkpoint files required")
    identity, header, setup = metadata["engine_identity"], declaration["header"], declaration["setup"]
    _header(header, identity, protocol)
    if _hash(declaration["header_sha256"]) != _digest(header):
        raise ValueError("Full static header hash differs")
    setup_keys = ("engine_start_ms", "engine_end_ms", "header_start_ms", "header_end_ms", "observer_ready_ms")
    if type(setup) is not dict or set(setup) != set(setup_keys):
        raise ValueError("Setup timings differ")
    clocks = [_integer(setup[key]) for key in setup_keys]
    if clocks != sorted(clocks):
        raise ValueError("Setup clock regressed")
    def take():
        event = next(events, None)
        if event is None:
            raise ValueError("Missing scheduled event")
        return event
    initial_event = take()
    initial_state = _checkpoint(initial_event, "brain-before.npz", 0)
    previous = initial_event["wall_ms"]
    if previous < setup["observer_ready_ms"]:
        raise ValueError("Initial checkpoint precedes setup")
    ring, queue = _RingAudit(), _QueueAudit(protocol["frame_sha256"])
    proposals, partials, resets = [], [], []
    statuses, reasons, coverage, direction_counts = Counter(), Counter(), Counter(), Counter()
    processing, delivery, gaps, ready_gaps, ready_latency, copying, sink_deltas, compute, kernel = [], [], [], [], [], [], [], [], []
    prior_sink = {"calls": 0, "total_ns": 0, "max_ns": 0}
    expired, last_ready, last_event, final_result = False, None, None, None
    fields = artifacts.OWNED | {"type", "branch_id", "sim_ms", "observation_index", "phase", "stimulus", "input_version",
        "start_tick", "end_tick", "duration_ticks", "learning", "stimulation", "pathway_detail", "qualification_detail",
        "input_sha256", "telemetry", "cells", "wall_start_ms", "wall_completion_ms", "snapshot_ready_ms",
        "copy_aggregation_ns", "sink_body", "ring", "ring_sha256", "queue_before", "queue_after", "queue_state",
        "motor_sample", "readout_now_ms", "readout_result"}
    for schedule in protocol["schedule"]:
        event, i = take(), schedule["observation_index"]
        if set(event) != fields | ({"complete_state_sha256_after"} if i == 119 else set()):
            raise ValueError("Observation fields differ")
        start, completion, now, ready = [_integer(event[key]) for key in
            ("wall_start_ms", "wall_completion_ms", "readout_now_ms", "snapshot_ready_ms")]
        if not previous <= start <= completion <= now <= ready:
            raise ValueError("Observation/snapshot clock regressed")
        before = queue.before(i, start)
        if i in (0, 40, 80):
            expired = before[-1]["status"] == "expired"
        frame = "black" if expired else schedule["nominal_frame"]
        after = queue.after(i, completion)
        _equal(event["queue_before"], before, "Before-observe admission transition differs")
        _equal(event["queue_after"], after, "After-observe admission transition differs")
        _equal(event["queue_state"], queue.state(), "Bounded admission state differs")
        if len(before) + len(after) > 8 or len(queue.transitions) > 16:
            raise ValueError("Admission transition cap exceeded")
        row = _row(schedule, frame, expired)
        fixed = {"type": "observe", "branch_id": "continuous", "sim_ms": row["end_tick"] / 10,
            "observation_index": i, "phase": schedule["phase"], "stimulus": frame, "input_version": row["input_version"],
            "start_tick": row["start_tick"], "end_tick": row["end_tick"], "duration_ticks": 5000,
            "learning": False, "stimulation": None, "pathway_detail": False, "qualification_detail": False,
            "input_sha256": protocol["frame_sha256"][frame]}
        _equal({key: event[key] for key in fixed}, fixed, "Fixed observation schedule/frame differs")
        totals = _telemetry(event["telemetry"], start=row["start_tick"], frame=frame, identity=identity, protocol=protocol)
        ring.accept(event["cells"], i)
        _cell_coupling(event["cells"], header, event["telemetry"])
        _equal(event["ring"], ring.stats(), "Ring transition differs")
        if _hash(event["ring_sha256"]) != ring.digest():
            raise ValueError("Independent chronological ring hash differs")
        sink = event["sink_body"]
        if type(sink) is not dict or set(sink) != {"calls", "total_ns", "max_ns"}:
            raise ValueError("Sink timing fields differ")
        calls, total, maximum = [_integer(sink[k], 2**63 - 1) for k in ("calls", "total_ns", "max_ns")]
        delta = total - prior_sink["total_ns"]
        if (calls != (i + 1) * 50 or delta < 0 or maximum < prior_sink["max_ns"]
                or maximum > total or delta > 50 * maximum
                or (maximum > prior_sink["max_ns"] and delta < maximum)):
            raise ValueError("Sink timing/callback counters differ")
        copy_ns = _integer(event["copy_aggregation_ns"], 2**63 - 1)
        # Integer monotonic-ms timestamps are floored readings. A single interval's
        # actual duration can exceed its floored endpoint difference by <1 ms.
        if delta > (completion - start + 1) * 1000000 or copy_ns > (now - completion + 1) * 1000000:
            raise ValueError("Self-recorded timing duration exceeds enclosing wall interval plus 1 ms quantization")
        sample = _sample(row, totals, protocol_hash=protocol_hash, session_id=declaration["session_id"],
                         wall_start=start, wall_completion=completion, protocol=protocol)
        _equal(event["motor_sample"], sample, "Motor sample differs")
        pending_before = _pending_state(decoder)
        result = decoder.consume(sample, now_ms=now)
        _equal(event["readout_result"], result, "Continuous driver result differs")
        statuses[result["status"]] += 1
        reasons[result["reason"]] += 1
        if result["status"] == "direction":
            direction_counts[decoder._decisions[-1]["direction"]] += 1
        if result["proposal"] is not None:
            proposals.append(result["proposal"])
            coverage[result["proposal"]["drink_id"]] += 1
        elif result["status"] == "reset":
            resets.append({"observation_index": i, "reason": result["reason"]})
            partials.append({"termination": result["reason"], "observation_index": i, "pending_state": pending_before})
        processing.append(completion - start)
        delivery.append(now - completion)
        gaps.append(start - previous)
        if last_ready is not None:
            ready_gaps.append(ready - last_ready)
        ready_latency.append(ready - completion)
        copying.append(copy_ns)
        sink_deltas.append(delta)
        compute.append(event["telemetry"]["compute_seconds"])
        kernel.append(event["telemetry"]["kernel_seconds"])
        prior_sink, previous, last_ready, last_event, final_result = sink, ready, ready, event, result
    final_event = take()
    final_state = _checkpoint(final_event, "brain-after.npz", 600000)
    if (final_state != _hash(last_event["complete_state_sha256_after"]) or final_event["wall_ms"] < previous
            or next(events, None) is not None):
        raise ValueError("Terminal state/clock/full EOF differs")
    pending = _pending_state(decoder, final_result)
    if decoder._decisions or decoder._block or decoder._anchor is not None:
        partials.append({"termination": "end-of-observation-pending", "pending_state": _pending_state(decoder)})
    handoffs = [q for q in queue.transitions if q["status"] == "handed_off"]
    positive = {q["request"]["sequence"] for q in handoffs} == {1, 2, 6}
    return {"version": VERSION, "validity": "complete-integrity-and-semantics-only",
        "verification_mode": run.verification_mode, "engine_mode": declaration["engine_mode"], "protocol_sha256": protocol_hash,
        "configuration_sha256": decoder.configuration_sha256, "session_id": declaration["session_id"],
        "source": {name: manifest[name] for name in ("schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256")},
        "exact_counts": EXACT_COUNTS, "initial_state_sha256": initial_state, "final_state_sha256": final_state,
        "header_sha256": declaration["header_sha256"], "bounds_correct": True,
        "observed_handoffs_before_deadline": positive,
        "resource_validity": "conditional-on-separately-reviewed-supervisor-receipt",
        "outcome": "observed-handoffs-resource-review-required" if positive else "correct-expiry-not-positive-throughput",
        "ring": ring.stats(), "final_ring_sha256": ring.digest(), "owned_array_bytes": 288000,
        "queue_transitions": queue.transitions, "queue_final_state": queue.state(),
        "queue_waits_ms": [{"sequence": q["request"]["sequence"], "status": q["status"],
            "wait_ms": q["wall_ms"] - q["request"]["offered_ms"]} for q in queue.transitions if q["status"] in ("handed_off", "expired")],
        "proposals": proposals, "partial_routes": partials, "resets": resets, "final_pending_state": pending,
        "direction_counts": {name: direction_counts[name] for name in ("lower", "upper")},
        "status_counts": dict(statuses), "reason_counts": dict(reasons),
        "observed_coverage": {drink["id"]: coverage[drink["id"]] for drink in decoder.configuration["drinks"]},
        "setup": setup, "timing": {"engine_start_through_final_checkpoint_ms": final_event["wall_ms"] - setup["engine_start_ms"],
            "engine_setup_ms": setup["engine_end_ms"] - setup["engine_start_ms"],
            "header_setup_ms": setup["header_end_ms"] - setup["header_start_ms"],
            "observation_ms": processing, "local_delivery_ms": delivery, "between_observation_ms": gaps,
            "snapshot_ready_gap_ms": ready_gaps, "snapshot_ready_after_completion_ms": ready_latency, "copy_aggregation_ns": copying,
            "sink_body_delta_ns": sink_deltas, "sink_body_final": prior_sink,
            "compute_seconds": compute, "kernel_seconds": kernel, "authenticated": False}, "limitations": LIMITATIONS}


def inspect_performance(output_dir: Path):
    """Bounded immutable snapshot, complete EOF; no engine/runtime/network reads."""
    output = Path(output_dir).absolute()
    protocol, protocol_hash = _read_protocol(output)
    with snapshot_recorded_run(output / "run", limits=READ_LIMITS, checkpoint_byte_limit=MAX_CHECKPOINT_BYTES) as snapshot:
        run = artifacts.verify_run(snapshot, limits=READ_LIMITS)
        with closing(run.iter_events()) as events:
            summary = _summarize(run, protocol, protocol_hash, events)
    if len(artifacts._canonical(summary)) + 1 >= MAX_SUMMARY_BYTES:
        raise ValueError("Derived summary exceeds strict byte bound")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run", "inspect"):
        command = commands.add_parser(name)
        command.add_argument("--output-dir", type=Path, required=True)
        if name == "run":
            command.add_argument("--expected-protocol-sha256", required=True)
            command.add_argument("--run-native", action="store_true", required=True)
            command.add_argument("--supervision-directory", type=Path, required=True)
            command.add_argument("--expected-readiness-sha256", required=True)
            command.add_argument("--start-token", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare_performance(args.output_dir)
    elif args.command == "inspect":
        result = inspect_performance(args.output_dir)
    else:
        result = run_performance(args.output_dir, expected_protocol_sha256=args.expected_protocol_sha256,
            supervision_directory=args.supervision_directory, expected_readiness_sha256=args.expected_readiness_sha256,
            start_token=args.start_token)
    print(artifacts._canonical(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
