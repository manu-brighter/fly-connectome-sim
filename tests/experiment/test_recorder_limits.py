"""Opt-in operational read ceilings preserve the complete artifact contract."""

from dataclasses import FrozenInstanceError, replace
from contextlib import contextmanager
from io import BytesIO
import os
from pathlib import Path

import pytest

from fly_connectome_sim.experiment import recorder as artifacts
from replay_helpers import map_engine_factory
from test_recorder import METADATA, event, seal
from test_replay import map_recording, seal_map_recording


@pytest.fixture
def sealed(tmp_path):
    recorder = artifacts.RunRecorder(tmp_path / "run", run_kind="pilot", metadata=METADATA,
                                    root_branch_id="root")
    recorder.append(event(value="tiny"))
    seal(recorder, tmp_path)
    return recorder.path


def limits_for(path, **changes):
    raw = (path / "events.jsonl").read_bytes()
    values = dict(max_manifest_bytes=len((path / "run.json").read_bytes()),
                  max_event_line_bytes=max(map(len, raw.splitlines(keepends=True))),
                  max_events_bytes=len(raw), max_events=len(raw.splitlines()),
                  max_checkpoints=len(list((path / "checkpoints").iterdir())))
    values.update(changes)
    return artifacts.RunReadLimits(**values)


def test_exact_limits_preserve_default_and_iterator(sealed):
    policy = limits_for(sealed)
    run = artifacts.verify_run(sealed, limits=policy)
    assert list(run.iter_events()) == list(artifacts.verify_run(sealed).iter_events())
    with pytest.raises(FrozenInstanceError):
        policy.max_events = 4


@pytest.mark.parametrize("field", ["max_manifest_bytes", "max_event_line_bytes", "max_events_bytes",
                                  "max_events", "max_checkpoints"])
def test_one_over_limit_rejected_but_default_accepts(sealed, field):
    policy = limits_for(sealed)
    with pytest.raises(artifacts.RunArtifactError, match="limit"):
        artifacts.verify_run(sealed, limits=replace(policy, **{field: getattr(policy, field) - 1}))
    assert len(list(artifacts.verify_run(sealed).iter_events())) == 3


@pytest.mark.parametrize("field", ["max_manifest_bytes", "max_event_line_bytes", "max_events_bytes",
                                  "max_events", "max_checkpoints"])
@pytest.mark.parametrize("value", [True, False, 0, -1, 1.0, "1", None])
def test_invalid_policy_fields_before_io(monkeypatch, field, value):
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: pytest.fail("Invalid policy did I/O"))
    values = dict.fromkeys(["max_manifest_bytes", "max_event_line_bytes", "max_events_bytes",
                           "max_events", "max_checkpoints"], 1)
    values[field] = value
    with pytest.raises(artifacts.RunArtifactError):
        artifacts.RunReadLimits(**values)


@pytest.mark.parametrize("value", [True, 1, 1.0, {}, "limits"])
def test_invalid_policy_object_before_io(monkeypatch, value):
    monkeypatch.setattr(Path, "is_dir", lambda *args: pytest.fail("Invalid policy did I/O"))
    with pytest.raises(artifacts.RunArtifactError):
        artifacts.verify_run("unused", limits=value)


class ReadSpy(BytesIO):
    def __init__(self, raw, reads):
        super().__init__(raw)
        self.reads = reads

    def read(self, size=-1):
        assert size > 0, "Unbounded read"
        self.reads.append(size)
        return super().read(size)

    def readline(self, size=-1):
        assert size > 0, "Unbounded line read"
        self.reads.append(size)
        return super().readline(size)


def test_manifest_bound_before_decode_despite_false_stat(sealed, monkeypatch):
    policy = limits_for(sealed, max_manifest_bytes=7)
    original = Path.open
    reads = []
    monkeypatch.setattr(Path, "open", lambda path, *args, **kwargs:
                        ReadSpy(b"invalid json beyond cap", reads) if path.name == "run.json"
                        else original(path, *args, **kwargs))
    with pytest.raises(artifacts.RunArtifactError, match="Manifest.*limit"):
        artifacts.verify_run(sealed, limits=policy)
    assert reads == [8]


