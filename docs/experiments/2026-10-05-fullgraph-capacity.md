# Bounded fullgraph capacity measurement — 2026-10-05

The native fullgraph components completed this local sample with deterministic
restores and repeats. This supports a bounded recorder/replay pilot next; it does
not establish whole-assay runtime, capacity or scientific qualification.

Measured commit: `5aaffb71f1fc261025d8cd82f2f0d45a85d0ec39`. One opt-in
throwaway probe ran at 13:18:05–13:18:26 UTC on Windows 11 10.0.26200 AMD64,
Python 3.12.14, NumPy 2.4.6, with 24 logical processors. It used the actual prepared
graph and C++ kernel: **166,700 neurons, 25,582,938 edges**, timestep 0.1 ms.
Source/dependencies/schemas and scientific gates were unchanged. Probe/raw
artifacts remain local; there is no new public command.

Two independent factories ran sequentially in one fresh Python process, releasing
the first engine before constructing the second. Disk/native build caches were
warm; cold preparation, compilation and concurrent engines were not measured.
Both identities and ordered groups matched: PAM11 15, PPL101 2, KC 4,064,
MBON07 4, MBON11 2, motor-left 1, motor-right 1.

## Components

Times are `perf_counter` wall seconds. Pairs give individual first/second values;
ranges cover the stated count. Factory/identity are timed separately. Archive
authentication includes loading, complete-state hashing and live-array byte equality.

| Component | Count | Seconds |
| --- | ---: | ---: |
| Fullgraph factory | 2 | 2.982168 / 2.832058 |
| Identity/provenance lock | 2 | 0.052818 / 0.052771 |
| Complete native state digest | 22 | 0.112602–0.121453 |
| Candidate + noncandidate digest | 4 | 0.153716–0.155045 |
| Source NPZ restore | 10 | 0.235902–0.252650 |
| Source archive authentication | 2 | 0.320324 / 0.320526 |
| Local compressed NPZ write | 2 | 1.377603 / 1.384085 |
| Local NPZ restore | 2 | 0.237521 / 0.242367 |
| Raw checkpoint file SHA-256 | 2 | 0.005199 / 0.005457 |

The source is the evolved 100-ms checkpoint from the current-source fullgraph
integration test, at tick 1,000: a short stimulated state, not long-trained
retention. Before **each** observation the source was restored and complete state
checked. Each condition ran twice, once per independent engine. All frames are
32×32 RGB `uint8`; A/B/C use `AssayStimuli(101, "confirmation")`, center/fixed
defaults. Calls match current `assay.call`: `learning=False`, `stimulation=None`,
`current_mv=20.0`, `pathway_detail=False`, `qualification_detail=False`. The source
was thawed; production thaw behavior was present but unexercised. These 100-ms
calls are illustrative components, not a scheduled frozen response window.

| Condition | Duration / exact advance | Wall s, first / second | Compute s, first / second | Kernel s, first / second | Telemetry JSON bytes |
| --- | --- | --- | --- | --- | ---: |
| Black | 500 ms / 5,000 ticks | 1.297331 / 1.359500 | 1.295793 / 1.357981 | 1.239215 / 1.296423 | 39,215 / 39,216 |
| A | 100 ms / 1,000 ticks | 0.272849 / 0.289507 | 0.271256 / 0.288011 | 0.259476 / 0.273101 | 33,875 / 33,875 |
| B | 100 ms / 1,000 ticks | 0.273480 / 0.285399 | 0.271921 / 0.283924 | 0.260170 / 0.271656 | 33,871 / 33,876 |
| C | 100 ms / 1,000 ticks | 0.272256 / 0.287336 | 0.270698 / 0.285841 | 0.258601 / 0.273544 | 33,876 / 33,875 |

JSON sizes include full telemetry/engine identity, compact sorted JSON without
newline. They are not recorder event sizes: compact black events omit telemetry.
Compute is the internal engine loop; wall includes surrounding `observe` work.

## State and resources

Validated source-archive state, both live restores, and both written/restored
checkpoints matched the complete source-state hash below. Both writes also
matched source file hash/size exactly. Repeated candidate digests left every live
array hash, scalar and array reference unchanged; complete hashes agreed
before/after. Each black/A/B/C pair matched the complete native endpoint digest
and **all telemetry fields**, excluding only top-level `compute_seconds` and
`kernel_seconds`. Independent post-run assertions rechecked raw telemetry
equality/hashes, ticks, scratch sizes and projection arithmetic. This does not
establish recorder/replay ancestry or qualification evidence.

| Resource | Bytes |
| --- | ---: |
| Source and each written NPZ including ZIP overhead | 6,573,159 |
| ZIP entries compressed / uncompressed, including NPY headers | 6,570,127 / 126,402,896 |
| Fresh process working set / prior lifetime peak, before NumPy/project imports | 25,272,320 / 26,148,864 |
| Working set after imports | 37,650,432 |
| Process lifetime peak working set | 1,065,197,568 |
| Final working set after engines released | 532,459,520 |
| Dedicated scratch files, maximum sampled at boundaries | 13,428,005 |

