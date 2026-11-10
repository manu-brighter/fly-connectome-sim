import type { AnyImageStatus as ImageStatus, AnyIntakeState as IntakeState } from './image-protocol.ts';
export type Painted = { incarnation: string; id: string; frame_sha256: string };
export type ImageState = { state: IntakeState | null; receivedAtMs: number | null; generation: number;
  painted: Painted | null; disconnected: boolean; pendingMutation: boolean; receipts: Map<string, ImageStatus> };
export function createImageState(): ImageState {
  return { state: null, receivedAtMs: null, generation: 0, painted: null, disconnected: false, pendingMutation: false, receipts: new Map() };
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
  const changed = value.state !== null && reply.incarnation !== value.state.incarnation;
  if (value.state !== null && !changed && value.state.schema !== reply.schema) throw new Error('Bildprotokoll verändert');
  let next = changed ? { ...value, receipts: new Map<string, ImageStatus>() } : value;
  for (const image of [reply.pending, ...('active' in reply ? [reply.active] : [])]) if (image) next = adoptImageReceipt(next, image);
  const old = currentPending(value), fresh = reply.pending;
  const preserve = old && fresh && sameTuple(identity(old), identity(fresh)) && fresh.status === 'accepted' && fresh.detail === 'awaiting_approval';
  return { ...next, state: reply, receivedAtMs: now, disconnected: false, painted: preserve ? value.painted : null,
    generation: reply.incarnation === value.state?.incarnation || value.state === null ? value.generation : value.generation + 1 };
}
export function validateImageProgress(old: ImageStatus, next: ImageStatus): void {
  if (old.incarnation !== next.incarnation || old.id !== next.id) throw new Error('Falsche Bildidentität');
  if (old.schema === 'market-image-status-wire/v1') return;
  if (next.schema !== old.schema || next.revision < old.revision || next.completed_observations < old.completed_observations ||
    (old.frame_sha256 !== null && next.frame_sha256 !== old.frame_sha256) ||
    (old.worker_session !== null && next.worker_session !== old.worker_session) ||
    (old.first_observation_index !== null && next.first_observation_index !== old.first_observation_index)) throw new Error('Widersprüchlicher Bildstatus');
  if (['processed', 'rejected', 'expired'].includes(old.status) &&
    ['status', 'detail', 'revision', 'worker_session', 'first_observation_index', 'completed_observations', 'observation_revision'].some(
      key => old[key as keyof typeof old] !== next[key as keyof typeof next])) throw new Error('Abgeschlossener Bildstatus verändert');
}
export function adoptImageReceipt(value: ImageState, reply: ImageStatus): ImageState {
  const key = `${reply.incarnation}:${reply.id}`, old = value.receipts.get(key);
  if (old) validateImageProgress(old, reply);
  const receipts = new Map(value.receipts); receipts.set(key, reply);
  if (receipts.size > 512) receipts.delete(receipts.keys().next().value!);
  return { ...value, receipts };
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
