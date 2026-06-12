"""Plan management: long-term milestones and daily task planning."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from .models import Config, DailyPlan, LongtermPlan, Milestone, Task
from .store import Store


# ---------------------------------------------------------------------------
# Long-term planning
# ---------------------------------------------------------------------------


def get_active_milestone(plan: LongtermPlan) -> Milestone | None:
    """Return the first incomplete milestone, or None if all done."""
    for m in plan.milestones:
        if not m.completed:
            return m
    return None


def get_upcoming_milestones(plan: LongtermPlan, days: int = 30) -> list[Milestone]:
    """Return incomplete milestones due within the given days."""
    today = date.today()
    limit = today + timedelta(days=days)
    result: list[Milestone] = []
    for m in plan.milestones:
        if m.completed:
            continue
        try:
            deadline = date.fromisoformat(m.deadline)
        except ValueError:
            continue
        if deadline <= limit:
            result.append(m)
    return result


def check_milestones(plan: LongtermPlan) -> list[dict[str, Any]]:
    """Check milestone status and return alerts."""
    today = date.today()
    alerts: list[dict[str, Any]] = []
    for m in plan.milestones:
        if m.completed:
            continue
        try:
            deadline = date.fromisoformat(m.deadline)
        except ValueError:
            continue
        days_left = (deadline - today).days
        if days_left < 0:
            alerts.append({"milestone": m.name, "status": "overdue", "days": days_left})
        elif days_left <= 7:
            alerts.append({"milestone": m.name, "status": "urgent", "days": days_left})
        elif days_left <= 14:
            alerts.append({"milestone": m.name, "status": "approaching", "days": days_left})
    return alerts


def toggle_milestone(plan: LongtermPlan, milestone_id: str) -> bool:
    """Toggle completion status of a milestone. Returns True if found."""
    for m in plan.milestones:
        if m.id == milestone_id:
            m.completed = not m.completed
            return True
    return False


# ---------------------------------------------------------------------------
# Daily planning
# ---------------------------------------------------------------------------

# Default time allocation ratios for the preparation phase.
# These are starting points; supervisor.py will adjust based on progress.
_SUBJECT_WEIGHTS: dict[str, float] = {
    "数学一": 0.35,
    "408": 0.30,
    "英语一": 0.20,
    "政治": 0.15,
}


def suggest_daily_tasks(
    config: Config,
    longterm: LongtermPlan,
    yesterday: DailyPlan | None = None,
) -> list[Task]:
    """Generate suggested tasks for today based on config and milestones."""
    total_minutes = config.daily_study_hours * 60
    active = get_active_milestone(longterm)
    tasks: list[Task] = []

    # Carry over incomplete tasks from yesterday
    if yesterday:
        for t in yesterday.tasks:
            if not t.done:
                tasks.append(
                    Task(
                        subject=t.subject,
                        content=f"[顺延] {t.content}",
                        planned_minutes=t.planned_minutes,
                    )
                )

    # Allocate remaining time across subjects
    carried_minutes = sum(t.planned_minutes for t in tasks)
    remaining = total_minutes - carried_minutes

    if remaining > 0:
        for subject, weight in _SUBJECT_WEIGHTS.items():
            if subject in config.subjects:
                minutes = int(remaining * weight)
                minutes = (minutes // 5) * 5  # round to 5-min blocks
                if minutes > 0:
                    content = _default_task_content(subject, active)
                    tasks.append(
                        Task(
                            subject=subject,
                            content=content,
                            planned_minutes=minutes,
                        )
                    )

    return tasks


def _default_task_content(subject: str, milestone: Milestone | None) -> str:
    """Return a placeholder task description for a subject."""
    phase = f"（{milestone.name}阶段）" if milestone else ""
    content_map: dict[str, str] = {
        "数学一": f"数学复习{phase}",
        "英语一": f"英语复习{phase}",
        "政治": f"政治复习{phase}",
        "408": f"专业课复习{phase}",
    }
    return content_map.get(subject, f"{subject}复习{phase}")


def create_today_plan(
    store: Store,
    tasks: list[Task] | None = None,
) -> DailyPlan:
    """Create or load today's plan. If tasks provided, use them; otherwise suggest."""
    today = date.today().isoformat()
    existing = store.load_daily_plan(today)
    if existing.tasks:
        return existing  # already has tasks, don't overwrite

    if tasks is None:
        config = store.load_config()
        longterm = store.load_longterm_plan()
        yesterday = store.load_daily_plan(date.today() - timedelta(days=1))
        tasks = suggest_daily_tasks(config, longterm, yesterday)

    plan = DailyPlan(date=today, tasks=tasks)
    store.save_daily_plan(plan)
    return plan


def add_task_to_plan(plan: DailyPlan, task: Task) -> DailyPlan:
    """Add a task to the daily plan."""
    plan.tasks.append(task)
    return plan


def remove_task(plan: DailyPlan, task_id: str) -> bool:
    """Remove a task by ID. Returns True if found and removed."""
    before = len(plan.tasks)
    plan.tasks = [t for t in plan.tasks if t.id != task_id]
    return len(plan.tasks) < before


def complete_task(plan: DailyPlan, task_id: str) -> bool:
    """Mark a task as done. Returns True if found."""
    task = plan.task_by_id(task_id)
    if task is None:
        return False
    task.done = True
    return True
