import json
from pathlib import Path

import pytest

from jogge_fly_brain.data import SourceIntegrityError, stage_sources, verify_sources


PROJECT_ROOT = Path(__file__).parents[1]


def test_official_malecns_sources_match_locked_manifest():
    verified = verify_sources(PROJECT_ROOT / "data" / "malecns-v1.0")

    assert [source.logical_name for source in verified] == [
        "annotations.feather",
        "neurotransmitters.feather",
        "edges.feather",
    ]
    assert sum(source.bytes for source in verified) == 1_109_008_094


def test_source_verification_rejects_modified_content(tmp_path):
    (tmp_path / "sample.feather").write_bytes(b"modified")
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": "sample.feather",
                        "logicalName": "annotations.feather",
                        "bytes": 8,
                        "sha256": "0" * 64,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SourceIntegrityError, match="SHA-256 mismatch"):
        verify_sources(tmp_path)


def test_stage_sources_exposes_locked_files_under_neural_core_names(tmp_path):
    source_directory = tmp_path / "source"
    runtime_directory = tmp_path / "runtime"
    source_directory.mkdir()
    payload = b"ARROW1-test-ARROW1"
    source = source_directory / "released-name.feather"
    source.write_bytes(payload)
    import hashlib

    (source_directory / "manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": source.name,
                        "logicalName": "annotations.feather",
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    staged = stage_sources(source_directory, runtime_directory)

    assert staged == (runtime_directory / "annotations.feather",)
    assert staged[0].read_bytes() == payload
    assert staged[0].stat().st_ino == source.stat().st_ino
