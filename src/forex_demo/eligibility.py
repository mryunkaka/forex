"""Fail-closed freshness, source, and currency filters for feed events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from forex_demo.feeds.base import FeedItem


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    eligible: bool
    reason: str


def _parse_utc(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must include UTC timezone")
    return parsed.astimezone(timezone.utc)


def is_eligible(
    item: FeedItem,
    *,
    now_utc: datetime,
    allowlist: set[str],
    currencies: set[str],
    max_age: timedelta = timedelta(minutes=30),
    min_importance: int = 1,
) -> EligibilityResult:
    if now_utc.tzinfo is None or now_utc.utcoffset() != timedelta(0):
        return EligibilityResult(False, "invalid_clock_timezone")
    if item.source_id not in allowlist:
        return EligibilityResult(False, "source_not_allowed")
    if not item.event_id or not item.title.strip() or not item.summary.strip():
        return EligibilityResult(False, "incomplete_item")
    if item.importance < min_importance:
        return EligibilityResult(False, "importance_too_low")
    if not currencies.intersection(item.currency_tags):
        return EligibilityResult(False, "currency_not_relevant")
    try:
        published = _parse_utc(item.published_at_utc)
    except (TypeError, ValueError):
        return EligibilityResult(False, "invalid_timestamp")
    current = now_utc.astimezone(timezone.utc)
    if published > current:
        return EligibilityResult(False, "future_timestamp")
    if current - published > max_age:
        return EligibilityResult(False, "stale")
    return EligibilityResult(True, "eligible")
