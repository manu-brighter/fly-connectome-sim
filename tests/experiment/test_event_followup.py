"""Declared session/HTTPS seams; no native execution or live provider calls."""

from copy import deepcopy
from hashlib import sha256
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from fly_connectome_sim.experiment.recorder import _canonical
from test_event_cards import example


KEY = "sk-followup-fixture-do-not-persist"
PARAMETERS = {"model": "explicit-model", "max_output_tokens": 1024}
SUPPLEMENT = {"overview": "Ein gemütlicher Abend mit Rücksicht auf alle Gäste.",
              "preparation": ["Zugänglichkeit prüfen.", "Budget als Schätzung behandeln."],
              "open_questions": ["Welche Allergien sind zu berücksichtigen?"]}


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    monkeypatch.setattr(http.client, "HTTPSConnection", lambda *a, **k: pytest.fail("Real HTTPS forbidden"))


@pytest.fixture
def source(tmp_path, monkeypatch):
    from fly_connectome_sim.experiment import event_followup as followup
    path = tmp_path / "session"
    path.mkdir()
    proposal = example()
    plan = {"version": "event-plan/v1", "status": "selected", "brief": proposal["brief"],
            "selected_option_id": proposal["options"][0]["id"], "selected_option": proposal["options"][0],
            "decision_ref": {"event_sequence": 214, "scientific_sha256": "a" * 64,
                             "input_sha256": "b" * 64, "policy_version": "event-card-choice/v1"},
            "source": {"verification_mode": "integrity-only", "private_source_marker": "DO-NOT-SEND-SOURCE"}}
    recording = {"private_neural_counts": [777], "unselected": proposal["options"][1]}
    def write(plan):
        raw = {"plan.json": _canonical(plan) + b"\n", "recording.json": _canonical(recording) + b"\n"}
        receipt = {"version": "session-bundle/v1", "status": "complete", "source": plan["source"],
                   "files": {name: {"size_bytes": len(value), "sha256": sha256(value).hexdigest()} for name, value in raw.items()}}
        for name, value in raw.items():
            (path / name).write_bytes(value)
        (path / "receipt.json").write_bytes(_canonical(receipt) + b"\n")
    write(plan)
    calls = []
    def inspect(target, *, receipt):
        # Explicit fixture inspector: only source-binding/control flow is tested
        # here. Ordinary workflow regressions separately test raw derivation.
        assert Path(target) == path and receipt is True
        calls.append(1)
        return {"status": "complete"}, (path / "receipt.json").read_bytes()
    monkeypatch.setattr(followup, "_inspect_session", inspect)
    return path, plan, write, calls


@pytest.fixture
def network(monkeypatch):
    from test_event_proposals import network as proposal_network, response_value
    state = proposal_network.__wrapped__(monkeypatch)
    # The shared HTTP fixture expects its own key at the Authorization seam.
    from test_event_proposals import KEY as transport_key
    monkeypatch.setenv("OPENAI_API_KEY", transport_key)
    value = response_value()
    value["output"][1]["content"][0]["text"] = json.dumps(SUPPLEMENT, ensure_ascii=False)
    state["body"] = json.dumps(value, ensure_ascii=False).encode()
    state["key"] = transport_key
    return state


def prepare(output, source, **kwargs):
    from fly_connectome_sim.experiment.event_followup import prepare_event_followup
    return prepare_event_followup(output, session_dir=source, **(PARAMETERS | kwargs))


def files(path):
    return {p.name: p.read_bytes() for p in path.iterdir() if p.is_file()}


def test_offline_request_only_sends_selected_data_and_never_reads_key(source, tmp_path, monkeypatch):
    import os
    path, plan, _, _ = source
    before = files(path)
    monkeypatch.setattr(type(os.environ), "get", lambda *a: pytest.fail("Offline read credentials"))
    output = tmp_path / "offline"
    receipt = prepare(output, path)
    assert receipt["status"] == "dry-run"
    assert set(files(output)) == {"request.json", "receipt.json"}
    request = json.loads((output / "request.json").read_bytes())
    assert request["store"] is request["stream"] is False and "tools" not in request
    assert json.loads(request["input"][1]["content"]) == {"brief": plan["brief"], "selected_option": plan["selected_option"]}
    assert "DO-NOT-SEND-SOURCE" not in json.dumps(request) and "private_neural_counts" not in json.dumps(request)
    assert request["text"]["format"]["strict"] is True
    properties = request["text"]["format"]["schema"]["properties"]
    assert set(properties) == set(SUPPLEMENT)
    assert files(path) == before


