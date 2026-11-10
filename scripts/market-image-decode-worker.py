"""Private canonical image worker; invoked only by the owned parent launcher."""

from contextlib import ExitStack
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
from uuid import UUID
import warnings
import zlib


MAX_SOURCE = 2_097_152
MAX_HEADER = 2048
FRAME_PREFIX = b'{"dtype":"uint8","rank":3,"shape":[64,64,3],"version":"rgb-input/v1"}\n'
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_RAW_MODES = {
    "1": ("1",), "L": ("L;2", "L;4", "L"), "LA": ("LA",),
    "P": ("P;1", "P;2", "P;4", "P"), "RGB": ("RGB",), "RGBA": ("RGBA",),
}
REQUEST_KEYS = {"schema", "incarnation", "id", "source_sha256", "encoded_bytes", "media_type"}
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


class WorkerInputError(Exception):
    """No valid request identity is available; emit no wire result."""


class ImageRejected(Exception):
    def __init__(self, code):
        if type(code) is not str or code not in (
            "malformed_image", "unsupported_format", "geometry", "mode",
            "multiple_frames", "source_mismatch",
        ):
            raise ValueError("invalid rejection reason")
        self.code = code
        super().__init__(code)


def decode(payload, media_type):
    """Transform trusted immutable bytes; production calls this only in the child."""
    if (type(payload) is not bytes or not 1 <= len(payload) <= MAX_SOURCE
            or type(media_type) is not str or media_type not in ("image/jpeg", "image/png")):
        raise WorkerInputError()

    from PIL import Image, ImageFile, PngImagePlugin

    ImageFile.LOAD_TRUNCATED_IMAGES = False
    Image.MAX_IMAGE_PIXELS = 12_000_000
    PngImagePlugin.MAX_TEXT_CHUNK = 65_536
    PngImagePlugin.MAX_TEXT_MEMORY = 262_144
    try:
        with warnings.catch_warnings(), ExitStack() as stack:
            warnings.simplefilter("error")
            if payload.startswith(PNG_SIGNATURE):
                if media_type != "image/png":
                    raise ImageRejected("unsupported_format")
                _png_header(payload)
            image = stack.enter_context(Image.open(io.BytesIO(payload), formats=("JPEG", "PNG")))
            _check_image(image, media_type)
            image.verify()
            image.close()
            image = stack.enter_context(Image.open(io.BytesIO(payload), formats=("JPEG", "PNG")))
            _check_image(image, media_type)
            image.load()
            source_width, source_height = image.size
            image_format = image.format

            # A fresh EXIF object deliberately avoids Pillow's getexif XMP fallback.
            orientation = 1
            if "exif" in image.info:
                data = image.info["exif"]
                if type(data) is not bytes or not data:
                    raise ImageRejected("malformed_image")
                exif = Image.Exif()
                exif.load(data)
                orientation = exif.get(274, 1)
            if type(orientation) is not int or not 1 <= orientation <= 8:
                raise ImageRejected("malformed_image")
            transposes = {
                2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180,
                4: Image.Transpose.FLIP_TOP_BOTTOM, 5: Image.Transpose.TRANSPOSE,
                6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE,
                8: Image.Transpose.ROTATE_90,
            }
            if orientation != 1:
                image = stack.enter_context(image.transpose(transposes[orientation]))
            width, height = image.size
            longest = max(width, height)
            resized_width = max(1, (64 * width + longest // 2) // longest)
            resized_height = max(1, (64 * height + longest // 2) // longest)
            with image.convert("RGBA") as rgba, Image.new("RGBA", image.size, (0, 0, 0, 255)) as black:
                with Image.alpha_composite(black, rgba) as composite:
                    rgb = stack.enter_context(composite.convert("RGB"))
            with rgb.resize((resized_width, resized_height), Image.Resampling.BILINEAR) as resized:
                with Image.new("RGB", (64, 64), (0, 0, 0)) as canvas:
                    canvas.paste(resized, ((64 - resized_width) // 2, (64 - resized_height) // 2))
                    pixels = canvas.tobytes()
            return {
                "source_width": source_width, "source_height": source_height,
                "oriented_width": width, "oriented_height": height, "format": image_format,
            }, pixels
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ImageRejected("geometry") from None
    except (Warning, OSError, SyntaxError, ValueError, TypeError, EOFError,
            struct.error, KeyError, IndexError, OverflowError):
        raise ImageRejected("malformed_image") from None


def _geometry(width, height):
    if not (1 <= width <= 8192 and 1 <= height <= 8192 and width * height <= 12_000_000):
        raise ImageRejected("geometry")


def _png_header(payload):
    if (len(payload) < 33 or payload[8:16] != b"\x00\x00\x00\x0dIHDR"
            or zlib.crc32(payload[12:29]) != struct.unpack(">I", payload[29:33])[0]):
        raise ImageRejected("malformed_image")
    width, height, depth = struct.unpack(">IIB", payload[16:25])
    _geometry(width, height)
    if depth == 16:
        raise ImageRejected("mode")


def _check_image(image, media_type):
    expected = "JPEG" if media_type == "image/jpeg" else "PNG"
    if image.format != expected:
        raise ImageRejected("unsupported_format")
    _geometry(*image.size)
    if getattr(image, "n_frames", 1) != 1:
        raise ImageRejected("multiple_frames")
    allowed = ("L", "RGB") if expected == "JPEG" else ("1", "L", "LA", "P", "RGB", "RGBA")
    if image.mode not in allowed:
        raise ImageRejected("mode")
    if expected == "PNG":
        # Pillow12.3 can replace IHDR state and expose RGB/RGBA for a 16-bit
        # source. Bind both pre-load checks to the actual selected zip rawmode.
        if len(image.tile) != 1 or image.tile[0].codec_name != "zip":
            raise ImageRejected("malformed_image")
        if image.tile[0].args not in PNG_RAW_MODES[image.mode]:
            raise ImageRejected("mode")


def _plain_path(path):
    if not path.is_absolute() or ".." in path.parts:
        raise WorkerInputError()
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise WorkerInputError()
    return info


def _read_file(path, limit):
    original = _plain_path(path)
    if not stat.S_ISREG(original.st_mode) or not 1 <= original.st_size <= limit:
        raise WorkerInputError()
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino, opened.st_size)
                != (original.st_dev, original.st_ino, original.st_size)):
            raise WorkerInputError()
        data = stream.read(limit + 1)
        final = os.fstat(stream.fileno())
        current = _plain_path(path)
        identity = (opened.st_dev, opened.st_ino, opened.st_size)
        if (len(data) != opened.st_size or len(data) > limit
                or (final.st_dev, final.st_ino, final.st_size) != identity
                or (current.st_dev, current.st_ino, current.st_size) != identity):
            raise WorkerInputError()
        return data


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WorkerInputError()
        result[key] = value
    return result


def _nonfinite(value):
    raise WorkerInputError()


def _uuid(value):
    if type(value) is not str or len(value) != 36:
        return False
    try:
        return str(UUID(value)) == value
    except ValueError:
        return False


def _request(data):
    try:
        request = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        raise WorkerInputError() from None
    if (type(request) is not dict or set(request) != REQUEST_KEYS
            or request["schema"] != "market-image-decode/v1"
            or not _uuid(request["incarnation"]) or not _uuid(request["id"])
            or type(request["source_sha256"]) is not str
            or DIGEST.fullmatch(request["source_sha256"]) is None
            or type(request["encoded_bytes"]) is not int
            or not 1 <= request["encoded_bytes"] <= MAX_SOURCE
            or type(request["media_type"]) is not str
            or request["media_type"] not in ("image/jpeg", "image/png")):
        raise WorkerInputError()
    return request


def _check_job(job):
    if not stat.S_ISDIR(_plain_path(job).st_mode):
        raise WorkerInputError()
    expected = {"request.json", "input.bin"}
    seen = set()
    for entry in job.iterdir():
        if entry.name not in expected:
            raise WorkerInputError()
        seen.add(entry.name)
    if seen != expected:
        raise WorkerInputError()


def process_job(job):
    """Consume only the parent's fixed files; return exactly one bounded frame."""
    job = Path(job)
    try:
        _check_job(job)
        request = _request(_read_file(job / "request.json", MAX_HEADER))
        payload = _read_file(job / "input.bin", MAX_SOURCE)
        _check_job(job)
    except OSError:
        raise WorkerInputError() from None
    if len(payload) != request["encoded_bytes"]:
        raise WorkerInputError()
    header = {
        "schema": "market-image-decode-result/v1", "incarnation": request["incarnation"],
        "id": request["id"], "source_sha256": request["source_sha256"],
    }
    pixels = b""
    try:
        if hashlib.sha256(payload).hexdigest() != request["source_sha256"]:
            raise ImageRejected("source_mismatch")
        metadata, pixels = decode(payload, request["media_type"])
        header.update(
            status="decoded", preprocessing_version="market-rgb64/v1",
            frame_sha256=hashlib.sha256(FRAME_PREFIX + pixels).hexdigest(), **metadata,
        )
    except ImageRejected as exc:
        header.update(status="rejected", reason=exc.code)
    encoded_header = json.dumps(header, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded_header) > MAX_HEADER or len(pixels) not in (0, 12_288):
        raise WorkerInputError()
    return struct.pack("<I", len(encoded_header)) + encoded_header + pixels


def _bootstrap_pillow():
    # The parent launches a fixed interpreter with -I -S -B, before any package import.
    if sys.version_info[:3] != (3, 12, 14) or not (
        sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    ):
        raise WorkerInputError()
    packages = Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages"
    _plain_path(packages)
    pillow_root = packages / "PIL"
    _plain_path(pillow_root)
    for name, module in tuple(sys.modules.items()):
        if name == "PIL" or name.startswith("PIL."):
            origin = getattr(module, "__file__", None)
            if origin is None or not Path(origin).resolve().is_relative_to(pillow_root):
                raise WorkerInputError()
    sys.path.insert(0, str(packages))
    from PIL import Image, ImageFile, JpegImagePlugin, PngImagePlugin, __version__

    if __version__ != "12.3.0":
        raise WorkerInputError()
    for name, module in tuple(sys.modules.items()):
        if name == "PIL" or name.startswith("PIL."):
            origin = getattr(module, "__file__", None)
            if origin is None or not Path(origin).resolve().is_relative_to(pillow_root):
                raise WorkerInputError()


def main(argv=None):
    try:
        arguments = sys.argv[1:] if argv is None else argv
        if len(arguments) != 1:
            return 1
        _bootstrap_pillow()
        message = process_job(Path(arguments[0]))
        sys.stdout.buffer.write(message)
        sys.stdout.buffer.flush()
        return 0
    except BaseException:
        # Metadata, exceptions and tracebacks never become a second output channel.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
