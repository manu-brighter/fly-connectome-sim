# Recorded cell activity replay — 2026-11-07

Status: authorized sequential product continuation; implement and review before
one bounded acquisition. The research assay remains parked. This extends the
reviewed static-anatomy presentation, not its scientific conclusions.

## Measurement and passive capture

Actual inspected interfaces: `engine.py:FlyEngine.observe` advances existing
`rgb_step` calls of at most 100 ticks (10 ms), then reduces returned cell counts
to seven group sums. `kernel.cpp` increments `counts[i]`; it does not return
individual spike timestamps. `feed_event_session.py` already bounds the session
to 240 feed observations plus four 500 ms card observations and 1,160 bins.

Add an optional passive observer at that existing Python bin boundary. It copies
only a validated, fixed cohort from the returned integer count vector, with exact
start/end ticks, observation ordinal and within-observation bin ordinal. Do not
change C++, native calls, call order/durations, sensory inputs, plasticity flags,
state updates, original group reductions or telemetry schema. The default path
remains observer-free. Never pass writable native/state arrays to the observer.
An observer failure stops acquisition and leaves incomplete evidence; do not
silently disable recording and continue. No cell detail derived from group sums.

Before acquisition, tests must compare observer off/on from identical synthetic
native test states: the full checkpoint numeric state, counters, RNG state where
present, original aggregate telemetry and scientific hashes must be equal.
Wall-clock performance fields need not be equal. Include multiple observations,
short frame-tail bins, explicit black frames and attempted mutation of copied
observer values. Reuse existing small-native test fixtures, not a second fullgraph
production run. Callback dispatch must not bypass source locking.

## Fixed cohort and static connections

Select before any input or measured outcome. Use group indices from the actual
locked engine identity, join to real graph IDs, and deduplicate by model index:

1. Include every cell in PAM11, PPL101, MBON07, MBON11, DNa02 left and right.
2. Sort remaining KC cells by numeric source ID. Fill the remaining capacity up
   to 256 cells with ordered stride indices `floor(i*N/K)`, `i=0..K-1`.
3. Sort the final cohort by source ID and preserve each cell's complete group
   membership. Reject a mandatory union over 256; do not silently drop a group.

Read only outgoing `ptr` ranges for these cells and retain existing `post` targets
inside the cohort. Preserve direction and original graph-edge index. Sort eligible
edges by source ID, target ID, then edge index; use the same ordered stride rule
to display at most 512. Record eligible/displayed edge counts. An empty induced
graph is valid, not a reason to choose different cells. Do not add bridge cells,
infer missing edges or optimize selection after seeing activity.

Topology binds existing prepared `ptr`/`post` array locks and engine identity.
Lines mean **existing directed model connections**, not measured transmission,
axon trajectories or spatial synapses. Omit dynamic weights, currents, propagation
particles and plasticity displays. `weight` is not needed for an adjacency view;
if retained as metadata it must be explicitly labelled a fixed model snapshot,
not a measured synaptic current or changing connection strength.

Join source IDs to the already locked annotations and actual `somaLocation` only.
Reuse the anatomy generator's verified join rules. Record absent coordinates as
null, count them and retain their measurements. Never substitute `tosomaLocation`.

## Artifact and verification contract

Keep ordinary session recording/plan schemas unchanged. A bounded raw detail
JSONL contains a header fixed before advancement (version, engine identity,
cohort/selection rule, topology, source/array hashes, nullable coordinates), then
one record per original bin with source ticks, observation/bin ordinals and the
ordered integer count vector. Flush incrementally; incomplete output remains
explicitly incomplete, with no successful completion declaration.

After the ordinary run seals and exports successfully, independently validate
raw detail and export optional `cell-activity.json`, version
`replay-cell-counts/v1`. This is a small sidecar, not a new recording/provenance
framework. Its closed fields are:

```text
version, tick_ms: 0.1
binding: {recording_sha256, raw_detail_sha256, engine_identity_sha256,
          graph_ids_sha256, graph_ptr_sha256, graph_post_sha256, annotations_sha256}
selection: {method: "mandatory-groups-kc-stride/v1", limit: 256,
            group_population_counts, group_selected_counts}
cells: [{model_index, source_id, groups, soma: [x,y,z] | null}, ...]
topology: {method: "induced-directed-edge-stride/v1", limit: 512,
           eligible_edges, edges: [[graph_edge_index, source_slot, target_slot], ...]}
bins: [{observation_index, bin_index, start_tick, end_tick, counts: [integer,...]}, ...]
display: {window_ticks: 1000, mode: "last-completed-whole-bin-window/v1"}
```

Counts are nonnegative integers, at most the native bin's duration in ticks per
cell; no booleans, fractions or inferred timestamps. Indices/IDs are unique and
in range; reject duplicate/unknown fields, oversized inputs and inconsistent
coverage. The producer and an independent raw audit must verify every bin against
the exported recording's exact source interval/order. Bins cover the continuous
session without gaps, overlap, omission or duplicates. Every fully selected group
must reconcile exactly per bin; selected KC sums cannot exceed its full group.
Independently check selected IDs/coordinates/edges against the locked source.

