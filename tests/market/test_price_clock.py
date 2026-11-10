from dataclasses import replace
from datetime import timedelta

import pytest

from market.price_service import ClockSample, MarketError, open_authority
from conftest import make_present, scenario


def test_postcommit_anchor_includes_latency(authority, clock, monkeypatch):
    make_present(authority)
    original = authority._commit_transaction
    def slow_commit():
        clock.advance(2500)
        original()
    monkeypatch.setattr(authority, "_commit_transaction", slow_commit)
    assert authority.run_fixture("slow", scenario()).status == "activated"
    monkeypatch.setattr(authority, "_commit_transaction", original)
    assert authority.snapshot().rows[0].remaining_lock_ms == 1_800_000
    assert authority.snapshot().rows[1].remaining_lock_ms == 0


def test_clock_fault_after_commit_preserves_price(authority, clock, monkeypatch):
    make_present(authority)
    original = authority._commit_transaction
    def commit_then_fault():
        original()
        clock.ns = -1
    monkeypatch.setattr(authority, "_commit_transaction", commit_then_fault)
    result = authority.run_fixture("clockfault", scenario())
    assert result.status == "activated"
    snapshot = authority.snapshot()
    assert snapshot.rows[0].current_rappen == 700
    assert snapshot.paused and snapshot.fault == "clock"
    assert authority._db.execute("SELECT fault FROM market").fetchone()[0] == "clock"


def test_backward_clock_fences(authority, clock):
    make_present(authority)
    before = authority.snapshot()
    clock.ns -= 1
    after = authority.snapshot()
    assert after.fault == "clock" and after.paused
    assert after.generation > before.generation


@pytest.mark.parametrize("value", [True, -1, 1.5, None, 2 ** 63])
def test_invalid_clock_samples(authority, clock, value):
    clock.ns = value
    assert authority.snapshot().fault == "clock"


def test_clock_exception_and_invalid_utc(authority, clock, monkeypatch):
    monkeypatch.setattr(clock, "sample", lambda: ClockSample(clock.ns, None))
    assert authority.snapshot().fault == "clock"


def test_unavailable_clock_does_not_ack_or_rejoin(authority, clock, monkeypatch):
    session = make_present(authority)
    previous = authority.snapshot(session).challenge
    def unavailable():
        raise OSError("clock unavailable")
    monkeypatch.setattr(clock, "sample", unavailable)
    snapshot = authority.snapshot(session)
    assert snapshot.fault == "clock" and snapshot.challenge is None
    assert not authority.ack_primary(session, previous.id).accepted
    assert authority.snapshot().primary_state == "absent"


def test_utc_jumps_do_not_unlock(authority, clock):
    make_present(authority)
    authority.run_fixture("jump", scenario())
    before = authority.snapshot().rows[0]
    clock.utc += timedelta(days=100)
    after = authority.snapshot().rows[0]
    assert after.remaining_lock_ms == before.remaining_lock_ms == 1_800_000
    assert after.estimated_eligible_utc != before.estimated_eligible_utc
    clock.advance(nanoseconds=1)
    assert authority.snapshot().rows[0].remaining_lock_ms == 1_800_000


def test_repeated_restart_full_lock(authority, config, clock, tmp_path):
    make_present(authority)
    authority.run_fixture("jump", scenario())
    authority.close()
    for _ in range(3):
        clock.advance(2_000_000)
        with open_authority(config, tmp_path / "market.sqlite3", clock) as reopened:
            snapshot = reopened.snapshot()
            assert snapshot.paused
            assert snapshot.rows[0].recovery_lock
            assert snapshot.rows[0].remaining_lock_ms == 1_800_000
            assert not snapshot.rows[1].recovery_lock
            assert snapshot.rows[1].remaining_lock_ms == 0
