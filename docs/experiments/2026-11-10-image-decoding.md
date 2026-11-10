# Isolated image decoding — component evidence

Status: both tasks implemented and independently accepted locally after their
corrections. Final local Market suite:540 passed/five Windows privilege skips.
Source publication and clean-checkout CI remain pending. This is a local decoder
component, not a usable upload service or an OS security sandbox.

The private worker consumes only bounded request metadata and image bytes,
rechecks source identity, and returns one bounded result. Its fixed
market-rgb64/v1 policy converts accepted JPEG/PNG inputs into12288 canonical
RGB bytes: EXIF-only orientation, black alpha composition, fixed aspect sizing,
bilinear resampling and centered black padding. The frame hash matches the
declared rgb-input/v1 prefix without loading the simulator.

## Task1 checks

Commands used `.venv/Scripts/python.exe -m pytest`, a fresh task-local
`--basetemp` and `-p no:cacheprovider`. Fixtures were generated locally from known
pixels and file chunks, not user photos.

| Check | Actual result |
| --- | --- |
| Initial behavioral tests against empty worker scaffold | 102 failed, two passed, three skipped |
| Initial complete worker suite | 116 passed, three skipped, 0.92s |
| Initial complete Market suite under Windows host execution | 431 passed, four skipped, 34.66s |
| Duplicate-header regression before correction | Two failed, two valid controls passed, no skips |
| Corrected duplicate-header regression | Four passed, no skips |
| Corrected complete worker suite | 120 passed, three skipped, 0.99s |

Independent review found that a second PNG IHDR could select a16-bit RGB/RGBA
raster while the first-header check saw8-bit. The correction also checks the
effective pinned-Pillow PNG decoder/rawmode before verification and again after
reopening. The forbidden sources now emit a bounded rejection without RGB; valid
8-bit controls retain their exact pixels. No general PNG text parser or relaxed
source-depth policy was added. Independent re-review accepted Task1 after15
additional checks passed without skips, including both original bypasses and
every valid PNG mode/depth pair.

The focused skips are three genuine Windows symlink-privilege failures
(WinError1314); the full Market suite adds one existing HTTP symlink skip. The
initial restricted-sandbox full run had378 passes, four skips, five failures and
48 setup errors from existing asset-path/startup access restrictions. The host
rerun used unchanged assertions. All attempts remain in private local logs under
`.tools/image-decoding-20261110/`.

The431-pass full-suite result belongs to the initial worker revision. After the
narrow PNG correction, the entire affected worker suite was rerun; the subsequent
Task2 full Market result below includes this correction. Two trusted CLI tests are
Windows-only due to the fixed repository venv bootstrap; portable pixel/wire tests are separate.
No source CI or Linux decoder test result is claimed yet.

At the initial Task1 review, all305 preexisting tracked files were unchanged
except five independently accepted D1 completion documents. All64 frozen helpers,
41 package members and seven historical artifacts retain their identities. No dependency,
D1 lifecycle, price authority, old readout or replay format changed.

## Task2 ownership and complete local integration

The parent reuses unchanged ownership and Windows Job primitives. A suspended
child is bound to the kill-on-close Job at creation, with an exact inherited-handle
allowlist and direct membership verification. The fixed interpreter starts with
`-I -S -B`, a minimal environment and detached/hidden creation. Bounded polling
enforces the original acceptance-based deadline, output limits and sampled memory
limit. Success requires exact frame identity and confirmed cleanup. Failed cleanup
retains exact ownership for retry; there is no PID discovery or unsafe fallback.

Independent full-source review found two terminal-path defects: an exception from
the final cancellation read could retain busy state or mask cleanup failure, and
a failed child could bypass buffered protocol validation before EOF. The corrections
preserve cleanup precedence, always release busy state and drain bounded output
through EOF while retaining all clock/cancellation/resource checks.

| Check | Actual result |
| --- | --- |
| Final-path regression before correction | Five failed, one passed, two stuck-busy teardown errors |
| Corrected final-path regression | Six passed, no skips |
| Corrected complete decoder suite | 225 passed, four skipped,4.51s |
| Corrected complete Market suite | 540 passed, five skipped,38.55s |
| Independent correction and neighboring-boundary checks | 16 passed, no skips,2.94s |

Actual final commands:

```powershell
.venv/Scripts/python.exe -m pytest tests/market/test_image_decode.py tests/market/test_image_decode_windows.py tests/market/test_image_decode_worker.py --basetemp=.tools/image-decoding-20261110/pytest-task2-fix1-focused -p no:cacheprovider
.venv/Scripts/python.exe -m pytest tests/market --basetemp=.tools/image-decoding-20261110/pytest-task2-fix1-market -p no:cacheprovider
```

All14 Windows checks passed in both final suites:13 fixture checks plus one adapter-
availability check. The fixture checks cover normal
decode, flood/crash, cancellation/deadline, parent death before and after resume,
creation-time membership, held process identity, unrelated sentinel survival,
environment/handle exclusion, bytecode suppression, cleanup retry and junction
refusal. Only artificial secret markers were used. The four decoder and fifth
existing HTTP symlink skips are actual WinError1314 privilege failures.

The final generated PNG success observed24,252,416 peak child bytes and12288 exact
RGB bytes; scratch was removed. This is one harmless fixture measurement, not a
worst-case image budget. Memory-threshold and scheduling-gap tests use synthetic
boundaries; sampled supervision is not a hard OS quota or real-time guarantee.
Independent review accepted complete local D2 source/integration after inspecting
these actual logs and running the16 additional controls. Frozen64 helpers,41
package members and seven historical artifacts remain unchanged.

## Remaining boundary

Clean-checkout CI remains required. Windows process evidence and portable pixel/
protocol tests are separate; no Linux process containment is claimed. There is no
HTTP intake, moderation, native handoff, secure erasure, event-capacity or public-
operation evidence. Upload/preview/approval is the next separately reviewed slice.
