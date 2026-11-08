# Accepted cell-count replay and live proposal — 2026-11-08

The agreed experimental observation scope is complete: a genuine API proposal,
continuous fullgraph session, measured selection, unchanged plan, recorded cell
view and actual film passed independent review. The accepted local bundle is
`runs/cell-demo-20261108-02/`. Existing static-anatomy recordings remain separate
historical evidence. Research and broader platform/model/account coverage remain
parked; no learning, semantic preference or scientific qualification is claimed.

## Accepted observation and film

The explicitly authorized second launch recorded 7 s feed + 2 s event cards with
one fresh engine, no reset/restore, external stimulation or learning. It produced
214 observations, 1,040 original native bins and 90 complete 100 ms windows.
All 256 selected cells have actual soma positions: KC 231/4,064 plus every
mandatory PAM11/PPL101/MBON07/MBON11/DNa02 cell. The fixed topology displays
512 of 4,254 eligible directed model edges. Independent source/bin checks found
5,388 cohort counts, 98 cells with any count and a maximum 14 counts per cell
per 100 ms window. These are binned simulated counts, not exact spike times or
measured synaptic transmission.

The final 500 ms counts were L7/R2 (one cell per motor group), Δ −10 Hz/cell:
the unchanged engineered lateral policy selected **Sunset Rooftop Social**.
Its brief, option and all four programme entries exactly retain the successful
API proposal. The actual downloaded plan is semantically identical to the saved
canonical plan. This does not establish event understanding or feasibility.

Supervision recorded 109.223 s, native OS peak RSS 948,957,184 bytes and peak
acquisition output 47,844,542 bytes; both exit codes were zero, with no cleanup
errors or termination reason. Raw detail plus sidecar is 1,354,132 bytes. The
post-film output/evidence scope is approximately 54.15 MB (54,147,182 bytes at
the artifact audit). All declared thresholds were respected; wall/RSS/output
are polled measurements, not OS hard quotas.

The actual film is 360 VP9 frames, 900×900, 30 fps, 12 s, without audio:
9 s measurement plus a labelled 3 s frozen-measurement hold and illustrative tap.
Decoded frame checks cover the first completed window, feed/card boundary,
pending/decision boundary and reach/contact/return/terminal hold. No premature
plan appears. Chrome 157 on Windows 11 finished playback with no media error or
dropped frames. All 256 displayed counts matched at 11 boundary/reverse-seek
samples; the actual narrow canvas was 341×1600. Synthetic both-side/defer checks
remain presentation tests, separate from this real left-selection observation.

Independent review checked all 119 freeze bindings, exact artifact hashes,
cohort IDs/positions, native-bin/window/group reconciliation, plan and decoded
film evidence. The controller's separate CSR source audit checked the edge
subset; the final reviewer inspected that audit rather than rereading the large
post array. Integrity-only inspection is not native replay attestation.

| Artifact relative to `runs/cell-demo-20261108-02/` | Bytes | SHA256 |
| --- | ---: | --- |
| `session/recording.json` | 13,139,108 | `c1972dc889fcfbe9e603b0d2790092998d46a9ec0780c52f2eb8d8fc3af379bd` |
| `session/plan.json` | 1,190 | `fdebbe5c86d417cb61c4ac39b7cffa47aa51a699d6d04de9ab7c3a66e47f9a89` |
| `session/receipt.json` | 702 | `e42e36754bb6e4fed775a92fed749b114d0549fa76743579fabdcb34bd3c428d` |
| `cell-activity.jsonl` | 700,081 | `24e61b5c2a066c7da18cd4c191ae64029f1186614883730784e4c81194aef9c2` |
| `cell-activity.json` | 654,051 | `7ab327bf915b2d456874cf38d209fbccb9c0b4cf164f546132982fca672253e3` |
| `anatomy.json` | 417,084 | `655d190f9b5f4d9f6bee1568bed29236ca930a4c84a1c1bc682261626e877f9f` |
| `demo-30fps.webm` | 3,022,788 | `486c86311bccc4f1b999e129c642294323e39cf069be941d492382c0fed931b6` |

