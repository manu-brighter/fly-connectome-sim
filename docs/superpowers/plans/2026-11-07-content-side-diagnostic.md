# Bounded content and side diagnostic implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development for this
> single bounded task. The current handover authorizes implementation and a
> reviewed feature commit/push; no additional product decision is needed.

**Goal:** Measure the fixed visual manipulation and card-side comparisons once,
including no-effect and defer outcomes.

**Architecture:** One small diagnostic module composes the existing decoder,
engine, complete checkpoints, renderer and motor adapter. Two feed prefixes
share one fresh start; three probes branch from each real feed-end checkpoint.
Diagnostic files remain separate from public replay/session contracts.

**Tech Stack:** Existing Python/native engine, NumPy, PyAV and Pillow; no new
dependency or numerical-model change.

**Spec:** [Fixed protocol](../specs/2026-11-07-content-side-diagnostic.md).

## Global constraints

- Work on `feat/connectome-experiment-core`, preserve existing core/locks.
- Exactly two 8s feeds and six 2s probes, 504 calls, one engine; no adaptive dwell.
- Explicit black uint8 input; no external DAN/learning; ordinary passive decay.
- Same complete start state at tick0, same history-specific probe state at80000.
- Fixed 1Hz motor adapter; no winner hunting or fullgraph retry.
- Fullgraph supervision: 900s wall, 4GiB RSS, 256MiB new output.
- Sol owns implementation/tests; Astra checks protocol and final integrity.
- Controller owns protocol coordination, supervision, independent checks/docs/git.

## Review focus

- Input/source drift must fail before native observation.
- Restored state mismatch, wrong clocks or missing black intervals must fail.
- Side swap must retain option objects and map physical action correctly.
- Counts/rates/windows must derive from actual native bins, including defer.
- Existing output and failed partial runs must never masquerade as completion.

## Task 1: Diagnostic harness, evidence and report

**Files:** Create `src/fly_connectome_sim/experiment/content_diagnostic.py`,
`tests/experiment/test_content_diagnostic.py`, scoped result under
`docs/experiments/`; update README and current cloud handover after evidence.

**Interfaces:** A `run_content_diagnostic` function with explicit input paths,
engine factory and pinned source declarations; module entry point for the
fixed original-input protocol. Return a count-derived summary and preserve raw
JSONL, input/protocol/engine bindings and checkpoints under a new output path.

- [x] Astra reviews the fixed protocol against actual code and scientific claims.
- [x] Sol writes and executes failing meaningful tests before implementation:
  actual tiny-native 504-call schedule, restore equivalence, normal/swapped/black
  inputs, final-window arithmetic/mapping, drift and partial-output failures.
- [x] Sol implements the bounded harness and module entry point; no public CLI,
  viewer, kernel, schema, selection policy or dependency changes.
- [x] Run diagnostic tests plus focused engine-adjacent adapter/card/video/session
  regression tests; record exact commands, outcomes and skips.
- [x] Independent implementation review; freeze/hash tested source and protocol.
- [x] Run the single supervised fullgraph attempt; retain partial failures.
- [x] Independently recompute raw clocks/counts/rates/adapter contrasts and verify
  checkpoint/input/source bindings. Do not rerun the native simulation.
- [x] Publish scoped results, presentation claim and current TODOs; obtain final
  independent evidence/claim review. Delivery uses an explicit reviewed
  first-party feature commit/push; Git history/tracking records delivery.

## Execution ledger

- Initial checkout: clean `1b0e996`, tracking matching origin feature branch.
- Ruling: no new worktree or approval round; the handover explicitly authorizes
  this technical continuation in the named branch/workspace.
- Ruling: plain diagnostic artifacts avoid extending formal/public verifiers;
  they carry no native replay or scientific qualification authority.
- Self-review: one task owns harness/tests and produces raw evidence for the
  controller's report. Both share the fixed protocol; no overlapping code edits.
- Protocol approved after independent engine/checkpoint/visual/adapter review;
  input hashes confirmed. Resource caps are monitored every2s, not OS limits.
- Sol observed11 behavioral failures against the stub, then11 passing tests;
  later strengthened assertions passed on their first verification run.
- Controller regression:204 passed, no skips,172.86s; exact command in report.
- Astra implementation review: no findings; all93 frozen paths rehashed.
- Single attempt completed:504 observations/521 events/3120 bins,183.240s module
  wall time. Independent raw audit passed and all93 frozen files still match.
- Supervision correction: original Windows venv launcher RSS missed its native
  child. A supplemental watcher used retrospective OS peak plus active samples;
  Astra accepted this disclosed deviation. See result report for exact limits.
- Task1 complete: final Astra evidence review independently reconstructed all56
  windows, confirmed204 tests and accepted scoped claims with the disclosed
  supervision deviation. No additional native run or API call is part of this plan.
