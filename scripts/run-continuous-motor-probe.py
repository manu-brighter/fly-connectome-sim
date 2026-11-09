"""Fixed continuous motor probe; complete integrity audit is not native attestation."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from hashlib import sha256
import math
from pathlib import Path
import re
import tempfile
import time
from uuid import uuid4

import numpy as np

from fly_connectome_sim.engine import FlyEngine, _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.experiment.cell_activity import LOCKS
from fly_connectome_sim.neural.checkpoint import model_fingerprint
from market_artifacts import _copy_bounded, _safe_directory, snapshot_recorded_run, write_json_exclusive
from market_motor_readout import MotorReadout


VERSION = "continuous-motor-probe/v1"
ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
ORDER = ("S1", "S2", "S3", "S4", "S5", "S6", "S6", "S5", "S4", "S3", "S2", "S1")
READ_LIMITS = artifacts.RunReadLimits(
    max_manifest_bytes=2 * 1024**2,
    max_event_line_bytes=1024**2,
    max_events_bytes=64 * 1024**2,
    max_events=194,
    max_checkpoints=2,
)
MAX_CHECKPOINT_BYTES = 64 * 1024**2
EXACT_COUNTS = {"episodes": 12, "observations": 192, "native_bins": 9600,
                "events": 194, "checkpoints": 2, "model_ms": 96000}
LIMITATIONS = [
    "Integrity and pure decoder reconstruction only; not native model replay attestation or scientific validity.",
    "Consistently rewritten and resealed monotonic timing is not independently authenticated.",
    "Both orders share continuous engine/decoder state; partitions are descriptive, not independent replication.",
    "No semantic recognition, biological choice/learning, twenty-slot coverage or full price-range validation.",
    "No image-upload latency, live-cell-display throughput or price activation qualification.",
    "Equal image brightness does not establish equal retinal drive; the development-selected decoder is unchanged.",
    "Proposals may concentrate on one leaf; neither outcome authorizes Stage C or another acquisition.",
]


def frames() -> dict[str, np.ndarray]:
    """Exact logical RGB arrays, with no media or adaptive preprocessing."""
    y, x = np.indices((64, 64))
    masks = ((x // 8) % 2 == 0, (y // 8) % 2 == 0,
             (x // 8 + y // 8) % 2 == 0, ((x + y) // 8) % 2 == 0,
             (16 <= x) & (x < 48), (16 <= y) & (y < 48))
    result = {"black": np.zeros((64, 64, 3), dtype=np.uint8)}
    result.update({f"S{index}": np.repeat((mask * 255).astype(np.uint8)[..., None], 3, axis=2)
                   for index, mask in enumerate(masks, 1)})
    return result


def _decoder() -> MotorReadout:
    drinks = [{"id": f"drink-{index:02d}", "minimum_rappen": 400,
               "maximum_rappen": 700, "grid_rappen": 50} for index in range(20)]
    return MotorReadout(drinks, max_sample_age_ms=5000)


def _digest(value) -> str:
    return sha256(artifacts._canonical(value)).hexdigest()


def _file_digest(path: Path) -> str:
    return artifacts._digest_file(path)[0]


def _schedule() -> list[dict]:
    return [{"observation_index": index, "start_tick": index * 5000, "end_tick": (index + 1) * 5000,
             "frame": "black" if index % 16 < 4 else ORDER[index // 16],
             "input_version": f"episode-{index // 16 + 1:02d}-{'black' if index % 16 < 4 else ORDER[index // 16]}"}
            for index in range(192)]


def _protocol() -> dict:
    sources = [Path(__file__).resolve(), ROOT / "scripts/market_motor_readout.py",
               ROOT / "scripts/market_artifacts.py", ROOT / "scripts/market_supervision.py",
               ROOT / "scripts/supervise-market-response.ps1",
               ROOT / "src/fly_connectome_sim/experiment/recorder.py",
               ROOT / "src/fly_connectome_sim/neural/datasets.json"]
    sources.extend(sorted((ROOT / "src/fly_connectome_sim/schemas").glob("*.json")))
    hashes = {path.relative_to(ROOT).as_posix(): _file_digest(path) for path in sources}
    hashes.update({f"src/fly_connectome_sim/neural/{path.name}": _file_digest(path)
                   for path in sorted(LOCKS.glob("*.lock.json"))})
    frame_hashes = {name: _rgb_input_sha256(frame) for name, frame in frames().items()}
    development = {"2bab35627cfde1611798b177adad84251453d15920ed0f2fa692dbb12b9cc166",
                   "b6302efedf629e2e20f933890d8a4748f904b64dfcca4672d427255f0a740ab2",
                   "cf407fa59d7028e75e8bcc8dc1f4a47aec4a8b3db60f738574c2f2cd8f451257",
                   "7f4c6c24d6ebd72dcbbdd186db8bc1ffefb9df0df2be13bcc875b0b52e9367d6"}
    if len(set(frame_hashes.values())) != 7 or set(frame_hashes.values()) & development:
        raise ValueError("Continuous probe patterns must be distinct from developmental A–D")
    decoder = _decoder()
    return {
        "version": VERSION, "scope": "continuous-motor-path-feasibility",
        "source": {"model_fingerprint": model_fingerprint(), "files_sha256": hashes},
        "frame_shape": [64, 64, 3], "frame_dtype": "uint8", "frame_sha256": frame_hashes,
        "pattern_order": list(ORDER), "schedule": _schedule(), "exact_counts": EXACT_COUNTS,
        "observation_ms": 500, "native_bin_ms": 10, "root_branch_id": "continuous",
        "decoder": {"configuration": decoder.configuration, "configuration_sha256": decoder.configuration_sha256},
        "observation": {"learning": False, "stimulation": None, "pathway_detail": False,
                        "qualification_detail": False, "passive_dynamics": "normal-engine-defaults"},
        "limits": {"wall_seconds": 900, "peak_rss_bytes": 4 * 1024**3,
                   "new_output_evidence_scratch_bytes": 256 * 1024**2, "poll_seconds_max": 2,
                   "manifest_bytes": READ_LIMITS.max_manifest_bytes,
                   "event_line_bytes": READ_LIMITS.max_event_line_bytes,
                   "events_bytes": READ_LIMITS.max_events_bytes,
                   "events": 194, "checkpoints": 2, "checkpoint_bytes_each": MAX_CHECKPOINT_BYTES},
        "verification_mode": "integrity-only",
    }


def prepare_probe(output_dir: Path) -> dict:
    """Exclusively freeze inputs/source/configuration; never construct an engine."""
    output = Path(output_dir).absolute()
    _safe_directory(output.parent)
    protocol = _protocol()
    output.mkdir()
    write_json_exclusive(protocol, output / "protocol.json")
    return protocol


def _read_protocol(output: Path, expected: str | None = None) -> tuple[dict, str]:
    _safe_directory(output)
    with tempfile.TemporaryDirectory(prefix="fly-continuous-protocol-") as scratch:
        copied = Path(scratch) / "protocol.json"
        _copy_bounded(output / "protocol.json", copied, READ_LIMITS.max_manifest_bytes)
        raw = copied.read_bytes()
    digest, protocol = sha256(raw).hexdigest(), artifacts._strict_load(raw)
    if ((expected is not None and digest != expected) or raw != artifacts._canonical(protocol) + b"\n"
            or artifacts._canonical(protocol) != artifacts._canonical(_protocol())):
        raise ValueError("Prepared protocol/hash/encoding or current source differs")
    return protocol, digest


def _integer(value, upper: int = 2**53 - 1) -> int:
    if type(value) is not int or not 0 <= value <= upper:
        raise ValueError("Invalid nonnegative JSON-safe integer/count")
    return value


def _number(value) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid finite nonnegative number")
    return value


def _hash(value) -> str:
    if type(value) is not str or not artifacts.DIGEST.fullmatch(value):
        raise ValueError("Missing complete source/state hash")
    return value


def _clock(value, tick: int) -> None:
    if _number(value) != tick / 10:
        raise ValueError("Contradictory model clock")


def _identity(identity: dict, protocol: dict) -> dict:
    if (type(identity) is not dict or set(identity) != {"version", "neural_groups", "model_provenance", "sha256"}
            or _digest({key: value for key, value in identity.items() if key != "sha256"}) != identity.get("sha256")
            or identity.get("model_provenance", {}).get("model_fingerprint") != protocol["source"]["model_fingerprint"]):
        raise ValueError("Engine/source identity differs")
    populations = identity["neural_groups"]
    if type(populations) is not dict or set(populations) != set(GROUPS):
        raise ValueError("Population declarations differ")
    for name, members in populations.items():
        if (type(members) is not list or not members or any(type(index) is not int for index in members)
                or len(set(members)) != len(members) or (name.startswith("motor_") and len(members) != 1)):
            raise ValueError("Empty, duplicate or wrong-size neural population")
        for index in members:
            _integer(index)
    if populations["motor_left"] == populations["motor_right"]:
        raise ValueError("Motor populations must be distinct declared cells")
    lock_path = LOCKS / "arrays.lock.json"
    with lock_path.open("rb") as stream:
        raw = stream.read(READ_LIMITS.max_manifest_bytes + 1)
    if (len(raw) > READ_LIMITS.max_manifest_bytes or sha256(raw).hexdigest()
            != protocol["source"]["files_sha256"].get("src/fly_connectome_sim/neural/arrays.lock.json")):
        raise ValueError("Array lock differs from protocol")
    arrays = artifacts._strict_load(raw)
    for name in ("ids", "ptr", "post"):
        if _hash(identity["model_provenance"].get(f"graph_{name}_sha256")) != arrays[name]:
            raise ValueError("Declared engine graph differs from frozen graph lock")
    return populations


def _telemetry(telemetry: dict, *, start: int, frame: str, identity: dict, protocol: dict) -> dict:
    end = start + 5000
    required = {"sim_ms", "interval_ms", "learning", "stimulation", "compute_seconds", "kernel_seconds",
                "rates_hz", "bins", "input_shape", "input_dtype", "input_sha256", "engine_identity"}
    optional = {"total_spikes", "turn_hz", "spike_sha256", "memory"}
    if (type(telemetry) is not dict or not required <= telemetry.keys() or telemetry.keys() - required - optional
            or artifacts._canonical(telemetry.get("engine_identity")) != artifacts._canonical(identity)):
        raise ValueError("Observation engine identity differs")
    if (telemetry.get("learning") is not False or "stimulation" not in telemetry
            or telemetry["stimulation"] is not None
            or "pathway_detail" in telemetry or "qualification_detail" in telemetry):
        raise ValueError("Unexpected learning, stimulation or detail telemetry")
    _clock(telemetry.get("sim_ms"), end)
    _clock(telemetry.get("interval_ms"), 5000)
    for field in ("compute_seconds", "kernel_seconds"):
        _number(telemetry.get(field))
    if (artifacts._canonical(telemetry.get("input_shape")) != b"[64,64,3]" or telemetry.get("input_dtype") != "uint8"
            or telemetry.get("input_sha256") != protocol["frame_sha256"][frame]):
        raise ValueError("Telemetry frame differs")
    bins, populations = telemetry.get("bins"), identity["neural_groups"]
    if type(bins) is not list or len(bins) != 50:
        raise ValueError("Exactly 50 original bins required")
    totals = dict.fromkeys(GROUPS, 0)
    memberships = {name: set(members) for name, members in populations.items()}
    inclusions = [(name, other) for name in GROUPS for other in GROUPS
                  if memberships[name] <= memberships[other]]
    for index, row in enumerate(bins):
        if type(row) is not dict or set(row) != {"end_ms", "duration_ms", "group_spikes"}:
            raise ValueError("Unexpected native bin fields")
        _clock(row["end_ms"], start + (index + 1) * 100)
        _clock(row["duration_ms"], 100)
        counts = row["group_spikes"]
        if type(counts) is not dict or set(counts) != set(GROUPS):
            raise ValueError("Population count fields differ")
        for name in GROUPS:
            value = _integer(counts[name], 100 * len(populations[name]))
            totals[name] += value
        if any(counts[name] > counts[other] for name, other in inclusions):
            raise ValueError("Population counts contradict membership inclusion")
    rates = telemetry.get("rates_hz")
    if type(rates) is not dict or set(rates) != set(GROUPS):
        raise ValueError("Population rate keys differ")
    for name in GROUPS:
        if not math.isclose(_number(rates[name]), totals[name] / (len(populations[name]) * 0.5),
                            rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Population rate/count mismatch")
    if "turn_hz" in telemetry:
        if (type(telemetry["turn_hz"]) not in (int, float) or not math.isfinite(telemetry["turn_hz"])
                or telemetry["turn_hz"] != rates["motor_right"] - rates["motor_left"]):
            raise ValueError("Turn rate contradicts group rates")
    if "total_spikes" in telemetry:
        minimum_total = 0
        for mask in range(1, 1 << len(GROUPS)):
            selected = [name for index, name in enumerate(GROUPS) if mask & (1 << index)]
            if all(memberships[left].isdisjoint(memberships[right])
                   for index, left in enumerate(selected) for right in selected[index + 1:]):
                minimum_total = max(minimum_total, sum(totals[name] for name in selected))
        if _integer(telemetry["total_spikes"]) < minimum_total:
            raise ValueError("Total spikes contradict population count")
    if "spike_sha256" in telemetry:
        _hash(telemetry["spike_sha256"])
    return totals


def _sample(row: dict, totals: dict, *, protocol_hash: str, session_id: str,
            wall_start: int, wall_completion: int, protocol: dict) -> dict:
    return {"source_sha256": protocol_hash, "session_id": session_id,
            "observation_index": row["observation_index"], "start_tick": row["start_tick"], "end_tick": row["end_tick"],
            "left_count": totals["motor_left"], "right_count": totals["motor_right"],
            "input_version": row["input_version"], "frame_sha256": protocol["frame_sha256"][row["frame"]],
            "wall_start_ms": wall_start, "wall_completion_ms": wall_completion}


def run_probe(output_dir: Path, *, expected_protocol_sha256: str, engine_factory=None,
              supervision_directory: Path | None = None, expected_readiness_sha256: str | None = None,
              start_token: str | None = None, clock_ms=None) -> dict:
    """Only an injected test factory bypasses the production owned-process guard."""
    if clock_ms is not None and engine_factory is None:
        raise ValueError("Injected clocks require an injected test engine factory")
    output = Path(output_dir).absolute()
    _hash(expected_protocol_sha256)
    _read_protocol(output, expected_protocol_sha256)
    if engine_factory is not None:
        return _run_probe(output, expected_protocol_sha256, engine_factory, clock_ms,
                          "injected-test-factory")
    if supervision_directory is None or expected_readiness_sha256 is None or start_token is None:
        raise ValueError("Production requires all supervision bindings")
    # Task2 is deliberately optional for prepare/inspect and synthetic Task1 tests.
    from continuous_motor_supervision import production_start

    with production_start(output, expected_protocol_sha256, supervision_directory,
                          expected_readiness_sha256, start_token):
        return _run_probe(output, expected_protocol_sha256, FlyEngine.from_prepared_graph,
                          None, "native-supervised")


def _run_probe(output: Path, expected: str, engine_factory, clock_ms, mode: str) -> dict:
    _safe_directory(output)
    if set(path.name for path in output.iterdir()) != {"protocol.json"}:
        raise ValueError("Run requires exactly a fresh protocol; no resume")
    protocol, protocol_hash = _read_protocol(output, expected)
    clock = clock_ms if clock_ms is not None else lambda: time.monotonic_ns() // 1000000
    decoder, session_id = _decoder(), uuid4().hex
    engine = engine_factory()
    identity = engine.identity()
    _identity(identity, protocol)
    metadata = {"engine_identity": identity, "protocol_version": VERSION,
                "stimulus_version": "continuous-motor-rgb/v1", "family": "continuous-motor-path-feasibility",
                "seeds": [], "factors": {}, "input_sha256": sorted(protocol["frame_sha256"].values()),
                "probe": {"protocol": protocol, "protocol_sha256": protocol_hash,
                          "configuration_sha256": decoder.configuration_sha256,
                          "session_id": session_id, "engine_mode": mode}}
    inputs, previous_now = frames(), None
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=output) as scratch:
        checkpoint = Path(scratch) / "state.npz"
        with artifacts.RunRecorder(output / "run", run_kind="pilot", metadata=metadata,
                                   root_branch_id="continuous") as recorder:

            def save(name, tick):
                if artifacts._canonical(engine.identity()) != artifacts._canonical(identity):
                    raise ValueError("Engine identity changed")
                _clock(float(engine.brain.sim_ms), tick)
                engine.brain.checkpoint(checkpoint)
                if checkpoint.stat().st_size > MAX_CHECKPOINT_BYTES:
                    raise ValueError("Checkpoint exceeds read limit")
                recorder.ingest_checkpoint(name, checkpoint, origin_branch_id="continuous")
                state = _hash(engine.brain.checkpoint_state_sha256())
                recorder.append({"type": "checkpoint", "branch_id": "continuous", "sim_ms": tick / 10,
                                 "sim_tick": tick, "checkpoint_name": name, "complete_state_sha256": state})
                return state

            save("brain-before.npz", 0)
            for row in protocol["schedule"]:
                if artifacts._canonical(engine.identity()) != artifacts._canonical(identity):
                    raise ValueError("Engine identity changed")
                _clock(float(engine.brain.sim_ms), row["start_tick"])
                wall_start = _integer(clock())
                telemetry = engine.observe(inputs[row["frame"]], 500, learning=False, stimulation=None,
                                           pathway_detail=False, qualification_detail=False)
                wall_completion = _integer(clock())
                totals = _telemetry(telemetry, start=row["start_tick"], frame=row["frame"],
                                    identity=identity, protocol=protocol)
                sample = _sample(row, totals, protocol_hash=protocol_hash, session_id=session_id,
                                 wall_start=wall_start, wall_completion=wall_completion, protocol=protocol)
                now = _integer(clock())
                if not wall_start <= wall_completion <= now or (previous_now is not None and wall_start < previous_now):
                    raise ValueError("Contradictory sequential monotonic clocks")
                result = decoder.consume(sample, now_ms=now)
                previous_now = now
                event = {"type": "observe", "branch_id": "continuous", "sim_ms": row["end_tick"] / 10,
                         "stimulus": row["frame"], "input_version": row["input_version"],
                         "start_tick": row["start_tick"], "end_tick": row["end_tick"], "duration_ticks": 5000,
                         "start_ms": row["start_tick"] / 10, "end_ms": row["end_tick"] / 10, "duration_ms": 500,
                         "learning": False, "stimulation": None, "pathway_detail": False, "qualification_detail": False,
                         "input_sha256": protocol["frame_sha256"][row["frame"]], "telemetry": telemetry,
                         "motor_sample": sample, "readout_now_ms": now, "readout_result": result}
                if row["observation_index"] == 191:
                    event["complete_state_sha256_after"] = _hash(engine.brain.checkpoint_state_sha256())
                recorder.append(event)
            save("brain-after.npz", 960000)
    summary = inspect_probe(output)
    write_json_exclusive(summary, output / "summary.json")
    receipt = {"version": VERSION, "status": "complete", "verification_mode": "integrity-only",
               "scope": "execution-and-offline-integrity-bookkeeping", "protocol_sha256": protocol_hash,
               "configuration_sha256": decoder.configuration_sha256, "session_id": session_id,
               "summary_sha256": _file_digest(output / "summary.json"), "source": summary["source"],
               "exact_counts": summary["exact_counts"], "final_state_sha256": summary["final_state_sha256"]}
    write_json_exclusive(receipt, output / "receipt.json")
    return receipt


def _checkpoint(event: dict, name: str, tick: int) -> str:
    fields = artifacts.OWNED | {"type", "branch_id", "sim_ms", "sim_tick", "checkpoint_name",
                                "complete_state_sha256", "checkpoint_sha256", "checkpoint_size"}
    if (set(event) != fields or event.get("type") != "checkpoint" or event.get("branch_id") != "continuous"
            or event.get("checkpoint_name") != name or _integer(event.get("sim_tick")) != tick):
        raise ValueError("Checkpoint route/order/fields differ")
    _clock(event["sim_ms"], tick)
    return _hash(event["complete_state_sha256"])


def _observation(event: dict, row: dict, *, identity: dict, protocol: dict,
                 protocol_hash: str, session_id: str, previous_now: int | None) -> dict:
    fields = artifacts.OWNED | {"type", "branch_id", "sim_ms", "stimulus", "input_version", "start_tick", "end_tick",
                                "duration_ticks", "start_ms", "end_ms", "duration_ms", "learning", "stimulation",
                                "pathway_detail", "qualification_detail", "input_sha256", "telemetry",
                                "motor_sample", "readout_now_ms", "readout_result"}
    if row["observation_index"] == 191:
        fields |= {"complete_state_sha256_after"}
    if (set(event) != fields or event.get("type") != "observe" or event.get("branch_id") != "continuous"
            or event.get("stimulus") != row["frame"] or event.get("input_version") != row["input_version"]
            or event.get("input_sha256") != protocol["frame_sha256"][row["frame"]]
            or event.get("learning") is not False or event.get("stimulation") is not None
            or event.get("pathway_detail") is not False or event.get("qualification_detail") is not False):
        raise ValueError("Observation fields/schedule/modes differ")
    for field, expected in (("start_tick", row["start_tick"]), ("end_tick", row["end_tick"]), ("duration_ticks", 5000)):
        if _integer(event[field]) != expected:
            raise ValueError("Observation tick mismatch")
    for field, tick in (("sim_ms", row["end_tick"]), ("start_ms", row["start_tick"]),
                        ("end_ms", row["end_tick"]), ("duration_ms", 5000)):
        _clock(event[field], tick)
    totals = _telemetry(event["telemetry"], start=row["start_tick"], frame=row["frame"], identity=identity, protocol=protocol)
    supplied = event["motor_sample"]
    if type(supplied) is not dict:
        raise ValueError("Missing recorded motor sample")
    start, completion = _integer(supplied.get("wall_start_ms")), _integer(supplied.get("wall_completion_ms"))
    now = _integer(event["readout_now_ms"])
    if not start <= completion <= now or (previous_now is not None and start < previous_now):
        raise ValueError("Contradictory sequential monotonic clocks")
    derived = _sample(row, totals, protocol_hash=protocol_hash, session_id=session_id,
                      wall_start=start, wall_completion=completion, protocol=protocol)
    if artifacts._canonical(supplied) != artifacts._canonical(derived):
        raise ValueError("Recorded sample disagrees with original bins/schedule/identity")
    return derived


def _summarize_events(run: artifacts.VerifiedRun, protocol: dict, protocol_hash: str, events) -> dict:
    manifest, decoder = run.manifest, _decoder()
    metadata, declaration = manifest["metadata"], manifest["metadata"].get("probe")
    if (set(metadata) != artifacts.REQUIRED_METADATA | {"probe"}
            or manifest["run_kind"] != "pilot" or manifest["root_branch_id"] != "continuous"
            or manifest["event_count"] != 194 or manifest["state_anchors"] != {}
            or metadata.get("protocol_version") != VERSION or metadata.get("stimulus_version") != "continuous-motor-rgb/v1"
            or metadata.get("family") != "continuous-motor-path-feasibility" or metadata.get("seeds") != []
            or metadata.get("factors") != {} or metadata.get("input_sha256") != sorted(protocol["frame_sha256"].values())
            or type(declaration) is not dict or set(declaration) != {"protocol", "protocol_sha256", "configuration_sha256", "session_id", "engine_mode"}
            or artifacts._canonical(declaration.get("protocol")) != artifacts._canonical(protocol)
            or declaration.get("protocol_sha256") != protocol_hash
            or declaration.get("configuration_sha256") != decoder.configuration_sha256
            or declaration.get("engine_mode") not in ("injected-test-factory", "native-supervised")
            or type(declaration.get("session_id")) is not str or re.fullmatch(r"[0-9a-f]{32}", declaration["session_id"]) is None):
        raise ValueError("Run protocol/configuration/session/source binding differs")
    identity, session_id = metadata["engine_identity"], declaration["session_id"]
    _identity(identity, protocol)
    if set(manifest["checkpoints"]) != {"brain-before.npz", "brain-after.npz"}:
        raise ValueError("Exactly two checkpoints required")
    count = 0

    def take():
        nonlocal count
        event = next(events, None)
        if event is None:
            raise ValueError("Missing scheduled event")
        count += 1
        return event

    initial_state = _checkpoint(take(), "brain-before.npz", 0)
    proposals, directions, partials, pending_directions, history = [], [], [], [], []
    statuses, reasons = Counter(), Counter()
    partitions = [{"order": name, "model_start_tick": start, "model_end_tick": start + 480000,
                   "status_counts": Counter(), "reason_counts": Counter(), "proposal_count": 0,
                   "direction_counts": {"lower": 0, "upper": 0}}
                  for name, start in (("forward", 0), ("reverse", 480000))]
    processing, delivery, calls, samples = [], [], [], []
    previous_now, last_event, final_result = None, None, None
    for row in protocol["schedule"]:
        event = take()
        sample = _observation(event, row, identity=identity, protocol=protocol, protocol_hash=protocol_hash,
                              session_id=session_id, previous_now=previous_now)
        now = event["readout_now_ms"]
        result = decoder.consume(sample, now_ms=now)
        if artifacts._canonical(result) != artifacts._canonical(event["readout_result"]):
            raise ValueError("Recorded decoder result differs from complete reconstruction")
        status, reason = result["status"], result["reason"]
        statuses[status] += 1
        reasons[reason] += 1
        partition = partitions[row["observation_index"] // 96]
        partition["status_counts"][status] += 1
        partition["reason_counts"][reason] += 1
        samples.append(sample)
        history.append(sample)
        if status == "direction":
            block = samples[-4:]
            direction = "upper" if sum(s["right_count"] - s["left_count"] for s in block) > 0 else "lower"
            decision = {"direction": direction, "interval": result["interval"], "support": block,
                        "readout_now_ms": now}
            directions.append(decision)
            pending_directions.append(decision)
            partition["direction_counts"][direction] += 1
        if result["proposal"] is not None:
            proposals.append(result["proposal"])
            partition["proposal_count"] += 1
            pending_directions, history = [], []
        elif status == "reset":
            partials.append({"termination": reason, "directions": pending_directions, "input_history": history})
            pending_directions, history = [], []
        processing.append(sample["wall_completion_ms"] - sample["wall_start_ms"])
        delivery.append(now - sample["wall_completion_ms"])
        calls.append(now)
        previous_now, last_event, final_result = now, event, result
    final_state = _checkpoint(take(), "brain-after.npz", 960000)
    if final_state != _hash(last_event["complete_state_sha256_after"]):
        raise ValueError("Final checkpoint and terminal observation state differ")
    if next(events, None) is not None or count != 194:
        raise ValueError("Unexpected extra event/count")
    pending = {**final_result, "directions": pending_directions, "input_history": history}
    if pending_directions:
        partials.append({"termination": "end-of-observation-pending", "directions": pending_directions,
                         "input_history": history})
    selected = Counter(proposal["drink_id"] for proposal in proposals)
    concentration = {drink["id"]: {"count": selected[drink["id"]],
                     "fraction": selected[drink["id"]] / len(proposals) if proposals else 0}
                     for drink in decoder.configuration["drinks"]}
    return {
        "version": VERSION, "validity": "complete-integrity-and-semantics-only",
        "scope": protocol["scope"], "verification_mode": run.verification_mode,
        "engine_mode": declaration["engine_mode"], "protocol_sha256": protocol_hash,
        "configuration_sha256": decoder.configuration_sha256, "session_id": session_id,
        "source": {name: manifest[name] for name in ("schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256")},
        "exact_counts": EXACT_COUNTS, "initial_state_sha256": initial_state, "final_state_sha256": final_state,
        "outcome": "narrow-positive" if proposals else "negative", "proposals": proposals,
        "route_metrics": {"complete_routes": len(proposals), "partial_routes": partials,
                          "directions": directions, "concentration": concentration,
                          "proposal_timings": [{"drink_id": proposal["drink_id"],
                              "model_elapsed_ms": (proposal["completion_tick"] - proposal["path_start_tick"]) / 10,
                              "wall_elapsed_ms": proposal["completion_wall_ms"] - proposal["path_start_wall_ms"],
                              "emission_delivery_ms": proposal["emitted_wall_ms"] - proposal["completion_wall_ms"]}
                              for proposal in proposals],
                          "maximum_selected_fraction": max(value["fraction"] for value in concentration.values())},
        "status_counts": dict(statuses), "reason_counts": dict(reasons),
        "direction_counts": {sign: sum(value["direction"] == sign for value in directions) for sign in ("lower", "upper")},
        "final_pending_state": pending,
        "clocks": {"domain": "declared-single-monotonic-milliseconds", "authenticated": False,
                   "first_observation_start_ms": samples[0]["wall_start_ms"],
                   "last_observation_completion_ms": samples[-1]["wall_completion_ms"],
                   "last_readout_now_ms": calls[-1], "readout_now_ms": calls,
                   "observation_span_ms": samples[-1]["wall_completion_ms"] - samples[0]["wall_start_ms"]},
        "latency_ms": {"processing": processing, "delivery": delivery},
        "order_partitions": partitions, "order_partition_scope": "shared-state descriptive; proposals assigned by completion",
        "limitations": LIMITATIONS,
    }


def inspect_probe(output_dir: Path) -> dict:
    """Read bounded private bytes through EOF; never execute the native model."""
    output = Path(output_dir).absolute()
    protocol, protocol_hash = _read_protocol(output)
    with snapshot_recorded_run(output / "run", limits=READ_LIMITS,
                               checkpoint_byte_limit=MAX_CHECKPOINT_BYTES) as snapshot:
        run = artifacts.verify_run(snapshot, limits=READ_LIMITS)
        # A semantic rejection must release the snapshot's open event stream on Windows.
        with closing(run.iter_events()) as events:
            return _summarize_events(run, protocol, protocol_hash, events)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "inspect", "run"):
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
            result = prepare_probe(args.output_dir)
        elif args.command == "inspect":
            result = inspect_probe(args.output_dir)
        else:
            result = run_probe(args.output_dir, expected_protocol_sha256=args.expected_protocol_sha256,
                               supervision_directory=args.supervision_directory,
                               expected_readiness_sha256=args.expected_readiness_sha256, start_token=args.start_token)
    except (ValueError, OSError, TypeError, OverflowError, RuntimeError, KeyError, AttributeError, ImportError) as error:
        parser.exit(1, f"Continuous motor probe failed: {error}\n")
    print(artifacts._canonical(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
