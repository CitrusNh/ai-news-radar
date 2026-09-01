from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.store import demo_store


def test_single_origin_serves_website_assets_and_api():
    client = TestClient(create_app(demo_store()))
    home = client.get("/")
    assert home.status_code == 200
    assert "SignalScope AI" in home.text
    assert '/assets/app.js' in home.text
    script = client.get("/assets/app.js")
    assert script.status_code == 200
    assert 'const API_BASE = window.SIGNALSCOPE_API_BASE || "/api/v1"' in script.text
    events = client.get("/api/v1/events?domain=AI")
    assert events.status_code == 200
    assert len(events.json()) == 12


def test_unknown_frontend_route_returns_application_shell():
    client = TestClient(create_app(demo_store()))
    response = client.get("/topics/ai")
    assert response.status_code == 200
    assert "SignalScope AI" in response.text


def test_public_website_sends_security_headers():
    client = TestClient(create_app(demo_store()))
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]
