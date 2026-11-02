# Strict Qualification Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit one independently reassessed qualification terminal and freeze only genuinely supported sealed evidence.

**Architecture:** Reuse declaration arithmetic, bounded e.2 pair comparison and authenticated grid reconstruction. One engine-free evaluator consumes genuine qualification context; intermediate dictionaries confer no proof. Qualification retains production/lifecycle ownership.

**Tech Stack:** Python 3.12, NumPy 2.4.6, existing recorder JSON/schema and native checkpoint codec; no new dependencies, source modules or framework.

**Spec:** [Strict qualification contract](../specs/2026-11-01-strict-qualification-contract.md), alongside the [current assay plan](2026-09-24-associative-plasticity-assay.md) and [continuation record](../../cloud-handover.md).

**Status:** f.1 is implemented and accepted on source `73994df1e35e1bd51407d863f42733551b994b8d2dbc8503a60bda33597e35ef`, with schema unchanged. f.2 design below is ratified but NOT released; f.3–f.6 remain future. Earlier e.3 acceptance is historical/source-specific, not current formal qualification. Unchecked commands remain planned checks.

## Global Constraints

- Preserve confirmation/False behavior, core/provenance, MBON11 endpoint equations and existing configuration serialization. Packaged `.py`/`.cpp` changes invalidate previous formal qualification/configuration/confirmation identities; complete source-bearing work before Task9.
- No provisional frozen config, invented metric, native-context fallback, extra selected checkpoint, response-history issuer or 408 archive scans. Bind genuine context at intake and final recheck; maps precede numeric decoding.
- Keep grid and selected-control/washout measurements separate; remove cross-protocol washout equality. Qualification C fails at integer count `<1`; confirmation fails at `<=1`. No tolerance or training/response W-metric substitution.
- Require **THREE** native verification boundaries/factories: grid prefix before selected production, final prefix before terminal, independently verified seal after close. Count all three in later resource evidence.
- The operational branch cap is 4096 until f.3's conditional proof. Confirmation stays at 4096; checkpoint/relevant-event limits remain 2048/10000. g owns actual integrated capacity/assay CLI; LF/source freeze and Task9 formal qualification remain open. No scientific support follows from this plan.

## Review Focus

1. Rounded one-count C boundaries must retain integer decisions across populations/windows: f.1.
2. Late target events and EOF mutations must fail despite earlier semantic errors: f.2/f.3.
3. Equal-hash occurrence aliases and PRE over-reuse must not satisfy exact ownership: f.3.
4. Terminal self-inclusion and failed selected gates must preserve truthful evidence/selection: f.4.
5. Synthetic/subclass proof and final-owner mutation during checkpoint writing must reject: f.5/f.6.

## Fixed Contracts

All objects are closed. Reject extras, Boolean numbers, nonfinite values and invalid enums. Reasons are sorted unique strings: at most 1024 entries, each at most 256 characters; overflow raises, never truncates. Preserve existing identifier/map bounds.

Execution reuses e.3's exact nine fields:
`family,seeds,engine_identity,mbon11_population_size,candidate_identity,selected_configuration,response_window,retention_times_ms,input_sha256`.
No artifact placeholder, floor or trusted flag belongs here.

Selection is null or
`{selected_configuration,selected_window,selected_retention_ms,observed_effect_sign}`
from reconstructed grid values. Configuration/window retain existing dataclass keys/choices; T is integer 10000/20000/30000/60000, sign integer ±1. Selected-gate failure retains selection.

Canonical report is exactly
`{report_version,status,reasons,grid,selected,verification}`:

- Version `strict-qualification-report/v1`; status supported/unsupported/inconclusive.
- Grid `{outcome,unit_count,point_count,selection}`; outcome selected/negative/inconclusive.
- Selected `{physical_pre_count,physical_post_count,logical_count,training_count,intervention_count,anchor_count,control_count,metrics}`; actual nonnegative integer counts include incomplete prefixes; metrics=null until complete valid selected evidence.
- Verification `{mode,qualification_map_checked,black_retention_anchor_count}`; mode=`native-replay`, genuine map check=true, actual attested anchor count. This describes existing verification, not acquisition/response history.

Complete negative grid uses `grid_no_eligible_point`; preserve `grid_incomplete`/`grid_unavailable`. Selected incomplete uses `selected_incomplete`; missing final framing uses `qualification_final_incomplete`. Selected scientific failures preserve `_assess` reasons/order; supported has no reasons. Terminal readiness requires complete 96/144 grid and actual final checkpoint, plus full selected/control inventory for selected routes. Complete unavailable-grid evidence may seal inconclusive; incomplete selected routes cannot.

