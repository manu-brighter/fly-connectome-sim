# Continuous Motor Drive v1

Status: independently accepted prospective engineering contract; implementation and development
replay not yet performed. Preserve all earlier negative candidates and recordings.

## Purpose and interpretation

The user accepts long quiet phases and favorites, provided every configured drink
remains technically selectable. Quiet/recovery between commands was an assumption
of the earlier event detector, not a user requirement. This separate contract lets
fresh sustained supported motor activity advance an engineered selector. It does
not establish repeated biological intentions, image understanding or learning.

Technical reachability means constructive synthetic input sequences can reach
every configured drink. Observed coverage is a separate measurement; a finite
recording need not visit every drink. Never add forced rotation, random choices,
timer-driven proposals or retargeting to manufacture coverage.

## Frozen mapping

- New external `scripts/market_continuous_drive.py`, class `ContinuousMotorDrive`,
  directly subclasses the unchanged `market_motor_readout.MotorReadout` v1.
- Policy version: `continuous-motor-drive/v1`. Configuration policy contains
  `command_mode: continuous-supported-drive`; omit the two unused neutral fields
  `neutral_samples` and `neutral_total_max`. Preserve every other v1 configuration
  value and its validation, canonical hashing and copy isolation. No v2 fields.
- Start ready. Each node consumes four new consecutive 500 ms observations, using
  unchanged v1 direction gates: total at least20, absolute net at least4,
  absolute net/total at least1/5, and at least3 signs supporting the same direction.
  Accepted lower/upper direction advances exactly one node in the unchanged binary
  partition of the ordered10–20 configured IDs.
- The next observation starts the next node's block. Once a leaf is reached, a
  separate four-observation price block uses unchanged v1 price support and exact
  integer grid mapping: total at least20 and at least3 active observations.
  Price may span the entire configured range; there is no per-change jump cap.
- Every completed unsupported or ambiguous block is discarded. It produces no
  direction or proposal. Pending accepted directions survive only within the
  unchanged expiry/history limits. No sliding windows or sample reuse.
- Anchor expiry at the first accepted direction block's start. Preserve60 model
  seconds,300 real seconds and128 history samples, together with v1 boundary
  comparison semantics. A sample causing expiry/reset/drop is discarded and
  cannot start another path. After a proposal, reset to the root; the following
  observation starts a completely new path and later separate price block.
- Preserve all field validation, source/session/clock ordering watermarks,
  input/frame provenance, freshness, pause/resume, reset and reconfiguration. Failed reconfiguration
  retains its old identity and existing v1 evidence/clock failure semantics.
  No rollback of the base clock watermark. No evidence crosses a source/session,
  configuration, pause or invalid-data boundary. Input/frame changes are retained
  exactly in the existing input history; they do not reset a continuous path.
- Constant newly measured supported drive may repeat a favorite and price.
  Wall time alone, repeated old samples, stale inputs, silence and ambiguous
  direction cannot force proposals. Command timing means completion of sufficient
  fresh evidence, subject to an engineering minimum duration.
- A proposal never activates a sale price. The later external service enforces
  at least30 real minutes between actual changes per drink, bounded grid prices,
  no-op rejection and pause. Rejections are discarded: no queue, retarget or
  recycled evidence. Those service behaviors are not implemented by this task.

## Minimal implementation and verification

Override `_clear` to call the frozen base and arm immediately; override `_consume`
to call the base once and rearm only after `direction/direction_supported`.
Use a small identity-binding helper after construction and successful reconfigure.
Do not copy validators, mapping blocks, alter module globals or edit old code.
First consume normally returns `collecting/incomplete_block`; no neutral-ready
or waiting-for-neutral statuses are emitted by this candidate.

Test first using synthetic measurements only: every leaf for each size10–20 and
both configured price endpoints, repeat commands on fresh constant drive,
non-overlapping consecutive evidence, separate price stage, silence/ambiguity,
failed block discard, boundary/expiry triggers, pause/reconfigure and identity.
Exercise malformed, stale, duplicate/out-of-order and source/input transitions
through the new subclass; keep all98 frozen base tests passing. Do not rereun
unrelated large offline suites without a new concern.

## One fixed development replay

After source acceptance, freeze a concrete helper/preflight with source hashes,
candidate configuration/hash and original artifact hashes. Use the complete old
`runs/continuous-motor-20261109-01/` recording, all192 original motor samples and
their unmodified `readout_now_ms` clocks. Start ready at observation0; the first
block is0–3. Never search alignment, reorder, shorten, repeat or rescale the trace.
Verify it with the accepted public probe inspector before consuming its samples.
Use a new exclusive output directory; preserve original files and old helpers.
No native loading, new model run, external process/network/API or training.

Retain all192 input/result rows and complete proposal support, accepted directions,
discarded blocks, reset/stall counters, every configured ID's proposal count,
unique observed targets, repeated target/price counts and final partial state.
Independently review source and actual evidence. A zero-proposal outcome stops
this candidate; no threshold/alignment variants follow this attempt.

Proposals demonstrate development feasibility only, not independent confirmation,
input causation, price activation or Stage C acceptance. A later held-out protocol
must separately test functional proposals and guest-input sensitivity beyond
tonic activity and state history. Sustained neural output alone is insufficient
evidence that uploaded images affect drink or price decisions. Resource and
service gates remain separate. All previous negative results stay valid.
