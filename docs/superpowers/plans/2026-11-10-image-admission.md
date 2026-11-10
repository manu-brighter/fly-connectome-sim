# Local Image Admission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first Stage-D metadata lifecycle with bounded admission,
immutable image deadlines and honest worker-outcome states.

**Architecture:** One process-local controller lock protects one receiving-or-
pending slot, one active slot and finite retained receipts. Trusted future adapters
provide hashes/worker receipts; this component does not handle bytes or transport.

**Tech Stack:** Existing Python3.12 stdlib/dataclasses/threading and pytest;
reuse public Clock/ClockSample/SystemClock from the unchanged market authority.

**Spec:** [Exact D1 contract](../specs/2026-11-10-image-admission-design.md).

**Status:** Independently accepted prospectively; no D1 implementation or test pass
is claimed. Stage-C source `b2eda225cf9709f1abf5d383c19106d707eb5444` passed all four
[CI42741755078 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42741755078).
The user's ongoing autonomous execution authorization covers technical choices;
prospective review resolved the exact contract before product code starts.

## Global Constraints

- Only new `market/image_admission.py` and `tests/market/test_image_admission.py`
  are product/test scope. No edits to price_service, ownership, HTTP, viewer,
  package/core, frozen ImageAdmission/CellRing/readouts/runners or dependencies.
- Public types, fields, enum/error strings and keyword-only APIs are exactly the
  spec. Frozen dataclasses and detached returns; no mutable internal references.
- Exact built-in str/int/bool/tuple and exact dataclass types. Times/counts are
  true Python integers in `[0, 2**63-1]`; new controller deadline overflow gives
  capacity before the requested transition. Due maintenance/fault fencing remains
  valid. A current worker start index without headroom for seven following indices
  is instead an atomic unknown-outcome stop, following worker branch precedence.
  Receipt revision follows its finite lifecycle, initially1 and at most6.
- One reservation OR accepted pending, plus one active. All live reservations,
  accepted records and terminal history share512 pre-reserved receipt slots.
- Reserve5s; acceptance occurs only at admit after complete bounded body metadata;
  immutable pending300s, decode10s and moderation60s from accepted_ns. Equality
  expires. Encoded length1..2097152; exact preprocessing version market-rgb64/v1.
- Dispatch-to-start-receipt10s; preserve the original absolute image deadline.
  The future worker polls between observations, emits receipt before image observe
  and checks that deadline immediately before observing. D1 proves metadata only.
- Completion declares exactly eight contiguous observation indices. D1 does not
  prove native observations occurred; later D3 validates real contiguous telemetry.
- Retain terminals15minutes; no pressure eviction, infinite tombstones, unbounded
  action history, automatic retry/requeue or durable-restart claim. Seven fixed
  operation retry slots per accepted record at most; original permits never renew.
- Clock failure/regression latches a stop; confirmed started fields survive any
  failure. Unknown worker outcomes must not be mislabeled conclusive expiry.
- Sol owns the bounded implementation; independent Astra review precedes source
  publication. Workers are not alone and must preserve concurrent documentation.
  No worker Git mutation, child agents, native/API work, dependencies or server.
- Root records prospective docs before implementation. Reviewed local commits may
  be grouped into one explicit feature push to avoid redundant CI cancellation.
  No protected-branch push, PR, merge, deployment, LAN/public upload or event action.

## Review Focus

1. A dispatch near the300s deadline starts legally but its receipt arrives later:
   distinguish known timely start from unknown outcome without extending admission.
2. A contradictory second start for the active image versus an old terminal one:
   current worker uncertainty must stop; historical conflict must not fault new work.
3. Capacity is full while an existing image becomes terminal: reserved receipt
   space must preserve its result without extra allocation or eviction.
4. Clock regression/exception occurs during status/maintenance while an image is
   active: diagnostics remain readable, started fields survive and no reactivation.
5. Old reservation IDs, pruned results or a restarted process must not silently
   become new accepted work or imply durable processed status.

---

### Task1: Complete metadata admission lifecycle and evidence

**Files:** create `market/image_admission.py`,
`tests/market/test_image_admission.py`. Root owns final handover/plan/result docs.

**Interfaces consumed:** unchanged public `Clock`, `ClockSample`, `SystemClock`
from `market.price_service`. A test-local clock implements sample/describe; no
production clock override endpoint or real-time sleep is added.

