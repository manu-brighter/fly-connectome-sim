"""Exact-handle Windows transport for the bounded native application worker.

The Job commit quota is an OS limit. RSS/disk observations are sampled stop
thresholds. This owner never imports the simulator or builds a native library.
"""

import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import importlib
import os
from pathlib import Path
import queue
import struct
import subprocess
import sys
import threading
import time

from . import native_protocol as protocol
from .price_service import SystemClock


ROOT = Path(__file__).absolute().parents[1]
RUNTIME_KEYS = frozenset(("graph", "normalized_neurons", "annotations", "neurotransmitters", "edges"))


class NativeTransportError(ValueError):
    def __init__(self, code):
        if code not in protocol.FAULTS:
            raise ValueError("unknown native fault")
        self.code = code
        super().__init__(code)


def _primitives():
    scripts = ROOT / "scripts"
    for name in ("market_artifacts", "market_supervision"):
        module = sys.modules.get(name)
        if module is not None and Path(getattr(module, "__file__", "")).resolve() != scripts / (name + ".py"):
            raise NativeTransportError("ownership")
    sys.path.insert(0, str(scripts))
    try:
        module = importlib.import_module("market_supervision")
        for name in ("market_artifacts", "market_supervision"):
            if Path(sys.modules[name].__file__).resolve() != scripts / (name + ".py"):
                raise NativeTransportError("ownership")
        return module
    finally:
        del sys.path[0]


PRIMITIVES = _primitives()


