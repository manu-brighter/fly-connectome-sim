import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { advanceGestureAtTick, parseAnyRecording, parseVideoRecording, sampleVideoAtTick, videoInputLabel, videoPlaneHeight, videoPolicyLabel, videoTimelineBlocks, visiblePolicyAtTick } from '../src/video-replay.ts';
import { quantizeVideoTick } from '../src/export.ts';
import * as stage from '../src/stage.ts';
const { drawOverlay } = stage;

const counts = { kc: 0, pam11: 0, ppl101: 0, mbon07: 0, mbon11: 0, motor_left: 0, motor_right: 0 };
const groups = Object.fromEntries(Object.keys(counts).map((name) => [name, 1]));
const policy = { effective_tick: 1000, action: 'advance', reason: 'motor_right', trigger: 'motor_right', readout: { action: 'inspect_right' } };
const recording = {
  version: 'measured-video-replay/v1', duration_ticks: 1333, groups,
  inputs: { first: { width: 90, height: 160, clip_id: 'clip-0', frame_index: 2, source_pts: 66, source_time_base: [1, 1000] }, second: { width: 90, height: 160, clip_id: 'clip-1', frame_index: 0, source_pts: 0, source_time_base: [1, 1000] } },
  segments: [
    { frame_id: 'first', clip_id: 'clip-0', frame_index: 2, playback_start_tick: 667, playback_end_tick: 1000, source_start_tick: 667, source_end_tick: 1000, bins: [{ end_tick: 1000, duration_ticks: 333, group_spikes: counts }], video_policy: policy },
    { frame_id: 'second', clip_id: 'clip-1', frame_index: 0, playback_start_tick: 1000, playback_end_tick: 1333, source_start_tick: 1000, source_end_tick: 1333, bins: [{ end_tick: 1333, duration_ticks: 333, group_spikes: counts }], video_policy: null },
  ],
};

test('end-of-observe decision is invisible before its effective tick', () => {
  assert.equal(visiblePolicyAtTick(recording, 999), null);
  assert.equal(advanceGestureAtTick(recording, 999), null);
  assert.equal(visiblePolicyAtTick(recording, 1000), policy);
  assert.equal(advanceGestureAtTick(recording, 1000).reason, 'motor_right');
  assert.ok(advanceGestureAtTick(recording, 1250));
  assert.equal(advanceGestureAtTick(recording, 3500), null);
});

test('following input starts at the decision boundary with exact frame identity', () => {
  const before = sampleVideoAtTick(recording, 999);
  const after = sampleVideoAtTick(recording, 1000);
  assert.equal(before.segment.frame_id, 'first');
  assert.equal(after.segment.frame_id, 'second');
  assert.equal(after.input, recording.inputs.second);
  assert.equal(after.policy, policy);
});

test('portrait image geometry and recorded decision labels are explicit', () => {
  assert.equal(videoPlaneHeight(1.19, 90, 160), 1.19 * 160 / 90);
  assert.equal(videoInputLabel({ clip_id: 'clip-1', frame_index: 4 }), 'Clip 2 · frame 5');
  assert.equal(videoPolicyLabel(policy), 'ADVANCE · motor readout');
  assert.equal(videoPolicyLabel({ ...policy, reason: 'clip_window_end' }), 'ADVANCE · clip window end');
  assert.equal(videoPolicyLabel(null), 'No policy evaluation yet');
  assert.equal(videoPolicyLabel({ ...policy, action: 'stop', reason: 'playlist_exhausted', trigger: 'motor_right' }), 'END · playlist exhausted (motor right)');
  assert.equal(videoPolicyLabel({ ...policy, action: 'stop', reason: 'playlist_exhausted', trigger: 'clip_window_end' }), 'END · playlist exhausted (clip window end)');
});

test('video timeline groups only contiguous recorded clip intervals', () => {
  const segments = [
    { clip_id: 'clip-0', playback_start_tick: 0, playback_end_tick: 333 },
    { clip_id: 'clip-0', playback_start_tick: 333, playback_end_tick: 667 },
    { clip_id: 'clip-1', playback_start_tick: 667, playback_end_tick: 1000 },
  ];
  assert.deepEqual(videoTimelineBlocks({ segments }), [
    { clipId: 'clip-0', duration: 667 },
    { clipId: 'clip-1', duration: 333 },
  ]);
});

