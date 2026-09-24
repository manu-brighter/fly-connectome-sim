import json
from dataclasses import replace
from typing import get_type_hints

import numpy as np
import pytest

import fly_connectome_sim.engine as engine_module
from fly_connectome_sim.engine import FlyEngine, NeuralGroups
from fly_connectome_sim.neural.checkpoint import model_fingerprint
from fly_connectome_sim.neural.visual import VisualMemoryBrain


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


def test_rgb_drive_samples_geometry_without_advancing_visual_state():
    class VisualFixture:
        rgb_drive = VisualMemoryBrain.rgb_drive

        def __init__(self):
            self.uv = np.array([[0.0, 0.0], [1.0, 1.0]], dtype=np.float32)
            self.r8_uv = np.array([[1.0, 0.0]], dtype=np.float32)
            self.r8_channel = np.array([1], dtype=np.int32)
            self.sim_ms = 2.0
            self.luminance = np.array([0.25, 0.75], dtype=np.float32)
            self.r8_light = np.array([0.5], dtype=np.float32)

    brain = VisualFixture()
    before = (brain.sim_ms, brain.luminance.tobytes(), brain.r8_light.tobytes())
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    frame[0, 1, 1] = 255
    wide = brain.rgb_drive(frame)
    tall = brain.rgb_drive(frame.reshape(1, 4, 3))

    np.testing.assert_array_equal(wide["r1_r6"], [0.0, 0.0])
    np.testing.assert_array_equal(wide["r8"], [1.0])
    np.testing.assert_array_equal(tall["r8"], [0.0])
    assert (brain.sim_ms, brain.luminance.tobytes(), brain.r8_light.tobytes()) == before


class DiagnosticBrain(DeterministicBrain):
    def __init__(self):
        super().__init__()
        self.n = 11
        self.ids = np.arange(100, 111, dtype=np.int64)
        self.post = np.array([0, 0, 8, 0, 0, 7, 0, 8], dtype=np.int32)
        self.circuit = {
            "edges": np.array([7, 5, 2], dtype=np.int64),
            "pre": np.array([5, 3, 4], dtype=np.int32),
            "dan": np.array([2, 1], dtype=np.int32),
        }
        self.rate_kc = np.zeros(3, dtype=np.float64)
        self.rate_dan = np.zeros(2, dtype=np.float64)
        self.memory_u = np.zeros(3, dtype=np.float64)
        self.memory_w = np.zeros(3, dtype=np.float64)
        self.baseline_plastic = np.array([2.0, 3.0, 4.0], dtype=np.float32)
        self.weight = np.ones(8, dtype=np.float32)
        self.rule_parameters = {"minimum_fraction": 0.1, "maximum_fraction": 2.0}
        self.phase = 0

    def rgb_drive(self, frame):
        return {
            "r1_r6": np.array([0.0, 1.0], dtype=np.float32),
            "r8": np.array([0.5], dtype=np.float32),
        }

    def rgb_step(self, frame, duration_ms, **kwargs):
        self.phase += 1
        self.sim_ms += duration_ms
        self.rate_kc[:] = [self.phase, 0.0, 2 * self.phase]
        self.rate_dan[:] = [3 * self.phase, 4 * self.phase]
        self.memory_u[:] = [
            -0.9 if self.phase == 1 else -0.2,
            0,
            1.0 if self.phase == 1 else 0.2,
        ]
        self.memory_w[:] = self.memory_u
        self.weight[self.circuit["edges"]] = self.baseline_plastic * (1 + self.memory_w)
        return np.arange(1, 12, dtype=np.int32), 0.001


DIAGNOSTIC_GROUPS = NeuralGroups(
    pam11=np.array([0]),
    ppl101=np.array([1, 2]),
    kc=np.array([3, 4, 5]),
    mbon07=np.array([7]),
    mbon11=np.array([8]),
    motor_left=np.array([9]),
    motor_right=np.array([10]),
)


