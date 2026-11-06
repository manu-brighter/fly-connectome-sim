# Continuation and cloud handover — 2026-11-06

Use `origin` of `manu-brighter/fly-connectome-sim`, branch
`feat/connectome-experiment-core`, latest pushed feature commit. The prior
standard-video checkpoint `639423f`, Phase 1 A/B checkpoint `4467431` and
screen-contact checkpoint `877fbe2`, standalone event-choice checkpoint
`d97e1e8` and continuous-session checkpoint `011f6fa` are historical. The
continuous-session pilot source had36 Python/C++ members, model identity
`d4b72b01f14c4c4ec1266f976692fa6bf7dc91b3b83ed40f6f5540ab25a7ec9c`;
schema remains `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
The [continuous-session contract](superpowers/specs/2026-11-03-feed-event-session.md)
and [implementation plan](superpowers/plans/2026-11-03-feed-event-session.md)
govern that completed slice: one fresh engine observes the bounded fast feed then
immediately the event cards, without reset/restore, and records a measured
left/right/defer choice plus unchanged plan. Strict imported proposal JSON
remains the measured pipeline's provider boundary. The separate
[proposal transport](superpowers/specs/2026-11-06-event-proposal-transport.md)
adds offline preparation and an explicit one-request paid opt-in; no live API
call or cost has occurred here. Formal qualification/freeze/confirmation, C1,
live API acceptance and old/trained-state integration remain parked.
Earlier evidence remains source-specific; continuous
production does not establish a causal content/learning effect.

The prior viewer-only [screen-contact correction](experiments/2026-11-02-screen-contact-swipe.md)
reuses that exact7s recording. The foreground leg now visibly reaches onto the
screen, strokes upward and retracts in400ms; only the middle200ms scrolls the
content. Actual encoded lower/mid/upper contact frames were inspected. Viewer
tests:66 passed/build0; all33 Python/C++ sources remain unchanged and no native
run was repeated. This supersedes the earlier small whole-leg tilt's visual
acceptance, not its data/frame checks.

Continue autonomously on the original Windows workstation, including reviewed
feature commits and explicit feature pushes. Pause after the next sensible
reviewed commit/push to report the result, as required by AGENTS.md.
No PR, merge or deployment is authorized. Cloud setup is for a future fresh
checkout, not a gate on current local work. Never push main/master/develop.

## Read first

1. [AGENTS.md](../AGENTS.md), [README](../README.md) and
   [product scope](specs/fly-event-planner.md).
2. [Approved assay design](superpowers/specs/2026-09-24-associative-plasticity-pivot-design.md)
   and [current plan/live task details](superpowers/plans/2026-09-24-associative-plasticity-assay.md).
3. [Strict qualification integration contract](superpowers/specs/2026-11-01-strict-qualification-contract.md)
   and [six-slice integration plan](superpowers/plans/2026-11-02-strict-qualification-integration.md).
4. [Replay contract](superpowers/specs/2026-10-02-replay-anchor-contract.md) and
   [candidate-state digest contract](superpowers/specs/2026-10-03-candidate-state-digest-contract.md).
5. [Detail-on first-training-prefix report](experiments/2026-11-02-fullgraph-detail-prefix-pilot.md),
   [70-second resource report](experiments/2026-11-01-fullgraph-retention-pilot.md)
   and [earlier short-retention report](experiments/2026-10-08-fullgraph-anchor-pilot.md).
6. [Measured Replay v1 plan](superpowers/plans/2026-11-02-measured-replay-v1.md)
   and [historical A/B observation report](experiments/2026-11-02-measured-replay-observation.md).
7. [Animated replay and genuine-video continuation](superpowers/plans/2026-11-02-animated-measured-replay.md)
   and [historical standard-video report](experiments/2026-11-02-video-feed-observation.md).
8. [Current fast-feed plan](superpowers/plans/2026-11-02-fast-reel-feed.md)
   and [fast-feed observation report](experiments/2026-11-02-fast-reel-feed-observation.md).
9. [Current event-choice plan](superpowers/plans/2026-11-02-event-choice-milestone.md),
   [contract](superpowers/specs/2026-11-02-event-choice-milestone.md) and
   [proposal handoff](event-proposal-prompt.md).
10. [Current continuous-session plan](superpowers/plans/2026-11-03-feed-event-session.md),
    [contract](superpowers/specs/2026-11-03-feed-event-session.md) and
    [observation report](experiments/2026-11-03-feed-event-session.md).
11. [Proposal transport plan](superpowers/plans/2026-11-06-event-proposal-transport.md),
    [contract](superpowers/specs/2026-11-06-event-proposal-transport.md) and
    [usage](getting-started.md#optional-model-generated-event-proposals).

The older connectome-core plan is background. This tracked handover and current
plan orient a fresh checkout; private local SDD notes/chats/scripts are not
required and do not travel through Git. Local raw evidence is not replaced by
this document. Do not claim to reverify unavailable bytes.

## Current proposal transport checkpoint

`prepare-event-proposal` defaults to an offline request/dry-run receipt. A live
invocation requires an explicit model,512..4096 output tokens, environment key
and `--allow-paid-request`; fixed verified-TLS host, one POST, no retry/tools.
Current37-member local Windows model identity:
`093081c36bbb64dbb36099e5281407075767e6083244abaf7800631a30ae588b`.
The new module and narrow CLI change leave existing validators, engine/native
equations, recorder/schema, viewer and dependencies byte-identical. Old formal
identities are invalidated; old pilot results remain source-specific.

Astra architecture/source/security/runtime review closed with0 Critical/
Important/Minor findings. Scoped compatibility:251passed/1sandboxjunctionskip;
that actual junction passed separately on the host. A later test-only regression
and full transport module87passed/1same skip preserve all packaged bytes. Test
counts overlap. These are no live API or full-assay acceptance claims.

The actual offline CLI and a clearly declared fake-HTTPS fixture passed independent
request/hash/import/render checks. No API key was configured, no paid call was
made, and live compatibility remains unverified. No new fullgraph observation
was run; existing compatibility tests exercise tiny-native fixtures separately.
Receipts are local completion/provenance records, not provider/native/scientific
attestation. Require a complete valid receipt and matching file hashes; partial
output persists, and path presence alone does not prove completion. Token/socket
limits are not a CHF budget or total process deadline. Exact evidence/limits:
[transport report](experiments/2026-11-06-event-proposal-transport.md).

## Historical continuous-session checkpoint

`feed-event-session` creates one fresh engine/recorder/root; existing fast-feed
STOP ends the feed phase only, immediately followed by four500ms card intervals
in the same state. Global clocks/owned event references are preserved; no reset,
restore, replacement engine, fake old-format run or intermediate hold. The new
closed replay switches phone→board at feed STOP and reveals the exact bound
plan only at the later decision. Old standalone readers/exporters remain strict;
same old Event/Fast/Standard artifacts re-exported byte-identically after freeze.

Independent architecture/frozen backend/fresh viewer reviews closed with no new
Critical/Important/Minor finding. Known foreign raw-run allocation hardening is
still open. Backend640passed/1junction skip215.58s; that exact test separately
passed on the host in0.07s,after a corrected root test-directory setup error.
Viewer91passed/0skip29.179s/build0; known bundle/type-strip notices remain.
Backend39-path and viewer24-path raw freezes matched; no dependencies/core/
adapter/recorder/schema changed. These are scoped checks, not a whole-assay pass.

One actual source-frozen pilot exited0 in94.735s/240s wall budget:216events,
214observations/1040bins,7s feed then2s cards. Feed ADVANCE at3s used motor-right;
STOP at7s was external clip_window_end/playlist_exhausted. Final500ms L6/R2,
pop1/1→12/4Hz,delta−8→inspect_left/Sunset House. Original240prepared source
frames/210consumed frames and all raw/global counts/clocks/plan were audited.
No causal/learned/semantic preference or native-history attestation is inferred.

Actual Chrome passed69999/70000 phone→cards,89999/90000 pending→plan, reverse
seek,play/pause83095 and bound JSON equality/export restoration. The actual
combined UI movie decodes360VP9 frames/900x900/12s,33–34ms PTS intervals:
9s measured source+3s labelled terminal plan hold. Decoded92shows foreleg swipe,
209/210 feed→cards,269/270 pending→selection and359terminalhold. Native player
reports12s/no media error. Broad platforms/liveFPS and orbit-hint polish stay open.
Full source/artifact identities, commands and limits are in the
[session report](experiments/2026-11-03-feed-event-session.md).

Local ignored `runs/feed-event-replay-20261103.json`,
`runs/feed-event-plan-20261103.json` and
`viewer/test-output/feed-event-session-30fps.webm` can be reused for presentation.
They are absent in cloud checkout; reproduce with the
[continuous commands](getting-started.md#continuous-reels-and-event-choice),
local source videos and tracked example. No live LLM/API call is configured.

## Historical standalone event-choice checkpoint

This source-specific checkpoint used35members/model
`e0bfc0ef08b44beafababa8598a0f902a9dcdc75e71d07f626f79fe5ed2c1275`.

Strict `event-options/v1` import renders two actual384x216 RGB cards; a fresh
engine observes four500ms intervals, without external stimulation or learning.
The first1500ms settle; unchanged strict1Hz lateral policy selects from final
500ms integer motor counts at20000ticks. The plan is the exact selected proposal
or explicit defer, bound to actual observe sequence/hash and source artifact.
No winner override, live API, old trained/reel checkpoint restore or retry loop.
The tracked example is authored; it is not a fabricated live LLM request.

Independent backend review closed C0/I0/M1 for the own bounded pilot; the foreign
raw-run allocation-hardening Minor stays open below. Initial viewer review
C0/I1/M2 was corrected test-first and independently closed C0/I0/M0. Backend
focused307passed/310deselected39.29s and separately79passed85.88s overlap at CLI;
no skips/failures. Viewer83passed/0skip10.263s,build0; known bundle-size and
test-only Node experimental notices remain. All40 backend freeze paths and23
viewer paths matched reviewed SHA256/size. No whole-project/assay pass claimed.

Exactly one actual2s MaleCNS pilot completed exit0 in14.687s/120s wall budget;
verify/replay export/plan export all exited0, with model/proposal exact throughout.
The6events/200bins original-byte audit found final left2/right1 spikes,
populations1/1:4Hz/2Hz,difference−2Hz → `inspect_left`, `sunset-house`.
The copied plan is Sunset House,rooftop/House,CHF4800,100guests,capacity120,
240minutes,programme0Welcome drinks/60DJ and dancing. No semantic or learned
preference, visual specificity or native-history attestation is established.

Actual Chrome checked pending19999/selected20000, reverse seek, bound JSON
download equality, play/pause and export. The same-artifact movie independently
decodes to150VP9 frames/900x900/5s,33–34ms intervals:2s source plus3s labelled
terminal plan hold. Frame59 remains pending;60/149 show selected plan/left outline.
The native video player reports5s and no media error. Broader platforms/live FPS
remain unverified. Full commands, source/artifact hashes and limits are in the
[event-choice report](experiments/2026-11-02-event-choice-observation.md).

Reuse local ignored `runs/event-choice-replay-v1-mvp-20261102.json`,
`runs/event-plan-v1-mvp-20261102.json` and
`viewer/test-output/event-choice-replay-30fps.webm` for presentation work;
these are absent in a fresh cloud checkout. Reproduce with the
[tracked example](../examples/event-options.json) and
[commands](getting-started.md#local-event-proposals-and-measured-selection).

## Scientific and provenance boundaries

- Locked MaleCNS v1.0 graph: 166,700 cells, 25,582,938 directed edges and
  124,177,617 synaptic contacts. Preserve source/prepared locks and upstream MIT notice.
- Primary endpoint is MBON11 under the declared PPL101-modulated KC-to-MBON11
  model. PAM11/MBON07 is exploratory and cannot rescue a failed primary gate.
- Artifact integrity and map/content authentication do not attest upstream native
  training. Existing native anchor replay proves its declared black retention.
  No consciousness, semantic understanding, dopamine concentration, receptor
  activity, biological learning or validated motor behavior is established.
  Scientific support remains unproved; the motor-only display policy is unvalidated.
- Advance every interval, including explicit black RGB uint8 frames. Calls are
  <=500 ms; reward-free tests/retention have no external DAN, learning=False and
  normal passive decay. Keep association-reference and training-end clocks distinct.
- No formal qualification, production frozen config or held-out fullgraph
  confirmation exists. Missing evidence is not an authenticated scientific negative.
  Never fabricate successful gates/configuration to continue a negative run.

## Historical fast-feed checkpoint

This checkpoint used the33-member model
`132b9c00a2a7d3d5da15963024abf85a0a31209d7f59f5903dd4edd9298a0ac2`.
Its original files remain viewable, but new packaged source does not upgrade this
historical evidence into current-source qualification or native attestation.

Explicit `observe-video --profile fast-feed` selects the closed v2 protocol,
stimulus, policy and compact-format quartet: source speed `[5,1]`, 20s source
coverage and 30000-tick minimum dwell. Default `standard` preserves the exact
v1/1× protocol, 4s coverage and 1s dwell. Both advance actual 90x160 RGB inputs
at normal 30Hz simulation time, at most 120 frames/4s per clip and 8s total.
Fast-feed samples source time `5*j/30`; it does not process every original frame.
No external stimulation or learning is enabled; passive evolution is unchanged.

The existing 1Hz lateral motor threshold, causal 300ms counts/100ms evaluations
and session > clip-window > motor-right > watch priority remain. Fast-feed
allows motor advance at 3s or later; the 4s clip-window limit is external.
No result is tuned to force a neural action. The400ms foreground-leg gesture
contains a200ms screen swipe, using the last fed outgoing frame and current
actual incoming frame. Its composite/foreleg motion is illustrative, not another
neural input. STOP/reduced motion do not swipe.
Media PTS, native simulation time and Replay Speed remain distinct.

Focused backend/CLI tests: **114 passed in 94.32s**, covering 81 existing and 33
new tests. Initial fast-feed viewer: **63 passed; build exit0**. Independent Astra source/integrity
review closed C0/I0/M0, including 240 actual source PTS/RGB hashes and 19,360
pure policy cases. That historical Sol viewer review closed C0/I0/M0 on 18-file freeze
`41423f850430b40c1447c6d508efbbef6682e36f563d864d03014aac3e30e00f`.
Historical actual v1-video and A/B re-exports remain byte-identical; the strict
reader was not loosened. Source tests alone do not establish native runtime.

The single actual pilot completed exit0 in **76.734s** (240s subprocess wall
budget); ordinary verify/export passed in 1.203s/2.250s. All 33 source members
stayed exact. Actual session: **7.0s/70000 ticks, 210 inputs, 840 bins, 212 events**.
Clip0 consumed 90 frames/3s (first 15s media); clip1 consumed 120 frames/4s
(first 20s media). Independent re-decode matched all 240 prepared RGB/PTS hashes
and all 210 consumed inputs/counts/clocks/policy windows. Compact JSON:
12,443,795 bytes, SHA256
`fa9565bea925a66b2afaccb6e337a8dd5c3c2d0b52e65524575325e936b29323`.

The recorded policy has 68 WATCH, one ADVANCE and one STOP. At tick30000,
`motor_right` advanced (300ms left3/right6, +10Hz difference). At tick70000,
`playlist_exhausted` stopped with trigger `clip_window_end` (left6/right3,
−10Hz). That terminal trigger is the external 4s clip cap, not neural rejection
or preference. Actual frontend parsing accepts this v2 and historical real v1/A/B
files: tick29999 outgoing/no swipe; tick30000 incoming frame0/gesture;
tick30667 incoming frame2; tick32000 incoming frame6/no swipe.

Actual Chrome file loading, play/pause, boundary/terminal labels and the clipped
swipe passed. At tick30667 incoming frame2 had PTS5120/15360, MBON11=50.00Hz
and KC=3.10Hz; tick32000 showed the full incoming frame without swipe. Playback
at 1× advanced, pause held tick10994 and export restored tick30667 paused.
Independent EBML/PyAV inspection of the actual UI WebM confirmed **225 VP9
frames, 900x900, 7.500s**: 210 measured frames/7s plus 15 labelled hold frames.
PTS span 0–7467ms with 33/34ms intervals and explicit end7500ms. Decoded frame92
showed the mid-swipe/current incoming frame2; frame96 ended the swipe at3.2s;
frame224 was labelled terminal hold/STOP without swipe. The video is 2,486,947
bytes, SHA256
`1f21825de97cadb8645ddc46124ba7ad2e53ef3debcfcefc2c30b8803bf40e4c`.

Reuse the same ignored
`runs/measured-video-replay-fast-reels-20261102.json` for presentation work;
never pair 5× footage with old 1× measurements. Exact results/limitations belong
in the [fast-feed report](experiments/2026-11-02-fast-reel-feed-observation.md).
Raw media/runs/acceptance tools remain ignored. Broader mobile/accessibility/
cross-browser/live-FPS checks stay open; C1/formal/LLM work remain parked.

## Historical standard-video observation

The earlier 1×/v1 run used model
`e8d0e046e890418541ee9f0bb84065966228e756834f5bd7fb084f9ff5005ba8`,
with 105 inputs/420 bins over 3.5s and motor-right advance at 2.3s. Its actual
Chrome/UI export decoded to 120 VP9 frames/4.0s, including 15 labelled terminal
hold frames. Its source-specific tests, reviews, identities and exact artifact
hashes are preserved in the [standard-video report](experiments/2026-11-02-video-feed-observation.md).
This historical evidence does not accept the new fast-feed runtime or viewer.

## Historical Phase 1 A/B observation and export

The single fixed six-cycle/12s actual observation completed in **208.125s**
within its 240s wall budget, then ordinary verify/export both completed exit0.
It has 26 events, 24 segments, 1200 bins; export 218,993 bytes,
SHA256 `c362c7a7dc3e8d25054b6c644e293b85e6d7ce52a087724d564bfb6a3b256602`.
Independent raw-count/pixel/source checks and the actual frontend parser passed.
These are integrity/implementation checks, not scientific or capacity evidence.
See the [observation report](experiments/2026-11-02-measured-replay-observation.md)
for exact source bindings, counts and commands.

Phase 1 browser QA used the local ignored
`runs/measured-replay-v1-fullgraph.json`. After the user manually enabled
Chrome local-file permission, the real export loaded. Play at 0.5x advanced;
pause held 3.660s. Seek/Home, source disclosure and sampled MBON11/KC values
matched the raw bins. Desktop 650px and mobile 375px layouts were observed without
clipped motor labels or horizontal overflow. No automated setting write occurred.
The old 110,864-byte clip has only 17 VP9 frames/13.326s, median spacing 1003ms
and maximum 1008ms. End-pixel inspection did not satisfy animation quality;
the user's complaint is independently confirmed. Source/artifact checks are not
retrospectively upgraded into smoothness evidence.

Phase 1 replaces wall-clock capture with Mediabunny 1.65.0/WebCodecs timestamped
encoding at 900x900. The actual UI export is 4,113,326 bytes, SHA256
`2d670f3cd06c3f0fe2db023ea930fdbc80a7177663d879a95eb6578e1a739ee3`:
375 VP9 frames, seven clusters, 33/34ms spacing, PTS 0..12467ms and explicit
last end 12500ms. Independent PyAV decoding confirmed 375 frames/12.5s/900 square;
frames 0/8 visibly change body/wings within the same A segment. The final 15 frames
are a labelled presentation hold of source tick 120000, not new measurements.
The pose is absolute-time/reduced-motion-aware illustration, not validated behavior.

The genuine-video continuation now has source implementation and tests as
recorded above. Downloaded renditions and all raw runs/checkpoints/video outputs
remain ignored; do not pair reel footage with old A/B neural measurements.

## Implemented scientific foundation

Completed reviewed source slices provide native checkpoint restore/reset,
candidate-only interventions, complete/candidate/noncandidate hashes, bounded
schema-only NPZ reading, owner/artifact/current-source-bound native map context,
exact grid occurrence/raw-call capture and compact shared producer arithmetic.
The integer C/replay/washout correction is accepted: qualification rejects C<1,
confirmation C<=1, washout w>max(5*r,1), using actual counts before canonical Hz
conversion. Unavailable counts stay unavailable; no gate tolerance was added.
NumPy 2.4.6's private header API supports NPY1/2/3; lossy structured/subarray
extension templates are rejected. Protocol/raw formats and native core remain.

**Task7B4f.3b passed source review and bounded implementation acceptance.**
One `_DeclaredEvidenceAccumulator` shares existing declaration validation,
intake and reconciliation; all seven result fields, arithmetic, copy depth and
caps remain unchanged. Public/declaration wrappers still enumerate their full
iterables and finish only after normal EOF. Direct explicit indices may have
genuinely neutral gaps; first-seen branches and checkpoint-name records remain
causal. Embedded sequence framing gains no arithmetic authority. Single-use
finish closes before reconciliation and certifies no EOF or native proof.

Historical f.3b model-source identity (not the current replay source):
`89c7b75442ae8c74fe731d178f54cc03349a81eb58cb5c23f208260fbe502a1b`;
schema unchanged. Full analysis: **432 passed in 249.14 s**; focused **86 passed
in 5.04 s** overlaps it. Normal-host recorder/replay: **622 passed, one graph
opt-in skip in 45.16 s**; the actual MaleCNS zero-anchor context separately
**passed in 8.35 s**. All actual exit0/zero failures/errors, applicable frozen
two-file/all30/schema identities exact before/after. Independent pre-extraction
fixtures pinned all seven fields for both families: **14 passed in 1.48 s**;
API RED: **40 failed/14 passed in 5.30 s**, real exit1. Structural comparison
preserved all three moved blocks and prefix/suffix; no production arithmetic fix.
The source review preceded full-run completion; final acceptance separately
confirmed the completed full result, XML and unchanged identities.

User-approved priority, 2026-11-02: **measured-data Replay v1 before the full formal
assay; LLM later**. This changes product sequencing, not scientific criteria/claims.
C1 DEV26 RED→GREEN remains locally preserved, uncommitted/unreviewed/unaccepted;
it is not a cloud-continuation dependency. Formal integration is a paused workstream.
- [x] Bounded unprofiled first-training prefix completed exit0 on isolated accepted
  bytes: [83.785 s / 55,257,563 bytes / peak WS1,124,093,952 bytes](experiments/2026-11-02-fullgraph-unprofiled-prefix-pilot.md).
  PRE A/B/C/A-replay MBON11 is zero in all three windows; zero-anchor context is not training replay.
- [x] [PARTIAL base + T10](experiments/2026-11-02-fullgraph-partial-retention-pilot.md)
  completed exit0:785.922s,368,399,953 bytes,peak WS1,908,953,088 bytes; A exactly
  matches frozen/matched controls in all three windows. No complete controlled A−B effect.
- [x] Record/export one genuine 12s fullgraph observation and check its compact
  pixels/counts through the actual frontend parser.
- [x] Load the SAME recording in Chrome; check play/pause/speed/seek/Home, source
  mode, sampled telemetry and desktop/mobile layouts.
- [x] Preserve historical numerical/end-pixel checks; correct the earlier
  overbroad visual acceptance (17 frames did not meet smooth-animation quality).
- [x] Phase 1: timestamped 30fps export/illustrative motion, reviewed race fix,
  actual 375-frame/PTS/decode/visible-pose checks using the SAME recording.
- [x] Implement the reviewed real-video observation/motor-scroll contract,
  following the [animated replay plan](superpowers/plans/2026-11-02-animated-measured-replay.md).
  No fabricated activity/dopamine interpretation/semantics or automatic assay/qualification runs/C1 return.
  Historical A/B and standard-video raw/runtime/browser/encoded-file checks passed.
Diagnostics grant no integrated capacity/history/config/freeze; no causal comparison
with profiled630s or automatic inventory return. One allocation/call may exceed guards.
The prior Viewer timing gate is superseded only for this explicitly approved replay slice; LLM stays later.
THREE verification boundaries and all f/g/LF/formal gates remain open.

## Historical evidence — not current-source acceptance

### Task7B4f.3a — standalone grid composition on earlier source

**Task7B4f.3a passed source review and bounded implementation acceptance.**
`_GridMeasurements(value, inventory, context, metadata)` exposes `consume(event)`
and `finish() -> _GridAssessment`. The genuine standalone driver retains two
exhausted passes, context intake/final checks, all-manifest checkpoint ownership
and existing grid-final/legacy-terminal policies. No engine, issuer or policy
switch was added; component summaries do not certify EOF or provenance.

Historical f.3a model-source identity:
`b8f0fcee7115f387f34a13d8e9651064290dc70626ed649f8f8bed32cce62ebb`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Focused grid tests: **68 passed, three deselected in 118.12 s**, exit0.
Normal-host recorder/replay: **622 passed, one graph opt-in skip in 43.44 s**;
the actual MaleCNS zero-anchor context and grid-baseline archive cases separately
**passed (two tests) in 16.71 s**, exit0. One-configuration native acceptance:
**one passed in 588.35 s**, exit0. All runs had zero failures/errors; applicable
two-file/all30/schema identities matched before/after and final acceptance passed.
The separately passed 588.35 s configuration test covers genuine partial
three-point/discarded-source mutations and eight-unit lifetime checks;
it is not complete96 coverage.

The one-configuration artifact contains eight bindings/twelve points, 129
checkpoints (1,204,732 bytes), and 7,585 events (303,809,000 bytes), events SHA256
`5a8dbf5f8c4a55fe55c5e6d25ce08aa890becb08ef763318ed83532b5373c576`.
It is unsealed/inconclusive and covers only one of twelve configurations on a
declared tiny-native fixture. Original-file count/hash auditing reissues no proof.
Graph tests briefly overlapped that run: these are functional durations, not
controlled capacity measurements. No current whole-project/408/full MaleCNS
assay, positive eligible-grid→selected lifecycle, freeze/config or support claim.

This f.3a configuration/grid evidence is not upgraded to current f.3b source.

### Task7B4f.2 — corrected bounded checker on earlier source

**Corrected Task7B4f.2 passed bounded source review and implementation acceptance.**
One checker collects at most five chronological actual prior records, twelve
operations and sixteen PRE/one POST rows in their actual interleaving. Finish
consumes the actual diagnostic once; map/model binding precedes W decoding.
The unchanged-signature adapter withholds success through EOF, drains after
semantic errors and propagates iterator/final-binding failures. Capture payloads
are released; compact late watches retain no history or proof authority.

For EVERY POST pair, intervention-event matching uses the actual source-origin
ID, including ordinary training sources, so malformed aliases cannot be silently
ignored; intervention-checkpoint roles remain restricted to INTERVENTIONS.
Hash-selected anchors are checked regardless of
changed origin/source. The extracted comparison kernel/equations, schema and
native core are unchanged; no global evaluator/lifecycle/cap was added.

Historical f.2 model-source identity:
`17e784092d0579680a8f0007699fb72275d82f9649a362eb2466b74d1ac13887`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Corrected worker frozen-r2 equals the accepted snapshot's r1 bytes. Focused:
**118 passed, 260 deselected in 117.82 s**; full analysis: **378 passed in
242.79 s**, exit0, zero failures/errors/skips. Focus overlaps full, not additive.
Normal-host recorder/replay: **622 passed, one declared opt-in skip in 43.74 s**,
exit0; the skipped actual MaleCNS zero-anchor map-context case separately
**passed in 8.42 s**, exit0, no skips/errors/failures. Applicable two-file/all30/
schema identities matched before/after; stored final acceptance audit passed.
These are bounded functional checks, not controlled capacity measurements.

R0 source aff5948… was rejected despite 372 green tests: ordinary-POST source-ID
intervention aliases were filtered out before the unchanged kernel could reject
them. Real fix RED: **four failed/two passed in 11.03 s**, exit1; two minimal
source clauses and six regression cases closed the Important finding, with no
remaining source-review findings. The first API RED retains six failures/log/XML
but no separate pytest subprocess exit; its shell exit is not pytest evidence.
Neither that omission nor earlier green R0 tests is relabeled acceptance.

This earlier acceptance is not upgraded to current f.3b's package identity.

### Task7B4f.1 — declaration arithmetic on earlier source

**Task7B4f.1 passed bounded acceptance on its earlier source.**
A declaration-based reducer now accepts plain scientific declarations; the
existing confirmation wrapper still validates its Frozen config. `_assess` chooses integer C
rules: qualification rejects counts below one; confirmation rejects counts at
or below one. Other assessment equations, native core, schema and public trust
boundaries are unchanged. Public strict freezing remains future f.5 work.

Historical f.1 model-source identity:
`73994df1e35e1bd51407d863f42733551b994b8d2dbc8503a60bda33597e35ef`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
The sole review finding was an old mutation hook not forwarding the new keyword;
its two-line test-only correction retained all eight integrity oracles and passed
independent closure review. R1 full analysis: **345 passed in 184.58 s**, exit0,
no failures/errors/skips. The focused **130 passed in 37.26 s** and hook-only
**eight passed in 14.41 s** overlap that full file and are not additive.

Related-module R0 compatibility on identical package source: **1,305 passed,
four skipped in 953.91 s**, exit0, no failures/errors. R1 changed only the two
test-hook lines afterward. Skips were complete96, actual MaleCNS grid baseline,
actual MaleCNS zero-anchor map context and a Windows-junction permission case.
The latter three separately **passed on the normal host in 15.55 s**, exit0,
no failures/errors/skips. Complete96 was not repeated. Each applicable run's two
frozen paths, all 30 source members and schema matched before/after. Final stored
acceptance audit passed; the full analysis process completion is externally
reported and supported by its original log/XML/result and identity records.

Development failures remain failures: initial RED had 114 failed/16 passed in
23.92 s; first GREEN had 81 fixture failures in 22.28 s; R0 full analysis had
337 passed/eight old-hook failures in 185.36 s. None is counted as acceptance.
No current whole-project/all-eight/complete96/full MaleCNS assay pass, formal
qualification/configuration, response-history proof or capacity is claimed.

This earlier f.1 evidence is not upgraded to the current f.3b source. Strict
global qualification/freezing remains separate future work.

### Task7B4e.3 — complete repeats on earlier source

**Task7B4e.3 and parent e implementation acceptance completed on this earlier source.**
The private True-qualification producer now executes independent native pairs,
measured window-stop response/W resolution, complete tails and exact diagnostic
references. False/confirmation retains its existing owner and behavior; True
returns the actual last successful repeat engine after diagnostic append and
scratch cleanup. f still owns global reconciliation and final lifecycle.

Historical e.3 source:
`2d07f37e85935f78b522bccb0a60d7f2b9f1d0e5a1475c8d306f12b995766da8`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Independent source review closed the retained-snapshot/anchor mismatch finding.
R1 focused: **78 passed, 89 deselected in 189.24 s**, no failures/errors/skips.
Later matrix-oracle additions and the raw/manifest sequence correction changed
tests only; their independent reviews passed. The earlier R2 True51 run failed
in 126.07 s on the test-only manifest/event_sequence mapping; it is not a pass.

Actual R3 True51: **1 passed in 155.54 s**, exit0, no failures/errors/skips.
The declared tiny-native fixture produced 51 diagnostics/96 logical cells,
130 production factories, 16 native black-retention anchors and nine durable
checkpoints including baseline. All eight conditions/intervention routes and
exact sixteen-fold PRE reuse were checked; every one of the 51 pairs passed
the e.2 actual fixed-prefix-to-EOF comparator, native window-W/raw-reference and
actual last-owner checks. Paired nine-comparison checks verified 21 production
factories.

Actual R3 True408 on the **four-node tiny-native fixture**:
**1 passed in 2,333.98 s**, runner 2,334.437 s, exit0, no failures/errors/skips.
The test checked 408 diagnostics (24 PRE + 384 POST), 768 original logical cells,
1,033 production factories before separate native verification, 128 native
black-retention anchors and 65 durable checkpoints including baseline. Every
PRE serves exactly sixteen condition/T cells. All 408 pairs passed the actual
native boundary/W/whole-operation/reference lookup oracle; nine selected pairs
also passed the full external e.2 fixed-prefix-to-EOF comparator, covering every
cohort, each intervention/T combination and PRE. This was not 408 full-prefix scans.

One actual MaleCNS zero-anchor map-context case **passed in 8.28 s**, exit0,
without failures/skips. These R3 runs matched two frozen paths, all 30 source
members and schema before/after. This is one context, not a full MaleCNS assay.
Earlier opt-in-off compatibility for the entire assay test module: **166 passed,
three declared opt-in skips in 1,426.94 s**, exit0, no failures/errors. Skips were
False all-eight, True51 and True408; the True nodes passed separately above. R3
source/test/schema bytes matched before/after. R1 focused and R3 broader coverage
overlap and are not additive. No current whole-project/complete96-grid/full
MaleCNS assay pass is claimed.
These are recorded-consistency/black-retention checks, not response or upstream
native-history attestation, scientific qualification or learning/capacity support.

Independent original-file audit passed the True51 prefix: **2,025 events /
5,274,722 bytes**, 128 branches, nine checkpoints/82,878 bytes, three physical
PRE and 48 POST comparisons/96 logical cells. Events SHA256:
`7662e4dc54eb5d8291938c835d4ea2fd34830e8cbd5f3562f839aade1ebd6cc6`.
It remains unsealed without scientific outcome/terminal/configuration. The audit
reissued no native proof; raw artifacts remain local-only.

The independent original-file/count audit also passed the True408 prefix:
**16,088 events / 42,057,618 bytes**, 1,010 branches, 65 checkpoints/598,897 bytes.
Events SHA256:
`78b660fd566045feb058ca49143e2487e14de4a63ac2e87e7d50ec7352790ebb`.
It remains unsealed with no scientific outcome, terminal or frozen configuration.
The audit reissued no native proof. This completes e's tiny-native implementation
acceptance; f's production global reconciliation/final lifecycle and g's integrated
capacity, LF/source-freeze and formal qualification gates remain open.

### Task7B4e.2 — accepted diagnostic foundation on earlier source

**Task7B4e.2 R1 passed independent source review and bounded Windows acceptance.**
Closed qualification_replay structural/schema intake, float64 W-pair projection
helpers and independent external-iterator pair comparison are implemented.
The corrected review findings cover exact source/recipient occurrences and
present-cell response fields, including cumulative pre-window PPL101 counts.
Plain metadata/execution/source/start expectations confer no authority; actual
native or genuine-context maps must bind before numeric decoding. Every target
operation, whole scientific telemetry, tail and EOF remains checked. These are
recorded-consistency checks, not isolated response/history attestation.

Historical e.2 R1 model-source identity:
`4527956304d4d1630c415a190d4a475912cbe4ca028b4abb63baa859f9af13ae`.
Schema SHA256:
`3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Focused R1 tests: **115 passed, 519 deselected in 62.55 s**, exit0, no
failures/errors/skips; all five owned paths and 30 source members matched
before/after. Actual native PRE, ordinary POST at 10,000/70,000 ms, SHAM and
[100,300) tonic-PPL101 fixtures exercise the local comparisons. R1 affected-file
compatibility: **853 passed, one declared opt-in skip in 172.38 s**, exit0,
no errors/failures. Its sole skipped fullgraph zero-anchor qualification-context
case separately **passed on actual MaleCNS in 7.89 s**, exit0, no skips/errors.
All three normal-host junction cases passed. Both runs matched all five frozen
paths, 30 source members and schema before/after; independent acceptance-file
audit passed. Focused/compatibility coverage overlaps and is not additive.
No whole ordinary/all-eight/complete96 run was repeated on this source.

