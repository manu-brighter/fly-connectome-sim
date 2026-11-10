# Bounded native image worker — accepted prospective design

Status: independently accepted for bounded software implementation, 2026-11-10.
Actual acquisition remains behind the source, CI and concrete preflight gates below.
The accepted intake-only implementation is the prerequisite.
No native process, API call, guest photograph or external exposure ran for this draft.

## 1. Scope and completion boundary

Add one owned Windows native child to the existing local image coordinator.
It consumes approved canonical pixels through the existing D1 lifecycle.
It advances one continuous engine through images and explicit black input.
It produces bounded, source-bound measurements and genuine completion evidence.
The local UI distinguishes queued, start-announced, measured, completed and unknown.
Completion means eight validated 500-model-ms observations, not a price decision.

This slice has no native price ingress and no native readout adapter.
Keep PriceAuthority, synthetic fixtures and existing price behavior unchanged.
Do not send measurements through run_fixture or submit_synthetic.
The existing synthetic-price banner remains visible beside the native image pane.
The pane says “Lokaler neuronaler Bildtest — Preise weiterhin synthetisch”.
No learning, external DAN, LLM, sale activation, LAN/public server or deployment.
No new brain renderer, fabricated cell animation or measured-transmission claim.
No checkpoint restoration, worker replacement or automatic acquisition retry.

Engineering proof limits are not product duration or event-capacity requirements.
One explicit start permits at most 20 model seconds and 900 real seconds.
This does not qualify 6–8-hour or 12-hour events.
The user already accepts slower model time, quiet phases and favorites.
No new product decision is needed for this bounded integration proof.
The existing Pause/Fortsetzen controls affect synthetic prices only, never native advancement.
Native stop is terminal; the UI labels these two scopes explicitly.

## 2. Preservation and authoritative reuse

Preserve all 41 packaged simulator source members and 64 frozen helper sources.
Preserve locks, MIT notice, old parsers, recordings and negative evidence.
Do not edit D1, D2 or their Windows decoder owner for this integration.
Any proposed exception returns to independent design review before implementation.
Application code remains outside src/fly_connectome_sim.

Reuse FlyEngine.from_prepared_graph, identity and configure_cell_observer.
Source: src/fly_connectome_sim/engine.py:212,228,237,259.
Reuse build_header(identity, DATA), including its actual locked data join.
Source: src/fly_connectome_sim/experiment/cell_activity.py:96.
Reuse CellRing and export_observation; source scripts/market_live_buffers.py:51,127.
Do not reuse that helper's historical ImageAdmission alongside D1.
Do not use CellActivityWriter or enlarge replay collectors for live buffering.
Reuse D1 dispatch/started/complete/stop through their public methods.
Source: market/image_admission.py:416,462,490,513.
Reuse D2 exact canonical RGB bytes and preprocessing identity.
Source: market/image_decode.py:86,279.
Readout helpers remain unchanged and unconnected in this slice.
The complete measured motor bins support a later separately reviewed adapter.

The fixed benchmark runners provide arithmetic/ownership references only.
Their fixed schedule and protocol validators are not arbitrary-image APIs.
Reference scripts/run-live-buffer-performance.py:132,218,255.
Reference scripts/run-continuous-motor-probe.py:167,196.
Write one bounded application validator; do not copy a second simulator.

## 3. Exact file ownership

New market/native_protocol.py:
strict IPC codecs, declarations, measurement validation and finite evidence reader.
New market/native_windows.py:
one owned native child, exact-handle IPC and resource monitoring.
New market/native_worker.py:
worker state machine composing unchanged engine/header/CellRing APIs.
New market/native_session.py:
parent owner, evidence persistence and public coordinator-facing session API.
New scripts/run-market-native-service.py:
explicit preflight/start/inspect entrypoint; no import-time native initialization.
Modify market/image_intake.py:
optional native-session integration, v2 DTOs and bounded active pixel ownership.
Modify market/local_server.py:
optional native state route and existing-image transport version dispatch.
New market/web/native-protocol.ts and market/web/native-state.ts:
strict v2 DTO parsing, freshness and image/measurement identity adoption.
Modify market/web/image-{protocol,state,main,view}.ts only after their accepted checkpoint.
Modify operator render/main minimally for native status and seven measured totals.
Preserve market/price_service.py, fixtures.py and existing price client state.
Preserve scripts/run-market-price-service.py and standalone intake startup.

Tests mirror ownership under tests/market and viewer/tests.
Add one scoped native-worker CI selection without removing existing coverage.
Tracked prospective documents/evidence/handover are controller-owned.
Private drafts do not enter Git.

## 4. Public application interfaces

NativeSession(config: NativeConfig, clock: Clock):
constructor validates declarations only; it launches nothing.
prepare() -> PreparedNative:
read/hash only an already matching source/runtime/native cache; no engine/compiler/build.
Missing/mismatched cache is a prerequisite failure; separate build work is not authorized.
start(prepared: PreparedNative, allow_native_run: bool) -> None:
requires literal True plus exact current prepared identity; one attempt only.
snapshot() -> NativeSnapshot:
detached bounded state, no process/file object leakage.
next_offer() -> Boundary | None:
returns the sole validated waiting observation boundary, never a queued history.
advance(boundary_id: int, permit: DispatchPermit | None, rgb: bytes | None) -> None:
one consumption of that boundary; exact 12288 bytes iff permit supplied.
poll() -> tuple[NativeNotice, ...]:
drains at most eight notices; caller must consume before requesting more.
reserve_receipts() -> ReceiptTicket | None: nonblocking reservation for three receipt changes.
publish_receipts(ticket, entries) -> None: nonblocking exact tuple of0..3 ReceiptEntry.
receipt_progress() -> ReceiptProgress: acknowledged durable ticket/watermark or fault.
finish_receipts() -> None: closes submission after terminal reconciliation; drain is asynchronous.
The normative R3 capture/outbox protocol is Appendix C; no D1 private API is used.
begin_stop(reason: closed enum) -> None:
idempotently fence commands and request termination.
finish_close() -> CleanupReceipt:
confirm exact child exit and empty owned Job, otherwise retain handles and fail.

NativeConfig has exact fields:
incarnation UUID; worker_session UUID; protocol_sha256 digest; work_root Path.
All resource constants below are fixed by this protocol, not arbitrary kwargs.
PreparedNative contains protocol digest and bounded immutable launch bindings.
NativeSession methods serialize under its lock and never invoke ImageIntake.
No intake lock is held while blocking on IO, child work, joins or cleanup.
Session snapshot/poll are nonblocking bounded copies.

ImageIntake constructor gains keyword native_session: NativeSession | None = None.
None retains exact intake-only v1 behavior and output schemas.
A supplied session is bound to the same controller incarnation and Clock.
The coordinator alone owns D1 transitions, capabilities and all image pixels.
The session owns process/IPC/evidence and receives only permitted canonical bytes.
No component reads the other's private attributes.
Boundary delivery cannot create an additional admitted-image queue.

Native notices: ready, boundary, start, observation, complete, ended, fault.
Each notice has worker_session, incarnation, protocol digest and contiguous index.
Their concrete payloads are defined below; arbitrary dictionaries are rejected.
The coordinator validates notice identity and applies D1 via existing public APIs.
Native faults stop D1 with worker_failed or worker_outcome_unknown as appropriate.
The price authority is not called by any native module.

## 5. Finite constants and rationale

Model observation = 500 ms = 5000 ticks; tick = 0.1 ms.
Run allowance = 40 observations = 20000 model ms.
Image exposure = eight observations = 4000 model ms, as accepted by D1.
Total owned-run wall deadline = release time +900000000000 ns.
Startup/readiness deadline = release time +180000000000 ns.
One observation compute deadline = call time +30000000000 ns.
Parent boundary/ACK deadline = message-ready time +5000000000 ns.
One framed write/read-progress operation deadline =5000000000 ns.
Stop/cleanup application wait allowance =25000000000 ns.
Monitor cadence target =100 ms; gap >=2 s is a monitor fault.
Native Job commit quota =4 GiB; sampled RSS stop threshold =4 GiB, not a hard RSS cap.
Permit only worker plus one exactly bound startup zig-version probe; other descendants fault.
Combined new native output/evidence/scratch ceiling =256 MiB.
Native evidence files additionally have a combined64 MiB ceiling.
Captured diagnostic stderr ceiling =65536 bytes; excess faults.
No unbounded log files, stdout debug prints or rejected-request logs.

Prior60-model-second evidence used477.704 real seconds and944357376B peak worker RSS.
A20-model-second proof is deliberately smaller; proportional runtime is not promised.
30-second observation and180-second startup limits are conservative engineering guards.
They are not measured worst-case guarantees; failure remains a valid negative outcome.
D1 original10-second start receipt and300-second handoff deadlines stay unchanged.
Model allowance exhaustion ends this session; it never silently extends it.

## 6. Source-bound startup and ownership

Preflight writes a fresh exclusive directory containing protocol.json and bindings.json.
Never resume, overwrite or automatically retry a previous directory.
Bind raw application/helper/package sources, schema/lock bytes and configuration.
Bind actual interpreter executable, version, environment inputs and native library digest.
Bind actual compiler/cache provenance using existing source-binding principles.
Prepare never builds or executes a compiler. A missing cache ends preparation.
Any necessary build needs a separately bounded authorization outside this slice.
The unchanged build_native necessarily executes one pinned zig.exe version probe.
Allow that real probe once, hidden, inside the same Job/startup/wall/resource budgets.
Appendix B fixes argv, output, deadline, identity and guard; all builds remain forbidden.
Prepared runtime arrays/annotation identities must match preserved locks.

Parent creates a fresh UUID worker session and random256-bit launch nonce.
Launch the real interpreter suspended, in the owned Job from process creation.
Use a restricted inherited-handle list, detached/hidden process and trusted cwd.
Hold exact process handle and creation identity; never reopen by a recycled PID.
Only private stdin/stdout IPC and bounded stderr handles cross into the child.
No public socket, environment secret or guest/operator capability enters the child.
Child gets the prepared digest, nonce and clock description through initial private IPC.
Require matching source/bindings before importing/constructing the engine.
Parent also verifies prepared bytes immediately before release.
Child creates exactly one engine with the external version-probe guard active,
checks zero model clock and obtains locked identity. The returned native build identity
must exactly equal the prepared cache metadata plus the preserved model name.
Child calls build_header and fixes the256-cell cohort once before advancement.
Child sends static header and readiness; parent verifies both before releasing observe0.
No upload is accepted in native mode until this readiness gate passes.

Reuse existing WindowsProcess/WindowsJob primitives through fixed verified module paths.
Do not alter frozen Win32 signatures; use private DLL function objects for new calls.
D2 OwnedChild is a reference, not a base class or native launch escape hatch.
Unrelated processes and D2 ownership are never terminated by native cleanup.
Readiness is local source/ownership bookkeeping, not scientific qualification.

## 7. Clock contract

