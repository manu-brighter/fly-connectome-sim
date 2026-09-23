import json
from dataclasses import replace
from typing import get_type_hints

import numpy as np
import pytest

import jogge_fly_brain.engine as engine_module
from jogge_fly_brain.engine import FlyEngine, NeuralGroups
from jogge_fly_brain.neural.checkpoint import model_fingerprint


class DeterministicBrain:
    def __init__(self):
        self.n = 9
        self.dt = 0.1
        self.sim_ms = 0.0
        self.calls = []
        self.provenance_calls = 0
        self.configuration_calls = 0
        self.eta = 0.001
        self._locked_eta = None

    def rgb_step(self, frame, duration_ms, **kwargs):
        self.calls.append((frame.copy(), duration_ms, kwargs))
        self.sim_ms += duration_ms
        return np.arange(1, 10, dtype=np.int32), 0.001

    def memory(self):
        return {"changed_edges": 3, "mean_efficacy": 0.9}

    def configuration_signature(self):
        self.configuration_calls += 1
        return {"model": "deterministic-test-brain/v1", "dt_ms": self.dt}

    def model_provenance(self):
        self.provenance_calls += 1
        return {
            "model": "deterministic-test-brain/v1",
            "model_fingerprint": model_fingerprint(),
            "build": {
                "model": "deterministic-test-brain/v1",
                "source_sha256": "1" * 64,
                "compiler": "test-compiler 1.0",
                "flags": ["-O3"],
                "library": "memory.dll",
                "binary_sha256": "2" * 64,
            },
            "eta": self.eta,
            "parameters": {"neural_dt_ms": self.dt},
            "graph_ids_sha256": "3" * 64,
            "graph_ptr_sha256": "4" * 64,
            "graph_post_sha256": "5" * 64,
            "plastic_edges_sha256": "6" * 64,
            "configuration_sha256": self.configuration_signature(),
        }

    def lock_model_provenance(self):
        provenance = self.model_provenance()
        self._locked_eta = self.eta
        return provenance

    def assert_model_provenance_locked(self):
        if self.eta != self._locked_eta:
            raise RuntimeError("Model provenance changed after engine identity")


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


def test_observe_uses_an_explicit_structural_telemetry_type():
    assert get_type_hints(FlyEngine.observe)["return"] is engine_module.FlyTelemetry


def test_native_build_identity_types_the_production_model_field():
    assert get_type_hints(engine_module.NativeBuildIdentity)["model"] is str


def test_input_hash_distinguishes_valid_rgb_geometries_with_identical_bytes():
    pixels = np.arange(24, dtype=np.uint8)
    wide = pixels.reshape(2, 4, 3)
    tall = pixels.reshape(4, 2, 3)

    wide_result = FlyEngine(brain=DeterministicBrain(), groups=GROUPS).observe(
        wide, 0.1
    )
    tall_result = FlyEngine(brain=DeterministicBrain(), groups=GROUPS).observe(
        tall, 0.1
    )

    assert wide.tobytes(order="C") == tall.tobytes(order="C")
    assert wide_result["input_sha256"] != tall_result["input_sha256"]
    assert wide_result["input_shape"] == [2, 4, 3]
    assert tall_result["input_shape"] == [4, 2, 3]
    assert wide_result["input_dtype"] == tall_result["input_dtype"] == "uint8"


def test_input_hash_normalizes_equivalent_noncontiguous_rgb_views():
    source = np.arange(48, dtype=np.uint8).reshape(4, 4, 3)
    view = source[::2]
    contiguous = np.ascontiguousarray(view)

    view_result = FlyEngine(brain=DeterministicBrain(), groups=GROUPS).observe(
        view, 0.1
    )
    contiguous_result = FlyEngine(
        brain=DeterministicBrain(), groups=GROUPS
    ).observe(contiguous, 0.1)

    assert not view.flags.c_contiguous
    assert np.array_equal(view, contiguous)
    assert view_result["input_sha256"] == contiguous_result["input_sha256"]


