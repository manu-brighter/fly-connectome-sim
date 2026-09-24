# Associative Plasticity Assay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether the declared PPL101-modulated KC→MBON11 state produces a persistent, stimulus-specific MBON11 response change in the MaleCNS-constrained model, then assess lateral motor evidence separately.

**Architecture:** Keep the existing full-graph engine and checkpoint format. Extend the project-owned experiment package from factorized stimuli and schedules through a gap executor, pathway measurements, qualification, an atomic candidate-state intervention, verified run artifacts, a frozen analysis, and held-out execution. The motor adapter consumes measured motor telemetry only after the primary assay is classified.

**Tech Stack:** Python 3.12, NumPy 2.4.6, C++17 native core, pytest, Windows PowerShell; use `.venv/Scripts/python.exe` in commands below (on Unix, `.venv/bin/python`).

**Spec:** `docs/superpowers/specs/2026-09-24-associative-plasticity-pivot-design.md`; retain the broader boundaries in `docs/specs/fly-event-planner.md`.

## Global Constraints

- The primary endpoint is MBON11 response, not preference, learned behavior, or event choice. The maximal positive claim is the model-specific statement in the design spec.
- PPL101-modulated KC→MBON11 plasticity is primary; PAM11→MBON07 is exploratory and cannot rescue a failed primary assay.
- Qualification and confirmation use disjoint seeds and stimulus families. Freeze timing, response window, effect sign, exclusions, effect floor, and analysis version before confirmation.
- All modes begin at identical baseline state and use separately restored copies. Reward-free retention and tests have `learning=False`, no external DAN, and normal passive memory decay.
- Every scheduled interval advances neural time. `stimulus=None` means an explicit black `uint8` RGB frame, including the unpaired DAN pulse; calls to `FlyEngine.observe` are at most 500 ms.
- `no_external_dan` omits only the external pulse; endogenous DAN firing and resulting plasticity are measured, never assumed zero. `reciprocal_pairing` is acquisition from baseline with the opposite paired identity, not reversal learning.
- Inspect `src/fly_connectome_sim/neural/visual.py` before labeling input drive: RGB is a modeled retinal/R8 drive, not calibrated receptor activation. Preserve source/build/graph/provenance locks and MIT attribution.
- Raw data, prepared arrays, checkpoints, pilot/qualification/confirmatory runs and benchmark files stay in ignored runtime locations. Never add them to Git.
- `model_fingerprint()` hashes every packaged `.py`/`.cpp` file. Formal qualification, its checkpoints, the frozen config and confirmation therefore happen only after all source-bearing tasks in this plan are committed. Any later package-source fix invalidates those artifacts and restarts the source-freeze gate.
- Use test-first RED/GREEN per task. After each GREEN, run `.venv/Scripts/python.exe -m pytest`; report any failures. Each commit uses the repository's English `<type> / <title> : Description` convention and explicit paths. Never push a protected branch.
- Do not implement viewer or LLM code in this plan.

## File ownership map

