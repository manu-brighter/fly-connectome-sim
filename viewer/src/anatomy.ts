import sourceLocks from '../../src/fly_connectome_sim/neural/sources.lock.json' with { type: 'json' };
import arrayLocks from '../../src/fly_connectome_sim/neural/arrays.lock.json' with { type: 'json' };

export type Anatomy = {
  version: 'replay-soma-anatomy/v1';
  source: { release: 'MaleCNS v1.0'; annotations_sha256: string; coordinate_field: 'somaLocation' };
  binding: { recording_sha256: string; graph_ids_sha256: string };
  coverage: { model_cells: number; positioned_cells: number; missing_positions: number; displayed_cells: number };
  sampling: { method: 'ordered-position-stride/v1'; limit: 12000 };
  points: Array<[number, string, number, number, number]>;
};
type Binding = { recordingSha256: string; graphIdsSha256: string };
export const MAX_ANATOMY_BYTES = 8 * 1024 * 1024;
function check(value: unknown, message: string): asserts value { if (!value) throw new Error(`Anatomy: ${message}`); }
function fields(value: any, names: string[]) {
  check(value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === names.length && names.every(name => Object.hasOwn(value, name)), 'missing or unsupported fields.');
}

export async function sha256Bytes(bytes: ArrayBuffer): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');
}
export async function readRecordingFile(file: Pick<File, 'arrayBuffer'>) {
  const bytes = await file.arrayBuffer();
  return { text: new TextDecoder('utf-8', { fatal: true }).decode(bytes), sha256: await sha256Bytes(bytes), byteLength: bytes.byteLength };
}

export function parseAnatomy(text: string, context: Binding): Anatomy {
  check(new TextEncoder().encode(text).length <= MAX_ANATOMY_BYTES, 'file exceeds 8 MiB.');
  const value = JSON.parse(text);
  const stack: Array<Set<string> | null> = [], tokens = text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+/g) ?? [];
  for (let index = 0; index < tokens.length; index++) {
    const token = tokens[index];
    if (token === '{' || token === '[') { stack.push(token === '{' ? new Set() : null); check(stack.length <= 12, 'excessive nesting.'); }
    else if (token === '}' || token === ']') stack.pop();
    else if (token.startsWith('"') && tokens[index + 1] === ':') {
      const key = JSON.parse(token), keys = stack.at(-1);
      check(keys && !keys.has(key) && !['__proto__', 'constructor', 'prototype'].includes(key), 'duplicate or unsupported property.'); keys.add(key);
    }
  }
  fields(value, ['version', 'source', 'binding', 'coverage', 'sampling', 'points']);
  fields(value.source, ['release', 'annotations_sha256', 'coordinate_field']); fields(value.binding, ['recording_sha256', 'graph_ids_sha256']);
  fields(value.coverage, ['model_cells', 'positioned_cells', 'missing_positions', 'displayed_cells']); fields(value.sampling, ['method', 'limit']);
  check(value.version === 'replay-soma-anatomy/v1' && value.source.release === 'MaleCNS v1.0' && value.source.coordinate_field === 'somaLocation', 'unsupported source or coordinate field.');
  check(value.source.annotations_sha256 === sourceLocks['annotations.feather'].sha256, 'annotation source differs from the tracked lock.');
  check(value.binding.graph_ids_sha256 === arrayLocks.ids && value.binding.graph_ids_sha256 === context.graphIdsSha256, 'graph IDs differ from locked model/recording.');
  check(/^[0-9a-f]{64}$/.test(context.recordingSha256) && value.binding.recording_sha256 === context.recordingSha256, 'choose anatomy generated for this exact recording file.');
  const coverage = value.coverage;
  check(Object.values(coverage).every(count => Number.isSafeInteger(count) && (count as number) >= 0), 'invalid coverage counts.');
  check(coverage.model_cells === 166700 && coverage.positioned_cells + coverage.missing_positions === coverage.model_cells && coverage.displayed_cells === Math.min(coverage.positioned_cells, 12000), 'coverage does not reconcile with the locked model.');
  check(value.sampling.method === 'ordered-position-stride/v1' && value.sampling.limit === 12000 && Array.isArray(value.points) && value.points.length === coverage.displayed_cells, 'invalid bounded sampling.');
  let previous = -1; const ids = new Set<string>();
  for (const point of value.points) {
    check(Array.isArray(point) && point.length === 5, 'each point needs index, ID and three coordinates.');
    check(Number.isSafeInteger(point[0]) && point[0] > previous && point[0] < coverage.model_cells, 'model indices must increase and remain in range.'); previous = point[0];
    check(typeof point[1] === 'string' && /^[1-9][0-9]{0,18}$/.test(point[1]) && !ids.has(point[1]), 'source IDs must be unique positive decimal strings.'); ids.add(point[1]);
    check(point.slice(2).every((coordinate: unknown) => typeof coordinate === 'number' && Number.isSafeInteger(coordinate)), 'coordinates must be finite safe integers.');
  }
  return value;
}

export function createAnatomyAttachment() {
  let generation = 0, request = 0, binding: Binding | null = null, value: Anatomy | null = null;
  return {
    get value() { return value; },
    setRecording(next: Binding) { generation++; request++; binding = next; value = null; },
    cancelPending() { request++; },
    async load(text: Promise<string>) {
      check(binding, 'open a recording first.');
      const expectedGeneration = generation, expectedRequest = ++request, expectedBinding = binding;
      const raw = await text;
      if (generation !== expectedGeneration || request !== expectedRequest) return false;
      value = parseAnatomy(raw, expectedBinding); return true;
    },
  };
}
