import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { parseEventRecording, sampleEventAtTick, eventPresentation, eventPlanJson } from '../src/event-replay.ts';
import { parseRecording } from '../src/replay.ts';
import { parseVideoRecording } from '../src/video-replay.ts';
import { parseAnyRecording } from '../src/recording.ts';
import { createEventBoard, drawEventPlan, drawOverlay } from '../src/stage.ts';
import * as THREE from 'three';
import { createOperationGate } from '../src/operation.ts';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { stripTypeScriptTypes } from 'node:module';
import * as replayModule from '../src/replay.ts';
import * as videoModule from '../src/video-replay.ts';
import * as recordingModule from '../src/recording.ts';
import * as eventModule from '../src/event-replay.ts';
import * as exportModule from '../src/export.ts';
import * as anatomyModule from '../src/anatomy.ts';
import * as cellModule from '../src/cell-activity.ts';

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
const parse = (value) => parseEventRecording(JSON.stringify(value));

test('event reader derives final 500ms left/right/defer from integer counts and populations', async () => {
  for (const [l, r, action] of [[0, 2, 'inspect_right'], [2, 0, 'inspect_left'], [1, 1, 'defer'], [0, 0, 'defer'], [0, 1, 'defer'], [1, 0, 'defer']]) {
    const recording = await parse(eventFixture(l, r));
    assert.equal(recording.decision.readout.action, action);
    assert.equal(sampleEventAtTick(recording, 19900).rates.motor_right, r * 50);
  }
});

test('choice, highlight, plan JSON and download remain unavailable through tick19999 and return on reverse seek', async () => {
  const recording = await parse(eventFixture());
  for (const tick of [0, 15000, 19999]) {
    const sample = sampleEventAtTick(recording, tick), view = eventPresentation(sample);
    assert.equal(sample.decision, null); assert.equal(sample.plan, null);
    assert.equal(view.selectedSide, null); assert.equal(view.canDownload, false); assert.equal(view.status, 'Choice pending · final 500 ms decision at 2.000 s');
    assert.equal(eventPlanJson(sample), null);
  }
  const sample = sampleEventAtTick(recording, 20000), view = eventPresentation(sample);
  assert.equal(view.selectedSide, 'right'); assert.equal(view.canDownload, true);
  assert.equal(view.title, 'Night lights');
  assert.deepEqual(JSON.parse(eventPlanJson(sample)), recording.plan);
  assert.equal(sampleEventAtTick(recording, 999999).tick, 20000);
  assert.equal(sampleEventAtTick(recording, 0).plan, null);
  assert.throws(() => sampleEventAtTick(recording, NaN));
});

test('terminal defer stays explicit without selected proposal or highlighted side', async () => {
  const recording = await parse(eventFixture(0, 0));
  const sample = sampleEventAtTick(recording, 20000), view = eventPresentation(sample);
  assert.equal(view.selectedSide, null); assert.equal(view.title, 'No option selected');
  assert.equal(view.status, 'Deferred · measured lateral difference stays within ±1 Hz/cell');
  assert.equal(JSON.parse(eventPlanJson(sample)).selected_option, null);
});

test('bound plan download is unavailable while another file loads or video exports', async () => {
  const recording = await parse(eventFixture()), sample = sampleEventAtTick(recording, 20000), gate = createOperationGate();
  const token = gate.beginLoad(); assert.equal(eventPlanJson(sample, gate), null);
  gate.endLoad(token); assert.deepEqual(JSON.parse(eventPlanJson(sample, gate)), recording.plan);
  assert.equal(gate.beginExport(), true); assert.equal(eventPlanJson(sample, gate), null);
  assert.equal(gate.beginLoad(), null); gate.endExport(); assert.ok(eventPlanJson(sample, gate));
});

test('shared event canvas presentation shows the bound plan only at the terminal decision', async () => {
  const recording = await parseAnyRecording(JSON.stringify(eventFixture()));
  for (const tick of [19999, 20000, 0]) {
    const lines = [], context = { save() {}, restore() {}, fillRect() {}, fillText(text) { lines.push(text); }, measureText(text) { return { width: text.length * 6 }; } };
    drawEventPlan(context, 900, sampleEventAtTick(recording, tick));
    assert.equal(lines.some((text) => text.includes('Night lights')), tick === 20000);
    assert.equal(lines.some((text) => text.includes('Techno')), tick === 20000);
    assert.equal(lines.some((text) => text.includes('Final 500 ms')), tick === 20000);
  }
});

