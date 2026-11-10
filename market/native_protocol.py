"""Strict, bounded native-image protocol and offline integrity evidence.

This module imports only the standard library. It never loads the simulator,
starts processes, advances clocks, reconciles D1 or performs transport ownership.
The offline verifier establishes internal integrity, not native attestation.
"""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import re
import stat
import struct
from types import MappingProxyType
from uuid import UUID


MAX_NS = 2 ** 63 - 1
MAX_U64 = 2 ** 64 - 1
MAX_J = 2 ** 53 - 1
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
POPULATIONS = dict(zip(GROUPS, (15, 2, 4064, 4, 2, 1, 1)))
FAULTS = (
    "startup", "source", "clock", "protocol", "deadline", "resource", "ownership",
    "storage", "journal_gap", "worker_failed", "worker_outcome_unknown", "cleanup_failed",
)
ZERO_SHA256 = "0" * 64
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PACKAGE_FINGERPRINT = "1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b"
CONSTANTS = MappingProxyType(dict(
    model_observations=40, observation_ticks=5000, image_observations=8,
    wall_ns=900000000000, startup_ns=180000000000, observe_ns=30000000000,
    exchange_ns=5000000000, probe_ns=5000000000, cleanup_ns=25000000000,
    monitor_period_ns=100000000, monitor_gap_ns=2000000000,
    job_commit_bytes=4294967296, rss_stop_bytes=4294967296,
    combined_output_bytes=268435456, evidence_bytes=67108864,
    event_bytes=33554432, event_records=4096, monitor_bytes=25165824,
    monitor_records=12000, receipt_batches=32, receipt_batch_bytes=8192,
))
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_ENVELOPE = "schema type seq incarnation worker_session protocol_sha256 launch_nonce"
_TUPLE = "id incarnation dispatch_id worker_session frame_sha256"


class ProtocolError(ValueError):
    """A closed protocol/integrity error; no arbitrary input text is reflected."""

    def __init__(self, code="protocol"):
        self.code = code if code in FAULTS else "protocol"
        super().__init__(self.code)


def _require(condition, code="protocol"):
    if not condition:
        raise ProtocolError(code)


def _int(value, low=0, high=MAX_NS):
    _require(type(value) is int and low <= value <= high)
    return value


def _bool(value):
    _require(type(value) is bool)


def _text(value, limit):
    _require(type(value) is str and len(value) <= limit)
    _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value))
    return value


def _literal(value, *choices):
    _require(type(value) is str and value in choices)


def _digest(value):
    _require(type(value) is str and _DIGEST.fullmatch(value) is not None)


def _uuid(value):
    _text(value, 36)
    try:
        _require(str(UUID(value)) == value)
    except (ValueError, AttributeError):
        raise ProtocolError() from None


def _number(value, low=0, high=900):
    _require(type(value) in (int, float) and low <= value <= high)
    _require(type(value) is int or math.isfinite(value))


def _optional(value, check):
    if value is not None:
        check(value)


def _keys(value, keys):
    if type(keys) is str:
        keys = keys.split()
    _require(type(value) is dict and set(value) == set(keys))


def _array(value, count=None, limit=5000):
    _require(type(value) is list and len(value) <= limit)
    if count is not None:
        _require(len(value) == count)


