# Continuous motor drive — software and development replay

Status: source and complete actual replay independently accepted. This is
development feasibility, not held-out confirmation or a
price-service acceptance. Previous v1/v2 and population-screen negatives remain.

The [prospective contract](../superpowers/specs/2026-11-09-continuous-motor-drive.md)
was reviewed and published as `df42efb5e0ed192bbec61b63cf95b7d393e71f21` before
implementation. A separate direct v1 subclass starts ready and rearms after each
supported direction. It consumes new four-observation blocks for each node and a
separate price block. Thresholds, integer mapping, clocks and guards are unchanged.
Quiet recovery was a prior event-detector assumption; sustained supported activity
now means repeated engineered commands, not repeated biological intentions.

The prospective checkpoint passed
[CI42700745822](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42700745822):
932 backend tests /41 skips in549.90s,243 viewer tests /four skips and build.
This precedes the new source and is not its CI evidence.

The subsequent source/result checkpoint `979b67bbaf8529ad9de98ccfa45a415656b73756`
passed [CI42702799722](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42702799722):
1350 backend tests /41 skips in443.95s,243 viewer tests /four skips and build.
All418 new driver cases passed on Linux; local targeted verification is below.

## Software evidence

`scripts/market_continuous_drive.py` is43 lines/1718 bytes. The only CI change adds
`tests/test_market_continuous_drive.py` to the existing selected test command.
There are418 new synthetic cases and98 unchanged v1 cases: **516 passed in1.18s**,
zero skips or warnings. All110 inventoried old source/test/license/lock paths
remained byte-identical. No packaged Python/C++ source or old helper was changed.

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_market_continuous_drive.py tests/test_market_motor_readout.py
```

Tests construct every165 leaf across sizes10–20 at both price endpoints (330
cases), verify full disjoint evidence, repeated fresh commands, separate price
measurement, unsupported-block discard, exact boundaries/expiry, malformed/stale/
duplicate/order/source changes, valid frame switches, pause and configuration.
The128-history defensive guard is seeded in one explicit test because the normal
60-model-second expiry precedes it; this is not a naturally observed long path.
These tests establish technical reachability, not observed neural coverage.

Test history is retained: initial expected missing-module setup error included
two optional-cache permission warnings; the clean RED with cache disabled failed
the explicit missing-module assertion. First GREEN had494 passes and one wrong
test expectation:72 samples permit3, not4, complete20-sample commands. Correcting
that expectation and adding inherited validation cases produced the final516.
Production source remained unchanged after its first implementation.

## One fixed actual replay

After source acceptance, concrete preflight and exclusive output were independently
reviewed. One guarded offline invocation used all192 original samples and original
`readout_now_ms` from `runs/continuous-motor-20261109-01/`; first block0–3, no
alignment search or new neural execution. The accepted public inspector first
reproduced the complete original v1 summary. Four sources, seven recording files
and three supervision files remained pinned. Full trace and summary are local at
`.tools/continuous-drive-20261109/`; completed directories must not be reused.

Execution:2026-11-09 21:22:26.5203615–21:22:29.4863802 UTC,2.9660187s, exit0,
one invocation, empty stderr. No native simulation, training, provider request or
price activation occurred. This replay's wall time is not model throughput.

Astra independently reproduced all192 results and directly recomputed all48
blocks, including support, integer prices, time limits, disjoint evidence and
final pending state. All source/artifact bindings and110 old files matched.

Result: **8 complete proposals, all for `drink-00`**. All33 accepted directions
are lower; each completed route has four directions and a separate price block.
Observed coverage is1/20, alongside the separate all-configured-leaf synthetic
proof. The user explicitly accepts favorites and does not require finite all-drink
occurrence. No forced variety or fallback was added.

| Completion in original model time | Target CHF | Price block observations | Price L/R counts |
| --- | --- | --- | --- |
| 12s | 5.00 | 20–23 | 22 /14 |
| 22s | 4.50 | 40–43 | 46 /8 |
| 32s | 4.50 | 60–63 | 38 /7 |
| 46s | 4.50 | 88–91 | 54 /9 |
| 58s | 5.00 | 112–115 | 39 /16 |
| 70s | 5.00 | 136–139 | 47 /23 |
| 84s | 5.50 | 164–167 | 37 /28 |
| 94s | 4.50 | 184–187 | 44 /9 |

Status counts:144 collecting,7 unsupported-direction blocks,33 accepted directions,
8 proposals, zero resets. Failed blocks are0–3,64–67,68–71,92–95,116–119,140–143,
148–151. Each block is discarded;148–151 remains documented in the surrounding
proposal's input history without being reused as support. Final observations
188–191 select only the lower half `[0,10)` of a new path, not a ninth proposal.
The completed paths span10 or12 model seconds and80.235–101.016 original real
seconds. The complete actual trace retains all original clocks and provenance.

Target counts:450 Rappen four times,500 three times,550 once. There are seven
repeated-target proposals and five repeats of a previously seen target/price pair.
No minimum400 or maximum700 price was observed in this recording. These are
proposals, not sale-price changes; the later service still applies each drink's
30-real-minute cooldown, no-op rejection and pause, without queue or retargeting.

## Frozen identities and limits

| Item | SHA256 |
| --- | --- |
| New source | `7285c150d2ab14506c94d90d995da142e71eb1d29277f7b4d582b740c953e42d` |
| New tests | `04791ca1f9e9bd5388110ebf5090e1338721646bfcb2b5dc9d6470b7509f15bb` |
| Guarded local helper | `ea00ec6be34e49ba3599610b57ec87e97bbd6a8bdf594b8420810f8605052d1a` |
| Concrete preflight | `bb641f739d9a7e9bd019263438be00368d23217114cf18f0d5c0a1f8f4c64a9b` |
| Candidate configuration | `c02ca9be4db5198b46e718116ff80c169aa3d051f29ff7703d27f1f4fd5315c5` |
| Original manifest | `ed2e30e8afe83450cafe613df4d3158e8a256feb16a4c96fcc0faac0d3bd7bc8` |
| Original events | `4ea7ddf519fa22ee5158c763a45bd0639226f1235d3540bba11e0205a446395f` |
| Complete209367-byte trace | `fb1c0302c174bd2fd1090527430fdfc55fdc774e5b604231fccb4854e312a85f` |
| Complete83776-byte summary | `897693bdce9b0a34a90dcec8e6c08427229c98e8299f0d54d683c077649b0608` |

The recording motivated this new mapping, so the result is development evidence.
It does not establish that particular images caused the different prices, robust
image control, learned preference or autonomous biological timing. Held-out
functional output and controlled input sensitivity must be evaluated separately
from tonic activity/state history, under a new prospective protocol. Performance,
live display, service and event-rehearsal gates remain open; Stage C is not accepted.
