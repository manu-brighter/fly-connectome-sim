# Local image intake, sanitized preview and moderation — prospective design

Status: **All three components and the complete local integration independently accepted**.
Corrections, real browser expiry/cleanup and protocol/security review are complete;
exact intake-source CI remains outstanding. D2 source CI is complete.
See [component evidence](../../experiments/2026-11-10-image-intake.md).
Compose accepted [D1](2026-11-10-image-admission-design.md) and
[D2](2026-11-10-image-decoding-design.md); local D2 acceptance does not replace its CI gate.

## Scope and ownership

One local guest page sends a bounded image; the operator inspects its canonical
pixels and approves/rejects. Approved images remain queued and eventually expire:
**no neural worker is connected in this slice**. No dispatch/started/complete calls,
fake processed status, measured activity, new price source/schema, sale prices,
native/API request, LAN/public endpoint or event-menu invention. The existing
synthetic board and fixture route remain clearly labelled and independent.

New source: `market/image_intake.py`, `market/web/image-{protocol,state,view,main}.ts`,
`viewer/market-image.html`, `viewer/src/market-image-entry.ts`. Narrow edits:
`market/local_server.py`, existing market operator entry/style, Vite/TS includes,
and `scripts/run-market-price-service.py`. New focused Python/browser tests.
Preserve D1/D2/core/frozen helpers/replay/dependencies and existing market behavior.

Extend `create_server(..., *, image_intake: ImageIntake|None=None)`. None retains
all existing routes/assets/auth/body limits and starts no decoder/thread. With the
optional collaborator, reuse the same parser, eight-handler limit, maintenance,
headers and asset loader; do not copy HTTP or price authority implementations.
Only this collaborator owns image bytes/capabilities and asynchronous decode.

All rates/lifetimes/UI choices below are engineering defaults for this loopback
slice, not accepted300-guest capacity or physiological settings. Bind remains
exactly127.0.0.1. Existing HTTP overload still latches the existing price pause;
do not change that behavior or add price transitions for image moderation/faults.

## Startup and coordinator API

CLI adds optional `--image-work-root PATH` under repository `.tools/`; omitted
means unchanged synthetic mode. Create one shared SystemClock for authority,
AdmissionController and ImageDecoder; D1 gets a fresh independent UUID incarnation.
Open D2 on the trusted root before opening the listener; stale scratch, unsupported
Windows or ownership failure refuses startup with a closed error, not a bypass.
Existing operator/view URLs remain; optional third URL is
`/market-image.html#guest=<guest capability>`. Print it only as explicit local startup
output. No new browser launches, network binding or automatic image submissions.

```text
ImageIntake(admission: AdmissionController, decoder: ImageDecoder, clock: Clock)
guest_capability -> str                         # server-owned, never a public DTO
reserve_upload(guest_capability: str) -> Reservation # guest auth + upload bucket + reserve
abandon_upload(id: UUID) -> None
accept_upload(id: UUID, media_type: str, payload: bytes) -> Acceptance
guest_status(id: UUID, status_capability: str) -> ImageStatus # receipt auth + reader bucket + status
charge_operator(diagnostic: bool) -> None        # adapter has authenticated original operator
operator_status(id: UUID) -> ImageStatus
operator_state() -> IntakeState
preview(id: UUID, frame_sha256: digest) -> bytes
moderate(id: UUID, incarnation: UUID, action_id: str, approved: bool) -> ImageStatus
maintain() -> None
begin_stop() -> None
finish_close() -> None
```

Methods use exact scalar types/D1 ID rules; no mutable external metadata objects.
Coordinator exclusively owns its initially empty D1 controller and decoder.
No caller except the HTTP adapter invokes these APIs. Coordinator public methods
authenticate image capabilities; adapter authenticates the original operator token.
No private-map access, exported secret map, duplicate token store or HTTP-selected
role. For an operator image request the adapter calls charge_operator exactly once,
then the corresponding uncharged operation. diagnostic=true is allowed only for
operator state/status GET; preview/moderation use false. Guest upload calls only
reserve_upload for its combined auth/rate gate; status-bearer GET calls only
guest_status, which atomically authenticates, charges and returns that ID's status.
No second charge in downstream methods. Closed/faulted coordinator refuses new
reservation/moderation; diagnostics remain available until server close.
One short coordinator lock precedes D1 calls; never acquire it from inside D1/D2.
Never hold it while body reading, decoding, socket writes or thread joining.

