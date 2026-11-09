# Population excursion candidate — fixed twenty-slot prerequisite screen

Status: prospectively accepted after independent protocol and builder reviews.
No calibration or screen
outcomes have been computed. This is a new engineered candidate, not a revision
of the preserved negative motor decoders or their thresholds.

## Scope and accepted product tradeoff

The user accepts long quiet phases and drink favorites in the experimental pilot,
provided every configured drink remains technically selectable. Do not require
every drink to appear in a finite recording, force rotation, redistribute locked
choices or introduce a mandatory price-update cadence. Technical selectable-output
coverage and observed neural coverage remain separate claims.

First test only necessary signal conditions for one fixed20-slot candidate, using
the accepted [96-second continuous recording](../../experiments/2026-11-09-continuous-motor-probe.md)
as development calibration. This trace and the earlier matched-state diagnostic
cannot later be independent acceptance data. No image-label fitting, feature
search, alternate alignment, online calibration, new model run or provider request.
No full decoder, proposals, price activation, service or live qualification yet.
Failure is not a universal worst-case proof for10–20 drinks: other sector grids
have different boundary placement. It must not trigger an automatic smaller-grid
rescue or channel/threshold substitution.

The controller explicitly chooses the fixed contrasts below as engineering axes.
Their anatomical labels do not establish biological opposition, preference or
semantic understanding. The point is to test this assumption cheaply before
implementing a full lifecycle or acquiring more data.

## Source and exact calibration

Use all192 original500-ms observations, including black intervals. Preserve order,
clocks, ticks, frame identities and original v1 results. There are exactly48 fixed
non-overlapping four-observation blocks:0–3,4–7,...,188–191. No exclusions/sliding.
Seven population counts come from all50 original10-ms native bins per observation,
in order `pam11,ppl101,kc,mbon07,mbon11,motor_left,motor_right`. Memberships come
from the verified engine identity; no individual KC cohort was recorded here.

All memberships must be nonempty, internally unique and stable. Require disjoint
membership within the MBON07/MBON11 pair and within the PAM11/PPL101 pair before
using their summed support. Other cross-population overlap is not a partition
claim; the three support gates are evaluated separately.

For each of the four contrast channels, with count c and population size n:

```text
rate = 2*c/n Hz
offset = median(all192 rates)
MAD = median(abs(rate-offset) for all192 rates)
scale = max((7413/5000)*MAD, 1 Hz, (10/n) Hz)
z = (rate-offset)/scale
x = (z_mbon07-z_mbon11)/2
y = (z_pam11-z_ppl101)/2
```

The median of an even-length sorted list averages its two central elements.
Everything above uses exact rational arithmetic. The scale floors and multiplier
are fixed engineering choices, not fitted confidence bounds. Do not replace zero
MAD, constant channels or outliers with an outcome-dependent rule. Calibration is
frozen once; a constant complete calibration trace produces zero coordinates.
Record memberships/sizes, all calibration values and a digest of all192 raw
population vectors plus membership declarations. No stimulus labels enter math.

## Fixed geometry

There are20 nominal sectors, counterclockwise from the positive x-axis. For sector
k, retain only its central half, bounded nominally by `(4k+1)*pi/40` and
`(4k+3)*pi/40`. The following40 rounded integer rays, in alternating lower/upper
order, define the actual engineering geometry. They are nearest integers to
`10^12*(cos(theta),sin(theta))`, with exact half ties away from zero. Runtime uses
the literal table and no trigonometry. These rounded rays, not ideal real angles,
are authoritative.

```text
(996917333733,78459095728), (972369920398,233445363856),
(923879532511,382683432365), (852640164354,522498564716),
(760405965600,649448048330), (649448048330,760405965600),
(522498564716,852640164354), (382683432365,923879532511),
(233445363856,972369920398), (78459095728,996917333733),
(-78459095728,996917333733), (-233445363856,972369920398),
(-382683432365,923879532511), (-522498564716,852640164354),
(-649448048330,760405965600), (-760405965600,649448048330),
(-852640164354,522498564716), (-923879532511,382683432365),
(-972369920398,233445363856), (-996917333733,78459095728),
(-996917333733,-78459095728), (-972369920398,-233445363856),
(-923879532511,-382683432365), (-852640164354,-522498564716),
(-760405965600,-649448048330), (-649448048330,-760405965600),
(-522498564716,-852640164354), (-382683432365,-923879532511),
(-233445363856,-972369920398), (-78459095728,-996917333733),
(78459095728,-996917333733), (233445363856,-972369920398),
(382683432365,-923879532511), (522498564716,-852640164354),
(649448048330,-760405965600), (760405965600,-649448048330),
(852640164354,-522498564716), (923879532511,-382683432365),
(972369920398,-233445363856), (996917333733,-78459095728)
```

