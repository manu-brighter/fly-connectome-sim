# Continuation handover — experimental v1, 2026-11-09

## Start here: accepted scope and current status

### Current continuation request

**November 9 product discussion supersedes automatic continuation:** the user
paused the next-feature discussion to define a live event drink-price market.
The [concept](superpowers/specs/2026-11-09-live-drink-market-design.md)
records full jumps anywhere within each drink's allowed range and at least
30 minutes of real time between actual changes of the same drink. There is
**no CHF0.50 per-change cap** and no mandatory periodic price update. The user
requested learning recommendations and concept definition before an implementation
plan. The user has now answered both product questions: **staff adopts prices
from the board manually; the model chooses the drink as well as its price.**
There is no POS integration in the first pilot. The proposed activation semantics
are an automatic durable server-side price version, without staff confirming
every change, and a clearly marked last-known display state on disconnection.
These are technical planning decisions, not a claim of simultaneous screen updates.
The recommendation is activity-driven operation without new training first,
with a separate evidence gate for any later learning claim. The
[staged implementation plan](superpowers/plans/2026-11-09-live-drink-market.md)
details an offline population/timing inventory as Stage A, then separately gated
readout/performance measurements, price service/board, uploads/live display and
rehearsal. **The user approved the plan and autonomous execution on November 9:**
continue until finished or explicitly stopped, with up to ten subagents requested;
this platform permits three concurrent children. Stage A is now complete
and independently accepted: [population inventory](experiments/2026-11-09-market-feasibility.md),
148 passing tests / five declared Windows symlink-privilege skips, and actual
sealed-run inspection without a new fullgraph run or API call. Published feature
`dcb7f79a24bcab16b07fa1d2b13e4cb516a277cc` passed
[clean-checkout CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42648225025):
429 backend tests / eight skips, 243 viewer tests / four private-artifact skips
and build. All five locally skipped analyzer symlink cases passed on Linux. The separate
[historical KC screen](experiments/2026-11-09-market-kc-screen.md) found that one
of twenty fixed artificial groups dominated every strict maximum; it does not
qualify twenty-drink control. Sampled-cohort recruitment began near two seconds
despite nonblack inputs, so very short negative probes would be inconclusive.
The next step is the [matched-state input-response diagnostic](superpowers/specs/2026-11-09-market-response-diagnostic.md)
and [sequential implementation plan](superpowers/plans/2026-11-09-market-response-diagnostic.md):
2 seconds black prefix plus eight restored 4-second arms, 34 executed model
seconds, 900-second wall/4-GiB native peak-RSS/256-MiB new-output limits.
Protocol/source/supervisor review and real host monitoring smoke precede one
bounded acquisition. No new diagnostic acquisition has run yet. This tests fixed
input responses, not drink selection, learning or long-duration event readiness.
User-supplied scale:
10–20 drinks, 50–300 guests, usually 6–8 hours but also shorter or roughly 12-hour
events. Duration stays configurable; 12 hours is the initial later long-run test
reference, not an automatic shutdown limit. Necessary new measurements require
a concrete reviewed protocol and finite resource bounds before execution;
do not launch indefinite fullgraph runs or infer live learning, paid API use,
POS access or deployment. Do not return to the previous event-input editor.
The plan does not claim that existing left/right output already supports multiple
drinks or that the 9-second recording qualifies continuous event operation.
The existing demo and its evidence below remain complete and unchanged.

After the reviewed presentation repair, the user requested sequential autonomous
continuation until the agreed work is finished, they say stop, or the token limit
is reached. **Do not pause automatically after each commit/push.** Keep a small
number of agents: bounded implementation with Sol, difficult design/integrity
review with Astra, and preserve progress in tracked checkpoints.

