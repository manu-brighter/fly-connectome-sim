# Passive-cell buffers and image admission — actual bounded measurement

The one prospectively specified acquisition completed with all observations and
resource bounds intact. Public offline inspection and independent result review
passed with the clock limitation below. Both waiting inputs were handed off before the accepted
five-real-minute deadline. This is a short local engineering measurement, not
native replay attestation, browser throughput or event-capacity qualification.

## Source and execution

The [protocol](../superpowers/specs/2026-11-09-live-buffer-performance.md) was
published before implementation as`1ad9f53`. All three
[source tasks](2026-11-10-live-buffer-software.md) were independently accepted.
Final source`70a73b19125d89fab5d4796284047b04eddd6752` passed
[CI42722594833](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42722594833):
1469 existing backend passes/47 skips in634.94s;253 new buffer-suite passes/six
Windows-only skips in182.48s;243 viewer passes/four private-artifact skips and build.
The Windows symlink cases skipped locally passed on Linux. Test jobs retain their
15-minute limits, with every original test preserved.

Concrete independent preflight accepted the actual protocol/readiness, clean
source/upstream, existing Python worker/compiler/native cache, source union,
fresh directories and exact owned-supervisor command. The only compiler invocation
was the pinned version probe; no rebuild or model construction occurred at preflight.
One native run then executed from2026-11-09T23:56:14.503766Z to
2026-11-10T00:04:12.214106Z. It used one fresh engine and continuous decoder with
no restore, learning, external DAN or pathway/qualification detail. Passive decay and
all explicit black intervals remained unchanged. No API call or retry ran.

Actual artifacts remain under `runs/live-buffer-performance-20261110-01/` and
`.tools/live-buffer-performance-20261110-01/`; controller inspection/CI evidence
is under `.tools/live-buffer-performance-controller-20261109/`. Completed directories
must not be resumed or overwritten. All64 frozen source/frontend files remain
byte-identical, including the41-member package fingerprint
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.

## Complete activity and admission record

All120×500-model-ms observations completed:60 model seconds,6000 original10-ms
bins,600 completed100-ms aggregates,122 sealed events and two checkpoints.
The source-bound header selects256 cells:231 KCs and all25 required other cells,
with512 static model edges. Static edges are not measured synaptic transmission.
The full KC population has4064 members; the cohort is a subset.

The fixed ring received6000 bins, retained1000 and evicted5000, finishing at write
position0. Its owned arrays remain288000 bytes; each detached observation export
adds17040 array bytes temporarily. These figures exclude Python objects, serialized
journals and the neural engine. The independently reconstructed chronological digest
is`cad5e6899118c0d2b1b0c1f9b61e1722389cc9109c56931b0945417be554d4a4`.
Header digest:`e8540ba3fd3a9cfcdbd849ca4ed2a3444a6e39b4f31e9128c0cef4c4641159b1`.

| Request | Input | Actual wait until first observe | Result |
| --- | --- | ---: | --- |
| 1 | A | 0 ms | Handed off |
| 2 | B | 147000 ms | Handed off before300000ms |
| 3–5 | Fixed A/B/black burst | No admission | All rejected as full |
| 6 | Explicit black | 156671 ms | Handed off before300000ms |

Both waiting inputs completed; final active/pending slots are empty and sequence
high-watermark is6. No expiry fallback occurred in this acquisition. Exact-boundary
expiry and both-expired fallback remain separate synthetic software evidence.
The three rejected offers were neither retained nor retargeted. This records one
active/one pending exercise, not an admission-rate guarantee for arbitrary guests.

## Recorded decisions and timing

The unchanged continuous drive emitted five proposals, all for`drink-00`:

| Completion in model time | Target in Rappen | Price-block left/right spikes |
| ---: | ---: | ---: |
| 12 s | 450 | 40 /10 |
| 24 s | 450 | 40 /13 |
| 36 s | 550 | 29 /22 |
| 46 s | 500 | 23 /13 |
| 60 s | 500 | 28 /10 |

There were20 lower direction decisions,90 collecting results,five unsupported
blocks and no resets or unfinished routes. After the fifth proposal the decoder
is empty and ready; the final result still contains that fifth proposal, not an
additional pending selection. No selling price was activated. Observed coverage
is1/20, distinct from the accepted synthetic reachability of all20 drinks and both
endpoints. Neither400 nor700 Rappen occurred here. Favorites are allowed under
the user's experimental-pilot criteria; no rotation or minimum-output gate was added.

