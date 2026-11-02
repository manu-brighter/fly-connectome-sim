import { GROUPS, parseRecording, type Bin, type Counts, type Input, type Recording } from './replay.ts';
import { quantizeVideoTick } from './export.ts';

export type VideoInput = Input & { clip_id: string; frame_index: number; source_pts: number; source_time_base: [number, number] };
export type VideoPolicy = {
  policy_version: 'right-scroll/v1' | 'right-scroll/v2'; effective_tick: number;
  window: null | { start_tick: number; end_tick: number; frame_count: 9; counts: { motor_left: number; motor_right: number }; populations: { motor_left: number; motor_right: number } };
  readout: null | { adapter_version: 'lateral-motor-adapter/v1'; signed_difference_hz: number; evidence_strength: number; action: 'inspect_left' | 'inspect_right' | 'defer' };
  minimum_dwell_met: boolean; action: 'watch' | 'advance' | 'stop';
  reason: 'minimum_dwell' | 'motor_left_or_defer' | 'motor_right' | 'clip_window_end' | 'playlist_exhausted' | 'session_limit';
  trigger: null | 'motor_right' | 'clip_window_end' | 'session_limit'; next_clip_index: number | null;
};
export type VideoSegment = {
  event_sequence: number; branch_id: string; frame_id: string; clip_id: string; frame_index: number;
  stimulation: null; learning: false; source_start_tick: number; source_end_tick: number;
  playback_start_tick: number; playback_end_tick: number; bins: Bin[]; video_policy: VideoPolicy | null;
};
export type VideoRecording = Omit<Recording, 'version' | 'inputs' | 'segments'> & {
  version: 'measured-video-replay/v1' | 'measured-video-replay/v2'; inputs: Record<string, VideoInput>; segments: VideoSegment[];
};

export function isVideoRecording(recording: { version: string }): recording is VideoRecording {
  return recording.version === 'measured-video-replay/v1' || recording.version === 'measured-video-replay/v2';
}
export function videoSpeedLabel(recording: { version: string }) {
  return recording.version === 'measured-video-replay/v2' ? 'Reel 5×' : 'Reel 1×';
}

export function videoPlaneHeight(width: number, inputWidth: number, inputHeight: number) { return width * inputHeight / inputWidth; }
export function videoInputLabel(input: Pick<VideoInput, 'clip_id' | 'frame_index'>) {
  const index = Number(input.clip_id.slice(5));
  return `Clip ${index + 1} · frame ${input.frame_index + 1}`;
}
export function videoPolicyLabel(policy: VideoPolicy | null) {
  if (!policy) return 'No policy evaluation yet';
  if (policy.action === 'advance') return `ADVANCE · ${policy.reason === 'motor_right' ? 'motor readout' : 'clip window end'}`;
  if (policy.action === 'stop') return `END · ${policy.reason.replaceAll('_', ' ')}${policy.reason === 'playlist_exhausted' ? ` (${policy.trigger?.replaceAll('_', ' ')})` : ''}`;
  return `WATCH · ${policy.reason === 'minimum_dwell' ? 'minimum dwell' : 'no right advance'}`;
}
export function videoTimelineBlocks(recording: { segments: Array<Pick<VideoSegment, 'clip_id' | 'playback_start_tick' | 'playback_end_tick'>> }) {
  const blocks: Array<{ clipId: string; duration: number }> = [];
  for (const segment of recording.segments) {
    const duration = segment.playback_end_tick - segment.playback_start_tick;
    const last = blocks.at(-1);
    if (last?.clipId === segment.clip_id) last.duration += duration;
    else blocks.push({ clipId: segment.clip_id, duration });
  }
  return blocks;
}
export async function parseAnyRecording(text: string): Promise<Recording | VideoRecording> {
  check(new TextEncoder().encode(text).length <= 32 * 1024 * 1024, 'Recording exceeds 32 MiB.');
  const value = JSON.parse(text) as { version?: unknown };
  return value?.version === 'measured-video-replay/v1' || value?.version === 'measured-video-replay/v2' ? parseVideoRecording(text) : parseRecording(text);
}

