"""Bounded, capability-authenticated loopback transport for synthetic prices."""

from dataclasses import asdict
import hmac
import json
import mimetypes
from pathlib import Path, PurePosixPath
import re
import secrets
import socketserver
import threading
import time

from .fixtures import _decode_json, parse_scenario
from .price_service import MarketError, PriceAuthority


_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; font-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
_STATUS = {
    "invalid_request": 400, "invalid_http": 400, "unauthorized": 401,
    "forbidden_origin": 403, "forbidden_host": 403, "not_found": 404,
    "method_not_allowed": 405, "request_timeout": 408,
    "idempotency_conflict": 409, "wrong_incarnation": 409,
    "primary_busy": 409, "superseded": 409, "length_required": 411,
    "body_too_large": 413, "unsupported_media_type": 415,
    "headers_too_large": 431, "clock": 503, "storage": 503,
    "capacity": 503, "claim_capacity": 503,
}
_PHRASE = {
    200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 408: "Request Timeout",
    409: "Conflict", 411: "Length Required", 413: "Content Too Large",
    415: "Unsupported Media Type", 431: "Request Header Fields Too Large",
    503: "Service Unavailable",
}
_HEADER_NAME = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_ROUTES = {
    "/api/snapshot": ("GET", None),
    "/api/primary/claim": ("POST", {"incarnation", "request_id"}),
    "/api/primary/ack": ("POST", {"session_id", "challenge"}),
    "/api/pause": ("POST", set()),
    "/api/resume": ("POST", {"request_id"}),
    "/api/fixtures": ("POST", {"request_id", "scenario"}),
}


def _validate_bind(host, port):
    if host != "127.0.0.1" or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Local market requires 127.0.0.1 and a port in 1..65535")


def _loopback_endpoint(port):
    # Browsers omit the default HTTP port in Host, Origin and serialized URLs.
    host_header = "127.0.0.1" if port == 80 else f"127.0.0.1:{port}"
    return host_header, "http://" + host_header


