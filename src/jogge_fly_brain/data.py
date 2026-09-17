"""Checksum-locked access to the released MaleCNS source tables."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path


class SourceIntegrityError(RuntimeError):
    """Raised when a local connectome input differs from its locked source."""


@dataclass(frozen=True)
class VerifiedSource:
    logical_name: str
    path: Path
    bytes: int
    sha256: str


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sources(data_directory: Path | str) -> tuple[VerifiedSource, ...]:
    """Verify every source declared in the data directory's manifest."""

    directory = Path(data_directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    verified: list[VerifiedSource] = []

    for record in manifest["files"]:
        path = directory / record["name"]
        if not path.is_file():
            raise SourceIntegrityError(f"Missing source file: {record['name']}")
        actual_bytes = path.stat().st_size
        if actual_bytes != record["bytes"]:
            raise SourceIntegrityError(f"Size mismatch: {record['name']}")
        actual_hash = _sha256(path)
        if actual_hash != record["sha256"]:
            raise SourceIntegrityError(f"SHA-256 mismatch: {record['name']}")
        verified.append(
            VerifiedSource(
                logical_name=record["logicalName"],
                path=path,
                bytes=actual_bytes,
                sha256=actual_hash,
            )
        )

    return tuple(verified)


def stage_sources(
    source_directory: Path | str,
    runtime_directory: Path | str,
) -> tuple[Path, ...]:
    """Expose verified sources under the numerical core's stable logical names.

    Hard links avoid duplicating the 1.1 GB connection table. Both directories
    must therefore be on the same filesystem.
    """

    verified = verify_sources(source_directory)
    runtime = Path(runtime_directory).resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []

    for source in verified:
        target = runtime / source.logical_name
        if target.exists():
            if target.stat().st_size != source.bytes or _sha256(target) != source.sha256:
                raise SourceIntegrityError(
                    f"Staged source differs from manifest: {source.logical_name}"
                )
        else:
            try:
                os.link(source.path, target)
            except OSError as error:
                raise SourceIntegrityError(
                    "Cannot create a hard link for MaleCNS data; keep source and "
                    "runtime directories on the same filesystem"
                ) from error
        staged.append(target)

    return tuple(staged)


def verify_runtime_sources(
    runtime_directory: Path | str,
    *,
    source_urls: dict[str, str] | None = None,
) -> dict[str, dict[str, object]]:
    """Bind staged inputs to the packaged authoritative MaleCNS source lock."""

    runtime = Path(runtime_directory).resolve()
    lock = Path(__file__).with_name("neural") / "sources.lock.json"
    expected = json.loads(lock.read_text(encoding="utf-8"))
    if source_urls is not None and set(source_urls) != set(expected):
        raise SourceIntegrityError("Configured source files differ from source lock")
    verified = {}
    for name, record in expected.items():
        url = record["url"] if source_urls is None else source_urls[name]
        if url != record["url"]:
            raise SourceIntegrityError(f"Source URL mismatch: {name}")
        path = runtime / name
        if not path.is_file():
            raise SourceIntegrityError(f"Missing source file: {name}")
        actual_bytes = path.stat().st_size
        if actual_bytes != record["bytes"]:
            raise SourceIntegrityError(f"Size mismatch: {name}")
        actual_hash = _sha256(path)
        if actual_hash != record["sha256"]:
            raise SourceIntegrityError(f"SHA-256 mismatch: {name}")
        verified[name] = {
            "url": url,
            "bytes": actual_bytes,
            "sha256": actual_hash,
        }
    return verified


def verify_prepared_graph(runtime_directory: Path | str) -> dict[str, object]:
    """Verify the prepared graph against the audited MaleCNS array locks."""

    import numpy as np
    import pyarrow.feather as feather

    runtime = Path(runtime_directory).resolve()
    verify_runtime_sources(runtime)
    package = Path(__file__).with_name("neural")
    graph_path = runtime / "graph.npz"
    expected = json.loads(
        (package / "arrays.lock.json").read_text(encoding="utf-8")
    )

    with np.load(graph_path, allow_pickle=False) as graph:
        if set(graph.files) != set(expected):
            raise SourceIntegrityError("Prepared graph fields mismatch")
        for name, expected_hash in expected.items():
            actual_hash = sha256(graph[name].tobytes()).hexdigest()
            if actual_hash != expected_hash:
                raise SourceIntegrityError(f"Prepared graph array mismatch: {name}")
        if len(graph["ids"]) != 166_700 or len(graph["post"]) != 25_582_938:
            raise SourceIntegrityError("Prepared graph has unexpected dimensions")
        ids = graph["ids"].copy()

    neurons_path = runtime / "normalized" / "neurons.feather"
    if not neurons_path.is_file():
        raise SourceIntegrityError("Normalized neuron metadata missing")
    neurons = feather.read_table(neurons_path).to_pandas()
    values = json.dumps(
        neurons.neurotransmitter.fillna("").astype(str).tolist(),
        separators=(",", ":"),
    ).encode()
    neuron_lock = json.loads(
        (package / "neurons.lock.json").read_text(encoding="utf-8")
    )
    if sha256(values).hexdigest() != neuron_lock["neurotransmitter_values_sha256"]:
        raise SourceIntegrityError("Normalized transmitter values mismatch")
    if not np.array_equal(neurons.source_id.to_numpy(), ids):
        raise SourceIntegrityError("Normalized neuron order mismatch")

    return {
        "release": "MaleCNS v1.0",
        "neurons": 166_700,
        "directed_edges": 25_582_938,
        "arrays_verified": True,
    }


def main() -> None:
    """Verify and stage local data without an ad-hoc Python invocation."""

    from .neural.common import DATA

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify-sources")
    verify.add_argument("source_directory", type=Path)
    stage = commands.add_parser("stage")
    stage.add_argument("source_directory", type=Path)
    stage.add_argument("--runtime-directory", type=Path, default=DATA)
    prepared = commands.add_parser("verify-prepared")
    prepared.add_argument("--runtime-directory", type=Path, default=DATA)
    args = parser.parse_args()

    try:
        if args.command == "verify-sources":
            sources = verify_sources(args.source_directory)
            result = {"files": len(sources), "bytes": sum(s.bytes for s in sources)}
        elif args.command == "stage":
            staged = stage_sources(args.source_directory, args.runtime_directory)
            result = {"staged": [str(path) for path in staged]}
        else:
            result = verify_prepared_graph(args.runtime_directory)
    except (SourceIntegrityError, FileNotFoundError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