Reopen existing files without a simulation or API call:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli inspect-session runs/cell-demo-20261108-02/session
npm --prefix viewer run dev
```

Open the printed localhost URL: **Open recording** → `session/recording.json`,
**Open cell counts** → `cell-activity.json`, optional **Open anatomy** →
`anatomy.json`, all within the accepted bundle. Play/seek or inspect exact counts;
the existing film can be played directly. **Export video** reproduces presentation
from these files without advancing neural time. No server is deliberately left
running. Raw data, artifacts and local audits remain ignored, outside Git.

## Passive capture

The existing native kernel already returns per-cell integer counts for each
Python observation bin. An optional fixed observer now copies a bounded cohort
at that boundary without changing native calls, sensory frames, dynamics or
ordinary telemetry. A real tiny-native checkpoint comparison proves equal full
state hashes, counters, clocks and scientific telemetry with capture off/on;
wall-clock performance fields are excluded. The observer receives detached
values, and a failure stops acquisition rather than silently losing detail.

The [contract](../superpowers/specs/2026-11-07-cell-activity-replay.md) fixes at
most 256 cells and 512 existing directed edges before advancement. All small
DAN/MBON/DNa02 groups are included; remaining KC slots use source-ID stride.
Locked graph arrays and annotations bind actual nullable soma coordinates.
Connections are static model topology, not observed transmission or axons.

The new entry point composes the existing ordinary session workflow (new output
directory required, only for a separately justified new observation):

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/run-cell-activity-session.py --runtime-directory data/malecns-v1.0/runtime --playlist .tools/reels-source/playlist.json --proposal runs/proposal-live-20261108-02/proposal.json --output runs/NEW-cell-session
```

The first supervised launch on November 8 was aborted after 0.353 s. The monitor
incorrectly counted older validation artifacts in its shared evidence directory:
1,814,974,188 observed bytes exceeded 256 MiB. That original output at
`runs/cell-demo-20261108/` contains only an empty `session/` directory; no
measurement files or complete observation were produced by that attempt.
Both owned processes ended, with no cleanup errors. Preserve this failed attempt.
The correction requires a fresh isolated acquisition evidence directory, unchanged
limits and non-neural tests/review before the explicitly authorized second launch. The
script itself enforces cell/bin/detail-byte bounds, not an OS memory quota.

Outputs are incremental `cell-activity.jsonl`, the normal bundle under `session/`,
and `cell-activity.json` only after source/ordinary-run/bin validation. The exporter
requires the canonical recording member and its exact inspected bytes. Review
found and corrected acceptance of an alternate file and replacement after
inspection; both cases were demonstrated with failing regression tests first.
Partial files alone do not establish completion.

The sidecar retains original counts in their original bins. The viewer contract
sums only whole bins into completed 100 ms windows, retaining zeros and missing
positions. It cannot recover exact intra-bin spike times. Integrity hashes,
source checks and population reconciliation are not native replay attestation.

## Actual verification

- Initial missing-feature RED:10 failures/11 errors. A further RED exposed the
  incorrectly accepted51st bin in an observation; the maximum is now50.
- Native equivalence includes33.3/33.4/33.3/500ms observations, explicit black
  input and attempted callback-payload mutation. A real tiny session records680
  bins over6s with positive and zero counts, using one acquisition engine.
- Backend focused tests after binding fixes:31 passed,2 Windows symlink-creation
  skips. The broader regression before those fixes was170 passed/4 permission
  skips; those four hardlink/junction cases subsequently passed on the host.
- Final combined host regression:285 passed,2 skipped in129.20s, exit0. Both
  skips require Windows symlink-creation privileges that this host lacks;
  hardlink/junction cases passed.
- [Linux CI for f5766f5](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42428235786)
  completed successfully:185 selected native/backend tests passed,1 Windows-only
  junction skip. Both new symlink tests ran successfully. The unchanged viewer
  passed114 tests with no skips and its build exited0. This does not cover the
  new cell viewer implementation; the later CI below covers that source.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/experiment/test_cell_activity.py tests/experiment/test_event_proposals.py tests/test_engine_contract.py tests/experiment/test_session_workflow.py tests/experiment/test_feed_event_session.py tests/test_cli.py -q -p no:cacheprovider --basetemp .tools/neural-detail-20261107/root-backend-host
