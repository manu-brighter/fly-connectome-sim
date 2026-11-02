# Strict Qualification Evidence Contract

**Status:** Integration in progress. The shared checkpoint reader and native
map context (Tasks7B4a/b), authenticated grid reconstruction (Task7B4c.2b) and
caller-owned selected native production (Task7B4d) are implemented and accepted.
d passed independent source review and actual tiny-native selected/legacy
confirmation matrices on its earlier source. Private successful-append reference
helper e.1 is accepted with unchanged public append. e.2 R1 schema/structural
intake, projections and independent local pair comparison passed source review,
focused/affected-file compatibility and separate actual MaleCNS context acceptance.
The private e.3 True producer passed source review, actual 9/51/408-pair
tiny-native checks and assay-module compatibility. Parent e implementation
acceptance is complete; production global reconciliation/public assessment/freeze
integration (f), CLI/capacity (g) and formal qualification remain open.
This is no source-freeze or scientific approval. **Date:** 2026-11-01.
**Updated:** 2026-11-02.

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

### Initial private grid component and incomplete evidence

The initial reader lives in `experiment/qualification_grid.py`, reached through
the private analysis wrapper. It accepts genuine current-source native-verified
prefixes or seals, creates no engine, and returns plain assessment data rather
than proof or configuration. Selected activity is explicitly outside this initial
component; public freezing and the selected lifecycle remain Task7B4f.

A fixed prefix may end before baseline, between complete units/point records, or
inside exactly the next expected unbound unit. Validate all available calls,
restores and archives before returning inconclusive with no selection. An
unbound tail may include only the producer's exact forward failed-T recovery
edges, which remain unresolved until its actual binding. Later-unit activity,
points or final framing cannot hide an omitted interior binding. A fresh prefix
still rejects ingested checkpoints without their checkpoint event; an older
fixed prefix ignores permitted later appends outside its captured boundary.

The initial sealed grammar follows actual grid-only `qualify`: final checkpoint
or result before all 96 bindings/all 144 points is an error, even at an otherwise
closed unit boundary. No manual early-seal/abort protocol is introduced. A seal
never admits an unbound tail; full inventory with genuinely unavailable data may
still be inconclusive. The final `brain-after.npz` belongs to the actual last
physical branch/ancestry/clock, not a guessed maximum-T branch or last binding.

`unit_count` counts distinct durably evidenced units, including the permitted
tail, not an invisible in-memory `begin_grid`. Keep errors as bounded reason
strings while draining valid framing, avoiding retained exception tracebacks.
Walk point fields without copying all vector-bearing replicas. Compare the twelve
points before releasing the current configuration's at most eight projections;
retain only bounded references and finished scalar summaries across grids.

Raw memory bounds use the actual float64 U/W rule clamp and engine hit masks;
float32 synaptic weights retain their existing consistency tolerance. DAN traces
may be signed because the declared model subtracts a baseline; KC traces/counts
remain nonnegative. Candidate KC counts are each bounded by call ticks, and the
group-minus-candidate integer count must fit the authenticated noncandidate KC
complement. Full candidate coverage requires equal totals. These are necessary
recorded-data constraints, not upstream native training attestation.
Summary counts are nonnegative integers. Empty arrays require null extrema/mean
and the SHA256 of empty bytes; a singleton requires numerically equal minimum,
mean and maximum. Do not infer general array contents or unseen visual-map
dimensions from aggregate summaries.

Authentic empty primary positions/edges/KCs are known absence only after complete
available base roles/archives and their exact base-validation failure agree.
Preserve the actual null/empty representation; do not generalize this exception
to unknown runtime failures or manufacture candidate state. An incomplete prefix
with known absence remains inconclusive because its inventory is incomplete.

The current native measurement helper has no reachable `_GateFailure` path,
although synthetic orchestration can inject a later-window failure without
recording its first failed window. This initial reader rejects inconsistent
mixed-window declarations rather than deriving ownership from trusted summaries.
It does not claim generic later-window failure support. A future source change
making that failure reachable must settle its wire ownership before acceptance.

## Shared native selected execution and measured resolution

