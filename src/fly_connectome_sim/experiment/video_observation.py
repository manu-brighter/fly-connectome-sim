"""Prepare real video RGB observations and export their sealed measured feed."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import math
import os
from pathlib import Path
import tempfile
from typing import Callable

import numpy as np
from PIL import Image

from ..engine import FlyEngine, _rgb_input_sha256
from .measured_replay import GROUPS, _integer, _populations, _ticks
from .recorder import DIGEST, RunArtifactError, RunRecorder, VerifiedRun, _canonical, _strict_load, verify_run
from .video_policy import ADAPTER, POLICY_VERSION, _profile_version, evaluate_video_policy


ROOT_BRANCH = "video-observation/root"
WIDTH = 90
HEIGHT = 160
FRAMES_PER_CLIP = 120
WINDOW_TICKS = 40000
SESSION_LIMIT_TICKS = 80000
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_SOURCE_BYTES = 512 * 1024 * 1024
MAX_DECODED_FRAMES = 4096

VIDEO_RECIPE = {
    "policy_version": POLICY_VERSION,
    "adapter_version": ADAPTER.version,
    "action_threshold_hz": ADAPTER.action_threshold_hz,
    "sample_fps": [30, 1],
    "sample_time_origin": "first-decoded-pts",
    "tick_quantization": "nearest-0.1ms-half-up-cumulative/v1",
    "window_ticks": WINDOW_TICKS,
    "session_limit_ticks": SESSION_LIMIT_TICKS,
    "rolling_window_ticks": 3000,
    "minimum_dwell_ticks": 10000,
    "input_width": WIDTH,
    "input_height": HEIGHT,
    "audio_input": False,
    "stimulation": None,
    "learning": False,
    "pathway_detail": False,
    "qualification_detail": False,
}


def _video_recipe(profile: str) -> dict:
    _profile_version(profile)
    if profile == "standard":
        return VIDEO_RECIPE
    return {
        **VIDEO_RECIPE, "policy_version": "right-scroll/v2",
        "minimum_dwell_ticks": 30000,
        "source_speed": [5, 1], "source_window_seconds": 20,
    }


def _stored_profile(metadata: dict) -> str:
    if type(metadata) is dict:
        if metadata.get("protocol_version") == "video-observation/v1":
            return "standard"
        if metadata.get("protocol_version") == "video-observation/v2":
            return "fast-feed"
    raise RunArtifactError("Unsupported video observation metadata")


def _telemetry_ticks(value: object) -> int:
    """Allow only native float noise around the authoritative 0.1 ms lattice."""
    if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
        raise RunArtifactError("Invalid measured simulation clock")
    ticks = round(value * 10)
    if abs(value * 10 - ticks) > 1e-7:
        raise RunArtifactError("Measured simulation clock is outside 0.1 ms lattice")
    return ticks


@dataclass(frozen=True)
class PreparedFrame:
    frame_id: str
    frame_index: int
    rgb: np.ndarray
    sha256: str
    source_pts: int
    source_time_base: list[int]


@dataclass(frozen=True)
class PreparedClip:
    metadata: dict
    frames: tuple[PreparedFrame, ...]


def frame_tick(index: int) -> int:
    """Nearest 0.1 ms cumulative boundary for an integer 30 fps frame index."""
    if type(index) is not int or not 0 <= index <= FRAMES_PER_CLIP:
        raise RunArtifactError("Invalid video frame boundary")
    return (index * 10000 + 15) // 30


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _dimensions(source_width: int, source_height: int) -> dict:
    if (type(source_width) is not int or type(source_height) is not int
            or not 1 <= source_width <= 8192 or not 1 <= source_height <= 8192):
        raise RunArtifactError("Invalid source video dimensions")
    scale = min(Fraction(WIDTH, source_width), Fraction(HEIGHT, source_height))
    inner_width = math.floor(source_width * scale + Fraction(1, 2))
    inner_height = math.floor(source_height * scale + Fraction(1, 2))
    left = (WIDTH - inner_width) // 2
    top = (HEIGHT - inner_height) // 2
    return {
        "width": WIDTH, "height": HEIGHT,
        "inner_width": inner_width, "inner_height": inner_height,
        "padding": [left, top, WIDTH - inner_width - left, HEIGHT - inner_height - top],
        "resize": "bilinear", "placement": "centered-black-letterbox",
        "pixel_format": "rgb24", "color_conversion": "PyAV-to_ndarray-rgb24-FFmpeg-defaults",
        "crop": "none", "orientation": "reject-rotation-and-displaymatrix/v1",
    }


def _rgb(frame, transform: dict) -> np.ndarray:
    original = frame.to_ndarray(format="rgb24")
    resized = Image.fromarray(original, mode="RGB").resize(
        (transform["inner_width"], transform["inner_height"]),
        resample=Image.Resampling.BILINEAR,
    )
    result = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    left, top = transform["padding"][:2]
    result[top:top + transform["inner_height"],
           left:left + transform["inner_width"]] = np.asarray(resized)
    result.flags.writeable = False
    return result


def _prepare_clip(
    path: Path, source_url: str, clip_index: int, *, profile: str = "standard",
) -> PreparedClip:
    _profile_version(profile)
    source_speed = 1 if profile == "standard" else 5
    source_window_seconds = 4 * source_speed
    try:
        import av
    except ImportError as error:
        raise RunArtifactError("Video preparation requires the optional media extra (PyAV 19.0.2)") from error
    if av.__version__ != "19.0.2":
        raise RunArtifactError("Unsupported PyAV version")
    if not path.is_file() or path.is_symlink():
        raise RunArtifactError(f"Missing local video source: {path}")
    size = path.stat().st_size
    if not 0 < size <= MAX_SOURCE_BYTES:
        raise RunArtifactError("Invalid or oversized video source")
    digest_before = _sha256_file(path)
    with av.open(str(path), mode="r") as container:
        if len(container.streams.video) != 1:
            raise RunArtifactError("Exactly one video stream is required")
        stream = container.streams.video[0]
        source_width, source_height = stream.width, stream.height
        transform = _dimensions(source_width, source_height)
        sar = stream.sample_aspect_ratio
        if sar is not None and (sar.numerator, sar.denominator) not in {(0, 1), (1, 1)}:
            raise RunArtifactError("Non-square source pixels are unsupported")
        source_sar = [sar.numerator, sar.denominator] if sar else [0, 1]
        rotation = stream.metadata.get("rotate", "0")
        if rotation not in {"0", "0.0"}:
            raise RunArtifactError("Source orientation transform is unsupported")
        selected = []
        current = None
        decoded_count = 0
        origin_pts = None
        time_base = None
        previous_pts = None
        coverage_end_pts = None
        coverage_method = None
        last_duration = None
        for source_frame in container.decode(stream):
            decoded_count += 1
            if decoded_count > MAX_DECODED_FRAMES:
                raise RunArtifactError("Source decoded frame limit exceeded")
            if source_frame.is_corrupt or type(source_frame.pts) is not int:
                raise RunArtifactError("Corrupt video frame or missing source PTS")
            if (source_frame.width != source_width or source_frame.height != source_height
                    or stream.width != source_width or stream.height != source_height):
                raise RunArtifactError("Variable source dimensions are unsupported")
            current_sar = stream.sample_aspect_ratio
            if ([current_sar.numerator, current_sar.denominator] if current_sar else [0, 1]) != source_sar:
                raise RunArtifactError("Variable source pixel aspect ratio is unsupported")
            if any(side_type.name == "DISPLAYMATRIX" for side_type in source_frame.side_data.keys()):
                raise RunArtifactError("Source display matrix is unsupported")
            frame_base = source_frame.time_base
            if (frame_base is None or frame_base.numerator <= 0
                    or frame_base.denominator <= 0):
                raise RunArtifactError("Invalid source timebase")
            if time_base is None:
                time_base = Fraction(frame_base)
                origin_pts = source_frame.pts
            elif Fraction(frame_base) != time_base:
                raise RunArtifactError("Variable source timebase is unsupported")
            if previous_pts is not None and source_frame.pts <= previous_pts:
                raise RunArtifactError("Nonmonotonic decoded source PTS")
            previous_pts = source_frame.pts
            elapsed = (source_frame.pts - origin_pts) * time_base
            if elapsed < 0:
                raise RunArtifactError("Negative source presentation time")
            coverage_end_pts = source_frame.pts
            last_duration = source_frame.duration
            if elapsed < source_window_seconds:
                if current is not None:
                    while (len(selected) < FRAMES_PER_CLIP
                           and Fraction(source_speed * len(selected), 30) < elapsed):
                        selected.append(current)
                current = (source_frame.pts, _rgb(source_frame, transform))
            else:
                coverage_method = "following_pts"
                break
        if (coverage_method is None and type(last_duration) is int and last_duration > 0
                and (coverage_end_pts + last_duration - origin_pts) * time_base >= source_window_seconds):
            coverage_end_pts += last_duration
            coverage_method = "final_frame_duration"
        if (origin_pts is None or current is None or coverage_end_pts is None
                or (coverage_end_pts - origin_pts) * time_base < source_window_seconds):
            raise RunArtifactError(
                "Source video lacks complete four-second coverage" if profile == "standard"
                else "Source video lacks complete twenty-second coverage"
            )
        while len(selected) < FRAMES_PER_CLIP:
            selected.append(current)
    if path.stat().st_size != size or _sha256_file(path) != digest_before:
        raise RunArtifactError("Video source changed while decoding")
    clip_id = f"clip-{clip_index}"
    frames = []
    for index, (source_pts, rgb) in enumerate(selected):
        frames.append(PreparedFrame(
            frame_id=f"{clip_id}/frame-{index}", frame_index=index,
            rgb=rgb, sha256=_rgb_input_sha256(rgb), source_pts=source_pts,
            source_time_base=[time_base.numerator, time_base.denominator],
        ))
    metadata = {
        "clip_id": clip_id, "source_url": source_url, "source_path": str(path),
        "source_sha256": digest_before, "source_size": size,
        "source_width": source_width, "source_height": source_height,
        "source_sample_aspect_ratio": source_sar,
        "source_time_base": [time_base.numerator, time_base.denominator],
        "origin_pts": origin_pts, "coverage_end_pts": coverage_end_pts,
        "coverage_method": coverage_method,
        "decoder": {
            "pyav_version": av.__version__,
            "ffmpeg_libraries": {name: list(version) for name, version in av.library_versions.items()},
        },
        "transform": transform,
        "frames": [{
            "frame_id": frame.frame_id, "frame_index": frame.frame_index,
            "sha256": frame.sha256, "source_pts": frame.source_pts,
            "source_time_base": frame.source_time_base,
        } for frame in frames],
    }
    return PreparedClip(metadata=metadata, frames=tuple(frames))


def prepare_playlist(
    playlist_path: str | Path, *, profile: str = "standard",
) -> tuple[PreparedClip, ...]:
    """Read and hash all closed-profile source windows before engine construction."""
    _profile_version(profile)
    declaration = Path(playlist_path)
    if not declaration.is_file() or declaration.stat().st_size > 16 * 1024:
        raise RunArtifactError("Missing or oversized local playlist declaration")
    entries = _strict_load(declaration.read_bytes())
    if (type(entries) is not list or not 1 <= len(entries) <= 5
            or any(type(item) is not dict or set(item) != {"path", "source_url"}
                   or type(item["path"]) is not str or not item["path"]
                   or type(item["source_url"]) is not str
                   or not item["source_url"].startswith("https://")
                   for item in entries)):
        raise RunArtifactError("Playlist requires 1–5 ordered local path/source_url entries")
    paths = []
    for entry in entries:
        path = Path(entry["path"])
        if not path.is_absolute():
            path = declaration.parent / path
        paths.append(path.resolve())
    if len(set(paths)) != len(paths):
        raise RunArtifactError("Repeated local video source")
    return tuple(_prepare_clip(path, entry["source_url"], index, profile=profile)
                 for index, (path, entry) in enumerate(zip(paths, entries, strict=True)))


def _metadata(
    identity: dict, clips: tuple[PreparedClip, ...], *, profile: str = "standard",
) -> dict:
    version = _profile_version(profile)
    return {
        "engine_identity": identity,
        "protocol_version": f"video-observation/{version}",
        "stimulus_version": f"decoded-video-rgb/{version}",
        "family": "video-observation", "seeds": [],
        "factors": {"clip_count": len(clips)},
        "video_recipe": _video_recipe(profile),
        "clips": [clip.metadata for clip in clips],
        "input_sha256": sorted({frame.sha256 for clip in clips for frame in clip.frames}),
    }


def _frame_payload(frame: PreparedFrame, clip_id: str) -> dict:
    return {
        "frame_id": frame.frame_id, "clip_id": clip_id,
        "frame_index": frame.frame_index,
        "width": WIDTH, "height": HEIGHT,
        "rgb_base64": base64.b64encode(frame.rgb.tobytes(order="C")).decode("ascii"),
        "sha256": frame.sha256, "source_pts": frame.source_pts,
        "source_time_base": frame.source_time_base,
    }


def _observe_video_phase(
    engine: FlyEngine, clips: tuple[PreparedClip, ...], *, branch_id: str,
    start_tick: int, profile: str,
):
    """Yield actual observations; the caller owns recording and engine lifecycle."""
    if engine.brain.cursor != start_tick or start_tick != 0:
        raise RunArtifactError("Feed phase requires the unchanged zero-origin engine")
    populations = {name: len(engine.identity()["neural_groups"][name])
                   for name in ("motor_left", "motor_right")}
    clip_index = 0
    frame_index = 0
    clip_start_tick = 0
    motor_counts: list[dict[str, int]] = []
    while True:
        clip = clips[clip_index]
        frame = clip.frames[frame_index]
        duration_ticks = frame_tick(frame_index + 1) - frame_tick(frame_index)
        start = engine.brain.cursor
        telemetry = engine.observe(
            frame.rgb, duration_ticks / 10,
            stimulation=None, learning=False,
            pathway_detail=False, qualification_detail=False,
        )
        end = engine.brain.cursor
        if end != start + duration_ticks or _telemetry_ticks(telemetry["sim_ms"]) != end:
            raise RunArtifactError("Actual video observation clock mismatch")
        motor_counts.append({
            name: sum(bin_["group_spikes"][name] for bin_ in telemetry["bins"])
            for name in populations
        })
        event = {
            "type": "observe", "branch_id": branch_id,
            "sim_ms": end / 10, "start_ms": start / 10, "end_ms": end / 10,
            "start_tick": start, "end_tick": end,
            "duration_ms": duration_ticks / 10, "duration_ticks": duration_ticks,
            "stimulus": "video", "stimulation": None, "learning": False,
            "pathway_detail": False, "qualification_detail": False,
            "telemetry": telemetry,
            "video_frame": _frame_payload(frame, clip.metadata["clip_id"]),
        }
        decision = None
        if frame_index % 3 == 2:
            decision = evaluate_video_policy(
                counts=motor_counts, populations=populations,
                clip_index=clip_index, clip_count=len(clips),
                clip_start_tick=clip_start_tick, frame_index=frame_index,
                end_tick=end, profile=profile,
            )
            event["video_policy"] = decision
        yield event
        if decision is not None and decision["action"] == "stop":
            break
        if decision is not None and decision["action"] == "advance":
            clip_index = decision["next_clip_index"]
            clip_start_tick = end
            frame_index = 0
            motor_counts = []
        else:
            frame_index += 1


def record_video_observation_run(
    output_dir: str | Path, *, playlist_path: str | Path,
    engine_factory: Callable[[], FlyEngine], profile: str = "standard",
) -> VerifiedRun:
    """Seal one continuous actual native pilot driven by decoded video frames."""
    target = Path(output_dir)
    if target.exists() or target.is_symlink() or target.is_junction():
        raise FileExistsError(f"Output path already exists: {target}")
    clips = prepare_playlist(playlist_path, profile=profile)
    engine = engine_factory()
    if (not isinstance(engine, FlyEngine) or engine.brain.cursor != 0
            or _ticks(float(engine.brain.sim_ms)) != 0 or engine.brain.dt != 0.1
            or engine.brain.weights_frozen):
        raise RunArtifactError("Video observation requires a fresh actual 0.1 ms engine")
    metadata = _metadata(engine.identity(), clips, profile=profile)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".video-checkpoint-") as scratch:
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
            for event in _observe_video_phase(
                engine, clips, branch_id=ROOT_BRANCH, start_tick=0, profile=profile,
            ):
                recorder.append(event)
            save("brain-after.npz")
    run = verify_run(target)
    _export_data(run)
    return run


def _validated_metadata(metadata: dict) -> list[dict]:
    profile = _stored_profile(metadata)
    version = _profile_version(profile)
    if (type(metadata) is not dict or set(metadata) != {
            "engine_identity", "protocol_version", "stimulus_version", "family",
            "seeds", "factors", "video_recipe", "clips", "input_sha256"}
            or metadata["protocol_version"] != f"video-observation/{version}"
            or metadata["stimulus_version"] != f"decoded-video-rgb/{version}"
            or metadata["family"] != "video-observation"
            or metadata["seeds"] != []
            or _canonical(metadata["video_recipe"]) != _canonical(_video_recipe(profile))):
        raise RunArtifactError("Unsupported video observation metadata")
    clips = metadata["clips"]
    if (type(clips) is not list or not 1 <= len(clips) <= 5
            or _canonical(metadata["factors"]) != _canonical({"clip_count": len(clips)})):
        raise RunArtifactError("Invalid prepared clip inventory")
    declared_hashes = _validated_clips(clips, profile=profile)
    if metadata["input_sha256"] != sorted(declared_hashes):
        raise RunArtifactError("Prepared RGB hash set differs from metadata")
    return clips


def _validated_clips(clips: list[dict], *, profile: str) -> set[str]:
    """Validate the actual prepared inventory independently of a run envelope."""
    _profile_version(profile)
    if type(clips) is not list or not 1 <= len(clips) <= 5:
        raise RunArtifactError("Invalid prepared clip inventory")
    source_speed = 1 if profile == "standard" else 5
    source_window_seconds = 4 * source_speed
    declared_hashes = set()
    for clip_index, clip in enumerate(clips):
        if type(clip) is not dict or set(clip) != {
                "clip_id", "source_url", "source_path", "source_sha256", "source_size",
                "source_width", "source_height", "source_sample_aspect_ratio",
                "source_time_base", "origin_pts",
                "coverage_end_pts", "coverage_method", "decoder", "transform", "frames"}:
            raise RunArtifactError("Invalid prepared clip declaration")
        if (clip["clip_id"] != f"clip-{clip_index}"
                or type(clip["source_url"]) is not str
                or not clip["source_url"].startswith("https://")
                or type(clip["source_path"]) is not str or not clip["source_path"]
                or type(clip["source_sha256"]) is not str
                or DIGEST.fullmatch(clip["source_sha256"]) is None):
            raise RunArtifactError("Invalid source identity")
        _integer(clip["source_size"], "source size", minimum=1, maximum=MAX_SOURCE_BYTES)
        transform = _dimensions(clip["source_width"], clip["source_height"])
        if _canonical(clip["transform"]) != _canonical(transform):
            raise RunArtifactError("Unsupported source resize or placement")
        if _canonical(clip["source_sample_aspect_ratio"]) not in {
                _canonical([0, 1]), _canonical([1, 1])}:
            raise RunArtifactError("Unsupported source pixel aspect ratio")
        base = clip["source_time_base"]
        if (type(base) is not list or len(base) != 2
                or any(type(value) is not int or value <= 0 for value in base)):
            raise RunArtifactError("Invalid source timebase")
        time_base = Fraction(*base)
        if (type(clip["origin_pts"]) is not int or type(clip["coverage_end_pts"]) is not int
                or (clip["coverage_end_pts"] - clip["origin_pts"]) * time_base < source_window_seconds):
            raise RunArtifactError("Incomplete declared source coverage")
        if clip["coverage_method"] not in {"following_pts", "final_frame_duration"}:
            raise RunArtifactError("Unknown source coverage method")
        decoder = clip["decoder"]
        if (type(decoder) is not dict or set(decoder) != {"pyav_version", "ffmpeg_libraries"}
                or decoder["pyav_version"] != "19.0.2"
                or type(decoder["ffmpeg_libraries"]) is not dict
                or not decoder["ffmpeg_libraries"]
                or any(type(name) is not str or not name.startswith(("libav", "libsw"))
                       or type(version) is not list or len(version) != 3
                       or any(type(value) is not int or value < 0 for value in version)
                       for name, version in decoder["ffmpeg_libraries"].items())):
            raise RunArtifactError("Invalid decoder version declaration")
        frames = clip["frames"]
        if type(frames) is not list or len(frames) != FRAMES_PER_CLIP:
            raise RunArtifactError("Incomplete prepared frame map")
        previous_pts = None
        for frame_index, frame in enumerate(frames):
            if (type(frame) is not dict or set(frame) != {
                    "frame_id", "frame_index", "sha256", "source_pts", "source_time_base"}
                    or frame["frame_id"] != f"clip-{clip_index}/frame-{frame_index}"
                    or type(frame["frame_index"]) is not int
                    or frame["frame_index"] != frame_index
                    or type(frame["sha256"]) is not str
                    or DIGEST.fullmatch(frame["sha256"]) is None
                    or type(frame["source_pts"]) is not int
                    or _canonical(frame["source_time_base"]) != _canonical(base)
                    or (frame["source_pts"] - clip["origin_pts"]) * time_base
                    > Fraction(source_speed * frame_index, 30)
                    or (previous_pts is not None and frame["source_pts"] < previous_pts)):
                raise RunArtifactError("Invalid prepared frame declaration or source PTS")
            if frame_index == 0 and frame["source_pts"] != clip["origin_pts"]:
                raise RunArtifactError("First prepared frame must bind the PTS origin")
            previous_pts = frame["source_pts"]
            declared_hashes.add(frame["sha256"])
    return declared_hashes


def _segment(
    event: dict, frame_map: dict, *, clip_index: int, frame_index: int,
    start_tick: int, groups: dict, identity: dict, branch_id: str = ROOT_BRANCH,
) -> tuple[dict, dict[str, int]]:
    expected_keys = {
        "type", "branch_id", "sim_ms", "start_ms", "end_ms", "start_tick",
        "end_tick", "duration_ms", "duration_ticks", "stimulus", "stimulation",
        "learning", "pathway_detail", "qualification_detail", "telemetry",
        "video_frame", "sequence", "previous_scientific_sha256",
        "scientific_sha256", "run_metadata_sha256",
    }
    if frame_index % 3 == 2:
        expected_keys.add("video_policy")
    if (type(event) is not dict or set(event) != expected_keys
            or event["type"] != "observe" or event["branch_id"] != branch_id
            or event["stimulus"] != "video" or event["stimulation"] is not None
            or event["learning"] is not False or event["pathway_detail"] is not False
            or event["qualification_detail"] is not False):
        raise RunArtifactError("Unsupported video observation event or flags")
    duration = frame_tick(frame_index + 1) - frame_tick(frame_index)
    end_tick = start_tick + duration
    for name, expected in (("start_tick", start_tick), ("end_tick", end_tick),
                           ("duration_ticks", duration)):
        if _integer(event[name], name) != expected:
            raise RunArtifactError("Discontinuous video frame clock")
    for name, expected in (("start_ms", start_tick), ("end_ms", end_tick),
                           ("sim_ms", end_tick), ("duration_ms", duration)):
        if _ticks(event[name]) != expected:
            raise RunArtifactError("Inconsistent video frame clock")
    payload = event["video_frame"]
    expected_payload = {
        **frame_map, "clip_id": f"clip-{clip_index}",
        "width": WIDTH, "height": HEIGHT,
    }
    if (type(payload) is not dict or set(payload) != set(expected_payload) | {"rgb_base64"}
            or any(_canonical(payload[name]) != _canonical(value)
                   for name, value in expected_payload.items())
            or type(payload["rgb_base64"]) is not str
            or len(payload["rgb_base64"]) > 57600):
        raise RunArtifactError("Video input differs from prepared frame map")
    try:
        rgb = base64.b64decode(payload["rgb_base64"], validate=True)
    except (ValueError, base64.binascii.Error) as error:
        raise RunArtifactError("Invalid RGB base64") from error
    if (len(rgb) != WIDTH * HEIGHT * 3
            or base64.b64encode(rgb).decode("ascii") != payload["rgb_base64"]
            or _rgb_input_sha256(np.frombuffer(rgb, dtype=np.uint8).reshape(HEIGHT, WIDTH, 3))
            != frame_map["sha256"]):
        raise RunArtifactError("Video pixels differ from declared RGB hash")
    telemetry = event["telemetry"]
    if (type(telemetry) is not dict or telemetry.get("engine_identity") != identity
            or telemetry.get("learning") is not False
            or telemetry.get("stimulation") is not None
            or telemetry.get("input_shape") != [HEIGHT, WIDTH, 3]
            or telemetry.get("input_dtype") != "uint8"
            or telemetry.get("input_sha256") != frame_map["sha256"]
            or {"pathway_detail", "qualification_detail"} & telemetry.keys()
            or _telemetry_ticks(telemetry["sim_ms"]) != end_tick
            or _telemetry_ticks(telemetry["interval_ms"]) != duration):
        raise RunArtifactError("Measured telemetry disagrees with exact video frame")
    raw_bins = telemetry["bins"]
    if type(raw_bins) is not list or not 1 <= len(raw_bins) <= 4:
        raise RunArtifactError("Missing or excessive measured video bins")
    cursor = start_tick
    totals = dict.fromkeys(GROUPS, 0)
    bins = []
    for raw in raw_bins:
        if type(raw) is not dict or set(raw) != {"end_ms", "duration_ms", "group_spikes"}:
            raise RunArtifactError("Unsupported measured bin")
        bin_duration = _telemetry_ticks(raw["duration_ms"])
        bin_end = _telemetry_ticks(raw["end_ms"])
        if not 0 < bin_duration <= 100 or bin_end != cursor + bin_duration or bin_end > end_tick:
            raise RunArtifactError("Incomplete or noncontiguous measured bins")
        counts = raw["group_spikes"]
        if type(counts) is not dict or set(counts) != set(GROUPS):
            raise RunArtifactError("Missing measured population counts")
        for name in GROUPS:
            totals[name] += _integer(counts[name], f"{name} count",
                                     maximum=bin_duration * groups[name])
        bins.append({"end_tick": bin_end, "duration_ticks": bin_duration,
                     "group_spikes": counts})
        cursor = bin_end
    if cursor != end_tick:
        raise RunArtifactError("Incomplete measured video interval")
    rates = telemetry["rates_hz"]
    if type(rates) is not dict or set(rates) != set(GROUPS):
        raise RunArtifactError("Missing measured population rates")
    for name in GROUPS:
        value = rates[name]
        if (type(value) not in {float, int} or not math.isfinite(value) or value < 0
                or not math.isclose(value, totals[name] / (groups[name] * duration / 10000),
                                    rel_tol=1e-12, abs_tol=1e-12)):
            raise RunArtifactError("Measured population rate differs from raw bins")
    turn = telemetry["turn_hz"]
    if (type(turn) not in {float, int} or not math.isfinite(turn)
            or not math.isclose(turn, rates["motor_right"] - rates["motor_left"],
                                rel_tol=1e-12, abs_tol=1e-12)):
        raise RunArtifactError("Measured lateral rate differs from raw bins")
    _integer(telemetry["total_spikes"], "total spikes")
    return ({
        "event_sequence": _integer(event["sequence"], "event sequence"),
        "branch_id": branch_id,
        "frame_id": frame_map["frame_id"], "clip_id": f"clip-{clip_index}",
        "frame_index": frame_index,
        "stimulation": None, "learning": False,
        "source_start_tick": start_tick, "source_end_tick": end_tick,
        "playback_start_tick": start_tick, "playback_end_tick": end_tick,
        "bins": bins, "video_policy": event.get("video_policy"),
    }, {name: totals[name] for name in ("motor_left", "motor_right")})


def _export_data(run: VerifiedRun) -> dict:
    manifest = run.manifest
    if (manifest["run_kind"] != "pilot" or manifest["root_branch_id"] != ROOT_BRANCH
            or set(manifest["checkpoints"]) != {"brain-before.npz", "brain-after.npz"}
            or manifest["state_anchors"]):
        raise RunArtifactError("Only sealed root video observation pilots are supported")
    metadata = manifest["metadata"]
    clips = _validated_metadata(metadata)
    profile = _stored_profile(metadata)
    version = _profile_version(profile)
    identity = metadata["engine_identity"]
    groups = _populations(identity)
    populations = {name: groups[name] for name in ("motor_left", "motor_right")}
    clip_index = 0
    frame_index = 0
    clip_start_tick = 0
    end_tick = 0
    motor_counts: list[dict[str, int]] = []
    segments = []
    inputs = {}
    terminal = False
    seen_before = False
    seen_after = False
    event_count = 0
    bin_count = 0
    checkpoint_keys = {
        "type", "branch_id", "checkpoint_name", "checkpoint_sha256",
        "checkpoint_size", "sim_ms", "sim_tick", "sequence",
        "previous_scientific_sha256", "scientific_sha256", "run_metadata_sha256",
    }
    for event in run.iter_events():
        event_count += 1
        if event_count > 242 or event.get("branch_id") != ROOT_BRANCH \
                or any(name.startswith("parent_") for name in event):
            raise RunArtifactError("Unsupported video branch or event bound")
        if not seen_before:
            if (set(event) != checkpoint_keys or event["type"] != "checkpoint"
                    or event["checkpoint_name"] != "brain-before.npz"
                    or _integer(event["sim_tick"], "before checkpoint tick") != 0
                    or _ticks(event["sim_ms"]) != 0):
                raise RunArtifactError("Missing native before checkpoint")
            seen_before = True
            continue
        if terminal:
            if (seen_after or set(event) != checkpoint_keys or event["type"] != "checkpoint"
                    or event["checkpoint_name"] != "brain-after.npz"
                    or _integer(event["sim_tick"], "after checkpoint tick") != end_tick
                    or _ticks(event["sim_ms"]) != end_tick):
                raise RunArtifactError("Invalid terminal video checkpoint or extra event")
            seen_after = True
            continue
        if len(segments) >= 240 or event["type"] != "observe":
            raise RunArtifactError("Premature video checkpoint or excessive observations")
        frame_map = clips[clip_index]["frames"][frame_index]
        segment, counts = _segment(
            event, frame_map, clip_index=clip_index, frame_index=frame_index,
            start_tick=end_tick, groups=groups, identity=identity,
        )
        if segment["event_sequence"] != len(segments) + 1:
            raise RunArtifactError("Video event sequence gap")
        segments.append(segment)
        end_tick = segment["source_end_tick"]
        motor_counts.append(counts)
        bin_count += len(segment["bins"])
        if bin_count > 960:
            raise RunArtifactError("Excessive measured video bins")
        payload = event["video_frame"]
        inputs[payload["frame_id"]] = {
            name: payload[name] for name in (
                "sha256", "width", "height", "rgb_base64", "clip_id",
                "frame_index", "source_pts", "source_time_base",
            )
        }
        if frame_index % 3 == 2:
            expected = evaluate_video_policy(
                counts=motor_counts, populations=populations,
                clip_index=clip_index, clip_count=len(clips),
                clip_start_tick=clip_start_tick, frame_index=frame_index,
                end_tick=end_tick, profile=profile,
            )
            if _canonical(event["video_policy"]) != _canonical(expected):
                raise RunArtifactError("Recorded feed decision differs from measured rolling policy")
            if expected["action"] == "stop":
                terminal = True
            elif expected["action"] == "advance":
                clip_index = expected["next_clip_index"]
                frame_index = 0
                clip_start_tick = end_tick
                motor_counts = []
            else:
                frame_index += 1
        else:
            frame_index += 1
    # The ordinary verified iterator must finish to normal EOF before publication.
    if not terminal or not seen_after or event_count != len(segments) + 2:
        raise RunArtifactError("Sealed video run ended before a legitimate terminal decision")
    return {
        "version": f"measured-video-replay/{version}", "tick_ms": 0.1,
        "source": {
            **{name: manifest[name] for name in (
                "run_kind", "schema_sha256", "run_metadata_sha256", "events_sha256",
                "final_scientific_sha256", "metadata",
            )},
            "verification_mode": run.verification_mode,
        },
        "groups": groups, "inputs": inputs, "segments": segments,
        "duration_ticks": end_tick,
    }


def export_video_replay(run_dir: str | Path, output_path: str | Path) -> dict:
    """Verify to normal EOF, then atomically publish a new bounded compact file."""
    source = Path(run_dir).resolve()
    output = Path(output_path)
    if output.resolve().is_relative_to(source):
        raise RunArtifactError("Video replay output must be outside the source artifact")
    if output.exists() or output.is_symlink() or output.is_junction():
        raise FileExistsError(f"Output path already exists: {output}")
    if any(parent.is_symlink() or parent.is_junction() for parent in output.absolute().parents):
        raise RunArtifactError("Output ancestor symlink or junction rejected")
    run = verify_run(run_dir)
    try:
        data = _export_data(run)
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise RunArtifactError(f"Incomplete video observation source: {error}") from error
    raw = _canonical(data) + b"\n"
    if len(raw) > MAX_OUTPUT_BYTES:
        raise RunArtifactError("Compact video replay exceeds 32 MiB")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent, prefix=".measured-video-replay-", suffix=".tmp", delete=False,
        ) as writer:
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
