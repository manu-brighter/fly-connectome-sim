# Associative Plasticity Assay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether the declared PPL101-modulated KC→MBON11 state produces a persistent, stimulus-specific MBON11 response change in the MaleCNS-constrained model, then assess lateral motor evidence separately.

**Architecture:** Keep the existing full-graph engine and checkpoint format. Extend the project-owned experiment package from factorized stimuli and schedules through a gap executor, pathway measurements, qualification, an atomic candidate-state intervention, verified run artifacts, a frozen analysis, and held-out execution. The motor adapter consumes measured motor telemetry only after the primary assay is classified.

**Tech Stack:** Python 3.12, NumPy 2.4.6, C++17 native core, pytest, Windows PowerShell; use `.venv/Scripts/python.exe` in commands below (on Unix, `.venv/bin/python`).

**Spec:** `docs/superpowers/specs/2026-09-24-associative-plasticity-pivot-design.md`; retain the broader boundaries in `docs/specs/fly-event-planner.md`.

**Replay refinement:** The bounded occurrence/content, black-retention and
verification contract is defined in
[`2026-10-02-replay-anchor-contract.md`](../specs/2026-10-02-replay-anchor-contract.md).

**Candidate-state refinement:** Production candidate/noncandidate content digests
follow [`2026-10-03-candidate-state-digest-contract.md`](../specs/2026-10-03-candidate-state-digest-contract.md).

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
| `src/fly_connectome_sim/neural/brain.py`, `src/fly_connectome_sim/neural/checkpoint.py`, `tests/test_checkpoint.py` | Atomic candidate-edge memory snapshot/replace and shared complete checkpoint-payload hashing, with validation before mutation. |
| `src/fly_connectome_sim/experiment/qualification.py`, `tests/experiment/test_qualification.py` (new) | Bounded exploratory grid, path/washout gate, runtime benchmark and frozen configuration output. |
| `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `src/fly_connectome_sim/cli.py`, `tests/experiment/test_recorder.py`, `tests/test_cli.py` (new) | Append-only pilot and assay artifacts, strict verifier and CLI. |
| `src/fly_connectome_sim/experiment/analysis.py`, `tests/experiment/test_analysis.py` (new) | Pure frozen-config builder, MBON11 evidence reducer and classification; no exploratory parameter selection. |
| `src/fly_connectome_sim/experiment/replay.py`, `tests/experiment/test_replay.py` (new) | Bounded black-retention recipe validation/execution, validated-prefix support and verifier-produced replay attestation. |
| `src/fly_connectome_sim/experiment/assay.py`, `tests/experiment/test_assay.py` (new) | Held-out confirmation orchestration, selected causal interventions and compact replay-anchor production. |
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

**Files:** Create `src/fly_connectome_sim/experiment/analysis.py`, `src/fly_connectome_sim/experiment/assay.py`, `tests/experiment/test_analysis.py`, `tests/experiment/test_assay.py`; modify `src/fly_connectome_sim/experiment/qualification.py`, `src/fly_connectome_sim/experiment/executor.py`, `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`, `src/fly_connectome_sim/cli.py` and their focused tests. Do not create the populated frozen config until Task 9 formal qualification completes.

**Interfaces:** `build_frozen_config(qualification: VerifiedRun) -> FrozenAssayConfig` and `analyze_assay(run: VerifiedRun, frozen: FrozenAssayConfig) -> AssayReport`. The builder accepts qualification-family artifacts only and carries their exact hashes, model/engine identity, protocol/stimulus versions, selected response window, mean-rate aggregation, expected sign, effect floor, timing, T, disjoint confirmation seeds/family, exclusions and analysis version. `run_assay(...)` supplies the previously missing held-out orchestration; `fly-connectome-sim assay --config PATH --output-dir PATH` invokes it without optimizing the config.

The endpoint for each paired identity is `delta=(post_plus-post_minus)-(pre_plus-pre_minus)`. `pre` and `post` are reward-free MBON11 rates recomputed from raw bins in the same fixed window. Calculate independently at T and T+60 s from distinct copies of the same training-end checkpoint. Require every seed/identity/order/time cell's signed trained delta to exceed the frozen floor and exceed corresponding frozen, `no_external_dan` and temporally unpaired deltas by that floor. Define `g=post_C/pre_C`; C must exceed the frozen one-spike response floor. Reject global gain unless signed `[(post_plus-g*pre_plus)-(post_minus-g*pre_minus)]` also exceeds the floor. Reciprocal pairing must reverse the raw A−B effect with paired identity while paired-minus-unpaired keeps the declared sign. Necessity must match the untouched reference within the floor and remove more than one floor from paired; sufficiency must exceed both the floor and its matched untouched recipient by one floor; sham matches paired within replay resolution. Donor/recipient training-end clocks and passive-decay durations must match. Missing branches, identity, C response, hashes or timing are `inconclusive` and take precedence over scientific-gate failures.

- [x] **RED 7A:** In `test_analysis.py`, use hand-calculated small event streams to test delta sign, both retention times, each control, reciprocal identity, global multiplication of pre A/B/C, necessity/sufficiency/sham, endogenous DAN in `no_external_dan`, missing/invalid bins and mismatched provenance. The global multiplier fixture must classify `unsupported` despite a nonzero raw delta.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py -q`; expected failure: missing pure analysis API.
- [x] **GREEN 7A:** Implement strict frozen-config serialization, exact arithmetic and classifications `supported`, `unsupported`, `inconclusive`; emit all values/reasons. Derive the effect floor from qualification as `max(5 * replay_numeric_resolution_hz, 2 * max_abs_qual_control_delta_hz, 0.05 * qualified_mbon11_dynamic_range_hz)` and record each term. This floor is not reused for washout. Consume the response window/sign already selected from Task 5's fixed candidates; do not search again. Do not use held-out values in configuration or thresholds.
- [ ] **RED/GREEN 7B:** Record and gate selected qualification controls/interventions at T and T+60, then implement held-out production for every frozen factor. Distinguish association T0 from the later schedule-complete checkpoint and preserve exact passive durations. Require matched-reference contrasts for necessity/sufficiency and freeze expected confirmation RGB/black hashes.
- [x] **7B1:** Require one complete, metadata-bound terminal `assay_result` for confirmation artifacts. Validate canonical report hashes and exact evidence-prefix bindings through shared recorder/verifier checks and mirror the payload contract in the packaged schema. The independent analyzer remains responsible for scientific recomputation.
- [x] Resolve the anchor occurrence/content contract: occurrence-envelope SHA binds the exact durable route and recorded recipe/prefix; a separate complete-state SHA permits identical paired/sham content without merging ancestry. Fix schema compatibility and bounded temporary-snapshot policy in the replay refinement.
- [x] **7B2a:** Implement shared live/archive checkpoint payload and canonical complete-state hashing with bounded array buffers, strict metadata and existing model/native-state validation. Preserve legacy provenance byte hashes and verify exact live/archive/restore agreement on the real full graph.
- [x] **7B2b:** Implement strict occurrence-envelope/black-retention recipe primitives and isolated real native execution. Bind exact source occurrence, completed scientific prefix, every explicit call and thaw; preserve analyzer source-identity semantics. These primitives do not yet attest persisted artifacts.
- [x] **7B2:** Use complete-state hashing to implement the occurrence envelope, strict `black-retention/v1` recipe, recorder/schema anchor indexing and immutable verifier-produced attestation. Demonstrate a real durable source to anchor to two sibling test forks; preserve all analyzer gates. Keep one bounded temporary retention snapshot for sibling restores outside sealed inventory.
- [x] **7B3a:** Share validated-prefix and sealed report construction, including inventory/provenance gates, computed verifier mode and nonmaterialized-parent labels. Prove exact canonical terminal/report equality using an honest real partial native artifact; missing assay cells remain inconclusive. Terminal framing does not consume the scientific event budget; incomplete reports preserve actual labels and provenance.
- [x] **7B3b:** Implement validated live candidate/noncandidate state digests with exact ordered selection maps, separate content domains and streamed complement exclusions. Follow the candidate-state contract and bounded steps below; existing candidate replacement, numerical behavior and complete checkpoint preimages remain unchanged.
- [ ] Extend the producer/artifact with strict response/intervention events and shared validated-prefix replay before terminal reduction. Formally verify after sealing and independently recompute the same canonical report, including nonmaterialized-parent and verification-mode labels. Retain durable before/after and all selected ordinary training-end/intervention checkpoints.
- [ ] Decide discarded-grid training ancestry using measured durable-storage versus separately reviewed exact training-replay cost; black-retention replay alone does not solve it. Do not introduce a generic replay interpreter or weaken freeze-input ancestry.
- [ ] Measure or conservatively project full-graph checkpoint/event/wall-time capacity before source freeze. Keep full response/CS/DAN bins but compact passive black-gap telemetry.
- [ ] Run focused/full pytest and a disposable CLI pilot. Commit source/tests only: `feat / frozen-assay : Implement MBON11 causal analysis`.

