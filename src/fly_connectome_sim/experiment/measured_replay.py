"""Record an ordinary observation pilot and export its measured replay subset.

The compact file retains source integrity bindings; it is not native-history
attestation, a training assay, or evidence of biological behavior.
"""

from __future__ import annotations

import base64
from decimal import Decimal
import math
import os
from pathlib import Path
import tempfile
from typing import Callable

import numpy as np

from ..engine import FlyEngine, _rgb_input_sha256
from .recorder import RunArtifactError, RunRecorder, VerifiedRun, _canonical, verify_run
from .stimuli import AssayStimuli


GROUPS = ("kc", "pam11", "ppl101", "mbon07", "mbon11", "motor_left", "motor_right")
SEQUENCE = ("A", "black", "B", "black")
ROOT_BRANCH = "measured-observation/root"


def _integer(value: object, name: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise RunArtifactError(f"Invalid integer {name}")
    return value


def _ticks(value: object) -> int:
    if type(value) not in {float, int} or not math.isfinite(value) or value < 0:
        raise RunArtifactError("Invalid simulation clock")
    ticks = Decimal(str(value)) * 10
    if ticks != ticks.to_integral_value():
        raise RunArtifactError("Simulation clock is outside the exact 0.1 ms lattice")
    return int(ticks)


def _frames(seed: int) -> dict[str, np.ndarray]:
    stimuli = AssayStimuli(seed, "qualification", width=32, height=32)
    return {name: (np.zeros((32, 32, 3), dtype=np.uint8) if name == "black"
                   else stimuli.frame(name, side="center", color_assignment="fixed"))
            for name in ("A", "B", "black")}


def _metadata(identity: dict, seed: int, cycles: int, frames: dict) -> dict:
    hashes = {name: _rgb_input_sha256(frame) for name, frame in frames.items()}
    return {
        "engine_identity": identity,
        "protocol_version": "measured-observation/v1",
        "stimulus_version": "associative-stimuli/v1",
        "family": "measured-observation",
        "seeds": [seed],
        "factors": {"cycles": cycles, "side": "center", "color_assignment": "fixed"},
        "stimulus_recipe": {
            "generator": "AssayStimuli", "version": "associative-stimuli/v1",
            "seed": seed, "family": "qualification", "width": 32, "height": 32,
            "side": "center", "color_assignment": "fixed",
        },
        "observation_recipe": {
            "sequence": list(SEQUENCE), "duration_ms": 500,
            "stimulation": None, "learning": False,
            "pathway_detail": False, "qualification_detail": False,
        },
        "black_input": {
            "generator": "black-rgb/v1", "input_dtype": "uint8",
            "input_shape": [32, 32, 3], "input_sha256": hashes["black"],
        },
        "rgb_input_sha256": hashes,
        "input_sha256": sorted(set(hashes.values())),
    }


def record_observation_run(
    output_dir: str | Path,
    *,
    engine_factory: Callable[[], FlyEngine],
    seed: int = 11,
    cycles: int = 3,
) -> VerifiedRun:
    """Create a fresh, sealed, reward-free pilot with actual native checkpoints."""
    _integer(seed, "seed", maximum=4294967295)
    _integer(cycles, "cycles", minimum=1, maximum=10)
    target = Path(output_dir)
    if target.exists() or target.is_symlink() or target.is_junction():
        raise FileExistsError(f"Output path already exists: {target}")
    engine = engine_factory()
    if (not isinstance(engine, FlyEngine) or engine.brain.cursor != 0
            or _ticks(float(engine.brain.sim_ms)) != 0 or engine.brain.dt != 0.1
            or engine.brain.weights_frozen):
        raise RunArtifactError("Observation requires a fresh actual 0.1 ms engine with normal passive evolution")
    identity = engine.identity()
    frames = _frames(seed)
    metadata = _metadata(identity, seed, cycles, frames)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".observation-checkpoint-") as scratch:
        checkpoint = Path(scratch) / "brain.npz"
        with RunRecorder(target, run_kind="pilot", metadata=metadata,
                         root_branch_id=ROOT_BRANCH) as recorder:
            def save(name: str) -> None:
                engine.brain.checkpoint(checkpoint)
                recorder.ingest_checkpoint(name, checkpoint, origin_branch_id=ROOT_BRANCH)
                recorder.append({
                    "type": "checkpoint", "branch_id": ROOT_BRANCH,
                    "sim_ms": engine.brain.cursor / 10, "sim_tick": engine.brain.cursor,
                    "checkpoint_name": name,
                })

            save("brain-before.npz")
            for _ in range(cycles):
                for stimulus in SEQUENCE:
                    start = engine.brain.cursor
                    telemetry = engine.observe(
                        frames[stimulus], 500.0, stimulation=None, learning=False,
                        pathway_detail=False, qualification_detail=False,
                    )
                    end = engine.brain.cursor
                    if end != start + 5000 or _ticks(telemetry["sim_ms"]) != end:
                        raise RunArtifactError("Actual observation clock mismatch")
                    recorder.append({
                        "type": "observe", "branch_id": ROOT_BRANCH,
                        "sim_ms": end / 10, "start_ms": start / 10, "end_ms": end / 10,
                        "start_tick": start, "end_tick": end,
                        "duration_ms": 500.0, "duration_ticks": 5000,
                        "stimulus": stimulus if stimulus != "black" else None,
                        "stimulation": None, "learning": False,
                        "pathway_detail": False, "qualification_detail": False,
                        "telemetry": telemetry,
                    })
            save("brain-after.npz")
    return verify_run(target)


