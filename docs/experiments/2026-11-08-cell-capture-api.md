# Cell capture and live proposal checkpoint — 2026-11-08

This is an implementation/API checkpoint. The new viewer, one fullgraph
cell-detail session and its exported film still require acceptance. Existing
static-anatomy recordings remain historical and unchanged. The research assay
is parked; no new learning or scientific-support result is claimed.

## Passive capture

The existing native kernel already returns per-cell integer counts for each
Python observation bin. An optional fixed observer now copies a bounded cohort
at that boundary without changing native calls, sensory frames, dynamics or
ordinary telemetry. A real tiny-native checkpoint comparison proves equal full
state hashes, counters, clocks and scientific telemetry with capture off/on;
wall-clock performance fields are excluded. The observer receives detached
values, and a failure stops acquisition rather than silently losing detail.

The [contract](../superpowers/specs/2026-11-07-cell-activity-replay.md) fixes at
most256 cells and512 existing directed edges before advancement. All small
DAN/MBON/DNa02 groups are included; remaining KC slots use source-ID stride.
Locked graph arrays and annotations bind actual nullable soma coordinates.
Connections are static model topology, not observed transmission or axons.

The new entry point composes the existing ordinary session workflow (new output
directory required):

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/run-cell-activity-session.py --runtime-directory data/malecns-v1.0/runtime --playlist .tools/reels-source/playlist.json --proposal runs/proposal-live-20261108-02/proposal.json --output runs/NEW-cell-session
```

The first supervised launch on November8 was aborted after0.353s. The monitor
incorrectly counted older validation artifacts in its shared evidence directory:
1,814,974,188 observed bytes exceeded256MiB. The output contains only an empty
`session/` directory; no measurement files or complete native observation exist.
Both owned processes ended, with no cleanup errors. Preserve this failed attempt.
The correction requires a fresh isolated acquisition evidence directory, unchanged
limits and non-neural tests/review before any explicitly authorized retry. The
script itself enforces cell/bin/detail-byte bounds, not an OS memory quota.

Outputs are incremental `cell-activity.jsonl`, the normal bundle under `session/`,
and `cell-activity.json` only after source/ordinary-run/bin validation. The exporter
requires the canonical recording member and its exact inspected bytes. Review
found and corrected acceptance of an alternate file and replacement after
inspection; both cases were demonstrated with failing regression tests first.
Partial files alone do not establish completion.

The sidecar retains original counts in their original bins. The viewer contract
sums only whole bins into completed100ms windows, retaining zeros and missing
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
  new cell viewer implementation.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/experiment/test_cell_activity.py tests/experiment/test_event_proposals.py tests/test_engine_contract.py tests/experiment/test_session_workflow.py tests/experiment/test_feed_event_session.py tests/test_cli.py -q -p no:cacheprovider --basetemp .tools/neural-detail-20261107/root-backend-host
```
- Independent backend and transport source reviews completed. No fullgraph
  observation or film acceptance is implied by these synthetic test fixtures.

Current working-tree model fingerprint (40 packaged source members):
`dc83d0796fd51c46323ee0e96a7bcfc725d34c6d94371971d235d90ed4144db5`.
This source-bearing change supersedes earlier model identities; it is not a
formal qualification/freeze claim. Exact source/test/protocol bytes were captured
before the aborted launch and checked again for the proposed retry below.

## Viewer and corrected acquisition supervision

The optional cell loader, source-coordinate projection, static directed edges,
exact integer count table and seven population traces are implemented. The
canvas uses only completed100ms windows and preserves zero/missing states.
At900px the entire card phase reserves a separate310px plan region beside the
fly/tablet; narrow views stack the plan and scene without removing programme
entries. The original tablet/foreleg geometry remains unchanged.

The final full viewer suite passed135 tests with zero skips in26.682s; the build
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
Production limits remain900s wall,4GiB native peak RSS,256MiB acquisition output
and2s polling; the native child/owner cleanup rules are unchanged.

Two non-neural host smoke cases passed with the older1.74GB test directory still
present: normal completion in4.243s with13,676 scoped bytes, and explicit output
overflow/cleanup in0.380s with132,445 bytes. Only a separate test copy used the
128KiB/100ms overflow threshold; production has no limit-override flags.
Both owned test processes ended and original attempt/freeze/receipt hashes stayed
unchanged. Astra independently checked the source, actual receipts and all119
retry freeze bindings. The original117 source/test/protocol bindings and native
model fingerprint remain unchanged. The new freeze SHA256 is
`66eedef72142b7e9117f2555170972313fe5816eaca38523c2fb8ccf36560bfa`.

The concrete retry targets `runs/cell-demo-20261108-02/` and isolated local
evidence remain uncreated. User authorization was requested because the accepted
protocol prohibits automatic retries. Native data audit and new film acceptance
remain open; no additional provider call is needed.

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

The successful proposal is fixed for the pending cell-detail session.
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
