from dataclasses import replace
import json
import sqlite3
import subprocess
import sys

import pytest

from market.price_service import MarketError, open_authority
from conftest import make_present, proposal, scenario


def fill_controls(authority, count):
    with authority._transaction():
        authority._db.executemany(
            "INSERT INTO control_results(command_id,result_json) VALUES (?,?)",
            ((f"filler-{i}", '{}') for i in range(count)),
        )


def test_rollback_accepts_no_mapping(authority, monkeypatch):
    make_present(authority)
    original = authority._commit_transaction
    monkeypatch.setattr(authority, "_commit_transaction", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("disk error")))
    with pytest.raises(MarketError, match="storage"):
        authority.run_fixture("lost", scenario())
    assert not authority._db.in_transaction
    for table in ("fixture_requests", "proposal_results", "activations"):
        assert authority._db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    monkeypatch.setattr(authority, "_commit_transaction", original)
    assert authority.snapshot().fault == "storage"


def test_fixture_worst_case_row_reservation(authority):
    make_present(authority)
    existing = authority._ledger_count()
    fill_controls(authority, 8998 - existing)
    with pytest.raises(MarketError, match="capacity"):
        authority.run_fixture("over-fixture-ceiling", scenario())
    assert authority._ledger_count() == 8998
    assert authority.snapshot().fault == "capacity"
    assert authority.pause().durable


def test_full_ledger_pause_without_audit(authority):
    make_present(authority)
    fill_controls(authority, 10_000 - authority._ledger_count())
    reply = authority.pause()
    assert reply.paused and reply.durable and not reply.audit_recorded
    assert authority._ledger_count() == 10_000
    assert authority._db.execute("SELECT paused FROM market").fetchone()[0] == 1


def test_failed_durable_pause_latches(authority, monkeypatch):
    make_present(authority)
    monkeypatch.setattr(authority, "_commit_transaction", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("injected")))
    reply = authority.pause()
    assert reply.paused and not reply.durable and reply.fault == "storage"


def test_sqlite_constraints_and_page_cap(authority):
    db = authority._db
    expected = {"page_size": 4096, "max_page_count": 16384, "foreign_keys": 1,
                "synchronous": 2, "busy_timeout": 1000, "cache_spill": 0}
    for name, value in expected.items():
        assert db.execute(f"PRAGMA {name}").fetchone()[0] == value
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE drinks SET current_rappen=0")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE market SET generation=-1")
    with pytest.raises(sqlite3.DatabaseError):
        db.execute("ATTACH ':memory:' AS forbidden")
    with pytest.raises(sqlite3.DatabaseError):
        db.execute("PRAGMA journal_mode=WAL")
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_sqlite_full_failure_injected_commit(authority, monkeypatch):
    make_present(authority)
    original = authority._commit_transaction
    def disk_full():
        raise sqlite3.OperationalError("database or disk is full")
    monkeypatch.setattr(authority, "_commit_transaction", disk_full)
    with pytest.raises(MarketError, match="storage"):
        authority.run_fixture("full", scenario())
    assert authority._fault == "storage" and authority._paused
    monkeypatch.setattr(authority, "_commit_transaction", original)


def test_sqlite_full_failure(authority):
    payload = json.dumps("x" * (1024 * 1024))
    with pytest.raises(MarketError, match="storage") as caught:
        with authority._transaction():
            for index in range(70):
                authority._db.execute("INSERT INTO control_results VALUES (?,?)", (f"full-{index}", payload))
    assert isinstance(caught.value.__cause__, sqlite3.OperationalError)
    assert caught.value.__cause__.sqlite_errorcode == sqlite3.SQLITE_FULL
    assert authority._paused and authority._fault == "storage"
    assert authority._db.execute("SELECT count(*) FROM control_results").fetchone()[0] == 0
    assert authority.db_path.stat().st_size <= 64 * 1024 * 1024


def test_runtime_rollback_journal_envelope(authority, monkeypatch):
    original = authority._commit_transaction
    payload = json.dumps("x" * 131_072)
    with authority._transaction():
        authority._db.executemany("INSERT INTO control_results VALUES (?,?)", ((f"journal-{i}", payload) for i in range(80)))
    evidence = {}
    def inspect_journal():
        journal = authority.db_path.with_name(authority.db_path.name + "-journal")
        data = journal.read_bytes()
        sector_size = int.from_bytes(data[20:24], "big")
        page_size = int.from_bytes(data[24:28], "big")
        assert 512 <= sector_size <= 65536 and sector_size & (sector_size - 1) == 0
        assert page_size == 4096 and (len(data) - sector_size) % (page_size + 8) == 0
        page_ids = [int.from_bytes(data[offset:offset + 4], "big")
                    for offset in range(sector_size, len(data), page_size + 8)]
        assert len(page_ids) == len(set(page_ids))
        evidence.update(
            sqlite=sqlite3.sqlite_version, page_count=authority._db.execute("PRAGMA page_count").fetchone()[0],
            page_size=authority._db.execute("PRAGMA page_size").fetchone()[0],
            cache_spill=authority._db.execute("PRAGMA cache_spill").fetchone()[0],
            journal_bytes=len(data), database_bytes=authority.db_path.stat().st_size,
            header_hex=data[:28].hex(),
            journal_sector_size=sector_size, preimage_records=len(page_ids), unique_preimages=True,
        )
        original()
    monkeypatch.setattr(authority, "_commit_transaction", inspect_journal)
    with authority._transaction():
        authority._db.execute("UPDATE control_results SET result_json=?", (json.dumps("y" * 131_072),))
    assert evidence["journal_bytes"] > 8 * 1024 * 1024
    assert evidence["journal_bytes"] <= evidence["page_count"] * 4104 + 2 * 65536 < 72 * 1024 * 1024
    assert evidence["journal_bytes"] + evidence["database_bytes"] <= 136 * 1024 * 1024
    assert evidence["cache_spill"] == 0 and evidence["page_size"] == 4096
    print("JOURNAL_EVIDENCE=" + json.dumps(evidence, sort_keys=True))


