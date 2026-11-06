# Event Proposal Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An offline-first command can explicitly opt into one bounded proposal
request and export strict options for the existing measured event pipeline.

**Architecture:** A focused transport module builds a strict request, decodes
untrusted responses and publishes an ordinary proposal with a local receipt.
The existing simulator, proposal validator, recorder, viewer and plan stay intact.

**Tech Stack:** Python3.12 standard-library HTTPS, existing pytest; no dependency.

**Spec:** [Proposal transport](../specs/2026-11-06-event-proposal-transport.md).

## Global constraints

- Base011f6fa, existing feature checkout; explicit reviewed feature push only.
- No paid request in this implementation session; OPENAI_API_KEY is absent.
- Offline default; live requires explicit model,512..4096 output tokens,
  environment key and --allow-paid-request; fixed endpoint, one POST/no retries.
- Existing brief/option validator and every measurement/plan/schema stay strict.
-64KiB request/proposal,256KiB response,30s socket timeout; sanitized errors.
- New output directory, exclusive files, receipt last; partial directories persist.
- No native rerun, learning claims, secrets/raw responses or generated artifacts in Git.

## Review focus

- Default invocation or invalid input must never read credentials/send a request.
- Provider errors/echoed credentials must never enter files or CLI diagnostics.
- Refusal, reasoning, extra messages/tools, mismatched briefs and bad usage must
  fail closed without inventing a proposal or silently retrying.
- Failed publication/ambiguous network failure must not trigger a paid retry or
  clobber prior outputs; receipt presence is only local completion bookkeeping.
- New proposal must use the unchanged loader/renderer and grant no choice or
  scientific authority; offline fixtures must not be reported as live evidence.

### Task 1: Request, transport, validation and CLI (Sol)

**Own:** create `src/fly_connectome_sim/experiment/event_proposals.py`,
`tests/experiment/test_event_proposals.py`; narrowly modify
`src/fly_connectome_sim/cli.py` and `tests/test_cli.py`. No other source changes.
Controller owns specs/plans/handover/docs and final commit.

**Interfaces:** `prepare_event_proposal(output_dir, *, title, guests,
max_budget_chf, model, max_output_tokens, allow_paid_request=False)->dict`
returns completion receipt; CLI prints its safe summary only.

- [x] Write failing behavior tests for offline no-credential/no-network request,
  strict valid response, preflight/overwrite, bad responses and sanitized errors.
- [x] Run focused RED tests; retain actual output/command under ignored workspace.
- [x] Implement minimal module and CLI according to the exact spec. Use actual
  http.client adapter exercised through a fake connection/response in tests;
  never execute a real POST. Reuse existing strict JSON/option validation.
- [x] Add one-request/no-retry, partial output/receipt ordering and active-key
  echo tests; test actual CLI refuses constructing any native engine.
- [x] Run new tests plus all CLI/event-card/event-choice/session tests once on
  final source. Record exact command/counts/skips and source byte hashes.
- [x] Self-review, report owned changes/test evidence/limitations; no commit yet.
- [x] Independent Astra source/security/authority review, fix/re-review findings.

### Task 2: Offline acceptance, documentation and reviewed publication

**Own:** controller documentation/checks; Sol release reviewer read-only.
Consumes unchanged Task1 public CLI/receipt and successful offline test response.

- [x] Run actual offline CLI to an ignored fresh directory. Inspect request,
  dry-run receipt, absence of proposal/credential/network evidence. Independently
  import/render a declared successful test fixture, without a native engine.
- [x] Verify all source bytes outside new module/CLI unchanged from base, source
  identity computed honestly; viewer/build/dependency/schema unchanged.
- [x] Update README, getting-started, proposal prompt, current handover/TODOs and
  assay status to distinguish implemented transport from missing live API proof.
- [x] Independent bounded release/evidence review; correct findings and inspect
  the complete explicit staged diff and size.

Publication procedure: commit per AGENTS, push the named feature, verify tracking
and clean state, then pause with the remaining live API gate. Actual publication
is established by the Git commit and remote receipt, not a prospective checkbox
inside the commit being published.
