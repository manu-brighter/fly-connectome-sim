"""Direct private worker tests: no simulator, graph, DLL or compiler."""

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from test_native_protocol import (
    INCARNATION, SESSION, IMAGE, DISPATCH, DIGEST, header_fixture, envelope,
)


def api():
    return importlib.import_module("market.native_worker")


class TickClock:
    def __init__(self):
        self.ns = 100

    def sample(self):
        self.ns += 1
        return SimpleNamespace(monotonic_ns=self.ns)


class FakeEngine:
    def __init__(self, header, *, fail=None):
        self.header = header
        self.brain = SimpleNamespace(sim_ms=0)
        self.frames = []
        self.callback = None
        self.fail = fail

    def identity(self):
        return self.header["engine_identity"]

    def configure_cell_observer(self, indices, callback):
        assert self.brain.sim_ms == 0
        assert indices == [cell["model_index"] for cell in self.header["cells"]]
        self.callback = callback

    def observe(self, frame, duration_ms, **kwargs):
        assert self.callback is not None
        assert duration_ms == 500
        assert kwargs == dict(learning=False, stimulation=None,
                              pathway_detail=False, qualification_detail=False)
        assert frame.shape == (64, 64, 3) and frame.dtype == np.uint8
        index = len(self.frames)
        self.frames.append(frame.tobytes())
        for ordinal in range(50):
            self.callback(dict(observation_index=index, bin_index=ordinal,
                               start_tick=index * 5000 + ordinal * 100,
                               end_tick=index * 5000 + (ordinal + 1) * 100,
                               counts=[1] * 256))
            if self.fail == "partial" and ordinal == 4:
                raise ValueError("partial native progress")
        self.brain.sim_ms += 500
        groups = self.header["selection"]["group_population_counts"]
        return dict(sim_ms=self.brain.sim_ms, interval_ms=500, input_shape=[64, 64, 3],
                    input_dtype="uint8", input_sha256=api().protocol.rgb_sha256(frame.tobytes()),
                    learning=False, stimulation=None, engine_identity=self.identity(),
                    bins=[dict(end_ms=index * 500 + (i + 1) * 10, duration_ms=10,
                               group_spikes={g: groups[g] for g in api().protocol.GROUPS})
                          for i in range(50)],
                    total_spikes=204450, rates_hz={g: 100.0 for g in groups},
                    compute_seconds=0.01, kernel_seconds=0.009)


def commands(image_at=None, rgb=None):
    permit = dict(id=IMAGE, incarnation=INCARNATION, dispatch_id=DISPATCH,
                  worker_session=SESSION, frame_sha256=api().protocol.rgb_sha256(rgb or bytes(12288)),
                  deadline_ns=100000, exposure_observations=8)
    yield envelope("release", last_observation_index=None, next_observation_index=0,
                   action="black", permit=None, dispatch_id=None, exposure_ordinal=None), b""
    for index in range(1, 40):
        active = image_at is not None and image_at <= index < image_at + 8
        ordinal = index - image_at if active else None
        action = "image" if ordinal == 0 else "continue_image" if active else "black"
        yield envelope("ack", last_observation_index=index - 1, next_observation_index=index,
                       action=action, permit=permit if ordinal == 0 else None,
                       dispatch_id=DISPATCH if active else None, exposure_ordinal=ordinal), rgb if ordinal == 0 else b""
    yield envelope("ack", last_observation_index=39, next_observation_index=None,
                   action="end", permit=None, dispatch_id=None, exposure_ordinal=None), b""


def run_worker(*, image_at=None, fail=None, send_hook=None):
    header = header_fixture()
    engine = FakeEngine(header, fail=fail)
    sent = []
    clock = TickClock()
    rgb = bytes([9]) * 12288
    incoming = iter(commands(image_at, rgb))

    def send(kind, fields, binary=b"", *, deadline_ns):
        sent.append((kind, fields, binary, deadline_ns))
        if send_hook:
            send_hook(kind, clock)

    worker = api()._Worker(engine, header, clock, send,
                          lambda **kwargs: next(incoming), wall_deadline_ns=1000000000000)
    return worker, engine, sent, clock


