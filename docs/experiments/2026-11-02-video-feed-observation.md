# Genuine reel observation and recorded motor-policy replay

One bounded Windows MaleCNS pilot fed actual pixels from the first two
user-selected Jogge-di-Balla reels into the existing engine. It completed in
**35.843s**, within its240s subprocess budget, and stopped after **3.5s simulated
time**. A recorded motor-right decision advanced to the second clip at2.3s.
The resulting900x900 video independently decoded to **120 VP9 frames/4.0s**:
105 measured input intervals plus15 explicitly labelled terminal-hold frames.

This demonstrates the implemented observation/engineered feed policy and replay
path. It does not establish learning, semantic understanding, a reel preference,
validated motor behavior or visual specificity versus autonomous model dynamics.
No black/shuffled control or training comparison was performed in this pilot.
The formal MBON11/PPL101 assay and LLM integration remain separate and unfinished.

## Inputs and declared protocol

The downloaded Instagram renditions are local decoder inputs, not authenticated
original upload masters. They were obtained without browser cookies; neither
the simulation command nor the viewer downloads media. Raw sources remain ignored.

| Ordered source | Bytes | SHA256 |
| --- | ---: | --- |
| [DcTiO6Ls3HT](https://www.instagram.com/reel/DcTiO6Ls3HT/) | 12,771,185 | `8cfa586a94b5e40ad00b197a57da348080bf4aa4490618ce9f5cf6778c0103fa` |
| [DZHp4mtNvJb](https://www.instagram.com/reel/DZHp4mtNvJb/) | 5,210,025 | `b30f710936b4799eaf1c158f6cc83067f5d1c25ee8596ea9b663752d0f1d2401` |

Both sources are1080x1920 VP9. Before engine construction, preparation checked
each complete first4s window and predeclared120 RGB uint8 frames at90x160.
Sampling takes the greatest decoded PTS at or before rational j/30; selected
PTS may repeat. Clip0 uses timebase1/11988, origin0, coverage endpoint48000 and
119 distinct selected PTS; clip1 uses1/15360, origin0, endpoint61440 and120
distinct PTS. Source files were fully hashed before/after preparation. Exact
RGB hashes, PTS, transform and decoder versions accompany the artifact.

PyAV19.0.2 converted RGB24 with FFmpeg defaults, bilinear resize, centered black
letterbox and no crop. Audio is not neural input. The second rendition starts
with nearly black frames; these were actually fed and displayed, not invented
gaps. Rotation/display matrices and changing geometry/SAR are rejected. The
preparation retains selected/current frames incrementally and rejects more
than4096 decoded frames per source.

The [predeclared contract](../superpowers/specs/2026-11-02-video-observation-feed.md)
fixes30Hz sampling, cumulative half-up0.1ms ticks, a4s clip window and8s session
limit. All consumed intervals advanced one continuous fresh engine without
reset/restore, external stimulation or learning. Both detail flags were false;
normal passive evolution remained enabled. There was no random input seed.

`right-scroll/v1` evaluates the existing1Hz lateral motor adapter every100ms,
using nine complete frames/300ms of actual counts. It requires1s dwell, clears
the window on clip change and decides after the current observation. Subsequent
input follows that decision. External clip-window/session limits have their
own reasons; neither limit caused this run's advance or stop.

## Actual measurements and actions

The sealed pilot has107 events: before checkpoint,105 observations, after
checkpoint. It contains420 bins over ticks0..35000;69 input frames came from
clip0 and36 from clip1. Populations are KC4064, PAM11=15, PPL101=2, MBON07=4,
MBON11=2, motor-left=1 and motor-right=1.

| Effective time | Rolling300ms L/R counts | Adapter difference | Recorded action |
| --- | --- | --- | --- |
| 2.300s | 0 / 2 | +6.6667Hz | `advance`, reason/trigger `motor_right`; next input clip1/frame0 |
| 3.500s | 3 / 4 | +3.3333Hz | `stop`, reason `playlist_exhausted`, trigger `motor_right` |

There were33 watch evaluations, one advance and one stop. Total recorded spikes:
KC18080, PAM11=2, PPL101=370, MBON07=17, MBON11=92, motor-left=23, motor-right=9.
Totals do not substitute for the declared rolling window or establish preference.
Intrinsic DAN population spikes do not imply external stimulation, dopamine
concentration or receptor activity.

## Identity and artifact bindings

The reviewed33-member packaged Python/C++ model-source identity is
`e8d0e046e890418541ee9f0bb84065966228e756834f5bd7fb084f9ff5005ba8`.
Schema remains`3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Native source is`e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509`;
Windows memory.dll is`21c03b93e5afee5e630ceaf9fbe6805286e84a3653abefa1de18a6b2b583e0f1`.
All33 package-source bytes matched before/after observe, verify and export.
Exact local identities are not portable source/native-history attestation;
LF normalization and formal source freeze remain future assay gates.

| Binding | Value |
| --- | --- |
| Run directory | `runs/video-observation-reels-20261102` |
| Events SHA256 | `10b15d4367ea4d587d7c95ac9d2cc6c1cdf083411e9db0124dd6a696fb19960b` |
| Metadata SHA256 | `f257daf3d8f88b467fb18c9d84ccd6dd50f557f8ac18ec52414929ae45f9cd10` |
| Final scientific-chain SHA256 | `3bd66c20826f912876af6848f56c1a282bcde0ee989f73f3ced5aca590c4fc7a` |
| Before NPZ / tick0 | 5,092,570 bytes / `9a73cd8368658167290114500acb0a3a3ebdb9ea97b925e4976ede746dd0fb1d` |
| After NPZ / tick35000 | 6,864,518 bytes / `5ce4df567d4576b2a540499b6809038fdc91236f1ee8c0a1ad717cc59fca6535` |
| Compact replay | `runs/measured-video-replay-reels-20261102.json`,6,266,520 bytes |
| Compact SHA256 | `ca85478dbe65edf64b4d60d579699b672aed54bc34f833a9d7c7837d3183e6f5` |

The environment was Windows, Python3.12.14, Zig0.16.0, Node24.21.0/npm11.19.0,
PyAV19.0.2. FFmpeg library versions: libavutil61.1.102, libavcodec63.1.102,
libavformat63.1.102, libavdevice63.1.102, libavfilter12.1.102,
libswscale10.1.102 and libswresample7.1.102. The optional media archive is locked;
existing core dependency versions and native equations were unchanged.

## Verification and visible replay

Independent scientific/integrity review found three decoder defects; genuine
H.264 SEI, variable-resolution and bounded high-fps regression fixes closed all
findings. Final focused backend/CLI checks: **81 passed in42.49s**, exit0/no skips.
Independent closure ran four overlapping regressions,360 selected-PTS oracle
comparisons and real rotation/mirror rejects. These are not additive suites.

Recorder/replay compatibility on the preceding8f69b283 candidate was **621
passed,2 skipped in84.09s**: sandbox junction creation and opt-in fullgraph
context. The normal-host junction subset separately passed2 tests/401 deselected
in0.14s. Only video_observation.py changed afterward; other32 package files and
schema remained identical. The81-test final focus covered the decoder fixes.
No whole assay/full project suite or opt-in graph-context rerun is claimed.
An earlier exploratory whole-suite start was interrupted; it is not a pass.

The actual commands below exited0, respectively35.843s,1.094s and1.766s:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli observe-video --playlist .tools/reels-source/playlist.json --output-dir runs/video-observation-reels-20261102
.venv/Scripts/python.exe -m fly_connectome_sim.cli verify-run runs/video-observation-reels-20261102
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-video-replay runs/video-observation-reels-20261102 --output runs/measured-video-replay-reels-20261102.json
```

Independent raw audit re-decoded both sources and matched all240 declared
selected PTS/RGB hashes and105 consumed pixel payloads. Counts, contiguous bins,
half-up boundaries, rolling windows and the next clip/frame were checked. The
actual frontend reader accepted the compact file and matched boundary samples,
including frame2 at667ticks. Ordinary verification/export preserve
`integrity-only`; they do not attest decoder correctness or native training history.

Viewer source review closed all findings; final57 tests and TypeScript/Vite
build passed. All18 viewer file identities matched freeze
`10ba7c3bacb748434ddebc17d60bf56b66ce2a7e698f1615b4eb654c92b8e5fc`.
Chrome imported the actual JSON. At tick22999 it displayed clip0/frame68,
PTS26800, KC2.61 and the previous WATCH decision. At23000 it selected
clip1/frame0, PTS0 and ADVANCE; current-clip rolling evidence was unavailable.
At23100, MBON11=50.00 and KC2.41 matched actual bins. Playback at0.5x advanced;
pause held tick1462. Terminal35000 displayed playlist exhaustion/motor-right
with L3/R4. Export restored the paused23100 source position.

The actual UI export is`viewer/test-output/reels-measured-replay-30fps.webm`,
**1,246,462 bytes**, SHA256
`96278f99e516e7330b30a06eed3e8b111adb6900fdaf0c5ef70acf5fb1b69fd5`.
Independent EBML inspection counted120 VP9 frames in two clusters,33/34ms
spacing, PTS0..3967ms and explicit final end4000ms. Separate PyAV decoding
confirmed120 frames,900x900 and4.000s. Decoded frames0/8 visibly change
illustrative wing/body pose within clip0; frame71 shows the foreground leg
gesture after the recorded advance; frame84 shows clip1 content. Frame119
retains the genuine terminal sample with a presentation-hold label. The15 hold
frames add no simulation time or activity. No swipe is invented for the stop.

This bounded Windows/Chrome source/raw/file/visible-motion acceptance does not
guarantee foreground browser FPS, all codecs, mobile/accessibility or other
platforms. Further presentation work must reuse this artifact. Longer/more-reel
sessions, broader browser polish, LLM planning and the formal assay remain open;
there is no automatic additional native/qualification/C1 run.

Raw media, tool receipts, checkpoints, run, compact JSON, screenshots and encoded
video stay ignored. A fresh checkout needs its own local sources/runtime and
new evidence; the tracked instructions and report do not replace unavailable
bytes. See [commands](../getting-started.md#local-video-observation-and-recorded-feed-actions)
and [live handover](../cloud-handover.md).
