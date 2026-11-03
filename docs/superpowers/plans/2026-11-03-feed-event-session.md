# Continuous Feed and Event Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One real continuous reel-to-event session produces a bound plan and
smooth combined measurement replay.

**Architecture:** Reuse existing engine/recorder, fast-feed and event rendering/
motor rules through small private phase helpers. New closed session producer,
reducer and browser reader preserve strict original public formats. No second
simulator, fabricated old-format phase runs or live LLM dependency.

**Tech Stack:** Existing Python3.12/C++17/Pillow12.3.0/PyAV19.0.2, TypeScript/
Three.js/Mediabunny, Node24; no new dependencies.

**Spec:** [Continuous session contract](../specs/2026-11-03-feed-event-session.md).

## Global constraints

- Base d97e1e8, feature branch only, preserve existing unrelated work/old evidence.
- One fresh engine/factory/recorder/root, no reset/restore/rebase between phases.
- Closed fast-feed≤8s/240frames → four500ms same-image cards without a gap;
  actual global T and final window[T+15000,T+20000], ordinary1Hz adapter/defer.
- External DAN/learning/detailFalse, passive evolution; core/adapter/schema stay.
- At most244observations/246events/1160bins;32MiBreplay/64KiBplan; full EOF.
- Old wrappers/metadata/readers remain strict; source-bearing changes invalidate
  previous formal identities, no learning/native-history/causal-content claim.
- One source-reviewed actual pilot≤10s/240s wall; no selection hunt or assay grid.
-30fps global nearest-half-up source ticks,90terminalholdframes once/3s;
  no intermediate hold/swipe after STOP, old defaults intact.

## Review focus

- A second fresh engine or restored/reset/rebased state must not masquerade as
  continuous execution; actual factory/observe ownership and clock tests pin it.
- Imported fields/phase transitions/resealed evidence cannot override policy,
  chosen proposal or scientific reference; no output before complete EOF.
- Backward seek, loading/export ownership and boundary tick T must switch all
  texture/labels/URL/plan visibility together, without early winner/download.
- Shared helper extraction must preserve exact old acceptance/rejection and
  representative export bytes; no fake metadata/proof projections for reuse.
- Partial/error/large/conflicting paths preserve existing bytes and fail closed;
  hostile arbitrary raw-run allocation hardening remains explicitly separate.

### Task1: Continuous producer and sealed session exports (Sol)

**Own:** new `src/fly_connectome_sim/experiment/feed_event_session.py`,
`tests/experiment/test_feed_event_session.py`; narrowly modify
`experiment/video_observation.py`, `experiment/event_choice.py`,
`src/fly_connectome_sim/cli.py`, `tests/experiment/test_video_observation.py`,
`tests/experiment/test_event_choice.py`, `tests/test_cli.py` as needed.
No core/adapter/recorder/schema/dependency edits. Others own viewer/docs.

**Interfaces:** `record_feed_event_session(output_dir, *, playlist_path,
proposal_path, engine_factory)->VerifiedRun`; `export_session_replay(run_dir,
output_path)->dict`; `export_session_plan(run_dir,output_path)->dict`.
CLI names/closed wire fields and limits are exact in spec. Internal extracted
phase helpers have explicit branch/start/sequence context with original wrapper
constants; communicate their final names/format fixture to root/viewer.

- [x] RED: test genuine tiny-native continuous factory once/no reset/restore,
  actual video/card RGB and contiguous clocks; seal6..246events and same plan;
  exact final counts, defer and declared selected fixtures. Run to intended fail.
- [x] GREEN: implement narrow phase reuse, one continuous producer, exhaustive
  session semantic reduction and atomic no-replace exports/CLI.
- [x] RED/GREEN: phase ordering/boundary/clock/policy/bin/plan/pixel/choice/EOF
  mutations fail; invalid proposal/render/path/allmedia fail before engine/output.
- [x] Run new session tests plus affected old event/video/CLI/recorder tests;
  preserve representative old export bytes. Use unique ignored pytest temp paths.
  Freeze all packaged sources/schema/owned test hashes and actual command logs;
  write true tiny-native wire fixture for independent viewer interoperability.
  No actual fullgraph/browser/Git mutation by worker; hold source frozen.

### Task2: Strict continuous replay and phase rendering (Sol, viewer only)

**Own:** `viewer/**` only: new `src/session-replay.ts` and focused test;
minimal existing reader/helper/recording/main/stage/export/style changes.
No backend/docs/dependency edits; backend may work concurrently on shared spec.

**Interfaces:** `parseSessionRecording(text)->Promise<SessionRecording>`,
`sampleSessionAtTick(recording,tick)` returns existing video or event-compatible
sample primitives with actual global clocks; `isSessionRecording` type guard.
New closed feed-event-replay/v1 per spec; old readers retain old public contracts.

- [x] RED/GREEN: strict session reader derives T from terminal feed STOP, checks
  exact recipes/maps/inputs/clocks/bin/count/policy/decision/plan; reject reordered,
  gapped/incomplete/oversized/overridden records and unknown old/new formats.
- [x] RED/GREEN: samples T−1/T,decision−1/decision,reverse seek; source5× label,
  phone/board/URL/policy panels/outline/download follow current phase. Reuse
  actual textures and existing foreleg gestures after ADVANCE only; no STOP swipe.
- [x] Implement recording dispatcher/main/stage integration and plan download;
  nearest-half-up global export quantizer and90finalholdframes, no intermediate
  hold. Preserve operation guard/cancel/reduced-motion/resource cleanup/old defaults.
- [x] Run all viewer tests/build and actual backend tiny-native fixture parser;
  freeze complete first-party viewer bytes/results/patch, no browser/native/Git.

### Task3: Independent review, actual acceptance and publication (root)

- [x] Architecture/integrity builder preflight; settle routine choices explicitly,
  amend source contract/plan before implementation when needed.
- [x] Independent frozen backend scientific/integrity and fresh viewer reviews;
  fix/review Critical/Important issues before actual fullgraph execution.
- [x] One fresh actual source-frozen≤10s/240s pilot on local original reels;
  verify/both exports/independent raw pixels/global clocks/policy/count/plan audit.
- [x] Same-artifact Chrome phase/seek/download/operation checks and UI movie;
  decode actual30fps frames/PTS around feed end and decision plus labelled3s hold.
- [x] Update README/how-to/current assay/handover/report/TODOs, review actual
  evidence and complete explicit first-party staged diff/size; conventional
  reviewed feature commit, explicit feature push, verify remote/clean state, pause.

## Reviewed checkpoint

Backend640pass/1sandboxjunctionskip215.58s plus separate host junction1pass0.07s;
viewer91pass/0skip/build0. Independent backend/viewer and final release/evidence
checks closed without new findings; known foreign raw-run allocation/orbit-hint
polish remain open. One actual94.735s pilot recorded7s feed+2s cards,final6:2→
Sunset House; source/raw/Chrome/360frame12s combined export passed. Exact
identities/commands/scope: [report](../../experiments/2026-11-03-feed-event-session.md).
No live LLM/API or scientific/formal qualification acceptance is claimed.
