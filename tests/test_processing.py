from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.models import Source, UserPreference
from backend.app.processing import (
    article_similarity,
    calculate_global_heat,
    canonicalize_url,
    cluster_events,
    deduplicate_articles,
    normalize_article,
    rank_events,
)


def raw(source_id: str, url: str, title: str, channel: str = "模型与产品", minutes_ago: int = 0):
    return {
        "source_id": source_id,
        "url": url,
        "title": title,
        "summary": f"关于 {title} 的公开信息摘要。",
        "channel": channel,
        "published_at": datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        "entities": ["OpenAI", "推理模型"] if "推理" in title else [],
    }


def article(source: Source, index: int, **kwargs):
    return normalize_article(raw(source.id, f"https://example.com/news/{index}", **kwargs), source, f"art-{index}")


def test_canonicalize_url_removes_tracking_params_and_trailing_slash():
    assert canonicalize_url("HTTPS://Example.com/a/?utm_source=x&b=2#fragment") == "https://example.com/a?b=2"


def test_normalize_article_rejects_missing_title_and_invalid_url():
    source = Source("s1", "Source")
    with pytest.raises(ValueError, match="title"):
        normalize_article({"url": "https://example.com/a", "published_at": datetime.now(timezone.utc)}, source, "a1")
    with pytest.raises(ValueError, match="absolute"):
        normalize_article({"url": "/relative", "title": "A", "published_at": datetime.now(timezone.utc)}, source, "a1")


def test_deduplicate_articles_marks_same_canonical_url_without_deleting_audit_record():
    source = Source("s1", "Source")
    first = normalize_article(raw("s1", "https://example.com/a?utm_source=x", "同一事件"), source, "a1")
    second = normalize_article(raw("s1", "https://example.com/a", "同一事件更新"), source, "a2")
    result = deduplicate_articles([first, second])
    assert len(result) == 2
    assert result[1].duplicate_of == "a1"
    assert result[1].status == "deduplicated"


def test_cluster_events_groups_similar_articles_but_keeps_different_channel_separate():
    source = Source("s1", "Source")
    first = article(source, 1, title="OpenAI 发布推理模型", channel="模型与产品", minutes_ago=20)
    second = article(source, 2, title="OpenAI 推理模型正式发布", channel="模型与产品", minutes_ago=5)
    different = article(source, 3, title="OpenAI 发布推理模型安全政策", channel="政策安全", minutes_ago=5)
    events = cluster_events([first, second, different], threshold=0.25)
    assert len(events) == 2
    assert sorted(len(event.article_ids) for event in events) == [1, 2]


def test_article_similarity_is_symmetric_and_bounded():
    source = Source("s1", "Source")
    left = article(source, 1, title="推理模型上线")
    right = article(source, 2, title="推理模型发布")
    assert article_similarity(left, right) == article_similarity(right, left)
    assert 0 <= article_similarity(left, right) <= 1


def test_heat_score_increases_with_more_sources():
    source_a = Source("a", "A", trust_tier=2)
    source_b = Source("b", "B", trust_tier=3)
    first = article(source_a, 1, title="单一来源事件")
    second = article(source_b, 2, title="单一来源事件补充")
    events = cluster_events([first, second], threshold=0.05)
    articles = {item.id: item for item in [first, second]}
    sources = {source.id: source for source in [source_a, source_b]}
    one_source = deepcopy(events[0])
    one_source.article_ids = [first.id]
    one_source.source_ids = [source_a.id]
    two_sources = deepcopy(events[0])
    two_sources.article_ids = [first.id, second.id]
    two_sources.source_ids = [source_a.id, source_b.id]
    assert calculate_global_heat(two_sources, articles, sources) > calculate_global_heat(one_source, articles, sources)


def test_rank_events_applies_domain_channel_keyword_and_muted_source_preferences():
    source = Source("s1", "Source")
    first = article(source, 1, title="推理模型发布", channel="模型与产品")
    second = article(source, 2, title="企业 AI 采购", channel="企业应用")
    events = cluster_events([first, second])
    articles = {item.id: item for item in [first, second]}
    for event in events:
        event.source_ids = [source.id]
        event.global_heat_score = 70
    preference = UserPreference("u1", domains=["AI"], channels=["模型与产品"], keywords=["推理"], muted_sources=[])
    ranked = rank_events(events, articles, preference, sort="relevance")
    assert len(ranked) == 2
    assert ranked[0].title == "推理模型发布"
    preference.muted_sources = [source.id]
    assert rank_events(events, articles, preference) == []
