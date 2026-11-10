import assert from 'node:assert/strict';
import test from 'node:test';
import { webcrypto } from 'node:crypto';
import { status, intake, receipt, id, incarnation } from './image-fixtures.mjs';
import { imageV2, intakeV2, native, session } from './native-fixtures.test.mjs';
import { adoptNativeState, createNativeState } from '../../market/web/native-state.ts';
const api = await import('../../market/web/image-main.ts').catch(() => ({}));
function fn(name) { assert.equal(typeof api[name], 'function', `${name} missing`); return api[name]; }
class Element {
  constructor(tagName, ownerDocument) { this.tagName = tagName; this.ownerDocument = ownerDocument; this.children = []; this.listeners = {}; this.attributes = {}; this._text = ''; this.hidden = false; this.disabled = false; this.classList = { add() {} }; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(' '); }
  append(...children) { this.children.push(...children); }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(key, callback) { (this.listeners[key] ??= new Set()).add(callback); }
  removeEventListener(key, callback) { this.listeners[key]?.delete(callback); }
  dispatch(key) { for (const callback of this.listeners[key] ?? []) callback({ preventDefault() {} }); }
  getContext() { return this.context ??= { clearRect() { this.image = null; }, putImageData(image) { this.image = image; } }; }
}
function fixture(fragment, fetch) {
  const doc = { defaultView: null, hidden: false, createElement(tag) { return new Element(tag, doc); }, listeners: {},
    addEventListener(key, cb) { (this.listeners[key] ??= new Set()).add(cb); }, removeEventListener(key, cb) { this.listeners[key]?.delete(cb); } };
  const listeners = {}, window = { location: { hash: fragment, pathname: '/market-image.html', search: '' },
    history: { replaceState(_a, _b, path) { this.path = path; window.location.hash = ''; } },
    fetch, navigator: { onLine: true }, performance: { now: () => window.now ?? 0 }, crypto: { ...webcrypto, subtle: webcrypto.subtle, randomUUID: () => '33333333-3333-4333-8333-333333333333' },
    setTimeout() { return 1; }, clearTimeout() {},
    addEventListener(key, cb) { (listeners[key] ??= new Set()).add(cb); }, removeEventListener(key, cb) { listeners[key]?.delete(cb); },
    dispatch(key) { for (const cb of listeners[key] ?? []) cb(); } };
  window.ImageData = class { constructor(data, width, height) { Object.assign(this, { data, width, height }); } };
  doc.defaultView = window; window.document = doc; return { root: new Element('main', doc), window };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
function elements(root, tag) { return root.children.flatMap(child => [ ...(child.tagName === tag ? [child] : []), ...elements(child, tag) ]); }
test('guest removes fragment before network and sends nothing until a valid file is selected', () => {
  const calls = []; const { root, window } = fixture(`#guest=ig.${'A'.repeat(43)}`, (...args) => { calls.push(args); throw new Error('unexpected'); });
  const dispose = fn('startGuest')(root);
  assert.equal(window.location.hash, ''); assert.equal(window.history.path, '/market-image.html'); assert.equal(calls.length, 0);
  assert.ok(root.textContent.includes('Verbindung wird beim Senden geprüft'));
  assert.equal(root.children.some(item => item.tagName === 'canvas' || item.tagName === 'img'), false);
  dispose();
});
test('invalid guest capability has no request or persistent credential', () => {
  const calls = []; const { root } = fixture('#guest=bad', (...args) => { calls.push(args); });
  const dispose = fn('startGuest')(root);
  assert.equal(calls.length, 0); assert.ok(root.textContent.includes('Bildzugang fehlt oder ist ungültig'));
  dispose();
});
test('operator start probes state independently and hides optional pane on 404', async () => {
  const calls = [], { root } = fixture('', async (path, options) => { calls.push([path, options]); return new Response('', { status: 404 }); });
  const dispose = fn('startOperatorImage')(root, 'A'.repeat(43));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.length, 1); assert.equal(calls[0][0], '/api/images/state');
  assert.equal(root.children[0].hidden, true);
  dispose();
});

test('lost upload response leaves no receipt poll and never resends', async () => {
  const calls = [], { root } = fixture(`#guest=ig.${'A'.repeat(43)}`, async path => { calls.push(path); throw new Error('lost response'); });
  const dispose = fn('startGuest')(root);
  const file = elements(root, 'input')[0], send = elements(root, 'button')[0];
  file.files = [new File(['abc'], 'private.png', { type: 'image/png' })]; send.dispatch('click'); await flush();
  assert.deepEqual(calls, ['/api/images']); assert.equal(send.disabled, true);
  assert.ok(root.textContent.includes('nicht automatisch erneut gesendet'));
  send.dispatch('click'); await flush(); assert.equal(calls.length, 1);
  dispose();
});

