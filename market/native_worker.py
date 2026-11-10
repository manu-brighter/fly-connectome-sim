"""Private bounded worker. Numerical imports occur only after bound bootstrap."""

import argparse
import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
import queue
import sys
import threading

from . import native_protocol as protocol
from .price_service import SystemClock
from .native_protocol import NativeProfile, owned, scope, from_declaration, current_profile


def _require(value, code="protocol"):
    if not value:
        raise protocol.ProtocolError(code)


def _now(clock, previous=None):
    value = clock.sample().monotonic_ns
    _require(type(value) is int and 0 <= value <= protocol.MAX_NS
             and (previous is None or value >= previous), "clock")
    return value


def _ordinary(path):
    path = Path(path).absolute()
    for member in (path, *path.parents):
        info = member.lstat()
        _require(not member.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400, "source")
    return path


def _bootstrap_dependencies(bindings):
    """Check declared package resolution before and after importing dependencies."""
    try:
        project = _ordinary(bindings["project_root"])
        site = _ordinary(bindings["dependencies"]["site_packages"])
        _require(site == project / ".venv/Lib/site-packages" and site.is_dir(), "source")
        roots = {name: _ordinary(site / name) for name in ("numpy", "pandas", "pyarrow")}
        for name, root in roots.items():
            _require(root.is_dir(), "source")
            init = _ordinary(root / "__init__.py")
            _require(init == Path(bindings["files"][name + "_init"]["path"]), "source")
            spec = importlib.util.find_spec(name)
            _require(spec is not None and spec.origin is not None and Path(spec.origin).absolute() == init, "source")

        def check_loaded():
            for module_name, module in tuple(sys.modules.items()):
                top = module_name.split(".")[0]
                if top in roots and module is not None:
                    origin = getattr(module, "__file__", None)
                    _require(origin is not None and _ordinary(origin).is_relative_to(roots[top]), "source")

        check_loaded()
        result = {}
        for name in roots:
            result[name] = importlib.import_module(name)
            _require(result[name].__version__ == bindings["dependencies"][name], "source")
        check_loaded()
        return result
    except (OSError, KeyError, ImportError, AttributeError, ValueError) as error:
        if isinstance(error, protocol.ProtocolError):
            raise
        raise protocol.ProtocolError("source") from None


def _initial_identity(engine, bindings):
    """Match the initial engine against every prepared native build field."""
    identity = engine.identity()
    _require(identity["model_provenance"]["build"] == dict(bindings.native_metadata.to_dict(),
        model="stonkfly-dual-compartment-v1") and engine.brain.sim_ms == 0, "source")
    return identity


