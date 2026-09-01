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


def test_persistent_store_uses_sqlite_locally_and_seeds_demo(tmp_path):
    store = persistent_store(tmp_path / "runtime" / "signalscope.db")
    assert len(store.events) == 12
    assert store.database_url.startswith("sqlite:///")
    store.reload()
    assert len(store.events) == 12
    store.close()
