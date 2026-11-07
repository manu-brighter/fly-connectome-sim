# Scientific replay presentation repair — 2026-11-07

Status: implemented and reviewed; see the [result](../../experiments/2026-11-07-scientific-presentation.md).
The previous film remains historical. Reuse its exact recording and plan. No
native simulation, changed neural input, new scientific result or live API call.

## What this restores

The original product specification requires synchronized technical telemetry
(H5) and the visual energy of the supplied DJ/doomscroll references (S2). The
November 2 replay plan reduced this to population traces and explicitly excluded
imported anatomy; it did not schedule a later anatomical display. This repair
adds the missing visual layer without copying unsupported dopamine percentages,
individual spike rasters or animated synapses from those references.

Two separate statements must remain visible: **static source cell-body
positions** and **recorded population activity**. A point is not an observed
spike. Neither panel is a complete anatomical reconstruction or biological proof.

## Scene and decision presentation

The separate scene repair places fly and tablet with positive geometric
clearance, grounded support feet and a body/head direction toward the display.
Check body, head, wings, idle legs and the complete gesture path, not only object
centres. Do not expand the tablet through the fly during the phase transition.
Exact card pixels appear at the actual feed/card boundary; presentation cannot
delay or replace their neural input history.

After the recorded decision becomes effective, one illustrative foreleg tap
contacts the chosen physical card half from the front and retracts. No early
result or gesture, and no tap for defer. The selected option and counts remain
unchanged. Use the existing three-second terminal hold with a separate bounded
presentation clock: source time, rates and input freeze at the terminal sample.
Playback, seek/reset, reduced motion and export must share that contract. Label
the tap as an illustration of the recorded decision, not a measured trajectory.

## Minimal optional anatomy sidecar

Use a standalone first-party `scripts/export-anatomy.py` generator and focused
tests. Do not modify packaged Python/C++ core, recording schemas or recording
bytes. Existing NumPy/PyArrow dependencies suffice. No graph construction,
kernel load, source download or full connectivity-table scan is needed.

Command contract:

```text
python scripts/export-anatomy.py --runtime-directory PATH --recording PATH --output NEW-anatomy.json
```

The output is local/ignored, at most 8 MiB, UTF-8 JSON, written without overwriting
an existing file. All runtime paths are explicit. The generator:

1. Checks `annotations.feather` size and SHA256 against the existing packaged
   `neural/sources.lock.json` entry. Reads only `bodyId` and `somaLocation`.
   Rejects duplicate body IDs and malformed non-null positions; null means absent.
2. Loads only `ids` from `graph.npz`, checks its signed little-endian int64 dtype,
   unique positive IDs and raw-byte hash against `neural/arrays.lock.json`.
   Require that hash to equal the supplied recording's existing
   `source.metadata.engine_identity.model_provenance.graph_ids_sha256`.
   This verifies the used projection inputs, not the entire prepared graph.
3. Joins by actual `bodyId` in graph-ID order. Every model ID must have an
   annotation row; only a present, finite integer XYZ `somaLocation` contributes
   a point. Never substitute `tosomaLocation`, infer a position from a cell type,
   or invent coordinates for missing cells. Require exactly three safe integer
   coordinates; reject booleans. Preserve raw coordinates in the sidecar.
4. Computes positioned/missing counts before sampling. Selects at most 12,000
   points from the ordered positioned list: for N available and K=min(N,12000),
   take indices floor(i*N/K), i=0..K-1. N=0 produces an empty anatomy panel, not
   generated fallback points. Sampling never uses activity or selected outcome.
5. Hashes original recording bytes and rechecks used source bytes before output.
   The existing source graph hash binds anatomy even when a recording has an
   older packaged-model fingerprint; never replace that historical fingerprint.

Exact sidecar fields, without a new seal or provenance framework:

```text
version: "replay-soma-anatomy/v1"
source: {release: "MaleCNS v1.0", annotations_sha256, coordinate_field: "somaLocation"}
binding: {recording_sha256, graph_ids_sha256}
coverage: {model_cells, positioned_cells, missing_positions, displayed_cells}
sampling: {method: "ordered-position-stride/v1", limit: 12000}
points: [[model_index, source_id_decimal_string, x, y, z], ...]
```

Coverage must reconcile: positioned+missing=model_cells and
displayed=min(positioned,12000)=points.length. Model indices are unique,
strictly increasing and in range; source IDs are unique positive decimal strings.
Use existing tracked locks as expected values, not hashes supplied by the sidecar
itself. Do not duplicate all model IDs or a connectivity table into the payload.

Observed local source facts for acceptance, not fabricated test data: annotation
hash `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2`,
14,483,314 bytes; graph-ID hash
`6b6b40c3bddf84b1281ef0b18db06927c2bf61c5f4cb32a4219ec9b7839dc2e5`.
The locked 166,700 model IDs join to 139,662 real soma positions and 27,038 null
positions. The full annotation table has more rows; its counts must not replace
these model-subset counts. This was checked without native execution.

## Loading and trust boundary