Metrics have exactly
`{replay_resolution_hz,max_abs_control_delta_hz,dynamic_range_hz,effect_floor_hz,one_spike_floor_hz,cells}`.
Use maximum paired replay resolution, maximum absolute four-control delta, maximum paired PRE A/B difference, floor=`max(5r,2control,0.05dynamic)` and canonical one-spike Hz. W-repeat resolution remains independently checked.

Cells have exactly sixteen seed/identity/order/T keys, each containing:

```text
rates_hz,delta_hz,endogenous_dan_spikes,pre_C_hz,post_C_hz,
global_gain_factor,global_gain_residual_hz,paired_minus_frozen_plasticity_hz,
paired_minus_no_external_dan_hz,paired_minus_temporally_unpaired_hz,
paired_minus_necessity_hz,necessity_minus_reference_hz,
sufficiency_minus_reference_hz,sham_minus_paired_hz,raw_A_minus_B_change_hz
```

Rate maps cover all eight CONDITIONS and six pre_A/pre_B/pre_C/post_A/post_B/post_C keys. Delta/count maps cover all CONDITIONS; counts are integers. Only the two global-gain values may be null when C fails. Preserve `_assess` equations.

Emit exactly 40 `qualification_control` events on the existing summary branch. Closed `control`:
`{seed,paired_identity,presentation_order,condition,retention_ms,pre_mbon11,post_mbon11,delta_hz}`.
Five ORDINARY_CONDITIONS×eight factors, selected T only; rate arrays are A/B/C length 3. Both T remain in report cells. No default secondary zeros or second control protocol.

Strict `qualification_result` has existing OWNED framing plus exactly:

```text
type,branch_id,sim_ms,parent_branch_id,parent_checkpoint_sha256,result_version,
analysis_version,status,family,seeds,selected_configuration,selected_window,
selected_retention_ms,observed_effect_sign,reasons,report,report_sha256,
evidence_event_count,evidence_final_scientific_sha256,benchmark,compute_seconds
```

Result version=`strict-qualification-result/v1`; analysis version unchanged. Preserve summary branch/clock 0/baseline ancestry. Selection fields are all null or all selected independently of status. Benchmark retains existing shape and is excluded from assessment equality.

Report hash is SHA256 of existing canonical UTF-8 JSON without newline. Evidence count/hash cover EVERY preterminal event, including final checkpoint/controls; terminal sequence=count, previous digest=hash. Canonical assessment excludes terminal, timings/benchmark and sealed hashes. Independently compare report, selection, status/reasons, evidence identity, terminal position and sealed tail exactly. Unversioned legacy terminals retain existing intake only; unknown/hybrid versions reject. Legacy readability cannot authorize strict freezing.

## Sequential Implementation

Each slice needs actual RED before implementation, hash-bound GREEN results, independent review and a reviewed checkpoint before continuation. Record commands, failures, skips and dependencies; stage only owned paths. No run/support/cap activation is asserted by these unchecked steps.

### f.1: Declaration Arithmetic and Integer C

**Ownership:** Modify `src/fly_connectome_sim/experiment/analysis.py`; test `tests/experiment/test_analysis.py`. This bounded slice is accepted.

- [x] RED `test_declared_reduction_matches_frozen_wrapper` compares every EvidenceReduction field; `test_declared_reduction_needs_no_frozen_artifact` supplies no artifact fields. `test_qualification_c_boundary_is_integer` covers PRE/POST C counts 0/1/2, populations 3/13/7 and all three windows. One count passes qualification C and fails confirmation C; unrelated failures remain visible.
- [x] Move the existing reducer body into `_reduce_declared_evidence(events: Iterable[dict], declarations: dict, *, event_type: str, attested_state_anchors: Iterable[str]=()) -> EvidenceReduction`. Closed declarations: `engine_identity,mbon11_population_size,candidate_identity,selected_configuration,response_window,retention_times_ms`, plus `confirmation_input_sha256` only for assay_response. Existing predicates validate identity/schedule/inputs; event type fixes family/seeds. Caller anchor strings remain arithmetic inputs, never proof.
- [x] Keep public `reduce_assay_evidence` signature/Frozen validation and project these fields. Change `_assess(reduction, config, seeds, *, strict_c: bool) -> AssayReport`; explicit False for qualification, True for confirmation; reject non-bool. No new wire/lifecycle/cap behavior or FixtureRun fallback; public-freeze migration waits for f.5.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py -k "declared_reduction or qualification_c_boundary or consumer_retains_counts or consumer_one_c_spike" -q -p no:cacheprovider`; record RED/GREEN, then affected compatibility/review.

Accepted R1 full analysis:345 passed/184.58 s, no skips/errors/failures. Focused130 and hook-eight overlap this run. Source-identical R0 related modules:1305 passed/four skips/953.91 s; three skipped context/junction cases separately passed on R1 normal host/15.55 s. Complete96 remains unrun. The two-line test-hook fix closed the sole review finding; no strict lifecycle is implemented.

### f.2: One Bounded Pair Checker

**Ownership:** Same analysis source/test paths as f.1.

- [ ] RED wrapper/dispatcher equivalence for existing PRE/POST/intervention faults, optional thaw, third window, signed zero and after-diagnostic activity.
- [ ] Extract ONE existing comparison kernel with this private API; preserve `_compare_selected_replay`'s existing signature as its full-EOF adapter:

```text
_SelectedReplayChecker(physical_key, *, expected_anchor_sha256, metadata,
 execution, expected_source_occurrence, expected_start, expected_maps, n,
 memory_count, edge_count, lower, upper, prior_events=())
