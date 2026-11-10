"""Injected measurements exercise engineering admission, not neural evidence."""

from dataclasses import asdict, replace
import sqlite3
from uuid import uuid4

import pytest

from market.price_service import MarketError, NativeProposal, open_authority
from market.native_price import NativePriceAdapter, NativePricePump
from market.native_protocol import BLACK_SHA256
from conftest import make_present, scenario


@pytest.fixture
def native(tmp_path, config, clock):
    with open_authority(config, tmp_path / "native.sqlite3", clock, mode="native") as value:
        yield value


def adapter_for(authority):
    return NativePriceAdapter(authority, worker_session=str(uuid4()), source_sha256="a" * 64,
                              header_sha256="b" * 64, protocol_sha256="c" * 64)


def measured(adapter, clock, index, *, left=10, right=0, **changes):
    value = dict(worker_session=adapter.binding.worker_session,
                 source_sha256=adapter.binding.source_sha256,
                 header_sha256=adapter.binding.header_sha256,
                 protocol_sha256=adapter.binding.protocol_sha256,
                 observation_index=index, start_tick=index * 5000, end_tick=(index + 1) * 5000,
                 wall_start_ns=clock.ns, wall_completion_ns=clock.ns + 1_000_000,
                 frame_sha256="d" * 64, input_kind="image", dispatch_id=str(uuid4()),
                 group_bin_counts=[[0, 0, 0, 0, 0, left, right]] + [[0] * 7 for _ in range(49)])
    value.update(changes)
    clock.advance(1)
    return value


def emit(adapter, native, clock, start=0, *, right_price=True):
    outcome = None
    for index in range(start, start + 20):
        make_present(native)
        adapter.synchronize(now_ns=clock.ns)
        outcome = adapter.consume(measured(adapter, clock, index,
                                          left=0 if index >= start + 16 and right_price else 10,
                                          right=10 if index >= start + 16 and right_price else 0), now_ns=clock.ns)
    return outcome


def test_native_database_activation_exact_counts_and_provenance(native, clock):
    make_present(native)
    adapter = adapter_for(native)
    value = emit(adapter, native, clock)
    assert value["decoder"]["proposal"]["price_measurement"]["right_count"] == 40
    assert value["result"]["status"] == "activated"
    snapshot = asdict(native.snapshot())
    assert snapshot["schema"] == "market-snapshot-v2"
    assert snapshot["source_kind"] == "native_measurement"
    assert snapshot["readout_version"] == "continuous-motor-drive/v1"
    assert snapshot["rows"][0]["current_rappen"] == 700
    with sqlite3.connect(native.db_path) as db:
        assert db.execute("SELECT readout_version FROM activations").fetchone()[0] == "continuous-motor-drive/v1"
        audit = db.execute("SELECT proposal_json FROM native_proposals").fetchone()[0]
        assert adapter.binding.header_sha256 in audit


def test_native_full_jump_cooldown_and_fresh_noop(native, clock):
    make_present(native)
    adapter = adapter_for(native)
    assert emit(adapter, native, clock)["result"]["status"] == "activated"
    anchor = clock.ns
    assert emit(adapter, native, clock, 20)["result"]["status"] == "no_change"
    clock.advance(nanoseconds=anchor + 1_799_999_000_000 - clock.ns - 20_000_000)
    assert emit(adapter, native, clock, 40, right_price=False)["result"]["reason"] == "cooldown"
    clock.advance(1)
    assert emit(adapter, native, clock, 60, right_price=False)["result"]["status"] == "activated"
    assert native.snapshot().rows[0].current_rappen == 400


def test_modes_refuse_each_other_without_mutating_database(config, clock, tmp_path):
    for mode, wrong in (("synthetic", "native"), ("native", "synthetic")):
        path = tmp_path / (mode + ".sqlite3")
        with open_authority(config, path, clock, mode=mode):
            pass
        before = path.read_bytes()
        with pytest.raises(MarketError, match="wrong_mode"):
            open_authority(config, path, clock, mode=wrong)
        assert path.read_bytes() == before