@owned
class _Worker:
    """Single-owner call loop; direct fake injection is private and never a CLI option."""

    def __init__(self, engine, header, clock, send, receive, *, wall_deadline_ns, profile=None):
        self.profile = profile or NativeProfile()
        self.engine, self.header, self.clock = engine, protocol.validate_header(header), clock
        self.send, self.receive = send, receive
        self.wall_deadline_ns = wall_deadline_ns
        self.completed = 0
        self.permit = self.start = self.ordinal = None
        self.rgb = bytes(12288)
        self._attempted = False
        self._last_ns = None
        self.previous = None
        self.ring = None

    def now(self):
        value = _now(self.clock, self._last_ns)
        self._last_ns = value
        _require(self.profile.live or value < self.wall_deadline_ns, "deadline")
        return value

    def configure(self):
        _require(self.ring is None and not self._attempted)
        # These are the unchanged observer/ring APIs, imported only after bootstrap
        # in production. The private direct entrypoint accepts no alternate model.
        scripts = Path(__file__).absolute().parents[1] / "scripts"
        module = sys.modules.get("market_live_buffers")
        _require(module is None or Path(module.__file__).absolute() == scripts / "market_live_buffers.py", "source")
        sys.path.insert(0, str(scripts))
        try:
            from market_live_buffers import CellRing
        finally:
            del sys.path[0]
        _require(self.engine.brain.sim_ms == 0 and self.engine.identity() == self.header.engine_identity.to_dict(), "source")
        self.ring = CellRing()
        self.engine.configure_cell_observer([cell.model_index for cell in self.header.cells], self.ring)

    def run(self):
        _require(not self._attempted, "worker_outcome_unknown")
        if self.ring is None:
            self.configure()
        self._attempted = True
        import numpy as np
        command_deadline = min(self.now() + 5_000_000_000, self.wall_deadline_ns)
        while True:
            if self.profile.live and self.now() >= self.wall_deadline_ns:
                self._ended("wall_limit")
                return
            try:
                command, binary = self.receive(deadline_ns=command_deadline, max_body=16384)
            except BaseException:
                if self.profile.live and self.now() >= self.wall_deadline_ns and command_deadline == self.wall_deadline_ns:
                    self._ended("wall_limit")
                    return
                raise
            command = protocol.validate_message(command, "parent", binary)
            now = self.now()
            if self.profile.live and now >= self.wall_deadline_ns:
                self._ended("wall_limit")
                return
            _require(now < command_deadline, "deadline")
            if command.type == "stop":
                self._ended("cancelled")
                return
            expected = "release" if self.completed == 0 else "ack"
            _require(command.type == expected)
            _require(command.last_observation_index == (self.completed - 1 if self.completed else None))
            _require(command.next_observation_index == (self.completed if self.completed < protocol.limits()["model_observations"] else None))
            if command.action == "end":
                _require(self.completed == protocol.limits()["model_observations"] and self.permit is None)
                self._ended("model_limit")
                return
            _require(self.completed < protocol.limits()["model_observations"])
            if self.permit is not None:
                _require(command.action == "continue_image" and command.dispatch_id == self.permit.dispatch_id
                         and command.exposure_ordinal == self.ordinal + 1)
                self.ordinal += 1
            elif command.action == "image":
                _require(self.completed <= protocol.limits()["model_observations"] - 8 and command.permit.incarnation == command.incarnation
                         and command.permit.worker_session == command.worker_session)
                self.permit, self.ordinal, self.rgb = command.permit, 0, binary
                _require(now < self.permit.deadline_ns, "deadline")
                started = self.now()
                self.start = protocol.FrozenRecord(dict(
                    **{key: self.permit[key] for key in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256")},
                    started_ns=started, first_observation_index=self.completed,
                ))
                self.send("start", dict(receipt=self.start), deadline_ns=min(started + 5_000_000_000, self.wall_deadline_ns))
            else:
                _require(command.action == "black" and self.permit is None)
                self.rgb = bytes(12288)
            frame = np.frombuffer(self.rgb, dtype=np.uint8).reshape(64, 64, 3)
            # No IO/admission occurs between this final TTL check and observe.
            wall_start = self.now()
            if self.permit is not None and self.ordinal == 0:
                _require(wall_start < self.permit.deadline_ns, "deadline")
            telemetry = self.engine.observe(frame, 500, learning=False, stimulation=None,
                                            pathway_detail=False, qualification_detail=False)
            completion = self.now()
            _require(completion < wall_start + 30_000_000_000, "deadline")
            if self.profile.live and completion >= self.wall_deadline_ns:
                self._ended("wall_limit")
                return
            _require(completion < wall_start + 30_000_000_000, "deadline")
            export = self.ring.export_observation(self.completed)
            data = export["counts"].tobytes(order="C")
            _require(telemetry["input_dtype"] == "uint8" and telemetry["input_shape"] == [64, 64, 3]
                     and telemetry["input_sha256"] == protocol.rgb_sha256(self.rgb)
                     and telemetry["learning"] is False and telemetry["stimulation"] is None
                     and "pathway_detail" not in telemetry and "qualification_detail" not in telemetry
                     and telemetry["engine_identity"] == self.header.engine_identity.to_dict()
                     and telemetry["sim_ms"] == (self.completed + 1) * 500
                     and telemetry["interval_ms"] == 500)
            bins = telemetry["bins"]
            _require(type(bins) is list and len(bins) == 50)
            rows = []
            for ordinal, row in enumerate(bins):
                _require(set(row) == {"end_ms", "duration_ms", "group_spikes"}
                         and row["duration_ms"] == 10
                         and row["end_ms"] == self.completed * 500 + (ordinal + 1) * 10)
                rows.append([row["group_spikes"][group] for group in protocol.GROUPS])
            spikes = {group: sum(row[i] for row in rows) for i, group in enumerate(protocol.GROUPS)}
            fields = dict(observation_index=self.completed, input_kind="image" if self.permit else "black",
                          image_id=self.permit.id if self.permit else None,
                          dispatch_id=self.permit.dispatch_id if self.permit else None,
                          exposure_ordinal=self.ordinal, frame_sha256=protocol.rgb_sha256(self.rgb),
                          engine_identity_sha256=self.header.engine_identity.sha256,
                          header_sha256=protocol.canonical_sha256(self.header),
                          start_tick=self.completed * 5000, end_tick=(self.completed + 1) * 5000,
                          wall_start_ns=wall_start, wall_completion_ns=completion, learning=False,
                          stimulation=None, pathway_detail=False, qualification_detail=False,
                          group_spikes=spikes, group_rates_hz=telemetry["rates_hz"], group_bin_counts=rows,
                          total_spikes=telemetry["total_spikes"], compute_seconds=telemetry["compute_seconds"],
                          kernel_seconds=telemetry["kernel_seconds"], cell_bytes_sha256=hashlib.sha256(data).hexdigest(),
                          start_receipt=self.start if self.ordinal == 0 else None,
                          first_call_ns=wall_start if self.ordinal == 0 else None)
            envelope = dict(schema=protocol.schema("ipc"), type="observation", seq=0,
                            incarnation=command.incarnation, worker_session=command.worker_session,
                            protocol_sha256=command.protocol_sha256, launch_nonce=command.launch_nonce, **fields)
            observation = protocol.validate_observation(envelope, data, self.header,
                                                       permit=self.permit, previous=self.previous)
            self.previous = observation
            self.completed += 1
            # One epoch covers observation7, complete and the single ACK/end.
            exchange_ns = self.now()
            command_deadline = min(exchange_ns + 5_000_000_000, self.wall_deadline_ns)
            self.send("observation", fields, data, deadline_ns=command_deadline)
            if self.ordinal == 7:
                complete = dict(**{key: self.permit[key] for key in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256")},
                                observation_indices=list(range(self.completed - 8, self.completed)), completed_ns=completion)
                self.send("complete", dict(receipt=complete), deadline_ns=command_deadline)
                self.permit = self.start = self.ordinal = None
                self.rgb = bytes(12288)

    def _ended(self, reason):
        now = self.now()
        self.send("ended", dict(reason=reason, observations_completed=self.completed,
                                last_observation_index=self.completed - 1 if self.completed else None,
                                last_tick=self.completed * 5000, wall_ns=now,
                                header_sha256=protocol.canonical_sha256(self.header),
                                engine_identity_sha256=self.header.engine_identity.sha256, fault=None),
                  deadline_ns=now + 5_000_000_000 if self.profile.live else min(now + 5_000_000_000, self.wall_deadline_ns))


@owned
class _Pipe:
    def __init__(self, bindings, clock):
        self.profile = current_profile()
        self.bindings, self.clock = bindings, clock
        self.validator = protocol.ProtocolValidator()
        self.seq = 0
        self.nonce = None

    def receive(self, *, deadline_ns, max_body=4096):
        outbox = queue.Queue(maxsize=1)

        def read():
            try:
                with scope(self.profile):
                    outbox.put(protocol.read_frame(sys.stdin.buffer, "parent", max_body=max_body))
            except BaseException as error:
                outbox.put(error)

        threading.Thread(target=read, name="native-command", daemon=True).start()
        remaining = (deadline_ns - _now(self.clock)) / 1e9
        _require(remaining > 0, "deadline")
        try:
            frame = outbox.get(timeout=remaining)
        except queue.Empty:
            raise protocol.ProtocolError("deadline") from None
        if isinstance(frame, BaseException):
            raise frame
        _require(frame is not None)
        message = self.validator.accept(frame.message, "parent", frame.binary, receipt_ns=_now(self.clock))
        _require(message.incarnation == self.bindings.incarnation
                 and message.worker_session == self.bindings.worker_session
                 and message.protocol_sha256 == self.bindings.protocol_sha256)
        self.nonce = message.launch_nonce
        return message, frame.binary

    def send(self, kind, fields, binary=b"", *, deadline_ns):
        message = dict(schema=protocol.schema("ipc"), type=kind, seq=self.seq,
                       incarnation=self.bindings.incarnation, worker_session=self.bindings.worker_session,
                       protocol_sha256=self.bindings.protocol_sha256, launch_nonce=self.nonce, **fields)
        self.validator.accept(message, "worker", binary, receipt_ns=_now(self.clock))
        raw = protocol.encode_frame(message, binary, direction="worker")
        outbox = queue.Queue(maxsize=1)

        def write():
            try:
                for offset in range(0, len(raw), 65536):
                    part = memoryview(raw)[offset:offset + 65536]
                    while part:
                        count = sys.stdout.buffer.write(part)
                        _require(type(count) is int and count > 0, "storage")
                        part = part[count:]
                sys.stdout.buffer.flush()
                outbox.put(None)
            except BaseException as error:
                outbox.put(error)

        threading.Thread(target=write, name="native-result", daemon=True).start()
        remaining = (min(deadline_ns, _now(self.clock) + 5_000_000_000) - _now(self.clock)) / 1e9
        _require(remaining > 0, "deadline")
        try:
            result = outbox.get(timeout=remaining)
        except queue.Empty:
            raise protocol.ProtocolError("deadline") from None
        if result is not None:
            raise result
        _require(_now(self.clock) < deadline_ns, "deadline")
        self.seq += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--bindings", required=True, type=Path)
    args = parser.parse_args()
    clock = SystemClock()
    started = _now(clock)
    guard = None
    profile_scope = None
    try:
        declaration_raw = protocol._bounded_file(args.protocol, 1048576)
        bindings_raw = protocol._bounded_file(args.bindings, 1048576)
        declaration_value = protocol.parse_json(declaration_raw, byte_limit=1048576, node_limit=20000)
        profile = from_declaration(declaration_value)
        profile_scope = scope(profile)
        profile_scope.__enter__()
        declaration = protocol.validate_protocol(declaration_value)
        bindings = protocol.validate_bindings(protocol.parse_json(bindings_raw, byte_limit=1048576, node_limit=20000),
                                               declaration, protocol_sha256=hashlib.sha256(declaration_raw).hexdigest())
        _require(args.protocol.absolute() == Path(bindings.work_root) / "protocol.json"
                 and args.bindings.absolute() == Path(bindings.work_root) / "bindings.json", "source")
        from .native_windows import CompilerProbeGuard, PRIMITIVES, compare_bound_files
        compare_bound_files(bindings, deadline_ns=started + 180_000_000_000)
        pipe = _Pipe(bindings, clock)
        hello, _ = pipe.receive(deadline_ns=started + 180_000_000_000)
        _require(hello.type == "hello" and hello.bindings_sha256 == hashlib.sha256(bindings_raw).hexdigest())
        held = PRIMITIVES.WindowsProcess(os.getpid())
        try:
            identity = held.identity()
            identity["executable_sha256"] = bindings.files.worker_exe.sha256
            _require(Path(identity["executable"]).absolute() == Path(bindings.files.worker_exe.path).absolute(), "ownership")
        finally:
            held.close()
        pipe.send("hello", dict(bindings_sha256=hello.bindings_sha256, worker=identity,
                                worker_clock=clock.describe()), deadline_ns=started + 180_000_000_000)
        for index in range(3):
            challenge, _ = pipe.receive(deadline_ns=started + 180_000_000_000)
            child_ns = _now(clock)
            pipe.send("clock", dict(challenge_index=index, p0_ns=challenge.p0_ns, child_ns=child_ns),
                      deadline_ns=min(started + 180_000_000_000, challenge.p0_ns + 2_000_000_000))
        pipe.receive(deadline_ns=started + 180_000_000_000)
        _bootstrap_dependencies(bindings)

        def exchange(kind, fields):
            pipe.send(kind, fields, deadline_ns=started + 180_000_000_000)
            if kind == "probe_request":
                result, _ = pipe.receive(deadline_ns=started + 180_000_000_000)
                return result

        guard = CompilerProbeGuard(bindings.to_dict(), exchange, clock)
        guard.install()
        # This is the only production model construction path.
        from fly_connectome_sim.engine import FlyEngine
        from fly_connectome_sim.experiment.cell_activity import build_header
        engine = FlyEngine.from_prepared_graph()
        guard.verify_cache()
        identity = _initial_identity(engine, bindings)
        header = build_header(identity, bindings.runtime_root)
        protocol.validate_header(header, bindings=bindings)
        worker = _Worker(engine, header, clock, pipe.send, pipe.receive,
                         wall_deadline_ns=hello.wall_deadline_ns if profile.live else started + protocol.limits()["wall_ns"], profile=profile)
        worker.configure()
        pipe.send("static_header", dict(header=header), deadline_ns=started + 180_000_000_000)
        pipe.send("ready", dict(bindings_sha256=hello.bindings_sha256,
                                header_sha256=protocol.canonical_sha256(header), engine_identity_sha256=identity["sha256"],
                                build_sha256=protocol.canonical_sha256(identity["model_provenance"]["build"]),
                                graph_nodes=166700, graph_edges=25582938, observation_index=0, model_tick=0,
                                ready_ns=_now(clock)), deadline_ns=started + 180_000_000_000)
        worker.run()
        return 0
    except BaseException:
        # A partial call is never retried or rewritten as a completed observation.
        return 1
    finally:
        try:
            if guard is not None:
                guard.close()
        finally:
            if profile_scope is not None:
                profile_scope.__exit__(None, None, None)


if __name__ == "__main__":
    raise SystemExit(main())