Canonical compact JSON array-of-arrays plus newline has1154 bytes and SHA256
`d0c360a8c9dcdb9bc06ef82bdb119fd95ff8274b1f0487f197e93058713545a1`.
It was generated with100-digit decimal arithmetic before calibration and checked
against standard trigonometry; the smallest half-tie distance exceeds0.176 units.

For exact rational v=(x,y), angular membership requires BOTH
`cross(lower[k],v)>0` and `cross(v,upper[k])>0`. Boundary equality abstains, as does
every gap including the positive x-axis. No vector may match two sectors. Radius
support requires `x*x+y*y >= 4`; exact radius equality passes. A qualifying
observation needs both radius and angular membership; record each condition.

## Block support and necessary confirmation opportunity

For every fixed block, report exact mean(x,y), individual geometry and all gates:

- All four observations qualify geometrically for the same sector.
- KC block count is at least20 and is positive in at least three observations.
- Combined MBON07/11 count is at least20 and positive in at least three observations.
- Combined PAM11/PPL101 count is at least20 and positive in at least three observations.

Retain every failure reason and all raw support counts, including rejected blocks.
The first fully supported block is the potential initial anchor; it emits nothing.
Enumerate ALL later adjacent block pairs (j,j+1), with j greater than the anchor
index, whose two fully supported blocks have the same sector and whose two mean
coordinates each have squared distance at least4 from the anchor mean. Do not
rank/select a favorable pair or change the anchor retrospectively.

No anchor or no such pair means this candidate cannot reach its first confirmation
on this development trace: stop before full implementation or another acquisition.
If pairs exist, label them only `necessary-opportunity-only`. They do not demonstrate
a proposal or warrant Stage C. Price support, pending-state expiry, subsequent
anchors, freshness behavior and continuous product operation remain untested.
Do not reject merely because this screen visits one sector: the user accepts
favorites, and even a same-sector state excursion may satisfy the change rule.

## Evidence, bounds and interfaces

Preserve every old script/package/lock/artifact byte. Load the frozen continuous
probe module explicitly. Use `_read_protocol`, then one private bounded snapshot,
`verify_run`, `_summarize_events(run,protocol,hash,events)` under explicit `closing`,
then a separate closing-protected complete EOF scan of the same VerifiedRun.
This validates original v1 results without replacing them. The new analysis uses
only observed population counts, fixed membership and clocks for provenance.

Require caller-pinned original protocol/manifest/events SHA256:

- protocol `eb4376bc1c8e02a674b71df63a6bc767f52599132e1990398fd66641c18ec1fa`
- manifest `ed2e30e8afe83450cafe613df4d3158e8a256feb16a4c96fcc0faac0d3bd7bc8`
- events `4ea7ddf519fa22ee5158c763a45bd0639226f1235d3540bba11e0205a446395f`

Old limits:2MiB manifest,1MiB event line,64MiB events,194 events, two checkpoints
of at most64MiB each. Exactly192 observations/9600 bins/96000 model-ms. New report
limit4MiB including newline; validate ordinary output parents and use the existing
exclusive writer. Failures/collisions/links produce no successful report.

Version `market-population-excursion-screen/v1`, scope `development-prerequisite-screen`,
verification `integrity-only`. Include exact source/analyzer/helper hashes, original
pins and calibration provenance, all192 coordinate records, all48 blocks, anchor
and complete opportunity list, plus explicit limitations. Raw individual counts
are nonnegative JSON-safe integers; reject bools/fractions. Derived sums use decimal
strings. Fractions use reduced signed decimal numerator and positive denominator
strings; zero is `0/1`. No NaN/infinity, decimal-based decision or scientific pass flag.
