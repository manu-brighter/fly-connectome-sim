# Offline proposal transport acceptance —2026-11-06

This product slice adds `prepare-event-proposal` independently of the simulator.
The default creates an inspectable offline request. An explicitly configured
model/output-token limit, environment API key and paid-request flag enable one
fixed-endpoint OpenAI Responses POST. No live request was executed in this work;
`OPENAI_API_KEY` was absent. API access, actual model compatibility, pricing and
real response behavior remain unverified. There is no learned/semantic result.

## Source and authority

Base feature commit `011f6fa`; new exact local Windows source identity:
`093081c36bbb64dbb36099e5281407075767e6083244abaf7800631a30ae588b`,
37 Python/C++ members. This hashes working-copy bytes, not a portable LF checkout
or formal source freeze. Old qualification/config/confirmation identities are
invalidated; existing measurements/video evidence remains historical on its own
source. No new fullgraph observation was run for a transport-only change;
existing compatibility tests may exercise their tiny-native fixtures.

Of54 controller-baselined package/schema/viewer/dependency files, only
`src/fly_connectome_sim/cli.py` changed; `experiment/event_proposals.py` is the
single new packaged module. Existing option validator/renderer, engine/native
model, adapter, recorder, schema, viewer and dependencies are byte-identical.
The generated file still enters observation as `imported-json`; a receipt has
no independent provider, native-history or scientific attestation authority.
Selection and bound plan cannot be overridden by a language model.

## Test and review evidence

Test-first missing-function/CLI RED:78 failed/2 passed/20 deselected in2.73s,
then80 passed/20 deselected in0.68s. Earlier test setup exceeded Windows' variable
length with an oversized parameter ID; explicit IDs corrected that harness error.
Additional genuine RED regressions exposed escaped credential publication;
recursive decoded/inner-proposal and final publication checks corrected it.
Focused corrected boundary cases:10 passed/76 deselected in0.29s.

The final frozen compatibility command was:

```powershell
.venv/Scripts/python.exe -m pytest tests/experiment/test_event_proposals.py tests/test_cli.py tests/experiment/test_event_cards.py tests/experiment/test_event_choice.py tests/experiment/test_feed_event_session.py -q -p no:cacheprovider --basetemp=.tools/proposal-transport/pytest-final-1
```

Result: **251 passed,1 skipped in108.54s**, exit0. The single skip was actual
Windows junction creation denied in the sandbox. That exact case was exercised
separately with normal-host approval: **1 passed,86 deselected in0.21s**, exit0.
The initial denied setup was a failed test, subsequently given an honest
permission-specific skip; it was never counted as a junction pass. Existing
event/session tests genuinely exercise tiny-native engines; the new transport
and CLI preparation construct none. This is scoped compatibility, not the full
assay suite, live API acceptance or a new fullgraph observation.

All44 frozen package/schema/owned-test path hashes matched before and after the
compatibility suite. A later test-only double-escaped inner-JSON regression
passed, and isolated in-memory omission of that guard produced the intended
failure (1 failed/87 deselected in0.86s), without changing source files. The new
module then passed **87 tests,1 identical junction skip in0.77s**; this overlaps
the compatibility run and is not additive. Only that test file differs between
the44-path original/v2 inventories; every v2 hash matches the final working bytes.

Boundary coverage includes refusal/incomplete/tool/multiple
messages/text, wrong brief/constraints, token usage, byte caps, no retries,
secret/error redaction, overwrite/collision, partial writes and offline no-key/
no-network behavior. Full logs and source inventory remain ignored local evidence.

Independent Astra architecture review accepted the design. Independent Astra
diff-scoped security/source/runtime review then closed with **0 Critical,
0 Important,0 Minor** findings; it read the actual source, final logs and nested
regression. The reviewer executed no API/native/tests and did not claim live
compatibility; the controller separately recomputed all44 final path hashes.
A separate Sol release/evidence review also returned0 Critical/Important/Minor
findings after independently reconstructing source and receipt hashes and checking
the complete first-party delta and111 relative documentation links.

## Controller-owned offline checks

Actual command, exit0, fresh ignored output directory:

```powershell
.venv/Scripts/python.exe -B -m fly_connectome_sim.cli prepare-event-proposal --title "Summer team party" --guests 100 --max-budget-chf 5000 --model explicit-offline-model --max-output-tokens 2048 --output-dir .tools/proposal-transport/actual-cli-preview
```

The placeholder model is not an actual provider availability claim. The output
contained only `request.json` and a `dry-run` receipt, with no proposal. Exact
request SHA256:
`5d5515b752be5adb7bee0bc26a217cdf5d7f3a8c7e84d742d7fccad35023ca51`.

A separately declared offline HTTPS fixture replaced only the connection seam
and supplied the authored example as a completed response, with inert reasoning
and one assistant message. Actual adapter/builder/decoder/validator/filesystem
code executed; one fake POST and both resource closures were asserted. Local
input/output/total fixture usage was120/250/370, not real API billing evidence.
The602-byte canonical proposal SHA256 was
`87a77b4179aa40d4f5a73170a9bc68f2748335922e533c8103d139c51b297173`.
It equalled the example structurally, loaded through the original source-aware
loader and rendered the original216x384 uint8 RGB cards. Request/response/proposal
hashes independently matched the local receipt; the fake credential appeared in
no published output. This fixture does not establish live compatibility.

Controller script and JSON evidence are ignored under
`.tools/proposal-transport/`; a fresh checkout must produce its own evidence.
No API key, raw provider response, recordings or generated files are committed.

## Limits and failure semantics

The command imposes64KiB request/proposal and256KiB response bounds, a30s socket
timeout,512..4096 output tokens, a fixed verified-TLS endpoint and no redirects,
proxy routing, tools, repair calls or retries. Socket timeout is not a total
process deadline; token limits are not a CHF/USD budget. Failure after submission
can still incur cost. An absent receipt does not prove no request was sent.

New-directory/exclusive-file publication writes request before submission,
then validated proposal and receipt last. Failure retains partial output; only
a complete valid receipt with matching request/proposal hashes marks completion.
Receipt path presence alone is insufficient, including a truncated write.
The existing strict validator rejects extra keys, changed briefs, invalid
constraints, programme schedules and any attempted selection authority. Raw and
decoded secret echoes are rejected before publishing a proposal, and provider/
transport/parser/publication failures use fixed sanitized diagnostics.

Formal assay/C1, longer feeds, old-state resumption, foreign raw-run allocation
bounds and broader viewer/accessibility work remain separately open. Actual API
acceptance needs explicit local credentials/model/cost configuration; optional
post-choice narrative is a separate future slice.
