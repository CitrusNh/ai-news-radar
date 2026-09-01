from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_github_news_workflow_has_beijing_schedule_and_manual_dispatch():
    workflow = (ROOT / ".github" / "workflows" / "news-update.yml").read_text(encoding="utf-8")
    assert 'cron: "0 0 * * *"' in workflow
    assert 'cron: "0 14 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "DATABASE_URL: ${{ secrets.DATABASE_URL }}" in workflow
    assert "python -m scripts.update_news" in workflow
    assert "cancel-in-progress: false" in workflow


def test_update_script_is_importable_without_running_the_job():
    from scripts.update_news import main

    assert callable(main)
