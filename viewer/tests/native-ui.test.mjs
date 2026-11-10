import assert from 'node:assert/strict';
import test from 'node:test';
import { native, intakeV2, imageV2 } from './native-fixtures.test.mjs';
const main = await import('../../market/web/image-main.ts');
const view = await import('../../market/web/image-view.ts');
const state = await import('../../market/web/native-state.ts').catch(() => ({}));
class Element {
  constructor(tagName, ownerDocument) { this.tagName = tagName; this.ownerDocument = ownerDocument; this.children = []; this.listeners = {}; this.attributes = {}; this._text = ''; this.hidden = false; this.disabled = false; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  append(...children) { this.children.push(...children); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, callback) { (this.listeners[key] ??= new Set()).add(callback); }
  removeEventListener(key, callback) { this.listeners[key]?.delete(callback); }
  dispatch(key) { for (const callback of this.listeners[key] ?? []) callback(); }
  getContext() { return { clearRect() {} }; }
}
function fixture(fetch) {
  const document = new Element('document', null), timers = new Map(); let next = 0;
  document.createElement = tag => new Element(tag, document); document.hidden = false;
  const window = new Element('window', document); Object.assign(window, { document, fetch, now: 0, navigator: { onLine: true },
    performance: { now: () => window.now }, setTimeout(callback, delay) { timers.set(++next, { callback, delay }); return next; }, clearTimeout(id) { timers.delete(id); } });
  document.defaultView = window;
  return { root: document.createElement('main'), window, timers, tick(delay) { const entry = [...timers].find(([, timer]) => timer.delay === delay); assert.ok(entry, `timer ${delay}`); timers.delete(entry[0]); entry[1].callback(); } };
}
async function flush() { for (let i = 0; i < 20; i++) await new Promise(resolve => setImmediate(resolve)); }

test('minimal measured pane keeps original age and last measurement identity, with no image or resume', () => {
  assert.equal(typeof view.createNativeView, 'function'); assert.equal(typeof view.renderNative, 'function');
  const h = fixture(), pane = view.createNativeView(h.root);
  let value = state.adoptNativeState(state.createNativeState(), native({ measurement_age_ms: 9000 }), 0, 0);
  view.renderNative(pane, value, 0);
  assert.ok(h.root.textContent.includes('Lokaler neuronaler Bildtest — Preise weiterhin synthetisch.'));
  assert.ok(h.root.textContent.includes('0.5 / 20 s')); assert.ok(h.root.textContent.includes('9.0 s'));
  view.renderNative(pane, value, 1000); assert.ok(h.root.textContent.includes('Messung veraltet'));
  view.renderNative(pane, value, 5000); assert.ok(h.root.textContent.includes('Verbindung unklar'));
  assert.ok(!h.root.textContent.includes('Fortsetzen')); assert.ok(!h.root.textContent.includes('verarbeitet'));
});

test('native HTTP poll is serial, bounded through body, independently aborted and ignores late replies', async () => {
  assert.equal(typeof main.startNative, 'function');
  const calls = [], pending = [];
  const h = fixture((url, options) => { calls.push({ url, options }); return new Promise(resolve => pending.push(resolve)); });
  const client = main.startNative(h.root, 'A'.repeat(43));
  assert.equal(calls.length, 1); assert.equal(calls[0].url, '/api/native/state');
  assert.equal(calls[0].options.credentials, 'omit'); assert.equal(calls[0].options.headers.Authorization, `Bearer ${'A'.repeat(43)}`);
  h.window.navigator.onLine = false; h.window.dispatch('offline');
  assert.equal(calls[0].options.signal.aborted, true);
  pending.shift()(Response.json(native())); await flush();
  assert.equal(client.getState().snapshot, null);
  h.window.navigator.onLine = true; h.window.dispatch('online'); await flush();
  assert.equal(calls.length, 2);
  pending.shift()(Response.json(native())); await flush(); assert.equal(client.getState().snapshot.observations_completed, 1);
  h.tick(2000); await flush(); assert.equal(calls.length, 3);
  h.window.now = 5000; h.tick(250); assert.ok(h.root.textContent.includes('Verbindung unklar'));
  h.tick(5000); assert.equal(calls[2].options.signal.aborted, true);
  pending.shift()(Response.json(native({ observations_completed: 2, model_ms: 1000 }))); await flush();
  assert.equal(client.getState().snapshot.observations_completed, 1, 'late reply after abort cannot become fresh');
  client.dispose(); assert.equal(h.timers.size, 0);
});

test('native JSON cap and optional 404 hide never become measurements', async () => {
  assert.equal(typeof main.startNative, 'function');
  for (const response of [new Response('x'.repeat(16385)), new Response('', { status: 404 })]) {
    const h = fixture(async () => response), client = main.startNative(h.root, 'A'.repeat(43));
    await flush(); assert.equal(client.getState().snapshot, null); client.dispose();
  }
});

test('native response body retains its single 5s deadline and 16KiB cap while streaming', async () => {
  let controller;
  const h = fixture(async () => new Response(new ReadableStream({ start(value) { controller = value; value.enqueue(new TextEncoder().encode('{')); } })));
  const client = main.startNative(h.root, 'A'.repeat(43)); await flush();
  assert.ok([...h.timers.values()].some(timer => timer.delay === 5000));
  h.tick(5000); controller.enqueue(new TextEncoder().encode(' '.repeat(16384))); await flush();
  assert.equal(client.getState().snapshot, null); assert.equal(client.getState().disconnected, true); client.dispose();
});

test('pending moderation identity never substitutes for the measured image or spike totals', async () => {
  const h = fixture(async path => {
    assert.equal(path, '/api/images/state'); return Response.json(intakeV2({ pending: imageV2({ id: '44444444-4444-4444-8444-444444444444', detail: 'decoding', frame_sha256: null, preview_available: false }) }));
  });
  const pane = view.createNativeView(h.root), measured = state.adoptNativeState(state.createNativeState(), native(), 0, 0);
  view.renderNative(pane, measured, 0);
  const before = pane.input.textContent;
  const stop = main.startOperatorImage(h.root, 'A'.repeat(43), () => measured); await flush();
  assert.equal(pane.input.textContent, before); assert.equal(pane.rows[0].count.textContent, '1');
  stop();
});

test('v2 guest progress names eight model intervals and terminal outcome uncertainty honestly', () => {
  assert.equal(view.statusText(imageV2({ status: 'queued', detail: 'ready' })), 'Bild freigegeben. Wartet auf ein freies Modellintervall.');
  assert.equal(view.statusText(imageV2({ status: 'processed', detail: 'completed', completed_observations: 8 })), '8/8 Modellintervalle verarbeitet.');
  assert.ok(view.statusText(imageV2({ status: 'rejected', detail: 'worker_outcome_unknown', completed_observations: 3 })).includes('3/8'));
});

test('live pane shows the explicit limit and native price scope without resetting measurement age', () => {
  const h = fixture(), pane = view.createNativeView(h.root);
  const value = state.adoptNativeState(state.createNativeState(), native({ schema: 'market-native-state/v2',
    profile: 'live-pilot/v1', mode: 'live-pilot', model_limit_ms: 60000, observations_completed: 50, model_ms: 25000 }), 0, 0);
  view.renderNative(pane, value, 0);
  assert.ok(h.root.textContent.includes('25.0 / 60 s'));
  assert.ok(h.root.textContent.includes('Experimenteller konfigurierter Motor-Readout'));
  assert.ok(!h.root.textContent.includes('Preise weiterhin synthetisch'));
});
