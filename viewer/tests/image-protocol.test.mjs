import assert from 'node:assert/strict';
import test from 'node:test';
import { status, intake, receipt, hash } from './image-fixtures.mjs';
import { webcrypto } from 'node:crypto';
const api = await import('../../market/web/image-protocol.ts').catch(() => ({}));
function fn(name) { assert.equal(typeof api[name], 'function', `${name} missing`); return api[name]; }

test('strict status rejects extra fields, invalid scalar bounds and contradictory combinations', () => {
  const parse = fn('parseImageStatus'); assert.deepEqual(parse(status()), status());
  for (const changes of [{ measured_activity: 1 }, { revision: 7 }, { accepted_age_ms: 9223372036856 },
    { status: 'processed' }, { status: 'queued' }, { detail: 'ready' }, { preview_available: false },
    { time_uncertain: true }, { frame_sha256: hash.toUpperCase() }, { remaining_moderation_ms: -1 }]) {
    assert.throws(() => parse(status(changes)), `accepted ${JSON.stringify(changes)}`);
  }
  assert.deepEqual(parse(status({ status: 'queued', detail: 'ready' })).status, 'queued');
  assert.deepEqual(parse(status({ status: 'rejected', detail: 'moderation_rejected', preview_available: false,
    remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 })).detail, 'moderation_rejected');
});

test('closed detail vocabulary rejects inherited Object names for every status family', () => {
  const parse = fn('parseImageStatus');
  for (const detail of ['toString', 'constructor', '__proto__', 'hasOwnProperty', 'unknown']) {
    for (const candidate of [
      status({ detail, frame_sha256: null, preview_available: false }),
      status({ status: 'queued', detail, frame_sha256: null, preview_available: false }),
      status({ status: 'expired', detail, frame_sha256: null, preview_available: false,
        remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 }),
      status({ status: 'rejected', detail, frame_sha256: null, preview_available: false,
        remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 }),
    ]) assert.throws(() => parse(candidate), `${candidate.status}/${detail}`);
  }
  for (const candidate of [
    status({ status: 'accepted', detail: 'decoding', frame_sha256: null, preview_available: false }),
    status({ status: 'accepted', detail: 'awaiting_approval' }),
    status({ status: 'queued', detail: 'ready' }),
    status({ status: 'expired', detail: 'ttl_expired', preview_available: false,
      remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 }),
    ...['decode_failed', 'decode_timeout', 'moderation_rejected', 'moderation_timeout', 'worker_failed', 'session_ended', 'clock'].map(detail =>
      status({ status: 'rejected', detail, frame_sha256: detail.startsWith('decode') ? null : hash,
        preview_available: false, remaining_decode_ms: 0, remaining_moderation_ms: 0, remaining_handoff_ms: 0 })),
  ]) assert.equal(parse(candidate), candidate);
});

test('state and acceptance require exact nested schema, identity and health relationships', () => {
  const state = fn('parseIntakeState'), acceptance = fn('parseAcceptance');
  assert.deepEqual(state(intake()), intake());
  assert.deepEqual(acceptance({ schema: 'market-image-acceptance/v1', status_capability: receipt, image: status() }).image, status());
  for (const changes of [{ worker_connected: true }, { health: 'faulted' }, { receiving: true },
    { pending: status({ id: 'invalid' }) }, { pending: { ...status(), incarnation: '33333333-3333-4333-8333-333333333333' } },
    { health: 'stopping' }, { receipt_count: 513 }, { surprise: 1 }]) assert.throws(() => state(intake(changes)));
  assert.throws(() => acceptance({ schema: 'market-image-acceptance/v1', status_capability: receipt.slice(1), image: status() }));
});

test('bounded stream aborts extra JSON and RGB bytes while consuming, and rejects truncated RGB', async () => {
  const read = fn('readBoundedResponse');
  const bytes = new Uint8Array(12288);
  assert.equal((await read(new Response(bytes), 12288, true)).length, 12288);
  await assert.rejects(read(new Response(bytes.slice(1)), 12288, true));
  let cancelled = false;
  const source = new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(8192)); controller.enqueue(new Uint8Array(1)); }, cancel() { cancelled = true; } });
  await assert.rejects(read(new Response(source), 8192, false));
  assert.equal(cancelled, true);
});

test('canonical RGB digest binds prefix and exact bytes', async () => {
  const verify = fn('verifyRgb'), rgb = new Uint8Array(12288);
  rgb[0] = 17; rgb[1] = 99;
  const prefix = new TextEncoder().encode('{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n');
  const input = new Uint8Array(prefix.length + rgb.length); input.set(prefix); input.set(rgb, prefix.length);
  const digest = Buffer.from(await webcrypto.subtle.digest('SHA-256', input)).toString('hex');
  await verify(rgb, digest, webcrypto);
  await assert.rejects(verify(rgb, hash, webcrypto));
  await assert.rejects(verify(rgb.slice(1), digest, webcrypto));
});
