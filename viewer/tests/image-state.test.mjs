import assert from 'node:assert/strict';
import test from 'node:test';
import { status, intake, incarnation, id, hash } from './image-fixtures.mjs';
const api = await import('../../market/web/image-state.ts').catch(() => ({}));
function fn(name) { assert.equal(typeof api[name], 'function', `${name} missing`); return api[name]; }

test('approval needs a painted exact tuple and metadata younger than five seconds; rejection does not need pixels', () => {
  const create = fn('createImageState'), adopt = fn('adoptOperatorState'), painted = fn('adoptPaintedPreview'), gates = fn('moderationGates');
  let value = adopt(create(), intake(), 100, 0);
  assert.deepEqual(gates(value, 100), { approve: false, reject: true });
  value = painted(value, { incarnation, id, frame_sha256: hash }, 0);
  assert.deepEqual(gates(value, 5099), { approve: true, reject: true });
  assert.deepEqual(gates(value, 5100), { approve: false, reject: false });
  value = adopt(value, intake({ pending: status({ frame_sha256: 'b'.repeat(64) }) }), 200, value.generation);
  assert.deepEqual(gates(value, 200), { approve: false, reject: true });
});

test('late preview cannot make stale metadata fresh; changed identity and mutation clear painted tuple', () => {
  const create = fn('createImageState'), adopt = fn('adoptOperatorState'), painted = fn('adoptPaintedPreview'), invalidate = fn('invalidatePreview');
  let value = adopt(create(), intake(), 0, 0);
  value = painted(value, { incarnation, id, frame_sha256: hash }, 0);
  assert.equal(value.receivedAtMs, 0);
  assert.equal(fn('moderationGates')(value, 5000).approve, false);
  assert.equal(invalidate(value).painted, null);
  value = adopt(value, intake({ pending: status({ id: '33333333-3333-4333-8333-333333333333' }) }), 1, value.generation);
  assert.equal(value.painted, null);
});
