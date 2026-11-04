"""Shadow-only decision orchestration; this module has no order or bridge API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from forex_demo.eligibility import is_eligible
from forex_demo.feeds.base import FeedItem
from forex_demo.schemas import Decision


class ProposalClient(Protocol):
    def propose(self, context: Mapping[str, Any]) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ProviderDisabled:
    action: str = "WAIT"
    reason: str = "provider_disabled"


@dataclass(frozen=True, slots=True)
class WaitResult:
    action: str = "WAIT"
    reason: str = "provider_error"


@dataclass(frozen=True, slots=True)
class ShadowProposal:
    decision: Decision
    mode: str = "shadow"


class DecisionService:
    """Call an injected proposal client within a daily budget, always shadow-only."""

    def __init__(self, *, client: ProposalClient, enabled: bool = False, calls_per_day: int = 5):
        if isinstance(calls_per_day, bool) or calls_per_day < 0:
            raise ValueError("calls_per_day must be a non-negative integer")
        if not isinstance(calls_per_day, int):
            raise ValueError("calls_per_day must be a non-negative integer")
        self._client = client
        self._enabled = enabled
        self._calls_per_day = calls_per_day
        self._call_day: str | None = None
        self._calls_today = 0
        self._seen_event_ids: set[str] = set()

    def process(
        self,
        event: FeedItem,
        market_snapshot: Mapping[str, Any],
        *,
        now_utc: datetime,
        allowlist: set[str] | None = None,
        currencies: set[str] | None = None,
    ) -> ProviderDisabled | WaitResult | ShadowProposal:
        if not self._enabled:
            return ProviderDisabled()
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            return WaitResult(reason="invalid_clock")
        now = now_utc.astimezone(timezone.utc)
        eligibility = is_eligible(
            event,
            now_utc=now,
            allowlist=allowlist if allowlist is not None else {event.source_id},
            currencies=currencies if currencies is not None else set(event.currency_tags),
        )
        if not eligibility.eligible:
            return WaitResult(reason=eligibility.reason)
        if event.event_id in self._seen_event_ids:
            return WaitResult(reason="duplicate_event")
        day = now.date().isoformat()
        if day != self._call_day:
            self._call_day, self._calls_today = day, 0
        if self._calls_today >= self._calls_per_day:
            return WaitResult(reason="daily_call_limit")
        self._seen_event_ids.add(event.event_id)
        self._calls_today += 1
        context = {
            "event": {
                "source_id": event.source_id,
                "event_id": event.event_id,
                "published_at_utc": event.published_at_utc,
                "currency_tags": list(event.currency_tags),
                "importance": event.importance,
                "title": event.title,
                "summary": event.summary,
                "url": event.url,
            },
            "market_snapshot": dict(market_snapshot),
        }
        try:
            raw = self._client.propose(context)
            decision = Decision.from_mapping(raw, now_utc=now)
        except Exception:
            return WaitResult(reason="provider_error")
        if decision.event_id != event.event_id:
            return WaitResult(reason="event_id_mismatch")
        return ShadowProposal(decision=decision)
