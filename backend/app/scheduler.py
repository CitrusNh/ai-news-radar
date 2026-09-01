from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class SchedulerState:
    enabled: bool
    interval_seconds: int
    running: bool = False


class IntervalScheduler:
    """Small dependency-free scheduler suitable for a single-process MVP."""

    def __init__(self, task: Callable[[], object], interval_seconds: int, enabled: bool = False) -> None:
        if interval_seconds < 60:
            raise ValueError("scheduler interval must be at least 60 seconds")
        self.task = task
        self.state = SchedulerState(enabled=enabled, interval_seconds=interval_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.state.enabled or self.state.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="signalscope-scheduler", daemon=True)
        self.state.running = True
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.state.interval_seconds):
            try:
                self.task()
            except Exception:
                # Workflow records source-level failures. An unexpected scheduler error
                # must not kill the API process or stop future intervals.
                continue

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.state.running = False

