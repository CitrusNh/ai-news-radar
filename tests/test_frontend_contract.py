from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")


def test_frontend_keeps_required_demo_surfaces():
    for element_id in ["domainTabs", "channelTabs", "newsFeed", "searchInput", "sortSelect", "detailModal", "filterModal", "dataStatus", "activeSourceCount", "schedulerStatus"]:
        assert f'id="{element_id}"' in INDEX


def test_frontend_uses_api_with_local_fallback():
    assert 'window.SIGNALSCOPE_API_BASE || "/api/v1"' in APP
    assert "loadNewsFromApi" in APP
    assert "FALLBACK_NEWS" in APP
    assert "apiNews || FALLBACK_NEWS" in APP
    assert "loadBackendState" in APP


def test_frontend_maps_api_event_fields_needed_by_cards():
    for field in ["source_names", "source_urls", "global_heat_score", "personal_relevance", "key_facts", "why_it_matters"]:
        assert field in APP


def test_readme_documents_persistence_safety_and_admin_workflow():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in ["SQLite 持久化", "compliance_status", "SIGNALSCOPE_ADMIN_KEY", "/api/v1/admin/runs"]:
        assert phrase in readme


def test_container_contract_serves_one_site_with_persistent_data():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "USER signalscope" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert "8000:8000" in compose
    assert "signalscope-data:/app/data/runtime" in compose