That e.2 source kept True production unavailable/False-only; current bounded
producer work is reported separately above. It does not upgrade these older
tests to the new source; e.3's source-specific 408/768 acceptance is recorded above.

### Task7B4e.1 — accepted reference foundation on earlier source

**Task7B4e.1 passed independent source review and bounded Windows acceptance.**
Only recorder.py gained the private `_append_reference` helper; public `append`
and its None return remain byte-for-byte unchanged. The helper returns claimed
`{sequence, scientific_sha256}` after exactly one complete successful append,
including write/flush/raw-digest update, with healthy/open and exact +1 position
checks. Failures/drift return no reference. It adds no cache, prefix scan, trust
issuer, crash-durability guarantee or proof; f must authenticate actual bytes.

Historical e.1 Windows model-source identity:
`293c8a721f0a18ba9dcf0baf726437b8455133d67cf343bb9fb1c69ca617a060`.
Schema remains
`c56a64f91bf08b2f3c379a4720d4be3a5c2d1743c1c09394d2483f23d61af115`.
Recorder/replay compatibility: **592 passed, one declared opt-in skip in 41.95 s**,
exit0. The sole skipped fullgraph zero-anchor qualification-context case passed
separately on actual MaleCNS: **1 passed in 7.93 s**, exit0, no skips/errors.
All three junction cases passed on the normal host; an earlier sandbox permission
skip is not a junction pass. All 30 source members and both frozen source/test
paths matched before/after these runs. No whole ordinary suite, all-eight matrix
or complete96 grid was repeated on this source.

