# Associative Plasticity Assay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether the declared PPL101-modulated KC→MBON11 state produces a persistent, stimulus-specific MBON11 response change in the MaleCNS-constrained model, then assess lateral motor evidence separately.

**Architecture:** Keep the existing full-graph engine and checkpoint format. Extend the project-owned experiment package from factorized stimuli and schedules through a gap executor, pathway measurements, qualification, an atomic candidate-state intervention, verified run artifacts, a frozen analysis, and held-out execution. The motor adapter consumes measured motor telemetry only after the primary assay is classified.

**Tech Stack:** Python 3.12, NumPy 2.4.6, C++17 native core, pytest, Windows PowerShell; use `.venv/Scripts/python.exe` in commands below (on Unix, `.venv/bin/python`).

**Spec:** `docs/superpowers/specs/2026-09-24-associative-plasticity-pivot-design.md`; retain the broader boundaries in `docs/specs/fly-event-planner.md`.

**Replay refinement:** The bounded occurrence/content, black-retention and
verification contract is defined in
[`2026-10-02-replay-anchor-contract.md`](../specs/2026-10-02-replay-anchor-contract.md).

**Candidate-state refinement:** Production candidate/noncandidate content digests
follow [`2026-10-03-candidate-state-digest-contract.md`](../specs/2026-10-03-candidate-state-digest-contract.md).

**Strict qualification refinement:** Remaining integration follows
[`2026-11-01-strict-qualification-contract.md`](../specs/2026-11-01-strict-qualification-contract.md).
The [six-slice f implementation plan](2026-11-02-strict-qualification-integration.md)
records exact contracts and ownership. f.1/f.2/f.3a/f.3b are accepted;
f.3c design is ratified; C1 is parked local uncommitted/unreviewed WIP, not accepted; later gates remain open.

## Current checkpoint and live remaining work — 2026-11-02

Current product source adds [bounded event export intake](2026-11-07-bounded-event-intake.md)
to the existing verifier as opt-in limits on four event/session exports. Defaults,
prefixes, native equations and scientific gates stay intact; old formal source
identities are invalidated and formal integration remains parked. Exact source
and evidence: [intake report](../../experiments/2026-11-07-bounded-event-intake.md).

The completed proposal source slice is the separate
[proposal transport](2026-11-06-event-proposal-transport.md): offline request
preparation plus explicit key/model/token/cost opt-in, using the unchanged JSON
import and measured choice. No API key is configured and live compatibility
remains unverified. It changes no neural equations, assay gates or plan authority;
new packaged source invalidates prior formal identities. Formal integration stays parked.

The completed product work follows the [continuous session plan](2026-11-03-feed-event-session.md):
one fresh engine observes fast-feed then event cards,without reset/restore; one
actual9s run and360frame/12s combined movie passed source/raw/Chrome/encoded
checks. Its historical36-member model is
`d4b72b01f14c4c4ec1266f976692fa6bf7dc91b3b83ed40f6f5540ab25a7ec9c`;
schema unchanged. This source-bearing integration invalidates old formal
identities and proves no causal content/learning effect. Exact scope/evidence:
[session report](../../experiments/2026-11-03-feed-event-session.md).

The historical standalone [event-choice plan](2026-11-02-event-choice-milestone.md) delivered
strict imported proposals become actual paired visual cards and a measured
left/right/defer selection with an immutable plan. The user released this bounded
product slice; live LLM transport and formal science stay separate. Its historical
35-member model is
`e0bfc0ef08b44beafababa8598a0f902a9dcdc75e71d07f626f79fe5ed2c1275`;
schema unchanged. This source-bearing addition invalidates old formal evidence
identities; no qualification or learning claim is made.
Independent reviews closed, one actual2s run chose left from2:1 motor spikes,
and same-artifact Chrome/150frame5s export acceptance passed. See the
[event-choice report](../../experiments/2026-11-02-event-choice-observation.md).

