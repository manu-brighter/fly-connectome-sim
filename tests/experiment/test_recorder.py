"""Integrity contracts for sealed qualification artifacts."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files
import json
import os
from pathlib import Path
import subprocess

import pytest

from fly_connectome_sim.experiment.recorder import RunArtifactError, RunRecorder, verify_run
from fly_connectome_sim.experiment import adapter as adapter_module


METADATA = {
    "engine_identity": {"version": "tiny/v1", "sha256": "tiny-engine", "model_provenance": {"graph": "tiny"}},
    "protocol_version": "qualification/v1",
    "stimulus_version": "associative-stimuli/v1",
    "family": "qualification",
    "seeds": [11, 23],
    "factors": {"order": ["AB", "BA"], "paired_identity": ["A", "B"]},
    "input_sha256": [sha256(b"black").hexdigest(), sha256(b"red").hexdigest()],
}
ZERO = "0" * 64


def _selected_replay_recorder(tmp_path):
    """Wire-only declarations and actual references, without native execution/proof."""
    import numpy as np
    from fly_connectome_sim.engine import _rgb_input_sha256
    black = _rgb_input_sha256(np.zeros((32, 32, 3), dtype=np.uint8))
    metadata = {**deepcopy(METADATA), "engine_identity": {"sha256": ZERO},
        "candidate_identity": "kc-mbon11-ppl101/v1", "mbon11_population_size": 1,
        "rgb_input_sha256": {"stimuli": {"11": {"A": METADATA["input_sha256"][1]}}, "black": black},
        "black_input": {"generator": "black-rgb/v1", "input_shape": [32, 32, 3], "input_dtype": "uint8", "input_sha256": black},
        "input_sha256": [*METADATA["input_sha256"], black]}
    recorder = RunRecorder(tmp_path / "selected-replay-wire", run_kind="qualification", metadata=metadata, root_branch_id="root")
    digest = checkpoint(recorder, tmp_path, "brain-before.npz")
    recorder.append(event(type="qualification_checkpoint", checkpoint_name="brain-before.npz", sim_tick=0))
    parent = {"parent_branch_id": "root", "parent_checkpoint_name": "brain-before.npz",
              "parent_checkpoint_sequence": 0, "parent_checkpoint_sha256": digest}
    operations = {}
    for side, branch in (("original", "selected/11/A/AB/pre/A"), ("repeat", "selected/11/A/AB/pre/A/repeat")):
        operations[side] = [recorder._append_reference(event(branch, type="branch_start", **parent))]
        operations[side].extend(recorder._append_reference(event(branch, type="observe", sim_ms=float(index))) for index in (1, 2, 3))
    start = {"sim_tick": 0, "complete_state_sha256": ZERO, "weights_frozen": False}
    state = {"sim_tick": 2000, "complete_state_sha256": ZERO, "candidate_memory_sha256": ZERO, "noncandidate_state_sha256": ZERO}
    body = {"type": "qualification_replay", "branch_id": "selected/11/A/AB/pre/A/repeat", "sim_ms": 400.0,
        "replay_version": "selected-response-repeat/v1", "replay_id": "selected/11/A/AB/pre/A/repeat",
        "original_branch_id": "selected/11/A/AB/pre/A",
        "physical_key": {"seed": 11, "paired_identity": "A", "presentation_order": "AB", "phase": "pre", "stimulus": "A"},
        "source_occurrence": {"checkpoint_name": "brain-before.npz", "checkpoint_sha256": digest,
            "checkpoint_sequence": 0, "origin_branch_id": "root", "sim_tick": 0},
        "engine_identity_sha256": ZERO, "candidate_identity": metadata["candidate_identity"], "population_size": 1,
        "input_sha256": METADATA["input_sha256"][1], "black_sha256": black,
        "response_window": {"start_ms": 0.0, "end_ms": 100.0}, "cs_onset_tick": 1000, "sim_tick": 4000,
        "operations": operations, "boundaries": {"start": {"original": start, "repeat": deepcopy(start)},
            "window": {"original": state, "repeat": deepcopy(state)},
            "final": {"original": {**state, "sim_tick": 4000}, "repeat": {**state, "sim_tick": 4000}}},
        "candidate_projection": {"projection_version": "selected-candidate-w-pair/v1", "dtype": "<f8", "shape": [1],
            "maps": {"target_indices": [0], "candidate_positions": [0], "candidate_edge_indices": [0]},
            "original_hex": "00" * 8, "repeat_hex": "00" * 8},
        "response_replay_resolution_hz": 0.0, "candidate_memory_w_resolution": 0.0, **parent}
    return recorder, body


def test_selected_replay_schema_closes_diagnostic_projection_and_dispatch():
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_text(encoding="utf-8"))
    definitions = schema["$defs"]
    assert definitions["qualification_replay"]["additionalProperties"] is False
    assert definitions["candidate_w_pair"]["additionalProperties"] is False
    assert definitions["candidate_w_pair"]["properties"]["dtype"] == {"const": "<f8"}
    assert definitions["selected_replay_operations"]["properties"]["original"]["maxItems"] == 6
    assert {"if": {"properties": {"type": {"const": "qualification_replay"}}, "required": ["type"]},
            "then": {"$ref": "#/$defs/qualification_replay"}} in definitions["event"]["allOf"]


def test_selected_replay_closed_append_rejection_preserves_valid_retry(tmp_path):
    recorder, body = _selected_replay_recorder(tmp_path)
    try:
        before = recorder.validate_prefix().scientific_prefix
        with pytest.raises(RunArtifactError):
            recorder.append({**body, "trusted": True})
        assert recorder.validate_prefix().scientific_prefix == before
        recorder.append(body)
        assert list(recorder.validate_prefix().iter_events())[-1]["replay_id"] == body["replay_id"]
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


@pytest.mark.parametrize("path,value", [
    (("physical_key", "seed"), True), (("physical_key", "retention_ms"), 10000),
    (("population_size",), True), (("population_size",), 2), (("candidate_identity",), "other/v1"),
    (("input_sha256",), ZERO), (("black_sha256",), ZERO), (("engine_identity_sha256",), "a" * 64),
    (("response_window", "end_ms"), True), (("response_window", "end_ms"), 1e308),
    (("boundaries", "start", "original", "weights_frozen"), 0),
    (("boundaries", "start", "original", "sim_tick"), True),
    (("boundaries", "final", "repeat", "complete_state_sha256"), "a" * 64),
    (("operations", "original", 0, "sequence"), True), (("operations", "original", 0, "sequence"), 10000),
    (("operations", "repeat", 0, "sequence"), 1), (("operations", "original", 0, "extra"), 0),
    (("candidate_projection", "shape"), [True]), (("candidate_projection", "shape"), [2]),
    (("candidate_projection", "maps", "target_indices"), [True]),
    (("candidate_projection", "dtype"), "<f4"), (("candidate_projection", "original_hex"), "00"),
    (("response_replay_resolution_hz",), True), (("candidate_memory_w_resolution",), -1),
    (("source_occurrence", "sim_tick"), True), (("extra",), "unclosed"),
])
def test_selected_replay_invalid_wire_is_nonmutating_with_valid_retry(tmp_path, path, value):
    recorder, body = _selected_replay_recorder(tmp_path)
    invalid = deepcopy(body)
    target = invalid
    for name in path[:-1]:
        target = target[name]
    target[path[-1]] = value
    try:
        before = recorder.validate_prefix().scientific_prefix
        with pytest.raises(RunArtifactError):
            recorder.append(invalid)
        assert recorder.validate_prefix().scientific_prefix == before
        recorder.append(body)
        recorder.validate_prefix()
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


def test_selected_replay_structural_later_t_is_not_limited_by_initial_grid(tmp_path):
    recorder, body = _selected_replay_recorder(tmp_path)
    key = {**body["physical_key"], "phase": "post", "condition": "paired", "retention_ms": 70000}
    parent = {"parent_branch_id": "retained", "parent_state_anchor_sha256": "a" * 64}
    body = {name: value for name, value in body.items() if not name.startswith("parent_")}
    body.update(physical_key=key, **parent)
    from fly_connectome_sim.experiment.recorder import _check_qualification_replay
    try:
        # Pure structural check; this does not register a fake anchor or native context.
        owned = {"sequence": recorder.next_sequence, "run_metadata_sha256": ZERO,
                 "previous_scientific_sha256": ZERO, "scientific_sha256": ZERO}
        _check_qualification_replay({**body, **owned}, recorder.metadata, recorder.next_sequence)
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


def test_selected_replay_coincident_window_final_requires_equal_full_records(tmp_path):
    recorder, body = _selected_replay_recorder(tmp_path)
    body.update(sim_tick=2000, sim_ms=200.0)
    for side in ("original", "repeat"):
        body["boundaries"]["final"][side].update(sim_tick=2000, complete_state_sha256="a" * 64)
    try:
        with pytest.raises(RunArtifactError, match="boundary clocks"):
            recorder.append(body)
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


def test_append_reference_matches_actual_prefix_bytes_and_preserves_public_append(tmp_path):
    recorder = RunRecorder(tmp_path / "references", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    try:
        payload = event(value="first", compute_seconds=12.5)
        first = recorder._append_reference(payload)
        assert recorder.append(event(value="middle")) is None
        second = recorder._append_reference(event(value="last", kernel_seconds=9.0))
        payload["value"] = "caller changed"
        prefix = recorder.validate_prefix()
        events = list(prefix.iter_events())  # Fully drain real fixed-byte validation.
        raw = [json.loads(line) for line in (recorder.path / "events.jsonl").read_bytes().splitlines()]
        assert [item["sequence"] for item in events] == [0, 1, 2]
        for reference, index in ((first, 0), (second, 2)):
            body = {key: value for key, value in raw[index].items()
                    if key not in {"scientific_sha256", "compute_seconds", "kernel_seconds"}}
            digest = sha256(canonical_json(body)).hexdigest()
            assert type(reference) is dict and set(reference) == {"sequence", "scientific_sha256"}
            assert reference == {"sequence": index, "scientific_sha256": digest}
            assert reference["scientific_sha256"] == events[index]["scientific_sha256"]
        assert events[0]["value"] == "first"
        first.update(sequence=99, scientific_sha256=ZERO)
        assert second == {"sequence": 2, "scientific_sha256": events[2]["scientific_sha256"]}
        assert recorder.validate_prefix().scientific_prefix == prefix.scientific_prefix
        assert recorder._raw_digest.hexdigest() == sha256((recorder.path / "events.jsonl").read_bytes()).hexdigest()
    finally:
        recorder.__exit__(RuntimeError, RuntimeError("unsealed recorder fixture"), None)


def test_append_reference_calls_public_append_once_without_prefix_scan(tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import recorder as recorder_module
    recorder = RunRecorder(tmp_path / "one-reference", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    append = recorder.append
    calls = []
    def tracked(payload):
        calls.append(payload)
        result = append(payload)
        assert result is None
        assert recorder._raw_digest.hexdigest() == sha256((recorder.path / "events.jsonl").read_bytes()).hexdigest()
        return result
    def forbidden(*args, **kwargs):
        pytest.fail("Append reference scanned growing history")
    monkeypatch.setattr(recorder, "append", tracked)
    monkeypatch.setattr(recorder, "validate_prefix", forbidden)
    monkeypatch.setattr(recorder_module, "validate_prefix", forbidden)
    monkeypatch.setattr(recorder_module, "_scan_chain", forbidden)
    try:
        payload = event(value="one append")
        reference = recorder._append_reference(payload)
        assert len(calls) == 1 and calls[0] is payload
        actual = json.loads((recorder.path / "events.jsonl").read_bytes())
        assert reference == {key: actual[key] for key in ("sequence", "scientific_sha256")}
    finally:
        recorder.__exit__(RuntimeError, RuntimeError("unsealed recorder fixture"), None)


@pytest.mark.parametrize("method", ["append", "_append_reference"])
@pytest.mark.parametrize("failure", ["write", "flush"])
def test_append_reference_io_failure_never_returns_advanced_chain_as_success(tmp_path, method, failure):
    recorder = RunRecorder(tmp_path / "io-failure", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    stream, stages = recorder._stream, []
    class FailingStream:
        def write(self, line):
            stages.append(("write", recorder.next_sequence))
            if failure == "write":
                raise OSError("injected write failure")
            return stream.write(line)

        def flush(self):
            stages.append(("flush", recorder.next_sequence))
            if failure == "flush":
                raise OSError("injected flush failure")
            return stream.flush()
    recorder._stream = FailingStream()
    reference = None
    try:
        with pytest.raises(RunArtifactError, match=f"Event append failed: injected {failure} failure") as error:
            reference = getattr(recorder, method)(event(value="failed append"))
        assert isinstance(error.value.__cause__, OSError)
        assert reference is None and recorder._failed
        assert recorder.next_sequence == 1 and recorder._chain.previous != ZERO
        assert stages == ([("write", 1)] if failure == "write" else [("write", 1), ("flush", 1)])
        assert recorder._raw_digest.hexdigest() == sha256(b"").hexdigest()
        with pytest.raises(RunArtifactError, match="closed or failed"):
            recorder._append_reference(event())
    finally:
        stream.close()


@pytest.mark.parametrize("state", ["closed", "failed"])
def test_append_reference_refuses_unhealthy_recorder_before_append(tmp_path, monkeypatch, state):
    recorder = RunRecorder(tmp_path / "unhealthy-reference", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    if state == "closed":
        recorder.__exit__(RuntimeError, RuntimeError(), None)
    else:
        recorder._failed = True
    def forbidden(*args, **kwargs):
        pytest.fail("Unhealthy recorder reached append")
    monkeypatch.setattr(recorder, "append", forbidden)
    try:
        with pytest.raises(RunArtifactError, match="closed or failed"):
            recorder._append_reference(event())
        assert (recorder.path / "events.jsonl").read_bytes() == b""
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


@pytest.mark.parametrize("position", [False, True, 0.0, -1, "0", None])
def test_append_reference_rejects_invalid_initial_position_without_writing(tmp_path, monkeypatch, position):
    recorder = RunRecorder(tmp_path / "invalid-reference-position", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    recorder._chain.count = position
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid reference position reached append")
    monkeypatch.setattr(recorder, "append", forbidden)
    try:
        with pytest.raises(RunArtifactError, match="position"):
            recorder._append_reference(event())
        assert (recorder.path / "events.jsonl").read_bytes() == b""
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


@pytest.mark.parametrize("mutation", ["extra_append", "closed", "failed", "boolean_count"])
def test_append_reference_refuses_drift_after_real_successful_append(tmp_path, monkeypatch, mutation):
    recorder = RunRecorder(tmp_path / "changed-reference-boundary", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    append = recorder.append
    def changed(payload):
        append(payload)
        if mutation == "extra_append":
            append(event(value="unexpected extra append"))
        elif mutation == "closed":
            recorder.__exit__(RuntimeError, RuntimeError(), None)
        elif mutation == "failed":
            recorder._failed = True
        else:
            recorder._chain.count = True
    monkeypatch.setattr(recorder, "append", changed)
    reference = None
    try:
        with pytest.raises(RunArtifactError, match="boundary"):
            reference = recorder._append_reference(event(value="original append"))
        assert reference is None
        raw = [json.loads(line) for line in (recorder.path / "events.jsonl").read_bytes().splitlines()]
        assert len(raw) == (2 if mutation == "extra_append" else 1)
        if mutation == "extra_append":
            assert [item["value"] for item in recorder.validate_prefix().iter_events()] == [
                "original append", "unexpected extra append",
            ]
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


@pytest.mark.parametrize("field", ["sequence", "scientific_sha256", "previous_scientific_sha256", "run_metadata_sha256"])
def test_append_reference_preserves_owned_fields_and_allows_valid_retry(tmp_path, field):
    recorder = RunRecorder(tmp_path / "owned-reference", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    try:
        with pytest.raises(RunArtifactError, match="Recorder-owned event field"):
            recorder._append_reference(event(**{field: ZERO}))
        assert (recorder.path / "events.jsonl").read_bytes() == b""
        reference = recorder._append_reference(event(value="valid retry"))
        recorded = list(recorder.validate_prefix().iter_events())
        assert len(recorded) == 1
        assert reference == {key: recorded[0][key] for key in ("sequence", "scientific_sha256")}
    finally:
        recorder.__exit__(RuntimeError, RuntimeError(), None)


def test_next_sequence_is_authoritative_readonly_and_rejected_append_does_not_advance(tmp_path):
    recorder = RunRecorder(tmp_path / "position", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    recorder.append(event())
    assert recorder.next_sequence == 1
    with pytest.raises(AttributeError):
        recorder.next_sequence = 99
    with pytest.raises(RunArtifactError):
        recorder.append(event(sequence=99))
    assert recorder.next_sequence == 1
    recorder.append(event())
    assert [item["sequence"] for item in recorder.validate_prefix().iter_events()] == [0, 1]
    recorder._stream.close()


def _grid_binding_recorder(tmp_path):
    recorder = RunRecorder(tmp_path / "grid-binding", run_kind="qualification", metadata=METADATA,
                           root_branch_id="root")
    digest = checkpoint(recorder, tmp_path, "brain-before.npz")
    recorder.append(event(type="qualification_checkpoint", checkpoint_name="brain-before.npz", sim_tick=0))
    recorder.append(event(type="qualification_observation"))
    binding = event(type="qualification_grid_binding", binding_version="qualification-grid-binding/v1",
                    grid_evidence_id="grid/0/11/A/AB", grid_index=0, seed=11,
                    paired_identity="A", presentation_order="AB",
                    baseline_occurrence={"checkpoint_name": "brain-before.npz", "checkpoint_sha256": digest,
                                         "origin_branch_id": "root", "checkpoint_sequence": 0, "sim_tick": 0},
                    training_occurrences={}, retained_occurrences={},
                    observation_sequences={"pre": {"A": [1]}, "training": {}, "retention": {}, "post": {}},
                    failures=[{"scope": "base", "stage": "pre", "condition": None, "stimulus": "A",
                               "retention_ms": None, "reason": "native data unavailable"}])
    return recorder, binding


GRID_INVALID_FIELDS = [
    (("binding_version",), "qualification-grid-binding/v2"),
    (("grid_index",), True), (("grid_index",), 12), (("seed",), True), (("seed",), 101),
    (("paired_identity",), "C"), (("presentation_order",), "AA"),
    (("grid_evidence_id",), "grid/1/11/A/AB"),
    (("extra",), None),
    (("baseline_occurrence", "checkpoint_sequence"), True),
    (("baseline_occurrence", "checkpoint_sequence"), 1),
    (("baseline_occurrence", "checkpoint_sha256"), "f" * 64),
    (("baseline_occurrence", "sim_tick"), 1),
    (("baseline_occurrence", "extra"), 0),
    (("training_occurrences", "unknown"), {}),
    (("retained_occurrences", "10000.0"), {}),
    (("retained_occurrences", "10000", "paired_replay"), {}),
    (("observation_sequences", "pre", "C"), [True]),
    (("observation_sequences", "pre", "A"), [1, 1]),
    (("observation_sequences", "pre", "A"), [2]),
    (("observation_sequences", "pre", "A"), [-1]),
    (("observation_sequences", "post", "10000", "frozen_plasticity", "B"), []),
    (("failures",), [{"scope": "base", "stage": "post", "condition": None, "stimulus": None,
                      "retention_ms": None, "reason": "bad stage"}]),
    (("failures",), [{"scope": "retention", "stage": "post", "condition": "paired_replay", "stimulus": "A",
                      "retention_ms": 10000, "reason": "bad role"}]),
    (("failures",), [{"scope": "retention", "stage": "post", "condition": "paired", "stimulus": "A",
                      "retention_ms": True, "reason": "bad T"}]),
    (("failures",), [{"scope": "base", "stage": "pre", "condition": None, "stimulus": None,
                      "retention_ms": None, "reason": ""}]),
]


@pytest.mark.parametrize("path,value", GRID_INVALID_FIELDS)
def test_grid_binding_invalid_append_is_nonmutating_and_valid_retry_succeeds(tmp_path, path, value):
    recorder, binding = _grid_binding_recorder(tmp_path)
    invalid = deepcopy(binding)
    target = invalid
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = value
    before = recorder.validate_prefix().scientific_prefix
    with pytest.raises(RunArtifactError):
        recorder.append(invalid)
    assert recorder.validate_prefix().scientific_prefix == before
    recorder.append(binding)
    with pytest.raises(RunArtifactError):
        recorder.append(binding)
    assert list(recorder.validate_prefix().iter_events())[-1]["grid_evidence_id"] == "grid/0/11/A/AB"
    recorder._stream.close()


def test_grid_binding_failures_are_one_base_or_ordered_distinct_fixed_retention_times(tmp_path):
    recorder, binding = _grid_binding_recorder(tmp_path)
    retention = [{"scope": "retention", "stage": "retention_timing", "condition": None,
                  "stimulus": None, "retention_ms": value, "reason": "unreachable clock"}
                 for value in (10000, 20000, 30000, 60000)]
    for invalid in (retention[::-1], retention[:1] * 2, binding["failures"] + retention,
                    binding["failures"] * 2, retention + retention[:1]):
        with pytest.raises(RunArtifactError):
            recorder.append({**binding, "failures": invalid})
    recorder.append({**binding, "failures": retention})
    recorder.validate_prefix()
    recorder._stream.close()


@pytest.mark.parametrize("path,value", GRID_INVALID_FIELDS)
def test_rehashed_grid_binding_tampering_is_rejected_by_both_stream_scanners(tmp_path, path, value):
    """Structural synthetic bytes, not native evidence or a complete grid."""
    from fly_connectome_sim.experiment.recorder import _scan_chain

    recorder, binding = _grid_binding_recorder(tmp_path)
    recorder.append(binding)
    checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    recorder.append(result_event(branch="root"))
    recorder.close()
    verified = verify_run(recorder.path)
    events = list(verified.iter_events())
    target = events[2]
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = value
    manifest = verified.manifest
    rewrite_sealed_run(recorder.path, events, manifest)
    with pytest.raises(RunArtifactError):
        list(_scan_chain(recorder.path, manifest))
    with pytest.raises(RunArtifactError):
        verify_run(recorder.path)


def test_grid_binding_schema_closes_partial_role_maps_and_typed_sequences():
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_text(encoding="utf-8"))
    definitions = schema["$defs"]
    binding = definitions["qualification_grid_binding"]
    assert binding["additionalProperties"] is False
    assert set(binding["properties"]["training_occurrences"]["properties"]) == {
        "paired", "matched_reference", "frozen_plasticity", "paired_replay",
    }
    assert set(definitions["grid_retained_occurrences"]["properties"]) == {
        "paired", "frozen_plasticity", "matched_reference",
    }
    for role, rule in definitions["grid_retention_sequences"]["properties"].items():
        assert role in {"paired", "frozen_plasticity", "matched_reference"}
        assert rule == {"type": "array", "maxItems": 120, "uniqueItems": True, "items": {"$ref": "#/$defs/tick"}}
    assert definitions["tick"]["type"] == "integer"
    assert definitions["source_occurrence"]["additionalProperties"] is False
    assert {"if": {"properties": {"type": {"const": "qualification_grid_binding"}}, "required": ["type"]},
            "then": {"$ref": "#/$defs/qualification_grid_binding"}} in definitions["event"]["allOf"]


def event(branch="root", sim_ms=0.0, **fields):
    return {"type": "observation", "branch_id": branch, "sim_ms": sim_ms, **fields}


def checkpoint(recorder, tmp_path, name, origin="root", data=b"state"):
    source = tmp_path / "source.npz"
    source.write_bytes(data)
    return recorder.ingest_checkpoint(name, source, origin_branch_id=origin)


def seal(recorder, tmp_path):
    checkpoint(recorder, tmp_path, "brain-before.npz")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
    checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    recorder.close()


def result_event(branch="summary", **fields):
    result = event(
        branch, 0.0, type="qualification_result", status="unsupported",
        family="qualification", seeds=[11, 23], selected_configuration=None,
        selected_window=None, selected_retention_ms=None,
        observed_effect_sign=None,
        benchmark={"simulated_seconds": 0.0, "event_count": 2,
                   "checkpoint_bytes": 10, "peak_event_buffer_bytes": 0},
        compute_seconds=0.0,
    )
    result.update(fields)
    return result


def supported_result_event(**fields):
    return result_event(
        status="supported",
        selected_configuration={"cs_duration_ms": 100.0, "dan_onset_ms": -100.0,
                                "post_pair_gap_ms": 500.0},
        selected_window={"start_ms": 0.0, "end_ms": 100.0},
        selected_retention_ms=10000.0, observed_effect_sign=1,
        **fields,
    )


def motor_event(**fields):
    adapter_type = getattr(adapter_module, "LateralMotorAdapter", None)
    assert adapter_type is not None, "Missing motor-only adapter API"
    telemetry = {
        "engine_identity": deepcopy(METADATA["engine_identity"]),
        "sim_ms": 0.0,
        "rates_hz": {"motor_left": 5.0, "motor_right": 15.0},
    }
    return event(telemetry=telemetry, motor_readout={
        "interpretation": "engineered_unvalidated_motor_readout",
        "action_threshold_hz": 1.0,
        "decision": asdict(adapter_type().adapt(telemetry)),
    }, **fields)


@pytest.mark.parametrize("event_type", ["observation", "observe"])
def test_motor_readout_roundtrip_binds_same_observation_and_legacy_stays_readable(tmp_path, event_type):
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root")
    measured = motor_event(type=event_type)
    recorder.append(measured)
    legacy = event(preference_readout={"adapter_version": "preference-adapter/v1", "confidence": 0.5})
    recorder.append(legacy)
    prefix = recorder.validate_prefix()
    prefix_events = list(prefix.iter_events())
    assert prefix_events[0]["motor_readout"] == {
        "interpretation": "engineered_unvalidated_motor_readout", "action_threshold_hz": 1.0,
        "decision": {"adapter_version": "lateral-motor-adapter/v1", "signed_difference_hz": 10.0,
                     "evidence_strength": 0.5, "action": "inspect_right"},
    }
    assert "motor_readout" not in prefix_events[1]
    assert prefix_events[1]["preference_readout"] == legacy["preference_readout"]
    seal(recorder, tmp_path)
    assert list(verify_run(recorder.path).iter_events())[:2] == prefix_events


MOTOR_INVALID_FIELDS = [
    (("motor_readout",), None),
    (("motor_readout", "extra"), True),
    (("motor_readout", "interpretation"), "validated"),
    (("motor_readout", "action_threshold_hz"), True),
    (("motor_readout", "action_threshold_hz"), "1"),
    (("motor_readout", "action_threshold_hz"), -1),
    (("motor_readout", "decision"), []),
    (("motor_readout", "decision", "extra"), True),
    (("motor_readout", "decision", "adapter_version"), "preference-adapter/v1"),
    (("motor_readout", "decision", "action"), "inspect_left"),
    (("motor_readout", "decision", "action"), True),
    (("motor_readout", "decision", "signed_difference_hz"), 9.0),
    (("motor_readout", "decision", "signed_difference_hz"), True),
    (("motor_readout", "decision", "signed_difference_hz"), "10"),
    (("motor_readout", "decision", "evidence_strength"), 0.6),
    (("motor_readout", "decision", "evidence_strength"), -0.5),
    (("motor_readout", "decision", "evidence_strength"), 1.5),
    (("motor_readout", "decision", "evidence_strength"), True),
    (("motor_readout", "decision", "evidence_strength"), "0.5"),
    (("type",), "other_event"),
    (("telemetry",), None),
    (("telemetry", "engine_identity"), {}),
    (("telemetry", "rates_hz"), []),
    (("telemetry", "rates_hz", "motor_left"), True),
    (("telemetry", "rates_hz", "motor_left"), "5"),
    (("telemetry", "rates_hz", "motor_left"), -5),
    (("telemetry", "rates_hz", "motor_left"), 4.0),
    (("telemetry", "sim_ms"), 1.0),
    (("telemetry", "sim_ms"), True),
    (("telemetry", "sim_ms"), "0"),
    (("telemetry", "sim_ms"), None),
]


def replace_motor_field(item, path, value):
    target = item
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value


@pytest.mark.parametrize(("path", "value"), MOTOR_INVALID_FIELDS)
def test_invalid_motor_readout_append_does_not_advance_chain(tmp_path, path, value):
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root")
    malformed = motor_event()
    replace_motor_field(malformed, path, value)
    with pytest.raises(RunArtifactError):
        recorder.append(malformed)
    assert (recorder.path / "events.jsonl").read_bytes() == b""
    recorder.append(motor_event())
    assert list(recorder.validate_prefix().iter_events())[0]["sequence"] == 0
    seal(recorder, tmp_path)
    assert verify_run(recorder.path).manifest["event_count"] == 3


@pytest.mark.parametrize("path", [
    ("telemetry",), ("telemetry", "rates_hz"), ("telemetry", "engine_identity"),
    ("telemetry", "sim_ms"),
    ("telemetry", "rates_hz", "motor_right"), ("motor_readout", "interpretation"),
    ("motor_readout", "action_threshold_hz"), ("motor_readout", "decision"),
    ("motor_readout", "decision", "action"),
    ("motor_readout", "decision", "adapter_version"),
    ("motor_readout", "decision", "signed_difference_hz"),
    ("motor_readout", "decision", "evidence_strength"),
])
def test_motor_readout_requires_complete_fields_and_same_event_source(tmp_path, path):
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root")
    malformed = motor_event()
    target = malformed
    for field in path[:-1]:
        target = target[field]
    del target[path[-1]]
    with pytest.raises(RunArtifactError):
        recorder.append(malformed)
    seal(recorder, tmp_path)


@pytest.mark.parametrize(("path", "value"), MOTOR_INVALID_FIELDS)
def test_rehashed_forged_motor_readout_rejected_by_prefix_and_sealed_scanners(tmp_path, path, value):
    from fly_connectome_sim.experiment.recorder import validate_prefix

    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root")
    recorder.append(motor_event())
    seal(recorder, tmp_path)
    verified = verify_run(recorder.path)
    events = list(verified.iter_events())
    replace_motor_field(events[0], path, value)
    rewrite_sealed_run(recorder.path, events, verified.manifest)
    with pytest.raises(RunArtifactError):
        verify_run(recorder.path)
    with pytest.raises(RunArtifactError):
        validate_prefix(recorder.path, run_kind="pilot", metadata=METADATA,
                        root_branch_id="root", checkpoints=verified.manifest["checkpoints"])


def test_motor_readout_recomputes_custom_threshold_and_rejects_prior_event_source(tmp_path):
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root")
    measured = motor_event()
    measured["motor_readout"]["action_threshold_hz"] = 10.0
    measured["motor_readout"]["decision"]["action"] = "defer"
    recorder.append(measured)
    missing_source = motor_event()
    del missing_source["telemetry"]
    with pytest.raises(RunArtifactError):
        recorder.append(missing_source)
    seal(recorder, tmp_path)
    assert list(verify_run(recorder.path).iter_events())[0]["motor_readout"]["decision"]["action"] == "defer"


@pytest.mark.parametrize("path", [
    ("motor_readout", "action_threshold_hz"),
    ("motor_readout", "decision", "signed_difference_hz"),
    ("motor_readout", "decision", "evidence_strength"),
    ("telemetry", "rates_hz", "motor_left"),
    ("telemetry", "rates_hz", "motor_right"),
    ("telemetry", "sim_ms"),
])
@pytest.mark.parametrize("value", [float("inf"), float("nan"), 10 ** 400])
def test_motor_readout_nonfinite_or_overflowing_numbers_fail_before_append(tmp_path, path, value):
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root")
    malformed = motor_event()
    replace_motor_field(malformed, path, value)
    with pytest.raises(RunArtifactError):
        recorder.append(malformed)
    assert (recorder.path / "events.jsonl").read_bytes() == b""
    seal(recorder, tmp_path)


def test_motor_source_identity_is_exact_even_for_boolean_numeric_equality(tmp_path):
    metadata = deepcopy(METADATA)
    metadata["engine_identity"]["neuron_ids"] = [1]
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=metadata, root_branch_id="root")
    measured = motor_event()
    measured["telemetry"]["engine_identity"] = deepcopy(metadata["engine_identity"])
    measured["telemetry"]["engine_identity"]["neuron_ids"] = [True]
    with pytest.raises(RunArtifactError):
        recorder.append(measured)
    seal(recorder, tmp_path)


def test_extreme_finite_motor_rates_remain_json_safe_through_real_recorder(tmp_path):
    recorder = RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root")
    measured = motor_event()
    measured["telemetry"]["rates_hz"] = {"motor_left": 1e308, "motor_right": 1.5e308}
    adapter_type = getattr(adapter_module, "LateralMotorAdapter", None)
    measured["motor_readout"]["decision"] = asdict(adapter_type().adapt(measured["telemetry"]))
    recorder.append(measured)
    seal(recorder, tmp_path)
    result = list(verify_run(recorder.path).iter_events())[0]["motor_readout"]["decision"]
    assert result["signed_difference_hz"] == pytest.approx(5e307)
    assert result["evidence_strength"] == pytest.approx(0.2)
    assert result["action"] == "inspect_right"


def test_motor_schema_declares_exact_optional_derived_contract():
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes())
    definitions = schema["$defs"]
    assert "motor_readout" not in definitions["event"]["required"]
    readout = definitions.get("motor_readout")
    assert readout is not None, "Schema must declare the optional motor contract"
    assert readout["additionalProperties"] is False
    assert set(readout["required"]) == set(readout["properties"]) == {
        "interpretation", "action_threshold_hz", "decision",
    }
    assert readout["properties"]["interpretation"] == {"const": "engineered_unvalidated_motor_readout"}
    assert readout["properties"]["action_threshold_hz"] == {"type": "number", "minimum": 0}
    decision = definitions["motor_decision"]
    assert decision["additionalProperties"] is False
    assert set(decision["required"]) == set(decision["properties"]) == {
        "adapter_version", "signed_difference_hz", "evidence_strength", "action",
    }
    assert decision["properties"]["adapter_version"] == {"const": "lateral-motor-adapter/v1"}
    assert decision["properties"]["signed_difference_hz"] == {"type": "number"}
    assert decision["properties"]["evidence_strength"] == {"type": "number", "minimum": 0, "maximum": 1}
    assert decision["properties"]["action"]["enum"] == ["inspect_left", "inspect_right", "defer"]
    conditional = next(rule["then"] for rule in definitions["event"]["allOf"]
                       if rule["if"].get("required") == ["motor_readout"])
    assert conditional["required"] == ["telemetry"]
    assert conditional["properties"]["type"]["enum"] == ["observation", "observe"]
    telemetry = conditional["properties"]["telemetry"]
    assert telemetry["type"] == "object"
    assert set(telemetry["required"]) == {"engine_identity", "rates_hz", "sim_ms"}
    assert telemetry["properties"]["sim_ms"] == {"type": "number", "minimum": 0}
    rates = telemetry["properties"]["rates_hz"]
    assert set(rates["required"]) == {"motor_left", "motor_right"}
    for side in ("motor_left", "motor_right"):
        assert rates["properties"][side] == {"type": "number", "minimum": 0}


def test_exclusive_directory_and_sealed_reopen(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    verified = verify_run(target)
    events = list(verified.iter_events())
    assert [item["sequence"] for item in events] == [0, 1]
    assert events[0]["previous_scientific_sha256"] == ZERO
    assert events[1]["previous_scientific_sha256"] == events[0]["scientific_sha256"]
    assert verified.manifest["event_count"] == 2
    assert set(verified.manifest["checkpoints"]) == {"brain-before.npz", "brain-after.npz"}
    with pytest.raises(RunArtifactError):
        recorder.append(event())
    with pytest.raises(RunArtifactError):
        RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root")
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pass  # Windows may deny unprivileged symlink creation.
    else:
        with pytest.raises(RunArtifactError):
            RunRecorder(link, run_kind="pilot", metadata=METADATA, root_branch_id="root")


def test_formal_zero_anchor_mode_requires_verifier_and_rechecks_bindings(tmp_path):
    from dataclasses import FrozenInstanceError
    from fly_connectome_sim.experiment.recorder import (
        ValidatedPrefix, VerifiedRun, verify_replay_prefix, verify_replay_run,
    )

    recorder = RunRecorder(tmp_path / "zero-anchor", run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    checkpoint(recorder, tmp_path, "brain-before.npz")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
    checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    ordinary_prefix = recorder.validate_prefix()

    def unused_factory():
        pytest.fail("Zero-anchor verification does not reconstruct an engine")

    prefix = verify_replay_prefix(ordinary_prefix, engine_factory=unused_factory)
    assert ordinary_prefix.verification_mode == "integrity-only"
    assert prefix.verification_mode == "native-replay"
    assert prefix.replay_attested_state_anchors == frozenset()
    with pytest.raises(TypeError):
        ValidatedPrefix(prefix.path, prefix._context_bytes, prefix._byte_length, prefix._raw_sha256,
                        prefix._directory_ids, verification_mode="native-replay")
    with pytest.raises(FrozenInstanceError):
        prefix.verification_mode = "native-replay"
    recorder.close()
    ordinary = verify_run(recorder.path)
    formal = verify_replay_run(recorder.path, engine_factory=unused_factory)
    assert ordinary.verification_mode == "integrity-only"
    assert formal.verification_mode == "native-replay"
    assert formal.replay_attested_state_anchors == frozenset()
    with pytest.raises(TypeError):
        VerifiedRun(formal.path, formal._manifest_bytes, verification_mode="native-replay")
    with pytest.raises(FrozenInstanceError):
        formal.verification_mode = "native-replay"
    (recorder.path / "checkpoints" / "brain-before.npz").write_bytes(b"changed")
    for value in (prefix, formal):
        with pytest.raises(RunArtifactError):
            _ = value.verification_mode


def test_output_rejects_junction_in_grandparent(tmp_path, monkeypatch):
    redirected = tmp_path / "redirected"
    nested = redirected / "nested"
    nested.mkdir(parents=True)
    actual_is_junction = Path.is_junction
    monkeypatch.setattr(Path, "is_junction", lambda path: path == redirected or actual_is_junction(path))
    target = nested / "run"
    with pytest.raises(RunArtifactError):
        RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root")
    assert not target.exists()


def test_scientific_hash_excludes_nested_timing_but_raw_hash_does_not(tmp_path):
    manifests = []
    for index, seconds in enumerate((0.1, 0.7)):
        target = tmp_path / f"run-{index}"
        with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
            recorder.append(event(telemetry={"compute_seconds": seconds, "nested": [{"kernel_seconds": seconds, "count": 2}]}))
            seal(recorder, tmp_path)
        manifests.append(verify_run(target).manifest)
    assert manifests[0]["final_scientific_sha256"] == manifests[1]["final_scientific_sha256"]
    assert manifests[0]["events_sha256"] != manifests[1]["events_sha256"]


def test_flush_exposes_complete_lines_before_close_without_sealing(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        recorder.append(event(value="measured"))
        recorder.flush()
        assert (target / "events.jsonl").read_bytes().endswith(b"\n")
        assert not (target / "run.json").exists()
        seal(recorder, tmp_path)
    assert verify_run(target).manifest["event_count"] == 3


@pytest.mark.parametrize("bad", [
    {"telemetry": {"rate": float("nan")}},
    {"telemetry": {"rate": float("inf")}},
    {"telemetry": {1: "non-string key"}},
    {"sequence": 5},
    {"scientific_sha256": ZERO},
    {"previous_scientific_sha256": ZERO},
    {"run_metadata_sha256": ZERO},
    {"input_sha256": "undeclared"},
    {"engine_identity": {"version": "wrong"}},
])
def test_append_rejects_invalid_or_owned_fields(tmp_path, bad):
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        with pytest.raises(RunArtifactError):
            recorder.append(event(**bad))
        seal(recorder, tmp_path)
    assert verify_run(tmp_path / "run").manifest["event_count"] == 2


def test_nested_scientific_sha256_is_preserved_and_rejection_does_not_advance_chain(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        recorder.append(event(telemetry={"scientific_sha256": "measurement"}))
        with pytest.raises(RunArtifactError):
            recorder.append(event("fork", 1.0, parent_branch_id="root",
                                  parent_checkpoint_sha256=ZERO))
        seal(recorder, tmp_path)
    events = list(verify_run(target).iter_events())
    assert events[0]["telemetry"]["scientific_sha256"] == "measurement"
    projection = dict(events[0])
    projection.pop("scientific_sha256")
    assert events[0]["scientific_sha256"] == sha256(json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    assert [item["sequence"] for item in events] == [0, 1, 2]


def test_extreme_branch_clock_fails_with_project_error(tmp_path):
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        with pytest.raises(RunArtifactError):
            recorder.append(event(sim_ms=10 ** 400))
        seal(recorder, tmp_path)


def test_explicit_null_parent_fields_are_rejected(tmp_path):
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        with pytest.raises(RunArtifactError):
            recorder.append(event(parent_checkpoint_sha256=None))
        with pytest.raises(RunArtifactError):
            recorder.append(event(parent_branch_id=None))
        seal(recorder, tmp_path)


def test_branch_time_and_parent_checkpoint_are_validated(tmp_path):
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
        recorder.append(event(sim_ms=100.0))
        with pytest.raises(RunArtifactError):
            recorder.append(event(sim_ms=99.0))
        for fields in ({}, {"parent_branch_id": "wrong", "parent_checkpoint_sha256": digest},
                       {"parent_branch_id": "root", "parent_checkpoint_sha256": ZERO}):
            with pytest.raises(RunArtifactError):
                recorder.append(event("fork", 0.0, **fields))
        recorder.append(event("fork", 0.0, parent_branch_id="root", parent_checkpoint_sha256=digest))
        recorder.append(event("fork", 1.0))
        with pytest.raises(RunArtifactError):
            recorder.append(event("fork", 0.5))
        checkpoint(recorder, tmp_path, "brain-after.npz", origin="fork", data=b"after")
        recorder.append(event("fork", 1.0, type="checkpoint", checkpoint_name="brain-after.npz"))
    assert len(list(verify_run(tmp_path / "run").iter_events())) == 5


def test_fork_cannot_reference_a_checkpoint_before_its_event(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        recorder.append(event())
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        fork = event("fork", 0.0, parent_branch_id="root",
                     parent_checkpoint_sha256=digest)
        with pytest.raises(RunArtifactError):
            recorder.append(fork)
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
        recorder.append(fork)
        checkpoint(recorder, tmp_path, "brain-after.npz", origin="fork", data=b"after")
        recorder.append(event("fork", 0.0, type="checkpoint", checkpoint_name="brain-after.npz"))
    assert verify_run(target).manifest["event_count"] == 4


def test_fork_starts_at_exact_parent_checkpoint_clock(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        recorder.append(event(sim_ms=100.0, type="checkpoint",
                              checkpoint_name="brain-before.npz"))
        with pytest.raises(RunArtifactError):
            recorder.append(event("fork", 0.0, parent_branch_id="root",
                                  parent_checkpoint_sha256=digest))
        recorder.append(event("fork", 100.0, parent_branch_id="root",
                              parent_checkpoint_sha256=digest))
        checkpoint(recorder, tmp_path, "brain-after.npz", origin="fork", data=b"after")
        recorder.append(event("fork", 100.0, type="checkpoint",
                              checkpoint_name="brain-after.npz"))
    verified = verify_run(target)
    assert verified.manifest["checkpoints"]["brain-before.npz"]["sim_ms"] == 100.0
    assert [item["sim_ms"] for item in verified.iter_events()] == [100.0, 100.0, 100.0]


def test_digest_identical_durable_occurrences_require_an_exact_route(tmp_path):
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz", sim_tick=0))
        checkpoint(recorder, tmp_path, "same-state.npz")
        recorder.append(event(type="checkpoint", checkpoint_name="same-state.npz", sim_tick=0))
        parent = {"parent_branch_id": "root", "parent_checkpoint_sha256": digest}
        with pytest.raises(RunArtifactError, match="ambiguous"):
            recorder.append(event("ambiguous", **parent))
        explicit = {**parent, "parent_checkpoint_name": "same-state.npz", "parent_checkpoint_sequence": 1}
        recorder.append(event("exact", **explicit))
        with pytest.raises(RunArtifactError):
            recorder.append(event("exact", **{**explicit, "parent_checkpoint_sequence": 0}))
        checkpoint(recorder, tmp_path, "brain-after.npz", origin="exact", data=b"after")
        recorder.append(event("exact", type="checkpoint", checkpoint_name="brain-after.npz", sim_tick=0))
    assert verify_run(recorder.path).manifest["event_count"] == 4


def test_manifest_checkpoint_clock_must_match_its_event(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    assert verify_run(target).manifest["checkpoints"]["brain-before.npz"]["sim_ms"] == 0.0
    manifest_path = target / "run.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["checkpoints"]["brain-before.npz"]["sim_ms"] = 100.0
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8") + b"\n")
    with pytest.raises(RunArtifactError):
        verify_run(target)


def test_checkpoint_names_and_tampering_are_rejected(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        source = tmp_path / "source.npz"
        source.write_bytes(b"baseline")
        with pytest.raises(RunArtifactError):
            recorder.ingest_checkpoint("../escape.npz", source, origin_branch_id="root")
        with pytest.raises(RunArtifactError):
            recorder.ingest_checkpoint("CON.npz", source, origin_branch_id="root")
        seal(recorder, tmp_path)
    (target / "checkpoints" / "brain-before.npz").write_bytes(b"changed")
    with pytest.raises(RunArtifactError):
        verify_run(target)


def test_checkpoint_ingestion_is_durable_and_unique(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        source = tmp_path / "source.npz"
        source.write_bytes(b"baseline")
        recorder.ingest_checkpoint("brain-before.npz", source, origin_branch_id="root")
        source.unlink()
        assert (target / "checkpoints" / "brain-before.npz").read_bytes() == b"baseline"
        with pytest.raises(RunArtifactError):
            recorder.ingest_checkpoint("brain-before.npz", source, origin_branch_id="root")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
        checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    assert verify_run(target).manifest["checkpoints"]["brain-before.npz"]["size"] == 8


def test_missing_checkpoint_fails_verification(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    (target / "checkpoints" / "brain-after.npz").unlink()
    with pytest.raises(RunArtifactError):
        verify_run(target)


def test_qualification_requires_one_terminal_result_event(tmp_path):
    target = tmp_path / "qualification"
    recorder = RunRecorder(target, run_kind="qualification", metadata=METADATA,
                           root_branch_id="root")
    checkpoint(recorder, tmp_path, "brain-before.npz")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
    checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    with pytest.raises(RunArtifactError):
        recorder.close()
    with pytest.raises(RunArtifactError):
        verify_run(target)


def test_qualification_result_must_be_terminal(tmp_path):
    target = tmp_path / "qualification"
    with RunRecorder(target, run_kind="qualification", metadata=METADATA,
                     root_branch_id="root") as recorder:
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
        checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
        recorder.append(result_event(parent_branch_id="root",
                                     parent_checkpoint_sha256=digest))
        with pytest.raises(RunArtifactError):
            recorder.append(result_event())
        with pytest.raises(RunArtifactError):
            recorder.append(event("summary", 0.0, type="observation"))


@pytest.mark.parametrize(("changes", "missing"), [
    ({}, "status"), ({}, "family"), ({}, "seeds"),
    ({}, "selected_configuration"), ({}, "selected_window"),
    ({}, "selected_retention_ms"), ({}, "observed_effect_sign"),
    ({}, "benchmark"), ({}, "compute_seconds"),
    ({"status": "unknown"}, None),
    ({"status": []}, None),
    ({"family": "wrong"}, None), ({"seeds": [23, 11]}, None),
    ({"status": "supported"}, None),
    ({"selected_retention_ms": 10000.0}, None),
    ({"compute_seconds": -1.0}, None),
    ({"benchmark": {"simulated_seconds": 0.0, "event_count": 2,
                    "checkpoint_bytes": 10, "peak_event_buffer_bytes": 0,
                    "wall_seconds": 1.0}}, None),
    ({"benchmark": {"simulated_seconds": 0.0, "event_count": 2.5,
                    "checkpoint_bytes": 10, "peak_event_buffer_bytes": 0}}, None),
])
def test_append_rejects_incomplete_or_inconsistent_qualification_result(
    tmp_path, changes, missing,
):
    recorder = RunRecorder(tmp_path / "qualification", run_kind="qualification",
                           metadata=METADATA, root_branch_id="root")
    digest = checkpoint(recorder, tmp_path, "brain-before.npz")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
    checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    result = result_event(parent_branch_id="root", parent_checkpoint_sha256=digest,
                          **changes)
    if missing is not None:
        result.pop(missing)
    with pytest.raises(RunArtifactError):
        recorder.append(result)
    with pytest.raises(RunArtifactError):
        recorder.close()


def test_verify_run_rejects_rehashed_empty_qualification_result(tmp_path):
    target = tmp_path / "qualification"
    with RunRecorder(target, run_kind="qualification", metadata=METADATA,
                     root_branch_id="root") as recorder:
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
        checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
        recorder.append(result_event(parent_branch_id="root",
                                     parent_checkpoint_sha256=digest))
    events_path = target / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_bytes().splitlines()]
    terminal = {key: value for key, value in events[-1].items()
                if key in {"sequence", "type", "branch_id", "sim_ms",
                           "parent_branch_id", "parent_checkpoint_sha256",
                           "run_metadata_sha256", "previous_scientific_sha256"}}
    terminal["scientific_sha256"] = sha256(json.dumps(
        terminal, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    events[-1] = terminal
    raw_events = b"".join(json.dumps(item, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8") + b"\n"
                          for item in events)
    events_path.write_bytes(raw_events)
    manifest_path = target / "run.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["final_scientific_sha256"] = terminal["scientific_sha256"]
    manifest["events_sha256"] = sha256(raw_events).hexdigest()
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8") + b"\n")
    with pytest.raises(RunArtifactError):
        verify_run(target)


@pytest.mark.parametrize("changes", [
    {"selected_configuration": {"cs_duration_ms": 100.0,
                                 "dan_onset_ms": -100.0}},
    {"selected_configuration": {"cs_duration_ms": 10 ** 400,
                                 "dan_onset_ms": -100.0,
                                 "post_pair_gap_ms": 500.0}},
    {"selected_window": {"start_ms": 0.0, "end_ms": 100.0, "extra": 1}},
    {"selected_retention_ms": 0.0},
    {"observed_effect_sign": True},
    {"benchmark": {"simulated_seconds": 0.0, "event_count": True,
                   "checkpoint_bytes": 10, "peak_event_buffer_bytes": 0}},
])
def test_append_rejects_invalid_supported_result_fields(tmp_path, changes):
    recorder = RunRecorder(tmp_path / "qualification", run_kind="qualification",
                           metadata=METADATA, root_branch_id="root")
    digest = checkpoint(recorder, tmp_path, "brain-before.npz")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
    checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
    recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    valid = supported_result_event(parent_branch_id="root",
                                   parent_checkpoint_sha256=digest)
    valid.update(changes)
    with pytest.raises(RunArtifactError):
        recorder.append(valid)
    with pytest.raises(RunArtifactError):
        recorder.close()


def test_complete_supported_result_seals_and_verifies(tmp_path):
    target = tmp_path / "qualification"
    with RunRecorder(target, run_kind="qualification", metadata=METADATA,
                     root_branch_id="root") as recorder:
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
        checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
        recorder.append(supported_result_event(parent_branch_id="root",
                                               parent_checkpoint_sha256=digest))
    terminal = list(verify_run(target).iter_events())[-1]
    assert terminal["status"] == "supported"
    assert terminal["selected_configuration"]["dan_onset_ms"] == -100.0
    assert terminal["selected_retention_ms"] == 10000.0


def test_checkpoint_event_cannot_override_ingested_hash(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        checkpoint(recorder, tmp_path, "brain-before.npz")
        with pytest.raises(RunArtifactError):
            recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz",
                                  checkpoint_sha256=ZERO))
        seal_event = event(type="checkpoint", checkpoint_name="brain-before.npz")
        recorder.append(seal_event)
        checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    assert verify_run(target).manifest["event_count"] == 2


def test_verifier_rejects_checkpoint_directory_junction(tmp_path, monkeypatch):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    actual_is_junction = Path.is_junction
    checkpoint_dir = target / "checkpoints"
    monkeypatch.setattr(Path, "is_junction", lambda path: path == checkpoint_dir
                        or actual_is_junction(path))
    with pytest.raises(RunArtifactError):
        verify_run(target)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction substitution regression")
def test_checkpoint_directory_substitution_cannot_write_outside_run(tmp_path):
    target = tmp_path / "run"
    recorder = RunRecorder(target, run_kind="pilot", metadata=METADATA,
                           root_branch_id="root")
    checkpoint_dir = target / "checkpoints"
    checkpoint_dir.rename(tmp_path / "original-checkpoints")
    external = tmp_path / "external"
    external.mkdir()
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(checkpoint_dir), str(external)],
        capture_output=True, text=True,
    )
    if created.returncode != 0 or not checkpoint_dir.is_junction():
        pytest.skip(f"Windows junction creation unavailable: {created.stderr}")
    source = tmp_path / "source.npz"
    source.write_bytes(b"baseline")
    try:
        with pytest.raises(RunArtifactError):
            recorder.ingest_checkpoint("brain-before.npz", source,
                                       origin_branch_id="root")
        assert list(external.iterdir()) == []
    finally:
        with pytest.raises(RunArtifactError):
            recorder.close()
        checkpoint_dir.rmdir()


@pytest.mark.parametrize("mutation", ["truncate", "extra", "duplicate", "manifest", "identity"])
def test_verifier_fails_closed_on_changed_artifact(tmp_path, mutation):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    events_path = target / "events.jsonl"
    if mutation == "truncate":
        events_path.write_bytes(events_path.read_bytes()[:-1])
    elif mutation == "extra":
        with events_path.open("ab") as stream:
            stream.write(b"{}\n")
    elif mutation == "duplicate":
        line = events_path.read_text(encoding="utf-8").splitlines()[0]
        events_path.write_text(line.replace('"type":', '"type":"duplicate","type":', 1) + "\n", encoding="utf-8")
    else:
        manifest_path = target / "run.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if mutation == "manifest":
            manifest["metadata"]["family"] = "confirmation"
        else:
            manifest["metadata"]["engine_identity"]["version"] = "fake"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RunArtifactError):
        verify_run(target)


def test_streaming_iteration_revalidates_after_concurrent_mutation(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        recorder.append(event())
        seal(recorder, tmp_path)
    verified = verify_run(target)
    assert not hasattr(verified, "events")
    iterator = verified.iter_events()
    next(iterator)
    with (target / "events.jsonl").open("ab") as stream:
        stream.write(b"{}\n")
    with pytest.raises(RunArtifactError):
        list(iterator)


def test_pilot_cannot_be_relabelled_as_qualification(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    manifest_path = target / "run.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["run_kind"] = "qualification"
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8") + b"\n")
    with pytest.raises(RunArtifactError):
        verify_run(target)


def test_malformed_manifest_type_fails_with_project_error(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    manifest_path = target / "run.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["run_kind"] = []
    manifest_path.write_bytes(json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8") + b"\n")
    with pytest.raises(RunArtifactError):
        verify_run(target)


@pytest.mark.parametrize("malformed", [
    b'{"event_count":' + b"9" * 5000 + b'}\n',
    b'{"metadata":' + b"[" * 2000 + b'0}\n',
], ids=["integer-limit", "excessive-depth"])
def test_verify_run_wraps_parser_limits_in_project_error(tmp_path, malformed):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    (target / "run.json").write_bytes(malformed)
    with pytest.raises(RunArtifactError, match="Invalid (strict )?JSON"):
        verify_run(target)


def test_verify_run_preserves_duplicate_key_error(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    (target / "run.json").write_bytes(b'{"x":1,"x":2}\n')
    with pytest.raises(RunArtifactError, match="Duplicate JSON key: x"):
        verify_run(target)


def test_streaming_iteration_detects_rewrite_of_already_read_line(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        recorder.append(event(value="a"))
        seal(recorder, tmp_path)
    iterator = verify_run(target).iter_events()
    next(iterator)
    events_path = target / "events.jsonl"
    raw = events_path.read_bytes()
    events_path.write_bytes(raw.replace(b'"value":"a"', b'"value":"b"', 1))
    with pytest.raises(RunArtifactError):
        list(iterator)


def test_packaged_schema_is_bound_to_manifest(tmp_path):
    target = tmp_path / "run"
    with RunRecorder(target, run_kind="pilot", metadata=METADATA, root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    raw = files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes()
    schema = json.loads(raw)
    assert {"format_version", "schema_sha256", "metadata", "run_metadata_sha256", "checkpoints"} <= set(schema["required"])
    assert verify_run(target).manifest["schema_sha256"] == sha256(raw).hexdigest()


def test_tickless_legacy_inventory_and_events_stay_valid(tmp_path):
    from fly_connectome_sim.experiment.recorder import verify_replay_run
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    ordinary = verify_run(recorder.path)
    assert all("sim_tick" not in entry for entry in ordinary.manifest["checkpoints"].values())
    assert all("sim_tick" not in item for item in ordinary.iter_events())
    def no_anchor_factory():
        pytest.fail("Tickless legacy artifact has no anchors to reconstruct")
    formal = verify_replay_run(recorder.path, engine_factory=no_anchor_factory)
    assert formal.manifest == ordinary.manifest
    assert formal.replay_attested_state_anchors == frozenset()


@pytest.mark.parametrize("partial", ["branch", "digest", "exact"])
def test_schema_permits_runtime_valid_repeated_partial_ancestry(tmp_path, partial):
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        digest = checkpoint(recorder, tmp_path, "brain-before.npz")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-before.npz"))
        # Completeness remains stateful: this same partial declaration is invalid initially.
        fields = {"branch": {"parent_branch_id": "root"},
                  "digest": {"parent_checkpoint_sha256": digest},
                  "exact": {"parent_checkpoint_name": "brain-before.npz", "parent_checkpoint_sequence": 0}}[partial]
        with pytest.raises(RunArtifactError):
            recorder.append(event("child", **fields))
        recorder.append(event("child", parent_branch_id="root", parent_checkpoint_sha256=digest))
        recorder.append(event("child", **fields))
        checkpoint(recorder, tmp_path, "brain-after.npz", data=b"after")
        recorder.append(event(type="checkpoint", checkpoint_name="brain-after.npz"))
    item = list(verify_run(recorder.path).iter_events())[2]
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes())["$defs"]["event"]

    def matches(rule, value):
        """Evaluate only generic ancestry presence clauses, not a full schema validator."""
        if not set(rule.get("required", ())) <= value.keys():
            return False
        for name, declaration in rule.get("properties", {}).items():
            if name in value and "const" in declaration and value[name] != declaration["const"]:
                return False
        if any(name in value and not set(required) <= value.keys()
               for name, required in rule.get("dependentRequired", {}).items()):
            return False
        if "not" in rule and matches(rule["not"], value):
            return False
        if "oneOf" in rule and sum(matches(part, value) for part in rule["oneOf"]) != 1:
            return False
        if "anyOf" in rule and not any(matches(part, value) for part in rule["anyOf"]):
            return False
        if "if" in rule and matches(rule["if"], value):
            return matches(rule["then"], value)
        return all(matches(part, value) for part in rule.get("allOf", ()))

    ancestry = {"dependentRequired": schema["dependentRequired"], "not": schema["not"],
                "allOf": [rule for rule in schema["allOf"]
                          if rule["if"].get("properties", {}).get("type") == {}]}
    assert matches(ancestry, item)
    assert not matches(ancestry, {**item, "parent_checkpoint_sha256": digest,
                                 "parent_state_anchor_sha256": "b" * 64})
    assert not matches(ancestry, {**item, "parent_checkpoint_name": "brain-before.npz",
                                 "parent_checkpoint_sequence": 0, "parent_state_anchor_sha256": "b" * 64})


def test_anchor_schema_roundtrip_requires_strict_new_occurrences(tmp_path):
    # The declared typed boundaries must accept the actual persisted wire shape.
    with RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA,
                     root_branch_id="root") as recorder:
        seal(recorder, tmp_path)
    verified = verify_run(recorder.path)
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes())
    assert not set(verified.manifest) - schema["properties"].keys()
    assert "state_anchors" in schema["required"]
    entry = schema["properties"]["checkpoints"]["additionalProperties"]
    for data in verified.manifest["checkpoints"].values():
        assert not set(data) - entry["properties"].keys()
        assert set(entry["required"]) <= data.keys()
    for name in ("state_anchor", "black_retention_recipe", "source_occurrence", "scientific_prefix",
                 "black_input", "anchor_occurrence"):
        assert schema["$defs"][name]["additionalProperties"] is False


def test_qualification_result_schema_declares_required_conditional_contract():
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json")
                        .read_bytes())
    event_schema = schema["$defs"]["event"]
    result_schema = next(rule["then"] for rule in event_schema["allOf"]
                         if rule["if"]["properties"]["type"] == {"const": "qualification_result"})
    assert set(result_schema["required"]) == {
        "status", "family", "seeds", "selected_configuration", "selected_window",
        "selected_retention_ms", "observed_effect_sign", "benchmark",
        "compute_seconds",
    }
    assert result_schema["properties"]["status"]["enum"] == ["supported", "unsupported"]
    assert result_schema["properties"]["compute_seconds"] == {"type": "number", "minimum": 0}
    benchmark_schema = schema["$defs"]["qualification_benchmark"]
    assert benchmark_schema["additionalProperties"] is False
    assert set(benchmark_schema["required"]) == {
        "simulated_seconds", "event_count", "checkpoint_bytes",
        "peak_event_buffer_bytes",
    }
    for name in ("qualification_configuration", "qualification_window"):
        assert schema["$defs"][name]["additionalProperties"] is False
    status_cases = {rule["if"]["properties"]["status"]["const"]: rule["then"]
                    for rule in result_schema["allOf"]}
    assert set(status_cases) == {"supported", "unsupported"}
    assert status_cases["unsupported"]["properties"]["selected_retention_ms"] == {"type": "null"}
    assert status_cases["supported"]["properties"]["observed_effect_sign"] == {"enum": [-1, 1]}


CONFIRMATION_METADATA = {
    **METADATA, "family": "confirmation",
    "frozen_config_sha256": sha256(b"frozen").hexdigest(),
    "assay_contract": {"analysis_version": "mbon11-causal-analysis/v1"},
}
ASSAY_FIELDS = {
    "result_version", "analysis_version", "frozen_config_sha256", "status",
    "reasons", "report", "report_sha256", "evidence_event_count",
    "evidence_final_scientific_sha256",
}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def confirmation_prefix(tmp_path):
    recorder = RunRecorder(tmp_path / "confirmation", run_kind="confirmation",
                           metadata=CONFIRMATION_METADATA, root_branch_id="root")
    for name, data in (("brain-before.npz", b"before"), ("brain-after.npz", b"after")):
        checkpoint(recorder, tmp_path, name, data=data)
        recorder.append(event(type="checkpoint", checkpoint_name=name))
    return recorder


def assay_result(recorder, status="supported"):
    prefix = [json.loads(line) for line in (recorder.path / "events.jsonl").read_bytes().splitlines()]
    reasons = [] if status == "supported" else ["effect_floor", "missing_cell"]
    report = {"status": status, "values": {"cells": {}, "signed_delta": -1e300,
                                          "large_counter": 10 ** 400}, "reasons": reasons}
    return event(
        type="assay_result", result_version="mbon11-assay-result/v1",
        analysis_version="mbon11-causal-analysis/v1",
        frozen_config_sha256=CONFIRMATION_METADATA["frozen_config_sha256"],
        status=status, reasons=reasons, report=report,
        report_sha256=sha256(canonical_json(report)).hexdigest(),
        evidence_event_count=len(prefix),
        evidence_final_scientific_sha256=prefix[-1]["scientific_sha256"] if prefix else ZERO,
    )


def rewrite_sealed_run(target, events, manifest):
    """Rehash attacker-controlled bytes so integrity checks alone cannot reject them."""
    def scientific(value):
        if isinstance(value, dict):
            return {key: scientific(item) for key, item in value.items()
                    if key not in {"compute_seconds", "kernel_seconds"}}
        if isinstance(value, list):
            return [scientific(item) for item in value]
        return value

    metadata_digest = sha256(canonical_json({
        "run_kind": manifest["run_kind"], "root_branch_id": manifest["root_branch_id"],
        "metadata": manifest["metadata"],
    })).hexdigest()
    previous = ZERO
    for sequence, item in enumerate(events):
        item.update(sequence=sequence, previous_scientific_sha256=previous,
                    run_metadata_sha256=metadata_digest)
        item.pop("scientific_sha256", None)
        previous = sha256(canonical_json(scientific(item))).hexdigest()
        item["scientific_sha256"] = previous
    raw = b"".join(canonical_json(item) + b"\n" for item in events)
    (target / "events.jsonl").write_bytes(raw)
    manifest.update(event_count=len(events), final_scientific_sha256=previous,
                    events_sha256=sha256(raw).hexdigest(), run_metadata_sha256=metadata_digest)
    (target / "run.json").write_bytes(canonical_json(manifest) + b"\n")


@pytest.mark.parametrize("status", ["supported", "unsupported", "inconclusive"])
def test_confirmation_complete_terminal_roundtrip_is_structural(tmp_path, status):
    recorder = confirmation_prefix(tmp_path)
    result = assay_result(recorder, status)
    recorder.append(result)
    recorder.close()
    verified = verify_run(recorder.path)
    terminal = list(verified.iter_events())[-1]
    assert terminal["report"] == result["report"]
    assert terminal["evidence_event_count"] == terminal["sequence"] == 2
    assert terminal["evidence_final_scientific_sha256"] == terminal["previous_scientific_sha256"]
    assert verified.manifest["final_scientific_sha256"] == terminal["scientific_sha256"]


def test_confirmation_missing_result_cannot_seal(tmp_path):
    recorder = confirmation_prefix(tmp_path)
    with pytest.raises(RunArtifactError):
        recorder.close()
    assert not (recorder.path / "run.json").exists()
    with pytest.raises(RunArtifactError):
        verify_run(recorder.path)


@pytest.mark.parametrize("following", ["assay_result", "observation", "qualification_result"])
def test_confirmation_result_is_single_and_terminal(tmp_path, following):
    recorder = confirmation_prefix(tmp_path)
    recorder.append(assay_result(recorder))
    before = (recorder.path / "events.jsonl").read_bytes()
    invalid = assay_result(recorder) if following == "assay_result" else event(type=following)
    with pytest.raises(RunArtifactError):
        recorder.append(invalid)
    assert (recorder.path / "events.jsonl").read_bytes() == before
    assert not (recorder.path / "run.json").exists()
    recorder.close()
    assert verify_run(recorder.path).manifest["event_count"] == 3


@pytest.mark.parametrize("run_kind", ["pilot", "qualification"])
def test_assay_result_rejected_in_other_run_kinds(tmp_path, run_kind):
    recorder = RunRecorder(tmp_path / "run", run_kind=run_kind,
                           metadata=METADATA, root_branch_id="root")
    invalid = assay_result(recorder)
    with pytest.raises(RunArtifactError):
        recorder.append(invalid)
    assert not (recorder.path / "run.json").exists()
    for name in ("brain-before.npz", "brain-after.npz"):
        checkpoint(recorder, tmp_path, name)
        recorder.append(event(type="checkpoint", checkpoint_name=name))
    if run_kind == "qualification":
        recorder.append(result_event(branch="root"))
    recorder.close()
    assert verify_run(recorder.path).manifest["event_count"] == (3 if run_kind == "qualification" else 2)


@pytest.mark.parametrize(("field", "value"), [
    ("frozen_config_sha256", None), ("frozen_config_sha256", "bad"),
    ("frozen_config_sha256", "A" * 64), ("frozen_config_sha256", 1),
    ("assay_contract", None), ("assay_contract", []), ("assay_contract", {}),
    ("assay_contract", {"analysis_version": "wrong"}),
    ("assay_contract", {"analysis_version": []}),
])
def test_confirmation_metadata_bindings_rejected_before_directory(tmp_path, field, value):
    metadata = deepcopy(CONFIRMATION_METADATA)
    metadata[field] = value
    target = tmp_path / "confirmation"
    with pytest.raises(RunArtifactError):
        RunRecorder(target, run_kind="confirmation", metadata=metadata, root_branch_id="root")
    assert not target.exists()


@pytest.mark.parametrize("field", ["frozen_config_sha256", "assay_contract"])
def test_confirmation_missing_metadata_bindings_rejected_before_directory(tmp_path, field):
    metadata = deepcopy(CONFIRMATION_METADATA)
    metadata.pop(field)
    target = tmp_path / "confirmation"
    with pytest.raises(RunArtifactError):
        RunRecorder(target, run_kind="confirmation", metadata=metadata, root_branch_id="root")
    assert not target.exists()


INVALID_ASSAY_CHANGES = [
    {"result_version": "wrong"}, {"analysis_version": "wrong"},
    {"analysis_version": []}, {"frozen_config_sha256": ZERO},
    {"frozen_config_sha256": "bad"}, {"status": "unknown"}, {"status": []},
    {"reasons": "reason"}, {"reasons": [""]}, {"reasons": [1]},
    {"reasons": ["z", "a"]}, {"reasons": ["a", "a"]},
    {"reasons": ["reason"]}, {"status": "unsupported"},
    {"status": "inconclusive"}, {"report": None}, {"report": []},
    {"report": {"status": "supported", "reasons": []}},
    {"report": {"status": "supported", "values": [], "reasons": []}},
    {"report": {"status": "supported", "values": {}, "reasons": [], "extra": 1}},
    {"report": {"status": "unsupported", "values": {}, "reasons": []}},
    {"report": {"status": "supported", "values": {}, "reasons": ["reason"]}},
    {"report_sha256": ZERO}, {"report_sha256": "bad"},
    {"evidence_event_count": True}, {"evidence_event_count": 2.0},
    {"evidence_event_count": -1}, {"evidence_event_count": 1},
    {"evidence_event_count": 3}, {"evidence_event_count": "2"},
    {"evidence_final_scientific_sha256": ZERO},
    {"evidence_final_scientific_sha256": "bad"},
    {"type": "qualification_result"},
]


@pytest.mark.parametrize("changes", INVALID_ASSAY_CHANGES)
def test_confirmation_invalid_result_append_does_not_seal_or_advance(tmp_path, changes):
    recorder = confirmation_prefix(tmp_path)
    invalid = {**assay_result(recorder), **changes}
    if "report" in changes:
        invalid["report_sha256"] = sha256(canonical_json(invalid["report"])).hexdigest()
    before = (recorder.path / "events.jsonl").read_bytes()
    with pytest.raises(RunArtifactError):
        recorder.append(invalid)
    assert (recorder.path / "events.jsonl").read_bytes() == before
    assert not (recorder.path / "run.json").exists()
    with pytest.raises(RunArtifactError):
        recorder.close()
    assert not (recorder.path / "run.json").exists()


@pytest.mark.parametrize("missing", sorted(ASSAY_FIELDS))
def test_confirmation_incomplete_result_rejected(tmp_path, missing):
    recorder = confirmation_prefix(tmp_path)
    invalid = assay_result(recorder)
    invalid.pop(missing)
    with pytest.raises(RunArtifactError):
        recorder.append(invalid)
    with pytest.raises(RunArtifactError):
        recorder.close()
    assert not (recorder.path / "run.json").exists()


@pytest.mark.parametrize("changes", INVALID_ASSAY_CHANGES)
def test_confirmation_rehashed_invalid_result_rejected_by_verifier(tmp_path, changes):
    recorder = confirmation_prefix(tmp_path)
    recorder.append(assay_result(recorder))
    recorder.close()
    manifest = json.loads((recorder.path / "run.json").read_bytes())
    events = [json.loads(line) for line in (recorder.path / "events.jsonl").read_bytes().splitlines()]
    events[-1].update(changes)
    if "report" in changes:
        events[-1]["report_sha256"] = sha256(canonical_json(events[-1]["report"])).hexdigest()
    rewrite_sealed_run(recorder.path, events, manifest)
    with pytest.raises(RunArtifactError):
        verify_run(recorder.path)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "nonterminal", "incomplete",
                                      "pilot", "qualification", "metadata_digest", "metadata_version"])
def test_confirmation_rehashed_terminal_structure_and_metadata_rejected(tmp_path, mutation):
    recorder = confirmation_prefix(tmp_path)
    recorder.append(assay_result(recorder))
    recorder.close()
    manifest = json.loads((recorder.path / "run.json").read_bytes())
    events = [json.loads(line) for line in (recorder.path / "events.jsonl").read_bytes().splitlines()]
    if mutation == "missing":
        events.pop()
    elif mutation == "duplicate":
        terminal = deepcopy(events[-1])
        terminal.update(evidence_event_count=3,
                        evidence_final_scientific_sha256=events[-1]["scientific_sha256"])
        events.append(terminal)
    elif mutation == "nonterminal":
        events.append(event())
    elif mutation == "incomplete":
        for name in ASSAY_FIELDS:
            events[-1].pop(name)
    elif mutation in {"pilot", "qualification"}:
        manifest["run_kind"] = mutation
    elif mutation == "metadata_digest":
        manifest["metadata"].pop("frozen_config_sha256")
    else:
        manifest["metadata"]["assay_contract"]["analysis_version"] = "wrong"
    rewrite_sealed_run(recorder.path, events, manifest)
    with pytest.raises(RunArtifactError):
        verify_run(recorder.path)


@pytest.mark.parametrize("reasons", [[], [""], ["z", "a"], ["a", "a"], [1]])
@pytest.mark.parametrize("status", ["unsupported", "inconclusive"])
def test_confirmation_matching_report_still_requires_deterministic_reasons(tmp_path, status, reasons):
    recorder = confirmation_prefix(tmp_path)
    invalid = assay_result(recorder, status)
    invalid["reasons"] = invalid["report"]["reasons"] = reasons
    invalid["report_sha256"] = sha256(canonical_json(invalid["report"])).hexdigest()
    with pytest.raises(RunArtifactError):
        recorder.append(invalid)
    with pytest.raises(RunArtifactError):
        recorder.close()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), 10 ** 5000],
                         ids=["nan", "inf", "negative-inf", "integer-limit"])
def test_confirmation_report_numeric_serializer_boundaries_fail_closed(tmp_path, value):
    recorder = confirmation_prefix(tmp_path)
    invalid = assay_result(recorder)
    invalid["report"]["values"]["malformed"] = value
    with pytest.raises(RunArtifactError, match="Invalid strict JSON"):
        recorder.append(invalid)
    with pytest.raises(RunArtifactError):
        recorder.close()
    assert not (recorder.path / "run.json").exists()


def test_confirmation_supported_report_cannot_have_matching_nonempty_reasons(tmp_path):
    recorder = confirmation_prefix(tmp_path)
    invalid = assay_result(recorder)
    invalid["reasons"] = invalid["report"]["reasons"] = ["reason"]
    invalid["report_sha256"] = sha256(canonical_json(invalid["report"])).hexdigest()
    with pytest.raises(RunArtifactError):
        recorder.append(invalid)
    recorder.append(assay_result(recorder))
    recorder.close()
    assert verify_run(recorder.path).manifest["event_count"] == 3


@pytest.mark.parametrize("malformed", [b"NaN", b"Infinity", b"1e999", b"9" * 5000],
                         ids=["nan", "infinity", "overflowing-float", "integer-limit"])
def test_confirmation_rehashed_malformed_report_numbers_fail_closed(tmp_path, malformed):
    recorder = confirmation_prefix(tmp_path)
    recorder.append(assay_result(recorder))
    recorder.close()
    events_path = recorder.path / "events.jsonl"
    raw = events_path.read_bytes().replace(
        b'"large_counter":' + str(10 ** 400).encode(),
        b'"large_counter":' + malformed,
    )
    events_path.write_bytes(raw)
    manifest_path = recorder.path / "run.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["events_sha256"] = sha256(raw).hexdigest()
    manifest_path.write_bytes(canonical_json(manifest) + b"\n")
    with pytest.raises(RunArtifactError, match="Invalid (strict )?JSON|Nonfinite JSON"):
        verify_run(recorder.path)


def test_assay_result_schema_declares_required_conditional_contract():
    schema = json.loads(files("fly_connectome_sim.schemas").joinpath("run.schema.json").read_bytes())
    result = next(rule["then"] for rule in schema["$defs"]["event"]["allOf"]
                  if rule["if"]["properties"]["type"] == {"const": "assay_result"})
    assert set(result["required"]) == ASSAY_FIELDS
    assert result["properties"]["status"]["enum"] == ["supported", "unsupported", "inconclusive"]
    assert result["properties"]["result_version"] == {"const": "mbon11-assay-result/v1"}
    assert result["properties"]["analysis_version"] == {"const": "mbon11-causal-analysis/v1"}
    assert result["properties"]["evidence_event_count"] == {"type": "integer", "minimum": 0}
    for name in ("frozen_config_sha256", "report_sha256", "evidence_final_scientific_sha256"):
        assert result["properties"][name] == {"$ref": "#/$defs/digest"}
    report = schema["$defs"]["assay_report"]
    assert report["additionalProperties"] is False
    assert set(report["required"]) == {"status", "values", "reasons"}
    assert report["properties"]["values"] == {"type": "object"}
    reasons = schema["$defs"]["assay_reasons"]
    assert reasons["uniqueItems"] is True
    assert reasons["items"] == {"type": "string", "minLength": 1}
    metadata = next(rule["then"]["properties"]["metadata"] for rule in schema["allOf"]
                    if rule["if"]["properties"]["run_kind"] == {"const": "confirmation"})
    assert set(metadata["required"]) == {"frozen_config_sha256", "assay_contract"}
    assert metadata["properties"]["frozen_config_sha256"] == {"$ref": "#/$defs/digest"}
    contract = metadata["properties"]["assay_contract"]
    assert contract["required"] == ["analysis_version"]
    assert contract["properties"]["analysis_version"] == {"const": "mbon11-causal-analysis/v1"}
