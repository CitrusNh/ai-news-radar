from datetime import datetime, timezone

import pytest

from backend.app.ingestion import fetch_feed, parse_feed, source_is_fetchable, validate_feed_url
from backend.app.models import Source


RSS = """<?xml version='1.0'?><rss version='2.0'><channel><item><title>AI 发布会</title><link>https://example.com/ai</link><description>公开摘要</description><pubDate>Tue, 01 Sep 2026 08:00:00 GMT</pubDate></item></channel></rss>"""
ATOM = """<feed xmlns='http://www.w3.org/2005/Atom'><entry><title>Atom 事件</title><link href='https://example.com/atom'/><summary>Atom 摘要</summary><updated>2026-09-01T08:00:00Z</updated></entry></feed>"""


def test_validate_feed_url_rejects_relative_and_accepts_https():
    assert validate_feed_url(" https://example.com/feed.xml ") == "https://example.com/feed.xml"
    with pytest.raises(ValueError):
        validate_feed_url("/feed.xml")


def test_parse_rss_and_atom_to_raw_article_shape():
    source = Source("s1", "来源", domain="AI")
    rss_items = parse_feed(RSS, source)
    atom_items = parse_feed(ATOM, source)
    assert rss_items[0]["title"] == "AI 发布会"
    assert rss_items[0]["published_at"].tzinfo == timezone.utc
    assert atom_items[0]["url"] == "https://example.com/atom"


def test_fetch_feed_retries_transient_errors_and_returns_articles():
    source = Source("s1", "来源", feed_url="https://example.com/feed.xml")
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        if len(calls) == 1:
            raise TimeoutError("temporary")
        return 200, RSS

    result = fetch_feed(source, http_get=fake_get, retries=1)
    assert result.status == "success"
    assert len(result.articles) == 1
    assert len(calls) == 2


def test_fetch_feed_does_not_retry_http_policy_failure():
    source = Source("s1", "来源", feed_url="https://example.com/feed.xml")
    calls = []

    def fake_get(url, timeout):
        calls.append(1)
        return 403, "blocked"

    result = fetch_feed(source, http_get=fake_get, retries=3)
    assert result.status == "failed"
    assert result.http_status == 403
    assert len(calls) == 1


def test_source_is_fetchable_requires_active_feed_and_nonblocked_robots():
    assert source_is_fetchable(Source("s1", "来源", feed_url="https://example.com/feed", robots_status="allowed"))
    assert not source_is_fetchable(Source("s2", "来源", feed_url="https://example.com/feed", robots_status="blocked"))
    assert not source_is_fetchable(Source("s3", "来源", feed_url="", robots_status="allowed"))
