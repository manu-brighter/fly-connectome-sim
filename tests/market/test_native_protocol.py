"""Analytical protocol fixtures; no engine, runtime, child or network."""

import copy
import hashlib
import importlib
import io
import json
import struct

import pytest


INCARNATION = "10000000-0000-0000-0000-000000000001"
SESSION = "20000000-0000-0000-0000-000000000002"
IMAGE = "30000000-0000-0000-0000-000000000003"
DISPATCH = "40000000-0000-0000-0000-000000000004"
DIGEST = "a" * 64
GROUPS = ("pam11", "ppl101", "kc", "mbon07", "mbon11", "motor_left", "motor_right")


def api():
    return importlib.import_module("market.native_protocol")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def envelope(kind="challenge", seq=0, **extra):
    return dict(schema="market-native-ipc/v1", type=kind, seq=seq,
                incarnation=INCARNATION, worker_session=SESSION,
                protocol_sha256=DIGEST, launch_nonce="b" * 64, **extra)


def raw_frame(message, binary=b""):
    encoded = canonical(message)
    body = struct.pack("<I", len(encoded)) + encoded + binary
    return struct.pack("<I", len(body)) + body


def release():
    return envelope("release", last_observation_index=None, next_observation_index=0,
                    action="black", permit=None, dispatch_id=None, exposure_ordinal=None)


def test_protocol_module_exists_without_native_import():
    assert api().GROUPS == GROUPS


def test_canonical_hash_and_detached_immutable_records():
    protocol = api()
    source = {"z": [1, {"a": "ä"}], "a": False}
    record = protocol.FrozenRecord(source)
    source["z"][1]["a"] = "changed"
    assert record.z[1].a == "ä"
    assert protocol.canonical_bytes(record) == b'{"a":false,"z":[1,{"a":"\\u00e4"}]}'
    with pytest.raises((AttributeError, TypeError)):
        record.z = ()


@pytest.mark.parametrize("bad", [True, 1.0, -1, 2 ** 63])
def test_clock_requires_exact_bounded_integer(bad):
    with pytest.raises(ValueError):
        api().decode_frame(raw_frame(envelope(p0_ns=bad, challenge_index=0)), "parent")


def test_roundtrip_and_partial_bounded_reads():
    protocol = api()
    message = envelope(p0_ns=12, challenge_index=0)

    class Pieces(io.BytesIO):
        def read(self, size=-1):
            assert 0 <= size <= 65536
            return super().read(min(size, 3))

    wire = protocol.encode_frame(message, direction="parent")
    assert wire == raw_frame(message)
    frame = protocol.read_frame(Pieces(wire), "parent")
    assert frame.message.p0_ns == 12
    assert frame.binary == b""
    assert protocol.read_frame(io.BytesIO(), "parent") is None


def test_wire_json_must_use_canonical_bytes():
    raw = json.dumps(envelope(p0_ns=12, challenge_index=0), indent=2).encode("utf-8")
    body = struct.pack("<I", len(raw)) + raw
    with pytest.raises(ValueError):
        api().decode_frame(struct.pack("<I", len(body)) + body, "parent")


@pytest.mark.parametrize("mutation", ["missing", "extra", "unknown", "wrong_direction", "binary"])
def test_closed_variant_fields(mutation):
    message = envelope(p0_ns=12, challenge_index=0)
    binary = b""
    if mutation == "missing":
        del message["challenge_index"]
    elif mutation == "extra":
        message["arbitrary"] = 0
    elif mutation == "unknown":
        message["type"] = "arbitrary"
    elif mutation == "binary":
        binary = b"x"
    with pytest.raises(ValueError):
        api().decode_frame(raw_frame(message, binary), "worker" if mutation == "wrong_direction" else "parent")


