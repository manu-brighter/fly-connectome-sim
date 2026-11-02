# Event proposals → measured choice → locked plan

The user approved the next small complete event-planning milestone after the
reel demonstration. This explicitly releases the reward-free product choice
slice before formal training qualification; scientific gates are unchanged.
No API credential is configured. The user delegated the provider recommendation:
use a neutral proposal JSON handoff first, without extra API costs. A committed
example is an example, not a claimed live LLM response. Any LLM may later fill
the same strict format. Live generation and post-choice narration remain later.

## Bounded outcome and authority

Import exactly two event proposals, render both as actual visible RGB cards,
observe them with one fresh real FlyEngine, derive a left/right/defer choice
from measured lateral motor output, seal the run and export a locked event
plan plus replay. The output copies the selected validated proposal exactly.
No caller/LLM can supply or replace selected_option_id. A defer produces an
explicit deferred plan with no selected option; never force or hunt a winner.

This is an engineered product selection policy. DNa02 left/right is not a
validated semantic preference or biological choice. No learning, visual
specificity versus autonomous dynamics, consciousness, dopamine concentration
or receptor activity is established. The legacy MBON preference adapter is
not used; the primary MBON11/PPL101 assay remains separate and parked.
This first pilot starts fresh. It does not restore old-source reel checkpoints
or pretend that watching/training history affected this round.

## Proposal input: event-options/v1

UTF-8 JSON, at most64KiB, no duplicate keys/nonfinite values/unknown fields.
Exactly these fields:

```text
version: "event-options/v1"
brief: {title, guests, max_budget_chf}
options: [option0, option1]
option: {id, title, setting, music, budget_chf, capacity,
         duration_minutes, programme}
programme: [{start_minute, label}, ...]
```

Text is printable ASCII without controls: brief/title1..48 chars, music1..24,
programme label1..40; IDs match `[a-z][a-z0-9-]{0,31}`, unique. Setting is
`rooftop` or `warehouse`, choosing two declared visual scene recipes. Guests
10..500, max budget100..100000 CHF; option budget100..max_budget_chf, capacity
guests..1000, duration60..600 minutes. Programme has2..6 entries, begins at0,
strictly increasing integer start_minute, each less than duration_minutes.
Booleans are not integers. No URLs, commands, assets, provider claims, secrets,
thresholds, selection fields or arbitrary renderer configuration are accepted.
Budget/capacity checks establish internal example consistency, not real quotes
or real-world venue feasibility. These constraints are builder defaults.

The producer owns proposal_source={kind:"imported-json", name, size_bytes,
raw_sha256}. Name is a bounded basename label, not authority. It freezes a deep
canonical copy and proposal_sha256=SHA256(canonical proposal JSON). The input
cannot claim live API provenance. Add a small example and a copyable proposal
prompt describing the closed format and the fact that the LLM cannot choose.

## Rendered input and fixed observation

One deterministic paired RGB uint8 image384x216, frame_id="options". Ordered
option0 is LEFT, option1 RIGHT, fixed before observing. Use Pillow12.3.0's
bundled load_default font(size12), with fixed layout/renderer version and no OS
font/network/image dependency. Each card displays title, music, budget/capacity
and a visibly distinct simplified scene derived from setting: rooftop skyline/
sunset/DJ/crowd versus warehouse/truss/night/DJ/crowd. These are synthetic
representations of the proposed events, not proof of semantic recognition.
Do not merely relabel unrelated assay A/B patterns. Renderer must fit/clip
validated text deterministically; no hidden title affects the motor adapter.
Record renderer recipe, Pillow version, exact RGB descriptor/hash/base64 and
canonical proposal hash. Reproduce and verify pixels from metadata on export.
All proposal and render validation occurs before constructing engine/output.

One fresh actual0.1ms FlyEngine, unfrozen weights and cursor0. Feed the SAME
paired image for four consecutive500ms calls, exactly2s. All intervals advance;
stimulation=None,learning=False,both detail flagsFalse,normal passive evolution.
The first1500ms is a fixed settling period; the sole decision uses the final
500ms call's actual counts/populations/rates. No black-gap/reset/restore/RNG,
threshold tuning, side shuffle or second test after inspecting the result.

Use unchanged LateralMotorAdapter1Hz: right-left>1→option1; <−1→option0;
otherwise defer. evidence_strength is an adapter ratio, not statistical
confidence. Policy version="event-card-choice/v1". Decision effective_tick
20000; window15000..20000. The same-event motor_readout has the existing
interpretation/action_threshold_hz/decision shape and is independently checked
by RunRecorder. Do not weaken that validator or use a rolling-window substitute.
Compute the decision independently from the final integer bin sums, populations
and exactly0.5s, not merely tolerance-checked telemetry.rates_hz. Producer,
exporter and browser use that same count-derived arithmetic. Raw telemetry and
same-event readout must agree; reject disagreement rather than rewriting raw
values. Tiny float drift around strict ±1 must never change the selected ID.

## Recorded pilot and semantic validation

RunRecorder run_kindpilot, branch="event-choice/root", metadata family
"event-choice", protocol"event-choice/v1", stimulus"event-card-rgb/v1",
seeds=[]; factors freeze two-card left/right mapping. Include original validated
proposal/source/hash, renderer recipe, exact input declaration and fixed choice
recipe. No schema/core change or qualification claim.

