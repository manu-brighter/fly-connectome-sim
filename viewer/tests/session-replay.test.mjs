import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
import { runInNewContext } from 'node:vm';
import * as replayModule from '../src/replay.ts';
import * as videoModule from '../src/video-replay.ts';
import * as recordingModule from '../src/recording.ts';
import * as eventModule from '../src/event-replay.ts';
import * as sessionModule from '../src/session-replay.ts';
import * as exportModule from '../src/export.ts';
import * as anatomyModule from '../src/anatomy.ts';
import * as cellModule from '../src/cell-activity.ts';
import { cellFixture } from './cell-activity.test.mjs';
import { drawOverlay, createEventBoard } from '../src/stage.ts';
import { createOperationGate } from '../src/operation.ts';
import * as THREE from 'three';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { parseSessionRecording, sampleSessionAtTick, isSessionRecording } from '../src/session-replay.ts';
import { parseAnyRecording, sampleAnyAtTick } from '../src/recording.ts';
import { parseVideoRecording, videoSpeedLabel } from '../src/video-replay.ts';
import { parseEventRecording, eventPresentation, eventPlanJson } from '../src/event-replay.ts';
import { quantizeVideoTick, frameAt, frameCount, writeFrames } from '../src/export.ts';
const canonical = (value) => value && typeof value === 'object' ? Array.isArray(value) ? value.map(canonical) : Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonical(value[key])])) : value;
const hash = (text) => createHash('sha256').update(text).digest('hex');
// INTERNAL declared data only: checks reader relationships, never a native/Pillow claim.
export function eventFixture(left = 0, right = 2, leftPopulation = 2, rightPopulation = 2) {
  const proposal = { version: 'event-options/v1', brief: { title: 'Team evening', guests: 40, max_budget_chf: 5000 }, options: [
    { id: 'rooftop', title: 'Above the city', setting: 'rooftop', music: 'House', budget_chf: 3000, capacity: 50, duration_minutes: 180, programme: [{ start_minute: 0, label: 'Welcome' }, { start_minute: 60, label: 'DJ set' }] },
    { id: 'warehouse', title: 'Night lights', setting: 'warehouse', music: 'Techno', budget_chf: 4000, capacity: 80, duration_minutes: 240, programme: [{ start_minute: 0, label: 'Doors' }, { start_minute: 60, label: 'Live set' }] },
  ] };
  const rgb = Buffer.alloc(384 * 216 * 3, 42);
  const input = { sha256: hash(Buffer.concat([Buffer.from('{"dtype":"uint8","rank":3,"shape":[216,384,3],"version":"rgb-input/v1"}\n'), rgb])), width: 384, height: 216, rgb_base64: rgb.toString('base64') };
  const groups = { kc: 2, pam11: 1, ppl101: 1, mbon07: 1, mbon11: 1, motor_left: leftPopulation, motor_right: rightPopulation };
  const metadata = {
    engine_identity: { neural_groups: Object.fromEntries(Object.entries(groups).map(([name, size]) => [name, Array.from({ length: size }, (_, i) => i)])) },
    protocol_version: 'event-choice/v1', stimulus_version: 'event-card-rgb/v1', family: 'event-choice', seeds: [], factors: { left_option_id: 'rooftop', right_option_id: 'warehouse' },
    proposal, proposal_source: { kind: 'imported-json', name: 'options.json', size_bytes: 1024, raw_sha256: 'e'.repeat(64) }, proposal_sha256: hash(JSON.stringify(canonical(proposal))),
    renderer_recipe: { version: 'event-cards/v1', pillow_version: '12.3.0', font: 'Pillow-load_default', font_size: 12, width: 384, height: 216 },
    input: { frame_id: 'options', ...input }, input_sha256: [input.sha256],
    choice_recipe: { policy_version: 'event-card-choice/v1', adapter_version: 'lateral-motor-adapter/v1', action_threshold_hz: 1, observation_count: 4, duration_ticks: 5000, settling_ticks: 15000, window_start_tick: 15000, window_end_tick: 20000, stimulation: null, learning: false, pathway_detail: false, qualification_detail: false },
  };
  const source = { run_kind: 'pilot', schema_sha256: 'a'.repeat(64), run_metadata_sha256: 'b'.repeat(64), events_sha256: 'c'.repeat(64), final_scientific_sha256: 'd'.repeat(64), verification_mode: 'integrity-only', metadata };
  const segments = Array.from({ length: 4 }, (_, i) => ({ event_sequence: i + 1, branch_id: 'event-choice/root', frame_id: 'options', stimulation: null, learning: false, source_start_tick: i * 5000, source_end_tick: (i + 1) * 5000, playback_start_tick: i * 5000, playback_end_tick: (i + 1) * 5000,
    bins: Array.from({ length: 50 }, (_, bin) => ({ end_tick: i * 5000 + (bin + 1) * 100, duration_ticks: 100, group_spikes: { kc: 0, pam11: 0, ppl101: 0, mbon07: 0, mbon11: 0, motor_left: i === 3 && bin === 49 ? left : 0, motor_right: i === 3 && bin === 49 ? right : 0 } })),
  }));
  const l = left / (leftPopulation * .5), r = right / (rightPopulation * .5), difference = r - l, scale = Math.max(l, r);
  const action = difference > 1 ? 'inspect_right' : difference < -1 ? 'inspect_left' : 'defer';
  const id = action === 'inspect_right' ? 'warehouse' : action === 'inspect_left' ? 'rooftop' : null;
  const decision = { policy_version: 'event-card-choice/v1', effective_tick: 20000, event_sequence: 4, event_scientific_sha256: 'f'.repeat(64), window_start_tick: 15000, window_end_tick: 20000, counts: { motor_left: left, motor_right: right }, populations: { motor_left: leftPopulation, motor_right: rightPopulation }, readout: { adapter_version: 'lateral-motor-adapter/v1', signed_difference_hz: difference, evidence_strength: scale ? Math.abs(difference / scale) / (r / scale + l / scale) : 0, action }, selected_option_id: id };
  const { metadata: _metadata, ...planSource } = source;
  const plan = { version: 'event-plan/v1', status: id ? 'selected' : 'deferred', brief: structuredClone(proposal.brief), selected_option_id: id, selected_option: id ? structuredClone(proposal.options.find((option) => option.id === id)) : null, decision_ref: { event_sequence: 4, scientific_sha256: decision.event_scientific_sha256, input_sha256: input.sha256, policy_version: decision.policy_version }, source: planSource };
  return { version: 'event-choice-replay/v1', tick_ms: .1, source, groups, inputs: { options: input }, segments, duration_ticks: 20000, decision, plan };
}