def test_forty_black_observations_advance_with_original_bins_and_end():
    worker, engine, sent, _ = run_worker()
    worker.run()
    assert len(engine.frames) == 40 and set(engine.frames) == {bytes(12288)}
    rows = [fields for kind, fields, _, _ in sent if kind == "observation"]
    assert [r["observation_index"] for r in rows] == list(range(40))
    assert rows[-1]["end_tick"] == 200000
    assert sent[-1][0] == "ended" and sent[-1][1]["reason"] == "model_limit"
    assert all(len(binary) == 12800 for kind, _, binary, _ in sent if kind == "observation")


@pytest.mark.parametrize("image_at", [1, 32])
def test_image_is_eight_contiguous_identical_frames_complete_before_next_command(image_at):
    worker, engine, sent, _ = run_worker(image_at=image_at)
    worker.run()
    assert engine.frames[image_at:image_at + 8] == [bytes([9]) * 12288] * 8
    kinds = [kind for kind, _, _, _ in sent]
    start = kinds.index("start")
    assert kinds[start:start + 10] == ["start"] + ["observation"] * 8 + ["complete"]
    complete = sent[start + 9]
    observation7 = sent[start + 8]
    assert complete[1]["receipt"]["observation_indices"] == list(range(image_at, image_at + 8))
    assert complete[3] == observation7[3]
    assert sent[start + 1][1]["first_call_ns"] >= sent[start][1]["receipt"]["started_ns"]


def test_partial_native_failure_is_terminal_never_reobserved():
    worker, engine, sent, _ = run_worker(fail="partial")
    with pytest.raises(ValueError):
        worker.run()
    with pytest.raises(ValueError):
        worker.run()
    assert len(engine.frames) == 1
    assert not any(kind == "observation" for kind, *_ in sent)


def test_start_transmission_expiry_prevents_first_image_observe():
    def stall(kind, clock):
        if kind == "start":
            clock.ns = 100000

    worker, engine, sent, _ = run_worker(image_at=1, send_hook=stall)
    with pytest.raises(ValueError, match="deadline"):
        worker.run()
    assert len(engine.frames) == 1
    assert any(kind == "start" for kind, *_ in sent)
    assert not any(kind == "complete" for kind, *_ in sent)


def test_new_image_after_boundary32_fails_without_native_call():
    worker, engine, _, _ = run_worker(image_at=33)
    with pytest.raises(ValueError):
        worker.run()
    assert len(engine.frames) == 33


def test_nonzero_engine_clock_and_identity_mismatch_fail_before_advance():
    worker, engine, _, _ = run_worker()
    engine.brain.sim_ms = 1
    with pytest.raises(ValueError):
        worker.run()
    assert not engine.frames


def test_bootstrap_rejects_missing_declared_packages_before_import(tmp_path):
    bindings = dict(project_root=str(tmp_path), dependencies=dict(
        site_packages=str(tmp_path / ".venv/Lib/site-packages"),
        numpy="2.4.6", pandas="3.0.5", pyarrow="25.0.1"), files={})
    with pytest.raises(ValueError, match="source"):
        api()._bootstrap_dependencies(bindings)


def test_worker_configures_fixed_observer_before_readiness_without_advancing():
    worker, engine, _, _ = run_worker()
    worker.configure()
    assert engine.callback is not None and engine.frames == []
    worker.run()
    assert len(engine.frames) == 40


def test_start_deadline_equality_prevents_first_call():
    def equality(kind, clock):
        if kind == "start":
            clock.ns = 99999
    worker, engine, _, _ = run_worker(image_at=1, send_hook=equality)
    with pytest.raises(ValueError, match="deadline"):
        worker.run()
    assert len(engine.frames) == 1


