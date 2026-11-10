"""Bounded coordinator behavior; safe synthetic pixels only, no neural worker."""

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import threading
import time
import zlib

import pytest

import market.image_intake as module
from market.image_intake import ImageIntake, IntakeError
from market.image_admission import AdmissionController
from market.image_decode import DecodeError, DecodedImage, ImageDecoder
from market.price_service import ClockSample, SystemClock


INC = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
PAYLOAD = b"generated image stand-in"
RGB = b"\xff\x00\x00" * 4096
PREFIX = b'{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n'
FRAME = hashlib.sha256(PREFIX + RGB).hexdigest()
ROOT = Path(__file__).resolve().parents[2]


class Clock:
    def __init__(self, ns=1_000_000_000):
        self.ns = ns
        self.failure = None

    def sample(self):
        if self.failure is not None:
            raise self.failure
        return ClockSample(self.ns, datetime(2026, 11, 10, tzinfo=timezone.utc))


class Decoder:
    """Replace only slow/OS D2 execution; D1 and coordinator remain real."""
    def __init__(self, clock):
        self.clock = clock
        self.entered = threading.Event()
        self.release = threading.Event()
        self.exited = threading.Event()
        self.failure = None
        self.change = None
        self.closed = False
        self.close_failure = False
        self.requests = []

    def decode(self, *, request, payload, cancel):
        self.requests.append((request, payload, cancel))
        self.entered.set()
        assert self.release.wait(10), "test did not release decoder"
        try:
            if self.failure is not None:
                raise self.failure
            result = DecodedImage(
                request.incarnation, request.id, request.source_sha256, FRAME,
                "market-rgb64/v1", RGB, 1, 1, 1, 1, "PNG", self.clock.ns, 100,
            )
            return result if self.change is None else self.change(result)
        finally:
            self.exited.set()

    def close(self):
        if self.close_failure:
            raise DecodeError("cleanup_failed")
        assert not self.entered.is_set() or self.exited.is_set()
        self.closed = True


@pytest.fixture
def setup():
    clock = Clock()
    admission = AdmissionController(INC, clock)
    decoder = Decoder(clock)
    intake = ImageIntake(admission, decoder, clock)
    yield intake, admission, decoder, clock
    decoder.release.set()
    intake.begin_stop()
    try:
        intake.finish_close()
    except IntakeError:
        pass


def error(code, operation, *args):
    with pytest.raises(IntakeError) as caught:
        operation(*args)
    assert caught.value.code == code
    assert str(caught.value) == code


def upload(intake, decoder, *, payload=PAYLOAD):
    reservation = intake.reserve_upload(intake.guest_capability)
    acceptance = intake.accept_upload(reservation.id, "image/png", payload)
    assert decoder.entered.wait(2)
    return acceptance


def settled(intake, decoder, item_id):
    decoder.release.set()
    assert decoder.exited.wait(2)
    # A thread join here is deliberately outside the coordinator lock. Polling
    # is bounded by real time only to await callback scheduling, not expiry.
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        state = intake.operator_state()
        if not state["decode_busy"]:
            return intake.operator_status(item_id)
        threading.Event().wait(0.001)
    pytest.fail("coordinator callback did not finish")


def test_upload_is_authenticated_before_state_and_bucket(setup):
    intake, admission, decoder, clock = setup
    for token in (None, "x", "is." + "a" * 43, "ig." + "a" * 44):
        error("unauthorized", intake.reserve_upload, token)
    assert admission.snapshot().reservation is None
    first = intake.reserve_upload(intake.guest_capability)
    assert first.incarnation == INC
    intake.abandon_upload(first.id)
    error("rate_limited", intake.reserve_upload, intake.guest_capability)
    clock.ns += 9_999_999_999
    error("rate_limited", intake.reserve_upload, intake.guest_capability)
    clock.ns += 1
    assert intake.reserve_upload(intake.guest_capability).id != first.id