def _populations(identity: dict) -> dict[str, int]:
    maps = identity["neural_groups"]
    if not isinstance(maps, dict) or set(maps) != set(GROUPS):
        raise RunArtifactError("Missing recorded population maps")
    result = {}
    for name in GROUPS:
        values = maps[name]
        if not isinstance(values, list) or not values:
            raise RunArtifactError(f"Missing positive population: {name}")
        for index in values:
            _integer(index, "neural index")
        if len(set(values)) != len(values):
            raise RunArtifactError("Repeated neural group index")
        result[name] = len(values)
    return result


def _segment(event: dict, *, index: int, frames: dict, groups: dict, identity: dict) -> dict:
    start = index * 5000
    end = start + 5000
    stimulus = SEQUENCE[index % 4]
    if (event["type"] != "observe" or event["stimulus"] != (None if stimulus == "black" else stimulus)
            or event["stimulation"] is not None or event["learning"] is not False
            or event["pathway_detail"] is not False or event["qualification_detail"] is not False):
        raise RunArtifactError("Unsupported observation flags or stimulus sequence")
    for name, expected in (("start_tick", start), ("end_tick", end), ("duration_ticks", 5000)):
        if _integer(event[name], name) != expected:
            raise RunArtifactError("Noncontinuous source observation ticks")
    for name, expected in (("start_ms", start), ("end_ms", end), ("sim_ms", end), ("duration_ms", 5000)):
        if _ticks(event[name]) != expected:
            raise RunArtifactError("Inconsistent source observation clock")
    telemetry = event["telemetry"]
    if (not isinstance(telemetry, dict) or telemetry["engine_identity"] != identity
            or telemetry["learning"] is not False or telemetry["stimulation"] is not None
            or telemetry["input_shape"] != [32, 32, 3] or telemetry["input_dtype"] != "uint8"
            or telemetry["input_sha256"] != _rgb_input_sha256(frames[stimulus])
            or {"pathway_detail", "qualification_detail"} & telemetry.keys()
            or _ticks(telemetry["sim_ms"]) != end or _ticks(telemetry["interval_ms"]) != 5000):
        raise RunArtifactError("Inconsistent recorded telemetry or RGB input hash")
    raw_bins = telemetry["bins"]
    if not isinstance(raw_bins, list) or not 1 <= len(raw_bins) <= 50:
        raise RunArtifactError("Missing or oversized measured bins")
    bins = []
    cursor = start
    totals = dict.fromkeys(GROUPS, 0)
    for raw in raw_bins:
        if not isinstance(raw, dict) or set(raw) != {"end_ms", "duration_ms", "group_spikes"}:
            raise RunArtifactError("Unsupported measured bin")
        duration = _ticks(raw["duration_ms"])
        bin_end = _ticks(raw["end_ms"])
        if not 0 < duration <= 100 or bin_end != cursor + duration or bin_end > end:
            raise RunArtifactError("Incomplete or noncontiguous measured bin coverage")
        counts = raw["group_spikes"]
        if not isinstance(counts, dict) or set(counts) != set(GROUPS):
            raise RunArtifactError("Missing measured population counts")
        for name in GROUPS:
            totals[name] += _integer(counts[name], f"{name} count", maximum=duration * groups[name])
        bins.append({"end_tick": bin_end, "duration_ticks": duration, "group_spikes": counts})
        cursor = bin_end
    if cursor != end:
        raise RunArtifactError("Incomplete measured interval")
    rates = telemetry["rates_hz"]
    if not isinstance(rates, dict) or set(rates) != set(GROUPS):
        raise RunArtifactError("Missing measured population rates")
    for name in GROUPS:
        value = rates[name]
        if (type(value) not in {float, int} or not math.isfinite(value) or value < 0
                or not math.isclose(value, totals[name] / (groups[name] * 0.5), rel_tol=1e-12, abs_tol=1e-12)):
            raise RunArtifactError("Recorded rates disagree with counts, population and duration")
    turn = telemetry["turn_hz"]
    if type(turn) not in {float, int} or not math.isfinite(turn) \
            or not math.isclose(turn, rates["motor_right"] - rates["motor_left"], rel_tol=1e-12, abs_tol=1e-12):
        raise RunArtifactError("Inconsistent recorded lateral rate")
    _integer(telemetry["total_spikes"], "total spikes")
    return {
        "event_sequence": _integer(event["sequence"], "sequence"),
        "branch_id": event["branch_id"], "stimulus": stimulus,
        "stimulation": None, "learning": False,
        "source_start_tick": start, "source_end_tick": end,
        "playback_start_tick": start, "playback_end_tick": end, "bins": bins,
    }


