"""Full-graph candidate memory dynamics with explicit stimulation and checkpoints."""

import ctypes as C
import hashlib
import json
import math
import numbers
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .circuit import identify
from .checkpoint import load_checkpoint, model_fingerprint
from .common import DATA, GRAPH, OUT, digest, save_json
from .native import build_native, library_path
from .state import NativeBrain

SOURCE = Path(__file__).with_name("kernel.cpp")
LIBRARY = library_path(OUT / "physiology-v6")
MODEL = "stonkfly-dual-compartment-v1"
from .rule import PARAMETERS as RULE_PARAMETERS

PARAMETERS = {
    **RULE_PARAMETERS,
    "neural_dt_ms": 0.1,
    "modulator_delivery_trace_ms": 100.0,
    "kc_rest_mV": -60.0,
    "kc_adaptation_jump_mV": 8.0,
    "kc_adaptation_tau_ms": 200.0,
    "interpretation": "Candidate KC adaptation/rest plus a baseline-centered anti-Hebbian rate-rule extension to two compartments. No fitted DAN/MBON background current; lamina bias is a display proxy. Gain, trace constants and transfer to this graph remain unvalidated assumptions.",
}


def build():
    return {"model": MODEL, **build_native(SOURCE, LIBRARY.parent)}


@dataclass(frozen=True)
class CandidateMemory:
    """One candidate edge group's model state at a neural clock."""

    target_indices: np.ndarray
    edge_indices: np.ndarray
    memory_u: np.ndarray
    memory_w: np.ndarray
    weight: np.ndarray
    cursor: int
    sim_ms: float


