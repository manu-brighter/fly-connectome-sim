import assert from 'node:assert/strict';
import test from 'node:test';
import { createOperationGate } from '../src/operation.ts';

test('pending file load prevents export until the newest load completes', async () => {
  const gate = createOperationGate();
  let finishFirst, finishSecond;
  const first = new Promise((resolve) => { finishFirst = resolve; });
  const second = new Promise((resolve) => { finishSecond = resolve; });
  const firstToken = gate.beginLoad();
  assert.equal(gate.beginExport(), false);
  const secondToken = gate.beginLoad();
  assert.equal(gate.isCurrentLoad(firstToken), false);
  finishFirst(); await first;
  gate.endLoad(firstToken);
  assert.equal(gate.beginExport(), false);
  finishSecond(); await second;
  assert.equal(gate.isCurrentLoad(secondToken), true);
  gate.endLoad(secondToken);
  assert.equal(gate.beginExport(), true);
  gate.endExport();
});

test('export rejects a queued file change until it finishes', () => {
  const gate = createOperationGate();
  assert.equal(gate.beginExport(), true);
  assert.equal(gate.beginLoad(), null);
  gate.endExport();
  const token = gate.beginLoad();
  assert.equal(gate.isCurrentLoad(token), true);
});
