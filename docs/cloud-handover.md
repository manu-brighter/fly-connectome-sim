# Continuation handover — experimental v1, 2026-11-08

## Start here: current decision and next action

### Current continuation request

After the reviewed presentation repair, the user requested sequential autonomous
continuation until the agreed work is finished, they say stop, or the token limit
is reached. **Do not pause automatically after each commit/push.** Keep a small
number of agents: bounded implementation with Sol, difficult design/integrity
review with Astra, and preserve progress in tracked checkpoints.

The next product step, inferred from the preceding missing-neuron/synapse
discussion, is a bounded **recorded single-cell activity and connection view**.
First inspect existing native detail output, then define a finite acquisition
and rendering contract before implementation or a new observation. The existing
static-anatomy film remains valid; aggregate group bins cannot reconstruct
individual spikes. Connection topology must not be mislabelled as measured
synaptic transmission. The learning assay is still a separate parked track.

The [cell activity contract](superpowers/specs/2026-11-07-cell-activity-replay.md)
and [sequential plan](superpowers/plans/2026-11-07-cell-activity-replay.md) now fix
256 selected cells, at most512 existing directed edges, original native-bin
counts and completed100ms display windows. Astra completed protocol and process
supervisor review. A non-neural host smoke test verified actual child-process
monitoring; sandbox CIM restrictions require host execution for supervision.
The first implementation attempt hit a usage limit before code changes. The user
resumed on November8. Sol implemented the passive observer, fixed source-bound
cohort/topology, incremental raw writer, verified sidecar export and a script
composing the existing session workflow. 29 focused tests passed; combined
regression170 passed with4 Windows permission skips, and those4 then passed on
the host. Astra found and reviewed a correction binding the exporter to the
canonical recording file's actually inspected bytes; both defects had failing
regression tests before correction. Backend and safe API diagnostics are now
reviewed. Final combined host tests:285 passed,2 symlink-privilege skips in129.20s;
hardlink/junction tests passed. The viewer is now implemented and source-reviewed.
Its final full suite passed135 tests with zero skips in26.682s; build passed.
Actual synthetic browser checks cover both live proposal plans, pending/defer and
the corrected first paint. See the
[backend/API checkpoint](experiments/2026-11-08-cell-capture-api.md).
That checkpoint is committed/pushed as `f5766f5094599ff2529436bfabc06c34009441cb`.
Its [Linux compatibility run](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42428235786)
passed:185 native/backend tests,1 Windows-only junction skip; both new symlink
cases ran successfully. The unchanged viewer passed114 tests and its build.
**Acquisition and film acceptance are not complete**; do not treat this backend
checkpoint or synthetic viewer fixtures as a completed demonstration. No
interrupted review counts as acceptance.

The first acquisition launch stopped after0.353s because the supervisor counted
pre-existing regression fixtures inside its evidence directory:1,814,974,188
observed bytes exceeded the256MiB acquisition output cap. Both owned processes
ended without cleanup errors. `runs/cell-demo-20261108/` contains only an empty
`session/` directory; logs are empty and no measurement files were produced.
Original attempt, source freeze and supervision receipts are preserved locally.
Supervisor v2 isolates new acquisition evidence from prior validation artifacts
and retains all caps. Both non-neural host smoke tests passed; Astra independently
reviewed source/receipts and all119 retry-freeze hashes. The concrete retry uses
`runs/cell-demo-20261108-02/` with fresh isolated local acquisition evidence;
both targets are still absent. No automatic native retry is permitted by the
accepted protocol. Explicit authorization for this reviewed retry was requested
and is pending; do not start another acquisition without it.