| File | Responsibility |
|---|---|
| `src/fly_connectome_sim/experiment/stimuli.py`, `tests/experiment/test_protocol.py` | New factorized assay stimuli while retaining the existing `SyntheticStimuli`/`synthetic-ab/v1` renderer byte-for-byte. |
| `src/fly_connectome_sim/experiment/protocol.py`, `tests/experiment/test_protocol.py` | Versioned condition names, pairing identity, order, side and explicit simulated schedule including retention branches. |
| `src/fly_connectome_sim/experiment/executor.py`, `tests/experiment/test_executor.py` (new) | Execute every step and neutral gap against `FlyEngine`, checkpoint forks and window aggregation. |
| `src/fly_connectome_sim/engine.py`, `src/fly_connectome_sim/neural/visual.py`, `tests/test_engine_contract.py` | Exact mapped RGB drive, MBON11-input KC activity and opt-in per-bin trace/memory diagnostics; keep default telemetry compact. |
| `src/fly_connectome_sim/neural/brain.py`, `tests/test_checkpoint.py` | Atomic candidate-edge memory snapshot/replace, with validation before mutation. |
| `src/fly_connectome_sim/experiment/qualification.py`, `tests/experiment/test_qualification.py` (new) | Bounded exploratory grid, path/washout gate, runtime benchmark and frozen configuration output. |
| `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `src/fly_connectome_sim/cli.py`, `tests/experiment/test_recorder.py`, `tests/test_cli.py` (new) | Append-only pilot and assay artifacts, strict verifier and CLI. |
| `src/fly_connectome_sim/experiment/analysis.py`, `tests/experiment/test_analysis.py` (new) | Pure, frozen MBON11 endpoint and classification; no exploratory parameter selection. |
| `configs/assay.synthetic.json` (new only after source freeze), `tests/test_full_graph_engine.py` | Frozen held-out protocol and opt-in full-graph confirmation. |
| `src/fly_connectome_sim/experiment/adapter.py`, `tests/experiment/test_adapter.py` | Keep v1 readable; new lateral-motor-only adapter with `evidence_strength`. |

Do not create a second simulation core. New modules above each own one orchestration or analysis responsibility. `src/fly_connectome_sim/neural/circuit.py`, `rule.py`, and `kernel.cpp` remain unchanged unless a failing gate identifies a specific defect and the design spec is revised before confirmation.

## Review Focus

1. A black neutral gap may still retain modeled lamina bias or retinal adaptation; the executor test must assert the exact black input and elapsed simulation, and pathway qualification must measure washout empirically.
2. A paired identity can be confounded with image side/order; protocol tests must vary these independently and confirm balanced schedules.
3. A broad KC average can hide identical MBON11-input patterns; the pathway test must compare the actual `circuit["pre"]` subset for MBON11 edges.
4. A global MBON response gain can move the difference-in-differences; analysis tests must reject it using a third unpaired stimulus C and a prespecified multiplicative-gain residual.
5. A partial memory transplant can fabricate causality; checkpoint tests must reject bad index/shape/nonfinite/out-of-bound states without mutating any of `memory_u`, `memory_w`, or `weight`.
6. Checkpoint forks make global simulated time nonmonotone; artifacts use a global event sequence plus branch-local simulated clocks and explicit parent-checkpoint hashes.

## Gate 0: integrity before qualification

- [ ] Run `.venv/Scripts/python.exe -m fly_connectome_sim.neural.prepare` to regenerate the ignored runtime manifest, then `.venv/Scripts/python.exe -m fly_connectome_sim.data verify-prepared` and `.venv/Scripts/python.exe -m pytest tests/test_checkpoint.py tests/test_native_build.py tests/test_full_graph_engine.py -q`. For the last file's actual graph run, set `$env:FLY_CONNECTOME_SIM_FULL_TEST='1'` and run it separately. Stop at a failed integrity gate; record the cause rather than weakening a lock.

### Task 1: Independent stimulus and protocol factors

**Files:** Modify `src/fly_connectome_sim/experiment/stimuli.py`, `src/fly_connectome_sim/experiment/protocol.py`, `tests/experiment/test_protocol.py`.

**Interfaces:** Keep `SyntheticStimuli` and its `synthetic-ab/v1` bytes unchanged. Add `AssayStimuli(seed, family, width=32, height=32, version="associative-stimuli/v1").frame(identity, *, side="center", color_assignment="fixed") -> np.ndarray`; `family` is explicitly `qualification` or `confirmation`. Add `schedule_from_json()` for the actual legacy `ab-protocol/v2` structure and the new emitted `associative-protocol/v1`. `ProtocolSchedule.create(*, condition, seed, paired_identity, presentation_order, training_side="center", test_side="center", ...)` emits only the new version. Conditions are `training`, `reciprocal_pairing`, `frozen_plasticity`, `no_external_dan`, and `temporally_unpaired`; reject new use of `reversal`/`no_dan` with a migration message. A, B and unpaired C have distinct spatial patterns at the same location and identical per-channel histograms.

- [ ] **RED:** Add fixed historical JSON and frame-hash fixtures for `ab-protocol/v2` and `synthetic-ab/v1`. Add new tests that vary identity, order, side and pairing independently; verify equal per-channel histograms, deterministic family-separated hashes, distinct A/B/C pixels, balanced A/B and B/A orders, explicit PPL101 pairing-trial membership, and renamed conditions. A reciprocal run is a matched schedule with the opposite explicit `paired_identity`, not continuing trained state.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_protocol.py -q`; expected failure is the missing factorized API, not a fixture/import error.
- [ ] **GREEN:** Implement the interfaces above. Use a deterministic permutation of a fixed RGB pixel multiset; any side placement must not crop pixels or change channel totals. New assay code always names a family. Keep each interval's stimulus, stimulation, `learning`, timestamp and duration explicit; offset timing is split into executable intervals in Task 5.
- [ ] Run the focused command, then `.venv/Scripts/python.exe -m pytest`; require all tests green. Review that no MBON/motor outcome or seed choice influenced the new pattern banks.
- [ ] Commit only these three files: `feat / assay-factors : Separate stimulus identity and schedule factors`.

