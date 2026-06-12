"""Progress reporting: daily summaries and weekly reports."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .models import Config, DailyPlan, LongtermPlan, TestResult
from .planner import check_milestones, get_active_milestone
from .store import Store


def generate_daily_summary(plan: DailyPlan) -> str:
    """Generate a short text summary of a daily plan."""
    total_tasks = len(plan.tasks)
    done_tasks = sum(1 for t in plan.tasks if t.done)
    planned_min = plan.total_planned_minutes()
    actual_min = plan.total_actual_minutes()
    pomodoro_count = len(plan.pomodoros)

    lines = [
        f"## 📊 每日总结 — {plan.date}",
        "",
        f"- 任务完成: **{done_tasks}/{total_tasks}** ({plan.completion_rate():.0%})",
        f"- 计划时长: **{planned_min // 60}h{planned_min % 60:02d}m**",
        f"- 实际时长: **{actual_min // 60}h{actual_min % 60:02d}m**",
        f"- 番茄钟数: **{pomodoro_count}**",
    ]

    if plan.reflection:
        lines.extend(["", f"> {plan.reflection}"])

    # Per-subject breakdown
    subjects: dict[str, dict[str, int]] = {}
    for t in plan.tasks:
        if t.subject not in subjects:
            subjects[t.subject] = {"planned": 0, "actual": 0, "done": 0, "total": 0}
        subjects[t.subject]["planned"] += t.planned_minutes
        subjects[t.subject]["actual"] += t.actual_minutes
        subjects[t.subject]["total"] += 1
        if t.done:
            subjects[t.subject]["done"] += 1

    if subjects:
        lines.extend(["", "### 各科目明细", "", "| 科目 | 计划 | 实际 | 完成 |", "|------|------|------|------|"])
        for subj, data in subjects.items():
            lines.append(
                f"| {subj} | {data['planned'] // 60}h{data['planned'] % 60:02d}m "
                f"| {data['actual'] // 60}h{data['actual'] % 60:02d}m "
                f"| {data['done']}/{data['total']} |"
            )

    return "\n".join(lines)


def generate_weekly_report(
    store: Store,
    end_date: date | None = None,
) -> str:
    """Generate a weekly progress report covering the last 7 days."""
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(days=6)

    config = store.load_config()
    longterm = store.load_longterm_plan()
    plans = store.load_daily_plans_range(start_date, end_date)
    test_results = store.load_test_results()

    # Filter test results to this week
    week_str = f"{start_date.isoformat()} ~ {end_date.isoformat()}"
    week_tests = [
        r for r in test_results if start_date.isoformat() <= r.date <= end_date.isoformat()
    ]

    # Aggregate stats
    total_planned = sum(p.total_planned_minutes() for p in plans)
    total_actual = sum(p.total_actual_minutes() for p in plans)
    total_pomodoros = sum(len(p.pomodoros) for p in plans)
    days_with_plans = len(plans)
    total_tasks = sum(len(p.tasks) for p in plans)
    done_tasks = sum(sum(1 for t in p.tasks if t.done) for p in plans)

    # Per-subject aggregation
    subject_time: dict[str, int] = {}
    for p in plans:
        for t in p.tasks:
            subject_time[t.subject] = subject_time.get(t.subject, 0) + t.actual_minutes

    # Streak calculation
    streak = _calculate_streak(store)

    # Milestone status
    active = get_active_milestone(longterm)
    milestone_alerts = check_milestones(longterm)

    # Build report
    lines = [
        f"# 📈 周报 — {week_str}",
        "",
        "## 总览",
        "",
        f"- 有计划天数: **{days_with_plans}/7**",
        f"- 任务完成: **{done_tasks}/{total_tasks}**",
        f"- 计划总时长: **{total_planned // 60}h{total_planned % 60:02d}m**",
        f"- 实际总时长: **{total_actual // 60}h{total_actual % 60:02d}m**",
        f"- 番茄钟总数: **{total_pomodoros}**",
        f"- 连续打卡: **{streak}天**",
        "",
        "## 各科目时间分布",
        "",
        "| 科目 | 实际时长 | 占比 |",
        "|------|----------|------|",
    ]

    for subj, minutes in sorted(subject_time.items(), key=lambda x: -x[1]):
        pct = (minutes / total_actual * 100) if total_actual > 0 else 0
        lines.append(f"| {subj} | {minutes // 60}h{minutes % 60:02d}m | {pct:.1f}% |")

    if active:
        lines.extend([
            "",
            "## 当前阶段",
            "",
            f"- 里程碑: **{active.name}**",
            f"- 截止: **{active.deadline}**",
            f"- 涉及科目: {', '.join(active.subjects) or '全科'}",
        ])

    if milestone_alerts:
        lines.extend(["", "## ⚠️ 里程碑提醒", ""])
        for a in milestone_alerts:
            status_icon = {"overdue": "🔴", "urgent": "🟡", "approaching": "🟠"}.get(
                a["status"], "⚪"
            )
            lines.append(f"- {status_icon} {a['milestone']}: 剩余{a['days']}天")

    if week_tests:
        lines.extend(["", "## 📝 本周自测", "", "| 日期 | 科目 | 得分 | 薄弱点 |", "|------|------|------|--------|"])
        for r in week_tests:
            lines.append(f"| {r.date} | {r.subject} | {r.score:.0%} | {', '.join(r.weak_topics) or '—'} |")

    # Daily details
    lines.extend(["", "## 每日明细", ""])
    for p in plans:
        done = sum(1 for t in p.tasks if t.done)
        total = len(p.tasks)
        actual = p.total_actual_minutes()
        lines.append(f"- **{p.date}**: {done}/{total} 任务, {actual // 60}h{actual % 60:02d}m")

    return "\n".join(lines)


def _calculate_streak(store: Store) -> int:
    """Calculate the current consecutive check-in streak."""
    streak = 0
    today = date.today()
    current = today

    while True:
        plan = store.load_daily_plan(current)
        if plan.reflection is not None:
            streak += 1
            current -= timedelta(days=1)
        else:
            break

    return streak
