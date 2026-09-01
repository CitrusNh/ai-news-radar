from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")


def test_frontend_keeps_required_demo_surfaces():
    for element_id in ["domainTabs", "channelTabs", "newsFeed", "searchInput", "sortSelect", "detailModal", "filterModal", "dataStatus", "activeSourceCount", "schedulerStatus"]:
        assert f'id="{element_id}"' in INDEX


def test_frontend_uses_api_with_local_fallback():
    assert "http://127.0.0.1:8000/api/v1" in APP
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
