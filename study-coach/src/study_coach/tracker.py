"""Pomodoro timer and study time tracking."""

from __future__ import annotations

import time
from datetime import date, datetime

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .models import DailyPlan, Pomodoro
from .store import Store


# Pomodoro defaults
WORK_MINUTES = 25
SHORT_BREAK_MINUTES = 5
LONG_BREAK_MINUTES = 15
POMODOROS_BEFORE_LONG_BREAK = 4


class PomodoroSession:
    """Tracks an in-progress pomodoro session."""

    def __init__(
        self,
        task_id: str,
        subject: str,
        duration_minutes: int = WORK_MINUTES,
    ) -> None:
        self.task_id = task_id
        self.subject = subject
        self.duration_minutes = duration_minutes
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self._running = False

    def start(self) -> None:
        self.start_time = datetime.now()
        self._running = True

    def stop(self) -> None:
        self.end_time = datetime.now()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def elapsed_seconds(self) -> int:
        if self.start_time is None:
            return 0
        end = self.end_time or datetime.now()
        return int((end - self.start_time).total_seconds())

    @property
    def remaining_seconds(self) -> int:
        return max(0, self.duration_minutes * 60 - self.elapsed_seconds)

    def to_pomodoro(self) -> Pomodoro:
        return Pomodoro(
            start=self.start_time.strftime("%H:%M") if self.start_time else "",
            end=self.end_time.strftime("%H:%M") if self.end_time else "",
            subject=self.subject,
            task_id=self.task_id,
            duration_minutes=self.duration_minutes,
        )


def _format_time(seconds: int) -> str:
    mins, secs = divmod(seconds, 60)
    return f"{mins:02d}:{secs:02d}"


def _build_display(session: PomodoroSession) -> Panel:
    remaining = session.remaining_seconds
    total = session.duration_minutes * 60
    progress = 1.0 - (remaining / total) if total > 0 else 0

    # Progress bar
    bar_width = 30
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)

    text = Text()
    text.append(f"  {session.subject}\n", style="bold cyan")
    text.append(f"  [{bar}] {progress:.0%}\n\n", style="green")
    text.append(f"  Remaining: ", style="dim")
    text.append(f"{_format_time(remaining)}\n", style="bold yellow")
    text.append(f"  Task: ", style="dim")
    text.append(f"{session.task_id}\n")

    return Panel(text, title="🍅 Pomodoro", border_style="red", width=50)


def run_pomodoro(session: PomodoroSession) -> Pomodoro:
    """Run a pomodoro timer with Rich live display. Blocks until done."""
    session.start()

    try:
        with Live(_build_display(session), refresh_per_second=1) as live:
            while session.remaining_seconds > 0:
                time.sleep(1)
                live.update(_build_display(session))
    except KeyboardInterrupt:
        session.stop()
        return session.to_pomodoro()

    session.stop()
    return session.to_pomodoro()


def record_pomodoro(store: Store, pomodoro: Pomodoro) -> DailyPlan:
    """Record a completed pomodoro to today's plan."""
    plan = store.load_daily_plan()

    # Update actual_minutes for the associated task
    task = plan.task_by_id(pomodoro.task_id)
    if task:
        task.actual_minutes += pomodoro.duration_minutes

    plan.pomodoros.append(pomodoro)
    store.save_daily_plan(plan)
    return plan


def get_pomodoro_count_today(store: Store) -> int:
    """Return number of pomodoros completed today."""
    plan = store.load_daily_plan()
    return len(plan.pomodoros)


def suggest_break(pomodoro_count: int) -> tuple[int, str]:
    """Return (break_minutes, break_type) based on pomodoro count."""
    if pomodoro_count > 0 and pomodoro_count % POMODOROS_BEFORE_LONG_BREAK == 0:
        return LONG_BREAK_MINUTES, "long"
    return SHORT_BREAK_MINUTES, "short"