The historical [fast-feed plan](2026-11-02-fast-reel-feed.md) delivered
explicit 5× media sampling, 3–4s per clip and a 200ms illustrative recorded-action
swipe, with normal simulation time. Default standard/v1 remains compatible.
Its historical33-member model is
`132b9c00a2a7d3d5da15963024abf85a0a31209d7f59f5903dd4edd9298a0ac2`;
schema remains `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Source review/focused tests, the actual 7s fast-feed pilot/raw/parser audit
and same-artifact Chrome/encoded-file checks passed. The [handover](../../cloud-handover.md)
and [fast-feed report](../../experiments/2026-11-02-fast-reel-feed-observation.md)
are authoritative for current evidence and TODOs. Historical [standard-video](../../experiments/2026-11-02-video-feed-observation.md)
and [A/B](../../experiments/2026-11-02-measured-replay-observation.md) results
remain separate/source-specific. C1, formal qualification/freeze/confirmation
and live LLM transport stay parked; integrity checks confer no scientific support or validated
motor behavior.

The early task-level RED/GREEN boxes are historical execution instructions, not
the current backlog. Tasks 1–6, strict analysis 7A, motor-only Task8 and source
slices 7B4a–e/f.1/f.2/f.3a/f.3b are implemented and accepted. Historical f.3b source:
`89c7b75442ae8c74fe731d178f54cc03349a81eb58cb5c23f208260fbe502a1b`;
schema unchanged. One explicit-sequence accumulator preserves existing declaration
validation/arithmetic/reconciliation, all seven fields, copy depth and caps.
Wrappers still enumerate complete iterables and finish only at normal EOF;
direct single-use finish closes before reconciliation and grants no EOF proof.
Gaps are genuinely neutral only: first-seen branches/checkpoint-name records
remain causal; optional embedded sequence framing gains no arithmetic authority.

Full analysis: **432 passed in 249.14 s**; focused **86 passed in 5.04 s**
overlaps full. Normal-host recorder/replay: **622 passed, one graph opt-in skip
in 45.16 s**; separately actual MaleCNS zero-anchor context **passed in 8.35 s**.
All actual exit0/no failures/errors, two-file/all30/schema before/after identities
exact; final acceptance passed. Source review passed before full completion;
the final result/XML/identities separately closed that pending runtime gate.
Independent pre-extraction capture: **14 passed in 1.48 s**, all seven fields/both
families; missing-API RED **40 failed/14 passed in 5.30 s**, real exit1.
All three moved blocks/prefix/suffix preserved; no production arithmetic fix.

The [unprofiled first-training prefix](../../experiments/2026-11-02-fullgraph-unprofiled-prefix-pilot.md) completed exit0:83.785s,55,257,563 bytes,peak WS1,124,093,952 bytes. PRE MBON11 is zero in all three windows; context with zero anchors is no training replay.
The [PARTIAL base + T10 diagnostic](../../experiments/2026-11-02-fullgraph-partial-retention-pilot.md) completed exit0:785.922s,368,399,953 bytes,peak WS1,908,953,088 bytes. A exactly matches frozen/matched controls; no complete controlled A−B effect or learning proof.
**User-approved product sequence, 2026-11-02:** actual compact measurement recording/export → smooth3D Replay v1 BEFORE the full formal assay; LLM later. Scientific gates/claims are unchanged. C1 is locally preserved, uncommitted/unreviewed/unaccepted, not a cloud dependency; formal integration is paused, without automatic additional assay/qualification runs or inventory return. Separately bounded real Replay v1 observation recording is allowed.

Historical f.3a source:
`b8f0fcee7115f387f34a13d8e9651064290dc70626ed649f8f8bed32cce62ebb`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Composable `_GridMeasurements` preserves the genuine standalone driver's two
exhausted passes, intake/final context checks, all-checkpoint ownership and
grid-final/legacy-terminal policies. Component finish grants no EOF/proof authority.
Focused grid tests: **68 passed, three deselected in 118.12 s**. Normal-host
recorder/replay: **622 passed, one graph opt-in skip in 43.44 s**; separate actual
MaleCNS context/grid-baseline archive tests: **two passed in 16.71 s**. Separately,
one configuration **passed in 588.35 s**. All exit0/zero failures/errors; applicable
two-file/all30/schema identities matched before/after; final acceptance passed.

One of twelve configurations has eight bindings/twelve points, 129 checkpoints
(1,204,732 bytes), 7,585 events (303,809,000 bytes), events SHA256
`5a8dbf5f8c4a55fe55c5e6d25ce08aa890becb08ef763318ed83532b5373c576`.
This declared tiny-native artifact is unsealed/inconclusive. Original-file
count/hash audit reissues no proof. The separately passed 588.35 s configuration
test also covers partial three-point/discarded-source mutations and eight-unit
lifetime checks.
Brief graph/configuration overlap means functional durations, not capacity evidence.
Complete96 remains deferred to stable f.3d; no current whole-project/408/full
MaleCNS assay, positive native lifecycle/configuration, formal freeze or capacity.

This f.3a configuration/grid evidence is historical, not current f.3b acceptance.
Genuine component/native checks do not establish preceding eligibility;
positive native eligible-grid→selected E2E remains unavailable.

Historical corrected f.2 source:
`17e784092d0579680a8f0007699fb72275d82f9649a362eb2466b74d1ac13887`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
One bounded collector feeds the unchanged comparison kernel only at actual
diagnostic finish; the existing wrapper retains full EOF/late-event behavior.
For ALL POST pairs, intervention-event selectors match the source-origin ID;
intervention-checkpoint roles remain INTERVENTIONS-only. This corrected the
Important ordinary-POST filtering regression without changing equations or wire.

Corrected worker frozen-r2/accepted r1: **118 passed, 260 deselected in 117.82 s**
focused; **378 passed in 242.79 s** full analysis, exit0, no failures/errors/skips.
Focus overlaps full. Normal-host recorder/replay: **622 passed, one opt-in skip
in 43.74 s**, exit0; the skipped actual MaleCNS zero-anchor context separately
**passed in 8.42 s**, no skips/errors/failures. Applicable two-file/all30/schema
identities match before/after; stored final acceptance audit passed.
R0 aff5948… was NOT accepted despite 372 green tests. Actual alias-fix RED had
four failures/two passes in 11.03 s, exit1; the two-clause correction and six
regressions passed scoped source closure without remaining findings. First API
RED's six failures retain log/XML, but no separate subprocess exit was retained.

These f.2 results are source-specific history, not current f.3b acceptance.
Keep genuine partial/native component checks distinct from declared internal
dispatch/math fixtures; no synthetic proof or recorded eligible point is allowed.

Historical accepted f.1 source:
`73994df1e35e1bd51407d863f42733551b994b8d2dbc8503a60bda33597e35ef`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
f.1 shares one declaration-based reducer while preserving the confirmation
wrapper; explicit integer C rules reject `<1` for qualification and `<=1` for
confirmation. No unrelated equation, schema, native core or public trust change.
Source review passed; the sole old mutation-hook finding was closed by forwarding
the new keyword in two test-only lines, preserving eight real integrity guards.

R1 full analysis: **345 passed in 184.58 s**, exit0, no errors/failures/skips.
Focused130/37.26 s and mutation-eight/14.41 s overlap the full file, not additive.
Related R0 modules on identical package source: **1,305 passed, four skipped in
953.91 s**, exit0. R1 then changed only the two test lines. Skips were complete96,
MaleCNS grid baseline, MaleCNS zero-anchor context and junction permission.
The latter three separately **passed on the normal host in 15.55 s**, exit0,
no errors/failures/skips. Complete96 remains unrun. Applicable two-path/all30/
schema before/after identities matched; stored final acceptance audit passed.
Initial114 RED failures/23.92 s, first-GREEN81 fixture failures/22.28 s and
R0 full-analysis eight hook failures/185.36 s remain failed development history.

These f.1 results remain source-specific history, not current f.3b acceptance.

Historical e.3 source review and actual 9/51/408 tiny-native repeat acceptance:
`2d07f37e85935f78b522bccb0a60d7f2b9f1d0e5a1475c8d306f12b995766da8`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
R1 focused: **78 passed, 89 deselected in 189.24 s**. Subsequent R2/R3 edits
changed only matrix test oracles. R2 True51 failed in 126.07 s on its test-only
manifest/event_sequence mapping; that failed run is preserved. After correction,
actual R3 full-cohort True51: **1 passed in
155.54 s**, no failures/errors/skips: 51 diagnostics, 96 logical cells, 130
production factories, 16 native black anchors, nine durable checkpoints including
baseline, all eight conditions and every pair's e.2 EOF comparison. Nine-pair
tests checked 21 factories. Actual R3 True408: **1 passed in 2,333.98 s**,
runner 2,334.437 s, no failures/errors/skips, on the four-node tiny-native fixture.
It checked 408 diagnostics (24 PRE + 384 POST), 768 logical cells, **1,033**
production factories, 128 native black anchors and 65 durable checkpoints including
baseline, with sixteen-fold PRE reuse. All 408 pairs passed the native/actual-byte
lookup oracle; nine full external e.2 EOF comparisons covered every cohort,
intervention/T combination and PRE, not 408 full-prefix scans.
Actual MaleCNS zero-anchor map context: **1 passed in 8.28 s**, no failures/skips.
Exact R3 source/test/schema bytes matched before/after. Earlier entire assay-module
opt-in-off compatibility: **166 passed, three declared opt-in skips in 1,426.94 s**,
exit0, no failures/errors. Its skips were False all-eight, True51 and True408;
the True nodes passed separately. R1 focused/R3 broader counts overlap, not additive.
True51 original-file audit passed: 2,025 events/5,274,722 bytes, nine checkpoints/
82,878 bytes, 128 branches, unsealed/no scientific outcome. The independent
True408 original-file audit passed: 16,088 events/42,057,618 bytes, 1,010 branches,
65 checkpoints/598,897 bytes; events SHA256
`78b660fd566045feb058ca49143e2487e14de4a63ac2e87e7d50ec7352790ebb`.
It is unsealed with no scientific outcome/terminal/configuration. These are
declared tiny-native recorded-consistency checks plus one actual
MaleCNS context, not response/history attestation or scientific qualification.

Historical e.2 R1 closed diagnostics/schema,
projection/arithmetic helpers and independent external-iterator pair comparison
passed source review and bounded runtime acceptance. Latest accepted e.2 source:
`4527956304d4d1630c415a190d4a475912cbe4ca028b4abb63baa859f9af13ae`;
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Focused R1: **115 passed, 519 deselected in 62.55 s**, exit0, no failures/errors/
skips; all five owned paths and 30 source members matched before/after. Native
PRE/ordinary POST10,000+70,000/SHAM/[100,300) tonic-PPL101 cases exercise recorded
consistency, not isolated response/history attestation. Affected-file R1
compatibility: **853 passed, one declared opt-in skip in 172.38 s**, exit0,
no errors/failures. The sole skipped actual MaleCNS zero-anchor context case
separately **passed in 7.89 s**, exit0, no errors/skips. All three junction cases
passed on the normal host; all frozen source/test/schema bytes matched before/
after. Focused and compatibility counts overlap; no whole ordinary/all-eight/
complete96 run was repeated on e.2 R1.
That e.2 source kept True production unavailable/False-only; its results are
historical, not current f.3b acceptance.

Historical accepted e.1 helper source:
`293c8a721f0a18ba9dcf0baf726437b8455133d67cf343bb9fb1c69ca617a060`;
schema `c56a64f91bf08b2f3c379a4720d4be3a5c2d1743c1c09394d2483f23d61af115`.
Independent source review passed. Actual recorder/replay compatibility was
**592 passed, one declared opt-in skip in 41.95 s**; that sole fullgraph
zero-anchor qualification-context case separately **passed in 7.93 s** on actual
MaleCNS, with no errors/skips. All three normal-host junction cases passed;
an earlier sandbox permission skip is separate. Source/test hashes matched
before/after. No whole ordinary/all-eight/complete96 repeat occurred on e.1.

Historical accepted d model-source identity:
`48af9d39b3ae8f0c9e965dbac6d0e987e0e23dda8fa68895f3807a6f98684ac3`.
Windows R1 ordinary acceptance was **2,333 passed, seven declared opt-in skips
in 1,909.58 s**, plus four actual MaleCNS graph cases in **26.31 s**. R2 changed
only two tests: two native bookkeeping cases passed in **210.06 s**, followed by
actual selected-eight (**1 passed, 1,532.18 s**) and legacy confirmation-eight
(**1 passed, 1,721.32 s**). Package bytes stayed unchanged; the whole ordinary
suite was not repeated on R2 tests. Both collections contained 2,340 cases.

Both matrices use declared tiny-native fixtures. Each has 40 trainings,
24 interventions, 128 black-retention anchors and 768 logical cells, with 24
physical PRE trials reused sixteen times and 384 POST originals. Selected
production contributes 64 sources plus caller baseline (65 checkpoints), remains
unsealed and has no scientific assessment until f. Legacy confirmation has
67 checkpoints and an actual unsupported report with 136 negative gates.
Neither is formal MaleCNS qualification or upstream training/response-history
attestation. Detailed actual inventories/hashes are in the
[tracked handover](../../cloud-handover.md).

The c.2b complete96 grid and reviewed detail-on fullgraph prefix sample remain
historical on source
`64041111c7cf3edfaf51128e071b79d939875937f810790c00d1425458c6e60e`.
The costly96 case was not repeated for d/e.1/e.2/e.3/f.1/f.2/f.3a/f.3b. Profiled durations require a controlled
unprofiled follow-up before runtime/capacity decisions. Continue on the original
Windows workstation with the approved measured-data Replay v1, LLM later;
formal integration stays parked until separately needed/released.
Earlier e/e.3 9/51/408 evidence stays source-specific.
The actual True producer remains private; production global
reconciliation/final lifecycle and integrated capacity remain unimplemented.
This is no current whole-project/complete96-grid/full MaleCNS assay acceptance.
No production config, formal source freeze or qualification is established.
Cloud setup below applies only to a future fresh checkout, not local continuation.

- [ ] Establish/verify the cloud toolchain and regenerate ignored runtime before
  any actual fullgraph work; see [tracked handover](../../cloud-handover.md).
- [x] Measure a separately bounded longer-retention fullgraph anchor/replay pilot.
- [ ] After integration, measure the actual detail-enabled grid path and bound
  complete qualification storage/events/verification costs before formal freeze.
- [x] Execute, independently review and publish the bounded actual MaleCNS
  detailed first-training prefix before d/e/f, as described below. This does not
  replace g or its required unprofiled controlled measurement.
- [x] Complete caller-owned selected controls/interventions and actual eight-factor
  selected/legacy confirmation production acceptance (d).
- [x] Accept private successful-append reference helper (e.1); public append unchanged.
- [x] Accept closed diagnostic/schema, projections and local pair comparison (e.2).
- [x] Measure all selected physical response repeats and actual state resolution (e).
- [x] Share declaration arithmetic and explicit integer qualification/confirmation C gates (f.1).
- [x] Implement/accept the corrected bounded pair checker and full-EOF adapter (f.2).
- [x] Accept f.3a composable standalone grid measurements and bounded one-configuration check.
- [x] Accept f.3b explicit-sequence accumulator and bounded analysis/related checks.
- [x] Complete the bounded unprofiled first-training diagnostic; report linked above.
- [x] Complete/review the bounded PARTIAL T10 diagnostic within its recorded scientific limits.
- [x] Implement/review Replay recorder/exporter/viewer source and record/export
  the bounded real fullgraph observation; independently check raw data/parser.
- [x] Complete the SAME recording's Chrome playback, sampled values, source-mode
  disclosure and desktop/mobile layout checks.
- [x] Complete corrected-video terminal-frame and bounded vertical checks.
- [ ] Finish foreground frame-pacing/export-precision/accessibility/cross-browser
  polish as needed for product completion; Replay stays experimental WIP.
  No fabricated activity or semantic/dopamine claims.
  Parked C1/unreleased C2 do not complete f.3c; resume formal integration only when separately needed/released.
- [ ] Integrate public frozen-config lifecycle and implement the real assay CLI;
  current CLI lacks `assay` (f/g).
- [ ] Resolve discarded-grid training ancestry without mistaking black-retention
  replay for proof of training history.
- [x] Complete Task 8's motor-only readout and its complete opt-in acceptance.
- [ ] Perform Task 9 source freeze/formal qualification; create a production
  frozen config only if all gates pass, before held-out confirmation.
- [ ] Complete reviewed confirmation/reproducibility for scientific claims; approved measured-data Replay v1 may precede it, LLM later.

## Global Constraints

- The primary endpoint is MBON11 response, not preference, learned behavior, or event choice. The maximal positive claim is the model-specific statement in the design spec.
- PPL101-modulated KC→MBON11 plasticity is primary; PAM11→MBON07 is exploratory and cannot rescue a failed primary assay.
- Qualification and confirmation use disjoint seeds and stimulus families. Freeze timing, response window, effect sign, exclusions, effect floor, and analysis version before confirmation.
- All modes begin at identical baseline state and use separately restored copies. Reward-free retention and tests have `learning=False`, no external DAN, and normal passive memory decay.
- Every scheduled interval advances neural time. `stimulus=None` means an explicit black `uint8` RGB frame, including the unpaired DAN pulse; calls to `FlyEngine.observe` are at most 500 ms.
- `no_external_dan` omits only the external pulse; endogenous DAN firing and resulting plasticity are measured, never assumed zero. `reciprocal_pairing` is acquisition from baseline with the opposite paired identity, not reversal learning.
- Inspect `src/fly_connectome_sim/neural/visual.py` before labeling input drive: RGB is a modeled retinal/R8 drive, not calibrated receptor activation. Preserve source/build/graph/provenance locks and MIT attribution.
- Raw data, prepared arrays, checkpoints, pilot/qualification/confirmatory runs and benchmark files stay in ignored runtime locations. Never add them to Git.
- `model_fingerprint()` hashes every packaged `.py`/`.cpp` file. Formal qualification, its checkpoints, the frozen config and confirmation therefore happen only after all source-bearing tasks in this plan are committed. Any later package-source fix invalidates those artifacts and restarts the source-freeze gate.
- Use test-first RED/GREEN per task. After each GREEN, run `.venv/Scripts/python.exe -m pytest`; report any failures. Each commit uses the repository's English `<type> / <title> : Description` convention and explicit paths. Never push a protected branch.
- User-approved2026-11-02 exception: measured-data Replay v1 precedes the full formal assay as a separate product slice; LLM remains later. Scientific gates are not waived.

## File ownership map

| File | Responsibility |
|---|---|
| `src/fly_connectome_sim/experiment/stimuli.py`, `tests/experiment/test_protocol.py` | New factorized assay stimuli while retaining the existing `SyntheticStimuli`/`synthetic-ab/v1` renderer byte-for-byte. |
| `src/fly_connectome_sim/experiment/protocol.py`, `tests/experiment/test_protocol.py` | Versioned condition names, pairing identity, order, side and explicit simulated schedule including retention branches. |
| `src/fly_connectome_sim/experiment/executor.py`, `tests/experiment/test_executor.py` (new) | Execute every step and neutral gap against `FlyEngine`, checkpoint forks and window aggregation. |
| `src/fly_connectome_sim/engine.py`, `src/fly_connectome_sim/neural/visual.py`, `tests/test_engine_contract.py` | Exact mapped RGB drive, MBON11-input KC activity and opt-in per-bin trace/memory diagnostics; keep default telemetry compact. |
| `src/fly_connectome_sim/neural/brain.py`, `src/fly_connectome_sim/neural/checkpoint.py`, `tests/test_checkpoint.py` | Atomic candidate-edge memory snapshot/replace and shared complete checkpoint-payload hashing, with validation before mutation. |
| `src/fly_connectome_sim/experiment/qualification.py`, `tests/experiment/test_qualification.py` (new) | Bounded exploratory grid, path/washout gate, runtime benchmark and frozen configuration output. |
| `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `src/fly_connectome_sim/cli.py`, `tests/experiment/test_recorder.py`, `tests/test_cli.py` (new) | Append-only pilot and assay artifacts, strict verifier and CLI. |
| `src/fly_connectome_sim/experiment/analysis.py`, `tests/experiment/test_analysis.py` (new) | Pure frozen-config builder, MBON11 evidence reducer and classification; no exploratory parameter selection. |
| `src/fly_connectome_sim/experiment/replay.py`, `tests/experiment/test_replay.py` (new) | Bounded black-retention recipe validation/execution, validated-prefix support and verifier-produced replay attestation. |
| `src/fly_connectome_sim/experiment/assay.py`, `tests/experiment/test_assay.py` (new) | Held-out confirmation orchestration, selected causal interventions and compact replay-anchor production. |
| `configs/assay.synthetic.json` (new only after source freeze), `tests/test_full_graph_engine.py` | Frozen held-out protocol and opt-in full-graph confirmation. |
| `src/fly_connectome_sim/experiment/adapter.py`, `tests/experiment/test_adapter.py` | Keep v1 readable; new lateral-motor-only adapter with `evidence_strength`. |

Do not create a second simulation core. New modules above each own one orchestration or analysis responsibility. `src/fly_connectome_sim/neural/circuit.py`, `rule.py`, and `kernel.cpp` remain unchanged unless a failing gate identifies a specific defect and the design spec is revised before confirmation.

## Review Focus

