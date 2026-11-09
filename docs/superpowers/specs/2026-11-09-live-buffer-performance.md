# Passive-cell buffering and image admission — bounded performance protocol

Status: independently accepted prospective protocol. No implementation or new run.

## Purpose and accepted boundary

The [fixed-input comparison](../../experiments/2026-11-09-drive-input-comparison.md)
establishes a narrowly scoped price/timing-sensitive result for the unchanged
continuous motor driver. This next experiment measures the existing engine with
a passive 256-cell observer, bounded rolling memory and one pending image. It
does not repeat an independent image-sensitivity claim, train the model, activate
prices, implement public uploads or qualify a 12-hour event.

User decisions remain: 10–20 drinks, 50–300 guests, usually 6–8 hours with shorter
or roughly 12-hour exceptions; slower-than-real-time computation is acceptable.
Favorites and quiet phases are permitted, all drinks must remain technically
selectable. An accepted image may wait at most five real minutes before model
handoff. A full finite queue rejects further admissions. Expired images must
never be shown late; worker failure cannot guarantee successful delivery.

## Fixed engine, cohort and input schedule

Use one fresh existing `FlyEngine.from_prepared_graph()`, no restore/forks, no
learning or external DAN, normal passive dynamics, no qualification/pathway detail.
Construct the unchanged `build_header(engine.identity(), runtime_directory)` once.
Bind its complete static content and canonical SHA256 to the run metadata. It
selects exactly 256 cells using the existing source-ID order/stride and includes
at most 512 static topology edges and nullable measured soma positions. Its source
and graph/annotation identities remain intact; topology is not measured transmission.
Install the header's ordered model indices once at model time zero with the
existing `configure_cell_observer(indices, callback)` API. Header construction
and engine startup count toward the total resource budget and are timed separately.

Run exactly 120 observations of 500 model ms: 60 model seconds, 6000 original
10-ms bins, one initial and one final neural checkpoint, 122 journal events.
Every scheduled interval advances, including explicit RGB uint8 black. Each
observation emits its original 50 callback bins, a completed snapshot and five
nonoverlapping 100-model-ms sums. These are model-time windows, not a 10-Hz
real-time display promise. Snapshot readiness and wall gaps are measured separately.

Use the already known 64×64×3 quadrant A, its complement B and explicit black
from the frozen input-comparison helper. Their logical RGB hashes remain:

- A: `7c58398da961353df4ef0040261541e17bcaae7467a92a6395a0eb4f4b9d81be`.
- B: `831971b6bf50a21b29e9a369c84669aeffa3e90fd6a10278780eab05a0a34e30`.
- Black: `aa5f1e84bc3d595d7cfa5f56d794840c0c55e6b67e5bc7a0fa976f9030e93448`.

Phases are fixed at model times 0–20s, 20–40s and 40–60s. They control only this
benchmark's input schedule, never the timing of price proposals. Carry the same
`continuous-motor-drive/v1` instance/session across all phases, unchanged binary
mapping, support requirements, price function and guards. Use the same 20 drinks,
400–700 Rappen bounds, 50-Rappen price grid and 5000-ms delivery freshness;
configuration SHA256
`c02ca9be4db5198b46e718116ff80c169aa3d051f29ff7703d27f1f4fd5315c5`.
Input changes do not reset a supported partial path. Report proposals, partials,
resets and observed coverage, without a new minimum-proposal or variety gate.

## Bounded callback memory and exported measurements

Use a new external sink, never extend the old 10-second cell writer/parser. Its
count storage is a fixed NumPy `uint8[1000,256]` ring. Fixed `int64[1000]` arrays
hold observation index, bin index, start tick and end tick: 288000 owned array
bytes in total. Scalar counters and one bounded export are additional, declared
memory, not included in that exact array-byte figure. No growing bin/history list.

Validate the complete callback before changing state: exact fields, true Python
integer indices/ticks/counts, 256 counts in cohort order, contiguous original
100-tick bins, observation/bin sequence and nonnegative bounded int64 clocks.
Each count must be between zero and its bin's tick duration (at most 100), matching
the old validator rather than introducing a new activity threshold. Check before
the uint8 cast. Invalid callbacks terminate the attempt; the engine may already
have advanced partially, so there is no drop, repair or retry.

The callback only validates/copies into fixed storage and updates bounded counters
and timing accumulators. No rendering, file/network operations or checkpoint work
inside it. Measure sink-body time separately from engine-side callback preparation;
do not call that value the entire observer overhead. Engine compute/kernel timing
and end-to-end observation/snapshot intervals remain separately visible.

After each observe, copy only its 50 completed bins and aggregate five 10-bin
windows with at least uint16 sums. Record those bounded raw bins and aggregates
with the existing population/motor telemetry in the new benchmark journal. The
finite audit file is separate from rolling runtime memory; no multi-hour in-memory
collector is introduced. Each export is detached from future ring overwrites.

At every observation boundary, valid length is min(total bins,1000), write position
is total bins modulo1000 and eviction count is max(total bins−1000,0). Final values
must be 6000 received,1000 retained,5000 evicted. Define the final hash in the new
version contract using dtype, shape, valid length, write position and chronological
index/tick/count bytes, so an independent audit can reconstruct it exactly. Timing
accumulators are not scientific cell counts. Preserve exact original bin timing;
never interpolate missing measured spikes.

