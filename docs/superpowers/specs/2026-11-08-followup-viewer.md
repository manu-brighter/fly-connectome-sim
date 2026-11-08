# Planning companion in measured replay

## Continuation and design

After accepting the fixed-choice feedback command, the user requested further
continuation. The controller's stated next-step assumption is local viewer
integration of that existing companion. No further model request or neural
acquisition is needed. Astra reviewed the design and binding contract.

Add one planning section below the replay/transport and before cell inspection,
outside canvas and telemetry. Keep the existing Bahnschrift/Aptos/Segoe UI type
stack and palette: background #e7eff4, surface #dfeaf2, ink #172b3a, secondary
#597083, rule #bdceda, action #2456d6. Left-aligned text, overview at most75ch,
two preparation/question columns on wide screens and one on narrow screens.
No new masthead button, animation, dependency or redesign. The replay remains
the main visual; the companion provides a readable next step after the choice.

Use existing English interface conventions and German companion content with
`lang="de"`. A section button selects both JSON files in one picker. A persistent
status distinguishes not loaded, loading, loaded but awaiting the decision,
available, and deferred/no selected plan. The revealed content explicitly says
`Unverbindlicher Begleittext`; estimates/availability remain unverified.

## Local import contract

Support only an already validated `feed-event-replay/v1` recording. Accept exactly
two files, assign by `version` rather than name/order: `event-followup/v1` and
`event-followup-receipt/v1`. Reject missing/duplicate/extra files, malformed UTF-8,
duplicate JSON properties, excessive nesting, unsupported/extra fields and
oversized inputs before publication. Bound each pre-read file at128KiB; enforce
follow-up128KiB and receipt16KiB after identification. Snapshot imported bytes.

Reuse existing `strictJson`, `canonical`, hash and plan-equality helpers. Only a
`validated` receipt is accepted. Match exact follow-up raw byte hash AND size;
require matching source hash objects and full original-plan equality with the
recording. Validate supplement text/count bounds from the Python contract,
Unicode/control/format/URL restrictions and provider receipt identifiers/usage.
All text goes through `textContent`/DOM lists, never provider HTML/Markdown.

The recording's first read already supplies exact raw SHA256. Retain its byte
length too; never reread it for attachment. Reconstruct canonical plan bytes as
`canonical(recording.plan) + '\n'`; reconstruct the canonical `session-bundle/v1`
receipt from those plan/recording hashes, sizes and `plan.source`, again with
its producer's trailing newline. Match both source hashes. This verifies local
bindings, not raw-run integrity, native history or provider authenticity.

Render the companion Markdown deterministically with parity to the existing
Python renderer, then check its exact bytes against the receipt's Markdown
hash/size. Download only these checked bytes as `event-plan.md`. Original bound
plan JSON download is unchanged. Do not request a third input file or a key.

## Playback and state

Import may finish before the measured choice. Keep title, overview, preparation,
questions and download unavailable until the CURRENT sampled plan is selected.
At `effective_tick - 1`, on rewind and on defer, remove revealed content and
disable/hide companion download. Do not reveal a winner through status text.
Do not infer visibility just from a recording's terminal stored plan.

Successful recording replacement clears the attachment. Pending attachment work
is cancelled at recording-load start and cannot later attach to another recording,
including during asynchronous hash work. Invalid imports retain a previously
valid attachment with an actionable error. Cancelled/obsolete work cannot clear
newer statuses. Integrate with existing load/export controls: no import during
export, no export while attachment import is pending, no download while busy.
Respect keyboard focus, native picker cancellation and reduced motion.

Canvas, movie rendering, tablet/fly geometry, original plan export and scientific
readouts remain unchanged. Existing Python/C++ sources and source identity stay
unchanged; this is not another acceptance recording.

## Acceptance

Test behavior first: file-order/schema/byte/source/plan/Markdown mismatches,
German Unicode and escaped markup, decision boundary/rewind/defer, load races,
export lock and replacement/error behavior. Run the viewer suite/build once
on final source; narrow fixes get targeted rechecks.

Independently review source, then use the actual accepted recording and existing
live companion/receipt in a real browser. Check desktop and narrow layouts,
pending/final/rewind visibility, safe text, stale-load handling, original plan
and exact Markdown downloads, and absence of application network/API activity
beyond the local development server. Record evidence without modifying the
source artifacts. No new film is required. Review docs, explicit commit/push
and CI complete this bounded continuation.
