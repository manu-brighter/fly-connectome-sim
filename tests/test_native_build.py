import ctypes
from pathlib import Path

from jogge_fly_brain.neural.native import build_native, library_filename


PROJECT_ROOT = Path(__file__).parents[1]


def test_zig_build_produces_loadable_kernel_with_exported_entrypoint(tmp_path):
    compiler = (
        PROJECT_ROOT
        / ".tools"
        / "zig"
        / "zig-x86_64-windows-0.16.0"
        / "zig.exe"
    )
    source = (
        PROJECT_ROOT
        / "src"
        / "jogge_fly_brain"
        / "neural"
        / "kernel.cpp"
    )

    build = build_native(source=source, output_directory=tmp_path, compiler=compiler)

    library = tmp_path / library_filename()
    assert build["library"] == library.name
    assert build["source_sha256"]
    assert build["binary_sha256"]
    assert getattr(ctypes.CDLL(str(library)), "memory_advance")
