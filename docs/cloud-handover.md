# Continuation handover — experimental v1, 2026-11-10

## Start here: accepted scope and current status

### Current continuation request

**November 9 product discussion supersedes automatic continuation:** the user
paused the next-feature discussion to define a live event drink-price market.
The [concept](superpowers/specs/2026-11-09-live-drink-market-design.md)
records full jumps anywhere within each drink's allowed range and at least
30 minutes of real time between actual changes of the same drink. There is
**no CHF0.50 per-change cap** and no mandatory periodic price update. The user
requested learning recommendations and concept definition before an implementation
plan. The user has now answered both product questions: **staff adopts prices
from the board manually; the model chooses the drink as well as its price.**
There is no POS integration in the first pilot. The proposed activation semantics
are an automatic durable server-side price version, without staff confirming
every change, and a clearly marked last-known display state on disconnection.
These are technical planning decisions, not a claim of simultaneous screen updates.
The recommendation is activity-driven operation without new training first,
with a separate evidence gate for any later learning claim. The
[staged implementation plan](superpowers/plans/2026-11-09-live-drink-market.md)
details an offline population/timing inventory as Stage A, then separately gated
readout/performance measurements, price service/board, uploads/live display and
rehearsal. **The user approved the plan and autonomous execution on November 9:**
continue until finished or explicitly stopped, with up to ten subagents requested;
this platform permits three concurrent children. Stage A is now complete
and independently accepted: [population inventory](experiments/2026-11-09-market-feasibility.md),
148 passing tests / five declared Windows symlink-privilege skips, and actual
sealed-run inspection without a new fullgraph run or API call. Published feature
`dcb7f79a24bcab16b07fa1d2b13e4cb516a277cc` passed
[clean-checkout CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42648225025):
429 backend tests / eight skips, 243 viewer tests / four private-artifact skips
and build. All five locally skipped analyzer symlink cases passed on Linux. The separate
[historical KC screen](experiments/2026-11-09-market-kc-screen.md) found that one
of twenty fixed artificial groups dominated every strict maximum; it does not
qualify twenty-drink control. Sampled-cohort recruitment began near two seconds
despite nonblack inputs, so very short negative probes would be inconclusive.
The [matched-state input-response diagnostic](experiments/2026-11-09-market-response-diagnostic.md)
is now executed and independently accepted within its declared scope. Source
`5c3611bb686bcfc56ba8a006aaf52be5181ce95f` passed
[CI42661319868](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42661319868):
482 backend tests / 34 skips, 243 viewer tests / four private-artifact skips and build.
The reviewed runner and Windows supervisor preserve the neural package and old
artifacts, bind the actual Python process/cache/compiler, count scratch and use
owned-job cleanup plus tested cancellation. Source/test history is retained in
the [implementation plan](superpowers/plans/2026-11-09-market-response-diagnostic.md).

One fresh acquisition at `runs/market-response-20261109-01/` and
`.tools/market-response-20261109-01/` executed 34 model seconds, 68 observations,
79 sealed events and 3,400 bins. Resources: 151.89 s wall, 877,383,680 bytes actual worker
peak RSS, 45,719,150 bytes sampled output peak / 22,946,791 retained, zero active processes
after cleanup. Black/A/C repetitions match exactly. A/B and C/D primary responses
differ; all active primary KC vectors still peak at group 10, so 20-way selection
is not established. Motor signs vary across windows. There was no training/API call.
The [frozen protocol](superpowers/specs/2026-11-09-market-response-diagnostic.md)
remains historical evidence; completed directories must not be resumed.

The subsequent offline receptor check shows that A reaches receptors; it is not
blind input. It does not isolate how coverage, spatial targets and network dynamics
produce the output difference.
The [sequential motor readout contract](superpowers/specs/2026-11-09-sequential-motor-readout.md)
and its [offline implementation](superpowers/plans/2026-11-09-sequential-motor-readout.md)
are independently accepted. The [software result](experiments/2026-11-09-sequential-motor-readout.md)
records 98 passing synthetic tests and Astra's additional 1,296-block direction
matrix. Fixed binary decisions address the ordered drinks, with neutral
rearm and a separate supported price block. This is an engineering mapping, not
twenty biological channels. No neural reachability is claimed. Checkpoint
`af4879b004f2eb7e263004a84c1e93cbe3adedac` is pushed; its
[CI42669739632](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42669739632)
passed: 580 backend tests / 34 skips, 243 viewer tests / four private-artifact
skips and build. The next [continuous probe protocol](superpowers/specs/2026-11-09-continuous-motor-probe.md)
and [plan](superpowers/plans/2026-11-09-continuous-motor-probe.md) are prospectively
accepted:96model seconds,192observations, six new analytic patterns in two fixed
orders, continuous engine/decoder and scheduled black intervals;900s/4GiB/256MiB
bounds. Its external runner/auditor is now independently accepted:
[software evidence](experiments/2026-11-09-continuous-motor-software.md),154 passing
focused tests with one Windows symlink-privilege skip. A review finding corrected
the whole-brain count lower bound for disjoint versus overlapping populations;
all68 earlier diagnostic observations also satisfy it. The thin new supervisor
and preserved PowerShell frontend are now independently accepted, with all35 new
supervision cases passing on the host. Combined runner/supervisor verification:
91 passed /one existing Windows symlink-privilege skip. Actual harmless-process
completion, cancellation, owner-death and unrelated-PID evidence was independently
checked; the package, decoder, old helpers and historical artifacts remain unchanged.
Task1 checkpoint `c0c0887cd8299c18106fe4aaddee86d84a0286af` passed
[CI42676056860](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42676056860):
637 backend tests /34 skips,243 viewer tests /four private-artifact skips and
build. All57 new probe cases passed on Linux. Final Task2 source checkpoint
`1d32e1c89e9d94659e43a24b8cbbee08e1cf2425` passed
[CI42678625455](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42678625455):
665 backend tests /41 declared skips,243 viewer tests /four private-artifact skips
and build. Seven new Windows lifecycle cases skip on Linux; all35 passed locally.

After independent concrete preflight, one continuous acquisition completed at
`runs/continuous-motor-20261109-01/` and `.tools/continuous-motor-20261109-01/`.
The [actual result](experiments/2026-11-09-continuous-motor-probe.md) is independently
accepted as **valid negative**: all192 observations/9600 bins/194 events and two
checkpoints, zero complete proposals. One3–5s block (L44/R17) selected the lower
half `[0,10)`; no later observation met the neutral bound. Later black observations
still contain6–27 combined motor spikes versus the maximum2. The partial path
expired at39model seconds by its300-real-second bound. Increasing expiry alone
would not supply the missing neutrality. The final pending state has no drink or price.
Actual resources:804.609s wall,858718208bytes held-worker peak RSS,
40652389bytes sampled output peak/20667412 retained,3131 samples,maxgap0.266s,
zero active owned processes after cleanup and empty stderr. Source and old
artifacts remain unchanged; no second attempt or paid request ran.

Result checkpoint `0c255b78e57b4a04cd284d47a9e9a6064e1e3705` passed
[CI42682879706](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42682879706):
665 backend tests /41 skips in267.32s,243 viewer tests /four skips and build.