#### Task7B3b: bounded state-digest implementation

**Files:** `src/fly_connectome_sim/neural/brain.py` owns actual live validation;
`src/fly_connectome_sim/neural/checkpoint.py` owns the narrow private codec;
`tests/test_checkpoint.py` owns wire/native/invalid-state/streaming regressions;
`tests/test_full_graph_engine.py` owns one opt-in read-only fullgraph hash test.
No engine, analysis, recorder, qualification, protocol or native-core changes.

**Interfaces:** `MemoryBrain.candidate_state_digests(target_indices, *,
chunk_bytes=HASH_CHUNK_BYTES) -> dict[str, str]` returns exactly
`candidate_memory_sha256` and `noncandidate_state_sha256`.
`checkpoint._candidate_state_digests(metadata, arrays, *, target_indices,
candidate_positions, edge_indices, chunk_bytes=HASH_CHUNK_BYTES)` is a private
encoding seam, not artifact/model authentication. The normative domains, G/A/E/X
records, maps, validation and acceptance cases are in the candidate-state contract.

**Review focus:** Unsorted global edges must not reorder memory; fully excluded
arrays must retain schema/map; invalid excluded values must still reject; actual
readonly arrays must remain unchanged; terminal/route identity must not enter
content or silently replace later donor provenance checks. Each is covered below.

