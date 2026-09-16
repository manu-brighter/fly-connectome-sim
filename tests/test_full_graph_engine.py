import os

import numpy as np
import pytest

from jogge_fly_brain.engine import FlyEngine


pytestmark = pytest.mark.skipif(
    os.getenv("JOGGE_FLY_FULL_TEST") != "1",
    reason="full MaleCNS integration test is opt-in",
)


def test_full_graph_replays_identically_after_reset():
    engine = FlyEngine.from_prepared_graph()
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    frame[:, :16] = (12, 80, 220)
    frame[:, 16:] = (235, 40, 24)

    first = engine.observe(frame, 20.0)
    engine.brain.reset()
    second = engine.observe(frame, 20.0)

    assert engine.brain.n == 166_700
    assert len(engine.groups.pam11) == 15
    assert len(engine.groups.ppl101) == 2
    assert len(engine.groups.mbon07) == 4
    assert len(engine.groups.mbon11) == 2
    assert first["input_sha256"] == second["input_sha256"]
    assert first["spike_sha256"] == second["spike_sha256"]
    assert first["total_spikes"] == second["total_spikes"]
    assert first["rates_hz"] == second["rates_hz"]
    assert first["memory"]["sha256"] == second["memory"]["sha256"]
