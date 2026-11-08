# Recorded cell activity implementation plan

> Execute sequentially with bounded implementation ownership and independent review.

**Goal:** Add real, source-bound cell counts and static directed model connections
to the existing measured replay and exported film.

**Architecture:** A passive Python observer copies a fixed cohort from existing
native bin results. A separate bounded raw writer/exporter composes the current
session workflow; an optional viewer sidecar drives a shared canvas panel.

**Stack:** Existing Python/NumPy/native fixtures and TypeScript/Canvas/Three.js.
No new simulator, dependencies or core C++ changes.

**Spec:** [Recorded cell activity replay](../specs/2026-11-07-cell-activity-replay.md).
The user authorized autonomous sequential continuation. The assay stays parked.

## Constraints and review focus

- Maximum 256 fixed cells, 512 fixed directed edges; selection precedes activity.
- Counts in complete original bins; display sums complete 100ms windows only.
- Same checkpoint state, clocks, scientific telemetry and choice with capture
  enabled or disabled. Runtime measurement fields are explicitly excluded.
- Validate raw/recording/engine/source bindings and all fully selected group sums.
- Missing coordinates stay missing; zero activity stays neutral; stale or invalid
  optional detail never replaces the current valid attachment or breaks replay.
- One acquisition only, after review: <=10s, 244 observations, 1160 bins,
  900s wall, 4GiB peak RSS, 256MiB task output, 16MiB combined detail.
- Export and seeking use the same deterministic drawing path; terminal hold
  freezes measurement time. No transmission, exact spike-time or semantic claim.

## 1. Passive capture and verified sidecar — Sol

Files: `src/fly_connectome_sim/engine.py`, new
`src/fly_connectome_sim/experiment/cell_activity.py`, one entry script under
`scripts/`, focused Python tests and the compatibility workflow selection.

- [x] Add failing tests for real tiny-native observer equivalence, detached
  values, short bins/black frames, fixed selection and exact induced topology.
- [x] Add the optional observer at the existing bin boundary without changing
  reductions, native call order, state dynamics or original telemetry fields.
- [x] Implement fixed cohort/source join and bounded incremental raw capture.
  Compose existing `session_workflow.run_session` through its engine factory.
- [x] Validate/export the closed sidecar from raw detail and exact recording
  bytes; test tampering, missing/duplicate bins, count reconciliation, limits,
  no overwrite, incomplete output and full tiny-native session composition.
- [x] Run focused tests plus existing engine/session/CLI compatibility tests;
  record actual commands, failures, skips and warnings.

Backend test checkpoint: 29 focused tests passed; combined regression170 passed
with4 Windows permission skips. Those4 hardlink/junction cases then passed on
the host in2.78s. Independent backend review remains a separate gate below.

## 2. Count-driven canvas presentation — Sol

Files: new `viewer/src/cell-activity.ts` and tests, existing `main.ts`, `stage.ts`,
`science-panel.ts`, `index.html` and styles as required.

- [x] Test strict loader bindings, malformed/duplicate fields, counts, topology,
  group coverage, original bin boundaries and stale replacement behavior.
- [x] Test first/terminal window, seeking, short-bin aggregation, exact count
  categories and all-zero/missing-coordinate fixtures before implementation.
- [x] Add optional loading, prominent cohort projection, static directed edges,
  schematic exact-count view and coverage/window/measurement legends.
- [x] Use one projection for real cohort/background coordinates and one drawing
  path for viewer/export; retain seven population traces and existing fly/tap.
- [x] Run viewer tests/build; inspect actual 900px and narrow layouts.

Viewer source checkpoint: 135 tests passed, zero skips, 26.682s; build passed.
Astra reviewed the source and synthetic browser layouts, including both actual
proposal texts, their reserved scene viewport and corrected first-paint background.
These fixture previews do not substitute for the new recording/film below.

## 3. Review and single acquisition — Astra review, root execution

- [x] Independently review source/tests/protocol, correct identified defects,
  and record concrete source/fixture/protocol hashes before acquisition.
- [x] Select existing playlist and declared proposal once. Use a validated live
  proposal if ready; otherwise label imported origin honestly. No extra native
  run just to change proposal origin.
- [ ] Run once under external wall/RSS/output supervision; preserve partial
  evidence on failure and never retry automatically.
- [ ] Audit every raw bin/window, selected group sum, ID/coordinate/edge, source
  binding and resource receipt independently of producer summaries.

First launch stopped after0.353s: the monitor mistakenly counted older regression
fixtures against the acquisition output cap. No measurement files were produced.
The original attempt/freeze/receipts remain unchanged. Reviewed supervisor v2
requires isolated fresh acquisition evidence and retains all production limits;
both non-neural normal/overflow smoke tests passed. The119-file retry freeze
preserves the original117 bindings and adds the corrected supervisor/test hashes.
Explicit retry authorization is pending; no automatic second acquisition ran.

## 4. Film and reviewed checkpoint

- [ ] Load the new recording and bound sidecars; export 30fps film, inspect
  window/feed/card/decision/hold boundaries and complete playback.
- [ ] Verify both-side/defer/reduced-motion presentation with synthetic fixtures,
  immutable plan, exact counts, no fabricated activity and readable legends.
- [ ] Record new source identity, actual results/limits and API status in the
  experiment report, usage, README and handover. Preserve historical evidence.
- [ ] Review the complete explicit staged diff, commit and push only
  `feat/connectome-experiment-core`; check compatibility CI.
- [ ] Continue remaining authorized work; no automatic pause after this checkpoint.