// Declared parser fixture. No native execution, renderer or causal evidence claim.
export function sessionFixture(clipCount = 1, earlyAdvance = false, left = 0, right = 2) {
  const value = eventFixture(left, right), metadata = value.source.metadata;
  value.version = 'feed-event-replay/v1';
  Object.assign(metadata, { protocol_version: 'feed-event-session/v1', stimulus_version: 'feed-event-rgb/v1', family: 'feed-event-session' });
  metadata.factors = { clip_count: clipCount, ...metadata.factors };
  metadata.choice_recipe.timing_origin = 'feed-stop/v1';
  metadata.video_recipe = { policy_version: 'right-scroll/v2', adapter_version: 'lateral-motor-adapter/v1', action_threshold_hz: 1, sample_fps: [30, 1], sample_time_origin: 'first-decoded-pts', tick_quantization: 'nearest-0.1ms-half-up-cumulative/v1', window_ticks: 40000, session_limit_ticks: 80000, rolling_window_ticks: 3000, minimum_dwell_ticks: 30000, input_width: 90, input_height: 160, audio_input: false, stimulation: null, learning: false, pathway_detail: false, qualification_detail: false, source_speed: [5, 1], source_window_seconds: 20 };
  const pixels = Buffer.alloc(90 * 160 * 3, 10), videoHash = hash(Buffer.concat([Buffer.from('{"dtype":"uint8","rank":3,"shape":[160,90,3],"version":"rgb-input/v1"}\n'), pixels]));
  metadata.clips = Array.from({ length: clipCount }, (_, c) => ({ clip_id: `clip-${c}`, source_url: `https://example.test/${c}`, source_path: `clip-${c}.mp4`, source_sha256: '9'.repeat(64), source_size: 1000, source_width: 90, source_height: 160, source_sample_aspect_ratio: [1, 1], source_time_base: [1, 30], origin_pts: 0, coverage_end_pts: 600, coverage_method: 'following_pts', decoder: { pyav_version: '19.0.2', ffmpeg_libraries: { libavcodec: [62, 1, 0] } }, transform: { width: 90, height: 160, inner_width: 90, inner_height: 160, padding: [0, 0, 0, 0], resize: 'bilinear', placement: 'centered-black-letterbox', pixel_format: 'rgb24', color_conversion: 'PyAV-to_ndarray-rgb24-FFmpeg-defaults', crop: 'none', orientation: 'reject-rotation-and-displaymatrix/v1' }, frames: Array.from({ length: 120 }, (_, i) => ({ frame_id: `clip-${c}/frame-${i}`, frame_index: i, sha256: videoHash, source_pts: i * 5, source_time_base: [1, 30] })) }));
  const videoSegments = [], zero = Object.fromEntries(Object.keys(value.groups).map((k) => [k, 0]));
  let tick = 0, stopped = false;
  for (let c = 0; c < clipCount && !stopped; c++) {
    const clipStart = tick, frames = [];
    for (let i = 0; i < 120 && !stopped; i++) {
      const start = tick, end = start + quantizeVideoTick(i + 1) - quantizeVideoTick(i), frameId = `clip-${c}/frame-${i}`;
      const motorRight = earlyAdvance && i === 89 ? 2 : 0;
      const bins = [];
      for (let t = start; t < end;) { const duration = Math.min(100, end - t); t += duration; bins.push({ end_tick: t, duration_ticks: duration, group_spikes: { ...zero, motor_right: t === end ? motorRight : 0 } }); }
      frames.push(motorRight);
      let video_policy = null;
      if (i % 3 === 2) {
        const counts = { motor_left: 0, motor_right: frames.slice(-9).reduce((a, b) => a + b, 0) }, populations = { motor_left: value.groups.motor_left, motor_right: value.groups.motor_right };
        const rate = counts.motor_right / (populations.motor_right * .3);
        const window = i < 8 ? null : { start_tick: end - 3000, end_tick: end, frame_count: 9, counts, populations };
        const readout = window ? { adapter_version: 'lateral-motor-adapter/v1', signed_difference_hz: rate, evidence_strength: rate ? 1 : 0, action: rate > 1 ? 'inspect_right' : 'defer' } : null;
        const dwell = end - clipStart >= 30000, trigger = end === 80000 ? 'session_limit' : i === 119 ? 'clip_window_end' : dwell && readout?.action === 'inspect_right' ? 'motor_right' : null;
        const action = trigger === 'session_limit' || trigger && c === clipCount - 1 ? 'stop' : trigger ? 'advance' : 'watch';
        const reason = trigger === 'session_limit' ? 'session_limit' : action === 'stop' ? 'playlist_exhausted' : trigger ?? (dwell ? 'motor_left_or_defer' : 'minimum_dwell');
        video_policy = { policy_version: 'right-scroll/v2', effective_tick: end, window, readout, minimum_dwell_met: dwell, action, reason, trigger, next_clip_index: action === 'stop' ? null : action === 'advance' ? c + 1 : c };
      }
      value.inputs[frameId] = { sha256: videoHash, width: 90, height: 160, rgb_base64: pixels.toString('base64'), clip_id: `clip-${c}`, frame_index: i, source_pts: i * 5, source_time_base: [1, 30] };
      videoSegments.push({ event_sequence: videoSegments.length + 1, branch_id: 'feed-event/root', frame_id: frameId, clip_id: `clip-${c}`, frame_index: i, stimulation: null, learning: false, source_start_tick: start, source_end_tick: end, playback_start_tick: start, playback_end_tick: end, bins, video_policy });
      tick = end;
      if (video_policy?.action === 'stop') stopped = true;
      if (video_policy?.action === 'advance') break;
    }
  }
  value.feed_end_tick = tick; value.duration_ticks = tick + 20000;
  for (const segment of value.segments) {
    segment.branch_id = 'feed-event/root'; segment.event_sequence += videoSegments.length;
    for (const k of ['source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick']) segment[k] += tick;
    for (const bin of segment.bins) bin.end_tick += tick;
  }
  value.segments = [...videoSegments, ...value.segments];
  value.decision.effective_tick += tick; value.decision.window_start_tick += tick; value.decision.window_end_tick += tick; value.decision.event_sequence += videoSegments.length;
  value.plan.decision_ref.event_sequence = value.decision.event_sequence;
  metadata.input_sha256 = [videoHash, value.inputs.options.sha256].sort();
  return value;
}
const parse = (value) => parseSessionRecording(JSON.stringify(value));