1. A black neutral gap may still retain modeled lamina bias or retinal adaptation; the executor test must assert the exact black input and elapsed simulation, and pathway qualification must measure washout empirically.
2. A paired identity can be confounded with image side/order; protocol tests must vary these independently and confirm balanced schedules.
3. A broad KC average can hide identical MBON11-input patterns; the pathway test must compare the actual `circuit["pre"]` subset for MBON11 edges.
4. A global MBON response gain can move the difference-in-differences; analysis tests must reject it using a third unpaired stimulus C and a prespecified multiplicative-gain residual.
5. A partial memory transplant can fabricate causality; checkpoint tests must reject bad index/shape/nonfinite/out-of-bound states without mutating any of `memory_u`, `memory_w`, or `weight`.
6. Checkpoint forks make global simulated time nonmonotone; artifacts use a global event sequence plus branch-local simulated clocks and explicit parent-checkpoint hashes.

## Gate 0: integrity before qualification

- [ ] Run `.venv/Scripts/python.exe -m fly_connectome_sim.neural.prepare` to regenerate the ignored runtime manifest, then `.venv/Scripts/python.exe -m fly_connectome_sim.data verify-prepared` and `.venv/Scripts/python.exe -m pytest tests/test_checkpoint.py tests/test_native_build.py tests/test_full_graph_engine.py -q`. For the last file's actual graph run, set `$env:FLY_CONNECTOME_SIM_FULL_TEST='1'` and run it separately. Stop at a failed integrity gate; record the cause rather than weakening a lock.

### Task 1: Independent stimulus and protocol factors

**Files:** Modify `src/fly_connectome_sim/experiment/stimuli.py`, `src/fly_connectome_sim/experiment/protocol.py`, `tests/experiment/test_protocol.py`.

**Interfaces:** Keep `SyntheticStimuli` and its `synthetic-ab/v1` bytes unchanged. Add `AssayStimuli(seed, family, width=32, height=32, version="associative-stimuli/v1").frame(identity, *, side="center", color_assignment="fixed") -> np.ndarray`; `family` is explicitly `qualification` or `confirmation`. Add `schedule_from_json()` for the actual legacy `ab-protocol/v2` structure and the new emitted `associative-protocol/v1`. `ProtocolSchedule.create(*, condition, seed, paired_identity, presentation_order, training_side="center", test_side="center", ...)` emits only the new version. Conditions are `training`, `reciprocal_pairing`, `frozen_plasticity`, `no_external_dan`, and `temporally_unpaired`; reject new use of `reversal`/`no_dan` with a migration message. A, B and unpaired C have distinct spatial patterns at the same location and identical per-channel histograms.

- [ ] **RED:** Add fixed historical JSON and frame-hash fixtures for `ab-protocol/v2` and `synthetic-ab/v1`. Add new tests that vary identity, order, side and pairing independently; verify equal per-channel histograms, deterministic family-separated hashes, distinct A/B/C pixels, balanced A/B and B/A orders, explicit PPL101 pairing-trial membership, and renamed conditions. A reciprocal run is a matched schedule with the opposite explicit `paired_identity`, not continuing trained state.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_protocol.py -q`; expected failure is the missing factorized API, not a fixture/import error.
- [ ] **GREEN:** Implement the interfaces above. Use a deterministic permutation of a fixed RGB pixel multiset; any side placement must not crop pixels or change channel totals. New assay code always names a family. Keep each interval's stimulus, stimulation, `learning`, timestamp and duration explicit; offset timing is split into executable intervals in Task 5.
- [ ] Run the focused command, then `.venv/Scripts/python.exe -m pytest`; require all tests green. Review that no MBON/motor outcome or seed choice influenced the new pattern banks.
- [ ] Commit only these three files: `feat / assay-factors : Separate stimulus identity and schedule factors`.

### Task 2: Neutral gap executor and retention forks

**Files:** Create `src/fly_connectome_sim/experiment/executor.py`, `tests/experiment/test_executor.py`; adjust `protocol.py`/its tests only for explicit gap/branch metadata.

**Interfaces:** `execute_schedule(engine: FlyEngine, schedule: ProtocolSchedule, stimuli: AssayStimuli, *, branch_id: str, on_event: Callable[[dict], None]) -> None`; `advance_neutral(engine, duration_ms, shape, *, stimulation=None, learning=False, branch_id, on_event) -> None`; `retention_test(engine, training_end_checkpoint: Path, delay_ms: float, ...) -> tuple[dict, ...]`. All gap calls use `np.zeros((height,width,3), dtype=np.uint8)` and chunk `min(500.0, remaining_ms)` on the 0.1 ms grid. Restore the same training-end checkpoint separately for `T` and `T+60000` branches; each A/B/C test presentation starts from a separately restored retention-end checkpoint to prevent carryover. `T=0` is the later end of the final training presentation and final external DAN pulse, including an unpaired B presentation if it is last.

- [ ] **RED:** In `test_executor.py`, use a recording fake engine to assert 1,201 ms gap calls of 500/500/201 ms, all-zero RGB and matching branch-local simulated timestamps; assert the unpaired DAN pulse also gets black RGB. Add checkpoint-fork tests proving both retention branches start at identical training-end bytes, each A/B/C test forks its retention-end checkpoint, parent checkpoint hashes are recorded, and the `T+60` branch advances exactly 60,000 ms more.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_executor.py -q`; expected failure: missing executor/retention APIs.
- [ ] **GREEN:** Implement the interfaces and events (`fork`, `step`, `neutral_gap_chunk`, `retention_start`, `retention_end`) with branch ID, parent checkpoint hash, input hash, exact branch-local time, stimulation and `learning`. Reject negative/nonfinite/off-grid durations before mutating the engine. Never skip the interval between scheduled timestamps or rewrite scientific clocks to make different branches appear monotone.
- [ ] Run focused then full pytest. Review exact `T` reference, no external DAN and `learning=False` in both retention branches and tests.
- [ ] Commit executor, tests and any protocol adjustment: `feat / neutral-executor : Advance every scheduled gap and fork retention tests`.

### Task 3: Pathway observability at the actual MBON11 inputs

**Files:** Modify `src/fly_connectome_sim/neural/visual.py`, `src/fly_connectome_sim/engine.py`, `tests/test_engine_contract.py`; add focused opt-in graph assertions to `tests/test_full_graph_engine.py`.

**Interfaces:** Add a pure `VisualMemoryBrain.rgb_drive(frame) -> dict[str, np.ndarray]` that returns the *modeled* sampled R1–R6 luminance and R8 channel input before neural state advances, with no mutation. Add `FlyEngine.observe(..., pathway_detail=False, qualification_detail=False)`. `pathway_detail` returns drive summaries and per-neuron spike counts keyed by stable source ID for the ordered unique KCs on candidate edges whose postsynaptic target is MBON11. `qualification_detail` augments every existing ≤10 ms bin with ordered `rate_kc` values for those candidate edges, ordered `rate_dan` values for `circuit["dan"]`, candidate `memory_u`/`memory_w` summaries and hashes, efficacy summary, and lower/upper-bound hit counts. Label `rate_kc`/`rate_dan` as model trace state rather than raw spikes. Default telemetry remains byte-for-byte compact.

- [ ] **RED:** Assert `rgb_drive` does not change `sim_ms`, `luminance` or `r8_light`; verify RGB geometry changes mapped drive; verify a tiny circuit's MBON11-input KC set excludes KCs connected only to MBON07 and all edge/DAN/source-ID orderings are deterministic. Force a transient bound hit that disappears by the endpoint and prove an opt-in bin still records it. Assert default telemetry has no candidate vectors or trace state.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/test_engine_contract.py -q`; expected failure is missing observability API.
- [ ] **GREEN:** Reuse the exact sampling expressions in `visual.py`'s `rgb_step` and `sensory.retinal_samples`; factor them into a pure helper without changing numerical equations. Snapshot diagnostics immediately after each internal neural bin, before the next advance. Aggregate KC counts from existing totals and label drive as `modeled_visual_drive`, never receptor occupancy/activity. Define saturation as any bin at a rule bound and retain the maximum bound-hit fraction as well as endpoint values.
- [ ] Run focused and full pytest, then opt-in `FLY_CONNECTOME_SIM_FULL_TEST=1` test. Review identical default spike/state hashes before and after the refactor; any difference is a gate failure.
- [ ] Commit these files: `feat / pathway-observability : Expose modeled visual drive and MBON11-input KC activity`.

### Task 4: Atomic MBON11 candidate memory intervention

**Files:** Modify `src/fly_connectome_sim/neural/brain.py`, `tests/test_checkpoint.py`; `executor.py` only to orchestrate branches.

**Interfaces:** `MemoryBrain.candidate_memory(target_indices: np.ndarray) -> CandidateMemory` derives the ordered KC→target candidate edges and returns copies of edge indices, `memory_u`, `memory_w`, and `weight`. `replace_candidate_memory(snapshot)` validates exact edge identity/order, shape, dtype, finite rule bounds and `weight == baseline_plastic * (1 + memory_w)` within float32 rounding, then assigns all three arrays atomically. No other neural state, trace, clock or weight changes.

All causal interventions occur at the common training-end clock. The donor is the trained branch; the recipient/baseline branch saw identical images, intervals and external-current-free trial structure with `learning=False`. Apply necessity, sufficiency and sham at that clock, then advance every branch through the identical full retention interval with `learning=False`, no external DAN and `weights_frozen=False`, so normal passive `u/w` decay continues.

- [ ] **RED:** On the four-neuron fixture, assert necessity (matched baseline triplet into trained), sufficiency (trained triplet into matched recipient) and sham preserve every noncandidate state hash, trace, cursor and clock at intervention time. Parameterize unequal donor/recipient clocks, bad edge order, duplicate/missing edge, wrong dtype/shape, NaN, out-of-bounds `u/w`, and inconsistent weight; rejection leaves all three live components byte-identical. Prove every accepted branch receives the same passive-decay duration.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/test_checkpoint.py -q`; expected failure: missing atomic API.
- [ ] **GREEN:** Define a frozen snapshot dataclass, copy on read, prevalidate the complete replacement against immutable `baseline_plastic`, then assign the three candidate slices. Checkpoint before and after each intervention. Never use `no_external_dan` as the supposedly memory-free recipient.
- [ ] Run focused/full pytest and the opt-in native checkpoint test. Confirm MBON07 candidate state is unchanged and separately report it.
- [ ] Commit: `feat / candidate-intervention : Replace MBON11 memory state atomically`.

### Task 5: Implement the bounded qualification protocol

**Files:** Create `src/fly_connectome_sim/experiment/qualification.py`, `tests/experiment/test_qualification.py`; use Tasks 1–4 without creating a durable full-graph result yet.

**Interfaces:** `qualify(engine_factory, recorder, *, seeds, family) -> QualificationResult` and `benchmark(...) -> dict`. Formal qualification seeds are `(11, 23)` and confirmation seeds `(101, 113)`; never cross them. The fixed grid has CS duration 100 or 300 ms, PPL101 pulse duration exactly 100 ms, DAN onset relative to CS onset −100, 0 or +100 ms, and post-pair gap 500 or 10,000 ms (12 configurations). Each trial reserves the same epoch from −100 ms through `CS_end + 200 ms`; split at every CS/DAN boundary and use black frames outside CS. The pulse belongs to the paired trial even when its −100 ms offset is visually black. The temporally unpaired pulse is fixed at least 10,000 ms from the nearest CS boundary and is not changed by the post-pair-gap grid. All conditions match total elapsed time and visual exposure. Current 20 mV current remains fixed.

Predeclared response-window candidates relative to CS onset are `[0,100)`, `[0,300)`, and `[100,300)` ms. For each window, `one_spike_rate_hz = 1 / (len(MBON11) * window_seconds)`. The C response floor is exactly that one-spike rate. The dimensionless candidate-state metric is mean absolute candidate `memory_w` difference from the time/exposure-matched `learning=False` branch at training end; its numerical resolution is measured from identical checkpoint replays in the same units. The washout metric is the absolute MBON11 response difference between externally stimulated frozen-plasticity and matched unstimulated frozen-plasticity branches. Its independent threshold is `max(5 * replay_numeric_resolution_hz, one_spike_rate_hz)` and never includes the acute value or later control deltas.

- [ ] **RED:** Test all interval splits, equal trial durations, fixed unpaired separation, grid cardinality/order, window definitions, disjoint seeds/families, deterministic edge/DAN ordering, transient any-bin saturation, finite measurements and benchmark fields. Fixtures where every candidate saturates, lacks a state shift above `5 * state_replay_resolution`, lacks MBON11/KC observability or fails independent washout must return `unsupported` with no selected configuration.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_qualification.py -q`; expected failure: missing qualification API.
- [ ] **GREEN:** Require nonzero modeled drive for A/B/C, distinguishable MBON11-input KC vectors for A/B, checkpoint replay determinism, C above its response floor and MBON11 dynamic range. Reject nonfinite points or any-bin candidate bound-hit fraction >1%. Test T candidates 10, 20, 30 and 60 s; choose the first passing independent washout threshold. Among remaining points, choose the largest absolute exploratory MBON11 difference-in-differences at T, tie-break by fixed grid then fixed response-window order, and freeze its observed sign. Record all points, including candidate-state metric/resolution, MBON11 values, MBON07 state and rejection reasons. The grid cannot expand after results.
- [ ] Implement benchmark output for simulated seconds, wall seconds, event count, checkpoint bytes and peak event-buffer bytes without altering scientific parameters. Run unit/tiny-graph pilots only; they are disposable and cannot supply the frozen config.
- [ ] Run focused/full pytest. Commit code/tests: `feat / timing-qualification : Declare the bounded exploratory assay`.