test('video overlay keeps the recorded decision and source PTS within narrow capture', () => {
  const calls = [], sample = sampleVideoAtTick(recording, 1000);
  const context = { font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
    measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
    fillText(text, x) { calls.push({ text, x, width: this.measureText(text).width }); },
  };
  drawOverlay(context, 320, 600, 320, recording, sample);
  assert.ok(calls.some(({ text }) => text.includes('PTS 0')));
  assert.ok(calls.some(({ text }) => text.includes('ADVANCE')));
  assert.ok(calls.some(({ text }) => text.includes('integrity-only')));
  for (const call of calls) assert.ok(call.x + call.width <= 320, `Clipped: ${call.text}`);
});

test('captured stop labels preserve both playlist exhaustion triggers without a swipe', () => {
  const context = { font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
    measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
    fillText(text, x) { this.calls.push({ text, x, width: this.measureText(text).width }); },
    calls: [],
  };
  for (const trigger of ['motor_right', 'clip_window_end']) {
    context.calls = [];
    const sample = { ...sampleVideoAtTick(recording, 1000), policy: { ...policy, action: 'stop', reason: 'playlist_exhausted', trigger } };
    drawOverlay(context, 320, 600, 320, recording, sample);
    assert.ok(context.calls.some(({ text }) => text.includes(`playlist exhausted (${trigger.replaceAll('_', ' ')})`)));
    assert.ok(context.calls.some(({ text }) => text.includes('integrity-only')));
    for (const call of context.calls) assert.ok(call.x + call.width <= 320, `Clipped: ${call.text}`);
    assert.equal(advanceGestureAtTick({ ...recording, segments: [{ ...recording.segments[0], video_policy: sample.policy }] }, 1000), null);
  }
});

test('empty captured overlay names both accepted recording formats', () => {
  for (const width of [320, 900]) {
    const context = { font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
      measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
      fillText(text, x) { this.calls.push({ text, x, width: this.measureText(text).width }); },
      calls: [],
    };
    drawOverlay(context, width, 600, width, null, null);
    assert.ok(context.calls.some(({ text }) => text.includes('measured-replay/v1')));
    assert.ok(context.calls.some(({ text }) => text.includes('measured-video-replay/v1')));
    for (const call of context.calls) assert.ok(call.x + call.width <= width, `Clipped: ${call.text}`);
  }
});

// Internal parser fixture only; never supplied as recorded or neural evidence.
function fixture() {
  const pixels = Buffer.alloc(90 * 160 * 3);
  const header = '{"dtype":"uint8","rank":3,"shape":[160,90,3],"version":"rgb-input/v1"}\n';
  const sha256 = createHash('sha256').update(header).update(pixels).digest('hex');
  const sourceTimeBase = [1, 30], frames = [], inputs = {}, segments = [];
  for (let index = 0; index < 120; index += 1) {
    const frameId = `clip-0/frame-${index}`;
    frames.push({ frame_id: frameId, frame_index: index, sha256, source_pts: index, source_time_base: sourceTimeBase });
    inputs[frameId] = { sha256, width: 90, height: 160, rgb_base64: pixels.toString('base64'), clip_id: 'clip-0', frame_index: index, source_pts: index, source_time_base: sourceTimeBase };
    const start = quantizeVideoTick(index), end = quantizeVideoTick(index + 1);
    const bins = [];
    for (let cursor = start; cursor < end;) {
      const duration = Math.min(100, end - cursor); cursor += duration;
      bins.push({ end_tick: cursor, duration_ticks: duration, group_spikes: { ...counts } });
    }
    const dwell = end >= 10000, final = index === 119;
    const window = index < 8 ? null : { start_tick: end - 3000, end_tick: end, frame_count: 9, counts: { motor_left: 0, motor_right: 0 }, populations: { motor_left: 1, motor_right: 1 } };
    const readout = window ? { adapter_version: 'lateral-motor-adapter/v1', signed_difference_hz: 0, evidence_strength: 0, action: 'defer' } : null;
    const video_policy = index % 3 === 2 ? { policy_version: 'right-scroll/v1', effective_tick: end, window, readout, minimum_dwell_met: dwell, action: final ? 'stop' : 'watch', reason: final ? 'playlist_exhausted' : dwell ? 'motor_left_or_defer' : 'minimum_dwell', trigger: final ? 'clip_window_end' : null, next_clip_index: final ? null : 0 } : null;
    segments.push({ event_sequence: index + 1, branch_id: 'video-observation/root', frame_id: frameId, clip_id: 'clip-0', frame_index: index, stimulation: null, learning: false, source_start_tick: start, source_end_tick: end, playback_start_tick: start, playback_end_tick: end, bins, video_policy });
  }
  const recipe = { policy_version: 'right-scroll/v1', adapter_version: 'lateral-motor-adapter/v1', action_threshold_hz: 1, sample_fps: [30, 1], sample_time_origin: 'first-decoded-pts', tick_quantization: 'nearest-0.1ms-half-up-cumulative/v1', window_ticks: 40000, session_limit_ticks: 80000, rolling_window_ticks: 3000, minimum_dwell_ticks: 10000, input_width: 90, input_height: 160, audio_input: false, stimulation: null, learning: false, pathway_detail: false, qualification_detail: false };
  const clip = { clip_id: 'clip-0', source_url: 'https://example.com/reel/one', source_path: 'fixture', source_sha256: 'e'.repeat(64), source_size: 1, source_width: 90, source_height: 160, source_sample_aspect_ratio: [0, 1], source_time_base: sourceTimeBase, origin_pts: 0, coverage_end_pts: 120, coverage_method: 'following_pts', decoder: { pyav_version: '19.0.2', ffmpeg_libraries: { libavcodec: [1, 0, 0] } }, transform: { width: 90, height: 160, inner_width: 90, inner_height: 160, padding: [0, 0, 0, 0], resize: 'bilinear', placement: 'centered-black-letterbox', pixel_format: 'rgb24', color_conversion: 'PyAV-to_ndarray-rgb24-FFmpeg-defaults', crop: 'none', orientation: 'reject-rotation-and-displaymatrix/v1' }, frames };
  const source = { run_kind: 'pilot', verification_mode: 'integrity-only', schema_sha256: 'a'.repeat(64), run_metadata_sha256: 'b'.repeat(64), events_sha256: 'c'.repeat(64), final_scientific_sha256: 'd'.repeat(64), metadata: { family: 'video-observation', protocol_version: 'video-observation/v1', stimulus_version: 'decoded-video-rgb/v1', seeds: [], factors: { clip_count: 1 }, input_sha256: [sha256], video_recipe: recipe, clips: [clip], engine_identity: { neural_groups: Object.fromEntries(Object.keys(groups).map((name) => [name, [0]])) } } };
  return { version: 'measured-video-replay/v1', tick_ms: .1, source, groups, inputs, segments, duration_ticks: 40000 };
}

