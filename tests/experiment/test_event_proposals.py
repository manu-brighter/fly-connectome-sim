"""Offline fixtures exercise the real bounded adapter, never the API."""

from copy import deepcopy
from hashlib import sha256
import http.client
import json
from pathlib import Path
import subprocess
import sys

import pytest

from fly_connectome_sim.experiment.event_cards import load_event_proposal


KEY = "sk-test-active-credential-do-not-persist"
PARAMETERS = {"title": "Summer team party", "guests": 100, "max_budget_chf": 5000,
              "model": "explicit-model", "max_output_tokens": 1024}
EXAMPLE = Path(__file__).parents[2] / "examples/event-options.json"


def prepare(target, **kwargs):
    from fly_connectome_sim.experiment.event_proposals import prepare_event_proposal

    return prepare_event_proposal(target, **(PARAMETERS | kwargs))


def response_value():
    return {
        "id": "resp_fixture", "model": "explicit-model-snapshot", "status": "completed",
        "error": None, "incomplete_details": None,
        "output": [
            {"type": "reasoning", "id": "rs_fixture", "summary": []},
            {"type": "message", "id": "msg_fixture", "role": "assistant", "status": "completed",
             "content": [{"type": "output_text", "text": EXAMPLE.read_text(encoding="utf-8"),
                          "annotations": []}]},
        ],
        "usage": {"input_tokens": 120, "output_tokens": 250, "total_tokens": 370,
                  "input_tokens_details": {"cached_tokens": 0},
                  "output_tokens_details": {"reasoning_tokens": 0}},
    }