### Task 2: Neutral gap executor and retention forks

**Files:** Create `src/fly_connectome_sim/experiment/executor.py`, `tests/experiment/test_executor.py`; adjust `protocol.py`/its tests only for explicit gap/branch metadata.

**Interfaces:** `execute_schedule(engine: FlyEngine, schedule: ProtocolSchedule, stimuli: AssayStimuli, *, branch_id: str, on_event: Callable[[dict], None]) -> None`; `advance_neutral(engine, duration_ms, shape, *, stimulation=None, learning=False, branch_id, on_event) -> None`; `retention_test(engine, training_end_checkpoint: Path, delay_ms: float, ...) -> tuple[dict, ...]`. All gap calls use `np.zeros((height,width,3), dtype=np.uint8)` and chunk `min(500.0, remaining_ms)` on the 0.1 ms grid. Restore the same training-end checkpoint separately for `T` and `T+60000` branches; each A/B/C test presentation starts from a separately restored retention-end checkpoint to prevent carryover. `T=0` is the later end of the final training presentation and final external DAN pulse, including an unpaired B presentation if it is last.

- [ ] **RED:** In `test_executor.py`, use a recording fake engine to assert 1,201 ms gap calls of 500/500/201 ms, all-zero RGB and matching branch-local simulated timestamps; assert the unpaired DAN pulse also gets black RGB. Add checkpoint-fork tests proving both retention branches start at identical training-end bytes, each A/B/C test forks its retention-end checkpoint, parent checkpoint hashes are recorded, and the `T+60` branch advances exactly 60,000 ms more.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_executor.py -q`; expected failure: missing executor/retention APIs.
- [ ] **GREEN:** Implement the interfaces and events (`fork`, `step`, `neutral_gap_chunk`, `retention_start`, `retention_end`) with branch ID, parent checkpoint hash, input hash, exact branch-local time, stimulation and `learning`. Reject negative/nonfinite/off-grid durations before mutating the engine. Never skip the interval between scheduled timestamps or rewrite scientific clocks to make different branches appear monotone.
- [ ] Run focused then full pytest. Review exact `T` reference, no external DAN and `learning=False` in both retention branches and tests.
- [ ] Commit executor, tests and any protocol adjustment: `feat / neutral-executor : Advance every scheduled gap and fork retention tests`.

### Task 3: Pathway observability at the actual MBON11 inputs

**Files:** Modify `src/fly_connectome_sim/neural/visual.py`, `src/fly_connectome_sim/engine.py`, `tests/test_engine_contract.py`; add focused opt-in graph assertions to `tests/test_full_graph_engine.py`.

**Interfaces:** Add a pure `VisualMemoryBrain.rgb_drive(frame) -> dict[str, np.ndarray]` that returns the *modeled* sampled R1–R6 luminance and R8 channel input before neural state advances, with no mutation. Add `FlyEngine.observe(..., pathway_detail=False, qualification_detail=False)`. `pathway_detail` returns drive summaries and per-neuron spike counts keyed by stable source ID for the ordered unique KCs on candidate edges whose postsynaptic target is MBON11. `qualification_detail` augments every existing ≤10 ms bin with ordered `rate_kc` values for those candidate edges, ordered `rate_dan` values for `circuit["dan"]`, candidate `memory_u`/`memory_w` summaries and hashes, efficacy summary, and lower/upper-bound hit counts. Label `rate_kc`/`rate_dan` as model trace state rather than raw spikes. Default telemetry remains byte-for-byte compact.

- [ ] **RED:** Assert `rgb_drive` does not change `sim_ms`, `luminance` or `r8_light`; verify RGB geometry changes mapped drive; verify a tiny circuit's MBON11-input KC set excludes KCs connected only to MBON07 and all edge/DAN/source-ID orderings are deterministic. Force a transient bound hit that disappears by the endpoint and prove an opt-in bin still records it. Assert default telemetry has no candidate vectors or trace state.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/test_engine_contract.py -q`; expected failure is missing observability API.
- [ ] **GREEN:** Reuse the exact sampling expressions in `visual.py`'s `rgb_step` and `sensory.retinal_samples`; factor them into a pure helper without changing numerical equations. Snapshot diagnostics immediately after each internal neural bin, before the next advance. Aggregate KC counts from existing totals and label drive as `modeled_visual_drive`, never receptor occupancy/activity. Define saturation as any bin at a rule bound and retain the maximum bound-hit fraction as well as endpoint values.
- [ ] Run focused and full pytest, then opt-in `FLY_CONNECTOME_SIM_FULL_TEST=1` test. Review identical default spike/state hashes before and after the refactor; any difference is a gate failure.
- [ ] Commit these files: `feat / pathway-observability : Expose modeled visual drive and MBON11-input KC activity`.

