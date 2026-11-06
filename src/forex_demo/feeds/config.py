"""TOML loading for explicit, allowlisted public feed sources."""

from __future__ import annotations

import tomllib
from pathlib import Path

from forex_demo.feeds.official_releases import SourceConfig


def load_sources(path: str | Path) -> tuple[SourceConfig, ...]:
    try:
        with Path(path).open("rb") as stream:
            config = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot load source configuration: {exc}") from exc
    rows = config.get("source", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("source configuration must contain at least one [[source]] entry")

    sources: list[SourceConfig] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each source entry must be a table")
        allowed_fields = {"source_id", "url", "currency_tags", "importance", "allowed_hosts", "allow_title_only"}
        required_fields = allowed_fields - {"allow_title_only"}
        if set(row) - allowed_fields or required_fields - set(row):
            raise ValueError("source entry has missing or unexpected fields")
        source = SourceConfig(
            source_id=row["source_id"],
            url=row["url"],
            currency_tags=tuple(row["currency_tags"]),
            importance=row["importance"],
            allowed_hosts=tuple(row["allowed_hosts"]),
            allow_title_only=row.get("allow_title_only", False),
        )
        if source.source_id in seen:
            raise ValueError(f"duplicate source_id: {source.source_id}")
        seen.add(source.source_id)
        sources.append(source)
    return tuple(sources)
