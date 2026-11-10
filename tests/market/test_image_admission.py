"""Metadata lifecycle checks; no image decoding or native observation occurs."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from threading import Barrier

import pytest

from market.image_admission import (
    AdmissionController, AdmissionError, CompletionReceipt, DispatchPermit,
    Receipt, Reservation, StartReceipt,
)
from market.price_service import ClockSample


INCARNATION = "00000000-0000-4000-8000-000000000001"
WORKER = "00000000-0000-4000-8000-000000000002"
OTHER = "00000000-0000-4000-8000-000000000003"
SOURCE = "a" * 64
FRAME = "b" * 64
VERSION = "market-rgb64/v1"
MAX_NS = 2 ** 63 - 1


class MetadataClock:
    def __init__(self, ns=1_000_000_000):
        self.ns = ns
        self.failure = None
        self.calls = 0

    def sample(self):
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return ClockSample(self.ns, datetime(2026, 11, 10, tzinfo=timezone.utc))

    def describe(self):
        return {"implementation": "test-metadata-clock"}


@pytest.fixture
def admission():
    clock = MetadataClock()
    return AdmissionController(INCARNATION, clock), clock


def accepted(controller):
    reservation = controller.reserve()
    return controller.admit(id=reservation.id, source_sha256=SOURCE, encoded_bytes=17)


def ready(controller):
    item = accepted(controller)
    controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION)
    return controller.moderate(id=item.id, action_id="staff-1", approved=True)


def dispatched(controller):
    return controller.dispatch(id=ready(controller).id, worker_session=WORKER)


def start_for(permit, clock, *, first=23):
    return StartReceipt(
        permit.id, permit.incarnation, permit.dispatch_id, permit.worker_session,
        permit.frame_sha256, clock.ns, first,
    )


def completion_for(start, clock):
    return CompletionReceipt(
        start.id, start.incarnation, start.dispatch_id, start.worker_session,
        start.frame_sha256, tuple(range(start.first_observation_index,
                                       start.first_observation_index + 8)), clock.ns,
    )


def error(code, operation, **kwargs):
    with pytest.raises(AdmissionError) as caught:
        operation(**kwargs)
    assert caught.value.code == code
    assert str(caught.value) == code


def test_concurrent_reservations_never_overbook(admission):
    controller, _ = admission
    barrier = Barrier(12)

    def reserve_once(_):
        barrier.wait()
        try:
            return controller.reserve()
        except AdmissionError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(reserve_once, range(12)))
    assert sum(result == "full" for result in results) == 11
    snapshot = controller.snapshot()
    assert snapshot.reserved_receipt_slots == 1
    assert snapshot.terminal_count == 0
    assert snapshot.pending is snapshot.active is None


def test_reservation_equality_and_old_cancel(admission):
    controller, clock = admission
    old = controller.reserve()
    assert (old.reserved_ns, old.expires_ns) == (1_000_000_000, 6_000_000_000)
    error("not_found", controller.status, id=old.id)
    clock.ns = old.expires_ns - 1
    error("full", controller.reserve)
    clock.ns += 1
    fresh = controller.reserve()
    error("not_found", controller.cancel_reservation, id=old.id)
    assert controller.snapshot().reservation == fresh
    controller.cancel_reservation(id=fresh.id)
    error("not_found", controller.cancel_reservation, id=fresh.id)
    assert controller.snapshot().reserved_receipt_slots == 0


def test_admit_owns_original_deadlines(admission):
    controller, clock = admission
    reservation = controller.reserve()
    clock.ns += 4_000_000_000
    item = controller.admit(id=reservation.id, source_sha256=SOURCE, encoded_bytes=17)
    assert (item.accepted_ns, item.deadline_ns, item.decode_deadline_ns,
            item.moderation_deadline_ns) == (
        5_000_000_000, 305_000_000_000, 15_000_000_000, 65_000_000_000,
    )
    assert (item.status, item.detail, item.revision, item.time_uncertain) == (
        "accepted", "decoding", 1, False,
    )
    clock.ns += 1
    assert controller.admit(id=item.id, source_sha256=SOURCE, encoded_bytes=17) == item
    error("idempotency_conflict", controller.admit,
          id=item.id, source_sha256="c" * 64, encoded_bytes=17)
    error("full", controller.reserve)
    assert controller.snapshot().reserved_receipt_slots == 1


@pytest.mark.parametrize(("phase", "offset", "detail"), [
    ("decode", 9_999_999_999, "awaiting_approval"),
    ("decode", 10_000_000_000, "decode_timeout"),
    ("moderate", 59_999_999_999, "ready"),
    ("moderate", 60_000_000_000, "moderation_timeout"),
])
def test_decode_and_moderation_equality(admission, phase, offset, detail):
    controller, clock = admission
    item = accepted(controller)
    if phase == "moderate":
        clock.ns += 9_000_000_000
        controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION)
    clock.ns = item.accepted_ns + offset
    operation = controller.decoded if phase == "decode" else controller.moderate
    kwargs = {"frame_sha256": FRAME, "preprocessing_version": VERSION} if phase == "decode" else {
        "action_id": "staff", "approved": True,
    }
    if detail.endswith("timeout"):
        error("invalid_transition", operation, id=item.id, **kwargs)
    else:
        operation(id=item.id, **kwargs)
    result = controller.status(id=item.id)
    assert result.detail == detail
    assert result.deadline_ns == item.deadline_ns
    if detail.endswith("timeout"):
        assert result.status == "rejected"
        assert result.terminal_ns == clock.ns


@pytest.mark.parametrize(("decoded_first", "detail"), [
    (False, "decode_timeout"), (True, "moderation_timeout"),
])
def test_delayed_maintenance_preserves_specific_timeout(admission, decoded_first, detail):
    controller, clock = admission
    item = accepted(controller)
    if decoded_first:
        controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION)
    clock.ns = item.deadline_ns + 40
    snapshot = controller.maintain()
    result = controller.status(id=item.id)
    assert (result.detail, result.status, result.terminal_ns) == (detail, "rejected", clock.ns)
    assert snapshot.reserved_receipt_slots == 0


def test_full_lifecycle_retains_confirmed_start(admission):
    controller, clock = admission
    permit = dispatched(controller)
    assert (permit.deadline_ns, permit.exposure_observations) == (301_000_000_000, 8)
    dispatching = controller.status(id=permit.id)
    assert (dispatching.status, dispatching.detail, dispatching.revision) == ("queued", "dispatching", 4)
    assert controller.snapshot().active is None
    error("full", controller.reserve)
    start = start_for(permit, clock)
    processing = controller.started(receipt=start)
    assert (processing.status, processing.detail, processing.revision) == ("processing", "processing", 5)
    assert controller.snapshot().pending is None
    assert controller.snapshot().active == processing
    pending = accepted(controller)
    assert controller.snapshot().reserved_receipt_slots == 2
    clock.ns = permit.deadline_ns + 1
    assert controller.started(receipt=start).revision == 5
    complete = completion_for(start, clock)
    result = controller.complete(receipt=complete)
    assert (result.status, result.detail, result.revision) == ("processed", "completed", 6)
    assert (result.started_ns, result.first_observation_index) == (start.started_ns, 23)
    assert result.terminal_ns == result.completed_ns == clock.ns
    assert controller.complete(receipt=complete) == result
    assert controller.started(receipt=start) == result
    assert controller.status(id=pending.id).detail == "decode_timeout"
    assert controller.snapshot().terminal_count == 2


def test_queued_ttl_boundary_never_renews(admission):
    controller, clock = admission
    item = ready(controller)
    clock.ns = item.deadline_ns - 1
    assert controller.moderate(id=item.id, action_id="staff-1", approved=True) == item
    assert controller.admit(id=item.id, source_sha256=SOURCE, encoded_bytes=17) == item
    clock.ns += 1
    error("invalid_transition", controller.dispatch, id=item.id, worker_session=WORKER)
    expired = controller.status(id=item.id)
    assert (expired.status, expired.detail, expired.revision) == ("expired", "ttl_expired", 4)
    assert expired.deadline_ns == item.deadline_ns
    assert controller.moderate(id=item.id, action_id="staff-1", approved=True) == expired
    assert controller.snapshot().fault is None


@pytest.mark.parametrize(("delay", "succeeds"), [
    (4_203_000_000, True), (9_999_999_999, True), (10_000_000_000, False),
])
def test_4203ms_start_receipt_and_10s_equality(admission, delay, succeeds):
    controller, clock = admission
    permit = dispatched(controller)
    actual_start = clock.ns + 1
    clock.ns += delay
    start = replace(start_for(permit, clock), started_ns=actual_start)
    if succeeds:
        assert controller.started(receipt=start).started_ns == actual_start
    else:
        error("stopped", controller.started, receipt=start)
        result = controller.status(id=permit.id)
        assert (result.status, result.detail, result.started_ns) == ("rejected", "worker_outcome_unknown", None)
        assert controller.snapshot().stop_required


def test_late_receipt_of_timely_start(admission):
    controller, clock = admission
    item = ready(controller)
    clock.ns = item.deadline_ns - 2_000_000_000
    permit = controller.dispatch(id=item.id, worker_session=WORKER)
    start = replace(start_for(permit, clock), started_ns=item.deadline_ns - 1)
    clock.ns = item.deadline_ns + 2_203_000_000
    controller.maintain()
    assert controller.status(id=item.id).detail == "dispatching"
    result = controller.started(receipt=start)
    assert result.status == "processing"
    assert result.started_ns < result.deadline_ns < clock.ns


@pytest.mark.parametrize("change", [
    {"started_ns": 301_000_000_000}, {"started_ns": 999_999_999},
    {"started_ns": 1_000_000_001}, {"incarnation": OTHER},
    {"worker_session": OTHER}, {"dispatch_id": OTHER}, {"frame_sha256": SOURCE},
    {"first_observation_index": MAX_NS - 6},
])
def test_first_start_contradictions_stop_unknown(admission, change):
    controller, clock = admission
    permit = dispatched(controller)
    result = controller.started(receipt=replace(start_for(permit, clock), **change))
    assert (result.status, result.detail, result.revision) == ("rejected", "worker_outcome_unknown", 5)
    assert result.started_ns is None
    assert controller.snapshot().fault == "worker_outcome_unknown"
    assert controller.snapshot().stop_required


@pytest.mark.parametrize("change", [
    {"started_ns": 1_000_000_001}, {"first_observation_index": 24},
    {"incarnation": OTHER}, {"worker_session": OTHER}, {"dispatch_id": OTHER},
    {"frame_sha256": SOURCE}, {"first_observation_index": MAX_NS},
])
def test_current_worker_contradictions_stop_before_retry_conflict(admission, change):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    controller.started(receipt=start)
    other = ready(controller)
    clock.ns += 2
    result = controller.started(receipt=replace(start, **change))
    assert (result.detail, result.revision) == ("worker_outcome_unknown", 6)
    assert (result.started_ns, result.first_observation_index) == (1_000_000_000, 23)
    assert controller.status(id=other.id).detail == "worker_outcome_unknown"
    assert controller.snapshot().reserved_receipt_slots == 0
    error("stopped", controller.reserve)


def test_completion_without_confirmed_start_is_unknown(admission):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    result = controller.complete(receipt=completion_for(start, clock))
    assert result.detail == "worker_outcome_unknown"
    assert result.started_ns is result.completed_ns is None
    assert controller.snapshot().stop_required


@pytest.mark.parametrize("phase", ["decoding", "awaiting_approval", "ready"])
@pytest.mark.parametrize("operation", ["started", "complete"])
def test_unsolicited_known_receipts_stop(admission, phase, operation):
    controller, clock = admission
    item = accepted(controller)
    if phase != "decoding":
        controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION)
    if phase == "ready":
        controller.moderate(id=item.id, action_id="a", approved=True)
    start = StartReceipt(item.id, INCARNATION, OTHER, WORKER, FRAME, clock.ns, 0)
    receipt = start if operation == "started" else completion_for(start, clock)
    result = getattr(controller, operation)(receipt=receipt)
    assert result.detail == "worker_outcome_unknown"
    assert controller.snapshot().stop_required


def test_terminal_retry_conflict_cannot_fault_new_work(admission):
    controller, clock = admission
    permit = dispatched(controller)
    start = start_for(permit, clock)
    controller.started(receipt=start)
    complete = completion_for(start, clock)
    processed = controller.complete(receipt=complete)
    live = ready(controller)
    error("idempotency_conflict", controller.started,
          receipt=replace(start, started_ns=MAX_NS, first_observation_index=MAX_NS))
    error("idempotency_conflict", controller.complete,
          receipt=replace(complete, observation_indices=(), completed_ns=MAX_NS))
    assert controller.started(receipt=start) == processed
    assert controller.complete(receipt=complete) == processed
    assert controller.dispatch(id=permit.id, worker_session=WORKER) == permit
    assert controller.status(id=live.id) == live
    assert controller.snapshot().fault is None


def test_terminal_unrecorded_worker_operation_cannot_fault_new_work(admission):
    controller, clock = admission
    item = accepted(controller)
    controller.decode_failed(id=item.id)
    live = accepted(controller)
    start = StartReceipt(item.id, INCARNATION, OTHER, WORKER, FRAME, MAX_NS, MAX_NS)
    error("invalid_transition", controller.started, receipt=start)
    error("invalid_transition", controller.complete, receipt=completion_for(replace(start, first_observation_index=0), clock))
    assert controller.status(id=live.id) == live
    assert controller.snapshot().fault is None


@pytest.mark.parametrize("indices", [(), (23,), tuple(range(23, 30)),
                                      (23, 24, 25, 26, 27, 28, 29, 31),
                                      (24, 25, 26, 27, 28, 29, 30, 31)])
def test_exact_eight_contiguous_indices(admission, indices):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    controller.started(receipt=start)
    result = controller.complete(receipt=replace(completion_for(start, clock), observation_indices=indices))
    assert (result.status, result.detail, result.completed_ns) == ("rejected", "worker_outcome_unknown", None)
    assert result.started_ns == start.started_ns


@pytest.mark.parametrize("change", [
    {"completed_ns": 999_999_999}, {"completed_ns": 1_000_000_001},
    {"incarnation": OTHER}, {"worker_session": OTHER}, {"dispatch_id": OTHER},
    {"frame_sha256": SOURCE},
])
def test_current_completion_contradictions_preserve_start(admission, change):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    controller.started(receipt=start)
    result = controller.complete(receipt=replace(completion_for(start, clock), **change))
    assert result.detail == "worker_outcome_unknown"
    assert result.started_ns == start.started_ns
    assert result.completed_ns is None


def test_worker_index_overflow_atomically_stops_unknown(admission):
    controller, clock = admission
    start = start_for(dispatched(controller), clock, first=MAX_NS - 7)
    assert controller.started(receipt=start).first_observation_index == MAX_NS - 7
    clock.ns = MAX_NS
    result = controller.complete(receipt=completion_for(start, clock))
    assert (result.status, result.terminal_ns, result.revision) == ("processed", MAX_NS, 6)
    assert controller.maintain().terminal_count == 1


def test_nonworker_idempotency_and_moderation_action_bounds(admission):
    controller, _ = admission
    item = accepted(controller)
    decoded = controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION)
    assert controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION) == decoded
    error("idempotency_conflict", controller.decoded,
          id=item.id, frame_sha256=SOURCE, preprocessing_version=VERSION)
    rejected = controller.moderate(id=item.id, action_id="staff-1", approved=False)
    assert (rejected.status, rejected.detail, rejected.revision) == ("rejected", "moderation_rejected", 3)
    assert controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION) == rejected
    assert controller.moderate(id=item.id, action_id="staff-1", approved=False) == rejected
    error("idempotency_conflict", controller.moderate, id=item.id, action_id="staff-1", approved=True)
    error("invalid_transition", controller.moderate, id=item.id, action_id="staff-2", approved=False)
    error("invalid_transition", controller.decode_failed, id=item.id)
    fresh = accepted(controller)
    failed = controller.decode_failed(id=fresh.id)
    assert controller.decode_failed(id=fresh.id) == failed
    error("invalid_transition", controller.decoded,
          id=fresh.id, frame_sha256=FRAME, preprocessing_version=VERSION)
    error("invalid_transition", controller.moderate, id=fresh.id, action_id="x", approved=True)


def test_active_plus_ready_blocks_dispatch_but_worker_binding_persists(admission):
    controller, clock = admission
    permit = dispatched(controller)
    start = start_for(permit, clock)
    controller.started(receipt=start)
    next_item = ready(controller)
    error("full", controller.dispatch, id=next_item.id, worker_session=WORKER)
    controller.complete(receipt=completion_for(start, clock))
    error("wrong_worker", controller.dispatch, id=next_item.id, worker_session=OTHER)
    assert controller.status(id=next_item.id).detail == "ready"
    second = controller.dispatch(id=next_item.id, worker_session=WORKER)
    assert second.dispatch_id != permit.dispatch_id
    error("idempotency_conflict", controller.dispatch, id=permit.id, worker_session=OTHER)


def test_capacity_reserves_terminal_space_and_prunes_only_by_age(admission):
    controller, clock = admission
    # All completions here are real public transitions, not manufactured storage.
    for _ in range(511):
        item = accepted(controller)
        controller.decode_failed(id=item.id)
    last = accepted(controller)
    assert (controller.snapshot().terminal_count, controller.snapshot().reserved_receipt_slots) == (511, 1)
    error("full", controller.reserve)
    terminal = controller.decode_failed(id=last.id)
    assert controller.snapshot().terminal_count == 512
    error("capacity", controller.reserve)
    clock.ns = terminal.terminal_ns + 899_999_999_999
    error("capacity", controller.reserve)
    assert controller.status(id=last.id) == terminal
    clock.ns += 1
    fresh = controller.reserve()
    assert (controller.snapshot().terminal_count, controller.snapshot().reserved_receipt_slots) == (0, 1)
    error("not_found", controller.status, id=last.id)
    error("not_found", controller.admit, id=last.id, source_sha256=SOURCE, encoded_bytes=17)
    assert controller.snapshot().reservation == fresh


def test_concurrent_capacity_reservations_are_atomic(admission):
    controller, _ = admission
    for _ in range(511):
        controller.decode_failed(id=accepted(controller).id)
    barrier = Barrier(8)

    def attempt(_):
        barrier.wait()
        try:
            item = accepted(controller)
            return controller.decode_failed(id=item.id).id
        except AdmissionError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(attempt, range(8)))
    assert sum(value not in ("full", "capacity") for value in outcomes) == 1
    assert controller.snapshot().terminal_count == 512


@pytest.mark.parametrize("failure", ["exception", "regression", "bool", "overflow", "dict"])
def test_clock_failure_preserves_diagnostic_state(admission, failure):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    processing = controller.started(receipt=start)
    other = accepted(controller)
    if failure == "exception":
        clock.failure = RuntimeError("private host detail")
    elif failure == "regression":
        clock.ns -= 1
    elif failure == "bool":
        clock.ns = True
    elif failure == "overflow":
        clock.ns = MAX_NS + 1
    else:
        clock.sample = lambda: {"monotonic_ns": 1_000_000_000}
    diagnostic = controller.snapshot()
    calls = clock.calls
    assert (diagnostic.fault, diagnostic.stop_required, diagnostic.reserved_receipt_slots) == ("clock", True, 0)
    result = controller.status(id=start.id)
    assert (result.detail, result.time_uncertain, result.terminal_ns, result.revision) == ("clock", True, 1_000_000_000, 6)
    assert (result.started_ns, result.first_observation_index, result.frame_sha256) == (
        processing.started_ns, 23, FRAME,
    )
    assert controller.status(id=other.id).time_uncertain
    assert controller.maintain() == diagnostic
    assert controller.stop(reason="worker_failed") == diagnostic
    error("clock", controller.reserve)
    error("clock", controller.started, receipt=start)
    assert clock.calls == calls


def test_first_clock_failure_and_reservation_fault_cleanup():
    clock = MetadataClock()
    clock.failure = OSError("private")
    controller = AdmissionController(INCARNATION, clock)
    error("clock", controller.reserve)
    assert controller.snapshot().terminal_count == 0
    healthy = MetadataClock()
    other = AdmissionController(INCARNATION, healthy)
    other.reserve()
    healthy.failure = OSError("private")
    assert other.maintain().reservation is None
    assert other.snapshot().fault == "clock"


@pytest.mark.parametrize(("phase", "remaining"), [
    ("reserve", 4_999_999_999), ("admit", 299_999_999_999),
])
def test_deadline_overflow_without_partial_requested_mutation(phase, remaining):
    clock = MetadataClock(MAX_NS - remaining)
    controller = AdmissionController(INCARNATION, clock)
    if phase == "reserve":
        operation, kwargs = controller.reserve, {}
    elif phase == "admit":
        reservation = controller.reserve()
        operation, kwargs = controller.admit, {
            "id": reservation.id, "source_sha256": SOURCE, "encoded_bytes": 17,
        }
    before = controller.snapshot()
    error("capacity", operation, **kwargs)
    assert controller.snapshot() == before


def test_dispatch_headroom_capacity_preserves_ready_receipt():
    clock = MetadataClock(MAX_NS - 300_000_000_000)
    controller = AdmissionController(INCARNATION, clock)
    item = ready(controller)
    clock.ns = MAX_NS - 9_999_999_999
    before = controller.snapshot()
    error("capacity", controller.dispatch, id=item.id, worker_session=WORKER)
    assert controller.snapshot() == before
    # Use another controller to avoid regressing a valid sampled clock.
    other_clock = MetadataClock(MAX_NS - 300_000_000_000)
    other = AdmissionController(OTHER, other_clock)
    other_item = ready(other)
    other_clock.ns = MAX_NS - 10_000_000_000
    assert other.dispatch(id=other_item.id, worker_session=WORKER).deadline_ns == MAX_NS


@pytest.mark.parametrize("phase", ["reservation", "unknown", "pruned"])
def test_unknown_worker_ids_never_fault_live_work(admission, phase):
    controller, clock = admission
    if phase == "reservation":
        item_id = controller.reserve().id
    elif phase == "pruned":
        item_id = accepted(controller).id
        controller.decode_failed(id=item_id)
        clock.ns += 900_000_000_000
        controller.maintain()
    else:
        item_id = OTHER
    start = StartReceipt(item_id, OTHER, OTHER, OTHER, FRAME, MAX_NS, MAX_NS)
    error("not_found", controller.started, receipt=start)
    error("not_found", controller.complete,
          receipt=CompletionReceipt(item_id, OTHER, OTHER, OTHER, FRAME, (), MAX_NS))
    assert controller.snapshot().fault is None


class StringSubclass(str):
    pass


class IntSubclass(int):
    pass


class TupleSubclass(tuple):
    pass


@pytest.mark.parametrize(("method", "changes"), [
    ("admit", {"encoded_bytes": True}), ("admit", {"encoded_bytes": 0}),
    ("admit", {"encoded_bytes": 2_097_153}), ("admit", {"encoded_bytes": IntSubclass(17)}),
    ("admit", {"source_sha256": StringSubclass(SOURCE)}),
    ("admit", {"source_sha256": "A" * 64}), ("admit", {"id": StringSubclass(INCARNATION)}),
    ("decoded", {"preprocessing_version": "market-rgb64/v2"}),
    ("decoded", {"preprocessing_version": StringSubclass(VERSION)}),
    ("moderate", {"approved": 1}), ("moderate", {"action_id": "ü"}),
    ("moderate", {"action_id": "x" * 65}), ("moderate", {"action_id": "a\n"}),
    ("dispatch", {"worker_session": "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"}),
    ("stop", {"reason": "clock"}), ("stop", {"reason": StringSubclass("worker_failed")}),
])
def test_invalid_syntax_never_samples_or_expires(admission, method, changes):
    controller, clock = admission
    item = accepted(controller)
    kwargs = {
        "admit": {"id": item.id, "source_sha256": SOURCE, "encoded_bytes": 17},
        "decoded": {"id": item.id, "frame_sha256": FRAME, "preprocessing_version": VERSION},
        "moderate": {"id": item.id, "action_id": "a", "approved": True},
        "dispatch": {"id": item.id, "worker_session": WORKER},
        "stop": {"reason": "worker_failed"},
    }[method] | changes
    calls = clock.calls
    clock.ns = item.decode_deadline_ns
    error("invalid_request", getattr(controller, method), **kwargs)
    assert clock.calls == calls
    assert controller.status(id=item.id).detail == "decode_timeout"


@pytest.mark.parametrize(("kind", "field", "value"), [
    ("start", "started_ns", True), ("start", "started_ns", -1),
    ("start", "started_ns", MAX_NS + 1), ("start", "started_ns", IntSubclass(1)),
    ("start", "first_observation_index", -1), ("start", "frame_sha256", StringSubclass(FRAME)),
    ("complete", "observation_indices", list(range(23, 31))),
    ("complete", "observation_indices", TupleSubclass(range(23, 31))),
    ("complete", "observation_indices", (True,)),
    ("complete", "observation_indices", tuple(range(9))),
    ("complete", "observation_indices", (MAX_NS + 1,)),
    ("complete", "completed_ns", MAX_NS + 1),
])
def test_forged_worker_syntax_is_rechecked_before_maintenance(admission, kind, field, value):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    receipt = start if kind == "start" else completion_for(start, clock)
    object.__setattr__(receipt, field, value)
    calls = clock.calls
    clock.ns += 10_000_000_000
    error("invalid_request", controller.started if kind == "start" else controller.complete, receipt=receipt)
    assert clock.calls == calls
    assert controller.status(id=start.id).detail == "worker_outcome_unknown"


def test_exact_receipt_types_and_keyword_only_operations(admission):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)

    class DerivedStart(StartReceipt):
        pass

    with pytest.raises(AdmissionError, match="invalid_request"):
        DerivedStart(**vars(start))
    derived = object.__new__(DerivedStart)
    for name, value in vars(start).items():
        object.__setattr__(derived, name, value)
    error("invalid_request", controller.started, receipt=derived)
    error("invalid_request", controller.started, receipt=vars(start))
    error("invalid_request", controller.complete, receipt=start)
    with pytest.raises(TypeError):
        controller.status(start.id)
    with pytest.raises(TypeError):
        controller.started(start)
    assert controller.snapshot().fault is None


@pytest.mark.parametrize("reason", ["worker_failed", "worker_outcome_unknown", "session_ended"])
def test_stop_preserves_first_reason_and_confirmed_fields(admission, reason):
    controller, clock = admission
    old = accepted(controller)
    old = controller.decode_failed(id=old.id)
    start = start_for(dispatched(controller), clock)
    controller.started(receipt=start)
    controller.reserve()
    result = controller.stop(reason=reason)
    assert (result.fault, result.stop_required, result.reservation) == (reason, True, None)
    rejected = controller.status(id=start.id)
    assert rejected.started_ns == start.started_ns
    assert rejected.detail == reason
    assert controller.status(id=old.id) == old
    calls = clock.calls
    clock.failure = OSError("must not sample again")
    assert controller.stop(reason="session_ended") == result
    assert controller.snapshot() == result
    assert controller.maintain() == result
    assert clock.calls == calls
    error("stopped", controller.decode_failed, id=old.id)


def test_detached_snapshots_and_restart_scope(admission):
    controller, clock = admission
    item = ready(controller)
    snapshot = controller.snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.pending.detail = "completed"
    permit = controller.dispatch(id=item.id, worker_session=WORKER)
    assert snapshot.pending.detail == "ready"
    assert snapshot.pending.revision == 3
    assert controller.snapshot().pending.detail == "dispatching"
    restarted = AdmissionController(OTHER, clock)
    error("not_found", restarted.status, id=item.id)
    error("not_found", restarted.started, receipt=start_for(permit, clock))
    assert restarted.snapshot().fault is None
    assert restarted.snapshot().incarnation == OTHER


def test_uuid_collision_never_replaces_retained_record(admission, monkeypatch):
    controller, _ = admission
    item = accepted(controller)
    terminal = controller.decode_failed(id=item.id)
    monkeypatch.setattr("market.image_admission.uuid4", lambda: item.id)
    error("capacity", controller.reserve)
    assert controller.status(id=item.id) == terminal
    assert controller.snapshot().reservation is None


def test_reservation_id_cannot_collide_with_retained_dispatch_id(admission, monkeypatch):
    controller, clock = admission
    permit = dispatched(controller)
    start = start_for(permit, clock)
    controller.started(receipt=start)
    processed = controller.complete(receipt=completion_for(start, clock))
    monkeypatch.setattr("market.image_admission.uuid4", lambda: permit.dispatch_id)
    error("capacity", controller.reserve)
    assert controller.status(id=permit.id) == processed
    assert controller.snapshot().reservation is None


def test_dispatch_id_collision_preserves_unbound_ready_work(admission, monkeypatch):
    controller, _ = admission
    item = ready(controller)
    monkeypatch.setattr("market.image_admission.uuid4", lambda: item.id)
    error("capacity", controller.dispatch, id=item.id, worker_session=WORKER)
    assert controller.status(id=item.id) == item
    assert controller.snapshot().fault is None


def test_reserved_slot_survives_active_completion_at_capacity(admission):
    controller, clock = admission
    for _ in range(510):
        controller.decode_failed(id=accepted(controller).id)
    start = start_for(dispatched(controller), clock)
    controller.started(receipt=start)
    reservation = controller.reserve()
    before = controller.snapshot()
    assert (before.terminal_count, before.reserved_receipt_slots) == (510, 2)
    processed = controller.complete(receipt=completion_for(start, clock))
    assert processed.status == "processed"
    after = controller.snapshot()
    assert (after.terminal_count, after.reserved_receipt_slots) == (511, 1)
    pending = controller.admit(id=reservation.id, source_sha256=SOURCE, encoded_bytes=2_097_152)
    controller.decode_failed(id=pending.id)
    assert controller.snapshot().terminal_count == 512
    error("capacity", controller.reserve)


def test_exact_reservation_headroom_and_due_maintenance_before_capacity():
    clock = MetadataClock(MAX_NS - 5_000_000_000)
    controller = AdmissionController(INCARNATION, clock)
    reservation = controller.reserve()
    assert reservation.expires_ns == MAX_NS
    clock.ns = MAX_NS
    error("capacity", controller.reserve)
    assert controller.snapshot().reservation is None
    assert controller.snapshot().fault is None


def test_timeout_precedes_successful_dispatch_retry(admission):
    controller, clock = admission
    permit = dispatched(controller)
    clock.ns += 10_000_000_000
    error("stopped", controller.dispatch, id=permit.id, worker_session=WORKER)
    result = controller.status(id=permit.id)
    assert result.detail == "worker_outcome_unknown"
    assert result.dispatch_id == permit.dispatch_id
    assert result.started_ns is None


def test_retention_is_measured_from_actual_maintenance_not_due_deadline(admission):
    controller, clock = admission
    item = accepted(controller)
    clock.ns = item.deadline_ns + 100_000_000_000
    terminal = controller.status(id=item.id)
    assert terminal.terminal_ns == 401_000_000_000
    clock.ns += 899_999_999_999
    assert controller.status(id=item.id) == terminal
    clock.ns += 1
    error("not_found", controller.status, id=item.id)


@pytest.mark.parametrize(("cls", "change"), [
    (Reservation, {"reserved_ns": True}),
    (Receipt, {"status": "invented"}), (Receipt, {"detail": "invented"}),
    (Receipt, {"status": StringSubclass("accepted")}), (Receipt, {"time_uncertain": 1}),
    (Receipt, {"revision": 0}), (Receipt, {"revision": 7}),
    (DispatchPermit, {"exposure_observations": True}),
])
def test_dto_constructors_reject_invalid_exact_primitives(admission, cls, change):
    controller, _ = admission
    reservation = controller.reserve()
    if cls is Reservation:
        dto = reservation
    else:
        item = controller.admit(id=reservation.id, source_sha256=SOURCE, encoded_bytes=17)
        if cls is Receipt:
            dto = item
        else:
            controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION)
            controller.moderate(id=item.id, action_id="a", approved=True)
            dto = controller.dispatch(id=item.id, worker_session=WORKER)
    with pytest.raises(AdmissionError, match="invalid_request"):
        replace(dto, **change)


def test_constructor_requires_canonical_exact_uuid():
    for value in (None, True, "bad", StringSubclass(INCARNATION), "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"):
        with pytest.raises(AdmissionError, match="invalid_request"):
            AdmissionController(value, MetadataClock())


@pytest.mark.parametrize("returned_by", ["admit", "decoded", "moderate", "status", "snapshot"])
def test_mutating_returned_pending_receipt_cannot_extend_controller_ttl(admission, returned_by):
    controller, clock = admission
    item = accepted(controller)
    if returned_by == "admit":
        returned = item
        vars(returned)["deadline_ns"] += 100_000_000_000
        assert controller.status(id=item.id).deadline_ns == 301_000_000_000
    decoded = controller.decoded(id=item.id, frame_sha256=FRAME, preprocessing_version=VERSION)
    if returned_by == "decoded":
        returned = decoded
        vars(returned)["deadline_ns"] += 100_000_000_000
        assert controller.status(id=item.id).deadline_ns == 301_000_000_000
    queued = controller.moderate(id=item.id, action_id="staff-1", approved=True)
    if returned_by == "moderate":
        returned = queued
    elif returned_by == "status":
        returned = controller.status(id=item.id)
    elif returned_by == "snapshot":
        returned = controller.snapshot().pending
    original_deadline = queued.deadline_ns
    vars(returned)["deadline_ns"] = original_deadline + 100_000_000_000
    assert controller.status(id=item.id).deadline_ns == 301_000_000_000
    clock.ns = original_deadline
    error("invalid_transition", controller.dispatch, id=item.id, worker_session=WORKER)
    result = controller.status(id=item.id)
    assert (result.status, result.detail, result.deadline_ns) == ("expired", "ttl_expired", 301_000_000_000)


@pytest.mark.parametrize("returned_by", ["reserve", "snapshot"])
def test_mutating_returned_reservation_cannot_delay_expiration(admission, returned_by):
    controller, clock = admission
    reservation = controller.reserve()
    original_id = reservation.id
    returned = reservation if returned_by == "reserve" else controller.snapshot().reservation
    vars(returned)["expires_ns"] = MAX_NS
    vars(returned)["id"] = OTHER
    assert controller.snapshot().reservation.id == original_id
    assert controller.snapshot().reservation.expires_ns == 6_000_000_000
    clock.ns = 6_000_000_000
    assert controller.maintain().reservation is None
    error("not_found", controller.admit, id=original_id, source_sha256=SOURCE, encoded_bytes=17)


@pytest.mark.parametrize("returned_by", ["first", "retry"])
def test_mutating_returned_dispatch_permit_cannot_rewrite_authorization(admission, returned_by):
    controller, clock = admission
    permit = dispatched(controller)
    original = replace(permit)
    returned = permit if returned_by == "first" else controller.dispatch(id=permit.id, worker_session=WORKER)
    vars(returned)["worker_session"] = OTHER
    vars(returned)["deadline_ns"] = MAX_NS
    vars(returned)["frame_sha256"] = SOURCE
    retry = controller.dispatch(id=original.id, worker_session=WORKER)
    assert retry == original
    result = controller.started(receipt=start_for(original, clock))
    assert (result.status, result.worker_session, result.frame_sha256) == ("processing", WORKER, FRAME)


@pytest.mark.parametrize("returned_by", ["started", "retry", "snapshot", "complete", "complete_retry", "status"])
def test_mutating_returned_active_or_terminal_receipt_cannot_rewrite_history(admission, returned_by):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    started = controller.started(receipt=start)
    if returned_by == "started":
        returned = started
    elif returned_by == "retry":
        returned = controller.started(receipt=start)
    elif returned_by == "snapshot":
        returned = controller.snapshot().active
    else:
        completion = completion_for(start, clock)
        returned = controller.complete(receipt=completion)
        if returned_by == "complete_retry":
            returned = controller.complete(receipt=completion)
        elif returned_by == "status":
            returned = controller.status(id=start.id)
    vars(returned)["started_ns"] = 0
    vars(returned)["first_observation_index"] = 100
    vars(returned)["status"] = "rejected"
    retained = controller.status(id=start.id)
    assert (retained.started_ns, retained.first_observation_index) == (1_000_000_000, 23)
    assert retained.status == ("processing" if returned_by in ("started", "retry", "snapshot") else "processed")
    assert controller.started(receipt=start) == retained


def test_mutating_caller_start_receipt_cannot_rewrite_successful_retry(admission):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    original = replace(start)
    controller.started(receipt=start)
    clock.ns += 1
    vars(start)["started_ns"] += 1
    # The original successful payload must remain retryable despite caller mutation.
    assert controller.started(receipt=original).detail == "processing"
    result = controller.started(receipt=start)
    assert (result.status, result.detail, result.started_ns) == ("rejected", "worker_outcome_unknown", 1_000_000_000)
    assert controller.snapshot().stop_required


def test_mutating_caller_completion_cannot_rewrite_terminal_retry_or_fault_new_work(admission):
    controller, clock = admission
    start = start_for(dispatched(controller), clock)
    controller.started(receipt=start)
    completion = completion_for(start, clock)
    original = replace(completion)
    processed = controller.complete(receipt=completion)
    next_item = ready(controller)
    clock.ns += 1
    vars(completion)["completed_ns"] += 1
    assert controller.complete(receipt=original) == processed
    error("idempotency_conflict", controller.complete, receipt=completion)
    assert controller.status(id=next_item.id) == next_item
    assert controller.snapshot().fault is None


def test_mutating_nonworker_retry_result_cannot_rewrite_later_retries(admission):
    controller, _ = admission
    item = ready(controller)
    retry = controller.admit(id=item.id, source_sha256=SOURCE, encoded_bytes=17)
    vars(retry)["source_sha256"] = FRAME
    vars(retry)["revision"] = 6
    current = controller.moderate(id=item.id, action_id="staff-1", approved=True)
    assert (current.source_sha256, current.revision, current.detail) == (SOURCE, 3, "ready")
