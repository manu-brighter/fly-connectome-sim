# Fullgraph longer-retention resource pilot — 2026-11-01

One predeclared 70-second retention sample completed with two independent A/B
siblings and both genuine isolated native replay passes. This measures a bounded
assay-style workload; it does not qualify settings, demonstrate learning or
establish whole-assay capacity. Package source, tests, dependencies and schema
were unchanged.

Measured commit: `460f5b046e4e18df2d147c18ba73899ac660032a`. Exactly one primary
run, no failed native attempt or repeat: 2026-11-01 15:19:05–15:57:12 UTC.
Process work through the final sample, before output-manifest hashing and raw
summary serialization/write, took **2,287.328442 s**. A predeclared one-hour
process-work guard checked native-call boundaries; it did not fire or interrupt
native calls/archive writes. This is an operational guard, not a scientific setting.

Windows 11 10.0.26200 AMD64, Python 3.12.14, NumPy 2.4.6, 24 logical processors;
Zig 0.16.0, `memory.dll`, C++17 `-O3 -shared -Wl,--export-all-symbols`.
Six sequential genuine `FlyEngine.from_prepared_graph()` factories each used
166,700 cells / 25,582,938 directed edges, dt 0.1 ms. Identities and ordered
groups matched: PAM11 15, PPL101 2, KC 4,064, MBON07 4, MBON11 2, motor-left/right
1 each. Every previous engine was released/collected before the next factory;
the maximum sampled live-engine count was 1.

## Executed workload and verification

Fresh baseline tick 0; qualification-family seed 11, 32×32 center/fixed A/B and
explicit same-shape black RGB uint8. Diagnostic `GridConfiguration(100.0, 0.0,
500.0)`, paired A/order AB, `controls=True`: all 26 training segments ran.
Learning matched `segment.start_ms < t0 and bool(stimulus or stimulation)`;
PPL101 stimulation was 100 ms at 20 mV. Black segments advanced too. Both detail
flags were False throughout, matching the assay-style call path; the older
qualifier's detail-enabled path and complete formal qualification were not measured.

Association/retention reference **109000** and schedule-complete source
**111000** ticks remained distinct. The 70,000-ms horizon was declared before
execution as the previous sample's T + 60 seconds, without selecting a grid point
from outcomes. CS onset was **809000**, anchor **808000**. Actual source-to-anchor
black time was **697000 ticks / 69,700 ms**: 139 calls of 500 ms plus 200 ms.
Retention and tests used learning False, stimulation None, current 20 mV,
weights unfrozen and normal passive decay; no implicit thaw occurred.

The genuine completed prefix had 169 events, final sequence 168. Its recipe
contained one direct fork plus 140 black operations and bound the actual source
occurrence at sequence 27. One complete-state anchor, `retention/70000`, was
appended. A retained scratch NPZ outside inventory was checked against native
state/tick and every numeric array before two fresh, independently restored A/B
siblings. Each executed the existing 100-ms black prelude / 100-ms CS / 200-ms
black tail: start 808000, onset 809000, window 809000..810000, end 812000. Each window
contained 7 MBON11 spikes across 2 cells, or 35 Hz; this is unclassified telemetry.
Only that checked retained scratch archive was removed after both siblings.

The sealed pilot has exactly **179 events**: 32 observe, 140 compact neutral-gap,
3 checkpoint, 1 fork, 2 anchor-only branch starts and 1 anchor. Durable checkpoint
occurrences are sequence 0/tick 0, sequence 27/tick 111000 and sequence 178/tick 812000;
the last archive is the actual B endpoint. Inventory contains exactly three files.
Actual observations total **452 = 26 + 140 + 3 + 3 + 140 + 140**.

Both genuine public prefix/sealed native verifiers returned `native-replay` and
the same nonempty singleton anchor. Ordinary prefix/read verification remained
`integrity-only`. Each replay reconstructed only the 140-call black endpoint from
the trained source; it did not authenticate training or sibling history by replay.
Executed training/sibling flags, input hashes, state and clocks were checked
separately. Full original/prefix/sealed black telemetry matched across all 140
calls after excluding only `compute_seconds` and `kernel_seconds`, without another
native run. Complete telemetry files remain in ignored local evidence.

## Measured costs

All wall times use `perf_counter`. Telemetry bytes are compact sorted JSON without
newline; compute/kernel are separate telemetry sums.