## Capabilities, routes and wire limits

Guest capability is `ig.` plus one service-lifetime token_urlsafe(32) secret, not a
new session per request. All local guest tabs share it; it authorizes upload only.
Each accepted image gets `is.` plus an independent token_urlsafe(32) secret, retained
with its D1 receipt. No public session-creation endpoint or rejected-attempt history.
Each complete image capability is exactly46 ASCII characters: fixed three-character
prefix plus43-character base64url suffix retaining all32 random bytes. Validators
are exactly `ig\.[A-Za-z0-9_-]{43}` and `is\.[A-Za-z0-9_-]{43}`. The dot/length makes
both structurally disjoint from unchanged43-character operator/view/future-primary
tokens and from each other, even with identical random suffixes. No constructor
exclusion set or price-token generation change is needed. Compare full bearer bytes
with constant-time comparison. Mint a status capability before D1.admit, trying at
most4 suffixes against retained status capabilities. Four same-role collisions or
generator failure returns503 capacity and releases only this reservation, with no
admitted image/token. Guest mint failure refuses startup. No unbounded remint loop.
Never put capabilities in paths, queries, logs, errors or arbitrary DOM content.

Original routes continue through original authentication; image guest/status tokens
cannot read price snapshots/events or submit fixtures/primary/pause/resume. Image
routes authenticate separately: original operator token alone is operator; view
and primary tokens are not image-operator credentials. No cross-role fallback.

| Route | Method/role | Body | Success |
|---|---|---|---|
| `/api/images` | POST guest | raw JPEG/PNG1..2097152 bytes |202 Acceptance |
| `/api/images/state` | GET operator | none |200 IntakeState |
| `/api/images/status/<id>` | GET matching status token OR operator | none |200 ImageStatus |
| `/api/images/preview/<id>/<hash>` | GET operator | none |200 exact12288 RGB bytes |
| `/api/images/moderate/<id>` | POST operator | exact JSON keys incarnation,action_id,approved;<=8192 bytes |200 ImageStatus |

Images disabled means these routes/assets are404; no token/authentication changes.
id is a canonical lowercase UUID, hash is64 lowercase hex; wrong route shape404.
No wildcard file serving, original-upload GET, filenames, URLs, multipart or CORS.
Preview content type is application/octet-stream, not a browser image type.
All original JSON POST limits remain8192; only the exact raw-upload route gets the
larger cap and exact image/jpeg or image/png MIME. No MIME parameters/aliases.
GET rejects a nonempty body. Required Content-Length is canonical decimal, bounded
by route limit before int conversion; missing411, oversize413, wrong MIME415.

Keep current2048 request-line/16384 aggregate-header/64-header-count limits,
duplicate sensitive-header rejection, no Transfer-Encoding/Expect, exact Host and
Origin rules, and rejection of query/fragment/percent/backslash/dot paths. POST
requires matching Origin; GET may omit it but any supplied Origin must match.
One total5-second request-read deadline and2-second socket operation limits remain
unchanged, including progress-making peers. Authenticate/rate-check/reserve before
reading a raw body. Header parser's at-most4096-byte read-ahead is not admission.

IntakeError.code is exactly unauthorized,not_found,full,busy,invalid_transition,
idempotency_conflict,wrong_incarnation,rate_limited,invalid_request,capacity,
intake_fault,stopping,closed,cleanup_failed. Map public D1/D2 failures to these;
never expose arbitrary exception names or decoder payloads as HTTP codes.
Other status codes:401 unauthorized (including unknown/pruned status capability),
404 operator-requested unknown/pruned image or missing preview,409 full/busy/
invalid_transition/idempotency_conflict/wrong_incarnation,429 rate_limited,
400 invalid_request,503 capacity/intake_fault/stopping/closed/cleanup_failed. Existing parser/price errors
keep their current mappings. JSON errors are exactly `{error: closed_code}`.
Image JSON replies<=8192 bytes; existing price response ceiling remains65536.
Preserve no-store,nosniff,referrer-policy,CSP and connection-close headers; no cookies.

## Exact DTOs

