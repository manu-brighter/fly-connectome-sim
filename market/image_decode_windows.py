"""Creation-time Windows Job binding and bounded anonymous-pipe adapter.

Reuses the acquisition helper's unchanged Job/process owners. Stop thresholds and
separate processes do not provide an OS sandbox or instantaneous memory quotas.
"""

import ctypes as ct
from ctypes import wintypes as wt
import importlib
import os
from pathlib import Path
import subprocess
import sys

from .image_decode import DecodeError


ROOT = Path(__file__).absolute().parents[1]


def _fixed_module(name, scripts):
    origin = getattr(sys.modules.get(name), "__file__", None)
    try:
        return type(origin) is str and Path(origin).resolve() == scripts / f"{name}.py"
    except (OSError, ValueError):
        return False


def _load_primitives():
    scripts = ROOT / "scripts"
    for name in ("market_artifacts", "market_supervision"):
        existing = sys.modules.get(name)
        if existing is not None and not _fixed_module(name, scripts):
            raise DecodeError("ownership")
    entry = str(scripts)
    sys.path.insert(0, entry)
    try:
        module = importlib.import_module("market_supervision")
        for name in ("market_artifacts", "market_supervision"):
            if not _fixed_module(name, scripts):
                raise DecodeError("ownership")
        return module
    finally:
        # This is a startup-only import, before service threads. Restore exactly
        # the entry we inserted rather than replacing the entire path list.
        del sys.path[0]


PRIMITIVES = _load_primitives()


if sys.platform == "win32":
    # Separate DLL/function objects: never alter frozen helper signatures.
    API = ct.WinDLL("kernel32", use_last_error=True)

    class SECURITY_ATTRIBUTES(ct.Structure):
        _fields_ = [("length", wt.DWORD), ("descriptor", ct.c_void_p), ("inherit", wt.BOOL)]

    class STARTUPINFOEX(ct.Structure):
        _fields_ = [("StartupInfo", PRIMITIVES.STARTUPINFO), ("lpAttributeList", ct.c_void_p)]

    for name, args, result in (
        ("InitializeProcThreadAttributeList", [ct.c_void_p, wt.DWORD, wt.DWORD, ct.POINTER(ct.c_size_t)], wt.BOOL),
        ("UpdateProcThreadAttribute", [ct.c_void_p, wt.DWORD, ct.c_size_t, ct.c_void_p, ct.c_size_t, ct.c_void_p, ct.c_void_p], wt.BOOL),
        ("DeleteProcThreadAttributeList", [ct.c_void_p], None),
        ("CreatePipe", [ct.POINTER(wt.HANDLE), ct.POINTER(wt.HANDLE), ct.POINTER(SECURITY_ATTRIBUTES), wt.DWORD], wt.BOOL),
        ("SetHandleInformation", [wt.HANDLE, wt.DWORD, wt.DWORD], wt.BOOL),
        ("CreateFileW", [wt.LPCWSTR, wt.DWORD, wt.DWORD, ct.POINTER(SECURITY_ATTRIBUTES), wt.DWORD, wt.DWORD, wt.HANDLE], wt.HANDLE),
        ("PeekNamedPipe", [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.c_void_p, ct.POINTER(wt.DWORD), ct.c_void_p], wt.BOOL),
        ("ReadFile", [wt.HANDLE, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD), ct.c_void_p], wt.BOOL),
        ("CreateProcessW", [wt.LPCWSTR, wt.LPWSTR, ct.c_void_p, ct.c_void_p, wt.BOOL, wt.DWORD,
                            ct.c_void_p, wt.LPCWSTR, ct.POINTER(STARTUPINFOEX), ct.POINTER(PRIMITIVES.PROCESS_INFORMATION)], wt.BOOL),
    ):
        function = getattr(API, name)
        function.argtypes, function.restype = args, result


def _check(value):
    if not value:
        raise ct.WinError(ct.get_last_error())
    return value


