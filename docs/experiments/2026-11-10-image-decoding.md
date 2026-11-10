# Isolated image decoding — component evidence

Status: Task1 worker implemented, tested and independently accepted after its fix.
Task2 parent ownership/cleanup is not implemented. This is not a usable upload
service, complete decoder controller or evidence of process containment.

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
narrow PNG correction, the entire affected worker suite was rerun; full Market
integration is due again with Task2. Two trusted CLI tests are Windows-only due
to the fixed repository venv bootstrap; portable pixel/wire tests are separate.
No source CI or Linux decoder test result is claimed yet.

All305 preexisting tracked files remain unchanged except five independently
accepted D1 completion documents. All64 frozen helpers,41 package members and
seven historical artifacts retain their original identities. No dependency,
D1 lifecycle, price authority, old readout or replay format changed.

## Remaining boundary

Task2 must establish creation-time process ownership, original acceptance-based
deadline enforcement, bounded pipe monitoring and confirmed cleanup. Ordinary
trusted CLI subprocess tests prove only startup/byte protocol. They do not prove
parent-death handling, memory supervision, public image safety, moderation, native
handoff or event capacity. HTTP intake, native integration and live presentation
remain later work.
