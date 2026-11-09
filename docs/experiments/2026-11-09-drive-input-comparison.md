# Fixed-input comparison — actual bounded result

Status: complete native recording, public integrity inspection and independent
raw-data/resource acceptance. No price has been activated.

The prospectively frozen [protocol](../superpowers/specs/2026-11-09-drive-input-comparison.md)
and [plan](../superpowers/plans/2026-11-09-drive-input-comparison.md) use the
unchanged `continuous-motor-drive/v1` candidate and20 technical drink IDs.
The [software evidence](2026-11-09-drive-input-software.md) records separate runner
and supervision acceptance. Final source checkpoint
`dd60d5584fd74f2d362667685cdec543cea3d68e` passed
[CI42709083761](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42709083761):
1469 backend tests /47 declared skips in618.99s,243 viewer tests /four skips and
build. The Windows lifecycle cases passed locally; the local symlink-privilege
skip passed on Linux. Concrete preparation was independently reviewed before launch.

## Recorded comparison

Exactly one supervised acquisition ran from2026-11-09T22:20:47.113856Z to
22:28:49.839662Z. It contains84 actual model seconds,168 observations,8400 native
10ms bins,175 sealed events and three checkpoints. Four seconds of explicit black
establish a common state; four20-second arms each restore that state and receive a
fresh decoder/session. Actual monotonic clocks are never rewound. The model clock
ends at24s, distinct from84s of actual advancement. There was no learning, external
DAN, passive-decay change, cell observer, provider call or automatic retry.

Both complementary quadrant images were fixed before any new projection or
response was measured. All configured price ranges are400–700 Rappen with50-Rappen
grid spacing; that grid is not a cap on the size of a price change.

| Arm | Complete proposals | Drink | Target | Completion after arm start | Price-block L/R |
| --- | ---: | --- | ---: | ---: | --- |
| Black | 0 | — | — | — | — |
| A | 1 | drink-00 | CHF4.50 | 18 model seconds | 39/5 |
| B | 1 | drink-00 | CHF5.00 | 14 model seconds | 35/24 |
| A repeat | 1 | drink-00 | CHF4.50 | 18 model seconds | 39/5 |

The complete supported path takes10 model seconds in each proposal, respectively
86.062/85.656/86.218 real seconds for A/B/repeat. Those path durations differ from
time since image presentation. A's price block is arm-relative16–18s; B's is12–14s.
The raw price measurements bind observations32–35 for A and24–27 for B; final
reporting uses their exact ticks rather than selecting favorable windows.

The full A/B motor sequences differ, as do price and relative completion time;
drink identity and proposal count do not. This is a functional/input-sensitive
result for these fixed inputs and this mapping, not merely a timing-only result.
Black has no complete proposal; unequal output counts do not constitute a matched
drink/price comparison against black. A's40 motor pairs, model-time proposal and
complete scientific end state repeat exactly. Real execution durations differ.
There are no stale/order/source/path-expiry resets.

Observed drink coverage is1/20. Independent synthetic tests cover all165 leaves
across configurations of10–20 drinks and both range endpoints. That establishes
technical selectability, not observed neural diversity. No400/700-Rappen endpoint
was observed here. Long quiet phases and favorites are permitted by the user's
experimental-pilot criterion; no forced rotation was added. Final partial paths
remain unfinished: A/repeat `[0,10)`, B `[0,2)`; these are not further proposals.

## Optical input and limitations

Each image has2048 white pixels and the same pixel-average brightness127.5.
Actual ordered optical vectors are retained before filtering/current mapping:

| Input | R1–R6 positive /3335 | R1–R6 mean | R8 positive /811 | R8 mean |
| --- | ---: | ---: | ---: | ---: |
| Black | 0 | 0 | 0 | 0 |
| A | 1789 | 0.536432 | 352 | 0.434032 |
| B | 1546 | 0.463568 | 459 | 0.565968 |

The values are0/1; vector sums equal the positive counts. Full values, raw Float64
C-order hashes and retinal-array ordering/configuration bindings remain in the
recording. Projection leaves the initial state/clock/identity unchanged. Equal
pixel brightness does not imply equal population stimulation; the comparison
does not isolate spatial arrangement from unequal retinal population coverage.
These are optical samples, not measured injected currents or neural responses.

The result does not establish semantic image understanding, biological learning,
arbitrary-picture generalization, reliable variety or12-hour event operation.
Artifact integrity remains `integrity-only`, not native replay attestation.
Recorded source/owned-worker evidence supports this observed native execution;
it does not turn integrity inspection into formal scientific qualification.

## Actual resources and verification

The supervisor completed with exit0, no cancellation, empty stderr and zero active
owned processes after cleanup. All58 preexisting source/frontend files and the
41-member Windows package fingerprint remain unchanged:
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.

