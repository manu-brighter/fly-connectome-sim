"""Real child-process ownership/recovery; no simulator imports or long sleeps."""

from dataclasses import asdict
import http.client
import json
import os
from pathlib import Path
import queue
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

import pytest

from market.price_service import open_authority

from conftest import make_present, scenario


ROOT = Path(__file__).resolve().parents[2]
SCENARIO = {"fixture_id": "synthetic-price-v1", "drink_id": "drink-00",
            "target_rappen": 700, "expected_drink_version": 0}
BOOTSTRAP = r'''
import atexit
import importlib.abc
import json
import os
from pathlib import Path
import sys

marker = Path(sys.argv[1])
class NoNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "fly_connectome_sim" or fullname.startswith("fly_connectome_sim."):
            marker.write_text(fullname, encoding="utf-8")
            raise AssertionError("native package import forbidden in market process")
sys.meta_path.insert(0, NoNative())
def check_imports():
    assert not any(name == "fly_connectome_sim" or name.startswith("fly_connectome_sim.") for name in sys.modules)
atexit.register(check_imports)
print(json.dumps({"pid": os.getpid(), "executable": sys.executable}), flush=True)
mode = sys.argv[2]
args = sys.argv[3:]
if mode == "cli":
    import _thread
    import runpy
    import threading
    # Exercise the real CLI's KeyboardInterrupt/finally path without requiring
    # an attached Windows console or changing production signal handling.
    def stop_on_command():
        if sys.stdin.readline().strip() == "stop":
            _thread.interrupt_main()
    threading.Thread(target=stop_on_command, daemon=True).start()
    sys.argv = ["scripts/run-market-price-service.py", *args]
    runpy.run_path(sys.argv[0], run_name="__main__")
elif mode == "crash":
    from dataclasses import asdict
    from market.fixtures import load_config
    from market.price_service import FixtureScenario, open_authority
    authority = open_authority(load_config(Path("examples/market-synthetic.json")), Path(args[0]))
    claim = authority.claim_primary(authority.snapshot().incarnation, "claim")
    challenge = authority.snapshot(claim.session_id).challenge
    assert authority.ack_primary(claim.session_id, challenge.id).accepted
    assert authority.resume("resume", ingress_epoch=authority.capture_safety_epoch()).result.status == "accepted"
    before = asdict(authority.snapshot())
    def committed_before_anchor(drink_id):
        assert not authority._db.in_transaction
        assert drink_id not in authority._deadlines
        result = json.loads(authority._db.execute("SELECT result_json FROM proposal_results").fetchone()[0])
        assert authority._db.execute("SELECT count(*) FROM activations").fetchone()[0] == 1
        print(json.dumps({"barrier": "committed-before-anchor", "before": before, "result": result}), flush=True)
        sys.stdin.readline()  # Parent kills only this owned child at the barrier.
        raise AssertionError("crash barrier unexpectedly released")
    authority._anchor_committed_activation = committed_before_anchor
    authority.run_fixture("crash-request", FixtureScenario("synthetic-price-v1", "drink-00", 700, 0))
elif mode == "sentinel":
    print("sentinel-ready", flush=True)
    assert sys.stdin.readline().strip() == "stop"
else:
    raise AssertionError("unknown test mode")
'''


