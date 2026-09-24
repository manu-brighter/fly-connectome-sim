# Fly Connectome Sim

A reproducible experiment in which an LLM proposes event ideas and a simulated
fruit-fly connectome influences which ideas survive.

The project uses the released MaleCNS v1.0 wiring graph. It does not claim to
simulate a complete living fly, consciousness, dopamine concentration, receptor
occupancy or semantic understanding. Physiology, learning and action mappings
are explicit model choices and are tested against controls.

## Current milestone

The first milestone is a controlled A/B learning assay:

1. present two synthetic visual stimuli;
2. pair one stimulus with an explicit dopaminergic-neuron input;
3. test both without reward;
4. compare trained, untrained, frozen and temporally unpaired runs;
5. store an immutable event stream for later 3D replay.

Product scope and evidence rules are defined in
[`docs/specs/fly-event-planner.md`](docs/specs/fly-event-planner.md).

### WIP status — 2026-09-16

- MaleCNS v1.0 sources are checksum-locked and the prepared graph verifies at
  166,700 cells and 25,582,938 directed edges.
- The attributed numerical core builds as a Windows DLL through the
  project-local Zig toolchain.
- `FlyEngine` exposes explicit PAM11/PPL101 stimulation and measured KC,
  MBON07, MBON11 and DNa02 telemetry.
- A full-graph test produces identical neural output after a complete reset.
- Next: freeze the A/B protocol and preference adapter, then run trained and
  matched control assays. No learning result is claimed yet.

## Fresh checkout setup

Run commands from the repository root. The required tools are a manual
prerequisite: this repository does not contain a tool-download/bootstrap script.
The Windows setup was exercised with Python **3.12.14**, uv **0.12.15**, Zig
**0.16.0**, and Node.js **25.9.0**. Obtain uv and Node.js from their upstream
distributions; on Windows, also obtain the Zig 0.16.0 x86_64 Windows archive.
Keep these versions when reproducing that environment.

On Windows, extract uv to `.tools/uv/uv.exe` and Zig so that its executable is
`.tools/zig/zig-x86_64-windows-0.16.0/zig.exe`. Those ignored directories are
absent in a fresh checkout. Then install the pinned Python and dependencies:

```powershell
.tools/uv/uv.exe --version
.tools/zig/zig-x86_64-windows-0.16.0/zig.exe version
node --version
.tools/uv/uv.exe python install 3.12.14 --install-dir .tools/python --no-bin --no-registry --cache-dir .tools/uv-cache
.tools/uv/uv.exe sync --locked --extra test --cache-dir .tools/uv-cache --python .tools/python/cpython-3.12.14-windows-x86_64-none/python.exe
```

On Linux/macOS, install uv and Node.js on `PATH`, plus your platform's C++17
toolchain exposing `c++`. No Unix compiler version is pinned or locally verified
yet; retain the exact compiler version recorded in the native build metadata for
reproduction on that platform. The existing Unix build path uses `c++`, while
Windows selects the project-local Zig above. `FLY_CONNECTOME_SIM_CXX` can override either
with an absolute executable path.

```sh
uv --version
node --version
c++ --version
export UV_PYTHON_INSTALL_DIR="$PWD/.tools/python"
uv python install 3.12.14 --no-bin --cache-dir .tools/uv-cache
uv sync --locked --extra test --cache-dir .tools/uv-cache --python 3.12.14
```

### Download, verify, stage and prepare

The three source tables come from the
[official HHMI Janelia release](https://male-cns.janelia.org/download/).
Allow space for the 1.1 GB download plus normalized and prepared outputs. Staging
uses hard links, so source and runtime directories must share a filesystem.
Raw and runtime data stay outside Git.

On Windows, after the dependency sync above:

```powershell
node scripts/download-connectome.mjs
.venv/Scripts/python.exe -m fly_connectome_sim.data verify-sources data/malecns-v1.0
.venv/Scripts/python.exe -m fly_connectome_sim.data stage data/malecns-v1.0
.venv/Scripts/python.exe -m fly_connectome_sim.neural.connectome malecns_v1
.venv/Scripts/python.exe -m fly_connectome_sim.neural.prepare
.venv/Scripts/python.exe -m fly_connectome_sim.data verify-prepared
.venv/Scripts/python.exe -m pytest
```

On Linux/macOS, run the same sequence with `.venv/bin/python` in place of
`.venv/Scripts/python.exe`. The downloader checks the released object generation,
size and MD5; `verify-sources` checks the manifest's SHA-256 values. The importer
then requires every staged file's URL, size and SHA-256 to match the packaged
`neural/sources.lock.json` before writing outputs. Runtime verification also
checks those source files, including annotations, as well as the locked arrays
and normalized neuron metadata. `FlyEngine.from_prepared_graph()` runs this gate
before constructing the brain. A local `source.lock.json` is only an audit copy.

The default runtime directory is `data/malecns-v1.0/runtime`. To use a different
directory, set `FLY_CONNECTOME_SIM_DATA` before staging and keep it set for import,
preparation, verification and execution. Use `$env:FLY_CONNECTOME_SIM_DATA='D:/fly/runtime'`
in PowerShell or `export FLY_CONNECTOME_SIM_DATA=/path/to/runtime` in a POSIX shell. The
stage and verify-prepared commands also accept `--runtime-directory PATH`;
the environment variable remains necessary for the numerical core. Python reads
it when the neural modules are first imported.

The normal suite verifies the data and compiles/loads the native kernel. The
complete graph simulation test is opt-in because it loads and advances the graph:

```powershell
$env:FLY_CONNECTOME_SIM_FULL_TEST='1'
.venv/Scripts/python.exe -m pytest tests/test_full_graph_engine.py
```

On Linux/macOS: `FLY_CONNECTOME_SIM_FULL_TEST=1 .venv/bin/python -m pytest tests/test_full_graph_engine.py`.
Local chat notes and visual references remain outside Git.

## Provenance

The numerical core is adapted from MIT-licensed Stonkfly/DOOMFLY work through a
checksum-pinned Fly/Wirehead revision. Its notice and exact revisions are kept in
`THIRD_PARTY.md` and `licenses/`. MaleCNS data is distributed separately under
CC BY 4.0; see the official project page for attribution and citation details.
