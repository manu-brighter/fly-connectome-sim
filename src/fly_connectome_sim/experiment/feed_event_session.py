"""One continuous reward-free fast feed followed immediately by event cards.

Exports bind recorded global clocks and counts, with integrity-only verification.
Continuity does not establish a causal or semantic effect of the earlier reels.
"""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import tempfile
from typing import Callable

from ..engine import FlyEngine
from . import event_choice as cards
from . import video_observation as video
from .event_cards import RENDERER_RECIPE, load_proposal_with_source, render_event_cards
from .measured_replay import _integer, _ticks
from .recorder import RunArtifactError, RunReadLimits, RunRecorder, VerifiedRun, _canonical, verify_run
from .video_policy import evaluate_video_policy


ROOT_BRANCH = "feed-event/root"
EXPORT_READ_LIMITS = RunReadLimits(
    max_manifest_bytes=2 * 1024 * 1024, max_event_line_bytes=1024 * 1024,
    max_events_bytes=64 * 1024 * 1024, max_events=246, max_checkpoints=2,
)
CHOICE_RECIPE = {**cards.CHOICE_RECIPE, "timing_origin": "feed-stop/v1"}
MAX_REPLAY_BYTES = 32 * 1024 * 1024
MAX_PLAN_BYTES = 64 * 1024


def _metadata(identity: dict, clips: list[dict], proposal: dict, source: dict, frame: dict) -> dict:
    return {
        "engine_identity": identity, "protocol_version": "feed-event-session/v1",
        "stimulus_version": "feed-event-rgb/v1", "family": "feed-event-session", "seeds": [],
        "factors": {"clip_count": len(clips), "left_option_id": proposal["options"][0]["id"],
                    "right_option_id": proposal["options"][1]["id"]},
        "video_recipe": video._video_recipe("fast-feed"), "clips": clips,
        "proposal": proposal, "proposal_source": source,
        "proposal_sha256": sha256(_canonical(proposal)).hexdigest(),
        "renderer_recipe": RENDERER_RECIPE, "input": frame, "choice_recipe": CHOICE_RECIPE,
        "input_sha256": sorted({frame["sha256"], *(item["sha256"] for clip in clips for item in clip["frames"])}),
    }


def _validated_metadata(metadata: dict) -> tuple[list[dict], dict, dict, dict]:
    clips = metadata["clips"]
    video._validated_clips(clips, profile="fast-feed")
    proposal = cards._validated_proposal_source(metadata["proposal"], metadata["proposal_source"])
    frame = cards._frame_payload(render_event_cards(proposal))
    cards._same(metadata, _metadata(metadata["engine_identity"], clips, proposal,
                                   metadata["proposal_source"], frame),
                "Session metadata differs from closed feed/proposal/render/choice recipe")
    return clips, proposal, frame, cards._groups(metadata["engine_identity"])


def record_feed_event_session(output_dir: str | Path, *, playlist_path: str | Path,
                              proposal_path: str | Path,
                              engine_factory: Callable[[], FlyEngine]) -> VerifiedRun:
    """Own one actual engine and recorder for both phases, without state resets."""
    proposal, source = load_proposal_with_source(proposal_path)
    frame = render_event_cards(proposal)
    payload = cards._frame_payload(frame)
    clips = video.prepare_playlist(playlist_path, profile="fast-feed")
    target = Path(output_dir)
    cards._new_output(None, target)
    engine = engine_factory()
    if (not isinstance(engine, FlyEngine) or engine.brain.cursor != 0
            or _ticks(float(engine.brain.sim_ms)) != 0 or engine.brain.dt != 0.1
            or engine.brain.weights_frozen):
        raise RunArtifactError("Session requires one fresh actual 0.1 ms unfrozen engine")
    metadata = _metadata(engine.identity(), [clip.metadata for clip in clips], proposal, source, payload)
    _validated_metadata(metadata)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".session-checkpoint-") as scratch:
        checkpoint = Path(scratch) / "brain.npz"
        with RunRecorder(target, run_kind="pilot", metadata=metadata, root_branch_id=ROOT_BRANCH) as recorder:
            def save(name: str) -> None:
                engine.brain.checkpoint(checkpoint)
                recorder.ingest_checkpoint(name, checkpoint, origin_branch_id=ROOT_BRANCH)
                recorder.append({"type": "checkpoint", "branch_id": ROOT_BRANCH,
                                 "sim_ms": engine.brain.cursor / 10, "sim_tick": engine.brain.cursor,
                                 "checkpoint_name": name})

            save("brain-before.npz")
            video_count = 0
            for event in video._observe_video_phase(
                engine, clips, branch_id=ROOT_BRANCH, start_tick=0, profile="fast-feed",
            ):
                recorder.append(event)
                video_count += 1
            feed_end = engine.brain.cursor
            for event in cards._observe_event_phase(
                engine, proposal=proposal, frame=frame, payload=payload, branch_id=ROOT_BRANCH,
                start_tick=feed_end, sequence_start=video_count + 1,
            ):
                recorder.append(event)
            save("brain-after.npz")
    run = verify_run(target)
    _export_data(run)
    return run


