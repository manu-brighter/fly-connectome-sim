"""Integrity contracts for sealed qualification artifacts."""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files
import json
import os
from pathlib import Path
import subprocess

import pytest

from fly_connectome_sim.experiment.recorder import RunArtifactError, RunRecorder, verify_run


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
