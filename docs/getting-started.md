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

## Clean-checkout compatibility

The [GitHub Actions workflow](../.github/workflows/compatibility.yml) has two
independent Ubuntu 24.04 jobs, triggered by feature pushes, pull requests or
manual dispatch. It pins uv 0.12.15, Python 3.12.14 and Node 24.21.0, installs
locked dependencies, and records the runner image, tool/compiler versions and
the actual checkout's source fingerprint. The first actual
[hosted Linux acceptance](experiments/2026-11-07-clean-checkout-ci.md) passed
142 Python tests with one Windows-only skip, plus 97 viewer tests/build.
The system C++17 compiler and runner image are not pinned.

For the Python job's local equivalent, use a fresh checkout/export with no
installed project environment or runtime data, and the prerequisites above.
The data directory below must not already exist. Set it before Python imports:

```sh
unset FLY_CONNECTOME_SIM_FULL_TEST FLY_CONNECTOME_SIM_CXX PYTHONPATH PYTHONHOME
export FLY_CONNECTOME_SIM_DATA="$PWD/.tools/ci/runtime"
mkdir -p .tools/ci
mkdir "$FLY_CONNECTOME_SIM_DATA"
uv sync --locked --extra test --extra media --python 3.12.14
uv run --no-sync python - <<'PY'
import json
import os
from pathlib import Path

runtime = Path(os.environ["FLY_CONNECTOME_SIM_DATA"]).resolve()
assert runtime.is_dir() and not any(runtime.iterdir()), runtime
import av
import fly_connectome_sim
from fly_connectome_sim.neural.checkpoint import model_fingerprint
from fly_connectome_sim.neural.common import DATA

assert Path(fly_connectome_sim.__file__).resolve() == (Path.cwd() / "src/fly_connectome_sim/__init__.py").resolve()
assert DATA == runtime
print(f"PyAV: {av.__version__}")
print(json.dumps(model_fingerprint(), sort_keys=True))
PY
uv run --no-sync pytest -q tests/test_native_build.py tests/test_checkpoint.py::test_evolved_emitted_checkpoint_replays_with_native_kernel tests/experiment/test_replay.py::test_native_qualification_context_maps_and_single_factory tests/experiment/test_session_workflow.py tests/experiment/test_recorder_limits.py tests/test_cli.py
```

This explicitly requires PyAV and exercises native compilation/loading, evolved
checkpoint continuation, tiny qualification context, session/recorder limits
and CLI behavior. It downloads no MaleCNS data and does not run the general
data-dependent suite or opt-in fullgraph cases. On Windows use PowerShell
environment syntax and the documented Zig compiler; record the selected tool
versions separately from hosted Linux results.

The viewer job runs these commands under `viewer/` with Node 24.21.0:

```sh
node --version
npm --version
npm ci
npm test
npm run build
```

