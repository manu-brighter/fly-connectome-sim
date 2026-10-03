"""Real tiny native visual engines shared by retention-route acceptance tests."""

from hashlib import sha256
import json

import numpy as np
import pytest

from fly_connectome_sim.engine import FlyEngine, NeuralGroups, _rgb_input_sha256
from fly_connectome_sim.experiment.analysis import FrozenAssayConfig
from fly_connectome_sim.experiment.stimuli import AssayStimuli
from fly_connectome_sim.neural.brain import MemoryBrain
from fly_connectome_sim.neural.visual import VisualMemoryBrain


class TinyVisualBrain(VisualMemoryBrain):
    def __init__(self, graph):
        MemoryBrain.__init__(
            self, path=graph,
            circuit={"kc": np.array([0], dtype=np.int32),
                     "dan": np.array([1], dtype=np.int32),
                     "edges": np.array([0], dtype=np.int64),
                     "pre": np.array([0], dtype=np.int32),
                     "gain": np.array([[1.0]], dtype=np.float32),
                     "kc_mask": np.array([1, 0, 0, 0], dtype=np.uint8),
                     "dan_index": np.array([-1, 0, -1, -1], dtype=np.int8)},
            modulation_mask=np.array([0, 1, 0, 0], dtype=np.uint8),
        )
        self.r8 = np.array([0], dtype=np.int32)
        self.r8_uv = np.array([[0.5, 0.5]], dtype=np.float32)
        self.r8_channel = np.array([2], dtype=np.int32)
        self.corrected_edges = np.array([], dtype=np.int64)
        self.r8_light = np.zeros(1, dtype=np.float32)
        self.fields.append("r8_light")
        self.initial["r8_light"] = self.r8_light.copy()


@pytest.fixture
def engine_factory(tmp_path):
    graph = tmp_path / "graph.npz"
    np.savez(graph, ids=np.array([10, 20, 30, 40], dtype=np.int64),
             ptr=np.array([0, 1, 2, 2, 2], dtype=np.int64),
             post=np.array([2, 2], dtype=np.int32),
             weight=np.array([0.275, 0.275], dtype=np.float32),
             retina=np.array([0], dtype=np.int32),
             uv=np.array([[0.5, 0.5]], dtype=np.float32),
             lamina=np.array([], dtype=np.int32), sugar=np.array([], dtype=np.int32),
             superclass=np.zeros(4, dtype=np.uint8))

    def factory():
        groups = NeuralGroups(**{name: np.array([index], dtype=np.int32)
                                 for name, index in [("pam11", 1), ("ppl101", 1),
                                                     ("kc", 0), ("mbon07", 2),
                                                     ("mbon11", 2), ("motor_left", 3),
                                                     ("motor_right", 3)]})
        return FlyEngine(brain=TinyVisualBrain(graph), groups=groups)

    return factory


def _declared_inputs(family):
    seeds = (11, 23) if family == "qualification" else (101, 113)
    return {str(seed): {name: _rgb_input_sha256((np.zeros((32, 32, 3), dtype=np.uint8) if name == "black" else AssayStimuli(seed, family).frame(name)))
                        for name in ("A", "B", "C", "black")} for seed in seeds}


def _declared_native_frozen_config(producer):
    """Declared tiny route-test contract, not evidence of executed qualification."""
    population = len(producer.groups.mbon11)
    # An explicit valid frozen contract, without a manufactured qualification run.
    data = {
        "version": "mbon11-frozen-assay/v1", "analysis_version": "mbon11-causal-analysis/v1",
        "qualification_version": "mbon11-qualification/v1", "aggregation": "raw-bin-mean-rate/v1",
        "qualification_artifact": {name: sha256(b"schema").hexdigest() for name in (
            "schema_sha256", "run_metadata_sha256", "events_sha256", "final_scientific_sha256")},
        "qualification_family": "qualification", "qualification_seeds": [11, 23],
        "qualification_protocol_version": "qualification/v1",
        "confirmation_family": "confirmation", "confirmation_seeds": [101, 113],
        "confirmation_protocol_version": "associative-confirmation/v1",
        "stimulus_version": "associative-stimuli/v1", "engine_identity": producer.identity(),
        "qualification_input_sha256": sorted({digest for row in _declared_inputs("qualification").values()
                                               for digest in row.values()}),
        "confirmation_input_sha256": _declared_inputs("confirmation"),
        "candidate_identity": "kc-mbon11-ppl101/v1", "mbon11_population_size": population,
        "selected_configuration": {"cs_duration_ms": 100.0, "dan_onset_ms": 0.0, "post_pair_gap_ms": 500.0}, "response_window": {"start_ms": 0.0, "end_ms": 100.0},
        "retention_ms": 10000, "retention_times_ms": [10000, 70000], "expected_effect_sign": 1,
        "conditions": ["paired", "frozen_plasticity", "no_external_dan", "temporally_unpaired", "matched_reference", "necessity", "sufficiency", "sham"], "interventions": ["necessity", "sufficiency", "sham"], "exclusions": [],
        "replay_resolution_hz": 0.0, "max_abs_control_delta_hz": 0.0,
        "dynamic_range_hz": 0.0, "effect_floor_hz": 0.0,
        "one_spike_floor_hz": 1000 / (population * 100),
        "floor_sources": {"replay_resolution_hz": "selected_paired_T_and_T_plus_60",
                          "max_abs_control_delta_hz": "selected_nonpaired_controls_T_and_T_plus_60",
                          "dynamic_range_hz": "selected_paired_pre_A_minus_pre_B",
                          "one_spike_floor_hz": "selected_response_window_and_population"},
    }
    data["digest"] = sha256(json.dumps(data, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()).hexdigest()
    return FrozenAssayConfig.from_dict(data)
