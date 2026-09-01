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
            if self._engine.dialect.name == "postgresql":
                connection.execute(text("CREATE SEQUENCE IF NOT EXISTS actions_id_seq"))
                connection.execute(text("ALTER SEQUENCE actions_id_seq OWNED BY actions.id"))
                connection.execute(text("ALTER TABLE actions ALTER COLUMN id SET DEFAULT nextval('actions_id_seq')"))
                connection.execute(
                    text(
                        "SELECT setval('actions_id_seq', "
                        "COALESCE((SELECT MAX(id) FROM actions), 0) + 1, false)"
                    )
                )

    def _rows(self, statement: str, parameters: dict | None = None):
        with self._engine.connect() as connection:
            return list(connection.execute(text(statement), parameters or {}).mappings())

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
            for table in ("sources", "articles", "events", "crawl_runs"):
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
                text("INSERT INTO crawl_runs(id, payload) VALUES(:id, :payload)"),
                [{"id": item.id, "payload": self._json(item)} for item in self.runs.values()],
            ) if self.runs else None

    def persist(self) -> None:
        self._persist()

    def seed(self, sources: list[Source], raw_articles: list[dict]) -> None:
        super().seed(sources, raw_articles)
        self.persist()

    def get_preference(self, anonymous_user_id: str) -> UserPreference:
        with self._lock:
            rows = self._rows(
                "SELECT payload FROM preferences WHERE anonymous_user_id = :anonymous_user_id",
                {"anonymous_user_id": anonymous_user_id},
            )
            if rows:
                preference = UserPreference(**json.loads(rows[0]["payload"]))
            else:
                preference = UserPreference(anonymous_user_id=anonymous_user_id)
                self._persist_preference(preference)
            self.preferences[anonymous_user_id] = preference
            return preference

    def _persist_preference(self, preference: UserPreference) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO preferences(anonymous_user_id, payload) "
                    "VALUES(:anonymous_user_id, :payload) "
                    "ON CONFLICT(anonymous_user_id) DO UPDATE SET payload = excluded.payload"
                ),
                {"anonymous_user_id": preference.anonymous_user_id, "payload": self._json(preference)},
            )

    def set_preference(self, preference: UserPreference) -> UserPreference:
        with self._lock:
            self._persist_preference(preference)
            self.preferences[preference.anonymous_user_id] = preference
            return preference

    def add_action(self, action: UserAction) -> UserAction:
        with self._lock:
            with self._engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO actions(anonymous_user_id, event_id, action_type, created_at) "
                        "VALUES(:anonymous_user_id, :event_id, :action_type, :created_at)"
                    ),
                    {
                        "anonymous_user_id": action.anonymous_user_id,
                        "event_id": action.event_id,
                        "action_type": action.action_type,
                        "created_at": ensure_utc(action.created_at).isoformat(),
                    },
                )
            self.actions.append(action)
            return action

    def library(self, anonymous_user_id: str, action_type: str = "saved") -> list[Event]:
        with self._lock:
            rows = self._rows(
                "SELECT anonymous_user_id, event_id, action_type, created_at "
                "FROM actions WHERE anonymous_user_id = :anonymous_user_id ORDER BY id",
                {"anonymous_user_id": anonymous_user_id},
            )
            user_actions = [
                UserAction(row["anonymous_user_id"], row["event_id"], row["action_type"], self._dt(row["created_at"]))
                for row in rows
            ]
            self.actions = [item for item in self.actions if item.anonymous_user_id != anonymous_user_id] + user_actions
            return super().library(anonymous_user_id, action_type=action_type)

    def close(self) -> None:
        self._engine.dispose()

    def reload(self) -> None:
        """Reload durable state after an explicit public-page refresh."""

        self._load()


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
