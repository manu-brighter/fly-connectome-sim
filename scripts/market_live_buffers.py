"""Pure in-memory passive-cell ring and session-local image admission.

No engine, runtime, network, rendering or disk work occurs here. The later runner
owns observation dispatch, transition journaling and terminal callback failures.
Instances are single-owner, synchronous state; concurrent access is unsupported.

Ring hash contract ``market-live-cell-ring/v1`` (SHA256): the exact ASCII prefix
below, then unsigned little-endian uint64 valid length and write position, then
four chronological little-endian signed int64 columns (observation_index,
bin_index, start_tick, end_tick), then chronological row-major uint8 counts.
Only valid rows enter the digest; unused storage and timing/export counters do
not. Column storage has shape [1000], counts [1000,256]. No native byte order,
JSON serialization, physical ring order or implicit padding enters the digest.

``owned_array_bytes`` counts only the five fixed arrays (288000 bytes), excluding
Python/scalar objects and caller-owned detached exports. One export allocates
17040 array bytes: 50x256 uint8 counts, four 50-element int64 columns, 5x256
uint16 sums and two 5-element int64 window clocks. No export/history is retained
by the ring. A callback converts at most one 256-byte count vector. Hashing uses
contiguous memoryviews of existing arrays, without a chronological snapshot.
Caller code must bound its own retention. Sink timing covers validation/copy/
counter work only, excluding engine-side callback preparation and export work.
"""

from dataclasses import dataclass, asdict
from hashlib import sha256
import re
import struct
from time import perf_counter_ns

import numpy as np


RING_VERSION = "market-live-cell-ring/v1"
ADMISSION_VERSION = "market-live-image-admission/v1"
RING_HASH_PREFIX = (
    b"market-live-cell-ring/v1\ncounts=|u1;shape=1000,256\n"
    b"observation_index,bin_index,start_tick,end_tick=<i8;shape=1000\n"
)
MAX_INT64 = 2**63 - 1
PENDING_DEADLINE_MS = 300000
BIN_FIELDS = {"observation_index", "bin_index", "start_tick", "end_tick", "counts"}


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= MAX_INT64:
        raise ValueError("Expected a bounded true Python integer")
    return value


class CellRing:
    """Callable native sink for contiguous 50-bin, 500-model-ms observations.

    Call ``ring(payload)`` for each original bin. After observe returns, call
    ``export_observation(index)`` once for that latest completed observation.
    Empty, incomplete, older, future and already-exported requests fail. Earlier
    completed exports may be skipped, but are never re-exported as fresh data.
    Invalid payloads raise before storage/counters/timings change; the caller
    must treat a native callback failure as terminal rather than retrying it.
    """

    __slots__ = (
        "_counts", "_observation_index", "_bin_index", "_start_tick", "_end_tick",
        "_total_bins", "_last_exported", "sink_body_calls",
        "sink_body_total_ns", "sink_body_max_ns",
    )

    def __init__(self):
        self._counts = np.zeros((1000, 256), dtype=np.uint8)
        self._observation_index = np.zeros(1000, dtype="<i8")
        self._bin_index = np.zeros(1000, dtype="<i8")
        self._start_tick = np.zeros(1000, dtype="<i8")
        self._end_tick = np.zeros(1000, dtype="<i8")
        self._total_bins = 0
        self._last_exported = -1
        self.sink_body_calls = 0
        self.sink_body_total_ns = 0
        self.sink_body_max_ns = 0

    @property
    def owned_array_bytes(self):
        return sum(array.nbytes for array in self._arrays())

    def _arrays(self):
        return (self._observation_index, self._bin_index, self._start_tick, self._end_tick, self._counts)

    @property
    def stats(self):
        return {
            "total_bins": self._total_bins,
            "valid_length": min(self._total_bins, 1000),
            "write_position": self._total_bins % 1000,
            "evictions": max(self._total_bins - 1000, 0),
        }

    def __call__(self, payload):
        started = perf_counter_ns()
        if type(payload) is not dict or set(payload) != BIN_FIELDS:
            raise ValueError("Unknown or missing bin fields")
        observation, ordinal, start, end = (
            _integer(payload[name]) for name in ("observation_index", "bin_index", "start_tick", "end_tick")
        )
        expected_observation, expected_bin = divmod(self._total_bins, 50)
        if (observation, ordinal, start, end) != (
            expected_observation, expected_bin, self._total_bins * 100, (self._total_bins + 1) * 100,
        ):
            raise ValueError("Noncontinuous original 100-tick bin")
        counts = payload["counts"]
        if type(counts) is not list or len(counts) != 256:
            raise ValueError("Expected exactly 256 cohort counts")
        for count in counts:
            if type(count) is not int or not 0 <= count <= 100:
                raise ValueError("Count outside original bin duration")
        converted = np.asarray(counts, dtype=np.uint8)
        position = self._total_bins % 1000
        self._counts[position] = converted
        self._observation_index[position] = observation
        self._bin_index[position] = ordinal
        self._start_tick[position] = start
        self._end_tick[position] = end
        self._total_bins += 1
        elapsed = perf_counter_ns() - started
        self.sink_body_calls += 1
        self.sink_body_total_ns += elapsed
        self.sink_body_max_ns = max(self.sink_body_max_ns, elapsed)

    def export_observation(self, observation_index):
        _integer(observation_index)
        if (self._total_bins == 0 or self._total_bins % 50
                or observation_index != self._total_bins // 50 - 1
                or observation_index <= self._last_exported):
            raise ValueError("Expected a fresh latest completed observation")
        # Both 1000 and 50 are fixed; completed observations never straddle the
        # physical ring boundary, so no full-ring snapshot or concatenate occurs.
        start = (self._total_bins - 50) % 1000
        stop = start + 50
        counts = self._counts[start:stop].copy()
        result = {
            "observation_index": observation_index,
            "observation_indices": self._observation_index[start:stop].copy(),
            "bin_index": self._bin_index[start:stop].copy(),
            "start_tick": self._start_tick[start:stop].copy(),
            "end_tick": self._end_tick[start:stop].copy(),
            "counts": counts,
            "window_counts": counts.reshape(5, 10, 256).sum(axis=1, dtype=np.uint16),
            "window_start_tick": self._start_tick[start:stop:10].copy(),
            "window_end_tick": self._end_tick[start + 9:stop:10].copy(),
        }
        self._last_exported = observation_index
        return result

    def ring_sha256(self):
        stats = self.stats
        digest = sha256(RING_HASH_PREFIX)
        digest.update(struct.pack("<QQ", stats["valid_length"], stats["write_position"]))
        start = stats["write_position"] if self._total_bins >= 1000 else 0
        stop = stats["valid_length"]
        for array in self._arrays():
            if start < stop:
                digest.update(memoryview(array[start:stop]).cast("B"))
            if start:
                digest.update(memoryview(array[:start]).cast("B"))
        return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class _Request:
    sequence: int
    frame_sha256: str
    offered_ms: int