test('new reader accepts exact portrait pixels and a complete recorded stop', async () => {
  const parsed = await parseVideoRecording(JSON.stringify(fixture()));
  assert.equal(parsed.segments.length, 120);
  assert.equal(parsed.inputs['clip-0/frame-0'].width, 90);
  assert.equal(parsed.inputs['clip-0/frame-0'].height, 160);
  assert.equal(parsed.segments.at(-1).video_policy.reason, 'playlist_exhausted');
});

test('new reader binds a recorded clip-window advance to the following input', async () => {
  const value = fixture(), second = structuredClone(value.source.metadata.clips[0]);
  second.clip_id = 'clip-1'; second.source_url = 'https://example.com/reel/two';
  second.frames.forEach((frame) => { frame.frame_id = frame.frame_id.replace('clip-0', 'clip-1'); });
  value.source.metadata.clips.push(second); value.source.metadata.factors.clip_count = 2;
  value.segments[119].video_policy = { ...value.segments[119].video_policy, action: 'advance', reason: 'clip_window_end', next_clip_index: 1 };
  for (const original of value.segments.slice(0, 120)) {
    const next = structuredClone(original);
    next.event_sequence += 120; next.clip_id = 'clip-1'; next.frame_id = next.frame_id.replace('clip-0', 'clip-1');
    for (const key of ['source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick']) next[key] += 40000;
    next.bins.forEach((bin) => { bin.end_tick += 40000; });
    if (next.video_policy) {
      next.video_policy.effective_tick += 40000;
      if (next.video_policy.window) { next.video_policy.window.start_tick += 40000; next.video_policy.window.end_tick += 40000; }
      if (next.frame_index === 119) { next.video_policy.action = 'stop'; next.video_policy.reason = 'session_limit'; next.video_policy.trigger = 'session_limit'; next.video_policy.next_clip_index = null; }
      else next.video_policy.next_clip_index = 1;
    }
    value.inputs[next.frame_id] = { ...value.inputs[original.frame_id], clip_id: 'clip-1' };
    value.segments.push(next);
  }
  value.duration_ticks = 80000;
  const parsed = await parseVideoRecording(JSON.stringify(value));
  const sample = sampleVideoAtTick(parsed, 40000);
  assert.equal(sample.input.clip_id, 'clip-1');
  assert.equal(sample.policy.reason, 'clip_window_end');
  assert.equal(sample.clipPolicy, null);
  assert.equal(sample.gesture.reason, 'clip_window_end');
  const fast = await parseVideoRecording(JSON.stringify(fastFixture(structuredClone(value))));
  assert.equal(sampleVideoAtTick(fast, 40000).input.clip_id, 'clip-1');
  assert.equal(sampleVideoAtTick(fast, 40000).policy.trigger, 'clip_window_end');
  assert.equal(sampleVideoAtTick(fast, 80000).policy.reason, 'session_limit');
  assert.equal(sampleVideoAtTick(fast, 80000).gesture, null);
});

