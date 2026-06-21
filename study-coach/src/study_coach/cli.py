"""CLI entry point for study-coach."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table

from . import examiner
from . import planner as planner_mod
from . import reporter
from . import supervisor
from . import tracker
from . import wrong_book as wb
from .models import Config, DailyPlan, LongtermPlan, Question, Task, TestResult
from .store import Store
from .syllabus import chapters

app = typer.Typer(
    name="study-coach",
    help="🎓 考研监督型 Agent — 制定计划、番茄钟、自测、进度报告",
    no_args_is_help=True,
)
console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _store() -> Store:
    return Store()


def _require_init(store: Store) -> Config:
    if not store.config_exists():
        console.print("[red]尚未初始化，请先运行 [bold]study-coach init[/bold][/red]")
        raise typer.Exit(1)
    return store.load_config()


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@app.command()
def init() -> None:
    """Initialize configuration for your exam preparation."""
    store = _store()

    if store.config_exists():
        if not Confirm.ask("已有配置，是否重新初始化？"):
            return

    console.print("[bold cyan]🎓 study-coach 初始化[/bold cyan]\n")

    exam_date = Prompt.ask("考试日期", default="2026-12-26")
    target_school = Prompt.ask("目标院校", default="待定")
    target_major = Prompt.ask("目标专业", default="待定")
    daily_hours = IntPrompt.ask("每天计划学习时长（小时）", default=8)

    config = Config(
        exam_date=exam_date,
        target_school=target_school,
        target_major=target_major,
        daily_study_hours=daily_hours,
    )
    store.save_config(config)

    # Initialize default long-term plan
    longterm = LongtermPlan.default_plan(exam_date)
    store.save_longterm_plan(longterm)

    console.print("\n[green]✓ 配置完成！[/green]")
    console.print(f"  考试日期: {exam_date}")
    console.print(f"  目标院校: {target_school}")
    console.print(f"  每日学习: {daily_hours}小时")
    console.print(f"  科目: {', '.join(config.subjects)}")
    console.print("\n[dim]运行 [bold]study-coach plan[/bold] 开始制定今日计划[/dim]")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@app.command()
def status() -> None:
    """Show current status overview."""
    store = _store()
    _require_init(store)

    info = supervisor.get_status(store)

    panel_text = []
    if info["days_to_exam"] >= 0:
        panel_text.append(f"[bold yellow]📅 距离考研: {info['days_to_exam']}天[/bold yellow]")
    if info["active_milestone"]:
        panel_text.append(f"🎯 当前阶段: [cyan]{info['active_milestone']}[/cyan]")

    panel_text.append(
        f"📊 今日任务: [green]{info['tasks_done']}[/green]/{info['tasks_total']}"
    )
    planned_h = info["planned_minutes"] // 60
    planned_m = info["planned_minutes"] % 60
    actual_h = info["actual_minutes"] // 60
    actual_m = info["actual_minutes"] % 60
    panel_text.append(f"⏱️  计划 {planned_h}h{planned_m:02d}m / 实际 {actual_h}h{actual_m:02d}m")
    panel_text.append(f"🍅 番茄钟: {info['pomodoros']}")
    panel_text.append(f"🔥 连续打卡: {info['streak']}天")

    console.print(Panel("\n".join(panel_text), title="study-coach 状态", border_style="cyan"))


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


@app.command()
def plan(
    week: bool = typer.Option(False, "--week", "-w", help="查看本周计划概览"),
    longterm: bool = typer.Option(False, "--longterm", "-l", help="查看/编辑长期里程碑"),
) -> None:
    """View or create today's study plan."""
    store = _store()
    _require_init(store)

    if longterm:
        _show_longterm(store)
        return

    if week:
        _show_week(store)
        return

    _show_or_create_daily(store)


