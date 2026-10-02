"""Validate checkpoint candidates without mutating the live neural state."""

from hashlib import sha256
import json
import math
from pathlib import Path
import struct

import numpy as np


STATE_HASH_DOMAIN = b"fly-connectome-checkpoint-state/v1\0"
HASH_CHUNK_BYTES = 1024 * 1024


def _validate_json(value):
    """Require JSON types without json.dumps' implicit key/scalar coercions."""
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError("Checkpoint JSON keys must be strings")
            _validate_json(item)
    elif type(value) is list:
        for item in value:
            _validate_json(item)
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Nonfinite checkpoint metadata")
    elif type(value) not in (str, int, bool, type(None)):
        raise ValueError("Unsupported checkpoint JSON value")


def _canonical_json(value):
    try:
        _validate_json(value)
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ValueError("Invalid checkpoint JSON encoding") from error


def _strict_metadata_json(encoded):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate checkpoint metadata key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Nonfinite checkpoint metadata: {value}")

    metadata = json.loads(
        encoded, object_pairs_hook=object_pairs, parse_constant=reject_constant,
    )
    _canonical_json(metadata)  # Also rejects overflowing JSON floats and surrogates.
    return metadata


def _validate_chunk_bytes(chunk_bytes):
    # Eight bytes accommodate every supported scalar and each framing length.
    if (type(chunk_bytes) is not int
            or not 8 <= chunk_bytes <= np.iinfo(np.intp).max):
        raise ValueError("chunk_bytes must be an integer from 8 to the native size limit")


def _array_chunks(value, chunk_bytes, *, canonical=False):
    """Iterate logical C order with bounded contiguous conversion buffers."""
    dtype = value.dtype.newbyteorder("<") if canonical else value.dtype
    with np.nditer(
        value, flags=["external_loop", "buffered", "zerosize_ok"],
        op_flags=[["readonly", "contig"]], op_dtypes=[dtype], casting="equiv",
        order="C", buffersize=max(1, chunk_bytes // dtype.itemsize),
    ) as iterator:
        yield from iterator


def _update_bytes(hasher, data, chunk_bytes):
    view = memoryview(data).cast("B")
    for start in range(0, len(view), chunk_bytes):
        hasher.update(view[start:start + chunk_bytes])


def raw_array_sha256(value, *, chunk_bytes=HASH_CHUNK_BYTES):
    """Existing array.tobytes() identity, streamed; preserve stored byte order."""
    _validate_chunk_bytes(chunk_bytes)
    if not isinstance(value, np.ndarray) or value.dtype.hasobject:
        raise ValueError("Raw array hash requires a non-object ndarray")
    hasher = sha256()
    for chunk in _array_chunks(value, chunk_bytes):
        _update_bytes(hasher, chunk, chunk_bytes)
    return hasher.hexdigest()


def checkpoint_state_sha256(metadata, arrays, *, chunk_bytes=HASH_CHUNK_BYTES):
    """Hash quiescent borrowed state; model/schema authenticity is caller-owned.

    v1 uses unsigned little-endian 64-bit lengths: domain, M/JSON-length/JSON,
    array-count, then sorted A/header-length/JSON-header/byte-length/C-data.
    JSON uses sorted string keys, compact separators and unescaped UTF-8.
    Supported scalars: signed/unsigned integers of 1/2/4/8 bytes and IEEE
    floats of 4/8 bytes. Multi-byte data is little endian; one-byte data is
    endian independent. No scalar coercion or cross-build replay is promised.
    """
    _validate_chunk_bytes(chunk_bytes)
    if type(metadata) is not dict:
        raise ValueError("Checkpoint metadata must be an object")
    if type(arrays) is not dict or any(type(name) is not str for name in arrays):
        raise ValueError("Checkpoint arrays require string names")
    encoded = _canonical_json(metadata)
    hasher = sha256()
    for data in (STATE_HASH_DOMAIN, b"M", struct.pack("<Q", len(encoded)), encoded,
                 struct.pack("<Q", len(arrays))):
        _update_bytes(hasher, data, chunk_bytes)
    for name in sorted(arrays):
        value = arrays[name]
        if not isinstance(value, np.ndarray):
            raise ValueError(f"Checkpoint state must be an ndarray: {name}")
        dtype = value.dtype
        if not (
            dtype.fields is None and dtype.subdtype is None
            and ((dtype.kind in "iu" and dtype.itemsize in (1, 2, 4, 8))
                 or (dtype.kind == "f" and dtype.itemsize in (4, 8)))
        ):
            raise ValueError(f"Unsupported checkpoint dtype: {name}")
        header = _canonical_json({
            "name": name, "kind": dtype.kind, "itemsize": dtype.itemsize,
            "byteorder": "independent" if dtype.itemsize == 1 else "little",
            "rank": value.ndim, "shape": list(value.shape), "nbytes": value.nbytes,
        })
        for data in (b"A", struct.pack("<Q", len(header)), header,
                     struct.pack("<Q", value.nbytes)):
            _update_bytes(hasher, data, chunk_bytes)
        for chunk in _array_chunks(value, chunk_bytes, canonical=True):
            if dtype.kind == "f" and not np.isfinite(chunk).all():
                raise ValueError(f"Nonfinite checkpoint state: {name}")
            _update_bytes(hasher, chunk, chunk_bytes)
    return hasher.hexdigest()


def model_fingerprint(root=None):
    """Hash exact project source bytes with portable, deterministic names."""
    root = Path(__file__).parents[1] if root is None else Path(root)
    sources = {
        path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".cpp"}
    }
    identity = {"version": "model-source/v1", "sources_sha256": sources}
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**identity, "sha256": sha256(encoded).hexdigest()}


