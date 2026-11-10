"""Offline evidence is integrity bookkeeping, never native attestation."""

import hashlib
import importlib
import io
import copy
import json
import struct
import sys
from pathlib import Path

import pytest

from test_native_protocol import (
    INCARNATION, SESSION, IMAGE, DISPATCH, DIGEST, canonical, digest,
    header_fixture, full_protocol,
    wire_receipt_ns,
)


def receipt_fixture():
    return dict(id=IMAGE, incarnation=INCARNATION, source_sha256=DIGEST, encoded_bytes=123,
                accepted_ns=1, deadline_ns=300000000001, decode_deadline_ns=10000000001,
                moderation_deadline_ns=60000000001, status="accepted", detail="decoding",
                frame_sha256=None, preprocessing_version=None, worker_session=None,
                dispatch_id=None, dispatched_ns=None, started_ns=None,
                first_observation_index=None, completed_ns=None, terminal_ns=None,
                revision=1, time_uncertain=False)


def binding_payload():
    return dict(protocol_sha256=DIGEST, bindings_sha256=DIGEST)


def event_fixture():
    row = dict(schema="market-native-event/v1", sequence=0, previous_sha256="0" * 64,
               recorded_ns=1, kind="binding", payload=binding_payload(),
               binary_bytes=0, binary_sha256=hashlib.sha256(b"").hexdigest())
    row["sha256"] = hashlib.sha256(b"market-native-event/v1\n" + canonical(row)).hexdigest()
    return row


def monitor_fixture():
    row = dict(schema="market-native-monitor/v1", sequence=0, previous_sha256="0" * 64,
               sample_ns=1, worker_pid=42, worker_creation_time_100ns=2,
               worker_rss_bytes=100, worker_peak_rss_bytes=200,
               probe_pid=None, probe_creation_time_100ns=None, probe_rss_bytes=0,
               probe_peak_rss_bytes=0, job_process_count=1, job_commit_bytes=300,
               job_peak_commit_bytes=400, combined_output_bytes=500,
               evidence_bytes=500, gap_ns=0, fault=None)
    row["sha256"] = hashlib.sha256(b"market-native-monitor/v1\n" + canonical(row)).hexdigest()
    return row


def cleanup_fixture():
    return dict(schema="market-native-cleanup/v1", incarnation=INCARNATION, worker_session=SESSION,
                requested_ns=421, finished_ns=300000000, worker_creation="verified",
                worker=dict(pid=42, creation_time_100ns=2, executable="C:\\Python312\\python.exe", executable_sha256=DIGEST),
                probe=dict(pid=43, creation_time_100ns=3, executable="C:\\tools\\zig.exe", executable_sha256=DIGEST),
                worker_exit_code=0, probe_exit_code=0, worker_exit_confirmed=True,
                probe_exit_confirmed=True, job_empty_confirmed=True, ipc_handles_closed=True,
                process_handles_closed=True, job_handle_closed=True, root_lock_closed=True,
                evidence_files_closed=True, first_fault=None, cleanup_fault=None, outcome="confirmed")


def api():
    return importlib.import_module("market.native_protocol")


@pytest.fixture(autouse=True)
def logical_windows_binding_paths(monkeypatch, tmp_path):
    """CI path resolution only: real files/stat/rawhash, unchanged validation."""
    if sys.platform != "win32":
        prefix = "C:\\native-protocol-fixture\\project\\"

        def resolve(declared_path):
            assert declared_path.startswith(prefix)
            return tmp_path / "project" / Path(declared_path[len(prefix):].replace("\\", "/"))

        monkeypatch.setattr(api(), "_bound_path", resolve)


def test_missing_seal_never_claims_complete(tmp_path):
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


def test_empty_evidence_is_incomplete():
    with pytest.raises(ValueError):
        api().read_events(io.BytesIO())


def test_event_hash_bytes_and_full_eof():
    row = event_fixture()
    encoded = api().encode_event(row)
    expected = canonical(row)
    assert encoded == struct.pack("<II", len(expected) + 4, len(expected)) + expected
    records = api().read_events(io.BytesIO(encoded))
    assert len(records) == 1 and records[0].message.sha256 == row["sha256"]
    for raw in (encoded[:-1], encoded + b"x", encoded + encoded, encoded[:12] + b"!" + encoded[13:]):
        with pytest.raises(ValueError):
            api().read_events(io.BytesIO(raw))