Use market.price_service.SystemClock, based on perf_counter_ns, on both processes.
Require monotonic=true, adjustable=false, resolution <=1 ms and identical implementation.
All native/intake deadlines use this shared-host domain, not time.monotonic on Python3.12.
Do not use UTC, browser time or model ticks to extend a real deadline.
Reject bool, float, negative, overflow or regressing nanoseconds.
Native nanoseconds are exact integers0..2**63-1 in private IPC.
Browser messages contain only bounded integer millisecond ages/durations.

Perform three sequential clock challenges before engine construction.
For each, parent samples p0, sends nonce, child samples c and replies, parent samples p1.
Require p0<=c<=p1 and p1-p0<2 seconds, and strictly bound challenge order/nonce.
Retain the exact brackets and both clock descriptions in startup evidence.
This is a same-host compatibility check, not independent time attestation.
Check each worker timestamp <=parent receipt time and monotonic lifecycle ordering.
A clock fault latches for the incarnation; no substitution or clock reset.
Quantization is explicit when deriving decoder-compatible milliseconds later.

## 8. IPC framing and finite backpressure

Every frame is uint32 little-endian body_length followed by exactly that body.
Body = uint32 little-endian json_length + canonical UTF-8 JSON + optional binary bytes.
Reject zero, overflow or declared lengths exceeding type-specific caps before allocation.
JSON rejects duplicate keys, nonfinite numbers, invalid UTF-8, unknown/missing fields.
Require exact built-in primitive types and bounded nesting/collection sizes.
Canonical encoding uses sorted keys, compact separators and no NaN.
Read fixed bounded chunks; incomplete/trailing frames at EOF are protocol faults.
Every direction has its own seq starting0 and increasing exactly by1.
Every message includes schema="market-native-ipc/v1", type, seq, incarnation,
worker_session, protocol_sha256 and launch_nonce.
No sender-controlled paths, class names, callback code or pickle are accepted.

Message types and maximum bodies:
hello/clock/challenge/initialize/release/ack/start/complete/ended/fault,
probe_request/probe_allow/probe_started/probe_finished:4096 bytes.
Exception ack(action=image):16384 bytes, including exactly12288 binary RGB bytes.
observation:32768 bytes, including exactly12800 binary cell-count bytes.
static_header:2097152 bytes, JSON only, exactly once.
ready:8192 bytes, JSON only, exactly once.
Parent reader has at most one partial frame and one complete unprocessed frame.
Child reader has at most one command; no image/command backlog.
A header oversize faults; it cannot trigger an automatic cap increase.

Ordinary observation: child sends one observation frame, then waits for one ack.
Image ordinal7 is the exception: send observation7 and complete consecutively,
without waiting for any intervening command; only then await one ack/end.
Its single exchange timer starts immediately before the observation7 frame write;
both writes and the one returned command must finish within five seconds.
Ordinary exchanges use the same epoch before their sole observation write.
Parent validates and persists it before acknowledging the next boundary.
Only a replaceable bounded browser snapshot may be dropped.
Lifecycle/evidence messages are never overwritten or silently dropped.
A blocked/late ack stops the session; it cannot cause unbounded telemetry accumulation.
Parent never acknowledges a native observation before complete validation.
Start and complete messages are ordered relative to observation frames.
After image ordinal7, parent persists both frames, captures/persists accepted D1.complete,
then exposes one boundary. At observation39 that command is end; child sends ended,
closes stdout and exits0. EOF before ended or extra observations/commands are faults.
No new observation begins while the previous one is awaiting ack.

The initial release is boundary0; later ack carries next boundary index.
Ack fields: last_observation_index, next_observation_index, action.
action is black, image, continue_image or end.
image also carries the exact D1 permit and12288 canonical bytes.
continue_image carries the matching dispatch_id and next exposure ordinal.
black contains no image identity or pixels; child uses its fixed explicit black array.
end contains no next observation and is terminal.
No command grants more than one next observation.

## 9. Scheduling, original TTL and real completion

Parent offers an approved queued image only when no active image exists.
Dispatch only at a held validated boundary, never during native computation.
A new4s image requires at least eight remaining observations.
At boundary indices33..39, no new image dispatch is permitted.
At index40, end the session immediately without any extra black observation.
While active, all eight observations must be consecutive and use the same pixels.
Between images/when empty, black observations advance normally without waiting for uploads.

Before D1.dispatch, resynchronize maintenance and check the actual remaining budget.
Dispatch preserves original accepted deadline; no new upload/approval/IPC deadline.
D1 dispatch reserves no second pending queue; its own item remains dispatching.
Copy the exact approved hash/bytes under coordinator lock, then send outside that lock.
Child validates permit/session/incarnation/hash and recomputes the RGB digest.
Hash uses the existing rgb-input/v1 prefix plus logical64×64 RGB bytes.
At worker_now>=permit.deadline_ns, do not call observe; stop with unknown dispatch outcome.
No attempted late handoff can be retried under a new permit for the same accepted image.

Start ordering requires special precision:
sample started_ns immediately before transmitting the start announcement;
transmit that fixed receipt before calling observe;
after transmission, resample first_call_ns and recheck the original deadline;
call observe immediately with no further IO or admission work between check and call.
Require started_ns<=first_call_ns<deadline_ns for a confirmed first observation.
If transmission stalls, deadline passes or call never completes, no processed result.
The first observation frame includes first_call_ns and the complete start tuple.
This separates announced start from subsequently evidenced actual invocation.
D1 StartReceipt alone remains an unverified worker assertion, never proof of a bin.
Independent protocol review must explicitly accept this timestamp refinement:
pre-observe emission cannot atomically prove a later function actually entered.
Do not falsely label started_ns an exact first-kernel-instruction timestamp.
Neither wrapper timestamp attests the first C++ step: the unchanged core has no such hook.
Arbitrary OS interruption after the last check cannot be excluded by this wrapper.
The enforced limit is timely host dispatch/check; no stronger physical-entry guarantee.
This limitation is an explicit independent-review point, not a fabricated native clock.

Parent passes the start assertion to D1.started before accepting observation evidence.
Its10-second dispatch-to-receipt budget and contradiction precedence remain unchanged.
A late start receipt may be valid only under D1's original documented conditions.
On image ordinal7, child sends complete only after sending observation7.
Parent calls D1.complete only after all eight observations are validated and persisted.
CompletionReceipt has exact first_index..first_index+7 and actual completion_ns.
Completed exposure is valid even if300s has passed after its timely start.
No native result/price/proposal is required to mark that exposure processed.
No partial exposure can become processed on shutdown, retry or UI timeout.

Before native-mode reserve/admit, parent checks ready/running state and remaining capacity.
Available allowance =40-issued_observations-unissued_active_exposure_observations.
Issued includes an in-flight native call or outstanding command, not merely completed data.
Appendix D freezes boundary/in-flight transitions so active time is counted exactly once.
Refuse new upload reservations if that unreserved allowance is less than eight.
A reservation does not promise a future4s exposure; progress may consume that allowance.
Recheck at admit; if budget closed before admit, release only that reservation and503 stopping.
An already accepted image not dispatched by session end becomes rejected/session_ended.
At end, D1.stop(session_ended) preserves completed/terminal history and confirmed start fields.
New session requires new process/controller incarnation and explicit user start.
Never inherit pending images, capabilities, native state or partial paths across it.

## 10. Measurement schema and verification

Observation JSON fields, beyond common envelope:
observation_index, input_kind, image_id, dispatch_id, exposure_ordinal,
frame_sha256, engine_identity_sha256, header_sha256,
start_tick, end_tick, wall_start_ns, wall_completion_ns,
learning, stimulation, pathway_detail, qualification_detail,
group_spikes, group_rates_hz, group_bin_counts, total_spikes,
compute_seconds, kernel_seconds, cell_bytes_sha256.
All observations also contain start_receipt and first_call_ns fields.
Both are null for black and image ordinals1..7; ordinal0 requires the complete
D1 StartReceipt object and first_call_ns. Appendix A fixes exact fields.
image_id/dispatch_id/exposure_ordinal are null for black.
Group order is pam11,ppl101,kc,mbon07,mbon11,motor_left,motor_right.
group_bin_counts is exactly50 rows×7 integer counts.
Binary payload is row-major50×256 uint8 original cell counts, no compression.
Parent reconstructs exact bin ticks from observation index and ordinal.

Validate contiguous zero-based observations and exact5000-tick spans.
Validate fifty100-tick bins, nonnegative counts and per-population population×100 bounds.
Validate group totals equal all original bins and rates equal total/(population×0.5s).
Rate comparison uses math.isclose(rel_tol=1e-9,abs_tol=1e-9), matching the frozen runner.
The worker validates native bins/input shape/dtype/hash before constructing this DTO.
Detail flags describe checked call arguments, not extra fields invented inside native telemetry.
Validate whole-brain total bounds using overlap-aware population unions:
never sum overlapping groups as though disjoint.
Validate mandatory cohort sums equal each corresponding complete-group bin.
Sampled KC cohort sums must not exceed the whole KC group bin.
Every cell count is0..100; original bytes/digest must match.
Validate engine/header/frame identity and declared no-learning/no-stimulation flags.
Validate wall_start<=wall_completion<=receipt and nondecreasing call order.
Validate finite nonnegative compute/kernel durations; they are declared measurements.
No guessed physiological rate cutoff, rearm threshold or favorable-result requirement.

Parent creates five completed100-ms cell windows by integer aggregation.
Raw bins, group totals and windows cannot be replaced by browser interpolation.
The latest browser payload shows seven whole500-ms group totals/rates only.
Cell counts/static header remain bounded inspectable evidence for later rendering.
Static edges do not imply measured transmission.
Any malformed observation faults the session before ack/complete.
A callback/native exception may follow partial advancement: never retry observe.

## 11. Evidence, memory and retention

Child owns one CellRing (288000 array bytes), one current export and one active RGB.
No parent mirror of the full ring is required.
Parent retains one latest validated observation and one active eight-index ledger.
Coordinator owns at most pending RGB, active RGB and one last-measured RGB.
Each RGB is12288 bytes; ownership transitions are explicit, no history list.
Last-measured RGB is replaced only with a validated observation's matching input.
Black clears the last-measured image; session stop revokes new image fetches.
Do not expose the pending approval preview as the actually measured image.

Parent exclusively creates protocol.json, bindings.json, header.json, events.bin,
monitor.bin, cleanup.json and final.json; failure.json is optional on incomplete runs.
events.bin is framed accepted input/start/observation/completion/end evidence.
Persist every D1 receipt transition once by(id,revision); max4096 total records.
Strip launch_nonce and credentials from evidence envelopes; preserve source/session/seq.
Each accepted record has prior-record SHA256, current SHA256 and bounded sequence.
Retain canonical inputs once per dispatch, not once per observation.
Maximum observations40, dispatches5, inputs5, start/completion pairs5.
Failed/partial journals stay explicitly incomplete. Valid EOF alone never permits final.json.
Appendix F requires terminal protocol, drained receipt outbox, confirmed worker/probe exit,
empty Job, handle/root-lock release and durable evidence-file closure before sealing.
Cap events.bin32 MiB/4096 records, monitor.bin24 MiB/12000 records and all evidence64 MiB.
Monitor records have their own counter; they never consume the4096 lifecycle allowance.
Fsync bounded causal event records before ack; preserve sampled monitoring limits honestly.
Slow/full storage faults; never claim guaranteed durability after failed sync.
No arbitrary exception payloads, tokens, filenames or raw uploads enter evidence.
Evidence retention is local per explicitly owned proof directory, never automatic public retention.

