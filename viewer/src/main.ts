import { isSessionRecording, sampleSessionAtTick } from './session-replay.ts';
import './style.css';
import { GROUPS, advancePlayback } from './replay.ts';
import { BufferTarget, CanvasSource, Output, WebMOutputFormat, canEncodeVideo } from 'mediabunny';
import { EXPORT_FPS, EXPORT_SIZE, advancePresentationPlayback, quantizeVideoTick, writeFrames } from './export.ts';
import { createStage } from './stage.ts';
import { createOperationGate } from './operation.ts';
import { isVideoRecording, videoInputLabel, videoPolicyLabel, videoSpeedLabel, videoTimelineBlocks } from './video-replay.ts';
import { parseAnyRecording, sampleAnyAtTick as sampleAt, type AnyRecording } from './recording.ts';
import { EVENT_HOLD_FRAMES, eventPlanJson, eventPresentation, isEventRecording, sampleEventAtTick } from './event-replay.ts';
import { MAX_ANATOMY_BYTES, createAnatomyAttachment, readRecordingFile } from './anatomy.ts';
import { MAX_CELL_ACTIVITY_BYTES, assertCellAnatomy, buildCellWindows, cellWindowAtTick, createCellActivityAttachment, type CellWindow } from './cell-activity.ts';
import { MAX_FOLLOWUP_BYTES, createFollowupAttachment, type FollowupBundle } from './followup.ts';
import { readDemoFiles, type DemoCandidate } from './demo.ts';

function element<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}
const canvas = element<HTMLCanvasElement>('stage');
const file = element<HTMLInputElement>('file');
const play = element<HTMLButtonElement>('play');
const seek = element<HTMLInputElement>('seek');
const speed = element<HTMLSelectElement>('speed');
const videoButton = element<HTMLButtonElement>('video');
const openButton = element<HTMLButtonElement>('open');
const demoButton = element<HTMLButtonElement>('demo-open');
const demoFiles = element<HTMLInputElement>('demo-files');
const sourceButton = element<HTMLButtonElement>('source-toggle');
const errorElement = element<HTMLParagraphElement>('error');
const videoNote = element<HTMLParagraphElement>('video-note');
const planButton = element<HTMLButtonElement>('download-plan');
const anatomyButton = element<HTMLButtonElement>('anatomy-open');
const anatomyFile = element<HTMLInputElement>('anatomy-file');
const anatomyNote = element('anatomy-note');
let anatomyAttachment = createAnatomyAttachment();
let anatomyLoading = false, anatomyRequest = 0;
const cellButton = element<HTMLButtonElement>('cell-open');
const cellFile = element<HTMLInputElement>('cell-file');
const cellNote = element('cell-note');
const cellCountCaption = element('cell-count-caption');
const cellCountBody = element('cell-count-body');
let cellAttachment = createCellActivityAttachment();
let cellLoading = false, cellRequest = 0, cellWindows: CellWindow[] = [], cellRows: HTMLElement[] = [];
let lastCellWindow: CellWindow | null | undefined;
const followupButton = element<HTMLButtonElement>('followup-open');
const followupFiles = element<HTMLInputElement>('followup-files');
const followupDownload = element<HTMLButtonElement>('followup-download');
const followupStatus = element('followup-status');
const followupContent = element('followup-content');
const followupTitle = element('followup-title');
const followupOverview = element('followup-overview');
const followupPreparation = element('followup-preparation');
const followupQuestions = element('followup-questions');
let followupAttachment = createFollowupAttachment();
let followupLoading = false, followupRequest = 0, shownFollowup: FollowupBundle | null = null;
const replayAnnouncement = element('replay-announcement');
let recording: AnyRecording | null = null;
let tick = 0, playing = false, lastTime = performance.now();
let holdElapsedTicks = 0;
const operations = createOperationGate();
let exportController: AbortController | null = null;
let videoCodec: 'vp9' | 'vp8' | null = null;
let pageHidden = false;
let stage: ReturnType<typeof createStage> | null = null;
let stageError = '';
try { stage = createStage(canvas); }
catch { stageError = '3D rendering is unavailable. Enable WebGL and reload to view the fly or export video. Recorded telemetry remains available.'; }

