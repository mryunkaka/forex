from datetime import datetime, timedelta, timezone

from forex_demo.decision_service import ShadowProposal, WaitResult
from forex_demo.feeds.base import FeedItem
from forex_demo.runtime_config import load_runtime_config
from forex_demo.shadow_pipeline import ShadowNewsPipeline
from forex_demo.state import StateStore


def make_config(*, enabled=True):
    return load_runtime_config({
        "APP_ENV": "demo", "TRADING_MODE": "shadow", "TRADING_EXECUTION_ENABLED": "false",
        "BROKER_NAME": "FINEX", "MT5_EXPECTED_ACCOUNT_MODE": "demo",
        "MT5_EXPECTED_SERVER": "FinexBisnisSolusi-Demo", "MT5_SYMBOL": "EURUSD",
        "MT5_TIMEFRAME": "M5", "MODEL_PROVIDER_ENABLED": str(enabled).lower(),
        "MODEL_BASE_URL": "http://127.0.0.1:20128/v1", "MODEL_ID": "cx/gpt-6-luna",
        "MODEL_TIMEOUT_SECONDS": "12", "MODEL_DAILY_CALL_LIMIT": "2",
        "MODEL_API_KEY": "local-test-key" if enabled else "",
    })


class FakeSnapshot:
    account_mode = "demo"
    symbol = "EURUSD"
    timeframe = "M5"
    server = "FinexBisnisSolusi-Demo"
    observed_at_utc = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)

    def to_context(self, *, now_utc):
        return {"market_snapshot": {"symbol": self.symbol, "timeframe": self.timeframe, "bid": 1.085,
                                    "ask": 1.0852, "spread_points": 2, "candles": []}}


class FakeClient:
    def __init__(self):
        self.calls = []

    def propose(self, context):
        self.calls.append(context)
        now = datetime.fromisoformat(context["current_time_utc"].replace("Z", "+00:00"))
        return {
            "event_id": context["event"]["event_id"],
            "created_at_utc": now.isoformat().replace("+00:00", "Z"),
            "valid_until_utc": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "symbol": "EURUSD", "timeframe": "M5", "action": "WAIT", "confidence": 0.2,
            "strategy_profile": "NO_TRADE", "reason_code": "TEST_ONLY",
            "source_ids": [context["event"]["source_id"]],
        }


def event(now, event_id="ecb:item-1"):
    return FeedItem("ecb", event_id, (now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
                    ("EUR",), 2, "ECB policy update", "No source summary provided.",
                    "https://www.ecb.europa.eu/update", "timestamp")


def test_news_pipeline_calls_model_once_and_persists_shadow_proposal(tmp_path):
    now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    store = StateStore(tmp_path / "state.sqlite3")
    client = FakeClient()
    pipeline = ShadowNewsPipeline(config=make_config(), store=store, client=client,
                                  snapshot_reader=lambda **_: FakeSnapshot(), source_ids={"ecb"})

    result = pipeline.process(event(now), now_utc=now)
    assert isinstance(result, ShadowProposal)
    assert result.decision.action.value == "WAIT"
    assert len(client.calls) == 1
    assert store.get_decision("shadow:ecb:item-1")["status"] == "SHADOW"
    assert isinstance(pipeline.process(event(now), now_utc=now), WaitResult)
    assert len(client.calls) == 1


def test_news_pipeline_fails_closed_without_snapshot_or_provider(tmp_path):
    now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    store = StateStore(tmp_path / "state.sqlite3")
    client = FakeClient()
    missing_market = ShadowNewsPipeline(config=make_config(), store=store, client=client,
                                        snapshot_reader=lambda **_: None, source_ids={"ecb"})
    assert missing_market.process(event(now), now_utc=now).reason == "market_snapshot_unavailable"
    disabled = ShadowNewsPipeline(config=make_config(enabled=False), store=store, client=client,
                                   snapshot_reader=lambda **_: FakeSnapshot(), source_ids={"ecb"})
    assert disabled.process(event(now, "ecb:item-2"), now_utc=now).reason == "provider_disabled"
    assert not client.calls


def test_daily_model_limit_persists_across_pipeline_instances(tmp_path):
    now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    store = StateStore(tmp_path / "state.sqlite3")
    client = FakeClient()
    pipeline = ShadowNewsPipeline(config=make_config(), store=store, client=client,
                                  snapshot_reader=lambda **_: FakeSnapshot(), source_ids={"ecb"})
    pipeline.process(event(now, "ecb:item-1"), now_utc=now)
    pipeline.process(event(now, "ecb:item-2"), now_utc=now)
    other_instance = ShadowNewsPipeline(config=make_config(), store=StateStore(tmp_path / "state.sqlite3"),
                                        client=client, snapshot_reader=lambda **_: FakeSnapshot(), source_ids={"ecb"})
    result = other_instance.process(event(now, "ecb:item-3"), now_utc=now)
    assert isinstance(result, WaitResult)
    assert result.reason == "daily_call_limit"
    assert len(client.calls) == 2
