# Live Drink Market Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development sequentially. Sol implements bounded
> tasks; Astra reviews difficult architecture, protocol and integrity questions.
> Keep one implementer and at most one reviewer active. Preserve others' edits.

**Goal:** Establish the live drink market's feasibility before building the
public event application, beginning with a reproducible offline evidence inventory.

**Architecture:** Reuse the existing native engine without modifying its package.
A separate future market application owns price state, real-time cooldowns,
uploads and live presentation. Stage A below is executable in isolation; Stages
B–E define dependent deliverables and gates, not premature implementation tasks.

**Tech Stack:** Stage A: existing Python 3.12, standard library, recorder verifier
and pytest. Later: existing Python engine, separate application under `market/`,
and a TypeScript presentation using the current viewer's rendering principles.
Server framework and transport are selected in the later service specification;
none is installed or implicitly approved by this plan.

**Spec:** [Live-Getränkebörse](../specs/2026-11-09-live-drink-market-design.md).

**Status:** User approved sequential execution until finished or stopped on
November 9. Stage A implementation and historical evidence are independently accepted locally; no new native observation,
learning experiment, paid request or deployment has started. The user supplied
10–20 drinks, 50–300 guests, usually 6–8 hours with shorter or approximately
12-hour exceptions. Keep duration configurable; use 12 hours as the initial
later soak-test reference, not an automatic runtime cap. Upload rate and
acceptable delay still need an explicit load model before that test.

## Global constraints

- Branch `feat/connectome-experiment-core`; documentation base `462f7a5`.
- Full minimum-to-maximum jumps are allowed; **no CHF0.50 per-change cap**.
- At least **30 minutes of real time** between actual changes of the same drink.
- Expiry permits a fresh decision; it neither forces nor queues a price change.
- Model chooses drink, target and decision timing. Guests cannot pick a drink.
- Staff reads the authoritative board; no POS integration in the first pilot.
- Target all 20 drink slots at the upper stated size; do not quietly reduce the
  product to the number of existing population channels. Guests: 50–300.
  Runtime: configurable, typical 6–8 hours, initial long-run reference 12 hours.
- Proposed activation: durable server-side price version, automatically applied;
  no per-change staff confirmation. Pause remains available.
- Proposed first version: `learning=False`, no external DAN stimulation, normal
  continuous state and passive decay. Research remains a separate later choice.
- Every scheduled interval advances the model, including explicit black RGB
  `uint8`; an observation is at most 500 ms. Real and model time stay separate.
- No package `.py`/`.cpp`, graph-lock or upstream-notice edits for Stage A.
  Additional modules inside the package would change its source fingerprint too.
- No second simulator, hidden random price selection, LLM price override, native
  replay-attestation claim or scientific qualification inferred from hashes.
- Tests use declared synthetic fixtures; actual measurements remain separately
  identified. No raw records, private images or `.tools/` material in commits.
- Preserve the completed observation demo, its five-file import and evidence.

## Review focus

1. Hash-valid but semantically inconsistent bin/rate data: reject instead of
   publishing plausible numbers (Stage A Task 1).
2. Unequal observation lengths, empty populations or zero activity: retain correct
   denominators and report absence without inventing decisions (A1).
3. Missing, oversized, malformed or branched input and duplicate output: fail
   without writing a success report or touching source evidence (A1).
4. Historical timing and integrity verification: never label them live throughput,
   independent resource monitoring or multi-drink qualification (A1/A2; Stage B).
