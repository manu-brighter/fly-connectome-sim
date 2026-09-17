from hashlib import sha256
import json

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pytest

from jogge_fly_brain import data
from jogge_fly_brain.engine import FlyEngine, NeuralGroups
from jogge_fly_brain.neural import common, connectome, visual


@pytest.fixture
def locked_runtime(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    tables = {
        "annotations.feather": {
            "bodyId": [10, 20],
            "superclass": ["central", "descending"],
            "statusLabel": ["Traced", "Traced"],
            "status": ["Neuron", "Neuron"],
            "type": ["KC", "DNa02"],
            "somaSide": ["L", "R"],
        },
        "neurotransmitters.feather": {
            "body": [10, 20],
            "consensus_nt": ["acetylcholine", "gaba"],
        },
        "edges.feather": {
            "body_pre": [10],
            "body_post": [20],
            "weight": [3],
        },
    }
    config = json.loads(connectome.REGISTRY.read_text(encoding="utf-8"))
    urls = config["datasets"]["malecns_v1"]["files"]
    records = {}
    for name, columns in tables.items():
        path = runtime / name
        feather.write_feather(pa.table(columns), path)
        payload = path.read_bytes()
        records[name] = {
            "url": urls[name],
            "bytes": len(payload),
            "sha256": sha256(payload).hexdigest(),
        }
    package = tmp_path / "package" / "neural"
    package.mkdir(parents=True)
    (package / "sources.lock.json").write_text(
        json.dumps(records), encoding="utf-8",
    )
    registry = tmp_path / "datasets.json"
    registry.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(data, "__file__", str(package.parent / "data.py"))
    monkeypatch.setattr(connectome, "DATA", runtime)
    monkeypatch.setattr(connectome, "REGISTRY", registry)
    monkeypatch.setattr(common, "DATA", runtime)
    return runtime, package, records


def test_prepared_verification_rejects_altered_runtime_annotations(locked_runtime):
    runtime, package, _ = locked_runtime
    # Keep the production dimensions while using compressible, synthetic arrays.
    ids = np.arange(166_700, dtype=np.int64)
    post = np.zeros(25_582_938, dtype=np.int8)
    np.savez_compressed(runtime / "graph.npz", ids=ids, post=post)
    (package / "arrays.lock.json").write_text(
        json.dumps({
            "ids": sha256(ids.tobytes()).hexdigest(),
            "post": sha256(post.tobytes()).hexdigest(),
        }),
        encoding="utf-8",
    )
    normalized = runtime / "normalized"
    normalized.mkdir()
    transmitters = [""] * len(ids)
    feather.write_feather(
        pa.table({"source_id": ids, "neurotransmitter": transmitters}),
        normalized / "neurons.feather",
    )
    (package / "neurons.lock.json").write_text(
        json.dumps({
            "neurotransmitter_values_sha256": sha256(
                json.dumps(transmitters, separators=(",", ":")).encode(),
            ).hexdigest(),
        }),
        encoding="utf-8",
    )
    assert data.verify_prepared_graph(runtime)["arrays_verified"] is True
    annotation = runtime / "annotations.feather"
    payload = annotation.read_bytes()
    annotation.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))

    with pytest.raises(data.SourceIntegrityError, match="annotations.feather"):
        data.verify_prepared_graph(runtime)