test('new reader rejects unknown policy, pixel mutation and premature decision', async () => {
  for (const mutate of [
    (value) => { value.segments[2].video_policy.policy_version = 'unknown'; },
    (value) => { value.inputs['clip-0/frame-0'].rgb_base64 = Buffer.alloc(90 * 160 * 3, 1).toString('base64'); },
    (value) => { value.segments[0].video_policy = value.segments[2].video_policy; },
    (value) => { value.segments[10].bins[0].group_spikes.motor_right = -1; },
    (value) => { value.segments[0].source_end_tick = 334; },
    (value) => { value.segments[0].bins = [{ end_tick: 333, duration_ticks: 333, group_spikes: { ...counts } }]; },
    (value) => { value.source.metadata.clips[0].transform.padding = [1, 0, 0, 0]; },
    (value) => { value.source.metadata.clips[0].transform.crop = 'center'; },
    (value) => { value.source.metadata.clips[0].source_sample_aspect_ratio = [2, 1]; },
    (value) => { value.source.metadata.clips[0].frames[2].source_pts = 3; },
  ]) {
    const value = fixture(); mutate(value);
    await assert.rejects(parseVideoRecording(JSON.stringify(value)));
  }
});

test('version dispatch preserves the strict original reader', async () => {
  await assert.rejects(parseAnyRecording(JSON.stringify({ ...fixture(), version: 'measured-replay/v1' })));
});

function fastFixture(value = fixture()) {
  const metadata = value.source.metadata;
  value.version = 'measured-video-replay/v2';
  metadata.protocol_version = 'video-observation/v2'; metadata.stimulus_version = 'decoded-video-rgb/v2';
  Object.assign(metadata.video_recipe, { policy_version: 'right-scroll/v2', minimum_dwell_ticks: 30000, source_speed: [5, 1], source_window_seconds: 20 });
  for (const clip of metadata.clips) {
    clip.coverage_end_pts = 600;
    clip.frames.forEach((frame) => { frame.source_pts *= 5; });
  }
  Object.values(value.inputs).forEach((input) => { input.source_pts *= 5; });
  for (const segment of value.segments) if (segment.video_policy) {
    const decision = segment.video_policy;
    decision.policy_version = 'right-scroll/v2'; decision.minimum_dwell_met = segment.frame_index >= 89;
    if (decision.action === 'watch') decision.reason = decision.minimum_dwell_met ? 'motor_left_or_defer' : 'minimum_dwell';
  }
  return value;
}

test('v2 dispatch accepts 20s media in 4s simulation and the 3s dwell boundary', async () => {
  const parsed = await parseAnyRecording(JSON.stringify(fastFixture()));
  assert.equal(parsed.version, 'measured-video-replay/v2');
  assert.equal(parsed.duration_ticks, 40000);
  assert.equal(parsed.inputs['clip-0/frame-119'].source_pts, 595);
  assert.equal(parsed.segments[86].video_policy.minimum_dwell_met, false);
  assert.equal(parsed.segments[86].video_policy.reason, 'minimum_dwell');
  assert.equal(parsed.segments[89].video_policy.minimum_dwell_met, true);
  assert.equal(parsed.segments[89].video_policy.reason, 'motor_left_or_defer');
});

