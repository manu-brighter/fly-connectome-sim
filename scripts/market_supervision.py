"""Fixed Windows acquisition supervision; process-start guard is not a sandbox.

Win32 contracts: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes as ct
from ctypes import wintypes as wt
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import threading
import time

from market_artifacts import _safe_directory, write_json_exclusive


ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"wall_seconds": 900, "peak_rss_bytes": 4 * 1024**3,
          "new_output_evidence_bytes": 256 * 1024**2, "poll_seconds_max": 2}
HASH = re.compile(r"[0-9a-f]{64}\Z")


def _file(path: Path) -> dict:
    _safe_directory(path.parent)
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Unsafe file: {path}")
    digest = sha256()
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("File changed during open")
        while block := stream.read(1024 * 1024):
            digest.update(block)
    after = path.stat(follow_symlinks=False)
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("File changed during hashing")
    return {"path": str(path.absolute()), "sha256": digest.hexdigest(), "size": before.st_size}


def _json(path: Path) -> dict:
    identity = _file(path)
    if identity["size"] > 2 * 1024**2:
        raise ValueError("Supervision JSON exceeds limit")
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != identity["sha256"]:
        raise ValueError("JSON changed during read")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs)
    if type(result) is not dict:
        raise ValueError("Expected JSON object")
    return result


def _paths(output: Path, evidence: Path) -> tuple[Path, Path]:
    paths = tuple(Path(os.path.abspath(path)) for path in (output, evidence))
    root = ROOT.resolve()
    for path in paths:
        if not path.is_relative_to(root) or path == root:
            raise ValueError("Supervision directories must be inside workspace")
        _safe_directory(path if path.exists() else path.parent)
    if paths[0].is_relative_to(paths[1]) or paths[1].is_relative_to(paths[0]):
        raise ValueError("Output/evidence directories must be disjoint")
    return paths


def _inventory(path: Path, names: set[str]) -> None:
    _safe_directory(path)
    if {child.name for child in path.iterdir()} != names:
        raise ValueError("Prepared directory inventory differs; no failed-run reuse")
    for name in names:
        _file(path / name)


def _configuration() -> dict:
    if sys.platform != "win32":
        raise ValueError("Production supervision requires Windows")
    python = ROOT / ".venv/Scripts/python.exe"
    cfg = ROOT / ".venv/pyvenv.cfg"
    home = dict(line.split(" = ", 1) for line in cfg.read_text().splitlines() if " = " in line)["home"]
    worker = Path(home) / "python.exe"
    data = ROOT / "data/malecns-v1.0/runtime"
    configured_data = Path(os.environ.get("FLY_CONNECTOME_SIM_DATA") or data).absolute()
    if configured_data != data:
        raise ValueError("Prepared graph environment differs")
    compiler = Path(os.environ.get("FLY_CONNECTOME_SIM_CXX") or ROOT / ".tools/zig/zig-x86_64-windows-0.16.0/zig.exe").absolute()
    if compiler.name.lower() != "zig.exe":
        raise ValueError("Only the pinned local Zig version probe is supported")
    source = ROOT / "src/fly_connectome_sim/neural/kernel.cpp"
    library = data / "cache/physiology-v6/memory.dll"
    metadata = library.with_suffix(".dll.json")
    identities = {name: _file(path) for name, path in {
        "python": python, "python_configuration": cfg, "worker": worker,
        "entrypoint": ROOT / "scripts/run-market-response-diagnostic.py",
        "helper": Path(__file__).resolve(), "supervisor": ROOT / "scripts/supervise-market-response.ps1",
        "native_source": source, "native_library": library, "native_metadata": metadata,
        "compiler": compiler,
    }.items()}
    record = _json(metadata)
    if (record != {"source_sha256": identities["native_source"]["sha256"], "compiler": "0.16.0",
                   "flags": ["-O3", "-std=c++17", "-shared", "-Wl,--export-all-symbols"],
                   "library": "memory.dll", "binary_sha256": identities["native_library"]["sha256"]}):
        raise ValueError("Prepared native cache metadata does not match pinned source/compiler/binary")
    # Construct/set/close an empty owned job in Prepare. No child/native launch.
    with WindowsJob():
        pass
    return {"files": identities, "data_directory": str(data),
            "compiler_version_argv": [str(compiler), "version"], "compiler_version": "0.16.0"}


def _readiness(output: Path, evidence: Path, expected: str) -> dict:
    if not HASH.fullmatch(expected) or _file(output / "protocol.json")["sha256"] != expected:
        raise ValueError("Prepared protocol hash differs")
    return {"version": "market-supervision/v1", "output_directory": str(output),
            "evidence_directory": str(evidence), "protocol_sha256": expected,
            "configuration": _configuration(), "limits": dict(LIMITS)}


def prepare(output: Path, evidence: Path, expected: str) -> dict:
    output, evidence = _paths(output, evidence)
    _inventory(output, {"protocol.json"})
    if evidence.exists():
        raise ValueError("Evidence directory must be new")
    readiness = _readiness(output, evidence, expected)
    evidence.mkdir()
    write_json_exclusive(readiness, evidence / "readiness.json")
    return readiness


def validate_prepared(output: Path, evidence: Path, protocol_hash: str, readiness_hash: str) -> dict:
    output, evidence = _paths(output, evidence)
    _inventory(output, {"protocol.json"})
    _inventory(evidence, {"readiness.json"})
    if not HASH.fullmatch(readiness_hash) or _file(evidence / "readiness.json")["sha256"] != readiness_hash:
        raise ValueError("Readiness hash differs")
    readiness = _json(evidence / "readiness.json")
    if readiness != _readiness(output, evidence, protocol_hash):
        raise ValueError("Prepared source/path/configuration identity differs")
    return readiness


def _wait_for_release(evidence: Path, binding: dict, *, timeout: float = 30) -> None:
    _safe_directory(evidence)
    write_json_exclusive(binding, evidence / "worker-ready.json")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        release = evidence / "release.json"
        if release.exists():
            if _json(release) != binding:
                raise ValueError("Supervision release binding differs")
            return
        time.sleep(0.02)
    raise TimeoutError("Supervision release missing after bounded wait")


@contextmanager
def compiler_probe_guard(argv: list[str]):
    """Guard the builder's known subprocess path; never bypass cache validation."""
    active = True
    expected = list(map(os.fspath, argv))
    def guard(event, args):
        if not active:
            return
        if event == "subprocess.Popen":
            executable, command, cwd, environment = args
            # Windows audit argv is the exact list2cmdline result, POSIX a list.
            matches = command == expected or command == subprocess.list2cmdline(expected)
            if (executable is None or os.fspath(executable) == expected[0]) and matches:
                return
            raise RuntimeError("Unapproved process start; only exact pinned compiler version probe allowed")
        if event in {"os.system", "os.posix_spawn", "os.spawn", "os.startfile", "os.exec", "os.fork", "os.forkpty"}:
            raise RuntimeError("Unapproved process start")
    sys.addaudithook(guard)
    try:
        yield
    finally:
        active = False