Add one optional local **Open anatomy** control, available after a recording has
loaded. Retain the loaded recording's raw-file SHA256 for exact sidecar binding;
do not hash a reserialized JSON object. Validate the bounded closed sidecar
structure, finite values, coverage and indices, source lock and graph-ID hash,
the locked release's 166,700 model-cell count, and exact recording hash before
attaching it. Loading a different recording
clears anatomy; a stale asynchronous result must not attach to a newer recording.
Disable anatomy replacement during export/loading and freeze the attached
sidecar with the recording for an export. Invalid anatomy must leave the current
recording usable, with an actionable error and no invented replacement.

The generator verifies positions against original bytes. A browser with only the
sidecar can check declarations and recording/graph binding, but cannot independently
prove each coordinate came from that annotation file. Do not present this as
native attestation or a newly authenticated dataset. Retain the generated file
hash and independent source-join check in the local acceptance evidence.

Without a sidecar, show **Anatomy not loaded** with the local-file action in the
viewer and a truthful small placeholder in export. All seven recorded activity
rows still work. Do not silently download data, draw a decorative brain, or
disable ordinary old-format replay. A zero-position sidecar says no positions
are available for this bound model; zero activity remains a different condition.

## Scientific panel and visual direction

Reserve roughly the lower 30–35% of the shared export canvas for a continuous
scientific panel, also visible in interactive replay. At 900×900, aim for about
285–300px panel height: static anatomy at left (~30% width), seven population
time traces at right. Fit the scene/camera and plan above it; no panel, caption,
fly, tablet or plan overlaps. Share layout measurements rather than competing
hard-coded bottom overlays. At small widths stack/reflow without losing labels.

Keep the porcelain scene, ink `#172B3A`, slate `#597083`, cobalt `#2456D6` and
local Bahnschrift/Aptos typography. A restrained ink-background science panel
with pale blue static dots and clear light labels echoes the references while
remaining part of the existing design. Use at least 12px essential labels in
the 900px export and strong numeric contrast; avoid tiny disclaimer paragraphs.

**Anatomy:** render a fixed source-coordinate point cloud, centred and uniformly
scaled by its largest extent. A fixed oblique projection may reveal depth; no
independent per-axis stretching, anatomy-shaping or time-varying brightness,
pulses, point motion or connections. State **Static cell-body positions**,
**Source coordinates; not calibrated anatomy**, displayed/positioned counts and
missing count. No micrometres, anatomical direction labels or claimed synapse
locations until their source meaning is separately established. It is a sampled
soma cloud, not brain surface, neurites, all neurons or the full CNS morphology.

**Activity:** use existing seven named populations: KC, PAM11, PPL101, MBON07,
MBON11, DNa02 left/right. Show actual current per-cell Hz and stepped time traces
derived solely from recorded integer group_spikes, group sizes and bin durations.
Use actual playback placement of source bins; no equal-width assumption for
short frame-tail bins. Clip trace history at the current playback position and
retain the existing complete-bin sampling semantics. Do not redistribute group
counts into synthetic single-cell spikes or call this a spike raster.

Cache trace geometry and fixed per-row scales when loading: max(1, maximum
recorded per-cell Hz for that row), with each row's upper limit printed and a
visible **Hz/cell · individual row scales** label. Keep zeros flat; no rate
smoothing, minimum glow, activity fallback or adaptive axis rescaling. Use
consistent row colours in labels/traces, independent of anatomy dots. During the
terminal presentation/tap, trace cursor and all numerical values remain frozen.
External stimulation/learning flags stay explicit; endogenous DAN firing is
never labelled dopamine percentage, concentration, reward or pleasure.

The panel must be painted through the same shared canvas path used by the film;
adding only DOM sidebar graphics would not satisfy this scope. Anatomy styling
and gesture animation cannot influence input pixels, adapter or event plan.

## Bounded acceptance

- Test first: generator ID join/sampling/missing coverage, locked-input drift,
  no overwrite; loader wrong recording/graph/source, malformed values/indices,
  oversize and stale-load handling. Small synthetic fixtures suffice for tests.
- Test native-bin arithmetic/time placement, all-zero rows, frozen terminal
  readouts, no single-cell fabrication and graceful absence of anatomy. Keep
  existing strict recording readers and integrity tests unchanged.
- Test both selected sides and defer for gesture timing, bounded geometry/path
  clearance, pause/reverse/reload and reduced motion; exported hold progresses
  the presentation clock while source time remains unchanged.
- Generate the one bound real sidecar without simulation; independently check
  its selected IDs/XYZ against locked annotation bytes and graph-ID order,
  reconcile coverage and repeat generation for deterministic bytes.
- Re-export the same existing recording. Inspect actual film frames before/at
  transition, both gesture sides via synthetic presentation fixtures, actual
  selected tap contact/retraction, late hold, scientific labels and counts.
  Decode frame/PTS timing, play the whole new film and recheck unchanged plan.
- Run focused viewer/generator checks and build, review the source/result, then
  update the reopened presentation status. Do not reuse the old film's visual
  acceptance or broaden this into new neural recordings/research gates.

Commit only generator/tests/viewer/docs. Anatomy, references, recording, raw data,
decoded frames, films and local audits remain ignored.
