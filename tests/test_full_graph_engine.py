from hashlib import sha256
import json
import os

import numpy as np
import pytest

from fly_connectome_sim.engine import FlyEngine
from fly_connectome_sim.neural.checkpoint import checkpoint_state_sha256, load_checkpoint


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


def test_full_graph_candidate_digests_are_read_only():
    engine = FlyEngine.from_prepared_graph()
    engine.identity()
    brain = engine.brain
    before = brain.checkpoint_state_sha256()
    scalars = (brain.cursor, brain.sim_ms, brain.total_spikes, brain.weights_frozen)
    references = {name: getattr(brain, name) for name in ["weight", *brain.fields]}
    first = brain.candidate_state_digests(engine.groups.mbon11)
    assert brain.candidate_state_digests(engine.groups.mbon11) == first
    assert set(first) == {"candidate_memory_sha256", "noncandidate_state_sha256"}
    assert all(len(value) == 64 and set(value) <= set("0123456789abcdef")
               for value in first.values())
    assert brain.checkpoint_state_sha256() == before
    assert (brain.cursor, brain.sim_ms, brain.total_spikes, brain.weights_frozen) == scalars
    assert all(getattr(brain, name) is value for name, value in references.items())


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
    checkpoint_digest = brain.checkpoint_state_sha256()
    checkpoint = tmp_path / "evolved-brain.npz"
    brain.checkpoint(checkpoint)
    metadata, arrays = load_checkpoint(
        checkpoint,
        brain.model_provenance(),
        {name: getattr(brain, name) for name in ["weight", *brain.fields]},
        brain.n,
    )
    assert checkpoint_state_sha256(metadata, arrays) == checkpoint_digest
    del arrays

    continuation_frame = np.ascontiguousarray(frame[:, ::-1])
    first = engine.observe(continuation_frame, 25.3)
    first_state = brain_state(brain)
    first_digest = brain.checkpoint_state_sha256()
    assert first["sim_ms"] == 125.3
    assert first["total_spikes"] > 0
    assert first_state != checkpoint_state
    assert first_digest != checkpoint_digest

    brain.restore(checkpoint)
    assert brain_state(brain) == checkpoint_state
    assert brain.checkpoint_state_sha256() == checkpoint_digest
    assert brain.memory() == prelude["memory"]

    second = engine.observe(continuation_frame, 25.3)
    assert brain_state(brain) == first_state
    assert brain.checkpoint_state_sha256() == first_digest

    # Include motor/MBON rates, turn evidence, bin timing and memory telemetry;
    # only the elapsed wall-clock measurements are nondeterministic.
    wall_clock_fields = {"compute_seconds", "kernel_seconds"}
    assert {
        key: value for key, value in first.items() if key not in wall_clock_fields
    } == {
        key: value for key, value in second.items() if key not in wall_clock_fields
    }

    brain.restore(checkpoint)
    before_drive = brain_state(brain)
    drive = brain.rgb_drive(continuation_frame)
    assert len(drive["r1_r6"]) == len(brain.retina)
    assert len(drive["r8"]) == len(brain.r8)
    assert brain_state(brain) == before_drive

    detailed = engine.observe(continuation_frame, 25.3, qualification_detail=True)
    assert brain_state(brain) == first_state
    pathway = detailed.pop("pathway_detail")
    qualification = detailed.pop("qualification_detail")
    assert pathway["candidate_edge_indices"] == brain.circuit["edges"][
        np.isin(brain.post[brain.circuit["edges"]], engine.groups.mbon11)
    ].tolist()
    assert len(pathway["candidate_kc_spikes_by_source_id"]) == len(
        pathway["candidate_kc_indices"]
    )
    assert qualification["dan_indices"] == brain.circuit["dan"].tolist()
    assert 0 <= qualification["maximum_bound_hit_fraction"] <= 1
    for bin in detailed["bins"]:
        details = bin.pop("qualification_detail")
        assert len(details["rate_kc"]) == len(pathway["candidate_edge_indices"])
        assert len(details["rate_dan"]) == len(brain.circuit["dan"])
        assert details["memory_u"]["count"] == len(pathway["candidate_edge_indices"])
        json.dumps(details, allow_nan=False)
    assert {
        key: value for key, value in first.items() if key not in wall_clock_fields
    } == {
        key: value for key, value in detailed.items() if key not in wall_clock_fields
    }