def test_engine_identity_includes_core_configuration_and_exact_groups():
    baseline_brain = DeterministicBrain()
    baseline = FlyEngine(brain=baseline_brain, groups=GROUPS).identity()
    changed_motor = FlyEngine(
        brain=DeterministicBrain(),
        groups=replace(GROUPS, motor_right=np.array([1, 8], dtype=np.int32)),
    ).identity()
    changed_mbon = FlyEngine(
        brain=DeterministicBrain(),
        groups=replace(GROUPS, mbon07=np.array([0, 5], dtype=np.int32)),
    ).identity()

    assert baseline["model_provenance"] == baseline_brain.model_provenance()
    assert baseline["model_provenance"]["model_fingerprint"] == model_fingerprint()
    assert baseline["model_provenance"]["configuration_sha256"] == {
        "model": "deterministic-test-brain/v1",
        "dt_ms": 0.1,
    }
    assert baseline["neural_groups"] == {
        "pam11": [0, 1],
        "ppl101": [2],
        "kc": [3, 4],
        "mbon07": [5],
        "mbon11": [6],
        "motor_left": [7],
        "motor_right": [8],
    }
    assert changed_motor["neural_groups"]["motor_right"] == [1, 8]
    assert changed_mbon["neural_groups"]["mbon07"] == [0, 5]
    assert baseline["sha256"] != changed_motor["sha256"]
    assert baseline["sha256"] != changed_mbon["sha256"]


def test_engine_identity_excludes_mutable_neural_state():
    brain = DeterministicBrain()
    engine = FlyEngine(brain=brain, groups=GROUPS)
    before = engine.identity()

    engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 20.0)

    assert brain.sim_ms == 20.0
    assert engine.identity() == before


def test_engine_copies_and_freezes_caller_owned_neural_groups():
    caller_groups = NeuralGroups(
        **{name: indices.copy() for name, indices in vars(GROUPS).items()}
    )
    engine = FlyEngine(brain=DeterministicBrain(), groups=caller_groups)
    before = engine.identity()

    caller_groups.motor_right[0] = 0
    result = engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 0.1)

    assert engine.identity() == before
    assert engine.groups.motor_right.tolist() == [8]
    assert not engine.groups.motor_right.flags.writeable
    assert result["rates_hz"]["motor_right"] == 90_000.0


def test_engine_groups_cannot_be_reassigned_after_identity_snapshot():
    engine = FlyEngine(brain=DeterministicBrain(), groups=GROUPS)
    canonical = engine.identity()
    replacement = replace(GROUPS, motor_right=np.array([0], dtype=np.int32))

    with pytest.raises(AttributeError, match="groups"):
        engine.groups = replacement

    result = engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 0.1)
    assert engine.groups.motor_right.tolist() == [8]
    assert result["engine_identity"] == canonical
    assert result["rates_hz"]["motor_right"] == 90_000.0


def test_same_engine_rejects_eta_change_before_neural_state_mutates():
    brain = DeterministicBrain()
    engine = FlyEngine(brain=brain, groups=GROUPS)
    engine.identity()
    brain.eta += 0.001

    with pytest.raises(RuntimeError, match="provenance"):
        engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 0.1)

    assert brain.calls == []
    assert brain.sim_ms == 0.0


def test_engine_identity_calculates_provenance_once_per_engine():
    brain = DeterministicBrain()
    engine = FlyEngine(brain=brain, groups=GROUPS)

    engine.identity()
    engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 0.1)
    engine.identity()
    engine.observe(np.ones((2, 2, 3), dtype=np.uint8), 0.1)

    assert brain.provenance_calls == 1
    assert brain.configuration_calls == 1


def test_returned_identity_cannot_mutate_the_cached_engine_identity():
    engine = FlyEngine(brain=DeterministicBrain(), groups=GROUPS)
    canonical = engine.identity()
    returned = engine.identity()
    returned["model_provenance"]["build"]["binary_sha256"] = "0" * 64
    telemetry = engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 0.1)
    telemetry["engine_identity"]["neural_groups"]["motor_right"].append(0)

    assert engine.identity() == canonical
    assert engine.observe(np.zeros((2, 2, 3), dtype=np.uint8), 0.1)[
        "engine_identity"
    ] == canonical


def test_observe_telemetry_is_strict_json_and_carries_engine_identity():
    engine = FlyEngine(brain=DeterministicBrain(), groups=GROUPS)

    result = engine.observe(
        np.zeros((2, 3, 3), dtype=np.uint8),
        0.1,
        stimulation="ppl101",
        current_mv=7.5,
    )

    encoded = json.dumps(result, sort_keys=True, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded["input_shape"] == [2, 3, 3]
    assert decoded["input_dtype"] == "uint8"
    assert decoded["engine_identity"] == engine.identity()
