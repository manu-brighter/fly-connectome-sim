import { GROUPS, decodePixels, type Counts, type Input } from './replay.ts';
import { validateRecipe, validatePreparedVideoClips, validateVideoInputs, validateVideoPhase, sampleVideoAtTick, videoPolicyLabel, type VideoInput, type VideoSegment } from './video-replay.ts';
import { check, object, keys, int, ascii, digest, canonical, equal, sha256, strictJson, validateProposal, type EventRecording, type EventSegment, type Decision, type EventPlan } from './event-replay.ts';

type MotorCounts = { motor_left: number; motor_right: number };
const SOURCE_KEYS = ['run_kind', 'schema_sha256', 'run_metadata_sha256', 'events_sha256', 'final_scientific_sha256', 'verification_mode'];
const SIDES = ['motor_left', 'motor_right'] as const;
export type SessionRecording = {
  version: 'feed-event-replay/v1'; tick_ms: .1; source: EventRecording['source']; groups: Counts;
  inputs: Record<string, VideoInput | Input> & { options: Input }; segments: Array<VideoSegment | EventSegment>;
  duration_ticks: number; feed_end_tick: number; decision: Decision; plan: EventPlan;
};
export function isSessionRecording(value: { version: string }): value is SessionRecording { return value.version === 'feed-event-replay/v1'; }

