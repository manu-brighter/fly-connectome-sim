"""A fixed reward-free event pilot and source-bound locked plan exports.

The count-derived motor policy is engineered and unvalidated. Artifact integrity
does not attest native history or semantic understanding of these event cards.
"""

from __future__ import annotations

import base64
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Callable

import numpy as np

from ..engine import FlyEngine, _rgb_input_sha256
from .adapter import LateralMotorAdapter
from .event_cards import (
    HEIGHT, MAX_PROPOSAL_BYTES, RENDERER_RECIPE, WIDTH, _text,
    load_proposal_with_source, render_event_cards, validate_event_proposal,
)
from .measured_replay import GROUPS, _integer, _populations, _ticks
from .recorder import DIGEST, OWNED, RunArtifactError, RunRecorder, VerifiedRun, _canonical, verify_run


ROOT_BRANCH = "event-choice/root"
POLICY_VERSION = "event-card-choice/v1"
ADAPTER = LateralMotorAdapter()
MOTOR_GROUPS = ("motor_left", "motor_right")
SOURCE_FIELDS = ("run_kind", "schema_sha256", "run_metadata_sha256", "events_sha256",
                 "final_scientific_sha256")
CHOICE_RECIPE = {
    "policy_version": POLICY_VERSION, "adapter_version": ADAPTER.version,
    "action_threshold_hz": 1.0, "observation_count": 4, "duration_ticks": 5000,
    "settling_ticks": 15000, "window_start_tick": 15000, "window_end_tick": 20000,
    "stimulation": None, "learning": False, "pathway_detail": False,
    "qualification_detail": False,
}
OBSERVE_FIELDS = {
    "type", "branch_id", "sim_ms", "start_ms", "end_ms", "start_tick", "end_tick",
    "duration_ms", "duration_ticks", "stimulus", "stimulation", "learning",
    "pathway_detail", "qualification_detail", "telemetry", "event_frame",
}
TELEMETRY_FIELDS = {
    "sim_ms", "interval_ms", "compute_seconds", "kernel_seconds", "total_spikes",
    "rates_hz", "turn_hz", "stimulation", "learning", "input_shape", "input_dtype",
    "input_sha256", "engine_identity", "spike_sha256", "memory", "bins",
}
CHECKPOINT_FIELDS = {
    "type", "branch_id", "checkpoint_name", "checkpoint_sha256", "checkpoint_size",
    "sim_ms", "sim_tick",
} | OWNED


def count_readout(counts: dict, populations: dict) -> dict:
    """Apply the unchanged adapter to integer sums over exactly the final 0.5s."""
    if (type(counts) is not dict or set(counts) != set(MOTOR_GROUPS)
            or type(populations) is not dict or set(populations) != set(MOTOR_GROUPS)):
        raise RunArtifactError("Expected the two lateral motor count/population fields")
    rates = {}
    for name in MOTOR_GROUPS:
        population = _integer(populations[name], name + " population", minimum=1,
                              maximum=9007199254740991)
        count = _integer(counts[name], name + " count", maximum=5000 * population)
        rates[name] = count / (population * 0.5)
    return asdict(ADAPTER.adapt({"rates_hz": rates}))


def _selected(readout: dict, proposal: dict) -> str | None:
    action = readout["action"]
    return (proposal["options"][0 if action == "inspect_left" else 1]["id"]
            if action != "defer" else None)


def _frame_payload(frame: np.ndarray) -> dict:
    return {"frame_id": "options", "sha256": _rgb_input_sha256(frame),
            "width": WIDTH, "height": HEIGHT,
            "rgb_base64": base64.b64encode(frame.tobytes(order="C")).decode("ascii")}


def _metadata(identity: dict, proposal: dict, source: dict, frame: dict) -> dict:
    return {
        "engine_identity": identity, "protocol_version": "event-choice/v1",
        "stimulus_version": "event-card-rgb/v1", "family": "event-choice", "seeds": [],
        "factors": {"left_option_id": proposal["options"][0]["id"],
                    "right_option_id": proposal["options"][1]["id"]},
        "proposal": proposal, "proposal_source": source,
        "proposal_sha256": sha256(_canonical(proposal)).hexdigest(),
        "renderer_recipe": RENDERER_RECIPE, "input": frame,
        "choice_recipe": CHOICE_RECIPE, "input_sha256": [frame["sha256"]],
    }