### Task 6: Recorder pilot, schema and CLI after fields are known

**Files:** Create `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `src/fly_connectome_sim/cli.py`, `tests/experiment/test_recorder.py`, `tests/test_cli.py`; update `pyproject.toml` only if the existing script entry needs correction.

**Interfaces:** CLI `fly-connectome-sim qualify --output-dir PATH`, `fly-connectome-sim verify-run PATH`; Task 7 adds the final `assay` command after analysis exists. Implement `RunRecorder.append(event)` and `verify_run(path) -> VerifiedRun`. `run.json` contains immutable provenance/config and hashes. Every JSONL event has a globally increasing `sequence`, `branch_id`, branch-local `sim_ms`, and for forks a parent branch/checkpoint hash. Require simulated-time monotonicity only within each branch. Checkpoints are `brain-before.npz`, `brain-after.npz` and named branch files. Hash canonical scientific events without `compute_seconds` or `kernel_seconds`; retain those as operational telemetry. Reject duplicate run directories instead of overwriting.

- [ ] **RED:** Test ordered append/flush/reopen, globally increasing sequence, branch-local time validation, explicit forks to earlier simulated clocks, truncated/tampered line or checkpoint rejection, mismatched config/engine identity, exact neutral chunks, separate checkpoints for T/T+60 and interventions, strict JSON, and deterministic scientific hashes despite different compute times. CLI tests show `verify-run` fails closed and output directories cannot be overwritten.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_recorder.py tests/test_cli.py -q`; expected failure: missing recorder/CLI.
- [ ] **GREEN:** Implement metadata and schema for measured fields established in Tasks 1–5: complete engine identity; factors, seed and RGB hashes; per-bin counts/rates, modeled pathway drive and trace diagnostics; stimulation, neutral chunks, memory/saturation, T reference, forks and interventions. Write metadata/checkpoints via temporary file plus atomic replace and verify hashes before analysis. Choose flush chunks from a disposable benchmark and preserve immutable event bytes after close.
- [ ] Run focused/full pytest; execute one short ignored `runs/pilot-*` tiny-graph artifact and verify it. It is a schema pilot only and is never referenced by qualification/configuration.
- [ ] Commit code/schema/tests only: `feat / assay-recorder : Verify append-only experiment artifacts`.

### Task 7: Implement the frozen analysis contract and assay CLI

**Files:** Create `src/fly_connectome_sim/experiment/analysis.py`, `src/fly_connectome_sim/experiment/assay.py`, `tests/experiment/test_analysis.py`, `tests/experiment/test_assay.py`; modify `src/fly_connectome_sim/experiment/qualification.py`, `src/fly_connectome_sim/experiment/executor.py`, `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `src/fly_connectome_sim/cli.py` and their focused tests. Do not create the populated frozen config until Task 9 formal qualification completes.

**Interfaces:** `build_frozen_config(qualification: VerifiedRun) -> FrozenAssayConfig` and `analyze_assay(run: VerifiedRun, frozen: FrozenAssayConfig) -> AssayReport`. The builder accepts qualification-family artifacts only and carries their exact hashes, model/engine identity, protocol/stimulus versions, selected response window, mean-rate aggregation, expected sign, effect floor, timing, T, disjoint confirmation seeds/family, exclusions and analysis version. `run_assay(...)` supplies the previously missing held-out orchestration; `fly-connectome-sim assay --config PATH --output-dir PATH` invokes it without optimizing the config.

The endpoint for each paired identity is `delta=(post_plus-post_minus)-(pre_plus-pre_minus)`. `pre` and `post` are reward-free MBON11 rates recomputed from raw bins in the same fixed window. Calculate independently at T and T+60 s from distinct copies of the same training-end checkpoint. Require every seed/identity/order/time cell's signed trained delta to exceed the frozen floor and exceed corresponding frozen, `no_external_dan` and temporally unpaired deltas by that floor. Define `g=post_C/pre_C`; C must exceed the frozen one-spike response floor. Reject global gain unless signed `[(post_plus-g*pre_plus)-(post_minus-g*pre_minus)]` also exceeds the floor. Reciprocal pairing must reverse the raw A−B effect with paired identity while paired-minus-unpaired keeps the declared sign. Necessity must match the untouched reference within the floor and remove more than one floor from paired; sufficiency must exceed both the floor and its matched untouched recipient by one floor; sham matches paired within replay resolution. Donor/recipient training-end clocks and passive-decay durations must match. Missing branches, identity, C response, hashes or timing are `inconclusive` and take precedence over scientific-gate failures.

- [x] **RED 7A:** In `test_analysis.py`, use hand-calculated small event streams to test delta sign, both retention times, each control, reciprocal identity, global multiplication of pre A/B/C, necessity/sufficiency/sham, endogenous DAN in `no_external_dan`, missing/invalid bins and mismatched provenance. The global multiplier fixture must classify `unsupported` despite a nonzero raw delta.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py -q`; expected failure: missing pure analysis API.
- [x] **GREEN 7A:** Implement strict frozen-config serialization, exact arithmetic and classifications `supported`, `unsupported`, `inconclusive`; emit all values/reasons. Derive the effect floor from qualification as `max(5 * replay_numeric_resolution_hz, 2 * max_abs_qual_control_delta_hz, 0.05 * qualified_mbon11_dynamic_range_hz)` and record each term. This floor is not reused for washout. Consume the response window/sign already selected from Task 5's fixed candidates; do not search again. Do not use held-out values in configuration or thresholds.
- [ ] **RED/GREEN 7B:** Record and gate selected qualification controls/interventions at T and T+60, then implement held-out production for every frozen factor. Distinguish association T0 from the later schedule-complete checkpoint and preserve exact passive durations. Require matched-reference contrasts for necessity/sufficiency and freeze expected confirmation RGB/black hashes.
- [x] **7B1:** Require one complete, metadata-bound terminal `assay_result` for confirmation artifacts. Validate canonical report hashes and exact evidence-prefix bindings through shared recorder/verifier checks and mirror the payload contract in the packaged schema. The independent analyzer remains responsible for scientific recomputation.
- [x] Resolve the anchor occurrence/content contract: occurrence-envelope SHA binds the exact durable route and recorded recipe/prefix; a separate complete-state SHA permits identical paired/sham content without merging ancestry. Fix schema compatibility and bounded temporary-snapshot policy in the replay refinement.
- [x] **7B2a:** Implement shared live/archive checkpoint payload and canonical complete-state hashing with bounded array buffers, strict metadata and existing model/native-state validation. Preserve legacy provenance byte hashes and verify exact live/archive/restore agreement on the real full graph.
- [x] **7B2b:** Implement strict occurrence-envelope/black-retention recipe primitives and isolated real native execution. Bind exact source occurrence, completed scientific prefix, every explicit call and thaw; preserve analyzer source-identity semantics. These primitives do not yet attest persisted artifacts.
- [x] **7B2:** Use complete-state hashing to implement the occurrence envelope, strict `black-retention/v1` recipe, recorder/schema anchor indexing and immutable verifier-produced attestation. Demonstrate a real durable source to anchor to two sibling test forks; preserve all analyzer gates. Keep one bounded temporary retention snapshot for sibling restores outside sealed inventory.
- [x] **7B3a:** Share validated-prefix and sealed report construction, including inventory/provenance gates, computed verifier mode and nonmaterialized-parent labels. Prove exact canonical terminal/report equality using an honest real partial native artifact; missing assay cells remain inconclusive. Terminal framing does not consume the scientific event budget; incomplete reports preserve actual labels and provenance.
- [x] **7B3b:** Implement validated live candidate/noncandidate state digests with exact ordered selection maps, separate content domains and streamed complement exclusions. Follow the candidate-state contract and bounded steps below; existing candidate replacement, numerical behavior and complete checkpoint preimages remain unchanged.
- [ ] Extend the producer/artifact with strict response/intervention events and shared validated-prefix replay before terminal reduction. Formally verify after sealing and independently recompute the same canonical report, including nonmaterialized-parent and verification-mode labels. Retain durable before/after and all selected ordinary training-end/intervention checkpoints.
- [ ] Decide discarded-grid training ancestry using measured durable-storage versus separately reviewed exact training-replay cost; black-retention replay alone does not solve it. Do not introduce a generic replay interpreter or weaken freeze-input ancestry.
- [ ] Measure or conservatively project full-graph checkpoint/event/wall-time capacity before source freeze. Keep full response/CS/DAN bins but compact passive black-gap telemetry.
- [ ] Run focused/full pytest and a disposable CLI pilot. Commit source/tests only: `feat / frozen-assay : Implement MBON11 causal analysis`.

#### Task7B3b: bounded state-digest implementation

**Files:** `src/fly_connectome_sim/neural/brain.py` owns actual live validation;
`src/fly_connectome_sim/neural/checkpoint.py` owns the narrow private codec;
`tests/test_checkpoint.py` owns wire/native/invalid-state/streaming regressions;
`tests/test_full_graph_engine.py` owns one opt-in read-only fullgraph hash test.
No engine, analysis, recorder, qualification, protocol or native-core changes.

**Interfaces:** `MemoryBrain.candidate_state_digests(target_indices, *,
chunk_bytes=HASH_CHUNK_BYTES) -> dict[str, str]` returns exactly
`candidate_memory_sha256` and `noncandidate_state_sha256`.
`checkpoint._candidate_state_digests(metadata, arrays, *, target_indices,
candidate_positions, edge_indices, chunk_bytes=HASH_CHUNK_BYTES)` is a private
encoding seam, not artifact/model authentication. The normative domains, G/A/E/X
records, maps, validation and acceptance cases are in the candidate-state contract.

**Review focus:** Unsorted global edges must not reorder memory; fully excluded
arrays must retain schema/map; invalid excluded values must still reject; actual
readonly arrays must remain unchanged; terminal/route identity must not enter
content or silently replace later donor provenance checks. Each is covered below.

- [x] **RED live boundary:** Reuse the actual native `intervention_brains` fixture,
  lock model provenance before hashing and capture tiny state bytes. Initial test:

```python
def test_candidate_state_digests_are_read_only(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    before = state_bytes(brain)
    result = brain.candidate_state_digests(np.array([2, 3], dtype=np.int32))
    assert set(result) == {"candidate_memory_sha256", "noncandidate_state_sha256"}
    assert all(len(value) == 64 and set(value) <= set("0123456789abcdef")
               for value in result.values())
    assert state_bytes(brain) == before
```

- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_checkpoint.py -k
  candidate_state_digests -q --basetemp=.tools/pytest-temp-7b3b-worker --tb=short`.
  Expected RED is absent live API after real brain construction/lock, not broken
  fixtures or imports. Record command/output before product edits.
- [x] Add independent literal-byte wire tests for both exact domains and map
  order, negative zero and an empty component complement. Assemble expected
  preimages from literal canonical metadata/header bytes, `struct.pack('<Q', n)`
  and literal numeric bytes, never production canonical/map/header helpers.
  Add native necessity/sufficiency/sham equality tests with distinct donor neural
  state, both targets selecting circuit edges `[1,0]`, and checkpoint-restore parity.
- [x] Implement the private codec using existing JSON/chunk/framing primitives,
  selected gathers bounded by `chunk_bytes` and basic complement slices. Validate
  entire array values before exclusion; preserve complete-state/raw digest wire
  bytes. Add the live wrapper validating the actual locked complete payload,
  registration/native state, exact candidate map and actual rule-bound/weight
  consistency before calling the codec; recheck the model lock before returning.
  The call computes both values from one quiescent state without snapshot/NPZ.
- [x] Add parameterized sensitivity/rejection tests for every contract acceptance
  category: all untouched registered fields and mutable scalars, candidate `rate_kc`,
  selected-only replacements, readonly inputs, wrong/empty/duplicate/out-of-range
  maps, invalid excluded u/w/weight, registration/schema/native/clock/model-lock
  divergence, endian/index-width/layout equivalence, dtype/rank/shape/map/signed-zero
  discrimination, empty state arrays and fully excluded components. Invalid calls
  leave actual state unchanged. Targets with no edges remain bound if group-wide
  selection is nonempty; an entirely edge-free candidate rejects.
- [x] Add sparse unsorted large synthetic-weight streaming guards and chunk-size
  invariance at8 and nonmultiple sizes. Observe encoder buffers/hash update pieces,
  not native validator/selection allocations. Reject full complement masks/copies,
  full-array byte/astype/byteswap/contiguous conversions and concatenation in codec.
- [x] Add opt-in `test_full_graph_candidate_digests_are_read_only`: create a real
  prepared-graph engine, obtain identity to lock, record complete-state SHA and
  scalar/array references, call live API twice on actual MBON11 targets and require
  equal digests plus unchanged complete-state SHA/scalars/references. No extra
  graph-scale snapshot/archive, observe, qualification or capacity measurement.
- [x] Run focused checkpoint/native/engine tests, self-review and report exact
  RED/GREEN/API/wire/limits. Freeze and notify coordinator before one ordinary
  complete suite; coordinator owns fresh independent review and final opt-in full
  suite after any fixes. Do not claim fullgraph capacity or an executed assay.
- [x] Coordinator commits reviewed code/tests and accurate contract/plan/status
  updates: `feat / state-digests : Bind candidate and noncandidate state evidence`;
  push explicitly `git push -u origin feat/connectome-experiment-core`.

Completion evidence: genuine native RED/GREEN implementation and review-fix
regressions; independent state/wire review plus clean scoped fix review.
Final root opt-in complete suite:1190 passed in322.64s, including both real
fullgraph integrations. Candidate hashes prove content, not donor provenance,
clock compatibility, capacity, formal qualification or a positive assay result.

#### Task7B3c: bounded paired-cohort producer

**Files:** Create `src/fly_connectome_sim/experiment/assay.py` and
`tests/experiment/test_assay.py`. Extract the existing declared native frozen
test contract into `tests/experiment/replay_helpers.py`, updating only its
test caller in `test_analysis.py`. Root owns plan and README status.

**Interface:** `run_paired_cohort(engine_factory, frozen, *, output_dir,
seed=101, paired_identity="A", presentation_order="AB") -> AssayReport` executes
one frozen paired cohort. It does not produce the full confirmatory assay or
choose scientific parameters. Other declared cohorts/controls/interventions
remain missing, with an inconclusive report.

**Review focus:** Actual current ordered groups must match frozen declarations
even when engine identity is cached. Candidate content is not occurrence or
clock proof. Independent pre/post trials must not carry preceding trial state.
Record response at its window stop before padding. Source/recipe mutation before
terminal must fail closed; excluded timing cannot contaminate scientific hashes.

- [x] **RED:** The native graph fixture reaches the absent producer module.
  Subsequent clock and canonical-report regressions fully construct real native
  engines and a schema-valid declared frozen correctness contract before their
  failing assertions. The fixture is not qualification evidence and does not
  call `build_frozen_config`.
- [x] **GREEN acquisition:** Reuse `_training_timeline(..., controls=True)`,
  `_trial_segments` and `_split_intervals`. Execute and record every actual
  <=500 ms call, its clocks/arguments and raw response/CS/DAN bins. Supply explicit
  black RGB during neutral time, learning-disabled reward-free retention/tests
  and passive decay. Derive strict training evidence and live candidate/noncandidate
  digests from actual state. Retain durable before/baseline/training-end/after
  occurrences and exact parent references. Check actual identity/groups/maps,
  clock, population and frozen input hashes rather than trusting cached labels.
- [x] **GREEN responses:** Acquire independent baseline A/B/C pre trials and
  both retention groups, producing twelve strict descriptors. Pre means restored
  baseline-state measurement; acquiring it after durable training-end hash exists
  cannot select parameters or carry training state into that restored copy.
  Truthful pre measurements may supply both retention rows. For each retention,
  source-to-anchor black replay stops at CS onset minus1000 ticks. Validate one
  scratch NPZ outside inventory by actual state SHA/tick, restore all three
  siblings independently, execute each prelude and reward-free trial, then remove
  scratch. Record exactly two used anchors and emit responses at window stop.
- [x] **GREEN lifecycle:** Use actual `verify_replay_prefix`,
  `assess_assay_prefix` and `build_assay_result`; append exactly one terminal,
  seal, call `verify_replay_run` and independently `analyze_assay`. Require exact
  canonical report equality. Ordinary verification remains integrity-only.
- [x] **Acceptance:** Independently check actual calls/source NPZ/raw counts;
  both paired rows have pre/post A/B/C without invalid training/response,
  ancestry/copy/clock/provenance/inventory/terminal reasons. Missing declared
  cells remain visible and result inconclusive. Source and recipe-operation
  tampering before terminal returns no attested result or seal. A timing-only
  native rerun preserves recipe/anchor/report/scientific identities. Reject
  current-group mismatch despite cached identity; cover declared timing/windows.
  Reject unreachable anchors before scratch/recorder creation while preserving
  the reachable anchor-equals-source boundary.
- [x] Run focused producer/analysis/replay coverage, fresh independent integrity
  review and the full suite with `FLY_CONNECTOME_SIM_FULL_TEST=1`.

Completion evidence: native missing-module RED, clock/canonical-comparison
RED/GREEN and timing-preflight artifact RED/GREEN. Independent integrity review
and scoped fix review are clean after one Important timing finding was fixed.
Final amended producer coverage:18 passed; final complete opt-in suite:1208
passed in444.47s, including both actual fullgraph integrations. Commit only
reviewed source/tests/status files and push the explicit feature branch.

This is a tiny correctness lifecycle pilot, not formal qualification,
confirmation, fullgraph capacity approval or a positive scientific finding.
Selected qualification evidence, control/intervention routes, all-factor
production and the assay CLI remain subsequent tasks.

#### Task7B3d: native matched reference and candidate replacement routes

**Files:** Extend `experiment/assay.py` and its native tests; update status docs.

**Interface:** `run_intervention_cohort(...) -> AssayReport` uses the paired
producer's arguments and shared execution path. Preserve `run_paired_cohort`
behavior. Execute paired and time-/exposure-matched reference acquisition from
independent baseline restores, then necessity, sufficiency and sham replacements
at their common training-end clock. Bind each route to its recipient training and
actual post-intervention source occurrence, including baseline responses.

- [x] **RED:** Initialize the genuine tiny native engine and declared test config
  before asserting the missing API. Then prove two training events, three real
  interventions, ten anchors, sixty responses and eight durable checkpoints.
- [x] **GREEN:** Reuse training/trial/retention schedules and preflight both source
  clocks before recording. Authenticate exact durable donor/recipient occurrences
  and their live training-end digests; compare canonical identities, current
  groups, clocks and actual ordered candidate maps. Capture a quiescent authentic
  donor snapshot. Bracket only replacement with recipient component digests;
  preserve noncandidate state and sham content. Identical necessity/sufficiency
  content is valid and must not be fabricated into a shift.
- [x] Verify native baseline/retained trial isolation, actual replacement triplets,
  telemetry/counts, source/occurrence tampering and compatibility rejection. Keep
  timing-only scientific equivalence and the existing paired API regressions.
- [x] Native-verify prefix and sealed artifact, with one terminal and independent
  canonical report equality. Ten complete route/time rows remain inconclusive
  because other declared factors and the three controls are still missing.
- [x] Freeze/self-review, independent integrity review, covering fixes and final
  complete opt-in suite before the explicit feature-branch commit/push.

Completion evidence (2026-10-04): genuine initialized native missing-API RED,
source/transfer and signed-zero snapshot-spoof RED/GREEN; focused native suite
45 passed in320.80s, including all eighteen paired regressions. Independent
integrity/specification/quality review found no open Critical, Important or Minor
findings. Final complete opt-in suite:1235 passed in643.92s, including both actual
fullgraph integrations, on the unchanged reviewed source/test bytes.

This slice does not supply formal qualification, a production frozen config,
fullgraph capacity approval, all-factor controls or the assay CLI.

#### Task7B3e: complete native control routes for one cohort

**Files:** Extend `experiment/assay.py` and its native tests; update status docs.

**Interface:** `run_controlled_cohort(...) -> AssayReport` shares the existing
producer and executes all eight conditions for one seed/identity/order cohort.
Preserve paired and intervention APIs. Add frozen-plasticity, no-external-DAN
and temporally-unpaired acquisition through the existing five ordinary plans.

- [x] **RED:** Initialize native engine/config before the absent-API failure.
- [x] **GREEN:** Acquire all five ordinary sources independently from baseline;
  match time/exposure/order and preflight every retention source. Execute each
  shared plan's learning/stimulation declarations. Frozen plasticity disables
  acquisition learning while weights stay unfrozen for passive memory decay.
  No-external-DAN preserves endogenous learning/telemetry. The unpaired pulse
  receives black RGB and stays at least 10000ms from every CS boundary.
- [x] Native evidence proves five trainings, three interventions, sixteen
  anchors, ninety-six responses, eleven durable checkpoints and forty-eight
  independent post trials. All sixteen condition/time rows have pre/post A/B/C;
  other declared factors remain missing and classify the pilot as inconclusive.
- [x] Preserve existing forty-five paired/intervention regressions, terminal
  canonical equality and native prefix/sealed replay. Independently review and
  run a final complete opt-in suite before feature-branch commit/push.

Completion evidence (2026-10-04): initialized native missing-API RED;
focused native coverage:52 passed in522.89s, including all forty-five existing
paired/intervention regressions. Fresh independent integrity review has no open
findings. Final complete opt-in suite with regular sandbox permission:1242 passed
in852.34s, including both fullgraph integrations and the native-build smoke, on
unchanged reviewed source/test bytes. Earlier sandbox full runs passed1241 tests
but Windows application control blocked the freshly built smoke DLL at load
(WinError4551); compilation completed, and no product or security-policy change
was made to obtain the final host-environment verification.

This slice supplies complete conditions for one factor cohort, not all-factor
confirmation, formal qualification/configuration, capacity approval or the CLI.

#### Task7B3f: shared artifact for reciprocal controlled cohorts

**Files:** Extend `experiment/assay.py` and its native tests; update status docs.

**Interface:** `run_controlled_cohorts(engine_factory, frozen, *, output_dir,
cohorts) -> AssayReport` accepts a nonempty bounded list/tuple of unique declared
seed/identity/order triples. Existing single-cohort APIs and evidence names stay
compatible. All requested cohorts share one real baseline occurrence and one
recorder, prefix, terminal and sealed artifact. Durable training/intervention
checkpoints and pre/post/retention/anchor identifiers are unique per cohort.

- [x] **RED:** Initialize genuine tiny native engine/config before missing API.
- [x] **GREEN:** Execute all eight conditions for each requested cohort from
  independent restores of one global baseline. Preflight actual input hashes and
  retention reachability for every requested cohort before scratch/recorder.
  Preserve source/donor/recipient occurrences, clocks, passive decay, sequence
  order and native replay contracts; no combination of independently sealed runs.
- [x] Native reciprocal acceptance executes `101/A/AB` and `101/B/AB`: ten
  trainings, six interventions, thirty-two anchors, 192 responses and nineteen
  durable checkpoints. Both cells at both retention times contain all eight
  conditions and pre/post A/B/C, while other factors remain visibly missing.
  Preserve negative scientific and reciprocal gates; status remains inconclusive.
- [x] Reject empty, duplicate, malformed and undeclared cohort factors plus
  late-cohort bad inputs/unreachable sources before creating artifacts. Preserve
  all fifty-two existing regressions. Independently review, freeze tested bytes,
  then run a complete opt-in suite before explicit feature-branch commit/push.

Completion evidence (2026-10-04): initialized native missing-API RED; final-byte
preflight coverage:20 passed. Fresh independent integrity review has no open
findings. Final complete opt-in suite:1263 passed in1661.01s, including all73
producer cases, both fullgraph integrations and the native-build smoke, with
zero failures/errors/skips and unchanged reviewed source/test hashes. The genuine
reciprocal native acceptance passed in791.396s on the stronger final assertions;
its one shared sealed artifact remains scientifically inconclusive.

This slice validates two cohorts in one native artifact; it does not establish
all-factor confirmation, formal qualification/configuration, fullgraph capacity
or the assay CLI. Full factor execution remains a subsequent validation gate.

#### Task7B3g: native acceptance of the complete factor matrix

**Files:** Create `tests/experiment/test_assay_all_factors.py`; update status docs.
Production APIs and existing producer regressions remain unchanged.

- [x] Add one genuine native opt-in integration using all eight declared
  seed/identity/order triples through `run_controlled_cohorts` in one artifact.
  Reuse the existing full-test environment convention and native fixture.
- [x] Require forty trainings, twenty-four interventions, 768 responses,
  128 native-attested anchors and sixty-seven durable checkpoints. Check all
  sixteen factor/retention keys and eight conditions with pre/post A/B/C,
  cohort-qualified source occurrences, actual inputs and response/anchor ancestry.
- [x] Independently verify and reduce the sealed evidence; require canonical
  report equality and a structurally complete matrix with honest scientific
  failures. Do not weaken gates or fabricate qualification/positive results.
- [x] Freeze and independently review the test; run one final complete opt-in
  suite covering the new native case and all existing regressions before explicit
  feature-branch commit/push. Retain actual verification evidence.

Verified 2026-10-05: fresh independent integrity review passed; the complete
opt-in suite passed all 1,264 cases with no failures, errors or skips in
52,202.15 seconds. The new native case took 50,563.872 seconds and authenticated
the complete 768-response matrix, 128 anchors and 67 durable checkpoints.
The report remains scientifically `unsupported`, including negative reciprocal
gates; matrix completeness does not imply learning or qualification. Production
source and all 73 existing producer regressions retain their frozen hashes.
Investigate recorder/replay timing before scaling this acceptance to fullgraph;
repeated prefix scans are a static hypothesis, not an isolated measurement.

This validates the complete declared factor matrix on the tiny native fixture;
it does not establish formal qualification, production configuration, fullgraph
assay execution/capacity or the CLI. Those remain separate gates.

#### Task7B3h: remove nested historical scans within authentic validation

**Files:** Update `experiment/recorder.py` and `experiment/replay.py`; create
`tests/experiment/test_recorder_projection.py`; update status docs.

Original read-only measurement: a genuine 64-anchor, 7,009-event prefix required
239,425 raw event consumptions in 38.398736 seconds. Source/artifact hashes stayed
unchanged. The full producer-loop traversal count of 120,410,288 is a call-graph
inference, not isolated wall-time attribution of the fourteen-hour native case.

- [x] Add a genuine deterministic RED regression counting raw reads during one
  complete chain scan; require one outer traversal and no historical rereads.
- [x] Share strict branch operation projection and use ephemeral scanner state
  with a bounded SHA256 accumulator over the exact canonical operation array.
  Independently compare all source/header/prefix fields and preserve grammar,
  deferred global/branch errors, mutation checks and actual checkpoint occurrence.
  This provides cryptographic equality under the existing hash assumption;
  it does not compare reconstructed operation arrays byte for byte.
- [x] Preserve standalone full-prefix authentication, live recorder physical
  rereads, wire/schema hashes, current-byte revalidation and verifier-only native
  attestations. Keep ordinary unanchored/legacy acceptance and bounded history
  memory; run existing integrity guards and new differential/projection tests.
- [x] Measure the same authentic prefix after the change, freeze reviewed bytes,
  obtain fresh independent integrity review and run one complete opt-in suite
  including the unchanged all-factor native case before explicit feature push.

No persistent trust cache, public skip-validation mode, new scientific support,
formal qualification or fullgraph capacity claim is introduced by this slice.

Verified 2026-10-05: fresh independent SPEC/QUALITY integrity review passed
with no Critical, Important or Minor findings. The complete opt-in suite passed
all 1,299 cases with zero failures, errors or skips in 2,646.14 seconds
(44 minutes 6 seconds), versus the prior 52,202.15 seconds. The unchanged genuine
all-factor native case took 1,701.331 seconds (28 minutes 21 seconds), versus
50,563.872 seconds: about 29.7 times faster in this comparison. The same authentic
64-anchor parser scan dropped from 38.398736 to 1.614710 seconds, with 7,009 raw
event reads and no historical readers. These local and end-to-end measurements
are separate evidence; neither establishes fullgraph assay capacity.

The fresh native artifact retains all 14,048 events, 40 trainings, 24 interventions,
768 responses, 128 native-attested anchors and 67 checkpoints. Independent XML
and artifact checks confirmed the frozen implementation hashes, all 73 existing
producer regressions, 35 new projection regressions, fullgraph checkpoint tests
and native compiler smoke. The scientific report remains `unsupported`, with
the same negative gates; formal qualification/configuration and CLI work remain
pending.

#### Task7B3i: measure bounded fullgraph resource components

**Files:** Create `docs/experiments/2026-10-05-fullgraph-capacity.md`; update
status docs. Keep package source, tests and scientific gates unchanged.
Measurement scripts and native artifacts remain private ignored outputs.

- [x] Measure actual current-source fullgraph factory, state/candidate digests,
  NPZ write/restore/hash, process working set and scoped scratch-file sizes.
  Authenticate the compatible checkpoint and preserve source/checkpoint bytes.
- [x] Repeat a 500-ms black retention call and separate 100-ms A/B/C response
  calls twice from the same source, using production flags; verify native tick
  advances, endpoint digests and telemetry equality excluding wall-clock fields.
- [x] Publish component ranges and clearly scoped memory/storage measurements;
  distinguish illustrative workload arithmetic from total runtime or resource
  guarantees. No formal configuration, qualification or assay capacity claim.
- [x] Obtain fresh independent measurement/report review, check provenance and
  documented arithmetic, then commit/push only the report and plan status.

Verified 2026-10-05: bounded native probe completed in about 21 seconds;
two real fullgraph factories and two repeats per black/A/B/C condition preserved
complete native endpoint and telemetry equality. All 29 package source files and
the compatible checkpoint retain their hashes. The 500-ms black calls took
1.297331/1.359500 seconds; 100-ms A/B/C calls took 0.272256-0.289507 seconds;
process lifetime peak working set was 1,065,197,568 bytes. The linked
[result report](../../experiments/2026-10-05-fullgraph-capacity.md) records
provenance, exact component samples and limitations. Fresh independent
SPEC/QUALITY review passed with no Critical, Important or Minor findings;
root independently checked actual telemetry/checkpoint files, hashes, counters,
determinism and arithmetic. This documentation-only slice preserves the existing
1,299-case acceptance and does not establish whole-assay resource capacity.
A representative-source one-anchor recorder/replay pilot remains the next
resource gate; formal qualification and configuration remain pending.

#### Task7B3j: trained fullgraph one-anchor recorder/replay resource pilot

**Files:** Create `docs/experiments/2026-10-08-fullgraph-anchor-pilot.md`; update
this plan only. Probe/raw/native artifacts remain ignored; package source,
tests, schemas, dependencies and scientific gates remain unchanged.

**Declared sample:** Fresh prepared fullgraph, qualification-family seed11,
paired A/order AB, grid CS100ms/DAN onset0/post-pair gap500ms and the existing
`controls=True` training timeline. This is a resource declaration, not a selected
qualification setting. Actual association reference109000ticks and complete
training source111000ticks stay distinct. T10000ms gives CS onset209000ticks,
anchor208000ticks and9700ms reward-free source-to-anchor replay. Two independent
A/B siblings each execute the existing100ms-prelude/100ms-CS/200ms-tail schedule
from one authenticated scratch archive outside inventory. No frozen config,
scientific response classification or confirmation terminal is manufactured.

- [x] Execute the complete actual declared native training and retain exact
  source/checkpoint occurrence, identity/groups, input/call flags and clocks.
  Measure complete/candidate hashes, factory/write/restore/ingest and observations.
- [x] Build one actual black-retention recipe/anchor through the validated prefix;
  verify scratch/independent siblings. Produce a real sealed pilot with ordinary
  integrity verification and separate actual isolated prefix/sealed native replay.
  Require the same nonempty singleton anchor attestation; replay reconstructs
  black endpoint only, not all training or response observations.
- [x] Measure validation/recipe/anchor/replay wall time, actual event/checkpoint
  bytes and scoped process/scratch resources. Preserve all package/schema bytes,
  avoid overlapping-timer totals and distinguish this one sample from a full
  assay/qualification/cold-cache/concurrent-capacity guarantee.
- [x] Independently check artifact/bindings/counts/clocks/arithmetic, obtain fresh
  measurement/integrity review, then commit/push only public report+plan. Use fresh
  focused baseline plus genuine probe checks; unchanged prior1299-case source
  acceptance is historical, not a newly executed complete suite.

Measured on `ec6474b3693beb49a9dde28c0e02c3cca9987dad`: one actual trained
fullgraph pilot passed with six sequential factories, 92 native observations,
59 sealed events, three durable checkpoints and one retained anchor. Genuine
prefix/sealed native verification took 82.445835/81.125468 seconds and attested
the same retained endpoint. Process lifetime peak was 1,274,982,400 bytes;
dedicated regular-file boundary maximum was 47,724,285 bytes, not an upper bound.
Root independently rebuilt the recipe/envelope and checked clocks, inventory,
state/file/telemetry hashes and resource arithmetic. Fresh focused baseline:
346 passed in 33.80 seconds; package/schema bytes and historical 1,299-case
accepted source remain unchanged. See
[`2026-10-08-fullgraph-anchor-pilot.md`](../../experiments/2026-10-08-fullgraph-anchor-pilot.md).
Independent SPEC/QUALITY review passed with no Critical, Important or Minor
findings on the frozen measured report. The documentation checkpoint also adds
tracked cloud handover/TODOs and repository instructions, without changing the
measured source or raw artifacts. This sample does not
qualify settings, demonstrate learning or establish full-assay capacity; a
longer retained endpoint remains a separate bounded resource gate.

#### Task7B3k: bounded longer-retention fullgraph recorder/replay costs

**Files:** Create `docs/experiments/2026-11-01-fullgraph-retention-pilot.md`;
update status only. Preserve package source, schema, dependencies and prior
measurement bytes. This is a resource gate, not a qualified timing selection.

- [x] Execute the same actual fresh paired-A/order-AB, qualification-family
  seed11 schedule and retain genuine source111000 versus reference109000 ticks.
  Resource horizon70000ms puts anchor808000 and CS onset809000, requiring
  69700ms of explicit reward-free black:139 calls500ms plus one200ms call.
- [x] Produce one genuine169-event prefix recipe/anchor and two independent
  A/B siblings with existing prelude/CS/tail, ending812000. Require179 sealed
  events, three durable checkpoints, six sequential factories and452 actual
  observations including both140-call isolated native replay passes.
- [x] Record current source/native/input/state/recipe/file bindings, actual
  observation/checking/recording/verification costs and scoped memory/disk.
  Preserve negative/qualification boundaries and no whole-assay ETA claim.
- [x] Independently validate artifacts/arithmetic and obtain a fresh scoped
  scientific-integrity/resource review before the feature-only checkpoint.
  Continue the remaining source-bearing work afterward; no automatic pause.

Measured on `460f5b046e4e18df2d147c18ba73899ac660032a`: one primary completed
452 actual observations, 179 sealed events, three durable checkpoints and one
anchor across six sequential fullgraph factories. Actual source-to-anchor time
was 69,700 ms; prefix/sealed native verification took 683.137087/732.934150 s
and attested the same singleton. All 140 original/prefix/sealed black telemetry
payloads match canonically excluding only the two timing fields. Observed
process lifetime peak through the final sample was 1,315,819,520 bytes;
dedicated file-boundary maximum was 56,872,704 bytes. Root independently checked
all 460 output files, source/schema hashes, rebuilt recipe/envelope, actual
checkpoint states, clocks and arithmetic. See the
[result report](../../experiments/2026-11-01-fullgraph-retention-pilot.md).
Fresh independent SPEC/QUALITY review passed with no Critical, Important or
Minor findings. This is assay-style False/False
detail flags, not the legacy qualifier's detail-enabled cost, whole-assay
capacity, scientific support or formal qualification. No new complete suite ran.

#### Task7B4: strict qualification integration after Task8

Keep the same plan/workspace. Source slices a–e and bounded f.1/f.2/f.3a/f.3b are implemented
and accepted. Earlier e.3 tiny-native 9/51/408 acceptance is source-specific;
f.3c–f.3d/f.4–f.6/g remain future,
without permission to run formal qualification now. Preserve all existing confirmation
routes and scientific gates. Concrete per-slice briefs must settle exact data
shapes before implementation; do not bootstrap with a fabricated frozen object.

**7B4a — shared schema-only archive reader.** Own `neural/checkpoint.py` and
checkpoint tests. Produce `read_checkpoint(path, expected, schema, n)`;
`schema` maps each array name to its exact dtype string and shape. Existing
`load_checkpoint(path, expected, templates, n)` keeps writable-destination
checks and delegates to that single decoder, without changing NPZ/preimages.
- [x] RED: read valid archives through a schema without writable live arrays;
  preserve rejection of malformed metadata, zip/schema/shape/dtype/finite/queue
  state and all existing destination/nonmutation behavior.
- [x] GREEN: factor the existing codec; run focused checkpoint guards, review
  and complete ordinary acceptance before the bounded feature checkpoint.

Accepted on 2026-11-01 after independent spec/quality review and two scoped fix
rounds: the NPZ-only entry boundary and malformed-header error normalization are
covered by genuine guarded regressions. Complete checkpoint focus: 484 passed
in 36.06 s. Root ordinary suite: **1,556 passed, three declared opt-in skips in
1,045.08 s**; separate actual fullgraph suite: **two passed in 10.91 s**, no
skips/errors. The ordinary skips are the all-factor case and both graph cases;
only the graph cases were subsequently run. All-factor Task8 evidence remains
historical on its own source revision; repeat the full matrix at selected
producer integration/final source-bearing acceptance. Final review has no
Critical, Important or Minor findings. NPZ writing, native core and hash formats
are unchanged. Lossy structured/subarray dtype templates are explicitly rejected;
the locked NumPy private header API preserves NPY1/2/3 support. This codec issues
no native map context or scientific proof.

**7B4b — authentic qualification map context.** Own recorder/replay helpers and
native tests. Extend private attestation with optional immutable
`qualification_context_bytes`; derive it from the fresh compatible engine
using actual rehashed maps/schema/initial weights before the first restore.
Preserve the current reused-engine loop: qualification uses exactly one fresh
factory for zero/one/multiple anchors. Confirmation stays zero for no anchors,
one otherwise; the builder creates no engine.
Private issuance binds the exact result owner and artifact bytes; source-freshness
checks recompute the current full package fingerprint without creating an engine.
Preserve existing nonempty named groups and genuine empty candidate selections.
- [x] RED: wrong equal-length candidate/KC/DAN maps, swapped compartment maps,
  stale/transplanted/missing contexts, mutation after proof and ordinary objects
  claiming context. Prove zero-anchor native context and zero builder factories.
- [x] GREEN: artifact-bound native context with decoded-copy access only;
  unchanged checkpoint format and confirmation replay regression coverage.

Accepted on 2026-11-01: fresh independent Astra spec/quality/integrity review,
no Critical/Important/Minor findings. Root actual fullgraph suite **three passed
in 24.46 s**, including the new incomplete zero-anchor map-prefix case (10.621 s)
and both existing graph tests. One verifier factory, actual maps/schema and
engine-free intake were checked; no scientific terminal/seal/config was created
by the map-prefix case. Root ordinary suite **1,627 passed, four opt-in skips in
1,155.74 s**, no failures/errors; those skips are all8 and the three separately
passed graph cases. No new all-factor result or scientific qualification follows.

**7B4c — declared, authenticated grid and bounded history.** Own qualification,
CLI metadata, analysis grid reduction, recorder/schema and their tests. Add the
six missing strict metadata declarations and 96 `qualification_grid_binding`
records with exact occurrence/raw-observation references. Point replicates name
`grid_evidence_id`. `_reduce_qualification_grid(value)` consumes genuine proof
context, validates all candidates/inventory and recomputes metrics/selection.
Use explicit `controls=True` grid schedules; do not copy later raw effects.
- [ ] RED: omitted metadata, discarded-source swap, occurrence alias/ordering,
  altered raw summary/selection, old mixed washout schedules and branch overflow.
  Enumerate the no-skip proposed grammar before enabling the changed cap.
- [ ] GREEN: closed qualification-only 5120 branches (bound4850), unchanged
  2048 snapshots/10000 relevant events; reject orphans, retain/drain all history.
  Static CP/event bounds1602/8099 are not execution/capacity measurements.

Implement this as two sequential reviewed slices: **7B4c.1** owns capture,
declarations, binding schema, recorder position and closed grammar; **7B4c.2**
owns the authenticated reducer and minimal shared pure arithmetic extraction.
Execute c.2 as two reviewed commits: **c.2a** extracts compact pure arithmetic
actually used by the producer; **c.2b** delivers the complete authenticated
two-pass component. Shared arithmetic must consume compact measurements, not
raw telemetry histories or a running engine. Genuine incomplete inputs remain
inconclusive after all available evidence is checked; malformed proof/content
is an error. Complete assessment still requires all 96 units and 144 points.
The first component accepts grid-only prefixes/negative seals and explicitly
rejects selected activity until its exact inventory is wired in the later
selected integration; no silent non-grid exemption or public-builder change.
The reviewed c.1 enumeration corrects the earlier unproved 8064 relevant-event
estimate to 8099, including 40 derived control summaries. Its 4850 intended branch
slots and 1602 checkpoint slots describe future selected/replay integration;
the operational branch cap remains 4096 until emission conformance is established.
Bindings have bounded ordered `failures` (one base failure OR up to four T
failures), retaining actual partial roles. Use existing summary-branch framing
and real global append positions. Reconstruct KC vectors/drive from linked
call-level pathway fields as well as response/bound bins and real archives.
Two complete stream passes and sequential archive projection retain at most one
configuration's eight compact unit projections, not the raw stream. A negative
remaining retention gap is independently schedule-infeasible; unavailable failed
call data is error/inconclusive, never a fabricated scientific negative. This is
a design bound, not measured capacity. Test the prefix/seal grid component
directly; public sealed-only freezing and arithmetic-fixture migration stay in
7B4f with selected evidence from d/e. Do not fabricate contexts/frozen objects.

- [x] c.1 capture/declarations/grammar: independent spec/quality review without
  Critical/Important/Minor findings. Worker focus 462 passed, one sandbox junction
  skip in 277.75 s. Root ordinary acceptance **1,693 passed, four declared opt-in
  skips in 1,119.95 s**, no failures/errors; compiler and junction tests passed.
  Three actual fullgraph cases passed separately in **18.79 s**, without skips.
  The ordinary skips are all8 and those graph cases; no fresh all8, complete native
  grid, formal qualification or capacity claim. Frozen reviewed hashes matched.
- [x] c.2a compact producer arithmetic: independent Astra numerical/integrity
  review without new Critical/Important/Minor findings. Worker module 119 passed
  in 259.59 s; root qualification/analysis/replay/CLI acceptance **470 passed,
  one declared opt-in skip in 349.63 s**, no failures/errors. The fullgraph context
  case is the sole skip; fullgraph/all8 were not repeated. Reviewed hashes matched.
  No authenticated consumer, formal qualification or new scientific support.
- [x] Separately correct inherited one-spike/C-floor and washout-equality rounding:
  actual integer counts, qualification `<1` versus confirmation `<=1`, washout
  `w > max(5*r,1)`, direct canonical conversion after integer differences. No
  tolerance or unrelated delta/gain/effect/state/KC/sham rewrite. Raw formats and
  versions remain; source identity distinguishes intentionally corrected scalars.
  Fresh independent Astra review C0/I0/M0. Worker full qualification/analysis
  **774 passed in 315.52 s** and two final native tests **passed in 39.55 s**.
  Root complete ordinary acceptance **2,230 passed, four declared opt-in skips
  in 1,064.83 s**, no failures/errors; actual graph cases **three passed in 18.03 s**.
  Ordinary skips are all8 and those graph cases; all8 was not repeated. Reviewed
  hashes matched. No formal qualification, support or capacity approval.
- [x] c.2b authenticated two-pass reconstruction and genuine prefix/seal tests.
  The private component has passed independent source/integrity review and
  ordinary Windows acceptance: **2,286 passed, six declared opt-in skips in
  1,703.31 s**, no failures/errors. The four actual MaleCNS compatibility cases
  passed separately in **25.42 s**. Ordinary skips are those graph cases, the
  all-eight matrix and the exact96 integration. The latter passed separately:
  **one test in 5,124.53 s**, no skips/errors/failures. Actual qualify produced
  all96 units/144 points; genuine prefix/sealed map contexts and engine-free
  reductions agree on the complete negative tiny-model assessment. It contains
  89,831 events, 1,478 checkpoints and 3,594,389,820 event bytes. There are zero
  anchors: this is native map/content authentication, not training-history replay.
  Expanded available-prefix, recovery, source-tamper and lifetime cases passed in
  the ordinary suite. All-eight assay acceptance was not repeated.
  Historical c.2b Windows source identity; the costly96 case was not repeated for d:
  `64041111c7cf3edfaf51128e071b79d939875937f810790c00d1425458c6e60e`.
  Parent c/cap activation and public freeze integration remain unfinished.

  Measured tiny-native full-grid phases, one Windows sample on this source:

  | Phase | Wall seconds |
  | --- | ---: |
  | Actual grid production | 1,588.87 |
  | Prefix validation and native context check | 1,312.07 |
  | Prefix grid reduction | 787.02 |
  | Sealed validation and native context check | 656.29 |
  | Sealed grid reduction | 779.41 |

  Checkpoints total 13,786,929 bytes, largest 9,384 bytes. Actual aggregate
  simulated duration is 385,844,000 ticks across restored branches, not one
  continuous animal trajectory. These measurements are not fullgraph capacity.

**Early detail-on resource sample after c.2b — historical, completed and reviewed.**
The [published Windows report](../../experiments/2026-11-02-fullgraph-detail-prefix-pilot.md)
records exit 0 and independent measurement review with no findings on source
`64041111c7cf3edfaf51128e071b79d939875937f810790c00d1425458c6e60e`,
commit `21f788342b276e1d8a323f572e37e248542948d6`: 38 calls/45 events/two checkpoints,
inconclusive/one evidenced unit/no points/no selection. Final sampling recorded
630.546 s, 55,267,543 dedicated bytes and 1,089,613,824 bytes lifetime peak working
set; later report writing/exit are excluded. These are earlier-source measurements,
not current d acceptance. The 1,617,776,145 global profiler
dispatches have unmeasured dispatch overhead, so these durations cannot establish
unprofiled throughput or justify optimization/capacity projections. The unprofiled
diagnostic follow-up now precedes further integration; g still owns integrated capacity.

The completed predeclared route and limits were: before d/e/f source edits, measure
the first canonical grid0/seed11/pairedA/orderAB prefix through its first paired
training checkpoint: actual baseline, A/B/C pre-trials, pre-replay and training,
including detailed 500-ms calls. Preserve every scheduled interval and stop as
an unbound incomplete prefix; no binding, terminal or seal is invented. Release
producer/verifier engines in sequence, obtain fresh native context, and reduce
all available data. A successful diagnostic result stays inconclusive.
Measure actual candidate/KC/DAN vector dimensions, canonical line/file and NPZ
bytes, phase CPU/wall and process memory, with declared stop criteria and timer/
sampling limitations. Predeclare stops at 30 minutes wall time, 8 GiB of dedicated
output/scratch, or 4 GiB process working set/lifetime peak. Before native imports,
require at least 20 GiB free disk and 8 GiB available host RAM, with working OS
memory monitoring. Check budgets at quiescent boundaries; individual allocations,
native calls and scans cannot be interrupted by those checks. Preserve partial
artifacts on a stop and do not relax limits automatically.
This exposes immediate capture/format/reader costs early;
it does not establish complete grid/assay capacity, native training replay or
scientific support. A measured failure requires its own bounded design review;
do not drop ancestry, controls or gates. Integrated g remains mandatory.
- [x] Execute, independently review and publish this bounded Windows sample
  after the accepted c.2b checkpoint; keep its source identity explicit.

**7B4d — caller-owned selected native execution: implemented and accepted.**
Own `assay.py`, qualification owner metadata and producer tests. Extract `_produce_cohorts(engine_factory,
recorder, *, execution, cohorts, conditions, baseline_occurrence, namespace,
measure_replay=False, confirmation_replay_resolution_hz=None)`;
execution declares family/seeds/identity/population/
candidate/timing/window/two retentions/per-seed A/B/C/black hash mapping only.
Outer confirmation wrapper retains genuine frozen validation and lifecycle.
The separate confirmation-only scalar comes from that genuine validated config;
qualification forbids it and omits unavailable resolution/replay fields until e.
Reject `measure_replay` unless exactly False before e; do not fabricate zero.
Add only the actual `black_input` descriptor to CLI qualification metadata and
its focused test, before recorder creation. Require it against actual black RGB
and input hashes; never retrofit metadata on a populated recorder. Keep the
intermediate emitter separate from legacy `qualify`/public evaluator wiring.
Require paired in every canonical conditions subset, matched_reference for
necessity/sufficiency, and one cohort for namespace=False. Preserve confirmation
names; qualification uses an explicit selected namespace, reserving all requested
names against the existing inventory before writes. Use actual global recorder
positions, including anchors. Authenticate the caller's exact baseline event/
occurrence and native state, preserving legitimate nonzero factory baselines.
Preserve factory counts/reuse and trial restores; allow exactly one additional
quiescent baseline-authentication restore on the existing preflight engine,
with equal state/clock and no observation. Count it separately from baseline trials.
Replace source authentication's whole-prefix list with bounded streaming lookup
and complete EOF drain, retaining exact occurrence/descriptor and post-factory
byte/state checks. No persistent trust cache or omitted discarded history.
The False/confirmation returned paired engine is production data; f owns final physical
branch/clock framing, and e owns actual repeated response measurements.

- [x] RED: real native qualification seed11 cannot use the confirmation-only
  wrapper; reject late source/clock/input/family errors before creating output.
- [x] GREEN: one qualification cohort's five sources, three interventions and
  independent two-T siblings, then eight-factor 40/24/128/768 evidence. Preserve
  all existing confirmation APIs/counts and exact occurrence/transfer checks.

Independent source review closed the fresh verifier-group guard finding; the
test-only baseline-accounting refinement also passed independent review. Focused
R1 acceptance was 124 passed/one opt-in skip in 1,271.88 s. Actual R2 eight-factor
selected and legacy confirmation cases passed on unchanged package bytes; their
full inventories and R1/R2 acceptance distinction are recorded above and in the
handover. The extra quiescent restore changes neither 64 actual baseline trials
nor the asserted 625 legacy production factories. This completes d production,
not e's response-resolution evidence, f's public lifecycle or g's capacity gate.

**7B4e — actual replay-resolution measurements: implemented and accepted.**
Follow the [strict selected-repeat contract](../specs/2026-11-01-strict-qualification-contract.md).
Own producer/analysis/schema, narrow recorder dispatch/reference helper and
existing tests. Exact qualification-only True enables independently restored
lockstep pairs; preserve False/confirmation behavior. Use deterministic `/repeat`
IDs, real window-stop Hz/W metrics, complete tails and closed diagnostics.

- [x] e.1: standalone private `_append_reference` after successful public append;
  unchanged None-return append, actual sequence/hash, healthy/+1 guards and no
  cache/scan/proof issuer. Independent review and recorder/replay plus actual
  fullgraph context acceptance passed on its historical source recorded above.
  This foundation alone had no True wiring; e.3 now uses it in production.
- [x] e.2: closed diagnostics/W projections/schema and independent current-pair
  stream comparison implemented and source-reviewed R1; focused115 tests passed.
  Affected-file and actual native-context acceptance passed on the exact R1 bytes;
  preserve ratified map/byte rules. This is recorded consistency, not full production.
- [x] e.3: source-reviewed lockstep native production; actual tiny-native 9/51/408
  checks and entire assay-module compatibility passed. Parent e implementation
  acceptance is complete; f's global assessment/lifecycle remains open.

The released e.3 design requires actual Engine/Brain independence and cross-field
mutable-buffer nonoverlap before either restore, then both-parent rechecks before
starts. True-only cleanup returns the actual last successful repeat owner after
both tails/diagnostic append through scratch cleanup; False/confirmation keeps
its training producer. f binds actual final diagnostic/owner, not a guessed branch.
Paired/full-cohort/full-matrix checks observed 21/130/1,033 production factories.
The full matrix passed on the four-node fixture; this is no capacity claim.

- [x] RED: local copied-zero/late-T, whole telemetry/tail/state/map, append/count,
  rehashed-reference, PRE-reuse and EOF guards covered by e.2/e.3 tests/oracles.
- [x] GREEN: nine paired/51 full-cohort and complete 24 PRE + 384 POST comparisons;
  768 logical cells with exact PRE reuse checked in the native test oracle.
  No extra NPZ, trust issuer, cap activation, public freeze or scientific approval;
  g retains actual controlled unprofiled capacity measurement.

**7B4f — truthful terminal and real freeze lifecycle.** Own analysis,
qualification, recorder/schema and tests. Share `_evaluate_qualification(value)`
over genuine prefix/seal proof plus a private execution contract. Keep public
`build_frozen_config(VerifiedRun)` sealed-only and engine-free.
Follow the [six-slice integration plan](2026-11-02-strict-qualification-integration.md).
- [x] f.1: declaration reducer plus explicit integer C flag; source review and
  bounded R1 analysis/source-identical related/normal-host acceptance passed.
- [x] f.2: corrected bounded checker/EOF adapter, with POST hash selector,
  five prior events/twelve operations/sixteen PRE rows, one finish/release/late watch.
  All POST source-origin intervention IDs match; only actual INTERVENTIONS own
  intervention-checkpoint roles. Source review and bounded acceptance passed.
- [x] f.3a: composable grid ownership/measurement; standalone two-pass behavior,
  explicit final/terminal ownership and bounded one-configuration acceptance.
- [x] f.3b: `_DeclaredEvidenceAccumulator` with explicit actual global sequences,
  genuinely neutral gaps and one-shot finish; bounded source/runtime acceptance passed.
- [ ] f.3c: selected component using f.2/f.3b, exact inventories/controls and late watches.
- [ ] f.3d: genuine combined same-two-pass evaluator, archive/final binding and cap proof.
  Remaining slices need sequential briefs; C1 is locally parked/unaccepted, C2 UNRELEASED; no automatic resumption after the completed measurement checkpoint.
- [ ] Independently reconcile all selected physical/logical references, sources,
  PRE reuse and EOF in the production shared evaluator; e's test oracle does not
  implement this f requirement.
- [ ] f.3d alone owns exactly one final `checkpoint` named `brain-after.npz` on the actual last repeat
  branch after full selected/control inventory, bound to diagnostic/owner/anchor/
  clock/decoded archive. This is no general late-event exception or local-wrapper rule.
- [ ] Keep complete96 native negative coverage historical until separately budgeted
  current-source acceptance after f.3d stabilizes. Genuine partial/native component
  tests do not prove prior grid eligibility; internal declared dispatch/math fixtures
  cannot issue proof or enter the genuine evaluator as a trusted selected result.
  Positive native eligible-grid→selected lifecycle coverage remains unavailable.
- [ ] RED: early support, missing causal cell/context, forged prefix/frozen
  data, terminal/report mutation and integrity-only objects claiming native proof.
- [ ] GREEN: prefix native verification, one evidence-bound terminal, seal,
  independent sealed evaluation/report equality. Complete valid negatives never
  freeze; malformed/incomplete data do not become scientific negatives. Keep
  mathematical fixtures separate from artifact/native proof.

**7B4g — CLI and integrated capacity.** Own CLI, assay wrapper and integration
tests. `run_assay(engine_factory, frozen, *, output_dir)` runs all frozen cohorts;
`assay --config PATH --output-dir PATH` uses actual fresh factories and refuses
overwrite/bad identity/config, rather than returning a preconstructed engine.
- [ ] RED/GREEN: actual CLI routing, strict native negative qualification and
  sealed verification. Do not create a positive config to continue a negative run.
- [ ] Benchmark actual detail-enabled grid/archive I/O and THREE verification
  boundaries: grid prefix before selected production, final prefix, independent seal,
  including a controlled unprofiled follow-up with coarse phase wall/process CPU
  and boundary memory/file samples before runtime, optimization or capacity
  decisions; do not extrapolate or subtract partial overhead from the profiled
  early sample. Conservatively account for the fixed complete grammar, review
  and complete source-bearing acceptance. Only then enter Task9; no capacity approval is
  inferred from the existing False/False resource samples.

### Task 8: Add a motor-only adapter without a behavioral claim

**Files:** Modify `src/fly_connectome_sim/experiment/adapter.py`, `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `tests/experiment/test_adapter.py`, `tests/experiment/test_recorder.py` and the primary-classification regression in `tests/experiment/test_analysis.py`. Keep `preference-adapter/v1` readable for old artifacts.