**Latest completed candidate: the offline-first rearming revision** under its
[separate spec](superpowers/specs/2026-11-09-balanced-motor-rearm.md) and
[plan](superpowers/plans/2026-11-09-balanced-motor-rearm.md). It retains quiet rearm
and adds four non-overlapping observations with block total at least20 and each
within an exact10% left/right balance band. The band is an engineering choice,
not fitted or biologically validated. A thin external v2 subclass preserves v1;
it does not remove the observed left bias. One complete unchanged-clock software
replay is independently accepted as [negative development evidence](experiments/2026-11-09-balanced-motor-rearm.md):
all192 results equal v1, no balanced releases and no proposals. Preserve both
candidates and their negative results. V2 source is independently accepted:101 new
synthetic cases plus98 unchanged v1 cases pass, zero skips;105 existing tracked
source/helper/core/lock files remain unchanged. Preflight, trace and summary are
separate local evidence under `.tools/balanced-motor-rearm-20261109/`; they never
replace the native v1 recording. No new simulation or provider call ran.
Stage B remains open; no Stage C, favorable-window search, twenty-slot/price-policy
qualification or new acquisition follows automatically. Completed run directories
must not be reused. Stop local cutoff/rearm iteration: this candidate supplies no
reason to repeat a native run. Checkpoint
`c73fa83384f698c4793a7b32d5ab84c1251f2a67` passed
[CI42686215403](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42686215403):
766 backend tests /41 skips in320.85s,243 viewer tests /four skips and build.

**Latest completed measurement: recorded response structure**, under its prospectively
accepted [spec](superpowers/specs/2026-11-09-response-structure-inventory.md) and
[plan](superpowers/plans/2026-11-09-response-structure-inventory.md). Analyze the
existing matched-state diagnostic only, with all64 arm/windows and224 fixed pairs.
Twenty original KC groups plus the eleven excluded sampled KCs cover all231
recorded KCs; exact composition comparisons distinguish scaling from distribution
changes. Seven population profiles are tested for common scaling separately,
without pretending that overlapping populations partition the brain. Source and
the [actual inventory](experiments/2026-11-09-response-structure-inventory.md) are
independently accepted. One offline invocation took7.4114244s and preserved all
old artifacts. KC relations:106 both-silent,96 one-silent,7 proportional and15
nonproportional; normalized silent comparisons remain undefined. Primary B/C/D
sampled totals250/260/270 have pairwise TV12/325,29/750,107/2340 (about3.7–4.6%).
Repeated C contributes duplicate pairs; these are not independent replicates.
All64 vectors/224 comparisons and repeat checks were independently recomputed.
There are54 distinct new test passes/two Windows symlink skips and184 unchanged
offline regression passes/five symlink skips/four explicitly excluded native cases.
No new model run or API call occurred. The complete233732-byte report remains
local at `.tools/response-structure-20261109/report.json`, SHA
`eedb293babe890d136587365bcf476d682f7ced1fe6228de20275fc9eda6a481`.

Source/result checkpoint `dfe16787573d911bd68973a3bbfe9e00e09a6249` passed
[CI42691875940](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42691875940):
822 backend tests /41 skips in263.92s,243 viewer tests /four skips and build.
All56 new analyzer cases passed on Linux, including the local symlink skips.

**Latest completed candidate:** the prospectively accepted
[population-excursion prerequisite screen](superpowers/specs/2026-11-09-population-excursion-screen.md)
and [plan](superpowers/plans/2026-11-09-population-excursion-screen.md). Use all192
old continuous observations/48 fixed blocks as development calibration only.
Freeze four-channel offsets/scales and fixed engineered MBON/DAN contrast axes,
exact20-sector rays, support and excursion thresholds before actual calculation.
No anchor or no adjacent confirming opportunity stops this candidate before a
full decoder or acquisition. An opportunity alone proves neither a proposal nor
price support. Source and the [actual negative screen](experiments/2026-11-09-population-excursion-screen.md)
are now independently accepted. One offline invocation took3.3264181s; all192
vectors/48 blocks were retained and independently recomputed. There are zero
supported blocks, no anchor and no opportunity. Only block0 satisfies geometry,
but its three support streams are silent and fail all absolute gates; blocks1–47 pass
absolute support but fail the four-sample geometry. The fixed candidate stops;
do not implement its full decoder, tune its constants or acquire another run for it.
The482571-byte complete report at `.tools/population-excursion-20261109/report.json`
has SHA`b0d8e64c99fe8bb57280c12591ab4e0a0d4e773058732692dfdbb75455f6e2b6`.
Software evidence:600 offline tests passed/11 genuine Windows symlink skips/four
explicitly excluded native cases, plus five focused review-fix passes. All63 old
source/package/lock files remain unchanged. Six production sources and seven original
continuous artifacts matched before/after the actual calculation. No native/API
execution occurred. Source/result checkpoint `93e6f1db66b8d9ae4fb504fa961a7bfb835f4f39`
passed [CI42698918907](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42698918907):
932 backend tests /41 skips in546.58s,243 viewer tests /four skips and build.
Any further readout requires a distinct justified contract, not a silent rescue.
Twenty engineered output regions do not require twenty biological channels;
current matched-state data cannot establish robust continuous-state decisions.
Specify calibration versus independent evaluation, abstention and separate neural
contributions to drink, price and timing before mapping. Do not stretch small
differences into20 outputs merely to obtain coverage. No fitted decoder, new
acquisition, threshold sweep or Stage C follows automatically. The broader
user-authorized market task remains open.
The user now explicitly accepts long quiet phases and drink favorites in the
experimental pilot, as long as every configured drink remains technically
selectable. Actual all-drink occurrence in a finite recording is not required.
Report technical versus observed coverage separately; no forced rotation or cadence.

