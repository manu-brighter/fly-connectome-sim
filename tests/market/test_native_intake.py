"""Real D1 integration with an explicitly synthetic, nonblocking session."""

from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from market.image_admission import AdmissionController
from market.image_intake import ImageIntake, IntakeError
from market.native_protocol import BLACK_SHA256, ReceiptEvidence
from market.native_session import Boundary, NativeNotice, NativeSnapshot, ReceiptProgress, ReceiptTicket

from test_image_intake import Clock, Decoder, FRAME, INC, RGB, settled, upload


WORKER = "00000000-0000-4000-8000-000000000003"
PROTOCOL = "a" * 64
GROUPS = dict(pam11=0, ppl101=0, kc=0, mbon07=0, mbon11=0, motor_left=0, motor_right=0)


class Session:
    """No neural model, process, disk writer or physical-time evidence."""

    def __init__(self, clock):
        self.clock = clock
        self.config = SimpleNamespace(protocol_sha256=PROTOCOL)
        self.state = "running"
        self.fault = None
        self.completed = 1
        self.issued = 1
        self.latest = self.measured(0)
        self.boundary = self.offer(1)
        self.notices = []
        self.seq = 0
        self.ticket = 0
        self.durable = 0
        self.auto_durable = True
        self.saturated = False
        self.finished = False
        self.batches = []
        self.advances = []
        self.stops = []
        self.validator = ReceiptEvidence()
        self.permit = None

    def measured(self, index, item_id=None):
        return dict(observation_index=index, input_kind="black" if item_id is None else "image",
                    image_id=item_id, frame_sha256=BLACK_SHA256 if item_id is None else FRAME,
                    wall_completion_ns=self.clock.ns, model_end_tick=(index + 1) * 5000,
                    group_spikes=dict(GROUPS), group_rates_hz=dict(GROUPS))

    def offer(self, index, active=None, remaining=0):
        return dict(id=index, next_observation_index=index, issued_observations=index,
                    completed_observations=index, active_dispatch_id=active,
                    unissued_active_observations=remaining, free_observations=40-index-remaining,
                    ack_deadline_ns=self.clock.ns + 5_000_000_000)

    def receipt_progress(self):
        return ReceiptProgress(dict(submitted_ticket=self.ticket, durable_ticket=self.durable,
                                    queued_batches=0, emergency_pending=False,
                                    closed=self.finished, fault=self.fault))

    def snapshot(self):
        remaining = self.boundary["unissued_active_observations"] if self.boundary else 0
        return NativeSnapshot(dict(schema="market-native-session/v1", incarnation=INC,
            worker_session=WORKER, state=self.state, fault=self.fault, cleanup_fault=None,
            issued_observations=self.issued, completed_observations=self.completed,
            in_flight_index=self.completed if self.issued > self.completed else None,
            active_dispatch_id=self.permit.dispatch_id if self.permit else None,
            unissued_active_observations=remaining,
            free_observations=40-self.issued-remaining, boundary=self.boundary,
            wall_deadline_ns=self.clock.ns + 900_000_000_000,
            startup_deadline_ns=None, observe_deadline_ns=None,
            receipt_progress=self.receipt_progress(), latest=self.latest,
            header_sha256="b" * 64, engine_identity_sha256="c" * 64))

    def reserve_receipts(self):
        if self.saturated or self.finished:
            return None
        self.ticket += 1
        return ReceiptTicket(self.ticket)

    def publish_receipts(self, ticket, entries):
        assert len(entries) <= (2 if ticket is None else 3)
        for entry in entries:
            self.validator.accept(asdict(entry["receipt"]))
        self.batches.append((ticket, entries))
        if ticket is not None and self.auto_durable:
            self.durable = ticket.ticket

    def finish_receipts(self):
        self.finished = True

    def poll(self):
        result, self.notices = tuple(self.notices[:8]), self.notices[8:]
        return result

    def notice(self, kind, payload):
        self.notices.append(NativeNotice(dict(notice_seq=self.seq, incarnation=INC,
            worker_session=WORKER, protocol_sha256=PROTOCOL, type=kind, payload=payload)))
        self.seq += 1

    def next_offer(self):
        return None if self.boundary is None else Boundary(self.boundary)

    def advance(self, boundary_id, permit, rgb):
        assert self.boundary is not None and boundary_id == self.boundary["id"]
        if permit is not None:
            assert any(ticket is not None and ticket.ticket <= self.durable
                       and entry["receipt"].dispatch_id == permit.dispatch_id
                       and entry["cause"]["operation"] == "dispatch"
                       for ticket, batch in self.batches for entry in batch)
        self.advances.append((boundary_id, permit, rgb))
        self.boundary = None
        self.issued += 1
        if permit is not None:
            self.permit = permit

    def begin_stop(self, reason):
        self.stops.append(reason)
        if self.state != "ended":
            self.state = "stopping"
        self.boundary = None

    def finish_close(self):
        return None

    def start_image(self):
        p = self.permit
        self.notice("start", dict(id=p.id, incarnation=INC, dispatch_id=p.dispatch_id,
            worker_session=WORKER, frame_sha256=FRAME, started_ns=self.clock.ns,
            first_observation_index=self.completed))

    def observation(self, index, *, image=True):
        self.issued = self.completed = index + 1
        self.latest = self.measured(index, self.permit.id if image else None)
        self.notice("observation", self.latest)

    def complete_image(self, first):
        p = self.permit
        self.notice("complete", dict(id=p.id, incarnation=INC, dispatch_id=p.dispatch_id,
            worker_session=WORKER, frame_sha256=FRAME, observation_indices=list(range(first, first+8)),
            completed_ns=self.clock.ns))
        self.permit = None