Offline inspect verifies bounded full EOF, exact hashes, sources, clocks and all arithmetic.
It imports no engine, starts no process/network and never updates source artifacts.
Its label is integrity-only; source binding is not replay attestation or scientific support.
No old session/replay parser is used to approve this journal.

## 12. HTTP and minimal UI versioning

Standalone intake retains market-image-status-wire/v1 and market-image-intake/v1 exactly.
Native-enabled mode uses market-image-status-wire/v2 and market-image-intake/v2.
Its202 envelope is market-image-acceptance/v2 containing exactly status_capability and v2 image.
Standalone v1 acceptance/parser dispatch remains unchanged; Appendix E fixes all variants.
Shared fields retain meaning; v2 adds processing/processed and documented D1 details.
v2 details include dispatching,processing,completed,worker_outcome_unknown.
Use D1 revision1..6; network polls do not increment it.
v2 status adds worker_session, first_observation_index, completed_observations0..8,
and observation_revision0..40; D1 revision remains separate from measurement progress.
worker_session/index are null before dispatch/start respectively; count/revision start0.
processing requires confirmed D1 start; processed requires count8 and completed detail.
queued/dispatching is permitted, with preview_available=false; accepted/queued-ready
retain v1 preview rules; processing/processed/terminal always have preview_available=false.
worker_outcome_unknown is rejected, retains confirmed measurement fields, and never revives.
v2 intake retains v1 fields and adds active:ImageStatusV2|null and native_state enum.
mode is bounded-native-test; worker_connected is true only after readiness until stop.
Native stopping/ended/faulted disables new images; v2 fault adds native_worker to v1 enum.
Pending/active must match incarnation and worker binding where one is established.
Only independently validated measurements increment completed_observations.
Started-but-unmeasured processing shows0, never an invented first result.
Terminal failures preserve confirmed indices/counts, with unknown outcome copy where needed.

GET /api/native/state exists only in native mode; otherwise404.
Authorize with existing operator/view/primary role checks, never guest upload/status tokens.
Reuse operator image-request bucket for operator calls; fixed global read bucket capacity120/refill2 tokens per second
for view/primary native reads, with no per-client allocation.
Clock-fault diagnostics spend frozen remaining credits without refill, as in intake.
Response <=16384 bytes, exact schema market-native-state/v1.
Required fields beyond schema: incarnation,worker_session,mode="bounded-native-test",state,
fault,model_ms,model_limit_ms,observations_completed,measurement_age_ms,
input_kind,image_id,frame_sha256,group_spikes,group_rates_hz,time_uncertain.
state: starting,running,stopping,ended,faulted; null measurements before first validated output.
input_kind/image_id/frame_sha256 always describe the last validated measurement,
not the currently announced/in-flight input or the pending approval preview.
Fault is a closed documented worker enum; no arbitrary diagnostic string.
No absolute ns, credentials, source filenames or raw evidence enter browser DTOs.
No native image/public preview endpoint is added in this slice.
Existing private moderation preview remains separate.

Poll native state every2s, serially, with5s abort and bounded streaming reads.
Native UI has independent request state and never blocks price polls/ACK/actions.
Transport stale>=5s: disable image mutations and show “Verbindung unklar”.
Measurement age>=10s: retain dated counts, mark stale, stop any activity indication.
Browser receipt time never refreshes measurement age to zero.
Advance age from server value using browser performance.now until next reply.
Clock uncertainty gives null ages, explicit unknown and no live claim.
Hide/clear current state on incarnation/session change; suppress old async responses.
No animation substitutes for absent/stale measurements.
Display model20s proof limit separately from real elapsed/measurement age.
Guest v2 status says “8/8 Modellintervalle verarbeitet”, never price change promised.

## 13. Faults, stop and independently gated acceptance

Closed native fault codes: startup,source,clock,protocol,deadline,resource,
ownership,storage,journal_gap,worker_failed,worker_outcome_unknown,cleanup_failed.
First cause latches; later cleanup failure is retained separately, never overwrites history.
Native fault cancels admission and its D2 task through the coordinator's existing stop path.
Price service remains responsive and synthetic; no native fault fabricates a price proposal.
Normal model-limit end preserves existing price service and terminal image diagnostics.
Shutdown fences intake first, signals native stop, then joins/cleans native and D2 separately.
Keep exact handles/root lock on unconfirmed cleanup; return nonzero, never success.
Job owner death must terminate child; verified cleanup receipt requires empty Job/exited handle.
No PID-wide kill, taskkill pattern or unrelated-process cleanup.

Gate0: independent architecture/protocol review before first-party implementation.
Resolve start timestamp refinement, exact shape variants and preservation list explicitly.
Gate1: offline unit tests with injected engine and Clock only; no native import/start.
Gate2: real Windows harmless-child lifecycle/IPC tests; no simulator/runtime access.
Gate3: independent source/security/integrity review plus exact source CI and preservation.
Gate4: concrete finite native preflight; independent review of actual prepared bindings.
Gate5: one separately released actual local acquisition, then independent full evidence review.
A failed/negative gate does not authorize retry, more model time or threshold changes.
A synthetic success never satisfies Gate5.

Gate5 protocol uses exactly the40-observation allowance and generated PNG fixtures only.
Submit/approve A after readiness. Attempt B once only after BOTH A's confirmed start
and at least10 real seconds after the successful A202 response; no guest photographs.
The extra10s preserves the existing guest bucket without rate changes or retry.
Freeze A/B bytes and scripted submission/moderation actions before launch.
Record all black intervals, all accepted/rejected uploads and actual latency.
Require at least one genuine8-observation processed image for positive integration acceptance.
Require a second timely exposure only if its frozen submission was accepted with sufficient budget.
Preserve failures/expiry honestly; do not extend the session to obtain a second result.
The protocol review fixes fixture interaction timing before execution.
No drink/price diversity, preferred signal or successful price activation is a gate.
Report actual processes/RSS/disk/cleanup, model/wall clocks and all receipt outcomes.
Public security, sustained event operation and native price admission remain later slices.

## Appendix A — normative types, frames and bounded parsing (R4)

This appendix is normative; omitted or extra keys are errors. No wire schema is
left to implementer discretion. Internal frozen records have the same field sets,
with tuple replacing JSON arrays and immutable copies on every public return.

Notation: I[a,b] is exact int (not bool); N=I[0,2**63-1]; U64=I[0,2**64-1];
J=I[0,2**53-1]; B=exact bool; D=64 lowercase hex; UUID=canonical lowercase UUID;
T[k]=exact Unicode str of at most k characters, no surrogates; ?X=X|null.
All strings also fit their containing byte cap. A closed literal is exact str.
C(x)=json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,
allow_nan=False).encode("utf-8"). H(x)=SHA256(C(x)); byte hashes hash exact bytes.
Depth<=12 including root, object keys<=128 except frozen source maps<=128;
array<=5000 except explicit shapes below. Parse byte/depth/node budgets before
constructing Python containers: <=40000 JSON value/key nodes for static_header,
<=20000 for bindings/protocol and <=8192 for other IPC/event/HTTP messages.
Read at most65536 bytes per OS operation; hash files in <=1MiB chunks.
Text, header and aggregate byte caps always take precedence over node limits.

ClockDescription={implementation:T[128],monotonic:true,adjustable:false,
resolution_ns:I[1,1000000]}; parent and child descriptions must be equal.
ProcessIdentity={pid:I[1,2**32-1],creation_time_100ns:U64,
executable:T[1024],executable_sha256:D}. Match held handle, path and creation time.
The first hello fixes the otherwise private launch_nonce D; only inherited private
pipes carry it. Parent has bound child identity before release; this is not
authentication against a malicious local administrator or native binary attestation.

Envelope E has exactly schema:"market-native-ipc/v1",type:T[32],seq:I[0,4095],
incarnation:UUID,worker_session:UUID,protocol_sha256:D,launch_nonce:D.
A frame adds ONLY the keys in its row. Binary is empty except the two named variants.
Each endpoint rejects a frame not legal in the current transition state.

| Direction/type | Additional exact fields |
|---|---|
| P->W hello | bindings_sha256:D,parent_clock:ClockDescription |
| W->P hello | bindings_sha256:D,worker:ProcessIdentity,worker_clock:ClockDescription |
| P->W challenge | challenge_index:I[0,2],p0_ns:N |
| W->P clock | challenge_index:I[0,2],p0_ns:N,child_ns:N |
| P->W initialize | bindings_sha256:D |
| W->P probe_request | compiler_sha256:D,argv_sha256:D,environment_sha256:D |
| P->W probe_allow | request_seq:I[0,4095],allowed_ns:N |
| W->P probe_started | process:ProcessIdentity,allowed_ns:N,started_ns:N |
| W->P probe_finished | process:ProcessIdentity,started_ns:N,completed_ns:N,exit_code:0,stdout_bytes:I[7,8],stderr_bytes:0,stdout_sha256:D,stderr_sha256:D,version:"0.16.0" |
| W->P static_header | header:Header |
| W->P ready | bindings_sha256:D,header_sha256:D,engine_identity_sha256:D,build_sha256:D,graph_nodes:166700,graph_edges:25582938,observation_index:0,model_tick:0,ready_ns:N |
| P->W release or ack | last_observation_index:?I[0,39],next_observation_index:?I[0,39],action:"black"|"image"|"continue_image"|"end",permit:?Permit,dispatch_id:?UUID,exposure_ordinal:?I[0,7] |
| W->P start | receipt:Start |
| W->P observation | Observation fields below |
| W->P complete | receipt:Complete |
| P->W stop | reason:"operator"|"session_fault"|"shutdown" |
| W->P ended | reason:"model_limit"|"cancelled"|"fault",observations_completed:I[0,40],last_observation_index:?I[0,39],last_tick:I[0,200000],wall_ns:?N,header_sha256:?D,engine_identity_sha256:?D,fault:?Fault |
| W->P fault | code:Fault,phase:"bootstrap"|"probe"|"startup"|"observe"|"delivery"|"shutdown",observation_index:?I[0,39],dispatch_id:?UUID,wall_ns:?N,observations_completed:I[0,40] |

Fault is exactly the closed code list in section13, now including journal_gap.
Null clock allowed only after latched clock failure; no fictional timestamp.
Ended model_limit requires40 observations, last index39, tick200000, valid hashes,
non-null time and fault=null. Cancelled requires fault=null, fault reason requires
nonnull fault. Before header, its two hashes are null together; afterward both match.
For n completed, last index is null iff n=0, otherwise n-1, and last_tick=n*5000.
A fatal protocol may close without ended; that is incomplete, not normal EOF.

