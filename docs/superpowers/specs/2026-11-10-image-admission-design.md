# Local image admission lifecycle — prospective D1 design

Status: **implemented and independently accepted locally; source publication/CI pending**.
See [actual evidence](../../experiments/2026-11-10-image-admission.md).
Stage-C source `b2eda225` passed all four CI42741755078 jobs. Independent protocol
review accepted this contract after clarifying receipt timing, contradiction
precedence and index overflow. This is the first bounded Stage-D slice of the
[market plan](../plans/2026-11-09-live-drink-market.md), following the
[local synthetic authority](2026-11-10-local-price-board-design.md).

## Purpose and scope

Establish a finite, honest image lifecycle before adding HTTP upload, decoding,
moderation UI or native work. Product files are only `market/image_admission.py`
and `tests/market/test_image_admission.py`. Reuse public `Clock`, `ClockSample`
and `SystemClock` from `market.price_service`; do not edit that authority.
Preserve the frozen `scripts/market_live_buffers.py`, packaged simulator, replay
formats, dependencies, old runners and existing artifacts.

D1 stores metadata, not pixels, filenames, temporary files, credentials or model
measurements. It starts no process/server, performs no decoding/native/API work,
activates no price and grants no public/LAN authority. Later trusted adapters must
verify actual bytes and native receipts; these metadata checks cannot attest them.
The module is a lifecycle/deadline gate, not another image FIFO or simulator.

User requirements: one finite queue; reject new work when full; at most 300000
real milliseconds from accepted upload to actual simulation handoff, including
decode and moderation; expired images must never be handed off late. These
requirements do not guarantee successful handoff when a worker fails.

All following operational values are **engineering choices**, not user-agreed
capacity or biologically validated settings. There is one receiving reservation
OR accepted pending image, plus at most one active image. Reservation lifetime is
5 s. Accepted image deadline is 300 s. Decode deadline is 10 s from acceptance;
manual approval deadline is 60 s from acceptance, including decode time. A start
receipt is due within 10 s of dispatch. An exposure comprises eight consecutive
500-model-ms observations. Later preprocessing is planned as 64×64 RGB uint8;
D1 validates its declared version and digest only. No duration promises a response.

## Exact types and constants

Use frozen dataclasses; snapshots/returns contain no mutable internal collections.
`MAX_NS = 2**63-1`. Times are absolute shared-host perf-counter nanoseconds, true
Python integers in `[0, MAX_NS]`, excluding bool. Counts/indices have the same
integer range; reachable receipt revisions are 1..6 (admit, decode, approve,
dispatch, start, terminal), not an unbounded polling counter. Insufficient headroom
for controller-created deadlines (now plus 5, 10, 60 or 300 seconds) gives capacity
before the requested transition mutates state; already-due maintenance and fault
fences still apply. Worker-supplied index headroom follows semantic receipt safety
below, not this controller-deadline capacity rule.
Digest is exactly 64 lowercase hexadecimal characters. UUID is canonical lowercase
36-character UUID spelling. Operator action IDs match ASCII `[A-Za-z0-9_-]{1,64}`.
Enums below reject unknown values. Dataclass instances must be their exact declared
type; reject subclass/coerced dictionaries. All string fields, including UUIDs,
digests, action IDs, enum values and versions, require exact built-in str; numeric
fields require exact built-in int and flags exact built-in bool. Completion indices
require exact built-in tuple of at most eight exact bounded ints: reject lists,
subclasses and arbitrary iterables before semantic checks. Exactly eight entries
and their continuity are semantic completion checks below. Public methods are keyword-only except
the constructor. No arbitrary policy/configuration dictionaries are accepted.