@pytest.fixture
def native():
    clock = Clock()
    admission, decoder, session = AdmissionController(INC, clock), Decoder(clock), Session(clock)
    intake = ImageIntake(admission, decoder, clock, native_session=session)
    yield intake, admission, decoder, clock, session
    decoder.release.set()
    intake.finish_close()


def ready(native):
    intake, admission, decoder, clock, session = native
    accepted = upload(intake, decoder)
    item_id = accepted["image"]["id"]
    settled(intake, decoder, item_id)
    intake.moderate(item_id, INC, "approve", True)
    return accepted


def test_v2_receipts_and_durable_dispatch(native):
    intake, _, _, _, session = native
    accepted = ready(native)
    assert accepted["schema"] == "market-image-acceptance/v2"
    session.auto_durable = False
    intake.maintain()
    current = intake.operator_status(accepted["image"]["id"])
    assert current["detail"] == "dispatching" and current["worker_session"] == WORKER
    assert not current["preview_available"] and current["completed_observations"] == 0
    assert not session.advances
    session.durable = session.ticket
    intake.maintain()
    assert session.advances[-1][2] == RGB
    assert [entry["receipt"].revision for _, entries in session.batches for entry in entries] == [1, 2, 3, 4]


def test_eight_measurements_and_terminal_watermark(native):
    intake, _, _, clock, session = native
    accepted = ready(native)
    item_id = accepted["image"]["id"]
    intake.maintain()
    session.start_image()
    intake.maintain()
    for index in range(1, 9):
        session.observation(index)
        intake.maintain()
        assert intake.operator_status(item_id)["status"] == "processing"
    session.complete_image(1)
    intake.maintain()
    terminal = intake.operator_status(item_id)
    assert terminal["status"] == "processed" and terminal["completed_observations"] == 8
    assert terminal["observation_revision"] == 9
    session.observation(9, image=False)
    clock.ns += 1_000_000
    intake.maintain()
    assert intake.operator_status(item_id)["observation_revision"] == 9
    measured = intake.native_state()
    assert measured["image_id"] is None and measured["observations_completed"] == 10
    assert measured["measurement_age_ms"] == 1


def test_budget_is_rechecked_at_admit(native):
    intake, _, _, _, session = native
    reservation = intake.reserve_upload(intake.guest_capability)
    session.completed = session.issued = 33
    session.latest, session.boundary = session.measured(32), session.offer(33)
    with pytest.raises(IntakeError) as caught:
        intake.accept_upload(reservation.id, "image/png", b"fixture")
    assert caught.value.code == "full"
    assert not any(entry["cause"]["operation"] == "admit" for _, batch in session.batches for entry in batch)


