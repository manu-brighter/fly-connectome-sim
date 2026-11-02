# Measured Replay v1

**Decision, 2026-11-02:** deliver an experimental replay of actual MaleCNS
measurements before the complete formal assay. LLM work follows later. This
changes product order, not scientific criteria. The existing simulator,
provenance locks and artifact reader remain. Parked selected-inventory work is
outside this milestone.

**Reviewed WIP checkpoint:** recorder/exporter and viewer source are implemented;
one six-cycle/12s actual fullgraph observation was sealed/verified/exported in
208.125s (240s budget), with independent raw audit and actual frontend-parser
checks. Source model `f70722c4c253d48b6496e772a2780e3f6aba3474aca13a7a799bcd5941463b46`
has 31 members; schema is unchanged. Backend 44 tests, recorder/replay 622 passed
with one opt-in skip. These are historical separate scoped results,
not complete scientific acceptance. Chrome real-file/play/pause/speed/seek/Home,
source disclosure, sampled telemetry and desktop/mobile checks passed. The old
video's final overlay was inspected, but 17 frames/13.326s failed the actual
animation/smoothness requirement. Phase 1 now has reviewed timestamped export
and illustrative motion, 44 viewer tests/build0/audit0 and an independently
decoded 375-frame/12.5s actual export. Real reel input/motor-driven scrolling are
not implemented. Continue under the
[animated replay plan](2026-11-02-animated-measured-replay.md) using the SAME A/B
recording for visual work. See the
[observation report](../../experiments/2026-11-02-measured-replay-observation.md).

## Smallest useful vertical slice

Record a short genuine observation, seal its ordinary pilot artifact, export
compact measurements and exact stimulus pixels, then replay them in a local 3D
viewer. An illustrative fly and phone accompany measured population activity.
The renderer never runs a simulator or invents an activity fallback. Zero
responses remain zero. An observation recording is not a training assay.

Initial recording uses existing `AssayStimuli`, seed11, qualification stimulus
family, 32×32, centered/fixed colors. The pilot's own experiment family is
`measured-observation`; the stimulus family does not confer qualification.
One cycle is A/black/B/black, 500ms each, repeated1–10 times (default3). All
calls use explicit RGB uint8, stimulation=None, learning=False, normal passive
evolution and both detail flags false. A fresh actual `FlyEngine` records real
before/after checkpoints. No restored branches or extra stimulus protocols in
this first supported format. Existing training/assay work remains separate.

## One compact exchange format

Use `version="measured-replay/v1"`, `tick_ms=0.1`. Exact top-level fields:

```text
version, tick_ms, source, groups, inputs, segments, duration_ticks
```

- `source`: actual `run_kind`, `verification_mode`, `schema_sha256`,
  `run_metadata_sha256`, `events_sha256`, `final_scientific_sha256`, `metadata`.
  Preserve the original metadata/engine identity. Mode is integrity-only, never
  promoted to native-history verification or scientific support.
  The browser displays that stored mode; it cannot reverify the source artifact
  from the compact file alone.
- `groups`: positive integer populations for exactly kc, pam11, ppl101, mbon07,
  mbon11, motor_left and motor_right, derived from actual neural-group maps.
- `inputs`: A/B/black mapped to exactly `{sha256,width,height,rgb_base64}`.
  Pixels are lossless RGB8, not guessed thumbnails. Regenerate only this fully
  declared existing generator and black zeros; verify every recorded input hash.
- `segments`: actual observations in original event order. Each has exactly
  `{event_sequence,branch_id,stimulus,stimulation,learning,source_start_tick,
  source_end_tick,playback_start_tick,playback_end_tick,bins}`. Stimulus is
  A/B/black, stimulation null and learning false for this supported protocol.
  Retain original source clocks; playback placement is the cumulative recorded
  interval duration, never a global sort by simulation time.
- Each bin is exactly `{end_tick,duration_ticks,group_spikes}` using original
  source ticks and exactly the seven nonnegative integer counts. Validate
  complete, contiguous coverage, count bounds and agreement with recorded
  telemetry/populations. Rates are counts divided by actual population and
  duration. Booleans are not integer counts; nonfinite values reject.

Support only the new producer's sealed `pilot` protocol and single continuous
root branch initially. Reject restores, unknown operations, inconsistent
clocks/pixels/flags and missing telemetry instead of silently flattening them.
Do not manufacture context to reopen the earlier unsealed diagnostics. Use
`verify_run` and consume its iterator to normal EOF before publishing an export;
write output atomically without replacing existing files. No partial successful
export after corruption or an iterator failure. Bound40 segments/2000 bins;
the viewer also bounds input file size. Do not introduce a second trust issuer.

## Implementation and ownership

