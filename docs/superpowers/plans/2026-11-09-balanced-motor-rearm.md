# Activity-Balanced Motor Rearm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development sequentially. Sol owns one bounded
> implementation task; Astra independently reviews source and evidence. No worker
> subagents. Preserve others' edits; the controller owns docs and Git operations.

**Goal:** Implement and evaluate one offline v2 rearm candidate without modifying
the accepted v1 decoder or running the neural model again.
**Architecture:** A thin external subclass adds one measured release condition;
all existing decision and ordering machinery remains in the frozen base. The
controller subsequently replays the accepted recording as development evidence.
**Tech Stack:** Existing Python 3.12, standard library and pytest; no dependency.
**Spec:** [activity-balanced rearm v2](../specs/2026-11-09-balanced-motor-rearm.md).
**Status:** Prospective offline scope and Task1 source independently accepted by
Astra. All199 focused tests pass (101new +98unchanged v1), zero skips;105 existing
tracked source/helper/core/lock files remain byte-identical. Concrete preflight
and one full development replay are independently accepted. The
[result is negative](../../experiments/2026-11-09-balanced-motor-rearm.md): all192
results equal v1, zero balanced releases and zero proposals. Source/result
checkpoint publication and CI remain. No additional decoder iteration or native
run is justified by this candidate's result.

## Global constraints

- Work on `feat/connectome-experiment-core`; preserve v1, its tests, package,
  locks, accepted helpers/runners/supervisors and all prior artifacts unchanged.
- Four non-overlapping accepted unarmed samples, combined total at least20;
  each satisfies `10*abs(R-L) <= L+R`. Original quiet-pair route has precedence.
- No release sample reuse, sliding search, timer, artificial sample, baseline
  subtraction, forced alternation, parameter sweep or changed expiry.
- Same five result fields; new `ready / balanced_ready` reason and v2 identity.
- No native acquisition, provider call, Stage C, deploy, PR or merge.
- Controller owns documentation and explicit reviewed commit/push; workers never
  stage or commit. Record real RED/GREEN commands, skips and failures.

## Review focus

1. A v1 drop/reset still reaching the new release buffer: retain validation,
   freshness, source/session boundaries and expiry before considering balance.
2. Quiet precedence or failed-block cleanup accidentally sharing evidence with
   a decision: test exact indices at partial/four-sample block boundaries.
3. Failed reconfiguration leaving mixed v1/v2 identity: preserve declared v2
   configuration and clear all decision/rearm state consistently.
4. Numeric type confusion or aggregate overflow: retain v1 JSON-safe validation
   and exact rational arithmetic, including four-sample totals.
5. Reporting historical success as independent confirmation: retain the original
   v1 report and label every candidate trace as later development replay.

## Task 1 — thin decoder candidate and synthetic tests (Sol)

**Files:** Create `scripts/market_motor_readout_v2.py` and
`tests/test_market_motor_readout_v2.py`; modify only one CI test-list entry in
`.github/workflows/compatibility.yml`. Do not edit the base or existing tests.

**Interfaces:** `MotorReadoutV2` mirrors the base public API and configuration
shape with the spec's exact extra policy keys and version. Import the base through
the existing scripts path. Explicit private dependencies are acceptable and must
be documented. Reuse base validation/ordering/measurement; do not duplicate its
state machine or mutate its globals. Report any interface conflict before edits.

Builder-checked details: `_clear()` is dynamically called during the base
constructor, so initialize the balance buffer there without assuming it already
exists. Call `super()._consume()` first and admit only its exact unarmed waiting
result. `neutral_ready` clears the balance buffer and returns immediately; a
failed four-sample block clears only that buffer, preserving the quiet streak.
Always validate the complete block with `_measurement()` before its band/minimum
test. Successful reconfiguration rebinds v2 identity; failed reconfiguration keeps
the prior configuration/boundary and original ordering behavior. Post-anchor raw
history still includes releases, but decision support never reuses those samples.

