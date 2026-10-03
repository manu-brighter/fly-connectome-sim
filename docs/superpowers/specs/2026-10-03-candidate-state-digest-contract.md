# Candidate and noncandidate state digest contract

Status: implemented and independently reviewed; final opt-in complete suite passed.

Date: 2026-10-03. Source baseline: `7c398f8c64fb315a2fe13ce294a38b920978989f`.

This refines the approved associative-plasticity pivot's causal memory
interventions. It changes no candidate, endpoint, scientific threshold, native
equation, checkpoint archive format or qualification gate.

## 1. Meaning and scope

`candidate_memory_sha256` identifies the ordered candidate `memory_u`,
`memory_w` and `weight` content, its exact selection map, and immutable model
provenance. It excludes neuronal state, clock and occurrence labels.

`noncandidate_state_sha256` identifies the complete checkpoint state with only
those three selected components omitted. It retains full checkpoint metadata,
every registered array's original schema, and the exact exclusion map. It
includes the clock through checkpoint `cursor` and the immutable model's `dt`.
Actual live `sim_ms == cursor * dt` is validated separately before either digest
is produced; a contradictory `sim_ms` must reject, not yield a digest.

These are SHA-256 content digests, returned as 64 lowercase hexadecimal digits.
They are distinct from complete-state SHA-256, raw NPZ file SHA-256, legacy raw
array digests and durable checkpoint/event identities. Existing values from
those domains must never be relabelled as either new digest.

No branch, condition, seed, training ID, route, donor/recipient role, archive
path or event ID enters either content preimage. Actual engine/group identity,
the declared candidate name, clock and durable occurrences remain independently
bound by the producer and existing artifact/event contracts.

## 2. Live API and ownership

Add one public method on `MemoryBrain`, inherited by `VisualMemoryBrain`:

```python
def candidate_state_digests(
    self, target_indices: np.ndarray, *, chunk_bytes=HASH_CHUNK_BYTES,
) -> dict[str, str]:
    ...
```

The result has exactly `candidate_memory_sha256` and
`noncandidate_state_sha256`. One call validates a single quiescent live state
and computes both digests. It does not write files, mutate or freeze arrays,
replace candidate memory, construct a `CandidateMemory` snapshot, or advance
time. The caller must already have locked model provenance, normally by calling
the owning `FlyEngine.identity()`. Missing/broken lock raises `RuntimeError`;
invalid state, arguments or maps raise `ValueError`. No partial result returns.

The caller keeps the brain and target array quiescent for the entire call.
The method is synchronous; it provides no concurrency locking or isolation from
external mutation. Recheck the existing model lock before returning. This
detects the changes covered by that lock, not adversarial mutation of storage
through external aliases.

Keep the implementation in `neural/brain.py` and `neural/checkpoint.py`.
The narrow private codec seam is:

```python
def _candidate_state_digests(
    metadata, arrays, *, target_indices, candidate_positions, edge_indices,
    chunk_bytes=HASH_CHUNK_BYTES,
):
    ...
```

`metadata` and `arrays` are the borrowed complete `_checkpoint_payload()`.
The three map inputs are one-dimensional integer ndarrays validated against
the actual brain by the live method. The codec also checks their local shape,
type, nonnegative uint64 range, ordering and uniqueness, the positions against
memory lengths and edges against weight length, and all array values before
excluding any. Population bounds and edge-to-target authenticity belong to
the live method. The codec cannot authenticate a model, a group or an
edge-to-target relation from arbitrary caller-created dictionaries.

Reuse `_canonical_json`, `_validate_chunk_bytes`, `_array_chunks` and
`_update_bytes`. Extract small private helpers for numeric headers, framed
array records and streamed finite checks where useful. Do not introduce a
general serializer/virtual-array framework or alter existing complete-state
preimages, public checkpoint APIs, raw vector digests, NPZ formats or native
code. There is no new public snapshot-hash or archive-hash API in this slice.

## 3. Exact candidate map

Let `T` be the supplied ordered targets, `P` the selected circuit positions,
and `E = circuit["edges"][P]` the corresponding global graph edge IDs.

- `T` must be a plain ndarray, rank one, nonempty, integer kind `i` or `u`
  of width 1/2/4/8 bytes, with unique values in `[0, n)`. Reject bool, float,
  object, structured, masked and other ndarray-subclass inputs. No coercion
  from lists or floating indices. Endian variants and integer widths with
  the same values are accepted and canonicalized as specified below.