const DIGEST = /^[0-9a-f]{64}$/;
const BASE64 = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
function check(ok: unknown, message: string): asserts ok { if (!ok) throw new Error(message); }
function object(value: unknown, path: string): Record<string, unknown> {
  check(value !== null && typeof value === 'object' && !Array.isArray(value), `${path}: expected object.`);
  return value as Record<string, unknown>;
}
function keys(value: unknown, names: readonly string[], path: string) {
  const result = object(value, path);
  check(Object.keys(result).length === names.length && names.every((name) => Object.hasOwn(result, name)), `${path}: missing or unsupported fields.`);
  return result;
}
function int(value: unknown, min: number, max: number, path: string): asserts value is number {
  check(typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max, `${path}: invalid integer.`);
}
function rational(value: unknown, path: string): [number, number] {
  check(Array.isArray(value) && value.length === 2, `${path}: invalid time base.`);
  int(value[0], 1, Number.MAX_SAFE_INTEGER, path); int(value[1], 1, Number.MAX_SAFE_INTEGER, path);
  return value as [number, number];
}
function equal(a: unknown, b: unknown, path: string) { check(JSON.stringify(a) === JSON.stringify(b), `${path}: recorded value differs from prepared evidence.`); }
function strictJson(text: string): unknown {
  const parsed: unknown = JSON.parse(text), stack: Array<Set<string> | null> = [];
  const tokens = text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+/g) ?? [];
  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    if (token === '{' || token === '[') { stack.push(token === '{' ? new Set() : null); check(stack.length <= 64, 'Recording is nested too deeply.'); }
    else if (token === '}' || token === ']') stack.pop();
    else if (token.startsWith('"') && tokens[i + 1] === ':') {
      const key: string = JSON.parse(token), names = stack.at(-1);
      check(names && !names.has(key), `Duplicate JSON key: ${key}.`);
      check(!['__proto__', 'prototype', 'constructor'].includes(key), 'Unsupported object property.');
      names.add(key);
    } else if (token !== ',' && token !== ':' && !token.startsWith('"') && !['null', 'true', 'false'].includes(token)) check(Number.isFinite(Number(token)), 'Nonfinite JSON number.');
  }
  return parsed;
}

function validateRecipe(raw: unknown, fast: boolean) {
  const expected = { policy_version: fast ? 'right-scroll/v2' : 'right-scroll/v1', adapter_version: 'lateral-motor-adapter/v1', action_threshold_hz: 1, sample_fps: [30, 1], sample_time_origin: 'first-decoded-pts', tick_quantization: 'nearest-0.1ms-half-up-cumulative/v1', window_ticks: 40000, session_limit_ticks: 80000, rolling_window_ticks: 3000, minimum_dwell_ticks: fast ? 30000 : 10000, input_width: 90, input_height: 160, audio_input: false, stimulation: null, learning: false, pathway_detail: false, qualification_detail: false, ...(fast ? { source_speed: [5, 1], source_window_seconds: 20 } : {}) };
  const recipe = keys(raw, Object.keys(expected), 'Video recipe');
  for (const [name, value] of Object.entries(expected)) equal(recipe[name], value, `Video recipe ${name}`);
}

function expectedTransform(sourceWidth: number, sourceHeight: number) {
  const scaleWidth = 90 * sourceHeight <= 160 * sourceWidth;
  const numerator = scaleWidth ? 90 : 160, denominator = scaleWidth ? sourceWidth : sourceHeight;
  const innerWidth = Math.floor((2 * sourceWidth * numerator + denominator) / (2 * denominator));
  const innerHeight = Math.floor((2 * sourceHeight * numerator + denominator) / (2 * denominator));
  const left = Math.floor((90 - innerWidth) / 2), top = Math.floor((160 - innerHeight) / 2);
  return { width: 90, height: 160, inner_width: innerWidth, inner_height: innerHeight, padding: [left, top, 90 - innerWidth - left, 160 - innerHeight - top], resize: 'bilinear', placement: 'centered-black-letterbox', pixel_format: 'rgb24', color_conversion: 'PyAV-to_ndarray-rgb24-FFmpeg-defaults', crop: 'none', orientation: 'reject-rotation-and-displaymatrix/v1' };
}

