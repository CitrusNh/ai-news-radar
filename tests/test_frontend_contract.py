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
    for phrase in ["Streamlit Community Cloud", "PostgreSQL", "compliance_status", "SIGNALSCOPE_ADMIN_KEY", "/api/v1/admin/runs", "所有人可访问的网站"]:
        assert phrase in readme


def test_readme_records_the_verified_public_release():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in [
        "https://ai-news-radarbranchmainmainfilepathappapppy-hhjj3jwd6mj57vhpez.streamlit.app/",
        "公网验收结果",
        "47 passed",
        "94.70%",
        "GitHub Actions CI",
        "API 文档仅供本地访问",
    ]:
        assert phrase in readme


def test_ci_runs_tests_frontend_check_and_container_build():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pytest -q" in workflow
    assert "node --check frontend/app.js" in workflow
    assert "python -m py_compile streamlit_app.py" in workflow
    assert "docker/build-push-action@v6" in workflow


def test_streamlit_is_the_public_contract_and_docker_is_a_backup():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "USER signalscope" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "--host 0.0.0.0" in dockerfile
    assert "8000:8000" in compose
    assert "signalscope-data:/app/data/runtime" in compose
    assert not (ROOT / "render.yaml").exists()
    streamlit_app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "resolve_public_database_url" in streamlit_app
    assert "load_public_store" in streamlit_app
    assert "streamlit" in requirements
    assert "DATABASE_URL" in (ROOT / ".streamlit" / "secrets.toml.example").read_text(encoding="utf-8")