def test_nonce_is_removed_from_journal_and_unknown_credentials_refused():
    direction, message, binary = full_protocol()[0]
    payload = api().wire_payload(message, direction, binary)
    assert "launch_nonce" not in payload.message
    row = api().make_event(0, "0" * 64, 1, "wire", payload, binary)
    encoded = api().encode_event(row)
    assert b"launch_nonce" not in encoded and b"bbbbbbbbbbbbbbbb" not in encoded
    bad = payload.to_dict()
    bad["message"]["status_capability"] = "is." + "x" * 43
    with pytest.raises(ValueError):
        api().make_event(0, "0" * 64, 1, "wire", bad)


@pytest.mark.parametrize("field,bad", [("revision", True), ("encoded_bytes", 0), ("accepted_ns", 1.5), ("deadline_ns", -1), ("worker_session", "x"), ("revision", 7), ("status", "processed"), ("time_uncertain", 1)])
def test_supplied_receipt_schema_and_status_semantics(field, bad):
    receipt = receipt_fixture()
    receipt[field] = bad
    with pytest.raises(ValueError):
        api().validate_receipt(receipt)


def test_receipt_revision_watermark_detects_gaps_and_conflicts():
    validator = api().ReceiptEvidence()
    receipt = receipt_fixture()
    assert validator.accept(receipt) is True
    assert validator.accept(receipt) is False
    decoded = dict(receipt, revision=2, detail="awaiting_approval", frame_sha256=DIGEST,
                   preprocessing_version="market-rgb64/v1")
    assert validator.accept(decoded) is True
    for bad in (dict(decoded, encoded_bytes=124), dict(decoded, revision=4), dict(receipt, revision=3)):
        with pytest.raises(ValueError, match="journal_gap"):
            validator.accept(bad)


def test_supplied_receipts_cannot_invent_two_pending_images():
    validator = api().ReceiptEvidence()
    receipt = receipt_fixture()
    validator.accept(receipt)
    with pytest.raises(ValueError, match="journal_gap"):
        validator.accept(dict(receipt, id=DISPATCH))


def test_monitor_chain_hash_and_independent_record_limit():
    row = monitor_fixture()
    encoded = api().encode_monitor(row)
    records = api().read_monitors(io.BytesIO(encoded))
    assert records[0].worker_peak_rss_bytes == 200
    with pytest.raises(ValueError):
        api().read_monitors(io.BytesIO(encoded + encoded))
    row["sequence"] = 4096  # monitor index is not the event index.
    row["sha256"] = hashlib.sha256(b"market-native-monitor/v1\n" + canonical({k: v for k, v in row.items() if k != "sha256"})).hexdigest()
    api().encode_monitor(row)
    row["sequence"] = 12000
    with pytest.raises(ValueError):
        api().encode_monitor(row)


def test_monitor_cadence_rejects_burst_catchup_but_allows_terminal_sample():
    rows = []
    previous = "0" * 64
    for index, now in enumerate((0, 1, 100000000)):
        row = monitor_fixture()
        row.pop("sha256")
        row.update(sequence=index, previous_sha256=previous, sample_ns=now,
                   gap_ns=0 if index == 0 else now - (0 if index == 1 else 1))
        row = api().make_monitor(row)
        previous = row.sha256
        rows.append(api().encode_monitor(row))
    assert len(api().read_monitors(io.BytesIO(b"".join(rows[:2])))) == 2
    with pytest.raises(ValueError):
        api().read_monitors(io.BytesIO(b"".join(rows)))


@pytest.mark.parametrize("field,bad", [("sample_ns", True), ("worker_pid", 0), ("probe_pid", 43), ("probe_rss_bytes", 1), ("evidence_bytes", 501), ("gap_ns", 2000000000)])
def test_monitor_malformed_and_resource_failure_cannot_look_clean(field, bad):
    row = monitor_fixture()
    row[field] = bad
    row["sha256"] = hashlib.sha256(b"market-native-monitor/v1\n" + canonical({k: v for k, v in row.items() if k != "sha256"})).hexdigest()
    with pytest.raises(ValueError):
        api().encode_monitor(row)


def test_cleanup_variant_matrix_no_fictional_identity_or_success():
    api().validate_cleanup(cleanup_fixture())
    honest_none = dict(cleanup_fixture(), worker_creation="not_created", worker=None, worker_exit_code=None,
                       probe=None, probe_exit_code=None)
    api().validate_cleanup(honest_none)
    for bad in (dict(honest_none, worker=cleanup_fixture()["worker"]),
                dict(cleanup_fixture(), worker_creation="created_unverified", worker=None),
                dict(cleanup_fixture(), job_empty_confirmed=False),
                dict(cleanup_fixture(), finished_ns=419),
                dict(cleanup_fixture(), worker_exit_code=None)):
        with pytest.raises(ValueError):
            api().validate_cleanup(bad)


