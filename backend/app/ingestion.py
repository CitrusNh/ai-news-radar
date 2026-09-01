from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

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
    return feed_url.strip()


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
            summary = _text(node.find("description"))
            published = _text(node.find("pubDate"))
            if title and link:
                articles.append({"source_id": source.id, "url": link, "title": title, "summary": summary, "channel": source.default_channel, "published_at": _parse_datetime(published), "entities": []})
    else:
        nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() == "entry"]
        for node in nodes:
            title = _text(next((child for child in node if child.tag.rsplit("}", 1)[-1].lower() == "title"), None))
            summary = _text(next((child for child in node if child.tag.rsplit("}", 1)[-1].lower() in {"summary", "content"}), None))
            published = _text(next((child for child in node if child.tag.rsplit("}", 1)[-1].lower() in {"published", "updated"}), None))
            links = [child.attrib.get("href", "") for child in node if child.tag.rsplit("}", 1)[-1].lower() == "link"]
            link = next((item for item in links if item), "")
            if title and link:
                articles.append({"source_id": source.id, "url": link, "title": title, "summary": summary, "channel": source.default_channel, "published_at": _parse_datetime(published), "entities": []})
    return articles


def fetch_feed(source: Source, http_get: Callable[[str, float], tuple[int, str]] | None = None, timeout_seconds: float = 8.0, retries: int = 2, throttle_seconds: float = 0.0) -> FeedFetchResult:
    """Fetch an approved RSS/Atom URL with bounded retries and no bypass behavior."""

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
            return FeedFetchResult(source.id, "success", parse_feed(body, source), http_status=status)
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
    """Conservative gate for sources; an explicit policy block always wins."""

    return bool(source.active and getattr(source, "feed_url", "") and getattr(source, "robots_status", "allowed") != "blocked")
