import arrayLocks from '../../src/fly_connectome_sim/neural/arrays.lock.json' with { type: 'json' };
import sourceLocks from '../../src/fly_connectome_sim/neural/sources.lock.json' with { type: 'json' };
import { GROUPS, type Counts, type Group } from './replay.ts';
import { check, keys, object, int, digest, equal, strictJson } from './event-replay.ts';
import type { AnyRecording } from './recording.ts';
import type { Anatomy } from './anatomy.ts';

export type Cell = { model_index: number; source_id: number; groups: Group[]; soma: [number, number, number] | null };
export type CellBin = { observation_index: number; bin_index: number; start_tick: number; end_tick: number; counts: number[] };
export type CellWindow = { start_tick: number; end_tick: number; counts: number[] };
export type CellActivity = {
  version: 'replay-cell-counts/v1'; tick_ms: .1;
  binding: { recording_sha256: string; raw_detail_sha256: string; engine_identity_sha256: string; graph_ids_sha256: string; graph_ptr_sha256: string; graph_post_sha256: string; annotations_sha256: string };
  selection: { method: 'mandatory-groups-kc-stride/v1'; limit: 256; group_population_counts: Counts; group_selected_counts: Counts };
  cells: Cell[];
  topology: { method: 'induced-directed-edge-stride/v1'; limit: 512; eligible_edges: number; edges: Array<[number, number, number]> };
  bins: CellBin[];
  display: { window_ticks: 1000; mode: 'last-completed-whole-bin-window/v1' };
};
type Context = { recording: AnyRecording; recordingSha256: string };
export const MAX_CELL_ACTIVITY_BYTES = 16 * 1024 * 1024;

