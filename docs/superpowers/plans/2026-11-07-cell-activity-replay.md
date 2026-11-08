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
Implementation, independent source/data review and actual session/film acceptance
are complete. The final documentation review is approved; the checkpoint is
recorded below.

## Constraints and review focus

- Maximum 256 fixed cells, 512 fixed directed edges; selection precedes activity.
- Counts in complete original bins; display sums complete 100ms windows only.
- Same checkpoint state, clocks, scientific telemetry and choice with capture
  enabled or disabled. Runtime measurement fields are explicitly excluded.
- Validate raw/recording/engine/source bindings and all fully selected group sums.
- Missing coordinates stay missing; zero activity stays neutral; stale or invalid
  optional detail never replaces the current valid attachment or breaks replay.
- One accepted acquisition after review; retain the initial accounting abort and
  explicitly authorized second launch. No automatic retries. Limits: <=10s,
  244 observations, 1160 bins,
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
the host in2.78s. Independent backend review subsequently passed, including the
canonical-recording/exact-inspected-byte binding correction.

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
- [x] Run under external wall/RSS/output supervision; preserve partial
  evidence on failure and never retry automatically.
- [x] Audit every raw bin/window, selected group sum, ID/coordinate/edge, source
  binding and resource receipt independently of producer summaries.

First launch stopped after0.353s: the monitor mistakenly counted older regression
fixtures against the acquisition output cap. No measurement files were produced.
The original attempt/freeze/receipts remain unchanged. Reviewed supervisor v2
requires isolated fresh acquisition evidence and retains all production limits;
both non-neural normal/overflow smoke tests passed. The119-file retry freeze
preserves the original117 bindings and adds the corrected supervisor/test hashes.
The user explicitly authorized the second launch. It completed at
`runs/cell-demo-20261108-02/`: 9 s (7 s feed + 2 s cards), 214 observations,
1,040 bins, 90 windows, final L7/R2 → Sunset Rooftop Social. All 256 cohort cells
are positioned; source/bin/group/topology audits passed. Supervision: 109.223 s,
948,957,184-byte native peak RSS, 47,844,542-byte observed output peak, both exit
codes zero, no cleanup errors. The first failed attempt remains intact.

## 4. Film and reviewed checkpoint

- [x] Load the new recording and bound sidecars; export 30fps film, inspect
  window/feed/card/decision/hold boundaries and complete playback.
- [x] Verify both-side/defer/reduced-motion presentation with synthetic fixtures,
  immutable plan, exact counts, no fabricated activity and readable legends.
- [x] Record new source identity, actual results/limits and API status in the
  experiment report, usage, README and handover. Preserve historical evidence.
- [x] Review the complete explicit staged diff, commit and push only
  `feat/connectome-experiment-core`; check compatibility CI.
- [x] Complete the agreed sequential experimental observation scope; no research
  resumption or further feature expansion is implied.

Actual film acceptance: VP9, 360 frames, 900×900, 12 s at 30 fps, including a
labelled 3 s terminal hold. Chrome playback ended without media error or dropped
frames; the actual 341×1600 narrow view passed. Independent final source/raw/
artifact/frame review approved the result. See the
[accepted report](../../experiments/2026-11-08-cell-capture-api.md).
Reviewed-source [Linux CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42431095712)
passed 185 native/backend tests (one Windows-only skip), 135 viewer tests
(no skips) and build. The final documentation records this accepted evidence;
the research track remains parked.
