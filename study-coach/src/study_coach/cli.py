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
from . import school_advisor as sa
from . import supervisor
from . import tracker
from .models import Config, DailyPlan, LongtermPlan, Question, Task, TestResult
from .store import Store

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


# ---------------------------------------------------------------------------
# school — TEMPORARY: delete after choosing your target school
# ---------------------------------------------------------------------------

school_app = typer.Typer(
    name="school",
    help="🏫 [临时] 择校辅助 — 用完可删除 (school_advisor.py + 此命令组)",
    no_args_is_help=True,
)
app.add_typer(school_app, name="school")


@school_app.command("list")
def school_list(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="地区: 北京/华东/华南/华中/西北"),
    direction: Optional[str] = typer.Option(None, "--direction", "-d", help="方向: embodied/llm/robotics/ml/cv"),
    tier: Optional[int] = typer.Option(None, "--tier", "-t", help="梯队: 1=顶尖 2=强势 3=中坚"),
    diff: Optional[int] = typer.Option(None, "--diff", help="最高难度: 1=极难 2=较难 3=中等"),
    require_408: bool = typer.Option(False, "--408", help="仅显示接受408统考的"),
) -> None:
    """List schools with optional filters."""
    schools = sa.filter_schools(
        region=region,
        direction=direction,
        tier=tier,
        difficulty_max=diff,
        require_408=require_408,
    )

    if not schools:
        console.print("[yellow]没有匹配的学校，试试放宽条件[/yellow]")
        return

    table = Table(title=f"🏫 院校列表 ({len(schools)}所)")
    table.add_column("院校", style="bold")
    table.add_column("地区")
    table.add_column("梯队")
    table.add_column("难度")
    table.add_column("408")
    table.add_column("方向")
    table.add_column("亮点")

    for s in schools:
        dirs = "、".join(sa.DIRECTION_LABELS.get(d, d) for d in s.directions)
        tier_label = sa.TIER_LABELS.get(s.tier, str(s.tier))
        diff_label = sa.DIFFICULTY_LABELS.get(s.difficulty, str(s.difficulty))
        exam_408 = "[green]✓[/green]" if s.exam_cs408 else "[dim]✗[/dim]"
        features = s.features[0] if s.features else ""
        table.add_row(s.name, s.region, tier_label, diff_label, exam_408, dirs, features)

    console.print(table)


@school_app.command("compare")
def school_compare(
    names: str = typer.Argument(..., help="院校名，逗号分隔，如: 浙江大学,哈尔滨工业大学(深圳)"),
) -> None:
    """Compare specific schools side by side."""
    name_list = [n.strip() for n in names.split(",")]
    schools = sa.compare_schools(name_list)

    if not schools:
        console.print("[red]未找到匹配的院校，请检查名称[/red]")
        return

    # Overview table
    table = Table(title="🏫 院校对比")
    table.add_column("维度", style="bold cyan")

    for s in schools:
        table.add_column(s.name)

    rows = [
        ("地区", [s.region for s in schools]),
        ("梯队", [sa.TIER_LABELS.get(s.tier, "") for s in schools]),
        ("难度", [sa.DIFFICULTY_LABELS.get(s.difficulty, "") for s in schools]),
        ("数学", [s.exam_math for s in schools]),
        ("408", ["✓" if s.exam_cs408 else "✗" for s in schools]),
        ("方向", ["、".join(sa.DIRECTION_LABELS.get(d, d) for d in s.directions) for s in schools]),
        ("实验室", [", ".join(s.labs[:2]) + ("..." if len(s.labs) > 2 else "") for s in schools]),
    ]

    for label, values in rows:
        table.add_row(label, *values)

    console.print(table)

    # Features detail
    for s in schools:
        console.print(f"\n[bold]{s.name}[/bold]")
        for f in s.features:
            console.print(f"  • {f}")
        if s.labs:
            console.print(f"  [dim]相关实验室: {', '.join(s.labs)}[/dim]")


@school_app.command("recommend")
def school_recommend(
    primary: str = typer.Option("embodied", "--primary", "-p", help="主方向: embodied/llm/robotics/ml/cv"),
    secondary: str = typer.Option("llm", "--secondary", "-s", help="副方向"),
    max_diff: int = typer.Option(3, "--max-diff", help="最高难度 1-3"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="偏好地区"),
    top_n: int = typer.Option(5, "--top", "-n", help="推荐数量"),
) -> None:
    """Get personalized school recommendations based on your profile."""
    console.print("[bold cyan]🎓 择校推荐[/bold cyan]")
    console.print(f"  主方向: {sa.DIRECTION_LABELS.get(primary, primary)}")
    console.print(f"  副方向: {sa.DIRECTION_LABELS.get(secondary, secondary)}")
    console.print(f"  408统考偏好: 是")
    console.print(f"  难度上限: {sa.DIFFICULTY_LABELS.get(max_diff, str(max_diff))}")
    if region:
        console.print(f"  偏好地区: {region}")
    console.print()

    results = sa.recommend(
        primary_direction=primary,
        secondary_direction=secondary,
        prefer_408=True,
        max_difficulty=max_diff,
        preferred_region=region,
        top_n=top_n,
    )

    if not results:
        console.print("[yellow]没有匹配的推荐，试试放宽条件[/yellow]")
        return

    table = Table(title=f"🎯 推荐结果 (Top {len(results)})")
    table.add_column("排名", style="bold")
    table.add_column("院校", style="bold")
    table.add_column("匹配度", style="green")
    table.add_column("难度")
    table.add_column("地区")
    table.add_column("方向")
    table.add_column("推荐理由")

    max_score = results[0][1] if results else 1.0

    for rank, (s, score) in enumerate(results, 1):
        match_pct = (score / max_score * 100) if max_score > 0 else 0
        dirs = "、".join(sa.DIRECTION_LABELS.get(d, d) for d in s.directions[:3])
        diff_label = sa.DIFFICULTY_LABELS.get(s.difficulty, str(s.difficulty))

        # Determine recommendation reason
        reasons = []
        if primary in s.directions and secondary in s.directions:
            reasons.append("双方向匹配")
        elif primary in s.directions:
            reasons.append("主方向匹配")
        if s.exam_cs408:
            reasons.append("408统考")
        if s.difficulty == 3:
            reasons.append("上岸友好")

        reason_str = "、".join(reasons)
        table.add_row(
            str(rank),
            s.name,
            f"{match_pct:.0f}%",
            diff_label,
            s.region,
            dirs,
            reason_str,
        )

    console.print(table)

    # Detailed advice for top recommendation
    if results:
        top_school = results[0][0]
        console.print(f"\n[bold green]🏆 首选推荐: {top_school.name}[/bold green]")
        for f in top_school.features:
            console.print(f"  • {f}")
        console.print(f"  [dim]实验室: {', '.join(top_school.labs)}[/dim]")
        console.print(f"\n[dim]用 [bold]study-coach school compare {top_school.name},{results[1][0].name if len(results) > 1 else ''}[/bold] 深入对比[/dim]")