@contextmanager
def production_start(output: Path, protocol_hash: str, evidence: Path | None,
                     readiness_hash: str | None, token: str | None):
    if evidence is None or not isinstance(readiness_hash, str) or not isinstance(token, str):
        raise ValueError("Native execution requires supervision directory/hash/start token")
    if not HASH.fullmatch(readiness_hash) or not HASH.fullmatch(token):
        raise ValueError("Invalid supervision hash/token")
    output, evidence = _paths(output, evidence)
    if _file(evidence / "readiness.json")["sha256"] != readiness_hash:
        raise ValueError("Supervision readiness hash differs")
    readiness = _json(evidence / "readiness.json")
    if readiness != _readiness(output, evidence, protocol_hash):
        raise ValueError("Supervision source/path/configuration differs")
    scratch = evidence / "scratch"
    _safe_directory(scratch)
    if any(Path(os.environ.get(name, "")).absolute() != scratch for name in ("TMP", "TEMP")):
        raise ValueError("Child temporary files must use counted supervision scratch")
    binding = {"pid": os.getpid(), "start_token": token,
               "protocol_sha256": protocol_hash, "readiness_sha256": readiness_hash}
    _wait_for_release(evidence, binding)
    # Recheck identities after waiting; the installed guard remains active through
    # engine construction/acquisition/audit. The compiler inherits the owned job.
    if readiness["configuration"] != _configuration():
        raise ValueError("Prepared native/source identity changed before release")
    with compiler_probe_guard(readiness["configuration"]["compiler_version_argv"]):
        yield


