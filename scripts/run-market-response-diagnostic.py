"""Fixed matched-state image diagnostic; offline integrity is not native attestation."""

from __future__ import annotations

import argparse
from hashlib import sha256
import math
from pathlib import Path
import tempfile

import numpy as np

from fly_connectome_sim.engine import FlyEngine, _rgb_input_sha256
from fly_connectome_sim.experiment import recorder as artifacts
from fly_connectome_sim.experiment.cell_activity import LOCKS, build_header
from fly_connectome_sim.neural.checkpoint import model_fingerprint
from fly_connectome_sim.neural.common import DATA
from market_artifacts import _copy_bounded, _safe_directory, snapshot_recorded_run, write_json_exclusive
from market_supervision import production_start


VERSION = "market-response-diagnostic/v1"
ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
ARMS = (("control-1", "black"), ("vertical-left", "A"), ("vertical-right", "B"),
        ("vertical-left-repeat", "A"), ("control-2", "black"), ("horizontal-top", "C"),
        ("horizontal-bottom", "D"), ("horizontal-top-repeat", "C"))
READ_LIMITS = artifacts.RunReadLimits(
    max_manifest_bytes=2 * 1024 * 1024,
    max_event_line_bytes=1024 * 1024,
    max_events_bytes=64 * 1024 * 1024,
    max_events=79,
    max_checkpoints=3,
)
MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024
REPEATS = (("control-1", "control-2"), ("vertical-left", "vertical-left-repeat"),
           ("horizontal-top", "horizontal-top-repeat"))


def frames() -> dict[str, np.ndarray]:
    """Exact logical RGB bytes, without resize, image files or random selection."""
    result = {name: np.zeros((64, 64, 3), dtype=np.uint8) for name in ("black", "A", "B", "C", "D")}
    result["A"][:, :32] = 255
    result["B"][:, 32:] = 255
    result["C"][:32] = 255
    result["D"][32:] = 255
    return result


def _digest(value) -> str:
    return sha256(artifacts._canonical(value)).hexdigest()


def _file_digest(path: Path) -> str:
    return artifacts._digest_file(path)[0]


def _protocol() -> dict:
    sources = [Path(__file__).resolve(), ROOT / "scripts/market_artifacts.py",
               ROOT / "scripts/market_supervision.py", ROOT / "scripts/supervise-market-response.ps1",
               ROOT / "src/fly_connectome_sim/neural/datasets.json"]
    sources.extend(sorted((ROOT / "src/fly_connectome_sim/schemas").glob("*.json")))
    source_hashes = {path.relative_to(ROOT).as_posix(): _file_digest(path) for path in sources}
    source_hashes.update({f"src/fly_connectome_sim/neural/{path.name}": _file_digest(path)
                          for path in sorted(LOCKS.glob("*.lock.json"))})
    return {
        "version": VERSION,
        "source": {"model_fingerprint": model_fingerprint(),
                   "files_sha256": source_hashes},
        "frame_shape": [64, 64, 3], "frame_dtype": "uint8",
        "frame_sha256": {name: _rgb_input_sha256(frame) for name, frame in frames().items()},
        "arms": [{"id": arm, "frame": frame} for arm, frame in ARMS],
        "prefix_ms": 2000, "arm_ms": 4000, "observation_ms": 500,
        "observations": 68, "events": 79, "native_bins": 3400, "actual_advance_ms": 34000,
        "primary_window_index": 7, "secondary_window_indices": list(range(8)),
        "grouping": {"method": "first-220-source-id-ordered-kc-rank-modulo-20/v1",
                     "groups": 20, "cells_per_group": 11, "remaining_kc": "excluded"},
        "observation": {"learning": False, "stimulation": None,
                        "pathway_detail": False, "qualification_detail": False,
                        "passive_dynamics": "normal-engine-defaults"},
        "limits": {"wall_seconds": 900, "peak_rss_bytes": 4 * 1024**3,
                   "new_output_evidence_bytes": 256 * 1024**2, "poll_seconds_max": 2,
                   "manifest_bytes": READ_LIMITS.max_manifest_bytes,
                   "event_line_bytes": READ_LIMITS.max_event_line_bytes,
                   "events_bytes": READ_LIMITS.max_events_bytes,
                   "checkpoint_bytes_each": MAX_CHECKPOINT_BYTES},
        "verification_mode": "integrity-only",
        "scope": "matched-state-image-response",
    }


