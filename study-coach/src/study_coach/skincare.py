"""Weekday-aware skincare routine generation.

Turns the weekly skincare schedule (data/routines/skincare.json) into
morning and night Task objects for a given date. Skincare is a lifestyle
routine kept separate from study-hour allocation: it never reduces the
time budget assigned to study subjects.
"""

from __future__ import annotations

from datetime import date

from .models import Task
from .store import Store

_WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _join_steps(steps: list[str]) -> str:
    return "；".join(steps)


def build_skincare_tasks(store: Store, target: date) -> list[Task]:
    """Return the skincare tasks for the given date, or [] if no routine is configured."""
    routine = store.load_skincare_routine()
    if not routine:
        return []

    tasks: list[Task] = []

    morning = routine.get("morning")
    if morning and morning.get("steps"):
        tasks.append(
            Task(
                subject="护肤",
                content=f"{morning.get('label', '晨间护肤')}：{_join_steps(morning['steps'])}",
                planned_minutes=morning.get("minutes", 10),
            )
        )

    night_templates = routine.get("night_templates", {})
    weekday_map = routine.get("weekday_map", {})
    day_key = _WEEKDAY_KEYS[target.weekday()]
    template_key = weekday_map.get(day_key)
    night = night_templates.get(template_key) if template_key else None
    if night and night.get("steps"):
        tasks.append(
            Task(
                subject="护肤",
                content=f"{night.get('label', '夜间护肤')}：{_join_steps(night['steps'])}",
                planned_minutes=night.get("minutes", 15),
            )
        )

    return tasks
