import assert from 'node:assert/strict';
import test from 'node:test';
import { imageV2, intakeV2, native, session, groups } from './native-fixtures.test.mjs';
import { status, intake, receipt } from './image-fixtures.mjs';
const api = await import('../../market/web/native-protocol.ts').catch(() => ({}));
const old = await import('../../market/web/image-protocol.ts');
function fn(name) { assert.equal(typeof api[name], 'function', `${name} missing`); return api[name]; }
const terminal = { preview_available: false, remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 };
const started = { worker_session: session, first_observation_index: 2, preview_available: false, remaining_handoff_ms: 0 };

test('exact v2 variants preserve v1 strictness and acceptance schema dispatch', () => {
  const parse = fn('parseImageStatusV2');
  const variants = [imageV2(), imageV2({ status: 'accepted', detail: 'decoding', frame_sha256: null, preview_available: false }),
    imageV2({ status: 'queued', detail: 'ready' }), imageV2({ status: 'queued', detail: 'dispatching', worker_session: session, preview_available: false }),
    imageV2({ status: 'processing', detail: 'processing', ...started }),
    imageV2({ status: 'processed', detail: 'completed', ...started, ...terminal, completed_observations: 8, observation_revision: 10 }),
    imageV2({ status: 'expired', detail: 'ttl_expired', ...terminal }),
    ...['decode_failed', 'decode_timeout', 'moderation_rejected', 'moderation_timeout', 'worker_failed', 'worker_outcome_unknown', 'session_ended', 'clock'].map(detail =>
      imageV2({ status: 'rejected', detail, frame_sha256: detail.startsWith('decode') ? null : 'a'.repeat(64), ...terminal })),
    imageV2({ status: 'rejected', detail: 'worker_outcome_unknown', ...started, ...terminal, completed_observations: 3, observation_revision: 5 })];
  for (const value of variants) assert.equal(parse(value), value);
  assert.throws(() => old.parseImageStatus(imageV2())); assert.throws(() => parse(status()));
  for (const [schema, image] of [['market-image-acceptance/v1', status()], ['market-image-acceptance/v2', imageV2()]]) {
    assert.equal(old.parseAcceptance({ schema, status_capability: receipt, image }).image, image);
    assert.throws(() => old.parseAcceptance({ schema, status_capability: receipt, image: schema.endsWith('v1') ? imageV2() : status() }));
  }
});

test('v2 rejects malformed scalar bounds, mixed variants and fabricated measurement progress', () => {
  const parse = fn('parseImageStatusV2');
  for (const changes of [{ extra: 1 }, { revision: 7 }, { worker_session: session }, { observation_revision: 1 },
    { completed_observations: true }, { first_observation_index: 33 }, { time_uncertain: true },
    { status: 'processing', detail: 'processing', ...started, completed_observations: 2, observation_revision: 3 },
    { status: 'processed', detail: 'completed', ...started, ...terminal, completed_observations: 7, observation_revision: 9 },
    { status: 'queued', detail: 'dispatching', preview_available: true, worker_session: session },
    { status: 'rejected', detail: 'worker_outcome_unknown', ...terminal, first_observation_index: 1 },
    { status: 'processing', detail: 'processing', ...started, remaining_handoff_ms: 1 },
    { status: 'rejected', detail: 'constructor', ...terminal }]) assert.throws(() => parse(imageV2(changes)), JSON.stringify(changes));
});

test('v2 intake validates start/end/fault and pending/active binding', () => {
  const parse = fn('parseIntakeStateV2');
  assert.equal(parse(intakeV2()).native_state, 'running');
  for (const state of ['starting', 'ended', 'stopping']) assert.equal(parse(intakeV2({ native_state: state, health: 'stopping', worker_connected: false, pending: null })).native_state, state);
  assert.equal(parse(intakeV2({ native_state: 'faulted', health: 'faulted', fault: 'native_worker', worker_connected: false, pending: null })).fault, 'native_worker');
  const active = imageV2({ status: 'processing', detail: 'processing', ...started });
  assert.equal(parse(intakeV2({ active, pending: imageV2({ id: '44444444-4444-4444-8444-444444444444' }) })).active, active);
  for (const changes of [{ active: imageV2() }, { native_state: 'ended' }, { worker_connected: false }, { receiving: true },
    { active: { ...active, incarnation: session } }, { active, pending: imageV2({ status: 'queued', detail: 'dispatching', preview_available: false, worker_session: '44444444-4444-4444-8444-444444444444' }) }]) assert.throws(() => parse(intakeV2(changes)));
  assert.throws(() => old.parseIntakeState(intakeV2())); assert.throws(() => parse(intake()));
});

