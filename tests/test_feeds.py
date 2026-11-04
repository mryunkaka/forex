from datetime import datetime, timedelta, timezone
from pathlib import Path

from forex_demo.eligibility import is_eligible
from forex_demo.feeds.config import load_sources
from forex_demo.feeds.official_releases import OfficialReleaseFeed, SourceConfig


def test_parses_rss_release_and_normalizes_timestamp_to_utc():
    payload = b"""<?xml version='1.0'?>
    <rss version='2.0'><channel><item>
      <guid>fed-123</guid><title>Policy statement</title>
      <link>https://example.gov/policy</link>
      <pubDate>Wed, 04 Nov 2026 10:00:00 +0000</pubDate>
      <description><![CDATA[Rate statement &amp; outlook]]></description>
    </item></channel></rss>"""
    source = SourceConfig(
        source_id="fed-policy",
        url="https://example.gov/feed.xml",
        currency_tags=("USD",),
        importance=2,
    )

    items = OfficialReleaseFeed.parse(payload, source)

    assert len(items) == 1
    assert items[0].event_id == "fed-policy:fed-123"
    assert items[0].published_at_utc == "2026-11-04T10:00:00Z"
    assert items[0].currency_tags == ("USD",)
    assert "Rate statement" in items[0].summary


def test_eligibility_rejects_stale_disallowed_and_wrong_currency_items():
    payload = b"""<rss><channel><item><guid>id1</guid><title>News</title>
    <link>https://example.gov/news</link><pubDate>Wed, 04 Nov 2026 08:00:00 +0000</pubDate>
    <description>Summary</description></item></channel></rss>"""
    source = SourceConfig("fed-policy", "https://example.gov/feed.xml", ("USD",), 2)
    item = OfficialReleaseFeed.parse(payload, source)[0]
    now = datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc)

    stale = is_eligible(item, now_utc=now, allowlist={"fed-policy"}, currencies={"USD"})
    disallowed = is_eligible(item, now_utc=now, allowlist=set(), currencies={"USD"})
    wrong_currency = is_eligible(item, now_utc=now, allowlist={"fed-policy"}, currencies={"EUR"})

    assert stale.reason == "stale"
    assert disallowed.reason == "source_not_allowed"
    assert wrong_currency.reason == "currency_not_relevant"


def test_eligibility_rejects_future_published_timestamp():
    payload = b"""<rss><channel><item><guid>id2</guid><title>Future</title>
    <link>https://example.gov/future</link><pubDate>Wed, 04 Nov 2026 10:01:00 +0000</pubDate>
    <description>Summary</description></item></channel></rss>"""
    source = SourceConfig("fed-policy", "https://example.gov/feed.xml", ("USD",), 2)
    item = OfficialReleaseFeed.parse(payload, source)[0]

    result = is_eligible(
        item,
        now_utc=datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc),
        allowlist={"fed-policy"},
        currencies={"USD"},
    )

    assert result.reason == "future_timestamp"


def test_loads_sources_from_toml_and_rejects_duplicate_ids(tmp_path):
    config_path = tmp_path / "sources.toml"
    config_path.write_text(
        """[[source]]
source_id = "fed-policy"
url = "https://www.federalreserve.gov/feeds/press_monetary.xml"
currency_tags = ["USD"]
importance = 2
allowed_hosts = ["www.federalreserve.gov"]
""",
        encoding="utf-8",
    )

    sources = load_sources(config_path)

    assert len(sources) == 1
    assert sources[0].source_id == "fed-policy"
    assert sources[0].currency_tags == ("USD",)

    duplicate = config_path.read_text(encoding="utf-8") + "\n" + config_path.read_text(encoding="utf-8")
    config_path.write_text(duplicate, encoding="utf-8")
    import pytest

    with pytest.raises(ValueError, match="duplicate source_id"):
        load_sources(config_path)