@pytest.mark.parametrize("wire", [b"\0\0\0\0", b"\xff\xff\xff\xff", b"\x08\0\0\0xx", raw_frame(envelope(p0_ns=12, challenge_index=0)) + b"x"])
def test_framing_rejects_zero_overflow_truncation_trailing(wire):
    with pytest.raises(ValueError):
        api().decode_frame(wire, "parent")


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":"\\ud800"}', b'{"a":\xff}', b'[' * 13 + b'0' + b']' * 13, b'{"a":' + b'9' * 100 + b'}'])
def test_json_budget_and_lexical_errors(raw):
    with pytest.raises(ValueError):
        api().parse_json(raw, byte_limit=4096)


def test_nonheader_node_budget_is_checked_before_json_container_load(monkeypatch):
    protocol = api()
    message = envelope("observation", unused=[0] * 5000, unused2=[0] * 4000)
    raw = canonical(message)
    original = protocol.json.loads

    def guard(text):
        # Lexical token decoding is allowed; full container construction is not.
        assert not text.startswith("{")
        return original(text)

    monkeypatch.setattr(protocol.json, "loads", guard)
    with pytest.raises(ValueError):
        protocol.decode_frame(raw_frame(message), "worker")


def test_start_and_complete_envelope_identity_matches_receipt():
    start = dict(id=IMAGE, incarnation=SESSION, dispatch_id=DISPATCH,
                 worker_session=SESSION, frame_sha256=DIGEST, started_ns=10,
                 first_observation_index=1)
    with pytest.raises(ValueError):
        api().decode_frame(raw_frame(envelope("start", receipt=start)), "worker")


def test_frame_reader_rejects_phase_specific_cap_before_body_read():
    class PrefixOnly(io.BytesIO):
        def read(self, size):
            assert self.tell() < 4
            return super().read(size)

    with pytest.raises(ValueError):
        api().read_frame(PrefixOnly(struct.pack("<I", 4097)), "worker", max_body=4096)


def test_clock_brackets_order_and_deadline_equality():
    protocol = api()
    protocol.validate_clock_brackets([
        {"index": 0, "p0_ns": 1, "child_ns": 2, "p1_ns": 3},
        {"index": 1, "p0_ns": 3, "child_ns": 4, "p1_ns": 5},
        {"index": 2, "p0_ns": 5, "child_ns": 6, "p1_ns": 7},
    ])
    for rows in ([{"index": i, "p0_ns": 0, "child_ns": 0, "p1_ns": 2_000_000_000} for i in range(3)],
                 [{"index": i, "p0_ns": 2, "child_ns": 1, "p1_ns": 3} for i in range(3)]):
        with pytest.raises(ValueError):
            protocol.validate_clock_brackets(rows)


@pytest.mark.parametrize("issued,reserved,want", [(0, 0, 40), (1, 7, 32), (32, 0, 8), (33, 0, 7), (40, 0, 0)])
def test_free_observations_reserve_active_exposure(issued, reserved, want):
    assert api().free_observations(issued, reserved) == want