test('guest accepts only current receipt status identity and exposes no pixels or filename', async () => {
  const calls = [], { root } = fixture(`#guest=ig.${'A'.repeat(43)}`, async (path, options) => {
    calls.push([path, options]);
    if (path === '/api/images') return Response.json({ schema: 'market-image-acceptance/v1', status_capability: receipt,
      image: status({ status: 'accepted', detail: 'decoding', frame_sha256: null, preview_available: false }) }, { status: 202 });
    return Response.json(status({ id: '33333333-3333-4333-8333-333333333333' }));
  });
  const dispose = fn('startGuest')(root), file = elements(root, 'input')[0];
  file.files = [new File(['abc'], 'private.png', { type: 'image/png' })]; elements(root, 'button')[0].dispatch('click'); await flush();
  assert.equal(calls.length, 1); assert.equal(calls[0][0], '/api/images');
  assert.equal(calls[0][1].headers.Authorization, `Bearer ig.${'A'.repeat(43)}`);
  assert.equal(calls[0][1].body, file.files[0]);
  assert.ok(!root.textContent.includes('private.png')); assert.equal(elements(root, 'canvas').length, 0);
  dispose();
});

test('operator paints verified RGB and approval uses current tuple only', async t => {
  const rgb = new Uint8Array(12288); rgb.set([1, 2, 3]);
  const prefix = new TextEncoder().encode('{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n'); const bytes = new Uint8Array(prefix.length + rgb.length);
  bytes.set(prefix); bytes.set(rgb, prefix.length);
  const digest = Buffer.from(await webcrypto.subtle.digest('SHA-256', bytes)).toString('hex');
  const calls = [], { root, window } = fixture('', async (path, options) => {
    calls.push([path, options]);
    if (path === '/api/images/state') return Response.json(intake({ pending: status({ frame_sha256: digest }) }));
    if (path.startsWith('/api/images/preview/')) return new Response(rgb);
    if (path.startsWith('/api/images/moderate/')) return Response.json(status({ status: 'queued', detail: 'ready', frame_sha256: digest }));
    throw new Error('unexpected');
  });
  const digestStarted = Promise.withResolvers(), releaseDigest = Promise.withResolvers();
  window.crypto.subtle = { async digest(...args) {
    digestStarted.resolve(); await releaseDigest.promise; return webcrypto.subtle.digest(...args);
  } };
  const dispose = fn('startOperatorImage')(root, 'A'.repeat(43));
  t.after(() => { releaseDigest.resolve(); dispose(); });
  const canvas = elements(root, 'canvas')[0], [approve, reject] = elements(root, 'button');
  const painted = Promise.withResolvers(), context = canvas.getContext('2d');
  const putImageData = context.putImageData.bind(context);
  context.putImageData = (...args) => { putImageData(...args); painted.resolve(); };
  await digestStarted.promise;
  assert.equal(context.image, null); assert.equal(approve.disabled, true);
  releaseDigest.resolve(); await painted.promise;
  assert.deepEqual([...canvas.context.image.data.slice(0, 4)], [1, 2, 3, 255]);
  assert.equal(approve.disabled, false); assert.equal(reject.disabled, false);
  window.now = 5000; approve.dispatch('click'); await flush();
  assert.equal(calls.filter(([path]) => path.startsWith('/api/images/moderate/')).length, 0);
});

test('upload keeps the original abort deadline active through the bounded acceptance body', async () => {
  const { root, window } = fixture(`#guest=ig.${'A'.repeat(43)}`, async () => new Response(new ReadableStream({ start(controller) {
    controller.enqueue(new TextEncoder().encode('{'));
  } }), { status: 202 }));
  const active = new Set(); let nextTimer = 0;
  window.setTimeout = callback => { const key = ++nextTimer; active.add(key); return key; };
  window.clearTimeout = key => active.delete(key);
  const dispose = fn('startGuest')(root), file = elements(root, 'input')[0];
  file.files = [new File(['abc'], 'private.png', { type: 'image/png' })]; elements(root, 'button')[0].dispatch('click'); await flush();
  assert.equal(active.has(1), true, 'one request deadline must remain live while reading the response body');
  dispose();
});

