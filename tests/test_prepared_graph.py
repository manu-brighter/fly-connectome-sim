from pathlib import Path

from jogge_fly_brain.data import verify_prepared_graph


PROJECT_ROOT = Path(__file__).parents[1]


def test_prepared_graph_matches_audited_malecns_array_locks():
    result = verify_prepared_graph(
        PROJECT_ROOT / "data" / "malecns-v1.0" / "runtime"
    )

    assert result == {
        "release": "MaleCNS v1.0",
        "neurons": 166_700,
        "directed_edges": 25_582_938,
        "arrays_verified": True,
    }
