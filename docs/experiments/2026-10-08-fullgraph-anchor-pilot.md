# Fullgraph one-anchor resource pilot — 2026-10-08

One predeclared trained schedule, two independent A/B response siblings and both
native recorder/replay passes completed. This measures one diagnostic resource
endpoint; it does not qualify a configuration, demonstrate learning or certify
whole-assay capacity. Package source, tests, dependencies and schema were unchanged.

Measured commit: `ec6474b3693beb49a9dde28c0e02c3cca9987dad`. Exactly one opt-in
primary run, no repeat or failed native attempt: 2026-10-07 23:54:22–23:59:40 UTC
(2026-10-08 locally). Windows 11 10.0.26200 AMD64, Python 3.12.14, NumPy 2.4.6,
24 logical processors. Six genuine `FlyEngine.from_prepared_graph()` factories
used 166,700 cells / 25,582,938 directed edges, dt 0.1 ms. Ordered groups matched:
PAM11 15, PPL101 2, KC 4,064, MBON07 4, MBON11 2, motor-left/right 1 each.

## Executed workload and proof

Fresh baseline tick 0; `AssayStimuli(11, "qualification")`, 32×32 center/fixed A/B
and same-shape black RGB uint8. Diagnostic `GridConfiguration(100.0, 0.0, 500.0)`,
paired A/order AB, `controls=True`: all 26 training segments ran. Learning was
enabled exactly when `segment.start_ms < t0` and stimulus or stimulation was
present. The actual PPL101 pulse ran 100 ms at 20 mV; black segments advanced too.
Both detail flags were False throughout. No frozen configuration was constructed.

Association T0 / paired retention reference was tick **109000**; schedule-complete
durable source was **111000**. T=10,000 ms from that reference gives CS onset
**209000** and retained anchor **208000**. Source-to-anchor was exactly 97,000 ticks
(9,700 ms): 19 black calls of 500 ms plus one of 200 ms, with learning False,
stimulation None, current 20 mV and weights unfrozen for passive decay.

The actual validated prefix built one recipe and complete-state anchor. A checked
retained scratch NPZ, outside inventory, supplied two independently constructed
and restored siblings. Each executed the existing three-call trial: 100-ms black
prelude, 100-ms visual, 200-ms black tail. Both started at 208000, reached CS onset
209000 and ended at **212000**. Each 0–100-ms MBON11 window measured 1 spike across
2 cells, or 5 Hz; these are telemetry observations, with no endpoint classification.

Sealed inventory has three actual ingested, typed checkpoints: `brain-before.npz`
at 0, `training-end.npz` at 111000 and `brain-after.npz` at sibling B's 212000.
Exactly **59 events**: 32 observe, 20 neutral-gap, 3 checkpoint, 1 direct fork,
2 anchor-parent branch starts and 1 anchor. Pre-seal prefix and separate sealed
verification each returned `native-replay` for the same nonempty singleton anchor.
They each reconstructed the 20-call black endpoint from the trained source;
training and sibling observations were checked directly, not replayed by these
verifiers. Ordinary `verify_run` remained `integrity-only`.

## Measured costs

Seconds are `perf_counter` wall times. Observe totals cover actual native calls;
compute/kernel are distinct telemetry sums. Telemetry bytes are compact sorted
JSON without newline, including engine identity; compact retention events omit it.

| Phase | Calls | Observe wall s | Compute s | Kernel s | Telemetry bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 26 | 31.624033 | 31.583756 | 30.101513 | 994,708 |
| Source-to-anchor black | 20 | 79.548542 | 79.514040 | 78.147787 | 783,630 |
| A sibling | 3 | 3.236562 | 3.231727 | 3.175601 | 103,062 |
| B sibling | 3 | 3.252801 | 3.247648 | 3.191265 | 103,059 |
| Prefix replay black | 20 | 77.996189 | 77.961947 | 76.622466 | 783,637 |
| Sealed replay black | 20 | 76.278144 | 76.247978 | 74.982391 | 783,640 |

| Operation | Count | Wall seconds |
| --- | ---: | ---: |
| Factory, training / retention / A / B / prefix / sealed | 6 | 5.496828 / 2.958739 / 2.817611 / 2.832059 / 2.899987 / 3.111090 |
| First identity/provenance lock | 6 | 0.052873–0.056771 |
| Complete native state digest | 9 | 0.112698–0.118182 |
| Candidate + noncandidate digest | 62 | 0.153038–0.170299 |
| Production `_check_engine` | 61 | 0.157740–0.185010 |
| Native NPZ write / restore | 4 / 5 | 1.279729–1.440289 / 0.245242–0.261398 |
| Checkpoint ingest/copy/hash | 3 | 0.010599–0.012475 |
| Generic observe / compact black append | 32 / 20 | 0.004423–0.006497 / 0.000171–0.000251 |
| Explicitly timed prefix validation | 3 | 0.253210–0.362215 |
| Exhaust prefix events + build recipe / build anchor / append anchor | 1 each | 0.234795 / 0.005524 / 0.160504 |
| Retained archive state/array authentication | 1 | 0.341648 |
| Entire native prefix / sealed verification | 1 each | 82.445835 / 81.125468 |
| Close/seal / ordinary sealed integrity check | 1 each | 0.023005 / 0.205764 |

