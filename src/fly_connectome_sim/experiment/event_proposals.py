"""Offline-first, one-request event proposals; receipts are local bookkeeping."""

from __future__ import annotations

from hashlib import sha256
import http.client
import os
from pathlib import Path
import re
import ssl

from .event_cards import MAX_PROPOSAL_BYTES, _integer, _text, validate_event_proposal
from .recorder import RunArtifactError, _canonical, _strict_load


ENDPOINT = "https://api.openai.com/v1/responses"
MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}")
RESPONSE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}")


def _object_schema(properties: dict) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def _request(brief: dict, model: str, max_output_tokens: int) -> bytes:
    programme = _object_schema({"start_minute": {"type": "integer"},
                                "label": {"type": "string"}})
    option = _object_schema({
        "id": {"type": "string"}, "title": {"type": "string"},
        "setting": {"type": "string", "enum": ["rooftop", "warehouse"]},
        "music": {"type": "string"}, "budget_chf": {"type": "integer"},
        "capacity": {"type": "integer"}, "duration_minutes": {"type": "integer"},
        "programme": {"type": "array", "items": programme},
    })
    schema = _object_schema({
        "version": {"type": "string", "enum": ["event-options/v1"]},
        "brief": _object_schema({"title": {"type": "string"},
                                  "guests": {"type": "integer"},
                                  "max_budget_chf": {"type": "integer"}}),
        "options": {"type": "array", "items": option},
    })
    instructions = (
        "Propose exactly two event concepts with illustrative estimates, not verified venues or costs. "
        "You have no selection authority. Return only the specified JSON and copy the brief exactly. "
        "Use printable ASCII without URLs. Option IDs must be unique, lowercase letters/digits/hyphens, "
        "begin with a letter and be at most 32 characters. Titles at most 48 characters; music at most 24. "
        "Use setting rooftop or warehouse. Integer budgets 100..brief.max_budget_chf CHF; "
        "integer capacity brief.guests..1000; integer duration_minutes 60..600. "
        "Each programme has 2..6 entries, starts at minute 0, has strictly increasing integer minutes "
        "below duration_minutes and labels of 1..40 characters. All text fields must be nonempty."
    )
    raw = _canonical({
        "model": model, "store": False, "stream": False, "max_output_tokens": max_output_tokens,
        "input": [{"role": "developer", "content": instructions},
                  {"role": "user", "content": _canonical(brief).decode("utf-8")}],
        "text": {"format": {"type": "json_schema", "name": "event_options",
                            "strict": True, "schema": schema}},
    })
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError
    return raw


def _post(request: bytes, key: str) -> bytes:
    connection = None
    response = None
    message = None
    generic = "Event proposal transport failed"
    try:
        try:
            # Direct HTTPS uses the platform's default verified TLS context, no proxy or redirect handler.
            connection = http.client.HTTPSConnection("api.openai.com", timeout=30)
            connection.request("POST", "/v1/responses", body=request, headers={
                "Authorization": "Bearer " + key, "Content-Type": "application/json",
            })
            response = connection.getresponse()
            status = response.status
            # Do not compare, format or hash arbitrary transport-supplied objects.
            if type(status) is not int or status != 200:
                message = generic
                if type(status) is int:
                    category = {400: "invalid request", 401: "authentication", 403: "permission",
                                404: "model/resource", 429: "rate limit or credit"}.get(status)
                    if 500 <= status <= 599:
                        category = "provider unavailable"
                    if category is not None:
                        message = f"{generic}: HTTP {status} ({category})"
            elif response.getheader("Content-Encoding") is not None:
                message = generic + ": compressed response rejected"
            else:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        finally:
            try:
                if response is not None:
                    response.close()
            finally:
                if connection is not None:
                    connection.close()
    except TimeoutError:
        message = message or generic + ": timeout"
    except ssl.SSLError:
        message = message or generic + ": TLS failure"
    except OSError:
        message = message or generic + ": connection/I/O failure"
    except Exception:
        message = message or generic
    # Raise outside exception handlers after both resources have been closed.
    # Provider bodies, headers, reasons and exception text never enter diagnostics.
    if message is not None:
        raise RunArtifactError(message) from None
    return raw


def _identifier(value: object, pattern: re.Pattern) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ValueError
    return value


def _contains_key(value: object, key: str) -> bool:
    if type(value) is str:
        return key in value
    if type(value) is dict:
        return any(_contains_key(name, key) or _contains_key(item, key) for name, item in value.items())
    if type(value) is list:
        return any(_contains_key(item, key) for item in value)
    return False