```text
ImageStatus = {schema:"market-image-status-wire/v1", incarnation:UUID, id:UUID,
 revision:int1..6, status:"accepted"|"queued"|"rejected"|"expired",
 detail:the exact valid combinations below,
 frame_sha256:digest|null, accepted_age_ms:int|null,
 remaining_decode_ms:int|null, remaining_moderation_ms:int|null,
 remaining_handoff_ms:int|null, time_uncertain:bool, preview_available:bool}
Acceptance = {schema:"market-image-acceptance/v1", status_capability:is.token,
 image:ImageStatus}
IntakeState = {schema:"market-image-intake/v1", incarnation:UUID,
 mode:"local-intake-only", worker_connected:false,
 health:"ready"|"stopping"|"faulted",
 fault:null|"clock"|"decoder"|"ownership"|"shutdown",
 receiving:bool, decode_busy:bool, pending:ImageStatus|null,
 receipt_count:int0..512}
```

Every named field is required; reject extras/exact-type violations. No absolute
nanoseconds pass through JavaScript numbers. Age floors `(now-accepted_ns)/1e6`;
remaining time is max0/ceil for original phase deadline minus now, and0 after
terminal status. Integer bounds are0..9223372036855, within JS safe integer range.
If coordinator or D1 clock is uncertain, age/remaining values are null and
time_uncertain=true; never substitute UTC. Status/detail/revision come from D1.
preview_available is true only for the current stored sanitized pending buffer.
Valid status/detail/hash/preview combinations are exactly:

| status | detail | frame_sha256 | preview_available |
|---|---|---|---|
| accepted | decoding | null | false |
| accepted | awaiting_approval | digest | true |
| queued | ready | digest | true |
| expired | ttl_expired | digest | false |
| rejected | decode_failed or decode_timeout | null | false |
| rejected | moderation_rejected or moderation_timeout | digest | false |
| rejected | worker_failed,session_ended or clock | null or preserved digest | false |

All four timing fields are null iff time_uncertain=true; otherwise valid integers,
with all three remaining fields0 for terminal status. IntakeState ready requires
fault=null; faulted requires a nonnull fault; stopping may retain an earlier fault.
Nonready state has receiving=false,pending=null; decode_busy may remain true during
cleanup. Ready state cannot have receiving=true and pending nonnull together.
Pending, when present, is accepted/queued and matches IntakeState.incarnation.
Unexpected D1 active/processing/processed state faults this intake rather than
publishing a synthetic native outcome. Browser parsers reject those states too.
No DTO includes raw upload, moderation secrets, guest token, source filename,
observer counts or scientific claims. Receipt capabilities appear only in202.

## Acceptance, original deadlines and bounded asynchronous work

reserve_upload authenticates its guest token before creating state, then reconciles
maintenance and rejects closed/stopping/faulted state before any bucket charge.
When healthy it charges the upload bucket once, checks decoder busy and calls
D1 reserve, which grants the single reservation with its original5s limit.
Use its ID locally; do not return it as accepted before complete body receipt.
Read body outside coordinator lock with unchanged request deadline; hash exact
bytes, then accept_upload rechecks reservation/current incarnation before D1 admit.
Admit fixes accepted_ns and original10/60/300s decode/moderation/handoff deadlines.
It must not reuse request-start time or renew any deadline on response/retry.
On read/hash/admit failure abandon only that reservation; never cancel a newer ID.
Maintenance may already have expired it; not_found cleanup is harmless.

After bounded capability mint succeeds, admit and attach that capability atomically
under the coordinator lock, then start one background decode
task, passing that exact accepted receipt's ID/hash/size/decode_deadline to D2.
No ThreadPoolExecutor/backlog: one task slot, fail busy while its prior task/cleanup
still runs even if D1 already released the pending slot. The202 contains CURRENT
D1 status, which may already be rejected if thread startup failed. A lost202 leaves
a real accepted receipt; client reports unknown and does not automatically resubmit.
There is no upload idempotency/retry endpoint in this slice. Task-start failure
fences intake;202 still returns its allocated capability and truthful terminal
receipt. Pre-admit capability failure has no accepted receipt and returns503 capacity.

Decoder runs outside coordinator lock. On return reacquire it, synchronize D1,
check captured incarnation/ID and shutdown generation, then call D1.decoded BEFORE
publishing bytes. Only success/current awaiting_approval adopts exact RGB/hash;
late/expired/stopped output is discarded. There is no result mailbox beyond this
one task. Decoder cannot invoke coordinator/D1 itself. D1 expiry continues every
100ms maintenance tick while the task runs. Moderation calls D1.moderate under the
same coordinator lock; original60s includes decode, equality rejects. Approval
sets queued/ready; no worker dispatch occurs, and300s equality expires it.

