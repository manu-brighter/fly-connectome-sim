"""Configured motor readout for validated, once-delivered native observations.

The caller owns protocol/bin/cell validation and supplies the session's public
readout export. This adapter never launches a model or accepts HTTP proposals.
"""

from dataclasses import asdict
import importlib
from pathlib import Path
import re
import sys
from uuid import UUID, uuid4

from .native_protocol import BLACK_SHA256, GROUPS
from .price_service import MAX_COUNTER, MAX_NS, MarketError, NativeProposal, SystemClock


def _decoder_type():
    scripts = Path(__file__).absolute().parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        return importlib.import_module("market_continuous_drive").ContinuousMotorDrive
    finally:
        del sys.path[0]


ContinuousMotorDrive = _decoder_type()
_FIELDS = frozenset("worker_session source_sha256 header_sha256 protocol_sha256 observation_index start_tick end_tick wall_start_ns wall_completion_ns frame_sha256 input_kind dispatch_id group_bin_counts".split())


def _integer(value, high=MAX_COUNTER):
    return type(value) is int and 0 <= value <= high


def _digest(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


class NativePriceAdapter:
    """One source, one frozen decoder, no retry or eligibility retargeting.

    consume() returns decoder visibility plus an optional final proposal/result.
    synchronize() uses public authority generation changes to clear partial
    evidence. terminal() permanently closes admission and pauses the authority.
    """

    def __init__(self, authority, *, worker_session, source_sha256, header_sha256,
                 protocol_sha256, max_sample_age_ms=5000, max_observations=86_400):
        if not _integer(max_observations) or not 1 <= max_observations <= 86_400:
            raise ValueError("invalid observation bound")
        self.authority = authority
        self.decoder = ContinuousMotorDrive([
            {name: getattr(drink, name) for name in (
                "id", "minimum_rappen", "maximum_rappen", "grid_rappen",
            )} for drink in authority.config.drinks
        ], max_sample_age_ms=max_sample_age_ms)
        self.binding = authority.bind_native_source(
            worker_session=worker_session, source_sha256=source_sha256,
            header_sha256=header_sha256, protocol_sha256=protocol_sha256,
            readout_configuration_sha256=self.decoder.configuration_sha256,
        )
        self._max_observations = max_observations
        self._last_index = -1
        self._last_completion_ns = 0
        self._last_now_ns = 0
        self._terminal = False
        self._snapshot = authority.snapshot()
        self._boundary_ns = 0
        if self._snapshot.paused:
            self.decoder.pause(now_ms=0)

    def _clock(self, now_ns):
        if not _integer(now_ns, MAX_NS) or now_ns < self._last_now_ns:
            raise ValueError("invalid adapter clock")
        self._last_now_ns = now_ns

    def synchronize(self, *, now_ns):
        self._clock(now_ns)
        snapshot = self.authority.snapshot()
        if snapshot.incarnation != self.binding.incarnation:
            self.terminal(now_ns=now_ns)
            raise MarketError("wrong_incarnation")
        if (snapshot.generation, snapshot.paused) != (self._snapshot.generation, self._snapshot.paused):
            self._boundary_ns = now_ns
            if snapshot.paused or self._terminal:
                self.decoder.pause(now_ms=now_ns // 1_000_000)
            else:
                self.decoder.resume(now_ms=now_ns // 1_000_000)
        self._snapshot = snapshot
        return snapshot

    def terminal(self, *, now_ns):
        self._terminal = True
        self.authority.pause()
        if _integer(now_ns, MAX_NS) and now_ns >= self._last_now_ns:
            self._clock(now_ns)
        self.decoder.pause(now_ms=self._last_now_ns // 1_000_000)

    def consume_terminal(self, readout, *, now_ns):
        """Account validated terminal telemetry without entering the decoder."""
        if not self._terminal:
            raise MarketError("native_running")
        self._clock(now_ns)
        self._sample(readout, now_ns)
        return {"decoder": {"status": "paused", "reason": "native_ended"},
                "proposal": None, "result": None}

    def _sample(self, value, now_ns):
        if hasattr(value, "to_dict"):
            value = value.to_dict()
        if type(value) is not dict or set(value) != _FIELDS:
            raise ValueError("invalid native readout fields")
        if any(value[name] != getattr(self.binding, name) for name in (
            "worker_session", "source_sha256", "header_sha256", "protocol_sha256",
        )):
            raise MarketError("wrong_source")
        for name in ("observation_index", "start_tick", "end_tick"):
            if not _integer(value[name]):
                raise ValueError("invalid observation interval")
        index = value["observation_index"]
        if index != self._last_index + 1 or index >= self._max_observations:
            raise ValueError("native observation discontinuity")
        if (value["start_tick"], value["end_tick"]) != (index * 5000, (index + 1) * 5000):
            raise ValueError("invalid observation ticks")
        start, completion = value["wall_start_ns"], value["wall_completion_ns"]
        if (not _integer(start, MAX_NS) or not _integer(completion, MAX_NS)
                or not self._last_completion_ns <= start <= completion <= now_ns
                or now_ns - completion > self.decoder.configuration["max_sample_age_ms"] * 1_000_000):
            raise ValueError("invalid observation wall clocks")
        bins = value["group_bin_counts"]
        if (type(bins) not in (list, tuple) or len(bins) != 50
                or any(type(row) not in (list, tuple) or len(row) != len(GROUPS)
                       or any(not _integer(count, 16_670_000) for count in row) for row in bins)):
            raise ValueError("invalid validated bins")
        if not _digest(value["frame_sha256"]) or value["input_kind"] not in ("image", "black"):
            raise ValueError("invalid input identity")
        if value["input_kind"] == "black":
            if value["dispatch_id"] is not None or value["frame_sha256"] != BLACK_SHA256:
                raise ValueError("invalid black identity")
        else:
            try:
                if str(UUID(value["dispatch_id"])) != value["dispatch_id"]:
                    raise ValueError("invalid image dispatch")
            except (TypeError, AttributeError):
                raise ValueError("invalid image dispatch") from None
        self._last_index, self._last_completion_ns = index, completion
        return {
            "source_sha256": value["source_sha256"], "session_id": value["worker_session"],
            "observation_index": index, "start_tick": value["start_tick"], "end_tick": value["end_tick"],
            "left_count": sum(row[GROUPS.index("motor_left")] for row in bins),
            "right_count": sum(row[GROUPS.index("motor_right")] for row in bins),
            "wall_start_ms": start // 1_000_000, "wall_completion_ms": completion // 1_000_000,
            "input_version": "native-" + value["input_kind"] + "-v1",
            "frame_sha256": value["frame_sha256"],
        }, start

    def consume(self, readout, *, now_ns):
        if self._terminal:
            raise MarketError("native_ended")
        try:
            snapshot = self.synchronize(now_ns=now_ns)
            sample, start_ns = self._sample(readout, now_ns)
            if start_ns < self._boundary_ns:
                self.decoder.reset(now_ms=now_ns // 1_000_000)
                return {"decoder": {"status": "reset", "reason": "before_boundary", "proposal": None},
                        "proposal": None, "result": None}
            decoded = self.decoder.consume(sample, now_ms=now_ns // 1_000_000)
            result = proposal = None
            if decoded["status"] == "proposal":
                measured = decoded["proposal"]
                row = next(row for row in snapshot.rows if row.id == measured["drink_id"])
                proposal = NativeProposal(
                    "market-proposal-v1", str(uuid4()), uuid4().hex, "native_measurement",
                    self.binding.worker_session, sample["observation_index"] + 1, snapshot.generation,
                    snapshot.config_id, self.decoder.policy_version, snapshot.incarnation,
                    measured["drink_id"], measured["target_rappen"], row.drink_version,
                    readout["wall_completion_ns"],
                    (measured["path_start_tick"] // 10, measured["completion_tick"] // 10),
                    snapshot.server_utc, self.binding.source_sha256, self.binding.header_sha256,
                    self.binding.protocol_sha256, self.binding.readout_configuration_sha256,
                )
                result = self.authority.submit_native(proposal)
            return {"decoder": decoded, "proposal": asdict(proposal) if proposal else None,
                    "result": asdict(result) if result else None}
        except (MarketError, ValueError, TypeError, KeyError):
            self.terminal(now_ns=now_ns)
            raise


class NativePricePump:
    """Bridge only public session exports to the public native price adapter.

    Construct before session.start(); call maintain() from the single sequential
    coordinator. The feed and last displayed outcome are bounded; no observation
    is replayed by polling snapshots and no rejected proposal is retried.
    """

    def __init__(self, authority, session, clock=None, *, max_sample_age_ms=5000,
                 max_observations=None):
        if authority.mode != "native":
            raise MarketError("wrong_mode")
        self.authority, self.session = authority, session
        self.clock = clock or SystemClock()
        self.adapter = None
        self._max_sample_age_ms = max_sample_age_ms
        if max_observations is None:
            config = getattr(session, "config", None)
            max_observations = getattr(config, "max_observations", 86_400)
        self._max_observations = max_observations
        self._terminal = False
        self._fault = None
        self._consumed = 0
        self._last_decoder = self._last_result = None
        self.session.enable_readout()

    def snapshot(self):
        return {
            "schema": "market-native-price/v1",
            "label": "experimental configured motor readout",
            "bound": self.adapter is not None, "terminal": self._terminal,
            "fault": self._fault, "observations_consumed": self._consumed,
            "last_decoder": dict(self._last_decoder) if self._last_decoder else None,
            "last_result": dict(self._last_result) if self._last_result else None,
        }

    def _stop(self, now_ns, fault=None):
        self._terminal, self._fault = True, fault
        if self.adapter is not None:
            self.adapter.terminal(now_ns=now_ns)
        else:
            self.authority.pause()

    def _observe_terminal(self, now_ns=None):
        if not self._terminal:
            native = self.session.snapshot()
            if native["state"] in ("faulted", "ended", "closed", "stopping"):
                self._stop(now_ns, native["fault"])

    def maintain(self):
        now_ns = None
        try:
            self._observe_terminal()
            identity = self.session.readout_identity()
            if self.adapter is None and identity is not None:
                self.adapter = NativePriceAdapter(
                    self.authority, **{name: identity[name] for name in (
                        "worker_session", "source_sha256", "header_sha256", "protocol_sha256",
                    )}, max_sample_age_ms=self._max_sample_age_ms,
                    max_observations=self._max_observations,
                )
                if self._terminal:
                    self.adapter.terminal(now_ns=None)
            if self.adapter is not None:
                if identity is None or any(identity[name] != getattr(self.adapter.binding, name) for name in (
                    "worker_session", "source_sha256", "header_sha256", "protocol_sha256",
                )):
                    raise MarketError("wrong_source")
                records = tuple(self.session.poll_readouts())
                self._observe_terminal()
                if len(records) > 8:
                    raise ValueError("native feed bound exceeded")
                for record in records:
                    # A worker may complete during snapshot/queue acquisition.
                    # Receipt freshness is checked against a new real clock,
                    # never inferred from the record's own completion value.
                    now_ns = self.clock.sample().monotonic_ns
                    self._observe_terminal(now_ns)
                    if self._terminal:
                        outcome = self.adapter.consume_terminal(record, now_ns=now_ns)
                    else:
                        outcome = self.adapter.consume(record, now_ns=now_ns)
                    self._consumed += 1
                    decoded = outcome["decoder"]
                    self._last_decoder = {key: decoded[key] for key in ("status", "reason")}
                    if "phase" in decoded:
                        self._last_decoder["phase"] = decoded["phase"]
                    if outcome["result"] is not None:
                        self._last_result = outcome["result"]
                if not records:
                    now_ns = self.clock.sample().monotonic_ns
                    self.adapter.synchronize(now_ns=now_ns)
            return self.snapshot()
        except (MarketError, ValueError, TypeError, KeyError) as error:
            self._stop(now_ns, getattr(error, "code", "protocol"))
            raise
