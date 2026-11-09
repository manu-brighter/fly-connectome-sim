# Continuous Motor Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development sequentially. Sol implements one bounded
> task at a time; Astra independently reviews protocol/source/evidence. No worker
> subagents; preserve others' edits. Controller owns documentation and commits.

**Goal:** One bounded, independently inspectable continuous-state probe of the
unchanged motor decoder, with honest positive/negative/incomplete outcomes.
**Architecture:** New external runner records192 observations plus decoder inputs
and results. A thin Windows adapter reuses the frozen owned-process monitor and
binds the new entrypoints; no changes to historical scripts or packaged sources.
**Tech Stack:** Existing Python3.12/NumPy/pytest, recorder, Windows ctypes monitor
and PowerShell7; no new dependency or service.
**Spec:** [continuous motor probe v1](../specs/2026-11-09-continuous-motor-probe.md).
**Status:** Prospective protocol and plan independently accepted and published
as `f07988a`. Task1 source is independently accepted:154 focused tests passed
with one declared Windows symlink-privilege skip. See the
[software evidence](../../experiments/2026-11-09-continuous-motor-software.md).
Task2 supervision is next; no acquisition yet.

## Global constraints

- Preserve the package, provenance locks, accepted decoder and all old diagnostic
  scripts/helpers/PS frontend and artifacts byte-for-byte. Branch remains
  `feat/connectome-experiment-core`; no PR, merge, deployment or paid request.
- Exact12×(2s black+6s pattern),96s/192observations/9600bins/194events/2checkpoints.
  New frames and fixed forward/reverse order come verbatim from the spec.
- One continuous root branch, no restores, resets, adaptive input or training.
  Every500ms interval advances. No cell observer or historical replay in this task.
- Unchanged v1 decoder,20fixture IDs/ranges/grid and5000ms delivery-age bound.
  This is path feasibility, not upload latency or live-display performance.
- Fixed900s/4GiB/256MiB supervision,≤2s polling, counted scratch; no automatic retry.
  Reader caps2MiB/1MiB/64MiB,194events,2checkpoints,64MiB each.
- Synthetic fixtures test software; actual fullgraph evidence is separate. No
  successful gate, native attestation, twenty-slot or priceboard claim is implied.

## Review focus

1. Resealed false motor counts/results: derive samples from original bins and
   reproduce every decoder result before success (Task1).
2. Hidden skipped black interval, decoder reset or shifted schedule: exact EOF
   event/tick/frame validation rejects a plausible shortened record (Task1).
3. Stale/rewound wall times or wrong source/config identities: raw clocks and
   metadata bind actual decoder reconstruction; invalid stream cannot pass (Task1).
4. A new entrypoint passing an old readiness record: bind new files explicitly,
   require hashes and actual held-process identity before release (Task2).
5. Frontend interruption/foreign ready PID/late cancellation: preserve ownership
   validation and fixed-size terminal cancellation semantics (Task2).

## Task1 — recorder and complete offline audit (Sol)

**Files:** Create `scripts/run-continuous-motor-probe.py` and
`tests/test_continuous_motor_probe.py`. Add only this test filename to CI.
Do not edit old runner, shared helpers or decoder. Controller owns docs.

**Interfaces:**

- `frames() -> dict[str, np.ndarray]` returns black,S1–S6 as specified.
- `prepare_probe(output_dir: Path) -> dict` exclusively writes the canonical
  source/config/schedule-bound protocol, without constructing an engine.
- `inspect_probe(output_dir: Path) -> dict` reads a bounded private snapshot and
  reconstructs all192 results without native execution or altering the original.
- `run_probe(output_dir: Path, *, expected_protocol_sha256: str,
  engine_factory=None, supervision_directory=None,
  expected_readiness_sha256=None, start_token=None, clock_ms=None) -> dict`.
  Test factory/clock injection is never a CLI option. Production requires Task2's
  `production_start` before engine construction; missing supervision fails closed.
  An injected clock without an injected test engine factory is rejected.
  Resolve the new supervision module only on this production run path, so
  `prepare`/`inspect` and synthetic Task1 tests work before Task2 exists.
- CLI `prepare`, `inspect`, `run` follows the old runner's explicit arguments;
  native run requires `--run-native` and all supervision bindings, no limit flags.
- Existing `MotorReadout.consume(sample, *, now_ms)`, `RunRecorder`, `verify_run`,
  `snapshot_recorded_run` and `write_json_exclusive` are reused as-is. Bind their
  source files. A single root `continuous` branch records no branch-start event.
- Each raw observation carries `motor_sample`, `readout_now_ms` and
  `readout_result`; metadata carries the fixed protocol/config digest and unique
  session ID. The auditor derives counts/expected identity from checked raw data,
  not the supplied sample. Fixed input version: `episode-01-black`,
  `episode-01-S1`, etc. Source SHA is the frozen protocol SHA256.
  Timing audit rejects contradictions, not a consistently rewritten/resealed
  history; no timestamp authenticity or native-attestation claim is made.
