# Continuous Motor Drive Implementation Plan

> Use superpowers:subagent-driven-development sequentially. One fresh Sol worker
> implements Task1; Astra independently reviews protocol, source and evidence.
> No worker subagents. Preserve others' edits. Controller owns docs, replay and Git.

**Spec:** [continuous motor drive v1](../specs/2026-11-09-continuous-motor-drive.md).
**Goal:** Test a distinct sustained-activity command contract without editing the
neural package, old readouts, evidence or helpers, and without another acquisition.
**Architecture:** Thin direct v1 subclass; unchanged support, mapping and guards.
**Stack:** Existing Python3.12/pytest, no dependency or application integration.
**Status:** Prospective contract independently accepted by Astra; no candidate result.

## Global constraints

One frozen candidate and one full unchanged-clock development replay. No training,
provider call, native execution, constant tuning, new simulator or Stage C work.
All old tracked source/package/locks and recordings remain unchanged. Scope stays
on the existing feature branch; explicit feature push only, no PR/merge/deploy.

## Task1 — Minimal driver and synthetic verification

Ownership: new `scripts/market_continuous_drive.py`, new
`tests/test_market_continuous_drive.py`, one test-path addition in
`.github/workflows/compatibility.yml`.
Controller handles documentation and ignored review logs.

- [ ] Write meaningful synthetic tests and record the expected red result before
  creating the module. No actual recording inspection or candidate calculation.
- [ ] Implement only the spec's three hooks plus identity rebinding. Preserve
  all v1 support/price arithmetic and guard order; no sample consumed twice.
- [ ] Construct all165 leaf routes across sizes10–20, at both price endpoints.
  Verify complete disjoint support, repeated fresh commands, ambiguity/silence,
  discarded blocks, malformed/stale/ordering/source boundaries, input history, expiry,
  pause/reset, successful/failed reconfigure, configuration/hash copy isolation.
- [ ] Run new tests plus unchanged98 base tests. Record real commands/results,
  skips and old-source hashes. Add only the new file to the existing CI selection.
- [ ] Astra independently reviews source and tests against the frozen contract;
  fix concrete findings and recheck affected cases before Task2.

## Task2 — One guarded development replay and checkpoint

Ownership: controller's new ignored helper/output; tracked result report,
this plan and `docs/cloud-handover.md`. No production code or old helper edits.

- [ ] Prepare a new helper by adapting the accepted old replay scaffold, preserve
  all input/provenance guards, replace v2 latch-specific accounting, and retain
  every proposal's separate fresh evidence. Bound output to the192 observations.
- [ ] Freeze exact command, source/configuration/input hashes and exclusive paths.
  Astra reviews concrete preflight before execution. Prepare does not consume
  samples or calculate candidate results.
- [ ] Run once on all192 unchanged samples/clocks with native/network/process
  starts prohibited. Record all results, counts, partial state and before/after
  artifact identities; never change the candidate based on its outcome.
- [ ] Astra independently verifies the complete actual trace and conclusions.
  Keep technical reachability separate from observed coverage and input causation.
- [ ] Record the honest result, inspect full explicit staged diff/size, publish
  the feature checkpoint and observe CI. A later functional/input-sensitivity
  gate requires its own prospective contract before any new acquisition.

Self-review: Task1 produces the candidate API and immutable identity Task2 consumes.
Only the controller writes docs/replay; the worker owns the three implementation
paths. Synthetic reachability is not substituted for actual neural coverage.