@pytest.fixture(autouse=True)
def forbid_real_https(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("real HTTPS is forbidden in these tests")
    monkeypatch.setattr(http.client, "HTTPSConnection", forbidden)


@pytest.fixture
def network(monkeypatch):
    """Replace only HTTPS I/O; keep builder/parser/validator/publication real."""
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    state = {"body": json.dumps(response_value()).encode(), "status": 200,
             "encoding": None, "calls": [], "reads": [], "response_closed": False,
             "connection_closed": False, "fail": None}

    class Response:
        @property
        def status(self):
            return state["status"]

        def getheader(self, name, default=None):
            assert name.lower() == "content-encoding"
            return state["encoding"] if state["encoding"] is not None else default

        def read(self, amount):
            state["reads"].append(amount)
            if state["fail"] == "read":
                raise OSError(KEY + " private provider text")
            return state["body"][:amount]

        def close(self):
            state["response_closed"] = True
            if state["fail"] == "response-close":
                raise OSError(KEY)

    class Connection:
        def __init__(self, host, *, timeout):
            assert host == "api.openai.com" and timeout == 30
            if state["fail"] == "constructor":
                raise OSError(KEY)

        def request(self, method, path, body, headers):
            state["calls"].append((method, path, body, headers))
            assert method == "POST" and path == "/v1/responses"
            assert headers["Authorization"] == "Bearer " + KEY
            assert headers["Content-Type"] == "application/json"
            if "target" in state:
                assert (state["target"] / "request.json").read_bytes() == body
                assert not (state["target"] / "proposal.json").exists()
                assert not (state["target"] / "receipt.json").exists()
            if state["fail"] == "request":
                raise OSError(KEY + " private provider text")

        def getresponse(self):
            if state["fail"] == "getresponse":
                raise OSError(KEY)
            return Response()

        def close(self):
            state["connection_closed"] = True
            if state["fail"] == "connection-close":
                raise OSError(KEY)

    monkeypatch.setattr(http.client, "HTTPSConnection", Connection)
    return state


def assert_incomplete(target):
    assert target.is_dir()
    assert (target / "request.json").is_file()
    assert not (target / "receipt.json").exists()
    for path in target.iterdir():
        assert KEY.encode() not in path.read_bytes()


def test_default_writes_offline_request_without_reading_credentials(tmp_path, monkeypatch):
    import os

    def forbidden(*args, **kwargs):
        pytest.fail("offline preparation read credentials")
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(type(os.environ), "__getitem__", forbidden)
    target = tmp_path / "offline"
    receipt = prepare(target)
    assert set(path.name for path in target.iterdir()) == {"request.json", "receipt.json"}
    request_raw = (target / "request.json").read_bytes()
    request = json.loads(request_raw)
    assert len(request_raw) <= 65536
    assert request["model"] == "explicit-model"
    assert request["store"] is False and request["stream"] is False
    assert request["max_output_tokens"] == 1024
    assert "tools" not in request
    assert receipt == json.loads((target / "receipt.json").read_bytes())
    assert receipt == {"version": "event-proposal-receipt/v1", "status": "dry-run",
                       "provider": "openai", "endpoint": "https://api.openai.com/v1/responses",
                       "requested_model": "explicit-model", "max_output_tokens": 1024,
                       "request_sha256": sha256(request_raw).hexdigest()}
    text = json.dumps(request["input"])
    assert "Summer team party" in text and "5000" in text and "100" in text
    assert "illustrative" in text and "ASCII" in text and "selection" in text

    format_ = request["text"]["format"]
    assert format_["type"] == "json_schema" and format_["strict"] is True
    assert format_["name"] == "event_options"
    def closed(schema):
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
            assert set(schema["required"]) == set(schema["properties"])
            for item in schema["properties"].values():
                closed(item)
        if schema.get("type") == "array":
            closed(schema["items"])
    schema = format_["schema"]
    closed(schema)
    assert schema["properties"]["version"]["enum"] == ["event-options/v1"]
    assert schema["properties"]["options"]["items"]["properties"]["setting"]["enum"] == ["rooftop", "warehouse"]


@pytest.mark.parametrize("overrides", [
    {"title": ""}, {"title": "x" * 49}, {"title": "www.example.test"}, {"title": "ü"},
    {"guests": 9}, {"guests": 501}, {"guests": True}, {"max_budget_chf": 99},
    {"max_budget_chf": 100001}, {"model": ""}, {"model": "x" * 101},
    {"model": "bad/model"}, {"model": "_model"}, {"model": "m\n"}, {"model": "mödel"},
    {"max_output_tokens": 511}, {"max_output_tokens": 4097},
    {"max_output_tokens": True}, {"max_output_tokens": 512.0}, {"allow_paid_request": "yes"},
])
def test_preflight_rejects_invalid_input_without_output_or_credentials(tmp_path, monkeypatch, overrides):
    import os

    def forbidden(*args, **kwargs):
        pytest.fail("invalid input read credentials")
    monkeypatch.setattr(os, "getenv", forbidden)
    target = tmp_path / "invalid"
    with pytest.raises(ValueError):
        prepare(target, **overrides)
    assert not target.exists()


@pytest.mark.parametrize("limit", [512, 4096])
def test_explicit_token_boundaries_are_accepted_offline(tmp_path, limit):
    assert prepare(tmp_path / "offline", max_output_tokens=limit)["max_output_tokens"] == limit


def test_live_requires_key_before_reserving_output(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError) as error:
        prepare(tmp_path / "missing-key", allow_paid_request=True)
    assert "OPENAI_API_KEY" in str(error.value)
    assert not (tmp_path / "missing-key").exists()


@pytest.mark.parametrize("kind", ["directory", "file", "missing-parent"])
def test_output_is_never_reused_or_parents_created(tmp_path, network, kind):
    target = tmp_path / "out"
    if kind == "directory":
        target.mkdir()
        (target / "sentinel").write_bytes(b"unchanged")
    elif kind == "file":
        target.write_bytes(b"unchanged")
    else:
        target = tmp_path / "missing-parent" / "out"
    with pytest.raises(ValueError):
        prepare(target, allow_paid_request=True)
    assert not network["calls"]
    if kind == "directory":
        assert [path.name for path in target.iterdir()] == ["sentinel"]
    elif kind == "file":
        assert target.read_bytes() == b"unchanged"
    else:
        assert not target.parent.exists()


def test_existing_directory_link_is_not_followed_or_reused(tmp_path, network):
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "sentinel").write_bytes(b"unchanged")
    link = tmp_path / "linked-output"
    if sys.platform == "win32":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(existing)],
                                capture_output=True, check=False)
        if result.returncode and (b"Zugriff verweigert" in result.stderr or b"Access is denied" in result.stderr):
            pytest.skip("Windows sandbox denied junction creation; requires normal-host acceptance")
        assert result.returncode == 0, "test junction creation failed"
        assert link.is_junction()
    else:
        link.symlink_to(existing, target_is_directory=True)
    with pytest.raises(ValueError, match="^Event proposal publication failed$"):
        prepare(link, allow_paid_request=True)
    assert [path.name for path in existing.iterdir()] == ["sentinel"]
    assert not network["calls"]