export function parseCellActivity(text: string, context: Context): CellActivity {
  check(new TextEncoder().encode(text).length <= MAX_CELL_ACTIVITY_BYTES, 'Cell activity exceeds 16 MiB.');
  const value = keys(strictJson(text), ['version', 'tick_ms', 'binding', 'selection', 'cells', 'topology', 'bins', 'display'], 'Cell activity');
  equal(value.version, 'replay-cell-counts/v1', 'Cell version'); equal(value.tick_ms, .1, 'Cell tick size');
  const recording = context.recording;
  check(recording.version === 'feed-event-replay/v1', 'Cell counts require a continuous feed/event recording.');
  int(recording.duration_ticks, 1000, 100000, 'Cell duration');
  check(recording.duration_ticks % 1000 === 0, 'Duration must contain complete 100 ms windows.');
  const identity = object(recording.source.metadata.engine_identity, 'Cell engine identity');
  equal(identity.version, 'fly-engine/v1', 'Cell engine version'); digest(identity.sha256, 'Cell engine hash');
  const provenance = object(identity.model_provenance, 'Cell model provenance');
  const binding = keys(value.binding, ['recording_sha256', 'raw_detail_sha256', 'engine_identity_sha256', 'graph_ids_sha256', 'graph_ptr_sha256', 'graph_post_sha256', 'annotations_sha256'], 'Cell binding');
  for (const [name, hash] of Object.entries(binding)) digest(hash, `Cell ${name}`);
  digest(context.recordingSha256, 'Recording hash'); equal(binding.recording_sha256, context.recordingSha256, 'Exact recording bytes');
  equal(binding.engine_identity_sha256, identity.sha256, 'Cell engine binding');
  for (const name of ['ids', 'ptr', 'post'] as const) {
    const field = `graph_${name}_sha256`;
    equal(binding[field], arrayLocks[name], `Locked ${name}`); equal(binding[field], provenance[field], `Engine ${name}`);
  }
  equal(binding.annotations_sha256, sourceLocks['annotations.feather'].sha256, 'Locked actual soma source');
  const selection = keys(value.selection, ['method', 'limit', 'group_population_counts', 'group_selected_counts'], 'Cell selection');
  equal(selection.method, 'mandatory-groups-kc-stride/v1', 'Cell selection method'); equal(selection.limit, 256, 'Cell limit');
  const populations = keys(selection.group_population_counts, GROUPS, 'Cell populations');
  const selected = keys(selection.group_selected_counts, GROUPS, 'Selected populations');
  const maps = keys(identity.neural_groups, GROUPS, 'Cell neural maps'), sets = {} as Record<Group, Set<number>>;
  const mandatory = new Set<number>(), union = new Set<number>();
  for (const name of GROUPS) {
    int(populations[name], 1, 166700, `Cell population ${name}`); equal(populations[name], recording.groups[name], `Recording population ${name}`);
    const map = maps[name]; check(Array.isArray(map) && map.length === populations[name], `Cell map ${name} differs.`);
    for (const index of map) { int(index, 0, 166699, 'Cell map index'); union.add(index); if (name !== 'kc') mandatory.add(index); }
    check(new Set(map).size === map.length, 'Duplicate neural map indices.'); sets[name] = new Set(map);
    int(selected[name], 0, 256, `Selected ${name}`);
  }
  check(mandatory.size <= 256, 'Mandatory cohort exceeds limit.');
  check(Array.isArray(value.cells) && value.cells.length === Math.min(256, union.size), 'Missing or oversized fixed cohort.');
  const indices = new Set<number>(); let previousId = 0;
  for (const raw of value.cells) {
    const cell = keys(raw, ['model_index', 'source_id', 'groups', 'soma'], 'Cell');
    int(cell.model_index, 0, 166699, 'Model index'); int(cell.source_id, 1, Number.MAX_SAFE_INTEGER, 'Source ID');
    check(!indices.has(cell.model_index) && cell.source_id > previousId && union.has(cell.model_index), 'Duplicate/unordered/outside-cohort cell.');
    indices.add(cell.model_index); previousId = cell.source_id;
    check(Array.isArray(cell.groups) && cell.groups.every(name => GROUPS.includes(name)) && new Set(cell.groups).size === cell.groups.length, 'Invalid cell memberships.');
    equal([...cell.groups].sort(), GROUPS.filter(name => sets[name].has(cell.model_index as number)).sort(), 'Complete cell memberships');
    check(cell.soma === null || Array.isArray(cell.soma) && cell.soma.length === 3 && cell.soma.every(v => typeof v === 'number' && Number.isSafeInteger(v)), 'Invalid actual soma coordinates.');
  }
  check([...mandatory].every(index => indices.has(index)), 'Mandatory cells were omitted.');
  const cells = value.cells as Cell[];
  for (const name of GROUPS) equal(selected[name], cells.filter(cell => cell.groups.includes(name)).length, `Selected coverage ${name}`);
  const topology = keys(value.topology, ['method', 'limit', 'eligible_edges', 'edges'], 'Cell topology');
  equal(topology.method, 'induced-directed-edge-stride/v1', 'Topology method'); equal(topology.limit, 512, 'Topology limit');
  int(topology.eligible_edges, 0, Number.MAX_SAFE_INTEGER, 'Eligible edges');
  check(Array.isArray(topology.edges) && topology.edges.length === Math.min(512, topology.eligible_edges), 'Invalid displayed edge count.');
  const edgeIndices = new Set<number>(); let previous: number[] | null = null;
  for (const edge of topology.edges) {
    check(Array.isArray(edge) && edge.length === 3, 'Invalid directed edge.');
    int(edge[0], 0, Number.MAX_SAFE_INTEGER, 'Graph edge index'); int(edge[1], 0, cells.length - 1, 'Source slot'); int(edge[2], 0, cells.length - 1, 'Target slot');
    const ordered = [edge[1], edge[2], edge[0]];
    check(!edgeIndices.has(edge[0]) && (!previous || ordered[0] > previous[0] || ordered[0] === previous[0] && (ordered[1] > previous[1] || ordered[1] === previous[1] && ordered[2] > previous[2])), 'Duplicate or unordered directed edges.');
    previous = ordered; edgeIndices.add(edge[0]);
  }
  equal(keys(value.display, ['window_ticks', 'mode'], 'Cell display'), { window_ticks: 1000, mode: 'last-completed-whole-bin-window/v1' }, 'Completed-window mode');
  check(Array.isArray(value.bins) && value.bins.length > 0 && value.bins.length <= 1160, 'Invalid original-bin count.');
  check(recording.segments.length <= 244, 'Too many cell observations.');
  let cursor = 0, offset = 0;
  for (const [observation, segment] of recording.segments.entries()) {
    check(segment.source_start_tick === cursor && segment.playback_start_tick === cursor && segment.source_end_tick === segment.playback_end_tick && segment.source_end_tick - cursor <= 5000, 'Cell source/playback clocks must be continuous.');
    for (const [ordinal, original] of segment.bins.entries()) {
      check(ordinal < 50, 'Too many native bins per observation.');
      const bin = keys(value.bins[offset++], ['observation_index', 'bin_index', 'start_tick', 'end_tick', 'counts'], 'Cell bin');
      equal(bin.observation_index, observation, 'Cell observation order'); equal(bin.bin_index, ordinal, 'Cell bin order');
      equal(bin.start_tick, cursor, 'Cell bin start'); equal(bin.end_tick, original.end_tick, 'Cell bin end');
      int(original.duration_ticks, 1, 100, 'Native bin duration');
      check(original.end_tick - cursor === original.duration_ticks && Math.floor(cursor / 1000) === Math.floor((original.end_tick - 1) / 1000), 'Native bin crosses a gap or 100 ms boundary.');
      check(Array.isArray(bin.counts) && bin.counts.length === cells.length, 'Wrong cell count vector.');
      for (const count of bin.counts) int(count, 0, original.duration_ticks, 'Cell spike count');
      for (const name of GROUPS) {
        const sum = cells.reduce((total, cell, slot) => total + (cell.groups.includes(name) ? (bin.counts as number[])[slot] : 0), 0);
        check(sum <= original.group_spikes[name] && (selected[name] !== populations[name] || sum === original.group_spikes[name]), `Cell counts disagree with ${name} population.`);
      }
      cursor = original.end_tick;
    }
    equal(cursor, segment.source_end_tick, 'Original observation coverage');
  }
  check(offset === value.bins.length && cursor === recording.duration_ticks, 'Incomplete cell bin coverage.');
  return value as CellActivity;
}