Permit has exactly D1 DispatchPermit fields:
{id:UUID,incarnation:UUID,dispatch_id:UUID,worker_session:UUID,
frame_sha256:D,deadline_ns:N,exposure_observations:8}.
Start has exactly {id,incarnation,dispatch_id,worker_session:UUID,
frame_sha256:D,started_ns:N,first_observation_index:I[0,32]}.
Complete has exactly {id,incarnation,dispatch_id,worker_session:UUID,
frame_sha256:D,observation_indices:array[8] of I[0,39],completed_ns:N}.
All identity tuples match the permit and D1; indices are first..first+7.

Command combinations are exhaustive:
release has last=null,next=0,action=black, all permit/dispatch/ordinal null.
It cannot carry an image; uploads are admitted only after this release.
ack black has last=n,next=n+1, n<39, no permit/dispatch/ordinal.
ack image has last=n,next=n+1<=32, permit nonnull, matching dispatch_id,
exposure_ordinal=0 and exactly12288 binary bytes; no other command has binary.
ack continue_image has last=n,next=n+1<=39, permit=null,
matching active dispatch_id and ordinal1..7.
ack end has last=39,next=null,action=end and all other fields null.
No empty ack or duplicate command exists. Early cancellation uses stop, not end.

Observation adds exactly:
observation_index:I[0,39],input_kind:"black"|"image",image_id:?UUID,
dispatch_id:?UUID,exposure_ordinal:?I[0,7],frame_sha256:D,
engine_identity_sha256:D,header_sha256:D,start_tick:I[0,195000],
end_tick:I[5000,200000],wall_start_ns:N,wall_completion_ns:N,
learning:false,stimulation:null,pathway_detail:false,qualification_detail:false,
group_spikes:GroupCounts,group_rates_hz:GroupRates,
group_bin_counts:array[50] of array[7] of I[0,16670000],
total_spikes:I[0,833500000],compute_seconds:finite number[0,900],
kernel_seconds:finite number[0,900],cell_bytes_sha256:D,
start_receipt:?Start,first_call_ns:?N.
GroupCounts has exactly the seven fixed group keys with I[0,833500000] values.
GroupRates has those keys with finite numbers0..10000 (bool forbidden).
Header population-specific count/rate bounds further restrict them.
Binary has exactly12800 bytes, row-major50 bins×256 cells, each byte<=100.
start_tick=index*5000; end_tick=(index+1)*5000.
Black: image_id,dispatch_id,ordinal,start_receipt,first_call all null,
and frame hash equals explicit black64 hash.
Image: IDs match active permit; ordinal0 has exact matching Start and
first_call_ns=wall_start_ns with started_ns<=first_call_ns<permit.deadline_ns.
Ordinals1..7 have start_receipt/first_call null and wall_start>=prior completion.
Input hash never comes from a UI declaration or black fallback substitution.
RGB hash=SHA256(C({version:"rgb-input/v1",dtype:"uint8",rank:3,shape:[64,64,3]})
+ LF +12288 logical RGB bytes), matching unchanged engine convention.

Transport state and deadlines:
P hello/W hello; three challenge/clock pairs0,1,2; initialize; exactly one
probe request/allow/started/finished; static_header; ready; release; observations.
Each challenge begins at p0 and ends at p1, under2s.
Startup silence until expected header/ready is governed by180s startup/900s wall,
not an indiscriminate5s idle pipe deadline. Probe has its own deadline in Appendix B.
Before an issued observe, parent records issued_ns and permits up to30s compute
plus5s result transmission; child checks its own30s from wall_start.
Once first frame-length byte arrives, the entire frame must arrive within5s.
Read progress never renews this total in-frame deadline.
At a completed observation boundary the child starts exchange_ns immediately
before the first observation-frame write. Write(s) plus returned ack/end must
complete by exchange_ns+5s, including both ordinal7 frames.
Parent uses wall_completion_ns+5s as a conservative ack deadline, never a later
receive timestamp; earlier expiry fails closed.
No message-ready epoch is guessed from a partial parse.
At observation39: observation(+complete if ordinal7), one end, ended, clean EOF,
exit0. No extra black interval. Parent drains EOF before cleanup.
Malformed/partial/extra trailing frames cannot be normalized into clean EOF.

## Appendix B — source/cache/probe bindings (R1/R4)

prepare has a120s read/hash deadline and no child/engine/library load.
Sources are read with stat/open/fstat/end-stat identity checks and bounded chunks.
No symlink/junction, changed inode/volume/file ID, changed bytes or escaping path.
Prepared paths are local absolute paths<=1024 chars, never UNC/network paths.
No arbitrary path is accepted from HTTP or child IPC.
Raw source member cap1MiB; all first-party source bytes cap16MiB.
Each executable/DLL cap512MiB; metadata/lock/config JSON cap1MiB.
Each declared runtime file cap4GiB; combined runtime files cap8GiB.
Bindings/protocol file cap1MiB each; header cap2MiB; no source auto-addition.
Read/hash existing runtime bytes only; prepare constructs no arrays or graph.

FileBinding={path:T[1024],bytes:I[0,4294967296],sha256:D,
device:U64,file_id:U64,mtime_ns:N}. Type-specific cap also applies.
Bindings={schema:"market-native-bindings/v1",protocol_sha256:D,
incarnation:UUID,worker_session:UUID,project_root:T[1024],work_root:T[1024],
decoder_work_root:T[1024],runtime_root:T[1024],files:map[T[256],FileBinding],
environment:Environment,python_version:"3.12.14",compiler_probe:ProbeBinding,
native_metadata:NativeMetadata,dependencies:Dependencies,package_fingerprint:D,prepared_ns:N}.
Files<=128; keys are the exact source map below plus the named runtime/tool bindings.
Absolute paths are identity evidence in this private file, never browser output.
PreparedNative={schema:"market-native-prepared/v1",protocol_sha256:D,
bindings_sha256:D,incarnation:UUID,worker_session:UUID}; no arbitrary object fields.

Protocol={schema:"market-native-protocol/v1",proof:"bounded-image20s/v1",
constants:Constants,preserved_sources:map[T[256],D],application_sources:map[T[256],D],
lock_sources:map[T[256],D],package_fingerprint:D}.
Constants exact keys/values:
model_observations:40,observation_ticks:5000,image_observations:8,
wall_ns:900000000000,startup_ns:180000000000,observe_ns:30000000000,
exchange_ns:5000000000,probe_ns:5000000000,cleanup_ns:25000000000,
monitor_period_ns:100000000,monitor_gap_ns:2000000000,
job_commit_bytes:4294967296,rss_stop_bytes:4294967296,
combined_output_bytes:268435456,evidence_bytes:67108864,
event_bytes:33554432,event_records:4096,monitor_bytes:25165824,
monitor_records:12000,receipt_batches:32,receipt_batch_bytes:8192.
Every constant is an exact integer, compared to this specification.

Application source map keys are exactly market/{__init__,fixtures,ownership,
price_service,local_server,image_admission,image_decode,image_decode_windows,
image_intake,native_protocol,native_windows,native_worker,native_session}.py,
scripts/run-market-native-service.py and scripts/market-image-decode-worker.py.
The map is generated only after these reviewed files exist; no wildcard imports.
Lock map keys are src/fly_connectome_sim/neural/{arrays.lock,sources.lock,
neurons.lock,datasets}.json and src/fly_connectome_sim/schemas/run.schema.json.
Preserved map is exactly Appendix G; package fingerprint is
1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b.
Files additionally have exact tool keys python_launcher,python_config,worker_exe,
compiler_exe,native_library,native_metadata; and runtime keys graph,
normalized_neurons,annotations,neurotransmitters,edges.
Files additionally bind six dependency files: numpy_init,numpy_metadata,
pandas_init,pandas_metadata,pyarrow_init,pyarrow_metadata, as defined below.
Map paths must match fixed project/runtime/configured-real-interpreter locations.
Library is runtime/cache/physiology-v6/memory.dll; metadata is memory.dll.json.
All arrays/source/normalized-neuron checks in unchanged verify_prepared_graph remain.
No missing-file download, build, synthetic metadata or alternate simulator fallback.

Environment exact keys: SystemRoot,WINDIR,PATH,TMP,TEMP,PYTHONPATH,
PYTHONHASHSEED,PYTHONDONTWRITEBYTECODE,PYTHONNOUSERSITE,
FLY_CONNECTOME_SIM_DATA,FLY_CONNECTOME_SIM_CXX.
Each value T[8192], combined canonical bytes<=16384.
SystemRoot/WINDIR bind actual Windows root; PATH binds explicit required system/
interpreter directories, not a copied secret-bearing arbitrary user environment.
TMP/TEMP point to owned counted scratch; PYTHONPATH is exactly project root, src,
and project/.venv/Lib/site-packages, in that order, joined by Windows semicolons.
HASHSEED="0",DONTWRITEBYTECODE="1",NOUSERSITE="1"; DATA/CXX are bound absolute paths.
No inherited additional variables. Worker command is the real bound interpreter,
-B -s -S -m market.native_worker --protocol <fixed> --bindings <fixed>;
working directory is project_root; command and environment must match bindings.
No nonce/capability appears in argv, environment or persisted bindings.

Fixed dependency bootstrap, before any numerical/engine import:
Dependencies={site_packages:T[1024],numpy:"2.4.6",pandas:"3.0.5",
pyarrow:"25.0.1"}; site_packages is exactly project/.venv/Lib/site-packages.
Require that existing ordinary directory and package roots numpy,pandas,pyarrow;
no symlink/junction or path outside that venv. No installation or sys.path fallback.
Bind the existing pyvenv.cfg FileBinding and the actual base interpreter it names.
The six added FileBindings are each package's __init__.py and its exact
numpy-2.4.6.dist-info/METADATA, pandas-3.0.5.dist-info/METADATA,
pyarrow-25.0.1.dist-info/METADATA, all under the fixed site-packages root.
Apply1MiB per-file source/metadata caps and the existing16MiB aggregate source cap.
Prepare reads these bytes/metadata versions without importing dependencies.
The -S flag suppresses base/global site initialization and .pth execution;
-s suppresses user site. The already fixed PYTHONPATH supplies only the three
declared directories; bootstrap verifies these entries before numerical imports.
market.native_worker initially imports only stdlib/bootstrap-safe local modules.
Before importing numpy/pandas/pyarrow, inspect their resolved module specs and
any preloaded same-prefix modules: origins must lie in the corresponding fixed
venv package root and top-level origin must be the bound __init__.py.
After imports require actual __version__ equality and recheck loaded same-prefix
module origins (including extension modules) under their declared package root.
Reject missing, shadowed or wrong-origin modules, mismatched version/metadata or
unexpected base/user package resolution; do not launch a second venv interpreter.
Transitive imports use that same fixed venv path; no site/global/user fallback.
These bindings establish declared installed versions/origins, not a hash
attestation of every external dependency binary. The simulator DLL is untouched.
Bootstrap regression tests may import these existing dependencies but must not
construct an engine, graph or simulator DLL; private fixtures cover wrong paths.