class Child:
    def __init__(self, marker, mode, args):
        self.marker = marker
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONUTF8="1")
        # Windows' venv python.exe is a redirector with a second interpreter PID.
        # These children need only stdlib and repository-local market modules;
        # launch the real interpreter so terminate/kill owns the actual authority.
        executable = getattr(sys, "_base_executable", sys.executable)
        self.process = subprocess.Popen(
            [executable, "-u", "-c", BOOTSTRAP, str(marker), mode, *map(str, args)],
            cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        self.lines = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.executable = executable

    def _read(self):
        for line in self.process.stdout:
            self.lines.put(line.strip())
        self.lines.put(None)

    def line(self):
        value = self.lines.get(timeout=10)
        assert value is not None, "child exited before readiness"
        return value

    def stop(self):
        self.process.stdin.write("stop\n")
        self.process.stdin.flush()
        assert self.process.wait(timeout=10) == 0


@pytest.fixture
def children(tmp_path):
    owned = []
    def spawn(mode, *args):
        child = Child(tmp_path / f"native-import-{len(owned)}", mode, args)
        owned.append(child)
        identity = json.loads(child.line())
        assert identity["pid"] == child.process.pid
        assert Path(identity["executable"]).resolve() == Path(child.executable).resolve()
        return child
    yield spawn
    started = time.monotonic()
    deadline = started + 14
    for child in owned:
        if child.process.poll() is None:
            child.process.terminate()
    for child in owned:
        try:
            child.process.wait(timeout=min(5, max(0, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            child.process.kill()
            child.process.wait(timeout=max(0, deadline - time.monotonic()))
        child.reader.join(timeout=max(0, deadline - time.monotonic()))
        for pipe in (child.process.stdin, child.process.stdout):
            pipe.close()
        assert not child.reader.is_alive()
        assert not child.marker.exists(), "market child attempted a native package import"
    assert time.monotonic() - started < 15


@pytest.fixture
def assets(tmp_path):
    root = tmp_path / "dist"
    (root / ".vite").mkdir(parents=True)
    (root / "assets").mkdir()
    (root / "market.html").write_text('<script type="module" src="/assets/market.js"></script>', encoding="utf-8")
    (root / "assets" / "market.js").write_text("// synthetic process test", encoding="utf-8")
    (root / ".vite" / "manifest.json").write_text(json.dumps({
        "market.html": {"file": "assets/market.js", "isEntry": True, "src": "market.html"},
    }), encoding="utf-8")
    return root


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def cli(children, db, assets, *, port=None, ready=True):
    child = children("cli", "--config", "examples/market-synthetic.json", "--db", db,
                     "--host", "127.0.0.1", "--port", port or free_port(), "--assets", assets)
    if ready:
        assert "keine Verkaufspreise" in child.line()
        assert child.line().startswith("Clock: ")
        child.operator_url = child.line()
        child.view_url = child.line()
        assert "#operator=" in child.operator_url and "#view=" in child.view_url
    return child


def request(child, method="GET", path="/api/snapshot", body=None, bearer=None):
    url = urlsplit(child.operator_url)
    headers = {"Origin": f"http://{url.netloc}",
               "Authorization": "Bearer " + (bearer or url.fragment.split("=", 1)[1])}
    if body is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(body).encode("utf-8")
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=6)
    try:
        connection.request(method, path, body, headers)
        reply = connection.getresponse()
        result = json.loads(reply.read())
        assert reply.status == 200, result
        return result
    finally:
        connection.close()


def present_and_resume(child):
    snapshot = request(child)
    claim = request(child, "POST", "/api/primary/claim", {
        "incarnation": snapshot["incarnation"], "request_id": "claim",
    })
    snapshot = request(child, bearer=claim["primary_token"])
    ack = request(child, "POST", "/api/primary/ack", {
        "session_id": claim["session_id"], "challenge": snapshot["challenge"]["id"],
    }, bearer=claim["primary_token"])
    assert ack["accepted"]
    assert request(child, "POST", "/api/resume", {"request_id": "resume"})["result"]["status"] == "accepted"


@pytest.mark.parametrize("stop", ["normal", "killed"])
def test_cli_cross_process_ownership_and_release(children, assets, tmp_path, stop):
    sentinel = children("sentinel")
    assert sentinel.line() == "sentinel-ready"
    db = tmp_path / "ownership.sqlite3"
    owner = cli(children, db, assets)
    first = request(owner)
    competitor = cli(children, db, assets, ready=False)
    assert competitor.line() == "Market service failed: ownership"
    assert competitor.process.wait(timeout=10) == 1
    lock = db.with_name(db.name + ".owner.lock")
    identity = lock.stat().st_ino
    if stop == "normal":
        owner.stop()
    else:
        owner.process.kill()
        assert owner.process.wait(timeout=10) != 0
    assert sentinel.process.poll() is None
    assert lock.exists() and lock.stat().st_ino == identity
    reopened = cli(children, db, assets)
    second = request(reopened)
    assert second["incarnation"] != first["incarnation"]
    assert second["paused"] and second["primary_state"] == "unclaimed"
    assert second["price_version"] == first["price_version"] == 0
    assert all(row["current_rappen"] == 400 and row["drink_version"] == 0 for row in second["rows"])
    assert lock.stat().st_ino == identity
    reopened.stop()
    assert sentinel.process.poll() is None
    sentinel.stop()


def test_crash_after_real_commit_before_anchor_recovers_full_lock(children, tmp_path, config, clock):
    db = tmp_path / "commit-crash.sqlite3"
    child = children("crash", db)
    barrier = json.loads(child.line())
    assert barrier["barrier"] == "committed-before-anchor"
    original = barrier["result"]
    assert original["status"] == "activated"
    # Independently observe a committed transaction while the child is still
    # blocked before anchoring, rather than trusting its readiness text alone.
    with sqlite3.connect(db) as check:
        assert check.execute("SELECT count(*) FROM activations").fetchone()[0] == 1
        assert json.loads(check.execute("SELECT result_json FROM proposal_results").fetchone()[0]) == original
    child.process.kill()
    assert child.process.wait(timeout=10) != 0
    with open_authority(config, db, clock) as reopened:
        snapshot = reopened.snapshot()
        assert snapshot.incarnation != barrier["before"]["incarnation"]
        assert snapshot.generation > barrier["before"]["generation"]
        assert snapshot.paused and snapshot.primary_state == "unclaimed"
        row = snapshot.rows[0]
        assert (row.current_rappen, row.drink_version, row.last_activation_id) == (700, 1, original["activation_id"])
        assert snapshot.price_version == original["terminal_price_version"] == 1
        assert row.recovery_lock and row.remaining_lock_ms == 1_800_000
        assert all(item.remaining_lock_ms == 0 and not item.recovery_lock for item in snapshot.rows[1:])
        assert asdict(reopened.get_event(original["event_id"])) == original
        assert asdict(reopened.run_fixture("crash-request", scenario())) == original
        make_present(reopened)
        assert reopened.run_fixture("fresh-before-recovery", scenario(target=400, version=1)).reason == "cooldown"
        assert reopened.snapshot().price_version == 1


def test_lost_http_result_restart_reuses_original_request(children, assets, tmp_path):
    db = tmp_path / "lost-result.sqlite3"
    child = cli(children, db, assets)
    present_and_resume(child)
    before = request(child)
    payload = json.dumps({"request_id": "lost-request", "scenario": SCENARIO}).encode("utf-8")
    url = urlsplit(child.operator_url)
    headers = (f"POST /api/fixtures HTTP/1.1\r\nHost: {url.netloc}\r\n"
               f"Origin: http://{url.netloc}\r\nAuthorization: Bearer {url.fragment.split('=', 1)[1]}\r\n"
               f"Content-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n").encode("ascii")
    with socket.create_connection((url.hostname, url.port), timeout=6) as connection:
        connection.sendall(headers + payload)
        connection.shutdown(socket.SHUT_WR)
        # Never read a response. A separate connection observes the durable result.
        deadline = time.monotonic() + 8
        while True:
            snapshot = request(child)
            if snapshot["price_version"] == 1:
                break
            assert time.monotonic() < deadline, "fixture never committed"
            threading.Event().wait(0.01)
    event_id = snapshot["rows"][0]["last_activation_id"]
    with sqlite3.connect(db) as check:
        original = json.loads(check.execute("SELECT result_json FROM proposal_results").fetchone()[0])
        assert original["activation_id"] == event_id
        counts = tuple(check.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                       for table in ("fixture_requests", "proposal_results", "activations"))
    child.stop()
    restarted = cli(children, db, assets)
    current = request(restarted)
    assert current["incarnation"] != before["incarnation"] and current["paused"]
    assert current["rows"][0]["recovery_lock"]
    assert 1_790_000 <= current["rows"][0]["remaining_lock_ms"] <= 1_800_000
    assert restarted.operator_url != child.operator_url
    retry = request(restarted, "POST", "/api/fixtures", {"request_id": "lost-request", "scenario": SCENARIO})
    assert retry == original
    assert request(restarted, path="/api/events/" + original["event_id"]) == original
    assert request(restarted)["price_version"] == current["price_version"] == 1
    with sqlite3.connect(db) as check:
        assert tuple(check.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                     for table in ("fixture_requests", "proposal_results", "activations")) == counts == (1, 1, 1)
    restarted.stop()
