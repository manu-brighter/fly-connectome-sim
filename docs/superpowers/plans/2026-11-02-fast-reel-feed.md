# Fast Reel Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Feed genuine5x reel content through the existing engine for3–4s per
clip, and replay a simple200ms recorded-action swipe at normal simulation speed.

**Architecture:** Add one closed fast-feed/v2 profile to the existing video
pipeline while preserving exact standard/v1 behavior. Share preparation,
recorder/exporter and frontend validation/rendering; no new simulator/dependency.

**Tech Stack:** Existing Python3.12/PyAV19.0.2/native C++, TypeScript/Three.js/
Mediabunny and Node24 viewer tests.

**Spec:** [Fast reel contract](../specs/2026-11-02-fast-reel-feed.md).

## Global constraints

- Profile v2: source_speed[5,1], source_window_seconds20, minimum_dwell_ticks30000;
 120 frames,4s clip cap,8s session cap. Keep v1 recipe exact.
- Advance all consumed simulation intervals; no learning/external stimulation,
 thresholds unchanged. Media sampling5*j/30, simulation half-up0.1ms at30Hz.
- 200ms screen/leg transition only after recorded ADVANCE; no extra ticks/input.
- One actual max8s/240s-wall pilot only after source freeze/review; ignored outputs.
- Preserve scientific provenance/locks, parked formal gates and protected Git.

## Review focus

- Short video covering4s but not20s fails before engine construction.
- Mixed v1/v2 speed/coverage/recipe/PTS is rejected; old exports stay readable.
- Decisions before3s, at4s and at8s retain causal priority and next input.
- Transition never exposes future input or persists after200ms; STOP/reduced
 motion/backward seek remain exact, no resources added per animation frame.
- Render/export uses the same normal simulation clock, distinct from5x source PTS.

### Task1: Closed backend profile (Sol ownership)

Files: `src/fly_connectome_sim/experiment/video_observation.py`,
`video_policy.py`, `src/fly_connectome_sim/cli.py`,
`tests/experiment/test_video_observation.py`, `test_video_policy.py`, `tests/test_cli.py`.

Interfaces: `record_video_observation_run(...,profile="standard")` and
`prepare_playlist(...,profile="standard")`; CLI `--profile standard|fast-feed`.
Exporter infers versions from stored metadata. Same payload shape and v2 recipe
defined in spec; shared helpers preserve existing v1 default tests/callers.

- [x] Add genuine20s decode/5x PTS/RGB/short-input, v2 policy/roundtrip/mutation
  and CLI forwarding/default tests; witness meaningful RED.
- [x] Implement two closed profiles and shared profile-aware decode/production/
  export validation. Do not alter native core/schema/dependencies or v1 semantics.
- [x] Run focused old/new backend+CLI tests; check actual two sources prepare
  successfully without native execution; freeze exact packaged/test bytes/results.

### Task2: Versioned viewer and quick swipe (separate Sol ownership)

Files: `viewer/src/video-replay.ts`, `main.ts`, `stage.ts`, `motion.ts`, relevant
viewer tests, `index.html`/CSS only as needed. No backend or dependency ownership.

Interfaces: accept old video v1 and closed v2; same source/policy shapes, v2
recipe fields from spec.200ms gesture carries outgoing last-fed ID and current
incoming ID; stage uses bounded clipped composite, main labels Reel5x/sim clock.

- [x] Add failing dual-version/5x PTS/3s dwell/mutation and transition boundary,
  current-incoming/clipping/reduced-motion/STOP/seek/disposal tests.
- [x] Implement shared version dispatch/validation and deterministic200ms phone/
  leg swipe; no new library, fake activity, timer-based actions or clock speedup.
- [x] Run all viewer tests/build; freeze source/results for independent review.

### Task3: Review and actual acceptance (root coordination)

- [x] Independent Astra profile/media-clock/policy/integrity review and Sol
  viewer review; fix Critical/Important and re-review before actual native work.
- [x] Verify frozen bytes, then one first-two-source fast-feed pilot within
 8s/240s; ordinary sealed verification/compact export and independent raw/parser
 checks. Preserve negative/external-limit results honestly; no policy retuning.
- [x] Browser-test/encode the actual artifact; inspect reel progress, clip dwell,
  200ms swipe, pixel/PTS/count samples and actual encoded FPS/final hold.
- [ ] Update README/handover/current TODOs/report, review full staged scope and
  docs/evidence, explicit first-party feature commit/push; pause at clean milestone.

## Actual acceptance checkpoint

Source reviews closed C0/I0/M0;114 backend tests passed in94.32s and63 viewer
tests/build passed. One actual fast-feed run completed in76.734s, preserving
all33 frozen package members. It consumed210 frames/840 bins/7s:3s first clip,
motor-right advance,4s second clip, external-window terminal stop. Independent
source/pixel/count/policy/parser checks passed. The actual Chrome export decoded
to225 VP9 frames/900x900/7.5s, including15 labelled hold frames; its200ms swipe
was inspected at frame92 and completed at frame96. Reuse this artifact; no
additional native/qualification/C1 run is implied. Exact identities/limits:
[fast-feed report](../../experiments/2026-11-02-fast-reel-feed-observation.md).