# ctypes declarations are Windows-only; offline CI still exercises path/handshake/guard.
if sys.platform == "win32":
    K = ct.WinDLL("kernel32", use_last_error=True)
    SIZE = ct.c_size_t
    ULONG_PTR = ct.c_size_t
    class BASIC_LIMIT(ct.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ct.c_int64), ("PerJobUserTimeLimit", ct.c_int64),
                    ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", SIZE), ("MaximumWorkingSetSize", SIZE),
                    ("ActiveProcessLimit", wt.DWORD), ("Affinity", ULONG_PTR),
                    ("PriorityClass", wt.DWORD), ("SchedulingClass", wt.DWORD)]
    class IO_COUNTERS(ct.Structure):
        _fields_ = [(name, ct.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                                   "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
    class EXTENDED_LIMIT(ct.Structure):
        _fields_ = [("BasicLimitInformation", BASIC_LIMIT), ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", SIZE), ("JobMemoryLimit", SIZE),
                    ("PeakProcessMemoryUsed", SIZE), ("PeakJobMemoryUsed", SIZE)]
    class MEMORY_COUNTERS(ct.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD)] + [
            (name, SIZE) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                     "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                                     "PagefileUsage", "PeakPagefileUsage")]
    class STARTUPINFO(ct.Structure):
        _fields_ = [("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR), ("lpTitle", wt.LPWSTR),
                    ("dwX", wt.DWORD), ("dwY", wt.DWORD), ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD),
                    ("dwXCountChars", wt.DWORD), ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
                    ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
                    ("lpReserved2", ct.c_void_p), ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE)]
    class PROCESS_INFORMATION(ct.Structure):
        _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]
    class PROCESSENTRY(ct.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ULONG_PTR), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", wt.LONG), ("dwFlags", wt.DWORD),
                    ("szExeFile", wt.WCHAR * 260)]
    for name, args, result in [
        ("CreateJobObjectW", [ct.c_void_p, wt.LPCWSTR], wt.HANDLE),
        ("SetInformationJobObject", [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD], wt.BOOL),
        ("QueryInformationJobObject", [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.c_void_p], wt.BOOL),
        ("AssignProcessToJobObject", [wt.HANDLE, wt.HANDLE], wt.BOOL),
        ("IsProcessInJob", [wt.HANDLE, wt.HANDLE, ct.POINTER(wt.BOOL)], wt.BOOL),
        ("TerminateJobObject", [wt.HANDLE, wt.UINT], wt.BOOL),
        ("CloseHandle", [wt.HANDLE], wt.BOOL),
        ("OpenProcess", [wt.DWORD, wt.BOOL, wt.DWORD], wt.HANDLE),
        ("GetProcessTimes", [wt.HANDLE, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p], wt.BOOL),
        ("QueryFullProcessImageNameW", [wt.HANDLE, wt.DWORD, wt.LPWSTR, ct.POINTER(wt.DWORD)], wt.BOOL),
        ("K32GetProcessMemoryInfo", [wt.HANDLE, ct.c_void_p, wt.DWORD], wt.BOOL),
        ("WaitForSingleObject", [wt.HANDLE, wt.DWORD], wt.DWORD),
        ("GetExitCodeProcess", [wt.HANDLE, ct.POINTER(wt.DWORD)], wt.BOOL),
        ("ResumeThread", [wt.HANDLE], wt.DWORD),
        ("TerminateProcess", [wt.HANDLE, wt.UINT], wt.BOOL),
        ("CreateToolhelp32Snapshot", [wt.DWORD, wt.DWORD], wt.HANDLE),
        ("Process32FirstW", [wt.HANDLE, ct.POINTER(PROCESSENTRY)], wt.BOOL),
        ("Process32NextW", [wt.HANDLE, ct.POINTER(PROCESSENTRY)], wt.BOOL),
        ("CreateProcessW", [wt.LPCWSTR, wt.LPWSTR, ct.c_void_p, ct.c_void_p, wt.BOOL, wt.DWORD,
                            ct.c_void_p, wt.LPCWSTR, ct.POINTER(STARTUPINFO), ct.POINTER(PROCESS_INFORMATION)], wt.BOOL),
    ]:
        function = getattr(K, name)
        function.argtypes, function.restype = args, result


def _check(value):
    if not value:
        raise ct.WinError(ct.get_last_error())
    return value