| Phase | Calls | Observe wall s | Compute s | Kernel s | Telemetry bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 26 | 30.125222 | 30.075148 | 28.003949 | 994,711 |
| Source-to-anchor black | 140 | 667.366738 | 667.072310 | 654.136546 | 5,510,209 |
| A sibling | 3 | 4.249850 | 4.243594 | 4.163349 | 103,063 |
| B sibling | 3 | 3.509698 | 3.503971 | 3.437046 | 103,058 |
| Prefix replay black | 140 | 617.389001 | 617.114322 | 605.360093 | 5,510,193 |
| Sealed replay black | 140 | 631.253591 | 630.986329 | 618.666638 | 5,510,199 |

| Operation | Count | Wall seconds |
| --- | ---: | ---: |
| Factory: training / retention / A / B / prefix / sealed | 6 | 3.764976 / 3.535177 / 3.353605 / 3.420713 / 3.425019 / 2.942807 |
| Initial identity/provenance lock | 6 | 0.063570–0.072685 |
| Complete native state digest | 9 | 0.130259–0.143805 |
| Candidate + noncandidate digest | 182 | 0.167950–0.229745 |
| Production `_check_engine` | 181 | 0.186333–0.512837 |
| Native NPZ write / restore | 4 / 5 | 1.508007–1.619852 / 0.278024–0.328914 |
| Checkpoint ingest/copy/hash | 3 | 0.015407–0.019266 |
| Observe / compact black append | 32 / 140 | 0.004604–0.009556 / 0.000179–0.000340 |
| Source / anchor / pre-seal prefix validation | 3 | 0.340257 / 0.315400 / 0.471129 |
| Extra scratch-membership prefix validation | 1 | 0.455785 |
| Exhaust source events / exhaust anchor events + build recipe | 1 each | 0.185297 / 0.295140 |
| Build / append anchor | 1 each | 0.010866 / 0.197575 |
| Retained archive state/array authentication | 1 | 0.403515 |
| Entire native prefix / sealed verifier | 1 each | 683.137087 / 732.934150 |
| Close/seal / ordinary sealed integrity check / exhaust sealed events | 1 each | 0.026631 / 0.258206 / 0.349477 |

Observe wall excludes subsequent production checks and telemetry-file writing.
Checks contain candidate-digest timers; full verifiers contain factory, restore,
observe, digest and instrumentation costs. Boundary file/memory sampling and
telemetry serialization add measurement overhead, including growing file scans.
Timers overlap: do not sum nested sections or derive exclusive costs by subtraction.
Individual 500-ms producer retention calls ranged **3.238430–5.870793 s**;
prefix/sealed ranges were 3.212480–5.490729 / 2.773464–5.429606 s.

## Storage and memory scope

| Item | File bytes | ZIP entries compressed / uncompressed bytes |
| --- | ---: | ---: |
| `brain-before.npz` | 5,092,301 | 5,089,269 / 126,402,868 |
| `training-end.npz` | 6,803,568 | 6,800,536 / 126,402,912 |
| `brain-after.npz` | 6,908,623 | 6,905,591 / 126,402,916 |
| Retained scratch NPZ, removed | 6,860,877 | 6,857,845 / 126,402,916 |
| Three durable inventory files, total | 18,804,492 | — |
| Sealed events / manifest | 1,410,186 / 121,649 | — |
| 140 compact black events, canonical JSON without newlines | 104,649 | — |
| Dedicated output, largest boundary / final | 56,872,704 / 56,872,704 | — |
| Fresh working set / lifetime peak at baseline | 22,482,944 / 22,482,944 | — |
| Lifetime peak observed through final sample / final working set | 1,315,819,520 / 878,223,360 | — |

Windows `GetProcessMemoryInfo` covers this Python process, starting before NumPy/
project imports. The reported OS-maintained lifetime peak is observed through the
final sample after native execution and telemetry comparison, not through process
exit. Subsequent output-manifest hashing, raw-summary serialization/write and exit
are outside that final sample. Children and OS-wide memory are excluded. Cached
allocations remain; cold-cache preparation/compilation and concurrency were not tested.

Disk boundaries include the sealed run, 452 telemetry files and three persistent
scratch checkpoint copies: 460 final regular files. They miss transient NPZ partial,
ingest/manifest temporary peaks. Prepared graph/native caches, pre-existing archives,
probe, raw summary (23,696,818 bytes), log and filesystem overhead are excluded.
ZIP sizes include NPY headers. Boundary maxima are observations, not upper bounds.

