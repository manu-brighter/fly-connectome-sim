"""Durable local synthetic prices, clocks, primary presence and safety fencing."""

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from typing import Protocol
import unicodedata
from uuid import UUID, uuid4

from .ownership import DatabaseOwnership


MAX_COUNTER = 9_007_199_254_740_991
MAX_NS = (1 << 63) - 1
LEASE_NS = 5_000_000_000
COOLDOWN_NS = 1_800_000_000_000
DB_LIMIT = 64 * 1024 * 1024
JOURNAL_LIMIT = 72 * 1024 * 1024
_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z", re.ASCII)
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z\Z", re.ASCII)


class MarketError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _integer(value, low=0, high=MAX_COUNTER):
    return type(value) is int and low <= value <= high


def _require(condition):
    if not condition:
        raise MarketError("invalid_request")


def _identifier(value):
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _uuid(value):
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _utc(value):
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        return "T" in value and parsed.utcoffset() == timedelta(0)
    except ValueError:
        return False


def _label(value):
    return value.isoformat().replace("+00:00", "Z")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _exact_dict(value, cls):
    _require(type(value) is dict and set(value) == {field.name for field in fields(cls)})


@dataclass(frozen=True)
class DrinkConfig:
    id: str
    name: str
    minimum_rappen: int
    maximum_rappen: int
    grid_rappen: int
    initial_rappen: int

    def __post_init__(self):
        _require(_identifier(self.id))
        _require(isinstance(self.name, str) and 1 <= len(self.name) <= 80)
        try:
            _require(len(self.name.encode("utf-8")) <= 320)
        except UnicodeError:
            raise MarketError("invalid_request") from None
        _require(not any(unicodedata.category(char).startswith("C") for char in self.name))
        amounts = (self.minimum_rappen, self.maximum_rappen, self.grid_rappen, self.initial_rappen)
        _require(all(_integer(value, 1, 1_000_000) for value in amounts))
        _require(self.minimum_rappen <= self.initial_rappen <= self.maximum_rappen)
        _require(all(value % self.grid_rappen == 0 for value in (
            self.minimum_rappen, self.maximum_rappen, self.initial_rappen,
        )))

    @classmethod
    def from_dict(cls, value):
        _exact_dict(value, cls)
        return cls(**value)


@dataclass(frozen=True)
class MarketConfig:
    schema: str
    drinks: tuple[DrinkConfig, ...]

    def __post_init__(self):
        _require(self.schema == "market-config-v1")
        _require(isinstance(self.drinks, (tuple, list)) and 10 <= len(self.drinks) <= 20)
        _require(all(isinstance(drink, DrinkConfig) for drink in self.drinks))
        _require(len({drink.id for drink in self.drinks}) == len(self.drinks))
        object.__setattr__(self, "drinks", tuple(self.drinks))

    @property
    def config_id(self):
        return _digest(asdict(self))

    @classmethod
    def from_dict(cls, value):
        _exact_dict(value, cls)
        _require(type(value["drinks"]) is list)
        return cls(value["schema"], tuple(DrinkConfig.from_dict(drink) for drink in value["drinks"]))


@dataclass(frozen=True)
class ClockSample:
    monotonic_ns: int
    utc: datetime


class Clock(Protocol):
    def sample(self) -> ClockSample: ...
    def describe(self) -> dict[str, str | int | bool]: ...


class SystemClock:
    def __init__(self):
        info = time.get_clock_info("perf_counter")
        if not info.monotonic or info.adjustable or info.resolution > 0.001:
            raise MarketError("clock")
        self._description = {
            "implementation": info.implementation, "monotonic": info.monotonic,
            "adjustable": info.adjustable, "resolution_ns": math.ceil(info.resolution * 1e9),
        }

    def sample(self):
        return ClockSample(time.perf_counter_ns(), datetime.now(timezone.utc))

    def describe(self):
        return dict(self._description)


@dataclass(frozen=True)
class FixtureScenario:
    fixture_id: str
    drink_id: str
    target_rappen: int
    expected_drink_version: int


@dataclass(frozen=True)
class Proposal:
    schema: str
    event_id: str
    request_id: str
    source_kind: str
    source_session: str
    sequence: int
    generation: int
    config_id: str
    readout_version: str
    incarnation: str
    drink_id: str
    target_rappen: int
    expected_drink_version: int
    created_ns: int
    model_interval_ms: tuple[int, int] | None
    recorded_utc: str


@dataclass(frozen=True)
class NativeProposal(Proposal):
    source_sha256: str
    header_sha256: str
    protocol_sha256: str
    readout_configuration_sha256: str


@dataclass(frozen=True)
class NativeBinding:
    worker_session: str
    source_sha256: str
    header_sha256: str
    protocol_sha256: str
    readout_configuration_sha256: str
    incarnation: str
    generation: int
    config_id: str


@dataclass(frozen=True)
class Challenge:
    id: str
    incarnation: str
    session_id: str
    revision: int
    expires_in_ms: int


@dataclass(frozen=True)
class PriceRow:
    id: str
    name: str
    minimum_rappen: int
    maximum_rappen: int
    grid_rappen: int
    initial_rappen: int
    current_rappen: int
    drink_version: int
    last_activation_id: str | None
    recorded_utc: str | None
    remaining_lock_ms: int
    estimated_eligible_utc: str | None
    recovery_lock: bool


@dataclass(frozen=True)
class Snapshot:
    schema: str
    incarnation: str
    revision: int
    price_version: int
    config_id: str
    generation: int
    paused: bool
    fault: str | None
    primary_state: str
    server_utc: str
    rows: tuple[PriceRow, ...]
    challenge: Challenge | None


