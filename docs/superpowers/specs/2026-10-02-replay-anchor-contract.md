# Bounded Replay Anchor Contract

**Status:** Approved; complete-state hashing, durable-rooted black-retention
reconstruction, persisted occurrence indexing, fixed-prefix verification and
immutable native replay attestation implemented. Shared prefix/terminal scientific
reports are implemented; full producer/CLI integration and fullgraph capacity
remain open.

**Date:** 2026-10-02

This refines Task 7B of the associative-plasticity assay plan. It preserves all
scientific response, timing, control and causal-route gates in the
[pivot design](2026-09-24-associative-plasticity-pivot-design.md). Replay proves
computational reconstruction of a retained parent, not the entire assay history
or biological learning.

## Occurrence and state identities

`anchor_version="state-anchor/v1"` uses `state_anchor_sha256` as a
domain-separated canonical occurrence-envelope digest. A separate
`complete_state_sha256` identifies checkpoint-state content. Equal paired/sham
content is valid; their occurrence references and causal routes remain distinct.

The envelope binds anchor ID, origin branch, integer target tick, complete-state
digest, executable recipe digest, full engine-identity digest, run metadata
digest and the completed source/prefix identity. It also binds the exact durable
checkpoint occurrence: safe inventory name, NPZ file SHA256, origin branch,
checkpoint-event sequence and integer source tick. It excludes the anchor's own
event-chain digest and all later terminal/seal hashes to avoid circular hashing.

The existing analyzer field `source_identity_sha256` retains the validated
`fly-engine/v1` identity's own `sha256` (its complete provenance/group payload
digest, excluding the derived hash itself). The full identity object remains
inside the executable recipe and is bound by the recipe and envelope; do not
replace the established field with a hash-of-identity-including-its-own-hash.

IDs and operation order are deterministic. Recipe, envelope and report bindings
use scientific projection, scientific chain digest, count and sequence
references. Raw-prefix hash and raw byte length are integrity-only verifier/
snapshot/seal bindings; they never enter scientific fields or nested scientific
digests. Otherwise excluded wall-clock telemetry would contaminate reproducible
scientific hashes indirectly.

Append and scan recompute the envelope. Manifest inventory, parent references
and replay attestations use its occurrence digest. Reject duplicate IDs or
occurrence references, late/missing/ambiguous parents, wrong clocks/origins,
both parent kinds and cyclic routes. Every anchor in this slice has a durable
source; recursive anchor-parent recipes are outside scope.

Sealed durable inventory records must match reconstructed event records exactly,
including optional-field presence. Initial prefix creation derives occurrence
fields from durable event bytes before freezing them; it does not trust producer
counters. Truly tick-less legacy checkpoint events/inventories remain readable.

## Complete checkpoint-state digest

One payload constructor supplies checkpoint serialization and live hashing:
complete checkpoint metadata, `weight`, every allocated state array and visual
state including `r8_light`. Include inactive queue/active backing entries and
both candidate memories. Existing provenance, finite-value, native queue and
time validations remain binding; live `sim_ms` equals `cursor * dt`.

Use a versioned domain tag and length-prefixed records. Metadata is strict
canonical UTF-8 JSON with string/sorted keys, fixed separators, no duplicate keys
or nonfinite values, and exact validated scalar types. Sorted named-array
headers bind scalar kind/width, canonical little-endian numeric byte order
(endian-independent for one-byte types), rank/shape and byte length. Logical
C-order bytes preserve integer widths and IEEE bit patterns, including signed
zero. Reject unsupported/object/structured/string dtypes. Exact model dtype and
shape validation still applies; this is not a cross-build portability promise.

Hash a quiescent engine using bounded buffers/conversion chunks, without NPZ
writes or graph-scale byte copies. Keep the NPZ file-byte SHA256 separate.

## Executable black-retention recipe

Implement only `black-retention/v1` first. Store or reconstruct canonical recipe
data from verified operations; a recipe hash alone is insufficient. Bind the
durable occurrence, source/target ticks, full engine identity, black uint8 RGB
shape/generator/hash and every ordered observe call and relevant argument.
Calls use `learning=False`, no external stimulation and at most 500 ms, including
the exact final partial call. Permit at most one explicit thaw before calls;
implicit or unsupported state mutations fail closed.

