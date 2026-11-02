import assert from 'node:assert/strict';
import test from 'node:test';
import { frameAt, writeFrames } from '../src/export.ts';
import { flyPose } from '../src/motion.ts';

test('12 second export has 360 source samples and 15 terminal presentation frames', () => {
  const frames = Array.from({ length: 375 }, (_, index) => frameAt(index, 120000));
  assert.equal(frames[0].tick, 0);
  assert.equal(frames[359].tick, 119666);
  assert.equal(frames[360].tick, 120000);
  assert.ok(frames.slice(360).every((frame) => frame.tick === 120000 && frame.terminalHold));
  assert.ok(frames.slice(0, 360).every((frame) => !frame.terminalHold));
  assert.equal(frames.at(-1).timestamp + frames.at(-1).duration, 12.5);
  assert.ok(frames.every((frame) => frame.duration === 1 / 30));
});

test('writer awaits every frame and finalizes only after all frames', async () => {
  const events = [];
  const result = await writeFrames(10000, {
    paint: async (frame) => { events.push(`paint ${frame.index}`); },
    add: async (timestamp, duration) => { events.push(`add ${timestamp} ${duration}`); },
    finalize: async () => { events.push('finalize'); return 'video'; },
    cancel: async () => { events.push('cancel'); },
  });
  assert.equal(result, 'video');
  assert.equal(events.at(-1), 'finalize');
  assert.equal(events.filter((event) => event.startsWith('add')).length, 45);
});

test('cancellation and encoding error never finalize and release writer', async () => {
  for (const failure of ['cancel', 'error']) {
    const events = [], controller = new AbortController();
    await assert.rejects(writeFrames(10000, {
      paint: async () => { if (failure === 'cancel') controller.abort(); else throw new Error('encode failure'); },
      add: async () => events.push('add'),
      finalize: async () => events.push('finalize'),
      cancel: async () => events.push('cancel'),
    }, controller.signal));
    assert.deepEqual(events, ['cancel']);
  }
});

test('illustrative pose depends on absolute replay time and reduced motion', () => {
  assert.deepEqual(flyPose(2500, false), flyPose(2500, false));
  assert.notDeepEqual(flyPose(2500, false), flyPose(5000, false));
  assert.deepEqual(flyPose(2500, true), flyPose(5000, true));
});
