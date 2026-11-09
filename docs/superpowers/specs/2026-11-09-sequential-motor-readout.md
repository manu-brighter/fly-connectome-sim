# Sequential motor readout candidate v1

Status: prospective engineering candidate for the approved market continuation.
Implement and test offline first. No new neural acquisition, price activation,
learning or event-readiness claim is authorized by this document alone.

The [accepted diagnostic](../../experiments/2026-11-09-market-response-diagnostic.md)
shows input-dependent responses and temporal sign variation. Its artificial KC
maximum remains dominated by one group. These recordings are development evidence;
they cannot qualify this new candidate or serve as held-out acceptance data.
The user accepts slower-than-real-time model operation for the first local pilot.
Model time, transport age and the separate 30-real-minute price lock stay distinct.

## Scope and fixed engineering choices

Use the existing two DNa02 population counts, each from one declared model cell.
This is an engineered decoder, not beverage recognition or a claim of twenty
independent biological channels. All thresholds below are unvalidated engineering
choices. Do not optimize them against this diagnostic and call the result accepted.

| Component | Fixed v1 rule |
| --- | --- |
| Samples | Contiguous 500-ms observations, including black; integer 0.1-ms ticks |
| Blocks | Four consecutive observations, non-overlapping; 2 model seconds |
| Direction support | Total left+right count >=20; absolute right-left count >=4; absolute net/total >=0.20; >=3 observations have that same nonzero sign |
| Direction | Right-positive chooses the upper half; left-positive the lower half; otherwise defer |
| Neutral/rearm | Two consecutive observations each with left+right <=2; required initially and after every accepted decision |
| Price support | A separate block after leaf selection and rearm: total >=20 and nonzero activity in >=3 observations |
| Path expiry | 60 model seconds or 300 real seconds from the first accepted direction block's start, whichever arrives first; exact boundary expires |

No random fallback, forced choice, synthetic neutral, manufactured black interval,
periodic proposal or automatic price update. The decoder observes inputs and never
controls the neural engine or stimulus schedule.

## Inputs, configuration and clock boundaries

Each sample supplies source identity, session identity, sequential observation
index, start/end ticks, left/right nonnegative integer counts, input version and
frame SHA256, and real monotonic timestamps at observation start and completion.
The caller also supplies current real monotonic time, all in one shared clock
domain; this adapter does not align clocks across hosts. Freshness measures delivery
after computation; it is not upload age or a promise of image-response latency.

Require exactly 5,000 ticks per sample, continuity within a source/session,
finite nonnegative integer clocks/counts (never booleans), nondecreasing completion
and current wall clocks, and start <=completion <=current time. A required
configuration value `max_sample_age_ms` is positive and at most 300,000; it has
no silent production default. Samples older than that value cannot contribute.
Test fixtures may use 5,000 ms without claiming a qualified pilot latency limit.

Configuration freezes an ordered list of 10–20 distinct stable drink IDs and each
drink's integer-Rappen minimum, maximum and positive grid. Bounds are nonnegative,
minimum <=maximum, and the span is divisible by the grid. Reject invalid/duplicate
IDs and unsafe/unbounded text fields; IDs/session/input versions are at most128
characters, source/frame digests are exact SHA256. Counts, clocks and prices must
fit nonnegative JSON-safe integers. Freeze the policy version, all constants,
ordered configuration and freshness limit into a canonical configuration digest.
The same numeric bound applies to retained and emitted aggregate counts; reject
an oversized aggregate rather than emitting an unsafe JSON number. Temporary
integer products used for exact rounding may exceed that bound.

Malformed, stale, out-of-order, duplicated, gapped or source/session-discontinuous
samples clear pending blocks/path and are dropped. Malformed data additionally
raises a clear validation error; other resets return an explicit reason. The next
valid segment starts waiting for neutral. No decision evidence crosses a reset.

Ordering protection is separate from decision evidence. Preserve the valid
current-time high-water mark and the last established sample's source/session,
index, model end and completion time across malformed/stale/duplicate/rewind
resets, pause/resume and reconfiguration. Invalid data must never lower them.
A fresh structurally valid forward gap is a dropped recovery boundary: advance
these sample watermarks to it, clear evidence, then require continuity and neutral
from subsequent samples. A source/session transition is likewise a dropped new
segment boundary only when its start is no earlier than the previous completion
and its completion is strictly later; adopt its key/index/model-end watermarks.
Old or overlapping transitions are rejected without changing the established
source. Within a source/session, duplicates, rewinds and overlapping model or
compute intervals cannot advance sample watermarks. The first valid sample of
a new decoder establishes initial watermarks and may count toward neutral.

