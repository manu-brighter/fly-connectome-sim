# Local image intake — component evidence

Status: all three components and the complete local intake integration are
independently accepted after corrections and actual browser checks. Source CI
remains outstanding. No native worker
is connected, and no image has changed a drink price.

The coordinator composes unchanged admission and owned decoding. It retains one
decode task, one canonical pending image and at most512 receipt capabilities.
Complete upload acceptance starts the original10s decode,60s moderation and300s
handoff limits. Approval only queues the image; without a worker it eventually
expires. There is no processed status or renewed deadline in this slice.

Separate image capabilities cannot equal existing price credentials. Public
authentication and finite rate gates precede admission/status access. Clock faults
freeze existing credits and make timing uncertain. Shutdown cancels, joins and
keeps decoder ownership until cleanup is confirmed.

## Task1 checks and corrections

Locally generated inputs only; no user photos, native run or provider request.

| Check | Actual result |
| --- | --- |
| Initial complete affected suite on Windows host |428 passed, four privilege skips,54.30s |
| Clock-boundary regressions before review corrections |18 failed,69 deselected,0.99s |
| Corrected clock-boundary regressions |18 passed,69 deselected,0.17s |
| Complete correction and neighboring-boundary checks |30 passed,69 deselected,0.20s |
| Corrected complete affected suite on Windows host |458 passed, four privilege skips,49.67s |
| Independent correction and neighboring-boundary checks |39 passed, no skips |

The initial independent review found three P2 boundary failures. A final D1 read
could expire an image while the response still advertised its preview; retention
pruning could return the wrong error and spend a reader credit; and a late clock
fault could leave trusted-looking times on a terminal receipt. The correction
reconciles real D1 receipts/snapshots before response construction and guest charging.
At most three target reads cover live→terminal→pruned; an inconsistent view fails
closed. It preserves stopped D1 retention and never manufactures a terminal state.
Independent re-review accepted all three corrections and Task1 after39 real-D1
boundary checks. These include deadline/pruning transitions at successive samples,
frozen diagnostic credits, both automatic transitions in one call and the explicit
three-read bound. Acceptance applies only to this coordinator component.

Self-review also corrected earned-credit retention on clock failure and thread
construction/partial-start failures. Genuine regression failures precede their
corrections. Initial scaffold failures, a fixture-name overflow caused by a large
parameter ID and three Windows sandbox failures remain recorded as unsuccessful
attempts. The unchanged Windows tests subsequently passed with host execution;
no assertion was relaxed.

Final affected command:

```powershell
.venv/Scripts/python.exe -m pytest tests/market/test_image_intake.py tests/market/test_image_admission.py tests/market/test_image_decode.py tests/market/test_image_decode_worker.py tests/market/test_image_decode_windows.py -q -p no:cacheprovider --basetemp=.tools/image-intake-20261110/task1-fix-final-regression-host-20261110-01
```

All99 coordinator cases passed. The four skips are unchanged D2 symlink tests
requiring unavailable Windows privilege1314. Full Market HTTP regression and
source CI remain later integration gates; this result is not that evidence.

An actual generated69-byte1×1 red PNG passed through real D2 into12288 canonical
RGB bytes, preview, approval and confirmed cleanup. The same decoder work root
could then be reopened. A separate injected close-failure test retained the real
root lock until a successful retry. Join-timeout tests use controlled thread
behavior; they do not prove a physical25s OS termination guarantee.

The512-receipt test bypasses only the upload-rate gate through a test-only public
D1 reservation seam. It proves a structural capacity/pruning boundary, not512
simultaneous guests: ordinary1-per10s pacing and900s retention cannot naturally
reach that count. Normal authentication/rate/retention tests use public intake gates.

Private logs and fixture receipts remain under `.tools/image-intake-20261110/`.
The prior D1/D2 and price sources,64 frozen helpers,41 packaged members and seven
historical artifacts remain unchanged. No process containment, public readiness,
event capacity, native measurement or scientific validity follows from these
coordinator tests.

## Task2 HTTP/CLI checks and corrections

The optional `--image-work-root` composes the existing loopback server, shared
clock and owned decoder. Default synthetic mode remains unchanged. Five bounded
image routes enforce role-specific capabilities, original deadlines and private
canonical previews; image actions never change prices. The guest asset route was
checked with generated build fixtures; its actual frontend remains Task3.

| Check | Actual result |
| --- | --- |
| Initial HTTP/CLI suite |70 passed,19.76s |
| Initial full Market suite |709 passed, five privilege skips,101.05s |
| Maintenance-failure regressions before correction |5 failed |
| Corrected maintenance-failure regressions |5 passed,55 deselected,3.68s |
| Final HTTP/CLI suite |74 passed,28.84s |
| Final full Market suite |713 passed, five privilege skips,134.88s |
| Independent correction scenarios over actual loopback HTTP |7 passed |

The independent review found one P2 failure: a swallowed maintenance exception
left image routes accepting work. The correction irreversibly fences image
actions before requesting public coordinator stop. Confirmed stop retains finite,
truthful diagnostics; failed stop refuses all image routes and retains ownership.
Bodies already being received cannot mutate after the failure. Price maintenance
continues independently. Independent re-review accepted Task2 with no open blocker.