- `P` is exactly the ascending sequence of positions whose global edge's
  postsynaptic neuron belongs to `T`, using the existing candidate selection
  rule. No caller-supplied partial selection is accepted. `P` is nonempty,
  unique and in range of both memory arrays and `baseline_plastic`.
- The live circuit edge array must be rank one, integer, nonempty, unique,
  and in global edge range before it is used for indexing. Selected `E`
  preserves circuit order; it is not sorted to form candidate vectors.
  Both selected memory arrays and the weight array are rank one. Circuit,
  baseline and memory lengths must agree.
- The selected map as a whole must be nonempty. An individual valid target may
  have no selected edges, consistent with existing candidate selection; its
  identity still enters `T`. The producer must reject targets that differ from
  its declared candidate group, whether or not those targets select edges.
- `T` order is significant: a permutation yields a different map and both
  digests, even when it selects the same edge set. The producer supplies the
  exact ordered declared group. Do not sort targets or silently canonicalize
  group permutations. This binds the declaration while leaving triplet order
  in circuit order.

The canonical map consists of three named arrays: `target_indices = T`,
`circuit_positions = P`, `edge_indices = E`. Their wire dtype is always unsigned
64-bit little endian, rank one. This is deliberate normalization of index
representation only; numeric state widths are never normalized. Conversion
must be range-checked before conversion and streamed in bounded chunks.

For example, `circuit["edges"] == [4, 1, 3]` and `P == [0, 2]` give
candidate `E == [4, 3]`. Candidate vectors use memory positions `[0, 2]` and
weights `[4, 3]`; weight exclusions traverse `[3, 4]`. The exclusions for
`memory_u` and `memory_w` are `P`; those for `weight` are `sorted(E)`.
All other arrays have no exclusions. Selected `rate_kc` entries remain included.

## 4. Full live validation before projection

The live method must finish all these validations on actual live values before
returning either digest or treating any value as excluded:

1. Validate `chunk_bytes` using the existing strict integer, minimum-eight-byte
   contract. Require and assert the existing model-provenance lock. Borrow the
   complete payload. Validate its provenance against the locked model identity,
   its exact metadata key set, cursor/total-spikes types and ranges, boolean
   `weights_frozen`, and actual finite `sim_ms == cursor * dt`. Require actual
   `dt` to equal the locked model's supported `parameters.neural_dt_ms`; an
   unsupported value changed before locking is invalid even at cursor zero.
   Authenticate the plain integer positive population size against the locked
   graph cardinality and required native state shapes before native validation
   or target selection. Mutable `n` is not an independent authority.
2. Enforce the complete-state field registration check: no duplicates in
   `fields`, exact equality to `initial` registration, and exactly `weight`
   plus every registered field in the payload. Require actual array shapes
   and dtypes to match authoritative native/visual state schemas as well as
   checkpoint templates (weight is float32 with `post.shape`). Required fields
   cannot disappear by coordinated edits to both `fields` and `initial`, before
   or after locking; coordinated template/live shape or dtype edits cannot
   redefine a required native field's schema. Preserve legitimately registered
   extensions and bind their complete actual state, with registration/template
   integrity captured independently at model locking. Required native schemas
   originate at construction; required visual schemas follow the actual visual
   configuration, not merely whether the mutable registry still lists them.
   Reject ndarray subclasses at this new live boundary,
   including masks; do not validate a projected or sanitized replacement for
   the actual arrays. No extra or silently missing array is accepted.
3. Check supported numeric kinds/widths and finite values across **all** arrays,
   including selected/excluded entries. Use bounded numeric chunks for finite
   scans. Validate native state using the existing `validate_native_state`,
   including active membership/flags, queues, counters and trace timestamps.
4. Validate the exact map above. For the selected live triplet, require the
   existing replacement rules: finite `u`, `w` and weight; both memories in
   `[minimum_fraction - 1, maximum_fraction - 1]`; weight consistent with
   `(baseline_plastic[P] * (1 + memory_w[P])).astype(weight.dtype)` using
   `rtol = 2 * finfo(weight.dtype).eps`,
   `atol = finfo(weight.dtype).tiny` and default `equal_nan=False`.
   Perform these checks on bounded selected blocks if needed. They validate
   existing live values, not values reconstructed and substituted for hashing.

Complete-state hashing alone currently does not check the selected triplet's
rule bounds or baseline-derived weight consistency. Calling it and then
discarding the resulting hash is not a substitute for item 4. This slice does
not add new physiological validity rules for untouched state: its finite,
schema and native checks remain the checkpoint checks. The candidate rule
checks above are explicit additional requirements of these new digests.