def _plain(value):
    if isinstance(value, FrozenRecord):
        return {key: _plain(item) for key, item in value.items()}
    if type(value) is dict or type(value) is MappingProxyType:
        return {key: _plain(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_plain(item) for item in value]
    return value


def _freeze(value):
    if type(value) is dict:
        return FrozenRecord(value)
    if type(value) in (list, tuple):
        return tuple(_freeze(item) for item in value)
    _require(value is None or type(value) in (str, int, float, bool))
    return value


@dataclass(frozen=True, init=False, eq=False)
class FrozenRecord(Mapping):
    """Detached immutable JSON object; arrays become tuples, objects records."""

    _values: Mapping

    def __init__(self, value):
        _require(isinstance(value, Mapping))
        object.__setattr__(self, "_values", MappingProxyType({key: _freeze(item) for key, item in value.items()}))

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __getattr__(self, key):
        try:
            return self._values[key]
        except KeyError:
            raise AttributeError(key) from None

    def to_dict(self):
        return _plain(self)


def canonical_bytes(value):
    try:
        return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ProtocolError() from None


def canonical_sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_json(raw, *, byte_limit, node_limit=8192, header_frame=False):
    """Preflight depth/collection/node budgets before json constructs containers."""
    _require(type(raw) is bytes and 0 < len(raw) <= byte_limit)
    try:
        text = raw.decode("utf-8", errors="strict")
        position = 0
        nodes = 0
        root_type = None

        def whitespace():
            nonlocal position
            while position < len(text) and text[position] in " \t\r\n":
                position += 1

        def string():
            nonlocal position
            start = position
            position += 1
            while position < len(text):
                char = text[position]
                if char == '"':
                    position += 1
                    value = json.loads(text[start:position])
                    _text(value, byte_limit)
                    return value
                if char == "\\":
                    position += 2
                else:
                    _require(ord(char) >= 32)
                    position += 1
            raise ProtocolError()

        def value(depth):
            nonlocal position, nodes, root_type
            _require(depth <= 12)
            nodes += 1
            _require(nodes <= node_limit)
            whitespace()
            _require(position < len(text))
            char = text[position]
            if char == '"':
                string()
            elif char in "[{":
                position += 1
                close = "]" if char == "[" else "}"
                whitespace()
                count = 0
                if position < len(text) and text[position] == close:
                    position += 1
                    return
                seen = set()
                while True:
                    count += 1
                    _require(count <= (5000 if char == "[" else 128))
                    if char == "{":
                        whitespace()
                        _require(position < len(text) and text[position] == '"')
                        key = string()
                        _require(key not in seen)
                        seen.add(key)
                        nodes += 1
                        _require(nodes <= node_limit)
                        whitespace()
                        _require(position < len(text) and text[position] == ":")
                        position += 1
                    content_start = position
                    value(depth + 1)
                    if depth == 1 and char == "{" and key == "type":
                        token = text[content_start:position].strip()
                        root_type = json.loads(token) if token.startswith('"') else None
                    whitespace()
                    _require(position < len(text))
                    delimiter = text[position]
                    position += 1
                    if delimiter == close:
                        break
                    _require(delimiter == ",")
            else:
                start = position
                while position < len(text) and text[position] not in " \t\r\n,]}":
                    position += 1
                token = text[start:position]
                _require(len(token) <= 64)
                parsed = json.loads(token)
                _require(parsed is None or type(parsed) is bool or type(parsed) in (int, float))
                if type(parsed) is int:
                    _require(-MAX_U64 <= parsed <= MAX_U64)
                if type(parsed) is float:
                    _require(math.isfinite(parsed))

        value(1)
        whitespace()
        _require(position == len(text))
        if header_frame and root_type != "static_header":
            _require(nodes <= 8192)
        return json.loads(text)
    except (UnicodeError, ValueError, IndexError, RecursionError, OverflowError):
        raise ProtocolError() from None


def rgb_sha256(binary):
    _require(type(binary) is bytes and len(binary) == 12288)
    declaration = dict(version="rgb-input/v1", dtype="uint8", rank=3, shape=[64, 64, 3])
    return hashlib.sha256(canonical_bytes(declaration) + b"\n" + binary).hexdigest()


BLACK_SHA256 = rgb_sha256(bytes(12288))


def free_observations(issued, unissued_active):
    _int(issued, 0, 40)
    _int(unissued_active, 0, 7)
    _require(issued + unissued_active <= 40)
    return 40 - issued - unissued_active


def validate_clock_brackets(brackets):
    brackets = _plain(brackets)
    _array(brackets, 3)
    previous = 0
    for index, row in enumerate(brackets):
        _keys(row, "index p0_ns child_ns p1_ns")
        _int(row["index"], index, index)
        for key in ("p0_ns", "child_ns", "p1_ns"):
            _int(row[key])
        _require(previous <= row["p0_ns"] <= row["child_ns"] <= row["p1_ns"])
        _require(row["p1_ns"] - row["p0_ns"] < 2000000000)
        previous = row["p1_ns"]
    return tuple(FrozenRecord(row) for row in brackets)


def _identity(value):
    _keys(value, "pid creation_time_100ns executable executable_sha256")
    _int(value["pid"], 1, 2 ** 32 - 1)
    _int(value["creation_time_100ns"], 0, MAX_U64)
    _text(value["executable"], 1024)
    _digest(value["executable_sha256"])


def _clock(value):
    _keys(value, "implementation monotonic adjustable resolution_ns")
    _text(value["implementation"], 128)
    _require(value["monotonic"] is True and value["adjustable"] is False)
    _int(value["resolution_ns"], 1, 1000000)


def _permit(value):
    _keys(value, _TUPLE + " deadline_ns exposure_observations")
    for key in _TUPLE.split():
        (_digest if key == "frame_sha256" else _uuid)(value[key])
    _int(value["deadline_ns"])
    _int(value["exposure_observations"], 8, 8)


def _start(value):
    _keys(value, _TUPLE + " started_ns first_observation_index")
    for key in _TUPLE.split():
        (_digest if key == "frame_sha256" else _uuid)(value[key])
    _int(value["started_ns"])
    _int(value["first_observation_index"], 0, 32)


def validate_start(start, permit):
    start, permit = _plain(start), _plain(permit)
    _start(start)
    _permit(permit)
    _require(all(start[key] == permit[key] for key in _TUPLE.split()))
    _require(start["started_ns"] < permit["deadline_ns"])
    return FrozenRecord(start)


def _complete(value):
    _keys(value, _TUPLE + " observation_indices completed_ns")
    for key in _TUPLE.split():
        (_digest if key == "frame_sha256" else _uuid)(value[key])
    _int(value["completed_ns"])
    _array(value["observation_indices"], 8)
    for index in value["observation_indices"]:
        _int(index, 0, 39)
    first = value["observation_indices"][0]
    _require(value["observation_indices"] == list(range(first, first + 8)))


_EXTRAS = {
    "challenge": "challenge_index p0_ns", "clock": "challenge_index p0_ns child_ns",
    "initialize": "bindings_sha256", "probe_request": "compiler_sha256 argv_sha256 environment_sha256",
    "probe_allow": "request_seq allowed_ns", "probe_started": "process allowed_ns started_ns",
    "probe_finished": "process started_ns completed_ns exit_code stdout_bytes stderr_bytes stdout_sha256 stderr_sha256 version",
    "static_header": "header",
    "ready": "bindings_sha256 header_sha256 engine_identity_sha256 build_sha256 graph_nodes graph_edges observation_index model_tick ready_ns",
    "release": "last_observation_index next_observation_index action permit dispatch_id exposure_ordinal",
    "ack": "last_observation_index next_observation_index action permit dispatch_id exposure_ordinal",
    "start": "receipt", "complete": "receipt", "stop": "reason",
    "ended": "reason observations_completed last_observation_index last_tick wall_ns header_sha256 engine_identity_sha256 fault",
    "fault": "code phase observation_index dispatch_id wall_ns observations_completed",
    "observation": "observation_index input_kind image_id dispatch_id exposure_ordinal frame_sha256 engine_identity_sha256 header_sha256 start_tick end_tick wall_start_ns wall_completion_ns learning stimulation pathway_detail qualification_detail group_spikes group_rates_hz group_bin_counts total_spikes compute_seconds kernel_seconds cell_bytes_sha256 start_receipt first_call_ns",
}
_PARENT = ("hello", "challenge", "initialize", "probe_allow", "release", "ack", "stop")
_WORKER = ("hello", "clock", "probe_request", "probe_started", "probe_finished", "static_header", "ready", "start", "observation", "complete", "ended", "fault")


def _group_map(value, rates=False):
    _keys(value, GROUPS)
    for item in value.values():
        if rates:
            _number(item, 0, 10000)
        else:
            _int(item, 0, 833500000)


def _observation_shape(value, binary):
    index = _int(value["observation_index"], 0, 39)
    _literal(value["input_kind"], "black", "image")
    for name in ("image_id", "dispatch_id"):
        _optional(value[name], _uuid)
    _optional(value["exposure_ordinal"], lambda v: _int(v, 0, 7))
    for name in ("frame_sha256", "engine_identity_sha256", "header_sha256", "cell_bytes_sha256"):
        _digest(value[name])
    _int(value["start_tick"], index * 5000, index * 5000)
    _int(value["end_tick"], (index + 1) * 5000, (index + 1) * 5000)
    _int(value["wall_start_ns"])
    _int(value["wall_completion_ns"])
    _require(value["wall_start_ns"] <= value["wall_completion_ns"])
    _require(value["wall_completion_ns"] - value["wall_start_ns"] < CONSTANTS["observe_ns"])
    for name in ("learning", "pathway_detail", "qualification_detail"):
        _require(value[name] is False)
    _require(value["stimulation"] is None)
    _group_map(value["group_spikes"])
    _group_map(value["group_rates_hz"], True)
    _array(value["group_bin_counts"], 50)
    for row in value["group_bin_counts"]:
        _array(row, 7)
        for item in row:
            _int(item, 0, 16670000)
    _int(value["total_spikes"], 0, 833500000)
    _number(value["compute_seconds"])
    _number(value["kernel_seconds"])
    _require(len(binary) == 12800 and max(binary) <= 100)
    _require(hashlib.sha256(binary).hexdigest() == value["cell_bytes_sha256"])
    _optional(value["start_receipt"], _start)
    _optional(value["first_call_ns"], _int)
    if value["input_kind"] == "black":
        _require(all(value[name] is None for name in ("image_id", "dispatch_id", "exposure_ordinal", "start_receipt", "first_call_ns")))
        _require(value["frame_sha256"] == BLACK_SHA256)
    else:
        _require(all(value[name] is not None for name in ("image_id", "dispatch_id", "exposure_ordinal")))
        if value["exposure_ordinal"] == 0:
            start = value["start_receipt"]
            _require(start is not None and value["first_call_ns"] == value["wall_start_ns"])
            _require(start["id"] == value["image_id"] and start["dispatch_id"] == value["dispatch_id"])
            _require(start["frame_sha256"] == value["frame_sha256"] and start["first_observation_index"] == index)
            _require(start["started_ns"] <= value["first_call_ns"])
        else:
            _require(value["start_receipt"] is None and value["first_call_ns"] is None)


def validate_message(message, direction, binary=b"", *, persisted=False):
    value = _plain(message)
    _literal(direction, "parent", "worker")
    _require(type(binary) is bytes and type(value) is dict)
    kind = value.get("type")
    _require(type(kind) is str and kind in (_PARENT if direction == "parent" else _WORKER))
    extra = ("bindings_sha256 parent_clock" if direction == "parent" else "bindings_sha256 worker worker_clock") if kind == "hello" else _EXTRAS[kind]
    base = _ENVELOPE.split()
    if persisted:
        base.remove("launch_nonce")
    _keys(value, base + extra.split())
    _literal(value["schema"], "market-native-ipc/v1")
    _int(value["seq"], 0, 4095)
    _uuid(value["incarnation"])
    _uuid(value["worker_session"])
    _digest(value["protocol_sha256"])
    if not persisted:
        _digest(value["launch_nonce"])
    for name in extra.split():
        if name.endswith("sha256"):
            _optional(value[name], _digest) if kind == "ended" else _digest(value[name])
    if kind not in ("ack", "observation"):
        _require(not binary)
    if kind == "hello":
        _clock(value["parent_clock" if direction == "parent" else "worker_clock"])
        if direction == "worker":
            _identity(value["worker"])
    elif kind in ("challenge", "clock"):
        _int(value["challenge_index"], 0, 2)
        _int(value["p0_ns"])
        if kind == "clock":
            _int(value["child_ns"])
            _require(value["child_ns"] >= value["p0_ns"])
    elif kind == "probe_allow":
        _int(value["request_seq"], 0, 4095)
        _int(value["allowed_ns"])
    elif kind in ("probe_started", "probe_finished"):
        _identity(value["process"])
        _int(value["started_ns"])
        if kind == "probe_started":
            _int(value["allowed_ns"])
            _require(value["allowed_ns"] <= value["started_ns"])
        else:
            _int(value["completed_ns"])
            _require(value["started_ns"] <= value["completed_ns"] < value["started_ns"] + CONSTANTS["probe_ns"])
            _int(value["exit_code"], 0, 0)
            _int(value["stderr_bytes"], 0, 0)
            _int(value["stdout_bytes"], 7, 8)
            expected = b"0.16.0\n" if value["stdout_bytes"] == 7 else b"0.16.0\r\n"
            _require(value["stdout_sha256"] == hashlib.sha256(expected).hexdigest())
            _require(value["stderr_sha256"] == EMPTY_SHA256)
            _literal(value["version"], "0.16.0")
    elif kind == "static_header":
        validate_header(value["header"])
    elif kind == "ready":
        for name, expected in (("graph_nodes", 166700), ("graph_edges", 25582938), ("observation_index", 0), ("model_tick", 0)):
            _int(value[name], expected, expected)
        _int(value["ready_ns"])
    elif kind in ("release", "ack"):
        last, nxt, action = value["last_observation_index"], value["next_observation_index"], value["action"]
        _optional(last, lambda v: _int(v, 0, 39))
        _optional(nxt, lambda v: _int(v, 0, 39))
        _literal(action, "black", "image", "continue_image", "end")
        if kind == "release":
            _require(last is None and nxt == 0 and action == "black")
        elif action == "end":
            _require(last == 39 and nxt is None)
        else:
            _require(last is not None and last < 39 and nxt == last + 1)
        if action in ("black", "end"):
            _require(not binary and all(value[key] is None for key in ("permit", "dispatch_id", "exposure_ordinal")))
        elif action == "image":
            _permit(value["permit"])
            _uuid(value["dispatch_id"])
            _int(value["exposure_ordinal"], 0, 0)
            _require(nxt <= 32 and value["permit"]["dispatch_id"] == value["dispatch_id"])
            _require(all(value["permit"][key] == value[key] for key in ("incarnation", "worker_session")))
            _require(rgb_sha256(binary) == value["permit"]["frame_sha256"])
        else:
            _require(value["permit"] is None and not binary)
            _uuid(value["dispatch_id"])
            _int(value["exposure_ordinal"], 1, 7)
    elif kind == "start":
        _start(value["receipt"])
        _require(all(value["receipt"][key] == value[key] for key in ("incarnation", "worker_session")))
    elif kind == "complete":
        _complete(value["receipt"])
        _require(all(value["receipt"][key] == value[key] for key in ("incarnation", "worker_session")))
    elif kind == "observation":
        _observation_shape(value, binary)
    elif kind == "stop":
        _literal(value["reason"], "operator", "session_fault", "shutdown")
    elif kind == "fault":
        _literal(value["code"], *FAULTS)
        _literal(value["phase"], "bootstrap", "probe", "startup", "observe", "delivery", "shutdown")
        _optional(value["observation_index"], lambda v: _int(v, 0, 39))
        _optional(value["dispatch_id"], _uuid)
        _optional(value["wall_ns"], _int)
        _int(value["observations_completed"], 0, 40)
        _require(value["wall_ns"] is not None or value["code"] == "clock")
    elif kind == "ended":
        _literal(value["reason"], "model_limit", "cancelled", "fault")
        count = _int(value["observations_completed"], 0, 40)
        _optional(value["last_observation_index"], lambda v: _int(v, 0, 39))
        _require(value["last_observation_index"] == (count - 1 if count else None))
        _int(value["last_tick"], count * 5000, count * 5000)
        _optional(value["wall_ns"], _int)
        _optional(value["fault"], lambda v: _literal(v, *FAULTS))
        _require((value["header_sha256"] is None) == (value["engine_identity_sha256"] is None))
        _require((value["reason"] == "fault") == (value["fault"] is not None))
        _require(value["wall_ns"] is not None or value["fault"] == "clock")
        if value["reason"] == "model_limit":
            _require(count == 40 and value["header_sha256"] is not None)
    return FrozenRecord(value)


def _body_cap(message):
    kind = message.get("type")
    if kind == "static_header":
        return 2097152
    if kind == "ready":
        return 8192
    if kind == "observation":
        return 32768
    if kind == "ack" and message.get("action") == "image":
        return 16384
    return 4096


@dataclass(frozen=True)
class Frame:
    message: FrozenRecord
    binary: bytes


def encode_frame(message, binary=b"", *, direction):
    record = validate_message(message, direction, binary)
    encoded = canonical_bytes(record)
    body = struct.pack("<I", len(encoded)) + encoded + binary
    _require(len(body) <= _body_cap(record))
    return struct.pack("<I", len(body)) + body


def decode_frame(raw, direction):
    _require(type(raw) is bytes and 8 <= len(raw) <= 2097156)
    length, json_length = struct.unpack("<II", raw[:8])
    _require(length == len(raw) - 4 and 0 < json_length <= length - 4)
    message = parse_json(raw[8:8 + json_length], byte_limit=2097148, node_limit=40000, header_frame=True)
    _require(type(message) is dict and length <= _body_cap(message))
    _require(canonical_bytes(message) == raw[8:8 + json_length])
    binary = raw[8 + json_length:]
    return Frame(validate_message(message, direction, binary), binary)


def _read_exact(stream, count, *, clean_eof=False):
    chunks = []
    remaining = count
    while remaining:
        chunk = stream.read(min(remaining, 65536))
        _require(type(chunk) is bytes and len(chunk) <= remaining)
        if not chunk:
            if clean_eof and remaining == count:
                return None
            raise ProtocolError()
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_frame(stream, direction, *, max_body=2097152):
    _int(max_body, 5, 2097152)
    prefix = _read_exact(stream, 4, clean_eof=True)
    if prefix is None:
        return None
    length = struct.unpack("<I", prefix)[0]
    _require(4 < length <= max_body)
    return decode_frame(prefix + _read_exact(stream, length), direction)


PARAMETER_KEYS = (
    "interpretation", "source", "kc_adaptation_jump_mV", "kc_adaptation_tau_ms",
    "kc_rest_mV", "maximum_fraction", "maximum_rate_bin_ms", "memory_decay_seconds",
    "minimum_fraction", "modulator_delivery_trace_ms", "neural_dt_ms",
    "trace_dan_seconds", "trace_kc_seconds", "weight_filter_seconds",
)
CONFIGURATION_KEYS = (
    "adaptation_jump", "adaptation_tau", "corrected_edges", "dan_baseline_hz",
    "dan_index", "gain", "initial_weight", "kc_mask", "lamina", "modulation_mask",
    "pre", "r8", "r8_channel", "r8_uv", "rest", "retina", "rule", "rule_sha256",
    "sugar", "tonic", "uv",
)
RULE_KEYS = (
    "interpretation", "source", "maximum_fraction", "maximum_rate_bin_ms",
    "memory_decay_seconds", "minimum_fraction", "trace_dan_seconds",
    "trace_kc_seconds", "weight_filter_seconds",
)
APPLICATION_SOURCES = tuple("market/" + name + ".py" for name in (
    "__init__", "fixtures", "ownership", "price_service", "local_server",
    "image_admission", "image_decode", "image_decode_windows", "image_intake",
    "native_protocol", "native_windows", "native_worker", "native_session",
)) + ("scripts/run-market-native-service.py", "scripts/market-image-decode-worker.py")
LOCK_SOURCES = tuple("src/fly_connectome_sim/neural/" + name + ".json" for name in (
    "arrays.lock", "sources.lock", "neurons.lock", "datasets",
)) + ("src/fly_connectome_sim/schemas/run.schema.json",)
TOOL_KEYS = ("python_launcher", "python_config", "worker_exe", "compiler_exe", "native_library", "native_metadata")
DEPENDENCY_KEYS = ("numpy_init", "numpy_metadata", "pandas_init", "pandas_metadata", "pyarrow_init", "pyarrow_metadata")
RUNTIME_KEYS = ("graph", "normalized_neurons", "annotations", "neurotransmitters", "edges")


def _native_metadata(value, *, build=False):
    names = "source_sha256 compiler flags library binary_sha256" + (" model" if build else "")
    _keys(value, names)
    _digest(value["source_sha256"])
    _digest(value["binary_sha256"])
    _literal(value["compiler"], "0.16.0")
    _require(value["flags"] == ["-O3", "-std=c++17", "-shared", "-Wl,--export-all-symbols"])
    _literal(value["library"], "memory.dll")
    _require(value["source_sha256"] == PRESERVED_SOURCES["src/fly_connectome_sim/neural/kernel.cpp"])
    if build:
        _literal(value["model"], "stonkfly-dual-compartment-v1")


def _declaration(value, keys):
    _keys(value, keys)
    for name, item in value.items():
        if name in ("interpretation", "source"):
            _text(item, 1024)
        else:
            _number(item, -MAX_U64, MAX_U64)


def _engine_identity(value):
    _keys(value, "version model_provenance neural_groups sha256")
    _literal(value["version"], "fly-engine/v1")
    _digest(value["sha256"])
    _require(canonical_sha256({k: v for k, v in value.items() if k != "sha256"}) == value["sha256"])
    groups = value["neural_groups"]
    _keys(groups, GROUPS)
    for name in GROUPS:
        _array(groups[name], POPULATIONS[name])
        for index in groups[name]:
            _int(index, 0, 166699)
        _require(len(set(groups[name])) == len(groups[name]))
    provenance = value["model_provenance"]
    _keys(provenance, "model model_fingerprint build eta parameters graph_ids_sha256 graph_ptr_sha256 graph_post_sha256 plastic_edges_sha256 configuration_sha256")
    _literal(provenance["model"], "stonkfly-dual-compartment-v1")
    _number(provenance["eta"], 0.001, 0.001)
    _native_metadata(provenance["build"], build=True)
    fingerprint = provenance["model_fingerprint"]
    _keys(fingerprint, "version sources_sha256 sha256")
    _literal(fingerprint["version"], "model-source/v1")
    expected = {key.removeprefix("src/fly_connectome_sim/"): value for key, value in PRESERVED_SOURCES.items() if key.startswith("src/fly_connectome_sim/")}
    _require(fingerprint["sources_sha256"] == expected)
    _require(fingerprint["sha256"] == PACKAGE_FINGERPRINT)
    _require(canonical_sha256({k: v for k, v in fingerprint.items() if k != "sha256"}) == fingerprint["sha256"])
    for name in ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "plastic_edges_sha256"):
        _digest(provenance[name])
    _declaration(provenance["parameters"], PARAMETER_KEYS)
    configuration = provenance["configuration_sha256"]
    _keys(configuration, CONFIGURATION_KEYS)
    for name, item in configuration.items():
        if name in ("adaptation_jump", "adaptation_tau"):
            _number(item, -MAX_U64, MAX_U64)
        elif name == "rule":
            _declaration(item, RULE_KEYS)
        else:
            _digest(item)


