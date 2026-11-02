import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { parseRecording, sampleAtTick, advancePlayback } from '../src/replay.ts';
import { drawOverlay } from '../src/stage.ts';
import { parseAnyRecording, sampleAnyAtTick } from '../src/recording.ts';

// INTERNAL fixture only. This is never bundled or offered as a recording.
function fixture() {
  const groups = { kc: 2, pam11: 1, ppl101: 1, mbon07: 1, mbon11: 1, motor_left: 1, motor_right: 1 };
  const counts = { kc: 2, pam11: 0, ppl101: 0, mbon07: 0, mbon11: 1, motor_left: 0, motor_right: 0 };
  const input = (rgb) => {
    const bytes = Buffer.from(rgb);
    const header = '{"dtype":"uint8","rank":3,"shape":[1,1,3],"version":"rgb-input/v1"}\n';
    return { sha256: createHash('sha256').update(header).update(bytes).digest('hex'), width: 1, height: 1, rgb_base64: bytes.toString('base64') };
  };
  const inputs = { A: input([255, 0, 0]), B: input([0, 255, 0]), black: input([0, 0, 0]) };
  const source = {
    run_kind: 'pilot', verification_mode: 'integrity-only', schema_sha256: 'a'.repeat(64),
    run_metadata_sha256: 'b'.repeat(64), events_sha256: 'c'.repeat(64), final_scientific_sha256: 'd'.repeat(64),
    metadata: { family: 'measured-observation', protocol_version: 'measured-observation/v1', engine_identity: { neural_groups: Object.fromEntries(Object.entries(groups).map(([key, count]) => [key, Array.from({ length: count }, (_, i) => i)])) }, input_sha256: Object.values(inputs).map((i) => i.sha256) },
  };
  return {
    version: 'measured-replay/v1', tick_ms: 0.1, source, groups, inputs,
    segments: ['A', 'black', 'B', 'black'].map((stimulus, index) => ({
      event_sequence: index + 3, branch_id: 'root', stimulus, stimulation: null, learning: false,
      source_start_tick: 100 + index * 100, source_end_tick: 200 + index * 100,
      playback_start_tick: index * 100, playback_end_tick: (index + 1) * 100,
      bins: [{ end_tick: 200 + index * 100, duration_ticks: 100, group_spikes: { ...counts, kc: index ? 0 : 2 } }],
    })), duration_ticks: 400,
  };
}
const parse = (value) => parseRecording(JSON.stringify(value));

test('raw population counts become Hz; zero remains an available measured zero', async () => {
  const recording = await parse(fixture());
  assert.deepEqual(await parseAnyRecording(JSON.stringify(fixture())), recording);
  assert.deepEqual(sampleAnyAtTick(recording, 0), sampleAtTick(recording, 0));
  const first = sampleAtTick(recording, 0);
  assert.equal(first.rates.kc, 100);
  assert.equal(first.rates.mbon11, 100);
  assert.equal(first.rates.motor_left, 0);
  assert.equal(first.sourceTick, 100);
  assert.equal(sampleAtTick(recording, 100).rates.kc, 0);
});

test('half-open segment boundaries and seek preserve source clocks without sorting', async () => {
  const recording = await parse(fixture());
  assert.equal(sampleAtTick(recording, 99).segment.stimulus, 'A');
  assert.equal(sampleAtTick(recording, 100).segment.stimulus, 'black');
  assert.equal(sampleAtTick(recording, 200).segment.stimulus, 'B');
  assert.equal(sampleAtTick(recording, 400).segment.stimulus, 'black');
  assert.equal(sampleAtTick(recording, 400).sourceTick, 500);
  assert.equal(sampleAtTick(recording, 0).segment.stimulus, 'A');
});

test('exact raw-bin boundaries select the next bin; seek clamps negative/end ticks', async () => {
  const value = fixture();
  value.segments[0].bins = [
    { end_tick: 150, duration_ticks: 50, group_spikes: { ...value.segments[0].bins[0].group_spikes } },
    { end_tick: 200, duration_ticks: 50, group_spikes: { ...value.segments[0].bins[0].group_spikes, mbon11: 0 } },
  ];
  const recording = await parse(value);
  assert.equal(sampleAtTick(recording, 49).rates.mbon11, 200);
  assert.equal(sampleAtTick(recording, 50).rates.mbon11, 0);
  assert.equal(sampleAtTick(recording, 50).bin.group_spikes.mbon11, 0);
  assert.equal(sampleAtTick(recording, -1).tick, 0);
  assert.equal(sampleAtTick(recording, 999).tick, 400);
  assert.throws(() => sampleAtTick(recording, NaN));
});

test('playback pauses, applies speed, clamps seek/end and never advances beyond duration', () => {
  assert.deepEqual(advancePlayback(100, 10, 2, false, 400), { tick: 100, playing: false });
  assert.deepEqual(advancePlayback(100, 10, 2, true, 400), { tick: 300, playing: true });
  assert.deepEqual(advancePlayback(300, 10, 2, true, 400), { tick: 400, playing: false });
  assert.throws(() => advancePlayback(0, NaN, 1, true, 400));
});

test('accepts 2000 complete bins and rejects a contiguous 2004-bin recording', async () => {
  const manyBins = (count) => {
    const value = fixture();
    value.duration_ticks = count * 4;
    value.segments.forEach((segment, index) => {
      segment.source_start_tick = 100 + index * count;
      segment.source_end_tick = 100 + (index + 1) * count;
      segment.playback_start_tick = index * count;
      segment.playback_end_tick = (index + 1) * count;
      segment.bins = Array.from({ length: count }, (_, i) => ({ end_tick: segment.source_start_tick + i + 1, duration_ticks: 1, group_spikes: { kc: 0, pam11: 0, ppl101: 0, mbon07: 0, mbon11: 0, motor_left: 0, motor_right: 0 } }));
    });
    return value;
  };
  assert.equal((await parse(manyBins(500))).duration_ticks, 2000);
  await assert.rejects(parse(manyBins(501)), /2000 bins/);
});

