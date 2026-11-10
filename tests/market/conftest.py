from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from market.price_service import (
    ClockSample, DrinkConfig, FixtureScenario, MarketConfig, Proposal,
    open_authority,
)


class FakeClock:
    def __init__(self):
        self.ns = 10_000_000_000
        self.utc = datetime(2026, 11, 10, tzinfo=timezone.utc)
        self.callback = None

    def sample(self):
        if self.callback:
            self.callback()
        return ClockSample(self.ns, self.utc)

    def describe(self):
        return {"implementation": "injected-test-clock", "monotonic": True,
                "adjustable": False, "resolution_ns": 1}

    def advance(self, milliseconds=0, *, nanoseconds=0):
        delta = milliseconds * 1_000_000 + nanoseconds
        self.ns += delta
        self.utc += timedelta(microseconds=delta / 1000)


@pytest.fixture
def config():
    return MarketConfig("market-config-v1", tuple(
        DrinkConfig(f"drink-{i:02d}", f"Testgetränk {i + 1:02d}", 400, 700, 50, 400)
        for i in range(20)
    ))


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def authority(tmp_path, config, clock):
    result = open_authority(config, tmp_path / "market.sqlite3", clock)
    yield result
    result.close()


def make_present(authority, *, resume=True):
    snapshot = authority.snapshot()
    if snapshot.primary_state in ("unclaimed", "absent") and authority._primary_session is None:
        claim = authority.claim_primary(snapshot.incarnation, uuid4().hex)
        session = claim.session_id
    else:
        session = authority._primary_session
    snapshot = authority.snapshot(session)
    ack = authority.ack_primary(session, snapshot.challenge.id)
    assert ack.accepted, ack.reason
    if resume:
        reply = authority.resume(uuid4().hex, ingress_epoch=authority.capture_safety_epoch())
        assert reply.result.status == "accepted", reply.result
    return session


def scenario(drink="drink-00", target=700, version=0):
    return FixtureScenario("synthetic-price-v1", drink, target, version)


def proposal(authority, clock, **changes):
    current = authority.snapshot()
    value = Proposal(
        "market-proposal-v1", str(uuid4()), uuid4().hex, "synthetic_fixture",
        authority._source_session, authority._high_water + 1, current.generation,
        current.config_id, "synthetic-price-v1", current.incarnation,
        "drink-00", 700, 0, clock.ns, None,
        clock.utc.isoformat().replace("+00:00", "Z"),
    )
    return replace(value, **changes)
