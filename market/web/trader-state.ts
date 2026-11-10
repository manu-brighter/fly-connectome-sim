import type { BoardState } from './state.ts';
import { isFresh } from './state.ts';
import type { PriceRow } from './protocol.ts';
import type { NativeState } from './native-state.ts';
import { nativeFreshness } from './native-state.ts';
import type { GroupValues } from './native-protocol.ts';

export type PricePoint = { price: number; version: number; utc: string; gap: boolean };
// Authoritative monetary values remain integer rappen in this model.
export type ObservedTrade = { id: string; drinkId: string; name: string; from: number; to: number; minimum: number; maximum: number };
export type TraderPrices = {
  incarnation: string | null; config: string | null; generation: number; revision: number; version: number;
  connected: boolean; live: boolean; gap: boolean; rows: PriceRow[]; histories: Record<string, PricePoint[]>; trade: ObservedTrade | null;
};
export function createTraderPrices(): TraderPrices {
  return { incarnation: null, config: null, generation: -1, revision: -1, version: -1,
    connected: false, live: false, gap: false, rows: [], histories: {}, trade: null };
}
export function adoptTraderPrices(previous: TraderPrices, board: BoardState, now: number): TraderPrices {
  const snapshot = board.snapshot;
  if (!snapshot || !isFresh(board, now)) return previous.connected ? { ...previous, connected: false, trade: null } : previous;
  const live = snapshot.schema === 'market-snapshot-v2';
  const reset = previous.incarnation !== snapshot.incarnation || previous.config !== snapshot.config_id ||
    previous.generation !== board.connectionGeneration || !previous.connected;
  if (reset) {
    const gap = previous.incarnation !== null;
    return { incarnation: snapshot.incarnation, config: snapshot.config_id, generation: board.connectionGeneration,
      revision: snapshot.revision, version: snapshot.price_version, connected: true, live, gap, rows: snapshot.rows,
      histories: Object.fromEntries(snapshot.rows.map(row => [row.id, [{ price: row.current_rappen, version: row.drink_version, utc: snapshot.server_utc, gap: false }]])), trade: null };
  }
  if (snapshot.revision <= previous.revision) return previous;
  const changed = snapshot.rows.filter(row => row.drink_version !== previous.rows.find(old => old.id === row.id)?.drink_version);
  if (snapshot.rows.some(row => {
    const old = previous.rows.find(item => item.id === row.id);
    return !old || row.drink_version < old.drink_version || row.drink_version === old.drink_version && row.current_rappen !== old.current_rappen;
  })) return { ...previous, connected: false, trade: null };
  const gap = snapshot.price_version > previous.version + changed.length;
  const histories = { ...previous.histories };
  let trade = previous.trade;
  for (const row of changed) {
    const old = previous.rows.find(item => item.id === row.id)!;
    const missed = gap || row.drink_version !== old.drink_version + 1;
    histories[row.id] = [...(histories[row.id] ?? []), { price: row.current_rappen, version: row.drink_version, utc: snapshot.server_utc, gap: missed }].slice(-180);
    if (live && !missed && changed.length === 1 && row.last_activation_id && row.last_activation_id !== old.last_activation_id && row.current_rappen !== old.current_rappen)
      trade = { id: `${snapshot.incarnation}/${row.last_activation_id}`, drinkId: row.id, name: row.name,
        from: old.current_rappen, to: row.current_rappen, minimum: row.minimum_rappen, maximum: row.maximum_rappen };
  }
  if (gap) trade = null;
  return { ...previous, revision: snapshot.revision, version: snapshot.price_version, rows: snapshot.rows, histories, gap, trade, live };
}

export type ActivityPoint = { observation: number; modelMs: number; rates: GroupValues; gap: boolean };
export type TraderActivity = { key: string | null; observation: number; connected: boolean; points: ActivityPoint[] };
export function createTraderActivity(): TraderActivity { return { key: null, observation: 0, connected: false, points: [] }; }
export function adoptTraderActivity(previous: TraderActivity, native: NativeState, now: number): TraderActivity {
  const snapshot = native.snapshot, fresh = nativeFreshness(native, now);
  const connected = fresh.live && fresh.ageMs !== null && fresh.ageMs < 5000 && snapshot?.fault === null;
  if (!snapshot || !connected || !snapshot.group_rates_hz) return previous.connected ? { ...previous, connected: false } : previous;
  const key = `${snapshot.incarnation}/${snapshot.worker_session}`;
  const reset = key !== previous.key;
  if (!reset && snapshot.observations_completed <= previous.observation) return previous.connected ? previous : { ...previous, connected: true };
  const point = { observation: snapshot.observations_completed, modelMs: snapshot.model_ms, rates: { ...snapshot.group_rates_hz },
    gap: !reset && (!previous.connected || snapshot.observations_completed !== previous.observation + 1) };
  return { key, observation: snapshot.observations_completed, connected: true, points: [...(reset ? [] : previous.points), point].slice(-120) };
}

export type NativeFrame = {
  schema: 'market-native-frame/v1'; incarnation: string; worker_session: string; observations_completed: number;
  input_kind: 'black' | 'image' | null; image_id: string | null; frame_sha256: string | null; rgb_base64: string | null;
};
export type VerifiedNativeFrame = Omit<NativeFrame, 'rgb_base64'> & { pixels: Uint8Array };
export function parseNativeFrame(value: unknown): NativeFrame {
  function require(valid: unknown): asserts valid { if (!valid) throw new Error('Ungültiger aktueller Bildeingang'); }
  require(value !== null && typeof value === 'object' && !Array.isArray(value));
  const row = value as Record<string, unknown>, fields = 'schema incarnation worker_session observations_completed input_kind image_id frame_sha256 rgb_base64'.split(' ');
  require(Object.keys(row).length === fields.length && fields.every(key => Object.hasOwn(row, key)));
  const uuid = (item: unknown) => typeof item === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(item);
  require(row.schema === 'market-native-frame/v1' && uuid(row.incarnation) && uuid(row.worker_session));
  require(typeof row.observations_completed === 'number' && Number.isSafeInteger(row.observations_completed) && row.observations_completed >= 0 && row.observations_completed <= 86400);
  require(row.input_kind === null || row.input_kind === 'black' || row.input_kind === 'image');
  require(row.frame_sha256 === null || typeof row.frame_sha256 === 'string' && /^[0-9a-f]{64}$/.test(row.frame_sha256));
  require(row.input_kind === 'image' ? uuid(row.image_id) && row.frame_sha256 !== null : row.image_id === null);
  require(row.observations_completed === 0 ? row.input_kind === null && row.frame_sha256 === null : row.input_kind !== null && row.frame_sha256 !== null);
  require(row.rgb_base64 === null || row.input_kind === 'image' && typeof row.rgb_base64 === 'string' && /^[A-Za-z0-9+/]{16384}$/.test(row.rgb_base64));
  return value as NativeFrame;
}
export function frameMatchesNative(frame: NativeFrame, native: NativeState, now: number): boolean {
  const snapshot = native.snapshot, freshness = nativeFreshness(native, now);
  return snapshot !== null && freshness.live && freshness.ageMs !== null && freshness.ageMs < 5000 && snapshot.fault === null &&
    frame.rgb_base64 !== null && frame.input_kind === 'image' && snapshot.input_kind === 'image' &&
    frame.incarnation === snapshot.incarnation && frame.worker_session === snapshot.worker_session &&
    frame.observations_completed === snapshot.observations_completed && frame.image_id === snapshot.image_id && frame.frame_sha256 === snapshot.frame_sha256;
}
