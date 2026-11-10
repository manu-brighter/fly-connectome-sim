# Local image admission — implementation evidence

Status: independently accepted and published; all four clean-checkout CI jobs passed
for source `6d72ed70353cb0ef3404303be6f071078f77da23`. The earlier prospective
[contract review](../superpowers/specs/2026-11-10-image-admission-design.md) does
not establish implementation acceptance.

The new `market/image_admission.py` implements the metadata lifecycle before
image decoding or upload integration. One receiving-or-pending slot and one active
slot share a finite 512-slot receipt budget. Acceptance starts the immutable
300-second handoff deadline; decoding, approval and retries cannot renew it.
Terminal receipts remain for 900 seconds without pressure eviction.

An unconfirmed or contradictory worker outcome stops unfinished work while
preserving previously confirmed start data. A timely start may be reported after
the image deadline within the separate ten-second receipt budget. Metadata checks
do not establish that pixels were decoded or native observations occurred.

## Actual local verification

All commands used `.venv/Scripts/python.exe -m pytest`, fresh task-local
`--basetemp` directories and `-p no:cacheprovider`.

| Check | Observed result |
| --- | --- |
| Initial focused tests before module creation | Exit2, missing-module collection error |
| Retained dispatch-ID collision regression before correction | 115 passed, one failed |
| Initial `tests/market/test_image_admission.py` | 116 passed, zero skips, 0.35s |
| Initial complete Market suite under Windows host execution | 297 passed, one skip, 30.02s |
| Detached-data regression before correction | 18 failed, 116 deselected |
| Corrected focused suite | 134 passed, zero skips, 0.46s |
| Corrected complete Market suite under Windows host execution | 315 passed, one skip, 33.52s |

The skipped existing HTTP asset test requires Windows symlink privilege
(WinError1314). The corresponding Linux case passed in the clean-checkout run below. The first full suite inside
the restricted Windows sandbox produced244 passes, five failures,48 setup errors
and one skip due to existing asset-path/startup access restrictions. The host run
used the same suite and unchanged assertions. Initial fixture corrections and all
failed attempts remain in the private local evidence record.

Independent review found a shared-reference defect: changing a returned dataclass's
dictionary could alter its stored deadline, and changing a submitted worker receipt
could rewrite the retained retry evidence. The correction copies data at input and
output boundaries, including nested snapshots; frozen setters alone were insufficient.
Eighteen regressions demonstrated the defect before correction. Independent
re-review accepted the fix and full D1 slice after seven additional metadata
reproductions passed. Source acceptance is separate from the subsequent Linux CI result below.

Behavioral tests cover slot/capacity concurrency, exact deadline boundaries,
original acceptance times, terminal retention, valid and contradictory retries,
worker identity/index/timing consistency, clock failure diagnostics, stopped
states, detached snapshots and process-local restart scope. Completion checks eight
declared consecutive indices; actual native telemetry validation is later work.

Before review, all300 preexisting tracked files,64 frozen helpers,41 package
members and seven historical artifacts matched the preimplementation baseline.
The Windows package fingerprint remains
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
Private logs and source hashes are under `.tools/image-admission-20261110/`;
they are local evidence, not required cloud-checkout inputs.

No dependency, packaged simulator, old readout, price-service source or replay
format changed. D1 runs no HTTP, decoder, native model or provider request. The
existing Market regression suite separately uses disposable HTTP processes and
synthetic temporary price databases. Public uploads, real image handoff, neural
price admission, event capacity and operating approval are not established.

## Published-source CI

[CI42803437054](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42803437054) completed successfully
for exact source `6d72ed70353cb0ef3404303be6f071078f77da23`:

| Job | Actual result |
| --- | --- |
| Market, including D1 | 316 passed, no skips, 23.00s |
| Existing native/session | 1469 passed, 47 declared skips, 504.55s |
| Existing buffers | 253 passed, six Windows-only skips, 245.28s |
| Viewer | 266 passed, four private-artifact skips, 71.85s; build282ms |

The Windows-only skip is resolved by Linux coverage, not by removing an assertion.
This closes D1 metadata lifecycle evidence only. The independently specified D2
decoder is next; no pixel conversion, uploads or native integration is implied.