def validate_header(header, *, bindings=None, arrays_lock=None, sources_lock=None):
    value = _plain(header)
    _require(len(canonical_bytes(value)) <= 2097152)
    _keys(value, "type version engine_identity selection cells topology source")
    _literal(value["type"], "header")
    _literal(value["version"], "cell-activity-raw/v1")
    _engine_identity(value["engine_identity"])
    groups = {name: set(indices) for name, indices in value["engine_identity"]["neural_groups"].items()}
    _array(value["cells"], 256)
    selected = set()
    last_source = 0
    selected_counts = dict.fromkeys(GROUPS, 0)
    for cell in value["cells"]:
        _keys(cell, "model_index source_id groups soma")
        index = _int(cell["model_index"], 0, 166699)
        source = _int(cell["source_id"], 1, MAX_J)
        _require(index not in selected and source > last_source)
        selected.add(index)
        last_source = source
        _require(cell["groups"] == [name for name in GROUPS if index in groups[name]])
        _require(bool(cell["groups"]))
        for name in cell["groups"]:
            selected_counts[name] += 1
        if cell["soma"] is not None:
            _array(cell["soma"], 3)
            for coordinate in cell["soma"]:
                _int(coordinate, -MAX_J, MAX_J)
    for name in GROUPS:
        if name != "kc":
            _require(groups[name] <= selected)
    selection = value["selection"]
    _keys(selection, "method limit group_population_counts group_selected_counts")
    _literal(selection["method"], "mandatory-groups-kc-stride/v1")
    _int(selection["limit"], 256, 256)
    _keys(selection["group_population_counts"], GROUPS)
    _keys(selection["group_selected_counts"], GROUPS)
    for name in GROUPS:
        _int(selection["group_population_counts"][name], POPULATIONS[name], POPULATIONS[name])
        _int(selection["group_selected_counts"][name], selected_counts[name], selected_counts[name])
    topology = value["topology"]
    _keys(topology, "method limit eligible_edges edges")
    _literal(topology["method"], "induced-directed-edge-stride/v1")
    _int(topology["limit"], 512, 512)
    eligible = _int(topology["eligible_edges"], 0, 25582938)
    _array(topology["edges"], min(eligible, 512))
    previous = None
    edge_ids = set()
    for edge in topology["edges"]:
        _array(edge, 3)
        identifier = _int(edge[0], 0, 25582937)
        a, b = (_int(slot, 0, 255) for slot in edge[1:])
        order = (value["cells"][a]["source_id"], value["cells"][b]["source_id"], identifier)
        _require(identifier not in edge_ids and (previous is None or order > previous))
        edge_ids.add(identifier)
        previous = order
    _keys(value["source"], "graph_ids_sha256 graph_ptr_sha256 graph_post_sha256 annotations_sha256")
    for name, item in value["source"].items():
        _digest(item)
        if name != "annotations_sha256":
            _require(item == value["engine_identity"]["model_provenance"][name])
    if bindings is not None:
        bound = _plain(bindings)
        _require(value["source"]["annotations_sha256"] == bound["files"]["annotations"]["sha256"])
        _require(value["engine_identity"]["model_provenance"]["build"] == dict(bound["native_metadata"], model="stonkfly-dual-compartment-v1"))
    if arrays_lock is not None:
        lock = _plain(arrays_lock)
        _keys(lock, "ptr post weight ids retina uv confidence hexes lamina sugar superclass")
        for item in lock.values():
            _digest(item)
        for name in ("ids", "ptr", "post"):
            _require(value["source"]["graph_" + name + "_sha256"] == lock[name])
    if sources_lock is not None:
        lock = _plain(sources_lock)
        _keys(lock, "annotations.feather neurotransmitters.feather edges.feather")
        for entry in lock.values():
            _keys(entry, "url bytes sha256")
            _text(entry["url"], 1024)
            _int(entry["bytes"], 0, 4294967296)
            _digest(entry["sha256"])
        annotation = lock["annotations.feather"]
        _require(value["source"]["annotations_sha256"] == annotation["sha256"])
        if bindings is not None:
            _require(bound["files"]["annotations"]["bytes"] == annotation["bytes"])
    return FrozenRecord(value)


def validate_observation(observation, binary, header, *, permit=None, previous=None, receipt_ns=None):
    value, header = _plain(observation), _plain(validate_header(header))
    persisted = "launch_nonce" not in value
    validate_message(value, "worker", binary, persisted=persisted)
    _require(value["type"] == "observation")
    _require(value["header_sha256"] == canonical_sha256(header))
    identity = header["engine_identity"]
    _require(value["engine_identity_sha256"] == identity["sha256"])
    groups = [set(identity["neural_groups"][name]) for name in GROUPS]
    totals = []
    for group_index, name in enumerate(GROUPS):
        population = len(groups[group_index])
        selected_slots = [slot for slot, cell in enumerate(header["cells"]) if name in cell["groups"]]
        total = 0
        for bin_index, row in enumerate(value["group_bin_counts"]):
            count = row[group_index]
            _require(count <= 100 * population)
            selected_count = sum(binary[bin_index * 256 + slot] for slot in selected_slots)
            _require(selected_count <= count if name == "kc" else selected_count == count)
            for other in range(7):
                if groups[group_index] <= groups[other]:
                    _require(count <= row[other])
            total += count
        _require(total == value["group_spikes"][name])
        _require(math.isclose(value["group_rates_hz"][name], total / (population * 0.5), rel_tol=1e-9, abs_tol=1e-9))
        totals.append(total)
    lower = 0
    for mask in range(1, 128):
        members = [index for index in range(7) if mask & (1 << index)]
        if all(groups[a].isdisjoint(groups[b]) for position, a in enumerate(members) for b in members[position + 1:]):
            lower = max(lower, sum(totals[index] for index in members))
    _require(max(lower, sum(binary)) <= value["total_spikes"] <= 833500000)
    if previous is not None:
        previous = _plain(previous)
        _require(value["observation_index"] == previous["observation_index"] + 1)
        _require(value["wall_start_ns"] >= previous["wall_completion_ns"])
    if receipt_ns is not None:
        _int(receipt_ns)
        _require(value["wall_completion_ns"] <= receipt_ns)
    if value["input_kind"] == "image":
        _require(permit is not None)
        permit = _plain(permit)
        _permit(permit)
        for key, observation_key in (("id", "image_id"), ("dispatch_id", "dispatch_id"), ("frame_sha256", "frame_sha256"), ("incarnation", "incarnation"), ("worker_session", "worker_session")):
            _require(permit[key] == value[observation_key])
        if value["exposure_ordinal"] == 0:
            validate_start(value["start_receipt"], permit)
            _require(value["first_call_ns"] < permit["deadline_ns"])
    return FrozenRecord(value)


