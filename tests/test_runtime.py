from datetime import datetime, timezone

from forex_demo.feeds.base import FeedItem
from forex_demo.feeds.official_releases import SourceConfig
from forex_demo.runtime import NewsObserver, build_observer
from forex_demo.state import StateStore


def test_news_observer_persists_new_ids_and_reports_zero_model_and_trades(tmp_path):
    source = SourceConfig("fed", "https://www.federalreserve.gov/feed.xml", ("USD",), 2)
    item = FeedItem(
        "fed", "fed:event-1", "2026-11-06T09:55:00Z", ("USD",), 2,
        "Policy update", "Summary", "https://www.federalreserve.gov/item", "Fri, 06 Nov 2026 09:55:00 GMT",
    )
    observer = NewsObserver(sources=(source,), store=StateStore(tmp_path / "state.sqlite3"), fetch=lambda _: (item,))
    now = datetime(2026, 11, 6, 10, 0, tzinfo=timezone.utc)

    assert observer.poll_once(now_utc=now) == {"sources_checked": 1, "new_items": 1, "failures": 0, "model_calls": 0}
    health = StateStore(tmp_path / "state.sqlite3").get_runtime_health("news_observer")
    assert health[0] == "OK"
    assert health[2] == {"model_calls": 0, "model_enabled": False, "new_items": 1,
                         "source_failures": 0, "sources_checked": 1, "trading_enabled": False}
    assert observer.poll_once(now_utc=now)["new_items"] == 0


def test_one_feed_failure_does_not_stop_other_sources(tmp_path):
    sources = (
        SourceConfig("bad", "https://www.federalreserve.gov/bad.xml", ("USD",), 2),
        SourceConfig("good", "https://www.federalreserve.gov/good.xml", ("USD",), 2),
    )

    def fetch(source):
        if source.source_id == "bad":
            raise OSError("network failure")
        return ()

    store = StateStore(tmp_path / "state.sqlite3")
    observer = NewsObserver(sources=sources, store=store, fetch=fetch)
    result = observer.poll_once(now_utc=datetime(2026, 11, 6, tzinfo=timezone.utc))
    assert result == {"sources_checked": 2, "new_items": 0, "failures": 1, "model_calls": 0}
    assert store.get_runtime_health("news_observer")[0] == "DEGRADED"
    assert store.get_runtime_health("feed:good")[0] == "OK"


def test_news_observer_sends_only_new_feed_items_to_shadow_pipeline(tmp_path):
    source = SourceConfig("fed", "https://www.federalreserve.gov/feed.xml", ("USD",), 2)
    item = FeedItem("fed", "fed:new", "2026-11-06T09:59:00Z", ("USD",), 2,
                    "Policy", "Summary", "https://www.federalreserve.gov/item", "Fri, 06 Nov 2026 09:59:00 GMT")

    class Pipeline:
        model_enabled = False
        def __init__(self):
            self.events = []

        def process(self, event, *, now_utc):
            self.events.append((event.event_id, now_utc))

    pipeline = Pipeline()
    observer = NewsObserver(sources=(source,), store=StateStore(tmp_path / "state.sqlite3"),
                            fetch=lambda _: (item,), pipeline=pipeline)
    now = datetime(2026, 11, 6, 10, 0, tzinfo=timezone.utc)
    observer.poll_once(now_utc=now)
    observer.poll_once(now_utc=now)

    assert pipeline.events == [("fed:new", now)]


def test_build_observer_loads_configured_sources_and_shadow_settings(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("""APP_ENV=demo
TRADING_MODE=shadow
TRADING_EXECUTION_ENABLED=false
BROKER_NAME=FINEX
MT5_EXPECTED_ACCOUNT_MODE=demo
MT5_EXPECTED_SERVER=FinexBisnisSolusi-Demo
MT5_SYMBOL=EURUSD
MT5_TIMEFRAME=M5
MODEL_PROVIDER_ENABLED=false
MODEL_BASE_URL=http://127.0.0.1:20128/v1
MODEL_ID=cx/gpt-6-luna
MODEL_TIMEOUT_SECONDS=12
MODEL_DAILY_CALL_LIMIT=5
""", encoding="utf-8")
    sources_path = tmp_path / "sources.toml"
    sources_path.write_text("""[[source]]
source_id="ecb"
url="https://www.ecb.europa.eu/rss/press.html"
currency_tags=["EUR"]
importance=2
allowed_hosts=["www.ecb.europa.eu"]
allow_title_only=true
""", encoding="utf-8")

    observer = build_observer(sources_path, tmp_path / "state.sqlite3", env_path=env_path,
                              snapshot_path=tmp_path / "snapshot.csv")

    assert [source.source_id for source in observer._sources] == ["ecb"]
    assert observer._pipeline.model_enabled is False
