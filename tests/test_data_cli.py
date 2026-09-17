from hashlib import sha256
import json
import os
import subprocess
import sys

import pytest


@pytest.fixture
def source_directory(tmp_path):
    directory = tmp_path / "source"
    directory.mkdir()
    payload = b"ARROW1-test-ARROW1"
    (directory / "released.feather").write_bytes(payload)
    (directory / "manifest.json").write_text(
        json.dumps({"files": [{
            "name": "released.feather",
            "logicalName": "annotations.feather",
            "bytes": len(payload),
            "sha256": sha256(payload).hexdigest(),
        }]}),
        encoding="utf-8",
    )
    return directory


def run_data(*arguments, runtime):
    return subprocess.run(
        [sys.executable, "-m", "jogge_fly_brain.data", *map(str, arguments)],
        env={**os.environ, "JOGGE_FLY_DATA": str(runtime)},
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("explicit_directory", [False, True])
def test_data_cli_verifies_and_stages_into_configured_runtime(
    source_directory, tmp_path, explicit_directory,
):
    runtime = tmp_path / "configured-runtime"
    arguments = ["stage", source_directory]
    environment_runtime = runtime
    if explicit_directory:
        arguments.extend(["--runtime-directory", runtime])
        environment_runtime = tmp_path / "unused-runtime"

    verified = run_data("verify-sources", source_directory, runtime=runtime)
    staged = run_data(*arguments, runtime=environment_runtime)

    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout) == {"files": 1, "bytes": 18}
    assert staged.returncode == 0, staged.stderr
    target = runtime / "annotations.feather"
    assert target.read_bytes() == b"ARROW1-test-ARROW1"
    assert target.stat().st_ino == (source_directory / "released.feather").stat().st_ino


@pytest.mark.parametrize("command", ["verify-sources", "stage"])
def test_data_cli_rejects_corrupt_sources_before_staging(
    source_directory, tmp_path, command,
):
    (source_directory / "released.feather").write_bytes(b"corrupt")
    runtime = tmp_path / "runtime"

    result = run_data(command, source_directory, runtime=runtime)

    assert result.returncode != 0
    assert "Size mismatch: released.feather" in result.stderr
    assert not runtime.exists()


@pytest.mark.parametrize("explicit_directory", [False, True])
def test_data_cli_prepared_gate_uses_configured_runtime(tmp_path, explicit_directory):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "annotations.feather").write_bytes(b"corrupt")
    arguments = ["verify-prepared"]
    environment_runtime = runtime
    if explicit_directory:
        arguments.extend(["--runtime-directory", runtime])
        environment_runtime = tmp_path / "unused-runtime"

    result = run_data(*arguments, runtime=environment_runtime)

    assert result.returncode != 0
    assert "Size mismatch: annotations.feather" in result.stderr
