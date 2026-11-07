import assert from 'node:assert/strict';
import test from 'node:test';
import { frameAt, frameCount, quantizeVideoTick, writeFrames } from '../src/export.ts';
import { flyPose } from '../src/motion.ts';
import * as exportModule from '../src/export.ts';

test('terminal presentation clock advances independently while the measured sample stays fixed', () => {
  const first = frameAt(270, 90000, quantizeVideoTick, 90);
  const contact = frameAt(294, 90000, quantizeVideoTick, 90);
  assert.equal(first.holdElapsedTicks, 0);
  assert.equal(contact.holdElapsedTicks, 8000);
  assert.equal(first.tick, 90000); assert.equal(contact.tick, 90000);
  assert.equal(frameAt(269, 90000, quantizeVideoTick, 90).holdElapsedTicks, 0);
  assert.equal(typeof exportModule.advancePresentationPlayback, 'function');
  const state = exportModule.advancePresentationPlayback(89900, 810, 1, true, 90000, 30000);
  assert.equal(state.tick, 90000); assert.equal(state.holdElapsedTicks, 8000);
  assert.equal(state.playing, true); assert.equal(state.terminalHold, true);
  const paused = exportModule.advancePresentationPlayback(98000, 700, 1, false, 90000, 30000);
  assert.equal(paused.holdElapsedTicks, 8000);
  const ended = exportModule.advancePresentationPlayback(119000, 1000, 1, true, 90000, 30000);
  assert.equal(ended.tick, 90000); assert.equal(ended.holdElapsedTicks, 30000); assert.equal(ended.playing, false);
});

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

test('video presentation uses cumulative half-up ticks while preserving nominal PTS', () => {
  assert.equal(quantizeVideoTick(1), 333);
  assert.equal(quantizeVideoTick(2), 667);
  assert.equal(frameAt(2, 80000, quantizeVideoTick).tick, 667);
  assert.equal(frameAt(2, 80000, quantizeVideoTick).timestamp, 2 / 30);
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

test('event export holds only the terminal sample for 90 frames without extending source clocks', async () => {
  assert.equal(frameCount(20000, 90), 150);
  assert.equal(frameCount(20000), 75);
  const frames = [];
  await writeFrames(20000, {
    paint: (frame) => { frames.push(frame); }, add: async () => {},
    finalize: async () => true, cancel: async () => {},
  }, undefined, undefined, undefined, 90);
  assert.equal(frames.length, 150);
  assert.ok(frames.slice(0, 60).every((frame) => !frame.terminalHold && frame.tick < 20000));
  assert.ok(frames.slice(60).every((frame) => frame.terminalHold && frame.tick === 20000));
  assert.equal(frames.at(-1).timestamp + frames.at(-1).duration, 5);
  for (const hold of [-1, 0, 1.5, 91, Infinity]) assert.throws(() => frameCount(20000, hold));
});