# Accepted Appendix G bytes; never regenerated from current files at runtime.
PRESERVED_SOURCES = MappingProxyType({
    'scripts/analyze-market-feasibility.py': '19bca306f6720d5931b31321d1ccc8939a447737b23cc052931b6348994a46cc',
    'scripts/analyze-response-structure.py': '5a8eaff4e2904191d394859c8eb02ae107a61de04cb000228e371e1c61052b25',
    'scripts/continuous_motor_supervision.py': 'b2527b1817baaee0962d4c49007826ff78e51e55ee0122728376739c0a649add',
    'scripts/drive_input_supervision.py': '06aa2ad4aed00c91027a03147229f6c507cb5e5fb21af0f1a01b13156bf210f8',
    'scripts/export-anatomy.py': '119c1898b3c018cde1e39059d8bf122a43c15c4bb7bac33e4f331f86f1d7161e',
    'scripts/live_buffer_supervision.py': '75dd275bd3a6e867fafd0d2d17c6adc0df38fb215752b5c404322dfab0246055',
    'scripts/market_artifacts.py': '1e6074838481d3149be56a6235f74b7de29d5d2c45d56bd1cf7311460ccb0c0a',
    'scripts/market_continuous_drive.py': '7285c150d2ab14506c94d90d995da142e71eb1d29277f7b4d582b740c953e42d',
    'scripts/market_live_buffers.py': '5c81391fd4bf1a667ef0d483f027601af66f10eafd64a6e98283c53e1d1ec9ad',
    'scripts/market_motor_readout.py': 'e11e9a7adc10b10f08a67b25e41ad1d717174c0e5a106ef9be61416e060734e1',
    'scripts/market_motor_readout_v2.py': '878b6a4d16c824727ac78edd68cb5e44da11445a0889e7b8a35e960b0f94bf69',
    'scripts/market_population_state.py': '8ad6552e6e7032035b6ded30d5823a1253751e02d66dc587cf7a64737903b550',
    'scripts/market_supervision.py': 'a1ed136a32a482f78f6a6de337e67ad28c05bd2ad42ac31d8ce949a27350182d',
    'scripts/run-cell-activity-session.py': 'cd4a04234d82c2a22b21b22f858e70ee2047c2c1cd78ce30336d0deb550ec6ed',
    'scripts/run-continuous-motor-probe.py': 'd01095013f16592c402347fbd962a566bf589ba666e5e3c9f27b53ebcd0ef1e8',
    'scripts/run-drive-input-comparison.py': 'ed7ca12a34193b1a4a01ca4dd305c396ad387708aa3b051f79209051b4d143d4',
    'scripts/run-live-buffer-performance.py': 'a8b5d50e15ed18c6f06b07a261a31006bbd2faa8a95a1edeccf31e351a3e761d',
    'scripts/run-market-response-diagnostic.py': '3b9b464d9bf43caecb3f44586bcf15481ea5fc53233b29db123a2a1451fe67f6',
    'scripts/screen-population-excursion.py': '06082860bc1ab0cc3ce5a27bf167aeb268ca04e0422905137ba3c29b7217d929',
    'scripts/supervise-continuous-motor.ps1': '16fcfee8458c693e01ab396d935750ff2bbb74dcc43c6dfc70accbb9cb2465f5',
    'scripts/supervise-drive-input.ps1': 'a50e1b09135d4a74b8b0f343a162d4ad6a7c005191245897ee869d3dc234512b',
    'scripts/supervise-live-buffer.ps1': 'ff23ea6ca3b83f00a88d5bd98f947c16e99e358c91a77a3e8ce54d97e11060cd',
    'scripts/supervise-market-response.ps1': '584358175f3a6be9a759ca816124c0ff70519f3488d35786001988776c918861',
    'src/fly_connectome_sim/__init__.py': 'e264625ca71686e6284982c6ed394e50a80e0bd295dcf58c8519ea94e009b234',
    'src/fly_connectome_sim/cli.py': '32a4e9c15c6c216a38f560143e5601c297af92e30cf48f4c9dbd7054261e608e',
    'src/fly_connectome_sim/data.py': 'f08f2c83ae788856d383adaf9aff8e7886a7b4a25326cd9c48559e4a73a93243',
    'src/fly_connectome_sim/engine.py': '25ac8924f46c434d788c7defd9ec66f489f6dbeef0e653873bb545a099b58833',
    'src/fly_connectome_sim/experiment/__init__.py': 'c52b94ba0296e4f3d43911f36c5e703a35e3ab4b84f59671bd428e45e6f32fb1',
    'src/fly_connectome_sim/experiment/adapter.py': '7e6fab3635d357780fee45d53769f385c5b15d95fa2d2f46b6e4e0e69583e3fe',
    'src/fly_connectome_sim/experiment/analysis.py': '2d63a826fa0c63f0208852ba447f8b73f8b614091255d505468cdf49f6bd6e0f',
    'src/fly_connectome_sim/experiment/assay.py': '23a3589818a6375521530403ac67718a9c48b440622206f3f84669b3ad201f58',
    'src/fly_connectome_sim/experiment/cell_activity.py': '63047d84b448511d8a41da73ba7d5252e085d23f1ff91b9972f2e677a41c456f',
    'src/fly_connectome_sim/experiment/content_diagnostic.py': 'e9a0657a634f0e770cf8dcd529c8428cac1c4b527014bf5e7a1da7cb07b26455',
    'src/fly_connectome_sim/experiment/event_cards.py': 'c3060ab49f1190ac2462e164709ca1aa3127f9d95d18b275178e7d66e5a037ba',
    'src/fly_connectome_sim/experiment/event_choice.py': '05a6d1aee7cf75729303cfb7fed6ea18cdc6febb56ec08ecf5ec2bcc121e5b31',
    'src/fly_connectome_sim/experiment/event_followup.py': '5f6c7928b3efa401bd754b2cb52af084466b957756331e89df4b42d1e4de7b00',
    'src/fly_connectome_sim/experiment/event_proposals.py': 'ccd54c3ff90e055add2600577221f91388472f270c2efcb5cd9e9e1c00964d2c',
    'src/fly_connectome_sim/experiment/executor.py': '616ec40e5df2f5c1290484a7aa023fd0383dcc7dca72e72ce5a2be399be23c7b',
    'src/fly_connectome_sim/experiment/feed_event_session.py': 'fdbbd7b13dc44bb9cbf4184f8f75849963dd6fa4879c5bcb613ff8aa8b4acea9',
    'src/fly_connectome_sim/experiment/measured_replay.py': 'edb2f582e8ea78c15da1fbb6700cf4304b40fcde41669c9e189aaa7afd1bf2fe',
    'src/fly_connectome_sim/experiment/protocol.py': '0cd8952a7176fd910ba4e3c87113aecebf1c87b57952ee967cea8eaf9afb40a2',
    'src/fly_connectome_sim/experiment/qualification.py': '0396d45ec373f124b6d7f0c6c827991273ad483ff5b8cc0400a400759dcbf559',
    'src/fly_connectome_sim/experiment/qualification_grid.py': '5e93098efe48f69337ba80b3b771829f9ad1d2ae48d63edabf97f63c06955420',
    'src/fly_connectome_sim/experiment/recorder.py': '7db2b493217933c15b4da7211cce1b2c66074d1ae0ad1ea40cb63fdbbce7764e',
    'src/fly_connectome_sim/experiment/replay.py': '322da0d210d98a14460e4df0b0f69528eceae3ed2dd7dfebb51b6efda5fcdba2',
    'src/fly_connectome_sim/experiment/session_workflow.py': 'f76cc9f9f828334b319f52b8a8c6e3c936d5ae2dfb8a87f8bb7e7f00c165ab1d',
    'src/fly_connectome_sim/experiment/stimuli.py': '02b2ae2288d8cae859f5ceb99291fcf0e6b05334c2ad9ff3fa1c0c7079fbad08',
    'src/fly_connectome_sim/experiment/video_observation.py': '688be0bb6632d71463cfa5cb5d211c272f6ca1953492252553a2e98b80cab0f5',
    'src/fly_connectome_sim/experiment/video_policy.py': '704b34de1d79bff91378c4d16521e25104360a81870b27a98ca829506a863e67',
    'src/fly_connectome_sim/neural/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'src/fly_connectome_sim/neural/brain.py': '0ebf5ef41a2bfa46664720c1d19b05ea7aff4fe7ec12b434bf4f3d81b2380814',
    'src/fly_connectome_sim/neural/checkpoint.py': 'b72ea9d0d80b5557a0102c41beead593fea77d3b90da749f6d2dc914bb48cd0f',
    'src/fly_connectome_sim/neural/circuit.py': 'e9ed5d237c7c01fbaf80f75cec75f5f9f2e33965461e3480813ade78597f6c45',
    'src/fly_connectome_sim/neural/common.py': 'fadb9b415d3ec4edabe928b1821f3f5dbb34eae8dc67a4927f287ad74074a40a',
    'src/fly_connectome_sim/neural/connectome.py': '38fffdf4bd31cb51be6f3dda3cc4236ff754a2a99d0ced8dbffe00352224d940',
    'src/fly_connectome_sim/neural/kernel.cpp': 'e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509',
    'src/fly_connectome_sim/neural/native.py': '85f68d859621d6c8065e93722f173230f35277ad8d0b18c02f4eee8c5911a4fc',
    'src/fly_connectome_sim/neural/prepare.py': '866c0b1349e47d42ca4915b8829adb74f367d7b5047bbc333bf7190c67fa8f1c',
    'src/fly_connectome_sim/neural/rule.py': '3c80680450c3b73042e332bd7ce8289d7d74d8695c60e7ac19eefd9759d95c44',
    'src/fly_connectome_sim/neural/sensory.py': '46ba99fd966e251a3422f77fdd27a78fe45aa45f9fd14e498e3c5e578566f7ac',
    'src/fly_connectome_sim/neural/state.py': 'de3dac9f37f7c12546124383410e1ac0e720459e2f8e636d3fa155dce6a7d220',
    'src/fly_connectome_sim/neural/transmitters.py': 'b1c1b080da44bdeaf498cdce3504134c1cf070b875f84a4007f16002b2956f93',
    'src/fly_connectome_sim/neural/visual.py': '50cb4f2a4c60a0d938d8e69cc41ce8544327fb433735db9ba1f337b13c342a33',
    'src/fly_connectome_sim/schemas/__init__.py': '2fc8231daedcfd148cae398fd73df982818abb24489436392c140e0c7ba78136',
})