NativeMetadata exact fields are source_sha256:D,compiler:"0.16.0",
flags:["-O3","-std=c++17","-shared","-Wl,--export-all-symbols"],
library:"memory.dll",binary_sha256:D.
Kernel source and binary hashes must equal FileBinding hashes.
ProbeBinding={executable_sha256:D,argv:array[2]T[1024],
environment_sha256:D,expected_version:"0.16.0",timeout_ns:5000000000,
stdout_limit:4096,stderr_limit:4096}; argv is [bound_zig_absolute_path,"version"].
No --version alternative, build command, repeated probe or other descendant.

External worker-only subprocess adapter wraps the actual build_native
subprocess.run call during engine construction; no packaged source changes.
It accepts only that exact argv and check=True,capture_output=True,text=True.
It executes the real pinned binary and returns its actual bounded CompletedProcess;
never invents/caches a version response or bypasses build_native's later cache test.
A persistent audit guard rejects every other process-start path/argv.
The adapter sends probe_request; parent verifies bindings and emits probe_allow.
After allow, exactly one temporary descendant may appear before probe_started.
It must be a direct child of the held worker, pinned executable/hash, created
within the allowed startup interval; at most worker+one probe may be in the Job.
Create probe hidden/NO_WINDOW, suspended, exact held handle and restricted pipe handles.
Verify inherited Job membership/creation identity; emit probe_started then resume.
Monitor allows this one provisional matching descendant, never arbitrary PID reuse.
Drain both output pipes concurrently, <=4096 bytes each; deadline5s from resume.
Only stdout b"0.16.0\n" or b"0.16.0\r\n", stderr empty and exit0 succeed.
Transmit probe_finished using real timestamps, lengths/hashes and retained identity.
Require held probe exit and disappearance from Job before readiness.
Parent independently matches process evidence, output hashes and the prior request.
Any subsequent compile attempt on cache mismatch is denied, not executed.

Rehash source/compiler/cache/metadata before release and immediately before
permitting the actual probe; recheck cache/source after build_native returns.
Compare engine.identity().model_provenance.build to actual unchanged build result
and prepared metadata plus model="stonkfly-dual-compartment-v1".
Cache mutation/miss or a second probe is fatal. Normal tests substitute harmless
executables only in private explicit test seams; production paths cannot inject them.
Hidden-probe/timeout/extra-child tests do not run the real compiler.

Read-only sizing recorded during review: historical header64242B, identity32939B;
ready is digest-only. Existing source map7074B/64 entries, sources1132746B,
largest146132B. Read-only file sizes in this revision: Zig177108480B, DLL190976B,
metadata333B. These support caps, not a fresh engine or performance claim.

## Appendix C — public D1 receipt capture and journal handoff (R3)

One coordinator lock serializes EVERY D1 call, including status/snapshot/maintain.
No other collaborator calls D1; native mode wraps existing public calls, not D1 internals.
Coordinator keeps a bounded last-seen receipt map<=512 and at most two known live IDs.
This is a detached validation watermark, not a second lifecycle/history.
Successful public operation Receipt returns are captured immediately before any next call.
Returned snapshot live receipts are captured too; terminal records come from public status.

Before a D1 call, reserve_receipts reserves one outbox slot for up to three changed receipts.
Ticket={ticket:I[1,2**53-1]}; at most one unpublished reservation under coordinator lock.
Ticket exhaustion faults before mutation; empty diagnostic batches need no journal record.
Normal outbox capacity32 batches; each batch<=8192B, receipts<=3, detached immutable.
A separate preallocated emergency batch of two receipts is never used for ordinary work.
reserve returns None immediately on full/fault/closed; never waits under intake lock.
On None: fence intake/native advancement, call D1.stop(worker_failed) using emergency
capacity, capture the <=2 unfinished receipts, and initiate owned worker stop.
This may leave incomplete evidence if storage cannot drain; never drop and continue.
Emergency publication cannot create a new accepted image or a success seal.

Capture algorithm per outer D1 call:
1. Save the <=2 formerly-live IDs, call the outer operation exactly once and
   capture its direct Receipt immediately; capture any directly returned live
   Receipt fields as well. Newly admitted IDs enter the known-ID set immediately.
2. Call public snapshot(), capture BOTH returned live receipts from that one
   atomic snapshot, and compare its live IDs with known formerly-live IDs.
3. For every disappeared ID not already captured terminal, call public status
   exactly once and capture its terminal Receipt immediately. A live result for
   a disappeared ID is impossible under coordinator ownership: journal_gap.
4. If step3 made any reads, take another public snapshot and capture both live
   receipts. Repeat step3 only for newly discovered uncaptured disappearances.
5. Finish on a snapshot with no uncaptured disappearance. That snapshot plus
   captured terminal watermark is the authoritative result for command/status
   gates. Do not perform another uncaptured D1 call before publishing that result.

At most TWO distinct live IDs can disappear while this lock is held. Each
repeat consumes at least one previously uncaptured disappeared ID. Therefore
the bound is three public snapshots plus two terminal status calls, not four
alternating live-status reads. Never freeze time or recurse through the wrapper.
If a terminal status read itself expires another live ID, the following
snapshot reveals that disappearance atomically; its status is captured once.
The last snapshot cannot hide a terminal transition: any missing formerly-live
ID is reconciled before finishing. No independent subsequent status read is
used merely to format an HTTP result.
Keep captured terminal receipts in the watermark until valid retention pruning.
This is a detached current-state/revision watermark, not new D1 transition history.
Three batch entries still cover one outer successful change plus at most two
subsequent terminal transitions, including clock-fault fan-out.
Same(id,revision) with identical bytes is deduplicated; differing bytes,
a revision increase other than previous+1, or a new ID not at revision1 is journal_gap.
A not_found for a disappeared ID lacking a captured terminal is journal_gap,
even if a long interruption could explain pruning; never infer its missing result.
Pruning of an already captured terminal is valid only with trusted elapsed retention.
Exceeded snapshot/status bounds, impossible live resurrection or unknown changed
identity is journal_gap; fence native advancement and preserve incomplete evidence.
A >15-minute interruption can make a transition irrecoverable under public D1 APIs.
No fabricated terminal or success seal repairs that case.
After an outer exception, perform this same bounded capture before propagating it.
Emergency stop applies the same algorithm with at most two terminal entries;
a reconciliation failure does not recursively retry recovery.

publish_receipts(ticket,entries) has no disk IO or callbacks.
Cause={operation:"reserve"|"cancel_reservation"|"admit"|"decoded"|"decode_failed"|
"moderate"|"dispatch"|"started"|"complete"|"stop"|"maintain"|"status"|"snapshot",
target_id:?UUID,notice_seq:?I[0,4095],read_pass:I[0,2]}.
Publish one aggregate batch with ReceiptEntry={receipt:Receipt,cause:Cause};
0..3 changed receipts; preserve per-entry cause if reads caused the change.
Three slots cover one successful operation plus two terminals from a later clock fault.
Emergency stop still changes at most the two live receipts.
D1 Receipt uses every original dataclass field in section D1, exact primitive
checks, optional fields and status semantics; no reduced/fabricated receipt.
ReceiptProgress={submitted_ticket:J,durable_ticket:J,
queued_batches:I[0,32],emergency_pending:B,closed:B,fault:?Fault}.
Worker/evidence thread writes batches FIFO outside coordinator lock.
It acknowledges a ticket only after complete bounded serialization/write/fsync.
No ticket/receipt is evicted early; empty batches release reservations without journal event.
Full 4096-event allowance or5s storage progress failure fences, never wraps counters.
finish_receipts is called only after final D1.stop reconciliation, and forbids new submissions.
Diagnostics after finish read terminal D1 data but create no accepted transitions.
At healthy model end no live IDs remain; their terminal revisions are already submitted.

Causal event order is mandatory:
admit -> decoded -> approval -> D1 dispatch receipt -> issued image command ->
worker start -> D1 started receipt -> original observations ->
worker complete -> D1 complete receipt -> next command.
Persist D1 dispatch ticket before sending its image command.
On ordinal7, persist observation and complete wire evidence, publish D1.complete,
wait asynchronously for its durable ticket, then release exactly one next command.
On ordinary boundaries, persist observation before ack.
Capture known D1 expiry/fault/stop before subsequent commands; fault forbids them.
If a callback returns after shutdown, capture actual D1 terminal result only;
never republish pixels or rewrite an earlier processed receipt.
The session cannot release an ack merely because a Receipt appeared in memory.
Multiple decode/moderation transitions between poll calls remain separate journal records.
No intake lock is held while waiting for a durable ticket or receipt drain.

## Appendix D — snapshots, notices, graph validation and journal encoding (R4)

Boundary={id:I[0,40],next_observation_index:I[0,40],
issued_observations:I[0,40],completed_observations:I[0,40],
active_dispatch_id:?UUID,unissued_active_observations:I[0,7],
free_observations:I[0,40],ack_deadline_ns:N}.
id=next index=issued=completed; free=40-issued-unissued_active.
Boundary exists only after prior causal evidence/receipt persistence.
Initial boundary0 is consumed internally by black release, not guest dispatch.
At active ordinal0 completed, unissued=7; at ordinal7 completed, active is null.
Consuming boundary sets it null and increments issued once, before command transport.
During call/transport, issued=completed+1 and reserved active remainder excludes
that already issued call; if image ordinal0 issued, unissued=7.
Receiving a result increments completed but does not expose boundary until required
complete/receipt drain; at this point issued=completed, active remainder unchanged.
Budget checks for reserve/admit use this atomic session snapshot, never a stale UI count.
Between coordinator check and admit, budget may shrink by at most one issued step;
admit must re-read nonblocking snapshot immediately before its D1 call.
If another step consumes allowance afterward, accepted image can still end rejected;
acceptance is not a reservation of eight model intervals.
advance uses exact current boundary ID; stale/duplicate ID faults instead of retrying.

