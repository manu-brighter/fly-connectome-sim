import assert from 'node:assert/strict';
import test from 'node:test';
import { snapshot } from './market-fixtures.mjs';
import { native } from './native-fixtures.test.mjs';
import { createState, applySnapshot, disconnect } from '../../market/web/state.ts';
import { createNativeState, adoptNativeState } from '../../market/web/native-state.ts';
const trader = await import('../../market/web/trader-state.ts');
const live = changes => snapshot({ schema: 'market-snapshot-v2', source_kind: 'native_measurement', readout_version: 'continuous-motor-drive/v1', paused: false, primary_state: 'present', ...changes });
const board = (value, now = 0) => applySnapshot(createState(), value, now, 0);

test('trader baselines current prices, animates exactly one confirmed activation and deduplicates polls', () => {
  let source = live(), state = trader.adoptTraderPrices(trader.createTraderPrices(), board(source), 0);
  assert.equal(state.trade, null); assert.equal(state.histories['drink-00'].length, 1);
  source = live({ revision: 2, price_version: 1, rows: source.rows.map((row, index) => index ? row : { ...row, current_rappen: 450, drink_version: 1, last_activation_id: '22222222-2222-4222-8222-222222222222' }) });
  state = trader.adoptTraderPrices(state, board(source, 100), 100);
  assert.equal(state.trade.from, 400); assert.equal(state.trade.to, 450);
  assert.equal(state.histories['drink-00'].length, 2);
  assert.equal(trader.adoptTraderPrices(state, board(source, 200), 200).trade.id, state.trade.id);
  assert.equal(trader.adoptTraderPrices(state, board(source, 200), 200).histories['drink-00'].length, 2);
});

test('reconnect and missed price versions start honest gaps without replaying a trade', () => {
  const initial = live(); let state = trader.adoptTraderPrices(trader.createTraderPrices(), board(initial), 0);
  const jumped = live({ revision: 4, price_version: 3, rows: initial.rows.map((row, index) => index ? row : { ...row, current_rappen: 600, drink_version: 3, last_activation_id: '22222222-2222-4222-8222-222222222222' }) });
  state = trader.adoptTraderPrices(state, board(jumped, 100), 100);
  assert.equal(state.trade, null); assert.equal(state.histories['drink-00'].at(-1).gap, true);
  state = trader.adoptTraderPrices(state, disconnect(board(jumped, 100)), 110);
  state = trader.adoptTraderPrices(state, board(jumped, 200), 200);
  assert.equal(state.histories['drink-00'].length, 1); assert.equal(state.trade, null); assert.equal(state.gap, true);
});

test('measured traces append observations once, mark missing intervals and reset on worker replacement', () => {
  let measurement = adoptNativeState(createNativeState(), native(), 0, 0);
  let state = trader.adoptTraderActivity(trader.createTraderActivity(), measurement, 0);
  assert.equal(state.points.length, 1);
  state = trader.adoptTraderActivity(state, measurement, 10); assert.equal(state.points.length, 1);
  measurement = adoptNativeState(measurement, native({ observations_completed: 3, model_ms: 1500 }), 20, 0);
  state = trader.adoptTraderActivity(state, measurement, 20);
  assert.equal(state.points.at(-1).gap, true);
  assert.equal(trader.adoptTraderActivity(state, measurement, 6000).connected, false);
  measurement = adoptNativeState(measurement, native({ worker_session: '44444444-4444-4444-8444-444444444444' }), 6001, 0);
  state = trader.adoptTraderActivity(state, measurement, 6001);
  assert.equal(state.points.length, 1);
});

test('native frame metadata must match the fresh measured tuple exactly; black, stale, missing pixels and replay fail', () => {
  const measurement = adoptNativeState(createNativeState(), native(), 0, 0), value = measurement.snapshot;
  const raw = { schema: 'market-native-frame/v1', incarnation: value.incarnation, worker_session: value.worker_session,
    observations_completed: value.observations_completed, input_kind: value.input_kind, image_id: value.image_id, frame_sha256: value.frame_sha256,
    rgb_base64: 'A'.repeat(16384) };
  const frame = trader.parseNativeFrame(raw);
  assert.equal(trader.frameMatchesNative(frame, measurement, 0), true);
  for (const changed of [{ observations_completed: 2 }, { frame_sha256: 'b'.repeat(64) }, { rgb_base64: null }, { image_id: '55555555-5555-4555-8555-555555555555' }])
    assert.equal(trader.frameMatchesNative(trader.parseNativeFrame({ ...raw, ...changed }), measurement, 0), false);
  assert.equal(trader.frameMatchesNative(frame, measurement, 5000), false);
  assert.throws(() => trader.parseNativeFrame({ ...raw, rgb_base64: 'A'.repeat(16385) }));
  assert.throws(() => trader.parseNativeFrame({ ...raw, input_kind: 'black', image_id: null }));
});