def test_defer_never_builds_request_or_reads_key_even_with_paid_flag(source, tmp_path, monkeypatch):
    import os
    from fly_connectome_sim.experiment import event_followup as followup
    path, plan, write, _ = source
    plan.update(status="deferred", selected_option_id=None, selected_option=None)
    write(plan)
    monkeypatch.setattr(type(os.environ), "get", lambda *a: pytest.fail("Defer read credentials"))
    monkeypatch.setattr(followup, "_request", lambda *a: pytest.fail("Defer built request"))
    output = tmp_path / "defer"
    assert prepare(output, path, allow_paid_request=True)["status"] == "no-selection"
    assert set(files(output)) == {"receipt.json"}


def test_live_preserves_full_plan_utf8_and_receipt_last(source, tmp_path, network, monkeypatch):
    from fly_connectome_sim.experiment import event_followup as followup
    path, plan, _, _ = source
    before = files(path)
    output = tmp_path / "live"
    opened = []
    original = Path.open
    def opening(member, mode="r", *args, **kwargs):
        if member.parent == output and mode == "xb":
            opened.append(member.name)
            assert not (output / "receipt.json").exists()
        return original(member, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opening)
    receipt = prepare(output, path, allow_paid_request=True)
    assert receipt["status"] == "validated"
    assert opened == ["request.json", "followup.json", "event-plan.md", "receipt.json"]
    result = json.loads((output / "followup.json").read_bytes())
    assert result["plan"] == plan and result["supplement"] == SUPPLEMENT
    assert result["source"] == receipt["source"]
    for name in ("plan", "recording", "receipt"):
        assert result["source"][name + "_sha256"] == sha256(before[name + ".json"]).hexdigest()
    markdown = (output / "event-plan.md").read_text(encoding="utf-8")
    assert "Schätzung" in markdown and "Unverbindlich" in markdown
    for entry in plan["selected_option"]["programme"]:
        assert entry["label"] in markdown and str(entry["start_minute"]) in markdown
    for name, binding in receipt["files"].items():
        raw = (output / name).read_bytes()
        assert binding == {"size_bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    assert len(network["calls"]) == 1 and network["response_closed"] and network["connection_closed"]
    assert files(path) == before


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(extra="x"), lambda v: v.pop("overview"), lambda v: v.update(overview=""),
    lambda v: v.update(overview="x" * 601), lambda v: v.update(overview="A\nB"),
    lambda v: v.update(overview="A\u202eB"), lambda v: v.update(overview="\ud800"),
    lambda v: v.update(overview="https://example.test"), lambda v: v.update(overview="www.example.test"),
    lambda v: v.update(overview="mailto:team@example.test"), lambda v: v.update(overview="https:example.test"),
    lambda v: v.update(overview="//example.test"), lambda v: v.update(overview="example.test"),
    lambda v: v.update(preparation=[]), lambda v: v.update(preparation=["x"] * 5),
    lambda v: v.update(preparation=["x" * 241]), lambda v: v.update(open_questions=["x"] * 5),
    lambda v: v.update(open_questions=[True]),
])
def test_bad_supplement_is_sanitized_and_never_completes(source, tmp_path, network, mutation):
    from test_event_proposals import response_value
    value = deepcopy(SUPPLEMENT)
    mutation(value)
    response = response_value()
    response["output"][1]["content"][0]["text"] = json.dumps(value)
    network["body"] = json.dumps(response).encode()
    output = tmp_path / "bad"
    with pytest.raises(ValueError, match="^Event follow-up response rejected$"):
        prepare(output, source[0], allow_paid_request=True)
    assert len(network["calls"]) == 1
    assert set(files(output)) == {"request.json"}