const mutations = [
  ['missing zero count', (v) => { delete v.segments[0].bins[0].group_spikes.motor_left; }],
  ['boolean count', (v) => { v.segments[0].bins[0].group_spikes.kc = true; }],
  ['negative count', (v) => { v.segments[0].bins[0].group_spikes.kc = -1; }],
  ['fractional count', (v) => { v.segments[0].bins[0].group_spikes.kc = 0.5; }],
  ['count greater than cells times ticks', (v) => { v.segments[0].bins[0].group_spikes.kc = 201; }],
  ['population missing', (v) => { delete v.groups.ppl101; }],
  ['population zero', (v) => { v.groups.ppl101 = 0; }],
  ['fork', (v) => { v.segments[1].branch_id = 'fork'; }],
  ['source rewind', (v) => { v.segments[1].source_start_tick = 0; }],
  ['playback gap', (v) => { v.segments[1].playback_start_tick += 1; }],
  ['event reorder', (v) => { v.segments[1].event_sequence = 1; }],
  ['partial bin coverage', (v) => { v.segments[0].bins[0].duration_ticks = 99; }],
  ['learning flag', (v) => { v.segments[0].learning = true; }],
  ['stimulation flag', (v) => { v.segments[0].stimulation = {}; }],
  ['unknown version', (v) => { v.version = 'measured-replay/v2'; }],
  ['unknown field', (v) => { v.demo = true; }],
  ['malformed binding', (v) => { v.source.events_sha256 = 'hello'; }],
  ['false native mode', (v) => { v.source.verification_mode = 'native'; }],
  ['unsupported protocol', (v) => { v.source.metadata.protocol_version = 'unknown'; }],
  ['population-map mismatch', (v) => { v.source.metadata.engine_identity.neural_groups.kc = [0]; }],
  ['duplicate map IDs', (v) => { v.source.metadata.engine_identity.neural_groups.kc = [0, 0]; }],
  ['input absent from metadata', (v) => { v.source.metadata.input_sha256 = []; }],
  ['pixel hash mismatch', (v) => { v.inputs.A.rgb_base64 = 'AAAA'; }],
  ['image dimensions mismatch', (v) => { v.inputs.A.width = 2; }],
  ['black is nonblack', (v) => { v.inputs.black = v.inputs.A; }],
  ['excess segments', (v) => { v.segments = Array(41).fill(v.segments[0]); }],
  ['duration mismatch', (v) => { v.duration_ticks += 1; }],
  ['boolean tick', (v) => { v.segments[0].source_start_tick = true; }],
  ['fractional tick', (v) => { v.segments[0].source_start_tick = 100.5; }],
  ['false initial playback offset', (v) => { v.segments[0].playback_start_tick = 1; }],
];
for (const [name, mutate] of mutations) test(`rejects ${name}`, async () => {
  const value = fixture(); mutate(value);
  await assert.rejects(parse(value));
});

test('rejects duplicate keys, prototype keys, excessive size and overflowing JSON numbers', async () => {
  await assert.rejects(parseRecording('{"version":"one","version":"two"}'));
  await assert.rejects(parseRecording('{"__proto__":{}}'));
  await assert.rejects(parseRecording(' '.repeat(8 * 1024 * 1024 + 1)));
  const value = fixture();
  await assert.rejects(parseRecording(JSON.stringify(value).replace('"duration_ticks":100', '"duration_ticks":1e999')));
});

test('captured telemetry fits mobile, intermediate and desktop canvas widths', async () => {
  for (const maximumRates of [false, true]) {
    const value = fixture();
    if (maximumRates) for (const segment of value.segments) for (const bin of segment.bins) {
      for (const group of Object.keys(value.groups)) bin.group_spikes[group] = value.groups[group] * bin.duration_ticks;
    }
    const recording = await parse(value), sample = sampleAtTick(recording, 0);
    for (const width of [320, 390, 649, 650, 720, 800, 900]) {
      const calls = [];
      const context = {
        font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
        measureText(text) { return { width: text.length * Number(this.font.match(/(\d+)px/)[1]) * 0.55 }; },
        fillText(text, x, y) { calls.push({ text, x, y, width: this.measureText(text).width }); },
      };
      drawOverlay(context, width, 600, width, recording, sample);
      assert.ok(calls.some((call) => call.text.includes('MBON11')));
      assert.ok(calls.some((call) => call.text.includes('Hz/cell')));
      for (const call of calls) assert.ok(call.x >= 0 && call.x + call.width <= width, `${width}px clips: ${call.text}`);
    }
  }
});

test('terminal export overlay labels the hold without changing sampled values', async () => {
  const recording = await parse(fixture());
  const sample = sampleAtTick(recording, recording.duration_ticks);
  const before = JSON.stringify(sample);
  const lines = [];
  const context = {
    font: '', save() {}, restore() {}, scale() {}, fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
    measureText(text) { return { width: text.length * 7 }; },
    fillText(text) { lines.push(text); },
  };
  drawOverlay(context, 900, 900, 900, recording, sample, true);
  assert.ok(lines.some((line) => line.includes('presentation hold')));
  assert.ok(lines.some((line) => line.includes('no simulation time advances')));
  assert.equal(JSON.stringify(sample), before);
});
