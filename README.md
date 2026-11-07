![Fly Connectome Sim: offline, reproducible MaleCNS experiments with an animated neural fly. The motif and motion are illustrative, not an anatomical reconstruction or measured activity.](docs/assets/fly-connectome-header.svg)

<p align="center">
  <a href="#current-status">Status</a> ·
  <a href="#the-assay">The assay</a> ·
  <a href="docs/getting-started.md">Getting started</a> ·
  <a href="#provenance">Provenance</a>
</p>

An offline experiment built on the released **MaleCNS v1.0** wiring graph.
The current milestone is a local experimental demo: real reels enter the native
simulation, measured motor activity controls a recorded event choice, and a
smooth 3D replay presents the result. The [current handover](docs/cloud-handover.md)
defines the remaining v1 tasks: actual LLM-proposal acceptance and the final
demonstration. The [bounded content/side diagnostic](docs/experiments/2026-11-07-content-side-diagnostic.md)
found a motor-readout response to the specific visual manipulation, including
feed after-effects and layout sensitivity; it did not establish semantic or
stable event preference.

The separate research track tests a declared KC → MBON11 associative-plasticity
mechanism using controlled visual stimuli and explicit PPL101 stimulation.

**Work in progress: native correctness pilots have not established scientific support.**
Formal full-graph qualification and confirmation have not run. Bounded fullgraph
resource pilots have run, but whole-assay capacity and a production frozen
configuration have not been established. No positive
plasticity or learned-behavior result is claimed.

The graph supplies wiring and annotations. Physiology, plasticity and action
mappings are explicit model choices. This is not a complete living fly, and it
does not establish consciousness, semantic understanding, dopamine concentration
or receptor occupancy. The MBON11 endpoint does not establish a learned
left/right preference.

## Current status

| Area | Implemented | Still to establish |
| --- | --- | --- |
| Data | Checksum-locked MaleCNS v1.0 sources; prepared graph verified at **166,700 cells** and **25,582,938 directed edges** | Formal assay qualification and confirmation on the full graph |
| Native model | C++17 kernel; explicit PAM11/PPL101 stimulation; KC, MBON07, MBON11 and DNa02 telemetry | Physiological validity beyond the declared model |
| Experiment state | Checkpoint restore, complete-state hashes, reset determinism, candidate-memory interventions and authenticated native map/schema context | A qualified production frozen configuration |
| Assay evidence | Caller-owned native production, source-specific 408-pair tiny-native repeats, shared declaration arithmetic and a bounded pair checker with full EOF validation | Global grid/selected-evidence reconciliation/public freezing, fullgraph held-out confirmation and the `assay` CLI |
| Resource pilots | Fullgraph components, trained 10-/70-second one-anchor pilots with isolated native replay, and a [reviewed detail-on first-training-prefix sample](docs/experiments/2026-11-02-fullgraph-detail-prefix-pilot.md) | Unprofiled controlled timing, complete grid/assay capacity and fullgraph cloud/Linux execution |
| Product | One-command continuous reel→event sessions, engine-free bundle inspection, measured choice/immutable plan and30fps replay; bounded visual/side diagnostic and opt-in proposal transport | Live API acceptance and final representative demo; longer feeds and broader platform checks are follow-ups |