def _show_longterm(store: Store) -> None:
    lt = store.load_longterm_plan()

    table = Table(title="🎯 长期规划")
    table.add_column("ID", style="dim")
    table.add_column("里程碑", style="bold")
    table.add_column("截止日期")
    table.add_column("科目")
    table.add_column("状态")

    for m in lt.milestones:
        status = "[green]✓ 完成[/green]" if m.completed else "[yellow]○ 进行中[/yellow]"
        try:
            d = date.fromisoformat(m.deadline)
            days_left = (d - date.today()).days
            deadline_str = f"{m.deadline} (剩余{days_left}天)"
        except ValueError:
            deadline_str = m.deadline

        table.add_row(m.id, m.name, deadline_str, ", ".join(m.subjects) or "全科", status)

    console.print(table)

    if Confirm.ask("\n是否标记某个里程碑完成？", default=False):
        mid = Prompt.ask("输入里程碑ID")
        if planner_mod.toggle_milestone(lt, mid):
            store.save_longterm_plan(lt)
            console.print("[green]✓ 已更新[/green]")
        else:
            console.print("[red]未找到该ID[/red]")


def _show_week(store: Store) -> None:
    today = date.today()
    start = today - timedelta(days=today.weekday())  # Monday

    table = Table(title=f"📅 本周计划 ({start.isoformat()} ~)")
    table.add_column("日期")
    table.add_column("任务数")
    table.add_column("已完成")
    table.add_column("时长")

    for i in range(7):
        d = start + timedelta(days=i)
        plan_obj = store.load_daily_plan(d)
        done = sum(1 for t in plan_obj.tasks if t.done)
        total = len(plan_obj.tasks)
        actual = plan_obj.total_actual_minutes()
        style = "bold" if d == today else ""
        table.add_row(
            f"[{style}]{d.isoformat()}[/{style}]" if style else d.isoformat(),
            str(total),
            str(done),
            f"{actual // 60}h{actual % 60:02d}m",
        )

    console.print(table)


def _show_or_create_daily(store: Store) -> None:
    today_plan = planner_mod.create_today_plan(store)

    if not today_plan.tasks:
        console.print("[yellow]今日暂无计划[/yellow]\n")
        _add_tasks_interactive(store, today_plan)
        return

    # Show today's plan
    table = Table(title=f"📋 今日计划 — {today_plan.date}")
    table.add_column("ID", style="dim")
    table.add_column("科目", style="cyan")
    table.add_column("内容")
    table.add_column("计划")
    table.add_column("实际")
    table.add_column("状态")

    for t in today_plan.tasks:
        status = "[green]✓[/green]" if t.done else "○"
        table.add_row(
            t.id,
            t.subject,
            t.content,
            f"{t.planned_minutes // 60}h{t.planned_minutes % 60:02d}m",
            f"{t.actual_minutes // 60}h{t.actual_minutes % 60:02d}m",
            status,
        )

        # Show knowledge points if available
        if t.knowledge_points:
            table.add_row(
                "",
                "",
                f"[dim]📚 今日知识点: {', '.join(t.knowledge_points[:5])}{'...' if len(t.knowledge_points) > 5 else ''}[/dim]",
                "",
                "",
                "",
            )

        # Show preview for tomorrow if available
        if t.preview_for_tomorrow:
            table.add_row(
                "",
                "",
                f"[dim]🔮 明日预习: {', '.join(t.preview_for_tomorrow[:5])}{'...' if len(t.preview_for_tomorrow) > 5 else ''}[/dim]",
                "",
                "",
                "",
            )

        # Add separator between tasks for readability
        table.add_section()

    console.print(table)

    # Offer actions
    console.print("\n[dim]操作: [bold]study-coach start <task_id>[/bold] 开始番茄钟")
    console.print("[dim]       [bold]study-coach done <task_id>[/bold] 标记完成")


def _add_tasks_interactive(store: Store, plan_obj: DailyPlan) -> None:
    """Interactively add tasks to a daily plan."""
    config = store.load_config()

    while True:
        console.print("\n[bold]添加新任务[/bold]")
        subject = Prompt.ask("科目", choices=config.subjects)
        content = Prompt.ask("内容描述")
        minutes = IntPrompt.ask("计划时长（分钟）", default=90)

        task = Task(subject=subject, content=content, planned_minutes=minutes)
        plan_obj.tasks.append(task)

        if not Confirm.ask("继续添加？", default=True):
            break

    store.save_daily_plan(plan_obj)
    console.print(f"\n[green]✓ 已添加 {len(plan_obj.tasks)} 个任务[/green]")


