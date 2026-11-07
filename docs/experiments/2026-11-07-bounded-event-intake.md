# Bounded event export intake —2026-11-07

From base `25f82b7`, the four event/session replay/plan exports opt into immutable
RunReadLimits on the existing verifier. Generic verification, recording, prefixes
and unrelated exporters keep their prior defaults. No second verifier, native
equation, schema, viewer, dependency, selection or plan change was introduced.

Current local Windows37-member Python/C++ identity:
`cad0926bd37e23aa9ab978be9ca28a8d784a97ab874b9dbe033caefc145548d6`.
Only recorder.py, event_choice.py and feed_event_session.py differ among the42
controller-baselined packaged source/JSON files. This is a working-copy byte
identity, not a portable LF freeze. New packaged source invalidates earlier formal
qualification/config/confirmation identities. No formal assay or new fullgraph
observation was run, and no scientific/native-history support follows.

## Operational policy

| Input | Standalone choice | Continuous session |
| --- | ---: | ---: |
| Manifest bytes | 2MiB | 2MiB |
| JSONL line, including LF | 1MiB | 1MiB |
| JSONL total bytes | 8MiB | 64MiB |
| Declared/actual events | 6 | 246 |
| Declared/actual checkpoint entries | 2 | 2 |

Bounded reads reject overflow before JSON decode and persist through all scan,
iterator and final recheck paths. Exact caps still require genuine normal EOF;
chain/schema/digest/checkpoint/semantic checks are preserved. Final event hashing
also has the byte ceiling. Directory entries use context-managed os.scandir:
Python3.12 Path.iterdir first allocates os.listdir's whole result, so merely
capping that loop would not suffice. Checkpoint contents remain opaque1MiB
hash chunks and are never decompressed by ordinary export verification.

These are operational ceilings, not a universal proof of serialized engine size
or a process RSS/CPU deadline. An over-cap artifact can still use generic
verify-run as a controlled local workflow; exports never silently fall back to
unlimited intake. Complete hostile-filesystem, arbitrary checkpoint-size and
decompressed-array guarantees remain outside this slice.

## Tests and source review

Python3.12, existing locked environment. Focused RED before implementation:
56 failed in1.56s from missing policy/API. Final focused limit coverage:
67 passed in2.47s. An intermediate event/session/limit compatibility run passed
200 tests in133.05s; it overlapped the later suite on separate temporary paths.
These counts overlap and are not additive. No interrupted run is counted as pass.

Frozen final command, from repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests/experiment/test_recorder.py tests/experiment/test_recorder_limits.py tests/experiment/test_replay.py tests/experiment/test_recorder_projection.py tests/experiment/test_event_choice.py tests/experiment/test_feed_event_session.py tests/test_cli.py -q -rs -p no:cacheprovider --basetemp=.tools/run-intake/pytest-final
```

Result: **883 passed,2 skipped in213.85s**, exit0. The sandbox denied actual
Windows junction creation in test_recorder.py:1209; that exact test passed
separately on the normal host: **1 passed in0.07s**, exit0. The other skip was
the existing opt-in full MaleCNS native map-context test, which was not run.
Existing genuine tiny-native fixtures were exercised; this is scoped affected
compatibility, not a whole-suite, fullgraph or formal qualification result.

Tests cover exact/one-over LF-inclusive byte/count limits, pre-decode bounded
read spies, false-stat/growth, actual EOF, final digest/manifest rechecks, retained
iterator/attestation policies, context-managed scandir caps/closure and default
unlimited behavior. All4 exports reject each limit dimension before publishing;
existing corruption, semantic/DAN, EOF and native-proof tests remain intact.

The41-file package/schema/owned-test inventories matched before and after tests;
the controller independently rehashed all41 current files as well. The41 files
comprise37 packaged Python/C++, the run schema and3 owned test files. Logs and
inventories are ignored local evidence, not independently hosted raw artifacts.

Independent Astra source/runtime review closed with0 Critical/Important/Minor
findings after reading the actual source, tests, logs, inventories and four CLI
comparison receipts. It also compared each actual before/after export file pair.
A separate Sol release/evidence review independently checked all41 raw hashes,
all42 baseline package paths, model identity, output hashes and documentation
links with the same0/0/0 outcome. Neither reviewer repeated tests, native execution
or provider calls; these remain bounded integrity/compatibility reviews.

## Same-artifact compatibility

Before code changes, the controller exported all4 outputs from the two existing
actual raw runs to fresh ignored files. After the final source freeze, actual
CLI re-exports exited0 and each output was compared byte-for-byte with that
pre-change baseline. No simulator or provider request was made by these checks.

| Export | Bytes | SHA256 |
| --- | ---: | --- |
| Standalone replay | 728429 | `ba5cb97c3d8068413dafc2869e463de1302207175b6d9a451c605f8a7bc709e4` |
| Standalone plan | 1075 | `4475f6ccc0f513e4b88b91e0ccd02d6b55202fbd7a4deeae469d8a8c3046224b` |
| Session replay | 13138312 | `d653f948af79980aeb5986109f0bfb301a749514ec396b65f60efd5abeae874d` |
| Session plan | 1077 | `39ea28c12e6b60e6f14b167072382f78c152568ded65ac66aa9859223b3a27a1` |

The standalone/session inputs had366849/427003 manifest bytes,
1490740/20886757 stream bytes and6/216 events. Largest LF-inclusive lines were
372738/372856 bytes. These real files fit the declared ceilings; this sample is
not a mathematical bound on arbitrary engine identities. Their old source-specific
native/visual evidence was not upgraded. Root evidence is ignored under
`.tools/run-intake/`, including baseline.json and controller-acceptance.json;
cloud checkouts must generate their own evidence from available raw inputs.