def _export_data(run: VerifiedRun) -> dict:
    manifest = run.manifest
    metadata = manifest["metadata"]
    if manifest["run_kind"] != "pilot" or manifest["root_branch_id"] != ROOT_BRANCH:
        raise RunArtifactError("Only sealed measured-observation root pilots are supported")
    seed = _integer(metadata["stimulus_recipe"]["seed"], "seed", maximum=4294967295)
    cycles = _integer(metadata["factors"]["cycles"], "cycles", minimum=1, maximum=10)
    frames = _frames(seed)
    expected = _metadata(metadata["engine_identity"], seed, cycles, frames)
    if any(_canonical(metadata.get(name)) != _canonical(value) for name, value in expected.items()):
        raise RunArtifactError("Unsupported or incomplete observation metadata recipe")
    groups = _populations(metadata["engine_identity"])
    if set(manifest["checkpoints"]) != {"brain-before.npz", "brain-after.npz"} or manifest["state_anchors"]:
        raise RunArtifactError("Unsupported checkpoint inventory")
    segments = []
    event_count = 0
    for event in run.iter_events():
        event_count += 1
        if event["branch_id"] != ROOT_BRANCH or any(name.startswith("parent_") for name in event):
            raise RunArtifactError("Restored or forked branches are unsupported")
        sequence = _integer(event["sequence"], "sequence")
        if sequence == 0 or sequence == cycles * 4 + 1:
            before = sequence == 0
            tick = 0 if before else cycles * 20000
            if (event["type"] != "checkpoint"
                    or event["checkpoint_name"] != ("brain-before.npz" if before else "brain-after.npz")
                    or _integer(event["sim_tick"], "checkpoint tick") != tick or _ticks(event["sim_ms"]) != tick):
                raise RunArtifactError("Unsupported checkpoint occurrence")
        else:
            if len(segments) >= 40 or sequence != len(segments) + 1:
                raise RunArtifactError("Invalid observation order or segment bound")
            segments.append(_segment(event, index=len(segments), frames=frames,
                                     groups=groups, identity=metadata["engine_identity"]))
    # The iterator's final manifest/file checks must finish before publication.
    if event_count != cycles * 4 + 2 or len(segments) != cycles * 4 \
            or sum(len(segment["bins"]) for segment in segments) > 2000:
        raise RunArtifactError("Incomplete or oversized measured observation run")
    return {
        "version": "measured-replay/v1", "tick_ms": 0.1,
        "source": {
            **{name: manifest[name] for name in ("run_kind", "schema_sha256", "run_metadata_sha256",
                                                "events_sha256", "final_scientific_sha256", "metadata")},
            "verification_mode": run.verification_mode,
        },
        "groups": groups,
        "inputs": {name: {"sha256": _rgb_input_sha256(frame), "width": 32, "height": 32,
                          "rgb_base64": base64.b64encode(frame.tobytes(order="C")).decode("ascii")}
                   for name, frame in frames.items()},
        "segments": segments, "duration_ticks": cycles * 20000,
    }


def export_measured_replay(run_dir: str | Path, output_path: str | Path) -> dict:
    """Verify to normal EOF, then atomically publish a new compact replay file."""
    source = Path(run_dir).resolve()
    output = Path(output_path)
    if output.resolve().is_relative_to(source):
        raise RunArtifactError("Replay output must be outside the source artifact")
    if output.exists() or output.is_symlink() or output.is_junction():
        raise FileExistsError(f"Output path already exists: {output}")
    if any(parent.is_symlink() or parent.is_junction() for parent in output.absolute().parents):
        raise RunArtifactError("Output ancestor symlink or junction rejected")
    run = verify_run(run_dir)
    try:
        data = _export_data(run)
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise RunArtifactError(f"Incomplete measured observation source: {error}") from error
    raw = _canonical(data) + b"\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".measured-replay-", suffix=".tmp", delete=False) as writer:
            temporary = Path(writer.name)
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        # Windows rename is atomic and refuses existing destinations. POSIX
        # rename replaces them, so use an exclusive same-directory hard link.
        if os.name == "nt":
            os.rename(temporary, output)
        else:
            os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return data