def _command(job):
    if sys.platform != "win32" or sys.version_info[:3] != (3, 12, 14):
        raise DecodeError("unsupported_platform")
    package = ROOT / ".venv/Lib/site-packages"
    if not package.is_dir() or package.resolve() != package:
        raise DecodeError("ownership")
    current = PRIMITIVES.WindowsProcess(os.getpid())
    try:
        executable = current.identity()["executable"]
    finally:
        current.close()
    environment = {name: os.environ[name] for name in ("SystemRoot", "WINDIR") if name in os.environ}
    if not environment.get("SystemRoot"):
        raise DecodeError("ownership")
    environment.update(TEMP=str(job), TMP=str(job))
    return [executable, "-I", "-S", "-B", str(ROOT / "scripts/market-image-decode-worker.py"), str(job)], environment


def _membership(process, job):
    inside = wt.BOOL()
    _check(PRIMITIVES.K.IsProcessInJob(process.handle, job.handle, ct.byref(inside)))
    return bool(inside.value)


class OwnedChild:
    """Retains exact handles on unresolved closure; cleanup can be retried."""

    def __init__(self, directory):
        if sys.platform != "win32":
            raise DecodeError("unsupported_platform")
        self.directory = directory
        self.job = None
        self.process = None
        self.thread = None
        self.read_pipe = None
        self.child_streams = []
        self.drained = False
        self.identity = None

    def _close_streams(self):
        for handle in tuple(self.child_streams):
            _check(PRIMITIVES.K.CloseHandle(handle))
            self.child_streams.remove(handle)

    def start(self):
        try:
            command, environment = _command(self.directory)
            self.job = PRIMITIVES.WindowsJob()
            security = SECURITY_ATTRIBUTES(ct.sizeof(SECURITY_ATTRIBUTES), None, True)
            read, write = wt.HANDLE(), wt.HANDLE()
            _check(API.CreatePipe(ct.byref(read), ct.byref(write), ct.byref(security), 4096))
            self.read_pipe = read.value
            self.child_streams.append(write.value)
            _check(API.SetHandleInformation(self.read_pipe, 1, 0))
            for access in (0x80000000, 0x40000000):
                handle = API.CreateFileW("NUL", access, 3, ct.byref(security), 3, 0, None)
                if handle == ct.c_void_p(-1).value:
                    raise ct.WinError(ct.get_last_error())
                self.child_streams.append(handle)
            startup = STARTUPINFOEX()
            startup.StartupInfo.cb = ct.sizeof(startup)
            startup.StartupInfo.dwFlags, startup.StartupInfo.wShowWindow = 0x101, 0
            startup.StartupInfo.hStdInput = self.child_streams[1]
            startup.StartupInfo.hStdOutput = self.child_streams[0]
            startup.StartupInfo.hStdError = self.child_streams[2]
            size = ct.c_size_t()
            API.InitializeProcThreadAttributeList(None, 2, 0, ct.byref(size))
            if not size.value:
                raise ct.WinError(ct.get_last_error())
            attributes = ct.create_string_buffer(size.value)
            startup.lpAttributeList = ct.cast(attributes, ct.c_void_p)
            _check(API.InitializeProcThreadAttributeList(startup.lpAttributeList, 2, 0, ct.byref(size)))
            jobs = (wt.HANDLE * 1)(self.job.handle)
            handles = (wt.HANDLE * 3)(*self.child_streams)
            try:
                _check(API.UpdateProcThreadAttribute(startup.lpAttributeList, 0, 0x0002000D,
                                                     jobs, ct.sizeof(jobs), None, None))
                _check(API.UpdateProcThreadAttribute(startup.lpAttributeList, 0, 0x00020002,
                                                     handles, ct.sizeof(handles), None, None))
                block = ct.create_unicode_buffer("\0".join(f"{key}={value}" for key, value in sorted(environment.items())) + "\0\0")
                information = PRIMITIVES.PROCESS_INFORMATION()
                _check(API.CreateProcessW(command[0], ct.create_unicode_buffer(subprocess.list2cmdline(command)),
                                         # DETACHED_PROCESS avoids even a hidden conhost
                                         # process; SW_HIDE is retained in STARTUPINFO.
                                         None, None, True, 0x00000008 | 0x00000004 | 0x00000400 | 0x00080000,
                                         block, str(self.directory), ct.byref(startup), ct.byref(information)))
                self.thread = information.hThread
                self.process = PRIMITIVES.WindowsProcess(information.dwProcessId, information.hProcess)
            finally:
                API.DeleteProcThreadAttributeList(startup.lpAttributeList)
            self._close_streams()
            self._verify(command[0])
            if PRIMITIVES.K.ResumeThread(self.thread) == 0xFFFFFFFF:
                raise ct.WinError(ct.get_last_error())
            _check(PRIMITIVES.K.CloseHandle(self.thread))
            self.thread = None
        except DecodeError:
            raise
        except Exception:
            raise DecodeError("ownership") from None

    def _verify(self, executable):
        self.identity = self.process.identity()
        if (Path(self.identity["executable"]) != Path(executable)
                or type(self.identity["creation_time_100ns"]) is not int
                or self.identity["creation_time_100ns"] <= 0
                or self.process.exited() or not _membership(self.process, self.job)):
            raise DecodeError("ownership")

    def poll(self, max_bytes=4096):
        if type(max_bytes) is not int or not 1 <= max_bytes <= 4096:
            raise DecodeError("child_protocol")
        available = wt.DWORD()
        eof = False
        if not API.PeekNamedPipe(self.read_pipe, None, 0, None, ct.byref(available), None):
            if ct.get_last_error() == 109:
                eof = True
            else:
                raise ct.WinError(ct.get_last_error())
        block = b""
        if available.value:
            count = min(available.value, max_bytes)
            buffer, read = ct.create_string_buffer(count), wt.DWORD()
            _check(API.ReadFile(self.read_pipe, buffer, count, ct.byref(read), None))
            block = buffer.raw[:read.value]
        exited = self.process.exited()
        peak = self.process.peak()
        pids = self.job.pids()
        extra = any(pid != self.process.pid for pid in pids)
        # Executable identity was fixed before resume and the exact process
        # handle is still held. QueryFullProcessImageNameW can fail after exit;
        # creation time remains queryable and does not reopen/search by PID.
        creation, end, kernel, user = (ct.c_uint64() for _ in range(4))
        _check(PRIMITIVES.K.GetProcessTimes(self.process.handle, ct.byref(creation), ct.byref(end),
                                           ct.byref(kernel), ct.byref(user)))
        if creation.value != self.identity["creation_time_100ns"]:
            raise DecodeError("ownership")
        # Empty job is required even after the held process signalled exit.
        return block, eof, exited and not pids, self.process.exit_code() if exited else None, peak, extra

    def cleanup(self):
        if not self.drained:
            # A creation/verification failure may leave a held suspended process;
            # terminate this exact handle even if JOB_LIST verification failed.
            if self.process is not None and not self.process.exited():
                _check(PRIMITIVES.K.TerminateProcess(self.process.handle, 1))
            if self.job is not None:
                self.job.terminate_and_wait()
            if self.process is not None and PRIMITIVES.K.WaitForSingleObject(self.process.handle, 10000) != 0:
                raise RuntimeError("held process closure not confirmed")
            if self.job is not None and self.job.pids():
                raise RuntimeError("owned job not empty")
            self.drained = True
        # Only close ownership handles after both proofs. Partial-close retry
        # retains all remaining exact handles and the already-confirmed drain.
        self._close_streams()
        if self.thread is not None:
            _check(PRIMITIVES.K.CloseHandle(self.thread))
            self.thread = None
        if self.read_pipe is not None:
            _check(PRIMITIVES.K.CloseHandle(self.read_pipe))
            self.read_pipe = None
        if self.process is not None:
            self.process.close()
            self.process = None
        if self.job is not None:
            self.job.close()