def prepared_fixtures(root=None):
    protocol = dict(schema="market-native-protocol/v1", proof="bounded-image20s/v1",
                    constants=dict(api().CONSTANTS), preserved_sources=dict(api().PRESERVED_SOURCES),
                    application_sources={key: DIGEST for key in api().APPLICATION_SOURCES},
                    lock_sources={key: DIGEST for key in api().LOCK_SOURCES},
                    package_fingerprint=api().PACKAGE_FINGERPRINT)
    project, runtime = "C:\\project", "C:\\project\\data\\malecns-v1.0\\runtime"
    if root is not None:
        project = str(root / "project") if sys.platform == "win32" else "C:\\native-protocol-fixture\\project"
        runtime = project + "\\data\\malecns-v1.0\\runtime"
    files = {}
    for group in ("preserved_sources", "application_sources", "lock_sources"):
        for key, checksum in protocol[group].items():
            files[key] = dict(path=project + "\\" + key.replace("/", "\\"), bytes=1,
                              sha256=checksum, device=1, file_id=len(files) + 1, mtime_ns=1)
    paths = dict(python_launcher=project + "\\.venv\\Scripts\\python.exe",
                 python_config=project + "\\.venv\\pyvenv.cfg",
                 worker_exe="C:\\Python312\\python.exe", compiler_exe="C:\\tools\\zig.exe",
                 native_library=runtime + "\\cache\\physiology-v6\\memory.dll",
                 native_metadata=runtime + "\\cache\\physiology-v6\\memory.dll.json",
                 graph=runtime + "\\graph.npz", normalized_neurons=runtime + "\\normalized\\neurons.feather",
                 **{name: runtime + "\\" + name + ".feather" for name in ("annotations", "neurotransmitters", "edges")})
    site = project + "\\.venv\\Lib\\site-packages"
    for name, version in (("numpy", "2.4.6"), ("pandas", "3.0.5"), ("pyarrow", "25.0.1")):
        paths[name + "_init"] = site + "\\" + name + "\\__init__.py"
        paths[name + "_metadata"] = site + "\\" + name + "-" + version + ".dist-info\\METADATA"
    for key, path in paths.items():
        files[key] = dict(path=path, bytes=1, sha256=DIGEST, device=1, file_id=len(files) + 1, mtime_ns=1)
    if root is not None:
        arrays_lock = {key: DIGEST for key in "ptr post weight ids retina uv confidence hexes lamina sugar superclass".split()}
        sources_lock = {key + ".feather": dict(url="https://example.invalid/" + key, bytes=1, sha256=DIGEST)
                        for key in ("annotations", "neurotransmitters", "edges")}
        for name, value in (("arrays.lock", arrays_lock), ("sources.lock", sources_lock)):
            key = "src/fly_connectome_sim/neural/" + name + ".json"
            path = root / "project" / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical(value))
            file_stat = path.stat()
            checksum = digest(value)
            files[key].update(bytes=file_stat.st_size, sha256=checksum, device=file_stat.st_dev,
                              file_id=file_stat.st_ino, mtime_ns=file_stat.st_mtime_ns)
            protocol["lock_sources"][key] = checksum
    environment = dict(SystemRoot="C:\\Windows", WINDIR="C:\\Windows", PATH="C:\\Windows\\System32;C:\\Python312;C:\\tools",
                       TMP="C:\\work\\scratch", TEMP="C:\\work\\scratch", PYTHONPATH=project + ";" + project + "\\src;" + site,
                       PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
                       FLY_CONNECTOME_SIM_DATA=runtime, FLY_CONNECTOME_SIM_CXX=paths["compiler_exe"])
    metadata = header_fixture()["engine_identity"]["model_provenance"]["build"].copy()
    del metadata["model"]
    bindings = dict(schema="market-native-bindings/v1", protocol_sha256=digest(protocol),
                    incarnation=INCARNATION, worker_session=SESSION, project_root=project,
                    work_root="C:\\work", decoder_work_root="C:\\decoder", runtime_root=runtime,
                    files=files, environment=environment, python_version="3.12.14",
                    compiler_probe=dict(executable_sha256=DIGEST, argv=[paths["compiler_exe"], "version"],
                                        environment_sha256=digest(environment), expected_version="0.16.0",
                                        timeout_ns=5000000000, stdout_limit=4096, stderr_limit=4096),
                    native_metadata=metadata, dependencies=dict(site_packages=site, numpy="2.4.6", pandas="3.0.5", pyarrow="25.0.1"),
                    package_fingerprint=api().PACKAGE_FINGERPRINT, prepared_ns=0)
    return protocol, bindings


