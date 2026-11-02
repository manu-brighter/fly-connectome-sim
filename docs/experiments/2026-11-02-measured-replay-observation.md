# Measured Replay observation — 2026-11-02

One genuine sealed fullgraph observation is available as local replay data.
Recording/export and source/parser checks passed; **Replay remains WIP**.
The earlier end-pixel video check did not meet the user's animation requirement:
the clip has only 17 frames/13.326s. Phase 1 replaces that capture with timestamped
encoding and visible illustrative fly motion; the actual replacement contains
375 decoded frames/12.5s. Real-video engine input and recorded motor scrolling
are not implemented. This reward-free A/B observation is not a training assay,
native-history attestation, scientific qualification or capacity result.

## Protocol and exact source

The existing actual `FlyEngine.from_prepared_graph()` used the locked MaleCNS
v1.0 prepared graph (166,700 cells; 25,582,938 directed edges). A fresh engine
ran six A/black/B/black cycles, 500ms per observation: 12s simulated total.
Every interval used explicit RGB uint8, external stimulation=None,
learning=False, both detail flags False and normal passive evolution.
Black intervals advanced time. AssayStimuli used seed 11, qualification stimulus
family, 32x32, center/fixed colors; the experiment itself is a `pilot`, family
`measured-observation`, protocol `measured-observation/v1`.

Current model-source SHA256:
`f70722c4c253d48b6496e772a2780e3f6aba3474aca13a7a799bcd5941463b46` (31 members).
Run schema SHA256:
`3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Engine identity SHA256:
`05b42bbdb262cf5b434c0c9359162138b562dc6e25f8432cefb3d90e22dbd2f9`.
Native kernel source SHA256:
`e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509`.
Windows Zig 0.16.0 build, `-O3 -std=c++17 -shared -Wl,--export-all-symbols`,
memory.dll SHA256:
`21c03b93e5afee5e630ceaf9fbe6805286e84a3653abefa1de18a6b2b583e0f1`.

The preceding accepted f.3b model 89c7b754… is historical. Only existing cli.py
and new experiment/measured_replay.py differ; the other 29 sources and schema
remain exact. The recording is bound to current exact source bytes, not a
formal qualification freeze. Later packaged source edits require new evidence.

## Actual commands and bounded result

These commands ran on Windows using the existing prepared graph;
observe had a 240s subprocess wall budget:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli observe --output-dir runs/measured-observation-v1-fullgraph --seed 11 --cycles 6
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli verify-run runs/measured-observation-v1-fullgraph
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli export-replay runs/measured-observation-v1-fullgraph --output runs/measured-replay-v1-fullgraph.json
```

Actual exits were 0. Observe took 208.125s, verify 0.297s and export 0.468s.
The observation stayed within its declared wall budget. No profiler, whole-assay
throughput extrapolation or formal capacity approval follows. Four backend/test
files, all 31 packaged source members and schema matched before/after each
command. No further native recording is needed for browser/visual iteration.

The ordinary sealed pilot contains 26 events: before checkpoint, 24 observations
and after checkpoint. Export is `measured-replay/v1`, 24 segments/1200 bins,
120,000 ticks at 0.1ms, 218,993 bytes. Its SHA256 is
`c362c7a7dc3e8d25054b6c644e293b85e6d7ce52a087724d564bfb6a3b256602`.

| Source binding | SHA256 |
| --- | --- |
| events | 01216e884e131cf84c8082545a6c050b4159474c60be8408b85188188025ae2a |
| final scientific chain | 31cd9fd7b195a7100db40fb4e989d3448ba1f01da4234bfac866c3f83468346e |
| run metadata | f3898e325434320da9ea8790886a0004dd8d9711f06cdfea85a655ad0f6dda7f |
| brain-before.npz | 0350a7e0336a8725b9bd2843f007971fdef27050e10259f4d576d54af3a1df2d |
| brain-after.npz | cd5a7bd533a18163671f2042783e544e77ccaf44fa7fd6b28a9d707b36238bf2 |

Before/after checkpoints are actual native NPZs, 5,092,433 / 6,879,870 bytes,
emitted at event 0/tick 0 and event 25/tick 120000. Root ancestry fields are absent.
The stored source verification mode is **integrity-only**; the word scientific
in the hash-chain field name does not establish scientific support.

## Independent checks and measured counts

