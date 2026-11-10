"""Optional CLI startup/cleanup and actual owned generated-fixture integration."""

from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sys
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from market.image_decode import DecodeError, ImageDecoder
from market.image_admission import AdmissionController
from market.image_intake import ImageIntake, IntakeError
from market.price_service import SystemClock, open_authority
from market.local_server import create_server
from test_image_intake_http import assets, free_port, head, request, token
from test_image_intake import RGB, FRAME
from test_image_decode_windows import png
from test_price_process import children


ROOT = Path(__file__).resolve().parents[2]


def cli_module():
    spec = importlib.util.spec_from_file_location("image_cli", ROOT / "scripts/run-market-price-service.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    return cli


def args(assets, tmp_path, work_root):
    return ["--config", "examples/market-synthetic.json", "--db", str(tmp_path / "state.sqlite3"), "--assets", str(assets), "--port", str(free_port()), "--image-work-root", str(work_root)]


def work_root(tmp_path):
    root = ROOT / ".tools/image-intake-20261110" / ("task2-owned-" + tmp_path.parent.name + "-" + tmp_path.name)
    root.mkdir(parents=True)
    return root


@pytest.mark.skipif(sys.platform != "win32", reason="optional CLI requires the accepted Windows D2 adapter")
def test_cli_optional_shared_clock_and_startup_urls(assets, tmp_path, monkeypatch, capsys):
    import market.image_decode as decode_module
    cli = cli_module()
    root = work_root(tmp_path)
    captured = []
    real_decoder = ImageDecoder
    def decoder(path, clock):
        captured.append(clock)
        return real_decoder(path, clock)
    monkeypatch.setattr(decode_module, "ImageDecoder", decoder)
    def serve(server):
        assert server.image_intake is not None
        captured.append(server.authority._clock)
        raise KeyboardInterrupt
    from market.local_server import LocalMarketServer
    monkeypatch.setattr(LocalMarketServer, "serve_forever", serve)
    assert cli.main(args(assets, tmp_path, root)) == 0
    output = capsys.readouterr()
    assert "#operator=" in output.out and "#view=" in output.out and "#guest=ig." in output.out
    assert captured[0] is captured[1]
    with closing(ImageDecoder(root, SystemClock())):
        pass


@pytest.mark.parametrize("failure", ["platform", "version", "outside", "stale", "missing"])
def test_cli_optional_preflight_refuses_before_listener(assets, tmp_path, monkeypatch, capsys, failure):
    cli = cli_module()
    root = work_root(tmp_path)
    if failure == "platform":
        monkeypatch.setattr(cli.sys, "platform", "linux")
    elif failure == "version":
        monkeypatch.setattr(cli.sys, "version_info", (3, 12, 13))
    elif failure == "outside":
        root = tmp_path / "outside"
    elif failure == "stale":
        (root / "job").mkdir()
    else:
        root = root / "missing"
    def forbidden(*args, **kwargs):
        pytest.fail("listener opened after invalid optional startup")
    monkeypatch.setattr(cli, "create_server", forbidden)
    assert cli.main(args(assets, tmp_path, root)) == 1
    output = capsys.readouterr()
    assert "#guest=" not in output.out
    if failure in ("platform", "version", "outside"):
        assert not (tmp_path / "state.sqlite3").exists()


def test_cli_optional_helper_import_failure_is_closed_without_payload(assets, tmp_path, monkeypatch, capsys):
    import builtins
    cli = cli_module()
    root = work_root(tmp_path)
    original = builtins.__import__
    def fail(name, *arguments, **keywords):
        if name == "market.image_decode":
            raise RuntimeError("private helper import payload")
        return original(name, *arguments, **keywords)
    monkeypatch.setattr(builtins, "__import__", fail)
    assert cli.main(args(assets, tmp_path, root)) == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == "Market service failed: invalid_startup\n"
    assert not (tmp_path / "state.sqlite3").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="optional CLI requires the accepted Windows D2 adapter")
def test_cli_bind_failure_releases_actual_decoder_and_price_owner(assets, tmp_path, config, clock, capsys):
    cli = cli_module()
    root = work_root(tmp_path)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        assert cli.main(args(assets, tmp_path, root) + ["--port", str(listener.getsockname()[1])]) == 1
    assert "#guest=" not in capsys.readouterr().out
    with open_authority(config, tmp_path / "state.sqlite3", clock):
        pass
    with closing(ImageDecoder(root, SystemClock())):
        pass