The e.1 slice added no qualification_replay schema/comparator or True production.
Later e.2 source/schema work is reported separately above; none upgrades the
earlier e.1 test evidence to the current source.

### Task7B4d — accepted production on earlier source

**Task7B4d passed independent source review and Windows runtime acceptance.**
The private caller-owned producer accepts plain qualification declarations and
an exact authenticated baseline, preserves genuine confirmation wrappers and
native candidate-only transfer checks, and uses bounded source lookup through
EOF. Fresh prefix/sealed verification checks actual current engine groups.
The source finding and later test-only bookkeeping correction passed independent
review. This is an intermediate producer, not formal source freeze or qualification.

Historical d Windows model-source identity:
`48af9d39b3ae8f0c9e965dbac6d0e987e0e23dda8fa68895f3807a6f98684ac3`.
Schema SHA256 remains
`c56a64f91bf08b2f3c379a4720d4be3a5c2d1743c1c09394d2483f23d61af115`.
All 30 packaged source members and the applicable frozen source/test paths
matched before and after each acceptance run. R1 focused: **124 passed, one declared opt-in skip in
1,271.88 s**. R1 ordinary: **2,333 passed, seven declared opt-in skips in
1,909.58 s**, no errors/failures; four actual MaleCNS graph cases separately
passed in **26.31 s**. R2 then changed only two test files: two native accounting
regressions passed in **210.06 s**. Package/schema stayed unchanged; the whole
ordinary suite was not repeated on R2 tests. R1/R2 collection each found 2,340
cases. Both R2 matrix cases below passed without skips/errors/failures.

