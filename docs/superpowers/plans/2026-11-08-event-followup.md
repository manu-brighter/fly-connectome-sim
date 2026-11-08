# Event follow-up implementation plan

**Goal:** Extend the accepted fixed choice with a separate, bounded German
planning companion. **Spec:** [contract](../specs/2026-11-08-event-followup.md).

**Architecture:** Focused `event_followup.py` consumes the canonical inspected
session and reuses existing HTTP/envelope validation. JSON and deterministic
Markdown are companions; the simulator, plan schema and viewer are unchanged.
Python3.12 standard library; no new dependencies.

## Constraints and review focus

- Existing feature branch, base927d411; preserve all unrelated work.
- Sol owns implementation/tests; controller owns docs/evidence; Astra reviews.
- No real API call or new fullgraph acquisition by workers. Existing tiny-native
  fixtures remain part of authorized regressions. One reviewed controller call.
- Test source changes between inspection/POST/publication and unsafe paths.
- Prove defer/default mode never reads keys or contacts the provider.
- Preserve existing proposal behavior, exact one-request failure handling and
  secret suppression, including JSON-escaped echoes and receipt metadata.
- Prove immutable original plan and bounded, escaped UTF-8 supplement rendering.
- Reject incomplete/refused/malformed responses; completion receipt last.

## Task 1: Implementation and offline evidence (Sol)

Own `src/fly_connectome_sim/experiment/event_followup.py`, narrow shared decoder
extraction in `event_proposals.py`, CLI wiring in `cli.py`, new
`tests/experiment/test_event_followup.py` and necessary proposal/CLI tests.
No other source files without coordination. Public interface:
`prepare_event_followup(output_dir, *, session_dir, model, max_output_tokens,
allow_paid_request=False) -> dict` returns the local receipt.

- [x] Write/run failing behavioral tests before implementation; save evidence.
- [x] Implement source binding, shared envelope decoder, request/schema,
  nonbinding companion renderer, exclusive publication and CLI.
- [x] Run focused tests plus proposal/session/CLI regressions; record commands,
  counts/skips and limitations. No fake evidence presented as live acceptance.
- [x] Independent Astra code/integrity review; fix and re-review findings.

## Task 2: Acceptance, docs and publication (controller)

Consumes Task1's real CLI/files; no conflicting source ownership.

- [x] Inspect actual offline request from the historical selected session.
- [x] Run exactly one bounded live call; inspect text/usage/source/output hashes.
- [x] Document CLI usage, actual result, historical/current identity and limits.
- [x] Complete appropriate regression/CI wiring and independent source/artifact
  review. Final documentation review precedes publication.

Publication procedure: inspect the complete explicit staged diff, commit and
push the named feature, then observe CI. Git/CI receipts establish actual
publication; no prospective success checkbox, PR, merge or deploy.

Self-review: Tasks1/2 share CLI/artifact contracts only; Task1 produces and
Task2 consumes the same files/statuses. Tests agree with source ownership and
the spec. No new selection or current-source qualification is implied.
