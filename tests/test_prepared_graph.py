import json

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pyarrow.ipc as ipc

from fly_connectome_sim.data import verify_prepared_graph
from fly_connectome_sim.neural.common import DATA
import fly_connectome_sim.neural.prepare as prepare_module


def test_prepared_graph_matches_audited_malecns_array_locks():
    result = verify_prepared_graph(DATA)

    assert result == {
        "release": "MaleCNS v1.0",
        "neurons": 166_700,
        "directed_edges": 25_582_938,
        "arrays_verified": True,
    }


def test_prepare_describes_the_project_owned_dna02_readout_without_biological_claims(
    tmp_path, monkeypatch
):
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    ids = np.arange(100, 108, dtype=np.int64)
    feather.write_feather(
        pa.table(
            {
                "source_id": ids,
                "neurotransmitter": ["acetylcholine"] * len(ids),
                "cell_type": [""] * len(ids),
                "superclass": ["visual"] * len(ids),
            }
        ),
        normalized / "neurons.feather",
    )
    feather.write_feather(
        pa.table(
            {
                "bodyId": ids,
                "type": ["R1-R6"] * 4 + ["L1"] * 4,
                "assignedOlHex1": [None] * 4 + [0.0, 2.0, 0.0, 2.0],
                "assignedOlHex2": [None] * 4 + [0.0, 1.0, 0.0, 1.0],
                "rootSide": ["L", "L", "R", "R"] * 2,
                "somaSide": ["L", "L", "R", "R"] * 2,
            }
        ),
        tmp_path / "annotations.feather",
    )
    edges = pa.table(
        {
            "pre_index": np.arange(4, dtype=np.int32),
            "post_index": np.arange(4, 8, dtype=np.int32),
            "synapse_count": np.ones(4, dtype=np.int32),
        }
    )
    with pa.OSFile(str(normalized / "edges.arrow"), "wb") as sink:
        with ipc.new_file(sink, edges.schema) as writer:
            writer.write_table(edges)
    (normalized / "report.json").write_text(
        json.dumps({"source_hashes": {"fixture": "0" * 64}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(prepare_module, "DATA", tmp_path)

    manifest = prepare_module.prepare()

    description = manifest["motor_interface"]
    assert "DNa02" in description
    assert "engineered" in description
    assert "unvalidated" in description
    assert "not a biological decision circuit" in description
    assert all(stale not in description for stale in ["DNp20", "DNpe017", "buy", "sell"])
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))[
        "motor_interface"
    ] == description
