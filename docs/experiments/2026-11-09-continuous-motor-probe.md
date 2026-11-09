# Continuous motor probe — actual negative result

Status: one complete native acquisition, successful offline reconstruction and
independent actual-evidence acceptance. The predeclared outcome is **negative**:
the unchanged decoder emitted no complete drink/price proposal in 96 model seconds.
This is not a resource-aborted or shortened run. Stage B remains open.

## Source and prospective authority

The [protocol](../superpowers/specs/2026-11-09-continuous-motor-probe.md) was frozen
before acquisition. Both [implementation tasks](../superpowers/plans/2026-11-09-continuous-motor-probe.md)
and their [software evidence](2026-11-09-continuous-motor-software.md) were independently
accepted. Source checkpoint `1d32e1c89e9d94659e43a24b8cbbee08e1cf2425` passed
[CI42678625455](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42678625455):
665 backend tests / 41 declared skips in 264.03 seconds, 243 viewer tests /
four private-artifact skips and build. Seven new Windows lifecycle cases skip
on Linux; all 35 new supervision cases passed on the actual Windows host.

Astra independently accepted the concrete protocol/readiness bytes, all 192
schedule rows, source and runtime bindings, fresh inventories, exact command,
successful CI and finite limits before this one acquisition. Approximately
905.7 GB was free. Local output is `runs/continuous-motor-20261109-01/`;
supervision evidence is `.tools/continuous-motor-20261109-01/`. These directories
are complete and must not be resumed or overwritten. No second attempt ran.

The source-bound command was:

```powershell
pwsh -NoProfile -File scripts/supervise-continuous-motor.ps1 -Mode Run -OutputDirectory C:\dev\jogge-di-fly-brain\runs\continuous-motor-20261109-01 -EvidenceDirectory C:\dev\jogge-di-fly-brain\.tools\continuous-motor-20261109-01 -ExpectedProtocolSha256 eb4376bc1c8e02a674b71df63a6bc767f52599132e1990398fd66641c18ec1fa -ExpectedReadinessSha256 ebff539c7be4dac1f32af214ad2f239a4bc7e04f1430d31b5fd262bafd64340a
```

## Complete acquisition

One fresh full-graph engine and the unchanged decoder advanced continuously for
12 episodes of two seconds black plus six seconds pattern. The order was
S1,S2,S3,S4,S5,S6,S6,S5,S4,S3,S2,S1. All 192 observations of 500 ms, 9,600 native
10-ms bins, 194 events and two checkpoints are present. Ticks cover 0–960000.
Both engine and decoder state continue through the 48-second order boundary.
There is no restore, manual decoder reset, adaptive input, training, external
DAN, cell observer or provider request. Final complete-state SHA256 is
`fe8cb78bc70c36189b08ab31273534224f22c34c371625c99c1756407e7da940`.

The producer records `native-supervised`, completes its sealed-data inspection
and exits 0. A separate controller invocation of the public `inspect` command
also exits 0 and reproduces the complete summary. Its stdout has a final Windows
CRLF instead of the stored file's LF: the initial literal byte comparison failed
only for that one additional byte. After newline normalization the entire bytes
match; JSON content is identical. Neither file was altered to obtain agreement.

## Why the declared decoder did not complete

The initial quiet observations arm the decoder once. An unsupported first block
is deferred. The 3–5 second block then records **left 44 / right 17** and accepts
one lower-half decision, narrowing the interval from `[0,20)` to `[0,10)`.
This does not identify a drink or enter the price phase.

The policy then requires two consecutive 500-ms observations, each with combined
left/right count at most two, before another decision. Only observation indices
0–4 satisfy that individual bound anywhere in the full session. After the accepted
direction, all combined counts are 5–27. The 44 later black observations have
combined counts 6–27; none supplies even one qualifying neutral observation.
Scheduled black input therefore does not produce the required measured neutrality
in this continuous session.

The single partial path expires at observation 77, ending at 39 model seconds.
Its age from the first supporting observation's start is 36 model seconds and
302,953 real milliseconds: the existing 300-second real-time bound triggers
before the 60-model-second bound. Extending only the expiry would not supply the
missing measured neutrality in this recording. No alternative policy was run.

| Decoder status / reason | Observations |
| --- | --- |
| waiting / waiting_for_neutral | 182 |
| collecting / incomplete_block | 6 |
| ready / neutral_ready | 1 |
| deferred / unsupported_direction | 1 |
| direction / direction_supported | 1 |
| reset / path_expired | 1 |

Complete routes: **0**. Supported directions: **one lower, zero upper**. One
partial route terminates by expiry. No leaf, target price, price support block
or activation occurs; all 20 proposal counts are zero. There is consequently
no selected-drink concentration or attainable-price-range evidence. The final
pending state is direction phase, interval `[0,20)`, waiting for neutrality,
without a direction history or proposal. It is not relabelled as another expiry.

The following episode totals include each episode's black and pattern phases.
They describe continuous shared-state activity, not accepted directions, matched
replicates or isolated causal effects of the named image:

| Episode | Pattern | Left spikes | Right spikes | Four black-observation combined counts |
| --- | --- | --- | --- | --- |
| 1 | S1 | 123 | 38 | 0, 0, 0, 0 |
| 2 | S2 | 163 | 59 | 18, 13, 10, 27 |
| 3 | S3 | 163 | 41 | 13, 8, 15, 8 |
| 4 | S4 | 184 | 47 | 15, 16, 12, 23 |
| 5 | S5 | 141 | 67 | 13, 17, 10, 9 |
| 6 | S6 | 156 | 59 | 6, 8, 23, 8 |
| 7 | S6 | 177 | 55 | 14, 18, 11, 17 |
| 8 | S5 | 119 | 71 | 6, 27, 8, 14 |
| 9 | S4 | 179 | 71 | 16, 16, 22, 12 |
| 10 | S3 | 133 | 68 | 9, 14, 10, 12 |
| 11 | S2 | 181 | 77 | 15, 10, 12, 26 |
| 12 | S1 | 144 | 44 | 6, 13, 14, 15 |

Every episode aggregate is left-dominant. That descriptive bias is a separate
limitation; removing the quiet-state requirement would not by itself establish
twenty-slot reachability. No favorable window search or threshold sweep was used.

## Actual supervision and timing

The monitor completed from 19:04:07.525752 to 19:17:32.129990 UTC on November 9.

| Quantity | Observed | Fixed bound / interpretation |
| --- | --- | --- |
| Wall time | 804.609 s | 900 s |
| Actual held worker peak RSS | 858,718,208 bytes, about 0.800 GiB | 4 GiB |
| Sampled peak output/evidence/scratch | 40,652,389 bytes | 256 MiB |
| Retained output/evidence after completion | 20,667,412 bytes | Distinct from sampled peak |
| Resource samples | 3,131 | Maximum adjacent gap 0.266 s, below 2 s |
| Active owned processes after cleanup | 0 | Completed owned-job cleanup |
| Worker stderr | 0 bytes | No captured worker error |

The terminal cancellation channel is byte `2`; no cancellation was requested at
cutoff. Peak RSS belongs to the actual held worker, not a launcher measurement
or an aggregate of the entire process tree. Child peaks are separately recorded.
Accounting is complete for the monitored output/evidence roots including scratch.
Limits remain sampled stop thresholds, not OS quotas or a general sandbox.

Recorded compute time totals 792.156052 seconds, kernel time 780.662457 seconds.
Each 500-ms observation took 1,047–5,234 real milliseconds (mean 4,127.177;
median 4,157). Completion-to-decoder handoff was 0–16 milliseconds. These are
different latencies: the 5,000-ms sample-age bound applies to the latter and
does not require the neural computation itself to finish within five seconds.
The recorded observation span is 794.390 seconds; whole-run wall/model ratio
is 8.381. This is one bounded population-only workload, not a live-cell-display,
upload, six-hour or twelve-hour capacity qualification.

## Artifact identities and review

| Artifact | SHA256 |
| --- | --- |
| Protocol | `eb4376bc1c8e02a674b71df63a6bc767f52599132e1990398fd66641c18ec1fa` |
| Readiness | `ebff539c7be4dac1f32af214ad2f239a4bc7e04f1430d31b5fd262bafd64340a` |
| Run manifest | `ed2e30e8afe83450cafe613df4d3158e8a256feb16a4c96fcc0faac0d3bd7bc8` |
| Raw events | `4ea7ddf519fa22ee5158c763a45bd0639226f1235d3540bba11e0205a446395f` |
| Before checkpoint file | `3f1f7a0fe9d6b3d2d487ac2de52b075e7164474d607d1dae402f886bc5eb6bd4` |
| After checkpoint file | `7840e9fbf48045b346ec2655e7ddcdc05f772a91a9825320815a4ca05277c2a8` |
| Summary | `f2880d8e8e58117d57551bf929cce7246a4cb180f89d7fb21778f8bb10fc7a52` |
| Producer receipt | `6098f97688859d8ca53db836d6beda1298b848aac2f630993dae4fa662017efe` |
| Supervisor receipt | `e72649241f9339b3519164d28f63d6870bbea6663d7033094abdead5827f543c` |
| Resource samples | `96f81532531392b3982b90b17d0c67c2b4bc1a016db57247c5e0f58d04347a13` |

The controller rechecked all 41 packaged sources, nine historical diagnostic
bindings, 15 original demo inputs, seven accepted diagnostic artifacts and the
Stage A/retinal reports; all remain unchanged. The new runner, decoder and
supervisor remain at their independently accepted source hashes. Package
fingerprint remains `1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
Local read-only inspection and descriptive metrics are retained under
`.tools/continuous-motor-controller-20261109/`.

Astra independently checked all 194 chained events through EOF, 9,600 bins,
population/rate arithmetic, all 192 reconstructed decoder results, checkpoint
hashes and complete-state digests, clocks, source/runtime bindings, supervision
and historical preservation. The result is accepted as a valid negative, with
no integrity or resource blocker. The absence of later measured neutrality,
single supported direction and real-time expiry are independently reproduced.

This negative result establishes that the declared v1 mapping did not complete
under this fixed continuous schedule. It does not show that every possible
engineering mapping must fail. Artifact hashes and pure decoder reconstruction
are not native replay attestation or scientific validation; consistently
rewritten/resealed timestamps are not independently authenticated.

The next technical step is a separately specified, offline-first concept revision
informed by the observed rearm failure and directional bias. Preserve this result
and v1 source unchanged.
No automatic retry, threshold adjustment, smaller simulator, fabricated price
choice or Stage C advancement follows from this report.