Baseline authentication adds one quiescent restore on the existing preflight
engine, without another factory, observation or clock advance. The 64 actual
acquisition/PRE baseline trials stay separate from this authentication-only
restore; the legacy matrix still asserted **625 production factories**, excluding
verification factories.

| Actual R2 matrix | Selected qualification producer | Legacy confirmation owner |
| --- | ---: | ---: |
| Pytest result | 1 passed, exit0, 1,532.18 s | 1 passed, exit0, 1,721.32 s |
| Trainings / interventions / anchors / logical responses | 40 / 24 / 128 / 768 | 40 / 24 / 128 / 768 |
| Checkpoints / bytes | 65 / 598,094 | 67 / 616,476 |
| Events / bytes | 14,048 / 28,305,472 | 14,048 / 28,219,135 |
| Scientific outcome | Unavailable: f not integrated | Unsupported, 136 negative gates |

Both use declared **tiny-native fixtures**, not formal MaleCNS qualification.
The 768 logical cells comprise 384 POST originals and 24 physical PRE trials,
each PRE reused sixteen times. Selected checkpoints are 64 source occurrences
plus one caller baseline; its artifact remains an unsealed prefix without
terminal/run.json/configuration. Real prefix verification asserted 128 native
black-retention anchors; legacy prefix and seal each asserted the same genuine
anchor inventory. These checks authenticate black retention/maps, not upstream
training or response history. Later e.3 response-repeat acceptance is recorded
above on its own source revision.