@dataclass(frozen=True)
class NativeSnapshot(Snapshot):
    source_kind: str
    readout_version: str


@dataclass(frozen=True)
class ProposalResult:
    event_id: str
    request_id: str
    status: str
    reason: str
    activation_id: str | None
    terminal_revision: int
    terminal_price_version: int
    drink_version: int | None
    current_rappen: int | None


@dataclass(frozen=True)
class PauseReply:
    paused: bool
    durable: bool
    fault: str | None
    revision: int
    audit_recorded: bool


@dataclass(frozen=True)
class ControlResult:
    command_id: str
    status: str
    reason: str
    terminal_revision: int


@dataclass(frozen=True)
class ResumeReply:
    result: ControlResult
    snapshot: Snapshot
    superseding_reason: str | None


@dataclass(frozen=True)
class ClaimReply:
    session_id: str
    primary_token: str
    snapshot: Snapshot


@dataclass(frozen=True)
class AckReply:
    accepted: bool
    reason: str
    snapshot: Snapshot


@dataclass(frozen=True)
class ApiError:
    error: str


_COUNTER_SQL = "BETWEEN 0 AND 9007199254740991"
_SCHEMA = {
    "market": f"""CREATE TABLE market (
        id INTEGER PRIMARY KEY CHECK(id=1), schema_version INTEGER NOT NULL CHECK(schema_version=1),
        config_json TEXT NOT NULL CHECK(json_valid(config_json)), config_id TEXT NOT NULL CHECK(length(config_id)=64),
        incarnation TEXT NOT NULL CHECK(length(incarnation)=36),
        revision INTEGER NOT NULL CHECK(revision {_COUNTER_SQL}),
        price_version INTEGER NOT NULL CHECK(price_version {_COUNTER_SQL}),
        generation INTEGER NOT NULL CHECK(generation {_COUNTER_SQL}),
        paused INTEGER NOT NULL CHECK(paused IN (0,1)),
        capacity_latched INTEGER NOT NULL CHECK(capacity_latched IN (0,1)),
        fault TEXT CHECK(fault IN ('clock','storage','capacity','overload')),
        primary_state TEXT NOT NULL CHECK(primary_state IN ('unclaimed','awaiting_ack','present','absent')),
        CHECK(fault!='capacity' OR capacity_latched=1)
    )""",
    "drinks": f"""CREATE TABLE drinks (
        id TEXT PRIMARY KEY CHECK(length(id) BETWEEN 1 AND 64),
        position INTEGER NOT NULL UNIQUE CHECK(position BETWEEN 0 AND 19),
        name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 80),
        minimum_rappen INTEGER NOT NULL CHECK(minimum_rappen BETWEEN 1 AND 1000000),
        maximum_rappen INTEGER NOT NULL CHECK(maximum_rappen BETWEEN minimum_rappen AND 1000000),
        grid_rappen INTEGER NOT NULL CHECK(grid_rappen BETWEEN 1 AND 1000000),
        initial_rappen INTEGER NOT NULL CHECK(initial_rappen BETWEEN minimum_rappen AND maximum_rappen AND initial_rappen%grid_rappen=0),
        current_rappen INTEGER NOT NULL CHECK(current_rappen BETWEEN minimum_rappen AND maximum_rappen AND current_rappen%grid_rappen=0),
        drink_version INTEGER NOT NULL CHECK(drink_version {_COUNTER_SQL}),
        last_activation_id TEXT REFERENCES activations(activation_id) DEFERRABLE INITIALLY DEFERRED,
        recorded_utc TEXT,
        CHECK(minimum_rappen%grid_rappen=0 AND maximum_rappen%grid_rappen=0)
    )""",
    "activations": """CREATE TABLE activations (
        activation_id TEXT PRIMARY KEY CHECK(length(activation_id)=36),
        event_id TEXT NOT NULL UNIQUE REFERENCES proposal_results(event_id) DEFERRABLE INITIALLY DEFERRED,
        drink_id TEXT NOT NULL REFERENCES drinks(id),
        old_rappen INTEGER NOT NULL CHECK(old_rappen BETWEEN 1 AND 1000000),
        new_rappen INTEGER NOT NULL CHECK(new_rappen BETWEEN 1 AND 1000000 AND new_rappen!=old_rappen),
        proposal_digest TEXT NOT NULL CHECK(length(proposal_digest)=64),
        config_id TEXT NOT NULL CHECK(length(config_id)=64),
        readout_version TEXT NOT NULL CHECK(readout_version='synthetic-price-v1'),
        source_session TEXT NOT NULL CHECK(length(source_session)=36),
        incarnation TEXT NOT NULL CHECK(length(incarnation)=36),
        recorded_utc TEXT NOT NULL,
        cooldown_policy TEXT NOT NULL CHECK(cooldown_policy='postcommit-1800s-restart-full-v1')
    )""",
    "proposal_results": """CREATE TABLE proposal_results (
        event_id TEXT PRIMARY KEY CHECK(length(event_id)=36),
        request_id TEXT NOT NULL UNIQUE CHECK(length(request_id) BETWEEN 1 AND 64),
        digest TEXT NOT NULL CHECK(length(digest)=64),
        result_json TEXT NOT NULL CHECK(json_valid(result_json)),
        activation_id TEXT UNIQUE REFERENCES activations(activation_id) DEFERRABLE INITIALLY DEFERRED
    )""",
    "source_state": f"""CREATE TABLE source_state (
        id INTEGER PRIMARY KEY CHECK(id=1),
        source_session TEXT NOT NULL UNIQUE CHECK(length(source_session)=36),
        high_water INTEGER NOT NULL CHECK(high_water {_COUNTER_SQL})
    )""",
    "fixture_requests": """CREATE TABLE fixture_requests (
        request_id TEXT PRIMARY KEY CHECK(length(request_id) BETWEEN 1 AND 64),
        digest TEXT NOT NULL CHECK(length(digest)=64),
        event_id TEXT NOT NULL UNIQUE REFERENCES proposal_results(event_id)
    )""",
    "control_results": """CREATE TABLE control_results (
        command_id TEXT PRIMARY KEY CHECK(length(command_id) BETWEEN 1 AND 64),
        result_json TEXT NOT NULL CHECK(json_valid(result_json))
    )""",
}
_SCHEMA = {name: sql + " STRICT" for name, sql in _SCHEMA.items()}
NATIVE_READOUT_VERSION = "continuous-motor-drive/v1"
_NATIVE_SCHEMA = dict(_SCHEMA)
_NATIVE_SCHEMA["market"] = _SCHEMA["market"].replace("schema_version=1", "schema_version=2")
_NATIVE_SCHEMA["activations"] = _SCHEMA["activations"].replace("synthetic-price-v1", NATIVE_READOUT_VERSION)
_NATIVE_SCHEMA["native_proposals"] = """CREATE TABLE native_proposals (
    event_id TEXT PRIMARY KEY REFERENCES proposal_results(event_id),
    proposal_json TEXT NOT NULL CHECK(json_valid(proposal_json) AND length(proposal_json)<=8192)
) STRICT"""


