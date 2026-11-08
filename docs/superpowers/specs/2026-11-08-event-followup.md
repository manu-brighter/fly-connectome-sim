# Bounded event follow-up

## Accepted scope

The user selected the LLM feedback/event-plan continuation after accepting the
observation demo. Add one separate German planning companion to an existing
completed session. The original selected option, budget, programme, measurement
and source recording remain unchanged. No new simulation, selection, learning,
viewer feature, venue lookup or booking. Astra reviewed this boundary before
implementation; technical execution and one bounded live acceptance are authorized.

## Input and authority

`prepare-event-followup --session-dir SESSION --output-dir NEW_DIRECTORY
--model MODEL --max-output-tokens INTEGER [--allow-paid-request]`

Consume only a canonical completed session accepted by the existing workflow
inspector. Bind the exact bounded plan/recording bytes to the inspector's derived
receipt hashes and sizes; do not accept alternate filenames. Recheck the same
receipt and file identity before POST and before publication of completion.
Reject symlinks/junctions and output paths overlapping the source directory;
reserve a fresh directory with exclusive writes. Do not change the source.

Only the checked brief and selected option enter the provider's user input.
Treat all their strings as untrusted data. Do not send raw neural counts,
recordings, the unselected option, paths, receipts or source identifiers.
No model field can replace the original plan. No inferred fly preferences,
neural explanation, semantic understanding or biological learning claim.

On `defer`, write a local `no-selection` receipt without reading credentials,
building a provider request or making a network call. Do not invent a winner.

## Request and response

Default mode is offline: request plus `dry-run` receipt only. Live mode requires
the environment key, explicit model and 512..4096 output-token limit. Reuse the
existing fixed-endpoint Responses transport and envelope/secret validation:
one POST, no retries/repair calls, no tools, 64 KiB request, 256 KiB response,
30 s socket timeout, sanitized errors and no persisted raw response or key.
Keep the existing event-proposal interface and behavior compatible.

Use `store:false`, `stream:false`, strict closed JSON schema. The only response
fields are `overview` (1..600 characters), `preparation` (1..4 strings, each
1..240 characters), `open_questions` (0..4 strings, each 1..240 characters).
Accept printable German Unicode; reject control/format characters, surrogate
codepoints, URLs and oversized/extra/missing fields. Supplement limit:16 KiB.
Render Markdown with escaped data, not provider-supplied Markdown/HTML.
The prompt asks for concise German proposals/questions, never confirmed venue,
availability, price, booking or new measurement claims. Structural validation
does not establish factual truth; inspect the live text separately.

## Output and completion

`followup.json` contains a version, the full unchanged original plan, the
supplement and exact source receipt/plan/recording hashes. `event-plan.md` renders
the original brief and every selected-option/programme field deterministically,
followed by a clearly separate nonbinding supplement and open questions.
Original budget/capacity remain proposal estimates; no confirmed offer.

Write `request.json` before POST. Publish a bounded receipt LAST, containing
status, source hashes, provider/endpoint, requested model/token limit, request
hash, returned response/model identifiers, raw response hash, token usage and
hash/size bindings for final JSON/Markdown. A valid receipt with matching files
means local completion, not provider authenticity or scientific evidence.
Failed/partial attempts persist and never trigger a retry. Recheck sources
after the response and before receipt publication; changes reject completion.

## Acceptance and history

Offline/fake-transport tests first; independent source/integrity review before
one real acceptance call. Use the accepted session under
`runs/cell-demo-20261108-02/session`, `gpt-5.4-mini-2026-03-17`, at most1024 output
tokens, fresh sibling output and an outer120 s process deadline. No retry or
native rerun. Token cap is not a monetary cap. Inspect the actual German text,
usage, hashes and unchanged original plan. Artifacts and secrets stay ignored.
Packaged Python edits change the current code identity; the existing demo
retains its historical source identity and is not requalified by this work.

Responses contract checked against the [official structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs)
on November8: closed objects and explicit incomplete/refusal handling.
