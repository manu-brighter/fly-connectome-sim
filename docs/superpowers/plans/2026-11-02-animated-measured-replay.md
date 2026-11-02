# Animated measured replay and genuine video observation

The user's assessment supersedes the previous visual acceptance: the delivered
WebM is not a satisfactory animated replay. Independent byte inspection found
17 VP9 frames in 13.326 seconds, median frame spacing 1003 ms. That historical source had no
fly pose animation, phone-feed scrolling or real reel input. Keep its numerical
and artifact checks; do not call those a finished product or smooth video.

Continue autonomously using the existing simulator and viewer. Routine design
and implementation choices below are builder decisions. The user supplied genuine
reel URLs; the first two downloaded renditions are locally hashed. Do not substitute unrelated
video or claim the old A/B measurements came from a reel.

## Historical standard-video checkpoint; current continuation

This plan records the completed A/B animation correction and original 1×/v1
video slice. The actual 3.5s standard-video run, reviews and 120-frame/4.0s export
are historical/source-specific; see its [report](../../experiments/2026-11-02-video-feed-observation.md).
The user subsequently requested 5× content, 3–4s watch time and a quick swipe.
Continue under the [fast-feed plan](2026-11-02-fast-reel-feed.md) and
[contract](../specs/2026-11-02-fast-reel-feed.md). Current source review/tests, the actual 7s pilot/raw/parser audit and
same-artifact Chrome/encoded-file acceptance passed.
The [handover](../../cloud-handover.md) and
[fast-feed report](../../experiments/2026-11-02-fast-reel-feed-observation.md)
track current identities/results. Reuse the validated current artifact for
presentation work. Do not substitute old 1× measurements for fast-feed content.
Broader browser/mobile/accessibility checks remain open; C1/formal/LLM stay parked.

## 1. Correct export and visible motion first

- [x] Replace wall-clock MediaRecorder capture with sequential timestamped
  canvas-frame encoding, independent of requestAnimationFrame timing. Pin
  mediabunny 1.65.0; its CanvasSource accepts explicit timestamps/durations and
  awaits encoder backpressure. Use a supported WebM codec, with explicit errors
  when WebCodecs encoding is unavailable; no silent real-time fallback.
- [x] Fixed export size: 900x900 for this first correction. Freeze camera and
  dimensions during export; prevent the interactive animation loop from
  overwriting the export canvas while a frame is being encoded.
- [x] Export 30 frames/second using frame indices, not elapsed wall time.
  For the existing 12-second recording encode 360 samples over [0,12), then
  15 presentation-only frames holding the actual terminal sample at source
  tick120000. Total375 frames/12.5 seconds. Clearly identify the final hold;
  it advances no simulation time and fabricates no bin or activity.
- [x] Show progress/cancel; cancellation and any encoder/finalization error
  produce no successful video download. Restore controls and the user's
  playback position after export, and release encoding resources on all paths.
- [x] Animate the existing illustrative fly from absolute replay time: modest
  body/head movement, legs and wings. Pause/seek/backward seek must reproduce
  the same pose. Respect reduced motion. The UI and captured overlay identify
  this as illustration; it is not a measured motor trajectory or preference.
- [x] Preserve exact A/B/black pixels and existing integer population bins.
  Do not animate neural spike locations or invent stimulation/learning.
  Add no timed feed swipe presented as a neural choice.
- [x] Cache invariant trace data and avoid recreating trace raster dimensions
  every animation frame. Retain discrete measured rates and source clocks.
- [x] Use focused test-first coverage for frame scheduling/durations, pose
  replay/seek, unchanged samples, cancellation/errors and the export/interactive
  rendering handoff. Preserve existing parser/integrity tests.
- [x] Review the change and encode the SAME existing actual recording once.
  Independently inspect encoded frame count and PTS:375 frames, approximately
  33.333ms spacing within the container's timebase,12.5s total. Visually inspect
  several different poses and source boundaries; a declaration of30fps is not
  acceptance. No native simulation is required for this correction.

## 2. Feed a real reel through the actual engine

The current user steering permits reward-free video observation before the
formal learning assay. This changes the old product sequencing, not scientific
criteria. No claim of learning, semantics or reel-specific preference follows.

- [x] Obtain user-selected reel URLs and locally hash the first two downloaded renditions.
- [x] Define a separate bounded video-observation protocol. Hash original bytes;
  declare decoder/color conversion/orientation/crop/resize and selected source
  interval; store exact RGB input frames and source PTS versus simulation ticks.
  The contract is defined; final independent scientific/integrity source review
  closure passed before the single fullgraph recording.
- [x] Sample/quantize the declared clip without accumulated time drift. Advance
  all intervals, each at most500ms, external stimulation=None,learning=False,
  normal passive evolution. Audio is outside the neural input.
- [x] Reuse the existing engine, recorder, actual checkpoints and full-EOF
  integrity checks. Add a versioned compact format with frame IDs; do not weaken
  measured-replay/v1's A/B recipe restrictions to accept arbitrary claimed data.
- [x] Implement exact fed-frame phone rendering; any higher-resolution preview
  must be separately labelled and bound to the same source/timing. Actual
  browser pixel/timing acceptance passed on the actual Chrome recording.
- [x] After source tests/review, run one bounded real observation and reuse it
  for presentation work. Display measured readouts even if the response is zero.

## 3. Make scrolling a real recorded action

- [x] Reuse the existing lateral motor readout. Explicitly define a new
  watch/scroll state rule before running it; inspect_right is not implicitly a
  scroll command. Do not tune thresholds to make an existing recording move.
- [x] Make decisions during production and simulate the resulting selected
  following input. Record decision, motor evidence, policy version and reason.
  Distinguish clip end/timeout from a motor-triggered advance.
- [x] Animate a swipe only for the matching recorded action. Idle illustration
  can remain independent; do not retroactively rearrange inputs or pair reel
  footage with old A/B measurements.

LLM integration and formal assay qualification remain separate. No additional
A/B fullgraph runs for visual work, no parked C1 return, and no second simulator.

## References used for the export choice

- https://mediabunny.dev/api/CanvasSource
- https://mediabunny.dev/guide/writing-media-files
- https://mediabunny.dev/guide/supported-formats-and-codecs

Context7 lookup succeeded but its detailed query returned a server error; the
official pages above and npm registry version/integrity were checked directly.

## Historical Phase 1 observed checkpoint

The replaced recording has17 encoded VP9 frames over13.326s (median spacing1003ms).
The corrected file has375 independently counted and decoded VP9 frames,900x900,
12.5s,33/34ms spacing and no gaps above34ms. SHA256:
`2d670f3cd06c3f0fe2db023ea930fdbc80a7177663d879a95eb6578e1a739ee3`.
Decoded samples at0 and0.267s show changed illustrative wing/body pose within
the same A stimulus; the last15 frames are explicitly labelled presentation hold.
Historical Phase 1 root checks:44 viewer tests passed in234.9783ms; build exit0;
unchanged16-file viewer freeze and all31 then-packaged sources. The source review closed the
pending-load/export mutual-exclusion finding. These checks do not make the A/B
recording a reel observation. Phase2/3 implementation follows the separate
[video-feed contract](../specs/2026-11-02-video-observation-feed.md).
