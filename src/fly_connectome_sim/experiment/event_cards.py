"""Closed imported event proposals and deterministic synthetic event cards."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageFont

from .recorder import RunArtifactError, _canonical, _strict_load


MAX_PROPOSAL_BYTES = 64 * 1024
WIDTH = 384
HEIGHT = 216
RENDERER_RECIPE = {
    "version": "event-cards/v1", "pillow_version": "12.3.0",
    "font": "Pillow-load_default", "font_size": 12, "width": WIDTH, "height": HEIGHT,
}
OPTION_FIELDS = {"id", "title", "setting", "music", "budget_chf", "capacity",
                 "duration_minutes", "programme"}


def _object(value: object, fields: set[str], name: str) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise RunArtifactError(f"Invalid or unsupported {name} fields")
    return value


def _integer(value: object, low: int, high: int, name: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise RunArtifactError(f"Invalid {name}")
    return value


def _text(value: object, limit: int, name: str) -> str:
    if (type(value) is not str or not 1 <= len(value) <= limit
            or any(not 32 <= ord(char) <= 126 for char in value)
            or re.search(r"(?:[a-z][a-z0-9+.-]*://|www\.)", value, re.IGNORECASE)):
        raise RunArtifactError(f"Invalid printable ASCII {name}")
    return value


def validate_event_proposal(value: object) -> dict:
    """Return a deep canonical copy; input text never supplies selection authority."""
    root = _object(value, {"version", "brief", "options"}, "proposal")
    if root["version"] != "event-options/v1":
        raise RunArtifactError("Unsupported event proposal version")
    brief = _object(root["brief"], {"title", "guests", "max_budget_chf"}, "brief")
    _text(brief["title"], 48, "brief title")
    guests = _integer(brief["guests"], 10, 500, "guests")
    budget = _integer(brief["max_budget_chf"], 100, 100000, "maximum budget")
    options = root["options"]
    if type(options) is not list or len(options) != 2:
        raise RunArtifactError("Exactly two event options are required")
    identifiers = set()
    for option in options:
        _object(option, OPTION_FIELDS, "option")
        identifier = option["id"]
        if (type(identifier) is not str or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", identifier)
                or identifier in identifiers):
            raise RunArtifactError("Invalid or duplicate option ID")
        identifiers.add(identifier)
        _text(option["title"], 48, "option title")
        _text(option["music"], 24, "music")
        if option["setting"] not in ("rooftop", "warehouse"):
            raise RunArtifactError("Unsupported event setting")
        _integer(option["budget_chf"], 100, budget, "option budget")
        _integer(option["capacity"], guests, 1000, "capacity")
        duration = _integer(option["duration_minutes"], 60, 600, "duration")
        programme = option["programme"]
        if type(programme) is not list or not 2 <= len(programme) <= 6:
            raise RunArtifactError("Programme requires two to six entries")
        previous = -1
        for index, item in enumerate(programme):
            _object(item, {"start_minute", "label"}, "programme entry")
            minute = _integer(item["start_minute"], 0, duration - 1, "programme minute")
            if minute <= previous or (index == 0 and minute != 0):
                raise RunArtifactError("Programme must begin at zero and increase strictly")
            previous = minute
            _text(item["label"], 40, "programme label")
    return _strict_load(_canonical(root))


def _load(path: str | Path) -> tuple[dict, bytes]:
    with Path(path).open("rb") as source:
        raw = source.read(MAX_PROPOSAL_BYTES + 1)
    if not 1 <= len(raw) <= MAX_PROPOSAL_BYTES:
        raise RunArtifactError("Proposal exceeds 64 KiB or is empty")
    return validate_event_proposal(_strict_load(raw)), raw


def load_event_proposal(path: str | Path) -> dict:
    """Read at most 64 KiB of strict UTF-8 JSON with duplicate rejection."""
    return _load(path)[0]


def load_proposal_with_source(path: str | Path) -> tuple[dict, dict]:
    proposal, raw = _load(path)
    name = Path(path).name
    _text(name, 80, "proposal source name")
    if any(char in name for char in '/\\:') or name in {".", ".."}:
        raise RunArtifactError("Invalid proposal source basename")
    return proposal, {"kind": "imported-json", "name": name,
                      "size_bytes": len(raw), "raw_sha256": sha256(raw).hexdigest()}


def _scene(draw: ImageDraw.ImageDraw, setting: str) -> None:
    # Fixed geometry is an illustration of each declared venue, not neural semantics.
    if setting == "rooftop":
        for y in range(56, 158):
            fraction = (y - 56) / 101
            draw.line((0, y, 183, y), fill=(int(235 - 95 * fraction), int(125 - 65 * fraction), 112))
        draw.ellipse((123, 68, 154, 99), fill=(255, 212, 126))
        for x, top, width in [(0, 112, 23), (20, 103, 18), (36, 117, 22),
                              (57, 97, 19), (74, 110, 24), (96, 119, 22), (160, 105, 24)]:
            draw.rectangle((x, top, x + width, 145), fill=(43, 48, 66))
        draw.rectangle((0, 142, 183, 157), fill=(50, 55, 66))
        draw.line((0, 133, 183, 133), fill=(209, 196, 166), width=2)
        for x in range(10, 184, 32):
            draw.line((x, 133, x, 157), fill=(209, 196, 166), width=2)
    else:
        draw.rectangle((0, 56, 183, 157), fill=(20, 25, 43))
        for x in (8, 88, 174):
            draw.rectangle((x, 62, x + 3, 157), fill=(106, 115, 130))
        for y in (66, 79):
            draw.line((8, y, 177, y), fill=(106, 115, 130), width=2)
        for x in range(10, 168, 18):
            draw.line((x, 66, x + 18, 79), fill=(106, 115, 130))
            draw.line((x, 79, x + 18, 66), fill=(106, 115, 130))
        draw.polygon([(28, 81), (3, 149), (86, 149)], fill=(61, 43, 101))
        draw.polygon([(146, 81), (100, 149), (181, 149)], fill=(26, 83, 110))
        draw.rectangle((0, 150, 183, 157), fill=(43, 44, 58))
    draw.rectangle((64, 118, 120, 142), fill=(25, 28, 39), outline=(212, 195, 154))
    draw.ellipse((83, 99, 96, 112), fill=(222, 177, 135))
    draw.rectangle((84, 112, 96, 121), fill=(18, 25, 40))
    draw.line((82, 115, 73, 124), fill=(222, 177, 135), width=3)
    draw.line((97, 115, 110, 123), fill=(222, 177, 135), width=3)
    for x, y in [(18, 145), (40, 138), (64, 152), (91, 149), (127, 145), (154, 138), (174, 151)]:
        draw.ellipse((x - 4, y - 12, x + 4, y - 4), fill=(197, 159, 138))
        draw.rectangle((x - 5, y - 3, x + 5, 157), fill=(21 + x % 30, 35, 56))


def _lines(draw: ImageDraw.ImageDraw, text: str, font, width: int, maximum: int) -> list[str]:
    # Character wrapping also bounds unbroken words; clipping is card-local.
    lines = [""]
    for char in text:
        if draw.textlength(lines[-1] + char, font=font) > width:
            if len(lines) == maximum:
                while lines[-1] and draw.textlength(lines[-1] + "...", font=font) > width:
                    lines[-1] = lines[-1][:-1]
                lines[-1] += "..."
                break
            lines.append("")
        lines[-1] += char
    return lines


def render_event_cards(proposal: dict) -> np.ndarray:
    """Render the ordered left/right proposal with the pinned bundled font."""
    proposal = validate_event_proposal(proposal)
    if PIL.__version__ != RENDERER_RECIPE["pillow_version"]:
        raise RunArtifactError("Event cards require Pillow 12.3.0")
    font = ImageFont.load_default(size=12)
    image = Image.new("RGB", (WIDTH, HEIGHT), (12, 18, 30))
    for index, option in enumerate(proposal["options"]):
        card = Image.new("RGB", (184, 200), (239, 233, 217))
        draw = ImageDraw.Draw(card)
        draw.rectangle((0, 0, 183, 20), fill=(38, 55, 69))
        draw.text((8, 3), "LEFT" if index == 0 else "RIGHT", font=font, fill=(249, 239, 208))
        for row, line in enumerate(_lines(draw, option["title"], font, 168, 2)):
            draw.text((8, 23 + row * 14), line, font=font, fill=(21, 29, 36))
        _scene(draw, option["setting"])
        music = _lines(draw, option["music"], font, 168, 1)[0]
        draw.text((8, 161), music, font=font, fill=(21, 29, 36))
        draw.text((8, 176), f"CHF {option['budget_chf']} | cap {option['capacity']}", font=font, fill=(21, 29, 36))
        image.paste(card, (4 + index * 192, 8))
    result = np.array(image, dtype=np.uint8)
    result.flags.writeable = False
    return result
