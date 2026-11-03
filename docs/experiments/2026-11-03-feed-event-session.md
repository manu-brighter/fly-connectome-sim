# Continuous feed-to-event observation

This milestone produces a single fresh-engine reel-to-event workflow. It does
not concatenate independent recordings, restore a prior-source checkpoint or
claim that reel content caused the later choice. The event proposals remain
authored/imported JSON, with no live LLM request or API cost.

## Fixed scope

The [contract](../superpowers/specs/2026-11-03-feed-event-session.md) and
[plan](../superpowers/plans/2026-11-03-feed-event-session.md) fix one engine,
one recorder/root and two genuine outer checkpoints. Existing fast-feed policy
processes at most8s at30Hz, with5× source sampling, then its actual STOP tick T
starts four500ms card observations immediately. There is no reset, restore,
replacement engine or rebased native clock between phases. No external DAN or
learning is supplied; ordinary passive evolution remains enabled.

The card window settles for1500ms; final500ms integer motor counts, actual
populations and the unchanged strict1Hz rule select left/right/defer at T+20000.
The plan copies the selected validated option unchanged or explicitly defers.
Its reference is the actual last-card global event sequence/scientific hash.
All source/playback clocks remain global. The first-party native core, adapter,
recorder/schema and dependencies are preserved.

Source-bearing changes invalidate previous formal identities; this is not formal
qualification, a production frozen configuration, native-history attestation,
scientific support or a learned/semantic preference. The product sequence is
user-authorized; formal assay/C1/live LLM transport remain separate.

## Implementation verification

The architecture/integrity preflight returned READY,C0/I0. It explicitly fixed
relative recipe offsets versus global observations,8s session-cap priority over
minimum dwell, outer-owner-only engine/recorder lifecycle and same-artifact old
export byte comparisons. No runtime approval was inferred from this preflight.

Frozen model:36 packaged Python/C++ members, SHA256
`d4b72b01f14c4c4ec1266f976692fa6bf7dc91b3b83ed40f6f5540ab25a7ec9c`;
schema unchanged:
`3cc3257af02363b056db8390c99bd0040ab902b7808138d8dfc6c3d92628fb13`.
Backend39-path inventory includes those sources, schema and two changed test
files. Complete viewer inventory has24first-party files; package/lock bytes
match base`d97e1e8`. Raw SHA256/size checks matched before/after tests/reviews.

```powershell
.venv/Scripts/python.exe -m pytest tests/experiment/test_feed_event_session.py tests/experiment/test_video_observation.py tests/experiment/test_event_choice.py tests/experiment/test_video_policy.py tests/test_cli.py tests/experiment/test_recorder.py tests/experiment/test_recorder_projection.py -q -p no:cacheprovider --basetemp=.tools/feed-event-backend/focused-final
.venv/Scripts/python.exe -m pytest tests/experiment/test_recorder.py::test_checkpoint_directory_substitution_cannot_write_outside_run -q -p no:cacheprovider --basetemp=.tools/feed-event-acceptance/junction-host-r1
npm --prefix viewer test
npm --prefix viewer run build
```

Backend:640passed/1skipped/zero failed in215.58s. The sole existing Windows
junction test could not create its junction inside the sandbox; its separate
host execution passed1/1 in0.07s. The first targeted host invocation failed
during setup because its temporary parent directory was missing; that test did
not execute and is not counted as a pass. The corrected invocation is above.
No broad suite was repeated. These are scoped integration checks, not a
whole-project/formal-assay pass.

Viewer:91passed/zero skipped/zero failed in29.179s, TypeScript/Vite build exit0.
The known830.01kB chunk-size and test-only Node type-strip warnings remain. An
initial wrong-directory`npx tsc` invocation fetched an unrelated CLI into npm's
cache and failed; no dependency/lockfile changed. Final builds use the installed
viewer toolchain. No live model/API request occurred.