The inherited one-spike boundary is corrected before strict grid consumption.
For equal actual populations/window durations, retain integer raw counts and
compute `r=abs(pre_paired-pre_replay)`, `w=abs(frozen_post-reference_post)` and
`k=max(5*r,1)`. Qualification C fails below one count; confirmation C fails at
or below one. Washout fails only at `w>k`. Convert counts/differences/k afterward
through the shared `count/(N*(duration_ticks/10000.0))` function. Do not subtract
rounded control rates, multiply an already rounded replay rate, infer counts
from declared scalar rates or introduce a gate tolerance. Missing remains
unavailable. Preserve other endpoint equations and reason/selection ordering;
only the exactly derived washout reason participates before earliest-T choice.
This corrects numerical boundary outcomes without changing the intended policy,
raw formats or version strings; exact source identity distinguishes execution.
It does not supply native history proof or complete the public freeze lifecycle.

Extract the current producer body as private
`_produce_cohorts(engine_factory, recorder, *, execution, cohorts, conditions,
baseline_occurrence, namespace, measure_replay=False,
confirmation_replay_resolution_hz=None)`.
`execution` is validated plain declarations: family, seeds, engine identity,
MBON11 population, candidate identity, selected timing/window, two retention
times and per-seed A/B/C/black input hashes. It contains no purported artifact
hashes, trusted flags, effect floor or synthetic frozen-config digest.

For the intermediate production-only component, reject `measure_replay` unless
exactly False. Qualification omits unavailable response resolution/replay fields
until actual repeats are implemented; no zero or borrowed frozen tolerance is
substituted. The separate confirmation-only scalar is extracted by the existing
wrapper after genuine frozen validation, preserving its legacy emitted field;
qualification forbids a supplied value.

The caller recorder must declare actual `black_input` before creation, matching
the generated black RGB and per-seed hashes. Add that descriptor to the CLI owner
metadata before selected integration; never mutate a populated recorder's
metadata. Require paired in every canonical conditions subset, matched_reference
for necessity/sufficiency, and exactly one cohort for namespace=False. Preserve
confirmation names and use a reserved selected namespace for qualification.
Validate all requested names/cohorts and the caller's exact baseline occurrence/
event/native state before the component's first mutation. Preserve factory
counts/reuse and all acquisition/intervention/trial restores. Baseline
authentication adds exactly one quiescent native restore on the already allocated
preflight engine, with equal complete state/clock and no observation; count it
separately from baseline trials without weakening the comparison. Use actual global
append positions; anchors append globally too. Training-source authentication
streams the complete prefix with bounded exact occurrence/descriptor lookup,
preserving post-factory byte/clock/digest checks without retaining raw history.
No persistent trust cache or skipped EOF validation is introduced.

Confirmation wrappers keep genuine frozen validation and lifecycle ownership.
Qualification supplies its own open recorder/baseline and qualification inputs;
family chooses the fixed training/response event types. Preserve authenticated
source restore, five ordinary acquisitions, three interventions and independent
siblings. Selected evidence comprises 40 acquisitions, 24 interventions,
128 anchors and 768 logical A/B/C pre/post cells across all eight factors.
Legacy selected-control summaries derive from actual new raw T cells; do not
execute a second inconsistent control protocol.

**Parent e, including e.1/e.2/e.3, is implemented and accepted with complete
tiny-native 9/51/408 checks. Production global f assessment remains open.** Accept only exact
Boolean `measure_replay`; True is qualification-only. False preserves absent
qualification fields and confirmation's genuine legacy scalar. Repeat all
**408 physical trials: 24 PRE + 384 POST**, including both T. Each full-matrix PRE
comparison serves sixteen logical cells; subsets serve twice their condition
count. Originals/repeats use independently restored fresh engines in lockstep
over the identical split schedule. PRE uses the exact caller baseline occurrence;
POST uses the same retained scratch parent, checking anchor complete-state/clock
and authenticated training-source binding. No extra NPZ is introduced.

Reserve all repeat IDs/branches before writes. `replay_id` and repeat branch are
`original_branch + "/repeat"`; `replay_version` is `selected-response-repeat/v1`.
At window stop, derive actual response resolution from absolute integer MBON11
count differences using canonical duration/population-to-Hz conversion. Derive
separate `candidate_memory_w_resolution` through existing `_state_difference`
on actual float64 W pairs, preserving dtype through subtraction/absolute/mean.
Keep original response clocks and forward `replay_id`; finish both trial tails,
then emit one closed `qualification_replay` diagnostic on the repeat branch.
No repeat emits extra logical responses. This metric does not replace grid
training `state_replay_resolution`; one-spike/effect-floor arithmetic is unchanged.