- [x] Write RED tests for quiet release, four `(3,3)` samples producing
  `balanced_ready`, insufficient total, and the exact band: `(9,11)` accepted,
  `(8,12)` rejected, in four-sample blocks. Two `(2,2)` plus two `(3,3)` meet
  total20 without a quiet release; four `(2,2)` remain below20. Interleaved
  `(0,0),(5,5),(0,0),(5,5)` uses balanced release; `(5,5),(5,5),(0,0),(0,0)`
  releases by the quiet route on the fourth sample despite satisfying both rules.
- [x] Write rejection cases for alternating `(10,0)/(0,10)` despite zero net,
  sustained one-sided activity, and a three-sample balanced suffix followed by
  a new block that would pass only if a sliding window were used. Verify that a
  valid quiet pair can span a rejected balance-block boundary.
- [x] Test release/decision support disjointness, partial-balance discard on
  quiet release, and all twenty literal routes using synthetic balanced releases
  plus unchanged supported direction and price blocks. Full400-to700 targets stay
  attainable synthetically, without implying a per-change cap or real selection.
- [x] Test stale/invalid samples, gap/overlap/source-session changes, rewind,
  pause/resume/reset, both expiry boundaries and successful/failed reconfigure
  while balance is partial. Dropped samples never count; previous ordering
  watermarks cannot decrease. Use exact JSON-safe boundaries and bool rejection.
- [x] Test left/right symmetry of rearming and supported directions, immutable
  detached configuration/results, distinct v2 digest and proposal identity,
  bounded rearm/history storage and unchanged imported v1 policy/configuration.
- [x] Run focused tests RED with the implementation absent; record actual output.
- [x] Implement the small subclass and fixed identity, then run the focused suite
  GREEN plus the unchanged98-case base suite. Add exactly one CI filename.
- [x] Astra reviews the source, contracts, arithmetic and actual test evidence.
  Fix findings test-first, preserve old bytes and freeze reviewed source hashes.

Example focused command (fresh basetemp if host execution is needed):

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_market_motor_readout_v2.py tests/test_market_motor_readout.py
```

## Task 2 — one development replay and checkpoint (controller)

**Files:** Add the actual result only after replay at
`docs/experiments/2026-11-09-balanced-motor-rearm.md`; update this plan, the parent
market plan and `docs/cloud-handover.md`. Local trace/metrics remain ignored under
`.tools/balanced-motor-rearm-20261109/`. No second production runner is needed.

**Consumes:** Reviewed `MotorReadoutV2`, immutable accepted v1 protocol/raw data,
and the accepted public `inspect_probe` result. **Produces:** a separate complete
candidate input/result trace and honest descriptive metrics, not native evidence.

- [x] Verify baseline public inspection and raw manifest/events hashes, review
  the bounded replay command with Astra, and freeze candidate configuration/hash
  before executing it. Use all192 unchanged samples and original `readout_now_ms`.
- [x] Execute once without neural construction or network/process starts. Record
  all candidate results and rearm support indices, final partial state and
  counters; compare all source-recording hashes before and after. No cutoff sweep.
- [x] Astra independently reviews the actual trace and reproduces the candidate
  result. Distinguish synthetic software acceptance from development feasibility;
  preserve zero-result or dominant-route outcomes without tuning.
- [x] Inspect full explicit staged diff/size, publish the reviewed source/result
  checkpoint, observe CI, and update the tracked continuation status. A new
  candidate/native acquisition/Stage C is not an automatic next task.

Checkpoint `c73fa83384f698c4793a7b32d5ab84c1251f2a67` passed
[CI42686215403](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42686215403):
766 backend tests /41 skips in320.85s,243 viewer tests /four skips and build.

Self-review: Task1 owns only the additional latch and v2 identity; Task2 consumes
that public API after acceptance. The spec fixes timing, block alignment and
quiet precedence. No native integration or product-state change is concealed in
the controller's read-only development replay.
