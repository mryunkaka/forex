from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from forex_demo.schemas import Decision, DecisionValidationError


def sample_decision(**overrides):
    value = {
        "event_id": "evt-001",
        "created_at_utc": "2026-11-04T10:00:00Z",
        "valid_until_utc": "2026-11-04T10:15:00Z",
        "symbol": "EURUSD",
        "timeframe": "M5",
        "action": "BUY",
        "confidence": 0.72,
        "strategy_profile": "TREND",
        "reason_code": "NEWS_AND_TREND",
        "source_ids": ["calendar:fed:123"],
    }
    value.update(overrides)
    return value


def test_accepts_a_complete_current_decision():
    decision = Decision.from_mapping(
        sample_decision(), now_utc=datetime(2026, 11, 4, 10, 1, tzinfo=timezone.utc)
    )

    assert decision.action == "BUY"
    assert decision.symbol == "EURUSD"
    assert decision.valid_until_utc - decision.created_at_utc == timedelta(minutes=15)


def test_rejects_any_execution_override_fields():
    with pytest.raises(DecisionValidationError, match="unexpected fields"):
        Decision.from_mapping(
            sample_decision(lot_size=0.5),
            now_utc=datetime(2026, 11, 4, 10, 1, tzinfo=timezone.utc),
        )


def test_rejects_expired_proposals():
    with pytest.raises(DecisionValidationError, match="expired"):
        Decision.from_mapping(
            sample_decision(),
            now_utc=datetime(2026, 11, 4, 10, 16, tzinfo=timezone.utc),
        )


def test_rejects_naive_timestamps():
    with pytest.raises(DecisionValidationError, match="UTC timezone"):
        Decision.from_mapping(
            sample_decision(created_at_utc="2026-11-04T10:00:00"),
            now_utc=datetime(2026, 11, 4, 10, 1, tzinfo=timezone.utc),
        )


def test_published_json_schema_rejects_execution_overrides():
    schema_path = Path(__file__).parents[1] / "schemas" / "decision-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(sample_decision(lot_size=0.1)))