test('session boundary and reverse seek use actual global clocks without an early plan', async () => {
  const value = sessionFixture(), recording = await parse(value), T = recording.feed_end_tick, D = recording.duration_ticks;
  assert.ok(isSessionRecording(recording)); assert.equal((await parseAnyRecording(JSON.stringify(value))).version, value.version);
  assert.equal(videoSpeedLabel(recording), 'Reel 5×');
  for (const t of [T - 1, T, D - 1, D, T, T - 1]) {
    const sample = sampleSessionAtTick(recording, t);
    assert.equal(sample.sourceTick, t); assert.equal(sample.tick, t);
    if (t < T) { assert.ok('input' in sample); assert.equal(sample.gesture, null); assert.equal('plan' in sample, false); }
    else { assert.ok('decision' in sample); assert.equal(sample.plan !== null, t === D); assert.equal(eventPresentation(sample).canDownload, t === D); assert.equal(eventPlanJson(sample) !== null, t === D); }
    assert.deepEqual(sampleAnyAtTick(recording, t), sample);
  }
  assert.equal(sampleSessionAtTick(recording, T).segment.frame_id, 'options');
  assert.match(eventPresentation(sampleSessionAtTick(recording, T)).status, /6.000 s/);
});

test('8s session cap outranks 3s dwell on third clip and ADVANCE alone swipes for400ms', async () => {
  const recording = await parse(sessionFixture(3, true));
  assert.equal(recording.feed_end_tick, 80000); assert.equal(recording.segments.at(-5).video_policy.reason, 'session_limit');
  assert.equal(recording.segments.at(-5).video_policy.minimum_dwell_met, false);
  assert.equal(sampleSessionAtTick(recording, 29999).gesture, null);
  assert.equal(sampleSessionAtTick(recording, 30000).gesture.progress, 0);
  assert.equal(sampleSessionAtTick(recording, 33999).gesture.progress, 3999 / 4000);
  assert.equal(sampleSessionAtTick(recording, 34000).gesture, null);
  assert.equal('gesture' in sampleSessionAtTick(recording, 80000), false);
});

