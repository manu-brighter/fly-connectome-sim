import { check, keys, object, int, digest, equal, strictJson, canonical, sha256, type EventPlan } from './event-replay.ts';
import type { AnyRecording } from './recording.ts';

export const MAX_FOLLOWUP_BYTES = 128 * 1024;
export const MAX_FOLLOWUP_RECEIPT_BYTES = 16 * 1024;
export type FollowupContext = { recording: AnyRecording; recordingSha256: string; recordingByteLength: number };
type BoundContext = { version: AnyRecording['version']; plan: EventPlan | null; recordingSha256: string; recordingByteLength: number };
type Source = { receipt_sha256: string; plan_sha256: string; recording_sha256: string };
type Supplement = { overview: string; preparation: string[]; open_questions: string[] };
type Followup = { version: 'event-followup/v1'; source: Source; plan: EventPlan; supplement: Supplement };
export type FollowupBundle = { followup: Followup; markdownBytes: Uint8Array };
const obsolete = Symbol('obsolete companion import');
const encode = (text: string) => new TextEncoder().encode(text);
function snapshotContext(context: FollowupContext): BoundContext {
  return { version: context.recording.version, plan: 'plan' in context.recording ? JSON.parse(canonical(context.recording.plan)) : null,
    recordingSha256: context.recordingSha256, recordingByteLength: context.recordingByteLength };
}

