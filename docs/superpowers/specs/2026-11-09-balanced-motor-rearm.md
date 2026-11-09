# Activity-balanced motor rearm — offline candidate v2

Status: prospective offline candidate, synthetic implementation and one
[negative development replay](../../experiments/2026-11-09-balanced-motor-rearm.md)
are independently accepted. The prospective rules below remain unchanged.
This is a bounded technical continuation of
the authorized drink-market feasibility work, not a new product decision.
Controller-selected engineering constants below are not user-specified or
biologically validated.

## Problem and scope

The accepted [continuous v1 probe](../../experiments/2026-11-09-continuous-motor-probe.md)
completed with no proposal. After one supported direction, ongoing activity never
met v1's quiet rearm requirement, including the later black intervals. All twelve
episode aggregates were left-dominant. Raising expiry cannot create missing
neutrality; increasing an absolute quiet cutoff could mislabel directional
activity as a release signal.

Test exactly one separately versioned engineering candidate: preserve the quiet
route and additionally permit a sustained, active, bilaterally balanced block to
release the latch. This addresses the release condition only. It does not remove
left bias, guarantee selections, force alternation, normalize cells or establish
twenty-drink control. No price service, viewer, upload endpoint, new native run,
training, provider request or dependency is part of this scope.

Preserve `scripts/market_motor_readout.py`, its tests, all accepted probe and
supervisor sources, packaged files, locks and historical artifacts byte-for-byte.
The accepted v1 result remains negative. The native runner continues using v1.

## Exact additional release rule

Version: `sequential-motor-readout/v2`. Existing sample/configuration validation,
source/session ordering, freshness, real/model clocks, binary drink routes,
direction and price support, expiry, pause/reset and output price mapping remain
unchanged. Both rearm alternatives apply initially and after every accepted
direction, including before price evidence, and after explicit or automatic resets.

The original quiet route retains precedence: two consecutive 500-ms observations
with `L+R <= 2` each produce `ready / neutral_ready`.

The additional route evaluates four consecutive accepted observations while
unarmed, in non-overlapping blocks starting with the first observation after
entering that state. An accepted observation here is a valid, fresh, in-order
sample for which v1 returns `waiting / waiting_for_neutral`. Require:

- Combined block total `sum(L+R) >= 20`.
- For **each** of the four observations, `10 * abs(R-L) <= L+R`, inclusive.
  Use exact integer arithmetic. A zero/zero observation satisfies the per-sample
  band; the block-total bound still applies. Activity is required across the
  block, not in every observation. No separate active-sample minimum is introduced.
- The block aggregate left, right and combined counts remain JSON-safe integers,
  using the same rejection/clear behavior as v1's supported measurements.

The 10% band is half the existing 20% direction threshold. This is a prospective
engineering separation, not a cutoff selected by searching the recorded run.
An aggregate-only balance test is insufficient: alternating strong one-sided
samples must not masquerade as sustained bilateral balance.

Evaluate a complete four-sample block, then discard it whether it succeeds or
fails. Do not restart its alignment on each imbalance or use a sliding window.
On success return `ready / balanced_ready`, clear both rearm buffers and arm the
unchanged direction/price collection. **The release sample/block cannot also
contribute to the next direction or price block.** A quiet release discards any
incomplete active-balance block. After either release, the next accepted sample
is the first possible decision sample. A rejected active-balance block leaves
the independent quiet streak intact, so valid quiet pairs can span its boundary.

All clears, stale samples, source/session transitions, gaps, invalid samples,
pause/resume/reset/reconfiguration and path expiries clear the new buffer whenever
v1 clears decision evidence. A sample dropped by v1 cannot become rearm evidence.
There is no timed release, synthetic neutrality, baseline subtraction, forced
direction, image-dependent release or reuse of pre-transition evidence.

## Source structure and identity

Create `scripts/market_motor_readout_v2.py` with `MotorReadoutV2`, a thin subclass
of the frozen `market_motor_readout.MotorReadout`. Reuse its private validation,
ordering, configuration, clearing, measurement and decision machinery explicitly;
do not copy the whole decoder, monkeypatch v1 globals or inject invented samples.
The original `_consume` executes its validation/order/expiry path first. Only its
valid unarmed waiting result can contribute to the additional balance buffer.
An already armed sample retains the original decision behavior.

Expose the same constructor and methods:

```text
MotorReadoutV2(drinks, *, max_sample_age_ms)
consume(sample, *, now_ms)
pause/resume/reset(*, now_ms)
reconfigure(drinks, *, max_sample_age_ms, now_ms)
configuration, configuration_sha256, policy_version
```

Configuration uses the v2 version and the complete unchanged v1 policy plus:
`balanced_rearm_samples=4`, `balanced_rearm_total_min=20`,
`balanced_rearm_fraction_numerator=1`, `balanced_rearm_fraction_denominator=10`.
These declarations are immutable through public access and included in the
configuration digest. Successful and failed reconfiguration must never leave a
v1 identity on the v2 object. No production CLI or adjustable band is introduced.
Keep the five existing result fields; `balanced_ready` is the only added reason.
Proposals retain the v2 policy/configuration identity and original bounded support
history. Complete raw input/result traces provide reconstruction evidence; the
new rearm buffer holds at most four observations.

Every complete rearm block passes the inherited aggregate measurement validation
before its minimum/band is evaluated, even if it would otherwise be rejected.
The complete post-anchor input history still contains rearm samples; non-reuse
means they are absent from subsequent direction/price support blocks, not erased
from that historical record.

## Offline acceptance and development inspection

Software acceptance requires synthetic cases for both release alternatives,
exact 10% and block-total boundaries, aggregate-cancelling strong directions,
non-overlapping windows, no decision/rearm evidence reuse, unchanged expiry and
all twenty literal synthetic routes. Check left/right symmetry at the rearm and
direction rules; the unequal-depth ordered 20-leaf tree is not a claim of a simple
mirrored drink-index mapping. Sustained one-sided activity must not repeatedly
advance a path. Existing v1 tests remain unchanged and pass.

After source review, perform **one** descriptive software replay over all 192
observations of the accepted continuous recording, with the original source,
input, model and real clock fields unchanged. First reproduce the accepted v1
audit, then bind the complete raw recording to its recorded manifest/events hashes.
Use the fixed 20-drink fixture and 5,000-ms delivery-age bound from that protocol.
No image/window subset, altered timing, reset, calibration, cutoff sweep or neural
execution is permitted. Retain a separate candidate trace/report; never replace
the producer's v1 summary, receipt or readout results.

This is **development evidence**, because the candidate was motivated by this
recording. It cannot be held-out confirmation. Report every release reason and
support interval, supported directions, complete/partial routes, target prices,
ID concentration, expiry, final state and the exact source/configuration hashes.
A valid replay with zero improvement is a valid result, not an implementation
failure. Synthetic reachability and even a completed historical route do not
qualify a live twenty-drink controller. If the candidate still cannot rearm on
this trace, no further native run is justified merely to repeat that failure.

Any later candidate or measurement requires an explicit new design/protocol and
independent review. A positive development replay likewise does not automatically
advance Stage C or authorize a native acquisition.