def _asset_path(root, relative):
    if not isinstance(relative, str) or "\\" in relative or "%" in relative:
        raise ValueError("Invalid market asset path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or not parts.parts or any(part in (".", "..") for part in relative.split("/")):
        raise ValueError("Invalid market asset path")
    if ":" in relative or "?" in relative or "#" in relative:
        raise ValueError("Invalid market asset path")
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlink market assets are forbidden")
    if not path.is_file() or not path.resolve().is_relative_to(root):
        raise ValueError("Missing or escaped market asset")
    return path


def _load_assets(assets_dir):
    source = Path(assets_dir).absolute()
    for path in (source, *source.parents):
        if path.is_symlink():
            raise ValueError("Symlink asset directory is forbidden")
    root = source.resolve(strict=True)
    manifest_path = _asset_path(root, ".vite/manifest.json")
    try:
        manifest = _decode_json(manifest_path.read_bytes())
    except MarketError:
        raise ValueError("Invalid Vite manifest") from None
    if type(manifest) is not dict or type(manifest.get("market.html")) is not dict:
        raise ValueError("Missing market manifest entry")
    entry = manifest["market.html"]
    if entry.get("isEntry") is not True or entry.get("src") != "market.html":
        raise ValueError("Invalid market manifest entry")
    files = {"market.html"}
    seen = set()
    def visit(key):
        if key in seen:
            return
        seen.add(key)
        record = manifest.get(key)
        if type(record) is not dict or not isinstance(record.get("file"), str):
            raise ValueError("Invalid reachable manifest record")
        if key != "market.html" and record.get("isEntry"):
            raise ValueError("Market assets cannot expose another entry")
        files.add(record["file"])
        for field in ("css", "assets"):
            values = record.get(field, [])
            if type(values) is not list or any(not isinstance(value, str) for value in values):
                raise ValueError("Invalid reachable asset list")
            files.update(values)
        for field in ("imports", "dynamicImports"):
            values = record.get(field, [])
            if type(values) is not list or any(not isinstance(value, str) for value in values):
                raise ValueError("Invalid reachable import list")
            for value in values:
                visit(value)
    visit("market.html")
    result = {}
    for relative in files:
        path = _asset_path(root, relative)
        if relative != "market.html" and (
            not relative.startswith("assets/") or path.suffix.lower() in (".map", ".json", ".html")
        ):
            raise ValueError("Forbidden market asset")
        content_type = mimetypes.guess_type(relative)[0] or "application/octet-stream"
        if path.suffix == ".js":
            content_type = "text/javascript"
        result["/" + relative] = (path.read_bytes(), content_type)
    return result


class _RequestReader:
    """One bounded buffer and one deadline, including progress-making peers."""

    def __init__(self, connection):
        self.connection = connection
        self.deadline = time.monotonic() + 5
        self.buffer = bytearray()

    def receive(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise MarketError("request_timeout")
        self.connection.settimeout(min(2, remaining))
        try:
            chunk = self.connection.recv(4096)
        except TimeoutError:
            raise MarketError("request_timeout") from None
        if time.monotonic() >= self.deadline:
            raise MarketError("request_timeout")
        if not chunk:
            raise MarketError("invalid_http")
        self.buffer.extend(chunk)

    def line(self, limit, error):
        while True:
            if time.monotonic() >= self.deadline:
                raise MarketError("request_timeout")
            end = self.buffer.find(b"\n")
            if end >= 0:
                if end + 1 > limit:
                    raise MarketError(error)
                result = bytes(self.buffer[:end + 1])
                del self.buffer[:end + 1]
                if not result.endswith(b"\r\n"):
                    raise MarketError("invalid_http")
                return result
            if len(self.buffer) >= limit:
                raise MarketError(error)
            self.receive()

    def body(self, length):
        if time.monotonic() >= self.deadline:
            raise MarketError("request_timeout")
        while len(self.buffer) < length:
            self.receive()
        return bytes(self.buffer[:length])


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self._handle_request()
        except MarketError as error:
            self._json({"error": error.code}, _STATUS.get(error.code, 503))
        except (OSError, TimeoutError):
            pass

    def _send(self, data, status, content_type):
        headers = (
            f"HTTP/1.1 {status} {_PHRASE[status]}\r\n"
            f"Content-Length: {len(data)}\r\nContent-Type: {content_type}\r\n"
            "Connection: close\r\nCache-Control: no-store\r\n"
            "X-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\n"
            f"Content-Security-Policy: {_CSP}\r\n\r\n"
        ).encode("ascii")
        try:
            self.request.settimeout(2)
            self.request.sendall(headers + data)
        except OSError:
            pass

    def _json(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":")).encode("utf-8")
        if len(data) > 65536:
            self._send(b'{"error":"capacity"}', 503, "application/json")
            return
        self._send(data, status, "application/json")

    def _handle_request(self):
        reader = _RequestReader(self.request)
        line = reader.line(2048, "invalid_http")
        try:
            method, path, version = line[:-2].decode("ascii").split(" ")
        except (UnicodeError, ValueError):
            raise MarketError("invalid_http") from None
        if version not in ("HTTP/1.1", "HTTP/1.0") or not path.startswith("/") or path.startswith("//"):
            raise MarketError("invalid_http")
        if not re.fullmatch(r"[A-Z]+", method, re.ASCII) or any(not 33 <= ord(char) <= 126 for char in path):
            raise MarketError("invalid_http")
        if any(char in path for char in ("?", "#", "%", "\\")) or any(part in (".", "..") for part in path.split("/")):
            raise MarketError("invalid_http")
        headers = {}
        total = 0
        count = 0
        while True:
            line = reader.line(16384 - total, "headers_too_large")
            total += len(line)
            if line == b"\r\n":
                break
            count += 1
            if count > 64:
                raise MarketError("headers_too_large")
            name, separator, value = line[:-2].partition(b":")
            if not separator or not _HEADER_NAME.fullmatch(name) or any(byte < 32 and byte != 9 or byte == 127 for byte in value):
                raise MarketError("invalid_http")
            key = name.decode("ascii").lower()
            headers.setdefault(key, []).append(value.decode("latin-1").strip(" \t"))
        for key in ("host", "origin", "authorization", "content-length", "content-type", "expect"):
            if len(headers.get(key, [])) > 1:
                raise MarketError("invalid_http")
        if "transfer-encoding" in headers or "expect" in headers:
            raise MarketError("invalid_http")
        if headers.get("host") != [self.server._host_header]:
            raise MarketError("forbidden_host")
        if "origin" in headers and headers["origin"] != [self.server._origin]:
            raise MarketError("forbidden_origin")
        if method == "POST" and headers.get("origin") != [self.server._origin]:
            raise MarketError("forbidden_origin")
        if method not in ("GET", "POST"):
            raise MarketError("method_not_allowed")
        lengths = headers.get("content-length", [])
        if lengths and not re.fullmatch(r"0|[1-9][0-9]*", lengths[0], re.ASCII):
            raise MarketError("invalid_http")
        if lengths and (len(lengths[0]) > 4 or int(lengths[0]) > 8192):
            raise MarketError("body_too_large")
        length = int(lengths[0]) if lengths else 0
        if method == "GET" and length:
            raise MarketError("invalid_http")
        if method == "POST":
            if not lengths:
                raise MarketError("length_required")
            if headers.get("content-type") != ["application/json"]:
                raise MarketError("unsupported_media_type")
        if path in self.server._assets:
            if method != "GET":
                raise MarketError("method_not_allowed")
            data, content_type = self.server._assets[path]
            self._send(data, 200, content_type)
            return
        event_route = path.startswith("/api/events/") and path.count("/") == 3 and bool(path[12:])
        route = ("GET", None) if event_route else _ROUTES.get(path)
        if route is None:
            raise MarketError("not_found")
        if method != route[0]:
            raise MarketError("method_not_allowed")
        credential = headers.get("authorization", [""])[0]
        if not credential.startswith("Bearer ") or not credential[7:]:
            raise MarketError("unauthorized")
        bearer = credential[7:]
        role, session = self.server._authenticate(bearer)
        if method == "POST" and (role != ("primary" if path == "/api/primary/ack" else "operator")):
            raise MarketError("unauthorized")
        # Capture before a possibly slow body read or authority-lock wait.
        epoch = self.server.authority.capture_safety_epoch() if path == "/api/resume" else None
        payload = None
        if method == "POST":
            payload = _decode_json(reader.body(length))
            if type(payload) is not dict or set(payload) != route[1]:
                raise MarketError("invalid_request")
        authority = self.server.authority
        if path == "/api/snapshot":
            reply = authority.snapshot(session)
        elif event_route:
            reply = authority.get_event(path[12:])
        elif path == "/api/primary/claim":
            reply = authority.claim_primary(payload["incarnation"], payload["request_id"])
        elif path == "/api/primary/ack":
            if payload["session_id"] != session:
                raise MarketError("unauthorized")
            reply = authority.ack_primary(session, payload["challenge"])
        elif path == "/api/pause":
            safety_epoch = authority.request_safety_pause("operator_pause")
            reply = authority.pause(safety_epoch=safety_epoch)
        elif path == "/api/resume":
            reply = authority.resume(payload["request_id"], ingress_epoch=epoch)
        else:
            reply = authority.run_fixture(payload["request_id"], parse_scenario(payload["scenario"]))
        self._json(asdict(reply))


class LocalMarketServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Eight handlers, a separate maintenance tick and explicit ownership close."""

    allow_reuse_address = False
    daemon_threads = False
    block_on_close = True

    def __init__(self, authority, host, port, assets):
        self.authority = authority
        self._assets = assets
        self._slots = threading.BoundedSemaphore(8)
        self._stop_maintenance = threading.Event()
        self._maintenance_thread = None
        self._operator_token = secrets.token_urlsafe(32)
        self._view_token = secrets.token_urlsafe(32)
        while self._view_token == self._operator_token:
            self._view_token = secrets.token_urlsafe(32)
        self._host_header, self._origin = _loopback_endpoint(port)
        super().__init__((host, port), _Handler)

    @property
    def operator_url(self) -> str:
        return f"{self._origin}/market.html#operator={self._operator_token}"

    @property
    def view_url(self) -> str:
        return f"{self._origin}/market.html#view={self._view_token}"

    def _authenticate(self, token):
        # compare_digest(str, str) rejects non-ASCII input; bytes are total here.
        supplied = token.encode("utf-8")
        if hmac.compare_digest(supplied, self._operator_token.encode("ascii")):
            return "operator", None
        if hmac.compare_digest(supplied, self._view_token.encode("ascii")):
            return "view", None
        session = self.authority.resolve_primary_token(token)
        if session is None:
            raise MarketError("unauthorized")
        return "primary", session

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.authority.request_safety_pause("overload")
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            self.shutdown_request(request)
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()

    def handle_error(self, request, client_address):
        # No stock tracebacks: they can include a request or application payload.
        pass

    def _maintain(self):
        while not self._stop_maintenance.wait(0.1):
            try:
                self.authority.maintain()
            except MarketError:
                pass

    def serve_forever(self, poll_interval=0.1):
        self._maintenance_thread = threading.Thread(target=self._maintain, name="market-maintenance")
        self._maintenance_thread.start()
        try:
            super().serve_forever(poll_interval=poll_interval)
        finally:
            self._stop_maintenance.set()
            self._maintenance_thread.join()

    def server_close(self):
        self._stop_maintenance.set()
        super().server_close()
        if self._maintenance_thread is not None:
            self._maintenance_thread.join()
        self.authority.close()


def create_server(authority: PriceAuthority, host: str, port: int,
                  assets_dir: Path) -> LocalMarketServer:
    _validate_bind(host, port)
    assets = _load_assets(assets_dir)
    return LocalMarketServer(authority, host, port, assets)
