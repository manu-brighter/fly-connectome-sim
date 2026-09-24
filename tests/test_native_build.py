import ctypes
from pathlib import Path

from fly_connectome_sim.neural.native import build_native, library_filename


PROJECT_ROOT = Path(__file__).parents[1]


def test_platform_compiler_produces_loadable_kernel_with_exported_entrypoint(tmp_path):
    source = (
        PROJECT_ROOT
        / "src"
        / "fly_connectome_sim"
        / "neural"
        / "kernel.cpp"
    )

    build = build_native(source=source, output_directory=tmp_path)

    library = tmp_path / library_filename()
    assert build["library"] == library.name
    assert build["source_sha256"]
    assert build["binary_sha256"]
    assert getattr(ctypes.CDLL(str(library)), "memory_advance")
