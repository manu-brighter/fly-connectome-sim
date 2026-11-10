"""Actual Windows harmless-process checks; no simulation or network."""

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
import zlib

import pytest

from market.image_decode import DecodeError, DecodeRequest, ImageDecoder


ROOT = Path(__file__).resolve().parents[2]
INC = "00000000-0000-4000-8000-000000000001"
ID = "00000000-0000-4000-8000-000000000002"
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows creation-time Job ownership required")


def png():
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0\xff\0\0")) + chunk(b"IEND", b""))


@pytest.fixture
def windows_root(tmp_path):
    root = ROOT / ".tools/image-decoding-20261110" / f"{tmp_path.parent.name}-{tmp_path.name}"
    root.mkdir(parents=True)
    return root


def actual_request(payload):
    now = time.perf_counter_ns()
    return DecodeRequest(INC, ID, hashlib.sha256(payload).hexdigest(), len(payload), "image/png", now, now + 10_000_000_000)


def test_actual_png_decode_cleans_owned_process_and_scratch(windows_root):
    decoder = ImageDecoder(windows_root)
    try:
        result = decoder.decode(request=actual_request(png()), payload=png())
        assert result.rgb == b"\xff\0\0" * 4096
        assert 0 < result.observed_peak_working_set_bytes <= 536870912
        assert not (windows_root / "job").exists()
        (windows_root / "success-evidence.json").write_text(json.dumps({
            "peak_working_set_bytes": result.observed_peak_working_set_bytes,
            "completed_ns": result.completed_ns, "frame_sha256": result.frame_sha256,
            "rgb_bytes": len(result.rgb), "scratch_removed": True,
        }), encoding="utf-8")
    finally:
        decoder.close()


@pytest.mark.parametrize("behavior,expected", [("flood", "child_protocol"), ("crash", "child_failed"), ("wait", "cancelled")])
def test_actual_harmless_failures_leave_zero_owned_survivors(windows_root, monkeypatch, behavior, expected):
    import threading
    from market import image_decode_windows as adapter

    fixture = windows_root / "fixture.py"
    fixture.write_text({"flood": "import os\nos.write(1, b'x' * 20000)\n",
                        "crash": "raise SystemExit(3)\n", "wait": "import time\ntime.sleep(30)\n"}[behavior])
    command = adapter._command
    def fixture_command(job):
        argv, environment = command(job)
        return argv[:4] + [str(fixture)], environment
    monkeypatch.setattr(adapter, "_command", fixture_command)
    held = []
    original = adapter.OwnedChild.start
    def start(child):
        original(child)
        held.append(child)
    monkeypatch.setattr(adapter.OwnedChild, "start", start)
    cancel = threading.Event()
    timer = threading.Timer(0.15, cancel.set)
    decoder = ImageDecoder(windows_root)
    try:
        timer.start()
        with pytest.raises(DecodeError, match=f"^{expected}$"):
            decoder.decode(request=actual_request(png()), payload=png(), cancel=cancel)
        assert len(held) == 1 and held[0].drained
        assert held[0].process is None and held[0].job.handle is None
        assert not (windows_root / "job").exists()
    finally:
        timer.join()
        decoder.close()


def test_missing_direct_membership_never_repairs_assignment(windows_root, monkeypatch):
    from market import image_decode_windows as adapter

    calls = []
    def forbidden(*args):
        calls.append(args)
        raise AssertionError("assignment repair forbidden")
    monkeypatch.setattr(adapter.PRIMITIVES.WindowsJob, "assign", forbidden)
    monkeypatch.setattr(adapter, "_membership", lambda process, job: False)
    decoder = ImageDecoder(windows_root)
    try:
        with pytest.raises(DecodeError, match="ownership"):
            decoder.decode(request=actual_request(png()), payload=png())
        assert not calls and not (windows_root / "job").exists()
    finally:
        decoder.close()


def test_actual_timeout_uses_original_acceptance_not_launch(windows_root, monkeypatch):
    from market import image_decode_windows as adapter

    fixture = windows_root / "idle.py"
    fixture.write_text("import time\ntime.sleep(30)\n")
    command = adapter._command
    def idle(job):
        argv, environment = command(job)
        return argv[:4] + [str(fixture)], environment
    monkeypatch.setattr(adapter, "_command", idle)
    now = time.perf_counter_ns()
    payload = png()
    request = DecodeRequest(INC, ID, hashlib.sha256(payload).hexdigest(), len(payload), "image/png",
                            now - 9_700_000_000, now + 300_000_000)
    decoder = ImageDecoder(windows_root)
    try:
        with pytest.raises(DecodeError, match="^timeout$"):
            decoder.decode(request=request, payload=payload)
        assert time.perf_counter_ns() - now < 2_000_000_000
        assert not (windows_root / "job").exists()
    finally:
        decoder.close()