test('maximum programme canvas panel stays above default board and bounds narrow text', async () => {
  const value = eventFixture();
  value.source.metadata.proposal.options[1].programme = Array.from({ length: 6 }, (_, index) => ({ start_minute: index * 30, label: 'Programme label for the evening guests' }));
  value.source.metadata.proposal_sha256 = hash(JSON.stringify(canonical(value.source.metadata.proposal)));
  value.plan.selected_option = structuredClone(value.source.metadata.proposal.options[1]);
  const recording = await parse(value);
  for (const width of [320, 390, 900]) {
    const texts = [], boxes = [];
    const context = { font: '', save() {}, restore() {}, fillRect(x, y, w, h) { boxes.push({ x, y, w, h }); },
      fillText(text, x, y, maxWidth) { texts.push({ text, x, y, width: Math.min(this.measureText(text).width, maxWidth ?? Infinity) }); },
      measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
    };
    drawEventPlan(context, width, sampleEventAtTick(recording, 20000));
    if (width === 900) assert.ok(boxes.every(({ y, h }) => y + h <= 225));
    assert.ok(texts.every(({ x, width: textWidth }) => x + textWidth <= width - 22));
  }
});

test('final count measurement wraps into readable lines instead of shrinking with long feed context', async () => {
  const recording = await parse(eventFixture());
  const sample = { ...sampleEventAtTick(recording, 20000), feedContext: 'Feed ended at 7.000 s · END · playlist exhausted (clip window end)' };
  for (const width of [390, 900]) {
    const calls = [], context = { font: '', save() {}, restore() {}, fillRect() {},
      measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
      fillText(text, x, y) { calls.push({ text, font: this.font, width: this.measureText(text).width }); } };
    drawEventPlan(context, width, sample);
    const measurement = calls.find(call => call.text.includes('Final 500 ms'));
    assert.ok(Number(measurement.font.match(/(\d+)px/)[1]) >= 12);
    assert.ok(calls.filter(call => call.text.includes('Final 500 ms') || call.text.includes('Feed ended')).every(call => call.width <= width - 44));
  }
});

test('landscape board uses the fed texture unchanged and highlights only an effective selected side', async () => {
  const board = createEventBoard(), texture = new THREE.Texture();
  const selected = await parse(eventFixture()), deferred = await parse(eventFixture(0, 0));
  assert.equal(board.screen.geometry.parameters.width / board.screen.geometry.parameters.height, 384 / 216);
  for (const [recording, tick, left, right] of [[selected, 0, false, false], [selected, 19999, false, false], [selected, 20000, false, true], [selected, 0, false, false], [deferred, 20000, false, false]]) {
    board.setSample(sampleEventAtTick(recording, tick), texture);
    assert.equal(board.screen.material.map, texture);
    assert.equal(board.highlights.left.visible, left); assert.equal(board.highlights.right.visible, right);
  }
  texture.dispose();
});

test('strict event contract rejects mutations instead of rewriting decision, plan, clocks, proposal or pixels', async () => {
  const mutations = [
    (v) => { v.extra = true; }, (v) => { v.source.verification_mode = 'native-replay'; },
    (v) => { v.source.metadata.extra = true; }, (v) => { v.source.metadata.choice_recipe.action_threshold_hz = .9; },
    (v) => { v.source.metadata.factors.left_option_id = 'warehouse'; },
    (v) => { v.source.metadata.proposal.options[0].title = 'Changed'; },
    (v) => { v.source.metadata.proposal.options[0].selected_option_id = 'rooftop'; },
    (v) => { v.source.metadata.proposal_source.name = '../options.json'; },
    (v) => { v.source.metadata.proposal_source.name = 'www.example.com'; },
    (v) => { v.source.metadata.renderer_recipe.pillow_version = '0'; },
    (v) => { v.inputs.options.rgb_base64 = Buffer.alloc(384 * 216 * 3).toString('base64'); },
    (v) => { v.inputs.options.width = 383; }, (v) => { v.source.metadata.input.sha256 = '0'.repeat(64); },
    (v) => { v.segments[0].source_start_tick = 1; }, (v) => { v.segments[3].playback_end_tick = 20001; },
    (v) => { v.segments.reverse(); }, (v) => { v.segments[0].event_sequence = 2; },
    (v) => { v.segments[0].branch_id = 'other'; }, (v) => { v.segments[0].frame_id = 'else'; },
    (v) => { v.segments[0].learning = true; }, (v) => { v.segments[0].bins[0].group_spikes.kc = -1; },
    (v) => { v.segments[0].bins[0].group_spikes.kc = 10001; },
    (v) => { v.segments[3].bins[0].group_spikes.motor_right++; },
    (v) => { v.decision.effective_tick = 19999; }, (v) => { v.decision.window_start_tick = 0; },
    (v) => { v.decision.event_sequence = 3; }, (v) => { v.decision.counts.motor_right++; },
    (v) => { v.decision.populations.motor_right++; }, (v) => { v.decision.selected_option_id = 'rooftop'; },
    (v) => { v.decision.readout.signed_difference_hz = 1; }, (v) => { v.decision.readout.action = 'inspect_left'; },
    (v) => { v.plan.selected_option.music = 'Rewritten'; }, (v) => { v.plan.source.metadata = v.source.metadata; },
    (v) => { v.plan.decision_ref.scientific_sha256 = '0'.repeat(64); }, (v) => { v.plan.status = 'deferred'; },
  ];
  for (const mutate of mutations) { const value = eventFixture(); mutate(value); await assert.rejects(parse(value), undefined, String(mutate)); }
});

