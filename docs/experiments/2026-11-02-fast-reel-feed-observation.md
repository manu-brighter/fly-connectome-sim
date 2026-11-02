# Fast reel feed: 5× content and a recorded quick swipe

Visual follow-up: the user's subsequent screen-contact request supersedes this
export's limb-animation acceptance. Its frame/input/count checks remain valid,
but the old whole-leg tilt did not visibly swipe across the screen. The
[screen-contact correction](2026-11-02-screen-contact-swipe.md) reuses exactly
this measurement artifact; it does not create new simulation evidence.

The requested fast-feed pilot is complete on Windows/Chrome. The first reel
ran for **3 seconds**, showing about 15 seconds of source content; the second
ran for **4 seconds**, showing about 20 seconds. Exact selected RGB frames went
through the existing MaleCNS engine at normal simulation time. A recorded
motor-right action caused the first transition, illustrated by a **200ms**
clipped phone/leg swipe. The second clip ended at its external window limit.

The actual encoded file has **225 VP9 frames at 30fps**, 900×900, lasting 7.5s:
7s recorded simulation plus 0.5s labelled terminal hold. This is an engineered
display policy, not learned preference, semantic understanding, validated motor
behavior or proof that visual content rather than autonomous dynamics caused
the activity. No training/control assay or new scientific support is claimed.

## Closed profile and source clocks

The [fast-feed contract](../superpowers/specs/2026-11-02-fast-reel-feed.md)
adds explicit `--profile fast-feed` with the v2 protocol/stimulus/policy/compact
version quartet. Omitted/default `standard` keeps v1 recording semantics.
Its recipe remains exact; v2 adds `source_speed:[5,1]`,
`source_window_seconds:20`, and uses 30000-tick minimum dwell with policy v2.
No native equation, schema or dependency changed.

Source files are the same two downloaded renditions from the
[earlier 1× pilot](2026-11-02-video-feed-observation.md):

