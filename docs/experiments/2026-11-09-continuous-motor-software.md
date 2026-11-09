# Continuous motor probe — software evidence

Status: Task1 runner/auditor implemented, synthetically tested and independently
accepted. Task2 supervision is not implemented. No native acquisition
has run under the [prospective protocol](../superpowers/specs/2026-11-09-continuous-motor-probe.md).
The [sequential plan](../superpowers/plans/2026-11-09-continuous-motor-probe.md)
keeps source, supervision and actual-result acceptance separate.

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