Compare every scientific operation payload (version, clocks, stimulation,
learning, current, detail flags) and WHOLE telemetry object through existing
`recorder._scientific`, excluding ONLY `compute_seconds`/`kernel_seconds`. Event
envelopes differ and are bound separately. Record both engines' start/window/final
clocks and complete-state hashes; require corresponding equality and parent/start
agreement. Window/final candidate/noncandidate digest pairs must also agree.
Scientific-body/source/state/nonfinite/binding errors raise and abort; incomplete
comparisons remain unavailable, never zero. Release each completed pair/raw data.

Persist versioned strict bounded W-pair projections: dtype `<f8`, one-dimensional
length and little-endian hexadecimal bytes, plus actual ordered target,
candidate-position and edge-index maps once per pair. Require finite values,
nonempty equal maps, unique indices and exact dtype/hex/byte lengths; preserve
bytes/sign zero without concealing casts. Production binds actual native maps;
f binds genuine qualification-context maps BEFORE numeric decoding and bounds
vectors by their cardinality. Hashes cannot reconstruct numerical distance or
attest full native history.

Closed diagnostics bind physical key/version, identity/input/window declarations,
both branches, exact parent occurrence/anchor, ordered observation sequence/hash
references, clock/state boundaries, projections and derived resolutions. Accepted
private recorder helper e.1 `_append_reference` checks healthy/open state, captures integer
`next_sequence`, calls unchanged
public `append` exactly once (still returning None), then returns that sequence
and actual `_chain.previous` only after the entire call succeeds, recorder remains
healthy/open and count advances exactly one. Failed write/flush/count drift returns
no receipt; exceptions propagate. No intervening append is allowed. Chain
advancement before writing is insufficient. Do not add per-diagnostic growing-
prefix hash-retrieval scans, raw-history caches or trust issuers. These producer-
supplied references are not crash-durable proof.

e.1 is the isolated reference foundation; e.2 R1 diagnostics/projections/schema
and independent local pair comparison are implemented and accepted on R1.
Lockstep native production has actual e.3 9/51/408 evidence; the complete matrix
was measured on the four-node tiny-native fixture. No new native/history trust
authority exists; production global reconciliation remains f.

e owns local structural/arithmetic validation and an independent bounded current-
pair stream comparison. f resolves ALL references against actual fixed bytes,
including sequence/hash/parent/operation/input/clock bindings, reconciles
408 physical/768 logical cells and exact PRE reuse, rejects duplicate/orphan/
missing links and drains EOF before assessment. Source authentication,
post-factory rehash, anchor recipe, native-map and existing EOF checks remain.
Native anchor replay proves black retention only, separately from response repeats.

Minimal e scope: producer, analysis, schema, narrow recorder structural dispatch/
reference helper and existing tests; no core/grid/public-freeze/terminal changes.
The staged nine paired-cohort, 51 full-cohort and separately budgeted 408 checks
have passed. Keep operational cap4096 and intended 1602-checkpoint
bound; cap activation and g's actual controlled unprofiled capacity remain separate.

### e.2 exact mechanical contract — bounded helpers accepted

