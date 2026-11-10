export type Fault = null | 'clock' | 'storage' | 'capacity' | 'overload';
export type PrimaryState = 'unclaimed' | 'awaiting_ack' | 'present' | 'absent';
export type Challenge = { id: string; incarnation: string; session_id: string; revision: number; expires_in_ms: number };
export type PriceRow = {
  id: string; name: string; minimum_rappen: number; maximum_rappen: number; grid_rappen: number;
  initial_rappen: number; current_rappen: number; drink_version: number; last_activation_id: string | null;
  recorded_utc: string | null; remaining_lock_ms: number; estimated_eligible_utc: string | null; recovery_lock: boolean;
};
type SnapshotFields = {
  incarnation: string; revision: number; price_version: number; config_id: string;
  generation: number; paused: boolean; fault: Fault; primary_state: PrimaryState; server_utc: string;
  rows: PriceRow[]; challenge: Challenge | null;
};
export type Snapshot = SnapshotFields & ({ schema: 'market-snapshot-v1' } |
  { schema: 'market-snapshot-v2'; source_kind: 'native_measurement'; readout_version: 'continuous-motor-drive/v1' });
export type ProposalReason = 'activated' | 'no_change' | 'clock' | 'storage' | 'capacity' | 'overload' |
  'wrong_config' | 'wrong_source' | 'wrong_incarnation' | 'wrong_generation' | 'reordered' | 'future_proposal' |
  'expired' | 'unknown_drink' | 'stale_drink_version' | 'paused' | 'board_absent' | 'out_of_range' | 'off_grid' | 'cooldown';
export type ProposalResult = {
  event_id: string; request_id: string; status: 'activated' | 'no_change' | 'rejected'; reason: ProposalReason;
  activation_id: string | null; terminal_revision: number; terminal_price_version: number;
  drink_version: number | null; current_rappen: number | null;
};
export type PauseReply = { paused: true; durable: boolean; fault: Fault; revision: number; audit_recorded: boolean };
export type ControlResult = {
  command_id: string; status: 'accepted' | 'rejected';
  reason: 'resumed' | 'clock' | 'storage' | 'capacity' | 'board_absent' | 'superseded'; terminal_revision: number;
};
export type ResumeReply = { result: ControlResult; snapshot: Snapshot; superseding_reason: null | 'operator_pause' | 'overload' };
export type ClaimReply = { session_id: string; primary_token: string; snapshot: Snapshot };
export type AckReply = { accepted: boolean; reason: 'acknowledged' | 'unknown_session' | 'invalid_challenge' | 'expired_challenge' | 'stale_revision'; snapshot: Snapshot };
export type ApiError = { error: string };

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const idPattern = /^[A-Za-z0-9_-]{1,64}$/;
function require(condition: unknown): asserts condition { if (!condition) throw new Error('Ungültige Serverantwort'); }
function object(value: unknown, keys: string): Record<string, unknown> {
  require(value !== null && typeof value === 'object' && !Array.isArray(value));
  const record = value as Record<string, unknown>, expected = keys.split(' ');
  require(Object.keys(record).length === expected.length && expected.every(key => Object.hasOwn(record, key)));
  return record;
}
function integer(value: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): asserts value is number {
  require(typeof value === 'number' && Number.isSafeInteger(value) && value >= minimum && value <= maximum);
}
function money(value: unknown): asserts value is number { integer(value, 1, 1000000); }
function uuid(value: unknown): asserts value is string { require(typeof value === 'string' && uuidPattern.test(value)); }
function id(value: unknown): asserts value is string { require(typeof value === 'string' && idPattern.test(value)); }
function boolean(value: unknown): asserts value is boolean { require(typeof value === 'boolean'); }
function oneOf(value: unknown, values: readonly unknown[]): void { require(values.includes(value)); }
function utc(value: unknown): void {
  require(typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value));
  const date = new Date(value);
  require(Number.isFinite(date.getTime()) && date.toISOString().slice(0, 19) === value.slice(0, 19));
}
function nullable(value: unknown, validate: (value: unknown) => void): void { if (value !== null) validate(value); }
function fault(value: unknown): void { oneOf(value, [null, 'clock', 'storage', 'capacity', 'overload']); }
function row(value: unknown): PriceRow {
  const r = object(value, 'id name minimum_rappen maximum_rappen grid_rappen initial_rappen current_rappen drink_version last_activation_id recorded_utc remaining_lock_ms estimated_eligible_utc recovery_lock');
  id(r.id);
  require(typeof r.name === 'string' && [...r.name].length >= 1 && [...r.name].length <= 80 &&
    new TextEncoder().encode(r.name).length <= 320 && !/[\p{Cc}\p{Cs}]/u.test(r.name));
  money(r.minimum_rappen); money(r.maximum_rappen); money(r.grid_rappen); money(r.initial_rappen); money(r.current_rappen);
  const grid = r.grid_rappen;
  require(r.minimum_rappen <= r.initial_rappen && r.initial_rappen <= r.maximum_rappen &&
    r.minimum_rappen <= r.current_rappen && r.current_rappen <= r.maximum_rappen &&
    [r.minimum_rappen, r.maximum_rappen, r.initial_rappen, r.current_rappen].every(amount => amount % grid === 0));
  integer(r.drink_version); nullable(r.last_activation_id, uuid); nullable(r.recorded_utc, utc);
  integer(r.remaining_lock_ms, 0, 1800000); nullable(r.estimated_eligible_utc, utc); boolean(r.recovery_lock);
  return value as PriceRow;
}
export function parseSnapshot(value: unknown): Snapshot {
  const native = (value as { schema?: unknown } | null)?.schema === 'market-snapshot-v2';
  const s = object(value, 'schema incarnation revision price_version config_id generation paused fault primary_state server_utc rows challenge' + (native ? ' source_kind readout_version' : ''));
  require(s.schema === (native ? 'market-snapshot-v2' : 'market-snapshot-v1'));
  if (native) require(s.source_kind === 'native_measurement' && s.readout_version === 'continuous-motor-drive/v1'); uuid(s.incarnation); integer(s.revision); integer(s.price_version); integer(s.generation);
  require(typeof s.config_id === 'string' && /^[a-f0-9]{64}$/.test(s.config_id)); boolean(s.paused); fault(s.fault);
  oneOf(s.primary_state, ['unclaimed', 'awaiting_ack', 'present', 'absent']); utc(s.server_utc);
  require(Array.isArray(s.rows) && s.rows.length >= 10 && s.rows.length <= 20);
  const rows = s.rows.map(row); require(new Set(rows.map(item => item.id)).size === rows.length);
  if (s.challenge !== null) {
    const c = object(s.challenge, 'id incarnation session_id revision expires_in_ms');
    uuid(c.id); uuid(c.incarnation); uuid(c.session_id); integer(c.revision); integer(c.expires_in_ms, 0, 5000);
    require(c.incarnation === s.incarnation && c.revision === s.revision);
  }
  return value as Snapshot;
}
const rejectionReasons = ['clock', 'storage', 'capacity', 'overload', 'wrong_config', 'wrong_source', 'wrong_incarnation',
  'wrong_generation', 'reordered', 'future_proposal', 'expired', 'unknown_drink', 'stale_drink_version', 'paused',
  'board_absent', 'out_of_range', 'off_grid', 'cooldown'];
