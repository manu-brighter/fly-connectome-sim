"""Export a bounded static soma projection, separate from neural recordings."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pyarrow.feather as feather


LOCKS = Path(__file__).resolve().parents[1] / "src/fly_connectome_sim/neural"
LIMIT = 12000
SAFE_INTEGER = 9007199254740991


def file_hash(path):
    result = sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def graph_ids(path):
    with np.load(path, allow_pickle=False) as graph:
        ids = graph["ids"]
    if (ids.ndim != 1 or ids.dtype.str != "<i8" or not len(ids)
            or np.any(ids <= 0) or len(np.unique(ids)) != len(ids)):
        raise ValueError("Graph IDs require unique positive little-endian int64 values")
    return ids


def export_anatomy(runtime_directory, recording_path, output_path, *, locks_directory=LOCKS):
    """Verify used locked inputs and preserve their graph-ordered raw positions.

    The optional locks directory supports explicit synthetic test declarations;
    the CLI always uses the repository's existing source/array locks.
    """
    runtime, recording, output = Path(runtime_directory), Path(recording_path), Path(output_path)
    if output.exists():
        raise FileExistsError(output)
    locks = Path(locks_directory)
    source = json.loads((locks / "sources.lock.json").read_bytes())["annotations.feather"]
    expected_ids = json.loads((locks / "arrays.lock.json").read_bytes())["ids"]
    annotation = runtime / "annotations.feather"
    if annotation.stat().st_size != source["bytes"] or file_hash(annotation) != source["sha256"]:
        raise ValueError("Locked annotation size/hash differs")
    if not 0 < recording.stat().st_size <= 32 * 1024 * 1024:
        raise ValueError("Recording exceeds 32 MiB or is empty")
    raw_recording = recording.read_bytes()
    recording_hash = sha256(raw_recording).hexdigest()
    declaration = json.loads(raw_recording)
    binding = declaration["source"]["metadata"]["engine_identity"]["model_provenance"]["graph_ids_sha256"]
    ids = graph_ids(runtime / "graph.npz")
    if sha256(ids.tobytes()).hexdigest() != expected_ids or binding != expected_ids:
        raise ValueError("Locked graph-ID hash/recording binding differs")
    rows = feather.read_table(annotation, columns=["bodyId", "somaLocation"]).to_pylist()
    positions = {}
    for row in rows:
        source_id, position = row["bodyId"], row["somaLocation"]
        if type(source_id) is not int or source_id <= 0 or source_id in positions:
            raise ValueError("Duplicate or invalid annotation bodyId")
        if position is not None and (type(position) is not list or len(position) != 3
                                     or any(type(value) is not int or abs(value) > SAFE_INTEGER for value in position)):
            raise ValueError("Non-null somaLocation must contain exactly three safe integer coordinates")
        positions[source_id] = position
    located = []
    for index, value in enumerate(ids):
        source_id = int(value)
        if source_id not in positions:
            raise ValueError("Model ID has no annotation row")
        position = positions[source_id]
        if position is not None:
            located.append([index, str(source_id), *position])
    count = min(len(located), LIMIT)
    points = [located[index * len(located) // count] for index in range(count)]
    result = {
        "version": "replay-soma-anatomy/v1",
        "source": {"release": "MaleCNS v1.0", "annotations_sha256": source["sha256"], "coordinate_field": "somaLocation"},
        "binding": {"recording_sha256": recording_hash, "graph_ids_sha256": expected_ids},
        "coverage": {"model_cells": len(ids), "positioned_cells": len(located),
                     "missing_positions": len(ids) - len(located), "displayed_cells": count},
        "sampling": {"method": "ordered-position-stride/v1", "limit": LIMIT},
        "points": points,
    }
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    if len(encoded) > 8 * 1024 * 1024:
        raise ValueError("Anatomy output exceeds 8 MiB")
    if (annotation.stat().st_size != source["bytes"] or file_hash(annotation) != source["sha256"]
            or sha256(graph_ids(runtime / "graph.npz").tobytes()).hexdigest() != expected_ids
            or file_hash(recording) != recording_hash):
        raise ValueError("Used source bytes changed before publication")
    with output.open("xb") as stream:
        stream.write(encoded)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime-directory", "recording", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = export_anatomy(args.runtime_directory, args.recording, args.output)
    print(json.dumps({"path": str(args.output), "coverage": result["coverage"]}))


if __name__ == "__main__":
    main()
