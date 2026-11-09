# Sequential motor readout — offline implementation plan

Use subagent-driven-development sequentially: Sol implements, Astra independently
reviews the contract and source. No worker agents. Preserve unrelated edits.

**Status:** Task1 independently accepted; 98 local tests pass without skips.
Published as `af4879b`; [CI42669739632](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42669739632)
passed 580 backend tests / 34 skips, 243 viewer tests / four private-artifact
skips and build. The separate [continuous probe protocol](../specs/2026-11-09-continuous-motor-probe.md)
is prospectively accepted; this offline plan is complete. No neural acquisition occurred.

**Goal:** A bounded deterministic decoder with honest synthetic evidence; no new
simulation, price activation or claim that all20drinks are neurally reachable.
**Spec:** [candidate v1](../specs/2026-11-09-sequential-motor-readout.md).
**Base:** reviewed source `5c3611b`, actual result `7e0fe3c`; both CI runs passed.
**Architecture:** One external standard-library Python module consumes explicit
samples. It owns only readout state; the unchanged neural engine and later price
service retain their separate responsibilities. No dependencies or core edits.

## Global constraints

- Preserve all accepted diagnostic scripts/helpers/supervisor, package sources,
  locks, raw evidence and old demo bytes. New code is outside the neural package.
- No engine/native/network/API calls, hidden random choices, price activation,
  source-data replay attestation or biological claims.
- Exact500-ms samples/four-sample blocks, fixed support/neutral/expiry rules,
  frozen drink order and required freshness configuration come from the spec.
- Every emitted target is integer Rappen on the configured bounded grid; full
  range jumps remain possible. The30-real-minute activation guard is not this module.
- No actual replay, calibration search or prospective neural acquisition in this
  implementation task. Tests explicitly use synthetic counts/clocks/identities.
- Keep source/return traces bounded and results detached. Source/session/clock
  discontinuities never combine old and new evidence into a proposal.

## Task1 — pure decoder and meaningful tests (Sol)

**Ownership:** Create `scripts/market_motor_readout.py` and
`tests/test_market_motor_readout.py`; add only the test filename to the existing
CI selection. No changes to accepted diagnostic/core source. Controller owns docs.

**Interface:** One small decoder object configured with ordered drinks and explicit
`max_sample_age_ms`. Consume one declared sample plus current wall milliseconds;
return status/reason and at most one detached proposal. Provide explicit pause/
resume and reconfiguration/reset methods. Use existing straightforward Python
style; no framework, persistence, transport or arbitrary threshold overrides.
Before implementation, report chosen exact field/method names to the controller.
The controller accepted the `MotorReadout` API now recorded in the spec.
Proposal measurement completion and call-time emission remain separate fields;
all stored/emitted aggregate counts must also be JSON-safe.

- [x] RED: supported positive/negative direction; each exact support boundary;
  silence, ties, alternating signs and one-spike cases abstain. Blocks do not overlap.
- [x] RED: two-sample neutral before first/each accepted decision; no repeated
  decisions from sustained evidence without rearm; deferred blocks do not expire
  or refresh paths except via declared clocks. No stimulus scheduling side effect.
- [x] RED: independently specified20-route truth table reaches every distinct ID.
  Expected bit routes for IDs0–19 are:
  `0000,0001,0010,00110,00111,0100,0101,0110,01110,01111,1000,1001,1010,10110,10111,1100,1101,1110,11110,11111`.
  Bits0/1 mean lower/upper. Do not compute expected routes using production bisection.
- [x] RED: separate price support, supported full minimum/maximum, half-up grid
  rounding and no single-spike extreme; one proposal only, then neutral required.
  No current price/cooldown fake service is needed to test target representability.
- [x] RED: model/wall exact expiry boundaries, no refreshed path timer, malformed
  or stale counts/clocks, duplicates/gaps/session/source changes, pause/resume,
  reconfiguration, restart and no pre-resume queued evidence crossing boundaries.
  Include a first supported block whose individual samples are fresh but whose
  recorded start is already expired. Ordering watermarks survive decision resets;
  forward-gap/new-session boundary packets are dropped and establish continuity
  for later samples. Old/rewound packets never lower or replace those watermarks.
- [x] RED: invalid drink counts/IDs/range/grid/config, explicit freshness requirement,
  immutable support history/config binding and long-silence bounded buffers.
- [x] Implement GREEN without importing the neural package or adding a CLI runner.
  Keep count/grid ratios integer-exact; no retrospective threshold tuning.
- [x] Run focused tests, record commands/RED/GREEN/skips, independent Astra source
  review; fix test-first and re-review. No broad unrelated suite or native run.

## Task2 — reviewed checkpoint and next protocol boundary (controller)

- [x] Verify all frozen diagnostic/core/historical identities unchanged. Run the
  meaningful targeted regression, not the previous native acquisition again.
- [x] Record tested software behavior and its synthetic-only scope; do not report
  real completed drink paths from generated traces. Review explicit staged paths,
  commit/push the feature branch and observe CI.
- [x] Only then define the separate continuous-state held-out protocol and its
  finite resources. No actual new acquisition or priceboard follows implicitly.

Preflight: Task1 produces only decoder behavior and tests; Task2 consumes test/
source evidence, not an unperformed neural result. CI is the only shared file;
there is one implementer. Existing diagnostic inspection remains unchanged.
