import sqlite3

from forex_demo.state import StateStore
from forex_demo.models import DecisionAuditRecord
import pytest


def test_claim_event_is_unique_across_store_restarts(tmp_path):
    database = tmp_path / "state.sqlite3"
    store = StateStore(database)

    assert store.claim_event("calendar:123", "calendar", "2026-11-04T10:00:00Z") is True
    assert store.claim_event("calendar:123", "calendar", "2026-11-04T10:00:00Z") is False

    reopened = StateStore(database)
    assert reopened.claim_event("calendar:123", "calendar", "2026-11-04T10:00:00Z") is False


def test_last_processed_event_is_per_source(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    store.claim_event("calendar:1", "calendar", "2026-11-04T10:00:00Z")
    store.claim_event("release:1", "official-release", "2026-11-04T10:02:00Z")

    assert store.get_last_processed("calendar") == ("calendar:1", "2026-11-04T10:00:00Z")
    assert store.get_last_processed("unknown") is None


def test_decision_audit_is_append_only_and_secret_redacted(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    record = {
        "record_id": "decision:1",
        "event_id": "calendar:1",
        "decided_at_utc": "2026-11-04T10:03:00Z",
        "model_id": "cx/gpt-6-luna",
        "prompt_version": "v1",
        "schema_version": "decision-v1",
        "decision_json": {"action": "WAIT", "reason_code": "SHADOW"},
        "status": "SHADOW",
        "reason": "eligible",
        "latency_ms": 120,
    }

    store.record_decision(record)
    assert store.get_decision("decision:1") == record


def test_decision_audit_rejects_secret_like_fields(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")

    with pytest.raises(ValueError, match="secret-like"):
        store.record_decision({"record_id": "bad", "api_key": "sk-example"})


def test_runtime_health_is_persisted_per_component(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    store.record_runtime_health(
        "router", "DISABLED", "2026-11-04T10:00:00Z", {"reason": "cost_cap_unverified"}
    )

    assert store.get_runtime_health("router") == (
        "DISABLED",
        "2026-11-04T10:00:00Z",
        {"reason": "cost_cap_unverified"},
    )


def test_source_cursor_advances_and_duplicate_decisions_are_not_overwritten(tmp_path):
    store = StateStore(tmp_path / "state.sqlite3")
    store.claim_event("calendar:1", "calendar", "2026-11-04T10:00:00Z")
    store.claim_event("calendar:2", "calendar", "2026-11-04T10:05:00Z")
    assert store.get_last_processed("calendar") == ("calendar:2", "2026-11-04T10:05:00Z")

    record = {
        "record_id": "decision:unique",
        "event_id": "calendar:2",
        "decided_at_utc": "2026-11-04T10:06:00Z",
        "model_id": "cx/gpt-6-luna",
        "prompt_version": "v1",
        "schema_version": "decision-v1",
        "decision_json": {"action": "WAIT"},
        "status": "SHADOW",
        "reason": "eligible",
        "latency_ms": 1,
    }
    store.record_decision(record)
    record["reason"] = "overwritten"
    with pytest.raises(sqlite3.IntegrityError):
        store.record_decision(record)
    assert store.get_decision("decision:unique")["reason"] == "eligible"


def test_decision_audit_model_produces_store_mapping():
    record = DecisionAuditRecord(
        record_id="decision:2",
        event_id="calendar:2",
        decided_at_utc="2026-11-04T10:06:00Z",
        model_id="cx/gpt-6-luna",
        prompt_version="v1",
        schema_version="decision-v1",
        decision_json={"action": "WAIT"},
        status="SHADOW",
        reason="eligible",
        latency_ms=1,
    )

    assert record.to_mapping()["decision_json"] == {"action": "WAIT"}
