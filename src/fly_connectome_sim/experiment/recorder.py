"""Streaming, integrity-checked run artifacts (hashes are not authentication)."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from importlib.resources import files
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Callable, Iterator


FORMAT_VERSION = "run-artifact/v1"
SCHEMA_VERSION = "run-schema/v1"
ASSAY_RESULT_VERSION = "mbon11-assay-result/v1"
ASSAY_ANALYSIS_VERSION = "mbon11-causal-analysis/v1"
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


def _metadata(metadata: dict, run_kind: str) -> dict:
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
    if "black_input" in result:
        from .replay import _black
        try:
            black = _black(result["black_input"])
            if black["input_sha256"] not in result["input_sha256"]:
                raise ValueError("Black input is not in the declared input set")
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
    if run_kind == "confirmation":
        digest = result.get("frozen_config_sha256")
        contract = result.get("assay_contract")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest) \
                or not isinstance(contract, dict) \
                or contract.get("analysis_version") != ASSAY_ANALYSIS_VERSION:
            raise RunArtifactError("Invalid confirmation config or analysis binding")
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


def _check_assay_result(event: dict, metadata: dict) -> None:
    required = {"result_version", "analysis_version", "frozen_config_sha256",
                "status", "reasons", "report", "report_sha256",
                "evidence_event_count", "evidence_final_scientific_sha256"}
    if not required <= event.keys():
        raise RunArtifactError("Incomplete assay result")
    if event["result_version"] != ASSAY_RESULT_VERSION \
            or event["analysis_version"] != metadata["assay_contract"]["analysis_version"] \
            or event["frozen_config_sha256"] != metadata["frozen_config_sha256"]:
        raise RunArtifactError("Assay result config or analysis binding mismatch")
    status = event["status"]
    reasons = event["reasons"]
    if not isinstance(status, str) or status not in {"supported", "unsupported", "inconclusive"} \
            or not isinstance(reasons, list) \
            or any(not isinstance(reason, str) or not reason for reason in reasons) \
            or reasons != sorted(set(reasons)) \
            or (status == "supported") != (not reasons):
        raise RunArtifactError("Invalid assay status or deterministic reasons")
    report = event["report"]
    if not isinstance(report, dict) or set(report) != {"status", "values", "reasons"} \
            or not isinstance(report["values"], dict) \
            or report["status"] != status or report["reasons"] != reasons:
        raise RunArtifactError("Assay report shape or result mismatch")
    if event["report_sha256"] != sha256(_canonical(report)).hexdigest():
        raise RunArtifactError("Assay report digest mismatch")


class _Chain:
    def __init__(self, root: str, metadata: dict, checkpoints: dict, run_kind: str,
                 prefix_events: Callable[[int], Iterator[dict]] | None = None):
        self.root = root
        self.run_kind = run_kind
        self.metadata = metadata
        self.checkpoints = checkpoints
        self.seen_checkpoints: set[str] = set()
        self.branches: dict[str, tuple] = {}
        self.anchors: dict[str, dict] = {}
        self.anchor_ids: set[str] = set()
        self.prefix_events = prefix_events
        self.projection = None
        self.count = 0
        self.previous = GENESIS
        self.result_seen = False
        self.metadata_digest = _metadata_digest(run_kind, root, metadata)

    def _parent(self, event: dict) -> tuple | None:
        fields = {"parent_branch_id", "parent_checkpoint_sha256", "parent_state_anchor_sha256",
                  "parent_checkpoint_name", "parent_checkpoint_sequence"}
        if not fields & event.keys():
            return None
        # Legacy later events may repeat only part of their established ancestry.
        # New branches still require exactly one complete, prior parent kind.
        declared = self.branches.get(event["branch_id"], (None, None))[1]
        if declared is not None:
            event = dict(event)
            event.setdefault("parent_branch_id", declared[0])
            if not {"parent_checkpoint_sha256", "parent_state_anchor_sha256"} & event.keys():
                if declared[1] == "checkpoint":
                    event["parent_checkpoint_sha256"] = declared[2][2]
                else:
                    event["parent_state_anchor_sha256"] = declared[2]
        parent = event.get("parent_branch_id")
        durable = "parent_checkpoint_sha256" in event
        anchor = "parent_state_anchor_sha256" in event
        if type(parent) is not str or not parent or durable == anchor:
            raise RunArtifactError("Exactly one nonempty parent occurrence is required")
        digest = event["parent_checkpoint_sha256" if durable else "parent_state_anchor_sha256"]
        if type(digest) is not str or not DIGEST.fullmatch(digest):
            raise RunArtifactError("Invalid parent occurrence digest")
        if parent not in self.branches or parent == event["branch_id"]:
            raise RunArtifactError("Missing, late or cyclic parent")
        if anchor:
            if {"parent_checkpoint_name", "parent_checkpoint_sequence"} & event.keys():
                raise RunArtifactError("Anchor parent cannot declare a durable occurrence")
            data = self.anchors.get(digest)
            if data is None or data["origin_branch_id"] != parent:
                raise RunArtifactError("Missing, late or wrong anchor parent")
            return parent, "anchor", digest, data["sim_tick"]
        explicit = {"parent_checkpoint_name", "parent_checkpoint_sequence"} & event.keys()
        if explicit and explicit != {"parent_checkpoint_name", "parent_checkpoint_sequence"}:
            raise RunArtifactError("Incomplete durable occurrence reference")
        if event.get("operation_version") is not None and not explicit:
            raise RunArtifactError("Replay fork requires exact durable name and sequence")
        if explicit:
            _safe_name(event["parent_checkpoint_name"])
            if type(event["parent_checkpoint_sequence"]) is not int \
                    or event["parent_checkpoint_sequence"] < 0:
                raise RunArtifactError("Invalid parent checkpoint sequence")
        candidates = [(name, data) for name, data in self.checkpoints.items()
                      if name in self.seen_checkpoints and data["sha256"] == digest
                      and data["origin_branch_id"] == parent
                      and (not explicit or (name == event["parent_checkpoint_name"]
                           and data["checkpoint_sequence"] == event["parent_checkpoint_sequence"]))]
        if len(candidates) != 1:
            raise RunArtifactError("Missing, late, wrong or ambiguous parent checkpoint")
        name, data = candidates[0]
        return parent, "checkpoint", (name, data["checkpoint_sequence"], digest), data.get("sim_tick")

    def _anchor(self, event: dict) -> dict:
        from .replay import ANCHOR_FIELDS, build_black_retention_recipe, validate_state_anchor

        framing = {"type", "branch_id", "sim_ms", "sequence", "previous_scientific_sha256",
                   "scientific_sha256"}
        try:
            if set(event) != ANCHOR_FIELDS | framing:
                raise ValueError("Invalid state anchor event fields")
            anchor = validate_state_anchor({key: event[key] for key in ANCHOR_FIELDS})
            from .replay import _clock
            _clock(event["sim_ms"], anchor["sim_tick"])
            if event["branch_id"] != anchor["origin_branch_id"] \
                    or anchor["anchor_id"] in self.anchor_ids \
                    or anchor["state_anchor_sha256"] in self.anchors:
                raise ValueError("Wrong anchor origin or duplicate occurrence")
            prefix = {"event_count": self.count, "final_sequence": self.count - 1,
                      "final_scientific_sha256": self.previous}
            black = self.metadata.get("black_input")
            if (self.prefix_events is None and self.projection is None) or black is None:
                raise ValueError("Anchor requires actual prefix and declared black input")
            if self.projection is not None:
                self.projection.check_recipe(anchor["recipe"], prefix)
            else:
                recipe = build_black_retention_recipe(
                    self.prefix_events(self.count), source_occurrence=anchor["source_occurrence"],
                    origin_branch_id=anchor["origin_branch_id"], target_tick=anchor["sim_tick"],
                    engine_identity=self.metadata["engine_identity"],
                    run_metadata_sha256=self.metadata_digest, black_input=black,
                    scientific_prefix=prefix,
                )
                if _canonical(recipe) != _canonical(anchor["recipe"]):
                    raise ValueError("Anchor recipe differs from actual completed prefix")
            return {**anchor, "event_sequence": self.count}
        except ValueError as error:
            raise RunArtifactError(f"Invalid state anchor: {error}") from error

    def check(self, event: dict) -> None:
        if self.result_seen:
            raise RunArtifactError("Result must be terminal")
        if not isinstance(event, dict) or not isinstance(event.get("type"), str) \
                or not event["type"] or not isinstance(event.get("branch_id"), str) \
                or not event["branch_id"]:
            raise RunArtifactError("Event needs a nonempty type and branch_id")
        if event["type"] == "qualification_result" and self.run_kind != "qualification":
            raise RunArtifactError("Qualification result in a non-qualification run")
        if event["type"] == "assay_result" and self.run_kind != "confirmation":
            raise RunArtifactError("Assay result in a non-confirmation run")
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
        wire_clock_value = clock_value
        tick_field = ("sim_tick" if "sim_tick" in event else "end_tick"
                      if event.get("operation_version") == "black-retention-operation/v1"
                      and event["type"] == "neutral_gap_chunk" else None)
        if tick_field is not None:
            from .replay import _clock, _integer
            try:
                tick = _integer(event[tick_field])
                _clock(clock, tick)
                clock_value = tick / 10
            except (KeyError, ValueError) as error:
                raise RunArtifactError("Invalid authoritative event tick/clock") from error
        if event.get("sequence") != self.count or type(event.get("sequence")) is not int:
            raise RunArtifactError("Event sequence gap or duplicate")
        if event.get("run_metadata_sha256") != self.metadata_digest:
            raise RunArtifactError("Event metadata digest mismatch")
        if event.get("previous_scientific_sha256") != self.previous:
            raise RunArtifactError("Scientific chain break")
        ancestry = self._parent(event)
        new_branch = branch not in self.branches
        if new_branch:
            if branch == self.root:
                if ancestry is not None:
                    raise RunArtifactError("Root branch cannot have a parent")
            else:
                if ancestry is None:
                    raise RunArtifactError("Restored branch lacks parent ancestry")
                parent, kind, reference, tick = ancestry
                if tick is not None:
                    from .replay import _clock, _integer
                    try:
                        _clock(event["sim_ms"], tick)
                        if "sim_tick" in event and _integer(event["sim_tick"]) != tick:
                            raise ValueError("Fork integer clock mismatch")
                    except ValueError as error:
                        raise RunArtifactError(str(error)) from error
                elif self.checkpoints[reference[0]]["sim_ms"] != wire_clock_value:
                    raise RunArtifactError("Parent checkpoint clock mismatch")
            branch_state = (clock_value, ancestry)
        else:
            previous_clock, declared_ancestry = self.branches[branch]
            if clock_value < previous_clock or (ancestry is not None and ancestry != declared_ancestry):
                raise RunArtifactError("Branch time or ancestry changed")
            branch_state = (clock_value, declared_ancestry)
        checkpoint_name = None
        if "checkpoint_name" in event:
            name = _safe_name(event["checkpoint_name"])
            data = self.checkpoints.get(name)
            if not data or name in self.seen_checkpoints or data["origin_branch_id"] != branch \
                    or event.get("checkpoint_sha256") != data["sha256"] \
                    or event.get("checkpoint_size") != data["size"] \
                    or ("sim_ms" in data and data["sim_ms"] != wire_clock_value) \
                    or ("checkpoint_sequence" in data and data["checkpoint_sequence"] != self.count) \
                    or ("sim_tick" in data and event.get("sim_tick") != data["sim_tick"]):
                raise RunArtifactError("Checkpoint event does not match ingested file")
            if "sim_tick" in event:
                from .replay import _clock, _integer
                try:
                    _clock(event["sim_ms"], _integer(event["sim_tick"]))
                except ValueError as error:
                    raise RunArtifactError(str(error)) from error
            checkpoint_name = name
        anchor = self._anchor(event) if event["type"] == "state_anchor" else None
        if event["type"] == "qualification_result":
            _check_qualification_result(event, self.metadata)
        elif event["type"] == "assay_result":
            _check_assay_result(event, self.metadata)
            if type(event["evidence_event_count"]) is not int \
                    or event["evidence_event_count"] != self.count \
                    or event["evidence_final_scientific_sha256"] != self.previous:
                raise RunArtifactError("Assay result evidence prefix mismatch")
        _walk_bindings(event, self.metadata)
        scientific_digest = sha256(_canonical(_scientific_event(event))).hexdigest()
        if event.get("scientific_sha256") != scientific_digest:
            raise RunArtifactError("Scientific event digest mismatch")
        if self.projection is not None:
            self.projection.accept(event)
        self.branches[branch] = branch_state
        if checkpoint_name is not None:
            self.checkpoints[checkpoint_name]["sim_ms"] = wire_clock_value
            self.checkpoints[checkpoint_name]["checkpoint_sequence"] = self.count
            if "sim_tick" in event:
                self.checkpoints[checkpoint_name]["sim_tick"] = event["sim_tick"]
            self.seen_checkpoints.add(checkpoint_name)
        if anchor is not None:
            self.anchors[anchor["state_anchor_sha256"]] = anchor
            self.anchor_ids.add(anchor["anchor_id"])
        self.previous = scientific_digest
        self.count += 1
        if event["type"] in {"qualification_result", "assay_result"}:
            self.result_seen = True


class RunRecorder:
    """Own one new directory; append is flushed per event, fsync at flush/close."""

    def __init__(self, path: str | Path, *, run_kind: str, metadata: dict,
                 root_branch_id: str):
        if not isinstance(run_kind, str) or run_kind not in {"pilot", "qualification", "confirmation"}:
            raise RunArtifactError("Invalid run kind")
        if not isinstance(root_branch_id, str) or not root_branch_id:
            raise RunArtifactError("Invalid root branch")
        self.metadata = _metadata(metadata, run_kind)
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
        self._chain = _Chain(root_branch_id, self.metadata, self._checkpoints, run_kind,
                             lambda count: _raw_events(self.path, count=count))
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

    def append_state_anchor(self, anchor: dict) -> None:
        """Adapt a strict envelope without relaxing generic owned-field protection."""
        from .replay import validate_state_anchor

        try:
            data = validate_state_anchor(anchor)
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
        if data.pop("run_metadata_sha256") != self._chain.metadata_digest:
            raise RunArtifactError("Anchor metadata mismatch")
        _check_files(self.path, {"checkpoints": self._checkpoints})
        self.append({**data, "type": "state_anchor", "branch_id": data["origin_branch_id"],
                     "sim_ms": data["sim_tick"] / 10})

    def validate_prefix(self) -> ValidatedPrefix:
        """Validate a quiescent producer's durable bytes; no counters supply proof."""
        self.flush()
        self._assert_directories()
        return validate_prefix(self.path, run_kind=self.run_kind, metadata=self.metadata,
                               root_branch_id=self.root_branch_id, checkpoints=self._checkpoints)

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._failed or (self.run_kind in {"qualification", "confirmation"}
                                and not self._chain.result_seen) \
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
                "state_anchors": self._chain.anchors,
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
                "run_metadata_sha256", "event_count", "final_scientific_sha256", "events_sha256", "checkpoints",
                "state_anchors"}
    if set(item) != required or item["format_version"] != FORMAT_VERSION \
            or item["schema_version"] != SCHEMA_VERSION \
            or item["schema_sha256"] != _schema_digest() \
            or not isinstance(item["run_kind"], str) \
            or item["run_kind"] not in {"pilot", "qualification", "confirmation"} \
            or not isinstance(item["root_branch_id"], str) or not item["root_branch_id"]:
        raise RunArtifactError("Manifest format or packaged schema mismatch")
    metadata = _metadata(item["metadata"], item["run_kind"])
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
        if not isinstance(data, dict) \
                or set(data) not in ({"sha256", "size", "origin_branch_id", "sim_ms", "checkpoint_sequence"},
                                     {"sha256", "size", "origin_branch_id", "sim_ms", "checkpoint_sequence", "sim_tick"}) \
                or not isinstance(data["sha256"], str) or not DIGEST.fullmatch(data["sha256"]) \
                or type(data["size"]) is not int or data["size"] < 0 \
                or not isinstance(data["origin_branch_id"], str) or not data["origin_branch_id"] \
                or type(data["checkpoint_sequence"]) is not int or data["checkpoint_sequence"] < 0 \
                or isinstance(data["sim_ms"], bool) or not isinstance(data["sim_ms"], (int, float)):
            raise RunArtifactError("Invalid checkpoint declaration")
        try:
            if not math.isfinite(float(data["sim_ms"])) or data["sim_ms"] < 0:
                raise RunArtifactError("Invalid checkpoint clock")
        except OverflowError as error:
            raise RunArtifactError("Invalid checkpoint clock") from error
        if "sim_tick" in data:
            from .replay import _clock, _integer
            try:
                _clock(data["sim_ms"], _integer(data["sim_tick"]))
            except ValueError as error:
                raise RunArtifactError(str(error)) from error
    _check_anchor_index(item["state_anchors"])
    return item, raw