def test_complete_start_tuple_and_command_matrix():
    protocol = api()
    permit = dict(id=IMAGE, incarnation=INCARNATION, dispatch_id=DISPATCH,
                  worker_session=SESSION, frame_sha256=protocol.rgb_sha256(bytes(12288)),
                  deadline_ns=1000, exposure_observations=8)
    start = dict({k: permit[k] for k in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256")},
                 started_ns=10, first_observation_index=1)
    protocol.validate_start(start, permit)
    for key in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256"):
        bad = dict(start, **{key: DIGEST if key == "frame_sha256" else SESSION})
        if bad[key] != start[key]:
            with pytest.raises(ValueError):
                protocol.validate_start(bad, permit)
    bad = dict(start, started_ns=1000)
    with pytest.raises(ValueError):
        protocol.validate_start(bad, permit)
    command = envelope("ack", last_observation_index=0, next_observation_index=1,
                       action="image", permit=permit, dispatch_id=DISPATCH, exposure_ordinal=0)
    protocol.decode_frame(raw_frame(command, bytes(12288)), "parent")
    for binary in (b"", bytes(12287), bytes(12289), bytes([1]) * 12288):
        with pytest.raises(ValueError):
            protocol.decode_frame(raw_frame(command, binary), "parent")
    for extra in (dict(action="end"), dict(next_observation_index=33), dict(permit=None), dict(exposure_ordinal=True)):
        with pytest.raises(ValueError):
            protocol.decode_frame(raw_frame(dict(command, **extra), bytes(12288)), "parent")


def header_fixture(overlap=False):
    """256 selected cells, all mandatory groups, analytic overlap/disjoint graph."""
    protocol = api()
    groups = {"kc": list(range(4064))}
    cursor = 4064
    for group, count in (("pam11", 15), ("ppl101", 2), ("mbon07", 4), ("mbon11", 2), ("motor_left", 1), ("motor_right", 1)):
        start = 0 if overlap else cursor
        groups[group] = list(range(start, start + count))
        cursor += count
    mandatory = set().union(*(set(groups[g]) for g in GROUPS if g != "kc"))
    selected = sorted(mandatory | set([i for i in range(4064) if i not in mandatory][:256 - len(mandatory)]))
    cells = [dict(model_index=i, source_id=i + 1, groups=[g for g in GROUPS if i in groups[g]], soma=None) for i in selected]
    parameters = {name: 1.0 for name in protocol.PARAMETER_KEYS if name not in ("interpretation", "source")}
    parameters.update(interpretation="declared model", source="analytical test")
    rule = {name: 1.0 for name in protocol.RULE_KEYS if name not in ("interpretation", "source")}
    rule.update(interpretation="declared model", source="analytical test")
    configuration = {name: DIGEST for name in protocol.CONFIGURATION_KEYS}
    configuration.update(adaptation_jump=1.0, adaptation_tau=1.0, rule=rule)
    fingerprint = {"version": "model-source/v1", "sources_sha256": {
        key.removeprefix("src/fly_connectome_sim/"): value
        for key, value in protocol.PRESERVED_SOURCES.items() if key.startswith("src/fly_connectome_sim/")},
    }
    fingerprint["sha256"] = digest(fingerprint)
    build = dict(source_sha256=protocol.PRESERVED_SOURCES["src/fly_connectome_sim/neural/kernel.cpp"], compiler="0.16.0",
                 flags=["-O3", "-std=c++17", "-shared", "-Wl,--export-all-symbols"], library="memory.dll", binary_sha256=DIGEST,
                 model="stonkfly-dual-compartment-v1")
    provenance = dict(model="stonkfly-dual-compartment-v1", model_fingerprint=fingerprint, build=build,
                      eta=0.001, parameters=parameters, configuration_sha256=configuration,
                      **{key: DIGEST for key in ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "plastic_edges_sha256")})
    identity = dict(version="fly-engine/v1", neural_groups=groups, model_provenance=provenance)
    identity["sha256"] = digest(identity)
    return dict(type="header", version="cell-activity-raw/v1", engine_identity=identity, cells=cells,
                selection=dict(method="mandatory-groups-kc-stride/v1", limit=256,
                               group_population_counts={g: len(groups[g]) for g in GROUPS},
                               group_selected_counts={g: sum(g in c["groups"] for c in cells) for g in GROUPS}),
                topology=dict(method="induced-directed-edge-stride/v1", limit=512, eligible_edges=0, edges=[]),
                source={key: DIGEST for key in ("graph_ids_sha256", "graph_ptr_sha256", "graph_post_sha256", "annotations_sha256")})


def observation_fixture(header, index=0, *, active=False, ordinal=0):
    counts = bytes([1]) * 12800
    populations = header["selection"]["group_population_counts"]
    row = [populations[g] for g in GROUPS]
    start = dict(id=IMAGE, incarnation=INCARNATION, dispatch_id=DISPATCH,
                 worker_session=SESSION, frame_sha256=api().BLACK_SHA256,
                 started_ns=10, first_observation_index=index) if active and ordinal == 0 else None
    return envelope("observation", observation_index=index, input_kind="image" if active else "black",
                    image_id=IMAGE if active else None, dispatch_id=DISPATCH if active else None,
                    exposure_ordinal=ordinal if active else None, frame_sha256=api().BLACK_SHA256,
                    engine_identity_sha256=header["engine_identity"]["sha256"], header_sha256=digest(header),
                    start_tick=index * 5000, end_tick=(index + 1) * 5000, wall_start_ns=20 + index * 10,
                    wall_completion_ns=25 + index * 10, learning=False, stimulation=None,
                    pathway_detail=False, qualification_detail=False,
                    group_spikes={g: populations[g] * 50 for g in GROUPS},
                    group_rates_hz={g: 100.0 for g in GROUPS}, group_bin_counts=[row[:] for _ in range(50)],
                    total_spikes=204450, compute_seconds=0.01, kernel_seconds=0.009,
                    cell_bytes_sha256=hashlib.sha256(counts).hexdigest(), start_receipt=start,
                    first_call_ns=20 + index * 10 if active and ordinal == 0 else None), counts


