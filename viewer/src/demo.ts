import { MAX_ANATOMY_BYTES, createAnatomyAttachment, sha256Bytes } from './anatomy.ts';
import { MAX_CELL_ACTIVITY_BYTES, assertCellAnatomy, createCellActivityAttachment } from './cell-activity.ts';
import { MAX_FOLLOWUP_BYTES, MAX_FOLLOWUP_RECEIPT_BYTES, createFollowupAttachment } from './followup.ts';
import { parseAnyRecording } from './recording.ts';
import { isSessionRecording } from './session-replay.ts';
import { object, strictJson } from './event-replay.ts';

export const DEMO_LIMITS = {
  'recording.json': 32 * 1024 * 1024,
  'cell-activity.json': MAX_CELL_ACTIVITY_BYTES,
  'anatomy.json': MAX_ANATOMY_BYTES,
  'followup.json': MAX_FOLLOWUP_BYTES,
  'receipt.json': MAX_FOLLOWUP_RECEIPT_BYTES,
} as const;
type DemoName = keyof typeof DEMO_LIMITS;
type DemoFile = { name: string; size: number; arrayBuffer(): Promise<ArrayBuffer> };

export async function readDemoFiles(files: readonly DemoFile[]) {
  const inputs = files.map(file => ({ name: file.name, size: file.size, read: file.arrayBuffer.bind(file) }));
  if (inputs.length !== 5 || new Set(inputs.map(file => file.name)).size !== 5) throw new Error('Choose exactly the five demo JSON files, once each.');
  for (const file of inputs) {
    if (!Object.hasOwn(DEMO_LIMITS, file.name) || !Number.isSafeInteger(file.size) || file.size <= 0 || file.size > DEMO_LIMITS[file.name as DemoName]) throw new Error(`Unsupported demo file or byte size: ${file.name}.`);
  }
  const snapshots = {} as Record<DemoName, Uint8Array<ArrayBuffer>>;
  const texts = {} as Record<DemoName, string>;
  await Promise.all(inputs.map(async file => {
    const source = new Uint8Array(await file.read());
    if (source.byteLength !== file.size) throw new Error('A demo file changed while reading.');
    const raw = source.slice();
    const name = file.name as DemoName;
    snapshots[name] = raw;
    texts[name] = new TextDecoder('utf-8', { fatal: true }).decode(raw);
  }));
  if (object(strictJson(texts['followup.json']), 'Demo companion').version !== 'event-followup/v1' || object(strictJson(texts['receipt.json']), 'Demo receipt').version !== 'event-followup-receipt/v1') throw new Error('Companion filenames must match their document roles.');
  const recording = await parseAnyRecording(texts['recording.json']);
  if (!isSessionRecording(recording) || !recording.plan.selected_option) throw new Error('The complete demo needs a continuous session with a selected plan. Open other recordings individually.');
  const recordingSha256 = await sha256Bytes(snapshots['recording.json'].buffer);
  const recordingByteLength = snapshots['recording.json'].byteLength;
  const identity = recording.source.metadata.engine_identity as { model_provenance?: { graph_ids_sha256?: string } };
  const anatomyAttachment = createAnatomyAttachment(), cellAttachment = createCellActivityAttachment(), followupAttachment = createFollowupAttachment();
  anatomyAttachment.setRecording({ recordingSha256, graphIdsSha256: identity?.model_provenance?.graph_ids_sha256 ?? '' });
  cellAttachment.setRecording({ recording, recordingSha256 });
  followupAttachment.setRecording({ recording, recordingSha256, recordingByteLength });
  await anatomyAttachment.load(Promise.resolve(texts['anatomy.json']));
  await cellAttachment.load(Promise.resolve(texts['cell-activity.json']));
  assertCellAnatomy(cellAttachment.value, anatomyAttachment.value);
  await followupAttachment.load(Promise.resolve([snapshots['followup.json'], snapshots['receipt.json']]));
  return { recording, recordingSha256, recordingByteLength, snapshots, anatomyAttachment, cellAttachment, followupAttachment };
}
export type DemoCandidate = Awaited<ReturnType<typeof readDemoFiles>>;
