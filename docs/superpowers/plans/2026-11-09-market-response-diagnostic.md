# Market Response Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL:
> superpowers:subagent-driven-development, sequentially. Sol implements; Astra
> independently reviews protocol, source and actual evidence. No worker agents.

**Status:** Completed and independently accepted; result commit `7e0fe3c` passed
[CI42665080242](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42665080242).
The broader market remains in Stage B. No additional acquisition is implied.

**Goal:** Collect one bounded matched-state input comparison without changing the
neural core or claiming a working drink market.
**Architecture:** An external diagnostic script composes existing engine,
checkpoint, observer and recorder interfaces. A separate Windows supervisor owns
the real Python child and resource limits. An offline auditor derives all reported
comparisons from a bounded verified raw snapshot.
**Tech Stack:** Existing Python 3.12/NumPy/pytest; a fixed PowerShell 7 entrypoint
and Python standard-library Win32 bindings for the first host supervisor. No new
dependencies or package-source changes.
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
- Monitored stop thresholds: 900 s wall, 4 GiB actual native Python peak RSS,
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

- [x] Write failing synthetic protocol/frame/observation/fork tests using the
  real recorder and declared test engine/cell fixtures. Exact checks: frame
  mirrors/bytes and fixed hashes; 68 observes/34,000ms; every call <=500ms;
  observer installed before advance; common-state restoration before all arms;
  monotonic observer indices despite branch clocks; no learning/DAN; invalid
  preparation/hash/output never starts the engine.
- [x] Write failing audit cases for missing/extra/reordered arms/events/bins,
  mismatched frame/group/cohort bindings, inconsistent population/cell counts,
  contradictory clocks/fork routes, unequal repeats and wrong final state hash.
  Validate fixed 20x11 grouping; do not make fixtures scientific evidence.
- [x] Test primary and secondary windows separately: an effect only in the
  first window remains secondary and cannot turn a zero primary into success.
  Pure zero vectors remain a valid null result; repeat mismatches invalidate
  comparisons and cannot produce an accepted completion receipt.
- [x] Record RED. Extract shared file helpers without widening limits; update
  existing tests/import setup for same-directory script helpers. Implement the
  diagnostic with public `brain.checkpoint/restore/checkpoint_state_sha256`,
  existing `build_header`, fixed observer and exact checkpoint-bound fork schema.
- [x] Capture at most50 callback bins per observe and immediately stream them
  as `cell_bins` on its ordinary observation event. Do not reuse the capped
  continuous `CellActivityWriter` or retain all callback arrays in memory.
- [x] Before each arm, verify common checkpoint bytes and restored state hash;
  record actual parent checkpoint sequence/name/hash and each arm's final state
  hash in the sealed raw stream: checkpoint/fork `complete_state_sha256`, final
  arm observe `complete_state_sha256_after`. Summary/receipt derive from those
  events; recorder metadata never gains post-hoc hashes. Use the spec's exact
  repeat projection, excluding administrative IDs/sequence/observer indices,
  timing and chain hashes while preserving measured cells/bins/rates/clocks.
  Do not invent a native replay-attestation mode or retention-operation version.
- [x] Run focused tests and the Stage A/recorder regression; include a bounded
  real tiny-native observer/restore interface check adapted from existing helpers.
  Confirm no default CLI mode can advance a native engine. Report actual skips.
- [x] Astra reviews the source/test diff against protocol; fix test-first and
  re-review. No acquisition or source publication claim before actual evidence.

**Historical Task 1 reviewed checkpoint:** diagnostic, capped audit and shared Stage A helpers
are implemented. Initial combined regression: 587 passed / five declared Windows
symlink-privilege skips. Astra identified one source-lock consistency gap; four
resealed counterexamples reproduced it. The corrected diagnostic passed all
40 tests, followed by two final fixture checks; scoped Astra re-review accepted.
The actual historical Stage A report stayed byte-identical, with all 15 historical
files and 41 package sources unchanged. No diagnostic acquisition has run.
The production CLI supervision gate below must land before native execution.

## Task 2 — Windows process supervision (Sol, after Task 1)

**Ownership:** Create `scripts/supervise-market-response.ps1`,
`scripts/market_supervision.py` and `tests/test_market_response_supervisor.py`;
narrowly add the latter to CI. After Task 1 review, adjust only the diagnostic's
production startup hook, CLI arguments and source bindings to require supervision;
update corresponding tests. Controller owns docs and host smoke evidence. Do not
mutate packaged core. Ownership is sequential, not shared concurrent editing.

**Interface:** PowerShell parameters `OutputDirectory`, `EvidenceDirectory`,
`ExpectedProtocolSha256`, `ExpectedReadinessSha256`, `Mode` (`Prepare`, `Run`).
The readiness hash is required in Run mode. Resolve the workspace/python/
entrypoint from the script location; no arbitrary program supplied by the public
interface. Diagnostic prepare creates only `protocol.json`; supervisor Prepare
requires that exact output inventory and creates a new evidence directory with
only `readiness.json`. Run checks both expected hashes, all bound identities and
both exact inventories before creating execution files. Prepare validates paths/
capabilities and writes readiness without native work; no failed-run reuse.
The Python helper owns Win32 Job/process handles, resource monitoring, the
spec's bounded ready/release handshake and exact compiler-version-only process
guard. PowerShell supplies the fixed public entrypoint. Its cancellation/exit
must also terminate the delegated supervisor and owned job; do not assume shell
child cleanup without host evidence. Native CLI requires supervision
directory, readiness hash and start token; only injected synthetic test engines
can execute without the host handshake. Freeze helper/supervisor/cache/compiler
identities in preparation. A static cache check alone does not prevent compilation.

