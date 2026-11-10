import { groups } from './native-protocol.ts';
import type { NativeSnapshot, NativeIntakeState } from './native-protocol.ts';

export type NativeState = { snapshot: NativeSnapshot | null; receivedAtMs: number | null; generation: number; disconnected: boolean };
export function createNativeState(): NativeState { return { snapshot: null, receivedAtMs: null, generation: 0, disconnected: false }; }
export function disconnectNative(value: NativeState): NativeState { return { ...value, disconnected: true, generation: value.generation + 1 }; }
export function nativeFreshness(value: NativeState, now: number): { transport: boolean; measurement: boolean; ageMs: number | null; live: boolean } {
  const elapsed = value.receivedAtMs === null ? null : now - value.receivedAtMs;
  const transport = !value.disconnected && elapsed !== null && Number.isFinite(elapsed) && elapsed >= 0 && elapsed < 5000;
  const ageMs = value.snapshot?.measurement_age_ms == null || elapsed === null || !Number.isFinite(elapsed) || elapsed < 0 ? null : value.snapshot.measurement_age_ms + elapsed;
  const measurement = ageMs !== null && ageMs < 10000;
  return { transport, measurement, ageMs, live: transport && measurement && value.snapshot?.state === 'running' && !value.snapshot.time_uncertain };
}
export function adoptNativeState(value: NativeState, reply: NativeSnapshot, now: number, generation: number): NativeState {
  if (generation !== value.generation) return value;
  const old = value.snapshot, same = old !== null && old.incarnation === reply.incarnation && old.worker_session === reply.worker_session;
  if (same) {
    if (old.schema !== reply.schema || old.mode !== reply.mode || old.model_limit_ms !== reply.model_limit_ms) throw new Error('Modellprotokoll verändert');
    if ((old.state !== 'starting' && reply.state === 'starting') ||
      (['stopping', 'ended', 'faulted'].includes(old.state) && reply.state === 'running') ||
      (old.fault !== null && reply.fault !== old.fault)) throw new Error('Abgeschlossener Modelltest verändert');
    if (reply.observations_completed < old.observations_completed) throw new Error('Veraltete Messantwort');
    if (reply.observations_completed === old.observations_completed) {
      for (const field of ['model_ms', 'input_kind', 'image_id', 'frame_sha256'] as const)
        if (old[field] !== reply[field]) throw new Error('Widersprüchliche Messantwort');
      for (const field of ['group_spikes', 'group_rates_hz'] as const)
        if (groups.some(group => old[field]?.[group] !== reply[field]?.[group])) throw new Error('Widersprüchliche Messantwort');
      const age = nativeFreshness(value, now).ageMs;
      if (age !== null && reply.measurement_age_ms !== null) reply = { ...reply, measurement_age_ms: Math.max(age, reply.measurement_age_ms) };
    }
  }
  return { snapshot: reply, receivedAtMs: now, disconnected: false, generation: old && !same ? value.generation + 1 : value.generation };
}
export function nativeAllowsImages(value: NativeState, intake: NativeIntakeState, now: number): boolean {
  const native = value.snapshot;
  return nativeFreshness(value, now).transport && native?.state === 'running' && native.fault === null && !native.time_uncertain &&
    native.incarnation === intake.incarnation && (native.mode === 'live-pilot') === (intake.mode === 'live-pilot') && [intake.pending, intake.active].every(image => (!image?.worker_session || image.worker_session === native.worker_session) &&
      (image?.first_observation_index == null || image.first_observation_index + 8 <= native.model_limit_ms / 500));
}
