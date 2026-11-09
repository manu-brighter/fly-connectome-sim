# Continuous motor-readout probe v1

Status: prospective protocol independently accepted. No acquisition has run.
This follows the accepted [offline decoder](../../experiments/2026-11-09-sequential-motor-readout.md),
published as `af4879b` with successful CI. The user accepts slower model computation
for the local pilot. No actual prices, new training, API request or event-readiness
claim follows from this probe.

## Question and fixed scope

Can the unchanged sequential-motor-readout/v1 decoder rearm and complete a
supported drink/price path during one continuous model session with new inputs?
This is a narrow engineering feasibility probe. It is not twenty-slot coverage,
biological choice, semantic recognition, full price-range validation or a
performance benchmark for the later cell display and upload service.

Use one fresh engine, the existing full graph and normal population telemetry.
No checkpoint restore, branch fork, manual decoder reset or adaptive stimulus.
The unchanged model advances every interval, including black, with `learning=False`,
no external stimulation, and normal passive dynamics. No cell observer is needed;
this probe cannot establish throughput with a later live cell display attached.

## Exact inputs and schedule

Every frame is 64×64 RGB `uint8`, with identical RGB channels, black 0 and white255.
Coordinates `x,y` are integers0–63. All six patterns contain2048 white pixels;
equal image brightness does not establish equal retinal drive.

| ID | White pixels |
| --- | --- |
| S1 | `(x // 8) % 2 == 0` |
| S2 | `(y // 8) % 2 == 0` |
| S3 | `(x // 8 + y // 8) % 2 == 0` |
| S4 | `((x + y) // 8) % 2 == 0` |
| S5 | `16 <= x < 48` |
| S6 | `16 <= y < 48` |

Twelve consecutive eight-second episodes each contain exactly **2 seconds black
then 6 seconds pattern**. Pattern order is
`S1,S2,S3,S4,S5,S6,S6,S5,S4,S3,S2,S1`.
Freeze generated frame bytes/hashes and assert that the six nonblack hashes
differ from each other and developmental A–D before acquisition. Do not normalize
or alter images based on model output. Black is the known control input; only the
six nonblack patterns are new. A new image does not make this independent research
confirmation of a development-selected decoder.

Prospective input hashes use the existing `rgb-input/v1` scheme: canonical JSON
dtype/rank/shape/version header, LF, then logical C-order RGB bytes. They are not
bare pixel-file hashes. Independently calculated before neural execution:

| ID | SHA256 |
| --- | --- |
| black |`aa5f1e84bc3d595d7cfa5f56d794840c0c55e6b67e5bc7a0fa976f9030e93448`|
| S1 |`c1fe7a097c8ee4b8a4d71211cc638e7a3a660e5d06f335b90ea2ae61c1964761`|
| S2 |`e6cbe8173a2ee4a339040e7463f73cbda6f5fd859032afdb65e0ac7d4134b029`|
| S3 |`c553a2bd58cf00fe0974cdaee4cc0b9eb5ad00a0aa173ff5aad3e82d81189a51`|
| S4 |`d03d741fd55ed52eff994c9f529fd74472330eb6bad8dc321e26a1ecbcfee094`|
| S5 |`c30d24a55590eacdbc4eef56f38de778a015cbca30c4e0f24e2bf8337e02454b`|
| S6 |`265475b42ecc0e1da35998836975864eed445e1ed12d901c832bf6d3ae46c8ae`|

Exactly **96 model seconds, 192 observations of500ms and9,600 original10-ms bins**.
Each episode has four black observations and twelve pattern observations. The
second order begins at48s, with both engine and decoder state preserved. Paths
may cross that boundary. Reversed ordering is not independent replication or a
causal order comparison; identical outputs are not required.

Black offers an opportunity for measured neutrality; it never sets a neutral
flag, clears the decoder or guarantees a decision. Six episodes per order allow
opportunities for five direction decisions plus separate price evidence, without
forcing those transitions or aligning block boundaries to episode boundaries.

## Decoder, configuration and clocks

Use the reviewed module without modifications. Freeze twenty ordered fixture IDs
`drink-00` through `drink-19`, each with minimum400Rappen, maximum700Rappen and
grid50Rappen. These are probe fixtures, not an actual bar configuration. The grid
is a target-price increment, **not a maximum change**: full CHF4→7 remains possible.
Use `max_sample_age_ms=5000` for this in-process handoff only; this does not qualify
image-upload latency. Record the canonical policy/configuration digest.

The existing60-model-second/300-real-second path expiry remains unchanged.
Slower execution may legitimately expire a path. A single monotonic clock supplies
actual observation-start/completion milliseconds and current time immediately
before calling the decoder. Record all three; never substitute model time or
wall-clock UTC. Sample source identity is the frozen protocol SHA256; an explicit
unique session ID is recorded in run metadata. Administrative IDs do not select
drinks or prices. Observation indices0–191 and ticks0–960000 are continuous.
Input versions identify each episode and its black/pattern interval.