## Bindings and interpretation

Before/after hashes and sizes matched all 29 package `.py`/`.cpp` files and schema.
The source manifest uses compact sorted JSON of relative paths, hashes and sizes;
it matches the previous pilot. Probe/raw/native artifacts remain ignored.

| SHA-256 binding | Value |
| --- | --- |
| Source + schema manifest, before = after | `2caef22e3193028f9766e2c98b97ef8faec5651ef4ddf71cdc8e289a677940e9` |
| Schema | `1248e4002f5566886f7871c2d7ed7a1a80e4d25670c779796a11fab02bbb239e` |
| Engine identity | `96ca50c06f255cd02aab11b990511316c6953f873d418e774499807955f06db3` |
| Native binary / kernel source | `21c03b93e5afee5e630ceaf9fbe6805286e84a3653abefa1de18a6b2b583e0f1` / `e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509` |
| Before / trained / after durable NPZ | `6e631283a1265b0718357a5d024f5ec1bf4192e14f37bba6a42bd898cf365e13` / `a5c7a3fd988972e434f5f24ba5256b9a8252213d6ee74c88a90308a285302790` / `c652e7b82b41cc976a406831c77d557532a62369fee488d6ad0d5e1c0cd9dd08` |
| Complete trained / retained state | `dc20d052fb75cb5b5c25d5a7f3150cf63530cb0b5f84f0ce42c2e5d81527c1bd` / `52daeec17e8cc4d8eee008cfb47d514d46bed4b4e1bca0dc7af8e217cb8045e1` |
| Retained scratch NPZ | `533e3014522f5b36df7fb328cf1717f10da6e43fc33354ad75d6e09d2668d6d8` |
| Run metadata / scientific prefix at anchor | `6ea3cce826d0a92652166dae2c830800dc8ac0059899670eb14556d0a1be60b6` / `5530e7f96c07ccbeeb58601336d6381dbc0f53e5ab10077e76c2bb1ae6c9f47b` |
| Replay recipe / anchor envelope | `bcf075821fc9ec7b6e4eb8ea0c4cdfd9b87dc842ddd6e8813f5fb4a95ef42de6` / `42263f4caa52c3a6f665ee551954564d50d7870d759573552bc095de1a08d9a2` |
| Final scientific chain / raw events | `370e4e8ba38b7c53f7d53a67c5aa3b2fc5b44d15873f9881bdcd8c04a2610104` / `58fdbe10b837bd0d589bc0d841cbfebd822636d951493428d2520273207dc992` |
| Sealed manifest / three-pass timing-stripped telemetry sequence | `6c84abbac53a4438448e223fda777b7a2c1002622a23207fc28ddd108922c0b0` / `218c544c2297e7580f15b7a7b1d74c877a72579992aed91d420da54beabc16b8` |
| Probe / local raw summary | `0ef233f9eb42b79fda8f062b2e70a0878f644d243784129f31c163bd4ab77988` / `60608fb6ebf602f541851376ba4978c8be4422fc23b2b8758a4b55944641a300` |

Compared with the [10-second pilot](2026-10-08-fullgraph-anchor-pilot.md), actual
black calls per pass increased 20 → 140, total calls 92 → 452 and events 59 → 179.
Entire prefix/sealed verifier times were 82.445835/81.125468 s there versus
683.137087/732.934150 s here; sampled lifetime peak was 1,274,982,400 versus
1,315,819,520 bytes, dedicated boundary maximum 47,724,285 versus 56,872,704 bytes.
These are two local samples with different retained states/work and instrumentation
burden, not an isolated causal estimate or linear whole-assay extrapolation.

The longer retained endpoint resource gate now has one actual Windows sample.
Remaining work includes selected control/intervention evidence and strict CLI/
configuration integration, discarded-training ancestry/storage decisions and the
separate motor adapter before source freeze/formal qualification. Complete
qualification costs, whole-assay capacity, cloud/Linux execution, positive
plasticity, valence, behavior, dopamine concentration and receptor activity remain
unestablished. No scientific setting was selected from these telemetry outcomes.
Fresh root-owned focused baseline: 380 passed, 1 Windows junction-permission skip
in 57.23 s. Historical 1,299-case acceptance was not rerun; no full suite or
all-factor assay ran for this source-unchanged measurement.
