"""Local HTTP image boundary; generated fixtures and explicit D2 logic doubles."""

import http.client
import json
from pathlib import Path
import socket
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from market.image_admission import AdmissionController
from market.image_intake import ImageIntake, IntakeError
from market.local_server import _RequestReader, create_server

from test_image_intake import Decoder, FRAME, RGB


@pytest.fixture
def assets(tmp_path):
    root = tmp_path / "dist"
    (root / ".vite").mkdir(parents=True)
    (root / "assets").mkdir()
    manifest = {}
    for entry in ("market", "market-image", "index", "sibling"):
        (root / (entry + ".html")).write_text("<p>test fixture</p>", encoding="utf-8")
        (root / "assets" / (entry + ".js")).write_text("// " + entry, encoding="utf-8")
        manifest[entry + ".html"] = {"file": "assets/" + entry + ".js", "src": entry + ".html", "isEntry": True}
    manifest["market-image.html"]["imports"] = ["_shared"]
    manifest["_shared"] = {"file": "assets/shared.js"}
    (root / "assets/shared.js").write_text("// shared", encoding="utf-8")
    (root / "assets/market-image.js.map").write_text("{}", encoding="utf-8")
    (root / ".vite/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def token(server, role="operator"):
    return urlsplit(getattr(server, role + "_url")).fragment.split("=", 1)[1]


def request(server, method="GET", path="/api/images/state", body=None, bearer=None, headers=None):
    values = {"Origin": server._origin, "Authorization": "Bearer " + (token(server) if bearer is None else bearer)}
    if body is not None:
        if type(body) is dict:
            body = json.dumps(body).encode()
            values["Content-Type"] = "application/json"
        else:
            values["Content-Type"] = "image/png"
    values.update(headers or {})
    conn = http.client.HTTPConnection(*server.server_address, timeout=7)
    try:
        conn.request(method, path, body, values)
        response = conn.getresponse()
        data = response.read()
        return response.status, dict(response.getheaders()), json.loads(data) if response.getheader("Content-Type") == "application/json" else data
    finally:
        conn.close()


def head(server, *, path="/api/images", method="POST", bearer=None, extra="", length="1", mime="image/png"):
    return (f"{method} {path} HTTP/1.1\r\nHost: {server._host_header}\r\nOrigin: {server._origin}\r\n"
            f"Authorization: Bearer {bearer or token(server, 'guest')}\r\nContent-Length: {length}\r\n"
            f"Content-Type: {mime}\r\n{extra}\r\n").encode()


def raw(server, data):
    with socket.create_connection(server.server_address, timeout=7) as sock:
        sock.sendall(data)
        result = bytearray()
        while True:
            try:
                block = sock.recv(65536)
            except ConnectionResetError:
                break
            if not block:
                return bytes(result)
            result.extend(block)
        return bytes(result)


@pytest.fixture
def running(authority, clock, assets):
    admission = AdmissionController(str(uuid4()), clock)
    decoder = Decoder(clock)
    intake = ImageIntake(admission, decoder, clock)
    server = create_server(authority, "127.0.0.1", free_port(), assets, image_intake=intake)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    yield server, intake, admission, decoder, clock
    decoder.release.set()
    server.shutdown()
    thread.join(7)
    server.server_close()
    assert not thread.is_alive()


def accepted(running):
    server, intake, admission, decoder, clock = running
    status, _, value = request(server, "POST", "/api/images", b"safe fixture", token(server, "guest"))
    assert status == 202, value
    assert decoder.entered.wait(2)
    return value


def settled(running, value):
    server, intake, admission, decoder, clock = running
    decoder.release.set()
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        result = intake.operator_status(value["image"]["id"])
        if result["detail"] != "decoding":
            return result
        threading.Event().wait(0.001)
    pytest.fail("decode callback did not settle")


def test_disabled_images_are_404_before_raw_mime(authority, assets):
    server = create_server(authority, "127.0.0.1", free_port(), assets)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        for path in ("/api/images", "/api/images/state", "/market-image.html"):
            assert request(server, "POST", path, b"x")[0] == 404
        assert request(server, path="/assets/market-image.js")[0] == 404
        assert request(server, path="/api/snapshot")[0] == 200
    finally:
        server.shutdown()
        thread.join(7)
        server.server_close()


def test_reader_releases_parser_buffer_after_copy():
    reader = _RequestReader(None)
    reader.buffer.extend(b"imageTAIL")
    assert reader.body(5) == b"image"
    assert not reader.buffer


def test_guest_upload_receipt_and_private_exact_preview(running):
    server, intake, admission, decoder, clock = running
    value = accepted(running)
    image = settled(running, value)
    path = "/api/images/status/" + image["id"]
    assert request(server, path=path, bearer=value["status_capability"])[2] == image
    assert request(server, path=path)[2] == image
    preview = "/api/images/preview/" + image["id"] + "/" + FRAME
    for credential in (token(server, "guest"), token(server, "view"), value["status_capability"], "bad"):
        assert request(server, path=preview, bearer=credential)[0] == 401
    status, headers, pixels = request(server, path=preview)
    assert status == 200 and headers["Content-Type"] == "application/octet-stream"
    assert len(pixels) == 12288 and pixels == RGB
    assert headers["Cache-Control"] == "no-store" and headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert not any(key.lower().startswith("access-control") or key.lower() == "set-cookie" for key in headers)
    assert request(server, path=preview[:-1] + ("a" if preview[-1] != "a" else "b"))[0] == 404
    assert request(server, path="/api/images/" + image["id"])[0] == 404
    assert request(server, path=path, bearer="is." + "x" * 43)[0] == 401


@pytest.mark.parametrize("path", ["/api/images/", "/api/images/status/UPPER", "/api/images/status/00000000-0000-4000-8000-00000000000A", "/api/images/state/", "/api/images/preview/" + str(uuid4()) + "/" + "A" * 64, "/api/images/moderate/nope"])
def test_literal_image_routes(running, path):
    assert request(running[0], path=path)[0] == 404


@pytest.mark.parametrize("credential", ["operator", "view", "bad", "is." + "x" * 43, "ig." + "x" * 44])
def test_upload_wrong_role_rejected_before_body(running, credential):
    server, intake, admission, decoder, clock = running
    credential = token(server, credential) if credential in ("operator", "view") else credential
    started = time.monotonic()
    reply = raw(server, head(server, bearer=credential, length="2097152"))
    assert reply.startswith(b"HTTP/1.1 401") and time.monotonic() - started < 1
    assert admission.snapshot().reservation is None and not decoder.entered.is_set()


def test_auth_reservation_before_body_and_only_own_abandon(running):
    server, intake, admission, decoder, clock = running
    with socket.create_connection(server.server_address, timeout=7) as sock:
        sock.sendall(head(server, length="3"))
        deadline = time.monotonic() + 1
        while admission.snapshot().reservation is None:
            assert time.monotonic() < deadline
            threading.Event().wait(0.001)
        old = admission.snapshot().reservation
        clock.advance(milliseconds=10000)
        new = intake.reserve_upload(token(server, "guest"))
        sock.shutdown(socket.SHUT_WR)
        assert sock.recv(4096).startswith(b"HTTP/1.1 400")
        assert admission.snapshot().reservation.id == new.id != old.id
        intake.abandon_upload(new.id)


@pytest.mark.parametrize("length,mime,status", [("0", "image/png", 400), ("2097153", "image/png", 413), ("0001", "image/png", 400), ("9" * 100, "image/png", 413), ("1", "image/jpg", 415), ("1", "image/png; x=y", 415), ("1", "multipart/form-data", 415)])
def test_raw_limits_and_exact_mime_before_reservation(running, length, mime, status):
    server, intake, admission, decoder, clock = running
    assert raw(server, head(server, length=length, mime=mime)).startswith(f"HTTP/1.1 {status}".encode())
    assert admission.snapshot().reservation is None


@pytest.mark.parametrize("extra", ["Transfer-Encoding: chunked\r\n", "Expect: 100-continue\r\n", "Content-Length: 1\r\n", "Authorization: Bearer bad\r\n", "Origin: http://evil.invalid\r\n"])
def test_raw_framing_duplicate_headers(running, extra):
    assert raw(running[0], head(running[0], extra=extra)).startswith(b"HTTP/1.1 400")


def test_two_mib_only_raw_route_and_json_remains_8192(running):
    server = running[0]
    assert request(server, "POST", "/api/images", b"x" * 2097152, token(server, "guest"))[0] == 202
    assert request(server, "POST", "/api/pause", b"x" * 8193, headers={"Content-Type": "application/json"})[0] == 413
    assert request(server, "POST", "/api/images/moderate/" + str(uuid4()), b"x" * 8193, headers={"Content-Type": "application/json"})[0] == 413


def test_operator_moderation_exact_keys_and_original_ttl(running):
    server, intake, admission, decoder, clock = running
    value = accepted(running)
    image = settled(running, value)
    path = "/api/images/moderate/" + image["id"]
    body = {"incarnation": image["incarnation"], "action_id": "approve", "approved": True}
    assert request(server, "POST", path, body | {"role": "operator"})[0] == 400
    for credential in (token(server, "guest"), token(server, "view"), value["status_capability"]):
        assert request(server, "POST", path, body, credential)[0] == 401
    reply = request(server, "POST", path, body)
    assert reply[0] == 200 and reply[2]["status"] == "queued"
    assert request(server, "POST", path, body)[2] == reply[2]
    clock.advance(milliseconds=300000)
    expired = request(server, path="/api/images/status/" + image["id"])[2]
    assert expired["status"] == "expired" and not expired["preview_available"]
    assert request(server, path="/api/snapshot")[2]["price_version"] == 0


def test_enabled_assets_are_immutable_bounded_reachable_entries(running, assets):
    server = running[0]
    for path in ("/market.html", "/market-image.html", "/assets/market-image.js", "/assets/shared.js"):
        assert request(server, path=path)[0] == 200
    (assets / "market-image.html").write_text("changed", encoding="utf-8")
    assert request(server, path="/market-image.html")[2] == b"<p>test fixture</p>"
    for path in ("/index.html", "/sibling.html", "/assets/index.js", "/assets/sibling.js", "/assets/market-image.js.map", "/.vite/manifest.json"):
        assert request(server, path=path)[0] == 404


def test_global_operator_bucket_exactly_once_and_failed_auth_free(running):
    server = running[0]
    for _ in range(3):
        assert request(server, bearer=token(server, "view"))[0] == 401
    for _ in range(120):
        assert request(server)[0] == 200
    assert request(server)[::2] == (429, {"error": "rate_limited"})


def test_receipt_bucket_exactly_once_and_wrong_id_free(running):
    server = running[0]
    value = accepted(running)
    path = "/api/images/status/" + value["image"]["id"]
    assert request(server, path="/api/images/status/" + str(uuid4()), bearer=value["status_capability"])[0] == 401
    for _ in range(120):
        assert request(server, path=path, bearer=value["status_capability"])[0] == 200
    assert request(server, path=path, bearer=value["status_capability"])[0] == 429


def test_image_secrets_cannot_read_or_mutate_price_routes(running):
    server = running[0]
    value = accepted(running)
    for bearer in (token(server, "guest"), value["status_capability"]):
        for method, path, body in (("GET", "/api/snapshot", None), ("GET", "/api/events/" + str(uuid4()), None), ("POST", "/api/pause", {}), ("POST", "/api/resume", {"request_id": "r"}), ("POST", "/api/primary/claim", {"incarnation": str(uuid4()), "request_id": "r"}), ("POST", "/api/primary/ack", {"session_id": str(uuid4()), "challenge": "x"}), ("POST", "/api/fixtures", {"request_id": "r", "scenario": {}})):
            assert request(server, method, path, body, bearer)[0] == 401


def fail_image_maintenance(running, monkeypatch):
    server, intake, admission, decoder, clock = running
    calls, failures = [], []
    failed = threading.Event()
    ready = threading.Event()
    original = server.authority.maintain
    def price_tick():
        original()
        if failed.is_set():
            calls.append(True)
            if len(calls) >= 3:
                ready.set()
    def image_tick():
        failures.append(True)
        failed.set()
        raise RuntimeError("private decoder exception must not escape maintenance")
    monkeypatch.setattr(server.authority, "maintain", price_tick)
    monkeypatch.setattr(intake, "maintain", image_tick)
    assert ready.wait(2), "an image maintenance fault stopped independent price maintenance"
    return failures


@pytest.mark.parametrize("phase", ["pending_preview", "inflight_decode"])
def test_image_maintenance_failure_stops_actions_and_preserves_price_ticks(running, monkeypatch, capsys, phase):
    server, intake, admission, decoder, clock = running
    value = accepted(running)
    item_id = value["image"]["id"]
    preview = "/api/images/preview/" + item_id + "/" + FRAME
    before = request(server, path="/api/snapshot")[2]
    if phase == "pending_preview":
        settled(running, value)
        assert request(server, path=preview)[2] == RGB
    failures = fail_image_maintenance(running, monkeypatch)
    state = request(server)[2]
    assert state["health"] == "stopping" and state["pending"] is None
    assert not state["receiving"] and state["fault"] is None
    assert decoder.requests[0][2].is_set(), "public stop did not cancel the owned decode"
    assert request(server, "POST", "/api/images", b"x", token(server, "guest"))[::2] == (503, {"error": "stopping"})
    assert request(server, path=preview)[::2] == (503, {"error": "stopping"})
    assert request(server, "POST", "/api/images/moderate/" + item_id, {
        "incarnation": value["image"]["incarnation"], "action_id": "after-fault", "approved": True,
    })[::2] == (503, {"error": "stopping"})
    decoder.release.set()
    assert decoder.exited.wait(2)
    deadline = time.monotonic() + 2
    while intake.operator_state()["decode_busy"]:
        assert time.monotonic() < deadline
        threading.Event().wait(0.001)
    assert request(server)[2]["pending"] is None
    path = "/api/images/status/" + item_id
    # Stopped diagnostics retain their original public receipt bucket ceiling.
    for _ in range(120):
        reply = request(server, path=path, bearer=value["status_capability"])
        assert reply[0] == 200 and reply[2]["detail"] == "session_ended"
        assert reply[2]["status"] == "rejected" and not reply[2]["preview_available"]
    assert request(server, path=path, bearer=value["status_capability"])[0] == 429
    after = request(server, path="/api/snapshot")[2]
    assert (after["price_version"], after["generation"], after["paused"], after["rows"]) == (
        before["price_version"], before["generation"], before["paused"], before["rows"],
    )
    assert len(failures) == 1, "a broken image callback was retried after its irreversible stop"
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_failed_public_stop_irreversibly_fences_image_transport(running, monkeypatch, capsys):
    server, intake, admission, decoder, clock = running
    value = accepted(running)
    settled(running, value)
    item_id = value["image"]["id"]
    before = request(server, path="/api/snapshot")[2]
    original_stop = intake.begin_stop
    attempts = []
    def broken_stop():
        attempts.append(True)
        raise RuntimeError("private public-stop failure")
    monkeypatch.setattr(intake, "begin_stop", broken_stop)
    try:
        failures = fail_image_maintenance(running, monkeypatch)
        for method, path, body, bearer in (
            ("GET", "/api/images/state", None, token(server)),
            ("GET", "/api/images/status/" + item_id, None, value["status_capability"]),
            ("GET", "/api/images/preview/" + item_id + "/" + FRAME, None, token(server)),
            ("POST", "/api/images", b"x", token(server, "guest")),
            ("POST", "/api/images/moderate/" + item_id, {"incarnation": value["image"]["incarnation"], "action_id": "fenced", "approved": True}, token(server)),
        ):
            assert request(server, method, path, body, bearer)[::2] == (503, {"error": "intake_fault"})
        assert len(attempts) == len(failures) == 1
        # The real owner is retained despite the failed stop; cleanup can retry it.
        assert not decoder.closed
        monkeypatch.setattr(intake, "begin_stop", original_stop)
        original_stop()
        assert request(server)[::2] == (503, {"error": "intake_fault"})
        after = request(server, path="/api/snapshot")[2]
        assert after["price_version"] == before["price_version"] == 0
        assert after["generation"] == before["generation"] and after["paused"] == before["paused"]
        output = capsys.readouterr()
        assert output.out == output.err == ""
    finally:
        monkeypatch.setattr(intake, "begin_stop", original_stop)


@pytest.mark.parametrize("kind", ["upload", "moderate"])
def test_public_stop_failure_fences_already_receiving_image_body(running, monkeypatch, kind):
    server, intake, admission, decoder, clock = running
    body = b"x"
    path, bearer, mime = "/api/images", token(server, "guest"), "image/png"
    if kind == "moderate":
        value = accepted(running)
        settled(running, value)
        path = "/api/images/moderate/" + value["image"]["id"]
        bearer, mime = token(server), "application/json"
        body = json.dumps({"incarnation": value["image"]["incarnation"], "action_id": "slow-after-fault", "approved": True}).encode()
    entered = threading.Event()
    original_body = _RequestReader.body
    def reading(reader, length):
        entered.set()
        return original_body(reader, length)
    monkeypatch.setattr(_RequestReader, "body", reading)
    original_stop = intake.begin_stop
    def broken_stop():
        raise RuntimeError("private failed stop with a receiving body")
    monkeypatch.setattr(intake, "begin_stop", broken_stop)
    try:
        with socket.create_connection(server.server_address, timeout=7) as sock:
            sock.sendall(head(server, path=path, bearer=bearer, length=str(len(body)), mime=mime))
            assert entered.wait(1)
            fail_image_maintenance(running, monkeypatch)
            sock.sendall(body)
            response = http.client.HTTPResponse(sock)
            response.begin()
            assert response.status == 503 and json.loads(response.read()) == {"error": "intake_fault"}
        if kind == "upload":
            assert not decoder.entered.is_set() and admission.snapshot().reservation is None
        else:
            image = intake.operator_status(value["image"]["id"])
            assert image["detail"] == "awaiting_approval", "fenced body reached moderation"
    finally:
        monkeypatch.setattr(intake, "begin_stop", original_stop)


@pytest.mark.parametrize("code,status", [("unauthorized", 401), ("not_found", 404), ("full", 409), ("busy", 409), ("invalid_transition", 409), ("idempotency_conflict", 409), ("wrong_incarnation", 409), ("rate_limited", 429), ("invalid_request", 400), ("capacity", 503), ("intake_fault", 503), ("stopping", 503), ("closed", 503), ("cleanup_failed", 503)])
def test_closed_image_error_mapping(running, monkeypatch, code, status):
    def fail(*args, **kwargs):
        raise IntakeError(code)
    monkeypatch.setattr(running[1], "charge_operator", fail)
    assert request(running[0])[::2] == (status, {"error": code})


def test_image_json_cap_and_no_exception_payload_logging(running, monkeypatch, capsys):
    server, intake, admission, decoder, clock = running
    monkeypatch.setattr(intake, "operator_state", lambda: {"oversize": "x" * 8192})
    assert request(server)[::2] == (503, {"error": "capacity"})
    def crash():
        raise RuntimeError("private-payload-" + token(server, "guest"))
    monkeypatch.setattr(intake, "operator_state", crash)
    reply = raw(server, head(server, method="GET", path="/api/images/state", bearer=token(server), length="0"))
    assert reply == b""
    output = capsys.readouterr()
    assert output.out == output.err == ""


def test_slow_body_operation_timeout_abandons_reservation(running):
    server, intake, admission, decoder, clock = running
    started = time.monotonic()
    reply = raw(server, head(server, length="100"))
    assert reply.startswith(b"HTTP/1.1 408")
    assert 1.5 <= time.monotonic() - started < 4
    assert admission.snapshot().reservation is None and not decoder.entered.is_set()
    # The authenticated request charged once even though its body failed.
    assert request(server, "POST", "/api/images", b"x", token(server, "guest"))[0] == 429


def test_progress_making_body_still_has_total_five_second_deadline(running):
    server, intake, admission, decoder, clock = running
    started = time.monotonic()
    with socket.create_connection(server.server_address, timeout=7) as sock:
        sock.sendall(head(server, length="100"))
        for _ in range(6):
            threading.Event().wait(0.8)
            sock.sendall(b"x")
        reply = sock.recv(4096)
    assert reply.startswith(b"HTTP/1.1 408")
    assert 4.5 <= time.monotonic() - started < 6.5
    assert admission.snapshot().reservation is None and not decoder.entered.is_set()


def test_raw_host_origin_path_get_body_and_methods(running):
    server = running[0]
    for old, new, status in ((server._host_header, "localhost:8765", 403), ("Origin: " + server._origin, "Origin: http://evil.invalid", 403), ("Origin: " + server._origin + "\r\n", "", 403), ("POST /api/images ", "POST /api/images?token=hidden ", 400), ("POST /api/images ", "POST /api/images%2f ", 400), ("POST /api/images ", "POST /api/../images ", 400), ("Content-Length: 1\r\n", "", 411)):
        data = head(server).decode().replace(old, new, 1).encode()
        assert raw(server, data).startswith(f"HTTP/1.1 {status}".encode())
    assert raw(server, head(server, method="GET", path="/api/images/state", bearer=token(server))).startswith(b"HTTP/1.1 400")
    assert raw(server, head(server, method="GET", length="0")).startswith(b"HTTP/1.1 405")
    assert raw(server, head(server, method="PUT")).startswith(b"HTTP/1.1 405")


def test_future_primary_with_identical_suffix_has_no_image_authority(authority, clock, assets, monkeypatch):
    import secrets
    suffix = "a" * 43
    values = iter([suffix, "o" * 43, "v" * 43, suffix, suffix])
    monkeypatch.setattr(secrets, "token_urlsafe", lambda size: next(values))
    decoder = Decoder(clock)
    intake = ImageIntake(AdmissionController(str(uuid4()), clock), decoder, clock)
    server = create_server(authority, "127.0.0.1", free_port(), assets, image_intake=intake)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        assert token(server, "guest") == "ig." + suffix
        value = request(server, "POST", "/api/images", b"x", token(server, "guest"))[2]
        assert value["status_capability"] == "is." + suffix
        incarnation = request(server, path="/api/snapshot")[2]["incarnation"]
        primary = request(server, "POST", "/api/primary/claim", {"incarnation": incarnation, "request_id": "future"})[2]
        assert primary["primary_token"] == suffix
        item_id = value["image"]["id"]
        for method, path, body in (("GET", "/api/images/state", None), ("GET", "/api/images/status/" + item_id, None), ("GET", "/api/images/preview/" + item_id + "/" + FRAME, None), ("POST", "/api/images", b"x"), ("POST", "/api/images/moderate/" + item_id, {"incarnation": value["image"]["incarnation"], "action_id": "bad", "approved": False})):
            assert request(server, method, path, body, suffix)[0] == 401
        for secret in ("ig." + suffix, "is." + suffix):
            assert request(server, path="/api/snapshot", bearer=secret)[0] == 401
        assert request(server, path="/api/images/status/" + item_id, bearer="is." + suffix)[0] == 200
    finally:
        decoder.release.set()
        server.shutdown()
        thread.join(7)
        server.server_close()


def test_acceptance_clock_starts_after_complete_body_and_late_decode_cannot_publish(running):
    server, intake, admission, decoder, clock = running
    start_ns = clock.ns
    with socket.create_connection(server.server_address, timeout=7) as sock:
        sock.sendall(head(server, length="4") + b"ab")
        deadline = time.monotonic() + 1
        while admission.snapshot().reservation is None:
            assert time.monotonic() < deadline
            threading.Event().wait(0.001)
        clock.advance(milliseconds=4000)
        sock.sendall(b"cd")
        response = http.client.HTTPResponse(sock)
        response.begin()
        assert response.status == 202
        value = json.loads(response.read())
    assert decoder.entered.wait(2)
    assert decoder.requests[0][0].accepted_ns == start_ns + 4_000_000_000
    assert value["image"]["accepted_age_ms"] == 0
    clock.advance(milliseconds=10000)
    final = request(server, path="/api/images/status/" + value["image"]["id"])[2]
    assert final["detail"] == "decode_timeout"
    late = settled(running, value)
    assert late["detail"] == "decode_timeout" and not late["preview_available"]
    assert request(server)[2]["pending"] is None


def test_bad_clock_diagnostics_use_frozen_credits_then_closed_is_503(running):
    server, intake, admission, decoder, clock = running
    value = accepted(running)
    settled(running, value)
    def fault():
        raise RuntimeError("private clock failure")
    clock.callback = fault
    status, _, state = request(server)
    assert status == 200 and state["health"] == "faulted" and state["fault"] == "clock"
    for _ in range(119):
        assert request(server)[0] == 200
    assert request(server)[0] == 429
    path = "/api/images/status/" + value["image"]["id"]
    for _ in range(120):
        reply = request(server, path=path, bearer=value["status_capability"])
        assert reply[0] == 200 and reply[2]["time_uncertain"]
        assert reply[2]["accepted_age_ms"] is None
    assert request(server, path=path, bearer=value["status_capability"])[0] == 429
    assert request(server, "POST", "/api/images", b"x", token(server, "guest"))[0] == 503
    intake.finish_close()
    assert request(server)[::2] == (503, {"error": "closed"})


def test_rejected_moderation_body_spends_one_operator_credit(running):
    server = running[0]
    path = "/api/images/moderate/" + str(uuid4())
    assert request(server, "POST", path, b'{"approved":true,"approved":false}', headers={"Content-Type": "application/json"})[0] == 400
    for _ in range(119):
        assert request(server)[0] == 200
    assert request(server)[0] == 429
