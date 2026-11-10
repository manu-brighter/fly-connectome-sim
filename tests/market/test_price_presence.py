from dataclasses import asdict
import sqlite3
import threading
from uuid import uuid4

import pytest

from market.price_service import MarketError, open_authority
from conftest import make_present, scenario


def test_claim_render_ack_and_readonly_challenge(authority):
    initial = authority.snapshot()
    claim = authority.claim_primary(initial.incarnation, "claim")
    rendered = authority.snapshot(claim.session_id)
    assert authority.snapshot().challenge is None
    reply = authority.ack_primary(claim.session_id, rendered.challenge.id)
    assert reply.accepted and reply.reason == "acknowledged"
    assert reply.snapshot.revision == rendered.revision + 1
    assert reply.snapshot.primary_state == "present" and reply.snapshot.challenge is None
    again = authority.snapshot(claim.session_id)
    acknowledged = authority.ack_primary(claim.session_id, again.challenge.id)
    assert acknowledged.accepted and acknowledged.snapshot.revision == reply.snapshot.revision


def test_revision_change_rejects_old_ack(authority):
    session = make_present(authority)
    rendered = authority.snapshot(session)
    authority.run_fixture("price", scenario())
    assert authority.ack_primary(session, rendered.challenge.id).reason == "stale_revision"


def test_presence_expiry_equality_fences_once_before_reconnect(authority, clock):
    session = make_present(authority)
    before = authority.snapshot()
    clock.advance(5000)
    rendered = authority.snapshot(session)
    assert rendered.primary_state == "absent"
    assert rendered.generation == before.generation + 1
    assert rendered.revision == before.revision + 1
    assert authority.snapshot().revision == rendered.revision
    assert authority.ack_primary(session, rendered.challenge.id).accepted


def test_snapshot_does_not_renew_lease(authority, clock):
    session = make_present(authority)
    clock.advance(4999)
    authority.snapshot(session)
    clock.advance(1)
    assert authority.snapshot().primary_state == "absent"


def test_awaiting_ack_timeout_and_replacement(authority, clock):
    start = authority.snapshot()
    old = authority.claim_primary(start.incarnation, "first")
    clock.advance(5000)
    expired = authority.snapshot()
    assert expired.primary_state == "absent" and expired.generation == start.generation
    replacement = authority.claim_primary(start.incarnation, "second")
    assert replacement.session_id != old.session_id
    assert replacement.primary_token != old.primary_token
    assert authority.resolve_primary_token(old.primary_token) is None
    assert authority.resolve_primary_token(replacement.primary_token) == replacement.session_id
    with pytest.raises(MarketError, match="superseded"):
        authority.claim_primary(start.incarnation, "first")
    with pytest.raises(MarketError, match="unauthorized"):
        authority.snapshot(old.session_id)
    assert not authority.ack_primary(old.session_id, old.snapshot.challenge.id).accepted


def test_claim_history_bound(authority, clock):
    incarnation = authority.snapshot().incarnation
    for i in range(64):
        current = authority.claim_primary(incarnation, f"claim-{i}")
        clock.advance(5000)
    with pytest.raises(MarketError, match="claim_capacity"):
        authority.claim_primary(incarnation, "claim-64")
    assert authority.claim_primary(incarnation, "claim-63").session_id == current.session_id
    fresh = authority.snapshot(current.session_id)
    assert authority.ack_primary(current.session_id, fresh.challenge.id).accepted
    with pytest.raises(MarketError, match="wrong_incarnation"):
        authority.claim_primary(str(uuid4()), "claim-63")


def test_savepoint_retains_presence_fence(authority, clock, config, tmp_path):
    make_present(authority)
    before = authority.snapshot()
    fired = False
    def expire_after_tentative_activation():
        nonlocal fired
        if not fired and authority._db.in_transaction and authority._db.execute("SELECT count(*) FROM activations").fetchone()[0]:
            fired = True
            clock.advance(5000)
    clock.callback = expire_after_tentative_activation
    result = authority.run_fixture("raced", scenario())
    clock.callback = None
    assert fired and result.status == "rejected" and result.reason == "wrong_generation"
    after = authority.snapshot()
    assert after.primary_state == "absent"
    assert after.generation == before.generation + 1 and after.revision == before.revision + 1
    assert after.price_version == 0 and after.rows[0].current_rappen == 400
    assert authority._high_water == 1
    persisted = authority._db.execute("SELECT primary_state,generation,revision FROM market").fetchone()
    assert tuple(persisted) == ("absent", after.generation, after.revision)
    assert authority._db.execute("SELECT count(*) FROM activations").fetchone()[0] == 0
    authority.close()
    with open_authority(config, tmp_path / "market.sqlite3", clock) as reopened:
        assert reopened.run_fixture("raced", scenario()) == result


def test_presence_fence_survives_persistence_failure(authority, clock, monkeypatch):
    make_present(authority)
    clock.advance(5000)
    monkeypatch.setattr(authority, "_commit_transaction", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("injected")))
    with pytest.raises(MarketError, match="storage"):
        authority.maintain()
    assert authority._fault == "storage" and authority._paused
    assert authority._primary_state == "absent"