videoNote.textContent = 'Checking WebCodecs video encoding support…';
if (stage && typeof VideoEncoder !== 'undefined') {
  void (async () => {
    try {
      for (const candidate of ['vp9', 'vp8'] as const) {
        if (await canEncodeVideo(candidate, { width: EXPORT_SIZE, height: EXPORT_SIZE, frameRate: EXPORT_FPS })) { videoCodec = candidate; break; }
      }
      anatomyControls();
      videoNote.textContent = videoCodec ? `Video export: 900×900, 30 timestamped frames/s. Last ${holdSeconds(recording)} s holds the measured terminal sample${recording && (isEventRecording(recording) || isSessionRecording(recording)) ? ' and locked plan' : ''} for presentation.` : 'Video export unavailable: this browser cannot encode VP9 or VP8 with WebCodecs at 900×900.';
    } catch { videoNote.textContent = 'Video export unavailable: WebCodecs capability check failed.'; }
  })();
} else videoNote.textContent = 'Video export unavailable: WebGL and WebCodecs video encoding are required.';

for (const name of ['pam11', 'ppl101', 'mbon07'] as const) {
  const row = document.createElement('p'), label = document.createElement('span'), value = document.createElement('b');
  label.textContent = name.toUpperCase(); value.id = `${name}-rate`; value.textContent = '—';
  row.append(label, value); element('additional-rates').append(row);
}

function showError(message: string) { errorElement.textContent = message; errorElement.hidden = false; }
if (stageError) showError(stageError);
function holdSeconds(record: AnyRecording | null) { return record && (isEventRecording(record) || isSessionRecording(record)) ? 3 : .5; }
function presentationHoldTicks() { return recording && (isEventRecording(recording) || isSessionRecording(recording)) ? 30000 : 0; }
function renderCurrent() { stage?.render(presentationHoldTicks() > 0 && tick >= (recording?.duration_ticks ?? Infinity) ? true : undefined, holdElapsedTicks); }
function anatomyControls() {
  anatomyButton.disabled = !recording || operations.loading || operations.exporting || anatomyLoading || cellLoading || followupLoading;
  anatomyFile.disabled = anatomyButton.disabled;
  cellButton.disabled = anatomyButton.disabled; cellFile.disabled = cellButton.disabled;
  followupButton.disabled = !recording || !isSessionRecording(recording) || anatomyButton.disabled;
  followupFiles.disabled = followupButton.disabled;
  videoButton.disabled = !recording || !videoCodec || !stage || operations.loading || (!operations.exporting && (anatomyLoading || cellLoading || followupLoading));
  updateFollowup();
}

function updateFollowup() {
  const sample = recording && isSessionRecording(recording) ? sampleSessionAtTick(recording, tick) : null;
  const plan = sample && 'plan' in sample ? sample.plan : null;
  const value = followupAttachment.value, selected = !!plan?.selected_option;
  const visible = !!value && selected;
  const status = followupLoading ? 'Loading planning companion…' : plan && !selected ? 'No selected plan — planning companion unavailable.'
    : !value ? 'Planning companion not loaded.' : selected ? 'Planning companion available for the current selected plan.' : 'Planning companion loaded — awaiting the recorded selection.';
  if (followupStatus.textContent !== status) followupStatus.textContent = status;
  followupContent.hidden = !visible;
  followupDownload.hidden = !visible;
  followupDownload.disabled = !visible || operations.loading || operations.exporting || anatomyLoading || cellLoading || followupLoading;
  if (!visible) {
    if (shownFollowup) { followupTitle.textContent = ''; followupOverview.textContent = ''; followupPreparation.replaceChildren(); followupQuestions.replaceChildren(); }
    shownFollowup = null; return;
  }
  if (value !== shownFollowup) {
    followupTitle.textContent = value!.followup.plan.selected_option!.title;
    followupOverview.textContent = value!.followup.supplement.overview;
    for (const [list, items] of [[followupPreparation, value!.followup.supplement.preparation], [followupQuestions, value!.followup.supplement.open_questions]] as const) {
      list.replaceChildren();
      for (const text of items) { const item = document.createElement('li'); item.textContent = text; list.append(item); }
    }
    shownFollowup = value;
  }
}