@pytest.mark.parametrize("line_cap,total_cap,expected", [(7, 20, 8), (20, 7, 8)])
def test_jsonl_bounds_before_decode(sealed, monkeypatch, line_cap, total_cap, expected):
    policy = limits_for(sealed, max_event_line_bytes=line_cap, max_events_bytes=total_cap)
    original = Path.open
    reads = []
    monkeypatch.setattr(Path, "open", lambda path, *args, **kwargs:
                        ReadSpy(b"invalid json beyond cap\n", reads) if path.name == "events.jsonl"
                        else original(path, *args, **kwargs))
    with pytest.raises(artifacts.RunArtifactError, match="limit"):
        artifacts.verify_run(sealed, limits=policy)
    assert reads == [expected]


def test_actual_event_limit_does_not_truncate_at_declared_count(sealed, monkeypatch):
    policy = limits_for(sealed, max_events=3, max_events_bytes=10000)
    original = Path.open
    raw = (sealed / "events.jsonl").read_bytes()
    reads = []
    monkeypatch.setattr(Path, "open", lambda path, *args, **kwargs:
                        ReadSpy(raw + b"not json\n", reads) if path.name == "events.jsonl"
                        else original(path, *args, **kwargs))
    with pytest.raises(artifacts.RunArtifactError, match="Event count.*limit"):
        artifacts.verify_run(sealed, limits=policy)
    assert len(reads) == 4


def test_checkpoint_directory_stops_at_cap_plus_one(sealed, monkeypatch):
    policy = limits_for(sealed)
    visited = []
    closed = []
    @contextmanager
    def entries(path):
        def generated():
            for number in range(10):
                visited.append(number)
                yield path / f"extra-{number}.npz"
        try:
            yield generated()
        finally:
            closed.append(True)
    monkeypatch.setattr(artifacts.os, "scandir", entries)
    monkeypatch.setattr(Path, "iterdir", lambda *args: pytest.fail("Directory list allocated"))
    monkeypatch.setattr(artifacts.os, "listdir", lambda *args: pytest.fail("Directory list allocated"))
    with pytest.raises(artifacts.RunArtifactError, match="Checkpoint.*limit"):
        artifacts.verify_run(sealed, limits=policy)
    assert visited == [0, 1, 2]
    assert closed == [True]


def test_iterator_retains_manifest_limit(sealed):
    run = artifacts.verify_run(sealed, limits=limits_for(sealed))
    with (sealed / "run.json").open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(artifacts.RunArtifactError, match="Manifest.*limit"):
        list(run.iter_events())


def test_final_digest_is_bounded_when_stream_grows(sealed, monkeypatch):
    policy = limits_for(sealed)
    raw = (sealed / "events.jsonl").read_bytes()
    original = Path.open
    reads, opens = [], []
    def opened(path, *args, **kwargs):
        if path.name == "events.jsonl":
            opens.append(path)
            if len(opens) == 2:
                return ReadSpy(raw + b"x", reads)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(artifacts.RunArtifactError, match="Event bytes.*limit"):
        artifacts.verify_run(sealed, limits=policy)
    assert sum(reads) <= len(raw) + 2


@pytest.mark.parametrize("mutation", ["missing_lf", "corrupt_tail", "digest"])
def test_limits_preserve_integrity_rejection(sealed, mutation):
    policy = limits_for(sealed, max_events_bytes=10000, max_event_line_bytes=10000, max_events=4)
    path = sealed / "events.jsonl"
    raw = path.read_bytes()
    if mutation == "missing_lf":
        raw = raw[:-1]
    elif mutation == "corrupt_tail":
        raw += b"{}\n"
    else:
        raw = raw.replace(b"tiny", b"tIny")
    path.write_bytes(raw)
    with pytest.raises(artifacts.RunArtifactError):
        artifacts.verify_run(sealed, limits=policy)


@pytest.mark.parametrize("field", ["event_count", "checkpoints"])
def test_declared_counts_rejected_before_opening_payloads(sealed, monkeypatch, field):
    policy = limits_for(sealed, max_manifest_bytes=10000)
    manifest = artifacts.verify_run(sealed).manifest
    if field == "event_count":
        manifest[field] = 4
    else:
        manifest[field]["extra.npz"] = manifest[field]["brain-before.npz"]
    (sealed / "run.json").write_bytes(artifacts._canonical(manifest) + b"\n")
    original = Path.open
    def opened(path, *args, **kwargs):
        if path.name == "events.jsonl" or path.suffix == ".npz":
            pytest.fail("Over-limit declaration reached payload files")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(artifacts.RunArtifactError, match="Declared.*limit"):
        artifacts.verify_run(sealed, limits=policy)