The user delegated model/token selection. The offline request at
`runs/proposal-preview-20261107/` uses `gpt-5.4-mini-2026-03-17` with 2048 output
tokens, the existing Summer team party / 100 guests / CHF5000 brief, and request
SHA256 `945b86de95401e1349c418e45507d3015ea3cb85e3a064cb69c020e25b8dac51`.
The current [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
supports Responses/structured output and lists USD0.75/M input and USD4.50/M output
tokens; the displayed rough estimate is 1–2 US cents for one call, not a monetary
cap. On November8 the user created an API project/key and stored it in the
Windows user environment as `OPENAI_API_KEY`; a presence-only check confirmed it
there. Read that user value locally into the request process if the running
app's inherited environment is stale. Never print or persist it.

The first live attempt at `runs/proposal-live-20261108/` exited1 with the existing
sanitized `Event proposal transport failed`. It retains only the2024-byte
`request.json`, no validated proposal/receipt or token usage; the precise cause,
transmission status and any charge are unverified. No automatic retry occurred.
After API credit setup, the user explicitly authorized a second attempt.
`runs/proposal-live-20261108-02/` completed with a validated proposal/receipt:
357 input +241 output =598 tokens, requested/returned model
`gpt-5.4-mini-2026-03-17`, nominal USD0.00135225 at the checked tariff. Request
bytes exactly match the offline preview. Proposal SHA256 is
`da144f530f962b07431200684b7b3d0e74c0d5b42d5f066431fc9b989741e397`.
The two concepts are Sunset Rooftop Social / Indoor Summer Bash, within the
unchanged brief. They remain illustrative estimates, not verified venues/costs.
Use this exact successful `proposal.json` for the one cell-detail session.
**No further provider request is needed for the current demo.** The user asked
to keep API spending bounded and purposeful. Do not purchase credit, enable
recharge or retry automatically. Actual billing deductions were not inspected.
No complete fullgraph observation exists for this continuation yet;
tiny-native test fixtures and the immediately aborted launch are separate.

### Completed observation baseline

The user accepted the direction review on 2026-11-07: finish a **local,
experimental, measured-data replay demo**. The original training/research goal
remains a separate follow-up. Do not resume the historical assay checklist just
because it has unchecked tasks. Replay-first was an explicit user decision.

The product chain is implemented: real reel RGB -> one native MaleCNS engine ->
measured motor activity -> left/right/defer -> unchanged event plan -> smooth
3D replay. **The [bounded diagnostic](experiments/2026-11-07-content-side-diagnostic.md)
found that this specific real-versus-black visual manipulation changes motor
activity and the final adapter result.** The fixed8s feed is separate from the adaptive demo.
Card relocation reveals layout/history sensitivity, not stable semantic event
preference. A positive MBON11 assay would not automatically establish that:
the current event/video policies
use only DNa02 motor-left/right, not the older MBON/motor preference adapter.

**Tasks 1 and 3 are complete within the imported-proposal observation scope.**
After the user reopened visual acceptance, the [reviewed presentation repair](experiments/2026-11-07-scientific-presentation.md)
replaced the intersecting tablet with safe placement and a selected-card tap,
and added static source anatomy plus seven recorded population traces.
`runs/scientific-demo-20261107/` contains the revised 30 fps film, exact original
recording/plan and optional bound anatomy file. The [previous film](experiments/2026-11-07-final-demo.md)
remains historical; its earlier visual acceptance was insufficient.
**Genuine API proposal generation has passed; its native session and film remain
open.** External API setup is resolved. Complete Task2 using the successful
proposal in the one planned cell-detail session; do not call the entire LLM v1
complete before the session/plan checks.
Reuse the revised film or exact recording/plan/anatomy for presentation. Do not repeat the diagnostic,
expand controls, resume research or run a fresh simulation merely for UI work.

## Repository, authority and working style

- Local workspace: `C:/dev/jogge-di-fly-brain`; public repository:
  `https://github.com/manu-brighter/fly-connectome-sim`.
- Branch: `feat/connectome-experiment-core`; remote: `origin`. The prior
  `5ec5398` film-documentation checkpoint is superseded by this presentation repair.
  Use the latest pushed feature HEAD, not a
  checkout/reset to that historical hash. Verify status/tracking before edits.
- Autonomous relevant implementation, tests, reviews, commits and explicit
  `git push -u origin feat/connectome-experiment-core` are authorized. Never
  push main/master/develop, force-push, discard existing work, create PR/merge,
  deploy, or change remote resources/settings without separate authority.
- German, short updates. Routine implementation/fixes/reviews use Sol; difficult
  scientific, architectural or integrity decisions use Astra. Keep delegation
  bounded, no repeated full-project reviews or many simultaneous agents.
- Ask only for actual product decisions, missing authority or irreversible work.
  A missing API credential/cost configuration is a real external prerequisite;
  do independent work without requesting secrets in chat.
- Follow [AGENTS.md](../AGENTS.md), including English commit convention and no
  attribution signatures. Stage explicit first-party files and inspect diff/size.
  Runtime/data, `.tools/`, `.venv/`, `.superpowers/`, `.ai/`, egg-info, runs,
  checkpoints, media, chats and reference images remain ignored/uncommitted.
- Continue through reviewed feature checkpoints under the current user request;
  stop for completion, an explicit stop, the token limit or a real unresolved
  dependency. Do not invent extra product scope or resume parked research.

## Read only what the next task needs

1. [AGENTS.md](../AGENTS.md), [README](../README.md), this handover.
2. [Revised scientific presentation](experiments/2026-11-07-scientific-presentation.md),
   [continuous-session contract](superpowers/specs/2026-11-03-feed-event-session.md),
   [workflow acceptance](experiments/2026-11-07-session-workflow.md) and
   [usage](getting-started.md#continuous-reels-and-event-choice).
3. For content comparison: [session pilot](experiments/2026-11-03-feed-event-session.md),
   `src/fly_connectome_sim/experiment/feed_event_session.py`, `video_observation.py`,
   `video_policy.py`, `event_choice.py`, `event_cards.py`, `adapter.py`, and
   `src/fly_connectome_sim/engine.py`; corresponding `tests/experiment/` files.
4. For provider work: [proposal contract](superpowers/specs/2026-11-06-event-proposal-transport.md)
   and [usage](getting-started.md#optional-model-generated-event-proposals).
5. [Original product specification](specs/fly-event-planner.md) is background;
   its original training-first sequencing/mixed adapter are superseded for the
   current observation v1 by this accepted direction. Preserve scientific claims.

The [full prior handover/history](handover-history-2026-11-07.md) preserves all
old task IDs, hashes, detailed acceptance and assay continuation links. Consult
it on demand; it is not the current execution order. Private local notes and
this long chat are not required to continue from a fresh checkout.

## Experimental v1 tasks, in order

### 1. Bounded visual-content and side diagnostic

- [x] Write a short fixed comparison protocol before running it. State exact
  inputs, checkpoint/start state, clocks, comparisons, output measures and a
  finite run/resource budget. Have Astra review the scientific interpretation
  once; use Sol for bounded implementation, test-first where code changes.
- [x] Separate **feed after-effect** from **response to event cards**. Compare
  the same start state and schedule with a controlled changed image sequence
  (e.g. black frames) and separately swap card positions. The current public
  feed policy changes duration based on activity; do not confuse different
  exposure times with a content effect. A small diagnostic harness may need
  fixed observation timing rather than copying the adaptive feed unchanged.
- [x] Measure actual native motor counts/rate time courses and adapter outputs;
  report changes, no change, side bias and defer honestly. Existing pilot count
  differences are not controls. Different pixels/hashes alone are insufficient.
  Do not tune thresholds, hunt a winner, require a selection reversal, change
  the kernel or launch the full learning grid to obtain a positive result.
- [x] Publish a concise scoped result and update the presentation claim. An
  absent effect is acceptable for an honest activity-driven demo; a claim of
  content-dependent preference requires supporting evidence. These controls
  cannot establish semantics, biological learning or general reel preference.

Completed once on2026-11-07: two fixed8s feeds and six2s probes from matched
complete checkpoints,28s cumulative/504 observations. Real versus black feed
changed12/16 motor windows; the common black probe showed residual differences
in4/4. Final counts after real feed: normal L11/R1→left/Sunset House, swapped
L7/R0→left/Warehouse Techno, black L5/R5→defer. After black feed: normal0/0→defer,
swapped1/8→right/Sunset House, black0/0→defer. All outcomes/ten contrasts retained.
The [result](experiments/2026-11-07-content-side-diagnostic.md) records204 passing
tests, independent raw audit, Astra reviews and the disclosed Windows launcher
RSS-monitor correction. No native repeat, threshold tuning or new learning claim.
Raw output remains local at `runs/content-diagnostic-20261107/`; use it for
inspection, not as a session recording accepted by the viewer.

### 2. One genuine LLM proposal -> session acceptance

- [x] Configure local key/model/token settings and make the offline request
  reviewable. The initial November7 missing-key blocker was resolved November8.
- [x] Complete one validated live proposal after the explicitly authorized
  second attempt; exact request/proposal/usage evidence is recorded above.
  Existing `prepare-event-proposal` still defaults offline. Only explicit local
  key/model/token configuration and `--allow-paid-request` enable one paid
  request. Token limit is not a monetary cap. Do not retry automatically.
- [ ] Pass the fixed successful `proposal.json` through the one planned
  cell-detail capture that composes `run-session`; preserve selected option/defer
  exactly and validate the resulting plan. Earlier pilots retain their authored
  `examples/event-options.json` origin and cannot substitute for this check.

### 3. Final demonstration and v1 close-out — presentation repaired

- [x] Repair tablet/fly intersection, place the fly looking at the display and
  animate one selected-side tap after the measured decision. Keep simulation
  time frozen throughout the existing presentation hold; defer never taps.
- [x] Add static source-bound cell-body anatomy and seven measured population
  traces to the exported canvas. No invented individual spikes or synapse
  locations; the existing recording contains aggregate group bins only.
- [x] Review actual geometry, encoded frames, scientific labels and unchanged
  recording/plan, then publish a replacement presentation checkpoint.

The replacement has 360 VP9 frames / 12 s at 900×900, with the same 7 s feed,
2 s cards and 3 s presentation hold. Both contact paths retain original limb
lengths and clear tablet/body meshes; the real film shows reach, contact and
retraction on the selected left card. Anatomy uses 12,000 real sampled somata
from 139,662 positioned model cells, with 27,038 missing positions explicit.
All seven traces use recorded bins; terminal values freeze during the tap.
114 viewer tests and 10 generator tests passed, build passed, actual Chrome
playthrough completed and independent source/frame review found no open blocker.
See the [repair report](experiments/2026-11-07-scientific-presentation.md) for
artifact hashes, source checks, responsive scope, warnings and limits.

The earlier export checks below remain historical:

- [x] Accept one coherent representative recording, bound plan and playable
  exported film, with clear real-input/measured-output/illustrative-motion labels.
  Reuse existing data for rendering work; only new input/provider/diagnostic
  needs justify new native runs. Longer feeds are optional, not a prerequisite.
- [x] Check actual exported video playback/timing and readable choice or defer;
  retain exact source recording/plan and concise reproduction commands. Do not
  silently reuse a historical film as evidence for a newer recording/source.
- [x] Align README/product scope with actual observation v1 and known limits.
  Record remaining training/research work separately and stop expanding v1.
  No post-choice narration, autonomous multi-round planner or deployment is needed.

Historical imported-proposal demo: `runs/final-demo-20261107/` retains the exact
November 7 session recording/plan and a newly exported `demo-30fps.webm`.
Actual Chrome 157 export/playback and full decode passed: 360 VP9 frames,
900×900, 12 s = 9 s recorded data + 3 s labelled presentation hold. Final
L6/R2 → left/Sunset House and the bound plan are unchanged. No new native
simulation ran; this uses historical source identity `f3ef2ff6…`, not the
newer diagnostic source. Viewer checks: 97 passed, no skips; build exited 0.
See the [final report](experiments/2026-11-07-final-demo.md) for exact artifact
hashes, reproduction, warnings and limits. Task 2 remains open; this older film
is superseded by the reviewed repair above.

**Stop rule:** once the bounded diagnostic is honestly reported, the genuine
LLM path is accepted (or explicitly left blocked by external API configuration),
and the representative demo is ready, close the corresponding experimental v1
scope. If API remains unavailable, label the result imported-proposal demo and
keep LLM acceptance open; do not call the entire LLM v1 complete.

## What already works and available local evidence

- Locked official MaleCNS v1.0 inputs/prepared graph: 166,700 cells,
  25,582,938 directed edges, 124,177,617 synaptic contacts.
- Existing Python/C++ native core, explicit PAM11/PPL101 stimulation, checkpoint
  restoration/continuation, KC/MBON07/MBON11/DNa02 telemetry and append-only runs.
  Mechanism correctness does not establish learned behavior.
- Fast feed: 5x source-content sampling; nominal 3s minimum watch/4s clip cap,
  8s total feed cap. Cap takes priority: a third clip can end after 2s. Then
  exactly 2s event cards, no reset/state replacement, no external DAN/learning.
  Final 500ms counts select/defer at the existing uncalibrated 1Hz threshold.
- Foreleg reach/stroke/retract is illustrative 400ms motion, content scroll
  occupies its middle 200ms. Replay/video export is 30fps and consumes recorded
  measurements; motion is not measured anatomy or validated motor behavior.
- `run-session` composes recording/export/plan and final local receipt;
  `inspect-session` rederives outputs from bounded raw verification without an
  engine/network/writes. Receipt/integrity does not attest native history.
- Current local bundle: `runs/session-workflow-20261107/` contains `recording.json`,
  `plan.json`, `receipt.json`, and `run/{run.json,events.jsonl,checkpoints/}`.
  Its actual 9s run was 7s feed+2s cards, final L6/R2 -> Sunset House. This is
  a result, not a target for the next run. CLI wall time was 98.969s for that
  specific workload; not a general capacity estimate. This exact recording was
  newly exported and played through for the final demo, without native rerun.
- Historical combined film acceptance: 360 frames/12s including 3s terminal
  hold, from the separate 2026-11-03 recording. See its linked session report.
  It is separate from the newly accepted November 7 film and retains its own
  historical source/acceptance context.
- One-command scoped suite: 315 passed/5 sandbox skips; those 5 host path cases
  separately passed. Latest [CI run](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42380161212)
  on `981373b`: 142 passed/1 Windows-only junction skip; viewer 97 passed/build0.
  CI is data-free tiny-native Linux compatibility, not fullgraph qualification.
  See [CI evidence](experiments/2026-11-07-clean-checkout-ci.md).

## Local commands and missing cloud inputs

From the existing Windows workspace (choose new output paths; parent must exist):

```powershell
git status --short --branch
.venv/Scripts/python.exe -m fly_connectome_sim.cli inspect-session runs/session-workflow-20261107
npm --prefix viewer run dev
# Open the localhost URL Vite prints; Open recording -> the bundle's recording.json.
# Export video in the viewer. Do not assume an old server/tab is still running.
```

Only when a new observation is justified:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli run-session --playlist .tools/reels-source/playlist.json --proposal examples/event-options.json --output-dir runs/NEW-session
```

Available local tools: `.venv/Scripts/python.exe` (3.12.14), `.tools/uv/uv.exe`
(0.12.15), `.tools/zig/zig-x86_64-windows-0.16.0/zig.exe`, Node24.21.0/npm11.19.0;
media extra PyAV19.0.2. Viewer `npm ci`, `npm test`, `npm run build` are documented
in [Getting started](getting-started.md). Data root defaults to
`data/malecns-v1.0/runtime/`; set `FLY_CONNECTOME_SIM_DATA` before imports if moving it.

Local ignored `.tools/reels-source/playlist.json` points to existing
`DcTiO6Ls3HT.mp4` and `DZHp4mtNvJb.mp4` in the same directory. URLs:
https://www.instagram.com/reel/DcTiO6Ls3HT/ and
https://www.instagram.com/reel/DZHp4mtNvJb/ . Other supplied source candidates:
`DVi5CMeDH2B`, `DI_HK5_gXrq`, `C8hNXYegKhB`; not all are downloaded/accepted.
Fast-feed decoding requires each source's complete first20s; URLs are provenance
labels, not automatic downloads. Audio is not neural input.

A cloud checkout has none of the ignored runtime, media, toolchains or run bytes.
Follow [setup/data instructions](getting-started.md) or run the
[CI-selected data-free checks](getting-started.md#clean-checkout-compatibility).
Never claim local historic evidence was reproduced in cloud. GitHub CLI is
available at the documented WinGet path in the user's instructions; host auth
works but sandbox credentials were invalid, so request normal auto-review host
execution when required. No authentication settings were changed.

## Scientific boundaries and deliberately parked work

Preserve core/provenance/locks/MIT notice; never weaken checks for a positive
result. No claims of consciousness, understanding, dopamine concentration,
receptor activity, biological learning or validated motor behavior. Advance all
scheduled intervals, including explicit black RGB uint8 frames; individual
observe calls <=500ms. Reward-free observations use no external DAN and
learning=False. Same-state comparisons must preserve real clocks and passive decay.

Do not automatically resume C1/7B4f.3c-d, global grid/selected-evidence integration,
assay CLI/capacity, LF/formal source-freeze, fullgraph qualification/frozen config,
held-out confirmation or old/trained-state resumption. Fullgraph-Linux, broader
hostile-artifact/resource hardening, all-browser/accessibility coverage and
narration are separately scoped future work, not this v1's remaining checklist.
For an explicit research return use the archived handover and
[current assay plan](superpowers/plans/2026-09-24-associative-plasticity-assay.md).
No complete production assay CLI, positive learning gate or formal qualification
is established. Preserve genuine negative/inconclusive results.

Current raw-byte model identity (39 Python/C++ members):

- Mixed-ending Windows working tree: `804899ab8b828365ffb8065094b84aa3eb78330da85b79dd62465435e2cfb1b4`.
- Exact Git LF blobs: `f55dcd784aa383193e642983d8afc2f505b55a9f82176865985cd98c60233878`.
- Schema: `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.

The Git-blob identity is a byte-layout check, not a new Linux/native run.
The earlier38-member Linux/CRLF identities remain historical CI evidence in the
linked report, not identities of this new source. Diagnostic source pins are
not a formal LF freeze. Any packaged .py/.cpp change
invalidates previous formal qualification/config/confirmation identities;
finish source-bearing work before a future formal freeze. Do not rerun science
for a documentation-only handover change.
