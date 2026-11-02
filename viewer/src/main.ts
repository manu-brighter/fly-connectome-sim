import './style.css';
import { GROUPS, MAX_FILE_BYTES, advancePlayback, parseRecording, sampleAtTick, type Recording } from './replay.ts';
import { createCaptureFinisher, createStage, wireCaptureEvents } from './stage.ts';

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
let recording: Recording | null = null;
let tick = 0, playing = false, lastTime = performance.now(), loadGeneration = 0;
let recorder: MediaRecorder | null = null;
let finishCapture: ReturnType<typeof createCaptureFinisher> | null = null;
let stage: ReturnType<typeof createStage> | null = null;
let stageError = '';
try { stage = createStage(canvas); }
catch { stageError = '3D rendering is unavailable. Enable WebGL and reload to view the fly or export video. Recorded telemetry remains available.'; }

const videoMime = typeof MediaRecorder !== 'undefined' && typeof canvas.captureStream === 'function'
  ? ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'].find((mime) => MediaRecorder.isTypeSupported(mime)) : undefined;
if (!videoMime) videoNote.textContent = 'Video export is unavailable in this browser. Use a browser with canvas capture and WebM MediaRecorder support.';

for (const name of ['pam11', 'ppl101', 'mbon07'] as const) {
  const row = document.createElement('p'), label = document.createElement('span'), value = document.createElement('b');
  label.textContent = name.toUpperCase(); value.id = `${name}-rate`; value.textContent = '—';
  row.append(label, value); element('additional-rates').append(row);
}

function showError(message: string) { errorElement.textContent = message; errorElement.hidden = false; }
if (stageError) showError(stageError);

function drawTrace(name: 'kc' | 'mbon11') {
  const trace = element<HTMLCanvasElement>(`${name}-trace`), ctx = trace.getContext('2d')!;
  trace.width = Math.max(1, trace.clientWidth * 2); trace.height = 64;
  ctx.clearRect(0, 0, trace.width, trace.height);
  ctx.strokeStyle = '#c9d9e5'; ctx.beginPath(); ctx.moveTo(0, 60); ctx.lineTo(trace.width, 60); ctx.stroke();
  if (!recording) return;
  const bins = recording.segments.flatMap((segment) => segment.bins.map((bin) => ({
    end: segment.playback_start_tick + bin.end_tick - segment.source_start_tick,
    duration: bin.duration_ticks,
    rate: bin.group_spikes[name] * 10000 / (recording!.groups[name] * bin.duration_ticks),
  })));
  const max = Math.max(1, ...bins.map((bin) => bin.rate));
  ctx.strokeStyle = name === 'mbon11' ? '#2456d6' : '#597083'; ctx.lineWidth = 2; ctx.beginPath();
  for (const [index, bin] of bins.entries()) {
    const x0 = (bin.end - bin.duration) / recording.duration_ticks * trace.width;
    const x1 = bin.end / recording.duration_ticks * trace.width;
    const y = 60 - bin.rate / max * 50;
    if (index === 0) ctx.moveTo(x0, y); else ctx.lineTo(x0, y);
    ctx.lineTo(x1, y);
  }
  ctx.stroke();
  ctx.strokeStyle = '#172b3a'; ctx.lineWidth = 1.5; ctx.beginPath();
  const x = tick / recording.duration_ticks * trace.width; ctx.moveTo(x, 0); ctx.lineTo(x, 64); ctx.stroke();
}

function update() {
  if (!recording) return;
  const sample = sampleAtTick(recording, tick);
  stage?.setSample(sample);
  element('stimulus').textContent = sample.segment.stimulus === 'black' ? 'Black' : sample.segment.stimulus;
  element('stimulation').textContent = sample.segment.stimulation === null ? 'None' : 'Present';
  element('learning').textContent = String(sample.segment.learning);
  for (const name of GROUPS) element(`${name}-rate`).textContent = sample.rates[name].toFixed(2);
  element('source-clock').textContent = `${(sample.sourceTick / 10000).toFixed(4)} s`;
  element('event-sequence').textContent = String(sample.segment.event_sequence);
  element('bin-note').textContent = `Hz / cell = integer spikes ÷ population ÷ ${(sample.bin.duration_ticks / 10).toFixed(1)} ms. Complete recorded-bin values; traces hold each bin without smoothing.`;
  element('time').textContent = `${(sample.tick / 10000).toFixed(3)} / ${(recording.duration_ticks / 10000).toFixed(3)} s`;
  seek.value = String(sample.tick); seek.setAttribute('aria-valuetext', `${(sample.tick / 10000).toFixed(3)} seconds, input ${sample.segment.stimulus}`);
  play.textContent = playing ? 'Pause' : 'Play'; play.setAttribute('aria-label', playing ? 'Pause recording' : 'Play recording');
  drawTrace('kc'); drawTrace('mbon11');
}