test('session mutations fail closed for metadata/maps/policy/clocks/counts/pixels/plan/EOF', async () => {
  const mutations = [
    v => { v.extra = true; }, v => { v.source.extra = 1; }, v => { v.source.verification_mode = 'native-replay'; },
    v => { v.source.metadata.family = 'video-observation'; }, v => { v.source.metadata.extra = 1; },
    v => { v.source.metadata.engine_identity.neural_groups.extra = []; }, v => { v.groups.motor_left++; },
    v => { v.source.metadata.engine_identity.neural_groups.motor_left = [0, 0]; },
    v => { v.source.metadata.choice_recipe.timing_origin = 'start'; }, v => { v.source.metadata.video_recipe.source_speed = [1, 1]; },
    v => { v.source.metadata.factors.clip_count++; }, v => { v.source.metadata.proposal.options[0].title = 'changed'; },
    v => { v.source.metadata.input_sha256.pop(); }, v => { v.feed_end_tick--; }, v => { v.duration_ticks--; },
    v => { v.segments[0].source_start_tick = 1; }, v => { v.segments[0].event_sequence++; },
    v => { v.segments[0].branch_id = 'video-observation/root'; }, v => { v.segments[0].learning = true; },
    v => { v.segments[0].bins[0].group_spikes.kc = true; }, v => { v.segments[0].bins[0].duration_ticks++; },
    v => { v.segments.at(-5).video_policy.action = 'watch'; }, v => { v.segments.at(-5).video_policy.readout.action = 'inspect_right'; },
    v => { v.segments.at(-4).playback_start_tick--; }, v => { v.segments.at(-4).bins[0].duration_ticks = 99; },
    v => { v.segments.at(-4).bins.pop(); }, v => { v.segments.at(-4).bins.push(v.segments.at(-4).bins[0]); },
    v => { v.segments.at(-1).bins.at(-1).group_spikes.motor_right++; },
    v => { v.inputs.options.rgb_base64 = Buffer.alloc(384 * 216 * 3).toString('base64'); },
    v => { v.inputs['clip-0/frame-0'].rgb_base64 = Buffer.alloc(90 * 160 * 3).toString('base64'); },
    v => { v.decision.window_start_tick = 15000; }, v => { v.decision.event_sequence = 4; },
    v => { v.decision.counts.motor_right++; }, v => { v.decision.readout.signed_difference_hz += 1e-12; },
    v => { v.plan.selected_option.music = 'changed'; }, v => { v.plan.source.metadata = v.source.metadata; },
    v => { v.plan.decision_ref.scientific_sha256 = '0'.repeat(64); },
    v => { v.segments.pop(); }, v => { v.segments.push(v.segments.at(-1)); }, v => { v.segments.reverse(); },
    v => { v.segments.splice(0, 0, v.segments.at(-1)); },
  ];
  const baseline = sessionFixture(); await parse(baseline);
  for (const change of mutations) { const value = structuredClone(baseline); change(value); await assert.rejects(parse(value), undefined, String(change)); }
  const text = JSON.stringify(baseline);
  await assert.rejects(parseSessionRecording(text.replace('"tick_ms":0.1', '"tick_ms":0.1,"tick_ms":0.1')));
  await assert.rejects(parseSessionRecording(text.slice(0, -1)));
  await assert.rejects(parseSessionRecording(' '.repeat(32 * 1024 * 1024 + 1)));
  await assert.rejects(parseVideoRecording(text)); await assert.rejects(parseEventRecording(text));
});

test('one global30fps export and final90frame hold preserve terminal plan, cancel and exact cap', async () => {
  const recording = await parse(sessionFixture(3, true)), samples = [];
  assert.equal(frameCount(recording.duration_ticks, 90), 390);
  await writeFrames(recording.duration_ticks, { paint: frame => { samples.push({ ...frame, sample: sampleSessionAtTick(recording, frame.tick) }); }, add: async () => {}, finalize: async () => true, cancel: async () => assert.fail('unexpected cancel') }, undefined, undefined, quantizeVideoTick, 90);
  assert.equal(samples.filter(f => f.terminalHold).length, 90);
  assert.equal(samples[240].tick, recording.feed_end_tick); assert.equal(samples[240].terminalHold, false);
  assert.equal(samples[299].tick, quantizeVideoTick(299));
  assert.ok(samples.slice(300).every(f => f.tick === recording.duration_ticks && f.sample.plan));
  const controller = new AbortController(); let canceled = false;
  await assert.rejects(writeFrames(100000, { paint: () => controller.abort(), add: async () => assert.fail('aborted write'), finalize: async () => assert.fail('aborted finalization'), cancel: async () => { canceled = true; } }, controller.signal, undefined, quantizeVideoTick, 90));
  assert.ok(canceled); assert.equal(frameAt(1, 20000).tick, 333); assert.equal(frameCount(20000), 75);
});