**Interfaces produced:** all frozen types in the spec; `AdmissionError(code)`;
`AdmissionController(incarnation, clock=None)` and exact keyword-only methods
reserve, cancel_reservation, admit, decoded, decode_failed, moderate, dispatch,
started, complete, stop, maintain, status and snapshot. Downstream adapters do not
exist yet. Do not add speculative public helpers or accept arbitrary dictionaries.

- [ ] Capture the exact reviewed spec/plan and unchanged Stage-C source identities.
  Confirm prescribed branch/tracking and read current handover. Root retains the
  original package/artifact fingerprint before any source changes.
- [ ] Write meaningful failing metadata tests, using fixed UUIDs/digests and a
  controllable nanosecond clock. At minimum cover these independently observable
  cases (parameterize boundaries/invalid exact types without duplicating tests):
  `test_concurrent_reservations_never_overbook`,
  `test_reservation_equality_and_old_cancel`,
  `test_admit_owns_original_deadlines`,
  `test_decode_and_moderation_equality`,
  `test_full_lifecycle_retains_confirmed_start`,
  `test_queued_ttl_boundary_never_renews`,
  `test_4203ms_start_receipt_and_10s_equality`,
  `test_late_receipt_of_timely_start`,
  `test_current_worker_contradictions_stop_before_retry_conflict`,
  `test_completion_without_confirmed_start_is_unknown`,
  `test_terminal_retry_conflict_cannot_fault_new_work`,
  `test_exact_eight_contiguous_indices_and_completion_after_ttl`,
  `test_capacity_reserves_terminal_space_and_prunes_only_by_age`,
  `test_clock_failure_preserves_diagnostic_state`,
  `test_deadline_overflow_without_partial_requested_mutation`,
  `test_worker_index_overflow_atomically_stops_unknown`,
  `test_detached_snapshots_and_restart_scope`.
  Assert exact status/detail/revision/fault/stop_required, slot counts, immutable
  times, preserved started fields, idempotent retries and unchanged unrelated work.
  Worker-receipt tests also include a known accepted/queued ID not dispatched yet,
  and ensure an exact active-start retry does not reapply the receipt deadline.
- [ ] Run initial `.venv/Scripts/python.exe -m pytest -q tests/market/test_image_admission.py`
  with a fresh task-local --basetemp and `-p no:cacheprovider`; retain actual output
  and exit code. Missing module/API or false behavioral assertions are genuine RED;
  infrastructure errors are reported separately, never relabeled product failures.
- [ ] Implement the exact lifecycle in one cohesive module, following the spec's
  worker-receipt branch order before generic idempotency. One lock owns sample,
  expiry, pruning and transitions. Validate syntax before state mutation. Reserve
  terminal capacity at ingress, store at most the fixed operation records, and
  keep all state private and process-local. No payload bytes/file handles/callbacks.
- [ ] Run green focused tests, then the complete `tests/market` suite with fresh
  basetemp/cache disabled. Use `.venv/Scripts/python.exe -m pytest`; never the
  AppControl-blocked pytest.exe. Known sandbox asset resolution errors may use
  identical approved host execution, not weakened assertions. Record all actual
  skips/failures, and preserve the original182-case Linux baseline separately.
- [ ] Provide stable source hashes and exact command/log evidence under ignored
  `.tools/image-admission-20261110/` and the controller's private progress record.
  Confirm no images decoded, no native worker/HTTP started and no prices changed.
- [ ] Independent Astra evaluates complete source, spec, tests and actual evidence,
  especially all five Review Focus items. Resolve actionable findings with real
  regressions. Never treat an interrupted review as acceptance.
- [ ] Root compares all preexisting sources/package/artifacts, inspects exact staged
  first-party paths/full diff and records a reviewed checkpoint on the existing
  feature branch. Update handover/status with actual results and pending limits.
- [ ] Explicit feature push and await terminal clean-checkout CI; existing
  `market_price` command automatically discovers this new test module. Keep every
  original native/buffer/viewer job unchanged. Record actual source SHA/run/counts
  and skipped cases before declaring this slice complete.

## Self-review and continuation

The single task owns one cohesive lifecycle rather than splitting a shared lock
across workers. Every spec transition, bounded resource and failure category maps
to a named behavioral test group above; the independent reviewer checks exact
branch priorities. The plan intentionally references the complete type contract
instead of duplicating it. No runtime image, native or public security result is
inferred from metadata tests.

After this slice's evidence gate, separately specify bounded decoder/local intake,
owned worker telemetry, explicit native-price admission and scientific live UI.
Do not connect through synthetic run_fixture or alter replay parsers. A later
actual native recording needs its own reviewed finite protocol/source freeze.