def test_exact_acceptance_status_state_and_pixel_binding(setup):
    intake, admission, decoder, clock = setup
    assert re.fullmatch(r"ig\.[A-Za-z0-9_-]{43}", intake.guest_capability)
    accepted = upload(intake, decoder)
    assert set(accepted) == {"schema", "status_capability", "image"}
    assert accepted["schema"] == "market-image-acceptance/v1"
    assert re.fullmatch(r"is\.[A-Za-z0-9_-]{43}", accepted["status_capability"])
    image = accepted["image"]
    assert image == {
        "schema": "market-image-status-wire/v1", "incarnation": INC, "id": image["id"],
        "revision": 1, "status": "accepted", "detail": "decoding", "frame_sha256": None,
        "accepted_age_ms": 0, "remaining_decode_ms": 10000,
        "remaining_moderation_ms": 60000, "remaining_handoff_ms": 300000,
        "time_uncertain": False, "preview_available": False,
    }
    request, payload, _ = decoder.requests[0]
    assert (request.id, request.incarnation, request.source_sha256, request.encoded_bytes,
            request.accepted_ns, request.decode_deadline_ns, payload) == (
        image["id"], INC, hashlib.sha256(PAYLOAD).hexdigest(), len(PAYLOAD),
        clock.ns, clock.ns + 10_000_000_000, PAYLOAD,
    )
    current = settled(intake, decoder, image["id"])
    assert (current["revision"], current["detail"], current["frame_sha256"], current["preview_available"]) == (
        2, "awaiting_approval", FRAME, True,
    )
    assert intake.preview(image["id"], FRAME) == RGB
    error("not_found", intake.preview, image["id"], "a" * 64)
    state = intake.operator_state()
    assert state == {
        "schema": "market-image-intake/v1", "incarnation": INC, "mode": "local-intake-only",
        "worker_connected": False, "health": "ready", "fault": None, "receiving": False,
        "decode_busy": False, "pending": current, "receipt_count": 1,
    }
    current["detail"] = "tampered"
    state["pending"]["id"] = OTHER
    assert intake.guest_status(image["id"], accepted["status_capability"])["detail"] == "awaiting_approval"
    assert intake.operator_state()["pending"]["id"] == image["id"]
    assert len(json.dumps(accepted).encode()) < 8192


def test_original_reservation_deadline_and_old_abandon(setup):
    intake, admission, decoder, clock = setup
    old = intake.reserve_upload(intake.guest_capability)
    clock.ns = old.expires_ns
    error("not_found", intake.accept_upload, old.id, "image/png", PAYLOAD)
    clock.ns += 5_000_000_000
    current = intake.reserve_upload(intake.guest_capability)
    intake.abandon_upload(old.id)
    assert admission.snapshot().reservation.id == current.id
    clock.ns += 123_456_789
    accepted = intake.accept_upload(current.id, "image/png", PAYLOAD)
    assert accepted["image"]["accepted_age_ms"] == 0
    assert decoder.entered.wait(2)
    assert decoder.requests[0][0].accepted_ns == clock.ns


@pytest.mark.parametrize("approved,detail,status", [(False, "moderation_rejected", "rejected"), (True, "ready", "queued")])
def test_moderation_is_d1_idempotent_and_never_dispatches(setup, approved, detail, status):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id = accepted["image"]["id"]
    settled(intake, decoder, item_id)
    error("wrong_incarnation", intake.moderate, item_id, OTHER, "staff", approved)
    current = intake.moderate(item_id, INC, "staff", approved)
    assert (current["status"], current["detail"], current["revision"]) == (status, detail, 3)
    assert intake.moderate(item_id, INC, "staff", approved) == current
    error("idempotency_conflict", intake.moderate, item_id, INC, "staff", not approved)
    assert admission.snapshot().active is None
    if approved:
        clock.ns += 300_000_000_000
        current = intake.operator_status(item_id)
        assert (current["status"], current["detail"]) == ("expired", "ttl_expired")
    assert not intake.operator_status(item_id)["preview_available"]
    error("not_found", intake.preview, item_id, FRAME)


@pytest.mark.parametrize("elapsed,detail", [(10_000_000_000, "decode_timeout"), (60_000_000_000, "decode_timeout")])
def test_late_callback_is_discarded_and_busy_survives_d1_expiry(setup, elapsed, detail):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id = accepted["image"]["id"]
    clock.ns += elapsed
    intake.maintain()
    assert intake.operator_status(item_id)["detail"] == detail
    error("busy", intake.reserve_upload, intake.guest_capability)
    current = settled(intake, decoder, item_id)
    assert current["detail"] == detail
    assert not current["preview_available"]
    assert intake.operator_state()["health"] == "ready"


