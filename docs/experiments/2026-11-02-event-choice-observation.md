# Event choice: measured motor selection and bound plan

This is a bounded product pilot, not a learning assay or a semantic-preference
experiment. The two event concepts are authored examples imported as strict
JSON; no live model request, API key or paid API call is involved. The renderer
feeds actual paired RGB cards to the existing MaleCNS engine. The plan copies
the measured selection unchanged, or explicitly records no selection.

## Fixed contract and identity

The [contract](../superpowers/specs/2026-11-02-event-choice-milestone.md) and
[plan](../superpowers/plans/2026-11-02-event-choice-milestone.md) declare one fresh
2s observation: four500ms calls with the same384x216 paired image, no external
stimulation or learning, normal passive evolution. The first1500ms settle;
integer motor counts from the final500ms determine the existing strict1Hz
left/right/defer action at20000ticks. No reset, old checkpoint restore, threshold
override or winner-hunting retry is allowed.

- 35 packaged Python/C++ members, model-source SHA256:
  `e0bfc0ef08b44beafababa8598a0f902a9dcdc75e71d07f626f79fe5ed2c1275`.
- Schema SHA256:
  `3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
- [Example proposal](../../examples/event-options.json):774 bytes, SHA256
  `ff6343b018b2043581acc915ed5699f85d3012185c061b510af78726962ff55c`.
- Actual RGB input hash:
  `727f76cdf9391c91dd3df2b8ec8d5bc759413b96c6ec6b21ffea737852758203`.

The historical33-member fast-feed model/evidence is not current-source formal
qualification. Native C++/DLL, schema, recorder, adapter and dependencies remain
unchanged. The current source-bearing addition does not confer formal assay
qualification, a production frozen configuration or confirmation.

## Source verification and independent review

Backend test commands, from the repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests/experiment/test_event_cards.py tests/experiment/test_event_choice.py tests/test_cli.py tests/experiment/test_measured_replay.py tests/experiment/test_adapter.py tests/experiment/test_recorder.py -k 'event or measured or adapter or motor_readout' -q --basetemp=.tools/event-choice-backend/focused-final -p no:cacheprovider
.venv/Scripts/python.exe -m pytest tests/test_cli.py tests/experiment/test_video_observation.py tests/experiment/test_video_policy.py -q --basetemp=.tools/event-choice-backend/old-compat-final -p no:cacheprovider
npm --prefix viewer test
npm --prefix viewer run build
```

Results:307 passed/310 deselected in39.29s; separately79 passed in85.88s.
These backend suites overlap at CLI and are not additive. Neither had skips or
unresolved failures. The genuine tiny-native fixture correctly deferred0:0;
positive/tie/mutation tests use explicitly declared fixtures, not fabricated
native outcomes. All40 backend freeze paths, including all35 sources, schema
and owned tests/example, were independently rehashed and matched.

Final viewer results:83 passed/zero failed/zero skipped in10.263s; build exit0.
The existing bundle-size warning remains; a test-only Node type-stripping probe
also emits an experimental warning. RED/GREEN includes strict proposal/selection
injection rejection, exact plan copying, timing/EOF, no early plan,200 native
10ms bins, merged/redistributed/199/201-bin rejection, correct late-codec3s hold
label and bounded narrow terminal title. Viewer freeze contains23 first-party
paths; this is not a whole-project/full-assay test pass.

Independent backend scientific/authority/security source review returned
**C0/I0/M1, pass with minor for the own bounded pilot**. The remaining minor is
unbounded allocation during generic raw-run manifest/JSONL intake before the
event export's output-size checks. Arbitrary foreign runs and production service
safety are outside this acceptance; intake hardening remains a tracked TODO.
The read-only reviewer inspected source, tests/logs and independently reduced
the saved tiny replay, but did not execute project tests or attest native history.

The initial independent viewer review found one Important bin-resolution gap
and two Minor presentation issues. All three received test-first corrections;
fresh independent scoped closure returned **C0/I0/M0**. All23 source identities
matched before/after its probes; three new regressions independently passed.
Final viewer manifest SHA256:
`fdb8c7c6ed6975414cfd0522f9d1b9a339bcc1321383e44b9efc6b64ae136dcc`.

## Actual artifact and presentation acceptance