Windows `GetProcessMemoryInfo` supplies this Python process's current working set
and OS-maintained lifetime peak. Peak is about 1,015.9 MiB, or 1,039,925,248 bytes
above fresh current baseline; it includes imports, factories, archive validation,
digests/checkpoints and observations, not just graph allocation. Child processes
and OS-wide memory are excluded. Allocator/cache memory remains after release.

Scratch samples cover regular files in the dedicated output: two NPZs and eight
telemetry files, sampled around operations and after telemetry writes. They
exclude prepared graph, source checkpoint, native cache, probe/log/raw summary
and filesystem overhead. Temporary peaks between boundaries are unobserved;
this is not a filesystem or OS-wide high-water.

## Provenance

All hashes are SHA-256. Before/after hashes matched for all 29 package `.py`/`.cpp`
files and the source checkpoint. The manifest hashes compact sorted JSON of
repository-relative source paths and file hashes.

| Binding | SHA-256 |
| --- | --- |
| Engine identity | `96ca50c06f255cd02aab11b990511316c6953f873d418e774499807955f06db3` |
| Model source fingerprint | `a4dbf871ceb6b87b77eb796901611c7683adc10f75c99d6eeb0f2f7eb0674c6a` |
| Package manifest, before = after | `1d47ed03f49f10b2938b8b1481cf7e6e098699bbab2ceae9384cb8c9087a9fb0` |
| Kernel source | `e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509` |
| Native binary | `21c03b93e5afee5e630ceaf9fbe6805286e84a3653abefa1de18a6b2b583e0f1` |
| Source NPZ, before = after = local writes | `2f6600c4fcfca88ceb24a62606670e8d5a603dd3ff874a5198ba246721858e20` |
| Complete source state, before = after = restored writes | `9ff5ae2d803ae9b2e0b1414fd440a1de2e2cc47a659be5338b1d1f50b55cdbc4` |
| Candidate memory | `f2bcabac8723680a9bc7bafad44c21e3a2e537bc90431e53baba7f1784e627a5` |
| Noncandidate state | `49d56eb64c34e654cb9cd09bf4f8dc58dbb455a1cc87a64ad2f64a73101eeb8d` |
| Probe at measurement freeze | `d2f45a636ba2d3f53e47b887c5cd2e8b284cbb425256fbf98d0ca490601e4e98` |
| Local raw summary | `2dd156d3f6b9f78c6ace2f9419b0ebfe9a0810e866b5d8031eee7610aeecfc0f` |

Native build: Zig 0.16.0, flags `-O3`, `-std=c++17`, `-shared`,
`-Wl,--export-all-symbols`, library `memory.dll`; model
`stonkfly-dual-compartment-v1`, eta 0.001. Identity binds graph IDs/CSR,
configuration, ordered groups and native build.

| Frame | Input SHA-256 |
| --- | --- |
| Black | `3973486a8ceb512b174a458a86d3fe966c1f88caed8d3f3a8d39047b06f6d4d9` |
| A | `ed7cff77d7d92f27517380883e3703e7b594bbfab70e19fa3d5106877ec60f31` |
| B | `e7ed4018057711f198414cc9aa081533e40ec14fa321eb2bcd1ef780162d650b` |
| C | `46d38427c3a1ef4eac44b4832e2e69ed6cd6395543f5c1f2c46e3df0c7ef5712` |

## Illustrative scale and next gate

At this particular compressed size, 67 inventory files occupy **440,401,653
bytes** (about 420 MiB); adding 67 concurrent temporary copies gives
**880,803,306 bytes** (about 840 MiB). This excludes retained scratch, events,
graph/cache and filesystem overhead. Later learned states may compress
differently; neither figure is an upper bound or capacity certificate.

Pure component multiplication gives 625 producer factories including identity
locking × the measured pair = **1,803–1,897 seconds**. In the illustrative
T=10 s / T+60=70 s scenario, 64 route/cohort sources × (20+140) black calls gives
10,240 calls; multiplying only measured black `observe` wall range gives
**13,285–13,921 seconds**. These are partial projections from this short source,
not whole-assay ETAs; do not sum them into one. Unmeasured costs include training,
restores/digests/writes, response schedules, recorder/fsync, current prefix/anchor
validation, both native replay passes and scientific qualification. Repeated
black calls from later states were not measured. The old capacity map's nested
historical-scan hypothesis was superseded by shipped recorder changes.

Next gate: a separately authorized bounded native pilot with one real retained
anchor from a representative trained source, timing recorder validation, anchor,
retained checkpoint/sibling restore and prefix/sealed replay, with event
count/bytes and process/scratch peaks. Formal configuration freeze and scientific
qualification remain separate gates. Existing 1,299-test acceptance preceded
this documentation slice; no full suite or all-factor assay was repeated here.
