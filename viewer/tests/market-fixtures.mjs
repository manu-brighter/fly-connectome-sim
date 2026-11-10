export const uuid = '11111111-1111-4111-8111-111111111111';
export function snapshot(overrides = {}) {
  return { schema: 'market-snapshot-v1', incarnation: uuid, revision: 1, price_version: 0,
    config_id: 'a'.repeat(64), generation: 1, paused: true, fault: null, primary_state: 'unclaimed',
    server_utc: '2026-11-10T12:00:00Z', rows: Array.from({ length: 20 }, (_, index) => ({
      id: `drink-${String(index).padStart(2, '0')}`, name: `Testgetränk ${String(index + 1).padStart(2, '0')}`,
      minimum_rappen: 400, maximum_rappen: 700, grid_rappen: 50, initial_rappen: 400,
      current_rappen: 400, drink_version: 0, last_activation_id: null, recorded_utc: null,
      remaining_lock_ms: 0, estimated_eligible_utc: null, recovery_lock: false,
    })), challenge: null, ...overrides };
}
export function result(overrides = {}) {
  return { event_id: uuid, request_id: 'request-1', status: 'activated', reason: 'activated', activation_id: uuid,
    terminal_revision: 2, terminal_price_version: 1, drink_version: 1, current_rappen: 700, ...overrides };
}