def prepare_diagnostic(output_dir: Path) -> dict:
    """Freeze source/protocol only. No engine or native kernel is constructed."""
    output = Path(output_dir).absolute()
    _safe_directory(output.parent)
    protocol = _protocol()
    output.mkdir()
    write_json_exclusive(protocol, output / "protocol.json")
    return protocol


def _read_protocol(output: Path, expected: str | None = None) -> tuple[dict, str]:
    _safe_directory(output)
    with tempfile.TemporaryDirectory(prefix="fly-market-protocol-") as scratch:
        copied = Path(scratch) / "protocol.json"
        _copy_bounded(output / "protocol.json", copied, READ_LIMITS.max_manifest_bytes)
        raw = copied.read_bytes()
    digest = sha256(raw).hexdigest()
    protocol = artifacts._strict_load(raw)
    if (expected is not None and digest != expected) or raw != artifacts._canonical(protocol) + b"\n":
        raise ValueError("Prepared protocol hash/encoding differs")
    if artifacts._canonical(protocol) != artifacts._canonical(_protocol()):
        raise ValueError("Prepared protocol or current source identity differs")
    return protocol, digest


def _integer(value, upper: int | None = None) -> int:
    if type(value) is not int or value < 0 or (upper is not None and value > upper):
        raise ValueError("Invalid nonnegative integer/count")
    return value


def _number(value) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Invalid finite nonnegative number")
    return value


def _hash(value) -> str:
    if type(value) is not str or not artifacts.DIGEST.fullmatch(value):
        raise ValueError("Missing complete-state/source hash")
    return value


def _clock(value, tick: int) -> None:
    if _number(value) != tick / 10:
        raise ValueError("Contradictory model clock")


