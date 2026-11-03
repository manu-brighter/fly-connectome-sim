# Continuous reel observation → event choice

The next product milestone joins the two already implemented demonstrations:
one fresh MaleCNS engine watches a bounded fast feed and immediately observes
event cards, then exports one continuous replay and unchanged bound event plan.
The user requested autonomous continuation after `d97e1e8`; the builder chooses
this integration before live LLM transport or longer sessions. Strict imported
proposal JSON remains the provider boundary; no paid API or new credential.

## Authority and bounds

- One real engine factory call, one RunRecorder/root branch, genuine global
  simulation time. No reset, restore, replacement engine, rebasing native clocks
  or concatenation of independent recordings between phases.
- Reuse the existing prepared graph, video decoder/transform, fast-feed policy,
  renderer, count-derived motor adapter and sealed recorder. No numerical core,
  adapter, schema, dependency or formal-assay changes.
- Feed is the existing closed fast-feed recipe:5× source sampling,3s minimum
  dwell,4s clip cap,8s session cap,1–5 declared clips,30Hz actual RGB90x160.
  Source preparation is completed before engine construction/output creation.
  The existing8s session cap has priority over minimum dwell: a third clip can
  end after only2s when earlier clips both advanced at3s. Preserve this priority.
- The existing STOP ends only the feed phase. At its exact end tick T, feed the
  actual paired384x216 event image four times for500ms, without a gap. Maximum
  total simulation10s; at most240video+4card observations,246events,1160bins.
- All calls have stimulation=None,learning=False,both detail flagsFalse,
  unfrozen weights and ordinary passive evolution. Cards settle for1500ms;
  final500ms counts at[T+15000,T+20000] give unchanged strict1Hz left/right/
  defer. Accept defer; no tuning/retry to obtain an action.
- Continuity is an implemented/recorded workflow, not proof that reel content
  caused the choice. No control experiment, semantic/visual specificity,
  learning, consciousness, dopamine-concentration, receptor or validated motor
  claim. Formal science/C1 remain parked. New packaged source invalidates old
  formal identities, as before.

## Reuse without weakening older contracts

Add a separate closed `feed-event-session/v1` producer and `feed-event-replay/v1`
reader/exporter. Original A/B, video v1/v2 and event-choice v1 public wrappers
must retain their exact accepted formats, fixed roots/clocks/sequences and
exported bytes. Do not make their public parsers accept a continuous session.

Small private phase producers/reducers may be extracted with explicit branch,
start-tick and sequence context, with old wrappers passing their original
constants. Reuse actual raw events and their global owned sequence/hash fields.
Never synthesize a VerifiedRun, fake metadata/provenance, rewrite event hashes,
fabricate a source verification mode or disguise a phase as an old full run.
No general session framework or second simulator; keep phase helpers bounded.
Only the outer producer owns engine/recorder/checkpoint/seal lifecycle; phase
helpers never construct/seal a run or manufacture a VerifiedRun. Extract actual
clip/recipe validation directly; session metadata checks the union of video and
card hashes, without fabricated old aggregate metadata.

## Input and recorded run

CLI `feed-event-session --playlist PATH --proposal PATH --output-dir NEW_RUN`.
No profile/seed/threshold/winner/duration override. Validate proposal, render,
prepare every source, check safe new output path, then construct one fresh
FlyEngine(cursor0,dt0.1,unfrozen). Existing proposal and playlist limits apply.
The authored event example and existing local two-reel sources can be reused;
never reuse old-source raw checkpoints or relabel old measurement files.

Run kind pilot, root `feed-event/root`; metadata has exactly:

```text
engine_identity
protocol_version: "feed-event-session/v1"
stimulus_version: "feed-event-rgb/v1"
family: "feed-event-session"
seeds: []
factors: {clip_count, left_option_id, right_option_id}
video_recipe: exact existing fast-feed recipe
clips: exact prepared source metadata in order
proposal, proposal_source, proposal_sha256: existing validated import contract
renderer_recipe: exact existing event-cards/v1 recipe
input: exact paired event frame declaration (frame_id="options")
choice_recipe: exact existing event choice recipe plus
               timing_origin: "feed-stop/v1"
input_sha256: sorted unique hashes of ALL prepared video frames plus cards
```

The choice recipe's15000/20000tick values are relative offsets to the verified
feed STOP T. Observe/bin/decision ticks are actual global values T+offset; no
recorded clock is rewritten into a relative phase clock.

Exactly one genuine before checkpoint at0 and after checkpoint atT+20000,
named brain-before.npz/brain-after.npz; no anchors/branches/interventions.
Video observe payloads retain their existing shape and original global clocks,
clip/frame fields and video_policy. Card payloads retain their existing shape,
with actual global clocks and same paired event_frame. Only the last card
observe includes motor_readout and event_choice. The choice policy remains
event-card-choice/v1 because the adapter/window mapping is unchanged; its time
origin is declared by the enclosing session recipe, never by a user override.
The feed's final STOP is followed by exactly four card observes and final CP.
No synthetic transition event or simulation interval is inserted.