class ProtocolValidator:
    """Finite offline wire-order validator; owns no clocks, IO or lifecycle."""

    def __init__(self):
        self._sequences = dict(parent=0, worker=0)
        self._identity = None
        self._nonce = None
        self._phase = "parent_hello"
        self._challenge = 0
        self._challenge_p0 = None
        self._last_clock_end = 0
        self._clock = None
        self._bindings = None
        self._probe_request = None
        self._probe_allow = None
        self._probe = None
        self._header = None
        self._ready = None
        self._permit = None
        self._start = None
        self._ordinal = None
        self._previous = None
        self._completed = 0
        self._dispatches = 0
        self._processed = 0
        self._ended = None
        self._issued_ns = None
        self._fault = None

    def accept_header(self, header, worker_seq, *, receipt_ns=None):
        """Journal substitute for static_header, whose full bytes live in header.json."""
        _require(self._identity is not None)
        message = dict(zip(("incarnation", "worker_session", "protocol_sha256"), self._identity))
        message.update(schema="market-native-ipc/v1", type="static_header", seq=worker_seq, header=_plain(header))
        return self.accept(message, "worker", receipt_ns=receipt_ns, persisted=True)

    def accept(self, message, direction, binary=b"", *, receipt_ns=None, persisted=False):
        value = _plain(validate_message(message, direction, binary, persisted=persisted))
        kind = value["type"]
        _require(self._ended is None)
        _require(value["seq"] == self._sequences[direction])
        self._sequences[direction] += 1
        identity = tuple(value[key] for key in ("incarnation", "worker_session", "protocol_sha256"))
        if self._identity is None:
            self._identity = identity
        _require(identity == self._identity)
        if not persisted:
            if self._nonce is None:
                self._nonce = value["launch_nonce"]
            _require(self._nonce == value["launch_nonce"])
        if receipt_ns is not None:
            _int(receipt_ns)
            for key in ("child_ns", "allowed_ns", "started_ns", "completed_ns", "ready_ns", "wall_ns", "wall_start_ns", "wall_completion_ns"):
                if value.get(key) is not None:
                    _require(value[key] <= receipt_ns, "clock")
        if kind == "stop":
            self._phase = "stopping"
            return FrozenRecord(value)
        if kind == "fault":
            _require(value["observations_completed"] == self._completed)
            self._fault = value["code"]
            self._phase = "faulted"
            return FrozenRecord(value)
        if kind == "ended":
            _require(self._phase in ("ending", "stopping", "faulted"))
            _require(value["observations_completed"] == self._completed)
            if self._header is None:
                _require(value["header_sha256"] is None)
            else:
                _require(value["header_sha256"] == canonical_sha256(self._header))
                _require(value["engine_identity_sha256"] == self._header["engine_identity"]["sha256"])
            if value["reason"] == "model_limit":
                _require(self._phase == "ending" and self._fault is None)
            elif value["reason"] == "cancelled":
                _require(self._phase == "stopping" and self._fault is None)
            else:
                _require(value["fault"] == self._fault or self._phase == "stopping")
            if self._previous is not None and value["wall_ns"] is not None:
                _require(value["wall_ns"] >= self._previous["wall_completion_ns"])
            self._ended = value
            self._phase = "ended"
            return FrozenRecord(value)
        if self._phase in ("parent_hello", "worker_hello"):
            expected = "parent" if self._phase == "parent_hello" else "worker"
            _require(kind == "hello" and direction == expected)
            if direction == "parent":
                self._clock = value["parent_clock"]
                self._bindings = value["bindings_sha256"]
                self._phase = "worker_hello"
            else:
                _require(value["worker_clock"] == self._clock and value["bindings_sha256"] == self._bindings)
                self._phase = "challenge"
        elif self._phase == "challenge":
            _require(kind == "challenge" and value["challenge_index"] == self._challenge)
            _require(value["p0_ns"] >= self._last_clock_end, "clock")
            self._challenge_p0 = value["p0_ns"]
            self._phase = "clock"
        elif self._phase == "clock":
            _require(kind == "clock" and value["challenge_index"] == self._challenge and value["p0_ns"] == self._challenge_p0)
            if receipt_ns is not None:
                _require(receipt_ns - self._challenge_p0 < CONSTANTS["monitor_gap_ns"], "clock")
            self._last_clock_end = receipt_ns if receipt_ns is not None else value["child_ns"]
            self._challenge += 1
            self._phase = "initialize" if self._challenge == 3 else "challenge"
        elif self._phase == "initialize":
            _require(kind == "initialize" and value["bindings_sha256"] == self._bindings)
            self._phase = "probe_request"
        elif self._phase == "probe_request":
            _require(kind == "probe_request")
            self._probe_request = value
            self._phase = "probe_allow"
        elif self._phase == "probe_allow":
            _require(kind == "probe_allow" and value["request_seq"] == self._probe_request["seq"])
            self._probe_allow = value["allowed_ns"]
            self._phase = "probe_started"
        elif self._phase == "probe_started":
            _require(kind == "probe_started" and value["allowed_ns"] == self._probe_allow)
            self._probe = value
            self._phase = "probe_finished"
        elif self._phase == "probe_finished":
            _require(kind == "probe_finished" and value["process"] == self._probe["process"] and value["started_ns"] == self._probe["started_ns"])
            self._phase = "header"
        elif self._phase == "header":
            _require(kind == "static_header")
            self._header = value["header"]
            self._phase = "ready"
        elif self._phase == "ready":
            _require(kind == "ready" and value["bindings_sha256"] == self._bindings)
            _require(value["header_sha256"] == canonical_sha256(self._header))
            _require(value["engine_identity_sha256"] == self._header["engine_identity"]["sha256"])
            _require(value["build_sha256"] == canonical_sha256(self._header["engine_identity"]["model_provenance"]["build"]))
            _require(value["ready_ns"] >= self._probe["started_ns"])
            self._ready = value
            self._phase = "release"
        elif self._phase in ("release", "command"):
            _require(kind == ("release" if self._phase == "release" else "ack"))
            _require(value["last_observation_index"] == (self._completed - 1 if self._completed else None))
            _require(value["next_observation_index"] == (self._completed if self._completed < 40 else None))
            if receipt_ns is not None and self._previous is not None:
                _require(receipt_ns < self._previous["wall_completion_ns"] + CONSTANTS["exchange_ns"], "deadline")
            self._issued_ns = receipt_ns
            action = value["action"]
            if action == "end":
                _require(self._completed == 40 and self._permit is None)
                self._phase = "ending"
            elif self._permit is not None:
                _require(action == "continue_image" and value["dispatch_id"] == self._permit["dispatch_id"] and value["exposure_ordinal"] == self._ordinal + 1)
                self._ordinal += 1
                self._phase = "observation"
            elif action == "image":
                _require(self._completed <= 32 and self._dispatches < 5)
                self._permit = value["permit"]
                if receipt_ns is not None:
                    _require(receipt_ns < self._permit["deadline_ns"], "deadline")
                self._ordinal = 0
                self._dispatches += 1
                self._phase = "start"
            else:
                _require(action == "black")
                self._phase = "observation"
        elif self._phase == "start":
            _require(kind == "start")
            start = _plain(validate_start(value["receipt"], self._permit))
            _require(start["first_observation_index"] == self._completed)
            if receipt_ns is not None:
                _require(start["started_ns"] <= receipt_ns)
            self._start = start
            self._phase = "observation"
        elif self._phase == "observation":
            _require(kind == "observation" and value["observation_index"] == self._completed)
            _require((value["input_kind"] == "image") == (self._permit is not None))
            if self._permit is not None:
                _require(value["exposure_ordinal"] == self._ordinal)
                if self._ordinal == 0:
                    _require(value["start_receipt"] == self._start)
            validate_observation(value, binary, self._header, permit=self._permit, previous=self._previous, receipt_ns=receipt_ns)
            if self._issued_ns is not None and receipt_ns is not None:
                _require(self._issued_ns <= value["wall_start_ns"] and receipt_ns < self._issued_ns + CONSTANTS["observe_ns"] + CONSTANTS["exchange_ns"], "deadline")
            self._previous = value
            self._completed += 1
            self._phase = "complete" if self._ordinal == 7 else "command"
        elif self._phase == "complete":
            _require(kind == "complete")
            complete = value["receipt"]
            _require(all(complete[key] == self._permit[key] for key in _TUPLE.split()))
            _require(complete["observation_indices"] == list(range(self._completed - 8, self._completed)))
            _require(complete["completed_ns"] == self._previous["wall_completion_ns"])
            self._processed += 1
            self._permit = self._start = self._ordinal = None
            self._phase = "command"
        else:
            raise ProtocolError()
        return FrozenRecord(value)

    def finish(self, *, complete=True):
        if complete:
            _require(self._ended is not None and self._ended["reason"] == "model_limit")
            _require(self._completed == 40 and self._fault is None)
        return FrozenRecord(dict(observations=self._completed, model_ticks=self._completed * 5000,
                                 image_dispatches=self._dispatches, processed_images=self._processed))


_RECEIPT_FIELDS = (
    "id incarnation source_sha256 encoded_bytes accepted_ns deadline_ns decode_deadline_ns "
    "moderation_deadline_ns status detail frame_sha256 preprocessing_version worker_session "
    "dispatch_id dispatched_ns started_ns first_observation_index completed_ns terminal_ns revision time_uncertain"
)
_REJECTIONS = (
    "decode_failed", "decode_timeout", "moderation_rejected", "moderation_timeout",
    "worker_failed", "worker_outcome_unknown", "session_ended", "clock",
)


def validate_receipt(receipt):
    value = _plain(receipt)
    _keys(value, _RECEIPT_FIELDS)
    for name in ("id", "incarnation"):
        _uuid(value[name])
    _digest(value["source_sha256"])
    _int(value["encoded_bytes"], 1, 2097152)
    for name in ("accepted_ns", "deadline_ns", "decode_deadline_ns", "moderation_deadline_ns"):
        _int(value[name])
    accepted = value["accepted_ns"]
    _require(value["deadline_ns"] == accepted + 300000000000)
    _require(value["decode_deadline_ns"] == accepted + 10000000000)
    _require(value["moderation_deadline_ns"] == accepted + 60000000000)
    for name in ("dispatched_ns", "started_ns", "completed_ns", "terminal_ns"):
        _optional(value[name], _int)
        if value[name] is not None:
            _require(value[name] >= accepted)
    for name in ("worker_session", "dispatch_id"):
        _optional(value[name], _uuid)
    _optional(value["frame_sha256"], _digest)
    _optional(value["preprocessing_version"], lambda v: _literal(v, "market-rgb64/v1"))
    _optional(value["first_observation_index"], lambda v: _int(v, 0, 32))
    _int(value["revision"], 1, 6)
    _bool(value["time_uncertain"])
    _require((value["frame_sha256"] is None) == (value["preprocessing_version"] is None))
    dispatched = value["worker_session"] is not None
    _require(dispatched == (value["dispatch_id"] is not None) == (value["dispatched_ns"] is not None))
    started = value["started_ns"] is not None
    _require(started == (value["first_observation_index"] is not None))
    if dispatched:
        _require(value["frame_sha256"] is not None and value["dispatched_ns"] < value["deadline_ns"])
    if started:
        _require(dispatched and value["dispatched_ns"] <= value["started_ns"] < value["deadline_ns"])
    if value["completed_ns"] is not None:
        _require(started and value["completed_ns"] >= value["started_ns"])
    status, detail = value["status"], value["detail"]
    _literal(status, "accepted", "queued", "processing", "processed", "rejected", "expired")
    terminal = status in ("processed", "rejected", "expired")
    _require(terminal == (value["terminal_ns"] is not None))
    _require(value["time_uncertain"] == (detail == "clock"))
    if status == "accepted":
        _literal(detail, "decoding", "awaiting_approval")
        _require(not dispatched and not started)
        _require((value["frame_sha256"] is None) == (detail == "decoding"))
    elif status == "queued":
        _literal(detail, "ready", "dispatching")
        _require(value["frame_sha256"] is not None and not started and dispatched == (detail == "dispatching"))
    elif status == "processing":
        _literal(detail, "processing")
        _require(started)
    elif status == "processed":
        _literal(detail, "completed")
        _require(value["completed_ns"] is not None and value["completed_ns"] <= value["terminal_ns"])
    elif status == "expired":
        _literal(detail, "ttl_expired")
        _require(value["frame_sha256"] is not None and not dispatched and value["terminal_ns"] >= value["deadline_ns"])
    else:
        _literal(detail, *_REJECTIONS)
        if detail in ("decode_failed", "decode_timeout"):
            _require(value["frame_sha256"] is None and not dispatched)
        if detail in ("moderation_rejected", "moderation_timeout"):
            _require(value["frame_sha256"] is not None and not dispatched)
    if status != "processed":
        _require(value["completed_ns"] is None)
    return FrozenRecord(value)


class ReceiptEvidence:
    """Validates supplied D1 revisions only; never calls or reconstructs D1."""

    def __init__(self):
        self._latest = {}

    def accept(self, receipt):
        value = _plain(validate_receipt(receipt))
        previous = self._latest.get(value["id"])
        if previous is None:
            _require(value["revision"] == 1 and value["status"] == "accepted" and value["detail"] == "decoding", "journal_gap")
            _require(len(self._latest) < 512, "resource")
        else:
            if value["revision"] == previous["revision"]:
                _require(value == previous, "journal_gap")
                return False
            _require(value["revision"] == previous["revision"] + 1, "journal_gap")
            _require(previous["terminal_ns"] is None, "journal_gap")
            for name in ("id", "incarnation", "source_sha256", "encoded_bytes", "accepted_ns", "deadline_ns", "decode_deadline_ns", "moderation_deadline_ns"):
                _require(value[name] == previous[name], "journal_gap")
            for name in ("frame_sha256", "preprocessing_version", "worker_session", "dispatch_id", "dispatched_ns", "started_ns", "first_observation_index"):
                if previous[name] is not None:
                    _require(value[name] == previous[name], "journal_gap")
            allowed = {
                "decoding": ("awaiting_approval", "decode_failed", "decode_timeout"),
                "awaiting_approval": ("ready", "moderation_rejected", "moderation_timeout"),
                "ready": ("dispatching", "ttl_expired"),
                "dispatching": ("processing",), "processing": ("completed",),
            }
            _require(value["detail"] in allowed.get(previous["detail"], ()) + ("worker_failed", "worker_outcome_unknown", "session_ended", "clock"), "journal_gap")
        live = [item for key, item in self._latest.items() if key != value["id"] and item["terminal_ns"] is None]
        if value["terminal_ns"] is None:
            live.append(value)
        _require(sum(item["status"] == "processing" for item in live) <= 1, "journal_gap")
        _require(sum(item["status"] in ("accepted", "queued") for item in live) <= 1, "journal_gap")
        self._latest[value["id"]] = value
        return True

    def snapshot(self):
        return tuple(FrozenRecord(value) for value in self._latest.values())


def _cause(value):
    _keys(value, "operation target_id notice_seq read_pass")
    _literal(value["operation"], "reserve", "cancel_reservation", "admit", "decoded", "decode_failed", "moderate", "dispatch", "started", "complete", "stop", "maintain", "status", "snapshot")
    _optional(value["target_id"], _uuid)
    _optional(value["notice_seq"], lambda v: _int(v, 0, 4095))
    _int(value["read_pass"], 0, 2)


