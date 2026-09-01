from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class EntityOut(BaseModel):
    name: str
    type: str


class EnrichmentOut(BaseModel):
    summary: str
    key_facts: list[str]
    entities: list[EntityOut]
    topic_labels: list[str]
    why_it_matters: str
    uncertainty_level: Literal["low", "medium", "high"]
    needs_review: bool
    model_name: str
    prompt_version: str


class SourceOut(BaseModel):
    id: str
    name: str


class ArticleOut(BaseModel):
    id: str
    source_id: str
    source_name: str
    canonical_url: str
    title: str
    source_summary: str
    published_at: datetime
    language: str


class EventOut(BaseModel):
    id: str
    domain: str
    channel: str
    title: str
    article_count: int
    source_count: int
    source_ids: list[str]
    source_names: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    first_seen_at: datetime
    last_seen_at: datetime
    global_heat_score: float
    personal_relevance: float
    impact_level: str
    uncertainty_level: str
    status: str
    enrichment: EnrichmentOut | None = None


class PreferenceIn(BaseModel):
    domains: list[str] = Field(default_factory=lambda: ["AI"])
    channels: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    muted_sources: list[str] = Field(default_factory=list)
    language: str = "zh-CN"

    @field_validator("domains", "channels", "keywords", "entities", "muted_sources")
    @classmethod
    def trim_values(cls, values: list[str]) -> list[str]:
        cleaned = [str(value).strip() for value in values if str(value).strip()]
        if len(cleaned) > 30:
            raise ValueError("a preference list may contain at most 30 items")
        return list(dict.fromkeys(cleaned))


class PreferenceOut(PreferenceIn):
    anonymous_user_id: str


class ActionIn(BaseModel):
    action_type: Literal["viewed", "saved", "unsaved", "read", "unread", "not_interested", "clicked_source", "shared"]


class ActionOut(BaseModel):
    anonymous_user_id: str
    event_id: str
    action_type: str
    created_at: datetime


class SourceHealthOut(BaseModel):
    id: str
    name: str
    active: bool
    trust_tier: int
    article_count: int
    latest_article_at: datetime | None


class SourceIn(BaseModel):
    id: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str = Field(min_length=1, max_length=120)
    domain: str = "AI"
    source_type: str = "official"
    trust_tier: int = Field(default=2, ge=1, le=3)
    active: bool = True
    feed_url: str
    terms_url: str = ""
    robots_status: Literal["unknown", "allowed", "blocked"] = "unknown"
    default_channel: str = "未分类"
    compliance_status: Literal["pending", "approved", "rejected"] = "pending"


class SourceDetailOut(SourceIn):
    pass


class RunOut(BaseModel):
    run_id: str
    status: str
    source_count: int
    article_count: int
    error_count: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