openButton.addEventListener('click', () => file.click());
file.addEventListener('change', async () => {
  const selected = file.files?.[0]; file.value = '';
  if (!selected) return;
  const generation = ++loadGeneration;
  playing = false; update();
  openButton.textContent = 'Opening…'; openButton.disabled = true;
  try {
    if (selected.size > MAX_FILE_BYTES) throw new Error('File exceeds 8 MiB. Export a shorter observation recording.');
    const parsed = await parseRecording(await selected.text());
    if (generation !== loadGeneration) return;
    recording = parsed; tick = 0;
    stage?.setRecording(parsed);
    errorElement.hidden = true;
    if (stageError) showError(stageError);
    element('recording-name').textContent = selected.name;
    element('status').textContent = 'Recorded simulation'; element('status').classList.add('loaded');
    seek.max = String(parsed.duration_ticks); seek.disabled = false; play.disabled = false; speed.disabled = false; sourceButton.disabled = false;
    videoButton.disabled = !videoMime || !stage;
    element('timeline-end').textContent = `${(parsed.duration_ticks / 10000).toFixed(1)} s`;
    const segments = element('segments'); segments.replaceChildren();
    for (const segment of parsed.segments) {
      const item = document.createElement('span'); item.className = `stimulus-${segment.stimulus}`;
      item.style.flexGrow = String(segment.playback_end_tick - segment.playback_start_tick);
      item.textContent = segment.stimulus === 'black' ? '' : segment.stimulus; segments.append(item);
    }
    element('source-mode').textContent = parsed.source.verification_mode;
    element('source-json').textContent = JSON.stringify(parsed.source, null, 2);
    update(); stage?.render();
  } catch (error) {
    showError(`Cannot open recording. ${error instanceof Error ? error.message : 'Invalid file.'} Choose the JSON produced by export-replay.${recording ? ' The previous recording remains loaded.' : ''}`);
  } finally { if (generation === loadGeneration) { openButton.disabled = false; openButton.textContent = 'Open recording'; } }
});

sourceButton.addEventListener('click', () => {
  const panel = element('source-panel'); panel.hidden = !panel.hidden;
  sourceButton.setAttribute('aria-expanded', String(!panel.hidden));
});
play.addEventListener('click', () => {
  if (!recording) return;
  if (tick >= recording.duration_ticks) tick = 0;
  playing = !playing; lastTime = performance.now(); update();
});
seek.addEventListener('input', () => { tick = Number(seek.value); update(); });
speed.addEventListener('change', () => { lastTime = performance.now(); });
canvas.addEventListener('keydown', (event) => {
  if (!recording || recorder) return;
  if (event.code === 'Space') { event.preventDefault(); play.click(); }
  if (event.code === 'ArrowLeft' || event.code === 'ArrowRight') {
    event.preventDefault(); tick = Math.max(0, Math.min(recording.duration_ticks, tick + (event.code === 'ArrowLeft' ? -1000 : 1000))); update();
  }
});

function captureControls(capturing: boolean) {
  openButton.disabled = capturing; file.disabled = capturing; play.disabled = capturing; seek.disabled = capturing; speed.disabled = capturing;
  videoButton.textContent = capturing ? 'Stop export' : 'Export video';
}

videoButton.addEventListener('click', () => {
  if (recorder) { if (recorder.state !== 'inactive') recorder.stop(); return; }
  if (!recording || !videoMime || !stage) return;
  const stream = canvas.captureStream(30);
  let markCaptureFailed: (() => void) | undefined;
  try {
    recorder = new MediaRecorder(stream, { mimeType: videoMime, videoBitsPerSecond: 5_000_000 });
    finishCapture = createCaptureFinisher(recorder);
    markCaptureFailed = wireCaptureEvents(recorder, () => {
      showError('Video recording failed in this browser. Replay data is unchanged.');
      videoNote.textContent = 'Video export failed. No video was saved.';
      stream.getTracks().forEach((track) => track.stop()); playing = false; update();
    }, () => {
      playing = false; recorder = null; finishCapture = null; stream.getTracks().forEach((track) => track.stop()); captureControls(false); update();
    }, (chunks) => {
      if (!chunks.length) { showError('The browser produced no video. Retry with a browser supporting canvas WebM capture.'); return; }
      const url = URL.createObjectURL(new Blob(chunks, { type: videoMime }));
      const link = document.createElement('a'); link.href = url; link.download = 'measured-replay.webm'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      videoNote.textContent = 'Video exported with measured telemetry. Presentation follows browser timing; frame precision and exact FPS are not guaranteed.';
    });
    tick = 0; speed.value = '1'; playing = true; update(); stage.render();
    recorder.start(200); lastTime = performance.now(); captureControls(true);
    videoNote.textContent = 'Recording the replay from the beginning at 1×. Keep this tab visible. Stop export saves the recorded portion.';
  } catch {
    markCaptureFailed?.();
    stream.getTracks().forEach((track) => track.stop()); recorder = null; finishCapture = null; playing = false; captureControls(false); update();
    showError('Cannot start video export. This browser could not capture the replay canvas.');
  }
});

function frame(time: number) {
  if (recording) {
    const state = advancePlayback(tick, Math.max(0, time - lastTime), Number(speed.value), playing, recording.duration_ticks);
    tick = state.tick; playing = state.playing; update();
  }
  lastTime = time;
  if (!playing && recorder?.state === 'recording' && finishCapture) finishCapture(() => stage?.render());
  else stage?.render();
}
if (stage) stage.renderer.setAnimationLoop(frame);
else {
  const ctx = canvas.getContext('2d');
  if (ctx) { canvas.width = 900; canvas.height = 600; ctx.fillStyle = '#DFEAF2'; ctx.fillRect(0, 0, 900, 600); ctx.fillStyle = '#172B3A'; ctx.font = '24px Bahnschrift, sans-serif'; ctx.fillText('3D rendering unavailable', 45, 285); ctx.font = '16px Bahnschrift, sans-serif'; ctx.fillText('Enable WebGL to see the illustrative fly. Recorded telemetry is available beside the stage.', 45, 320); }
  const fallbackFrame = (time: number) => { frame(time); requestAnimationFrame(fallbackFrame); }; requestAnimationFrame(fallbackFrame);
}
window.addEventListener('pagehide', () => { if (recorder?.state === 'recording') recorder.stop(); stage?.dispose(); });
