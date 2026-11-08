import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { cellFixture } from './cell-activity.test.mjs';
const module = await import('../src/science-panel.ts').catch(() => ({}));
function api() { assert.equal(typeof module.buildActivityTraces, 'function', 'Shared science panel is missing'); return module; }
const groups = ['kc', 'pam11', 'ppl101', 'mbon07', 'mbon11', 'motor_left', 'motor_right'];
function recording() {
  return { groups: Object.fromEntries(groups.map(name => [name, 2])), duration_ticks: 8000,
    segments: [{ playback_start_tick: 7000, source_start_tick: 1000, bins: [
      { end_tick: 1100, duration_ticks: 100, group_spikes: Object.fromEntries(groups.map(name => [name, name === 'kc' ? 2 : 0])) },
      { end_tick: 1133, duration_ticks: 33, group_spikes: Object.fromEntries(groups.map(name => [name, 0])) },
    ] }] };
}

test('all seven cached traces use real bin durations and playback placement with fixed row scales', () => {
  const { buildActivityTraces, traceHistory } = api();
  const cache = buildActivityTraces(recording());
  assert.equal(cache.length, 7);
  assert.equal(cache[0].maximum, 100); assert.equal(cache[1].maximum, 1);
  assert.deepEqual(cache[0].bins, [{ start: 7000, end: 7100, rate: 100 }, { start: 7100, end: 7133, rate: 0 }]);
  assert.deepEqual(traceHistory(cache[0], 7050), [{ start: 7000, end: 7050, rate: 100 }]);
  assert.deepEqual(traceHistory(cache[0], 6900), []);
  assert.ok(cache.slice(1).every(row => row.bins.every(bin => bin.rate === 0)));
});

test('shared panel shows absence of anatomy and seven actual values without changing terminal data', () => {
  const { buildActivityTraces, drawSciencePanel } = api();
  const value = recording(), cache = buildActivityTraces(value), lines = [], widths = [900, 390];
  const sample = { tick: 7050, sourceTick: 7050, bin: { duration_ticks: 100 }, segment: { stimulation: null, learning: false, event_sequence: 3, stimulus: 'A' }, rates: Object.fromEntries(groups.map(name => [name, name === 'kc' ? 100 : 0])) };
  const before = JSON.stringify({ value, sample, cache });
  for (const width of widths) {
    lines.length = 0;
    const context = { font: '', fillStyle: '', save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, rect() {}, clip() {}, fillRect() {},
      fillText(text, x, y) { lines.push({ text, x, y, font: this.font }); }, measureText(text) { return { width: text.length * 6 }; } };
    drawSciencePanel(context, width, width === 900 ? 900 : 790, value, sample, cache, null);
    assert.ok(lines.some(line => /Anatomy not loaded/.test(line.text)));
    assert.ok(lines.some(line => /individual row scales/.test(line.text)));
    assert.ok(lines.some(line => /100\.00/.test(line.text)));
    for (const label of ['KC', 'PAM11', 'PPL101', 'MBON07', 'MBON11', 'DNa02 L', 'DNa02 R']) assert.ok(lines.some(line => line.text === label), label);
    assert.ok(lines.every(line => Number(line.font.match(/(\d+)px/)[1]) >= 12));
  }
  assert.equal(JSON.stringify({ value, sample, cache }), before);
});

test('static cloud uniformly fits the projected rectangle without stretching either axis', () => {
  const { drawSciencePanel, buildActivityTraces } = api(), rects = [];
  const context = { font: '', save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, fillText() {},
    measureText(text) { return { width: text.length * 6 }; },
    fillRect(x, y, width, height) { rects.push({ x, y, width, height }); } };
  const value = recording(), sample = { tick: 7050, sourceTick: 7050, bin: { duration_ticks: 100 }, segment: { stimulation: null, learning: false, event_sequence: 3, stimulus: 'A' }, rates: Object.fromEntries(groups.map(name => [name, 0])) };
  const anatomy = { coverage: { displayed_cells: 2, positioned_cells: 2, missing_positions: 166698 } };
  drawSciencePanel(context, 900, 900, value, sample, buildActivityTraces(value), anatomy, [[-.5, -.05], [.5, .05]]);
  const dots = rects.filter(rect => rect.width === 1.2);
  const horizontal = dots[1].x - dots[0].x, vertical = dots[0].y - dots[1].y;
  assert.ok(horizontal > 220 && horizontal < 250, 'Cloud should use available width when height permits');
  assert.ok(Math.abs(horizontal / vertical - 10) < 1e-8, 'One common scale must preserve projected aspect');
});

test('active canvas panel retains exact input, media/source clocks and complete-bin integrity labels', () => {
  const { drawSciencePanel, buildActivityTraces } = api(), lines = [];
  const context = { font: '', save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, fillRect() {},
    fillText(text) { lines.push(text); }, measureText(text) { return { width: text.length * 6 }; } };
  const value = { ...recording(), version: 'measured-video-replay/v2' };
  const sample = { tick: 7050, sourceTick: 3050, input: { clip_id: 'clip-0', frame_index: 4, source_pts: 77, source_time_base: [1, 30] },
    bin: { duration_ticks: 100 }, policy: null, clipPolicy: null, segment: { stimulation: null, learning: false, event_sequence: 3 }, rates: Object.fromEntries(groups.map(name => [name, 0])) };
  drawSciencePanel(context, 900, 900, value, sample, buildActivityTraces(value), null);
  assert.ok(lines.some(line => line.includes('Reel 5×')));
  assert.ok(lines.some(line => line.includes('Source 0.3050 s') && line.includes('media PTS 77')));
  assert.ok(lines.some(line => /Complete 10 ms bin/.test(line) && line.includes('integrity-only')));
});

