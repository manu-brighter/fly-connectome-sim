# Market Response Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL:
> superpowers:subagent-driven-development, sequentially. Sol implements; Astra
> independently reviews protocol, source and actual evidence. No worker agents.

**Goal:** Collect one bounded matched-state input comparison without changing the
neural core or claiming a working drink market.
**Architecture:** An external diagnostic script composes existing engine,
checkpoint, observer and recorder interfaces. A separate Windows supervisor owns
the real Python child and resource limits. An offline auditor derives all reported
comparisons from a bounded verified raw snapshot.
**Tech Stack:** Existing Python 3.12/NumPy/pytest; PowerShell 7 for the first host
supervisor. No new dependencies or package-source changes.
**Spec:** [frozen diagnostic protocol](../specs/2026-11-09-market-response-diagnostic.md).
**Base:** Stage A implementation `dcb7f79`; source review and actual acceptance
passed. CI [42648225025](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42648225025)
passed: 429 backend tests / eight skips, 243 viewer tests / four private-artifact
skips and build. All five locally skipped analyzer link tests passed on Linux.

## Global constraints

- No `src/fly_connectome_sim/` changes, new simulator, DAN stimulation, training,
  LLM/API calls or deployment. Preserve all historical files and provenance locks.
- Exact protocol: 2,000 ms black prefix, eight restored 4,000-ms arms, 500-ms
  observations, 34,000 ms actual advancement, 68 observations, 79 events,
  3,400 native bins; primary last500ms, all eight windows secondary.
- Exact frame/arm order, fixed cohort/grouping and source bindings come from the
  spec. No adaptive parameter choices or repeated search after inspecting output.
- Hard stop thresholds: 900 s wall, 4 GiB actual native Python peak RSS,
  256 MiB total new output/evidence, polling interval <=2 s.
- First acquisition only after source/supervisor review and host monitoring smoke
  tests. Worker tests may use bounded existing tiny-native interfaces, not fullgraph.
- No new native runs by workers; controller performs the reviewed acquisition.
- Failure/inconclusive are valid outcomes. Never label this twenty-slot, price,
  learning, real-time or twelve-hour qualification.

## Review focus

- Restoring neural arrays but not visual filters/complete state (Task 1 tests).
- Mixing arm times or administrative observer indices into repeat comparisons
  and thereby inventing nondeterminism or continuity (Task 1 tests).
- Correct hashes with missing/cross-arm bins or altered frame/group/protocol
  declarations (Task 1 tests).
- Monitoring a wrapper, failing to kill the owned process, counting old output,
  or publishing success after monitor/resource failure (Task 2 tests).
- Earlier effects replacing a null primary window, or receipt existence replacing
  raw/source/resource acceptance (Tasks 1 and 3).

## Task 1 — diagnostic and offline audit (Sol)

**Ownership:** Create `scripts/run-market-response-diagnostic.py`,
`tests/test_market_response_diagnostic.py`. Reuse the existing bounded snapshot
and exclusive JSON publication logic by extracting it into
`scripts/market_artifacts.py`; narrowly adjust
`scripts/analyze-market-feasibility.py` and `tests/test_market_feasibility.py` to
consume it. Preserve their CLI, validation behavior and exact report encoding.
Add the new tests to `.github/workflows/compatibility.yml`. No other source changes.

**Interfaces:**

- Shared `snapshot_recorded_run(source: Path, *, limits: RunReadLimits,
  checkpoint_byte_limit: int)` is a context manager yielding an owned bounded
  snapshot. `write_json_exclusive(payload: dict, path: Path) -> None` preserves
  Stage A's complete-write/fsync/exclusive-hardlink behavior. Keep helpers narrow.
- New `prepare_diagnostic(output_dir: Path) -> dict` freezes protocol, frame
  hashes and source identities without constructing the native engine. Existing
  output refuses overwrite; no raw execution artifacts may exist at preparation.
- New `run_diagnostic(output_dir: Path, *, expected_protocol_sha256: str,
  engine_factory=None) -> dict` executes exactly the protocol and returns a
  completion receipt only after offline audit. Test injection stays out of CLI;
  production constructs the normal prepared-graph engine.
- New `inspect_diagnostic(output_dir: Path) -> dict` validates the capped raw
  snapshot and derives primary/secondary comparisons and repetition checks.
- CLI subcommands `prepare`, `run`, `inspect`, all with `--output-dir`.
  `run` also requires `--expected-protocol-sha256` and explicit `--run-native`.
  No timing/group/limit override, auto-resume, API option or permissive verifier.

- [ ] Write failing synthetic protocol/frame/observation/fork tests using the
  real recorder and declared test engine/cell fixtures. Exact checks: frame
  mirrors/bytes and fixed hashes; 68 observes/34,000ms; every call <=500ms;
  observer installed before advance; common-state restoration before all arms;
  monotonic observer indices despite branch clocks; no learning/DAN; invalid
  preparation/hash/output never starts the engine.
- [ ] Write failing audit cases for missing/extra/reordered arms/events/bins,
  mismatched frame/group/cohort bindings, inconsistent population/cell counts,
  contradictory clocks/fork routes, unequal repeats and wrong final state hash.
  Validate fixed 20x11 grouping; do not make fixtures scientific evidence.