The mechanical contract is implemented and accepted for bounded R1 helpers/schema/
local pair comparison on source
`4527956304d4d1630c415a190d4a475912cbe4ca028b4abb63baa859f9af13ae`,
schema `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Parent e acceptance is complete; accepted e.2's False-only baseline is historical. The
current private True producer is scoped below; confirmation behavior stays.

Closed `qualification_replay` adds exactly this payload to existing seven event
framing fields (sequence/type/branch_id/sim_ms/run_metadata_sha256/
previous_scientific_sha256/scientific_sha256); nested objects forbid extras/nulls:

```text
replay_version="selected-response-repeat/v1", replay_id, original_branch_id,
physical_key, source_occurrence, engine_identity_sha256, candidate_identity,
population_size, input_sha256, black_sha256, response_window, cs_onset_tick,
sim_tick, operations, boundaries, candidate_projection,
response_replay_resolution_hz, candidate_memory_w_resolution, parent_branch_id
```

Add PRE's parent_checkpoint_name/parent_checkpoint_sequence/parent_checkpoint_sha256,
or POST's parent_state_anchor_sha256. Require qualification run/family,
branch_id=replay_id=original_branch_id+
`"/repeat"`, sim_tick=repeat final tick, sim_ms=tick/10. Closed `physical_key`:
`{seed,paired_identity,presentation_order,phase,stimulus}`; POST adds exactly
`{condition,retention_ms}`. Phase is pre/post respectively; existing qualification
factors apply. PRE source_occurrence is caller baseline; POST is training/intervention
source matching the actual anchor source. PRE omits T/condition.

`operations={original,repeat}` contains ordered, unique, disjoint prior
`{sequence,scientific_sha256}` references: branch_start, optional immediate
replay_thaw, EVERY observe through tail, excluding logical evidence. Each list
has 4–6 entries: three/four scheduled calls, start, at most one thaw; schedule
tests must reject incompatible future changes.

`boundaries={start,window,final}`, each exactly `{original,repeat}`. Start records
are `{sim_tick,complete_state_sha256,weights_frozen}`; window/final records replace
the flag with `candidate_memory_sha256,noncandidate_state_sha256`. Start precedes
thaw and equals parent tick/state and onset−1000; window=onset+window.end_ms*10;
final=onset+cs_duration_ms*10+2000.
Pair records agree at each boundary; coincident window/final clocks require
identical records per side. Exact Boolean start flag requires/forbids immediate
true-to-false thaw; later final state need not equal earlier window state.

Closed projection:

```text
{projection_version:"selected-candidate-w-pair/v1",dtype:"<f8",shape:[m],
 maps:{target_indices,candidate_positions,candidate_edge_indices},original_hex,repeat_hex}
```

Maps are nonempty unique exact nonnegative ordered integers; positions/edges
length=m>0. Each lowercase hex string has exactly16*m characters. Structure checks
allocate no hex bytes/NumPy arrays. Actual 1D ndarray `<f8` encoding uses C-order
bytes without casts. Bind complete expected maps, cardinality and index bounds
BEFORE fromhex/frombuffer; then check finite values/model bounds, preserving
signed zero. Equal candidate hashes require equal W bytes.

Private APIs:

```text
recorder._check_qualification_replay(event, metadata, count) -> None
analysis._encode_candidate_w_pair(first, second, *, maps) -> dict
analysis._decode_candidate_w_pair(projection, *, expected_maps, n,
 memory_count, edge_count, lower, upper) -> (first, second)
analysis._compare_replay_operations(first_event, second_event) -> None
analysis._compare_selected_replay(events, diagnostic, *, metadata, execution,
 expected_source_occurrence, expected_start, expected_maps, n,
 memory_count, edge_count, lower, upper) -> dict