function updateCellCounts(sourceTick: number) {
  const detail = cellAttachment.value;
  if (!detail) return;
  const window = cellWindowAtTick(cellWindows, sourceTick);
  if (window === lastCellWindow) return;
  lastCellWindow = window;
  cellCountCaption.textContent = window ? `Completed 100 ms window ${(window.start_tick / 10000).toFixed(3)}–${(window.end_tick / 10000).toFixed(3)} s. Schematic grid slots follow these source-ID rows.` : 'Awaiting first complete 100 ms window';
  cellRows.forEach((row, slot) => { row.textContent = window ? String(window.counts[slot]) : '—'; });
}

const traceBases: Partial<Record<'kc' | 'mbon11', HTMLCanvasElement>> = {};
function drawTrace(name: 'kc' | 'mbon11') {
  const trace = element<HTMLCanvasElement>(`${name}-trace`), ctx = trace.getContext('2d')!;
  if (!recording) return;
  const width = Math.max(1, Math.round(trace.clientWidth * 2));
  let base = traceBases[name];
  if (!base || base.width !== width) {
    base = document.createElement('canvas'); base.width = width; base.height = 64; traceBases[name] = base;
    const background = base.getContext('2d')!;
    background.strokeStyle = '#c9d9e5'; background.beginPath(); background.moveTo(0, 60); background.lineTo(width, 60); background.stroke();
    const bins = recording.segments.flatMap((segment) => segment.bins.map((bin) => ({
      end: segment.playback_start_tick + bin.end_tick - segment.source_start_tick,
      duration: bin.duration_ticks,
      rate: bin.group_spikes[name] * 10000 / (recording!.groups[name] * bin.duration_ticks),
    })));
    const max = Math.max(1, ...bins.map((bin) => bin.rate));
    background.strokeStyle = name === 'mbon11' ? '#2456d6' : '#597083'; background.lineWidth = 2; background.beginPath();
    for (const [index, bin] of bins.entries()) {
      const x0 = (bin.end - bin.duration) / recording.duration_ticks * width;
      const x1 = bin.end / recording.duration_ticks * width;
      const y = 60 - bin.rate / max * 50;
      if (index === 0) background.moveTo(x0, y); else background.lineTo(x0, y);
      background.lineTo(x1, y);
    }
    background.stroke();
  }
  if (trace.width !== width || trace.height !== 64) { trace.width = width; trace.height = 64; }
  ctx.clearRect(0, 0, width, 64); ctx.drawImage(base, 0, 0);
  ctx.strokeStyle = '#172b3a'; ctx.lineWidth = 1.5; ctx.beginPath();
  const x = tick / recording.duration_ticks * trace.width; ctx.moveTo(x, 0); ctx.lineTo(x, 64); ctx.stroke();
}

