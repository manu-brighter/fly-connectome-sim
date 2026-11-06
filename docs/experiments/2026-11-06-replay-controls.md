# Replay controls acceptance —2026-11-06

Viewer-only change from `a0cee3d`: help below the canvas, explicit focused-canvas
Home/End and100ms arrow seeking, guarded Space play/pause, and deduplicated
polite phase/result announcements. No geometry, measurement parser, export,
Python/C++, schema or dependency changes. The local37-member model identity stays
`093081c36bbb64dbb36099e5281407075767e6083244abaf7800631a30ae588b`.

## Tests

Node24.21.0/npm11.19.0, existing local dependencies, from `viewer/`:

```powershell
node --test --test-name-pattern='canvas shortcuts|only focused|main announces|A/B replay announcements' tests/session-replay.test.mjs
npm.cmd test
npm.cmd run build
```

Focused RED:6 expected failures in2814.8571ms; unchanged command GREEN:6 passed
in4161.5803ms. Final full viewer suite: **97 passed,0 skipped/failed in35.605s**;
TypeScript/Vite production build exit0. Existing experimental type-strip and
large-bundle warnings remain; no npm update was installed. The tests execute real
main/parser/sample control flow with DOM/WebGL/codec doubles, including operation
gates, native-control key handling, reverse/deferred results and live-region
write counts. They do not prove audible screenreader or encoded-video behavior.

The91-path final raw-byte inventory matched after tests/build. Its pre-implementation
comparison was captured after RED test addition: only3 product files differ from
that inventory; all87 non-owned paths are unchanged when excluding4 owned files.
The new test change is independently present in the Git diff. No simulator,
provider or new video-encoding run was required.

## Actual Chrome check on existing measurements

Reused `runs/feed-event-replay-20261103.json` from the historical9s continuous
session; no new measurements were produced or relabelled as current native proof.
Before the fix, the orbit hint's rectangle overlapped the canvas. Afterward:

- Canvas End→90000 selected Sunset House; ArrowLeft→89000 pending and no plan
  download; Home then ArrowRight→1000 with Feed clip1 announcement.
- Ctrl+End left the canvas timeline at1000; two Space presses started then
  paused real playback (observed1284 then1770). Final End restored90000.
- Default3840x1600 viewport: canvas1229x1022.5625; help top equals canvas bottom
  at1255.453125. Narrow390x844: canvas341x341; help top equals bottom556.78125.
  Neither had horizontal overflow. Resetting the viewport restored the same
  desktop canvas height; no progressive sizing growth was observed.
- Both actual screenshots were visually inspected. The help no longer obscures
  recorded canvas text. The narrow canvas remains dense; complete plan/measurement
  text remains available in the DOM below it. This is not full mobile certification.

Browser evidence/screenshots and exact control observations remain ignored under
`.tools/replay-controls/`. The initial sandbox Vite process bound its port but
did not respond to host HTTP; only that verified own process was replaced by a
host-local instance on127.0.0.1:5174. No public server or user browser settings
were changed. The temporary viewport override was reset.

Independent fresh Sol source/runtime/visual review closed with0 Critical,
Important or Minor findings. It read the actual code/logs/browser evidence,
rehashed91 final files and inspected both screenshots; it did not repeat tests
or claim audible screenreader/liveFPS/cross-browser acceptance.

Broader assistive-technology testing, cross-browser/liveFPS/device coverage and
the separate live API/formal-assay gates remain open. This slice adds no scientific
interpretation and changes no recorded choice or immutable event plan.
