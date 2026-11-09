# Continuous Drive Input Comparison Implementation Plan

> Use superpowers:subagent-driven-development sequentially. Fresh Sol worker per
> bounded task; Astra reviews protocol/source/integrity. No worker subagents.
> Preserve others' edits; controller owns docs, acquisition and Git.

**Spec:** [fixed input comparison](../specs/2026-11-09-drive-input-comparison.md).
**Goal:** One prospective84-model-second controlled comparison of the frozen driver.
**Architecture:** New external runner/auditor, existing engine/recorder/telemetry,
new thin adapter to the accepted Windows owned-job supervisor. No package edits.
**Stack:** Existing Python3.12/numpy/pytest and PowerShell; no dependencies.
**Status:** Protocol/plan and Task1 runner/auditor independently accepted by Astra:
[software evidence](../../experiments/2026-11-09-drive-input-software.md),150 focused
passes/330 deliberate exclusions/no skips,57 old files and41-member package
fingerprint unchanged. Task2 supervision, source-CI and concrete acquisition
review remain; no new native execution or actual optical projection occurred.

## Global constraints

One fixed candidate/frames/schedule; no source/cutoff/outcome-driven changes after
freeze, no paid requests/training/random fallback, no Stage C or deployment.
Keep the accepted source, previous candidates and all original evidence unchanged.
Fresh feature-branch checkpoint after review, explicit push only. No PR/merge.

## Task1 — External acquisition and strict offline audit

Own new `scripts/run-drive-input-comparison.py`, new
`tests/test_drive_input_comparison.py`, one path in existing compatibility CI.

Public interfaces follow the existing runner pattern: `prepare_comparison(Path)`,
`run_comparison(Path, *, expected_protocol_sha256, engine_factory=None,
supervision_directory=None, expected_readiness_sha256=None, start_token=None)`,
`inspect_comparison(Path)`. CLI modes `prepare`, `run`, `inspect` retain existing
`--output-dir`, `--expected-protocol-sha256`, `--run-native`,
`--supervision-directory`, `--expected-readiness-sha256`, `--start-token` names.
Only injected synthetic factories bypass production supervision; CLI has no such
option. Import the new adapter lazily in the native path, so Task1 synthetic
preparation/inspection does not depend on Task2 files already existing. Task1
protocol pins its own/shared dependencies; readiness separately pins new adapter
and frontend, following the accepted continuous-supervision pattern.

- [x] Record synthetic RED before implementation. Reuse appropriate existing
  fixture patterns and small helpers; do not read actual input-response artifacts.
- [x] Implement deterministic frames/175-event schedule/source-bound preparation,
  fixed decoder configuration and input-vector metadata. Projection must not
  advance state; bind actual ordered vectors and summaries to engine provenance.
- [x] Implement fresh-engine4s prefix and four restored20s branches; distinct
  fresh decoder per arm, actual clocks, exact complete-state checks and bounded
  three-checkpoint recording. Prefix is recorded without decoder consumption.
- [x] Implement independent full-snapshot/EOF inspection with exact fields/types,
  fixed schedule/provenance/telemetry, complete decoder reconstruction and all
  predetermined interpretation flags. Never trust stored summary success fields.
- [x] Test valid functional/sensitive, timing-only and count-only distinction,
  functional-without-sensitivity, all-deferred, repeat mismatch and wall failure.
  Exercise wrong state/branch/checkpoint/source/frame/decoder/time, resealed rate/
  bin/count tampering, projection metadata arithmetic, malformed/oversized input,
  iterator closure, write collision and forbidden native/network inspect paths.
- [x] Run focused new tests plus only relevant unchanged helper/driver regression;
  record exact passes/skips, failures and old-source preservation. Add CI path.
- [x] Astra independently accepts producer/auditor/fixture scope and evidence.

## Task2 — Thin supervision binding

Own new `scripts/drive_input_supervision.py`, new
`scripts/supervise-drive-input.ps1`, new `tests/test_drive_input_supervisor.py`,
one CI test path. Task1 is accepted before this fresh worker starts.

- [ ] Test-first new version/entrypoint/source/runtime/limit/path bindings and
  actual-PID release; refuse altered protocol/readiness, reused paths or missing
  supervisor authority before engine construction.
- [ ] Adapt the accepted continuous supervisor with only necessary binding/name
  differences, preserve the old module and PowerShell files byte-for-byte. Reuse
  monitor, compiler guard, owned-job cleanup and cancellation; no global patching.
- [ ] Verify changed adapter behavior and unchanged monitor/frontend lifecycle
  assumptions with focused tests/byte comparisons; reuse existing accepted
  harmless-process evidence where the underlying path is exactly unchanged.
- [ ] Astra reviews source and real execution boundaries. Freeze all source-bearing
  tasks and confirm unchanged package fingerprint before any concrete prepare.

## Task3 — One acquisition and accepted evidence

Controller owns ignored fresh protocol/readiness/output/evidence and tracked
result report, plan/handover updates. No source edits during a frozen attempt.

- [ ] Review a concrete command, finite limits, empty fresh paths, actual worker/
  compiler/cache identities, source and source-CI results. Independently check
  the preparation and supervisor release/cancellation bindings before launch.
- [ ] Run exactly once under the owned supervisor. Observe actual resource bounds
  until completion/termination, retain partials and confirm zero owned survivors.
- [ ] Inspect complete actual artifacts; Astra independently verifies declared
  states, every observation, proposal, projection, repeats, clocks and resources.
  Report each component's outcome without retuning or automatic retry.
- [ ] Publish reviewed evidence with exact test/acquisition/CI results. Decide the
  next Stage B deliverable from the actual result, keeping service/load gates open.

Self-review: Task1 defines protocol/public run/inspect interfaces; Task2 binds them
without changing the monitor; Task3 consumes both only after freeze. CI is shared
sequentially, docs controller-only. The prefix has no readout; branch restores reset
neural state but never real clocks. Projection is optical input, not motor evidence.