def test_pathway_detail_excludes_mbon07_only_kc_and_keeps_default_compact():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    compact = FlyEngine(brain=DiagnosticBrain(), groups=DIAGNOSTIC_GROUPS).observe(
        frame, 20.0
    )
    detailed = FlyEngine(brain=DiagnosticBrain(), groups=DIAGNOSTIC_GROUPS).observe(
        frame, 20.0, pathway_detail=True
    )

    assert "pathway_detail" not in compact
    assert all("qualification_detail" not in bin for bin in compact["bins"])
    assert detailed["pathway_detail"]["candidate_edge_indices"] == [7, 2]
    assert detailed["pathway_detail"]["candidate_kc_indices"] == [4, 5]
    assert detailed["pathway_detail"]["candidate_kc_source_ids"] == ["104", "105"]
    assert detailed["pathway_detail"]["candidate_kc_spike_counts"] == [10, 12]
    assert detailed["pathway_detail"]["candidate_kc_spikes_by_source_id"] == {
        "104": 10,
        "105": 12,
    }
    assert detailed["pathway_detail"]["candidate_edge_pre_source_ids"] == [
        "105", "104",
    ]
    assert detailed["pathway_detail"]["candidate_edge_post_source_ids"] == [
        "108", "108",
    ]
    assert detailed["pathway_detail"]["modeled_visual_drive"]["r8"]["mean"] == 0.5
    assert detailed["total_spikes"] == compact["total_spikes"]
    assert detailed["spike_sha256"] == compact["spike_sha256"]
    json.dumps(detailed, allow_nan=False)


def test_qualification_detail_captures_transient_bound_hit_per_bin():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    result = FlyEngine(brain=DiagnosticBrain(), groups=DIAGNOSTIC_GROUPS).observe(
        frame, 20.0, qualification_detail=True
    )

    first, second = [bin["qualification_detail"] for bin in result["bins"]]
    assert first["rate_kc"] == [1.0, 2.0]
    assert first["rate_dan"] == [3.0, 4.0]
    assert first["lower_bound_hits"] == 1
    assert first["upper_bound_hits"] == 1
    assert second["lower_bound_hits"] == 0
    assert second["upper_bound_hits"] == 0
    assert result["qualification_detail"]["maximum_bound_hit_fraction"] == 1.0
    assert result["qualification_detail"]["dan_indices"] == [2, 1]
    assert result["qualification_detail"]["dan_source_ids"] == ["102", "101"]
    assert result["qualification_detail"]["rate_kc_semantics"] == "model_trace_state_hz"
    assert result["qualification_detail"]["rate_dan_semantics"] == "model_trace_state_hz"
    assert first["memory_u"]["minimum"] == -0.9
    assert first["memory_w"]["maximum"] == 1.0
    assert first["memory_u"]["sha256"] != second["memory_u"]["sha256"]
    assert first["efficacy"]["minimum"] == pytest.approx(0.1)
    json.dumps(result, allow_nan=False)


def test_bound_hit_fraction_counts_an_edge_at_opposite_bounds_once():
    class OppositeBoundsBrain(DiagnosticBrain):
        def rgb_step(self, frame, duration_ms, **kwargs):
            counts, elapsed = super().rgb_step(frame, duration_ms, **kwargs)
            if self.phase == 1:
                self.memory_w[0] = 1.0
                self.memory_u[2] = 0.2
                self.memory_w[2] = 0.2
                self.weight[self.circuit["edges"]] = self.baseline_plastic * (
                    1 + self.memory_w
                )
            return counts, elapsed

    result = FlyEngine(brain=OppositeBoundsBrain(), groups=DIAGNOSTIC_GROUPS).observe(
        np.zeros((2, 2, 3), dtype=np.uint8), 20.0, qualification_detail=True
    )
    first, second = [bin["qualification_detail"] for bin in result["bins"]]

    assert len(result["pathway_detail"]["candidate_edge_indices"]) == 2
    assert first["lower_bound_hits"] == 1
    assert first["upper_bound_hits"] == 1
    assert first["bound_hit_fraction"] == 0.5
    assert second["bound_hit_fraction"] == 0.0
    assert result["qualification_detail"]["maximum_bound_hit_fraction"] == 0.5
