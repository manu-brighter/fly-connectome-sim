# Bounded native worker — sequential implementation plan

Status: independently accepted prospectively, 2026-11-10; implementation pending.
The [accepted design](../specs/2026-11-10-native-worker-design.md) is binding.
Actual acquisition and any retry require the separate gates below.
Prerequisite: independently accepted intake checkpoint and its exact successful CI.
Method: bounded Sol implementation, independent Astra contract/integrity review.
Only one implementer owns a task at a time; no parallel ownership of shared files.
All workers are not alone in the repository: preserve unrelated edits and source.
Controller publishes reviewed source/doc checkpoints under existing branch rules.

## Gate 0 — freeze and independently review the prospective contract

Owner: controller plus independent architectural reviewer, not the implementer.

- Read the exact draft, accepted D1/D2/intake contracts and actual public APIs.
- Resolve and record the host-start timestamp limitation explicitly:
  pre-observe announcement/check cannot attest entry to the first C++ step.
  Preserve original TTL; do not silently relabel it native physical-time attestation.
- Verify forty-observation budget arithmetic, active reserved slots and late uploads.
- Freeze normative Appendices A–G: exact frames/DTOs/source declarations, public receipt
  capture/outbox, monitor/cleanup and seal schema; no payload design deferred to Sol.
- Check ordinal7 emits observation+complete before its sole ACK/end, including index39.
- Freeze all untouched packaged/helpers/D1/D2/price files by hashes.
- Recheck the already recorded read-only source/header/DLL/compiler size evidence
  against fixed Appendix B caps; do not construct an engine or execute zig version.
  Prepare only hashes/checks an already matching cache; a missing cache is a prerequisite.
- Bind the one real hidden zig.exe version probe required by unchanged build_native,
  including same Job, exact argv/environment/output/deadline and cache mutation guards.
- Publish accepted tracked spec/plan before first-party implementation begins.
- Record review findings and their resolution; interrupted review is not acceptance.

## Task 1 — strict protocol, validation and offline evidence

Sol owns new market/native_protocol.py and tests/market/test_native_protocol.py,
tests/market/test_native_evidence.py. No native import, processes or runtime loading.

Consumes normative Appendices A–G; produces exact codecs, immutable DTOs and bounded
full-EOF event/monitor/cleanup integrity reader. No simulator or lifecycle duplication.

RED cases before implementation:
- Framing lengths, partial reads, duplicate/extra keys, unknown variants, sequence gaps.
- Bool/float/overflow/negative clocks/counts; body/header/nesting caps and wrong binary size.
- RGB/body digest mismatch; exact clock bracket order and deadline equality.
- Forty-observation limit; eight-slot availability with active exposure reservation.
- Bin continuity, all seven arithmetic profiles, equal/superset/disjoint populations.
- Mandatory-cell/group equality, sampled-KC inequality and 100-ms integer sums.
- Corrupted/truncated/trailing evidence, incomplete output never sealed.
- Tokens stripped from journal; source identity/last hash must match final seal.
- Complete Start tuple, null/variant matrix, digest-only ready and bounded full header.
- Overlap inclusion/disjoint lower bounds, selected-cell sum and166700-cell upper bound.
- Journal hash bytes, independent4096-event/12000-monitor caps and all final-seal fields.
- Supplied receipt-record schemas/revision sequences and journal_gap handling only;
  Task1 does not implement or exercise coordinator reconciliation. Actual public-D1
  final-read/expiry/pruning capture belongs to Task4; session outbox handoff to Task3.
- No imports/construction/calls to native, network or real process APIs.

Implement only these owned files, then run focused tests and relevant existing
D1/CellRing arithmetic regressions. Record actual RED/GREEN commands/results.
Independent review recomputes arithmetic from fixtures and inspects malformed cases.
No private old-run validator is weakened to make an arbitrary image fit.

## Task 2 — owned Windows transport with harmless processes

Sol owns market/native_windows.py, tests/market/test_native_windows.py and
bounded harmless-child fixtures under tests/market/fixtures/.
It may consume Task1 APIs; frozen supervisors and D2 ownership remain unchanged.

Implement suspended exact-interpreter launch, restricted handles/Job membership,
framed bounded duplex IO, stderr cap, separately persisted monitor/cleanup evidence.
Set/query the4GiB Job commit quota; distinguish sampled RSS/disk stop thresholds.
Implement only the exact one-shot hidden version-probe guard/adapter; no build path.
Retain exact handles/root lock on unconfirmed cleanup; seal only after required closure.
Public test seam accepts explicit harmless-child scripts only in tests.
Production launch target is fixed; no arbitrary executable/argv supplied over HTTP.

Required actual Windows process cases:
- Normal EOF/completion; partial/oversized frames; slow progress and full output pipe.
- Parent cancellation, owner death, nonzero child, child sleeping mid-frame.
- One permitted bound harmless probe, duplicate/unexpected probe/descendant, hidden
  launch, probe timeout/output cap and parent/child cache-mutation detection.
