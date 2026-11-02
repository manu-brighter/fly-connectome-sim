# Genuine video observation and recorded feed actions

The user supplied five Jogge-di-Balla reel URLs and asked for an animated fly
that actually observes and scrolls that material. Build on the existing engine,
recorder and timestamped replay. This is reward-free model observation and an
engineered motor policy, not a learned preference or validated fly behavior.
Reel observation may precede the formal learning assay; its criteria stay intact.

## First bounded outcome

Use the first two supplied reels, in that order, each with a prepared first4s
window. End the session after at most8s simulated time or playlist exhaustion.
The first downloaded rendition is `.tools/reels-source/DcTiO6Ls3HT.mp4`,
SHA256 `8cfa586a94b5e40ad00b197a57da348080bf4aa4490618ce9f5cf6778c0103fa`.
It is an Instagram rendition, not an authenticated original upload master.
The next supplied source is `https://www.instagram.com/reel/DZHp4mtNvJb/`.
All raw media, source receipts, checkpoints, runs and video outputs remain ignored.

## Preparation and source binding

- Add optional pinned `media` dependency PyAV19.0.2. It was independently probed
  on the first actual VP9 rendition. Record PyAV and FFmpeg library versions.
  Existing core dependencies/locks and native equations must stay unchanged.
- Accept a local playlist JSON containing1–5 ordered entries `{path,source_url}`;
  no browser-cookie handling or network acquisition in the simulator command.
  The first acceptance uses exactly2 entries. Source URLs are provenance labels;
  decoder inputs are the actual locally hashed files.
- Before engine construction, validate/read the entire declared first4s window
  of every source. Hash full file bytes before/after decoding and reject change.
  Reject unsupported orientation/display transforms, invalid/nonmonotonic PTS,
  missing video, inadequate coverage or limits before creating a pilot artifact.
  Do not silently omit an unavailable source.
- Preprocessing: RGB24 uint8,90x160, explicitly declared bilinear resize and
  centered black letterbox, no audio input or crop. Preserve source PTS as integer plus rational
  timebase. Sample at rational j/30 seconds using the last decoded frame whose
  normalized PTS is <= that instant. Declare the time origin. Never infer
  semantic tags/reward from filename, source URL or captions. Reject non-square
  source pixels and unsupported orientation/display matrices. Resize dimensions
  use min(90/source_width,160/source_height), integer half-up rounding and
  floor-centered placement; record inner dimensions and padding exactly.
- Quantize cumulative simulation boundaries to the nearest0.1ms tick using
  declared integer half-up rounding; derive durations by subtracting adjacent
  boundaries. For30fps this distributes333/334ticks without drift. A clip has
  120 input intervals and exactly40000ticks. Every interval is advanced.
- Predeclare the exact RGB hashes for all prepared frames in metadata; store
  source file hashes, transform recipe, sampling/time-origin and decoder versions.
  The ordinary verifier does not independently attest decoder/source extraction.
  Include the complete unique frame_id-to-clip/index/hash/sourcePTS/timebase map,
  numeric origin PTS and coverage endpoints. Decoder PTS strictly increase;
  selected PTS may repeat when29.97Hz is sampled at30Hz. Demonstrate coverage
  through4.000s using a decoded following PTS or valid final-frame duration,
  rather than stopping after the sample at3.966...s. Event frame bindings must
  equal this prepared metadata map, not merely another self-consistent hash.
- Keep preparation memory bounded by incremental last-PTS selection: retain the
  120 selected frames plus the current source frame, rather than all decoded
  frames. Reject more than4096 decoded frames per clip. Freeze initial geometry
  and pixel aspect ratio and reject changes before engine/output construction.
  Benign H.264 SEI side data is supported; display matrices remain rejected.

## Production and predeclared policy

Construct one fresh actual0.1ms FlyEngine. Ingest genuine native before/after NPZ
checkpoints, use a single continuous root branch and seal an ordinary `pilot`.
Each observe call receives the exact RGB frame and its quantized duration,
stimulation=None,learning=False,both detail flagsFalse,normal passive evolution.
No resets, restored branches, skipped time or training pulse in this protocol.

Keep the existing `LateralMotorAdapter` and its1Hz threshold unchanged; do not
reactivate the old MBON07−MBON11 preference adapter. Evaluate once every100ms
(three input frames), using sums of actual counts/populations over the last300ms
(nine complete input frames). Before300ms, the readout is unavailable, not zero.

The new explicitly engineered `right-scroll/v1` policy is:

1. A clip's first1000ms is minimum dwell; no motor-triggered advance before it.
2. After minimum dwell, `inspect_right` advances to the next prepared clip;
   `inspect_left` and `defer` continue watching. This mapping is a product choice,
   not the biological meaning of that adapter output.
3. At the declared4s window end, advance with reason `clip_window_end`, regardless
   of the readout. This is an external presentation limit, not a neural choice.