test('preview failure blocks approval while rejection and same-action explicit retry remain available', async () => {
  const calls = [], { root } = fixture('', async (path, options) => {
    calls.push([path, options]);
    if (path === '/api/images/state') return Response.json(intake());
    if (path.startsWith('/api/images/preview/')) return new Response('', { status: 404 });
    if (path.startsWith('/api/images/moderate/')) throw new Error('lost moderation response');
  });
  const dispose = fn('startOperatorImage')(root, 'A'.repeat(43));
  const [approve, reject, retry] = elements(root, 'button');
  for (let i = 0; i < 20 && !root.textContent.includes('Vorschau nicht verfügbar'); i++) await flush();
  assert.equal(approve.disabled, true); assert.equal(reject.disabled, false);
  reject.dispatch('click');
  for (let i = 0; i < 20 && retry.hidden; i++) await flush();
  assert.equal(retry.hidden, false);
  const first = calls.find(([path]) => path.startsWith('/api/images/moderate/'));
  assert.deepEqual(JSON.parse(first[1].body), { incarnation, action_id: '33333333-3333-4333-8333-333333333333', approved: false });
  for (let i = 0; i < 20 && retry.disabled; i++) await flush();
  retry.dispatch('click'); await flush();
  const moderation = calls.filter(([path]) => path.startsWith('/api/images/moderate/'));
  assert.equal(moderation.length, 2);
  assert.equal(moderation[1][1].body, moderation[0][1].body);
  dispose();
});

test('late preview after offline never paints or enables approval', async () => {
  let resolvePreview; const { root, window } = fixture('', async path => {
    if (path === '/api/images/state') return Response.json(intake());
    return new Promise(resolve => { resolvePreview = resolve; });
  });
  const dispose = fn('startOperatorImage')(root, 'A'.repeat(43));
  for (let i = 0; i < 20 && !resolvePreview; i++) await flush();
  window.navigator.onLine = false; window.dispatch('offline');
  resolvePreview(new Response(new Uint8Array(12288)));
  await flush(); await flush();
  assert.equal(elements(root, 'canvas')[0].hidden, true);
  assert.equal(elements(root, 'button')[0].disabled, true);
  dispose();
});

test('guest does not adopt a late 202 after upload was interrupted offline', async () => {
  let resolveUpload; const { root, window } = fixture(`#guest=ig.${'A'.repeat(43)}`,
    () => new Promise(resolve => { resolveUpload = resolve; }));
  const dispose = fn('startGuest')(root), file = elements(root, 'input')[0];
  file.files = [new File(['abc'], 'private.png', { type: 'image/png' })];
  const send = elements(root, 'button')[0]; send.dispatch('click'); await flush();
  window.navigator.onLine = false; window.dispatch('offline');
  resolveUpload(Response.json({ schema: 'market-image-acceptance/v1', status_capability: receipt,
    image: status({ status: 'accepted', detail: 'decoding', frame_sha256: null, preview_available: false }) }, { status: 202 }));
  await flush();
  assert.equal(send.disabled, true);
  assert.ok(root.textContent.includes('nicht automatisch erneut gesendet'));
  dispose();
});

test('reject retry is withdrawn if current pending hash changes under the same id', async () => {
  let pendingHash = 'a'.repeat(64);
  const { root } = fixture('', async path => {
    if (path === '/api/images/state') return Response.json(intake({ pending: status({ frame_sha256: pendingHash }) }));
    if (path.startsWith('/api/images/preview/')) return new Response('', { status: 404 });
    pendingHash = 'b'.repeat(64); throw new Error('lost moderation response');
  });
  const dispose = fn('startOperatorImage')(root, 'A'.repeat(43));
  const [, reject, retry] = elements(root, 'button');
  for (let i = 0; i < 20 && reject.disabled; i++) await flush();
  reject.dispatch('click');
  for (let i = 0; i < 20 && pendingHash === 'a'.repeat(64); i++) await flush();
  for (let i = 0; i < 20; i++) await flush();
  assert.equal(retry.hidden, true);
  dispose();
});

