"""News-triggered GPT proposal path. This module has no order interface."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Callable

from forex_demo.decision_service import DecisionService, ProviderDisabled, ShadowProposal, WaitResult
from forex_demo.eligibility import is_eligible
from forex_demo.feeds.base import FeedItem
from forex_demo.market import MarketSnapshot, MarketSnapshotError
from forex_demo.models import DecisionAuditRecord
from forex_demo.runtime_config import RuntimeConfig
from forex_demo.state import StateStore


PipelineResult = ProviderDisabled | WaitResult | ShadowProposal


class ShadowNewsPipeline:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        store: StateStore,
        client,
        snapshot_reader: Callable[..., MarketSnapshot] = MarketSnapshot.read,
        source_ids: set[str],
    ) -> None:
        self._config = config
        self._store = store
        self._client = client
        self._snapshot_reader = snapshot_reader
        self._source_ids = set(source_ids)
        self._decision_service = DecisionService(
            client=client,
            enabled=config.model_provider_enabled,
            calls_per_day=config.model_daily_call_limit,
        )

    @property
    def model_enabled(self) -> bool:
        return self._config.model_provider_enabled

    def process(self, event: FeedItem, *, now_utc: datetime | None = None) -> PipelineResult:
        now = now_utc or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() != timedelta(0):
            return WaitResult(reason="invalid_clock")
        now = now.astimezone(timezone.utc)
        if not self._config.model_provider_enabled:
            return ProviderDisabled()
        if len(event.event_id) > 128:
            return WaitResult(reason="event_id_too_long")
        currency_prefix = self._config.mt5_symbol.split(".", 1)[0][:6]
        currencies = {currency_prefix[:3], currency_prefix[3:6]}
        eligible = is_eligible(
            event,
            now_utc=now,
            allowlist=self._source_ids,
            currencies=currencies,
            max_age=timedelta(minutes=30),
            min_importance=2,
        )
        if not eligible.eligible:
            result = WaitResult(reason=eligible.reason)
            self._record_health(event, now, "WAIT", result.reason)
            return result
        try:
            snapshot = self._snapshot_reader(
                expected_server=self._config.mt5_expected_server,
                expected_symbol=self._config.mt5_symbol,
                now_utc=now,
            )
        except MarketSnapshotError as exc:
            reason = str(exc).replace(" ", "_")[:64]
            result = WaitResult(reason="market_snapshot_invalid")
            self._record_health(event, now, "WAIT", reason)
            return result
        if snapshot is None:
            result = WaitResult(reason="market_snapshot_unavailable")
            self._record_health(event, now, "WAIT", result.reason)
            return result
        if (
            snapshot.account_mode != "demo"
            or snapshot.server != self._config.mt5_expected_server
            or snapshot.symbol != self._config.mt5_symbol
            or snapshot.timeframe != "M5"
        ):
            result = WaitResult(reason="market_snapshot_identity_mismatch")
            self._record_health(event, now, "WAIT", result.reason)
            return result
        age = now - snapshot.observed_at_utc
        if age < timedelta(seconds=-15) or age > timedelta(seconds=90):
            result = WaitResult(reason="market_snapshot_stale")
            self._record_health(event, now, "WAIT", result.reason)
            return result
        if not self._store.claim_model_call(event.event_id, now.date().isoformat(),
                                            daily_limit=self._config.model_daily_call_limit):
            result = WaitResult(reason="daily_call_limit")
            self._record_health(event, now, "WAIT", result.reason)
            return result
        market_context = snapshot.to_context(now_utc=now)["market_snapshot"]
        request_started = monotonic()
        result = self._decision_service.process(
            event,
            market_context,
            now_utc=now,
            allowlist=self._source_ids,
            currencies=currencies,
        )
        if isinstance(result, ShadowProposal):
            decision = result.decision
            decision_json = {
                "event_id": decision.event_id,
                "created_at_utc": decision.created_at_utc.isoformat().replace("+00:00", "Z"),
                "valid_until_utc": decision.valid_until_utc.isoformat().replace("+00:00", "Z"),
                "symbol": decision.symbol,
                "timeframe": decision.timeframe,
                "action": decision.action.value,
                "confidence": decision.confidence,
                "strategy_profile": decision.strategy_profile.value,
                "reason_code": decision.reason_code,
                "source_ids": list(decision.source_ids),
            }
            self._store.record_decision(DecisionAuditRecord(
                record_id="shadow:" + event.event_id,
                event_id=event.event_id,
                decided_at_utc=now.isoformat().replace("+00:00", "Z"),
                model_id=self._config.model_id,
                prompt_version="v1",
                schema_version="decision-v1",
                decision_json=decision_json,
                status="SHADOW",
                reason="model_proposal_only",
                latency_ms=max(0, round((monotonic() - request_started) * 1000)),
            ).to_mapping())
            self._store.record_runtime_health(
                "shadow_ai", "SHADOW", now.isoformat(),
                {"event_id": event.event_id, "action": decision.action.value,
                 "confidence": decision.confidence, "trading_enabled": False},
            )
        else:
            self._record_health(event, now, "WAIT", result.reason)
        return result

    def _record_health(self, event: FeedItem, now: datetime, status: str, reason: str) -> None:
        self._store.record_runtime_health(
            "shadow_ai", status, now.isoformat(),
            {"event_id": event.event_id, "reason": reason, "trading_enabled": False},
        )