# ---------------------------------------------------------------------------
# start / stop (pomodoro)
# ---------------------------------------------------------------------------


@app.command()
def start(
    task_id: Optional[str] = typer.Argument(None, help="任务ID"),
    minutes: int = typer.Option(25, "--minutes", "-m", help="番茄钟时长（分钟）"),
) -> None:
    """Start a pomodoro timer for a task."""
    store = _store()
    _require_init(store)

    plan_obj = store.load_daily_plan()

    # If no task_id given, let user pick
    if task_id is None:
        undone = [t for t in plan_obj.tasks if not t.done]
        if not undone:
            console.print("[yellow]没有未完成的任务，请先添加计划[/yellow]")
            raise typer.Exit(0)

        console.print("[bold]选择任务:[/bold]")
        for i, t in enumerate(undone, 1):
            console.print(f"  {i}. [{t.id}] {t.subject} — {t.content}")

        choice = IntPrompt.ask("选择序号", default=1)
        if 1 <= choice <= len(undone):
            task = undone[choice - 1]
            task_id = task.id
        else:
            console.print("[red]无效选择[/red]")
            raise typer.Exit(1)

    task = plan_obj.task_by_id(task_id)
    if task is None:
        console.print(f"[red]未找到任务: {task_id}[/red]")
        raise typer.Exit(1)

    if task.done:
        console.print("[yellow]该任务已完成[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold cyan]🍅 开始番茄钟: {task.subject} — {task.content}[/bold cyan]")
    console.print(f"   时长: {minutes}分钟 | 任务ID: {task.id}\n")

    session = tracker.PomodoroSession(
        task_id=task.id,
        subject=task.subject,
        duration_minutes=minutes,
    )

    pomodoro = tracker.run_pomodoro(session)
    tracker.record_pomodoro(store, pomodoro)

    count = tracker.get_pomodoro_count_today(store)
    break_min, break_type = tracker.suggest_break(count)

    console.print(f"\n[green]✓ 番茄钟完成！今日已完成 {count} 个[/green]")
    console.print(f"[dim]建议{break_type}休息 {break_min} 分钟[/dim]")


