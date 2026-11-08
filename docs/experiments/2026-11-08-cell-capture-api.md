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

This command has **not** yet been run on the full graph for this checkpoint.
The declared production acquisition also requires external wall/RSS/output
supervision before execution. The script enforces its cell/bin/detail-byte bounds;
it does not implement an OS memory quota.

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
  hardlink/junction cases passed. Linux CI can exercise the symlink cases.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/experiment/test_cell_activity.py tests/experiment/test_event_proposals.py tests/test_engine_contract.py tests/experiment/test_session_workflow.py tests/experiment/test_feed_event_session.py tests/test_cli.py -q -p no:cacheprovider --basetemp .tools/neural-detail-20261107/root-backend-host
```
- Independent backend and transport source reviews completed. No fullgraph
  observation or film acceptance is implied by these synthetic test fixtures.

Current working-tree model fingerprint (40 packaged source members):
`dc83d0796fd51c46323ee0e96a7bcfc725d34c6d94371971d235d90ed4144db5`.
This source-bearing change supersedes earlier model identities; it is not a
formal qualification/freeze claim. Exact acquisition source bytes will be recorded
after the remaining implementation/review steps.

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

The successful proposal is fixed for the upcoming single cell-detail session.
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