function update() {
  if (!recording) return;
  const sample = sampleAt(recording, tick);
  stage?.setSample(sample);
  updateFollowup();
  updateCellCounts(sample.sourceTick);
  const video = 'input' in sample;
  const event = 'decision' in sample;
  element('input-caption').textContent = event ? 'Exact fed paired RGB · 384×216' : video ? `Fed video frame · ${videoSpeedLabel(recording)}` : 'Recorded input';
  element('stimulus').textContent = event ? 'Event options' : video ? videoInputLabel(sample.input) : sample.segment.stimulus === 'black' ? 'Black' : sample.segment.stimulus;
  element('stimulation').textContent = sample.segment.stimulation === null ? 'None' : 'Present';
  element('learning').textContent = String(sample.segment.learning);
  for (const name of GROUPS) element(`${name}-rate`).textContent = sample.rates[name].toFixed(2);
  element('source-clock').textContent = `${(sample.sourceTick / 10000).toFixed(4)} s`;
  element('event-sequence').textContent = String(sample.segment.event_sequence);
  element('video-policy').hidden = !video;
  element('event-plan').hidden = !event;
  planButton.hidden = !event || !sample.plan;
  if (event) {
    const view = eventPresentation(sample);
    const message = !sample.decision ? 'Paired event options. Choice pending.' : sample.plan?.selected_option ? `Selected option: ${sample.plan.selected_option.title}. Engineered measured lateral policy.` : 'Deferred. No option selected by the measured lateral policy.';
    if (replayAnnouncement.textContent !== message) replayAnnouncement.textContent = message;
    element('event-status').textContent = view.status;
    element('event-title').textContent = view.title;
    element('event-details').textContent = view.lines.join('\n');
    element('event-measurement').textContent = view.measurement;
    planButton.disabled = !view.canDownload || operations.loading || operations.exporting;
  } else {
    planButton.disabled = true;
    const message = video ? `Feed clip ${Number(sample.input.clip_id.slice(5)) + 1}.` : `Recorded stimulus: ${sample.segment.stimulus === 'black' ? 'Black' : sample.segment.stimulus}.`;
    if (replayAnnouncement.textContent !== message) replayAnnouncement.textContent = message;
  }
  if (video) {
    element('source-pts').textContent = `${sample.input.source_pts} × ${sample.input.source_time_base[0]}/${sample.input.source_time_base[1]} s`;
    if (isVideoRecording(recording) || isSessionRecording(recording)) {
      const clips = recording.source.metadata.clips as Array<{ source_url: string }>;
      element<HTMLAnchorElement>('clip-url').href = clips[Number(sample.input.clip_id.slice(5))].source_url;
      element('policy-note').textContent = `Recorded right-scroll/${recording.version === 'measured-video-replay/v1' ? 'v1' : 'v2'} display policy; not validated fly behavior.`;
    }
    element('policy-status').textContent = videoPolicyLabel(sample.policy);
    const current = sample.clipPolicy;
    element('rolling-readout').textContent = current?.window && current.readout ? `${current.readout.action} · Δ ${current.readout.signed_difference_hz.toFixed(2)} Hz · L ${current.window.counts.motor_left} / R ${current.window.counts.motor_right} spikes over 300 ms` : 'Unavailable until 300 ms of this clip has been observed';
  }
  element('bin-note').textContent = `Hz / cell = integer spikes ÷ population ÷ ${(sample.bin.duration_ticks / 10).toFixed(1)} ms. Complete recorded-bin values; traces hold each bin without smoothing.`;
  element('time').textContent = `${(sample.tick / 10000).toFixed(3)} / ${(recording.duration_ticks / 10000).toFixed(3)} s`;
  seek.value = String(sample.tick); seek.setAttribute('aria-valuetext', `${(sample.tick / 10000).toFixed(3)} seconds, input ${event ? 'paired event options' : video ? videoInputLabel(sample.input) : sample.segment.stimulus}`);
  play.textContent = playing ? 'Pause' : 'Play'; play.setAttribute('aria-label', playing ? 'Pause recording' : 'Play recording');
  drawTrace('kc'); drawTrace('mbon11');
}

openButton.addEventListener('click', () => file.click());
function loadingControls(loading: boolean) {
  openButton.disabled = loading; file.disabled = loading; demoButton.disabled = loading; demoFiles.disabled = loading;
  play.disabled = loading || !recording; seek.disabled = loading || !recording; speed.disabled = loading || !recording;
  videoButton.disabled = loading || !recording || !videoCodec || !stage;
  planButton.disabled = loading || !recording || !(isEventRecording(recording) || isSessionRecording(recording)) || tick < recording.decision.effective_tick;
  openButton.textContent = loading ? 'Opening…' : 'Open recording';
  anatomyControls();
}
function beginLoad() {
  anatomyRequest++; cellRequest++;
  anatomyAttachment.cancelPending(); anatomyLoading = false;
  cellAttachment.cancelPending(); cellLoading = false;
  followupRequest++; followupAttachment.cancelPending(); followupLoading = false;
  playing = false; update();
  loadingControls(true);
}

function installAnatomy() {
  stage?.setAnatomy(anatomyAttachment.value);
  anatomyNote.textContent = `${anatomyAttachment.value!.coverage.displayed_cells.toLocaleString('en-US')} static source positions loaded`;
}
function installCells() {
  const detail = cellAttachment.value!;
  stage?.setCellActivity(detail);
  cellWindows = buildCellWindows(detail); lastCellWindow = undefined; cellRows = []; cellCountBody.replaceChildren();
  for (const [slot, cell] of detail.cells.entries()) {
    const row = document.createElement('tr');
    for (const text of [String(slot + 1), String(cell.source_id), cell.groups.join(', '), cell.soma ? cell.soma.join(', ') : 'Missing position']) {
      const value = document.createElement('td'); value.textContent = text; row.append(value);
    }
    const count = document.createElement('td'); count.textContent = '—'; row.append(count); cellRows.push(count); cellCountBody.append(row);
  }
  cellNote.textContent = `${detail.cells.length} recorded cells; ${detail.cells.filter(cell => !cell.soma).length} without positions. Static model connections, not measured transmission.`;
}

