"""Real tiny native visual engines shared by retention-route acceptance tests."""

import numpy as np
import pytest

from fly_connectome_sim.engine import FlyEngine, NeuralGroups
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