The [continuous session](docs/superpowers/specs/2026-11-03-feed-event-session.md)
uses one fresh engine for fast-feed reels and then2s of event cards, without
reset/restore. One actual run recorded7s feed+2s cards and selected Sunset House
from final6:2 motor spikes. Its combined film has360frames/12s at30fps, including
one labelled3s terminal plan hold. See the
[report](docs/experiments/2026-11-03-feed-event-session.md) and
[commands](docs/getting-started.md#continuous-reels-and-event-choice).
Continuous state does not establish that reel content caused the choice.
The separate fixed8s-feed diagnostic compared matched native states and clocks:
real versus black input changed motor counts, while swapping the cards after
real reels kept the final physical action left and therefore changed the
selected option. This supports sensitivity to those visual inputs, not event
understanding or a stable preference; it does not relabel the historical pilot.

Use `run-session` to record and export a new local session in one command, then
`inspect-session` to verify its raw-backed outputs without running the engine.
Open the bundle's `recording.json` in the viewer; selected and deferred results
are both valid completions. See the
[workflow commands and partial-run recovery](docs/getting-started.md#continuous-reels-and-event-choice).
The completion receipt is local bookkeeping and adds no scientific authority.

The [event-choice contract](docs/superpowers/specs/2026-11-02-event-choice-milestone.md)
adds two imported event concepts, deterministic visual cards and a fresh 2s
reward-free observation. The final 500ms motor counts select the left or right
proposal, or explicitly defer. The exported plan retains the chosen proposal
exactly; an LLM cannot override that selection. Start with the small
[example](examples/event-options.json) or [proposal prompt](docs/event-proposal-prompt.md).
These observation commands import JSON and make no model/API call. The separate
[proposal command](docs/getting-started.md#optional-model-generated-event-proposals)
defaults to offline preparation; an explicit key/model/token configuration and
cost opt-in enable one request. Live API compatibility remains unverified.
The historical standalone pilot selected Sunset House from final left2/right1 spikes;
same-artifact Chrome/plan-download and150-frame/5s export checks passed. See the
[event-choice report](docs/experiments/2026-11-02-event-choice-observation.md).

The motor readout is an engineered display policy with an uncalibrated 1 Hz
threshold. It uses measured lateral motor rates and leaves the primary MBON11
classification unchanged; it does not establish learned behavior.

Measured Replay remains experimental WIP. The current [fast-feed contract](docs/superpowers/specs/2026-11-02-fast-reel-feed.md)
adds an explicit `fast-feed` profile: 5× source-content sampling, 3s minimum
watch time and a 4s clip cap. After recorded ADVANCE, an illustrative foreground
leg reaches onto the display, swipes it and retracts in400ms; the synchronized
content stroke takes200ms.
Simulation stays at normal time; media PTS and replay speed are separate clocks.
Default `standard` preserves the original 1×/v1 protocol. The swipe combines
actual fed outgoing/incoming frames for presentation; it is not neural input.
Source review, focused tests and the actual 7s fast-feed pilot/raw/parser audit
passed. Chrome/boundary checks and the actual 225-frame/7.5s export passed,
including a labelled 0.5s presentation hold. See the [current handover](docs/cloud-handover.md),
[fast-feed plan](docs/superpowers/plans/2026-11-02-fast-reel-feed.md)
and [video commands](docs/getting-started.md#local-video-observation-and-recorded-feed-actions).
The earlier [12s A/B](docs/experiments/2026-11-02-measured-replay-observation.md)
and [3.5s standard-video](docs/experiments/2026-11-02-video-feed-observation.md)
observations are separate historical evidence, not fast-feed measurements.

Implementation and verification details live in the
[assay plan](docs/superpowers/plans/2026-09-24-associative-plasticity-assay.md).
The [assay design](docs/superpowers/specs/2026-09-24-associative-plasticity-pivot-design.md)
defines the scientific boundaries; the [product specification](docs/specs/fly-event-planner.md)
describes the broader event-planning goal; live API acceptance and optional
post-choice narrative remain open.

For a fresh cloud checkout, start with the versioned
[cloud handover and live TODOs](docs/cloud-handover.md). Local runtime data,
toolchains and private working notes are not part of the repository.

## The assay

Present synthetic A/B stimuli, pair one with PPL101 stimulation, then measure
A/B and neutral C probes **without external stimulation**. Compare matched
controls and necessity, sufficiency and sham interventions at two retention
times using the frozen MBON11 response endpoint.

![Conceptual assay pipeline: checksum-locked MaleCNS graph, explicit native model, controlled visual/PPL101 training, MBON11 probes at two retention times, and recorded native replay with analysis. This describes the workflow, not a validated result.](docs/assets/assay-pipeline.svg)

- **Locked inputs:** released source checksums, normalized metadata and prepared
  array locks gate model construction.
- **Controlled state:** counterbalanced protocols, complete-state validation and
  separate candidate/noncandidate content hashes support auditable interventions.
  Content equality alone does not prove donor history or clock compatibility.
- **Recorded evidence:** append-only events, durable retention anchors and
  isolated native replay support validated-prefix and sealed reports. Missing
  assay cells remain visible and yield an inconclusive result.

The ordinary `verify-run` command checks artifact integrity. Native replay is a
separate verification path; an intact artifact is not evidence of learning.

## Getting started

The native/data Windows workflow was exercised with **Python 3.12.14**,
**uv 0.12.15**, **Zig 0.16.0** and **Node.js 25.9.0**. The replay viewer was
checked separately with **Node.js 24.21.0 / npm 11.19.0** and requires Node >=24.
The numerical kernel uses C++17; Python coordinates experiments and Node.js
downloads the released data and serves/builds the local viewer.

Follow [Getting started](docs/getting-started.md) for the complete toolchain
setup, locked data download and verification, preparation, experiment commands
and tests. Allow space for the 1.1 GB source download plus generated outputs.
The [clean-checkout compatibility workflow](.github/workflows/compatibility.yml)
targets Ubuntu 24.04 with tiny native/session tests and viewer tests/build,
without MaleCNS data. The first [hosted Linux run](docs/experiments/2026-11-07-clean-checkout-ci.md)
passed 142 Python tests with one Windows-only skip, plus 97 viewer tests/build.
The system compiler and runner image are recorded per run, not pinned. See the
[exact scope and local commands](docs/getting-started.md#clean-checkout-compatibility).
macOS remains unverified.

## Provenance

The numerical core is adapted from MIT-licensed Stonkfly/DOOMFLY work through a
checksum-pinned Fly/Wirehead revision. Exact revisions and the retained notice
are documented in [THIRD_PARTY.md](THIRD_PARTY.md) and
[the upstream MIT notice](licenses/stonkfly-MIT.txt).

MaleCNS data is distributed separately under **CC BY 4.0**. Attribution and
citation details are provided by the
[official MaleCNS release](https://male-cns.janelia.org/download/). Raw data and
generated runtime artifacts remain outside Git. These third-party terms do not
declare a license for the project-owned code.