def test_data_markdown_is_escaped_and_original_plan_unchanged(source, tmp_path, network):
    from test_event_proposals import response_value
    path, plan, write, _ = source
    plan["selected_option"]["title"] = "<script>*party*</script>"
    write(plan)
    supplement = {**SUPPLEMENT, "overview": "<b>Grüße</b> [Plan](intern) *unverbindlich*"}
    response = response_value()
    response["output"][1]["content"][0]["text"] = json.dumps(supplement)
    network["body"] = json.dumps(response).encode()
    output = tmp_path / "escaped"
    prepare(output, path, allow_paid_request=True)
    md = (output / "event-plan.md").read_text(encoding="utf-8")
    assert "<script>" not in md and "<b>" not in md
    assert "\\*party\\*" in md and "\\[Plan\\]\\(intern\\)" in md
    assert json.loads((output / "followup.json").read_bytes())["plan"] == plan


@pytest.mark.parametrize("overlap", ["same", "inside", "parent", "existing"])
def test_output_must_be_fresh_and_disjoint(source, tmp_path, network, overlap):
    path = source[0]
    output = {"same": path, "inside": path / "new", "parent": tmp_path, "existing": tmp_path / "existing"}[overlap]
    if overlap == "existing": output.mkdir()
    before = files(path)
    with pytest.raises(ValueError):
        prepare(output, path, allow_paid_request=True)
    assert files(path) == before and not network["calls"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows extended path namespace")
def test_extended_namespace_cannot_place_output_inside_source(source, network):
    path = source[0]
    output = Path("\\\\?\\" + str(path.absolute())) / "new-followup"
    with pytest.raises(ValueError, match="fresh disjoint"):
        prepare(output, path)
    assert not (path / "new-followup").exists() and not network["calls"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows short path namespace")
def test_short_path_namespace_cannot_place_output_inside_source(source, network):
    import ctypes
    path = source[0]
    buffer = ctypes.create_unicode_buffer(32768)
    size = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
    if not 0 < size < len(buffer) or buffer.value.casefold() == str(path).casefold():
        pytest.skip("8.3 path alias unavailable on this volume")
    output = Path(buffer.value) / "new-followup"
    with pytest.raises(ValueError, match="fresh disjoint"):
        prepare(output, path)
    assert not (path / "new-followup").exists() and not network["calls"]


def test_followup_cli_wiring_and_default_offline(tmp_path, monkeypatch, capsys):
    from fly_connectome_sim import cli
    calls = []
    def run(output, **kwargs):
        calls.append((output, kwargs))
        return {"status": "dry-run"}
    monkeypatch.setattr(cli, "prepare_event_followup", run)
    assert cli.main(["prepare-event-followup", "--session-dir", "session", "--output-dir", str(tmp_path), "--model", "explicit-model", "--max-output-tokens", "1024"]) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "dry-run"}
    assert calls == [(tmp_path, {"session_dir": Path("session"), **PARAMETERS, "allow_paid_request": False})]


@pytest.mark.parametrize("stage", ["inspection-read", "before-post", "after-post", "before-receipt", "same-bytes-new-inode"])
def test_source_changes_reject_completion_without_retry(source, tmp_path, network, monkeypatch, stage):
    from fly_connectome_sim.experiment import event_followup as followup
    path = source[0]
    def mutate():
        member = path / "recording.json"
        if stage == "same-bytes-new-inode":
            replacement = path / "replacement.json"
            replacement.write_bytes(member.read_bytes())
            os.replace(replacement, member)
        else:
            member.write_bytes(member.read_bytes() + b" ")
    if stage == "inspection-read":
        original = followup._inspect_session
        def inspect(*args, **kwargs):
            result = original(*args, **kwargs)
            mutate()
            return result
        monkeypatch.setattr(followup, "_inspect_session", inspect)
    elif stage == "before-post":
        original = followup._request
        def request(*args):
            result = original(*args)
            mutate()
            return result
        monkeypatch.setattr(followup, "_request", request)
    elif stage in {"after-post", "same-bytes-new-inode"}:
        original = followup.provider._post
        def post(*args):
            raw = original(*args)
            mutate()
            return raw
        monkeypatch.setattr(followup.provider, "_post", post)
    else:
        original = Path.open
        class Writer:
            def __enter__(self):
                self.stream = original(tmp_path / "changed/event-plan.md", "xb")
                return self.stream
            def __exit__(self, *args):
                self.stream.close()
                mutate()
        def opening(member, mode="r", *args, **kwargs):
            if member == tmp_path / "changed/event-plan.md" and mode == "xb": return Writer()
            return original(member, mode, *args, **kwargs)
        monkeypatch.setattr(Path, "open", opening)
    output = tmp_path / "changed"
    with pytest.raises(ValueError, match="^Event follow-up source (changed|rejected)$"):
        prepare(output, path, allow_paid_request=True)
    assert len(network["calls"]) == (0 if stage in {"inspection-read", "before-post"} else 1)
    assert not (output / "receipt.json").exists()
    if stage == "before-receipt": assert set(files(output)) == {"request.json", "followup.json", "event-plan.md"}


@pytest.mark.parametrize("member", ["receipt.json", "plan.json", "recording.json"])
def test_source_symlinks_are_rejected(source, tmp_path, network, member):
    path = source[0] / member
    original = path.with_suffix(".original")
    path.rename(original)
    try:
        path.symlink_to(original)
    except OSError as error:
        if error.errno in {1, 13} or getattr(error, "winerror", None) in {5, 1314}:
            pytest.skip("Symlink creation unavailable")
        raise
    with pytest.raises(ValueError, match="^Event follow-up source rejected$"):
        prepare(tmp_path / "alias", source[0], allow_paid_request=True)
    assert not network["calls"]


def test_output_parent_symlink_is_rejected(source, tmp_path, network):
    parent = tmp_path / "parent"
    parent.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(parent, target_is_directory=True)
    except OSError as error:
        if error.errno in {1, 13} or getattr(error, "winerror", None) in {5, 1314}:
            pytest.skip("Symlink creation unavailable")
        raise
    with pytest.raises(ValueError):
        prepare(alias / "new", source[0], allow_paid_request=True)
    assert not list(parent.iterdir()) and not network["calls"]


@pytest.mark.parametrize("location", ["supplement", "metadata", "escaped-inner"])
def test_active_key_echo_is_rejected_without_persistence(source, tmp_path, network, location):
    from test_event_proposals import response_value
    key = network["key"]
    value = response_value()
    supplement = deepcopy(SUPPLEMENT)
    if location == "metadata": value["id"] = key
    else: supplement["overview"] = key
    inner = json.dumps(supplement)
    if location == "escaped-inner": inner = inner.replace(key, "".join("\\u%04x" % ord(c) for c in key))
    value["output"][1]["content"][0]["text"] = inner
    network["body"] = json.dumps(value).encode()
    output = tmp_path / "secret"
    with pytest.raises(ValueError, match="^Event follow-up response rejected$"):
        prepare(output, source[0], allow_paid_request=True)
    assert len(network["calls"]) == 1 and set(files(output)) == {"request.json"}
    assert key.encode() not in b"".join(files(output).values())


@pytest.mark.parametrize("key", ["sk-\"quoted-key", "sk-back\\slash-key"])
def test_escaped_source_key_never_enters_request(source, tmp_path, network, monkeypatch, key):
    path, plan, write, _ = source
    plan["selected_option"]["title"] = key
    write(plan)
    monkeypatch.setenv("OPENAI_API_KEY", key)
    output = tmp_path / "key-request"
    with pytest.raises(ValueError): prepare(output, path, allow_paid_request=True)
    assert not output.exists() and not network["calls"]


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(status="incomplete"), lambda v: v.update(error={"message": KEY}),
    lambda v: v["output"][1].update(content=[{"type": "refusal", "refusal": KEY}]),
    lambda v: v["usage"].update(output_tokens=True), lambda v: v["usage"].update(total_tokens=1),
])
def test_shared_envelope_guards_apply_to_followup(source, tmp_path, network, mutation):
    from test_event_proposals import response_value
    value = response_value()
    value["output"][1]["content"][0]["text"] = json.dumps(SUPPLEMENT)
    mutation(value)
    network["body"] = json.dumps(value).encode()
    with pytest.raises(ValueError, match="^Event follow-up response rejected$"):
        prepare(tmp_path / "envelope", source[0], allow_paid_request=True)
    assert len(network["calls"]) == 1 and set(files(tmp_path / "envelope")) == {"request.json"}