4. Stop at8s or when an advance exhausts the playlist. Record the actual reason.
   Clear the rolling evidence when switching clips; next input starts at that
   clip's frame0 and continues neural time from the previous interval's end.

Decide during production, after observing the current input. The following
input must follow that decision. Preserve every evaluated readout, evidence
window/counts/populations, minimum-dwell condition, chosen action, reason and
next clip index. Never tune the mapping after inspecting actual results.
No forced motor action if neural output is zero or consistently points left.

Decisions take effect at the current observe.end_tick, never at its start or an
earlier bin. Priority at a simultaneous boundary is session limit, then4s clip
window limit, then eligible motor-right advance, otherwise watch. An advance
with no next clip ends with reason playlist_exhausted and a separate trigger
that preserves motor_right versus clip_window_end. Last policy evaluation must
end the session legitimately. A sealed arbitrary prefix is not a full session.
The final checkpoint follows that decision at exactly the actual terminal tick.

## Self-contained events and compact replay

Reuse existing generic RunRecorder/schema semantics, without loosening
`measured-replay/v1` or changing the run schema. Each observe event adds a bounded
`video_frame` payload with frame ID,clip ID,index,dimensions,RGB base64,existing
shape/dtype-prefixed input hash and source PTS/timebase. Bind it to the actual
telemetry input hash/shape/dtype. Attach any policy evaluation to that observe
event. Generic integrity chains cover these fields, but new protocol validation
must independently check their meaning.
Use a separate `video_policy` field for rolling-window counts/readout; do not
use or relax existing `motor_readout`, whose validator binds to rates from the
same individual observe event. Store rolling window start/end and count sums.

Add a separate `measured-video-replay/v1` exporter. Top-level fields remain
version,tick_ms,source,groups,inputs,segments,duration_ticks. Preserve actual
metadata and stored integrity-only mode. Input dictionary keys are frame IDs;
descriptors retain exact RGB pixels, hash, clip identity/index and rational PTS.
Segments retain original event order/source and playback clocks, frame ID,
clip ID,flags,raw bins and any recorded policy evaluation. No global clock sort.

The exporter must verify the ordinary sealed pilot, exhaust events to normal EOF
before atomic no-replace publication, and check exact metadata/flags/recipe,
frame-to-telemetry hash equality, pixel shape/length/hash, all seven populations,
strict integer counts/bounds, full contiguous bins/rate conservation and clocks.
Recompute the declared policy from actual counts and verify each subsequent
clip/frame occurrence against it. Reject fabricated decisions, unsupported
operations, forks, unknown policies and damaged tails. Source-file hashes are
retained provenance, not new native-history attestation.

Bounds:5 prepared clips,120frames/clip,90x160RGB; actual session<=8s/240observe
segments/960bins. Cap each encoded input and the compact JSON (32MiB). Export
only actually consumed input frames, while retaining prepared input declarations
in original metadata. Do not create generic immutable-media machinery or a new
scientific trust issuer.

## Presentation and acceptance

The phone shows the exact fed portrait frames, with correct aspect ratio and
source identity. The existing A/B reader remains strict and supported. Add a
separate version-dispatched video reader; preserve zero versus missing and
all existing source-mode claims. Show actual motor readout and watch/advance
reason. Animate a foreground leg swipe only for a recorded advance, with distinct
labels for motor versus clip-window limits; do not synthesize feed choices.
Illustrative idle remains separate from the motor readout. Replay and30fps
encoding use absolute recorded/playback time and the same recorded decisions.
For this video's30Hz presentation, map nominal frame times to the simulation
lattice using the SAME cumulative half-up quantizer as production. Flooring
2/30s to666ticks instead of667 would repeat frame1 and omit frame2 at that
boundary; test this explicitly. Retain the nominal encoded PTS separately.
The renderer may expose a policy evaluation/swipe only at or after its recorded
decision tick. A segment carrying an end-of-interval result does not make that
result available for an earlier frame within that segment.

Test preparation using a genuinely decoded tiny video fixture, quantization,
source mutation/truncation, original PTS and exact RGB hashes. Test policy
minimum dwell/right/left/defer/window-end/exhaustion, including zero activity,
and a genuine tiny-native sealed roundtrip. Mutation tests must fail closed for
pixels, clocks, decisions, next inputs, flags and EOF failures. No old qualification
claim is upgraded by these tests.

Finish all packaged source, tests and independent scientific/integrity review
before one bounded actual fullgraph feed run (max8s,240s subprocess wall budget).
Then reuse that artifact. Check sampled phone pixels,sourcePTS,source tick,
raw bin and motor decision together. Audit actual encoded frame count/PTS and
inspect visible motion. Report no motor-triggered advance honestly if none occurs.

LLM integration, training qualification and scientific confirmation remain later.