def _grouping(header: dict, identity: dict, protocol: dict) -> dict:
    """Validate frozen membership before using any activity; group fixed KC ranks."""
    if (type(header) is not dict or header.get("type") != "header"
            or header.get("version") != "cell-activity-raw/v1"
            or header.get("engine_identity") != identity
            or _digest({key: value for key, value in identity.items() if key != "sha256"}) != identity.get("sha256")
            or identity.get("model_provenance", {}).get("model_fingerprint") != protocol["source"]["model_fingerprint"]):
        raise ValueError("Frozen header/engine/source identity differs")
    populations = identity.get("neural_groups")
    if type(populations) is not dict or set(populations) != set(GROUPS):
        raise ValueError("Invalid neural group declarations")
    for members in populations.values():
        if type(members) is not list or not members or len(set(members)) != len(members):
            raise ValueError("Empty or duplicate neural group")
        for index in members:
            _integer(index)
    source = header.get("source")
    if type(source) is not dict or set(source) != {"graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "annotations_sha256"}:
        raise ValueError("Missing frozen source bindings")
    locks = {}
    for name in ("arrays.lock.json", "sources.lock.json"):
        with (LOCKS / name).open("rb") as stream:
            raw = stream.read(READ_LIMITS.max_manifest_bytes + 1)
        key = f"src/fly_connectome_sim/neural/{name}"
        if (len(raw) > READ_LIMITS.max_manifest_bytes
                or sha256(raw).hexdigest() != protocol["source"]["files_sha256"].get(key)):
            raise ValueError("Source lock bytes differ from frozen protocol")
        locks[name] = artifacts._strict_load(raw)
    for name, value in source.items():
        _hash(value)
        if name != "annotations_sha256" and identity["model_provenance"].get(name) != value:
            raise ValueError("Header graph source differs from engine")
    for name in ("ids", "ptr", "post"):
        field = f"graph_{name}_sha256"
        if source[field] != locks["arrays.lock.json"][name]:
            raise ValueError("Header/engine graph source differs from frozen array lock")
    if source["annotations_sha256"] != locks["sources.lock.json"]["annotations.feather"]["sha256"]:
        raise ValueError("Header annotations source differs from frozen source lock")
    cells = header.get("cells")
    if type(cells) is not list or not 220 <= len(cells) <= 256:
        raise ValueError("Fixed cohort requires at least 220 KC cells and at most 256 cells")
    indices, sources, kc_slots = [], [], []
    selected = dict.fromkeys(GROUPS, 0)
    for slot, cell in enumerate(cells):
        if type(cell) is not dict or set(cell) != {"model_index", "source_id", "groups", "soma"}:
            raise ValueError("Invalid frozen cell declaration")
        index, source_id = _integer(cell["model_index"]), _integer(cell["source_id"], 9007199254740991)
        memberships = [name for name in GROUPS if index in populations[name]]
        if not source_id or not memberships or cell["groups"] != memberships:
            raise ValueError("Cell membership contradicts population declaration")
        if cell["soma"] is not None and (type(cell["soma"]) is not list or len(cell["soma"]) != 3
                or any(type(v) is not int or abs(v) > 9007199254740991 for v in cell["soma"])):
            raise ValueError("Invalid soma declaration")
        indices.append(index)
        sources.append(source_id)
        for name in memberships:
            selected[name] += 1
        if "kc" in memberships:
            kc_slots.append(slot)
    if len(set(indices)) != len(indices) or sources != sorted(set(sources)) or len(kc_slots) < 220:
        raise ValueError("Cohort IDs/order or required 220 KC cells differ")
    selection = header.get("selection")
    if selection != {"method": "mandatory-groups-kc-stride/v1", "limit": 256,
                     "group_population_counts": {name: len(populations[name]) for name in GROUPS},
                     "group_selected_counts": selected}:
        raise ValueError("Cohort group declaration/count mismatch")
    if any(selected[name] != len(populations[name]) for name in GROUPS if name != "kc"):
        raise ValueError("Mandatory populations are incompletely recorded")
    return {"method": protocol["grouping"]["method"],
            "groups": [kc_slots[:220][rank::20] for rank in range(20)],
            "excluded_kc_slots": kc_slots[220:], "cohort_model_indices": indices,
            "cohort_source_ids": sources}


def run_diagnostic(output_dir: Path, *, expected_protocol_sha256: str, engine_factory=None,
                   supervision_directory: Path | None = None, expected_readiness_sha256: str | None = None,
                   start_token: str | None = None) -> dict:
    """Production requires an actual-PID owned-job release before construction."""
    if engine_factory is not None:
        return _run_diagnostic(output_dir, expected_protocol_sha256=expected_protocol_sha256,
                               engine_factory=engine_factory)
    output = Path(output_dir).absolute()
    _read_protocol(output, expected_protocol_sha256)
    with production_start(output, expected_protocol_sha256, supervision_directory,
                          expected_readiness_sha256, start_token):
        return _run_diagnostic(output, expected_protocol_sha256=expected_protocol_sha256,
                               engine_factory=FlyEngine.from_prepared_graph)


def _run_diagnostic(output_dir: Path, *, expected_protocol_sha256: str, engine_factory) -> dict:
    """Exact acquisition; the only production caller holds the process guard."""
    output = Path(output_dir).absolute()
    _safe_directory(output)
    if set(path.name for path in output.iterdir()) != {"protocol.json"}:
        raise ValueError("Run requires exactly the new prepared protocol; no resume")
    _hash(expected_protocol_sha256)
    protocol, protocol_hash = _read_protocol(output, expected_protocol_sha256)
    engine = engine_factory()
    identity = engine.identity()
    header = build_header(identity, DATA)
    grouping = _grouping(header, identity, protocol)
    declaration = {"protocol": protocol, "protocol_sha256": protocol_hash, "header": header,
                   "header_sha256": _digest(header), "grouping": grouping, "grouping_sha256": _digest(grouping)}
    metadata = {"engine_identity": identity, "protocol_version": VERSION, "stimulus_version": "market-rgb-halves/v1",
                "family": "matched-state-image-response", "seeds": [], "factors": {},
                "input_sha256": sorted(protocol["frame_sha256"].values()), "diagnostic": declaration}
    buffered = []

    def capture(row):
        if len(buffered) >= 50:
            raise ValueError("Cell observer exceeds one-observation 50-bin buffer")
        buffered.append(artifacts._strict_load(artifacts._canonical(row)))

    engine.configure_cell_observer(grouping["cohort_model_indices"], capture)
    inputs = frames()
    with tempfile.TemporaryDirectory(prefix=".checkpoint-", dir=output) as scratch:
        checkpoint = Path(scratch) / "state.npz"
        with artifacts.RunRecorder(output / "run", run_kind="pilot", metadata=metadata, root_branch_id="prefix") as recorder:

            def save(name, branch):
                if engine.identity() != identity:
                    raise ValueError("Engine identity changed")
                engine.brain.checkpoint(checkpoint)
                if checkpoint.stat().st_size > MAX_CHECKPOINT_BYTES:
                    raise ValueError("Checkpoint exceeds read limit")
                digest = recorder.ingest_checkpoint(name, checkpoint, origin_branch_id=branch)
                sequence = recorder.next_sequence
                state = _hash(engine.brain.checkpoint_state_sha256())
                recorder.append({"type": "checkpoint", "branch_id": branch,
                                 "sim_ms": float(engine.brain.sim_ms), "sim_tick": round(engine.brain.sim_ms * 10),
                                 "checkpoint_name": name, "complete_state_sha256": state})
                return digest, sequence, state

            def observe(branch, frame_name, count):
                for window in range(count):
                    if buffered or engine.identity() != identity:
                        raise ValueError("Unexpected buffered bins or changed engine identity")
                    start = round(float(engine.brain.sim_ms) * 10)
                    telemetry = engine.observe(inputs[frame_name], 500, learning=False, stimulation=None,
                                               pathway_detail=False, qualification_detail=False)
                    event = {"type": "observe", "branch_id": branch, "stimulus": frame_name,
                             "sim_ms": telemetry["sim_ms"], "start_tick": start, "end_tick": start + 5000,
                             "start_ms": start / 10, "end_ms": (start + 5000) / 10,
                             "duration_ms": 500, "duration_ticks": 5000,
                             "learning": False, "stimulation": None,
                             "pathway_detail": False, "qualification_detail": False,
                             "input_sha256": protocol["frame_sha256"][frame_name],
                             "telemetry": telemetry, "cell_bins": buffered}
                    if branch != "prefix" and window == count - 1:
                        event["complete_state_sha256_after"] = _hash(engine.brain.checkpoint_state_sha256())
                    recorder.append(event)
                    buffered.clear()

            _clock(float(engine.brain.sim_ms), 0)
            save("brain-before.npz", "prefix")
            observe("prefix", "black", 4)
            common_hash, common_sequence, common_state = save("black-prefix.npz", "prefix")
            common_path = output / "run/checkpoints/black-prefix.npz"
            for branch, frame_name in ARMS:
                if _file_digest(common_path) != common_hash:
                    raise ValueError("Common checkpoint bytes changed")
                engine.brain.restore(common_path)
                if (engine.identity() != identity or engine.brain.checkpoint_state_sha256() != common_state
                        or _file_digest(common_path) != common_hash):
                    raise ValueError("Restored complete state or engine identity differs")
                _clock(float(engine.brain.sim_ms), 20000)
                recorder.append({"type": "branch_start", "branch_id": branch, "sim_ms": 2000,
                                 "sim_tick": 20000, "parent_branch_id": "prefix",
                                 "parent_checkpoint_name": "black-prefix.npz", "parent_checkpoint_sequence": common_sequence,
                                 "parent_checkpoint_sha256": common_hash, "complete_state_sha256": common_state})
                observe(branch, frame_name, 8)
            save("brain-after.npz", ARMS[-1][0])
    summary = inspect_diagnostic(output)
    write_json_exclusive(summary, output / "summary.json")
    receipt = {"version": VERSION, "status": "complete", "verification_mode": "integrity-only",
               "protocol_sha256": protocol_hash, "summary_sha256": _file_digest(output / "summary.json"),
               "source": summary["source"], "observations": summary["observations"],
               "bins": summary["bins"], "simulated_ms": summary["simulated_ms"],
               "final_state_sha256": summary["final_state_sha256"],
               "scope": "execution-and-offline-integrity-bookkeeping"}
    write_json_exclusive(receipt, output / "receipt.json")
    return receipt


def _observation(event: dict, *, branch: str, frame: str, start: int, ordinal: int,
                 identity: dict, header: dict, protocol: dict, grouping: dict) -> tuple[dict, dict]:
    if (event.get("type") != "observe" or event.get("branch_id") != branch or event.get("stimulus") != frame
            or any(key.startswith("parent_") for key in event) or "operation_version" in event
            or event.get("input_sha256") != protocol["frame_sha256"][frame]):
        raise ValueError("Unexpected observation arm/frame/binding")
    end = start + 5000
    for field, expected in (("start_tick", start), ("end_tick", end), ("duration_ticks", 5000)):
        if _integer(event.get(field)) != expected:
            raise ValueError("Observation tick mismatch")
    for field, tick in (("sim_ms", end), ("start_ms", start), ("end_ms", end), ("duration_ms", 5000)):
        _clock(event.get(field), tick)
    telemetry = event.get("telemetry")
    if type(telemetry) is not dict or telemetry.get("engine_identity") != identity:
        raise ValueError("Observation engine identity differs")
    for record in (event, telemetry):
        if record.get("learning") is not False or "stimulation" not in record or record["stimulation"] is not None:
            raise ValueError("Diagnostic requires no learning or external stimulation")
    if event.get("pathway_detail") is not False or event.get("qualification_detail") is not False:
        raise ValueError("Unexpected observation detail mode")
    if "pathway_detail" in telemetry or "qualification_detail" in telemetry:
        raise ValueError("Unexpected detail telemetry")
    _clock(telemetry.get("sim_ms"), end)
    _clock(telemetry.get("interval_ms"), 5000)
    for field in ("compute_seconds", "kernel_seconds"):
        _number(telemetry.get(field))
    if (telemetry.get("input_shape") != [64, 64, 3] or telemetry.get("input_dtype") != "uint8"
            or telemetry.get("input_sha256") != protocol["frame_sha256"][frame]):
        raise ValueError("Telemetry frame differs")
    native, cells = telemetry.get("bins"), event.get("cell_bins")
    if type(native) is not list or type(cells) is not list or len(native) != 50 or len(cells) != 50:
        raise ValueError("Exactly 50 aligned native/cell bins required")
    populations = identity["neural_groups"]
    totals = dict.fromkeys(GROUPS, 0)
    cell_totals = [0] * len(header["cells"])
    native_projection, cell_projection = [], []
    for index, (native_bin, cell_bin) in enumerate(zip(native, cells)):
        bin_start, bin_end = start + 100 * index, start + 100 * (index + 1)
        if type(native_bin) is not dict or set(native_bin) != {"end_ms", "duration_ms", "group_spikes"}:
            raise ValueError("Unexpected native bin fields")
        _clock(native_bin["end_ms"], bin_end)
        _clock(native_bin["duration_ms"], 100)
        if type(cell_bin) is not dict or set(cell_bin) != {"observation_index", "bin_index", "start_tick", "end_tick", "counts"}:
            raise ValueError("Unexpected cell bin fields")
        for field, expected in (("observation_index", ordinal), ("bin_index", index),
                                ("start_tick", bin_start), ("end_tick", bin_end)):
            if _integer(cell_bin[field]) != expected:
                raise ValueError("Cell/native bin clock/order mismatch")
        counts, population_counts = cell_bin["counts"], native_bin["group_spikes"]
        if type(counts) is not list or len(counts) != len(cell_totals):
            raise ValueError("Wrong cell count vector")
        for slot, count in enumerate(counts):
            cell_totals[slot] += _integer(count, 100)
        if type(population_counts) is not dict or set(population_counts) != set(GROUPS):
            raise ValueError("Wrong population count keys")
        for name in GROUPS:
            population = _integer(population_counts[name], 100 * len(populations[name]))
            selected = sum(counts[slot] for slot, cell in enumerate(header["cells"]) if name in cell["groups"])
            full = header["selection"]["group_selected_counts"][name] == len(populations[name])
            if selected > population or (full and selected != population):
                raise ValueError("Cell counts contradict native population counts")
            for other in GROUPS:
                if set(populations[name]) <= set(populations[other]) and population > _integer(population_counts[other]):
                    raise ValueError("Population counts contradict membership inclusion")
            totals[name] += population
        native_projection.append(native_bin)
        cell_projection.append({key: value for key, value in cell_bin.items() if key != "observation_index"})
    rates = telemetry.get("rates_hz")
    if type(rates) is not dict or set(rates) != set(GROUPS):
        raise ValueError("Population rate keys differ")
    for name in GROUPS:
        expected = totals[name] / (len(populations[name]) * 0.5)
        if not math.isclose(_number(rates[name]), expected, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Population rate/count mismatch")
    metrics = {"group_counts": [sum(cell_totals[slot] for slot in members) for members in grouping["groups"]],
               "whole_kc_count": totals["kc"], "motor_left_count": totals["motor_left"],
               "motor_right_count": totals["motor_right"],
               "signed_dna02_hz": rates["motor_right"] - rates["motor_left"]}
    projection = {"start_tick": start, "end_tick": end, "duration_ticks": 5000,
                  "sim_ms": event["sim_ms"], "start_ms": event["start_ms"], "end_ms": event["end_ms"],
                  "duration_ms": event["duration_ms"], "input_sha256": event["input_sha256"],
                  "learning": event["learning"], "stimulation": event["stimulation"],
                  "telemetry_sim_ms": telemetry["sim_ms"], "interval_ms": telemetry["interval_ms"],
                  "telemetry_learning": telemetry["learning"], "telemetry_stimulation": telemetry["stimulation"],
                  "rates_hz": rates, "bins": native_projection, "cell_bins": cell_projection}
    if "complete_state_sha256_after" in event:
        projection["complete_state_sha256_after"] = _hash(event["complete_state_sha256_after"])
    return metrics, projection


def _differences(windows: dict, index: int) -> dict:
    pairs = (("A-B", "vertical-left", "vertical-right"), ("C-D", "horizontal-top", "horizontal-bottom"),
             ("A-black", "vertical-left", "control-1"), ("B-black", "vertical-right", "control-1"),
             ("C-black", "horizontal-top", "control-2"), ("D-black", "horizontal-bottom", "control-2"),
             ("black-black-repeat", "control-1", "control-2"),
             ("A-A-repeat", "vertical-left", "vertical-left-repeat"),
             ("C-C-repeat", "horizontal-top", "horizontal-top-repeat"))
    comparisons = {}
    for label, left, right in pairs:
        a, b = windows[left][index], windows[right][index]
        comparisons[label] = {key: ([x - y for x, y in zip(a[key], b[key])] if key == "group_counts"
                                   else a[key] - b[key]) for key in a}
    return {"window_index": index, "relative_start_ms": index * 500, "relative_end_ms": (index + 1) * 500,
            "model_start_ms": 2000 + index * 500, "model_end_ms": 2500 + index * 500,
            "arms": {arm: values[index] for arm, values in windows.items()}, "comparisons": comparisons,
            "any_difference": any(any(value) if isinstance(value, list) else bool(value)
                                  for comparison in comparisons.values() for value in comparison.values())}


def _summarize(run: artifacts.VerifiedRun, protocol: dict, protocol_hash: str) -> dict:
    manifest = run.manifest
    metadata = manifest["metadata"]
    declaration = metadata.get("diagnostic")
    if (manifest["run_kind"] != "pilot" or manifest["root_branch_id"] != "prefix"
            or metadata["protocol_version"] != VERSION or metadata["stimulus_version"] != "market-rgb-halves/v1"
            or metadata["family"] != "matched-state-image-response" or metadata["seeds"] != []
            or metadata["factors"] != {} or metadata["input_sha256"] != sorted(protocol["frame_sha256"].values())
            or type(declaration) is not dict or declaration.get("protocol") != protocol
            or declaration.get("protocol_sha256") != protocol_hash):
        raise ValueError("Run protocol/source binding differs")
    identity = metadata["engine_identity"]
    header = declaration["header"]
    grouping = _grouping(header, identity, protocol)
    if (declaration.get("header_sha256") != _digest(header) or declaration.get("grouping") != grouping
            or declaration.get("grouping_sha256") != _digest(grouping)):
        raise ValueError("Frozen cohort/grouping hash differs")
    if set(manifest["checkpoints"]) != {"brain-before.npz", "black-prefix.npz", "brain-after.npz"}:
        raise ValueError("Diagnostic requires exactly three checkpoints")
    events = iter(run.iter_events())
    count = 0

    def take():
        nonlocal count
        try:
            event = next(events)
        except StopIteration as error:
            raise ValueError("Missing protocol event/arm") from error
        count += 1
        return event

    def checkpoint(event, name, branch, tick):
        if (event.get("type") != "checkpoint" or event.get("branch_id") != branch
                or event.get("checkpoint_name") != name or _integer(event.get("sim_tick")) != tick
                or any(key.startswith("parent_") for key in event) or "operation_version" in event):
            raise ValueError("Checkpoint route/order differs")
        _clock(event["sim_ms"], tick)
        return _hash(event.get("complete_state_sha256"))

    initial_state = checkpoint(take(), "brain-before.npz", "prefix", 0)
    for window in range(4):
        event = take()
        _observation(event, branch="prefix", frame="black", start=window * 5000, ordinal=window,
                     identity=identity, header=header, protocol=protocol, grouping=grouping)
        if "complete_state_sha256_after" in event:
            raise ValueError("Unexpected prefix terminal-state declaration")
    common = take()
    common_state = checkpoint(common, "black-prefix.npz", "prefix", 20000)
    windows, projections, final_states = {}, {}, {}
    for arm_index, (arm, frame) in enumerate(ARMS):
        fork = take()
        if (fork.get("type") != "branch_start" or fork.get("branch_id") != arm
                or fork.get("parent_branch_id") != "prefix" or fork.get("parent_checkpoint_name") != "black-prefix.npz"
                or _integer(fork.get("parent_checkpoint_sequence")) != common["sequence"]
                or fork.get("parent_checkpoint_sha256") != common["checkpoint_sha256"]
                or fork.get("complete_state_sha256") != common_state or _integer(fork.get("sim_tick")) != 20000
                or "operation_version" in fork or "parent_state_anchor_sha256" in fork):
            raise ValueError("Arm fork does not bind common checkpoint/state")
        _clock(fork["sim_ms"], 20000)
        windows[arm], projections[arm] = [], []
        for window in range(8):
            event = take()
            metrics, projection = _observation(event, branch=arm, frame=frame, start=20000 + window * 5000,
                ordinal=4 + arm_index * 8 + window, identity=identity, header=header, protocol=protocol, grouping=grouping)
            if window == 7:
                final_states[arm] = _hash(event.get("complete_state_sha256_after"))
            elif "complete_state_sha256_after" in event:
                raise ValueError("Unexpected early terminal-state declaration")
            windows[arm].append(metrics)
            # Keep only bounded projection digests across observations, never all callback arrays.
            projections[arm].append(_digest(projection))
    final_state = checkpoint(take(), "brain-after.npz", ARMS[-1][0], 60000)
    if final_state != final_states[ARMS[-1][0]]:
        raise ValueError("Final checkpoint/observed complete-state hash differs")
    if next(events, None) is not None or count != 79:
        raise ValueError("Unexpected extra event/count")
    repeats = {f"{left}={right}": projections[left] == projections[right] and final_states[left] == final_states[right]
               for left, right in REPEATS}
    if not all(repeats.values()):
        raise ValueError("Repeated scientific outputs/complete states differ; comparisons invalid")
    secondary = [_differences(windows, index) for index in range(8)]
    return {"version": VERSION, "scope": "matched-state-image-response", "verification_mode": run.verification_mode,
            "protocol_sha256": protocol_hash,
            "source": {name: manifest[name] for name in ("schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256")},
            "header_sha256": declaration["header_sha256"], "grouping": grouping,
            "observations": 68, "bins": 3400, "simulated_ms": 34000, "events": 79,
            "initial_state_sha256": initial_state, "common_state_sha256": common_state,
            "arm_final_state_sha256": final_states, "final_state_sha256": final_state,
            "repeats": repeats, "primary": secondary[7], "secondary": secondary,
            "limitations": ["Input-dependent counts only; no semantic or learning claim.",
                            "Twenty derived groups do not establish independent drink channels.",
                            "No price mapping, real-time or twelve-hour qualification.",
                            "Integrity-only audit is not native replay attestation.",
                            "Null primary results cannot be rescued by secondary windows.",
                            "Equal whole-frame brightness does not match receptor drive."]}


def inspect_diagnostic(output_dir: Path) -> dict:
    """Check all bounded raw bytes and exact semantics before deriving comparisons."""
    output = Path(output_dir).absolute()
    protocol, protocol_hash = _read_protocol(output)
    with snapshot_recorded_run(output / "run", limits=READ_LIMITS,
                               checkpoint_byte_limit=MAX_CHECKPOINT_BYTES) as snapshot:
        run = artifacts.verify_run(snapshot, limits=READ_LIMITS)
        return _summarize(run, protocol, protocol_hash)


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
            result = prepare_diagnostic(args.output_dir)
        elif args.command == "run":
            result = run_diagnostic(args.output_dir, expected_protocol_sha256=args.expected_protocol_sha256,
                                    supervision_directory=args.supervision_directory,
                                    expected_readiness_sha256=args.expected_readiness_sha256,
                                    start_token=args.start_token)
        else:
            result = inspect_diagnostic(args.output_dir)
    except (ValueError, OSError, TypeError, OverflowError, RuntimeError, KeyError, AttributeError) as error:
        parser.exit(1, f"Market diagnostic failed: {error}\n")
    print(artifacts._canonical(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
