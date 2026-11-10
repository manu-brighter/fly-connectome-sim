# Bounded native worker — software evidence, 2026-11-10

The [prospective contract](../superpowers/specs/2026-11-10-native-worker-design.md)
and [sequential plan](../superpowers/plans/2026-11-10-native-worker.md) define one
bounded local image-to-engine proof. Task1's protocol/evidence library is implemented
and independently accepted after two integrity corrections. No worker process, actual image exposure,
native price proposal or new acquisition is established by these software tests.

## Published prerequisite

Contract checkpoint `c1d6c034be16e7114ec6936603511eb9a3314a04` passed all four
[CI42844507066 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42844507066):
693 Market passes/25 Windows-specific skips,1469 native/session passes/47 skips,
253 buffer passes/six skips and287 viewer passes/four absent-artifact skips, plus
build. This CI covers the contract and preceding implementation, not the new
Task1 source described below.

## Task1 scope and verification

The new stdlib-only `market/native_protocol.py` provides bounded exact IPC
codecs, immutable records, header/observation arithmetic, finite protocol and
receipt-evidence validation, event/monitor journals and a full-EOF inspector.
It imports no simulator, constructs no engine, launches no process and calls no
provider. D1 state transitions, transport, session ownership and HTTP remain later
tasks; this module validates supplied evidence rather than operating that lifecycle.

The final affected test command was:

```powershell
.venv/Scripts/python.exe -m pytest tests/market/test_native_protocol.py tests/market/test_native_evidence.py tests/market/test_image_admission.py tests/test_market_live_buffers.py -p no:cacheprovider --basetemp=.tools/native-worker-20261110/fix1-green-temp
```

Actual Windows result: **410 passed, zero failures/skips,38.32s**:152 new cases
and258 existing D1/CellRing regressions. The complete repository suite was not run
for this bounded assignment. Intermediate missing-implementation failures and
later semantic failures were retained before their fixes. In particular, final
wire canonicalization was shown failing before the initial407-case passing run.
An earlier406-case run passed before that added regression. Independent review
then reproduced two further gaps using correctly rehashed analytical artifacts:
an image permit could extend the original D1 deadline by100s, and a terminal-only
monitor journal could omit all startup/run coverage. Three targeted cases failed
before the fix; the410-case run above passed afterward. The independent reviewer
also confirmed the original mutation artifacts now fail at the new checks.

Fixtures cover an integrity-complete40-observation black run and a complete
eight-observation image path ending at index39. The image path requires dispatch,
start, matching D1 receipts, original observations, completion and the one terminal
ACK in causal order. Missing, duplicate, reordered, partial and late evidence is
rejected. These are analytical software fixtures, not decoded audience images or
native measurements. A complete zero-image fixture remains integration-negative.

Header arithmetic checks all seven population profiles, inclusions, pairwise
disjoint subset lower bounds, unique selected-cell counts and mandatory/cohort
coupling. Final evidence checks compare journal/monitor summaries, hashes,
bound process declarations, confirmed cleanup fields and the exact source-check
commitment. They do not prove that an operating system executed those actions.

## Explicit verification boundaries

The inspector authenticates small existing `arrays.lock.json` and `sources.lock.json`
files through their declared raw hashes and file identities before comparing
header/engine declarations. It does not derive array hashes from an NPZ file hash,
load graph arrays or repeat annotation joins. Those actual data checks remain
part of the later source-bound startup.

On this Windows host, complete fixtures use real absolute paths and real file
stat/hash checks without mapping. Linux-only fixture code maps logical Windows
paths at the leaf path-resolution boundary to actual temporary files; the schema,
path rules, stat/hash/EOF checks remain active. That adapter has not yet run in
clean-checkout CI and is not evidence of Windows process or filesystem ownership.
The64-source fixture declarations are synthetic and do not attest current
checkout bytes.

`SourceCheck` binds the declared final comparison. The later session owner must
actually perform it and cleanup before publishing a success seal. Static inspection
is integrity-only, not native replay attestation, historical fsync proof,
continuous source attestation or scientific qualification.

Monitor coverage now begins no later than the first recorded worker hello, with
the held worker alone in its Job, and continues with gaps below2s through the
terminal empty-Job sample. No OS-resume timestamp exists in this format; this is
the available startup evidence anchor, not physical process-release attestation.
The later process/session owner must actually begin monitoring before/at resume.

The controller independently compared all64 frozen helper bytes, the exact41-member
packaged source set and seven historical artifacts with the preceding baseline;
all are unchanged. No D1/D2, price authority, historical evidence or packaged
simulator source is changed by Task1.

## Remaining work

Owned Windows transport with harmless-process tests; worker/session integration;
coordinator/HTTP/measured-status connection;
explicit CLI and exact source CI. Only then does the separately reviewed concrete
preflight precede one finite actual acquisition. Native price ingress, richer
measured live presentation and sustained event rehearsal remain subsequent work.