Exactly6 events: genuine before checkpoint at0; four observe events;
genuine after checkpoint at20000. Observe events retain actual telemetry and
event_frame={frame_id:"options",sha256,width:384,height:216,rgb_base64}.
Only the last observe includes motor_readout and event_choice={policy_version,
selected_option_id:null|id}; the others contain neither. The exporter binds
the decision to that final observe's actual sequence/scientific hash. No new
trust issuer or invented native-history reference is introduced.

Semantic export verifies the ordinary sealed pilot, consumes every event to
normal EOF, rejects extra operations/branches/reordered/missing intervals and
premature seals, checks checkpoint positions, flags, identity/maps, all seven
populations, integer spike bounds, complete contiguous bins and rate/turn
conservation. Recompute image, proposal hash, final readout and selected ID;
never trust a claimed event_choice or final plan. Cap exactly4 observations,
200 bins,384x216 input,2MiB replay and64KiB plan. Preserve atomic new-target/
no-replace publication and safe paths. Old exporters/readers remain strict.

## Exported contracts

CLI commands:

```text
event-choice --proposal PATH --output-dir NEW_RUN
export-event-replay RUN --output NEW_JSON
export-event-plan RUN --output NEW_JSON
```

The two exports share one semantic reduction and independently finish EOF
before publication. One successful output is not authority to skip validation
for another. Producer returns VerifiedRun; exports take only source/output
paths, with no override/selected-option/threshold arguments.

event-choice-replay/v1 has exactly these top-level keys:
version,tick_ms,source,groups,inputs,segments,duration_ticks,decision,plan.
tick_ms=.1; source uses exactly run_kind,schema_sha256,run_metadata_sha256,
events_sha256,final_scientific_sha256,verification_mode,metadata.
inputs={options:{sha256,width,height,rgb_base64}}. Four segments retain
event_sequence,branch_id,frame_id,stimulation,learning,source_start_tick,
source_end_tick,playback_start_tick,playback_end_tick,bins. No clock sorting.

decision has exactly policy_version,effective_tick,event_sequence,
event_scientific_sha256,window_start_tick,window_end_tick,counts,populations,
readout,selected_option_id. Counts/populations are the two lateral groups;
readout is the existing four-field MotorDecision. Its reference is last observe,
not a native proof. selected_option_id follows the frozen left/right mapping.

event-plan/v1 has exactly version,status,brief,selected_option_id,selected_option,
decision_ref,source. Status selected or deferred. selected_option is the exact
frozen chosen option object or null. decision_ref={event_sequence,
scientific_sha256,input_sha256,policy_version}. source has run_kind,
schema_sha256,run_metadata_sha256,events_sha256,final_scientific_sha256,
verification_mode:"integrity-only". Replay.plan equals this same export object.
Plan bytes are a deterministic derivation; no post-selection LLM rewrite.

## Viewer and presentation

Add a separate strict event reader/dispatcher; do not loosen the original A/B
or video v1/v2 formats. Validate exact metadata/recipe/proposal/pixels/hash,
clock/bin/count/readout/mapping/decision/plan relationships, source mode and
terminal timing. The browser cannot independently attest native history or
Pillow rendering; the source-bound exporter reproduces those pixels.

Show a simple landscape planning board with the exact fed composite RGB and
the fly, using existing scene/style. Before tick20000 show pending; only at/after
20000 highlight the selected card and reveal the resulting plan, or explicit
defer with no highlight/plan. Do not fabricate a winner/gesture. A plain-text
plan panel shows chosen title/setting/music/budget/guests/programme and offers
download of the same bound plan after the decision. Use textContent, no HTML
from imported text. Keep actual measurements and their clock visible.

Timestamped30fps export stays at normal simulation speed. This event format
uses90 terminal-hold frames(3s), making2s source+3s labelled plan hold=5s film.
No simulation time/bins are added. Other formats retain their15-frame hold.
Make the existing frame writer accept a bounded optional hold length, default15,
and label dynamic duration accurately. Preserve exclusive export/cancel/load
ownership, deterministic seek/reduced motion and resource disposal. No autoplay
LLM/network call, real venue booking or multi-user deployment.

## Acceptance and release

Test-first proposal limits/injection/unknown-selection keys and deep-copy,
deterministic scene/pixel hashes and render binding, ±/tie/zero/count-derived
choice, genuine tiny-native deferred sealed roundtrip, resealed decision/
proposal/plan/pixel/clock/EOF mutations, fail-before-engine on invalid input,
atomic no-overwrite and old CLI/export compatibility. Tiny native fixture
correctly defers; do not alter it to force a winner. Frontend strict reader/
no-early-choice/plan/defer/hold/mutations and existing viewer tests/build.

Independent architecture/scientific/authority review before implementation;
source/security/integrity review after frozen code before one fresh actual
MaleCNS pilot(max2s simulated/120s subprocess wall). Accept selection OR defer,
no winner hunting. Audit actual pixels, bins, readout, plan identity and EOF;
view/export the same actual artifact and inspect encoded frame count/PTS and
decision visibility. Update handover/TODOs/report, reviewed feature commit/push.
Raw runs/checkpoints/video stay ignored; the small authored example/prompt are
first-party source. Live LLM transport, narrative continuation, reel-history
integration, training/qualification and broader platform checks remain open.
