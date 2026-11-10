// Deterministic HTTP fixtures only; these values are not native measurements.
import { status, intake, incarnation, id, hash } from './image-fixtures.mjs';
export const session = '33333333-3333-4333-8333-333333333333';
export const groups = ['pam11', 'ppl101', 'kc', 'mbon07', 'mbon11', 'motor_left', 'motor_right'];
export const populations = [15, 2, 4064, 4, 2, 1, 1];
export function imageV2(changes = {}) {
  return status({ schema: 'market-image-status-wire/v2', worker_session: null, first_observation_index: null,
    completed_observations: 0, observation_revision: 0, ...changes });
}
export function intakeV2(changes = {}) {
  return intake({ schema: 'market-image-intake/v2', mode: 'bounded-native-test', worker_connected: true,
    native_state: 'running', active: null, pending: imageV2(), ...changes });
}
export function native(changes = {}) {
  return { schema: 'market-native-state/v1', incarnation, worker_session: session, mode: 'bounded-native-test',
    state: 'running', fault: null, model_ms: 500, model_limit_ms: 20000, observations_completed: 1,
    measurement_age_ms: 1000, input_kind: 'image', image_id: id, frame_sha256: hash,
    group_spikes: Object.fromEntries(groups.map(group => [group, 1])),
    group_rates_hz: Object.fromEntries(groups.map((group, index) => [group, 2 / populations[index]])),
    time_uncertain: false, ...changes };
}