function checkPolicy(raw: unknown, expected: VideoPolicy) {
  const policy = keys(raw, ['policy_version', 'effective_tick', 'window', 'readout', 'minimum_dwell_met', 'action', 'reason', 'trigger', 'next_clip_index'], 'Video policy');
  for (const name of ['policy_version', 'effective_tick', 'minimum_dwell_met', 'action', 'reason', 'trigger', 'next_clip_index']) equal(policy[name], expected[name as keyof VideoPolicy], `Video policy ${name}`);
  if (expected.window === null) check(policy.window === null && policy.readout === null, 'Readout before complete 300ms coverage.');
  else {
    const window = keys(policy.window, ['start_tick', 'end_tick', 'frame_count', 'counts', 'populations'], 'Policy window');
    for (const name of ['start_tick', 'end_tick', 'frame_count']) equal(window[name], expected.window[name as keyof typeof expected.window], `Policy window ${name}`);
    const counts = keys(window.counts, ['motor_left', 'motor_right'], 'Policy counts');
    const populations = keys(window.populations, ['motor_left', 'motor_right'], 'Policy populations');
    for (const side of ['motor_left', 'motor_right'] as const) { equal(counts[side], expected.window.counts[side], `Policy ${side} count`); equal(populations[side], expected.window.populations[side], `Policy ${side} population`); }
    const readout = keys(policy.readout, ['adapter_version', 'signed_difference_hz', 'evidence_strength', 'action'], 'Policy readout');
    equal(readout.adapter_version, expected.readout!.adapter_version, 'Adapter version'); equal(readout.action, expected.readout!.action, 'Adapter action');
    for (const name of ['signed_difference_hz', 'evidence_strength'] as const) {
      const value = readout[name], target = expected.readout![name];
      check(typeof value === 'number' && Number.isFinite(value) && Math.abs(value - target) <= 1e-10 * Math.max(1, Math.abs(target)), `Policy ${name} does not match measured counts.`);
    }
  }
}

function expectedPolicy(end: number, frameIndex: number, clipIndex: number, clipCount: number, clipStart: number, motorFrames: Array<{ motor_left: number; motor_right: number }>, populations: { motor_left: number; motor_right: number }, fast: boolean): VideoPolicy {
  const windowCounts = { motor_left: 0, motor_right: 0 };
  if (frameIndex >= 8) for (const row of motorFrames.slice(-9)) { windowCounts.motor_left += row.motor_left; windowCounts.motor_right += row.motor_right; }
  const window: VideoPolicy['window'] = frameIndex < 8 ? null : { start_tick: end - 3000, end_tick: end, frame_count: 9, counts: windowCounts, populations };
  let readout: VideoPolicy['readout'] = null;
  if (window) {
    const left = windowCounts.motor_left / (populations.motor_left * .3), right = windowCounts.motor_right / (populations.motor_right * .3);
    const diff = right - left, scale = Math.max(left, right);
    readout = { adapter_version: 'lateral-motor-adapter/v1', signed_difference_hz: diff, evidence_strength: scale ? Math.abs(diff / scale) / (right / scale + left / scale) : 0, action: diff > 1 ? 'inspect_right' : diff < -1 ? 'inspect_left' : 'defer' };
  }
  const minimum_dwell_met = end - clipStart >= (fast ? 30000 : 10000);
  let action: VideoPolicy['action'], reason: VideoPolicy['reason'], trigger: VideoPolicy['trigger'], next_clip_index: number | null;
  if (end === 80000) { action = 'stop'; reason = 'session_limit'; trigger = 'session_limit'; next_clip_index = null; }
  else {
    trigger = frameIndex === 119 ? 'clip_window_end' : minimum_dwell_met && readout?.action === 'inspect_right' ? 'motor_right' : null;
    if (trigger === null) { action = 'watch'; reason = minimum_dwell_met ? 'motor_left_or_defer' : 'minimum_dwell'; next_clip_index = clipIndex; }
    else if (clipIndex + 1 === clipCount) { action = 'stop'; reason = 'playlist_exhausted'; next_clip_index = null; }
    else { action = 'advance'; reason = trigger; next_clip_index = clipIndex + 1; }
  }
  return { policy_version: fast ? 'right-scroll/v2' : 'right-scroll/v1', effective_tick: end, window, readout, minimum_dwell_met, action, reason, trigger, next_clip_index };
}