### Task 4: Atomic MBON11 candidate memory intervention

**Files:** Modify `src/fly_connectome_sim/neural/brain.py`, `tests/test_checkpoint.py`; `executor.py` only to orchestrate branches.

**Interfaces:** `MemoryBrain.candidate_memory(target_indices: np.ndarray) -> CandidateMemory` derives the ordered KC→target candidate edges and returns copies of edge indices, `memory_u`, `memory_w`, and `weight`. `replace_candidate_memory(snapshot)` validates exact edge identity/order, shape, dtype, finite rule bounds and `weight == baseline_plastic * (1 + memory_w)` within float32 rounding, then assigns all three arrays atomically. No other neural state, trace, clock or weight changes.

All causal interventions occur at the common training-end clock. The donor is the trained branch; the recipient/baseline branch saw identical images, intervals and external-current-free trial structure with `learning=False`. Apply necessity, sufficiency and sham at that clock, then advance every branch through the identical full retention interval with `learning=False`, no external DAN and `weights_frozen=False`, so normal passive `u/w` decay continues.

- [ ] **RED:** On the four-neuron fixture, assert necessity (matched baseline triplet into trained), sufficiency (trained triplet into matched recipient) and sham preserve every noncandidate state hash, trace, cursor and clock at intervention time. Parameterize unequal donor/recipient clocks, bad edge order, duplicate/missing edge, wrong dtype/shape, NaN, out-of-bounds `u/w`, and inconsistent weight; rejection leaves all three live components byte-identical. Prove every accepted branch receives the same passive-decay duration.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/test_checkpoint.py -q`; expected failure: missing atomic API.
- [ ] **GREEN:** Define a frozen snapshot dataclass, copy on read, prevalidate the complete replacement against immutable `baseline_plastic`, then assign the three candidate slices. Checkpoint before and after each intervention. Never use `no_external_dan` as the supposedly memory-free recipient.
- [ ] Run focused/full pytest and the opt-in native checkpoint test. Confirm MBON07 candidate state is unchanged and separately report it.
- [ ] Commit: `feat / candidate-intervention : Replace MBON11 memory state atomically`.

### Task 5: Implement the bounded qualification protocol

**Files:** Create `src/fly_connectome_sim/experiment/qualification.py`, `tests/experiment/test_qualification.py`; use Tasks 1–4 without creating a durable full-graph result yet.

**Interfaces:** `qualify(engine_factory, recorder, *, seeds, family) -> QualificationResult` and `benchmark(...) -> dict`. Formal qualification seeds are `(11, 23)` and confirmation seeds `(101, 113)`; never cross them. The fixed grid has CS duration 100 or 300 ms, PPL101 pulse duration exactly 100 ms, DAN onset relative to CS onset −100, 0 or +100 ms, and post-pair gap 500 or 10,000 ms (12 configurations). Each trial reserves the same epoch from −100 ms through `CS_end + 200 ms`; split at every CS/DAN boundary and use black frames outside CS. The pulse belongs to the paired trial even when its −100 ms offset is visually black. The temporally unpaired pulse is fixed at least 10,000 ms from the nearest CS boundary and is not changed by the post-pair-gap grid. All conditions match total elapsed time and visual exposure. Current 20 mV current remains fixed.

Predeclared response-window candidates relative to CS onset are `[0,100)`, `[0,300)`, and `[100,300)` ms. For each window, `one_spike_rate_hz = 1 / (len(MBON11) * window_seconds)`. The C response floor is exactly that one-spike rate. The dimensionless candidate-state metric is mean absolute candidate `memory_w` difference from the time/exposure-matched `learning=False` branch at training end; its numerical resolution is measured from identical checkpoint replays in the same units. The washout metric is the absolute MBON11 response difference between externally stimulated frozen-plasticity and matched unstimulated frozen-plasticity branches. Its independent threshold is `max(5 * replay_numeric_resolution_hz, one_spike_rate_hz)` and never includes the acute value or later control deltas.

- [ ] **RED:** Test all interval splits, equal trial durations, fixed unpaired separation, grid cardinality/order, window definitions, disjoint seeds/families, deterministic edge/DAN ordering, transient any-bin saturation, finite measurements and benchmark fields. Fixtures where every candidate saturates, lacks a state shift above `5 * state_replay_resolution`, lacks MBON11/KC observability or fails independent washout must return `unsupported` with no selected configuration.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_qualification.py -q`; expected failure: missing qualification API.
- [ ] **GREEN:** Require nonzero modeled drive for A/B/C, distinguishable MBON11-input KC vectors for A/B, checkpoint replay determinism, C above its response floor and MBON11 dynamic range. Reject nonfinite points or any-bin candidate bound-hit fraction >1%. Test T candidates 10, 20, 30 and 60 s; choose the first passing independent washout threshold. Among remaining points, choose the largest absolute exploratory MBON11 difference-in-differences at T, tie-break by fixed grid then fixed response-window order, and freeze its observed sign. Record all points, including candidate-state metric/resolution, MBON11 values, MBON07 state and rejection reasons. The grid cannot expand after results.
- [ ] Implement benchmark output for simulated seconds, wall seconds, event count, checkpoint bytes and peak event-buffer bytes without altering scientific parameters. Run unit/tiny-graph pilots only; they are disposable and cannot supply the frozen config.
- [ ] Run focused/full pytest. Commit code/tests: `feat / timing-qualification : Declare the bounded exploratory assay`.

