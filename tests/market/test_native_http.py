"""Actual bounded loopback requests; measurements are explicitly synthetic."""

import threading

import pytest

from market.image_admission import AdmissionController
from market.image_intake import ImageIntake
from market.local_server import create_server

from test_image_intake import Clock, Decoder, INC
from test_image_intake_http import assets, free_port, request, token
from test_native_intake import Session


@pytest.fixture
def native_server(authority, assets):
    clock = Clock()
    decoder, session = Decoder(clock), Session(clock)
    # Boundaries are released explicitly by the synthetic test driver.
    session.boundary = None
    intake = ImageIntake(AdmissionController(INC, clock), decoder, clock, native_session=session)
    server = create_server(authority, "127.0.0.1", free_port(), assets, image_intake=intake)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield server, intake, decoder, session
    decoder.release.set()
    server.shutdown()
    thread.join(7)
    server.server_close()
    assert not thread.is_alive()


def test_native_state_role_and_no_invented_stop_route(native_server):
    server, intake, decoder, session = native_server
    for role in ("operator", "view"):
        code, _, value = request(server, path="/api/native/state", bearer=token(server, role))
        assert code == 200 and value["schema"] == "market-native-state/v1"
        assert value["observations_completed"] == 1 and value["mode"] == "bounded-native-test"
    assert request(server, path="/api/native/state", bearer=token(server, "guest"))[0] == 401
    assert not session.stops
    assert request(server, "POST", "/api/native/stop", {})[0] == 404
    assert request(server, path="/api/native/resume")[0] == 404


def test_native_routes_keep_host_origin_and_methods(native_server):
    server, *_ = native_server
    assert request(server, path="/api/native/state", headers={"Host": "evil.test"})[0] == 403
    assert request(server, path="/api/native/state", headers={"Origin": "http://evil.test"})[0] == 403
    assert request(server, "POST", "/api/native/state", {})[0] == 405
    assert request(server, path="/api/native/stop")[0] == 404


def test_v2_upload_and_price_snapshot_remain_separate(native_server):
    server, *_ = native_server
    code, _, value = request(server, "POST", "/api/images", b"synthetic PNG stand-in", token(server, "guest"))
    assert code == 202 and value["schema"] == "market-image-acceptance/v2"
    assert value["image"]["schema"] == "market-image-status-wire/v2"
    assert request(server, path="/api/snapshot")[0] == 200
    assert request(server, path="/api/images/state")[2]["schema"] == "market-image-intake/v2"


def test_standalone_native_routes_disabled(authority, assets):
    server = create_server(authority, "127.0.0.1", free_port(), assets)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        assert request(server, path="/api/native/state")[0] == 404
        assert request(server, "POST", "/api/native/stop", {})[0] == 404
    finally:
        server.shutdown()
        thread.join(7)
        server.server_close()

def test_live_http_state_acceptance_and_native_price_mode(config, clock, tmp_path, assets):
    from market.price_service import open_authority
    from test_native_intake import LiveSession
    image_clock = Clock()
    decoder, session = Decoder(image_clock), LiveSession(image_clock)
    session.completed = session.issued = 50
    session.latest, session.boundary = session.measured(49), None
    intake = ImageIntake(AdmissionController(INC, image_clock), decoder, image_clock, native_session=session)
    authority = open_authority(config, tmp_path / "live-prices.sqlite3", clock, mode="native")
    server = create_server(authority, "127.0.0.1", free_port(), assets, image_intake=intake)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        status, _, value = request(server, path="/api/native/state")
        assert status == 200 and value["schema"] == "market-native-state/v2"
        assert value["observations_completed"] == 50 and value["profile"] == "live-pilot/v1"
        status, _, value = request(server, "POST", "/api/images", b"fixture", token(server, "guest"))
        assert status == 202 and value["schema"] == "market-image-acceptance/v3"
        assert request(server, path="/api/images/state")[2]["schema"] == "market-image-intake/v3"
        value = request(server, path="/api/snapshot")[2]
        assert value["schema"] == "market-snapshot-v2" and value["source_kind"] == "native_measurement"
        status, _, value = request(server, "POST", "/api/fixtures", {"request_id": "fixture", "scenario": {}})
        assert status == 409 and value == {"error": "wrong_mode"}
        assert request(server, "POST", "/api/native/proposals", {})[0] == 404
    finally:
        decoder.release.set()
        server.shutdown()
        thread.join(7)
        server.server_close()


def test_server_calls_native_pump_outside_intake_lock_and_pauses_on_failure(authority, assets, monkeypatch):
    from conftest import make_present
    make_present(authority)
    image_clock = Clock()
    decoder, session = Decoder(image_clock), Session(image_clock)
    session.boundary = None
    intake = ImageIntake(AdmissionController(INC, image_clock), decoder, image_clock, native_session=session)
    called = threading.Event()
    pause = authority.pause
    def confirm_pause():
        result = pause()
        called.set()
        return result
    monkeypatch.setattr(authority, "pause", confirm_pause)
    class Pump:
        def maintain(self):
            assert intake._lock.acquire(blocking=False)
            intake._lock.release()
            raise RuntimeError("explicit pump failure")
    server = create_server(authority, "127.0.0.1", free_port(), assets, image_intake=intake, native_prices=Pump())
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        assert called.wait(2)
        assert authority.snapshot().paused
        assert request(server, path="/api/native/state")[0] == 200
        assert intake.native_state()["fault"] is None
    finally:
        decoder.release.set()
        server.shutdown()
        thread.join(7)
        server.server_close()


def test_native_frame_only_original_operator_and_view_and_bounded_json(native_server):
    from test_image_intake import settled, upload
    from test_native_intake import FRAME, RGB
    import base64
    import json
    server, intake, decoder, session = native_server
    item_id = upload(intake, decoder)["image"]["id"]
    settled(intake, decoder, item_id)
    intake.moderate(item_id, INC, "approve-frame", True)
    session.boundary = session.offer(1)
    intake.maintain()
    session.start_image()
    session.observation(1)
    intake.maintain()
    claim = server.authority.claim_primary(server.authority.snapshot().incarnation, "frame-primary")
    for credential in (token(server, "guest"), claim.primary_token, "bad"):
        assert request(server, path="/api/native/frame", bearer=credential)[0] == 401
    for role in ("operator", "view"):
        code, headers, value = request(server, path="/api/native/frame", bearer=token(server, role))
        assert code == 200 and value["schema"] == "market-native-frame/v1"
        assert value["image_id"] == item_id and value["frame_sha256"] == FRAME
        assert base64.b64decode(value["rgb_base64"], validate=True) == RGB
        assert len(json.dumps(value).encode("utf-8")) <= 24576
        assert headers["Cache-Control"] == "no-store"
        assert not any(key in value for key in ("pending", "status_capability", "source_sha256"))
    assert request(server, path="/api/native/frame", headers={"Host": "evil.test"})[0] == 403
    assert request(server, "POST", "/api/native/frame", {})[0] == 405
