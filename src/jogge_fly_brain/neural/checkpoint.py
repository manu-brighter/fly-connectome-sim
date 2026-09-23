"""Validate checkpoint candidates without mutating the live neural state."""

from hashlib import sha256
import json
from pathlib import Path

import numpy as np


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
    if any(metadata[key] != value for key, value in expected.items()):
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
        metadata = json.loads(encoded.item())
        validate_metadata(metadata, expected)
        arrays = {}
        for name, target in templates.items():
            value = archive[name]
            if value.shape != target.shape or value.dtype != target.dtype:
                raise ValueError(f"Checkpoint array mismatch: {name}")
            if value.dtype.kind == "f" and not np.isfinite(value).all():
                raise ValueError(f"Nonfinite checkpoint state: {name}")
            if not target.flags.writeable:
                raise ValueError(f"Checkpoint destination is read-only: {name}")
            arrays[name] = value
        validate_native_state(arrays, n, metadata["cursor"])
    return metadata, arrays