Engine setup took3078ms and static-header construction407ms. Each500-model-ms
observation took1469–4203 real ms (mean3849.54ms); completed local snapshot gaps
were1609–4235ms. Completion-to-snapshot delay was0–16ms. The6000 callback sink
bodies totalled212.4358ms; post-observe copying/aggregation totalled13.0862ms.
Engine-side callback preparation is included in engine/end-to-end time, not
separately claimed as sink cost. Recorded compute/kernel sums were461.8088815s /
453.4400333s. Self-recorded timings are not independent clock attestation.

Additional runtime review found that this Python3.12.14 Windows executable uses
`GetTickCount64()` for `monotonic`, with15.625ms reported resolution, and
`QueryPerformanceCounter()` for `perf_counter`, with100ns reported resolution.
Integer-ms serialization does not improve the former's resolution. The frozen
inspector adds1ms to its sink/copy enclosing-interval checks; its original
endpoint-quantization rationale does not account for this clock difference.
All actual frozen checks passed. An additional exploratory compute-versus-wall
comparison with a1ms allowance fails44/120 observations; that comparison was not
an acquisition gate and does not relabel the successful producer/inspector.

Reported wall durations/waits retain their original recorded values and coarse
resolution. Both waits and resource measurements have large margins to their
limits. Future live service timing must use one common suitable high-resolution
clock for deadline/cooldown and duration arithmetic, rather than repeat the1ms
assumption. Do not alter frozen sources, round historical records into agreement
or rerun this acquisition to remove the limitation.

| Supervised quantity | Actual | Fixed limit |
| --- | ---: | ---: |
| Wall duration including setup/finalization | 477.704 s | 900 s |
| Actual held worker peak working set | 944357376 bytes | 4294967296 bytes |
| Sampled combined output/evidence/scratch peak | 41836953 bytes | 268435456 bytes |
| Retained output/evidence | 21157074 bytes | Included in combined accounting |
| Maximum adjacent poll gap | 0.266 s | 2 s |
| Active owned processes after cleanup | 0 | 0 |

There were1862 monitor samples, exit0, empty stderr, completed terminal receipt
and fixed cancellation byte`2`. Peak RSS belongs to the actual held worker;
children are reported separately. Bounds are stop thresholds, not OS quotas.
Observed total wall/model ratio is7.9617;100-model-ms windows do not imply10-Hz
wall-clock presentation. No browser rendering or network delivery was measured.

## Integrity records and interpretation

The public command completed successfully, with its output equal to the producer
summary and no error output:

```powershell
.venv/Scripts/python.exe scripts/run-live-buffer-performance.py inspect --output-dir runs/live-buffer-performance-20261110-01
```

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Protocol | 25040 | `7e4774a4218acbcaff095e875f403f77700502f971a367f03572b4c8ed629280` |
| Readiness | 3131 | `6edad792b476eeea517f3387f384f080ed935fbbeb9680b5832efbfde5ee625e` |
| Manifest | 124069 | `742d2dcafb30de8f0506d102bdb2eee3ce304a053d0bd9b3176093418c108613` |
| Events | 8683578 | `48104625d5175b8db96b154656f860bf9e25a2318aa1e22cdbe6d1f95c344017` |
| Initial checkpoint | 5093122 | `3f1f7a0fe9d6b3d2d487ac2de52b075e7164474d607d1dae402f886bc5eb6bd4` |
| Final checkpoint | 6862344 | `3fee6acaf7833bf2239cc048429446a236effaa3ee18c89437701c0407909d1e` |
| Summary | 78934 | `d047780b7d393cbb268d82efce2d336b9c41806d3f146e9d10ee66bd4c22d956` |
| Producer receipt | 883 | `9d8fbb0f32154eeecb953be9c1eabe28add49f921670a3207bd58f41390b880c` |
| Supervisor receipt | 2247 | `b84d352758c9d5ee998221ec1d4b305b58b0c85c2a95c2d51f43b2c4a17ac4b7` |
| Resource samples | 281109 | `27a64d9f97380cc142f215e7f8da7ebc8ab0b601a648eef33b654aeb838441b5` |

Validity/resource compliance, fixed-buffer/queue correctness and observed timely
handoffs are separately accepted. Astra independently reconstructed the complete
event chain, all bins/windows and120 ringhashes, cell/group coupling, queue and
all120 decoder outputs, plus both complete checkpoint-state hashes and actual
source/runtime/release/resource/cleanup bindings. The bounded result supports
separately specifying the local synthetic Stage-C price service/board under the
accepted slow experimental-pilot criteria. No further readout tuning is required.
The next contract must test durable/idempotent price activation, real30-minute
cooldowns, stale/reordered proposals, restart/clock uncertainty and operator pause.
Known A/B/black are performance inputs, not new held-out evidence
of image effects. The earlier matched-state comparison remains separate. This run
does not establish semantic recognition, biological learning, general drink variety,
live browser behavior,300-guest/12-hour capacity or public-event readiness.