NativeSnapshot={schema:"market-native-session/v1",incarnation:UUID,worker_session:UUID,
state:"prepared"|"starting"|"running"|"stopping"|"ended"|"faulted"|"closed",
fault:?Fault,cleanup_fault:?Fault,issued_observations:I[0,40],
completed_observations:I[0,40],in_flight_index:?I[0,39],
active_dispatch_id:?UUID,unissued_active_observations:I[0,7],
free_observations:I[0,40],boundary:?Boundary,wall_deadline_ns:?N,
startup_deadline_ns:?N,observe_deadline_ns:?N,receipt_progress:ReceiptProgress,
latest:?Measured,header_sha256:?D,engine_identity_sha256:?D}.
Measured={observation_index:I[0,39],input_kind:"black"|"image",
image_id:?UUID,frame_sha256:D,wall_completion_ns:N,model_end_tick:I[5000,200000],
group_spikes:GroupCounts,group_rates_hz:GroupRates}.
Latest is null before completed>0; then its index=completed-1 and model_end=completed*5000.
Black latest has image_id=null, black digest; image latest has bound approved ID/hash.
Prepared has no deadlines/identity/latest/boundary/in-flight; counts0.
Starting has wall/startup deadlines, counts0; ready sets header/identity together.
Running has wall deadline; observe_deadline iff an in-flight call is authorized.
in_flight=index completed iff issued=completed+1, else null.
Ended requires no in-flight/boundary/active and40 completed; fault=null.
Faulted has first fault; stopping may retain it; closed is only after successful cleanup.
A separate retained final outcome distinguishes normal ended from fault before closed.
Snapshots do not erase latest measurements on stop, but their liveness is false.

NativeNotice={notice_seq:I[0,4095],incarnation:UUID,worker_session:UUID,
protocol_sha256:D,type:literal,payload:one exact variant}.
ready payload={header_sha256:D,engine_identity_sha256:D,ready_ns:N}.
boundary payload=Boundary; derived parent-side, never a child wire type.
start payload=Start; observation payload=Measured;
complete payload=Complete; ended payload={reason:"model_limit"|"cancelled",completed:I[0,40]};
fault payload={code:Fault,cleanup_fault:?Fault}.
A single-consumer FIFO holds at most8 notices; all ordered by notice_seq.
Overflow fences using one preallocated fault slot; never overwrite completion or keep running.
The parent retains full observation/evidence privately; notices carry no unbounded arrays.
A complete notice is delivered only after worker frame validation, not after D1 completion.
Coordinator supplies that separate public receipt ticket before the next boundary exists.

Header exact keys:type:"header",version:"cell-activity-raw/v1",
engine_identity:EngineIdentity,selection:Selection,cells:array[256]Cell,
topology:Topology,source:HeaderSource.
HeaderSource exactly graph_ids_sha256,graph_ptr_sha256,graph_post_sha256,
annotations_sha256:D; all match prepared locks and engine identity.
Cell={model_index:I[0,166699],source_id:I[1,2**53-1],
groups:nonempty unique subset of seven names in GROUPS order,
soma:null|array[3]I[-(2**53-1),2**53-1]}.
Unique model indices and strictly ascending source IDs.
Selection={method:"mandatory-groups-kc-stride/v1",limit:256,
group_population_counts:seven-key positive integer map,
group_selected_counts:seven-key I[0,256] map}.
Topology={method:"induced-directed-edge-stride/v1",limit:512,
eligible_edges:I[0,25582938],edges:array[min(eligible_edges,512)] of
[edge_id:I[0,25582937],source_slot:I[0,255],target_slot:I[0,255]]}.
Edge IDs unique; tuples ordered by source source_id,target source_id,edge_id.
Every membership equals the engine's actual index membership; counts are rederived.
All non-KC group cells are selected; KC subset cannot be counted as the whole KC population.

EngineIdentity exact keys version:"fly-engine/v1",model_provenance,
neural_groups:seven-key arrays of distinct model indices,sha256:D.
Hash matches unchanged canonical engine identity without sha256.
Group sizes for this fixed locked configuration are KC4064,PAM1115,PPL1012,
MBON074,MBON112,motor_left1,motor_right1; no new physiology claim.
model_provenance exact keys model,model_fingerprint,build,eta,parameters,
graph_ids_sha256,graph_ptr_sha256,graph_post_sha256,plastic_edges_sha256,
configuration_sha256, as the unchanged engine declaration.
model is "stonkfly-dual-compartment-v1"; eta=0.001; build is NativeMetadata plus model.
model_fingerprint={version:"model-source/v1",sources_sha256:41-member map,sha256:D};
map matches Appendix G package-relative members and its unchanged canonical fingerprint.
All four array/plastic hashes are D; ids/ptr/post match locks.
parameters/configuration_sha256 are the exact bounded unchanged declaration maps:
their key sets and nested rule keys are enumerated below; no extra fields.
Numeric entries are finite numbers; hashes are D; explanatory/source strings T[1024].
parameters keys: interpretation,source,kc_adaptation_jump_mV,kc_adaptation_tau_ms,
kc_rest_mV,maximum_fraction,maximum_rate_bin_ms,memory_decay_seconds,
minimum_fraction,modulator_delivery_trace_ms,neural_dt_ms,trace_dan_seconds,
trace_kc_seconds,weight_filter_seconds.
configuration_sha256 keys: adaptation_jump,adaptation_tau,corrected_edges,
dan_baseline_hz,dan_index,gain,initial_weight,kc_mask,lamina,modulation_mask,pre,
r8,r8_channel,r8_uv,rest,retina,rule,rule_sha256,sugar,tonic,uv.
Only adaptation_jump/adaptation_tau are numeric; rule is the object below;
every other configuration value is D.
rule keys: interpretation,source,maximum_fraction,maximum_rate_bin_ms,
memory_decay_seconds,minimum_fraction,trace_dan_seconds,trace_kc_seconds,
weight_filter_seconds. Only interpretation/source are strings; others numeric.
These declared numbers are checked against preserved source defaults by source
review and worker's actual identity, not treated as measured physiology.
Parent does not claim to independently reconstruct array-derived hashes/cohort soma joins.

Per-bin group count <=100*group_size; sum50 yields each500-ms total.
For every group inclusion A subset B, counts_A<=counts_B in every bin.
Whole-brain total <=166700*5000=833500000.
Lower bound = max over every pairwise-disjoint subset of the seven groups of
the sum of its observation totals; enumerate exactly127 nonempty subsets.
Also require unique selected-cell sum over all12800 bytes<=total_spikes.
Each non-KC group bin equals sum of its selected members; selected KC bin sum<=KC bin.
No sum of overlapping group totals substitutes for either lower bound.
Rates=total/(population*0.5), math.isclose rel/abs1e-9, finite0..10000.
Group-bin timestamps are exact index-derived original10-ms windows, not interpolation.

Journal files are immutable append-only, exclusively created; only final seal is a rename.
events.bin records use uint32LE length +uint32LE json_length+C(Record)+binary.
Record={schema:"market-native-event/v1",sequence:I[0,4095],previous_sha256:D,
recorded_ns:?N,kind:literal,payload:variant,binary_bytes:I[0,12800],
binary_sha256:D,sha256:D}.
Hash=SHA256(b"market-native-event/v1\n"+C(record without sha256)+binary).
First previous_sha256 is64 zeroes. Empty binary has SHA256(empty), not null.
Record body<=65536 bytes; entire file<=32MiB and4096 records.
Kinds/payloads:
binding={protocol_sha256:D,bindings_sha256:D};
header={header_sha256:D,engine_identity_sha256:D,worker_seq:I[0,4095]} (full header only header.json);
wire={direction:"parent"|"worker",message:E-without-launch_nonce + exact extra fields};
receipt={ticket:I[1,2**53-1],receipt:full D1 Receipt,cause:Cause};
clock_bracket={index:I[0,2],p0_ns:N,child_ns:N,p1_ns:N};
session_fault={code:Fault,cleanup_fault:?Fault}.
Static_header wire is replaced by header kind, retaining its wire seq in worker_seq.
All other wire records retain both envelope sequence and immutable content;
binary only image ack/observation. Nonce is never persisted.
Full D1 Receipt field set/types are the frozen dataclass at image_admission.py:99–127;
UUID/hash/indices/times and revisions1..6 remain exact and every field is mandatory.
No Receipt fields are excluded from canonical hashing.
recorded_ns null only when parent clock faulted; such runs cannot seal complete.
No unbounded event metadata, error text, arbitrary paths or credential fields.

## Appendix E — exact HTTP v2 combinations (R4)

AcceptanceV2={schema:"market-image-acceptance/v2",status_capability:
str matching is.[A-Za-z0-9_-]{43},image:StatusV2}; exactly these fields.
parseAcceptance dispatches by exact schema to strict v1 or strict v2 image parser;
it rejects v1-with-v2-image and v2-with-v1-image. No permissive mixed fallback.
StatusV2 has EXACT v1 fields plus worker_session:?UUID,
first_observation_index:?I[0,32],completed_observations:I[0,8],
observation_revision:I[0,40], with schema="market-image-status-wire/v2".
v1 fields: incarnation:UUID,id:UUID,revision:I[1,6],status:literal,detail:literal,
frame_sha256:?D,accepted_age_ms:?J,remaining_decode_ms:?J,
remaining_moderation_ms:?J,remaining_handoff_ms:?J,time_uncertain:B,
preview_available:B.
All four times null iff time_uncertain, otherwise finite integer ages/remaining.
Terminal remaining values0; nonterminal remaining fields derive original D1 phase
deadlines with ceil(max(0,deadline-now)/1e6), age floor, never renewed.
processing remaining_handoff is0 because handoff already occurred, not a new expiry.
completed_observations is this image's validated count, never global.
observation_revision=0 before its first validated observation, else last validated
global index+1; immutable after terminal status, even as black/other images advance.
For k>0: first index nonnull and observation_revision=first+k.
Metadata-only terminal has k=0 and revision watermark0.

Exhaustive status/detail combinations:
accepted/decoding: hash null,preview false,worker/index null,k=0.
accepted/awaiting_approval: hash D,preview true,worker/index null,k=0.
queued/ready: hash D,preview true,worker/index null,k=0.
queued/dispatching: hash D,preview false,worker UUID,index null,k=0.
processing/processing: hash D,preview false,worker UUID,index nonnull,k0..8.
processed/completed: hash D,preview false,worker UUID,index nonnull,k=8.
expired/ttl_expired: hash D,preview false,worker/index null,k=0.
rejected/decode_failed or decode_timeout: hash null,preview false,worker/index null,k=0.
rejected/moderation_rejected or moderation_timeout: hash D,preview false,
worker/index null,k=0.
rejected/worker_failed,worker_outcome_unknown,session_ended,clock:
preview false; preserve confirmed hash/session/index/k, never invent or clear them.
For these rejection variants: index requires worker/hash; k>0 requires index;
worker requires hash; null hash requires worker/index null,k=0.
A dispatched but unconfirmed start has worker UUID,index null,k=0.
D1 revision remains its authoritative revision; no inferred exact fixed revision by status.

IntakeV2={schema:"market-image-intake/v2",incarnation:UUID,
mode:"bounded-native-test",worker_connected:B,
health:"ready"|"stopping"|"faulted",fault:null|"clock"|"decoder"|"ownership"|
"shutdown"|"native_worker",receiving:B,decode_busy:B,pending:?StatusV2,
receipt_count:I[0,512],active:?StatusV2,
native_state:"starting"|"running"|"stopping"|"ended"|"faulted"}.
Running healthy: health=ready,fault=null,worker_connected=true;
starting: health=stopping,fault=null,worker_connected=false,receiving=false,
pending/active null; this means not accepting, not an implicit start retry.
Normal ended: health=stopping,fault=null,worker_connected=false,
receiving=false,pending/active null; terminal status reads remain available.
Faulted: health=faulted,fault nonnull,worker_connected=false,receiving=false,
pending/active null; stopping retains first fault if any.
decode_busy can remain true until separately confirmed D2 cleanup.
Pending is accepted or queued; active is processing; both match incarnation.
No simultaneous receiving and pending; active may coexist with one of them.
Any processing/queued-dispatching worker_session equals current native session.
Post-stop reads show retained per-image failures; they are not active work.