```text
RESERVATION_NS = 5000000000
PENDING_NS = 300000000000
DECODE_NS = 10000000000
MODERATION_NS = 60000000000
START_RECEIPT_NS = 10000000000
RETENTION_NS = 900000000000
CAPACITY = 512
MAX_ENCODED_BYTES = 2097152
EXPOSURE_OBSERVATIONS = 8
PREPROCESSING_VERSION = "market-rgb64/v1"

Status = "accepted" | "queued" | "processing" | "processed" | "rejected" | "expired"
Detail = "decoding" | "awaiting_approval" | "ready" | "dispatching" |
         "processing" | "completed" | "decode_failed" | "decode_timeout" |
         "moderation_rejected" | "moderation_timeout" | "ttl_expired" |
         "worker_failed" | "worker_outcome_unknown" | "session_ended" | "clock"
Fault = None | "clock" | "worker_failed" | "worker_outcome_unknown" | "session_ended"

Reservation(id: UUID, incarnation: UUID, reserved_ns: int, expires_ns: int)
Receipt(id: UUID, incarnation: UUID, source_sha256: digest, encoded_bytes: int,
        accepted_ns: int, deadline_ns: int, decode_deadline_ns: int,
        moderation_deadline_ns: int, status: Status, detail: Detail,
        frame_sha256: digest|None, preprocessing_version: str|None,
        worker_session: UUID|None, dispatch_id: UUID|None,
        dispatched_ns: int|None, started_ns: int|None,
        first_observation_index: int|None, completed_ns: int|None,
        terminal_ns: int|None, revision: int, time_uncertain: bool)
DispatchPermit(id: UUID, incarnation: UUID, dispatch_id: UUID,
               worker_session: UUID, frame_sha256: digest,
               deadline_ns: int, exposure_observations: int)
StartReceipt(id: UUID, incarnation: UUID, dispatch_id: UUID,
             worker_session: UUID, frame_sha256: digest,
             started_ns: int, first_observation_index: int)
CompletionReceipt(id: UUID, incarnation: UUID, dispatch_id: UUID,
                  worker_session: UUID, frame_sha256: digest,
                  observation_indices: tuple[int, ...], completed_ns: int)
AdmissionSnapshot(incarnation: UUID, fault: Fault, stop_required: bool,
                  reservation: Reservation|None, pending: Receipt|None,
                  active: Receipt|None, terminal_count: int,
                  reserved_receipt_slots: int)
```

`Receipt.id` is its former Reservation.id, minted internally with uuid4. Collision
with any retained ID is `capacity`, not replacement. Caller cannot supply new IDs.
Dispatch IDs are also internally minted. No bearer token is stored here. The future
adapter creates a separate unguessable status capability; a public UUID alone is
not authorization. Incarnation is supplied once to the constructor, unique for each
new controller process. Strings returned in `detail` describe state, not free text.

`AdmissionError(code)` has exactly: invalid_request, not_found, invalid_transition,
idempotency_conflict, wrong_incarnation, wrong_worker, wrong_dispatch, wrong_frame,
full, capacity, clock, stopped. It exposes no arbitrary user payload in messages.

## API

```text
AdmissionController(incarnation: UUID, clock: Clock|None = None)
reserve() -> Reservation
cancel_reservation(id: UUID) -> None
admit(id: UUID, source_sha256: digest, encoded_bytes: int) -> Receipt
decoded(id: UUID, frame_sha256: digest, preprocessing_version: str) -> Receipt
decode_failed(id: UUID) -> Receipt
moderate(id: UUID, action_id: str, approved: bool) -> Receipt
dispatch(id: UUID, worker_session: UUID) -> DispatchPermit
started(receipt: StartReceipt) -> Receipt
complete(receipt: CompletionReceipt) -> Receipt
stop(reason: "worker_failed" | "worker_outcome_unknown" | "session_ended") -> AdmissionSnapshot
maintain() -> AdmissionSnapshot
status(id: UUID) -> Receipt
snapshot() -> AdmissionSnapshot
```

One internal lock serializes all clock reads and state changes. Validation of exact
types/bounds occurs before entering mutation logic. Under lock, sample/check clock,
perform due expiry/pruning, then apply the operation. Invalid syntax does not change
state; a valid operation may discover due expiration before rejecting its requested
transition. Every actual receipt change increments its revision exactly once;
initial revision is 1. Polling, identical retries and countdowns do not increment.
For non-worker operations, before ordinary state checks a retained identical
successful operation returns its defined retry result; differing retained payload
conflicts. Worker receipts use the more specific ordered branches below; generic
idempotency must not intercept their safety checks. Expiry and fault fencing
precede retry lookup. Reserved_receipt_slots counts reservation plus
accepted pending plus active; terminal_count counts retained terminal receipts.

