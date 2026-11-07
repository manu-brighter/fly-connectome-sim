import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

const sources = JSON.parse(readFileSync(new URL('../../src/fly_connectome_sim/neural/sources.lock.json', import.meta.url)));
const arrays = JSON.parse(readFileSync(new URL('../../src/fly_connectome_sim/neural/arrays.lock.json', import.meta.url)));
const recordingSha256 = 'a'.repeat(64), context = { recordingSha256, graphIdsSha256: arrays.ids };
const module = await import('../src/anatomy.ts').catch(() => ({}));
function api() { assert.equal(typeof module.parseAnatomy, 'function', 'Bound anatomy reader is missing'); return module; }
export function anatomyFixture(hash = recordingSha256) {
  return { version: 'replay-soma-anatomy/v1', source: { release: 'MaleCNS v1.0', annotations_sha256: sources['annotations.feather'].sha256, coordinate_field: 'somaLocation' },
    binding: { recording_sha256: hash, graph_ids_sha256: arrays.ids },
    coverage: { model_cells: 166700, positioned_cells: 2, missing_positions: 166698, displayed_cells: 2 },
    sampling: { method: 'ordered-position-stride/v1', limit: 12000 }, points: [[1, '101', 1, 2, 3], [7, '108', 8, 9, 10]] };
}

test('anatomy binds exact original recording bytes and preserves raw integer coordinates', async () => {
  const { parseAnatomy, readRecordingFile } = api();
  const raw = new Uint8Array([239, 187, 191, 123, 125, 10]);
  const read = await readRecordingFile({ arrayBuffer: async () => raw.buffer });
  assert.equal(read.text.trim(), '{}');
  assert.notEqual(read.sha256, await module.sha256Bytes(new TextEncoder().encode('{}').buffer));
  const value = anatomyFixture(); assert.deepEqual(parseAnatomy(JSON.stringify(value), context), value);
});

test('closed anatomy reader rejects wrong source/graph/recording, unsafe indices, coverage and oversize', () => {
  const { parseAnatomy } = api();
  const changes = [v => v.binding.recording_sha256 = 'b'.repeat(64), v => v.binding.graph_ids_sha256 = 'b'.repeat(64),
    v => v.source.annotations_sha256 = 'b'.repeat(64), v => v.source.release = 'other', v => v.source.coordinate_field = 'tosomaLocation',
    v => v.coverage.model_cells = 166701, v => v.coverage.missing_positions++, v => v.coverage.displayed_cells = 1,
    v => v.points[1][0] = 1, v => v.points[0][0] = -1, v => v.points[1][1] = '101', v => v.points[0][1] = '0',
    v => v.points[0][2] = true, v => v.points[0][2] = .5, v => v.points[0][2] = 1e30, v => v.points[0].push(3), v => v.extra = true];
  for (const change of changes) { const value = anatomyFixture(); change(value); assert.throws(() => parseAnatomy(JSON.stringify(value), context), undefined, String(change)); }
  assert.throws(() => parseAnatomy(' '.repeat(8 * 1024 * 1024 + 1), context));
  assert.throws(() => parseAnatomy(JSON.stringify(anatomyFixture()).replace('"version":', '"version":"duplicate","version":'), context));
});

test('stale asynchronous anatomy cannot attach to a different recording and zero positions stay empty', async () => {
  const { createAnatomyAttachment, parseAnatomy } = api();
  const attachment = createAnatomyAttachment(); attachment.setRecording(context);
  let finish; const pending = attachment.load(new Promise(resolve => { finish = resolve; }));
  attachment.setRecording({ ...context, recordingSha256: 'c'.repeat(64) }); finish(JSON.stringify(anatomyFixture()));
  assert.equal(await pending, false); assert.equal(attachment.value, null);
  const value = anatomyFixture('c'.repeat(64)); await attachment.load(Promise.resolve(JSON.stringify(value)));
  assert.deepEqual(attachment.value, value);
  attachment.setRecording(context); assert.equal(attachment.value, null);
  const empty = anatomyFixture(); empty.points = []; empty.coverage = { model_cells: 166700, positioned_cells: 0, missing_positions: 166700, displayed_cells: 0 };
  assert.deepEqual(parseAnatomy(JSON.stringify(empty), context).points, []);
});