// Execute real application control flow with only DOM/WebGL/codec dependencies
// replaced. This is a control-flow test, not browser or encoded-video evidence.
function mainHarness() {
  const nodes = new Map(), paints = [], downloads = [];
  const context = { beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, clearRect() {}, drawImage() {} };
  function node() { return { content: '', writes: [], get textContent() { return this.content; }, set textContent(value) { this.content = value; this.writes.push(value); }, hidden: false, disabled: false, value: '1', clientWidth: 200, width: 0, height: 0, handlers: {}, children: [], style: {}, classList: { add() {} }, append(child) { this.children.push(child); }, replaceChildren() { this.children = []; }, setAttribute(name, value) { this[name] = value; }, getContext() { return context; }, addEventListener(name, handler) { this.handlers[name] = handler; }, click() { if (this.download) downloads.push(this.download); return this.handlers.click?.(); } }; }
  const document = { getElementById(id) { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); }, createElement() { return node(); } };
  let currentSample, currentCell = null, animation, loadCount = 0, cancelAt = null;
  const stage = { renderer: { setAnimationLoop(callback) { animation = callback; } }, setRecording() { loadCount++; currentCell = null; }, setAnatomy() {}, setCellActivity(value) { currentCell = value; }, setSample(sample) { currentSample = sample; }, render(hold, holdElapsedTicks) { paints.push({ sample: currentSample, hold, holdElapsedTicks, cell: currentCell }); }, setExporting() {}, dispose() {} };
  class BufferTarget { buffer = new ArrayBuffer(1); }
  class Output { state = 'pending'; constructor({target}) { this.target = target; } addVideoTrack() {} async start() { this.state = 'started'; } async finalize() { this.state = 'finalized'; } async cancel() { this.state = 'canceled'; } }
  class CanvasSource { async add() { if (cancelAt !== null && paints.filter(p => p.hold !== undefined).length >= cancelAt) { cancelAt = null; await nodes.get('video').handlers.click(); } } }
  const javascript = stripTypeScriptTypes(readFileSync(new URL('../src/main.ts', import.meta.url), 'utf8')).replace(/^import .+;\r?$/gm, '');
  runInNewContext(javascript, { ...replayModule, ...videoModule, ...recordingModule, ...eventModule, ...sessionModule, ...exportModule, ...anatomyModule, ...cellModule, sampleAt: recordingModule.sampleAnyAtTick, createOperationGate, createStage: () => stage, canEncodeVideo: async () => true, document, performance, VideoEncoder: class {}, window: { addEventListener() {} }, setTimeout: () => {}, Blob, URL: { createObjectURL: () => 'blob:declared', revokeObjectURL() {} }, AbortController, BufferTarget, Output, CanvasSource, WebMOutputFormat: class {} });
  const load = async (value, textPromise) => { const json = JSON.stringify(value); nodes.get('file').files = [{ name: 'session.json', size: Buffer.byteLength(json), arrayBuffer: async () => new TextEncoder().encode(await (textPromise ?? json)).buffer }]; await nodes.get('file').handlers.change(); };
  const seek = (tick) => { nodes.get('seek').value = String(tick); nodes.get('seek').handlers.input(); };
  const key = (code, options = {}, focus = 'stage') => {
    document.activeElement = nodes.get(focus);
    const event = { code, repeat: false, altKey: false, ctrlKey: false, metaKey: false, shiftKey: false, prevented: false, preventDefault() { this.prevented = true; }, ...options };
    nodes.get('stage').handlers.keydown(event); return event.prevented;
  };
  return { nodes, load, seek, key, paints, downloads, sample: () => currentSample, cell: () => currentCell, loadCount: () => loadCount, cancelAfter: n => { cancelAt = n; }, animate: t => animation(t) };
}

test('real application cell loading preserves valid detail, ignores stale files and freezes export attachment', async () => {
  const app = mainHarness(), value = sessionFixture(1, false, 0, 0), detail = cellFixture().detail;
  let index = 0;
  const maps = Object.fromEntries(Object.entries(value.groups).map(([name, count]) => [name, Array.from({ length: count }, () => index++)]));
  value.source.metadata.engine_identity = { ...cellFixture().context.recording.source.metadata.engine_identity, neural_groups: maps };
  detail.binding.recording_sha256 = hash(JSON.stringify(value));
  detail.selection.group_population_counts = { ...value.groups }; detail.selection.group_selected_counts = { ...value.groups };
  detail.cells = Array.from({ length: index }, (_, i) => ({ model_index: i, source_id: i + 1, groups: Object.keys(maps).filter(name => maps[name].includes(i)), soma: null }));
  detail.topology.eligible_edges = 0; detail.topology.edges = [];
  detail.bins = value.segments.flatMap((segment, observation) => segment.bins.map((bin, ordinal) => ({ observation_index: observation, bin_index: ordinal, start_tick: bin.end_tick - bin.duration_ticks, end_tick: bin.end_tick, counts: Array(index).fill(0) })));
  await app.load(value); await new Promise(setImmediate);
  const file = app.nodes.get('cell-file'); assert.ok(file, 'Optional cell action is missing');
  const select = async text => { file.files = [{ size: text.length, text: async () => text }]; await file.handlers.change(); };
  await select(JSON.stringify(detail)); assert.ok(app.cell()); const valid = app.cell();
  assert.match(app.nodes.get('cell-count-caption').textContent, /Awaiting first complete/);
  app.seek(1000); assert.match(app.nodes.get('cell-count-caption').textContent, /0\.000–0\.100/);
  await select('{}'); assert.equal(app.cell(), valid); assert.equal(app.nodes.get('play').disabled, false);
  app.paints.length = 0;
  const exporting = app.nodes.get('video').handlers.click();
  assert.equal(app.nodes.get('cell-open').disabled, true);
  await select('{}'); assert.equal(app.cell(), valid);
  await exporting; assert.ok(app.paints.every(paint => paint.cell === valid));
  let finish; file.files = [{ size: 2, text: () => new Promise(resolve => { finish = resolve; }) }];
  const pending = file.handlers.change(); assert.equal(app.nodes.get('video').disabled, true);
  await app.load(value); finish('{}'); await pending;
  assert.equal(app.cell(), null); assert.equal(app.nodes.get('cell-note').textContent, 'Cell activity not loaded');
  assert.equal(app.nodes.get('error').hidden, true);
});