def test_stop_does_not_invent_completion_and_preserves_count(native):
    intake, _, _, _, session = native
    item_id = ready(native)["image"]["id"]
    intake.maintain()
    session.start_image()
    session.observation(1)
    intake.maintain()
    intake.begin_stop()
    status = intake.operator_status(item_id)
    assert status["status"] == "rejected" and status["detail"] == "session_ended"
    assert (status["completed_observations"], status["observation_revision"]) == (1, 2)
    assert session.finished


def test_outbox_full_uses_terminal_emergency(native):
    intake, _, _, _, session = native
    item_id = ready(native)["image"]["id"]
    session.saturated = True
    intake.maintain()
    assert intake.operator_status(item_id)["detail"] == "worker_failed"
    assert session.batches[-1][0] is None
    assert not session.advances


def test_clock_fault_retains_measurements_with_unknown_age(native):
    intake, _, _, clock, session = native
    clock.failure = RuntimeError("clock")
    intake.maintain()
    value = intake.native_state()
    assert value["fault"] == "clock" and value["time_uncertain"]
    assert value["measurement_age_ms"] is None and value["observations_completed"] == 1


def test_native_starting_does_not_accept(native):
    intake, _, _, _, session = native
    session.state = "starting"
    session.completed = session.issued = 0
    session.latest = session.boundary = None
    state = intake.operator_state()
    assert state["native_state"] == "starting" and state["health"] == "stopping"
    with pytest.raises(IntakeError):
        intake.reserve_upload(intake.guest_capability)


def active_and_pending(native):
    intake, admission, decoder, clock, session = native
    first = ready(native)
    intake.maintain()
    session.start_image()
    intake.maintain()
    clock.ns += 10_000_000_000
    second = upload(intake, decoder)
    second_id = second["image"]["id"]
    settled(intake, decoder, second_id)
    intake.moderate(second_id, INC, "approve-second", True)
    return first["image"]["id"], second_id


def test_pending_does_not_overwrite_active_pixels_or_capability(native):
    intake, _, _, clock, session = native
    first_id, second_id = active_and_pending(native)
    state = intake.operator_state()
    assert state["active"]["id"] == first_id and state["pending"]["id"] == second_id
    assert state["receipt_count"] == 2
    deadline = intake._receipts[second_id].deadline_ns
    for index in range(1, 9):
        session.observation(index)
    session.complete_image(1)
    intake.maintain()
    session.boundary = session.offer(9)
    intake.maintain()
    permit = session.advances[-1][1]
    assert permit.id == second_id and permit.deadline_ns == deadline
    assert intake.operator_status(first_id)["completed_observations"] == 8


def test_final_status_snapshot_expiry_is_captured_without_extra_read(native, monkeypatch):
    intake, admission, _, clock, session = native
    first_id, second_id = active_and_pending(native)
    for index in range(1, 9):
        session.observation(index)
    session.complete_image(1)
    intake.maintain()
    original_snapshot, original_status = admission.snapshot, admission.status
    calls = []
    def snapshot():
        calls.append("snapshot")
        clock.ns = intake._receipts[second_id].deadline_ns
        return original_snapshot()
    def status(**kwargs):
        calls.append(kwargs["id"])
        return original_status(**kwargs)
    monkeypatch.setattr(admission, "snapshot", snapshot)
    monkeypatch.setattr(admission, "status", status)
    # The public D1.status(A) result must be captured before snapshot expires B.
    with intake._lock:
        intake._d1("status", id=first_id)
    assert calls == [first_id, "snapshot", second_id, "snapshot"]
    assert intake.operator_status(second_id)["detail"] == "ttl_expired"
    assert intake.operator_status(first_id)["status"] == "processed"
    changes = session.batches
    assert any(entry["receipt"].id == second_id and entry["receipt"].detail == "ttl_expired"
               for _, entries in changes for entry in entries)


