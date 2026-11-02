import { parseAnyRecording as parseObservationRecording, sampleVideoAtTick, isVideoRecording, type VideoRecording } from './video-replay.ts';
import { sampleAtTick, type Recording } from './replay.ts';
import { isEventRecording, parseEventRecording, sampleEventAtTick, type EventRecording } from './event-replay.ts';

export type AnyRecording = Recording | VideoRecording | EventRecording;
export async function parseAnyRecording(text: string): Promise<AnyRecording> {
  if (new TextEncoder().encode(text).length > 32 * 1024 * 1024) throw new Error('Recording exceeds 32 MiB.');
  const value: unknown = JSON.parse(text);
  return value !== null && typeof value === 'object' && 'version' in value && value.version === 'event-choice-replay/v1' ? parseEventRecording(text) : parseObservationRecording(text);
}
export function sampleAnyAtTick(recording: AnyRecording, tick: number) {
  return isEventRecording(recording) ? sampleEventAtTick(recording, tick) : isVideoRecording(recording) ? sampleVideoAtTick(recording, tick) : sampleAtTick(recording, tick);
}
