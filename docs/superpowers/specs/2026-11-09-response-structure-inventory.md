# Recorded response structure — bounded offline inventory

Status: prospectively accepted after independent protocol and builder review.
At protocol freeze, no new composition calculation had run. This follows the
accepted negative motor v1/v2 results;
it is a different descriptive question, not another decoder threshold candidate.

## Question and fixed source

Does the existing matched-state diagnostic contain differences in response
composition, beyond a common scaling of activity? Use the accepted
[34-second diagnostic](../../experiments/2026-11-09-market-response-diagnostic.md)
only. Do not construct a model, acquire data, choose neurons, regroup cells,
fit a classifier, map drinks or change any accepted source/artifact.

The source has eight arms, each with eight 500-ms windows. Preserve the exact arm
order: control-1/black, vertical-left/A, vertical-right/B, vertical-left-repeat/A,
control-2/black, horizontal-top/C, horizontal-bottom/D, horizontal-top-repeat/C.
Window index7 (model5.5–6.0s) remains primary. Report every window0–7 (model2.0–6.0s)
as the complete secondary course; the primary is part of that course, not another
independent observation. The four initial black-prefix observations are validated
but excluded from the arm-comparison matrix.

Freeze **all28 unordered arm pairs at each of eight matched window indices**:
224 comparisons, including28 primary comparisons. Mark the three identical-frame
pairs as repeat checks at every window. Retain all other contrasts, including
weak, silent and negative results. Windows and deterministic repeats are not
independent biological replicates. This is later development characterization,
not a new experiment or a replacement primary endpoint.

## KC partition and population profiles

Use21 fixed KC buckets: the original20 disjoint eleven-cell groups plus one
explicit `excluded-sampled-kc` bucket containing the eleven excluded recorded KCs.
The extra bucket is not a21st drink channel. Verify disjointness and coverage of
all231 recorded KCs in the256-cell cohort. Group entries are cohort slots, not
model indices. Do not claim coverage of all4064 model KCs; other full-graph KCs
were not individually recorded. Preserve the original header/grouping hashes.

For each arm/window derive bucket counts from all50 original10-ms cell bins.
Check the first20 values against the accepted inspector's `group_counts` and
the21-bucket total against the directly summed231 recorded KC slots. Report all
counts, total, normalized bucket shares and the excluded bucket's share. At total
zero retain raw zeros and set shares to null, rather than inventing a distribution.

Separately report all seven populations in their fixed order:
`pam11,ppl101,kc,mbon07,mbon11,motor_left,motor_right`. Derive counts from original
native `group_spikes` bins and retain declared membership and population size.
Per-neuron rate is `count/(population_size*0.5s)` and must agree with validated
telemetry. Membership may overlap: the seven populations are **not** assumed to
partition distinct cells. Do not compute biological composition shares or total
variation across these seven populations.

## Exact arithmetic and zero handling

For nonnegative integer vectors `x,y`, define algebraic component sums `X,Y`.
For `X>0,Y>0`, exact common scaling holds iff every `x[i]*Y == y[i]*X`.
Use exact integer arithmetic, not floating tolerances. For KC buckets this means
equal composition. For the seven populations it means a common scale factor in
the recorded profile; their summed counts are not a distinct-cell total. Fixed
population sizes make this scaling test equivalent for their per-neuron rates.

For KC buckets only, report descriptive total variation:

```text
numerator   = sum(abs(x[i]*Y - y[i]*X))
denominator = 2*X*Y
TV = numerator/denominator
```

Store reduced exact fractions with canonical nonnegative decimal-string
`numerator` and positive decimal-string `denominator`, so JSON consumers do not
lose large-integer precision. This also applies to normalized shares. A separate
finite decimal TV value may aid display but cannot determine any relation or
acceptance. Raw counts remain nonnegative JSON-safe integers; reject bools,
negative/fractional counts, mismatched or empty vectors. Intermediate products
use Python integers without rounding.