def test_untrusted_transport_exception_is_sanitized_no_retry(source, tmp_path, network, monkeypatch):
    from fly_connectome_sim.experiment import event_followup as followup
    from fly_connectome_sim.experiment.recorder import RunArtifactError
    calls = []
    def fail(*args):
        calls.append(1)
        raise RunArtifactError(network["key"] + " private failure")
    monkeypatch.setattr(followup.provider, "_post", fail)
    with pytest.raises(ValueError, match="^Event follow-up transport failed$"):
        prepare(tmp_path / "transport", source[0], allow_paid_request=True)
    assert calls == [1] and set(files(tmp_path / "transport")) == {"request.json"}


@pytest.mark.parametrize("member", ["request.json", "followup.json", "event-plan.md", "receipt.json"])
def test_publication_failure_never_overwrites_or_declares_success(source, tmp_path, network, monkeypatch, member):
    output = tmp_path / "publication"
    original = Path.open
    def collide(path, mode="r", *args, **kwargs):
        if path == output / member and mode == "xb":
            path.write_bytes(b"unchanged sentinel")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", collide)
    with pytest.raises(ValueError, match="^Event follow-up publication failed$"):
        prepare(output, source[0], allow_paid_request=True)
    assert (output / member).read_bytes() == b"unchanged sentinel"
    assert len(network["calls"]) == (0 if member == "request.json" else 1)
    if member != "receipt.json": assert not (output / "receipt.json").exists()


