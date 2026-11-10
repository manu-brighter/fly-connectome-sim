# Local Image Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Accept a bounded local upload, decode it through the accepted owner,
show only sanitized pixels to the operator and record explicit approval/rejection.

**Status:** Independently accepted prospectively with the
[exact intake contract](../specs/2026-11-10-image-intake-design.md).
D2 source/Windows review and all four source CI jobs passed. Task1 is in progress.

**Architecture:** One coordinator composes unchanged D1 lifecycle and D2 decoder;
the existing HTTP server gains optional image routes, followed by bounded guest/
operator UI. There is no neural worker in this slice: approval queues an image,
and the original deadline eventually expires it without any processed claim.

## Global Constraints

- Preserve D1/D2, package/frozen helpers/replay and dependencies. Extend the
  existing server/parser/assets and client patterns narrowly; no second HTTP,
  lifecycle, decoder or price engine. Default synthetic mode remains unchanged.
- Exactly the spec's DTOs/routes/roles/body limits/error codes and capability
  rules. Only the raw upload route gets2MiB; old JSON routes stay8192 bytes.
- Shared existing clock; reservation5s, accepted decode10s, moderation60s and
  handoff300s remain original. No late callback or retry restarts any clock.
- One receiving-or-pending image, one asynchronous decoder task without a queue,
  one pending12288-byte canonical image, at most512 receipt capabilities and the
  three fixed rate buckets. No unbounded sessions/attempt/error history.
- Guest upload capability cannot control prices/primary/moderation; receipt
  capability reads only its own status; original operator alone sees RGB/approves.
  Preserve exact Host/Origin/framing/deadlines/headers and no credential logging.
  Use structurally disjoint image-role prefixes retaining32 random bytes; preserve
  original price token generation, including future primary claims.
- No original image serving/browser preview, no fake processed/native activity,
  no new price source/schema or price action from image moderation/faults.
- Existing127.0.0.1 binding only, no LAN/public exposure/deployment/provider/native
  call or user photos. Generated safe fixtures and disposable test databases only.
- Callback generation, terminal state and image/hash identity are checked before
  adopting bytes. Shutdown cancels/joins and retains D2 ownership on unconfirmed
  cleanup; daemon exit is never successful application cleanup evidence.
- Sol owns sequential bounded tasks; Astra reviews source/integrity and the HTTP
  security boundary. Workers are not alone; preserve concurrent changes. Root owns
  documentation/Git. No worker child agents/Git/dependencies or scope expansion.
- Test first with actual RED/GREEN logs/exits. Python via .venv/Scripts/python.exe
  -m pytest, fresh --basetemp, -p no:cacheprovider; host approval for known Windows
  restrictions, genuine skips retained. Use existing viewer test/build commands.
- Inspect exact staged first-party files, preserve source/artifact identities and
  group reviewed local commits into an explicit feature push. All original CI
  jobs must pass before this local integration slice is marked complete.

## Task 1 — Bounded coordinator, pixels and capabilities

Ownership: create market/image_intake.py and tests/market/test_image_intake.py.
Consume unchanged AdmissionController/ImageDecoder/Clock APIs; produce the exact
ImageIntake methods and DTOs. No HTTP/browser/native integration in this task.

- [x] Capture accepted contract/plan and prior source/artifact identities.
- [ ] Write meaningful failing tests for reserve/body/admit timing, asynchronous
  completion, original phase boundaries, capability/pixel capacity/pruning,
  lost acceptance response semantics, normal decoder rejection versus fatal
  clock/ownership/integration errors, and no processed state without a worker.
- [ ] Implement one coordinator lock with documented fixed lock order; never
  hold it during decode/body/socket/join. Capture completion identity/generation,
  preserve D1's state authority and discard late bytes after expiry/stop.
- [ ] Test callback/maintenance/moderation races, one busy task even after D1
  pending release, status/preview identity and capability retirement, exact bucket
  boundaries, stop/join/cleanup failure and retained owner context. Include one
  actual owned D2 conversion of a generated safe fixture; doubles prove only logic.
  Test explicit public receipt-authentication/rate APIs without private-field
  access, auth failure with no bucket/state change, exactly-once role accounting,
  pruned tokens, clock-faulted diagnostics and closed-state HTTP outcomes. Include
  deterministic same-role collisions with bounded failure and cross-role/future
  primary separation; no authority token-generator changes.
  Exercise reserve_upload(guest_capability), atomic guest_status(id,status_capability),
  charge_operator(diagnostic) and uncharged operator_status/state/preview/moderate.
  Failed clocks spend only frozen remaining diagnostic credits, without refill,
  then return429; closed returns503. Test all four pre-admit mint attempts and
  release only the caller's reservation on collision exhaustion.