- [x] **RED live boundary:** Reuse the actual native `intervention_brains` fixture,
  lock model provenance before hashing and capture tiny state bytes. Initial test:

```python
def test_candidate_state_digests_are_read_only(intervention_brains):
    brain, _ = intervention_brains
    brain.lock_model_provenance()
    before = state_bytes(brain)
    result = brain.candidate_state_digests(np.array([2, 3], dtype=np.int32))
    assert set(result) == {"candidate_memory_sha256", "noncandidate_state_sha256"}
    assert all(len(value) == 64 and set(value) <= set("0123456789abcdef")
               for value in result.values())
    assert state_bytes(brain) == before
```

- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_checkpoint.py -k
  candidate_state_digests -q --basetemp=.tools/pytest-temp-7b3b-worker --tb=short`.
  Expected RED is absent live API after real brain construction/lock, not broken
  fixtures or imports. Record command/output before product edits.
- [x] Add independent literal-byte wire tests for both exact domains and map
  order, negative zero and an empty component complement. Assemble expected
  preimages from literal canonical metadata/header bytes, `struct.pack('<Q', n)`
  and literal numeric bytes, never production canonical/map/header helpers.
  Add native necessity/sufficiency/sham equality tests with distinct donor neural
  state, both targets selecting circuit edges `[1,0]`, and checkpoint-restore parity.
- [x] Implement the private codec using existing JSON/chunk/framing primitives,
  selected gathers bounded by `chunk_bytes` and basic complement slices. Validate
  entire array values before exclusion; preserve complete-state/raw digest wire
  bytes. Add the live wrapper validating the actual locked complete payload,
  registration/native state, exact candidate map and actual rule-bound/weight
  consistency before calling the codec; recheck the model lock before returning.
  The call computes both values from one quiescent state without snapshot/NPZ.
- [x] Add parameterized sensitivity/rejection tests for every contract acceptance
  category: all untouched registered fields and mutable scalars, candidate `rate_kc`,
  selected-only replacements, readonly inputs, wrong/empty/duplicate/out-of-range
  maps, invalid excluded u/w/weight, registration/schema/native/clock/model-lock
  divergence, endian/index-width/layout equivalence, dtype/rank/shape/map/signed-zero
  discrimination, empty state arrays and fully excluded components. Invalid calls
  leave actual state unchanged. Targets with no edges remain bound if group-wide
  selection is nonempty; an entirely edge-free candidate rejects.
- [x] Add sparse unsorted large synthetic-weight streaming guards and chunk-size
  invariance at8 and nonmultiple sizes. Observe encoder buffers/hash update pieces,
  not native validator/selection allocations. Reject full complement masks/copies,
  full-array byte/astype/byteswap/contiguous conversions and concatenation in codec.
- [x] Add opt-in `test_full_graph_candidate_digests_are_read_only`: create a real
  prepared-graph engine, obtain identity to lock, record complete-state SHA and
  scalar/array references, call live API twice on actual MBON11 targets and require
  equal digests plus unchanged complete-state SHA/scalars/references. No extra
  graph-scale snapshot/archive, observe, qualification or capacity measurement.
- [x] Run focused checkpoint/native/engine tests, self-review and report exact
  RED/GREEN/API/wire/limits. Freeze and notify coordinator before one ordinary
  complete suite; coordinator owns fresh independent review and final opt-in full
  suite after any fixes. Do not claim fullgraph capacity or an executed assay.
- [x] Coordinator commits reviewed code/tests and accurate contract/plan/status
  updates: `feat / state-digests : Bind candidate and noncandidate state evidence`;
  push explicitly `git push -u origin feat/connectome-experiment-core`.

Completion evidence: genuine native RED/GREEN implementation and review-fix
regressions; independent state/wire review plus clean scoped fix review.
Final root opt-in complete suite:1190 passed in322.64s, including both real
fullgraph integrations. Candidate hashes prove content, not donor provenance,
clock compatibility, capacity, formal qualification or a positive assay result.

#### Task7B3c: bounded paired-cohort producer

**Files:** Create `src/fly_connectome_sim/experiment/assay.py` and
`tests/experiment/test_assay.py`. Extract the existing declared native frozen
test contract into `tests/experiment/replay_helpers.py`, updating only its
test caller in `test_analysis.py`. Root owns plan and README status.

**Interface:** `run_paired_cohort(engine_factory, frozen, *, output_dir,
seed=101, paired_identity="A", presentation_order="AB") -> AssayReport` executes
one frozen paired cohort. It does not produce the full confirmatory assay or
choose scientific parameters. Other declared cohorts/controls/interventions
remain missing, with an inconclusive report.

**Review focus:** Actual current ordered groups must match frozen declarations
even when engine identity is cached. Candidate content is not occurrence or
clock proof. Independent pre/post trials must not carry preceding trial state.
Record response at its window stop before padding. Source/recipe mutation before
terminal must fail closed; excluded timing cannot contaminate scientific hashes.

- [x] **RED:** The native graph fixture reaches the absent producer module.
  Subsequent clock and canonical-report regressions fully construct real native
  engines and a schema-valid declared frozen correctness contract before their
  failing assertions. The fixture is not qualification evidence and does not
  call `build_frozen_config`.
- [x] **GREEN acquisition:** Reuse `_training_timeline(..., controls=True)`,
  `_trial_segments` and `_split_intervals`. Execute and record every actual
  <=500 ms call, its clocks/arguments and raw response/CS/DAN bins. Supply explicit
  black RGB during neutral time, learning-disabled reward-free retention/tests
  and passive decay. Derive strict training evidence and live candidate/noncandidate
  digests from actual state. Retain durable before/baseline/training-end/after
  occurrences and exact parent references. Check actual identity/groups/maps,
  clock, population and frozen input hashes rather than trusting cached labels.
- [x] **GREEN responses:** Acquire independent baseline A/B/C pre trials and
  both retention groups, producing twelve strict descriptors. Pre means restored
  baseline-state measurement; acquiring it after durable training-end hash exists
  cannot select parameters or carry training state into that restored copy.
  Truthful pre measurements may supply both retention rows. For each retention,
  source-to-anchor black replay stops at CS onset minus1000 ticks. Validate one
  scratch NPZ outside inventory by actual state SHA/tick, restore all three
  siblings independently, execute each prelude and reward-free trial, then remove
  scratch. Record exactly two used anchors and emit responses at window stop.
- [x] **GREEN lifecycle:** Use actual `verify_replay_prefix`,
  `assess_assay_prefix` and `build_assay_result`; append exactly one terminal,
  seal, call `verify_replay_run` and independently `analyze_assay`. Require exact
  canonical report equality. Ordinary verification remains integrity-only.
- [x] **Acceptance:** Independently check actual calls/source NPZ/raw counts;
  both paired rows have pre/post A/B/C without invalid training/response,
  ancestry/copy/clock/provenance/inventory/terminal reasons. Missing declared
  cells remain visible and result inconclusive. Source and recipe-operation
  tampering before terminal returns no attested result or seal. A timing-only
  native rerun preserves recipe/anchor/report/scientific identities. Reject
  current-group mismatch despite cached identity; cover declared timing/windows.
  Reject unreachable anchors before scratch/recorder creation while preserving
  the reachable anchor-equals-source boundary.
- [x] Run focused producer/analysis/replay coverage, fresh independent integrity
  review and the full suite with `FLY_CONNECTOME_SIM_FULL_TEST=1`.

Completion evidence: native missing-module RED, clock/canonical-comparison
RED/GREEN and timing-preflight artifact RED/GREEN. Independent integrity review
and scoped fix review are clean after one Important timing finding was fixed.
Final amended producer coverage:18 passed; final complete opt-in suite:1208
passed in444.47s, including both actual fullgraph integrations. Commit only
reviewed source/tests/status files and push the explicit feature branch.

This is a tiny correctness lifecycle pilot, not formal qualification,
confirmation, fullgraph capacity approval or a positive scientific finding.
Selected qualification evidence, control/intervention routes, all-factor
production and the assay CLI remain subsequent tasks.

#### Task7B3d: native matched reference and candidate replacement routes

**Files:** Extend `experiment/assay.py` and its native tests; update status docs.

**Interface:** `run_intervention_cohort(...) -> AssayReport` uses the paired
producer's arguments and shared execution path. Preserve `run_paired_cohort`
behavior. Execute paired and time-/exposure-matched reference acquisition from
independent baseline restores, then necessity, sufficiency and sham replacements
at their common training-end clock. Bind each route to its recipient training and
actual post-intervention source occurrence, including baseline responses.

- [x] **RED:** Initialize the genuine tiny native engine and declared test config
  before asserting the missing API. Then prove two training events, three real
  interventions, ten anchors, sixty responses and eight durable checkpoints.
- [x] **GREEN:** Reuse training/trial/retention schedules and preflight both source
  clocks before recording. Authenticate exact durable donor/recipient occurrences
  and their live training-end digests; compare canonical identities, current
  groups, clocks and actual ordered candidate maps. Capture a quiescent authentic
  donor snapshot. Bracket only replacement with recipient component digests;
  preserve noncandidate state and sham content. Identical necessity/sufficiency
  content is valid and must not be fabricated into a shift.
- [x] Verify native baseline/retained trial isolation, actual replacement triplets,
  telemetry/counts, source/occurrence tampering and compatibility rejection. Keep
  timing-only scientific equivalence and the existing paired API regressions.
- [x] Native-verify prefix and sealed artifact, with one terminal and independent
  canonical report equality. Ten complete route/time rows remain inconclusive
  because other declared factors and the three controls are still missing.
- [x] Freeze/self-review, independent integrity review, covering fixes and final
  complete opt-in suite before the explicit feature-branch commit/push.

Completion evidence (2026-10-04): genuine initialized native missing-API RED,
source/transfer and signed-zero snapshot-spoof RED/GREEN; focused native suite
45 passed in320.80s, including all eighteen paired regressions. Independent
integrity/specification/quality review found no open Critical, Important or Minor
findings. Final complete opt-in suite:1235 passed in643.92s, including both actual
fullgraph integrations, on the unchanged reviewed source/test bytes.

This slice does not supply formal qualification, a production frozen config,
fullgraph capacity approval, all-factor controls or the assay CLI.

#### Task7B3e: complete native control routes for one cohort

**Files:** Extend `experiment/assay.py` and its native tests; update status docs.

**Interface:** `run_controlled_cohort(...) -> AssayReport` shares the existing
producer and executes all eight conditions for one seed/identity/order cohort.
Preserve paired and intervention APIs. Add frozen-plasticity, no-external-DAN
and temporally-unpaired acquisition through the existing five ordinary plans.

- [x] **RED:** Initialize native engine/config before the absent-API failure.
- [x] **GREEN:** Acquire all five ordinary sources independently from baseline;
  match time/exposure/order and preflight every retention source. Execute each
  shared plan's learning/stimulation declarations. Frozen plasticity disables
  acquisition learning while weights stay unfrozen for passive memory decay.
  No-external-DAN preserves endogenous learning/telemetry. The unpaired pulse
  receives black RGB and stays at least 10000ms from every CS boundary.
- [x] Native evidence proves five trainings, three interventions, sixteen
  anchors, ninety-six responses, eleven durable checkpoints and forty-eight
  independent post trials. All sixteen condition/time rows have pre/post A/B/C;
  other declared factors remain missing and classify the pilot as inconclusive.
- [x] Preserve existing forty-five paired/intervention regressions, terminal
  canonical equality and native prefix/sealed replay. Independently review and
  run a final complete opt-in suite before feature-branch commit/push.

Completion evidence (2026-10-04): initialized native missing-API RED;
focused native coverage:52 passed in522.89s, including all forty-five existing
paired/intervention regressions. Fresh independent integrity review has no open
findings. Final complete opt-in suite with regular sandbox permission:1242 passed
in852.34s, including both fullgraph integrations and the native-build smoke, on
unchanged reviewed source/test bytes. Earlier sandbox full runs passed1241 tests
but Windows application control blocked the freshly built smoke DLL at load
(WinError4551); compilation completed, and no product or security-policy change
was made to obtain the final host-environment verification.

This slice supplies complete conditions for one factor cohort, not all-factor
confirmation, formal qualification/configuration, capacity approval or the CLI.

#### Task7B3f: shared artifact for reciprocal controlled cohorts

**Files:** Extend `experiment/assay.py` and its native tests; update status docs.

**Interface:** `run_controlled_cohorts(engine_factory, frozen, *, output_dir,
cohorts) -> AssayReport` accepts a nonempty bounded list/tuple of unique declared
seed/identity/order triples. Existing single-cohort APIs and evidence names stay
compatible. All requested cohorts share one real baseline occurrence and one
recorder, prefix, terminal and sealed artifact. Durable training/intervention
checkpoints and pre/post/retention/anchor identifiers are unique per cohort.

- [x] **RED:** Initialize genuine tiny native engine/config before missing API.
- [x] **GREEN:** Execute all eight conditions for each requested cohort from
  independent restores of one global baseline. Preflight actual input hashes and
  retention reachability for every requested cohort before scratch/recorder.
  Preserve source/donor/recipient occurrences, clocks, passive decay, sequence
  order and native replay contracts; no combination of independently sealed runs.
- [x] Native reciprocal acceptance executes `101/A/AB` and `101/B/AB`: ten
  trainings, six interventions, thirty-two anchors, 192 responses and nineteen
  durable checkpoints. Both cells at both retention times contain all eight
  conditions and pre/post A/B/C, while other factors remain visibly missing.
  Preserve negative scientific and reciprocal gates; status remains inconclusive.
- [x] Reject empty, duplicate, malformed and undeclared cohort factors plus
  late-cohort bad inputs/unreachable sources before creating artifacts. Preserve
  all fifty-two existing regressions. Independently review, freeze tested bytes,
  then run a complete opt-in suite before explicit feature-branch commit/push.

Completion evidence (2026-10-04): initialized native missing-API RED; final-byte
preflight coverage:20 passed. Fresh independent integrity review has no open
findings. Final complete opt-in suite:1263 passed in1661.01s, including all73
producer cases, both fullgraph integrations and the native-build smoke, with
zero failures/errors/skips and unchanged reviewed source/test hashes. The genuine
reciprocal native acceptance passed in791.396s on the stronger final assertions;
its one shared sealed artifact remains scientifically inconclusive.

This slice validates two cohorts in one native artifact; it does not establish
all-factor confirmation, formal qualification/configuration, fullgraph capacity
or the assay CLI. Full factor execution remains a subsequent validation gate.

#### Task7B3g: native acceptance of the complete factor matrix

**Files:** Create `tests/experiment/test_assay_all_factors.py`; update status docs.
Production APIs and existing producer regressions remain unchanged.

- [x] Add one genuine native opt-in integration using all eight declared
  seed/identity/order triples through `run_controlled_cohorts` in one artifact.
  Reuse the existing full-test environment convention and native fixture.
- [x] Require forty trainings, twenty-four interventions, 768 responses,
  128 native-attested anchors and sixty-seven durable checkpoints. Check all
  sixteen factor/retention keys and eight conditions with pre/post A/B/C,
  cohort-qualified source occurrences, actual inputs and response/anchor ancestry.
- [x] Independently verify and reduce the sealed evidence; require canonical
  report equality and a structurally complete matrix with honest scientific
  failures. Do not weaken gates or fabricate qualification/positive results.
- [x] Freeze and independently review the test; run one final complete opt-in
  suite covering the new native case and all existing regressions before explicit
  feature-branch commit/push. Retain actual verification evidence.

Verified 2026-10-05: fresh independent integrity review passed; the complete
opt-in suite passed all 1,264 cases with no failures, errors or skips in
52,202.15 seconds. The new native case took 50,563.872 seconds and authenticated
the complete 768-response matrix, 128 anchors and 67 durable checkpoints.
The report remains scientifically `unsupported`, including negative reciprocal
gates; matrix completeness does not imply learning or qualification. Production
source and all 73 existing producer regressions retain their frozen hashes.
Investigate recorder/replay timing before scaling this acceptance to fullgraph;
repeated prefix scans are a static hypothesis, not an isolated measurement.

This validates the complete declared factor matrix on the tiny native fixture;
it does not establish formal qualification, production configuration, fullgraph
assay execution/capacity or the CLI. Those remain separate gates.

#### Task7B3h: remove nested historical scans within authentic validation

**Files:** Update `experiment/recorder.py` and `experiment/replay.py`; create
`tests/experiment/test_recorder_projection.py`; update status docs.

Original read-only measurement: a genuine 64-anchor, 7,009-event prefix required
239,425 raw event consumptions in 38.398736 seconds. Source/artifact hashes stayed
unchanged. The full producer-loop traversal count of 120,410,288 is a call-graph
inference, not isolated wall-time attribution of the fourteen-hour native case.

- [x] Add a genuine deterministic RED regression counting raw reads during one
  complete chain scan; require one outer traversal and no historical rereads.
- [x] Share strict branch operation projection and use ephemeral scanner state
  with a bounded SHA256 accumulator over the exact canonical operation array.
  Independently compare all source/header/prefix fields and preserve grammar,
  deferred global/branch errors, mutation checks and actual checkpoint occurrence.
  This provides cryptographic equality under the existing hash assumption;
  it does not compare reconstructed operation arrays byte for byte.
- [x] Preserve standalone full-prefix authentication, live recorder physical
  rereads, wire/schema hashes, current-byte revalidation and verifier-only native
  attestations. Keep ordinary unanchored/legacy acceptance and bounded history
  memory; run existing integrity guards and new differential/projection tests.
- [x] Measure the same authentic prefix after the change, freeze reviewed bytes,
  obtain fresh independent integrity review and run one complete opt-in suite
  including the unchanged all-factor native case before explicit feature push.

No persistent trust cache, public skip-validation mode, new scientific support,
formal qualification or fullgraph capacity claim is introduced by this slice.

Verified 2026-10-05: fresh independent SPEC/QUALITY integrity review passed
with no Critical, Important or Minor findings. The complete opt-in suite passed
all 1,299 cases with zero failures, errors or skips in 2,646.14 seconds
(44 minutes 6 seconds), versus the prior 52,202.15 seconds. The unchanged genuine
all-factor native case took 1,701.331 seconds (28 minutes 21 seconds), versus
50,563.872 seconds: about 29.7 times faster in this comparison. The same authentic
64-anchor parser scan dropped from 38.398736 to 1.614710 seconds, with 7,009 raw
event reads and no historical readers. These local and end-to-end measurements
are separate evidence; neither establishes fullgraph assay capacity.

The fresh native artifact retains all 14,048 events, 40 trainings, 24 interventions,
768 responses, 128 native-attested anchors and 67 checkpoints. Independent XML
and artifact checks confirmed the frozen implementation hashes, all 73 existing
producer regressions, 35 new projection regressions, fullgraph checkpoint tests
and native compiler smoke. The scientific report remains `unsupported`, with
the same negative gates; formal qualification/configuration and CLI work remain
pending.

#### Task7B3i: measure bounded fullgraph resource components

**Files:** Create `docs/experiments/2026-10-05-fullgraph-capacity.md`; update
status docs. Keep package source, tests and scientific gates unchanged.
Measurement scripts and native artifacts remain private ignored outputs.

- [x] Measure actual current-source fullgraph factory, state/candidate digests,
  NPZ write/restore/hash, process working set and scoped scratch-file sizes.
  Authenticate the compatible checkpoint and preserve source/checkpoint bytes.
- [x] Repeat a 500-ms black retention call and separate 100-ms A/B/C response
  calls twice from the same source, using production flags; verify native tick
  advances, endpoint digests and telemetry equality excluding wall-clock fields.
- [x] Publish component ranges and clearly scoped memory/storage measurements;
  distinguish illustrative workload arithmetic from total runtime or resource
  guarantees. No formal configuration, qualification or assay capacity claim.
- [x] Obtain fresh independent measurement/report review, check provenance and
  documented arithmetic, then commit/push only the report and plan status.

Verified 2026-10-05: bounded native probe completed in about 21 seconds;
two real fullgraph factories and two repeats per black/A/B/C condition preserved
complete native endpoint and telemetry equality. All 29 package source files and
the compatible checkpoint retain their hashes. The 500-ms black calls took
1.297331/1.359500 seconds; 100-ms A/B/C calls took 0.272256-0.289507 seconds;
process lifetime peak working set was 1,065,197,568 bytes. The linked
[result report](../../experiments/2026-10-05-fullgraph-capacity.md) records
provenance, exact component samples and limitations. Fresh independent
SPEC/QUALITY review passed with no Critical, Important or Minor findings;
root independently checked actual telemetry/checkpoint files, hashes, counters,
determinism and arithmetic. This documentation-only slice preserves the existing
1,299-case acceptance and does not establish whole-assay resource capacity.
A representative-source one-anchor recorder/replay pilot remains the next
resource gate; formal qualification and configuration remain pending.

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