consume(event) -> None
finish(diagnostic) -> dict
```

Return exactly `{response_replay_resolution_hz,candidate_memory_w_resolution}`.

- [ ] Validate `prior_events` as an exact tuple of at most five distinct actual unchanged events: PRE baseline1; ordinary POST checkpoint/training/anchor3; intervention POST recipient checkpoint/training, intervention checkpoint/event, anchor5. Role aliases share occurrences. Require strictly increasing non-bool integer global sequences, permit gaps; never sort/renumber/deduplicate malformed input. Seed before pair activity through the same collection path; data confer no authority.
- [ ] Require `expected_anchor_sha256`: valid POST digest, exactly None for PRE. Select ALL matching-hash anchors regardless of branch/origin/source/clock, then validate. Malformed-first/healthy-later fails; wrong-hash canonical anchors cannot replace it. Bind finish's actual diagnostic to that hash. The adapter takes it from its caller diagnostic without decoding W.
- [ ] Retain ≤12 operations/16 PRE rows(one POST) in actual interleaving. Finish consumes the actual diagnostic once instead of `consume`, strictly after captured activity; compare full caller/actual diagnostic, references, windows, rows and tails with unchanged arithmetic. Bind maps/model before numeric decode. Release payload/vectors on success AND semantic failure; duplicate finish rejects. Store bounded error strings, no traceback objects; callers drain EOF after constructor/semantic errors and propagate iterator/final-binding errors.
- [ ] Keep only compact branch/training/intervention IDs, anchor hash and scalar result/error/closed state afterward. Reject matching late activity despite changed branch/origin. Local adapter rejects ANY later target event, including final checkpoints; withhold its result until clean EOF. No second decoder/model, fake diagnostic, history scan or trust issuer. RED also covers malformed chronology, seeded equivalence, decoder timing, matching-hash anchor with altered origin AND source before a healthy anchor, wrong clock, mismatched finish hash, late anchor/route duplicates, release and repeated finish.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py -k "selected_replay or candidate_w_pair" -q -p no:cacheprovider`, including new equivalence tests; record actual RED/GREEN and review before global use.

### f.3: Global Ownership and Shared Assessment

**Ownership:** `analysis.py`, `qualification_grid.py` under `src/fly_connectome_sim/experiment/`; corresponding `tests/experiment/test_analysis.py`, `test_qualification_grid.py`.

