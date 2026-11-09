# Activity-balanced rearm v2 — software and negative development result

Status: source and actual offline development replay independently accepted.
The fixed candidate produced **no improvement** on the accepted 96-second
recording: zero additional balanced releases and zero drink/price proposals.
There was no new neural acquisition, training or provider request. Stage B remains
open; this result does not justify another native run merely to repeat the test.

## Prospective candidate and implementation

The [separate spec](../superpowers/specs/2026-11-09-balanced-motor-rearm.md) and
[plan](../superpowers/plans/2026-11-09-balanced-motor-rearm.md) were independently
accepted and published before implementation as
`5a30762648ec52f03056eba1ff652ac206ade90e`.
[CI42684069257](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42684069257)
passed 665 backend tests /41 declared skips in310.10s,243 viewer tests /four
private-artifact skips and build. That checkpoint contains the prospective docs,
not the subsequent v2 source.

The new external `MotorReadoutV2` subclasses the frozen v1 decoder. It retains
quiet rearm and adds four non-overlapping waiting observations, combined count
at least20, each satisfying `10*abs(R-L) <= L+R`. Quiet release has precedence;
release evidence cannot also support the next direction or price. Existing
ordering, typed count validation, freshness, expiry, routes and price mapping
remain inherited. All complete rearm blocks receive aggregate validation first.
No old source, global policy or native integration was changed.

The10% band was fixed prospectively as an engineering choice, not fitted by
searching this trace. Activity is required across the block; individual zero/zero
observations are permitted. This is not biological neutrality or calibrated
confidence. It does not correct the observed left/right activity bias.

## Synthetic software evidence

The initial absent-source RED produced89 explicit fixture errors in1.69s, each
asserting that the new module was missing. These were not89 failing behavior
assertions against an implementation. First GREEN:187 passed in0.47s. Additional
boundary/price/ordering cases yielded **199 passed in0.52s, zero skips**:
101 new cases plus the unchanged98 v1 cases.

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_market_motor_readout_v2.py tests/test_market_motor_readout.py
```

Coverage includes quiet and balanced releases, exact total/band boundaries,
interleaved zero observations, fourth-sample quiet precedence, cancellation of
opposite strong signals, fixed block alignment, quiet streak across a failed
block, disjoint support, all20 literal routes and all seven fixture price targets,
symmetry, lifecycle/source/freshness/order failures, overflow, expiry and v2
identity on successful/failed reconfiguration. Full post-anchor raw history may
contain releases; subsequent decision support cannot reuse them.

The worker compared105 existing tracked source/helper/core/lock files before and
after implementation: all byte-identical. Historical recordings were not opened
by the implementer. Astra independently accepted the actual source, tests, logs,
hashes and preservation evidence with no blocking finding. The only CI source
change adds the new test filename. Logs and inventory are local under
`.tools/balanced-motor-implementation-20261109/`.

## One fixed development replay

After source acceptance, the controller froze the concrete configuration,
source/helper hashes and ten original acquisition/supervision artifact identities.
Astra independently accepted that preflight and exact command before execution:

```powershell
.venv/Scripts/python.exe .tools/balanced-motor-controller-20261109/development-replay.py run 72d0eec965ad3e6436146856d953ca5c3d5ecad8ba0c63c1846dc3f8143aa308
```

One controller invocation exited0 in approximately3.06s. The guarded script
first reproduces the accepted v1 inspection, then consumes all192 original
samples with their original `readout_now_ms` values. Native model loading,
network and child process starts are rejected during execution. Candidate output
is separate under `.tools/balanced-motor-rearm-20261109/`; no original summary,
receipt or measurement is replaced. No window selection, altered clocks,
threshold sweep, reset or neural execution occurred.

| Result | v1 baseline | v2 development replay |
| --- | --- | --- |
| Initial quiet release | indices0–1 | indices0–1 |
| Additional balanced release | not part of v1 | 0 |
| Supported direction | lower, indices6–9, L44/R17 | identical |
| Partial route expiry | one at observation77 | identical |
| Complete proposals / selected drinks / prices | 0 | 0 |
| Waiting observations | 182 | 182 |

All192 five-field results are exactly equal between versions, not merely the
aggregate counts. Both report six collecting observations, one unsupported
direction block, one ready state, one supported lower decision and one expiry.
The final v2 state waits for release in direction phase `[0,20)`, with no pending
decision or selected path; its incomplete balance block contains indices190–191.
Every one of the20 drink proposal counts is zero. The trace retains every original
sample, clock, baseline result and candidate result, including unsuccessful cases.

Astra independently reproduced all192 candidate results and checked complete
trace/configuration/source identities, release/support/expiry/final-state details,
the ten original artifacts and historical source/result preservation. This is an
accepted **negative development replay**, not held-out confirmation. The candidate
was motivated by this recording; no new biological or native behavior was measured.

## Frozen identities

| Item | SHA256 |
| --- | --- |
| v2 source | `878b6a4d16c824727ac78edd68cb5e44da11445a0889e7b8a35e960b0f94bf69` |
| v2 tests | `88fc6cbfa0eaefb9c451574be4c9018c8b4576a7a38ba765bef5d01baba424b5` |
| Replay helper | `e8badc40673de95c315c3d03ee815284fdc508a3d669599bf0b2d1a150ed4edd` |
| Preflight | `72d0eec965ad3e6436146856d953ca5c3d5ecad8ba0c63c1846dc3f8143aa308` |
| v2 configuration | `e0850a54139afcc685a0c80f8a42accec4e5da433de3183a43cb9b2a7d2387ca` |
| Complete candidate trace | `24ac7009f33053a6df22b766dab10f6a212708d2e65319a491d4b44a45ebddda` |
| Development summary | `f6c13abd0faca0537cecf5e5af6feb5940b5a048db5ce615713c042a95537d3b` |

The original [native v1 negative result](2026-11-09-continuous-motor-probe.md)
and all its artifact identities remain unchanged. The package fingerprint remains
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.

## Technical decision

Source/result checkpoint `c73fa83384f698c4793a7b32d5ab84c1251f2a67` passed
[CI42686215403](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42686215403):
766 backend tests /41 skips in320.85s,243 viewer tests /four skips and build.

Retain this unsuccessful candidate and stop local cutoff/rearm iteration here.
There is no evidence-based reason to acquire another native run solely to try
this same candidate again. Neither synthetic route coverage nor the preserved
negative outcomes establish a usable20-drink controller, and neither proves that
every possible neural readout must fail. Further implementation requires a
distinct, justified design question, not another retrospective cutoff adjustment.
No automatic v3, Stage C, native acquisition or price activation follows.
