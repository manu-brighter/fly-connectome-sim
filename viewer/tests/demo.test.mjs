import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { demoFixture, demoFiles } from './session-replay.test.mjs';

const module = await import('../src/demo.ts').catch(() => ({}));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const bytes = value => new TextEncoder().encode(JSON.stringify(value));
function api() { assert.equal(typeof module.readDemoFiles, 'function', 'Combined demo reader is missing'); return module; }

test('demo validates arbitrary ordering and keeps exact snapshots with isolated loaded controllers', async () => {
  const f = demoFixture(), candidate = await api().readDemoFiles(demoFiles(f).reverse());
  assert.deepEqual(candidate.recording, f.recording);
  assert.deepEqual(Object.keys(candidate.snapshots).sort(), Object.keys(f.snapshots).sort());
  for (const [name, raw] of Object.entries(f.snapshots)) assert.deepEqual(candidate.snapshots[name], raw);
  assert.ok(candidate.anatomyAttachment.value); assert.ok(candidate.cellAttachment.value); assert.ok(candidate.followupAttachment.value);
  assert.deepEqual(candidate.followupAttachment.value.markdownBytes, f.followup.markdown);
});

test('demo rejects wrong sets, duplicates and role limits before reading any input', async () => {
  const { readDemoFiles, DEMO_LIMITS } = api(), f = demoFixture();
  let reads = 0;
  const files = demoFiles(f, async () => { reads++; throw new Error('Read forbidden'); });
  const variants = [files.slice(1), [...files, files[0]], files.map((file, i) => i ? file : { ...file, name: 'other.json' }), files.map((file, i) => i === 1 ? { ...file, name: files[0].name } : file)];
  for (const [name, limit] of Object.entries(DEMO_LIMITS)) for (const size of [0, -1, 1.5, NaN, limit + 1]) variants.push(files.map(file => file.name === name ? { ...file, size } : file));
  for (const variant of variants) await assert.rejects(readDemoFiles(variant));
  assert.equal(reads, 0);
});

test('demo rejects changed lengths, invalid UTF-8 and mixed exact-byte bindings', async () => {
  const { readDemoFiles } = api(), f = demoFixture();
  await assert.rejects(readDemoFiles(demoFiles(f, async raw => raw.slice(1).buffer)));
  const invalid = demoFiles(f).map(file => file.name === 'anatomy.json' ? { ...file, size: 1, arrayBuffer: async () => new Uint8Array([255]).buffer } : file);
  await assert.rejects(readDemoFiles(invalid));
  const mixed = demoFixture(); mixed.snapshots['recording.json'] = new TextEncoder().encode(new TextDecoder().decode(mixed.snapshots['recording.json']) + '\n');
  await assert.rejects(readDemoFiles(demoFiles(mixed)));
  const wrong = demoFixture(), anatomy = JSON.parse(new TextDecoder().decode(wrong.snapshots['anatomy.json'])); anatomy.binding.recording_sha256 = 'f'.repeat(64); wrong.snapshots['anatomy.json'] = bytes(anatomy);
  await assert.rejects(readDemoFiles(demoFiles(wrong)));
});

test('demo filenames identify companion roles, and each original file is read exactly once', async () => {
  const { readDemoFiles } = api(), f = demoFixture(), counts = {};
  await readDemoFiles(demoFiles(f, async (raw, name) => { counts[name] = (counts[name] ?? 0) + 1; return raw.buffer; }));
  assert.deepEqual(Object.values(counts), [1, 1, 1, 1, 1]);
  [f.snapshots['followup.json'], f.snapshots['receipt.json']] = [f.snapshots['receipt.json'], f.snapshots['followup.json']];
  await assert.rejects(readDemoFiles(demoFiles(f)));
});

test('demo captures file metadata before delayed reads rather than trusting caller mutation', async () => {
  const { readDemoFiles } = api(), f = demoFixture(); let release;
  const files = demoFiles(f, (raw, name) => name === 'receipt.json' ? new Promise(resolve => { release = () => resolve(raw.buffer); }) : Promise.resolve(raw.buffer));
  const pending = readDemoFiles(files), receipt = files.find(file => file.name === 'receipt.json');
  receipt.name = 'unexpected.json'; receipt.size = 0;
  release(); const candidate = await pending;
  assert.deepEqual(candidate.snapshots['receipt.json'], f.snapshots['receipt.json']); assert.equal(candidate.snapshots['unexpected.json'], undefined);
});