def _groups(identity: dict) -> dict:
    if (type(identity) is not dict or set(identity) != {
            "version", "model_provenance", "neural_groups", "sha256"}
            or identity["version"] != "fly-engine/v1"
            or type(identity["model_provenance"]) is not dict
            or not identity["model_provenance"]):
        raise RunArtifactError("Unsupported event engine identity")
    payload = {key: value for key, value in identity.items() if key != "sha256"}
    expected = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                allow_nan=False).encode("utf-8")).hexdigest()
    if identity["sha256"] != expected:
        raise RunArtifactError("Engine identity hash differs from its maps/provenance")
    groups = _populations(identity)
    for name in GROUPS:
        for index in identity["neural_groups"][name]:
            _integer(index, "neural index", maximum=9007199254740991)
    return groups


def _validated_proposal_source(proposal: dict, source: dict) -> dict:
    """Validate the original import directly, independently of its run envelope."""
    proposal = validate_event_proposal(proposal)
    if (type(source) is not dict or set(source) != {"kind", "name", "size_bytes", "raw_sha256"}
            or source["kind"] != "imported-json"
            or type(source["raw_sha256"]) is not str or not DIGEST.fullmatch(source["raw_sha256"])):
        raise RunArtifactError("Unsupported imported proposal source")
    _text(source["name"], 80, "proposal source name")
    if any(char in source["name"] for char in '/\\:') or source["name"] in {".", ".."}:
        raise RunArtifactError("Invalid proposal source basename")
    _integer(source["size_bytes"], "proposal bytes", minimum=1, maximum=MAX_PROPOSAL_BYTES)
    return proposal


def _validate_metadata(metadata: dict) -> tuple[dict, dict, dict]:
    proposal = _validated_proposal_source(metadata["proposal"], metadata["proposal_source"])
    source = metadata["proposal_source"]
    frame = _frame_payload(render_event_cards(proposal))
    expected = _metadata(metadata["engine_identity"], proposal, source, frame)
    if _canonical(metadata) != _canonical(expected):
        raise RunArtifactError("Event metadata differs from closed proposal/render/choice recipe")
    return proposal, frame, _groups(metadata["engine_identity"])


def _same(actual: object, expected: object, message: str) -> None:
    if _canonical(actual) != _canonical(expected):
        raise RunArtifactError(message)


