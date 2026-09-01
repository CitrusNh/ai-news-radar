from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from .models import Article, Event, Source, UserAction, UserPreference
from .processing import build_demo_enrichment, calculate_global_heat, cluster_events, deduplicate_articles, normalize_article, rank_events


class InMemoryStore:
    """Thread-safe repository for the MVP; replaceable by SQLite/PostgreSQL later."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.sources: dict[str, Source] = {}
        self.articles: dict[str, Article] = {}
        self.events: dict[str, Event] = {}
        self.preferences: dict[str, UserPreference] = {}
        self.actions: list[UserAction] = []

    def seed(self, sources: list[Source], raw_articles: list[dict]) -> None:
        with self._lock:
            self.sources = {source.id: source for source in sources}
            articles: list[Article] = []
            for index, raw in enumerate(raw_articles, start=1):
                source = self.sources[raw["source_id"]]
                articles.append(normalize_article(raw, source, f"art-{index:04d}"))
            articles = deduplicate_articles(articles)
            self.articles = {article.id: article for article in articles}
            events = cluster_events(articles)
            self.events = {event.id: event for event in events}
            for event in events:
                calculate_global_heat(event, self.articles, self.sources)
                build_demo_enrichment(event, self.articles)

    def get_preference(self, anonymous_user_id: str) -> UserPreference:
        with self._lock:
            return self.preferences.setdefault(anonymous_user_id, UserPreference(anonymous_user_id=anonymous_user_id))

    def set_preference(self, preference: UserPreference) -> UserPreference:
        with self._lock:
            self.preferences[preference.anonymous_user_id] = preference
            return preference

    def list_events(self, anonymous_user_id: str, domain: str | None = None, channel: str | None = None, keyword: str | None = None, sort: str = "heat") -> list[Event]:
        preference = self.get_preference(anonymous_user_id)
        if domain:
            preference.domains = [domain]
        events = rank_events(self.events.values(), self.articles, preference, sort=sort)
        if channel and channel != "全部":
            events = [event for event in events if event.channel == channel]
        if keyword:
            query = keyword.lower()
            events = [event for event in events if query in event.title.lower() or any(query in article.title.lower() for article in self._event_articles(event))]
        return events

    def _event_articles(self, event: Event) -> list[Article]:
        return [self.articles[article_id] for article_id in event.article_ids if article_id in self.articles]

    def get_event(self, event_id: str) -> Event | None:
        return self.events.get(event_id)

    def add_action(self, action: UserAction) -> UserAction:
        with self._lock:
            if action.action_type == "saved":
                self.actions = [existing for existing in self.actions if not (existing.anonymous_user_id == action.anonymous_user_id and existing.event_id == action.event_id and existing.action_type == "unsaved")]
            self.actions.append(action)
            return action

    def library(self, anonymous_user_id: str, action_type: str = "saved") -> list[Event]:
        active_ids: set[str] = set()
        for action in self.actions:
            if action.anonymous_user_id != anonymous_user_id:
                continue
            if action.action_type == action_type:
                active_ids.add(action.event_id)
            elif action.action_type in {"unsaved", "unread"} and action_type == "saved":
                active_ids.discard(action.event_id)
        return [self.events[event_id] for event_id in active_ids if event_id in self.events]


def demo_store() -> InMemoryStore:
    now = datetime.now(timezone.utc)
    sources = [
        Source("openai", "OpenAI", trust_tier=3),
        Source("deepmind", "Google DeepMind", trust_tier=3),
        Source("mit-tech-review", "MIT Technology Review", source_type="editorial", trust_tier=2),
        Source("huggingface", "Hugging Face", source_type="community", trust_tier=2),
        Source("microsoft-ai", "Microsoft AI", trust_tier=3),
    ]
    raw_articles = [
        {"source_id": "openai", "url": "https://openai.com/news/reasoning-model?utm_source=demo", "title": "OpenAI 发布新一代推理模型", "summary": "新模型针对长链路推理与工具调用做了系统性优化，开发者预览版开放。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["OpenAI", "推理模型"]},
        {"source_id": "deepmind", "url": "https://deepmind.google/discover/blog/gemini-collab", "title": "Gemini 新增实时协作能力", "summary": "更新后的工作流允许用户在文档和代码环境中持续调整目标。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["Gemini", "协作"]},
        {"source_id": "mit-tech-review", "url": "https://www.technologyreview.com/ai-safety-standard", "title": "全球 AI 安全评测开始趋向统一", "summary": "监管机构与研究组织正在推动更可比的评测框架。", "channel": "政策安全", "published_at": now.replace(microsecond=0), "entities": ["AI 安全", "监管"]},
        {"source_id": "huggingface", "url": "https://huggingface.co/blog/light-multimodal", "title": "开源社区发布轻量级多模态模型", "summary": "新模型在消费级 GPU 上即可运行，降低多模态原型成本。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["多模态", "开源模型"]},
        {"source_id": "microsoft-ai", "url": "https://blogs.microsoft.com/ai/agent-workflow", "title": "企业开始把 AI Agent 接入审批和运营流程", "summary": "企业案例显示 Agent 的价值正在从对话体验转向流程自动化。", "channel": "企业应用", "published_at": now.replace(microsecond=0), "entities": ["AI Agent", "工作流"]},
    ]
    store = InMemoryStore()
    store.seed(sources, raw_articles)
    return store