def test_terminal_read_clock_fault_fans_out_to_other_live_id(native, monkeypatch):
    intake, admission, _, clock, session = native
    first_id, second_id = active_and_pending(native)
    original_snapshot, original_status = admission.snapshot, admission.status
    calls = []
    def snapshot():
        calls.append("snapshot")
        if len(calls) == 1:
            clock.ns = intake._receipts[second_id].deadline_ns
        return original_snapshot()
    def status(**kwargs):
        calls.append(kwargs["id"])
        if kwargs["id"] == second_id:
            clock.failure = RuntimeError("clock failed while reading expired B")
        return original_status(**kwargs)
    monkeypatch.setattr(admission, "snapshot", snapshot)
    monkeypatch.setattr(admission, "status", status)
    with intake._lock:
        intake._d1("maintain")
    assert calls == ["snapshot", second_id, "snapshot", first_id, "snapshot"]
    assert intake.operator_status(first_id)["detail"] == "clock"
    assert intake.operator_status(second_id)["detail"] == "ttl_expired"
    entries = [entry for _, batch in session.batches for entry in batch]
    assert any(e["receipt"].id == first_id and e["receipt"].detail == "clock" for e in entries)


@pytest.mark.parametrize("failure", ["not_found", "live", "revision_gap"])
def test_unrecoverable_public_capture_fences_and_never_advances(native, monkeypatch, failure):
    intake, admission, _, clock, session = native
    first_id, second_id = active_and_pending(native)
    original_status = admission.status
    old = intake._receipts[second_id]
    clock.ns = old.deadline_ns
    def status(**kwargs):
        from market.image_admission import AdmissionError
        if kwargs["id"] == second_id:
            if failure == "not_found":
                raise AdmissionError("not_found")
            if failure == "live":
                return old
            return replace(original_status(**kwargs), revision=6)
        return original_status(**kwargs)
    monkeypatch.setattr(admission, "status", status)
    before = len(session.advances)
    with pytest.raises(IntakeError):
        intake.maintain()
    assert intake.native_state()["fault"] == "journal_gap"
    assert len(session.advances) == before


def test_multiple_moderation_transitions_are_journaled_without_poll(native):
    intake, _, _, _, session = native
    ready(native)
    changes = [e["cause"]["operation"] for _, entries in session.batches for e in entries]
    assert changes == ["admit", "decoded", "moderate"]


def test_global_native_read_bucket_freezes_after_clock_fault(native):
    intake, _, _, clock, _ = native
    for _ in range(120):
        intake.charge_native_read()
    with pytest.raises(IntakeError) as caught:
        intake.charge_native_read()
    assert caught.value.code == "rate_limited"
    clock.ns += 500_000_000
    intake.maintain()
    clock.failure = RuntimeError("clock")
    intake.charge_native_read()
    with pytest.raises(IntakeError) as caught:
        intake.charge_native_read()
    assert caught.value.code == "rate_limited"


def test_stop_drains_already_validated_observation_before_terminal_watermark(native):
    intake, _, _, _, session = native
    item_id = ready(native)["image"]["id"]
    intake.maintain()
    session.start_image()
    intake.maintain()
    session.observation(1)
    intake.begin_stop()
    value = intake.operator_status(item_id)
    assert value["status"] == "rejected" and value["completed_observations"] == 1


def test_normal_ended_health_retains_measurement_and_terminal_status(native):
    intake, _, _, _, session = native
    session.issued = session.completed = 40
    session.latest = session.measured(39)
    session.boundary = None
    session.state = "ended"
    session.notice("ended", dict(reason="model_limit", completed=40))
    intake.maintain()
    state = intake.operator_state()
    assert state["native_state"] == "ended" and state["health"] == "stopping"
    assert state["fault"] is None and state["pending"] is None and state["active"] is None
    measured = intake.native_state()
    assert measured["state"] == "ended" and measured["model_ms"] == 20000
    assert measured["fault"] is None