## Reservation, acceptance, decode and moderation

Reserve requires a healthy controller, empty pending/reservation slot and available
receipt capacity. It reserves that slot before future HTTP body reading; it is NOT
an accepted image. At `now >= expires_ns` it is removed. Cancel matches the current
reservation; unknown/expired ID is not_found. No tombstones for unaccepted requests.
Cancellation performs no accepted receipt transition. A retry after cancellation
returns not_found; it cannot release a newer reservation.

Admit requires the current unexpired reservation, a verified bounded complete body
and declared digest/byte length `1..MAX_ENCODED_BYTES`. D1 verifies metadata, not body.
It samples `accepted_ns=now`, fixes `deadline_ns=now+PENDING_NS`, decode deadline
`now+DECODE_NS`, moderation deadline `now+MODERATION_NS`, consumes the reservation
and creates status accepted/detail decoding. Every later phase retains these exact
timestamps. Reservation time is separate and is not silently called acceptance.

Future HTTP contract: return 202 only after admit succeeds, with accepted-pending-
checks wording, status capability and remaining lifetime. Reservation/full/body-read
failure is never 202. Decode begins only after acceptance; neither decode completion
nor approval starts a fresh five-minute clock. Lost HTTP replies cannot authorize
automatic replay of an old body as a newly accepted image.

Decoded requires accepted/decoding before its deadline, a frame digest and exactly
PREPROCESSING_VERSION. It records them and changes detail to awaiting_approval.
Decode failure terminally rejects with decode_failed. At decode deadline equality,
maintenance rejects with decode_timeout; a late successful decode cannot revive it.
Moderation only operates on awaiting_approval. `approved` is a true bool; false
rejects with moderation_rejected, true sets queued/ready. There is no auto-approval.
At moderation equality, accepted work rejects with moderation_timeout. Decode time
is included in that 60 s. No pending image is published or dispatched before approval.
All terminal transitions free the pending slot but retain their bounded receipt.

## Handoff, receipt uncertainty and completion

Dispatch requires queued/ready, no active image, and `now < deadline_ns`. The first
dispatch binds the controller to one worker_session; a different worker requires
a new controller incarnation and is wrong_worker. It records dispatched_ns and
dispatch_id, changes detail to dispatching and returns the fixed permit. The item
still occupies the pending slot. There is no additional input IPC queue.

The future worker checks for the single dispatched permit between observations,
including after an in-flight black observation. It must validate the original
permit deadline in the same shared clock domain immediately before first image
observe and emit the start receipt before entering that observe; never wait for
the first image observation to finish. A parent check alone is insufficient.
At `worker_now >= deadline_ns` it must discard the image. Shared clock implementation/
identity and bracketed startup handshake are future integration prerequisites, not
established by D1. Never replace this deadline with IPC receipt or model time.
The ten-second dispatch-to-receipt budget accommodates the measured Stage-B
4.203-second black observation plus delivery margin. It is an engineering
supervision threshold, not a guaranteed runtime upper bound, new image TTL or
held-ready-boundary requirement. A longer stall still fails closed. D1 does not
establish this future D3 scheduling/receipt behavior and needs no native run.

The first successful Started transition requires matching retained
ID/incarnation/dispatch/worker/frame, detail
dispatching, `dispatched_ns <= started_ns < deadline_ns`, and `started_ns <= now`.
It also requires `now < dispatched_ns+START_RECEIPT_NS`. On success it moves pending
to active and sets processing, started_ns and first observation index. A receipt
can arrive after the original image deadline if its actual started_ns was before
it and the ten-second receipt deadline has not elapsed. Never confuse receipt time
with handoff time. A first index of MAX_NS-7 has valid headroom for eight indices.
First indices MAX_NS-6..MAX_NS are syntactically within range but cannot describe
eight bounded indices: for a current nonterminal worker receipt, atomically apply
worker_outcome_unknown/stop_required and terminal rejection, never capacity,
invalid_request or a partial start. Terminal and unknown-ID branches below retain
precedence; this semantic check cannot fault other work through a terminal conflict.
The receipt budget applies only while dispatching: an exact successful start retry
after processing began is not re-expired merely because ten seconds have passed.