def test_native_no_synthetic_ingress_or_rebinding(native, clock):
    with pytest.raises(MarketError, match="wrong_mode"):
        native.run_fixture("fixture", scenario())
    make_present(native)
    adapter = adapter_for(native)
    with pytest.raises(MarketError, match="source_bound"):
        adapter_for(native)
    value = emit(adapter, native, clock)
    event = NativeProposal(**value["proposal"])
    with pytest.raises(MarketError, match="invalid_request"):
        native.submit_synthetic(event)
    with pytest.raises(MarketError, match="wrong_source"):
        native.submit_native(replace(event, event_id=str(uuid4()), request_id=uuid4().hex,
                                     source_sha256="e" * 64))
    assert native.submit_native(event).status == "activated"


@pytest.mark.parametrize("changes", [
    {"worker_session": str(uuid4())}, {"header_sha256": "e" * 64},
    {"protocol_sha256": "e" * 64}, {"source_sha256": "e" * 64},
    {"group_bin_counts": [[0] * 7]}, {"end_tick": 1},
])
def test_invalid_measurement_terminally_pauses(native, clock, changes):
    make_present(native)
    adapter = adapter_for(native)
    with pytest.raises((MarketError, ValueError)):
        adapter.consume(measured(adapter, clock, 0, **changes), now_ns=clock.ns)
    assert native.snapshot().paused
    assert native.snapshot().price_version == 0


@pytest.mark.parametrize("bad", ["replay", "gap", "stale"])
def test_replay_gap_stale_never_price(native, clock, bad):
    make_present(native)
    adapter = adapter_for(native)
    first = measured(adapter, clock, 0)
    adapter.consume(first, now_ns=clock.ns)
    value = first if bad == "replay" else measured(adapter, clock, 2 if bad == "gap" else 1)
    if bad == "stale":
        clock.advance(5001)
        make_present(native)
    with pytest.raises((MarketError, ValueError)):
        adapter.consume(value, now_ns=clock.ns)
    assert native.snapshot().paused


def test_pause_resume_clears_partial_measurement(native, clock):
    make_present(native)
    adapter = adapter_for(native)
    for index in range(12):
        adapter.consume(measured(adapter, clock, index), now_ns=clock.ns)
    native.pause()
    adapter.synchronize(now_ns=clock.ns)
    make_present(native)
    adapter.synchronize(now_ns=clock.ns)
    for index in range(12, 16):
        outcome = adapter.consume(measured(adapter, clock, index, left=0, right=10), now_ns=clock.ns)
        assert outcome["result"] is None
    assert native.snapshot().price_version == 0


def test_native_restart_requires_fresh_binding_and_preserves_locks(native, config, clock):
    make_present(native)
    adapter = adapter_for(native)
    event = NativeProposal(**emit(adapter, native, clock)["proposal"])
    path = native.db_path
    native.close()
    with open_authority(config, path, clock, mode="native") as reopened:
        assert reopened.snapshot().rows[0].recovery_lock
        with pytest.raises(MarketError, match="unbound_source"):
            reopened.submit_native(event)
        adapter_for(reopened)
        assert reopened.snapshot().rows[0].current_rappen == 700


class ReadoutSession:
    """Test-only validated-session export fixture; never launches native code."""

    def __init__(self):
        self.enabled = False
        self.state = "prepared"
        self.records = []
        self.identity = None

    def enable_readout(self):
        self.enabled = True

    def readout_identity(self):
        return self.identity

    def poll_readouts(self):
        records, self.records = self.records[:8], self.records[8:]
        return records

    def snapshot(self):
        return {"state": self.state, "fault": None}


def test_pump_binds_public_export_consumes_once_and_pauses_terminal(native, clock):
    make_present(native)
    session = ReadoutSession()
    pump = NativePricePump(native, session, clock)
    assert session.enabled
    pump.maintain()
    assert not pump.snapshot()["bound"]
    session.state = "running"
    session.identity = dict(worker_session=str(uuid4()), source_sha256="a" * 64,
                            header_sha256="b" * 64, protocol_sha256="c" * 64,
                            engine_identity_sha256="e" * 64)
    pump.maintain()
    for index in range(20):
        make_present(native)
        session.records.append(measured(pump.adapter, clock, index,
                                        left=0 if index >= 16 else 10, right=10 if index >= 16 else 0))
        pump.maintain()
    assert native.snapshot().price_version == 1
    assert pump.snapshot()["observations_consumed"] == 20
    assert pump.snapshot()["last_result"]["status"] == "activated"
    pump.maintain()
    assert pump.snapshot()["observations_consumed"] == 20
    session.state = "ended"
    pump.maintain()
    assert native.snapshot().paused
    assert pump.snapshot()["terminal"]


