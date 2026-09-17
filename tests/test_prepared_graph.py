from jogge_fly_brain.data import verify_prepared_graph
from jogge_fly_brain.neural.common import DATA


def test_prepared_graph_matches_audited_malecns_array_locks():
    result = verify_prepared_graph(DATA)

    assert result == {
        "release": "MaleCNS v1.0",
        "neurons": 166_700,
        "directed_edges": 25_582_938,
        "arrays_verified": True,
    }
