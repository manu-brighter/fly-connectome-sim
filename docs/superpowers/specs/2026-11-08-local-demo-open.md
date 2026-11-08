# Open the complete local demo

## Selected continuation

After completion of the measured demo, fixed-choice feedback and companion
viewer, the user selected **Einfacher lokaler Demo-Start**: open the existing
recording, brain layers and planning notes together. Astra's initial triage
recommended one bounded file selection, without a new server or archive format.
Implementation choices below are the controller's, within that selected goal.

Add **Open demo** alongside **Open recording**, using the current viewer style.
It selects exactly five JSON files from one flat prepared folder:
`recording.json`, `cell-activity.json`, `anatomy.json`, `followup.json`,
`receipt.json`. Order is irrelevant; these exact unique names identify roles.
Existing version/schema/source checks determine whether each role is valid.
Explain the five-file selection in concise adjacent help. Existing individual
imports remain available. No directory permission, URL loading or automatic
provider request is added. Start paused at tick zero, as ordinary recording load.

## Validation and publication

Preflight count, unique supported names, nonempty integer byte sizes and each
role's existing limits BEFORE reading any file: recording 32 MiB, cell activity
16 MiB, anatomy 8 MiB, follow-up 128 KiB, receipt 16 KiB. Read each selected file
once; require returned length to match, snapshot bytes and decode strict UTF-8.
Do not weaken existing parsers, graph locks or follow-up source/Markdown checks.
Use the original recording bytes for all binding hashes and lengths.

Prepare the recording and three attachment controllers independently of the
currently displayed state. Reuse the actual recording/anatomy/cell/follow-up
parsers/controllers, plus `assertCellAnatomy`; no parallel schema implementation.
Only complete continuous-session selections with all five layers are supported
by this convenience import. A deferred or incomplete session remains usable
through the existing individual recording path and cannot manufacture notes.

After ALL files and cross-bindings pass, and the load is still current, install
the prepared recording/controllers and stage layers synchronously. Validation
failure must preserve the existing recording, tick, loaded layers, plan and
notes; loading may pause playback. No partially installed new recording/layer
may flash. A successful replacement resets timeline/hold and reveals no planning
text before the recorded choice. All original export, choice and rewind rules
remain intact. This guarantees validation atomicity, not recovery from GPU or
browser process failure.

Use the existing operation gate for recording/demo loads and export. Pending
work must not overwrite later selections/errors/status; superseding either
load invalidates the older candidate. Native picker cancellation changes nothing.
No export or attachment mutation during a combined load, no combined load
during export. Preserve existing cancellation and correctly ignore obsolete
individual attachment work when a new recording/demo load starts.
Anatomy/cell callbacks need request or generation guards in success, catch and
finally; recording-object equality alone fails after an unsuccessful replacement.
Test old attachment completion after failed demo load and a newer attachment.

## Local preparation command

Add a small Node 24 script `scripts/prepare-demo.mjs`, using built-in modules
and the same bounded viewer validation. Explicit inputs:
`--recording`, `--cell-activity`, `--anatomy`, `--followup-dir`, `--output-dir`.
Read exactly the three named files and follow-up directory's `followup.json`
and `receipt.json`; no recursive scan, key/env read, subprocess or network.
Open regular-file handles, preflight their sizes, and bound each actual read to
the expected size plus one byte; reject changed/truncated/grown input. A separate
stat followed by unbounded `readFile` does not satisfy the byte limits.
Validate immutable input snapshots before output creation, then copy those exact
five snapshots into a newly created output directory. Existing output is an
error, including symlinks/dangling links; never overwrite/merge/delete anything.
Use exclusive file creation. Require an existing parent directory. If a write
fails, report an incomplete output and keep it for inspection; no recursive
cleanup or success claim. Print the output location and simple selection/start
instructions only after all copies succeed. This does not start a simulation,
install dependencies, broaden server filesystem access or create provenance.

The result is a convenience folder, not a fresh run or scientific certificate.
Raw runs, checkpoints, API requests, keys, videos and other directory contents
are excluded. Existing ordinary Vite startup remains the local server command;
no new launcher/service lifetime or automatic browser startup is introduced.

## Acceptance

Test first: file count/names/duplicates/pre-read caps/UTF-8, exact bytes and mixed
bindings, complete commit versus preserved old state, cancellation and stale
read/hash success/error, export locks, selected-boundary/rewind, unchanged
downloads; script rejects existing outputs and invalid inputs without writes.
Use declared fixtures for failure/race tests, clearly separated from acceptance.

Prepare a NEW ignored folder from the already accepted real demo and companion.
Verify five output files equal their inputs; open all five in one real browser
selection. Check original cells/anatomy, pending/final/rewind notes, failed mixed
import preservation, downloads and desktop/narrow layout. No new provider or
native acquisition, no movie export required. Independent Astra source/integrity
and actual evidence review, relevant tests/build, docs/handover and reviewed
feature commit/push/CI complete the step. Python/C++ package identity is unchanged.
