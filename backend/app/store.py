from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from .models import Article, CrawlRun, Event, Source, UserAction, UserPreference
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
        self.runs: dict[str, CrawlRun] = {}

    def persist(self) -> None:
        """Persistence hook overridden by durable stores."""

    def upsert_source(self, source: Source) -> Source:
        with self._lock:
            self.sources[source.id] = source
            self.persist()
            return source

    def add_run(self, run: CrawlRun) -> CrawlRun:
        with self._lock:
            self.runs[run.id] = run
            self.persist()
            return run

    def ingest_raw_articles(self, raw_articles: list[dict]) -> list[Article]:
        """Incrementally add new articles and rebuild derived events deterministically."""

        with self._lock:
            known_urls = {article.canonical_url for article in self.articles.values()}
            added: list[Article] = []
            for raw in raw_articles:
                source = self.sources[raw["source_id"]]
                candidate_id = f"art-{uuid4().hex[:12]}"
                article = normalize_article(raw, source, candidate_id)
                if article.canonical_url in known_urls:
                    continue
                known_urls.add(article.canonical_url)
                self.articles[article.id] = article
                added.append(article)
            all_articles = deduplicate_articles(list(self.articles.values()))
            events = cluster_events(all_articles)
            self.events = {event.id: event for event in events}
            for event in events:
                calculate_global_heat(event, self.articles, self.sources)
                build_demo_enrichment(event, self.articles)
            self.persist()
            return added

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
            self.persist()
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
            self.persist()
            return action

    def library(self, anonymous_user_id: str, action_type: str = "saved") -> list[Event]:
        latest_actions: dict[str, str] = {}
        for action in self.actions:
            if action.anonymous_user_id != anonymous_user_id:
                continue
            if action_type == "saved" and action.action_type in {"saved", "unsaved"}:
                latest_actions[action.event_id] = action.action_type
            elif action_type == "read" and action.action_type in {"read", "unread"}:
                latest_actions[action.event_id] = action.action_type
        active_ids = {event_id for event_id, latest in latest_actions.items() if latest == action_type}
        return [self.events[event_id] for event_id in active_ids if event_id in self.events]


def demo_store() -> InMemoryStore:
    now = datetime.now(timezone.utc)
    sources = [
        Source("openai", "OpenAI", trust_tier=3),
        Source("deepmind", "Google DeepMind", trust_tier=3),
        Source("mit-tech-review", "MIT Technology Review", source_type="editorial", trust_tier=2),
        Source("huggingface", "Hugging Face", source_type="community", trust_tier=2),
        Source("microsoft-ai", "Microsoft AI", trust_tier=3),
        Source("the-information", "The Information", source_type="editorial", trust_tier=2),
        Source("bloomberg", "Bloomberg", source_type="editorial", trust_tier=2),
        Source("stanford-hai", "Stanford HAI", source_type="research", trust_tier=3),
        Source("techcrunch", "TechCrunch", source_type="editorial", trust_tier=2),
        Source("anthropic", "Anthropic", trust_tier=3),
        Source("aws-ml", "AWS Machine Learning", trust_tier=3),
        Source("meta-ai", "Meta AI", trust_tier=3),
    ]
    raw_articles = [
        {"source_id": "openai", "url": "https://openai.com/news/reasoning-model?utm_source=demo", "title": "OpenAI 发布新一代推理模型", "summary": "新模型针对长链路推理与工具调用做了系统性优化，开发者预览版开放。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["OpenAI", "推理模型"]},
        {"source_id": "deepmind", "url": "https://deepmind.google/discover/blog/gemini-collab", "title": "Gemini 新增实时协作能力", "summary": "更新后的工作流允许用户在文档和代码环境中持续调整目标。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["Gemini", "协作"]},
        {"source_id": "mit-tech-review", "url": "https://www.technologyreview.com/ai-safety-standard", "title": "全球 AI 安全评测开始趋向统一", "summary": "监管机构与研究组织正在推动更可比的评测框架。", "channel": "政策安全", "published_at": now.replace(microsecond=0), "entities": ["AI 安全", "监管"]},
        {"source_id": "huggingface", "url": "https://huggingface.co/blog/light-multimodal", "title": "开源社区发布轻量级多模态模型", "summary": "新模型在消费级 GPU 上即可运行，降低多模态原型成本。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["多模态", "开源模型"]},
        {"source_id": "microsoft-ai", "url": "https://blogs.microsoft.com/ai/agent-workflow", "title": "企业开始把 AI Agent 接入审批和运营流程", "summary": "企业案例显示 Agent 的价值正在从对话体验转向流程自动化。", "channel": "企业应用", "published_at": now.replace(microsecond=0), "entities": ["AI Agent", "工作流"]},
        {"source_id": "the-information", "url": "https://www.theinformation.com/articles/manufacturing-ai-procurement", "title": "制造业 AI 采购从试点进入规模化", "summary": "多家制造企业将 AI 项目移交到业务线，采购关注点转向可量化的效率收益。", "channel": "企业应用", "published_at": now.replace(microsecond=0), "entities": ["制造业", "企业采购", "ROI"]},
        {"source_id": "bloomberg", "url": "https://www.bloomberg.com/news/articles/ai-infrastructure-europe", "title": "欧洲 AI 基础设施融资升温", "summary": "新一轮投资关注数据中心、电力和模型服务的组合方案。", "channel": "资本市场", "published_at": now.replace(microsecond=0), "entities": ["AI 基础设施", "算力", "能源"]},
        {"source_id": "stanford-hai", "url": "https://hai.stanford.edu/research/agent-risk-benchmark", "title": "研究团队提出新的 Agent 风险基准", "summary": "基准测试覆盖任务规划、工具调用和越权行为，为评估 Agent 可控性提供样例。", "channel": "政策安全", "published_at": now.replace(microsecond=0), "entities": ["Agent 安全", "评测基准", "工具调用"]},
        {"source_id": "techcrunch", "url": "https://techcrunch.com/2026/09/01/ai-app-funding-retention", "title": "AI 应用公司融资逻辑转向客户留存", "summary": "投资人开始要求 AI 应用证明重复使用率和毛利改善。", "channel": "资本市场", "published_at": now.replace(microsecond=0), "entities": ["AI 应用", "融资", "客户留存"]},
        {"source_id": "anthropic", "url": "https://www.anthropic.com/research/context-management", "title": "更好的上下文管理可能比更大的模型更重要", "summary": "研究者将注意力放在任务拆解、上下文压缩和记忆策略。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["上下文管理", "模型优化", "记忆"]},
        {"source_id": "aws-ml", "url": "https://aws.amazon.com/machine-learning/case-studies/retail-knowledge", "title": "零售企业用生成式 AI 重做客服知识库", "summary": "项目重点在知识更新、人工复核和效果监控组成的完整闭环。", "channel": "企业应用", "published_at": now.replace(microsecond=0), "entities": ["零售", "客服", "知识库"]},
        {"source_id": "meta-ai", "url": "https://ai.meta.com/blog/creative-tools", "title": "社交平台把生成式 AI 工具前置到创作入口", "summary": "图片编辑和短视频辅助开始以低门槛方式嵌入已有创作流程。", "channel": "模型与产品", "published_at": now.replace(microsecond=0), "entities": ["生成式 AI", "内容创作", "平台"]},
    ]
    store = InMemoryStore()
    store.seed(sources, raw_articles)
    return store
