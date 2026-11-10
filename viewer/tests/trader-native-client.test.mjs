import assert from 'node:assert/strict';
import test from 'node:test';
import { native } from './native-fixtures.test.mjs';
import { startNative } from '../../market/web/image-main.ts';
class Element {
  constructor(ownerDocument) { this.ownerDocument = ownerDocument; this.children = []; this.listeners = {}; this.attributes = {}; this._text = ''; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  append(...children) { this.children.push(...children); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, callback) { (this.listeners[key] ??= new Set()).add(callback); }
  removeEventListener(key, callback) { this.listeners[key]?.delete(callback); }
  dispatch(key) { for (const callback of this.listeners[key] ?? []) callback(); }
}
function fixture(fetch) {
  const document = new Element(null), timers = new Map(); let next = 0;
  document.createElement = () => new Element(document); document.hidden = false;
  const window = new Element(document); Object.assign(window, { document, fetch, now: 0, navigator: { onLine: true },
    performance: { now: () => window.now }, setTimeout(callback, delay) { timers.set(++next, { callback, delay }); return next; }, clearTimeout(id) { timers.delete(id); } });
  document.defaultView = window;
  return { root: document.createElement('main'), window, timers };
}
async function until(predicate) { const end = performance.now() + 2000; while (!predicate() && performance.now() < end) await new Promise(resolve => setImmediate(resolve)); assert.ok(predicate()); }

test('optional native presentation receives parsed state and clears input on disconnect without changing default requests', async () => {
  let observed = null; const frames = [], calls = [];
  const h = fixture(async path => { calls.push(path); return path === '/api/native/state' ? Response.json(native({ input_kind: 'black', image_id: null })) : new Response('', { status: 404 }); });
  const client = startNative(h.root, 'A'.repeat(43), { onState: value => { observed = value; }, onFrame: value => frames.push(value) });
  await until(() => observed?.snapshot !== null && observed !== null);
  assert.deepEqual(calls, ['/api/native/state']);
  h.window.dispatch('offline'); assert.equal(observed.disconnected, true);
  assert.equal(frames.at(-1), null); client.dispose(); assert.equal(h.timers.size, 0);
});

async function rgbFixture() {
  const { createHash, webcrypto } = await import('node:crypto');
  const pixels = new Uint8Array(12288).fill(9);
  const prefix = '{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n';
  const hash = createHash('sha256').update(prefix).update(pixels).digest('hex');
  const measured = native({ frame_sha256: hash });
  const frame = { schema: 'market-native-frame/v1', incarnation: measured.incarnation, worker_session: measured.worker_session,
    observations_completed: measured.observations_completed, input_kind: measured.input_kind, image_id: measured.image_id,
    frame_sha256: hash, rgb_base64: Buffer.from(pixels).toString('base64') };
  return { pixels, measured, frame, webcrypto };
}

test('current-frame client verifies real RGB digest before exposing exact measured pixels', async () => {
  const data = await rgbFixture(), frames = [], calls = [];
  const h = fixture(async (path, options) => { calls.push({ path, options }); return Response.json(path === '/api/native/state' ? data.measured : data.frame); });
  h.window.crypto = data.webcrypto; h.window.atob = atob;
  const client = startNative(h.root, 'A'.repeat(43), { onState() {}, onFrame: value => frames.push(value) });
  await until(() => frames.some(Boolean));
  const painted = frames.find(Boolean); assert.deepEqual(painted.pixels, data.pixels);
  assert.equal(painted.observations_completed, 1); assert.equal(painted.frame_sha256, data.frame.frame_sha256);
  assert.equal(calls.filter(call => call.path === '/api/native/frame').length, 1);
  assert.equal(calls.at(-1).options.headers.Authorization, `Bearer ${'A'.repeat(43)}`);
  client.dispose(); assert.equal(frames.at(-1), null); assert.equal(h.timers.size, 0);
});

test('wrong digest never exposes RGB even when server and native metadata agree', async () => {
  const data = await rgbFixture(), frames = []; let digests = 0;
  data.measured.frame_sha256 = data.frame.frame_sha256 = 'b'.repeat(64);
  const h = fixture(async path => Response.json(path === '/api/native/state' ? data.measured : data.frame));
  h.window.atob = atob; h.window.crypto = { subtle: { async digest(...args) { const value = await data.webcrypto.subtle.digest(...args); digests++; return value; } } };
  const client = startNative(h.root, 'A'.repeat(43), { onState() {}, onFrame: value => frames.push(value) });
  await until(() => digests === 1); await new Promise(resolve => setImmediate(resolve));
  assert.equal(frames.some(Boolean), false); client.dispose();
});

for (const change of ['black', 'disconnect', 'replacement', 'dispose']) test(`deferred digest cannot repaint after ${change}`, async () => {
  const data = await rgbFixture(), frames = []; let release = null, observed = null, frameRequests = 0, current = data.measured;
  const h = fixture(async path => {
    if (path === '/api/native/state') return Response.json(current);
    frameRequests++; return Response.json(frameRequests === 1 ? data.frame : { ...data.frame, worker_session: current.worker_session, rgb_base64: null });
  });
  h.window.atob = atob;
  h.window.crypto = { subtle: { digest(...args) { return new Promise(resolve => { void data.webcrypto.subtle.digest(...args).then(value => { release = () => resolve(value); }); }); } } };
  const client = startNative(h.root, 'A'.repeat(43), { onState: value => { observed = value; }, onFrame: value => frames.push(value) });
  await until(() => release !== null);
  if (change === 'dispose') client.dispose();
  else if (change === 'disconnect') { h.window.navigator.onLine = false; h.window.dispatch('offline'); }
  else {
    current = change === 'black' ? native({ observations_completed: 2, model_ms: 1000, input_kind: 'black', image_id: null }) : native({ ...data.measured, worker_session: '44444444-4444-4444-8444-444444444444' });
    const timer = [...h.timers].find(([, value]) => value.delay === 2000); assert.ok(timer);
    h.timers.delete(timer[0]); timer[1].callback();
    await until(() => change === 'black' ? observed?.snapshot?.input_kind === 'black' : observed?.snapshot?.worker_session === current.worker_session);
  }
  release(); await new Promise(resolve => setImmediate(resolve)); await new Promise(resolve => setImmediate(resolve));
  assert.equal(frames.some(Boolean), false); client.dispose(); assert.equal(h.timers.size, 0);
});
