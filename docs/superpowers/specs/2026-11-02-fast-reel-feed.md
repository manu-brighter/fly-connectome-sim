# Fast reel content with recorded feed actions

The user requests 500% reel-content speed, roughly3–4s watching each reel,
then a simple quick swipe into the next reel. Use the existing engine and
viewer. Builder choices: first acceptance reuses the same two local renditions;
3s minimum dwell,4s clip cap,8s session cap,200ms illustrative swipe. No new
dependency, simulator, learning/semantic claim or formal assay work.

## Closed profile and backward compatibility

Add explicit `observe-video --profile fast-feed`; omitted/default `standard`
preserves the complete existing1x/v1 behavior. Export infers the profile only
from stored metadata. Keep one implementation with two closed profiles, not
arbitrary speed/dwell overrides or a second protocol pipeline.

| Profile | Protocol / stimulus / policy / compact versions | Media sampling | Minimum dwell |
| --- | --- | --- | --- |
| standard | `video-observation/v1`, `decoded-video-rgb/v1`, `right-scroll/v1`, `measured-video-replay/v1` | j/30 seconds,4s coverage | 10000 ticks |
| fast-feed | corresponding `/v2` versions | 5*j/30 seconds,20s coverage | 30000 ticks |

The v1 recipe stays exact and gains no fields. The v2 recipe uses the same
closed fields except `policy_version="right-scroll/v2"` and
`minimum_dwell_ticks=30000`, plus exactly `source_speed:[5,1]` and
`source_window_seconds:20`. No top-level or other descriptor fields change.
Reject mixed version/profile/recipe declarations. Old A/B and genuine-video
v1 files must remain readable and strictly validated.

## Distinct media and simulation clocks

Prepare120 RGB uint8 frames per clip at90x160 using last decoded normalized
PTS <= 5*j/30 for fast-feed. Prove full20.000s coverage, not just the final
sample at19.833...s; hash source before/after. Retain exact selected source
PTS/timebase and RGB/frame hashes. Incremental selection, immutable geometry/
SAR, orientation rejection, benign H.264 support and4096 decoded-work cap
remain. Reject short/malformed sources before engine/output construction.
Both existing actual sources exceed20s; do not pad, loop or invent tail frames.

All120 selected frames still advance exactly4s of simulation with cumulative
half-up0.1ms boundaries and333/334-tick observations. This deliberately samples
a sped-up source; it does not process every original frame. No global5x replay,
synthetic neural interpolation, simulation-clock speedup or retroactive pairing
with old1x measurements. External stimulation=None,learning=False, normal
passive evolution, both detail flagsFalse and genuine checkpoints remain.

The v2 policy keeps the unchanged1Hz lateral motor adapter, nine-frame300ms
counts and100ms evaluations. No motor advance before3s; first eligible right
decision is at30000ticks. At4s the external clip-window limit advances. Session
limit remains80000ticks with existing priority session>window>right>watch.
Preserve cause/trigger and next-input causality. A last-clip advance produces
STOP/playlist exhaustion; never invent another clip or swipe for STOP. Nothing
is tuned after inspecting results.

Exporter and reader recompute the correct profile's policy and validate its
media PTS bounds/coverage/recipe alongside existing pixels, clocks, populations,
counts, bins, terminal/checkpoints and normal EOF. Existing32MiB/240-segment/
960-bin limits and no-replace publication remain unchanged.

## Presentation

Show `Reel 5×` for v2; simulation/replay time stays normal. Label native
source_start_tick/sourceTick as simulation time and media PTS separately.
Keep30fps timestamped export, half-up frame quantizer and0.5s terminal hold.

For200ms after an actual recorded ADVANCE, move the last actually consumed
outgoing frame upward and reveal the current actually consumed incoming frame
from below. Clip both to the phone screen. Incoming advances with its real
recorded frames throughout the transition; it must not freeze frame0 or show
unobserved future media. The current input label/telemetry/PTS refers to incoming.
The composited screen/leg motion is explicitly labelled illustrative during
the swipe; the composite is not an additional neural input. Static phone
textures outside transitions are exact fed RGB. Do not insert any observation,
presentation pause, extra simulation ticks or reordered inputs for the swipe.

Animate the foreground leg quickly using the same absolute-time transition.
At effective_tick the transition begins, at effective_tick+2000 it is complete;
before the boundary it is absent. STOP never swipes. Seek/backward seek must
reproduce the pose/composite. Reduced motion disables slide/gesture and shows
the actual incoming frame immediately. Bound/reuse/dispose transient canvas/
texture resources; export and interactive rendering share the same function.

## Acceptance

Test-first: preserve v1 tests/real export acceptance; genuine tiny20s decode
proves5x selected PTS/RGB and short-source rejection before factory; v2 native
sealed roundtrip and profile/PTS/policy mutations; 2.9/3.0s dwell and4s/8s
priorities; strict frontend dual version validation;200ms boundary/seek/STOP/
reduced-motion/current-incoming and clipped-composite tests. Run focused old
and new backend/CLI tests, viewer tests/build and appropriate compatibility.

Freeze packaged source and obtain independent Astra clock/policy/integrity
review, plus bounded independent viewer review, before one new actual pilot
with the same two sources, max8s simulation and240s subprocess wall budget.
Independently re-decode/check selected actual source frames, counts, policy
and clocks. Browser/encoded-file QA must show visibly sped-up content,
3–4s per consumed clip, a readable quick swipe and original matched telemetry.
Audit actual encoded frame count/PTS and final hold. No forced neural action
or scientific support claim if the external time limit causes the advance.
Then update handover/TODOs, reviewed feature commit/push; raw media/runs/tools
stay ignored. Broader accessibility/cross-browser/LLM/formal science remain open.