@pytest.mark.parametrize("overlap", [False, True])
def test_header_and_observation_analytic_populations(overlap):
    header = header_fixture(overlap)
    api().validate_header(header)
    observation, binary = observation_fixture(header)
    api().validate_observation(observation, binary, header)


@pytest.mark.parametrize("group", GROUPS)
def test_each_population_bound_and_rate_is_validated(group):
    header = header_fixture()
    observation, binary = observation_fixture(header)
    observation["group_bin_counts"][0][GROUPS.index(group)] += 1
    with pytest.raises(ValueError):
        api().validate_observation(observation, binary, header)
    observation, binary = observation_fixture(header)
    observation["group_rates_hz"][group] += 0.001
    with pytest.raises(ValueError):
        api().validate_observation(observation, binary, header)


@pytest.mark.parametrize("mutation", ["selected", "whole_upper", "disjoint_lower", "kc_lower", "mandatory", "cells", "identity", "topology", "source", "tick", "binary_digest", "byte_upper"])
def test_header_cell_group_and_total_integrity(mutation):
    header = header_fixture()
    observation, binary = observation_fixture(header)
    if mutation == "selected":
        observation["total_spikes"] = 12799
    elif mutation == "whole_upper":
        observation["total_spikes"] = 833500001
    elif mutation == "disjoint_lower":
        observation["total_spikes"] = 203200
    elif mutation in ("kc_lower", "mandatory"):
        binary = bytes([100]) * 12800
        observation["cell_bytes_sha256"] = hashlib.sha256(binary).hexdigest()
    elif mutation == "cells":
        header["cells"][1]["model_index"] = header["cells"][0]["model_index"]
    elif mutation == "identity":
        header["engine_identity"]["neural_groups"]["motor_left"] = [3]
    elif mutation == "topology":
        header["topology"].update(eligible_edges=1, edges=[[0, 256, 0]])
    elif mutation == "source":
        header["source"]["graph_ptr_sha256"] = "c" * 64
    elif mutation == "tick":
        observation["start_tick"] = 1
    elif mutation == "binary_digest":
        binary = bytes(12800)
    elif mutation == "byte_upper":
        binary = bytes([101]) + binary[1:]
        observation["cell_bytes_sha256"] = hashlib.sha256(binary).hexdigest()
    with pytest.raises(ValueError):
        api().validate_observation(observation, binary, header)


def test_overlap_lower_bound_uses_disjoint_subsets_and_inclusion():
    header = header_fixture(True)
    observation, binary = observation_fixture(header)
    observation["total_spikes"] = 203200  # KC contains all six other groups.
    api().validate_observation(observation, binary, header)
    observation["group_bin_counts"][0][GROUPS.index("kc")] = 0
    observation["group_spikes"]["kc"] -= 4064
    observation["group_rates_hz"]["kc"] = observation["group_spikes"]["kc"] / 2032
    with pytest.raises(ValueError):
        api().validate_observation(observation, binary, header)


