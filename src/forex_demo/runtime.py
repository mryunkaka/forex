"""Continuous, news-only observer for the demo runtime.

This process deliberately does not call the model or connect to MT5. It keeps
the official-source polling and event deduplication serviceable while the
market-data bridge and EA compatibility work are incomplete.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from forex_demo.feeds.config import load_sources
from forex_demo.feeds.official_releases import OfficialReleaseFeed, SourceConfig
from forex_demo.llm_client import ModelClient
from forex_demo.market import MarketSnapshot
from forex_demo.runtime_config import load_runtime_config_file, read_model_api_key
from forex_demo.shadow_pipeline import ShadowNewsPipeline
from forex_demo.state import StateStore

LOGGER = logging.getLogger("forex_demo.runtime")


class NewsObserver:
    def __init__(
        self,
        *,
        sources: tuple[SourceConfig, ...],
        store: StateStore,
        fetch: Callable[[SourceConfig], tuple] = OfficialReleaseFeed.fetch,
        pipeline: ShadowNewsPipeline | None = None,
    ) -> None:
        self._sources = sources
        self._store = store
        self._fetch = fetch
        self._pipeline = pipeline

    def poll_once(self, *, now_utc: datetime | None = None) -> dict[str, int]:
        now = now_utc or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            raise ValueError("now_utc must be timezone-aware UTC")
        checked = discovered = failures = 0
        calls_before = self._store.count_model_calls(now.date().isoformat())
        for source in self._sources:
            checked += 1
            try:
                items = self._fetch(source)
                new_count = 0
                for item in sorted(items, key=lambda row: (row.published_at_utc, row.event_id)):
                    if self._store.claim_event(item.event_id, item.source_id, item.published_at_utc):
                        new_count += 1
                        try:
                            published = datetime.fromisoformat(item.published_at_utc.replace("Z", "+00:00"))
                        except ValueError:
                            published = now - timedelta(days=3650)
                        if published >= now - timedelta(minutes=30):
                            LOGGER.info("new_feed_item source=%s published_at=%s event_id=%s", item.source_id, item.published_at_utc, item.event_id)
                        if self._pipeline is not None:
                            try:
                                result = self._pipeline.process(item, now_utc=now)
                                if getattr(result, "mode", None) == "shadow":
                                    LOGGER.info("shadow_proposal event_id=%s action=%s confidence=%.3f", item.event_id,
                                                result.decision.action.value, result.decision.confidence)
                                elif getattr(result, "reason", "") not in {"provider_disabled", "stale", "importance_too_low", "currency_not_relevant"}:
                                    LOGGER.info("shadow_event event_id=%s status=WAIT reason=%s", item.event_id,
                                                getattr(result, "reason", "no_proposal"))
                            except Exception as exc:
                                LOGGER.warning("shadow_pipeline_failed event_id=%s error_type=%s", item.event_id, type(exc).__name__)
                                self._store.record_runtime_health(
                                    "shadow_ai", "ERROR", now.isoformat(),
                                    {"event_id": item.event_id, "error_type": type(exc).__name__, "trading_enabled": False},
                                )
                discovered += new_count
                self._store.record_runtime_health(
                    f"feed:{source.source_id}", "OK", now.isoformat(),
                    {"items_seen": len(items), "new_items": new_count},
                )
            except Exception as exc:  # a bad source must not stop other feeds
                failures += 1
                LOGGER.warning("feed_poll_failed source=%s error_type=%s", source.source_id, type(exc).__name__)
                self._store.record_runtime_health(
                    f"feed:{source.source_id}", "ERROR", now.isoformat(),
                    {"error_type": type(exc).__name__},
                )
        status = "OK" if failures == 0 else ("ERROR" if failures == checked else "DEGRADED")
        model_calls = self._store.count_model_calls(now.date().isoformat()) - calls_before
        self._store.record_runtime_health(
            "news_observer", status, now.isoformat(),
            {"sources_checked": checked, "new_items": discovered, "source_failures": failures,
             "model_calls": model_calls, "model_enabled": bool(self._pipeline and self._pipeline.model_enabled),
             "trading_enabled": False},
        )
        LOGGER.info("poll_complete status=%s sources=%d new_items=%d failures=%d model_calls=%d trading_enabled=false",
                    status, checked, discovered, failures, model_calls)
        return {"sources_checked": checked, "new_items": discovered, "failures": failures, "model_calls": model_calls}


def run_forever(*, observer: NewsObserver, interval_seconds: int = 300) -> None:
    if isinstance(interval_seconds, bool) or interval_seconds < 30:
        raise ValueError("poll interval must be at least 30 seconds")
    while True:
        observer.poll_once()
        time.sleep(interval_seconds)


def build_observer(
    source_config: str | Path,
    database_path: str | Path,
    *,
    env_path: str | Path = ".env",
    snapshot_path: str | Path | None = None,
) -> NewsObserver:
    env_path = Path(env_path)
    sources = load_sources(source_config)
    config = load_runtime_config_file(env_path)
    api_key = read_model_api_key(env_path)
    client = None
    if config.model_provider_enabled:
        client = ModelClient(
            base_url=config.model_base_url,
            model_id=config.model_id,
            api_key=api_key,
            timeout_seconds=config.model_timeout_seconds,
        )
    if snapshot_path is None:
        common_files = Path.home() / ".mt5-finex-demo-staging-11.21" / "drive_c" / "users" / "saidadam28" / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files"
        snapshot_path = common_files / "forex_demo_snapshot.csv"
    store = StateStore(database_path)
    pipeline = ShadowNewsPipeline(
        config=config,
        store=store,
        client=client,
        snapshot_reader=lambda **kwargs: MarketSnapshot.read(snapshot_path, **kwargs),
        source_ids={source.source_id for source in sources},
    )
    return NewsObserver(sources=sources, store=store, pipeline=pipeline)