malformed_image/unsupported_format/geometry/mode/multiple_frames/source_mismatch/memory_limit/
child_failed/monitor_stalled map to D1.decode_failed after maintenance. D2 timeout
first runs maintenance so elapsed original10s produces decode_timeout. Unexpected
early timeout is decoder fault, not permission to extend it. D2 cancellation during
shutdown leaves session_ended; cancellation otherwise is decoder fault.
closed/busy/invalid_request/unsupported_platform/child_protocol are integration or
decoder faults, not guest-file diagnoses. ownership/cleanup_failed fence intake
as ownership; clock fences as clock. Fencing sets coordinator fault, cancels its
task, discards pixels and calls D1.stop(worker_failed) unless D1 already clock-faulted
or stopping. Here worker_failed means the image decode pipeline, not a neural run.
Do not manufacture a D1 clock fault; if its own clock later fails, preserve it.
No image fault invokes synthetic price actions. No automatic decoder recreation.

## Storage, capability pruning, rate limits and races

This slice retains exactly ONE canonical pending buffer (12288 bytes). Active and
last-completed buffers are absent because no simulation occurs. On rejection,
expiry, fencing or shutdown discard it immediately. Preview route checks current
ID/hash/state under lock, takes one bounded detached reference and returns it;
an already authorized in-flight response may finish after expiry. No new fetch is
authorized afterward; this is not a promise to erase bytes already shown.
Operator UI clears its canvas on state change. No guest preview is served, even
after approval. Browser converts exact raw RGB to a64×64 RGBA canvas and enlarges
it without reading the original file. Before painting, verify the rgb-input/v1
prefix+RGB SHA256 equals the current pending frame hash; suppress superseded work.
No PNG/JPEG re-encoding or blob URL needed.

Raw upload has one parent payload<=2MiB plus existing parser buffer<=2MiB+4096
temporarily; release reader buffer after body extraction and all payload references
after task completion. Copies inside accepted D2 stay governed by D2. No raw bytes
are stored with status. Preview response/header/canvas copies are separately finite.
Status map has at most512 entries, one capability per accepted D1 receipt and no
rejected-attempt records. A maintenance pass removes entries whose D1 status is
not_found after15-minute retention; never evict a retained receipt for capacity.
No new admission while pruning reconciliation is incomplete. Only one pass over
<=512 IDs per tick; no unbounded events, upload IDs, sessions or error logs.

Three fixed token buckets use the shared monotonic clock: upload requests capacity1,
refill1 per10s; operator image requests capacity120/refill2 per second; status-token
GET requests capacity120/refill2 per second globally. Start full. Consume after
successful role authentication and before reserve/body/action, only in the public
gate methods above. No per-token/IP bucket allocation. Each request passing its
gate consumes exactly one token, including later body/action failure; exhausted429
consumes none. Authentication failure consumes no token and creates no state.
Original price routes never use these buckets.

guest_status first checks the supplied exact token against its retained ID, then
reconciles D1 maintenance/pruning and rechecks that mapping under the same lock
before charging/reading. A pruned/unknown/mismatched token gives401, not an operator
404. Operator status uses trusted operator authentication then its operator bucket;
unknown/pruned ID gives404. No helper infers a role from an HTTP body/query field.
Already-due maintenance may expire existing state during either gate, but failed
authentication allocates no receipt/bucket/history.

On clock fault, freeze existing bucket balances at their last valid values: no UTC,
new clock, refill or reset. Only authenticated diagnostic state/status reads are
allowed, spending one remaining whole token from the corresponding frozen bucket.
After exhaustion they receive429 indefinitely for this incarnation. Diagnostics
retain bounded existing capabilities/receipts without age pruning when no trusted
clock is available; do not claim their retention deadline was verified. Mutating
or preview gates fail503 intake_fault without a bucket charge. Non-clock faults
may refill diagnostic buckets only with valid clock samples. Stopping allows only
diagnostics and uses the same finite accounting; new actions fail503 stopping.
Successful finish_close sets closed: every public request gate/operation then
raises closed without clock/refill/auth state allocation. begin_stop/finish_close
remain idempotent after closure; retained cleanup failure does not mark closed.

## UI, assets and shutdown