**Latest completed readout:** the independently accepted
[continuous motor drive contract](superpowers/specs/2026-11-09-continuous-motor-drive.md)
and [two-task plan](superpowers/plans/2026-11-09-continuous-motor-drive.md).
Quiet/recovery was an event-detector assumption, not a user requirement. This
distinct engineering mapping starts ready and consumes fresh supported four-sample
blocks for every binary direction and a separate price block, preserving all v1
thresholds, clocks, guards and provenance. Sustained newly measured drive may
repeat a favorite; it does not establish repeated biological intention or image
influence. The tiny external subclass and516 targeted tests are now accepted;
all165 leaves across sizes10–20 and both price endpoints are synthetically covered.
All110 old files remain byte-identical. One2.9660187s unchanged-clock development
replay is independently accepted: [actual result](experiments/2026-11-09-continuous-motor-drive.md).
All192 observations yield8 proposals for drink-00, with prices500/450/450/450/500/
500/550/450 Rappen;33 lower decisions,7 unsupported blocks, no resets. Observed
coverage1/20 is distinct from technical reachability. The final partial lower-half
decision is not a ninth proposal. No new native/API run or sale-price activation.
Trace SHA`fb1c0302c174bd2fd1090527430fdfc55fdc774e5b604231fccb4854e312a85f`,
summary SHA`897693bdce9b0a34a90dcec8e6c08427229c98e8299f0d54d683c077649b0608`;
both complete local artifacts are under `.tools/continuous-drive-20261109/`.
Input/frame
changes remain documented within a continuous path, as in v1; they are not reset
boundaries. Previous negatives remain intact. Source/result checkpoint
`979b67bbaf8529ad9de98ccfa45a415656b73756` is published; its
[CI42702799722](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42702799722)
passed:1350 backend tests /41 skips in443.95s,243 viewer tests /four skips and build.
All418 new driver cases passed on Linux. The separate held-out functional/input-sensitivity
[protocol](superpowers/specs/2026-11-09-drive-input-comparison.md) and
[three-task plan](superpowers/plans/2026-11-09-drive-input-comparison.md) are now
independently accepted and published as `8fec9466a1a655fe46917d650f4d258ece2c7e0e`.
Task1 runner/auditor is independently accepted:
[software evidence](experiments/2026-11-09-drive-input-software.md),150 focused
passes/330 deliberate exclusions/no skips. The pending-state reporting finding
was corrected and independently rechecked; all57 old source files and the41-member
package fingerprint are unchanged. Task2 thin supervision is now independently
accepted:139 focused passes/one Windows symlink-privilege skip/three deliberate
private runtime-preflight exclusions in39.10s. Actual harmless-process receipts
confirm completion/cancellation/owner-death cleanup and unrelated-process protection;
all58 preexisting sources and the package fingerprint are unchanged.
Protocol checkpoint CI42704146157 passed1350backend/41skips548.50s,
243viewer/4skips and build; this precedes new Task1 source.
Its fixed shape is84model seconds:4s black prefix, common checkpoint, four20s
arms (black, newA, newB, repeatA), each with a fresh decoder and unchanged real clocks.
A/B are complementary32px quadrant patterns with exact logical RGB hashes and
equal pixel brightness, chosen without model/projection evaluation.
Function, output sensitivity and individual drink/price/timing components remain
separate; timing-only effects cannot establish image-caused price changes.
Final source checkpoint`dd60d5584fd74f2d362667685cdec543cea3d68e` passed
[CI42709083761](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42709083761):
1469 backend tests /47 skips in618.99s,243 viewer tests /four skips and build.
After independently accepted concrete preflight, exactly one acquisition completed
at `runs/drive-input-comparison-20261109-01/` and matching `.tools/` evidence.
The [actual result](experiments/2026-11-09-drive-input-comparison.md) is independently
accepted:168 observations/8400 bins/175 events/
three checkpoints; A450Rappen at18s, B500Rappen at14s, bothdrink-00; black0proposals,
A repeats exactly. Full A/B motor sequences differ; no clock/path resets occurred.
Observed1/20 coverage remains separate from all20 technical routes. Equal pixel
brightness gives unequal retinal population coverage, so spatial vs population
input-magnitude effects are not isolated. Resources:482.719s wall,856920064bytes
worker peak,50399859bytes combined output peak/25571025retained,1880 samples,
maxadjacentgap0.266s,cleanup0,stderr0. All frozen sources remain unchanged.
No retry or paid call. Result checkpoint`4862f84ff681fe958ffb852528ada7a2a589e8aa`
passed [CI42713559202](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42713559202):
1469 backend tests /47 skips in685.71s,243 viewer tests /four skips and build.
The next separate [passive-cell/rolling-buffer protocol](superpowers/specs/2026-11-09-live-buffer-performance.md)
and [four-task plan](superpowers/plans/2026-11-09-live-buffer-performance.md) are
independently accepted prospectively:60 model seconds,256 passive observed cells,
1000 original bins in fixed arrays, one pending image, three synthetic full-queue
rejections, exact five-minute expiry and unchanged900s/4GiB/256MiB supervision.
Prospective checkpoint`1ad9f53b8e753b6176c942f66feed86e02137410` is published.
Task1 ring/admission source is now independently accepted:
[software evidence](experiments/2026-11-10-live-buffer-software.md),640 focused
passes/no skips or warnings,60 old sources and41 package members unchanged.
Ring storage stays288000 array bytes; explicit sequence watermarks prevent request
revival. Five ringhash vectors were independently verified. Task1 is local
checkpoint`b358f4ad10d54d6404e6f81bd5c82faba9b0787f`. Task2 producer/auditor is
now independently accepted:55 new synthetic cases plus640 unchanged cases passed
their latest execution. The complete run had694 passes and one incorrect reset
fixture; the corrected case then passed alone in12.46s. All61 old sources and41
packaged members remain unchanged. Task2 local checkpoint is
`e1dd77df21054e00a010226a0599e7e91233e3cb`. Task3 thin supervision and the separate
pinned15-minute CI job are now independently accepted:218 passing focused tests,
two true Windows symlink-privilege skips, three explicitly excluded private runtime
preflight cases. Actual harmless completion/cancellation/owner-death receipts have
cleanup0; unrelated-process protection passed. All62 old sources/41 package members
remain unchanged. CI preserves every old test and adds exactly one new supervisor
path; Actionlint passed. Final source`70a73b19125d89fab5d4796284047b04eddd6752`
passed [CI42722594833](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42722594833):
1469 old backend passes/47 skips in634.94s,253 new buffer-suite passes/six Windows-only
skips in182.48s,243 viewer passes/four skips and build. Concrete preflight passed;
the one acquisition is complete and independently accepted:
[actual result](experiments/2026-11-10-live-buffer-performance.md). All120 observations,
6000 bins/600 windows/122 events/two checkpoints are intact; ring1000 retained/5000
evicted,256 measured cells/512 static edges. B/C waits147000/156671ms, three full
rejections, no expiry. Five proposals all drink-00 at450/450/550/500/500 Rappen;
no resets/open paths. Resources477.704s wall,944357376B workerpeak,41836953B sampled
combined output peak/21157074B retained,1862 samples/maxgap0.266s,cleanup0/stderr0.
All64 frozen sources remain unchanged. Actual artifacts are under
`runs/live-buffer-performance-20261110-01/` and matching`.tools/`; never resume.
The actual Python3.12 Windows monotonic clock is GetTickCount64 with15.625ms
resolution; QPC sink/copy timings have100ns resolution. The old1ms quantization
rationale was too strong. Frozen checks passed; retain the original source and
records, document this limitation and use a common high-resolution clock in future
service work. No rerun or threshold change is justified.
**Next accepted continuation:** separately specify/implement the local synthetic
Stage-C price service/board. Astra judged the scoped evidence sufficient under
the accepted slow pilot/favorite criteria. Keep durable integer prices, full
bounded jumps, per-drink30-real-minute cooldowns, pause, idempotency and conservative
restart/clock handling. This does not accept live uploads, browser performance,
300-guest/12-hour load or public operation. Preserve old10-second parsers and the
core; no further readout tuning or native acquisition is required for Stage C.

