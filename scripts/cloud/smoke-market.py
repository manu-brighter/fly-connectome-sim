"""Exercise the saved loopback start command with a disposable SQLite database.

Run with a Python containing Playwright and system Chromium; no credentials are
written to disk, printed, or included in assertion/Playwright error messages.
This is a synthetic UI check, never a native simulation or image-worker test.
"""

import os
from pathlib import Path
import queue
import signal
import socket
import subprocess
import tempfile
import threading
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[2]


def launch(database):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        ["bash", "scripts/cloud/start.sh", "market", str(port), str(database)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, start_new_session=True,
    )
    lines = queue.Queue()

    def read():
        for line in process.stdout:
            lines.put(line.strip())

    threading.Thread(target=read, daemon=True).start()
    urls = {}
    try:
        while len(urls) < 2:
            line = lines.get(timeout=20)
            if line.startswith("http://127.0.0.1:"):
                fragment = urlsplit(line).fragment
                if fragment.startswith("operator="):
                    urls["operator"] = line
                elif fragment.startswith("view="):
                    urls["view"] = line
        return process, urls, port
    except BaseException:
        stop(process, port)
        raise RuntimeError("Service startup did not provide its two local roles") from None


def stop(process, port):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
    try:
        result = process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        raise RuntimeError("Owned service did not stop within 15 seconds") from None
    if result != 0:
        raise RuntimeError("Service shutdown was not clean")
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError("Service listener remains after shutdown")


def open_board(context, url):
    page = context.new_page()
    page.goto(url)
    expect(page.locator(".market-row")).to_have_count(20)
    assert page.evaluate("location.hash") == ""
    return page


def main():
    with tempfile.TemporaryDirectory(prefix="market-smoke-", dir=ROOT / ".tools/cloud") as work:
        database = Path(work) / "state.sqlite3"
        process, urls, port = launch(database)
        try:
            with sync_playwright() as runtime:
                browser = runtime.chromium.launch(
                    executable_path="/usr/bin/chromium", headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                context = browser.new_context(viewport={"width": 1280, "height": 900})
                page = open_board(context, urls["operator"])
                expect(page.locator(".market-status")).to_contain_text("Pausiert")
                page.get_by_text("Bedienung öffnen / schliessen", exact=True).click()
                page.get_by_role("button", name="Primäre Tafel übernehmen", exact=True).click()
                expect(page.locator(".market-status")).to_contain_text("anwesend", timeout=15000)
                page.get_by_role("button", name="Fortsetzen", exact=True).click()
                expect(page.locator(".market-status")).to_contain_text("Testbetrieb aktiv")
                target = page.get_by_label("Zielpreis in Rappen")
                send = page.get_by_role("button", name="Testvorschlag senden", exact=True)
                target.fill("700")
                send.click()
                expect(page.locator(".market-row").first.locator(".market-amount")).to_have_text("CHF 7.00")
                send.click()
                expect(page.locator(".market-feedback")).to_contain_text("no_change")
                target.fill("400")
                send.click()
                expect(page.locator(".market-feedback")).to_contain_text("cooldown")
                page.get_by_role("button", name="Pausieren", exact=True).click()
                expect(page.locator(".market-status")).to_contain_text("Pausiert")
                mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
                readonly = open_board(mobile, urls["view"])
                expect(readonly.locator(".market-operator")).to_have_count(0)
                assert readonly.evaluate("document.documentElement.scrollWidth <= innerWidth")
                stop(process, port)
                expect(page.locator(".market-status")).to_contain_text("aktuell unbekannt", timeout=15000)
                process, new_urls, port = launch(database)
                assert new_urls["operator"] != urls["operator"]
                restarted = open_board(context, new_urls["operator"])
                expect(restarted.locator(".market-status")).to_contain_text("Pausiert")
                expect(restarted.locator(".market-row").first).to_contain_text("CHF 7.00")
                expect(restarted.locator(".market-row").first).to_contain_text("Sicherheitswartezeit nach Neustart")
                browser.close()
        finally:
            if process.poll() is None:
                stop(process, port)
    print("PASS: saved start; 20 drinks; claim/ACK/resume; CHF4->7; no_change; cooldown; pause; mobile view; disconnect; durable restart/recovery; SIGINT cleanup")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Avoid Playwright call logs containing private opening capabilities.
        print("FAIL: synthetic market smoke check (private URLs suppressed)")
        raise SystemExit(1) from None
