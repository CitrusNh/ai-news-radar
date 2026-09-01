from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from .models import UserAction, UserPreference, model_to_dict
from .schemas import ActionIn, ActionOut, EventOut, PreferenceIn, PreferenceOut, RunOut, SourceHealthOut
from .store import InMemoryStore, demo_store


def create_app(store: InMemoryStore | None = None) -> FastAPI:
    app = FastAPI(title="SignalScope AI API", version="0.1.0", description="AI 热点摘要雷达 MVP API")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "PUT"], allow_headers=["*"])
    app.state.store = store or demo_store()

    def get_store() -> InMemoryStore:
        return app.state.store

    def anonymous_user(x_anonymous_user: str | None = Header(default=None)) -> str:
        value = (x_anonymous_user or "demo-user").strip()
        if len(value) > 80:
            raise HTTPException(status_code=400, detail="X-Anonymous-User is too long")
        return value

    def event_out(event, store: InMemoryStore) -> EventOut:
        payload = model_to_dict(event)
        payload["article_count"] = len(event.article_ids)
        payload["source_count"] = len(event.source_ids)
        payload["source_names"] = [store.sources[source_id].name for source_id in event.source_ids if source_id in store.sources]
        payload["source_urls"] = [store.articles[article_id].canonical_url for article_id in event.article_ids if article_id in store.articles and not store.articles[article_id].duplicate_of]
        return EventOut.model_validate(payload)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "signalscope-api"}

    @app.get("/api/v1/domains")
    def domains(store: InMemoryStore = Depends(get_store)) -> list[dict[str, object]]:
        counts: dict[str, int] = {}
        for event in store.events.values():
            counts[event.domain] = counts.get(event.domain, 0) + 1
        return [{"id": domain, "name": domain, "event_count": counts.get(domain, 0), "status": "active" if counts.get(domain, 0) else "planned"} for domain in ["全部", "AI", "科技", "财经", "娱乐", "体育", "游戏"]]

    @app.get("/api/v1/events", response_model=list[EventOut])
    def list_events(
        domain: str | None = Query(default=None, max_length=30),
        channel: str | None = Query(default=None, max_length=40),
        keyword: str | None = Query(default=None, max_length=80),
        sort: str = Query(default="heat", pattern="^(heat|fresh|relevance)$"),
        user_id: str = Depends(anonymous_user),
        store: InMemoryStore = Depends(get_store),
    ) -> list[EventOut]:
        if domain == "全部":
            domain = "AI"
        events = store.list_events(user_id, domain=domain, channel=channel, keyword=keyword, sort=sort)
        return [event_out(event, store) for event in events]

    @app.get("/api/v1/events/{event_id}", response_model=EventOut)
    def get_event(event_id: str, store: InMemoryStore = Depends(get_store), user_id: str = Depends(anonymous_user)) -> EventOut:
        event = store.get_event(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="event not found")
        # Calculate the same personalized score as the list endpoint.
        event_list = store.list_events(user_id, domain=event.domain, channel=event.channel)
        selected = next((item for item in event_list if item.id == event_id), event)
        return event_out(selected, store)

    @app.get("/api/v1/preferences", response_model=PreferenceOut)
    def get_preferences(user_id: str = Depends(anonymous_user), store: InMemoryStore = Depends(get_store)) -> PreferenceOut:
        return PreferenceOut.model_validate(model_to_dict(store.get_preference(user_id)))

    @app.put("/api/v1/preferences", response_model=PreferenceOut)
    def put_preferences(payload: PreferenceIn, user_id: str = Depends(anonymous_user), store: InMemoryStore = Depends(get_store)) -> PreferenceOut:
        preference = UserPreference(anonymous_user_id=user_id, **payload.model_dump())
        return PreferenceOut.model_validate(model_to_dict(store.set_preference(preference)))

    @app.post("/api/v1/events/{event_id}/actions", response_model=ActionOut, status_code=status.HTTP_201_CREATED)
    def add_action(event_id: str, payload: ActionIn, user_id: str = Depends(anonymous_user), store: InMemoryStore = Depends(get_store)) -> ActionOut:
        if store.get_event(event_id) is None:
            raise HTTPException(status_code=404, detail="event not found")
        action = store.add_action(UserAction(anonymous_user_id=user_id, event_id=event_id, action_type=payload.action_type))
        return ActionOut.model_validate(model_to_dict(action))

    @app.get("/api/v1/library", response_model=list[EventOut])
    def library(type: str = Query(default="saved", pattern="^(saved|read)$"), user_id: str = Depends(anonymous_user), store: InMemoryStore = Depends(get_store)) -> list[EventOut]:
        return [event_out(event, store) for event in store.library(user_id, action_type=type)]

    @app.get("/api/v1/admin/source-health", response_model=list[SourceHealthOut])
    def source_health(store: InMemoryStore = Depends(get_store)) -> list[SourceHealthOut]:
        result = []
        for source in store.sources.values():
            articles = [article for article in store.articles.values() if article.source_id == source.id and not article.duplicate_of]
            result.append(SourceHealthOut(id=source.id, name=source.name, active=source.active, trust_tier=source.trust_tier, article_count=len(articles), latest_article_at=max((article.published_at for article in articles), default=None)))
        return result

    @app.post("/api/v1/admin/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED)
    def trigger_run(store: InMemoryStore = Depends(get_store)) -> RunOut:
        run_id = f"run-{uuid4().hex[:10]}"
        return RunOut(run_id=run_id, status="demo_noop", source_count=len(store.sources), article_count=len(store.articles))

    return app


app = create_app()