Hash original recording bytes, not reserialized JSON. Bind the new source-bearing
implementation identity honestly: a packaged Python change invalidates earlier
formal qualification and changes the model fingerprint. Freeze source/tests/
protocol before acquisition. Do not relabel old recordings or imply that hashes,
the optional sidecar or agreement of subset sums constitute native replay
attestation. The browser validates declarations/binding/structure; only the local
source audit checks coordinates and graph edges against their original arrays.

## Exact display clock

The activity signal is **cell spike count per completed 100 ms**, not a spike
raster of exact firing times. For window `k`, sum all original bins entirely in
`[1000*k, 1000*(k+1))`. Validate that each window boundary is an actual native-bin
boundary and duration is a multiple of 1,000 ticks. The current session recipe's
three video frames per 100 ms and 10 ms card bins provide these boundaries;
reject incompatibility rather than split/prorate a bin or fabricate timing.

At playback tick `t`, show window `floor(t/1000)-1`, clamped only at the terminal
duration. Before tick 1,000 show "Awaiting first complete 100 ms window", not a
measured zero. Each window first becomes visible at its end and persists to the
next end. At 30 fps this preserves every window for three frames; the final one
continues through the existing terminal hold. Show the actual window start/end.
Seeking derives state solely from the requested tick. No interpolation, decay,
intra-bin flashes or smoothing. A count heatmap/history can append each completed
window once; it must not be called an exact spike-time raster.

The original seven population traces retain their current complete native-bin
values and durations. Label their different measurement window clearly. Neither
cell display nor topology can affect the adapter, input, decision or plan.

## Visual and loading contract

Make the scientific layer prominent and readable in the shared 900px export
canvas: a larger count-driven cohort view over the subdued static soma context,
restrained static directed edges, and the retained group traces. Use one shared
source-coordinate projection/scale for background and cohort; do not independently
normalize them. No anatomy-shaped layout, animated synapses or invented axes.
Where points overlap, an explicitly schematic count-grid inset/history is allowed;
cells without soma positions belong only in that labelled inset/table.

Node hue identifies group, not neurotransmitter concentration. A fixed discrete
brightness legend uses counts 0, 1, 2–4 and 5+ per 100 ms; exact counts remain
available in the count view/inspection. Zero is neutral, with no fallback glow.
Show cohort/group coverage, positioned/missing counts and displayed/eligible
connections. Labels must say **recorded cell counts**, **completed 100 ms window**
and **static model connections — not measured transmission**. This is simulated
model activity, not an in-vivo measurement or biological motor validation.

Add optional local cell-sidecar loading through existing viewer conventions.
New recording clears it; stale loads cannot attach; export freezes the loaded
sidecars and blocks replacements. Wrong/missing detail leaves ordinary replay
usable with "Cell activity not loaded". Verify exact recording/engine/graph/source
bindings and count/group/bin consistency. A count sidecar can supply its own
cohort coordinates without requiring a separate anatomy upload; if background
anatomy is present both must share binding and projection. Keep the current
illustrative fly/tap, immutable plan and no-early-result behavior.

## One acquisition and finite budget

After implementation tests and independent review, run one fresh, reward-free
continuous fast-feed/event session with the existing adaptive feed stop policy:
at most 8 s feed plus 2 s cards, at most 244 observations and 1,160 native bins.
All observations are at most 500 ms; explicit black RGB still advances time.
No external DAN, learning=false, normal passive decay. Choose proposal/playlist
before acquisition. A genuine provider-produced proposal may be used if its
separately authorized configuration/transport is ready; otherwise use the declared
imported proposal. Do not delay the protocol, fabricate API provenance or perform
a second native run merely to change proposal origin.

Limits: 900 s wall time, 4 GiB native-process peak RSS, 256 MiB total task-generated
output including checkpoints/exports, with at most 16 MiB combined raw/exported
cell detail. Enforce cell/bin/byte caps in-process before adding a record; supervise
the actual native Python descendant rather than just the Windows venv launcher.
Wall/RSS/total-output thresholds are externally polled at at most 2 s, with
bounded detection latency, not OS hard quotas. On any breach, exception or
incomplete evidence, stop the owned workload, retain partial evidence, report the
failure and do not automatically retry, shrink/reselect the cohort or change seed.
A zero/inconclusive response or defer is a successful honest presentation outcome.

## Sequential slices and acceptance

1. Backend: passive observer, fixed cohort/topology extraction, bounded raw writer,
   sidecar validator/export and tests; independent integrity review before run.
2. Viewer: optional loader, exact completed-window mapping, shared projection,
   count view/static connections, export and malformed/stale/zero/missing tests.
3. Freeze; perform the single supervised acquisition; audit raw detail versus
   recording/source, counts, clocks, hashes and resource receipts independently.
4. Export the new recording once valid; inspect real frames at window/phase/
   decision boundaries and terminal hold, whole playback, readable legends and
   fixed anatomy/edges. Test both selection sides/defer with labelled synthetic
   fixtures, not additional native sessions. Review actual evidence and update
   the handover; commit only first-party code/tests/docs, never raw detail/media.

Do not claim complete research support, semantic understanding, exact spike-time
reconstruction, measured synaptic transmission or genuine LLM acceptance without
their separately required evidence.
