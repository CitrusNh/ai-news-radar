from __future__ import annotations

from pathlib import Path

from .database_store import RelationalStore, persistent_store


class SQLiteStore(RelationalStore):
    """Backward-compatible SQLite wrapper for local development and tests."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(f"sqlite:///{self.database_path.resolve().as_posix()}")


def persistent_demo_store(database_path: str | Path = "data/runtime/signalscope.db", database_url: str | None = None) -> RelationalStore:
    return persistent_store(database_path, database_url)