def _later_pause_defeats_resume(authority, clock, monkeypatch, *, during_commit):
    make_present(authority)
    authority.pause()
    epoch = authority.capture_safety_epoch()
    entered, release = threading.Event(), threading.Event()
    original = authority._commit_transaction if during_commit else clock.callback
    def blocked(*args):
        entered.set()
        assert release.wait(5)
        return original(*args) if original else None
    if during_commit:
        monkeypatch.setattr(authority, "_commit_transaction", blocked)
    else:
        def before_commit():
            if authority._db.in_transaction and not authority._paused:
                blocked()
        clock.callback = before_commit
    replies, errors = [], []
    def resume():
        try:
            replies.append(authority.resume("racing-resume", ingress_epoch=epoch))
        except BaseException as error:
            errors.append(error)
    worker = threading.Thread(target=resume)
    worker.start()
    assert entered.wait(5)
    later_epoch = authority.request_safety_pause("operator_pause")
    assert later_epoch > epoch
    release.set()
    worker.join(5)
    assert not worker.is_alive() and not errors
    if during_commit:
        monkeypatch.setattr(authority, "_commit_transaction", original)
    else:
        clock.callback = original
    reply = replies[0]
    assert reply.snapshot.paused and reply.superseding_reason == "operator_pause"
    generation = reply.snapshot.generation
    assert authority.snapshot().generation == generation
    retry = authority.resume("racing-resume", ingress_epoch=later_epoch)
    assert retry.result == reply.result and retry.snapshot.paused
    assert authority.resume("fresh-resume", ingress_epoch=later_epoch).result.status == "accepted"
    assert not authority.snapshot().paused
    authority.pause()
    before = authority.snapshot()
    authority.pause()
    after = authority.snapshot()
    assert (after.revision, after.generation) == (before.revision, before.generation)


def test_later_pause_defeats_resume_before_commit(authority, clock, monkeypatch):
    _later_pause_defeats_resume(authority, clock, monkeypatch, during_commit=False)


def test_later_pause_defeats_resume_during_commit(authority, clock, monkeypatch):
    _later_pause_defeats_resume(authority, clock, monkeypatch, during_commit=True)


def test_same_drink_attempts_serialize(authority):
    make_present(authority)
    ready = threading.Barrier(3)
    results, errors = [], []
    def attempt(request):
        try:
            ready.wait(5)
            results.append(authority.run_fixture(request, scenario()))
        except BaseException as error:
            errors.append(error)
    workers = [threading.Thread(target=attempt, args=(f"same-{i}",)) for i in range(2)]
    for worker in workers:
        worker.start()
    ready.wait(5)
    for worker in workers:
        worker.join(5)
    assert not errors and all(not worker.is_alive() for worker in workers)
    assert sorted(result.reason for result in results) == ["activated", "stale_drink_version"]
    assert authority.snapshot().price_version == 1


def test_pause_during_proposal_commit_keeps_committed_price(authority, clock, monkeypatch):
    make_present(authority)
    before = authority.snapshot()
    original = authority._commit_transaction
    fired = False
    def pause_during_commit():
        nonlocal fired
        if not fired:
            fired = True
            authority.request_safety_pause("operator_pause")
            clock.advance(5000)
        original()
    monkeypatch.setattr(authority, "_commit_transaction", pause_during_commit)
    result = authority.run_fixture("slow-price", scenario())
    assert result.status == "activated"
    snapshot = authority.snapshot()
    assert snapshot.paused and snapshot.primary_state == "absent"
    assert snapshot.generation > before.generation
    assert snapshot.rows[0].current_rappen == 700
    assert snapshot.rows[0].remaining_lock_ms == 1_800_000


def test_savepoint_expiry_and_storage_failure_keeps_memory_fence(authority, clock, monkeypatch):
    make_present(authority)
    before = authority.snapshot()
    fired = False
    def expire():
        nonlocal fired
        if not fired and authority._db.in_transaction and authority._db.execute("SELECT count(*) FROM activations").fetchone()[0]:
            fired = True
            clock.advance(5000)
    clock.callback = expire
    monkeypatch.setattr(authority, "_commit_transaction", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("injected")))
    with pytest.raises(MarketError, match="storage"):
        authority.run_fixture("failed-fence", scenario())
    clock.callback = None
    assert fired and authority._primary_state == "absent" and authority._paused
    assert authority._generation > before.generation
    assert authority._db.execute("SELECT count(*) FROM activations").fetchone()[0] == 0
    assert authority._db.execute("SELECT count(*) FROM fixture_requests").fetchone()[0] == 0


def test_overload_requires_new_explicit_resume(authority):
    make_present(authority)
    epoch = authority.capture_safety_epoch()
    authority.request_safety_pause("overload")
    snapshot = authority.snapshot()
    assert snapshot.paused and snapshot.fault == "overload"
    assert authority.resume("old-epoch", ingress_epoch=epoch).result.reason == "superseded"
    assert authority.resume("new-epoch", ingress_epoch=authority.capture_safety_epoch()).result.reason == "resumed"
    assert authority.snapshot().fault is None and not authority.snapshot().paused