### Task 6: Recorder pilot, schema and CLI after fields are known

**Files:** Create `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `src/fly_connectome_sim/cli.py`, `tests/experiment/test_recorder.py`, `tests/test_cli.py`; update `pyproject.toml` only if the existing script entry needs correction.

**Interfaces:** CLI `fly-connectome-sim qualify --output-dir PATH`, `fly-connectome-sim verify-run PATH`; Task 7 adds the final `assay` command after analysis exists. Implement `RunRecorder.append(event)` and `verify_run(path) -> VerifiedRun`. `run.json` contains immutable provenance/config and hashes. Every JSONL event has a globally increasing `sequence`, `branch_id`, branch-local `sim_ms`, and for forks a parent branch/checkpoint hash. Require simulated-time monotonicity only within each branch. Checkpoints are `brain-before.npz`, `brain-after.npz` and named branch files. Hash canonical scientific events without `compute_seconds` or `kernel_seconds`; retain those as operational telemetry. Reject duplicate run directories instead of overwriting.

- [ ] **RED:** Test ordered append/flush/reopen, globally increasing sequence, branch-local time validation, explicit forks to earlier simulated clocks, truncated/tampered line or checkpoint rejection, mismatched config/engine identity, exact neutral chunks, separate checkpoints for T/T+60 and interventions, strict JSON, and deterministic scientific hashes despite different compute times. CLI tests show `verify-run` fails closed and output directories cannot be overwritten.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_recorder.py tests/test_cli.py -q`; expected failure: missing recorder/CLI.
- [ ] **GREEN:** Implement metadata and schema for measured fields established in Tasks 1–5: complete engine identity; factors, seed and RGB hashes; per-bin counts/rates, modeled pathway drive and trace diagnostics; stimulation, neutral chunks, memory/saturation, T reference, forks and interventions. Write metadata/checkpoints via temporary file plus atomic replace and verify hashes before analysis. Choose flush chunks from a disposable benchmark and preserve immutable event bytes after close.
- [ ] Run focused/full pytest; execute one short ignored `runs/pilot-*` tiny-graph artifact and verify it. It is a schema pilot only and is never referenced by qualification/configuration.
- [ ] Commit code/schema/tests only: `feat / assay-recorder : Verify append-only experiment artifacts`.