- Unexpected descendant/resource violation; actual commit quota/readback evidence;
  sampled RSS/disk limits and exact Job empty proof after cleanup.
- Creation-time/handle identity mismatch; unrelated live process remains untouched.
- Startup failure before CreateProcessW: nullable worker/not_created, no fake PID/sample.
  Created-but-unverified failure retains exact handles/root ownership and cannot seal.
  Verified worker actual exit and cleanup variants remain distinct; closure failure retains ownership.
- Injected OS-call failures and capability-handle leakage checks.
- Real two-frame ordinal7 exchange, including39: observation then complete then one end;
  no intervening ACK, duplicate advance or processed claim after persistence failure.
- Clean EOF followed by Job/handle/fsync/root-lock failure leaves no success seal.
- Monitor12000-row cap remains independent of4096 lifecycle records; stalled writer
  and owner death leave bounded incomplete evidence, not fabricated cleanup.
- No simulator import/runtime read/network/real compiler in any harmless child.

Tests use bounded real high-resolution deadlines; report controlled-time tests separately.
Run Windows cases on the host where required; Linux skips stay explicit.
Independent review examines actual process receipts, not just test totals.
No native model launches in this task, CI, or a fallback test path.

## Task 3 — worker loop and parent session, still software-only

Sol owns market/native_worker.py, market/native_session.py and
tests/market/test_native_worker.py, tests/market/test_native_session.py.
Task1/2 interfaces may be corrected only with scoped regression and re-review.
No D1/D2/price source modifications.

Worker composes the preserved engine/header/CellRing public APIs.
Parent handles readiness, source binding, one boundary, finite evidence and notices.
No ContinuousMotorDrive instance, price proposal, fixture dispatch or checkpoint restore.
Preflight/constructor do not instantiate the engine or run a compiler.
Prepare only reads/hashes the existing matching cache; it cannot build/fix it.
Bind the existing venv package path, pyvenv.cfg and fixed numpy/pandas/pyarrow
versions/metadata/init origins. The real worker uses the declared -S bootstrap;
no global/user fallback, installation or second worker.
Production start requires explicit allow_native_run plus an exact reviewed prepared digest.
Injected engine/header are accepted only by private direct unit-test entrypoints,
never by production CLI options or imported environment variables.

RED cases:
- Exactly40 observations; black advances; no new image after boundary32.
- Eight contiguous frames and same RGB; never re-observe after callback/partial failure.
- Start transmission stall, deadline equality, expiry after send but before observe.
- Timely announced start versus missing first measurement remains incomplete/unknown.
- Exact ordinal7 observation+complete send ordering/timer epoch before one ACK/end.
  Next boundary waits for both persisted frames and accepted durable D1 completion.
- Bootstrap hello/challenge/probe/header/ready transitions, meaningful silence versus
  first-byte/in-frame/compute deadlines, complete Start tuple and EOF39.
- Missing/duplicate/contradictory start/complete; zero-based session continuity.
- Observer/header configuration before advance; locked identity mismatch faults.
- Startup/observe/ack/model/wall/resource/counter limits; no automatic restart.
- Source mutation between prepare/release and stale prepared bindings.
- Public reserve_receipts/publish_receipts/receipt_progress/finish_receipts lifecycle:
  capacity reservation before D1 call, three-change normal batches/two-change emergency,
  explicit causal order, finite nonblocking outbox, async fsync/drain and terminal gap.
- Task3 validates supplied three-entry batches/causal tickets, saturation fencing and
  durable drain. The actual D1 call/snapshot capture algorithm remains Task4-owned.
- Harmless/private dependency-bootstrap cases: declared existing path succeeds,
  absent/shadowed/wrong-origin or wrong-version packages fail before engine/DLL work.
- Final rehash covers exactly Appendix F's source/lock/tool/cache/dependency-control
  subset and prepared control files under the shared25s finalization deadline.
  Mutate a bound fixture source after readiness: no final seal; preserve real prior receipts.
- Inspection verifies SourceCheck scope/subset digest/count/times and finite complete
  event/monitor/cleanup evidence without engine/writes.
- Monitor/intake remain responsive while injected computation is blocked.

Run deterministic fake-engine/clock tests plus harmless-process transport regression.
Separately review actual source and full fake evidence; call them software evidence.
Preserve the entire frozen simulator/helper/source set.

## Task 4 — D1 coordinator, optional HTTP and minimal UI

Sol owns changes to market/image_intake.py, market/local_server.py,
market/web/image-{protocol,state,main,view}.ts,
market/web/main.ts, market/web/render.ts and scoped styles;
new market/web/native-protocol.ts, market/web/native-state.ts;
tests/market/test_native_intake.py, tests/market/test_native_http.py,
viewer/tests/native-*.test.mjs and needed focused image tests.

Keep standalone intake v1 byte/shape behavior and price authority/client state unchanged.
Use one existing D1 controller for both pending and active states.
NativeSession only supplies bounded notices; coordinator alone invokes D1 methods.
No private-attribute bridges or second image admission implementation.