test('interactive presentation hold pauses, reverses and exports without advancing neural time', async () => {
  const app = mainHarness(), value = sessionFixture(); await app.load(value); await new Promise(setImmediate);
  app.seek(value.duration_ticks - 1000); app.key('Space');
  const time = performance.now(); app.animate(time + 900);
  let painted = app.paints.at(-1);
  assert.equal(painted.sample.tick, value.duration_ticks);
  assert.equal(painted.hold, true);
  assert.ok(painted.holdElapsedTicks > 7900 && painted.holdElapsedTicks < 8200);
  assert.equal(app.nodes.get('play').textContent, 'Pause');
  app.key('Space'); const paused = painted.holdElapsedTicks;
  app.animate(time + 1500); assert.equal(app.paints.at(-1).holdElapsedTicks, paused);
  app.paints.length = 0; await app.nodes.get('video').handlers.click();
  const holds = app.paints.slice(0, -1).filter(paint => paint.hold === true);
  assert.equal(holds.length, 90);
  assert.equal(holds[0].holdElapsedTicks, 0); assert.equal(holds[24].holdElapsedTicks, 8000);
  assert.equal(app.paints.at(-1).holdElapsedTicks, paused, 'Export must restore paused presentation position');
  app.seek(value.feed_end_tick); app.animate(time + 1700);
  assert.equal(app.paints.at(-1).holdElapsedTicks, 0); assert.equal(app.sample().decision, null);
  app.seek(value.duration_ticks); app.key('Space'); app.animate(performance.now() + 3100);
  assert.equal(app.paints.at(-1).holdElapsedTicks, 30000); assert.equal(app.nodes.get('play').textContent, 'Play');
  app.key('Space'); assert.equal(app.sample().tick, 0, 'Replay after completed presentation must start at zero');
});

test('optional anatomy loading blocks export and stale files never replace a newer recording', async () => {
  const app = mainHarness(), value = sessionFixture(); await app.load(value); await new Promise(setImmediate);
  const open = app.nodes.get('anatomy-open'), file = app.nodes.get('anatomy-file');
  assert.ok(open && file, 'Recording needs an optional local anatomy action');
  assert.equal(open.disabled, false);
  let finish; file.files = [{ size: 2, text: () => new Promise(resolve => { finish = resolve; }) }];
  const pending = file.handlers.change();
  assert.equal(open.disabled, true); assert.equal(app.nodes.get('video').disabled, true);
  await app.load(eventFixture()); finish('{}'); await pending;
  assert.equal(app.sample().tick, 0); assert.equal(app.nodes.get('anatomy-note').textContent, 'Anatomy not loaded');
  assert.equal(app.nodes.get('error').hidden, true);
  file.files = [{ size: 2, text: async () => '{}' }]; await file.handlers.change();
  assert.match(app.nodes.get('error').textContent, /anatomy/i); assert.equal(app.nodes.get('play').disabled, false);
});

test('canvas shortcuts seek the real timeline by100ms and Home/End clamp to recorded bounds', async () => {
  const app = mainHarness(), value = sessionFixture(); await app.load(value);
  for (const [code, tick] of [['ArrowRight', 1000], ['ArrowLeft', 0], ['ArrowLeft', 0], ['End', 60000], ['ArrowRight', 60000], ['ArrowLeft', 59000], ['Home', 0]]) {
    assert.equal(app.key(code), true, code); assert.equal(app.sample().tick, tick, code);
    assert.equal(app.nodes.get('seek').value, String(tick));
  }
});

test('only focused unmodified canvas shortcuts act, and repeated Space cannot toggle playback', async () => {
  const app = mainHarness(); await app.load(sessionFixture());
  assert.equal(app.key('Space'), true); assert.equal(app.nodes.get('play').textContent, 'Pause');
  assert.equal(app.key('Space', { repeat: true }), true); assert.equal(app.nodes.get('play').textContent, 'Pause');
  for (const modifier of ['altKey', 'ctrlKey', 'metaKey', 'shiftKey']) {
    for (const code of ['Space', 'ArrowLeft', 'ArrowRight', 'Home', 'End']) assert.equal(app.key(code, { [modifier]: true }), false);
  }
  for (const focus of ['play', 'seek', 'speed', 'open']) {
    for (const code of ['Space', 'ArrowLeft', 'ArrowRight', 'Home', 'End']) assert.equal(app.key(code, {}, focus), false);
  }
  assert.equal(app.key('KeyX'), false); assert.equal(app.sample().tick, 0); assert.equal(app.nodes.get('play').textContent, 'Pause');
  assert.equal(app.key('Space'), true); assert.equal(app.nodes.get('play').textContent, 'Play');
});

test('canvas shortcuts leave clocks and browser defaults alone without a recording or during loading/export', async () => {
  const app = mainHarness(), value = sessionFixture();
  for (const code of ['Space', 'ArrowLeft', 'ArrowRight', 'Home', 'End']) assert.equal(app.key(code), false);
  await app.load(value); await new Promise(setImmediate); app.seek(12345);
  let finishLoad; const pending = app.load(value, new Promise(resolve => { finishLoad = resolve; }));
  for (const code of ['Space', 'ArrowLeft', 'ArrowRight', 'Home', 'End']) {
    assert.equal(app.key(code), false, code); assert.equal(app.sample().tick, 12345); assert.equal(app.nodes.get('play').textContent, 'Play');
  }
  finishLoad(JSON.stringify(value)); await pending; app.seek(12345);
  const exporting = app.nodes.get('video').handlers.click();
  for (const code of ['Space', 'ArrowLeft', 'ArrowRight', 'Home', 'End']) {
    assert.equal(app.key(code), false, code); assert.equal(app.nodes.get('seek').value, '12345');
  }
  await exporting; assert.equal(app.sample().tick, 12345);
});