- [ ] Test primary and secondary windows separately: an effect only in the
  first window remains secondary and cannot turn a zero primary into success.
  Pure zero vectors remain a valid null result; repeat mismatches invalidate
  comparisons and cannot produce an accepted completion receipt.
- [ ] Record RED. Extract shared file helpers without widening limits; update
  existing tests/import setup for same-directory script helpers. Implement the
  diagnostic with public `brain.checkpoint/restore/checkpoint_state_sha256`,
  existing `build_header`, fixed observer and exact checkpoint-bound fork schema.
- [ ] Capture at most50 callback bins per observe and immediately stream them
  as `cell_bins` on its ordinary observation event. Do not reuse the capped
  continuous `CellActivityWriter` or retain all callback arrays in memory.
- [ ] Before each arm, verify common checkpoint bytes and restored state hash;
  record actual parent checkpoint sequence/name/hash and each arm's final state
  hash in the sealed raw stream: checkpoint/fork `complete_state_sha256`, final
  arm observe `complete_state_sha256_after`. Summary/receipt derive from those
  events; recorder metadata never gains post-hoc hashes. Use the spec's exact
  repeat projection, excluding administrative IDs/sequence/observer indices,
  timing and chain hashes while preserving measured cells/bins/rates/clocks.
  Do not invent a native replay-attestation mode or retention-operation version.
- [ ] Run focused tests and the Stage A/recorder regression; include a bounded
  real tiny-native observer/restore interface check adapted from existing helpers.
  Confirm no default CLI mode can advance a native engine. Report actual skips.
- [ ] Astra reviews the source/test diff against protocol; fix test-first and
  re-review. No acquisition or source publication claim before actual evidence.

## Task 2 — Windows process supervision (Sol, after Task 1)

**Ownership:** Create `scripts/supervise-market-response.ps1` and
`tests/test_market_response_supervisor.py`; narrowly add the latter to CI.
Controller owns docs and host smoke evidence. Do not mutate the diagnostic/core.

**Interface:** PowerShell parameters `OutputDirectory`, `EvidenceDirectory`,
`ExpectedProtocolSha256`, `ExpectedReadinessSha256`, `Mode` (`Prepare`, `Run`).
The readiness hash is required in Run mode. Resolve the workspace/python/
entrypoint from the script location; no arbitrary program supplied by the public
interface. Diagnostic prepare creates only `protocol.json`; supervisor Prepare
requires that exact output inventory and creates a new evidence directory with
only `readiness.json`. Run checks both expected hashes, all bound identities and
both exact inventories before creating execution files. Prepare validates paths/
capabilities and writes readiness without native work; no failed-run reuse.

- [ ] Write failing process/path tests: disjoint fresh directories, old/partial
  artifacts rejected, no command interpretation of arguments, actual Python PID
  and start identity, timeout/memory/disk/monitor-failure terminate-and-wait,
  cancellation cleanup, nonzero exit/partial files never count as success.
  Internal test entrypoints may be non-neural children only, clearly test-scoped.
- [ ] Implement hidden direct Python launch with robust argument handling and
  asynchronous stdout/stderr capture. Track the owned handle, elapsed monotonic
  time, peak process memory and all output/evidence bytes at <=2s intervals.
  Check final counters/status after child exit too. Handle compiler children
  within supervision or reject missing validated native cache before launch.
- [ ] Use native PowerShell operations for filesystem work. Resolve and verify
  paths within the intended workspace before any cleanup; retain partial evidence
  on failure. Do not delete user data or count unrelated old test directories.
- [ ] A supervisor receipt records real start/end, PID identity, limits, observed
  peak memory/output/wall time, exit/stop reason and exact prepared-manifest hash.
  Do not claim prevention of all between-poll spikes or distributed atomicity.
- [ ] Run non-neural smoke children on the real host to prove owned-child
  identification and each stop condition. Tests may inject small thresholds but
  production limits remain fixed. State unsupported-platform skips explicitly.
- [ ] Astra reviews actual source plus host smoke evidence before native launch.

## Task 3 — bounded acquisition and actual evidence (controller)

**Ownership:** tracked experiment report, plan/current handover; new ignored
`runs/market-response-20261109-01/` and
`.tools/market-response-20261109-01/`. Never reuse a failed output path.

- [ ] Verify unchanged baseline/core and protocol/source hashes; prepare the
  exact fresh manifest and supervisor readiness without neural advancement.
- [ ] Review the complete concrete command/paths/limits and actual readiness.
  Execute one supervised Run under the user's approved sequential continuation;
  no automatic retry after a failed or inconclusive acquisition.
- [ ] Inspect sealed raw data and summary; independently compare all repeated
  arms, primary/secondary vectors, cell/population arithmetic and resource logs.
  An aborted/invalid run remains incomplete; do not create a successful result.
- [ ] Astra reviews actual evidence and unchanged original/source identities.
  Report observed input differences or null/invalid results within the exact
  declared scope. Decide the next technical step from evidence, not desired prices.
- [ ] Review complete explicit staged files, commit/push the feature branch,
  observe CI and update the parent plan/current handover. Continue the approved
  project; do not infer readiness for the event market from this diagnostic alone.

Self-review: each timeline/identity/window requirement has Task 1 coverage;
process/resource/path risks have Task 2 tests plus host evidence; actual scientific
and performance interpretation is gated separately in Task 3. No future test or
acquisition is marked completed. Three tasks are sequential, with no source-file
ownership overlap during implementation.
