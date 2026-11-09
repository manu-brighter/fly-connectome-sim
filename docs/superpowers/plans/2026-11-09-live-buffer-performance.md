# Passive-cell buffering performance implementation plan

> Use superpowers:subagent-driven-development sequentially. Fresh Sol worker per
> bounded implementation task; Astra reviews protocol, architecture and integrity.
> No worker subagents. Preserve others' edits. Controller owns docs, Git and runs.

**Spec:** [bounded performance protocol](../specs/2026-11-09-live-buffer-performance.md).
**Goal:** Measure fixed rolling cell storage and one pending image against the
accepted five-real-minute handoff bound without changing the engine/readout.
**Status:** Protocol/plan and all three source tasks independently accepted by Astra;
[software evidence](../../experiments/2026-11-10-live-buffer-software.md): Task1
640 passes; Task2 complete run694 passes/one fixture failure followed by the
corrected single-case pass. All695 distinct focused cases passed their latest
execution, no skips/warnings. Task3 final218 passes/two true Windows privilege
skips/three private preflight exclusions; source/CI split/lifecycle evidence accepted.
Final source publication/CI and Task4 remain; no native measurement yet.
**Stack:** Existing Python3.12/NumPy/pytest/PowerShell. No new dependencies.

## Global constraints and boundaries

Preserve the41-member neural package, existing reader/collector duration limits,
all old source/protocol/readout/supervision modules and completed artifacts.
Known A/B/black are deliberate performance inputs, not new independent confirmation.
No learning/DAN, API call, price activation, upload endpoint, browser work or deployment.
Source-bearing Tasks1–3 finish before concrete freeze; Task4 runs at most once.

Interfaces: Task1 supplies a fixed callback ring and bounded admission state.
Task2 uses these with the existing engine/header/recorder and owns a new exact
protocol/journal inspector. Task3 binds that protocol and entrypoint through the
unchanged owned monitor. Task4 consumes only accepted source and concrete readiness.
Shared CI edits are sequential; controller documents actual failures/skips/results.

## Task1 — Fixed ring and one-pending-image state

Fresh Sol owns new `scripts/market_live_buffers.py`, new
`tests/test_market_live_buffers.py` and one CI test path. No model/actual data run.

- [x] Record meaningful failing tests before implementation.
- [x] Implement the fixed1000×256 uint8 ring and four int64 index/tick arrays,
  strict atomic payload validation, chronology, wrap/evictions and declared hash.
  No unbounded callback history, file operations or rendering in the callback.
- [x] Export detached50-bin batches and five exact100-ms aggregates using safe
  sum dtype. Keep sink-body timings distinct from engine-side observer preparation.
- [x] Implement at most one active/one pending identity with exact monotonic
  five-minute expiry, full rejection, duplicate protection and no double handoff.
  Strictly increasing request sequences/high-watermark include full rejections;
  distinguish request identity from frame identity. No implicit retry/retargeting
  or growing completed-request store; no durable restart claim.
- [x] Test wrap beyond capacity, detached exports, maximum valid counts, invalid
  casts/types/shapes/clock gaps, exact aggregate arithmetic and digest chronology.
  Test queue deadline−1/equality/+1, stalls, duplicates, full-slot retention,
  sequence reuse after terminal/rejected states and new-sequence same-frame use,
  many rejections and invalid clock behavior without unbounded state growth.
- [x] Run focused tests; record real failures/skips and old-source preservation.
  Astra independently accepts source/contracts and tests before Task2 begins.

## Task2 — New bounded benchmark producer and auditor

Fresh Sol owns new `scripts/run-live-buffer-performance.py`, new
`tests/test_live_buffer_performance.py` and one CI test path. No actual runtime,
graph/header construction, native run or model response during implementation.

- [x] Synthetic test-first protocol/engine/callback fixtures; label injected scope.
  Prepare exclusively pins exact frame/decoder/source/package identities, memory,
  schedule, metadata/journal bounds and ring/admission contracts.
