import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

const module = await import('../src/cell-activity.ts').catch(() => ({}));
const locks = JSON.parse(readFileSync(new URL('../../src/fly_connectome_sim/neural/arrays.lock.json', import.meta.url)));
const annotations = JSON.parse(readFileSync(new URL('../../src/fly_connectome_sim/neural/sources.lock.json', import.meta.url)))['annotations.feather'].sha256;
const names = ['pam11', 'ppl101', 'kc', 'mbon07', 'mbon11', 'motor_left', 'motor_right'];
function api() { assert.equal(typeof module.parseCellActivity, 'function', 'Recorded cell-count reader is missing'); return module; }

// Declared relationships only: these fixtures do not claim a source/native audit.
export function cellFixture() {
  const maps = { pam11: [2], ppl101: [3], kc: [0, 1], mbon07: [4], mbon11: [5], motor_left: [6], motor_right: [7] };
  const population = Object.fromEntries(names.map(name => [name, maps[name].length]));
  const cells = Array.from({ length: 8 }, (_, i) => ({ model_index: i, source_id: (i + 1) * 101, groups: names.filter(name => maps[name].includes(i)), soma: i ? [i * 100, i * 200, i * 300] : null }));
  const bins = [], segments = [];
  let cursor = 0;
  for (const [observation, duration] of [333, 334, 333, 5000].entries()) {
    const start = cursor, original = [];
    let ordinal = 0;
    while (cursor < start + duration) {
      const end = Math.min(start + duration, cursor + 100), counts = Array(8).fill(0);
      if (cursor === 0) { counts[0] = 1; counts[2] = 2; counts[6] = 5; }
      if (end === 6000) counts[7] = 3;
      bins.push({ observation_index: observation, bin_index: ordinal++, start_tick: cursor, end_tick: end, counts });
      original.push({ end_tick: end, duration_ticks: end - cursor, group_spikes: Object.fromEntries(names.map(name => [name, maps[name].reduce((sum, i) => sum + counts[i], 0)])) });
      cursor = end;
    }
    segments.push({ source_start_tick: start, source_end_tick: cursor, playback_start_tick: start, playback_end_tick: cursor, bins: original });
  }
  const identity = { version: 'fly-engine/v1', sha256: 'b'.repeat(64), neural_groups: maps, model_provenance: { graph_ids_sha256: locks.ids, graph_ptr_sha256: locks.ptr, graph_post_sha256: locks.post } };
  const recording = { version: 'feed-event-replay/v1', tick_ms: .1, duration_ticks: 6000, groups: population, source: { metadata: { engine_identity: identity } }, segments };
  const detail = { version: 'replay-cell-counts/v1', tick_ms: .1,
    binding: { recording_sha256: 'a'.repeat(64), raw_detail_sha256: 'c'.repeat(64), engine_identity_sha256: identity.sha256, graph_ids_sha256: locks.ids, graph_ptr_sha256: locks.ptr, graph_post_sha256: locks.post, annotations_sha256: annotations },
    selection: { method: 'mandatory-groups-kc-stride/v1', limit: 256, group_population_counts: population, group_selected_counts: { ...population } },
    cells, topology: { method: 'induced-directed-edge-stride/v1', limit: 512, eligible_edges: 2, edges: [[0, 0, 4], [1, 0, 5]] }, bins,
    display: { window_ticks: 1000, mode: 'last-completed-whole-bin-window/v1' } };
  return { detail, context: { recording, recordingSha256: 'a'.repeat(64) } };
}

test('bound cell counts preserve original short bins, nullable positions, all groups and directed edges', () => {
  const { parseCellActivity } = api(), { detail, context } = cellFixture();
  assert.deepEqual(parseCellActivity(JSON.stringify(detail), context), detail);
  assert.equal(detail.bins[3].end_tick, 333); assert.equal(detail.bins[7].end_tick, 667);
  const empty = structuredClone(detail); empty.topology = { ...empty.topology, eligible_edges: 0, edges: [] };
  assert.deepEqual(parseCellActivity(JSON.stringify(empty), context).topology.edges, []);
});