def wire_payload(message, direction, binary=b""):
    value = _plain(validate_message(message, direction, binary))
    _require(value["type"] != "static_header")
    del value["launch_nonce"]
    return FrozenRecord(dict(direction=direction, message=value))


def _event_payload(kind, payload, binary):
    if kind == "binding":
        _keys(payload, "protocol_sha256 bindings_sha256")
        for item in payload.values():
            _digest(item)
    elif kind == "header":
        _keys(payload, "header_sha256 engine_identity_sha256 worker_seq")
        _digest(payload["header_sha256"])
        _digest(payload["engine_identity_sha256"])
        _int(payload["worker_seq"], 0, 4095)
    elif kind == "wire":
        _keys(payload, "direction message")
        validate_message(payload["message"], payload["direction"], binary, persisted=True)
        _require(payload["message"]["type"] != "static_header")
    elif kind == "receipt":
        _keys(payload, "ticket receipt cause")
        _int(payload["ticket"], 1, MAX_J)
        validate_receipt(payload["receipt"])
        _cause(payload["cause"])
    elif kind == "clock_bracket":
        _keys(payload, "index p0_ns child_ns p1_ns")
        _int(payload["index"], 0, 2)
        for key in ("p0_ns", "child_ns", "p1_ns"):
            _int(payload[key])
        _require(payload["p0_ns"] <= payload["child_ns"] <= payload["p1_ns"])
        _require(payload["p1_ns"] - payload["p0_ns"] < 2000000000)
    elif kind == "session_fault":
        _keys(payload, "code cleanup_fault")
        _literal(payload["code"], *FAULTS)
        _optional(payload["cleanup_fault"], lambda v: _literal(v, *FAULTS))
    else:
        raise ProtocolError()
    if kind != "wire":
        _require(not binary)


def make_event(sequence, previous_sha256, recorded_ns, kind, payload, binary=b""):
    row = dict(schema="market-native-event/v1", sequence=sequence, previous_sha256=previous_sha256,
               recorded_ns=recorded_ns, kind=kind, payload=_plain(payload), binary_bytes=len(binary),
               binary_sha256=hashlib.sha256(binary).hexdigest())
    row["sha256"] = hashlib.sha256(b"market-native-event/v1\n" + canonical_bytes(row) + binary).hexdigest()
    validate_event(row, binary)
    return FrozenRecord(row)


def validate_event(row, binary=b""):
    value = _plain(row)
    _keys(value, "schema sequence previous_sha256 recorded_ns kind payload binary_bytes binary_sha256 sha256")
    _literal(value["schema"], "market-native-event/v1")
    _int(value["sequence"], 0, 4095)
    _digest(value["previous_sha256"])
    _optional(value["recorded_ns"], _int)
    _int(value["binary_bytes"], 0, 12800)
    _require(type(binary) is bytes and len(binary) == value["binary_bytes"])
    _digest(value["binary_sha256"])
    _digest(value["sha256"])
    _require(value["binary_sha256"] == hashlib.sha256(binary).hexdigest())
    _event_payload(value["kind"], value["payload"], binary)
    expected = hashlib.sha256(b"market-native-event/v1\n" + canonical_bytes({k: v for k, v in value.items() if k != "sha256"}) + binary).hexdigest()
    _require(value["sha256"] == expected)
    return FrozenRecord(value)


def encode_event(row, binary=b""):
    row = validate_event(row, binary)
    encoded = canonical_bytes(row)
    body = struct.pack("<I", len(encoded)) + encoded + binary
    _require(len(body) <= 65536)
    return struct.pack("<I", len(body)) + body


def _event_iterator(stream):
    count = 0
    total = 0
    previous = ZERO_SHA256
    while True:
        prefix = _read_exact(stream, 4, clean_eof=True)
        if prefix is None:
            _require(count > 0)
            return
        count += 1
        _require(count <= 4096)
        length = struct.unpack("<I", prefix)[0]
        _require(4 < length <= 65536)
        total += length + 4
        _require(total <= 33554432)
        body = _read_exact(stream, length)
        json_length = struct.unpack("<I", body[:4])[0]
        _require(0 < json_length <= length - 4)
        value = parse_json(body[4:4 + json_length], byte_limit=65532)
        _require(canonical_bytes(value) == body[4:4 + json_length])
        binary = body[4 + json_length:]
        row = validate_event(value, binary)
        _require(row.sequence == count - 1 and row.previous_sha256 == previous)
        previous = row.sha256
        yield Frame(row, binary)


def read_events(stream):
    """Consume through EOF; bounded records, including binary, returned detached."""
    return tuple(_event_iterator(stream))


def validate_monitor(row):
    value = _plain(row)
    _keys(value, "schema sequence previous_sha256 sample_ns worker_pid worker_creation_time_100ns worker_rss_bytes worker_peak_rss_bytes probe_pid probe_creation_time_100ns probe_rss_bytes probe_peak_rss_bytes job_process_count job_commit_bytes job_peak_commit_bytes combined_output_bytes evidence_bytes gap_ns fault sha256")
    _literal(value["schema"], "market-native-monitor/v1")
    _int(value["sequence"], 0, 11999)
    for name in ("previous_sha256", "sha256"):
        _digest(value[name])
    _optional(value["sample_ns"], _int)
    _int(value["worker_pid"], 1, 2 ** 32 - 1)
    _int(value["worker_creation_time_100ns"], 0, MAX_U64)
    _optional(value["probe_pid"], lambda v: _int(v, 1, 2 ** 32 - 1))
    _optional(value["probe_creation_time_100ns"], lambda v: _int(v, 0, MAX_U64))
    _require((value["probe_pid"] is None) == (value["probe_creation_time_100ns"] is None))
    for name in ("worker_rss_bytes", "worker_peak_rss_bytes", "probe_rss_bytes", "probe_peak_rss_bytes", "job_commit_bytes", "job_peak_commit_bytes", "combined_output_bytes", "evidence_bytes"):
        _int(value[name], 0, MAX_U64)
    _int(value["job_process_count"], 0, 2)
    _int(value["gap_ns"])
    _optional(value["fault"], lambda v: _literal(v, *FAULTS))
    _require(value["sample_ns"] is not None or value["fault"] == "clock")
    if value["probe_pid"] is None:
        _require(value["probe_rss_bytes"] == 0)
    _require(value["worker_rss_bytes"] <= value["worker_peak_rss_bytes"])
    _require(value["probe_rss_bytes"] <= value["probe_peak_rss_bytes"])
    _require(value["job_commit_bytes"] <= value["job_peak_commit_bytes"])
    _require(value["evidence_bytes"] <= value["combined_output_bytes"])
    if value["fault"] is None:
        _require(value["gap_ns"] < 2000000000)
        _require(value["worker_rss_bytes"] + value["probe_rss_bytes"] <= 4294967296)
        _require(value["job_peak_commit_bytes"] <= 4294967296)
        _require(value["combined_output_bytes"] <= 268435456 and value["evidence_bytes"] <= 67108864)
    expected = hashlib.sha256(b"market-native-monitor/v1\n" + canonical_bytes({k: v for k, v in value.items() if k != "sha256"})).hexdigest()
    _require(value["sha256"] == expected)
    return FrozenRecord(value)


def make_monitor(fields):
    value = _plain(fields)
    _require("sha256" not in value)
    value["sha256"] = hashlib.sha256(b"market-native-monitor/v1\n" + canonical_bytes(value)).hexdigest()
    return validate_monitor(value)


def encode_monitor(row):
    encoded = canonical_bytes(validate_monitor(row))
    _require(len(encoded) <= 2048)
    return struct.pack("<I", len(encoded)) + encoded


def _monitor_iterator(stream):
    count = total = 0
    previous = None
    while True:
        prefix = _read_exact(stream, 4, clean_eof=True)
        if prefix is None:
            _require(count > 0)
            return
        count += 1
        _require(count <= 12000)
        length = struct.unpack("<I", prefix)[0]
        _require(0 < length <= 2048)
        total += length + 4
        _require(total <= 25165824)
        raw = _read_exact(stream, length)
        value = parse_json(raw, byte_limit=2048)
        _require(canonical_bytes(value) == raw)
        row = validate_monitor(value)
        _require(row.sequence == count - 1)
        _require(row.previous_sha256 == (ZERO_SHA256 if previous is None else previous.sha256))
        if previous is None:
            _require(row.gap_ns == 0)
        else:
            if previous.sequence > 0:
                _require(previous.gap_ns >= 100000000 or previous.fault is not None)
            _require((row.worker_pid, row.worker_creation_time_100ns) == (previous.worker_pid, previous.worker_creation_time_100ns))
            for name in ("worker_peak_rss_bytes", "probe_peak_rss_bytes", "job_peak_commit_bytes"):
                _require(row[name] >= previous[name])
            if row.sample_ns is not None and previous.sample_ns is not None:
                _require(row.sample_ns >= previous.sample_ns and row.gap_ns == row.sample_ns - previous.sample_ns)
            else:
                _require(row.fault == "clock")
        previous = row
        yield row


def read_monitors(stream):
    return tuple(_monitor_iterator(stream))


def validate_cleanup(receipt):
    value = _plain(receipt)
    _keys(value, "schema incarnation worker_session requested_ns finished_ns worker_creation worker probe worker_exit_code probe_exit_code worker_exit_confirmed probe_exit_confirmed job_empty_confirmed ipc_handles_closed process_handles_closed job_handle_closed root_lock_closed evidence_files_closed first_fault cleanup_fault outcome")
    _literal(value["schema"], "market-native-cleanup/v1")
    _uuid(value["incarnation"])
    _uuid(value["worker_session"])
    for name in ("requested_ns", "finished_ns"):
        _optional(value[name], _int)
    for name in ("worker", "probe"):
        _optional(value[name], _identity)
    for name in ("worker_exit_code", "probe_exit_code"):
        _optional(value[name], lambda v: _int(v, 0, 2 ** 32 - 1))
    for name in ("first_fault", "cleanup_fault"):
        _optional(value[name], lambda v: _literal(v, *FAULTS))
    for name in ("worker_exit_confirmed", "probe_exit_confirmed", "job_empty_confirmed", "ipc_handles_closed", "process_handles_closed", "job_handle_closed", "root_lock_closed", "evidence_files_closed"):
        _bool(value[name])
    _literal(value["worker_creation"], "not_created", "created_unverified", "verified")
    _literal(value["outcome"], "confirmed", "unconfirmed")
    if value["requested_ns"] is None or value["finished_ns"] is None:
        _require(value["first_fault"] == "clock" or value["cleanup_fault"] == "clock")
    else:
        _require(value["requested_ns"] <= value["finished_ns"])
    if value["worker_creation"] == "not_created":
        _require(value["worker"] is None and value["worker_exit_code"] is None and value["worker_exit_confirmed"] is True)
    elif value["worker_creation"] == "created_unverified":
        _require(value["worker"] is None and value["outcome"] == "unconfirmed")
    else:
        _require(value["worker"] is not None)
        if value["worker_exit_confirmed"]:
            _require(value["worker_exit_code"] is not None)
    if value["probe"] is None:
        _require(value["probe_exit_code"] is None and value["probe_exit_confirmed"] is True)
    elif value["probe_exit_confirmed"]:
        _require(value["probe_exit_code"] is not None)
    if value["outcome"] == "confirmed":
        _require(all(value[name] for name in ("worker_exit_confirmed", "probe_exit_confirmed", "job_empty_confirmed", "ipc_handles_closed", "process_handles_closed", "job_handle_closed", "root_lock_closed", "evidence_files_closed")))
        _require(value["cleanup_fault"] is None)
    _require(len(canonical_bytes(value)) <= 16384)
    return FrozenRecord(value)