def test_ready_digest_only_and_header_body_cap():
    header = header_fixture()
    frame = api().encode_frame(envelope("static_header", header=header), direction="worker")
    assert api().decode_frame(frame, "worker").message.header.cells[0].source_id == 1
    ready = envelope("ready", bindings_sha256=DIGEST, header_sha256=digest(header),
                     engine_identity_sha256=header["engine_identity"]["sha256"], build_sha256=digest(header["engine_identity"]["model_provenance"]["build"]),
                     graph_nodes=166700, graph_edges=25582938, observation_index=0, model_tick=0, ready_ns=10)
    api().decode_frame(raw_frame(ready), "worker")
    with pytest.raises(ValueError):
        api().decode_frame(raw_frame(dict(ready, header=header)), "worker")
    with pytest.raises(ValueError):
        api().read_frame(io.BytesIO(struct.pack("<I", 2097153)), "worker")


def startup_frames(header):
    clock = dict(implementation="QueryPerformanceCounter()", monotonic=True, adjustable=False, resolution_ns=100)
    process = dict(pid=42, creation_time_100ns=2, executable="C:\\Python312\\python.exe", executable_sha256=DIGEST)
    probe = dict(pid=43, creation_time_100ns=3, executable="C:\\tools\\zig.exe", executable_sha256=DIGEST)
    messages = [("parent", envelope("hello", bindings_sha256=DIGEST, parent_clock=clock)),
                ("worker", envelope("hello", bindings_sha256=DIGEST, worker=process, worker_clock=clock))]
    for index in range(3):
        messages.extend([("parent", envelope("challenge", challenge_index=index, p0_ns=index * 3)),
                         ("worker", envelope("clock", challenge_index=index, p0_ns=index * 3, child_ns=index * 3 + 1))])
    messages.extend([
        ("parent", envelope("initialize", bindings_sha256=DIGEST)),
        ("worker", envelope("probe_request", compiler_sha256=DIGEST, argv_sha256=DIGEST, environment_sha256=DIGEST)),
        ("parent", envelope("probe_allow", request_seq=4, allowed_ns=8)),
        ("worker", envelope("probe_started", process=probe, allowed_ns=8, started_ns=9)),
        ("worker", envelope("probe_finished", process=probe, started_ns=9, completed_ns=10,
                            exit_code=0, stdout_bytes=7, stderr_bytes=0,
                            stdout_sha256=hashlib.sha256(b"0.16.0\n").hexdigest(), stderr_sha256=hashlib.sha256(b"").hexdigest(), version="0.16.0")),
        ("worker", envelope("static_header", header=header)),
        ("worker", envelope("ready", bindings_sha256=DIGEST, header_sha256=digest(header),
                            engine_identity_sha256=header["engine_identity"]["sha256"],
                            build_sha256=digest(header["engine_identity"]["model_provenance"]["build"]),
                            graph_nodes=166700, graph_edges=25582938, observation_index=0, model_tick=0, ready_ns=11)),
    ])
    sequences = dict(parent=0, worker=0)
    for direction, message in messages:
        message["seq"] = sequences[direction]
        sequences[direction] += 1
    return messages