export function parseProposalResult(value: unknown): ProposalResult {
  const r = object(value, 'event_id request_id status reason activation_id terminal_revision terminal_price_version drink_version current_rappen');
  uuid(r.event_id); id(r.request_id); oneOf(r.status, ['activated', 'no_change', 'rejected']);
  oneOf(r.reason, r.status === 'rejected' ? rejectionReasons : [r.status]);
  nullable(r.activation_id, uuid); require((r.status === 'activated') === (r.activation_id !== null));
  integer(r.terminal_revision); integer(r.terminal_price_version);
  if (r.drink_version === null || r.current_rappen === null) {
    require(r.status === 'rejected' && r.drink_version === null && r.current_rappen === null);
  } else { integer(r.drink_version); money(r.current_rappen); }
  if (r.reason === 'unknown_drink') require(r.drink_version === null && r.current_rappen === null);
  return value as ProposalResult;
}
export function parseResumeReply(value: unknown): ResumeReply {
  const reply = object(value, 'result snapshot superseding_reason');
  const result = object(reply.result, 'command_id status reason terminal_revision');
  id(result.command_id); oneOf(result.status, ['accepted', 'rejected']);
  oneOf(result.reason, result.status === 'accepted' ? ['resumed'] : ['clock', 'storage', 'capacity', 'board_absent', 'superseded']);
  integer(result.terminal_revision); parseSnapshot(reply.snapshot); oneOf(reply.superseding_reason, [null, 'operator_pause', 'overload']);
  return value as ResumeReply;
}
export function parseClaimReply(value: unknown): ClaimReply {
  const r = object(value, 'session_id primary_token snapshot'); uuid(r.session_id);
  require(typeof r.primary_token === 'string' && /^[A-Za-z0-9_-]{43}$/.test(r.primary_token)); parseSnapshot(r.snapshot);
  return value as ClaimReply;
}
export function parseAckReply(value: unknown): AckReply {
  const r = object(value, 'accepted reason snapshot'); boolean(r.accepted);
  oneOf(r.reason, r.accepted ? ['acknowledged'] : ['unknown_session', 'invalid_challenge', 'expired_challenge', 'stale_revision']);
  parseSnapshot(r.snapshot); return value as AckReply;
}
export function parsePauseReply(value: unknown): PauseReply {
  const r = object(value, 'paused durable fault revision audit_recorded'); require(r.paused === true);
  boolean(r.durable); fault(r.fault); integer(r.revision); boolean(r.audit_recorded); return value as PauseReply;
}