@pytest.mark.parametrize("phase", ["suspended-launch", "resumed"])
def test_actual_parent_death_kills_bound_child_preserves_unrelated_sentinel(windows_root, phase):
    from market import image_decode_windows as adapter

    current = adapter.PRIMITIVES.WindowsProcess(os.getpid())
    try:
        executable = current.identity()["executable"]
    finally:
        current.close()
    fixture = windows_root / "idle.py"
    fixture.write_text("import time\ntime.sleep(30)\n")
    harness = windows_root / "owner.py"
    marker, release = windows_root / "identity.json", windows_root / "release"
    job = windows_root / "owned-job"
    job.mkdir()
    harness.write_text("\n".join([
        "import os, sys, json, time", "from pathlib import Path",
        f"sys.path.insert(0, {str(ROOT)!r})", f"sys.path.insert(0, {str(ROOT / 'src')!r})",
        "from market import image_decode_windows as a",
        "original = a._command", "def command(job):", "    argv, env = original(job)",
        f"    return argv[:4] + [{str(fixture)!r}], env", "a._command = command",
        "def leave(child):", "    identity = child.process.identity()",
        "    identity['membership'] = a._membership(child.process, child.job)",
        "    identity['job_pids'] = child.job.pids()",
        f"    Path({str(marker)!r}).write_text(json.dumps(identity))",
        "    deadline = time.monotonic() + 8", f"    while not Path({str(release)!r}).exists():",
        "        if time.monotonic() >= deadline: raise RuntimeError('release timeout')",
        "        time.sleep(.01)", "    os._exit(73)",
        *( ["a.OwnedChild._verify = lambda child, executable: leave(child)"] if phase == "suspended-launch" else [] ),
        f"child = a.OwnedChild(Path({str(job)!r}))", "child.start()", "leave(child)",
    ]), encoding="utf-8")
    sentinel = subprocess.Popen([executable, "-I", "-S", "-B", str(fixture)], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x8)
    owner = subprocess.Popen([executable, "-I", "-S", "-B", str(harness)], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x8)
    held = None
    try:
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline and owner.poll() is None:
            time.sleep(.01)
        assert marker.exists(), f"owner exited {owner.poll()} before identity"
        identity = json.loads(marker.read_text())
        held = adapter.PRIMITIVES.WindowsProcess(identity["pid"])
        assert held.identity()["creation_time_100ns"] == identity["creation_time_100ns"]
        assert identity["membership"] is True and identity["job_pids"] == [identity["pid"]]
        assert not held.exited() and sentinel.poll() is None
        release.write_bytes(b"go")
        assert owner.wait(timeout=3) == 73
        deadline = time.monotonic() + 3
        while not held.exited() and time.monotonic() < deadline:
            time.sleep(.01)
        assert held.exited(), "creation-time-bound child survived parent death"
        assert sentinel.poll() is None, "unrelated process must survive"
        (windows_root / "death-evidence.json").write_text(json.dumps({
            "phase": phase, "child": identity, "child_exited": held.exited(),
            "owner_exit": owner.returncode, "sentinel_alive": sentinel.poll() is None,
        }), encoding="utf-8")
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.wait(timeout=3)
        if held is not None:
            if not held.exited():
                adapter.PRIMITIVES.K.TerminateProcess(held.handle, 1)
                assert adapter.PRIMITIVES.K.WaitForSingleObject(held.handle, 3000) == 0
            held.close()
        sentinel.terminate()
        sentinel.wait(timeout=3)