def _segment(event: dict, index: int, *, identity: dict, groups: dict,
             frame: dict, proposal: dict, recorded: bool = True,
             branch_id: str = ROOT_BRANCH, start_tick: int = 0,
             sequence_start: int = 1) -> tuple[dict, dict]:
    fields = OBSERVE_FIELDS | (OWNED if recorded else set())
    if index == 3:
        fields = fields | {"motor_readout", "event_choice"}
    if (type(event) is not dict or set(event) != fields
            or event["type"] != "observe" or event["branch_id"] != branch_id
            or event["stimulus"] != "options" or event["stimulation"] is not None
            or event["learning"] is not False or event["pathway_detail"] is not False
            or event["qualification_detail"] is not False):
        raise RunArtifactError("Unsupported event observation fields or flags")
    start, end = start_tick + index * 5000, start_tick + (index + 1) * 5000
    for name, expected in (("start_tick", start), ("end_tick", end), ("duration_ticks", 5000)):
        if _integer(event[name], name) != expected:
            raise RunArtifactError("Noncontinuous event observation ticks")
    for name, expected in (("start_ms", start), ("end_ms", end), ("sim_ms", end), ("duration_ms", 5000)):
        if _ticks(event[name]) != expected:
            raise RunArtifactError("Inconsistent event observation clock")
    _same(event["event_frame"], frame, "Recorded event pixels differ from proposal rendering")
    telemetry = event["telemetry"]
    if (type(telemetry) is not dict or set(telemetry) != TELEMETRY_FIELDS
            or telemetry["engine_identity"] != identity or telemetry["learning"] is not False
            or telemetry["stimulation"] is not None or telemetry["input_shape"] != [HEIGHT, WIDTH, 3]
            or telemetry["input_dtype"] != "uint8" or telemetry["input_sha256"] != frame["sha256"]
            or _ticks(telemetry["sim_ms"]) != end or _ticks(telemetry["interval_ms"]) != 5000):
        raise RunArtifactError("Recorded telemetry differs from fixed event input/clock")
    raw_bins = telemetry["bins"]
    if type(raw_bins) is not list or not 1 <= len(raw_bins) <= 50:
        raise RunArtifactError("Missing or excessive event bins")
    bins = []
    cursor = start
    totals = dict.fromkeys(GROUPS, 0)
    for raw in raw_bins:
        if type(raw) is not dict or set(raw) != {"end_ms", "duration_ms", "group_spikes"}:
            raise RunArtifactError("Unsupported event bin")
        duration, bin_end = _ticks(raw["duration_ms"]), _ticks(raw["end_ms"])
        if not 0 < duration <= 100 or bin_end != cursor + duration or bin_end > end:
            raise RunArtifactError("Incomplete or noncontiguous event bins")
        counts = raw["group_spikes"]
        if type(counts) is not dict or set(counts) != set(GROUPS):
            raise RunArtifactError("Missing event population counts")
        for name in GROUPS:
            totals[name] += _integer(counts[name], name + " count", maximum=duration * groups[name])
        bins.append({"end_tick": bin_end, "duration_ticks": duration, "group_spikes": counts})
        cursor = bin_end
    if cursor != end:
        raise RunArtifactError("Incomplete event interval")
    rates = telemetry["rates_hz"]
    if type(rates) is not dict or set(rates) != set(GROUPS):
        raise RunArtifactError("Missing event population rates")
    for name in GROUPS:
        rate = rates[name]
        if (type(rate) not in {float, int} or not math.isfinite(rate) or rate < 0
                or not math.isclose(rate, totals[name] / (groups[name] * 0.5), rel_tol=1e-12, abs_tol=1e-12)):
            raise RunArtifactError("Event rates differ from integer bins/populations")
    turn = telemetry["turn_hz"]
    if (type(turn) not in {float, int} or not math.isfinite(turn)
            or not math.isclose(turn, rates["motor_right"] - rates["motor_left"], rel_tol=1e-12, abs_tol=1e-12)):
        raise RunArtifactError("Event turn rate differs from measured rates")
    total_spikes = _integer(telemetry["total_spikes"], "total spikes")
    if total_spikes < max(totals.values()):
        raise RunArtifactError("Population counts exceed whole-brain spike total")
    counts = {name: totals[name] for name in MOTOR_GROUPS}
    populations = {name: groups[name] for name in MOTOR_GROUPS}
    readout = count_readout(counts, populations)
    if index == 3:
        # Exact adapter equality is deliberate: tolerant raw-rate conservation
        # must never move a strict ±1 boundary or replace count-derived evidence.
        _same(asdict(ADAPTER.adapt(telemetry)), readout,
              "Raw telemetry motor readout differs from count-derived final window")
        _same(event["motor_readout"], {
            "interpretation": "engineered_unvalidated_motor_readout",
            "action_threshold_hz": 1.0, "decision": readout,
        }, "Final same-event motor readout differs from integer bins")
        _same(event["event_choice"], {"policy_version": POLICY_VERSION,
                                     "selected_option_id": _selected(readout, proposal)},
              "Recorded event selection differs from fixed measured policy")
    return {
        "event_sequence": event["sequence"] if recorded else sequence_start + index,
        "branch_id": branch_id, "frame_id": "options", "stimulation": None, "learning": False,
        "source_start_tick": start, "source_end_tick": end,
        "playback_start_tick": start, "playback_end_tick": end, "bins": bins,
    }, {"counts": counts, "populations": populations, "readout": readout}


def _new_output(source: Path | None, output: Path) -> None:
    if source is not None and output.resolve().is_relative_to(source.resolve()):
        raise RunArtifactError("Output must be outside the source artifact")
    if output.exists() or output.is_symlink() or output.is_junction():
        raise FileExistsError(f"Output path already exists: {output}")
    if any(parent.is_symlink() or parent.is_junction() for parent in output.absolute().parents):
        raise RunArtifactError("Output ancestor symlink or junction rejected")
    if any(parent.exists() and not parent.is_dir() for parent in output.absolute().parents):
        raise RunArtifactError("Output ancestor is not a directory")


