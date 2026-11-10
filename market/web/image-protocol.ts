export type ImageStatus = {
  schema: 'market-image-status-wire/v1'; incarnation: string; id: string; revision: number;
  status: 'accepted' | 'queued' | 'rejected' | 'expired'; detail: string; frame_sha256: string | null;
  accepted_age_ms: number | null; remaining_decode_ms: number | null; remaining_moderation_ms: number | null;
  remaining_handoff_ms: number | null; time_uncertain: boolean; preview_available: boolean;
};
export type IntakeState = {
  schema: 'market-image-intake/v1'; incarnation: string; mode: 'local-intake-only'; worker_connected: false;
  health: 'ready' | 'stopping' | 'faulted'; fault: null | 'clock' | 'decoder' | 'ownership' | 'shutdown';
  receiving: boolean; decode_busy: boolean; pending: ImageStatus | null; receipt_count: number;
};
export type Acceptance = { schema: 'market-image-acceptance/v1'; status_capability: string; image: ImageStatus };
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const digestPattern = /^[0-9a-f]{64}$/;
const receiptPattern = /^is\.[A-Za-z0-9_-]{43}$/;
const bound = 9223372036855;
function require(condition: unknown): asserts condition { if (!condition) throw new Error('Ungültige Serverantwort'); }
function object(value: unknown, keys: string): Record<string, unknown> {
  require(value !== null && typeof value === 'object' && !Array.isArray(value));
  const record = value as Record<string, unknown>, expected = keys.split(' ');
  require(Object.keys(record).length === expected.length && expected.every(key => Object.hasOwn(record, key)));
  return record;
}
function integer(value: unknown, low = 0, high = bound): asserts value is number {
  require(typeof value === 'number' && Number.isSafeInteger(value) && value >= low && value <= high);
}
function uuid(value: unknown): asserts value is string { require(typeof value === 'string' && uuidPattern.test(value)); }
function oneOf(value: unknown, options: readonly unknown[]): void { require(options.includes(value)); }
function boolean(value: unknown): asserts value is boolean { require(typeof value === 'boolean'); }
export function parseImageStatus(value: unknown): ImageStatus {
  const s = object(value, 'schema incarnation id revision status detail frame_sha256 accepted_age_ms remaining_decode_ms remaining_moderation_ms remaining_handoff_ms time_uncertain preview_available');
  require(s.schema === 'market-image-status-wire/v1'); uuid(s.incarnation); uuid(s.id); integer(s.revision, 1, 6);
  oneOf(s.status, ['accepted', 'queued', 'rejected', 'expired']);
  boolean(s.preview_available); boolean(s.time_uncertain);
  if (s.frame_sha256 !== null) require(typeof s.frame_sha256 === 'string' && digestPattern.test(s.frame_sha256));
  const combinations: Record<string, Record<string, 'null' | 'hash' | 'either'>> = {
    accepted: { decoding: 'null', awaiting_approval: 'hash' }, queued: { ready: 'hash' },
    expired: { ttl_expired: 'hash' }, rejected: { decode_failed: 'null', decode_timeout: 'null',
      moderation_rejected: 'hash', moderation_timeout: 'hash', worker_failed: 'either', session_ended: 'either', clock: 'either' },
  };
  require(typeof s.status === 'string' && typeof s.detail === 'string');
  const details = combinations[s.status]; require(Object.hasOwn(details, s.detail));
  const rule = details[s.detail];
  require(rule === 'either' || (rule === 'hash') === (s.frame_sha256 !== null));
  require(s.preview_available === ((s.status === 'accepted' && s.detail === 'awaiting_approval') || s.status === 'queued'));
  for (const field of ['accepted_age_ms', 'remaining_decode_ms', 'remaining_moderation_ms', 'remaining_handoff_ms']) {
    if (s.time_uncertain) require(s[field] === null); else integer(s[field]);
  }
  if (s.status === 'rejected' || s.status === 'expired') {
    for (const field of ['remaining_decode_ms', 'remaining_moderation_ms', 'remaining_handoff_ms'])
      require(s.time_uncertain || s[field] === 0);
  }
  return value as ImageStatus;
}
export function parseIntakeState(value: unknown): IntakeState {
  const s = object(value, 'schema incarnation mode worker_connected health fault receiving decode_busy pending receipt_count');
  require(s.schema === 'market-image-intake/v1' && s.mode === 'local-intake-only' && s.worker_connected === false);
  uuid(s.incarnation); oneOf(s.health, ['ready', 'stopping', 'faulted']);
  oneOf(s.fault, [null, 'clock', 'decoder', 'ownership', 'shutdown']);
  require((s.health === 'ready' && s.fault === null) || (s.health === 'faulted' && s.fault !== null) || s.health === 'stopping');
  boolean(s.receiving); boolean(s.decode_busy); integer(s.receipt_count, 0, 512);
  if (s.pending !== null) {
    const pending = parseImageStatus(s.pending);
    require((pending.status === 'accepted' || pending.status === 'queued') && pending.incarnation === s.incarnation);
  }
  if (s.health !== 'ready') require(!s.receiving && s.pending === null);
  if (s.pending !== null) require(!s.receiving);
  return value as IntakeState;
}
export function parseAcceptance(value: unknown): Acceptance {
  const a = object(value, 'schema status_capability image'); require(a.schema === 'market-image-acceptance/v1');
  require(typeof a.status_capability === 'string' && receiptPattern.test(a.status_capability)); parseImageStatus(a.image);
  return value as Acceptance;
}
export async function readBoundedResponse(response: Response, maximum: number, exact: boolean): Promise<Uint8Array> {
  const reader = response.body?.getReader(); require(reader !== undefined);
  const result = new Uint8Array(maximum); let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read(); if (done) break;
      require(value instanceof Uint8Array && length + value.length <= maximum);
      result.set(value, length); length += value.length;
    }
    require(!exact || length === maximum);
    return result.slice(0, length);
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  finally { reader.releaseLock(); }
}
export async function readImageJson(response: Response): Promise<unknown> {
  const bytes = await readBoundedResponse(response, 8192, false);
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)) as unknown;
}
export async function verifyRgb(rgb: Uint8Array, expected: string, crypto: Crypto): Promise<void> {
  require(rgb.length === 12288 && digestPattern.test(expected));
  const prefix = new TextEncoder().encode('{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n');
  const content = new Uint8Array(prefix.length + rgb.length); content.set(prefix); content.set(rgb, prefix.length);
  const actual = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', content)), byte => byte.toString(16).padStart(2, '0')).join('');
  require(actual === expected);
}
