"""Persistent deduplication and redacted decision audit storage."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping


_DECISION_FIELDS = {
    "record_id",
    "event_id",
    "decided_at_utc",
    "model_id",
    "prompt_version",
    "schema_version",
    "decision_json",
    "status",
    "reason",
    "latency_ms",
}
_SECRET_PARTS = ("api_key", "apikey", "password", "secret", "token", "authorization")


def _assert_no_secret_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(part in normalized for part in _SECRET_PARTS):
                raise ValueError("audit record contains a secret-like field")
            _assert_no_secret_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_no_secret_keys(child)


class StateStore:
    """SQLite-backed event dedupe and append-only decision record store."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    published_at_utc TEXT NOT NULL,
                    claimed_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
                );
                CREATE INDEX IF NOT EXISTS idx_events_source_time
                    ON events(source_id, published_at_utc, event_id);
                CREATE TABLE IF NOT EXISTS source_cursors (
                    source_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    published_at_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    record_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    decided_at_utc TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_health (
                    component TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    detail_json TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def claim_event(self, event_id: str, source_id: str, published_at_utc: str) -> bool:
        if not event_id or not source_id or not published_at_utc:
            raise ValueError("event_id, source_id, and published_at_utc are required")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO events(event_id, source_id, published_at_utc) VALUES (?, ?, ?) "
                "ON CONFLICT(event_id) DO NOTHING",
                (event_id, source_id, published_at_utc),
            )
            if cursor.rowcount == 1:
                connection.execute(
                    """INSERT INTO source_cursors(source_id, event_id, published_at_utc)
                    VALUES (?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET
                    event_id = excluded.event_id, published_at_utc = excluded.published_at_utc""",
                    (source_id, event_id, published_at_utc),
                )
            return cursor.rowcount == 1

    def get_last_processed(self, source_id: str) -> tuple[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT event_id, published_at_utc FROM source_cursors WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        if row is None:
            return None
        return row["event_id"], row["published_at_utc"]

    def record_decision(self, record: Mapping[str, Any]) -> None:
        _assert_no_secret_keys(record)
        missing = _DECISION_FIELDS - set(record)
        unexpected = set(record) - _DECISION_FIELDS
        if missing or unexpected:
            parts = []
            if missing:
                parts.append("missing fields: " + ", ".join(sorted(missing)))
            if unexpected:
                parts.append("unexpected fields: " + ", ".join(sorted(unexpected)))
            raise ValueError("; ".join(parts))
        latency = record["latency_ms"]
        if isinstance(latency, bool) or not isinstance(latency, int) or latency < 0:
            raise ValueError("latency_ms must be a non-negative integer")
        decision_json = json.dumps(record["decision_json"], sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO decisions(
                    record_id, event_id, decided_at_utc, model_id, prompt_version,
                    schema_version, decision_json, status, reason, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record["record_id"],
                    record["event_id"],
                    record["decided_at_utc"],
                    record["model_id"],
                    record["prompt_version"],
                    record["schema_version"],
                    decision_json,
                    record["status"],
                    record["reason"],
                    latency,
                ),
            )

    def get_decision(self, record_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM decisions WHERE record_id = ?", (record_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "record_id": row["record_id"],
            "event_id": row["event_id"],
            "decided_at_utc": row["decided_at_utc"],
            "model_id": row["model_id"],
            "prompt_version": row["prompt_version"],
            "schema_version": row["schema_version"],
            "decision_json": json.loads(row["decision_json"]),
            "status": row["status"],
            "reason": row["reason"],
            "latency_ms": row["latency_ms"],
        }

    def record_runtime_health(
        self, component: str, status: str, updated_at_utc: str, detail: Mapping[str, Any]
    ) -> None:
        if not component or not status or not updated_at_utc:
            raise ValueError("component, status, and updated_at_utc are required")
        _assert_no_secret_keys(detail)
        detail_json = json.dumps(detail, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO runtime_health(component, status, updated_at_utc, detail_json)
                VALUES (?, ?, ?, ?) ON CONFLICT(component) DO UPDATE SET
                status = excluded.status,
                updated_at_utc = excluded.updated_at_utc,
                detail_json = excluded.detail_json""",
                (component, status, updated_at_utc, detail_json),
            )

    def get_runtime_health(self, component: str) -> tuple[str, str, dict[str, Any]] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, updated_at_utc, detail_json FROM runtime_health WHERE component = ?",
                (component,),
            ).fetchone()
        if row is None:
            return None
        return row["status"], row["updated_at_utc"], json.loads(row["detail_json"])
