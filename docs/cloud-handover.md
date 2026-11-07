# Continuation handover — experimental v1, 2026-11-07

## Start here: current decision and next action

The user accepted the direction review on 2026-11-07: finish a **local,
experimental, measured-data replay demo**. The original training/research goal
remains a separate follow-up. Do not resume the historical assay checklist just
because it has unchecked tasks. Replay-first was an explicit user decision.

The product chain is implemented: real reel RGB -> one native MaleCNS engine ->
measured motor activity -> left/right/defer -> unchanged event plan -> smooth
3D replay. **Whether changing the visual content changes motor activity or the
choice has not been established by a controlled comparison.** A positive MBON11
assay would not automatically establish that: the current event/video policies
use only DNa02 motor-left/right, not the older MBON/motor preference adapter.

**Next session starts with Task 1 below: design a small, bounded content/side
comparison.** Do not start another general audit, verifier rewrite, full assay,
large control grid, platform expansion or fresh simulation merely for UI work.
The user wants completion and useful evidence, with bounded effort.

## Repository, authority and working style

- Local workspace: `C:/dev/jogge-di-fly-brain`; public repository:
  `https://github.com/manu-brighter/fly-connectome-sim`.
- Branch: `feat/connectome-experiment-core`; remote: `origin`. Latest code/CI
  checkpoint before this documentation handover: `981373bc2ff23273ce2980b722c2241b7b8da95f`.
  This handover is committed on top; use the latest pushed feature HEAD, not a
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
- Pause with concise status after the next sensible reviewed feature commit/push.

## Read only what the next task needs

1. [AGENTS.md](../AGENTS.md), [README](../README.md), this handover.
2. [Continuous-session contract](superpowers/specs/2026-11-03-feed-event-session.md),
   [current workflow acceptance](experiments/2026-11-07-session-workflow.md) and
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

## Three remaining v1 tasks, in order

### 1. Bounded visual-content and side diagnostic

- [ ] Write a short fixed comparison protocol before running it. State exact
  inputs, checkpoint/start state, clocks, comparisons, output measures and a
  finite run/resource budget. Have Astra review the scientific interpretation
  once; use Sol for bounded implementation, test-first where code changes.
- [ ] Separate **feed after-effect** from **response to event cards**. Compare
  the same start state and schedule with a controlled changed image sequence
  (e.g. black frames) and separately swap card positions. The current public
  feed policy changes duration based on activity; do not confuse different
  exposure times with a content effect. A small diagnostic harness may need
  fixed observation timing rather than copying the adaptive feed unchanged.
- [ ] Measure actual native motor counts/rate time courses and adapter outputs;
  report changes, no change, side bias and defer honestly. Existing pilot count
  differences are not controls. Different pixels/hashes alone are insufficient.
  Do not tune thresholds, hunt a winner, require a selection reversal, change
  the kernel or launch the full learning grid to obtain a positive result.
- [ ] Publish a concise scoped result and update the presentation claim. An
  absent effect is acceptable for an honest activity-driven demo; a claim of
  content-dependent preference requires supporting evidence. These controls
  cannot establish semantics, biological learning or general reel preference.

### 2. One genuine LLM proposal -> session acceptance

- [ ] Check local API/model/token/cost configuration. At handover the process
  has **no OPENAI_API_KEY** (presence checked only); no actual provider request
  or API cost has occurred. ChatGPT subscription does not supply API credit.
- [ ] Existing `prepare-event-proposal` defaults offline. Only explicit local
  key/model/token configuration and `--allow-paid-request` enable one paid
  request. Token limit is not a monetary cap. Do not retry automatically.
- [ ] Validate the successful provider proposal/receipt, pass its `proposal.json`
  into existing `run-session`, and preserve selected option/defer exactly.
  Current earlier pilots use authored `examples/event-options.json`, not live
  generated proposals. An unavailable API leaves this task explicitly open;
  it must not block the diagnostic or presentation work.

### 3. Final demonstration and v1 close-out

- [ ] Accept one coherent representative recording, bound plan and playable
  exported film, with clear real-input/measured-output/illustrative-motion labels.
  Reuse existing data for rendering work; only new input/provider/diagnostic
  needs justify new native runs. Longer feeds are optional, not a prerequisite.
- [ ] Check actual exported video playback/timing and readable choice or defer;
  retain exact source recording/plan and concise reproduction commands. Do not
  silently reuse a historical film as evidence for a newer recording/source.
- [ ] Align README/product scope with actual observation v1 and known limits.
  Record remaining training/research work separately and stop expanding v1.
  No post-choice narration, autonomous multi-round planner or deployment is needed.

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
  specific workload; not a general capacity estimate. Actual Chrome inspected
  this recording; no film was encoded from this newest bundle.
- Historical combined film acceptance: 360 frames/12s including 3s terminal
  hold, from the separate 2026-11-03 recording. See its linked session report.
  Local film location is not promised here; export again from the desired
  recording if required. Existing bundle/playlist/media presence was checked
  for handover, not independently reverified against all recorded hashes.
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

Current raw-byte model identities (38 Python/C++ members):

- Mixed-ending Windows working tree: `f3ef2ff605432fe549ada0aeb37384f3426df94be23d95049f2a180cc2d4197c`.
- Linux LF/exact Git blobs: `26b0f88127be9bd3d0732161519e23d34c0e8f9ef436ff0d773f558c447ea3e0`.
- Windows archive with CRLF conversion: `8bc237a7a592ab023d23a980034e4c5dc9441dd84b35b6d056bca60fea355e59`.
- Schema: `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.

All38 hosted member hashes matched exact Git blobs; in-memory CRLF->LF explains
archive difference. This was not a formal LF freeze. Any packaged .py/.cpp change
invalidates previous formal qualification/config/confirmation identities;
finish source-bearing work before a future formal freeze. Do not rerun science
for a documentation-only handover change.
