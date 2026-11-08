"""Passive cell capture against actual tiny native states and locked sources."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pytest

from fly_connectome_sim.experiment.recorder import _canonical, _scientific
from replay_helpers import map_engine_factory, engine_factory


def test_native_observer_is_detached_and_scientifically_identical(map_engine_factory, tmp_path):
    off = map_engine_factory(tonic=np.array([20, 0, 0, 0, 0, 0, 20, 0], dtype=np.float32))
    on = map_engine_factory(tonic=np.array([20, 0, 0, 0, 0, 0, 20, 0], dtype=np.float32))
    off.identity()
    initial = tmp_path / "initial"
    off.brain.checkpoint(initial)
    on.brain.restore(initial)
    captured = []
    def observe(value):
        captured.append(deepcopy(value))
        value["counts"][0] = 999999
        value["end_tick"] = -1
    on.configure_cell_observer(list(range(8)), observe)
    blue = np.full((8, 8, 3), [0, 0, 255], dtype=np.uint8)
    black = np.zeros_like(blue)
    for frame, duration in [(blue, 33.3), (black, 33.4), (blue, 33.3), (black, 500)]:
        assert _scientific(on.observe(frame, duration)) == _scientific(off.observe(frame, duration))
        assert on.brain.checkpoint_state_sha256() == off.brain.checkpoint_state_sha256()
        assert (on.brain.cursor, on.brain.total_spikes) == (off.brain.cursor, off.brain.total_spikes)
    assert len(captured) == 62
    assert captured[3]["end_tick"] == 333 and captured[7]["end_tick"] == 667
    assert captured[-1]["end_tick"] == 6000
    assert sum(sum(row["counts"]) for row in captured) > 0
    with pytest.raises(ValueError):
        on.configure_cell_observer([0], observe)


def test_observer_failure_stops_and_source_lock_is_not_bypassed(map_engine_factory):
    engine = map_engine_factory()
    def fail(value):
        raise RuntimeError("capture failure")
    engine.configure_cell_observer([0], fail)
    with pytest.raises(RuntimeError, match="capture failure"):
        engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 500)
    assert engine.brain.cursor == 100
    engine = map_engine_factory()
    engine.configure_cell_observer([0], fail)
    engine.identity()
    engine.brain.eta += 0.1
    with pytest.raises(RuntimeError, match="provenance"):
        engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 10)
    assert engine.brain.cursor == 0


@pytest.mark.parametrize("indices", [[True], [0, 0], [-1], [8], [], [0.5]])
def test_invalid_observer_cohort_rejected(map_engine_factory, indices):
    with pytest.raises(ValueError):
        map_engine_factory().configure_cell_observer(indices, lambda value: None)


def test_fixed_selection_and_topology():
    from fly_connectome_sim.experiment.cell_activity import select_cells, select_topology
    ids = np.arange(1000, 1600, dtype=np.int64)[::-1].copy()
    groups = {name: [index] for index, name in enumerate(("pam11", "ppl101", "mbon07", "mbon11", "motor_left", "motor_right"))}
    groups["kc"] = list(range(600))
    cells, selection = select_cells(ids, groups, {int(v): None for v in ids})
    assert len(cells) == 256 and [c["source_id"] for c in cells] == sorted(c["source_id"] for c in cells)
    assert all({"kc", name} <= set(next(c for c in cells if c["model_index"] == groups[name][0])["groups"]) for name in groups if name != "kc")
    remaining = sorted(range(6, 600), key=lambda i: int(ids[i]))
    assert {c["model_index"] for c in cells} == set(range(6)) | {remaining[i * 594 // 250] for i in range(250)}
    assert selection["group_selected_counts"]["kc"] == 256
    groups["pam11"] = list(range(257))
    with pytest.raises(ValueError, match="mandatory"):
        select_cells(ids, groups, {int(v): None for v in ids})
    ids = np.arange(1, 41, dtype=np.int64)
    cells = [{"model_index": i, "source_id": int(v)} for i, v in enumerate(ids)]
    edges = select_topology(ids, np.arange(0, 1601, 40), np.tile(np.arange(40), 40), cells)
    assert edges["eligible_edges"] == 1600 and len(edges["edges"]) == 512
    assert [row[0] for row in edges["edges"]] == [i * 1600 // 512 for i in range(512)]


def locked_runtime(root, engine):
    runtime, locks = root / "runtime", root / "locks"
    runtime.mkdir()
    locks.mkdir()
    brain = engine.brain
    np.savez(runtime / "graph.npz", ids=brain.ids, ptr=brain.ptr, post=brain.post)
    feather.write_feather(pa.table({"bodyId": [int(v) for v in brain.ids],
                                   "somaLocation": pa.array([[i, i + 1, i + 2] if i else None for i in range(brain.n)], type=pa.list_(pa.int64()))}), runtime / "annotations.feather")
    annotation = (runtime / "annotations.feather").read_bytes()
    (locks / "sources.lock.json").write_bytes(_canonical({"annotations.feather": {"bytes": len(annotation), "sha256": sha256(annotation).hexdigest()}}))
    (locks / "arrays.lock.json").write_bytes(_canonical({name: sha256(getattr(brain, name).tobytes()).hexdigest() for name in ("ids", "ptr", "post")}))
    return runtime, locks


@pytest.fixture(scope="module")
def captured_session(tmp_path_factory):
    from fly_connectome_sim.experiment.cell_activity import run_cell_activity_session
    from test_video_observation import playlist
    from test_event_cards import example
    root = tmp_path_factory.mktemp("cell-session")
    factory = engine_factory.__wrapped__(root)
    runtime, locks = locked_runtime(root, factory())
    declaration, _ = playlist(root, count=1, frames=601)
    proposal = root / "proposal.json"
    proposal.write_bytes(_canonical(example()))
    calls = []
    def once():
        calls.append(1)
        return factory()
    result = run_cell_activity_session(root / "capture", playlist_path=declaration, proposal_path=proposal,
                                      runtime_directory=runtime, locks_directory=locks, engine_factory=once)
    assert calls == [1]
    return root / "capture", runtime, locks, result


def test_real_session_raw_binding_and_all_bins(captured_session):
    path, runtime, locks, result = captured_session
    sidecar = json.loads((path / "cell-activity.json").read_bytes())
    recording = json.loads((path / "session/recording.json").read_bytes())
    assert sidecar["binding"]["recording_sha256"] == sha256((path / "session/recording.json").read_bytes()).hexdigest()
    assert sidecar["binding"]["raw_detail_sha256"] == sha256((path / "cell-activity.jsonl").read_bytes()).hexdigest()
    assert len(sidecar["cells"]) == 4 and sidecar["cells"][0]["soma"] is None
    assert sidecar["topology"]["edges"] == [[0, 0, 2], [1, 1, 2]]
    expected = [(o, b, row) for o, segment in enumerate(recording["segments"]) for b, row in enumerate(segment["bins"])]
    assert len(sidecar["bins"]) == len(expected)
    for detail, (observation, bin_index, original) in zip(sidecar["bins"], expected):
        assert detail["observation_index"] == observation and detail["bin_index"] == bin_index
        assert all(type(v) is int and v >= 0 for v in detail["counts"])
        for name, total in original["group_spikes"].items():
            assert sum(detail["counts"][slot] for slot, cell in enumerate(sidecar["cells"]) if name in cell["groups"]) == total
    assert any(0 in row["counts"] for row in sidecar["bins"])
    assert sidecar["bins"][-1]["end_tick"] == recording["duration_ticks"] == 60000
    assert result["session"]["status"] == "complete"


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "bool", "bound", "group", "gap", "unknown", "cell", "edge", "source"])
def test_independent_export_rejects_tampering(captured_session, tmp_path, mutation):
    from fly_connectome_sim.experiment.cell_activity import export_cell_activity
    path, runtime, locks, _ = captured_session
    lines = [json.loads(line) for line in (path / "cell-activity.jsonl").read_bytes().splitlines()]
    if mutation == "missing": lines.pop()
    elif mutation == "duplicate": lines.insert(2, deepcopy(lines[1]))
    elif mutation == "bool": lines[1]["counts"][0] = True
    elif mutation == "bound": lines[1]["counts"][0] = 101
    elif mutation == "group": lines[1]["counts"][0] = 1
    elif mutation == "gap": lines[1]["start_tick"] += 1
    elif mutation == "unknown": lines[1]["invented"] = 0
    elif mutation == "cell": lines[0]["cells"][0]["source_id"] = 999
    elif mutation == "edge": lines[0]["topology"]["edges"][0][1] = 3
    elif mutation == "source": lines[0]["source"]["annotations_sha256"] = "0" * 64
    raw = tmp_path / "raw.jsonl"
    raw.write_bytes(b"".join(_canonical(line) + b"\n" for line in lines))
    with pytest.raises(ValueError):
        export_cell_activity(raw, path / "session/recording.json", tmp_path / "sidecar.json", runtime_directory=runtime, locks_directory=locks)
    assert not (tmp_path / "sidecar.json").exists()


def test_capture_budgets_and_exclusive_outputs(map_engine_factory, tmp_path):
    from fly_connectome_sim.experiment.cell_activity import CellActivityWriter, build_header
    engine = map_engine_factory()
    runtime, locks = locked_runtime(tmp_path, engine)
    header = build_header(engine.identity(), runtime, locks_directory=locks)
    path = tmp_path / "raw.jsonl"
    with pytest.raises(ValueError, match="budget"):
        CellActivityWriter(path, header, detail_budget=10)
    assert not path.exists()
    writer = CellActivityWriter(path, header, max_bins=1)
    row = {"observation_index": 0, "bin_index": 0, "start_tick": 0, "end_tick": 100, "counts": [0] * 8}
    writer(row)
    with pytest.raises(ValueError, match="bin"):
        writer({**row, "bin_index": 1, "start_tick": 100, "end_tick": 200})
    writer.close()
    assert len(path.read_bytes().splitlines()) == 2
    with pytest.raises(FileExistsError):
        CellActivityWriter(path, header)


def test_writer_rejects_oversized_observation_before_append(map_engine_factory, tmp_path):
    from fly_connectome_sim.experiment.cell_activity import CellActivityWriter, build_header
    engine = map_engine_factory()
    runtime, locks = locked_runtime(tmp_path, engine)
    writer = CellActivityWriter(tmp_path / "raw.jsonl", build_header(engine.identity(), runtime, locks_directory=locks))
    for index in range(50):
        writer({"observation_index": 0, "bin_index": index, "start_tick": index * 100,
                "end_tick": (index + 1) * 100, "counts": [0] * 8})
    before = (tmp_path / "raw.jsonl").read_bytes()
    with pytest.raises(ValueError):
        writer({"observation_index": 0, "bin_index": 50, "start_tick": 5000, "end_tick": 5100, "counts": [0] * 8})
    writer.close()
    assert (tmp_path / "raw.jsonl").read_bytes() == before


def test_combined_byte_budget_and_cross_window_reject_before_append(map_engine_factory, tmp_path):
    from fly_connectome_sim.experiment.cell_activity import CellActivityWriter, build_header
    engine = map_engine_factory()
    runtime, locks = locked_runtime(tmp_path, engine)
    header = build_header(engine.identity(), runtime, locks_directory=locks)
    probe = CellActivityWriter(tmp_path / "probe.jsonl", header)
    budget = probe.raw_size + probe.export_size + 1
    probe.close()
    path = tmp_path / "bounded.jsonl"
    writer = CellActivityWriter(path, header, detail_budget=budget)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="budget"):
        writer({"observation_index": 0, "bin_index": 0, "start_tick": 0, "end_tick": 100, "counts": [0] * 8})
    writer.close()
    assert path.read_bytes() == before
    writer = CellActivityWriter(tmp_path / "crossing.jsonl", header)
    for index in range(10):
        writer({"observation_index": 0, "bin_index": index, "start_tick": index * 99,
                "end_tick": (index + 1) * 99, "counts": [0] * 8})
    before = (tmp_path / "crossing.jsonl").read_bytes()
    with pytest.raises(ValueError, match="window"):
        writer({"observation_index": 0, "bin_index": 10, "start_tick": 990, "end_tick": 1090, "counts": [0] * 8})
    writer.close()
    assert (tmp_path / "crossing.jsonl").read_bytes() == before


def test_export_no_overwrite_duplicate_fields_and_incomplete_raw(captured_session, tmp_path):
    from fly_connectome_sim.experiment.cell_activity import export_cell_activity
    path, runtime, locks, _ = captured_session
    raw = path / "cell-activity.jsonl"
    output = tmp_path / "sidecar.json"
    output.write_bytes(b"preserve")
    with pytest.raises(FileExistsError):
        export_cell_activity(raw, path / "session/recording.json", output, runtime_directory=runtime, locks_directory=locks)
    assert output.read_bytes() == b"preserve"
    for label, data in [("truncated", raw.read_bytes()[:-1]),
                        ("duplicate", raw.read_bytes().replace(b'"type":"bin"', b'"type":"bin","type":"bin"', 1))]:
        bad = tmp_path / (label + ".jsonl")
        bad.write_bytes(data)
        with pytest.raises(ValueError):
            export_cell_activity(bad, path / "session/recording.json", tmp_path / (label + ".json"),
                                 runtime_directory=runtime, locks_directory=locks)


def test_export_rejects_alternate_recording_in_valid_bundle(captured_session, tmp_path):
    from fly_connectome_sim.experiment.cell_activity import export_cell_activity
    path, runtime, locks, _ = captured_session
    alternate = path / "session/forged.json"
    alternate.write_bytes((path / "session/recording.json").read_bytes())
    try:
        with pytest.raises(ValueError, match="recording.json"):
            export_cell_activity(path / "cell-activity.jsonl", alternate, tmp_path / "sidecar.json",
                                 runtime_directory=runtime, locks_directory=locks)
        assert not (tmp_path / "sidecar.json").exists()
    finally:
        alternate.unlink()


def test_export_binds_bytes_actually_inspected(captured_session, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment.cell_activity import export_cell_activity
    from fly_connectome_sim.experiment import session_workflow
    path, runtime, locks, _ = captured_session
    recording = path / "session/recording.json"
    original_bytes = recording.read_bytes()
    original_read = session_workflow._read
    def replace_after_recording_read(member, limit):
        raw = original_read(member, limit)
        if member.name == "plan.json":
            # Inspection has already read the canonical recording. The later
            # exporter read sees different, still parseable JSON bytes.
            recording.write_bytes(original_bytes + b" ")
        return raw
    monkeypatch.setattr(session_workflow, "_read", replace_after_recording_read)
    try:
        with pytest.raises(ValueError, match="inspected"):
            export_cell_activity(path / "cell-activity.jsonl", recording, tmp_path / "sidecar.json",
                                 runtime_directory=runtime, locks_directory=locks)
        assert not (tmp_path / "sidecar.json").exists()
    finally:
        recording.write_bytes(original_bytes)


@pytest.mark.parametrize("alias", ["recording", "bundle"])
def test_export_rejects_recording_or_parent_symlink(captured_session, tmp_path, alias):
    from fly_connectome_sim.experiment.cell_activity import export_cell_activity
    path, runtime, locks, _ = captured_session
    bundle = Path(shutil.copytree(path / "session", tmp_path / "bundle"))
    recording = bundle / "recording.json"
    try:
        if alias == "recording":
            original = bundle / "original.json"
            recording.rename(original)
            recording.symlink_to(original)
        else:
            linked = tmp_path / "linked-bundle"
            linked.symlink_to(bundle, target_is_directory=True)
            recording = linked / "recording.json"
    except OSError as error:
        if error.errno in {1, 13} or getattr(error, "winerror", None) in {5, 1314}:
            pytest.skip("Symlink creation unavailable in this environment")
        raise
    with pytest.raises(ValueError, match="symlink or junction"):
        export_cell_activity(path / "cell-activity.jsonl", recording, tmp_path / "sidecar.json",
                             runtime_directory=runtime, locks_directory=locks)
    assert not (tmp_path / "sidecar.json").exists()


def test_callback_error_retains_incomplete_session_without_retry(engine_factory, tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import cell_activity as capture
    runtime, locks = locked_runtime(tmp_path, engine_factory())
    calls = []
    def session(target, **kwargs):
        engine = kwargs["engine_factory"]()
        calls.append(1)
        Path(target).mkdir()
        engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 10)
        raise RuntimeError("declared session failure")
    monkeypatch.setattr(capture, "run_session", session)
    with pytest.raises(RuntimeError, match="declared session failure"):
        capture.run_cell_activity_session(tmp_path / "capture", playlist_path="unused", proposal_path="unused",
                                          runtime_directory=runtime, locks_directory=locks, engine_factory=engine_factory)
    assert calls == [1]
    assert len((tmp_path / "capture/cell-activity.jsonl").read_bytes().splitlines()) == 2
    assert not (tmp_path / "capture/cell-activity.json").exists()


@pytest.mark.parametrize("mutation", ["position", "ids", "ptr", "post"])
def test_locked_source_changes_rejected(map_engine_factory, tmp_path, mutation):
    from fly_connectome_sim.experiment.cell_activity import build_header
    engine = map_engine_factory()
    runtime, locks = locked_runtime(tmp_path, engine)
    identity = engine.identity()
    if mutation == "position":
        annotation = runtime / "annotations.feather"
        rows = feather.read_table(annotation).to_pylist()
        rows[1]["somaLocation"][0] += 1
        feather.write_feather(pa.Table.from_pylist(rows), annotation)
    else:
        with np.load(runtime / "graph.npz") as graph:
            arrays = {name: graph[name] for name in graph.files}
        arrays[mutation][0] += 1
        np.savez(runtime / "graph.npz", **arrays)
    with pytest.raises(ValueError):
        build_header(identity, runtime, locks_directory=locks)
