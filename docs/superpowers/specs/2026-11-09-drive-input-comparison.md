# Fixed-input comparison of continuous motor drive

Status: independently accepted prospective protocol. No new acquisition or candidate evaluation of
these inputs has occurred. Existing source and development evidence stay frozen.

## Question and scope

The accepted continuous-drive development replay emitted eight proposals for one
favorite. This new experiment separates functional proposals from sensitivity to
two unseen fixed visual inputs, controlling the neural starting state and retaining
an exact repeat. It is a bounded engineering observation, not biological validation,
training, semantic image recognition or proof about arbitrary guest photographs.

Use the unchanged `continuous-motor-drive/v1` configuration:20 ordered IDs
`drink-00` through `drink-19`,400–700 Rappen in50-Rappen grid steps,5000ms delivery
freshness. Configuration SHA256:
`c02ca9be4db5198b46e718116ff80c169aa3d051f29ff7703d27f1f4fd5315c5`.
No thresholds, alignment, duration or mapping are selected after outcomes.

## Exact inputs

Coordinates `x,y` range0–63; arrays use `[y,x,channel]`, shape `(64,64,3)`,
RGB `uint8`, each pixel either `(0,0,0)` or `(255,255,255)`.

- Black: all zero.
- A: white iff `(x < 32) == (y < 32)`; top-left and bottom-right quadrants.
- B: exact complement of A; top-right and bottom-left quadrants.

A and B each have2048 white pixels and mean channel value127.5. No resize, noise,
randomization or adaptive preprocessing. The logical hashes use the existing
`_rgb_input_sha256`, including its shape/dtype header, not merely raw RGB bytes.

| Frame | Logical RGB SHA256 |
| --- | --- |
| Black | `aa5f1e84bc3d595d7cfa5f56d794840c0c55e6b67e5bc7a0fa976f9030e93448` |
| A | `7c58398da961353df4ef0040261541e17bcaae7467a92a6395a0eb4f4b9d81be` |
| B | `831971b6bf50a21b29e9a369c84669aeffa3e90fd6a10278780eab05a0a34e30` |

Both new hashes differ from all ten earlier half-frame and continuous-probe
patterns. This statement is a pure array-identity check, not held-out outcome
evidence. Exact arrays/hashes were chosen without projecting or evaluating them.

Before any advance, document `engine.brain.rgb_drive(frame)` for all three frames.
Record ordered `r1_r6` and `r8` vectors, each finite in[0,1], together with shape,
count, minimum/mean/maximum, sum, positive count and existing Float64-C-order hash.
Each vector is capped at10000 values; full metadata stays within2MiB. Bind lengths
and ordering to the engine's retina/r8 identity and provenance configuration hashes
for `retina`, `uv`, `r8`, `r8_uv`, `r8_channel`. Verify complete state hash and model
clock unchanged before/after projection. These are optical samples before filters
and current mapping, not measured injected currents or neural responses. Equal
image brightness does not imply equal retinal drive. Store this declaration in
the run metadata, never mutate the prepared protocol. The offline reader validates
the stored vectors/hash/arithmetic without constructing an engine.

## Schedule and state

One fresh engine, unchanged normal passive dynamics, `learning=False`, no external
stimulation, no pathway/qualification detail and no individual-cell observer.
Every observe call advances exactly500ms, including explicit black RGB arrays.

1. Save initial checkpoint at tick0. Advance4s black (8 observations), without
   feeding a decoder. Save the common checkpoint at tick40000.
2. In exact order run `control-black`, `image-a`, `image-b`, `image-a-repeat`.
   Before each arm restore the same common checkpoint, verify its bytes, engine
   identity, complete state hash and model clock. Record the bound branch start.
3. Each arm shows its fixed frame continuously for20s (40 observations), ticks
   40000–240000. Create a fresh unchanged decoder and distinct source-bound branch
   session; observation indices0–39. Do not reuse decoder evidence across arms.
4. Record each arm's complete end-state hash on its final observation. Save the
   final checkpoint after the fourth arm. Never stop early on a desired outcome.

Exact totals:84s actual model advance,168 observations,8400 native10ms bins,
4 branch starts,3 checkpoint events/files,175 sealed events. Shared prefix is not
counted four times. The branch endpoint clock is24s, not84s. All acquisition and
delivery clocks remain actual monotonic values; restoring a neural checkpoint
does not rewind wall time. No nominal/synthetic clocks may replace them.