test('main announces clip/paired pending/selected phases once, and reverse seek clears the winner', async () => {
  const app = mainHarness(), value = sessionFixture(); await app.load(value);
  const live = app.nodes.get('replay-announcement');
  assert.match(live?.textContent ?? '', /feed.*clip 1/i);
  let writes = live.writes.length;
  app.seek(1000); app.animate(performance.now()); app.animate(performance.now()); assert.equal(live.writes.length, writes);
  app.seek(value.feed_end_tick); assert.match(live.textContent, /paired.*pending/i); assert.doesNotMatch(live.textContent, /Night lights/);
  writes = live.writes.length; app.seek(value.duration_ticks - 1); assert.equal(live.writes.length, writes);
  app.seek(value.duration_ticks); assert.match(live.textContent, /selected.*Night lights/i);
  writes = live.writes.length; app.animate(performance.now()); app.seek(value.duration_ticks); assert.equal(live.writes.length, writes);
  app.seek(value.feed_end_tick); assert.match(live.textContent, /pending/i); assert.doesNotMatch(live.textContent, /Night lights/);
  app.seek(0); assert.match(live.textContent, /feed.*clip 1/i); assert.doesNotMatch(live.textContent, /selected|Night lights/i);
});

test('main announces clip changes and honestly deferred standalone and continuous choices', async () => {
  const app = mainHarness(), value = sessionFixture(3, true); await app.load(value);
  app.seek(30000); assert.match(app.nodes.get('replay-announcement')?.textContent ?? '', /feed.*clip 2/i);
  for (const deferred of [eventFixture(1, 1), sessionFixture(1, false, 1, 1)]) {
    await app.load(deferred); app.seek(deferred.duration_ticks);
    assert.match(app.nodes.get('replay-announcement').textContent, /deferred.*no option selected/i);
    app.seek(deferred.duration_ticks - 1); assert.match(app.nodes.get('replay-announcement').textContent, /pending/i);
  }
});

test('A/B replay announcements describe the current stimulus without implying a choice', async () => {
  const event = eventFixture(), groups = event.groups;
  const input = rgb => { const bytes = Buffer.from(rgb); return { width: 1, height: 1, rgb_base64: bytes.toString('base64'), sha256: hash(Buffer.concat([Buffer.from('{"dtype":"uint8","rank":3,"shape":[1,1,3],"version":"rgb-input/v1"}\n'), bytes])) }; };
  const inputs = { A: input([255, 0, 0]), B: input([0, 255, 0]), black: input([0, 0, 0]) };
  const value = { version: 'measured-replay/v1', tick_ms: .1, groups, inputs, source: { ...event.source, metadata: { family: 'measured-observation', protocol_version: 'measured-observation/v1', engine_identity: event.source.metadata.engine_identity, input_sha256: Object.values(inputs).map(input => input.sha256) } }, segments: ['A', 'black', 'B', 'black'].map((stimulus, i) => ({ event_sequence: i + 1, branch_id: 'root', stimulus, stimulation: null, learning: false, source_start_tick: i * 100, source_end_tick: (i + 1) * 100, playback_start_tick: i * 100, playback_end_tick: (i + 1) * 100, bins: [{ end_tick: (i + 1) * 100, duration_ticks: 100, group_spikes: Object.fromEntries(Object.keys(groups).map(name => [name, 0])) }] })), duration_ticks: 400 };
  const app = mainHarness(); await app.load(value);
  for (const [tick, stimulus] of [[0, 'A'], [100, 'Black'], [200, 'B'], [400, 'Black']]) {
    app.seek(tick); const live = app.nodes.get('replay-announcement');
    assert.match(live?.textContent ?? '', new RegExp(`stimulus.*${stimulus}`, 'i')); assert.doesNotMatch(live.textContent, /selected|choice/i);
  }
});

test('main keeps phase labels/URL/timeline/plan/download coherent through forward and reverse seeks', async () => {
  const app = mainHarness(), value = sessionFixture(); await app.load(value); await new Promise(setImmediate);
  const node = id => app.nodes.get(id), T = value.feed_end_tick, D = value.duration_ticks;
  assert.equal(node('error').hidden, true);
  assert.match(node('input-caption').textContent, /Reel 5×/); assert.match(node('policy-note').textContent, /right-scroll\/v2/);
  assert.equal(node('clip-url').href, 'https://example.test/0'); assert.equal(node('video-policy').hidden, false); assert.equal(node('event-plan').hidden, true); assert.equal(node('download-plan').hidden, true);
  assert.equal(node('segments').children.length, 2); assert.equal(node('segments').children[1].style.flexGrow, '20000');
  for (const t of [T - 1, T, D - 1, D, T, T - 1]) {
    app.seek(t); const event = t >= T;
    assert.equal(node('video-policy').hidden, event); assert.equal(node('event-plan').hidden, !event);
    assert.equal(node('download-plan').hidden, t !== D); assert.equal(node('download-plan').disabled, t !== D);
    if (event && t < D) { assert.match(node('event-status').textContent, /6.000 s/); assert.match(node('event-measurement').textContent, /Feed ended at 4.000 s/); assert.doesNotMatch(node('event-details').textContent, /Techno/); }
  }
  app.seek(D); await node('download-plan').handlers.click(); assert.deepEqual(app.downloads, ['event-plan.json']);
  app.seek(T); await node('download-plan').handlers.click(); assert.equal(app.downloads.length, 1);
  app.seek(D); let finishLoad; const pending = app.load(value, new Promise(resolve => { finishLoad = resolve; }));
  assert.equal(node('download-plan').disabled, true); assert.equal(node('video').disabled, true);
  await node('download-plan').handlers.click(); assert.equal(app.downloads.length, 1);
  await node('video').handlers.click(); assert.equal(app.downloads.length, 1);
  finishLoad(JSON.stringify(value)); await pending; assert.equal(app.sample().tick, 0);
});