def test_valid_response_is_one_request_then_importable_proposal_and_allowlisted_receipt(tmp_path, network):
    target = tmp_path / "live-fixture"
    network["target"] = target
    receipt = prepare(target, allow_paid_request=True)
    assert len(network["calls"]) == 1
    assert network["reads"] == [262145]
    assert network["response_closed"] and network["connection_closed"]
    assert load_event_proposal(target / "proposal.json") == json.loads(EXAMPLE.read_bytes())
    assert receipt == json.loads((target / "receipt.json").read_bytes())
    assert set(receipt) == {"version", "status", "provider", "endpoint", "requested_model",
                            "max_output_tokens", "request_sha256", "proposal_sha256",
                            "response_sha256", "response_id", "response_model", "usage"}
    assert receipt["status"] == "validated"
    assert receipt["response_id"] == "resp_fixture"
    assert receipt["response_model"] == "explicit-model-snapshot"
    assert receipt["usage"] == {"input_tokens": 120, "output_tokens": 250, "total_tokens": 370}
    assert receipt["request_sha256"] == sha256((target / "request.json").read_bytes()).hexdigest()
    assert receipt["proposal_sha256"] == sha256((target / "proposal.json").read_bytes()).hexdigest()
    assert receipt["response_sha256"] == sha256(network["body"]).hexdigest()
    assert network["calls"][0][2] == (target / "request.json").read_bytes()
    assert KEY.encode() not in b"".join(path.read_bytes() for path in target.iterdir())


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(status="incomplete"), lambda p: p.update(error={"message": KEY}),
    lambda p: p.update(incomplete_details={"reason": "max_output_tokens"}),
    lambda p: p.update(id=""), lambda p: p.update(id="r" * 201),
    lambda p: p.update(model="bad/model"), lambda p: p.update(output=[]),
    lambda p: p["output"].append(deepcopy(p["output"][1])),
    lambda p: p["output"].append({"type": "function_call", "name": "secret"}),
    lambda p: p["output"].append({"type": "unknown"}),
    lambda p: p["output"][1].update(role="user"),
    lambda p: p["output"][1].update(status="in_progress"),
    lambda p: p["output"][1]["content"].append({"type": "output_text", "text": "{}"}),
    lambda p: p["output"][1].update(content=[{"type": "refusal", "refusal": "no"}]),
    lambda p: p["output"][1]["content"][0].update(text=" " * 65537),
    lambda p: p["output"][1]["content"][0].update(text='{"secret-key":1,"secret-key":2}'),
    lambda p: p["output"][1]["content"][0].update(text='{"x":NaN}'),
    lambda p: p["output"][1]["content"][0].update(text=EXAMPLE.read_text().replace("Summer team party", "Other party")),
    lambda p: p["output"][1]["content"][0].update(text=EXAMPLE.read_text().replace('"warehouse-techno"', '"sunset-house"')),
    lambda p: p["output"][1]["content"][0].update(text=EXAMPLE.read_text().replace('"budget_chf": 4800', '"budget_chf": 99999')),
    lambda p: p["usage"].update(output_tokens=True),
    lambda p: p["usage"].update(input_tokens=-1),
    lambda p: p["usage"].update(total_tokens=371),
    lambda p: p["usage"].update(output_tokens=1025, total_tokens=1145),
    lambda p: p["usage"].pop("input_tokens"),
    lambda p: p["usage"].update(input_tokens=1.0),
])
def test_bad_response_is_sanitized_incomplete_and_never_retried(tmp_path, network, mutation):
    value = response_value()
    mutation(value)
    network["body"] = json.dumps(value).encode()
    target = tmp_path / "bad"
    with pytest.raises(ValueError) as error:
        prepare(target, allow_paid_request=True)
    assert str(error.value) == "Event proposal response rejected"
    assert len(network["calls"]) == 1
    assert network["response_closed"] and network["connection_closed"]
    assert_incomplete(target)
    assert not (target / "proposal.json").exists()


@pytest.mark.parametrize("body", [b"\xff", b'{"x":1,"x":2}', b" " * 262145,
                                  (" " * 1000 + KEY).encode()],
                         ids=["utf8", "duplicate", "oversized", "credential-echo"])
def test_response_bytes_are_bounded_strict_and_secret_free(tmp_path, network, body):
    network["body"] = body
    target = tmp_path / "bad-bytes"
    with pytest.raises(ValueError, match="^Event proposal response rejected$"):
        prepare(target, allow_paid_request=True)
    assert_incomplete(target)
    assert not (target / "proposal.json").exists()
    assert network["reads"] == [262145]
    assert len(network["calls"]) == 1