- [x] Write failing process/path tests: disjoint fresh directories, old/partial
  artifacts rejected, no command interpretation of arguments, actual Python PID
  and start identity, timeout/memory/disk/monitor-failure terminate-and-wait,
  cancellation cleanup, nonzero exit/partial files never count as success.
  Internal test entrypoints may be non-neural children only, clearly test-scoped.
- [x] Implement hidden Python launch with robust argument handling and streamed
  stdout/stderr capture. Hold the actual worker handle after PID/start-time/path/
  ancestry checks; assign launcher and actual worker to a non-breakaway Windows
  Job Object with kill-on-close, then release the handshake after the first
  sample. Failure never releases native work. Track monotonic time, actual peak
  working set and all output/evidence bytes at <=2s intervals, including startup
  and final counters after exit. Compiler version children inherit the job;
  the Python process guard rejects new builds. Job commit limits are not RSS.
  Bind child `TMP`/`TEMP` to new counted evidence scratch after preflight; private
  audit copies count against the same total output threshold.
- [x] Use native PowerShell operations for filesystem work. Resolve and verify
  paths within the intended workspace before any cleanup; retain partial evidence
  on failure. Do not delete user data or count unrelated old test directories.
- [x] A supervisor receipt records real start/end, PID identity, limits, observed
  peak memory/output/wall time, exit/stop reason and exact prepared-manifest hash.
  Do not claim prevention of all between-poll spikes or distributed atomicity.
- [x] Run non-neural smoke children on the real host to prove owned-child
  identification and each stop condition. Tests may inject small thresholds but
  production limits remain fixed. State unsupported-platform skips explicitly.
  Include virtualenv forwarding, missing/wrong release, assignment failure,
  hanging version child, compile rejection and whole-job cancellation.
- [x] Astra reviews actual source plus host smoke evidence before native launch.

**Historical Task 2 reviewed checkpoint:** fixed PowerShell entrypoint, held actual Python
processes, owned kill-on-close job, parent watchdog, compiler-version-only guard
and counted scratch are implemented. Initial 32 Windows tests passed. Three
review findings were corrected test-first: actual `receipt.json` consumption,
identity/ancestry validation before cleanup authority, and locked fixed-size
cancellation with a terminal cutoff after job drain. The affected 23-case
regression passed, followed by three final cutoff/watchdog cases after the last
join check. Scoped Astra review accepted all three fixes and independently
checked 22 retained receipts: 21 exact final byte counts, one deliberately
incomplete accounting result, all recorded cleanup counts zero. Real Ctrl+C,
forced frontend/owner death and surviving unrelated processes were exercised.
Windows supervision is not claimed on Linux/macOS. Hosted CI selects the
portable tests and explicitly skips Windows-only host cases.

Repeat the public tests with:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_market_response_supervisor.py -p no:cacheprovider --basetemp=.tools/market-supervisor-check-new
```

Use a fresh basetemp. Windows sandbox hardlink/host-API restrictions required
normal host execution locally; checks were not weakened. The genuine earlier
prepare-only smoke is now stale because the reviewed fixes changed sources.
At that source checkpoint no diagnostic native acquisition had run. Both manifests
were subsequently prepared afresh for the completed Task 3 acquisition; see the
[accepted result](../../experiments/2026-11-09-market-response-diagnostic.md).
Those completed paths cannot be reused.

## Task 3 — bounded acquisition and actual evidence (controller)

**Ownership:** tracked experiment report, plan/current handover; new ignored
`runs/market-response-20261109-01/` and
`.tools/market-response-20261109-01/`. Never reuse a failed output path.

- [x] Verify unchanged baseline/core and protocol/source hashes; prepare the
  exact fresh manifest and supervisor readiness without neural advancement.
- [x] Review the complete concrete command/paths/limits and actual readiness.
  Execute one supervised Run under the user's approved sequential continuation;
  no automatic retry after a failed or inconclusive acquisition.
- [x] Inspect sealed raw data and summary; independently compare all repeated
  arms, primary/secondary vectors, cell/population arithmetic and resource logs.
  An aborted/invalid run remains incomplete; do not create a successful result.
- [x] Astra reviews actual evidence and unchanged original/source identities.
  Report observed input differences or null/invalid results within the exact
  declared scope. Decide the next technical step from evidence, not desired prices.
- [x] Review complete explicit staged files, commit/push the feature branch,
  observe CI and update the parent plan/current handover. Continue the approved
  project; do not infer readiness for the event market from this diagnostic alone.

Self-review: each timeline/identity/window requirement has Task 1 coverage;
process/resource/path risks have Task 2 tests plus host evidence; actual scientific
and performance interpretation is gated separately in Task 3. No future test or
acquisition is marked completed. Three tasks are sequential, with no source-file
ownership overlap during implementation.