def validate_protocol(protocol):
    value = _plain(protocol)
    _keys(value, "schema proof constants preserved_sources application_sources lock_sources package_fingerprint")
    _literal(value["schema"], "market-native-protocol/v1")
    _literal(value["proof"], "bounded-image20s/v1")
    _keys(value["constants"], CONSTANTS)
    for name, expected in CONSTANTS.items():
        _int(value["constants"][name], expected, expected)
    _require(value["preserved_sources"] == dict(PRESERVED_SOURCES))
    for name, expected in (("application_sources", APPLICATION_SOURCES), ("lock_sources", LOCK_SOURCES)):
        _keys(value[name], expected)
        for item in value[name].values():
            _digest(item)
    _literal(value["package_fingerprint"], PACKAGE_FINGERPRINT)
    _require(len(canonical_bytes(value)) <= 1048576)
    return FrozenRecord(value)


def _local_path(value):
    _text(value, 1024)
    drive, tail = ntpath.splitdrive(value)
    _require(len(drive) == 2 and drive[0].isalpha() and drive[1] == ":" and tail.startswith(("/", "\\")))
    _require(not value.startswith(("\\\\", "//")) and "\0" not in value)
    parts = value.replace("/", "\\").split("\\")
    _require(all(part not in (".", "..") and ":" not in part for part in parts[1:]))
    return ntpath.normcase(ntpath.normpath(value))


def _file_binding(value, cap):
    _keys(value, "path bytes sha256 device file_id mtime_ns")
    _local_path(value["path"])
    _int(value["bytes"], 0, cap)
    _digest(value["sha256"])
    _int(value["device"], 0, MAX_U64)
    _int(value["file_id"], 0, MAX_U64)
    _int(value["mtime_ns"])


_ENVIRONMENT_KEYS = (
    "SystemRoot", "WINDIR", "PATH", "TMP", "TEMP", "PYTHONPATH", "PYTHONHASHSEED",
    "PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE", "FLY_CONNECTOME_SIM_DATA", "FLY_CONNECTOME_SIM_CXX",
)


def validate_bindings(bindings, protocol, *, protocol_sha256=None):
    value, protocol = _plain(bindings), _plain(validate_protocol(protocol))
    _keys(value, "schema protocol_sha256 incarnation worker_session project_root work_root decoder_work_root runtime_root files environment python_version compiler_probe native_metadata dependencies package_fingerprint prepared_ns")
    _literal(value["schema"], "market-native-bindings/v1")
    _digest(value["protocol_sha256"])
    _require(value["protocol_sha256"] == (canonical_sha256(protocol) if protocol_sha256 is None else protocol_sha256))
    _uuid(value["incarnation"])
    _uuid(value["worker_session"])
    for name in ("project_root", "work_root", "decoder_work_root", "runtime_root"):
        _local_path(value[name])
    project, runtime = value["project_root"], value["runtime_root"]
    _require(_local_path(value["work_root"]) != _local_path(value["decoder_work_root"]))
    _literal(value["python_version"], "3.12.14")
    _literal(value["package_fingerprint"], PACKAGE_FINGERPRINT)
    _int(value["prepared_ns"])
    declared = {**protocol["preserved_sources"], **protocol["application_sources"], **protocol["lock_sources"]}
    files = value["files"]
    _keys(files, tuple(declared) + TOOL_KEYS + DEPENDENCY_KEYS + RUNTIME_KEYS)
    _require(len(files) <= 128)
    source_bytes = runtime_bytes = 0
    for name, binding in files.items():
        if name in RUNTIME_KEYS:
            cap = 4294967296
            runtime_bytes += binding.get("bytes", 0) if type(binding.get("bytes")) is int else 0
        elif name in ("python_launcher", "worker_exe", "compiler_exe", "native_library"):
            cap = 536870912
        else:
            cap = 1048576
            source_bytes += binding.get("bytes", 0) if type(binding.get("bytes")) is int else 0
        _file_binding(binding, cap)
        if name in declared:
            _require(binding["sha256"] == declared[name])
            _require(_local_path(binding["path"]) == _local_path(ntpath.join(project, name.replace("/", "\\"))))
    _require(source_bytes <= 16777216 and runtime_bytes <= 8589934592)
    fixed_paths = dict(
        python_launcher=ntpath.join(project, ".venv", "Scripts", "python.exe"),
        python_config=ntpath.join(project, ".venv", "pyvenv.cfg"),
        native_library=ntpath.join(runtime, "cache", "physiology-v6", "memory.dll"),
        native_metadata=ntpath.join(runtime, "cache", "physiology-v6", "memory.dll.json"),
        graph=ntpath.join(runtime, "graph.npz"),
        normalized_neurons=ntpath.join(runtime, "normalized", "neurons.feather"),
        **{name: ntpath.join(runtime, name + ".feather") for name in ("annotations", "neurotransmitters", "edges")},
    )
    dependencies = value["dependencies"]
    _keys(dependencies, "site_packages numpy pandas pyarrow")
    site_packages = ntpath.join(project, ".venv", "Lib", "site-packages")
    _require(_local_path(dependencies["site_packages"]) == _local_path(site_packages))
    for name, version in (("numpy", "2.4.6"), ("pandas", "3.0.5"), ("pyarrow", "25.0.1")):
        _literal(dependencies[name], version)
        fixed_paths[name + "_init"] = ntpath.join(site_packages, name, "__init__.py")
        fixed_paths[name + "_metadata"] = ntpath.join(site_packages, name + "-" + version + ".dist-info", "METADATA")
    for name, path in fixed_paths.items():
        _require(_local_path(files[name]["path"]) == _local_path(path))
    environment = value["environment"]
    _keys(environment, _ENVIRONMENT_KEYS)
    for item in environment.values():
        _text(item, 8192)
        _require("\0" not in item)
    _require(len(canonical_bytes(environment)) <= 16384)
    for name, expected in (("PYTHONHASHSEED", "0"), ("PYTHONDONTWRITEBYTECODE", "1"), ("PYTHONNOUSERSITE", "1")):
        _literal(environment[name], expected)
    _require(environment["PYTHONPATH"] == ";".join((project, ntpath.join(project, "src"), site_packages)))
    _require(_local_path(environment["SystemRoot"]) == _local_path(environment["WINDIR"]))
    for name in ("TMP", "TEMP"):
        scratch = _local_path(environment[name])
        _require(scratch.startswith(_local_path(value["work_root"]) + "\\"))
    _require(_local_path(environment["FLY_CONNECTOME_SIM_DATA"]) == _local_path(runtime))
    _require(_local_path(environment["FLY_CONNECTOME_SIM_CXX"]) == _local_path(files["compiler_exe"]["path"]))
    for entry in environment["PATH"].split(";"):
        _local_path(entry)
    probe = value["compiler_probe"]
    _keys(probe, "executable_sha256 argv environment_sha256 expected_version timeout_ns stdout_limit stderr_limit")
    _digest(probe["executable_sha256"])
    _digest(probe["environment_sha256"])
    _array(probe["argv"], 2)
    _require(probe["argv"] == [files["compiler_exe"]["path"], "version"])
    _require(probe["executable_sha256"] == files["compiler_exe"]["sha256"] and probe["environment_sha256"] == canonical_sha256(environment))
    _literal(probe["expected_version"], "0.16.0")
    for name, expected in (("timeout_ns", 5000000000), ("stdout_limit", 4096), ("stderr_limit", 4096)):
        _int(probe[name], expected, expected)
    _native_metadata(value["native_metadata"])
    _require(value["native_metadata"]["binary_sha256"] == files["native_library"]["sha256"])
    _require(len(canonical_bytes(value)) <= 1048576)
    return FrozenRecord(value)


def source_subset(protocol, bindings, protocol_sha256, bindings_sha256):
    """Exact final SourceCheck commitment; excludes five large runtime bindings."""
    protocol, bindings = _plain(protocol), _plain(bindings)
    names = set(protocol["preserved_sources"]) | set(protocol["application_sources"]) | set(protocol["lock_sources"]) | set(TOOL_KEYS) | set(DEPENDENCY_KEYS)
    subset = {name: bindings["files"][name] for name in names}
    subset.update(protocol_sha256=protocol_sha256, bindings_sha256=bindings_sha256)
    return FrozenRecord(dict(file_count=len(subset), bindings_subset_sha256=canonical_sha256(subset)))


def validate_final(final):
    value = _plain(final)
    _keys(value, "schema status verification incarnation worker_session protocol_sha256 bindings_sha256 header_sha256 event_records events_sha256 event_chain_sha256 monitor_records monitor_sha256 monitor_chain_sha256 cleanup_sha256 observations model_ticks image_dispatches processed_images max_monitor_gap_ns peak_worker_rss_bytes peak_probe_rss_bytes peak_job_commit_bytes peak_output_bytes source_unchanged source_check first_fault cleanup_fault")
    _literal(value["schema"], "market-native-final/v1")
    _literal(value["status"], "complete")
    _literal(value["verification"], "integrity-only")
    _uuid(value["incarnation"])
    _uuid(value["worker_session"])
    for name in ("protocol_sha256", "bindings_sha256", "header_sha256", "events_sha256", "event_chain_sha256", "monitor_sha256", "monitor_chain_sha256", "cleanup_sha256"):
        _digest(value[name])
    _int(value["event_records"], 1, 4096)
    _int(value["monitor_records"], 1, 12000)
    _int(value["observations"], 40, 40)
    _int(value["model_ticks"], 200000, 200000)
    _int(value["image_dispatches"], 0, 5)
    _int(value["processed_images"], 0, 5)
    _int(value["max_monitor_gap_ns"], 0, 1999999999)
    for name in ("peak_worker_rss_bytes", "peak_probe_rss_bytes", "peak_job_commit_bytes", "peak_output_bytes"):
        _int(value[name], 0, MAX_U64)
    _require(value["source_unchanged"] is True and value["first_fault"] is None and value["cleanup_fault"] is None)
    source = value["source_check"]
    _keys(source, "scope started_ns finished_ns file_count bindings_subset_sha256 all_match")
    _literal(source["scope"], "prepared-source-lock-tool-cache/v1")
    _int(source["started_ns"])
    _int(source["finished_ns"])
    _int(source["file_count"], 1, 128)
    _digest(source["bindings_subset_sha256"])
    _require(source["all_match"] is True and source["started_ns"] <= source["finished_ns"])
    _require(len(canonical_bytes(value)) <= 16384)
    return FrozenRecord(value)


