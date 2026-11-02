# Getting started

[Back to the project overview](../README.md)

Run commands from the repository root. The required tools are a manual
prerequisite: this repository does not contain a tool-download/bootstrap script.
The Windows setup was exercised with Python **3.12.14**, uv **0.12.15**, Zig
**0.16.0**, and Node.js **25.9.0**. Obtain uv and Node.js from their upstream
distributions; on Windows, also obtain the Zig 0.16.0 x86_64 Windows archive.
Keep these versions when reproducing that environment.
The replay viewer was checked separately with Node **24.21.0** / npm **11.19.0**;
its package declares Node >=24. The older Node 25.9.0 observation belongs to the
native/data setup, not the viewer acceptance result.

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

## Download, verify, stage and prepare

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
The same flag also enables the complete eight-cohort native assay test and the
96-unit/144-point native grid prefix/seal test. Running all of pytest with this
flag includes those long integrations as well as the graph cases. They use
declared tiny native fixtures where stated; passing them is not formal MaleCNS
qualification or a whole-assay capacity measurement.
Local chat notes and visual references remain outside Git.

## Measured observation and local replay

The observation recorder/exporter and viewer source are implemented and reviewed;
bounded real-file browser/sample/video terminal-frame checks passed. Experimental
WIP remains in frame pacing/export precision and broader accessibility/browser checks. The
[recorded fullgraph checkpoint](experiments/2026-11-02-measured-replay-observation.md)
contains the exact current results and limitations. Existing local UI work must
reuse `runs/measured-replay-v1-fullgraph.json`, rather than record another run.
That generated file is ignored and is absent in a fresh checkout.

To create your own recording after completing the graph preparation above:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli observe --output-dir runs/my-observation --seed 11 --cycles 3
.venv/Scripts/python.exe -m fly_connectome_sim.cli verify-run runs/my-observation
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-replay runs/my-observation --output runs/my-replay.json
```

On Linux/macOS, replace `.venv/Scripts/python.exe` with `.venv/bin/python`.
`observe` constructs the actual prepared-graph engine. It defaults to seed 11 and
three A/black/B/black cycles, 500ms per observation; cycles 1–10 and integer
seeds 0–4294967295 are supported. Every call has no external stimulation,
learning=False and both detail flags False. Black frames advance neural time.
This is a reward-free observation protocol, not a training assay.

Both output paths must be new. The export must be outside the source artifact;
neither command overwrites an existing output. Runs, checkpoints, compact pixel
exports and generated videos stay in ignored locations such as `runs/`.
`verify-run` and the source's stored `integrity-only` mode check artifact
integrity; the compact file does not provide native-history attestation.

Install the locked viewer dependencies and start the local viewer from the
repository root (use `npm.cmd` instead of `npm` if PowerShell blocks npm.ps1):

```powershell
npm --prefix viewer ci
npm --prefix viewer test
npm --prefix viewer run build
npm --prefix viewer run dev
```

Open the localhost URL printed by Vite, then **Open recording** and choose the
exported JSON. The viewer reads the file locally; it has no upload, model call
or fabricated activity fallback. The fly/pose is illustrative, not measured
anatomy or tracked movement. Its telemetry uses the recorded integer bin counts,
actual population and bin duration without smoothing. Video export is
feature-detected; one Chrome WebM was decoded and its final measured overlay
checked. Browser capture is not an exact 12s/30fps export guarantee. Foreground
frame pacing, export precision and broader accessibility/browser checks remain.

For a built preview, use `npm --prefix viewer run preview` after the build.
Unix/native reproduction and browser capture availability require their own
checks; current evidence is from the Windows environment described above.

## Separate assay commands

The existing qualification command remains separate from Replay v1 and is not
needed to record or view observations. Formal execution remains gated by the
assay plan. Qualification is not a positive assay result or a production
frozen configuration. Its output directory must not already exist.

After preparing and verifying the graph, on Windows:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli qualify --output-dir runs/qualification
.venv/Scripts/python.exe -m fly_connectome_sim.cli verify-run runs/qualification
```

On Linux/macOS, replace `.venv/Scripts/python.exe` with `.venv/bin/python`.
`verify-run` checks integrity only; native replay verification is a separate
Python API path. Native cohort production is currently exposed through Python
APIs; the `assay` CLI and LLM event planner remain pending. Replay's recorder and
renderer source passed the bounded real-file/video-end check and remain experimental WIP.

See the [assay implementation plan](superpowers/plans/2026-09-24-associative-plasticity-assay.md)
for the current scientific milestone and verification details.
