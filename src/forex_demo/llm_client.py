"""Small OpenAI-compatible 9Router client with one bounded, redacted request."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from forex_demo.prompt import make_messages


class ModelClientError(RuntimeError):
    """A sanitized provider error safe to store in an audit record."""


class ModelClient:
    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        api_key: str,
        timeout_seconds: int = 10,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("model API key is required")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be an integer from 1 through 60")
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._model_id = model_id
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds

    def propose(self, context: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            payload = json.dumps(
                {
                    "model": self._model_id,
                    "messages": make_messages(context),
                    "temperature": 0,
                    "max_tokens": 350,
                    "stream": False,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            request = Request(
                self._url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw_response = response.read(65_537)
            if len(raw_response) > 65_536:
                raise ValueError("response too large")
            envelope = json.loads(raw_response.decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
            if not isinstance(content, str) or len(content) > 16_384:
                raise ValueError("invalid model content")
            decision = json.loads(content)
            if not isinstance(decision, Mapping):
                raise ValueError("decision must be an object")
            return decision
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, ValueError, KeyError, IndexError, TypeError):
            # Do not expose request credentials, provider response bodies, or exception details.
            raise ModelClientError("model request failed or returned invalid JSON") from None
