"""Build the audited C++ neural kernel on the current platform."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def library_filename() -> str:
    if sys.platform == "win32":
        return "memory.dll"
    if sys.platform == "darwin":
        return "libmemory.dylib"
    return "libmemory.so"


def library_path(output_directory: Path | str) -> Path:
    return Path(output_directory) / library_filename()


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _default_compiler() -> Path | str:
    configured = os.environ.get("FLY_CONNECTOME_SIM_CXX")
    if configured:
        return Path(configured)
    if sys.platform == "win32":
        local_zig = (
            Path.cwd()
            / ".tools"
            / "zig"
            / "zig-x86_64-windows-0.16.0"
            / "zig.exe"
        )
        if local_zig.is_file():
            return local_zig
        zig = shutil.which("zig")
        if zig:
            return zig
        raise RuntimeError(
            "No Windows C++ compiler found; set FLY_CONNECTOME_SIM_CXX or install the "
            "project-local Zig toolchain"
        )
    compiler = shutil.which("c++")
    if not compiler:
        raise RuntimeError("No C++17 compiler found")
    return compiler


def build_native(
    source: Path | str,
    output_directory: Path | str,
    compiler: Path | str | None = None,
) -> dict[str, object]:
    """Build once per source/compiler configuration and verify cached output."""

    source_path = Path(source).resolve()
    output = Path(output_directory).resolve()
    library = library_path(output)
    metadata = library.with_suffix(library.suffix + ".json")
    source_hash = _digest(source_path)
    selected = Path(compiler or _default_compiler()).resolve()
    is_zig = selected.name.lower() in {"zig", "zig.exe"}

    flags = ["-O3", "-std=c++17", "-shared"]
    if sys.platform == "win32":
        flags.append("-Wl,--export-all-symbols")
    else:
        flags.append("-fPIC")
    command = [str(selected), *( ["c++"] if is_zig else [] ), *flags]
    compiler_id = subprocess.run(
        [str(selected), "version"] if is_zig else [str(selected), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().splitlines()[0]

    expected = {
        "source_sha256": source_hash,
        "compiler": compiler_id,
        "flags": flags,
        "library": library.name,
    }
    if library.is_file() and metadata.is_file():
        record = json.loads(metadata.read_text(encoding="utf-8"))
        if all(record.get(key) == value for key, value in expected.items()):
            if record.get("binary_sha256") == _digest(library):
                return record

    output.mkdir(parents=True, exist_ok=True)
    temporary = library.with_stem(f"{library.stem}.partial")
    environment = os.environ.copy()
    if is_zig:
        environment.setdefault("ZIG_GLOBAL_CACHE_DIR", str(output / "zig-global-cache"))
        environment.setdefault("ZIG_LOCAL_CACHE_DIR", str(output / "zig-local-cache"))
    subprocess.run(
        [*command, str(source_path), "-o", str(temporary)],
        check=True,
        env=environment,
    )
    temporary.replace(library)
    record = {**expected, "binary_sha256": _digest(library)}
    temporary_metadata = metadata.with_suffix(metadata.suffix + ".partial")
    temporary_metadata.write_text(
        json.dumps(record, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary_metadata.replace(metadata)
    return record
