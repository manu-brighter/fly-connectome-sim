import numpy as np
import pytest

from jogge_fly_brain.engine import FlyEngine, NeuralGroups


class DeterministicBrain:
    def __init__(self):
        self.n = 9
        self.dt = 0.1
        self.sim_ms = 0.0
        self.calls = []

    def rgb_step(self, frame, duration_ms, **kwargs):
        self.calls.append((frame.copy(), duration_ms, kwargs))
        self.sim_ms += duration_ms
        return np.arange(1, 10, dtype=np.int32), 0.001

    def memory(self):
        return {"changed_edges": 3, "mean_efficacy": 0.9}


GROUPS = NeuralGroups(
    pam11=np.array([0, 1]),
    ppl101=np.array([2]),
    kc=np.array([3, 4]),
    mbon07=np.array([5]),
    mbon11=np.array([6]),
    motor_left=np.array([7]),
    motor_right=np.array([8]),
)


def test_observe_returns_declared_neural_rates_and_explicit_stimulation():
    brain = DeterministicBrain()
    engine = FlyEngine(brain=brain, groups=GROUPS)
    frame = np.zeros((4, 4, 3), dtype=np.uint8)

    result = engine.observe(
        frame,
        20.0,
        stimulation="pam11",
        current_mv=12.5,
        learning=True,
    )

    assert result["sim_ms"] == 20.0
    assert result["total_spikes"] == 90
    assert result["rates_hz"] == {
        "pam11": 150.0,
        "ppl101": 300.0,
        "kc": 450.0,
        "mbon07": 600.0,
        "mbon11": 700.0,
        "motor_left": 800.0,
        "motor_right": 900.0,
    }
    assert result["turn_hz"] == 100.0
    assert result["stimulation"] == {
        "population": "pam11",
        "current_mv": 12.5,
        "duration_ms": 20.0,
    }
    assert result["learning"] is True
    assert result["memory"] == {"changed_edges": 3, "mean_efficacy": 0.9}
    assert len(result["bins"]) == 2
    assert all(call[2]["learning"] is True for call in brain.calls)
    assert all(np.array_equal(call[2]["stimulation"][0], GROUPS.pam11) for call in brain.calls)
    assert all(call[2]["stimulation"][1] == 12.5 for call in brain.calls)


@pytest.mark.parametrize(
    ("frame", "duration_ms", "message"),
    [
        (np.zeros((4, 4), dtype=np.uint8), 10.0, "RGB uint8"),
        (np.zeros((4, 4, 3), dtype=np.float32), 10.0, "RGB uint8"),
        (np.zeros((4, 4, 3), dtype=np.uint8), 0.0, "Duration"),
        (np.zeros((4, 4, 3), dtype=np.uint8), 10.05, "0.1 ms"),
    ],
)
def test_observe_rejects_inputs_that_break_the_kernel_contract(
    frame, duration_ms, message
):
    engine = FlyEngine(brain=DeterministicBrain(), groups=GROUPS)

    with pytest.raises(ValueError, match=message):
        engine.observe(frame, duration_ms)


def test_observe_rejects_unknown_stimulation_population():
    engine = FlyEngine(brain=DeterministicBrain(), groups=GROUPS)

    with pytest.raises(ValueError, match="Unknown stimulation population"):
        engine.observe(
            np.zeros((4, 4, 3), dtype=np.uint8),
            10.0,
            stimulation="dopamine",
        )
