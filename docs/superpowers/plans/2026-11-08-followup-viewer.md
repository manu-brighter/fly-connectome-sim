# Follow-up Viewer Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to execute
> the bounded implementation and independent review in sequence.

**Goal:** Display and download the existing German planning companion after the
recorded choice, with local source/file bindings.

**Architecture:** A focused `followup.ts` validates two files and owns attachment
state. Existing `main.ts` wires its controls/display to the current sample.
`anatomy.ts` retains recording byte length alongside its existing first-read hash.
No backend, canvas, dependencies or additional provider requests.

**Tech Stack:** Existing TypeScript/Vite/DOM and Node test runner.
**Spec:** [viewer contract](../specs/2026-11-08-followup-viewer.md).

## Global constraints and review focus

- Current clean feature branch, base1b21af4; preserve other work.
- Follow-up128KiB, receipt16KiB; read only exactly two bounded files.
- Canonical plan/derived session receipt and exact recording/file bytes must bind.
- Before decision, rewind and defer must reveal no selected companion text.
- Async parsing/hashing from old imports must not attach to a new recording.
- Untrusted Unicode/markup must be bounded and text-only; downloaded Markdown
  must match the producer receipt, including escaping and newline bytes.
- Preserve original plan export and all existing scientific/video behavior.

## Task 1 — bounded implementation (Sol)

Own new `viewer/src/followup.ts`, `viewer/tests/followup.test.mjs`; narrow changes
to `viewer/src/main.ts`, `viewer/src/anatomy.ts`, `viewer/src/style.css`,
`viewer/index.html`, `viewer/tests/session-replay.test.mjs`, the existing main
VM import adapter in `viewer/tests/event-replay.test.mjs`, and relevant anatomy
tests if needed. Controller owns docs/browser evidence. No other source changes,
new agents, API calls, simulation, commits or dependency installation.

Interfaces: `FollowupContext` holds validated recording, its raw SHA256 and byte
length. `parseFollowupBundle(files: readonly Uint8Array[], context)` returns a
validated companion plus checked Markdown bytes. `createFollowupAttachment()`
matches existing attachment methods: value, setRecording, cancelPending, load;
check generation/request after every asynchronous parsing stage before publish.
Reuse existing sample.plan gating in main; never change numerical/choice code.

- [x] Write/run failing parser/binding/Unicode/receipt/Markdown tests.
- [x] Implement bounded parser, renderer and generation-safe attachment.
- [x] Add real-main control-flow tests for predecision/final/rewind/defer,
  invalid/late imports, recording replacement and export/download controls.
- [x] Add the section and wire it through existing controls; retain style.
- [x] Run focused tests, full viewer suite and build; record counts/skips.
- [x] Independent Astra review; fix findings with failing regressions first.

## Task 2 — actual browser acceptance and publication (controller)

Consumes Task1's unchanged local artifact/import/download contract.

- [x] Inspect actual desktop/narrow browser layout with accepted files.
- [x] Check actual pending/final/rewind/defer/replacement behavior, downloads,
  console/network and original source hashes; preserve screenshots/evidence.
- [x] Update usage, report and current handover; independently review results.
- [x] Inspect explicit staged diff; reviewed feature commit/push and observe CI.

Accepted feature checkpoint: `46e0200c2a94c88f984f8c4b5f65617e8cdffa94`.
[CI 42522727223](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42522727223)
passed: 151 viewer tests / 2 private-artifact skips and build, 343 backend/native
tests / 8 skips. Local viewer suite: 153 passed, no skips. See the
[acceptance report](../../experiments/2026-11-08-followup-viewer.md).

Self-review: Task1 source/interfaces agree with its tests and the spec. Task2
consumes those interfaces and owns no concurrent source edits. No new provider
or scientific authority is introduced by importing local files.