For `started` and `complete`, apply exactly this branch order:

1. Exact dataclass/primitive syntax and absolute integer bounds. Malformed fields
   fail invalid_request without mutation. Future timestamps are semantically
   inconsistent, not syntax failures. The later IPC adapter must stop its owned
   worker on malformed messages; D1 does not infer authenticity from their shape.
2. Under lock, clock/maintenance/fault fence. A due receipt timeout therefore
   latches unknown before the requested call; that call raises stopped. Existing
   faults likewise raise clock/stopped; status reads reveal the terminal result.
3. Retained accepted-ID lookup: unknown/pruned/reservation-only ID is not_found.
4. Terminal record: exact recorded successful retry returns CURRENT terminal
   Receipt; differing payload for that recorded operation is idempotency_conflict;
   an unrecorded operation is invalid_transition. None can fault another live item.
5. Nonterminal safety consistency BEFORE generic successful-operation lookup.
   For current dispatching/processing IDs, wrong incarnation/session/dispatch/hash,
   future or inconsistent timing, first-index-plus-seven headroom failure,
   inconsistent completion indices, or completion
   before a confirmed start latch worker_outcome_unknown and stop_required.
   Any StartReceipt differing from a previously successful start also does so,
   even if its fields could otherwise describe a plausible second start. One
   exposure cannot have two starts. Return that item's terminal rejected Receipt;
   reject all other unfinished accepted items under the same stop, retaining their
   already confirmed fields. A receipt for a known accepted/decoding,
   awaiting_approval or queued/ready item has no authorized dispatch identity:
   it is also unknown/stop, not proof that the unapproved input was never observed.
6. Exact recorded successful worker retry returns CURRENT Receipt without change.
   These checks handle valid duplicate starts while processing. No current-worker
   contradiction may fall through to generic idempotency_conflict instead.
7. Apply the ordinary first-start/first-completion transition described here.

Thus terminal conflicts preserve history and other work, whereas contradictory
claims about unfinished work fence the worker. No receipt can resurrect an item.

While dispatching, passage of the image deadline alone does not establish that no
handoff occurred. At the ten-second receipt deadline, latch worker_outcome_unknown,
set stop_required, reject unfinished accepted items with that detail, and refuse
new work. Future ownership must stop the worker; D1 cannot claim it did so. Late
start receipts cannot resurrect the rejected image. It must never become processed
merely because bytes were sent. Do not report conclusive ttl_expired for this case.

Complete requires the same active identity tuple, exactly eight consecutive indices
`first_observation_index..first_observation_index+7`, and
`started_ns <= completed_ns <= now`. Future D3 must validate all eight actual
500-ms observations before calling complete; D1 only validates this finite receipt.
It sets processed/completed, completed_ns, terminal_ns=now and frees active. The
image TTL no longer expires legally started processing. No D1 active timeout is
invented: later worker supervision must call stop on failure. Active storage remains
one bounded item even if supervision is absent. Black intervals belong to D3, not D1.

Stop latches its first reason, sets stop_required, drops a receiving reservation
and terminally rejects all unfinished accepted records with that reason. Existing
terminal results remain unchanged. Repeating stop does not rewrite them. Recovery
requires a new controller; there is no resume or worker replacement method.
All terminal failure transitions preserve any confirmed started_ns/first index,
frame/dispatch identity and other already recorded fields. Rejected after a
confirmed start means incomplete/failed processing, not that no input was observed.
Null started_ns after a dispatch means unconfirmed, not proof it never started.

## Expiry, bounded history and idempotency

Each operation expires in this order: receiving reservation; decoding timeout;
pending moderation timeout; queued/ready total TTL; dispatch receipt timeout;
terminal pruning. Delayed maintenance uses current sampled time as terminal_ns;
records must never imply maintenance ran exactly at their deadline. Accepted work
that reaches total TTL despite delayed maintenance retains the more specific
earlier decode/moderation timeout; only queued/ready becomes expired/ttl_expired.

