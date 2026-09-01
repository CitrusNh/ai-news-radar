from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from .database_store import normalize_database_url
from .models import Event, UserAction, ensure_utc
from .store import InMemoryStore


PUBLIC_DOMAINS = ("全部", "AI", "科技", "财经", "娱乐", "体育", "游戏")
PUBLIC_SORTS = {"综合热度": "heat", "最新发布": "fresh", "与你相关": "relevance"}


class PublicDatabaseConfigurationError(RuntimeError):
    """Raised when the public Streamlit deployment lacks durable PostgreSQL."""


def resolve_public_database_url(environment: Mapping[str, str], secrets: Mapping[str, object] | None = None) -> str:
    """Resolve a PostgreSQL-only URL without falling back to ephemeral SQLite."""

    secret_value = str((secrets or {}).get("DATABASE_URL", "")).strip()
    value = secret_value or str(environment.get("DATABASE_URL", "")).strip()
    if not value:
        raise PublicDatabaseConfigurationError("缺少 DATABASE_URL：公网版本必须连接 Neon PostgreSQL。")
    normalized = normalize_database_url(value)
    if not normalized.startswith("postgresql+psycopg://"):
        raise PublicDatabaseConfigurationError("DATABASE_URL 必须是 PostgreSQL 连接，公网版本不允许使用临时 SQLite。")
    return normalized


def list_public_events(
    store: InMemoryStore,
    anonymous_user_id: str,
    *,
    domain: str = "全部",
    keyword: str = "",
    sort: str = "heat",
    collection: str = "热点雷达",
) -> list[Event]:
    """Reuse the core ranking/search logic while supporting future domains."""

    selected_domains = sorted({event.domain for event in store.events.values()}) if domain == "全部" else [domain]
    events: list[Event] = []
    seen_ids: set[str] = set()
    for selected_domain in selected_domains:
        for event in store.list_events(anonymous_user_id, domain=selected_domain, keyword=keyword or None, sort=sort):
            if event.id not in seen_ids:
                seen_ids.add(event.id)
                events.append(event)

    if collection in {"我的收藏", "已读"}:
        action_type = "saved" if collection == "我的收藏" else "read"
        active_ids = {event.id for event in store.library(anonymous_user_id, action_type=action_type)}
        events = [event for event in events if event.id in active_ids]

    if sort == "fresh":
        return sorted(events, key=lambda item: ensure_utc(item.last_seen_at), reverse=True)
    if sort == "relevance":
        return sorted(events, key=lambda item: (item.personal_relevance, item.global_heat_score), reverse=True)
    return sorted(events, key=lambda item: (item.global_heat_score, item.personal_relevance), reverse=True)


def active_action_ids(store: InMemoryStore, anonymous_user_id: str, action_type: str) -> set[str]:
    return {event.id for event in store.library(anonymous_user_id, action_type=action_type)}


def toggle_action(store: InMemoryStore, anonymous_user_id: str, event_id: str, action_type: str) -> str:
    if action_type not in {"saved", "read"}:
        raise ValueError("only saved and read actions can be toggled")
    active_ids = active_action_ids(store, anonymous_user_id, action_type)
    next_action = {"saved": "unsaved", "read": "unread"}[action_type] if event_id in active_ids else action_type
    store.add_action(UserAction(anonymous_user_id, event_id, next_action))
    return next_action


def event_source_links(store: InMemoryStore, event: Event) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for article_id in event.article_ids:
        article = store.articles.get(article_id)
        if article and not article.duplicate_of:
            links.append((article.source_name, article.canonical_url))
    return links


def latest_update_at(store: InMemoryStore) -> datetime | None:
    return max((ensure_utc(event.last_seen_at) for event in store.events.values()), default=None)
