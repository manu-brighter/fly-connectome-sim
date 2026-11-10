import assert from 'node:assert/strict';
import test from 'node:test';
import { snapshot, result, uuid } from './market-fixtures.mjs';

const protocol = await import('../../market/web/protocol.ts').catch(() => ({}));
function parse(value) { assert.equal(typeof protocol.parseSnapshot, 'function'); return protocol.parseSnapshot(value); }

test('market DTO accepts exact complete twenty-row snapshot without coercion', () => {
  assert.deepEqual(parse(snapshot()), snapshot());
});

test('market DTO rejects schema, keys, numeric limits, enums and invalid identity/time', () => {
  for (const patch of [{ schema: 'other' }, { revision: true }, { revision: -1 }, { revision: 2 ** 53 },
    { generation: 1.5 }, { fault: 'network' }, { primary_state: 'ready' }, { extra: 1 },
    { incarnation: uuid.toUpperCase().replace('1111', 'ABCD') }, { config_id: 'A'.repeat(64) },
    { server_utc: '2026-02-30T12:00:00Z' }, { server_utc: '2026-11-10T12:00:00+00:00' },
    { rows: snapshot().rows.slice(0, 9) }, { rows: [...snapshot().rows, snapshot().rows[0]] }]) {
    assert.throws(() => parse(snapshot(patch)), JSON.stringify(patch));
  }
  const missing = snapshot(); delete missing.fault; assert.throws(() => parse(missing));
});

test('market row validation preserves config order and rejects invalid prices, duplicates and names', () => {
  for (const patch of [{ current_rappen: 0 }, { current_rappen: 1000001 }, { current_rappen: 401 },
    { initial_rappen: 750 }, { minimum_rappen: 800 }, { grid_rappen: 0 }, { remaining_lock_ms: 1800001 },
    { remaining_lock_ms: true }, { name: '' }, { name: 'x'.repeat(81) }, { name: 'line\nname' },
    { id: 'ä' }, { drink_version: -1 }, { last_activation_id: 'bad' }, { recovery_lock: 0 }, { extra: 1 }]) {
    const value = snapshot(); Object.assign(value.rows[0], patch); assert.throws(() => parse(value), JSON.stringify(patch));
  }
  const duplicate = snapshot(); duplicate.rows[1].id = duplicate.rows[0].id; assert.throws(() => parse(duplicate));
  const emoji = snapshot(); emoji.rows[0].name = '🪰'.repeat(80); assert.equal(parse(emoji).rows[0].name, emoji.rows[0].name);
});

test('challenge is bounded and tied to snapshot incarnation and revision', () => {
  const challenge = { id: uuid, incarnation: uuid, session_id: uuid, revision: 1, expires_in_ms: 5000 };
  assert.deepEqual(parse(snapshot({ challenge })).challenge, challenge);
  for (const patch of [{ expires_in_ms: 5001 }, { expires_in_ms: -1 }, { revision: 2 }, { incarnation: '22222222-2222-4222-8222-222222222222' }, { extra: 1 }]) {
    assert.throws(() => parse(snapshot({ challenge: { ...challenge, ...patch } })));
  }
});

test('proposal and resume parsers enforce exact result reason and status relationships', () => {
  assert.equal(typeof protocol.parseProposalResult, 'function');
  assert.deepEqual(protocol.parseProposalResult(result()), result());
  for (const patch of [{ reason: 'surprise' }, { status: 'rejected' }, { activation_id: null },
    { current_rappen: 0 }, { terminal_revision: 2 ** 53 }, { extra: 1 }]) assert.throws(() => protocol.parseProposalResult(result(patch)));
  assert.doesNotThrow(() => protocol.parseProposalResult(result({ status: 'rejected', reason: 'unknown_drink', activation_id: null, drink_version: null, current_rappen: null })));
  // Faults precede drink lookup; an unknown drink can therefore have a clock result.
  assert.doesNotThrow(() => protocol.parseProposalResult(result({ status: 'rejected', reason: 'clock', activation_id: null, drink_version: null, current_rappen: null })));
  const reply = { result: { command_id: 'resume-1', status: 'accepted', reason: 'resumed', terminal_revision: 2 },
    snapshot: snapshot({ revision: 3, paused: true }), superseding_reason: 'operator_pause' };
  assert.equal(typeof protocol.parseResumeReply, 'function');
  assert.deepEqual(protocol.parseResumeReply(reply), reply);
  for (const patch of [{ superseding_reason: 'unknown' }, { extra: 1 }, { result: { ...reply.result, reason: 'paused' } }]) assert.throws(() => protocol.parseResumeReply({ ...reply, ...patch }));
});

test('native price snapshots and nested replies keep exact declared source identity', () => {
  const value = snapshot({ schema: 'market-snapshot-v2', source_kind: 'native_measurement', readout_version: 'continuous-motor-drive/v1' });
  assert.equal(parse(value), value);
  for (const patch of [{ schema: 'market-snapshot-v1' }, { source_kind: 'synthetic' }, { readout_version: 'unknown' }, { extra: 1 }])
    assert.throws(() => parse({ ...value, ...patch }));
  const missing = { ...value }; delete missing.source_kind; assert.throws(() => parse(missing));
  assert.equal(protocol.parseAckReply({ accepted: true, reason: 'acknowledged', snapshot: value }).snapshot, value);
  assert.equal(protocol.parseClaimReply({ session_id: uuid, primary_token: 'a'.repeat(43), snapshot: value }).snapshot, value);
  assert.equal(protocol.parseResumeReply({ result: { command_id: 'r', status: 'accepted', reason: 'resumed', terminal_revision: 1 }, snapshot: value, superseding_reason: null }).snapshot, value);
});
