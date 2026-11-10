from dataclasses import asdict, replace
from uuid import uuid4

import pytest

from market.price_service import MarketConfig, MarketError, open_authority
from conftest import make_present, proposal, scenario


def test_full_jump(authority):
    make_present(authority)
    result = authority.run_fixture("jump", scenario())
    assert (result.status, result.reason, result.current_rappen, result.drink_version) == (
        "activated", "activated", 700, 1,
    )
    assert authority.snapshot().price_version == 1


def test_exact_cooldown(authority, clock):
    make_present(authority)
    authority.run_fixture("first", scenario())
    clock.advance(1_799_999)
    make_present(authority)
    assert authority.run_fixture("early", scenario(target=400, version=1)).reason == "cooldown"
    clock.advance(1)
    make_present(authority)
    assert authority.run_fixture("exact", scenario(target=400, version=1)).reason == "activated"


def test_independent_drinks(authority):
    make_present(authority)
    authority.run_fixture("first", scenario())
    assert authority.run_fixture("other", scenario("drink-01")).status == "activated"


def test_no_change_preserves_anchor(authority):
    make_present(authority)
    authority.run_fixture("first", scenario())
    before = authority.snapshot()
    deadline = authority._deadlines["drink-00"]
    count = authority._db.execute("SELECT count(*) FROM activations").fetchone()[0]
    assert authority.run_fixture("same", scenario(target=700, version=1)).status == "no_change"
    assert authority.snapshot().price_version == before.price_version
    assert authority._deadlines["drink-00"] == deadline
    assert authority._db.execute("SELECT count(*) FROM activations").fetchone()[0] == count


def test_expiry_alone_does_nothing(authority, clock):
    make_present(authority)
    authority.run_fixture("first", scenario())
    clock.advance(1_800_000)
    authority.maintain()
    assert authority.snapshot().price_version == 1
    assert authority.snapshot().rows[0].current_rappen == 700


@pytest.mark.parametrize(("age", "reason"), [
    (-1, "future_proposal"), (0, "activated"),
    (4_999_999_999, "activated"), (5_000_000_000, "expired"),
])
def test_sequence_age_and_reasons(authority, clock, age, reason):
    make_present(authority)
    event = proposal(authority, clock, created_ns=clock.ns - age, sequence=3)
    assert authority.submit_synthetic(event).reason == reason
    assert authority._high_water == 3
    assert authority.submit_synthetic(proposal(authority, clock, sequence=2)).reason == "reordered"
    assert authority.submit_synthetic(proposal(authority, clock, sequence=8, drink_id="drink-01")).status == "activated"


@pytest.mark.parametrize(("changes", "reason", "consumes"), [
    ({"config_id": "0" * 64}, "wrong_config", False),
    ({"source_session": str(uuid4())}, "wrong_source", False),
    ({"incarnation": str(uuid4())}, "wrong_incarnation", False),
    ({"generation": 0}, "wrong_generation", False),
    ({"drink_id": "unknown"}, "unknown_drink", True),
    ({"expected_drink_version": 3}, "stale_drink_version", True),
    ({"target_rappen": 750}, "out_of_range", True),
    ({"target_rappen": 425}, "off_grid", True),
])
def test_first_failure_reasons(authority, clock, changes, reason, consumes):
    make_present(authority)
    high = authority._high_water
    result = authority.submit_synthetic(proposal(authority, clock, **changes))
    assert result.reason == reason
    assert authority._high_water == high + int(consumes)
    assert (result.drink_version is None) == (reason == "unknown_drink")


@pytest.mark.parametrize("target", [700, 400, 750])
def test_immutable_idempotency_after_restart(authority, config, clock, tmp_path, target):
    make_present(authority)
    event = proposal(authority, clock, target_rappen=target)
    expected = asdict(authority.submit_synthetic(event))
    clock.advance(10_000)
    authority.pause()
    assert asdict(authority.submit_synthetic(event)) == expected
    high = authority._high_water
    with pytest.raises(MarketError, match="idempotency_conflict"):
        authority.submit_synthetic(replace(event, target_rappen=650))
    assert authority._high_water == high
    authority.close()
    with open_authority(config, tmp_path / "market.sqlite3", clock) as reopened:
        assert asdict(reopened.submit_synthetic(event)) == expected
        assert asdict(reopened.get_event(event.event_id)) == expected


def test_fixture_mapping_retry_conflict(authority, clock):
    make_present(authority)
    result = authority.run_fixture("fixture", scenario())
    clock.advance(10_000)
    assert authority.run_fixture("fixture", scenario()) == result
    with pytest.raises(MarketError, match="idempotency_conflict"):
        authority.run_fixture("fixture", scenario(target=650))


