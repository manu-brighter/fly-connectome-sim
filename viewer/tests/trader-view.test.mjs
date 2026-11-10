import assert from 'node:assert/strict';
import test from 'node:test';
import { createMarketTrader } from '../src/market-trader.ts';
import { snapshot } from './market-fixtures.mjs';
import { native } from './native-fixtures.test.mjs';
import { createState, applySnapshot } from '../../market/web/state.ts';
import { createNativeState, adoptNativeState } from '../../market/web/native-state.ts';
class Element {
  constructor(document) { this.ownerDocument = document; this.children = []; this.attributes = {}; this.dataset = {}; this.listeners = {}; this.classList = { add() {} }; }
  set textContent(value) { this.text = value; this.children = []; }
  get textContent() { return this.text ?? ''; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(key, callback) { this.listeners[key] = callback; }
  removeEventListener(key) { delete this.listeners[key]; }
}
const live = changes => snapshot({ schema: 'market-snapshot-v2', source_kind: 'native_measurement', readout_version: 'continuous-motor-drive/v1', paused: false, ...changes });
const board = (value, now) => applySnapshot(createState(), value, now, 0);

test('wrapper converts authoritative rappen to CHF and clears old scene price on connected source reset or history gap', () => {
  const document = {}; document.createElement = document.createElementNS = () => new Element(document);
  const trades = [], scene = { setConnection() {}, setActivity() {}, setInput() {}, setTrade(value) { trades.push(value); }, dispose() {} };
  const view = createMarketTrader(new Element(document), () => scene);
  view.presentation.onState(adoptNativeState(createNativeState(), native(), 0, 0), 0);
  const initial = live(); view.presentation.onBoard(board(initial, 0), 0);
  const activated = live({ revision: 2, price_version: 1, rows: initial.rows.map((row, index) => index ? row : { ...row, current_rappen: 450, drink_version: 1, last_activation_id: '22222222-2222-4222-8222-222222222222' }) });
  view.presentation.onBoard(board(activated, 100), 100);
  assert.equal(trades.at(-1).from, 4); assert.equal(trades.at(-1).to, 4.5);
  view.presentation.onBoard(board(live({ incarnation: '55555555-5555-4555-8555-555555555555' }), 200), 200);
  assert.equal(trades.at(-1), null);
  view.presentation.onBoard(board(initial, 300), 300);
  view.presentation.onBoard(board(activated, 400), 400); assert.ok(trades.at(-1));
  view.presentation.onBoard(board(live({ revision: 5, price_version: 4, rows: activated.rows.map((row, index) => index ? row : { ...row, current_rappen: 600, drink_version: 4 }) }), 500), 500);
  assert.equal(trades.at(-1), null); view.dispose();
});
