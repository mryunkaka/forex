from datetime import datetime, timezone
from dataclasses import replace

from forex_demo.decision_service import DecisionService, ProviderDisabled
from forex_demo.feeds.base import FeedItem


class CountingClient:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def propose(self, context):
        self.calls += 1
        return self.response


def sample_event():
    return FeedItem(
        source_id="fed-policy",
        event_id="fed-policy:evt-1",
        published_at_utc="2026-11-04T10:00:00Z",
        currency_tags=("USD",),
        importance=2,
        title="Policy statement",
        summary="Rates held steady.",
        url="https://example.gov/policy",
        original_published_at="Wed, 04 Nov 2026 10:00:00 +0000",
    )


def test_disabled_provider_fails_closed_without_calling_client():
    client = CountingClient({})
    service = DecisionService(client=client, enabled=False, calls_per_day=5)

    result = service.process(
        sample_event(),
        {"symbol": "EURUSD", "timeframe": "M5"},
        now_utc=datetime(2026, 11, 4, 10, 1, tzinfo=timezone.utc),
    )

    assert isinstance(result, ProviderDisabled)
    assert result.reason == "provider_disabled"
    assert client.calls == 0
    assert not hasattr(result, "bridge_command")


def test_call_budget_blocks_client_after_limit():
    client = CountingClient({})
    service = DecisionService(client=client, enabled=True, calls_per_day=1)
    now = datetime(2026, 11, 4, 10, 1, tzinfo=timezone.utc)

    service.process(sample_event(), {}, now_utc=now)
    second = service.process(replace(sample_event(), event_id="fed-policy:evt-2"), {}, now_utc=now)

    assert client.calls == 1
    assert second.reason == "daily_call_limit"
    assert not hasattr(second, "bridge_command")

    duplicate = service.process(sample_event(), {}, now_utc=now)
    assert duplicate.reason == "duplicate_event"


def test_client_failure_returns_wait_without_exposing_bridge_command():
    class FailingClient:
        def propose(self, context):
            raise TimeoutError("provider timed out")

    result = DecisionService(client=FailingClient(), enabled=True).process(
        sample_event(), {}, now_utc=datetime(2026, 11, 4, 10, 1, tzinfo=timezone.utc)
    )

    assert result.action == "WAIT"
    assert result.reason == "provider_error"
    assert not hasattr(result, "bridge_command")