| Ordered reel | Source SHA256 |
| --- | --- |
| [DcTiO6Ls3HT](https://www.instagram.com/reel/DcTiO6Ls3HT/) | `8cfa586a94b5e40ad00b197a57da348080bf4aa4490618ce9f5cf6778c0103fa` |
| [DZHp4mtNvJb](https://www.instagram.com/reel/DZHp4mtNvJb/) | `b30f710936b4799eaf1c158f6cc83067f5d1c25ee8596ea9b663752d0f1d2401` |

Before engine construction, both complete first-20s source windows were
validated and hashed, with 120 declared 90×160 RGB uint8 frames each. Sampling
selects the greatest normalized source PTS ≤ 5*j/30. This deliberately samples
sped-up media; it does not process every original video frame. The last sample
is at 19⅚s, while coverage must reach 20s. Clip0 timebase is 1/11988, origin0,
coverage endpoint240000, last selected PTS237600; clip1 uses 1/15360, origin0,
endpoint307200, last selected304640. Both have 120 distinct selected PTS.

Simulation still advances every consumed input interval at 30Hz, with cumulative
half-up 0.1ms boundaries and 333/334-tick durations. No global 5× replay, skipped
simulation interval or pairing with old measurements was used. Stimulation
was None, learning=False, both detail flags=False, with normal passive evolution.
No reset/restore or fabricated random seed was introduced. Media PTS and
simulation clock are labelled separately; audio is not neural input.

The v2 policy preserves the 1Hz lateral motor adapter, rolling nine-frame/300ms
counts and 100ms evaluations. Motor advances wait until 3s; a 4s clip cap and
8s session cap remain explicit external limits with recorded reasons. Decoder
geometry/SAR/orientation checks, incremental retained-frame memory, 4096 decoded
frame cap, output limits and no-replace publication remain in force.

## Actual run and actions

One actual run completed in **76.734s**, within its 240s subprocess wall budget.
Ordinary verify/export completed in 1.203s/2.250s; all exited0. All 33 packaged
source bytes matched the reviewed freeze before and after each command.
The sealed pilot has 212 events: before checkpoint, 210 observations, after
checkpoint. It contains 840 bins over ticks0..70000: 90 inputs from clip0 and
120 from clip1. There were 68 WATCH, one ADVANCE and one STOP evaluations.

| Effective time | Rolling300ms L/R counts | Adapter difference | Recorded action |
| --- | --- | --- | --- |
| 3.000s | 3 / 6 | +10Hz | ADVANCE, `motor_right`; following input clip1/frame0 |
| 7.000s | 6 / 3 | −10Hz | STOP, `playlist_exhausted`, trigger `clip_window_end` |

The terminal event is an external four-second clip limit, not a neural rejection.
No STOP swipe or nonexistent next clip is invented. Populations are KC4064,
PAM11=15, PPL101=2, MBON07=4, MBON11=2, left=1 and right=1. Total spikes:
KC46571, PAM11=1, PPL101=815, MBON07=28, MBON11=195, left=119 and right=45.
Totals do not replace the declared rolling window or establish preference.
Intrinsic DAN spikes do not imply external stimulation, dopamine concentration
or receptor activity.

## Exact identity and bindings

The reviewed 33-member local model-source identity is
`132b9c00a2a7d3d5da15963024abf85a0a31209d7f59f5903dd4edd9298a0ac2`.
Schema remains `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Native source/DLL and the Windows Python3.12.14, PyAV19.0.2, Zig0.16.0 and
Node24.21.0/npm11.19.0 environment match the earlier linked pilot. Only cli.py,
video_observation.py and video_policy.py changed among packaged sources;
the other 30 remain unchanged. Formal source freeze/LF normalization and assay
qualification remain future gates; old evidence is not upgraded to this source.

| Binding | Value |
| --- | --- |
| Run | `runs/video-observation-fast-reels-20261102` |
| Events SHA256 | `d6879ad06893b495aecc07b71735aff9c1fa84cbd5d7d37032d84d39b094eee7` |
| Metadata SHA256 | `5c6c53ed2a1d3da770e0e6f3295d25a3515cf1d8ea4bcacf08728e086b9c0b00` |
| Final scientific-chain SHA256 | `c2a80a317659355477cae8817135f386f6736a2be9d0ae32c01711ca8f8dd056` |
| Before NPZ / tick0 | 5,092,567 bytes / `46ec2fb5de5b9e75a4447b3c7fe50bb49ad20ec8d515ea1f2a07068d57a07b32` |
| After NPZ / tick70000 | 6,872,651 bytes / `2ab3e4c2baa74a954dbace52708d27d1856ae697b195fb38a27b29b116442434` |
| Compact JSON | `runs/measured-video-replay-fast-reels-20261102.json`, 12,443,795 bytes |
| Compact SHA256 | `fa9565bea925a66b2afaccb6e337a8dd5c3c2d0b52e65524575325e936b29323` |

## Verification and visible acceptance

Test-first implementation completed **114 focused backend/CLI tests in94.32s**
(all81 previous cases plus33 new), no warnings/skips. Independent Astra review
closed C0/I0/M0, verified the frozen bytes, 19,360 pure policy-reference cases,
all240 separately decoded actual source PTS/RGB hashes and original historical
v1/A-B re-export bytes. No native pilot was executed by that reviewer.
Historical outputs remained byte-identical at 6,266,520 and 218,993 bytes.
The viewer passed **63 tests and TypeScript/Vite build**; independent Sol review
closed C0/I0/M0 on all18 frozen viewer files, manifest SHA256
`41423f850430b40c1447c6d508efbbef6682e36f563d864d03014aac3e30e00f`.
The existing >500kB bundle advisory persists. No whole assay/ordinary project
suite or fullgraph map-context opt-in rerun is claimed for this product slice.

Actual commands, guarded by source checks and the one-shot wall budget:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli observe-video --profile fast-feed --playlist .tools/reels-source/playlist.json --output-dir runs/video-observation-fast-reels-20261102
.venv/Scripts/python.exe -m fly_connectome_sim.cli verify-run runs/video-observation-fast-reels-20261102
.venv/Scripts/python.exe -m fly_connectome_sim.cli export-video-replay runs/video-observation-fast-reels-20261102 --output runs/measured-video-replay-fast-reels-20261102.json
```

Post-run independent raw audit re-decoded both sources and matched all240
declared RGB/PTS values and all210 consumed pixel payloads. It checked counts,
contiguous clocks/bins, 5× media mapping and v2 policy priorities/next inputs.
Actual frontend parsing accepted this v2 artifact and both original real v1/A-B
files. Ordinary verification is stored `integrity-only`; it does not attest
decoder correctness or native history. Content equality is not scientific support.

Chrome imported the actual compact file. At29999, clip0/frame89 still had WATCH
and no swipe. At30000, clip1/frame0 followed the recorded ADVANCE. At30667,
clip1/frame2 had media PTS5120/15360, MBON11=50.00 and KC3.10, with the visible
clipped outgoing/current-incoming composite and foreground leg gesture. At32000
the 200ms swipe was over and the exact incoming frame filled the phone.
STOP70000 showed playlist exhaustion/clip-window-end with L6/R3 and −10Hz.
Replay1× advanced; pause held10994. Export restored paused30667.

The actual UI WebM is `viewer/test-output/fast-reels-measured-replay-30fps.webm`,
**2,486,947 bytes**, SHA256
`1f21825de97cadb8645ddc46124ba7ad2e53ef3debcfcefc2c30b8803bf40e4c`.
Independent EBML inspection counted225 VP9 frames in four clusters, 33/34ms
spacing, PTS0..7467ms and explicit final end7500ms. Separate PyAV decoding
confirmed225 frames/900×900/7.5s. Frame92 shows the mid-swipe at3.067s;
frame96 at3.2s has no composite/caption; frame224 retains the genuine terminal
sample with a presentation-hold label. The six-frame swipe uses the last fed
outgoing frame and the currently fed incoming frame, is labelled illustrative
and adds no neural input or ticks. Reduced motion bypasses it in tested code.

This is bounded Windows/Chrome source/raw/encoded-file/visible acceptance,
not a foreground FPS, mobile, all-browser or accessibility guarantee. Reuse the
new ignored compact artifact for further presentation work. Raw sources, runs,
checkpoints, receipts, screenshots and video remain ignored. A fresh checkout
needs its own local media/runtime and evidence; see [commands](../getting-started.md#local-video-observation-and-recorded-feed-actions)
and [handover](../cloud-handover.md). Longer/more-reel sessions, LLM integration
and the formal learning assay remain separate unfinished work.
