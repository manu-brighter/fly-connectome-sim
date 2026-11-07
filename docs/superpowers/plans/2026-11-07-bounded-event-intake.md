# Bounded event export intake

> **For agentic workers:** Use superpowers:subagent-driven-development and test-driven-development. Work in the existing authorized feature checkout, base25f82b7; preserve unrelated work and dependencies.

**Goal:** Reject oversized raw event/session inputs before unbounded reads or
decoding, while preserving existing complete integrity verification and exports.

**Architecture:** Optional immutable limits in the existing recorder verifier,
retained by VerifiedRun. Only the two event/session export entry points opt in;
default verification, producers, prefixes, assay and other exporters stay intact.

**Spec:** Existing [session integrity contract](../specs/2026-11-03-feed-event-session.md)
and [event-choice contract](../specs/2026-11-02-event-choice-milestone.md), refined
by the binding read policy below. Astra reviewed this bounded approach before
implementation; it is no formal qualification or native-history attestation.

## Binding read policy

Create frozen `RunReadLimits` in recorder.py with strictly positive integer fields
`max_manifest_bytes`, `max_event_line_bytes`, `max_events_bytes`, `max_events`,
`max_checkpoints`. Reject bool/nonintegers/invalid policy before file I/O.
`verify_run(path, *, limits=None)` preserves existing default behavior. Retain
limits on the returned VerifiedRun for iter_events and attestation accessors;
do not add a separate verifier or reuse a prefix count as a full-stream cutoff.

| Operational ceiling | Event choice | Continuous session |
| --- | ---: | ---: |
| Manifest | 2MiB | 2MiB |
| JSONL line, including LF | 1MiB | 1MiB |
| Total JSONL bytes | 8MiB | 64MiB |
| Actual/declared events | 6 | 246 |
| Declared/actual checkpoint entries | 2 | 2 |

These are conservative operational intake ceilings, not a proof of every
possible engine identity's serialized size. Over-cap exports intentionally fail;
generic verify_run without limits remains available. No CLI override or automatic
retry/fallback to unbounded verification. Production recording is unchanged.

- Every manifest read with limits uses a bounded max+1 read before strict JSON
  decoding, including initial/final and iterator rechecks. Stat may reject early
  but is never the sole guard against growth or replacement.
- Every limited JSONL read is bounded by line+1 and remaining total+1. Count actual
  records independently of the manifest; exact limits still require normal EOF.
  Enforce caps before decoding an overflowing row. Preserve LF/canonical/schema/
  chain/digest/checkpoint/semantic rejection. Never silently truncate the stream.
- Preserve limits through every scan and final event digest recheck. Digest
  reading remains chunked and cannot read an unbounded growing event stream.
  VerifiedRun.iter_events cannot drop the policy on its second verification pass.
- Check declared counts early. With a checkpoint cap, enumerate actual directory
  entries with context-managed os.scandir and stop at cap+1 before constructing
  an arbitrary set. Python3.12 Path.iterdir internally calls os.listdir and
  therefore cannot supply this limited enumeration by itself.
  Existing opaque checkpoint hashing remains1MiB chunks; do not decompress arrays.
- Apply fixed module-level policies only inside event_choice._export and
  feed_event_session._export, covering all four replay/plan APIs. Reject with
  RunArtifactError before creating temporary/final export output.
- No change to native code/equations, schemas, viewer, LLM, prefix/replay proof
  issuance or existing policy/selected plan. Source-bearing edits invalidate old
  formal identities; no learning or new native-history support follows.
- No full hostile-filesystem/service, process RSS, CPU deadline, checkpoint-size
  or decompressed-array guarantee. Do not broaden to unrelated exporters here.

## Review focus

Stat drift/growing streams, exact byte/line/count boundary versus real EOF,
retained second-pass/final-digest limits, manifest/directory inventories, and
no output before complete original validation. Prefix/default compatibility is
load-bearing; a limit rejection must not become evidence of successful verification.

### Task 1: Verifier limits and exporter wiring (Sol)

**Own:** src/fly_connectome_sim/experiment/recorder.py, event_choice.py,
feed_event_session.py; tests/experiment/test_recorder.py (or a focused new
test_recorder_limits.py), test_event_choice.py, test_feed_event_session.py.
No other packaged source, schema, dependencies or viewer edits. Controller owns docs.

- [x] Write/run focused failing tests with tiny caps/read spies (no huge allocation):
  exact/one-over manifest, LF-inclusive line, total bytes, actual/declared counts,
  checkpoint enumeration and invalid policy before I/O. Record actual RED.
- [x] Implement minimal shared bounded reads/digests and retained policy, then
  fixed exporter opt-in. No duplicate verifier or prefix-EOF shortcut.
- [x] Test false stat/growth on manifest/JSONL/final digest, retained iterator
  policy, extra trailing event/missing LF/digest/late manifest/checkpoint rejection,
  all four exports no publication on rejection and default-unlimited compatibility.
- [x] Freeze final package/schema/tests; run affected recorder/replay/projection,
  event/session/CLI tests once. Record actual skips/dependencies and host-only
  checks honestly; existing tiny-native fixtures allowed, no new fullgraph pilot.
- [x] Self-review/report, independent Astra source/runtime integrity review;
  fix and re-review Critical/Important findings. No worker commit/push.

### Task 2: Same-artifact compatibility and publication (controller)

- [x] Re-export both actual historical raw runs after the final source freeze to
  fresh ignored paths; compare all4 outputs byte-for-byte against precoded
  .tools/run-intake/baseline.json. No new simulation or video needed.
- [x] Independently rehash frozen files, update exact source identity, tracked
  handover/current TODO/getting-started and concise acceptance note with limits.
- [x] Complete independent release/staged-diff scope/size checks; preserve all
  scientific boundaries and disclose remaining generic/unrelated intake limits.

Publication: explicit first-party staging, reviewed English commit and named
feature push only; verify actual remote/clean state and pause per AGENTS.
