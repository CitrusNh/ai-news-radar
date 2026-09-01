from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .models import Article, CrawlRun, Enrichment, Event, Source, UserAction, UserPreference, ensure_utc, model_to_dict
from .store import InMemoryStore, demo_store


SCHEMA_STATEMENTS = (
    "CREATE TABLE IF NOT EXISTS sources (id VARCHAR(255) PRIMARY KEY, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS articles (id VARCHAR(255) PRIMARY KEY, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS events (id VARCHAR(255) PRIMARY KEY, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS preferences (anonymous_user_id VARCHAR(255) PRIMARY KEY, payload TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS actions (id INTEGER PRIMARY KEY, anonymous_user_id VARCHAR(255) NOT NULL, event_id VARCHAR(255) NOT NULL, action_type VARCHAR(32) NOT NULL, created_at VARCHAR(64) NOT NULL)",
    "CREATE TABLE IF NOT EXISTS crawl_runs (id VARCHAR(255) PRIMARY KEY, payload TEXT NOT NULL)",
)


def normalize_database_url(database_url: str) -> str:
    """Use psycopg 3 for PostgreSQL URLs supplied by hosting platforms."""

    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


class RelationalStore(InMemoryStore):
    """Durable JSON-document store that works with SQLite and PostgreSQL."""

    def __init__(self, database_url: str, *, engine: Engine | None = None) -> None:
        super().__init__()
        self.database_url = normalize_database_url(database_url)
        connect_args = {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        self._engine = engine or create_engine(self.database_url, pool_pre_ping=True, connect_args=connect_args)
        self._create_schema()
        self._load()

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

    def _create_schema(self) -> None:
        with self._engine.begin() as connection:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(text(statement))

    def _rows(self, statement: str):
        with self._engine.connect() as connection:
            return list(connection.execute(text(statement)).mappings())

    def _load(self) -> None:
        with self._lock:
            self.sources = {row["id"]: self._source(json.loads(row["payload"])) for row in self._rows("SELECT id, payload FROM sources")}
            self.articles = {row["id"]: self._article(json.loads(row["payload"])) for row in self._rows("SELECT id, payload FROM articles")}
            self.events = {row["id"]: self._event(json.loads(row["payload"])) for row in self._rows("SELECT id, payload FROM events")}
            self.preferences = {
                row["anonymous_user_id"]: UserPreference(**json.loads(row["payload"]))
                for row in self._rows("SELECT anonymous_user_id, payload FROM preferences")
            }
            self.actions = [
                UserAction(row["anonymous_user_id"], row["event_id"], row["action_type"], self._dt(row["created_at"]))
                for row in self._rows("SELECT anonymous_user_id, event_id, action_type, created_at FROM actions ORDER BY id")
            ]
            self.runs = {}
            for row in self._rows("SELECT id, payload FROM crawl_runs"):
                payload = json.loads(row["payload"])
                payload["started_at"] = self._dt(payload["started_at"])
                payload["finished_at"] = self._dt(payload["finished_at"]) if payload.get("finished_at") else None
                self.runs[row["id"]] = CrawlRun(**payload)

    @staticmethod
    def _json(value) -> str:
        return json.dumps(model_to_dict(value), ensure_ascii=False)

    def _persist(self) -> None:
        with self._engine.begin() as connection:
            for table in ("sources", "articles", "events", "preferences", "actions", "crawl_runs"):
                connection.execute(text(f"DELETE FROM {table}"))
            connection.execute(
                text("INSERT INTO sources(id, payload) VALUES(:id, :payload)"),
                [{"id": item.id, "payload": self._json(item)} for item in self.sources.values()],
            ) if self.sources else None
            connection.execute(
                text("INSERT INTO articles(id, payload) VALUES(:id, :payload)"),
                [{"id": item.id, "payload": self._json(item)} for item in self.articles.values()],
            ) if self.articles else None
            connection.execute(
                text("INSERT INTO events(id, payload) VALUES(:id, :payload)"),
                [{"id": item.id, "payload": self._json(item)} for item in self.events.values()],
            ) if self.events else None
            connection.execute(
                text("INSERT INTO preferences(anonymous_user_id, payload) VALUES(:anonymous_user_id, :payload)"),
                [{"anonymous_user_id": item.anonymous_user_id, "payload": self._json(item)} for item in self.preferences.values()],
            ) if self.preferences else None
            connection.execute(
                text("INSERT INTO actions(id, anonymous_user_id, event_id, action_type, created_at) VALUES(:id, :anonymous_user_id, :event_id, :action_type, :created_at)"),
                [
                    {
                        "id": position,
                        "anonymous_user_id": item.anonymous_user_id,
                        "event_id": item.event_id,
                        "action_type": item.action_type,
                        "created_at": ensure_utc(item.created_at).isoformat(),
                    }
                    for position, item in enumerate(self.actions, start=1)
                ],
            ) if self.actions else None
            connection.execute(
                text("INSERT INTO crawl_runs(id, payload) VALUES(:id, :payload)"),
                [{"id": item.id, "payload": self._json(item)} for item in self.runs.values()],
            ) if self.runs else None

    def persist(self) -> None:
        self._persist()

    def seed(self, sources: list[Source], raw_articles: list[dict]) -> None:
        super().seed(sources, raw_articles)
        self.persist()

    def get_preference(self, anonymous_user_id: str) -> UserPreference:
        preference = super().get_preference(anonymous_user_id)
        self.persist()
        return preference

    def close(self) -> None:
        self._engine.dispose()


class PostgreSQLStore(RelationalStore):
    pass


def persistent_store(database_path: str | Path = "data/runtime/signalscope.db", database_url: str | None = None) -> RelationalStore:
    if database_url:
        store = PostgreSQLStore(database_url)
    else:
        path = Path(database_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        store = RelationalStore(f"sqlite:///{path.as_posix()}")
    if not store.events:
        seeded = demo_store()
        store.sources = seeded.sources
        store.articles = seeded.articles
        store.events = seeded.events
        store.persist()
    return store
