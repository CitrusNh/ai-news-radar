from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from .ingestion import FeedFetchResult, fetch_feed, source_is_fetchable
from .models import CrawlRun, Source
from .store import InMemoryStore


class IngestionWorkflow:
    def __init__(self, store: InMemoryStore, fetcher: Callable[[Source], FeedFetchResult] = fetch_feed) -> None:
        self.store = store
        self.fetcher = fetcher

    def run(self) -> CrawlRun:
        run = CrawlRun(id=f"run-{uuid4().hex[:10]}", started_at=datetime.now(timezone.utc))
        sources = [source for source in self.store.sources.values() if source_is_fetchable(source)]
        run.source_count = len(sources)
        raw_articles: list[dict] = []
        for source in sources:
            try:
                result = self.fetcher(source)
            except Exception as exc:  # A source failure must not abort the whole run.
                run.error_count += 1
                run.errors.append(f"{source.id}: {exc}")
                continue
            if result.status == "success":
                raw_articles.extend(result.articles)
            else:
                run.error_count += 1
                run.errors.append(f"{source.id}: {result.error or 'fetch failed'}")
        added = self.store.ingest_raw_articles(raw_articles) if raw_articles else []
        run.article_count = len(added)
        run.finished_at = datetime.now(timezone.utc)
        run.status = "completed_with_errors" if run.error_count else "completed"
        self.store.add_run(run)
        return run