@app.command()
def done(
    task_id: str = typer.Argument(..., help="任务ID"),
) -> None:
    """Mark a task as completed."""
    store = _store()
    _require_init(store)

    plan_obj = store.load_daily_plan()
    if planner_mod.complete_task(plan_obj, task_id):
        store.save_daily_plan(plan_obj)
        task = plan_obj.task_by_id(task_id)
        console.print(f"[green]✓ 任务完成: {task.content if task else task_id}[/green]")

        done_count = sum(1 for t in plan_obj.tasks if t.done)
        console.print(f"[dim]今日进度: {done_count}/{len(plan_obj.tasks)}[/dim]")
    else:
        console.print(f"[red]未找到任务: {task_id}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# checkin
# ---------------------------------------------------------------------------


@app.command()
def checkin() -> None:
    """Daily check-in: review the day and write a reflection."""
    store = _store()
    _require_init(store)

    plan_obj = store.load_daily_plan()

    if not plan_obj.tasks:
        console.print("[yellow]今日没有计划，请先 [bold]study-coach plan[/bold][/yellow]")
        raise typer.Exit(0)

    # Show today's summary
    summary = reporter.generate_daily_summary(plan_obj)
    console.print(summary)

    # Prompt reflection
    console.print("\n[bold]📝 今日反思[/bold]")
    reflection = Prompt.ask("今天学得怎么样？有什么收获和不足？")

    if Confirm.ask("是否记录各任务实际完成时长？", default=False):
        for t in plan_obj.tasks:
            actual = IntPrompt.ask(
                f"  {t.subject} — {t.content}（计划{t.planned_minutes}分钟）",
                default=t.actual_minutes,
            )
            t.actual_minutes = actual

    plan_obj.reflection = reflection
    store.save_daily_plan(plan_obj)

    done_count = sum(1 for t in plan_obj.tasks if t.done)
    console.print(
        f"\n[green]✓ 打卡成功！今日完成 {done_count}/{len(plan_obj.tasks)} 个任务[/green]"
    )


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@app.command()
def report(
    adjust: bool = typer.Option(False, "--adjust", "-a", help="根据进度调整后续计划"),
) -> None:
    """Generate a weekly progress report."""
    store = _store()
    _require_init(store)

    report_text = reporter.generate_weekly_report(store)

    # Save report
    today = date.today()
    filename = f"{today.isoformat()}-weekly.md"
    path = store.save_report(filename, report_text)

    console.print(report_text)
    console.print(f"\n[dim]报告已保存至: {path}[/dim]")

    if adjust:
        adjustments = supervisor.adjust_plan(store)
        console.print("\n[bold cyan]📈 计划调整建议[/bold cyan]")
        console.print(f"  完成率: {adjustments['adherence_rate']:.0%}")
        for a in adjustments["adjustments"]:
            console.print(f"  • {a}")


# ---------------------------------------------------------------------------
# yearly / monthly / review / drift — plan cascade & knowledge-point review
# ---------------------------------------------------------------------------


def _fmt_weights(weights: dict[str, float]) -> str:
    return "  ".join(f"{k} {v:.0%}" for k, v in weights.items()) if weights else "—"


@app.command()
def yearly(
    regenerate: bool = typer.Option(
        False, "--regenerate", help="按考试日期重建默认阶段"
    ),
) -> None:
    """查看年度计划（阶段划分 + 各阶段权重）。"""
    store = _store()
    _require_init(store)

    if regenerate:
        from .models import YearlyPlan
        config = store.load_config()
        yp = YearlyPlan.default_plan(config.exam_date, config.subjects)
        store.save_yearly_plan(yp)
        console.print("[green]✓ 已按考试日期重建年度阶段[/green]")

    yp = store.load_yearly_plan()
    table = Table(title=f"📅 年度计划（考试 {yp.exam_date}）")
    table.add_column("阶段", style="bold")
    table.add_column("起")
    table.add_column("止")
    table.add_column("侧重")
    table.add_column("权重")

    for p in yp.phases:
        table.add_row(
            p.name,
            p.start,
            p.end,
            ", ".join(p.focus_subjects) or "—",
            _fmt_weights(p.weight_overrides),
        )

    console.print(table)
    if yp.target_scores:
        scores = "  ".join(f"{k} {v}" for k, v in yp.target_scores.items() if v)
        if scores:
            console.print(f"[dim]目标分数: {scores}[/dim]")


@app.command()
def monthly(
    month: str = typer.Option("", "--month", "-m", help="YYYY-MM，默认本月"),
    generate: bool = typer.Option(
        False, "--generate", "-g", help="生成/重新生成月度计划"
    ),
) -> None:
    """查看或生成本月计划（阶段权重 + 目标）。"""
    store = _store()
    _require_init(store)

    target = month or date.today().strftime("%Y-%m")

    if generate:
        plan = planner_mod.generate_monthly_plan(store, target)
        source = plan.generated_from.get("source", "")
        console.print(
            f"[green]✓ 已生成 {target} 月度计划[/green] [dim](来源: {source})[/dim]"
        )

    plan = store.load_monthly_plan(target)
    if plan is None:
        console.print(f"[yellow]{target} 暂无月度计划，用 -g 生成[/yellow]")
        return

    console.print(
        f"[bold cyan]🗓️  {plan.month} 月度计划[/bold cyan] "
        f"[dim]阶段: {plan.phase or '—'}[/dim]"
    )
    console.print(f"  权重: {_fmt_weights(plan.subject_weights)}")
    if plan.goals:
        console.print("  目标:")
        for g in plan.goals:
            console.print(f"    • [{g.subject}] {g.goal}")
    rationale = plan.generated_from.get("rationale", "")
    if rationale:
        console.print(f"  [dim]说明: {rationale}[/dim]")


@app.command()
def review(
    budget: int = typer.Option(40, "--budget", "-b", help="复习时间预算（分钟）"),
    agent: bool = typer.Option(False, "--agent", help="用 ReviewPicker agent 精选"),
) -> None:
    """按知识点弱点抽取今日复查错题。"""
    store = _store()
    _require_init(store)

    if agent:
        res = wb.pick_reviews_with_agent(store, time_budget_minutes=budget)
        console.print(
            f"[dim]来源: {res['source']} | {res['rationale']}[/dim]"
        )
        items = res["items"]
    else:
        res = wb.pick_reviews_kp_aware(store, time_budget_minutes=budget)
        items = res["items"]

    if not items:
        console.print("[yellow]暂无可复查的错题[/yellow]")
        return

    table = Table(title=f"📝 今日复查（{res['count']} 题 / {budget} 分钟）")
    table.add_column("ID", style="dim")
    table.add_column("科目", style="cyan")
    table.add_column("知识点")
    table.add_column("掌握度")
    table.add_column("到期")
    table.add_column("紧急度", justify="right")

    for it in items:
        q = it["question"]
        kp = ", ".join(q.get("knowledge_points", [])) or "—"
        due = "●" if it.get("due") else "○"
        console_kp = f"{it.get('kp_mastery', 0):.0%}" if "kp_mastery" in it else "—"
        table.add_row(
            q["id"],
            q.get("subject", ""),
            kp,
            console_kp,
            due,
            f"{it.get('score', 0):.2f}",
        )

    console.print(table)
    console.print("[dim]用 [bold]study-coach review --agent[/bold] 让 AI 精选排序[/dim]")


@app.command()
def drift() -> None:
    """检测计划漂移信号（触发则建议重新生成月度计划）。"""
    store = _store()
    _require_init(store)

    result = supervisor.detect_drift(store)
    if not result["signals"]:
        console.print("[green]✓ 未检测到漂移信号，计划节奏正常[/green]")
        return

    console.print("[bold yellow]⚠️  检测到漂移信号[/bold yellow]\n")
    table = Table(title="漂移信号")
    table.add_column("类型", style="cyan")
    table.add_column("严重度")
    table.add_column("说明")
    sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for sig in result["signals"]:
        table.add_row(
            sig["type"],
            sev_icon.get(sig["severity"], "⚪") + " " + sig["severity"],
            sig["detail"],
        )
    console.print(table)
    console.print(
        "\n[dim]建议运行 [bold]study-coach monthly -g[/bold] 重新生成月度计划[/dim]"
    )


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------


@app.command()
def test(
    subject: str = typer.Argument(..., help="科目名称"),
    count: int = typer.Option(5, "--count", "-n", help="题目数量"),
    add: bool = typer.Option(False, "--add", help="添加题目到题库"),
) -> None:
    """Self-test: quiz yourself on a subject."""
    store = _store()
    _require_init(store)

    if add:
        _add_questions_interactive(store, subject)
        return

    questions = examiner.pick_random_questions(store, subject, count)

    if not questions:
        console.print(f"[yellow]{subject} 题库为空，请先用 [bold]study-coach test {subject} --add[/bold] 添加题目[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold cyan]📝 {subject} 自测 — {len(questions)}题[/bold cyan]\n")

    correct = 0
    weak_topics: list[str] = []

    for i, q in enumerate(questions, 1):
        console.print(f"[bold]Q{i}[/bold] ({q.topic}): {q.question_text}")
        user_answer = Prompt.ask("你的答案")

        console.print(f"[dim]参考答案: {q.answer}[/dim]")
        is_correct = Confirm.ask("回答正确？", default=True)

        if is_correct:
            correct += 1
        else:
            if q.topic not in weak_topics:
                weak_topics.append(q.topic)
            console.print(f"[red]✗ 错误[/red]")
        console.print()

    # Save result
    result = TestResult(
        date=date.today().isoformat(),
        subject=subject,
        total_questions=len(questions),
        correct=correct,
        weak_topics=weak_topics,
    )
    examiner.save_test_result(store, result)

    score = correct / len(questions)
    color = "green" if score >= 0.7 else "yellow" if score >= 0.5 else "red"
    console.print(f"[{color}]得分: {correct}/{len(questions)} ({score:.0%})[/{color}]")

    if weak_topics:
        console.print(f"[yellow]薄弱知识点: {', '.join(weak_topics)}[/yellow]")


def _add_questions_interactive(store: Store, subject: str) -> None:
    """Interactively add questions to the question bank."""
    console.print(f"[bold cyan]📝 添加 {subject} 题目[/bold cyan]\n")

    # Load syllabus and show chapter hints for the selected subject
    syllabus = store.load_syllabus()
    subject_chapters = chapters(syllabus, subject) if syllabus else []
    if subject_chapters:
        # Show first 10 chapters as hints, truncated if too many
        hint = subject_chapters[:10]
        console.print(f"[dim]可选章节：{' | '.join(hint)}{'...' if len(subject_chapters) > 10 else ''}[/dim]\n")

    count = 0
    while True:
        topic = Prompt.ask("知识点/章节")
        question_text = Prompt.ask("题目")
        answer = Prompt.ask("参考答案")
        difficulty = IntPrompt.ask("难度 (1-5)", default=3)

        examiner.add_question(
            store,
            subject=subject,
            topic=topic,
            question_text=question_text,
            answer=answer,
            difficulty=difficulty,
        )
        count += 1

        if not Confirm.ask("继续添加？", default=True):
            break

    console.print(f"\n[green]✓ 已添加 {count} 道题目[/green]")


@app.command()
def match(
    text: str = typer.Argument(..., help="要匹配的文本内容"),
    subject: str = typer.Option(None, "--subject", "-s", help="筛选科目: 高等数学/线性代数/概率论与数理统计"),
    formulas: bool = typer.Option(False, "--formulas", "-f", help="显示相关公式"),
) -> None:
    """测试数学知识点匹配功能。"""
    from .math_matcher import get_formulas_for_text, get_kp_summary_for_text, load_math_kps, match_kps

    kps = load_math_kps()
    if not kps:
        console.print("[red]未找到知识点索引，请检查 data/math_knowledge_points.json[/red]")
        raise typer.Exit(1)

    subject_filter = subject
    matched = match_kps(text, kps=kps, subject=subject_filter)

    if not matched:
        console.print(f"[yellow]未找到匹配的知识点[/yellow]")
        return

    table = Table(title=f"📚 匹配结果 ({len(matched)} 个知识点)")
    table.add_column("ID", style="dim")
    table.add_column("知识点", style="bold cyan")
    table.add_column("科目")
    table.add_column("章节")
    table.add_column("难度", justify="center")
    table.add_column("描述")

    for kp in matched:
        table.add_row(
            kp.id,
            kp.name,
            kp.subject,
            kp.chapter,
            str(kp.difficulty),
            kp.description[:30] + "..." if len(kp.description) > 30 else kp.description,
        )

    console.print(table)

    if formulas:
        formula_list = get_formulas_for_text(text, kps=kps, subject=subject_filter)
        if formula_list:
            console.print("\n[bold]📝 相关公式:[/bold]")
            for i, f in enumerate(formula_list[:5], 1):
                console.print(f"  {i}. {f}")


# ---------------------------------------------------------------------------
# room — launch online study room web server
# ---------------------------------------------------------------------------


@app.command()
def room(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="监听地址"),
    port: int = typer.Option(8900, "--port", "-p", help="监听端口"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="自动打开浏览器"),
) -> None:
    """Launch the online study room web server."""
    import webbrowser

    console.print(f"[bold cyan]🏠 启动线上自习室[/bold cyan]")
    console.print(f"  地址: http://{host}:{port}")
    console.print(f"  按 Ctrl+C 停止\n")

    if open_browser:
        webbrowser.open(f"http://{host}:{port}")

    from .web.server import run_server
    run_server(host=host, port=port)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    app()