if sys.platform == "win32":
    # Private function objects; the frozen supervision signatures stay untouched.
    API = ct.WinDLL("kernel32", use_last_error=True)

    class SECURITY_ATTRIBUTES(ct.Structure):
        _fields_ = [("length", wt.DWORD), ("descriptor", ct.c_void_p), ("inherit", wt.BOOL)]

    class STARTUPINFOEX(ct.Structure):
        _fields_ = [("StartupInfo", PRIMITIVES.STARTUPINFO), ("lpAttributeList", ct.c_void_p)]

    class JOB_MEMORY_USAGE(ct.Structure):
        _fields_ = [("JobMemory", ct.c_uint64), ("PeakJobMemoryUsed", ct.c_uint64)]

    for name, args, result in (
        ("InitializeProcThreadAttributeList", [ct.c_void_p, wt.DWORD, wt.DWORD, ct.POINTER(ct.c_size_t)], wt.BOOL),
        ("UpdateProcThreadAttribute", [ct.c_void_p, wt.DWORD, ct.c_size_t, ct.c_void_p, ct.c_size_t, ct.c_void_p, ct.c_void_p], wt.BOOL),
        ("DeleteProcThreadAttributeList", [ct.c_void_p], None),
        ("CreatePipe", [ct.POINTER(wt.HANDLE), ct.POINTER(wt.HANDLE), ct.POINTER(SECURITY_ATTRIBUTES), wt.DWORD], wt.BOOL),
        ("SetHandleInformation", [wt.HANDLE, wt.DWORD, wt.DWORD], wt.BOOL),
        ("PeekNamedPipe", [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.c_void_p, ct.POINTER(wt.DWORD), ct.c_void_p], wt.BOOL),
        ("ReadFile", [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD), ct.c_void_p], wt.BOOL),
        ("WriteFile", [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD), ct.c_void_p], wt.BOOL),
        ("OpenThread", [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
        ("CancelSynchronousIo", [wt.HANDLE], wt.BOOL),
        ("CreateProcessW", [wt.LPCWSTR, wt.LPWSTR, ct.c_void_p, ct.c_void_p, wt.BOOL, wt.DWORD,
                            ct.c_void_p, wt.LPCWSTR, ct.POINTER(STARTUPINFOEX), ct.POINTER(PRIMITIVES.PROCESS_INFORMATION)], wt.BOOL),
        ("SetInformationJobObject", [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD], wt.BOOL),
        ("QueryInformationJobObject", [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.c_void_p], wt.BOOL),
        ("TerminateJobObject", [wt.HANDLE, wt.UINT], wt.BOOL),
    ):
        function = getattr(API, name)
        function.argtypes, function.restype = args, result


def _check(value):
    if not value:
        raise ct.WinError(ct.get_last_error())
    return value


def _terminate_held(process, *, deadline_ns=None):
    if deadline_ns is not None and time.perf_counter_ns() >= deadline_ns:
        raise NativeTransportError("deadline")
    if process.exited():
        return
    if not PRIMITIVES.K.TerminateProcess(process.handle, 1):
        error = ct.get_last_error()
        # Concurrent Job termination can make TerminateProcess return access
        # denied before the already-terminating process handle signals exit.
        wait_ms = 1000 if deadline_ns is None else min(1000, max(0, (deadline_ns - time.perf_counter_ns()) // 1_000_000))
        result = PRIMITIVES.K.WaitForSingleObject(process.handle, wait_ms)
        if deadline_ns is not None and (time.perf_counter_ns() >= deadline_ns or (result == 258 and wait_ms < 1000)):
            raise NativeTransportError("deadline")
        if result != 0:
            raise ct.WinError(error)


def _ordinary(path):
    path = Path(path)
    if not path.is_absolute() or str(path).startswith("\\\\"):
        raise NativeTransportError("ownership")
    for part in (path, *path.parents):
        stat = part.lstat()
        if part.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            raise NativeTransportError("ownership")
    return path


def _executable_digest(path):
    path = _ordinary(path)
    identity = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    before = path.stat()
    if before.st_size > 536870912:
        raise NativeTransportError("source")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        if identity(os.fstat(handle.fileno())) != identity(before):
            raise NativeTransportError("source")
        remaining = before.st_size
        while remaining:
            chunk = handle.read(min(1048576, remaining))
            if not chunk:
                raise NativeTransportError("source")
            digest.update(chunk)
            remaining -= len(chunk)
        if handle.read(1) or identity(os.fstat(handle.fileno())) != identity(before):
            raise NativeTransportError("source")
    if identity(path.stat()) != identity(before):
        raise NativeTransportError("source")
    return digest.hexdigest()


def compare_bound_files(bindings, *, deadline_ns):
    """Recheck declared non-runtime sources/tools without constructing arrays."""
    for key, binding in bindings["files"].items():
        if key in RUNTIME_KEYS:
            continue
        path = _ordinary(binding["path"])
        before = path.stat()
        expected = (binding["device"], binding["file_id"], binding["bytes"], binding["mtime_ns"])
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        if identity(before) != expected:
            raise NativeTransportError("source")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            if identity(os.fstat(handle.fileno())) != expected:
                raise NativeTransportError("source")
            remaining = binding["bytes"]
            while remaining:
                if time.perf_counter_ns() >= deadline_ns:
                    raise NativeTransportError("deadline")
                chunk = handle.read(min(1048576, remaining))
                if not chunk:
                    raise NativeTransportError("source")
                digest.update(chunk)
                remaining -= len(chunk)
            if handle.read(1) or identity(os.fstat(handle.fileno())) != expected:
                raise NativeTransportError("source")
        if identity(path.stat()) != expected or digest.hexdigest() != binding["sha256"]:
            raise NativeTransportError("source")


class _RootLock:
    def __init__(self, root):
        import msvcrt
        self.handle = open(root / "native.owner.lock", "a+b")
        try:
            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        except BaseException:
            self.handle.close()
            self.handle = None
            raise

    def close(self):
        if self.handle is not None:
            # Windows releases the byte-range lock on handle closure. Do not
            # unlock first: a failed file close must retain root ownership.
            self.handle.close()
            self.handle = None


class OwnedNativeChild:
    """One attempted fixed worker launch, private pipes, bounded sampled evidence.

    The caller owns event/D1 persistence and passes a common absolute exchange
    deadline for ordinal7 observation+complete+ACK. send() checks monitor faults;
    no ACK is generated here. finish_close() does not publish a success seal.
    """

    def __init__(self, bindings, clock=None):
        self.bindings = protocol.FrozenRecord(bindings)
        self.clock = clock or SystemClock()
        self.work_root = Path(bindings["work_root"])
        self.decoder_work_root = Path(bindings["decoder_work_root"])
        self.identity = None
        self.process = self.job = self.thread = self.root_lock = None
        self.command = None
        self.commit_limit_bytes = None
        self.resumed_ns = None
        self.fault = None
        self._attempted = self._created = self._drained = False
        self._stopped = threading.Event()
        self._monitor_stop = threading.Event()
        self._writer_stop = threading.Event()
        self._monitor_thread = self._writer_thread = self._write_thread = None
        self._monitor_file = None
        self._outbox = queue.Queue(maxsize=32)
        self._last_monitor = None
        self._monitor_count = self._monitor_bytes = 0
        self._read_pipe = self._write_pipe = self._stderr_pipe = None
        self._child_streams = []
        self._stderr = bytearray()
        self._read_buffer = bytearray()
        self._read_started_ns = None
        self._send_seq = self._receive_seq = 0
        self._nonce = None
        self._last_clock = None
        self._cleanup_requested_ns = None
        self._cleanup_real_deadline = None
        self._receipt = None
        self._write_lock = threading.Lock()
        self._sample_lock = threading.Lock()
        self._clock_lock = threading.Lock()
        self._io_error = None
        self._test = False
        self.probe = None
        self.probe_identity = None
        self._probe_allowed_ns = None
        self._probe_finished = False
        self._probe_peak = 0
        self._worker_exit_code = self._probe_exit_code = None
        self._stdout_eof = False

    def _now(self):
        with self._clock_lock:
            value = self.clock.sample().monotonic_ns
            if type(value) is not int or not 0 <= value <= protocol.MAX_NS or (self._last_clock is not None and value < self._last_clock):
                self._latch("clock")
                raise NativeTransportError("clock")
            self._last_clock = value
            return value

    def _latch(self, code):
        if self.fault is None:
            self.fault = code
        self._stopped.set()

    def _require_live(self, deadline_ns):
        if self.fault is not None:
            raise NativeTransportError(self.fault)
        if self._stopped.is_set():
            raise NativeTransportError("worker_outcome_unknown")
        if self._now() >= deadline_ns:
            self._latch("deadline")
            raise NativeTransportError("deadline")

    def start(self):
        bindings = self.bindings
        executable = bindings.files.worker_exe.path
        command = [executable, "-B", "-s", "-S", "-m", "market.native_worker", "--protocol",
                   str(self.work_root / "protocol.json"), "--bindings", str(self.work_root / "bindings.json")]
        compare_bound_files(bindings, deadline_ns=self._now() + 120_000_000_000)
        self._start(command, bindings.environment.to_dict(), Path(bindings.project_root))

    def _start_test(self, fixture, mode):
        # Private, explicit fixture-only seam: never sourced from CLI/env/HTTP.
        fixture = Path(fixture).resolve()
        allowed = ROOT / "tests/market/fixtures"
        if fixture.parent != allowed or fixture.suffix != ".py" or not fixture.is_file():
            raise NativeTransportError("ownership")
        current = PRIMITIVES.WindowsProcess(os.getpid())
        try:
            executable = current.identity()["executable"]
        finally:
            current.close()
        environment = {name: os.environ[name] for name in ("SystemRoot", "WINDIR") if name in os.environ}
        environment.update(TMP=str(self.work_root), TEMP=str(self.work_root))
        self._test = True
        self._start([executable, "-I", "-S", "-B", str(fixture), mode], environment, self.work_root)

    def _start(self, command, environment, cwd):
        if self._attempted or sys.platform != "win32":
            raise NativeTransportError("startup")
        self._attempted = True
        self.command = tuple(command)
        try:
            _ordinary(self.work_root)
            _ordinary(cwd)
            self.root_lock = _RootLock(self.work_root)
            self.job = PRIMITIVES.WindowsJob()
            limits = PRIMITIVES.EXTENDED_LIMIT()
            _check(API.QueryInformationJobObject(self.job.handle, 9, ct.byref(limits), ct.sizeof(limits), None))
            limits.BasicLimitInformation.LimitFlags |= 0x200
            limits.JobMemoryLimit = 4294967296
            _check(API.SetInformationJobObject(self.job.handle, 9, ct.byref(limits), ct.sizeof(limits)))
            _check(API.QueryInformationJobObject(self.job.handle, 9, ct.byref(limits), ct.sizeof(limits), None))
            if limits.JobMemoryLimit != 4294967296 or limits.BasicLimitInformation.LimitFlags != 0x2200:
                raise NativeTransportError("ownership")
            self.commit_limit_bytes = limits.JobMemoryLimit
            self._launch(command, environment, cwd)
            self._close_child_streams()
            self._verify(command[0])
            self._monitor_file = open(self.work_root / "monitor.bin", "xb", buffering=0)
            self._writer_thread = threading.Thread(target=self._write_monitors, name="native-monitor-writer", daemon=True)
            self._writer_thread.start()
            self._sample()
            self._monitor_thread = threading.Thread(target=self._monitor, name="native-monitor", daemon=True)
            self._monitor_thread.start()
            self.resumed_ns = self._now()
            if PRIMITIVES.K.ResumeThread(self.thread) == 0xFFFFFFFF:
                raise ct.WinError(ct.get_last_error())
            _check(PRIMITIVES.K.CloseHandle(self.thread))
            self.thread = None
        except Exception as error:
            code = error.code if isinstance(error, NativeTransportError) else "ownership"
            self._latch(code)
            raise NativeTransportError(code) from None

    def _pipe(self, parent_reads):
        security = SECURITY_ATTRIBUTES(ct.sizeof(SECURITY_ATTRIBUTES), None, True)
        read, write = wt.HANDLE(), wt.HANDLE()
        _check(API.CreatePipe(ct.byref(read), ct.byref(write), ct.byref(security), 4096))
        parent, child = (read.value, write.value) if parent_reads else (write.value, read.value)
        self._child_streams.append(child)
        # Track the parent before a possibly failing flag operation.
        return parent, child

    def _launch(self, command, environment, cwd):
        self._write_pipe, child_input = self._pipe(False)
        self._read_pipe, child_output = self._pipe(True)
        self._stderr_pipe, child_error = self._pipe(True)
        for handle in (self._write_pipe, self._read_pipe, self._stderr_pipe):
            _check(API.SetHandleInformation(handle, 1, 0))
        startup = STARTUPINFOEX()
        startup.StartupInfo.cb = ct.sizeof(startup)
        startup.StartupInfo.dwFlags, startup.StartupInfo.wShowWindow = 0x101, 0
        startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = child_input, child_output, child_error
        size = ct.c_size_t()
        count = 2 if self.job is not None else 1
        API.InitializeProcThreadAttributeList(None, count, 0, ct.byref(size))
        if not size.value:
            raise ct.WinError(ct.get_last_error())
        attributes = ct.create_string_buffer(size.value)
        startup.lpAttributeList = ct.cast(attributes, ct.c_void_p)
        _check(API.InitializeProcThreadAttributeList(startup.lpAttributeList, count, 0, ct.byref(size)))
        handles = (wt.HANDLE * 3)(*self._child_streams)
        try:
            if self.job is not None:
                jobs = (wt.HANDLE * 1)(self.job.handle)
                _check(API.UpdateProcThreadAttribute(startup.lpAttributeList, 0, 0x0002000D, jobs, ct.sizeof(jobs), None, None))
            _check(API.UpdateProcThreadAttribute(startup.lpAttributeList, 0, 0x00020002, handles, ct.sizeof(handles), None, None))
            block = ct.create_unicode_buffer("\0".join(f"{key}={value}" for key, value in sorted(environment.items())) + "\0\0")
            information = PRIMITIVES.PROCESS_INFORMATION()
            _check(API.CreateProcessW(command[0], ct.create_unicode_buffer(subprocess.list2cmdline(command)),
                                     None, None, True, 0x00000008 | 0x00000004 | 0x00000400 | 0x00080000,
                                     block, str(cwd), ct.byref(startup), ct.byref(information)))
            self._created = True
            self.thread = information.hThread
            self.process = PRIMITIVES.WindowsProcess(information.dwProcessId, information.hProcess)
        finally:
            API.DeleteProcThreadAttributeList(startup.lpAttributeList)

    def _verify(self, executable):
        identity = self.process.identity()
        inside = wt.BOOL()
        _check(PRIMITIVES.K.IsProcessInJob(self.process.handle, self.job.handle, ct.byref(inside)))
        if (Path(identity["executable"]) != Path(executable) or identity["creation_time_100ns"] <= 0
                or not inside.value or (not self.process.exited() and self.job.pids() != [self.process.pid])):
            raise NativeTransportError("ownership")
        identity["executable_sha256"] = _executable_digest(executable)
        if not self._test and identity["executable_sha256"] != self.bindings.files.worker_exe.sha256:
            raise NativeTransportError("source")
        self.identity = protocol.FrozenRecord(identity)

    def _close_child_streams(self):
        for handle in tuple(self._child_streams):
            _check(PRIMITIVES.K.CloseHandle(handle))
            self._child_streams.remove(handle)

    def _read(self, handle, limit):
        available = wt.DWORD()
        if not API.PeekNamedPipe(handle, None, 0, None, ct.byref(available), None):
            if ct.get_last_error() == 109:
                return b"", True
            raise ct.WinError(ct.get_last_error())
        if not available.value:
            return b"", False
        size = min(available.value, limit, 65536)
        buffer, count = ct.create_string_buffer(size), wt.DWORD()
        _check(API.ReadFile(handle, buffer, size, ct.byref(count), None))
        return buffer.raw[:count.value], False

    def _drain_stderr(self):
        if self._stderr_pipe is None:
            return
        remaining = 65536 - len(self._stderr)
        block, _ = self._read(self._stderr_pipe, min(4096, remaining + 1))
        self._stderr.extend(block[:remaining])
        if len(block) > remaining:
            self._latch("resource")

    def receive(self, *, deadline_ns, max_body=2097152):
        if type(max_body) is not int or not 5 <= max_body <= 2097152:
            raise NativeTransportError("protocol")
        try:
            while True:
                self._require_live(deadline_ns)
                if self._read_started_ns is not None:
                    self._require_live(min(deadline_ns, self._read_started_ns + 5_000_000_000))
                needed = 4 - len(self._read_buffer)
                if len(self._read_buffer) >= 4:
                    length = struct.unpack("<I", self._read_buffer[:4])[0]
                    if not 5 <= length <= max_body:
                        raise NativeTransportError("protocol")
                    needed = 4 + length - len(self._read_buffer)
                    if needed == 0:
                        frame = protocol.decode_frame(bytes(self._read_buffer), "worker")
                        self._check_envelope(frame.message)
                        if frame.message.seq != self._receive_seq:
                            raise NativeTransportError("protocol")
                        self._receive_seq += 1
                        self._read_buffer.clear()
                        self._read_started_ns = None
                        return frame
                block, eof = self._read(self._read_pipe, needed)
                if block:
                    if not self._read_buffer:
                        self._read_started_ns = self._now()
                    self._read_buffer.extend(block)
                elif eof:
                    if self._read_buffer:
                        raise NativeTransportError("protocol")
                    self._stdout_eof = True
                    # Pipe EOF can precede process-handle signalling. Keep the
                    # finite read epoch until the exact exit code is queryable.
                    if not self.process.exited():
                        if self._read_started_ns is None:
                            self._read_started_ns = self._now()
                        time.sleep(0.005)
                        continue
                    if self.process.exit_code() != 0:
                        raise NativeTransportError("worker_failed")
                    self._read_started_ns = None
                    return None
                else:
                    time.sleep(0.005)
        except Exception as error:
            code = error.code if isinstance(error, (NativeTransportError, protocol.ProtocolError)) else "ownership"
            self._latch(code)
            raise NativeTransportError(code) from None

    def send(self, message, binary=b"", *, deadline_ns=None):
        self._check_envelope(message)
        if message["seq"] != self._send_seq:
            self._latch("protocol")
            raise NativeTransportError("protocol")
        raw = protocol.encode_frame(message, binary, direction="parent")
        self._write(raw, deadline_ns if deadline_ns is not None else self._now() + 5_000_000_000)
        self._send_seq += 1

    def _check_envelope(self, message):
        if (any(message[key] != self.bindings[key] for key in ("incarnation", "worker_session", "protocol_sha256"))
                or (self._nonce is not None and message["launch_nonce"] != self._nonce)):
            self._latch("protocol")
            raise NativeTransportError("protocol")
        if self._nonce is None:
            self._nonce = message["launch_nonce"]

    def _write(self, raw, deadline_ns):
        with self._write_lock:
            deadline_ns = min(deadline_ns, self._now() + 5_000_000_000)
            self._require_live(deadline_ns)
            self._io_error = None
            def write():
                try:
                    for offset in range(0, len(raw), 4096):
                        chunk = raw[offset:offset + 4096]
                        count = wt.DWORD()
                        _check(API.WriteFile(self._write_pipe, chunk, len(chunk), ct.byref(count), None))
                        if count.value != len(chunk):
                            raise OSError("partial pipe write")
                except Exception as error:
                    self._io_error = error
            self._write_thread = threading.Thread(target=write, name="native-pipe-write", daemon=True)
            self._write_thread.start()
            try:
                while self._write_thread.is_alive():
                    self._require_live(deadline_ns)
                    self._write_thread.join(0.005)
                self._require_live(deadline_ns)
                if self._io_error is not None:
                    self._latch("worker_failed")
                    raise NativeTransportError("worker_failed")
            except NativeTransportError:
                self._cancel_write()
                raise

    def _cancel_write(self):
        if self._write_thread is not None and self._write_thread.is_alive():
            handle = _check(API.OpenThread(0x0001, False, self._write_thread.native_id))
            try:
                # ERROR_NOT_FOUND means no synchronous IO was pending at that instant.
                if not API.CancelSynchronousIo(handle) and ct.get_last_error() != 1168:
                    raise ct.WinError(ct.get_last_error())
            finally:
                _check(PRIMITIVES.K.CloseHandle(handle))

    def _disk_usage(self):
        def total(root):
            if not root.exists():
                return 0
            _ordinary(root)
            count = 0
            for directory, dirs, files in os.walk(root, followlinks=False):
                for name in (*dirs, *files):
                    path = _ordinary(Path(directory) / name)
                    if path.is_file():
                        count += path.stat().st_size
            return count
        evidence = sum(path.stat().st_size for path in self.work_root.iterdir() if path.name in
                       ("protocol.json", "bindings.json", "header.json", "events.bin", "monitor.bin", "cleanup.json", "final.json", "failure.json"))
        return total(self.work_root) + (0 if self.decoder_work_root.is_relative_to(self.work_root) else total(self.decoder_work_root)), evidence

    def _sample(self):
        with self._sample_lock:
            if self.identity is None:
                return
            now = self._now()
            previous = self._last_monitor
            gap = 0 if previous is None else now - previous.sample_ns
            if self._monitor_count >= 12000:
                self._latch("resource")
                raise NativeTransportError("resource")
            creation, end, kernel, user = (ct.c_uint64() for _ in range(4))
            _check(PRIMITIVES.K.GetProcessTimes(self.process.handle, ct.byref(creation), ct.byref(end), ct.byref(kernel), ct.byref(user)))
            if creation.value != self.identity.creation_time_100ns:
                self._latch("ownership")
                raise NativeTransportError("ownership")
            exited = self.process.exited()
            rss, os_peak = self._memory(self.process)
            pids = self.job.pids()
            memory = JOB_MEMORY_USAGE()
            _check(API.QueryInformationJobObject(self.job.handle, 28, ct.byref(memory), ct.sizeof(memory), None))
            combined, evidence = self._disk_usage()
            current = 0 if exited else rss
            peak = max(os_peak, previous.worker_peak_rss_bytes if previous else 0)
            if gap >= 2_000_000_000:
                self._latch("deadline")
            if len(pids) > 2:
                self._latch("ownership")
                raise NativeTransportError("ownership")
            for pid in pids:
                if pid != self.process.pid:
                    try:
                        self._capture_probe(pid)
                    except Exception:
                        self._latch("ownership")
                        raise NativeTransportError("ownership") from None
            probe_rss = 0
            probe_identity = None
            if self.probe is not None:
                probe_rss, probe_peak = self._memory(self.probe)
                self._probe_peak = max(self._probe_peak, probe_peak)
                if self.probe.exited():
                    probe_rss = 0
                else:
                    probe_identity = self.probe_identity
            if current + probe_rss > 4294967296 or memory.PeakJobMemoryUsed > 4294967296 or combined > 268435456 or evidence > 67108864:
                self._latch("resource")
            fields = dict(schema="market-native-monitor/v1", sequence=self._monitor_count,
                          previous_sha256=protocol.ZERO_SHA256 if previous is None else previous.sha256,
                          sample_ns=now, worker_pid=self.identity.pid,
                          worker_creation_time_100ns=self.identity.creation_time_100ns,
                          worker_rss_bytes=current, worker_peak_rss_bytes=peak,
                          probe_pid=None if probe_identity is None else probe_identity.pid,
                          probe_creation_time_100ns=None if probe_identity is None else probe_identity.creation_time_100ns,
                          probe_rss_bytes=probe_rss, probe_peak_rss_bytes=self._probe_peak,
                          job_process_count=len(pids), job_commit_bytes=memory.JobMemory,
                          job_peak_commit_bytes=max(memory.PeakJobMemoryUsed, previous.job_peak_commit_bytes if previous else 0), combined_output_bytes=combined,
                          evidence_bytes=evidence, gap_ns=gap, fault=self.fault)
            row = protocol.make_monitor(fields)
            raw = protocol.encode_monitor(row)
            if self._monitor_bytes + len(raw) > 25165824:
                self._latch("resource")
                raise NativeTransportError("resource")
            try:
                self._outbox.put_nowait(raw)
            except queue.Full:
                self._latch("storage")
                raise NativeTransportError("storage") from None
            self._last_monitor = row
            self._monitor_count += 1
            self._monitor_bytes += len(raw)

    def _memory(self, process):
        counters = PRIMITIVES.MEMORY_COUNTERS()
        counters.cb = ct.sizeof(counters)
        _check(PRIMITIVES.K.K32GetProcessMemoryInfo(process.handle, ct.byref(counters), ct.sizeof(counters)))
        return counters.WorkingSetSize, counters.PeakWorkingSetSize

    def permit_probe(self, request):
        """Exactly one source-bound request; returns probe_allow.allowed_ns."""
        binding = self.bindings.compiler_probe
        if (self._probe_allowed_ns is not None or request.type != "probe_request"
                or request.compiler_sha256 != binding.executable_sha256
                or request.argv_sha256 != protocol.canonical_sha256(binding.argv)
                or request.environment_sha256 != binding.environment_sha256):
            self._latch("ownership")
            raise NativeTransportError("ownership")
        compare_bound_files(self.bindings, deadline_ns=self._now() + 5_000_000_000)
        self._probe_allowed_ns = self._now()
        return self._probe_allowed_ns

    def _capture_probe(self, pid):
        binding = self.bindings.compiler_probe
        if self._probe_allowed_ns is None or self._probe_finished or self._now() >= self._probe_allowed_ns + 5_000_000_000:
            raise NativeTransportError("ownership")
        if self.probe is None:
            # Only a current member of this held Job in its one permitted
            # interval may be opened by PID, once; retain that exact handle.
            if pid not in self.job.pids() or PRIMITIVES._parents().get(pid) != self.identity.pid:
                raise NativeTransportError("ownership")
            self.probe = PRIMITIVES.WindowsProcess(pid)
            identity = self.probe.identity()
            identity["executable_sha256"] = _executable_digest(identity["executable"])
            if (Path(identity["executable"]) != Path(binding.argv[0])
                    or identity["executable_sha256"] != binding.executable_sha256
                    or identity["creation_time_100ns"] < self.identity.creation_time_100ns):
                raise NativeTransportError("ownership")
            self.probe_identity = protocol.FrozenRecord(identity)
        if pid != self.probe.pid:
            raise NativeTransportError("ownership")

    def accept_probe_started(self, message):
        with self._sample_lock:
            if message.allowed_ns != self._probe_allowed_ns:
                raise NativeTransportError("ownership")
            self._capture_probe(message.process.pid)
            if message.process != self.probe_identity:
                raise NativeTransportError("ownership")

    def accept_probe_finished(self, message):
        with self._sample_lock:
            if (self.probe is None or self._probe_finished or message.process != self.probe_identity
                    or not self.probe.exited() or self.probe.exit_code() != 0
                    or self.probe.pid in self.job.pids()):
                self._latch("ownership")
                raise NativeTransportError("ownership")
            self._probe_peak = max(self._probe_peak, self._memory(self.probe)[1])
            self._probe_finished = True

    def _monitor(self):
        while not self._monitor_stop.wait(0.1):
            try:
                self._drain_stderr()
                self._sample()
                if self.fault is not None:
                    _check(PRIMITIVES.K.TerminateJobObject(self.job.handle, 1))
                    return
            except Exception as error:
                self._latch(error.code if isinstance(error, NativeTransportError) else "ownership")
                # A monitor fault is terminal even if the session consumer is
                # stalled. Only the already-held owned Job is terminated.
                PRIMITIVES.K.TerminateJobObject(self.job.handle, 1)
                return

    def _write_monitors(self):
        last_sync = time.perf_counter_ns()
        try:
            while not self._writer_stop.is_set() or not self._outbox.empty():
                try:
                    raw = self._outbox.get(timeout=0.05)
                except queue.Empty:
                    raw = None
                if raw is not None:
                    if self._monitor_file.write(raw) != len(raw):
                        raise OSError("partial monitor write")
                now = time.perf_counter_ns()
                if now - last_sync >= 1_000_000_000:
                    os.fsync(self._monitor_file.fileno())
                    last_sync = now
            os.fsync(self._monitor_file.fileno())
            self._monitor_file.close()
            self._monitor_file = None
        except Exception:
            self._latch("storage")

    def begin_stop(self, reason="shutdown"):
        if reason not in ("operator", "session_fault", "shutdown"):
            raise NativeTransportError("protocol")
        if self._cleanup_real_deadline is None:
            # An OS-wait budget remains finite on clock failure; this internal
            # watchdog is never substituted into evidence timestamps.
            self._cleanup_real_deadline = time.perf_counter_ns() + 25_000_000_000
            self._cleanup_requested_ns = self._cleanup_time()
        self._stopped.set()

    def _cleanup_time(self):
        try:
            return self._now()
        except NativeTransportError:
            return None

    def _remaining(self):
        return max(0, (self._cleanup_real_deadline - time.perf_counter_ns()) / 1e9)

    def confirm_exit(self):
        """Stop exact owned processes; retain handles/lock for caller final rehash.

        This is factual process closure, not evidence-file closure or a seal.
        One first-stop 25s budget also covers the later finish_close call.
        """
        self.begin_stop()
        self._cancel_write()
        if self._remaining() <= 0:
            raise NativeTransportError("deadline")
        if self.process is not None:
            if self._stdout_eof and not self.process.exited():
                PRIMITIVES.K.WaitForSingleObject(self.process.handle, min(5000, int(self._remaining() * 1000)))
            _terminate_held(self.process, deadline_ns=self._cleanup_real_deadline)
            if PRIMITIVES.K.WaitForSingleObject(self.process.handle, min(10000, int(self._remaining() * 1000))) != 0:
                raise NativeTransportError("cleanup_failed")
            self._worker_exit_code = self.process.exit_code()
        if self.job is not None:
            with self.job.lock:
                if self._remaining() <= 0:
                    raise NativeTransportError("deadline")
                self.job.stopping = True
                _check(API.TerminateJobObject(self.job.handle, 1))
            while True:
                if self._remaining() <= 0:
                    raise NativeTransportError("deadline")
                members = self.job.pids()
                if self._remaining() <= 0:
                    raise NativeTransportError("deadline")
                if not members:
                    break
                time.sleep(min(0.02, self._remaining()))
        if self.probe is not None and PRIMITIVES.K.WaitForSingleObject(self.probe.handle, min(1000, int(self._remaining() * 1000))) != 0:
            raise NativeTransportError("cleanup_failed")
        if self.probe is not None:
            self._probe_exit_code = self.probe.exit_code()
        if self._remaining() <= 0:
            raise NativeTransportError("deadline")
        return protocol.FrozenRecord(dict(worker_exit_confirmed=True,
                                         worker_exit_code=self._worker_exit_code,
                                         job_empty_confirmed=True))

    def finish_close(self, *, evidence_files_closed):
        if self._receipt is not None and self._receipt.outcome == "confirmed":
            return self._receipt
        self.begin_stop()
        requested = self._cleanup_requested_ns
        worker_exit = not self._created
        job_empty = self.job is None
        exit_code = self._worker_exit_code
        probe_exit_code = self._probe_exit_code
        cleanup_fault = None
        ipc_closed = process_closed = job_closed = root_closed = False
        evidence_closed = False
        try:
            proof = self.confirm_exit()
            worker_exit, exit_code, job_empty = proof.worker_exit_confirmed, proof.worker_exit_code, proof.job_empty_confirmed
            if self.probe is not None:
                probe_exit_code = self.probe.exit_code()
                if self.probe_identity is None:
                    # The normative schema has no anonymous-created probe
                    # variant. Do not fabricate a null/"none launched" receipt.
                    raise NativeTransportError("ownership")
            self._monitor_stop.set()
            if self._monitor_thread is not None:
                self._monitor_thread.join(min(1, self._remaining()))
                if self._monitor_thread.is_alive():
                    raise NativeTransportError("cleanup_failed")
            self._drain_stderr()
            if self.identity is not None and self._writer_thread is not None and self._monitor_file is not None:
                self._sample()
            self._writer_stop.set()
            if self._writer_thread is not None:
                self._writer_thread.join(min(2, self._remaining()))
                if self._writer_thread.is_alive() or self._monitor_file is not None:
                    raise NativeTransportError("cleanup_failed")
            evidence_closed = bool(evidence_files_closed)
            if not evidence_closed or (self._created and self.identity is None):
                raise NativeTransportError("cleanup_failed")
            if self._write_thread is not None:
                self._write_thread.join(min(1, self._remaining()))
                if self._write_thread.is_alive():
                    raise NativeTransportError("cleanup_failed")
            self._close_child_streams()
            for name in ("_read_pipe", "_write_pipe", "_stderr_pipe", "thread"):
                handle = getattr(self, name)
                if handle is not None:
                    _check(PRIMITIVES.K.CloseHandle(handle))
                    setattr(self, name, None)
            ipc_closed = True
            if self.process is not None:
                self.process.close()
                self.process = None
            if self.probe is not None:
                self.probe.close()
                self.probe = None
            process_closed = True
            if self.job is not None:
                self.job.close()
                self.job = None
            job_closed = True
            if self._remaining() <= 0:
                raise NativeTransportError("deadline")
            if self.root_lock is not None:
                self.root_lock.close()
            root_closed = True
        except Exception as error:
            cleanup_fault = error.code if isinstance(error, NativeTransportError) else "cleanup_failed"
        if self.probe is not None and self.probe_identity is None:
            raise NativeTransportError("cleanup_failed")
        creation = "verified" if self.identity is not None else "created_unverified" if self._created else "not_created"
        fields = dict(schema="market-native-cleanup/v1", incarnation=self.bindings.incarnation,
                      worker_session=self.bindings.worker_session, requested_ns=requested, finished_ns=self._cleanup_time(),
                      worker_creation=creation, worker=None if self.identity is None else self.identity.to_dict(),
                      probe=None if self.probe_identity is None else self.probe_identity.to_dict(),
                      worker_exit_code=exit_code, probe_exit_code=probe_exit_code,
                      worker_exit_confirmed=worker_exit,
                      probe_exit_confirmed=(self.probe_identity is None and self.probe is None) or probe_exit_code is not None,
                      job_empty_confirmed=job_empty,
                      ipc_handles_closed=ipc_closed, process_handles_closed=process_closed,
                      job_handle_closed=job_closed, root_lock_closed=root_closed, evidence_files_closed=evidence_closed,
                      first_fault=self.fault, cleanup_fault=cleanup_fault,
                      outcome="confirmed" if cleanup_fault is None else "unconfirmed")
        self._receipt = protocol.validate_cleanup(fields)
        return self._receipt



class CompilerProbeGuard:
    """Worker-only exact one-shot subprocess.run adapter; persistent audit fence.

    exchange(kind, fields) sends a wire payload; probe_request must return the
    validated probe_allow message. Keep this guard (and exact probe handle) alive
    until worker shutdown, so the parent can independently retain its own handle.
    """

    _pipe = OwnedNativeChild._pipe
    _launch = OwnedNativeChild._launch
    _read = OwnedNativeChild._read
    _close_child_streams = OwnedNativeChild._close_child_streams

    def __init__(self, bindings, exchange, clock=None, *, _test_argv=None):
        self.bindings = protocol.FrozenRecord(bindings)
        self.exchange = exchange
        self.clock = clock or SystemClock()
        self._command = tuple(self.bindings.compiler_probe.argv)
        if _test_argv is not None:
            fixture = Path(_test_argv[-2]).resolve()
            if (tuple(_test_argv) != self._command or fixture.parent != ROOT / "tests/market/fixtures"
                    or fixture.name != "native_probe_payload.py"):
                raise NativeTransportError("ownership")
        elif len(self._command) != 2 or self._command[1] != "version":
            raise NativeTransportError("ownership")
        self._test = _test_argv is not None
        self.job = self.process = self.thread = None
        self._read_pipe = self._write_pipe = self._stderr_pipe = None
        self._child_streams = []
        self._created = self._used = self._installed = False
        self._original_run = None
        self.identity = None

    def install(self):
        if self._installed:
            raise NativeTransportError("ownership")
        self._installed = True
        self._original_run = subprocess.run
        subprocess.run = self.run
        # This hook intentionally remains for the rest of the worker lifetime.
        # Source-bound worker code never starts a process through another path.
        def audit(event, args):
            if event in ("subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn", "os.exec", "os.startfile", "os.startfile/2", "os.fork", "os.forkpty"):
                raise NativeTransportError("ownership")
        sys.addaudithook(audit)

    def _now(self):
        value = self.clock.sample().monotonic_ns
        if type(value) is not int or not 0 <= value <= protocol.MAX_NS:
            raise NativeTransportError("clock")
        return value

    def verify_cache(self):
        compare_bound_files(self.bindings, deadline_ns=self._now() + 5_000_000_000)

    def run(self, args, **kwargs):
        if (self._used or type(args) not in (list, tuple) or tuple(args) != self._command
                or kwargs != dict(check=True, capture_output=True, text=True)):
            raise NativeTransportError("ownership")
        self._used = True
        self.verify_cache()
        binding = self.bindings.compiler_probe
        allowed = self.exchange("probe_request", dict(compiler_sha256=binding.executable_sha256,
                                argv_sha256=protocol.canonical_sha256(binding.argv),
                                environment_sha256=binding.environment_sha256))
        allowed_ns = allowed["allowed_ns"]
        self.verify_cache()
        environment = self.bindings.get("environment")
        environment = environment.to_dict() if environment is not None else {
            name: os.environ[name] for name in ("SystemRoot", "WINDIR", "TMP", "TEMP") if name in os.environ}
        if not self._test and protocol.canonical_sha256(environment) != binding.environment_sha256:
            raise NativeTransportError("source")
        try:
            self._launch(self._command, environment, Path(self.bindings.project_root))
            self._close_child_streams()
            identity = self.process.identity()
            identity["executable_sha256"] = _executable_digest(identity["executable"])
            inside = wt.BOOL()
            _check(PRIMITIVES.K.IsProcessInJob(self.process.handle, None, ct.byref(inside)))
            if (not inside.value or Path(identity["executable"]) != Path(self._command[0])
                    or identity["executable_sha256"] != binding.executable_sha256):
                raise NativeTransportError("ownership")
            self.identity = protocol.FrozenRecord(identity)
            started = self._now()
            if started < allowed_ns or started >= allowed_ns + 5_000_000_000:
                raise NativeTransportError("deadline")
            self.exchange("probe_started", dict(process=identity, allowed_ns=allowed_ns, started_ns=started))
            if PRIMITIVES.K.ResumeThread(self.thread) == 0xFFFFFFFF:
                raise ct.WinError(ct.get_last_error())
            _check(PRIMITIVES.K.CloseHandle(self.thread))
            self.thread = None
            stdout, stderr = bytearray(), bytearray()
            stdout_eof = stderr_eof = False
            while not (stdout_eof and stderr_eof and self.process.exited()):
                if self._now() >= started + 5_000_000_000:
                    raise NativeTransportError("deadline")
                for name, handle, output in (("stdout", self._read_pipe, stdout), ("stderr", self._stderr_pipe, stderr)):
                    block, eof = self._read(handle, 4097 - len(output))
                    output.extend(block)
                    if len(output) > 4096:
                        raise NativeTransportError("resource")
                    if name == "stdout":
                        stdout_eof = eof
                    else:
                        stderr_eof = eof
                time.sleep(0.002)
            completed = self._now()
            if self.process.exit_code() != 0 or bytes(stdout) not in (b"0.16.0\n", b"0.16.0\r\n") or stderr:
                raise NativeTransportError("startup")
            self.verify_cache()
            self.exchange("probe_finished", dict(process=identity, started_ns=started, completed_ns=completed,
                          exit_code=0, stdout_bytes=len(stdout), stderr_bytes=0,
                          stdout_sha256=hashlib.sha256(stdout).hexdigest(), stderr_sha256=hashlib.sha256(stderr).hexdigest(), version="0.16.0"))
            return subprocess.CompletedProcess(args, 0, stdout.decode("ascii"), "")
        except NativeTransportError:
            if self.process is not None and not self.process.exited():
                _terminate_held(self.process)
                PRIMITIVES.K.WaitForSingleObject(self.process.handle, 1000)
            raise
        except Exception:
            if self.process is not None and not self.process.exited():
                _terminate_held(self.process)
            raise NativeTransportError("ownership") from None

    def close(self):
        if self._original_run is not None:
            subprocess.run = self._original_run
        if self.process is not None:
            _terminate_held(self.process)
            if PRIMITIVES.K.WaitForSingleObject(self.process.handle, 1000) != 0:
                raise NativeTransportError("cleanup_failed")
        self._close_child_streams()
        for name in ("_read_pipe", "_write_pipe", "_stderr_pipe", "thread"):
            handle = getattr(self, name)
            if handle is not None:
                _check(PRIMITIVES.K.CloseHandle(handle))
                setattr(self, name, None)
        if self.process is not None:
            self.process.close()
            self.process = None
