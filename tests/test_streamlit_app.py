from pathlib import Path

from streamlit.testing.v1 import AppTest

from streamlit_app import format_wait_time


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_page_reports_missing_public_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=10).run()
    assert not app.exception
    assert any("缺少 DATABASE_URL" in item.value for item in app.error)
    assert any("Streamlit Community Cloud" in item.value for item in app.info)


def test_manual_update_wait_time_is_readable():
    assert format_wait_time(45) == "45 秒"
    assert format_wait_time(125) == "2 分 5 秒"
