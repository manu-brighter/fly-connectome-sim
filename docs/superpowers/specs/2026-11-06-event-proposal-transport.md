# Opt-in event proposal transport

## Intent and authority

Prepare two event concepts through a separate OpenAI Responses command, then
feed the resulting ordinary `event-options/v1` file to existing event-choice or
continuous-session commands. This implements the user-delegated next product
step. The controller chooses OpenAI first, standard-library HTTPS and an explicit
model rather than a changing default. Imported JSON remains supported.

The model proposes options only. It receives the brief, never neural recordings,
reels, checkpoints or a selected plan. Existing measured left/right/defer choice,
event rendering and immutable plan exports remain unchanged. No narrative or
second round is included. This is no learning or semantic-understanding claim.

## Command and request

`prepare-event-proposal --title TEXT --guests INT --max-budget-chf INT
--model MODEL --max-output-tokens INT --output-dir NEW_DIRECTORY`

Without `--allow-paid-request`, produce only an offline request and a dry-run
receipt. Never read credentials or contact the network in that mode. With that
flag, require `OPENAI_API_KEY` from the environment and send exactly one POST to
`https://api.openai.com/v1/responses`. A new command invocation and a new output
directory are necessary for another attempt. No automatic retries, repair calls,
tools, remote images, configurable endpoints, redirects or proxy routing.

Validate the existing brief ranges/text, model identifier (1-100 ASCII letters,
digits, underscore, dot or hyphen; begins alphanumeric), and an explicit integer
output limit in512..4096 before creating output or doing I/O. Brief title1..48
printable ASCII without URLs, guests10..500, maximum budget100..100000 CHF.
Output-token limits are not a hard monetary budget. Model access, support and
pricing belong to the user's API project; no subscription-coverage claim.

Request uses `store:false`, `stream:false`, `max_output_tokens` and
`text.format={type:json_schema,name:event_options,strict:true,schema:...}`.
Use a closed structural schema with required fields/additionalProperties:false
at every object and explicit enum settings/version. Local existing validation
remains authoritative for numeric/text/cross-field limits and uniqueness.
Prompt specifies illustrative estimates, printable ASCII, exact brief and no
selection authority. No raw free-form prompt override. Request <=64KiB.

Transport uses standard-library `http.client.HTTPSConnection`, default TLS
verification, fixed host/path,30s socket timeout and response read <=256KiB+1.
These are socket/byte bounds, not a guaranteed whole-process deadline or service
availability claim. Close response/connection on every path. Reject all non-200
responses, compressed bodies and redirects without a second request.

## Completion, persistence and errors

Reserve the final NEW directory with exclusive mkdir after all local validation
and, for live mode, credential validation. Parent must exist; never overwrite or
reuse any existing file/directory/link/junction. Write request.json exclusively
before any paid POST. It contains no credentials. Dry run ends with receipt.json
status `dry-run`, no proposal and no response claims.

For live responses: bound bytes before UTF-8 strict/duplicate-key JSON decoding;
require root status completed, nonempty bounded response ID/model and valid
nonnegative integer input/output/total token usage with total=input+output and
output<=requested limit. Permit inert reasoning output items, but require exactly
one completed assistant message with exactly one output_text; reject refusal,
tools, unknown outputs, incomplete/error status and multiple texts/messages.
Output text <=64KiB. Apply validate_event_proposal unchanged and require its brief
equals the exact requested brief. No repair, normalization to rescue invalid
values or retry. Different returned snapshot model is recorded honestly.

Reject the exact active credential in request/response bytes and decoded data,
including decoded proposal strings and allowlisted receipt metadata; JSON
escaping must not bypass the check before any proposal is published.
never persist raw response/body/headers/provider error text. Replace exceptions
from transport, response parsing/validation or publication with fixed sanitized
errors. No stringification of untrusted exceptions in CLI diagnostics.

After successful validation, exclusively publish canonical proposal.json, then
receipt.json LAST. Receipt is a bounded local provenance record: version,
status/provider/endpoint, requested model/output limit, exact request SHA256,
exact proposal-file SHA256, raw response SHA256, allowlisted returned response
ID/model and token usage. No timestamp/identity invention; no secret. A live
receipt means validated response, not provider authentication or scientific proof.
If anything fails or the process crashes, leave the reserved partial directory;
receipt absence or a truncated/invalid receipt means incomplete, even if proposal
exists after a write failure. A file's mere existence is not completion; require
a complete valid receipt and matching request/proposal hashes.
No automatic cleanup/retry or crash-durability/atomic multi-file guarantee.
Existing importer continues to label the proposal `imported-json`.

## Acceptance

Test-first tests intercept only the HTTPS I/O seam; the real request builder,
HTTP adapter, decoder, existing validator and filesystem publication execute.
Check default offline/no env/net, preflight no side effects, limits, exact request,
valid response with reasoning, brief mismatch, invalid options/duplicates,
refusal/incomplete/tool/oversized/non-200/redirect/compression, secret echo and
exception redaction, token usage, one POST/no retry, no overwrite and incomplete
publication. CLI tests must prove it never constructs an engine.

Exercise an actual offline command, import/render its captured valid fixture
through existing loader, and preserve all original packaged source bytes except
new transport and narrow CLI changes. No paid/API/native run without configured
authority; disclose missing key and unverified live compatibility. Source-bearing
changes invalidate old formal model identities; old measurements/videos remain
historical evidence on their own source. No new native pilot is necessary.

## Official API references checked2026-11-06

- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [API authentication](https://developers.openai.com/api/reference/overview)

Local fixtures are declared test responses, never live request evidence.
