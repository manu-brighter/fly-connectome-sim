"""One bounded image in an owned child; never decodes pixels in this process."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import threading
import time
from uuid import UUID

from .ownership import DatabaseOwnership
from .price_service import Clock, ClockSample, SystemClock


ROOT = Path(__file__).absolute().parents[1]
MAX_NS = 2 ** 63 - 1
MAX_SOURCE = 2_097_152
DECODE_NS = 10_000_000_000
FRAME_PREFIX = b'{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n'
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_REJECTIONS = ("malformed_image", "unsupported_format", "geometry", "mode", "multiple_frames", "source_mismatch")
_ERRORS = (
    "invalid_request", "busy", "closed", "unsupported_platform", "ownership", "timeout",
    "cancelled", "clock", *_REJECTIONS, "child_failed", "child_protocol", "memory_limit",
    "monitor_stalled", "cleanup_failed",
)


class DecodeError(Exception):
    def __init__(self, code):
        self.code = code if type(code) is str and code in _ERRORS else "invalid_request"
        super().__init__(self.code)


def _integer(value, low=0, high=MAX_NS):
    return type(value) is int and low <= value <= high


def _uuid(value):
    if type(value) is not str or len(value) != 36:
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _require(condition, code="invalid_request"):
    if not condition:
        raise DecodeError(code)


def _geometry(width, height):
    return (_integer(width, 1, 8192) and _integer(height, 1, 8192)
            and width * height <= 12_000_000)


@dataclass(frozen=True, slots=True)
class DecodeRequest:
    incarnation: str
    id: str
    source_sha256: str
    encoded_bytes: int
    media_type: str
    accepted_ns: int
    decode_deadline_ns: int

    def __post_init__(self):
        _require(type(self) is DecodeRequest)
        _require(_uuid(self.incarnation) and _uuid(self.id) and _digest(self.source_sha256))
        _require(_integer(self.encoded_bytes, 1, MAX_SOURCE))
        _require(type(self.media_type) is str and self.media_type in ("image/jpeg", "image/png"))
        _require(_integer(self.accepted_ns, 0, MAX_NS - DECODE_NS))
        _require(_integer(self.decode_deadline_ns) and self.decode_deadline_ns == self.accepted_ns + DECODE_NS)


@dataclass(frozen=True, slots=True)
class DecodedImage:
    incarnation: str
    id: str
    source_sha256: str
    frame_sha256: str
    preprocessing_version: str
    rgb: bytes
    source_width: int
    source_height: int
    oriented_width: int
    oriented_height: int
    format: str
    completed_ns: int
    observed_peak_working_set_bytes: int

    def __post_init__(self):
        _require(type(self) is DecodedImage)
        _require(_uuid(self.incarnation) and _uuid(self.id) and _digest(self.source_sha256))
        _require(_digest(self.frame_sha256) and type(self.rgb) is bytes and len(self.rgb) == 12288)
        _require(type(self.preprocessing_version) is str and self.preprocessing_version == "market-rgb64/v1")
        _require(_geometry(self.source_width, self.source_height))
        _require(_geometry(self.oriented_width, self.oriented_height))
        _require((self.oriented_width, self.oriented_height) in (
            (self.source_width, self.source_height), (self.source_height, self.source_width),
        ))
        _require(type(self.format) is str and self.format in ("JPEG", "PNG"))
        _require(_integer(self.completed_ns) and _integer(self.observed_peak_working_set_bytes, 0, 536870912))
        _require(hashlib.sha256(FRAME_PREFIX + self.rgb).hexdigest() == self.frame_sha256)


def _safe_directory(path):
    for component in (path, *path.parents):
        state = component.stat(follow_symlinks=False)
        if (not stat.S_ISDIR(state.st_mode) or component.is_symlink()
                or getattr(state, "st_file_attributes", 0) & 0x400):
            raise DecodeError("ownership")
    return path.stat(follow_symlinks=False)


def _identity(state):
    return state.st_dev, state.st_ino


def _ordinary(path):
    state = path.stat(follow_symlinks=False)
    if (not stat.S_ISREG(state.st_mode) or path.is_symlink()
            or getattr(state, "st_file_attributes", 0) & 0x400):
        raise DecodeError("ownership")
    return state


def _new_child(job):
    return _WINDOWS.OwnedChild(job)


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _protocol(data, request):
    """Validate the complete, EOF-terminated wire without trusting child metadata."""
    try:
        _require(4 <= len(data) <= 14340, "child_protocol")
        size = struct.unpack_from("<I", data)[0]
        _require(1 <= size <= 2048 and len(data) >= 4 + size, "child_protocol")
        def nonfinite(_):
            raise ValueError("nonfinite number")
        header = json.loads(data[4:4 + size].decode("utf-8"), object_pairs_hook=_pairs, parse_constant=nonfinite)
        _require(type(header) is dict, "child_protocol")
        common = {"schema", "incarnation", "id", "source_sha256", "status"}
        _require(header.get("schema") == "market-image-decode-result/v1", "child_protocol")
        for name in ("incarnation", "id", "source_sha256"):
            _require(type(header.get(name)) is str and header[name] == getattr(request, name), "child_protocol")
        if header.get("status") == "rejected":
            _require(set(header) == common | {"reason"}, "child_protocol")
            _require(type(header["reason"]) is str and header["reason"] in _REJECTIONS, "child_protocol")
            _require(len(data) == 4 + size, "child_protocol")
            return header["reason"], None
        _require(header.get("status") == "decoded", "child_protocol")
        keys = {"preprocessing_version", "frame_sha256", "source_width", "source_height",
                "oriented_width", "oriented_height", "format"}
        _require(set(header) == common | keys and len(data) == 4 + size + 12288, "child_protocol")
        _require(header["preprocessing_version"] == "market-rgb64/v1" and _digest(header["frame_sha256"]), "child_protocol")
        _require(_geometry(header["source_width"], header["source_height"]), "child_protocol")
        _require(_geometry(header["oriented_width"], header["oriented_height"]), "child_protocol")
        _require((header["oriented_width"], header["oriented_height"]) in (
            (header["source_width"], header["source_height"]),
            (header["source_height"], header["source_width"]),
        ), "child_protocol")
        _require(header["format"] == ("PNG" if request.media_type == "image/png" else "JPEG"), "child_protocol")
        rgb = bytes(data[4 + size:])
        _require(hashlib.sha256(FRAME_PREFIX + rgb).hexdigest() == header["frame_sha256"], "child_protocol")
        return None, {key: header[key] for key in keys} | {"rgb": rgb}
    except (ValueError, UnicodeError, TypeError, struct.error, KeyError, RecursionError):
        raise DecodeError("child_protocol") from None


class ImageDecoder:
    def __init__(self, work_root: Path, clock: Clock | None = None):
        self._lock = threading.Lock()
        self._busy = self._closed = self._cleanup_fault = self._clock_fault = False
        self._owned = None
        self._job_identity = None
        self._job_created = False
        self._files = {}
        self._last_ns = None
        self._clock = SystemClock() if clock is None else clock
        self._ownership = None
        try:
            _require(isinstance(work_root, Path), "ownership")
            self._root = work_root.absolute()
            _require(self._root.is_relative_to(ROOT / ".tools") and self._root != ROOT / ".tools", "ownership")
            self._root_identity = _identity(_safe_directory(self._root))
            _require(self._root.resolve() == self._root, "ownership")
            self._job_path = self._root / "job"
            _require(not os.path.lexists(self._job_path), "ownership")
            lock_path = self._root / "decoder.owner.lock"
            if os.path.lexists(lock_path):
                _ordinary(lock_path)
            self._ownership = DatabaseOwnership(self._root / "decoder")
            _require(_identity(_ordinary(lock_path)) == _identity(os.fstat(self._ownership._file.fileno())), "ownership")
            _require(not os.path.lexists(self._job_path), "ownership")
        except BaseException as error:
            if self._ownership is not None:
                self._ownership.close()
            if isinstance(error, (KeyboardInterrupt, SystemExit)):
                raise
            raise DecodeError("ownership") from None

    def _sample(self):
        try:
            sample = self._clock.sample()
            if type(sample) is not ClockSample:
                raise ValueError("invalid clock")
            now = sample.monotonic_ns
            if (not _integer(now) or self._last_ns is not None and now < self._last_ns):
                raise ValueError("invalid clock")
            self._last_ns = now
            return now
        except Exception:
            with self._lock:
                self._clock_fault = True
            raise DecodeError("clock") from None

    def _check_root(self):
        _require(_identity(_safe_directory(self._root)) == self._root_identity, "ownership")

    def _scratch(self, request, payload):
        self._check_root()
        self._job_path.mkdir()
        self._job_created = True
        self._job_identity = _identity(_safe_directory(self._job_path))
        record = {name: getattr(request, name) for name in ("incarnation", "id", "source_sha256", "encoded_bytes", "media_type")}
        record["schema"] = "market-image-decode/v1"
        encoded = json.dumps(record, separators=(",", ":"), allow_nan=False).encode("utf-8")
        _require(len(encoded) <= 2048, "invalid_request")
        for name, content in (("request.json", encoded), ("input.bin", payload)):
            path = self._job_path / name
            with path.open("xb") as stream:
                self._files[name] = _identity(os.fstat(stream.fileno()))
                stream.write(content)
                _require(_identity(_ordinary(path)) == self._files[name], "ownership")

    def _inventory(self):
        self._check_root()
        _require(_identity(_safe_directory(self._job_path)) == self._job_identity, "ownership")
        names = {path.name for path in self._job_path.iterdir()}
        _require(names == set(self._files), "ownership")
        for name, identity in self._files.items():
            state = _ordinary(self._job_path / name)
            _require(_identity(state) == identity, "ownership")
            _require(state.st_size <= (2048 if name == "request.json" else MAX_SOURCE), "ownership")

    def _cleanup(self):
        # Keep this exact context even if a later close fails. No PID recovery.
        if self._owned is not None:
            self._owned.cleanup()
        if self._job_created:
            _require(self._job_identity is not None, "ownership")
            self._inventory()
            for name in tuple(self._files):
                (self._job_path / name).unlink()
                del self._files[name]
            self._job_path.rmdir()
            self._job_identity = None
            self._job_created = False
        self._owned = None

    def decode(self, *, request: DecodeRequest, payload: bytes, cancel: threading.Event | None = None) -> DecodedImage:
        with self._lock:
            for condition, code in ((self._closed, "closed"), (self._busy, "busy"),
                                    (self._cleanup_fault, "ownership"), (self._clock_fault, "clock")):
                if condition:
                    raise DecodeError(code)
            _require(type(request) is DecodeRequest and type(payload) is bytes)
            # Copy scalar slots before any call out to caller-supplied clock/Event.
            try:
                request = DecodeRequest(request.incarnation, request.id, request.source_sha256,
                                        request.encoded_bytes, request.media_type, request.accepted_ns, request.decode_deadline_ns)
            except AttributeError:
                raise DecodeError("invalid_request") from None
            _require(len(payload) == request.encoded_bytes)
            _require(cancel is None or type(cancel) is threading.Event)
            self._busy = True
        failure = interrupt = candidate = None
        peak = 0
        completed_ns = None
        try:
            now = self._sample()
            _require(request.accepted_ns <= now, "invalid_request")
            _require(now < request.decode_deadline_ns, "timeout")
            _require(hashlib.sha256(payload).hexdigest() == request.source_sha256, "source_mismatch")
            if cancel is not None and cancel.is_set():
                raise DecodeError("cancelled")
            self._scratch(request, payload)
            self._owned = _new_child(self._job_path)
            self._owned.start()
            data = bytearray()
            previous = now
            while True:
                poll_error = None
                try:
                    observation = self._owned.poll(min(4096, 14341 - len(data)))
                except Exception as error:
                    poll_error = error
                now = self._sample()
                cancelled = cancel is not None and cancel.is_set()
                _require(not cancelled, "cancelled")
                _require(now < request.decode_deadline_ns, "timeout")
                _require(now - previous <= 250_000_000, "monitor_stalled")
                previous = now
                if poll_error is not None:
                    raise DecodeError(poll_error.code if type(poll_error) is DecodeError else "ownership")
                block, eof, exited, exit_code, sampled_peak, extra_children = observation
                peak = max(peak, sampled_peak)
                _require(peak <= 536870912, "memory_limit")
                _require(not extra_children, "child_protocol")
                _require(type(block) is bytes and len(block) <= 4096 and len(data) + len(block) <= 14340, "child_protocol")
                data.extend(block)
                if len(data) >= 4:
                    _require(1 <= struct.unpack_from("<I", data)[0] <= 2048, "child_protocol")
                try:
                    self._inventory()
                except (DecodeError, OSError):
                    raise DecodeError("child_protocol") from None
                if eof and exited:
                    validation_ns = self._sample()
                    _require(cancel is None or not cancel.is_set(), "cancelled")
                    _require(validation_ns < request.decode_deadline_ns, "timeout")
                    if not data and exit_code != 0:
                        raise DecodeError("child_failed")
                    failure, candidate = _protocol(data, request)
                    if exit_code != 0:
                        failure, candidate = "child_failed", None
                    break
                # Even a failed process can leave buffered bytes. The next
                # available-byte poll establishes EOF before protocol/exit
                # precedence, under the same deadline and resource budgets.
                time.sleep(0.02)
        except DecodeError as error:
            failure = error.code
        except (KeyboardInterrupt, SystemExit) as error:
            interrupt = error
        except Exception:
            failure = "ownership" if self._owned is None else "child_failed"
        except BaseException as error:
            interrupt = error
        finally:
            try:
                self._cleanup()
            except BaseException:
                with self._lock:
                    self._cleanup_fault = True
                failure = "cleanup_failed"
                candidate = None
            # A newly broken post-cleanup clock latches even after an earlier error.
            if not self._clock_fault:
                try:
                    completed_ns = self._sample()
                except DecodeError:
                    if failure is None and interrupt is None:
                        failure = "clock"
                except BaseException as error:
                    if interrupt is None:
                        interrupt = error
            # Last event read is the cancellation cutoff. No blocking I/O follows.
            with self._lock:
                try:
                    cancelled = cancel is not None and cancel.is_set()
                    if failure is None and interrupt is None:
                        if self._clock_fault:
                            failure = "clock"
                        elif cancelled:
                            failure = "cancelled"
                        elif completed_ns >= request.decode_deadline_ns:
                            failure = "timeout"
                except BaseException as error:
                    if interrupt is None:
                        interrupt = error
                finally:
                    self._busy = False
        if failure is not None:
            raise DecodeError(failure)
        if interrupt is not None:
            raise interrupt
        return DecodedImage(incarnation=request.incarnation, id=request.id, source_sha256=request.source_sha256,
                            completed_ns=completed_ns, observed_peak_working_set_bytes=peak, **candidate)

    def close(self):
        with self._lock:
            if self._closed:
                return
            if self._busy:
                raise DecodeError("busy")
            self._busy = True
        try:
            self._cleanup()
            self._ownership.close()
            self._ownership = None
            with self._lock:
                self._closed = True
        except BaseException:
            with self._lock:
                self._cleanup_fault = True
            raise DecodeError("cleanup_failed") from None
        finally:
            with self._lock:
                self._busy = False


# Resolve and verify the fixed helper imports at controller-module startup,
# before a service can start worker threads. No Pillow/engine is imported here.
from . import image_decode_windows as _WINDOWS