test('v2 rejects mixed versions, nonclosed speed/recipe, short coverage, future media and early dwell', async () => {
  for (const mutate of [
    (v) => { v.version = 'measured-video-replay/v1'; },
    (v) => { v.source.metadata.protocol_version = 'video-observation/v1'; },
    (v) => { v.source.metadata.stimulus_version = 'decoded-video-rgb/v1'; },
    (v) => { v.source.metadata.video_recipe.policy_version = 'right-scroll/v1'; },
    (v) => { v.source.metadata.video_recipe.minimum_dwell_ticks = 10000; },
    (v) => { v.source.metadata.video_recipe.source_speed = [4, 1]; },
    (v) => { v.source.metadata.video_recipe.source_window_seconds = 4; },
    (v) => { delete v.source.metadata.video_recipe.source_speed; },
    (v) => { v.source.metadata.video_recipe.speed = 5; },
    (v) => { v.source.metadata.clips[0].coverage_end_pts = 599; },
    (v) => { v.source.metadata.clips[0].frames[119].source_pts = 596; },
    (v) => { v.inputs['clip-0/frame-119'].source_pts = 119; },
    (v) => { v.segments[86].video_policy.minimum_dwell_met = true; },
    (v) => { v.segments[89].video_policy.policy_version = 'right-scroll/v1'; },
    (v) => { v.segments[119].video_policy.action = 'advance'; },
  ]) {
    const value = fastFixture(); mutate(value);
    await assert.rejects(parseAnyRecording(JSON.stringify(value)));
  }
  const v1 = fixture(); v1.source.metadata.video_recipe.source_speed = [1, 1];
  await assert.rejects(parseAnyRecording(JSON.stringify(v1)));
});

test('v2 measured right readout watches through 2.9s then causally advances at 3s', async () => {
  const value = fastFixture(), metadata = value.source.metadata, second = structuredClone(metadata.clips[0]);
  second.clip_id = 'clip-1'; second.frames.forEach((frame) => { frame.frame_id = frame.frame_id.replace('clip-0', 'clip-1'); });
  metadata.clips.push(second); metadata.factors.clip_count = 2;
  value.segments = value.segments.slice(0, 90);
  for (const id of Object.keys(value.inputs)) if (value.inputs[id].frame_index >= 90) delete value.inputs[id];
  for (const segment of value.segments) {
    segment.bins[0].group_spikes.motor_right = 1;
    if (segment.video_policy?.window) {
      segment.video_policy.window.counts.motor_right = 9;
      segment.video_policy.readout = { adapter_version: 'lateral-motor-adapter/v1', signed_difference_hz: 30, evidence_strength: 1, action: 'inspect_right' };
    }
  }
  Object.assign(value.segments[89].video_policy, { action: 'advance', reason: 'motor_right', trigger: 'motor_right', next_clip_index: 1 });
  for (const segment of value.segments.slice()) {
    const next = structuredClone(segment);
    next.event_sequence += 90; next.clip_id = 'clip-1'; next.frame_id = next.frame_id.replace('clip-0', 'clip-1');
    for (const key of ['source_start_tick', 'source_end_tick', 'playback_start_tick', 'playback_end_tick']) next[key] += 30000;
    next.bins.forEach((bin) => { bin.end_tick += 30000; });
    if (next.video_policy) {
      next.video_policy.effective_tick += 30000; next.video_policy.next_clip_index = 1;
      if (next.video_policy.window) { next.video_policy.window.start_tick += 30000; next.video_policy.window.end_tick += 30000; }
      if (next.frame_index === 89) Object.assign(next.video_policy, { action: 'stop', reason: 'playlist_exhausted', next_clip_index: null });
    }
    value.inputs[next.frame_id] = { ...value.inputs[segment.frame_id], clip_id: 'clip-1' };
    value.segments.push(next);
  }
  value.duration_ticks = 60000;
  const parsed = await parseVideoRecording(JSON.stringify(value));
  assert.equal(parsed.segments[86].video_policy.readout.action, 'inspect_right');
  assert.equal(parsed.segments[86].video_policy.action, 'watch');
  assert.equal(sampleVideoAtTick(parsed, 29999).input.clip_id, 'clip-0');
  const incoming = sampleVideoAtTick(parsed, 30000);
  assert.equal(incoming.input.clip_id, 'clip-1'); assert.equal(incoming.input.frame_index, 0);
  assert.equal(incoming.policy.action, 'advance'); assert.equal(incoming.policy.effective_tick, 30000);
  assert.equal(sampleVideoAtTick(parsed, 60000).policy.reason, 'playlist_exhausted');
  assert.equal(sampleVideoAtTick(parsed, 60000).gesture, null);
  for (const mutate of [
    (v) => { v.segments[86].video_policy.action = 'advance'; v.segments[86].video_policy.reason = 'motor_right'; },
    (v) => { v.segments[90].frame_id = 'clip-0/frame-0'; },
    (v) => { v.segments[89].video_policy.next_clip_index = 0; },
  ]) {
    const changed = structuredClone(value); mutate(changed); await assert.rejects(parseVideoRecording(JSON.stringify(changed)));
  }
});