export async function parseVideoRecording(text: string): Promise<VideoRecording> {
  check(new TextEncoder().encode(text).length <= 32 * 1024 * 1024, 'Video recording exceeds 32 MiB.');
  const item = keys(strictJson(text), ['version', 'tick_ms', 'source', 'groups', 'inputs', 'segments', 'duration_ticks'], 'Video recording');
  check((item.version === 'measured-video-replay/v1' || item.version === 'measured-video-replay/v2') && item.tick_ms === .1, 'Unsupported video replay version or tick size.');
  const fast = item.version === 'measured-video-replay/v2';
  const source = keys(item.source, ['run_kind', 'verification_mode', 'schema_sha256', 'run_metadata_sha256', 'events_sha256', 'final_scientific_sha256', 'metadata'], 'Source');
  check(source.run_kind === 'pilot' && source.verification_mode === 'integrity-only', 'Only integrity-only pilot video recordings are supported.');
  for (const name of ['schema_sha256', 'run_metadata_sha256', 'events_sha256', 'final_scientific_sha256']) check(typeof source[name] === 'string' && DIGEST.test(source[name]), `Invalid source ${name}.`);
  const metadata = keys(source.metadata, ['engine_identity', 'protocol_version', 'stimulus_version', 'family', 'seeds', 'factors', 'video_recipe', 'clips', 'input_sha256'], 'Metadata');
  check(metadata.family === 'video-observation' && metadata.protocol_version === `video-observation/v${fast ? 2 : 1}` && metadata.stimulus_version === `decoded-video-rgb/v${fast ? 2 : 1}`, 'Unsupported video observation protocol.');
  validateRecipe(metadata.video_recipe, fast);
  const identity = object(metadata.engine_identity, 'Engine identity'), maps = object(identity.neural_groups, 'Neural-group maps');
  const groups = keys(item.groups, GROUPS, 'Groups');
  for (const name of GROUPS) {
    int(groups[name], 1, Number.MAX_SAFE_INTEGER, `Population ${name}`);
    check(Array.isArray(maps[name]) && maps[name].length === groups[name], `Population ${name} differs from recorded map.`);
    for (const id of maps[name]) int(id, 0, Number.MAX_SAFE_INTEGER, `Map ${name}`);
    check(new Set(maps[name]).size === groups[name], `Duplicate map entry for ${name}.`);
  }
  check(Array.isArray(metadata.clips) && metadata.clips.length >= 1 && metadata.clips.length <= 5, 'Expected 1–5 prepared clips.');
  equal(metadata.seeds, [], 'Video seeds'); equal(metadata.factors, { clip_count: metadata.clips.length }, 'Video factors');
  const prepared = new Map<string, { clip_id: string; frame_index: number; sha256: string; source_pts: number; source_time_base: [number, number] }>();
  const declaredHashes = new Set<string>();
  for (const [clipIndex, rawClip] of metadata.clips.entries()) {
    const clip = keys(rawClip, ['clip_id', 'source_url', 'source_path', 'source_sha256', 'source_size', 'source_width', 'source_height', 'source_sample_aspect_ratio', 'source_time_base', 'origin_pts', 'coverage_end_pts', 'coverage_method', 'decoder', 'transform', 'frames'], `Clip ${clipIndex}`);
    const clipId = `clip-${clipIndex}`;
    check(clip.clip_id === clipId && typeof clip.source_url === 'string' && /^https:\/\//.test(clip.source_url) && typeof clip.source_sha256 === 'string' && DIGEST.test(clip.source_sha256), 'Invalid clip identity or source provenance.');
    int(clip.source_size, 1, 512 * 1024 * 1024, 'Source size'); int(clip.source_width, 1, 8192, 'Source width'); int(clip.source_height, 1, 8192, 'Source height');
    check(JSON.stringify(clip.source_sample_aspect_ratio) === '[0,1]' || JSON.stringify(clip.source_sample_aspect_ratio) === '[1,1]', 'Unsupported source pixel aspect ratio.');
    const base = rational(clip.source_time_base, 'Clip time base'); int(clip.origin_pts, Number.MIN_SAFE_INTEGER, Number.MAX_SAFE_INTEGER, 'Origin PTS'); int(clip.coverage_end_pts, Number.MIN_SAFE_INTEGER, Number.MAX_SAFE_INTEGER, 'Coverage PTS');
    check((clip.coverage_end_pts - clip.origin_pts) * base[0] >= (fast ? 20 : 4) * base[1] && typeof clip.source_path === 'string' && clip.source_path.length > 0, 'Invalid clip coverage or path label.');
    check(clip.coverage_method === 'following_pts' || clip.coverage_method === 'final_frame_duration', 'Unknown source coverage method.');
    const decoder = keys(clip.decoder, ['pyav_version', 'ffmpeg_libraries'], 'Decoder');
    check(decoder.pyav_version === '19.0.2', 'Unsupported decoder declaration.');
    const libraries = object(decoder.ffmpeg_libraries, 'FFmpeg libraries');
    check(Object.keys(libraries).length > 0, 'Missing FFmpeg library versions.');
    for (const [name, version] of Object.entries(libraries)) {
      check(/^lib(av|sw)/.test(name) && Array.isArray(version) && version.length === 3, 'Invalid FFmpeg library version.');
      for (const part of version) int(part, 0, Number.MAX_SAFE_INTEGER, 'FFmpeg version part');
    }
    const transform = keys(clip.transform, ['width', 'height', 'inner_width', 'inner_height', 'padding', 'resize', 'placement', 'pixel_format', 'color_conversion', 'crop', 'orientation'], 'Transform');
    for (const [name, value] of Object.entries(expectedTransform(clip.source_width, clip.source_height))) equal(transform[name], value, `Transform ${name}`);
    check(Array.isArray(clip.frames) && clip.frames.length === 120, 'Prepared clip must declare 120 frames.');
    let previousPts: number | null = null;
    for (const [index, rawFrame] of clip.frames.entries()) {
      const frame = keys(rawFrame, ['frame_id', 'frame_index', 'sha256', 'source_pts', 'source_time_base'], `Prepared frame ${index}`);
      check(frame.frame_id === `${clipId}/frame-${index}` && frame.frame_index === index && typeof frame.sha256 === 'string' && DIGEST.test(frame.sha256), 'Invalid prepared frame identity.');
      int(frame.source_pts, Number.MIN_SAFE_INTEGER, Number.MAX_SAFE_INTEGER, 'Prepared frame PTS');
      check((previousPts === null ? frame.source_pts === clip.origin_pts : frame.source_pts >= previousPts) && (frame.source_pts - clip.origin_pts) * base[0] * 30 <= (fast ? 5 : 1) * index * base[1], 'Prepared frame PTS differs from source sampling.'); previousPts = frame.source_pts;
      equal(rational(frame.source_time_base, 'Prepared frame time base'), base, 'Prepared frame time base');
      declaredHashes.add(frame.sha256 as string);
      prepared.set(frame.frame_id as string, { clip_id: clipId, frame_index: index, sha256: frame.sha256 as string, source_pts: frame.source_pts, source_time_base: base });
    }
  }
  equal(metadata.input_sha256, [...declaredHashes].sort(), 'Prepared RGB hash set');
  const rawInputs = object(item.inputs, 'Inputs');
  check(Object.keys(rawInputs).length >= 1 && Object.keys(rawInputs).length <= 240, 'Video input count exceeds bounds.');
  for (const [frameId, raw] of Object.entries(rawInputs)) {
    const input = keys(raw, ['sha256', 'width', 'height', 'rgb_base64', 'clip_id', 'frame_index', 'source_pts', 'source_time_base'], `Input ${frameId}`);
    const declared = prepared.get(frameId);
    check(declared && input.width === 90 && input.height === 160, `Input ${frameId} was not prepared as 90×160 RGB.`);
    for (const name of ['sha256', 'clip_id', 'frame_index', 'source_pts']) equal(input[name], declared[name as keyof typeof declared], `Input ${frameId} ${name}`);
    equal(rational(input.source_time_base, 'Input time base'), declared.source_time_base, `Input ${frameId} time base`);
    check(typeof input.rgb_base64 === 'string' && BASE64.test(input.rgb_base64) && input.rgb_base64.length <= 57600, 'Invalid canonical RGB base64.');
    const pixels = Uint8Array.from(atob(input.rgb_base64), (character) => character.charCodeAt(0));
    check(pixels.length === 90 * 160 * 3, 'Incorrect RGB pixel count.');
    const header = new TextEncoder().encode('{"dtype":"uint8","rank":3,"shape":[160,90,3],"version":"rgb-input/v1"}\n');
    const bytes = new Uint8Array(header.length + pixels.length); bytes.set(header); bytes.set(pixels, header.length);
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), (byte) => byte.toString(16).padStart(2, '0')).join('');
    check(digest === input.sha256, `Input ${frameId}: pixel SHA256 mismatch.`);
  }
  check(Array.isArray(item.segments) && item.segments.length >= 1 && item.segments.length <= 240, 'Video segment count exceeds bounds.');
  const populations = { motor_left: groups.motor_left as number, motor_right: groups.motor_right as number };
  let tick = 0, sequence = -1, clipIndex = 0, frameIndex = 0, clipStart = 0, binCount = 0, stopped = false;
  let motorFrames: Array<{ motor_left: number; motor_right: number }> = [];
  const used = new Set<string>();
  for (const [index, rawSegment] of item.segments.entries()) {
    const segment = keys(rawSegment, ['event_sequence', 'branch_id', 'frame_id', 'clip_id', 'frame_index', 'stimulation', 'learning', 'source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick', 'bins', 'video_policy'], `Segment ${index}`);
    int(segment.event_sequence, 0, Number.MAX_SAFE_INTEGER, 'Event sequence'); check(segment.event_sequence === index + 1 && segment.event_sequence > sequence, 'Events are reordered, missing or repeated.'); sequence = segment.event_sequence;
    check(segment.branch_id === 'video-observation/root' && segment.stimulation === null && segment.learning === false, 'Unsupported branch, external stimulation or learning.');
    check(segment.clip_id === `clip-${clipIndex}` && segment.frame_index === frameIndex && segment.frame_id === `${segment.clip_id}/frame-${frameIndex}`, 'Video frame occurrence differs from recorded policy.');
    check(Object.hasOwn(rawInputs, segment.frame_id as string), 'Segment frame has no exact input.'); used.add(segment.frame_id as string);
    const end = tick + quantizeVideoTick(frameIndex + 1) - quantizeVideoTick(frameIndex);
    check(segment.source_start_tick === tick && segment.playback_start_tick === tick && segment.source_end_tick === end && segment.playback_end_tick === end, 'Video source/playback clock or frame duration mismatch.');
    check(Array.isArray(segment.bins) && segment.bins.length > 0 && segment.bins.length <= 4 && (binCount += segment.bins.length) <= 960, 'Missing or excessive video bins.');
    let binStart = tick; const motor = { motor_left: 0, motor_right: 0 };
    for (const rawBin of segment.bins) {
      const bin = keys(rawBin, ['end_tick', 'duration_ticks', 'group_spikes'], 'Video bin');
      int(bin.end_tick, 1, 80000, 'Bin end'); int(bin.duration_ticks, 1, 100, 'Bin duration');
      check(bin.end_tick - bin.duration_ticks === binStart && bin.end_tick <= end, 'Video bins are not contiguous.'); binStart = bin.end_tick;
      const spikes = keys(bin.group_spikes, GROUPS, 'Video bin counts');
      for (const name of GROUPS) int(spikes[name], 0, Math.min(Number.MAX_SAFE_INTEGER, (groups[name] as number) * bin.duration_ticks), `Spike count ${name}`);
      motor.motor_left += spikes.motor_left as number; motor.motor_right += spikes.motor_right as number;
    }
    check(binStart === end, 'Video bins do not cover the observation.'); motorFrames.push(motor);
    tick = end;
    if (frameIndex % 3 === 2) {
      const expected = expectedPolicy(end, frameIndex, clipIndex, metadata.clips.length, clipStart, motorFrames, populations, fast);
      checkPolicy(segment.video_policy, expected);
      if (expected.action === 'advance') { clipIndex += 1; frameIndex = 0; clipStart = end; motorFrames = []; }
      else if (expected.action === 'stop') { stopped = true; check(index === item.segments.length - 1, 'Frames follow recorded stop.'); }
      else frameIndex += 1;
    } else { check(segment.video_policy === null, 'Policy decision appears before evaluation boundary.'); frameIndex += 1; }
  }
  int(item.duration_ticks, 1, 80000, 'Video duration');
  check(stopped && tick === item.duration_ticks, 'Video session lacks a complete recorded stop.');
  check(used.size === Object.keys(rawInputs).length, 'Unused or unbound video input.');
  return item as unknown as VideoRecording;
}

