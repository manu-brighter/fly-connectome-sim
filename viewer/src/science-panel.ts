import { GROUPS, type Group } from './replay.ts';
import type { AnyRecording, sampleAnyAtTick } from './recording.ts';
import type { Anatomy } from './anatomy.ts';
import { videoInputLabel, videoPolicyLabel, videoSpeedLabel } from './video-replay.ts';
import { buildCellWindows, cellWindowAtTick, countCategory, projectCellScene, type CellActivity } from './cell-activity.ts';

const LABELS = ['KC', 'PAM11', 'PPL101', 'MBON07', 'MBON11', 'DNa02 L', 'DNa02 R'];
const COLORS = ['#9bb8ce', '#cfa6e8', '#e5b590', '#8ed1c0', '#7ca7ff', '#b9d889', '#eab19e'];
type TraceBin = { start: number; end: number; rate: number };
export type ActivityTrace = { name: Group; label: string; color: string; maximum: number; bins: TraceBin[] };
export const CELL_PANEL_MIN_WIDTH = 860;

export function buildActivityTraces(recording: AnyRecording): ActivityTrace[] {
  return GROUPS.map((name, index) => {
    const bins = recording.segments.flatMap(segment => segment.bins.map(bin => {
      const end = segment.playback_start_tick + bin.end_tick - segment.source_start_tick;
      return { start: end - bin.duration_ticks, end, rate: bin.group_spikes[name] * 10000 / (recording.groups[name] * bin.duration_ticks) };
    }));
    return { name, label: LABELS[index], color: COLORS[index], maximum: Math.max(1, ...bins.map(bin => bin.rate)), bins };
  });
}
export function traceHistory(row: ActivityTrace, tick: number) {
  return row.bins.filter(bin => bin.start < tick).map(bin => ({ ...bin, end: Math.min(bin.end, tick) }));
}
export function scienceLayout(width: number, height: number, cellsLoaded = false) {
  const narrow = width < (cellsLoaded ? CELL_PANEL_MIN_WIDTH : 650);
  const panelHeight = cellsLoaded ? (narrow ? 960 : 420) : (narrow ? 520 : 300);
  return { top: height - panelHeight, panelHeight, sceneHeight: Math.max(1, height - panelHeight), narrow };
}