export function buildCellWindows(detail: CellActivity): CellWindow[] {
  const windows: CellWindow[] = [];
  let counts = detail.cells.map(() => 0);
  for (const bin of detail.bins) {
    counts = counts.map((value, slot) => value + bin.counts[slot]);
    if (bin.end_tick % 1000 === 0) { windows.push({ start_tick: bin.end_tick - 1000, end_tick: bin.end_tick, counts }); counts = detail.cells.map(() => 0); }
  }
  return windows;
}
export function cellWindowAtTick(windows: CellWindow[], tick: number): CellWindow | null {
  check(Number.isFinite(tick) && tick >= 0, 'Invalid cell playback tick.');
  return windows[Math.min(windows.length, Math.floor(tick / 1000)) - 1] ?? null;
}
export function countCategory(count: number): '0' | '1' | '2–4' | '5+' {
  return count === 0 ? '0' : count === 1 ? '1' : count < 5 ? '2–4' : '5+';
}
export function assertCellAnatomy(detail: CellActivity | null, anatomy: Anatomy | null) {
  if (!detail || !anatomy) return;
  equal(anatomy.binding.recording_sha256, detail.binding.recording_sha256, 'Cell/background recording');
  equal(anatomy.binding.graph_ids_sha256, detail.binding.graph_ids_sha256, 'Cell/background graph');
  equal(anatomy.source.annotations_sha256, detail.binding.annotations_sha256, 'Cell/background soma source');
}
export function projectCellScene(detail: CellActivity, anatomy: Anatomy | null) {
  assertCellAnatomy(detail, anatomy);
  const rawBackground = anatomy?.points.map(point => [point[2] - point[4] * .35, point[3] + point[4] * .2]) ?? [];
  const rawCohort = detail.cells.map(cell => cell.soma ? [cell.soma[0] - cell.soma[2] * .35, cell.soma[1] + cell.soma[2] * .2] : null);
  const all = [...rawBackground, ...rawCohort.filter(point => point !== null)];
  const bounds = all.reduce((value, point) => [Math.min(value[0], point[0]), Math.min(value[1], point[1]), Math.max(value[2], point[0]), Math.max(value[3], point[1])], [Infinity, Infinity, -Infinity, -Infinity]);
  const extent = Math.max(1, bounds[2] - bounds[0], bounds[3] - bounds[1]);
  const project = (point: number[]): [number, number] => [(point[0] - (bounds[0] + bounds[2]) / 2) / extent, (point[1] - (bounds[1] + bounds[3]) / 2) / extent];
  return { background: rawBackground.map(project), cohort: rawCohort.map(point => point ? project(point) : null) };
}
export function createCellActivityAttachment() {
  let generation = 0, request = 0, context: Context | null = null, value: CellActivity | null = null, exporting = false;
  return {
    get value() { return value; },
    setRecording(next: Context) { if (exporting) return false; generation++; request++; context = next; value = null; return true; },
    cancelPending() { request++; },
    setExporting(next: boolean) { exporting = next; if (next) request++; },
    async load(text: Promise<string>) {
      if (exporting) return false;
      check(context, 'Open a recording before cell activity.');
      const expectedGeneration = generation, expectedRequest = ++request, expectedContext = context;
      const raw = await text;
      if (exporting || generation !== expectedGeneration || request !== expectedRequest) return false;
      value = parseCellActivity(raw, expectedContext); return true;
    },
  };
}