def _check_anchor_index(index: object) -> None:
    from .replay import validate_state_anchor

    if type(index) is not dict:
        raise RunArtifactError("Invalid anchor inventory")
    ids = set()
    for digest, entry in index.items():
        if type(entry) is not dict or type(entry.get("event_sequence")) is not int \
                or entry["event_sequence"] < 0:
            raise RunArtifactError("Invalid anchor occurrence sequence")
        try:
            anchor = validate_state_anchor({key: value for key, value in entry.items()
                                            if key != "event_sequence"})
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
        if digest != anchor["state_anchor_sha256"] or anchor["anchor_id"] in ids:
            raise RunArtifactError("Duplicate or mismatched anchor inventory")
        ids.add(anchor["anchor_id"])


def _check_files(path: Path, manifest: dict, *, allow_later: bool = False) -> None:
    directory = path / "checkpoints"
    if directory.is_symlink() or directory.is_junction() or not directory.is_dir():
        raise RunArtifactError("Missing safe checkpoint directory")
    names = {entry.name for entry in directory.iterdir()}
    if (not manifest["checkpoints"].keys() <= names if allow_later
            else names != manifest["checkpoints"].keys()):
        raise RunArtifactError("Missing or extra checkpoint file")
    for name, data in manifest["checkpoints"].items():
        target = directory / name
        if target.is_symlink() or not target.is_file() or _digest_file(target) != (data["sha256"], data["size"]):
            raise RunArtifactError(f"Checkpoint digest mismatch: {name}")