### Task 7: Implement the frozen analysis contract and assay CLI

**Files:** Create `src/fly_connectome_sim/experiment/analysis.py`, `tests/experiment/test_analysis.py`; modify `src/fly_connectome_sim/cli.py`, `tests/test_cli.py`. Do not create the populated frozen config until Task 9 formal qualification completes.

**Interfaces:** `build_frozen_config(qualification: VerifiedRun) -> FrozenAssayConfig` and `analyze_assay(run: VerifiedRun, frozen: FrozenAssayConfig) -> AssayReport`. The builder accepts qualification-family artifacts only and carries their exact hashes, model/engine identity, protocol/stimulus versions, selected response window, mean-rate aggregation, expected sign, effect floor, timing, T, disjoint confirmation seeds/family, exclusions and analysis version. `fly-connectome-sim assay --config PATH --output-dir PATH` runs existing orchestration without optimizing the config.

The endpoint for each paired identity is `delta=(post_plus-post_minus)-(pre_plus-pre_minus)`. `pre` and `post` are reward-free MBON11 rates from the same fixed window. Calculate independently at T and T+60 s from distinct training-end checkpoint copies. Require signed trained delta to exceed the frozen floor at both times and exceed corresponding frozen, `no_external_dan` and temporally unpaired deltas by that floor. Define `g=post_C/pre_C`; C must exceed the frozen one-spike response floor. Reject global gain unless signed `[(post_plus-g*pre_plus)-(post_minus-g*pre_minus)]` also exceeds the floor. Reciprocal pairing must move the raw A−B change with paired identity while paired-minus-unpaired keeps the declared sign. Necessity removes the effect to within the floor, sufficiency restores it above the floor, and sham matches untouched within replay resolution. Donor/recipient training-end clocks and passive-decay durations must match. Missing branches, identity, C response, hashes or timing are `inconclusive`.

- [ ] **RED:** In `test_analysis.py`, use hand-calculated small event streams to test delta sign, both retention times, each control, reciprocal identity, global multiplication of pre A/B/C, necessity/sufficiency/sham, endogenous DAN in `no_external_dan`, missing/invalid bins and mismatched provenance. The global multiplier fixture must classify `unsupported` despite a nonzero raw delta.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py -q`; expected failure: missing pure analysis API.
- [ ] **GREEN:** Implement exact arithmetic and classifications `supported`, `unsupported`, `inconclusive`; emit all values/reasons. Derive the effect floor from qualification as `max(5 * replay_numeric_resolution_hz, 2 * max_abs_qual_control_delta_hz, 0.05 * qualified_mbon11_dynamic_range_hz)` and record each term. This floor is not reused for washout. Consume the response window/sign already selected from Task 5's fixed candidates; do not search again. Do not use held-out values in configuration or thresholds.
- [ ] Run focused/full pytest and a disposable CLI pilot. Commit source/tests only: `feat / frozen-assay : Implement MBON11 causal analysis`.

### Task 8: Add a motor-only adapter without a behavioral claim

**Files:** Modify `src/fly_connectome_sim/experiment/adapter.py`, `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `tests/experiment/test_adapter.py`, `tests/experiment/test_recorder.py`. Keep `preference-adapter/v1` readable for old artifacts.

**Interfaces:** `LateralMotorAdapter(version="lateral-motor-adapter/v1", action_threshold_hz=1.0).adapt(telemetry) -> MotorDecision` uses only `motor_right - motor_left`, with `evidence_strength=abs(right-left)/(right+left)` (zero when both are zero). It never reads MBON activity, stimulus identity, condition, reward or event metadata. The 1 Hz threshold is an explicitly engineered display rule, not a calibrated behavioral threshold. This task exposes unvalidated motor telemetry only; motor qualification and held-out validation require a later dedicated design/plan.