test('superseded moderation success releases its own latch without adopting old result over a new image', async () => {
  let finishOld, activeId = id;
  const calls = [], { root, window } = fixture('', async (path, options) => {
    calls.push([path, options]);
    if (path === '/api/images/state') return Response.json(intake({ pending: status({ id: activeId }) }));
    if (path.startsWith('/api/images/preview/')) return new Response('', { status: 404 });
    if (path.startsWith('/api/images/moderate/')) {
      if (!finishOld) return new Promise(resolve => { finishOld = () => resolve(Response.json(status({
        status: 'rejected', detail: 'moderation_rejected', preview_available: false,
        remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0,
      }))); });
      return Response.json(status({ id: activeId, status: 'rejected', detail: 'moderation_rejected',
        preview_available: false, remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 }));
    }
  });
  const dispose = fn('startOperatorImage')(root, 'A'.repeat(43));
  const [, reject] = elements(root, 'button');
  for (let i = 0; i < 20 && reject.disabled; i++) await flush();
  reject.dispatch('click'); for (let i = 0; i < 20 && !finishOld; i++) await flush();
  window.navigator.onLine = false; window.dispatch('offline');
  activeId = '33333333-3333-4333-8333-333333333333';
  window.navigator.onLine = true; window.dispatch('online'); finishOld();
  for (let i = 0; i < 30 && reject.disabled; i++) await flush();
  assert.equal(reject.disabled, false, 'new healthy pending image must not inherit old mutation latch');
  assert.ok(!root.textContent.includes('Bild abgelehnt.'));
  reject.dispatch('click'); await flush();
  assert.equal(calls.filter(([path]) => path === `/api/images/moderate/${activeId}`).length, 1);
  dispose();
});

test('guest v2 acceptance and genuine-shaped completion use strict progress copy without price promises', async () => {
  const { root, window } = fixture(`#guest=ig.${'A'.repeat(43)}`, async path => {
    if (path === '/api/images') return Response.json({ schema: 'market-image-acceptance/v2', status_capability: receipt,
      image: imageV2({ detail: 'decoding', frame_sha256: null, preview_available: false }) }, { status: 202 });
    assert.equal(path, `/api/images/status/${id}`);
    return Response.json(imageV2({ revision: 6, status: 'processed', detail: 'completed', worker_session: session,
      first_observation_index: 1, completed_observations: 8, observation_revision: 9, preview_available: false,
      remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 }));
  });
  const dispose = fn('startGuest')(root), file = elements(root, 'input')[0], send = elements(root, 'button')[0];
  file.files = [new File(['abc'], 'private.png', { type: 'image/png' })]; send.dispatch('click'); await flush();
  assert.ok(root.textContent.includes('Preise weiterhin synthetisch'));
  window.dispatch('online'); await flush();
  assert.ok(root.textContent.includes('8/8 Modellintervalle verarbeitet')); assert.equal(send.disabled, false);
  dispose();
});

test('fresh v2 moderation cannot mutate after the independent native transport reaches 5s', async () => {
  const calls = [], { root, window } = fixture('', async path => {
    calls.push(path);
    if (path === '/api/images/state') return Response.json(intakeV2());
    if (path.startsWith('/api/images/preview/')) return new Response('', { status: 404 });
    throw new Error('unexpected mutation');
  });
  const measured = adoptNativeState(createNativeState(), native(), 0, 0);
  const dispose = fn('startOperatorImage')(root, 'A'.repeat(43), () => measured);
  const [, reject] = elements(root, 'button');
  for (let i = 0; i < 20 && reject.disabled; i++) await flush();
  assert.equal(reject.disabled, false);
  window.now = 5000; reject.dispatch('click'); await flush();
  assert.equal(calls.some(path => path.startsWith('/api/images/moderate/')), false);
  dispose();
});

test('live guest receipt changes the scope honestly and keeps later completion progress', async () => {
  const { root, window } = fixture(`#guest=ig.${'A'.repeat(43)}`, async path => {
    if (path === '/api/images') return Response.json({ schema: 'market-image-acceptance/v3', status_capability: receipt,
      image: imageV2({ schema: 'market-image-status-wire/v3', detail: 'decoding', frame_sha256: null, preview_available: false }) }, { status: 202 });
    return Response.json(imageV2({ schema: 'market-image-status-wire/v3', revision: 6, status: 'processed', detail: 'completed', worker_session: session,
      first_observation_index: 50, completed_observations: 8, observation_revision: 58, preview_available: false,
      remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 }));
  });
  const dispose = fn('startGuest')(root), file = elements(root, 'input')[0], send = elements(root, 'button')[0];
  file.files = [new File(['abc'], 'private.png', { type: 'image/png' })]; send.dispatch('click'); await flush();
  assert.ok(root.textContent.includes('experimenteller konfigurierter Motor-Readout'));
  assert.ok(!root.textContent.includes('verändert hier keine Getränkepreise'));
  window.dispatch('online'); await flush();
  assert.ok(root.textContent.includes('8/8 Modellintervalle verarbeitet')); assert.equal(send.disabled, false);
  dispose();
});
