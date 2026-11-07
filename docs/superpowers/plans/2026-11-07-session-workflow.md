# One-command sessions and engine-free inspection

> **For agentic workers:** Use superpowers:subagent-driven-development and test-driven-development. Base4b1826a, existing authorized feature checkout; no new dependencies or worktree.

**Goal:** Deliver two connected product milestones: one-command observation with
ready-to-open outputs, and later engine-free verification/summary of the bundle.

**Architecture:** One thin workflow module composes the existing recorder and
bounded exporters; inspection reuses the same verified semantic derivation.
Existing recording, replay and plan formats, numerical rules and viewer stay.

**Spec:** Existing [continuous-session contract](../specs/2026-11-03-feed-event-session.md)
and [bounded input policy](2026-11-07-bounded-event-intake.md), refined below.
This technical continuation is controller-chosen under user-delegated authority.
Formal assay/C1 and live provider acceptance remain parked.

## Binding product contract

`run-session --playlist PATH --proposal PATH --output-dir NEW_DIRECTORY` produces
fixed members `run/`, `recording.json`, `plan.json`, `receipt.json`.
Require an existing parent and a new target; reject existing paths, symlinks,
junctions, unsafe ancestors and aliases before the engine factory. Reserve the
outer directory exclusively. The existing recorder retains input preparation
and validation ownership: invalid inputs may leave an empty reserved directory,
but must never construct an engine. Do not duplicate media decoding/preparation.

Call record_feed_event_session exactly once with the supplied factory. It owns
one continuous engine, no reset/restore/retry/resume or selection hunt. A deferred
choice is successful completion. Freeze the returned manifest's five SOURCE_FIELDS
immediately, plus actual verification_mode (must be integrity-only). Never index
manifest['verification_mode']: it is derived, not a manifest field.

Use existing export_session_replay and export_session_plan to fixed output paths.
Compare typed data via canonical bytes, not bool/int-permissive dict equality;
both source bindings and replay['plan'] must equal the original bound plan/source.
After exports, independently rederive from the current raw run using exactly
verify_run(limits=session.EXPORT_READ_LIMITS) → session._export_data with normal
EOF. Compare expected canonical replay/plan plus LF to actual bounded disk bytes,
and pin the source to the originally recorded binding before completion.

Receipt `session-bundle/v1` is closed canonical JSON plus LF, <=16KiB:
`{version,status:'complete',source,files:{'recording.json':{size_bytes,sha256},
'plan.json':{size_bytes,sha256}}}`. Source is exactly the existing six export
fields. Hash exact files, preserve original plan/proposal/decision references;
no absolute input paths, provider inference or new scientific authority.
Publish receipt LAST, exclusively/atomically with the existing temp+rename/link
pattern. A parseable consistent receipt is completion bookkeeping, not independent
provider/native-history/scientific attestation or a durable filesystem snapshot.

Any stage failure retains partial output, raises a stage-labelled RunArtifactError
with the bundle/run path for manual diagnosis/recovery, and never retries, deletes,
repairs or replaces output. Preserve the original exception as cause. A sealed
run may be recovered via existing standalone exporters to new paths; do not call
an unsealed/missing run complete. No blanket multi-file atomicity claim.

`inspect-session DIRECTORY` returns the same concise machine-readable summary
without engine construction, external I/O/network or writes. Fixed local members
only: reject symlinks/junctions/unsafe ancestors, require regular member files and
reject pairwise aliases (samefile) before reads. Use bounded cap+1 reads: receipt
16KiB, replay32MiB, plan64KiB, before JSON decode or equality. Reuse _strict_load
and _canonical; no second replay parser, event policy evaluator or verifier.

One shared derivation/inspection helper verifies the raw run with the existing
limits, consumes complete semantic EOF, compares the actual files to expected
canonical exports and their expected closed receipt, and retains the original
binding when called by run-session. Missing/truncated/extra/noncanonical/mismatched
receipt or altered raw/export data fails incomplete/invalid; never silently repair.
Self-consistent rehashed forged exports cannot override genuine raw derivation.
No claim to detect a wholesale replacement by another independently valid bundle.

Summary includes bundle completion, integrity-only mode, plan selected/deferred,
selected ID/title (null on defer), duration/feed ticks, final-window ticks and
motor counts, and fixed output paths. It never invents confidence or neural
meaning. Existing CLI commands remain available. No automatic browser launch.

Current read limits bound JSON/event data/counts; opaque checkpoints are streamed
without byte ceilings. No whole hostile-filesystem, RSS/CPU/deadline guarantee.
Packaged source changes invalidate old formal identities; preserve historical
source-specific evidence and the upstream core/provenance/notice.

## Review focus

Original A source substituted by valid B between stages; canonical typed equality;
receipt-hash-only forgery; incomplete output and repeated execution; bounded files,
aliases and genuine late EOF errors. Neither summary nor a receipt grants native
execution history, scientific qualification or content-specific learning authority.

### Task 1: Both workflow commands and tests (Sol)

**Own:** new src/fly_connectome_sim/experiment/session_workflow.py and
tests/experiment/test_session_workflow.py; narrow cli.py/tests/test_cli.py only.
No other package, parser, recorder, core, schema, viewer or dependency edits.

- [x] Write/run actual RED tests before implementation. Cover one recording/
  factory call, ordered exports and receipt last; left/right/defer exact plans,
  invalid inputs/existing output zero factory calls, no retry/reset/restore.
- [x] Implement thin runner and shared inspector/receipt logic per contract.
- [x] Cover all failing stages/retained partials, receipt corruption/duplicate/
  extra fields, cap+1 reads, paths/aliases, late EOF, recomputed forgery hashes,
  and valid A→B source replacement before finalization. Inspection forbids any
  engine/network/write. At least one genuine tiny-native composition succeeds;
  synthetic selections stay explicitly declared test fixtures.
- [x] Freeze all package/schema/owned test files; run workflow/CLI/session/event
  compatibility once on final source, record skips/warnings. No parallel repeated
  native compatibility runs. Report commands/results, then independent Astra
  source/integrity review and fix/re-review Critical/Important findings.

### Task 2: Practical acceptance and release (controller)

- [x] After source freeze/review, run at most ONE actual fullgraph run-session
  with the existing two local source reels/example: <=10s simulation/240s wall,
  no retry/winner hunt. If unavailable report that limit; do not fabricate success.
- [x] Inspect the resulting bundle through the real CLI engine-free. Recompute
  receipts/source/plan identity; verify raw global clocks/counts and inspect a
  deliberately altered disposable copy fails without writes. Use the actual new
  recording in the existing browser viewer, preserving known output formats.
- [x] Update getting-started/README/handover/TODO and concise acceptance report;
  independent final release/evidence/staged-diff check. No scientific upgrade.

Publication: explicit first-party staging, English commit, named feature push,
fresh remote/clean-state check. Both connected milestones finish before pausing.