RED integration cases:
- Reserve/admit at changing remaining budget; no promise of model time at reservation.
- Pending approved during active image, original deadline preserved through dispatch.
- Two accepted images never overwrite active RGB, receipt count or status capability.
- Native completion is eight validated observations, not a send/ACK/partial exposure.
- D1 late/contradictory receipt precedence and10-second receipt timeout unchanged.
- Actual public-D1 reconciliation captures direct returns, then atomic snapshots
  (max3) and only disappeared-terminal status reads (max2), with unchanged3-entry batch.
  Reproduce A,B,A,B final-read expiry from FIX1 review; the new algorithm captures A.
  Induce a terminal read expiring the other ID, clock-fault fan-out, impossible live
  return, retention disappearance and revision gap: bounded capture or journal_gap,
  never inferred history/uncaptured extra read. No D1 private API or source change.
- Multiple transitions between polls, stop of pending+active and outbox saturation
  are coordinator-owned tests here; Task3 covers only session persistence/handoff.
- End/reject/clock/cleanup paths preserve all earlier completed receipts.
- No native mode until readiness; v1 parser rejects v2 and v2 validates every variant.
- Measured totals cannot race across session/image identity or pending moderation preview.
- Exact v2 acceptance envelope and v1/v2 parser dispatch; mixed-schema rejection.
- Last-measured versus in-flight/pending identity, per-image immutable terminal watermark,
  premeasurement null fields and normal-ended health from Appendix E.
- Server original Host/Origin/role/bucket/body/read/asset boundaries stay enforced.
- No native fault/loop/IO delay enters price polling, ACK or mutation paths.
- UI5-second transport and10-second completion-time measurement staleness, unknown clocks
  and late replies; preview/status replies cannot refresh measured age.
- Synthetic price Pause/Fortsetzen remains independent; native stop has no resume.
- No API reports processed from injected UI state without accepted D1 completion.

Run actual loopback tests against harmless fake session, strict viewer tests/build.
Bounded browser checks use only generated fixtures and explicitly synthetic measurements.
Keep the board's synthetic price banner; new pane labels its test measurement source.
Independent source/browser review closes all findings before CLI/native acceptance.

## Task 5 — explicit CLI, preflight/inspection, CI and checkpoint

Sol owns scripts/run-market-native-service.py, tests/market/test_native_cli.py,
narrow CI selection and operator documentation assigned by controller.
Controller owns handover/evidence/spec/plan status updates.

CLI modes: prepare, start, inspect; subcommand parsing requires explicit arguments.
Start requires --allow-native-run and exact --prepared-sha256.
A fresh work root and owned output root are mandatory; inspect never starts/rewrites.
Default invocation/help/import cannot start a child or engine.
Keep existing synthetic service CLI unchanged.
Report wrong platform/version/missing runtime as prerequisites, never install silently.
Describe20-model-second proof limit, actual timestamps and physical-entry limitation.
Document standalone intake versus bounded-native test and synthetic prices explicitly.

Run all new software/harmless-process tests, relevant Market regressions,
viewer suite/build and preservation comparison; report skips honestly.
Independent final source/security/integrity review before reviewed feature commit/push.
Observe exact source CI before actual acquisition preparation.
CI never executes prepared native start, accesses private data or enables paid APIs.

## Later Gate 4/5 — separately prepared actual native acceptance

Controller prepares one concrete run only after accepted source/CI.
Use fresh dirs, frozen generated A/B fixtures and exact40-observation/900s bounds.
Inspect actual interpreter/library/cache/locks/source hashes and monitor readiness.
Prepare itself performs only bounded reads/hashes of a matching existing cache.
Freeze one real hidden zig-version probe inside the acquisition's owned Job/budgets;
no compiler execution, build or engine construction occurs in ordinary tests/preparation.
Independent reviewer approves concrete source/protocol/budget/fixture-action bindings.
Only then explicitly release one native process; no actual execution occurs in this plan.

Freeze deterministic bounded test-client behavior before release:
after readiness, upload/approve A through actual public local intake APIs;
after BOTH A's confirmed start AND at least10 real seconds after A's successful202,
upload/approve B exactly once; preserve any refusal, with no rate-limit change/retry;
no retries, no additional photos, no synthetic completion/telemetry injection.
Retain all actual accept/refusal/decode/moderation/start/observation/completion results.
Specify script response deadlines and evidence caps in concrete preflight.
A failed dependency/expiry/resource/negative result remains a recorded outcome.
Stop at the fixed allowance; never extend or rerun to make an image complete.

Independently inspect full event/monitor journals, source/cache/probe bindings and
confirmed cleanup/final seal and the final bounded SourceCheck. EOF alone is never
accepted as clean ownership/storage closure or unchanged source evidence.
Require at least one genuine8-observation completion for positive integration evidence.
Check any second accepted image and all black intervals; disclose incomplete exposure.
Inspect UI only from those actual measurements; historical/fake data cannot substitute.
Publish the honest result and limits after independent review.
Native-price admission and rich measured visualization require their own next contract.
