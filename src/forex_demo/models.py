"""Shared immutable records used by feed, decision, and persistence layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DecisionAuditRecord:
    record_id: str
    event_id: str
    decided_at_utc: str
    model_id: str
    prompt_version: str
    schema_version: str
    decision_json: dict[str, Any]
    status: str
    reason: str
    latency_ms: int

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)