Final full command:

```powershell
.venv/Scripts/python.exe -m pytest tests/market -q -p no:cacheprovider --basetemp=.tools/image-intake-20261110/task2-fix1-market-host-01
```

The five skips are the unchanged Windows1314 symlink cases: four decoder cases
and one existing price HTTP case. Actual generated69-byte PNG uploads produced
12288 canonical RGB bytes through owned D2, then preview, approval/expiry or
rejection and confirmed cleanup. Expiry uses a controlled clock, not a five-minute
rehearsal. Actual CLI child processes covered a deliberately unread202 and shutdown
during receive. A separate direct-server case covered owned Job cancellation;
an injected CLI close-failure case verified retained ownership.
The cancellation case uses a harmless waiting child, not an active image conversion;
the close failure is injected, not a physical OS fault. Neither proves an OS
termination guarantee. Seven independent correction scenarios use actual HTTP,
real D1/coordinator and a logic decoder, not a new native or D2 conversion run.

Initial setup/sandbox failures and the eager optional-helper import regression
remain recorded. Lazy optional imports preserve all four original default-mode
no-native process checks. Optional-mode guards allow only the existing package,
experiment package and recorder helper imports; no simulation engine executes.
No original price assertion, D1/D2 source, frozen helper, package member or
historical artifact changed. Complete integration CI remains outstanding.

## Task3 browser interface and corrections

The guest page sends bounded raw files and retains one receipt in memory. The
operator pane shows hash-verified64×64 RGB pixels, requires that current displayed
preview for approval and clears it on stale/disconnected/queued state. Image
requests have independent controllers/timers; the read-only board has no image
traffic. Disabled intake hides the optional pane after its404 probe. Original
price assertions remain unchanged; their test fixture now models that extra probe.

| Check | Actual result |
| --- | --- |
| Initial source-freeze focused UI/price-render suite |33 passed, no skips |
| Initial source-freeze complete viewer |287 passed, one existing Windows link skip,57.614s |
| Independent-review regressions before correction |3 failed,16 passed |
| Corrected targeted tests |19 passed |
| Corrected focused UI/price-render suite |36 passed, no skips |
| Corrected complete viewer |290 passed, one unchanged Windows link skip,58.107s |
| Corrected TypeScript/Vite build |Exit0; existing large viewer-chunk warning |
| Independent correction and neighboring-state probes |72 passed |

Initial self-review corrected the response-body deadline, a late upload response,
retry hash identity and a wrong browser digest prefix using behavioral regressions.
The independent review then reproduced three issues: superseded successful
moderation could retain its mutation lock, inherited object properties bypassed
the closed detail parser, and nonready intake looked like a healthy empty service.
The correction releases only the completing operation's lock, requires own declared
detail keys and displays clear stopped/unavailable state. Independent correction
review accepted all three findings and the complete local integration after72
additional parser, async lifecycle and health/staleness checks.

Commands from `viewer/`:

```powershell
node --test tests/image-*.test.mjs tests/market-render.test.mjs
npm test
npm run build
```

The sole local viewer skip is an existing unavailable Windows dangling-link
privilege. Workflow/race tests use explicit DOM/fetch/clock doubles; these do not
establish actual browser or native behavior. Missing-API scaffolding, intermediate
compile failures and the initial old-fixture probe conflict remain unsuccessful
attempts, not passing evidence. No original price assertion was weakened.

Actual Chrome157 checks use generated images, real SystemClock and owned D2
against disposable loopback services. The initial build passed guest validation,
invalid-image rejection, exact canvas RGB/hash comparison, offline clearing and
reconnect, rejection, approval, full-intake refusal, disabled/read-only roles and
independent synthetic price controls. One explicit synthetic proposal changed
CHF4→7 while the approved image waited; no image action changed prices.
An actual five-minute wait produced queued→expired for the same identity/hash,
observed at accepted_age301615ms with zero remaining time and no preview. Exact
service shutdown exited0, removed scratch and allowed decoder/both price-owner
reacquisition. A fresh corrected-build run independently confirmed exact pixels,
mobile layout, focus preservation during polling, offline clearing/reconnect and
rejection. Its actual queued/expired browser responses crossed the same original
deadline at age299678ms/rest322ms→age301687ms/rest0. Cleanup again exited0 with
scratch absent and decoder/both price owners reacquired; no price changed in that
second run. Both services used real clocks; neither expiry was accelerated.
All owned tabs closed, preserving the original blank tab. Private evidence records
mistaken harness waits separately from actual application outcomes.

These are bounded local checks, not a hostile public-upload assessment,300-guest
load test,12-hour rehearsal or neural measurement. The [local setup](../getting-started.md#local-image-upload-and-moderation)
uses the optional Windows decoder; opening capabilities and generated/private
evidence stay outside Git.

## Remaining integration

The accepted [plan](../superpowers/plans/2026-11-10-image-intake.md) awaits the
reviewed source checkpoint and its four existing CI jobs.
Continuous native handoff, measured display and real price admission are later work.