After both source reviews closed, exactly one fresh actual MaleCNS pilot ran:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli event-choice --proposal examples/event-options.json --output-dir runs/event-choice-v1-mvp-20261102
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli verify-run runs/event-choice-v1-mvp-20261102
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli export-event-replay runs/event-choice-v1-mvp-20261102 --output runs/event-choice-replay-v1-mvp-20261102.json
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli export-event-plan runs/event-choice-v1-mvp-20261102 --output runs/event-plan-v1-mvp-20261102.json
```

All exited0. Observation took14.687s within its120s subprocess wall budget;
ordinary verification/replay export/plan export took0.406s/0.515s/0.531s.
All35 model-source members and proposal bytes remained exact before/after every
command. These are exact local Windows working-copy bytes, not a cross-platform
source/physiology attestation. The existing Zig0.16.0 toolchain and prepared
MaleCNS166,700-cell graph were used; no additional native run was made.

The sealed run has6events,4observations,200 contiguous10ms bins and20000ticks.
The final500ms contained **left2/right1 spikes**, populations1/1, hence
**4Hz/2Hz per cell, difference−2Hz → inspect_left**. The unchanged policy chose
`sunset-house`: Sunset House, rooftop/House,CHF4800,100guests,capacity120,
240minutes,programme0Welcome drinks/60DJ and dancing. This is one measured
position decision, not a demonstrated preference for rooftop events or music.

Original-byte audit independently checked the raw6-event sequence/stream hash,
all4actual inputs against the frozen rendered RGB bytes, proposal/source hashes,
200 bin clocks/counts/populations/rates and final same-event motor readout/hash.
The standalone plan is byte-identical to canonical embedded plan JSON plusLF.
No extra native simulation or native-history attestation was performed by this
arithmetic/pixel audit. The source-bound exporters completed full sealed EOF.

| Local ignored artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `runs/event-choice-replay-v1-mvp-20261102.json` |728429|`ba5cb97c3d8068413dafc2869e463de1302207175b6d9a451c605f8a7bc709e4`|
| `runs/event-plan-v1-mvp-20261102.json` |1075|`4475f6ccc0f513e4b88b91e0ccd02d6b55202fbd7a4deeae469d8a8c3046224b`|
| `viewer/test-output/event-choice-replay-30fps.webm` |859517|`a2d6b63875e1db6ab81f9747aa582b3b99a54f8c103891e2a1b12c0d960f9571`|

Events:1,490,740 bytes,SHA256
`bbcc1736500c9e9608584d0ea5317e29711d2c327de65bdfe7692bc412137f8f`;
metadata SHA256
`79c5246b07e2a2976e057819090e887eababbf39ec4b3d3ffbc0c8970cb35297`;
final scientific chain SHA256
`0b7b895eca8c82241466db949874995f05a401e2d1f17b02543bd4b5603f78b5`.
Decision references actual observe sequence4,scientific SHA256
`39fc1bf5707285640992cf233b27cec8bfe926b6b2e569f70c2fd0010de38cfc`.

Actual Chrome loaded that same replay file. At19999ticks the plan/highlight
remained absent and download disabled; at20000ticks Sunset House and its exact
plan appeared, with guests100/capacity120 and final-window2:1 counts. Reverse
seek restored pending/disabled download. Playback at0.25× advanced to10438ticks;
pause held10438. Export restored its original paused terminal position, with a
correct3s presentation-hold note. Browser-downloaded plan JSON equals the CLI
plan structurally; its pretty formatting differs from canonical CLI bytes.

Independent EBML audit and complete PyAV decode of the actual UI export found
**150VP9 frames,900x900,5.000s**:60source frames/2s plus90 labelled hold frames/3s.
PTS are0..4967ms,intervals33/34ms,explicit end5000ms; each second has30frames.
Decoded frames0/8 show illustrative wing/body/leg motion; frame59 at1.967s is
pending with no highlight/plan. Frame60 at2s and final149 show the selected plan,
left outline and labelled hold of the2s measured endpoint. No simulation time
advances during the hold. The native Chrome video player reports5s/900x900 and
no media error. This is Windows Chrome/VP9 acceptance, not live-FPS, mobile or
cross-browser acceptance.
The interactive DOM orbit hint touches/overlaps the event overlay's top edge;
this minor layout polish remains open. The encoded film omits that DOM hint.

Raw runs/checkpoints, audit scripts/logs/screenshots and movie stay local and
ignored. A fresh checkout can reproduce with the tracked example/commands;
it cannot reverify these absent local bytes from this report alone.

## Limits and remaining work

This is an engineered mapping from lateral motor activity to option position.
It does not establish visual specificity, semantic understanding, learned
preference or validated motor behavior. There is no counterbalanced causal
experiment. Integrity/semantic consistency do not attest native execution
history. The fresh event pilot does not continue reel history or trained state.

Live LLM transport/narrative continuation, event-history integration, longer feed
sessions, broader browser/accessibility checks and formal scientific gates remain
separate. The [proposal prompt](../event-proposal-prompt.md) and
[commands](../getting-started.md#local-event-proposals-and-measured-selection)
support the current provider-neutral local workflow.