NativeState has EXACT fields listed in section12 plus schema,
and all are required. mode="bounded-native-test",model_limit_ms=20000.
incarnation/worker_session UUID; state enum starting/running/stopping/ended/faulted;
fault:?Fault; model_ms=500*observations_completed, count I[0,40].
Before count0: input_kind,image_id,frame_sha256,group_spikes,group_rates_hz,
measurement_age_ms all null. After count>0: input_kind black/image, digest D,
seven-key numeric maps valid; image_id null iff black, otherwise bound UUID.
These always describe latest validated completed observation, never current start.
measurement_age_ms=floor((parent_now-latest.wall_completion_ns)/1e6).
When time_uncertain=true, age null; other immutable measured values remain.
When clock valid and measurement exists age is nonnull J; no clipping a negative age.
Starting count0/fault=null; running fault=null; ended count40/fault=null.
Faulted has nonnull fault; stopping may retain a fault and last measurements.
time_uncertain iff parent/session clock fault, not a substitute for transport stale.
Completed observations can exist with no image processed (all black is valid negative).
UI updates neither measurement identity nor age on preview completion/status polls.
Price pause/resume remains synthetic-price control; native stop has no resume.
No native image route is added, so a preview is never sold as a current measured image.

## Appendix F — monitor, cleanup and successful sealing (R5)

Set JOB_OBJECT_LIMIT_JOB_MEMORY=4GiB while preserving KILL_ON_JOB_CLOSE and no
breakaway flags, through new owner's private Win32 declarations, before process creation.
Query/read back effective limits; failure prevents release.
This is a Job commit quota for worker+probe, not a hard RSS/physical-RAM guarantee.
Parent/D2 are outside that Job. Monitor reports this scope explicitly.
Sample worker and temporary probe working sets; stop if either or their current
sum exceeds4GiB. OS PeakWorkingSetSize per exact held handle is retained separately.
Sampled RSS/disk checks may overshoot between samples; never claim instant limits.
Query Job PeakJobMemoryUsed/commit; unexpected members terminate the owned Job.
Only the one provisional/proved version probe exception in Appendix B is permitted.

Sample at most once per100ms plus initial/final samples; never burst-catch-up.
Start at process release, continue through cleanup (up to25s after a900s stop).
At most12000 samples; cap reached is resource fault, not dropping samples.
Real inter-sample gap>=2s is monitor fault; failed queries retain failure/incomplete.
Combined disk scope is every regular byte in native work root and D2 decoder work
root including scratch/journals/logs, excluding immutable runtime/tool sources.
Count symlink/unknown directory escape as ownership fault, never follow it.
Compare current/peak counts to256MiB; native evidence itself also<=64MiB.
Monitor thread has one32-row finite outbox, separate from32 receipt batches.
One writer drains it; if full, latch storage fault and stop, never allocate more.
Flush/fsync monitor at least every1s and at terminal drain; timestamps are sampled,
not rewritten to file-write time. Native ack cannot bypass an existing writer fault.

MonitorRow exact fields:
{schema:"market-native-monitor/v1",sequence:I[0,11999],previous_sha256:D,
sample_ns:?N,worker_pid:I[1,2**32-1],worker_creation_time_100ns:U64,
worker_rss_bytes:U64,worker_peak_rss_bytes:U64,
probe_pid:?I[1,2**32-1],probe_creation_time_100ns:?U64,
probe_rss_bytes:U64,probe_peak_rss_bytes:U64,
job_process_count:I[0,2],job_commit_bytes:U64,job_peak_commit_bytes:U64,
combined_output_bytes:U64,evidence_bytes:U64,gap_ns:N,
fault:?Fault,sha256:D}.
Probe PID/creation both null before start/after exit; current RSS0 when absent,
peak preserves maximum observed/OS-reported probe peak until terminal.
Worker current RSS0 after exited; last OS peak retained with exact handle identity.
sample_ns null only on clock fault; then gap_ns preserves last valid gap and fault=clock.
Rows use uint32LE len+C(row), <=2048B, <=24MiB/12000 records.
Hash=SHA256(b"market-native-monitor/v1\n"+C(row without sha256)).
First previous hash zero64; independent sequence/hash chain, not events.bin counter.
OS identity/commit/query failure stops; it cannot produce a fake zero-success row.

CleanupReceipt exact fields:
{schema:"market-native-cleanup/v1",incarnation:UUID,worker_session:UUID,
requested_ns:?N,finished_ns:?N,
worker_creation:"not_created"|"created_unverified"|"verified",
worker:?ProcessIdentity,probe:?ProcessIdentity,
worker_exit_code:?I[0,2**32-1],probe_exit_code:?I[0,2**32-1],
worker_exit_confirmed:B,probe_exit_confirmed:B,job_empty_confirmed:B,
ipc_handles_closed:B,process_handles_closed:B,job_handle_closed:B,
root_lock_closed:B,evidence_files_closed:B,
first_fault:?Fault,cleanup_fault:?Fault,outcome:"confirmed"|"unconfirmed"}.
worker_creation=not_created iff CreateProcessW never succeeded:
worker=null,worker_exit_code=null,worker_exit_confirmed=true means none launched,
not a measured exit. Existing Job/pipes/root-lock cleanup obligations still apply.
No monitor row exists before a verified worker identity; no pid0/fake sample.
worker_creation=created_unverified iff creation succeeded but identity capture failed:
worker=null,outcome=unconfirmed; retain exact created process/thread handles and
root lock even if exit can be observed, until identity/owned cleanup is resolved.
worker_exit_code may be the actual queried code, otherwise null; never invent identity.
worker_creation=verified requires concrete ProcessIdentity and its actual held-handle
exit result. Only this variant can support a complete final seal, with exit_code0.
No-probe startup failure has probe=null and probe_exit_confirmed=true (nothing launched).
Confirmed permits the honest not_created variant after all created resources close,
or verified actual exits, empty Job and all closure flags true.
Unconfirmed retains exact remaining handles/root lock; never reports success.
CleanupReceipt returned by finish_close is this exact type, written as cleanup.json
only after its stated operations occurred; <=16384B. No nonce or arbitrary errors.
Parent shutdown has at most25s application wait, but cannot guarantee physical
termination of a stalled kernel/OS call; unconfirmed stays an honest limitation.

Success-seal order:
1. Require model_limit ended, clean full EOF, exit0 and40 validated observations.
2. Capture D1.stop(session_ended), close submissions, drain all receipt/event/monitor
   outboxes and fsync/close their files; preserve every genuine earlier processed receipt.
3. Confirm actual held worker/probe exits and empty Job. Perform the final bounded
   source comparison below, then close IPC/process/Job handles.
4. Close root ownership lock only after the above confirmed cleanup; on any failure
   retain ownership and produce no final.json. No same-root startup is allowed.
5. Write cleanup.json through an exclusive temporary file, fsync, close and rename;
   read back bounded bytes/hash and close the verification file. All flags are now true.
6. Prepare final.json.tmp exclusive, write/fsync/close, verify bounded bytes/hash
   with a separately closed reader. Recheck unchanged directory/file identities.
7. Rename that fully closed temp to absent final.json without replacement.
   Only a successful final rename publishes the success seal.
The session directory is unique/nonempty and cannot become a fresh-start directory
after root-lock release; no further image/native mutation is allowed.
Directory/file identity checks surround final publication; any conflict is incomplete.
This establishes completed application operations, not power-loss-proof NTFS durability.
No success file is created before child/Job/handle/evidence closure is confirmed.
A pre-creation or created-unverified failure can never produce final.json.


Final source comparison and finalization budget:
One final rehash occurs after observations and confirmed worker/probe exit, before
root-lock release or final publication. It uses <=1MiB chunks with the same
stat/open/fstat/end-stat identity checks and all Appendix B per-file/aggregate caps.
Covered set is exactly Protocol preserved_sources,application_sources,lock_sources
and Bindings tool keys python_launcher,python_config,worker_exe,compiler_exe,
native_library,native_metadata plus the six dependency init/METADATA bindings.
Exclude the five runtime data keys graph,normalized_neurons,annotations,
neurotransmitters,edges:
no end-of-run graph construction, array load or duplicate multi-gigabyte data audit.
Compare every covered raw SHA256, byte count, device/file ID and mtime to bindings.
Also rehash the preserved protocol.json/bindings.json bytes against prepared digests.
No changed/missing/unreadable member, partial comparison or timeout can yield true.
The scoped claim means comparison at prepared/start and final checkpoints only;
it is not continuous physical source attestation or a new dependency-binary audit.

finalization_deadline_ns = first stop request time +25000000000; on normal end,
use the parent receipt time of model_limit ended as the first stop request.
This ONE25s budget covers drains, process/Job cleanup, final rehash, file fsync/
closure and seal publication, not separate25s grants for each operation.
Check remaining budget before/after each bounded read/hash/write/cleanup stage
and immediately before final rename; failure leaves incomplete output/no success.
OS-call stalls remain explicitly unguaranteed; elapsed time never authorizes retry.
The final comparison produces SourceCheck={scope:"prepared-source-lock-tool-cache/v1",
started_ns:N,finished_ns:N,file_count:I[1,128],bindings_subset_sha256:D,all_match:true}.
bindings_subset_sha256=H(the covered Bindings.files subset plus protocol/bindings
raw digests under reserved keys protocol_sha256 and bindings_sha256).
file_count counts actual covered FileBindings plus these two control files.
Require started<=finished<=finalization_deadline, all reads closed before sealing.
SourceCheck is embedded in Final, no extra journal stream or artifact.
Inspector recomputes the exact subset digest/count from prepared declarations,
validates source-check times/scope and requires the matching true comparison.
When checking current files, use the same bounded subset; changed current bytes
cannot be presented as reproducing the historical source check.
Mutation-after-readiness tests must refuse the final seal, without changing
previous genuine processed-image receipts.

Final exact fields:
{schema:"market-native-final/v1",status:"complete",verification:"integrity-only",
incarnation:UUID,worker_session:UUID,protocol_sha256:D,bindings_sha256:D,
header_sha256:D,event_records:I[1,4096],events_sha256:D,event_chain_sha256:D,
monitor_records:I[1,12000],monitor_sha256:D,monitor_chain_sha256:D,
cleanup_sha256:D,observations:40,model_ticks:200000,image_dispatches:I[0,5],
processed_images:I[0,5],max_monitor_gap_ns:N,peak_worker_rss_bytes:U64,
peak_probe_rss_bytes:U64,peak_job_commit_bytes:U64,peak_output_bytes:U64,
source_unchanged:true,source_check:SourceCheck,first_fault:null,cleanup_fault:null}.
All summaries rederive from full files, not just this seal. final cap16384B.
Model run complete with zero processed images is integrity-complete but integration-negative.
Positive integration acceptance is a separate reviewed result, never the seal's inference.

