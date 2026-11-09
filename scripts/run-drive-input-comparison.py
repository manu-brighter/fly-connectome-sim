"""Fixed restored-state visual comparison; integrity-only, never price activation."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import importlib.util
from pathlib import Path
import re
import tempfile
import time
from uuid import uuid4

import numpy as np

from fly_connectome_sim.engine import FlyEngine, _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.experiment.cell_activity import LOCKS
from fly_connectome_sim.neural.checkpoint import model_fingerprint, raw_array_sha256
from market_artifacts import _copy_bounded, _safe_directory, snapshot_recorded_run, write_json_exclusive
from market_continuous_drive import ContinuousMotorDrive


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_fixed_probe_helpers", ROOT / "scripts/run-continuous-motor-probe.py")
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)
# These frozen helpers validate no schedule/version-specific probe fields.
_identity, _telemetry, _sample = _shared._identity, _shared._telemetry, _shared._sample
_integer, _hash, _clock = _shared._integer, _shared._hash, _shared._clock
_file_digest = _shared._file_digest

VERSION = "drive-input-comparison/v1"
ARMS = (("control-black", "black"), ("image-a", "A"), ("image-b", "B"), ("image-a-repeat", "A"))
BINDING = {"retina": (3335,), "uv": (3335, 2), "r8": (811,), "r8_uv": (811, 2), "r8_channel": (811,)}
READ_LIMITS = artifacts.RunReadLimits(max_manifest_bytes=2 * 1024**2, max_event_line_bytes=1024**2,
                                    max_events_bytes=64 * 1024**2, max_events=175, max_checkpoints=3)
MAX_CHECKPOINT_BYTES, MAX_SUMMARY_BYTES = 64 * 1024**2, 8 * 1024**2
EXACT_COUNTS = {"observations": 168, "native_bins": 8400, "events": 175, "checkpoints": 3,
                "branch_starts": 4, "actual_advance_ms": 84000, "branch_endpoint_ms": 24000}
CLOCK_RESETS = {"stale_sample", "old_transition", "source_session_changed", "sample_out_of_order", "sample_gap",
                "path_expired", "before_boundary", "history_limit"}
LIMITATIONS = [
    "Integrity-only reconstruction is not native replay attestation or scientific qualification.",
    "Consistently rewritten and resealed monotonic clocks are not independently authenticated.",
    "Optical samples precede filtering/current mapping; they are not injected currents or neural responses.",
    "Synthetic factories provide software evidence only; they never attest a native acquisition.",
    "A proposal does not activate a price. No semantic recognition, biological learning or arbitrary-image claim.",
    "Technical mapping reachability is separate from observed target/price coverage; Stage C remains open.",
    "Live display, upload/load, price service and rehearsal remain unqualified.",
    "Resource limits are observed supervisor stop thresholds, not hard quotas or process-tree RSS.",
]


def frames() -> dict[str, np.ndarray]:
    y, x = np.indices((64, 64))
    a = np.repeat((255 * ((x < 32) == (y < 32))).astype(np.uint8)[..., None], 3, axis=2)
    return {"black": np.zeros((64, 64, 3), dtype=np.uint8), "A": a, "B": 255 - a}


def _decoder() -> ContinuousMotorDrive:
    decoder = ContinuousMotorDrive([
        {"id": f"drink-{i:02d}", "minimum_rappen": 400, "maximum_rappen": 700, "grid_rappen": 50}
        for i in range(20)], max_sample_age_ms=5000)
    if decoder.configuration_sha256 != "c02ca9be4db5198b46e718116ff80c169aa3d051f29ff7703d27f1f4fd5315c5":
        raise ValueError("Frozen continuous-drive configuration differs")
    return decoder


def _schedule() -> list[dict]:
    result = []
    for branch, frame, count, offset in (("prefix", "black", 8, 0), *((arm, frame, 40, 40000) for arm, frame in ARMS)):
        result.extend({"branch_id": branch, "frame": frame, "observation_index": i,
                       "start_tick": offset + i * 5000, "end_tick": offset + (i + 1) * 5000,
                       "input_version": f"{branch}-{frame}"} for i in range(count))
    return result


def _protocol() -> dict:
    sources = [Path(__file__).resolve(), ROOT / "scripts/run-continuous-motor-probe.py",
               ROOT / "scripts/market_continuous_drive.py", ROOT / "scripts/market_motor_readout.py",
               ROOT / "scripts/market_artifacts.py", ROOT / "scripts/market_supervision.py",
               ROOT / "scripts/supervise-market-response.ps1", ROOT / "src/fly_connectome_sim/experiment/recorder.py",
               ROOT / "src/fly_connectome_sim/neural/datasets.json"]
    sources.extend(sorted((ROOT / "src/fly_connectome_sim/schemas").glob("*.json")))
    hashes = {p.relative_to(ROOT).as_posix(): _file_digest(p) for p in sources}
    hashes.update({f"src/fly_connectome_sim/neural/{p.name}": _file_digest(p) for p in sorted(LOCKS.glob("*.lock.json"))})
    decoder = _decoder()
    return {"version": VERSION, "scope": "fixed-input-restored-state-engineering-observation",
            "source": {"model_fingerprint": model_fingerprint(), "files_sha256": hashes},
            "frame_shape": [64, 64, 3], "frame_dtype": "uint8",
            "frame_sha256": {name: _rgb_input_sha256(frame) for name, frame in frames().items()},
            "arms": [{"id": arm, "frame": frame} for arm, frame in ARMS], "schedule": _schedule(),
            "prefix_ms": 4000, "arm_ms": 20000, "observation_ms": 500, "native_bin_ms": 10,
            "root_branch_id": "prefix", "exact_counts": EXACT_COUNTS,
            "decoder": {"configuration": decoder.configuration, "configuration_sha256": decoder.configuration_sha256},
            "observation": {"learning": False, "stimulation": None, "pathway_detail": False,
                            "qualification_detail": False, "passive_dynamics": "normal-engine-defaults"},
            "projection": {"kind": "optical-before-filtering-and-current-mapping", "maximum_vector_values": 10000,
                           "vector_counts": {"r1_r6": 3335, "r8": 811}, "hash_dtype": "float64", "hash_order": "C"},
            "limits": {"wall_seconds": 900, "peak_rss_bytes": 4 * 1024**3,
                       "new_output_evidence_scratch_bytes": 256 * 1024**2, "poll_seconds_max": 2,
                       "manifest_bytes": READ_LIMITS.max_manifest_bytes, "protocol_bytes": 2 * 1024**2,
                       "event_line_bytes": READ_LIMITS.max_event_line_bytes, "events_bytes": READ_LIMITS.max_events_bytes,
                       "events": 175, "checkpoints": 3, "checkpoint_bytes_each": MAX_CHECKPOINT_BYTES,
                       "summary_bytes_exclusive": MAX_SUMMARY_BYTES}, "verification_mode": "integrity-only"}


def prepare_comparison(output_dir: Path) -> dict:
    output = Path(output_dir).absolute()
    _safe_directory(output.parent)
    protocol = _protocol()
    output.mkdir()
    write_json_exclusive(protocol, output / "protocol.json")
    return protocol


def _read_protocol(output: Path, expected: str | None = None) -> tuple[dict, str]:
    _safe_directory(output)
    with tempfile.TemporaryDirectory(prefix="fly-drive-protocol-") as scratch:
        copy = Path(scratch) / "protocol.json"
        _copy_bounded(output / "protocol.json", copy, READ_LIMITS.max_manifest_bytes)
        raw = copy.read_bytes()
    digest, protocol = sha256(raw).hexdigest(), artifacts._strict_load(raw)
    if ((expected is not None and digest != expected) or raw != artifacts._canonical(protocol) + b"\n"
            or artifacts._canonical(protocol) != artifacts._canonical(_protocol())):
        raise ValueError("Prepared protocol/hash/current source differs")
    return protocol, digest


def _vector(value, count: int) -> dict:
    array = np.asarray(value)
    if (array.shape != (count,) or array.dtype.kind not in "fiu" or count > 10000
            or not np.isfinite(array).all() or np.any(array < 0) or np.any(array > 1)):
        raise ValueError("Projection vector shape/range/finite bound differs")
    array = np.asarray(array, dtype=np.float64, order="C")
    return {"values": array.tolist(), "shape": [count], "count": count, "minimum": float(array.min()),
            "mean": float(array.mean()), "maximum": float(array.max()), "sum": float(array.sum()),
            "positive_count": int(np.count_nonzero(array > 0)), "sha256": raw_array_sha256(array)}


def _binding(brain, identity: dict) -> dict:
    result = {}
    configuration = identity["model_provenance"].get("configuration_sha256", {})
    for name, shape in BINDING.items():
        array = getattr(brain, name)
        if (not isinstance(array, np.ndarray) or array.shape != shape or array.dtype.hasobject
                or raw_array_sha256(array) != _hash(configuration.get(name))):
            raise ValueError("Actual retinal ordering/configuration differs")
        result[name] = {"sha256": configuration[name], "shape": list(shape), "dtype": array.dtype.str}
    return result


def _project(engine, identity: dict) -> dict:
    _clock(float(engine.brain.sim_ms), 0)
    state = _hash(engine.brain.checkpoint_state_sha256())
    binding = _binding(engine.brain, identity)
    projected = {}
    for name, frame in frames().items():
        values = engine.brain.rgb_drive(frame)
        if type(values) is not dict or set(values) != {"r1_r6", "r8"}:
            raise ValueError("Projection populations differ")
        projected[name] = {key: _vector(values[key], count) for key, count in (("r1_r6", 3335), ("r8", 811))}
        _clock(float(engine.brain.sim_ms), 0)
        if (engine.brain.checkpoint_state_sha256() != state
                or artifacts._canonical(engine.identity()) != artifacts._canonical(identity)
                or _binding(engine.brain, identity) != binding):
            raise ValueError("Projection mutated state/identity/ordering")
    return {"kind": "optical-before-filtering-and-current-mapping", "identity_sha256": identity["sha256"],
            "state_sha256_before": state, "state_sha256_after": state,
            "model_tick_before": 0, "model_tick_after": 0, "binding": binding, "frames": projected}


def _validate_projection(projection: dict, identity: dict) -> None:
    if (type(projection) is not dict or set(projection) != {"kind", "identity_sha256", "state_sha256_before",
            "state_sha256_after", "model_tick_before", "model_tick_after", "binding", "frames"}
            or projection["kind"] != "optical-before-filtering-and-current-mapping"
            or projection["identity_sha256"] != identity["sha256"]
            or _hash(projection["state_sha256_before"]) != _hash(projection["state_sha256_after"])
            or _integer(projection["model_tick_before"]) != 0 or _integer(projection["model_tick_after"]) != 0
            or type(projection["binding"]) is not dict or set(projection["binding"]) != set(BINDING)
            or type(projection["frames"]) is not dict or set(projection["frames"]) != {"black", "A", "B"}):
        raise ValueError("Projection declaration differs")
    for name, shape in BINDING.items():
        record = projection["binding"][name]
        if (type(record) is not dict or set(record) != {"sha256", "shape", "dtype"}
                or artifacts._canonical(record["shape"]) != artifacts._canonical(list(shape))
                or record["sha256"] != _hash(identity["model_provenance"].get("configuration_sha256", {}).get(name))
                or type(record["dtype"]) is not str):
            raise ValueError("Projection ordering/provenance binding differs")
        try:
            dtype = np.dtype(record["dtype"])
        except TypeError as error:
            raise ValueError("Invalid projection binding dtype") from error
        if dtype.kind not in "fiu" or dtype.str != record["dtype"]:
            raise ValueError("Invalid projection binding dtype")
    for frame in projection["frames"].values():
        if type(frame) is not dict or set(frame) != {"r1_r6", "r8"}:
            raise ValueError("Projection vector fields differ")
        for name, count in (("r1_r6", 3335), ("r8", 811)):
            record = frame[name]
            if (type(record) is not dict or type(record.get("values")) is not list
                    or len(record["values"]) != count or len(record["values"]) > 10000
                    or any(type(value) not in (int, float) for value in record["values"])):
                raise ValueError("Projection vector bound/type differs")
            derived = _vector(record["values"], count)
            if artifacts._canonical(record) != artifacts._canonical(derived):
                raise ValueError("Projection vector hash/arithmetic differs")


def run_comparison(output_dir: Path, *, expected_protocol_sha256: str, engine_factory=None,
                   supervision_directory: Path | None = None, expected_readiness_sha256: str | None = None,
                   start_token: str | None = None) -> dict:
    output = Path(output_dir).absolute()
    _hash(expected_protocol_sha256)
    _read_protocol(output, expected_protocol_sha256)
    if set(path.name for path in output.iterdir()) != {"protocol.json"}:
        raise ValueError("Run needs fresh protocol only; no resume or overwrite")
    if engine_factory is not None:
        return _run(output, expected_protocol_sha256, engine_factory, "injected-test-factory")
    if supervision_directory is None or expected_readiness_sha256 is None or start_token is None:
        raise ValueError("Production requires all reviewed supervision bindings")
    # Separate Task2 authority; never construct a native engine during preparation/inspection.
    from drive_input_supervision import production_start
    with production_start(output, expected_protocol_sha256, supervision_directory, expected_readiness_sha256, start_token):
        return _run(output, expected_protocol_sha256, FlyEngine.from_prepared_graph, "native-supervised")


def _run(output: Path, expected: str, engine_factory, mode: str) -> dict:
    protocol, protocol_hash = _read_protocol(output, expected)
    engine = engine_factory()
    identity = engine.identity()
    _identity(identity, protocol)
    projection = _project(engine, identity)
    sessions = {arm: uuid4().hex for arm, _ in ARMS}
    metadata = {"engine_identity": identity, "protocol_version": VERSION, "stimulus_version": "drive-input-rgb/v1",
                "family": protocol["scope"], "seeds": [], "factors": {},
                "input_sha256": sorted(protocol["frame_sha256"].values()),
                "comparison": {"protocol": protocol, "protocol_sha256": protocol_hash,
                               "configuration_sha256": _decoder().configuration_sha256, "sessions": sessions,
                               "engine_mode": mode, "projection": projection}}
    if len(artifacts._canonical(metadata)) > READ_LIMITS.max_manifest_bytes:
        raise ValueError("Metadata exceeds 2 MiB")
    inputs, previous = frames(), None
    clock = lambda: _integer(time.monotonic_ns() // 1000000)
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=output) as scratch:
        checkpoint = Path(scratch) / "state.npz"
        with artifacts.RunRecorder(output / "run", run_kind="pilot", metadata=metadata, root_branch_id="prefix") as recorder:
            def check(tick):
                _clock(float(engine.brain.sim_ms), tick)
                if artifacts._canonical(engine.identity()) != artifacts._canonical(identity):
                    raise ValueError("Engine identity changed")

            def save(name, branch, tick):
                check(tick)
                state = _hash(engine.brain.checkpoint_state_sha256())
                engine.brain.checkpoint(checkpoint)
                if checkpoint.stat().st_size > MAX_CHECKPOINT_BYTES:
                    raise ValueError("Checkpoint exceeds limit")
                check(tick)
                if engine.brain.checkpoint_state_sha256() != state:
                    raise ValueError("Checkpoint mutated state")
                digest = recorder.ingest_checkpoint(name, checkpoint, origin_branch_id=branch)
                sequence = recorder.next_sequence
                recorder.append({"type": "checkpoint", "branch_id": branch, "sim_ms": tick / 10,
                                 "sim_tick": tick, "checkpoint_name": name, "complete_state_sha256": state})
                return digest, sequence, state

            def observe(row, decoder=None):
                nonlocal previous
                check(row["start_tick"])
                start = clock()
                telemetry = engine.observe(inputs[row["frame"]], 500, learning=False, stimulation=None,
                                           pathway_detail=False, qualification_detail=False)
                completion = clock()
                totals = _telemetry(telemetry, start=row["start_tick"], frame=row["frame"], identity=identity, protocol=protocol)
                check(row["end_tick"])
                if not start <= completion or (previous is not None and start < previous):
                    raise ValueError("Contradictory actual monotonic clocks")
                event = {"type": "observe", "branch_id": row["branch_id"], "sim_ms": row["end_tick"] / 10,
                         "stimulus": row["frame"], "input_version": row["input_version"],
                         "start_tick": row["start_tick"], "end_tick": row["end_tick"], "duration_ticks": 5000,
                         "start_ms": row["start_tick"] / 10, "end_ms": row["end_tick"] / 10, "duration_ms": 500,
                         "learning": False, "stimulation": None, "pathway_detail": False, "qualification_detail": False,
                         "input_sha256": protocol["frame_sha256"][row["frame"]], "telemetry": telemetry,
                         "wall_start_ms": start, "wall_completion_ms": completion}
                previous = completion
                if decoder is not None:
                    sample = _sample(row, totals, protocol_hash=protocol_hash, session_id=sessions[row["branch_id"]],
                                     wall_start=start, wall_completion=completion, protocol=protocol)
                    now = clock()
                    if now < completion:
                        raise ValueError("Decoder clock precedes acquisition")
                    event.update(motor_sample=sample, readout_now_ms=now, readout_result=decoder.consume(sample, now_ms=now))
                    previous = now
                    if row["observation_index"] == 39:
                        event["complete_state_sha256_after"] = _hash(engine.brain.checkpoint_state_sha256())
                recorder.append(event)

            save("brain-before.npz", "prefix", 0)
            for row in protocol["schedule"][:8]:
                observe(row)
            common_hash, sequence, state = save("black-prefix.npz", "prefix", 40000)
            common_path = output / "run/checkpoints/black-prefix.npz"
            for index, (arm, _) in enumerate(ARMS):
                if _file_digest(common_path) != common_hash:
                    raise ValueError("Common checkpoint changed")
                engine.brain.restore(common_path)
                check(40000)
                if engine.brain.checkpoint_state_sha256() != state or _file_digest(common_path) != common_hash:
                    raise ValueError("Restored complete state/checkpoint differs")
                wall = clock()
                if wall < previous:
                    raise ValueError("Restore rewound monotonic clock")
                previous = wall
                recorder.append({"type": "branch_start", "branch_id": arm, "sim_ms": 4000, "sim_tick": 40000,
                                 "parent_branch_id": "prefix", "parent_checkpoint_name": "black-prefix.npz",
                                 "parent_checkpoint_sequence": sequence, "parent_checkpoint_sha256": common_hash,
                                 "complete_state_sha256": state, "session_id": sessions[arm], "wall_start_ms": wall})
                decoder = _decoder()
                for row in protocol["schedule"][8 + index * 40:48 + index * 40]:
                    observe(row, decoder)
            save("brain-after.npz", ARMS[-1][0], 240000)
    summary = inspect_comparison(output)
    write_json_exclusive(summary, output / "summary.json")
    receipt = {"version": VERSION, "status": "complete", "verification_mode": "integrity-only",
               "scope": "execution-and-offline-integrity-bookkeeping", "protocol_sha256": protocol_hash,
               "summary_sha256": _file_digest(output / "summary.json"), "source": summary["source"],
               "exact_counts": EXACT_COUNTS, "final_state_sha256": summary["final_state_sha256"]}
    write_json_exclusive(receipt, output / "receipt.json")
    return receipt


def _checkpoint(event: dict, name: str, branch: str, tick: int) -> str:
    fields = artifacts.OWNED | {"type", "branch_id", "sim_ms", "sim_tick", "checkpoint_name",
                                "complete_state_sha256", "checkpoint_sha256", "checkpoint_size"}
    if (set(event) != fields or event["type"] != "checkpoint" or event["branch_id"] != branch
            or event["checkpoint_name"] != name or _integer(event["sim_tick"]) != tick):
        raise ValueError("Checkpoint route/order/fields differ")
    _clock(event["sim_ms"], tick)
    return _hash(event["complete_state_sha256"])


def _observation(event: dict, row: dict, identity: dict, protocol: dict, previous: int | None) -> tuple[dict, int]:
    branch = row["branch_id"] != "prefix"
    fields = artifacts.OWNED | {"type", "branch_id", "sim_ms", "stimulus", "input_version", "start_tick", "end_tick",
        "duration_ticks", "start_ms", "end_ms", "duration_ms", "learning", "stimulation", "pathway_detail",
        "qualification_detail", "input_sha256", "telemetry", "wall_start_ms", "wall_completion_ms"}
    if branch:
        fields |= {"motor_sample", "readout_now_ms", "readout_result"}
    if branch and row["observation_index"] == 39:
        fields.add("complete_state_sha256_after")
    if (set(event) != fields or event["type"] != "observe" or event["branch_id"] != row["branch_id"]
            or event["stimulus"] != row["frame"] or event["input_version"] != row["input_version"]
            or event["input_sha256"] != protocol["frame_sha256"][row["frame"]]
            or event["learning"] is not False or event["stimulation"] is not None
            or event["pathway_detail"] is not False or event["qualification_detail"] is not False):
        raise ValueError("Observation fields/schedule/modes differ")
    for name, expected in (("start_tick", row["start_tick"]), ("end_tick", row["end_tick"]), ("duration_ticks", 5000)):
        if _integer(event[name]) != expected:
            raise ValueError("Observation tick mismatch")
    for name, tick in (("sim_ms", row["end_tick"]), ("start_ms", row["start_tick"]),
                       ("end_ms", row["end_tick"]), ("duration_ms", 5000)):
        _clock(event[name], tick)
    totals = _telemetry(event["telemetry"], start=row["start_tick"], frame=row["frame"], identity=identity, protocol=protocol)
    start, completion = _integer(event["wall_start_ms"]), _integer(event["wall_completion_ms"])
    now = _integer(event["readout_now_ms"]) if branch else completion
    if not start <= completion <= now or (previous is not None and start < previous):
        raise ValueError("Contradictory sequential monotonic clocks")
    return totals, now


def _compare(left: dict, right: dict) -> dict:
    a, b = left["proposal_signatures"], right["proposal_signatures"]
    same_length = len(a) == len(b)
    return {"lengths": [len(a), len(b)], "availability_count_difference": not same_length,
            "proposal_signatures_equal": a == b, "motor_counts_equal": left["motor_counts"] == right["motor_counts"],
            "drink_ids_equal": [s[0] for s in a] == [s[0] for s in b] if same_length else None,
            "target_prices_equal": [s[1] for s in a] == [s[1] for s in b] if same_length else None,
            "relative_times_equal": [s[2] for s in a] == [s[2] for s in b] if same_length else None}


def _summarize(run, protocol: dict, protocol_hash: str, events) -> dict:
    manifest, decoder = run.manifest, _decoder()
    metadata = manifest["metadata"]
    declaration = metadata.get("comparison")
    if (set(metadata) != artifacts.REQUIRED_METADATA | {"comparison"}
            or manifest["run_kind"] != "pilot" or manifest["root_branch_id"] != "prefix"
            or manifest["event_count"] != 175 or manifest["state_anchors"] != {}
            or metadata["protocol_version"] != VERSION or metadata["stimulus_version"] != "drive-input-rgb/v1"
            or metadata["family"] != protocol["scope"] or metadata["seeds"] != [] or metadata["factors"] != {}
            or metadata["input_sha256"] != sorted(protocol["frame_sha256"].values())
            or type(declaration) is not dict or set(declaration) != {"protocol", "protocol_sha256", "configuration_sha256",
                                                                 "sessions", "engine_mode", "projection"}
            or artifacts._canonical(declaration["protocol"]) != artifacts._canonical(protocol)
            or declaration["protocol_sha256"] != protocol_hash
            or declaration["configuration_sha256"] != decoder.configuration_sha256
            or declaration["engine_mode"] not in ("injected-test-factory", "native-supervised")):
        raise ValueError("Run metadata/protocol/source binding differs")
    sessions, identity = declaration["sessions"], metadata["engine_identity"]
    if (type(sessions) is not dict or set(sessions) != {arm for arm, _ in ARMS}
            or any(type(s) is not str or re.fullmatch(r"[0-9a-f]{32}", s) is None for s in sessions.values())
            or len(set(sessions.values())) != 4):
        raise ValueError("Branch sessions must be distinct")
    _identity(identity, protocol)
    _validate_projection(declaration["projection"], identity)
    if set(manifest["checkpoints"]) != {"brain-before.npz", "black-prefix.npz", "brain-after.npz"}:
        raise ValueError("Exactly three checkpoints required")
    count = 0

    def take():
        nonlocal count
        event = next(events, None)
        if event is None:
            raise ValueError("Missing scheduled event")
        count += 1
        return event

    initial = _checkpoint(take(), "brain-before.npz", "prefix", 0)
    if initial != declaration["projection"]["state_sha256_after"]:
        raise ValueError("Projection and initial checkpoint state differ")
    previous, first_wall, processing, delivery = None, None, [], []
    for row in protocol["schedule"][:8]:
        event = take()
        _, previous = _observation(event, row, identity, protocol, previous)
        if first_wall is None:
            first_wall = event["wall_start_ms"]
        processing.append(event["wall_completion_ms"] - event["wall_start_ms"])
    common = take()
    state = _checkpoint(common, "black-prefix.npz", "prefix", 40000)
    arms, reset_reasons = {}, []
    for index, (arm, _) in enumerate(ARMS):
        fork = take()
        fields = artifacts.OWNED | {"type", "branch_id", "sim_ms", "sim_tick", "parent_branch_id",
            "parent_checkpoint_name", "parent_checkpoint_sequence", "parent_checkpoint_sha256",
            "complete_state_sha256", "session_id", "wall_start_ms"}
        if (set(fork) != fields or fork["type"] != "branch_start" or fork["branch_id"] != arm
                or fork["parent_branch_id"] != "prefix" or fork["parent_checkpoint_name"] != "black-prefix.npz"
                or _integer(fork["parent_checkpoint_sequence"]) != common["sequence"]
                or fork["parent_checkpoint_sha256"] != common["checkpoint_sha256"]
                or fork["complete_state_sha256"] != state or _integer(fork["sim_tick"]) != 40000
                or fork["session_id"] != sessions[arm]):
            raise ValueError("Branch/common checkpoint binding differs")
        _clock(fork["sim_ms"], 40000)
        if _integer(fork["wall_start_ms"]) < previous:
            raise ValueError("Branch clock rewound")
        previous, decoder = fork["wall_start_ms"], _decoder()
        proposals, counts, samples, results, resets = [], [], [], [], []
        statuses, reasons = Counter(), Counter()
        for row in protocol["schedule"][8 + index * 40:48 + index * 40]:
            event = take()
            totals, now = _observation(event, row, identity, protocol, previous)
            sample = _sample(row, totals, protocol_hash=protocol_hash, session_id=sessions[arm],
                             wall_start=event["wall_start_ms"], wall_completion=event["wall_completion_ms"], protocol=protocol)
            if artifacts._canonical(sample) != artifacts._canonical(event["motor_sample"]):
                raise ValueError("Motor sample contradicts original counts/source/clock")
            result = decoder.consume(sample, now_ms=now)
            if artifacts._canonical(result) != artifacts._canonical(event["readout_result"]):
                raise ValueError("Complete decoder reconstruction differs")
            previous = now
            counts.append([totals["motor_left"], totals["motor_right"]])
            samples.append(sample)
            results.append(result)
            statuses[result["status"]] += 1
            reasons[result["reason"]] += 1
            if result["reason"] in CLOCK_RESETS:
                resets.append({"observation_index": row["observation_index"], "reason": result["reason"]})
                reset_reasons.append(f"{arm}:{result['reason']}")
            if result["proposal"] is not None:
                proposals.append(result["proposal"])
            processing.append(event["wall_completion_ms"] - event["wall_start_ms"])
            delivery.append(now - event["wall_completion_ms"])
        final_state = _hash(event["complete_state_sha256_after"])
        selected = Counter(p["drink_id"] for p in proposals)
        arms[arm] = {"motor_counts": counts, "proposals": proposals,
            "proposal_signatures": [[p["drink_id"], p["target_rappen"], p["completion_tick"] - 40000] for p in proposals],
            "final_state_sha256": final_state, "status_counts": dict(statuses), "reason_counts": dict(reasons),
            "resets": resets, "motor_samples": samples, "readout_results": results,
            # Frozen decoder hooks expose the independently reconstructed unfinished path.
            "final_pending_state": artifacts._strict_load(artifacts._canonical({**results[-1], "decisions": decoder._decisions,
                "input_history": decoder._history, "partial_block": decoder._block,
                "path_anchor": decoder._anchor, "armed": decoder._armed})),
            "coverage": {"drink_ids": sorted(selected), "target_rappen": sorted({p["target_rappen"] for p in proposals}),
                         "favorites": dict(selected), "maximum_selected_fraction": max(selected.values()) / len(proposals) if proposals else 0},
            "proposal_elapsed": [{"model_ms": (p["completion_tick"] - p["path_start_tick"]) / 10,
                                  "wall_ms": p["completion_wall_ms"] - p["path_start_wall_ms"],
                                  "delivery_ms": p["emitted_wall_ms"] - p["completion_wall_ms"]} for p in proposals]}
    final = _checkpoint(take(), "brain-after.npz", ARMS[-1][0], 240000)
    if final != arms[ARMS[-1][0]]["final_state_sha256"]:
        raise ValueError("Final checkpoint/end state differs")
    if next(events, None) is not None or count != 175:
        raise ValueError("Unexpected EOF/count")
    comparisons = {"A/B": _compare(arms["image-a"], arms["image-b"]),
                   "A/black": _compare(arms["image-a"], arms["control-black"]),
                   "B/black": _compare(arms["image-b"], arms["control-black"])}
    repeat = _compare(arms["image-a"], arms["image-a-repeat"])
    repeat_exact = (repeat["motor_counts_equal"] and repeat["proposal_signatures_equal"]
                    and arms["image-a"]["final_state_sha256"] == arms["image-a-repeat"]["final_state_sha256"])
    reasons = ([] if repeat_exact else ["A repeat motor/proposal/scientific-state mismatch"]) + reset_reasons
    evaluable = not reasons
    function = any(arms[name]["proposals"] for name in ("image-a", "image-b"))
    ab = comparisons["A/B"]
    sensitivity = evaluable and not ab["proposal_signatures_equal"] and not ab["motor_counts_equal"]
    timing_only = sensitivity and ab["drink_ids_equal"] is True and ab["target_prices_equal"] is True
    outcome = ("not-evaluable" if not evaluable else "functional-negative" if not function
               else "functional-output-timing-sensitive" if timing_only else "functional-input-sensitive" if sensitivity
               else "functional-sensitivity-not-shown")
    summary = {"version": VERSION, "scope": protocol["scope"], "verification_mode": run.verification_mode,
        "engine_mode": declaration["engine_mode"], "protocol_sha256": protocol_hash,
        "configuration_sha256": declaration["configuration_sha256"], "exact_counts": EXACT_COUNTS,
        "source": {name: manifest[name] for name in ("schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256")},
        "initial_state_sha256": initial, "common_state_sha256": state, "final_state_sha256": final,
        "projection": declaration["projection"], "arms": arms, "comparisons": comparisons, "outcome": outcome,
        "evaluation": {"evaluable": evaluable, "repeat_exact": repeat_exact, "reasons": reasons,
                       "scope": "conditional-on-separately-verified-supervisor-resource-receipt",
                       "function_present": function if evaluable else None, "ab_output_sensitivity": sensitivity,
                       "output_timing_only": timing_only},
        "clocks": {"domain": "actual-single-monotonic-milliseconds", "authenticated": False,
                   "first_observation_start_ms": first_wall, "last_readout_now_ms": previous,
                   "observation_span_ms": previous - first_wall},
        "latency_ms": {"processing": processing, "delivery": delivery}, "limitations": LIMITATIONS}
    if len(artifacts._canonical(summary)) + 1 >= MAX_SUMMARY_BYTES:
        raise ValueError("Summary exceeds exclusive 8 MiB limit")
    return summary


def inspect_comparison(output_dir: Path) -> dict:
    output = Path(output_dir).absolute()
    protocol, digest = _read_protocol(output)
    with snapshot_recorded_run(output / "run", limits=READ_LIMITS, checkpoint_byte_limit=MAX_CHECKPOINT_BYTES) as snapshot:
        run = artifacts.verify_run(snapshot, limits=READ_LIMITS)
        with closing(run.iter_events()) as events:
            return _summarize(run, protocol, digest, events)


def main() -> int:
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
    try:
        if args.command == "prepare":
            result = prepare_comparison(args.output_dir)
        elif args.command == "inspect":
            result = inspect_comparison(args.output_dir)
        else:
            result = run_comparison(args.output_dir, expected_protocol_sha256=args.expected_protocol_sha256,
                supervision_directory=args.supervision_directory, expected_readiness_sha256=args.expected_readiness_sha256,
                start_token=args.start_token)
    except (ValueError, OSError, TypeError, OverflowError, RuntimeError, KeyError, AttributeError, ImportError) as error:
        parser.exit(1, f"Drive input comparison failed: {error}\n")
    print(artifacts._canonical(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
