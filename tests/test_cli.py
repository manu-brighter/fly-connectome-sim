"""CLI artifact boundary tests."""

from __future__ import annotations

import json

from fly_connectome_sim.cli import main
from fly_connectome_sim.experiment.recorder import verify_run


def test_verify_run_cli_fails_closed(tmp_path, capsys):
    assert main(["verify-run", str(tmp_path / "missing")]) != 0
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip()


def test_qualify_cli_uses_fixed_declaration_and_refuses_overwrite(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli

    class FakeEngine:
        def identity(self):
            return {"version": "tiny/v1", "sha256": "tiny-engine"}

    def fake_qualify(factory, recorder, *, seeds, family):
        assert seeds == (11, 23) and family == "qualification"
        assert factory().identity() == recorder.metadata["engine_identity"]
        from pathlib import Path
        source = Path(recorder.path).parent / "fake.npz"
        source.write_bytes(b"before")
        baseline_digest = recorder.ingest_checkpoint("brain-before.npz", source,
                                                       origin_branch_id="qualification/baseline")
        recorder.append({"type": "qualification_checkpoint", "branch_id": "qualification/baseline", "sim_ms": 0.0, "checkpoint_name": "brain-before.npz"})
        source.write_bytes(b"after")
        recorder.ingest_checkpoint("brain-after.npz", source, origin_branch_id="qualification/baseline")
        recorder.append({"type": "qualification_checkpoint", "branch_id": "qualification/baseline", "sim_ms": 0.0, "checkpoint_name": "brain-after.npz"})
        recorder.append({
            "type": "qualification_result", "branch_id": "qualification/summary",
            "sim_ms": 0.0, "parent_branch_id": "qualification/baseline",
            "parent_checkpoint_sha256": baseline_digest,
            "status": "unsupported", "family": "qualification", "seeds": [11, 23],
            "selected_configuration": None, "selected_window": None,
            "selected_retention_ms": None, "observed_effect_sign": None,
            "benchmark": {"simulated_seconds": 0.0, "event_count": 2,
                          "checkpoint_bytes": 11, "peak_event_buffer_bytes": 0},
            "compute_seconds": 0.0,
        })
        return type("Result", (), {"status": "unsupported", "benchmark": {"event_count": 2}})()

    calls = []

    def fake_engine():
        calls.append(1)
        return FakeEngine()

    monkeypatch.setattr(cli.FlyEngine, "from_prepared_graph", fake_engine)
    monkeypatch.setattr(cli, "qualify", fake_qualify)
    target = tmp_path / "qualification"
    assert main(["qualify", "--output-dir", str(target)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "unsupported"
    manifest = verify_run(target).manifest
    assert manifest["run_kind"] == "qualification"
    assert manifest["metadata"]["configuration"] == {
        "pulse_duration_ms": 100.0,
        "external_dan_current_mv": 20.0,
        "unpaired_minimum_separation_ms": 10000.0,
    }
    assert main(["qualify", "--output-dir", str(target)]) != 0
    assert capsys.readouterr().err.strip()
    assert len(calls) == 1
    assert main(["verify-run", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["event_count"] == 3
