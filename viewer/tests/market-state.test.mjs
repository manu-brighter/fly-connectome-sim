import assert from 'node:assert/strict';
import test from 'node:test';
import { snapshot, uuid } from './market-fixtures.mjs';
const module = await import('../../market/web/state.ts').catch(() => ({}));
function api() { assert.equal(typeof module.createState, 'function'); return module; }

test('board starts unknown and freshness expires exactly at 5000ms', () => {
  const { createState, applySnapshot, isFresh } = api();
  const empty = createState(); assert.equal(empty.unknown, true); assert.equal(empty.snapshot, null); assert.equal(isFresh(empty, 0), false);
  const state = applySnapshot(empty, snapshot(), 100, 0);
  assert.equal(isFresh(state, 5099), true); assert.equal(isFresh(state, 5100), false); assert.equal(isFresh(state, 99), false);
});

test('lower revision and old connection generation cannot refresh or replace current rows', () => {
  const { createState, applySnapshot, disconnect, isFresh } = api();
  const current = applySnapshot(createState(), snapshot({ revision: 5 }), 100, 0);
  assert.equal(applySnapshot(current, snapshot({ revision: 4 }), 200, 0), current);
  const offline = disconnect(current); assert.equal(offline.connectionGeneration, 1); assert.equal(offline.unknown, true);
  assert.equal(offline.snapshot, current.snapshot); assert.equal(isFresh(offline, 101), false);
  assert.equal(applySnapshot(offline, snapshot({ revision: 6 }), 200, 0), offline);
});

test('new connection full snapshot resets incarnation, generation and primary credentials', () => {
  const { createState, applySnapshot } = api();
  const first = applySnapshot(createState(), snapshot({ revision: 9 }), 10, 0);
  first.primarySession = { session_id: uuid, primary_token: 'old-secret' };
  const next = applySnapshot(first, snapshot({ incarnation: '22222222-2222-4222-8222-222222222222', revision: 0 }), 20, 0);
  assert.equal(next.snapshot.revision, 0); assert.equal(next.connectionGeneration, 1); assert.equal(next.primarySession, null);
  assert.equal(applySnapshot(next, snapshot({ revision: 99 }), 30, 0), next);
});
