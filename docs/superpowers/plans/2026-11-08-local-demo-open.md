# Local Demo Open Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development sequentially;
> Sol implements, Astra independently reviews. Keep the existing small agent team.

**Goal:** Open the five existing local demo files together with one selection.
**Architecture:** A bounded candidate loader composes current parsers and isolated
attachment controllers. Main commits the prepared state only after complete
validation. A Node copy command reuses that validation and writes exact snapshots.
**Tech Stack:** Existing Node 24, TypeScript/Vite/DOM and Node test runner.
**Spec:** [local demo contract](../specs/2026-11-08-local-demo-open.md).

## Global constraints

- Feature branch `feat/connectome-experiment-core`, clean base `3e4e996`.
- Exactly five role-named files; current per-role caps and all binding checks.
- No new dependencies, numerical sources, graph locks, API calls or native runs.
- Do not modify raw inputs; output is new/exclusive and contains only five files.
- Keep current individual load paths, exports and scientific/illustrative labels.

## Review focus

- Wrong set or late file read must not replace part of a previously valid demo.
- Nested async hashes and superseded individual imports must not publish stale state.
- Oversized/duplicate/unknown inputs must fail before reads and output writes.
- Copy failure or existing output must never overwrite/delete files or claim success.
- Pre-choice/rewind must not expose the final companion through combined import.

## Task 1 — combined viewer and preparation command (Sol)

Ownership: create `viewer/src/demo.ts`, `viewer/tests/demo.test.mjs`,
`scripts/prepare-demo.mjs`, `viewer/tests/prepare-demo.test.mjs`; modify
`viewer/src/main.ts`, `viewer/index.html`, and narrowly existing main VM tests
in `viewer/tests/session-replay.test.mjs` and `event-replay.test.mjs`.
Existing style should suffice; a narrow `viewer/src/style.css` change is allowed.
Controller owns docs/evidence. Do not change attachment parser contracts unless
a concrete issue requires controller review first. Do not revert others' edits.

Interface: `readDemoFiles(files)` accepts File-like `{name,size,arrayBuffer}`
entries and returns a fully checked candidate, including exact input snapshots,
parsed recording and independently initialized attachment controllers. Use
`createAnatomyAttachment`, `createCellActivityAttachment`,
`createFollowupAttachment` and `assertCellAnatomy` without trusting filenames
as validation. Expose per-role limits for the script preflight. Main's common
recording installation consumes the candidate without asynchronous side effects;
individual recording loading continues to clear old optional layers.

- [x] Write failing bounded loader tests for accepted arbitrary ordering, raw
  bytes, wrong/mixed bindings, duplicate/missing/extra files and pre-read limits.
- [x] Implement `readDemoFiles` with isolated candidates and existing checks.
- [x] Write real-main failures for atomic commit, prior-state retention, empty
  picker, stale success/error and recording/demo/export replacement races.
  Include anatomy/cell catch/finally after a failed replacement followed by a
  new attachment import; old recording identity alone must not pass the guard.
- [x] Add Open demo controls and share narrow installation/render helpers;
  gate attachment and export work through the existing operations.
- [x] Write script failures for invalid input (no output), existing/dangling-link
  output (no overwrite), exclusive copied bytes and exactly five destinations.
- [x] Implement preparation script with validated immutable snapshots and
  explicit CLI arguments; bound handle reads to expected size plus one byte,
  reject growth/truncation and record platform-dependent test skips honestly.
- [x] Run focused tests, then `npm test` and `npm run build` in viewer. Record
  actual RED/GREEN logs and final counts under `.tools/local-demo-open-20261108/`.
- [x] Independent Astra review; fix actionable findings test-first, scoped rerun.

## Task 2 — actual acceptance and publication (controller)

Consumes Task 1 command, five-file folder and complete candidate/UI contract.

- [x] Prepare a new ignored folder from existing accepted files; compare exact
  hashes/lengths and recheck unchanged originals/package fingerprint.
- [x] Actual browser one-selection import, layers, choice/rewind, invalid mixed
  combination retention, downloads, desktop/narrow layout and local-only requests.
- [x] Independent actual evidence/visual review; document limits and commands.
- [ ] Update report/current handover/TODOs, inspect complete explicit staged diff,
  reviewed feature commit/push and observe CI; preserve ignored evidence locally.

Self-review: one coherent five-file contract covers parser, UI and script; each
review focus has a Task 1 regression and Task 2 actual acceptance where relevant.
No unrelated platform, research or source-identity change is introduced.
