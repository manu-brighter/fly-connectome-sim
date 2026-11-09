# Offline market evidence inventory — 2026-11-09

## Result

The new bounded analyzer successfully inspected the existing accepted raw run at
`runs/cell-demo-20261108-02/session/run`. It verified and summarized **214
observations, 1,040 native bins and 9,000 ms**: seven seconds of video and two
seconds of option cards. No new fullgraph observation, training or API call ran.

This is an integrity-checked historical population inventory, **not a successful
twenty-drink feasibility gate**, native replay attestation or live benchmark.
The [separate historical cell screen](2026-11-09-market-kc-screen.md) found strong
dominance in an initial twenty-group KC grouping; those cell-level results are
not reconstructed from this population report.

## Actual population measurements

Mean rates use total spikes divided by group size and the complete nine-second
duration. Original native-bin rates use their actual, sometimes short duration;
their maxima must not be confused with sustained firing rates.

| Group | Cells | Spikes | Mean spikes/s/cell | Nonzero bins /1,040 |
| --- | ---: | ---: | ---: | ---: |
| KC | 4,064 | 64,338 | 1.759022 | 836 |
| MBON07 | 4 | 33 | 0.916667 | 27 |
| MBON11 | 2 | 256 | 14.222222 | 197 |
| Motor left | 1 | 152 | 16.888889 | 131 |
| Motor right | 1 | 55 | 6.111111 | 47 |
| PAM11 | 15 | 1 | 0.007407 | 1 |
| PPL101 | 2 | 1,124 | 62.444444 | 630 |

Declared membership sets do not overlap. This does not establish functional
independence. Different group sizes, sparseness and activity levels also mean
these seven rates cannot simply be used as interchangeable drink scores.

Recorded telemetry sums are 71.91710060005425 seconds of compute and
69.91145439996762 seconds of kernel time: respectively 7.990789 and 7.767939
recorded seconds per simulated second. These historical fields are covered by
the event-file hash but are not independent resource monitoring. The earlier
109.223-second supervised total remains a separate end-to-end measurement.
Neither timing establishes future steady-state throughput or twelve-hour uptime.

## Implementation and reviewed corrections

`scripts/analyze-market-feasibility.py` provides an explicit local CLI and two
small interfaces, `analyze_recorded_run` and `write_report`. It reuses the current
recorder verifier and consumes the complete event stream through EOF.

Before verification, an owned private snapshot caps manifest reads at 2 MiB,
event bytes at 64 MiB and each of at most two checkpoints at 64 MiB. Total maximum
payload is 194 MiB. The snapshot rejects unsafe/link paths and source identity
substitution; the verifier retains the 1-MiB event-line and 246-event limits.
Report hashes bind those exact inspected snapshot bytes, not the subsequent
state of a mutable caller directory. No native checkpoint state is instantiated.

Additional checks cover observation/bin clocks and coverage, population/count
arithmetic, `learning=False`, absent external stimulation, finite timing and
uninterrupted single-branch observations. Unsupported histories fail closed.

Independent source review identified three defects, reproduced with failing tests
before correction:

- Emitted redundant `start_ms`/`end_ms` could contradict authoritative ticks.
  Present fields are now checked against those ticks.
- Identical cell memberships could claim contradictory counts. Per-bin subset
  monotonicity now also enforces equality for identical sets in either ordering.
- Failed output cleanup could delete another process's replacement. A fully
  written, flushed and fsynced private temporary file is now published exclusively
  by hardlink; cleanup never deletes the final output path.

The scoped fix review accepted all three corrections. Output filesystems without
hardlink support fail closed. Exclusive publication is not a claim that the
parent directory entry has been directory-fsynced for power-loss durability.

## Commands and actual validation

Final local command, run on the host because sandbox temporary-directory ACLs
prevented required filesystem operations:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_market_feasibility.py tests/experiment/test_recorder_limits.py -q --basetemp=.tools/market-stage-a-20261109/review-regression-tmp -o cache_dir=.tools/market-stage-a-20261109/cache
```

**148 passed, 5 skipped in 5.98 seconds**, no warnings: 81 analyzer cases and
67 recorder cases. Five symbolic-link cases explicitly skip for Windows
`WinError 1314`, rather than counting as passed. The existing recorder suite's
three tiny-native fixtures are bounded compatibility tests, separate from the
analyzer's no-native behavior and this historical acceptance.

The initial RED run had the expected missing-script failures. Sandbox temp/cache
permission errors and two subsequently corrected fixture mistakes are retained
in the implementation report. The three review fixes had six reproduced RED
failures before GREEN. Additional regression cases check per-bin consistency,
partial output failure and a competing final file at publication.

Actual historical acceptance command:

```powershell
.venv/Scripts/python.exe scripts/analyze-market-feasibility.py --run-dir runs/cell-demo-20261108-02/session/run --output runs/market-feasibility-20261109.json
```

Exit code 0; 35,216-byte JSON report, SHA256
`447b3b1ad68b98cae9cee34e87bf8eb9b404aa1489762e9b57443949911e4c72`.
It explicitly declares `integrity-only`, historical scope and all scientific/
product limitations. It has no overall market/scientific success flag.

All 15 original accepted artifacts and 41 packaged Python/C++ members matched
their pre-task snapshots after acceptance. Package fingerprint remains
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
No viewer source, package source, provenance lock or dependency changed.

Local logs and baseline are under `.tools/market-stage-a-20261109/`; detailed
implementation/review notes are plan-scoped ignored scratch. Actual result,
scope and limitations are retained here so continuation does not depend on that
scratch. Independent historical-evidence review accepted every population/rate,
time total, manifest/event binding, report hash, unchanged input/source set and
the separate KC-screen claims. Clean-checkout CI remains pending at this
checkpoint; it is not implied by local test success.

## Next diagnostic boundary

The first prospective question is whether fixed inputs produce reproducible
differences across the chosen readouts from a common complete state. It is not
yet selection among twenty drinks, full price-range control or a long event run.
The historical cohort's late recruitment requires predeclared observation
coverage; a short null window cannot establish incapacity. A separate finite
protocol, runner and process supervision must be reviewed before acquisition.
