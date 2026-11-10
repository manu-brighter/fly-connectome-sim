"""Private diagnostic with explicit probe-only or zero-observation startup mode."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


class BoundedTrace:
    def __init__(self, path):
        self.fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.bytes = self.records = 0

    def record(self, phase, **fields):
        raw = (json.dumps(dict(phase=phase, wall_ns=time.perf_counter_ns(), **fields),
            sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if self.records >= 64 or len(raw) > 1024 or self.bytes + len(raw) > 32768:
            raise ValueError("trace_budget")
        if os.write(self.fd, raw) != len(raw):
            raise OSError("trace_write")
        os.fsync(self.fd)
        self.bytes += len(raw)
        self.records += 1

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", required=True, type=Path)
    args = parser.parse_args()
    watchdog = threading.Timer(30, lambda: os._exit(97))
    watchdog.daemon = True
    watchdog.start()
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root))
    from market import native_protocol as p, native_windows as w
    from market.native_worker import _Pipe, _initial_identity
    from market.price_service import SystemClock

    trace = BoundedTrace(args.controls.parent / "child-phases.jsonl")
    guard = pipe = None
    scope = None
    try:
        trace.record("child_enter")
        raw = p._bounded_file(args.controls, 2097152)
        control = p.parse_json(raw, byte_limit=2097152, node_limit=40000)
        mode = control["mode"]
        if mode not in ("probe-only", "startup-context"):
            raise p.ProtocolError()
        if control["fixture_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
            raise p.ProtocolError("source")
        profile = p.from_declaration(control["protocol"])
        scope = p.scope(profile)
        scope.__enter__()
        declaration = p.validate_protocol(control["protocol"])
        bindings = p.validate_bindings(control["bindings"], declaration)
        clock = SystemClock()
        deadline = control["deadline_ns"]
        if not time.perf_counter_ns() < deadline <= time.perf_counter_ns() + 30_000_000_000:
            raise p.ProtocolError("deadline")
        trace.record("source_verify_enter")
        w.compare_bound_files(bindings, deadline_ns=min(deadline, time.perf_counter_ns() + 5_000_000_000))
        trace.record("source_verify_return")

        class TracedPipe(_Pipe):
            def send(self, kind, fields, binary=b"", *, deadline_ns):
                trace.record("pipe_send_enter", message_type=kind)
                result = super().send(kind, fields, binary, deadline_ns=deadline_ns)
                trace.record("pipe_send_return", message_type=kind)
                return result

            def receive(self, *, deadline_ns, max_body=4096):
                trace.record("pipe_receive_enter")
                result = super().receive(deadline_ns=deadline_ns, max_body=max_body)
                trace.record("pipe_receive_return", message_type=result[0].type)
                return result

        pipe = TracedPipe(bindings, clock)
        hello, _ = pipe.receive(deadline_ns=deadline)
        held = w.PRIMITIVES.WindowsProcess(os.getpid())
        try:
            identity = held.identity()
            identity["executable_sha256"] = bindings.files.worker_exe.sha256
        finally:
            held.close()
        pipe.send("hello", dict(bindings_sha256=hello.bindings_sha256,
            worker=identity, worker_clock=clock.describe()), deadline_ns=deadline)
        for _ in range(3):
            challenge, _ = pipe.receive(deadline_ns=deadline)
            pipe.send("clock", dict(challenge_index=challenge.challenge_index,
                p0_ns=challenge.p0_ns, child_ns=time.perf_counter_ns()),
                deadline_ns=min(deadline, challenge.p0_ns + 2_000_000_000))
        initialize, _ = pipe.receive(deadline_ns=deadline)
        if initialize.type != "initialize":
            raise p.ProtocolError()
        if mode == "startup-context":
            from market.native_worker import _bootstrap_dependencies
            trace.record("dependency_bootstrap_enter")
            _bootstrap_dependencies(bindings)
            trace.record("dependency_bootstrap_return")

        original_digest = w._executable_digest
        def traced_digest(path):
            trace.record("executable_digest_enter")
            digest = original_digest(path)
            trace.record("executable_digest_return", sha256=digest)
            return digest
        w._executable_digest = traced_digest

        class HeldProbe:
            def __init__(self, process):
                self.process = process

            def __getattr__(self, name):
                return getattr(self.process, name)

            def identity(self):
                trace.record("held_identity_enter")
                result = self.process.identity()
                trace.record("held_identity_return", pid=result["pid"])
                return result

        class TracedGuard(w.CompilerProbeGuard):
            def verify_cache(self):
                trace.record("cache_verify_enter")
                result = super().verify_cache()
                trace.record("cache_verify_return")
                return result

            def _launch(self, *values):
                trace.record("create_process_enter")
                result = super()._launch(*values)
                trace.record("create_process_return", pid=self.process.pid)
                self.process = HeldProbe(self.process)
                return result

        def exchange(kind, fields):
            pipe.send(kind, fields, deadline_ns=deadline)
            if kind == "probe_request":
                value, _ = pipe.receive(deadline_ns=deadline)
                trace.record("permission_consumed", allowed_ns=value.allowed_ns)
                return value

        guard = TracedGuard(bindings.to_dict(), exchange, clock)
        guard.install()
        if mode == "startup-context":
            trace.record("engine_import_enter")
            from fly_connectome_sim.engine import FlyEngine
            trace.record("engine_import_return")
            trace.record("engine_construct_enter")
            engine = FlyEngine.from_prepared_graph()
            trace.record("engine_construct_return")
            guard.verify_cache()
            trace.record("engine_identity_enter")
            identity = _initial_identity(engine, bindings)
            trace.record("engine_identity_return", sha256=identity["sha256"])
        else:
            subprocess.run(list(bindings.compiler_probe.argv), check=True, capture_output=True, text=True)
        stop, _ = pipe.receive(deadline_ns=deadline)
        if stop.type != "stop":
            raise p.ProtocolError()
        pipe.send("ended", dict(reason="cancelled", observations_completed=0,
            last_observation_index=None, last_tick=0, wall_ns=time.perf_counter_ns(),
            header_sha256=None, engine_identity_sha256=None, fault=None), deadline_ns=deadline)
        trace.record("diagnostic_complete")
        return 0
    except BaseException as error:
        trace.record("diagnostic_failed", code=getattr(error, "code", "worker_failed"))
        return 1
    finally:
        try:
            if guard is not None:
                guard.close()
            trace.record("guard_closed")
        finally:
            if scope is not None:
                scope.__exit__(None, None, None)
            trace.close()
            watchdog.cancel()


if __name__ == "__main__":
    raise SystemExit(main())