class LiveSession(Session):
    def __init__(self, clock, maximum=120):
        self.maximum = maximum
        super().__init__(clock)
        self.config = SimpleNamespace(protocol_sha256=PROTOCOL, profile="live-pilot/v1",
                                      duration_minutes=1, max_observations=maximum)

    def offer(self, index, active=None, remaining=0):
        value = super().offer(index, active, remaining)
        value["free_observations"] = self.maximum-index-remaining
        return value

    def snapshot(self):
        from market.native_protocol import NativeProfile, scope
        with scope(NativeProfile("live-pilot/v1", 1, self.maximum)):
            remaining = self.boundary["unissued_active_observations"] if self.boundary else 0
            return NativeSnapshot(dict(schema="market-native-session/v2", incarnation=INC,
                worker_session=WORKER, state=self.state, fault=self.fault, cleanup_fault=None,
                issued_observations=self.issued, completed_observations=self.completed,
                in_flight_index=self.completed if self.issued > self.completed else None,
                active_dispatch_id=self.permit.dispatch_id if self.permit else None,
                unissued_active_observations=remaining,
                free_observations=self.maximum-self.issued-remaining, boundary=self.boundary,
                wall_deadline_ns=self.clock.ns + 60_000_000_000,
                startup_deadline_ns=None, observe_deadline_ns=None,
                receipt_progress=self.receipt_progress(), latest=self.latest,
                header_sha256="b" * 64, engine_identity_sha256="c" * 64))

    def notice(self, kind, payload):
        from market.native_protocol import NativeProfile, scope
        with scope(NativeProfile("live-pilot/v1", 1, self.maximum)):
            super().notice(kind, payload)


@pytest.fixture
def live_native():
    clock = Clock()
    admission, decoder, session = AdmissionController(INC, clock), Decoder(clock), LiveSession(clock)
    session.completed = session.issued = 50
    session.latest, session.boundary = session.measured(49), session.offer(50)
    intake = ImageIntake(admission, decoder, clock, native_session=session)
    yield intake, admission, decoder, clock, session
    decoder.release.set()
    intake.finish_close()


def test_live_dispatch_after_forty_retains_real_d1_eight_interval_completion(live_native):
    intake, admission, _, _, session = live_native
    accepted = ready(live_native)
    assert accepted["schema"] == "market-image-acceptance/v3"
    assert accepted["image"]["schema"] == "market-image-status-wire/v3"
    item_id = accepted["image"]["id"]
    intake.maintain()
    assert session.advances[-1][1].id == item_id
    session.start_image()
    intake.maintain()
    for index in range(50, 58):
        session.observation(index)
        intake.maintain()
    session.complete_image(50)
    intake.maintain()
    value = intake.operator_status(item_id)
    assert value["status"] == "processed" and value["completed_observations"] == 8
    assert value["first_observation_index"] == 50 and value["observation_revision"] == 58
    assert admission.status(id=item_id).status == "processed"
    native = intake.native_state()
    assert native["schema"] == "market-native-state/v2" and native["profile"] == "live-pilot/v1"
    assert native["observations_completed"] == 58 and native["model_limit_ms"] == 60000
    assert intake.operator_state()["mode"] == "live-pilot"


def test_live_normal_wall_end_keeps_measured_prefix_and_no_fault(live_native):
    intake, _, _, _, session = live_native
    session.boundary, session.state = None, "ended"
    session.notice("ended", dict(reason="wall_limit", completed=50))
    intake.maintain()
    assert intake.native_state()["state"] == "ended" and intake.native_state()["fault"] is None
    assert intake.native_state()["observations_completed"] == 50
    assert intake.operator_state()["schema"] == "market-image-intake/v3"


def test_live_reserve_and_admit_keep_actual_remaining_capacity(live_native):
    intake, _, _, _, session = live_native
    reservation = intake.reserve_upload(intake.guest_capability)
    session.completed = session.issued = 113
    session.latest, session.boundary = session.measured(112), session.offer(113)
    with pytest.raises(IntakeError) as caught:
        intake.accept_upload(reservation.id, "image/png", b"fixture")
    assert caught.value.code == "full"

def test_live_wall_end_with_inflight_image_retains_partial_watermark(live_native):
    intake, admission, _, _, session = live_native
    item_id = ready(live_native)["image"]["id"]
    intake.maintain()
    session.start_image()
    for index in range(50, 53):
        session.observation(index)
    intake.maintain()
    session.issued = 54
    session.boundary, session.state = None, "ended"
    session.notice("ended", dict(reason="wall_limit", completed=53))
    intake.maintain()
    status = intake.operator_status(item_id)
    assert status["status"] == "rejected" and status["detail"] == "session_ended"
    assert status["completed_observations"] == 3 and status["observation_revision"] == 53
    assert admission.status(id=item_id).status == "rejected"
    value = intake.native_state()
    assert value["state"] == "ended" and value["fault"] is None
    assert value["observations_completed"] == 53


