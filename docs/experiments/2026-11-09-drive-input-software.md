# Fixed-input comparison — software evidence

Status: Task1 runner/auditor and Task2 supervisor independently accepted by Astra.
Source-CI, concrete preflight and actual acquisition remain outstanding. Evidence is software
verification; no new neural response or actual optical projection was calculated.

The [protocol](../superpowers/specs/2026-11-09-drive-input-comparison.md) and
[plan](../superpowers/plans/2026-11-09-drive-input-comparison.md) were reviewed and
frozen as `8fec9466a1a655fe46917d650f4d258ece2c7e0e` before implementation.
That prospective checkpoint passed
[CI42704146157](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42704146157):
1350 backend tests /41 skips in548.50s,243 viewer tests /four skips and build.
This precedes the new runner source and is not its source-CI evidence.

## Implemented boundary

The external `run-drive-input-comparison.py` prepares the exact source-bound
protocol, records4s black plus four restored20s arms and independently inspects
all175 sealed events/168 observations/8400 bins/three checkpoints. Each arm has a
fresh unchanged decoder; restoration never rewinds actual monotonic clocks.
The prefix is recorded without feeding the decoder. Native construction requires
the separate, lazily imported supervisor authority; there is no CLI test-factory
or synthetic-clock override.

Optical declarations preserve ordered3335 R1–R6 and811 R8 samples per frame,
their raw Float64-C-order hashes, arithmetic and retinal-array provenance. Source
checks require projection to leave complete state, model clock and identity
unchanged. These samples precede current/filtering dynamics and are not neural
responses. The reader validates stored declarations without constructing an engine.

The auditor owns a bounded snapshot and closes its full-EOF iterator even on
retained exceptions. It reconstructs every motor sample and decoder result from
raw counts and clocks. Repeat mismatch is retained as not evaluable; output count,
matched drink/price sequences, timing-only and count-only differences stay distinct.
Open paths include detached direction/history/block/anchor/arming evidence.
Resource interpretation remains conditional on the separately verified supervisor
receipt. Integrity-only inspection does not attest native execution or resource use.

## Verification and review