def _raw_events(path: Path, *, count: int | None = None,
                byte_length: int | None = None) -> Iterator[dict]:
    """Raw bounded streaming under a validated context; never recursively scan."""
    events_path = path / "events.jsonl"
    if events_path.is_symlink() or not events_path.is_file():
        raise RunArtifactError("Missing safe event stream")
    with events_path.open("rb") as stream:
        remaining = byte_length
        emitted = 0
        while (remaining is None or remaining > 0) and (count is None or emitted < count):
            line = stream.readline(-1 if remaining is None else remaining)
            if not line:
                if remaining is not None and remaining > 0 or count is not None and emitted < count:
                    raise RunArtifactError("Fixed event prefix truncated")
                break
            if remaining is not None:
                remaining -= len(line)
            if not line.endswith(b"\n"):
                raise RunArtifactError("Truncated event line")
            event = _strict_load(line)
            if not isinstance(event, dict) or line != _canonical(event) + b"\n":
                raise RunArtifactError("Noncanonical event bytes")
            emitted += 1
            yield event


def _digest_boundary(path: Path, byte_length: int) -> str:
    if path.is_symlink() or not path.is_file():
        raise RunArtifactError("Missing safe event stream")
    digest = sha256()
    with path.open("rb") as stream:
        remaining = byte_length
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise RunArtifactError("Fixed event prefix truncated")
            remaining -= len(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def _scan_chain(path: Path, manifest: dict, *, byte_length: int | None = None) -> Iterator[dict]:
    from .replay import _PrefixProjection

    chain = _Chain(manifest["root_branch_id"], manifest["metadata"],
                   _strict_load(_canonical(manifest["checkpoints"])), manifest["run_kind"])
    chain.projection = _PrefixProjection(chain.metadata, chain.metadata_digest)
    raw_digest = sha256()
    for event in _raw_events(path, byte_length=byte_length):
        # _raw_events has already checked exact canonical bytes including LF.
        raw_digest.update(_canonical(event) + b"\n")
        chain.check(event)
        yield event
    if chain.seen_checkpoints != manifest["checkpoints"].keys():
        raise RunArtifactError("Unrepresented checkpoint inventory")
    chain.scanned_raw_sha256 = raw_digest.hexdigest()
    return chain


def _scan(path: Path, manifest: dict) -> Iterator[dict]:
    chain = yield from _scan_chain(path, manifest)
    if chain.count != manifest["event_count"] or chain.previous != manifest["final_scientific_sha256"] \
            or chain.scanned_raw_sha256 != manifest["events_sha256"] \
            or (manifest["run_kind"] in {"qualification", "confirmation"} and not chain.result_seen) \
            or _canonical(chain.checkpoints) != _canonical(manifest["checkpoints"]) \
            or _canonical(chain.anchors) != _canonical(manifest["state_anchors"]):
        raise RunArtifactError("Event stream count, chain or raw digest mismatch")
    if (path / "events.jsonl").is_symlink() \
            or _digest_file(path / "events.jsonl")[0] != manifest["events_sha256"]:
        raise RunArtifactError("Event stream changed during scan")


@dataclass(frozen=True)
class _ReplayAttestation:
    artifact_bytes: bytes
    occurrences: tuple[str, ...]


@dataclass(frozen=True)
class ValidatedPrefix:
    """Fixed durable bytes, not a seal. Later bytes/files are outside its proof.

    Producers must be quiescent while validating/replaying. Rechecks bind every
    represented file and the exact first byte boundary, ignoring later tails.
    All raw integrity bindings remain private and outside scientific projections.
    """
    path: Path
    _context_bytes: bytes
    _byte_length: int
    _raw_sha256: str
    _directory_ids: tuple[tuple[int, int], tuple[int, int]]
    _attestation: _ReplayAttestation | None = field(default=None, init=False, repr=False)

    @property
    def verification_mode(self) -> str:
        if self._attestation is None:
            return "integrity-only"
        ValidatedPrefix.replay_attested_state_anchors.fget(self)
        return "native-replay"

    @property
    def manifest(self) -> dict:
        return _strict_load(self._context_bytes)

    @property
    def scientific_prefix(self) -> dict:
        context = self.manifest
        return {"event_count": context["event_count"], "final_sequence": context["event_count"] - 1,
                "final_scientific_sha256": context["final_scientific_sha256"]}

    def _check_binding(self) -> None:
        context = self.manifest
        if context["schema_sha256"] != _schema_digest():
            raise RunArtifactError("Prefix packaged schema changed")
        if (_directory_identity(self.path), _directory_identity(self.path / "checkpoints")) \
                != self._directory_ids:
            raise RunArtifactError("Prefix directory substituted")
        _check_files(self.path, context, allow_later=True)
        if _digest_boundary(self.path / "events.jsonl", self._byte_length) != self._raw_sha256:
            raise RunArtifactError("Fixed event prefix changed")

    def _attestation_binding(self) -> bytes:
        return self._context_bytes + self._byte_length.to_bytes(8, "little") + bytes.fromhex(self._raw_sha256)

    @property
    def replay_attested_state_anchors(self) -> frozenset[str]:
        if self._attestation is None:
            return frozenset()
        self._check_binding()
        if self._attestation.artifact_bytes != self._attestation_binding():
            raise RunArtifactError("Replay attestation does not bind prefix")
        return frozenset(self._attestation.occurrences)

    def iter_events(self) -> Iterator[dict]:
        self._check_binding()
        context = self.manifest
        chain = yield from _scan_chain(self.path, context, byte_length=self._byte_length)
        if chain.count != context["event_count"] or chain.previous != context["final_scientific_sha256"] \
                or chain.scanned_raw_sha256 != self._raw_sha256 \
                or _canonical(chain.anchors) != _canonical(context["state_anchors"]):
            raise RunArtifactError("Fixed prefix inventory or endpoint mismatch")
        self._check_binding()


def validate_prefix(path: str | Path, *, run_kind: str, metadata: dict,
                    root_branch_id: str, checkpoints: dict) -> ValidatedPrefix:
    """Verify the current durable prefix from disk with explicit producer context."""
    target = Path(path)
    directory_ids = (_directory_identity(target), _directory_identity(target / "checkpoints"))
    if type(run_kind) is not str or run_kind not in {"pilot", "qualification", "confirmation"} \
            or type(root_branch_id) is not str or not root_branch_id:
        raise RunArtifactError("Invalid prefix run context")
    if type(checkpoints) is not dict:
        raise RunArtifactError("Invalid prefix checkpoint inventory")
    context = {"schema_sha256": _schema_digest(), "run_kind": run_kind, "root_branch_id": root_branch_id,
               "metadata": _metadata(metadata, run_kind),
               "checkpoints": _strict_load(_canonical(checkpoints))}
    for name, data in context["checkpoints"].items():
        _safe_name(name)
        required = {"sha256", "size", "origin_branch_id"}
        optional = {"sim_ms", "checkpoint_sequence", "sim_tick"}
        if type(data) is not dict or not required <= data.keys() or set(data) - required - optional \
                or type(data.get("size")) is not int or data["size"] < 0 \
                or type(data.get("sha256")) is not str or not DIGEST.fullmatch(data["sha256"]) \
                or type(data.get("origin_branch_id")) is not str or not data["origin_branch_id"]:
            raise RunArtifactError("Invalid prefix checkpoint inventory")
        from .replay import _clock, _integer
        try:
            for key in ("checkpoint_sequence", "sim_tick"):
                if key in data:
                    _integer(data[key])
            if "sim_ms" in data and not _finite_number(data["sim_ms"]):
                raise ValueError("Invalid inventory clock")
            if "sim_tick" in data and "sim_ms" in data:
                _clock(data["sim_ms"], data["sim_tick"])
        except ValueError as error:
            raise RunArtifactError(str(error)) from error
    _check_files(target, context)
    boundary = (target / "events.jsonl").stat().st_size
    raw_digest = _digest_boundary(target / "events.jsonl", boundary)
    iterator = _scan_chain(target, context, byte_length=boundary)
    while True:
        try:
            next(iterator)
        except StopIteration as result:
            chain = result.value
            break
    context.update(run_metadata_sha256=chain.metadata_digest, event_count=chain.count,
                   final_scientific_sha256=chain.previous, state_anchors=chain.anchors)
    # Reconstruct occurrence inventory from event bytes, never producer counters.
    context["checkpoints"] = chain.checkpoints
    result = ValidatedPrefix(target, _canonical(context), boundary, raw_digest, directory_ids)
    for _ in result.iter_events():
        pass
    return result


@dataclass(frozen=True)
class VerifiedRun:
    path: Path
    _manifest_bytes: bytes
    _attestation: _ReplayAttestation | None = field(default=None, init=False, repr=False)

    @property
    def verification_mode(self) -> str:
        if self._attestation is None:
            return "integrity-only"
        VerifiedRun.replay_attested_state_anchors.fget(self)
        return "native-replay"

    @property
    def replay_attested_state_anchors(self) -> frozenset[str]:
        if self._attestation is None:
            return frozenset()
        manifest, raw = _read_manifest(self.path)
        if raw != self._manifest_bytes or self._attestation.artifact_bytes != raw:
            raise RunArtifactError("Manifest changed since replay verification")
        _check_files(self.path, manifest)
        if (self.path / "events.jsonl").is_symlink() \
                or _digest_file(self.path / "events.jsonl")[0] != manifest["events_sha256"]:
            raise RunArtifactError("Events changed since replay verification")
        return frozenset(self._attestation.occurrences)

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


def _replay_verified(value: VerifiedRun | ValidatedPrefix, *, engine_factory: Callable) -> None:
    from .replay import _replay_black_retention

    engine = None
    anchors = value.manifest["state_anchors"]
    try:
        for entry in anchors.values():
            anchor = {key: item for key, item in entry.items() if key != "event_sequence"}
            # Fully restore each occurrence, even when state content digests agree.
            engine = _replay_black_retention(anchor,
                source_path=value.path / "checkpoints" / anchor["source_occurrence"]["checkpoint_name"],
                engine_factory=engine_factory, engine=engine)
        for _ in value.iter_events():
            pass
    except (ValueError, OSError) as error:
        raise RunArtifactError(f"Actual anchor replay verification failed: {error}") from error
    binding = value._manifest_bytes if isinstance(value, VerifiedRun) else value._attestation_binding()
    object.__setattr__(value, "_attestation", _ReplayAttestation(binding, tuple(sorted(anchors))))


def verify_replay_run(path: str | Path, *, engine_factory: Callable) -> VerifiedRun:
    """Ordinary whole-artifact validation, actual isolated replay, final recheck."""
    value = verify_run(path)
    _replay_verified(value, engine_factory=engine_factory)
    return value


def verify_replay_prefix(prefix: ValidatedPrefix, *, engine_factory: Callable) -> ValidatedPrefix:
    """Validate/replay a fixed prefix and return a separately attested frozen value."""
    if type(prefix) is not ValidatedPrefix:
        raise RunArtifactError("Replay requires a validated fixed prefix")
    for _ in prefix.iter_events():
        pass
    value = ValidatedPrefix(prefix.path, prefix._context_bytes, prefix._byte_length,
                            prefix._raw_sha256, prefix._directory_ids)
    _replay_verified(value, engine_factory=engine_factory)
    return value
