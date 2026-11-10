"""Trusted generated pixel fixtures and wire checks; no process ownership claim."""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

import pytest
from PIL import Image, PngImagePlugin


ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "scripts" / "market-image-decode-worker.py"
INCARNATION = "00000000-0000-4000-8000-000000000001"
IMAGE_ID = "00000000-0000-4000-8000-000000000002"
RED_HASH = "99cf1c4e7d6bb987428be8eaf102357240171f55b796a0e53f38e5cf8150d90b"
MAX_SOURCE = 2_097_152
PREFIX = b'{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n'


@pytest.fixture(scope="module")
def worker():
    assert WORKER.is_file(), "The private pixel/wire worker is not implemented"
    spec = importlib.util.spec_from_file_location("market_image_decode_worker_test", WORKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encoded(image, format="PNG", **kwargs):
    stream = io.BytesIO()
    image.save(stream, format=format, **kwargs)
    return stream.getvalue()


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def source_png(*, size=(1, 1), depth=8, color=2, chunks=(), pixel=b"\x00\xff\x00\x00"):
    ihdr = struct.pack(">IIBBBBB", *size, depth, color, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + b"".join(png_chunk(kind, data) for kind, data in chunks)
            + png_chunk(b"IDAT", zlib.compress(pixel)) + png_chunk(b"IEND", b""))


def request_for(payload, **changes):
    request = {
        "schema": "market-image-decode/v1", "incarnation": INCARNATION,
        "id": IMAGE_ID, "source_sha256": hashlib.sha256(payload).hexdigest(),
        "encoded_bytes": len(payload), "media_type": "image/png",
    }
    return request | changes


def write_job(tmp_path, payload, request=None):
    job = tmp_path / "job"
    job.mkdir()
    (job / "input.bin").write_bytes(payload)
    (job / "request.json").write_bytes(json.dumps(
        request_for(payload) if request is None else request,
        separators=(",", ":"),
    ).encode())
    return job


def unpack(message):
    assert type(message) is bytes
    assert 4 < len(message) <= 14_340
    count, = struct.unpack("<I", message[:4])
    assert 0 < count <= 2048
    header = json.loads(message[4:4 + count].decode("utf-8"))
    pixels = message[4 + count:]
    assert len(pixels) == (12_288 if header["status"] == "decoded" else 0)
    return header, pixels


def rejected(worker, payload, reason, mime="image/png"):
    with pytest.raises(worker.ImageRejected) as caught:
        worker.decode(payload, mime)
    assert caught.value.code == reason
    assert str(caught.value) == reason


def test_red_png_exact_raw_frame_and_wire_identity(worker, tmp_path):
    payload = encoded(Image.new("RGB", (1, 1), "red"))
    header, pixels = unpack(worker.process_job(write_job(tmp_path, payload)))
    assert pixels == b"\xff\x00\x00" * 4096
    assert header == {
        "schema": "market-image-decode-result/v1", "incarnation": INCARNATION,
        "id": IMAGE_ID, "source_sha256": hashlib.sha256(payload).hexdigest(),
        "status": "decoded", "preprocessing_version": "market-rgb64/v1",
        "frame_sha256": RED_HASH, "source_width": 1, "source_height": 1,
        "oriented_width": 1, "oriented_height": 1, "format": "PNG",
    }
    assert hashlib.sha256(PREFIX + pixels).hexdigest() == RED_HASH


@pytest.mark.parametrize(("size", "box"), [
    ((3, 2), (0, 10, 64, 43)), ((2, 3), (10, 0, 43, 64)),
    ((128, 65), (0, 15, 64, 33)), ((128, 63), (0, 16, 64, 32)),
    ((8192, 1), (0, 31, 64, 1)), ((1, 8192), (31, 0, 1, 64)),
])
def test_integer_half_up_upscaling_and_odd_black_padding(worker, size, box):
    metadata, pixels = worker.decode(encoded(Image.new("RGB", size, (12, 34, 56))), "image/png")
    left, top, width, height = box
    expected = bytearray(12_288)
    for y in range(top, top + height):
        start = (y * 64 + left) * 3
        expected[start:start + width * 3] = bytes((12, 34, 56)) * width
    assert pixels == bytes(expected)
    assert (metadata["source_width"], metadata["source_height"]) == size
    assert (metadata["oriented_width"], metadata["oriented_height"]) == size


def test_alpha_is_composited_before_bilinear_resize(worker):
    image = Image.new("RGBA", (2, 1))
    image.putdata([(255, 0, 0, 0), (0, 200, 100, 128)])
    _, pixels = worker.decode(encoded(image), "image/png")
    assert pixels[:16 * 64 * 3] == b"\x00" * (16 * 64 * 3)
    row = pixels[16 * 64 * 3:17 * 64 * 3]
    assert row[:16 * 3] == b"\x00\x00\x00" * 16
    assert row[-16 * 3:] == b"\x00\x64\x32" * 16
    assert row[31 * 3:33 * 3] == bytes((0, 48, 24, 0, 52, 26))
    assert pixels[48 * 64 * 3:] == b"\x00" * (16 * 64 * 3)


@pytest.mark.parametrize(("mode", "color", "want"), [
    ("1", 1, (255, 255, 255)), ("L", 87, (87, 87, 87)),
    ("LA", (200, 128), (100, 100, 100)), ("RGBA", (255, 80, 10, 128), (128, 40, 5)),
])
def test_allowed_png_modes_composite_exactly(worker, mode, color, want):
    _, pixels = worker.decode(encoded(Image.new(mode, (1, 1), color)), "image/png")
    assert pixels == bytes(want) * 4096


def test_palette_transparency_is_honored(worker):
    image = Image.new("P", (1, 1), 0)
    image.putpalette([200, 100, 50] + [0] * 765)
    _, pixels = worker.decode(encoded(image, transparency=bytes((128,))), "image/png")
    assert pixels == bytes((100, 50, 25)) * 4096


@pytest.mark.parametrize(("mode", "color", "want"), [
    ("RGB", (60, 60, 60), (60, 60, 60)), ("L", 101, (101, 101, 101)),
])
def test_jpeg_decoded_channels_and_format(worker, mode, color, want):
    metadata, pixels = worker.decode(encoded(Image.new(mode, (1, 1), color), "JPEG"), "image/jpeg")
    assert pixels == bytes(want) * 4096
    assert metadata["format"] == "JPEG"


@pytest.mark.parametrize(("orientation", "quadrants"), [
    (1, (0, 1, 2, 3)), (2, (1, 0, 3, 2)), (3, (3, 2, 1, 0)),
    (4, (2, 3, 0, 1)), (5, (0, 2, 1, 3)), (6, (2, 0, 3, 1)),
    (7, (3, 1, 2, 0)), (8, (1, 3, 0, 2)),
])
def test_all_exif_only_orientation_transforms_have_exact_pixels(worker, orientation, quadrants):
    colors = (b"\xff\x00\x00", b"\x00\xff\x00", b"\x00\x00\xff", b"\xff\xff\xff")
    source = (colors[0] * 32 + colors[1] * 32) * 32 + (colors[2] * 32 + colors[3] * 32) * 32
    image = Image.frombytes("RGB", (64, 64), source)
    exif = Image.Exif()
    exif[274] = orientation
    _, pixels = worker.decode(encoded(image, exif=exif), "image/png")
    a, b, c, d = quadrants
    assert pixels == (colors[a] * 32 + colors[b] * 32) * 32 + (colors[c] * 32 + colors[d] * 32) * 32


def test_orientation_keeps_source_and_oriented_dimensions_separate(worker):
    exif = Image.Exif()
    exif[274] = 6
    metadata, pixels = worker.decode(encoded(Image.new("RGB", (3, 2), "red"), exif=exif), "image/png")
    assert metadata == {"source_width": 3, "source_height": 2, "oriented_width": 2,
                        "oriented_height": 3, "format": "PNG"}
    assert pixels[:30] == b"\x00" * 30
    assert pixels[30:159] == b"\xff\x00\x00" * 43
    assert pixels[159:192] == b"\x00" * 33


@pytest.mark.parametrize(("exif_orientation", "oriented"), [(None, (3, 2)), (1, (3, 2)), (8, (2, 3))])
def test_xmp_only_orientation_is_ignored_and_exif_wins(worker, exif_orientation, oriented):
    info = PngImagePlugin.PngInfo()
    info.add_itxt("XML:com.adobe.xmp", '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:Description '
                  'xmlns:rdf="urn:rdf" xmlns:tiff="http://ns.adobe.com/tiff/1.0/" tiff:Orientation="6"/></x:xmpmeta>')
    info.add_text("Raw profile type exif", "not an EXIF source")
    options = {"pnginfo": info}
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[274] = exif_orientation
        options["exif"] = exif
    metadata, _ = worker.decode(encoded(Image.new("RGB", (3, 2), "red"), **options), "image/png")
    assert (metadata["oriented_width"], metadata["oriented_height"]) == oriented


@pytest.mark.parametrize("orientation", [0, 9, -1, "6", 6.0])
def test_noninteger_or_invalid_exif_orientation_rejected(worker, orientation):
    if type(orientation) is str:
        kind, count, value, extra = 2, 2, b"6\x00\x00\x00", b""
    elif type(orientation) is float:
        kind, count, value, extra = 12, 1, struct.pack("<I", 26), struct.pack("<d", orientation)
    elif orientation < 0:
        kind, count, value, extra = 9, 1, struct.pack("<i", orientation), b""
    else:
        kind, count, value, extra = 3, 1, struct.pack("<H", orientation) + b"\x00\x00", b""
    exif = (b"II*\x00\x08\x00\x00\x00\x01\x00"
            + struct.pack("<HHI", 274, kind, count) + value + b"\x00" * 4 + extra)
    rejected(worker, source_png(chunks=((b"eXIf", exif),)), "malformed_image")


def test_malformed_exif_rejected_without_error_text(worker):
    rejected(worker, source_png(chunks=((b"eXIf", b"private broken metadata"),)), "malformed_image")


@pytest.mark.parametrize(("payload", "mime"), [
    (encoded(Image.new("RGB", (1, 1)), "JPEG"), "image/png"),
    (encoded(Image.new("RGB", (1, 1))), "image/jpeg"),
])
def test_mime_must_match_decoded_format(worker, payload, mime):
    rejected(worker, payload, "unsupported_format", mime)


def test_cmyk_jpeg_is_not_silently_converted(worker):
    rejected(worker, encoded(Image.new("CMYK", (1, 1)), "JPEG"), "mode", "image/jpeg")


def test_mime_mismatch_does_not_become_source_mode_rejection(worker):
    rejected(worker, source_png(depth=16, pixel=b"\x00" + b"\xff" * 6),
             "unsupported_format", "image/jpeg")


@pytest.mark.parametrize("color", [0, 2, 4, 6])
def test_source_png_16bit_is_rejected_even_when_pillow_reports_rgb(worker, color):
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color]
    rejected(worker, source_png(depth=16, color=color, pixel=b"\x00" + b"\xff\xff" * channels), "mode")