def validate_metadata(metadata, expected):
    state_fields = {"cursor", "total_spikes", "weights_frozen"}
    if not isinstance(metadata, dict) or set(metadata) != set(expected) | state_fields:
        raise ValueError("Checkpoint metadata fields mismatch")
    if _canonical_json({key: metadata[key] for key in expected}) != _canonical_json(expected):
        raise ValueError("Checkpoint provenance mismatch")
    for key in ["cursor", "total_spikes"]:
        value = metadata[key]
        if type(value) is not int or not 0 <= value <= np.iinfo(np.int64).max:
            raise ValueError(f"Invalid checkpoint {key}")
    if type(metadata["weights_frozen"]) is not bool:
        raise ValueError("Checkpoint weights_frozen must be a boolean")


def validate_native_state(arrays, n, cursor):
    nactive = int(arrays["nactive"][0])
    if not 0 <= nactive <= n:
        raise ValueError("Checkpoint active count out of bounds")
    active = arrays["active"][:nactive]
    flags = arrays["active_flag"]
    if (
        np.any(active < 0)
        or np.any(active >= n)
        or len(np.unique(active)) != nactive
        or np.any(flags > 1)
        or np.count_nonzero(flags) != nactive
        or np.any(flags[active] != 1)
    ):
        raise ValueError("Checkpoint active indices/flags mismatch")

    queue_counts = arrays["queue_count"]
    if np.any(queue_counts < 0) or np.any(queue_counts > n):
        raise ValueError("Checkpoint queue count out of bounds")
    delay = len(queue_counts) - 1
    if cursor > np.iinfo(np.int64).max - delay:
        raise ValueError("Checkpoint cursor leaves no room for native delay")
    # This slot was drained on the previous tick. Native code appends up to n
    # spikes here before draining the current slot; any old entries are unsafe.
    if queue_counts[(cursor + delay) % len(queue_counts)] != 0:
        raise ValueError("Checkpoint next queue write slot must be empty")
    for row, count in zip(arrays["queue"], queue_counts):
        queued = row[:count]
        if np.any(queued < 0) or np.any(queued >= n):
            raise ValueError("Checkpoint queued index out of bounds")

    for name in ["refractory", "counts"]:
        if np.any(arrays[name] < 0):
            raise ValueError(f"Negative checkpoint {name}")
    # last starts at -1: lazy evolution at clock 0 has not visited any cell.
    # Trace timestamps start at 0, even before the first integration tick.
    for name, earliest in [
        ("last", -1),
        ("eligibility_last", 0),
        ("modulation_last", 0),
    ]:
        latest = max(earliest, cursor - 1)
        if np.any(arrays[name] < earliest) or np.any(arrays[name] > latest):
            raise ValueError(f"Checkpoint {name} is outside elapsed neural time")


def load_checkpoint(path, expected, templates, n):
    """Read once and validate everything before the caller commits any state."""
    with np.load(path, allow_pickle=False) as archive:
        fields = {"metadata", *templates}
        if set(archive.files) != fields or len(archive.files) != len(fields):
            raise ValueError("Checkpoint array fields mismatch")
        encoded = archive["metadata"]
        if encoded.shape != () or encoded.dtype.kind != "U":
            raise ValueError("Checkpoint metadata must be a JSON string scalar")
        metadata = _strict_metadata_json(encoded.item())
        validate_metadata(metadata, expected)
        arrays = {}
        for name, target in templates.items():
            value = archive[name]
            if value.shape != target.shape or value.dtype != target.dtype:
                raise ValueError(f"Checkpoint array mismatch: {name}")
            if value.dtype.kind == "f":
                for chunk in _array_chunks(value, HASH_CHUNK_BYTES):
                    if not np.isfinite(chunk).all():
                        raise ValueError(f"Nonfinite checkpoint state: {name}")
            if not target.flags.writeable:
                raise ValueError(f"Checkpoint destination is read-only: {name}")
            arrays[name] = value
        validate_native_state(arrays, n, metadata["cursor"])
    return metadata, arrays
