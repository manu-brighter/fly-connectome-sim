"""Exact fixed population-excursion prerequisites, without a production decoder."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json


GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
CHANNELS = ("pam11", "ppl101", "mbon07", "mbon11")
RAYS = (
    (996917333733, 78459095728), (972369920398, 233445363856),
    (923879532511, 382683432365), (852640164354, 522498564716),
    (760405965600, 649448048330), (649448048330, 760405965600),
    (522498564716, 852640164354), (382683432365, 923879532511),
    (233445363856, 972369920398), (78459095728, 996917333733),
    (-78459095728, 996917333733), (-233445363856, 972369920398),
    (-382683432365, 923879532511), (-522498564716, 852640164354),
    (-649448048330, 760405965600), (-760405965600, 649448048330),
    (-852640164354, 522498564716), (-923879532511, 382683432365),
    (-972369920398, 233445363856), (-996917333733, 78459095728),
    (-996917333733, -78459095728), (-972369920398, -233445363856),
    (-923879532511, -382683432365), (-852640164354, -522498564716),
    (-760405965600, -649448048330), (-649448048330, -760405965600),
    (-522498564716, -852640164354), (-382683432365, -923879532511),
    (-233445363856, -972369920398), (-78459095728, -996917333733),
    (78459095728, -996917333733), (233445363856, -972369920398),
    (382683432365, -923879532511), (522498564716, -852640164354),
    (649448048330, -760405965600), (760405965600, -649448048330),
    (852640164354, -522498564716), (923879532511, -382683432365),
    (972369920398, -233445363856), (996917333733, -78459095728),
)


def _integer(value) -> None:
    if type(value) is not int or not 0 <= value <= 2**53 - 1:
        raise ValueError("Expected a nonnegative JSON-safe integer")


def _validate(count_vectors: list[list[int]], memberships: dict[str, list[int]]) -> None:
    if type(count_vectors) is not list or len(count_vectors) != 192:
        raise ValueError("Exactly 192 population count vectors required")
    for row in count_vectors:
        if type(row) is not list or len(row) != len(GROUPS):
            raise ValueError("Exactly seven counts in fixed group order required")
        for count in row:
            _integer(count)
    if type(memberships) is not dict or set(memberships) != set(GROUPS):
        raise ValueError("Exactly seven membership declarations required")
    for members in memberships.values():
        if type(members) is not list or not members:
            raise ValueError("Nonempty membership lists required")
        for member in members:
            _integer(member)
        if len(set(members)) != len(members):
            raise ValueError("Duplicate population member")
    for left, right in (("mbon07", "mbon11"), ("pam11", "ppl101")):
        if not set(memberships[left]).isdisjoint(memberships[right]):
            raise ValueError(f"Summed support requires disjoint {left}/{right} memberships")


def _fraction(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _median(values: list[Fraction]) -> Fraction:
    ordered = sorted(values)
    return (ordered[95] + ordered[96]) / 2


def _calibration(count_vectors, memberships) -> dict[str, dict[str, Fraction]]:
    channels = {}
    for name in CHANNELS:
        index, size = GROUPS.index(name), len(memberships[name])
        rates = [Fraction(2 * row[index], size) for row in count_vectors]
        offset = _median(rates)
        mad = _median([abs(rate - offset) for rate in rates])
        channels[name] = {"offset_hz": offset, "mad_hz": mad,
                          "scale_hz": max(Fraction(7413, 5000) * mad, Fraction(1), Fraction(10, size))}
    return channels


def _calibration_report(count_vectors, memberships, channels) -> dict:
    raw = json.dumps({"count_vectors": count_vectors, "memberships": memberships},
                     sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    return {
        "group_order": list(GROUPS), "memberships": deepcopy(memberships),
        "population_sizes": {name: len(memberships[name]) for name in GROUPS},
        "input_sha256": sha256(raw).hexdigest(),
        "channels": {name: {field: _fraction(value) for field, value in channel.items()}
                     for name, channel in channels.items()},
    }


def calibrate(count_vectors: list[list[int]], memberships: dict[str, list[int]]) -> dict:
    """Freeze all four offsets/MADs/scales from all 192 exact rate vectors."""
    _validate(count_vectors, memberships)
    return _calibration_report(count_vectors, memberships, _calibration(count_vectors, memberships))


def classify_coordinate(x: Fraction, y: Fraction) -> dict:
    """Open ray wedges and inclusive squared radius, with no floating arithmetic."""
    if type(x) is not Fraction or type(y) is not Fraction:
        raise ValueError("Coordinates must be exact Fractions")
    sector = None
    for index in range(20):
        lower, upper = RAYS[2 * index:2 * index + 2]
        if lower[0] * y - lower[1] * x > 0 and x * upper[1] - y * upper[0] > 0:
            if sector is not None:
                raise ValueError("Ambiguous fixed geometry")
            sector = index
    radius_squared = x * x + y * y
    eligible = radius_squared >= 4
    return {"radius_squared": _fraction(radius_squared), "radius_eligible": eligible,
            "angular_sector": sector, "qualifying_sector": sector if eligible else None}


def screen(count_vectors: list[list[int]], memberships: dict[str, list[int]]) -> dict:
    """Retain every fixed block and every necessary pair relative to the first anchor."""
    _validate(count_vectors, memberships)
    channels = _calibration(count_vectors, memberships)
    observations, coordinates = [], []
    for index, row in enumerate(count_vectors):
        z = {name: (Fraction(2 * row[GROUPS.index(name)], len(memberships[name])) - channel["offset_hz"])
             / channel["scale_hz"] for name, channel in channels.items()}
        x, y = (z["mbon07"] - z["mbon11"]) / 2, (z["pam11"] - z["ppl101"]) / 2
        coordinates.append((x, y))
        observations.append({"observation_index": index, "counts": row.copy(),
                             "x": _fraction(x), "y": _fraction(y), **classify_coordinate(x, y)})
    blocks, means = [], []
    for start in range(0, 192, 4):
        block_index = start // 4
        mean_x = sum((x for x, _ in coordinates[start:start + 4]), Fraction(0)) / 4
        mean_y = sum((y for _, y in coordinates[start:start + 4]), Fraction(0)) / 4
        means.append((mean_x, mean_y))
        sectors = [row["qualifying_sector"] for row in observations[start:start + 4]]
        geometry = sectors[0] is not None and all(sector == sectors[0] for sector in sectors)
        support, failures = {}, [] if geometry else ["geometry"]
        for name, indices in (("kc", (2,)), ("mbon_pair", (3, 4)), ("dan_pair", (0, 1))):
            counts = [sum(row[index] for index in indices) for row in count_vectors[start:start + 4]]
            total, positive = sum(counts), sum(count > 0 for count in counts)
            support[name] = {"observation_counts": [str(count) for count in counts],
                             "total_count": str(total), "positive_observations": positive,
                             "count_supported": total >= 20, "activity_supported": positive >= 3}
            if total < 20:
                failures.append(f"{name}-count")
            if positive < 3:
                failures.append(f"{name}-activity")
        blocks.append({"block_index": block_index, "observation_indices": list(range(start, start + 4)),
                       "mean_x": _fraction(mean_x), "mean_y": _fraction(mean_y),
                       "sector": sectors[0] if geometry else None, "geometry_supported": geometry,
                       "support": support, "supported": not failures, "failure_reasons": failures})
    anchor_block = next((block for block in blocks if block["supported"]), None)
    anchor, opportunities = None, []
    if anchor_block is not None:
        anchor = {key: anchor_block[key] for key in ("block_index", "sector", "mean_x", "mean_y")}
        anchor_x, anchor_y = means[anchor["block_index"]]
        for index in range(anchor["block_index"] + 1, 47):
            pair = blocks[index:index + 2]
            distances = [(x - anchor_x)**2 + (y - anchor_y)**2 for x, y in means[index:index + 2]]
            if (all(block["supported"] for block in pair) and pair[0]["sector"] == pair[1]["sector"]
                    and all(distance >= 4 for distance in distances)):
                opportunities.append({"block_indices": [index, index + 1], "sector": pair[0]["sector"],
                                      "distance_squared_from_anchor": [_fraction(distance) for distance in distances],
                                      "status": "necessary-opportunity-only"})
    return {
        "calibration": _calibration_report(count_vectors, memberships, channels),
        "observations": observations, "blocks": blocks, "anchor": anchor, "opportunities": opportunities,
        "stopping_condition": "no-anchor" if anchor is None else
                              "necessary-opportunity-only" if opportunities else "no-necessary-opportunity",
    }
