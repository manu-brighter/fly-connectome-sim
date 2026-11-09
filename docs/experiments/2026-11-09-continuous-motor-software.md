# Continuous motor probe — software evidence

Status: Task1 runner/auditor implemented, synthetically tested and independently
accepted. Task2 supervision and its bounded host evidence are independently
accepted as well. One later native acquisition under the
[prospective protocol](../superpowers/specs/2026-11-09-continuous-motor-probe.md)
is now independently accepted as a [valid negative result](2026-11-09-continuous-motor-probe.md).
The [sequential plan](../superpowers/plans/2026-11-09-continuous-motor-probe.md)
keeps source, supervision and actual-result acceptance separate.

Task1 is published as `c0c0887cd8299c18106fe4aaddee86d84a0286af`.
[CI42676056860](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42676056860)
passed637 backend tests /34 declared skips in263.48s,243 viewer tests /four
private-artifact skips and build. All57 new probe cases passed on Linux, including
the Windows-skipped symlink case.

Final Task2 source checkpoint `1d32e1c89e9d94659e43a24b8cbbee08e1cf2425` passed
[CI42678625455](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42678625455):
665 backend tests /41 declared skips in264.03s,243 viewer tests /four
private-artifact skips and build. Seven new Windows-only cases skip on Linux;
all35 passed on the actual Windows host. Concrete preflight was independently
accepted before the single acquisition described in its separate report.

## Task1 scope

The new external `scripts/run-continuous-motor-probe.py` prepares the fixed
source/configuration/input protocol, records the exact continuous schedule with
decoder inputs/results, and inspects the complete sealed stream without a neural
run. There are192 observations,9600 original bins and194 events including two
checkpoints. Both the engine and unchanged decoder preserve state across48s.

Inspection derives left/right counts from the original bins, checks all seven
population rates/counts and metadata/clock/checkpoint agreement, then reconstructs
every decoder result. Canonical comparisons distinguish different JSON types;
`False` cannot stand in for0 in declarations. Invalid input does not produce a
successful summary or complete receipt. Event generators close before temporary
snapshots are cleaned up, including semantic-error paths on Windows.

Summary outcomes on valid complete sessions are `negative` or `narrow-positive`.
The validity field means complete integrity/semantic inspection only. Summaries
retain proposals, partial routes, neutral/defer/reset counts, direction signs,
price concentration, clocks/latencies and descriptive order partitions. A path
crossing48s is not split; its proposal belongs to the completion partition.
Neither hashes nor this reconstruction authenticate consistently rewritten,
resealed timestamps or establish native replay attestation.

Prepare/inspect do not depend on the future supervision module. Production resolves
that dependency lazily and requires the guarded start before constructing an
engine. Factory/clock injection belongs to synthetic tests and is absent from the
CLI. An injected clock without a test factory is rejected. The guard-order test
uses a synthetic context/factory; it is not evidence of actual process supervision.

## Actual Task1 tests

The first40 tests failed before implementation. The initial sandbox GREEN attempt
hit the unchanged exclusive writer's hardlink restriction. The same tests ran on
the authorized host; no safety helper was weakened. Windows error-path cleanup
and further resealed contradiction cases exposed defects before their fixes.

| Test stage | Actual result |
| --- | --- |
| Initial RED |40 failed, missing implementation |
| Sandbox attempt |39 failed /1 passed; atomic-publication access denied |
| First host attempt |22 failed /17 passed /1 skip; open-generator cleanup masked semantic errors, and incomplete-manifest fixture exception expectation needed correction |
| Corrected baseline |39 passed /1 skip in66.84s |
| Extra contradiction/timing RED |3 failed /46 deselected |
| First combined GREEN |146 passed /1 skip in79.62s |
| JSON type-equality RED |3 failed /51 deselected |
| Pre-review combined GREEN |151 passed /1 skip in90.43s |
| Independent P2 regression RED |2 failed /1 valid-overlap case passed |
| Targeted P2 GREEN |3 passed |
| Final post-review combined GREEN |**154 passed /1 skip in101.84s** |