class WindowsProcess:
    def __init__(self, pid: int, handle=None):
        self.pid = pid
        self.handle = handle or _check(K.OpenProcess(0x00100000 | 0x0400 | 0x0010 | 0x0100 | 0x0001, False, pid))

    def identity(self) -> dict:
        creation, exit_time, kernel, user = (ct.c_uint64() for _ in range(4))
        _check(K.GetProcessTimes(self.handle, ct.byref(creation), ct.byref(exit_time), ct.byref(kernel), ct.byref(user)))
        size = wt.DWORD(32768)
        path = ct.create_unicode_buffer(size.value)
        _check(K.QueryFullProcessImageNameW(self.handle, 0, path, ct.byref(size)))
        return {"pid": self.pid, "creation_time_100ns": creation.value, "executable": str(Path(path.value).absolute())}

    def peak(self) -> int:
        counters = MEMORY_COUNTERS()
        counters.cb = ct.sizeof(counters)
        _check(K.K32GetProcessMemoryInfo(self.handle, ct.byref(counters), ct.sizeof(counters)))
        return counters.PeakWorkingSetSize

    def exited(self) -> bool:
        result = K.WaitForSingleObject(self.handle, 0)
        if result == 0xFFFFFFFF:
            raise ct.WinError(ct.get_last_error())
        return result == 0

    def exit_code(self) -> int:
        code = wt.DWORD()
        _check(K.GetExitCodeProcess(self.handle, ct.byref(code)))
        return code.value

    def close(self):
        if self.handle:
            _check(K.CloseHandle(self.handle))
            self.handle = None


class WindowsJob:
    def __init__(self):
        if sys.platform != "win32":
            raise ValueError("Windows Job Objects unavailable")
        self.lock = threading.RLock()
        self.stopping = False
        self.handle = _check(K.CreateJobObjectW(None, None))
        limits = EXTENDED_LIMIT()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE; neither breakaway flag.
        try:
            _check(K.SetInformationJobObject(self.handle, 9, ct.byref(limits), ct.sizeof(limits)))
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def assign(self, process: WindowsProcess):
        with self.lock:
            if self.stopping:
                raise RuntimeError("Owned job is stopping; no process may be assigned/released")
            inside = wt.BOOL()
            _check(K.IsProcessInJob(process.handle, self.handle, ct.byref(inside)))
            if not inside.value:
                _check(K.AssignProcessToJobObject(self.handle, process.handle))
            _check(K.IsProcessInJob(process.handle, self.handle, ct.byref(inside)))
            if not inside.value:
                raise RuntimeError("Owned process job assignment failed")

    def pids(self) -> list[int]:
        class PID_LIST(ct.Structure):
            _fields_ = [("assigned", wt.DWORD), ("count", wt.DWORD), ("pids", ULONG_PTR * 256)]
        result = PID_LIST()
        _check(K.QueryInformationJobObject(self.handle, 3, ct.byref(result), ct.sizeof(result), None))
        if result.assigned > 256 or result.count > 256:
            raise RuntimeError("Owned process inventory exceeds fixed cap")
        return list(result.pids[:result.count])

    def terminate_and_wait(self):
        with self.lock:
            self.stopping = True
            _check(K.TerminateJobObject(self.handle, 1))
        deadline = time.monotonic() + 10
        while self.pids():
            if time.monotonic() >= deadline:
                raise RuntimeError("Owned job termination did not finish within 10 seconds")
            time.sleep(0.02)

    def close(self):
        if self.handle:
            _check(K.CloseHandle(self.handle))
            self.handle = None


def _parents() -> dict[int, int]:
    snapshot = K.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ct.c_void_p(-1).value:
        raise ct.WinError(ct.get_last_error())
    try:
        entry = PROCESSENTRY()
        entry.dwSize = ct.sizeof(entry)
        _check(K.Process32FirstW(snapshot, ct.byref(entry)))
        result = {}
        while True:
            result[entry.th32ProcessID] = entry.th32ParentProcessID
            if not K.Process32NextW(snapshot, ct.byref(entry)):
                if ct.get_last_error() != 18:
                    raise ct.WinError(ct.get_last_error())
                return result
    finally:
        K.CloseHandle(snapshot)


def _descends(pid: int, launcher: int) -> bool:
    parents, seen = _parents(), set()
    while pid != launcher:
        if pid in seen or pid not in parents:
            return False
        seen.add(pid)
        pid = parents[pid]
    return True


def _launch_suspended(command: list[str], evidence: Path, environment: dict) -> tuple[WindowsProcess, int]:
    import msvcrt
    startup, information = STARTUPINFO(), PROCESS_INFORMATION()
    startup.cb, startup.dwFlags, startup.wShowWindow = ct.sizeof(startup), 0x101, 0
    with (evidence / "stdout.log").open("xb", buffering=0) as stdout, \
            (evidence / "stderr.log").open("xb", buffering=0) as stderr, open(os.devnull, "rb") as stdin:
        handles = [msvcrt.get_osfhandle(stream.fileno()) for stream in (stdin, stdout, stderr)]
        for handle in handles:
            os.set_handle_inheritable(handle, True)
        startup.hStdInput, startup.hStdOutput, startup.hStdError = handles
        block = ct.create_unicode_buffer("\0".join(f"{key}={value}" for key, value in sorted(environment.items())) + "\0\0")
        try:
            _check(K.CreateProcessW(command[0], ct.create_unicode_buffer(subprocess.list2cmdline(command)),
                                   None, None, True, 0x08000000 | 0x00000004 | 0x00000400,
                                   block, str(ROOT), ct.byref(startup), ct.byref(information)))
        finally:
            for handle in handles:
                os.set_handle_inheritable(handle, False)
    return WindowsProcess(information.dwProcessId, information.hProcess), information.hThread


