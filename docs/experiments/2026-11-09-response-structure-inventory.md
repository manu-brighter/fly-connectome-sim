# Recorded response structure — bounded descriptive inventory

Status: actual offline calculation complete and independently accepted. The fixed
comparison finds distribution differences among some active
sampled-KC responses, beyond common magnitude scaling. It does not establish a
usable drink decoder, twenty reachable outcomes or biological/semantic preference.
No new neural acquisition, training or provider request ran.

## Fixed scope and software evidence

The prospectively accepted [spec](../superpowers/specs/2026-11-09-response-structure-inventory.md)
and [plan](../superpowers/plans/2026-11-09-response-structure-inventory.md) fix all
eight arms and eight500-ms windows from the accepted
[matched-state diagnostic](2026-11-09-market-response-diagnostic.md). There are64
vectors and224 unordered pair/window comparisons, including28 primary comparisons
at model5.5–6.0s. All three identical-input pairs are marked at each window:24
repeat checks. The four black-prefix observations are validated but not compared.

The21 sampled-KC buckets comprise the unchanged20 eleven-cell groups and one
eleven-cell excluded-sample bucket. They cover231 recorded KCs within256 recorded
cells, not all4064 model KCs. Seven full-population profiles retain their separate
membership/size and exact per-neuron rates. They are not treated as a partition;
their sum is explicitly algebraic. Counts, decimal-string sums and reduced exact
fractions are retained; undefined zero comparisons stay null.

The external analyzer preserves the package and previous scripts/decoders. It
checks caller-pinned raw hashes, validates all79 original events/68 observations
and three checkpoints with the frozen inspector, then derives values from a second
complete scan of the same private snapshot. Both iterators close explicitly even
with retained exception tracebacks. A4MiB limit includes the terminal newline;
output publication is exclusive and rejects linked parents.

Independent source/protocol review accepted the implementation. Actual local test
evidence covers54 distinct new passes with two Windows symlink-privilege skips:
53 passed/two skipped in253.63s, then two focused tests passed in17.62s after a
precise original-error assertion and one all21-bucket arithmetic case were added.
The unchanged offline regression passed184 cases with five Windows symlink skips
and four explicitly excluded native-construction cases in263.34s. The first host
run's two test-only snapshot-path failures and earlier sandbox hardlink failures
are retained in local logs; they are not reported as passes. All62 inventoried
old source/package/lock files remain
byte-identical; the workflow adds only the new test filename.

Prospective checkpoint `8e484224c459d1b08e2815c13159dc659bfaa415` passed
[CI42688192608](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42688192608):
766 backend tests /41 skips in259.34s,243 viewer tests /four skips and build.
That checkpoint predates the new analyzer and is not its clean-checkout test result.

Source/result checkpoint `dfe16787573d911bd68973a3bbfe9e00e09a6249` passed
[CI42691875940](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42691875940):
822 backend tests /41 skips in263.92s,243 viewer tests /four skips and build.
All56 new analyzer cases passed on Linux, including both locally skipped symlink cases.

## Actual execution and complete comparison counts

After source acceptance and independent concrete preflight, one declared offline
CLI invocation completed with exit0 in7.4114244s. It produced the233732-byte
report at `.tools/response-structure-20261109/report.json`; all64 vectors and224
comparisons remain there. Six reviewed source files and all eight original
diagnostic artifacts matched their before/after hashes. This is a processing
duration, not a new model-performance measurement.

Independent review recomputed all64 vectors and224 comparisons from the pinned
raw recording, checked full event-chain/EOF/checkpoint validation, exact fractions,
all21 buckets and seven population rates, silence and repeat/primary labels.
Every result and the six-source/eight-artifact preservation check matched.

| Profile | Proportional | Nonproportional | Both silent | One silent |
| --- | ---: | ---: | ---: | ---: |
|21 sampled-KC buckets |7 |15 |106 |96 |
| Seven population counts |24 |91 |10 |99 |

