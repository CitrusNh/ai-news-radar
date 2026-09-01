from datetime import datetime, timezone

from backend.app.models import Source, UserAction, UserPreference
from backend.app.sqlite_store import SQLiteStore


def test_sqlite_store_persists_events_preferences_and_actions(tmp_path):
    db_path = tmp_path / "signalscope.db"
    first = SQLiteStore(db_path)
    source = Source("source-1", "测试来源", trust_tier=3)
    first.seed([source], [{"source_id": "source-1", "url": "https://example.com/story", "title": "持久化测试事件", "summary": "摘要", "channel": "模型与产品", "published_at": datetime.now(timezone.utc)}])
    event_id = next(iter(first.events))
    first.set_preference(UserPreference("persist-user", keywords=["测试"]))
    first.add_action(UserAction("persist-user", event_id, "saved"))
    first.close()

    second = SQLiteStore(db_path)
    assert event_id in second.events
    assert second.get_preference("persist-user").keywords == ["测试"]
    assert [event.id for event in second.library("persist-user")] == [event_id]
    second.close()


def test_sqlite_store_creates_parent_directory(tmp_path):
    store = SQLiteStore(tmp_path / "nested" / "store.db")
    assert (tmp_path / "nested" / "store.db").exists()
    store.close()