- [ ] Run focused tests and independent Astra spec/quality review; fix concrete
  findings with regressions and record the reviewed local checkpoint.

## Task 2 — Optional HTTP/CLI integration without price regressions

Ownership: market/local_server.py, scripts/run-market-price-service.py,
tests/market/test_image_intake_http.py and test_image_intake_process.py. Existing
test_price_http/process files change only for a justified shared regression.
Consume accepted Task1 and D2. Root owns docs and browser work.

- [ ] Write failing route/auth/body/timeout tests before optional-server changes.
  Cover disabled mode, all cross-role attempts, matching status capability,
  private preview, literal route grammar, auth/reserve before body, slow/oversize
  bodies, rate limits and sensitive response/request logging boundaries.
- [ ] Add only the optional collaborator, fixed raw route and route-specific role/
  length/MIME selection; preserve every original parser/header/price limit and
  overload/pause behavior. Extend reachable guest assets only when enabled.
  Authenticate image capabilities and account image rates through the accepted
  public coordinator interface; authenticate the original operator in the existing
  adapter. Operator versus receipt-reader access to one ID consumes the proper
  bucket once, without duplicated secret maps or client-selected roles. Validate
  ig./is. plus43-character suffixes as46-character image capabilities; original
  43-character price capabilities retain their existing generation/authentication.
- [ ] Wire explicit CLI --image-work-root, shared clock and ordered startup/failure
  cleanup. Test actual local HTTP→owned decode→preview→approval/expiry with safe
  fixtures, failed bind/startup, lost202/no automatic replay, shutdown during
  receive/decode and unconfirmed cleanup nonzero/retained ownership.
- [ ] Run focused/full Market regression with actual source hashes and honest
  Windows skips. Independent Astra security/protocol review checks the changed
  HTTP boundary and actual lifecycle evidence; resolve actionable findings.

## Task 3 — Guest upload and sanitized operator pane

Ownership: new market/web/image-{protocol,state,view,main}.ts,
viewer/market-image.html, viewer/src/market-image-entry.ts and matching
viewer/tests/image-* tests; narrow existing market operator entry/style and
viewer Vite/TS configuration edits. Coordinate any server integration defect with
Task2 ownership; do not silently widen its accepted authorization/body policy.

- [ ] Write failing strict wire/state tests for exact DTOs/enums/bounds, bounded
  stream reads, serial generations, fragment removal/credential memory, aborted
  or uncertain upload, status revocation, no automatic resubmission and stale
  controls. Reject processing/processed/live measurements in this slice.
- [ ] Add clear German guest guidance and a separate operator pane using existing
  visual patterns. Raw file bytes go to the sole upload route; only validated
  canonical RGB reaches the operator canvas after its hash check. Preserve
  independent price polling/ACK/control behavior and synthetic price labelling.
- [ ] Test exact canvas pixels, superseded preview suppression, original remaining
  time, explicit moderation retry identity and disabled-image404 behavior. Run
  focused then complete viewer suite/build, plus backend integration if modified.
  Approve requires current healthy/fresh awaiting-approval metadata and the exact
  verified-preview tuple already adopted into the canvas. Test delayed/failing/
  mismatched/superseded preview and stale metadata: none enables approve. Preview
  completion cannot refresh metadata age; clear the tuple on every invalidation.
  Reject may remain available without preview. Validate status/detail/frame
  combinations and requested identities; old moderation replies cannot replace
  another pending image.
- [ ] Root performs bounded real-browser verification against a disposable local
  service: guest upload/status, operator preview/approve/reject, unsupported/full/
  expired/error flows, offline/stale UI and unchanged price controls/layout. Use
  generated fixtures only; record actual results and limits, then close owned
  tabs/server/decoder and verify cleanup. No synthetic processed animation.
- [ ] Independent final Astra review covers this complete integration and concrete
  browser/process/security evidence. Fix findings, update handover/result/plan,
  verify preserved sources and exact staged diff, commit/push the feature and
  await all existing clean-checkout CI jobs.

## Remaining work

Completion proves only the local image path without a neural worker. Owned
continuous telemetry, real handoff/completion, explicit native price admission
and measured display follow separately. Event menu, sustained load, moderator
operation, sales use and public/LAN deployment remain later scoped decisions.
