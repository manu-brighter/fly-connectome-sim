"""Streaming, integrity-checked run artifacts (hashes are not authentication)."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Iterator


FORMAT_VERSION = "run-artifact/v1"
SCHEMA_VERSION = "run-schema/v1"
GENESIS = "0" * 64
OWNED = {"sequence", "previous_scientific_sha256", "scientific_sha256", "run_metadata_sha256"}
REQUIRED_METADATA = {"engine_identity", "protocol_version", "stimulus_version", "family", "seeds", "factors", "input_sha256"}
CHECKPOINT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.npz$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DEVICES = ({"CON", "PRN", "AUX", "NUL"}
                   | {f"COM{number}" for number in range(1, 10)}
                   | {f"LPT{number}" for number in range(1, 10)})


class RunArtifactError(ValueError):
    """An incomplete or invalid run artifact."""


def _canonical(value: object) -> bytes:
    def check_keys(item: object) -> None:
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise RunArtifactError("JSON object keys must be strings")
            for child in item.values():
                check_keys(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                check_keys(child)

    try:
        check_keys(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except RunArtifactError:
        raise
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as error:
        raise RunArtifactError(f"Invalid strict JSON: {error}") from error


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            raise RunArtifactError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_load(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              RunArtifactError(f"Nonfinite JSON value: {value}")))
    except RunArtifactError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise RunArtifactError(f"Invalid JSON: {error}") from error


def _scientific(value: object) -> object:
    if isinstance(value, dict):
        return {key: _scientific(item) for key, item in value.items()
                if key not in {"compute_seconds", "kernel_seconds"}}
    if isinstance(value, list):
        return [_scientific(item) for item in value]
    return value


def _scientific_event(event: dict) -> dict:
    return _scientific({key: value for key, value in event.items()
                        if key != "scientific_sha256"})


def _metadata(metadata: dict) -> dict:
    if not isinstance(metadata, dict) or not REQUIRED_METADATA <= metadata.keys():
        raise RunArtifactError("Missing run metadata declaration")
    result = _strict_load(_canonical(metadata))
    if not isinstance(result["engine_identity"], dict) or not result["engine_identity"]:
        raise RunArtifactError("Missing engine identity")
    if any(not isinstance(result[name], str) or not result[name]
           for name in ("protocol_version", "stimulus_version", "family")):
        raise RunArtifactError("Invalid protocol or stimulus declaration")
    if (not isinstance(result["seeds"], list)
            or any(type(seed) is not int or seed < 0 for seed in result["seeds"])
            or not isinstance(result["factors"], dict)
            or not isinstance(result["input_sha256"], list)
            or any(not isinstance(item, str) or not DIGEST.fullmatch(item)
                   for item in result["input_sha256"])):
        raise RunArtifactError("Invalid seeds, factors or input hash set")
    return result


def _metadata_digest(run_kind: str, root_branch_id: str, metadata: dict) -> str:
    return sha256(_canonical({"run_kind": run_kind, "root_branch_id": root_branch_id,
                              "metadata": metadata})).hexdigest()


def _schema_digest() -> str:
    return sha256(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes()).hexdigest()


def _safe_name(name: object) -> str:
    if (not isinstance(name, str) or name in {".", ".."}
            or not CHECKPOINT_NAME.fullmatch(name)
            or name.split(".", 1)[0].upper() in WINDOWS_DEVICES):
        raise RunArtifactError("Unsafe checkpoint name")
    return name


def _directory_identity(path: Path) -> tuple[int, int]:
    if path.is_symlink() or path.is_junction() or not path.is_dir():
        raise RunArtifactError(f"Run directory substituted: {path}")
    state = path.stat(follow_symlinks=False)
    return state.st_dev, state.st_ino


def _walk_bindings(value: object, metadata: dict) -> None:
    if isinstance(value, dict):
        if "engine_identity" in value and value["engine_identity"] != metadata["engine_identity"]:
            raise RunArtifactError("Engine identity mismatch")
        if "input_sha256" in value and value["input_sha256"] is not None \
                and value["input_sha256"] not in metadata["input_sha256"]:
            raise RunArtifactError("Undeclared input hash")
        for item in value.values():
            _walk_bindings(item, metadata)
    elif isinstance(value, list):
        for item in value:
            _walk_bindings(item, metadata)


def _finite_number(value: object, *, positive: bool = False,
                   allow_negative: bool = False) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        number = float(value)
    except OverflowError:
        return False
    return math.isfinite(number) and (allow_negative or
                                      (number > 0 if positive else number >= 0))


def _numeric_object(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields \
        and all(_finite_number(item, allow_negative=True) for item in value.values())


def _check_qualification_result(event: dict, metadata: dict) -> None:
    required = {"status", "family", "seeds", "selected_configuration",
                "selected_window", "selected_retention_ms", "observed_effect_sign",
                "benchmark", "compute_seconds"}
    if not required <= event.keys():
        raise RunArtifactError("Incomplete qualification result")
    if type(event["status"]) is not str \
            or event["status"] not in {"supported", "unsupported"} \
            or type(event["family"]) is not str \
            or event["family"] != metadata["family"] \
            or type(event["seeds"]) is not list \
            or any(type(seed) is not int for seed in event["seeds"]) \
            or event["seeds"] != metadata["seeds"]:
        raise RunArtifactError("Qualification result status or declaration mismatch")
    benchmark = event["benchmark"]
    counters = {"event_count", "checkpoint_bytes", "peak_event_buffer_bytes"}
    if not isinstance(benchmark, dict) or set(benchmark) != counters | {"simulated_seconds"} \
            or not _finite_number(benchmark["simulated_seconds"]) \
            or any(type(benchmark[name]) is not int or benchmark[name] < 0
                   for name in counters) \
            or not _finite_number(event["compute_seconds"]):
        raise RunArtifactError("Invalid qualification benchmark")
    selection = (event["selected_configuration"], event["selected_window"],
                 event["selected_retention_ms"], event["observed_effect_sign"])
    if event["status"] == "supported":
        if not _numeric_object(selection[0], {"cs_duration_ms", "dan_onset_ms",
                                              "post_pair_gap_ms"}) \
                or not _numeric_object(selection[1], {"start_ms", "end_ms"}) \
                or not _finite_number(selection[2], positive=True) \
                or type(selection[3]) is not int or selection[3] not in (-1, 1):
            raise RunArtifactError("Invalid supported qualification selection")
    elif any(value is not None for value in selection):
        raise RunArtifactError("Unsupported qualification cannot have a selection")


class _Chain:
    def __init__(self, root: str, metadata: dict, checkpoints: dict, run_kind: str):
        self.root = root
        self.run_kind = run_kind
        self.metadata = metadata
        self.checkpoints = checkpoints
        self.seen_checkpoints: set[str] = set()
        self.branches: dict[str, tuple[float, str | None, str | None]] = {}
        self.count = 0
        self.previous = GENESIS
        self.result_seen = False
        self.metadata_digest = _metadata_digest(run_kind, root, metadata)

    def check(self, event: dict) -> None:
        if self.result_seen:
            raise RunArtifactError("Qualification result must be terminal")
        if not isinstance(event, dict) or not isinstance(event.get("type"), str) \
                or not event["type"] or not isinstance(event.get("branch_id"), str) \
                or not event["branch_id"]:
            raise RunArtifactError("Event needs a nonempty type and branch_id")
        if event["type"] == "qualification_result" and self.run_kind != "qualification":
            raise RunArtifactError("Qualification result in a non-qualification run")
        branch = event["branch_id"]
        clock = event.get("sim_ms")
        if isinstance(clock, bool) or not isinstance(clock, (int, float)) or clock < 0:
            raise RunArtifactError("Invalid branch clock")
        try:
            clock_value = float(clock)
        except OverflowError as error:
            raise RunArtifactError("Invalid branch clock") from error
        if not math.isfinite(clock_value):
            raise RunArtifactError("Invalid branch clock")
        if event.get("sequence") != self.count or type(event.get("sequence")) is not int:
            raise RunArtifactError("Event sequence gap or duplicate")
        if event.get("run_metadata_sha256") != self.metadata_digest:
            raise RunArtifactError("Event metadata digest mismatch")
        if event.get("previous_scientific_sha256") != self.previous:
            raise RunArtifactError("Scientific chain break")
        parent = event.get("parent_branch_id")
        parent_digest = event.get("parent_checkpoint_sha256")
        if ("parent_branch_id" in event and (not isinstance(parent, str) or not parent)) \
                or ("parent_checkpoint_sha256" in event and
                    (not isinstance(parent_digest, str) or not DIGEST.fullmatch(parent_digest))):
            raise RunArtifactError("Parent ancestry fields must be nonempty strings when present")
        new_branch = branch not in self.branches
        if new_branch:
            if branch == self.root:
                if parent is not None or parent_digest is not None:
                    raise RunArtifactError("Root branch cannot have a parent")
            else:
                if not isinstance(parent, str) or not isinstance(parent_digest, str):
                    raise RunArtifactError("Restored branch lacks parent ancestry")
                parent_clocks = {
                    data["sim_ms"] for name, data in self.checkpoints.items()
                    if name in self.seen_checkpoints and data["sha256"] == parent_digest
                    and data["origin_branch_id"] == parent
                }
                if parent not in self.branches or parent_clocks != {clock_value}:
                    raise RunArtifactError("Missing, late, wrong or clock-mismatched parent checkpoint")
            branch_state = (clock_value, parent, parent_digest)
        else:
            previous_clock, declared_parent, declared_digest = self.branches[branch]
            if clock_value < previous_clock or (parent is not None and parent != declared_parent) \
                    or (parent_digest is not None and parent_digest != declared_digest):
                raise RunArtifactError("Branch time or ancestry changed")
            branch_state = (clock_value, declared_parent, declared_digest)
        checkpoint_name = None
        if "checkpoint_name" in event:
            name = _safe_name(event["checkpoint_name"])
            data = self.checkpoints.get(name)
            if not data or name in self.seen_checkpoints or data["origin_branch_id"] != branch \
                    or event.get("checkpoint_sha256") != data["sha256"] \
                    or event.get("checkpoint_size") != data["size"] \
                    or ("sim_ms" in data and data["sim_ms"] != clock_value):
                raise RunArtifactError("Checkpoint event does not match ingested file")
            checkpoint_name = name
        if event["type"] == "qualification_result":
            _check_qualification_result(event, self.metadata)
        _walk_bindings(event, self.metadata)
        scientific_digest = sha256(_canonical(_scientific_event(event))).hexdigest()
        if event.get("scientific_sha256") != scientific_digest:
            raise RunArtifactError("Scientific event digest mismatch")
        self.branches[branch] = branch_state
        if checkpoint_name is not None:
            self.checkpoints[checkpoint_name]["sim_ms"] = clock_value
            self.seen_checkpoints.add(checkpoint_name)
        self.previous = scientific_digest
        self.count += 1
        if event["type"] == "qualification_result":
            self.result_seen = True


class RunRecorder:
    """Own one new directory; append is flushed per event, fsync at flush/close."""

    def __init__(self, path: str | Path, *, run_kind: str, metadata: dict,
                 root_branch_id: str):
        if not isinstance(run_kind, str) or run_kind not in {"pilot", "qualification", "confirmation"}:
            raise RunArtifactError("Invalid run kind")
        if not isinstance(root_branch_id, str) or not root_branch_id:
            raise RunArtifactError("Invalid root branch")
        self.metadata = _metadata(metadata)
        self.path = Path(path)
        if any(parent.is_symlink() or parent.is_junction()
               for parent in self.path.absolute().parents):
            raise RunArtifactError("Output ancestor symlink or junction rejected")
        self.run_kind = run_kind
        self.root_branch_id = root_branch_id
        try:
            self.path.mkdir(parents=False, exist_ok=False)
            (self.path / "checkpoints").mkdir()
            self._stream = (self.path / "events.jsonl").open("xb")
        except OSError as error:
            raise RunArtifactError(f"Cannot exclusively create output directory: {error}") from error
        self._run_identity = _directory_identity(self.path)
        self._checkpoint_identity = _directory_identity(self.path / "checkpoints")
        self._checkpoints: dict[str, dict] = {}
        self._chain = _Chain(root_branch_id, self.metadata, self._checkpoints, run_kind)
        self._raw_digest = sha256()
        self._closed = False
        self._failed = False

    def __enter__(self) -> RunRecorder:
        return self

    def __exit__(self, error_type, error, traceback) -> None:
        if error_type is None:
            self.close()
        elif not self._closed:
            self._stream.close()
            self._closed = True

    def _assert_directories(self) -> None:
        if (_directory_identity(self.path) != self._run_identity
                or _directory_identity(self.path / "checkpoints") != self._checkpoint_identity):
            raise RunArtifactError("Run or checkpoint directory identity changed")

    def ingest_checkpoint(self, name: str, source: str | Path, *, origin_branch_id: str) -> str:
        if self._closed or self._failed:
            raise RunArtifactError("Recorder is closed or failed")
        name = _safe_name(name)
        if name in self._checkpoints or not isinstance(origin_branch_id, str) \
                or not origin_branch_id:
            raise RunArtifactError("Duplicate checkpoint or invalid origin")
        target = self.path / "checkpoints" / name
        if target.exists() or target.is_symlink():
            raise RunArtifactError("Checkpoint target already exists")
        temporary = None
        digest = sha256()
        size = 0
        try:
            with Path(source).open("rb") as reader:
                self._assert_directories()
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{name}.",
                                                 suffix=".tmp", delete=False) as writer:
                    temporary = Path(writer.name)
                    while chunk := reader.read(1024 * 1024):
                        writer.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                    writer.flush()
                    os.fsync(writer.fileno())
            self._assert_directories()
            if target.exists() or target.is_symlink():
                raise RunArtifactError("Checkpoint target already exists")
            os.replace(temporary, target)
        except (OSError, RunArtifactError) as error:
            self._failed = True
            if isinstance(error, RunArtifactError):
                raise
            raise RunArtifactError(f"Checkpoint ingest failed: {error}") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self._checkpoints[name] = {"sha256": digest.hexdigest(), "size": size,
                                   "origin_branch_id": origin_branch_id}
        return digest.hexdigest()

    def append(self, event: dict) -> None:
        if self._closed or self._failed:
            raise RunArtifactError("Recorder is closed or failed")
        if not isinstance(event, dict) or OWNED & event.keys():
            raise RunArtifactError("Recorder-owned event field supplied")
        try:
            item = _strict_load(_canonical(event))
            if "checkpoint_name" in item:
                name = _safe_name(item["checkpoint_name"])
                data = self._checkpoints.get(name)
                if data is None:
                    raise RunArtifactError("Checkpoint not ingested")
                if ("checkpoint_sha256" in item and item["checkpoint_sha256"] != data["sha256"]) \
                        or ("checkpoint_size" in item and item["checkpoint_size"] != data["size"]):
                    raise RunArtifactError("Checkpoint event conflicts with ingested file")
                item["checkpoint_sha256"] = data["sha256"]
                item["checkpoint_size"] = data["size"]
            item.update(sequence=self._chain.count,
                        previous_scientific_sha256=self._chain.previous,
                        run_metadata_sha256=self._chain.metadata_digest)
            item["scientific_sha256"] = sha256(_canonical(_scientific_event(item))).hexdigest()
            self._chain.check(item)
            line = _canonical(item) + b"\n"
            self._stream.write(line)
            self._stream.flush()
            self._raw_digest.update(line)
        except (OSError, RunArtifactError) as error:
            if isinstance(error, OSError):
                self._failed = True
                raise RunArtifactError(f"Event append failed: {error}") from error
            raise

    def flush(self) -> None:
        if self._closed:
            raise RunArtifactError("Recorder is closed")
        self._stream.flush()
        os.fsync(self._stream.fileno())

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._failed or (self.run_kind == "qualification" and not self._chain.result_seen) \
                    or not {"brain-before.npz", "brain-after.npz"} <= self._chain.seen_checkpoints \
                    or self._chain.seen_checkpoints != self._checkpoints.keys():
                raise RunArtifactError("Cannot seal incomplete checkpoint set")
            self.flush()
            manifest = {
                "format_version": FORMAT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "schema_sha256": _schema_digest(),
                "run_kind": self.run_kind,
                "root_branch_id": self.root_branch_id,
                "metadata": self.metadata,
                "run_metadata_sha256": self._chain.metadata_digest,
                "event_count": self._chain.count,
                "final_scientific_sha256": self._chain.previous,
                "events_sha256": self._raw_digest.hexdigest(),
                "checkpoints": self._checkpoints,
            }
            self._assert_directories()
            _check_files(self.path, manifest)
            target = self.path / "run.json"
            self._assert_directories()
            with tempfile.NamedTemporaryFile(dir=self.path, prefix=".run.", suffix=".tmp",
                                             delete=False) as writer:
                temporary = Path(writer.name)
                try:
                    writer.write(_canonical(manifest) + b"\n")
                    writer.flush()
                    os.fsync(writer.fileno())
                except Exception:
                    temporary.unlink(missing_ok=True)
                    raise
            self._assert_directories()
            os.replace(temporary, target)
        finally:
            self._stream.close()
            self._closed = True


def _digest_file(path: Path) -> tuple[str, int]:
    digest = sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _read_manifest(path: Path) -> tuple[dict, bytes]:
    if path.is_symlink() or path.is_junction() or not path.is_dir():
        raise RunArtifactError("Run path is not a sealed directory")
    manifest_path = path / "run.json"
    if manifest_path.is_symlink():
        raise RunArtifactError("Manifest symlink rejected")
    try:
        raw = manifest_path.read_bytes()
    except OSError as error:
        raise RunArtifactError(f"Missing run seal: {error}") from error
    item = _strict_load(raw)
    if not isinstance(item, dict) or raw != _canonical(item) + b"\n":
        raise RunArtifactError("Noncanonical run manifest")
    required = {"format_version", "schema_version", "schema_sha256", "run_kind", "root_branch_id", "metadata",
                "run_metadata_sha256", "event_count", "final_scientific_sha256", "events_sha256", "checkpoints"}
    if set(item) != required or item["format_version"] != FORMAT_VERSION \
            or item["schema_version"] != SCHEMA_VERSION \
            or item["schema_sha256"] != _schema_digest() \
            or not isinstance(item["run_kind"], str) \
            or item["run_kind"] not in {"pilot", "qualification", "confirmation"} \
            or not isinstance(item["root_branch_id"], str) or not item["root_branch_id"]:
        raise RunArtifactError("Manifest format or packaged schema mismatch")
    metadata = _metadata(item["metadata"])
    if item["run_metadata_sha256"] != _metadata_digest(item["run_kind"], item["root_branch_id"], metadata):
        raise RunArtifactError("Manifest metadata digest mismatch")
    if type(item["event_count"]) is not int or item["event_count"] < 0 \
            or any(not isinstance(item[name], str) or not DIGEST.fullmatch(item[name])
                   for name in ("final_scientific_sha256", "events_sha256")):
        raise RunArtifactError("Invalid manifest counts or digests")
    checkpoints = item["checkpoints"]
    if not isinstance(checkpoints, dict) or not {"brain-before.npz", "brain-after.npz"} <= checkpoints.keys():
        raise RunArtifactError("Missing reserved checkpoints")
    for name, data in checkpoints.items():
        _safe_name(name)
        if not isinstance(data, dict) or set(data) != {"sha256", "size", "origin_branch_id", "sim_ms"} \
                or not isinstance(data["sha256"], str) or not DIGEST.fullmatch(data["sha256"]) \
                or type(data["size"]) is not int or data["size"] < 0 \
                or not isinstance(data["origin_branch_id"], str) or not data["origin_branch_id"] \
                or isinstance(data["sim_ms"], bool) or not isinstance(data["sim_ms"], (int, float)):
            raise RunArtifactError("Invalid checkpoint declaration")
        try:
            if not math.isfinite(float(data["sim_ms"])) or data["sim_ms"] < 0:
                raise RunArtifactError("Invalid checkpoint clock")
        except OverflowError as error:
            raise RunArtifactError("Invalid checkpoint clock") from error
    return item, raw


def _check_files(path: Path, manifest: dict) -> None:
    directory = path / "checkpoints"
    if directory.is_symlink() or directory.is_junction() or not directory.is_dir():
        raise RunArtifactError("Missing safe checkpoint directory")
    if {entry.name for entry in directory.iterdir()} != manifest["checkpoints"].keys():
        raise RunArtifactError("Missing or extra checkpoint file")
    for name, data in manifest["checkpoints"].items():
        target = directory / name
        if target.is_symlink() or not target.is_file() or _digest_file(target) != (data["sha256"], data["size"]):
            raise RunArtifactError(f"Checkpoint digest mismatch: {name}")


def _scan(path: Path, manifest: dict) -> Iterator[dict]:
    events_path = path / "events.jsonl"
    if events_path.is_symlink() or not events_path.is_file():
        raise RunArtifactError("Missing safe event stream")
    chain = _Chain(manifest["root_branch_id"], manifest["metadata"], manifest["checkpoints"],
                   manifest["run_kind"])
    raw_digest = sha256()
    with events_path.open("rb") as stream:
        for line in stream:
            raw_digest.update(line)
            if not line.endswith(b"\n"):
                raise RunArtifactError("Truncated event line")
            event = _strict_load(line)
            if not isinstance(event, dict) or line != _canonical(event) + b"\n":
                raise RunArtifactError("Noncanonical event bytes")
            chain.check(event)
            yield event
    if chain.count != manifest["event_count"] or chain.previous != manifest["final_scientific_sha256"] \
            or raw_digest.hexdigest() != manifest["events_sha256"] \
            or (manifest["run_kind"] == "qualification" and not chain.result_seen) \
            or chain.seen_checkpoints != manifest["checkpoints"].keys():
        raise RunArtifactError("Event stream count, chain or raw digest mismatch")
    if events_path.is_symlink() or _digest_file(events_path)[0] != manifest["events_sha256"]:
        raise RunArtifactError("Event stream changed during scan")


@dataclass(frozen=True)
class VerifiedRun:
    path: Path
    _manifest_bytes: bytes

    @property
    def manifest(self) -> dict:
        return _strict_load(self._manifest_bytes)

    def iter_events(self) -> Iterator[dict]:
        manifest, raw = _read_manifest(self.path)
        if raw != self._manifest_bytes:
            raise RunArtifactError("Manifest changed since verification")
        _check_files(self.path, manifest)
        yield from _scan(self.path, manifest)
        current, raw = _read_manifest(self.path)
        if raw != self._manifest_bytes:
            raise RunArtifactError("Manifest changed during iteration")
        _check_files(self.path, current)


def verify_run(path: str | Path) -> VerifiedRun:
    """Verify a complete artifact without retaining its events in memory."""
    target = Path(path)
    try:
        manifest, raw = _read_manifest(target)
        _check_files(target, manifest)
        for _ in _scan(target, manifest):
            pass
        if _read_manifest(target)[1] != raw:
            raise RunArtifactError("Manifest changed during verification")
        _check_files(target, manifest)
        return VerifiedRun(target, raw)
    except OSError as error:
        raise RunArtifactError(f"Unreadable run artifact: {error}") from error