Preserve values bit-for-bit in the preimage, including small accepted weight
rounding differences and signed zero. Never recompute weight for serialization,
clamp a memory, clear inactive storage, zero a trace, or omit an invalid value.
Read-only state arrays are valid hash inputs; destination writability is a
replacement requirement, not a hashing requirement.

## 5. Normative wire encoding

All lengths/counts are unsigned little-endian 64-bit integers, denoted `U64`.
Reject a length outside that range. Concatenation below is literal byte
concatenation; no whitespace, separator or terminator is implicit.

`J(x)` is precisely the checkpoint `_canonical_json(x)`: strict JSON types and
string keys, sorted keys, compact separators, `ensure_ascii=False`, finite
numbers, UTF-8, no BOM. No scalar/key coercion, Unicode normalization or custom
float formatting. Duplicate JSON keys are rejected if parsing an external
encoding with the existing strict parser; the live codec accepts dictionaries.

For a named logical array `a`, its header is exactly:

```text
H(name, kind, itemsize, shape) = J({
  "name": name,
  "kind": kind,
  "itemsize": itemsize,
  "byteorder": "independent" if itemsize == 1 else "little",
  "rank": len(shape),
  "shape": shape,
  "nbytes": product(shape) * itemsize
})
```

As in the checkpoint codec, scalar shape is `[]` with one element; an empty
dimension gives zero elements. Signed/unsigned widths 1/2/4/8 and IEEE float
widths 4/8 are supported; bool, complex, object, string, structured and subarray
dtypes reject. Numerical payload bytes use logical C order and little endian,
independent of strides or physical order, preserving IEEE signed-zero bits.

A standard array record, identical to the existing checkpoint record, is:

```text
A = b"A" + U64(len(H)) + H + U64(nbytes) + canonical_array_bytes
```

The map block is exactly:

```text
G = b"G" + U64(3)
    + A("circuit_positions", uint64, [len(P)], P)
    + A("edge_indices", uint64, [len(E)], E)
    + A("target_indices", uint64, [len(T)], T)
```

Map records therefore use lexicographically sorted names. A selected candidate
array has the original state kind/itemsize, rank one, shape `[len(P)]`, and
`nbytes = len(P) * itemsize`. No original complement bytes enter it.

Let `I` be the complete checkpoint metadata with exactly the three mutable
keys `cursor`, `total_spikes`, `weights_frozen` removed. This is the full
immutable model provenance, not its hash alone. The candidate preimage is:

```text
b"fly-connectome-candidate-memory/v1\0"
+ b"M" + U64(len(J(I))) + J(I)
+ G
+ b"C" + U64(3)
+ A("memory_u", selected memory_u[P])
+ A("memory_w", selected memory_w[P])
+ A("weight", selected weight[E])
```

The candidate component records are in the shown lexicographic order.
Selection order inside each is the common circuit order.

For noncandidate content, every original complete-state array gets one
projection record. `H_original` uses its **original complete shape, rank,
kind, itemsize and nbytes**, even when every element is excluded. Let `X` be
its strictly ascending exclusion index sequence, or empty for every array
other than the three named components. Nonempty `X` is allowed only for a
rank-one array, with unique indices in range. Define:

```text
R = b"E" + U64(len(H_original)) + H_original
    + b"X" + U64(len(X)) + concatenated_U64_indices(X)
    + U64(original_nbytes - len(X) * itemsize)
    + canonical_bytes_of_nonexcluded_elements_in_original_C_order
```

The noncandidate preimage is exactly:

```text
b"fly-connectome-noncandidate-state/v1\0"
+ b"M" + U64(len(J(metadata))) + J(metadata)
+ G
+ b"N" + U64(len(arrays))
+ R_for_each_array_in_lexicographic_name_order
```

Even arrays with no exclusions use `R` with `X` count zero, not `A`. The
original header and explicit indices disambiguate equal-looking complements.
The codec derives the three `X` sequences from the map, rather than accepting
an unrelated exclusion dictionary. Full field names, counts and original
schemas remain bound when the complement is empty.

Domain bytes include the shown final NUL. The map and projection markers and
all framing bytes are included in the SHA-256 preimage. Framing is unaffected
by `chunk_bytes` or iteration partitioning.

## 6. Streaming and memory scope

Borrow the complete live arrays. For noncandidate `memory_u`, `memory_w` and
`weight`, visit basic slices between consecutive excluded indices and stream
each slice with `_array_chunks(..., canonical=True)`. Do not allocate a
graph-sized boolean exclusion mask, fancy-indexed complement, concatenation
of retained slices, full weight copy, or complete `.tobytes()` buffer.