Independent original-file/count audits passed both artifacts; they reissued no
native proof. Event SHA256: selected
`ad4484543ee69959a524261352afefb31c5e7c0128524e663737845160c6470b`;
legacy `e15c8f459501d4a75d5812a7901c3690d20464586ad46dd5ea4060cb2ed3d779`.
Both bound all eight factors and seven input hashes. Raw artifacts remain
local-only. No formal qualification, production configuration or whole-assay
capacity follows from these matrices or the graph compatibility cases.

### Earlier grid and resource evidence

- Accepted c.2b source:
  `64041111c7cf3edfaf51128e071b79d939875937f810790c00d1425458c6e60e`.
  Its complete96 tiny-native prefix/seal case passed in **5,124.53 s**:
  96 units/144 points, 89,831 events, 1,478 checkpoints and 3,594,389,820 event
  bytes; zero-anchor checks authenticated maps/context, not training replay.
  This costly case was **not repeated on d, e.1, e.2, e.3, f.1, f.2, f.3a or f.3b source**.
- The [detail-on fullgraph prefix sample](experiments/2026-11-02-fullgraph-detail-prefix-pilot.md)
  used that same c.2b source at commit `21f788342b276e1d8a323f572e37e248542948d6`.
  Its final sample was 630.546 s / 55,267,543 dedicated bytes /
  1,089,613,824 bytes lifetime peak working set, within 30 min/8 GiB/4 GiB limits;
  later report writing/exit are excluded. The 1,617,776,145 profiler dispatches
  have unmeasured dispatch overhead; timings cannot establish unprofiled
  throughput/capacity. g requires a controlled unprofiled follow-up.
