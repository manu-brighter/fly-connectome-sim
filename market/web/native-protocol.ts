import type { ImageStatus, IntakeState } from './image-protocol.ts';

export const groups = ['pam11', 'ppl101', 'kc', 'mbon07', 'mbon11', 'motor_left', 'motor_right'] as const;
const populations = [15, 2, 4064, 4, 2, 1, 1];
const faults = ['startup', 'source', 'clock', 'protocol', 'deadline', 'resource', 'ownership',
  'storage', 'journal_gap', 'worker_failed', 'worker_outcome_unknown', 'cleanup_failed'] as const;
export type NativeFault = typeof faults[number];
export type NativePhase = 'starting' | 'running' | 'stopping' | 'ended' | 'faulted';
export type GroupValues = Record<typeof groups[number], number>;
export type ImageStatusV2 = Omit<ImageStatus, 'schema' | 'status'> & {
  schema: 'market-image-status-wire/v2'; status: ImageStatus['status'] | 'processing' | 'processed';
  worker_session: string | null; first_observation_index: number | null;
  completed_observations: number; observation_revision: number;
};
export type ImageStatusV3 = Omit<ImageStatusV2, 'schema'> & { schema: 'market-image-status-wire/v3' };
export type NativeImageStatus = ImageStatusV2 | ImageStatusV3;
export type IntakeStateV2 = Omit<IntakeState, 'schema' | 'mode' | 'worker_connected' | 'fault' | 'pending'> & {
  schema: 'market-image-intake/v2'; mode: 'bounded-native-test'; worker_connected: boolean;
  fault: IntakeState['fault'] | 'native_worker'; pending: ImageStatusV2 | null;
  active: ImageStatusV2 | null; native_state: NativePhase;
};
export type IntakeStateV3 = Omit<IntakeStateV2, 'schema' | 'mode' | 'pending' | 'active'> & {
  schema: 'market-image-intake/v3'; mode: 'live-pilot'; pending: ImageStatusV3 | null; active: ImageStatusV3 | null;
};
export type NativeIntakeState = IntakeStateV2 | IntakeStateV3;
type NativeMeasurement = {
  incarnation: string; worker_session: string;
  state: NativePhase; fault: NativeFault | null; model_ms: number; model_limit_ms: number;
  observations_completed: number; measurement_age_ms: number | null; time_uncertain: boolean;
  input_kind: 'black' | 'image' | null; image_id: string | null; frame_sha256: string | null;
  group_spikes: GroupValues | null; group_rates_hz: GroupValues | null;
};
export type NativeSnapshot = NativeMeasurement & ({ schema: 'market-native-state/v1'; mode: 'bounded-native-test' } |
  { schema: 'market-native-state/v2'; mode: 'live-pilot'; profile: 'live-pilot/v1' });
function require(condition: unknown): asserts condition { if (!condition) throw new Error('Ungültige Serverantwort'); }
function object(value: unknown, keys: string): Record<string, unknown> {
  require(value !== null && typeof value === 'object' && !Array.isArray(value));
  const record = value as Record<string, unknown>, expected = keys.split(' ');
  require(Object.keys(record).length === expected.length && expected.every(key => Object.hasOwn(record, key)));
  return record;
}
function integer(value: unknown, low = 0, high = Number.MAX_SAFE_INTEGER): asserts value is number {
  require(typeof value === 'number' && Number.isSafeInteger(value) && value >= low && value <= high);
}
function uuid(value: unknown): asserts value is string { require(typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value)); }
function digest(value: unknown): void { require(typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)); }
function boolean(value: unknown): void { require(typeof value === 'boolean'); }
function oneOf(value: unknown, choices: readonly unknown[]): void { require(choices.includes(value)); }
function phase(value: unknown): void { oneOf(value, ['starting', 'running', 'stopping', 'ended', 'faulted']); }

