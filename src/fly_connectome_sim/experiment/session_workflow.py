"""One continuous session bundle and engine-free, integrity-only inspection.

A receipt records completion bookkeeping, not native history or scientific support.
Failures retain partial output for manual diagnosis; no stage retries or repairs.
"""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import tempfile
from typing import Callable

from ..engine import FlyEngine
from . import feed_event_session as session
from .recorder import RunArtifactError, _canonical, _strict_load, verify_run


MAX_RECEIPT_BYTES = 16 * 1024
SOURCE_FIELDS = (*session.cards.SOURCE_FIELDS, "verification_mode")


def _safe_path(path: Path, *, directory: bool) -> None:
    for member in (path, *path.absolute().parents):
        if member.is_symlink() or member.is_junction():
            raise RunArtifactError(f"Session symlink or junction rejected: {member}")
        if member != path and not member.is_dir():
            raise RunArtifactError(f"Session ancestor is not a directory: {member}")
    if not (path.is_dir() if directory else path.is_file()):
        raise RunArtifactError(f"Missing or nonregular session member: {path}")


def _members(target: Path, *, receipt: bool) -> dict[str, Path]:
    _safe_path(target, directory=True)
    _safe_path(target / "run", directory=True)
    names = ("receipt.json", "recording.json", "plan.json") if receipt else ("recording.json", "plan.json")
    paths = {name: target / name for name in names}
    for path in paths.values():
        _safe_path(path, directory=False)
    files = list(paths.values())
    if any(left.samefile(right) for index, left in enumerate(files) for right in files[index + 1:]):
        raise RunArtifactError("Session members alias each other")
    return paths


def _read(path: Path, limit: int) -> bytes:
    with path.open("rb") as reader:
        raw = reader.read(limit + 1)
    if len(raw) > limit:
        raise RunArtifactError(f"Session member exceeds byte bound: {path.name}")
    return raw


def _source(run) -> dict:
    source = {name: run.manifest[name] for name in session.cards.SOURCE_FIELDS}
    if run.verification_mode != "integrity-only":
        raise RunArtifactError("Session requires integrity-only verification")
    source["verification_mode"] = run.verification_mode
    # Freeze values independently of mutable returned manifests or exporter results.
    return _strict_load(_canonical(source))


def _same(actual: object, expected: object, message: str) -> None:
    if _canonical(actual) != _canonical(expected):
        raise RunArtifactError(message)


def _bound_exports(replay: dict, plan: dict, source: dict, original_plan: dict) -> None:
    _same({name: replay["source"][name] for name in SOURCE_FIELDS}, source,
          "Session replay source differs from recorded source")
    _same(plan["source"], source, "Session plan source differs from recorded source")
    _same(replay["plan"], original_plan, "Session replay plan differs from recorded plan")
    _same(plan, original_plan, "Session exported plan differs from recorded plan")


def _summary(target: Path, replay: dict) -> dict:
    plan, decision = replay["plan"], replay["decision"]
    return {
        "path": str(target), "status": "complete", "verification_mode": "integrity-only",
        "plan_status": plan["status"], "selected_option_id": plan["selected_option_id"],
        "selected_title": None if plan["selected_option"] is None else plan["selected_option"]["title"],
        "duration_ticks": replay["duration_ticks"], "feed_end_tick": replay["feed_end_tick"],
        "window_start_tick": decision["window_start_tick"], "window_end_tick": decision["window_end_tick"],
        "counts": decision["counts"],
        "files": {name: str(target / name) for name in ("run", "recording.json", "plan.json", "receipt.json")},
    }


def _inspect(target: Path, *, receipt: bool, original_source: dict | None = None,
             original_plan: dict | None = None) -> tuple[dict, bytes]:
    paths = _members(target, receipt=receipt)
    limits = {"receipt.json": MAX_RECEIPT_BYTES, "recording.json": session.MAX_REPLAY_BYTES,
              "plan.json": session.MAX_PLAN_BYTES}
    # All fixed members/aliases are checked, then every file is bounded before decoding.
    raw = {name: _read(path, limits[name]) for name, path in paths.items()}
    parsed_receipt = _strict_load(raw["receipt.json"]) if receipt else None
    run = verify_run(target / "run", limits=session.EXPORT_READ_LIMITS)
    source = _source(run)
    if original_source is not None:
        _same(source, original_source, "Session source changed after recording")
    replay = session._export_data(run)  # Complete semantic iteration, including normal EOF.
    plan = replay["plan"]
    _bound_exports(replay, plan, source, plan if original_plan is None else original_plan)
    for name, expected in (("recording.json", replay), ("plan.json", plan)):
        if raw[name] != _canonical(expected) + b"\n":
            raise RunArtifactError(f"Session file differs from canonical raw derivation: {name}")
    expected_receipt = {
        "version": "session-bundle/v1", "status": "complete", "source": source,
        "files": {name: {"size_bytes": len(raw[name]), "sha256": sha256(raw[name]).hexdigest()}
                  for name in ("recording.json", "plan.json")},
    }
    receipt_raw = _canonical(expected_receipt) + b"\n"
    if len(receipt_raw) > MAX_RECEIPT_BYTES:
        raise RunArtifactError("Session receipt exceeds byte bound")
    if receipt:
        _same(parsed_receipt, expected_receipt, "Session receipt differs from raw derivation")
        if raw["receipt.json"] != receipt_raw:
            raise RunArtifactError("Session receipt is not canonical JSON plus LF")
    return _summary(target, replay), receipt_raw


def _publish_receipt(path: Path, raw: bytes) -> None:
    session.cards._new_output(None, path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".session-receipt-", suffix=".tmp",
                                         delete=False) as writer:
            temporary = Path(writer.name)
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        if os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_session(output_dir: str | Path, *, playlist_path: str | Path, proposal_path: str | Path,
                engine_factory: Callable[[], FlyEngine]) -> dict:
    """Reserve a new bundle and compose the existing continuous recorder/exports once."""
    target = Path(output_dir)
    stage = "reserve"
    try:
        session.cards._new_output(None, target)
        _safe_path(target.parent, directory=True)
        target.mkdir()
        stage = "record"
        recorded = session.record_feed_event_session(
            target / "run", playlist_path=playlist_path, proposal_path=proposal_path,
            engine_factory=engine_factory,
        )
        source = _source(recorded)
        stage = "replay"
        replay = session.export_session_replay(target / "run", target / "recording.json")
        _bound_exports(replay, replay["plan"], source, replay["plan"])
        original_plan = _strict_load(_canonical(replay["plan"]))
        stage = "plan"
        plan = session.export_session_plan(target / "run", target / "plan.json")
        _bound_exports(replay, plan, source, original_plan)
        stage = "finalize"
        summary, receipt_raw = _inspect(target, receipt=False, original_source=source,
                                        original_plan=original_plan)
        stage = "receipt"
        _publish_receipt(target / "receipt.json", receipt_raw)
        return summary
    except Exception as error:
        raise RunArtifactError(f"Session {stage} failed; retained bundle {target}, run {target / 'run'}: {error}") from error


def inspect_session(path: str | Path) -> dict:
    """Read and derive fixed local members without engine construction, network or writes."""
    target = Path(path)
    try:
        return _inspect(target, receipt=True)[0]
    except Exception as error:
        raise RunArtifactError(f"Session inspect failed; retained bundle {target}, run {target / 'run'}: {error}") from error
