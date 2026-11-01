# Strict Qualification Evidence Contract

**Status:** Integration in progress. The shared checkpoint reader and native
map context (Tasks7B4a/b) are implemented; grid reconstruction, selected evidence
and public freeze integration remain pending, without formal qualification
approval. **Date:** 2026-11-01.

Refines the [assay design](2026-09-24-associative-plasticity-pivot-design.md),
[replay contract](2026-10-02-replay-anchor-contract.md) and existing
[implementation plan](../plans/2026-09-24-associative-plasticity-assay.md).
The endpoint, fixed grid, seeds, windows, current, floors, exclusions and
scientific interpretation remain unchanged. No supported result is presumed.

## Durable exploration and exact source bindings

Keep the existing durable grid snapshots, including discarded candidates.
Do not delete selection history, merge sealed runs or add a generic training
replay interpreter. A later storage redesign needs its own evidence and review.

`qualification_grid_binding` uses `binding_version="qualification-grid-binding/v1"`
and binds one of the 96 grid/seed/identity/order combinations: `grid_evidence_id`,
`grid_index`, `seed`, `paired_identity`, `presentation_order`,
`baseline_occurrence`, `training_occurrences`, `retained_occurrences` and
`observation_sequences`. Roles follow the existing four grid acquisitions and
three retained-state paths, with T-specific raw trials. Every point replicate
names its `grid_evidence_id`; failed routes record only their actually completed
prefix and explicit reason, never invented snapshots.

Use bounded ordered `failures`: one base failure OR up to one failure per fixed
T, never both. Later T routes can continue after an earlier failure. Omit
unentered roles and retain actually completed partial calls; a successful
zero-duration retention has an empty observation list and a real checkpoint.

An occurrence is the existing five-field checkpoint name/hash/origin/sequence/tick
object, not a digest-only alias. Obtain sequence from the real recorder position.
Validate every binding, role, factor, input, interval and source against actual
stream/inventory bytes, including discarded candidates. Recompute grid metrics,
reasons and selection ordering from linked observations and authenticated arrays.
The selected-only training namespace must not contain all grid variants.

Use `controls=True` explicitly for all grid ordinary acquisitions, including
paired replay, and for selected acquisitions. This corrects inconsistent washout
schedules and requires fresh qualification; do not reinterpret old results.
Keep grid selection effects distinct from later time/exposure-matched raw effects.
Washout equality is checked from measurements, never assigned to make it pass.

## Authentic maps and engine-free archive reduction

Checkpoint NPZs do not contain static graph/circuit selection maps. Their hashes
cannot reconstruct maps or establish the origin/order of summary vectors.
Do not trust a producer-provided map digest or silently create an engine in
`build_frozen_config(VerifiedRun)`.

For qualification, the real native verifier creates a private immutable
`qualification_context_bytes` inside its existing artifact-bound attestation.
`context_version="qualification-map-context/v1"` binds actual engine identity,
neuron count, checkpoint array names/dtypes/shapes, MBON11/MBON07 candidate maps,
ordered KC/DAN indices and source IDs, and baseline plastic weights. Derive these
from a fresh compatible engine, rehash actual provenance/static arrays and check
CSR/edge/DAN ordering, groups, registration and original weights before capture.
No runtime arrays escape; only canonical immutable bytes are retained.

Preserve the existing one-engine anchor loop. Each qualification verification
boundary creates one fresh compatible engine, captures context before its first
restore, then reuses that engine for every anchor with complete independent
source restores as today. Qualification uses exactly one factory for zero, one
or multiple anchors. Confirmation keeps its current zero factories for no
anchors and one for a nonempty set. No extra engine or new reuse optimization
is introduced; only the zero-anchor qualification map check is new.

Only genuine artifact-bound `ValidatedPrefix`/`VerifiedRun` accessors expose a
decoded copy after rechecking current bindings. Plain integrity objects,
subclasses supplying synthetic proof, stale/transplanted contexts, serialized
flags and caller registration cannot issue this context. Prefix and sealed
verification construct separate contexts; do not promote a prefix proof to a seal.

Bind private native-proof issuance to the exact result object as well as its
artifact bytes, using an unissued-by-default private capability and owner weak
reference. Ordinary construction, subclasses, copies and proof transplantation
cannot issue a new native proof. Apply the shared issuance check to existing
native-proof accessors too; no caller registration or persisted trust registry.
At final context issuance and each engine-free context intake, recompute and
compare the full current packaged source fingerprint, in addition to existing
schema/event/checkpoint bindings. Do not rebuild the DLL to consume context.
Existing named engine groups stay nonempty; authentic zero-candidate selections
stay empty, without relaxing engine contracts or inventing candidate indices.

Factor `checkpoint.read_checkpoint(path, expected, schema, n)` from the existing
codec, preserving NPZ format and all metadata/shape/finite/native-state checks.
`load_checkpoint` keeps its destination-writability checks and delegates to this
single decoder. No ndarray-shaped placeholder allocations or second decoder.
Descriptors contain the exact lossless `dtype.str` and a nonnegative integer
shape. Structured/subarray templates that cannot be represented losslessly are
rejected; actual native formats and the NPZ writer remain unchanged. The locked
NumPy header parser covers NPY1/2/3, behind a bounded NPZ-only input boundary.
Grid reduction reads one authenticated archive at a time with this context,
checks actual candidate arrays/bounds/weight consistency and recomputes state
metrics. Response rates and historical bound diagnostics come from linked raw
bins. KC vectors require linked call-level pathway counts for whole driven calls
inside the window; modeled drive sums the absolute drive means of the first
driven call. Neither can be recovered from archives/context or group bins alone.
Validate their actual index/source order and recompute summaries. This proves
map/content consistency, not independent training execution.