## Export and source binding

CLI `export-session-replay RUN --output NEW_JSON` and
`export-session-plan RUN --output NEW_JSON`. Both independently verify ordinary
sealed integrity, complete semantic consistency and normal EOF before publishing
atomic new files, never overwrite/source-internal/symlink/junction targets.
Plan64KiB/replay32MiB, at most244observations/246events/1160bins; validate each
phase before building output. This remains integrity-only, not native-history
attestation or safe arbitrary hostile raw-run intake (existing hardening TODO).

Validate one root, outer CP positions, exact metadata/flags/maps/populations,
all actual pixel/clock/bin/count/rate/turn relationships, existing fast-feed
policy recomputation and full ordered consumed prefix through STOP. Freeze T
from that STOP's actual end tick, not a caller field. No cards before STOP, no
feed after cards, no missing/extra/gapped observations. Re-render cards and
validate final raw motor readout against integer sums/populations/exact0.5s.
Reject disagreements; never rewrite raw rates or force selection.

Compact top keys exactly:
version,tick_ms,source,groups,inputs,segments,duration_ticks,feed_end_tick,
decision,plan. Version feed-event-replay/v1,tick_ms0.1; duration_ticks=T+20000.
Source is the same7-field shape as other replays, including complete metadata.
Groups are all seven population sizes. Inputs contain only consumed video
frames (existing VideoInput fields) plus options(existing plain RGB input).
Video segments use the existing video shape; cards use the existing event
shape. All source/playback ticks are actual identical global clocks, contiguous
from0. No locally rebased phase/source record or invented reference.

Decision fields match event-choice/v1: policy_version,effective_tick,
event_sequence,event_scientific_sha256,window_start_tick,window_end_tick,counts,
populations,readout,selected_option_id. Here effective/window end=T+20000,
window start=T+15000,event sequence=actual last card observe (N_video+4).
Bind the original scientific hash, not a reconstructed projection hash.

Plan retains event-plan/v1's exact7-field contract and six-field source shape:
version,status,brief,selected_option_id,selected_option,decision_ref,source.
Selected option equals the original frozen option exactly, or null/deferred.
Replay.plan equals separately exported plan. No extra session authority or
post-choice rewrite is introduced.

## Viewer and film

Separate strict session parser through recording.ts, with bounded explicit phase
helpers where useful. Validate the new closed metadata/timing/proposal/input/
policy/decision/plan contract. Do not validate by fabricating old-format metadata
and passing invented old recordings to old readers. Old formats stay strict.

Sampling and rendering use global time. Before T show the existing phone/feed,
exact fed portrait pixels, current media PTS/5× label, measured policy, fly motion
and400ms foreleg gesture only after genuine ADVANCE. At T directly switch to
the event board with actual paired pixels, pending decision. Feed STOP has no
swipe or intermediate hold. Backward seek reverses phase/visibility and hides
the plan/highlight/download. At T+20000 show the exact bound plan or honest defer.
Keep feed-end trigger available as recorded context, not a semantic rejection.

Reuse existing sample/draw primitives; build/dispose textures once per recording
and change phone/board visibility with sampled phase. URL/policy widgets, timeline,
5× source label and plan download must follow actual phase; session is not
mistaken for a v1/1× video or a fresh standalone event-choice recording.
The later-card measurement does not imply a learned effect of the earlier reels.

Export global nearest-half-up30Hz source ticks with existing frame writer,
then90 labelled terminal-hold frames/3s once after the final decision. No hold
at the feed/cards boundary and no new simulated interval. Maximum10s+3s film,
390frames at30fps. Preserve existing exclusive export/load/cancel/reduced-motion
behavior and old15/90hold defaults. Exact measured telemetry stays unsmoothed.

## Acceptance and release

Test-first actual tiny-native continuous execution and sealed export/plan,
factory exactly once/no reset/restore/object replacement, original global ticks,
feed STOP→four cards, actual input changes, exact final count readout and honest
defer. Declared positive/mutation fixtures remain explicitly declared. Reject
phase ordering/gaps/extra operations/resealed clocks/policy/plan/pixel/selection
drift and premature EOF. Prove old representative exports byte-identical and
compare before/after using the SAME old artifacts, since newly generated runs
legitimately have changed source identities after packaged-source changes; then
run focused old/new backend/CLI tests. Viewer tests cover phase boundaries,
reverse seek/no early plan, labels/swipe/STOP, operation/hold and strict parsing;
run all viewer tests/build. No new numerical/assay/dependency work.

Independent architecture/integrity preflight and frozen backend/Viewer reviews
before one actual maximum10s/240s-wall MaleCNS run using original local source
videos. No winner hunting/control-grid detour. Independently audit raw source
pixels/global bins/phase boundary/selection/plan, load that same replay in Chrome
and inspect actual encoded30fps frames/PTS around feed→cards→decision. Accept
selection OR defer. Track real identities/results/limits and remaining TODOs,
review explicit first-party staged diff, commit/push only feature and pause.