A shared validated projection constructs and executes the recipe. It covers the
complete contiguous branch-local interval, binding actual operation sequence
references and scientific prefix; interleaved global events are permitted.
Reject omitted, extra, reordered or overlapping operations even if the endpoint
would match. Restore must verify actual NPZ cursor against the declared source
tick. Engine identity and regenerated input hashes must match before advancing.
Only existing `compute_seconds`/`kernel_seconds` hash exclusions remain allowed.

## Verification and terminal boundaries

Ordinary verification returns no replay attestation. Formal verification first
checks the artifact, reconstructs all declared anchors in an isolated compatible
engine, compares exact ticks and complete-state digests, then rechecks artifact
bindings before returning immutable verifier-produced attestation. Partial
failure returns no attested object. Caller-supplied digest sets, Boolean callbacks
and persisted `attested=true` flags are not proof. Preserve repeated artifact
validation in `VerifiedRun.iter_events`.

The producer uses a separate validated-prefix value binding metadata, event count,
raw-prefix length/hash, final scientific hash and durable occurrence inventory.
It is not a fabricated `VerifiedRun`. Shared replay primitives verify this fixed
prefix before pure terminal reduction. Then append the result once, seal,
formally verify and independently analyze; canonical reports must agree.
Nonmaterialized parents and verification mode belong inside that shared report.

The implemented report exposes computed `integrity-only`/`native-replay` mode
and sorted used anchor-occurrence parents. Formal verification with no anchors
still reports native mode; caller arithmetic inputs cannot issue it. Missing
terminal reports keep truthful labels and provenance while remaining inconclusive.
Terminal framing consumes no scientific evidence budget or branch science;
validated streams still drain completely and sealed terminal bindings are checked
independently. Honest partial native acceptance proves report equality, not full
training acquisition, qualification or a supported assay.

Prefix creation checks the entire current checkpoint directory. Later consumption
rechecks every represented snapshot file and exactly the saved event byte boundary;
subsequently appended bytes/files, including incomplete tails, are outside that
proof. Sealed verification still checks the complete event stream and inventory.

## Scope, compatibility and capacity

Allow one bounded temporary retention NPZ for independently restored sibling
tests. Validate it against the complete-state digest, keep it outside sealed
inventory and discard it after the sibling group. Formal ancestry still names
the recorded anchor. This avoids replaying retention for every A/B/C sibling.

Retain selected ordinary training ends and intervention states durably: at least
66 occurrences for eight cohorts, plus any necessary distinct baselines. Before
source freeze, measure/project durable and peak scratch bytes, engine/restore/hash
memory, event bytes, restore counts, simulated retention time and both pre-seal
and post-seal verification costs.

Current scans rebuild recipes with linear earlier-prefix rereads per anchor and
rehash represented durable files. Measure that multiplication at the capacity gate,
not just the bounded count of verifier-engine constructions.

Discarded-grid training ancestry remains a later explicit decision: compare
measured durable-storage cost with a separately reviewed exact training-replay
grammar. Do not build a general interpreter now or accept incomplete exploratory
ancestry to reduce storage. A tiny correctness pilot does not prove fullgraph
capacity.

Keep the current exact packaged-schema binding policy: older pre-formal WIP
seals require their matching code/schema revision and are not silently migrated.
No persisted content-digest anchor is reinterpreted as the occurrence format.
Formal artifacts are produced only after the revised source/schema freeze.

The first acceptance slice is a real durable source, black retention, one anchor
and two independent test forks, including identical paired/sham content on
different routes. It tests digest completeness/nonmutation, recipe-prefix
agreement, append/scan/schema parity, actual immutable replay attestation and
artifact mutation rejection. Changing only excluded operational timings must
preserve recipe/envelope/report scientific identities while changing raw
integrity bindings. Shared prefix/terminal report equality is now implemented and
tested. Discarded-grid replay, producer-wide integration, CLI and formal assays
remain subsequent work.