@pytest.mark.parametrize("changed_field", ["sha256", "bytes", "url", "missing"])
@pytest.mark.parametrize("local_lock", [False, True])
def test_import_rejects_authoritative_mismatch_before_writing_outputs(
    locked_runtime, changed_field, local_lock,
):
    runtime, _, records = locked_runtime
    annotation = runtime / "annotations.feather"
    if changed_field == "sha256":
        # A valid Feather table with the same size, but different laterality.
        table = feather.read_table(annotation).set_column(
            5, "somaSide", pa.array(["R", "L"]),
        )
        feather.write_feather(table, annotation)
        assert annotation.stat().st_size == records[annotation.name]["bytes"]
    elif changed_field == "bytes":
        table = feather.read_table(annotation).replace_schema_metadata(
            {"changed": "metadata"},
        )
        feather.write_feather(table, annotation)
        assert annotation.stat().st_size != records[annotation.name]["bytes"]
    elif changed_field == "url":
        config = json.loads(connectome.REGISTRY.read_text(encoding="utf-8"))
        config["datasets"]["malecns_v1"]["files"][annotation.name] += "?changed"
        connectome.REGISTRY.write_text(json.dumps(config), encoding="utf-8")
    else:
        annotation.unlink()
    if local_lock:
        forged = dict(records)
        if annotation.exists():
            forged[annotation.name] = {
                **records[annotation.name],
                "bytes": annotation.stat().st_size,
                "sha256": sha256(annotation.read_bytes()).hexdigest(),
            }
        (runtime / "source.lock.json").write_text(
            json.dumps(forged), encoding="utf-8",
        )
    before = {path.name: path.read_bytes() for path in runtime.iterdir()}

    with pytest.raises(data.SourceIntegrityError, match="annotations.feather"):
        connectome.import_graph()

    assert {path.name: path.read_bytes() for path in runtime.iterdir()} == before


def test_import_accepts_authoritative_sources_and_writes_derived_audit_lock(
    locked_runtime,
):
    runtime, _, records = locked_runtime

    report = connectome.import_graph()

    assert report["retained_neuron_candidates"] == 2
    assert report["graph"]["retained_edge_rows"] == 1
    assert report["graph"]["retained_synaptic_contacts"] == 3
    assert report["source_hashes"] == records
    assert json.loads((runtime / "source.lock.json").read_text()) == records
    neurons = feather.read_table(runtime / "normalized" / "neurons.feather")
    assert neurons["source_id"].to_pylist() == [10, 20]


@pytest.mark.parametrize(
    "name", ["annotations.feather", "neurotransmitters.feather", "edges.feather"],
)
@pytest.mark.parametrize("missing", [False, True])
def test_runtime_source_gate_checks_every_staged_source(locked_runtime, name, missing):
    runtime, _, records = locked_runtime
    assert data.verify_runtime_sources(runtime) == records
    path = runtime / name
    if missing:
        path.unlink()
    else:
        payload = path.read_bytes()
        path.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))

    with pytest.raises(data.SourceIntegrityError, match=name):
        data.verify_runtime_sources(runtime)


def test_import_rejects_incomplete_source_registry(locked_runtime):
    runtime, _, _ = locked_runtime
    config = json.loads(connectome.REGISTRY.read_text(encoding="utf-8"))
    del config["datasets"]["malecns_v1"]["files"]["annotations.feather"]
    connectome.REGISTRY.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(data.SourceIntegrityError, match="Configured source files"):
        connectome.import_graph()

    assert not (runtime / "normalized").exists()
    assert not (runtime / "source.lock.json").exists()


def test_engine_rejects_corrupt_data_before_constructing_brain(
    locked_runtime, monkeypatch,
):
    runtime, _, _ = locked_runtime
    (runtime / "annotations.feather").write_bytes(b"corrupt")
    constructed = []

    def construct():
        constructed.append(True)
        raise AssertionError("Brain construction must not run on corrupt data")

    monkeypatch.setattr(visual, "VisualMemoryBrain", construct)

    with pytest.raises(data.SourceIntegrityError, match="annotations.feather"):
        FlyEngine.from_prepared_graph()

    assert constructed == []


def test_engine_verifies_configured_runtime_before_constructing_brain(
    tmp_path, monkeypatch,
):
    events = []
    runtime = tmp_path / "configured-runtime"
    monkeypatch.setattr(common, "DATA", runtime)

    def verify(directory):
        assert directory == runtime
        events.append("verified")

    class Brain:
        def __init__(self):
            assert events == ["verified"]
            events.append("constructed")
            self.n = 1

    groups = NeuralGroups(**{
        name: np.array([0]) for name in NeuralGroups.__dataclass_fields__
    })
    monkeypatch.setattr(data, "verify_prepared_graph", verify)
    monkeypatch.setattr(visual, "VisualMemoryBrain", Brain)
    monkeypatch.setattr(NeuralGroups, "from_brain", lambda brain: groups)

    engine = FlyEngine.from_prepared_graph()

    assert isinstance(engine, FlyEngine)
    assert events == ["verified", "constructed"]