def test_sqlite_rejects_fractional_counters(authority):
    with pytest.raises(sqlite3.IntegrityError):
        authority._db.execute("UPDATE market SET generation=1.5")


def test_control_reserve_reaches_total_cap(authority):
    make_present(authority)
    fill_controls(authority, 9999 - authority._ledger_count())
    assert authority.resume("last-control", ingress_epoch=authority.capture_safety_epoch()).result.status == "accepted"
    assert authority._ledger_count() == 10_000
    with pytest.raises(MarketError, match="capacity"):
        authority.resume("too-many-controls", ingress_epoch=authority.capture_safety_epoch())
    assert authority.pause().durable


def test_ownership_released_by_process_death(tmp_path, config, clock):
    path = tmp_path / "process.sqlite3"
    child_code = """
import json, os, sys
from pathlib import Path
from market.price_service import MarketConfig, open_authority
authority = open_authority(MarketConfig.from_dict(json.loads(sys.argv[2])), Path(sys.argv[1]))
print('owned', flush=True)
sys.stdin.buffer.read(1)
os._exit(0)
"""
    from dataclasses import asdict
    child = subprocess.Popen(
        [sys.executable, "-u", "-c", child_code, str(path), json.dumps(asdict(config))],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        assert child.stdout.readline().strip() == b"owned"
        with pytest.raises(MarketError, match="ownership"):
            open_authority(config, path, clock)
        stdout, stderr = child.communicate(b"x", timeout=5)
        assert child.returncode == 0 and not stderr
        with open_authority(config, path, clock) as reopened:
            assert reopened.snapshot().paused
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


@pytest.mark.parametrize("operation_name", ["snapshot", "run_fixture", "submit_synthetic"])
def test_closed_authority_fails_with_domain_error(authority, operation_name):
    event = proposal(authority, authority._clock)
    authority.close()
    operations = {
        "snapshot": authority.snapshot,
        "run_fixture": lambda: authority.run_fixture("closed-fixture", scenario()),
        "submit_synthetic": lambda: authority.submit_synthetic(event),
    }
    with pytest.raises(MarketError, match="storage"):
        operations[operation_name]()


@pytest.mark.parametrize("counter", ["revision", "generation"])
def test_pause_remains_durable_at_counter_exhaustion(authority, counter):
    make_present(authority)
    setattr(authority, "_" + counter, 9_007_199_254_740_991)
    authority._db.execute(f"UPDATE market SET {counter}=9007199254740991")
    reply = authority.pause()
    assert reply.paused and reply.durable and reply.fault == "capacity"
    row = authority._db.execute("SELECT paused,fault FROM market").fetchone()
    assert tuple(row) == (1, "capacity")


def test_ownership_and_idempotent_close(authority, config, clock, tmp_path):
    with pytest.raises(MarketError, match="ownership"):
        open_authority(config, tmp_path / "market.sqlite3", clock)
    authority.close()
    authority.close()
    with open_authority(config, tmp_path / "market.sqlite3", clock):
        pass
    assert (tmp_path / "market.sqlite3.owner.lock").exists()


def test_exact_reopen_config(authority, config, clock, tmp_path):
    authority.close()
    changed = replace(config, drinks=(replace(config.drinks[0], name="different"),) + config.drinks[1:])
    with pytest.raises(MarketError, match="config_mismatch"):
        open_authority(changed, tmp_path / "market.sqlite3", clock)


@pytest.mark.parametrize("kind", ["db", "journal", "broken", "incompatible"])
def test_refuse_oversize_or_incompatible(tmp_path, config, clock, kind):
    path = tmp_path / "bad.sqlite3"
    if kind in ("db", "journal"):
        target = path if kind == "db" else path.with_name(path.name + "-journal")
        with target.open("wb") as output:
            output.truncate((64 if kind == "db" else 72) * 1024 * 1024 + 1)
    elif kind == "broken":
        path.write_bytes(b"not a sqlite database")
    else:
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE unrelated(x)")
    with pytest.raises(MarketError, match="storage"):
        open_authority(config, path, clock)