class MemoryBrain(NativeBrain):
    def __init__(
        self,
        path=GRAPH,
        *,
        eta=0.001,
        circuit=None,
        modulation_mask=None,
        tonic=None,
        dan_baseline_hz=None,
        kc_rest=-60.0,
        adaptation_jump=8.0,
        adaptation_tau=200.0,
    ):
        super().__init__(path)
        self.build = build()
        self.library = C.CDLL(str(LIBRARY))
        self.advance = self.library.memory_advance
        self.advance.argtypes = (
            [C.c_int]
            + [C.c_void_p] * 11
            + [C.c_int, C.c_float]
            + [C.c_void_p] * 5
            + [C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p, C.c_int]
            + [C.c_void_p] * 4
            + [
                C.c_float,
                C.c_float,
                C.c_float,
                C.c_int,
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.c_void_p,
                C.c_float,
                C.c_float,
            ]
        )
        self.advance.restype = None
        self.circuit = identify(self) if circuit is None else circuit
        if not math.isfinite(kc_rest) or not -80 <= kc_rest <= -45:
            raise ValueError("Invalid KC resting potential")
        self.rest = np.full(self.n, -52.0, dtype=np.float32)
        self.rest[self.circuit["kc"]] = kc_rest
        self.v[:] = self.rest
        if (
            not math.isfinite(adaptation_jump)
            or adaptation_jump < 0
            or not math.isfinite(adaptation_tau)
            or adaptation_tau <= 20
        ):
            raise ValueError("Invalid adaptation parameters")
        self.adaptation = np.zeros(self.n, dtype=np.float32)
        self.adaptation_jump = float(adaptation_jump)
        self.adaptation_tau = float(adaptation_tau)
        if modulation_mask is None:
            import pyarrow.feather as feather

            neurons = (
                feather.read_table(DATA / "normalized/neurons.feather")
                .to_pandas()
                .set_index("source_id")
                .loc[self.ids]
            )
            modulation_mask = neurons.neurotransmitter.isin(
                ["dopamine", "octopamine", "serotonin"]
            ).to_numpy(dtype=np.uint8)
        self.modulation_mask = np.asarray(modulation_mask, dtype=np.uint8).copy()
        if self.modulation_mask.shape != (self.n,) or np.any(self.modulation_mask > 1):
            raise ValueError("Invalid modulation mask")
        self.eta = float(eta)
        if not math.isfinite(self.eta) or self.eta < 0:
            raise ValueError("Finite nonnegative eta required")
        self.eligibility = np.zeros(self.n, dtype=np.float64)
        self.eligibility_last = np.zeros(self.n, dtype=np.int64)
        self.modulation = np.zeros(self.n, dtype=np.float32)
        self.modulation_last = np.zeros(self.n, dtype=np.int64)
        self.baseline_plastic = self.weight[self.circuit["edges"]].copy()
        self.initial_weight_sha256 = digest(self.weight)
        self.fields = [
            "v",
            "g",
            "refractory",
            "drive",
            "previous_drive",
            "queue",
            "queue_count",
            "counts",
            "luminance",
            "active",
            "active_flag",
            "nactive",
            "last",
            "eligibility",
            "eligibility_last",
            "modulation",
            "modulation_last",
            "adaptation",
        ]
        self.initial = {k: getattr(self, k).copy() for k in self.fields}
        from .rule import PARAMETERS as RULE_PARAMETERS

        self.rule_parameters = RULE_PARAMETERS.copy()
        self.rate_kc = np.zeros(len(self.circuit["edges"]), dtype=np.float64)
        self.rate_dan = np.zeros(len(self.circuit["dan"]), dtype=np.float64)
        self.memory_u = np.zeros_like(self.rate_kc)
        self.memory_w = np.zeros_like(self.rate_kc)
        self.tonic = (
            np.zeros(self.n, dtype=np.float32)
            if tonic is None
            else np.asarray(tonic, dtype=np.float32).copy()
        )
        self.dan_baseline_hz = (
            np.zeros(len(self.circuit["dan"]), dtype=np.float64)
            if dan_baseline_hz is None
            else np.asarray(dan_baseline_hz, dtype=np.float64).copy()
        )
        if self.tonic.shape != (self.n,) or not np.isfinite(self.tonic).all():
            raise ValueError("Invalid tonic current")
        if (
            self.dan_baseline_hz.shape != (len(self.rate_dan),)
            or not np.isfinite(self.dan_baseline_hz).all()
        ):
            raise ValueError("Invalid DAN baseline")
        self.weights_frozen = False
        for k in ["rate_kc", "rate_dan", "memory_u", "memory_w"]:
            self.fields.append(k)
            self.initial[k] = getattr(self, k).copy()

    def reset(self, keep_memory=False):
        if keep_memory:
            saved = (self.memory_u.copy(), self.memory_w.copy())
        for k, v in self.initial.items():
            getattr(self, k)[:] = v
        self.cursor = 0
        self.sim_ms = 0.0
        self.total_spikes = 0
        if not keep_memory:
            self.weight[self.circuit["edges"]] = self.baseline_plastic
        else:
            self.memory_u[:], self.memory_w[:] = saved

    def _preflight_step(self, duration_ms):
        if not math.isfinite(duration_ms) or duration_ms <= 0:
            raise ValueError("Invalid duration")
        steps = round(duration_ms / self.dt)
        if steps < 1:
            raise ValueError("Duration too short")
        maximum = int(np.iinfo(np.int64).max)
        delay = self.queue.shape[0] - 1
        if self.cursor > maximum - delay - steps:
            raise ValueError("Neural cursor would exceed native time range")
        if self.total_spikes > maximum - self.n * steps:
            raise ValueError("Total spike count would exceed checkpoint range")
        return steps

    def _neural_step(
        self,
        luminance,
        duration_ms,
        *,
        learning=False,
        stimulation=None,
        lamina_bias=12.0,
    ):
        light = np.asarray(luminance)
        if light.shape != (len(self.retina),) or not np.isfinite(light).all():
            raise ValueError("Invalid retinal input")
        steps = self._preflight_step(duration_ms)
        if not math.isfinite(lamina_bias):
            raise ValueError("Invalid interval/current")
        self.luminance += (1 - math.exp(-steps * self.dt / 10)) * (
            np.clip(light, 0, 1) - self.luminance
        )
        self.drive.fill(0)
        self.drive[self.lamina] = lamina_bias
        self.drive[self.retina] = 30 * self.luminance / (0.02 + self.luminance)
        self.drive += self.tonic
        if stimulation is not None:
            pulses = stimulation if isinstance(stimulation, list) else [stimulation]
            for indices, current in pulses:
                ix = np.asarray(indices, dtype=np.int32)
                amplitude = np.asarray(current, dtype=np.float32)
                if (
                    ix.ndim != 1
                    or np.any(ix < 0)
                    or np.any(ix >= self.n)
                    or not np.isfinite(amplitude).all()
                    or amplitude.shape not in [(), ix.shape]
                ):
                    raise ValueError("Invalid external stimulation")
                self.drive[ix] += amplitude
        self.counts.fill(0)
        clock = np.asarray([self.cursor], dtype=np.int64)
        c = self.circuit
        arrays = [
            self.ptr,
            self.post,
            self.weight,
            self.v,
            self.g,
            self.refractory,
            self.drive,
            self.previous_drive,
            self.queue,
            self.queue_count,
            clock,
        ]
        start = time.perf_counter()
        self.advance(
            self.n,
            *[x.ctypes.data for x in arrays],
            steps,
            self.dt,
            *[
                getattr(self, k).ctypes.data
                for k in ["counts", "active", "active_flag", "nactive", "last"]
            ],
            c["kc_mask"].ctypes.data,
            c["dan_index"].ctypes.data,
            self.eligibility.ctypes.data,
            self.eligibility_last.ctypes.data,
            len(c["edges"]),
            c["edges"].ctypes.data,
            c["pre"].ctypes.data,
            self.baseline_plastic.ctypes.data,
            c["gain"].ctypes.data,
            self.eta,
            PARAMETERS["trace_kc_seconds"] * 1000,
            PARAMETERS["minimum_fraction"],
            int(learning),
            self.modulation.ctypes.data,
            self.modulation_last.ctypes.data,
            self.modulation_mask.ctypes.data,
            self.rest.ctypes.data,
            self.adaptation.ctypes.data,
            self.adaptation_jump,
            self.adaptation_tau,
        )
        elapsed = time.perf_counter() - start
        self.cursor = int(clock[0])
        self.sim_ms = self.cursor * self.dt
        self.total_spikes += int(self.counts.sum())
        return self.counts.copy(), elapsed

    def step(
        self,
        luminance,
        duration_ms,
        *,
        learning=False,
        stimulation=None,
        lamina_bias=12.0,
    ):
        from .rule import advance

        remaining = self._preflight_step(duration_ms)
        total = np.zeros(self.n, dtype=np.int32)
        wall = 0.0
        while remaining:
            ticks = min(100, remaining)
            interval = ticks * self.dt
            # The original LTD update is disabled. Only the centered rule below
            # writes candidate memory efficacies; all neural integration remains.
            c, t = self._neural_step(
                luminance,
                interval,
                learning=False,
                stimulation=stimulation,
                lamina_bias=lamina_bias,
            )
            seconds = interval / 1000
            advance(
                self.rate_kc,
                self.rate_dan,
                self.memory_u,
                self.memory_w,
                c[self.circuit["pre"]] / seconds,
                c[self.circuit["dan"]] / seconds - self.dan_baseline_hz,
                self.circuit["gain"],
                seconds,
                self.eta,
                learning,
                self.weights_frozen,
            )
            if not self.weights_frozen:
                self.weight[self.circuit["edges"]] = self.baseline_plastic * (
                    1 + self.memory_w
                )
            total += c
            wall += t
            remaining -= ticks
        self.counts[:] = total
        return total, wall

    def memory(self):
        w = self.weight[self.circuit["edges"]]
        fraction = w / self.baseline_plastic
        return {
            "plastic_edges": len(w),
            "changed_edges": int(np.count_nonzero(w != self.baseline_plastic)),
            "mean_efficacy": float(fraction.mean()),
            "minimum_efficacy": float(fraction.min()),
            "sha256": digest(w),
            "model": MODEL,
        }

    def _candidate_positions(self, target_indices):
        targets = np.asarray(target_indices)
        if (targets.ndim != 1 or targets.size == 0
                or not np.issubdtype(targets.dtype, np.integer)
                or np.any(targets < 0) or np.any(targets >= self.n)
                or len(np.unique(targets)) != len(targets)):
            raise ValueError("Invalid candidate target indices")
        positions = np.flatnonzero(np.isin(self.post[self.circuit["edges"]], targets))
        if not len(positions):
            raise ValueError("No candidate edges for target indices")
        return positions

    def candidate_memory(self, target_indices: np.ndarray) -> CandidateMemory:
        """Copy ordered KC-to-target candidate state at the current clock."""
        positions = self._candidate_positions(target_indices)

        def frozen_copy(value):
            copied = np.array(value, copy=True)
            return np.frombuffer(copied.tobytes(), dtype=copied.dtype).reshape(copied.shape)

        edges = self.circuit["edges"][positions]
        return CandidateMemory(
            target_indices=frozen_copy(target_indices),
            edge_indices=frozen_copy(edges),
            memory_u=frozen_copy(self.memory_u[positions]),
            memory_w=frozen_copy(self.memory_w[positions]),
            weight=frozen_copy(self.weight[edges]),
            cursor=self.cursor,
            sim_ms=self.sim_ms,
        )

    def replace_candidate_memory(self, snapshot: CandidateMemory) -> None:
        """Validate a complete candidate state before replacing its three slices."""
        if not isinstance(snapshot, CandidateMemory):
            raise ValueError("Expected a candidate memory snapshot")
        if (isinstance(snapshot.cursor, (bool, np.bool_))
                or not isinstance(snapshot.cursor, numbers.Integral)
                or isinstance(snapshot.sim_ms, (bool, np.bool_))
                or not isinstance(snapshot.sim_ms, numbers.Real)
                or not math.isfinite(snapshot.sim_ms)):
            raise ValueError("Invalid candidate memory clock metadata")
        if snapshot.cursor != self.cursor or snapshot.sim_ms != self.sim_ms:
            raise ValueError("Candidate memory clocks differ")
        names = ("target_indices", "edge_indices", "memory_u", "memory_w", "weight")
        if any(type(getattr(snapshot, name)) is not np.ndarray for name in names):
            raise ValueError("Candidate memory arrays must be plain ndarrays")
        staged = {
            name: np.array(getattr(snapshot, name), copy=True, subok=False)
            for name in names
        }
        positions = self._candidate_positions(staged["target_indices"])
        edges = self.circuit["edges"][positions]
        expected = {
            "edge_indices": (edges.dtype, edges.shape),
            "memory_u": (self.memory_u.dtype, positions.shape),
            "memory_w": (self.memory_w.dtype, positions.shape),
            "weight": (self.weight.dtype, positions.shape),
        }
        for name, (dtype, shape) in expected.items():
            value = staged[name]
            if value.dtype != dtype or value.shape != shape:
                raise ValueError(f"Invalid candidate {name} shape or dtype")
            if not np.isfinite(value).all():
                raise ValueError(f"Nonfinite candidate {name}")
        if not np.array_equal(staged["edge_indices"], edges):
            raise ValueError("Candidate edge identity or order differs")
        lower = self.rule_parameters["minimum_fraction"] - 1
        upper = self.rule_parameters["maximum_fraction"] - 1
        for value in (staged["memory_u"], staged["memory_w"]):
            if np.any(value < lower) or np.any(value > upper):
                raise ValueError("Candidate memory exceeds rule bounds")
        expected_weight = (
            self.baseline_plastic[positions] * (1 + staged["memory_w"])
        ).astype(self.weight.dtype)
        if not np.allclose(
            staged["weight"], expected_weight,
            rtol=2 * np.finfo(self.weight.dtype).eps,
            atol=np.finfo(self.weight.dtype).tiny,
        ):
            raise ValueError("Candidate weight disagrees with baseline and memory")
        if not all(array.flags.writeable for array in
                   (self.memory_u, self.memory_w, self.weight)):
            raise ValueError("Candidate destination is read-only")
        self.memory_u[positions] = staged["memory_u"]
        self.memory_w[positions] = staged["memory_w"]
        self.weight[edges] = staged["weight"]

    def model_provenance(self):
        """Return immutable numerical identity shared by checkpoints and engines."""
        return {
            "model": MODEL,
            "model_fingerprint": model_fingerprint(),
            "build": self.build,
            "eta": self.eta,
            "parameters": PARAMETERS,
            "graph_ids_sha256": digest(self.ids),
            "graph_ptr_sha256": digest(self.ptr),
            "graph_post_sha256": digest(self.post),
            "plastic_edges_sha256": digest(self.circuit["edges"]),
            "configuration_sha256": self.configuration_signature(),
        }

    def lock_model_provenance(self):
        """Snapshot provenance and freeze large immutable numerical inputs."""
        if hasattr(self, "_locked_model_provenance_json"):
            self.assert_model_provenance_locked()
            return json.loads(self._locked_model_provenance_json)

        provenance = self.model_provenance()
        arrays = self._model_provenance_arrays()
        for value in arrays.values():
            value.flags.writeable = False
        self._locked_model_provenance_arrays = arrays
        self._locked_model_provenance_values = self._model_provenance_values_json()
        self._locked_model_provenance_json = json.dumps(
            provenance,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return json.loads(self._locked_model_provenance_json)

    def assert_model_provenance_locked(self):
        """Reject cheap-to-detect divergence from a locked engine identity."""
        try:
            current = self._model_provenance_arrays()
            unchanged_arrays = (
                current.keys() == self._locked_model_provenance_arrays.keys()
                and all(
                    current[name] is original and not original.flags.writeable
                    for name, original in self._locked_model_provenance_arrays.items()
                )
            )
            unchanged_values = (
                self._model_provenance_values_json()
                == self._locked_model_provenance_values
            )
        except (AttributeError, TypeError, ValueError):
            unchanged_arrays = False
            unchanged_values = False
        if not unchanged_arrays or not unchanged_values:
            raise RuntimeError("Model provenance changed after engine identity")

    def _model_provenance_arrays(self):
        arrays = {
            name: getattr(self, name)
            for name in [
                "ids",
                "ptr",
                "post",
                "retina",
                "uv",
                "lamina",
                "sugar",
                "modulation_mask",
                "tonic",
                "dan_baseline_hz",
                "rest",
                "baseline_plastic",
            ]
        }
        arrays.update(
            {
                f"circuit.{name}": value
                for name, value in self.circuit.items()
                if isinstance(value, np.ndarray)
            }
        )
        arrays.update(
            {
                name: getattr(self, name)
                for name in ["r8", "r8_uv", "r8_channel", "corrected_edges"]
                if hasattr(self, name)
            }
        )
        return arrays

    def _model_provenance_values_json(self):
        return json.dumps(
            {
                "model": MODEL,
                "build": self.build,
                "dt": self.dt,
                "eta": self.eta,
                "parameters": PARAMETERS,
                "initial_weight_sha256": self.initial_weight_sha256,
                "rule_parameters": self.rule_parameters,
                "adaptation_jump": self.adaptation_jump,
                "adaptation_tau": self.adaptation_tau,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    def checkpoint(self, path):
        metadata = {
            **self.model_provenance(),
            "cursor": self.cursor,
            "weights_frozen": self.weights_frozen,
            "total_spikes": self.total_spikes,
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".partial")
        with temporary.open("wb") as handle:
            np.savez_compressed(
                handle,
                metadata=json.dumps(metadata),
                weight=self.weight,
                **{k: getattr(self, k) for k in self.fields},
            )
        temporary.replace(path)

    def restore(self, path):
        expected = self.model_provenance()
        targets = {name: getattr(self, name) for name in ["weight", *self.fields]}
        metadata, arrays = load_checkpoint(path, expected, targets, self.n)
        sim_ms = metadata["cursor"] * self.dt
        for name, target in targets.items():
            target[:] = arrays[name]
        self.cursor = metadata["cursor"]
        self.sim_ms = sim_ms
        self.total_spikes = metadata["total_spikes"]
        self.weights_frozen = metadata["weights_frozen"]

    def configuration_signature(self):
        # Equal cell IDs and CSR endpoints alone do not imply equal input
        # geometry, original efficacies or compartment assignment.
        return {
            "initial_weight": self.initial_weight_sha256,
            "modulation_mask": digest(self.modulation_mask),
            "rule": self.rule_parameters,
            "rule_sha256": hashlib.sha256(
                Path(__file__).with_name("rule.py").read_bytes()
            ).hexdigest(),
            "tonic": digest(self.tonic),
            "dan_baseline_hz": digest(self.dan_baseline_hz),
            "rest": digest(self.rest),
            "adaptation_jump": self.adaptation_jump,
            "adaptation_tau": self.adaptation_tau,
            **{
                k: digest(getattr(self, k)) for k in ["retina", "uv", "lamina", "sugar"]
            },
            **{
                k: digest(self.circuit[k])
                for k in ["pre", "gain", "kc_mask", "dan_index"]
            },
        }
