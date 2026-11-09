# Recorded Response Structure Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development sequentially. Sol implements one bounded
> analyzer; Astra reviews source, arithmetic and actual evidence. No worker
> subagents. Preserve others' edits; controller owns docs and Git operations.

**Goal:** Characterize composition versus global scaling in the accepted diagnostic
without changing a decoder or running the neural model.
**Architecture:** One external analyzer validates the entire existing diagnostic
through its frozen inspector, then derives fixed vectors and exact comparisons
from the same private snapshot. A separate controller step evaluates actual data.
**Tech Stack:** Existing Python3.12, standard library fractions, pytest and recorder
helpers; no new dependencies or service.
**Spec:** [bounded response inventory](../specs/2026-11-09-response-structure-inventory.md).
**Status:** Source, synthetic tests and one actual inventory independently accepted.
[Actual result](../../experiments/2026-11-09-response-structure-inventory.md):64 vectors,
224 comparisons; some active KC distributions differ, without decoder qualification.
Source/result publication and clean-checkout CI remain to finish.

## Global constraints

- Same feature branch; no package/lock/decoder/old-script/artifact changes.
- Exactly64 arm/windows and224 paired comparisons; window7 stays primary.
- Fixed20 eleven-cell KC groups plus11 excluded sampled KCs as a separate bucket;
  all231 recorded KCs covered once. No whole-graph individual-cell claim.
- Exact cross-products; reduced string fractions and canonical decimal-string
  component sums even above2^53-1, explicit undefined zero cases.
- No seven-population composition shares/TV because membership may overlap.
- Old79-event/three-checkpoint read limits; new report maximum4MiB, exclusive output.
- No model run, provider call, candidate fitting, parameter sweep, price mapping,
  Stage C, PR, merge or deployment. No actual outcomes during implementation.

## Review focus

1. Cohort slots mistaken for model indices or excluded cells omitted: reject
   partition gaps/overlap and retain the excluded bucket explicitly.
2. Zero or weak activity inflated into a normalized result: raw counts retained,
   null undefined shares/comparisons; exact differences get no usefulness label.
3. Overlapping population counts treated as distinct-cell composition: only
   per-population rates and algebraic common-scaling relation are allowed.
4. Validated-source/analysis-source race: calculate from the same bounded private
   snapshot after full inspector acceptance, check caller-pinned file hashes.
5. Primary windows or convenient pairs cherry-picked: fixed full matrix and
   repeat labels; primary rows remain part of the secondary course.

## Task1 — analyzer and synthetic checks (Sol)

**Files:** Create `scripts/analyze-response-structure.py` and
`tests/test_response_structure.py`; add only its test filename to
`.github/workflows/compatibility.yml`. No old-source edits.

**Interfaces:**

```text
compare_vectors(left, right, *, composition: bool) -> dict
analyze_diagnostic(output_dir: Path, *, expected_protocol_sha256: str,
                   expected_manifest_sha256: str, expected_events_sha256: str) -> dict
write_report(report: dict, output_path: Path) -> None
```

The pure comparison returns relation, component sums, exact optional TV and
display decimal; composition=false never emits shares/TV. Integration derives
KC shares separately and supplies fixed vector order. Choose exact report field
names consistently and record them before implementation; do not add a pass flag.
CLI requires `--diagnostic-dir`, all three `--expected-…-sha256` flags and
`--output`; no auto-discovery, native mode or permissive verifier flags.

Reuse `run-market-response-diagnostic.py` via an explicit module loader. Its
`_read_protocol`, `_summarize`, `READ_LIMITS`, `MAX_CHECKPOINT_BYTES`, `ARMS` and
`GROUPS` are private frozen dependencies. `summary.secondary[w].arms[arm]` supplies
validated20-group counts. Native population counts come from
`event.telemetry.bins[].group_spikes`; cell counts from `event.cell_bins[].counts`.
Grouping entries and excluded_kc_slots are cohort slots. Header cells describe
their model indices and memberships. Close event generators on error paths.
The analyzer owns the inspector's iterator under `contextlib.closing`, passing a
minimal same-run manifest/mode/iterator view because the frozen inspector does not
close its iterator on exception. Test early semantic rejection with a retained
traceback: original error survives, iterator closes and snapshot is removed.
Use `event.branch_id` and `(event.start_tick - 20000) // 5000` for the arm/window
mapping, checking global observer ordinal `4 + arm_index*8 + window`. The existing
SyntheticEngine fixture hardcodes220KC/226cells and cannot directly satisfy this
231KC/256cell contract. Provide a faithful new fixture; reuse loaders/lock setup
only on the same diagnostic module instance used by the analyzer.

- [x] Write RED exact math tests: scaled `[1,2]`/`[2,4]` gives proportional TV0;
  `[3,1]`/`[1,3]` gives nonproportional TV1/2. Test both/one-silent null cases,
  malformed bool/negative/fractional/empty/mismatched values, large JSON-safe
  counts whose products and sums exceed2^53, reduced fractions and symmetric
  comparisons. Assert exact decimal-string sums above the safe-integer boundary.
- [x] Write synthetic fixed-partition tests including shuffled non-slot model
  indices, an excluded-bucket-only composition change, disjoint complete231KC
  coverage, wrong/missing/duplicate members and all21-bucket arithmetic.
- [x] Test overlapping seven-population memberships, exact rates and scaling;
  no population shares/TV or distinct-cell summed-total claim is emitted.
- [x] Write complete synthetic integration using existing diagnostic fixtures or
  faithful guarded recorder fixtures. Verify all64 rows/224 comparisons/28 primary
  flags and three repeated-input pairs at each window, source/hash binding, all
  secondary windows, and original files unchanged. Do not open private recordings.
- [x] Test wrong expected hashes, malformed/altered recorded values, inspector
  rejection, omitted/extra windows, output collision/links/4MiB limit and bounded
  reads. Prove output derives from the validated snapshot, not changed originals.
  Invalid input never publishes a successful report; no native/network call occurs.
- [x] Run RED before source creation; implement minimally, then GREEN with
  relevant unchanged diagnostic/artifact tests. Avoid broad native tests. Record
  real commands/results/skips; use host execution only for required file semantics.
- [x] Astra independently reviews source, arithmetic and actual synthetic evidence;
  fix findings test-first, then freeze accepted source identities before Task2.

## Task2 — actual inventory and checkpoint (controller)

**Files:** Create `docs/experiments/2026-11-09-response-structure-inventory.md` only
after actual analysis; update this plan, parent market plan and handover. Raw JSON
stays ignored under a fresh `.tools/response-structure-20261109/` evidence root.

- [x] Freeze reviewed command/source/three expected hashes and exclusive output;
  obtain independent concrete offline preflight before calculating actual results.
- [x] Run once on the accepted diagnostic without native execution or source edits.
  Preserve all64 rows and224 comparisons, zeros, repeats and primary labels.
- [x] Independently audit actual vectors, fractions, matrix coverage and complete
  source preservation with Astra. Report only descriptive development evidence and
  follow the spec's stopping rules; no selected calibration or decoder is implied.
- [ ] Inspect complete explicit staged diff/size, commit/push reviewed code/result,
  observe CI and update tracked continuation. Decide any distinct next scope only
  from accepted evidence; no automatic acquisition or Stage C.

Self-review: Task1 produces bounded validated vectors and exact math; Task2 consumes
the pinned old recording only after acceptance. All comparison choices are fixed
before calculation. Existing primary results and motor negatives remain unchanged.