@school_app.command("interactive")
def school_interactive() -> None:
    """Interactive school selection wizard."""
    console.print("[bold cyan]🎓 择校向导\n[/bold cyan]")

    # Step 1: direction priorities
    console.print("[bold]Step 1: 你的方向偏好[/bold]")
    dir_options = list(sa.DIRECTION_LABELS.keys())
    for i, d in enumerate(dir_options, 1):
        console.print(f"  {i}. {sa.DIRECTION_LABELS[d]}")
    primary_idx = IntPrompt.ask("主方向序号", default=1)
    secondary_idx = IntPrompt.ask("副方向序号", default=2)
    primary = dir_options[primary_idx - 1]
    secondary = dir_options[secondary_idx - 1]

    # Step 2: difficulty tolerance
    console.print("\n[bold]Step 2: 难度接受度[/bold]")
    console.print("  1. 只冲顶尖（清北中科院）")
    console.print("  2. 可以较难（浙大上交南大等）")
    console.print("  3. 追求上岸（北航华科中大等）")
    max_diff = IntPrompt.ask("最高难度", default=3)

    # Step 3: region preference
    console.print("\n[bold]Step 3: 地区偏好[/bold]")
    console.print("  北京 / 华东 / 华南 / 华中 / 西北 / 无偏好")
    region_input = Prompt.ask("偏好地区（留空=不限）", default="")
    region = region_input if region_input and region_input != "无偏好" else None

    # Step 4: recommend
    console.print()
    results = sa.recommend(
        primary_direction=primary,
        secondary_direction=secondary,
        prefer_408=True,
        max_difficulty=max_diff,
        preferred_region=region,
        top_n=5,
    )

    if not results:
        console.print("[yellow]没有匹配推荐，请放宽条件重试[/yellow]")
        return

    table = Table(title="🎯 为你推荐的院校")
    table.add_column("排名", style="bold")
    table.add_column("院校", style="bold")
    table.add_column("难度")
    table.add_column("地区")
    table.add_column("方向")
    table.add_column("亮点")

    for rank, (s, score) in enumerate(results, 1):
        dirs = "、".join(sa.DIRECTION_LABELS.get(d, d) for d in s.directions[:3])
        diff_label = sa.DIFFICULTY_LABELS.get(s.difficulty, str(s.difficulty))
        highlight = s.features[0] if s.features else ""
        table.add_row(str(rank), s.name, diff_label, s.region, dirs, highlight)

    console.print(table)

    # Step 5: save to config
    if Confirm.ask("\n是否将某个院校设为目标？", default=True):
        school_names = [s.name for s, _ in results]
        console.print(f"可选: {', '.join(school_names)}")
        chosen = Prompt.ask("输入院校全名")
        if chosen in school_names:
            store = _store()
            config = store.load_config()
            config.target_school = chosen
            store.save_config(config)
            console.print(f"[green]✓ 目标院校已设为: {chosen}[/green]")
            console.print("[dim]运行 [bold]study-coach school clean[/bold] 可删除择校模块[/dim]")
        else:
            console.print(f"[yellow]未找到 {chosen}，可稍后用 [bold]study-coach init[/bold] 修改[/yellow]")


@school_app.command("clean")
def school_clean() -> None:
    """Show instructions to remove the school advisor module."""
    console.print("[bold yellow]择校模块清理指南[/bold yellow]\n")
    console.print("择校完成后，手动执行以下步骤:\n")
    console.print("  1. 删除文件:")
    console.print("     [dim]rm src/study_coach/school_advisor.py[/dim]")
    console.print()
    console.print("  2. 编辑 [bold]src/study_coach/cli.py[/bold]:")
    console.print("     - 删除 [dim]from . import school_advisor as sa[/dim]")
    console.print("     - 删除 [dim]school_app[/dim] 及其下所有 [dim]@school_app.command[/dim] 函数")
    console.print("     - 删除 [dim]app.add_typer(school_app, ...)[/dim]")
    console.print()
    console.print("[green]目标院校已保存在 config.json 中，不受删除影响。[/green]")


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
