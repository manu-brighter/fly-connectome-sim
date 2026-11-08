# Combined local demo import — 2026-11-08

## Result and use

The user selected an easier local demo start after the companion viewer was
completed. **Open demo** now loads the recording, cell activity, source anatomy
and planning companion together. A local Node command prepares the five files
in a new folder; the existing viewer opens them with one multiple-file selection.
Individual imports remain available. See the
[preparation command and usage](../getting-started.md#open-the-complete-saved-demo-together).

The actual prepared folder is `runs/local-demo-20261108/`. It contains exactly
five byte-identical copies, independently compared with the accepted sources:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| recording.json | 13139108 | `c1972dc889fcfbe9e603b0d2790092998d46a9ec0780c52f2eb8d8fc3af379bd` |
| cell-activity.json | 654051 | `7ab327bf915b2d456874cf38d209fbccb9c0b4cf164f546132982fca672253e3` |
| anatomy.json | 417084 | `655d190f9b5f4d9f6bee1568bed29236ca930a4c84a1c1bc682261626e877f9f` |
| followup.json | 2508 | `00cdcd1cda075e7569c5152a5dc4109c3f62fc83e2ae13fc195dfc65e4239fa8` |
| receipt.json | 1046 | `690a139631aa65d3e091eabde4c581f1f7002bc5c4900bf99b40d21d21327657` |

The original recording/cell/anatomy files are from `runs/cell-demo-20261108-02/`;
the companion pair is from `runs/event-followup-live-20261108/`. The folder is
local convenience output, not a new run, receipt format or provenance claim.
No raw events, checkpoints, movie, request or key are copied. No API call,
native acquisition, movie export or dependency change was needed.

## Contract and implementation

All five names and per-role byte limits are checked before any read. The loader
captures metadata/read methods and exact byte snapshots, then composes existing
recording/attachment parsers and cross-binding checks in isolated controllers.
Only a completely valid, still-current candidate replaces the view. Failure
retains the current recording, tick and layers; successful load starts paused
at zero. Choice, rewind and original plan/Markdown export rules are unchanged.

The preparation command opens regular-file handles and actually limits reads
to expected size plus one byte, rejecting growth/truncation. It validates before
creating output, refuses an existing directory or link, and uses exclusive file
creation. Write failure retains an explicitly incomplete folder for inspection.
There is no new file server, archive format, key access or recursive scan/delete.
See the [contract](../superpowers/specs/2026-11-08-local-demo-open.md).

## Actual browser acceptance

- One combined import of the real copied files, in arbitrary order, loads all
  256 recorded cells and 12,000 static anatomy positions. Planning text remains
  empty/hidden at tick zero; tick 90000 reveals the unchanged selected companion.
- A deliberately modified companion is rejected while tick 90000, both brain
  layers, selected text and available downloads remain intact. This altered file
  is synthetic failure evidence, not a new measurement or provider response.
- Rewind to 89999 removes the notes; returning to the end restores them.
  Cancelling the actual file picker preserves the loaded demo.
- An injected delayed read checks pending export/download locks and superseding
  individual recording load. After the old candidate finishes hashing, its
  attachments cannot reappear on the replacement. This is a synthetic timing test.
- The UI Markdown download exactly matches the original 1614 bytes, SHA256
  `cae0096b487e8af80d0c67f580df70a62999f957e24c03b6ad7aee5a0decae2e`.
  Downloaded plan JSON remains deeply equal to the entire original plan.
- Desktop 1280×1000 and mobile 390×844 have no horizontal overflow; the new
  controls wrap within the existing layout. Scientific labels and companion
  qualification remain present. Final console: zero errors, one pre-existing
  Three.js shadow-map warning. Recorded requests only access local Vite resources.

An initial Playwright helper yielded at the native file chooser; the dedicated
file-upload tool completed that selection. Definitive behavioral evidence was
then collected in a fresh page without overlapping chooser helpers. This was
an automation coordination issue, not counted as an application failure/pass.
An initial navigation also retained the known missing-favicon response.

Evidence is ignored under `.tools/local-demo-open-20261108/`: preparation and
artifact audits, browser behavior/layout/race/cancellation JSON, downloads,
desktop/mobile screenshots, console/network logs and preserved tool history.
The owned preview server and browser were closed after acceptance.
The mobile screenshot ends within the preparation list; it does not document
the complete lower companion text. Layout/behavior evidence and the previously
accepted companion remain separate from that capture boundary.

## Tests and source identity

Sol used test-first implementation, including actual failures for missing
features, stale attachment `finally`, mutable file metadata and swapped roles.
After fixes, focused tests passed 19 with one Windows dangling-link permission
skip. Final `npm --prefix viewer test` passed 246 with one skip in 62.305 s;
counts include existing fixture-module test registration. The private historical
Markdown parity test ran four times locally through these imports; when ignored
artifacts are absent, those checks skip. These are local results, not CI counts.
`npm --prefix viewer
run build` passed with the existing large-chunk advisory. Link creation is
unavailable in this Windows environment; that test remains enabled for Linux.

Feature `c7bbbdc99ed39e6e03facd43902e3c71ffc71bce` was pushed to
`origin/feat/connectome-experiment-core`. Its
[clean-checkout CI](https://github.com/manu-brighter/fly-connectome-sim/actions/runs/42525145089)
passed 243 viewer tests with four expected private-artifact parity skips and a
successful build. The dangling-output-link test executed and passed on Linux.
Backend/native compatibility passed 343 tests with eight skips; that automated
tiny-native coverage is separate from the preserved fullgraph observation.

Astra independently accepted the design and source/integrity changes, then
inspected actual screenshots/browser evidence and rechecked copies, originals,
package identity and downloads. That evidence review ran no new browser test.
No packaged Python/C++ source changed: all 41 members match the pre-task identity
`1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
All 15 historical input/artifact files remain identical. Local byte/binding
checks do not attest native history or provider authenticity, and this viewing
convenience adds no scientific qualification or new observation.
