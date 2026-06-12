"""Supervisor: plan compliance checking and automatic adjustment."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .models import Config, DailyPlan, LongtermPlan, Task
from .planner import (
    _SUBJECT_WEIGHTS,
    get_active_milestone,
    suggest_daily_tasks,
)
from .store import Store


def check_compliance(store: Store, days: int = 7) -> dict[str, Any]:
    """Check plan compliance over the last N days."""
    plans = store.load_recent_plans(days)
    report: dict[str, Any] = {
        "days_checked": len(plans),
        "days_with_plan": 0,
        "days_completed": 0,
        "total_planned_minutes": 0,
        "total_actual_minutes": 0,
        "overdue_tasks": 0,
        "subject_deficit": {},
    }

    for plan in plans:
        if plan.tasks:
            report["days_with_plan"] += 1

        planned = plan.total_planned_minutes()
        actual = plan.total_actual_minutes()
        report["total_planned_minutes"] += planned
        report["total_actual_minutes"] += actual

        done_count = sum(1 for t in plan.tasks if t.done)
        if plan.tasks and done_count == len(plan.tasks):
            report["days_completed"] += 1

        for t in plan.tasks:
            if not t.done:
                report["overdue_tasks"] += 1
                deficit = t.planned_minutes - t.actual_minutes
                if t.subject not in report["subject_deficit"]:
                    report["subject_deficit"][t.subject] = 0
                report["subject_deficit"][t.subject] += deficit

    # Calculate adherence rate
    if report["total_planned_minutes"] > 0:
        report["adherence_rate"] = (
            report["total_actual_minutes"] / report["total_planned_minutes"]
        )
    else:
        report["adherence_rate"] = 0.0

    return report


def adjust_plan(store: Store) -> dict[str, Any]:
    """Analyze recent performance and adjust future planning weights.

    Returns a description of adjustments made.
    """
    config = store.load_config()
    longterm = store.load_longterm_plan()
    compliance = check_compliance(store, days=7)

    adjustments: dict[str, Any] = {
        "adherence_rate": compliance["adherence_rate"],
        "adjustments": [],
        "new_weights": dict(_SUBJECT_WEIGHTS),
    }

    # If overall adherence is low, reduce planned hours
    adherence = compliance["adherence_rate"]
    if adherence < 0.5:
        adjustments["adjustments"].append(
            f"完成率仅{adherence:.0%}，建议减少每日计划时长"
        )
        if config.daily_study_hours > 6:
            config.daily_study_hours -= 1
            adjustments["adjustments"].append(
                f"每日学习时长调整为 {config.daily_study_hours} 小时"
            )

    # Redistribute time towards deficit subjects
    total_deficit = sum(compliance["subject_deficit"].values())
    if total_deficit > 0:
        for subject, deficit in compliance["subject_deficit"].items():
            if deficit > 0 and subject in _SUBJECT_WEIGHTS:
                # Increase weight for subjects with the most deficit
                bonus = 0.05
                adjustments["new_weights"][subject] = _SUBJECT_WEIGHTS[subject] + bonus
                adjustments["adjustments"].append(
                    f"{subject}: 增加{bonus:.0%}权重（累计落后{deficit // 60}h{deficit % 60}m）"
                )

        # Normalize weights so they sum to 1.0
        total = sum(adjustments["new_weights"].values())
        for k in adjustments["new_weights"]:
            adjustments["new_weights"][k] /= total

    store.save_config(config)
    return adjustments


def get_status(store: Store) -> dict[str, Any]:
    """Return a quick status summary for display."""
    today = date.today()
    plan = store.load_daily_plan(today)
    longterm = store.load_longterm_plan()
    config = store.load_config()

    done_tasks = sum(1 for t in plan.tasks if t.done)
    total_tasks = len(plan.tasks)
    pomodoro_count = len(plan.pomodoros)
    active = get_active_milestone(longterm)

    # Calculate days until exam
    try:
        exam = date.fromisoformat(config.exam_date)
        days_to_exam = (exam - today).days
    except ValueError:
        days_to_exam = -1

    # Streak
    streak = 0
    current = today
    while True:
        p = store.load_daily_plan(current)
        if p.reflection is not None:
            streak += 1
            current -= timedelta(days=1)
        else:
            break

    return {
        "date": today.isoformat(),
        "days_to_exam": days_to_exam,
        "tasks_done": done_tasks,
        "tasks_total": total_tasks,
        "pomodoros": pomodoro_count,
        "active_milestone": active.name if active else None,
        "streak": streak,
        "planned_minutes": plan.total_planned_minutes(),
        "actual_minutes": plan.total_actual_minutes(),
    }