def test_bootstrap_declared_packages_reject_shadow_and_wrong_version(tmp_path, monkeypatch):
    site = tmp_path / ".venv/Lib/site-packages"
    files = {}
    for name, version in (("numpy", "2.4.6"), ("pandas", "3.0.5"), ("pyarrow", "25.0.1")):
        package = site / name
        package.mkdir(parents=True)
        init = package / "__init__.py"
        init.write_text('__version__ = "' + version + '"\n', encoding="utf-8")
        files[name + "_init"] = dict(path=str(init))
        monkeypatch.delitem(sys.modules, name, raising=False)
    bindings = dict(project_root=str(tmp_path), dependencies=dict(site_packages=str(site),
        numpy="2.4.6", pandas="3.0.5", pyarrow="25.0.1"), files=files)
    # Real numerical imports in this pytest process have extension submodules;
    # the fixture must reject those stale origins before trying a fake top-level.
    monkeypatch.syspath_prepend(str(site))
    with pytest.raises(ValueError, match="source"):
        api()._bootstrap_dependencies(bindings)


@pytest.mark.skipif(sys.platform != "win32", reason="installed bootstrap binds the fixed Windows .venv/Lib layout")
def test_bootstrap_declared_existing_venv_imports_only_fixed_versions():
    root = Path(__file__).absolute().parents[2]
    site = root / ".venv/Lib/site-packages"
    bindings = dict(project_root=str(root), dependencies=dict(site_packages=str(site),
        numpy="2.4.6", pandas="3.0.5", pyarrow="25.0.1"),
        files={name + "_init": dict(path=str(site / name / "__init__.py"))
               for name in ("numpy", "pandas", "pyarrow")})
    result = api()._bootstrap_dependencies(bindings)
    assert {name: module.__version__ for name, module in result.items()} == {
        "numpy": "2.4.6", "pandas": "3.0.5", "pyarrow": "25.0.1"}


def test_bootstrap_private_package_versions_checked_after_origin(tmp_path, monkeypatch):
    import importlib.machinery
    from types import ModuleType
    site = tmp_path / ".venv/Lib/site-packages"
    files, modules = {}, {}
    for module_name in tuple(sys.modules):
        if module_name.split(".")[0] in ("numpy", "pandas", "pyarrow"):
            monkeypatch.delitem(sys.modules, module_name)
    for name, version in (("numpy", "2.4.6"), ("pandas", "3.0.5"), ("pyarrow", "25.0.1")):
        root = site / name
        root.mkdir(parents=True)
        init = root / "__init__.py"
        init.write_bytes(b"# harmless private dependency fixture\n")
        module = ModuleType(name)
        module.__file__, module.__version__ = str(init), version
        module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, origin=str(init))
        monkeypatch.setitem(sys.modules, name, module)
        modules[name] = module
        files[name + "_init"] = dict(path=str(init))
    bindings = dict(project_root=str(tmp_path), dependencies=dict(site_packages=str(site),
        numpy="2.4.6", pandas="3.0.5", pyarrow="25.0.1"), files=files)
    assert api()._bootstrap_dependencies(bindings) == modules
    modules["pandas"].__version__ = "0.0.0"
    with pytest.raises(ValueError, match="source"):
        api()._bootstrap_dependencies(bindings)


def test_binding_accepts_only_checksum_pinned_empty_preserved_source(tmp_path):
    from market import native_session as n, native_protocol as p, native_windows as w
    import hashlib
    import time
    source = n.ROOT / 'src/fly_connectome_sim/neural/__init__.py'
    assert source.read_bytes() == b''
    assert p.PRESERVED_SOURCES['src/fly_connectome_sim/neural/__init__.py'] == hashlib.sha256(b'').hexdigest()
    binding = n._binding(source, 1048576, time.perf_counter_ns() + 1000000000)
    assert binding['bytes'] == 0 and binding['sha256'] == p.EMPTY_SHA256
    w.compare_bound_files(
        dict(files={'src/fly_connectome_sim/neural/__init__.py': binding}),
        deadline_ns=time.perf_counter_ns() + 1000000000,
    )
    for name in ('unbound.py', 'memory.dll', 'graph.npz', 'protocol.json'):
        empty = tmp_path / name
        empty.write_bytes(b'')
        with pytest.raises(ValueError, match='source'):
            n._binding(empty, 1048576, time.perf_counter_ns() + 1000000000)
