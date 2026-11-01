# Continuation and cloud handover — 2026-11-01

This is the tracked entry point for continuing from a fresh checkout. Use remote
`origin` of `manu-brighter/fly-connectome-sim`, branch
`feat/connectome-experiment-core`; use its latest pushed commit, not `main`.
No pull request or merge is requested. The repository is still a WIP, not v1.

Work resumed on the original Windows workstation. The cloud setup below remains
available for a future fresh checkout; it is not required to continue locally.
The latest request is continuous autonomous execution, including feature commits
and pushes, without pausing at each checkpoint. No PR/merge is authorized.

## Read first

1. [Repository instructions](../AGENTS.md) and [README](../README.md).
2. [Product scope](specs/fly-event-planner.md).
3. [Approved assay design](superpowers/specs/2026-09-24-associative-plasticity-pivot-design.md).
4. [Current plan and remaining work](superpowers/plans/2026-09-24-associative-plasticity-assay.md).
5. [Replay contract](superpowers/specs/2026-10-02-replay-anchor-contract.md) and
   [candidate-state digest contract](superpowers/specs/2026-10-03-candidate-state-digest-contract.md).
6. [Latest longer-retention report](experiments/2026-11-01-fullgraph-retention-pilot.md)
   and [earlier short-retention report](experiments/2026-10-08-fullgraph-anchor-pilot.md).
7. [Strict qualification integration contract](superpowers/specs/2026-11-01-strict-qualification-contract.md).

The older connectome-experiment-core plan is background, not the next task list.
The private local SDD ledger, scripts, raw results and agent conversations do
not travel through Git. This document and the public plan replace their role in
orienting the next session; they do not replace missing native evidence files.

## Completed foundation

- Official MaleCNS v1.0 input checksums and prepared-array locks; native graph
  166,700 cells, 25,582,938 directed edges, 124,177,617 synaptic contacts.
- Audited MIT-derived Python/C++ core; explicit PAM11/PPL101 stimulation and
  KC/MBON07/MBON11/DNa02 telemetry. Checkpoint restore/reset determinism.
- Independent stimulus/schedule factors, exact neutral-gap execution, pathway
  telemetry, candidate-memory interventions, recorder/integrity/replay contracts
  and strict analysis primitives.
- Optional `LateralMotorAdapter` and recorder-validated
  `engineered_unvalidated_motor_readout`. Decisions use only the measured lateral
  rates, retain legacy v1 readability and cannot change the primary MBON11 report.
  The display threshold is engineered, not behaviorally calibrated.
- Shared schema-only checkpoint reader without a running engine or placeholder
  arrays. It preserves native NPZ/hash formats and legacy writable-destination
  checks, validates bounded headers before array allocation and rejects malformed
  containers consistently. It issues no qualification/native proof.
- Verifier-issued native map/schema context, bound to the exact result owner,
  current source and artifact bytes. Qualification checks one fresh engine even
  without anchors; confirmation/pilot retain their prior zero/one factory policy.
  Engine-free consumers receive independent decoded copies. This authenticates
  maps and existing black replays, not upstream training or scientific support.
- Exact grid occurrence/observation bindings, actual per-role acquisition clocks,
  explicit aligned schedules and incremental failed-route prefixes. Structural
  recorder/schema checks do not authenticate metrics or scientific ownership;
  engine-free reconstruction remains the next task.
- All eight controlled cohorts are produced in one authentic tiny-native pilot:
  40 trainings, 24 interventions, 768 responses, 128 anchors, 67 checkpoints,
  14,048 events. It remains **unsupported with 136 negative gates**; complete
  production is not a positive scientific result or fullgraph qualification.
- Proof-preserving validation performance work shipped in `5aaffb7`.
  Historical Windows complete acceptance: **1,299 passed in 2,646.14 s**, no
  failure/error/skip; the genuine all-factor case took 1,701.331 s.
- Short-source fullgraph components shipped in `ec6474b`. The newer one-anchor
  report measures an actually executed paired training schedule, two independent
  A/B siblings, six sequential fullgraph factories, 92 calls and 59 sealed
  events. Both genuine isolated native replay passes reproduced one retained
  black endpoint. This is resource-only, not learning/configuration approval.
