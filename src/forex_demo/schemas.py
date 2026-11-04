"""Strict validation for model decisions that may be shown to the EA."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping


class DecisionValidationError(ValueError):
    """Raised when a decision does not match the allowlisted schema."""


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"
    WAIT = "WAIT"


class StrategyProfile(str, Enum):
    TREND = "TREND"
    MEAN_REVERSION = "MEAN_REVERSION"
    NEWS_PAUSE = "NEWS_PAUSE"
    NO_TRADE = "NO_TRADE"


_FIELDS = {
    "event_id",
    "created_at_utc",
    "valid_until_utc",
    "symbol",
    "timeframe",
    "action",
    "confidence",
    "strategy_profile",
    "reason_code",
    "source_ids",
}
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,31}$")
_REASON_RE = re.compile(r"^[A-Z0-9_]{1,64}$")
_MAX_HORIZON = timedelta(minutes=15)


def _utc_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise DecisionValidationError(f"{field} must be an ISO-8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DecisionValidationError(f"{field} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise DecisionValidationError(f"{field} must use the UTC timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class Decision:
    event_id: str
    created_at_utc: datetime
    valid_until_utc: datetime
    symbol: str
    timeframe: str
    action: Action
    confidence: float
    strategy_profile: StrategyProfile
    reason_code: str
    source_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, now_utc: datetime) -> "Decision":
        if not isinstance(value, Mapping):
            raise DecisionValidationError("decision must be an object")

        missing = _FIELDS - set(value)
        unexpected = set(value) - _FIELDS
        if missing:
            raise DecisionValidationError(f"missing fields: {', '.join(sorted(missing))}")
        if unexpected:
            raise DecisionValidationError(f"unexpected fields: {', '.join(sorted(unexpected))}")

        if now_utc.tzinfo is None or now_utc.utcoffset() != timedelta(0):
            raise DecisionValidationError("now_utc must use the UTC timezone")
        now = now_utc.astimezone(timezone.utc)
        created = _utc_datetime(value["created_at_utc"], "created_at_utc")
        expiry = _utc_datetime(value["valid_until_utc"], "valid_until_utc")
        if expiry <= created:
            raise DecisionValidationError("valid_until_utc must be later than created_at_utc")
        if expiry - created > _MAX_HORIZON:
            raise DecisionValidationError("decision validity cannot exceed three M5 candles")
        if expiry <= now:
            raise DecisionValidationError("decision is expired")

        event_id = value["event_id"]
        if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 128:
            raise DecisionValidationError("event_id must be a non-empty string up to 128 characters")

        symbol = value["symbol"]
        if not isinstance(symbol, str) or not _SYMBOL_RE.fullmatch(symbol):
            raise DecisionValidationError("symbol has an invalid format")
        if value["timeframe"] != "M5":
            raise DecisionValidationError("timeframe must be M5")

        try:
            action = Action(value["action"])
            profile = StrategyProfile(value["strategy_profile"])
        except (ValueError, TypeError) as exc:
            raise DecisionValidationError("action or strategy_profile is not allowlisted") from exc

        confidence = value["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise DecisionValidationError("confidence must be a number from 0 to 1")
        if not 0 <= confidence <= 1:
            raise DecisionValidationError("confidence must be a number from 0 to 1")

        reason = value["reason_code"]
        if not isinstance(reason, str) or not _REASON_RE.fullmatch(reason):
            raise DecisionValidationError("reason_code must be uppercase letters, digits, or underscores")

        source_ids = value["source_ids"]
        if (
            not isinstance(source_ids, list)
            or any(not isinstance(item, str) or not item.strip() or len(item) > 200 for item in source_ids)
            or len(set(source_ids)) != len(source_ids)
        ):
            raise DecisionValidationError("source_ids must be a unique list of non-empty strings")

        return cls(
            event_id=event_id,
            created_at_utc=created,
            valid_until_utc=expiry,
            symbol=symbol,
            timeframe="M5",
            action=action,
            confidence=float(confidence),
            strategy_profile=profile,
            reason_code=reason,
            source_ids=tuple(source_ids),
        )
