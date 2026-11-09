"""Bounded private run snapshots and exclusive complete JSON publication."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import tempfile

from fly_connectome_sim.experiment import recorder as artifacts


def _safe_directory(path: Path) -> tuple[int, int]:
    for directory in (path, *path.parents):
        if directory.is_symlink() or directory.is_junction() or not directory.is_dir():
            raise ValueError(f"Unsafe input directory: {directory}")
    state = path.stat(follow_symlinks=False)
    return state.st_dev, state.st_ino


def _copy_bounded(source: Path, target: Path, limit: int) -> None:
    """Copy at most cap+1 bytes, checking the opened regular file's identity."""
    directory_identity = _safe_directory(source.parent)
    before = source.stat(follow_symlinks=False)
    if source.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Unsafe input file: {source}")
    if before.st_size > limit:
        raise ValueError(f"Input file exceeds read limit: {source.name}")
    with source.open("rb") as reader, target.open("xb") as writer:
        opened = os.fstat(reader.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)):
            raise ValueError("Input file changed during open")
        consumed = 0
        while block := reader.read(min(1024 * 1024, limit - consumed + 1)):
            consumed += len(block)
            if consumed > limit:
                raise ValueError(f"Input file exceeds read limit: {source.name}")
            writer.write(block)
        after = source.stat(follow_symlinks=False)
        if (source.is_symlink() or not stat.S_ISREG(after.st_mode)
                or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
                or _safe_directory(source.parent) != directory_identity):
            raise ValueError("Input file or directory changed during copy")


@contextmanager
def snapshot_recorded_run(source: Path, *, limits: artifacts.RunReadLimits,
                          checkpoint_byte_limit: int):
    """Yield an owned, capped snapshot; callers finish verification inside context."""
    source = Path(source).absolute()
    source_identity = _safe_directory(source)
    with tempfile.TemporaryDirectory(prefix="fly-market-inventory-") as scratch:
        snapshot = Path(scratch)
        (snapshot / "checkpoints").mkdir()
        _copy_bounded(source / "run.json", snapshot / "run.json", limits.max_manifest_bytes)
        manifest, _ = artifacts._read_manifest(snapshot, limits=limits)
        directory = source / "checkpoints"
        checkpoint_identity = _safe_directory(directory)
        with os.scandir(directory) as entries:
            names = set()
            for entry in entries:
                names.add(entry.name)
                if len(names) > limits.max_checkpoints:
                    raise ValueError("Checkpoint directory exceeds read limit")
        if names != set(manifest["checkpoints"]):
            raise ValueError("Missing or extra checkpoint files")
        for name, declaration in manifest["checkpoints"].items():
            if declaration["size"] > checkpoint_byte_limit:
                raise ValueError("Declared checkpoint exceeds read limit")
            _copy_bounded(directory / name, snapshot / "checkpoints" / name, checkpoint_byte_limit)
        _copy_bounded(source / "events.jsonl", snapshot / "events.jsonl", limits.max_events_bytes)
        if _safe_directory(source) != source_identity or _safe_directory(directory) != checkpoint_identity:
            raise ValueError("Source directories changed during snapshot")
        yield snapshot


def write_json_exclusive(payload: dict, path: Path) -> None:
    """Fully write an owned temporary file, then publish exclusively and atomically."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8") + b"\n"
    output = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=output.parent, prefix=f".{output.name}.",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