- Summary includes validity/scope, exactcounts, complete/partial route metrics,
  all proposed IDs/prices/timing, status/reason counts, direction signs, observed
  clocks/latencies and limitations from the spec. No price activation pass flag.
  Before implementation, report any remaining result-field naming decision.
  Accepted names: `validity`, `scope`, `exact_counts`, `outcome`, `proposals`,
  `route_metrics`, `status_counts`, `reason_counts`, `direction_counts`,
  `final_pending_state`, `clocks`, `latency_ms`, `order_partitions`, `limitations`,
  plus normal source/protocol/configuration identities. A valid full-session
  outcome is `narrow-positive` or `negative`; validity means the complete integrity
  audit only. Attribute a proposal to its completion partition without splitting
  a path across48s or treating orders as independent.

- [x] Write RED frame/timeline tests: all six exact formulas and2048white pixels,
  distinct hashes versus A–D,12episodes/192observations/9600bins/194events. Include
  every black observation, no restore, and unchanged decoder across48s boundary.
- [x] Write synthetic recorder/engine tests for valid no-proposal and supported
  proposal sessions; fake complete-state checkpoints are explicitly fixtures.
  Assert exact inputs, false learning/no stimulation, source/config digests and
  deterministic independent inspection. No private graph or native dependency.
- [x] Write resealed contradiction tests for bins/counts/rates/populations,
  sample/result/config/source/session/clock manipulation, learning/stimulation,
  wrong frame/order, gaps/overlap, missing/extra event and checkpoint mismatch.
  All invalid sources produce no summary/complete receipt.
- [x] Write limits/path/output collision/linked-path tests using existing safety
  patterns. Verify prepare/inspect never construct an engine or contact network.
  Test factory failure preserves partials and cannot create success artifacts.
- [x] Run focused suite RED, implement GREEN and record actual commands/skips.
  Default monotonic milliseconds use actual observation start/end and call time.
  No actor changes or thresholds are introduced to make fixtures work.
- [x] Astra independently reviews source/arithmetic/bindings and claims. Fix
  findings test-first; freeze reviewed hashes/report before Task2 starts.

## Task2 — thin bounded Windows supervision (Sol)

**Files:** Create `scripts/continuous_motor_supervision.py`,
`scripts/supervise-continuous-motor.ps1`,
`tests/test_continuous_motor_supervisor.py`; add only that test filename to CI.
No edits to Task1 or frozen sources without explicitly reporting the interface
need to the controller first. Sequential ownership avoids concurrent edits.

**Interfaces:** `prepare(output,evidence,protocol_hash)`,
`validate_prepared(output,evidence,protocol_hash,readiness_hash)`,
`production_start(output,protocol_hash,evidence,readiness_hash,token)` contextmanager
and `run(output,evidence,protocol_hash,readiness_hash,*,owner)` mirror the existing
supervisor boundaries, with a new readiness version and honest entrypoint binding.
`production_start` is the exact callable consumed by Task1's default run path.
The CLI/PowerShell parameters mirror existing Prepare/Run, paths/hashes and owner
identity. No arbitrary command, fallback runtime or limit override is exposed.

- [ ] Write RED binding tests for new runner/helper/frontend hashes, actual
  Python/cache/compiler configuration, reused helper source, owner identity,
  release/token/hash mismatch and scratch confinement. An old diagnostic readiness
  record or wrong new entrypoint must fail before engine construction.
- [ ] Implement a thin adapter around frozen `_run_owned`, `_wait_for_release`,
  compiler guard and process helpers. A nested, honestly named snapshot of the
  old runtime configuration may be reused, with separate new-file bindings; never
  relabel the old entrypoint as the actual new one or monkeypatch old globals.
- [ ] Preserve the PS ownership/ancestry/ACK/cancellation behavior in the new
  small frontend. Compare it to the frozen original apart from helper filename;
  do not duplicate the large Python monitor. Document private dependencies.
- [ ] Exercise new public entrypoints with harmless non-neural workers on the
  Windows host: normal completion contract, cancellation/owner death, unrelated
  ready PID rejection, late cancel after terminal cutoff and bounded cleanup.
  Static equality with old PS behavior supplements actual new-adapter smoke tests.
- [ ] Run focused tests, record real host checks/skips, then Astra source and
  lifecycle evidence review. No fullgraph run is part of implementation tests.

## Task3 — source checkpoint, one acquisition, actual result (controller)

- [ ] Integrate Tasks1/2, verify frozen core/decoder/old-source/artifact bytes,
  run the meaningful combined new tests and inspect explicit staged diff/size.
  Publish reviewed feature source and observe clean-checkout CI before acquisition.
- [ ] Prepare unique output/evidence paths and frozen protocol/readiness; review
  actual bytes/hashes, free space, exact command and finite limits with Astra.
  Do not reuse any completed diagnostic directory or treat docs as a run receipt.
- [ ] Execute exactly one bounded supervised acquisition under the authorized
  continuation; preserve aborts, no automatic retry. Inspect process cleanup and
  actual worker peak/output accounting, without claiming total-tree RSS.
- [ ] Inspect complete raw data and independently check derived metrics/outcomes.
  Astra evaluates actual evidence. Record negative/inconclusive honestly and
  preserve all source and historical artifacts.
- [ ] Update tracked experiment report, parent plan and handover; review/commit/
  push checkpoint and observe CI. Decide next technical step from actual evidence;
  no Stage C, additional acquisition or revised decoder follows implicitly.

Self-review: Task1 owns schedule/raw/reconstruction, Task2 owns actual execution
authority and bounds, Task3 consumes both independently reviewed deliverables.
CI entries are sequential; helper/decoder historical identities stay frozen.