Capture all seven populations with their exact bins and validated counts/rates,
including population overlap and the existing disjoint-set whole-brain bound.
Record every branch's motor sample, actual `readout_now_ms` and complete decoder
result. Prefix observations have no decoder result or consumed motor sample.
Separate actual duration/latency from model time. Final pending paths stay visible.

## Predetermined interpretation

Only complete, source-bound, resource-compliant and reproducible runs are evaluated.
Repeat A must exactly reproduce all40 motor-count pairs, the scientific end-state
hash and the ordered proposal signatures `(drink_id,target_rappen,relative_end_tick)`.
Relative end tick is completion minus40000. Branch/session/sequence IDs, hash-chain
administration, compute timings and real wall timestamps are explicitly excluded
from repeat equality; scientific state is not approximated. Validate all fields
and true clocks independently even where excluded from repeat equality.

- Function is present iff at least one fully supported complete proposal occurs
  in `image-a` or `image-b`. A proposal never activates a selling price.
- A/B output sensitivity is present iff their complete ordered proposal-signature
  sequences differ and the associated40-sample motor sequences differ. Black is
  a comparison, not a required silent state. Also report A/black and B/black
  descriptively; they cannot rescue an equal A/B output sequence.
- Report drink-ID sequence, target-price sequence and relative-time sequence
  comparisons separately, with lengths explicit. Different lengths are proposal
  availability/count differences, not matched-proposal drink/price differences.
  When lengths match, report each component's equality directly. Timing-only
  differences establish output-timing sensitivity only, never image-caused drink
  choice or price changes. Unmatched proposals are not paired by searching offsets.
- Resource/integrity/repeat failure is not evaluable, not a negative response.
  Any stale-sample, ordering/source or path-expiry reset in a comparison arm makes
  input attribution not evaluable: real-clock failures cannot serve as image effects.
  Preserve all acquired results and report the specific reason; no automatic retry.
- Valid runs without function are functional negatives. Function with identical
  A/B output is functional evidence with input sensitivity not shown. Differences
  in raw counts alone do not prove output sensitivity. No fitted rescue follows.

No requirement for all20 drinks or both price endpoints to occur. Report technical
reachability separately from actual target/price coverage, favorites, repeats,
unsupported blocks and complete pending states. One deterministic comparison is
not a population-level statistical result or arbitrary-image robustness claim.
Even positive function and sensitivity leave live-display throughput, upload/load,
price-service and event-rehearsal gates open; Stage C is not automatic.

## Acquisition, integrity and finite resource contract

New external runner/auditor and thin supervisor adapter only; no packaged source,
old decoder, runner, supervisor, schema, graph lock or historic artifact edits.
Preserve the current41-member Windows package fingerprint
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
Reuse the existing engine/checkpoint/recorder and frozen telemetry helpers; do not
relax their old fixed protocols to accommodate this experiment.

Prepare exclusively freezes protocol, frame/decoder, runner and its existing
package/shared-helper identities. The separately reviewed readiness then freezes
the new adapter/frontend, actual runtime, compiler/cache, paths and actual-worker
binding; together they cover all execution sources. Production requires owned-job
release, acknowledged cancellation and owner-death cleanup. Do not start native
execution until source/tests and concrete preflight are independently accepted.

Limits remain900s wall,4GiB actual worker peak RSS,256MiB combined newly written
run/evidence/scratch bytes, at most2s monitor sampling gaps. These are observed
stop thresholds, not hard quotas or aggregate process-tree RSS. Parser limits:
2MiB manifest/protocol,1MiB event line,64MiB events,175 events,3 checkpoints,
64MiB per checkpoint. Exclusive8MiB summary ceiling; no resume or overwrite.
Use fresh ordinary output/evidence directories; never reuse a completed attempt.

The inspector owns one bounded snapshot, verifies the entire hash chain/checkpoints
and strict new schedule/metadata/count/clock/readout semantics through EOF, with
explicit iterator closure on failure. It reconstructs the complete summary rather
than trusting producer flags. Verification mode remains `integrity-only`; source
and file integrity are not native replay attestation or scientific qualification.
One supervised acquisition only; partial/error artifacts retained honestly.