**The agreed experimental observation v1 scope is complete.** The genuine API
proposal → continuous native session → measured choice → unchanged plan → film
chain and the bounded recorded single-cell/static-connection view are accepted.
No further acquisition, provider request or feature expansion is needed for that
completed scope. The user subsequently selected **LLM feedback and event-plan
continuation**: a separate German companion to the fixed, inspected selection.
This is now **complete and independently accepted** under the
[follow-up contract](superpowers/specs/2026-11-08-event-followup.md) and
[plan](superpowers/plans/2026-11-08-event-followup.md): offline-first CLI,
unchanged original plan, one bounded live acceptance, no new fullgraph recording.
The [accepted result](experiments/2026-11-08-event-followup.md) is local at
`runs/event-followup-live-20261108/event-plan.md` with JSON/request/receipt beside
it. The single call used308input+228output=536tokens and15.562s, nominal
USD0.001257 at the checked tariff; actual billing was not inspected. All seven
historical source files and the full plan stayed identical. No more provider
calls or acquisitions are needed for this selected continuation.
After the next `continue`, the controller stated the next-step assumption:
show that existing companion directly in the viewer. This local-only display
is implemented under the [viewer contract](superpowers/specs/2026-11-08-followup-viewer.md)
and [plan](superpowers/plans/2026-11-08-followup-viewer.md), with no new provider
request, simulation or film. Sol implemented it and Astra independently reviewed
the source/UI. The [browser acceptance](experiments/2026-11-08-followup-viewer.md)
checks the real saved pair, decision/rewind visibility, desktop/mobile layout,
exact Markdown download and unchanged original plan. Separate declared fixtures
cover replacement/defer; all 15 historical inputs and 41 package sources remain
unchanged. Astra accepted the actual desktop/mobile screenshots and independently
matched the inputs, package identity and downloads. This bounded viewer
continuation is complete and published as `46e0200c2a94c88f984f8c4b5f65617e8cdffa94`.
Its [clean-checkout CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42522727223)
passed: 343 native/backend tests with 8 declared skips; 151 viewer tests with
2 private-artifact parity skips, plus typecheck/build. Locally all 153 viewer
tests passed without skips. No additional provider request or acquisition is
needed for the completed companion/viewer scope.
The user then explicitly selected **Einfacher lokaler Demo-Start** as the next
step: a preparation command and one combined viewer file selection for the
existing recording, cells, anatomy and companion pair. This is now implemented
under the [local demo contract](superpowers/specs/2026-11-08-local-demo-open.md)
and [plan](superpowers/plans/2026-11-08-local-demo-open.md). Reuse accepted files;
no new API request, native acquisition, packaged Python/C++ change or deployment.
The [actual combined-import result](experiments/2026-11-08-local-demo-open.md)
uses `runs/local-demo-20261108/`: exactly five verified copies, one selection,
all existing brain layers and choice-gated notes. Invalid import retention,
rewind, picker cancellation, delayed replacement and desktop/mobile layout passed.
Final local viewer suite: 246 passed, one Windows link-creation skip; build passed.
Astra independently accepted source, actual visual evidence and artifact bindings;
the step is complete and published as `c7bbbdc99ed39e6e03facd43902e3c71ffc71bce`.
[Clean-checkout CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42525145089)
passed 243 viewer tests with four private-artifact parity skips and a successful
build; the Windows-skipped dangling-link case passed on Linux. Backend/native
compatibility passed 343 tests with eight skips. No further acquisition or
provider request is needed to use the prepared demo folder.
The learning assay and broader platform work remain separately parked.
Aggregate group bins cannot reconstruct individual spikes; the new cell view uses
separately captured counts. Static connections are not measured transmission.

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
That was the backend checkpoint, not film acceptance. The subsequent reviewed
source checkpoint `776465dce2ece99ffdec74a43d6f6116157ecc60` passed
[Linux CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42431095712):
185 native/backend tests, one Windows-only skip, 135 viewer tests with no skips
and a successful build. Actual recording/film acceptance below is separate from
synthetic fixtures; no interrupted review counts as acceptance.

