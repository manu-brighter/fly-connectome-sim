# Fixed-choice event follow-up — November 8, 2026

## Result

The user-selected feedback step is complete. One real Responses call consumed
the accepted session's brief and selected option and produced a separate German
planning companion. The complete original plan, all four programme entries and
all seven historical source files remained unchanged. No new fullgraph session,
provider retry, venue lookup or booking was performed.

Local output: `runs/event-followup-live-20261108/event-plan.md` and
`followup.json`, with `request.json` and a final `receipt.json`. The supplement
has an overview, three preparation suggestions and three open questions.
It discusses guest/seating organization, catering/music/weather coordination,
communication, accessibility, guest scope and catering preferences. These are
nonbinding planning suggestions, not verified availability, prices or a neural
explanation of the choice. The original estimate remains CHF4200 for100guests
within the CHF5000 brief, duration240minutes, Sunset Rooftop Social.

Astra independently inspected the actual German text, complete original-plan
equality, source files, request, output hashes and receipt. Source/protocol and
focused security reviews passed after the Windows namespace-alias correction.

## Actual request and bounds

The offline preview at `runs/event-followup-preview-20261108/` contained only
request and dry-run receipt. Its user input is exactly `brief` and
`selected_option`: no unselected option, neural counts, recording, source
identifiers, paths or credentials. The live request was byte-identical.

- Model requested/returned: `gpt-5.4-mini-2026-03-17`.
- One POST; output cap1024tokens,30s socket timeout,120s outer deadline.
- Actual usage:308input +228output =536tokens;15.562s elapsed, exit0, no stderr.
- Nominal text cost:USD0.001257 using the checked
  [published rates](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
  of USD0.75/M input and USD4.50/M output. Actual billing was not inspected.
  A token limit is not a monetary limit.
- The supervisor directly launches the verified real Python executable, avoiding
  the Windows venv launcher. A non-neural timeout smoke confirmed identical
  launched/executing PID and successful termination/reaping; Astra reviewed it.

| Local file | Bytes | SHA256 |
| --- | ---: | --- |
| request.json | 1622 | `66a36b9a893755633ca848be6d87f7b8806f40b69d966c7dda7f12498434063d` |
| followup.json | 2508 | `00cdcd1cda075e7569c5152a5dc4109c3f62fc83e2ae13fc195dfc65e4239fa8` |
| event-plan.md | 1614 | `cae0096b487e8af80d0c67f580df70a62999f957e24c03b6ad7aee5a0decae2e` |
| receipt.json | 1046 | `690a139631aa65d3e091eabde4c581f1f7002bc5c4900bf99b40d21d21327657` |

Raw-response hash recorded by the transport:
`7e117fbf59c2bc05b9acc4cf6324cee62e815d0db852d75f64e388756d8b6bc2`.
The raw response and key were not persisted. Receipts establish local consistency,
not provider authentication or scientific validity. Private artifacts/evidence
remain ignored under `runs/` and `.tools/event-followup-20261108/`.

## Verification and limitations

Test-first evidence includes initial missing-feature failures, actual URL-filter
failures and a reproduced Windows extended-path overlap. The final overlap guard
uses existing ancestor directory identities as well as path/reparse checks;
both extended-prefix and actual8.3 alias regressions passed.

The combined follow-up/proposal/session/CLI regression passed223tests with11
Windows permission skips in46.65s. After the narrow alias fix, the final
follow-up/proposal/CLI run passed188 with7permission skips in18.35s:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/experiment/test_event_followup.py tests/experiment/test_event_proposals.py tests/test_cli.py -q -p no:cacheprovider --basetemp .tools/event-followup-20261108/sol-alias-green
```

Host follow-up/proposal tests passed159 with4symlink-privilege skips; a pytest
cache-write warning did not affect results. The host then passed all four
workflow hardlink/junction cases, six disjoint-output/junction cases and both
namespace cases. Symlink creation remained unavailable on this Windows host;
the updated clean-checkout CI includes the new suite and existing proposal
suite for Linux coverage. Three tests that consume the accepted historical
bundle ran locally; they explicitly skip when that private bundle is absent.
Mandatory declared-source tests and ordinary workflow tests remain data-free.

Code, protocol and final artifact reviews were independent of implementation.
Schema validation cannot prove the prose factually correct; actual text was
read separately. No browser/UI or film change was part of this continuation.

## Source identity

Current Windows raw-byte package identity,41Python/C++members:
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
This includes the new companion module and shared decoder/CLI changes.
The existing [accepted demo](2026-11-08-cell-capture-api.md) retains its historical
40-member identity and engine identity; this command does not requalify it or
establish formal research qualification. Sources and package bytes were identical
before/after the live request. See the [contract](../superpowers/specs/2026-11-08-event-followup.md)
and [usage](../getting-started.md#optional-follow-up-to-a-fixed-event-choice).