The grid component uses two complete event passes and sequential archive reads,
retaining bounded references, one decoded archive, one raw observation and at most
one configuration's eight compact unit projections. This is a design bound,
not measured capacity. Test it on genuine prefix/seal context independently;
public sealed-only freeze enforcement and arithmetic-fixture migration land
with the shared lifecycle in Task7B4f, without synthetic context fallbacks.

## Shared native selected execution and measured resolution

Extract the current producer body as private
`_produce_cohorts(engine_factory, recorder, *, execution, cohorts, conditions,
baseline_occurrence, namespace, measure_replay=False)`.
`execution` is validated plain declarations: family, seeds, engine identity,
MBON11 population, candidate identity, selected timing/window, two retention
times and per-seed A/B/C/black input hashes. It contains no purported artifact
hashes, trusted flags, effect floor or synthetic frozen-config digest.

Confirmation wrappers keep genuine frozen validation and lifecycle ownership.
Qualification supplies its own open recorder/baseline and qualification inputs;
family chooses the fixed training/response event types. Preserve authenticated
source restore, five ordinary acquisitions, three interventions and independent
siblings. Selected evidence comprises 40 acquisitions, 24 interventions,
128 anchors and 768 logical A/B/C pre/post cells across all eight factors.
Legacy selected-control summaries derive from actual new raw T cells; do not
execute a second inconsistent control protocol.

With `measure_replay=True`, repeat all 408 physically distinct selected trials
from their exact independent parents: 24 pre and 384 post, including both T.
Emit source/observation/state-bound `qualification_replay` records and link each
response by `replay_id`. Derive response resolution from actual bin/rate
differences; require deterministic raw-bin/complete-state agreement. Compare
actual candidate state pairs rather than copying a zero tolerance. Shared pre
cells reuse their real comparison, not fictitious duplicate trials. One-spike
and effect-floor arithmetic remain unchanged. Native anchor replay still proves
black retention only; report response repeats separately.

## One truthful terminal and sealed-only freezing

Use a shared pure qualification evaluator for real validated prefixes and seals,
and a private scientific execution contract rather than a provisional frozen
object with fake artifact hashes. Lifecycle: authenticated grid and selection,
selected native matrix, final checkpoint, validated/native-verified prefix,
shared assessment, one evidence-prefix-bound qualification terminal, seal,
native-verify sealed artifact and independently compare the canonical assessment.

`build_frozen_config` keeps its sealed-only signature and creates no engine. It
requires the genuine qualification context, re-evaluates evidence and creates
final frozen fields only for a supported outcome using actual sealed hashes.
Complete authenticated negative exploration may be unsupported with zero
reconstructed anchors; report the separate native map check explicitly.
Missing/malformed evidence, unavailable runtime or verification failure cannot
be turned into an authenticated scientific negative or a confirmation config.
Pure arithmetic fixtures remain separate from artifact/native trust tests.

The specific pre-call negative remaining retention gap is independently
schedule-infeasible only when actual training clocks and the declared timeline
prove `target_onset - 100 ms - training_end < 0`. Unmeasured values stay null;
no failed-call observation or retained checkpoint is invented. Other unavailable
native/clock/ingest evidence cannot become a scientific negative from its reason
label. Genuine complete measurements still use the unchanged scientific gates.

## Closed bounds and capacity gate

Before enabling integration, prove the proposed closed qualification grammar
fits a qualification-only 5120-branch cap; confirmation stays at 4096. Retain
2048 checkpoints and 10000 relevant events, enumerate permitted roles/factors,
reject orphans and drain the whole stream rather than hiding discarded data.

Conservative no-skip accounting, not measured execution: grid branches
`12*8*(4+4+4*(3+5))=3840`, selected600, response replays408, shared2: total4850.
With one shared baseline/before occurrence and final checkpoint, the snapshot
bound is 1602. Closed role enumeration corrects the earlier unproved 8064 estimate
to **8099 relevant events**: 4848 first-branch events, 1602 checkpoints, 96 grid
bindings, 144 points, 40 trainings, 24 interventions, 128 anchors, 768 responses,
408 response-repeat diagnostics, 40 derived control summaries and one terminal.
The shared baseline/summary first events are already counted. Raw observation
bytes/counts require separate accounting. These are intended integration roles;
the capture-only implementation leaves the operational 4096 branch cap unchanged.
Selected production must prove conformance before qualification-only 5120 is
enabled. Tests must fail closed if these bounds or completeness assumptions change.

Measure the integrated grid path with its actual diagnostic flags, snapshot I/O,
archive reduction and both native verifications before formal source freeze.
The 70-second resource pilot used False/False detail flags, not legacy grid detail.
Sample checkpoint size times1602 is not an upper bound; no whole-assay runtime
or storage approval follows from it. A capacity failure is reported, never solved
by dropping ancestry, controls or scientific gates.
