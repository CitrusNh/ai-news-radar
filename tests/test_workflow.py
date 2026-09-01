from datetime import datetime, timezone

from backend.app.ingestion import FeedFetchResult
from backend.app.models import Source
from backend.app.store import InMemoryStore
from backend.app.workflow import IngestionWorkflow


def test_workflow_ingests_successful_sources_and_isolates_failures():
    store = InMemoryStore()
    store.sources = {
        "ok": Source("ok", "成功来源", feed_url="https://example.com/ok", robots_status="allowed", default_channel="模型与产品", compliance_status="approved"),
        "bad": Source("bad", "失败来源", feed_url="https://example.com/bad", robots_status="allowed", compliance_status="approved"),
        "blocked": Source("blocked", "禁止来源", feed_url="https://example.com/blocked", robots_status="blocked", compliance_status="approved"),
    }

    def fetcher(source):
        if source.id == "bad":
            return FeedFetchResult(source.id, "failed", [], "timeout")
        return FeedFetchResult(source.id, "success", [{"source_id": source.id, "url": "https://example.com/new", "title": "新的 AI 事件", "summary": "摘要", "channel": source.default_channel, "published_at": datetime.now(timezone.utc), "entities": []}])

    run = IngestionWorkflow(store, fetcher=fetcher).run()
    assert run.source_count == 2
    assert run.article_count == 1
    assert run.error_count == 1
    assert run.status == "completed_with_errors"
    assert len(store.events) == 1
    assert run.id in store.runs


def test_workflow_is_idempotent_for_existing_urls():
    store = InMemoryStore()
    source = Source("ok", "来源", feed_url="https://example.com/feed", robots_status="allowed", default_channel="模型与产品", compliance_status="approved")
    store.sources[source.id] = source
    item = {"source_id": source.id, "url": "https://example.com/same", "title": "相同事件", "summary": "摘要", "channel": source.default_channel, "published_at": datetime.now(timezone.utc), "entities": []}
    fetcher = lambda current: FeedFetchResult(current.id, "success", [item])
    assert IngestionWorkflow(store, fetcher).run().article_count == 1
    assert IngestionWorkflow(store, fetcher).run().article_count == 0
    assert len(store.articles) == 1


def test_incremental_workflow_preserves_existing_event_ids():
    store = InMemoryStore()
    source = Source("ok", "来源", feed_url="https://example.com/feed", robots_status="allowed", default_channel="模型与产品", compliance_status="approved")
    store.sources[source.id] = source
    first_item = {"source_id": source.id, "url": "https://example.com/first", "title": "OpenAI 推理模型发布", "summary": "摘要", "channel": source.default_channel, "published_at": datetime.now(timezone.utc), "entities": ["OpenAI", "推理模型"]}
    second_item = {"source_id": source.id, "url": "https://example.com/second", "title": "OpenAI 发布推理模型更新", "summary": "补充", "channel": source.default_channel, "published_at": datetime.now(timezone.utc), "entities": ["OpenAI", "推理模型"]}
    IngestionWorkflow(store, lambda current: FeedFetchResult(current.id, "success", [first_item])).run()
    original_event_id = next(iter(store.events))
    IngestionWorkflow(store, lambda current: FeedFetchResult(current.id, "success", [first_item, second_item])).run()
    assert original_event_id in store.events
    assert len(store.events[original_event_id].article_ids) == 2