def _new_bytes(*directories: Path) -> int:
    total = 0
    def visit(directory):
        nonlocal total
        _safe_directory(directory)
        for path in directory.iterdir():
            state = path.stat(follow_symlinks=False)
            if path.is_symlink() or path.is_junction():
                raise ValueError("Unsafe link in counted output")
            if stat.S_ISDIR(state.st_mode):
                visit(path)
            elif stat.S_ISREG(state.st_mode):
                total += state.st_size
            else:
                raise ValueError("Nonregular counted output")
    for directory in directories:
        visit(directory)
    return total


def _cancel_state(evidence: Path, *, terminal: bool = False, request: bool = False) -> bytes:
    """One pre-counted byte, locked across Python and the PowerShell frontend.

    0=accepting cancellation, 1=requested, 2=terminal cancellation cutoff.
    The cutoff observes and changes state under the same OS byte-range lock as
    cancellation requests; a request after state2 neither writes nor grows data.
    """
    import msvcrt
    path = evidence / "cancel.signal"
    _safe_directory(evidence)
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not stat.S_ISREG(before.st_mode) or before.st_size != 1:
        raise ValueError("Invalid fixed-size cancellation signal")
    with path.open("r+b", buffering=0) as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size) != (before.st_dev, before.st_ino, 1):
            raise ValueError("Cancellation signal identity changed")
        deadline = time.monotonic() + 1
        while True:
            try:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Cancellation signal lock unavailable") from error
                time.sleep(0.01)
        try:
            state = stream.read(1)
            if state not in {b"0", b"1", b"2"}:
                raise ValueError("Invalid cancellation signal state")
            next_state = b"2" if terminal else (b"1" if request and state != b"2" else state)
            if next_state != state:
                stream.seek(0)
                stream.write(next_state)
                os.fsync(stream.fileno())
            return state
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def request_cancellation(evidence: Path) -> bool:
    """Internal fixed-byte cancellation channel; no program or limit injection."""
    return _cancel_state(evidence, request=True) != b"2"