Add the guest Vite entry to the immutable asset allowlist ONLY when enabled;
preserve the original reachable-assets boundary otherwise. Guest fragment is read
once/removed before network use; capabilities remain in closure memory, never
localStorage/sessionStorage/cookies. File chooser advertises JPEG/PNG/2MiB and sends
raw File bytes; do not render the original or send its name. One current receipt
per tab, serial fetches,2s status polling,5s abort deadline, bounded8192-byte JSON
and exact12288-byte preview reads. Enforce caps while consuming response streams,
not after unbounded text/arrayBuffer allocation; abort extra bytes. No automatic
upload retry after abort/disconnect.

Existing operator board probes the optional state route once:404 hides the image
pane. Otherwise add a separate pane with canonical preview, approve/reject and
explicit “Lokaler Bildtest — Simulation nicht verbunden”. Its independent request
state/AbortController must never delay or mutate price polling/ACK/control state.
Image mutations are disabled while image status is stale>=5s or disconnected.
Maintain a verified displayed tuple `(incarnation,id,frame_sha256)` only after
exact12288-byte/hash verification AND adoption of those pixels into the current
canvas. Approve (including explicit retry) requires healthy ready intake, fresh
metadata, accepted/awaiting_approval with preview_available=true and exact current
tuple equality, with no superseding generation or pending mutation. A pending/
failed preview cannot enable approve. Clear tuple and canvas on identity/hash/
incarnation change, stale/disconnected metadata, preview failure, terminal/queued
state or mutation start. Preview completion never refreshes metadata freshness.
Reject may be enabled without preview, but still requires healthy/fresh
accepted/awaiting_approval and no pending mutation. These are UI workflow gates;
the authenticated operator's direct HTTP authority is unchanged.
Moderation retries reuse the same action_id/approval only on explicit retry; server
D1 determines idempotency. Serial generations suppress late replies/old previews;
incarnation change clears all image state. Missing/revoked status becomes unknown/
unavailable, never processed. Existing board prices and synthetic banner remain.
Status replies must match requested id and established incarnation. Moderation
replies must match requested id/incarnation and the current UI generation/target;
an older reply cannot replace a newer pending item. The202 may establish its newly
minted id/incarnation only for the current upload operation. Validate all DTO
combinations above before adoption; a scalar-valid contradictory reply is rejected.

begin_stop is idempotent: mark stopping/advance callback generation, set cancellation,
call D1.stop(session_ended), revoke preview and refuse new image actions. Invoke it
before server_close waits for handlers; receiving handlers release only their own
reservation. finish_close joins the one decoder task up to25 real seconds, then
calls D2.close only after that task is idle; D2 itself proves exact owned cleanup
or retains its faulted context. It must never call
busy decoder.close or drop faulted D2's retained root lock/handles. A live task or
failed cleanup produces a controlled shutdown failure, retains owned context and
returns no success; late callback can release payload but cannot republish pixels.
The decode task is daemonized solely so a failed process exit cannot hang forever;
normal shutdown still requires join/owned cleanup, not daemon abandonment. CLI
reports failure/nonzero on unconfirmed cleanup; OS-exit Job cleanup is not a
successful application receipt. Stale D2 scratch still blocks the next startup.
Close the independent authority/server resources through their original cleanup
path; do not release D2 ownership as a side effect. OS-call stalls remain an honest
limit, not a guaranteed25s physical process termination.

## Required acceptance evidence

Test exact raw-route limits/roles/Host/Origin/read deadline, authentication-before-
body/reserve, global buckets/capacity, slow/full bodies and reservation races;
actual owned D2 decode with a safe generated fixture; accept/decode/preview/approve/
reject/expiry without processed, original10/60/300s boundaries and stale callback;
pixel/hash binding, private preview, bounded capabilities/pruning and lost202;
fatal decoder/clock/shutdown/cleanup races with preserved ownership; old Stage-C
routes/body limits/presence/price behavior unchanged. Browser checks cover fragment
removal, strict wire parsing, canvas pixels, explicit no-worker copy, offline/stale
controls and late reply rejection. No guest photos/native run or sale activation
is needed. Public-event security, real worker telemetry and native-price admission
remain separately reviewed later slices.

Focused interface regressions: use public guest/operator paths for the same ID;
failed/pruned authentication spends no token, accepted request spends exactly one;
bad-clock diagnostics spend only frozen finite credits and cannot refill from UTC;
closed mappings and exact D2 error names. Force identical guest/status/price/primary
random suffixes, future primary creation, four status collisions and generator
failure. UI tests must cover delayed/failed/mismatched/superseded preview, changed
pending ID, metadata becoming stale during hashing, reject without preview,
approval retry gating, wrong response identity and contradictory DTO combinations.