The first acquisition launch stopped after0.353s because the supervisor counted
pre-existing regression fixtures inside its evidence directory:1,814,974,188
observed bytes exceeded the256MiB acquisition output cap. Both owned processes
ended without cleanup errors. `runs/cell-demo-20261108/` contains only an empty
`session/` directory; logs are empty and no measurement files were produced.
Original attempt, source freeze and supervision receipts are preserved locally.
Supervisor v2 isolates new acquisition evidence from prior validation artifacts
and retains all caps. Both non-neural host smoke tests passed; Astra independently
reviewed source/receipts and all 119 retry-freeze hashes. The user explicitly
authorized the second launch at `runs/cell-demo-20261108-02/` with isolated
evidence under `.tools/cell-acquisition-20261108-02/`. It completed in 109.223 s;
both exit codes were zero, with no cleanup errors. Observed native peak RSS was
948,957,184 bytes and acquisition output peak 47,844,542 bytes. No automatic
retry occurred; the first incomplete attempt remains intact.

The accepted recording has 7 s feed + 2 s cards, 214 observations, 1,040 native
bins and 90 completed 100 ms windows. Its fixed cohort has 256 positioned cells
(KC 231/4,064 plus all mandatory groups), 512/4,254 directed connections and
5,388 recorded counts across 98 active cells; maximum 14 per cell/window.
Final L7/R2 selects Sunset Rooftop Social through the unchanged lateral policy.
The saved/downloaded plan exactly retains the live proposal. Independent source,
bin/window, artifact and film audits passed. Actual Chrome 157 on Windows 11
played all 360 VP9 frames / 12 s at 900×900 without error or dropped frames;
the final 3 s is a labelled frozen-measurement hold with illustrative tap.
The actual 341×1600 narrow view was checked. See the
[accepted report](experiments/2026-11-08-cell-capture-api.md) for hashes and limits.

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
This exact successful `proposal.json` was used for the accepted cell-detail session.
**No further provider request is needed for the current demo.** The user asked
to keep API spending bounded and purposeful. Do not purchase credit, enable
recharge or retry automatically. Actual billing deductions were not inspected.
The completed fullgraph observation is distinct from tiny-native test fixtures
and the immediately aborted first launch. It establishes an experimental replay
demonstration, not scientific qualification or semantic preference.

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
**Task 2 and the recorded cell-view extension are now accepted** through the
November 8 native session, unchanged plan and actual film. This closes the agreed
observation scope, not the broader research/event-platform specification.
Use the November 8 bundle for the current presentation; retain November 7 as
historical evidence. Do not repeat the diagnostic,
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
- [x] Pass the fixed successful `proposal.json` through the accepted November 8
  cell-detail capture that composes `run-session`; the selected option/brief/
  programme and downloaded plan exactly match. Earlier pilots retain their authored
  `examples/event-options.json` origin and cannot substitute for this check.

### 2b. Bounded feedback to the selected event — accepted

- [x] Fix scope with the user: separate German planning companion, no changed
  original plan or new neural recording. Astra design review completed.
- [x] Implement offline-first `prepare-event-followup`, source binding, strict
  response handling and JSON/Markdown publication; review/test before live use.
- [x] Inspect one actual offline request, then make one bounded live acceptance
  using the accepted session and pinned model,1024 output tokens,120 s deadline.
- [x] Independently inspect actual text/usage/source hashes and document the new
  source identity. No automatic provider retry. Feature publication and its
  compatibility outcome are established by the corresponding Git/CI receipts.

### 2c. Local companion viewer — accepted

- [x] Bind the two imported companion/receipt files to the exact original
  recording and complete plan; download only checked Markdown bytes.
- [x] Gate text/download by the current recorded choice, including rewind,
  replacement, stale imports and deferred results; preserve original plan export.
- [x] Independently accept actual desktop/mobile display, original downloads
  and unchanged historical files; use declared fixtures only for race/defer checks.
- [x] Publish the reviewed feature checkpoint and observe successful clean-checkout
  CI. See the [viewer result](experiments/2026-11-08-followup-viewer.md).

### 2d. Simple local demo start — accepted

- [x] Prepare exactly five checked copies using bounded reads and exclusive output.
- [x] Open recording, cells, anatomy and companion pair with one selection;
  preserve old state on failure and ignore superseded asynchronous imports.
- [x] Accept real prepared files, choice/rewind/download behavior, desktop/mobile
  layout and unchanged original artifacts; independently review source/evidence.
- [x] Publish the reviewed feature and observe successful Linux CI, including
  the dangling-link test. [Result and commands](experiments/2026-11-08-local-demo-open.md).