@pytest.mark.parametrize("changes", [
    {"target_rappen": True}, {"target_rappen": 0}, {"sequence": True},
    {"sequence": 0}, {"generation": 2 ** 53}, {"created_ns": -1},
    {"event_id": "no-uuid"}, {"request_id": "ü"},
    {"recorded_utc": "2026-01-01"}, {"model_interval_ms": (5, 4)},
])
def test_invalid_proposals_do_not_write(authority, clock, changes):
    event = proposal(authority, clock, **changes)
    before = authority._db.total_changes
    with pytest.raises(MarketError, match="invalid_request"):
        authority.submit_synthetic(event)
    assert authority._db.total_changes == before


@pytest.mark.parametrize("change", [
    {"minimum_rappen": True}, {"name": ""}, {"name": "x" * 81},
    {"name": "a\n"}, {"name": "\ud800"}, {"id": "ä"},
    {"initial_rappen": 401}, {"maximum_rappen": 1_000_001},
])
def test_invalid_config(config, change):
    with pytest.raises(MarketError, match="invalid_request"):
        changed = replace(config.drinks[0], **change)
        MarketConfig(config.schema, (changed,) + config.drinks[1:])


def test_config_unknown_duplicate_and_bounds(config):
    raw = asdict(config)
    raw["unexpected"] = 1
    with pytest.raises(MarketError, match="invalid_request"):
        MarketConfig.from_dict(raw)
    with pytest.raises(MarketError, match="invalid_request"):
        MarketConfig(config.schema, (config.drinks[0],) * 10)
    with pytest.raises(MarketError, match="invalid_request"):
        MarketConfig(config.schema, config.drinks[:9])


def test_json_safe_exhaustion(authority):
    make_present(authority)
    authority._db.execute("UPDATE market SET price_version=9007199254740991")
    with pytest.raises(MarketError, match="capacity"):
        authority.run_fixture("exhausted", scenario())
    assert authority.snapshot().paused
    assert authority.snapshot().fault == "capacity"


def test_capacity_fence_is_durable_after_observation(authority, config, clock, tmp_path):
    make_present(authority)
    authority._high_water = 9_007_199_254_740_991
    with pytest.raises(MarketError, match="capacity"):
        authority.run_fixture("exhausted-source", scenario())
    assert authority.snapshot().fault == "capacity"
    assert authority._db.execute("SELECT fault FROM market").fetchone()[0] == "capacity"


def test_reject_non_rfc3339_utc(authority, clock):
    with pytest.raises(MarketError, match="invalid_request"):
        authority.submit_synthetic(proposal(authority, clock, recorded_utc="2026-W46-2T00:00:00Z"))


@pytest.mark.parametrize("later_fault", [None, "clock", "storage"])
def test_capacity_survives_immediate_close_and_later_fault(
    authority, config, clock, tmp_path, monkeypatch, later_fault,
):
    import sqlite3

    session = make_present(authority)
    outcome = authority.submit_synthetic(proposal(
        authority, clock, sequence=9_007_199_254_740_991, target_rappen=400,
    ))
    assert outcome.reason == "no_change"
    with pytest.raises(MarketError, match="capacity"):
        authority.run_fixture("exhausted-immediately", scenario())
    # No snapshot/maintenance call may be needed to make the fence durable.
    if later_fault == "clock":
        clock.ns -= 1
        assert authority.snapshot().fault == "clock"
        clock.ns += 1
    elif later_fault == "storage":
        original = authority._commit_transaction
        monkeypatch.setattr(authority, "_commit_transaction", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("later persistence fault")))
        assert authority.pause().fault == "storage"
        monkeypatch.setattr(authority, "_commit_transaction", original)
    authority.close()
    with open_authority(config, tmp_path / "market.sqlite3", clock) as reopened:
        current = make_present(reopened, resume=False)
        reply = reopened.resume("cannot-clear-capacity", ingress_epoch=reopened.capture_safety_epoch())
        assert reply.result.status == "rejected" and reply.result.reason == "capacity"
        assert reply.snapshot.paused and reply.snapshot.fault == "capacity"
        assert reopened.run_fixture("still-fenced", scenario()).reason == "capacity"
        assert reopened.snapshot().price_version == 0


def test_capacity_persistence_failure_reports_storage_without_terminal(
    authority, clock, monkeypatch,
):
    import sqlite3

    make_present(authority)
    authority.submit_synthetic(proposal(
        authority, clock, sequence=9_007_199_254_740_991, target_rappen=400,
    ))
    before = authority._ledger_count()
    original = authority._commit_transaction
    monkeypatch.setattr(authority, "_commit_transaction", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("capacity fence cannot commit")))
    with pytest.raises(MarketError, match="storage"):
        authority.run_fixture("failed-capacity-fence", scenario())
    assert authority._fault == "storage" and authority._paused
    assert authority._ledger_count() == before
    assert authority._db.execute("SELECT count(*) FROM fixture_requests WHERE request_id='failed-capacity-fence'").fetchone()[0] == 0
    monkeypatch.setattr(authority, "_commit_transaction", original)
    assert authority.resume("capacity-after-storage-error", ingress_epoch=authority.capture_safety_epoch()).result.reason == "capacity"