- [ ] **RED:** Assert MBON-only changes cannot affect action, right/left motor changes produce the corresponding proposal, zero/threshold evidence defers, metadata changes do nothing, and v1 output remains readable.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_adapter.py -q`; expected failure: missing motor-only adapter.
- [ ] **GREEN:** Implement the adapter and use `evidence_strength`; never infer direction from MBON07−MBON11. Recorder labels the output `engineered_unvalidated_motor_readout` and it cannot alter the primary analysis classification.
- [ ] Run focused/full pytest. Commit adapter/recorder/schema tests together: `feat / motor-readout : Separate lateral evidence from MBON analysis`.

### Task 9: Source freeze, formal qualification and held-out confirmation

**Files:** Create `configs/assay.synthetic.json` only after formal qualification; modify `tests/test_full_graph_engine.py` for opt-in end-to-end coverage; create a concise result document under `docs/`. Use ignored `runs/qualification-*` and `runs/confirmation-*`; do not modify packaged `.py`/`.cpp` after source freeze.

**Source-freeze rule:** Begin from a clean commit after Tasks 1–8. Run source/runtime verification and the complete suite including full graph. Record commit SHA and engine identity. From this point, any package-source change discards all formal qualification/config/confirmation artifacts and restarts Task 9 from a new clean commit. Tests, config and result docs may change because they are outside `model_fingerprint`, but they cannot alter numerical behavior.

- [ ] Run formal `fly-connectome-sim qualify` on the full graph with qualification family/seeds `(11,23)`, all fixed grid points, both paired identities and AB/BA order. Apply matched controls and causal interventions to the selected candidate configuration, not as extra grid-selection dimensions. Record benchmark values and verify the artifact before selecting anything. If integrity, observability, state-shift, saturation, intervention or independent washout fails, stop: commit only an honest negative qualification report and do not create a confirmation config.
- [ ] If qualification passes, generate `configs/assay.synthetic.json` only via `build_frozen_config()`. It contains exact qualification hashes and engine identity, selected fixed-grid timing/window/sign/T, all floor terms, confirmation family/seeds `(101,113)`, conditions and intervention clocks. Independently review and commit this config before reading confirmation output: `feat / assay-preregistration : Freeze the held-out MBON11 assay`.
- [ ] **RED:** Add an opt-in integration test that requires all condition/factor/T/T+60/intervention cells, branch-local clocks, parent checkpoint hashes and deterministic scientific hashes, without asserting a positive classification.
- [ ] Run `$env:FLY_CONNECTOME_SIM_FULL_TEST='1'; .venv/Scripts/python.exe -m pytest tests/test_full_graph_engine.py -q`; expected new failure is missing held-out output/orchestration evidence, not source behavior. Clear the environment variable afterward.
- [ ] Execute `fly-connectome-sim assay --config configs/assay.synthetic.json --output-dir runs/confirmation-<unique-id>` once. Every condition starts from the same baseline checkpoint and matches exposure/order/side/time. Test A/B/C at T and T+60; interventions occur at the common training-end clock and then receive identical passive decay. Verify before analysis and classify without changing config or thresholds.
- [ ] Rerun the identical deterministic schedule into a separate directory only to compare scientific hashes; this is computational reproducibility, not another biological sample. Review reciprocal identity, global-gain residual, endogenous DAN, MBON07 state, and sham/necessity/sufficiency rows.
- [ ] Run the full suite again without changing packaged source. Commit the integration test and concise result document with artifact hashes/classification, never raw artifacts: `feat / held-out-assay : Classify the frozen full-graph experiment`.

## Final verification and interpretation gate

- [ ] Verify source/runtime locks and full pytest, plus the opt-in full-graph suite with `FLY_CONNECTOME_SIM_FULL_TEST=1`. Compare artifact hashes after deterministic rerun; exclude wall-clock fields only.
- [ ] Review the held-out report against the approved claim boundary. If any primary gate fails, state which one and report an unsupported or inconclusive model experiment. If all pass, use only the design spec's model-specific wording and the demonstrated T and T+60 duration. Report MBON07 state, endogenous DAN, motor results and runtime separately.
- [ ] Do not begin viewer or LLM work until the assay result and artifact contract have their own review. Neither can upgrade a failed scientific gate.