def full_protocol(header=None, image_start=None):
    header = header_fixture() if header is None else header
    messages = [(direction, message, b"") for direction, message in startup_frames(header)]
    seqs = {d: sum(direction == d for direction, _, _ in messages) for d in ("parent", "worker")}
    command = release()
    command["seq"] = seqs["parent"]
    seqs["parent"] += 1
    messages.append(("parent", command, b""))
    pixels = bytes([2]) * 12288
    permit = dict(id=IMAGE, incarnation=INCARNATION, dispatch_id=DISPATCH, worker_session=SESSION,
                  frame_sha256=api().rgb_sha256(pixels), deadline_ns=300000000012, exposure_observations=8)
    for index in range(40):
        observation, binary = observation_fixture(header, index)
        if image_start is not None and image_start <= index < image_start + 8:
            ordinal = index - image_start
            observation.update(input_kind="image", image_id=IMAGE, dispatch_id=DISPATCH,
                               exposure_ordinal=ordinal, frame_sha256=permit["frame_sha256"])
            if ordinal == 0:
                start = dict({k: permit[k] for k in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256")},
                             started_ns=observation["wall_start_ns"] - 1, first_observation_index=index)
                observation.update(start_receipt=start, first_call_ns=observation["wall_start_ns"])
                messages.append(("worker", envelope("start", seqs["worker"], receipt=start), b""))
                seqs["worker"] += 1
        observation["seq"] = seqs["worker"]
        seqs["worker"] += 1
        messages.append(("worker", observation, binary))
        if image_start is not None and index == image_start + 7:
            complete = dict({k: permit[k] for k in ("id", "incarnation", "dispatch_id", "worker_session", "frame_sha256")},
                            observation_indices=list(range(image_start, image_start + 8)), completed_ns=observation["wall_completion_ns"])
            messages.append(("worker", envelope("complete", seqs["worker"], receipt=complete), b""))
            seqs["worker"] += 1
        command = envelope("ack", seqs["parent"], last_observation_index=index,
                           next_observation_index=index + 1 if index < 39 else None,
                           action="black" if index < 39 else "end", permit=None,
                           dispatch_id=None, exposure_ordinal=None)
        seqs["parent"] += 1
        command_pixels = b""
        if image_start is not None and index == image_start - 1:
            command.update(action="image", permit=permit, dispatch_id=DISPATCH, exposure_ordinal=0)
            command_pixels = pixels
        elif image_start is not None and image_start <= index < image_start + 7:
            command.update(action="continue_image", dispatch_id=DISPATCH, exposure_ordinal=index - image_start + 1)
        messages.append(("parent", command, command_pixels))
    messages.append(("worker", envelope("ended", seqs["worker"], reason="model_limit", observations_completed=40,
                                        last_observation_index=39, last_tick=200000, wall_ns=420,
                                        header_sha256=digest(header), engine_identity_sha256=header["engine_identity"]["sha256"], fault=None), b""))
    return messages


def wire_receipt_ns(message):
    kind = message["type"]
    if kind == "clock":
        return message["p0_ns"] + 2
    if kind == "observation":
        return message["wall_completion_ns"] + 1
    if kind == "ack":
        return 27 + message["last_observation_index"] * 10
    if kind == "start":
        return message["receipt"]["started_ns"]
    if kind == "complete":
        return message["receipt"]["completed_ns"] + 1
    return {"hello": 0, "challenge": message.get("p0_ns", 0), "initialize": 8,
            "probe_request": 8, "probe_allow": 8, "probe_started": 9,
            "probe_finished": 10, "static_header": 10, "ready": 11,
            "release": 12, "ended": 421}.get(kind, 1000)


def test_offline_protocol_state_complete_forty_observations():
    validator = api().ProtocolValidator()
    for direction, message, binary in full_protocol():
        validator.accept(message, direction, binary, receipt_ns=wire_receipt_ns(message))
    result = validator.finish()
    assert result.observations == 40 and result.model_ticks == 200000
    assert result.image_dispatches == result.processed_images == 0


@pytest.mark.parametrize("mutation", ["gap", "duplicate", "nonce", "identity", "order", "early_eof", "late_clock", "extra", "regression"])
def test_protocol_offline_state_rejects_bad_sequences(mutation):
    messages = full_protocol()
    if mutation == "gap":
        messages[2][1]["seq"] += 1
    elif mutation == "duplicate":
        messages.insert(2, copy.deepcopy(messages[1]))
    elif mutation == "nonce":
        messages[2][1]["launch_nonce"] = "c" * 64
    elif mutation == "identity":
        messages[2][1]["worker_session"] = INCARNATION
    elif mutation == "order":
        messages[2], messages[4] = messages[4], messages[2]
    elif mutation == "early_eof":
        messages = messages[:-1]
    elif mutation == "late_clock":
        messages[3][1]["child_ns"] = 1001
    elif mutation == "extra":
        messages.append(copy.deepcopy(messages[-1]))
    elif mutation == "regression":
        # Observation1 cannot start before observation0 completed.
        messages[18][1]["wall_start_ns"] = 0
    with pytest.raises(ValueError):
        validator = api().ProtocolValidator()
        for direction, message, binary in messages:
            validator.accept(message, direction, binary, receipt_ns=wire_receipt_ns(message))
        validator.finish()


@pytest.mark.parametrize("mutation", ["missing_start", "duplicate_start", "early_complete", "partial_exposure", "wrong_tuple", "deadline_equal"])
def test_image_wire_missing_duplicate_order_partial_and_deadline(mutation):
    messages = full_protocol(image_start=32)
    start_index = next(i for i, (_, message, _) in enumerate(messages) if message["type"] == "start")
    complete_index = next(i for i, (_, message, _) in enumerate(messages) if message["type"] == "complete")
    if mutation == "missing_start":
        messages.pop(start_index)
    elif mutation == "duplicate_start":
        messages.insert(start_index, copy.deepcopy(messages[start_index]))
    elif mutation == "early_complete":
        complete = messages.pop(complete_index)
        messages.insert(complete_index - 1, complete)
    elif mutation == "partial_exposure":
        messages.pop(complete_index - 1)
    elif mutation == "wrong_tuple":
        messages[start_index][1]["receipt"]["worker_session"] = INCARNATION
    elif mutation == "deadline_equal":
        image_command = next(message for _, message, _ in messages if message["type"] == "ack" and message["action"] == "image")
        image_command["permit"]["deadline_ns"] = 340
    sequences = dict(parent=0, worker=0)
    for direction, message, _ in messages:
        message["seq"] = sequences[direction]
        sequences[direction] += 1
    with pytest.raises(ValueError):
        validator = api().ProtocolValidator()
        for direction, message, binary in messages:
            validator.accept(message, direction, binary, receipt_ns=wire_receipt_ns(message))
        validator.finish()


def test_explicit_native_fixture_path_mapping_preserves_closed_windows_validation():
    from native_fixtures import logical_local_path
    from market.native_protocol import _local_path
    roots = ('/tmp/native-fixture', '/workspace/source')
    result = logical_local_path('/tmp/native-fixture/project\\src/module.py', roots, _local_path)
    assert result == _local_path('C:\\tmp\\native-fixture\\project\\src\\module.py')
    assert logical_local_path('C:\\tools\\python.exe', roots, _local_path) == _local_path('C:\\tools\\python.exe')
    for rejected in (
        '/outside/fixture/file.py', 'relative/file.py',
        '/tmp/native-fixture/../escape', '/tmp/native-fixture-neighbor/file.py',
    ):
        with pytest.raises(ValueError):
            logical_local_path(rejected, roots, _local_path)


def test_posix_fake_bindings_use_real_paths_and_original_windows_checks(monkeypatch):
    from native_fixtures import logical_local_path
    from test_native_evidence import prepared_fixtures
    protocol = api()
    declaration, bindings = prepared_fixtures()
    project = '/tmp/native-fixture/project'

    def relocate(value):
        if type(value) is str:
            return value.replace('C:\\project', project)
        if type(value) is dict:
            return {key: relocate(item) for key, item in value.items()}
        if type(value) is list:
            return [relocate(item) for item in value]
        return value

    bindings = relocate(bindings)
    for binding in bindings['files'].values():
        if binding['path'].startswith(project + '\\'):
            binding['path'] = binding['path'].replace('\\', '/')
    bindings.update(work_root='/tmp/native-fixture/native', decoder_work_root='/tmp/native-fixture/decoder')
    bindings['environment'].update(TMP='/tmp/native-fixture/native/scratch', TEMP='/tmp/native-fixture/native/scratch')
    bindings['compiler_probe']['environment_sha256'] = protocol.canonical_sha256(bindings['environment'])
    original = protocol._local_path
    monkeypatch.setattr(protocol, '_local_path', lambda value: logical_local_path(value, ('/tmp/native-fixture',), original))
    accepted = protocol.validate_bindings(bindings, declaration)
    assert accepted.project_root == project
    assert accepted.files['src/fly_connectome_sim/neural/arrays.lock.json'].path == project + '/src/fly_connectome_sim/neural/arrays.lock.json'
    bindings['files']['src/fly_connectome_sim/neural/arrays.lock.json']['path'] = '/outside/arrays.lock.json'
    with pytest.raises(ValueError):
        protocol.validate_bindings(bindings, declaration)
