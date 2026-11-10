import assert from 'node:assert/strict';
import test from 'node:test';
import { intake } from './image-fixtures.mjs';
import { adoptOperatorState, createImageState } from '../../market/web/image-state.ts';
const api = await import('../../market/web/image-view.ts').catch(() => ({}));
function fn(name) { assert.equal(typeof api[name], 'function', `${name} missing`); return api[name]; }

test('canvas adopts exact RGB samples as opaque pixels and can clear the verified image', () => {
  const draw = fn('paintRgb'), clear = fn('clearPreview');
  let painted;
  const context = { putImageData(image, x, y) { painted = { image, x, y }; }, clearRect(x, y, w, h) { this.cleared = [x, y, w, h]; } };
  const canvas = { width: 64, height: 64, getContext(kind) { assert.equal(kind, '2d'); return context; },
    ownerDocument: { defaultView: { ImageData: class { constructor(data, width, height) { this.data = data; this.width = width; this.height = height; } } } } };
  const rgb = new Uint8Array(12288); rgb.set([12, 34, 56, 78, 90, 123]);
  assert.equal(draw(canvas, rgb), true);
  assert.deepEqual([...painted.image.data.slice(0, 8)], [12, 34, 56, 255, 78, 90, 123, 255]);
  assert.deepEqual([painted.x, painted.y, painted.image.width, painted.image.height], [0, 0, 64, 64]);
  clear(canvas); assert.deepEqual(context.cleared, [0, 0, 64, 64]);
});

test('fresh faulted and stopping intake reports unavailable state, while ready empty stays empty', () => {
  const render = fn('renderOperator');
  const view = { status: { textContent: '' }, timing: { textContent: '' }, approve: { disabled: true },
    reject: { disabled: true }, retry: { disabled: true, hidden: true },
    canvas: { hidden: true, getContext() { return { clearRect() {} }; } } };
  const cases = [
    [intake({ pending: null }), 'Kein Bild zur Prüfung.'],
    [intake({ health: 'faulted', fault: 'decoder', pending: null }), 'Bildannahme derzeit nicht verfügbar.'],
    [intake({ health: 'stopping', pending: null }), 'Lokaler Bildtest beendet.'],
  ];
  for (const [reply, expected] of cases) {
    render(view, adoptOperatorState(createImageState(), reply, 0, 0), 0);
    assert.equal(view.status.textContent, expected);
    assert.equal(view.approve.disabled, true); assert.equal(view.reject.disabled, true);
  }
});