5. Later stale signals, disconnected boards and restart: keep committed prices,
   preserve per-drink cooldowns, reject old/duplicate proposals, clearly mark an
   unknown display state (Stage C's mandatory contract tests).

## Existing boundaries verified for planning

- `src/fly_connectome_sim/engine.py`: `FlyEngine.from_prepared_graph()` and
  `observe(frame, duration_ms, *, stimulation=None, current_mv=20.0,
  learning=False, pathway_detail=False, qualification_detail=False)` provide
  ongoing state, seven population counts and original native bins.
- `configure_cell_observer(indices, callback)` permits a fixed cohort of at most
  256 cells before the first advance. It can feed a future bounded stream.
- `experiment/adapter.py::LateralMotorAdapter.adapt()` provides only
  left/right/defer. Its evidence strength is not an independent price signal or
  a calibrated confidence. Seven recorded groups are not seven proven channels.
- `experiment/recorder.py::verify_run()` streams sealed records and checkpoint
  hashes without loading a graph or executing the native model. Imports alone do
  not construct an engine. It does not validate all bin/rate arithmetic.
- Existing session, cell writer and viewer readers intentionally accumulate
  bounded recordings. The cell writer retains bins in memory; the cell viewer is
  limited to 10 seconds. Do not turn them into live services by raising limits.
- There is no tracked general process supervisor or HTTP service. The historical
  local PowerShell supervisor is not a portable dependency for new work.

## Stage A — offline population and timing inventory

Deliverable: one bounded, repeatable report from a sealed recorded run. It answers
what was measured and what remains missing, not whether the proposed market works.
No cell reconstruction, new drink mapping, price prediction or recalibration.

### Task 1 — bounded analyzer and public tests (Sol)

**Files:**

- Create `scripts/analyze-market-feasibility.py`.
- Create `tests/test_market_feasibility.py`.
- Modify `.github/workflows/compatibility.yml` only to include that test in the
  existing Python test command. Do not modify package sources or dependencies.

**Interfaces:**

- Reuse `verify_run(path, *, limits: RunReadLimits | None = None) -> VerifiedRun`.
  Read `run.manifest`, `run.verification_mode`, `run.iter_events()` through EOF.
  There is no `run.metadata` attribute.
- New `analyze_recorded_run(run_directory: Path) -> dict[str, object]` returns a
  JSON-safe report only after complete validation.
- New `write_report(report: dict[str, object], output_path: Path) -> None` writes
  exclusively to a new file after validation. Existing files, including dangling
  links, must not be overwritten. Failed writes must not leave a success report.
- CLI: `--run-dir PATH --output PATH`; no source auto-discovery, native mode,
  network mode, interactive prompt, permissive verification flag or limit override.

**Input and limits:**

- A sealed run directory with `run.json`, `events.jsonl` and the checkpoints
  referenced by its manifest; no runtime arrays, images or viewer sidecars needed.
- Use `RunReadLimits(2 MiB manifest, 1 MiB line, 64 MiB events, 246 events,
  2 checkpoints)` with the actual named constructor fields:
  `max_manifest_bytes`, `max_event_line_bytes`, `max_events_bytes`, `max_events`,
  `max_checkpoints`. Additionally reject checkpoint files above 64 MiB each
  before hashing. Never follow caller-supplied paths outside the sealed run.
- Restrict this first analyzer to one branch and uninterrupted observations.
  Reject reset/restore/branching semantics instead of merging incompatible clocks.
- Inspect `event["type"] == "observe"`, its `start_tick`, `end_tick`,
  `duration_ticks` and `telemetry`. One tick is 0.1 ms. Require coherent observation
  clocks, interval <=500 ms, nonempty bins, contiguous bin coverage and bins <=10 ms.
- Group membership and sizes come from
  `manifest["metadata"]["engine_identity"]["neural_groups"]`. Require the seven
  groups `pam11`, `ppl101`, `kc`, `mbon07`, `mbon11`, `motor_left`, `motor_right`.
  Validate group declarations and reject an empty required group before division.
- Counts come from `telemetry["bins"][i]["group_spikes"][group]`; require
  nonnegative integer counts, reject booleans and non-finite numeric inputs.
  Verify rates against total counts / (population size × duration in seconds)
  with `math.isclose(rel_tol=1e-9, abs_tol=1e-9)`. Check all expected group keys.
- Require `learning=False` and no external stimulation in both event and telemetry.
  Reject incompatible records rather than describing them as the recommended mode.

**Report contract:**

- `format`: `fly-market-feasibility/v1`; `verification_mode`: `integrity-only`;
  `scope`: `historical-population-inventory`.
- `source`: the inspected manifest's `schema_sha256`, `run_metadata_sha256`,
  `events_sha256`, `final_scientific_sha256`, run kind and declared engine identity.
  These describe the historical source, not a claim of current-source equivalence.
- `observations`, `bins`, `simulated_ms`, phase durations derived from events.
- `groups`: per-group size, spike total, duration-weighted mean rate, minimum and
  maximum native-bin rate, zero/nonzero bin counts. Report membership overlap;
  do not infer functional independence from distinct group names or members.
- `timing`: finite nonnegative sums of recorded `compute_seconds` and
  `kernel_seconds`, plus each sum / simulated seconds; zero duration is invalid.
  These are recorded historical fields, not a new benchmark or supervisor result.
- `limitations`: no single-cell inference, no new learning evidence, no validated
  drink selection/price mapping and no long-run or real-time qualification.
  There is deliberately no overall scientific or market-feasibility pass flag.

- [x] Write synthetic `RunRecorder` fixtures with explicit test metadata and
  hashed dummy checkpoint bytes; use the recorder's public ingest/seal interfaces.
  No native fixtures, private-run discovery or downloaded graph dependency.
- [x] Write `test_weighted_population_summary`: two contiguous observations of
  100 and 200 ms, population size 2 and spike totals 2 and 8 must yield
  `observations == 2`, `simulated_ms == 300`, `spikes == 10`,
  `mean_rate_hz == pytest.approx(10 / (2 * 0.3))`; derive matching bin coverage.
  Other required groups may be silent and must retain zero counts/rates.
- [x] Write focused cases for altered bytes/hash failure; hash-valid rate
  mismatch; bin gaps/overlap/wrong coverage; missing/empty groups; NaN/Infinity,
  booleans and negative counts; nonzero learning/stimulation; discontinuous
  branches; declared limit excess and oversized checkpoints.
- [x] Write CLI cases proving invalid input emits no report, output collision or
  dangling output link never overwrites, valid report labels all limitations,
  and a no-native/no-network guard fails the test if either path is invoked.
  Platform-specific link privilege skips must be stated, not counted as passes.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_market_feasibility.py -q`
  and record the actual expected RED failures before implementation.
- [x] Implement the script's two interfaces and CLI using existing verifier
  patterns. Consume the full checked event stream before publishing the report;
  do not calculate statistics from a prefix and label the whole run checked.
- [x] Run the focused suite GREEN, then together with
  `tests/experiment/test_recorder_limits.py`; add the new test to CI. Record real
  commands/counts/skips. Do not run unrelated neural acquisitions as regression.
- [x] Astra independently reviews source, input binding, arithmetic, bounded
  reads and claims. Fix actionable findings test-first within these owned files.
- [ ] Inspect complete explicit staged diff; make a reviewed feature commit.

### Task 2 — actual historical report and checkpoint (controller)

**Files:** Create `docs/experiments/2026-11-09-market-feasibility.md` only when
the report has actually run; update this plan's checkboxes and
`docs/cloud-handover.md`. Local JSON/evidence stay ignored under `runs/`/`.tools/`.

**Consumes:** Task 1 CLI and report contract. **Produces:** reviewed evidence
summary, clear missing measurements and the input to Stage B's bounded protocol.

- [x] Run exactly the offline analyzer against the existing accepted raw run:

  ```powershell
  .venv/Scripts/python.exe scripts/analyze-market-feasibility.py --run-dir runs/cell-demo-20261108-02/session/run --output runs/market-feasibility-20261109.json
  ```

  If the output already exists, select a new explicit filename; never overwrite.
  If the private original is unavailable, report that limitation and stop actual
  acceptance. Synthetic CI success cannot substitute for historical evidence.
- [x] Check expected historical scope (214 observations / 9 simulated seconds),
  independently inspect representative arithmetic and verify unchanged source
  bytes/package identity. Report discrepancies honestly; do not force agreement.
- [x] Record available groups, rate ranges/silence/overlap and recorded timing.
  Explicitly state that this single feed/cards run contains no held-out market
  comparison and cannot validate multi-drink control or hours of operation.
- [x] Astra reviews actual report against source evidence; controller records
  conclusions, remaining gaps and the next protocol task in the handover.
- [ ] Review docs and complete staged diff; commit/push explicitly to the feature
  branch and observe CI. No PR, merge, deployment or native run follows implicitly.

**Stage A completion:** analyzer tests and real report accepted, or a documented
unavailable-input outcome. This is a software/evidence checkpoint, not a market
feasibility pass. Stage B cannot be replaced by an attractive synthetic price demo.

## Stage B — separately bounded readout and continuous-operation feasibility

Next deliverable: an exact reviewed measurement protocol and a dedicated runner
outside the package, followed only by an authorized bounded acquisition.

- Specify candidate group/cell channels, channel-to-drink mapping, price function,
  neutral/tie handling, threshold/rearm behavior and exact calibration/held-out
  inputs **before** examining acceptance results. Labels are engineered mappings.
- Measure input sensitivity, channel bias/variety, neutral rate, attainable price
  range, repetitions and ordering/state effects. Compare matched initial states,
  real/black and controlled visual manipulations. Do not reuse calibration images
  as independent confirmation or promise a decision for each upload.
- The protocol fixes numerical acceptance criteria and run budgets before running:
  model duration, wall deadline, native process RSS, disk/log/queue limits,
  independent child monitoring and stop/recovery behavior. No infinite loop.
- Benchmark the intended hardware separately from the readout experiment. Use a
  fixed passive cell callback and bounded rolling buffers; keep advancing black
  intervals. Existing 10-second collectors/parsers must not be expanded into a
  multi-hour store. Declare model time, wall time and measured latency separately.
- Reuse the engine and reviewed supervision principles; do not depend on ignored
  local supervisor paths or alter provenance to make a gate succeed.

**Gate to Stage C:** a reviewed candidate readout on held-out inputs and bounded
performance evidence adequate for a stated latency/load target, with uncertainty
reported. A negative result leads to an explicit concept revision. No random
fallback, fabricated neural decision or automatic switch to a smaller simulator.
Event duration, expected load and acceptable delay are required before sizing
the sustained-operation pilot; they are not invented in Stage A.

## Stage C — price service and local test board

Next subsystem specification/plan lives under the same docs hierarchy; source
lives under `market/`, separate from `src/fly_connectome_sim/` and replay parsers.
Define its state/transport contract after Stage B establishes viable inputs.

- Durable authoritative state: integer Rappen, drink range/grid, current version,
  activation timestamp, per-drink cooldown, event-ID deduplication and pause state.
- Fresh measurement proposals carry identity, model/wall clocks, selected drink,
  target and readout version. Validate independently of the simulator process.
- Check event uniqueness, freshness, range and cooldown in the same state
  transaction as activation. No-op prices do not reset cooldown. Rejected
  proposals are discarded, not retargeted or saved for expiry.
- Automatic activation without per-change staff approval; board presence/freshness
  policy and connection-loss detection bound are explicit configuration. Central
  commit is authoritative; no claim of atomically updating distributed screens.
- Required test cases: CHF 4→7 allowed; at 29:59.999 the same drink is locked;
  at 30:00 a fresh eligible proposal can succeed; other drinks remain independent;
  expiry alone does nothing; restart/duplicate messages/clock uncertainty cannot
  shorten a lock; stale/reordered data cannot replace current state.
- Show current price/version, last change, earliest eligibility and manual pause.
  Separate displays retain a clearly dated last-known state on disconnect and
  reload a full snapshot on reconnect. Do not show an uncommitted candidate as
  a price customers can buy at. Preserve persisted changes after lost delivery.

**Deliverable:** an independently tested local board with synthetic proposals
clearly marked test data. It does not count as neural or public-event acceptance.

## Stage D — bounded uploads, native worker and live display

- Write the service/security specification before exposing an endpoint: upload
  size/pixel/type limits, decode isolation, queue/backpressure, retention,
  publication moderation and private operator controls. Choose exact finite values
  for the stated pilot load; do not accumulate data for the whole evening in RAM.
- Connect a long-running engine worker with explicit black intervals, no resets
  between uploads, versioned bounded telemetry and a separate price controller.
  Worker slowness or failure must never block the real-time cooldown or pause.
- Guests see accepted/queued/processed/rejected status. The screen presents the
  actually processed image, associated measured data, latency and decision status.
  Measured activity, static edges and illustrative animation remain distinct.
- Reuse useful rendering components only after assessing their interfaces. Keep
  current replay formats and historical evidence unchanged. There is no reason to
  put live messages through `parseAnyRecording()` or remove its limits.
- Test oversize/malformed uploads, overload, disconnection, worker failure,
  late telemetry, admin authorization and bounded storage. Independent security
  review is required before public exposure, along with protocol/source review.

**Deliverable:** integrated local pilot with real measured proposals and honest
latency/status; no public deployment or automatic paid API use.

## Stage E — rehearsal and first bar pilot

- Fix actual drink count/list, initial/range/grid prices, intended event duration,
  hardware, audience/load, moderation responsibility and acceptable latency.
- Rehearse without sales for the intended duration/load, including restart,
  network/display failure, manual pause and recovery. Verify prices and cooldowns
  against the durable log and observe memory/disk/queue behavior.
- Review evidence and bar workflow. The initial sales pilot uses one authoritative
  board and manual price adoption; staff can stop the market. No POS integration,
  live learning, purchase optimization or unannounced global price-change rule.
- Deployment and actual event operation are separate actions, not authorized by
  completion of a software task. A research-learning plan remains separate too.

## Self-review and next action

Spec coverage: accepted pricing/selection/bar rules map to Stage C; neural
readout and performance unknowns to A/B; live images/brain display and upload
controls to D; actual event configuration and rehearsal to E. Learning options
remain deliberately outside the first version. Every review focus has an owning
test task or a mandatory test contract in its later subsystem.

Only Stage A is detailed enough for the next implementation assignment. Later
subsystem plans must consume measured results rather than invent viable readouts,
resource budgets or display-service contracts now. Stage A checks reflect actual
local implementation/evidence; publication and CI remain pending until observed.
The chosen execution method is already Sol implementation plus Astra review;
there is no need to ask the user to select that method again.