Neither job restores dependency caches, uploads artifacts, deploys or accesses
secrets. Passing compatibility checks does not establish native-history
attestation, scientific qualification, fullgraph capacity, macOS/hosted Windows
support, live API compatibility, or browser/video-encoding acceptance.

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
real-file measurement checks remain valid. The previous end-pixel video check
did not establish smooth animation (17 frames/13.326s). Phase 1 now uses explicit
frame timestamps and illustrative motion; one actual export decoded 375 frames
at 30fps scheduling. Genuine-video input and recorded motor-driven feed actions
now have a separate [bounded actual pilot](experiments/2026-11-02-video-feed-observation.md)
and [commands below](#local-video-observation-and-recorded-feed-actions). The
[recorded fullgraph checkpoint](experiments/2026-11-02-measured-replay-observation.md)
contains historical A/B results and limitations. A/B-specific local UI work must
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
actual population and bin duration without smoothing. **Export video** now
encodes 900x900 frames sequentially at explicit 30fps timestamps, with progress
and cancellation; it requires supported WebCodecs encoding and reports failure
without a real-time fallback. For 12s of data it writes 360 source samples plus 15
labelled terminal-hold frames (12.5s media total). The hold advances no simulation
time. Interactive pause/seek reproduce an absolute-time illustrative pose;
reduced motion is respected. No pose is a measured motor trajectory.

An actual exported file was independently decoded and its375 frames/33–34ms
container timestamps checked. This does not guarantee live-browser frame pacing
or every browser/codec combination. The historical A/B measurements remain
separate from the new genuine-video protocol; never pair reel footage with
those A/B measurements. See the [current product plan](superpowers/plans/2026-11-02-fast-reel-feed.md).

Event-choice recordings use the same viewer, with a landscape board and a bound
plan revealed only at the final recorded decision. Their 2s source recording has
90 labelled terminal-hold frames, producing a 150-frame/5s video at30fps. The
hold advances no simulation time; older formats retain their15-frame hold.

For a built preview, use `npm --prefix viewer run preview` after the build.
Unix/native reproduction and browser capture availability require their own
checks; current evidence is from the Windows environment described above.

### Keyboard replay controls

Tab to the replay canvas to use **Space** for play/pause, **Left/Right** for100ms
steps, **Home** for the beginning and **End** for the terminal sample. Controls
are inactive while loading/exporting; modified shortcuts retain browser behavior.
Buttons, speed selection and timeline keep their normal keyboard controls.
Visible help sits below the measured image. A polite live region announces clip,
pending and selected/deferred phase changes without repeating on every frame;
reverse seeking restores the earlier phase. Full assistive-technology testing
remains open; see the [acceptance note](experiments/2026-11-06-replay-controls.md).

## Local video observation and recorded feed actions

For genuine video input, install the optional locked decoder after the graph
preparation above:

```powershell
.tools/uv/uv.exe sync --locked --extra media --extra test --cache-dir .tools/uv-cache
```

Create an ignored local playlist JSON with one to five ordered local files:

```json
[
  {"path":"C:/media/first-reel.mp4","source_url":"https://www.instagram.com/reel/DcTiO6Ls3HT/"},
  {"path":"C:/media/second-reel.mp4","source_url":"https://www.instagram.com/reel/DZHp4mtNvJb/"}
]
```

Paths identify actual local decoder inputs; URLs are provenance labels. The
command downloads nothing and reads no browser cookies. With `fast-feed`, each
source must cover its complete first **20 seconds**. Preparation hashes the
source and declares 120 exact 90x160 RGB frames sampled at media time `5*j/30`,
selected source PTS and decoder/resize recipe before engine construction.
Audio is not neural input. Short sources are rejected; no padding or looping.

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli observe-video --profile fast-feed --playlist runs/my-playlist.json --output-dir runs/my-fast-video-observation
.venv/Scripts/python.exe -m fly_connectome_sim.cli verify-run runs/my-fast-video-observation
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-video-replay runs/my-fast-video-observation --output runs/my-fast-video-replay.json
```

Omitting `--profile` (or using `--profile standard`) preserves the original
1×/v1 protocol: full first **4 seconds** of each source and 1s minimum dwell.
Fast-feed uses the closed v2 protocol with 5× source sampling and 3s minimum
dwell. Both have a 4s clip cap/8s session cap; simulation advances at normal
30Hz with no external stimulation, `learning=False` and normal passive evolution.

Choose the exported JSON through **Open recording** in the same viewer.
Both `measured-video-replay/v1` and `/v2` show actual fed portrait frames,
media PTS and recorded policy; original A/B `measured-replay/v1` remains supported.
`Reel 5×` describes media sampling, independently of native simulation time and
Replay Speed. Outputs must be new and ignored. Unix uses `.venv/bin/python`;
that platform needs its own native/decoder verification.

The engineered right-scroll policy uses actual 300ms lateral motor counts,
evaluated every 100ms. After the profile's minimum dwell, `inspect_right` may
advance; left/defer watches. The 4s clip-window limit can also advance, explicitly
labelled external. A recorded ADVANCE starts a 200ms illustrative swipe using
the last fed outgoing frame and current actual incoming frame. The composite
and foreleg gesture are presentation, not extra neural input or measured limb
motion. STOP does not swipe; reduced motion immediately shows incoming input.
No semantic reaction, learned preference or validated biological behavior is claimed.

For current local UI work, reuse the validated fast-feed artifact
`runs/measured-video-replay-fast-reels-20261102.json`. Its bounded actual
runtime/raw/Chrome/encoded-file acceptance passed. The [fast-feed report](experiments/2026-11-02-fast-reel-feed-observation.md)
and [handover](cloud-handover.md) record current results/limitations. The earlier
[3.5s standard-video pilot](experiments/2026-11-02-video-feed-observation.md)
is separate historical 1× evidence. A fresh checkout must provide its missing
sources/runtime/recording. See the [fast-feed contract](superpowers/specs/2026-11-02-fast-reel-feed.md).

## Local event proposals and measured selection

After the graph/toolchain setup, use the authored example or prepare a strict
proposal with the [copyable prompt](event-proposal-prompt.md). No API key,
live LLM call or API charge is involved. Example budgets are not verified offers.

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli event-choice --proposal examples/event-options.json --output-dir runs/my-event-choice
.venv/Scripts/python.exe -m fly_connectome_sim.cli verify-run runs/my-event-choice
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-event-replay runs/my-event-choice --output runs/my-event-replay.json
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-event-plan runs/my-event-choice --output runs/my-event-plan.json
```

Use new output paths; existing files/runs are never replaced. Four500ms calls
feed the same actual paired384x216 RGB image to a fresh engine, without external
stimulation or learning. The first1500ms settle; the final500ms integer lateral
motor counts determine left/right/defer at2s with the existing strict1Hz policy.
There is no winner override and no automatic retry to obtain a selection.

Open `runs/my-event-replay.json` in the viewer. Pending has no selected plan;
at2s the selected proposal appears unchanged, or the viewer reports deferred.
**Download bound plan** exports that same recorded object, including its source
and decision references. This fresh pilot does not continue reel history or
establish semantic understanding, visual specificity or learned behavior.

The exporter checks sealed integrity and complete semantic consistency; it does
not attest native execution history. The event and continuous-session replay/plan
exporters apply fixed read limits before parsing raw input:2MiB manifest,1MiB per
JSONL line including LF,2 checkpoint entries, and6 events/8MiB stream for standalone
choice or246 events/64MiB for continuous sessions. Exact caps still require normal
EOF and all original integrity/semantic checks. Limits persist through second
passes and final rechecks; no automatic unlimited fallback is available.
These are operational intake ceilings, not a process-memory/CPU guarantee or
complete hostile-filesystem safety. Generic `verify-run`, producers, prefix APIs
and other exporters retain their previous behavior and are intended for your own
controlled artifacts. Proposal and compact replay readers have their own bounds.
See the [bounded intake plan](superpowers/plans/2026-11-07-bounded-event-intake.md)
and the
[contract](superpowers/specs/2026-11-02-event-choice-milestone.md) for the trust model.

## Continuous reels and event choice

Use a local playlist prepared as above and the same strict event proposal file.
The one-command workflow constructs one fresh engine and retains it through both
phases, then exports the replay and plan automatically:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli run-session --playlist runs/my-playlist.json --proposal examples/event-options.json --output-dir runs/my-session
.venv/Scripts/python.exe -m fly_connectome_sim.cli inspect-session runs/my-session
```

The parent directory must already exist; `my-session` must be new. It contains
`run/` (the sealed raw artifact), `recording.json` (open this in the viewer),
`plan.json` and `receipt.json`. The inspector prints completion, selected/deferred
status/title, global duration/feed ticks, final-window motor counts and file paths.
It derives the outputs from the bounded raw verifier without constructing an
engine, calling a provider or writing files. Keep `run/` alongside the outputs for
inspection. The compact recording alone remains sufficient for viewer playback.

A missing, truncated or inconsistent receipt is incomplete/invalid. Hashes alone
are insufficient: inspection checks exact canonical exports against the raw
semantic derivation. A valid receipt records local completion, not native-history
or scientific attestation. Deferred choice is a valid completed result.

Failures retain the directory and name the failed stage; no automatic retry,
cleanup, replacement or resume occurs. Input validation still belongs to the
existing recorder, so invalid input can leave an empty reserved directory without
constructing an engine. If recording sealed but a later export failed, recover
manually using the existing export commands below and fresh destination paths.
Do not rerun run-session into an existing directory or treat a partial tree as
completed. No atomic snapshot of every file or crash-durability guarantee is made.

The component commands remain available for diagnosis and manual export:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli feed-event-session --playlist runs/my-playlist.json --proposal examples/event-options.json --output-dir runs/my-feed-event-session
.venv/Scripts/python.exe -m fly_connectome_sim.cli verify-run runs/my-feed-event-session
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-session-replay runs/my-feed-event-session --output runs/my-session-replay.json
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-session-plan runs/my-feed-event-session --output runs/my-session-plan.json
```

Open `runs/my-session-replay.json` in the same viewer. The phone shows the actual
5×-sampled feed, with its recorded motor policy and illustrative foreleg swipe.
At the feed's recorded STOP tick T, the same native state immediately observes
the event cards for2s. There is no reset, restore, replacement engine or hidden
simulation gap. The first1.5s of cards settle; final0.5s counts select/defer with
the unchanged1Hz rule. The plan appears only at T+2s, unchanged from its proposal.
Backward seek restores the corresponding phase and hides later results.

The feed lasts at most8s, cards exactly2s, with no external stimulation or
learning. The8s session cap takes priority over minimum clip dwell; a third clip
can therefore end after2s. Export adds one labelled3s terminal plan hold, with
global30fps timestamps and no hold at the feed/cards boundary. It adds no neural
measurements. During that hold, the fly makes one illustrative tap on the
selected card and retracts; defer makes no tap. Interactive event/session replay
uses the same presentation hold, while simulation time and rates remain fixed.
Pause freezes the gesture; seeking resets its presentation progress. Reduced
motion retains the selected highlight without a reaching gesture.
One continuous state does not establish that reel content caused
the choice, visual specificity or learning; no such effect is claimed.

The closed [session contract](superpowers/specs/2026-11-03-feed-event-session.md)
defines the exact source/count/plan/EOF validation. This uses imported JSON,
not a live LLM/API call. Generated runs/media remain local and ignored.

## Optional scientific replay anatomy

The scientific canvas combines recorded population rates with an optional,
static sample of source cell-body positions. Generate that separate local file
from the existing locked runtime and the exact recording you will open:

```powershell
.venv/Scripts/python.exe scripts/export-anatomy.py --runtime-directory data/malecns-v1.0/runtime --recording runs/my-session/recording.json --output runs/my-session/anatomy.json
```

The output path must be new. This reads existing annotations and graph IDs;
it does not download data or run the simulator. Open the recording in the viewer,
then use **Open anatomy** for its matching `anatomy.json`. Loading another
recording clears the attached anatomy. The same panel appears in video export;
without the optional file, rates still work and anatomy is labelled unloaded.

The generator uses only actual `somaLocation` entries for the modeled IDs,
reports missing positions and deterministically selects at most 12,000 points.
The cloud is static source-coordinate context, without calibrated anatomical
axes or inferred synapse positions. The seven activity rows use recorded group
counts and per-cell Hz with individually labelled fixed scales. They are not
individual-neuron spike rasters or measured synaptic activity.

The sidecar binds to the original recording bytes and graph-ID hash. The
generator checks original source bytes; a browser without those sources cannot
independently prove coordinate provenance. Generated anatomy stays outside Git.
See the [presentation contract](superpowers/specs/2026-11-07-scientific-replay-presentation.md).

## Optional recorded cell activity

In the existing Windows workspace, the accepted bundle is already available at
`runs/cell-demo-20261108-02/`; no simulation or provider request is needed:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli inspect-session runs/cell-demo-20261108-02/session
npm --prefix viewer run dev
```

Open the printed localhost URL, choose **Open recording** with that bundle's
`session/recording.json`, then **Open cell counts** with `cell-activity.json`.
Optionally **Open anatomy** with `anatomy.json`. Play/seek/inspect, or play the
existing `demo-30fps.webm` directly. **Export video** reproduces presentation from
the loaded files. A server is not deliberately left running. The
[accepted report](experiments/2026-11-08-cell-capture-api.md) records exact hashes
and the retained first failed launch.

Individual counts require capture during a new session; old population totals
cannot be converted into cell activity. The bounded capture script composes the
same session engine and records a fixed cohort of at most 256 cells and 512 actual
directed model edges. It makes no provider request:

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/run-cell-activity-session.py --runtime-directory data/malecns-v1.0/runtime --playlist runs/my-playlist.json --proposal examples/event-options.json --output runs/my-cell-session
```

Use a new output directory. The ordinary bundle is under `session/`; incremental
`cell-activity.jsonl` and the validated `cell-activity.json` are at the output root.
The script enforces cell/bin/detail-byte limits; the bounded acceptance protocol
additionally requires external wall/RSS/output supervision. The
[acquisition report](experiments/2026-11-08-cell-capture-api.md) records the actual
status and any incomplete attempt; partial output is not an accepted recording.

Open `session/recording.json`, then **Open cell counts** with `cell-activity.json`.
The viewer checks exact recording bytes, source declarations, original bins and
population reconciliation. Its canvas shows the last completed 100 ms window;
before 100 ms no completed window exists. **Inspect exact recorded cell counts**
lists every source ID and integer count in the same grid order. Zeros remain
neutral, missing coordinates remain explicit, and seeking/terminal hold use the
same immutable counts. New recordings clear attachments; invalid files preserve
the current valid attachment and playback.

Optional anatomy adds static background context using the same projection.
Export video includes the count panel, fixed connections and seven original
population traces. These are simulated model counts; connections are static
topology, not measured synaptic transmission or exact intra-bin spike times.
See the [cell activity contract](superpowers/specs/2026-11-07-cell-activity-replay.md).

## Optional model-generated event proposals

`prepare-event-proposal` prepares a request independently of any simulation.
Its default mode is offline: it needs no API key and makes no network request.
Choose a model available to your own API project; `YOUR_MODEL_ID` below is a
placeholder, not an available/recommended model or a pricing claim.

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli prepare-event-proposal --title "Summer team party" --guests 100 --max-budget-chf 5000 --model YOUR_MODEL_ID --max-output-tokens 2048 --output-dir runs/proposal-preview
```

The parent directory must exist and the final directory must be new. Inspect
`request.json` and the `dry-run` receipt. There is deliberately no proposal in a
dry run. Existing JSON prepared by a person or another model remains supported.

To make one **paid external request**, configure `OPENAI_API_KEY` securely in
your local process environment, choose the model and token limit explicitly,
and add `--allow-paid-request` with a different new directory:

On Windows, create the key in the [API dashboard](https://platform.openai.com/api-keys),
then use **Edit environment variables for your account → User variables → New**:
name `OPENAI_API_KEY`, value your key. Open a new terminal after saving; an
already-running process keeps its previous environment. Keep the value out of
chat, Git, command history and request files. The command reads the process
environment; it does not load a `.env` file.

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli prepare-event-proposal --title "Summer team party" --guests 100 --max-budget-chf 5000 --model YOUR_MODEL_ID --max-output-tokens 2048 --output-dir runs/proposal-live --allow-paid-request
```

This sends the brief and fixed schema/instructions to OpenAI, with `store:false`;
no reels, measurements, selected plan or checkpoints are sent. The token range
is512..4096. This limits output tokens, **not CHF/USD cost**; check your API
project's access/pricing/spending controls. No API access or credit is assumed
from a ChatGPT subscription. The command never retries, follows redirects or
repairs a rejected answer automatically. Timeout/connection loss can still cost
money; an absent completion receipt does not prove the request was not sent.

On success, `proposal.json` passes the existing strict validator and matches the
exact brief; `receipt.json` is written last and records local hashes/usage. Only
the complete valid receipt with matching request/proposal hashes completes the
preparation; file presence alone does not. An error leaves the reserved directory
incomplete, potentially with a proposal or truncated receipt if a write failed.
Do not treat incomplete output as completed generation or automatically retry it.
Raw provider responses and API keys are not saved. The30s socket timeout is not
a whole-process deadline. Protect local brief/request files as your own data.

Use the successful proposal through the existing boundary:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli feed-event-session --playlist runs/my-playlist.json --proposal runs/proposal-live/proposal.json --output-dir runs/my-generated-session
```

The importer still identifies it as `imported-json`; a transport receipt is no
provider attestation or scientific evidence. The model cannot select a winner,
change the measured plan or configure neural behavior. A live Responses request
using `gpt-5.4-mini-2026-03-17` passed validation on November8,2026; other
models/accounts are not thereby verified. Eligible subscriptions can activate
[included API credits](https://help.openai.com/en/articles/20001626-api-credits-benefit-for-eligible-chatgpt-subscriptions);
check the linked API organization's actual grant rather than assuming credit
from the subscription alone. See the
[transport contract](superpowers/specs/2026-11-06-event-proposal-transport.md)
and [proposal handoff](event-proposal-prompt.md).

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
APIs; the `assay` CLI remains pending. The optional proposal transport is separate:
the pinned model/account path completed the accepted genuine proposal/session/
plan/film chain; broader model/account compatibility remains unverified.
Replay remains experimental, with the current bounded acceptance documented in
the [cell-count report](experiments/2026-11-08-cell-capture-api.md).

See the [assay implementation plan](superpowers/plans/2026-09-24-associative-plasticity-assay.md)
for the current scientific milestone and verification details.