def test_native_frame_hides_pending_and_unobserved_approved_pixels(native):
    intake, _, decoder, _, session = native
    accepted = upload(intake, decoder)
    item_id = accepted["image"]["id"]
    settled(intake, decoder, item_id)
    assert intake.native_frame()["rgb_base64"] is None
    intake.moderate(item_id, INC, "frame-approve", True)
    assert intake.native_frame()["rgb_base64"] is None
    intake.maintain()
    session.start_image()
    intake.maintain()
    assert intake.native_frame()["rgb_base64"] is None
    assert intake.native_frame()["input_kind"] == "black"


def frame_started(native):
    intake, _, _, _, session = native
    item_id = ready(native)["image"]["id"]
    intake.maintain()
    session.start_image()
    session.observation(1)
    intake.maintain()
    return item_id


def test_native_frame_returns_exact_started_sanitized_rgb_and_detached_metadata(native):
    import base64
    intake, _, _, _, session = native
    item_id = frame_started(native)
    value = intake.native_frame()
    assert value == dict(schema="market-native-frame/v1", incarnation=INC, worker_session=WORKER,
        observations_completed=2, input_kind="image", image_id=item_id, frame_sha256=FRAME,
        rgb_base64=base64.b64encode(RGB).decode("ascii"))
    assert len(base64.b64decode(value["rgb_base64"], validate=True)) == 12288
    value["rgb_base64"] = "changed response"
    assert intake.native_frame()["rgb_base64"] != value["rgb_base64"]


@pytest.mark.parametrize("change", ["id", "hash", "dispatch", "black", "stale", "ended", "clock"])
def test_native_frame_never_reveals_mismatched_unavailable_or_stale_pixels(native, change):
    intake, _, _, clock, session = native
    frame_started(native)
    if change == "id":
        session.latest = {**session.latest, "image_id": "00000000-0000-4000-8000-000000000099"}
    elif change == "hash":
        session.latest = {**session.latest, "frame_sha256": "f" * 64}
    elif change == "dispatch":
        session.permit = replace(session.permit, dispatch_id="00000000-0000-4000-8000-000000000099")
    elif change == "black":
        session.latest = session.measured(1)
        session.permit = None
    elif change == "stale":
        clock.ns += 5_000_000_001
    elif change == "ended":
        session.state = "ended"
        session.issued = session.completed = 40
        session.latest = session.measured(39, session.permit.id)
        session.permit = session.boundary = None
    else:
        clock.failure = RuntimeError("clock")
    value = intake.native_frame()
    assert value["rgb_base64"] is None
    assert value["input_kind"] == ("black" if change == "black" else "image")
    if change in ("black", "ended", "clock"):
        assert intake._active_pixels is None


def test_native_frame_cache_clears_on_complete_before_black_and_never_changes_ttl(native):
    intake, _, _, _, session = native
    item_id = frame_started(native)
    deadline = intake._receipts[item_id].deadline_ns
    for index in range(2, 9):
        session.observation(index)
        intake.maintain()
    session.complete_image(1)
    intake.maintain()
    assert intake.native_frame()["rgb_base64"] is None
    assert intake._active_pixels is None
    assert intake._receipts[item_id].deadline_ns == deadline
    assert intake.operator_status(item_id)["completed_observations"] == 8


def test_native_frame_cache_stays_one_frame_and_cannot_show_queued_b(native):
    intake, _, decoder, clock, session = native
    first = frame_started(native)
    clock.ns += 10_000_000_000
    second = upload(intake, decoder)["image"]["id"]
    settled(intake, decoder, second)
    intake.moderate(second, INC, "second-frame", True)
    session.latest = {**session.latest, "wall_completion_ns": clock.ns}
    assert intake.native_frame()["image_id"] == first
    assert intake.native_frame()["rgb_base64"] is not None
    for index in range(2, 9):
        session.observation(index)
        intake.maintain()
    session.complete_image(1)
    intake.maintain()
    session.boundary = session.offer(9)
    intake.maintain()
    assert len(intake._active_pixels[-1]) == 12288
    value = intake.native_frame()
    assert value["image_id"] == first and value["rgb_base64"] is None