Expiry is checked before consuming the triggering sample; that sample is dropped.
When a first supported direction would create a path, check its proposed anchor
against the current model end and supplied current wall time too: fresh individual samples can still
span an already-expired block. Reject/reset before accepting that first direction.
After a pause or reconfiguration, also reject samples completed before the resume/
configuration boundary. Explicit restart starts a new decoder with no partial path.
Normal model advancement remains the caller's responsibility, even while paused.

## State transitions and drink mapping

Start waiting for neutral. After the second qualifying neutral observation,
collect a fresh block; those two neutral samples are not evidence for that block.
Unsupported blocks are discarded and the next complete block can be evaluated.
An accepted direction always clears the block and requires neutral again.

Represent the current candidate interval as `[lo, hi)` over the frozen drink list.
At each supported direction use `mid = (lo + hi) // 2`: lower selects `[lo, mid)`,
upper selects `[mid, hi)`. A single remaining drink starts the separate price
phase after another rearm. At20drinks this needs four or five supported directions.
Unequal path lengths, fixed ordering and correlated signs can bias selection;
do not rebalance or substitute drinks after observing output.

The path clock starts at the first accepted block's first model tick and recorded
observation-start wall timestamp, not its completion or a later branch/leaf.
Rearm and deferred blocks do not refresh that clock. Retain the
ordered input-version/frame history for all observations within this bounded
path interval, plus the measurement ranges supporting each accepted direction.
This is a support trace, not a complete causal history of the continuous brain;
earlier neural state can still matter. Keep at most128 sample records, four
pending block samples and two rearm samples; fail closed/reset if a bound is hit.
Before a path exists, only the small pending/rearm buffers may accumulate.

## Price and proposal

For a supported price block, let `R` be right count and `T` total count. With
`steps = (maximum - minimum) // grid`, compute
`k = (2 * R * steps + T) // (2 * T)` and target `minimum + k * grid`.
This is integer half-up rounding. Supported all-left/all-right blocks reach the
configured endpoints. There is no per-change step cap; CHF4→7 is representable.
One spike cannot support a price block or an endpoint proposal.

Emit exactly one proposal at completion of that price block, then clear the path
and require neutral. Include policy/configuration identity, source/session,
selected stable drink ID, target Rappen, measurement ranges/counts, model and
real start/completion clocks, and bounded input-version history. Results returned
to callers are detached from internal mutable state. A proposal has no authority
to change a price and carries no confidence, semantic or native-attestation claim.
`completion_wall_ms` records the last supporting observation's completion;
`emitted_wall_ms` records the current `now_ms` of the emitting call. These are
distinct clocks: expiry always uses current time, not the measurement completion.

## Offline module interface

`MotorReadout(drinks, *, max_sample_age_ms)` accepts drink records with `id`,
`minimum_rappen`, `maximum_rappen` and `grid_rappen`.
`consume(sample, *, now_ms)` returns detached `status`, `reason`, `phase`,
`interval` and `proposal` fields. A sample contains `source_sha256`, `session_id`,
`observation_index`, `start_tick`, `end_tick`, `left_count`, `right_count`,
`input_version`, `frame_sha256`, `wall_start_ms` and `wall_completion_ms`.
Explicit `pause`, `resume` and `reset` calls require `now_ms`;
`reconfigure(drinks, *, max_sample_age_ms, now_ms)` replaces the configuration.
`reset` preserves ordering watermarks and introduces a current-time boundary;
only a new decoder instance starts with no established ordering cursor.
Read-only `policy_version` and `configuration_sha256` identify the policy;
`configuration` exposes a detached canonical configuration.

The future price service independently checks freshness, configuration, deduplication,
range and at least30real minutes since actual activation of the same drink. A
rejected proposal is consumed/discarded: no retargeting, delayed queue or cooldown
expiry trigger. This offline component neither implements nor weakens that guard.

## Evidence required before a neural pilot

Synthetic tests must reach every one of20leaves, both supported price endpoints,
rounding boundaries, exact thresholds, ties/silence/alternating signs, rearm,
expiry, resets, pause/restart and bounded storage. They establish software behavior
only. Any replay of old branched evidence must keep branch discontinuities visible;
do not stitch restored arms into an apparently continuous history.

A later protocol must freeze this mapping/rules, previously unused input sequences
and ordering, transitions, durations, all clocks and finite resource limits before
running. Include sustained/changed inputs, neutral opportunities and repetitions.
Predeclare decision count, completed paths, slot concentration, price range and
timing; retain stalls and dominant choices. No favorable-window search, automatic
retry or20-slot/6–12h qualification from one short probe. Stage C remains gated.
