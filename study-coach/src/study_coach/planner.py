"""Plan management: long-term milestones and daily task planning."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from .kp_index import KnowledgePointStat, build_kp_index, rank_weak_kps
from .models import (
    Config,
    DailyPlan,
    LongtermPlan,
    Milestone,
    MonthlyPlan,
    Task,
    YearlyPlan,
)
from .skincare import build_skincare_tasks
from .store import Store
from .wrong_book import REVIEW_MINUTES_PER_ITEM, pick_reviews_kp_aware


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

# Time carved out of the daily study budget for wrong-question review. Sized so a
# typical session surfaces ~5 cards without crowding out new-material study.
REVIEW_BUDGET_DEFAULT_MINUTES = 40


# ---------------------------------------------------------------------------
# Plan cascade: yearly -> monthly weights
# ---------------------------------------------------------------------------


def derive_monthly_weights(
    yearly: YearlyPlan,
    month: str,
    config: Config,
    compliance: dict[str, Any] | None = None,
    kp_index: list[KnowledgePointStat] | None = None,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Deterministic baseline for a month's subject weights.

    Anchors on the yearly phase that covers the month, then nudges toward
    subjects with accumulated time deficit or weak knowledge points. Returns
    the normalized weights and an audit dict describing how they were derived.
    """
    try:
        ref_date = date.fromisoformat(f"{month}-01")
    except ValueError:
        ref_date = date.today()

    phase = yearly.phase_for_date(ref_date)
    if phase and phase.weight_overrides:
        base = {
            s: w for s, w in phase.weight_overrides.items() if s in config.subjects
        }
    else:
        base = {s: _SUBJECT_WEIGHTS.get(s, 0.0) for s in config.subjects}
    if not base:
        base = dict(_SUBJECT_WEIGHTS)

    nudges: dict[str, float] = {s: 0.0 for s in base}

    # Deficit nudge: redistribute a bounded share toward behind-schedule subjects.
    if compliance:
        deficit = compliance.get("subject_deficit", {}) or {}
        total_deficit = sum(deficit.values())
        if total_deficit > 0:
            for s in base:
                share = deficit.get(s, 0) / total_deficit
                nudges[s] += 0.15 * share

    # Knowledge-point weakness nudge: subjects with weaker tagged KPs get a boost.
    if kp_index:
        per_subject: dict[str, list[float]] = {}
        for stat in kp_index:
            per_subject.setdefault(stat.subject, []).append(stat.mastery_level)
        for s in base:
            levels = per_subject.get(s)
            if levels:
                weakness = 1.0 - (sum(levels) / len(levels))
                nudges[s] += 0.10 * weakness

    adjusted = {s: max(base[s] * (1.0 + nudges[s]), 0.01) for s in base}
    total = sum(adjusted.values())
    normalized = {s: round(adjusted[s] / total, 4) for s in adjusted}

    audit = {
        "phase": phase.name if phase else "",
        "base": {s: round(w, 4) for s, w in base.items()},
        "nudges": {s: round(n, 4) for s, n in nudges.items()},
    }
    return normalized, audit


def generate_monthly_plan(
    store: Store, month: str | None = None
) -> MonthlyPlan:
    """Build (and persist) a month's plan from the yearly cascade + recent signals.

    Computes the deterministic baseline, then asks the Planner agent to refine
    weights/goals. The agent falls back to the baseline when AI is unavailable,
    so a valid plan is always produced and persisted.
    """
    # Lazy imports avoid the planner<->supervisor and planner<->ai cycles at load.
    from .ai import agent_plan_monthly
    from .supervisor import check_compliance

    if month is None:
        month = date.today().strftime("%Y-%m")

    config = store.load_config()
    yearly = store.load_yearly_plan()
    compliance = check_compliance(store, days=30)
    questions = store.load_wrong_questions()
    kp_index = build_kp_index(questions)

    baseline_weights, audit = derive_monthly_weights(
        yearly, month, config, compliance, kp_index
    )
    weak_kps = [s.to_dict() for s in rank_weak_kps(kp_index, limit=5)]

    proposal = agent_plan_monthly(
        {
            "month": month,
            "phase": audit["phase"],
            "subjects": config.subjects,
            "adherence_rate": compliance.get("adherence_rate"),
            "subject_deficit": compliance.get("subject_deficit"),
            "top_weak_kps": weak_kps,
            "baseline_weights": baseline_weights,
        }
    )

    goals = [MonthlyGoal(subject=g.get("subject", ""), goal=g.get("goal", ""))
             for g in proposal.get("goals", [])]

    plan = MonthlyPlan(
        month=month,
        phase=audit["phase"],
        subject_weights=proposal["subject_weights"],
        goals=goals,
        generated_at=date.today().isoformat(),
        generated_from={
            "source": proposal["source"],
            "rationale": proposal["rationale"],
            "base": audit["base"],
            "nudges": audit["nudges"],
            "adherence_rate": compliance.get("adherence_rate"),
            "subject_deficit": compliance.get("subject_deficit"),
            "top_weak_kps": weak_kps,
        },
    )
    store.save_monthly_plan(plan)
    return plan


def suggest_daily_tasks(
    config: Config,
    longterm: LongtermPlan,
    yesterday: DailyPlan | None = None,
    weights: dict[str, float] | None = None,
    review_load_minutes: int = 0,
) -> list[Task]:
    """Generate suggested tasks for today based on config and milestones.

    weights: per-subject allocation from the monthly plan. When None the static
    phase defaults (_SUBJECT_WEIGHTS) are used, preserving prior behavior.
    review_load_minutes: time already reserved for wrong-question review, carved
    out of the new-material budget so the daily total still fits the configured
    study hours.
    """
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

    carried_minutes = sum(t.planned_minutes for t in tasks)
    remaining = total_minutes - carried_minutes - review_load_minutes

    allocation = weights if weights else _SUBJECT_WEIGHTS

    if remaining > 0:
        for subject, weight in allocation.items():
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
    review_budget_minutes: int = REVIEW_BUDGET_DEFAULT_MINUTES,
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

        # The daily entry point drives the cascade: when this month has no plan
        # yet, generate one so the agent + phase weights actually apply. The
        # load==None check is the idempotent gate — generate_monthly_plan
        # persists, so subsequent daily generations skip the agent entirely.
        month_str = date.today().strftime("%Y-%m")
        monthly = store.load_monthly_plan(month_str)
        if monthly is None:
            monthly = generate_monthly_plan(store, month_str)
        weights = monthly.subject_weights if monthly else None

        # Knowledge-point-driven review selection: weakest KPs surface first.
        review_pick = pick_reviews_kp_aware(store, time_budget_minutes=review_budget_minutes)
        review_load = review_pick["count"] * REVIEW_MINUTES_PER_ITEM

        tasks = suggest_daily_tasks(
            config,
            longterm,
            yesterday,
            weights=weights,
            review_load_minutes=review_load,
        )

        # Surface the review session as an explicit task so it is visible and
        # counts toward the daily budget.
        if review_pick["count"]:
            tasks.append(
                Task(
                    subject="复习",
                    content=f"错题复查 {review_pick['count']} 题（按知识点弱点）",
                    planned_minutes=review_load,
                )
            )

        # Lifestyle routines (e.g. skincare) are appended after study
        # allocation so they never draw from the study-hour budget.
        tasks.extend(build_skincare_tasks(store, date.today()))

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
