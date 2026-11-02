export const GROUPS = ['kc', 'pam11', 'ppl101', 'mbon07', 'mbon11', 'motor_left', 'motor_right'] as const;
export type Group = typeof GROUPS[number];
export type Counts = Record<Group, number>;
export type Stimulus = 'A' | 'B' | 'black';
export type Input = { sha256: string; width: number; height: number; rgb_base64: string };
export type Bin = { end_tick: number; duration_ticks: number; group_spikes: Counts };
export type Segment = {
  event_sequence: number; branch_id: string; stimulus: Stimulus; stimulation: null; learning: false;
  source_start_tick: number; source_end_tick: number; playback_start_tick: number; playback_end_tick: number; bins: Bin[];
};
export type Recording = {
  version: 'measured-replay/v1'; tick_ms: 0.1;
  source: { run_kind: 'pilot'; verification_mode: 'integrity-only'; schema_sha256: string; run_metadata_sha256: string; events_sha256: string; final_scientific_sha256: string; metadata: Record<string, unknown> };
  groups: Counts; inputs: Record<Stimulus, Input>; segments: Segment[]; duration_ticks: number;
};
export const MAX_FILE_BYTES = 8 * 1024 * 1024;
const DIGEST = /^[0-9a-f]{64}$/;

function requireValue(ok: unknown, message: string): asserts ok {
  if (!ok) throw new Error(message);
}
function object(value: unknown, path: string): Record<string, unknown> {
  requireValue(value !== null && typeof value === 'object' && !Array.isArray(value), `${path}: expected an object.`);
  return value as Record<string, unknown>;
}
function keys(value: unknown, expected: readonly string[], path: string): Record<string, unknown> {
  const item = object(value, path);
  requireValue(Object.keys(item).length === expected.length && expected.every((key) => Object.hasOwn(item, key)), `${path}: missing or unsupported fields.`);
  return item;
}
function integer(value: unknown, min: number, max: number, path: string): asserts value is number {
  requireValue(typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max, `${path}: expected an integer from ${min} to ${max}.`);
}

// JSON.parse validates syntax; this token walk also rejects duplicate keys and
// dangerous property names before any untrusted object is consumed.
function strictJson(text: string): unknown {
  const parsed: unknown = JSON.parse(text);
  const stack: Array<Set<string> | null> = [];
  const tokens = text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+/g) ?? [];
  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    if (token === '{' || token === '[') {
      stack.push(token === '{' ? new Set() : null);
      requireValue(stack.length <= 64, 'Recording is nested too deeply.');
    } else if (token === '}' || token === ']') stack.pop();
    else if (token.startsWith('"') && tokens[i + 1] === ':') {
      const key: string = JSON.parse(token);
      const names = stack.at(-1);
      requireValue(names && !names.has(key), `Duplicate JSON key: ${key}.`);
      requireValue(!['__proto__', 'prototype', 'constructor'].includes(key), 'Unsupported object property.');
      names.add(key);
    } else if (token !== ',' && token !== ':' && !token.startsWith('"') && !['null', 'true', 'false'].includes(token)) {
      requireValue(Number.isFinite(Number(token)), 'Nonfinite JSON number.');
    }
  }
  return parsed;
}

export function decodePixels(input: Input): Uint8Array {
  const raw = atob(input.rgb_base64);
  return Uint8Array.from(raw, (character) => character.charCodeAt(0));
}

