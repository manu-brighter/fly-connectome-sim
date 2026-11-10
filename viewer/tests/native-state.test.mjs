import assert from 'node:assert/strict';
import test from 'node:test';
import { native, session, imageV2, intakeV2 } from './native-fixtures.test.mjs';
const api = await import('../../market/web/native-state.ts').catch(() => ({}));
function fn(name) { assert.equal(typeof api[name], 'function', `${name} missing`); return api[name]; }

test('transport 5s and measurement 10s are independent and same-count replies do not renew age', () => {
  let value = fn('adoptNativeState')(fn('createNativeState')(), native({ measurement_age_ms: 8000 }), 100, 0);
  assert.deepEqual(fn('nativeFreshness')(value, 2099), { transport: true, measurement: true, ageMs: 9999, live: true });
  assert.equal(fn('nativeFreshness')(value, 2100).measurement, false);
  value = fn('adoptNativeState')(value, native({ measurement_age_ms: 1000 }), 2500, 0);
  assert.equal(fn('nativeFreshness')(value, 2500).ageMs, 10400);
  assert.equal(fn('nativeFreshness')(value, 7500).transport, false);
  assert.equal(fn('nativeFreshness')(value, 7500).live, false);
});

test('late generations, regressions, same-count mutation and identity changes never mix measurements', () => {
  let value = fn('adoptNativeState')(fn('createNativeState')(), native(), 0, 0);
  const disconnected = fn('disconnectNative')(value);
  assert.equal(fn('adoptNativeState')(disconnected, native(), 1, 0), disconnected);
  assert.throws(() => fn('adoptNativeState')(value, native({ observations_completed: 0, model_ms: 0 }), 1, 0));
  assert.throws(() => fn('adoptNativeState')(value, native({ image_id: session }), 1, 0));
  const changed = fn('adoptNativeState')(value, native({ worker_session: '44444444-4444-4444-8444-444444444444' }), 1, 0);
  assert.equal(changed.generation, 1); assert.notEqual(changed.snapshot.worker_session, session);
});

test('clock uncertainty and ended retain dated counts without liveness or native resume', () => {
  const create = fn('createNativeState'), adopt = fn('adoptNativeState'), fresh = fn('nativeFreshness');
  assert.equal(fresh(adopt(create(), native({ state: 'stopping' }), 0, 0), 0).live, false);
  const value = adopt(create(), native({ state: 'faulted', fault: 'clock', time_uncertain: true, measurement_age_ms: null }), 0, 0);
  assert.equal(fresh(value, 0).ageMs, null); assert.equal(fresh(value, 0).live, false);
  assert.equal(fresh(adopt(create(), native(), 100, 0), 99).transport, false);
});

test('image changes cannot revive terminal per-image watermark or regress D1 progress', async () => {
  const image = await import('../../market/web/image-state.ts');
  const done = imageV2({ status: 'processing', detail: 'processing', worker_session: session, first_observation_index: 1,
    completed_observations: 3, observation_revision: 4, remaining_handoff_ms: 0, preview_available: false });
  let value = image.adoptOperatorState(image.createImageState(), intakeV2({ active: done, pending: null }), 0, 0);
  assert.throws(() => image.adoptOperatorState(value, intakeV2({ active: { ...done, completed_observations: 2, observation_revision: 3 }, pending: null }), 1, 0));
  assert.equal(fn('nativeAllowsImages')(fn('adoptNativeState')(fn('createNativeState')(), native(), 0, 0), value.state, 0), true);
  assert.equal(fn('nativeAllowsImages')(fn('adoptNativeState')(fn('createNativeState')(), native(), 0, 0), value.state, 5000), false);
});

test('terminal image watermark remains immutable while black and other image measurements advance', async () => {
  const image = await import('../../market/web/image-state.ts');
  const done = imageV2({ revision: 6, status: 'processed', detail: 'completed', worker_session: session, first_observation_index: 1,
    completed_observations: 8, observation_revision: 9, preview_available: false, remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 });
  let value = image.adoptImageReceipt(image.createImageState(), done);
  value = image.adoptOperatorState(value, intakeV2({ pending: null }), 100, 0);
  const measured = fn('adoptNativeState')(fn('createNativeState')(), native({ observations_completed: 20, model_ms: 10000, input_kind: 'black', image_id: null }), 100, 0);
  assert.equal(value.receipts.get(`${done.incarnation}:${done.id}`).observation_revision, 9);
  assert.equal(measured.snapshot.observations_completed, 20);
  assert.throws(() => image.adoptImageReceipt(value, { ...done, observation_revision: 20 }));
  assert.throws(() => image.adoptImageReceipt(value, { ...done, status: 'processing', detail: 'processing' }));
  assert.equal(image.adoptImageReceipt(value, { ...done, accepted_age_ms: 2000 }).receivedAtMs, 100, 'receipt updates cannot refresh transport');
});