export function prepareCellPanel(detail: CellActivity, anatomy: Anatomy | null) {
  return { detail, windows: buildCellWindows(detail), projection: projectCellScene(detail, anatomy) };
}
type CellPanel = ReturnType<typeof prepareCellPanel>;
function wrappedText(context: CanvasRenderingContext2D, text: string, x: number, y: number, width: number) {
  let line = '';
  for (const word of text.split(' ')) {
    if (line && context.measureText(`${line} ${word}`).width > width) { context.fillText(line, x, y); y += 16; line = word; }
    else line = line ? `${line} ${word}` : word;
  }
  context.fillText(line, x, y); return y + 16;
}
function drawCells(context: CanvasRenderingContext2D, width: number, headerEnd: number, panel: CellPanel, tick: number) {
  const { detail, projection, windows } = panel, narrow = width < CELL_PANEL_MIN_WIDTH, heading = headerEnd + 24;
  const window = cellWindowAtTick(windows, tick), positioned = projection.cohort.filter(point => point !== null).length;
  context.fillStyle = '#edf5fb'; context.fillText('Recorded cell counts', 16, heading);
  context.fillStyle = '#b8cddd';
  wrappedText(context, window ? `Completed 100 ms window ${(window.start_tick / 10000).toFixed(3)}–${(window.end_tick / 10000).toFixed(3)} s` : 'Awaiting first complete 100 ms window', 16, heading + 16, width - 32);
  const cloudWidth = narrow ? width - 32 : 340, cloudHeight = 170, cloudTop = heading + 36;
  let halfWidth = 0, halfHeight = 0;
  for (const position of [...projection.background, ...projection.cohort]) if (position) {
    halfWidth = Math.max(halfWidth, Math.abs(position[0])); halfHeight = Math.max(halfHeight, Math.abs(position[1]));
  }
  const scale = Math.min(cloudWidth / Math.max(2 * halfWidth, 1e-6), cloudHeight / Math.max(2 * halfHeight, 1e-6)) * .9;
  // One common scale for both layers: source position differences remain real.
  const point = ([x, y]: [number, number]) => [16 + cloudWidth / 2 + x * scale, cloudTop + cloudHeight / 2 - y * scale];
  context.fillStyle = '#638096'; context.globalAlpha = .25;
  for (const position of projection.background) { const [x, y] = point(position); context.fillRect(x, y, 1, 1); }
  context.globalAlpha = .6; context.strokeStyle = '#7894a7'; context.lineWidth = .65;
  let projectedEdges = 0;
  for (const [, source, target] of detail.topology.edges) {
    const a = projection.cohort[source], b = projection.cohort[target]; if (!a || !b) continue;
    const [x0, y0] = point(a), [x1, y1] = point(b), angle = Math.atan2(y1 - y0, x1 - x0);
    context.beginPath(); context.moveTo(x0, y0); context.lineTo(x1, y1);
    context.moveTo(x1 - Math.cos(angle - .5) * 5, y1 - Math.sin(angle - .5) * 5); context.lineTo(x1, y1); context.lineTo(x1 - Math.cos(angle + .5) * 5, y1 - Math.sin(angle + .5) * 5); context.stroke(); projectedEdges++;
  }
  const color = (slot: number) => {
    const count = window?.counts[slot];
    context.globalAlpha = count === undefined || count === 0 ? 1 : count === 1 ? .4 : count < 5 ? .7 : 1;
    if (count === undefined) return '#314957';
    if (countCategory(count) === '0') return '#405361';
    const group = detail.cells[slot].groups.find(name => name !== 'kc') ?? 'kc';
    return COLORS[GROUPS.indexOf(group)];
  };
  for (const [slot, position] of projection.cohort.entries()) {
    if (!position) continue; const [x, y] = point(position);
    context.fillStyle = color(slot); context.fillRect(x - 2.5, y - 2.5, 5, 5);
  }
  context.globalAlpha = 1; context.fillStyle = '#b8cddd';
  const gridX = narrow ? 16 : 384, gridHeading = narrow ? heading + 226 : heading;
  context.fillText('Schematic count grid', gridX, gridHeading);
  const spacing = 9.5;
  for (let slot = 0; slot < detail.cells.length; slot++) {
    context.fillStyle = color(slot); context.fillRect(gridX + slot % 16 * spacing, gridHeading + 15 + Math.floor(slot / 16) * spacing, 8, 8);
  }
  context.globalAlpha = 1; context.fillStyle = '#b8cddd';
  if (!narrow) { context.fillText('Source-ID table order', gridX, gridHeading + 185); context.fillText('Exact counts: inspect table', gridX, gridHeading + 201); }
  const coverageX = narrow ? 184 : 16, coverageWidth = narrow ? width - 200 : width - 32;
  let coverageY = narrow ? gridHeading + 16 : heading + 230;
  coverageY = wrappedText(context, `${detail.cells.length} fixed cells; ${positioned} positioned; ${detail.cells.length - positioned} without positions`, coverageX, coverageY, coverageWidth);
  const coverage = GROUPS.map((name, index) => `${LABELS[index]} ${detail.selection.group_selected_counts[name]}/${detail.selection.group_population_counts[name]}`).join(' · ');
  if (!narrow) coverageY = wrappedText(context, coverage, coverageX, coverageY, coverageWidth);
  wrappedText(context, `Connections: ${projectedEdges} projected / ${detail.topology.edges.length} displayed / ${detail.topology.eligible_edges} eligible`, coverageX, coverageY, coverageWidth);
  let footer = narrow ? heading + 624 : Math.max(coverageY + 20, heading + 280);
  if (narrow) footer = wrappedText(context, coverage, 16, footer, width - 32);
  footer = wrappedText(context, 'Node hue: group. Brightness: 0 neutral · 1 · 2–4 · 5+ counts per 100 ms', 16, footer, width - 32);
  footer = wrappedText(context, 'Static model connections — not measured transmission', 16, footer, width - 32);
  wrappedText(context, 'Simulated model activity; no biological motor validation.', 16, footer, width - 32);
  return { left: narrow ? 16 : 568, heading: narrow ? heading + 430 : heading, rowHeight: narrow ? 22 : 27 };
}
export function projectSomaPoints(anatomy: Anatomy | null): Array<[number, number]> {
  if (!anatomy?.points.length) return [];
  const minimum = [Infinity, Infinity, Infinity], maximum = [-Infinity, -Infinity, -Infinity];
  for (const point of anatomy.points) for (let axis = 0; axis < 3; axis++) { minimum[axis] = Math.min(minimum[axis], point[axis + 2] as number); maximum[axis] = Math.max(maximum[axis], point[axis + 2] as number); }
  const centre = minimum.map((value, axis) => (value + maximum[axis]) / 2), extent = Math.max(1, ...maximum.map((value, axis) => value - minimum[axis]));
  const projected: Array<[number, number]> = anatomy.points.map(point => {
    const x = (point[2] - centre[0]) / extent, y = (point[3] - centre[1]) / extent, z = (point[4] - centre[2]) / extent;
    return [x - z * .35, y + z * .2];
  });
  const bounds = projected.reduce((value, [x, y]) => [Math.min(value[0], x), Math.min(value[1], y), Math.max(value[2], x), Math.max(value[3], y)], [Infinity, Infinity, -Infinity, -Infinity]);
  const projectedExtent = Math.max(bounds[2] - bounds[0], bounds[3] - bounds[1], Number.EPSILON);
  return projected.map(([x, y]) => [(x - (bounds[0] + bounds[2]) / 2) / projectedExtent, (y - (bounds[1] + bounds[3]) / 2) / projectedExtent]);
}