The true frozen-source tiny-native session has126events,124observations,
680bins,T40000/final60000,decision sequence124 and honest0:0/defer. A separate
declared tonic toy fixture verifies advances at3s/6s and session STOP at8s even
when the third clip has only2s dwell; cap244observations/246events/1160bins.
Declared positive count fixtures are not presented as native winners. RED/GREEN
also covers phase/policy/clock/pixel/plan/selection/EOF/path/publication mutations,
one engine/no reset/restore, boundary/reverse visibility and operation ownership.

Independent frozen backend review closed PASS,C0/I0/M0new after reading final
test receipts. Known foreign raw-run allocation hardening remains open. The
read-only reviewer ran no programs/tests and wrote no report file; this is a
controller-owned account of the delivered verdict. Independent fresh viewer
review closed C0/I0/M0:24raw identities, final tiny fixture/separate plan,
six extra rejection probes, boundaries and old parser/default checks verified.
It did not repeat the complete suite or perform browser/native/encoded QA.

Before refactoring, three actual existing sealed runs were exported with base
`d97e1e8`, without any new native simulation. These baseline bytes are retained
locally for exact after-refactor comparisons:

| Historical format | Bytes | SHA256 |
| --- | ---: | --- |
| event-choice-replay/v1 |728429|`ba5cb97c3d8068413dafc2869e463de1302207175b6d9a451c605f8a7bc709e4`|
| measured-video-replay/v2 |12443795|`fa9565bea925a66b2afaccb6e337a8dd5c3c2d0b52e65524575325e936b29323`|
| measured-video-replay/v1 |6266520|`ca85478dbe65edf64b4d60d579699b672aed54bc34f833a9d7c7837d3183e6f5`|

These are compatibility comparisons of the same old artifacts, not upgrades of
their historical model-source identities or new fullgraph acceptance. All three
were re-exported again after the final source freeze and remained byte-identical.

## Actual observation and presentation

