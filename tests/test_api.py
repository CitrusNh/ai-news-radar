import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.store import demo_store


@pytest.fixture()
def client():
    return TestClient(create_app(demo_store()))


def test_health_and_domains(client):
    assert client.get("/api/v1/health").json()["status"] == "ok"
    domains = client.get("/api/v1/domains").json()
    assert [item["id"] for item in domains] == ["全部", "AI", "科技", "财经", "娱乐", "体育", "游戏"]
    assert next(item for item in domains if item["id"] == "AI")["event_count"] > 0


def test_list_events_supports_domain_channel_keyword_and_sort(client):
    response = client.get("/api/v1/events", params={"domain": "AI", "channel": "企业应用", "sort": "relevance"}, headers={"X-Anonymous-User": "u-api"})
    assert response.status_code == 200
    events = response.json()
    assert events and all(event["channel"] == "企业应用" for event in events)
    assert events[0]["source_names"] and events[0]["source_urls"]
    keyword = client.get("/api/v1/events", params={"keyword": "Agent"}, headers={"X-Anonymous-User": "u-api"}).json()
    assert keyword and all("Agent" in event["title"] or "Agent" in event["enrichment"]["summary"] for event in keyword)


def test_event_actions_preferences_and_library_flow(client):
    headers = {"X-Anonymous-User": "u-flow"}
    event = client.get("/api/v1/events", headers=headers).json()[0]
    event_id = event["id"]
    saved = client.post(f"/api/v1/events/{event_id}/actions", json={"action_type": "saved"}, headers=headers)
    assert saved.status_code == 201
    assert client.get("/api/v1/library", headers=headers).json()[0]["id"] == event_id
    preference = client.put("/api/v1/preferences", json={"domains": ["AI"], "channels": ["企业应用"], "keywords": ["Agent"]}, headers=headers)
    assert preference.json()["channels"] == ["企业应用"]
    assert client.get("/api/v1/preferences", headers=headers).json()["keywords"] == ["Agent"]
    assert client.post(f"/api/v1/events/{event_id}/actions", json={"action_type": "read"}, headers=headers).status_code == 201
    assert client.get("/api/v1/library", params={"type": "read"}, headers=headers).json()[0]["id"] == event_id


def test_unread_and_unsaved_actions_remove_items_from_library(client):
    headers = {"X-Anonymous-User": "u-toggle"}
    event_id = client.get("/api/v1/events", headers=headers).json()[0]["id"]
    client.post(f"/api/v1/events/{event_id}/actions", json={"action_type": "saved"}, headers=headers)
    client.post(f"/api/v1/events/{event_id}/actions", json={"action_type": "unsaved"}, headers=headers)
    assert client.get("/api/v1/library", headers=headers).json() == []
    client.post(f"/api/v1/events/{event_id}/actions", json={"action_type": "read"}, headers=headers)
    client.post(f"/api/v1/events/{event_id}/actions", json={"action_type": "unread"}, headers=headers)
    assert client.get("/api/v1/library", params={"type": "read"}, headers=headers).json() == []


def test_invalid_event_and_invalid_action_are_rejected(client):
    assert client.get("/api/v1/events/not-found").status_code == 404
    assert client.post("/api/v1/events/not-found/actions", json={"action_type": "saved"}).status_code == 404
    event_id = client.get("/api/v1/events").json()[0]["id"]
    assert client.post(f"/api/v1/events/{event_id}/actions", json={"action_type": "unknown"}).status_code == 422


def test_source_health_and_demo_run(client):
    health = client.get("/api/v1/admin/source-health")
    assert health.status_code == 200 and len(health.json()) >= 5
    run = client.post("/api/v1/admin/runs")
    assert run.status_code == 201 and run.json()["status"] == "completed"
    assert client.get(f"/api/v1/admin/runs/{run.json()['run_id']}").json()["run_id"] == run.json()["run_id"]