- The 70-second resource sample on `460f5b0` completed six factories, 452 calls,
  179 events and one anchor. Both genuine native replay passes reached the same
  retained state; root independently checked all 460 files, recipe/state/timing
  bindings and canonical three-pass black telemetry. This remains one sample,
  not a whole-assay capacity or scientific qualification certificate.

The 10-second measurement source was `ec6474b3693beb49a9dde28c0e02c3cca9987dad`;
the 70-second source was `460f5b046e4e18df2d147c18ba73899ac660032a`. Both
resource slices change documentation only. The public reports retain exact raw,
source/schema, native, checkpoint, recipe and event bindings. The underlying
raw run is local-only: a cloud session cannot claim to have reverified it unless
those exact bytes are separately made available. On a new compiler/platform,
generate new evidence; do not relabel a Windows identity as a cloud identity.
The later motor-readout changes alter package/schema identities. Reverification
of either historical resource artifact requires its matching source revision.

Final handover-focused Windows check on 2026-10-09: protocol, recorder and replay
tests **502 passed, 1 skipped in 39.08 s**. The skip was a Windows junction test
because junction creation was denied; a pytest cache-write permission warning
also occurred. No complete suite or fullgraph simulation was repeated for this
documentation-only handover. The independent measurement review passed without
Critical, Important or Minor findings; its private report is not cloud evidence.

Fresh Task8 Windows complete opt-in acceptance on 2026-11-01: **1,449 passed in
3,237.62 s**, no failures, errors, skips or deselections. It includes the genuine
all-factor case (2,134.180 s), actual recorder/analyzer roundtrip and both
fullgraph tests. The all-factor report remains unsupported with 136 negative
gates and the same 40/24/768/128/67/14,048 training/intervention/response/anchor/
checkpoint/event counts. No Linux execution or formal qualification is claimed.
Independent scoped Task8 review passed without Critical, Important or Minor
findings. Reviewed file hashes and model/schema identities matched after testing.

The completed Task8 working-source identity is
`3c712e0b6b30dc83e3048db2bab18a12f8918c87b5723a52c17bceb73a88faa9`;
schema SHA256 is
`767dc2bfed78ecc5f6a935b031e257ff44789fb7fb1a005a4bd827a7054ea4f1`.
Later source-bearing integration will change this identity again; it is not a
formal source freeze.

The later Task7B4a reader snapshot passed independent spec/quality review after
two scoped fix rounds. Root ordinary Windows acceptance: **1,556 passed, three
declared opt-in skips in 1,045.08 s**. Both actual fullgraph tests then passed
separately in **10.91 s**, with no skips/errors. The original three skips were
the all-factor case and both graph cases; all-factor acceptance was not repeated
for this codec slice. The Task8 all-factor result above belongs to its earlier
source. Repeat the complete matrix at selected-producer integration/final
source-bearing acceptance before formal qualification.

Reader snapshot model-source identity:
`ad4fae1adfaeb19afaba6d27128e0d623be6f8b33e9377b67ba59401148fa202`.
Schema remains `767dc2bfed78ecc5f6a935b031e257ff44789fb7fb1a005a4bd827a7054ea4f1`.
NumPy remains locked to 2.4.6; its private header parser supports NPY1/2/3.
Structured/subarray extension templates with lossy `dtype.str` are explicitly
rejected. Native array formats, writer and numerical core are unchanged.

Task7B4b's later native context snapshot passed an independent Astra source/
integrity review without Critical, Important or Minor findings. Root actual
MaleCNS tests: **three passed in 24.46 s**, including a genuine zero-anchor
qualification prefix with one verifier factory and both existing graph cases.
The prefix is incomplete, with no scientific terminal, seal or configuration.
Root ordinary Windows suite: **1,627 passed, four declared opt-in skips in
1,155.74 s**, no failures/errors. The skips are the all-factor case and the
three separately passed graph cases. All-factor evidence remains historical;
no new full-matrix or formal qualification result is claimed.

Context snapshot model-source identity:
`62fdc90c0893228c3be4345d83dddaec2ed7eb1f36564e6be2fbbc7b2eecb4ea`.
The schema and checkpoint codec hashes are unchanged from Task7B4a. Actual
grid reconstruction, selected evidence and public freeze integration remain open.