All counts below use the complete predeclared28 pairs per window. They are not
independent replicates; repeated arms deliberately remain in the matrix.

| Window / model time(s) | KC proportional | KC nonproportional | KC both silent | KC one silent | Population proportional | Population nonproportional | Population both silent | Population one silent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
|0 /2.0–2.5 |0 |0 |28 |0 |4 |6 |3 |15 |
|1 /2.5–3.0 |1 |0 |15 |12 |4 |11 |1 |12 |
|2 /3.0–3.5 |1 |0 |15 |12 |4 |11 |1 |12 |
|3 /3.5–4.0 |1 |0 |15 |12 |4 |11 |1 |12 |
|4 /4.0–4.5 |1 |0 |15 |12 |2 |13 |1 |12 |
|5 /4.5–5.0 |1 |5 |6 |16 |2 |13 |1 |12 |
|6 /5.0–5.5 |1 |5 |6 |16 |2 |13 |1 |12 |
|7 /5.5–6.0 primary |1 |5 |6 |16 |2 |13 |1 |12 |

## Primary window: support and magnitude

| Arm / frame | Whole-population KC spikes | Sampled KC spikes | Excluded-sample bucket spikes |
| --- | ---: | ---: | ---: |
| control-1 /black |0 |0 |0 |
| vertical-left /A |1 |0 |0 |
| vertical-right /B |4396 |250 |6 |
| vertical-left-repeat /A |1 |0 |0 |
| control-2 /black |0 |0 |0 |
| horizontal-top /C |4520 |260 |6 |
| horizontal-bottom /D |4592 |270 |7 |
| horizontal-top-repeat /C |4520 |260 |6 |

The three distinct active-frame contrasts have the following exact sampled-KC
total variation. The repeated C arm reproduces its B/C and C/D comparisons;
those duplicate pairs explain five nonproportional primary matrix entries.

| Contrast | Exact TV | Approximate TV |
| --- | --- | ---: |
| B versus C |12/325 |0.036923 |
| B versus D |29/750 |0.038667 |
| C versus D |107/2340 |0.045726 |

These small exact differences are descriptive, without a usefulness/significance
threshold. All other primary sampled-KC comparisons involving A or black have
undefined normalized quantities; silence is not zero or maximum TV. A has one
full-population KC spike outside the recorded KC cohort, so sampled silence does
not imply absence of every KC response. The C repeat is proportional with TV0.
Black/A/C repeat validations all pass across the entire original trajectories.
Seven-population nonproportionality is a profile-scaling result, not composition
across disjoint biological populations.

## Frozen identities

| Item | SHA256 |
| --- | --- |
| Analyzer | `5a8eaff4e2904191d394859c8eb02ae107a61de04cb000228e371e1c61052b25` |
| Final tests | `f5755b1c37e2e428c729699605d38ffb7b55a84c2657ef30e919d4cafb49f03d` |
| Concrete preflight | `7d2555ea68855b5cc41fca3c8ff24bcff9e4f859c24a6f225df26967ce29c877` |
| Original protocol | `f125b9449594fcbb5d4da751bba39ba2a3014fb00e12af94dc36dc153e318492` |
| Original manifest | `d495de34c84e9b696ab01efcf06ece2bb0e3533b48f0e7b134112ed2c32245b9` |
| Original events | `96ce14faddcbb63e2bfb2417834f14fe93b8cb08f7b40d8a28000cb68ec0a605` |
| Complete response inventory | `eedb293babe890d136587365bcf476d682f7ced1fe6228de20275fc9eda6a481` |

## Interpretation and continuation

The inventory does not meet its all-proportional stopping condition: some active
sampled-KC response shapes differ. It supports considering a separately specified
engineering readout/calibration question, with the small differences, sparse
support, dominant baseline and continuous-state uncertainty kept visible. It
does not itself supply that decoder or authorize a held-out acquisition.
The motor v1/v2 negative results remain unchanged. Stage B stays open; no Stage C,
twenty-outcome qualification, semantic claim or public-event readiness follows.