For each observation derive left/right counts from the original telemetry bins,
not from rounded rates. Preserve all seven group counts/rates and their declared
population membership. DNa02 left/right each contain one declared model cell.
Record the exact decoder input, current-time argument and returned result with
the corresponding raw observation. Every proposal retains its support history;
this is not a complete causal history of the continuously evolving brain.

## Artifacts and complete offline inspection

New exclusive directories only; no overwrite, resume or automatic retry.
Artifacts follow the existing layout: `protocol.json`, `run/run.json`,
`run/events.jsonl`, two recorded checkpoints `brain-before.npz` and
`brain-after.npz`, then `summary.json` and `receipt.json`. Use a single root branch
`continuous` and exactly194 events: initial checkpoint,192 observations, final
checkpoint. Initial/final ticks are0/960000. Every event is read through EOF.

The protocol binds new runner/decoder and reused helper sources, the unchanged
package fingerprint and graph/source/schema locks. The separate readiness record
also binds the actual new supervisor/entrypoints and Python/compiler/native cache.
Preserve all historical source files and artifacts byte-for-byte. A hash verifies
artifact identity, not neural replay attestation.

Inspection validates canonical sealed data and metadata/protocol/source agreement,
complete checkpoint bindings, exact schedule and clocks, contiguous native bins,
nonnegative integer counts, all group declarations, and count/rate arithmetic
using actual population sizes. Reject learning/stimulation/detail or branching
contradictions, sample counts/identities that disagree with checked data, clock
contradictions and altered decoder results,
even when the artifact is resealed with internally consistent hashes.
Reconstruct the entire decoder stream from checked bin counts and recorded clocks;
compare every result exactly before deriving a summary. Reconstruction is pure
software replay, not native model replay. Invalid/incomplete data emits no success
summary or complete receipt. Preserve partial records for diagnosis.
A consistently rewritten and resealed timing history is not independently
authenticated by this audit. Hashes and reconstruction cannot prove that a
declared monotonic timestamp was originally measured; actual acquisition review
also examines the separately supervised execution evidence within its limits.

## Supervision and finite limits

Reuse the frozen Windows owned-process monitor through a thin new adapter; do
not copy its large monitor or mutate its globals. Its private integration points
are explicit, source-bound dependencies. Add a new small PowerShell frontend with
the same validated ownership/ancestry, ACK and fixed-byte cancellation behavior.
Old diagnostic entrypoints remain unchanged and inspectable.

| Bound | Fixed value |
| --- | --- |
| Wall deadline |900s including startup, acquisition, audit and cleanup monitoring |
| Actual worker peak RSS |4GiB; child peaks reported separately |
| Combined new output/evidence/scratch |256MiB; sample peak and retained bytes distinct |
| Monitor polling |At most2s; existing monitor normally checks every0.25s |
| Manifest / event line / total events bytes |2MiB /1MiB /64MiB |
| Event count / checkpoint count |194 /2 |
| Each checkpoint |64MiB |

Limits are stop thresholds with measured overshoot semantics, not hard resource
quotas or a general sandbox. The actual Python worker, owner and supervisor are
identity-bound; parent death/cancellation closes only the owned tree. Scratch is
counted. Production requires prepare/hash/release handshakes and only the pinned
compiler-version probe; no compile or unconstrained child command. Before a native
run, review the final source, non-neural lifecycle tests, protocol/readiness bytes,
exact fresh paths and concrete command. Then one bounded run is within the user's
authorized continuation. Failures do not authorize an automatic retry.
The900s budget bounds the attempt; it does not guarantee all96model seconds finish.

## Predeclared interpretation and metrics

- **Valid acquisition:** complete exact schedule and source/clock/decoder audit,
  with no integrity or resource failure.
- **Narrow positive:** a valid session emits at least one supported complete
  proposal. This establishes path completion only under this schedule.
- **Negative:** a valid session emits no proposal. Distinguish missing neutrality,
  unsupported direction, expiry and unsupported price evidence.
- **Incomplete/inconclusive:** resource termination, missing observations, invalid
  bindings or failed reconstruction. Retain partial evidence; no retry by default.

Report all supported directions by sign, complete and partial routes, every
selected ID and concentration, target prices, supported/deferred blocks, neutral
waiting, resets/expiries, proposal/model/wall timings, input histories and measured
processing/delivery latency. Keep all outcomes, including silence and dominance.
Both orders share state; partitioned summaries are descriptive only. Final pending
state is reported without inventing an additional expired/reset event.

A sole repeated leaf remains a dominance problem even with proposals. Neither a
positive nor a negative result automatically advances Stage C. Review the failure
or limitation before a separately versioned design or next scoped measurement;
do not repeatedly adjust windows, patterns or thresholds until proposals appear.
The eventual service still owns the30-real-minute activation lock independently.
