"""Pure bounded occurrence recipes and isolated execution, without attestation.

The caller supplies a completed scientific prefix. Artifact/file inventory
authentication and immutable verifier-produced attestations remain recorder-owned.
All retained JSON values are strict, scientific defensive copies.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re
import struct
from typing import Callable, Iterable

import numpy as np

from ..engine import FlyEngine, _rgb_input_sha256
from ..neural.checkpoint import _canonical_json


RECIPE_VERSION = "black-retention/v1"
ANCHOR_VERSION = "state-anchor/v1"
OPERATION_VERSION = "black-retention-operation/v1"
RECIPE_DOMAIN = b"fly-connectome-black-retention/v1\0"
ANCHOR_DOMAIN = b"fly-connectome-state-anchor/v1\0"
# Existing native queue uses an 18-tick delay at the audited 0.1-ms dt.
MAX_TICK = int(np.iinfo(np.int64).max) - 18
DIGEST = re.compile(r"^[0-9a-f]{64}$")
FRAMING = {"sequence", "previous_scientific_sha256", "scientific_sha256",
           "run_metadata_sha256", "branch_id", "sim_ms", "operation_version"}
SOURCE_FIELDS = {"checkpoint_name", "checkpoint_sha256", "origin_branch_id",
                 "checkpoint_sequence", "sim_tick"}
PREFIX_FIELDS = {"event_count", "final_sequence", "final_scientific_sha256"}
BLACK_FIELDS = {"generator", "input_shape", "input_dtype", "input_sha256"}
CALL_FIELDS = {"start_tick", "end_tick", "duration_ticks", "duration_ms", "sim_ms",
               "stimulation", "learning", "current_mv", "pathway_detail",
               "qualification_detail"}
FORK_FIELDS = {"type", "sim_tick", "parent_branch_id", "parent_checkpoint_name",
               "parent_checkpoint_sequence", "parent_checkpoint_sha256"}
THAW_FIELDS = {"type", "sim_tick", "before_weights_frozen", "after_weights_frozen"}
REFERENCE_FIELDS = {"type", "event_sequence", "event_scientific_sha256"}
RECIPE_FIELDS = {"recipe_version", "source_occurrence", "origin_branch_id", "target_tick",
                 "engine_identity", "run_metadata_sha256", "black_input",
                 "scientific_prefix", "operations", "replay_recipe_sha256"}
ANCHOR_FIELDS = {"anchor_version", "anchor_id", "state_anchor_sha256", "origin_branch_id",
                 "sim_tick", "complete_state_sha256", "durable_ancestor_checkpoint_sha256",
                 "replay_recipe_sha256", "source_identity_sha256", "run_metadata_sha256",
                 "source_occurrence", "scientific_prefix", "recipe"}
RAW_PREFIX_FIELDS = {"raw_prefix_sha256", "raw_prefix_length", "raw_prefix_bytes",
                     "raw_prefix_size", "raw_prefix_byte_length", "raw_prefix_hash",
                     "events_sha256", "events_bytes", "events_byte_length"}


def _domain_sha256(domain: bytes, value: dict) -> str:
    encoded = _canonical_json(value)
    return sha256(domain + struct.pack("<Q", len(encoded)) + encoded).hexdigest()


def _copy(value: object, *, scientific: bool = False) -> object:
    """Strict copies; only event projection applies existing timing exclusions."""
    strict = json.loads(_canonical_json(value))
    _reject_raw_prefix(strict)
    if scientific:
        from .recorder import _scientific

        return _scientific(strict)
    return strict


def _reject_raw_prefix(value: object) -> None:
    if type(value) is dict:
        if any(key in RAW_PREFIX_FIELDS or key.startswith("raw_prefix_") for key in value):
            raise ValueError("Raw prefix integrity fields cannot enter scientific replay data")
        for item in value.values():
            _reject_raw_prefix(item)
    elif type(value) is list:
        for item in value:
            _reject_raw_prefix(item)


def _fields(value: object, fields: set[str], name: str) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(f"Invalid {name} fields")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or not DIGEST.fullmatch(value):
        raise ValueError("Invalid SHA256")
    return value


def _identifier(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("Expected a nonempty identifier")
    return value


def _integer(value: object, *, maximum: int = MAX_TICK) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("Expected an exact nonnegative native integer")
    return value


def _number(value: object) -> float | int:
    if type(value) not in (float, int):
        raise ValueError("Expected a finite number")
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Expected a finite number")
    return value


def _clock(value: object, tick: int) -> None:
    if _number(value) not in (tick * 0.1, tick / 10):
        raise ValueError("Replay wire clock does not match its exact integer tick")


def _live_clock(value: object, tick: int) -> None:
    if _number(value) != tick * 0.1:
        raise ValueError("Live replay clock does not equal cursor * dt")


def _source(value: object) -> dict:
    from .recorder import _safe_name

    data = _fields(value, SOURCE_FIELDS, "durable source occurrence")
    _safe_name(data["checkpoint_name"])
    _digest(data["checkpoint_sha256"])
    _identifier(data["origin_branch_id"])
    _integer(data["checkpoint_sequence"])
    _integer(data["sim_tick"])
    return data


def _prefix(value: object) -> dict:
    data = _fields(value, PREFIX_FIELDS, "scientific prefix")
    count = _integer(data["event_count"])
    sequence = _integer(data["final_sequence"])
    if count < 1 or sequence != count - 1:
        raise ValueError("Scientific prefix count/endpoint mismatch")
    _digest(data["final_scientific_sha256"])
    return data


def _identity(value: object) -> dict:
    data = _fields(value, {"version", "model_provenance", "neural_groups", "sha256"},
                   "full engine identity")
    if data["version"] != "fly-engine/v1":
        raise ValueError("Unsupported engine identity")
    provenance = data["model_provenance"]
    _fields(provenance, {"model", "model_fingerprint", "build", "eta", "parameters",
                         "graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256",
                         "plastic_edges_sha256", "configuration_sha256"}, "model provenance")
    _identifier(provenance["model"])
    _number(provenance["eta"])
    for name in ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "plastic_edges_sha256"):
        _digest(provenance[name])
    if type(provenance["configuration_sha256"]) is not dict:
        raise ValueError("Invalid configuration signature")
    fingerprint = _fields(provenance["model_fingerprint"],
                          {"version", "sources_sha256", "sha256"}, "model fingerprint")
    _identifier(fingerprint["version"])
    _digest(fingerprint["sha256"])
    if type(fingerprint["sources_sha256"]) is not dict or not fingerprint["sources_sha256"]:
        raise ValueError("Incomplete model source fingerprints")
    for item in fingerprint["sources_sha256"].values():
        _digest(item)
    build = _fields(provenance["build"],
                    {"model", "source_sha256", "compiler", "flags", "library", "binary_sha256"},
                    "native build identity")
    for name in ("model", "compiler", "library"):
        _identifier(build[name])
    for name in ("source_sha256", "binary_sha256"):
        _digest(build[name])
    if type(build["flags"]) is not list or any(type(flag) is not str for flag in build["flags"]):
        raise ValueError("Invalid native build flags")
    groups = _fields(data["neural_groups"],
                     {"pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right"},
                     "neural groups")
    for indices in groups.values():
        if type(indices) is not list or not indices:
            raise ValueError("Empty or invalid neural group")
        for index in indices:
            _integer(index)
    if type(provenance.get("parameters")) is not dict \
            or type(provenance["parameters"].get("neural_dt_ms")) is not float \
            or provenance["parameters"]["neural_dt_ms"] != 0.1:
        raise ValueError("Replay requires engine dt exactly 0.1")
    _digest(data["sha256"])
    payload = {key: item for key, item in data.items() if key != "sha256"}
    # FlyEngine uses its own canonical encoding (ASCII escaping by default).
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode()
    if sha256(encoded).hexdigest() != data["sha256"]:
        raise ValueError("Full engine identity digest mismatch")
    return data


def _black(value: object) -> dict:
    data = _fields(value, BLACK_FIELDS, "black input declaration")
    shape = data["input_shape"]
    if (type(shape) is not list or len(shape) != 3
            or any(type(size) is not int for size in shape)
            or not 1 <= shape[0] <= 32 or not 1 <= shape[1] <= 32 or shape[2] != 3):
        raise ValueError("Unsupported bounded RGB shape")
    if data["generator"] != "black-rgb/v1" or data["input_dtype"] != "uint8":
        raise ValueError("Unsupported black generator or dtype")
    _digest(data["input_sha256"])
    # Same rgb-input/v1 definition, without allocating an ndarray in validators.
    header = {"version": "rgb-input/v1", "dtype": "uint8", "rank": 3, "shape": shape}
    encoded = json.dumps(header, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode()
    expected = sha256(encoded + b"\n" + bytes(math.prod(shape))).hexdigest()
    if data["input_sha256"] != expected:
        raise ValueError("Black input digest does not match declared shape")
    return data


def _call(data: dict, cursor: int) -> int:
    start = _integer(data["start_tick"])
    end = _integer(data["end_tick"])
    duration = _integer(data["duration_ticks"], maximum=5000)
    if duration < 1 or start != cursor or end != start + duration:
        raise ValueError("Missing, overlapping or reordered replay call")
    _clock(data["sim_ms"], end)
    _clock(data["duration_ms"], duration)
    if data["stimulation"] is not None or data["learning"] is not False:
        raise ValueError("Black retention must be unstimulated with learning=False")
    _number(data["current_mv"])
    for name in ("pathway_detail", "qualification_detail"):
        if type(data[name]) is not bool:
            raise ValueError("Replay detail flags must be exact booleans")
    return end


def _thaw(data: dict, cursor: int) -> None:
    if _integer(data["sim_tick"]) != cursor:
        raise ValueError("Thaw clock mismatch")
    if type(data["before_weights_frozen"]) is not bool \
            or data["after_weights_frozen"] is not False:
        raise ValueError("Invalid explicit thaw declaration")


def _telemetry_bindings(value: object, event: dict, identity: dict, black: dict) -> None:
    """Preserve all evidence via its event digest and reject contradictory bindings."""
    if type(value) is dict:
        expected = {"engine_identity": identity, "input_shape": black["input_shape"],
                    "input_dtype": black["input_dtype"], "input_sha256": black["input_sha256"],
                    "sim_ms": round(event["end_tick"] * 0.1, 3),
                    "interval_ms": event["duration_ms"],
                    "start_tick": event["start_tick"], "end_tick": event["end_tick"],
                    "sim_tick": event["end_tick"], "duration_ticks": event["duration_ticks"],
                    "duration_ms": event["duration_ms"],
                    "end_ms": round(event["end_tick"] * 0.1, 3),
                    "learning": False, "stimulation": None}
        for name, item in expected.items():
            if name in value and _canonical_json(value[name]) != _canonical_json(item):
                raise ValueError(f"Contradictory scientific telemetry {name}")
        for name, item in value.items():
            if name == "bins":
                if type(item) is not list or len(item) != (event["duration_ticks"] + 99) // 100:
                    raise ValueError("Scientific bin count differs from actual call bins")
                cursor = event["start_tick"]
                for bin_data in item:
                    if type(bin_data) is not dict:
                        raise ValueError("Invalid scientific observation bin")
                    ticks = min(100, event["end_tick"] - cursor)
                    bin_event = {**event, "start_tick": cursor, "end_tick": cursor + ticks,
                                 "duration_ticks": ticks, "duration_ms": ticks * 0.1}
                    _telemetry_bindings(bin_data, bin_event, identity, black)
                    cursor += ticks
            else:
                _telemetry_bindings(item, event, identity, black)
    elif type(value) is list:
        for item in value:
            _telemetry_bindings(item, event, identity, black)


def _check_source_event(event: dict, source: dict) -> None:
    """Require an actual typed earlier checkpoint, not an inventory declaration."""
    if (event.get("type") != "checkpoint"
            or event.get("branch_id") != source["origin_branch_id"]
            or event.get("checkpoint_name") != source["checkpoint_name"]
            or event.get("checkpoint_sha256") != source["checkpoint_sha256"]
            or _integer(event.get("sim_tick")) != source["sim_tick"]):
        raise ValueError("Exact durable checkpoint occurrence mismatch")
    _clock(event.get("sim_ms"), source["sim_tick"])


def _project_operation(event: dict, source: dict, identity: dict, black: dict) -> dict:
    """Shared exact scientific event projection; no prefix authenticity claim."""
    if event.get("operation_version") != OPERATION_VERSION:
        raise ValueError("Late source or unsupported replay operation version")
    kind = event.get("type")
    reference = {"type": kind, "event_sequence": event["sequence"],
                 "event_scientific_sha256": event["scientific_sha256"]}
    if kind == "fork":
        _fields(event, FRAMING | FORK_FIELDS, "direct replay fork event")
        if (event["parent_branch_id"] != source["origin_branch_id"]
                or event["parent_checkpoint_name"] != source["checkpoint_name"]
                or _integer(event["parent_checkpoint_sequence"]) != source["checkpoint_sequence"]
                or event["parent_checkpoint_sha256"] != source["checkpoint_sha256"]
                or _integer(event["sim_tick"]) != source["sim_tick"]):
            raise ValueError("Direct fork occurrence mismatch")
        _clock(event["sim_ms"], source["sim_tick"])
        return {**reference, "sim_tick": event["sim_tick"]}
    elif kind == "replay_thaw":
        _fields(event, FRAMING | THAW_FIELDS, "explicit thaw event")
        _clock(event["sim_ms"], _integer(event["sim_tick"]))
        return {**reference, **{key: event[key] for key in THAW_FIELDS - {"type"}}}
    elif kind == "neutral_gap_chunk":
        fields = FRAMING | {"type"} | BLACK_FIELDS | CALL_FIELDS
        _fields(event, fields | ({"telemetry"} if "telemetry" in event else set()),
                "black replay call event")
        _call(event, _integer(event["start_tick"]))
        if _canonical_json(_black({key: event[key] for key in BLACK_FIELDS})) != _canonical_json(black):
            raise ValueError("Replay call input is not the context-declared black input")
        if "telemetry" in event:
            if type(event["telemetry"]) is not dict:
                raise ValueError("Replay telemetry must be an object")
            _telemetry_bindings(event["telemetry"], event, identity, black)
        return {**reference, **{key: event[key] for key in CALL_FIELDS}}
    else:
        raise ValueError("Unknown branch-local event in bounded replay interval")


def _recipe_headers(source: dict, branch: str, target: int, identity: dict,
                    metadata: str, black: dict, prefix: dict) -> dict:
    return {"recipe_version": RECIPE_VERSION, "source_occurrence": source,
            "origin_branch_id": branch, "target_tick": target,
            "engine_identity": identity, "run_metadata_sha256": metadata,
            "black_input": black, "scientific_prefix": prefix}


def build_black_retention_recipe(
    events: Iterable[dict], *, source_occurrence: dict, origin_branch_id: str,
    target_tick: int, engine_identity: dict, run_metadata_sha256: str,
    black_input: dict, scientific_prefix: dict,
) -> dict:
    """Project every target-branch event in one completed ordered scientific prefix."""
    from .recorder import _scientific_event

    source = _source(_copy(source_occurrence))
    branch = _identifier(origin_branch_id)
    target = _integer(target_tick)
    identity = _identity(_copy(engine_identity))
    metadata = _digest(run_metadata_sha256)
    black = _black(_copy(black_input))
    prefix = _prefix(_copy(scientific_prefix))
    if branch == source["origin_branch_id"] or target < source["sim_tick"]:
        raise ValueError("Replay target must be a distinct direct fork at/after source")
    operations = []
    source_seen = False
    previous = "0" * 64
    count = 0
    for raw in events:
        event = _copy(raw, scientific=True)
        if type(event) is not dict:
            raise ValueError("Scientific prefix events must be objects")
        if _integer(event.get("sequence")) != count:
            raise ValueError("Scientific prefix sequence gap or reordering")
        if event.get("previous_scientific_sha256") != previous \
                or event.get("run_metadata_sha256") != metadata:
            raise ValueError("Scientific prefix chain or metadata mismatch")
        expected = sha256(_canonical_json(_scientific_event(event))).hexdigest()
        if _digest(event.get("scientific_sha256")) != expected:
            raise ValueError("Scientific event digest mismatch")
        previous = expected
        count += 1
        if event["sequence"] == source["checkpoint_sequence"]:
            _check_source_event(event, source)
            source_seen = True
        if event.get("branch_id") != branch:
            continue
        if not source_seen or event.get("operation_version") != OPERATION_VERSION:
            raise ValueError("Late source or unsupported replay operation version")
        operations.append(_project_operation(event, source, identity, black))
    if count != prefix["event_count"] or previous != prefix["final_scientific_sha256"]:
        raise ValueError("Completed prefix count or scientific endpoint mismatch")
    if not source_seen:
        raise ValueError("Durable source occurrence absent from prefix")
    data = {**_recipe_headers(source, branch, target, identity, metadata, black, prefix),
            "operations": operations}
    data["replay_recipe_sha256"] = _domain_sha256(RECIPE_DOMAIN, data)
    return validate_black_retention_recipe(data)


class _OperationGrammar:
    """Scalar grammar state, shared by recipe validation and scanner projection."""

    def __init__(self, source: dict):
        self.cursor = source["sim_tick"]
        self.previous_sequence = source["checkpoint_sequence"]
        self.count = 0
        self.thaw_seen = False

    def accept(self, operation: dict, final_sequence: int) -> None:
        if type(operation) is not dict:
            raise ValueError("Invalid replay operation")
        sequence = _integer(operation.get("event_sequence"))
        if not self.previous_sequence < sequence <= final_sequence:
            raise ValueError("Operation sequence order or prefix range mismatch")
        _digest(operation.get("event_scientific_sha256"))
        kind = operation.get("type")
        cursor = self.cursor
        thaw_seen = self.thaw_seen
        if self.count == 0:
            _fields(operation, REFERENCE_FIELDS | {"sim_tick"}, "fork operation")
            if kind != "fork" or _integer(operation["sim_tick"]) != cursor:
                raise ValueError("Replay must start with its direct source fork")
        elif kind == "replay_thaw":
            _fields(operation, REFERENCE_FIELDS | (THAW_FIELDS - {"type"}), "thaw operation")
            if thaw_seen or self.count != 1:
                raise ValueError("Duplicate or reordered replay thaw")
            _thaw(operation, cursor)
            thaw_seen = True
        elif kind == "neutral_gap_chunk":
            _fields(operation, REFERENCE_FIELDS | CALL_FIELDS, "black call operation")
            cursor = _call(operation, cursor)
        else:
            raise ValueError("Unsupported replay operation")
        self.cursor = cursor
        self.thaw_seen = thaw_seen
        self.previous_sequence = sequence
        self.count += 1

    def finish(self, target: int) -> None:
        if not self.count or self.cursor != target:
            raise ValueError("Replay operations do not reach exact target tick")


class _BranchProjection:
    """Canonical operation-array binding with no retained operation history."""

    def __init__(self, source: dict):
        self.source = dict(source)
        self.grammar = _OperationGrammar(source)
        self.operations_sha256 = sha256(b"[")

    def accept(self, event: dict, identity: dict, black: dict) -> None:
        operation = _project_operation(event, self.source, identity, black)
        encoded = _canonical_json(operation)
        self.grammar.accept(operation, event["sequence"])
        if self.grammar.count > 1:
            self.operations_sha256.update(b",")
        self.operations_sha256.update(encoded)

    def matches_operations(self, operations: list) -> bool:
        if self.grammar.count != len(operations):
            return False
        expected = self.operations_sha256.copy()
        expected.update(b"]")
        actual = sha256(b"[")
        for index, operation in enumerate(operations):
            if index:
                actual.update(b",")
            actual.update(_canonical_json(operation))
        actual.update(b"]")
        return expected.digest() == actual.digest()


class _PrefixProjection:
    """One scan's accepted events only; replay-only failures stay deferred.

    None is a permanent branch tombstone. The hash binds the full canonical
    array under the same SHA256 collision-resistance assumption as the chain;
    all source, header and operation semantic checks remain independent.
    """

    def __init__(self, metadata: dict, metadata_digest: str):
        # Snapshot without replay validation: legacy/no-anchor identities remain
        # readable. Each context is validated lazily once, shared by candidates.
        self.context = json.loads(_canonical_json(metadata))
        self.metadata_digest = metadata_digest
        self.context_checked = False
        self.identity = None
        self.black = None
        self.raw_prefix_invalid = False
        self.sources: dict[str, dict] = {}
        self.branches: dict[str, _BranchProjection | None] = {}

    def _check_context(self) -> None:
        if not self.context_checked:
            self.context_checked = True
            try:
                identity = _identity(_copy(self.context["engine_identity"]))
                black = _black(_copy(self.context.get("black_input")))
            except ValueError:
                pass
            else:
                self.identity, self.black = identity, black
            self.context = None
        if self.identity is None or self.black is None:
            raise ValueError("Anchor requires replay identity and declared black input")

    def accept(self, raw: dict) -> None:
        """Called only after every ordinary chain check, before yielding aliases."""
        try:
            _reject_raw_prefix(raw)
        except ValueError:
            self.raw_prefix_invalid = True
        branch = raw["branch_id"]
        if branch not in self.branches:
            self.branches[branch] = None
            if raw.get("type") == "fork":
                source = self.sources.get(raw.get("parent_checkpoint_name"))
                if source is not None and branch != source["origin_branch_id"]:
                    self.branches[branch] = _BranchProjection(source)
        candidate = self.branches[branch]
        if raw["type"] == "state_anchor":
            # Its validation used strictly earlier events. Once accepted, this
            # unsupported branch-local event permanently releases the candidate.
            self.branches[branch] = None
            candidate = None
        if candidate is not None:
            try:
                self._check_context()
                from .recorder import _scientific

                candidate.accept(_scientific(raw), self.identity, self.black)
            except ValueError:
                self.branches[branch] = None
        if raw.get("type") == "checkpoint" and "checkpoint_name" in raw:
            try:
                source = _source({"checkpoint_name": raw["checkpoint_name"],
                    "checkpoint_sha256": raw["checkpoint_sha256"], "origin_branch_id": branch,
                    "checkpoint_sequence": raw["sequence"], "sim_tick": raw.get("sim_tick")})
                _check_source_event(raw, source)
            except ValueError:
                pass
            else:
                self.sources[source["checkpoint_name"]] = source

    def check_recipe(self, recipe: dict, prefix: dict) -> None:
        """Compare an already fully validated recipe against strictly prior events."""
        if self.raw_prefix_invalid:
            raise ValueError("Raw prefix integrity fields cannot enter scientific replay data")
        self._check_context()
        branch = recipe["origin_branch_id"]
        candidate = self.branches.get(branch)
        if candidate is None:
            raise ValueError("Unsupported earlier branch-local replay history")
        candidate.grammar.finish(recipe["target_tick"])
        expected = _recipe_headers(candidate.source, branch, candidate.grammar.cursor,
                                   self.identity, self.metadata_digest, self.black, prefix)
        actual = {key: value for key, value in recipe.items()
                  if key not in {"operations", "replay_recipe_sha256"}}
        if _canonical_json(expected) != _canonical_json(actual) \
                or not candidate.matches_operations(recipe["operations"]):
            raise ValueError("Anchor recipe differs from actual completed prefix")


def validate_black_retention_recipe(recipe: dict) -> dict:
    """Return a strict independent canonical copy; no artifact authenticity claim."""
    data = _fields(_copy(recipe), RECIPE_FIELDS, "black retention recipe")
    if data["recipe_version"] != RECIPE_VERSION:
        raise ValueError("Unsupported replay recipe")
    source = _source(data["source_occurrence"])
    prefix = _prefix(data["scientific_prefix"])
    _identity(data["engine_identity"])
    _black(data["black_input"])
    _digest(data["run_metadata_sha256"])
    if _identifier(data["origin_branch_id"]) == source["origin_branch_id"]:
        raise ValueError("Replay origin must be a distinct direct fork")
    target = _integer(data["target_tick"])
    operations = data["operations"]
    if type(operations) is not list or not operations:
        raise ValueError("Replay recipe must include its direct fork")
    grammar = _OperationGrammar(source)
    for operation in operations:
        grammar.accept(operation, prefix["final_sequence"])
    grammar.finish(target)
    payload = {key: item for key, item in data.items() if key != "replay_recipe_sha256"}
    if _digest(data["replay_recipe_sha256"]) != _domain_sha256(RECIPE_DOMAIN, payload):
        raise ValueError("Replay recipe digest mismatch")
    return data


def build_state_anchor(*, anchor_id: str, complete_state_sha256: str, recipe: dict) -> dict:
    """Bind state content to an exact occurrence route and executable recipe."""
    recipe = validate_black_retention_recipe(recipe)
    data = {"anchor_version": ANCHOR_VERSION, "anchor_id": _identifier(anchor_id),
            "origin_branch_id": recipe["origin_branch_id"], "sim_tick": recipe["target_tick"],
            "complete_state_sha256": _digest(complete_state_sha256),
            "durable_ancestor_checkpoint_sha256": recipe["source_occurrence"]["checkpoint_sha256"],
            "replay_recipe_sha256": recipe["replay_recipe_sha256"],
            "source_identity_sha256": recipe["engine_identity"]["sha256"],
            "run_metadata_sha256": recipe["run_metadata_sha256"],
            "source_occurrence": recipe["source_occurrence"],
            "scientific_prefix": recipe["scientific_prefix"], "recipe": recipe}
    data["state_anchor_sha256"] = _domain_sha256(ANCHOR_DOMAIN, data)
    return _copy(data)


def validate_state_anchor(anchor: dict) -> dict:
    """Recompute occurrence bindings; this never returns replay attestation."""
    data = _fields(_copy(anchor), ANCHOR_FIELDS, "state anchor")
    _integer(data["sim_tick"])
    for name in ("state_anchor_sha256", "complete_state_sha256", "durable_ancestor_checkpoint_sha256",
                 "replay_recipe_sha256", "source_identity_sha256", "run_metadata_sha256"):
        _digest(data[name])
    expected = build_state_anchor(anchor_id=data["anchor_id"],
                                  complete_state_sha256=data["complete_state_sha256"],
                                  recipe=data["recipe"])
    if _canonical_json(data) != _canonical_json(expected):
        raise ValueError("State anchor occurrence envelope mismatch")
    return data


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def replay_black_retention(
    anchor: dict, *, source_path: str | Path, engine_factory: Callable[[], FlyEngine],
) -> FlyEngine:
    """Reconstruct one anchor in one caller-provided isolated compatible engine.

    source_path is authenticated by the artifact caller; basename and actual
    bytes are rebound here. The factory must produce a fresh engine. No endpoint
    checkpoint is written, no producer wrapper is called, and no proof is issued.
    """
    return _replay_black_retention(anchor, source_path=source_path, engine_factory=engine_factory)


def _replay_black_retention(
    anchor: dict, *, source_path: str | Path, engine_factory: Callable[[], FlyEngine],
    engine: FlyEngine | None = None,
) -> FlyEngine:
    """Shared executor; only the artifact verifier reuses its own isolated engine."""
    data = validate_state_anchor(anchor)
    recipe = data["recipe"]
    source = recipe["source_occurrence"]
    path = Path(source_path)
    if path.name != source["checkpoint_name"] or path.is_symlink() or not path.is_file():
        raise ValueError("Replay source path does not bind the exact durable basename")
    initial_stat = path.stat()
    expected_file = source["checkpoint_sha256"]
    if _file_sha256(path) != expected_file:
        raise ValueError("Durable source file digest mismatch")
    if engine is None:
        engine = engine_factory()
    if not isinstance(engine, FlyEngine):
        raise ValueError("Replay factory must return a compatible isolated FlyEngine")
    identity = _canonical_json(recipe["engine_identity"])
    if _canonical_json(engine.identity()) != identity or type(engine.brain.dt) is not float \
            or engine.brain.dt != 0.1:
        raise ValueError("Isolated replay engine identity/dt mismatch")
    engine.brain.restore(path)
    if type(engine.brain.cursor) is not int or engine.brain.cursor != source["sim_tick"]:
        raise ValueError("Actual durable source cursor differs from occurrence")
    _live_clock(engine.brain.sim_ms, source["sim_tick"])
    delay = len(engine.brain.queue_count) - 1
    if recipe["target_tick"] > int(np.iinfo(np.int64).max) - delay:
        raise ValueError("Replay target leaves no native queue-delay room")
    if _canonical_json(engine.identity()) != identity:
        raise ValueError("Restored engine identity mismatch")
    black = recipe["black_input"]
    frame = np.zeros(tuple(black["input_shape"]), dtype=np.uint8)
    frame.flags.writeable = False
    if _rgb_input_sha256(frame) != black["input_sha256"]:
        raise ValueError("Regenerated black frame digest mismatch")
    operations = recipe["operations"]
    thaw = operations[1] if len(operations) > 1 and operations[1]["type"] == "replay_thaw" else None
    if thaw is None and engine.brain.weights_frozen is not False:
        raise ValueError("Frozen durable source requires an explicit thaw")
    for operation in operations[1:]:
        if _canonical_json(engine.identity()) != identity or _rgb_input_sha256(frame) != black["input_sha256"]:
            raise ValueError("Replay engine or black input changed before an operation")
        if operation["type"] == "replay_thaw":
            if engine.brain.weights_frozen is not operation["before_weights_frozen"] \
                    or engine.brain.cursor != operation["sim_tick"]:
                raise ValueError("Actual source freeze/clock precondition differs from thaw")
            engine.brain.weights_frozen = False
        else:
            if type(engine.brain.cursor) is not int or engine.brain.cursor != operation["start_tick"]:
                raise ValueError("Actual replay call start cursor mismatch")
            _live_clock(engine.brain.sim_ms, operation["start_tick"])
            engine.observe(frame, operation["duration_ms"], stimulation=operation["stimulation"],
                           current_mv=operation["current_mv"], learning=operation["learning"],
                           pathway_detail=operation["pathway_detail"],
                           qualification_detail=operation["qualification_detail"])
            if type(engine.brain.cursor) is not int or engine.brain.cursor != operation["end_tick"]:
                raise ValueError("Actual replay call end cursor mismatch")
            _live_clock(engine.brain.sim_ms, operation["end_tick"])
    if _canonical_json(engine.identity()) != identity or engine.brain.cursor != data["sim_tick"] \
            or engine.brain.checkpoint_state_sha256() != data["complete_state_sha256"]:
        raise ValueError("Actual replay target state/identity mismatch")
    final_stat = path.stat()
    if (initial_stat.st_dev, initial_stat.st_ino, initial_stat.st_size, initial_stat.st_mtime_ns) != (
            final_stat.st_dev, final_stat.st_ino, final_stat.st_size, final_stat.st_mtime_ns) \
            or _file_sha256(path) != expected_file:
        raise ValueError("Durable source changed during replay")
    return engine