function installRecording(parsed: AnyRecording, raw: { sha256: string; byteLength: number }, name: string, candidate?: DemoCandidate) {
  recording = parsed; tick = 0; holdElapsedTicks = 0;
  const identity = parsed.source.metadata.engine_identity as { model_provenance?: { graph_ids_sha256?: string } };
  anatomyAttachment = candidate?.anatomyAttachment ?? createAnatomyAttachment();
  cellAttachment = candidate?.cellAttachment ?? createCellActivityAttachment();
  followupAttachment = candidate?.followupAttachment ?? createFollowupAttachment();
  if (!candidate) anatomyAttachment.setRecording({ recordingSha256: raw.sha256, graphIdsSha256: identity?.model_provenance?.graph_ids_sha256 ?? '' });
  anatomyNote.textContent = 'Anatomy not loaded';
  if (!candidate) cellAttachment.setRecording({ recordingSha256: raw.sha256, recording: parsed });
  if (!candidate) followupAttachment.setRecording(isSessionRecording(parsed) ? { recording: parsed, recordingSha256: raw.sha256, recordingByteLength: raw.byteLength } : null);
  cellNote.textContent = 'Cell activity not loaded'; cellCountCaption.textContent = 'Cell activity not loaded';
  cellWindows = []; cellRows = []; lastCellWindow = undefined; cellCountBody.replaceChildren();
  delete traceBases.kc; delete traceBases.mbon11;
  stage?.setRecording(parsed);
  if (candidate) { installAnatomy(); installCells(); }
  errorElement.hidden = true;
  if (stageError) showError(stageError);
  element('recording-name').textContent = name;
  element('status').textContent = 'Recorded simulation'; element('status').classList.add('loaded');
  seek.max = String(parsed.duration_ticks); seek.disabled = false; play.disabled = false; speed.disabled = false; sourceButton.disabled = false;
  videoButton.disabled = !videoCodec || !stage;
  element('timeline-end').textContent = `${(parsed.duration_ticks / 10000).toFixed(1)} s`;
  const segments = element('segments'); segments.replaceChildren();
  if (isEventRecording(parsed)) {
    const item = document.createElement('span'); item.className = 'stimulus-event'; item.style.flexGrow = '1'; item.textContent = 'Paired options · 1.5 s settling + 0.5 s decision'; segments.append(item);
  } else if (isVideoRecording(parsed) || isSessionRecording(parsed)) {
    for (const block of videoTimelineBlocks({ segments: parsed.segments.flatMap((segment) => 'clip_id' in segment ? [segment] : []) })) {
      const item = document.createElement('span'); item.className = `stimulus-video-${Number(block.clipId.slice(5)) % 2}`;
      item.style.flexGrow = String(block.duration); item.textContent = `Clip ${Number(block.clipId.slice(5)) + 1}`; segments.append(item);
    }
    if (isSessionRecording(parsed)) {
      const item = document.createElement('span'); item.className = 'stimulus-event'; item.style.flexGrow = '20000'; item.textContent = 'Paired options · 1.5 s settling + 0.5 s decision'; segments.append(item);
    }
  } else for (const segment of parsed.segments) {
    const item = document.createElement('span'); item.className = `stimulus-${segment.stimulus}`;
    item.style.flexGrow = String(segment.playback_end_tick - segment.playback_start_tick);
    item.textContent = segment.stimulus === 'black' ? '' : segment.stimulus; segments.append(item);
  }
  element('source-mode').textContent = parsed.source.verification_mode;
  element('source-json').textContent = JSON.stringify(parsed.source, null, 2);
  if (videoCodec) videoNote.textContent = `Video export: 900×900, 30 timestamped frames/s. Last ${holdSeconds(parsed)} s holds the measured terminal sample${(isEventRecording(parsed) || isSessionRecording(parsed)) ? ' and locked plan' : ''} for presentation.`;
  update(); stage?.render();
}

