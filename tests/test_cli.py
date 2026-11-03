"""CLI artifact boundary tests."""

from __future__ import annotations

import json

import pytest

from fly_connectome_sim.cli import main
from fly_connectome_sim.experiment.recorder import verify_run


def test_qualification_metadata_declares_real_population_and_heldout_pixels():
    from fly_connectome_sim.cli import _qualification_metadata
    from fly_connectome_sim.engine import _rgb_input_sha256
    from fly_connectome_sim.experiment.stimuli import AssayStimuli
    import numpy as np

    identity = {"version": "tiny/v1", "neural_groups": {"mbon11": [8, 9]}}
    metadata = _qualification_metadata(identity)
    assert metadata["qualification_version"] == "mbon11-qualification/v1"
    assert metadata["aggregation"] == "raw-bin-mean-rate/v1"
    assert metadata["exclusions"] == []
    assert metadata["mbon11_population_size"] == 2
    assert metadata["candidate_identity"] == "kc-mbon11-ppl101/v1"
    black = _rgb_input_sha256(np.zeros((32, 32, 3), dtype=np.uint8))
    assert metadata["black_input"] == {
        "generator": "black-rgb/v1", "input_dtype": "uint8",
        "input_shape": [32, 32, 3], "input_sha256": black,
    }
    assert metadata["rgb_input_sha256"]["black"] == black
    assert metadata["confirmation_input_sha256"] == {
        str(seed): {**{name: _rgb_input_sha256(AssayStimuli(seed, "confirmation").frame(name))
                      for name in ("A", "B", "C")}, "black": black}
        for seed in (101, 113)
    }


def test_verify_run_cli_fails_closed(tmp_path, capsys):
    assert main(["verify-run", str(tmp_path / "missing")]) != 0
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip()