An independent raw-file audit checked source/export bindings, every regenerated
input hash, actual observation flags, source clocks, contiguous bins, integer
counts and count/population/duration rate conservation. A further raw audit
checked all 168 segment/group rates, population maps and clocks against the
export. The actual frontend
parser accepted the same fullgraph export and sampled its half-open timeline.
This parser execution is not a browser-rendered DOM/video test.

| Group | Actual population | Total recorded group spikes across 12s |
| --- | ---: | ---: |
| KC | 4064 | 96466 |
| PAM11 | 15 | 0 |
| PPL101 | 2 | 1756 |
| MBON07 | 4 | 42 |
| MBON11 | 2 | 402 |
| Motor left | 1 | 222 |
| Motor right | 1 | 64 |

These are per-group measured counts, not whole-graph totals or a stimulus-causal
comparison. Zero PAM11 counts remain zero. PPL101 population spikes occur
despite no external stimulation; those spikes are model population activity,
not dopamine concentration, receptor activity or an injected reward. Nothing
here establishes associative learning or validated motor behavior.

Historical backend source review passed. Focused actual tiny-native/CLI tests: 44 passed
in 9.58s, exit 0. Separate current-source recorder/replay compatibility: 622 passed,
one skipped in 48.97s, exit 0. The skip is the opt-in full MaleCNS map-context
integration; it was not rerun in this slice. Earlier full-analysis/408/grid
checks remain historical and were not repeated. Packaged source 31/schema are
unchanged in Phase 1; no native test or recording was rerun for this correction.

Current Phase 1 viewer source review closure has zero Critical/Important/Minor
findings after fixing a pending-load/export texture race. Worker checks used
Node 24.21.0/npm 11.19.0: 44 tests passed, TypeScript/Vite build and npm audit exited 0.
The bundled output retains the >500kB advisory (785.06kB JS). The 16-file viewer
freeze JSON SHA256 is
`1f768481cc4652a06056f66bbdb2ade3738debf58b671f3f06be475cb263166c`.
Earlier 42-test/eleven-file receipts are historical, not the current viewer source.
Fresh repeated checks passed 44 tests in 234.9783ms and build exit0; all 16 viewer
files and the 31-member model matched before/after both commands. No native run
was part of these checks.

## Historical browser and end-pixel checks

The user manually enabled Chrome extension local-file access, after which the
actual fullgraph export loaded. No automated settings write occurred. Empty and
loaded desktop/mobile states were observed. Actual checks include:

- Seek tick 13900: B, event 3, source 1.3900s; MBON11=150.00Hz/cell,
  KC=8.37Hz/cell, motor left/right=0.00, matching the independent raw reference.
- Seek tick 14000: MBON11=200.00 and KC=13.48, matching the next raw bin. Home
  returns tick 0, A and measured zeros for all groups.
- Playback at 0.5x advanced; pause at 3.660s remained 3.660s across the next action.
- Source panel displays stored integrity-only and explicitly denies issuing
  browser attestation.
- The full-page 650px desktop view shows complete motor labels. A 375px mobile
  viewport has a 341px stage and no horizontal overflow; B pixels, 200.00/13.48
  values and the full telemetry overlay remain visible.
- Malformed `{}` is rejected with an actionable error while the previous
  12.000s recording remains loaded.

An initial 90,450-byte video decoded but ended at 11.062/12.000s, B. That clip was
also interrupted by download tooling; it is not acceptance evidence and does
not isolate the cause of its short duration. A concrete stop-before-terminal-
render defect was separately reproduced test-first and corrected. The corrected
path paints the existing final measured sample before a deferred capture stop;
it adds no source bin, spike or simulation time.

Re-exporting the SAME actual JSON produced a 110,864-byte WebM, SHA256
`2a2c523a0e038114bd9beee266c4dea9a7e93b10ba1d1fe750441b4a4741337d`.
It was independently opened and decoded 650x660 with no decode error. Its actual
media duration is 13.326s, including terminal-frame hold/browser capture timing;
this is not an exact 12s/30fps guarantee. The visible last frame shows input
black, 12.000/12.000s, KC 1.87 and MBON11=0 with telemetry included. The app ended
on black, event 24, 12.000/12.000s with controls reenabled and the success note.
That clip passed a terminal-frame/overlay check only. Independent later byte
inspection found 17 VP9 frames, median spacing 1003ms and maximum 1008ms across
13.326s. The user's poor-animation complaint is confirmed: the old visual
acceptance was too broad, and the smoothness/animation gate was not met.
Its source-count/pixel/integrity checks remain valid within their stated scope.
The verified retained screenshot is local `final-desktop.png` in the vertical
evidence directory (B at1.390s, MBON11=150.00/KC=8.37 and source disclosure).
The loaded mobile view above was observed inline with viewport/stage geometry;
no valid loaded-mobile screenshot was retained on disk. The saved
`final-mobile.png` repeats desktop bytes and `mobile.png` is an earlier empty
state, so neither file is loaded-mobile evidence.

