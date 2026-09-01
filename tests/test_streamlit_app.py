from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_page_reports_missing_public_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=10).run()
    assert not app.exception
    assert any("缺少 DATABASE_URL" in item.value for item in app.error)
    assert any("Streamlit Community Cloud" in item.value for item in app.info)