- Task8 complete Windows opt-in acceptance: **1,449 passed in 3,237.62 s**,
  no skips/errors/failures, including the genuine all-eight case. Source identity:
  `3c712e0b6b30dc83e3048db2bab18a12f8918c87b5723a52c17bceb73a88faa9`.
  Its tiny-native matrix had 40 trainings, 24 interventions, 768 responses,
  128 anchors, 67 checkpoints and 14,048 events: **unsupported, 136 negative gates**.
- Last accepted boundary-correction source before c.2b:
  `aa2ffb172d9694e1d727199f533eaf2ec59432c3445cf758cccfd4ed5a6c5b29`.
  Ordinary Windows: **2,230 passed, four declared opt-in skips in 1,064.83 s**;
  the three graph cases passed separately in **18.03 s**. All-eight was not repeated.
  Earlier per-slice commands/counts remain in the current plan and repository history.
- The linked 10-second pilot used source
  `ec6474b3693beb49a9dde28c0e02c3cca9987dad`; the 70-second pilot used
  `460f5b046e4e18df2d147c18ba73899ac660032a`. The latter measured six factories,
  452 calls, 179 events and one anchor, with both genuine black replay passes.
  These are bounded resource samples, not learning or whole-assay capacity.

Reports retain exact source/schema/native/checkpoint/recipe bindings. Their raw
artifacts are local-only; use matching source bytes to reverify them. On a new
compiler/platform generate new evidence, never relabel Windows identity as Linux.
Repeat relevant complete matrices after later source-bearing integration;
historical unsupported results cannot satisfy a new source's acceptance gate.
Interrupted development runs are never counted as passes.

