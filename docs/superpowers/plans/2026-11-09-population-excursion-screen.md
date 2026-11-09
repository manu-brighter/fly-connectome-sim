# Population Excursion Prerequisite Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development sequentially. One fresh Sol implementer;
> Astra reviews protocol, source and evidence. No worker subagents. Preserve
> others' edits; controller owns docs and Git.

**Goal:** Determine whether the fixed candidate has necessary supported state
excursions in the existing continuous development trace before building a decoder.
**Architecture:** A small pure exact-math module plus an external bounded analyzer
reusing the complete frozen probe inspector and the same private snapshot.
**Tech Stack:** Python3.12 standard-library fractions, existing recorder helpers
and pytest; no dependencies or native/provider work.
**Spec:** [fixed20-slot screen](../specs/2026-11-09-population-excursion-screen.md).
**Status:** Prospectively accepted after independent protocol and builder reviews.
No calibration outcomes.

## Global constraints and review focus

- All192 observations including black;48 fixed non-overlapping four-sample blocks.
- Fixed four-channel median/MAD calibration and scale floors; no label fitting,
  feature/threshold sweep, alternate grid or online adaptation.
- Exact signed rational coordinates and fixed40 integer rays; open angular
  boundaries, inclusive radius2 and excursion2. No runtime trigonometry.
- Disjoint membership within the two summed pairs; no global partition assumption.
- Old194-event/two-checkpoint bounds and4MiB exclusive report; preserve all old bytes.
- No proposals, prices, full lifecycle, new recording, API, Stage C, PR or deployment.
- Review failures: unsafe large numeric serialization; ray-boundary ambiguity;
  omitted black/late observations; validator/data snapshot mismatch; favorable
  pair selection or a necessary opportunity mislabelled as operational success.

## Task1 — exact math and bounded analyzer (Sol)

**Own files:** Create `scripts/market_population_state.py`,
`scripts/screen-population-excursion.py`, `tests/test_population_excursion_screen.py`;
add only the new test filename to `.github/workflows/compatibility.yml`.

**Pure interfaces:**

```text
calibrate(count_vectors: list[list[int]], memberships: dict[str,list[int]]) -> dict
classify_coordinate(x: Fraction, y: Fraction) -> dict
screen(count_vectors: list[list[int]], memberships: dict[str,list[int]]) -> dict
```

Count vectors are exactly192 rows of seven counts in spec order. Validate shape,
numeric types and memberships before calibration. `calibrate` returns canonical
four-channel offset/MAD/scale fractions, sizes and exact input identity.
`classify_coordinate` returns radius-squared, radius eligibility, angular-sector
or null, and final qualifying-sector or null. `screen` returns calibration,
all192 observations, all48 blocks, first supported anchor or null and ALL necessary
adjacent-pair opportunities. Record field names before implementation. Keep pure
helpers focused; no future production decoder/state machine.

**External interfaces:**

```text
analyze_probe(output_dir: Path, *, expected_protocol_sha256: str,
              expected_manifest_sha256: str, expected_events_sha256: str) -> dict
write_report(report: dict, output_path: Path) -> None
```

CLI requires `--probe-dir`, all three `--expected-...-sha256` arguments and `--output`.
No auto-discovery, native mode or relaxed verifier. Load the old probe once and
reuse its `_read_protocol`, `_summarize_events`, `READ_LIMITS`, `MAX_CHECKPOINT_BYTES`,
`GROUPS`. The complete inspector already reconstructs v1 decisions and validates
all seven native counts/rates. Extract counts from `event.telemetry.bins[]` on the
second owned scan; ordinal and original timestamps are in `event.motor_sample`,
with original `event.readout_now_ms`. Memberships are in manifest engine identity.
Preserve these fields for provenance without using labels or clocks in calibration.
The old test `FixtureEngine` keeps all four calibration channels zero. It can
cover full null integration, but add a test-local faithful extension or consistently
resealed nonzero bins/rates/whole-brain totals for extraction and positive-opportunity
coverage. Synthetic lock patches must target the analyzer's same loaded probe.
Pairwise disjointness is a new candidate precondition; the old inspector permits
these memberships to overlap and must remain unchanged.

- [ ] Write RED median/MAD cases with192 literal fixtures, even-middle ties,
  zero MAD, both scale floors, exact7413/5000 multiplication, malformed inputs,
  large safe counts and signed reduced-string outputs. Constant complete input
  must have zero coordinates and no supported block.
- [ ] Test all20 sector interiors using literal ray sums; boundary rays and axes
  abstain, radius equality passes, smaller radius fails. Assert frozen table
  digest, opposite/quadrant symmetry and non-overlap. Use exact rational witnesses
  such as `(24/13,10/13)` on radius2 inside sector1.
- [ ] Test support thresholds19/20, two/three active observations, mixed sectors,
  one failed radius/angle, pair overlap and retained rejection details. Combined
  pair counts are distinct-cell support only after disjointness validation.
- [ ] Test fixed48-block alignment, first-anchor selection, inclusive squared
  excursion4, both adjacent blocks required, same-sector excursion allowed,
  interrupted/nonadjacent confirmation rejected and full unranked opportunity list.
- [ ] Test positive synthetic coordinate opportunities through full calibration
  using a majority unchanged baseline and bounded supported excursions. Synthetic
  opportunities must not be called proposals or actual neural feasibility.
- [ ] Build a guarded faithful synthetic continuous recording using existing test
  fixtures on the same loaded probe instance. Verify all192 rows/48 blocks, pins,
  original clocks/provenance, full inspector rejection and same-snapshot derivation
  after originals mutate. No private actual recordings during implementation.
- [ ] Test bounds, wrong pins, malformed counts/memberships, error-path generator
  closure, output collision/links/exact newline-inclusive4MiB and no success file
  on rejection. Native construction/replay and network are forbidden in tests.
- [ ] Run RED before production source, then focused GREEN and relevant unchanged
  probe/helper tests. Record actual commands/results/skips; host execution is
  allowed for required Windows file semantics, never weaken checks.
- [ ] Astra independently reviews source, math, integrity and actual synthetic
  evidence. Fix concrete findings test-first and freeze final source identities.

## Task2 — one actual development screen and checkpoint (controller)

**Own files:** Actual result only after execution at
`docs/experiments/2026-11-09-population-excursion-screen.md`; current plan, market
plan and handover. Raw outputs stay ignored under a fresh evidence directory.

- [ ] Freeze reviewed command, source hashes, original pins and absent output;
  independent concrete preflight before actual calibration/screen calculation.
- [ ] Run once; retain all calibration values, observations, blocks, failures and
  opportunities. Verify source/original artifacts before and after. No rerun/tuning.
- [ ] Astra independently recomputes exact math/full coverage and assesses the
  predeclared stopping condition. No anchor/no opportunity stops this candidate
  before full implementation; an opportunity proves only a necessary condition.
- [ ] Review complete staged diff/size, commit/push explicitly to the feature
  branch, observe CI and update tracked continuation. Later scope depends on
  accepted evidence and cannot relabel this calibration as independent evaluation.

Self-review: Task1 produces validated fixed math from immutable observations;
Task2 supplies actual development data only after acceptance. User tolerance for
quiet phases/favorites does not create proposals from unsupported activity.
