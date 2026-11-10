from dataclasses import asdict
from pathlib import Path
import sqlite3

import pytest

from market.fixtures import load_config, parse_scenario
from market.price_service import MarketError, open_authority

from conftest import make_present


SCENARIO = {"fixture_id": "synthetic-price-v1", "drink_id": "drink-00",
            "target_rappen": 700, "expected_drink_version": 0}


def test_exact_twenty_row_example(config):
    actual = load_config(Path("examples/market-synthetic.json"))
    assert actual == config
    assert asdict(parse_scenario(SCENARIO)) == SCENARIO


@pytest.mark.parametrize("change", [
    {"fixture_id": "neural"}, {"drink_id": "../bad"}, {"target_rappen": True},
    {"target_rappen": 0}, {"target_rappen": 1000001}, {"expected_drink_version": -1},
    {"expected_drink_version": 9007199254740992}, {"expected_drink_version": False},
    {"created_ns": 1}, {"sequence": 1}, {"source_kind": "synthetic_fixture"},
    {"model_interval_ms": None}, {"source_session": "invented"},
])
def test_strict_scenario(change):
    with pytest.raises(MarketError, match="invalid_request"):
        parse_scenario(SCENARIO | change)


@pytest.mark.parametrize("payload", [None, [], {}, SCENARIO | {"extra": 1}])
def test_missing_or_non_object_scenario(payload):
    with pytest.raises(MarketError, match="invalid_request"):
        parse_scenario(payload)


@pytest.mark.parametrize("text", [
    '{"schema":"market-config-v1","schema":"market-config-v1","drinks":[]}',
    '{"schema":"market-config-v1","drinks":NaN}', 'null', '\ufeff{}',
])
def test_config_rejects_invalid_json(tmp_path, text):
    path = tmp_path / "invalid.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(MarketError, match="invalid_request"):
        load_config(path)


def test_factory_restart_deduplication_and_real_synthetic_labels(tmp_path, config, clock, monkeypatch):
    path = tmp_path / "factory.sqlite3"
    with open_authority(config, path, clock) as authority:
        make_present(authority)
        captured = []
        original = authority._submit_locked
        def capture(proposal, *args):
            captured.append(proposal)
            return original(proposal, *args)
        monkeypatch.setattr(authority, "_submit_locked", capture)
        result = authority.run_fixture("same-request", parse_scenario(SCENARIO))
        assert result.status == "activated"
        assert captured[0].source_kind == "synthetic_fixture"
        assert captured[0].readout_version == "synthetic-price-v1"
        assert captured[0].model_interval_ms is None
        assert authority._db.execute("SELECT readout_version FROM activations").fetchone()[0] == "synthetic-price-v1"
    with open_authority(config, path, clock) as authority:
        assert authority.run_fixture("same-request", parse_scenario(SCENARIO)) == result
        assert authority.get_event(result.event_id) == result
        with pytest.raises(MarketError, match="idempotency_conflict"):
            authority.run_fixture("same-request", parse_scenario(SCENARIO | {"target_rappen": 650}))


def test_factory_rollback_accepts_no_mapping(authority, monkeypatch):
    original = authority._commit_transaction
    def failed_commit():
        raise sqlite3.OperationalError("injected commit failure")
    monkeypatch.setattr(authority, "_commit_transaction", failed_commit)
    with pytest.raises(MarketError, match="storage"):
        authority.run_fixture("rollback-request", parse_scenario(SCENARIO))
    monkeypatch.setattr(authority, "_commit_transaction", original)
    assert authority._db.execute("SELECT count(*) FROM fixture_requests").fetchone()[0] == 0
