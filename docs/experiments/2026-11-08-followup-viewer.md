# Planning companion viewer acceptance — 2026-11-08

## Scope and result

The existing German companion can be imported beside its original measured
session and downloaded as checked Markdown. It appears in a separate planning
section after the recorded selection. Rewinding before that selection removes
the text and disables its download. The original plan export is unchanged.
This adds no provider request, native recording, movie or scientific result.

Open `runs/cell-demo-20261108-02/session/recording.json`, then use **Open planning
companion** to select both `followup.json` and `receipt.json` from
`runs/event-followup-live-20261108/`. Names and selection order do not determine
the file types. The full original plan, recording bytes, reconstructed canonical
plan/session-receipt bytes and companion/Markdown bytes must match the receipt
before publication.
See the [contract](../superpowers/specs/2026-11-08-followup-viewer.md) and
[usage](../getting-started.md#optional-follow-up-to-a-fixed-event-choice).

These checks establish local binding consistency, not raw/native replay
attestation, provider authentication or factual accuracy of the suggestions.
The visible German label identifies an advisory companion and states that
availability and prices are unconfirmed. Static connections and measured cell
counts retain their existing, separate scientific labels.

## Browser observations

Actual acceptance used the previously accepted native recording and live
follow-up pair, without modifying or regenerating them:

- At ticks 0 and 89999, the imported companion has no revealed title, overview
  or list content, and its download is disabled. At the recorded choice tick
  90000, Sunset Rooftop Social appears with three preparation suggestions and
  three open questions. Rewind hides it; returning to the end restores it.
- A changed companion fails the exact-file binding and preserves the previously
  valid attachment. Both file orders import successfully.
- The Markdown downloaded through the UI equals the original 1614 bytes:
  SHA256 `cae0096b487e8af80d0c67f580df70a62999f957e24c03b6ad7aee5a0decae2e`.
  The original JSON download remains deeply equal to the complete saved plan.
- Desktop 1280×1000 and mobile 390×844 show readable two-column/one-column
  content with `lang="de"` and no horizontal overflow. The existing 256-cell
  attachment and 12,000 static anatomy positions still load correctly.
- An artificially delayed file read plus a different declared test recording
  verifies that late work cannot attach to a replacement recording. During the
  pending import, video/notes downloads are disabled and recording replacement
  remains available. Importing the old pair against that replacement fails.
  A separate declared deferred fixture reveals no companion before or after
  its decision. These synthetic checks are not new native observations.
- The final browser session has no console errors, one pre-existing Three.js
  shadow-map fallback warning, and no resource requests beyond local Vite files.
  An earlier baseline navigation had the existing missing-favicon response.

Browser evidence and screenshots are preserved locally under
`.tools/followup-viewer-20261108/`: `followupBrowserBehavior.json`,
`followupBrowserRaces.json`, `browser-layout.json`, `desktop-companion.png`,
`mobile-companion.png`, console/network logs and downloaded files. The initial
automation wait used incorrect status capitalization; element screenshot calls
also timed out at the tool boundary. Corrected waits/direct Playwright captures
completed. Neither is counted as an application failure or hidden test pass.

## Verification

Sol implemented the bounded viewer change test-first. Independent Astra review
covered the binding contract, untrusted text, async replacement, export locks
and actual main-controller behavior. A mutable-context finding reproduced a
failure before the binding snapshot fix. An identifier-newline finding was
retracted after direct tests showed the unchanged regex already rejected it.
Astra separately inspected both actual screenshots and the browser evidence,
independently matched the input/package hashes and downloads, and accepted the
bounded visual/artifact result with no blockers. This review did not perform a
second browser run or imply another film or native acceptance.

Final commands in `viewer/`:

```powershell
npm test
npm run build
```

The suite passed 153 tests, zero failures/skips, in 36.868 seconds; typecheck
and production build passed with the existing large-chunk advisory. Two test
registrations check the private accepted Markdown and explicitly skip when
those ignored artifacts are absent in a clean checkout. All ordinary parser
and controller regressions use declared, data-free fixtures.

The controller independently reconstructed the exact original plan and session
receipt bytes using the existing browser parser/canonical encoder. A read-only
artifact audit matched all 15 pre-task historical files, both downloads and all
41 packaged Python/C++ sources. The unchanged Windows raw-byte package identity
is `1f2a004c9dfcd37c4824a2fd220d1d723c7f95cc34620bb1ebbe7ced7634e77b`.
This does not replace the historical recording identity or qualify the parked
research assay. No API cost was incurred by this viewer continuation.
