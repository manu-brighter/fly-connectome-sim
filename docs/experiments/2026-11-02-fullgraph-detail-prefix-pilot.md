# Fullgraph detail-on first-training-prefix pilot — 2026-11-02

One bounded Windows sample completed, exit **0**, on accepted c.2b source.
Independent measurement review found **0 Critical / 0 Important / 0 Minor**
findings and accepted publication within this scope. This establishes completion
of this instrumented resource sample, not scientific support, qualification,
production configuration or complete grid/assay capacity. Source and tests were
unchanged. Continue with bounded d/e/f implementation; integrated g remains open.

## Workload and authenticated boundary

Actual `FlyEngine.from_prepared_graph()` used MaleCNS v1.0: **166,700 neurons /
25,582,938 directed edges**, dt 0.1 ms. Existing production helpers executed
qualification configuration 0 (`cs_duration_ms=100`, `dan_onset_ms=-100`,
`post_pair_gap_ms=500`), seed 11, paired A/order AB, `controls=True`, with
`qualification_detail=True` and the default `pathway_detail=False`; qualification
detail also emits pathway telemetry. The route was baseline checkpoint,
independently restored pre A/B/C, independently restored pre-replay A, then paired
training through its actual checkpoint. Every black interval advanced using
explicit RGB uint8; reward-free calls disabled learning and external stimulation.

There were **38 calls / 1,270 detailed bins / 127,000 aggregate scheduled ticks**:
twelve 100-ms, five 200-ms and twenty-one 500-ms calls. Aggregate time crosses
restored branches; the final physical clock was **111,000 ticks**, with association
reference **109,000**. Durable evidence contains **45 events**: 38 observations,
five restores, two checkpoints. It has no binding, points, terminal, seal or
`run.json`.

Two genuine engines were constructed sequentially: producer released before fresh
native prefix verification, verifier released before engine-free reduction.
Maximum live engines was one; both release boundaries recorded zero. The verifier
returned `native-replay` with **zero attested anchors**: map/content authentication,
not training replay. Reduction returned **inconclusive**, `grid_incomplete`, one
evidenced unit, zero points and no selection.

Each raw call contained 4,184 MBON11 candidate edges, 3,623 candidate KCs and
17 circuit DANs. Authenticated MBON11/MBON07 target sizes were 2/4; MBON07 had
3,651 candidate edges / 1,875 candidate KCs. The final call's **last bin** contained
three nonzero KC and two nonzero DAN trace entries; this is model-state telemetry.

## Measured resources and timing limits

Unchanged stop criteria were **1,800 s wall / 8 GiB dedicated output and scratch /
4 GiB current or process-lifetime peak working set**. Preflight required
20 GiB free disk and 8 GiB available host RAM; actual values were
948,664,508,416 / 54,103,097,344 bytes. All 112 recorded boundaries passed.
Guards cannot interrupt individual allocations, native calls or scans.

| Measurement | Actual value / boundary |
| --- | ---: |
| Final resource-sample elapsed wall | 630.5461221000005 s |
| Event file | 31,313,620 bytes |
| Largest complete canonical line, including LF | 1,121,811 bytes |
| Durable checkpoints / additional scratch copies | 11,895,963 / 11,895,963 bytes |
| Dedicated directory at final resource sample | 55,267,543 bytes |
| Dedicated directory after final report write, console | 55,268,419 bytes |
| Final working set / lifetime peak working set | 591,233,024 / 1,089,613,824 bytes |
| Final private usage / peak pagefile usage | 1,825,792,000 / 2,302,390,272 bytes |

Final counters were read sequentially after the preceding report write, before
persisting the final sample. Subsequent metadata writing, stdout and exit are
excluded: **630.546 s is not an exact exit time or exit memory peak**. Disk samples
miss transient copies and exclude shared prepared/native caches and filesystem
overhead. Production helpers temporarily retain their own raw records; this route
does not bound complete retained-history memory. Existing DLL cache matched
before/after; OS cache state was neither controlled nor measured.

Phase bodies exclude stage-boundary monitoring/report writes but include per-call
guards. Exact wall/process-CPU nanoseconds from the report:

| Phase | Wall ns | Process CPU ns |
| --- | ---: | ---: |
| Producer factory | 6,158,817,700 | 6,796,875,000 |
| First-training-prefix production | 138,176,220,900 | 137,609,375,000 |
| Ordinary prefix validation | 153,580,475,200 | 152,765,625,000 |
| Fresh native context verification | 159,861,189,600 | 159,468,750,000 |
| Engine-free reduction | 170,166,544,000 | 169,640,625,000 |