def test_event_choice_cli_validates_import_before_engine(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli

    def forbidden():
        raise AssertionError("Invalid proposal constructed an engine")

    monkeypatch.setattr(cli.FlyEngine, "from_prepared_graph", forbidden)
    target = tmp_path / "event-run"
    assert main(["event-choice", "--proposal", str(tmp_path / "missing.json"),
                 "--output-dir", str(target)]) == 1
    assert not target.exists()
    assert capsys.readouterr().err


def test_event_export_cli_commands_fail_closed(tmp_path, capsys):
    for command in ("export-event-replay", "export-event-plan"):
        output = tmp_path / f"{command}.json"
        assert main([command, str(tmp_path / "missing"), "--output", str(output)]) == 1
        assert not output.exists()
        assert capsys.readouterr().err


def test_event_cli_has_no_selection_or_threshold_override(tmp_path, capsys):
    import pytest

    for name in ("--selected-option-id", "--action-threshold-hz", "--cycles"):
        with pytest.raises(SystemExit) as error:
            main(["event-choice", "--proposal", "options.json", "--output-dir", str(tmp_path / "run"), name, "1"])
        assert error.value.code == 2
    capsys.readouterr()


def test_event_export_cli_reports_bound_plan_and_replay(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli

    calls = []
    def replay(source, output):
        calls.append(("replay", source, output))
        return {"version": "event-choice-replay/v1", "duration_ticks": 20000,
                "segments": [{}, {}, {}, {}], "source": {"verification_mode": "integrity-only"}}
    def plan(source, output):
        calls.append(("plan", source, output))
        return {"version": "event-plan/v1", "status": "deferred", "selected_option_id": None,
                "source": {"verification_mode": "integrity-only"}}
    monkeypatch.setattr(cli, "export_event_replay", replay)
    monkeypatch.setattr(cli, "export_event_plan", plan)
    source = tmp_path / "source"
    output = tmp_path / "output.json"
    assert main(["export-event-replay", str(source), "--output", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["duration_ticks"] == 20000 and result["segment_count"] == 4
    assert main(["export-event-plan", str(source), "--output", str(output)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "deferred" and result["selected_option_id"] is None
    assert calls == [("replay", source, output), ("plan", source, output)]


def test_observation_cli_rejects_invalid_cycles_before_engine(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli

    def forbidden():
        raise AssertionError("invalid request must not construct an engine")

    monkeypatch.setattr(cli.FlyEngine, "from_prepared_graph", forbidden)
    target = tmp_path / "invalid"
    assert main(["observe", "--output-dir", str(target), "--cycles", "11"]) == 1
    assert not target.exists()
    output = capsys.readouterr()
    assert output.out == "" and "cycles" in output.err


def test_export_replay_cli_missing_source_is_fail_closed(tmp_path, capsys):
    target = tmp_path / "replay.json"
    assert main(["export-replay", str(tmp_path / "missing"), "--output", str(target)]) == 1
    assert not target.exists()
    output = capsys.readouterr()
    assert output.out == "" and output.err


def test_video_observation_cli_rejects_missing_playlist_before_engine(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli

    def forbidden():
        raise AssertionError("invalid video request constructed an engine")

    monkeypatch.setattr(cli.FlyEngine, "from_prepared_graph", forbidden)
    target = tmp_path / "video-run"
    assert main(["observe-video", "--playlist", str(tmp_path / "missing.json"),
                 "--output-dir", str(target)]) == 1
    assert not target.exists()
    output = capsys.readouterr()
    assert output.out == "" and "playlist" in output.err.lower()


def test_export_video_replay_cli_missing_source_is_fail_closed(tmp_path, capsys):
    target = tmp_path / "video-replay.json"
    assert main(["export-video-replay", str(tmp_path / "missing"),
                 "--output", str(target)]) == 1
    assert not target.exists()
    output = capsys.readouterr()
    assert output.out == "" and output.err


def test_qualify_cli_uses_fixed_declaration_and_refuses_overwrite(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli

    class FakeEngine:
        def identity(self):
            return {"version": "tiny/v1", "sha256": "tiny-engine", "neural_groups": {"mbon11": [8]}}

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



def test_video_cli_selects_closed_profile_before_native_construction(tmp_path, monkeypatch, capsys):
    import pytest
    from fly_connectome_sim import cli

    profiles = []
    def capture(output_dir, *, playlist_path, engine_factory, profile):
        profiles.append(profile)
        raise ValueError("profile selected before native")
    monkeypatch.setattr(cli, "record_video_observation_run", capture)
    common = ["observe-video", "--playlist", str(tmp_path / "missing.json")]
    assert main(common) == 1
    assert main([*common, "--profile", "fast-feed"]) == 1
    assert main([*common, "--profile", "standard"]) == 1
    assert profiles == ["standard", "fast-feed", "standard"]
    with pytest.raises(SystemExit) as error:
        main([*common, "--profile", "custom"])
    assert error.value.code == 2
    assert profiles == ["standard", "fast-feed", "standard"]
    capsys.readouterr()
@pytest.mark.parametrize("command", ["export-session-replay", "export-session-plan"])
def test_session_export_cli_is_bound_to_closed_exporter(tmp_path, monkeypatch, capsys, command):
    from fly_connectome_sim import cli

    calls = []
    def export(path, output):
        calls.append((path, output))
        return {"version": "feed-event-replay/v1" if command.endswith("replay") else "event-plan/v1",
                "source": {"verification_mode": "integrity-only"}, "duration_ticks": 60000,
                "segments": [{}, {}], "status": "deferred", "selected_option_id": None}
    monkeypatch.setattr(cli, command.replace("-", "_"), export)
    source, output = tmp_path / "run", tmp_path / "out.json"
    assert cli.main([command, str(source), "--output", str(output)]) == 0
    assert calls == [(source, output)]
    assert json.loads(capsys.readouterr().out)["verification_mode"] == "integrity-only"


@pytest.mark.parametrize("override", ["--profile", "--seed", "--threshold", "--winner", "--duration"])
def test_session_cli_has_no_behavior_overrides(tmp_path, override):
    from fly_connectome_sim.cli import main

    with pytest.raises(SystemExit):
        main(["feed-event-session", "--playlist", "videos.json", "--proposal", "options.json",
              "--output-dir", str(tmp_path / "run"), override, "1"])


def test_session_cli_missing_input_fails_before_graph(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli

    def forbidden():
        pytest.fail("invalid input constructed graph")
    monkeypatch.setattr(cli.FlyEngine, "from_prepared_graph", forbidden)
    assert cli.main(["feed-event-session", "--playlist", "missing.json", "--proposal", "missing.json",
                     "--output-dir", str(tmp_path / "run")]) == 1
    assert not (tmp_path / "run").exists()