test('strict ±1 boundary uses count-derived action even when claimed float is tolerance-close', async () => {
  const drift = eventFixture(0, 1);
  drift.decision.readout.signed_difference_hz = 1 + 1e-12;
  await assert.rejects(parse(drift));
  const value = eventFixture(0, 1);
  value.decision.readout.signed_difference_hz = 1 + 1e-12;
  value.decision.readout.action = 'inspect_right'; value.decision.selected_option_id = 'warehouse';
  await assert.rejects(parse(value));
});

test('event bounds and duplicate keys are rejected, old readers cross-reject event files', async () => {
  const value = eventFixture();
  await assert.rejects(parseEventRecording(JSON.stringify(value).replace('"version":', '"version":"event-choice-replay/v1","version":')));
  await assert.rejects(parseEventRecording(' '.repeat(2 * 1024 * 1024 + 1)));
  await assert.rejects(parseRecording(JSON.stringify(value))); await assert.rejects(parseVideoRecording(JSON.stringify(value)));
  value.version = 'measured-replay/v1'; await assert.rejects(parse(value));
});

test('exact 200-bin coverage is accepted, 201 bins and missing/boolean/duplicate population evidence fail', async () => {
  const makeBins = (count, start) => Array.from({ length: count }, (_, index) => {
    const begin = Math.floor(index * 5000 / count), end = Math.floor((index + 1) * 5000 / count);
    return { end_tick: start + end, duration_ticks: end - begin, group_spikes: { kc: 0, pam11: 0, ppl101: 0, mbon07: 0, mbon11: 0, motor_left: 0, motor_right: start === 15000 && index === count - 1 ? 2 : 0 } };
  });
  const value = eventFixture(); value.segments.forEach((segment, index) => { segment.bins = makeBins(50, index * 5000); });
  await parse(value); value.segments[0].bins = makeBins(51, 0); await assert.rejects(parse(value));
  for (const change of [(v) => { delete v.segments[0].bins[0].group_spikes.kc; }, (v) => { v.segments[0].bins[0].group_spikes.kc = false; }, (v) => { v.source.metadata.engine_identity.neural_groups.motor_left = [0, 0]; }, (v) => { v.groups.motor_right = 3; }, (v) => { v.segments.push(v.segments[3]); }]) {
    const invalid = eventFixture(); change(invalid); await assert.rejects(parse(invalid));
  }
});

test('fixed 10 ms resolution rejects aggregate, redistributed, 199-bin and 201-bin evidence', async () => {
  const valid = eventFixture(); assert.equal((await parse(valid)).segments.flatMap((segment) => segment.bins).length, 200);
  const merged = eventFixture();
  for (const segment of merged.segments) {
    const sums = Object.fromEntries(Object.keys(merged.groups).map((name) => [name, segment.bins.reduce((sum, bin) => sum + bin.group_spikes[name], 0)]));
    segment.bins = [{ end_tick: segment.source_end_tick, duration_ticks: 5000, group_spikes: sums }];
  }
  await assert.rejects(parse(merged), undefined, 'four aggregated500ms bins lose native resolution');
  const redistributed = eventFixture();
  redistributed.segments[0].bins[0].duration_ticks = 99; redistributed.segments[0].bins[0].end_tick = 99;
  redistributed.segments[0].bins[1].duration_ticks = 101;
  await assert.rejects(parse(redistributed), undefined, '200 bins with redistributed durations');
  const fewer = eventFixture();
  fewer.segments[0].bins[1].duration_ticks = 200; fewer.segments[0].bins.shift();
  await assert.rejects(parse(fewer), undefined, '199 complete bins');
  const more = eventFixture();
  const first = more.segments[0].bins[0]; first.duration_ticks = 50;
  more.segments[0].bins.unshift({ ...first, end_tick: 50, group_spikes: { ...first.group_spikes } });
  await assert.rejects(parse(more), undefined, '201 complete bins');
});