test('200ms transition binds last actually fed outgoing and current incoming across seek', () => {
  const value = structuredClone(recording), incoming = value.segments[1];
  incoming.playback_end_tick = incoming.source_end_tick = 1333;
  for (let index = 1; index < 7; index += 1) {
    const id = `incoming-${index}`, start = 1000 + Math.round(index * 1000 / 3), end = 1000 + Math.round((index + 1) * 1000 / 3);
    value.inputs[id] = { ...value.inputs.second, frame_index: index };
    value.segments.push({ ...incoming, frame_id: id, frame_index: index, playback_start_tick: start, source_start_tick: start, playback_end_tick: end, source_end_tick: end });
  }
  value.duration_ticks = 3333;
  assert.equal(advanceGestureAtTick(value, 999), null);
  assert.deepEqual(advanceGestureAtTick(value, 1000), { reason: 'motor_right', progress: 0, outgoingFrameId: 'first', incomingFrameId: 'second' });
  assert.equal(advanceGestureAtTick(value, 1700).incomingFrameId, 'incoming-2');
  assert.equal(advanceGestureAtTick(value, 2999).incomingFrameId, 'incoming-5');
  assert.equal(advanceGestureAtTick(value, 3000), null);
  assert.equal(advanceGestureAtTick(value, 1000).progress, 0);
  assert.equal(advanceGestureAtTick(value, 1500).progress, .25);
  assert.equal(advanceGestureAtTick(value, 1500, true), null);
  assert.equal(sampleVideoAtTick(value, 1700).input, value.inputs['incoming-2']);
});

test('swipe surface clips both images, reuses its texture and releases it', () => {
  const calls = [], context = {
    save() { calls.push(['save']); }, restore() { calls.push(['restore']); },
    beginPath() {}, rect(...args) { calls.push(['rect', ...args]); }, clip() { calls.push(['clip']); },
    clearRect(...args) { calls.push(['clear', ...args]); }, drawImage(...args) { calls.push(['draw', ...args]); },
  };
  const canvas = { width: 90, height: 160, getContext() { return context; } };
  const surface = stage.createVideoSwipeSurface(canvas), texture = surface.texture;
  const outgoing = { id: 'last-fed' }, incoming = { id: 'current-fed' };
  surface.draw(outgoing, incoming, .25);
  assert.deepEqual(calls, [['save'], ['rect', 0, 0, 90, 160], ['clip'], ['clear', 0, 0, 90, 160], ['draw', outgoing, 0, -40, 90, 160], ['draw', incoming, 0, 120, 90, 160], ['restore']]);
  assert.equal(context.imageSmoothingEnabled, false);
  surface.draw(outgoing, { id: 'next-current-fed' }, .5);
  assert.equal(surface.texture, texture);
  let disposed = 0; texture.addEventListener('dispose', () => { disposed += 1; });
  surface.dispose(); assert.equal(disposed, 1); assert.equal(canvas.width, 1); assert.equal(canvas.height, 1);
});

test('v2 capture labels speed and distinguishes simulation clock from media PTS and swipe', () => {
  const value = { ...recording, version: 'measured-video-replay/v2' }, calls = [];
  const context = { font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
    measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
    fillText(text, x) { calls.push({ text, x, width: this.measureText(text).width }); },
  };
  drawOverlay(context, 320, 600, 320, value, sampleVideoAtTick(value, 1000));
  assert.ok(calls.some(({ text }) => text.includes('Reel 5×')));
  assert.ok(calls.some(({ text }) => text.includes('Sim ') && text.includes('media PTS')));
  assert.ok(calls.some(({ text }) => text.includes('Illustrative swipe')));
  for (const call of calls) assert.ok(call.x + call.width <= 320, `Clipped: ${call.text}`);
  calls.length = 0;
  drawOverlay(context, 900, 900, 900, value, sampleVideoAtTick(value, 1000));
  assert.ok(calls.some(({ text }) => text.includes('Reel 5×')));
  assert.ok(calls.some(({ text }) => text.includes('Illustrative swipe')));
  for (const call of calls) assert.ok(call.x + call.width <= 900, `Clipped: ${call.text}`);
  calls.length = 0;
  drawOverlay(context, 900, 900, 900, value, sampleVideoAtTick(value, 1000), false, true);
  assert.ok(!calls.some(({ text }) => text.includes('Illustrative swipe')));
});