export function visiblePolicyAtTick(recording: VideoRecording, tick: number): VideoPolicy | null {
  return recording.segments.findLast((segment) => segment.video_policy !== null && segment.video_policy.effective_tick <= tick)?.video_policy ?? null;
}

export function currentClipPolicyAtTick(recording: VideoRecording, tick: number, clipId: string): VideoPolicy | null {
  return recording.segments.findLast((segment) => segment.clip_id === clipId && segment.video_policy !== null && segment.video_policy.effective_tick <= tick)?.video_policy ?? null;
}

export function advanceGestureAtTick(recording: VideoRecording, tick: number, reducedMotion = false) {
  if (reducedMotion || visiblePolicyAtTick(recording, tick)?.action === 'stop') return null;
  const outgoing = recording.segments.findLast((segment) => segment.video_policy?.action === 'advance' && segment.video_policy.effective_tick <= tick);
  const policy = outgoing?.video_policy;
  if (!outgoing || !policy || tick >= policy.effective_tick + 4000) return null;
  const incoming = recording.segments.find((segment) => segment.playback_start_tick <= tick && tick < segment.playback_end_tick);
  if (!incoming || incoming.clip_id === outgoing.clip_id) return null;
  const elapsed = tick - policy.effective_tick;
  return { reason: policy.reason, progress: elapsed / 4000, screenProgress: Math.max(0, Math.min(1, (elapsed - 1000) / 2000)), outgoingFrameId: outgoing.frame_id, incomingFrameId: incoming.frame_id };
}

export function sampleVideoAtTick(recording: VideoRecording, requestedTick: number) {
  if (!Number.isFinite(requestedTick)) throw new Error('Invalid seek position.');
  const tick = Math.max(0, Math.min(recording.duration_ticks, Math.floor(requestedTick)));
  const segment = recording.segments.find((candidate) => tick < candidate.playback_end_tick) ?? recording.segments.at(-1)!;
  const sourceTick = segment.source_start_tick + tick - segment.playback_start_tick;
  const bin = segment.bins.find((candidate) => sourceTick < candidate.end_tick) ?? segment.bins.at(-1)!;
  const rates = Object.fromEntries(GROUPS.map((name) => [name, bin.group_spikes[name] * 10000 / (recording.groups[name] * bin.duration_ticks)])) as Counts;
  return { tick, sourceTick, segment, bin, rates, input: recording.inputs[segment.frame_id], policy: visiblePolicyAtTick(recording, tick), clipPolicy: currentClipPolicyAtTick(recording, tick, segment.clip_id), gesture: advanceGestureAtTick(recording, tick) };
}