test('actual main export has no phase hold, holds final plan90frames, prevents load and restores after cancel', async () => {
  const app = mainHarness(), value = sessionFixture(); await app.load(value); await new Promise(setImmediate); app.seek(12345);
  app.paints.length = 0;
  const exporting = app.nodes.get('video').handlers.click();
  assert.equal(app.nodes.get('file').disabled, true); const loadCount = app.loadCount(); await app.load(value); assert.equal(app.loadCount(), loadCount);
  await exporting;
  assert.equal(app.paints.filter(p => p.hold === true).length, 90);
  const sourcePaints = app.paints.filter(p => p.hold === false); assert.equal(sourcePaints.length, 180);
  assert.equal(sourcePaints[120].sample.tick, value.feed_end_tick); assert.equal(sourcePaints[120].sample.segment.frame_id, 'options');
  assert.ok(app.paints.filter(p => p.hold === true).every(p => p.sample.plan));
  assert.equal(app.sample().tick, 12345); assert.equal(app.nodes.get('file').disabled, false); assert.deepEqual(app.downloads, ['measured-replay.webm']);
  app.paints.length = 0; app.cancelAfter(4); await app.nodes.get('video').handlers.click();
  assert.match(app.nodes.get('video-note').textContent, /canceled/); assert.deepEqual(app.downloads, ['measured-replay.webm']); assert.equal(app.sample().tick, 12345); assert.equal(app.nodes.get('seek').disabled, false);
});

test('paired board and overlay preserve global decision, exact texture and reduced-motion no swipe', async () => {
  const recording = await parse(sessionFixture(3, true)), board = createEventBoard(), texture = new THREE.Texture();
  for (const t of [80000, 99999, 100000, 80000]) { board.setSample(sampleSessionAtTick(recording, t), texture); assert.equal(board.screen.material.map, texture); assert.equal(board.highlights.right.visible, t === 100000); }
  const calls = [], context = { font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; }, fillText(text, x, _y, maxWidth) { calls.push({ text, x, width: Math.min(this.measureText(text).width, maxWidth ?? Infinity) }); } };
  drawOverlay(context, 390, 600, 390, recording, sampleSessionAtTick(recording, 31000), false, true);
  assert.ok(calls.some(c => c.text.includes('Reel 5×'))); assert.ok(calls.every(c => !c.text.includes('Illustrative swipe')));
  calls.length = 0; drawOverlay(context, 390, 600, 390, recording, sampleSessionAtTick(recording, 80000));
  assert.ok(calls.some(c => c.text.includes('10.000 s'))); assert.ok(calls.every(c => !c.text.includes('presentation hold') && !c.text.includes('Illustrative swipe')));
  texture.dispose();
});

test('session keeps strict left/right/defer selection and exact200card plus960video bins at cap', async () => {
  for (const [left, right, selected] of [[2, 0, 'rooftop'], [0, 2, 'warehouse'], [1, 1, null], [0, 1, null]]) {
    const recording = await parse(sessionFixture(1, false, left, right));
    assert.equal(recording.decision.selected_option_id, selected); assert.equal(recording.plan.selected_option_id, selected);
    assert.equal(Object.keys(recording.plan).length, 7); assert.equal(Object.keys(recording.plan.source).length, 6); assert.equal(Object.keys(recording.source).length, 7);
  }
  const value = sessionFixture(3, true); await parse(value);
  assert.equal(value.segments.length, 244); assert.equal(value.segments.flatMap(s => s.bins).length, 1160);
  const redistributed = structuredClone(value); redistributed.segments[0].bins[0].duration_ticks = 99; redistributed.segments[0].bins[0].end_tick = 99; redistributed.segments[0].bins[1].duration_ticks = 101;
  await assert.rejects(parse(redistributed));
  const nativeResolution = structuredClone(value); nativeResolution.segments[0].bins[0].duration_ticks = 99; nativeResolution.segments[0].bins[0].end_tick = 99; nativeResolution.segments[0].bins[1].duration_ticks = 100; nativeResolution.segments[0].bins[1].end_tick = 199; nativeResolution.segments[0].bins[2].duration_ticks = 100; nativeResolution.segments[0].bins[2].end_tick = 299; nativeResolution.segments[0].bins[3].duration_ticks = 34;
  await assert.rejects(parse(nativeResolution), /Native video bin duration/);
  const oversized = structuredClone(value); oversized.segments.push(structuredClone(value.segments.at(-1))); await assert.rejects(parse(oversized));
});
