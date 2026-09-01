from __future__ import annotations

import os

from backend.app.database_store import persistent_store
from backend.app.workflow import run_public_news_update


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required for a durable news update")
    store = persistent_store(database_url=database_url)
    run = run_public_news_update(store)
    print(
        f"status={run.status} sources={run.source_count} articles={run.article_count} "
        f"errors={run.error_count} run_id={run.id}"
    )
    store.close()
    return 0 if run.status in {"completed", "completed_with_errors"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