- [x] **Record/export source:** add `experiment/measured_replay.py`, focused tests and
  narrow `observe` / `export-replay` CLI commands. Reuse engine/stimuli/recorder;
  no qualification `_Run`, core/schema changes or second simulator. Existing
  executor drops full telemetry, so a small recorder loop is intentional.
  A genuine pilot seal needs emitted/ingested before and after checkpoints, not
  a scientific result terminal. CLI defaults write under ignored `runs/`.
- [x] **Viewer source:** separate `viewer/` with vanilla TypeScript, Three.js and a small
  Vite build. Pin dependencies/lockfile. Local file input, play/pause, seek,
  speed, recorded stimulus, learning/stimulation flags and population telemetry.
  No uploads, remote model calls, fabricated demo data or imported anatomy.
- [x] **Real recording/export/parser check:** after backend review, record one bounded actual
  fullgraph observation (fixed six cycles/12s; 240s wall budget), verify/export
  it and check its raw bytes/counts/pixels and actual frontend parser.
- [x] **Real browser check:** load that SAME export, then verify play/pause/seek,
  sampled displayed values and desktop/mobile behavior. Code/UI iterations reuse the resulting data;
  no repeated fullgraph runs for styling. No formal capacity claim follows.
- [x] **Historical measurement/end-pixel check only:** source numbers, sampled
  displayed values and terminal pixels checked; this did not establish smooth
  animation. The old 17-frame clip failed the user's quality requirement.
- [x] **Phase 1 export/motion:** timestamped 900x900/30fps encoding; 360 measured
  samples plus 15 labelled hold frames for 12s input. Actual375-frame encoded
  output has 33/34ms PTS spacing and 12.5s duration; decoded fly poses differ.
- [ ] **Next product slice:** genuine-video neural input and recorded motor-driven
  scrolling after separate contract review; broader accessibility/cross-browser QA.

The user manually enabled Chrome local-file access; no automated settings write
occurred. Real-file numerical/layout/end-pixel checks remain historical evidence.
The old 17-frame export was not smooth animation. The replacement's explicit
frame schedule was checked against actual encoded bytes/PTS and decoded images,
not just an fps declaration. A presentation hold advances no simulation time;
fly motion is illustrative, with no invented neural decisions or feed swipe.
One real reel rendition has been downloaded for the next slice, but no video
observation or motor-scroll behavior has run. This remains experimental WIP.
Commit code/lockfiles/docs only; never recordings/checkpoints/exported pixels/videos.

Backend and viewer workers own disjoint paths and share this format. Keep
integrity/timing review focused on real risks. Do not repeat the complete assay
suite for UI changes. Meaningful checks include a real tiny-native sealed
roundtrip, exact input hashes/black frames/flags, count-to-rate conservation,
unsupported clock rewinds, tail corruption and no output before EOF. Viewer
checks cover zero versus missing, half-open boundaries, seeking and no fake
fallback. Record actual command results and unavailable browser capabilities.

## Visual direction

One quiet experiment stage: illustrative 3D fruit fly beside a phone showing
the exact input; a narrow telemetry rail and a real playback timeline. Use cool
porcelain `#E7EFF4`, blue-grey `#C9D9E5`, ink `#172B3A`, slate `#597083`, cobalt
`#2456D6` and restrained amber `#D39A3F` for actual stimulation indications.
Use local Bahnschrift/Aptos/system sans, sentence-case controls, strong numeric
legibility and no remote fonts. Left-align labels; give the stage most of the
space. The fly silhouette is the distinctive visual element, with restrained
shadows/translucent wings rather than dashboard decoration.

```text
Brand / recording title                         Open recording / source
┌─────────────────────────────────────────┬───────────────────────────┐
│                                         │ Recorded stimulus / flags │
│        Illustrative fly + real-input     │ MBON11 / KC                │
│                 phone                   │ Motor left / right         │
│                                         │ Population traces          │
├─────────────────────────────────────────┴───────────────────────────┤
│ Play / pause      recorded timeline / seek      speed / video export │
└─────────────────────────────────────────────────────────────────────┘
```

On mobile the telemetry follows the stage. Keep one continuous rail and timeline;
the data should not become a grid of unrelated cards. The chosen cool palette
and local sans keep attention on the subject and exact inputs.

Keep source counts and flags discrete. Group-rate smoothing, if used, must be
explicitly defined from complete recorded bins. Camera/illustrative pose motion
does not claim tracked movement or individual spike locations. Reduced motion,
keyboard focus, responsive layout and an actionable empty/file-error state are
part of the basic implementation. Video capture must not fabricate skipped
measurements or claim exact biological motion.

## Claim boundary

Label the result as experimental recorded simulation. No consciousness,
semantics, dopamine concentration, receptor activity, biological learning or
validated motor behavior. The reviewed diagnostics remain source-specific:
candidate state changed, but the sampled T10 A response matched measured
controls. Scientific qualification/freeze/confirmation criteria stay unchanged
in the separate [assay plan](2026-09-24-associative-plasticity-assay.md).