@pytest.mark.parametrize("during_iteration", [False, True])
def test_final_manifest_recheck_keeps_limit(sealed, monkeypatch, during_iteration):
    policy = limits_for(sealed)
    run = artifacts.verify_run(sealed, limits=policy) if during_iteration else None
    original = Path.open
    raw = (sealed / "run.json").read_bytes()
    opens, reads = [], []
    def opened(path, *args, **kwargs):
        if path.name == "run.json":
            opens.append(path)
            if len(opens) == 2:
                return ReadSpy(raw + b" ", reads)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(artifacts.RunArtifactError, match="Manifest.*limit"):
        if during_iteration:
            list(run.iter_events())
        else:
            artifacts.verify_run(sealed, limits=policy)
    assert reads == [policy.max_manifest_bytes + 1]


@pytest.mark.parametrize("pass_number", [1, 2])
def test_false_stat_does_not_bypass_actual_stream_bytes(sealed, monkeypatch, pass_number):
    policy = limits_for(sealed)
    run = artifacts.verify_run(sealed, limits=policy) if pass_number == 2 else None
    original_stat = Path.stat
    def false_stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if path.name in {"run.json", "events.jsonl"}:
            fields = list(result)
            fields[6] = 0
            return os.stat_result(fields)
        return result
    monkeypatch.setattr(Path, "stat", false_stat)
    with (sealed / "events.jsonl").open("ab") as stream:
        stream.write(b"x")
    with pytest.raises(artifacts.RunArtifactError, match="Event bytes.*limit"):
        if run is None:
            artifacts.verify_run(sealed, limits=policy)
        else:
            list(run.iter_events())


def test_lf_counts_towards_line_limit(sealed):
    raw = (sealed / "events.jsonl").read_bytes()
    policy = limits_for(sealed, max_event_line_bytes=max(map(len, raw.splitlines())))
    with pytest.raises(artifacts.RunArtifactError, match="Event line bytes.*limit"):
        artifacts.verify_run(sealed, limits=policy)


def test_remaining_total_bounds_each_read_and_requires_eof(sealed, monkeypatch):
    policy = limits_for(sealed)
    raw = (sealed / "events.jsonl").read_bytes()
    original = Path.open
    reads = []
    monkeypatch.setattr(Path, "open", lambda path, *args, **kwargs:
                        ReadSpy(raw, reads) if path.name == "events.jsonl"
                        else original(path, *args, **kwargs))
    assert len(list(artifacts._raw_events(sealed, limits=policy))) == 3
    remaining = len(raw)
    expected = []
    for line in raw.splitlines(keepends=True):
        expected.append(min(policy.max_event_line_bytes + 1, remaining + 1))
        remaining -= len(line)
    assert reads == [*expected, 1]


@pytest.mark.parametrize("mutation", ["manifest", "events", "checkpoints"])
def test_actual_native_attestation_accessors_retain_limits(tmp_path, map_engine_factory, mutation):
    recorder, engine = map_recording(map_engine_factory, tmp_path, anchors=1)
    seal_map_recording(recorder, engine, tmp_path)
    policy = limits_for(recorder.path)
    run = artifacts.verify_run(recorder.path, limits=policy)
    artifacts._replay_verified(run, engine_factory=map_engine_factory)
    assert len(run.replay_attested_state_anchors) == 1
    if mutation == "checkpoints":
        (recorder.path / "checkpoints" / "extra.npz").write_bytes(b"extra")
    else:
        path = recorder.path / ("run.json" if mutation == "manifest" else "events.jsonl")
        with path.open("ab") as stream:
            stream.write(b" ")
    with pytest.raises(artifacts.RunArtifactError, match="limit"):
        _ = run.replay_attested_state_anchors
    with pytest.raises(artifacts.RunArtifactError, match="limit"):
        _ = run.verification_mode
