export const incarnation = '11111111-1111-4111-8111-111111111111';
export const id = '22222222-2222-4222-8222-222222222222';
export const hash = 'a'.repeat(64);
export const receipt = `is.${'A'.repeat(43)}`;
export function status(changes = {}) {
  return { schema: 'market-image-status-wire/v1', incarnation, id, revision: 2,
    status: 'accepted', detail: 'awaiting_approval', frame_sha256: hash,
    accepted_age_ms: 1000, remaining_decode_ms: 0, remaining_moderation_ms: 59000,
    remaining_handoff_ms: 299000, time_uncertain: false, preview_available: true, ...changes };
}
export function intake(changes = {}) {
  return { schema: 'market-image-intake/v1', incarnation, mode: 'local-intake-only', worker_connected: false,
    health: 'ready', fault: null, receiving: false, decode_busy: false, pending: status(), receipt_count: 1, ...changes };
}
