import { constants } from 'node:fs';
import { open, mkdir, lstat, stat, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { DEMO_LIMITS, readDemoFiles } from '../viewer/src/demo.ts';

function checkSize(info, name) {
  if (!info.isFile() || !Number.isSafeInteger(info.size) || info.size <= 0 || info.size > DEMO_LIMITS[name]) throw new Error(`Invalid regular demo file or byte size: ${name}.`);
}

export async function readBoundedHandle(handle, name, initial) {
  const info = initial ?? await handle.stat();
  checkSize(info, name);
  const buffer = Buffer.alloc(info.size + 1);
  let length = 0;
  while (length < buffer.length) {
    const { bytesRead } = await handle.read(buffer, length, buffer.length - length, null);
    if (!bytesRead) break;
    length += bytesRead;
  }
  const after = await handle.stat();
  if (length !== info.size || after.size !== info.size || after.mtimeMs !== info.mtimeMs) throw new Error(`Demo input changed while reading: ${name}.`);
  return new Uint8Array(buffer.subarray(0, length)).slice();
}

export async function prepareDemo({ recording, cellActivity, anatomy, followupDir, outputDir }) {
  if (![recording, cellActivity, anatomy, followupDir, outputDir].every(value => typeof value === 'string' && value.length)) throw new Error('All five explicit input/output paths are required.');
  const output = resolve(outputDir);
  try { await lstat(output); throw new Error('Output already exists; choose a new directory.'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (!(await stat(dirname(output))).isDirectory()) throw new Error('The output parent must be an existing directory.');
  const sources = { 'recording.json': recording, 'cell-activity.json': cellActivity, 'anatomy.json': anatomy, 'followup.json': join(followupDir, 'followup.json'), 'receipt.json': join(followupDir, 'receipt.json') };
  const handles = [];
  let candidate;
  try {
    for (const [name, path] of Object.entries(sources)) {
      const handle = await open(path, constants.O_RDONLY | constants.O_NONBLOCK);
      handles.push({ name, handle });
      const info = await handle.stat(); checkSize(info, name);
      handles.at(-1).info = info;
    }
    const files = [];
    for (const { name, handle, info } of handles) {
      const raw = await readBoundedHandle(handle, name, info);
      files.push({ name, size: raw.length, arrayBuffer: async () => raw.buffer });
    }
    candidate = await readDemoFiles(files);
  } finally { await Promise.all(handles.map(({ handle }) => handle.close())); }
  await mkdir(output);
  try {
    for (const [name, raw] of Object.entries(candidate.snapshots)) await writeFile(join(output, name), raw, { flag: 'wx' });
  } catch { throw new Error(`Incomplete demo output retained at ${output}. No files were removed; choose a new output directory.`); }
  return output;
}

function argumentsFrom(argv) {
  const names = { '--recording': 'recording', '--cell-activity': 'cellActivity', '--anatomy': 'anatomy', '--followup-dir': 'followupDir', '--output-dir': 'outputDir' }, options = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = names[argv[i]], value = argv[i + 1];
    if (!key || Object.hasOwn(options, key) || !value || value.startsWith('--')) throw new Error('Unknown, duplicate or missing argument. Required: --recording --cell-activity --anatomy --followup-dir --output-dir.');
    options[key] = value;
  }
  return options;
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const output = await prepareDemo(argumentsFrom(process.argv.slice(2)));
    console.log(`Prepared demo: ${output}\nStart the existing viewer with npm --prefix viewer run dev. Choose Open demo and select all five JSON files in this folder.`);
  } catch (error) { console.error(error instanceof Error ? error.message : 'Demo preparation failed.'); process.exitCode = 1; }
}