@pytest.mark.parametrize("cache", ["absent", "stale"])
def test_actual_isolated_flags_environment_handle_allowlist_and_no_bytecode(windows_root, monkeypatch, cache):
    import ctypes as ct
    import msvcrt
    import py_compile
    from market import image_decode_windows as adapter

    package = windows_root / "trusted-package"
    package.mkdir()
    source = package / "fixture_module.py"
    source.write_text("VALUE = 0\n")
    if cache == "stale":
        py_compile.compile(str(source), doraise=True)
    source.write_text("VALUE = 777\n")
    before = {str(path.relative_to(package)): path.read_bytes() for path in package.rglob("*") if path.is_file()}
    fixture = windows_root / "isolation.py"
    foreign = windows_root / "unrelated-handle.bin"
    with foreign.open("xb", buffering=0) as stream:
        handle = msvcrt.get_osfhandle(stream.fileno())
        os.set_handle_inheritable(handle, True)
        fixture.write_text("\n".join([
            "import sys, os, json, ctypes as c", "from ctypes import wintypes as w",
            f"sys.path.insert(0, {str(package)!r})", "import fixture_module",
            "api = c.WinDLL('kernel32', use_last_error=True)",
            "api.WriteFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.c_void_p, c.c_void_p]",
            "api.WriteFile.restype = w.BOOL", "written = w.DWORD()",
            f"inherited = bool(api.WriteFile(w.HANDLE({handle}), b'leak', 4, c.byref(written), None))",
            "print(json.dumps(dict(isolated=sys.flags.isolated, no_site=sys.flags.no_site,",
            "    no_bytecode=sys.dont_write_bytecode, value=fixture_module.VALUE,",
            "    secret=os.environ.get('D2_TEST_SECRET'), inherited=inherited,",
            "    environment=sorted(os.environ))))",
        ]), encoding="utf-8")
        monkeypatch.setenv("D2_TEST_SECRET", "must-not-reach-child")
        monkeypatch.setenv("PYTHONPATH", "must-not-reach-child")
        command = adapter._command
        def isolate(job):
            argv, env = command(job)
            return argv[:4] + [str(fixture)], env
        monkeypatch.setattr(adapter, "_command", isolate)
        child = adapter.OwnedChild(windows_root)
        data = bytearray()
        try:
            child.start()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                block, eof, exited, code, peak, extra = child.poll()
                assert not extra and len(block) <= 4096 and len(data) + len(block) <= 4096
                data.extend(block)
                if eof and exited:
                    assert code == 0
                    break
                time.sleep(.02)
            else:
                pytest.fail("isolated child did not finish")
        finally:
            child.cleanup()
            os.set_handle_inheritable(handle, False)
    result = json.loads(data)
    assert result == dict(isolated=1, no_site=1, no_bytecode=True, value=777,
                          secret=None, inherited=False, environment=["SYSTEMROOT", "TEMP", "TMP", "WINDIR"])
    assert foreign.read_bytes() == b""
    assert {str(path.relative_to(package)): path.read_bytes() for path in package.rglob("*") if path.is_file()} == before
    assert child.drained and child.job.handle is None and child.process is None


@pytest.mark.parametrize("failure", ["drain", "process-handle"])
def test_actual_cleanup_failure_keeps_exact_remaining_handles_and_root_lock(windows_root, monkeypatch, failure):
    from market import image_decode_windows as adapter
    from market.ownership import DatabaseOwnership

    original = adapter.OwnedChild._verify
    retained = []
    restore = []
    def verify(child, executable):
        original(child, executable)
        retained.append(child)
        target, name = (child.job, "terminate_and_wait") if failure == "drain" else (child.process, "close")
        restore.append((target, name, getattr(target, name)))
        def broken():
            raise OSError("controlled cleanup fault")
        setattr(target, name, broken)
    monkeypatch.setattr(adapter.OwnedChild, "_verify", verify)
    decoder = ImageDecoder(windows_root)
    try:
        with pytest.raises(DecodeError, match="cleanup_failed"):
            decoder.decode(request=actual_request(png()), payload=png())
        assert len(retained) == 1
        child = retained[0]
        assert child.job.handle is not None and child.process.handle is not None
        assert child.drained is (failure == "process-handle")
        with pytest.raises(OSError):
            DatabaseOwnership(windows_root / "decoder")
        with pytest.raises(DecodeError, match="ownership"):
            decoder.decode(request=None, payload=None)
        for target, name, method in restore:
            setattr(target, name, method)
        decoder.close()
        assert child.drained and child.job.handle is None and child.process is None
        assert not (windows_root / "job").exists()
        ownership = DatabaseOwnership(windows_root / "decoder")
        ownership.close()
    finally:
        for target, name, method in restore:
            setattr(target, name, method)
        decoder.close()


def test_actual_junction_root_refused_without_locking_or_deleting_target(windows_root):
    target = windows_root / "target"
    target.mkdir()
    link = windows_root / "junction"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                            capture_output=True, timeout=3)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    try:
        with pytest.raises(DecodeError, match="ownership"):
            ImageDecoder(link)
        assert not list(target.iterdir())
    finally:
        link.rmdir()  # Remove this exact junction only, never the target tree.


@pytest.mark.skipif(sys.platform != "win32", reason="Windows creation-time Job ownership required")
def test_windows_adapter_is_available():
    from market import image_decode_windows

    assert callable(image_decode_windows.OwnedChild)