def _decode(raw: bytes, brief: dict, max_output_tokens: int, key: str) -> tuple[bytes, dict]:
    try:
        if not 1 <= len(raw) <= MAX_RESPONSE_BYTES or key.encode("ascii") in raw:
            raise ValueError
        value = _strict_load(raw)
        if (type(value) is not dict or _contains_key(value, key) or value.get("status") != "completed"
                or value.get("error") is not None or value.get("incomplete_details") is not None):
            raise ValueError
        response_id = _identifier(value.get("id"), RESPONSE_ID)
        model = _identifier(value.get("model"), MODEL)
        usage = value["usage"]
        if type(usage) is not dict:
            raise ValueError
        tokens = {name: _integer(usage[name], 0, 2**63 - 1, "token usage")
                  for name in ("input_tokens", "output_tokens", "total_tokens")}
        if (tokens["total_tokens"] != tokens["input_tokens"] + tokens["output_tokens"]
                or tokens["output_tokens"] > max_output_tokens):
            raise ValueError
        output = value["output"]
        if type(output) is not list:
            raise ValueError
        messages = []
        for item in output:
            if type(item) is not dict:
                raise ValueError
            if item.get("type") == "reasoning":
                if (set(item) - {"type", "id", "summary", "status", "encrypted_content"}
                        or item.get("status", "completed") != "completed"
                        or type(item.get("summary")) is not list):
                    raise ValueError
                for summary in item["summary"]:
                    if (type(summary) is not dict or set(summary) != {"type", "text"}
                            or summary["type"] != "summary_text" or type(summary["text"]) is not str):
                        raise ValueError
            elif (item.get("type") == "message" and item.get("role") == "assistant"
                  and item.get("status") == "completed"):
                messages.append(item)
            else:
                raise ValueError
        if len(messages) != 1:
            raise ValueError
        content = messages[0]["content"]
        if (type(content) is not list or len(content) != 1 or type(content[0]) is not dict
                or content[0].get("type") != "output_text" or type(content[0].get("text")) is not str):
            raise ValueError
        text = content[0]["text"].encode("utf-8")
        if not 1 <= len(text) <= MAX_PROPOSAL_BYTES:
            raise ValueError
        proposal = validate_event_proposal(_strict_load(text))
        if proposal["brief"] != brief or _contains_key(proposal, key):
            raise ValueError
        canonical = _canonical(proposal)
        if len(canonical) > MAX_PROPOSAL_BYTES:
            raise ValueError
        return canonical, {"response_sha256": sha256(raw).hexdigest(),
                           "response_id": response_id, "response_model": model, "usage": tokens}
    except Exception:
        raise RunArtifactError("Event proposal response rejected") from None


def _publish(path: Path, raw: bytes) -> None:
    try:
        with path.open("xb") as output:
            output.write(raw)
    except Exception:
        raise RunArtifactError("Event proposal publication failed") from None


def prepare_event_proposal(
    output_dir: str | Path, *, title: str, guests: int, max_budget_chf: int,
    model: str, max_output_tokens: int, allow_paid_request: bool = False,
) -> dict:
    """Prepare offline, or opt into one paid request; incomplete directories are retained.

    A validated receipt records local validation and hashes, not provider authentication
    or scientific support. Socket timeouts are not a whole-process deadline.
    """
    try:
        brief = {"title": _text(title, 48, "brief title"),
                 "guests": _integer(guests, 10, 500, "guests"),
                 "max_budget_chf": _integer(max_budget_chf, 100, 100000, "maximum budget")}
        _identifier(model, MODEL)
        _integer(max_output_tokens, 512, 4096, "maximum output tokens")
        if type(allow_paid_request) is not bool:
            raise ValueError
        request = _request(brief, model, max_output_tokens)
        target = Path(output_dir)
    except Exception:
        raise RunArtifactError("Invalid event proposal request") from None
    key = None
    if allow_paid_request:
        try:
            key = os.environ.get("OPENAI_API_KEY")
            if (type(key) is not str or not 1 <= len(key) <= 4096
                    or any(not 33 <= ord(char) <= 126 for char in key)):
                raise ValueError
            if (key.encode("ascii") in request or _contains_key(brief, key)
                    or _contains_key(_strict_load(request), key)):
                raise ValueError
        except Exception:
            raise RunArtifactError("Live event proposal requires a valid OPENAI_API_KEY without request echo") from None
    try:
        # Exclusive mkdir rejects existing directories, files, symlinks and junctions.
        target.mkdir()
    except Exception:
        raise RunArtifactError("Event proposal publication failed") from None
    _publish(target / "request.json", request)
    receipt = {"version": "event-proposal-receipt/v1", "status": "dry-run",
               "provider": "openai", "endpoint": ENDPOINT, "requested_model": model,
               "max_output_tokens": max_output_tokens, "request_sha256": sha256(request).hexdigest()}
    if allow_paid_request:
        proposal, provenance = _decode(_post(request, key), brief, max_output_tokens, key)
        receipt.update(status="validated", proposal_sha256=sha256(proposal).hexdigest(), **provenance)
    try:
        receipt_raw = _canonical(receipt)
    except Exception:
        raise RunArtifactError("Event proposal publication failed") from None
    if allow_paid_request:
        if key.encode("ascii") in receipt_raw or _contains_key(receipt, key):
            raise RunArtifactError("Event proposal response rejected")
        _publish(target / "proposal.json", proposal)
    _publish(target / "receipt.json", receipt_raw)
    return receipt
