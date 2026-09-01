from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Callable
from uuid import uuid4

from .ingestion import FeedFetchResult, fetch_feed, source_is_fetchable
from .models import CrawlRun, Source, ensure_utc
from .store import InMemoryStore


class IngestionCooldownError(RuntimeError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__(f"news update is cooling down for {self.retry_after_seconds} seconds")


class IngestionWorkflow:
    def __init__(self, store: InMemoryStore, fetcher: Callable[[Source], FeedFetchResult] = fetch_feed, max_workers: int = 6, max_age_days: int = 7) -> None:
        self.store = store
        self.fetcher = fetcher
        self.max_workers = max(1, max_workers)
        self.max_age_days = max(1, max_age_days)

    def _fetch_source(self, source: Source) -> FeedFetchResult:
        try:
            return self.fetcher(source)
        except Exception as exc:  # A source failure must not abort the whole run.
            return FeedFetchResult(source.id, "failed", [], str(exc))

    def run(
        self,
        *,
        cooldown_seconds: int = 0,
        configure_sources: Callable[[], object] | None = None,
        purge_source_ids: frozenset[str] = frozenset(),
    ) -> CrawlRun:
        with self.store.ingestion_guard():
            self.store.reload_for_ingestion()
            now = datetime.now(timezone.utc)
            completed_runs = [
                item for item in self.store.runs.values() if item.status in {"completed", "completed_with_errors"}
            ]
            if cooldown_seconds and completed_runs:
                latest = max(completed_runs, key=lambda item: item.started_at)
                retry_at = latest.started_at + timedelta(seconds=cooldown_seconds)
                if retry_at > now:
                    raise IngestionCooldownError(ceil((retry_at - now).total_seconds()))
            if configure_sources:
                configure_sources()

            run = CrawlRun(id=f"run-{uuid4().hex[:10]}", started_at=now)
            self.store.add_run(run)
            try:
                sources = [source for source in self.store.sources.values() if source_is_fetchable(source)]
                run.source_count = len(sources)
                raw_articles: list[dict] = []
                if sources:
                    workers = min(self.max_workers, len(sources))
                    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="news-fetch") as executor:
                        results = list(executor.map(self._fetch_source, sources))
                    cutoff = now - timedelta(days=self.max_age_days)
                    for result in results:
                        if result.status == "success":
                            raw_articles.extend(
                                article
                                for article in result.articles
                                if ensure_utc(article["published_at"]) >= cutoff
                            )
                        else:
                            run.error_count += 1
                            run.errors.append(f"{result.source_id}: {result.error or 'fetch failed'}")
                added = self.store.ingest_raw_articles(raw_articles) if raw_articles else []
                run.article_count = len(added)
                if added and purge_source_ids:
                    self.store.purge_sources(purge_source_ids)
                run.finished_at = datetime.now(timezone.utc)
                run.status = "failed" if run.error_count and run.error_count >= max(1, run.source_count) else ("completed_with_errors" if run.error_count else "completed")
                self.store.add_run(run)
                return run
            except Exception:
                run.finished_at = datetime.now(timezone.utc)
                run.status = "failed"
                run.error_count = max(1, run.error_count)
                run.errors.append("internal ingestion failure")
                self.store.add_run(run)
                raise


def run_ingestion_once(store: InMemoryStore) -> CrawlRun:
    """Small entry point shared by the API, scheduler and GitHub Actions."""

    return IngestionWorkflow(store).run()


def run_public_news_update(
    store: InMemoryStore,
    *,
    cooldown_seconds: int = 0,
    fetcher: Callable[[Source], FeedFetchResult] = fetch_feed,
) -> CrawlRun:
    """Run the shared six-domain public catalog and retire demo content on success."""

    from .source_catalog import DEMO_SOURCE_IDS, ensure_public_sources

    return IngestionWorkflow(store, fetcher=fetcher).run(
        cooldown_seconds=cooldown_seconds,
        configure_sources=lambda: ensure_public_sources(store),
        purge_source_ids=DEMO_SOURCE_IDS,
    )