@pytest.mark.parametrize("status,encoding", [(400, None), (401, None), (429, None),
                                            (500, None), (302, None), (200, "gzip"),
                                            (200, "br")])
def test_http_errors_redirects_and_compression_are_rejected_without_body_or_retry(tmp_path, network, status, encoding):
    network.update(status=status, encoding=encoding, body=KEY.encode())
    target = tmp_path / "http-error"
    with pytest.raises(ValueError, match="^Event proposal transport failed$"):
        prepare(target, allow_paid_request=True)
    assert len(network["calls"]) == 1 and not network["reads"]
    assert network["response_closed"] and network["connection_closed"]
    assert_incomplete(target)


@pytest.mark.parametrize("stage", ["constructor", "request", "getresponse", "read",
                                   "response-close", "connection-close"])
def test_transport_exceptions_and_closures_never_echo_secret_or_retry(tmp_path, network, stage):
    network["fail"] = stage
    target = tmp_path / "exception"
    with pytest.raises(ValueError, match="^Event proposal transport failed$"):
        prepare(target, allow_paid_request=True)
    assert len(network["calls"]) <= 1
    if stage != "constructor":
        assert network["connection_closed"]
    if stage in {"read", "response-close", "connection-close"}:
        assert network["response_closed"]
    assert_incomplete(target)


def test_active_key_echo_in_request_rejected_before_output_or_network(tmp_path, network):
    target = tmp_path / "request-key"
    with pytest.raises(ValueError) as error:
        prepare(target, title=KEY, allow_paid_request=True)
    assert KEY not in str(error.value)
    assert not target.exists() and not network["calls"]


@pytest.mark.parametrize("failed_file", ["request.json", "proposal.json", "receipt.json"])
def test_exclusive_publication_failure_is_sanitized_and_keeps_partial_directory(tmp_path, network, monkeypatch, failed_file):
    target = tmp_path / "partial"
    opened = []
    original = Path.open

    def fail_write(self, mode="r", *args, **kwargs):
        if self.parent == target and "x" in mode:
            opened.append(self.name)
            if self.name == failed_file:
                raise OSError(KEY + " sensitive path")
        return original(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_write)
    with pytest.raises(ValueError, match="^Event proposal publication failed$"):
        prepare(target, allow_paid_request=True)
    assert target.is_dir() and not (target / "receipt.json").exists()
    expected = ["request.json", "proposal.json", "receipt.json"]
    assert opened == expected[:expected.index(failed_file) + 1]
    assert len(network["calls"]) == (0 if failed_file == "request.json" else 1)
    assert (target / "proposal.json").exists() is (failed_file == "receipt.json")


