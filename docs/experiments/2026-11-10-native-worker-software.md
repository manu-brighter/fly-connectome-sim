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

Published Task1 source`b86a31918675989b50843be31e5250ab0ea8694b` subsequently
passed all four [CI42851467117 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42851467117):
845 Market passes/25 existing Windows-specific skips in136.75s,1469 native/session
passes/47 skips in500.22s,253 buffer passes/six skips in282.88s and287 viewer
passes/four absent-artifact skips in89.167s, plus build. All152 new protocol/evidence
cases passed on Linux, including the explicitly mapped analytical lockfile paths.

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
path rules, stat/hash/EOF checks remain active. That adapter passed the exact-source
clean-checkout CI above; it is not evidence of Windows process or filesystem ownership.
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

## Task2 owned Windows transport

Task2 is implemented and independently accepted after three bounded corrections.
The new transport owns one suspended, hidden worker in a kill-on-close Job from
creation, with restricted pipe inheritance and an actual4GiB Job commit quota.
It provides bounded framed communication, separate finite monitor persistence,
retained handle identity and one exact compiler-version adapter. The adapter was
tested with a harmless Python substitute; no real compiler or simulator ran.
RSS and output limits remain sampled thresholds, not instantaneous physical caps.

An actual host integration run passed **211 cases in55.95s**, covering45 transport,
152 protocol/evidence and14 unchanged D2 ownership cases. Three D2 sandbox failures
passed unchanged with normal host execution; no checks were weakened. After a
targeted root-lock closure correction,46 transport cases passed in17.18s.
Independent review then reproduced three defects: cleanup granted an additional
wait beyond the common budget; an unknown probe exit was marked confirmed; an
explicit caller deadline could exceed the fixed5s framed-write cap. Four focused
cases failed before correction and passed afterward. The final source passed
**50 Windows transport tests, zero skips/failures,22.23s**:

```powershell
.venv/Scripts/python.exe -m pytest tests/market/test_native_windows.py -p no:cacheprovider --basetemp=.tools/native-worker-20261110/task2-fix1-host-temp
```

The211-case result is the earlier integration checkpoint, not a repeated result
on the final correction. No public API or frozen helper changed. Independent
re-review replayed the original bounded probes and accepted all three fixes.

Real harmless-process cases include duplex/EOF, blocked pipes, nonzero exit,
hidden worker/probe, excluded inheritable capability, unrelated sentinel survival,
owner death killing its Job, and observation7/complete before one ACK/end at7 and39.
Quota readback and initial/terminal monitor records use actual OS queries. RSS/disk
thresholds, writer stalls and OS failures are injected rather than multi-GiB or
physical-disk stress claims. All harmless worker fixtures have a12s self-exit limit.

The transport confirms exits while retaining ownership so the later session can
close its journals and perform the final source check before releasing handles.
Caller confirmation of evidence closure is an obligation, not independently observed
proof. Unknown launched-probe identity retains ownership and throws a closed error;
it cannot fabricate a successful cleanup receipt. No transport method creates a
final seal or claims an integrated native run.

Reusing frozen Windows primitives imports the existing stdlib-only recorder through
`market_supervision`/`market_artifacts` and the two package initializers. Tests allow
exactly this required chain; no engine/data/neural module or simulator DLL is loaded.
The same64 frozen sources,41 packaged members and seven old artifacts are unchanged.

## Integrated local pilot software

Worker/session, public D1 coordination, HTTP/measured-status display and explicit
prepare/start/inspect CLI are implemented. Following the request to finish the
local pilot, the same engine/session machinery now has a separately versioned
live-pilot/v1 profile. The original v1 proof remains exactly40 observations/20model
seconds/900real seconds and rejects live evidence outside its declared scope.

Live defaults to8real hours, accepts1–720minutes and a maximum of86400 observations.
Limits are bound before release; there is no repeated-worker simulation reset.
Observations remain500ms, images require8 contiguous validated observations, black
intervals still advance, and learning/DAN remain off. Memory/Job limits remain4GiB;
live disk is bounded at8GiB, with6GiB event and1GiB monitor limits. This is a storage
ceiling, not a preallocation or proof of12-hour throughput. Live journals are streamed
for inspection; a wall-limited run is explicitly partial rather than complete.

The existing ContinuousMotorDrive consumes exact validated group bins and actual
start/completion times through a bounded public feed. A separate native SQLite
schema/database admits those proposals through the existing transaction, board
presence, pause and postcommit30-real-minute cooldown checks. Synthetic APIs cannot
submit native proposals. Full jumps within configured bounds remain allowed; no
retargeting, retries, forced rotation or learning claim is introduced.

Independent source reviews covered core/CLI, price and HTTP/intake/UI. Price review
found and closed stale-clock and terminal-drain/activation races. Core review found
and closed conflicting startup cleanup epochs, nonterminal D1 receipts reaching a
complete seal, doubled live observe deadlines and misleading CLI mode/limit text.
The inspectors and original numerical sources were not weakened to close findings.

Root's combined pre-core-fix run passed1084 Market tests with5 existing Windows
symlink-privilege skips in220.78s; viewer passed318 with1 existing Windows symlink
skip, plus build. The previously omitted actual owned generated-PNG coordinator
case also passed separately in0.25s and in that full Market run. After the grouped
core fixes, affected parent/live/CLI tests passed89 with1 path-location-dependent
test deselected, followed by17 final live tests. That deselected CLI path test had
passed in the combined run using a temporary root outside the allowed .tools area.
Final price fixes passed36 focused cases; the unchanged authority had passed119
regressions. Exact-source CI will supply the next combined checkpoint.

These are software/fake-engine and harmless-process results. No actual simulator,
graph acquisition, compiler probe or paid API ran for this implementation evidence.
No multi-hour performance or scientific support is inferred.

## Remaining work

Exact-source CI, a concrete finite preflight, actual image-to-native/price integration
and browser inspection. Longer real-time rehearsal and public operation remain
distinct from the first local pilot; rich live cell/anatomy rendering is not added
by this minimal measured-status pane.