## Live remaining work

- [x] Implement/review measured observation recording/export and viewer source;
  complete bounded real fullgraph recording/export and independent raw/parser checks.
- [x] Complete same-recording Chrome playback/sample/desktop/mobile QA.
- [x] Correct prior video-quality acceptance and complete Phase 1 timestamped
  export/motion/source/actual encoded-file checks without another native run.
- [x] Implement genuine-video input and recorded motor-policy replay; viewer review passed.
- [x] Close independent backend review and complete one bounded video fullgraph run,
  ordinary verification/compact export and independent raw/source-policy audit.
- [x] Complete actual browser/parser and encoded-file acceptance using that same artifact.
- [x] Implement/review closed 5× fast-feed/v2 and deterministic 200ms swipe; preserve v1.
- [x] Close one bounded actual fast-feed pilot and independent raw/parser audit.
- [x] Close same-artifact Chrome/boundary and encoded-file QA: 225 frames/7.5s.
- [x] Implement strict imported event proposals, actual paired-card observation,
  measured selection and immutable plan; close source reviews and one bounded
  actual2s pilot/raw audit with left2/right1 → Sunset House.
- [x] Close same-artifact event Chrome boundary/plan download and150frame/5s video
  acceptance. Preserve strict old readers and the authored-example/API distinction.
- [x] Join fast-feed and cards in one fresh continuous engine, close independent
  source reviews and one actual9s pilot/raw audit; preserve old export bytes.
- [x] Close same-artifact session Chrome/global-boundary/download and360frame/12s
  combined movie acceptance; no intermediate hold or clock/state reset.
- [ ] Continue longer-feed work when requested; reuse validated current data for UI
  changes and keep live LLM/formal integration separately gated.
- [ ] Harden event-export raw-run intake with pre-allocation manifest/JSONL
  bounds before accepting arbitrary foreign runs. Current local exporter uses
  generic verify_run before its output-size bound; oversized foreign inputs can
  exhaust memory. No service/deployment or arbitrary hostile-run safety claim.
- [x] Add a separate offline-default proposal transport with explicit key/model/
  token/cost opt-in and local receipts; preserve JSON import and measured choice.
- [ ] Exercise one actual API request only after explicit local key/model/cost
  configuration. Offline fixture tests are not live compatibility evidence.
