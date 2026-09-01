from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Article, Enrichment, Event, Source, UserPreference, ensure_utc


TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}
TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[\u4e00-\u9fff]")
ALLOWED_ACTIONS = {"viewed", "saved", "unsaved", "read", "unread", "not_interested", "clicked_source", "shared"}


def clean_text(value: str | None, max_length: int | None = None) -> str:
    text = re.sub(r"\s+", " ", (value or "")).strip()
    if max_length is not None:
        return text[:max_length]
    return text


def canonicalize_url(url: str) -> str:
    """Normalize a source URL without fetching it or retaining tracking parameters."""

    if not url or not url.strip():
        raise ValueError("article URL is required")
    parsed = urlsplit(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("article URL must be an absolute http(s) URL")
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() not in TRACKING_PARAMS]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, urlencode(query), ""))


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(clean_text(text)) if len(token) > 1 or "\u4e00" <= token <= "\u9fff"}


def stable_hash(*parts: str) -> str:
    payload = "\x1f".join(clean_text(part).lower() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_article(raw: dict, source: Source, article_id: str, fetched_at: datetime | None = None) -> Article:
    """Convert an RSS/API-like dictionary into a validated internal article."""

    title = clean_text(raw.get("title"), max_length=300)
    if not title:
        raise ValueError("article title is required")
    summary = clean_text(raw.get("summary") or raw.get("description"), max_length=1000)
    published_at = raw.get("published_at")
    if not isinstance(published_at, datetime):
        raise ValueError("published_at must be a datetime")
    published_at = ensure_utc(published_at)
    url = canonicalize_url(str(raw.get("url", "")))
    entities = [clean_text(str(item), max_length=80) for item in raw.get("entities", []) if clean_text(str(item))]
    return Article(
        id=article_id,
        source_id=source.id,
        source_name=source.name,
        domain=source.domain,
        channel=clean_text(raw.get("channel") or "未分类", max_length=40),
        canonical_url=url,
        title=title,
        source_summary=summary,
        published_at=published_at,
        fetched_at=ensure_utc(fetched_at or datetime.now(timezone.utc)),
        language=clean_text(raw.get("language") or "zh-CN", max_length=20),
        title_hash=stable_hash(title),
        content_hash=stable_hash(title, summary),
        entities=entities,
        status="normalized",
    )


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def article_similarity(left: Article, right: Article) -> float:
    title_score = jaccard_similarity(tokenize(left.title), tokenize(right.title))
    entity_score = jaccard_similarity(set(left.entities), set(right.entities)) if left.entities and right.entities else 0.0
    channel_bonus = 0.1 if left.channel == right.channel else 0.0
    return min(1.0, title_score * 0.7 + entity_score * 0.2 + channel_bonus)


def deduplicate_articles(articles: Sequence[Article]) -> list[Article]:
    """Mark duplicates while preserving every original article for auditability."""

    unique_by_url: dict[str, Article] = {}
    result: list[Article] = []
    for article in sorted(articles, key=lambda item: ensure_utc(item.published_at)):
        previous = unique_by_url.get(article.canonical_url)
        if previous:
            article.duplicate_of = previous.id
            article.status = "deduplicated"
            result.append(article)
            continue
        unique_by_url[article.canonical_url] = article
        article.status = "deduplicated"
        result.append(article)
    return result


def _same_event(left: Article, right: Article, window_hours: int, threshold: float) -> bool:
    if left.domain != right.domain or left.channel != right.channel:
        return False
    delta = abs(ensure_utc(left.published_at) - ensure_utc(right.published_at))
    return delta <= timedelta(hours=window_hours) and article_similarity(left, right) >= threshold


def cluster_events(articles: Sequence[Article], event_prefix: str = "evt", threshold: float = 0.42, window_hours: int = 48) -> list[Event]:
    events: list[Event] = []
    active_articles = [article for article in articles if not article.duplicate_of]
    for article in sorted(active_articles, key=lambda item: ensure_utc(item.published_at)):
        matching: Event | None = None
        best_score = 0.0
        for event in events:
            representative = next((item for item in active_articles if item.id == event.article_ids[0]), None)
            if representative is None:
                continue
            score = article_similarity(article, representative)
            if _same_event(article, representative, window_hours, threshold) and score > best_score:
                matching, best_score = event, score
        if matching is None:
            matching = Event(
                id=f"{event_prefix}-{len(events) + 1:04d}",
                domain=article.domain,
                channel=article.channel,
                title=article.title,
                first_seen_at=article.published_at,
                last_seen_at=article.published_at,
            )
            events.append(matching)
        matching.article_ids.append(article.id)
        if article.source_id not in matching.source_ids:
            matching.source_ids.append(article.source_id)
        matching.first_seen_at = min(ensure_utc(matching.first_seen_at), ensure_utc(article.published_at))
        matching.last_seen_at = max(ensure_utc(matching.last_seen_at), ensure_utc(article.published_at))
        article.event_id = matching.id
        article.status = "clustered"
    return events


def freshness_score(published_at: datetime, now: datetime | None = None, half_life_hours: float = 24.0) -> float:
    current = ensure_utc(now or datetime.now(timezone.utc))
    age_hours = max(0.0, (current - ensure_utc(published_at)).total_seconds() / 3600)
    return max(0.0, min(100.0, 100.0 * math.exp(-math.log(2) * age_hours / half_life_hours)))


def calculate_global_heat(event: Event, articles_by_id: dict[str, Article], sources_by_id: dict[str, Source], now: datetime | None = None) -> float:
    articles = [articles_by_id[item_id] for item_id in event.article_ids if item_id in articles_by_id]
    source_trust = sum(sources_by_id[item.source_id].trust_tier for item in articles if item.source_id in sources_by_id) / max(1, len(articles))
    freshness = freshness_score(event.last_seen_at, now)
    source_count = min(100.0, len(event.source_ids) / 5 * 100)
    trust = min(100.0, source_trust / 3 * 100)
    novelty = 100.0 if len(event.article_ids) == 1 else 75.0
    impact = 70.0 if event.channel in {"政策安全", "企业应用"} else 62.0
    agreement = min(100.0, 60.0 + len(event.source_ids) * 10)
    score = 0.25 * freshness + 0.20 * source_count + 0.20 * trust + 0.15 * impact + 0.10 * novelty + 0.10 * agreement
    event.global_heat_score = round(score, 2)
    return event.global_heat_score


def calculate_personal_relevance(event: Event, articles_by_id: dict[str, Article], preference: UserPreference) -> float:
    articles = [articles_by_id[item_id] for item_id in event.article_ids if item_id in articles_by_id]
    haystack = " ".join([event.title, event.channel, *[article.title for article in articles], *[entity for article in articles for entity in article.entities]]).lower()
    score = 0.0
    if event.domain in preference.domains or not preference.domains:
        score += 35
    if event.channel in preference.channels:
        score += 25
    score += min(25.0, sum(8 for keyword in preference.keywords if keyword.lower() in haystack))
    score += min(15.0, sum(5 for entity in preference.entities if entity.lower() in haystack))
    event.personal_relevance = round(min(100.0, score), 2)
    return event.personal_relevance


def rank_events(events: Iterable[Event], articles_by_id: dict[str, Article], preference: UserPreference, sort: str = "heat") -> list[Event]:
    visible = [event for event in events if event.domain in preference.domains and not any(source_id in preference.muted_sources for source_id in event.source_ids)]
    for event in visible:
        calculate_personal_relevance(event, articles_by_id, preference)
    if sort == "fresh":
        return sorted(visible, key=lambda item: ensure_utc(item.last_seen_at), reverse=True)
    if sort == "relevance":
        return sorted(visible, key=lambda item: (item.personal_relevance, item.global_heat_score), reverse=True)
    return sorted(visible, key=lambda item: (item.global_heat_score, item.personal_relevance), reverse=True)


def build_demo_enrichment(event: Event, articles_by_id: dict[str, Article]) -> Enrichment:
    """Deterministic enrichment used until an LLM adapter is configured."""

    articles = [articles_by_id[item_id] for item_id in event.article_ids if item_id in articles_by_id]
    primary = articles[0]
    summary = primary.source_summary or primary.title
    facts = [article.title for article in articles[:3]]
    entities = [{"name": entity, "type": "entity"} for entity in primary.entities[:6]]
    enrichment = Enrichment(
        event_id=event.id,
        summary=summary[:120],
        key_facts=facts,
        entities=entities,
        topic_labels=[event.domain, event.channel],
        why_it_matters=f"该事件来自 {len(event.source_ids)} 个来源，建议查看原文核实。",
        uncertainty_level="medium" if len(event.source_ids) < 3 else "low",
        needs_review=len(event.source_ids) < 2,
    )
    event.enrichment = enrichment
    event.uncertainty_level = enrichment.uncertainty_level
    event.status = "published"
    return enrichment