async function validateInput(value: unknown, name: Stimulus): Promise<Input> {
  const item = keys(value, ['sha256', 'width', 'height', 'rgb_base64'], `inputs.${name}`);
  integer(item.width, 1, 1024, 'Image width'); integer(item.height, 1, 1024, 'Image height');
  requireValue(typeof item.sha256 === 'string' && DIGEST.test(item.sha256), 'Invalid input SHA256.');
  requireValue(typeof item.rgb_base64 === 'string' && /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(item.rgb_base64), 'Input pixels must be canonical base64 RGB8.');
  const input = item as Input;
  const pixels = decodePixels(input);
  requireValue(pixels.length === input.width * input.height * 3, 'RGB8 pixel count does not match image dimensions.');
  if (name === 'black') requireValue(pixels.every((channel) => channel === 0), 'Recorded black input contains nonblack pixels.');
  const header = new TextEncoder().encode(`{"dtype":"uint8","rank":3,"shape":[${input.height},${input.width},3],"version":"rgb-input/v1"}\n`);
  const hashInput = new Uint8Array(header.length + pixels.length);
  hashInput.set(header); hashInput.set(pixels, header.length);
  const hash = new Uint8Array(await crypto.subtle.digest('SHA-256', hashInput));
  requireValue(Array.from(hash, (byte) => byte.toString(16).padStart(2, '0')).join('') === input.sha256, `Input ${name}: pixel SHA256 does not match.`);
  return input;
}

