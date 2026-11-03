import { GROUPS, decodePixels, type Bin, type Counts, type Input } from './replay.ts';

export type EventOption = { id: string; title: string; setting: 'rooftop' | 'warehouse'; music: string; budget_chf: number; capacity: number; duration_minutes: number; programme: Array<{ start_minute: number; label: string }> };
type Brief = { title: string; guests: number; max_budget_chf: number };
type Proposal = { version: 'event-options/v1'; brief: Brief; options: [EventOption, EventOption] };
type MotorCounts = { motor_left: number; motor_right: number };
type Readout = { adapter_version: 'lateral-motor-adapter/v1'; signed_difference_hz: number; evidence_strength: number; action: 'inspect_left' | 'inspect_right' | 'defer' };
type Source = { run_kind: 'pilot'; schema_sha256: string; run_metadata_sha256: string; events_sha256: string; final_scientific_sha256: string; verification_mode: 'integrity-only' };
export type EventPlan = { version: 'event-plan/v1'; status: 'selected' | 'deferred'; brief: Brief; selected_option_id: string | null; selected_option: EventOption | null; decision_ref: { event_sequence: number; scientific_sha256: string; input_sha256: string; policy_version: 'event-card-choice/v1' }; source: Source };
export type Decision = { policy_version: 'event-card-choice/v1'; effective_tick: number; event_sequence: number; event_scientific_sha256: string; window_start_tick: number; window_end_tick: number; counts: MotorCounts; populations: MotorCounts; readout: Readout; selected_option_id: string | null };
export type EventSegment = { event_sequence: number; branch_id: string; frame_id: 'options'; stimulation: null; learning: false; source_start_tick: number; source_end_tick: number; playback_start_tick: number; playback_end_tick: number; bins: Bin[] };
export type EventRecording = { version: 'event-choice-replay/v1'; tick_ms: .1; source: Source & { metadata: Record<string, unknown> & { proposal: Proposal } }; groups: Counts; inputs: { options: Input }; segments: EventSegment[]; duration_ticks: 20000; decision: Decision; plan: EventPlan };
export const EVENT_HOLD_FRAMES = 90;
const DIGEST = /^[0-9a-f]{64}$/;
const SOURCE_KEYS = ['run_kind', 'schema_sha256', 'run_metadata_sha256', 'events_sha256', 'final_scientific_sha256', 'verification_mode'];
const SIDES = ['motor_left', 'motor_right'] as const;
export function check(ok: unknown, message: string): asserts ok { if (!ok) throw new Error(message); }
export function object(value: unknown, path: string): Record<string, unknown> {
  check(value !== null && typeof value === 'object' && !Array.isArray(value), `${path}: expected object.`);
  return value as Record<string, unknown>;
}
export function keys(value: unknown, names: readonly string[], path: string) {
  const item = object(value, path);
  check(Object.keys(item).length === names.length && names.every((name) => Object.hasOwn(item, name)), `${path}: missing or unsupported fields.`);
  return item;
}
export function int(value: unknown, min: number, max: number, path: string): asserts value is number { check(typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max, `${path}: invalid integer.`); }
export function ascii(value: unknown, max: number, path: string): asserts value is string { check(typeof value === 'string' && value.length >= 1 && value.length <= max && /^[\x20-\x7e]+$/.test(value) && !/(?:[a-z][a-z0-9+.-]*:\/\/|www\.)/i.test(value), `${path}: expected printable ASCII text without URLs.`); }
export function digest(value: unknown, path: string) { check(typeof value === 'string' && DIGEST.test(value), `${path}: invalid SHA256.`); }
export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map((name) => `${JSON.stringify(name)}:${canonical((value as Record<string, unknown>)[name])}`).join(',')}}`;
  return JSON.stringify(value);
}
export function equal(a: unknown, b: unknown, path: string) { check(canonical(a) === canonical(b), `${path}: differs from bound evidence.`); }
export async function sha256(bytes: Uint8Array) { return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes as Uint8Array<ArrayBuffer>)), (byte) => byte.toString(16).padStart(2, '0')).join(''); }

export function strictJson(text: string): unknown {
  const value: unknown = JSON.parse(text), stack: Array<Set<string> | null> = [];
  const tokens = text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+/g) ?? [];
  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    if (token === '{' || token === '[') { stack.push(token === '{' ? new Set() : null); check(stack.length <= 64, 'Recording is nested too deeply.'); }
    else if (token === '}' || token === ']') stack.pop();
    else if (token.startsWith('"') && tokens[i + 1] === ':') {
      const name: string = JSON.parse(token), names = stack.at(-1);
      check(names && !names.has(name), `Duplicate JSON key: ${name}.`);
      check(!['__proto__', 'constructor', 'prototype'].includes(name), 'Unsupported object property.'); names.add(name);
    } else if (!token.startsWith('"') && ![',', ':', 'true', 'false', 'null'].includes(token)) check(Number.isFinite(Number(token)), 'Nonfinite JSON number.');
  }
  return value;
}

export function validateProposal(raw: unknown): Proposal {
  const proposal = keys(raw, ['version', 'brief', 'options'], 'Proposal'); equal(proposal.version, 'event-options/v1', 'Proposal version');
  const brief = keys(proposal.brief, ['title', 'guests', 'max_budget_chf'], 'Brief');
  ascii(brief.title, 48, 'Brief title'); int(brief.guests, 10, 500, 'Guests'); int(brief.max_budget_chf, 100, 100000, 'Maximum budget');
  check(Array.isArray(proposal.options) && proposal.options.length === 2, 'Exactly two event options required.');
  const ids = new Set();
  for (const rawOption of proposal.options) {
    const option = keys(rawOption, ['id', 'title', 'setting', 'music', 'budget_chf', 'capacity', 'duration_minutes', 'programme'], 'Option');
    check(typeof option.id === 'string' && /^[a-z][a-z0-9-]{0,31}$/.test(option.id) && !ids.has(option.id), 'Invalid or duplicate option ID.'); ids.add(option.id);
    ascii(option.title, 48, 'Option title'); ascii(option.music, 24, 'Music');
    check(option.setting === 'rooftop' || option.setting === 'warehouse', 'Unsupported scene setting.');
    int(option.budget_chf, 100, brief.max_budget_chf, 'Option budget'); int(option.capacity, brief.guests, 1000, 'Capacity'); int(option.duration_minutes, 60, 600, 'Duration');
    check(Array.isArray(option.programme) && option.programme.length >= 2 && option.programme.length <= 6, 'Programme requires 2–6 entries.');
    let minute = -1;
    for (const [index, rawEntry] of option.programme.entries()) {
      const entry = keys(rawEntry, ['start_minute', 'label'], 'Programme');
      int(entry.start_minute, 0, option.duration_minutes - 1, 'Start minute'); ascii(entry.label, 40, 'Programme label');
      check(entry.start_minute > minute && (index !== 0 || entry.start_minute === 0), 'Programme must begin at zero and increase.'); minute = entry.start_minute;
    }
  }
  return proposal as unknown as Proposal;
}

export function isEventRecording(value: { version: string }): value is EventRecording { return value.version === 'event-choice-replay/v1'; }

export async function parseEventRecording(text: string): Promise<EventRecording> {
  check(new TextEncoder().encode(text).length <= 2 * 1024 * 1024, 'Event recording exceeds 2 MiB.');
  const item = keys(strictJson(text), ['version', 'tick_ms', 'source', 'groups', 'inputs', 'segments', 'duration_ticks', 'decision', 'plan'], 'Event recording');
  equal(item.version, 'event-choice-replay/v1', 'Event version'); equal(item.tick_ms, .1, 'Tick size'); equal(item.duration_ticks, 20000, 'Duration');
  const source = keys(item.source, [...SOURCE_KEYS, 'metadata'], 'Source');
  check(source.run_kind === 'pilot' && source.verification_mode === 'integrity-only', 'Only integrity-only pilots are supported.');
  for (const name of SOURCE_KEYS.filter((name) => name.endsWith('_sha256'))) digest(source[name], `Source ${name}`);
  const metadata = keys(source.metadata, ['engine_identity', 'protocol_version', 'stimulus_version', 'family', 'seeds', 'factors', 'proposal', 'proposal_source', 'proposal_sha256', 'renderer_recipe', 'input', 'choice_recipe', 'input_sha256'], 'Metadata');
  equal(metadata.protocol_version, 'event-choice/v1', 'Protocol'); equal(metadata.stimulus_version, 'event-card-rgb/v1', 'Stimulus'); equal(metadata.family, 'event-choice', 'Family'); equal(metadata.seeds, [], 'Seeds');
  const proposal = validateProposal(metadata.proposal);
  const proposalHash = await sha256(new TextEncoder().encode(canonical(proposal)));
  equal(metadata.proposal_sha256, proposalHash, 'Proposal hash');
  const proposalSource = keys(metadata.proposal_source, ['kind', 'name', 'size_bytes', 'raw_sha256'], 'Proposal source');
  equal(proposalSource.kind, 'imported-json', 'Proposal source kind'); ascii(proposalSource.name, 80, 'Proposal source name');
  check(!/[\\/:]/.test(proposalSource.name) && proposalSource.name !== '.' && proposalSource.name !== '..', 'Proposal source must be a basename.');
  int(proposalSource.size_bytes, 1, 65536, 'Proposal source size'); digest(proposalSource.raw_sha256, 'Proposal source raw hash');
  equal(keys(metadata.factors, ['left_option_id', 'right_option_id'], 'Factors'), { left_option_id: proposal.options[0].id, right_option_id: proposal.options[1].id }, 'Frozen side mapping');
  equal(metadata.renderer_recipe, { version: 'event-cards/v1', pillow_version: '12.3.0', font: 'Pillow-load_default', font_size: 12, width: 384, height: 216 }, 'Renderer recipe');
  equal(metadata.choice_recipe, { policy_version: 'event-card-choice/v1', adapter_version: 'lateral-motor-adapter/v1', action_threshold_hz: 1, observation_count: 4, duration_ticks: 5000, settling_ticks: 15000, window_start_tick: 15000, window_end_tick: 20000, stimulation: null, learning: false, pathway_detail: false, qualification_detail: false }, 'Choice recipe');
  const groups = keys(item.groups, GROUPS, 'Groups'), maps = keys(object(metadata.engine_identity, 'Engine identity').neural_groups, GROUPS, 'Neural maps');
  for (const name of GROUPS) {
    int(groups[name], 1, Number.MAX_SAFE_INTEGER, `Population ${name}`);
    const map = maps[name]; check(Array.isArray(map) && map.length === groups[name], `Population ${name} differs from map.`);
    for (const cell of map) int(cell, 0, Number.MAX_SAFE_INTEGER, `Map ${name}`);
    check(new Set(map).size === map.length, `Map ${name} has duplicate cells.`);
  }
  const inputs = keys(item.inputs, ['options'], 'Inputs'), input = keys(inputs.options, ['sha256', 'width', 'height', 'rgb_base64'], 'Options input');
  equal(input.width, 384, 'Input width'); equal(input.height, 216, 'Input height'); digest(input.sha256, 'Input hash');
  check(typeof input.rgb_base64 === 'string' && input.rgb_base64.length === 384 * 216 * 4 && /^(?:[A-Za-z0-9+/]{4})*$/.test(input.rgb_base64), 'Invalid canonical RGB8 base64.');
  const pixels = decodePixels(input as Input);
  check(pixels.length === 384 * 216 * 3, 'Input byte count differs.');
  const header = new TextEncoder().encode('{"dtype":"uint8","rank":3,"shape":[216,384,3],"version":"rgb-input/v1"}\n');
  const bytes = new Uint8Array(header.length + pixels.length); bytes.set(header); bytes.set(pixels, header.length);
  equal(input.sha256, await sha256(bytes), 'Input pixel hash');
  equal(metadata.input_sha256, [input.sha256], 'Metadata input hashes'); equal(metadata.input, { frame_id: 'options', ...input }, 'Metadata input');
  check(Array.isArray(item.segments) && item.segments.length === 4, 'Exactly four observations required.');
  const finalCounts: MotorCounts = { motor_left: 0, motor_right: 0 };
  for (const [index, raw] of item.segments.entries()) {
    const segment = keys(raw, ['event_sequence', 'branch_id', 'frame_id', 'stimulation', 'learning', 'source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick', 'bins'], 'Segment');
    equal(segment.event_sequence, index + 1, 'Observation sequence'); equal(segment.branch_id, 'event-choice/root', 'Branch'); equal(segment.frame_id, 'options', 'Frame'); equal(segment.stimulation, null, 'Stimulation'); equal(segment.learning, false, 'Learning');
    for (const clock of ['source_start_tick', 'playback_start_tick']) equal(segment[clock], index * 5000, clock);
    for (const clock of ['source_end_tick', 'playback_end_tick']) equal(segment[clock], (index + 1) * 5000, clock);
    check(Array.isArray(segment.bins) && segment.bins.length === 50, 'Expected exactly fifty recorded 10 ms bins per observation.');
    let end = index * 5000;
    for (const rawBin of segment.bins) {
      const bin = keys(rawBin, ['end_tick', 'duration_ticks', 'group_spikes'], 'Bin'); int(bin.end_tick, 1, 20000, 'Bin end'); int(bin.duration_ticks, 100, 100, 'Recorded bin duration');
      check(bin.end_tick - bin.duration_ticks === end && bin.end_tick <= (index + 1) * 5000, 'Bins must completely cover observation without gaps.'); end = bin.end_tick;
      const counts = keys(bin.group_spikes, GROUPS, 'Spike counts');
      for (const name of GROUPS) int(counts[name], 0, Math.min(Number.MAX_SAFE_INTEGER, (groups[name] as number) * bin.duration_ticks), `Count ${name}`);
      if (index === 3) for (const side of SIDES) { finalCounts[side] += counts[side] as number; int(finalCounts[side], 0, Number.MAX_SAFE_INTEGER, 'Final count'); }
    }
    equal(end, (index + 1) * 5000, 'Final bin end');
  }
  const decision = keys(item.decision, ['policy_version', 'effective_tick', 'event_sequence', 'event_scientific_sha256', 'window_start_tick', 'window_end_tick', 'counts', 'populations', 'readout', 'selected_option_id'], 'Decision');
  equal(decision.policy_version, 'event-card-choice/v1', 'Decision policy'); equal(decision.effective_tick, 20000, 'Decision time'); equal(decision.event_sequence, 4, 'Decision event'); digest(decision.event_scientific_sha256, 'Decision event hash'); equal(decision.window_start_tick, 15000, 'Decision start'); equal(decision.window_end_tick, 20000, 'Decision end');
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
  equal(item.plan, { version: 'event-plan/v1', status: selected ? 'selected' : 'deferred', brief: proposal.brief, selected_option_id: selected?.id ?? null, selected_option: selected, decision_ref: { event_sequence: 4, scientific_sha256: decision.event_scientific_sha256, input_sha256: input.sha256, policy_version: 'event-card-choice/v1' }, source: planSource }, 'Locked plan');
  check(new TextEncoder().encode(canonical(item.plan)).length <= 65536, 'Plan exceeds 64 KiB.');
  return item as unknown as EventRecording;
}

export function sampleEventAtTick(recording: EventRecording, requestedTick: number) {
  check(Number.isFinite(requestedTick), 'Invalid seek position.');
  const tick = Math.max(0, Math.min(recording.duration_ticks, Math.floor(requestedTick)));
  const segment = recording.segments.find((segment) => tick < segment.playback_end_tick) ?? recording.segments.at(-1)!;
  const sourceTick = tick, bin = segment.bins.find((bin) => sourceTick < bin.end_tick) ?? segment.bins.at(-1)!;
  const rates = Object.fromEntries(GROUPS.map((name) => [name, bin.group_spikes[name] * 10000 / (recording.groups[name] * bin.duration_ticks)])) as Counts;
  const decision = tick >= recording.decision.effective_tick ? recording.decision : null;
  return { tick, sourceTick, segment, bin, rates, decisionTick: recording.decision.effective_tick, decision, plan: decision ? recording.plan : null, leftOptionId: recording.source.metadata.proposal.options[0].id };
}

export function eventPresentation(sample: ReturnType<typeof sampleEventAtTick> & { feedContext?: string }) {
  const option = sample.plan?.selected_option;
  return {
    status: !sample.decision ? `Choice pending · final 500 ms decision at ${(sample.decisionTick / 10000).toFixed(3)} s` : option ? 'Selected · engineered measured lateral policy' : 'Deferred · measured lateral difference stays within ±1 Hz/cell',
    title: option?.title ?? (sample.decision ? 'No option selected' : 'Waiting for the recorded decision'),
    selectedSide: option ? option.id === sample.leftOptionId ? 'left' as const : 'right' as const : null,
    canDownload: sample.plan !== null,
    lines: option && sample.plan ? [`${option.setting} · ${option.music}`, `CHF ${option.budget_chf} · ${sample.plan.brief.guests} guests · capacity ${option.capacity}`, `${option.duration_minutes} minutes`, ...option.programme.map((entry) => `${entry.start_minute} min · ${entry.label}`)] : [],
    measurement: [sample.decision ? `Final 500 ms · L ${sample.decision.counts.motor_left} / R ${sample.decision.counts.motor_right} spikes · Δ ${sample.decision.readout.signed_difference_hz.toFixed(2)} Hz/cell · ${sample.decision.readout.action}` : '', sample.feedContext].filter(Boolean).join(' · '),
  };
}
export function eventPlanJson(sample: ReturnType<typeof sampleEventAtTick>, operations?: { loading: boolean; exporting: boolean }): string | null {
  return sample.plan && !operations?.loading && !operations?.exporting ? JSON.stringify(sample.plan, null, 2) + '\n' : null;
}