def _checkpoint(event: dict, *, before: bool, tick: int) -> None:
    if (set(event) != cards.CHECKPOINT_FIELDS or event["type"] != "checkpoint"
            or event["checkpoint_name"] != ("brain-before.npz" if before else "brain-after.npz")
            or _integer(event["sim_tick"], "checkpoint tick") != tick
            or _ticks(event["sim_ms"]) != tick):
        raise RunArtifactError("Invalid outer session checkpoint")


def _export_data(run: VerifiedRun) -> dict:
    manifest = run.manifest
    if (manifest["run_kind"] != "pilot" or manifest["root_branch_id"] != ROOT_BRANCH
            or set(manifest["checkpoints"]) != {"brain-before.npz", "brain-after.npz"}
            or manifest["state_anchors"] or run.verification_mode != "integrity-only"):
        raise RunArtifactError("Only ordinary sealed continuous root pilots are supported")
    metadata = manifest["metadata"]
    clips, proposal, frame, groups = _validated_metadata(metadata)
    identity = metadata["engine_identity"]
    populations = {name: groups[name] for name in cards.MOTOR_GROUPS}
    clip_index = frame_index = clip_start = end_tick = event_count = bin_count = card_count = 0
    motor_counts = []
    segments, inputs = [], {}
    feed_end = final = None
    seen_after = False
    for event in run.iter_events():
        sequence = event_count
        event_count += 1
        if (event_count > 246 or event["branch_id"] != ROOT_BRANCH
                or _integer(event["sequence"], "event sequence") != sequence
                or any(name.startswith("parent_") for name in event)):
            raise RunArtifactError("Unsupported session branch, sequence or event bound")
        if sequence == 0:
            _checkpoint(event, before=True, tick=0)
            continue
        if card_count == 4:
            if seen_after:
                raise RunArtifactError("Extra operation after session checkpoint")
            _checkpoint(event, before=False, tick=end_tick)
            seen_after = True
            continue
        if len(segments) >= 244 or event["type"] != "observe":
            raise RunArtifactError("Premature checkpoint or excessive session observations")
        if feed_end is None:
            if len(segments) >= 240 or set(event["telemetry"]) != cards.TELEMETRY_FIELDS:
                raise RunArtifactError("Excessive feed observations or unsupported telemetry")
            frame_map = clips[clip_index]["frames"][frame_index]
            segment, counts = video._segment(
                event, frame_map, clip_index=clip_index, frame_index=frame_index,
                start_tick=end_tick, groups=groups, identity=identity, branch_id=ROOT_BRANCH,
            )
            if event["telemetry"]["total_spikes"] < max(
                sum(bin_["group_spikes"][name] for bin_ in segment["bins"]) for name in groups
            ):
                raise RunArtifactError("Feed population counts exceed whole-brain spikes")
            motor_counts.append(counts)
            end_tick = segment["source_end_tick"]
            if end_tick > 80000:
                raise RunArtifactError("Feed exceeds the closed eight-second cap")
            payload = event["video_frame"]
            inputs[payload["frame_id"]] = {name: payload[name] for name in (
                "sha256", "width", "height", "rgb_base64", "clip_id", "frame_index",
                "source_pts", "source_time_base",
            )}
            if frame_index % 3 == 2:
                policy = evaluate_video_policy(
                    counts=motor_counts, populations=populations, clip_index=clip_index,
                    clip_count=len(clips), clip_start_tick=clip_start, frame_index=frame_index,
                    end_tick=end_tick, profile="fast-feed",
                )
                cards._same(event["video_policy"], policy, "Session feed policy differs from measured prefix")
                if policy["action"] == "stop":
                    feed_end = end_tick
                elif policy["action"] == "advance":
                    clip_index = policy["next_clip_index"]
                    frame_index = 0
                    clip_start = end_tick
                    motor_counts = []
                else:
                    frame_index += 1
            else:
                frame_index += 1
        else:
            segment, evidence = cards._segment(
                event, card_count, identity=identity, groups=groups, frame=frame, proposal=proposal,
                branch_id=ROOT_BRANCH, start_tick=feed_end, sequence_start=sequence - card_count,
            )
            end_tick = segment["source_end_tick"]
            card_count += 1
            if card_count == 4:
                final = {
                    "policy_version": cards.POLICY_VERSION, "effective_tick": end_tick,
                    "event_sequence": sequence, "event_scientific_sha256": event["scientific_sha256"],
                    "window_start_tick": feed_end + 15000, "window_end_tick": end_tick, **evidence,
                    "selected_option_id": cards._selected(evidence["readout"], proposal),
                }
        segments.append(segment)
        bin_count += len(segment["bins"])
        if bin_count > 1160:
            raise RunArtifactError("Excessive measured session bins")
    # Publication is possible only after the genuine verifier iterator reaches normal EOF.
    if (feed_end is None or card_count != 4 or final is None or not seen_after
            or event_count != len(segments) + 2 or end_tick != feed_end + 20000
            or sum(len(segment["bins"]) for segment in segments[-4:]) != 200):
        raise RunArtifactError("Incomplete continuous feed/event session")
    source = {**{name: manifest[name] for name in cards.SOURCE_FIELDS},
              "verification_mode": run.verification_mode}
    selected_id = final["selected_option_id"]
    selected = next((option for option in proposal["options"] if option["id"] == selected_id), None)
    plan = {
        "version": "event-plan/v1", "status": "selected" if selected is not None else "deferred",
        "brief": proposal["brief"], "selected_option_id": selected_id, "selected_option": selected,
        "decision_ref": {"event_sequence": final["event_sequence"],
                         "scientific_sha256": final["event_scientific_sha256"],
                         "input_sha256": frame["sha256"], "policy_version": cards.POLICY_VERSION},
        "source": source,
    }
    inputs["options"] = {name: value for name, value in frame.items() if name != "frame_id"}
    return {
        "version": "feed-event-replay/v1", "tick_ms": 0.1,
        "source": {**source, "metadata": metadata}, "groups": groups, "inputs": inputs,
        "segments": segments, "duration_ticks": end_tick, "feed_end_tick": feed_end,
        "decision": final, "plan": plan,
    }


def _export(run_dir: str | Path, output_path: str | Path, *, plan_only: bool) -> dict:
    output = Path(output_path)
    cards._new_output(Path(run_dir), output)
    run = verify_run(run_dir, limits=EXPORT_READ_LIMITS)
    try:
        replay = _export_data(run)
    except (KeyError, TypeError, AttributeError, IndexError, OverflowError) as error:
        raise RunArtifactError(f"Incomplete continuous session source: {error}") from error
    data = replay["plan"] if plan_only else replay
    raw = _canonical(data) + b"\n"
    if len(raw) > (MAX_PLAN_BYTES if plan_only else MAX_REPLAY_BYTES):
        raise RunArtifactError("Session export exceeds its closed byte bound")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".session-export-", suffix=".tmp", delete=False) as writer:
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


def export_session_replay(run_dir: str | Path, output_path: str | Path) -> dict:
    """Independently verify the complete source before publishing its replay."""
    return _export(run_dir, output_path, plan_only=False)


def export_session_plan(run_dir: str | Path, output_path: str | Path) -> dict:
    """Independently verify both phases and publish their frozen bound plan."""
    return _export(run_dir, output_path, plan_only=True)
