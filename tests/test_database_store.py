from datetime import datetime, timezone

from backend.app.database_store import RelationalStore, normalize_database_url, persistent_store
from backend.app.models import CrawlRun, Source, UserAction, UserPreference


def test_normalize_database_url_selects_psycopg_driver():
    assert normalize_database_url("postgres://user:pass@db.example/app") == "postgresql+psycopg://user:pass@db.example/app"
    assert normalize_database_url("postgresql://user:pass@db.example/app") == "postgresql+psycopg://user:pass@db.example/app"
    assert normalize_database_url("sqlite:///local.db") == "sqlite:///local.db"


def test_relational_store_persists_all_server_state(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'portable.db').as_posix()}"
    first = RelationalStore(database_url)
    first.seed(
        [Source("source-1", "测试来源", trust_tier=3)],
        [{"source_id": "source-1", "url": "https://example.com/story", "title": "关系数据库持久化", "summary": "摘要", "channel": "模型与产品", "published_at": datetime.now(timezone.utc)}],
    )
    event_id = next(iter(first.events))
    first.set_preference(UserPreference("portable-user", keywords=["关系数据库"]))
    first.add_action(UserAction("portable-user", event_id, "saved"))
    first.add_run(CrawlRun("run-portable", datetime.now(timezone.utc), status="completed"))
    first.close()

    second = RelationalStore(database_url)
    assert event_id in second.events
    assert second.get_preference("portable-user").keywords == ["关系数据库"]
    assert [event.id for event in second.library("portable-user")] == [event_id]
    assert second.runs["run-portable"].status == "completed"
    second.close()


def test_relational_store_shares_user_state_without_rewriting_catalog(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'shared-users.db').as_posix()}"
    first = RelationalStore(database_url)
    first.seed(
        [Source("source-1", "测试来源", trust_tier=3)],
        [{"source_id": "source-1", "url": "https://example.com/story", "title": "共享用户状态", "summary": "摘要", "channel": "模型与产品", "published_at": datetime.now(timezone.utc)}],
    )
    second = RelationalStore(database_url)
    event_id = next(iter(first.events))

    first.add_action(UserAction("shared-user", event_id, "saved"))
    assert [event.id for event in second.library("shared-user")] == [event_id]

    second.set_preference(UserPreference("shared-user", keywords=["跨实例可见"]))
    second.upsert_source(Source("source-2", "并发新增来源", feed_url="https://example.com/feed"))
    second.add_action(UserAction("second-user", event_id, "read"))
    first.add_run(CrawlRun("run-after-actions", datetime.now(timezone.utc), status="completed"))
    assert first.get_preference("shared-user").keywords == ["跨实例可见"]
    assert [event.id for event in first.library("second-user", action_type="read")] == [event_id]
    assert event_id in first.events
    assert event_id in second.events
    first.reload()
    assert "source-2" in first.sources
    first.close()
    second.close()


def test_relational_store_appends_multiple_actions_with_generated_ids(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'action-ids.db').as_posix()}"
    store = RelationalStore(database_url)
    store.seed(
        [Source("source-1", "测试来源", trust_tier=3)],
        [{"source_id": "source-1", "url": "https://example.com/story", "title": "动作编号", "summary": "摘要", "channel": "模型与产品", "published_at": datetime.now(timezone.utc)}],
    )
    event_id = next(iter(store.events))

    store.add_action(UserAction("action-user", event_id, "saved"))
    store.add_action(UserAction("action-user", event_id, "unsaved"))
    store.add_action(UserAction("action-user", event_id, "read"))

    assert store.library("action-user", action_type="saved") == []
    assert [event.id for event in store.library("action-user", action_type="read")] == [event_id]
    store.close()


def test_persistent_store_uses_sqlite_locally_and_seeds_demo(tmp_path):
    store = persistent_store(tmp_path / "runtime" / "signalscope.db")
    assert len(store.events) == 12
    assert store.database_url.startswith("sqlite:///")
    store.reload()
    assert len(store.events) == 12
    store.close()


def test_database_url_store_starts_empty_without_demo_seed(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'public.db').as_posix()}"
    store = persistent_store(database_url=database_url)
    assert store.events == {}
    store.close()


def test_purge_sources_removes_durable_articles_and_events(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'purge.db').as_posix()}"
    store = RelationalStore(database_url)
    store.seed(
        [Source("demo", "演示"), Source("real", "真实")],
        [
            {"source_id": "demo", "url": "https://example.com/demo", "title": "演示新闻内容", "summary": "摘要", "channel": "AI", "published_at": datetime.now(timezone.utc)},
            {"source_id": "real", "url": "https://example.com/real", "title": "真实新闻内容", "summary": "摘要", "channel": "AI", "published_at": datetime.now(timezone.utc)},
        ],
    )
    assert store.purge_sources({"demo"}) == 1
    store.close()

    reopened = RelationalStore(database_url)
    assert "demo" not in reopened.sources
    assert {article.source_id for article in reopened.articles.values()} == {"real"}
    assert all(event.title == "真实新闻内容" for event in reopened.events.values())
    reopened.close()