For selected candidate values, gather at most
`max(1, chunk_bytes // itemsize)` values at a time in the specified index order;
then stream their canonical bytes. Do the same for canonical uint64 map/index
encoding. Sorting global excluded edges may allocate `O(candidate_edges)`;
never sort the full graph-weight array or reorder the candidate payload.
Untouched arrays use the existing canonical numeric chunk iterator.

Every numeric conversion/gather buffer is bounded by `chunk_bytes`; finite
checking may additionally allocate a boolean buffer proportional to that
numeric chunk. Every byte piece passed to SHA-256 update is at most
`chunk_bytes`, including domains, JSON and lengths. Canonical metadata and
header JSON may be materialized, as in the existing codec; this is not a
constant bound on metadata size. Array headers and map headers are small;
map index values are streamed, not placed in a large JSON list.

This is a bounded **encoder buffer** guarantee. Brain construction, immutable
provenance computation, target/circuit validation and selection, map arrays,
sorting, native validation (`unique`, membership/masks), and separately needed
intervention snapshots have their own allocations. They are not claimed to be
fixed-buffer bounded. Candidate storage may itself scale with the selected
population. Do not describe the whole call or assay as constant-memory.

## 7. Producer compatibility, clock and evidence bindings

`CandidateMemory` remains an immutable detached triplet/map/clock snapshot; it
does not carry source-engine provenance or neural-group identity. A digest of
a snapshot must not be treated as self-authentication. This slice hashes live
state, and creates no standalone snapshot digest API.

Before donor transfer, the later producer must obtain actual donor and
recipient `engine.identity()` values and require exact canonical identity
equality, including all neural groups and model provenance. It must also check
the actual ordered group arrays against that identity and the frozen declared
candidate group (MBON11 for the approved primary assay), and check exact
target/circuit-position/global-edge map equality. A cached engine identity
alone must not conceal a replaced or changed current group declaration.

Both live brains must pass the new validation and have the same actual
`cursor` and `sim_ms`, the same `dt`, and the recorded training-end ticks. Keep
the donor quiescent across its digest and snapshot capture. Check the snapshot's
targets, ordered edges and clock against that captured source and destination.
For necessity, use the independently validated time-/exposure-matched reference
at the common training-end clock; do not relabel a clock-zero snapshot by
editing its clock. The content digest alone intentionally cannot detect that.

Existing `replace_candidate_memory` already validates snapshot type, plain
arrays, clock type/value and recipient-clock equality, target validity,
recipient-derived edge identity/order, component shape/dtype/finite values,
memory bounds, baseline-derived weight consistency and writable destinations.
It stages copies before assignment and writes only the three selected slices.
It does **not** verify donor provenance, group identity, training history,
durable occurrences, full recipient validity, or that an input snapshot really
came from the declared source. Preserve all existing checks; producer checks
above supplement them.

For each intervention, compute recipient digests immediately before replacement,
perform only `replace_candidate_memory(snapshot)`, and compute recipient digests
immediately after. No observe, restore, decay, freeze toggle, clock assignment
or trace edit may occur inside that bracket. Bind the values to independently
recorded source/recipient identities, common clock and durable checkpoint
occurrences using the current artifact contract. Obtain the donor digest at
the source capture point. Do not substitute full-state or NPZ digests into
component fields.

The existing analysis equality gates remain intact:

| Relation | Required result |
| --- | --- |
| All interventions: recipient noncandidate before vs after | Equal |
| All interventions: recipient candidate after vs donor candidate | Equal |
| Sham: recipient candidate before vs after | Equal |
| Necessity/sufficiency with distinct accepted donor triplet bytes | Candidate before differs from after |
| Training-end candidate vs declared donor/recipient-before occurrence | Equal for the referenced occurrence |
| Recipient training-end noncandidate vs intervention before | Equal |

Necessity/sufficiency need not change candidate content when the source content
is already identical; that is a valid negative/control outcome, not a reason
to fabricate different hashes. Candidate digest equality is possible across
different clocks or neuronal states; compatibility and common-clock checks
remain mandatory. Noncandidate equality across donors and recipients is not
required. Scientific gate success cannot be inferred from these digest
relations alone.

## 8. Acceptance and verification

The implementation must add focused tests; this design task runs none.

1. Independent wire vectors for **both domains**, constructed from literal
   metadata/header bytes, explicit framing with `struct.pack("<Q", ...)`,
   and literal numerical bytes. Expected preimages must not call production
   canonical/header/map/projection helpers. Include a map with ascending `P`
   and unsorted `E`, a retained float negative zero, and a component with empty
   complement. Check the candidate and noncandidate SHA against independently
   assembled preimages, and verify both differ from complete-state/raw hashes.
