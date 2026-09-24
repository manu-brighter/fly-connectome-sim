from hashlib import sha256
import os

import numpy as np
import pytest

from fly_connectome_sim.engine import FlyEngine


pytestmark = pytest.mark.skipif(
    os.getenv("FLY_CONNECTOME_SIM_FULL_TEST") != "1",
    reason="full MaleCNS integration test is opt-in",
)


def brain_state(brain):
    return {
        "cursor": brain.cursor,
        "sim_ms": brain.sim_ms,
        "total_spikes": brain.total_spikes,
        "weights_frozen": brain.weights_frozen,
        "arrays": {
            name: sha256(getattr(brain, name).tobytes()).hexdigest()
            for name in ["weight", *brain.fields]
        },
    }


def test_full_graph_replays_identically_after_checkpoint_restore(tmp_path):
    engine = FlyEngine.from_prepared_graph()
    brain = engine.brain

    assert brain.n == 166_700
    assert len(brain.post) == 25_582_938
    assert len(engine.groups.pam11) == 15
    assert len(engine.groups.ppl101) == 2
    assert len(engine.groups.mbon07) == 4
    assert len(engine.groups.mbon11) == 2

    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    frame[:, :16] = (12, 80, 220)
    frame[:, 16:] = (235, 40, 24)
    initial_memory = brain.memory()
    prelude = engine.observe(
        frame,
        100.0,
        stimulation="pam11",
        current_mv=20.0,
        learning=True,
    )

    assert brain.cursor == 1000
    assert brain.sim_ms == 100.0
    assert prelude["total_spikes"] > 0
    assert prelude["rates_hz"]["pam11"] > 0
    assert prelude["memory"]["changed_edges"] > 0
    assert prelude["memory"]["sha256"] != initial_memory["sha256"]
    assert np.any(brain.rate_kc != 0)
    assert np.any(brain.rate_dan != 0)
    assert np.any(brain.memory_u != 0)
    assert np.any(brain.memory_w != 0)
    assert np.any(brain.luminance != 0)
    assert np.any(brain.r8_light != 0)
    assert np.any(brain.queue_count != 0)

    checkpoint_state = brain_state(brain)
    checkpoint = tmp_path / "evolved-brain.npz"
    brain.checkpoint(checkpoint)

    continuation_frame = np.ascontiguousarray(frame[:, ::-1])
    first = engine.observe(continuation_frame, 25.3)
    first_state = brain_state(brain)
    assert first["sim_ms"] == 125.3
    assert first["total_spikes"] > 0
    assert first_state != checkpoint_state

    brain.restore(checkpoint)
    assert brain_state(brain) == checkpoint_state
    assert brain.memory() == prelude["memory"]

    second = engine.observe(continuation_frame, 25.3)
    assert brain_state(brain) == first_state

    # Include motor/MBON rates, turn evidence, bin timing and memory telemetry;
    # only the elapsed wall-clock measurements are nondeterministic.
    wall_clock_fields = {"compute_seconds", "kernel_seconds"}
    assert {
        key: value for key, value in first.items() if key not in wall_clock_fields
    } == {
        key: value for key, value in second.items() if key not in wall_clock_fields
    }