The [local synthetic board design](superpowers/specs/2026-11-10-local-price-board-design.md)
and [four-task implementation plan](superpowers/plans/2026-11-10-local-price-board.md)
are now prospectively accepted after independent architecture and contract review.
Python/SQLite owns prices, postcommit cooldowns, restart recovery, presence and
idempotency; a separate TypeScript board uses the existing viewer build. All service
durations share the high-resolution authority clock. Race tests cover late pause
versus resume, presence loss during rollback and retired primary sessions.
Prospective checkpoint `b05ce336600ed1e8031907b2a3bad10813ab93ba` and accepted result
`6c7685c` are published on the feature branch. Execute the four bounded tasks with
Sol and independent Astra reviews. Task 1's authority is independently accepted:
95 tests passed without skips in 8.24 s on Windows, including real SQLite-full,
rollback-journal and process-ownership evidence. One review correction preserves
capacity across immediate restart and later clock/storage faults; a separate
re-review accepted both that fix and closed-authority error handling. Price jumps,
postcommit cooldowns, idempotency, presence fences and pause/resume races are
covered. Task 2's bounded local HTTP/fixture adapter is independently accepted too:
the complete Market suite passed 177 tests / one Windows symlink-privilege skip
in 27.14 s. Actual sockets cover deadlines, eight-handler overload, later overload
versus resume, lost responses and restart. The independent static security review
found no actionable issue; it read actual source/logs and did not execute code.
CLI interruption was injected at serve entry, not an OS-console Ctrl+C test.
Task 3's separate board is implemented and independently source-reviewed after
correcting activation indicators lost on immediate rerender. The final complete
Windows viewer suite passed 270 tests without skips (247 existing plus23 new),
and the two-entry build passed. Actual bounded browser checks cover claim/ACK,
resume, full400-to700 jumps, cooldown/no_change, pause, read-only access, offline
unknown/reconnect and retained keyboard focus. All20 synthetic drinks were
activated individually; all20 cooldown rows fit at1920x1080 and1280x720, with
normal single-column scrolling at390px. Reduced motion and the10.62:1 main color
pair were checked. Actual hidden-tab behavior could not be induced in the
headless browser; its abort/no-ACK behavior has unit coverage. A harmless favicon404
remains. Task4's cross-process tests, CI configuration and operator instructions
are now independently accepted locally: four real process cases passed in2.20s
(independently2.15s), complete Market suite181 passed/one Windows symlink skip
in29.85s. Actual COMMIT-before-anchor crash retains the activation and restarts
paused with full recovery; lost-response retry after restart preserves the same
result and ledger counts. A verified real-interpreter PID fixes the Windows
test harness, with no product change. Normal CLI interruption is test-injected,
not a physical-console Ctrl+C observation. See the [result and limits](experiments/2026-11-10-local-price-board.md)
and [local start instructions](getting-started.md#local-synthetic-drink-price-board).
StageC is complete within that local synthetic scope. Published source
`b2eda225cf9709f1abf5d383c19106d707eb5444` passed all four
[CI42741755078 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42741755078):
182 price passes/no skips in22.18s (including POSIX ownership and symlink rejection),
1469 existing backend passes/47 skips in632.97s,253 buffer passes/six Windows-only
skips in260.97s,266 viewer passes/four private-artifact skips and build. The local
270-pass viewer evidence remains separate. The next StageD
[image-admission contract](superpowers/specs/2026-11-10-image-admission-design.md)
and [single-task plan](superpowers/plans/2026-11-10-image-admission.md) are now
independently accepted prospectively. Implement only the metadata lifecycle:
one receiving-or-pending slot plus one active image, immutable300s acceptance-to-
handoff deadline, finite receipt history and explicit unknown worker outcomes.
Receipt timing and retry/contradiction/index-overflow precedence were corrected
before implementation. This starts no decoder, HTTP upload or native worker and
changes no price; those are later reviewed slices. No sale prices, public readiness
or neural integration are claimed.
Local D1 implementation now exists in `market/image_admission.py` with134 focused
passes and315 complete Market passes/one Windows symlink-privilege skip. An
independent review found shared mutable metadata references; the correction added
18 regression cases, and independent fix re-review accepted the complete
D1 slice with seven additional reproductions. The
[implementation evidence](experiments/2026-11-10-image-admission.md) records the
exact limits. Published source `6d72ed70353cb0ef3404303be6f071078f77da23` passed
all four [CI42803437054 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42803437054):
316 Market passes/no skips,1469 native/session passes/47 skips,253 buffer passes/
six Windows-only skips,266 viewer passes/four private-artifact skips and build.
D1 is complete within its metadata-only scope. The next
[decoder contract](superpowers/specs/2026-11-10-image-decoding-design.md) and
[plan](superpowers/plans/2026-11-10-image-decoding.md) are independently accepted
prospectively. Task1, the private canonical pixel/protocol worker, is now
independently accepted locally after closing a duplicate-PNG-header depth bypass:
120 focused passes/three Windows symlink skips and15 independent re-review passes.
[Component evidence](experiments/2026-11-10-image-decoding.md) separates historical
and corrected results. Task2 ownership/cleanup and complete local D2 integration
are now independently accepted after final cancellation/EOF corrections:225
decoder passes/four Windows privilege skips,540 full Market passes/five privilege
skips,14 Windows checks and16 independent correction checks.
Published source`cbc41a35eec5b1b64cdd1dce33082a6a70e060b2` passed all four
[CI42814654483 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42814654483):
529 Market passes/16 Windows-only skips,1469 native/session passes/47 skips,253
buffer passes/six Windows-only skips,266 viewer passes/four private-artifact skips
and build. All five locally skipped symlink cases passed on Linux. D2 is complete.
The next local [intake/preview/approval contract](superpowers/specs/2026-11-10-image-intake-design.md)
and [three-task plan](superpowers/plans/2026-11-10-image-intake.md) are independently
accepted prospectively after public auth/rate API, capability separation and
verified-preview corrections. Task1 coordinator is now independently accepted
after fixing final-read expiry/pruning/clock inconsistencies:458 affected passes/
four Windows privilege skips, all99 coordinator cases and39 independent boundary
checks. [Component evidence](experiments/2026-11-10-image-intake.md) records the
actual owned generated-image fixture and the test-only512-receipt pressure seam.
Task2 optional HTTP/CLI is also independently accepted after correcting a
maintenance-failure fence:74 focused passes,713 full Market passes/five unchanged
Windows privilege skips and seven independent loopback scenarios. Actual generated
PNG→owned D2→private RGB→moderation and CLI shutdown cases passed; controlled-clock
expiry and injected failures are labelled in the component evidence. The guest/
operator UI is now implemented and corrected after three independent findings:
290 viewer passes/one existing Windows link skip and build0. Initial actual Chrome
checks include matching D2/canvas pixels, real five-minute expiry and confirmed
owner cleanup. Corrected-build checks also passed real expiry, mobile/focus/offline
behavior and cleanup;72 independent correction cases passed. All three components
and the complete local integration are independently accepted. Published source
`31f82947451899577b4607c2616e5cb3dc5ed055` passed all four
[CI42834493163 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42834493163):
693 Market passes/25 Windows-specific skips,1469 native/session passes/47 skips,
253 buffer passes/six Windows-only skips,287 viewer passes/four absent historical
artifact skips and build. The local intake slice is complete. No neural
worker is connected; approved images queue and expire without a processed claim.
The next [bounded native-worker contract](superpowers/specs/2026-11-10-native-worker-design.md)
and [five-task implementation plan](superpowers/plans/2026-11-10-native-worker.md)
are independently accepted prospectively. Implementation is next: one owned
Windows worker, genuine eight-observation image completion and bounded measured
telemetry. The engineering proof allows40 observations/20 model seconds,900 real
seconds and one terminal session; these are not event-duration limits. Intake-only
mode and synthetic prices remain available. The review resolved compiler-probe
ownership, final-observation/ACK ordering, bounded public D1 receipt capture,
exact wire/HTTP/evidence variants, dependency bootstrap and confirmed cleanup
with final source checks. A controlled public-D1 probe reproduced the earlier
final-read expiry gap; the accepted replacement uses at most three atomic
snapshots and two terminal reads. Missing retained evidence is an explicit
journal_gap, never a fabricated completion. Contract checkpoint`c1d6c03` passed
all four [CI42844507066 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42844507066).
Task1's protocol/evidence library is implemented and independently accepted after
binding the original D1 deadline and monitor coverage:410 affected passes,
zero skips. [Software evidence](experiments/2026-11-10-native-worker-software.md)
separates analytical black/image fixtures from actual native exposure and records
the authenticated lock-read and platform-path limits. No live worker is connected.
Published Task1`b86a319` passed all four
[CI42851467117 jobs](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42851467117),
including845 Market passes/25 existing Windows-specific skips; all152 new
protocol/evidence cases passed on Linux. Task2 owned transport is independently
accepted after fixing common cleanup-budget enforcement, unknown probe-exit
confirmation and the framed-write cap. Earlier host integration:211 passes;
final transport source:50 passes/zero skips, with actual harmless-process evidence
distinguished from injected faults. The required frozen-helper import chain is
stdlib recorder/package initializers only, with no simulator initialization.
Tasks3–5 and the requested complete local pilot implementation are now independently
source-reviewed, including native price admission, versioned live profile and minimal
measured display. The strict40-observation v1 proof remains separate. The user asked
to prioritize direct implementation, with no further specification rounds and no
pause at intermediate commits. Root's integrated pre-core-fix checks passed1084
Market tests/5 existing Windows symlink skips and318 viewer tests/1 existing skip,
plus build; grouped core fixes passed89 affected tests and17 final live tests.
The four core findings and three price handoff findings are independently closed;
the HTTP/intake/UI review found no blocking source defect. See the updated
[software evidence](experiments/2026-11-10-native-worker-software.md).
No actual native worker has yet run. Next: exact-source CI, concrete finite local
acceptance with generated images, actual source-bound execution/browser inspection,
then the usable local pilot. Preserve the distinction from multi-hour performance,
public deployment and scientific support. Continue until the local pilot works.
Independent source/CI and
concrete finite preflight gates precede one actual run. The330-file baseline
preserves all64 frozen helpers,41 package members
and seven historical artifacts. Native price admission and richer measured live
presentation follow; never route real evidence through the synthetic fixture path.
The preservation baseline records all 270 preexisting tracked files, all 64 frozen
helpers unchanged and the same 41-member package fingerprint. No new dependency,
provider call or fullgraph acquisition was needed for the completed local intake.
The earlier planning checkpoint passed
[CI42730169795](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42730169795):
1469 existing backend passes / 47 skips in 634.51 s, 253 buffer passes / six
Windows-only skips in 355.87 s, 243 viewer passes / four private-artifact skips
and build. This CI precedes the new application implementation.

The protocol-only checkpoint `f07988a` triggered
[CI42671895977](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42671895977),
which failed before creating any jobs, including one unchanged retry. GitHub's
visible annotation says "Internal server error" on both attempts. This is not a
test failure or a successful check; the workflow and executable source match the
successful `af4879b` run. Local implementation continued during that outage;
Both later source checkpoints passed CI; the concrete acquisition preflight and
actual-result review are complete. The outage remains historical evidence only.
The user explicitly approved slower-than-real-time model operation for the first
local pilot, with an honest model clock and fresh/queued status; the price lock
still uses30 minutes of real time. The user selected a maximum five real minutes
queue wait until simulator handoff, with rejection when the finite queue is full.
Expired entries must never be handed off late; concrete capacity and performance
remain to establish. This does not guarantee delivery through a worker failure.
User-supplied scale:
10–20 drinks, 50–300 guests, usually 6–8 hours; shorter or roughly 12-hour
events are exceptions. Duration stays configurable; 12 hours is the initial later long-run test
reference, not an automatic shutdown limit. Necessary new measurements require
a concrete reviewed protocol and finite resource bounds before execution;
do not launch indefinite fullgraph runs or infer live learning, paid API use,
POS access or deployment. Do not return to the previous event-input editor.
Technical mapping covers all configured drinks; observed neural target variety
and continuous event operation remain distinct, unqualified claims.
The existing demo and its evidence below remain complete and unchanged.

After the reviewed presentation repair, the user requested sequential autonomous
continuation until the agreed work is finished, they say stop, or the token limit
is reached. **Do not pause automatically after each commit/push.** Keep a small
number of agents: bounded implementation with Sol, difficult design/integrity
review with Astra, and preserve progress in tracked checkpoints.

**The agreed experimental observation v1 scope is complete.** The genuine API
proposal → continuous native session → measured choice → unchanged plan → film
chain and the bounded recorded single-cell/static-connection view are accepted.
No further acquisition, provider request or feature expansion is needed for that
completed scope. The user subsequently selected **LLM feedback and event-plan
continuation**: a separate German companion to the fixed, inspected selection.
This is now **complete and independently accepted** under the
[follow-up contract](superpowers/specs/2026-11-08-event-followup.md) and
[plan](superpowers/plans/2026-11-08-event-followup.md): offline-first CLI,
unchanged original plan, one bounded live acceptance, no new fullgraph recording.
The [accepted result](experiments/2026-11-08-event-followup.md) is local at
`runs/event-followup-live-20261108/event-plan.md` with JSON/request/receipt beside
it. The single call used308input+228output=536tokens and15.562s, nominal
USD0.001257 at the checked tariff; actual billing was not inspected. All seven
historical source files and the full plan stayed identical. No more provider
calls or acquisitions are needed for this selected continuation.
After the next `continue`, the controller stated the next-step assumption:
show that existing companion directly in the viewer. This local-only display
is implemented under the [viewer contract](superpowers/specs/2026-11-08-followup-viewer.md)
and [plan](superpowers/plans/2026-11-08-followup-viewer.md), with no new provider
request, simulation or film. Sol implemented it and Astra independently reviewed
the source/UI. The [browser acceptance](experiments/2026-11-08-followup-viewer.md)
checks the real saved pair, decision/rewind visibility, desktop/mobile layout,
exact Markdown download and unchanged original plan. Separate declared fixtures
cover replacement/defer; all 15 historical inputs and 41 package sources remain
unchanged. Astra accepted the actual desktop/mobile screenshots and independently
matched the inputs, package identity and downloads. This bounded viewer
continuation is complete and published as `46e0200c2a94c88f984f8c4b5f65617e8cdffa94`.
Its [clean-checkout CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42522727223)
passed: 343 native/backend tests with 8 declared skips; 151 viewer tests with
2 private-artifact parity skips, plus typecheck/build. Locally all 153 viewer
tests passed without skips. No additional provider request or acquisition is
needed for the completed companion/viewer scope.
The user then explicitly selected **Einfacher lokaler Demo-Start** as the next
step: a preparation command and one combined viewer file selection for the
existing recording, cells, anatomy and companion pair. This is now implemented
under the [local demo contract](superpowers/specs/2026-11-08-local-demo-open.md)
and [plan](superpowers/plans/2026-11-08-local-demo-open.md). Reuse accepted files;
no new API request, native acquisition, packaged Python/C++ change or deployment.
The [actual combined-import result](experiments/2026-11-08-local-demo-open.md)
uses `runs/local-demo-20261108/`: exactly five verified copies, one selection,
all existing brain layers and choice-gated notes. Invalid import retention,
rewind, picker cancellation, delayed replacement and desktop/mobile layout passed.
Final local viewer suite: 246 passed, one Windows link-creation skip; build passed.
Astra independently accepted source, actual visual evidence and artifact bindings;
the step is complete and published as `c7bbbdc99ed39e6e03facd43902e3c71ffc71bce`.
[Clean-checkout CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42525145089)
passed 243 viewer tests with four private-artifact parity skips and a successful
build; the Windows-skipped dangling-link case passed on Linux. Backend/native
compatibility passed 343 tests with eight skips. No further acquisition or
provider request is needed to use the prepared demo folder.
The learning assay and broader platform work remain separately parked.
Aggregate group bins cannot reconstruct individual spikes; the new cell view uses
separately captured counts. Static connections are not measured transmission.

The [cell activity contract](superpowers/specs/2026-11-07-cell-activity-replay.md)
and [sequential plan](superpowers/plans/2026-11-07-cell-activity-replay.md) now fix
256 selected cells, at most512 existing directed edges, original native-bin
counts and completed100ms display windows. Astra completed protocol and process
supervisor review. A non-neural host smoke test verified actual child-process
monitoring; sandbox CIM restrictions require host execution for supervision.
The first implementation attempt hit a usage limit before code changes. The user
resumed on November8. Sol implemented the passive observer, fixed source-bound
cohort/topology, incremental raw writer, verified sidecar export and a script
composing the existing session workflow. 29 focused tests passed; combined
regression170 passed with4 Windows permission skips, and those4 then passed on
the host. Astra found and reviewed a correction binding the exporter to the
canonical recording file's actually inspected bytes; both defects had failing
regression tests before correction. Backend and safe API diagnostics are now
reviewed. Final combined host tests:285 passed,2 symlink-privilege skips in129.20s;
hardlink/junction tests passed. The viewer is now implemented and source-reviewed.
Its final full suite passed135 tests with zero skips in26.682s; build passed.
Actual synthetic browser checks cover both live proposal plans, pending/defer and
the corrected first paint. See the
[backend/API checkpoint](experiments/2026-11-08-cell-capture-api.md).
That checkpoint is committed/pushed as `f5766f5094599ff2529436bfabc06c34009441cb`.
Its [Linux compatibility run](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42428235786)
passed:185 native/backend tests,1 Windows-only junction skip; both new symlink
cases ran successfully. The unchanged viewer passed114 tests and its build.
That was the backend checkpoint, not film acceptance. The subsequent reviewed
source checkpoint `776465dce2ece99ffdec74a43d6f6116157ecc60` passed
[Linux CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42431095712):
185 native/backend tests, one Windows-only skip, 135 viewer tests with no skips
and a successful build. Actual recording/film acceptance below is separate from
synthetic fixtures; no interrupted review counts as acceptance.

The first acquisition launch stopped after0.353s because the supervisor counted
pre-existing regression fixtures inside its evidence directory:1,814,974,188
observed bytes exceeded the256MiB acquisition output cap. Both owned processes
ended without cleanup errors. `runs/cell-demo-20261108/` contains only an empty
`session/` directory; logs are empty and no measurement files were produced.
Original attempt, source freeze and supervision receipts are preserved locally.
Supervisor v2 isolates new acquisition evidence from prior validation artifacts
and retains all caps. Both non-neural host smoke tests passed; Astra independently
reviewed source/receipts and all 119 retry-freeze hashes. The user explicitly
authorized the second launch at `runs/cell-demo-20261108-02/` with isolated
evidence under `.tools/cell-acquisition-20261108-02/`. It completed in 109.223 s;
both exit codes were zero, with no cleanup errors. Observed native peak RSS was
948,957,184 bytes and acquisition output peak 47,844,542 bytes. No automatic
retry occurred; the first incomplete attempt remains intact.

The accepted recording has 7 s feed + 2 s cards, 214 observations, 1,040 native
bins and 90 completed 100 ms windows. Its fixed cohort has 256 positioned cells
(KC 231/4,064 plus all mandatory groups), 512/4,254 directed connections and
5,388 recorded counts across 98 active cells; maximum 14 per cell/window.
Final L7/R2 selects Sunset Rooftop Social through the unchanged lateral policy.
The saved/downloaded plan exactly retains the live proposal. Independent source,
bin/window, artifact and film audits passed. Actual Chrome 157 on Windows 11
played all 360 VP9 frames / 12 s at 900×900 without error or dropped frames;
the final 3 s is a labelled frozen-measurement hold with illustrative tap.
The actual 341×1600 narrow view was checked. See the
[accepted report](experiments/2026-11-08-cell-capture-api.md) for hashes and limits.

The user delegated model/token selection. The offline request at
`runs/proposal-preview-20261107/` uses `gpt-5.4-mini-2026-03-17` with 2048 output
tokens, the existing Summer team party / 100 guests / CHF5000 brief, and request
SHA256 `945b86de95401e1349c418e45507d3015ea3cb85e3a064cb69c020e25b8dac51`.
The current [official model page](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
supports Responses/structured output and lists USD0.75/M input and USD4.50/M output
tokens; the displayed rough estimate is 1–2 US cents for one call, not a monetary
cap. On November8 the user created an API project/key and stored it in the
Windows user environment as `OPENAI_API_KEY`; a presence-only check confirmed it
there. Read that user value locally into the request process if the running
app's inherited environment is stale. Never print or persist it.

The first live attempt at `runs/proposal-live-20261108/` exited1 with the existing
sanitized `Event proposal transport failed`. It retains only the2024-byte
`request.json`, no validated proposal/receipt or token usage; the precise cause,
transmission status and any charge are unverified. No automatic retry occurred.
After API credit setup, the user explicitly authorized a second attempt.
`runs/proposal-live-20261108-02/` completed with a validated proposal/receipt:
357 input +241 output =598 tokens, requested/returned model
`gpt-5.4-mini-2026-03-17`, nominal USD0.00135225 at the checked tariff. Request
bytes exactly match the offline preview. Proposal SHA256 is
`da144f530f962b07431200684b7b3d0e74c0d5b42d5f066431fc9b989741e397`.
The two concepts are Sunset Rooftop Social / Indoor Summer Bash, within the
unchanged brief. They remain illustrative estimates, not verified venues/costs.
This exact successful `proposal.json` was used for the accepted cell-detail session.
**No further provider request is needed for the current demo.** The user asked
to keep API spending bounded and purposeful. Do not purchase credit, enable
recharge or retry automatically. Actual billing deductions were not inspected.
The completed fullgraph observation is distinct from tiny-native test fixtures
and the immediately aborted first launch. It establishes an experimental replay
demonstration, not scientific qualification or semantic preference.

### Completed observation baseline

The user accepted the direction review on 2026-11-07: finish a **local,
experimental, measured-data replay demo**. The original training/research goal
remains a separate follow-up. Do not resume the historical assay checklist just
because it has unchecked tasks. Replay-first was an explicit user decision.

The product chain is implemented: real reel RGB -> one native MaleCNS engine ->
measured motor activity -> left/right/defer -> unchanged event plan -> smooth
3D replay. **The [bounded diagnostic](experiments/2026-11-07-content-side-diagnostic.md)
found that this specific real-versus-black visual manipulation changes motor
activity and the final adapter result.** The fixed8s feed is separate from the adaptive demo.
Card relocation reveals layout/history sensitivity, not stable semantic event
preference. A positive MBON11 assay would not automatically establish that:
the current event/video policies
use only DNa02 motor-left/right, not the older MBON/motor preference adapter.

**Tasks 1 and 3 are complete within the imported-proposal observation scope.**
After the user reopened visual acceptance, the [reviewed presentation repair](experiments/2026-11-07-scientific-presentation.md)
replaced the intersecting tablet with safe placement and a selected-card tap,
and added static source anatomy plus seven recorded population traces.
`runs/scientific-demo-20261107/` contains the revised 30 fps film, exact original
recording/plan and optional bound anatomy file. The [previous film](experiments/2026-11-07-final-demo.md)
remains historical; its earlier visual acceptance was insufficient.
**Task 2 and the recorded cell-view extension are now accepted** through the
November 8 native session, unchanged plan and actual film. This closes the agreed
observation scope, not the broader research/event-platform specification.
Use the November 8 bundle for the current presentation; retain November 7 as
historical evidence. Do not repeat the diagnostic,
expand controls, resume research or run a fresh simulation merely for UI work.

## Repository, authority and working style

- Local workspace: `C:/dev/jogge-di-fly-brain`; public repository:
  `https://github.com/manu-brighter/fly-connectome-sim`.
- Branch: `feat/connectome-experiment-core`; remote: `origin`. The prior
  `5ec5398` film-documentation checkpoint is superseded by this presentation repair.
  Use the latest pushed feature HEAD, not a
  checkout/reset to that historical hash. Verify status/tracking before edits.
- Autonomous relevant implementation, tests, reviews, commits and explicit
  `git push -u origin feat/connectome-experiment-core` are authorized. Never
  push main/master/develop, force-push, discard existing work, create PR/merge,
  deploy, or change remote resources/settings without separate authority.
- German, short updates. Routine implementation/fixes/reviews use Sol; difficult
  scientific, architectural or integrity decisions use Astra. Keep delegation
  bounded, no repeated full-project reviews or many simultaneous agents.
- Ask only for actual product decisions, missing authority or irreversible work.
  A missing API credential/cost configuration is a real external prerequisite;
  do independent work without requesting secrets in chat.
- Follow [AGENTS.md](../AGENTS.md), including English commit convention and no
  attribution signatures. Stage explicit first-party files and inspect diff/size.
  Runtime/data, `.tools/`, `.venv/`, `.superpowers/`, `.ai/`, egg-info, runs,
  checkpoints, media, chats and reference images remain ignored/uncommitted.
- Continue through reviewed feature checkpoints under the current user request;
  stop for completion, an explicit stop, the token limit or a real unresolved
  dependency. Do not invent extra product scope or resume parked research.

## Read only what the next task needs

1. [AGENTS.md](../AGENTS.md), [README](../README.md), this handover.
2. [Revised scientific presentation](experiments/2026-11-07-scientific-presentation.md),
   [continuous-session contract](superpowers/specs/2026-11-03-feed-event-session.md),
   [workflow acceptance](experiments/2026-11-07-session-workflow.md) and
   [usage](getting-started.md#continuous-reels-and-event-choice).
3. For content comparison: [session pilot](experiments/2026-11-03-feed-event-session.md),
   `src/fly_connectome_sim/experiment/feed_event_session.py`, `video_observation.py`,
   `video_policy.py`, `event_choice.py`, `event_cards.py`, `adapter.py`, and
   `src/fly_connectome_sim/engine.py`; corresponding `tests/experiment/` files.
4. For provider work: [proposal contract](superpowers/specs/2026-11-06-event-proposal-transport.md)
   and [usage](getting-started.md#optional-model-generated-event-proposals).
5. [Original product specification](specs/fly-event-planner.md) is background;
   its original training-first sequencing/mixed adapter are superseded for the
   current observation v1 by this accepted direction. Preserve scientific claims.

The [full prior handover/history](handover-history-2026-11-07.md) preserves all
old task IDs, hashes, detailed acceptance and assay continuation links. Consult
it on demand; it is not the current execution order. Private local notes and
this long chat are not required to continue from a fresh checkout.

## Experimental v1 tasks, in order

### 1. Bounded visual-content and side diagnostic

- [x] Write a short fixed comparison protocol before running it. State exact
  inputs, checkpoint/start state, clocks, comparisons, output measures and a
  finite run/resource budget. Have Astra review the scientific interpretation
  once; use Sol for bounded implementation, test-first where code changes.
- [x] Separate **feed after-effect** from **response to event cards**. Compare
  the same start state and schedule with a controlled changed image sequence
  (e.g. black frames) and separately swap card positions. The current public
  feed policy changes duration based on activity; do not confuse different
  exposure times with a content effect. A small diagnostic harness may need
  fixed observation timing rather than copying the adaptive feed unchanged.
- [x] Measure actual native motor counts/rate time courses and adapter outputs;
  report changes, no change, side bias and defer honestly. Existing pilot count
  differences are not controls. Different pixels/hashes alone are insufficient.
  Do not tune thresholds, hunt a winner, require a selection reversal, change
  the kernel or launch the full learning grid to obtain a positive result.
- [x] Publish a concise scoped result and update the presentation claim. An
  absent effect is acceptable for an honest activity-driven demo; a claim of
  content-dependent preference requires supporting evidence. These controls
  cannot establish semantics, biological learning or general reel preference.

Completed once on2026-11-07: two fixed8s feeds and six2s probes from matched
complete checkpoints,28s cumulative/504 observations. Real versus black feed
changed12/16 motor windows; the common black probe showed residual differences
in4/4. Final counts after real feed: normal L11/R1→left/Sunset House, swapped
L7/R0→left/Warehouse Techno, black L5/R5→defer. After black feed: normal0/0→defer,
swapped1/8→right/Sunset House, black0/0→defer. All outcomes/ten contrasts retained.
The [result](experiments/2026-11-07-content-side-diagnostic.md) records204 passing
tests, independent raw audit, Astra reviews and the disclosed Windows launcher
RSS-monitor correction. No native repeat, threshold tuning or new learning claim.
Raw output remains local at `runs/content-diagnostic-20261107/`; use it for
inspection, not as a session recording accepted by the viewer.

### 2. One genuine LLM proposal -> session acceptance

- [x] Configure local key/model/token settings and make the offline request
  reviewable. The initial November7 missing-key blocker was resolved November8.
- [x] Complete one validated live proposal after the explicitly authorized
  second attempt; exact request/proposal/usage evidence is recorded above.
  Existing `prepare-event-proposal` still defaults offline. Only explicit local
  key/model/token configuration and `--allow-paid-request` enable one paid
  request. Token limit is not a monetary cap. Do not retry automatically.
- [x] Pass the fixed successful `proposal.json` through the accepted November 8
  cell-detail capture that composes `run-session`; the selected option/brief/
  programme and downloaded plan exactly match. Earlier pilots retain their authored
  `examples/event-options.json` origin and cannot substitute for this check.

### 2b. Bounded feedback to the selected event — accepted

- [x] Fix scope with the user: separate German planning companion, no changed
  original plan or new neural recording. Astra design review completed.
- [x] Implement offline-first `prepare-event-followup`, source binding, strict
  response handling and JSON/Markdown publication; review/test before live use.
- [x] Inspect one actual offline request, then make one bounded live acceptance
  using the accepted session and pinned model,1024 output tokens,120 s deadline.
- [x] Independently inspect actual text/usage/source hashes and document the new
  source identity. No automatic provider retry. Feature publication and its
  compatibility outcome are established by the corresponding Git/CI receipts.

### 2c. Local companion viewer — accepted

- [x] Bind the two imported companion/receipt files to the exact original
  recording and complete plan; download only checked Markdown bytes.
- [x] Gate text/download by the current recorded choice, including rewind,
  replacement, stale imports and deferred results; preserve original plan export.
- [x] Independently accept actual desktop/mobile display, original downloads
  and unchanged historical files; use declared fixtures only for race/defer checks.
- [x] Publish the reviewed feature checkpoint and observe successful clean-checkout
  CI. See the [viewer result](experiments/2026-11-08-followup-viewer.md).

### 2d. Simple local demo start — accepted

- [x] Prepare exactly five checked copies using bounded reads and exclusive output.
- [x] Open recording, cells, anatomy and companion pair with one selection;
  preserve old state on failure and ignore superseded asynchronous imports.
- [x] Accept real prepared files, choice/rewind/download behavior, desktop/mobile
  layout and unchanged original artifacts; independently review source/evidence.
- [x] Publish the reviewed feature and observe successful Linux CI, including
  the dangling-link test. [Result and commands](experiments/2026-11-08-local-demo-open.md).

### 3. Final demonstration and v1 close-out — presentation repaired

- [x] Accept the November 8 genuine-proposal session with 256 recorded cells,
  static source connections, unchanged plan and actual 30 fps film. Independent
  raw/source/film review, complete playback and narrow layout passed. The agreed
  experimental scope is closed; broader platform and research remain separate.

- [x] Repair tablet/fly intersection, place the fly looking at the display and
  animate one selected-side tap after the measured decision. Keep simulation
  time frozen throughout the existing presentation hold; defer never taps.
- [x] Add static source-bound cell-body anatomy and seven measured population
  traces to the exported canvas. No invented individual spikes or synapse
  locations; the existing recording contains aggregate group bins only.
- [x] Review actual geometry, encoded frames, scientific labels and unchanged
  recording/plan, then publish a replacement presentation checkpoint.

The historical November 7 replacement has 360 VP9 frames / 12 s at 900×900, with the same 7 s feed,
2 s cards and 3 s presentation hold. Both contact paths retain original limb
lengths and clear tablet/body meshes; the real film shows reach, contact and
retraction on the selected left card. Anatomy uses 12,000 real sampled somata
from 139,662 positioned model cells, with 27,038 missing positions explicit.
All seven traces use recorded bins; terminal values freeze during the tap.
114 viewer tests and 10 generator tests passed, build passed, actual Chrome
playthrough completed and independent source/frame review found no open blocker.
See the [repair report](experiments/2026-11-07-scientific-presentation.md) for
artifact hashes, source checks, responsive scope, warnings and limits.

The earlier export checks below remain historical:

- [x] Accept one coherent representative recording, bound plan and playable
  exported film, with clear real-input/measured-output/illustrative-motion labels.
  Reuse existing data for rendering work; only new input/provider/diagnostic
  needs justify new native runs. Longer feeds are optional, not a prerequisite.
- [x] Check actual exported video playback/timing and readable choice or defer;
  retain exact source recording/plan and concise reproduction commands. Do not
  silently reuse a historical film as evidence for a newer recording/source.
- [x] Align README/product scope with actual observation v1 and known limits.
  Record remaining training/research work separately and stop expanding v1.
  No post-choice narration, autonomous multi-round planner or deployment is needed.

Historical imported-proposal demo: `runs/final-demo-20261107/` retains the exact
November 7 session recording/plan and a newly exported `demo-30fps.webm`.
Actual Chrome 157 export/playback and full decode passed: 360 VP9 frames,
900×900, 12 s = 9 s recorded data + 3 s labelled presentation hold. Final
L6/R2 → left/Sunset House and the bound plan are unchanged. No new native
simulation ran; this uses historical source identity `f3ef2ff6…`, not the
newer diagnostic source. Viewer checks: 97 passed, no skips; build exited 0.
See the [final report](experiments/2026-11-07-final-demo.md) for exact artifact
hashes, reproduction, warnings and limits. This older film is superseded by the
reviewed November 7 repair and the accepted November 8 cell-detail demonstration.

**Completion rule:** the diagnostic, genuine proposal/session path and current
representative film are accepted. Close this agreed experimental v1 scope; do
not infer further features, research resumption or deployment from that closure.

## What already works and available local evidence

- Locked official MaleCNS v1.0 inputs/prepared graph: 166,700 cells,
  25,582,938 directed edges, 124,177,617 synaptic contacts.
- Existing Python/C++ native core, explicit PAM11/PPL101 stimulation, checkpoint
  restoration/continuation, KC/MBON07/MBON11/DNa02 telemetry and append-only runs.
  Mechanism correctness does not establish learned behavior.
- Fast feed: 5x source-content sampling; nominal 3s minimum watch/4s clip cap,
  8s total feed cap. Cap takes priority: a third clip can end after 2s. Then
  exactly 2s event cards, no reset/state replacement, no external DAN/learning.
  Final 500ms counts select/defer at the existing uncalibrated 1Hz threshold.
- Foreleg reach/stroke/retract is illustrative 400ms motion, content scroll
  occupies its middle 200ms. Replay/video export is 30fps and consumes recorded
  measurements; motion is not measured anatomy or validated motor behavior.
- `run-session` composes recording/export/plan and final local receipt;
  `inspect-session` rederives outputs from bounded raw verification without an
  engine/network/writes. Receipt/integrity does not attest native history.
- Current local bundle: `runs/cell-demo-20261108-02/` contains the ordinary
  `session/` bundle, raw/exported cell detail, optional anatomy and the accepted
  `demo-30fps.webm`. It is 9 s measured data plus a 3 s presentation hold, final
  L7/R2 → Sunset Rooftop Social. Reopen it without another simulation/API call.
- Historical local bundle: `runs/session-workflow-20261107/` contains `recording.json`,
  `plan.json`, `receipt.json`, and `run/{run.json,events.jsonl,checkpoints/}`.
  Its actual 9s run was 7s feed+2s cards, final L6/R2 -> Sunset House. This is
  a historical result. CLI wall time was 98.969s for that
  specific workload; not a general capacity estimate. This exact recording was
  newly exported and played through for the final demo, without native rerun.
- Historical combined film acceptance: 360 frames/12s including 3s terminal
  hold, from the separate 2026-11-03 recording. See its linked session report.
  It is separate from the newly accepted November 7 film and retains its own
  historical source/acceptance context.
- Historical one-command scoped suite: 315 passed/5 sandbox skips; those 5 host path cases
  separately passed. Historical [CI run](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42380161212)
  on `981373b`: 142 passed/1 Windows-only junction skip; viewer 97 passed/build0.
  CI is data-free tiny-native Linux compatibility, not fullgraph qualification.
  See [CI evidence](experiments/2026-11-07-clean-checkout-ci.md).

## Local commands and missing cloud inputs

From the existing Windows workspace (choose new output paths; parent must exist):

```powershell
git status --short --branch
.venv/Scripts/python.exe -m fly_connectome_sim.cli inspect-session runs/cell-demo-20261108-02/session
npm --prefix viewer run dev
# Open recording -> runs/cell-demo-20261108-02/session/recording.json.
# Open cell counts -> runs/cell-demo-20261108-02/cell-activity.json.
# Optional Open anatomy -> runs/cell-demo-20261108-02/anatomy.json.
# Play/seek/inspect, or open existing demo-30fps.webm. No simulation rerun is needed.
# Export video only to reproduce presentation. Do not assume an old server is running.
```

Only when a new observation is justified:

```powershell
.venv/Scripts/python.exe -m fly_connectome_sim.cli run-session --playlist .tools/reels-source/playlist.json --proposal examples/event-options.json --output-dir runs/NEW-session
```

Available local tools: `.venv/Scripts/python.exe` (3.12.14), `.tools/uv/uv.exe`
(0.12.15), `.tools/zig/zig-x86_64-windows-0.16.0/zig.exe`, Node24.21.0/npm11.19.0;
media extra PyAV19.0.2. Viewer `npm ci`, `npm test`, `npm run build` are documented
in [Getting started](getting-started.md). Data root defaults to
`data/malecns-v1.0/runtime/`; set `FLY_CONNECTOME_SIM_DATA` before imports if moving it.

Local ignored `.tools/reels-source/playlist.json` points to existing
`DcTiO6Ls3HT.mp4` and `DZHp4mtNvJb.mp4` in the same directory. URLs:
https://www.instagram.com/reel/DcTiO6Ls3HT/ and
https://www.instagram.com/reel/DZHp4mtNvJb/ . Other supplied source candidates:
`DVi5CMeDH2B`, `DI_HK5_gXrq`, `C8hNXYegKhB`; not all are downloaded/accepted.
Fast-feed decoding requires each source's complete first20s; URLs are provenance
labels, not automatic downloads. Audio is not neural input.

A cloud checkout has none of the ignored runtime, media, toolchains or run bytes.
Follow [setup/data instructions](getting-started.md) or run the
[CI-selected data-free checks](getting-started.md#clean-checkout-compatibility).
Never claim local historic evidence was reproduced in cloud. GitHub CLI is
available at the documented WinGet path in the user's instructions; host auth
works but sandbox credentials were invalid, so request normal auto-review host
execution when required. No authentication settings were changed.

## Scientific boundaries and deliberately parked work

Preserve core/provenance/locks/MIT notice; never weaken checks for a positive
result. No claims of consciousness, understanding, dopamine concentration,
receptor activity, biological learning or validated motor behavior. Advance all
scheduled intervals, including explicit black RGB uint8 frames; individual
observe calls <=500ms. Reward-free observations use no external DAN and
learning=False. Same-state comparisons must preserve real clocks and passive decay.

Do not automatically resume C1/7B4f.3c-d, global grid/selected-evidence integration,
assay CLI/capacity, LF/formal source-freeze, fullgraph qualification/frozen config,
held-out confirmation or old/trained-state resumption. Fullgraph-Linux, broader
hostile-artifact/resource hardening, all-browser/accessibility coverage and
narration are separately scoped future work, not this v1's remaining checklist.
For an explicit research return use the archived handover and
[current assay plan](superpowers/plans/2026-09-24-associative-plasticity-assay.md).
No complete production assay CLI, positive learning gate or formal qualification
is established. Preserve genuine negative/inconclusive results.

Current raw-byte model identity after the separate follow-up implementation
(41 packaged source members):

- Model fingerprint: `1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
- This source has no new fullgraph recording or formal qualification. The
  historical recording remains bound to its original sources below.

Historical November8 acquisition-freeze identity (40 packaged source members):

- Model fingerprint: `dc83d0796fd51c46323ee0e96a7bcfc725d34c6d94371971d235d90ed4144db5`.
- Accepted session engine identity: `13eb5c81d3898597224405ae06a62e03359d28588d0b81f5c1a51ead528ae1e7`.
- All 119 acquisition-freeze bindings were checked independently. This local
  observation freeze is not formal research qualification.

Historical November 7 raw-byte identity (39 Python/C++ members):

- Mixed-ending Windows working tree: `804899ab8b828365ffb8065094b84aa3eb78330da85b79dd62465435e2cfb1b4`.
- Exact Git LF blobs: `f55dcd784aa383193e642983d8afc2f505b55a9f82176865985cd98c60233878`.
- Schema: `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.

The Git-blob identity is a byte-layout check, not a new Linux/native run.
The earlier38-member Linux/CRLF identities remain historical CI evidence in the
linked report, not identities of this new source. Diagnostic source pins are
not a formal LF freeze. Any packaged .py/.cpp change
invalidates previous formal qualification/config/confirmation identities;
finish source-bearing work before a future formal freeze. Do not rerun science
for a documentation-only handover change.
