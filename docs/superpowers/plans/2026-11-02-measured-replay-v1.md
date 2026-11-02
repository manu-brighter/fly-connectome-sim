# Measured Replay v1

**Decision, 2026-11-02:** deliver an experimental replay of actual MaleCNS
measurements before the complete formal assay. LLM work follows later. This
changes product order, not scientific criteria. The existing simulator,
provenance locks and artifact reader remain. Parked selected-inventory work is
outside this milestone.

**Historical status:** Phase 1 A/B checkpoint `4467431` and standard-video
checkpoint `639423f` are reviewed/pushed historical slices. Their
[12s A/B](../../experiments/2026-11-02-measured-replay-observation.md) and
[3.5s standard-video](../../experiments/2026-11-02-video-feed-observation.md)
measurements/exports do not represent the new 5× profile. The earlier 17-frame
A/B export failed smoothness acceptance; its corrected export has 375 frames.

**Current continuation:** use the [fast-feed plan](2026-11-02-fast-reel-feed.md)
for explicit 5× content, 3–4s watch time and a 200ms illustrative recorded-action
swipe at normal simulation speed. Source review/tests, the actual 7s pilot/raw/parser audit and
same-artifact Chrome/encoded-file acceptance passed. The [handover](../../cloud-handover.md)
and [fast-feed report](../../experiments/2026-11-02-fast-reel-feed-observation.md)
track current identities/evidence. Broader browser/mobile/accessibility, C1,
formal qualification/freeze/confirmation and LLM remain open/parked.

The remaining protocol/checklist below describes the historical A/B slice.

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
- [x] **Genuine-video continuation:** implemented and accepted in the linked
  continuation plan/report; broader accessibility/cross-browser QA remains open.

The user manually enabled Chrome local-file access; no automated settings write
occurred. Real-file numerical/layout/end-pixel checks remain historical evidence.
The old 17-frame export was not smooth animation. The replacement's explicit
frame schedule was checked against actual encoded bytes/PTS and decoded images,
not just an fps declaration. A presentation hold advances no simulation time;
fly motion is illustrative, with no invented neural decisions or feed swipe.
This historical A/B milestone preceded the genuine-video observation now
recorded in the continuation plan/report. The product remains experimental WIP.
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
