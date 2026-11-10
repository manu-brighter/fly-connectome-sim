import type { Snapshot } from './protocol.ts';

export type BoardState = {
  snapshot: Snapshot | null;
  connectionGeneration: number;
  receivedAtMs: number | null;
  unknown: boolean;
  primarySession: { session_id: string; primary_token: string } | null;
};
export function createState(): BoardState {
  return { snapshot: null, connectionGeneration: 0, receivedAtMs: null, unknown: true, primarySession: null };
}
export function disconnect(state: BoardState): BoardState {
  return { ...state, connectionGeneration: state.connectionGeneration + 1, unknown: true };
}
export function applySnapshot(state: BoardState, snapshot: Snapshot, receivedAtMs: number, connectionGeneration: number): BoardState {
  if (connectionGeneration !== state.connectionGeneration || !Number.isFinite(receivedAtMs)) return state;
  const changedIncarnation = state.snapshot !== null && state.snapshot.incarnation !== snapshot.incarnation;
  if (!changedIncarnation && state.snapshot !== null &&
    (snapshot.revision < state.snapshot.revision || snapshot.schema !== state.snapshot.schema)) return state;
  return {
    snapshot, receivedAtMs, unknown: false,
    connectionGeneration: state.connectionGeneration + (changedIncarnation ? 1 : 0),
    primarySession: changedIncarnation ? null : state.primarySession,
  };
}
export function isFresh(state: BoardState, nowMs: number): boolean {
  return !state.unknown && state.snapshot !== null && state.receivedAtMs !== null &&
    nowMs >= state.receivedAtMs && nowMs - state.receivedAtMs < 5000;
}
