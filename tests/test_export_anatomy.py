"""Synthetic locked projection fixtures; no fullgraph/native evidence."""

from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pytest


def generator():
    path = Path(__file__).resolve().parents[1] / "scripts/export-anatomy.py"
    assert path.is_file(), "The locked soma projection exporter is missing"
    spec = importlib.util.spec_from_file_location("export_anatomy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, *, ids=(103, 101, 102, 104), rows=None, dtype="<i8"):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    rows = rows or [{"bodyId": 101, "somaLocation": [1, 2, 3]},
                    {"bodyId": 102, "somaLocation": None},
                    {"bodyId": 103, "somaLocation": [10, 20, 30]},
                    {"bodyId": 104, "somaLocation": [-4, 5, 6]}]
    feather.write_feather(pa.Table.from_pylist(rows), runtime / "annotations.feather")
    values = np.array(ids, dtype=dtype)
    np.savez(runtime / "graph.npz", ids=values, ignored_large_array=np.zeros(1))
    locks = tmp_path / "locks"
    locks.mkdir()
    annotation = (runtime / "annotations.feather").read_bytes()
    (locks / "sources.lock.json").write_text(json.dumps({"annotations.feather": {
        "bytes": len(annotation), "sha256": sha256(annotation).hexdigest(),
    }}), encoding="utf-8")
    graph_hash = sha256(values.tobytes()).hexdigest()
    (locks / "arrays.lock.json").write_text(json.dumps({"ids": graph_hash}), encoding="utf-8")
    recording = tmp_path / "recording.json"
    recording.write_text(json.dumps({"source": {"metadata": {"engine_identity": {
        "model_provenance": {"graph_ids_sha256": graph_hash},
    }}}}), encoding="utf-8")
    return runtime, recording, locks


def test_joins_by_id_preserves_raw_coordinates_and_missing_coverage(tmp_path):
    args = fixture(tmp_path)
    target = tmp_path / "anatomy.json"
    result = generator().export_anatomy(*args[:2], target, locks_directory=args[2])
    assert result["points"] == [[0, "103", 10, 20, 30], [1, "101", 1, 2, 3], [3, "104", -4, 5, 6]]
    assert result["coverage"] == dict(model_cells=4, positioned_cells=3, missing_positions=1, displayed_cells=3)
    assert result["binding"]["recording_sha256"] == sha256(args[1].read_bytes()).hexdigest()
    assert json.loads(target.read_bytes()) == result
    again = tmp_path / "again.json"
    generator().export_anatomy(*args[:2], again, locks_directory=args[2])
    assert again.read_bytes() == target.read_bytes()


def test_sampling_is_fixed_graph_order_and_capped_at_twelve_thousand(tmp_path):
    size = 12003
    rows = [{"bodyId": index + 1, "somaLocation": [index, 2, 3]} for index in range(size)]
    runtime, recording, locks = fixture(tmp_path, ids=range(1, size + 1), rows=rows)
    result = generator().export_anatomy(runtime, recording, tmp_path / "a.json", locks_directory=locks)
    assert len(result["points"]) == 12000
    assert [point[0] for point in result["points"]] == [index * 12003 // 12000 for index in range(12000)]
    assert result["points"][-1] == [12001, "12002", 12001, 2, 3]


@pytest.mark.parametrize("problem", ["annotation", "graph-binding", "big-endian", "duplicate", "missing", "malformed", "boolean"])
def test_rejects_drift_invalid_ids_and_non_null_positions(tmp_path, problem):
    kwargs = {}
    if problem == "big-endian":
        kwargs["dtype"] = ">i8"
    if problem == "duplicate":
        kwargs["ids"] = (101, 101)
    if problem in {"missing", "malformed", "boolean"}:
        kwargs["rows"] = [{"bodyId": 101, "somaLocation": ([1, 2] if problem == "malformed" else [True, False, True] if problem == "boolean" else [1, 2, 3])}]
    runtime, recording, locks = fixture(tmp_path, **kwargs)
    if problem == "annotation":
        with (runtime / "annotations.feather").open("ab") as stream:
            stream.write(b"drift")
    if problem == "graph-binding":
        recording.write_text(recording.read_text().replace(json.loads((locks / "arrays.lock.json").read_text())["ids"], "0" * 64))
    with pytest.raises(ValueError):
        generator().export_anatomy(runtime, recording, tmp_path / "bad.json", locks_directory=locks)
    assert not (tmp_path / "bad.json").exists()


def test_no_overwrite_and_empty_positions_do_not_invent_points(tmp_path):
    rows = [{"bodyId": index, "somaLocation": None} for index in (101, 102, 103, 104)]
    runtime, recording, locks = fixture(tmp_path, rows=rows)
    target = tmp_path / "a.json"
    result = generator().export_anatomy(runtime, recording, target, locks_directory=locks)
    assert result["points"] == [] and result["coverage"]["missing_positions"] == 4
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        generator().export_anatomy(runtime, recording, target, locks_directory=locks)
    assert target.read_bytes() == before