Task7B4c.1's later grid-capture snapshot passed independent spec/quality review
without Critical, Important or Minor findings. Root ordinary Windows acceptance:
**1,693 passed, four declared opt-in skips in 1,119.95 s**, no failures/errors.
The three actual MaleCNS tests passed separately in **18.79 s**, without skips;
ordinary skips are those graph cases and the all-eight matrix. That matrix was
not repeated for this capture slice; its Task8 evidence remains historical.
The ordinary run also passed the compiler and Windows junction tests. The
worker's earlier focused sandbox run had one junction-permission skip, which
does not replace the later host result. Reviewed file bytes matched after tests.

Capture now links actual checkpoint names/hashes/origins/sequences/ticks and all
completed raw calls, including black intervals, across partial failed routes.
All four acquisitions explicitly use aligned control schedules and record their
own association clocks. No grid metric reconstruction, upstream training replay,
successful qualification, production config or capacity approval follows.

Capture snapshot model-source identity:
`ddeae343045809654511dc5f1558739c9e4b09d301be13a2456e62bbadeb8dc0`.
Schema SHA256:
`c56a64f91bf08b2f3c379a4720d4be3a5c2d1743c1c09394d2483f23d61af115`.
Closed future integration roles enumerate 4850 branches, 1602 checkpoints and
8099 relevant events, correcting the unproved 8064 estimate. Operational branch
cap remains 4096; actual selected/replay conformance and capacity are unfinished.

Task7B4c.2a's compact producer arithmetic passed independent Astra numerical/
integrity review without new Critical, Important or Minor findings. The producer
uses shared pure state, response, point and selection functions over compact
measurements; response windows reject gaps, overlaps and reordered bins. Existing
native-valid arithmetic, float32 behavior and earliest-T/tie rules are preserved.
Worker qualification module: **119 passed in 259.59 s**, no skips/errors/failures.
Root qualification/analysis/replay/CLI acceptance: **470 passed, one declared
opt-in skip in 349.63 s**, no errors/failures. The skipped actual fullgraph context
case and the full all-eight matrix were not repeated. Frozen hashes matched.

Arithmetic snapshot model-source identity:
`ce4e59df80c14ec6ee12af94e071aabb6a010bfadc6dc58a63296dcbd776709b`.
Schema is unchanged from c.1. This is still not authenticated grid reduction,
formal qualification, support, a frozen config or capacity approval.

The review separately identified inherited one-spike rounding: for population 3
and 100 ms, exactly one spike can compare below its floor. It is intentionally
preserved by this equivalence refactor and requires the separate fix below.
The reviewed fix design uses actual integer C/replay/washout counts, subtracts
counts before Hz conversion and preserves qualification's inclusive C floor
versus confirmation's strict floor. It introduces no ad hoc tolerance.

## Actual next work

Use these live TODOs together with the plan; do not restart historical completed
RED/GREEN steps because an old procedural checkbox is unchecked.

- [ ] Establish the fresh cloud environment and collect focused tests; record
  compiler/platform identity and missing data explicitly.
- [x] Measure a bounded longer-retention fullgraph one-anchor pilot, including
  both genuine replay passes. One 70-second Windows sample is now recorded.
- [ ] Before formal execution, benchmark the actual integrated grid path with
  diagnostic detail flags and bound complete storage/stream/verification costs.
- [ ] Complete selected qualification control/intervention evidence at T and T+60,
  strict artifact/config integration and the actual `assay --config --output-dir`
  CLI. Current CLI has only `qualify` and `verify-run`; planning text describing
  the future `assay` invocation does not mean it exists.
- [ ] Implement exact bindings for all durable grid snapshots, including
  discarded candidates, and authenticate maps in the real native verifier.
  Preserve the existing grid ancestry; any later storage redesign needs separate
  measurements and review. Black-retention replay does not prove training history.
- [x] Implement and independently review Task 8's labelled motor-only adapter,
  preserve old v1 readability and complete opt-in acceptance.
- [x] Complete Task7B4a's shared schema-only checkpoint reader, independent review,
  ordinary acceptance and separate actual fullgraph tests.
- [x] Complete Task7B4b's verifier-issued map context, object-bound native proof,
  current-source checks, independent review and real-MaleCNS compatibility tests.
- [x] Task7B4c.1: exact grid bindings, declarations, multiple failed-T prefixes,
  closed intended grammar, independent review and ordinary/scoped graph acceptance.
- [x] Task7B4c.2a: compact pure producer arithmetic, independent numerical review
  and targeted qualification/analysis/replay/CLI acceptance.
