"""Immutable normalized feed records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedItem:
    source_id: str
    event_id: str
    published_at_utc: str
    currency_tags: tuple[str, ...]
    importance: int
    title: str
    summary: str
    url: str
    original_published_at: str
