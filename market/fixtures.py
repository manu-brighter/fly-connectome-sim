"""Strict configuration and synthetic-scenario input for the local test board."""

import json
from pathlib import Path

from .price_service import FixtureScenario, MarketConfig, MarketError, _validate_scenario


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MarketError("invalid_request")
        result[key] = value
    return result


def _invalid_constant(value):
    raise MarketError("invalid_request")


def _decode_json(data: bytes):
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise MarketError("invalid_request") from None


def parse_scenario(payload: object) -> FixtureScenario:
    if type(payload) is not dict or set(payload) != {
        "fixture_id", "drink_id", "target_rappen", "expected_drink_version",
    }:
        raise MarketError("invalid_request")
    result = FixtureScenario(**payload)
    _validate_scenario(result)
    return result


def load_config(path: Path) -> MarketConfig:
    return MarketConfig.from_dict(_decode_json(path.read_bytes()))
