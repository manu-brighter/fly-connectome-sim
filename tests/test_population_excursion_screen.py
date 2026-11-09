"""Fixed engineering screen, synthetic recordings only; never native acquisition."""

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from fly_connectome_sim.experiment import recorder as artifacts
from test_continuous_motor_probe import FixtureEngine, reseal


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")
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


@pytest.fixture(autouse=True)
def forbid_native_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Population screen attempted native construction/replay or network")
    from fly_connectome_sim.engine import FlyEngine
    monkeypatch.setattr(FlyEngine, "__init__", forbidden)
    monkeypatch.setattr(FlyEngine, "from_prepared_graph", forbidden)
    monkeypatch.setattr(artifacts, "verify_replay_run", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def load(name, filename):
    path = SCRIPTS / filename
    assert path.is_file(), f"Missing population screen implementation: {filename}"
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def state():
    return load("population_screen_math_test", "market_population_state.py")


def analyzer():
    return load("population_screen_test", "screen-population-excursion.py")


def fraction(value):
    value = Fraction(value)
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def memberships(size=10):
    return {name: list(range(index * size, (index + 1) * size)) for index, name in enumerate(GROUPS)}


def rows():
    return [[10, 10, 5, 10, 10, 0, 0] for _ in range(192)]


def positive_rows():
    values = rows()
    values[4:8] = [[20, 10, 5, 30, 10, 0, 0] for _ in range(4)]  # (2,1)
    for block in (3, 4, 6, 7, 8):
        values[4 * block:4 * block + 4] = [[30, 10, 5, 50, 10, 0, 0] for _ in range(4)]  # (4,2)
    return values


def test_constant_trace_and_digest_cover_all_counts_memberships_without_aliases():
    module, values, groups = state(), rows(), memberships()
    result = module.screen(values, groups)
    assert len(result["observations"]) == 192 and len(result["blocks"]) == 48
    assert result["anchor"] is None and result["opportunities"] == []
    assert result["stopping_condition"] == "no-anchor"
    assert all(row["x"] == row["y"] == fraction(0) for row in result["observations"])
    calibration = result["calibration"]
    assert calibration["channels"]["pam11"] == {
        "offset_hz": fraction(2), "mad_hz": fraction(0), "scale_hz": fraction(1),
    }
    expected = sha256((json.dumps({"count_vectors": values, "memberships": groups}, sort_keys=True,
                                 separators=(",", ":")) + "\n").encode()).hexdigest()
    assert calibration["input_sha256"] == expected
    values[-1][-1] = 1
    assert module.calibrate(values, groups)["input_sha256"] != expected
    assert result["observations"][-1]["counts"][-1] == 0
    groups["kc"].reverse()
    assert calibration["memberships"]["kc"] == list(range(20, 30))


@pytest.mark.parametrize("size,offset,mad,scale", [
    (1, 3, 1, 10), (10, Fraction(3, 10), Fraction(1, 10), 1),
    (1, 30, 10, Fraction(7413, 500)),
])
def test_even_median_mad_and_both_fixed_floors(size, offset, mad, scale):
    # Literal 96/96 split proves middle averaging and exact 7413/5000.
    low, high = ((10, 20) if offset == 30 else (1, 2))
    values = [[low] * 7 for _ in range(96)] + [[high] * 7 for _ in range(96)]
    calibration = state().calibrate(values, memberships(size))
    assert set(calibration["channels"]) == {"pam11", "ppl101", "mbon07", "mbon11"}
    for channel in calibration["channels"].values():
        assert channel == {"offset_hz": fraction(offset), "mad_hz": fraction(mad), "scale_hz": fraction(scale)}


@pytest.mark.parametrize("bad", [True, -1, 1.0, Fraction(1), 2**53, None])
def test_invalid_raw_counts_rejected(bad):
    values = rows()
    values[191][6] = bad
    with pytest.raises(ValueError):
        state().screen(values, memberships())


@pytest.mark.parametrize("problem", ["short", "long", "width", "tuple", "missing", "extra", "empty", "duplicate", "bool", "negative", "unsafe", "mbon-overlap", "dan-overlap"])
def test_complete_shape_and_membership_validation_precede_calibration(problem):
    values, groups = rows(), memberships()
    if problem == "short": values.pop()
    elif problem == "long": values.append(values[0])
    elif problem == "width": values[-1].append(0)
    elif problem == "tuple": values[-1] = tuple(values[-1])
    elif problem == "missing": groups.pop("kc")
    elif problem == "extra": groups["other"] = [99]
    elif problem == "empty": groups["kc"] = []
    elif problem == "duplicate": groups["kc"] = [2, 2]
    elif problem == "bool": groups["kc"] = [True]
    elif problem == "negative": groups["kc"] = [-1]
    elif problem == "unsafe": groups["kc"] = [2**53]
    elif problem == "mbon-overlap": groups["mbon11"].append(groups["mbon07"][0])
    else: groups["ppl101"].append(groups["pam11"][0])
    with pytest.raises(ValueError):
        state().calibrate(values, groups)


def test_other_population_overlap_is_allowed_and_large_derived_values_are_strings():
    groups = memberships()
    groups["kc"] = groups["pam11"].copy()
    values = [[2**53 - 1] * 7 for _ in range(192)]
    result = state().screen(values, groups)
    support = result["blocks"][0]["support"]
    assert support["dan_pair"]["total_count"] == "72057594037927928"
    assert support["dan_pair"]["observation_counts"] == ["18014398509481982"] * 4
    assert support["kc"]["total_count"] == "36028797018963964"
    json.dumps(result, allow_nan=False)


def test_geometry_frozen_table_digest_symmetry_and_twenty_distinct_interiors():
    module = state()
    encoded = (json.dumps(module.RAYS, separators=(",", ":")) + "\n").encode()
    assert len(encoded) == 1154
    assert sha256(encoded).hexdigest() == "d0c360a8c9dcdb9bc06ef82bdb119fd95ff8274b1f0487f197e93058713545a1"
    assert tuple(module.RAYS) == RAYS
    for index in range(20):
        lower, upper = RAYS[2 * index:2 * index + 2]
        x, y = Fraction(lower[0] + upper[0]), Fraction(lower[1] + upper[1])
        classified = module.classify_coordinate(x, y)
        assert classified["angular_sector"] == classified["qualifying_sector"] == index
        assert RAYS[(2 * index + 20) % 40] == tuple(-v for v in lower)
        assert module.classify_coordinate(-y, x)["angular_sector"] == (index + 5) % 20


@pytest.mark.parametrize("x,y", [*RAYS, (3, 0), (0, 3), (-3, 0), (0, -3), (0, 0)])
def test_open_boundary_rays_and_axis_gaps_abstain(x, y):
    result = state().classify_coordinate(Fraction(x), Fraction(y))
    assert result["angular_sector"] is None and result["qualifying_sector"] is None


def test_radius_inclusive_equality_and_strict_angle_with_signed_reduced_fractions():
    module = state()
    result = module.classify_coordinate(Fraction(24, 13), Fraction(10, 13))
    assert result == {"radius_squared": fraction(4), "radius_eligible": True,
                      "angular_sector": 1, "qualifying_sector": 1}
    small = module.classify_coordinate(Fraction(24, 13) * Fraction(999, 1000), Fraction(10, 13) * Fraction(999, 1000))
    assert small["angular_sector"] == 1 and not small["radius_eligible"] and small["qualifying_sector"] is None
    values = rows()
    values[0] = [0, 10, 5, 0, 10, 0, 0]
    assert module.screen(values, memberships())["observations"][0]["x"] == fraction(-1)
    with pytest.raises(ValueError):
        module.classify_coordinate(2.0, Fraction(1))


def test_first_anchor_fixed_alignment_and_every_unranked_same_sector_opportunity():
    result = state().screen(positive_rows(), memberships())
    assert result["anchor"] == {"block_index": 1, "sector": 1, "mean_x": fraction(2), "mean_y": fraction(1)}
    assert [value["block_indices"] for value in result["opportunities"]] == [[3, 4], [6, 7], [7, 8]]
    for opportunity in result["opportunities"]:
        assert opportunity["status"] == "necessary-opportunity-only"
        assert opportunity["sector"] == 1
        assert opportunity["distance_squared_from_anchor"] == [fraction(5), fraction(5)]
    assert result["stopping_condition"] == "necessary-opportunity-only"
    assert [block["observation_indices"] for block in result["blocks"]] == [list(range(i, i + 4)) for i in range(0, 192, 4)]


@pytest.mark.parametrize("kc,positive,want", [(19, 3, False), (20, 2, False), (20, 3, True)])
def test_support_inclusive_twenty_and_at_least_three_active_samples(kc, positive, want):
    values = positive_rows()
    counts = ([kc // 2, kc - kc // 2, 0, 0] if positive == 2 else [1, 1, kc - 2, 0])
    for i, count in enumerate(counts, 4): values[i][2] = count
    block = state().screen(values, memberships())["blocks"][1]
    assert block["supported"] is want
    assert block["support"]["kc"]["total_count"] == str(kc)
    assert block["support"]["kc"]["positive_observations"] == positive
    assert block["support"]["kc"]["observation_counts"] == [str(c) for c in counts]


@pytest.mark.parametrize("pair,index,other_index", [("dan_pair", 0, 3), ("mbon_pair", 3, 0)])
@pytest.mark.parametrize("total,want", [(19, False), (20, True)])
def test_each_disjoint_pair_count_floor_is_independently_required(pair, index, other_index, total, want):
    values = [[0] * 7 for _ in range(192)]
    for observation, count in enumerate((5, 5, 5, total - 15)):
        values[observation][2] = 5
        values[observation][index] = count
        values[observation][other_index] = 30
    block = state().screen(values, memberships())["blocks"][0]
    assert block["geometry_supported"]
    assert block["support"][pair]["count_supported"] is want
    assert block["support"][pair]["total_count"] == str(total)
    assert block["supported"] is want


def test_terminal_adjacent_pair_is_retained_and_anchor_is_never_reselected():
    values = rows()
    values[180:184] = [[20, 10, 5, 30, 10, 0, 0] for _ in range(4)]
    values[184:192] = [[30, 10, 5, 50, 10, 0, 0] for _ in range(8)]
    result = state().screen(values, memberships())
    assert result["anchor"]["block_index"] == 45
    assert [opportunity["block_indices"] for opportunity in result["opportunities"]] == [[46, 47]]
    assert result["observations"][191]["x"] == fraction(4)


@pytest.mark.parametrize("problem", ["radius", "angle", "mixed", "shifted", "interrupted", "one-close", "both-close"])
def test_no_sliding_or_nonadjacent_or_one_block_confirmation(problem):
    values = rows()
    values[4:8] = [[20, 10, 5, 30, 10, 0, 0] for _ in range(4)]
    values[12:20] = [[30, 10, 5, 50, 10, 0, 0] for _ in range(8)]
    if problem == "radius": values[12] = rows()[0]
    elif problem == "angle": values[12] = [10, 10, 5, 50, 10, 0, 0]
    elif problem == "mixed": values[12] = [50, 10, 5, 30, 10, 0, 0]
    elif problem == "shifted": values = values[1:] + values[:1]
    elif problem == "interrupted": values[16:20], values[20:24] = rows()[:4], values[16:20]
    elif problem == "one-close": values[16:20] = [[25, 10, 5, 40, 10, 0, 0] for _ in range(4)]
    else: values[12:20] = [[25, 10, 5, 40, 10, 0, 0] for _ in range(8)]
    result = state().screen(values, memberships())
    assert result["opportunities"] == []
    if problem != "shifted": assert result["anchor"]["block_index"] == 1


def test_exact_squared_excursion_four_is_inclusive_and_all_failures_retained():
    values = rows()
    values[0:4] = [[25, 10, 5, 40, 10, 0, 0] for _ in range(4)]  # (3,1.5), sector1
    values[8:16] = [[45, 10, 5, 40, 10, 0, 0] for _ in range(8)]  # (3,3.5), sector2
    result = state().screen(values, memberships())
    assert [o["block_indices"] for o in result["opportunities"]] == [[2, 3]]
    assert result["opportunities"][0]["distance_squared_from_anchor"] == [fraction(4), fraction(4)]
    zeros = state().screen([[0] * 7 for _ in range(192)], memberships())["blocks"][0]
    assert set(zeros["failure_reasons"]) == {
        "geometry", "kc-count", "kc-activity", "mbon_pair-count", "mbon_pair-activity", "dan_pair-count", "dan_pair-activity",
    }


class PopulationFixtureEngine(FixtureEngine):
    """Faithful nonzero bins/rates/whole-brain total, with dummy checkpoints."""

    def __init__(self, values):
        super().__init__()
        self.values = values
        groups = memberships()
        groups.update(motor_left=[50], motor_right=[60])
        self._identity["neural_groups"] = groups
        self._identity["sha256"] = sha256(artifacts._canonical({
            k: v for k, v in self._identity.items() if k != "sha256"})).hexdigest()

    def observe(self, *args, **kwargs):
        row = self.values[len(self.calls)]
        telemetry = super().observe(*args, **kwargs)
        for slot, native in enumerate(telemetry["bins"]):
            # Distributed counts force extraction to include every bin, including last.
            native["group_spikes"] = {name: count // 50 + int(slot < count % 50)
                                      for name, count in zip(GROUPS, row)}
        telemetry["rates_hz"] = {name: count / (0.5 * len(self._identity["neural_groups"][name]))
                                 for name, count in zip(GROUPS, row)}
        telemetry["total_spikes"] = sum(row)
        return telemetry


def recording(tmp_path, monkeypatch, values=None):
    module = analyzer()
    probe = module.PROBE
    engine = PopulationFixtureEngine(positive_rows() if values is None else values)
    locks = tmp_path / "synthetic-locks"
    locks.mkdir()
    (locks / "arrays.lock.json").write_bytes(artifacts._canonical({
        name: engine._identity["model_provenance"][f"graph_{name}_sha256"] for name in ("ids", "ptr", "post")}))
    monkeypatch.setattr(probe, "LOCKS", locks)
    output = tmp_path / "synthetic-probe"
    probe.prepare_probe(output)
    digest = sha256((output / "protocol.json").read_bytes()).hexdigest()
    timer = iter(range(1000, 1000 + 5760, 10))
    probe.run_probe(output, expected_protocol_sha256=digest, engine_factory=lambda: engine, clock_ms=lambda: next(timer))
    pins = {"expected_protocol_sha256": digest,
            "expected_manifest_sha256": sha256((output / "run/run.json").read_bytes()).hexdigest(),
            "expected_events_sha256": sha256((output / "run/events.jsonl").read_bytes()).hexdigest()}
    monkeypatch.setattr(probe.FlyEngine, "from_prepared_graph", lambda: pytest.fail("Forbidden native engine"))
    return module, output, pins


def test_full_nonzero_synthetic_extraction_preserves_clocks_sources_and_v1(tmp_path, monkeypatch):
    module, output, pins = recording(tmp_path, monkeypatch)
    report = module.analyze_probe(output, **pins)
    assert report["version"] == "market-population-excursion-screen/v1"
    assert report["scope"] == "development-prerequisite-screen" and report["verification_mode"] == "integrity-only"
    assert report["exact_counts"]["observations"] == 192 and report["exact_counts"]["native_bins"] == 9600
    assert [row["counts"] for row in report["observations"]] == positive_rows()
    assert len(report["blocks"]) == 48 and len(report["opportunities"]) == 3
    assert report["anchor"]["block_index"] == 1
    assert report["original_v1_summary"] == json.loads((output / "summary.json").read_bytes())
    for index in (0, 1, 191):
        provenance = report["observations"][index]["provenance"]
        assert provenance["motor_sample"]["observation_index"] == index
        assert provenance["motor_sample"]["wall_start_ms"] == 1000 + index * 30
        assert provenance["motor_sample"]["wall_completion_ms"] == 1010 + index * 30
        assert provenance["readout_now_ms"] == 1020 + index * 30
        assert provenance["start_tick"] == index * 5000 and provenance["end_tick"] == (index + 1) * 5000
        assert provenance["input_sha256"] == module.PROBE._protocol()["frame_sha256"][provenance["stimulus"]]
    assert report["observations"][0]["provenance"]["stimulus"] == "black"
    assert report["observations"][-1]["provenance"]["stimulus"] == "S1"
    assert report["source"]["original_protocol"] == module.PROBE._protocol()["source"]
    for path, digest in report["source"]["analyzer_files_sha256"].items():
        assert sha256((ROOT / path).read_bytes()).hexdigest() == digest
    destination = tmp_path / "report.json"
    module.write_report(report, destination)
    assert json.loads(destination.read_bytes()) == report
    assert not any(key in report for key in ("pass", "proposals", "scientific_pass"))


def test_constant_synthetic_full_null_integration(tmp_path, monkeypatch):
    module, output, pins = recording(tmp_path, monkeypatch, rows())
    report = module.analyze_probe(output, **pins)
    assert report["anchor"] is None and report["opportunities"] == []


def test_two_owned_full_eof_scans_use_the_same_snapshot_after_originals_mutate(tmp_path, monkeypatch):
    module, output, pins = recording(tmp_path, monkeypatch)
    verify = artifacts.verify_run
    completed = []

    def wrapped_verify(path, **kwargs):
        run = verify(path, **kwargs)
        original = run.iter_events

        def events():
            count = 0
            try:
                for event in original():
                    count += 1
                    yield event
                completed.append(count)
                if len(completed) == 1:
                    (output / "run/events.jsonl").write_bytes(b"mutated original\n")
                    (output / "run/run.json").write_bytes(b"{}\n")
            finally:
                pass
        monkeypatch.setattr(type(run), "iter_events", lambda self: events())
        return run
    monkeypatch.setattr(artifacts, "verify_run", wrapped_verify)
    report = module.analyze_probe(output, **pins)
    assert completed == [194, 194]
    assert [row["counts"] for row in report["observations"]] == positive_rows()


@pytest.mark.parametrize("pin", ["protocol", "manifest", "events"])
def test_wrong_pins_reject_before_any_success_report(tmp_path, monkeypatch, pin):
    module, output, pins = recording(tmp_path, monkeypatch)
    pins[f"expected_{pin}_sha256"] = "0" * 64
    with pytest.raises(ValueError): module.analyze_probe(output, **pins)
    assert not (tmp_path / "screen.json").exists()


@pytest.mark.parametrize("problem", ["result", "rate", "counts", "late", "pair-overlap"])
def test_complete_v1_semantics_and_new_pair_precondition_are_both_required(tmp_path, monkeypatch, problem):
    module, output, pins = recording(tmp_path, monkeypatch)

    def mutate(metadata, events):
        event = events[-2] if problem == "late" else events[1]
        if problem in ("result", "late"): event["readout_result"]["status"] = "invented"
        elif problem == "rate": event["telemetry"]["rates_hz"]["pam11"] += 1
        elif problem == "counts": event["telemetry"]["bins"][-1]["group_spikes"]["pam11"] = True
        else:
            identity = metadata["engine_identity"]
            identity["neural_groups"]["ppl101"] = identity["neural_groups"]["pam11"].copy()
            identity["sha256"] = sha256(artifacts._canonical({k: v for k, v in identity.items() if k != "sha256"})).hexdigest()
            for row in events[1:-1]:
                row["telemetry"]["engine_identity"] = deepcopy(identity)
                for native in row["telemetry"]["bins"]:
                    native["group_spikes"]["ppl101"] = native["group_spikes"]["pam11"]
                row["telemetry"]["rates_hz"]["ppl101"] = row["telemetry"]["rates_hz"]["pam11"]
    if problem == "pair-overlap":
        reseal(output, mutate)
        pins["expected_manifest_sha256"] = sha256((output / "run/run.json").read_bytes()).hexdigest()
        pins["expected_events_sha256"] = sha256((output / "run/events.jsonl").read_bytes()).hexdigest()
        # The frozen inspector permits this overlap. Only the new candidate rejects it.
        assert module.PROBE.inspect_probe(output)["exact_counts"]["observations"] == 192
        with pytest.raises(ValueError, match="disjoint pam11/ppl101 memberships"):
            module.analyze_probe(output, **pins)
    else:
        with pytest.raises(ValueError):
            reseal(output, mutate)
            pins["expected_manifest_sha256"] = sha256((output / "run/run.json").read_bytes()).hexdigest()
            pins["expected_events_sha256"] = sha256((output / "run/events.jsonl").read_bytes()).hexdigest()
            module.analyze_probe(output, **pins)


@pytest.mark.parametrize("scan", [1, 2])
def test_error_path_explicitly_closes_each_event_generator(tmp_path, monkeypatch, scan):
    module, output, pins = recording(tmp_path, monkeypatch)
    original_iter = artifacts.VerifiedRun.iter_events
    closed, calls = [], []

    def events(self):
        calls.append(True)
        ordinal = len(calls)
        with __import__("contextlib").closing(original_iter(self)) as stream:
            try:
                for index, event in enumerate(stream):
                    if ordinal == scan and index == 2: raise ValueError("synthetic stream failure")
                    yield event
            finally: closed.append(ordinal)
    monkeypatch.setattr(artifacts.VerifiedRun, "iter_events", events)
    with pytest.raises(ValueError, match="synthetic stream failure"):
        module.analyze_probe(output, **pins)
    assert closed == list(range(1, scan + 1))


@pytest.mark.parametrize("target,cap", [("protocol.json", 2 * 1024**2), ("run/run.json", 2 * 1024**2),
                                        ("run/events.jsonl", 64 * 1024**2), ("run/checkpoints/brain-after.npz", 64 * 1024**2)])
def test_input_caps_are_reused(tmp_path, monkeypatch, target, cap):
    module, output, pins = recording(tmp_path, monkeypatch)
    with (output / target).open("wb") as stream: stream.truncate(cap + 1)
    with pytest.raises(ValueError): module.analyze_probe(output, **pins)


def test_report_newline_inclusive_cap_atomic_collision_and_invalid_numbers(tmp_path):
    module = analyzer()
    cap = 4 * 1024**2
    # Compact {"x":""}\n is nine bytes.
    payload = {"x": "a" * (cap - 9)}
    exact = tmp_path / "exact.json"
    module.write_report(payload, exact)
    assert exact.stat().st_size == cap
    before = exact.read_bytes()
    with pytest.raises(FileExistsError): module.write_report({}, exact)
    assert exact.read_bytes() == before
    with pytest.raises(ValueError): module.write_report({"x": payload["x"] + "a"}, tmp_path / "oversized.json")
    with pytest.raises(ValueError): module.write_report({"x": float("nan")}, tmp_path / "nan.json")
    assert set(path.name for path in tmp_path.iterdir()) == {"exact.json"}


@pytest.mark.parametrize("kind", ["output", "parent", "input"])
def test_links_are_rejected_without_following_or_success(tmp_path, monkeypatch, kind):
    module, output, pins = recording(tmp_path, monkeypatch)
    target = tmp_path / "target.json"
    target.write_text("unchanged", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(output if kind == "input" else tmp_path if kind == "parent" else target,
                        target_is_directory=kind != "output")
    except OSError as error:
        if getattr(error, "winerror", None) == 1314: pytest.skip("Windows symlink privilege unavailable")
        raise
    with pytest.raises((ValueError, FileExistsError)):
        if kind == "input": module.analyze_probe(link, **pins)
        else: module.write_report({}, link / "report.json" if kind == "parent" else link)
    assert target.read_text(encoding="utf-8") == "unchanged"
    assert not (output / "report.json").exists()


def test_cli_requires_all_pins_and_has_no_native_or_limit_escape(tmp_path):
    module = analyzer()
    help_result = subprocess.run([sys.executable, str(SCRIPTS / "screen-population-excursion.py"), "--help"], capture_output=True, text=True)
    assert help_result.returncode == 0
    for field in ("--probe-dir", "--expected-protocol-sha256", "--expected-manifest-sha256", "--expected-events-sha256", "--output"):
        assert field in help_result.stdout
    for field in ("--native", "--limit", "--engine", "--relax"):
        assert field not in help_result.stdout
    failed = subprocess.run([sys.executable, str(SCRIPTS / "screen-population-excursion.py"),
                             "--probe-dir", str(tmp_path), "--output", str(tmp_path / "never.json")], capture_output=True, text=True)
    assert failed.returncode != 0 and not (tmp_path / "never.json").exists()