- [ ] Add optional post-choice narrative separately if needed; keep selected
  plan immutable. Do not relabel authored examples as live model requests.
- [ ] Define authenticated old/trained-state resumption separately if needed;
  the current session starts fresh and retains state only within that one run.
- [ ] Complete broader accessibility/cross-browser checks and separate the
  interactive orbit hint from the event overlay's top edge; preserve experimental WIP.
- [x] Complete c.2b source review, ordinary/actual graph/full tiny-native grid
  acceptance and exact reviewed-source checks.
- [x] Execute, independently review and publish the bounded actual MaleCNS
  detail-on first-training prefix with fresh context verification and reduction.
  The linked report preserves exact workload, identities and sampling limits.
- [x] 7B4d: caller-owned selected native execution, exact baseline/occurrence
  authentication, preserved confirmation wrappers/native transfer checks and
  actual selected-eight/legacy confirmation-eight acceptance.
- [x] 7B4e.1: private successful-append reference foundation; public append unchanged.
- [x] 7B4e: measure all 408 physical response repeats and actual state resolution;
  bind exact independent parents/raw bins. Never borrow frozen tolerance or invent 0.
  e.1/e.2 foundations and e.3 tiny-native 9/51/408 acceptance are complete.
  Global f assessment/freezing remains separate and unimplemented.
- [x] 7B4e.2: closed diagnostic/schema intake, bounded W projections and independent
  external-iterator local pair comparison; no True-production wiring.
- [x] 7B4e.3: source-reviewed True producer and actual tiny-native 9/51/408 checks;
  whole assay-module compatibility and separate complete repeat acceptance passed.
  No full MaleCNS assay, scientific outcome or capacity approval follows.
- [x] 7B4f.1: shared declaration reduction and explicit integer C assessment;
  bounded analysis/related-module/normal-host acceptance recorded above.
- [x] 7B4f.2: corrected bounded pair checker and full-EOF adapter; bounded
  source/analysis/recorder/replay/actual map-context acceptance recorded above.
- [x] 7B4f.3a: composable standalone grid measurements and bounded one-configuration
  acceptance; complete96 remains deferred to stable f.3d.
- [x] 7B4f.3b: explicit-sequence accumulator, preserved arithmetic/caps/EOF wrappers;
  bounded analysis/recorder/replay/actual map-context acceptance recorded above.
- [ ] 7B4f.3c/d: parked local C1 WIP; resume only if needed under a separate
  explicit release, not automatically after diagnostics or Replay v1.
  Keep genuine partial/native checks separate from internal declared fixtures;
  positive eligible-grid→selected native integration remains unavailable.
- [ ] 7B4f: integrate selected inventory with authenticated grid assessment, one
  evidence-bound terminal and independently checked seal; sealed-only engine-free
  public freezing. Complete valid negatives never create a production config.
- [ ] 7B4g: actual assay CLI/fresh-factory routing and integrated detail-enabled
  grid/archive/stream capacity with THREE verification boundaries. Include controlled unprofiled
  phase/resource measurement before runtime or capacity decisions; profiled pilot
  durations cannot establish throughput. Current CLI lacks `assay`.
- [ ] Prove selected/replay emissions fit the intended 4850 branches/1602
  checkpoints/8099 relevant events before enabling qualification-only cap 5120.
  Operational cap 4096 and limits of 2048 checkpoints/10000 relevant events
  remain; raw calls/bytes need separate accounting.
- [ ] Finish source-bearing work, independent review and final complete acceptance.
  Pin LF checkout for packaged Python/C++, normalize once and verify exact identity.
- [ ] Only then Task9: clean source freeze and formal fullgraph qualification.
  If all gates pass, review/commit a genuine production config before reading
  held-out confirmation; otherwise publish the honest negative/inconclusive result.
- [ ] Execute/independently verify frozen confirmation and reproducibility.
  User-approved measured-data Replay v1 may precede this; LLM and scientific claims remain separately gated.

Any packaged .py/.cpp change invalidates formal qualification/config/confirmation
identities and restarts the source-freeze gate. Content hashes are not proof of
training history. No sample checkpoint-size multiplication establishes capacity.

## Fresh Linux/cloud checkout

Local .venv, Windows Zig/DLL, graph data, prepared arrays, checkpoints, runs and
.tools probes are intentionally absent. Prerequisites: Python 3.12.14, uv, Node.js
and a C++17 compiler exposing c++. The exercised Windows versions are uv 0.12.15,
Zig 0.16.0 and historically Node 25.9.0 for the native/data workflow; the viewer
was checked with Node 24.21.0/npm 11.19.0 and requires Node >=24. Unix
compiler/platform execution is not yet locally verified or pinned. See
[Getting started](getting-started.md) for platform setup.
These are instructions, not new Linux results; record actual versions/limitations.

```sh
git branch --show-current
git status --short
git remote -v
uv --version
node --version
c++ --version
export UV_PYTHON_INSTALL_DIR="$PWD/.tools/python"
uv python install 3.12.14 --no-bin --cache-dir .tools/uv-cache
uv sync --locked --extra test --cache-dir .tools/uv-cache --python 3.12.14
.venv/bin/python -m pytest tests/experiment/test_protocol.py -q
.venv/bin/python -m pytest tests/experiment/test_recorder.py tests/experiment/test_replay.py -q
```

The latter uses tiny native fixtures and needs the compiler, not released graph
inputs. Ordinary full pytest does need downloaded/prepared data and native builds.
Report unavailable dependencies/permissions honestly; do not weaken locks or
hide skips behind a passing label.

For fullgraph work allow the 1.1 GB source download plus derived/runtime space.
Staging uses hard links: source/runtime must share a filesystem. Set
FLY_CONNECTOME_SIM_DATA before imports when relocating runtime and retain it
through staging/preparation/verification. Raw/downloaded/runtime files stay out of Git.

```sh
node scripts/download-connectome.mjs
.venv/bin/python -m fly_connectome_sim.data verify-sources data/malecns-v1.0
.venv/bin/python -m fly_connectome_sim.data stage data/malecns-v1.0
.venv/bin/python -m fly_connectome_sim.neural.connectome malecns_v1
.venv/bin/python -m fly_connectome_sim.neural.prepare
.venv/bin/python -m fly_connectome_sim.data verify-prepared
.venv/bin/python -m pytest -q
FLY_CONNECTOME_SIM_FULL_TEST=1 .venv/bin/python -m pytest -q
```

Coordinate costly opt-in/full runs; do not duplicate an active acceptance run or
call interruption success. Do not run formal qualify yet or change frozen gates
from confirmation output. A cloud checkout requires its own evidence, not private notes.