After both independent frozen-source reviews closed, exactly one fresh actual
MaleCNS run executed. The local original two-reel playlist retained the source
files used by the prior fast-feed observation; no media was downloaded or old
measurement/checkpoint restored for this run.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli feed-event-session --playlist .tools/reels-source/playlist.json --proposal examples/event-options.json --output-dir runs/feed-event-session-20261103
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli verify-run runs/feed-event-session-20261103
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli export-session-replay runs/feed-event-session-20261103 --output runs/feed-event-replay-20261103.json
.venv/Scripts/python.exe -X utf8 -B -m fly_connectome_sim.cli export-session-plan runs/feed-event-session-20261103 --output runs/feed-event-plan-20261103.json
```

Observation exited0 in94.735s within240s. Ordinary verification/replay export/
plan export all exited0 in1.282/2.359/2.344s. Source fingerprint and proposal/
playlist bytes were exact before/after every command. This records actual local
Windows working-copy bytes, not cross-platform or native-history attestation.
No second actual run or tuning/control search was performed.

Actual session:216events,214observations,1040bins,90000ticks/9s. Feed consumed
210frames/7s:90frames/3s from clip0 and120frames/4s from clip1. At30000ticks,
motor-right advanced(rolling L3/R6,delta+10Hz). Feed stopped at70000ticks via
playlist_exhausted/clip_window_end(rolling L6/R3,delta−10Hz); that terminal
trigger is the external clip cap, not a semantic rejection. Card observations
cover70000..75000..80000..85000..90000 in the same state, without a reset/gap.

Final500ms counts **L6/R2**, populations1/1, give **12/4Hz per cell,delta−8Hz →
inspect_left**. The bound option is Sunset House,rooftop/House,CHF4800,
100guests,capacity120,240minutes,programme0Welcome drinks/60DJ and dancing.
The actual last-card sequence214 scientific hash is
`292373a95bdc95a1e0007683e30dddfd95b1c184a573012bacfc22dd5b767fc2`.
Different counts from the historical standalone pilot are not a controlled
content-effect comparison; no causal or learned preference is inferred.

Independent raw audit re-decoded both original source files and verified all240
prepared PTS/RGB hashes and210consumed video pixels, then all four paired-card
frames against the fixed rendered bytes. It checked original216-event/global
sequence, contiguous clocks/flags/bins/populations/rates, complete feed-policy
arithmetic, STOP→cards boundary, final counts/readout/reference and exact plan.
The standalone plan equals canonical replay.plan plusLF. This audit performs no
new neural simulation and does not attest native execution history.

| Local ignored artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `runs/feed-event-replay-20261103.json` |13138312|`d653f948af79980aeb5986109f0bfb301a749514ec396b65f60efd5abeae874d`|
| `runs/feed-event-plan-20261103.json` |1077|`39ea28c12e6b60e6f14b167072382f78c152568ded65ac66aa9859223b3a27a1`|
| `viewer/test-output/feed-event-session-30fps.webm` |3335167|`3f44bf0056644bcf19d6641e12570999b6d28817cdde6c4771814aaaf18b61f6`|

Raw events20,886,757bytes,SHA256
`2da87c82e29ff440a8a29a166b56606501c63cdd0286507b76ab263d96e57183`;
metadata SHA256
`4e1ec147632d61e9a1edb3e26e963bca5f17b6dc9455e412ad185c454b2a7be8`;
final scientific chain SHA256
`470bd09d024731f811a8129a18f419b3ee52acad96b9c750d643de3897704135`.
Outer checkpoints are seq0/tick0(5,092,783bytes) and seq215/tick90000
(6,858,386bytes). The source model/native core and all global steps are declared
in the original artifact; these hashes alone grant no history/science authority.

Actual Chrome loaded that same compact file. At69999ticks it showed phone,
clip2/frame120,source PTS304640/15360,5× label/URL and recorded WATCH. At70000
it switched directly to pending cards,event211,with the recorded feed-end context.
At89999 no plan/download was available;90000 showed selected Sunset House,
left outline, exact proposal and final6:2 readout. Reverse69999 restored the
phone/feed widgets and hid the plan. Playback at0.25× crossed into cards;
pause held83095ticks. Export restored paused90000,with correct final3s label.
Downloaded browser plan JSON equals the CLI plan structurally (pretty JSON
formatting differs). Actual loading/export controls and disabled plan button
were observed; cancellation semantics are tested, not re-enacted in this film run.

Independent EBML audit and full PyAV decode confirmed **360VP9 frames,900x900,
12.000s**:270source frames/9s plus90labelled terminal-hold frames/3s. PTS span
0..11967ms,33/34ms intervals,explicit end12000ms. Decoded frames0/8 show actual
video/illustrative pose changes;92 shows the existing foreleg screen stroke;
209is the last phone frame,210at7s is pending cards with no intermediate hold;
269is pending at8.967s,270/359show selected plan/left outline and labelled9s
terminal sample. Native Chrome player reports12s/900x900 and no media error.
This is Windows Chrome/VP9 acceptance, not broad mobile/browser/live-FPS proof.
The known interactive orbit-hint overlap remains; the film omits that DOM hint.
The long final feed-context line uses compressed text in the900px film.

## Remaining limits

Continuous production alone is not a counterbalanced content-effect experiment.
The uncalibrated motor policy is an engineered mapping to position. Source
integrity and semantic consistency do not attest native execution history.
No consciousness, semantic understanding, dopamine concentration, receptor
activity, biological learning or validated motor behavior is established.

Live LLM transport, longer feed sessions, broader platform/accessibility checks
and formal learning qualification/confirmation remain open. Generic foreign
raw-run manifest/JSONL intake still lacks pre-allocation bounds; own bounded
local runs are the reviewed use case, not an arbitrary hostile-input service.
Raw media/runs/checkpoints, logs/scripts/screenshots and movies stay ignored and
are unavailable to a fresh cloud checkout; the tracked contract/commands allow
fresh reproduction, not reverification of absent local bytes.