- [x] Native construction is behind lazy Task3 authority import. Build/bind the
  unchanged static header once, install its ordered cohort before any advance,
  run all120×500ms intervals in one continuous engine/decoder and save two states.
- [x] Observe fixed A/B/black phases and exact queue exercise. Check pending-image
  age at the actual first observe boundary; expiry gets labelled black fallback.
  B/burst arrive after the first A observe; C after the first phase2 observe.
  Bind before/after transitions to observations; no hidden replacement/early stop
  or admission work between the handoff check and observe dispatch.
- [x] Export only bounded completed callback batches after observe. Record raw
  bins, aggregates, original group telemetry, real clocks, sink/copy timing and
  ring state. Snapshot-ready is local availability, not browser publication.
- [x] Implement bounded snapshot/full-EOF audit, including all6000 bins/600 windows,
  population relationships,120 complete driver results, ring hash/evictions,
  exact cohort/source/clock/queue semantics, checkpoints and strict caps.
  Group comparisons use bins; unique selected-cell union uses the required
  interval total_spikes. Never fabricate unavailable per-bin whole-brain values.
  Use a small appropriate static-header validator, preserving authoritative lock
  checks; do not add a fictitious old KC grouping. State that offline inspection
  cannot repeat the runtime/annotation data join, stride selection or topology proof.
  Separate validity, correct expiry and positive observed handoff throughput.
- [x] Test valid success, deadline-expiry fallback, no-proposal completion, invalid
  callback/partial-run retention, resealed cell/group/window/ring/queue/time/source
  alterations, parser/summary caps, iterator closure and no-native inspection.
- [x] Focused regression only, actual results/skips and preservation recorded;
  independent Astra producer/auditor acceptance before the fresh Task3 worker.

## Task3 — Thin owned-supervision binding

Fresh Sol owns new `scripts/live_buffer_supervision.py`, new
`scripts/supervise-live-buffer.ps1`, new `tests/test_live_buffer_supervisor.py`
and the bounded CI split below. Preserve all accepted supervisor/frontend bytes.

Task2 measured334.94s for its focused run; prior Linux backend runs took632–686s.
Place the three new live-buffer test files in a separate15-minute job with the
same pinned checkout/uv/Python/dependencies and empty-runtime import checks. Keep
every preexisting test and both old jobs' budgets unchanged. Compare full test-path
multisets and validate workflow syntax; Astra reviews the complete diff. This CI
scheduling change does not alter900s native supervision or remove test coverage.

- [x] Test-first new protocol/version/entrypoint/source/path/runtime/limit/release
  bindings. Missing/altered authority must fail before engine construction.
- [x] Adapt the accepted thin adapter/frontend by necessary names only; reuse
  frozen monitor, compiler guard, counted scratch and owned-process lifecycle.
  No monitor-global patch or new process-killing implementation.
- [x] Verify new bindings and harmless public completion/cancellation/owner-death
  behavior, actual worker identity and unrelated-process survival. Preserve exact
  old-source byte evidence; do not run private model/runtime preflight here.
- [x] Astra accepts actual evidence/source/CI split and unchanged package fingerprint.
- [ ] Publish final source checkpoint and successful source CI before Task4 preparation.

## Task4 — One acquisition, independent result and next decision

Controller owns fresh ignored preparation/output/evidence, tracked result report,
handover/plan updates and publication. No frozen source edits during the attempt.

- [ ] Independently review exact command, fresh directories, source-CI, actual
  worker/compiler/cache, source/readiness union and900s/4GiB/256MiB bounds.
- [ ] Run once under owned supervision. Observe to completion or termination;
  preserve partials, stderr, actual resources and zero-owned-survivor evidence.
- [ ] Public offline full inspection and Astra independent raw-cell/group/ring/
  queue/clock/resource audit. Report actual waits, gaps and all outcome dimensions.
  No automatic retry, retuning or rate/generalization claims from a short burst.
- [ ] Publish reviewed evidence and update the continuation record. Decide whether
  the scoped performance result supports the local synthetic Stage C board;
  keep real upload/display/load/rehearsal and public-use gates distinct.
