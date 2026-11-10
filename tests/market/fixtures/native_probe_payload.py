"""A finite harmless substitute for a version executable, never a compiler."""
import os
from pathlib import Path
import sys
import time

import ctypes as ct
import json
kernel = ct.WinDLL("kernel32", use_last_error=True)
kernel.GetConsoleWindow.restype = ct.c_void_p
Path(os.environ["TMP"]).joinpath("probe-hidden.json").write_text(json.dumps(dict(console_window=int(kernel.GetConsoleWindow() or 0))))
mode = sys.argv[1]
if mode == "timeout":
    time.sleep(7)
elif mode == "flood":
    os.write(1, b"x" * 5000)
elif mode == "badversion":
    os.write(1, b"wrong\n")
else:
    os.write(1, b"0.16.0\n")
