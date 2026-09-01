from datetime import datetime, timezone

import pytest

from backend.app.models import Source
from backend.app.store import InMemoryStore, demo_store
from backend.app.streamlit_service import (
    PublicDatabaseConfigurationError,
    active_action_ids,
    event_source_links,
    latest_update_at,
    list_public_events,
    resolve_public_database_url,
    toggle_action,
)


def test_public_database_url_requires_postgresql_and_prefers_secrets():
    with pytest.raises(PublicDatabaseConfigurationError, match="缺少 DATABASE_URL"):
        resolve_public_database_url({})
    with pytest.raises(PublicDatabaseConfigurationError, match="不允许使用临时 SQLite"):
        resolve_public_database_url({"DATABASE_URL": "sqlite:///temporary.db"})
    assert resolve_public_database_url({"DATABASE_URL": "postgres://env/db"}, {"DATABASE_URL": "postgresql://secret/db"}) == "postgresql+psycopg://secret/db"


def test_streamlit_event_query_supports_categories_search_and_collections():
    store = demo_store()
    user_id = "web-test-user"
    all_events = list_public_events(store, user_id)
    assert len(all_events) == 12
    assert list_public_events(store, user_id, domain="科技") == []
    search_results = list_public_events(store, user_id, keyword="OpenAI")
    assert [event.title for event in search_results] == ["OpenAI 发布新一代推理模型"]

    event_id = all_events[0].id
    assert toggle_action(store, user_id, event_id, "saved") == "saved"
    assert event_id in active_action_ids(store, user_id, "saved")
    assert [event.id for event in list_public_events(store, user_id, collection="我的收藏")] == [event_id]
    assert toggle_action(store, user_id, event_id, "saved") == "unsaved"
    assert list_public_events(store, user_id, collection="我的收藏") == []


def test_streamlit_detail_sources_and_update_status_reuse_store_data():
    store = InMemoryStore()
    published_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    store.seed(
        [Source("official", "Official", trust_tier=3)],
        [{"source_id": "official", "url": "https://example.com/news", "title": "测试新闻", "summary": "摘要", "channel": "科技", "published_at": published_at}],
    )
    event = next(iter(store.events.values()))
    assert event_source_links(store, event) == [("Official", "https://example.com/news")]
    assert latest_update_at(store) == published_at
    with pytest.raises(ValueError, match="saved and read"):
        toggle_action(store, "web-test-user", event.id, "shared")
