from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Source:
    id: str
    name: str
    domain: str = "AI"
    source_type: str = "official"
    trust_tier: int = 2
    active: bool = True
    feed_url: str = ""
    terms_url: str = ""
    robots_status: str = "unknown"


@dataclass(slots=True)
class Article:
    id: str
    source_id: str
    source_name: str
    domain: str
    channel: str
    canonical_url: str
    title: str
    source_summary: str
    published_at: datetime
    fetched_at: datetime = field(default_factory=utc_now)
    language: str = "zh-CN"
    title_hash: str = ""
    content_hash: str = ""
    status: str = "fetched"
    duplicate_of: str | None = None
    entities: list[str] = field(default_factory=list)
    event_id: str | None = None


@dataclass(slots=True)
class Enrichment:
    event_id: str
    summary: str
    key_facts: list[str]
    entities: list[dict[str, str]]
    topic_labels: list[str]
    why_it_matters: str
    uncertainty_level: str = "medium"
    needs_review: bool = False
    model_name: str = "rule-based-demo"
    prompt_version: str = "v0"


@dataclass(slots=True)
class Event:
    id: str
    domain: str
    channel: str
    title: str
    article_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    first_seen_at: datetime = field(default_factory=utc_now)
    last_seen_at: datetime = field(default_factory=utc_now)
    global_heat_score: float = 0.0
    personal_relevance: float = 0.0
    impact_level: str = "medium"
    uncertainty_level: str = "medium"
    status: str = "draft"
    enrichment: Enrichment | None = None


@dataclass(slots=True)
class UserPreference:
    anonymous_user_id: str
    domains: list[str] = field(default_factory=lambda: ["AI"])
    channels: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    muted_sources: list[str] = field(default_factory=list)
    language: str = "zh-CN"


@dataclass(slots=True)
class UserAction:
    anonymous_user_id: str
    event_id: str
    action_type: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CrawlRun:
    id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    source_count: int = 0
    article_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)


def ensure_utc(value: datetime) -> datetime:
    """Return an aware UTC datetime for stable comparisons and serialization."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def model_to_dict(value: Any) -> dict[str, Any]:
    """Small dataclass serializer used by the API layer and tests."""

    if hasattr(value, "__dataclass_fields__"):
        result: dict[str, Any] = {}
        for name in value.__dataclass_fields__:  # type: ignore[attr-defined]
            field_value = getattr(value, name)
            if isinstance(field_value, datetime):
                result[name] = ensure_utc(field_value).isoformat()
            elif isinstance(field_value, list):
                result[name] = [model_to_dict(item) if hasattr(item, "__dataclass_fields__") else item for item in field_value]
            elif hasattr(field_value, "__dataclass_fields__"):
                result[name] = model_to_dict(field_value)
            else:
                result[name] = field_value
        return result
    raise TypeError(f"Unsupported model: {type(value)!r}")