def test_native_admission_exact_real_boundary(native, clock):
    make_present(native)
    adapter = adapter_for(native)
    first = NativeProposal(**emit(adapter, native, clock)["proposal"])
    clock.advance(1_799_999)
    make_present(native)
    current = native.snapshot()
    early = replace(first, event_id=str(uuid4()), request_id=uuid4().hex, sequence=21,
                    generation=current.generation, created_ns=clock.ns, target_rappen=400,
                    expected_drink_version=1)
    assert native.submit_native(early).reason == "cooldown"
    clock.advance(1)
    exact = replace(early, event_id=str(uuid4()), request_id=uuid4().hex, sequence=22, created_ns=clock.ns)
    assert native.submit_native(exact).status == "activated"


def test_black_bins_are_consumed_without_input_reset(native, clock):
    make_present(native)
    adapter = adapter_for(native)
    for index in range(20):
        bins = [[0] * 7 for _ in range(50)]
        bins[0][5 if index < 16 else 6] = 2
        bins[49][5 if index < 16 else 6] = 8
        value = measured(adapter, clock, index, group_bin_counts=bins,
                         input_kind="black", dispatch_id=None, frame_sha256=BLACK_SHA256)
        outcome = adapter.consume(value, now_ns=clock.ns)
    assert outcome["result"]["status"] == "activated"
    proposal = outcome["decoder"]["proposal"]
    assert proposal["price_measurement"]["right_count"] == 40
    assert all(sample["input_version"] == "native-black-v1" for sample in proposal["input_history"])
    assert proposal["input_history"][0]["wall_start_ms"] == 10_000
    assert proposal["input_history"][-1]["wall_completion_ms"] == clock.ns // 1_000_000


def test_unsupported_block_does_not_invent_target(native, clock):
    make_present(native)
    adapter = adapter_for(native)
    for index in range(4):
        outcome = adapter.consume(measured(adapter, clock, index, left=0), now_ns=clock.ns)
    assert outcome["decoder"]["reason"] == "unsupported_direction"
    assert outcome["proposal"] is None
    assert native.snapshot().price_version == 0


def test_wrong_native_version_and_interval_reject_without_persistence(native, clock):
    make_present(native)
    adapter = adapter_for(native)
    event = NativeProposal(**emit(adapter, native, clock)["proposal"])
    for changes in ({"readout_version": "synthetic-price-v1"}, {"model_interval_ms": None}):
        with pytest.raises(MarketError, match="invalid_request"):
            native.submit_native(replace(event, **changes))
    assert native.snapshot().price_version == 1


def test_pump_identity_change_without_observations_pauses(native, clock):
    make_present(native)
    session = ReadoutSession()
    session.state = "running"
    session.identity = dict(worker_session=str(uuid4()), source_sha256="a" * 64,
                            header_sha256="b" * 64, protocol_sha256="c" * 64,
                            engine_identity_sha256="e" * 64)
    pump = NativePricePump(native, session, clock)
    pump.maintain()
    session.identity["header_sha256"] = "f" * 64
    with pytest.raises(MarketError, match="wrong_source"):
        pump.maintain()
    assert native.snapshot().paused
    assert pump.snapshot()["terminal"]


def running_pump(native, clock):
    make_present(native)
    session = ReadoutSession()
    session.state = "running"
    session.identity = dict(worker_session=str(uuid4()), source_sha256="a" * 64,
                            header_sha256="b" * 64, protocol_sha256="c" * 64,
                            engine_identity_sha256="e" * 64)
    pump = NativePricePump(native, session, clock)
    pump.maintain()
    return pump, session


def test_pump_samples_clock_after_completion_during_queue_poll(native, clock):
    pump, session = running_pump(native, clock)

    def completing_poll():
        session.poll_readouts = lambda: ()
        return (measured(pump.adapter, clock, 0),)

    session.poll_readouts = completing_poll
    assert pump.maintain()["observations_consumed"] == 1
    assert not pump.snapshot()["terminal"]
    assert not native.snapshot().paused
    assert pump.maintain()["observations_consumed"] == 1