test('active shared cell panel labels complete windows, neutral zero and static connections at readable sizes', () => {
  const { prepareCellPanel, drawSciencePanel, buildActivityTraces } = api();
  assert.equal(typeof prepareCellPanel, 'function');
  const { detail, context: fixture } = cellFixture(), value = fixture.recording;
  const cache = prepareCellPanel(detail, null), before = JSON.stringify(detail);
  for (const [width, height] of [[900, 900], [390, 1500]]) {
    const lines = [], fills = [];
    const context = { font: '', fillStyle: '', globalAlpha: 1, save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
      fillRect(x, y, w, h) { fills.push({ x, y, w, h, color: this.fillStyle }); },
      fillText(text, x, y) { lines.push({ text, x, y, font: this.font }); }, measureText(text) { return { width: text.length * 6 }; } };
    const sample = { tick: 2000, sourceTick: 2000, bin: { duration_ticks: 100 }, segment: { stimulation: null, learning: false, event_sequence: 4, stimulus: 'A' }, rates: Object.fromEntries(groups.map(name => [name, 0])) };
    drawSciencePanel(context, width, height, value, sample, buildActivityTraces(value), null, [], cache);
    const text = lines.map(line => line.text).join(' ');
    assert.match(text, /Recorded cell counts/); assert.match(text, /Completed 100 ms window 0\.100–0\.200 s/);
    assert.match(text, /Schematic count grid/); assert.match(text, /without positions/);
    assert.match(text, /Static model connections/); assert.match(text, /not measured transmission/);
    assert.ok(fills.some(fill => fill.color === '#405361'), 'All-zero bins must use the neutral count color');
    assert.ok(lines.every(line => Number(line.font.match(/(\d+)px/)[1]) >= 12 && line.y <= height), 'Essential labels must remain legible and inside the canvas');
    lines.length = 0; sample.tick = sample.sourceTick = 999;
    drawSciencePanel(context, width, height, value, sample, buildActivityTraces(value), null, [], cache);
    assert.match(lines.map(line => line.text).join(' '), /Awaiting first complete 100 ms window/);
  }
  assert.equal(JSON.stringify(detail), before);
});

test('full256-cell coverage and feed captions stay inside a341px canvas without entering trace rows', () => {
  const { prepareCellPanel, drawSciencePanel, buildActivityTraces } = api(), { detail, context: fixture } = cellFixture();
  for (let i = 8; i < 256; i++) detail.cells.push({ model_index: i, source_id: 10000 + i, groups: ['kc'], soma: null });
  detail.selection.group_population_counts.kc = 15000; detail.selection.group_selected_counts.kc = 250;
  for (const bin of detail.bins) while (bin.counts.length < 256) bin.counts.push(0);
  const lines = [], width = 341, height = 1600;
  const context = { font: '', save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, fillRect() {},
    fillText(text, x, y) { lines.push({ text, x, y }); }, measureText(text) { return { width: text.length * 6 }; } };
  const sample = { tick: 2000, sourceTick: 2000, input: { clip_id: 'clip-0', frame_index: 100, source_pts: 1500, source_time_base: [1, 15360] },
    bin: { duration_ticks: 100 }, policy: null, clipPolicy: null, segment: { stimulation: null, learning: false, event_sequence: 240 }, rates: Object.fromEntries(groups.map(name => [name, 0])) };
  drawSciencePanel(context, width, height, fixture.recording, sample, buildActivityTraces(fixture.recording), null, [], prepareCellPanel(detail, null));
  assert.ok(lines.every(line => line.y <= height && line.x + line.text.length * 6 <= width), 'Labels must fit at actual narrow-canvas width');
  const traceY = lines.find(line => line.text === 'Hz/cell · individual row scales').y;
  const connectionLines = lines.filter(line => line.x === 184);
  assert.ok(connectionLines.every(line => line.y < traceY - 20), 'Coverage beside the grid must finish before population traces');
});

test('cell columns switch together before traces run out of width at650..815px', () => {
  const { scienceLayout, prepareCellPanel, drawSciencePanel, buildActivityTraces } = api(), { detail, context: fixture } = cellFixture();
  for (const width of [650, 700, 800, 815, 859, 860, 900]) {
    const baselines = [], context = { font: '', strokeStyle: '', save() {}, restore() {}, beginPath() {}, stroke() {}, fillRect() {}, fillText() {},
      measureText(text) { return { width: text.length * 6 }; },
      moveTo(x, y) { this.start = [x, y]; }, lineTo(x, y) { if (this.strokeStyle === '#344f63') baselines.push([this.start[0], x]); } };
    const sample = { tick: 2000, sourceTick: 2000, bin: { duration_ticks: 100 }, segment: { stimulation: null, learning: false, event_sequence: 4, stimulus: 'A' }, rates: Object.fromEntries(groups.map(name => [name, 0])) };
    drawSciencePanel(context, width, 1600, fixture.recording, sample, buildActivityTraces(fixture.recording), null, [], prepareCellPanel(detail, null));
    assert.equal(baselines.length, 7);
    assert.ok(baselines.every(([start, end]) => end > start && end <= width - 16), `${width}px traces must advance into positive visible width`);
    assert.equal(scienceLayout(width, 1600, true).narrow, width < 860);
  }
  const css = readFileSync(new URL('../src/style.css', import.meta.url), 'utf8');
  assert.match(css, /@container \(max-width:859px\)\s*\{\s*\.stage>canvas\.has-cell-activity\s*\{\s*min-height:1600px/);
});
