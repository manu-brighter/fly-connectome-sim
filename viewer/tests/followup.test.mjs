import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { canonical } from '../src/event-replay.ts';
const module = await import('../src/followup.ts').catch(() => ({}));
const bytes = text => new TextEncoder().encode(text);
const hash = value => createHash('sha256').update(value).digest('hex');
function api() { assert.equal(typeof module.parseFollowupBundle, 'function', 'Bound companion reader is missing'); return module; }

// Declared relationships only; actual accepted local files are checked separately.
export function followupFixture(recording) {
  const source = { run_kind: 'pilot', verification_mode: 'integrity-only', schema_sha256: 'a'.repeat(64), run_metadata_sha256: 'b'.repeat(64), events_sha256: 'c'.repeat(64), final_scientific_sha256: 'd'.repeat(64) };
  const plan = { version: 'event-plan/v1', status: 'selected', brief: { title: 'Team party', guests: 100, max_budget_chf: 5000 },
    selected_option_id: 'rooftop', selected_option: { id: 'rooftop', title: 'Team <Abend>', setting: 'rooftop', music: 'House', budget_chf: 4200, capacity: 120, duration_minutes: 240,
      programme: [{ start_minute: 0, label: 'Welcome & drinks' }, { start_minute: 60, label: 'Music' }] },
    decision_ref: { event_sequence: 214, scientific_sha256: 'e'.repeat(64), input_sha256: 'f'.repeat(64), policy_version: 'event-card-choice/v1' }, source };
  recording ??= { version: 'feed-event-replay/v1', plan };
  const rawRecording = bytes(JSON.stringify(recording)), rawPlan = bytes(canonical(recording.plan) + '\n');
  const sessionReceipt = { version: 'session-bundle/v1', status: 'complete', source: recording.plan.source, files: {
    'recording.json': { size_bytes: rawRecording.length, sha256: hash(rawRecording) }, 'plan.json': { size_bytes: rawPlan.length, sha256: hash(rawPlan) },
  } };
  const binding = { receipt_sha256: hash(bytes(canonical(sessionReceipt) + '\n')), plan_sha256: hash(rawPlan), recording_sha256: hash(rawRecording) };
  const supplement = { overview: 'Grüße & <Plan> *klar*.', preparation: ['Zugänglichkeit prüfen.'], open_questions: ['Wer kommt?'] };
  const followup = { version: 'event-followup/v1', source: binding, plan: recording.plan, supplement };
  const markdown = fixtureMarkdown(recording.plan, supplement);
  const receipt = { version: 'event-followup-receipt/v1', status: 'validated', source: { ...binding }, provider: 'openai', endpoint: 'https://api.openai.com/v1/responses', requested_model: 'explicit-model', max_output_tokens: 1024,
    request_sha256: '1'.repeat(64), response_id: 'resp_fixture', response_model: 'explicit-model-snapshot', response_sha256: '2'.repeat(64), usage: { input_tokens: 20, output_tokens: 30, total_tokens: 50 },
    files: { 'followup.json': { size_bytes: 0, sha256: '' }, 'event-plan.md': { size_bytes: markdown.length, sha256: hash(markdown) } } };
  return { followup, receipt, markdown, context: { recording, recordingSha256: hash(rawRecording), recordingByteLength: rawRecording.length } };
}
function fixtureMarkdown(plan, s) {
  const e = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replace(/[\\`*_{}\[\]()#+.!|\-]/g, '\\$&');
  const b = plan.brief, o = plan.selected_option;
  return bytes([
    '# Eventplan: ' + e(o.title), '', '## Unveränderter Originalvorschlag', '', '- Brief: ' + e(b.title), '- Gäste: ' + e(b.guests), '- Budgetrahmen: CHF ' + e(b.max_budget_chf),
    '- Options-ID: ' + e(o.id), '- Setting: ' + e(o.setting), '- Musik: ' + e(o.music), '- Budgetvorschlag: CHF ' + e(o.budget_chf), '- Kapazitätsvorschlag: ' + e(o.capacity), '- Dauer: ' + e(o.duration_minutes) + ' Minuten',
    '', 'Budget und Kapazität sind Vorschlagsschätzungen, kein bestätigtes Angebot.', '', '### Originalprogramm', '', ...o.programme.map(p => '- ' + e(p.start_minute) + ' min: ' + e(p.label)),
    '', '## Unverbindliche Ergänzung', '', 'Planungshinweise und Fragen, keine bestätigte Verfügbarkeit, Buchung oder neue Messung.', '', e(s.overview), '', '### Vorbereitung', '', ...s.preparation.map(p => '- ' + e(p)),
    '', '### Offene Fragen', '', ...(s.open_questions.length ? s.open_questions.map(q => '- ' + e(q)) : ['Keine zusätzlichen Fragen vorgeschlagen.']), '',
  ].join('\n'));
}
export function followupFiles(fixture) {
  const raw = bytes(JSON.stringify(fixture.followup));
  fixture.receipt.files['followup.json'] = { size_bytes: raw.length, sha256: hash(raw) };
  return [raw, bytes(JSON.stringify(fixture.receipt))];
}

test('companion identifies both versions in any order and binds exact bytes, full plan and derived source receipt', async () => {
  const { parseFollowupBundle } = api(), f = followupFixture(), files = followupFiles(f);
  for (const input of [files, [...files].reverse()]) {
    const result = await parseFollowupBundle(input, f.context);
    assert.deepEqual(result.followup, f.followup); assert.deepEqual(result.markdownBytes, f.markdown);
    assert.match(new TextDecoder().decode(result.markdownBytes), /Grüße &amp; &lt;Plan&gt; \\\*klar\\\*/);
  }
});

test('strict bundle rejects byte/source/plan/receipt/usage and malformed text without trusting self-declared hashes', async () => {
  const { parseFollowupBundle } = api();
  const changes = [f => f.followup.extra = true, f => f.receipt.extra = true, f => f.receipt.status = 'dry-run', f => f.receipt.provider = 'other', f => f.receipt.endpoint = 'https://other.test',
    f => f.followup.source.recording_sha256 = '3'.repeat(64), f => f.followup.source.plan_sha256 = '3'.repeat(64), f => f.followup.source.receipt_sha256 = '3'.repeat(64),
    f => f.receipt.source.plan_sha256 = '3'.repeat(64), f => f.followup.plan.brief.guests++, f => f.receipt.response_id = '<html>', f => f.receipt.response_model = 'bad/model',
    f => f.receipt.requested_model = 'bad/model', f => f.receipt.max_output_tokens = true, f => f.receipt.max_output_tokens = 511, f => f.receipt.usage.output_tokens = true,
    f => f.receipt.usage.total_tokens++, f => f.receipt.usage.output_tokens = 1025, f => f.receipt.usage.extra = 0, f => f.receipt.files['event-plan.md'].sha256 = '0'.repeat(64),
    f => f.receipt.files['event-plan.md'].size_bytes++, f => f.receipt.files.extra = {}, f => f.followup.supplement.extra = true,
    f => f.followup.supplement.overview = '', f => f.followup.supplement.overview = 'a'.repeat(601), f => f.followup.supplement.overview = 'A\nB',
    f => f.followup.supplement.overview = 'A\u202eB', f => f.followup.supplement.overview = '\ud800', f => f.followup.supplement.overview = 'A\u00a0B',
    f => f.followup.supplement.overview = 'https://example.test', f => f.followup.supplement.overview = 'mailto:a@example.test',
    f => f.followup.supplement.preparation = [], f => f.followup.supplement.preparation = ['a'.repeat(241)], f => f.followup.supplement.open_questions = Array(5).fill('a'),
  ];
  for (const change of changes) { const f = followupFixture(); f.followup = structuredClone(f.followup); change(f); await assert.rejects(parseFollowupBundle(followupFiles(f), f.context), undefined, String(change)); }
  const f = followupFixture(), files = followupFiles(f);
  await assert.rejects(parseFollowupBundle([files[0]], f.context)); await assert.rejects(parseFollowupBundle([...files, files[1]], f.context)); await assert.rejects(parseFollowupBundle([files[0], files[0]], f.context));
  await assert.rejects(parseFollowupBundle([new Uint8Array(128 * 1024 + 1), files[1]], f.context));
  await assert.rejects(parseFollowupBundle([files[0], bytes(new TextDecoder().decode(files[1]) + ' '.repeat(16 * 1024))], f.context));
  await assert.rejects(parseFollowupBundle([files[0], new Uint8Array([255])], f.context));
  await assert.rejects(parseFollowupBundle([bytes(new TextDecoder().decode(files[0]) + ' '), files[1]], f.context));
  await assert.rejects(parseFollowupBundle([bytes(new TextDecoder().decode(files[0]).replace('"version":', '"version":"duplicate","version":')), files[1]], f.context));
  await assert.rejects(parseFollowupBundle(files, { ...f.context, recordingByteLength: f.context.recordingByteLength + 1 }));
  await assert.rejects(parseFollowupBundle(files, { ...f.context, recording: { ...f.context.recording, version: 'event-choice-replay/v1' } }));
});

test('Unicode codepoint limits and empty questions follow the Python producer and preserve checked snapshots', async () => {
  const { parseFollowupBundle } = api(), f = followupFixture();
  f.followup.supplement = { overview: '😀'.repeat(600), preparation: ['Äöüß'], open_questions: [] };
  f.markdown = fixtureMarkdown(f.followup.plan, f.followup.supplement);
  f.receipt.files['event-plan.md'] = { size_bytes: f.markdown.length, sha256: hash(f.markdown) };
  const files = followupFiles(f), pending = parseFollowupBundle(files, f.context);
  files[0].fill(0); files[1].fill(0);
  const result = await pending;
  assert.deepEqual(result.markdownBytes, f.markdown); assert.equal(Array.from(result.followup.supplement.overview).length, 600);
});

test('obsolete imports during hash work cannot attach, clear valid state or survive export/replacement', async () => {
  const { createFollowupAttachment } = api(), f = followupFixture(), attachment = createFollowupAttachment();
  attachment.setRecording(f.context); assert.equal(await attachment.load(Promise.resolve(followupFiles(f))), true);
  const valid = attachment.value;
  await assert.rejects(attachment.load(Promise.resolve([]))); assert.equal(attachment.value, valid);
  const original = crypto.subtle.digest.bind(crypto.subtle); let release;
  crypto.subtle.digest = async (...args) => { if (!release) await new Promise(resolve => { release = resolve; }); return original(...args); };
  try {
    const pending = attachment.load(Promise.resolve(followupFiles(f))); while (!release) await new Promise(setImmediate);
    attachment.setRecording(f.context); release(); assert.equal(await pending, false); assert.equal(attachment.value, null);
  } finally { crypto.subtle.digest = original; }
  await attachment.load(Promise.resolve(followupFiles(f))); const frozen = attachment.value;
  attachment.setExporting(true); assert.equal(await attachment.load(Promise.resolve([])), false); assert.equal(attachment.value, frozen);
  attachment.setExporting(false); let reject;
  const stale = attachment.load(new Promise((_, fail) => { reject = fail; })); attachment.cancelPending(); reject(new Error('obsolete read'));
  assert.equal(await stale, false); assert.equal(attachment.value, frozen);
});

test('actual historical Python Markdown bytes match reconstructed viewer output without a new call', async t => {
  const location = new URL('../../runs/event-followup-live-20261108/', import.meta.url), recordingPath = new URL('../../runs/cell-demo-20261108-02/session/recording.json', import.meta.url);
  if (!existsSync(recordingPath) || !existsSync(new URL('followup.json', location))) { t.skip('Historical local artifacts unavailable'); return; }
  const { parseFollowupBundle } = api(), { parseAnyRecording } = await import('../src/recording.ts');
  const raw = readFileSync(recordingPath), recording = await parseAnyRecording(raw.toString('utf8'));
  const result = await parseFollowupBundle([readFileSync(new URL('receipt.json', location)), readFileSync(new URL('followup.json', location))], { recording, recordingSha256: hash(raw), recordingByteLength: raw.length });
  assert.deepEqual(result.markdownBytes, new Uint8Array(readFileSync(new URL('event-plan.md', location))));
});

test('provider identifiers require complete strings without trailing LF or CRLF', async () => {
  const { parseFollowupBundle } = api();
  for (const field of ['requested_model', 'response_model', 'response_id']) for (const ending of ['\n', '\r\n']) {
    const f = followupFixture(); f.receipt[field] += ending;
    await assert.rejects(parseFollowupBundle(followupFiles(f), f.context), undefined, field + JSON.stringify(ending));
  }
});

test('attachment snapshots minimal source context before file reads and direct parsing snapshots before hashing', async () => {
  const { createFollowupAttachment, parseFollowupBundle } = api(), f = followupFixture(), files = followupFiles(f);
  const originalTitle = f.context.recording.plan.selected_option.title;
  const attachment = createFollowupAttachment(); attachment.setRecording(f.context);
  let finish; const pending = attachment.load(new Promise(resolve => { finish = resolve; }));
  f.context.recording.plan.selected_option.title = 'Mutated by caller'; f.context.recordingByteLength++; f.context.recordingSha256 = '0'.repeat(64);
  finish(files); assert.equal(await pending, true); assert.equal(attachment.value.followup.plan.selected_option.title, originalTitle);
  const direct = followupFixture(), directFiles = followupFiles(direct), parsed = parseFollowupBundle(directFiles, direct.context);
  direct.context.recordingByteLength++; direct.context.recordingSha256 = '0'.repeat(64); direct.context.recording.plan.selected_option.title = 'Mutation during hash';
  assert.equal((await parsed).followup.plan.selected_option.title, originalTitle);
});