- [ ] RED missing/duplicate 96 bindings/144 points, discarded-grid corruption, selected orphans/late events, exact 24 PRE/384 POST/768 logical cells, PRE reuse 16, 40 trainings/24 interventions/128 anchors, occurrence aliases, final branch/archive mismatch and EOF failure after semantic error.
- [ ] Implement `_evaluate_qualification(value: ValidatedPrefix | VerifiedRun) -> dict`, exactly `{grid,execution,reduction,controls,last_physical,evidence,report}`. Reuse grid/reduction dataclasses; reduction=null before complete selected evidence, execution=null without selection; controls are ordered tuples. Last physical=null or `{branch_id,sim_tick,parent,complete_state_sha256}`, unavailable digest=null. Evidence=`{event_count,final_scientific_sha256}` excludes terminal. These are plain data.
- [ ] Pass 1 owns closed roles/references/occurrences without W payload retention. Pass 2 reconstructs grid selection before selected activity, consuming one pair/archive and finished scalar rows. Share an internal reduction accumulator; pass actual global sequence explicitly. Read baseline/source/final archives through existing codec/state hashing and genuine context; NPZ byte SHA is not state SHA. Global dispatcher owns completeness/late events and drains both streams after bounded semantic errors; iterator errors propagate.
- [ ] Preserve valid incomplete-prefix inconclusive versus malformed-after-drain errors and complete negatives. Remove cross-protocol washout equality. `_selected_control_summaries(reduction, retention: int) -> tuple[dict,...]` derives 40 controls; compare present claims, requiring summaries/final only for terminal readiness.
- [ ] Supply expected anchor hash from actual indexed prior anchor, reconciled with compact diagnostic parent hash, without retaining408 W payloads. Own compact late watches after checker disposal. Admit exactly ONE ordinary `checkpoint` named `brain-after.npz` after full selected/control inventory on the actual last repeat branch, bound to diagnostic/native owner/anchor/clock/decoded archive. Never feed this final framing to the discarded checker or generalize it to late activity.
- [ ] Prove role bijection/≤4850 branches/1602 checkpoints/8099 relevant events using e.3 conformance and finite grid enumeration; only then enable 5120 for strict qualification global inventory. Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py tests/experiment/test_qualification_grid.py -q -p no:cacheprovider` and review; this proves grammar, not capacity.

### f.4: Strict Terminal Wire

**Ownership:** `src/fly_connectome_sim/experiment/analysis.py`, `src/fly_connectome_sim/experiment/recorder.py`, `src/fly_connectome_sim/schemas/run.schema.json`; `tests/experiment/test_analysis.py`, `tests/experiment/test_recorder.py`.

- [ ] RED extras/types/versions, unknown metric/cell keys, unsupported-with-selection, premature terminal, report/hash/count mutation, terminal self-inclusion and legacy hybrids.
- [ ] Implement fixed contracts and `_build_qualification_result(prefix: ValidatedPrefix, *, benchmark: dict, compute_seconds: float) -> dict` through fresh shared evaluation, requiring complete final framing. Caller takes preseal report from payload, avoiding redundant evaluation. Recorder checks structure/report hash/prefix only, without analysis imports/vector decoding. Sealed evaluator independently compares terminal.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py tests/experiment/test_recorder.py -q -p no:cacheprovider`, including complete unavailable-grid inconclusive and negative zero-anchor map checks. No early-abort seal or runtime failure converted to unsupported.

### f.5: Sealed-Only Freeze

**Ownership:** Analysis source/test paths from f.1.

- [ ] Migrate FixtureRun arithmetic tests to declaration reduction/assessment and explicitly declared confirmation Frozen fixtures; never forge qualification context. RED rejects subclasses, integrity-only/stale/transplanted proofs and legacy seals at public freeze.
- [ ] `build_frozen_config(VerifiedRun)` invokes shared strict sealed evaluation, requires supported, and constructs final payload once using actual ARTIFACT_FIELDS. No provisional `_freeze`, zero metrics or washout equality; confirmation equations/serialization stay.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_analysis.py tests/experiment/test_replay.py -q -p no:cacheprovider`, including genuine native prefix/seal tests; independently review trust migration.

### f.6: Qualification Lifecycle and Fresh Caller

**Ownership:** `src/fly_connectome_sim/experiment/qualification.py`, `src/fly_connectome_sim/cli.py`; `tests/experiment/test_qualification.py`, `tests/test_cli.py`, narrowly necessary `tests/experiment/test_analysis.py` integration tests.

- [ ] RED authentic selection before e.3, THREE verifier factories, actual final repeat/anchor ancestry, checkpoint-write mutation, failed gates retaining selection, sealed disagreement preventing return and fresh CLI factories.
- [ ] Keep `qualify` signature. Native-verify the zero-anchor grid prefix before selection/True production. Replace old controls with e.3 full matrix; one bounded integrity-prefix handoff scan collects the actual last diagnostic and 40 summary claims. Bind diagnostic lineage/clock/state to owner before and after writing final. Then native-verify final prefix, build/append one terminal and close idempotently. Independently native-verify/reassess seal; return only afterward. Grid-only negative/unavailable uses actual last grid owner. Issue separate contexts at all THREE boundaries, never promote prefix proof. Update QualificationResult status/controls truthfully without dummy ControlMeasurement vectors.
- [ ] Repair qualification CLI fresh-factory caller; no assay command. Run `.venv/Scripts/python.exe -m pytest tests/experiment/test_qualification.py tests/test_cli.py -q -p no:cacheprovider`, independently review, then perform separately budgeted integrated acceptance. Record all three verification/resource costs; g's controlled unprofiled capacity and Task9 remain later gates.