class ImageAdmission:
    """One active and one waiting request; monotonic integer-ms session state.

    ``offer`` admits to the pending slot even when idle. ``handoff`` is explicit
    immediately before the runner's observe dispatch; ``finish`` is explicit
    at its chosen boundary and never activates a pending request. All methods
    return detached transition dictionaries with status, request and wall_ms.
    Request offered_ms records the offer time for both admitted and rejected
    requests; admission happens at that same time only when status is admitted.
    Statuses: admitted/full, handed_off/expired/busy/empty, and completed.

    Sequence and timestamps are true Python ints in [1,2**63-1] and
    [0,2**63-1] respectively. Frame hashes are lowercase 64-digit hex strings.
    Valid new offers advance the high watermark even on full rejection; invalid
    arguments/reused sequences change nothing, including the clock watermark.
    Every successful operation (also full/busy/empty) checks/advances the clock.
    Pending expiry is checked on handoff, even while busy; full rejection never
    replaces or refreshes an entry. No history is kept. This is session-local
    deduplication, with no durable restart or delivery guarantee.
    """

    __slots__ = ("_active", "_pending", "_high_watermark", "_last_now_ms")

    def __init__(self):
        self._active = None
        self._pending = None
        self._high_watermark = 0
        self._last_now_ms = None

    @property
    def active(self):
        return None if self._active is None else asdict(self._active)

    @property
    def pending(self):
        return None if self._pending is None else asdict(self._pending)

    @property
    def high_watermark(self):
        return self._high_watermark

    @property
    def state(self):
        return {
            "active": self.active, "pending": self.pending,
            "high_watermark": self._high_watermark, "last_now_ms": self._last_now_ms,
        }

    def _check_clock(self, now_ms):
        _integer(now_ms)
        if self._last_now_ms is not None and now_ms < self._last_now_ms:
            raise ValueError("Monotonic wall clock regressed")

    @staticmethod
    def _result(status, request, now_ms):
        return {"status": status, "request": None if request is None else asdict(request), "wall_ms": now_ms}

    def offer(self, sequence, frame_sha256, *, now_ms):
        _integer(sequence, 1)
        if type(frame_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", frame_sha256) is None:
            raise ValueError("Expected a lowercase frame SHA256")
        if sequence <= self._high_watermark:
            raise ValueError("Request sequence must strictly increase")
        self._check_clock(now_ms)
        request = _Request(sequence, frame_sha256, now_ms)
        self._high_watermark = sequence
        self._last_now_ms = now_ms
        if self._pending is not None:
            return self._result("full", request, now_ms)
        self._pending = request
        return self._result("admitted", request, now_ms)

    def handoff(self, *, now_ms):
        self._check_clock(now_ms)
        self._last_now_ms = now_ms
        if self._pending is not None and now_ms - self._pending.offered_ms >= PENDING_DEADLINE_MS:
            expired = self._pending
            self._pending = None
            return self._result("expired", expired, now_ms)
        if self._active is not None:
            return self._result("busy", None, now_ms)
        if self._pending is None:
            return self._result("empty", None, now_ms)
        self._active = self._pending
        self._pending = None
        return self._result("handed_off", self._active, now_ms)

    def finish(self, sequence, *, now_ms):
        _integer(sequence, 1)
        self._check_clock(now_ms)
        if self._active is None or sequence != self._active.sequence:
            raise ValueError("Completion must identify the active request")
        request = self._active
        self._active = None
        self._last_now_ms = now_ms
        return self._result("completed", request, now_ms)
