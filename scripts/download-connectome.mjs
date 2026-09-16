import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream } from 'node:fs';
import { mkdir, readFile, rename, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';

const directory = new URL('../data/malecns-v1.0/', import.meta.url);
const manifest = JSON.parse(await readFile(new URL('manifest.json', directory), 'utf8'));

async function exists(path) {
  try {
    await stat(path);
    return true;
  } catch (error) {
    if (error.code === 'ENOENT') return false;
    throw error;
  }
}

async function verify(path, file) {
  const md5 = createHash('md5');
  const sha256 = createHash('sha256');
  let bytes = 0;

  for await (const chunk of createReadStream(path)) {
    bytes += chunk.length;
    md5.update(chunk);
    sha256.update(chunk);
  }

  if (bytes !== file.bytes || md5.digest('base64') !== file.md5Base64) {
    throw new Error(`Size or checksum mismatch: ${file.name}`);
  }

  return { name: file.name, bytes, sha256: sha256.digest('hex') };
}

await mkdir(directory, { recursive: true });

for (const file of manifest.files) {
  if (!/^[a-z0-9.-]+\.feather$/.test(file.name)) {
    throw new Error(`Invalid dataset filename: ${file.name}`);
  }

  const target = new URL(file.name, directory);
  if (await exists(target)) {
    console.log(JSON.stringify({ status: 'already-verified', ...await verify(target, file) }));
    continue;
  }

  const partial = new URL(`${file.name}.part`, directory);
  if (await exists(partial)) {
    throw new Error(`Existing partial download needs inspection: ${fileURLToPath(partial)}`);
  }

  const response = await fetch(new URL(file.name, manifest.baseUrl));
  if (!response.ok || !response.body) {
    throw new Error(`Download failed for ${file.name}: HTTP ${response.status}`);
  }
  if (response.headers.get('x-goog-generation') !== file.generation) {
    await response.body.cancel();
    throw new Error(`Source generation changed: ${file.name}`);
  }

  let received = 0;
  let lastReport = Date.now();
  console.log(`Downloading ${file.name} (${file.bytes} bytes)`);
  const progress = new Transform({
    transform(chunk, encoding, callback) {
      received += chunk.length;
      if (Date.now() - lastReport >= 10000) {
        console.log(`${file.name}: ${(100 * received / file.bytes).toFixed(1)}%`);
        lastReport = Date.now();
      }
      callback(null, chunk);
    },
  });

  await pipeline(response.body, progress, createWriteStream(partial, { flags: 'wx' }));
  const result = await verify(partial, file);
  if (await exists(target)) throw new Error(`Target appeared during download: ${file.name}`);
  await rename(partial, target);
  console.log(JSON.stringify({ status: 'downloaded-and-verified', ...result }));
}