@pytest.mark.parametrize("role", ["source", "output-parent"])
def test_source_and_output_junctions_rejected(source, tmp_path, network, role):
    if sys.platform != "win32": pytest.skip("Windows junction case")
    actual = source[0] if role == "source" else tmp_path / "real-parent"
    if role == "output-parent": actual.mkdir()
    alias = tmp_path / "junction"
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(actual)], capture_output=True, check=False)
    if result.returncode and (b"Zugriff verweigert" in result.stderr or b"Access is denied" in result.stderr):
        pytest.skip("Windows sandbox denied junction creation")
    assert result.returncode == 0 and alias.is_junction()
    output = tmp_path / "new" if role == "source" else alias / "new"
    with pytest.raises(ValueError): prepare(output, alias if role == "source" else source[0], allow_paid_request=True)
    assert not network["calls"] and not output.exists()


def historical_session():
    path = Path(__file__).resolve().parents[2] / "runs/cell-demo-20261108-02/session"
    if not path.is_dir(): pytest.skip("Accepted historical session not present in this checkout")
    return path


def test_actual_inspected_historical_session_offline_is_read_only(tmp_path, monkeypatch):
    import os
    from fly_connectome_sim.experiment.event_followup import prepare_event_followup
    path = historical_session()
    before = files(path)
    monkeypatch.setattr(type(os.environ), "get", lambda *a: pytest.fail("Offline integration read credentials"))
    receipt = prepare_event_followup(tmp_path / "actual-offline", session_dir=path, **PARAMETERS)
    assert receipt["status"] == "dry-run"
    assert receipt["source"]["plan_sha256"] == sha256(before["plan.json"]).hexdigest()
    assert files(path) == before


@pytest.mark.parametrize("stage", ["before-post", "after-post"])
def test_real_inspector_rejects_forged_exports_and_changed_raw_source(tmp_path, network, monkeypatch, stage):
    from fly_connectome_sim.experiment import event_followup as followup
    path = Path(shutil.copytree(historical_session(), tmp_path / "copied-session"))
    if stage == "before-post":
        original = followup._request
        def request(*args):
            result = original(*args)
            plan = json.loads((path / "plan.json").read_bytes())
            plan["selected_option"]["title"] = "Forged title"
            raw = _canonical(plan) + b"\n"
            (path / "plan.json").write_bytes(raw)
            receipt = json.loads((path / "receipt.json").read_bytes())
            receipt["files"]["plan.json"] = {"sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
            (path / "receipt.json").write_bytes(_canonical(receipt) + b"\n")
            return result
        monkeypatch.setattr(followup, "_request", request)
    else:
        original = followup.provider._post
        def post(*args):
            raw = original(*args)
            events = path / "run/events.jsonl"
            events.write_bytes(events.read_bytes() + b"{}\n")
            return raw
        monkeypatch.setattr(followup.provider, "_post", post)
    with pytest.raises(ValueError, match="^Event follow-up source rejected$"):
        prepare(tmp_path / "raw-change", path, allow_paid_request=True)
    assert len(network["calls"]) == (0 if stage == "before-post" else 1)
    assert set(files(tmp_path / "raw-change")) == {"request.json"}
