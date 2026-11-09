# Historical KC screen for twenty drink slots — 2026-11-09

## Result and scope

The user specified 10–20 drinks, 50–300 guests and configurable event duration,
usually 6–8 hours with shorter or approximately 12-hour exceptions. The existing
seven population outputs cannot simply be declared twenty drink channels.

A descriptive screen of the already accepted nine-second cell recording used
twenty artificial groups of eleven KC cells. **One group had every strict
maximum: 14 of 18 half-second windows.** Three windows were entirely silent;
one had a positive tie. A naive absolute-maximum readout therefore does not
provide useful twenty-slot variety on this recording. This is not evidence that
the core cannot respond to images or that every possible readout is impossible.

No new simulation, training, API call, price choice or decision threshold was
used. This historical material is exploratory design data, not independent
confirmation of a subsequently designed adapter.

## Fixed grouping and measurements

Before reading activity, the 231 recorded KC cells were sorted by source ID.
The first 220 ranks were distributed by zero-based rank modulo 20, giving equal
groups of eleven; the remaining eleven cells were explicitly excluded. No
selection or regrouping used measured activity. Frozen declaration SHA256:
`396720efcea69f32255f246a1441ada480e958b9e29a23f444a9b639bcc8dafe`.

All 1,040 original bins were assigned to 18 complete 500-ms windows covering
nine seconds. Included cells contributed 3,684 spikes; excluded cells, 83.
Strict maxima describe counts only, not accepted decisions or biological roles.

| Artificial group | Spikes | Nonzero windows /18 | Maximum per 500 ms | Strict maxima /18 |
| --- | ---: | ---: | ---: | ---: |
| 01 | 99 | 14 | 9 | 0 |
| 02 | 236 | 15 | 21 | 0 |
| 03 | 80 | 14 | 8 | 0 |
| 04 | 252 | 14 | 23 | 0 |
| 05 | 289 | 15 | 26 | 0 |
| 06 | 78 | 15 | 7 | 0 |
| 07 | 146 | 15 | 13 | 0 |
| 08 | 340 | 15 | 29 | 0 |
| 09 | 45 | 14 | 4 | 0 |
| 10 | 418 | 15 | 37 | 14 |
| 11 | 210 | 15 | 19 | 0 |
| 12 | 168 | 15 | 13 | 0 |
| 13 | 94 | 15 | 9 | 0 |
| 14 | 80 | 15 | 6 | 0 |
| 15 | 216 | 14 | 21 | 0 |
| 16 | 244 | 15 | 21 | 0 |
| 17 | 95 | 15 | 7 | 0 |
| 18 | 182 | 14 | 17 | 0 |
| 19 | 242 | 15 | 21 | 0 |
| 20 | 170 | 14 | 17 | 0 |

The three silent windows cover 0–1.5 seconds. At 1.5–2 seconds, groups 08, 10 and
16 tie at two spikes. Every later window has group 10 as its strict maximum.
No significance, independence or false-alarm claim follows from these counts.

## Input and onset check

All 90 stored RGB frames covering the first three seconds are nonblack, and
their bytes match their recorded input hashes. This rules out a uniformly black
video introduction as the explanation for sampled-cohort silence. Whole-frame
brightness is not a reconstruction of actual receptor sampling coordinates.

| Model interval | Mean RGB /255 | Whole KC, 4,064 cells | Recorded KC, 231 cells | Motor L/R |
| --- | ---: | ---: | ---: | ---: |
| 0–500 ms | 88.27 | 7 | 0 | 0/0 |
| 500–1,000 ms | 78.60 | 10 | 0 | 0/0 |
| 1,000–1,500 ms | 82.13 | 9 | 0 | 0/0 |
| 1,500–2,000 ms | 87.02 | 284 | 17 | 0/0 |
| 2,000–2,500 ms | 100.78 | 5,778 | 334 | 6/4 |
| 2,500–3,000 ms | 92.94 | 4,156 | 251 | 7/9 |

The first positive whole-KC bin is 30–33.3 ms; the first recorded-KC-cohort bin
is 1,986.7–1,996.7 ms. Motor-left first appears at 2,020–2,030 ms and motor-right
at 2,353.3–2,363.3 ms. This is sparse/late recruitment in this particular evolving
input sequence, **not an established universal two-second response latency**.

The checked source path is `FlyEngine.observe` →
`VisualMemoryBrain.rgb_step/rgb_drive` → retinal sampling →
`MemoryBrain._neural_step` → `memory_advance`. Its six checked source members
match the historical fingerprint. The model uses 10-ms sensory smoothing and a
1.8-ms fixed synaptic delay; these do not establish effective network latency.
Black input preserves a 12-mV lamina bias and is neither reset nor zero current.

A prospective one-second exposure could miss a late sampled response. A null
within that window would only establish no detected response during that window.
The next diagnostic must predeclare longer observation coverage and matched-state
controls before collecting results; it must not retune a failed held-out test.

## Evidence and verification limits

Exact source bindings:

| Local source | Bytes | SHA256 |
| --- | ---: | --- |
| `runs/cell-demo-20261108-02/cell-activity.jsonl` | 700,081 | `24e61b5c2a066c7da18cd4c191ae64029f1186614883730784e4c81194aef9c2` |
| `runs/cell-demo-20261108-02/cell-activity.json` | 654,051 | `7ab327bf915b2d456874cf38d209fbccb9c0b4cf164f546132982fca672253e3` |
| `runs/cell-demo-20261108-02/session/recording.json` | 13,139,108 | `c1972dc889fcfbe9e603b0d2790092998d46a9ec0780c52f2eb8d8fc3af379bd` |

Checks covered accepted hashes/lengths, header identity, raw/sidecar equality,
original-bin coverage, population arithmetic and a second aggregation from the
sidecar. The input/onset check additionally checked stored RGB input hashes.
Neither screen revalidated graph/annotation sources, performed native replay,
decoded original media or ran the sealed `RunRecorder` verifier. The separate
Stage A analyzer supplies its own stronger sealed-run inventory; these checks
must not be conflated.

Local code, freeze, JSON and Markdown evidence remain ignored under
`.tools/market-kc-screen-20261109/`. The primary `report.json` SHA256 is
`ff6c451dab73bf6ae345b2b5d3882fd8065058b6d69bfc21edcabac292cfd77d`.
This screen cannot qualify twenty-drink control, price range, learned behavior,
arbitrary guest images, live throughput or twelve-hour operation.
