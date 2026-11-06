# Replay controls and phase announcements

> **For agentic workers:** Use superpowers:subagent-driven-development and test-driven-development. Continue the existing authorized feature checkout; no new dependencies or worktree.

**Goal:** Make the existing replay easier to operate by keyboard and communicate
phase/result changes without obscuring the measured canvas.

**Architecture:** Narrow HTML/CSS/main changes, using the existing DOM and tests.
Measurement parsers, stage geometry, exports and simulator remain unchanged.

**Spec:** Existing [session contract](../specs/2026-11-03-feed-event-session.md)
plus the bounded behavior below. This small UI contract is controller-chosen
under the user's autonomous continuation authority; no new product decision.

## Binding behavior

- Move the stage orbit hint into normal document flow below the canvas, so it
  cannot cover the canvas event overlay. Preserve responsive desktop/mobile sizing.
- Visible help describes canvas-focused Space play/pause, Left/Right100ms,
  Home beginning and End terminal sample. Connect canvas via aria-describedby.
- Keyboard handlers act only on the focused canvas, ignore modified shortcuts,
  suppress repeated Space toggles, and do nothing during loading/export or without
  a recording. Recognized active shortcuts prevent browser default; other controls
  retain their native keyboard behavior. Home/End update the same real timeline.
- Dedicated visually hidden polite atomic live region announces feed clip,
  pending paired options, selected option or deferred result. Write only when
  the message changes, never on every animation frame; reverse seek clears any
  later winner and announces the earlier phase. A/B recordings get an appropriate
  stimulus message. No new scientific interpretation or automatic focus changes.
- No .py/.cpp/schema/package/dependency/parser/export/stage changes. Reuse actual
  local continuous replay for browser QA; no API, graph download or native run.
- This is scoped keyboard/announcement/layout improvement, not full screenreader,
  mobile, cross-browser or WCAG certification.

## Review focus

Busy loading with an old recording cannot change clocks via keyboard; export
cancellation/ownership remains unchanged. Pending/reverse/deferred announcements
must not retain a winner. Announcements must not flood on idle frames. Normal
controls must keep native key handling. Help must lie outside measured pixels.

### Task 1: Viewer controls (Sol)

**Own:** viewer/index.html, viewer/src/main.ts, viewer/src/style.css,
viewer/tests/session-replay.test.mjs; event-replay tests only if genuinely needed
for existing harness compatibility. Others own docs; do not revert other edits.

- [x] Add meaningful real-main control-flow failing tests for Home/End/arrows,
  repeated/modified Space and loading/export rejection, plus pending/result/
  reverse/defer announcements and no repeated live-region write at equal sample.
- [x] Record actual RED command/result, implement smallest matching change.
- [x] Run full viewer test suite and pinned local npm build once on final source;
  freeze owned files and unchanged backend/dependencies, report exact outcomes.
- [x] Independent fresh Sol review, fix/re-review any Important/Critical findings.

### Task 2: Same-data browser QA and publication (controller)

- [x] Reuse runs/feed-event-replay-20261103.json in actual Chrome; verify keyboard
  navigation, pending/selected/reverse DOM, layout/help outside canvas and a
  narrower responsive viewport if available via documented browser controls.
- [x] Inspect screenshots and save local evidence; do not call DOM-only tests
  audible screenreader evidence or generate another native/export run.
- [x] Update tracked handover and brief acceptance note with commands/results,
  limits and exact unchanged model identity. Review complete staged delta/size.

Publication: commit per AGENTS, push named feature, verify clean tracking/remote,
then pause. Actual commit/push evidence is Git and the private recovery ledger.