@pytest.mark.parametrize("state", ["ended", "faulted", "closed", "stopping"])
def test_terminal_queue_drain_accounts_once_without_price_decision(native, clock, state):
    pump, session = running_pump(native, clock)
    for index in range(19):
        session.records.append(measured(pump.adapter, clock, index,
                                        left=10 if index < 16 else 0,
                                        right=0 if index < 16 else 10))
        pump.maintain()
    session.records.append(measured(pump.adapter, clock, 19, left=0, right=10))
    session.state = state
    original_poll = session.poll_readouts

    def fenced_poll():
        assert native.snapshot().paused
        return original_poll()

    session.poll_readouts = fenced_poll
    result = pump.maintain()
    assert result["terminal"]
    assert result["observations_consumed"] == 20
    assert result["last_decoder"] == {"status": "paused", "reason": "native_ended"}
    assert result["last_result"] is None
    assert not session.records
    assert native.snapshot().price_version == 0
    assert pump.maintain() == result


@pytest.mark.parametrize("changes", [
    {"observation_index": 1, "start_tick": 5000, "end_tick": 10000},
    {"source_sha256": "f" * 64},
    {"wall_completion_ns": 20_000_000_000},
])
def test_terminal_queue_drain_still_validates_identity_order_and_clock(native, clock, changes):
    pump, session = running_pump(native, clock)
    session.records.append(measured(pump.adapter, clock, 0, **changes))
    session.state = "ended"
    with pytest.raises((MarketError, ValueError)):
        pump.maintain()
    assert pump.snapshot()["observations_consumed"] == 0
    assert pump.snapshot()["terminal"]
    assert native.snapshot().paused
    assert native.snapshot().price_version == 0


@pytest.mark.parametrize("kind", ["future", "stale", "backward"])
def test_fresh_pump_clock_does_not_launder_invalid_measurements(native, clock, kind):
    pump, session = running_pump(native, clock)
    value = measured(pump.adapter, clock, 0)
    if kind == "future":
        value["wall_completion_ns"] = clock.ns + 1_000_000
    elif kind == "stale":
        clock.advance(5001)
    else:
        clock.advance(nanoseconds=-2_000_000)
    session.records.append(value)
    with pytest.raises((MarketError, ValueError)):
        pump.maintain()
    assert pump.snapshot()["observations_consumed"] == 0
    assert native.snapshot().paused


@pytest.mark.parametrize("state", ["ended", "faulted"])
def test_terminal_during_poll_accounts_final_measurement_without_activation(native, clock, state):
    pump, session = running_pump(native, clock)
    for index in range(19):
        session.records.append(measured(pump.adapter, clock, index,
                                        left=10 if index < 16 else 0,
                                        right=0 if index < 16 else 10))
        pump.maintain()

    def terminal_poll():
        record = measured(pump.adapter, clock, 19, left=0, right=10)
        session.state = state
        session.poll_readouts = lambda: ()
        return (record,)

    session.poll_readouts = terminal_poll
    result = pump.maintain()
    assert result["terminal"]
    assert result["observations_consumed"] == 20
    assert result["last_result"] is None
    assert native.snapshot().price_version == 0
    assert native.snapshot().paused
    assert pump.maintain() == result


@pytest.mark.parametrize("state", ["ended", "faulted"])
def test_terminal_between_batch_records_fences_remaining_price_boundary(native, clock, state):
    pump, session = running_pump(native, clock)
    for index in range(18):
        session.records.append(measured(pump.adapter, clock, index,
                                        left=10 if index < 16 else 0,
                                        right=0 if index < 16 else 10))
        pump.maintain()
    session.records = [measured(pump.adapter, clock, index, left=0, right=10) for index in (18, 19)]
    original_consume = pump.adapter.consume

    def complete_then_terminal(record, *, now_ns):
        result = original_consume(record, now_ns=now_ns)
        session.state = state
        return result

    pump.adapter.consume = complete_then_terminal
    result = pump.maintain()
    assert result["terminal"]
    assert result["observations_consumed"] == 20
    assert result["last_result"] is None
    assert native.snapshot().price_version == 0
    assert native.snapshot().paused