def write_complete_fixture(root, *, image=False, mutation=None):
    protocol, bindings = prepared_fixtures(root)
    if mutation == "worker_binding":
        bindings["files"]["worker_exe"]["sha256"] = "f" * 64
    elif mutation == "probe_binding":
        bindings["files"]["compiler_exe"]["sha256"] = "f" * 64
        bindings["compiler_probe"]["executable_sha256"] = "f" * 64
    protocol_digest, bindings_digest = digest(protocol), digest(bindings)
    header = header_fixture()
    header_digest = digest(header)
    events = []
    previous = "0" * 64

    def append(kind, payload, recorded_ns, binary=b""):
        nonlocal previous
        row = api().make_event(len(events), previous, recorded_ns, kind, payload, binary)
        previous = row.sha256
        events.append(api().encode_event(row, binary))

    append("binding", dict(protocol_sha256=protocol_digest, bindings_sha256=bindings_digest), 0)
    receipt = dict(receipt_fixture(), accepted_ns=12, deadline_ns=300000000012,
                   decode_deadline_ns=10000000012, moderation_deadline_ns=60000000012)

    def receipt_event(operation, now):
        append("receipt", dict(ticket=receipt["revision"], receipt=receipt.copy(),
                               cause=dict(operation=operation, target_id=IMAGE, notice_seq=None, read_pass=0)), now)

    for direction, source, binary in full_protocol(header, image_start=32 if image else None):
        message = copy.deepcopy(source)
        message["protocol_sha256"] = protocol_digest
        if "bindings_sha256" in message:
            message["bindings_sha256"] = bindings_digest
        if message["type"] == "probe_request":
            message["compiler_sha256"] = bindings["compiler_probe"]["executable_sha256"]
            message["argv_sha256"] = digest(bindings["compiler_probe"]["argv"])
            message["environment_sha256"] = digest(bindings["environment"])
        if image and message["type"] == "ack" and message["action"] == "image":
            receipt.update(revision=4, detail="dispatching", worker_session=SESSION,
                           dispatch_id=DISPATCH, dispatched_ns=336)
            if mutation != "missing_dispatch":
                receipt_event("dispatch", 336)
        if message["type"] == "static_header":
            append("header", dict(header_sha256=header_digest, engine_identity_sha256=header["engine_identity"]["sha256"], worker_seq=message["seq"]), 10)
        else:
            append("wire", api().wire_payload(message, direction, binary), wire_receipt_ns(message), binary)
        if message["type"] == "clock":
            append("clock_bracket", dict(index=message["challenge_index"], p0_ns=message["p0_ns"], child_ns=message["child_ns"], p1_ns=message["p0_ns"] + 2), message["p0_ns"] + 2)
        if image and message["type"] == "release":
            receipt_event("admit", 12)
            receipt.update(revision=2, detail="awaiting_approval", frame_sha256=api().rgb_sha256(bytes([2]) * 12288), preprocessing_version="market-rgb64/v1")
            receipt_event("decoded", 13)
            receipt.update(revision=3, status="queued", detail="ready")
            receipt_event("moderate", 14)
        if image and message["type"] == "start":
            receipt.update(revision=5, status="processing", detail="processing", started_ns=339, first_observation_index=32)
            if mutation != "missing_started":
                receipt_event("started", 339)
        if image and message["type"] == "complete":
            receipt.update(revision=6, status="processed", detail="completed", completed_ns=415, terminal_ns=416)
            if mutation != "missing_processed":
                receipt_event("complete", 416)
            if mutation == "duplicate_processed":
                receipt_event("complete", 416)
    # Three samples: monitor has an independent sequence/hash chain.
    monitor_rows = []
    monitor_previous = "0" * 64
    for index, now in enumerate((0, 100000000, 200000000)):
        row = monitor_fixture()
        row.update(sequence=index, previous_sha256=monitor_previous, sample_ns=now,
                   gap_ns=0 if not index else 100000000,
                   combined_output_bytes=4000000, evidence_bytes=4000000)
        if index == 2 and mutation != "monitor_live":
            row.update(worker_rss_bytes=0, job_process_count=0, job_commit_bytes=0)
        row.pop("sha256")
        row = api().make_monitor(row)
        monitor_previous = row.sha256
        monitor_rows.append(api().encode_monitor(row))
    cleanup = cleanup_fixture()
    event_bytes, monitor_bytes = b"".join(events), b"".join(monitor_rows)
    subset = {key: value for key, value in bindings["files"].items() if key not in api().RUNTIME_KEYS}
    subset.update(protocol_sha256=protocol_digest, bindings_sha256=bindings_digest)
    final = dict(schema="market-native-final/v1", status="complete", verification="integrity-only",
                 incarnation=INCARNATION, worker_session=SESSION, protocol_sha256=protocol_digest,
                 bindings_sha256=bindings_digest, header_sha256=header_digest,
                 event_records=len(events), events_sha256=hashlib.sha256(event_bytes).hexdigest(), event_chain_sha256=previous,
                 monitor_records=3, monitor_sha256=hashlib.sha256(monitor_bytes).hexdigest(), monitor_chain_sha256=monitor_previous,
                 cleanup_sha256=digest(cleanup), observations=40, model_ticks=200000, image_dispatches=int(image), processed_images=int(image),
                 max_monitor_gap_ns=100000000, peak_worker_rss_bytes=200, peak_probe_rss_bytes=0,
                 peak_job_commit_bytes=400, peak_output_bytes=4000000,
                 source_unchanged=True, source_check=dict(scope="prepared-source-lock-tool-cache/v1",
                     started_ns=200000001, finished_ns=299999999, file_count=len(subset), bindings_subset_sha256=digest(subset), all_match=True),
                 first_fault=None, cleanup_fault=None)
    for name, content in (("protocol.json", canonical(protocol)), ("bindings.json", canonical(bindings)),
                          ("header.json", canonical(header)), ("cleanup.json", canonical(cleanup)),
                          ("final.json", canonical(final)), ("events.bin", event_bytes), ("monitor.bin", monitor_bytes)):
        (root / name).write_bytes(content)
    return final