// Validate the actual two phases in one source identity and global clock domain.
// Neither phase is projected into a legacy recording or fabricated metadata.
export async function parseSessionRecording(text: string): Promise<SessionRecording> {
  check(new TextEncoder().encode(text).length <= 32 * 1024 * 1024, 'Session recording exceeds 32 MiB.');
  const item = keys(strictJson(text), ['version', 'tick_ms', 'source', 'groups', 'inputs', 'segments', 'duration_ticks', 'feed_end_tick', 'decision', 'plan'], 'Session recording');
  equal(item.version, 'feed-event-replay/v1', 'Session version'); equal(item.tick_ms, .1, 'Tick size');
  int(item.feed_end_tick, 1, 80000, 'Feed end');
  const source = keys(item.source, [...SOURCE_KEYS, 'metadata'], 'Source');
  check(source.run_kind === 'pilot' && source.verification_mode === 'integrity-only', 'Only integrity-only pilots are supported.');
  for (const name of SOURCE_KEYS.filter((name) => name.endsWith('_sha256'))) digest(source[name], `Source ${name}`);
  const metadata = keys(source.metadata, ['engine_identity', 'protocol_version', 'stimulus_version', 'family', 'seeds', 'factors', 'video_recipe', 'clips', 'proposal', 'proposal_source', 'proposal_sha256', 'renderer_recipe', 'input', 'choice_recipe', 'input_sha256'], 'Metadata');
  equal(metadata.protocol_version, 'feed-event-session/v1', 'Protocol'); equal(metadata.stimulus_version, 'feed-event-rgb/v1', 'Stimulus'); equal(metadata.family, 'feed-event-session', 'Family'); equal(metadata.seeds, [], 'Seeds');
  const proposal = validateProposal(metadata.proposal);
  const proposalHash = await sha256(new TextEncoder().encode(canonical(proposal)));
  equal(metadata.proposal_sha256, proposalHash, 'Proposal hash');
  const proposalSource = keys(metadata.proposal_source, ['kind', 'name', 'size_bytes', 'raw_sha256'], 'Proposal source');
  equal(proposalSource.kind, 'imported-json', 'Proposal source kind'); ascii(proposalSource.name, 80, 'Proposal source name');
  check(!/[\\/:]/.test(proposalSource.name) && proposalSource.name !== '.' && proposalSource.name !== '..', 'Proposal source must be a basename.');
  int(proposalSource.size_bytes, 1, 65536, 'Proposal source size'); digest(proposalSource.raw_sha256, 'Proposal source raw hash');
  check(Array.isArray(metadata.clips), 'Missing prepared clips');
  validateRecipe(metadata.video_recipe, true);
  const { prepared, declaredHashes } = validatePreparedVideoClips(metadata.clips, true);
  equal(keys(metadata.factors, ['clip_count', 'left_option_id', 'right_option_id'], 'Factors'), { clip_count: metadata.clips.length, left_option_id: proposal.options[0].id, right_option_id: proposal.options[1].id }, 'Frozen side mapping');
  equal(metadata.renderer_recipe, { version: 'event-cards/v1', pillow_version: '12.3.0', font: 'Pillow-load_default', font_size: 12, width: 384, height: 216 }, 'Renderer recipe');
  equal(metadata.choice_recipe, { policy_version: 'event-card-choice/v1', adapter_version: 'lateral-motor-adapter/v1', action_threshold_hz: 1, observation_count: 4, duration_ticks: 5000, settling_ticks: 15000, window_start_tick: 15000, window_end_tick: 20000, stimulation: null, learning: false, pathway_detail: false, qualification_detail: false, timing_origin: 'feed-stop/v1' }, 'Choice recipe');
  const groups = keys(item.groups, GROUPS, 'Groups'), maps = keys(object(metadata.engine_identity, 'Engine identity').neural_groups, GROUPS, 'Neural maps');
  for (const name of GROUPS) {
    int(groups[name], 1, Number.MAX_SAFE_INTEGER, `Population ${name}`);
    const map = maps[name]; check(Array.isArray(map) && map.length === groups[name], `Population ${name} differs from map.`);
    for (const cell of map) int(cell, 0, Number.MAX_SAFE_INTEGER, `Map ${name}`);
    check(new Set(map).size === map.length, `Map ${name} has duplicate cells.`);
  }
  const inputs = object(item.inputs, 'Inputs');
  check(Object.hasOwn(inputs, 'options'), 'Missing paired options input');
  const videoInputs = Object.fromEntries(Object.entries(inputs).filter(([name]) => name !== 'options'));
  await validateVideoInputs(videoInputs, prepared);
  const input = keys(inputs.options, ['sha256', 'width', 'height', 'rgb_base64'], 'Options input');
  equal(input.width, 384, 'Input width'); equal(input.height, 216, 'Input height'); digest(input.sha256, 'Input hash');
  check(typeof input.rgb_base64 === 'string' && input.rgb_base64.length === 384 * 216 * 4 && /^(?:[A-Za-z0-9+/]{4})*$/.test(input.rgb_base64), 'Invalid canonical RGB8 base64.');
  const pixels = decodePixels(input as Input);
  check(pixels.length === 384 * 216 * 3, 'Input byte count differs.');
  const header = new TextEncoder().encode('{"dtype":"uint8","rank":3,"shape":[216,384,3],"version":"rgb-input/v1"}\n');
  const bytes = new Uint8Array(header.length + pixels.length); bytes.set(header); bytes.set(pixels, header.length);
  equal(input.sha256, await sha256(bytes), 'Input pixel hash');
  declaredHashes.add(input.sha256 as string);
  equal(metadata.input_sha256, [...declaredHashes].sort(), 'Metadata input hashes'); equal(metadata.input, { frame_id: 'options', ...input }, 'Metadata input');
  check(Array.isArray(item.segments) && item.segments.length >= 5 && item.segments.length <= 244, 'Expected bounded feed and four card observations.');
  const feed = item.segments.slice(0, -4), cards = item.segments.slice(-4);
  const recordedEnd = object(feed.at(-1), 'Final feed segment').source_end_tick;
  const T = validateVideoPhase(feed, videoInputs, groups, recordedEnd, { branchId: 'feed-event/root', startTick: 0, firstSequence: 1, clipCount: metadata.clips.length, fast: true });
  equal(item.feed_end_tick, T, 'Verified STOP time'); equal(item.duration_ticks, T + 20000, 'Duration');
  for (const raw of feed) {
    const segment = raw as VideoSegment;
    let cursor = segment.source_start_tick;
    for (const bin of segment.bins) {
      equal(bin.duration_ticks, Math.min(100, segment.source_end_tick - cursor), 'Native video bin duration');
      cursor = bin.end_tick;
    }
  }
  const finalCounts: MotorCounts = { motor_left: 0, motor_right: 0 };
  for (const [index, raw] of cards.entries()) {
    const segment = keys(raw, ['event_sequence', 'branch_id', 'frame_id', 'stimulation', 'learning', 'source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick', 'bins'], 'Segment');
    equal(segment.event_sequence, feed.length + index + 1, 'Observation sequence'); equal(segment.branch_id, 'feed-event/root', 'Branch'); equal(segment.frame_id, 'options', 'Frame'); equal(segment.stimulation, null, 'Stimulation'); equal(segment.learning, false, 'Learning');
    for (const clock of ['source_start_tick', 'playback_start_tick']) equal(segment[clock], T + index * 5000, clock);
    for (const clock of ['source_end_tick', 'playback_end_tick']) equal(segment[clock], T + (index + 1) * 5000, clock);
    check(Array.isArray(segment.bins) && segment.bins.length === 50, 'Expected exactly fifty recorded 10 ms bins per observation.');
    let end = T + index * 5000;
    for (const rawBin of segment.bins) {
      const bin = keys(rawBin, ['end_tick', 'duration_ticks', 'group_spikes'], 'Bin'); int(bin.end_tick, T + 1, T + 20000, 'Bin end'); int(bin.duration_ticks, 100, 100, 'Recorded bin duration');
      check(bin.end_tick - bin.duration_ticks === end && bin.end_tick <= T + (index + 1) * 5000, 'Bins must completely cover observation without gaps.'); end = bin.end_tick;
      const counts = keys(bin.group_spikes, GROUPS, 'Spike counts');
      for (const name of GROUPS) int(counts[name], 0, Math.min(Number.MAX_SAFE_INTEGER, (groups[name] as number) * bin.duration_ticks), `Count ${name}`);
      if (index === 3) for (const side of SIDES) { finalCounts[side] += counts[side] as number; int(finalCounts[side], 0, Number.MAX_SAFE_INTEGER, 'Final count'); }
    }
    equal(end, T + (index + 1) * 5000, 'Final bin end');
  }
  const decision = keys(item.decision, ['policy_version', 'effective_tick', 'event_sequence', 'event_scientific_sha256', 'window_start_tick', 'window_end_tick', 'counts', 'populations', 'readout', 'selected_option_id'], 'Decision');
  equal(decision.policy_version, 'event-card-choice/v1', 'Decision policy'); equal(decision.effective_tick, T + 20000, 'Decision time'); equal(decision.event_sequence, feed.length + 4, 'Decision event'); digest(decision.event_scientific_sha256, 'Decision event hash'); equal(decision.window_start_tick, T + 15000, 'Decision start'); equal(decision.window_end_tick, T + 20000, 'Decision end');
  equal(decision.counts, finalCounts, 'Final counts'); equal(decision.populations, { motor_left: groups.motor_left, motor_right: groups.motor_right }, 'Decision populations');
  const left = finalCounts.motor_left / ((groups.motor_left as number) * .5), right = finalCounts.motor_right / ((groups.motor_right as number) * .5);
  const difference = right - left, scale = Math.max(left, right), action = difference > 1 ? 'inspect_right' : difference < -1 ? 'inspect_left' : 'defer';
  const readout = keys(decision.readout, ['adapter_version', 'signed_difference_hz', 'evidence_strength', 'action'], 'Motor readout');
  equal(readout.adapter_version, 'lateral-motor-adapter/v1', 'Adapter'); equal(readout.action, action, 'Count-derived action');
  for (const [name, expected] of [['signed_difference_hz', difference], ['evidence_strength', scale ? Math.abs(difference / scale) / (right / scale + left / scale) : 0]] as const) {
    const actual = readout[name]; check(typeof actual === 'number' && Number.isFinite(actual) && actual === expected, `Readout ${name} differs from counts.`);
  }
  const selected = action === 'inspect_left' ? proposal.options[0] : action === 'inspect_right' ? proposal.options[1] : null;
  equal(decision.selected_option_id, selected?.id ?? null, 'Selected option ID');
  const planSource = Object.fromEntries(SOURCE_KEYS.map((name) => [name, source[name]]));
  equal(item.plan, { version: 'event-plan/v1', status: selected ? 'selected' : 'deferred', brief: proposal.brief, selected_option_id: selected?.id ?? null, selected_option: selected, decision_ref: { event_sequence: feed.length + 4, scientific_sha256: decision.event_scientific_sha256, input_sha256: input.sha256, policy_version: 'event-card-choice/v1' }, source: planSource }, 'Locked plan');
  check(new TextEncoder().encode(canonical(item.plan)).length <= 65536, 'Plan exceeds 64 KiB.');
  return item as unknown as SessionRecording;
}