def _validate_scenario(value):
    _require(isinstance(value, FixtureScenario) and value.fixture_id == "synthetic-price-v1")
    _require(_identifier(value.drink_id) and _integer(value.target_rappen, 1, 1_000_000))
    _require(_integer(value.expected_drink_version))


def _validate_proposal(value, *, native=False):
    _require(isinstance(value, Proposal))
    _require(value.schema == "market-proposal-v1")
    _require(value.source_kind == ("native_measurement" if native else "synthetic_fixture"))
    _require(value.readout_version == (NATIVE_READOUT_VERSION if native else "synthetic-price-v1"))
    if native:
        _require(isinstance(value, NativeProposal))
        _require(all(isinstance(item, str) and _DIGEST.fullmatch(item) is not None for item in (
            value.source_sha256, value.header_sha256, value.protocol_sha256, value.readout_configuration_sha256,
        )))
    _require(all(_uuid(item) for item in (value.event_id, value.source_session, value.incarnation)))
    _require(_identifier(value.request_id) and _identifier(value.drink_id))
    _require(isinstance(value.config_id, str) and _DIGEST.fullmatch(value.config_id) is not None)
    _require(_integer(value.sequence, 1) and _integer(value.generation))
    _require(_integer(value.expected_drink_version) and _integer(value.target_rappen, 1, 1_000_000))
    _require(_integer(value.created_ns, 0, MAX_NS) and _utc(value.recorded_utc))
    interval = value.model_interval_ms
    _require(interval is None or (
        isinstance(interval, tuple) and len(interval) == 2
        and all(_integer(item) for item in interval) and interval[0] <= interval[1]
    ))
    if native:
        _require(interval is not None and 0 < interval[1] - interval[0] < 60_000)