def test_complete_full_eof_integrity_negative_zero_images(tmp_path):
    write_complete_fixture(tmp_path)
    result = api().inspect_evidence(tmp_path)
    assert result.status == "complete" and result.verification == "integrity-only"
    assert result.observations == 40 and result.processed_images == 0


def test_complete_software_only_image_path_at_observation39(tmp_path):
    write_complete_fixture(tmp_path, image=True)
    result = api().inspect_evidence(tmp_path)
    assert result.image_dispatches == result.processed_images == 1


@pytest.mark.parametrize("mutation", ["missing_dispatch", "missing_started", "missing_processed", "duplicate_processed"])
def test_image_causal_receipt_gaps_never_seal(tmp_path, mutation):
    write_complete_fixture(tmp_path, image=True, mutation=mutation)
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


@pytest.mark.parametrize("name", ["arrays.lock.json", "sources.lock.json"])
def test_changed_bound_lock_is_not_historical_source_match(tmp_path, name):
    write_complete_fixture(tmp_path)
    path = tmp_path / "project" / "src" / "fly_connectome_sim" / "neural" / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


def test_complete_seal_requires_final_monitor_confirmed_empty_job(tmp_path):
    write_complete_fixture(tmp_path, mutation="monitor_live")
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


@pytest.mark.parametrize("mutation", ["worker_binding", "probe_binding"])
def test_worker_probe_identity_must_match_prepared_tool_binding(tmp_path, mutation):
    write_complete_fixture(tmp_path, mutation=mutation)
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


def test_rehashed_image_permit_cannot_extend_original_d1_deadline(tmp_path):
    final = write_complete_fixture(tmp_path, image=True)
    frames = api().read_events(io.BytesIO((tmp_path / "events.bin").read_bytes()))
    previous = "0" * 64
    encoded = []
    for frame in frames:
        row = frame.message.to_dict()
        if row["kind"] == "wire":
            message = row["payload"]["message"]
            if message["type"] == "ack" and message["action"] == "image":
                message["permit"]["deadline_ns"] += 100000000000
        event = api().make_event(row["sequence"], previous, row["recorded_ns"], row["kind"], row["payload"], frame.binary)
        encoded.append(api().encode_event(event, frame.binary))
        previous = event.sha256
    raw = b"".join(encoded)
    (tmp_path / "events.bin").write_bytes(raw)
    final.update(events_sha256=hashlib.sha256(raw).hexdigest(), event_chain_sha256=previous)
    (tmp_path / "final.json").write_bytes(canonical(final))
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


