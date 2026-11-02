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

## Current video-source checkpoint

Phase 1 `4467431` is reviewed/pushed. Current genuine-video source has 33 packaged
Python/C++ members, model identity
`e8d0e046e890418541ee9f0bb84065966228e756834f5bd7fb084f9ff5005ba8`;
schema is unchanged at
`3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
The [video-feed contract](../specs/2026-11-02-video-observation-feed.md) fixes
90x160 RGB/30Hz first 4s clip windows, causal rolling 300ms/100ms motor evaluation,
1s dwell, 4s clip cap and 8s session cap. This is an engineered reward-free policy.

Focused video tests: 81 passed in 42.49s. Three independent Astra decoder findings
are fixed; independent closure is C0/I0/M0. Pre-decoder-fix candidate `8f69b283` recorder/replay compatibility: 621 passed,
2 skipped in 84.09s (sandbox junction/fullgraph opt-in); normal-host junction
subset 2 passed/401 deselected in 0.14s. Only video_observation.py changed afterward; other 32 packaged sources/schema
stayed exact. Final 81 focus covers the fixes; no current whole-suite/fullgraph
compatibility rerun is claimed.
Viewer 57 tests/build exit0; independent Sol review C0/I0/M0 on 18-file freeze
`10ba7c3bacb748434ddebc17d60bf56b66ce2a7e698f1615b4eb654c92b8e5fc`.

The [single actual fullgraph video observation](../../experiments/2026-11-02-video-feed-observation.md)
completed exit0 in 35.843s (240s wall budget): 105 input frames/420 bins/3.5s.
Ordinary verify/export and independent source-PTS/RGB/count/clock/policy audit
passed with unchanged 33-member source. A recorded motor-right advance at 2.3s
selected the second clip's actual next input; playlist exhaustion stopped the
session at 3.5s with motor-right trigger. This is an engineered policy result,
not learning or validated preference.

Actual parser/Chrome file loading, play/pause, boundary seek, terminal labels
and export-position restoration passed. The actual UI export independently
decoded to 120 VP9 frames/900x900/4.0s, 33/34ms spacing: 3.5s measured plus 15
labelled hold frames. Sampled poses changed; the foreleg gesture followed the
recorded advance and clip1 content matched actual inputs, including near-black
early frames. See the report for artifact hashes and exact boundary values.

The bounded runtime/raw/browser/file acceptance is complete. Broader mobile,
accessibility/cross-browser/live-FPS and longer-feed work remain open; LLM/formal
assay/C1 stay parked. Reuse the SAME artifact for presentation work; no automatic
new native run. Raw clips, downloaded data, runs and media outputs stay ignored.

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