- [ ] Resolve the inherited one-spike/C-floor and washout-equality rounding
  boundary before the strict consumer/source freeze. Preserve qualification's
  inclusive floor versus confirmation's strict floor; use a reviewed exact
  numerical convention, never an ad hoc tolerance to obtain a positive gate.
- [ ] Task7B4c.2b: implement authenticated bounded two-pass grid reconstruction,
  checking all candidates and available prefixes without inventing missing data.
  Public qualification/freeze integration still belongs to Task7B4f.
- [ ] Finish source-bearing tasks, independently review and run full acceptance;
  only then perform Task 9 source freeze and formal fullgraph qualification.
- [ ] Before that source freeze, pin LF checkout handling for packaged Python/C++
  sources, normalize once and verify the resulting exact source identity.
  The present mixed line endings and local `core.autocrlf` are not a portable lock.
- [ ] If every qualification gate passes, build/review/commit the production
  frozen config before reading held-out confirmation. If gates fail, publish
  an honest negative report, without manufacturing a configuration.
- [ ] Execute and independently verify frozen confirmation/reproducibility.
  Offline 3D replay of genuine measurements and LLM event planning are later
  product phases, not work to begin while the scientific/artifact gates are open.

No production `configs/assay.synthetic.json`, successful formal qualification,
held-out fullgraph confirmation, viewer or LLM planner has been established.

## Fresh Linux/cloud checkout

Local `.venv`, Windows Zig/DLL, graph data, prepared arrays, checkpoints, runs
and `.tools` probes are intentionally absent. Python 3.12, uv, Node.js and a
C++17 compiler exposing `c++` are prerequisites. The Unix build path exists but
has not been exercised by this Windows handover. Do not claim cloud readiness
means a tested Linux simulation or an installed cloud environment.

From the repository root, inspect versions and install locked dependencies:

```sh
git branch --show-current
git status --short
git remote -v
uv --version
node --version
c++ --version
uv python install 3.12.14 --no-bin --cache-dir .tools/uv-cache
uv sync --locked --extra test --cache-dir .tools/uv-cache --python 3.12.14
.venv/bin/python -m pytest tests/experiment/test_protocol.py -q
.venv/bin/python -m pytest tests/experiment/test_recorder.py tests/experiment/test_replay.py -q
```

The first test command exercises stimulus/protocol logic; the second includes
small native fixtures and therefore needs the compiler, not the released graph.
These commands are instructions, not new Linux results. Follow
[Getting started](getting-started.md) for the complete platform-specific setup.
Network/package/compiler permissions depend on the selected cloud environment;
if blocked, report the exact limitation rather than changing locks or skipping
checks under a passing label.

For actual fullgraph work, allow the 1.1 GB download **plus** derived outputs and
runtime/workspace resources. The downloader and data commands are already tracked:

```sh
node scripts/download-connectome.mjs
.venv/bin/python -m fly_connectome_sim.data verify-sources data/malecns-v1.0
.venv/bin/python -m fly_connectome_sim.data stage data/malecns-v1.0
.venv/bin/python -m fly_connectome_sim.neural.connectome malecns_v1
.venv/bin/python -m fly_connectome_sim.neural.prepare
.venv/bin/python -m fly_connectome_sim.data verify-prepared
.venv/bin/python -m pytest -q
```

Staging requires source/runtime on the same filesystem for hard links. Set
`FLY_CONNECTOME_SIM_DATA` before imports if relocating runtime. Ordinary full
pytest already includes downloaded-data checks and native compilation; it is
not a data-free smoke suite. After preparation, complete opt-in acceptance is:

```sh
FLY_CONNECTOME_SIM_FULL_TEST=1 .venv/bin/python -m pytest -q
```

That opt-in includes the costly genuine all-factor case and fullgraph tests.
Do not launch duplicate complete runs or silently treat timeout as success.
Do not run formal `qualify` yet: selected-control evidence/source-freeze gates
are still open. Do not change frozen thresholds based on confirmation outputs.

## Continuation instructions

Work autonomously on the next bounded task, preserve scientific and provenance
gates, use TDD for source changes and independent review before shipping. Prefer
Astra for difficult scientific/integrity reviews and Sol for routine implementation
when those models are available; surface unavailable review capabilities.
Update this handover/plan after a reviewed checkpoint, commit explicit first-party
paths using the repository convention and push only the named feature branch.
Then give a short German status. Do not add raw artifacts to make a handover work.
