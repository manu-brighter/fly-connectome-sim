import assert from 'node:assert/strict';
import test from 'node:test';
import { snapshot, result, uuid } from './market-fixtures.mjs';
const rendering = await import('../../market/web/render.ts').catch(() => ({}));
const main = await import('../../market/web/main.ts').catch(() => ({}));

class Element {
  constructor(tagName, ownerDocument) { this.tagName = tagName; this.ownerDocument = ownerDocument; this.children = []; this.attributes = {}; this.listeners = {}; this.value = ''; this.disabled = false; this.hidden = false; this._text = ''; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  set innerHTML(_) { throw new Error('HTML injection is forbidden'); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ''; this.children = children; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  addEventListener(name, callback) { (this.listeners[name] ??= new Set()).add(callback); }
  removeEventListener(name, callback) { this.listeners[name]?.delete(callback); }
  dispatch(name) { for (const callback of this.listeners[name] ?? []) callback({ preventDefault() {}, target: this }); }
  getContext() { return { clearRect() {} }; }
  querySelector(selector) { return this.querySelectorAll(selector)[0] ?? null; }
  querySelectorAll(selector) {
    return this.children.flatMap(child => [ ...(selector.startsWith('[') ? child.getAttribute(selector.slice(1, -1)) !== null : child.tagName === selector) ? [child] : [], ...child.querySelectorAll(selector) ]);
  }
}
function documentDouble() {
  const doc = { hidden: false, listeners: {}, createElement(tag) { return new Element(tag, doc); },
    addEventListener(name, callback) { (this.listeners[name] ??= new Set()).add(callback); },
    removeEventListener(name, callback) { this.listeners[name]?.delete(callback); },
    dispatch(name) { for (const callback of this.listeners[name] ?? []) callback(); } };
  return doc;
}
function state(value = snapshot()) { return { snapshot: value, unknown: false, receivedAtMs: 0, connectionGeneration: 0, primarySession: null }; }
function render(root, value, now = 0) { assert.equal(typeof rendering.renderBoard, 'function'); rendering.renderBoard(root, value, now); }

test('semantic board renders all twenty ordered literal names and exact CHF prices without HTML', () => {
  const doc = documentDouble(), root = doc.createElement('main'), value = snapshot();
  value.rows[0].name = '<img src=x onerror=alert(1)>';
  render(root, state(value));
  const rows = root.querySelectorAll('li'); assert.equal(rows.length, 20);
  assert.ok(rows[0].textContent.includes(value.rows[0].name)); assert.ok(rows.every(row => row.textContent.includes('CHF 4.00')));
  assert.ok(rows[19].textContent.includes('Testgetränk 20')); assert.equal(root.querySelectorAll('img').length, 0);
  assert.equal(root.querySelectorAll('ol').length, 2); assert.equal(root.querySelectorAll('button').length, 0);
  for (const copy of ['Lokaler Testbetrieb', 'Testvorschläge, keine Verkaufspreise.', 'Synthetischer lokaler Test — keine Verkaufspreise / keine Neuronendaten']) assert.ok(root.textContent.includes(copy));
});

test('unknown board has no placeholders; stale board retains dated rows and recovery estimates', () => {
  const doc = documentDouble(), root = doc.createElement('main');
  render(root, { ...state(), snapshot: null, unknown: true, receivedAtMs: null });
  assert.equal(root.querySelectorAll('li').length, 0); assert.ok(root.textContent.includes('Letzter bekannter Stand — aktuell unbekannt')); assert.ok(!root.textContent.includes('CHF 0'));
  const value = snapshot(); Object.assign(value.rows[0], { remaining_lock_ms: 1800000, recovery_lock: true, estimated_eligible_utc: '2026-11-10T12:30:00Z' });
  render(root, state(value), 5000);
  assert.equal(root.querySelectorAll('li').length, 20); assert.ok(root.textContent.includes('2026-11-10T12:00:00Z'));
  assert.ok(root.textContent.includes('Sicherheitswartezeit nach Neustart')); assert.ok(root.textContent.includes('geschätzt'));
  assert.ok(root.textContent.includes('Letzter bekannter Stand — aktuell unbekannt'));
});

test('ten-drink configuration uses two balanced ordered lists', () => {
  const doc = documentDouble(), root = doc.createElement('main'), value = snapshot(); value.rows = value.rows.slice(0, 10);
  render(root, state(value)); assert.deepEqual(root.querySelectorAll('ol').map(list => list.children.length), [5, 5]);
  assert.ok(root.querySelectorAll('ol')[1].textContent.startsWith('Testgetränk 06'));
});

test('activation direction survives immediate ACK and timer renders without replacing or replaying rows', () => {
  const doc = documentDouble(), root = doc.createElement('main'), initial = snapshot();
  render(root, state(initial), 0);
  const activated = snapshot({ revision: 2, price_version: 1 });
  Object.assign(activated.rows[0], { current_rappen: 700, drink_version: 1, last_activation_id: uuid });
  render(root, { ...state(activated), receivedAtMs: 100 }, 100);
  const row = root.querySelectorAll('li')[0];
  assert.ok(row.textContent.includes('↑ Erhöht')); assert.ok(row.className.includes('market-activated'));
  // ACK and finish can render synchronously before the first animation paint.
  for (const time of [100, 101, 350, 1299]) {
    render(root, { ...state(activated), receivedAtMs: 100 }, time);
    assert.equal(root.querySelectorAll('li')[0], row, 'ordinary renders must retain the animated DOM node');
    assert.ok(row.textContent.includes('↑ Erhöht')); assert.ok(row.className.includes('market-activated'));
  }
  render(root, { ...state(activated), receivedAtMs: 100 }, 1300);
  assert.ok(!row.textContent.includes('↑ Erhöht')); assert.ok(!row.className.includes('market-activated'));
  render(root, { ...state({ ...activated, revision: 3 }), receivedAtMs: 1500 }, 1500);
  assert.equal(root.querySelectorAll('li')[0], row); assert.ok(!row.className.includes('market-activated'));
});

test('decrease gets its own activation window and a new incarnation resets the old direction', () => {
  const doc = documentDouble(), root = doc.createElement('main'), high = snapshot();
  Object.assign(high.rows[0], { current_rappen: 700, drink_version: 1 });
  render(root, state(high), 0);
  const lower = snapshot({ revision: 3, price_version: 2 }); Object.assign(lower.rows[0], { drink_version: 2, last_activation_id: uuid });
  render(root, { ...state(lower), receivedAtMs: 100 }, 100);
  assert.ok(root.querySelectorAll('li')[0].textContent.includes('↓ Gesenkt'));
  const restarted = { ...lower, incarnation: '22222222-2222-4222-8222-222222222222' };
  render(root, { ...state(restarted), receivedAtMs: 200 }, 200);
  assert.ok(!root.querySelectorAll('li')[0].textContent.includes('↓ Gesenkt'));
  assert.ok(!root.querySelectorAll('li')[0].className.includes('market-activated'));
});

const operatorCapability = 'o'.repeat(43), viewCapability = 'v'.repeat(43), primaryCapability = 'p'.repeat(43);
function harness(hash = `#operator=${operatorCapability}`) {
  const doc = documentDouble(), root = doc.createElement('main'), listeners = {}, calls = [], pending = [], timers = new Map(); let timerId = 0, now = 0;
  const win = { document: doc, location: { hash, pathname: '/market.html', search: '' },
    history: { replaceState(_state, _title, url) { win.location.hash = ''; win.history.url = url; } },
    navigator: { onLine: true }, performance: { now: () => now }, crypto: { randomUUID: (() => { let count = 0; return () => `action-${++count}`; })() },
    setTimeout(callback, delay) { timers.set(++timerId, { callback, delay }); return timerId; }, clearTimeout(id) { timers.delete(id); },
    addEventListener(name, callback) { (listeners[name] ??= new Set()).add(callback); }, removeEventListener(name, callback) { listeners[name]?.delete(callback); },
    fetch(url, options) {
      if (url === '/api/images/state') return Promise.resolve(new Response('', { status: 404 }));
      calls.push({ url, options }); return new Promise((resolve, reject) => pending.push({ resolve: (value, status = 200) => resolve({ ok: status === 200, status, text: async () => JSON.stringify(value) }), reject }));
    } };
  doc.defaultView = win;
  return { doc, root, win, calls, pending, timers, setNow(value) { now = value; }, event(name) { for (const callback of listeners[name] ?? []) callback(); },
    tick(delay) { const entry = [...timers].find(([, timer]) => timer.delay === delay); assert.ok(entry, `timer ${delay}`); timers.delete(entry[0]); entry[1].callback(); },
    button(text) { const button = root.querySelectorAll('button').find(item => item.textContent === text); assert.ok(button, text); return button; } };
}
async function flush() { for (let i = 0; i < 12; i++) await Promise.resolve(); }
function start(h) { assert.equal(typeof main.startBoard, 'function'); return main.startBoard(h.root); }
async function reply(h, value) { assert.ok(h.pending.length); h.pending.shift().resolve(value); await flush(); }
async function claim(h) {
  h.button('Primäre Tafel übernehmen').dispatch('click'); await flush();
  await reply(h, { session_id: uuid, primary_token: primaryCapability, snapshot: snapshot({ revision: 2, primary_state: 'awaiting_ack', challenge: { id: uuid, incarnation: uuid, session_id: uuid, revision: 2, expires_in_ms: 5000 } }) });
}

test('fragment credentials are immediately removed; read-only view never has controls or writes', async () => {
  const h = harness(`#view=${viewCapability}`), stop = start(h);
  assert.equal(h.win.location.hash, ''); assert.equal(h.win.history.url, '/market.html');
  assert.equal(h.calls[0].options.headers.Authorization, `Bearer ${viewCapability}`);
  await reply(h, snapshot()); assert.equal(h.root.querySelectorAll('button').length, 0); assert.equal(h.calls.length, 1);
  assert.ok(!h.root.textContent.includes('secret')); stop(); assert.equal(h.timers.size, 0);
  const missing = harness(''); start(missing)(); assert.equal(missing.calls.length, 0);
  const query = harness(''); query.win.location.search = '?operator=query-secret'; start(query)(); assert.equal(query.calls.length, 0);
});

test('test_hidden_and_disconnect_stop_ack: serial render before ACK, hidden abort and full reload', async () => {
  const h = harness(), stop = start(h); assert.equal(h.calls.length, 1);
  await reply(h, snapshot()); await claim(h);
  assert.equal(h.calls.at(-1).url, '/api/primary/ack'); assert.equal(h.root.querySelectorAll('li').length, 20);
  const late = h.pending.shift(); h.doc.hidden = true; h.doc.dispatch('visibilitychange');
  assert.equal(h.calls.at(-1).options.signal.aborted, true);
  late.resolve({ accepted: true, reason: 'acknowledged', snapshot: snapshot({ revision: 3, paused: false, primary_state: 'present' }) }); await flush();
  assert.ok(h.root.textContent.includes('Letzter bekannter Stand — aktuell unbekannt'));
  const count = h.calls.length; h.tick(1000); await flush(); assert.equal(h.calls.length, count);
  h.doc.hidden = false; h.doc.dispatch('visibilitychange'); await flush(); assert.equal(h.calls.at(-1).url, '/api/snapshot');
  await reply(h, snapshot({ revision: 4, primary_state: 'present', challenge: { id: uuid, incarnation: uuid, session_id: uuid, revision: 4, expires_in_ms: 5000 } }));
  assert.equal(h.calls.at(-1).url, '/api/primary/ack');
  await reply(h, { accepted: true, reason: 'acknowledged', snapshot: snapshot({ revision: 4, primary_state: 'present' }) });
  assert.equal(h.pending.length, 0); h.tick(1000); await flush(); assert.equal(h.calls.at(-1).url, '/api/snapshot');
  h.event('offline'); assert.ok(h.root.textContent.includes('Letzter bekannter Stand — aktuell unbekannt')); stop();
});

test('independent freshness timer expires display even while a poll is stuck', async () => {
  const h = harness(`#view=${viewCapability}`), stop = start(h); await reply(h, snapshot());
  h.tick(1000); await flush(); h.setNow(5000); h.tick(250); await flush();
  assert.ok(h.root.textContent.includes('Letzter bekannter Stand — aktuell unbekannt')); stop();
});

test('historical fixture outcome never replaces active rows and uncertain retry preserves request id', async () => {
  const h = harness(), stop = start(h); await reply(h, snapshot());
  h.button('Testvorschlag senden').dispatch('click'); await flush();
  const firstBody = JSON.parse(h.calls.at(-1).options.body); h.pending.shift().reject(new Error('lost response')); await flush();
  assert.ok(h.root.textContent.includes('Ergebnis unbekannt')); h.event('online'); await flush(); await reply(h, snapshot({ revision: 7 }));
  h.button('Ungewisse Aktion wiederholen').dispatch('click'); await flush(); assert.equal(JSON.parse(h.calls.at(-1).options.body).request_id, firstBody.request_id);
  await reply(h, result()); assert.ok(h.root.textContent.includes('Vergangenes Fixture-Ergebnis'));
  assert.ok(h.root.querySelectorAll('li').every(row => row.textContent.includes('CHF 4.00')));
  h.button('Testvorschlag senden').dispatch('click'); await flush(); assert.notEqual(JSON.parse(h.calls.at(-1).options.body).request_id, firstBody.request_id); stop();
});

test('accepted historical resume displays superseding pause; old-generation operator response ignored', async () => {
  const h = harness(), stop = start(h); await reply(h, snapshot());
  h.button('Fortsetzen').dispatch('click'); await flush();
  await reply(h, { result: { command_id: 'action-1', status: 'accepted', reason: 'resumed', terminal_revision: 2 }, snapshot: snapshot({ revision: 3, paused: true }), superseding_reason: 'operator_pause' });
  assert.ok(h.root.textContent.includes('Pausiert')); assert.ok(h.root.textContent.includes('Neuere Pause'));
  h.button('Fortsetzen').dispatch('click'); await flush(); const old = h.pending.shift();
  h.event('offline'); h.event('online'); await flush(); await reply(h, snapshot({ revision: 4, paused: true }));
  old.resolve({ result: { command_id: 'action-2', status: 'accepted', reason: 'resumed', terminal_revision: 5 }, snapshot: snapshot({ revision: 5, paused: false }), superseding_reason: null }); await flush();
  assert.ok(h.root.textContent.includes('Pausiert')); stop();
});

test('retired primary bearer falls back to fragment read capability and discovers restarted incarnation', async () => {
  const h = harness(), stop = start(h); await reply(h, snapshot()); await claim(h);
  await reply(h, { accepted: true, reason: 'acknowledged', snapshot: snapshot({ revision: 3, primary_state: 'present' }) });
  h.tick(1000); await flush(); assert.equal(h.calls.at(-1).options.headers.Authorization, `Bearer ${primaryCapability}`);
  h.pending.shift().resolve({ error: 'unauthorized' }, 401); await flush();
  h.tick(1000); await flush(); assert.equal(h.calls.at(-1).options.headers.Authorization, `Bearer ${operatorCapability}`);
  await reply(h, snapshot({ incarnation: '22222222-2222-4222-8222-222222222222', revision: 1 }));
  assert.equal(h.pending.length, 0); assert.ok(h.root.textContent.includes('Pausiert'));
  h.tick(1000); await flush(); assert.equal(h.calls.at(-1).options.headers.Authorization, `Bearer ${operatorCapability}`); stop();
});

test('cleanup removes handlers, aborts pending request and late response never redraws', async () => {
  const h = harness(), stop = start(h), pending = h.pending.shift(); stop(); const before = h.root.textContent;
  assert.equal(h.calls[0].options.signal.aborted, true); pending.resolve(snapshot({ paused: false })); await flush();
  assert.equal(h.root.textContent, before); assert.equal(h.timers.size, 0);
  assert.ok(Object.values(h.doc.listeners).every(listeners => listeners.size === 0));
  h.event('online'); h.doc.dispatch('visibilitychange'); assert.equal(h.calls.length, 1);
});

test('poll and operator writes never overlap and ACK self-transition does not form a loop', async () => {
  const h = harness(), stop = start(h); await reply(h, snapshot());
  h.tick(1000); await flush(); const before = h.calls.length;
  assert.equal(h.button('Fortsetzen').disabled, false, 'poll must preserve keyboard focus on operator controls');
  h.button('Fortsetzen').dispatch('click'); assert.equal(h.calls.length, before);
  await reply(h, snapshot()); assert.equal(h.calls.at(-1).url, '/api/resume');
  await reply(h, { result: { command_id: 'action-1', status: 'rejected', reason: 'board_absent', terminal_revision: 1 }, snapshot: snapshot(), superseding_reason: null });
  await claim(h);
  await reply(h, { accepted: true, reason: 'acknowledged', snapshot: snapshot({ revision: 3, primary_state: 'present' }) });
  assert.equal(h.pending.length, 0); assert.equal(h.calls.filter(call => call.url === '/api/primary/ack').length, 1); stop();
});

test('a failed ACK after successful claim does not mark the claim itself uncertain', async () => {
  const h = harness(), stop = start(h); await reply(h, snapshot()); await claim(h);
  h.pending.shift().reject(new Error('ACK response lost')); await flush();
  assert.ok(h.root.textContent.includes('Letzter bekannter Stand — aktuell unbekannt'));
  h.event('online'); await flush(); await reply(h, snapshot({ revision: 3, primary_state: 'present' }));
  assert.equal(h.button('Ungewisse Aktion wiederholen').hidden, true); stop();
});

test('valid fixture rejection and no-change feedback remain historical without rendering target as price', async () => {
  const h = harness(), stop = start(h); await reply(h, snapshot());
  for (const [status, reason] of [['rejected', 'paused'], ['no_change', 'no_change']]) {
    h.button('Testvorschlag senden').dispatch('click'); await flush();
    await reply(h, result({ status, reason, activation_id: null, drink_version: 0, current_rappen: 400 }));
    assert.ok(h.root.textContent.includes(`Vergangenes Fixture-Ergebnis: ${status} (${reason})`));
    assert.ok(h.root.querySelectorAll('li').every(row => row.textContent.includes('CHF 4.00')));
  }
  stop();
});