**Interfaces:** `LateralMotorAdapter(version="lateral-motor-adapter/v1", action_threshold_hz=1.0).adapt(telemetry) -> MotorDecision` uses only `motor_right - motor_left`, with `evidence_strength=abs(right-left)/(right+left)` (zero when both are zero). It never reads MBON activity, stimulus identity, condition, reward or event metadata. The 1 Hz threshold is an explicitly engineered display rule, not a calibrated behavioral threshold. This task exposes unvalidated motor telemetry only; motor qualification and held-out validation require a later dedicated design/plan.

- [x] **RED:** Assert MBON-only changes cannot affect action, right/left motor changes produce the corresponding proposal, zero/threshold evidence defers, metadata changes do nothing, and v1 output remains readable.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_adapter.py -q`; expected failure: missing motor-only adapter.
- [x] **GREEN:** Implement the adapter and use `evidence_strength`; never infer direction from MBON07−MBON11. Recorder labels the output `engineered_unvalidated_motor_readout` and it cannot alter the primary analysis classification.
- [x] Run focused/full pytest. Commit adapter/recorder/schema tests together: `feat / motor-readout : Separate lateral evidence from MBON analysis`.

Independent scoped review: spec and quality passed without Critical, Important
or Minor findings. Root complete Windows acceptance on 2026-11-01:
`FLY_CONNECTOME_SIM_FULL_TEST=1`, `python -m pytest -q -p no:cacheprovider`
(fresh ignored basetemp, JUnit output and `--tb=short`): **1,449 passed in
3,237.62 s**, no failures/errors/skips or deselections. It includes the genuine
all-eight-cohort case (2,134.180 s), actual recorder/analyzer roundtrip (6.589 s)
and both fullgraph tests. The tiny-native artifact again has 40 trainings,
24 interventions, 768 responses, 128 anchors, 67 checkpoints and 14,048 events;
its report is unsupported with 136 negative gates. This is functional acceptance,
not formal qualification, motor validation or a source freeze.

### Task 9: Source freeze, formal qualification and held-out confirmation

**Files:** Create `configs/assay.synthetic.json` only after formal qualification; modify `tests/test_full_graph_engine.py` for opt-in end-to-end coverage; create a concise result document under `docs/`. Use ignored `runs/qualification-*` and `runs/confirmation-*`; do not modify packaged `.py`/`.cpp` after source freeze.

**Source-freeze rule:** Begin from a clean commit after Tasks 1–8. Run source/runtime verification and the complete suite including full graph. Record commit SHA and engine identity. From this point, any package-source change discards all formal qualification/config/confirmation artifacts and restarts Task 9 from a new clean commit. Tests, config and result docs may change because they are outside `model_fingerprint`, but they cannot alter numerical behavior.

Before that clean commit, pin LF checkout handling for packaged Python/C++
sources and normalize their bytes once. Recompute the source identity and run
acceptance on the normalized state; mixed line endings and a workstation's
`core.autocrlf` setting do not lock a fresh checkout's exact source bytes.

- [ ] Run formal `fly-connectome-sim qualify` on the full graph with qualification family/seeds `(11,23)`, all fixed grid points, both paired identities and AB/BA order. Apply matched controls and causal interventions to the selected candidate configuration, not as extra grid-selection dimensions. Record benchmark values and verify the artifact before selecting anything. If integrity, observability, state-shift, saturation, intervention or independent washout fails, stop: commit only an honest negative qualification report and do not create a confirmation config.
- [ ] If qualification passes, generate `configs/assay.synthetic.json` only via `build_frozen_config()`. It contains exact qualification hashes and engine identity, selected fixed-grid timing/window/sign/T, all floor terms, confirmation family/seeds `(101,113)`, conditions and intervention clocks. Independently review and commit this config before reading confirmation output: `feat / assay-preregistration : Freeze the held-out MBON11 assay`.
- [ ] **RED:** Add an opt-in integration test that requires all condition/factor/T/T+60/intervention cells, branch-local clocks, parent checkpoint hashes and deterministic scientific hashes, without asserting a positive classification.
- [ ] Run `$env:FLY_CONNECTOME_SIM_FULL_TEST='1'; .venv/Scripts/python.exe -m pytest tests/test_full_graph_engine.py -q`; expected new failure is missing held-out output/orchestration evidence, not source behavior. Clear the environment variable afterward.
- [ ] Execute `fly-connectome-sim assay --config configs/assay.synthetic.json --output-dir runs/confirmation-<unique-id>` once. Every condition starts from the same baseline checkpoint and matches exposure/order/side/time. Test A/B/C at T and T+60; interventions occur at the common training-end clock and then receive identical passive decay. Verify before analysis and classify without changing config or thresholds.
- [ ] Rerun the identical deterministic schedule into a separate directory only to compare scientific hashes; this is computational reproducibility, not another biological sample. Review reciprocal identity, global-gain residual, endogenous DAN, MBON07 state, and sham/necessity/sufficiency rows.
- [ ] Run the full suite again without changing packaged source. Commit the integration test and concise result document with artifact hashes/classification, never raw artifacts: `feat / held-out-assay : Classify the frozen full-graph experiment`.

## Final verification and interpretation gate

- [ ] Verify source/runtime locks and full pytest, plus the opt-in full-graph suite with `FLY_CONNECTOME_SIM_FULL_TEST=1`. Compare artifact hashes after deterministic rerun; exclude wall-clock fields only.
- [ ] Review the held-out report against the approved claim boundary. If any primary gate fails, state which one and report an unsupported or inconclusive model experiment. If all pass, use only the design spec's model-specific wording and the demonstrated T and T+60 duration. Report MBON07 state, endogenous DAN, motor results and runtime separately.
- [ ] Measured-data Replay v1 may proceed first under the explicit2026-11-02 product decision; LLM and scientific interpretation remain gated. Replay cannot upgrade failed scientific gates.