## Phase 1: actual timestamped animated export

The replacement exports sequential 900x900 frames with Mediabunny 1.65.0 and
WebCodecs, explicit frame-index timestamps and awaited encoder backpressure.
There is no silent real-time fallback. Camera/dimensions are held during export;
progress/cancel and error cleanup do not publish a successful partial video.
The operation gate blocks export during file loading and blocks texture
replacement during export. No packaged Python or native source was changed.

For the same 12s A/B recording, 360 measured samples cover [0,12), followed by 15
explicit presentation-only frames holding the actual terminal sample at source
tick 120000. That hold advances no simulation time or bin. Absolute-time body,
head, wing and leg pose is illustrative, reproducible on seek and respects
reduced motion; it is not measured movement or validated motor behavior.

The actual UI-exported `animated-replay-30fps.webm` is 4,113,326 bytes, SHA256
`2d670f3cd06c3f0fe2db023ea930fdbc80a7177663d879a95eb6578e1a739ee3`.
An independent container audit found 375 VP9 frames in seven clusters, 33/34ms
spacing, timestamps 0..12467ms, explicit last block end 12500ms and declared 12.5s.
Independent PyAV 19.0.2 decoding confirmed 375 frames, 12,500,000us duration and
900x900 RGB images of the same exact file hash.

Decoded frames 0 and 8 (source 0.0000s/0.2666s, both A) visibly differ in body/wing
pose. A fixed fly-region comparison excluding the phone and bottom overlay
also changed; the animation is not just changing labels. Decoded frame 374
shows black, 12.000/12.000s, KC 1.87/MBON11=0 and an explicit presentation-hold
caption. These encoded/decoded checks establish this file's frame schedule and
visible pose changes, not universal live-browser smoothness, scientific behavior
or any causal performance comparison with the old clip.

The SAME input JSON retains SHA256
`c362c7a7dc3e8d25054b6c644e293b85e6d7ce52a087724d564bfb6a3b256602`.
No further native recording was needed. Current video/decoded images/audits stay
local under ignored `viewer/test-output/` and `.tools/replay-export-motion/`.

## Next: authentic video input and recorded actions

Five user-selected Instagram links were supplied; the first downloaded
[reel rendition](https://www.instagram.com/reel/DcTiO6Ls3HT/) is 1080x1920 VP9,
12,771,185 bytes, SHA256
`8cfa586a94b5e40ad00b197a57da348080bf4aa4490618ce9f5cf6778c0103fa`.
The receipt records yt-dlp 2026.10.26 and no browser cookies. It is a downloaded
rendition, not the original upload master; no source interval/decoder-frame
contract or engine observation is claimed from the download alone.

Next comes implementation of the separately reviewed genuine-video observation
and recorded motor-scroll contract after the Phase 1 checkpoint. Real video has not been fed through the
engine, and no causal feed scrolling is implemented or accepted. Do not combine
that reel with the old A/B neural measurements. Reuse the SAME A/B JSON for
visual work; new native video observation follows only after its source/tests/
protocol review. Accessibility/cross-browser checks remain open. LLM work,
formal science and parked C1 stay separate/paused. Follow the
[animated replay plan](../superpowers/plans/2026-11-02-animated-measured-replay.md),
[original Replay plan](../superpowers/plans/2026-11-02-measured-replay-v1.md) and
[fresh-checkout commands](../getting-started.md#measured-observation-and-local-replay).

Phase 1 encoded/decoded audits, frame images and worker checks are local under
`.tools/replay-export-motion/`; genuine-source intake is in
`.tools/reels-source/source-receipt.json`. Historical receipt/logs/audit/parser JSON are under
`.tools/measured-replay-vertical-r1/`; backend receipts under
`.tools/measured-replay-backend/`; viewer root/review logs under
`.tools/measured-replay-viewer/`. Runs/checkpoints/exported pixels/videos are
ignored and absent from a fresh checkout. This tracked report preserves their
identity and limits; it does not replace unavailable raw bytes.
