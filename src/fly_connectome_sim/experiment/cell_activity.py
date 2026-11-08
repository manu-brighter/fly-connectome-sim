"""Bounded passive cell counts composed with the ordinary continuous session.

Counts belong to original native bins. Connections are static model topology,
not measured transmission. Partial raw output never declares completion.
"""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path

import numpy as np
import pyarrow.feather as feather

from ..engine import FlyEngine
from ..neural.checkpoint import raw_array_sha256
from .recorder import _canonical, _strict_load
from .session_workflow import _inspect as _inspect_session, _safe_path, run_session


LOCKS = Path(__file__).resolve().parents[1] / "neural"
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
DETAIL_BUDGET = 16 * 1024 * 1024
MAX_BINS = 1160
BIN_FIELDS = {"observation_index", "bin_index", "start_tick", "end_tick", "counts"}
SAFE_INTEGER = 9007199254740991


def _hash_file(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _read(path, limit):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError("Empty input or byte budget exceeded")
    return raw


def _integer(value, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError("Invalid integer or range")
    return value


def _stride(values, limit):
    count = min(len(values), limit)
    return [values[i * len(values) // count] for i in range(count)]


def select_cells(ids, groups, positions):
    """Select mandatory populations, then source-ID-ordered KC stride."""
    if set(groups) != set(GROUPS):
        raise ValueError("Invalid neural groups")
    memberships = {}
    for name in GROUPS:
        values = groups[name]
        if (not isinstance(values, list) or not values or len(set(values)) != len(values)):
            raise ValueError("Invalid group indices")
        for index in values:
            _integer(index, 0, len(ids) - 1)
            memberships.setdefault(index, []).append(name)
    mandatory = {index for name in GROUPS if name != "kc" for index in groups[name]}
    if len(mandatory) > 256:
        raise ValueError("The mandatory cohort exceeds 256 cells")
    remaining = sorted(set(groups["kc"]) - mandatory, key=lambda i: int(ids[i]))
    chosen = sorted(mandatory | set(_stride(remaining, 256 - len(mandatory))), key=lambda i: int(ids[i]))
    cells = [{"model_index": i, "source_id": int(ids[i]), "groups": memberships[i],
              "soma": positions[int(ids[i])]} for i in chosen]
    selection = {"method": "mandatory-groups-kc-stride/v1", "limit": 256,
                 "group_population_counts": {name: len(groups[name]) for name in GROUPS},
                 "group_selected_counts": {name: sum(name in c["groups"] for c in cells) for name in GROUPS}}
    return cells, selection


def select_topology(ids, ptr, post, cells):
    slots = {cell["model_index"]: slot for slot, cell in enumerate(cells)}
    eligible = []
    for pre, source_slot in slots.items():
        for edge in range(int(ptr[pre]), int(ptr[pre + 1])):
            target = int(post[edge])
            if target in slots:
                eligible.append((int(ids[pre]), int(ids[target]), edge, source_slot, slots[target]))
    eligible.sort()
    return {"method": "induced-directed-edge-stride/v1", "limit": 512,
            "eligible_edges": len(eligible),
            "edges": [[edge, source, target] for _, _, edge, source, target in _stride(eligible, 512)]}


def build_header(identity, runtime_directory, *, locks_directory=LOCKS):
    """Rejoin locked arrays/annotations without constructing another engine."""
    runtime, locks = Path(runtime_directory), Path(locks_directory)
    declaration = _strict_load(_canonical(identity))
    identity_payload = {key: value for key, value in declaration.items() if key != "sha256"}
    if declaration["sha256"] != sha256(_canonical(identity_payload)).hexdigest():
        raise ValueError("Engine identity hash differs")
    expected = _strict_load((locks / "arrays.lock.json").read_bytes())
    annotation_lock = _strict_load((locks / "sources.lock.json").read_bytes())["annotations.feather"]
    annotation = runtime / "annotations.feather"
    if (annotation.stat().st_size != annotation_lock["bytes"]
            or _hash_file(annotation) != annotation_lock["sha256"]):
        raise ValueError("Locked annotation differs")
    with np.load(runtime / "graph.npz", allow_pickle=False) as graph:
        ids, ptr, post = (graph[name] for name in ("ids", "ptr", "post"))
    if (ids.ndim != 1 or ids.dtype.str != "<i8" or not len(ids)
            or np.any(ids <= 0) or np.any(ids > SAFE_INTEGER) or len(np.unique(ids)) != len(ids)
            or ptr.ndim != 1 or ptr.dtype.str != "<i8" or len(ptr) != len(ids) + 1
            or ptr[0] != 0 or ptr[-1] != len(post) or np.any(ptr[1:] < ptr[:-1])
            or post.ndim != 1 or post.dtype.str != "<i4" or np.any(post < 0) or np.any(post >= len(ids))):
        raise ValueError("Invalid graph IDs or directed topology")
    source = {}
    for name, value in (("ids", ids), ("ptr", ptr), ("post", post)):
        digest = raw_array_sha256(value)
        field = f"graph_{name}_sha256"
        if digest != expected[name] or digest != declaration["model_provenance"][field]:
            raise ValueError("Locked graph source differs")
        source[field] = digest
    source["annotations_sha256"] = annotation_lock["sha256"]
    positions = {}
    for row in feather.read_table(annotation, columns=["bodyId", "somaLocation"]).to_pylist():
        body, soma = row["bodyId"], row["somaLocation"]
        if type(body) is not int or body <= 0 or body in positions:
            raise ValueError("Duplicate or invalid annotation ID")
        if soma is not None and (type(soma) is not list or len(soma) != 3
                                 or any(type(v) is not int or abs(v) > SAFE_INTEGER for v in soma)):
            raise ValueError("Invalid actual somaLocation")
        positions[body] = soma
    if any(int(value) not in positions for value in ids):
        raise ValueError("Graph ID missing from annotations")
    cells, selection = select_cells(ids, declaration["neural_groups"], positions)
    topology = select_topology(ids, ptr, post, cells)
    if _hash_file(annotation) != source["annotations_sha256"]:
        raise ValueError("Annotation changed during join")
    return {"type": "header", "version": "cell-activity-raw/v1", "engine_identity": declaration,
            "selection": selection, "cells": cells, "topology": topology, "source": source}


def _sidecar(header, bins, recording_hash="0" * 64, raw_hash="0" * 64):
    return {"version": "replay-cell-counts/v1", "tick_ms": 0.1,
            "binding": {"recording_sha256": recording_hash, "raw_detail_sha256": raw_hash,
                        "engine_identity_sha256": header["engine_identity"]["sha256"], **header["source"]},
            "selection": header["selection"], "cells": header["cells"], "topology": header["topology"],
            "bins": bins, "display": {"window_ticks": 1000, "mode": "last-completed-whole-bin-window/v1"}}


def _validate_bin(row, size, previous):
    if not isinstance(row, dict) or set(row) != BIN_FIELDS:
        raise ValueError("Unknown or missing bin fields")
    observation = _integer(row["observation_index"], 0, 243)
    ordinal = _integer(row["bin_index"], 0, 49)
    start, end = (_integer(row[key], 0, 100000) for key in ("start_tick", "end_tick"))
    if not 0 < end - start <= 100 or start // 1000 != (end - 1) // 1000:
        raise ValueError("Invalid native bin or crossed display window")
    expected = (0, 0, 0) if previous is None else (
        (previous["observation_index"], previous["bin_index"] + 1, previous["end_tick"])
        if observation == previous["observation_index"] else
        (previous["observation_index"] + 1, 0, previous["end_tick"]))
    if (observation, ordinal, start) != expected:
        raise ValueError("Noncontinuous bin order")
    if type(row["counts"]) is not list or len(row["counts"]) != size:
        raise ValueError("Wrong cohort count vector")
    for count in row["counts"]:
        _integer(count, 0, end - start)


class CellActivityWriter:
    """Append flushed original bins, reserving combined raw and export bytes."""

    def __init__(self, path, header, *, detail_budget=DETAIL_BUDGET, max_bins=MAX_BINS):
        self.header = _strict_load(_canonical(header))
        self.detail_budget = _integer(detail_budget, 1, DETAIL_BUDGET)
        self.max_bins = _integer(max_bins, 1, MAX_BINS)
        self.bins = []
        raw = _canonical(self.header) + b"\n"
        self.raw_size = len(raw)
        self.export_size = len(_canonical(_sidecar(self.header, []))) + 1
        if self.raw_size + self.export_size > self.detail_budget:
            raise ValueError("Combined cell detail byte budget exceeded")
        self.stream = Path(path).open("xb")
        self.stream.write(raw)
        self.stream.flush()

    def __call__(self, value):
        row = _strict_load(_canonical(value))
        _validate_bin(row, len(self.header["cells"]), self.bins[-1] if self.bins else None)
        if len(self.bins) >= self.max_bins:
            raise ValueError("Cell bin cap exceeded")
        encoded = _canonical(row)
        raw = _canonical({"type": "bin", **row}) + b"\n"
        export_size = self.export_size + len(encoded) + bool(self.bins)
        if self.raw_size + len(raw) + export_size > self.detail_budget:
            raise ValueError("Combined cell detail byte budget exceeded")
        self.stream.write(raw)
        self.stream.flush()
        self.bins.append(row)
        self.raw_size += len(raw)
        self.export_size = export_size

    def close(self):
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()


def export_cell_activity(raw_path, recording_path, output_path, *, runtime_directory,
                         locks_directory=LOCKS, detail_budget=DETAIL_BUDGET):
    """Validate every raw bin against a sealed ordinary bundle and locked source."""
    output, recording_path = Path(output_path), Path(recording_path)
    if output.exists():
        raise FileExistsError(output)
    if recording_path.name != "recording.json":
        raise ValueError("Cell detail requires the verified recording.json member")
    _integer(detail_budget, 1, DETAIL_BUDGET)
    # The inspector's derived receipt binds the bytes it actually read, rather
    # than trusting a later independent read of the receipt or another filename.
    _, inspected_receipt = _inspect_session(recording_path.parent, receipt=True)
    inspected = _strict_load(inspected_receipt)["files"]["recording.json"]
    _safe_path(recording_path, directory=False)
    recording_bytes = _read(recording_path, 32 * 1024 * 1024)
    if (len(recording_bytes) != inspected["size_bytes"]
            or sha256(recording_bytes).hexdigest() != inspected["sha256"]):
        raise ValueError("Recording bytes differ from the inspected recording.json")
    recording = _strict_load(recording_bytes)
    raw = _read(raw_path, detail_budget)
    if not raw.endswith(b"\n"):
        raise ValueError("Incomplete raw cell detail")
    lines = raw.splitlines()
    if not 1 < len(lines) <= MAX_BINS + 1:
        raise ValueError("Raw bin cap exceeded or empty detail")
    header = _strict_load(lines[0])
    identity = recording["source"]["metadata"]["engine_identity"]
    expected_header = build_header(identity, runtime_directory, locks_directory=locks_directory)
    if _canonical(header) != _canonical(expected_header):
        raise ValueError("Raw cohort/topology/source/identity differs from locked source")
    bins = []
    for line in lines[1:]:
        row = _strict_load(line)
        if not isinstance(row, dict) or row.get("type") != "bin" or set(row) != BIN_FIELDS | {"type"}:
            raise ValueError("Invalid raw bin record")
        row = {key: value for key, value in row.items() if key != "type"}
        _validate_bin(row, len(header["cells"]), bins[-1] if bins else None)
        bins.append(row)
    expected_bins = [(observation, ordinal, bin_) for observation, segment in enumerate(recording["segments"])
                     for ordinal, bin_ in enumerate(segment["bins"])]
    if (len(bins) != len(expected_bins) or bins[-1]["end_tick"] != recording["duration_ticks"]
            or recording["duration_ticks"] % 1000):
        raise ValueError("Incomplete original-bin coverage or display windows")
    for row, (observation, ordinal, original) in zip(bins, expected_bins):
        if (row["observation_index"], row["bin_index"], row["start_tick"], row["end_tick"]) != (
                observation, ordinal, original["end_tick"] - original["duration_ticks"], original["end_tick"]):
            raise ValueError("Cell bin differs from original source interval/order")
        for group in GROUPS:
            selected = sum(row["counts"][slot] for slot, cell in enumerate(header["cells"]) if group in cell["groups"])
            population = original["group_spikes"][group]
            full = header["selection"]["group_population_counts"][group] == header["selection"]["group_selected_counts"][group]
            if selected > population or (full and selected != population):
                raise ValueError("Cell counts disagree with original population bin")
    result = _sidecar(header, bins, sha256(recording_bytes).hexdigest(), sha256(raw).hexdigest())
    encoded = _canonical(result) + b"\n"
    if len(raw) + len(encoded) > detail_budget:
        raise ValueError("Combined cell detail byte budget exceeded")
    _safe_path(recording_path, directory=False)
    if _hash_file(recording_path) != result["binding"]["recording_sha256"] or _hash_file(raw_path) != result["binding"]["raw_detail_sha256"]:
        raise ValueError("Used recording/raw detail changed before publication")
    with output.open("xb") as stream:
        stream.write(encoded)
    return result


def run_cell_activity_session(output_dir, *, playlist_path, proposal_path, runtime_directory,
                              engine_factory=FlyEngine.from_prepared_graph, locks_directory=LOCKS,
                              detail_budget=DETAIL_BUDGET):
    """Use one unchanged session workflow; errors retain incomplete evidence."""
    target = Path(output_dir)
    target.mkdir()
    writers = []
    def factory():
        if writers:
            raise ValueError("Only one acquisition engine is permitted")
        engine = engine_factory()
        header = build_header(engine.identity(), runtime_directory, locks_directory=locks_directory)
        writer = CellActivityWriter(target / "cell-activity.jsonl", header, detail_budget=detail_budget)
        writers.append(writer)
        engine.configure_cell_observer([cell["model_index"] for cell in header["cells"]], writer)
        return engine
    try:
        summary = run_session(target / "session", playlist_path=playlist_path, proposal_path=proposal_path,
                              engine_factory=factory)
    finally:
        for writer in writers:
            writer.close()
    result = export_cell_activity(target / "cell-activity.jsonl", target / "session/recording.json",
                                  target / "cell-activity.json", runtime_directory=runtime_directory,
                                  locks_directory=locks_directory, detail_budget=detail_budget)
    return {"session": summary, "cell_activity": str(target / "cell-activity.json"),
            "cells": len(result["cells"]), "bins": len(result["bins"])}
