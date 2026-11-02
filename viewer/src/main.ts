import './style.css';
import { GROUPS, advancePlayback } from './replay.ts';
import { BufferTarget, CanvasSource, Output, WebMOutputFormat, canEncodeVideo } from 'mediabunny';
import { EXPORT_FPS, EXPORT_SIZE, quantizeVideoTick, writeFrames } from './export.ts';
import { createStage } from './stage.ts';
import { createOperationGate } from './operation.ts';
import { isVideoRecording, videoInputLabel, videoPolicyLabel, videoSpeedLabel, videoTimelineBlocks } from './video-replay.ts';
import { parseAnyRecording, sampleAnyAtTick as sampleAt, type AnyRecording } from './recording.ts';
import { EVENT_HOLD_FRAMES, eventPlanJson, eventPresentation, isEventRecording, sampleEventAtTick } from './event-replay.ts';

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
const sourceButton = element<HTMLButtonElement>('source-toggle');
const errorElement = element<HTMLParagraphElement>('error');
const videoNote = element<HTMLParagraphElement>('video-note');
const planButton = element<HTMLButtonElement>('download-plan');
let recording: AnyRecording | null = null;
let tick = 0, playing = false, lastTime = performance.now();
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
      videoButton.disabled = !recording || !videoCodec || operations.loading || operations.exporting;
      videoNote.textContent = videoCodec ? `Video export: 900×900, 30 timestamped frames/s. Last ${holdSeconds(recording)} s holds the measured terminal sample${recording && isEventRecording(recording) ? ' and locked plan' : ''} for presentation.` : 'Video export unavailable: this browser cannot encode VP9 or VP8 with WebCodecs at 900×900.';
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
function holdSeconds(record: AnyRecording | null) { return record && isEventRecording(record) ? 3 : .5; }

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
  if (event) {
    const view = eventPresentation(sample);
    element('event-status').textContent = view.status;
    element('event-title').textContent = view.title;
    element('event-details').textContent = view.lines.join('\n');
    element('event-measurement').textContent = view.measurement;
    planButton.disabled = !view.canDownload || operations.loading || operations.exporting;
  } else planButton.disabled = true;
  if (video) {
    element('source-pts').textContent = `${sample.input.source_pts} × ${sample.input.source_time_base[0]}/${sample.input.source_time_base[1]} s`;
    if (isVideoRecording(recording)) {
      const clips = recording.source.metadata.clips as Array<{ source_url: string }>;
      element<HTMLAnchorElement>('clip-url').href = clips[Number(sample.input.clip_id.slice(5))].source_url;
      element('policy-note').textContent = `Recorded right-scroll/${recording.version === 'measured-video-replay/v2' ? 'v2' : 'v1'} display policy; not validated fly behavior.`;
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
  openButton.disabled = loading; file.disabled = loading;
  play.disabled = loading || !recording; seek.disabled = loading || !recording; speed.disabled = loading || !recording;
  videoButton.disabled = loading || !recording || !videoCodec || !stage;
  planButton.disabled = loading || !recording || !isEventRecording(recording) || tick < recording.decision.effective_tick;
  openButton.textContent = loading ? 'Opening…' : 'Open recording';
}
file.addEventListener('change', async () => {
  const selected = file.files?.[0]; file.value = '';
  if (!selected) return;
  const generation = operations.beginLoad();
  if (generation === null) return;
  playing = false; update();
  loadingControls(true);
  try {
    if (selected.size > 32 * 1024 * 1024) throw new Error('File exceeds 32 MiB. Export a shorter observation recording.');
    const parsed = await parseAnyRecording(await selected.text());
    if (!operations.isCurrentLoad(generation)) return;
    recording = parsed; tick = 0;
    delete traceBases.kc; delete traceBases.mbon11;
    stage?.setRecording(parsed);
    errorElement.hidden = true;
    if (stageError) showError(stageError);
    element('recording-name').textContent = selected.name;
    element('status').textContent = 'Recorded simulation'; element('status').classList.add('loaded');
    seek.max = String(parsed.duration_ticks); seek.disabled = false; play.disabled = false; speed.disabled = false; sourceButton.disabled = false;
    videoButton.disabled = !videoCodec || !stage;
    element('timeline-end').textContent = `${(parsed.duration_ticks / 10000).toFixed(1)} s`;
    const segments = element('segments'); segments.replaceChildren();
    if (isEventRecording(parsed)) {
      const item = document.createElement('span'); item.className = 'stimulus-event'; item.style.flexGrow = '1'; item.textContent = 'Paired options · 1.5 s settling + 0.5 s decision'; segments.append(item);
    } else if (isVideoRecording(parsed)) {
      for (const block of videoTimelineBlocks(parsed)) {
        const item = document.createElement('span'); item.className = `stimulus-video-${Number(block.clipId.slice(5)) % 2}`;
        item.style.flexGrow = String(block.duration); item.textContent = `Clip ${Number(block.clipId.slice(5)) + 1}`; segments.append(item);
      }
    } else for (const segment of parsed.segments) {
      const item = document.createElement('span'); item.className = `stimulus-${segment.stimulus}`;
      item.style.flexGrow = String(segment.playback_end_tick - segment.playback_start_tick);
      item.textContent = segment.stimulus === 'black' ? '' : segment.stimulus; segments.append(item);
    }
    element('source-mode').textContent = parsed.source.verification_mode;
    element('source-json').textContent = JSON.stringify(parsed.source, null, 2);
    if (videoCodec) videoNote.textContent = `Video export: 900×900, 30 timestamped frames/s. Last ${holdSeconds(parsed)} s holds the measured terminal sample${isEventRecording(parsed) ? ' and locked plan' : ''} for presentation.`;
    update(); stage?.render();
  } catch (error) {
    if (operations.isCurrentLoad(generation)) showError(`Cannot open recording. ${error instanceof Error ? error.message : 'Invalid file.'} Choose the JSON produced by export-replay.${recording ? ' The previous recording remains loaded.' : ''}`);
  } finally { if (operations.isCurrentLoad(generation)) { operations.endLoad(generation); loadingControls(false); } }
});

sourceButton.addEventListener('click', () => {
  const panel = element('source-panel'); panel.hidden = !panel.hidden;
  sourceButton.setAttribute('aria-expanded', String(!panel.hidden));
});
planButton.addEventListener('click', () => {
  if (!recording || !isEventRecording(recording) || operations.loading || operations.exporting) return;
  const json = eventPlanJson(sampleEventAtTick(recording, tick), operations);
  if (!json) return;
  const url = URL.createObjectURL(new Blob([json], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = 'event-plan.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
});
play.addEventListener('click', () => {
  if (!recording) return;
  if (tick >= recording.duration_ticks) tick = 0;
  playing = !playing; lastTime = performance.now(); update();
});
seek.addEventListener('input', () => { tick = Number(seek.value); update(); });
speed.addEventListener('change', () => { lastTime = performance.now(); });
canvas.addEventListener('keydown', (event) => {
  if (!recording || exportController) return;
  if (event.code === 'Space') { event.preventDefault(); play.click(); }
  if (event.code === 'ArrowLeft' || event.code === 'ArrowRight') {
    event.preventDefault(); tick = Math.max(0, Math.min(recording.duration_ticks, tick + (event.code === 'ArrowLeft' ? -1000 : 1000))); update();
  }
});

function exportControls(exporting: boolean) {
  openButton.disabled = exporting; file.disabled = exporting; play.disabled = exporting; seek.disabled = exporting; speed.disabled = exporting;
  videoButton.textContent = exporting ? 'Cancel export' : 'Export video';
  videoButton.disabled = !exporting && (!recording || !videoCodec || !stage);
  planButton.disabled = exporting || !recording || !isEventRecording(recording) || tick < recording.decision.effective_tick;
}

videoButton.addEventListener('click', async () => {
  if (exportController) { exportController.abort(); return; }
  if (!recording || !videoCodec || !stage || !operations.beginExport()) return;
  const sourceRecording = recording, sourceStage = stage;
  const previousTick = tick, wasPlaying = playing;
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
      paint: (frame) => { sourceStage.setSample(sampleAt(sourceRecording, frame.tick)); sourceStage.render(frame.terminalHold); },
      add: (timestamp, duration) => source.add(timestamp, duration),
      finalize: async () => { await output!.finalize(); return target.buffer; },
      cancel: () => output!.cancel(),
    }, controller.signal, (done, total) => { videoNote.textContent = `Encoding ${done}/${total} frames…`; }, isVideoRecording(sourceRecording) ? quantizeVideoTick : undefined, isEventRecording(sourceRecording) ? EVENT_HOLD_FRAMES : undefined);
    if (!completed?.byteLength) throw new Error('Encoder produced an empty video.');
    const url = URL.createObjectURL(new Blob([completed], { type: 'video/webm' }));
    const link = document.createElement('a'); link.href = url; link.download = 'measured-replay.webm'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    videoNote.textContent = `Video exported. The final ${holdSeconds(sourceRecording)} s holds the measured terminal sample${isEventRecording(sourceRecording) ? ' and locked plan' : ''} for presentation; no simulation time is added.`;
  } catch (error) {
    if (output && output.state !== 'canceled' && output.state !== 'finalized') try { await output.cancel(); } catch { /* Preserve export error. */ }
    if (controller.signal.aborted) videoNote.textContent = 'Video export canceled. No video was saved.';
    else { showError(`Video export failed: ${error instanceof Error ? error.message : 'Unknown encoding error.'} No video was saved.`); videoNote.textContent = 'Video export failed. No video was saved.'; }
  } finally {
    tick = previousTick; playing = wasPlaying; lastTime = performance.now();
    sourceStage.setExporting(false); exportController = null; operations.endExport(); exportControls(false); update();
    if (pageHidden) sourceStage.dispose(); else sourceStage.render();
  }
});

function frame(time: number) {
  if (exportController) { lastTime = time; return; }
  if (recording) {
    const state = advancePlayback(tick, Math.max(0, time - lastTime), Number(speed.value), playing, recording.duration_ticks);
    tick = state.tick; playing = state.playing; update();
  }
  lastTime = time;
  stage?.render();
}
if (stage) stage.renderer.setAnimationLoop(frame);
else {
  const ctx = canvas.getContext('2d');
  if (ctx) { canvas.width = 900; canvas.height = 600; ctx.fillStyle = '#DFEAF2'; ctx.fillRect(0, 0, 900, 600); ctx.fillStyle = '#172B3A'; ctx.font = '24px Bahnschrift, sans-serif'; ctx.fillText('3D rendering unavailable', 45, 285); ctx.font = '16px Bahnschrift, sans-serif'; ctx.fillText('Enable WebGL to see the illustrative fly. Recorded telemetry is available beside the stage.', 45, 320); }
  const fallbackFrame = (time: number) => { frame(time); requestAnimationFrame(fallbackFrame); }; requestAnimationFrame(fallbackFrame);
}
window.addEventListener('pagehide', () => { pageHidden = true; exportController?.abort(); if (!exportController) stage?.dispose(); });