def _observe_event_phase(engine: FlyEngine, *, proposal: dict, frame: np.ndarray,
                         payload: dict, branch_id: str, start_tick: int,
                         sequence_start: int):
    """Yield four observations without owning engine, checkpoints or recording."""
    if engine.brain.cursor != start_tick:
        raise RunArtifactError("Event phase must start at the current native tick")
    identity = engine.identity()
    groups = _groups(identity)
    for index in range(4):
        start = engine.brain.cursor
        telemetry = engine.observe(frame, 500.0, stimulation=None, learning=False,
                                   pathway_detail=False, qualification_detail=False)
        end = engine.brain.cursor
        if start != start_tick + index * 5000 or end != start + 5000:
            raise RunArtifactError("Actual event observation clock mismatch")
        event = {
            "type": "observe", "branch_id": branch_id, "sim_ms": end / 10,
            "start_ms": start / 10, "end_ms": end / 10, "start_tick": start,
            "end_tick": end, "duration_ms": 500.0, "duration_ticks": 5000,
            "stimulus": "options", "stimulation": None, "learning": False,
            "pathway_detail": False, "qualification_detail": False,
            "telemetry": telemetry, "event_frame": payload,
        }
        if index == 3:
            raw_readout = asdict(ADAPTER.adapt(telemetry))
            event["motor_readout"] = {
                "interpretation": "engineered_unvalidated_motor_readout",
                "action_threshold_hz": 1.0, "decision": raw_readout,
            }
            event["event_choice"] = {"policy_version": POLICY_VERSION,
                                     "selected_option_id": _selected(raw_readout, proposal)}
        _segment(event, index, identity=identity, groups=groups, frame=payload,
                 proposal=proposal, recorded=False, branch_id=branch_id,
                 start_tick=start_tick, sequence_start=sequence_start)
        yield event


def record_event_choice_run(output_dir: str | Path, *, proposal_path: str | Path,
                            engine_factory: Callable[[], FlyEngine]) -> VerifiedRun:
    """Record exactly one fresh two-second trial; a defer is a complete result."""
    proposal, source = load_proposal_with_source(proposal_path)
    frame = render_event_cards(proposal)
    payload = _frame_payload(frame)
    target = Path(output_dir)
    _new_output(None, target)
    engine = engine_factory()
    if (not isinstance(engine, FlyEngine) or engine.brain.cursor != 0
            or _ticks(float(engine.brain.sim_ms)) != 0 or engine.brain.dt != 0.1
            or engine.brain.weights_frozen):
        raise RunArtifactError("Event choice requires one fresh actual 0.1 ms unfrozen engine")
    identity = engine.identity()
    metadata = _metadata(identity, proposal, source, payload)
    groups = _groups(identity)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".event-checkpoint-") as scratch:
        checkpoint = Path(scratch) / "brain.npz"
        with RunRecorder(target, run_kind="pilot", metadata=metadata, root_branch_id=ROOT_BRANCH) as recorder:
            def save(name: str) -> None:
                engine.brain.checkpoint(checkpoint)
                recorder.ingest_checkpoint(name, checkpoint, origin_branch_id=ROOT_BRANCH)
                recorder.append({"type": "checkpoint", "branch_id": ROOT_BRANCH,
                                 "sim_ms": engine.brain.cursor / 10, "sim_tick": engine.brain.cursor,
                                 "checkpoint_name": name})

            save("brain-before.npz")
            for event in _observe_event_phase(
                engine, proposal=proposal, frame=frame, payload=payload,
                branch_id=ROOT_BRANCH, start_tick=0, sequence_start=1,
            ):
                recorder.append(event)
            save("brain-after.npz")
    return verify_run(target)


