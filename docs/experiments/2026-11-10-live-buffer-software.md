# Live buffer performance — software evidence

Task1 is independently accepted. The runner, native callback integration,
supervision binding and actual performance measurement remain outstanding.
The [protocol](../superpowers/specs/2026-11-09-live-buffer-performance.md) and
[plan](../superpowers/plans/2026-11-09-live-buffer-performance.md) were published
prospectively as`1ad9f53b8e753b6176c942f66feed86e02137410` before implementation.

## Fixed memory and admission state

`scripts/market_live_buffers.py` adds two synchronous in-memory components.
`CellRing` owns a fixed1000×256 uint8 count array and four little-endian int64
index/tick arrays:288000 array bytes. It validates exact original-bin chronology,
true integer fields and counts0–100 before casts or state changes. Successful
callback timing covers the sink body only, not engine-side callback preparation.
No callback history, rendering, file or network operation is introduced.

`export_observation(index)` produces a detached latest completed50-bin batch and
five nonoverlapping100-model-ms aggregates using uint16 sums. Its arrays occupy
17040 additional bytes; the ring retains no export. Repeated/incomplete/old exports
fail rather than masquerading as fresh data. Scalar/Python objects and caller-owned
retention are separate from these exact array-byte figures.

The versioned `market-live-cell-ring/v1` digest binds its exact ASCII dtype/shape/
column prefix, little-endian length/write position, four chronological int64
columns and chronological uint8 count rows. Empty,1-,50-,1001- and6000-bin literal
hash vectors were fixed independently using only stdlib/struct before implementation.
Astra independently recalculated all five. No machine-native byte order, padding,
timing or unused ring storage enters the digest. The full byte contract lives in
the module docstring; it is not a model-state or native-execution attestation.

`ImageAdmission.offer/handoff/finish` retain only one active request, one pending
request, a sequence high-watermark and a monotonic clock watermark. Valid new
sequences advance the watermark even when rejected as full. Reused sequences
cannot reenter; a later new request may use the same frame. Age<300000ms permits
handoff, equality or later expires pending. Finishing never implicitly activates
another request. Invalid inputs leave state unchanged; checked busy/empty/full
operations advance the wall clock. Expiry while busy removes only pending.

Each detached request uses `offered_ms`, including rejected offers. Accepted
offers are admitted at that same instant. This avoids falsely naming a rejected
request's time `admitted_ms`. State is session-local and single-owner, with no
durable restart deduplication or delivery guarantee.

## Actual verification and review

Final focused command:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_market_live_buffers.py tests/test_market_continuous_drive.py tests/test_market_motor_readout.py --basetemp=.tools/live-buffer-implementation-20261109/pytest-focused-02
```

**640 passed in2.27s, zero skips or warnings:**124 new ring/admission cases and516
unchanged synthetic driver/readout cases. No backend-wide suite or native run.
The new CI path is added; this local result is not hosted source-CI evidence.

Tests exercise6000 bins with stable array addresses/bytes,1000 retained and5000
evictions; exact hash chronology, detached exports in both directions, count100
to window1000 without uint8 overflow, malformed payload atomicity and gaps/types/
overflow. Queue cases include deadline−1/equality/+1, stalls, busy expiry, explicit
matching finish, double handoff, old sequences after all terminal/rejected states,
same-frame fresh sequences and10000 full rejections without growing history.

Failures remain recorded. Before implementation there were114 missing-module
fixture errors and then one isolated expected missing-module assertion; optional
pytest-cache access produced two warnings in each run. Disabling only that cache
provider removed the environmental warnings. Initial implementation failed46
cases while69 passed because an empty-shaped memoryview could not be cast for
hashing. Skipping empty slices fixed it;115 tests then passed. Nine added boundary
cases plus unchanged readouts passed640 before the timestamp review. A failing
`offered_ms` assertion preceded that correction; the final640-case run passed.
No validation/skip policy was weakened and no host escalation was needed.

Astra accepted final source/tests/CI hashes, actual logs, independent vectors and
preservation without findings. All60 old src/scripts Python/C++/PowerShell files
and41 packaged members remain byte-identical. The original259 tracked-file
inventory differs only at the CI insertion and two controller-owned protocol/plan
clarifications for the later offline-header audit. Package fingerprint remains
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.

| File | SHA256 |
| --- | --- |
| `scripts/market_live_buffers.py` | `5c81391fd4bf1a667ef0d483f027601af66f10eafd64a6e98283c53e1d1ec9ad` |
| `tests/test_market_live_buffers.py` | `1479877375a304db6d3dfee2a5fd11c446819f4704078b0312706bd5303b9b8a` |

RED/GREEN logs, hash vectors and before/after inventories remain in
`.tools/live-buffer-implementation-20261109/`. No actual recording, graph/header,
projection or engine was opened and no API/network call ran. A fresh Sol worker
may now implement Task2; actual measurement still requires all source reviews,
source CI and independently accepted concrete supervision readiness.
