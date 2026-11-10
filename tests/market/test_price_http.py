from dataclasses import replace
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from market.local_server import create_server
from market.price_service import open_authority

from conftest import make_present, proposal


SCENARIO = {"fixture_id": "synthetic-price-v1", "drink_id": "drink-00",
            "target_rappen": 700, "expected_drink_version": 0}
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"


@pytest.fixture
def assets(tmp_path):
    root = tmp_path / "dist"
    (root / ".vite").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "market.html").write_text('<script type="module" src="/assets/market.js"></script>', encoding="utf-8")
    for name in ("market.js", "shared.js", "market.css", "picture.svg", "replay.js", "market.js.map"):
        (root / "assets" / name).write_text("asset-" + name, encoding="utf-8")
    manifest = {
        "market.html": {"file": "assets/market.js", "isEntry": True, "src": "market.html",
                        "imports": ["_shared.js"], "css": ["assets/market.css"], "assets": ["assets/picture.svg"]},
        "_shared.js": {"file": "assets/shared.js"},
        "index.html": {"file": "assets/replay.js", "isEntry": True},
    }
    (root / ".vite" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture
def server(authority, assets):
    result = create_server(authority, "127.0.0.1", free_port(), assets)
    worker = threading.Thread(target=result.serve_forever)
    worker.start()
    yield result
    result.shutdown()
    worker.join(6)
    result.server_close()
    assert not worker.is_alive()


def token(server, role="operator"):
    return urlsplit(getattr(server, role + "_url")).fragment.split("=", 1)[1]


def address(server):
    value = urlsplit(server.operator_url)
    return value.hostname, value.port


def request(server, method="GET", path="/api/snapshot", body=None, role="operator", headers=None):
    host, port = address(server)
    values = {"Authorization": "Bearer " + (token(server, role) if role in ("operator", "view") else role),
              "Origin": f"http://{host}:{port}"}
    if body is not None:
        body = json.dumps(body).encode() if not isinstance(body, bytes) else body
        values["Content-Type"] = "application/json"
    values.update(headers or {})
    connection = http.client.HTTPConnection(host, port, timeout=6)
    try:
        connection.request(method, path, body, values)
        response = connection.getresponse()
        data = response.read()
        return response.status, dict(response.getheaders()), json.loads(data) if data else None
    finally:
        connection.close()


def raw(server, data):
    with socket.create_connection(address(server), timeout=6) as connection:
        connection.settimeout(6)
        connection.sendall(data)
        result = bytearray()
        while True:
            try:
                chunk = connection.recv(65536)
            except ConnectionResetError:
                break
            if not chunk:
                break
            result.extend(chunk)
        return bytes(result)


def head(server, *, path="/api/pause", method="POST"):
    _, port = address(server)
    return (f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            f"Origin: http://127.0.0.1:{port}\r\nAuthorization: Bearer {token(server)}\r\n").encode()


def claim(server, request_id="claim-1"):
    incarnation = request(server)[2]["incarnation"]
    status, _, reply = request(server, "POST", "/api/primary/claim", {"incarnation": incarnation, "request_id": request_id})
    assert status == 200
    return reply


def present(server):
    value = claim(server)
    status, _, snap = request(server, role=value["primary_token"])
    assert status == 200 and snap["challenge"] is not None
    status, _, ack = request(server, "POST", "/api/primary/ack", {
        "session_id": value["session_id"], "challenge": snap["challenge"]["id"],
    }, role=value["primary_token"])
    assert status == 200 and ack["accepted"]
    return value


def test_urls_headers_static_and_read_only(server):
    assert server.operator_url.startswith(f"http://127.0.0.1:{address(server)[1]}/market.html#operator=")
    assert server.view_url.startswith(f"http://127.0.0.1:{address(server)[1]}/market.html#view=")
    assert token(server) != token(server, "view") and len(token(server)) >= 43
    status, headers, snap = request(server, role="view")
    assert status == 200 and snap["challenge"] is None
    assert snap["primary_state"] == "unclaimed"
    assert headers["Cache-Control"] == "no-store"
    assert headers["Content-Security-Policy"] == CSP
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert not any(key.lower().startswith("access-control") for key in headers)
    for path in ("/market.html", "/assets/market.js", "/assets/shared.js", "/assets/market.css", "/assets/picture.svg"):
        data = raw(server, head(server, path=path, method="GET") + b"\r\n")
        assert data.startswith(b"HTTP/1.1 200"), path
    for path in ("/", "/index.html", "/assets/replay.js", "/.vite/manifest.json", "/assets/market.js.map", "/../market.html", "/%2e%2e/market.html", "/market.html?q=1", "/api/snapshot?q=1", "/api/events", "/api/proposals"):
        assert request(server, path=path)[0] in (400, 404), path


@pytest.mark.parametrize("method,path,body", [
    ("POST", "/api/pause", {}), ("POST", "/api/resume", {"request_id": "r"}),
    ("POST", "/api/primary/claim", {"incarnation": str(uuid4()), "request_id": "c"}),
    ("POST", "/api/fixtures", {"request_id": "f", "scenario": SCENARIO}),
    ("POST", "/api/primary/ack", {"session_id": str(uuid4()), "challenge": str(uuid4())}),
])
def test_view_cannot_mutate(server, method, path, body):
    before = request(server)[2]
    assert request(server, method, path, body, role="view")[0] == 401
    after = request(server)[2]
    assert (after["revision"], after["generation"]) == (before["revision"], before["generation"])


@pytest.mark.parametrize("headers,status,error", [
    ({"Host": "localhost:8765"}, 403, "forbidden_host"),
    ({"Origin": "http://evil.invalid"}, 403, "forbidden_origin"),
    ({"Authorization": "Bearer bad"}, 401, "unauthorized"),
    ({"Content-Type": "text/plain"}, 415, "unsupported_media_type"),
])
def test_authorization_boundaries(server, headers, status, error):
    assert request(server, "POST", "/api/pause", {}, headers=headers)[::2] == (status, {"error": error})


def test_primary_role_and_readonly_cannot_steal_challenge(server):
    primary = claim(server)
    assert len({primary["primary_token"], token(server), token(server, "view")}) == 3
    snap = request(server, role=primary["primary_token"])[2]
    assert request(server, role="view")[2]["challenge"] is None
    assert request(server)[2]["challenge"] is None
    assert request(server, "POST", "/api/resume", {"request_id": "wrong-role"}, role=primary["primary_token"])[0] == 401
    assert request(server, "POST", "/api/primary/ack", {"session_id": primary["session_id"], "challenge": snap["challenge"]["id"]}, role=primary["primary_token"])[2]["accepted"]
    assert request(server, "POST", "/api/primary/ack", {"session_id": primary["session_id"], "challenge": snap["challenge"]["id"]})[0] == 401


def test_fixture_terminal_lookup_and_restart_retry(server, authority):
    present(server)
    assert request(server, "POST", "/api/resume", {"request_id": "resume"})[2]["result"]["status"] == "accepted"
    payload = {"request_id": "fixture", "scenario": SCENARIO}
    status, _, result = request(server, "POST", "/api/fixtures", payload)
    assert status == 200 and result["status"] == "activated"
    assert request(server, "POST", "/api/fixtures", payload)[2] == result
    assert request(server, path="/api/events/" + result["event_id"], role="view")[2] == result
    assert request(server, path="/api/events/" + str(uuid4()))[0] == 404
    assert request(server, "POST", "/api/fixtures", payload | {"scenario": SCENARIO | {"target_rappen": 650}})[0] == 409
    rejected = request(server, "POST", "/api/fixtures", {"request_id": "cooldown", "scenario": SCENARIO | {"target_rappen": 650, "expected_drink_version": 1}})
    assert rejected[0] == 200 and rejected[2]["reason"] == "cooldown"


@pytest.mark.parametrize("path,body", [
    ("/api/pause", {"extra": 1}), ("/api/resume", {}),
    ("/api/fixtures", {"request_id": "bad", "scenario": SCENARIO | {"created_ns": 1}}),
    ("/api/fixtures", {"request_id": "bad", "scenario": SCENARIO, "source_kind": "neural"}),
    ("/api/primary/claim", {"incarnation": str(uuid4()), "request_id": True}),
])
def test_exact_fields(server, path, body):
    before = request(server)[2]
    assert request(server, "POST", path, body)[0] == 400
    assert request(server)[2]["revision"] == before["revision"]


@pytest.mark.parametrize("suffix,status,error", [
    (b"\r\n", 411, b"length_required"),
    (b"Content-Length: 0\r\nContent-Length: 0\r\n\r\n", 400, b"invalid_http"),
    (b"Content-Length: 0,0\r\n\r\n", 400, b"invalid_http"),
    (b"Transfer-Encoding: chunked\r\n\r\n", 400, b"invalid_http"),
    (b"Content-Length: 8193\r\n\r\n", 413, b"body_too_large"),
    (b"Content-Length: 2\r\nContent-Type: text/plain\r\n\r\n{}", 415, b"unsupported_media_type"),
    (b"Content-Length: 15\r\nContent-Type: application/json\r\n\r\n{\"x\":1,\"x\":2}  ", 400, b"invalid_request"),
    (b"Content-Length: 3\r\nContent-Type: application/json\r\n\r\nNaN", 400, b"invalid_request"),
    (b"Content-Length: 1\r\nContent-Type: application/json\r\n\r\n\xff", 400, b"invalid_request"),
    (b" Folded: no\r\n\r\n", 400, b"invalid_http"),
])
def test_framing_no_mutation(server, suffix, status, error):
    before = request(server)[2]
    result = raw(server, head(server) + suffix)
    assert result.startswith(f"HTTP/1.1 {status} ".encode()) and error in result
    assert request(server)[2]["revision"] == before["revision"]


def test_body_exact_limit_and_header_line_bounds(server):
    assert request(server, "POST", "/api/pause", b"{}" + b" " * 8190)[0] == 200
    assert request(server, "POST", "/api/pause", b"{}" + b" " * 8191)[0] == 413
    assert raw(server, head(server) + b"X: " + b"a" * 16384 + b"\r\n\r\n").startswith(b"HTTP/1.1 431 ")
    assert raw(server, head(server) + b"X: a\r\n" * 65 + b"\r\n").startswith(b"HTTP/1.1 431 ")
    assert raw(server, b"GET /" + b"a" * 2048 + b" HTTP/1.1\r\n\r\n").startswith(b"HTTP/1.1 400 ")
    assert request(server, "PUT", "/api/pause", {})[0] == 405
    assert raw(server, head(server).replace(b"Origin:", b"Other:") + b"Content-Length: 2\r\nContent-Type: application/json\r\n\r\n{}").startswith(b"HTTP/1.1 403 ")


def test_json_response_cap(server, authority, monkeypatch):
    actual = authority.snapshot()
    monkeypatch.setattr(authority, "snapshot", lambda *args: replace(actual, server_utc="x" * 65536))
    status, _, body = request(server)
    assert status == 503 and body == {"error": "capacity"}


@pytest.mark.parametrize("phase", ["headers", "body"])
def test_socket_read_timeout(server, phase):
    data = head(server)
    if phase == "body":
        data += b"Content-Length: 2\r\nContent-Type: application/json\r\n\r\n{"
    start = time.monotonic()
    result = raw(server, data)
    assert result.startswith(b"HTTP/1.1 408 ")
    assert 1.7 <= time.monotonic() - start < 3.5


@pytest.mark.parametrize("phase", ["headers", "body"])
def test_absolute_read_deadline_despite_progress(server, phase):
    with socket.create_connection(address(server), timeout=6) as connection:
        connection.settimeout(6)
        connection.sendall(head(server) + (b"X: " if phase == "headers" else b"Content-Length: 100\r\nContent-Type: application/json\r\n\r\n"))
        stop = threading.Event()
        def drip():
            while not stop.wait(0.35):
                try:
                    connection.sendall(b" ")
                except OSError:
                    break
        worker = threading.Thread(target=drip)
        worker.start()
        start = time.monotonic()
        try:
            result = connection.recv(4096)
            assert result.startswith(b"HTTP/1.1 408 ")
            assert 4.5 <= time.monotonic() - start < 6
        finally:
            stop.set()
            worker.join(1)


def occupy(server, count, monkeypatch):
    # A receive barrier in the real request reader keeps all admitted handlers occupied.
    import market.local_server as module
    entered = threading.Condition()
    release = threading.Event()
    original = module._RequestReader.receive
    seen = 0
    def barrier(reader):
        nonlocal seen
        with entered:
            seen += 1
            entered.notify_all()
        assert release.wait(6)
        return original(reader)
    monkeypatch.setattr(module._RequestReader, "receive", barrier)
    connections = [socket.create_connection(address(server), timeout=6) for _ in range(count)]
    with entered:
        assert entered.wait_for(lambda: seen >= count, timeout=5)
    return connections, release


def close_occupied(connections, release):
    for connection in connections:
        connection.close()
    release.set()


def test_eight_handlers_overload_latches_pause(server, authority, monkeypatch):
    make_present(authority)
    before = authority.snapshot()
    connections, release = occupy(server, 8, monkeypatch)
    try:
        assert raw(server, b"") == b""
        assert authority.capture_safety_epoch() > 0
    finally:
        close_occupied(connections, release)
    after = authority.snapshot()
    assert after.paused and after.fault == "overload"
    assert after.price_version == before.price_version
    assert authority.snapshot().paused


def test_overload_defeats_older_resume_during_commit(server, authority, monkeypatch):
    make_present(authority)
    authority.pause()
    entered, release_commit = threading.Event(), threading.Event()
    original = authority._commit_transaction
    def blocked_commit():
        entered.set()
        assert release_commit.wait(6)
        original()
    monkeypatch.setattr(authority, "_commit_transaction", blocked_commit)
    replies = []
    worker = threading.Thread(target=lambda: replies.append(request(server, "POST", "/api/resume", {"request_id": "old-resume"})))
    worker.start()
    assert entered.wait(5)
    connections, release = occupy(server, 7, monkeypatch)
    try:
        assert raw(server, b"") == b""
    finally:
        close_occupied(connections, release)
        release_commit.set()
    worker.join(6)
    monkeypatch.setattr(authority, "_commit_transaction", original)
    assert not worker.is_alive()
    reply = replies[0][2]
    assert reply["snapshot"]["paused"] and reply["superseding_reason"] == "overload"
    assert request(server, "POST", "/api/resume", {"request_id": "old-resume"})[2]["snapshot"]["paused"]
    assert not request(server, "POST", "/api/resume", {"request_id": "new-resume"})[2]["snapshot"]["paused"]


def test_http_lease_get_never_renews_and_replacement_revokes(server, clock):
    old = present(server)
    generation = request(server)[2]["generation"]
    clock.advance(4999)
    assert request(server, role=old["primary_token"])[2]["primary_state"] == "present"
    clock.advance(1)
    # GET itself synchronizes expiry; no dependence on the maintenance tick.
    snap = request(server, role=old["primary_token"])[2]
    assert snap["primary_state"] == "absent" and snap["generation"] == generation + 1
    new = claim(server, "replacement")
    assert request(server, role=old["primary_token"])[0] == 401
    assert request(server, "POST", "/api/primary/ack", {"session_id": old["session_id"], "challenge": snap["challenge"]["id"]}, role=new["primary_token"])[0] == 401
    incarnation = new["snapshot"]["incarnation"]
    assert request(server, "POST", "/api/primary/claim", {"incarnation": incarnation, "request_id": "claim-1"})[0] == 409
    assert request(server, "POST", "/api/primary/claim", {"incarnation": str(uuid4()), "request_id": "replacement"})[0] == 409


def test_claim_capacity_http(server, clock):
    for index in range(64):
        assert claim(server, f"claim-{index}")["session_id"]
        clock.advance(5000)
    incarnation = request(server)[2]["incarnation"]
    assert request(server, "POST", "/api/primary/claim", {"incarnation": incarnation, "request_id": "claim-over"})[::2] == (503, {"error": "claim_capacity"})


def test_symlink_assets_rejected(authority, assets, tmp_path):
    target = tmp_path / "outside.js"
    target.write_text("secret", encoding="utf-8")
    path = assets / "assets" / "market.js"
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError as error:
        pytest.skip(f"symlink privilege unavailable: {error}")
    with pytest.raises(ValueError):
        create_server(authority, "127.0.0.1", free_port(), assets)


@pytest.mark.parametrize("host,port", [("localhost", 8765), ("0.0.0.0", 8765), ("127.0.0.1", 0), ("127.0.0.1", 65536), ("127.0.0.1", True)])
def test_bind_validation(authority, assets, host, port):
    with pytest.raises(ValueError):
        create_server(authority, host, port, assets)


def test_no_request_credentials_or_body_logged(server, capsys):
    request(server, "POST", "/api/pause", b'{"private_body":"secret"}')
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_exact_request_line_header_and_response_boundaries(server, authority, monkeypatch):
    # 2048 includes CRLF; an equally valid 2049-byte line must fail at framing.
    line = b"GET /" + b"a" * (2048 - len(b"GET / HTTP/1.1\r\n")) + b" HTTP/1.1\r\n"
    assert len(line) == 2048
    _, port = address(server)
    host = f"Host: 127.0.0.1:{port}\r\n".encode()
    assert raw(server, line + host + b"\r\n").startswith(b"HTTP/1.1 404 ")
    assert raw(server, line[:-2] + b"x\r\n" + host + b"\r\n").startswith(b"HTTP/1.1 400 ")
    prefix = b"GET /market.html HTTP/1.1\r\n"
    assert raw(server, prefix + host + b"X: a\r\n" * 63 + b"\r\n").startswith(b"HTTP/1.1 200 ")
    assert raw(server, prefix + host + b"X: a\r\n" * 64 + b"\r\n").startswith(b"HTTP/1.1 431 ")
    headers = host + b"X: " + b"a" * (16384 - len(host) - 7) + b"\r\n\r\n"
    assert len(headers) == 16384
    assert raw(server, prefix + headers).startswith(b"HTTP/1.1 200 ")
    assert raw(server, prefix + headers[:-2] + b"x\r\n").startswith(b"HTTP/1.1 431 ")
    actual = authority.snapshot()
    from dataclasses import asdict
    empty = replace(actual, server_utc="")
    base = len(json.dumps(asdict(empty), ensure_ascii=False, separators=(",", ":")).encode())
    monkeypatch.setattr(authority, "snapshot", lambda *args: replace(empty, server_utc="x" * (65536 - base)))
    assert request(server)[0] == 200
    monkeypatch.setattr(authority, "snapshot", lambda *args: replace(empty, server_utc="x" * (65537 - base)))
    assert request(server)[::2] == (503, {"error": "capacity"})


@pytest.mark.parametrize("wire", [
    b"GET /api/snapshot HTTP/0.9\r\n\r\n",
    b"GET http://127.0.0.1/api/snapshot HTTP/1.1\r\n\r\n",
    b"GET //api/snapshot HTTP/1.1\r\n\r\n",
    b"GET /api/\x00snapshot HTTP/1.1\r\n\r\n",
    b"GET /api/snapshot HTTP/1.1\n\n",
])
def test_invalid_request_targets_and_versions(server, wire):
    assert raw(server, wire).startswith(b"HTTP/1.1 400 ")


def test_successful_commit_with_lost_http_response_retries_once(server, authority, monkeypatch):
    primary = present(server)
    request(server, "POST", "/api/resume", {"request_id": "lost-resume"})
    committed = threading.Event()
    original = authority.run_fixture
    outcomes = []
    def observe_commit(*args):
        result = original(*args)
        outcomes.append(result)
        committed.set()
        return result
    monkeypatch.setattr(authority, "run_fixture", observe_commit)
    payload = json.dumps({"request_id": "lost", "scenario": SCENARIO}).encode()
    wire = head(server, path="/api/fixtures") + f"Content-Length: {len(payload)}\r\nContent-Type: application/json\r\n\r\n".encode() + payload
    connection = socket.create_connection(address(server), timeout=6)
    connection.sendall(wire)
    connection.shutdown(socket.SHUT_RDWR)
    connection.close()
    assert committed.wait(5)
    retry = request(server, "POST", "/api/fixtures", {"request_id": "lost", "scenario": SCENARIO})
    assert retry[0] == 200 and retry[2]["event_id"] == outcomes[0].event_id
    assert retry[2]["status"] == "activated"
    assert request(server)[2]["price_version"] == 1
    assert request(server, path="/api/events/" + outcomes[0].event_id, role=primary["primary_token"])[2] == retry[2]


def test_http_restart_keeps_original_outcome_and_revokes_old_capabilities(config, clock, assets, tmp_path):
    path = tmp_path / "restart.sqlite3"
    old_primary = old_operator = old_incarnation = original = None
    for iteration in range(2):
        authority = open_authority(config, path, clock)
        service = create_server(authority, "127.0.0.1", free_port(), assets)
        thread = threading.Thread(target=service.serve_forever)
        thread.start()
        try:
            if iteration == 0:
                old_primary = present(service)
                old_operator = token(service)
                old_incarnation = old_primary["snapshot"]["incarnation"]
                request(service, "POST", "/api/resume", {"request_id": "restart-resume"})
                original = request(service, "POST", "/api/fixtures", {"request_id": "restart-fixture", "scenario": SCENARIO})[2]
                assert original["status"] == "activated"
            else:
                assert request(service, role=old_primary["primary_token"])[0] == 401
                assert request(service, role=old_operator)[0] == 401
                snapshot = request(service)[2]
                assert snapshot["incarnation"] != old_incarnation and snapshot["paused"]
                assert snapshot["rows"][0]["recovery_lock"] and snapshot["rows"][0]["remaining_lock_ms"] == 1800000
                assert request(service, "POST", "/api/fixtures", {"request_id": "restart-fixture", "scenario": SCENARIO})[2] == original
                assert request(service, "POST", "/api/primary/claim", {"request_id": "claim-1", "incarnation": old_incarnation})[::2] == (409, {"error": "wrong_incarnation"})
        finally:
            service.shutdown()
            thread.join(6)
            service.server_close()
            assert not thread.is_alive()


def test_maintenance_expires_without_polling(server, authority, clock, monkeypatch):
    present(server)
    expired = threading.Event()
    original = authority.maintain
    def observe_maintenance():
        original()
        if authority.snapshot().primary_state == "absent":
            expired.set()
    monkeypatch.setattr(authority, "maintain", observe_maintenance)
    clock.advance(5000)
    assert expired.wait(1)
    assert request(server)[2]["primary_state"] == "absent"


def test_http_cannot_clear_capacity_with_overload_then_resume(server, authority, clock):
    present(server)
    request(server, "POST", "/api/resume", {"request_id": "capacity-resume"})
    authority.submit_synthetic(proposal(authority, clock, sequence=9007199254740991, target_rappen=400))
    assert request(server, "POST", "/api/fixtures", {"request_id": "exhausted", "scenario": SCENARIO})[::2] == (503, {"error": "capacity"})
    authority.request_safety_pause("overload")
    reply = request(server, "POST", "/api/resume", {"request_id": "no-capacity-reset"})
    assert reply[0] == 200 and reply[2]["result"]["reason"] == "capacity"
    assert reply[2]["snapshot"]["paused"] and reply[2]["snapshot"]["price_version"] == 0


def test_rejected_resume_and_ack_remain_domain_200(server):
    resume = request(server, "POST", "/api/resume", {"request_id": "no-board"})
    assert resume[0] == 200 and resume[2]["result"]["reason"] == "board_absent"
    primary = claim(server)
    ack = request(server, "POST", "/api/primary/ack", {"session_id": primary["session_id"], "challenge": str(uuid4())}, role=primary["primary_token"])
    assert ack[0] == 200 and not ack[2]["accepted"] and ack[2]["reason"] == "invalid_challenge"


def test_cli_invalid_inputs_create_no_database(assets, tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("market_cli", Path("scripts/run-market-price-service.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    db = tmp_path / "new-directory" / "state.sqlite3"
    args = ["--config", "examples/market-synthetic.json", "--db", str(db), "--assets", str(assets)]
    assert cli.main(args + ["--host", "0.0.0.0"]) == 1
    assert not db.parent.exists()
    assert cli.main(args + ["--port", "0"]) == 1
    assert not db.parent.exists()
    assert cli.main(args + ["--assets", str(tmp_path / "missing-dist")]) == 1
    assert not db.parent.exists()


def test_cli_interrupt_and_bind_failure_release_ownership(assets, tmp_path, config, clock, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("market_cli", Path("scripts/run-market-price-service.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    from market.local_server import LocalMarketServer
    def interrupted(server):
        raise KeyboardInterrupt
    monkeypatch.setattr(LocalMarketServer, "serve_forever", interrupted)
    db = tmp_path / "created" / "state.sqlite3"
    args = ["--config", "examples/market-synthetic.json", "--db", str(db), "--assets", str(assets), "--port", str(free_port())]
    assert cli.main(args) == 0
    # Opening URLs intentionally stay in this in-memory capture, never in logs.
    captured = capsys.readouterr()
    assert "#operator=" in captured.out and "#view=" in captured.out and "Clock:" in captured.out
    with open_authority(config, db, clock):
        pass
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        assert cli.main(args + ["--port", str(listener.getsockname()[1])]) == 1
    with open_authority(config, db, clock):
        pass


def test_standard_http_port_has_canonical_browser_authority():
    from market.local_server import _loopback_endpoint
    assert _loopback_endpoint(80) == ("127.0.0.1", "http://127.0.0.1")
    assert _loopback_endpoint(8765) == ("127.0.0.1:8765", "http://127.0.0.1:8765")


def test_buffered_request_bytes_cannot_outlive_read_deadline():
    from market.local_server import _RequestReader
    from market.price_service import MarketError
    reader = _RequestReader(None)
    reader.buffer.extend(b"{}\r\n")
    reader.deadline = time.monotonic() - 1
    with pytest.raises(MarketError, match="request_timeout"):
        reader.body(2)
    with pytest.raises(MarketError, match="request_timeout"):
        reader.line(2048, "invalid_http")