Final focused run: **150 passed,330 deliberately deselected, zero skips in100.39s**.
This contains all56 new cases,88 unchanged driver cases and six unchanged
telemetry/type/overlap checks. The330 unchanged reachability-matrix cases had
already passed in the preceding CI; no unrelated broad local suite was repeated.

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=.tools/drive-input-comparison-implementation-20261109/final-focused tests/test_drive_input_comparison.py tests/test_market_continuous_drive.py tests/test_continuous_motor_probe.py::test_resealed_total_spikes_cannot_omit_disjoint_population_counts tests/test_continuous_motor_probe.py::test_resealed_total_spikes_uses_disjoint_subsets_without_overlap_double_count tests/test_continuous_motor_probe.py::test_resealed_equal_valued_json_type_contradictions_fail -k 'not every_leaf_all_sizes_both_endpoints'
```

Use a fresh basetemp for any separately justified future run; the documented
directory is completed evidence. Tests cover wrong source/frame/session/state/
clocks/counts/rates/bins, resealed semantic alterations, projection bounds/arithmetic,
restoration failure, retained partials, full EOF, collisions, parser/summary caps,
offline no-native/no-network behavior and guarded native-factory placement.
The summary-size cap is an explicit unit test of the actual summarizer helper.

Test history remains explicit: initial sandbox temp cleanup failed before tests;
then the intended missing-module RED passed its purpose. The unchanged exclusive
hardlink writer caused47 sandbox failures; regular host execution resolved that
environmental restriction without modifying the writer. First host run had46
passes and one stale-fixture timing error: clock read140 shifted completion,141
shifts delivery. The fixture was corrected without changing production thresholds.
Review found one production issue: incomplete pending-state reporting. Direction
and price-path RED tests, including a detached-copy RED, preceded its correction.
A subsequent54-pass/one-fail test attempted to change a frozen summary limit after
prepare; the protocol correctly refused it. The corrected helper-cap/stale/pending
checks passed4/4 before the final full focused run. No failed check is counted as
passed. Astra accepted the final source, fix, complete test log and preservation.

## Preservation and remaining work

All57 inventoried old package/script Python/C++/PowerShell files are byte-identical.
The41-member packaged fingerprint remains
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
Task1 added one CI test path. Local logs and before/after inventories
remain under `.tools/drive-input-comparison-implementation-20261109/`.

| File | SHA256 |
| --- | --- |
| Runner,36429 bytes | `ed7ca12a34193b1a4a01ca4dd305c396ad387708aa3b051f79209051b4d143d4` |
| New tests,22332 bytes | `6df9c4ad874da06a0fe7b17ce6b1d9ec20cacd0fb2271a28de1258ac9383ed2b` |

## Thin supervision binding

Task2 adds `drive_input_supervision.py` and `supervise-drive-input.ps1`, reusing
the unchanged Windows owned-job monitor. The adapter is exactly the accepted
continuous adapter after explicit version/path/diagnostic substitutions (normalized
newlines); the frontend is byte-exact after its sole helper filename replacement.
Readiness binds the new sources and the unchanged legacy runtime snapshot. The
fixed limits remain900s,4GiB actual-worker peak working set,256MiB combined new
output/evidence/scratch and at-most2s polling. These are monitored stop thresholds,
not hard quotas or aggregate process-tree RSS. No monitor globals are patched.

Final focused host verification: **139 passed,1 skipped,3 deliberately deselected
in39.10s**. All69 new cases are included (68 passes plus one actual Windows
symlink-privilege skip, WinError1314), alongside71 unchanged monitor/adapter cases.
The three exclusions are old private runtime/cache preparation and Zig-version
checks, reserved for concrete controller preflight. CI adds the new test path.

```powershell
.venv/Scripts/python.exe -m pytest -q -rs -p no:cacheprovider --basetemp=.tools/drive-input-supervisor-implementation-20261109/final-focused tests/test_drive_input_supervisor.py tests/test_continuous_motor_supervisor.py tests/test_market_response_supervisor.py -k 'not actual_runtime_binds and not actual_preparation_binds and not actual_pinned_zig'
```

Use a fresh basetemp for a justified rerun. Initial missing-adapter RED preceded
implementation; sandbox execution then failed24 cases at the unchanged hardlink
writer (three passed,seven deselected). Regular approved host execution passed34
cases, followed by68 passes/one privilege skip after expanded binding tests.
No source checks or writer semantics were weakened to bypass that restriction.

Tests cover actual copied source mutations, explicitly synthetic runtime/cache
identity mutations, every limit's type/value/presence, malformed/oversized JSON,
fresh/confined/disjoint paths, readiness/release/PID mismatches, scratch routing,
post-release rechecks and rejection before native-engine construction. Harmless
Windows harnesses use the new public frontend and supervisor with labelled
synthetic configuration. Completion consumes an actual injected-runner receipt;
it is not a fabricated native result. Independent review of the actual receipts
confirmed distinct launcher/worker identities, cancellation and owner-death cleanup,
zero remaining owned processes and survival of an unrelated test-owned process.

Astra accepted final source/tests, real harmless-process evidence and preservation.
All58 preexisting source/frontend files, including Task1, remain byte-identical;
the41-member package fingerprint is unchanged. Evidence remains under
`.tools/drive-input-supervisor-implementation-20261109/`.

| File | SHA256 |
| --- | --- |
| Adapter,9470 bytes | `06aa2ad4aed00c91027a03147229f6c507cb5e5fb21af0f1a01b13156bf210f8` |
| Frontend,8470 bytes | `a50e1b09135d4a74b8b0f343a162d4ad6a7c005191245897ee869d3dc234512b` |
| New tests,26003 bytes | `9b77d9888a56ef3d53719474e1f5d70420c007721a86e24b4e38cc82cf841024` |

All source-bearing tasks are complete. Next confirm source-CI and independently
review concrete preparation before one bounded acquisition. Software tests do
not establish actual run resource compliance, real input sensitivity, neural
target coverage, biological learning, selling-price activation or Stage C acceptance.
