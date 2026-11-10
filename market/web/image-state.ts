import type { ImageStatus, IntakeState } from './image-protocol.ts';
export type Painted = { incarnation: string; id: string; frame_sha256: string };
export type ImageState = { state: IntakeState | null; receivedAtMs: number | null; generation: number;
  painted: Painted | null; disconnected: boolean; pendingMutation: boolean };
export function createImageState(): ImageState {
  return { state: null, receivedAtMs: null, generation: 0, painted: null, disconnected: false, pendingMutation: false };
}
export function currentPending(value: ImageState): ImageStatus | null { return value.state?.pending ?? null; }
export function identity(status: ImageStatus): Painted | null {
  return status.frame_sha256 === null ? null : { incarnation: status.incarnation, id: status.id, frame_sha256: status.frame_sha256 };
}
export function sameTuple(left: Painted | null, right: Painted | null): boolean {
  return !!left && !!right && left.incarnation === right.incarnation && left.id === right.id && left.frame_sha256 === right.frame_sha256;
}
export function adoptOperatorState(value: ImageState, reply: IntakeState, now: number, generation: number): ImageState {
  if (generation !== value.generation) return value;
  const old = currentPending(value), fresh = reply.pending;
  const preserve = old && fresh && sameTuple(identity(old), identity(fresh)) && fresh.status === 'accepted' && fresh.detail === 'awaiting_approval';
  return { ...value, state: reply, receivedAtMs: now, disconnected: false, painted: preserve ? value.painted : null,
    generation: reply.incarnation === value.state?.incarnation || value.state === null ? value.generation : value.generation + 1 };
}
export function adoptPaintedPreview(value: ImageState, tuple: Painted, generation: number): ImageState {
  const pending = currentPending(value);
  if (generation !== value.generation || !pending || !sameTuple(identity(pending), tuple) ||
    pending.status !== 'accepted' || pending.detail !== 'awaiting_approval' || !pending.preview_available || value.disconnected) return value;
  return { ...value, painted: tuple };
}
export function invalidatePreview(value: ImageState): ImageState { return { ...value, painted: null }; }
export function disconnectImage(value: ImageState): ImageState {
  return { ...value, disconnected: true, painted: null, generation: value.generation + 1 };
}
export function moderationGates(value: ImageState, now: number): { approve: boolean; reject: boolean } {
  const pending = currentPending(value), ready = value.state?.health === 'ready' && value.state.fault === null &&
    !value.disconnected && !value.pendingMutation && value.receivedAtMs !== null && now >= value.receivedAtMs && now - value.receivedAtMs < 5000 &&
    pending?.status === 'accepted' && pending.detail === 'awaiting_approval';
  return { approve: !!ready && !!pending?.preview_available && sameTuple(value.painted, pending ? identity(pending) : null), reject: !!ready };
}