class PriceAuthority:
    def __init__(self, config, db_path, clock, *, mode="synthetic"):
        _require(mode in ("synthetic", "native"))
        self.mode = mode
        self._schema = _NATIVE_SCHEMA if mode == "native" else _SCHEMA
        self._schema_version = 2 if mode == "native" else 1
        self._native_binding = None
        self.config = config
        self.db_path = Path(db_path).resolve()
        self._clock = clock or SystemClock()
        self.clock_diagnostics = self._clock.describe()
        self._lock = threading.Lock()
        self._safety_lock = threading.Lock()
        self._safety_epoch = 0
        self._reconciled_epoch = 0
        self._safety_reason = None
        self._closed = False
        self._ownership = None
        self._db = None
        self._last_sample = None
        self._durable_state = None
        self._revision = self._generation = self._price_version = self._high_water = 0
        self._paused = True
        self._fault = None
        self._capacity_latched = False
        self._primary_state = "unclaimed"
        self._primary_session = self._primary_token = self._challenge = None
        self._challenge_deadline = self._lease_deadline = self._claim_deadline = 0
        self._claims = {}
        self._deadlines = {}
        self._recovery = set()
        self._source_session = str(uuid4())
        self._incarnation = str(uuid4())
        try:
            try:
                self._ownership = DatabaseOwnership(self.db_path)
            except OSError:
                raise MarketError("ownership") from None
            self._check_files()
            exists = self.db_path.exists()
            self._db = sqlite3.connect(
                self.db_path, autocommit=sqlite3.LEGACY_TRANSACTION_CONTROL,
                isolation_level=None, check_same_thread=False,
            )
            self._db.row_factory = sqlite3.Row
            if exists:
                version = self._db.execute("PRAGMA user_version").fetchone()[0]
                if version in (1, 2) and version != self._schema_version:
                    raise MarketError("wrong_mode")
            self._configure_database()
            sample = self._sample()
            if self._fault:
                raise MarketError("clock")
            with self._transaction():
                if exists:
                    self._load_database()
                else:
                    self._initialize_database()
                self._advance("_generation", "_revision")
                self._paused = True
                self._primary_state = "unclaimed"
                self._persist()
            sample = self._sample()
            if self._fault == "clock":
                raise MarketError("clock")
            for row in self._db.execute("SELECT id FROM drinks WHERE last_activation_id IS NOT NULL"):
                self._deadlines[row[0]] = sample.monotonic_ns + COOLDOWN_NS
                self._recovery.add(row[0])
            self._db.set_authorizer(self._authorize)
        except BaseException as error:
            self.close()
            if isinstance(error, (sqlite3.Error, OSError)):
                raise MarketError("storage") from error
            raise

    @staticmethod
    def _authorize(action, arg1, arg2, database, trigger):
        if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA and arg1.lower() == "journal_mode" and arg2 is not None:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    def _check_files(self):
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        journal = self.db_path.with_name(self.db_path.name + "-journal")
        journal_size = journal.stat().st_size if journal.exists() else 0
        if db_size > DB_LIMIT or journal_size > JOURNAL_LIMIT or db_size + journal_size > DB_LIMIT + JOURNAL_LIMIT:
            raise MarketError("storage")
        if any(self.db_path.with_name(self.db_path.name + suffix).exists() for suffix in ("-wal", "-shm")):
            raise MarketError("storage")

    def _configure_database(self):
        # DELETE journal: at most one 4096-byte preimage + 8-byte page metadata
        # per page, plus a bounded sector/header per record, even at 16384 pages.
        # With cache_spill OFF one transaction has no repeated spilled preimages.
        for sql in (
            "PRAGMA page_size=4096", "PRAGMA max_page_count=16384",
            "PRAGMA foreign_keys=ON", "PRAGMA synchronous=FULL",
            "PRAGMA busy_timeout=1000", "PRAGMA journal_mode=DELETE",
            "PRAGMA cache_spill=OFF", "PRAGMA journal_size_limit=75497472",
        ):
            self._db.execute(sql)
        if self._db.execute("PRAGMA page_size").fetchone()[0] != 4096:
            raise MarketError("storage")
        if self._db.execute("PRAGMA max_page_count").fetchone()[0] != 16384:
            raise MarketError("storage")
        # With cache spill disabled, the main rollback journal has one segment.
        # Reserve two maximum SQLite sectors (65536 bytes) for header/padding;
        # records themselves are packed page_size+8 bytes, not sector padded.
        if 16384 * (4096 + 8) + 2 * 65536 > JOURNAL_LIMIT:
            raise MarketError("storage")

    def _initialize_database(self):
        for sql in self._schema.values():
            self._db.execute(sql)
        self._db.execute(f"PRAGMA user_version={self._schema_version}")
        self._db.execute(
            "INSERT INTO market VALUES (1,?,?,?,?,0,0,0,1,0,NULL,'unclaimed')",
            (self._schema_version, _canonical(asdict(self.config)), self.config.config_id, self._incarnation),
        )
        self._db.execute("INSERT INTO source_state VALUES (1,?,0)", (self._source_session,))
        for position, drink in enumerate(self.config.drinks):
            self._db.execute(
                "INSERT INTO drinks VALUES (?,?,?,?,?,?,?,?,0,NULL,NULL)",
                (drink.id, position, drink.name, drink.minimum_rappen, drink.maximum_rappen,
                 drink.grid_rappen, drink.initial_rappen, drink.initial_rappen),
            )

    def _load_database(self):
        actual = {row[0]: row[1] for row in self._db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")}
        normalize = lambda value: " ".join(value.split())
        if set(actual) != set(self._schema) or any(normalize(actual[name]) != normalize(sql) for name, sql in self._schema.items()):
            raise MarketError("storage")
        if self._db.execute("PRAGMA user_version").fetchone()[0] != self._schema_version:
            raise MarketError("storage")
        if self._db.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or self._db.execute("PRAGMA foreign_key_check").fetchone():
            raise MarketError("storage")
        rows = self._db.execute("SELECT * FROM market").fetchall()
        if len(rows) != 1 or self._db.execute("SELECT count(*) FROM source_state").fetchone()[0] != 1:
            raise MarketError("storage")
        row = rows[0]
        if row["config_json"] != _canonical(asdict(self.config)) or row["config_id"] != self.config.config_id:
            raise MarketError("config_mismatch")
        stored_drinks = self._db.execute("SELECT * FROM drinks ORDER BY position").fetchall()
        if len(stored_drinks) != len(self.config.drinks):
            raise MarketError("storage")
        for stored, drink in zip(stored_drinks, self.config.drinks):
            if any(stored[key] != value for key, value in asdict(drink).items()):
                raise MarketError("storage")
        self._revision, self._price_version, self._generation = row["revision"], row["price_version"], row["generation"]
        self._capacity_latched = bool(row["capacity_latched"])
        self._fault = "capacity" if self._capacity_latched else None
        if self._ledger_count() > 10_000:
            raise MarketError("storage")

    def _advance(self, *names):
        if any(getattr(self, name) >= MAX_COUNTER for name in names):
            self._paused, self._fault = True, "capacity"
            self._capacity_latched = True
            raise MarketError("capacity")
        for name in names:
            setattr(self, name, getattr(self, name) + 1)

    def _latch_fault(self, fault):
        if fault == "capacity":
            self._capacity_latched = True
        if self._fault == fault:
            return
        self._fault, self._paused = fault, True
        self._challenge = None
        if self._primary_state in ("present", "awaiting_ack"):
            self._primary_state = "absent"
        for name in ("_generation", "_revision"):
            setattr(self, name, min(MAX_COUNTER, getattr(self, name) + 1))

    def _sample(self):
        try:
            sample = self._clock.sample()
            if not isinstance(sample, ClockSample) or not _integer(sample.monotonic_ns, 0, MAX_NS):
                raise ValueError("invalid monotonic sample")
            if not isinstance(sample.utc, datetime) or sample.utc.utcoffset() != timedelta(0):
                raise ValueError("invalid UTC label")
            if self._last_sample and sample.monotonic_ns < self._last_sample.monotonic_ns:
                raise ValueError("backward monotonic sample")
            self._last_sample = sample
            return sample
        except Exception:
            self._latch_fault("clock")
            return self._last_sample or ClockSample(0, datetime(1970, 1, 1, tzinfo=timezone.utc))

    def _state(self):
        return (self._revision, self._price_version, self._generation,
                self._paused, self._fault, self._primary_state, self._high_water,
                self._capacity_latched)

    def _persist(self):
        self._db.execute(
            "UPDATE market SET incarnation=?,revision=?,price_version=?,generation=?,paused=?,capacity_latched=?,fault=?,primary_state=? WHERE id=1",
            (self._incarnation, self._revision, self._price_version, self._generation,
             int(self._paused), int(self._capacity_latched), self._fault, self._primary_state),
        )
        self._db.execute("UPDATE source_state SET source_session=?,high_water=? WHERE id=1", (self._source_session, self._high_water))

    def _commit_transaction(self) -> None:
        self._db.execute("COMMIT")

    @contextmanager
    def _transaction(self):
        if self._closed:
            raise MarketError("storage")
        try:
            self._check_files()
            self._db.execute("BEGIN IMMEDIATE")
            yield
            self._commit_transaction()
            self._durable_state = self._state()
        except BaseException as error:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            if isinstance(error, MarketError) and error.code == "capacity":
                # Rejection rolls back the candidate, but a newly recognized
                # permanent fence must be durable before the caller can close.
                # A failing fence COMMIT raises storage from this transaction.
                self._restore_price_counters()
                with self._transaction():
                    self._persist()
                raise
            if isinstance(error, (sqlite3.Error, OSError)) or isinstance(error, MarketError) and error.code == "storage":
                self._latch_fault("storage")
                raise MarketError("storage") from error
            raise

    def _synchronize(self, sample):
        with self._safety_lock:
            epoch, reason = self._safety_epoch, self._safety_reason
        if reason is not None and epoch > self._reconciled_epoch:
            if not self._paused:
                self._advance("_generation", "_revision")
                self._paused = True
            if reason == "overload" and self._fault is None:
                self._fault = "overload"
            self._reconciled_epoch = epoch
        now = sample.monotonic_ns
        if self._primary_state == "present" and now >= self._lease_deadline:
            self._primary_state = "absent"
            self._challenge = None
            self._advance("_generation", "_revision")
        elif self._primary_state == "awaiting_ack" and now >= self._claim_deadline:
            self._primary_state = "absent"
            self._challenge = None
            self._advance("_revision")

    def _synchronize_durable(self):
        if self._closed:
            raise MarketError("storage")
        sample = self._sample()
        self._synchronize(sample)
        if self._state() != self._durable_state:
            with self._transaction():
                self._persist()
        return sample

    def _ledger_count(self):
        tables = (
            "fixture_requests", "proposal_results", "activations", "control_results",
        ) + (("native_proposals",) if self.mode == "native" else ())
        return sum(self._db.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in tables)

    def _reserve(self, count, ceiling):
        if self._ledger_count() + count > ceiling:
            self._latch_fault("capacity")
            raise MarketError("capacity")

    def _make_snapshot(self, sample, primary_session=None, *, issue_challenge=False):
        if primary_session is not None and primary_session != self._primary_session:
            raise MarketError("unauthorized")
        challenge = None
        if primary_session is not None and issue_challenge and self._fault != "clock":
            self._challenge = Challenge(str(uuid4()), self._incarnation, primary_session, self._revision, 5000)
            self._challenge_deadline = sample.monotonic_ns + LEASE_NS
            challenge = self._challenge
        rows = []
        for row in self._db.execute("SELECT * FROM drinks ORDER BY position"):
            remaining = max(0, self._deadlines.get(row["id"], 0) - sample.monotonic_ns)
            milliseconds = (remaining + 999_999) // 1_000_000
            try:
                estimate = _label(sample.utc + timedelta(milliseconds=milliseconds)) if remaining else None
            except OverflowError:
                estimate = None
            rows.append(PriceRow(
                row["id"], row["name"], row["minimum_rappen"], row["maximum_rappen"],
                row["grid_rappen"], row["initial_rappen"], row["current_rappen"], row["drink_version"],
                row["last_activation_id"], row["recorded_utc"], milliseconds, estimate,
                row["id"] in self._recovery,
            ))
        values = ("market-snapshot-v2" if self.mode == "native" else "market-snapshot-v1",
                  self._incarnation, self._revision, self._price_version,
                  self.config.config_id, self._generation, self._paused, self._fault,
                  self._primary_state, _label(sample.utc), tuple(rows), challenge)
        if self.mode == "native":
            return NativeSnapshot(*values, "native_measurement", NATIVE_READOUT_VERSION)
        return Snapshot(*values)

    def snapshot(self, primary_session: str | None = None) -> Snapshot:
        with self._lock:
            sample = self._synchronize_durable()
            return self._make_snapshot(sample, primary_session, issue_challenge=primary_session is not None)

    def request_safety_pause(self, reason: str) -> int:
        _require(reason in ("operator_pause", "overload"))
        with self._safety_lock:
            self._safety_epoch += 1
            self._safety_reason = reason
            return self._safety_epoch

    def capture_safety_epoch(self) -> int:
        with self._safety_lock:
            return self._safety_epoch

    def _superseding_reason(self):
        with self._safety_lock:
            return self._safety_reason

    def pause(self, *, safety_epoch: int | None = None) -> PauseReply:
        if safety_epoch is None:
            safety_epoch = self.request_safety_pause("operator_pause")
        else:
            _require(_integer(safety_epoch) and safety_epoch <= self.capture_safety_epoch())
        with self._lock:
            audit = False
            try:
                with self._transaction():
                    before = self._state()
                    self._synchronize(self._sample())
                    if not self._paused:
                        self._paused = True
                        self._advance("_generation", "_revision")
                    if self._state() != before and self._ledger_count() < 10_000:
                        result = ControlResult(uuid4().hex, "accepted", "operator_pause", self._revision)
                        self._db.execute("INSERT INTO control_results VALUES (?,?)", (result.command_id, _canonical(asdict(result))))
                        audit = True
                    self._persist()
                return PauseReply(True, True, self._fault, self._revision, audit)
            except MarketError as error:
                if error.code == "capacity":
                    # Exhausted counters cannot prevent the fixed safety flag
                    # from being persisted. Capacity remains permanently latched.
                    try:
                        with self._transaction():
                            self._persist()
                        return PauseReply(True, True, "capacity", self._revision, False)
                    except MarketError as persistence_error:
                        if persistence_error.code != "storage":
                            raise
                        return PauseReply(True, False, "storage", self._revision, False)
                if error.code != "storage":
                    raise
                return PauseReply(True, False, "storage", self._revision, False)

    def resume(self, request_id: str, *, ingress_epoch: int) -> ResumeReply:
        _require(_identifier(request_id) and _integer(ingress_epoch))
        with self._lock:
            result = None
            new_result = False
            with self._transaction():
                sample = self._sample()
                self._synchronize(sample)
                previous = self._db.execute("SELECT result_json FROM control_results WHERE command_id=?", (request_id,)).fetchone()
                if previous:
                    result = ControlResult(**json.loads(previous[0]))
                else:
                    self._reserve(1, 10_000)
                    reason = "capacity" if self._capacity_latched else self._fault if self._fault in ("clock", "storage") else None
                    if reason is None and ingress_epoch != self.capture_safety_epoch():
                        reason = "superseded"
                    if reason is None and self._primary_state != "present":
                        reason = "board_absent"
                    if reason is None:
                        if self._paused or self._fault == "overload":
                            self._paused, self._fault = False, None
                            self._advance("_generation", "_revision")
                    final_sample = self._sample()
                    self._synchronize(final_sample)
                    if reason is None:
                        if self._capacity_latched:
                            reason = "capacity"
                        elif self._fault in ("clock", "storage"):
                            reason = self._fault
                        elif ingress_epoch != self.capture_safety_epoch():
                            reason = "superseded"
                        elif self._primary_state != "present":
                            reason = "board_absent"
                        if reason is not None and not self._paused:
                            self._paused = True
                            self._advance("_generation", "_revision")
                    result = ControlResult(request_id, "accepted" if reason is None else "rejected", reason or "resumed", self._revision)
                    self._db.execute("INSERT INTO control_results VALUES (?,?)", (request_id, _canonical(asdict(result))))
                    new_result = True
                self._persist()
            if new_result and result.status == "accepted":
                with self._safety_lock:
                    if self._safety_epoch == ingress_epoch:
                        self._safety_reason = None
            sample = self._synchronize_durable()
            return ResumeReply(result, self._make_snapshot(sample), self._superseding_reason())

    def claim_primary(self, incarnation: str, request_id: str) -> ClaimReply:
        _require(_uuid(incarnation) and _identifier(request_id))
        with self._lock:
            sample = self._synchronize_durable()
            if incarnation != self._incarnation:
                raise MarketError("wrong_incarnation")
            if request_id in self._claims:
                session, token = self._claims[request_id]
                if session != self._primary_session:
                    raise MarketError("superseded")
            else:
                if len(self._claims) >= 64:
                    raise MarketError("claim_capacity")
                if self._primary_state not in ("unclaimed", "absent"):
                    raise MarketError("primary_busy")
                session, token = str(uuid4()), secrets.token_urlsafe(32)
                self._primary_session, self._primary_token = session, token
                self._claims[request_id] = (session, token)
                self._primary_state = "awaiting_ack"
                self._claim_deadline = sample.monotonic_ns + LEASE_NS
                self._challenge = None
                self._advance("_revision")
                with self._transaction():
                    self._persist()
            return ClaimReply(session, token, self._make_snapshot(sample, session, issue_challenge=True))

    def resolve_primary_token(self, token: str) -> str | None:
        with self._lock:
            self._synchronize_durable()
            if isinstance(token, str) and self._primary_token is not None and hmac.compare_digest(token.encode("utf-8"), self._primary_token.encode("ascii")):
                return self._primary_session
            return None

    def ack_primary(self, session_id: str, challenge: str) -> AckReply:
        _require(_uuid(session_id) and _uuid(challenge))
        with self._lock:
            original_challenge = self._challenge
            original_deadline = self._challenge_deadline
            sample = self._synchronize_durable()
            reason = None
            if session_id != self._primary_session:
                reason = "unknown_session"
            elif original_challenge is not None and original_challenge.id == challenge and sample.monotonic_ns >= original_deadline:
                reason = "expired_challenge"
            elif self._challenge is None or self._challenge.id != challenge:
                reason = "invalid_challenge"
            elif self._challenge.revision != self._revision:
                reason = "stale_revision"
            if reason is None:
                if self._primary_state != "present":
                    self._primary_state = "present"
                    self._advance("_revision")
                    with self._transaction():
                        self._persist()
                self._lease_deadline = sample.monotonic_ns + LEASE_NS
                self._challenge = None
            return AckReply(reason is None, reason or "acknowledged", self._make_snapshot(sample))

    def _proposal_reason(self, proposal, sample, *, final=False):
        if self._fault:
            return self._fault
        if not final:
            if proposal.config_id != self.config.config_id:
                return "wrong_config"
            if proposal.source_session != self._source_session:
                return "wrong_source"
            if proposal.incarnation != self._incarnation:
                return "wrong_incarnation"
        if proposal.generation != self._generation:
            return "wrong_generation"
        if not final:
            if proposal.sequence <= self._high_water:
                return "reordered"
            self._high_water = proposal.sequence
        age = sample.monotonic_ns - proposal.created_ns
        if age < 0:
            return "future_proposal"
        if age >= LEASE_NS:
            return "expired"
        row = self._db.execute("SELECT * FROM drinks WHERE id=?", (proposal.drink_id,)).fetchone()
        if not final:
            if row is None:
                return "unknown_drink"
            if row["drink_version"] != proposal.expected_drink_version:
                return "stale_drink_version"
        if self._paused:
            return "paused"
        if self._primary_state != "present":
            return "board_absent"
        if not final:
            if not row["minimum_rappen"] <= proposal.target_rappen <= row["maximum_rappen"]:
                return "out_of_range"
            if proposal.target_rappen % row["grid_rappen"]:
                return "off_grid"
            if proposal.target_rappen == row["current_rappen"]:
                return "no_change"
        if sample.monotonic_ns < self._deadlines.get(proposal.drink_id, 0):
            return "cooldown"
        return None

    def _anchor_committed_activation(self, drink_id: str) -> None:
        sample = self._sample()
        self._deadlines[drink_id] = sample.monotonic_ns + COOLDOWN_NS
        self._recovery.discard(drink_id)

    def _submit_locked(self, proposal, sample, fixture_digest=None):
        digest = _digest(asdict(proposal))
        previous = self._db.execute("SELECT digest,result_json FROM proposal_results WHERE event_id=? OR request_id=?", (proposal.event_id, proposal.request_id)).fetchone()
        if previous:
            if previous["digest"] != digest:
                raise MarketError("idempotency_conflict")
            return ProposalResult(**json.loads(previous["result_json"]))
        self._reserve(3 if fixture_digest is not None else 2, 9000)
        reason = self._proposal_reason(proposal, sample)
        activation_id = None
        if reason is None:
            row = self._db.execute("SELECT * FROM drinks WHERE id=?", (proposal.drink_id,)).fetchone()
            if row["drink_version"] >= MAX_COUNTER or self._db.execute("SELECT price_version FROM market").fetchone()[0] >= MAX_COUNTER:
                self._latch_fault("capacity")
                raise MarketError("capacity")
            before_revision, before_price_version = self._revision, self._price_version
            self._db.execute("SAVEPOINT candidate")
            self._advance("_revision", "_price_version")
            activation_id = str(uuid4())
            self._db.execute(
                "INSERT INTO activations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (activation_id, proposal.event_id, proposal.drink_id, row["current_rappen"], proposal.target_rappen,
                 digest, proposal.config_id, proposal.readout_version, proposal.source_session,
                 proposal.incarnation, proposal.recorded_utc, "postcommit-1800s-restart-full-v1"),
            )
            self._db.execute(
                "UPDATE drinks SET current_rappen=?,drink_version=drink_version+1,last_activation_id=?,recorded_utc=? WHERE id=?",
                (proposal.target_rappen, activation_id, proposal.recorded_utc, proposal.drink_id),
            )
            tentative_revision = self._revision
            final_sample = self._sample()
            self._synchronize(final_sample)
            final_reason = self._proposal_reason(proposal, final_sample, final=True)
            if final_reason:
                # Keep detected safety/presence state in memory and reapply its revision
                # after rolling back the tentative price, never roll back a fence.
                transition_revisions = self._revision - tentative_revision
                self._db.execute("ROLLBACK TO candidate")
                self._revision = before_revision + transition_revisions
                self._price_version = before_price_version
                activation_id, reason = None, final_reason
            self._db.execute("RELEASE candidate")
        elif reason == "no_change":
            final_sample = self._sample()
            self._synchronize(final_sample)
            final_reason = self._proposal_reason(proposal, final_sample, final=True)
            if final_reason and final_reason != "cooldown":
                reason = final_reason
        else:
            self._synchronize(self._sample())
        row = self._db.execute("SELECT drink_version,current_rappen FROM drinks WHERE id=?", (proposal.drink_id,)).fetchone()
        status = "activated" if activation_id else "no_change" if reason == "no_change" else "rejected"
        result = ProposalResult(proposal.event_id, proposal.request_id, status, reason or "activated", activation_id,
                                self._revision, self._price_version, row[0] if row else None, row[1] if row else None)
        self._db.execute("INSERT INTO proposal_results VALUES (?,?,?,?,?)",
                         (proposal.event_id, proposal.request_id, digest, _canonical(asdict(result)), activation_id))
        if fixture_digest is not None:
            self._db.execute("INSERT INTO fixture_requests VALUES (?,?,?)", (proposal.request_id, fixture_digest, proposal.event_id))
        self._persist()
        return result

    def _after_proposal_commit(self, result, drink_id):
        if result.status == "activated":
            self._anchor_committed_activation(drink_id)
        self._synchronize_durable()

    def run_fixture(self, request_id: str, scenario: FixtureScenario) -> ProposalResult:
        if self.mode != "synthetic":
            raise MarketError("wrong_mode")
        _require(_identifier(request_id))
        _validate_scenario(scenario)
        digest = _digest(asdict(scenario))
        with self._lock:
            try:
                with self._transaction():
                    sample = self._sample()
                    self._synchronize(sample)
                    previous = self._db.execute("SELECT digest,event_id FROM fixture_requests WHERE request_id=?", (request_id,)).fetchone()
                    if previous:
                        if previous["digest"] != digest:
                            raise MarketError("idempotency_conflict")
                        result = self._get_event(previous["event_id"])
                        self._persist()
                        return result
                    if self._high_water >= MAX_COUNTER:
                        self._latch_fault("capacity")
                        raise MarketError("capacity")
                    event = Proposal("market-proposal-v1", str(uuid4()), request_id, "synthetic_fixture",
                                     self._source_session, self._high_water + 1, self._generation,
                                     self.config.config_id, "synthetic-price-v1", self._incarnation,
                                     scenario.drink_id, scenario.target_rappen, scenario.expected_drink_version,
                                     sample.monotonic_ns, None, _label(sample.utc))
                    result = self._submit_locked(event, sample, digest)
            except BaseException:
                self._restore_price_counters()
                raise
            self._after_proposal_commit(result, scenario.drink_id)
            return result

    def _restore_price_counters(self):
        # Read back the durable truth after rollback (or an uncertain COMMIT).
        # Safety/presence fences stay latched in memory.
        if self._closed:
            return
        self._price_version = self._db.execute("SELECT price_version FROM market").fetchone()[0]
        self._high_water = self._db.execute("SELECT high_water FROM source_state").fetchone()[0]

    def submit_synthetic(self, proposal: Proposal) -> ProposalResult:
        _validate_proposal(proposal)
        if self.mode != "synthetic":
            raise MarketError("wrong_mode")
        return self._submit(proposal)

    def bind_native_source(self, *, worker_session: str, source_sha256: str,
                           header_sha256: str, protocol_sha256: str,
                           readout_configuration_sha256: str) -> NativeBinding:
        if self.mode != "native":
            raise MarketError("wrong_mode")
        _require(_uuid(worker_session))
        _require(all(isinstance(item, str) and _DIGEST.fullmatch(item) is not None for item in (
            source_sha256, header_sha256, protocol_sha256, readout_configuration_sha256,
        )))
        with self._lock:
            self._synchronize_durable()
            binding = NativeBinding(worker_session, source_sha256, header_sha256, protocol_sha256,
                                    readout_configuration_sha256, self._incarnation,
                                    self._generation, self.config.config_id)
            if self._native_binding is not None:
                if self._native_binding != binding:
                    raise MarketError("source_bound")
                return self._native_binding
            with self._transaction():
                self._source_session = worker_session
                self._persist()
            self._native_binding = binding
            return binding

    def submit_native(self, proposal: NativeProposal) -> ProposalResult:
        _validate_proposal(proposal, native=True)
        if self.mode != "native":
            raise MarketError("wrong_mode")
        return self._submit(proposal, native=True)

    def _submit(self, proposal, *, native=False):
        with self._lock:
            if native:
                binding = self._native_binding
                if binding is None:
                    raise MarketError("unbound_source")
                if proposal.source_session != binding.worker_session or any(
                    getattr(proposal, name) != getattr(binding, name) for name in (
                        "source_sha256", "header_sha256", "protocol_sha256", "readout_configuration_sha256",
                    )
                ):
                    raise MarketError("wrong_source")
            duplicate = False
            try:
                with self._transaction():
                    sample = self._sample()
                    self._synchronize(sample)
                    duplicate = self._db.execute("SELECT 1 FROM proposal_results WHERE event_id=?", (proposal.event_id,)).fetchone() is not None
                    if native and not duplicate:
                        self._reserve(3, 9000)
                    result = self._submit_locked(proposal, sample)
                    if native and not duplicate:
                        self._db.execute("INSERT INTO native_proposals VALUES (?,?)",
                                         (proposal.event_id, _canonical(asdict(proposal))))
                    self._persist()
            except BaseException:
                self._restore_price_counters()
                raise
            if not duplicate:
                self._after_proposal_commit(result, proposal.drink_id)
            return result

    def _get_event(self, event_id):
        row = self._db.execute("SELECT result_json FROM proposal_results WHERE event_id=?", (event_id,)).fetchone()
        if row is None:
            raise MarketError("not_found")
        return ProposalResult(**json.loads(row[0]))

    def get_event(self, event_id: str) -> ProposalResult:
        _require(_uuid(event_id))
        with self._lock:
            self._synchronize_durable()
            return self._get_event(event_id)

    def maintain(self) -> None:
        with self._lock:
            self._synchronize_durable()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                if self._db is not None:
                    self._db.close()
            finally:
                if self._ownership is not None:
                    self._ownership.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def open_authority(config: MarketConfig, db_path: Path, clock: Clock | None = None, *, mode="synthetic") -> PriceAuthority:
    _require(isinstance(config, MarketConfig))
    return PriceAuthority(config, db_path, clock, mode=mode)