```

Recorder checks structure/local clocks/prior refs/finite scalars against ACTUAL metadata
identity/population/candidate and stimulus hashes; black matches both declarations.
Bind engine_identity.sha256, mbon11_population_size, candidate_identity,
rgb_input_sha256.stimuli[str(seed)][stimulus], rgb_input_sha256.black and
black_input.input_sha256. Dispatch inside _Chain.check before commit.
Metadata declares grid candidates, not selected CS/T/window: preserve later70000.
No analysis import/decode/scan. Analysis binds exact existing plain execution,
source occurrence and start-record expectations, not capabilities. e.3 supplies actual
native parents/maps; f derives PRE state from bound NPZ content (not file SHA),
POST from verified anchor/source/thaw. f uses _verified_qualification_context;
maps are context.candidate_maps.mbon11;
n/layout derive from genuine context/checkpoint_schema memory_w/weight lengths.
Indices obey target<n/position<memory_count/edge<edge_count; lower/upper are actual
minimum_fraction−1/maximum_fraction−1. Context binding precedes numeric decoding.
Recompute float64 W distance via `_state_difference`, response Hz via integer
window-count difference/`_response_rate`; reject mismatches, never invent zero.

Operation comparison excludes EXACTLY:

```text
sequence,scientific_sha256,previous_scientific_sha256,run_metadata_sha256,
branch_id,parent_branch_id,parent_checkpoint_name,parent_checkpoint_sequence,
parent_checkpoint_sha256,parent_state_anchor_sha256
```

Bind these separately; retain WHOLE remaining object through `_scientific`,
including type/sim_ms/version/flags/telemetry. Never use replay.FRAMING.
branch_start adds no invented operation_version.

Comparator drains an externally supplied fixed-prefix iterator, resolving actual
diagnostic/source/anchor/training route and EVERY target-branch event through EOF,
including after diagnostic. Require exact scheduled coverage/inputs/raw bins;
permit only referenced start/thaw/observe, valid original window-stop evidence
after both measurements, and one exact repeat diagnostic. Reject extra/unknown/
unreferenced/subsequent activity. Validate present unique cells, max16 PRE/1 POST;
execution invents no requested-condition list. Retain at most12 operations/bounded
descriptors/keys; semantic errors drain with bounded reasons, iterator errors
and final-binding errors propagate; semantic errors then raise. Recorded state
checks do not reconstruct unrecorded full native history. e.3 adds no408 scans;
f owns global408/768 completeness/PRE reuse.
No new line-allocation bound, checkpoint, proof issuer or cap activation follows.

### e.3 independence and final-owner handoff — complete tiny-native acceptance

Source review and actual 9/51/408 native checks passed on model
`2d07f37e85935f78b522bccb0a60d7f2b9f1d0e5a1475c8d306f12b995766da8`,
with unchanged schema3cc3257…; e.2 runtime evidence above is historical. Assay
compatibility passed. R3 True408 passed in **2,333.98 s**, runner 2,334.437 s,
with no failures/errors/skips. It checked 408 diagnostics (24 PRE + 384 POST),
768 logical cells, sixteen-fold PRE reuse, 1,033 production factories, 128 native
black-retention anchors and 65 durable CPs including caller baseline. All 408 pairs
had native/actual-byte lookup checks; nine external full-prefix e.2 EOF comparisons
covered every cohort, intervention/T combination and PRE. No 408 prefix scans
were added. Both frozen paths/all 30 source members/schema matched before/after.
This four-node tiny-native prefix remains unsealed without scientific outcome.
These checks establish recorded consistency, not response/native-history or
scientific proof.

Acquire both pair engines before either restore. Validate native checkpoint
registration; reject identical Engine/Brain objects and ANY cross-field mutable
buffer overlap among weight plus validated registered fields, between the pair
and still-required owners whose state must survive. Local np.shares_memory must
fail closed on indeterminate overlap; static graph/maps may be shared. No global
registry, historical IDs or extra factory. After BOTH restores, recheck BOTH
actual parent/start states, clocks, frozen flags and maps before EITHER start.
Preserve existing source rehash/occurrence/anchor/EOF checks.

True-only cleanup drops obsolete acquired/donor/recipient/retained/sibling engines
and window/raw/projection references at existing scope boundaries; preserve the
training producer only while acquisition reuse/live-state guards require it.
False/confirmation retains its existing returned training producer and behavior.
True returns the ACTUAL last successful repeat native engine, unchanged engine
type, only after both tails/final checks and successful diagnostic append.
Discard the preceding completed owner before another pair; retain the final
repeat through scratch cleanup. Failure raises without partial-success return.
No reconstructed owner, extra NPZ/checkpoint/factory or rerun.

f authenticates the actual last diagnostic and binds its repeat branch, lineage,
final clock/complete-state hash to this owner before final checkpoint/terminal/seal; owner data
is no trust issuer. The 9/51/408 checks observed **21/130/1,033** production factories.
Parent e implementation acceptance is complete; f/g/formal gates remain open.

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
An earlier bounded actual MaleCNS first-training-prefix sample after the grid
reader is accepted should expose immediate detail-on line/memory/I/O costs before
selected integration. It remains incomplete and cannot replace this integrated
gate or certify later configurations, retentions, repeats or whole-assay capacity.
The 70-second resource pilot used False/False detail flags, not legacy grid detail.
Sample checkpoint size times1602 is not an upper bound; no whole-assay runtime
or storage approval follows from it. A capacity failure is reported, never solved
by dropping ancestry, controls or scientific gates.
