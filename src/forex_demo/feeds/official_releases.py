"""RSS/Atom parser and bounded HTTPS client for allowlisted official sources."""

from __future__ import annotations

import hashlib
import html
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import urlparse

from forex_demo.feeds.base import FeedItem


_MAX_FEED_BYTES = 2 * 1024 * 1024
_HTML_TAG = re.compile(r"<[^>]*>")


class FeedParseError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceConfig:
    source_id: str
    url: str
    currency_tags: tuple[str, ...]
    importance: int
    allowed_hosts: tuple[str, ...] = ()
    allow_title_only: bool = False

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("source URL must use HTTPS")
        hosts = self.allowed_hosts or (parsed.hostname.lower(),)
        if parsed.hostname.lower() not in {host.lower() for host in hosts}:
            raise ValueError("source URL host must be in allowed_hosts")
        if not self.source_id or not self.currency_tags:
            raise ValueError("source_id and currency_tags are required")
        if self.importance not in range(0, 4):
            raise ValueError("importance must be from 0 through 3")

    @property
    def hosts(self) -> frozenset[str]:
        parsed_host = urlparse(self.url).hostname
        return frozenset(host.lower() for host in (self.allowed_hosts or (parsed_host,)))


class _HostAllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: Iterable[str]):
        super().__init__()
        self.allowed_hosts = {host.lower() for host in allowed_hosts}

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname is None or parsed.hostname.lower() not in self.allowed_hosts:
            raise urllib.error.HTTPError(newurl, code, "redirect host is not allowlisted", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class OfficialReleaseFeed:
    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].lower()

    @staticmethod
    def _child_text(node: ET.Element, name: str) -> str:
        for child in node:
            if OfficialReleaseFeed._local_name(child.tag) == name.lower():
                return " ".join("".join(child.itertext()).split())
        return ""

    @staticmethod
    def _date(value: str) -> datetime:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            try:
                normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
                parsed = datetime.fromisoformat(normalized)
            except (TypeError, ValueError) as exc:
                raise FeedParseError("feed item has an invalid publication timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise FeedParseError("feed item timestamp is missing a timezone")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(html.unescape(_HTML_TAG.sub(" ", value)).split())

    @classmethod
    def parse(cls, payload: bytes, source: SourceConfig) -> tuple[FeedItem, ...]:
        if len(payload) > _MAX_FEED_BYTES:
            raise FeedParseError("feed exceeds the 2 MiB size limit")
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise FeedParseError("feed is not valid XML") from exc

        entries = [node for node in root.iter() if cls._local_name(node.tag) in {"item", "entry"}]
        items: list[FeedItem] = []
        for entry in entries:
            title_raw = cls._child_text(entry, "title")
            summary_raw = cls._child_text(entry, "description") or cls._child_text(entry, "summary")
            if not summary_raw and source.allow_title_only:
                summary_raw = "Source feed does not provide a summary."
            published_raw = (
                cls._child_text(entry, "pubdate")
                or cls._child_text(entry, "published")
                or cls._child_text(entry, "updated")
            )
            link = cls._child_text(entry, "link")
            if not link:
                for child in entry:
                    if cls._local_name(child.tag) == "link":
                        link = child.attrib.get("href", "")
                        if child.attrib.get("rel", "alternate") == "alternate":
                            break
            guid = cls._child_text(entry, "guid") or cls._child_text(entry, "id") or link
            title, summary = cls._clean_text(title_raw), cls._clean_text(summary_raw)
            if not title or not summary or not link or not published_raw or not guid:
                raise FeedParseError("feed entry is missing title, summary, link, id, or timestamp")
            parsed_link = urlparse(link)
            if parsed_link.scheme != "https" or not parsed_link.hostname:
                raise FeedParseError("feed entry link must use HTTPS")
            published = cls._date(published_raw)
            stable_id = f"{source.source_id}:{guid}"
            if len(stable_id) > 200:
                stable_id = f"{source.source_id}:{hashlib.sha256(guid.encode()).hexdigest()}"
            items.append(
                FeedItem(
                    source_id=source.source_id,
                    event_id=stable_id,
                    published_at_utc=published.isoformat(timespec="seconds").replace("+00:00", "Z"),
                    currency_tags=source.currency_tags,
                    importance=source.importance,
                    title=title,
                    summary=summary,
                    url=link,
                    original_published_at=published_raw,
                )
            )
        return tuple(items)

    @classmethod
    def fetch(cls, source: SourceConfig, *, timeout_seconds: float = 8.0) -> tuple[FeedItem, ...]:
        parsed = urlparse(source.url)
        if parsed.scheme != "https" or parsed.hostname is None or parsed.hostname.lower() not in source.hosts:
            raise ValueError("feed URL is not allowlisted")
        request = urllib.request.Request(
            source.url,
            headers={"User-Agent": "forex-demo-shadow/0.1 (public-feed reader)"},
        )
        opener = urllib.request.build_opener(_HostAllowlistRedirectHandler(source.hosts))
        with opener.open(request, timeout=timeout_seconds) as response:
            payload = response.read(_MAX_FEED_BYTES + 1)
        return cls.parse(payload, source)
