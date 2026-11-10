# Local image intake — component evidence

Status: Task1 coordinator implemented, tested and independently accepted after
correction review. HTTP/CLI and guest/operator UI are not implemented. No native worker
is connected, and no image has changed a drink price.

The coordinator composes unchanged admission and owned decoding. It retains one
decode task, one canonical pending image and at most512 receipt capabilities.
Complete upload acceptance starts the original10s decode,60s moderation and300s
handoff limits. Approval only queues the image; without a worker it eventually
expires. There is no processed status or renewed deadline in this slice.

Separate image capabilities cannot equal existing price credentials. Public
authentication and finite rate gates precede admission/status access. Clock faults
freeze existing credits and make timing uncertain. Shutdown cancels, joins and
keeps decoder ownership until cleanup is confirmed.

## Task1 checks and corrections

Locally generated inputs only; no user photos, native run or provider request.

| Check | Actual result |
| --- | --- |
| Initial complete affected suite on Windows host |428 passed, four privilege skips,54.30s |
| Clock-boundary regressions before review corrections |18 failed,69 deselected,0.99s |
| Corrected clock-boundary regressions |18 passed,69 deselected,0.17s |
| Complete correction and neighboring-boundary checks |30 passed,69 deselected,0.20s |
| Corrected complete affected suite on Windows host |458 passed, four privilege skips,49.67s |
| Independent correction and neighboring-boundary checks |39 passed, no skips |

The initial independent review found three P2 boundary failures. A final D1 read
could expire an image while the response still advertised its preview; retention
pruning could return the wrong error and spend a reader credit; and a late clock
fault could leave trusted-looking times on a terminal receipt. The correction
reconciles real D1 receipts/snapshots before response construction and guest charging.
At most three target reads cover live→terminal→pruned; an inconsistent view fails
closed. It preserves stopped D1 retention and never manufactures a terminal state.
Independent re-review accepted all three corrections and Task1 after39 real-D1
boundary checks. These include deadline/pruning transitions at successive samples,
frozen diagnostic credits, both automatic transitions in one call and the explicit
three-read bound. Acceptance applies only to this coordinator component.

Self-review also corrected earned-credit retention on clock failure and thread
construction/partial-start failures. Genuine regression failures precede their
corrections. Initial scaffold failures, a fixture-name overflow caused by a large
parameter ID and three Windows sandbox failures remain recorded as unsuccessful
attempts. The unchanged Windows tests subsequently passed with host execution;
no assertion was relaxed.

Final affected command:

```powershell
.venv/Scripts/python.exe -m pytest tests/market/test_image_intake.py tests/market/test_image_admission.py tests/market/test_image_decode.py tests/market/test_image_decode_worker.py tests/market/test_image_decode_windows.py -q -p no:cacheprovider --basetemp=.tools/image-intake-20261110/task1-fix-final-regression-host-20261110-01
```

All99 coordinator cases passed. The four skips are unchanged D2 symlink tests
requiring unavailable Windows privilege1314. Full Market HTTP regression and
source CI remain later integration gates; this result is not that evidence.

An actual generated69-byte1×1 red PNG passed through real D2 into12288 canonical
RGB bytes, preview, approval and confirmed cleanup. The same decoder work root
could then be reopened. A separate injected close-failure test retained the real
root lock until a successful retry. Join-timeout tests use controlled thread
behavior; they do not prove a physical25s OS termination guarantee.

The512-receipt test bypasses only the upload-rate gate through a test-only public
D1 reservation seam. It proves a structural capacity/pruning boundary, not512
simultaneous guests: ordinary1-per10s pacing and900s retention cannot naturally
reach that count. Normal authentication/rate/retention tests use public intake gates.

Private logs and fixture receipts remain under `.tools/image-intake-20261110/`.
The prior D1/D2 and price sources,64 frozen helpers,41 packaged members and seven
historical artifacts remain unchanged. No process containment, public readiness,
event capacity, native measurement or scientific validity follows from these
coordinator tests.

## Remaining integration

The accepted [plan](../superpowers/plans/2026-11-10-image-intake.md) next adds optional
routes to the existing local server, then a guest page and private operator preview.
Actual HTTP, browser and whole-slice review/CI evidence remain outstanding.
Continuous native handoff, measured display and real price admission are later work.
