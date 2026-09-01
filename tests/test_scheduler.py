import pytest

from backend.app.scheduler import IntervalScheduler


def test_scheduler_rejects_unsafe_short_interval():
    with pytest.raises(ValueError):
        IntervalScheduler(lambda: None, 10)


def test_disabled_scheduler_does_not_start_and_stop_is_safe():
    scheduler = IntervalScheduler(lambda: None, 60, enabled=False)
    scheduler.start()
    assert not scheduler.state.running
    scheduler.stop()
    assert not scheduler.state.running


def test_enabled_scheduler_start_and_stop():
    scheduler = IntervalScheduler(lambda: None, 60, enabled=True)
    scheduler.start()
    assert scheduler.state.running
    scheduler.stop()
    assert not scheduler.state.running