export function drawSciencePanel(context: CanvasRenderingContext2D, width: number, height: number, recording: AnyRecording,
                                 sample: ReturnType<typeof sampleAnyAtTick>, traces: ActivityTrace[], anatomy: Anatomy | null,
                                 projection = projectSomaPoints(anatomy), cellPanel: CellPanel | null = null) {
  const { top, panelHeight, narrow } = scienceLayout(width, height, cellPanel !== null);
  context.save(); context.fillStyle = '#172B3A'; context.fillRect(0, top, width, panelHeight);
  context.font = '500 13px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#edf5fb';
  context.fillText(`Recorded population activity · replay ${(sample.tick / 10000).toFixed(3)} s`, 16, top + 22);
  context.font = '12px Bahnschrift, Aptos, sans-serif'; context.fillStyle = '#b8cddd';
  context.fillText(`Stim ${sample.segment.stimulation === null ? 'none' : 'present'} · learning ${sample.segment.learning}`, narrow ? 16 : width - 235, top + (narrow ? 40 : 22));
  const input = 'input' in sample ? `${videoSpeedLabel(recording)} · ${videoInputLabel(sample.input)}` : 'decision' in sample ? 'Paired event cards' : `Input ${sample.segment.stimulus}`;
  const clock = `Source ${(sample.sourceTick / 10000).toFixed(4)} s · event ${sample.segment.event_sequence}${'input' in sample ? ` · media PTS ${sample.input.source_pts} × ${sample.input.source_time_base[0]}/${sample.input.source_time_base[1]}` : ''}`;
  const detail = `Complete ${sample.bin.duration_ticks / 10} ms bin${'input' in sample ? ` · ${videoPolicyLabel(sample.clipPolicy ?? sample.policy)}` : ''} · integrity-only`;
  const captions = narrow ? [input, clock, detail] : [`${input} · ${clock}`, detail];
  let headerEnd = top + (narrow ? 42 : 24);
  for (const caption of captions) {
    let line = '';
    for (const word of caption.split(' ')) {
      if (line && context.measureText(`${line} ${word}`).width > width - 32) { headerEnd += 16; context.fillText(line, 16, headerEnd); line = word; }
      else line = line ? `${line} ${word}` : word;
    }
    headerEnd += 16; context.fillText(line, 16, headerEnd);
  }
  const anatomyHeading = headerEnd + 24;
  const cellLayout = cellPanel ? drawCells(context, width, headerEnd, cellPanel, sample.sourceTick) : null;
  const anatomyWidth = narrow ? width - 32 : 260;
  if (!cellPanel) {
  context.fillStyle = '#edf5fb'; context.fillText('Static cell-body positions', 16, anatomyHeading);
  context.fillStyle = '#b8cddd'; context.fillText('Source coordinates; not calibrated anatomy', 16, anatomyHeading + 16);
  const cloudTop = anatomyHeading + 24, cloudHeight = narrow ? 100 : 112;
  if (projection.length) {
    let halfWidth = 0, halfHeight = 0;
    for (const [x, y] of projection) { halfWidth = Math.max(halfWidth, Math.abs(x)); halfHeight = Math.max(halfHeight, Math.abs(y)); }
    const scale = Math.min(anatomyWidth / Math.max(2 * halfWidth, 1e-6), cloudHeight / Math.max(2 * halfHeight, 1e-6)) * .9;
    context.fillStyle = '#a8c8e0';
    for (const [x, y] of projection) context.fillRect(16 + anatomyWidth / 2 + x * scale, cloudTop + cloudHeight / 2 - y * scale, 1.2, 1.2);
  } else {
    context.fillStyle = '#edf5fb'; context.fillText(anatomy ? 'No positions available' : 'Anatomy not loaded', 24, cloudTop + 44);
    context.fillStyle = '#b8cddd'; if (!anatomy) context.fillText('Open anatomy in the viewer', 24, cloudTop + 64);
  }
  context.fillStyle = '#b8cddd';
  if (anatomy) {
    context.fillText(`${anatomy.coverage.displayed_cells.toLocaleString('en-US')} / ${anatomy.coverage.positioned_cells.toLocaleString('en-US')} positioned shown`, 16, cloudTop + cloudHeight + 18);
    context.fillText(`${anatomy.coverage.missing_positions.toLocaleString('en-US')} model cells without positions`, 16, cloudTop + cloudHeight + 34);
  }
  }
  const left = cellLayout?.left ?? (narrow ? 16 : 300), heading = cellLayout?.heading ?? (narrow ? anatomyHeading + 24 + 100 + 59 : anatomyHeading), rowHeight = cellLayout?.rowHeight ?? (narrow ? 22 : 27);
  context.fillText('Hz/cell · individual row scales', left, heading);
  const plotX = left + (narrow ? 142 : 155), plotWidth = width - plotX - 92;
  for (const [index, row] of traces.entries()) {
    const baseline = heading + 27 + index * rowHeight;
    context.fillStyle = row.color; context.fillText(row.label, left, baseline);
    context.fillStyle = '#ffffff'; context.fillText(sample.rates[row.name].toFixed(2), left + 72, baseline);
    context.fillStyle = '#b8cddd'; context.fillText(`max ${row.maximum.toFixed(1)}`, width - 86, baseline);
    context.strokeStyle = '#344f63'; context.beginPath(); context.moveTo(plotX, baseline); context.lineTo(plotX + plotWidth, baseline); context.stroke();
    context.strokeStyle = row.color; context.lineWidth = 1.2; context.beginPath();
    let previousRate: number | null = null;
    for (const bin of row.bins) {
      if (bin.start >= sample.tick) break;
      const x0 = plotX + bin.start / recording.duration_ticks * plotWidth, x1 = plotX + Math.min(sample.tick, bin.end) / recording.duration_ticks * plotWidth;
      const y = baseline - bin.rate / row.maximum * 15;
      if (previousRate === null) context.moveTo(x0, y); else context.lineTo(x0, y);
      context.lineTo(x1, y); previousRate = bin.rate;
    }
    context.stroke();
    const cursor = plotX + sample.tick / recording.duration_ticks * plotWidth;
    context.strokeStyle = '#e8f2fa'; context.beginPath(); context.moveTo(cursor, baseline - 17); context.lineTo(cursor, baseline + 2); context.stroke();
  }
  context.restore();
}