Final command:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_continuous_motor_probe.py tests/test_market_motor_readout.py -p no:cacheprovider --basetemp=.tools/continuous-probe-implementation-20261109/review-p2-final-temp
```

This is56 passing new probe cases plus98 unchanged decoder cases. The one skipped
new case requires Windows symlink privilege (`WinError1314`); it remains enabled
on Linux CI. These tests use synthetic engines, populations, clocks and dummy
checkpoints, with no graph acquisition, network/API call or native execution.
`py_compile`, `git diff --check` and the frozen-source Git diff checks passed.
The CI modification adds only the new probe test filename.

Astra's independent source review found one P2: checking only the largest
population count allowed a whole-brain interval total of5 despite distinct left
and right motor counts of5 each. The corrected reader takes the maximum summed
count among pairwise-disjoint subsets of the seven declared populations.
Resealed contradiction tests and a valid overlap fixture establish both rejection
and avoidance of double-counting. Existing bins have no whole-brain-total field;
this check applies only to interval-level `telemetry.total_spikes`.
Astra independently accepted the scoped correction and its consistent overlap
fixture, matched final source/test hashes and verified the RED/GREEN/final logs.
No other source blocker remained. A read-only impact check of the preserved prior
diagnostic found all68 observations satisfy this bound (minimum margin133316);
no old bytes changed and no neural or decoder replay was involved.

Local logs and full source/lock inventory:
`.tools/continuous-probe-implementation-20261109/`.
Independently accepted source identities:

| File | SHA256 |
| --- | --- |
| New runner |`d01095013f16592c402347fbd962a566bf589ba666e5e3c9f27b53ebcd0ef1e8`|
| New tests |`4ba4249c2d4ed86a0a493562492a7e8a41dbe8bccef14478dceb92ff673d2e49`|
| Existing decoder |`e11e9a7adc10b10f08a67b25e41ad1d717174c0e5a106ef9be61416e060734e1`|

Package fingerprint remains
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
No packaged file, provenance lock, accepted decoder or historical helper/diagnostic
was edited. The eventual actual run still requires reviewed supervision, successful
source CI and concrete fresh-path/protocol/readiness preflight.

## Task2 scope and host evidence

The new `scripts/continuous_motor_supervision.py` is a thin adapter to the
unchanged owned-process monitor. Its readiness record separately binds the new
runner, adapter and PowerShell frontend. The old runtime inventory is retained
as `legacy_runtime_configuration`, with its original names and meanings. The
adapter derives the actual new worker command; no arbitrary command, limit or
test-hook CLI option exists. The new frontend differs from the accepted original
only in the helper filename; a byte-comparison test checks this relationship.

Canonical JSON comparisons reject type-confused readiness and release bindings.
A regression first demonstrated that the reused handshake accepts an integer
PID represented as a float; the adapter rechecks the exact binding after that
handshake, before entering the production context. The old helper stays unchanged.
The new scratch-inclusive limit name maps explicitly to the old monitor's key,
whose accounting already includes output, evidence and scratch. Limits remain
900 seconds, 4 GiB actual worker peak RSS and 256 MiB counted files, with normal
0.25-second sampling. These are sampled stop thresholds, not OS quotas or total
process-tree memory limits.

Final host command:

```powershell
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_continuous_motor_supervisor.py tests/test_continuous_motor_probe.py --basetemp=.tools/continuous-supervisor-implementation-20261109/host-final-06
```

Result: **91 passed / 1 skipped in 110.99 seconds**, exit 0. All 35 new
supervision cases passed; the one skip is the existing Windows symlink-privilege
case. Initial complete RED was 27 failures for missing implementation. The first
sandbox GREEN attempt encountered the unchanged atomic writer's access restriction;
the authorized host run passed 27 cases. The added float-PID regression failed
before the fix, followed by 35 passing supervision cases and the combined run.
`py_compile`, `git diff --check` and frozen-source checks also passed.

Harmless Windows workers exercise the exact shipped frontend and public
prepare/run/production-start boundaries with an explicitly synthetic runtime
configuration. Completion consumes the actual synthetic producer's `receipt.json`;
it is not native evidence. Cancellation and owner death clean up worker and
grandchild; an unrelated ready PID is rejected without termination. Repeated
late cancellation leaves the terminal channel at one byte and does not grow
evidence. The real runtime inventory is checked without starting a model; the
separately guarded compiler child is only the pinned `zig.exe version` command.

| Host fixture | Result | Actual worker peak bytes | Counted bytes | Cleanup active processes |
| --- | --- | --- | --- | --- |
| Normal completion | completed | 23,183,360 | 7,305 | 0 |
| Cancellation | failed / cancelled | 23,187,456 | 6,168 | 0 |
| Owner death | failed / owner-exited | 22,847,488 | 6,157 | 0 |

Real console Ctrl+C was not newly injected; preserved frontend bytes supplement
the actual cancellation and owner-death tests. The complete frozen monitor suite
was not rerun. Logs, receipts and source inventory are local under
`.tools/continuous-supervisor-implementation-20261109/`.

| Accepted Task2 file | SHA256 |
| --- | --- |
| Adapter | `b2527b1817baaee0962d4c49007826ff78e51e55ee0122728376739c0a649add` |
| Frontend | `16fcfee8458c693e01ab396d935750ff2bbb74dcc43c6dfc70accbb9cb2465f5` |
| Tests | `5c551df46a2fb27acabd0c6e05e53997fc7c6da6414d93efc90af4feeda09f75` |

Astra independently matched source/package hashes, actual runtime readiness,
the preserved frontend relationship, canonical release checks and scratch
accounting. All three lifecycle receipts match their hashes, handshake identities
and retained byte totals, with zero active processes and terminal signal `2`.
The foreign-process evidence confirms survival without ACK. Task2 source and
bounded host evidence are accepted, with no blocking finding.

No actual acquisition or capacity result follows from these synthetic checks
alone. The subsequent source CI, concrete preflight and actual result are recorded
separately above; the negative result does not invalidate these software checks
or establish a usable price-selection policy.
