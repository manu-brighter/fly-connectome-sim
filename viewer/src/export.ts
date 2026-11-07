export const EXPORT_SIZE = 900;
export const EXPORT_FPS = 30;
export const TERMINAL_HOLD_FRAMES = 15;

// Presentation time can advance beyond the immutable last recorded sample.
export function advancePresentationPlayback(presentationTick: number, elapsedMs: number, speed: number, playing: boolean, durationTicks: number, holdTicks: number) {
  const next = Math.max(0, Math.min(durationTicks + holdTicks, presentationTick + (playing ? elapsedMs * 10 * speed : 0)));
  return {
    tick: Math.min(durationTicks, next),
    holdElapsedTicks: Math.max(0, next - durationTicks),
    terminalHold: holdTicks > 0 && next >= durationTicks,
    playing: playing && next < durationTicks + holdTicks,
  };
}

export function quantizeVideoTick(index: number) {
  if (!Number.isSafeInteger(index) || index < 0) throw new RangeError('Invalid video frame index.');
  return Math.floor((index * 10000 + 15) / EXPORT_FPS);
}

export function frameCount(durationTicks: number, terminalHoldFrames = TERMINAL_HOLD_FRAMES) {
  if (!Number.isSafeInteger(durationTicks) || durationTicks <= 0 || !Number.isSafeInteger(terminalHoldFrames) || terminalHoldFrames < 1 || terminalHoldFrames > 90) throw new RangeError('Invalid export duration or presentation hold.');
  return Math.ceil(durationTicks * EXPORT_FPS / 10000) + terminalHoldFrames;
}

export function frameAt(index: number, durationTicks: number, sourceTickForFrame: (index: number) => number = (frame) => Math.floor(frame * 10000 / EXPORT_FPS), terminalHoldFrames = TERMINAL_HOLD_FRAMES) {
  const sourceFrames = Math.ceil(durationTicks * EXPORT_FPS / 10000);
  if (!Number.isSafeInteger(index) || index < 0 || index >= frameCount(durationTicks, terminalHoldFrames)) throw new RangeError('Frame index is outside the export.');
  const terminalHold = index >= sourceFrames;
  return {
    index,
    tick: terminalHold ? durationTicks : sourceTickForFrame(index),
    timestamp: index / EXPORT_FPS,
    duration: 1 / EXPORT_FPS,
    terminalHold,
    holdElapsedTicks: terminalHold ? Math.round((index - sourceFrames) * 10000 / EXPORT_FPS) : 0,
  };
}

type Frame = ReturnType<typeof frameAt>;
type Writer<T> = {
  paint: (frame: Frame) => void | Promise<void>;
  add: (timestamp: number, duration: number) => Promise<void>;
  finalize: () => Promise<T>;
  cancel: () => Promise<void>;
};

export async function writeFrames<T>(durationTicks: number, writer: Writer<T>, signal?: AbortSignal, onProgress?: (done: number, total: number) => void, sourceTickForFrame?: (index: number) => number, terminalHoldFrames = TERMINAL_HOLD_FRAMES): Promise<T> {
  const total = frameCount(durationTicks, terminalHoldFrames);
  try {
    for (let index = 0; index < total; index += 1) {
      signal?.throwIfAborted();
      const frame = frameAt(index, durationTicks, sourceTickForFrame, terminalHoldFrames);
      await writer.paint(frame);
      signal?.throwIfAborted();
      await writer.add(frame.timestamp, frame.duration);
      signal?.throwIfAborted();
      onProgress?.(index + 1, total);
    }
    signal?.throwIfAborted();
    const result = await writer.finalize();
    signal?.throwIfAborted();
    return result;
  } catch (error) {
    try { await writer.cancel(); } catch { /* Preserve the original failure. */ }
    throw error;
  }
}
