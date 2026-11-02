"""Closed proposal intake and deterministic genuine event scenes."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pytest


def example():
    return {
        "version": "event-options/v1",
        "brief": {"title": "Summer team party", "guests": 100, "max_budget_chf": 5000},
        "options": [
            {"id": "sunset-house", "title": "Sunset House", "setting": "rooftop",
             "music": "House", "budget_chf": 4800, "capacity": 120,
             "duration_minutes": 240,
             "programme": [{"start_minute": 0, "label": "Welcome drinks"},
                           {"start_minute": 60, "label": "DJ and dancing"}]},
            {"id": "warehouse-techno", "title": "Warehouse Techno", "setting": "warehouse",
             "music": "Techno", "budget_chf": 4500, "capacity": 150,
             "duration_minutes": 300,
             "programme": [{"start_minute": 0, "label": "Doors and food"},
                           {"start_minute": 90, "label": "Techno set"}]},
        ],
    }


def test_valid_proposal_is_frozen_copy_and_exact_example(tmp_path):
    from fly_connectome_sim.experiment.event_cards import load_event_proposal, validate_event_proposal

    value = example()
    result = validate_event_proposal(value)
    value["options"][0]["programme"][0]["label"] = "Changed"
    assert result == example()
    path = tmp_path / "options.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert load_event_proposal(path) == result
    assert load_event_proposal(Path(__file__).parents[2] / "examples/event-options.json") == result


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(selected_option_id="sunset-house"),
    lambda p: p["options"][0].update(asset="https://example.test/image"),
    lambda p: p["brief"].update(guests=True),
    lambda p: p["brief"].update(guests=9),
    lambda p: p["options"].pop(),
    lambda p: p["options"][1].update(id="sunset-house"),
    lambda p: p["options"][0].update(title="<script>" + "x" * 50),
    lambda p: p["options"][0].update(music="https://test"),
    lambda p: p["options"][0].update(title="Line\nBreak"),
    lambda p: p["options"][0].update(setting="beach"),
    lambda p: p["options"][0].update(budget_chf=5001),
    lambda p: p["options"][0].update(capacity=99),
    lambda p: p["options"][0].update(duration_minutes=59),
    lambda p: p["options"][0]["programme"][0].update(start_minute=1),
    lambda p: p["options"][0]["programme"][1].update(start_minute=0),
    lambda p: p["options"][0]["programme"][1].update(start_minute=240),
    lambda p: p["options"][0]["programme"][1].update(start_minute=True),
])
def test_proposal_rejects_open_fields_and_invalid_values(mutation):
    from fly_connectome_sim.experiment.event_cards import validate_event_proposal

    value = example()
    mutation(value)
    with pytest.raises(ValueError):
        validate_event_proposal(value)


@pytest.mark.parametrize("raw", [b'{"version":1,"version":2}', b'{"x":NaN}', b' ' * 65537, b'\xff'],
                         ids=["duplicate", "nonfinite", "oversized", "utf8"])
def test_loader_rejects_duplicate_nonfinite_oversized_and_bad_utf8(tmp_path, raw):
    from fly_connectome_sim.experiment.event_cards import load_event_proposal

    path = tmp_path / "options.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        load_event_proposal(path)


def test_render_has_frozen_scene_pixels_and_visible_proposal_text():
    from fly_connectome_sim.experiment.event_cards import render_event_cards

    proposal = example()
    frame = render_event_cards(proposal)
    assert frame.shape == (216, 384, 3) and frame.dtype == np.uint8
    assert frame.flags.writeable is False
    np.testing.assert_array_equal(frame, render_event_cards(deepcopy(proposal)))
    assert not np.array_equal(frame[:, :192], frame[:, 192:])
    assert sha256(frame.tobytes()).hexdigest() == "a072fa0ac3e23b83707005d69faf03304ee9d1785630b1b3cc58f909ae214147"
    changed = deepcopy(proposal)
    changed["options"][0]["title"] = "New title"
    assert not np.array_equal(frame, render_event_cards(changed))
    changed["options"][0]["setting"] = "warehouse"
    assert not np.array_equal(frame[70:170, :192], render_event_cards(changed)[70:170, :192])


def test_visible_capacity_label_does_not_claim_actual_attendance(monkeypatch):
    from PIL import ImageDraw
    from fly_connectome_sim.experiment.event_cards import render_event_cards

    labels = []
    original = ImageDraw.ImageDraw.text
    def capture(self, xy, text, *args, **kwargs):
        labels.append(text)
        return original(self, xy, text, *args, **kwargs)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    render_event_cards(example())
    assert "CHF 4800 | cap 120" in labels and "CHF 4500 | cap 150" in labels
    assert not any("120 guests" in label or "150 guests" in label for label in labels)


def test_exact_byte_limit_and_maximum_valid_fields_remain_renderable(tmp_path):
    from fly_connectome_sim.experiment.event_cards import load_event_proposal, render_event_cards, validate_event_proposal

    value = example()
    value["brief"] = {"title": "X" * 48, "guests": 500, "max_budget_chf": 100000}
    for option in value["options"]:
        option.update(title="M" * 48, music="M" * 24, capacity=1000,
                      budget_chf=100000, duration_minutes=600,
                      programme=[{"start_minute": n * 100, "label": "L" * 40} for n in range(6)])
    assert validate_event_proposal(value) == value
    frame = render_event_cards(value)
    assert frame.shape == (216, 384, 3) and frame.dtype == np.uint8
    raw = json.dumps(value).encode("utf-8")
    path = tmp_path / "limit.json"
    path.write_bytes(raw + b" " * (65536 - len(raw)))
    assert load_event_proposal(path) == value
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        load_event_proposal(path)
