"""Portable parent contract tests; synthetic adapters do not attest OS ownership."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
import threading
import types

import pytest

import market.image_decode as module
from market.image_decode import DecodeError, DecodeRequest, DecodedImage, ImageDecoder
from market.price_service import ClockSample


ROOT = Path(__file__).resolve().parents[2]
INC = "00000000-0000-4000-8000-000000000001"
ID = "00000000-0000-4000-8000-000000000002"
PAYLOAD = b"trusted fixture source"
SOURCE = hashlib.sha256(PAYLOAD).hexdigest()
RGB = b"\xff\x00\x00" * 4096
# Independently stated protocol prefix, not the implementation's hash helper.
FRAME = hashlib.sha256(b'{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n' + RGB).hexdigest()


class Clock:
    def __init__(self):
        self.ns = 100
        self.failure = None
        self.calls = 0

    def sample(self):
        self.calls += 1
        if self.failure:
            raise self.failure
        return ClockSample(self.ns, datetime(2026, 11, 10, tzinfo=timezone.utc))


def request(**changes):
    return replace(DecodeRequest(INC, ID, SOURCE, len(PAYLOAD), "image/png", 100, 10_000_000_100), **changes)


def header(**changes):
    result = dict(schema="market-image-decode-result/v1", incarnation=INC, id=ID,
                  source_sha256=SOURCE, status="decoded", preprocessing_version="market-rgb64/v1",
                  frame_sha256=FRAME, source_width=2, source_height=1,
                  oriented_width=2, oriented_height=1, format="PNG")
    result.update(changes)
    return result


def wire(value=None, rgb=RGB):
    raw = json.dumps(header() if value is None else value, separators=(",", ":")).encode()
    return struct.pack("<I", len(raw)) + raw + rgb


class Child:
    """Only the OS boundary is synthetic; controller/files/clock/wire remain real."""
    def __init__(self, job):
        self.job_path = job
        self.data = bytearray(wire())
        self.peak = 12345
        self.code = 0
        self.children = False
        self.eof = False
        self.cleaned = False
        self.cleanup_hook = None
        self.poll_hook = None
        self.start_hook = None
        self.cleanup_failure = False

    def start(self):
        if self.start_hook:
            self.start_hook()

    def poll(self, max_bytes=4096):
        if self.poll_hook:
            self.poll_hook()
        block = bytes(self.data[:max_bytes])
        del self.data[:max_bytes]
        self.eof = not self.data
        return block, self.eof, True, self.code, self.peak, self.children

    def cleanup(self):
        if self.cleanup_hook:
            self.cleanup_hook()
        if self.cleanup_failure:
            raise OSError("fixture drain unresolved")
        self.cleaned = True


@pytest.fixture
def parent(tmp_path, monkeypatch):
    # Work roots must really be under .tools, even in portable controller tests.
    base = ROOT / ".tools/image-decoding-20261110" / f"{tmp_path.parent.name}-{tmp_path.name}"
    base.mkdir(parents=True)
    clock = Clock()
    children = []
    def factory(job):
        child = Child(job)
        children.append(child)
        return child
    monkeypatch.setattr(module, "_new_child", factory, raising=False)
    decoder = ImageDecoder(base, clock)
    yield decoder, clock, children, base
    for child in children:
        child.cleanup_failure = False
        child.cleanup_hook = None
    decoder.close()


@pytest.mark.parametrize("changes", [
    {"id": ID.upper().replace("000002", "00000A")}, {"incarnation": "x"},
    {"source_sha256": "A" * 64}, {"encoded_bytes": True}, {"encoded_bytes": 0},
    {"encoded_bytes": 2097153}, {"media_type": "image/gif"}, {"accepted_ns": True},
    {"accepted_ns": -1}, {"accepted_ns": 2 ** 63 - 1}, {"decode_deadline_ns": 101},
])
def test_request_rejects_invalid_exact_fields(changes):
    with pytest.raises(DecodeError, match="invalid_request"):
        request(**changes)


def test_request_has_no_mutable_dictionary_alias():
    item = request()
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.id = INC


def test_success_validates_wire_cleans_files_and_uses_parent_completion(parent):
    decoder, clock, children, base = parent
    result = decoder.decode(request=request(), payload=PAYLOAD)
    assert type(result) is DecodedImage and result.rgb == RGB
    assert result.frame_sha256 == FRAME and result.completed_ns == 100
    assert result.observed_peak_working_set_bytes == 12345
    assert not hasattr(result, "__dict__") and children[0].cleaned
    assert sorted(p.name for p in base.iterdir()) == ["decoder.owner.lock"]
    assert clock.calls >= 6
    decoder.close()
    calls = clock.calls
    decoder.close()
    assert clock.calls == calls
    with pytest.raises(DecodeError, match="closed"):
        decoder.decode(request=None, payload=None)


@pytest.mark.parametrize("changes,expected", [
    ({"source_sha256": "0" * 64}, "source_mismatch"),
    ({"accepted_ns": 101, "decode_deadline_ns": 10_000_000_101}, "invalid_request"),
    ({"accepted_ns": 0, "decode_deadline_ns": 10_000_000_000}, "timeout"),
])
def test_prelaunch_checks_make_no_files(parent, changes, expected):
    decoder, clock, children, base = parent
    if expected == "timeout":
        clock.ns = 10_000_000_000
    with pytest.raises(DecodeError, match=expected):
        decoder.decode(request=request(**changes), payload=PAYLOAD)
    assert not children and not (base / "job").exists()


@pytest.mark.parametrize("payload", [bytearray(PAYLOAD), memoryview(PAYLOAD), PAYLOAD + b"x", None])
def test_payload_is_exact_bounded_bytes(parent, payload):
    decoder, _, children, _ = parent
    with pytest.raises(DecodeError, match="invalid_request"):
        decoder.decode(request=request(), payload=payload)
    assert not children


@pytest.mark.parametrize("bad", [
    b"", b"\x01", struct.pack("<I", 2049), wire()[:-1], wire() + b"x", wire() + wire(),
    struct.pack("<I", 2) + b"{}", wire(header(id=INC)), wire(header(frame_sha256="0" * 64)),
    wire(header(source_width=True)), wire(header(source_width=8193)),
    wire(header(source_width=4000, source_height=4000)),
    wire(header(oriented_width=3)), wire(header(format="JPEG")), wire(header(extra=1)),
    struct.pack("<I", 21) + b'{"x":1,"x":2,"z":NaN}', b"x" * 14341,
], ids=[f"wire-{index}" for index in range(17)])
def test_untrusted_pipe_never_returns_pixels(parent, monkeypatch, bad):
    decoder, _, children, _ = parent
    original = module._new_child
    def factory(job):
        child = original(job)
        child.data = bytearray(bad)
        return child
    monkeypatch.setattr(module, "_new_child", factory)
    with pytest.raises(DecodeError, match="child_protocol"):
        decoder.decode(request=request(), payload=PAYLOAD)
    assert children[0].cleaned


@pytest.mark.parametrize("reason", ["malformed_image", "unsupported_format", "geometry", "mode", "multiple_frames", "source_mismatch"])
def test_rejection_requires_exact_protocol_and_exit(parent, monkeypatch, reason):
    decoder, _, _, _ = parent
    original = module._new_child
    def factory(job):
        child = original(job)
        child.data = bytearray(wire(dict(schema="market-image-decode-result/v1", incarnation=INC, id=ID,
                                          source_sha256=SOURCE, status="rejected", reason=reason), b""))
        return child
    monkeypatch.setattr(module, "_new_child", factory)
    with pytest.raises(DecodeError, match=f"^{reason}$"):
        decoder.decode(request=request(), payload=PAYLOAD)


def install(parent, monkeypatch, configure):
    decoder, clock, children, base = parent
    original = module._new_child
    def factory(job):
        child = original(job)
        configure(child)
        return child
    monkeypatch.setattr(module, "_new_child", factory)
    return decoder, clock, children, base


@pytest.mark.parametrize("kind,expected", [("clock", "clock"), ("cancel", "cancelled"),
    ("timeout", "timeout"), ("gap", "monitor_stalled"), ("memory", "memory_limit"),
    ("children", "child_protocol"), ("exit", "child_failed")])
def test_monitor_failure_selection(parent, monkeypatch, kind, expected):
    decoder, clock, children, _ = parent
    cancel = threading.Event()
    def configure(child):
        child.peak = 536870913 if kind == "memory" else 0
        child.children = kind == "children"
        child.code = 1 if kind == "exit" else 0
        def hook():
            if kind == "clock": clock.ns = 99
            if kind == "cancel": cancel.set()
            if kind == "timeout": clock.ns = 10_000_000_100
            if kind == "gap": clock.ns += 250_000_001
        child.poll_hook = hook
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match=f"^{expected}$"):
        decoder.decode(request=request(), payload=PAYLOAD, cancel=cancel)
    assert children[0].cleaned


@pytest.mark.parametrize("kind,expected", [("cancel", "cancelled"), ("timeout", "timeout"), ("clock", "clock")])
def test_final_gate_includes_cleanup_and_latches_clock(parent, monkeypatch, kind, expected):
    decoder, clock, _, _ = parent
    cancel = threading.Event()
    def configure(child):
        def cleanup():
            if kind == "cancel": cancel.set()
            if kind == "timeout": clock.ns = 10_000_000_100
            if kind == "clock": clock.ns = 99
        child.cleanup_hook = cleanup
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match=f"^{expected}$"):
        decoder.decode(request=request(), payload=PAYLOAD, cancel=cancel)
    if kind == "clock":
        with pytest.raises(DecodeError, match="clock"):
            decoder.decode(request=None, payload=None)


def test_cleanup_failure_retains_lock_faults_reuse_and_close_retries(parent, monkeypatch):
    decoder, _, children, base = install(parent, monkeypatch, lambda child: setattr(child, "cleanup_failure", True))
    with pytest.raises(DecodeError, match="cleanup_failed"):
        decoder.decode(request=request(), payload=PAYLOAD)
    with pytest.raises(DecodeError, match="ownership"):
        decoder.decode(request=None, payload=None)
    with pytest.raises(DecodeError, match="ownership"):
        ImageDecoder(base, Clock())
    with pytest.raises(DecodeError, match="cleanup_failed"):
        decoder.close()
    assert (base / "job/input.bin").exists()
    children[0].cleanup_failure = False
    decoder.close()
    assert children[0].cleaned and not (base / "job").exists()
    with pytest.raises(DecodeError, match="closed"):
        decoder.decode(request=None, payload=None)


def test_busy_call_and_close_refused_without_sampling_or_files(parent, monkeypatch):
    decoder, clock, _, _ = parent
    def configure(child):
        def start():
            count = clock.calls
            with pytest.raises(DecodeError, match="busy"):
                decoder.decode(request=None, payload=None)
            with pytest.raises(DecodeError, match="busy"):
                decoder.close()
            assert clock.calls == count
        child.start_hook = start
    install(parent, monkeypatch, configure)
    decoder.decode(request=request(), payload=PAYLOAD)


def test_prior_failure_kept_but_cleanup_clock_fault_latches(parent, monkeypatch):
    decoder, clock, _, _ = parent
    def configure(child):
        child.code = 1
        child.cleanup_hook = lambda: setattr(clock, "ns", 99)
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match="child_failed"):
        decoder.decode(request=request(), payload=PAYLOAD)
    with pytest.raises(DecodeError, match="clock"):
        decoder.decode(request=None, payload=None)


@pytest.mark.parametrize("cleanup_failure", [False, True])
def test_interrupt_rethrows_only_after_confirmed_cleanup(parent, monkeypatch, cleanup_failure):
    decoder, _, children, _ = parent
    def configure(child):
        child.cleanup_failure = cleanup_failure
        def interrupt(): raise KeyboardInterrupt
        child.poll_hook = interrupt
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError if cleanup_failure else KeyboardInterrupt) as error:
        decoder.decode(request=request(), payload=PAYLOAD)
    if cleanup_failure:
        assert error.value.code == "cleanup_failed"
    else:
        assert children[0].cleaned


def test_stale_job_refuses_startup_without_deleting(tmp_path):
    base = ROOT / ".tools/image-decoding-20261110" / f"{tmp_path.parent.name}-{tmp_path.name}"
    (base / "job").mkdir(parents=True)
    (base / "job/input.bin").write_bytes(b"stale")
    with pytest.raises(DecodeError, match="ownership"):
        ImageDecoder(base, Clock())
    assert (base / "job/input.bin").read_bytes() == b"stale"


def test_foreign_scratch_keeps_root_lock_until_explicit_recovery(parent, monkeypatch):
    decoder, _, children, base = parent
    def configure(child):
        child.start_hook = lambda: (base / "job/foreign").write_bytes(b"foreign")
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match="cleanup_failed"):
        decoder.decode(request=request(), payload=PAYLOAD)
    assert children[0].cleaned and (base / "job/foreign").exists()
    (base / "job/foreign").unlink()  # Explicit trusted test recovery, never product deletion.
    decoder.close()


@pytest.mark.parametrize("sample", [True, -1, 2 ** 63, 1.0, None])
def test_invalid_clock_samples_latch_before_any_child(parent, sample):
    decoder, clock, children, base = parent
    clock.ns = sample
    with pytest.raises(DecodeError, match="clock"):
        decoder.decode(request=request(), payload=PAYLOAD)
    assert not children and not (base / "job").exists()
    clock.ns = 100
    with pytest.raises(DecodeError, match="clock"):
        decoder.decode(request=None, payload=None)


def test_clock_exception_fails_closed_without_exception_text(parent):
    decoder, clock, _, _ = parent
    clock.failure = OSError("private clock details")
    with pytest.raises(DecodeError, match="^clock$"):
        decoder.decode(request=request(), payload=PAYLOAD)


@pytest.mark.parametrize("changes", [{"rgb": bytearray(RGB)}, {"rgb": RGB[:-1]},
    {"frame_sha256": "0" * 64}, {"source_width": True}, {"oriented_height": 3},
    {"completed_ns": True}, {"observed_peak_working_set_bytes": 536870913}, {"format": "GIF"}])
def test_result_constructor_requires_exact_canonical_values(changes):
    values = {key: value for key, value in header().items() if key not in ("schema", "status")}
    values.update(rgb=RGB, completed_ns=100, observed_peak_working_set_bytes=1)
    values.update(changes)
    with pytest.raises(DecodeError, match="invalid_request"):
        DecodedImage(**values)


def test_request_scalar_snapshot_survives_caller_mutation_during_clock(parent):
    decoder, clock, _, _ = parent
    original = request()
    sample = clock.sample
    def mutate():
        object.__setattr__(original, "id", INC)
        object.__setattr__(original, "decode_deadline_ns", 101)
        return sample()
    clock.sample = mutate
    result = decoder.decode(request=original, payload=PAYLOAD)
    assert result.id == ID and result.completed_ns == 100


def test_simultaneous_protocol_and_failed_exit_selects_protocol(parent, monkeypatch):
    decoder, _, _, _ = parent
    def configure(child):
        child.data = bytearray(b"bad")
        child.code = 3
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match="child_protocol"):
        decoder.decode(request=request(), payload=PAYLOAD)


def test_poll_error_still_samples_clock_before_selecting_failure(parent, monkeypatch):
    decoder, clock, _, _ = parent
    def configure(child):
        def broken_poll():
            clock.ns = 99
            raise OSError("pipe failure")
        child.poll_hook = broken_poll
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match="clock"):
        decoder.decode(request=request(), payload=PAYLOAD)


def test_final_validation_deadline_precedes_child_rejection(parent, monkeypatch):
    decoder, clock, _, _ = parent
    original = clock.sample
    def sample():
        # initial sample, one poll, final-validation sample.
        if clock.calls == 2:
            clock.ns = 10_000_000_100
        return original()
    clock.sample = sample
    def configure(child):
        child.data = bytearray(wire(dict(schema="market-image-decode-result/v1", incarnation=INC,
            id=ID, source_sha256=SOURCE, status="rejected", reason="mode"), b""))
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match="timeout"):
        decoder.decode(request=request(), payload=PAYLOAD)


def test_root_outside_tools_refused_without_writing(tmp_path):
    outside = ROOT / "tests"
    before = {path.name for path in outside.iterdir()}
    with pytest.raises(DecodeError, match="ownership"):
        ImageDecoder(outside, Clock())
    assert {path.name for path in outside.iterdir()} == before


def test_root_symlink_refused_without_touching_target(tmp_path):
    base = ROOT / ".tools/image-decoding-20261110" / f"{tmp_path.parent.name}-{tmp_path.name}"
    target = base.with_name(base.name + "-target")
    target.mkdir(parents=True)
    try:
        base.symlink_to(target, target_is_directory=True)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink creation requires privilege: WinError1314")
        raise
    with pytest.raises(DecodeError, match="ownership"):
        ImageDecoder(base, Clock())
    assert not list(target.iterdir())


@pytest.mark.parametrize("cleanup_failure", [False, True])
def test_post_cleanup_interrupt_releases_busy_and_preserves_cleanup_override(parent, monkeypatch, cleanup_failure):
    decoder, clock, _, _ = parent
    def configure(child):
        child.cleanup_failure = cleanup_failure
        child.cleanup_hook = lambda: setattr(clock, "failure", KeyboardInterrupt())
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError if cleanup_failure else KeyboardInterrupt) as error:
        decoder.decode(request=request(), payload=PAYLOAD)
    if cleanup_failure:
        assert error.value.code == "cleanup_failed"
    clock.failure = None
    # Teardown must be retryable, without a permanently stuck busy flag.
    for child in parent[2]:
        child.cleanup_failure = False
        child.cleanup_hook = None
    decoder.close()


def test_pipe_read_budget_stops_at_single_overflow_byte(parent, monkeypatch):
    decoder, _, _, _ = parent
    def configure(child):
        child.data = bytearray(wire() + b"\0" * 10000)
        poll = child.poll
        observed = 0
        def bounded(max_bytes):
            nonlocal observed
            assert observed + max_bytes <= 14341
            result = poll(max_bytes)
            observed += len(result[0])
            return result
        child.poll = bounded
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match="child_protocol"):
        decoder.decode(request=request(), payload=PAYLOAD)


def test_forged_incomplete_exact_dto_is_invalid_without_latching_busy(parent):
    decoder, clock, children, _ = parent
    forged = object.__new__(DecodeRequest)
    with pytest.raises(DecodeError, match="invalid_request"):
        decoder.decode(request=forged, payload=PAYLOAD)
    assert not children and clock.calls == 0
    decoder.decode(request=request(), payload=PAYLOAD)


@pytest.mark.parametrize("origin", [str(ROOT / "foreign.py"), None])
def test_fixed_startup_import_restores_sys_path_and_refuses_foreign_preload(monkeypatch, origin):
    before = list(sys.path)
    assert module._WINDOWS._load_primitives() is module._WINDOWS.PRIMITIVES
    assert sys.path == before
    foreign = types.ModuleType("market_supervision")
    foreign.__file__ = origin
    monkeypatch.setitem(sys.modules, "market_supervision", foreign)
    with pytest.raises(DecodeError, match="ownership"):
        module._WINDOWS._load_primitives()
    assert sys.path == before


@pytest.mark.parametrize("cleanup_failure", [False, True])
def test_final_event_interrupt_preserves_cleanup_outcome_and_allows_close_retry(parent, monkeypatch, cleanup_failure):
    decoder, _, children, base = parent
    event = threading.Event()
    cutoffs = 0
    def interrupt_once():
        nonlocal cutoffs
        cutoffs += 1
        raise KeyboardInterrupt("test final cancellation cutoff")
    def configure(child):
        child.cleanup_failure = cleanup_failure
        child.cleanup_hook = lambda: setattr(event, "is_set", interrupt_once)
    install(parent, monkeypatch, configure)
    caught = None
    try:
        decoder.decode(request=request(), payload=PAYLOAD, cancel=event)
    except BaseException as error:
        caught = error
    # Restore only the injected external boundary. Product close must recover
    # through the retained owner; the test never resets its busy/owner state.
    children[0].cleanup_failure = False
    children[0].cleanup_hook = None
    assert cutoffs == 1
    assert type(caught) is (DecodeError if cleanup_failure else KeyboardInterrupt)
    if cleanup_failure:
        assert caught.code == "cleanup_failed" and (base / "job/input.bin").exists()
    decoder.close()
    assert children[0].cleaned and not (base / "job").exists()
    with pytest.raises(DecodeError, match="closed"):
        decoder.decode(request=None, payload=None)


@pytest.mark.parametrize("body,code,expected", [
    (b"bad", 3, "child_protocol"), (struct.pack("<I", 2) + b"{}", 3, "child_protocol"),
    (b"", 3, "child_failed"), (wire(), 3, "child_failed"),
], ids=["truncated-prefix", "invalid-header", "empty-failed", "valid-failed"])
def test_failed_exit_waits_for_next_poll_eof_and_preserves_protocol_priority(parent, monkeypatch, body, code, expected):
    decoder, _, children, _ = parent
    polls = 0
    eof_seen = False
    def configure(child):
        child.data = bytearray(body)
        child.code = code
        poll = child.poll
        def real_pipe_shape(max_bytes):
            nonlocal polls, eof_seen
            polls += 1
            block, _, exited, exit_code, peak, extra = poll(max_bytes)
            # PeekNamedPipe sees available bytes at entry; consuming the last
            # bytes cannot also report the EOF found by the following Peek.
            eof = not block
            eof_seen = eof_seen or eof
            return block, eof, exited, exit_code, peak, extra
        child.poll = real_pipe_shape
    install(parent, monkeypatch, configure)
    with pytest.raises(DecodeError, match=f"^{expected}$"):
        decoder.decode(request=request(), payload=PAYLOAD)
    assert children[0].cleaned and eof_seen
    assert polls == (5 if body == wire() else 2 if body else 1)