Nested function timers overlap and are nonadditive; CPU excludes compiler
children. The global profiler dispatched **1,617,776,145 events**, selecting
**2,934**. Its **497,676,600 ns** callback wall measurement covers selected bodies
only, excluding dispatch/filter and untracked overhead. These are instrumented
durations: never subtract that partial overhead, infer unprofiled throughput or
linearly project capacity. A controlled **unprofiled** follow-up with coarse
phase wall/CPU and boundary resource measurements is mandatory before runtime,
optimization or capacity decisions; include it in integrated g. No storage
redesign follows from this sample.

## Identities and local evidence

Windows 11 10.0.26200 AMD64, Python 3.12.14; Zig 0.16.0 `memory.dll`, flags
`-O3 -std=c++17 -shared -Wl,--export-all-symbols`. SHA256 values:

| Object | Identity |
| --- | --- |
| Measured commit | `21f788342b276e1d8a323f572e37e248542948d6` |
| Model-source/v1 | `64041111c7cf3edfaf51128e071b79d939875937f810790c00d1425458c6e60e` |
| Run schema | `c56a64f91bf08b2f3c379a4720d4be3a5c2d1743c1c09394d2483f23d61af115` |
| Native binary | `21c03b93e5afee5e630ceaf9fbe6805286e84a3653abefa1de18a6b2b583e0f1` |
| Native kernel source | `e2d4d584f4633613277bb1bf6ea7ba20855c01a332ae2e9344ed7782604c8509` |
| Prepared graph, 250,157,214 bytes | `f4d41f011e97e510761d011634891b1c082f61f91463eb586ee9cf8c6371b1d1` |
| Engine identity, fly-engine/v1 | `e296cea3f9f320c588c146dd1e16f91ba3c86c92ec8b9590ded89883885ceebd` |
| Private driver | `39c5bd13c39fc1d64fbde5c67adde827ba93f0ad17bbbc46ba54063c630496d4` |
| Resource report | `4cdd1aaf18231575460f33b29ffe0b8f41d2cf1e058a3fb4cf719cad291c00ce` |
| Events file | `eb5c317544b276b5d1c40430df62de3e821536bbc5a87782d3befc1e9674a90e` |
| Final scientific chain, sequence 44 | `b154c515cbfe6853f3e02164a91738a37f0b2faa9cd6789a8879fd0df50a61e9` |
| Baseline NPZ, 5,092,351 bytes, sequence 0/tick 0 | `bba46777f4815e621d061cd89eecc25f0df5cbf0975dd54d04ce02eec4d9bd77` |
| Trained NPZ, 6,803,612 bytes, sequence 44/tick 111000 | `b894f900fa143dbed2d39f3f81de925f3bf81ab0735a5fbcde883466b7996f07` |
| Black input | `3973486a8ceb512b174a458a86d3fe966c1f88caed8d3f3a8d39047b06f6d4d9` |
| Seed 11 A / B / C inputs | `13892cf9c65312e77377bffd6739dc221aaf55753a54f9c0cd937d44ae563bc8` / `4b0059de4ebd0755a982a8c8f89a62bf44c828ef41ab5da4e60d425605ecf072` / `1008b8ec97de35444367bf350ab2537c897f1ebc01ab08216cb99a1fc5d2a126` |

Actual invocation, operator-recorded from the execution tool history:

```powershell
& .venv/Scripts/python.exe -B .tools/task7b4-fullgraph-detail-pilot.py --execute --expected-head 21f788342b276e1d8a323f572e37e248542948d6 --expected-driver-sha256 39c5bd13c39fc1d64fbde5c67adde827ba93f0ad17bbbc46ba54063c630496d4 --output-dir .tools/task7b4-detail-pilot-20261102-r1 > .tools/task7b4-detail-pilot-20261102-r1.console.log 2>&1
```

Raw events/checkpoints/report, console and private driver/audit remain local-only
under `.tools/`; they are absent from a fresh checkout. An independent
scalar/file audit passed source-member/event/checkpoint hashes and counts;
independent review also inspected original events and NPZ headers. Neither
reissued native proof. This publication does not enable cloud re-verification
without original bytes. Later source changes make it historical evidence.