@pytest.mark.parametrize("terminal_only", [True, False])
def test_rehashed_monitor_requires_early_startup_coverage(tmp_path, terminal_only):
    final = write_complete_fixture(tmp_path, image=True)
    rows = api().read_monitors(io.BytesIO((tmp_path / "monitor.bin").read_bytes()))
    retained = rows[-1:] if terminal_only else rows[1:]
    previous = "0" * 64
    encoded = []
    for index, original in enumerate(retained):
        fields = original.to_dict()
        fields.pop("sha256")
        fields.update(sequence=index, previous_sha256=previous, gap_ns=0 if index == 0 else original.gap_ns)
        row = api().make_monitor(fields)
        previous = row.sha256
        encoded.append(api().encode_monitor(row))
    raw = b"".join(encoded)
    (tmp_path / "monitor.bin").write_bytes(raw)
    final.update(monitor_records=len(retained), monitor_sha256=hashlib.sha256(raw).hexdigest(),
                 monitor_chain_sha256=previous, max_monitor_gap_ns=0 if terminal_only else 100000000)
    (tmp_path / "final.json").write_bytes(canonical(final))
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


@pytest.mark.parametrize("name", ["protocol.json", "bindings.json", "header.json", "cleanup.json", "events.bin", "monitor.bin"])
def test_corrupt_truncated_or_trailing_evidence_refused(tmp_path, name):
    write_complete_fixture(tmp_path)
    path = tmp_path / name
    raw = path.read_bytes()
    path.write_bytes(raw[:-1])
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)
    path.write_bytes(raw + b"x")
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


@pytest.mark.parametrize("field", ["incarnation", "worker_session", "protocol_sha256", "bindings_sha256", "header_sha256", "event_records", "events_sha256", "event_chain_sha256", "monitor_records", "monitor_sha256", "monitor_chain_sha256", "cleanup_sha256", "observations", "model_ticks", "image_dispatches", "processed_images", "max_monitor_gap_ns", "peak_worker_rss_bytes", "peak_probe_rss_bytes", "peak_job_commit_bytes", "peak_output_bytes", "source_unchanged", "source_check", "first_fault", "cleanup_fault", "verification", "status"])
def test_every_final_seal_field_is_checked(tmp_path, field):
    final = write_complete_fixture(tmp_path)
    item = final[field]
    if field == "source_check":
        final[field] = dict(item, bindings_subset_sha256="f" * 64)
    elif type(item) is int:
        final[field] += 1
    elif type(item) is bool:
        final[field] = False
    elif item is None:
        final[field] = "storage"
    else:
        final[field] = "f" * len(item)
    (tmp_path / "final.json").write_bytes(canonical(final))
    with pytest.raises(ValueError):
        api().inspect_evidence(tmp_path)


@pytest.mark.parametrize("mutation", ["missing_source", "extra_source", "source_hash", "bool_constant", "binary_cap", "runtime_cap", "environment", "dependency", "path_escape", "probe"])
def test_prepared_exact_maps_and_bounds(mutation):
    protocol, bindings = prepared_fixtures()
    if mutation == "missing_source":
        protocol["preserved_sources"].pop(next(iter(protocol["preserved_sources"])))
    elif mutation == "extra_source":
        protocol["application_sources"]["arbitrary.py"] = DIGEST
    elif mutation == "source_hash":
        bindings["files"]["market/native_protocol.py"]["sha256"] = "f" * 64
    elif mutation == "bool_constant":
        protocol["constants"]["model_observations"] = True
    elif mutation == "binary_cap":
        bindings["files"]["worker_exe"]["bytes"] = 536870913
    elif mutation == "runtime_cap":
        bindings["files"]["graph"]["bytes"] = 4294967297
    elif mutation == "environment":
        bindings["environment"]["SECRET"] = "x"
    elif mutation == "dependency":
        bindings["dependencies"]["numpy"] = "2.4.5"
    elif mutation == "path_escape":
        bindings["files"]["market/native_protocol.py"]["path"] = "C:\\elsewhere\\native_protocol.py"
    elif mutation == "probe":
        bindings["compiler_probe"]["argv"][1] = "--version"
    with pytest.raises(ValueError):
        api().validate_protocol(protocol)
        api().validate_bindings(bindings, protocol)