test('native DTO requires exact closed fields, populations/rates, clocks and last-measurement variants', () => {
  const parse = fn('parseNativeState'); assert.equal(parse(native()).input_kind, 'image');
  const empty = native({ state: 'starting', model_ms: 0, observations_completed: 0, measurement_age_ms: null,
    input_kind: null, image_id: null, frame_sha256: null, group_spikes: null, group_rates_hz: null });
  assert.equal(parse(empty).group_spikes, null);
  assert.equal(parse(native({ input_kind: 'black', image_id: null })).image_id, null);
  assert.equal(parse(native({ state: 'ended', model_ms: 20000, observations_completed: 40 })).state, 'ended');
  assert.equal(parse(native({ state: 'faulted', fault: 'clock', time_uncertain: true, measurement_age_ms: null })).measurement_age_ms, null);
  assert.equal(parse(native({ state: 'faulted', fault: 'source', time_uncertain: true, measurement_age_ms: null })).fault, 'source', 'a later clock failure must not replace the first fault');
  for (const changes of [{ extra: 1 }, { fault: 'unknown' }, { state: 'ended' }, { state: 'starting' }, { model_ms: 1000 },
    { observations_completed: true }, { input_kind: 'black' }, { time_uncertain: true }, { measurement_age_ms: -1 },
    { time_uncertain: true, measurement_age_ms: null }, { state: 'faulted' },
    { group_spikes: { ...native().group_spikes, [groups[0]]: 75001 } },
    { group_rates_hz: { ...native().group_rates_hz, kc: Infinity } },
    { group_rates_hz: { ...native().group_rates_hz, kc: 100 } }]) assert.throws(() => parse(native(changes)), JSON.stringify(changes));
});

test('explicit live schemas accept later observations and wall-limited end while proof remains bounded', () => {
  const parse = fn('parseNativeState');
  const live = native({ schema: 'market-native-state/v2', profile: 'live-pilot/v1', mode: 'live-pilot',
    model_limit_ms: 43200000, observations_completed: 51, model_ms: 25500 });
  assert.equal(parse(live), live);
  assert.equal(parse({ ...live, state: 'ended' }).state, 'ended');
  for (const patch of [{ profile: 'proof/v1' }, { model_limit_ms: 43200500 }, { observations_completed: 86401, model_ms: 43200500 },
    { model_limit_ms: 25000 }, { extra: true }]) assert.throws(() => parse({ ...live, ...patch }));
  assert.throws(() => parse(native({ observations_completed: 51, model_ms: 25500 })));
  const image = imageV2({ schema: 'market-image-status-wire/v3', ...started, ...terminal,
    status: 'processed', detail: 'completed', first_observation_index: 50, completed_observations: 8, observation_revision: 58 });
  assert.equal(old.parseAnyImageStatus(image), image);
  assert.throws(() => api.parseImageStatusV2({ ...image, schema: 'market-image-status-wire/v2' }));
  assert.throws(() => old.parseAnyImageStatus({ ...image, first_observation_index: 86393, observation_revision: 86401 }));
  const intake = intakeV2({ schema: 'market-image-intake/v3', mode: 'live-pilot', pending: null, active: { ...image,
    status: 'processing', detail: 'processing', completed_observations: 3, observation_revision: 53 } });
  assert.equal(old.parseAnyIntakeState(intake), intake);
  const accepted = { schema: 'market-image-acceptance/v3', status_capability: receipt, image };
  assert.equal(old.parseAcceptance(accepted), accepted);
  assert.throws(() => old.parseAcceptance({ ...accepted, image: imageV2() }));
});