def _export_data(run: VerifiedRun) -> dict:
    manifest = run.manifest
    if (manifest["run_kind"] != "pilot" or manifest["root_branch_id"] != ROOT_BRANCH
            or set(manifest["checkpoints"]) != {"brain-before.npz", "brain-after.npz"}
            or manifest["state_anchors"] or run.verification_mode != "integrity-only"):
        raise RunArtifactError("Only ordinary sealed event-choice root pilots are supported")
    metadata = manifest["metadata"]
    proposal, frame, groups = _validate_metadata(metadata)
    segments = []
    final = None
    event_count = 0
    for event in run.iter_events():
        sequence = event_count
        event_count += 1
        if (sequence > 5 or event["branch_id"] != ROOT_BRANCH
                or _integer(event["sequence"], "event sequence") != sequence):
            raise RunArtifactError("Unsupported event branch, operation or event count")
        if sequence in (0, 5):
            before = sequence == 0
            tick = 0 if before else 20000
            if (set(event) != CHECKPOINT_FIELDS or event["type"] != "checkpoint"
                    or event["checkpoint_name"] != ("brain-before.npz" if before else "brain-after.npz")
                    or _integer(event["sim_tick"], "checkpoint tick") != tick
                    or _ticks(event["sim_ms"]) != tick):
                raise RunArtifactError("Invalid event checkpoint occurrence")
            continue
        segment, evidence = _segment(event, sequence - 1, identity=metadata["engine_identity"],
                                     groups=groups, frame=frame, proposal=proposal)
        segments.append(segment)
        if sequence == 4:
            final = {
                "policy_version": POLICY_VERSION, "effective_tick": 20000,
                "event_sequence": sequence, "event_scientific_sha256": event["scientific_sha256"],
                "window_start_tick": 15000, "window_end_tick": 20000, **evidence,
                "selected_option_id": _selected(evidence["readout"], proposal),
            }
    # Do not return or publish until the ordinary iterator has reached normal EOF.
    if (event_count != 6 or len(segments) != 4 or final is None
            or sum(len(segment["bins"]) for segment in segments) != 200):
        raise RunArtifactError("Incomplete or oversized event-choice run")
    source = {**{name: manifest[name] for name in SOURCE_FIELDS}, "verification_mode": "integrity-only"}
    selected_id = final["selected_option_id"]
    selected = next((option for option in proposal["options"] if option["id"] == selected_id), None)
    plan = {
        "version": "event-plan/v1", "status": "selected" if selected is not None else "deferred",
        "brief": proposal["brief"], "selected_option_id": selected_id, "selected_option": selected,
        "decision_ref": {"event_sequence": final["event_sequence"],
                         "scientific_sha256": final["event_scientific_sha256"],
                         "input_sha256": frame["sha256"], "policy_version": POLICY_VERSION},
        "source": source,
    }
    return {
        "version": "event-choice-replay/v1", "tick_ms": 0.1,
        "source": {**source, "metadata": metadata}, "groups": groups,
        "inputs": {"options": {key: value for key, value in frame.items() if key != "frame_id"}},
        "segments": segments, "duration_ticks": 20000, "decision": final, "plan": plan,
    }


def _export(run_dir: str | Path, output_path: str | Path, *, plan_only: bool) -> dict:
    output = Path(output_path)
    _new_output(Path(run_dir), output)
    run = verify_run(run_dir)
    try:
        replay = _export_data(run)
    except (KeyError, TypeError, AttributeError, IndexError, OverflowError) as error:
        raise RunArtifactError(f"Incomplete event-choice source: {error}") from error
    data = replay["plan"] if plan_only else replay
    raw = _canonical(data) + b"\n"
    if len(raw) > (64 * 1024 if plan_only else 2 * 1024 * 1024):
        raise RunArtifactError("Event export exceeds its closed byte bound")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".event-export-", suffix=".tmp", delete=False) as writer:
            temporary = Path(writer.name)
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        if os.name == "nt":
            os.rename(temporary, output)
        else:
            os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return data


def export_event_replay(run_dir: str | Path, output_path: str | Path) -> dict:
    """Independently verify complete EOF before publishing a new replay."""
    return _export(run_dir, output_path, plan_only=False)


def export_event_plan(run_dir: str | Path, output_path: str | Path) -> dict:
    """Independently derive the exact frozen proposal or explicit deferred plan."""
    return _export(run_dir, output_path, plan_only=True)
