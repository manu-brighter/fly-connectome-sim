# Measured Replay observation — 2026-11-02

One genuine sealed fullgraph observation is available as local replay data.
Recording/export and source/parser checks passed; **Replay v1 remains WIP**.
Real-file browser playback, sampled displayed values and desktop/mobile checks
passed; the corrected video decoded with its final measured overlay visible.
The bounded vertical check passed, with further product polish open. This reward-free observation is not a training assay,
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

Backend source review passed. Focused actual tiny-native/CLI tests: 44 passed
in 9.58s, exit 0. Separate current-source recorder/replay compatibility: 622 passed,
one skipped in 48.97s, exit 0. The skip is the opt-in full MaleCNS map-context
integration; it was not rerun in this slice. Earlier full-analysis/408/grid
checks remain historical and were not repeated.

Viewer review closure has zero remaining findings. Final repeated checks used
Node 24.21.0/npm 11.19.0: 42 tests passed in 206.567ms and TypeScript/Vite build
exit 0; all eleven first-party viewer files remained frozen. The bundled
Three.js output retains the >500kB advisory. Earlier 39-test runs are superseded
by this corrected 42-test source; runs overlap and are not additive. Independent
source-review closure has zero Critical/Important/Minor findings after the
terminal-render correction. The eleven-file viewer freeze JSON SHA256 is
`1f8b1ab90648bb457bed87ba81968613f6578d1aa1d48d5bd8230b17fbcb4f48`.

## Actual browser and video checks

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
The corrected clip passes this bounded terminal-frame/overlay check; no
quantitative pacing, export precision or causal performance comparison follows.
The verified retained screenshot is local `final-desktop.png` in the vertical
evidence directory (B at1.390s, MBON11=150.00/KC=8.37 and source disclosure).
The loaded mobile view above was observed inline with viewport/stage geometry;
no valid loaded-mobile screenshot was retained on disk. The saved
`final-mobile.png` repeats desktop bytes and `mobile.png` is an earlier empty
state, so neither file is loaded-mobile evidence.

The bounded real recording/parser/browser/video-end vertical check is complete.
Continue with the SAME `runs/measured-replay-v1-fullgraph.json` for dedicated
foreground frame-pacing/export-precision/accessibility/cross-browser checks as
needed for product completion. The project remains experimental WIP. No automatic second
fullgraph run, assay/qualification, parked C1 return or LLM work is authorized by
this report. Scientific gates and claims stay unchanged. Follow the
[Replay plan](../superpowers/plans/2026-11-02-measured-replay-v1.md) and
[fresh-checkout commands](../getting-started.md#measured-observation-and-local-replay).

Raw receipt/logs/audit/parser JSON are local under
`.tools/measured-replay-vertical-r1/`; backend receipts under
`.tools/measured-replay-backend/`; viewer root/review logs under
`.tools/measured-replay-viewer/`. Runs/checkpoints/exported pixels/videos are
ignored and absent from a fresh checkout. This tracked report preserves their
identity and limits; it does not replace unavailable raw bytes.