test('closed parser rejects malformed source, cohorts, topology, count sums and bin coverage', () => {
  const { parseCellActivity } = api();
  const changes = [v => v.extra = 1, v => v.binding.extra = 1, v => v.binding.recording_sha256 = 'd'.repeat(64),
    v => v.binding.engine_identity_sha256 = 'd'.repeat(64), v => v.binding.graph_ptr_sha256 = 'd'.repeat(64), v => v.binding.graph_post_sha256 = 'd'.repeat(64),
    v => v.binding.graph_ids_sha256 = 'd'.repeat(64), v => v.binding.annotations_sha256 = 'd'.repeat(64), v => v.binding.raw_detail_sha256 = true,
    v => v.cells[0].source_id = true, v => v.cells[0].source_id = 0, v => v.cells[1].source_id = 101, v => v.cells.reverse(),
    v => v.cells[0].model_index = 166700, v => v.cells[1].model_index = 0, v => v.cells[0].groups = [], v => v.cells[2].groups.push('kc'),
    v => v.cells[0].soma = [1, 2, .5], v => v.cells.pop(), v => v.selection.group_selected_counts.kc++, v => v.selection.group_population_counts.kc++,
    v => v.topology.edges[0][1] = 8, v => v.topology.edges[0][0] = -1, v => v.topology.edges[1][0] = 0, v => v.topology.eligible_edges++,
    v => v.topology.edges.reverse(), v => v.bins[0].counts[0] = true, v => v.bins[0].counts[0] = 101, v => v.bins[0].counts[0]++,
    v => v.bins[0].counts.pop(), v => v.bins[0].start_tick++, v => v.bins[1].bin_index++, v => v.bins[0].observation_index++,
    v => v.bins.pop(), v => v.bins.splice(2, 0, v.bins[1]), v => v.bins[0].unknown = 1, v => v.display.window_ticks = 500,
  ];
  for (const change of changes) { const { detail, context } = cellFixture(); change(detail); assert.throws(() => parseCellActivity(JSON.stringify(detail), context), undefined, String(change)); }
  const { detail, context } = cellFixture(), text = JSON.stringify(detail);
  assert.throws(() => parseCellActivity(text.replace('"tick_ms":', '"tick_ms":0.1,"tick_ms":'), context));
  assert.throws(() => parseCellActivity(' '.repeat(16 * 1024 * 1024 + 1), context));
  const crossed = structuredClone(detail); crossed.bins[11].end_tick = 1001;
  assert.throws(() => parseCellActivity(JSON.stringify(crossed), context));
});

test('only completed whole-bin100ms windows appear; reverse seeking and terminal hold are exact', () => {
  const { parseCellActivity, buildCellWindows, cellWindowAtTick, countCategory } = api(), { detail, context } = cellFixture();
  const windows = buildCellWindows(parseCellActivity(JSON.stringify(detail), context));
  assert.equal(windows.length, 6);
  assert.equal(cellWindowAtTick(windows, 0), null); assert.equal(cellWindowAtTick(windows, 999), null);
  assert.deepEqual(cellWindowAtTick(windows, 1000), { start_tick: 0, end_tick: 1000, counts: [1, 0, 2, 0, 0, 0, 5, 0] });
  assert.equal(cellWindowAtTick(windows, 1999), windows[0]); assert.equal(cellWindowAtTick(windows, 2000), windows[1]);
  assert.deepEqual(cellWindowAtTick(windows, 6000).counts, [0, 0, 0, 0, 0, 0, 0, 3]);
  assert.equal(cellWindowAtTick(windows, 36000), windows[5]); assert.equal(cellWindowAtTick(windows, 1000), windows[0]);
  assert.deepEqual([0, 1, 2, 4, 5, 1000].map(countCategory), ['0', '1', '2–4', '2–4', '5+', '5+']);
  assert.ok(windows[1].counts.every(count => count === 0));
});

test('attachment retains valid data on error, rejects stale loads, freezes export, clears on new recording', async () => {
  const { createCellActivityAttachment } = api(), { detail, context } = cellFixture();
  const attachment = createCellActivityAttachment(); attachment.setRecording(context);
  assert.equal(await attachment.load(Promise.resolve(JSON.stringify(detail))), true);
  const valid = attachment.value;
  await assert.rejects(attachment.load(Promise.resolve('{}'))); assert.equal(attachment.value, valid);
  let finish;
  const pending = attachment.load(new Promise(resolve => { finish = resolve; }));
  attachment.setExporting(true); finish(JSON.stringify(detail)); assert.equal(await pending, false);
  assert.equal(await attachment.load(Promise.resolve(JSON.stringify(detail))), false); assert.equal(attachment.value, valid);
  assert.equal(attachment.setRecording(context), false); attachment.setExporting(false);
  const stale = attachment.load(new Promise(resolve => { finish = resolve; }));
  attachment.setRecording(context); finish(JSON.stringify(detail)); assert.equal(await stale, false); assert.equal(attachment.value, null);
});

test('cohort and optional soma background share one source-coordinate projection and bindings', () => {
  const { projectCellScene, assertCellAnatomy } = api(), { detail } = cellFixture();
  const anatomy = { binding: { recording_sha256: detail.binding.recording_sha256, graph_ids_sha256: locks.ids }, source: { annotations_sha256: annotations }, points: [[1, '202', 100, 200, 300], [100, '999', 10000, 300, 900]] };
  assertCellAnatomy(detail, anatomy);
  const projection = projectCellScene(detail, anatomy);
  assert.equal(projection.cohort[0], null);
  assert.deepEqual(projection.cohort[1], projection.background[0]);
  assert.ok(projection.background[1][0] > projection.cohort[1][0]);
  const wrong = structuredClone(anatomy); wrong.binding.recording_sha256 = 'f'.repeat(64);
  assert.throws(() => assertCellAnatomy(detail, wrong));
});