file.addEventListener('change', async () => {
  const selected = file.files?.[0]; file.value = '';
  if (!selected) return;
  const generation = operations.beginLoad();
  if (generation === null) return;
  beginLoad();
  try {
    if (selected.size > 32 * 1024 * 1024) throw new Error('File exceeds 32 MiB. Export a shorter observation recording.');
    const raw = await readRecordingFile(selected);
    const parsed = await parseAnyRecording(raw.text);
    if (!operations.isCurrentLoad(generation)) return;
    installRecording(parsed, raw, selected.name);
  } catch (error) {
    if (operations.isCurrentLoad(generation)) showError(`Cannot open recording. ${error instanceof Error ? error.message : 'Invalid file.'} Choose the JSON produced by export-replay.${recording ? ' The previous recording remains loaded.' : ''}`);
  } finally { if (operations.isCurrentLoad(generation)) { operations.endLoad(generation); loadingControls(false); } }
});

demoButton.addEventListener('click', () => { if (!demoButton.disabled) demoFiles.click(); });
demoFiles.addEventListener('change', async () => {
  const selected = Array.from(demoFiles.files ?? []); demoFiles.value = '';
  if (!selected.length) return;
  const generation = operations.beginLoad();
  if (generation === null) return;
  beginLoad();
  try {
    const candidate = await readDemoFiles(selected);
    if (!operations.isCurrentLoad(generation)) return;
    installRecording(candidate.recording, { sha256: candidate.recordingSha256, byteLength: candidate.recordingByteLength }, 'Local demo', candidate);
  } catch (error) {
    if (operations.isCurrentLoad(generation)) showError(`Cannot open demo. ${error instanceof Error ? error.message : 'Invalid files.'} Select all five JSON files from the same prepared demo folder. The previous recording and layers remain loaded.`);
  } finally { if (operations.isCurrentLoad(generation)) { operations.endLoad(generation); loadingControls(false); } }
});

anatomyButton.addEventListener('click', () => { if (!anatomyButton.disabled) anatomyFile.click(); });
anatomyFile.addEventListener('change', async () => {
  const selected = anatomyFile.files?.[0]; anatomyFile.value = '';
  if (!selected || !recording || anatomyLoading || cellLoading || followupLoading || operations.loading || operations.exporting) return;
  const sourceRecording = recording, request = ++anatomyRequest;
  const current = () => recording === sourceRecording && request === anatomyRequest;
  anatomyLoading = true; anatomyControls();
  try {
    if (selected.size > MAX_ANATOMY_BYTES) throw new Error('Anatomy file exceeds 8 MiB.');
    const attached = await anatomyAttachment.load(selected.text());
    if (!attached || !current()) return;
    assertCellAnatomy(cellAttachment.value, anatomyAttachment.value);
    installAnatomy();
    errorElement.hidden = true;
  } catch (error) {
    if (current()) showError(`Cannot open anatomy. ${error instanceof Error ? error.message : 'Invalid sidecar.'} Generate a sidecar for this exact recording; replay remains available.`);
  } finally {
    if (current()) { anatomyLoading = false; anatomyControls(); renderCurrent(); }
  }
});

cellButton.addEventListener('click', () => { if (!cellButton.disabled) cellFile.click(); });
cellFile.addEventListener('change', async () => {
  const selected = cellFile.files?.[0]; cellFile.value = '';
  if (!selected || !recording || cellLoading || anatomyLoading || followupLoading || operations.loading || operations.exporting) return;
  const sourceRecording = recording, request = ++cellRequest;
  const current = () => recording === sourceRecording && request === cellRequest;
  cellLoading = true; anatomyControls();
  try {
    if (selected.size > MAX_CELL_ACTIVITY_BYTES) throw new Error('Cell activity file exceeds 16 MiB.');
    const attached = await cellAttachment.load(selected.text());
    if (!attached || !current()) return;
    const detail = cellAttachment.value!;
    assertCellAnatomy(detail, anatomyAttachment.value);
    installCells();
    errorElement.hidden = true; update();
  } catch (error) {
    if (current()) showError(`Cannot open cell activity. ${error instanceof Error ? error.message : 'Invalid sidecar.'} Choose a sidecar for this exact recording; replay remains available.`);
  } finally {
    if (current()) { cellLoading = false; anatomyControls(); renderCurrent(); }
  }
});