| Measure | Observed | Fixed bound |
| --- | ---: | ---: |
| Wall time | 482.719s | 900s |
| Actual held-worker peak working set | 856920064 bytes | 4294967296 bytes |
| Sampled combined new output/evidence/scratch peak | 50399859 bytes | 268435456 bytes |
| Retained output/evidence | 25571025 bytes | Included in combined accounting |
| Monitor samples / maximum adjacent gap | 1880 /0.266s | At most2s gap |

Stop thresholds are not hard quotas or aggregate process-tree RSS. Recorded
compute time is466.868943s, kernel time456.147316s. Each500ms observation takes
1031–5204ms processing (mean2780.702ms, median3781ms). Separately measured decoder
delivery delay is0–16ms (mean3.894ms); it does not hide computation time. Overall
wall/model ratio is5.747. This is compatible with the accepted slower-than-real-time
experiment, not a cell-display or sustained-load benchmark.

The public offline inspector reproduced the complete summary from bounded snapshots,
all checkpoints, the entire hash chain and strict event semantics through EOF:

```powershell
.venv/Scripts/python.exe scripts/run-drive-input-comparison.py inspect --output-dir runs/drive-input-comparison-20261109-01
```

Astra independently verified all175 events/168 observations/8400 bins,160 decoder
outputs, direct support/price arithmetic, optical vector arithmetic/hashes and all
three complete NPZ state hashes. It accepted exact repetition, clocks/freshness,
release/owner/worker bindings, current sources/runtime, resource samples and cleanup
without findings. No engine, new projection or native simulation was used for that audit.

Actual records are under `runs/drive-input-comparison-20261109-01/`; readiness,
monitor receipts/samples and counted scratch are under
`.tools/drive-input-comparison-20261109-01/`. Completed paths must never be reused.
Controller preflight, CI logs, independent-inspection output and descriptive metrics
remain separate under `.tools/drive-input-comparison-controller-20261109/`.

## Artifact identities

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `runs/drive-input-comparison-20261109-01/protocol.json` | 31141 | `1102c33c50331acd1f0b54402f4b1733701ceab1c1c91a7a06b1d4e6f20f8822` |
| `runs/drive-input-comparison-20261109-01/run/run.json` | 118024 | `182506e32204918bea3239d5ddccb982697ca85746e9d1faf7303f85ccb6eab4` |
| `runs/drive-input-comparison-20261109-01/run/events.jsonl` | 7051951 | `17ecb0f0acafc904573f3cebf1c8a89457485932e07afc3ebab1311bc5ac954b` |
| `runs/drive-input-comparison-20261109-01/run/checkpoints/brain-before.npz` | 5093122 | `3f1f7a0fe9d6b3d2d487ac2de52b075e7164474d607d1dae402f886bc5eb6bd4` |
| `runs/drive-input-comparison-20261109-01/run/checkpoints/black-prefix.npz` | 5909442 | `2c25dea78657908b5f0e51a4877c63cec0ea565fb7e2e78573cbb7051b414415` |
| `runs/drive-input-comparison-20261109-01/run/checkpoints/brain-after.npz` | 6867703 | `a8d6747181eb597ce9b339cc359ce6895531110105405d9e1126370caf6a2924` |
| `runs/drive-input-comparison-20261109-01/summary.json` | 207026 | `ae7879e9ab67efb9608c27675d11ef4f3e49b1e65b75b3f4501c6fe3be7658df` |
| `runs/drive-input-comparison-20261109-01/receipt.json` | 922 | `38e0e9fb2f34e3925615f46b2b1f52d79b0e7d091d5657000c494aeeaed743ec` |
| `.tools/drive-input-comparison-20261109-01/readiness.json` | 3128 | `7684ade75bebdf82141ef2703646208d8912b3a75cf4c23325dba9a0fffcf06d` |
| `.tools/drive-input-comparison-20261109-01/supervisor-receipt.json` | 2250 | `91cbe0134643f29558e5c878a099167429eb2681a67fda8ace88d9d644ce5a07` |
| `.tools/drive-input-comparison-20261109-01/samples.jsonl` | 283658 | `37fb3067c4cce7b39101dd2cd1aff7d3ea6fb2052bfd5c8066ae50aaa3d9d2cb` |

Next, separately specify the bounded passive-cell/rolling-buffer performance
benchmark and image-admission behavior. The user chose a maximum five real minutes
from accepted upload to model handoff; a finite full queue rejects new uploads,
and expired entries must never be handed off late. Source/measurement review and
a concrete finite protocol precede that benchmark. Price service, live uploads,
display and rehearsal remain separate gates; Stage C is not accepted here.
