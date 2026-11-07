# Session workflow acceptance —2026-11-07

Two connected product milestones from base `4b1826a`: `run-session` records one
continuous session and publishes its existing-format outputs; `inspect-session`
independently checks a completed bundle without running the engine. One focused
workflow module and narrow CLI changes compose the existing recorder, bounded
verifier and semantic reducer. No numerical/selection/parser/schema/viewer or
dependency change was made.

Current local Windows38-member Python/C++ source identity:
`f3ef2ff605432fe549ada0aeb37384f3426df94be23d95049f2a180cc2d4197c`.
Among60 controller-baselined package/schema/viewer/dependency paths only cli.py
changed; session_workflow.py is new. This is a working-copy byte identity, not a
portable LF freeze. Existing formal qualification/config/confirmation identities
are invalidated; C1/formal science and actual provider acceptance remain parked.

## Tests and review

The initial feature RED covered two API/CLI absence assertions (2 failed1.07s).
24 behavior cases were written before implementation but first executed GREEN;
this is an explicit initial TDD evidence limitation. Later observed behavior RED
found an extra unbounded producer-returned verifier pass and unnecessary replay
decode (2 failed4.24s), corrected before freeze. Intermediate test-only misplaced
lines and Windows permission failures were corrected/reported as such. Isolated
in-memory mutations removing source pins or trusting forged hashes each caused
the expected failure (2 failed6.90s); source files were not modified for that check.

Final command used the existing Python3.12 environment:

```powershell
.venv/Scripts/python.exe -m pytest tests/experiment/test_session_workflow.py tests/test_cli.py tests/experiment/test_feed_event_session.py tests/experiment/test_event_choice.py tests/experiment/test_event_cards.py tests/experiment/test_event_proposals.py -q -rs -p no:cacheprovider --basetemp=.tools/session-workflow/pytest-final
```

**315 passed,5 skipped in141.23s**, exit0. Skips were3 hardlink permissions and
2 Windows junction permissions. Those exact cases were separately exercised on
the normal host: **5 passed,124 deselected in2.68s**, exit0. This is scoped
compatibility, not the whole project/assay suite. Genuine tiny-native composition
was exercised; synthetic left/right results are explicitly declared resealed
count fixtures, not native positive outcomes. All74 frozen source/schema/test/
dependency paths matched before/after/current. No new source edits followed.

Independent Astra architecture/source/runtime review closed with0 Critical/
Important/Minor findings. It read actual source/tests/logs/receipts and checked
owned source bindings and plan/receipt hashes. It did not repeat tests/native
execution or independently rehash the large recording/checkpoint corpus; the
controller did the full74-path rehash and actual CLI/audit checks below.
A separate Sol release/evidence review also closed0/0/0 after independently
rehashing all74 frozen paths, reconstructing the38-source identity, checking
all60 baseline paths and actual bundle/input hashes, and reading the216-event
raw stream/global windows. It reviewed the screenshot/documentation without
repeating tests, native computation, browser actions or provider calls.

## One actual fullgraph attempt

Exactly one source-frozen command, no retry or winner hunt, with the existing
two local reels and authored example (no model/provider call):

```powershell
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli run-session --playlist .tools/reels-source/playlist.json --proposal examples/event-options.json --output-dir runs/session-workflow-20261107
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli inspect-session runs/session-workflow-20261107
```

Run-session exited0 in**98.969s**, within240s wall/10s simulation limits. It produced
7s feed then2s cards:216 events/214 observations/1040 bins. Global feed-end70000,
final90000 ticks; final window85000..90000 contained L6/R2 spikes (one cell per
side), delta−8Hz, inspect_left→Sunset House. The original option/brief/programme
was retained exactly. This remains an engineered policy, with no learned or
semantic preference or content-specific causal effect established.

Inspect-session exited0 in**2.391s**, with deliberately unavailable prepared-graph
and compiler paths. Its summary exactly matched the runner. The controller also
checked global raw clocks, every scheduled card interval, final bin counts/
populations/rate/action, unchanged proposal and source/input hashes. Integrity-only
verification does not attest native history or prove learning.

| Output | Bytes | SHA256 |
| --- | ---: | --- |
| recording.json | 13138511 | `b7887d75cc84db3d28ab341f265a78c16336abc9554798149ed7b28c38eb4983` |
| plan.json | 1077 | `824d82356164a315f3acb22b1f414add8074b9d9eda12404e6668c79a51279e1` |
| receipt.json | 702 | `452b2da4ba66ecb77c6d698122b2abb3bdd8b45ebb9474559e8f11f3beab037a` |

A disposable actual bundle copy had its plan/embedded plan altered and receipt
hashes recomputed consistently. The real inspector still exited1 against raw
derivation; all7 copied files remained byte-identical after inspection. It used
no available prepared graph/compiler. A self-consistent forged receipt is no
authority to replace measured selection.

The actual new recording loaded in unchanged Chrome viewer:5× feed at0, pending
cards/no download at70000, Sunset House and L6/R2/−8Hz with download enabled at
90000. Screenshot inspected. No new movie was encoded and no new liveFPS/mobile/
cross-browser certification is claimed. The prior film remains historical.

## Persistence and scope

Receipt is closed local completion bookkeeping, exclusively/atomically published
last. Inspection rederives canonical outputs through full bounded raw EOF and
pins the original source during production. Missing/corrupt/partial output is
not repaired or rerun. Fixed-file reads are capped16KiB/32MiB/64KiB; existing raw
limits apply, while opaque checkpoint bytes remain streamed without total caps.
These checked observations are no atomic/durable filesystem snapshot, hostile-
filesystem safety, RSS/CPU deadline, provider/native-history or scientific proof.

Raw bundle/media and exact local evidence under `.tools/session-workflow/` remain
ignored. A cloud checkout must create its own artifact/evidence from available
locked inputs; the tracked report cannot substitute for absent raw files.