test('receipt preview adoption does not refresh independently measured native age', async () => {
  const image = await import('../../market/web/image-state.ts');
  const measurement = fn('adoptNativeState')(fn('createNativeState')(), native(), 0, 0);
  let pending = image.adoptOperatorState(image.createImageState(), intakeV2(), 2000, 0);
  pending = image.adoptPaintedPreview(pending, image.identity(pending.state.pending), 0);
  assert.notEqual(pending.painted, null);
  assert.equal(fn('nativeFreshness')(measurement, 2000).ageMs, 3000);
  assert.equal(measurement.receivedAtMs, 0);
  const changed = fn('adoptNativeState')(measurement, native({ incarnation: session }), 2000, 0);
  assert.equal(fn('adoptNativeState')(changed, native(), 2001, 0), changed, 'old session generation cannot return');
});

test('native image mutation gate requires the exact intake binding and valid clock', () => {
  const create = fn('createNativeState'), adopt = fn('adoptNativeState'), allow = fn('nativeAllowsImages');
  const value = adopt(create(), native(), 0, 0);
  assert.equal(allow(value, intakeV2(), 0), true);
  assert.equal(allow(value, intakeV2({ incarnation: session }), 0), false);
  assert.equal(allow(value, intakeV2({ pending: imageV2({ worker_session: '44444444-4444-4444-8444-444444444444' }) }), 0), false);
  assert.equal(allow(adopt(create(), native({ state: 'stopping' }), 0, 0), intakeV2(), 0), false);
  assert.equal(allow(adopt(create(), native({ state: 'faulted', fault: 'clock', measurement_age_ms: null, time_uncertain: true }), 0, 0), intakeV2(), 0), false);
});

test('terminal native session and intake schema cannot be revived under the same identity', async () => {
  const image = await import('../../market/web/image-state.ts');
  const stopping = fn('adoptNativeState')(fn('createNativeState')(), native({ state: 'stopping', fault: 'deadline' }), 0, 0);
  assert.throws(() => fn('adoptNativeState')(stopping, native(), 1, 0));
  assert.throws(() => fn('adoptNativeState')(stopping, native({ state: 'faulted', fault: 'source' }), 1, 0));
  const intake = image.adoptOperatorState(image.createImageState(), intakeV2({ pending: null }), 0, 0);
  const { active, native_state, ...downgrade } = intake.state;
  Object.assign(downgrade, { schema: 'market-image-intake/v1', mode: 'local-intake-only', worker_connected: false });
  assert.throws(() => image.adoptOperatorState(intake, downgrade, 1, 0));
});

test('live image state keeps later progress and independent freshness with fixed session bounds', async () => {
  const image = await import('../../market/web/image-state.ts');
  const measurement = native({ schema: 'market-native-state/v2', profile: 'live-pilot/v1', mode: 'live-pilot',
    observations_completed: 51, model_ms: 25500, model_limit_ms: 60000 });
  const measured = fn('adoptNativeState')(fn('createNativeState')(), measurement, 0, 0);
  const active = imageV2({ schema: 'market-image-status-wire/v3', status: 'processing', detail: 'processing',
    worker_session: session, first_observation_index: 50, completed_observations: 1, observation_revision: 51,
    remaining_handoff_ms: 0, preview_available: false });
  const intake = intakeV2({ schema: 'market-image-intake/v3', mode: 'live-pilot', pending: null, active });
  const value = image.adoptOperatorState(image.createImageState(), intake, 0, 0);
  assert.equal(fn('nativeAllowsImages')(measured, intake, 0), true);
  assert.equal(fn('nativeAllowsImages')(measured, intake, 5000), false);
  assert.throws(() => image.adoptImageReceipt(value, { ...active, completed_observations: 0, observation_revision: 0 }));
  assert.equal(fn('nativeAllowsImages')(measured, { ...intake, active: { ...active, first_observation_index: 113 } }, 0), false);
  assert.throws(() => fn('adoptNativeState')(measured, { ...measurement, model_limit_ms: 65000 }, 1, 0));
  assert.throws(() => fn('adoptNativeState')(measured, native({ observations_completed: 51, model_ms: 25500 }), 1, 0));
});