failure.json, if writable, is capped16384B with exact fields:
{schema:"market-native-failure/v1",incarnation:UUID,worker_session:UUID,
first_fault:Fault,cleanup_fault:?Fault,last_event_sequence:?I[0,4095],
last_monitor_sequence:?I[0,11999],cleanup:?CleanupReceipt}.
Its absence after disk failure is not success. Partial journals/temp files remain
incomplete; offline inspector refuses complete mode without valid final/cleanup/full EOF.
Normal EOF followed by fsync/handle/Job/root-lock failure cannot seal.
Owner death relies on kill-on-close and leaves incomplete evidence; never synthesizes
an application cleanup receipt after the owner has disappeared.

## Appendix G — exact preserved source map

The following64 path/hash pairs are the accepted byte-preservation boundary.
The41 src/fly_connectome_sim entries are the packaged model-source/v1 membership.
These hashes were read from the accepted intake baseline, not regenerated by running
the model. Prepare/release must compare current raw bytes to them.

```text
scripts/analyze-market-feasibility.py 19bca306f6720d5931b31321d1ccc8939a447737b23cc052931b6348994a46cc
scripts/analyze-response-structure.py 5a8eaff4e2904191d394859c8eb02ae107a61de04cb000228e371e1c61052b25
scripts/continuous_motor_supervision.py b2527b1817baaee0962d4c49007826ff78e51e55ee0122728376739c0a649add
scripts/drive_input_supervision.py 06aa2ad4aed00c91027a03147229f6c507cb5e5fb21af0f1a01b13156bf210f8
scripts/export-anatomy.py 119c1898b3c018cde1e39059d8bf122a43c15c4bb7bac33e4f331f86f1d7161e
scripts/live_buffer_supervision.py 75dd275bd3a6e867fafd0d2d17c6adc0df38fb215752b5c404322dfab0246055
scripts/market_artifacts.py 1e6074838481d3149be56a6235f74b7de29d5d2c45d56bd1cf7311460ccb0c0a
scripts/market_continuous_drive.py 7285c150d2ab14506c94d90d995da142e71eb1d29277f7b4d582b740c953e42d
scripts/market_live_buffers.py 5c81391fd4bf1a667ef0d483f027601af66f10eafd64a6e98283c53e1d1ec9ad
scripts/market_motor_readout.py e11e9a7adc10b10f08a67b25e41ad1d717174c0e5a106ef9be61416e060734e1
scripts/market_motor_readout_v2.py 878b6a4d16c824727ac78edd68cb5e44da11445a0889e7b8a35e960b0f94bf69
scripts/market_population_state.py 8ad6552e6e7032035b6ded30d5823a1253751e02d66dc587cf7a64737903b550
scripts/market_supervision.py a1ed136a32a482f78f6a6de337e67ad28c05bd2ad42ac31d8ce949a27350182d
scripts/run-cell-activity-session.py cd4a04234d82c2a22b21b22f858e70ee2047c2c1cd78ce30336d0deb550ec6ed
scripts/run-continuous-motor-probe.py d01095013f16592c402347fbd962a566bf589ba666e5e3c9f27b53ebcd0ef1e8
scripts/run-drive-input-comparison.py ed7ca12a34193b1a4a01ca4dd305c396ad387708aa3b051f79209051b4d143d4
scripts/run-live-buffer-performance.py a8b5d50e15ed18c6f06b07a261a31006bbd2faa8a95a1edeccf31e351a3e761d
scripts/run-market-response-diagnostic.py 3b9b464d9bf43caecb3f44586bcf15481ea5fc53233b29db123a2a1451fe67f6
scripts/screen-population-excursion.py 06082860bc1ab0cc3ce5a27bf167aeb268ca04e0422905137ba3c29b7217d929
scripts/supervise-continuous-motor.ps1 16fcfee8458c693e01ab396d935750ff2bbb74dcc43c6dfc70accbb9cb2465f5
scripts/supervise-drive-input.ps1 a50e1b09135d4a74b8b0f343a162d4ad6a7c005191245897ee869d3dc234512b
scripts/supervise-live-buffer.ps1 ff23ea6ca3b83f00a88d5bd98f947c16e99e358c91a77a3e8ce54d97e11060cd
scripts/supervise-market-response.ps1 584358175f3a6be9a759ca816124c0ff70519f3488d35786001988776c918861
src/fly_connectome_sim/__init__.py e264625ca71686e6284982c6ed394e50a80e0bd295dcf58c8519ea94e009b234
src/fly_connectome_sim/cli.py 32a4e9c15c6c216a38f560143e5601c297af92e30cf48f4c9dbd7054261e608e
src/fly_connectome_sim/data.py f08f2c83ae788856d383adaf9aff8e7886a7b4a25326cd9c48559e4a73a93243
src/fly_connectome_sim/engine.py 25ac8924f46c434d788c7defd9ec66f489f6dbeef0e653873bb545a099b58833
src/fly_connectome_sim/experiment/__init__.py c52b94ba0296e4f3d43911f36c5e703a35e3ab4b84f59671bd428e45e6f32fb1
src/fly_connectome_sim/experiment/adapter.py 7e6fab3635d357780fee45d53769f385c5b15d95fa2d2f46b6e4e0e69583e3fe
src/fly_connectome_sim/experiment/analysis.py 2d63a826fa0c63f0208852ba447f8b73f8b614091255d505468cdf49f6bd6e0f
src/fly_connectome_sim/experiment/assay.py 23a3589818a6375521530403ac67718a9c48b440622206f3f84669b3ad201f58
src/fly_connectome_sim/experiment/cell_activity.py 63047d84b448511d8a41da73ba7d5252e085d23f1ff91b9972f2e677a41c456f
src/fly_connectome_sim/experiment/content_diagnostic.py e9a0657a634f0e770cf8dcd529c8428cac1c4b527014bf5e7a1da7cb07b26455
src/fly_connectome_sim/experiment/event_cards.py c3060ab49f1190ac2462e164709ca1aa3127f9d95d18b275178e7d66e5a037ba
src/fly_connectome_sim/experiment/event_choice.py 05a6d1aee7cf75729303cfb7fed6ea18cdc6febb56ec08ecf5ec2bcc121e5b31
src/fly_connectome_sim/experiment/event_followup.py 5f6c7928b3efa401bd754b2cb52af084466b957756331e89df4b42d1e4de7b00
src/fly_connectome_sim/experiment/event_proposals.py ccd54c3ff90e055add2600577221f91388472f270c2efcb5cd9e9e1c00964d2c
src/fly_connectome_sim/experiment/executor.py 616ec40e5df2f5c1290484a7aa023fd0383dcc7dca72e72ce5a2be399be23c7b
src/fly_connectome_sim/experiment/feed_event_session.py fdbbd7b13dc44bb9cbf4184f8f75849963dd6fa4879c5bcb613ff8aa8b4acea9
src/fly_connectome_sim/experiment/measured_replay.py edb2f582e8ea78c15da1fbb6700cf4304b40fcde41669c9e189aaa7afd1bf2fe
src/fly_connectome_sim/experiment/protocol.py 0cd8952a7176fd910ba4e3c87113aecebf1c87b57952ee967cea8eaf9afb40a2
src/fly_connectome_sim/experiment/qualification.py 0396d45ec373f124b6d7f0c6c827991273ad483ff5b8cc0400a400759dcbf559
src/fly_connectome_sim/experiment/qualification_grid.py 5e93098efe48f69337ba80b3b771829f9ad1d2ae48d63edabf97f63c06955420
src/fly_connectome_sim/experiment/recorder.py 7db2b493217933c15b4da7211cce1b2c66074d1ae0ad1ea40cb63fdbbce7764e
src/fly_connectome_sim/experiment/replay.py 322da0d210d98a14460e4df0b0f69528eceae3ed2dd7dfebb51b6efda5fcdba2
src/fly_connectome_sim/experiment/session_workflow.py f76cc9f9f828334b319f52b8a8c6e3c936d5ae2dfb8a87f8bb7e7f00c165ab1d
src/fly_connectome_sim/experiment/stimuli.py 02b2ae2288d8cae859f5ceb99291fcf0e6b05334c2ad9ff3fa1c0c7079fbad08
src/fly_connectome_sim/experiment/video_observation.py 688be0bb6632d71463cfa5cb5d211c272f6ca1953492252553a2e98b80cab0f5
src/fly_connectome_sim/experiment/video_policy.py 704b34de1d79bff91378c4d16521e25104360a81870b27a98ca829506a863e67
src/fly_connectome_sim/neural/__init__.py e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
src/fly_connectome_sim/neural/brain.py 0ebf5ef41a2bfa46664720c1d19b05ea7aff4fe7ec12b434bf4f3d81b2380814
src/fly_connectome_sim/neural/checkpoint.py b72ea9d0d80b5557a0102c41beead593fea77d3b90da749f6d2dc914bb48cd0f
src/fly_connectome_sim/neural/circuit.py e9ed5d237c7c01fbaf80f75cec75f5f9f2e33965461e3480813ade78597f6c45
src/fly_connectome_sim/neural/common.py fadb9b415d3ec4edabe928b1821f3f5dbb34eae8dc67a4927f287ad74074a40a
src/fly_connectome_sim/neural/connectome.py 38fffdf4bd31cb51be6f3dda3cc4236ff754a2a99d0ced8dbffe00352224d940
src/fly_connectome_sim/neural/kernel.cpp e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509
src/fly_connectome_sim/neural/native.py 85f68d859621d6c8065e93722f173230f35277ad8d0b18c02f4eee8c5911a4fc
src/fly_connectome_sim/neural/prepare.py 866c0b1349e47d42ca4915b8829adb74f367d7b5047bbc333bf7190c67fa8f1c
src/fly_connectome_sim/neural/rule.py 3c80680450c3b73042e332bd7ce8289d7d74d8695c60e7ac19eefd9759d95c44
src/fly_connectome_sim/neural/sensory.py 46ba99fd966e251a3422f77fdd27a78fe45aa45f9fd14e498e3c5e578566f7ac
src/fly_connectome_sim/neural/state.py de3dac9f37f7c12546124383410e1ac0e720459e2f8e636d3fa155dce6a7d220
src/fly_connectome_sim/neural/transmitters.py b1c1b080da44bdeaf498cdce3504134c1cf070b875f84a4007f16002b2956f93
src/fly_connectome_sim/neural/visual.py 50cb4f2a4c60a0d938d8e69cc41ce8544327fb433735db9ba1f337b13c342a33
src/fly_connectome_sim/schemas/__init__.py 2fc8231daedcfd148cae398fd73df982818abb24489436392c140e0c7ba78136
```
