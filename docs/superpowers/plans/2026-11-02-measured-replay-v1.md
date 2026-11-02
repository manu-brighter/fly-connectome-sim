# Measured Replay v1

**Decision, 2026-11-02:** deliver an experimental replay of actual MaleCNS
measurements before the complete formal assay. LLM work follows later. This
changes product order, not scientific criteria. The existing simulator,
provenance locks and artifact reader remain. Parked selected-inventory work is
outside this milestone.

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

- [ ] **Record/export:** add `experiment/measured_replay.py`, focused tests and
  narrow `observe` / `export-replay` CLI commands. Reuse engine/stimuli/recorder;
  no qualification `_Run`, core/schema changes or second simulator. Existing
  executor drops full telemetry, so a small recorder loop is intentional.
  A genuine pilot seal needs emitted/ingested before and after checkpoints, not
  a scientific result terminal. CLI defaults write under ignored `runs/`.
- [ ] **Viewer:** separate `viewer/` with vanilla TypeScript, Three.js and a small
  Vite build. Pin dependencies/lockfile. Local file input, play/pause, seek,
  speed, recorded stimulus, learning/stimulation flags and population telemetry.
  No uploads, remote model calls, fabricated demo data or imported anatomy.
- [ ] **Real vertical check:** after backend review, record one bounded actual
  fullgraph observation (fixed six cycles/12s; 240s wall budget), verify/export
  it, then load it in the browser. Code/UI iterations reuse the resulting data;
  no repeated fullgraph runs for styling. No formal capacity claim follows.
- [ ] **Finish:** verify exported numbers against displayed sampled frames,
  inspect desktop/mobile screenshots, build and run focused tests. Provide
  browser-supported video export of the same measured replay, including a
  readable telemetry overlay; feature-detect unsupported capture. Review the
  final vertical slice and update README/handover. Commit code/lockfiles/docs,
  never recordings, checkpoints, exported pixels or generated videos.

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
