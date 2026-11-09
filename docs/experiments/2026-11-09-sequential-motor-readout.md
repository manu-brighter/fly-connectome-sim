# Sequential motor readout — offline software evidence

Status: implementation, synthetic tests and independent source review accepted;
publication/clean-checkout CI pending. No new neural acquisition or actual-price change.

The [candidate contract](../superpowers/specs/2026-11-09-sequential-motor-readout.md)
and [plan](../superpowers/plans/2026-11-09-sequential-motor-readout.md) define a
deterministic external decoder. Its input counts, identities and clocks in this
report's tests are synthetic. The earlier matched-state recordings are development
evidence, not held-out acceptance for this candidate.

## Implemented behavior

`scripts/market_motor_readout.py` consumes contiguous 500-ms observations.
Two low-activity observations arm a fresh four-observation decision block.
Sufficient supported left/right activity halves the ordered drink interval;
another neutral interval is required before each subsequent decision. After one
drink remains, a separate supported block maps the right/total count ratio onto
that drink's integer-Rappen grid using exact half-up rounding.

The decoder can abstain indefinitely. It never inserts a stimulus, invents a
neutral observation, schedules the engine or activates a price. A partial path
expires after 60 model seconds or 300 real seconds from its first supporting
sample's start. Old, malformed and discontinuous data cannot preserve partial
decision evidence. Ordering protection survives evidence resets. Freshness uses
delivery age after computation and does not claim a bound on uploaded-image age.

| Synthetic check | Observed software behavior |
| --- | --- |
| Twenty independently specified routes | Every stable drink ID is reachable with its literal binary route |
| Exact activity/net/sign thresholds | Boundaries accepted; silence, ties, alternating signs and weak activity defer |
| Separate price evidence | Supported endpoints reach CHF4 and CHF7; no per-change step cap; one spike cannot support a price |
| Integer arithmetic | Half-up grid rounding stays exact, including large valid integers; unsafe aggregate payloads fail closed |
| Rearm and non-overlap | Neutral samples do not enter decision blocks; sustained evidence alone cannot repeat decisions |
| Model and wall expiry | Exact boundaries expire; deferred blocks do not renew the anchor; an already-expired first block is rejected |
| Ordering and boundaries | Duplicates, rewinds, gaps, stale samples, source/session changes and pause/reset/config changes discard old evidence |
| Output/configuration ownership | Detached results and immutable policy binding; bounded pending/history buffers |

These are software properties, not measured neural reachability or validated
twenty-drink control. Fixed ordering and unequal route lengths can bias choices.
The proposed price has no authority; the future service must enforce durable
activation, freshness, deduplication and each drink's 30-real-minute lock.

## Actual local test history

Sol wrote the tests before the module. The first missing-module attempt produced
86 fixture errors and two pytest-cache permission warnings; these were not 86
behavioral assertion failures. An explicit availability assertion then failed as
expected. Initial implementation passed 87 tests. A subsequent immutable-policy
regression failed before its fix; the fixed suite passed 99 tests. Removing the
redundant availability-only assertion left the final behavioral suite:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_market_motor_readout.py -p no:cacheprovider --basetemp=.tools/motor-readout-implementation-20261109/final-temp
```

**98 passed in 0.31 s, zero skips and no final warnings.** The cache provider was
disabled after its initial filesystem warnings; no test was removed for a missing
dependency. The controller independently reran the focused suite with
`--basetemp=.tools/motor-readout-controller-20261109/final-temp`:
**98 passed in 0.28 s, zero skips.** The existing CI selection includes this suite.

Astra independently reviewed source, tests and all three frozen file hashes, then
exercised another 1,296-block direction/sign matrix successfully. No blocking
contract or code-quality finding remained. This accepts offline software behavior
only; no neural execution was involved. Clean-checkout results are recorded after
publication, separately from these local tests.

Reviewed module SHA256:
`e11e9a7adc10b10f08a67b25e41ad1d717174c0e5a106ef9be61416e060734e1`.
Test SHA256:
`100485f1676904ced21a6a5a4ed83c09164793ca02d36ee76f00ab13d4629820`.

## Preserved evidence

A read-only controller byte check passed for all 41 packaged sources, nine frozen
diagnostic source/lock bindings, 15 historical demo/companion files, seven named
diagnostic artifacts and both the Stage A and offline retinal reports. Package
fingerprint remains
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
The check imported no neural code and ran no engine.

Local evidence: `.tools/motor-readout-implementation-20261109/` and
`.tools/motor-readout-controller-20261109/preservation-check.json`.
No raw or private evidence is included in the source commit.

## Remaining gate

After publication, define a separate bounded
continuous-state protocol with previously unused inputs, fixed order/timing,
explicit neutral opportunities and finite resources. Measure completed paths,
stalls, slot concentration, attainable prices and latency without favorable-window
selection. No new acquisition, live board or event readiness follows from these
synthetic tests. Slower model computation is accepted for the local pilot; the
real-time price lock remains unchanged.