Observe excludes subsequent production checks and telemetry-file serialization.
Production checks contain candidate-digest timers; whole verification includes
factory/restore/observe/digest timings and instrumentation. Do not sum nested
sections. One additional scratch-membership prefix check ran without its own
wall timer. Individual 500-ms producer retention calls took 2.586086–4.401760 s;
this evolved state has different costs from the earlier short-state component
sample. No component multiplication is used as a whole-assay ETA.

## Bytes and process scope

| Item | File bytes | ZIP entries compressed / uncompressed bytes |
| --- | ---: | ---: |
| `brain-before.npz` | 5,092,301 | 5,089,269 / 126,402,868 |
| `training-end.npz` | 6,803,568 | 6,800,536 / 126,402,912 |
| `brain-after.npz` | 6,901,907 | 6,898,875 / 126,402,916 |
| Retained scratch NPZ, removed after siblings | 6,865,351 | 6,862,319 / 126,402,916 |
| Sealed events, 59 | 1,278,871 | — |
| Three durable inventory files, total | 18,797,776 | — |
| Dedicated output, largest boundary sample / final | 47,724,285 / 42,506,421 | — |
| Fresh process working set / prior lifetime peak | 23,359,488 / 23,359,488 | — |
| Process lifetime peak / final working set | 1,274,982,400 / 729,255,936 | — |

Windows `GetProcessMemoryInfo` measures this Python process, baseline before
NumPy/project imports. OS-maintained peak includes imports, factories, checks,
checkpoints, responses and replay; children and OS-wide memory are excluded.
Each engine was released and collected before the next factory, with maximum
live-engine count 1. Allocator/cache memory remained; concurrency and cold
preparation/compilation were not characterized.

Disk samples include sealed files, all 92 telemetry files and three persistent
scratch checkpoint copies. Only the authenticated retained scratch NPZ was
removed. Boundary sampling misses transient NPZ partial/ingest/manifest copies;
prepared graph, caches, prior archives, probe/raw/log and filesystem overhead
are excluded. ZIP entry sizes include NPY headers. Neither measurement is an
upper bound.

## Provenance and next gate

Before/after hashes matched all 29 package `.py`/`.cpp` files and the schema.
Manifest hashes below use compact sorted JSON of relative source paths with
their hashes and byte sizes. Local probe/raw artifacts remain ignored.

| SHA-256 binding | Value |
| --- | --- |
| Source + schema manifest, before = after | `2caef22e3193028f9766e2c98b97ef8faec5651ef4ddf71cdc8e289a677940e9` |
| Schema | `1248e4002f5566886f7871c2d7ed7a1a80e4d25670c779796a11fab02bbb239e` |
| Engine identity | `96ca50c06f255cd02aab11b990511316c6953f873d418e774499807955f06db3` |
| Native binary / kernel source | `21c03b93e5afee5e630ceaf9fbe6805286e84a3653abefa1de18a6b2b583e0f1` / `e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509` |
| Trained source NPZ / complete source state | `a5c7a3fd988972e434f5f24ba5256b9a8252213d6ee74c88a90308a285302790` / `dc20d052fb75cb5b5c25d5a7f3150cf63530cb0b5f84f0ce42c2e5d81527c1bd` |
| Retained complete state | `19a5fb8ba571c29be6d8dd7496930955450cbf86d1f3c031817ac8b9f367db74` |
| Replay recipe / anchor envelope | `a994b594774787b54e10e0a23b4ea1a3e127ab2fdb5b2863a02ab3c604bff358` / `55706ad7e1cf71693dd0e4aafc6dec489dd7535333abc35add8119578195cc0c` |
| Final scientific chain / raw events | `e7f57f62794812303ebc4121b4446f150faca3a3e32ad9fc6dfeb3b7e8b1f564` / `9871687b1e6c9f3702963db6f3662b47475ae7de33777eaa5f1064c8b7a469b1` |
| Sealed manifest | `3913b2e25da1882d07c2c4a4880c2c1e976195ce57437101e9f02873ccd7c93e` |
| Probe / local raw summary | `063963c5ebd9ba2fb5a4da3e309a3e9ed1aca5303a1e645f2db729745d3e6fa5` / `5b197c4d78e10091cc264e679cbb789c98251ead89ad3d77f981d502312fe4bc` |

Native identity records Zig 0.16.0, `memory.dll`, model
`stonkfly-dual-compartment-v1`, eta 0.001 and flags `-O3`, `-std=c++17`, `-shared`,
`-Wl,--export-all-symbols`; it binds graph/configuration and ordered groups.

Next resource gate: a separately authorized, bounded one-anchor pilot for a
longer retained endpoint, measuring state-dependent black cost and both genuine
replay passes. This sample is not a long-trained or qualified population, an
all-factor/control assay, a biological/positive-plasticity claim or a behavior
certificate. Formal qualification and configuration freeze remain separate.
The fresh 346 recorder/replay checks preceded this probe; historical 1,299-case
acceptance is unchanged. No full suite or all-factor assay was repeated here.
