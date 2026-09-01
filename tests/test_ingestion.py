from datetime import datetime, timezone

import pytest

from backend.app.ingestion import fetch_feed, parse_feed, parse_public_page, source_is_fetchable, validate_feed_url
from backend.app.models import Source


RSS = """<?xml version='1.0'?><rss version='2.0'><channel><item><title>AI 发布会</title><link>https://example.com/ai</link><description>公开摘要</description><pubDate>Tue, 01 Sep 2026 08:00:00 GMT</pubDate></item></channel></rss>"""
ATOM = """<feed xmlns='http://www.w3.org/2005/Atom'><entry><title>Atom 事件</title><link href='https://example.com/atom'/><summary>Atom 摘要</summary><updated>2026-09-01T08:00:00Z</updated></entry></feed>"""
HTML = """
<main>
  <article><h2><a href='/news/one'>公开网页新闻一</a></h2><p>第一条 <b>摘要</b></p><time datetime='2026-09-01T08:00:00Z'></time></article>
  <article><h2><a href='/news/one'>公开网页新闻一（重复卡片）</a></h2></article>
  <article><h2><a href='https://other.example/news/two'>公开网页新闻二</a></h2><p>没有发布时间</p></article>
</main>
"""


def test_validate_feed_url_rejects_relative_and_accepts_https():
    assert validate_feed_url(" https://example.com/feed.xml ") == "https://example.com/feed.xml"
    with pytest.raises(ValueError):
        validate_feed_url("/feed.xml")
    with pytest.raises(ValueError, match="local"):
        validate_feed_url("http://localhost/feed.xml")
    with pytest.raises(ValueError, match="private"):
        validate_feed_url("http://127.0.0.1/feed.xml")


def test_parse_rss_and_atom_to_raw_article_shape():
    source = Source("s1", "来源", domain="AI")
    rss_items = parse_feed(RSS, source)
    atom_items = parse_feed(ATOM, source)
    assert rss_items[0]["title"] == "AI 发布会"
    assert rss_items[0]["published_at"].tzinfo == timezone.utc
    assert atom_items[0]["url"] == "https://example.com/atom"


def test_parse_feed_removes_html_from_source_summary():
    source = Source("s1", "来源")
    payload = RSS.replace("公开摘要", "&lt;p&gt;公开 &lt;b&gt;摘要&lt;/b&gt;&lt;/p&gt;")
    assert parse_feed(payload, source)[0]["summary"] == "公开 摘要"


def test_parse_public_page_handles_relative_links_duplicates_and_missing_dates():
    source = Source("s1", "来源", domain="科技", feed_url="https://example.com/latest")
    before = datetime.now(timezone.utc)
    items = parse_public_page(HTML, source)
    after = datetime.now(timezone.utc)
    assert [item["url"] for item in items] == ["https://example.com/news/one", "https://other.example/news/two"]
    assert items[0]["summary"] == "第一条 摘要"
    assert items[0]["published_at"] == datetime(2026, 9, 1, 8, tzinfo=timezone.utc)
    assert before <= items[1]["published_at"] <= after


def test_parse_public_page_supports_configured_card_selectors():
    source = Source(
        "hn",
        "Hacker News",
        feed_url="https://news.ycombinator.com/",
        fetch_mode="html",
        article_selector="tr.athing",
        title_selector="span.titleline",
        link_selector="span.titleline > a",
    )
    payload = "<table><tr class='athing'><td><span class='titleline'><a href='item?id=1'>Example technology headline</a></span></td></tr></table>"
    assert parse_public_page(payload, source)[0]["url"] == "https://news.ycombinator.com/item?id=1"


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


def test_fetch_feed_uses_html_parser_for_html_sources():
    source = Source("s1", "来源", feed_url="https://example.com/latest", fetch_mode="html")
    result = fetch_feed(source, http_get=lambda _url, _timeout: (200, HTML))
    assert result.status == "success"
    assert len(result.articles) == 2


def test_source_is_fetchable_requires_active_feed_without_explicit_block():
    assert source_is_fetchable(Source("s1", "来源", feed_url="https://example.com/feed", robots_status="allowed", compliance_status="approved"))
    assert not source_is_fetchable(Source("s2", "来源", feed_url="https://example.com/feed", robots_status="blocked", compliance_status="approved"))
    assert not source_is_fetchable(Source("s3", "来源", feed_url="", robots_status="allowed", compliance_status="approved"))
    assert source_is_fetchable(Source("s4", "来源", feed_url="https://example.com/feed", robots_status="allowed", compliance_status="pending"))
    assert not source_is_fetchable(Source("s5", "来源", feed_url="https://example.com/feed", robots_status="allowed", compliance_status="rejected"))
