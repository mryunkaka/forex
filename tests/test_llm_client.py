import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from forex_demo.llm_client import ModelClient, ModelClientError


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return json.dumps(self.payload).encode()


def test_posts_bearer_key_to_chat_completions_and_parses_json(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data)
        return FakeResponse(
            {"choices": [{"message": {"content": '{"action":"WAIT"}'}}]}
        )

    monkeypatch.setattr("forex_demo.llm_client.urlopen", fake_urlopen)
    client = ModelClient(
        base_url="http://127.0.0.1:20128/v1",
        model_id="cx/gpt-6-luna",
        api_key="private-key",
        timeout_seconds=7,
    )

    result = client.propose({"event": {"event_id": "e-1"}})

    assert result == {"action": "WAIT"}
    assert captured["url"] == "http://127.0.0.1:20128/v1/chat/completions"
    assert captured["authorization"] == "Bearer private-key"
    assert captured["timeout"] == 7
    assert captured["body"]["model"] == "cx/gpt-6-luna"


def test_rejects_non_json_model_content_without_leaking_key(monkeypatch):
    monkeypatch.setattr(
        "forex_demo.llm_client.urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            {"choices": [{"message": {"content": "```json\n{}\n```"}}]}
        ),
    )
    client = ModelClient(
        base_url="https://router.example/v1",
        model_id="cx/gpt-6-luna",
        api_key="never-log-this-key",
    )

    with pytest.raises(ModelClientError) as error:
        client.propose({})

    assert "never-log-this-key" not in str(error.value)


@pytest.mark.parametrize("exception", [TimeoutError("slow"), URLError("offline")])
def test_network_failures_are_sanitized_and_not_retried(monkeypatch, exception):
    calls = 0

    def fail(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise exception

    monkeypatch.setattr("forex_demo.llm_client.urlopen", fail)
    client = ModelClient(
        base_url="https://router.example/v1",
        model_id="cx/gpt-6-luna",
        api_key="private-key",
    )

    with pytest.raises(ModelClientError, match="request failed") as error:
        client.propose({})

    assert calls == 1
    assert "private-key" not in str(error.value)


def test_http_error_body_is_not_exposed(monkeypatch):
    def fail(*_args, **_kwargs):
        raise HTTPError("https://router", 401, "Unauthorized", {}, BytesIO(b"secret body"))

    monkeypatch.setattr("forex_demo.llm_client.urlopen", fail)
    client = ModelClient(
        base_url="https://router.example/v1",
        model_id="cx/gpt-6-luna",
        api_key="private-key",
    )

    with pytest.raises(ModelClientError) as error:
        client.propose({})

    assert "secret body" not in str(error.value)
    assert "private-key" not in str(error.value)