export async function parseRecording(text: string): Promise<Recording> {
  requireValue(new TextEncoder().encode(text).length <= MAX_FILE_BYTES, 'Recording exceeds the 8 MiB limit. Export a shorter recording.');
  const item = keys(strictJson(text), ['version', 'tick_ms', 'source', 'groups', 'inputs', 'segments', 'duration_ticks'], 'Recording');
  requireValue(item.version === 'measured-replay/v1' && item.tick_ms === 0.1, 'Unsupported recording version or tick size. Use export-replay for measured-replay/v1.');
  const source = keys(item.source, ['run_kind', 'verification_mode', 'schema_sha256', 'run_metadata_sha256', 'events_sha256', 'final_scientific_sha256', 'metadata'], 'Source');
  requireValue(source.run_kind === 'pilot' && source.verification_mode === 'integrity-only', 'Only integrity-only pilot recordings are supported.');
  for (const field of ['schema_sha256', 'run_metadata_sha256', 'events_sha256', 'final_scientific_sha256']) requireValue(typeof source[field] === 'string' && DIGEST.test(source[field]), `Invalid source ${field}.`);
  const metadata = object(source.metadata, 'Source metadata');
  requireValue(metadata.family === 'measured-observation' && metadata.protocol_version === 'measured-observation/v1', 'Unsupported observation family or protocol.');
  const identity = object(metadata.engine_identity, 'Engine identity');
  const maps = object(identity.neural_groups, 'Recorded neural-group maps');
  const groups = keys(item.groups, GROUPS, 'Groups');
  for (const name of GROUPS) {
    integer(groups[name], 1, Number.MAX_SAFE_INTEGER, `Population ${name}`);
    requireValue(Array.isArray(maps[name]) && (maps[name] as unknown[]).length === groups[name], `Population ${name} does not match its recorded map.`);
    for (const index of maps[name] as unknown[]) integer(index, 0, Number.MAX_SAFE_INTEGER, `Map ${name}`);
    requireValue(new Set(maps[name] as unknown[]).size === groups[name], `Recorded map ${name} contains duplicate cells.`);
  }
  const rawInputs = keys(item.inputs, ['A', 'B', 'black'], 'Inputs');
  const inputs = await Promise.all((['A', 'B', 'black'] as const).map((name) => validateInput(rawInputs[name], name)));
  requireValue(inputs.every((input) => input.width === inputs[0].width && input.height === inputs[0].height), 'Input dimensions differ.');
  requireValue(Array.isArray(metadata.input_sha256) && inputs.every((input) => (metadata.input_sha256 as unknown[]).includes(input.sha256)), 'Input hashes are absent from the recorded metadata.');
  requireValue(Array.isArray(item.segments) && item.segments.length > 0 && item.segments.length <= 40 && item.segments.length % 4 === 0, 'Expected 1–10 complete A/black/B/black cycles (at most 40 segments).');
  integer(item.duration_ticks, 1, 200000, 'Recording duration');
  let playbackEnd = 0, sourceEnd = -1, sequence = -1, binCount = 0;
  let branch: string | undefined;
  for (const [index, raw] of item.segments.entries()) {
    const segment = keys(raw, ['event_sequence', 'branch_id', 'stimulus', 'stimulation', 'learning', 'source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick', 'bins'], `Segment ${index}`);
    integer(segment.event_sequence, 0, Number.MAX_SAFE_INTEGER, 'Event sequence');
    requireValue(segment.event_sequence > sequence, 'Events are reordered or duplicated.'); sequence = segment.event_sequence;
    requireValue(typeof segment.branch_id === 'string' && segment.branch_id.length > 0 && segment.branch_id.length <= 256, 'Invalid branch ID.');
    branch ??= segment.branch_id;
    requireValue(segment.branch_id === branch, 'Forked recordings are not supported.');
    requireValue(segment.stimulus === ['A', 'black', 'B', 'black'][index % 4] && segment.stimulation === null && segment.learning === false, 'Unsupported stimulus order, external stimulation or learning flags.');
    for (const key of ['source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick']) integer(segment[key], 0, Number.MAX_SAFE_INTEGER, key);
    const s = segment as unknown as Segment;
    const duration = s.source_end_tick - s.source_start_tick;
    requireValue(duration > 0 && duration <= 5000 && s.playback_start_tick === playbackEnd && s.playback_end_tick - s.playback_start_tick === duration, 'Inconsistent playback/source interval.');
    requireValue(sourceEnd < 0 || s.source_start_tick === sourceEnd, 'Source clocks are discontinuous or rewind.');
    sourceEnd = s.source_end_tick; playbackEnd = s.playback_end_tick;
    requireValue(Array.isArray(s.bins) && s.bins.length > 0 && (binCount += s.bins.length) <= 2000, 'Missing bins or recording exceeds 2000 bins.');
    let end = s.source_start_tick;
    for (const rawBin of s.bins) {
      const bin = keys(rawBin, ['end_tick', 'duration_ticks', 'group_spikes'], 'Bin');
      integer(bin.end_tick, 1, Number.MAX_SAFE_INTEGER, 'Bin end'); integer(bin.duration_ticks, 1, 5000, 'Bin duration');
      requireValue(bin.end_tick - bin.duration_ticks === end && bin.end_tick <= s.source_end_tick, 'Bins must completely and contiguously cover each observation.');
      end = bin.end_tick;
      const counts = keys(bin.group_spikes, GROUPS, 'Bin counts');
      for (const name of GROUPS) integer(counts[name], 0, Math.min(Number.MAX_SAFE_INTEGER, (groups[name] as number) * bin.duration_ticks), `Spike count ${name}`);
    }
    requireValue(end === s.source_end_tick, 'Incomplete bin coverage.');
  }
  requireValue(playbackEnd === item.duration_ticks, 'Recording duration does not match the intervals.');
  return item as unknown as Recording;
}

export function sampleAtTick(recording: Recording, requestedTick: number) {
  requireValue(Number.isFinite(requestedTick), 'Invalid seek position.');
  const tick = Math.max(0, Math.min(recording.duration_ticks, Math.floor(requestedTick)));
  const segment = recording.segments.find((candidate) => tick < candidate.playback_end_tick) ?? recording.segments.at(-1)!;
  const sourceTick = segment.source_start_tick + tick - segment.playback_start_tick;
  const bin = segment.bins.find((candidate) => sourceTick < candidate.end_tick) ?? segment.bins.at(-1)!;
  const rates = Object.fromEntries(GROUPS.map((name) => [name, bin.group_spikes[name] * 10000 / (recording.groups[name] * bin.duration_ticks)])) as Counts;
  return { tick, sourceTick, segment, bin, rates };
}

export function advancePlayback(tick: number, elapsedMs: number, speed: number, playing: boolean, duration: number) {
  requireValue([tick, elapsedMs, speed, duration].every(Number.isFinite) && elapsedMs >= 0 && speed > 0 && duration > 0, 'Invalid playback timing.');
  const next = Math.max(0, Math.min(duration, tick + (playing ? elapsedMs * 10 * speed : 0)));
  return { tick: next, playing: playing && next < duration };
}
