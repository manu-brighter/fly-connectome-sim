"""Explicit harmless transport fixture; finite exit, no application imports."""
import json
import os
import struct
import subprocess
import sys
import time
import threading

watchdog = threading.Timer(12, lambda: os._exit(97))
watchdog.daemon = True
watchdog.start()

mode = sys.argv[1]
if mode in ("echo", "echo_slow"):
    prefix = os.read(0, 4)
    if len(prefix) == 4:
        length = struct.unpack("<I", prefix)[0]
        body = b""
        while len(body) < length:
            body += os.read(0, min(4096, length - len(body)))
        json_length = struct.unpack("<I", body[:4])[0]
        message = json.loads(body[4:4 + json_length])
        message.update(type="clock", child_ns=2)
        encoded = json.dumps(message, sort_keys=True, separators=(",", ":")).encode()
        body = struct.pack("<I", len(encoded)) + encoded
        output = struct.pack("<I", len(body)) + body
        if mode == "echo_slow":
            for offset in range(0, len(output), 7):
                os.write(1, output[offset:offset + 7])
                time.sleep(0.005)
        else:
            os.write(1, output)
elif mode == "partial":
    os.write(1, b"\x20\x00")
elif mode == "oversize":
    os.write(1, struct.pack("<I", 2097153))
elif mode == "midframe":
    os.write(1, struct.pack("<I", 100) + b"x")
    time.sleep(8)
elif mode == "nonzero":
    raise SystemExit(9)
elif mode == "stderr":
    os.write(2, b"x" * 70000)
    time.sleep(8)
elif mode == "descendant":
    subprocess.Popen([sys.executable, "-I", "-S", "-c", "import time; time.sleep(8)"])
    time.sleep(8)
elif mode == "sleep":
    time.sleep(8)
elif mode == "pair":
    from pathlib import Path
    payload = Path("exchange-frames.bin").read_bytes()
    # Both frames precede the only read. A parent ACK between them cannot be
    # necessary to make the complete frame available, including observation39.
    for offset in range(0, len(payload), 4096):
        os.write(1, payload[offset:offset + 4096])
    prefix = os.read(0, 4)
    if len(prefix) == 4:
        length = struct.unpack("<I", prefix)[0]
        body = b""
        while len(body) < length:
            body += os.read(0, length - len(body))
        command = json.loads(body[4:])
        Path("exchange-command.json").write_text(json.dumps(command))
        if command["action"] == "end":
            os.write(1, Path("exchange-ended.bin").read_bytes())
elif mode == "handles":
    import ctypes as ct
    from ctypes import wintypes as wt
    from pathlib import Path
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    kernel.GetConsoleWindow.restype = wt.HWND
    kernel.GetHandleInformation.argtypes = [wt.HANDLE, ct.POINTER(wt.DWORD)]
    flags = wt.DWORD()
    try:
        visible = bool(kernel.GetHandleInformation(int(Path("unlisted-handle.txt").read_text()), ct.byref(flags)))
    except OSError as error:
        if error.winerror not in (6, -1073741816):
            raise
        visible = False
    proof = dict(console_window=int(kernel.GetConsoleWindow() or 0), unlisted_handle_visible=visible)
    Path("handle-proof.json").write_text(json.dumps(proof))
elif mode != "probe_host":
    raise SystemExit(4)


if mode == "probe_host":
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    sys.path.insert(1, str(Path(__file__).resolve().parents[3] / "src"))
    from market.native_windows import CompilerProbeGuard, NativeTransportError
    data = json.loads(Path("probe-binding.json").read_text(encoding="utf-8-sig"))
    sequence = [0]
    def exchange(kind, fields):
        value = dict(schema="market-native-ipc/v1", type=kind, seq=sequence[0],
                     incarnation=data["incarnation"], worker_session=data["worker_session"],
                     protocol_sha256=data["protocol_sha256"], launch_nonce="b" * 64, **fields)
        sequence[0] += 1
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        body = struct.pack("<I", len(encoded)) + encoded
        output = struct.pack("<I", len(body)) + body
        if mode == "echo_slow":
            for offset in range(0, len(output), 7):
                os.write(1, output[offset:offset + 7])
                time.sleep(0.005)
        else:
            os.write(1, output)
        if kind == "probe_request":
            prefix = os.read(0, 4)
            length = struct.unpack("<I", prefix)[0]
            body = b""
            while len(body) < length:
                body += os.read(0, length - len(body))
            return json.loads(body[4:])
    guard = CompilerProbeGuard(data, exchange, _test_argv=data["compiler_probe"]["argv"])
    try:
        guard.install()
        command = data["compiler_probe"]["argv"]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        if command[-1] == "duplicate":
            subprocess.run(command, check=True, capture_output=True, text=True)
        if command[-1] == "unexpected":
            subprocess.Popen(command)
        if command[-1] == "mutate":
            Path(data["files"]["native_library"]["path"]).write_bytes(b"changed")
            guard.verify_cache()
    except NativeTransportError as error:
        exchange("fault", dict(code=error.code, phase="probe", observation_index=None,
                               dispatch_id=None, wall_ns=time.perf_counter_ns(), observations_completed=0))
    finally:
        guard.close()
