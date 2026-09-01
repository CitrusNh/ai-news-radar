from __future__ import annotations

import time
import ipaddress
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from .models import Source


@dataclass(slots=True)
class FeedFetchResult:
    source_id: str
    status: str
    articles: list[dict]
    error: str | None = None
    http_status: int | None = None


def validate_feed_url(feed_url: str) -> str:
    parsed = urlparse(feed_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("feed URL must be an absolute http(s) URL")
    hostname = (parsed.hostname or "").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise ValueError("feed URL must not target a local host")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_unspecified):
        raise ValueError("feed URL must not target a private or reserved address")
    return feed_url.strip()


def _text(element: object | None) -> str:
    if element is None:
        return ""
    if isinstance(element, ET.Element):
        return "".join(element.itertext()).strip()
    get_text = getattr(element, "get_text", None)
    return get_text(" ", strip=True) if callable(get_text) else str(element).strip()


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_summary(value: str) -> str:
    """Turn feed-provided HTML fragments into compact plain text."""

    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)[:1000]


def parse_feed(xml_payload: str, source: Source) -> list[dict]:
    """Parse RSS 2.0 or Atom XML into the internal raw article shape."""

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as exc:
        raise ValueError("feed XML is invalid") from exc
    articles: list[dict] = []
    root_name = root.tag.rsplit("}", 1)[-1].lower()
    if root_name == "rss":
        nodes = root.findall("./channel/item")
        for node in nodes:
            link = _text(node.find("link"))
            title = _text(node.find("title"))
            summary = _clean_summary(_text(node.find("description")))
            published = _text(node.find("pubDate"))
            if title and link:
                articles.append({"source_id": source.id, "url": link, "title": title, "summary": summary, "channel": source.default_channel, "published_at": _parse_datetime(published), "entities": []})
    else:
        nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() == "entry"]
        for node in nodes:
            title = _text(next((child for child in node if child.tag.rsplit("}", 1)[-1].lower() == "title"), None))
            summary = _clean_summary(_text(next((child for child in node if child.tag.rsplit("}", 1)[-1].lower() in {"summary", "content"}), None)))
            published = _text(next((child for child in node if child.tag.rsplit("}", 1)[-1].lower() in {"published", "updated"}), None))
            links = [child.attrib.get("href", "") for child in node if child.tag.rsplit("}", 1)[-1].lower() == "link"]
            link = next((item for item in links if item), "")
            if title and link:
                articles.append({"source_id": source.id, "url": link, "title": title, "summary": summary, "channel": source.default_channel, "published_at": _parse_datetime(published), "entities": []})
    return articles


def parse_public_page(html_payload: str, source: Source, base_url: str | None = None) -> list[dict]:
    """Extract article cards from a public HTML page without executing page scripts."""

    soup = BeautifulSoup(html_payload, "html.parser")
    page_url = base_url or source.feed_url
    candidates = list(soup.select(source.article_selector)) if source.article_selector else list(soup.find_all("article"))
    if not candidates:
        main = soup.find("main") or soup
        candidates = list(main.find_all(["h1", "h2", "h3"], limit=30))
    articles: list[dict] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        heading = candidate.select_one(source.title_selector) if source.title_selector else None
        if heading is None:
            heading = candidate if getattr(candidate, "name", "") in {"h1", "h2", "h3", "h4", "h5", "h6"} else candidate.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        title = _text(heading)
        if not title or len(title) < 6:
            continue
        link_node = candidate.select_one(source.link_selector) if source.link_selector else None
        if link_node is None:
            link_node = (candidate.find("a", href=True) if getattr(candidate, "find", None) else None) or (heading.find_parent("a", href=True) if heading is not None else None)
        href = link_node.get("href", "") if link_node is not None else ""
        link = urljoin(page_url, href)
        if not href or not link.startswith(("http://", "https://")) or link in seen_urls:
            continue
        summary_node = candidate.select_one(source.summary_selector) if source.summary_selector else None
        if summary_node is None:
            summary_node = candidate.find("p") if getattr(candidate, "find", None) else None
        time_node = candidate.select_one(source.date_selector) if source.date_selector else None
        if time_node is None:
            time_node = candidate.find("time") if getattr(candidate, "find", None) else None
        published = ""
        if time_node is not None:
            published = time_node.get("datetime", "") or _text(time_node)
        if not published:
            published = _text(candidate.find(attrs={"class": lambda value: value and "date" in str(value).lower()})) if getattr(candidate, "find", None) else ""
        seen_urls.add(link)
        articles.append(
            {
                "source_id": source.id,
                "url": link,
                "title": title,
                "summary": _clean_summary(str(summary_node)) if summary_node is not None else "",
                "channel": source.default_channel,
                "published_at": _parse_datetime(published),
                "entities": [],
            }
        )
        if len(articles) >= 30:
            break
    return articles


def fetch_feed(source: Source, http_get: Callable[[str, float], tuple[int, str]] | None = None, timeout_seconds: float = 8.0, retries: int = 2, throttle_seconds: float = 0.0) -> FeedFetchResult:
    """Fetch a public RSS/Atom feed or HTML listing with bounded retries."""

    feed_url = validate_feed_url(getattr(source, "feed_url", ""))
    if throttle_seconds:
        time.sleep(min(throttle_seconds, 10.0))
    request = http_get or _default_http_get
    last_error = "unknown fetch error"
    for attempt in range(retries + 1):
        try:
            status, body = request(feed_url, timeout_seconds)
            if status < 200 or status >= 300:
                return FeedFetchResult(source.id, "failed", [], f"source returned HTTP {status}", status)
            parser = parse_public_page if getattr(source, "fetch_mode", "rss") == "html" or source.source_type in {"html", "webpage", "site"} else parse_feed
            articles = parser(body, source, feed_url) if parser is parse_public_page else parser(body, source)
            return FeedFetchResult(source.id, "success", articles, http_status=status)
        except (TimeoutError, OSError, ValueError) as exc:
            last_error = str(exc)
            if attempt < retries:
                continue
    return FeedFetchResult(source.id, "failed", [], last_error)


def _default_http_get(url: str, timeout: float) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "SignalScopeAI/0.1 (+public-news-radar)"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL is managed by an allow-listed source registry.
        payload = response.read(2_000_000)
        return int(response.status), payload.decode("utf-8", errors="replace")


def source_is_fetchable(source: Source) -> bool:
    """Allow configured public sources while respecting an explicit block."""

    return bool(source.active and getattr(source, "feed_url", "") and source.robots_status != "blocked" and source.compliance_status != "rejected")