@pytest.mark.skipif(sys.platform != "win32", reason="actual D2 Windows Job ownership required")
@pytest.mark.parametrize("approved", [True, False])
def test_actual_http_owned_d2_preview_moderation_expiry(assets, tmp_path, authority, clock, approved):
    root = work_root(tmp_path)
    decoder = ImageDecoder(root, clock)
    intake = ImageIntake(AdmissionController(str(uuid4()), clock), decoder, clock)
    server = create_server(authority, "127.0.0.1", free_port(), assets, image_intake=intake)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    payload = png()
    try:
        status, _, value = request(server, "POST", "/api/images", payload, token(server, "guest"))
        assert status == 202
        item_id = value["image"]["id"]
        deadline = time.monotonic() + 12
        while True:
            image = request(server, path="/api/images/status/" + item_id, bearer=value["status_capability"])[2]
            if image["detail"] != "decoding":
                break
            assert time.monotonic() < deadline
            threading.Event().wait(0.03)
        assert image["detail"] == "awaiting_approval" and image["frame_sha256"] == FRAME
        preview = "/api/images/preview/" + item_id + "/" + FRAME
        assert request(server, path=preview)[2] == RGB
        assert not (root / "job").exists()
        reply = request(server, "POST", "/api/images/moderate/" + item_id, {
            "incarnation": image["incarnation"], "action_id": "actual-safe", "approved": approved,
        })
        assert reply[0] == 200
        assert reply[2]["status"] == ("queued" if approved else "rejected")
        clock.advance(milliseconds=300000)
        final = request(server, path="/api/images/status/" + item_id)[2]
        assert final["status"] == ("expired" if approved else "rejected")
        assert not final["preview_available"] and request(server, path=preview)[0] == 404
        assert request(server, path="/api/snapshot")[2]["price_version"] == 0
        (root / "task2-fixture-evidence.json").write_text(json.dumps({
            "source_sha256": hashlib.sha256(payload).hexdigest(), "encoded_bytes": len(payload),
            "frame_sha256": FRAME, "rgb_bytes": len(RGB), "scratch_removed": True,
            "approved": approved, "final_image": final,
        }), encoding="utf-8")
    finally:
        server.shutdown()
        worker.join(7)
        server.server_close()
    with closing(ImageDecoder(root, clock)):
        pass


@pytest.fixture
def image_children(children, monkeypatch):
    import test_price_process
    # D2's accepted frozen ownership helper imports only the artifact recorder.
    # Every other simulator-package module remains forbidden in this parent.
    allowed = '("fly_connectome_sim", "fly_connectome_sim.experiment", "fly_connectome_sim.experiment.recorder")'
    bootstrap = test_price_process.BOOTSTRAP.replace(
        'if fullname == "fly_connectome_sim" or fullname.startswith("fly_connectome_sim."):',
        'if (fullname == "fly_connectome_sim" or fullname.startswith("fly_connectome_sim.")) and fullname not in ' + allowed + ':',
    ).replace(
        'assert not any(name == "fly_connectome_sim" or name.startswith("fly_connectome_sim.") for name in sys.modules)',
        'assert not any((name == "fly_connectome_sim" or name.startswith("fly_connectome_sim.")) and name not in ' + allowed + ' for name in sys.modules)',
    )
    # The existing child deliberately launches the base interpreter to own its
    # real PID; supply the editable package location without site startup.
    bootstrap = bootstrap.replace('mode = sys.argv[2]', 'sys.path.insert(0, str(Path("src").resolve()))\nmode = sys.argv[2]')
    assert bootstrap != test_price_process.BOOTSTRAP
    monkeypatch.setattr(test_price_process, "BOOTSTRAP", bootstrap)
    return children


def cli_child(children, assets, tmp_path, root):
    child = children("cli", *args(assets, tmp_path, root))
    assert "keine Verkaufspreise" in child.line()
    assert child.line().startswith("Clock: ")
    operator, view, guest = child.line(), child.line(), child.line()
    url = urlsplit(operator)
    server = SimpleNamespace(server_address=(url.hostname, url.port), _host_header=url.netloc,
                             _origin="http://" + url.netloc, operator_url=operator,
                             view_url=view, guest_url=guest)
    return child, server