export function sampleSessionAtTick(recording: SessionRecording, requestedTick: number) {
  check(Number.isFinite(requestedTick), 'Invalid seek position.');
  const tick = Math.max(0, Math.min(recording.duration_ticks, Math.floor(requestedTick)));
  if (tick < recording.feed_end_tick) {
    const segments = recording.segments.filter((segment): segment is VideoSegment => 'video_policy' in segment);
    const inputs = Object.fromEntries(Object.entries(recording.inputs).filter((entry): entry is [string, VideoInput] => 'clip_id' in entry[1]));
    return sampleVideoAtTick({ segments, inputs, groups: recording.groups, duration_ticks: recording.feed_end_tick }, tick);
  }
  const segment = recording.segments.find((candidate) => tick < candidate.playback_end_tick) ?? recording.segments.at(-1)!;
  check(!('video_policy' in segment), 'Expected card phase.');
  const sourceTick = tick, bin = segment.bins.find((candidate) => tick < candidate.end_tick) ?? segment.bins.at(-1)!;
  const rates = Object.fromEntries(GROUPS.map((name) => [name, bin.group_spikes[name] * 10000 / (recording.groups[name] * bin.duration_ticks)])) as Counts;
  const decision = tick >= recording.decision.effective_tick ? recording.decision : null;
  return { tick, sourceTick, segment, bin, rates, decisionTick: recording.decision.effective_tick, feedContext: `Feed ended at ${(recording.feed_end_tick / 10000).toFixed(3)} s · ${videoPolicyLabel((recording.segments.at(-5) as VideoSegment).video_policy)}`, decision, plan: decision ? recording.plan : null, leftOptionId: recording.source.metadata.proposal.options[0].id };
}