followupButton.addEventListener('click', () => { if (!followupButton.disabled) followupFiles.click(); });
followupFiles.addEventListener('change', async () => {
  const selected = Array.from(followupFiles.files ?? []); followupFiles.value = '';
  if (!selected.length || !recording || !isSessionRecording(recording) || followupLoading || anatomyLoading || cellLoading || operations.loading || operations.exporting) return;
  const sourceRecording = recording, request = ++followupRequest;
  const current = () => recording === sourceRecording && request === followupRequest;
  followupLoading = true; anatomyControls();
  try {
    if (selected.length !== 2 || selected.some(file => !file.size || file.size > MAX_FOLLOWUP_BYTES)) throw new Error('Choose exactly two nonempty JSON files, each at most 128 KiB.');
    const inputs = Promise.all(selected.map(async file => {
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (bytes.byteLength !== file.size) throw new Error('A companion file changed while reading.');
      return bytes;
    }));
    const attached = await followupAttachment.load(inputs);
    if (!current() || !attached) return;
    errorElement.hidden = true;
  } catch (error) {
    if (current()) showError(`Cannot open planning companion. ${error instanceof Error ? error.message : 'Invalid files.'} Choose followup.json and its validated receipt.json for this exact recording; the previous valid attachment remains available.`);
  } finally {
    if (current()) { followupLoading = false; anatomyControls(); }
  }
});
followupDownload.addEventListener('click', () => {
  if (!recording || !isSessionRecording(recording) || operations.loading || operations.exporting || followupLoading || anatomyLoading || cellLoading) return;
  const sample = sampleSessionAtTick(recording, tick), value = followupAttachment.value;
  if (!('plan' in sample) || !sample.plan?.selected_option || !value) return;
  const url = URL.createObjectURL(new Blob([value.markdownBytes.slice()], { type: 'text/markdown;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = 'event-plan.md'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
});

sourceButton.addEventListener('click', () => {
  const panel = element('source-panel'); panel.hidden = !panel.hidden;
  sourceButton.setAttribute('aria-expanded', String(!panel.hidden));
});
planButton.addEventListener('click', () => {
  if (!recording || !(isEventRecording(recording) || isSessionRecording(recording)) || operations.loading || operations.exporting) return;
  const sample = isSessionRecording(recording) ? sampleSessionAtTick(recording, tick) : sampleEventAtTick(recording, tick);
  const json = 'decision' in sample ? eventPlanJson(sample, operations) : null;
  if (!json) return;
  const url = URL.createObjectURL(new Blob([json], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = 'event-plan.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
});
play.addEventListener('click', () => {
  if (!recording) return;
  if (tick >= recording.duration_ticks && (presentationHoldTicks() === 0 || holdElapsedTicks >= presentationHoldTicks())) { tick = 0; holdElapsedTicks = 0; }
  playing = !playing; lastTime = performance.now(); update();
});
seek.addEventListener('input', () => { tick = Number(seek.value); holdElapsedTicks = 0; update(); });
speed.addEventListener('change', () => { lastTime = performance.now(); });
canvas.addEventListener('keydown', (event) => {
  if (document.activeElement !== canvas || !recording || operations.loading || operations.exporting || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (!['Space', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.code)) return;
  event.preventDefault();
  if (event.code === 'Space') { if (!event.repeat) play.click(); return; }
  tick = event.code === 'Home' ? 0 : event.code === 'End' ? recording.duration_ticks : Math.max(0, Math.min(recording.duration_ticks, tick + (event.code === 'ArrowLeft' ? -1000 : 1000)));
  holdElapsedTicks = 0;
  update();
});

function exportControls(exporting: boolean) {
  cellAttachment.setExporting(exporting);
  followupAttachment.setExporting(exporting);
  openButton.disabled = exporting; file.disabled = exporting; demoButton.disabled = exporting; demoFiles.disabled = exporting; play.disabled = exporting; seek.disabled = exporting; speed.disabled = exporting;
  videoButton.textContent = exporting ? 'Cancel export' : 'Export video';
  videoButton.disabled = !exporting && (!recording || !videoCodec || !stage);
  planButton.disabled = exporting || !recording || !(isEventRecording(recording) || isSessionRecording(recording)) || tick < recording.decision.effective_tick;
  anatomyControls();
}

videoButton.addEventListener('click', async () => {
  if (exportController) { exportController.abort(); return; }
  if (!recording || !videoCodec || !stage || anatomyLoading || cellLoading || followupLoading || !operations.beginExport()) return;
  const sourceRecording = recording, sourceStage = stage;
  const previousTick = tick, previousHoldElapsedTicks = holdElapsedTicks, wasPlaying = playing;
  const controller = new AbortController(); exportController = controller;
  playing = false; exportControls(true); sourceStage.setExporting(true);
  let output: Output<WebMOutputFormat, BufferTarget> | null = null;
  try {
    const target = new BufferTarget();
    output = new Output({ format: new WebMOutputFormat(), target });
    const source = new CanvasSource(canvas, { codec: videoCodec, bitrate: 5_000_000 });
    output.addVideoTrack(source);
    await output.start();
    controller.signal.throwIfAborted();
    const completed = await writeFrames(sourceRecording.duration_ticks, {
      paint: (frame) => { sourceStage.setSample(sampleAt(sourceRecording, frame.tick)); sourceStage.render(frame.terminalHold, frame.holdElapsedTicks); },
      add: (timestamp, duration) => source.add(timestamp, duration),
      finalize: async () => { await output!.finalize(); return target.buffer; },
      cancel: () => output!.cancel(),
    }, controller.signal, (done, total) => { videoNote.textContent = `Encoding ${done}/${total} frames…`; }, (isVideoRecording(sourceRecording) || isSessionRecording(sourceRecording)) ? quantizeVideoTick : undefined, (isEventRecording(sourceRecording) || isSessionRecording(sourceRecording)) ? EVENT_HOLD_FRAMES : undefined);
    if (!completed?.byteLength) throw new Error('Encoder produced an empty video.');
    const url = URL.createObjectURL(new Blob([completed], { type: 'video/webm' }));
    const link = document.createElement('a'); link.href = url; link.download = 'measured-replay.webm'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    videoNote.textContent = `Video exported. The final ${holdSeconds(sourceRecording)} s holds the measured terminal sample${(isEventRecording(sourceRecording) || isSessionRecording(sourceRecording)) ? ' and locked plan' : ''} for presentation; no simulation time is added.`;
  } catch (error) {
    if (output && output.state !== 'canceled' && output.state !== 'finalized') try { await output.cancel(); } catch { /* Preserve export error. */ }
    if (controller.signal.aborted) videoNote.textContent = 'Video export canceled. No video was saved.';
    else { showError(`Video export failed: ${error instanceof Error ? error.message : 'Unknown encoding error.'} No video was saved.`); videoNote.textContent = 'Video export failed. No video was saved.'; }
  } finally {
    tick = previousTick; holdElapsedTicks = previousHoldElapsedTicks; playing = wasPlaying; lastTime = performance.now();
    sourceStage.setExporting(false); exportController = null; operations.endExport(); exportControls(false); update();
    if (pageHidden) sourceStage.dispose(); else renderCurrent();
  }
});

function frame(time: number) {
  if (exportController) { lastTime = time; return; }
  if (recording) {
    const state = advancePresentationPlayback(tick + holdElapsedTicks, Math.max(0, time - lastTime), Number(speed.value), playing, recording.duration_ticks, presentationHoldTicks());
    tick = state.tick; holdElapsedTicks = state.holdElapsedTicks; playing = state.playing; update();
  }
  lastTime = time;
  renderCurrent();
}
if (stage) stage.renderer.setAnimationLoop(frame);
else {
  const ctx = canvas.getContext('2d');
  if (ctx) { canvas.width = 900; canvas.height = 600; ctx.fillStyle = '#DFEAF2'; ctx.fillRect(0, 0, 900, 600); ctx.fillStyle = '#172B3A'; ctx.font = '24px Bahnschrift, sans-serif'; ctx.fillText('3D rendering unavailable', 45, 285); ctx.font = '16px Bahnschrift, sans-serif'; ctx.fillText('Enable WebGL to see the illustrative fly. Recorded telemetry is available beside the stage.', 45, 320); }
  const fallbackFrame = (time: number) => { frame(time); requestAnimationFrame(fallbackFrame); }; requestAnimationFrame(fallbackFrame);
}
window.addEventListener('pagehide', () => { pageHidden = true; exportController?.abort(); if (!exportController) stage?.dispose(); });