@pytest.mark.parametrize(("color", "depth"), [(2, 8), (6, 8), (2, 16), (6, 16)])
def test_wire_checks_effective_png_depth_after_a_second_ihdr(worker, tmp_path, color, depth):
    channels = {2: 3, 6: 4}[color]
    chunks = ()
    if depth == 16:
        chunks = ((b"IHDR", struct.pack(">IIBBBBB", 1, 1, 16, color, 0, 0, 0)),)
    payload = source_png(color=color, chunks=chunks,
                         pixel=b"\x00" + b"\xff" * (channels * depth // 8))
    header, pixels = unpack(worker.process_job(write_job(tmp_path, payload)))
    identity = {
        "schema": "market-image-decode-result/v1", "incarnation": INCARNATION,
        "id": IMAGE_ID, "source_sha256": hashlib.sha256(payload).hexdigest(),
    }
    if depth == 16:
        assert header == identity | {"status": "rejected", "reason": "mode"}
        assert pixels == b""
    else:
        assert header == identity | {
            "status": "decoded", "preprocessing_version": "market-rgb64/v1",
            "frame_sha256": "ad54ff1c79105292048cfb0ce2dfa2e78bd28c255cb880a549cff0840d622502",
            "source_width": 1, "source_height": 1, "oriented_width": 1,
            "oriented_height": 1, "format": "PNG",
        }
        assert pixels == b"\xff\xff\xff" * 4096


@pytest.mark.parametrize(("depth", "color", "pixel", "want"), [
    (1, 0, b"\x00\x80", (255, 255, 255)), (2, 0, b"\x00\x80", (170, 170, 170)),
    (4, 0, b"\x00\x80", (136, 136, 136)),
])
def test_low_bit_depth_png_is_retained(worker, depth, color, pixel, want):
    _, pixels = worker.decode(source_png(depth=depth, color=color, pixel=pixel), "image/png")
    assert pixels == bytes(want) * 4096


@pytest.mark.parametrize("damage", ["crc", "length", "type", "short"])
def test_first_png_ihdr_requires_exact_shape_and_crc(worker, damage):
    payload = bytearray(source_png())
    if damage == "crc":
        payload[29] ^= 1
    elif damage == "length":
        payload[11] = 12
    elif damage == "type":
        payload[12:16] = b"iHDR"
    else:
        payload = payload[:32]
    rejected(worker, bytes(payload), "malformed_image")


@pytest.mark.parametrize("size", [(8193, 1), (1, 8193), (4000, 3001), (8000, 4000)])
def test_geometry_rejected_before_inflating_incomplete_raster(worker, size):
    rejected(worker, source_png(size=size), "geometry")


@pytest.mark.parametrize("size", [(4000, 3001), (8000, 4000)])
def test_jpeg_pillow_bomb_warning_and_error_map_to_geometry(worker, size):
    payload = bytearray(encoded(Image.new("RGB", (1, 1)), "JPEG"))
    marker = payload.index(b"\xff\xc0")
    width, height = size
    payload[marker + 5:marker + 9] = struct.pack(">HH", height, width)
    rejected(worker, bytes(payload), "geometry", "image/jpeg")


def test_real_exif_parse_warning_is_rejected(worker):
    payload = source_png(chunks=((b"eXIf", b"II*\x00\x08\x00\x00\x00\x01\x00"),))
    with Image.open(io.BytesIO(payload)) as image, pytest.warns(UserWarning):
        exif = Image.Exif()
        exif.load(image.info["exif"])
    rejected(worker, payload, "malformed_image")


@pytest.mark.parametrize("size", [(0, 1), (1, 0)])
def test_zero_dimensions_are_rejected_as_geometry(worker, size):
    rejected(worker, source_png(size=size), "geometry")


def test_apng_multiple_frames_rejected(worker):
    payload = encoded(Image.new("RGB", (1, 1), "red"), save_all=True,
                      append_images=[Image.new("RGB", (1, 1), "blue")], duration=100)
    rejected(worker, payload, "multiple_frames")


@pytest.mark.parametrize("kind", ["png_crc", "png_truncated", "jpeg_truncated", "junk"])
def test_verify_and_full_load_failures_are_malformed(worker, kind):
    if kind == "jpeg_truncated":
        payload = encoded(Image.new("RGB", (64, 64)), "JPEG")[:-8]
        mime = "image/jpeg"
    else:
        payload = source_png()
        mime = "image/png"
        if kind == "png_crc":
            payload = payload[:-5] + bytes((payload[-5] ^ 1,)) + payload[-4:]
        elif kind == "png_truncated":
            payload = payload[:-15]
        else:
            payload = b"private-not-a-photo"
    rejected(worker, payload, "malformed_image", mime)


@pytest.mark.parametrize(("kind", "count", "reject"), [
    ("zTXt", 65_536, False), ("zTXt", 65_537, True),
    ("compressed_iTXt", 65_537, True), ("tEXt", 65_537, False),
    ("tEXt", 262_144, False), ("tEXt", 262_145, True),
    ("unicode_iTXt", 100_000, False), ("unicode_iTXt", 262_144, False),
    ("unicode_iTXt", 262_145, True),
])
def test_pinned_png_text_limit_units_not_a_general_encoded_byte_cap(worker, kind, count, reject):
    if kind == "zTXt":
        chunk = (b"zTXt", b"note\x00\x00" + zlib.compress(b"a" * count))
    elif kind == "compressed_iTXt":
        chunk = (b"iTXt", b"note\x00\x01\x00\x00\x00" + zlib.compress(b"a" * count))
    elif kind == "unicode_iTXt":
        chunk = (b"iTXt", b"note\x00\x00\x00\x00\x00" + ("\u20ac" * count).encode())
    else:
        chunk = (b"tEXt", b"note\x00" + b"a" * count)
    payload = source_png(chunks=(chunk,))
    if reject:
        rejected(worker, payload, "malformed_image")
    else:
        _, pixels = worker.decode(payload, "image/png")
        assert pixels == b"\xff\x00\x00" * 4096


@pytest.mark.parametrize(("repeats", "reject"), [(4, False), (5, True)])
def test_repeated_png_text_keys_still_accumulate(worker, repeats, reject):
    payload = source_png(chunks=((b"tEXt", b"same\x00" + b"a" * 65_536),) * repeats)
    if reject:
        rejected(worker, payload, "malformed_image")
    else:
        _, pixels = worker.decode(payload, "image/png")
        assert pixels == b"\xff\x00\x00" * 4096


def test_png_text_key_and_language_fields_do_not_count_as_value_text(worker):
    chunk = (b"iTXt", b"k" * 1000 + b"\x00\x00\x00" + b"l" * 300_000 + b"\x00\x00ok")
    _, pixels = worker.decode(source_png(chunks=(chunk,)), "image/png")
    assert pixels == b"\xff\x00\x00" * 4096


def test_malformed_itxt_ignored_by_pillow_is_not_claimed_rejected(worker):
    _, pixels = worker.decode(source_png(chunks=((b"iTXt", b"bad\x00\x00\x00\x00\x00\xff"),)), "image/png")
    assert pixels == b"\xff\x00\x00" * 4096


def test_icc_and_comment_metadata_do_not_change_pixels_or_escape_in_header(worker, tmp_path):
    info = PngImagePlugin.PngInfo()
    info.add_text("private-secret", "private-secret-content")
    payload = encoded(Image.new("RGB", (1, 1), "red"), pnginfo=info, icc_profile=b"private-icc")
    message = worker.process_job(write_job(tmp_path, payload))
    header, pixels = unpack(message)
    assert pixels == b"\xff\x00\x00" * 4096
    assert b"private" not in message
    assert header["frame_sha256"] == RED_HASH


def test_hash_mismatch_has_exact_identity_bounded_rejection_without_pixels(worker, tmp_path):
    payload = b"private-invalid-source"
    request = request_for(payload, source_sha256="a" * 64)
    header, pixels = unpack(worker.process_job(write_job(tmp_path, payload, request)))
    assert header == {
        "schema": "market-image-decode-result/v1", "incarnation": INCARNATION,
        "id": IMAGE_ID, "source_sha256": "a" * 64,
        "status": "rejected", "reason": "source_mismatch",
    }
    assert pixels == b""


@pytest.mark.parametrize(("payload", "reason"), [(b"private-invalid-source", "malformed_image"),
    (source_png(depth=16, pixel=b"\x00" + b"\xff" * 6), "mode"),
    (source_png(size=(8193, 1)), "geometry"),
])
def test_image_rejection_is_one_exact_header_with_no_metadata_or_pixels(worker, tmp_path, payload, reason):
    header, pixels = unpack(worker.process_job(write_job(tmp_path, payload)))
    assert header == {
        "schema": "market-image-decode-result/v1", "incarnation": INCARNATION,
        "id": IMAGE_ID, "source_sha256": hashlib.sha256(payload).hexdigest(),
        "status": "rejected", "reason": reason,
    }
    assert pixels == b""


@pytest.mark.parametrize(("key", "value"), [
    ("schema", "other"), ("id", IMAGE_ID.upper()), ("id", "private-secret"),
    ("incarnation", None), ("source_sha256", "A" * 64), ("encoded_bytes", True),
    ("encoded_bytes", 1.0), ("encoded_bytes", 0), ("encoded_bytes", MAX_SOURCE + 1),
    ("media_type", "image/PNG"), ("media_type", "image/gif"), ("extra", "private-secret"),
])
def test_strict_request_keys_and_types_do_not_invent_rejection_identity(worker, tmp_path, key, value):
    payload = source_png()
    request = request_for(payload, **{key: value})
    if key == "id" and value == IMAGE_ID.upper():
        request[key] = "AAAAAAAA-0000-4000-8000-000000000002"
    with pytest.raises(worker.WorkerInputError):
        worker.process_job(write_job(tmp_path, payload, request))


@pytest.mark.parametrize("damage", ["missing", "duplicate", "nonfinite", "invalid_utf8", "oversize", "trailing"])
def test_strict_bounded_json_request(worker, tmp_path, damage):
    payload = source_png()
    job = write_job(tmp_path, payload)
    request_path = job / "request.json"
    data = request_path.read_bytes()
    if damage == "missing":
        request = request_for(payload)
        del request["id"]
        data = json.dumps(request).encode()
    elif damage == "duplicate":
        data = data[:-1] + b',"id":"' + IMAGE_ID.encode() + b'"}'
    elif damage == "nonfinite":
        data = data.replace(str(len(payload)).encode(), b"NaN")
    elif damage == "invalid_utf8":
        data += b"\xff"
    elif damage == "oversize":
        data += b" " * 2048
    else:
        data += b"{}"
    request_path.write_bytes(data)
    with pytest.raises(worker.WorkerInputError):
        worker.process_job(job)


def test_exact_2048_byte_request_is_accepted(worker, tmp_path):
    job = write_job(tmp_path, source_png())
    request_path = job / "request.json"
    data = request_path.read_bytes()
    request_path.write_bytes(data + b" " * (2048 - len(data)))
    header, _ = unpack(worker.process_job(job))
    assert header["status"] == "decoded"


def test_single_byte_source_has_valid_identity_and_malformed_rejection(worker, tmp_path):
    header, pixels = unpack(worker.process_job(write_job(tmp_path, b"x")))
    assert header["reason"] == "malformed_image"
    assert header["source_sha256"] == "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"
    assert pixels == b""


def test_unknown_rejection_reason_cannot_become_wire_metadata(worker):
    with pytest.raises(ValueError):
        raise worker.ImageRejected("private-sensitive-error")


@pytest.mark.parametrize("payload", [bytearray(b"x"), memoryview(b"x"), None, "x"])
def test_transform_refuses_mutable_and_nonbytes_payloads(worker, payload):
    with pytest.raises(worker.WorkerInputError):
        worker.decode(payload, "image/png")


def test_transform_refuses_builtin_subclasses(worker):
    class Payload(bytes):
        pass

    class Mime(str):
        pass

    with pytest.raises(worker.WorkerInputError):
        worker.decode(Payload(source_png()), "image/png")
    with pytest.raises(worker.WorkerInputError):
        worker.decode(source_png(), Mime("image/png"))


@pytest.mark.parametrize("size", [0, MAX_SOURCE + 1])
def test_input_bound_enforced_before_image_parsing(worker, tmp_path, size):
    payload = b"x" * size
    with pytest.raises(worker.WorkerInputError):
        worker.process_job(write_job(tmp_path, payload))


def test_exact_two_mib_source_is_accepted_without_advertising_file_purity(worker, tmp_path):
    payload = source_png()
    payload += b"\x00" * (MAX_SOURCE - len(payload))
    header, pixels = unpack(worker.process_job(write_job(tmp_path, payload)))
    assert header["status"] == "decoded"
    assert pixels == b"\xff\x00\x00" * 4096


def test_declared_size_must_equal_actual_file_size(worker, tmp_path):
    payload = source_png()
    with pytest.raises(worker.WorkerInputError):
        worker.process_job(write_job(tmp_path, payload, request_for(payload, encoded_bytes=len(payload) - 1)))


@pytest.mark.parametrize("entry", ["input_directory", "request_directory", "extra_file"])
def test_job_only_contains_two_ordinary_known_files(worker, tmp_path, entry):
    job = write_job(tmp_path, source_png())
    if entry == "extra_file":
        (job / "private-extra").write_bytes(b"secret")
    else:
        path = job / ("input.bin" if entry == "input_directory" else "request.json")
        path.unlink()
        path.mkdir()
    with pytest.raises(worker.WorkerInputError):
        worker.process_job(job)


@pytest.mark.parametrize("entry", ["job", "input.bin", "request.json"])
def test_child_refuses_symbolic_paths(worker, tmp_path, entry):
    job = write_job(tmp_path, source_png())
    target = job if entry == "job" else job / entry
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=entry == "job")
    except OSError as exc:
        pytest.skip(f"host lacks symlink privilege: {exc.winerror if hasattr(exc, 'winerror') else exc.errno}")
    if entry == "job":
        job = link
    else:
        target.unlink()
        target.symlink_to(link)
    with pytest.raises(worker.WorkerInputError):
        worker.process_job(job)


def test_main_unexpected_exception_exits_nonzero_without_stdout_or_traceback(worker, tmp_path, monkeypatch, capsys):
    def fail(*args):
        raise RuntimeError("private-sensitive-error")
    monkeypatch.setattr(worker, "_bootstrap_pillow", lambda: None)
    monkeypatch.setattr(worker, "process_job", fail)
    assert worker.main([str(tmp_path)]) == 1
    assert capsys.readouterr() == ("", "")


@pytest.mark.skipif(os.name != "nt", reason="fixed Windows .venv/Lib isolated bootstrap; portable tests cover pixels/wire")
def test_standalone_isolated_child_emits_one_message_and_no_files(tmp_path):
    payload = source_png()
    job = write_job(tmp_path, payload)
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(WORKER), str(job)],
        cwd=job, capture_output=True, timeout=15, check=False,
    )
    assert completed.returncode == 0
    assert completed.stderr == b""
    header, pixels = unpack(completed.stdout)
    assert header["frame_sha256"] == RED_HASH
    assert pixels == b"\xff\x00\x00" * 4096
    assert sorted(path.name for path in job.iterdir()) == ["input.bin", "request.json"]


@pytest.mark.skipif(os.name != "nt", reason="fixed Windows .venv/Lib isolated bootstrap; portable tests cover pixels/wire")
def test_standalone_invalid_request_exits_nonzero_without_metadata(tmp_path):
    job = write_job(tmp_path, source_png(), {"private": "secret"})
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(WORKER), str(job)],
        cwd=job, capture_output=True, timeout=15, check=False,
    )
    assert completed.returncode == 1
    assert completed.stdout == completed.stderr == b""