export function parseImageStatusV2(value: unknown): ImageStatusV2 { return parseNativeImageStatus(value, false) as ImageStatusV2; }
export function parseImageStatusV3(value: unknown): ImageStatusV3 { return parseNativeImageStatus(value, true) as ImageStatusV3; }
function parseNativeImageStatus(value: unknown, live: boolean): NativeImageStatus {
  const s = object(value, 'schema incarnation id revision status detail frame_sha256 accepted_age_ms remaining_decode_ms remaining_moderation_ms remaining_handoff_ms time_uncertain preview_available worker_session first_observation_index completed_observations observation_revision');
  require(s.schema === (live ? 'market-image-status-wire/v3' : 'market-image-status-wire/v2')); uuid(s.incarnation); uuid(s.id); integer(s.revision, 1, 6);
  boolean(s.time_uncertain); boolean(s.preview_available);
  if (s.frame_sha256 !== null) digest(s.frame_sha256);
  if (s.worker_session !== null) uuid(s.worker_session);
  if (s.first_observation_index !== null) integer(s.first_observation_index, 0, live ? 86392 : 32);
  integer(s.completed_observations, 0, 8); integer(s.observation_revision, 0, live ? 86400 : 40);
  require(s.completed_observations === 0 ? s.observation_revision === 0 :
    s.first_observation_index !== null && s.observation_revision === (s.first_observation_index as number) + s.completed_observations);
  require(s.first_observation_index === null || (s.worker_session !== null && s.frame_sha256 !== null));
  require(s.worker_session === null || s.frame_sha256 !== null);
  const variants: Record<string, readonly string[]> = {
    accepted: ['decoding', 'awaiting_approval'], queued: ['ready', 'dispatching'], processing: ['processing'],
    processed: ['completed'], expired: ['ttl_expired'], rejected: ['decode_failed', 'decode_timeout',
      'moderation_rejected', 'moderation_timeout', 'worker_failed', 'worker_outcome_unknown', 'session_ended', 'clock'],
  };
  require(typeof s.status === 'string' && Object.hasOwn(variants, s.status) && typeof s.detail === 'string' && variants[s.status].includes(s.detail));
  const retained = s.status === 'rejected' && ['worker_failed', 'worker_outcome_unknown', 'session_ended', 'clock'].includes(s.detail);
  if (!retained) {
    const noHash = s.detail === 'decoding' || s.detail === 'decode_failed' || s.detail === 'decode_timeout';
    require(noHash === (s.frame_sha256 === null));
    const dispatched = ['dispatching', 'processing', 'completed'].includes(s.detail);
    require(dispatched === (s.worker_session !== null));
    const started = s.status === 'processing' || s.status === 'processed';
    require(started === (s.first_observation_index !== null));
    if (!started) require(s.completed_observations === 0);
  }
  require(s.preview_available === (s.detail === 'awaiting_approval' || (s.status === 'queued' && s.detail === 'ready')));
  if (s.status === 'processed') require(s.completed_observations === 8);
  for (const field of ['accepted_age_ms', 'remaining_decode_ms', 'remaining_moderation_ms', 'remaining_handoff_ms']) {
    if (s.time_uncertain) require(s[field] === null); else integer(s[field]);
  }
  if (['rejected', 'expired', 'processed'].includes(s.status))
    for (const field of ['remaining_decode_ms', 'remaining_moderation_ms', 'remaining_handoff_ms']) require(s.time_uncertain || s[field] === 0);
  if (s.status === 'processing') require(s.time_uncertain || s.remaining_handoff_ms === 0);
  return value as NativeImageStatus;
}