```
- Independent backend and transport source reviews completed. No fullgraph
  observation or film acceptance is implied by these synthetic test fixtures.

Current working-tree model fingerprint (40 packaged source members):
`dc83d0796fd51c46323ee0e96a7bcfc725d34c6d94371971d235d90ed4144db5`.
This source-bearing change supersedes earlier model identities; it is not a
formal qualification/freeze claim. Exact source/test/protocol bytes were captured
before the aborted launch and checked again for the authorized second launch.
Accepted engine identity:
`13eb5c81d3898597224405ae06a62e03359d28588d0b81f5c1a51ead528ae1e7`.

## Viewer and corrected acquisition supervision

The optional cell loader, source-coordinate projection, static directed edges,
exact integer count table and seven population traces are implemented. The
cell-count layer sums only whole native bins into completed 100 ms windows and
preserves zero/missing states; population traces retain their native bin times.
At 900 px the entire card phase reserves a separate 310 px plan region beside the
fly/tablet; narrow views stack the plan and scene without removing programme
entries. The original tablet/foreleg geometry remains unchanged.

The final full viewer suite passed 135 tests with zero skips in 26.682 s; the build
passed with its existing large-chunk advisory. Independent source review and
synthetic browser previews passed after correcting the intermediate-width
breakpoint, plan/tablet overlap and first-paint clear color. The clear-color
regression observed black before the fix, then passed against actual stage
initialization. An actual Chrome invalid-sidecar check retained working replay.
Synthetic previews, including source-derived coordinates with deliberately fake
counts, are layout evidence only and are not accepted native measurements.

After the aborted launch described above, supervisor v2 separates fresh output
and evidence directories from all historical validation fixtures. Both must be
new, non-nested paths inside the workspace with no reparse-point parents.
Production limits remain 900 s wall, 4 GiB native peak RSS, 256 MiB acquisition
output and 2 s polling; the native child/owner cleanup rules are unchanged.

Two non-neural host smoke cases passed with the older1.74GB test directory still
present: normal completion in4.243s with13,676 scoped bytes, and explicit output
overflow/cleanup in0.380s with132,445 bytes. Only a separate test copy used the
128KiB/100ms overflow threshold; production has no limit-override flags.
Both owned test processes ended and original attempt/freeze/receipt hashes stayed
unchanged. Astra independently checked the source, actual receipts and all119
retry freeze bindings. The original117 source/test/protocol bindings and native
model fingerprint remain unchanged. The new freeze SHA256 is
`66eedef72142b7e9117f2555170972313fe5816eaca38523c2fb8ccf36560bfa`.

After explicit user authorization, the second launch used
`runs/cell-demo-20261108-02/` and isolated
`.tools/cell-acquisition-20261108-02/`. Its accepted native data/film results are
reported above. The first failure is retained; no automatic retry occurred and
no further observation or provider call is needed.

[CI for the reviewed source](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42431095712)
at `776465dce2ece99ffdec74a43d6f6116157ecc60` succeeded: 185 selected
native/backend tests passed with one Windows-only skip; 135 viewer tests passed
with zero skips and the build succeeded. Linux ran the symlink cases skipped on
Windows. This data-free CI is compatibility evidence, not fullgraph qualification.

## Live proposal transport

The offline request used the existing Summer team party /100 guests /CHF5000
brief, pinned `gpt-5.4-mini-2026-03-17` and2048 output tokens. Its SHA256 is
`945b86de95401e1349c418e45507d3015ea3cb85e3a064cb69c020e25b8dac51`.

The first explicitly authorized live attempt failed with a generic sanitized
transport error. Only its request file remains; the actual error/status/usage
were not retained and are unknown. After API credit setup, the user explicitly
authorized a second attempt. It passed existing strict proposal/brief validation;
request bytes exactly match the dry run. No automatic retry or repair call ran.

- Local bundle: `runs/proposal-live-20261108-02/`.
- Requested/returned model: `gpt-5.4-mini-2026-03-17`.
- Reported usage:357 input +241 output =598 tokens, within the2048 output cap.
- Proposal SHA256:
  `da144f530f962b07431200684b7b3d0e74c0d5b42d5f066431fc9b989741e397`.
- Concepts: Sunset Rooftop Social / Indoor Summer Bash. These are illustrative
  estimates, not checked venues or prices. Neither the model nor its receipt
  selects the eventual option.
- Nominal token cost: USD0.00135225 using the checked
  [USD0.75/M input and USD4.50/M output tariff](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
  Actual billing deductions were not inspected; credits may cover usage.

The successful proposal was used unchanged in the accepted cell-detail session.
No additional provider call is needed for this demo. Keys and raw provider
responses are never saved; receipts are local bookkeeping, not provider
authentication or scientific evidence.

Safe transport diagnostics now classify only allowlisted HTTP statuses and fixed
timeout/TLS/connection/compression categories. They preserve no provider body,
header, status reason or exception text. Strict plain-integer status checks reject
adversarial objects; response/connection cleanup and one-POST behavior remain.
These changes had21 expected RED failures, then136 passing transport/CLI tests
with1 Windows junction permission skip. That junction test passed in the combined
host run above.