Cross-check selected-cell counts against original per-bin population telemetry:
fully represented groups match exactly per bin; selected KC subsets cannot exceed
their corresponding per-bin group counts. There are no whole-brain counts per
bin. Sum the unique selected-cell union over all 50 bins and compare it with the
existing interval `total_spikes`, required for every benchmark observation. Do
not invent per-bin global counts or sum overlapping groups as if disjoint. The
passive observer has no motor authority.

## Fixed admission exercise and five-minute expiry

The small admission state holds at most one active and one pending identity; it
does not retain an unbounded completed/rejected history. This is a synthetic
admission exercise with known frames, not an upload endpoint, decoder or service.
All real monotonic timestamps are true integer milliseconds; clock regression
or invalid input fails rather than shortening a wait. No CLI clock override.

Each request has a true integer sequence in1..2^63−1, strictly increasing within
this admission session. Keep one high-watermark, advancing it even when a valid
new request is rejected as full. An already used/lower sequence is never admitted
again; it cannot replace, revive or rearm an entry. Frame identity is separate:
the same frame can later be admitted under a new sequence. This bounded in-process
contract is not durable restart deduplication for a future public service.

After engine/header setup, use these fixed transitions:

1. Admit A (sequence1) and hand it off immediately before the first observe of phase1.
2. Immediately after that first completed500-ms observe, admit B (sequence2).
3. At that same after-observe point, offer sequences3/4/5 using A/B/black respectively;
   each must be rejected as `full`, without replacing B or changing its deadline.

At phase 2, finish A. Recheck B at the actual first following observe boundary:
age <300000ms permits handoff; age ≥300000ms expires and removes it. Immediately
after the first completed observe of phase2, including a black fallback, admit C
(sequence6, explicit black) into the pending slot for phase3. At phase3, finish B
if it was active and apply the same actual-boundary deadline check to C. Finish C
at the end if active. No admission work occurs between a handoff deadline check
and its immediately following observe dispatch. An entry must never be handed
off twice or revived after expiry.

If B or C expires, its phase still advances all 20 model seconds with explicit
black under an expiry/fallback input identity. This is no replacement guest task
and does not count as a successful handoff. The phase schedule is fixed even on
expiry; do not stop early on a favorable result. Record every request's admission
or rejection and any handoff, expiry and completion with exact wall timestamps.
Queue transitions are bound to explicit `before`/`after` sides of the relevant
observations, with at most16 total transition records and at most eight on one
observation. Handoff timestamps equal the following observe's wall-start timestamp.
No queue-only fork/events.

Unit tests separately cover exact deadline equality, delayed/stalled worker,
duplicate/double handoff, sequence reuse after expiry/completion/full rejection,
same-frame new-sequence admission, full queue, invalid clocks and bounded state
under many rejections. Do not waste a native run waiting five minutes merely to
test a clock.

## Finite supervision and independent inspection

Only new external buffer/runner/supervisor/frontend/test modules. Preserve the
packaged engine, old drivers, old collectors/parsers, every accepted runner/helper,
locks/licenses and historical artifacts byte-for-byte. Windows package fingerprint:
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
Reuse small accepted telemetry/source/frame helpers where their contracts fit,
never mutate old protocol versions, monitor globals or old fixed schedule checks.

The producer prepares a new versioned, exclusively written source-bound protocol.
Separate readiness binds its thin adapter/frontend, actual Python worker, compiler,
native cache, directories and release authority. Complete all source-bearing tasks,
reviews and source CI before concrete preparation and independent launch review.
Only the owned Windows supervisor may enter the production native path; preserve
actual-PID release, counted temporary scratch, cancellation and owner-death cleanup.
Injected engines/clocks exist only in labelled tests, never as CLI alternatives.

One acquisition in fresh directories, no automatic retry. Fixed bounds: 900 real
seconds including setup; 4GiB actual worker peak working set; 256MiB combined new
run/evidence/scratch; monitor polling gaps at most2s. These are stop thresholds,
not hard quotas or aggregate process-tree RSS. Parser bounds: protocol/manifest/
metadata2MiB, event line1MiB, total events64MiB,122 events, two checkpoints of at
most64MiB each and summary strictly below8MiB. Preserve incomplete outcomes.

The offline auditor uses a bounded immutable snapshot, verifies the complete chain,
both checkpoints and exact schedule through EOF, and closes iterators on failure.
Reconstruct all6000 cell bins, all600 aggregates, all120 motor/readout results, ring
length/position/evictions/hash and every queue transition. Validate cohort/header
identity, raw counts/population relationships, clocks, detached exports and fixed
source/configuration bindings. No engine, native call or network during inspection.
Self-recorded clock/callback-cost arithmetic is not independent clock attestation.

## Outcome and next gate

Separate integrity/resource validity, bounded-memory/queue correctness and observed
five-minute throughput. A positive observed admission result requires the complete
run, exact callback/ring/aggregate reconstruction, all resource bounds, three
`full` rejections and actual B/C handoffs before their deadlines. Correct expiry
demonstrates the bound working but is not positive throughput evidence. A resource,
clock, source, observer or journal failure is incomplete/not evaluable; never rescue
it with a favorable subsection or retuned thresholds.

Report setup time, sink-body time, bounded copying/aggregation time, observation
and snapshot-ready intervals, actual queue waits/decisions, RSS and output peaks.
No nominal frame rate hides model computation. No browser/display has been measured.
This short one-waiting-slot exercise provides no admission-rate guarantee for
300 guests or12 hours. After independent acceptance, assess whether it supports
the next local synthetic price-board subsystem; live uploads, display, sustained
load, rehearsal and public event operation remain separate gates.