All derived component sums, including `algebraic_component_sum`, use canonical
nonnegative decimal strings too: sums may exceed2^53-1 even when each input count
is JSON-safe. Do not reject otherwise valid vectors merely because their sum
exceeds that range. Population sizes and raw individual counts remain integers.

Relation labels: `proportional`, `nonproportional`, `both-silent`, `one-silent`.
When either sum is zero, composition/scaling comparison and TV are undefined:
retain the relevant silence label and null fractions, never zero or maximum TV.
Report absolute counts/totals alongside all normalized quantities. Do not call
any nonzero difference useful, significant or semantically meaningful; one spike
can change an exact relation. No fitted cutoff, classifier accuracy, ranking of
best windows or scientific pass flag is introduced.

## Complete source inspection and output

New external analyzer only; preserve the package, v1/v2 decoders, old diagnostic
runner, supervisors/helpers, source locks and all original reports. Reuse the
frozen diagnostic module's `_read_protocol(output, expected)` and its private
`_summarize(run, protocol, protocol_hash)` within a single bounded
`snapshot_recorded_run` context. After complete existing validation, iterate the
same immutable `VerifiedRun` through EOF again to derive the new vectors. Do not
validate one copy and then calculate from mutable original files.

Own both event iterators explicitly until closed. The frozen inspector retains
its iterator in an exception traceback, which can outlive snapshot cleanup on
Windows. Pass it a minimal view of the same verified run's manifest and mode,
whose `iter_events()` returns the analyzer-owned iterator under `closing`.
Close that iterator before snapshot teardown even when the traceback is retained;
the second analysis iterator is separately owned. This changes no inspected bytes.

Require expected protocol, raw manifest and raw events SHA256 values from the
caller. Verify them against the exact inspected bytes. For the actual source:
protocol `f125b9449594fcbb5d4da751bba39ba2a3014fb00e12af94dc36dc153e318492`,
manifest `d495de34c84e9b696ab01efcf06ece2bb0e3533b48f0e7b134112ed2c32245b9`,
events `96ce14faddcbb63e2bfb2417834f14fe93b8cb08f7b40d8a28000cb68ec0a605`.
The existing source/protocol checks remain strict; do not weaken them or rewrite
old metadata to make inspection pass.

Reuse exact old limits:2MiB manifest,1MiB event line,64MiB events,79 events,
three checkpoints,64MiB each. Validate all79 events/68 observations including
prefix, restore/fork semantics and repeats. Analyze only the64 declared arm
windows. Bound the canonical report to4MiB and publish exclusively to a new path
with the existing safe writer; collisions/linked paths or invalid input produce
no success report. No native/network mode, configurable thresholds or reset exists.
Explicitly validate the output parent with the existing `_safe_directory` helper
and check the exact encoded JSON bytes including their terminal newline before
publication; the exclusive writer alone does not enforce these two conditions.

Report version `market-response-structure/v1`, scope
`historical-development-response-inventory`, verification `integrity-only`.
Include actual analyzer and reused-source hashes, pinned source identities,
cohort/grouping declarations and memberships, all64 arm/window vectors, all224
paired results, primary flags, exact-repeat labels and a summary of relation
counts. For population sums name the field `algebraic_component_sum`; do not call
it a whole-brain total. Retain existing repeat-validation results separately.
Artifact integrity and this analysis are not native replay attestation.

## Interpretation and stopping rules

If every non-silent KC contrast is proportional, this aggregation/resolution
provides no compositional distinction; stop this composition-based route there.
If nonproportional contrasts exist, retain their magnitudes and absolute support
and conclude only that response structure may warrant a separately specified
calibration/generalization question. It does not authorize a drink decoder,
another acquisition, twenty-slot coverage or Stage C.

If bindings, bucket coverage, arithmetic, repeat validation or recorded support
fail, preserve the failure and make no positive inventory claim. A repeat mismatch
cannot be hidden by normalization or attributed to input without explanation.
The user would need to decide if long abstention or persistent drink bias is an
acceptable product tradeoff; this inventory does not silently decide that for them.