def _run_owned(command, output, evidence, *, expected_executable, binding, limits,
               owner=None, _test_fault=None, _test_cancel=None) -> dict:
    """Internal monitor; production caller supplies only the fixed derived command.

    `_test_*` are non-neural test injection, never exposed by either public CLI.
    """
    start, started = time.monotonic(), datetime.now(timezone.utc).isoformat()
    receipt = {"version": "market-supervisor-receipt/v1", "status": "failed", "stop_reason": "monitor-failure",
               "started_utc": started, "limits": dict(limits), "protocol_sha256": binding["protocol_sha256"],
               "readiness_sha256": binding["readiness_sha256"], "launcher": None, "worker": None,
               "observed_peak_working_set_bytes": 0, "owned_children_peak_working_set_bytes": {},
               "pre_ready_python_peak_working_set_bytes": 0, "owned_children": {},
               "owner": owner.identity() if owner is not None else None,
               "observed_output_evidence_bytes": 0, "exit_code": None, "samples": 0,
               "output_accounting_complete": True,
               "memory_semantics": "actual held worker PROCESS_MEMORY_COUNTERS.PeakWorkingSetSize; children separate",
               "sampling_limits": "stop thresholds; output may overshoot between polls; not a sandbox or scientific acceptance"}
    job, launcher, worker, thread = WindowsJob(), None, None, None
    held = {}
    watch_stop, interrupted = threading.Event(), threading.Event()
    terminal_lock = threading.Lock()
    interruption = {}
    watchdog = None
    scratch = evidence / "scratch"
    scratch.mkdir()
    with (evidence / "cancel.signal").open("xb") as signal:
        signal.write(b"0")
    environment = dict(os.environ, TMP=str(scratch), TEMP=str(scratch))
    try:
        with_self = WindowsProcess(os.getpid())
        try:
            receipt["supervisor"] = with_self.identity()
        finally:
            with_self.close()
        if owner is not None:
            # Separate watchdog continues to close the owned tree even if a
            # monitor filesystem/hash/API call stalls. It holds the exact PS
            # process handle, never a later process that reuses the PID.
            def watch_owner():
                try:
                    while not watch_stop.wait(0.02):
                        with terminal_lock:
                            state = _cancel_state(evidence)
                            if state == b"2":
                                return
                            reason = "owner-exited" if owner.exited() else ("cancelled" if state == b"1" else None)
                            if reason:
                                interruption["reason"] = reason
                                interrupted.set()
                        if reason:
                            job.terminate_and_wait()
                            return
                except BaseException as error:
                    interruption.update(reason="monitor-failure", error=str(error))
                    interrupted.set()
                    try:
                        job.terminate_and_wait()
                    except BaseException as cleanup:
                        interruption["cleanup_error"] = str(cleanup)
            watchdog = threading.Thread(target=watch_owner, name="market-owner-watchdog", daemon=True)
            watchdog.start()
            with_self = WindowsProcess(os.getpid())
            try:
                supervisor_ready = {**with_self.identity(), "owner": owner.identity(), **binding}
            finally:
                with_self.close()
            write_json_exclusive(supervisor_ready, evidence / "supervisor-ready.json")
            acknowledged = False
            while time.monotonic() - start < min(30, limits["wall_seconds"]):
                if interrupted.is_set():
                    break
                if (evidence / "supervisor-ack.json").exists():
                    if _json(evidence / "supervisor-ack.json") != supervisor_ready:
                        raise ValueError("PowerShell actual-supervisor acknowledgement differs")
                    acknowledged = True
                    break
                time.sleep(0.02)
            if not acknowledged:
                if interrupted.is_set():
                    raise InterruptedError(interruption["reason"])
                raise TimeoutError("PowerShell did not hold/acknowledge actual supervisor within bounded deadline")
        launcher, thread = _launch_suspended(command, evidence, environment)
        receipt["launcher"] = launcher.identity()
        if _test_fault == "assignment":
            raise RuntimeError("Injected job assignment failure before resume/release")
        job.assign(launcher)
        if K.ResumeThread(thread) == 0xFFFFFFFF:
            raise ct.WinError(ct.get_last_error())
        K.CloseHandle(thread)
        thread = None
        with (evidence / "samples.jsonl").open("xb", buffering=0) as samples:
            while True:
                if interrupted.is_set():
                    receipt["stop_reason"] = interruption["reason"]
                    break
                if owner is not None and owner.exited():
                    receipt["stop_reason"] = "owner-exited"
                    break
                if _test_cancel is not None and _test_cancel():
                    receipt["stop_reason"] = "cancelled"
                    break
                if _test_fault == "monitor":
                    raise RuntimeError("Injected monitor failure")
                ready = evidence / "worker-ready.json"
                if worker is None and ready.exists():
                    actual = _json(ready)
                    pid = actual.get("pid")
                    if type(pid) is not int or pid < 1 or actual != {"pid": pid, **binding}:
                        raise ValueError("Actual worker ready binding differs")
                    worker = WindowsProcess(pid)
                    identity = worker.identity()
                    if (Path(identity["executable"]) != Path(expected_executable).absolute()
                            or identity["creation_time_100ns"] < receipt["launcher"]["creation_time_100ns"]
                            or not _descends(pid, launcher.pid) or worker.exited()):
                        raise ValueError("Actual worker executable/start/descent identity differs")
                    job.assign(worker)
                    receipt["worker"] = identity
                    if pid in held:
                        held.pop(pid).close()
                        receipt["owned_children"].pop(str(pid), None)
                        receipt["owned_children_peak_working_set_bytes"].pop(str(pid), None)
                for pid in job.pids():
                    if pid != (worker.pid if worker else None) and pid not in held:
                        held[pid] = WindowsProcess(pid)
                        receipt["owned_children"][str(pid)] = held[pid].identity()
                for pid, child in held.items():
                    peak = child.peak()
                    receipt["owned_children_peak_working_set_bytes"][str(pid)] = max(
                        peak, receipt["owned_children_peak_working_set_bytes"].get(str(pid), 0))
                    if (worker is None and Path(receipt["owned_children"][str(pid)]["executable"])
                            == Path(expected_executable).absolute()):
                        receipt["pre_ready_python_peak_working_set_bytes"] = max(
                            receipt["pre_ready_python_peak_working_set_bytes"], peak)
                if worker is not None:
                    receipt["observed_peak_working_set_bytes"] = max(receipt["observed_peak_working_set_bytes"], worker.peak())
                elapsed = time.monotonic() - start
                size = _new_bytes(output, evidence)
                receipt["observed_output_evidence_bytes"] = max(size, receipt["observed_output_evidence_bytes"])
                samples.write((json.dumps({"wall_seconds": elapsed, "worker_peak_working_set_bytes": receipt["observed_peak_working_set_bytes"],
                                           "output_evidence_bytes": size, "owned_pids": job.pids()}, sort_keys=True) + "\n").encode())
                receipt["samples"] += 1
                if elapsed >= limits["wall_seconds"]:
                    receipt["stop_reason"] = "wall-limit"
                    break
                if max(receipt["observed_peak_working_set_bytes"], receipt["pre_ready_python_peak_working_set_bytes"]) > limits["peak_rss_bytes"]:
                    receipt["stop_reason"] = "memory-limit"
                    break
                if _new_bytes(output, evidence) > limits["new_output_evidence_bytes"]:
                    receipt["stop_reason"] = "output-limit"
                    break
                if worker is not None and not (evidence / "release.json").exists():
                    with job.lock:
                        if job.stopping or interrupted.is_set():
                            raise InterruptedError(interruption.get("reason", "cancelled"))
                        write_json_exclusive({"pid": worker.pid, **binding}, evidence / "release.json")
                if worker is not None and worker.exited():
                    receipt["exit_code"] = worker.exit_code()
                    if receipt["exit_code"] != 0:
                        receipt["stop_reason"] = "child-failed"
                        break
                    # The venv launcher can need a few milliseconds to reap worker.
                    if launcher.exited():
                        if job.pids():
                            receipt["stop_reason"] = "owned-child-still-running"
                        elif (output / "receipt.json").is_file():
                            receipt.update(status="completed", stop_reason="completed")
                        else:
                            receipt["stop_reason"] = "missing-receipt"
                        break
                elif worker is None and launcher.exited():
                    receipt["exit_code"] = launcher.exit_code()
                    receipt["stop_reason"] = "worker-not-ready"
                    break
                time.sleep(min(limits["poll_seconds_max"], 0.25))
    except InterruptedError:
        receipt["stop_reason"] = interruption.get("reason", "cancelled")
    except KeyboardInterrupt:
        receipt["stop_reason"] = "cancelled"
    except BaseException as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        receipt["stop_reason"] = "monitor-failure"
    finally:
        try:
            # A pre-assignment failure leaves the launcher suspended outside job.
            if launcher is not None and not launcher.exited():
                K.TerminateProcess(launcher.handle, 1)
            job.terminate_and_wait()
            if launcher is not None and K.WaitForSingleObject(launcher.handle, 10000) != 0:
                raise RuntimeError("Launcher termination wait failed")
            if worker is not None:
                receipt["observed_peak_working_set_bytes"] = max(receipt["observed_peak_working_set_bytes"], worker.peak())
                receipt["exit_code"] = worker.exit_code()
            for pid, child in held.items():
                receipt["owned_children_peak_working_set_bytes"][str(pid)] = max(
                    child.peak(), receipt["owned_children_peak_working_set_bytes"].get(str(pid), 0))
            receipt["job_active_processes_after_cleanup"] = len(job.pids())
        except BaseException as error:
            receipt.update(status="failed", stop_reason="cleanup-failure", cleanup_error=str(error))
        finally:
            if thread:
                K.CloseHandle(thread)
            for process in [worker, launcher, *held.values()]:
                if process:
                    process.close()
        # Keep the independent watchdog active through job drain. This locked
        # transition is the terminal cancellation cutoff, before final byte
        # accounting/publication. The signal is never created/grown by PS.
        try:
            with terminal_lock:
                state = _cancel_state(evidence, terminal=True)
                receipt["cancellation_requested_at_cutoff"] = state == b"1"
                if state == b"1":
                    receipt.update(status="failed", stop_reason="cancelled")
                elif owner is not None and owner.exited():
                    receipt.update(status="failed", stop_reason="owner-exited")
                if interrupted.is_set():
                    receipt.update(status="failed", stop_reason=interruption["reason"])
                receipt["terminal_cutoff_utc"] = datetime.now(timezone.utc).isoformat()
                receipt["terminal_cutoff_wall_seconds"] = time.monotonic() - start
                receipt["cancellation_semantics"] = "locked fixed-byte cutoff after job drain; later cancellation is ignored without changing counted bytes"
                watch_stop.set()
        except (OSError, ValueError) as error:
            receipt.update(status="failed", stop_reason="monitor-failure", cancellation_error=str(error))
            watch_stop.set()
        if watchdog is not None:
            watchdog.join(11)
            if watchdog.is_alive():
                receipt.update(status="failed", stop_reason="cleanup-failure", cleanup_error="Owner watchdog did not finish")
            elif interrupted.is_set() and receipt["status"] == "completed":
                # An exception begun under the pre-cutoff monitor lock can
                # finish reporting during join; it must not escape acceptance.
                receipt.update(status="failed", stop_reason=interruption["reason"])
        job.close()
    receipt["ended_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["wall_seconds"] = time.monotonic() - start
    if max(receipt["observed_peak_working_set_bytes"], receipt["pre_ready_python_peak_working_set_bytes"]) > limits["peak_rss_bytes"]:
        receipt.update(status="failed", stop_reason="memory-limit")
    try:
        base = _new_bytes(output, evidence)
    except (OSError, ValueError) as error:
        base = receipt["observed_output_evidence_bytes"]
        receipt.update(status="failed", stop_reason="monitor-failure", output_accounting_complete=False,
                       output_accounting_error=str(error))
    # Include this receipt's own bytes; incomplete accounting remains a labelled
    # lower bound and can never produce completion.
    for _ in range(4):
        receipt["observed_output_evidence_bytes"] = max(base + len(_encoded(receipt)), receipt["observed_output_evidence_bytes"])
    if receipt["observed_output_evidence_bytes"] > limits["new_output_evidence_bytes"] and receipt["output_accounting_complete"]:
        receipt.update(status="failed", stop_reason="output-limit")
    if receipt["wall_seconds"] >= limits["wall_seconds"] and receipt["status"] == "completed":
        receipt.update(status="failed", stop_reason="wall-limit")
    for _ in range(4):
        receipt["observed_output_evidence_bytes"] = max(base + len(_encoded(receipt)), receipt["observed_output_evidence_bytes"])
    _safe_directory(evidence)
    write_json_exclusive(receipt, evidence / "supervisor-receipt.json")
    return receipt


def _encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode()


def run(output: Path, evidence: Path, protocol_hash: str, readiness_hash: str, *, owner: WindowsProcess) -> dict:
    readiness = validate_prepared(output, evidence, protocol_hash, readiness_hash)
    output, evidence = _paths(output, evidence)
    config = readiness["configuration"]
    token = secrets.token_hex(32)
    os.environ["FLY_CONNECTOME_SIM_CXX"] = config["files"]["compiler"]["path"]
    os.environ["FLY_CONNECTOME_SIM_DATA"] = config["data_directory"]
    command = [config["files"]["python"]["path"], config["files"]["entrypoint"]["path"], "run",
               "--output-dir", str(output), "--expected-protocol-sha256", protocol_hash, "--run-native",
               "--supervision-directory", str(evidence), "--expected-readiness-sha256", readiness_hash,
               "--start-token", token]
    return _run_owned(command, output, evidence, expected_executable=Path(config["files"]["worker"]["path"]),
                      binding={"start_token": token, "protocol_sha256": protocol_hash, "readiness_sha256": readiness_hash},
                      limits=LIMITS, owner=owner)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("Prepare", "Run"), required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--expected-protocol-sha256", required=True)
    parser.add_argument("--expected-readiness-sha256")
    parser.add_argument("--owner-pid", type=int, required=True)
    parser.add_argument("--owner-created", type=int, required=True)
    args = parser.parse_args()
    owner = None
    try:
        if sys.platform != "win32":
            raise ValueError("Windows supervision required")
        owner = WindowsProcess(args.owner_pid)
        if owner.identity()["creation_time_100ns"] != args.owner_created or not _descends(os.getpid(), owner.pid):
            raise ValueError("PowerShell owner identity/descent differs")
        if args.mode == "Prepare":
            result = prepare(args.output_directory, args.evidence_directory, args.expected_protocol_sha256)
        else:
            if args.expected_readiness_sha256 is None:
                raise ValueError("Run requires expected readiness hash")
            result = run(args.output_directory, args.evidence_directory, args.expected_protocol_sha256,
                         args.expected_readiness_sha256, owner=owner)
        print(_encoded(result).decode().rstrip())
        return 0 if args.mode == "Prepare" or result["status"] == "completed" else 1
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        parser.exit(1, f"Market supervision failed: {error}\n")
    finally:
        if owner is not None:
            owner.close()


if __name__ == "__main__":
    raise SystemExit(main())