CAPACITY is the maximum total receipt slots: terminal + accepted pending + active
+ receiving reservation <=512. Reservation reserves its future terminal space;
terminal conversion never needs extra capacity. Retain terminal receipts until
`now-terminal_ns >= RETENTION_NS`, then remove them; subtraction avoids overflow
when an active item finishes near MAX_NS. Reserve/admit/dispatch require headroom
for the deadlines they create, otherwise capacity before mutation. Full pending gives full;
otherwise exhausted history gives capacity. Never evict a younger receipt to admit.
Snapshot returns at most two accepted live records and one mutually exclusive
reservation; status returns one retained accepted record. An absent/pruned/unaccepted
ID is not_found, not an invented rejection or a new image. No infinite ID tombstones.

For each retained accepted ID, retain only fixed operation fingerprints/results:
admit payload, successful decoded payload, one moderation action/payload, dispatch
permit, successful start receipt, successful completion receipt, decode-failure
marker. This is at most seven fixed slots, not arbitrary action history. Identical
retries return CURRENT receipt (dispatch returns its original permit); they never
restore an old state or renew a deadline. Changed payload for the same completed
non-worker operation is idempotency_conflict; worker receipts follow the ordered
safety/terminal branches above. A different moderation action after a recorded
decision is invalid_transition; same action with changed approval conflicts.
An operation never successfully recorded before terminal status cannot be retried
into success. Duplicate dispatch permits returned after terminal status convey no
new validity; downstream must honor their original deadlines/session/one-use ID.
No idempotency is promised after pruning or across process restart.

## Clock faults and restart truth

Default clock is SystemClock; call sample() under the lifecycle lock. Require an
actual ClockSample and a bounded true-int monotonic_ns no smaller than the last
valid sample. UTC is unused metadata, never deadline arithmetic. Clock exception,
invalid sample or regression latches clock; refuse further mutations, clear live
reservation, reject unfinished accepted records with detail clock using the last
valid timestamp and time_uncertain=true, and set stop_required. If the first sample
fails there can be no accepted records. Do not invent a current time or repair from
UTC. Existing terminal records remain intact. Faulted status/snapshot/maintain
return diagnostic state without further clock reads or pruning; repeated stop also
returns that unchanged diagnostic snapshot. Other calls raise
clock (or stopped for a non-clock stop). Future timestamps in current worker
receipts use the semantic unknown/stop branch; terminal differences conflict and
unknown IDs remain not_found. They never move local time. Metadata errors do not attest producer
trust and must be handled by the later worker owner.

Storage is deliberately in-memory and process-local. Restart uses a new incarnation
and loses this history. The future adapter must mark an old receipt session ended/
unknown rather than claim processed, requeue it, or pretend durable status exists.
No D1 behavior resets the independent durable price state or real-time cooldown.

## Required validation evidence

Test concurrent slot/capacity contention; reserve equality and stale cancellation;
admit timing and immutable deadlines; accepted/queued/processing/processed sequence;
decode 10 s and moderation 60 s equality; queue TTL at one ns before versus equality;
delayed IPC final check; legal receipt after 4.203 s; ten-second equality/uncertainty;
late actual start versus a timely start received after image TTL within the budget;
current-active contradictory duplicate starts versus terminal conflicts, including
otherwise plausible different starts; exact retries, wrong/pruned IDs, unsolicited
receipts for known pre-dispatch items and timeout-before-retry precedence;
wrong identity/hash/worker, future receipts and completion before confirmed start;
exactly eight contiguous completion
indices, no early processed status, completion after TTL; every duplicate/conflict;
terminal nonresurrection; capacity reservations, 15-minute pruning and missing IDs;
deadline/index headroom overflow, exact primitive/subclass/list rejection and
reachable revision bound <=6 without manufactured enormous counter loops;
detached snapshots; clock failure/regression
with diagnostic reads; stop/restart scope. Tests use fake clocks and metadata only.
They must not claim pixels were decoded, native observations ran or public uploads
are safe. Record actual test commands/results later; no passes are claimed here.
