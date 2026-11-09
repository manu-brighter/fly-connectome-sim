"""Thin continuous-probe adapter to the source-bound Windows owned-job monitor.

Private dependencies from frozen market_supervision: runtime inventory, safe
paths/files/JSON/inventories, release handshake, compiler guard, WindowsProcess,
ancestry validation, fixed limits, owned monitor and receipt encoding. The
monitor's receipt version/field names retain their original meanings; its output
byte field already counts evidence/scratch. No monitor globals are modified.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import sys

import market_supervision as _monitor
from market_artifacts import _safe_directory, write_json_exclusive


ROOT = Path(__file__).resolve().parents[1]
VERSION = "continuous-motor-supervision/v1"
# The legacy key means combined output/evidence INCLUDING its scratch subtree.
# Map the new protocol's explicit scratch name to that unchanged monitor key.
LIMITS = {"wall_seconds": 900, "peak_rss_bytes": 4 * 1024**3,
          "new_output_evidence_scratch_bytes": 256 * 1024**2, "poll_seconds_max": 2}
_legacy_configuration = _monitor._configuration
_paths, _file, _json, _inventory = _monitor._paths, _monitor._file, _monitor._json, _monitor._inventory
compiler_probe_guard = _monitor.compiler_probe_guard
WindowsProcess = _monitor.WindowsProcess
_new_bytes, request_cancellation = _monitor._new_bytes, _monitor.request_cancellation


def _same(first, second) -> bool:
    """Canonical JSON equality preserves bool/number type distinctions."""
    return _monitor._encoded(first) == _monitor._encoded(second)


def _wait_for_release(evidence: Path, binding: dict, *, timeout: float = 30) -> None:
    _monitor._wait_for_release(evidence, binding, timeout=timeout)
    if not _same(_json(evidence / "release.json"), binding):
        raise ValueError("Supervision release binding type/value differs")


def _configuration() -> dict:
    return {
        "legacy_runtime_configuration": _legacy_configuration(),
        "files": {name: _file(path) for name, path in {
            "entrypoint": ROOT / "scripts/run-continuous-motor-probe.py",
            "helper": Path(__file__).resolve(),
            "supervisor": ROOT / "scripts/supervise-continuous-motor.ps1",
        }.items()},
    }


def _readiness(output: Path, evidence: Path, protocol_hash: str) -> dict:
    if not _monitor.HASH.fullmatch(protocol_hash) or _file(output / "protocol.json")["sha256"] != protocol_hash:
        raise ValueError("Prepared continuous protocol hash differs")
    protocol = _json(output / "protocol.json")
    declared = protocol.get("limits")
    if (protocol.get("version") != "continuous-motor-probe/v1" or type(declared) is not dict
            or not _same({name: declared.get(name) for name in LIMITS}, LIMITS)):
        raise ValueError("Continuous protocol/version/fixed limits differ")
    mapped = {"new_output_evidence_bytes" if name == "new_output_evidence_scratch_bytes" else name: value
              for name, value in LIMITS.items()}
    if not _same(mapped, _monitor.LIMITS):
        raise ValueError("Frozen monitor limits differ from continuous protocol")
    return {"version": VERSION, "output_directory": str(output), "evidence_directory": str(evidence),
            "protocol_sha256": protocol_hash, "configuration": _configuration(), "limits": dict(LIMITS)}


def prepare(output: Path, evidence: Path, protocol_hash: str) -> dict:
    output, evidence = _paths(output, evidence)
    _inventory(output, {"protocol.json"})
    if evidence.exists():
        raise ValueError("Evidence directory must be new")
    readiness = _readiness(output, evidence, protocol_hash)
    evidence.mkdir()
    write_json_exclusive(readiness, evidence / "readiness.json")
    return readiness


def validate_prepared(output: Path, evidence: Path, protocol_hash: str, readiness_hash: str) -> dict:
    output, evidence = _paths(output, evidence)
    _inventory(output, {"protocol.json"})
    _inventory(evidence, {"readiness.json"})
    if not _monitor.HASH.fullmatch(readiness_hash) or _file(evidence / "readiness.json")["sha256"] != readiness_hash:
        raise ValueError("Readiness hash differs")
    readiness = _json(evidence / "readiness.json")
    if not _same(readiness, _readiness(output, evidence, protocol_hash)):
        raise ValueError("Prepared continuous source/path/configuration identity differs")
    return readiness


@contextmanager
def production_start(output: Path, protocol_hash: str, evidence: Path | None,
                     readiness_hash: str | None, token: str | None):
    if evidence is None or not isinstance(readiness_hash, str) or not isinstance(token, str):
        raise ValueError("Native execution requires supervision directory/hash/start token")
    if not _monitor.HASH.fullmatch(readiness_hash) or not _monitor.HASH.fullmatch(token):
        raise ValueError("Invalid supervision hash/token")
    output, evidence = _paths(output, evidence)
    if _file(evidence / "readiness.json")["sha256"] != readiness_hash:
        raise ValueError("Supervision readiness hash differs")
    readiness = _json(evidence / "readiness.json")
    if not _same(readiness, _readiness(output, evidence, protocol_hash)):
        raise ValueError("Continuous supervision source/path/configuration differs")
    scratch = evidence / "scratch"
    _safe_directory(scratch)
    if any(Path(os.environ.get(name, "")).absolute() != scratch for name in ("TMP", "TEMP")):
        raise ValueError("Child temporary files must use counted supervision scratch")
    binding = {"pid": os.getpid(), "start_token": token,
               "protocol_sha256": protocol_hash, "readiness_sha256": readiness_hash}
    _wait_for_release(evidence, binding)
    if not _same(readiness["configuration"], _configuration()):
        raise ValueError("Prepared native/source identity changed before release")
    runtime = readiness["configuration"]["legacy_runtime_configuration"]
    with compiler_probe_guard(runtime["compiler_version_argv"]):
        yield


def _validate_owner(owner: WindowsProcess) -> None:
    if owner is None or owner.exited() or not _monitor._descends(os.getpid(), owner.pid):
        raise ValueError("PowerShell owner identity/descent differs")


def run(output: Path, evidence: Path, protocol_hash: str, readiness_hash: str, *, owner: WindowsProcess) -> dict:
    _validate_owner(owner)
    readiness = validate_prepared(output, evidence, protocol_hash, readiness_hash)
    output, evidence = _paths(output, evidence)
    config = readiness["configuration"]
    runtime = config["legacy_runtime_configuration"]
    token = secrets.token_hex(32)
    os.environ["FLY_CONNECTOME_SIM_CXX"] = runtime["files"]["compiler"]["path"]
    os.environ["FLY_CONNECTOME_SIM_DATA"] = runtime["data_directory"]
    command = [runtime["files"]["python"]["path"], config["files"]["entrypoint"]["path"], "run",
               "--output-dir", str(output), "--expected-protocol-sha256", protocol_hash, "--run-native",
               "--supervision-directory", str(evidence), "--expected-readiness-sha256", readiness_hash,
               "--start-token", token]
    return _monitor._run_owned(command, output, evidence,
        expected_executable=Path(runtime["files"]["worker"]["path"]),
        binding={"start_token": token, "protocol_sha256": protocol_hash, "readiness_sha256": readiness_hash},
        limits=_monitor.LIMITS, owner=owner)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("Prepare", "Run"), required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--expected-readiness-sha256")
    parser.add_argument("--owner-pid", type=int, required=True)
    parser.add_argument("--owner-created", type=int, required=True)
    args = parser.parse_args()
    owner = None
    try:
        if sys.platform != "win32":
            raise ValueError("Windows supervision required")
        owner = WindowsProcess(args.owner_pid)
        if owner.identity()["creation_time_100ns"] != args.owner_created:
            raise ValueError("PowerShell owner creation identity differs")
        _validate_owner(owner)
        if args.mode == "Prepare":
            result = prepare(args.output_directory, args.evidence_directory, args.expected_protocol_sha256)
        else:
            if args.expected_readiness_sha256 is None:
                raise ValueError("Run requires expected readiness hash")
            result = run(args.output_directory, args.evidence_directory, args.expected_protocol_sha256,
                         args.expected_readiness_sha256, owner=owner)
        print(_monitor._encoded(result).decode().rstrip())
        return 0 if args.mode == "Prepare" or result["status"] == "completed" else 1
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as error:
        parser.exit(1, f"Continuous motor supervision failed: {error}\n")
    finally:
        if owner is not None:
            owner.close()


if __name__ == "__main__":
    raise SystemExit(main())
