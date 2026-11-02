export const EXPORT_SIZE = 900;
export const EXPORT_FPS = 30;
export const TERMINAL_HOLD_FRAMES = 15;

export function frameCount(durationTicks: number) {
  return Math.ceil(durationTicks * EXPORT_FPS / 10000) + TERMINAL_HOLD_FRAMES;
}

export function frameAt(index: number, durationTicks: number) {
  const sourceFrames = Math.ceil(durationTicks * EXPORT_FPS / 10000);
  if (!Number.isSafeInteger(index) || index < 0 || index >= sourceFrames + TERMINAL_HOLD_FRAMES) throw new RangeError('Frame index is outside the export.');
  const terminalHold = index >= sourceFrames;
  return {
    index,
    tick: terminalHold ? durationTicks : Math.floor(index * 10000 / EXPORT_FPS),
    timestamp: index / EXPORT_FPS,
    duration: 1 / EXPORT_FPS,
    terminalHold,
  };
}

type Frame = ReturnType<typeof frameAt>;
type Writer<T> = {
  paint: (frame: Frame) => void | Promise<void>;
  add: (timestamp: number, duration: number) => Promise<void>;
  finalize: () => Promise<T>;
  cancel: () => Promise<void>;
};

export async function writeFrames<T>(durationTicks: number, writer: Writer<T>, signal?: AbortSignal, onProgress?: (done: number, total: number) => void): Promise<T> {
  const total = frameCount(durationTicks);
  try {
    for (let index = 0; index < total; index += 1) {
      signal?.throwIfAborted();
      const frame = frameAt(index, durationTicks);
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
