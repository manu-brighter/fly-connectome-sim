"""Genuine decoded RGB feed input and sealed native replay validation."""

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
import weakref

import numpy as np
import pytest

from fly_connectome_sim.experiment.recorder import OWNED, RunRecorder, VerifiedRun
from replay_helpers import engine_factory


def tiny_video(path, *, width=40, height=60, frames=121, rate=30):
    av = pytest.importorskip("av")
    with av.open(str(path), mode="w") as output:
        stream = output.add_stream("mpeg4", rate=rate)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p"
        for index in range(frames):
            rgb = np.zeros((height, width, 3), dtype=np.uint8)
            rgb[:, :, 0] = index % 256
            rgb[:, :, 1] = 25
            for packet in stream.encode(av.VideoFrame.from_ndarray(rgb, format="rgb24")):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    return path


def tiny_h264(path, *, width=40, height=60, frames=126, pts_offset=0):
    av = pytest.importorskip("av")
    with av.open(str(path), mode="w", format="mpegts") as output:
        stream = output.add_stream("libx264", rate=30)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p"
        stream.options = {"bf": "0", "preset": "ultrafast"}
        for index in range(frames):
            rgb = np.full((height, width, 3), index % 256, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            frame.pts = pts_offset + index
            frame.time_base = Fraction(1, 30)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    return path


def playlist(tmp_path, count=2, *, frames=121):
    paths = [tiny_video(tmp_path / f"clip-{index}.mp4", frames=frames) for index in range(count)]
    declaration = tmp_path / "playlist.json"
    declaration.write_text(json.dumps([
        {"path": str(path), "source_url": f"https://example.test/reel/{index}/"}
        for index, path in enumerate(paths)
    ]), encoding="utf-8")
    return declaration, paths


def test_half_up_boundaries_have_no_thirty_fps_drift():
    from fly_connectome_sim.experiment.video_observation import frame_tick

    assert [frame_tick(index) for index in range(7)] == [0, 333, 667, 1000, 1333, 1667, 2000]
    assert frame_tick(120) == 40000
    assert set(frame_tick(index + 1) - frame_tick(index) for index in range(120)) == {333, 334}


def test_preparation_decodes_complete_first_four_seconds_and_binds_pixels(tmp_path):
    from fly_connectome_sim.engine import _rgb_input_sha256
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    declaration, paths = playlist(tmp_path, count=1)
    prepared = prepare_playlist(declaration)
    assert len(prepared) == 1 and len(prepared[0].frames) == 120
    clip = prepared[0]
    assert clip.metadata["source_sha256"] == sha256(paths[0].read_bytes()).hexdigest()
    assert clip.metadata["source_url"] == "https://example.test/reel/0/"
    assert clip.metadata["source_time_base"] == [1, 15360]
    assert clip.metadata["origin_pts"] == 0
    assert clip.metadata["coverage_end_pts"] >= 61440
    assert clip.metadata["transform"]["width"] == 90
    assert clip.metadata["transform"]["height"] == 160
    assert clip.metadata["transform"]["inner_width"] == 90
    assert clip.metadata["transform"]["inner_height"] == 135
    assert clip.metadata["transform"]["padding"] == [0, 12, 0, 13]
    for index, frame in enumerate(clip.frames):
        assert frame.rgb.dtype == np.uint8 and frame.rgb.shape == (160, 90, 3)
        assert frame.frame_id == f"clip-0/frame-{index}"
        assert frame.sha256 == _rgb_input_sha256(frame.rgb)
        assert clip.metadata["frames"][index] == {
            "frame_id": frame.frame_id,
            "frame_index": index,
            "sha256": frame.sha256,
            "source_pts": frame.source_pts,
            "source_time_base": [1, 15360],
        }
    assert clip.frames[0].source_pts == 0
    assert clip.frames[1].source_pts == 512


def test_preparation_rejects_truncated_video_before_engine_and_output(tmp_path):
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    path = tiny_video(tmp_path / "short.mp4", frames=119)
    declaration = tmp_path / "short.json"
    declaration.write_text(json.dumps([{"path": str(path), "source_url": "https://example.test/short"}]))
    with pytest.raises(ValueError, match="coverage"):
        prepare_playlist(declaration)


@pytest.mark.parametrize("profile,frames", [("standard", 126), ("fast-feed", 601)])
def test_h264_nonorientation_sei_is_decoded_without_rejection(tmp_path, profile, frames):
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    source = tiny_h264(tmp_path / "h264.ts", frames=frames)
    declaration = tmp_path / "h264.json"
    declaration.write_text(json.dumps([{
        "path": str(source), "source_url": "https://example.test/h264",
    }]))
    prepared = prepare_playlist(declaration, profile=profile)
    assert len(prepared[0].frames) == 120
    assert prepared[0].metadata["source_width"] == 40
    assert prepared[0].metadata["source_height"] == 60


@pytest.mark.parametrize("profile,frames", [("standard", 63), ("fast-feed", 303)])
def test_h264_resolution_change_fails_before_engine_and_artifact(tmp_path, profile, frames):
    from fly_connectome_sim.experiment.video_observation import record_video_observation_run

    first = tiny_h264(tmp_path / "portrait.ts", width=40, height=60,
                      frames=frames, pts_offset=0)
    second = tiny_h264(tmp_path / "landscape.ts", width=60, height=40,
                       frames=frames, pts_offset=frames)
    source = tmp_path / "changing.ts"
    source.write_bytes(first.read_bytes() + second.read_bytes())
    declaration = tmp_path / "changing.json"
    declaration.write_text(json.dumps([{
        "path": str(source), "source_url": "https://example.test/changing",
    }]))
    import av
    with av.open(str(source)) as container:
        sizes = {(frame.width, frame.height) for frame in container.decode(video=0)}
    assert sizes == {(40, 60), (60, 40)}

    def forbidden():
        pytest.fail("changing source constructed an engine")

    target = tmp_path / "not-created"
    with pytest.raises(ValueError, match="dimension"):
        record_video_observation_run(target, playlist_path=declaration,
                                     engine_factory=forbidden, profile=profile)
    assert not target.exists()


@pytest.mark.parametrize("profile,frames,rate,speed", [
    ("standard", 961, 240, 1), ("fast-feed", 2401, 120, 5),
])
def test_high_fps_last_pts_selection_keeps_only_bounded_rgb_frames(tmp_path, monkeypatch, profile, frames, rate, speed):
    from fly_connectome_sim.experiment import video_observation

    source = tiny_video(tmp_path / "high-fps.mp4", frames=frames, rate=rate)
    declaration = tmp_path / "high-fps.json"
    declaration.write_text(json.dumps([{
        "path": str(source), "source_url": "https://example.test/high-fps",
    }]))
    original = video_observation._rgb
    references = []
    maximum_live = 0

    def track(frame, transform):
        nonlocal maximum_live
        result = original(frame, transform)
        references.append(weakref.ref(result))
        maximum_live = max(maximum_live, sum(ref() is not None for ref in references))
        return result

    monkeypatch.setattr(video_observation, "_rgb", track)
    clip = video_observation.prepare_playlist(declaration, profile=profile)[0]
    assert len(clip.frames) == 120
    assert len(references) >= 960
    assert maximum_live <= 125
    time_base = Fraction(*clip.metadata["source_time_base"])
    for index in (0, 1, 2, 60, 119):
        assert (clip.frames[index].source_pts - clip.metadata["origin_pts"]) * time_base == Fraction(speed * index, 30)


@pytest.mark.parametrize("profile,rate", [("standard", 1024), ("fast-feed", 205)])
def test_excessive_decoded_frame_work_fails_closed_before_engine(tmp_path, profile, rate):
    from fly_connectome_sim.experiment.video_observation import record_video_observation_run

    source = tiny_video(tmp_path / "too-fast.mp4", width=16, height=16,
                        frames=4097, rate=rate)
    declaration = tmp_path / "too-fast.json"
    declaration.write_text(json.dumps([{
        "path": str(source), "source_url": "https://example.test/too-fast",
    }]))

    def forbidden():
        pytest.fail("excessive source constructed an engine")

    target = tmp_path / "not-created"
    with pytest.raises(ValueError, match="decoded frame limit"):
        record_video_observation_run(target, playlist_path=declaration,
                                     engine_factory=forbidden, profile=profile)
    assert not target.exists()


@pytest.mark.parametrize("profile,frames", [("standard", 121), ("fast-feed", 601)])
def test_source_change_during_decode_prevents_engine_and_artifact(tmp_path, monkeypatch, profile, frames):
    from fly_connectome_sim.experiment import video_observation

    declaration, paths = playlist(tmp_path, count=1, frames=frames)
    original = video_observation._rgb
    changed = False

    def mutate_source(frame, transform):
        nonlocal changed
        if not changed:
            with paths[0].open("ab") as output:
                output.write(b"source changed during decode")
            changed = True
        return original(frame, transform)

    def forbidden():
        pytest.fail("changed source constructed an engine")

    monkeypatch.setattr(video_observation, "_rgb", mutate_source)
    target = tmp_path / "not-created"
    with pytest.raises(ValueError, match="changed"):
        video_observation.record_video_observation_run(
            target, playlist_path=declaration, engine_factory=forbidden, profile=profile,
        )
    assert not target.exists()


@pytest.mark.parametrize("count", [0, 6])
def test_playlist_count_is_bounded_before_decode(tmp_path, count):
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    declaration = tmp_path / "playlist.json"
    declaration.write_text(json.dumps([
        {"path": "unused.mp4", "source_url": "https://example.test/clip"}
        for _ in range(count)
    ]))
    with pytest.raises(ValueError, match="1–5"):
        prepare_playlist(declaration)


@pytest.fixture
def recording(tmp_path, engine_factory):
    from fly_connectome_sim.experiment.video_observation import record_video_observation_run

    declaration, _ = playlist(tmp_path)
    return record_video_observation_run(
        tmp_path / "recorded", playlist_path=declaration,
        engine_factory=engine_factory,
    )


def test_tiny_native_sealed_roundtrip_uses_exact_fed_pixels(recording, tmp_path):
    from fly_connectome_sim.experiment.video_observation import export_video_replay

    destination = tmp_path / "video-replay.json"
    replay = export_video_replay(recording.path, destination)
    assert json.loads(destination.read_text()) == replay
    assert set(replay) == {"version", "tick_ms", "source", "groups", "inputs", "segments", "duration_ticks"}
    assert replay["version"] == "measured-video-replay/v1"
    assert replay["duration_ticks"] == 80000
    assert replay["source"]["verification_mode"] == "integrity-only"
    assert len(replay["segments"]) == 240
    assert len(replay["inputs"]) == 240
    assert [replay["segments"][index]["source_end_tick"] for index in (0, 1, 2, 119, 120, 239)] == [333, 667, 1000, 40000, 40333, 80000]
    assert replay["segments"][119]["video_policy"]["reason"] == "clip_window_end"
    assert replay["segments"][-1]["video_policy"]["reason"] == "session_limit"
    events = list(recording.iter_events())
    assert events[0]["checkpoint_name"] == "brain-before.npz"
    assert events[-1]["checkpoint_name"] == "brain-after.npz"
    assert all(event["stimulation"] is None and event["learning"] is False
               and event["pathway_detail"] is False and event["qualification_detail"] is False
               for event in events[1:-1])
    for event, segment in zip(events[1:-1], replay["segments"], strict=True):
        frame = event["video_frame"]
        assert frame["sha256"] == event["telemetry"]["input_sha256"]
        assert segment["frame_id"] == frame["frame_id"]
        assert replay["inputs"][frame["frame_id"]]["rgb_base64"] == frame["rgb_base64"]


def rewrite(recording, target, mutate, *, metadata=None):
    with RunRecorder(target, run_kind="pilot",
                     metadata=recording.manifest["metadata"] if metadata is None else metadata,
                     root_branch_id=recording.manifest["root_branch_id"]) as recorder:
        for source in recording.iter_events():
            event = deepcopy({key: value for key, value in source.items() if key not in OWNED})
            mutate(event, source["sequence"])
            if "checkpoint_name" in event:
                recorder.ingest_checkpoint(event["checkpoint_name"],
                                           recording.path / "checkpoints" / event["checkpoint_name"],
                                           origin_branch_id=event["branch_id"])
            recorder.append(event)
    return target


@pytest.mark.parametrize("mutation", [
    "pixel", "frame_hash", "source_pts", "clock", "decision", "next_frame", "learning", "stimulation",
    "checkpoint_operation",
])
def test_export_rejects_rehashed_semantic_mutations(recording, tmp_path, mutation):
    from fly_connectome_sim.experiment.video_observation import export_video_replay

    def mutate(event, sequence):
        if mutation == "checkpoint_operation" and sequence == 0:
            event["operation_version"] = "unsupported/v1"
        if event["type"] != "observe":
            return
        if mutation == "pixel" and sequence == 1:
            event["video_frame"]["rgb_base64"] = "AAAA"
        elif mutation == "frame_hash" and sequence == 1:
            event["video_frame"]["sha256"] = "0" * 64
        elif mutation == "source_pts" and sequence == 1:
            event["video_frame"]["source_pts"] += 1
        elif mutation == "clock" and sequence == 1:
            event["start_tick"] = 1
        elif mutation == "decision" and sequence == 30:
            event["video_policy"]["reason"] = "motor_right"
        elif mutation == "next_frame" and sequence == 121:
            event["video_frame"]["frame_id"] = "clip-0/frame-0"
        elif mutation == "learning" and sequence == 1:
            event["learning"] = True
        elif mutation == "stimulation" and sequence == 1:
            event["stimulation"] = "ppl101"

    source = rewrite(recording, tmp_path / mutation, mutate)
    destination = tmp_path / f"{mutation}.json"
    with pytest.raises(ValueError):
        export_video_replay(source, destination)
    assert not destination.exists()


def test_sealed_prefix_and_tail_failure_never_publish(recording, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment.video_observation import export_video_replay
    from fly_connectome_sim.experiment.recorder import verify_run

    prefix = tmp_path / "prefix"
    with RunRecorder(prefix, run_kind="pilot", metadata=recording.manifest["metadata"],
                     root_branch_id=recording.manifest["root_branch_id"]) as recorder:
        for source in list(recording.iter_events())[:4]:
            event = deepcopy({key: value for key, value in source.items() if key not in OWNED})
            if "checkpoint_name" in event:
                recorder.ingest_checkpoint(event["checkpoint_name"],
                                           recording.path / "checkpoints" / event["checkpoint_name"],
                                           origin_branch_id=event["branch_id"])
            recorder.append(event)
        recorder.ingest_checkpoint("brain-after.npz",
                                   recording.path / "checkpoints" / "brain-after.npz",
                                   origin_branch_id=recording.manifest["root_branch_id"])
        recorder.append({
            "type": "checkpoint", "branch_id": recording.manifest["root_branch_id"],
            "sim_ms": 100.0, "sim_tick": 1000,
            "checkpoint_name": "brain-after.npz",
        })
    assert verify_run(prefix).manifest["event_count"] == 5
    with pytest.raises(ValueError, match="[Tt]erminal|[Pp]refix|session|[Pp]remature"):
        export_video_replay(prefix, tmp_path / "prefix.json")
    assert not (tmp_path / "prefix.json").exists()
    output = tmp_path / "tail.json"
    original = VerifiedRun.iter_events

    def failing(self):
        yield from original(self)
        assert not output.exists()
        raise OSError("tail failed")

    monkeypatch.setattr(VerifiedRun, "iter_events", failing)
    with pytest.raises(OSError, match="tail failed"):
        export_video_replay(recording.path, output)
    assert not output.exists()



def test_fast_feed_decodes_twenty_seconds_at_five_times_source_speed(tmp_path):
    import av
    from PIL import Image
    from fly_connectome_sim.engine import _rgb_input_sha256
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    declaration, paths = playlist(tmp_path, count=1, frames=601)
    clip = prepare_playlist(declaration, profile="fast-feed")[0]
    assert len(clip.frames) == 120
    base = Fraction(*clip.metadata["source_time_base"])
    assert (clip.metadata["coverage_end_pts"] - clip.metadata["origin_pts"]) * base == 20
    assert clip.metadata["source_sha256"] == sha256(paths[0].read_bytes()).hexdigest()
    with av.open(str(paths[0])) as container:
        decoded = list(container.decode(video=0))
        for index in (0, 1, 2, 60, 119):
            prepared = clip.frames[index]
            assert (prepared.source_pts - clip.metadata["origin_pts"]) * base == Fraction(5 * index, 30)
            source = decoded[5 * index].to_ndarray(format="rgb24")
            expected = np.zeros((160, 90, 3), dtype=np.uint8)
            expected[12:147] = np.asarray(Image.fromarray(source).resize(
                (90, 135), resample=Image.Resampling.BILINEAR,
            ))
            np.testing.assert_array_equal(prepared.rgb, expected)
            assert prepared.sha256 == _rgb_input_sha256(expected)
            assert not prepared.rgb.flags.writeable


@pytest.mark.parametrize("frames", [121, 599])
def test_fast_feed_short_source_fails_before_engine_and_output(tmp_path, frames):
    from fly_connectome_sim.experiment.video_observation import record_video_observation_run

    declaration, _ = playlist(tmp_path, count=1, frames=frames)
    def forbidden():
        pytest.fail("short fast-feed source constructed an engine")
    target = tmp_path / "short-fast"
    with pytest.raises(ValueError, match="coverage"):
        record_video_observation_run(target, playlist_path=declaration,
                                     engine_factory=forbidden, profile="fast-feed")
    assert not target.exists()


@pytest.fixture
def fast_recording(tmp_path, engine_factory):
    from fly_connectome_sim.experiment.video_observation import record_video_observation_run

    declaration, _ = playlist(tmp_path, frames=601)
    return record_video_observation_run(tmp_path / "fast-recorded", playlist_path=declaration,
                                        engine_factory=engine_factory, profile="fast-feed")


def test_fast_feed_tiny_native_roundtrip_preserves_simulation_clock(fast_recording, tmp_path):
    from fly_connectome_sim.experiment.video_observation import VIDEO_RECIPE, export_video_replay

    output = tmp_path / "fast.json"
    replay = export_video_replay(fast_recording.path, output)
    assert json.loads(output.read_text()) == replay
    assert set(replay) == {"version", "tick_ms", "source", "groups", "inputs", "segments", "duration_ticks"}
    assert replay["version"] == "measured-video-replay/v2"
    metadata = replay["source"]["metadata"]
    assert metadata["protocol_version"] == "video-observation/v2"
    assert metadata["stimulus_version"] == "decoded-video-rgb/v2"
    assert metadata["video_recipe"] == {
        **VIDEO_RECIPE, "policy_version": "right-scroll/v2", "minimum_dwell_ticks": 30000,
        "source_speed": [5, 1], "source_window_seconds": 20,
    }
    assert replay["duration_ticks"] == 80000 and len(replay["segments"]) == 240
    assert replay["source"]["verification_mode"] == "integrity-only"
    assert [replay["segments"][i]["source_end_tick"] for i in (0, 1, 2, 119, 120, 239)] == [333, 667, 1000, 40000, 40333, 80000]
    assert replay["segments"][86]["video_policy"]["reason"] == "minimum_dwell"
    assert replay["segments"][89]["video_policy"]["minimum_dwell_met"] is True
    assert replay["segments"][119]["video_policy"]["trigger"] == "clip_window_end"
    assert replay["segments"][-1]["video_policy"]["reason"] == "session_limit"
    events = list(fast_recording.iter_events())
    for event, segment in zip(events[1:-1], replay["segments"], strict=True):
        frame = event["video_frame"]
        assert frame["sha256"] == event["telemetry"]["input_sha256"]
        assert replay["inputs"][frame["frame_id"]]["rgb_base64"] == frame["rgb_base64"]
        assert event["stimulation"] is None and event["learning"] is False
        assert event["pathway_detail"] is False and event["qualification_detail"] is False


@pytest.mark.parametrize("mutation", [
    "protocol", "stimulus", "policy_recipe", "speed", "coverage", "dwell", "extra_profile",
    "pts_bound", "negative_pts", "event_policy", "event_pts", "pixel",
])
def test_fast_feed_export_rejects_mixed_profiles_and_rehashed_mutations(fast_recording, tmp_path, mutation):
    from fly_connectome_sim.experiment.video_observation import export_video_replay

    metadata = deepcopy(fast_recording.manifest["metadata"])
    if mutation == "protocol":
        metadata["protocol_version"] = "video-observation/v1"
    elif mutation == "stimulus":
        metadata["stimulus_version"] = "decoded-video-rgb/v1"
    elif mutation == "policy_recipe":
        metadata["video_recipe"]["policy_version"] = "right-scroll/v1"
    elif mutation == "speed":
        metadata["video_recipe"]["source_speed"] = [1, 1]
    elif mutation == "coverage":
        metadata["clips"][0]["coverage_end_pts"] //= 5
    elif mutation == "dwell":
        metadata["video_recipe"]["minimum_dwell_ticks"] = 10000
    elif mutation == "extra_profile":
        metadata["profile"] = "fast-feed"
    elif mutation == "pts_bound":
        metadata["clips"][0]["frames"][1]["source_pts"] = 3072
    elif mutation == "negative_pts":
        metadata["clips"][0]["frames"][1]["source_pts"] = -1
    def mutate(event, sequence):
        if mutation == "event_policy" and sequence == 3:
            event["video_policy"]["policy_version"] = "right-scroll/v1"
        elif mutation == "event_pts" and sequence == 1:
            event["video_frame"]["source_pts"] += 1
        elif mutation == "pixel" and sequence == 1:
            event["video_frame"]["rgb_base64"] = "AAAA"
    source = rewrite(fast_recording, tmp_path / mutation, mutate, metadata=metadata)
    destination = tmp_path / f"{mutation}.json"
    with pytest.raises(ValueError):
        export_video_replay(source, destination)
    assert not destination.exists()


def test_unknown_preparation_profile_is_rejected_before_decode(tmp_path):
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    with pytest.raises(ValueError, match="profile"):
        prepare_playlist(tmp_path / "unused.json", profile="custom")



def test_fast_feed_accepts_exact_twenty_second_final_duration(tmp_path):
    from fly_connectome_sim.experiment.video_observation import prepare_playlist

    declaration, _ = playlist(tmp_path, count=1, frames=600)
    clip = prepare_playlist(declaration, profile="fast-feed")[0]
    assert clip.metadata["coverage_method"] == "final_frame_duration"
    assert (clip.metadata["coverage_end_pts"] - clip.metadata["origin_pts"]) * Fraction(*clip.metadata["source_time_base"]) == 20


@pytest.mark.parametrize("field,value", [
    ("source_speed", [5, 1]), ("source_window_seconds", 20),
    ("minimum_dwell_ticks", 30000), ("policy_version", "right-scroll/v2"),
])
def test_standard_export_rejects_fast_feed_recipe_fields(recording, tmp_path, field, value):
    from fly_connectome_sim.experiment.video_observation import export_video_replay

    metadata = deepcopy(recording.manifest["metadata"])
    metadata["video_recipe"][field] = value
    source = rewrite(recording, tmp_path / field, lambda event, sequence: None, metadata=metadata)
    destination = tmp_path / f"{field}.json"
    with pytest.raises(ValueError, match="metadata"):
        export_video_replay(source, destination)
    assert not destination.exists()
