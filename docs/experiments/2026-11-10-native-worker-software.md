# Bounded native worker — software and local pilot evidence, 2026-11-10

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
regressions. Subsequent exact-source CI is recorded below.

These are software/fake-engine and harmless-process results. No actual simulator,
graph acquisition, compiler probe or paid API ran for this implementation evidence.
No multi-hour performance or scientific support is inferred.

Current source `9e6fa86` passed all four
[CI42892533266 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42892533266):

| Job | Passed | Skipped | Duration |
| --- | ---: | ---: | ---: |
| Market | 1030 | 77 | 129.11s |
| Native/session | 1469 | 47 | 352.50s |
| Market buffers | 253 | 6 | 356.11s |
| Viewer | 315 | 4 | 90.780s |

Viewer build also passed (355ms). Skips remain explicit; these data-free/tiny-native
compatibility jobs establish neither the actual full-graph pilot nor multi-hour
capacity. The previously published `760d03b` checkpoint also passed all four jobs.

## Actual finite local run

The separately released second attempt at `.tools/native-pilot-20261110-02/`
completed on November 10 with one continuous existing native engine. It was bound
before release to `live-pilot/v1`, 80 observations / 40 model seconds and 600 real seconds,
using the existing prepared graph/cache and no paid provider request. Source was
`9e6fa86bc42aa7cf790767bc1054f1fc2c0fa3fb`; CLI exited 0. The public `inspect` command
exited 0 and reports
`complete`/`model_limit`, 80 observations, 197 event records, 3462 monitor records,
99 matching source/lock/tool/cache files and no first or cleanup fault. Independent
inspection accepted the complete finite run, including full EOF, source and cleanup;
the inspector's verification remains integrity-only.

The public HTTP client followed 438.266 real seconds and exited 0 after the expected
server connection close. It made one primary claim/resume, two generated PNG
uploads and one approval per image, with no mutation retries. Original five-minute
handoff TTLs were preserved. Actual receipts show:

| Input | Measured observation indices | Result | Canonical RGB SHA256 |
| --- | --- | --- | --- |
| A, red/blue stripes | 15–22 | processed, 8/8 | `0ed4b02146ccfceb967bc55c1499deb88de0676eb4d8807d44e8a7088829d968` |
| B, green/magenta checker | 23–30 | processed, 8/8 | `9581f69336b912b39c4e631a1ce69a10bcca72fae48593925df1e388212f9f41` |

B was accepted 10.906 real seconds after A, after A's start was confirmed. The same
session advanced 64 black-input and 16 image-input observations in total, without reset,
learning or external DAN. The HTTP observer retained native progress through 80/80
and 40 model seconds; its final price snapshot was paused with price version 1.

The separate native-price SQLite database contains one actual activation:
`drink-00`, CHF4→CHF5, price/drink version 1 at `2026-11-10T20:15:07.575751Z`.
The database contains two native proposals: sequence 58 activated CHF4→5; sequence 78
was `no_change`. It contains one activation and zero fixture requests. Independent
review exactly rederived both targets and their configuration/path/clock bindings
from recorded bins. The other 19 test drinks remained CHF4. This is a configured
motor-readout result, not evidence that either image caused the choice, semantic preference or biological
learning. The original 30-real-minute per-drink cooldown was retained; this short
run cannot establish repeated cooldown expiry or multi-hour operation.

Confirmed terminal cleanup records worker/probe exit 0, empty Job and closed owned
IPC/process/Job/evidence/root-lock handles in 2.3486257s. Peak worker RSS was 910184448 bytes,
peak Job commit 2005450752 bytes, peak recorded output 3720701 bytes and maximum monitor
gap 392.4927ms. These are measurements for this finite run, not capacity guarantees.

Actual browser inspection covered the read-only board at 1440×1100 with the CHF5
price/status/table and 390×844 with page width 375 and no horizontal overflow. The
terminal view correctly retained last-known paused/unknown status and 40 model seconds.
The only runtime resource error was favicon404; connection-refused polling errors
followed the expected server shutdown. The minimal live pane shows seven measured
groups and freshness, without rich live cell/anatomy rendering.

Retain the separate first attempt `.tools/native-pilot-20261110-01/`: its 5s compiler
probe-start timeout occurred before any observation and cleanup was confirmed. Its
root cause remains unexplained. A separate startup-context diagnostic established
an initial tuple/list identity mismatch that was fixed in `9e6fa86`; this does not
establish the cause of the first attempt's timeout. No failed attempt is relabelled
as the successful second run.

Local raw evidence remains under `.tools/native-pilot-20261110-02/`; HTTP receipt
history/summary and desktop/mobile/price screenshots remain under
`.tools/pilot-acceptance-20261110/`. Private role URLs/capabilities are not published.
Exact terminal hashes:

- `final.json`: `bedbf9c3d63e3a28c4aa0ce3b710f141d4fc7109f329af0441115558f6591bbd`.
- `cleanup.json`: `8f6ccc2144b5ca1f798affc5e58f3062c3f8ef367f71603120088b8387749078`.
- `http-02.summary.json`: `1790429b6f0b0305b0a950b7f267dac8c30c03f8c19c87b21fc4c20808bab297`.

## Remaining work

Longer real-time rehearsal and separately authorized public operation remain
outside this local result. Rich live cell/anatomy rendering is not implemented by the measured-status
pane. No scientific qualification or biological validation is established.
