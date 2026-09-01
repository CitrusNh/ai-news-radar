from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock

from .models import Article, Enrichment, Event, Source, UserAction, UserPreference, ensure_utc, model_to_dict
from .store import InMemoryStore


class SQLiteStore(InMemoryStore):
    """SQLite-backed store using the same domain objects as the in-memory MVP."""

    def __init__(self, database_path: str | Path) -> None:
        super().__init__()
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.database_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._create_schema()
        self._load()

    def _create_schema(self) -> None:
        with self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS articles (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS preferences (anonymous_user_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY AUTOINCREMENT, anonymous_user_id TEXT NOT NULL, event_id TEXT NOT NULL, action_type TEXT NOT NULL, created_at TEXT NOT NULL);
                """
            )

    @staticmethod
    def _dt(value: str) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def _source(payload: dict) -> Source:
        return Source(**payload)

    @classmethod
    def _article(cls, payload: dict) -> Article:
        payload = dict(payload)
        payload["published_at"] = cls._dt(payload["published_at"])
        payload["fetched_at"] = cls._dt(payload["fetched_at"])
        return Article(**payload)

    @classmethod
    def _event(cls, payload: dict) -> Event:
        payload = dict(payload)
        payload["first_seen_at"] = cls._dt(payload["first_seen_at"])
        payload["last_seen_at"] = cls._dt(payload["last_seen_at"])
        enrichment = payload.get("enrichment")
        payload["enrichment"] = Enrichment(**enrichment) if enrichment else None
        return Event(**payload)

    def _load(self) -> None:
        with self._lock:
            self.sources = {row["id"]: self._source(json.loads(row["payload"])) for row in self._db.execute("SELECT id, payload FROM sources")}
            self.articles = {row["id"]: self._article(json.loads(row["payload"])) for row in self._db.execute("SELECT id, payload FROM articles")}
            self.events = {row["id"]: self._event(json.loads(row["payload"])) for row in self._db.execute("SELECT id, payload FROM events")}
            self.preferences = {}
            for row in self._db.execute("SELECT anonymous_user_id, payload FROM preferences"):
                self.preferences[row["anonymous_user_id"]] = UserPreference(**json.loads(row["payload"]))
            self.actions = [UserAction(row["anonymous_user_id"], row["event_id"], row["action_type"], self._dt(row["created_at"])) for row in self._db.execute("SELECT anonymous_user_id, event_id, action_type, created_at FROM actions ORDER BY id")]

    def _persist(self) -> None:
        with self._db:
            self._db.execute("DELETE FROM sources")
            self._db.executemany("INSERT INTO sources(id, payload) VALUES(?, ?)", [(item.id, json.dumps(model_to_dict(item), ensure_ascii=False)) for item in self.sources.values()])
            self._db.execute("DELETE FROM articles")
            self._db.executemany("INSERT INTO articles(id, payload) VALUES(?, ?)", [(item.id, json.dumps(model_to_dict(item), ensure_ascii=False)) for item in self.articles.values()])
            self._db.execute("DELETE FROM events")
            self._db.executemany("INSERT INTO events(id, payload) VALUES(?, ?)", [(item.id, json.dumps(model_to_dict(item), ensure_ascii=False)) for item in self.events.values()])
            self._db.execute("DELETE FROM preferences")
            self._db.executemany("INSERT INTO preferences(anonymous_user_id, payload) VALUES(?, ?)", [(item.anonymous_user_id, json.dumps(model_to_dict(item), ensure_ascii=False)) for item in self.preferences.values()])
            self._db.execute("DELETE FROM actions")
            self._db.executemany("INSERT INTO actions(anonymous_user_id, event_id, action_type, created_at) VALUES(?, ?, ?, ?)", [(item.anonymous_user_id, item.event_id, item.action_type, ensure_utc(item.created_at).isoformat()) for item in self.actions])

    def seed(self, sources: list[Source], raw_articles: list[dict]) -> None:
        super().seed(sources, raw_articles)
        self._persist()

    def get_preference(self, anonymous_user_id: str) -> UserPreference:
        preference = super().get_preference(anonymous_user_id)
        self._persist()
        return preference

    def set_preference(self, preference: UserPreference) -> UserPreference:
        value = super().set_preference(preference)
        self._persist()
        return value

    def add_action(self, action: UserAction) -> UserAction:
        value = super().add_action(action)
        self._persist()
        return value

    def close(self) -> None:
        self._db.close()


def persistent_demo_store(database_path: str | Path = "data/runtime/signalscope.db") -> SQLiteStore:
    store = SQLiteStore(database_path)
    if not store.events:
        demo = InMemoryStore()
        from .store import demo_store

        seeded = demo_store()
        store.sources = seeded.sources
        store.articles = seeded.articles
        store.events = seeded.events
        store._persist()
    return store
