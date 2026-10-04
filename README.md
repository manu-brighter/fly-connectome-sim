# Fly Connectome Sim

A reproducible experiment in which an LLM proposes event ideas and a simulated
fruit-fly connectome influences which ideas survive.

The project uses the released MaleCNS v1.0 wiring graph. It does not claim to
simulate a complete living fly, consciousness, dopamine concentration, receptor
occupancy or semantic understanding. Physiology, learning and action mappings
are explicit model choices and are tested against controls.

## Current milestone

The first milestone is a controlled A/B associative-plasticity assay:

1. present two synthetic visual stimuli;
2. pair one stimulus with explicit PPL101 stimulation;
3. test A/B and a neutral C probe without external stimulation;
4. compare matched controls and candidate-memory interventions at two retention
   times using a frozen MBON11 response endpoint;
5. store an immutable event stream for later 3D replay.

Product scope is defined in
[`docs/specs/fly-event-planner.md`](docs/specs/fly-event-planner.md). The current
scientific milestone and claim boundaries are defined by the
[`associative-plasticity design`](docs/superpowers/specs/2026-09-24-associative-plasticity-pivot-design.md)
and its [`implementation plan`](docs/superpowers/plans/2026-09-24-associative-plasticity-assay.md).

### WIP status — 2026-10-04

- MaleCNS v1.0 sources are checksum-locked and the prepared graph verifies at
  166,700 cells and 25,582,938 directed edges.
- The attributed numerical core builds as a Windows DLL through the
  project-local Zig toolchain.
- `FlyEngine` exposes explicit PAM11/PPL101 stimulation and measured KC,
  MBON07, MBON11 and DNa02 telemetry.
- Checkpoint restore, canonical complete-state hashes and full-graph reset
  determinism are tested. Hashing uses bounded array buffers without writing
  checkpoints. Synthetic stimuli, counterbalanced protocols, pathway telemetry
  and atomic candidate-memory interventions are implemented.
- Live candidate/noncandidate content hashes bind the exact selected memory
  triplet and all other state in separate domains, with complete-state validation
  before exclusions and bounded numeric encoding. Content equality is not donor
  history, current-group identity or clock-compatibility proof; native intervention
  production verifies those separately against authenticated training sources.
- Exploratory qualification and append-only verified artifacts are available
  through `qualify` and `verify-run`. The pure frozen-config builder and MBON11
  analysis contract are implemented and independently reviewed.
- Durable-rooted black-retention anchors, immutable fixed prefixes and actual
  isolated native replay attestations are implemented. Ordinary `verify-run`
  remains integrity-only; full assay/CLI integration is still pending.
- Validated-prefix and sealed scientific reports share provenance/inventory gates,
  actual verification-mode and used-anchor labels. A real partial native artifact
  preserves its canonical report through terminal append and sealing; missing
  assay cells still classify it as inconclusive, not a positive assay result.
- A bounded paired-cohort producer executes real training and independent A/B/C
  baseline and retained trials, records twelve response descriptors and two
  retained-parent anchors, then native-verifies both prefix and sealed reports.
  Its incomplete tiny native correctness pilot remains inconclusive; the declared
  test contract is not qualification evidence or a production frozen config.
- A five-route cohort adds independently acquired matched reference, necessity,
  sufficiency and sham. Actual replacements bind authenticated training-end
  occurrences and preserve noncandidate state. Two trainings, three interventions,
  sixty response descriptors and ten retained-parent anchors pass the same native
  prefix/terminal/sealed lifecycle; missing factors and controls remain visible.
- In progress: selected qualification interventions, all-factor held-out assay
  production, remaining control routes and the `assay` CLI.
  Formal full-graph qualification
  and confirmation have not run; no positive plasticity or behavior result is
  claimed.
- Still to add: a separately labelled, unvalidated motor readout. Verified
  offline 3D replay and LLM event planning follow the scientific gate. The
  current MBON11 endpoint does not establish a learned left/right preference.

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