### 3. Final demonstration and v1 close-out — presentation repaired

- [x] Accept the November 8 genuine-proposal session with 256 recorded cells,
  static source connections, unchanged plan and actual 30 fps film. Independent
  raw/source/film review, complete playback and narrow layout passed. The agreed
  experimental scope is closed; broader platform and research remain separate.

- [x] Repair tablet/fly intersection, place the fly looking at the display and
  animate one selected-side tap after the measured decision. Keep simulation
  time frozen throughout the existing presentation hold; defer never taps.
- [x] Add static source-bound cell-body anatomy and seven measured population
  traces to the exported canvas. No invented individual spikes or synapse
  locations; the existing recording contains aggregate group bins only.
- [x] Review actual geometry, encoded frames, scientific labels and unchanged
  recording/plan, then publish a replacement presentation checkpoint.

The historical November 7 replacement has 360 VP9 frames / 12 s at 900×900, with the same 7 s feed,
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
hashes, reproduction, warnings and limits. This older film is superseded by the
reviewed November 7 repair and the accepted November 8 cell-detail demonstration.

**Completion rule:** the diagnostic, genuine proposal/session path and current
representative film are accepted. Close this agreed experimental v1 scope; do
not infer further features, research resumption or deployment from that closure.

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
- Current local bundle: `runs/cell-demo-20261108-02/` contains the ordinary
  `session/` bundle, raw/exported cell detail, optional anatomy and the accepted
  `demo-30fps.webm`. It is 9 s measured data plus a 3 s presentation hold, final
  L7/R2 → Sunset Rooftop Social. Reopen it without another simulation/API call.
- Historical local bundle: `runs/session-workflow-20261107/` contains `recording.json`,
  `plan.json`, `receipt.json`, and `run/{run.json,events.jsonl,checkpoints/}`.
  Its actual 9s run was 7s feed+2s cards, final L6/R2 -> Sunset House. This is
  a historical result. CLI wall time was 98.969s for that
  specific workload; not a general capacity estimate. This exact recording was
  newly exported and played through for the final demo, without native rerun.
- Historical combined film acceptance: 360 frames/12s including 3s terminal
  hold, from the separate 2026-11-03 recording. See its linked session report.
  It is separate from the newly accepted November 7 film and retains its own
  historical source/acceptance context.
- Historical one-command scoped suite: 315 passed/5 sandbox skips; those 5 host path cases
  separately passed. Historical [CI run](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42380161212)
  on `981373b`: 142 passed/1 Windows-only junction skip; viewer 97 passed/build0.
  CI is data-free tiny-native Linux compatibility, not fullgraph qualification.
  See [CI evidence](experiments/2026-11-07-clean-checkout-ci.md).

## Local commands and missing cloud inputs

From the existing Windows workspace (choose new output paths; parent must exist):

```powershell
git status --short --branch
.venv/Scripts/python.exe -m fly_connectome_sim.cli inspect-session runs/cell-demo-20261108-02/session
npm --prefix viewer run dev
# Open recording -> runs/cell-demo-20261108-02/session/recording.json.
# Open cell counts -> runs/cell-demo-20261108-02/cell-activity.json.
# Optional Open anatomy -> runs/cell-demo-20261108-02/anatomy.json.
# Play/seek/inspect, or open existing demo-30fps.webm. No simulation rerun is needed.
# Export video only to reproduce presentation. Do not assume an old server is running.
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

Current raw-byte model identity after the separate follow-up implementation
(41 packaged source members):

- Model fingerprint: `1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
- This source has no new fullgraph recording or formal qualification. The
  historical recording remains bound to its original sources below.

Historical November8 acquisition-freeze identity (40 packaged source members):

- Model fingerprint: `dc83d0796fd51c46323ee0e96a7bcfc725d34c6d94371971d235d90ed4144db5`.
- Accepted session engine identity: `13eb5c81d3898597224405ae06a62e03359d28588d0b81f5c1a51ead528ae1e7`.
- All 119 acquisition-freeze bindings were checked independently. This local
  observation freeze is not formal research qualification.

Historical November 7 raw-byte identity (39 Python/C++ members):

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