function text(value: unknown, limit: number): asserts value is string {
  check(typeof value === 'string' && Array.from(value).length >= 1 && Array.from(value).length <= limit && value.trim().length > 0, 'Companion text length is invalid.');
  check(Array.from(value).every(character => character === ' ' || !/[\p{C}\p{Z}]/u.test(character)), 'Companion contains nonprintable Unicode.');
  check(!/(?:[a-z][a-z0-9+.-]*:\/\/|www\.|(?:https?|ftp|file|mailto|data|javascript|tel):|\/\/|\b(?:[a-z0-9-]+\.)+[a-z]{2,63}\b)/i.test(value), 'Companion URLs are unsupported.');
}
function escape(value: string | number) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replace(/[\\`*_{}\[\]()#+.!|\-]/g, '\\$&');
}
export function renderFollowupMarkdown(plan: EventPlan, supplement: Supplement): Uint8Array {
  const brief = plan.brief, option = plan.selected_option;
  check(option, 'A selected original plan is required.');
  const lines = ['# Eventplan: ' + escape(option.title), '', '## Unveränderter Originalvorschlag', '',
    '- Brief: ' + escape(brief.title), '- Gäste: ' + escape(brief.guests), '- Budgetrahmen: CHF ' + escape(brief.max_budget_chf),
    '- Options-ID: ' + escape(option.id), '- Setting: ' + escape(option.setting), '- Musik: ' + escape(option.music),
    '- Budgetvorschlag: CHF ' + escape(option.budget_chf), '- Kapazitätsvorschlag: ' + escape(option.capacity), '- Dauer: ' + escape(option.duration_minutes) + ' Minuten',
    '', 'Budget und Kapazität sind Vorschlagsschätzungen, kein bestätigtes Angebot.', '', '### Originalprogramm', '',
    ...option.programme.map(entry => '- ' + escape(entry.start_minute) + ' min: ' + escape(entry.label)),
    '', '## Unverbindliche Ergänzung', '', 'Planungshinweise und Fragen, keine bestätigte Verfügbarkeit, Buchung oder neue Messung.', '',
    escape(supplement.overview), '', '### Vorbereitung', '', ...supplement.preparation.map(item => '- ' + escape(item)),
    '', '### Offene Fragen', '', ...(supplement.open_questions.length ? supplement.open_questions.map(item => '- ' + escape(item)) : ['Keine zusätzlichen Fragen vorgeschlagen.']), '',
  ];
  return encode(lines.join('\n'));
}

async function parseBundle(files: readonly Uint8Array[], context: BoundContext, current: () => boolean): Promise<FollowupBundle> {
  check(files.length === 2, 'Choose exactly followup.json and its validated receipt.json together.');
  check(files.every(file => ArrayBuffer.isView(file) && Object.prototype.toString.call(file) === '[object Uint8Array]' && file.byteLength > 0 && file.byteLength <= MAX_FOLLOWUP_BYTES), 'Each companion input must be nonempty and at most 128 KiB.');
  const snapshots = files.map(file => new Uint8Array(file));
  const parsed = snapshots.map(file => object(strictJson(new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(file)), 'Companion file'));
  const followupIndex = parsed.findIndex(value => value.version === 'event-followup/v1');
  const receiptIndex = parsed.findIndex(value => value.version === 'event-followup-receipt/v1');
  check(followupIndex >= 0 && receiptIndex >= 0 && followupIndex !== receiptIndex, 'Expected one follow-up and one receipt version.');
  check(snapshots[receiptIndex].byteLength <= MAX_FOLLOWUP_RECEIPT_BYTES, 'Companion receipt exceeds 16 KiB.');
  const value = keys(parsed[followupIndex], ['version', 'source', 'plan', 'supplement'], 'Follow-up');
  const receipt = keys(parsed[receiptIndex], ['version', 'status', 'source', 'provider', 'endpoint', 'requested_model', 'max_output_tokens', 'request_sha256', 'response_id', 'response_model', 'response_sha256', 'usage', 'files'], 'Follow-up receipt');
  equal(receipt.status, 'validated', 'Follow-up completion'); equal(receipt.provider, 'openai', 'Follow-up provider'); equal(receipt.endpoint, 'https://api.openai.com/v1/responses', 'Follow-up endpoint');
  for (const name of ['requested_model', 'response_model']) check(typeof receipt[name] === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/.test(receipt[name]), 'Invalid companion model identifier.');
  check(typeof receipt.response_id === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$/.test(receipt.response_id), 'Invalid companion response identifier.');
  int(receipt.max_output_tokens, 512, 4096, 'Companion token cap'); digest(receipt.request_sha256, 'Companion request hash'); digest(receipt.response_sha256, 'Companion response hash');
  const usage = keys(receipt.usage, ['input_tokens', 'output_tokens', 'total_tokens'], 'Companion usage');
  for (const count of Object.values(usage)) int(count, 0, Number.MAX_SAFE_INTEGER, 'Companion usage');
  check(usage.total_tokens === (usage.input_tokens as number) + (usage.output_tokens as number) && (usage.output_tokens as number) <= receipt.max_output_tokens, 'Companion usage does not reconcile.');
  const binding = keys(value.source, ['receipt_sha256', 'plan_sha256', 'recording_sha256'], 'Companion source');
  for (const hash of Object.values(binding)) digest(hash, 'Companion source hash');
  equal(keys(receipt.source, ['receipt_sha256', 'plan_sha256', 'recording_sha256'], 'Receipt source'), binding, 'Companion/receipt source');
  check(context.version === 'feed-event-replay/v1', 'Open a continuous session recording for this companion.');
  digest(context.recordingSha256, 'Current recording hash'); int(context.recordingByteLength, 1, 32 * 1024 * 1024, 'Current recording byte length');
  const plan = context.plan;
  check(plan?.status === 'selected' && plan.selected_option, 'A deferred recording has no selected companion.');
  equal(value.plan, plan, 'Complete original plan'); equal(binding.recording_sha256, context.recordingSha256, 'Exact recording bytes');
  const supplement = keys(value.supplement, ['overview', 'preparation', 'open_questions'], 'Companion supplement');
  text(supplement.overview, 600);
  for (const [name, minimum] of [['preparation', 1], ['open_questions', 0]] as const) {
    const items = supplement[name]; check(Array.isArray(items) && items.length >= minimum && items.length <= 4, 'Invalid companion list length.');
    for (const item of items) text(item, 240);
  }
  check(encode(canonical(supplement)).byteLength <= 16 * 1024, 'Companion supplement exceeds 16 KiB.');
  const bindings = keys(receipt.files, ['followup.json', 'event-plan.md'], 'Companion output bindings');
  const outputBindings = Object.fromEntries(Object.entries(bindings).map(([name, raw]) => {
    const item = keys(raw, ['size_bytes', 'sha256'], 'Companion file binding');
    int(item.size_bytes, 1, MAX_FOLLOWUP_BYTES, 'Companion file size'); digest(item.sha256, 'Companion file hash'); return [name, item];
  }));
  const hash = async (bytes: Uint8Array) => { const result = await sha256(bytes); if (!current()) throw obsolete; return result; };
  equal(outputBindings['followup.json'].size_bytes, snapshots[followupIndex].byteLength, 'Exact companion file size');
  equal(outputBindings['followup.json'].sha256, await hash(snapshots[followupIndex]), 'Exact companion file bytes');
  const planBytes = encode(canonical(plan) + '\n'), planHash = await hash(planBytes);
  equal(binding.plan_sha256, planHash, 'Canonical original plan bytes');
  const sessionReceipt = { version: 'session-bundle/v1', status: 'complete', source: plan.source,
    files: { 'recording.json': { size_bytes: context.recordingByteLength, sha256: context.recordingSha256 }, 'plan.json': { size_bytes: planBytes.byteLength, sha256: planHash } } };
  equal(binding.receipt_sha256, await hash(encode(canonical(sessionReceipt) + '\n')), 'Canonical original session receipt');
  const followup = value as Followup, markdownBytes = renderFollowupMarkdown(plan, followup.supplement);
  equal(outputBindings['event-plan.md'].size_bytes, markdownBytes.byteLength, 'Reconstructed Markdown size');
  equal(outputBindings['event-plan.md'].sha256, await hash(markdownBytes), 'Reconstructed Markdown bytes');
  return { followup, markdownBytes };
}
export async function parseFollowupBundle(files: readonly Uint8Array[], context: FollowupContext): Promise<FollowupBundle> {
  return parseBundle(files, snapshotContext(context), () => true);
}
export function createFollowupAttachment() {
  let generation = 0, request = 0, exporting = false, context: BoundContext | null = null, value: FollowupBundle | null = null;
  return {
    get value() { return value; },
    setRecording(next: FollowupContext | null) { if (exporting) return false; generation++; request++; context = next ? snapshotContext(next) : null; value = null; return true; },
    cancelPending() { request++; },
    setExporting(next: boolean) { exporting = next; if (next) request++; },
    async load(files: Promise<readonly Uint8Array[]>) {
      if (exporting) return false;
      check(context, 'Open a continuous session recording first.');
      const token = ++request, expectedGeneration = generation, expectedContext = context;
      const current = () => !exporting && token === request && generation === expectedGeneration;
      try {
        const bytes = await files; if (!current()) return false;
        const candidate = await parseBundle(bytes, expectedContext, current);
        if (!current()) return false; value = candidate; return true;
      } catch (error) { if (!current() || error === obsolete) return false; throw error; }
    },
  };
}