def test_moderation_equality_and_remaining_rounding(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id = accepted["image"]["id"]
    settled(intake, decoder, item_id)
    clock.ns += 1_000_001
    current = intake.operator_status(item_id)
    assert (current["accepted_age_ms"], current["remaining_decode_ms"], current["remaining_moderation_ms"],
            current["remaining_handoff_ms"]) == (1, 9999, 59999, 299999)
    clock.ns = 61_000_000_000
    error("invalid_transition", intake.moderate, item_id, INC, "late", True)
    current = intake.operator_status(item_id)
    assert current["detail"] == "moderation_timeout"
    assert [current[key] for key in ("remaining_decode_ms", "remaining_moderation_ms", "remaining_handoff_ms")] == [0, 0, 0]


@pytest.mark.parametrize("code", ["malformed_image", "unsupported_format", "geometry", "mode", "multiple_frames", "source_mismatch", "memory_limit", "child_failed", "monitor_stalled"])
def test_expected_decode_failure_rejects_without_fencing(setup, code):
    intake, admission, decoder, clock = setup
    decoder.failure = DecodeError(code)
    accepted = upload(intake, decoder)
    current = settled(intake, decoder, accepted["image"]["id"])
    assert current["detail"] == "decode_failed"
    assert intake.operator_state()["health"] == "ready"


@pytest.mark.parametrize("code,fault", [
    ("closed", "decoder"), ("busy", "decoder"), ("invalid_request", "decoder"),
    ("unsupported_platform", "decoder"), ("child_protocol", "decoder"),
    ("cancelled", "decoder"), ("timeout", "decoder"), ("ownership", "ownership"),
    ("cleanup_failed", "ownership"), ("clock", "clock"),
])
def test_integration_errors_fence_without_manufactured_d1_clock(setup, code, fault):
    intake, admission, decoder, clock = setup
    decoder.failure = DecodeError(code)
    accepted = upload(intake, decoder)
    current = settled(intake, decoder, accepted["image"]["id"])
    state = intake.operator_state()
    assert (state["health"], state["fault"], state["pending"]) == ("faulted", fault, None)
    assert current["detail"] == "worker_failed"
    assert admission.snapshot().fault == "worker_failed"
    assert current["time_uncertain"] == (fault == "clock")
    error("intake_fault", intake.reserve_upload, intake.guest_capability)


def test_elapsed_timeout_is_d1_timeout_not_decoder_fault(setup):
    intake, admission, decoder, clock = setup
    decoder.failure = DecodeError("timeout")
    accepted = upload(intake, decoder)
    clock.ns += 10_000_000_000
    current = settled(intake, decoder, accepted["image"]["id"])
    assert current["detail"] == "decode_timeout"
    assert intake.operator_state()["health"] == "ready"


def test_status_authentication_and_global_buckets_are_atomic(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id, token = accepted["image"]["id"], accepted["status_capability"]
    for _ in range(125):
        error("unauthorized", intake.guest_status, item_id, "is." + "x" * 43)
    for _ in range(120):
        assert intake.guest_status(item_id, token)["id"] == item_id
        intake.charge_operator(True)
        assert intake.operator_status(item_id)["id"] == item_id
        intake.operator_state()  # uncharged downstream operations
    error("rate_limited", intake.guest_status, item_id, token)
    error("rate_limited", intake.charge_operator, True)
    clock.ns += 499_999_999
    error("rate_limited", intake.guest_status, item_id, token)
    clock.ns += 1
    intake.guest_status(item_id, token)
    intake.charge_operator(False)
    error("rate_limited", intake.charge_operator, False)


def test_clock_fault_freezes_finite_diagnostic_credits(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id, token = accepted["image"]["id"], accepted["status_capability"]
    intake.guest_status(item_id, token)
    intake.charge_operator(True)
    clock.failure = RuntimeError("secret clock details")
    intake.maintain()
    current = intake.operator_status(item_id)
    assert current["detail"] == "clock"
    assert current["time_uncertain"] is True
    assert all(current[key] is None for key in ("accepted_age_ms", "remaining_decode_ms", "remaining_moderation_ms", "remaining_handoff_ms"))
    for _ in range(119):
        intake.guest_status(item_id, token)
        intake.charge_operator(True)
    clock.failure = None
    clock.ns += 10_000_000_000_000
    error("rate_limited", intake.guest_status, item_id, token)
    error("rate_limited", intake.charge_operator, True)
    error("intake_fault", intake.charge_operator, False)
    error("intake_fault", intake.preview, item_id, FRAME)


def test_receipt_pruning_revokes_token_and_never_charges_failed_auth(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id, token = accepted["image"]["id"], accepted["status_capability"]
    settled(intake, decoder, item_id)
    intake.moderate(item_id, INC, "reject", False)
    clock.ns += 900_000_000_000
    for _ in range(121):
        error("unauthorized", intake.guest_status, item_id, token)
    error("not_found", intake.operator_status, item_id)
    assert intake.operator_state()["receipt_count"] == 0


def test_capability_mint_collisions_are_bounded_and_release_reservation(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda size: "a" * 43)
    first = upload(intake, decoder)
    item_id = first["image"]["id"]
    settled(intake, decoder, item_id)
    intake.moderate(item_id, INC, "reject", False)
    clock.ns += 10_000_000_000
    reservation = intake.reserve_upload(intake.guest_capability)
    calls = []
    def collide(size):
        calls.append(size)
        return "a" * 43
    monkeypatch.setattr(module.secrets, "token_urlsafe", collide)
    error("capacity", intake.accept_upload, reservation.id, "image/png", PAYLOAD)
    assert calls == [32, 32, 32, 32]
    assert admission.snapshot().reservation is None
    assert intake.operator_state()["receipt_count"] == 1


def test_guest_and_status_roles_keep_full_random_suffix_and_disjoint_price_shape(monkeypatch):
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda size: "a" * 43)
    clock = Clock()
    decoder = Decoder(clock)
    intake = ImageIntake(AdmissionController(INC, clock), decoder, clock)
    try:
        assert intake.guest_capability == "ig." + "a" * 43
        accepted = upload(intake, decoder)
        assert accepted["status_capability"] == "is." + "a" * 43
        for price_or_future_primary in ("a" * 43, accepted["status_capability"]):
            error("unauthorized", intake.reserve_upload, price_or_future_primary)
        error("unauthorized", intake.guest_status, accepted["image"]["id"], intake.guest_capability)
    finally:
        decoder.release.set()
        intake.begin_stop()
        intake.finish_close()


def test_generator_failure_has_no_admitted_receipt(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    reservation = intake.reserve_upload(intake.guest_capability)
    def broken(size):
        raise RuntimeError("do not expose me")
    monkeypatch.setattr(module.secrets, "token_urlsafe", broken)
    error("capacity", intake.accept_upload, reservation.id, "image/png", PAYLOAD)
    assert intake.operator_state()["receipt_count"] == 0
    assert admission.snapshot().reservation is None
    with pytest.raises(IntakeError, match="^capacity$"):
        ImageIntake(AdmissionController(OTHER, clock), Decoder(clock), clock)


def test_stop_during_decode_revokes_callback_and_closed_precedes_auth(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id = accepted["image"]["id"]
    intake.begin_stop()
    assert decoder.requests[0][2].is_set()
    assert intake.operator_status(item_id)["detail"] == "session_ended"
    assert intake.operator_state()["health"] == "stopping"
    error("stopping", intake.reserve_upload, intake.guest_capability)
    settled(intake, decoder, item_id)
    intake.finish_close()
    assert decoder.closed
    clock.failure = RuntimeError("closed must not read clock")
    for operation, args in (
        (intake.reserve_upload, (None,)), (intake.guest_status, (None, None)),
        (intake.charge_operator, (False,)), (intake.operator_state, ()),
        (intake.operator_status, (None,)), (intake.preview, (None, None)),
        (intake.moderate, (None, None, None, None)), (intake.maintain, ()),
        (intake.abandon_upload, (None,)), (intake.accept_upload, (None, None, None)),
    ):
        error("closed", operation, *args)
    intake.begin_stop()
    intake.finish_close()


def test_thread_start_failure_returns_real_terminal_acceptance(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    def fail_start(thread):
        raise RuntimeError("thread unavailable")
    monkeypatch.setattr(module.threading.Thread, "start", fail_start)
    reservation = intake.reserve_upload(intake.guest_capability)
    accepted = intake.accept_upload(reservation.id, "image/png", PAYLOAD)
    assert accepted["image"]["detail"] == "worker_failed"
    assert intake.guest_status(reservation.id, accepted["status_capability"])["detail"] == "worker_failed"
    assert intake.operator_state()["fault"] == "decoder"
    assert not decoder.entered.is_set()


def test_cleanup_failure_retains_context_and_does_not_claim_closed(setup):
    intake, admission, decoder, clock = setup
    decoder.close_failure = True
    intake.begin_stop()
    error("cleanup_failed", intake.finish_close)
    assert intake.operator_state()["fault"] == "shutdown"
    assert not decoder.closed
    error("stopping", intake.reserve_upload, intake.guest_capability)
    decoder.close_failure = False
    intake.finish_close()
    assert decoder.closed


@pytest.mark.skipif(sys.platform != "win32", reason="actual D2 Windows Job ownership required")
def test_actual_owned_generated_png_through_coordinator(tmp_path):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    payload = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(b"\0\xff\0\0")) + chunk(b"IEND", b""))
    work_root = ROOT / ".tools/image-intake-20261110" / f"task1-owned-{tmp_path.parent.name}-{tmp_path.name}"
    work_root.mkdir(parents=True)
    clock = SystemClock()
    decoder = ImageDecoder(work_root, clock)
    intake = ImageIntake(AdmissionController(INC, clock), decoder, clock)
    try:
        reservation = intake.reserve_upload(intake.guest_capability)
        accepted = intake.accept_upload(reservation.id, "image/png", payload)
        deadline = time.monotonic() + 12
        while intake.operator_state()["decode_busy"] and time.monotonic() < deadline:
            threading.Event().wait(0.01)
        current = intake.guest_status(reservation.id, accepted["status_capability"])
        assert (current["detail"], current["frame_sha256"]) == ("awaiting_approval", FRAME)
        assert intake.preview(reservation.id, FRAME) == RGB
        assert not (work_root / "job").exists()
        assert intake.moderate(reservation.id, INC, "actual-safe", True)["status"] == "queued"
        (work_root / "task1-fixture-evidence.json").write_text(json.dumps({
            "source_sha256": hashlib.sha256(payload).hexdigest(), "encoded_bytes": len(payload),
            "frame_sha256": FRAME, "rgb_bytes": len(RGB), "scratch_removed": True,
            "image": current,
        }), encoding="utf-8")
    finally:
        intake.begin_stop()
        intake.finish_close()
    # Exact owner was released by successful finish_close, not daemon exit.
    again = ImageDecoder(work_root, clock)
    again.close()


def test_valid_clock_samples_refill_before_fault_freezes_balances(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id, token = accepted["image"]["id"], accepted["status_capability"]
    for _ in range(120):
        intake.guest_status(item_id, token)
        intake.charge_operator(True)
    clock.ns += 500_000_000
    intake.maintain()  # this valid shared sample earns one token in each bucket
    clock.failure = ValueError("clock failed after earned refill")
    intake.maintain()
    intake.guest_status(item_id, token)
    intake.charge_operator(True)
    error("rate_limited", intake.guest_status, item_id, token)
    error("rate_limited", intake.charge_operator, True)


def test_thread_construction_failure_still_returns_allocated_terminal_receipt(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    def unavailable(*args, **kwargs):
        raise RuntimeError("thread constructor unavailable")
    monkeypatch.setattr(module.threading, "Thread", unavailable)
    reservation = intake.reserve_upload(intake.guest_capability)
    accepted = intake.accept_upload(reservation.id, "image/png", PAYLOAD)
    assert accepted["image"]["detail"] == "worker_failed"
    assert intake.guest_status(reservation.id, accepted["status_capability"])["detail"] == "worker_failed"
    assert intake.operator_state()["fault"] == "decoder"


def test_live_task_join_timeout_keeps_decoder_and_allows_later_cleanup(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    original = threading.Thread.join
    waits = []
    def timed_out(thread, timeout=None):
        waits.append(timeout)
    monkeypatch.setattr(threading.Thread, "join", timed_out)
    error("cleanup_failed", intake.finish_close)
    assert waits == [25]
    assert not decoder.closed
    assert intake.operator_state()["decode_busy"] is True
    assert intake.operator_status(accepted["image"]["id"])["detail"] == "session_ended"
    monkeypatch.setattr(threading.Thread, "join", original)
    decoder.release.set()
    intake.finish_close()
    assert decoder.closed


@pytest.mark.parametrize("changes", [
    {"id": OTHER}, {"incarnation": OTHER}, {"source_sha256": "a" * 64},
    {"rgb": RGB[:-1]}, {"frame_sha256": "a" * 64},
])
def test_untrusted_decoder_result_identity_and_pixels_cannot_publish(setup, changes):
    intake, admission, decoder, clock = setup
    def changed(result):
        # Emulate a faulty collaborator bypassing frozen-dataclass construction.
        for key, value in changes.items():
            object.__setattr__(result, key, value)
        return result
    decoder.change = changed
    accepted = upload(intake, decoder)
    current = settled(intake, decoder, accepted["image"]["id"])
    assert current["detail"] == "worker_failed"
    assert current["frame_sha256"] is None
    assert intake.operator_state()["fault"] == "decoder"
    error("intake_fault", intake.preview, accepted["image"]["id"], FRAME)


@pytest.mark.parametrize("media,payload", [
    ("image/png; charset=utf-8", PAYLOAD), ("image/jpg", PAYLOAD),
    ("image/png", b""), ("image/png", b"x" * 2_097_153),
    ("image/png", bytearray(PAYLOAD)), (None, PAYLOAD),
], ids=["mime-parameter", "mime-alias", "empty", "oversize", "mutable", "null-mime"])
def test_bad_upload_metadata_releases_only_own_reservation(setup, media, payload):
    intake, admission, decoder, clock = setup
    reservation = intake.reserve_upload(intake.guest_capability)
    error("invalid_request", intake.accept_upload, reservation.id, media, payload)
    assert admission.snapshot().reservation is None
    assert intake.operator_state()["receipt_count"] == 0


def test_old_invalid_upload_cannot_cancel_new_reservation(setup):
    intake, admission, decoder, clock = setup
    old = intake.reserve_upload(intake.guest_capability)
    clock.ns += 10_000_000_000
    current = intake.reserve_upload(intake.guest_capability)
    error("invalid_request", intake.accept_upload, old.id, "image/gif", PAYLOAD)
    assert admission.snapshot().reservation.id == current.id


def test_clock_regression_fences_without_utc_fallback(setup):
    intake, admission, decoder, clock = setup
    clock.ns -= 1
    intake.maintain()
    state = intake.operator_state()
    assert (state["health"], state["fault"]) == ("faulted", "clock")
    assert admission.snapshot().fault == "clock"


def test_original_headroom_failure_releases_reservation(setup):
    intake, admission, decoder, clock = setup
    clock.ns = 2 ** 63 - 1 - 6_000_000_000
    reservation = intake.reserve_upload(intake.guest_capability)
    error("capacity", intake.accept_upload, reservation.id, "image/png", PAYLOAD)
    assert admission.snapshot().reservation is None
    assert intake.operator_state()["receipt_count"] == 0


def test_rejected_lost_acceptance_remains_authenticated_receipt(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    # Losing transport's 202 does not undo admission or introduce a retry API.
    item_id = accepted["image"]["id"]
    assert intake.operator_status(item_id)["detail"] == "decoding"
    error("not_found", intake.accept_upload, item_id, "image/png", PAYLOAD)
    assert intake.guest_status(item_id, accepted["status_capability"])["detail"] == "decoding"
    assert intake.operator_state()["receipt_count"] == 1


def test_512_retained_capability_boundary_with_public_d1_pressure_seam(setup):
    intake, admission, decoder, clock = setup
    decoder.release.set()
    retained = []
    # Deliberately bypass only the 1/10s upload gate through real public D1.reserve.
    # Natural upload pacing/retention cannot reach 512. This pressure seam tests
    # the structural retention ceiling, not operational guest/event capacity.
    for _ in range(512):
        reservation = admission.reserve()
        accepted = intake.accept_upload(reservation.id, "image/png", PAYLOAD)
        settled(intake, decoder, reservation.id)
        intake.moderate(reservation.id, INC, "reject", False)
        retained.append((reservation.id, accepted["status_capability"]))
    assert intake.operator_state()["receipt_count"] == 512
    error("capacity", intake.reserve_upload, intake.guest_capability)
    for item_id, token in (retained[0], retained[-1]):
        assert intake.guest_status(item_id, token)["detail"] == "moderation_rejected"
    clock.ns += 900_000_000_000
    intake.maintain()
    assert intake.operator_state()["receipt_count"] == 0
    for item_id, token in (retained[0], retained[-1]):
        error("unauthorized", intake.guest_status, item_id, token)
    assert intake.reserve_upload(intake.guest_capability).incarnation == INC


def test_callback_rechecks_d1_deadline_at_decoded_call(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    entering = threading.Event()
    resume = threading.Event()
    original = admission.decoded
    def delayed(**kwargs):
        entering.set()
        assert resume.wait(2)
        return original(**kwargs)
    monkeypatch.setattr(admission, "decoded", delayed)
    accepted = upload(intake, decoder)
    decoder.release.set()
    assert entering.wait(2)
    clock.ns += 10_000_000_000
    resume.set()
    current = settled(intake, decoder, accepted["image"]["id"])
    assert current["detail"] == "decode_timeout"
    assert current["frame_sha256"] is None
    assert not current["preview_available"]
    assert intake.operator_state()["health"] == "ready"


def test_moderation_before_callback_cannot_approve_unpublished_pixels(setup):
    intake, admission, decoder, clock = setup
    accepted = upload(intake, decoder)
    item_id = accepted["image"]["id"]
    error("invalid_transition", intake.moderate, item_id, INC, "before", True)
    assert intake.operator_status(item_id)["detail"] == "decoding"
    settled(intake, decoder, item_id)
    assert intake.moderate(item_id, INC, "after", True)["status"] == "queued"
    assert intake.preview(item_id, FRAME) == RGB


def test_fourth_status_mint_attempt_can_succeed(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda size: "a" * 43)
    first = upload(intake, decoder)
    settled(intake, decoder, first["image"]["id"])
    intake.moderate(first["image"]["id"], INC, "reject", False)
    clock.ns += 10_000_000_000
    candidates = iter(["a" * 43, "a" * 43, "a" * 43, "b" * 43])
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda size: next(candidates))
    second = upload(intake, decoder)
    assert second["status_capability"] == "is." + "b" * 43
    assert intake.operator_state()["receipt_count"] == 2


@pytest.mark.parametrize("suffix", [None, b"a" * 43, "a" * 42, "a" * 44, "." * 43])
def test_guest_capability_invalid_generator_output_refuses_startup(suffix, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda size: suffix)
    with pytest.raises(IntakeError, match="^capacity$"):
        ImageIntake(AdmissionController(INC, clock), Decoder(clock), clock)


def test_nonclock_fault_diagnostics_refill_only_from_valid_shared_samples(setup):
    intake, admission, decoder, clock = setup
    decoder.failure = DecodeError("child_protocol")
    accepted = upload(intake, decoder)
    item_id, token = accepted["image"]["id"], accepted["status_capability"]
    settled(intake, decoder, item_id)
    for _ in range(120):
        intake.guest_status(item_id, token)
        intake.charge_operator(True)
    error("rate_limited", intake.guest_status, item_id, token)
    clock.ns += 500_000_000
    intake.guest_status(item_id, token)
    intake.charge_operator(True)
    error("intake_fault", intake.charge_operator, False)
    error("rate_limited", intake.charge_operator, True)


def test_partial_thread_start_failure_retains_live_task_for_shutdown(setup, monkeypatch):
    intake, admission, decoder, clock = setup
    original = threading.Thread.start
    def started_then_failed(thread):
        original(thread)
        assert decoder.entered.wait(2)
        raise RuntimeError("startup acknowledgement failed")
    monkeypatch.setattr(threading.Thread, "start", started_then_failed)
    reservation = intake.reserve_upload(intake.guest_capability)
    accepted = intake.accept_upload(reservation.id, "image/png", PAYLOAD)
    assert accepted["image"]["detail"] == "worker_failed"
    assert intake.operator_state()["decode_busy"] is True
    decoder.release.set()
    intake.finish_close()
    assert decoder.exited.is_set() and decoder.closed


def test_future_primary_with_identical_random_suffix_stays_disjoint(setup, authority, monkeypatch):
    intake, admission, decoder, clock = setup
    monkeypatch.setattr(module.secrets, "token_urlsafe", lambda size: "a" * 43)
    accepted = upload(intake, decoder)
    # Price authority is a disposable existing fixture. Claim happens AFTER image
    # receipt mint, so a construction-time exclusion set could not protect it.
    claim = authority.claim_primary(authority.snapshot().incarnation, "future-primary")
    assert claim.primary_token == "a" * 43
    assert accepted["status_capability"] == "is." + claim.primary_token
    assert authority.resolve_primary_token(accepted["status_capability"]) is None
    assert authority.resolve_primary_token(intake.guest_capability) is None
    error("unauthorized", intake.reserve_upload, claim.primary_token)
    error("unauthorized", intake.guest_status, accepted["image"]["id"], claim.primary_token)


def test_actual_owner_retained_after_unconfirmed_close(tmp_path, monkeypatch):
    work_root = ROOT / ".tools/image-intake-20261110" / f"task1-owner-{tmp_path.parent.name}-{tmp_path.name}"
    work_root.mkdir(parents=True)
    clock = SystemClock()
    decoder = ImageDecoder(work_root, clock)
    intake = ImageIntake(AdmissionController(INC, clock), decoder, clock)
    original = decoder.close
    def unconfirmed():
        raise DecodeError("cleanup_failed")
    monkeypatch.setattr(decoder, "close", unconfirmed)
    try:
        error("cleanup_failed", intake.finish_close)
        with pytest.raises(DecodeError, match="^ownership$"):
            ImageDecoder(work_root, clock)
        assert intake.operator_state()["fault"] == "shutdown"
    finally:
        monkeypatch.setattr(decoder, "close", original)
        intake.finish_close()
    replacement = ImageDecoder(work_root, clock)
    replacement.close()


class BoundaryClock(Clock):
    """Advance/fail at a specific real shared-clock sample, including D1 reads."""
    def arm(self, countdown, *, next_ns=None, fail=False):
        self.countdown = countdown
        self.next_ns = next_ns
        self.fail = fail

    def arm_steps(self, steps):
        self.steps = steps
        self.sample_index = 0

    def sample(self):
        if hasattr(self, "steps"):
            self.sample_index += 1
            if self.sample_index in self.steps:
                self.ns = self.steps[self.sample_index]
        if getattr(self, "countdown", 0):
            self.countdown -= 1
            if self.countdown == 0:
                if self.fail:
                    self.failure = ValueError("controlled final-read clock fault")
                else:
                    self.ns = self.next_ns
        return super().sample()


@pytest.fixture
def boundary_setup():
    clock = BoundaryClock()
    admission = AdmissionController(INC, clock)
    decoder = Decoder(clock)
    intake = ImageIntake(admission, decoder, clock)
    accepted = upload(intake, decoder)
    settled(intake, decoder, accepted["image"]["id"])
    yield intake, admission, decoder, clock, accepted
    decoder.release.set()
    intake.finish_close()


@pytest.mark.parametrize("operation", ["operator_status", "guest_status", "operator_state"])
@pytest.mark.parametrize("approved,deadline,detail", [
    (False, 61_000_000_000, "moderation_timeout"),
    (True, 301_000_000_000, "ttl_expired"),
])
@pytest.mark.parametrize("crossing_sample", [5, 6, 7])
def test_final_read_and_reconciliation_snapshot_cross_original_deadline(
    boundary_setup, operation, approved, deadline, detail, crossing_sample,
):
    intake, admission, decoder, clock, accepted = boundary_setup
    item_id = accepted["image"]["id"]
    if approved:
        intake.moderate(item_id, INC, "queue", True)
    clock.ns = deadline - 1
    # The first four samples belong to existing maintenance/reconciliation.
    # Five is the target status read; six is its following public D1 snapshot.
    clock.arm(crossing_sample, next_ns=deadline)
    if operation == "operator_status":
        image = intake.operator_status(item_id)
    elif operation == "guest_status":
        image = intake.guest_status(item_id, accepted["status_capability"])
    else:
        assert intake.operator_state()["pending"] is None
        image = intake.operator_status(item_id)
    assert image["detail"] == detail
    assert image["preview_available"] is False
    assert image["accepted_age_ms"] == (60000 if not approved else 300000)
    assert [image[key] for key in ("remaining_decode_ms", "remaining_moderation_ms", "remaining_handoff_ms")] == [0, 0, 0]
    error("not_found", intake.preview, item_id, FRAME)


@pytest.mark.parametrize("crossing_sample", [6, 7])
def test_final_guest_retention_prune_revokes_only_target_without_spending_credit(boundary_setup, crossing_sample):
    intake, admission, decoder, clock, accepted = boundary_setup
    item_id = accepted["image"]["id"]
    intake.moderate(item_id, INC, "first-reject", False)
    clock.ns += 10_000_000_000
    second = upload(intake, decoder)
    second_id, second_token = second["image"]["id"], second["status_capability"]
    settled(intake, decoder, second_id)
    intake.moderate(second_id, INC, "second-reject", False)
    clock.ns = 901_000_000_000 - 1
    # Two retained IDs add one sample to the reconciliation pass.
    clock.arm(crossing_sample, next_ns=901_000_000_000)
    error("unauthorized", intake.guest_status, item_id, accepted["status_capability"])
    assert intake.operator_state()["receipt_count"] == 1
    for _ in range(120):
        assert intake.guest_status(second_id, second_token)["id"] == second_id
    error("rate_limited", intake.guest_status, second_id, second_token)
    error("not_found", intake.operator_status, item_id)


@pytest.mark.parametrize("operation", ["operator_status", "guest_status"])
@pytest.mark.parametrize("crossing_sample", [5, 6])
def test_terminal_receipt_final_read_and_snapshot_clock_fault_null_all_times(boundary_setup, operation, crossing_sample):
    intake, admission, decoder, clock, accepted = boundary_setup
    item_id = accepted["image"]["id"]
    intake.moderate(item_id, INC, "reject-before-fault", False)
    clock.arm(crossing_sample, fail=True)
    image = (intake.operator_status(item_id) if operation == "operator_status"
             else intake.guest_status(item_id, accepted["status_capability"]))
    assert image["detail"] == "moderation_rejected"
    assert image["time_uncertain"] is True
    assert all(image[key] is None for key in (
        "accepted_age_ms", "remaining_decode_ms", "remaining_moderation_ms", "remaining_handoff_ms",
    ))
    assert admission.snapshot().fault == "clock"
    assert intake.operator_state()["fault"] == "clock"


@pytest.mark.parametrize("operation", ["operator_status", "guest_status", "operator_state"])
def test_bounded_target_reads_resolve_both_terminal_and_retention_transition(boundary_setup, operation):
    intake, admission, decoder, clock, accepted = boundary_setup
    item_id = accepted["image"]["id"]
    clock.ns = 61_000_000_000 - 1
    # Four maintenance samples, then each target read has D1.status, snapshot,
    # and a coordinator sample. First late sample requires real terminalization;
    # second late sample reaches its actual terminal_ns + retention.
    clock.arm_steps({7: 61_000_000_000, 10: 961_000_000_000})
    if operation == "guest_status":
        error("unauthorized", intake.guest_status, item_id, accepted["status_capability"])
    elif operation == "operator_status":
        error("not_found", intake.operator_status, item_id)
    else:
        state = intake.operator_state()
        assert state["pending"] is None
        assert state["receipt_count"] == 0
    assert clock.sample_index == 11  # three target reads, last proves not_found


def test_inconsistent_public_d1_view_fails_closed_after_three_target_reads(boundary_setup, monkeypatch):
    intake, admission, decoder, clock, accepted = boundary_setup
    item_id = accepted["image"]["id"]
    stale = admission.status(id=item_id)
    original = admission.status
    calls = []
    def inconsistent(**kwargs):
        current = original(**kwargs)
        calls.append(current)
        # Keep normal initial reconciliation real. Thereafter emulate a broken
        # collaborator returning stale live metadata after D1 has terminalized.
        return current if len(calls) == 1 else stale
    monkeypatch.setattr(admission, "status", inconsistent)
    clock.ns = 61_000_000_000 - 1
    clock.arm(5, next_ns=61_000_000_000)
    error("intake_fault", intake.guest_status, item_id, accepted["status_capability"])
    assert len(calls) == 4  # one retained-ID reconciliation plus three target reads
    assert admission.snapshot().fault == "worker_failed"


@pytest.mark.parametrize("stopping", [False, True])
def test_reconciliation_preserves_d1_retention_when_stopped_without_clock_fault(boundary_setup, stopping):
    intake, admission, decoder, clock, accepted = boundary_setup
    item_id = accepted["image"]["id"]
    if stopping:
        intake.begin_stop()
    else:
        # An unexpected decoder fault is a supported lifetime fence; D1 owns
        # subsequent retention and deliberately stops age-pruning after its latch.
        admission.stop(reason="worker_failed")
        intake.maintain()
    clock.ns += 901_000_000_000
    image = intake.guest_status(item_id, accepted["status_capability"])
    assert image["detail"] == ("session_ended" if stopping else "worker_failed")
    assert image["time_uncertain"] is False
    assert intake.operator_status(item_id)["id"] == item_id