def test_existing_file_created_during_publication_is_not_overwritten(tmp_path, network, monkeypatch):
    target = tmp_path / "race"
    original = Path.open

    def collision(self, mode="r", *args, **kwargs):
        if self == target / "proposal.json" and mode == "xb":
            self.write_bytes(b"sentinel")
        return original(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", collision)
    with pytest.raises(ValueError, match="^Event proposal publication failed$"):
        prepare(target, allow_paid_request=True)
    assert (target / "proposal.json").read_bytes() == b"sentinel"
    assert not (target / "receipt.json").exists()


def test_decoded_credential_echo_cannot_be_published_even_when_wire_escaped(tmp_path, network):
    value = response_value()
    value["output"][1]["content"][0]["text"] = EXAMPLE.read_text().replace("Sunset House", KEY)
    # The wire representation contains only Unicode escapes for the active key.
    escaped = "".join("\\u%04x" % ord(char) for char in KEY)
    network["body"] = json.dumps(value).replace(KEY, escaped).encode()
    target = tmp_path / "escaped-key"
    with pytest.raises(ValueError, match="^Event proposal response rejected$"):
        prepare(target, allow_paid_request=True)
    assert_incomplete(target)


@pytest.mark.parametrize("key", ['sk-"quoted-key', "sk-back\\slash-key"])
def test_escaped_request_credential_is_rejected_before_publication(tmp_path, network, monkeypatch, key):
    monkeypatch.setenv("OPENAI_API_KEY", key)
    target = tmp_path / "escaped-request"
    with pytest.raises(ValueError):
        prepare(target, title=key, allow_paid_request=True)
    assert not target.exists() and not network["calls"]


@pytest.mark.parametrize("name", ["request.json", "proposal.json", "receipt.json"])
def test_midwrite_failure_retains_partial_bytes_without_retry_or_success_receipt(tmp_path, network, monkeypatch, name):
    target = tmp_path / "midwrite"
    original = Path.open

    class PartialWriter:
        def __enter__(self):
            self.output = original(target / name, "xb")
            return self

        def write(self, raw):
            self.output.write(raw[:7])
            raise OSError(KEY)

        def __exit__(self, *args):
            self.output.close()

    def fail_after_open(self, mode="r", *args, **kwargs):
        if self == target / name and mode == "xb":
            return PartialWriter()
        return original(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_after_open)
    with pytest.raises(ValueError, match="^Event proposal publication failed$"):
        prepare(target, allow_paid_request=True)
    assert (target / name).stat().st_size == 7
    assert len(network["calls"]) == (0 if name == "request.json" else 1)
    if name == "receipt.json":
        with pytest.raises(json.JSONDecodeError):
            json.loads((target / name).read_bytes())
    else:
        assert not (target / "receipt.json").exists()


def test_escaped_credential_in_returned_metadata_is_not_saved(tmp_path, network):
    value = response_value()
    value["id"] = KEY
    escaped = "".join("\\u%04x" % ord(char) for char in KEY)
    network["body"] = json.dumps(value).replace(KEY, escaped).encode()
    target = tmp_path / "escaped-metadata"
    with pytest.raises(ValueError, match="^Event proposal response rejected$"):
        prepare(target, allow_paid_request=True)
    assert_incomplete(target)


def test_inner_json_escaped_credential_reaches_proposal_guard_and_is_rejected(tmp_path, network, monkeypatch):
    from fly_connectome_sim.experiment import event_proposals

    proposal = json.loads(EXAMPLE.read_bytes())
    proposal["options"][0]["title"] = KEY
    escaped = "".join("\\u%04x" % ord(char) for char in KEY)
    value = response_value()
    value["output"][1]["content"][0]["text"] = json.dumps(proposal).replace(KEY, escaped)
    network["body"] = json.dumps(value).encode()
    assert KEY not in json.loads(network["body"])["output"][1]["content"][0]["text"]
    reached = []
    original = event_proposals._contains_key

    def capture(item, key):
        if type(item) is dict and item.get("version") == "event-options/v1":
            reached.append(item["options"][0]["title"])
        return original(item, key)
    monkeypatch.setattr(event_proposals, "_contains_key", capture)
    target = tmp_path / "inner-escaped-key"
    with pytest.raises(ValueError, match="^Event proposal response rejected$"):
        prepare(target, allow_paid_request=True)
    assert reached == [KEY]
    assert_incomplete(target)
    assert not (target / "proposal.json").exists()


def test_exact_response_and_proposal_byte_bounds_allow_valid_padding(tmp_path, network):
    value = response_value()
    text = value["output"][1]["content"][0]["text"]
    value["output"][1]["content"][0]["text"] = text + " " * (65536 - len(text.encode()))
    raw = json.dumps(value).encode()
    network["body"] = raw + b" " * (262144 - len(raw))
    target = tmp_path / "exact-bounds"
    assert prepare(target, allow_paid_request=True)["status"] == "validated"
    assert load_event_proposal(target / "proposal.json") == json.loads(EXAMPLE.read_bytes())


@pytest.mark.parametrize("stage", [None, "read"])
def test_actual_paid_cli_uses_fake_transport_without_native_or_secret_diagnostics(tmp_path, network, monkeypatch, capsys, stage):
    from fly_connectome_sim import cli

    def forbidden(*args, **kwargs):
        pytest.fail("proposal constructed native engine")
    monkeypatch.setattr(cli.FlyEngine, "from_prepared_graph", forbidden)
    network["fail"] = stage
    target = tmp_path / "cli-fixture"
    code = cli.main(["prepare-event-proposal", "--title", "Summer team party", "--guests", "100",
                     "--max-budget-chf", "5000", "--model", "explicit-model",
                     "--max-output-tokens", "1024", "--allow-paid-request", "--output-dir", str(target)])
    captured = capsys.readouterr()
    assert KEY not in captured.out + captured.err
    assert len(network["calls"]) == 1
    if stage is None:
        assert code == 0 and json.loads(captured.out)["status"] == "validated" and not captured.err
    else:
        assert code == 1 and not captured.out
        assert captured.err == "fly-connectome-sim: Event proposal transport failed\n"
        assert_incomplete(target)