export function parseIntakeStateV2(value: unknown): IntakeStateV2 { return parseNativeIntake(value, false) as IntakeStateV2; }
export function parseIntakeStateV3(value: unknown): IntakeStateV3 { return parseNativeIntake(value, true) as IntakeStateV3; }
function parseNativeIntake(value: unknown, live: boolean): NativeIntakeState {
  const s = object(value, 'schema incarnation mode worker_connected health fault receiving decode_busy pending receipt_count active native_state');
  require(s.schema === (live ? 'market-image-intake/v3' : 'market-image-intake/v2') && s.mode === (live ? 'live-pilot' : 'bounded-native-test')); uuid(s.incarnation); phase(s.native_state);
  oneOf(s.health, ['ready', 'stopping', 'faulted']); oneOf(s.fault, [null, 'clock', 'decoder', 'ownership', 'shutdown', 'native_worker']);
  boolean(s.worker_connected); boolean(s.receiving); boolean(s.decode_busy); integer(s.receipt_count, 0, 512);
  for (const field of ['pending', 'active']) if (s[field] !== null) {
    const image = parseNativeImageStatus(s[field], live); require(image.incarnation === s.incarnation);
    require(field === 'pending' ? ['accepted', 'queued'].includes(image.status) : image.status === 'processing');
  }
  const pending = s.pending as NativeImageStatus | null, active = s.active as NativeImageStatus | null;
  if (pending && active) {
    require(pending.id !== active.id);
    if (pending.worker_session !== null) require(pending.worker_session === active.worker_session);
  }
  require(!(s.receiving && pending));
  if (s.native_state === 'running') require(s.health === 'ready' && s.fault === null && s.worker_connected === true);
  else {
    require(s.worker_connected === false && s.receiving === false && pending === null && active === null);
    if (s.native_state === 'faulted') require(s.health === 'faulted' && s.fault !== null);
    else require(s.health === 'stopping');
    if (s.native_state === 'starting' || s.native_state === 'ended') require(s.fault === null);
  }
  return value as NativeIntakeState;
}

export function parseNativeState(value: unknown): NativeSnapshot {
  const live = (value as { schema?: unknown } | null)?.schema === 'market-native-state/v2';
  const s = object(value, 'schema incarnation worker_session mode state fault model_ms model_limit_ms observations_completed measurement_age_ms input_kind image_id frame_sha256 group_spikes group_rates_hz time_uncertain' + (live ? ' profile' : ''));
  require(s.schema === (live ? 'market-native-state/v2' : 'market-native-state/v1') && s.mode === (live ? 'live-pilot' : 'bounded-native-test'));
  if (live) { require(s.profile === 'live-pilot/v1'); integer(s.model_limit_ms, 500, 43200000); require(s.model_limit_ms % 500 === 0); }
  else require(s.model_limit_ms === 20000);
  uuid(s.incarnation); uuid(s.worker_session); phase(s.state); oneOf(s.fault, [null, ...faults]); boolean(s.time_uncertain);
  // A later clock failure cannot overwrite a different retained first fault.
  require(s.fault !== 'clock' || s.time_uncertain);
  require(!s.time_uncertain || s.fault !== null);
  integer(s.observations_completed, 0, (s.model_limit_ms as number) / 500); require(s.model_ms === s.observations_completed * 500);
  if (s.state === 'faulted') require(s.fault !== null);
  if (['starting', 'running', 'ended'].includes(s.state as string)) require(s.fault === null);
  if (s.state === 'starting') require(s.observations_completed === 0);
  if (s.state === 'ended' && !live) require(s.observations_completed === 40);
  if (s.observations_completed === 0) {
    for (const field of ['input_kind', 'image_id', 'frame_sha256', 'group_spikes', 'group_rates_hz', 'measurement_age_ms']) require(s[field] === null);
  } else {
    oneOf(s.input_kind, ['black', 'image']); digest(s.frame_sha256);
    if (s.input_kind === 'black') require(s.image_id === null); else uuid(s.image_id);
    if (s.time_uncertain) require(s.measurement_age_ms === null); else integer(s.measurement_age_ms);
    const counts = object(s.group_spikes, groups.join(' ')), rates = object(s.group_rates_hz, groups.join(' '));
    groups.forEach((group, index) => {
      integer(counts[group], 0, populations[index] * 5000);
      const rate = rates[group], expected = counts[group] / (populations[index] * .5);
      require(typeof rate === 'number' && Number.isFinite(rate) && rate >= 0 && rate <= 10000 && Math.abs(rate - expected) <= 1e-9);
    });
  }
  return value as NativeSnapshot;
}