test('narrow terminal event hold caption stays bounded without changing terminal sample', async () => {
  const recording = await parse(eventFixture()), sample = sampleEventAtTick(recording, 20000), before = JSON.stringify(sample);
  for (const width of [320, 390]) {
    const calls = [], context = { font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
      measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * .55 }; },
      fillText(text, x, _y, maxWidth) { calls.push({ text, x, width: Math.min(this.measureText(text).width, maxWidth ?? Infinity) }); },
    };
    drawOverlay(context, width, 600, width, recording, sample, true);
    assert.ok(calls.some(({ text }) => text.includes('presentation hold')));
    assert.ok(calls.every(({ x, width: textWidth }) => x + textWidth <= width), `${width}px terminal caption overflow`);
  }
  assert.equal(JSON.stringify(sample), before);
});

test('late codec completion labels the current event recording with its three-second hold', async () => {
  const nodes = new Map();
  const context = { beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, clearRect() {}, drawImage() {} };
  function node() {
    return { textContent: '', hidden: false, disabled: false, value: '1', clientWidth: 200, width: 0, height: 0, handlers: {}, style: {}, classList: { add() {} }, append() {}, replaceChildren() {}, setAttribute() {}, getContext() { return context; }, addEventListener(name, handler) { this.handlers[name] = handler; } };
  }
  const document = { getElementById(id) { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); }, createElement() { return node(); } };
  let finishCapability;
  const capability = new Promise((resolve) => { finishCapability = resolve; });
  const stage = { renderer: { setAnimationLoop() {} }, setRecording() {}, setAnatomy() {}, setCellActivity() {}, setSample() {}, render() {} };
  const source = readFileSync(new URL('../src/main.ts', import.meta.url), 'utf8');
  const javascript = stripTypeScriptTypes(source).replace(/^import .+;\r?$/gm, '');
  // Execute real main control flow without a browser/WebGL/encoder. The pending
  // encoder is a controlled external dependency; parser and sampling stay real.
  runInNewContext(javascript, { ...replayModule, ...exportModule, ...anatomyModule, ...cellModule, ...videoModule, ...recordingModule, ...eventModule, sampleAt: recordingModule.sampleAnyAtTick, createOperationGate, createStage: () => stage, canEncodeVideo: () => capability, document, performance, VideoEncoder: class {}, window: { addEventListener() {} }, setTimeout });
  const file = nodes.get('file'), json = JSON.stringify(eventFixture());
  file.files = [{ name: 'event.json', size: Buffer.byteLength(json), arrayBuffer: async () => new TextEncoder().encode(json).buffer }];
  await file.handlers.change();
  assert.equal(nodes.get('error').hidden, true);
  assert.equal(nodes.get('video-note').textContent, 'Checking WebCodecs video encoding support…');
  finishCapability(true); await new Promise(setImmediate);
  assert.match(nodes.get('video-note').textContent, /Last 3 s holds the measured terminal sample/);
  assert.equal(nodes.get('video').disabled, false);
});

test('only final-window integer counts set decision despite unequal motor populations and earlier activity', async () => {
  const value = eventFixture(2, 3, 2, 6);
  // L=2/(2*.5)=2, R=3/(6*.5)=1: exactly -1, therefore defer.
  value.segments[0].bins[0].group_spikes.motor_right = 200;
  const recording = await parse(value);
  assert.equal(recording.decision.readout.action, 'defer');
  assert.equal(recording.decision.readout.signed_difference_hz, -1);
  assert.equal(eventPresentation(sampleEventAtTick(recording, 20000)).selectedSide, null);
});

test('event proposal text remains plain text, URLs and inconsistent capacity are rejected', async () => {
  for (const change of [(p) => { p.options[0].music = 'https://bad.test'; }, (p) => { p.options[0].capacity = 39; }, (p) => { p.brief.guests = true; }, (p) => { p.options[0].programme[1].start_minute = 0; }]) {
    const value = eventFixture(); change(value.source.metadata.proposal);
    value.source.metadata.proposal_sha256 = hash(JSON.stringify(canonical(value.source.metadata.proposal)));
    await assert.rejects(parse(value));
  }
});
