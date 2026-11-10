"""Finite owner-death fixture; its Job has kill-on-owner-close semantics."""
import json
import os
from pathlib import Path
import sys
import time

project = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project), str(project / "src")]
from market.native_windows import OwnedNativeChild

root = Path(sys.argv[1])
owner = OwnedNativeChild(dict(incarnation="10000000-0000-0000-0000-000000000001",
                             worker_session="20000000-0000-0000-0000-000000000002",
                             protocol_sha256="a" * 64, work_root=str(root),
                             decoder_work_root=str(root / "decoder"), project_root=str(project)))
owner._start_test(project / "tests/market/fixtures/native_harmless.py", "sleep")
(root / "identity.tmp").write_text(json.dumps(owner.identity.to_dict()), encoding="utf-8")
(root / "identity.tmp").rename(root / "owned-identity.json")
time.sleep(0.8)
os._exit(0)