2. Existing tiny native intervention fixture: necessity, sufficiency and sham
   satisfy every equality above, including different donor neuronal state.
   Preserve existing atomic replacement/rejection and passive-decay tests.
   Also select both targets of the fixture with circuit edges `[1, 0]`, so
   ordered candidate weights and sorted weight exclusions exercise distinct
   index spaces; the one-target case alone cannot prove this.
3. Change each untouched registered field, including visual fields, inactive
   queue/active backing, trace timestamps, candidate-associated `rate_kc`, and
   every valid mutable metadata scalar. Noncandidate hash changes; candidate
   hash remains equal where its triplet/map/model is unchanged. A change that
   violates invariants rejects instead of returning a misleading hash.
4. Change untouched `memory_u`/`memory_w` entries or nonselected global weights:
   noncandidate changes. Apply accepted candidate-only replacements:
   noncandidate stays equal; changed candidate bytes change candidate digest.
   Bind different valid target order/map identities even if all numeric
   values and concatenated complements happen to be equal.
5. Reject missing/empty/wrong-type/duplicate/out-of-range targets and maps,
   groups with no selected edges, missing/extra/duplicate state registration, wrong
   dtype/shape, masked arrays, invalid clocks and invalid native state. Include
   coordinated required-field removal/template changes before and after locking,
   locked-extension omission, unsupported actual dt at zero/nonzero clocks and
   invalid or graph-inconsistent n, including a nonexistent edge-free target
   alongside a valid selected target.
   Inject NaN/Inf, out-of-bound candidate memories and inconsistent candidate
   weights **inside excluded entries**: no digest may return. Test unlocked
   and diverged model provenance. Bind a valid target with no selected edges
   in the map rather than silently dropping it; later producer tests must
   reject any mismatch with the actual declared group. Invalid calls leave
   state unchanged.
6. At the codec seam, equivalent C/Fortran/strided/endian data encodes equally;
   names, numeric widths, rank and original shape remain discriminating.
   Canonical index widths/endian normalize as specified. Signed zeros in either
   included candidate content or retained complement remain distinguishable.
   Empty ordinary state arrays encode; empty candidate maps reject; fully
   excluded component arrays preserve their original header and map.
   The live API still rejects state dtypes/shapes incompatible with its native
   templates, even if the lower-level codec could encode them.
7. Check equality across chunk sizes including 8 and nonmultiples of itemsize;
   instrument numeric buffers and SHA updates. Guard against full-array copy,
   `tobytes`, `astype`, `byteswap`, contiguous conversion, concatenation and
   full exclusion masks in the encoder. Exercise a large synthetic weight
   array with sparse unsorted selected global IDs. Do not apply an alleged
   fixed-memory guard to documented selection/native-validator allocations.
8. On the tiny fixture, save/restore a valid complete checkpoint and confirm
   the two live digests are preserved. Existing compressed/plain complete-state
   parity tests remain unchanged. No new archive codec is exposed: future
   archive hashing would require full archive validation plus explicit parity
   tests and a separate design decision about materialization.
9. Add an opt-in actual fullgraph **read-only hash** integration test using an
   existing/fullgraph `FlyEngine` and its declared MBON11 targets. Capture
   complete-state SHA and scalar/array-reference metadata, call the new API
   twice at quiescence, then confirm identical component digests and unchanged
   complete-state SHA/scalars/references. Use streamed complete-state hashing;
   allocate no extra graph-scale snapshot/copy/archive solely for this proof.
   Do not run observe, training, qualification or a capacity benchmark merely
   to establish read-only hashing. Execution is owned by the implementation
   coordinator, not this design task.

Implementation ownership: the subsequent implementer owns the two neural
modules and relevant checkpoint/fullgraph tests under the coordinator's plan.
Engine/analysis/recorder producer changes are outside this slice. Existing
analysis functions check hash syntax and equality, not digest recomputation;
native producer adoption must supply this contract and provenance checks
before these fields can represent actual state evidence. No positive learning
or qualification claim follows from completing the serialization slice.

Implementation evidence (2026-10-03): one live method/private codec, independent
literal wire vectors, real native interventions/restore, invalid-state and
bounded-encoder regressions. The independent review's three Important
validation findings and one Minor coverage gap were fixed and a scoped
re-review found no remaining issues. Final root complete opt-in suite:1190 passed
in322.64s, including actual fullgraph read-only digests and checkpoint replay.
Full assay acquisition, producer compatibility checks and formal capacity/
qualification/confirmation remain separate work.