@pytest.mark.skipif(sys.platform != "win32", reason="actual D2 Windows Job ownership required")
def test_actual_cli_lost_202_keeps_single_receipt_without_resubmission(image_children, assets, tmp_path):
    root = work_root(tmp_path)
    child, server = cli_child(image_children, assets, tmp_path, root)
    payload = png()
    with socket.create_connection(server.server_address, timeout=7) as connection:
        connection.sendall(head(server, length=str(len(payload))) + payload)
        connection.shutdown(socket.SHUT_WR)
        # Intentionally discard the 202: only the original operator can inspect it.
    deadline = time.monotonic() + 12
    while True:
        status, _, state = request(server)
        assert status == 200
        if state["pending"] is not None and state["pending"]["detail"] == "awaiting_approval":
            break
        assert time.monotonic() < deadline
        threading.Event().wait(0.03)
    assert state["receipt_count"] == 1
    image = state["pending"]
    assert request(server, path="/api/images/preview/" + image["id"] + "/" + FRAME)[2] == RGB
    assert request(server, path="/api/snapshot")[2]["price_version"] == 0
    child.stop()
    assert not (root / "job").exists()
    with closing(ImageDecoder(root, SystemClock())):
        pass


@pytest.mark.skipif(sys.platform != "win32", reason="actual D2 Windows Job ownership required")
def test_actual_cli_shutdown_during_receive_closes_owned_resources(image_children, assets, tmp_path, config, clock):
    root = work_root(tmp_path)
    child, server = cli_child(image_children, assets, tmp_path, root)
    with socket.create_connection(server.server_address, timeout=7) as connection:
        connection.sendall(head(server, length="100"))
        deadline = time.monotonic() + 3
        while not request(server)[2]["receiving"]:
            assert time.monotonic() < deadline
            threading.Event().wait(0.01)
        child.stop()
        reply = connection.recv(4096)
        assert reply.startswith(b"HTTP/1.1 408")
    assert not (root / "job").exists()
    with closing(ImageDecoder(root, SystemClock())):
        pass
    with open_authority(config, tmp_path / "state.sqlite3", clock):
        pass


@pytest.mark.skipif(sys.platform != "win32", reason="actual D2 Windows Job ownership required")
def test_actual_owned_decode_shutdown_cancels_joins_and_closes_exact_job(assets, tmp_path, authority, monkeypatch):
    from market import image_decode_windows as adapter
    root = work_root(tmp_path)
    fixture = root / "task2-wait-fixture.py"
    fixture.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    command = adapter._command
    def wait_command(job):
        argv, environment = command(job)
        return argv[:4] + [str(fixture)], environment
    monkeypatch.setattr(adapter, "_command", wait_command)
    entered = threading.Event()
    held = []
    start = adapter.OwnedChild.start
    def observe(child):
        start(child)
        held.append(child)
        entered.set()
    monkeypatch.setattr(adapter.OwnedChild, "start", observe)
    clock = SystemClock()
    decoder = ImageDecoder(root, clock)
    intake = ImageIntake(AdmissionController(str(uuid4()), clock), decoder, clock)
    server = create_server(authority, "127.0.0.1", free_port(), assets, image_intake=intake)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        assert request(server, "POST", "/api/images", png(), token(server, "guest"))[0] == 202
        assert entered.wait(5)
    finally:
        server.shutdown()
        worker.join(7)
        server.server_close()
    assert len(held) == 1 and held[0].drained
    assert held[0].process is None and held[0].job.handle is None
    assert not (root / "job").exists()
    with closing(ImageDecoder(root, clock)):
        pass


@pytest.mark.skipif(sys.platform != "win32", reason="optional CLI requires the accepted Windows D2 adapter")
def test_cli_cleanup_failure_nonzero_retains_owner_and_closes_price(assets, tmp_path, config, clock, monkeypatch, capsys):
    cli = cli_module()
    root = work_root(tmp_path)
    from market.local_server import LocalMarketServer
    monkeypatch.setattr(LocalMarketServer, "serve_forever", lambda server: None)
    close = ImageDecoder.close
    def fail(self):
        raise DecodeError("cleanup_failed")
    monkeypatch.setattr(ImageDecoder, "close", fail)
    assert cli.main(args(assets, tmp_path, root)) == 1
    output = capsys.readouterr()
    assert output.err == "Market service failed: cleanup_failed\n"
    with pytest.raises(DecodeError, match="ownership"):
        ImageDecoder(root, SystemClock())
    with open_authority(config, tmp_path / "state.sqlite3", clock):
        pass
    monkeypatch.setattr(ImageDecoder, "close", close)
    assert cli._unclosed_image_owner is not None
    cli._unclosed_image_owner.finish_close()
    with closing(ImageDecoder(root, SystemClock())):
        pass
