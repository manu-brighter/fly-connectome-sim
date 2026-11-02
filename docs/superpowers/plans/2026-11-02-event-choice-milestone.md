# Event Choice Milestone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two imported event proposals become actual visual inputs, a measured
left/right/defer decision and a locked event plan/replay.

**Architecture:** Extend the existing engine/RunRecorder with a closed product
pilot and deterministic card renderer; use the unchanged motor adapter. Separate
strict event replay/plan exports and viewer support preserve old formats. No
LLM API dependency or new simulator; the imported proposal is untrusted data.

**Tech Stack:** Python3.12/Pillow12.3/native C++, existing TypeScript/Three.js/
Mediabunny viewer and Node24. No new dependency.

**Spec:** [Event choice contract](../specs/2026-11-02-event-choice-milestone.md).

## Global constraints

- Exactly two event-options/v1 proposals;384x216 deterministic paired RGB.
- Fresh engine;four500ms observe calls;final500ms same-event 1Hz motor readout;
  decision at20000ticks. No learning/DAN/reset/forced winner or old CP restores.
- Plan is exact selected proposal or explicit defer, derived only after full
  sealed semantic verification. No selected-option/threshold override API.
- Imported examples are not live LLM calls. No schema/core/dependency changes.
- Current-source reviews before one max2s/120s actual pilot; no formal/C1 return.
- Event export2s source+90 labelled hold frames=5s at30fps; old formats keep15.

## Review focus

- Malicious/oversized/duplicate/unknown proposal fields fail before engine/output.
- Rehashed selection/plan/raw-bin/clock modifications fail semantic verification.
- Zero/tie/defer never turns into a winner, confidence or semantic claim.
- Choice/plan/highlight/download stay hidden until effective20000tick boundary.
- Repeated export validates normal EOF and never overwrites or loosens old readers.

### Task1: Proposal renderer and measured choice pipeline (Sol ownership)

Create `src/fly_connectome_sim/experiment/event_cards.py` and `event_choice.py`;
tests in `tests/experiment/test_event_cards.py` and `test_event_choice.py`;
modify `src/fly_connectome_sim/cli.py`, `tests/test_cli.py`;
create `examples/event-options.json`. No other packaged-source ownership.

Interfaces: `load_event_proposal(path)->validated dict`,
`render_event_cards(proposal)->np.ndarray`; `record_event_choice_run(output_dir,
*,proposal_path,engine_factory)->VerifiedRun`; `export_event_replay(run,output)`
and `export_event_plan(run,output)` return their published object. Shared reduction
uses the exact contracts in spec, no choice override. Keep proposal/render helpers
small; don't refactor the existing recorder/neural core or generic trust model.

- [x] RED/GREEN strict proposal/deepcopy/renderer/±choice/defer/mutations and CLI
  tests, including a genuine tiny-native deferred sealed roundtrip.
- [x] Implement bounded source-bound production/semantic exports/plan assembly;
  preserve all old command/schema/core behavior and successful-append semantics.
- [x] Run focused old/new backend/CLI and relevant recorder/replay compatibility;
  freeze all packaged/owned bytes/schema/results, no actual fullgraph by worker.

### Task2: Event-board replay and plan presentation (separate Sol ownership)

Own `viewer/**` only. Add `event-replay.ts` and minimal dispatcher if needed;
modify existing main/stage/index/style/export helpers and focused tests.
Keep original A/B/video readers strict; avoid cyclic imports and broad redesign.

Interfaces: closed event-choice-replay/v1 from spec, same source/groups/input/bin
shapes; `sampleEventAtTick` reveals decision/plan only at20000. Optional bounded
terminal-hold parameter on shared writer defaults15; event uses90. Render actual
paired pixels on a landscape board, highlight selected side only after decision,
plain-text plan/defer panel and bound plan download. No semantic fly gesture.

- [x] RED/GREEN strict event parser/mutation/defer/no-early-plan/hold tests;
  old reader/export/operation tests remain valid.
- [x] Implement deterministic board/result rendering and download,90-frame hold
  with accurate labels, shared interactive/export path, proper cleanup.
- [x] Run all viewer tests/build; freeze complete first-party viewer bytes and
  results, no server/browser/native/Git mutations by worker.

### Task3: Independent review and actual vertical acceptance (root)

- [x] Architecture/scientific/untrusted-proposal authority preflight; settle
  builder details without weakening the contract or requesting routine approval.
- [x] Independent frozen backend security/integrity and viewer reviews; fix
  Critical/Important findings and obtain scoped closure before actual native work.
- [x] One max2s/120s actual pilot, seal/verify/both exports; independent raw/
  renderer/count/window/decision/plan audit, accepting selected or deferred.
- [x] Same-artifact Chrome board/decision/plan/download checks and actual encoded
 150frames/5s audit, including delayed reveal and labelled held source endpoint.
- [x] Add proposal prompt/how-to, update status/handover/report, inspect complete
 first-party staged diff; reviewed feature commit/push and pause at clean milestone.

## Checkpoint evidence

Backend307passed/310deselected and separate79passed (overlap, no skips);
viewer83passed/0skip/build0. Source reviews: backendC0/I0/M1 (foreign raw-run
pre-allocation hardening deferred), viewer initialC0/I1/M2 → scopedC0/I0/M0.
One actual2s run14.687s exited0:final left2/right1 → Sunset House; raw/pixel/
count/plan checks and actual Chrome150frame/5s export passed. Exact commands,
hashes and limitations: [report](../../experiments/2026-11-02-event-choice-observation.md).
No live API call or scientific/formal qualification acceptance is claimed.
Final independent release/evidence consistency review closed C0/I0/M0; the
documented foreign-run intake and interactive orbit-hint polish TODOs remain.
