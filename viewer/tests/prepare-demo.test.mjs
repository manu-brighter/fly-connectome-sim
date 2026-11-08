import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, mkdir, rmdir, readFile, readdir, writeFile, symlink, lstat, open } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { demoFixture } from './session-replay.test.mjs';
const module = await import('../../scripts/prepare-demo.mjs').catch(() => ({}));
function api() { assert.equal(typeof module.prepareDemo, 'function', 'Demo preparation command is missing'); return module; }
async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), 'fly-demo-')), f = demoFixture();
  for (const [name, raw] of Object.entries(f.snapshots)) await writeFile(join(directory, name), raw);
  return { ...f, directory, paths: { recording: join(directory, 'recording.json'), cellActivity: join(directory, 'cell-activity.json'), anatomy: join(directory, 'anatomy.json'), followupDir: directory, outputDir: join(directory, 'prepared') } };
}

test('prepare demo writes only five checked exact snapshots and refuses an existing output', async () => {
  const { prepareDemo } = api(), f = await fixture();
  await prepareDemo(f.paths);
  assert.deepEqual((await readdir(f.paths.outputDir)).sort(), Object.keys(f.snapshots).sort());
  for (const [name, raw] of Object.entries(f.snapshots)) assert.deepEqual(new Uint8Array(await readFile(join(f.paths.outputDir, name))), raw);
  await assert.rejects(prepareDemo(f.paths));
  await writeFile(join(f.paths.outputDir, 'sentinel'), 'retained');
  await assert.rejects(prepareDemo(f.paths)); assert.equal(await readFile(join(f.paths.outputDir, 'sentinel'), 'utf8'), 'retained');
});

test('prepare demo invalid bindings, nonfiles, oversized input and absent parent create no output', async () => {
  const { prepareDemo } = api();
  for (const mutate of [async f => writeFile(f.paths.anatomy, '{}'), async f => { f.paths.anatomy = f.directory; }, async f => { const handle = await open(f.paths.anatomy, 'w'); try { await handle.truncate(8 * 1024 * 1024 + 1); } finally { await handle.close(); } }, async f => { f.paths.outputDir = join(f.directory, 'missing', 'prepared'); }]) {
    const f = await fixture(); await mutate(f); await assert.rejects(prepareDemo(f.paths)); await assert.rejects(lstat(f.paths.outputDir), { code: 'ENOENT' });
  }
});

test('prepare demo refuses dangling output links without changing them', async t => {
  const { prepareDemo } = api(), f = await fixture();
  const target = join(f.directory, 'target'); await mkdir(target);
  try { await symlink(target, f.paths.outputDir, 'junction'); } catch (error) { if (['EPERM', 'EACCES'].includes(error.code)) { t.skip('Link creation is unavailable'); return; } throw error; }
  await rmdir(target);
  await assert.rejects(prepareDemo(f.paths)); assert.equal((await lstat(f.paths.outputDir)).isSymbolicLink(), true);
});

test('prepare demo bounds actual handle reads and rejects growth and truncation', async () => {
  const { readBoundedHandle } = api(); assert.equal(typeof readBoundedHandle, 'function');
  for (const length of [1, 2, 3]) {
    let offset = 0, requested = 0;
    const stat = { size: 2, mtimeMs: 1, isFile: () => true };
    const handle = { stat: async () => stat, read: async (buffer, start, count) => { requested += count; const n = Math.min(count, length - offset); buffer.fill(32, start, start + n); offset += n; return { bytesRead: n }; } };
    if (length === 2) assert.equal((await readBoundedHandle(handle, 'receipt.json')).length, 2);
    else await assert.rejects(readBoundedHandle(handle, 'receipt.json'));
    assert.ok(offset <= 3); assert.ok(requested <= 6, 'Reads must stay inside the size + one buffer');
  }
});

test('prepare demo CLI requires all explicit paths and never starts work on unknown flags', () => {
  const result = spawnSync(process.execPath, [new URL('../../scripts/prepare-demo.mjs', import.meta.url).pathname.replace(/^\/(?:([A-Za-z]:))/, '$1'), '--unknown', 'value'], { encoding: 'utf8' });
  assert.notEqual(result.status, 0); assert.match(result.stderr, /usage|unknown|required/i);
});