def _stat_identity(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _ordinary(path):
    info = path.lstat()
    _require(stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return info


def _bounded_file(path, cap, *, binding=None):
    """Read bounded ordinary bytes with before/open/after identity checks."""
    try:
        path = Path(path)
        for parent in path.parents:
            info = parent.lstat()
            _require(not stat.S_ISLNK(info.st_mode))
            _require(not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        before = _ordinary(path)
        _require(0 < before.st_size <= cap)
        with path.open("rb") as stream:
            _require(_stat_identity(before) == _stat_identity(os.fstat(stream.fileno())))
            raw = _read_exact(stream, before.st_size)
            _require(stream.read(1) == b"")
            _require(_stat_identity(before) == _stat_identity(os.fstat(stream.fileno())))
        _require(_stat_identity(before) == _stat_identity(_ordinary(path)))
        if binding is not None:
            binding = _plain(binding)
            _require(_stat_identity(before) == (binding["device"], binding["file_id"], binding["bytes"], binding["mtime_ns"]))
            _require(hashlib.sha256(raw).hexdigest() == binding["sha256"])
        return raw
    except OSError:
        raise ProtocolError("source" if binding is not None else "storage") from None


def _bound_path(declared_path):
    # Kept separate for tests of logical Windows declarations on non-Windows CI.
    # Production always resolves the actual declared path without redirection.
    return Path(declared_path)


class _HashReader:
    def __init__(self, stream, cap):
        self.stream = stream
        self.cap = cap
        self.bytes = 0
        self.digest = hashlib.sha256()

    def read(self, count):
        _require(0 <= count <= 65536)
        raw = self.stream.read(count)
        self.bytes += len(raw)
        _require(self.bytes <= self.cap)
        self.digest.update(raw)
        return raw


def inspect_evidence(root):
    """Validate the complete files through EOF and recompute every final summary.

    Only the two small authenticated source lock files are read outside root.
    No graph/native code is loaded, and current source comparison is not inferred.
    """
    try:
        return _inspect_evidence(Path(root))
    except (OSError, KeyError, TypeError, OverflowError):
        raise ProtocolError("storage") from None


def _inspect_evidence(root):
    _require(root.is_dir() and not root.is_symlink())
    raw_final = _bounded_file(root / "final.json", 16384)
    final = _plain(validate_final(parse_json(raw_final, byte_limit=16384)))
    raws = {"protocol": _bounded_file(root / "protocol.json", 1048576),
            "bindings": _bounded_file(root / "bindings.json", 1048576),
            "header": _bounded_file(root / "header.json", 2097152),
            "cleanup": _bounded_file(root / "cleanup.json", 16384)}
    for name in raws:
        _require(hashlib.sha256(raws[name]).hexdigest() == final[name + "_sha256"])
    protocol = _plain(validate_protocol(parse_json(raws["protocol"], byte_limit=1048576, node_limit=20000)))
    bindings = _plain(validate_bindings(parse_json(raws["bindings"], byte_limit=1048576, node_limit=20000), protocol,
                                        protocol_sha256=final["protocol_sha256"]))
    _require(all(final[name] == bindings[name] for name in ("incarnation", "worker_session")))
    locks = {}
    for name in ("arrays", "sources"):
        key = "src/fly_connectome_sim/neural/" + name + ".lock.json"
        binding = bindings["files"][key]
        _require(binding["sha256"] == protocol["lock_sources"][key])
        locks[name] = parse_json(_bounded_file(_bound_path(binding["path"]), 1048576, binding=binding), byte_limit=1048576, node_limit=20000)
    header = _plain(validate_header(parse_json(raws["header"], byte_limit=2097152, node_limit=40000), bindings=bindings,
                                    arrays_lock=locks["arrays"], sources_lock=locks["sources"]))
    _require(canonical_sha256(header) == final["header_sha256"])
    cleanup = _plain(validate_cleanup(parse_json(raws["cleanup"], byte_limit=16384)))
    _require(cleanup["incarnation"] == final["incarnation"] and cleanup["worker_session"] == final["worker_session"])
    _require(cleanup["outcome"] == "confirmed" and cleanup["worker_creation"] == "verified")
    _require(cleanup["worker_exit_code"] == 0 and cleanup["first_fault"] is None and cleanup["cleanup_fault"] is None)
    _require(cleanup["probe"] is not None and cleanup["probe_exit_code"] == 0)
    _require(cleanup["requested_ns"] is not None and cleanup["finished_ns"] is not None)
    subset = source_subset(protocol, bindings, final["protocol_sha256"], final["bindings_sha256"])
    _require(final["source_check"]["file_count"] == subset.file_count and final["source_check"]["bindings_subset_sha256"] == subset.bindings_subset_sha256)
    deadline = cleanup["requested_ns"] + CONSTANTS["cleanup_ns"]
    _require(deadline <= MAX_NS and cleanup["requested_ns"] <= final["source_check"]["started_ns"] <= final["source_check"]["finished_ns"] <= cleanup["finished_ns"] <= deadline)
    validator = ProtocolValidator()
    receipts = ReceiptEvidence()
    clocks = []
    wire_clocks = []
    pending_start = pending_complete = None
    last_ticket = 0
    ticket_entries = 0
    last_recorded = None
    event_count = 0
    event_last = None
    hello_worker = probe_process = None
    worker_hello_ns = None
    ended_ns = None
    released = False
    event_path = root / "events.bin"
    before = _ordinary(event_path)
    _require(before.st_size <= 33554432)
    with event_path.open("rb") as stream:
        _require(_stat_identity(before) == _stat_identity(os.fstat(stream.fileno())))
        event_reader = _HashReader(stream, 33554432)
        for frame in _event_iterator(event_reader):
            row = frame.message
            event_count += 1
            event_last = row.sha256
            _require(row.recorded_ns is not None)
            _require(last_recorded is None or row.recorded_ns >= last_recorded, "clock")
            last_recorded = row.recorded_ns
            payload = row.payload
            if row.kind == "binding":
                _require(event_count == 1 and payload.protocol_sha256 == final["protocol_sha256"] and payload.bindings_sha256 == final["bindings_sha256"])
            else:
                _require(event_count > 1)
            if row.kind == "header":
                _require(payload.header_sha256 == final["header_sha256"] and payload.engine_identity_sha256 == header["engine_identity"]["sha256"])
                validator.accept_header(header, payload.worker_seq, receipt_ns=row.recorded_ns)
            elif row.kind == "clock_bracket":
                clocks.append(_plain(payload))
                _require(len(clocks) <= 3 and len(clocks) <= len(wire_clocks))
                _require(clocks[-1] == wire_clocks[len(clocks) - 1])
            elif row.kind == "session_fault":
                raise ProtocolError(payload.code)
            elif row.kind == "receipt":
                _require(released)
                _require(payload.receipt.incarnation == final["incarnation"])
                if payload.receipt.worker_session is not None:
                    _require(payload.receipt.worker_session == final["worker_session"])
                _require(payload.ticket >= last_ticket)
                ticket_entries = ticket_entries + 1 if payload.ticket == last_ticket else 1
                _require(ticket_entries <= 3)
                last_ticket = payload.ticket
                changed = receipts.accept(payload.receipt)
                _require(changed, "journal_gap")
                detail = payload.receipt.detail
                if detail == "processing":
                    _require(pending_start is not None)
                    _require(all(payload.receipt[key] == pending_start[key] for key in _TUPLE.split()))
                    _require(payload.receipt.started_ns == pending_start.started_ns and payload.receipt.first_observation_index == pending_start.first_observation_index)
                    pending_start = None
                elif detail == "completed":
                    _require(pending_complete is not None)
                    _require(all(payload.receipt[key] == pending_complete[key] for key in _TUPLE.split()))
                    _require(payload.receipt.completed_ns == pending_complete.completed_ns)
                    pending_complete = None
            elif row.kind == "wire":
                message = payload.message
                _require(all(message[name] == final[name] for name in ("incarnation", "worker_session", "protocol_sha256")))
                if message.type == "hello":
                    _require(message.bindings_sha256 == final["bindings_sha256"])
                    if payload.direction == "worker":
                        hello_worker = message.worker
                        worker_hello_ns = row.recorded_ns
                        _require(hello_worker == cleanup["worker"])
                        worker_binding = bindings["files"]["worker_exe"]
                        _require(_local_path(hello_worker.executable) == _local_path(worker_binding["path"]) and hello_worker.executable_sha256 == worker_binding["sha256"])
                elif message.type == "probe_request":
                    probe = bindings["compiler_probe"]
                    _require(message.compiler_sha256 == probe["executable_sha256"] and message.argv_sha256 == canonical_sha256(probe["argv"]) and message.environment_sha256 == probe["environment_sha256"])
                elif message.type == "probe_started":
                    probe_process = message.process
                    _require(probe_process == cleanup["probe"])
                    probe_binding = bindings["files"]["compiler_exe"]
                    _require(_local_path(probe_process.executable) == _local_path(probe_binding["path"]) and probe_process.executable_sha256 == probe_binding["sha256"])
                elif message.type == "clock":
                    wire_clocks.append(dict(index=message.challenge_index, p0_ns=message.p0_ns, child_ns=message.child_ns, p1_ns=row.recorded_ns))
                elif message.type == "release":
                    released = True
                elif message.type == "ack":
                    _require(pending_start is None and pending_complete is None)
                    _require(not any(r.detail in ("worker_failed", "worker_outcome_unknown", "clock") for r in receipts.snapshot()))
                    if message.action == "image":
                        matches = [r for r in receipts.snapshot() if r.id == message.permit.id]
                        _require(len(matches) == 1 and matches[0].detail == "dispatching")
                        _require(all(matches[0][key] == message.permit[key] for key in _TUPLE.split()))
                        _require(matches[0].deadline_ns == message.permit.deadline_ns)
                elif message.type == "start":
                    pending_start = message.receipt
                elif message.type == "observation":
                    _require(pending_start is None)
                elif message.type == "complete":
                    pending_complete = message.receipt
                elif message.type == "ended":
                    ended_ns = row.recorded_ns
                validator.accept(message, payload.direction, frame.binary, receipt_ns=row.recorded_ns, persisted=True)
        _require(_stat_identity(before) == _stat_identity(os.fstat(stream.fileno())))
    _require(_stat_identity(before) == _stat_identity(_ordinary(event_path)))
    summary = validator.finish()
    validate_clock_brackets(clocks)
    _require(hello_worker is not None and probe_process is not None and ended_ns == cleanup["requested_ns"])
    _require(pending_start is None and pending_complete is None)
    _require(all(receipt.terminal_ns is not None for receipt in receipts.snapshot()))
    for name in ("observations", "model_ticks", "image_dispatches", "processed_images"):
        _require(final[name] == summary[name])
    _require(final["event_records"] == event_count and final["event_chain_sha256"] == event_last and final["events_sha256"] == event_reader.digest.hexdigest())
    monitor_path = root / "monitor.bin"
    before = _ordinary(monitor_path)
    _require(before.st_size <= 25165824)
    monitor_count = max_gap = worker_peak = probe_peak = commit_peak = output_peak = 0
    monitor_last = None
    with monitor_path.open("rb") as stream:
        _require(_stat_identity(before) == _stat_identity(os.fstat(stream.fileno())))
        monitor_reader = _HashReader(stream, 25165824)
        for row in _monitor_iterator(monitor_reader):
            monitor_count += 1
            monitor_last = row.sha256
            _require(row.fault is None and row.sample_ns is not None and row.sample_ns <= cleanup["finished_ns"])
            _require((row.worker_pid, row.worker_creation_time_100ns) == (hello_worker.pid, hello_worker.creation_time_100ns))
            if monitor_count == 1:
                # Earliest evidenced running-worker anchor, not an invented OS
                # resume timestamp. The owner separately monitors from release.
                _require(row.sample_ns <= worker_hello_ns)
                _require(row.job_process_count == 1 and row.probe_pid is None)
            if row.probe_pid is not None:
                _require((row.probe_pid, row.probe_creation_time_100ns) == (probe_process.pid, probe_process.creation_time_100ns))
            max_gap = max(max_gap, row.gap_ns)
            worker_peak = max(worker_peak, row.worker_peak_rss_bytes)
            probe_peak = max(probe_peak, row.probe_peak_rss_bytes)
            commit_peak = max(commit_peak, row.job_peak_commit_bytes)
            output_peak = max(output_peak, row.combined_output_bytes)
        _require(_stat_identity(before) == _stat_identity(os.fstat(stream.fileno())))
    _require(row.job_process_count == 0 and row.worker_rss_bytes == 0 and row.probe_pid is None)
    _require(row.sample_ns >= cleanup["requested_ns"])
    _require(_stat_identity(before) == _stat_identity(_ordinary(monitor_path)))
    expected = dict(monitor_records=monitor_count, monitor_chain_sha256=monitor_last,
                    monitor_sha256=monitor_reader.digest.hexdigest(), max_monitor_gap_ns=max_gap,
                    peak_worker_rss_bytes=worker_peak, peak_probe_rss_bytes=probe_peak,
                    peak_job_commit_bytes=commit_peak, peak_output_bytes=output_peak)
    _require(all(final[name] == item for name, item in expected.items()))
    total_bytes = sum(map(len, raws.values())) + len(raw_final) + event_reader.bytes + monitor_reader.bytes
    _require(total_bytes <= 67108864)
    return FrozenRecord(final)
