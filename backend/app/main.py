from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .ingestion import validate_feed_url
from .models import Source, UserAction, UserPreference, model_to_dict
from .schemas import ActionIn, ActionOut, EventOut, PreferenceIn, PreferenceOut, RunOut, SourceDetailOut, SourceHealthOut, SourceIn
from .scheduler import IntervalScheduler
from .store import InMemoryStore
from .sqlite_store import persistent_demo_store
from .workflow import IngestionWorkflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def create_app(store: InMemoryStore | None = None, frontend_dir: Path | None = None) -> FastAPI:
    database_path = os.getenv("SIGNALSCOPE_DATABASE_PATH", "data/runtime/signalscope.db")
    database_url = os.getenv("DATABASE_URL")
    selected_store = store or persistent_demo_store(database_path, database_url)
    scheduler_enabled = os.getenv("SIGNALSCOPE_SCHEDULER_ENABLED", "false").lower() in {"1", "true", "yes"}
    scheduler_interval = int(os.getenv("SIGNALSCOPE_SCHEDULER_INTERVAL_SECONDS", "14400"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.scheduler.start()
        yield
        app.state.scheduler.stop()

    app = FastAPI(title="SignalScope AI API", version="0.1.0", description="AI 热点摘要雷达 MVP API", lifespan=lifespan)
    allowed_origins = [origin.strip() for origin in os.getenv("SIGNALSCOPE_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
    if allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type", "X-Anonymous-User", "X-Admin-Key"])
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.state.store = selected_store
    app.state.scheduler = IntervalScheduler(lambda: IngestionWorkflow(app.state.store).run(), scheduler_interval, scheduler_enabled)
    web_dir = frontend_dir or FRONTEND_DIR

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'"
        return response

    def get_store() -> InMemoryStore:
        return app.state.store

    def anonymous_user(x_anonymous_user: str | None = Header(default=None)) -> str:
        value = (x_anonymous_user or "demo-user").strip()
        if len(value) > 80:
            raise HTTPException(status_code=400, detail="X-Anonymous-User is too long")
        return value

    def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
        expected = os.getenv("SIGNALSCOPE_ADMIN_KEY", "")
        if not expected:
            raise HTTPException(status_code=503, detail="admin API is disabled until SIGNALSCOPE_ADMIN_KEY is configured")
        if x_admin_key != expected:
            raise HTTPException(status_code=401, detail="invalid admin key")

    def event_out(event, store: InMemoryStore) -> EventOut:
        payload = model_to_dict(event)
        payload["article_count"] = len(event.article_ids)
        payload["source_count"] = len(event.source_ids)
        payload["source_names"] = [store.sources[source_id].name for source_id in event.source_ids if source_id in store.sources]
        payload["source_urls"] = [store.articles[article_id].canonical_url for article_id in event.article_ids if article_id in store.articles and not store.articles[article_id].duplicate_of]
        return EventOut.model_validate(payload)

    @app.get("/api/v1/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "service": "signalscope-api", "storage": type(app.state.store).__name__, "scheduler": {"enabled": app.state.scheduler.state.enabled, "running": app.state.scheduler.state.running, "interval_seconds": app.state.scheduler.state.interval_seconds}}

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

    @app.get("/api/v1/admin/sources", response_model=list[SourceDetailOut], dependencies=[Depends(require_admin)])
    def list_sources(store: InMemoryStore = Depends(get_store)) -> list[SourceDetailOut]:
        return [SourceDetailOut.model_validate(model_to_dict(source)) for source in store.sources.values()]

    @app.put("/api/v1/admin/sources/{source_id}", response_model=SourceDetailOut, dependencies=[Depends(require_admin)])
    def put_source(source_id: str, payload: SourceIn, store: InMemoryStore = Depends(get_store)) -> SourceDetailOut:
        if source_id != payload.id:
            raise HTTPException(status_code=400, detail="source id in path and payload must match")
        try:
            validate_feed_url(payload.feed_url)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return SourceDetailOut.model_validate(model_to_dict(store.upsert_source(Source(**payload.model_dump()))))

    @app.post("/api/v1/admin/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
    def trigger_run(store: InMemoryStore = Depends(get_store)) -> RunOut:
        run = IngestionWorkflow(store).run()
        return RunOut(run_id=run.id, status=run.status, source_count=run.source_count, article_count=run.article_count, error_count=run.error_count, errors=run.errors, started_at=run.started_at, finished_at=run.finished_at)

    @app.get("/api/v1/admin/runs/{run_id}", response_model=RunOut, dependencies=[Depends(require_admin)])
    def get_run(run_id: str, store: InMemoryStore = Depends(get_store)) -> RunOut:
        run = store.runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return RunOut(run_id=run.id, status=run.status, source_count=run.source_count, article_count=run.article_count, error_count=run.error_count, errors=run.errors, started_at=run.started_at, finished_at=run.finished_at)

    if web_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=web_dir), name="assets")

        @app.get("/", include_in_schema=False)
        def website_home() -> FileResponse:
            return FileResponse(web_dir / "index.html")

        @app.get("/{path:path}", include_in_schema=False)
        def website_fallback(path: str) -> FileResponse:
            candidate = (web_dir / path).resolve()
            if web_dir.resolve() in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(web_dir / "index.html")

    return app


app = create_app()
