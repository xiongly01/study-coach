"""FastAPI server: online study room with real-time timer, plan display, and wrong book."""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import wrong_book as wb
from ..ai import is_api_key_configured
from ..examiner import (
    add_question,
    get_questions_by_subject,
    get_weak_topics,
    pick_random_questions,
    save_test_result,
)
from ..models import (
    REVIEW_INTERVALS,
    Question,
    ReviewRecord,
    TestResult,
    WrongQuestion,
    _gen_id,
)
from ..planner import (
    add_task_to_plan,
    check_milestones,
    create_today_plan,
    generate_monthly_plan,
    suggest_daily_tasks,
    toggle_milestone,
)
from ..reporter import generate_weekly_report
from ..store import Store
from ..supervisor import (
    adjust_plan,
    check_compliance,
    detect_drift,
    get_status as _get_status,
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="study-coach")

# Serve uploaded images and static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global state: current timer sessions keyed by a simple id
_active_sessions: dict[str, dict[str, Any]] = {}


def _store() -> Store:
    return Store()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# API: Config
# ---------------------------------------------------------------------------


@app.get("/api/config")
async def get_config():
    store = _store()
    if not store.config_exists():
        return {"initialized": False}
    config = store.load_config()
    return {"initialized": True, **config.to_dict()}


@app.post("/api/config")
async def save_config(body: dict[str, Any]):
    from ..models import Config
    config = Config.from_dict(body)
    store = _store()
    store.save_config(config)
    # Also initialize longterm plan if not exists
    if not (store.root / "longterm_plan.json").exists():
        from ..models import LongtermPlan
        lt = LongtermPlan.default_plan(config.exam_date)
        store.save_longterm_plan(lt)
    return {"ok": True}


# ---------------------------------------------------------------------------
# API: Plans & Tasks
# ---------------------------------------------------------------------------


@app.get("/api/today")
async def get_today_plan():
    """Return today's plan with task details."""
    store = _store()
    plan = store.load_daily_plan()
    config = store.load_config() if store.config_exists() else None

    tasks = []
    for t in plan.tasks:
        tasks.append({
            "id": t.id,
            "subject": t.subject,
            "content": t.content,
            "planned_minutes": t.planned_minutes,
            "actual_minutes": t.actual_minutes,
            "done": t.done,
        })

    pomodoros = []
    for p in plan.pomodoros:
        pomodoros.append({
            "start": p.start,
            "end": p.end,
            "subject": p.subject,
            "task_id": p.task_id,
            "duration_minutes": p.duration_minutes,
        })

    return {
        "date": plan.date,
        "tasks": tasks,
        "pomodoros": pomodoros,
        "reflection": plan.reflection,
        "total_planned": plan.total_planned_minutes(),
        "total_actual": plan.total_actual_minutes(),
        "completion_rate": plan.completion_rate(),
        "config": config.to_dict() if config else None,
    }


@app.post("/api/plan/generate")
async def generate_plan():
    """Auto-generate today's plan based on config and milestones."""
    store = _store()
    plan = create_today_plan(store)
    return {
        "ok": True,
        "date": plan.date,
        "task_count": len(plan.tasks),
    }


@app.post("/api/tasks")
async def add_task(body: dict[str, Any]):
    """Manually add a task to today's plan."""
    store = _store()
    plan = store.load_daily_plan()
    from ..models import Task
    task = Task(
        subject=body.get("subject", ""),
        content=body.get("content", ""),
        planned_minutes=body.get("planned_minutes", 60),
    )
    plan.tasks.append(task)
    store.save_daily_plan(plan)
    return {"ok": True, "task": task.to_dict()}


@app.post("/api/tasks/{task_id}/done")
async def mark_task_done(task_id: str):
    store = _store()
    plan = store.load_daily_plan()
    task = plan.task_by_id(task_id)
    if task is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    task.done = True
    store.save_daily_plan(plan)
    return {"ok": True, "task_id": task_id}


@app.post("/api/tasks/{task_id}/undone")
async def mark_task_undone(task_id: str):
    store = _store()
    plan = store.load_daily_plan()
    task = plan.task_by_id(task_id)
    if task is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    task.done = False
    store.save_daily_plan(plan)
    return {"ok": True, "task_id": task_id}


@app.post("/api/checkin")
async def checkin(body: dict[str, Any]):
    store = _store()
    plan = store.load_daily_plan()
    plan.reflection = body.get("reflection", "")
    store.save_daily_plan(plan)
    return {"ok": True}


# ---------------------------------------------------------------------------
# API: Milestones
# ---------------------------------------------------------------------------


@app.get("/api/milestones")
async def get_milestones():
    store = _store()
    lt = store.load_longterm_plan()
    alerts = check_milestones(lt)
    return {
        "milestones": [m.to_dict() for m in lt.milestones],
        "alerts": alerts,
    }


@app.post("/api/milestones/{milestone_id}/toggle")
async def toggle_milestone_status(milestone_id: str):
    store = _store()
    lt = store.load_longterm_plan()
    found = toggle_milestone(lt, milestone_id)
    if not found:
        return JSONResponse({"error": "not found"}, status_code=404)
    store.save_longterm_plan(lt)
    return {"ok": True}


# ---------------------------------------------------------------------------
# API: Plan cascade (yearly -> monthly)
# ---------------------------------------------------------------------------


@app.get("/api/yearly")
async def get_yearly_plan():
    """Return the yearly plan, deriving a default from config when absent."""
    store = _store()
    plan = store.load_yearly_plan()
    return {"plan": plan.to_dict()}


@app.post("/api/yearly/regenerate")
async def regenerate_yearly_plan():
    """Rebuild the default yearly phases anchored to the configured exam date."""
    store = _store()
    config = store.load_config()
    from ..models import YearlyPlan
    plan = YearlyPlan.default_plan(config.exam_date, config.subjects)
    store.save_yearly_plan(plan)
    return {"ok": True, "plan": plan.to_dict()}


@app.get("/api/monthly")
async def get_monthly_plan(month: str = ""):
    """Return a month's plan. month is YYYY-MM; defaults to current month."""
    store = _store()
    from datetime import date as _date
    target = month or _date.today().strftime("%Y-%m")
    plan = store.load_monthly_plan(target)
    if plan is None:
        return {"plan": None, "month": target}
    return {"plan": plan.to_dict(), "month": target}


@app.get("/api/monthly/all")
async def list_monthly_plans():
    store = _store()
    return {"plans": [p.to_dict() for p in store.list_monthly_plans()]}


@app.post("/api/monthly/generate")
async def generate_monthly(month: str = ""):
    """Generate (or regenerate) a month's plan via the cascade + Planner agent."""
    store = _store()
    from datetime import date as _date
    target = month or _date.today().strftime("%Y-%m")
    plan = generate_monthly_plan(store, target)
    return {"ok": True, "plan": plan.to_dict()}


@app.get("/api/drift")
async def get_drift():
    """Return drift signals that warrant re-planning."""
    store = _store()
    return detect_drift(store)


# ---------------------------------------------------------------------------
# API: Status & Stats
# ---------------------------------------------------------------------------


@app.get("/api/status")
async def get_status():
    store = _store()
    if not store.config_exists():
        return {"initialized": False}
    info = _get_status(store)
    return {"initialized": True, **info}


@app.get("/api/stats/week")
async def get_week_stats():
    """Return daily stats for the past 7 days."""
    store = _store()
    plans = store.load_recent_plans(7)

    days = []
    for p in plans:
        days.append({
            "date": p.date,
            "tasks_total": len(p.tasks),
            "tasks_done": sum(1 for t in p.tasks if t.done),
            "planned_minutes": p.total_planned_minutes(),
            "actual_minutes": p.total_actual_minutes(),
            "pomodoros": len(p.pomodoros),
            "checked_in": p.reflection is not None,
        })

    return {"days": days}


@app.get("/api/stats/compliance")
async def get_compliance():
    """Return compliance report for the last 7 days."""
    store = _store()
    return check_compliance(store)


# ---------------------------------------------------------------------------
# API: Questions / Self-test
# ---------------------------------------------------------------------------


@app.get("/api/questions")
async def list_questions(subject: str = ""):
    store = _store()
    if subject:
        questions = get_questions_by_subject(store, subject)
    else:
        questions = store.load_questions()
    return {"questions": [q.to_dict() for q in questions]}


@app.post("/api/questions")
async def create_question(body: dict[str, Any]):
    store = _store()
    q = add_question(
        store,
        subject=body.get("subject", ""),
        topic=body.get("topic", ""),
        question_text=body.get("question_text", ""),
        answer=body.get("answer", ""),
        difficulty=body.get("difficulty", 3),
        tags=body.get("tags", []),
    )
    return {"ok": True, "question": q.to_dict()}


@app.post("/api/test/start")
async def start_test(body: dict[str, Any]):
    """Pick random questions for a test session."""
    store = _store()
    subject = body.get("subject", "")
    count = body.get("count", 5)
    difficulty_min = body.get("difficulty_min", 1)
    difficulty_max = body.get("difficulty_max", 5)

    questions = pick_random_questions(
        store, subject, count, (difficulty_min, difficulty_max)
    )
    test_id = _gen_id("test")

    return {
        "test_id": test_id,
        "questions": [q.to_dict() for q in questions],
        "total": len(questions),
    }


@app.post("/api/test/submit")
async def submit_test(body: dict[str, Any]):
    """Submit test results."""
    store = _store()
    result = TestResult(
        date=date.today().isoformat(),
        subject=body.get("subject", ""),
        total_questions=body.get("total_questions", 0),
        correct=body.get("correct", 0),
        weak_topics=body.get("weak_topics", []),
        notes=body.get("notes", ""),
    )
    save_test_result(store, result)
    return {"ok": True, "score": result.score}


@app.get("/api/test/results")
async def get_test_results(subject: str = ""):
    store = _store()
    results = store.load_test_results()
    if subject:
        results = [r for r in results if r.subject == subject]
    return {"results": [r.to_dict() for r in results]}


@app.get("/api/test/weak-topics")
async def get_weak(subject: str = ""):
    store = _store()
    weak = get_weak_topics(store, subject) if subject else []
    return {"weak_topics": weak}


# ---------------------------------------------------------------------------
# API: Reports
# ---------------------------------------------------------------------------


@app.get("/api/reports")
async def list_reports():
    """List all saved reports."""
    store = _store()
    reports_dir = store.reports_dir
    if not reports_dir.exists():
        return {"reports": []}
    files = sorted(reports_dir.glob("*.md"), reverse=True)
    return {
        "reports": [
            {"filename": f.name, "size": f.stat().st_size}
            for f in files
        ]
    }


@app.get("/api/reports/{filename}")
async def get_report(filename: str):
    store = _store()
    path = store.reports_dir / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"filename": filename, "content": path.read_text(encoding="utf-8")}


@app.post("/api/report/generate")
async def generate_report():
    """Generate and save a weekly report."""
    store = _store()
    content = generate_weekly_report(store)
    filename = f"{date.today().isoformat()}-weekly.md"
    store.save_report(filename, content)
    return {"ok": True, "filename": filename}


# ---------------------------------------------------------------------------
# API: Wrong Answer Book
# ---------------------------------------------------------------------------


@app.post("/api/wrong-book/upload")
async def upload_wrong_question(
    file: UploadFile = File(...),
    subject: str = Form(""),
    source: str = Form(""),
):
    """Upload an image for AI analysis and add to wrong book."""
    if not is_api_key_configured():
        return JSONResponse(
            {"error": "AI service not configured. Set ANTHROPIC_API_KEY environment variable."},
            status_code=503,
        )

    content = await file.read()
    media_type = file.content_type or "image/jpeg"

    try:
        wq = wb.add_from_image(
            _store(),
            image_bytes=content,
            media_type=media_type,
            subject_hint=subject,
            source=source,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return {"ok": True, "question": wq.to_dict()}


@app.post("/api/wrong-book")
async def create_wrong_question(body: dict[str, Any]):
    """Manually add a wrong question."""
    wq = wb.add_manual(
        _store(),
        subject=body.get("subject", ""),
        topic=body.get("topic", ""),
        question_text=body.get("question_text", ""),
        answer=body.get("answer", ""),
        knowledge_points=body.get("knowledge_points", []),
        difficulty=body.get("difficulty", 3),
        source=body.get("source", ""),
    )
    return {"ok": True, "question": wq.to_dict()}


@app.get("/api/wrong-book")
async def list_wrong_questions(
    subject: str = "",
    mastery_min: int = -1,
    mastery_max: int = 6,
    page: int = 1,
    page_size: int = 20,
):
    result = wb.list_wrong_questions(
        _store(), subject=subject,
        mastery_min=mastery_min, mastery_max=mastery_max,
        page=page, page_size=page_size,
    )
    return result


@app.get("/api/wrong-book/stats")
async def wrong_book_stats():
    return wb.get_mastery_stats(_store())


@app.get("/api/wrong-book/review/today")
async def today_reviews():
    questions = wb.get_today_reviews(_store())
    return {"questions": [q.to_dict() for q in questions], "count": len(questions)}


@app.get("/api/wrong-book/review/pick")
async def pick_reviews(budget: int = 40):
    """Knowledge-point-driven review set, ranked by weakness (deterministic)."""
    return wb.pick_reviews_kp_aware(_store(), time_budget_minutes=budget)


@app.post("/api/wrong-book/review/agent-pick")
async def agent_pick_reviews(body: dict[str, Any] = None):
    """Agent-curated review set with deterministic fallback."""
    body = body or {}
    budget = int(body.get("budget", 40))
    return wb.pick_reviews_with_agent(_store(), time_budget_minutes=budget)


@app.get("/api/wrong-book/knowledge-points")
async def knowledge_points():
    """All knowledge points ranked from weakest to strongest."""
    return {"knowledge_points": wb.get_knowledge_point_index(_store())}


@app.get("/api/wrong-book/knowledge-points/merges")
async def kp_merge_suggestions():
    """Agent-proposed alias -> canonical merges for near-duplicate KPs."""
    return wb.suggest_kp_merges(_store())


@app.post("/api/wrong-book/knowledge-points/canon")
async def apply_kp_canon(body: dict[str, Any]):
    """Apply alias -> canonical merges and rewrite stored tags."""
    merges = body.get("merges", {}) if isinstance(body, dict) else {}
    if not isinstance(merges, dict):
        return JSONResponse({"error": "merges must be an object"}, status_code=400)
    return wb.apply_kp_merges(_store(), merges)


@app.get("/api/wrong-book/{question_id}")
async def get_wrong_question(question_id: str):
    wq = wb.get_wrong_question(_store(), question_id)
    if wq is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    # Also load review history
    records = _store().reviews_for_question(question_id)
    return {
        "question": wq.to_dict(),
        "reviews": [r.to_dict() for r in records],
    }


@app.put("/api/wrong-book/{question_id}")
async def update_wrong_question(question_id: str, body: dict[str, Any]):
    wq = wb.update_wrong_question(_store(), question_id, body)
    if wq is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"ok": True, "question": wq.to_dict()}


@app.delete("/api/wrong-book/{question_id}")
async def delete_wrong_question(question_id: str):
    ok = wb.delete_wrong_question(_store(), question_id)
    if not ok:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"ok": True}


@app.post("/api/wrong-book/{question_id}/review")
async def submit_wrong_question_review(question_id: str, body: dict[str, Any]):
    result = body.get("result", "")
    note = body.get("note", "")
    if result not in ("mastered", "familiar", "unfamiliar", "forgot"):
        return JSONResponse(
            {"error": "result must be one of: mastered, familiar, unfamiliar, forgot"},
            status_code=400,
        )
    wq = wb.submit_review(_store(), question_id, result, note)
    if wq is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"ok": True, "question": wq.to_dict()}


@app.post("/api/wrong-book/{question_id}/regenerate")
async def regenerate_analysis(question_id: str):
    """Re-run AI analysis on an existing wrong question."""
    if not is_api_key_configured():
        return JSONResponse(
            {"error": "AI service not configured."},
            status_code=503,
        )

    store = _store()
    wq = store.wrong_question_by_id(question_id)
    if wq is None:
        return JSONResponse({"error": "not found"}, status_code=404)

    if not wq.image_path:
        return JSONResponse({"error": "No image associated"}, status_code=400)

    from ..ai import analyze_question_image
    img_path = store.root / wq.image_path
    if not img_path.exists():
        return JSONResponse({"error": "Image file missing"}, status_code=404)

    analysis = analyze_question_image(img_path.read_bytes(), subject_hint=wq.subject)

    wq.question_text = analysis.get("question_text", wq.question_text)
    wq.topic = analysis.get("topic", wq.topic)
    wq.knowledge_points = analysis.get("knowledge_points", wq.knowledge_points)
    wq.difficulty = analysis.get("difficulty", wq.difficulty)
    wq.answer = analysis.get("answer", wq.answer)

    store.update_wrong_question(wq)
    return {"ok": True, "question": wq.to_dict()}


# ---------------------------------------------------------------------------
# API: AI status
# ---------------------------------------------------------------------------


@app.get("/api/ai/status")
async def ai_status():
    return {"available": is_api_key_configured()}


# ---------------------------------------------------------------------------
# API: Timer (record study sessions)
# ---------------------------------------------------------------------------


@app.post("/api/timer/start")
async def timer_start(task_id: str = "", subject: str = ""):
    """Start a new timer session, returns a session id."""
    session_id = _gen_id("ses")
    _active_sessions[session_id] = {
        "id": session_id,
        "task_id": task_id,
        "subject": subject,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
    }
    return {"session_id": session_id}


@app.post("/api/timer/stop/{session_id}")
async def timer_stop(session_id: str):
    """Stop a timer session and record the time to today's plan."""
    if session_id not in _active_sessions:
        return JSONResponse({"error": "session not found"}, status_code=404)

    session = _active_sessions.pop(session_id)
    session["end_time"] = datetime.now().isoformat()

    start = datetime.fromisoformat(session["start_time"])
    end = datetime.fromisoformat(session["end_time"])
    elapsed_minutes = int((end - start).total_seconds() / 60)

    store = _store()
    plan = store.load_daily_plan()

    task_id = session.get("task_id", "")
    if task_id:
        task = plan.task_by_id(task_id)
        if task:
            task.actual_minutes += elapsed_minutes

    from ..models import Pomodoro
    plan.pomodoros.append(Pomodoro(
        start=start.strftime("%H:%M"),
        end=end.strftime("%H:%M"),
        subject=session.get("subject", ""),
        task_id=task_id,
        duration_minutes=elapsed_minutes,
    ))

    store.save_daily_plan(plan)
    return {"elapsed_minutes": elapsed_minutes, "session_id": session_id}


# ---------------------------------------------------------------------------
# WebSocket: real-time timer sync
# ---------------------------------------------------------------------------


@app.websocket("/ws/timer")
async def ws_timer(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["type"] == "start":
                session_id = _gen_id("ws")
                _active_sessions[session_id] = {
                    "id": session_id,
                    "task_id": msg.get("task_id", ""),
                    "subject": msg.get("subject", ""),
                    "start_time": datetime.now().isoformat(),
                    "end_time": None,
                }
                await websocket.send_json({"type": "started", "session_id": session_id})

            elif msg["type"] == "stop":
                session_id = msg.get("session_id", "")
                if session_id in _active_sessions:
                    session = _active_sessions.pop(session_id)
                    session["end_time"] = datetime.now().isoformat()
                    start = datetime.fromisoformat(session["start_time"])
                    end = datetime.fromisoformat(session["end_time"])
                    elapsed = int((end - start).total_seconds() / 60)

                    store = _store()
                    plan = store.load_daily_plan()
                    task_id = session.get("task_id", "")
                    if task_id:
                        task = plan.task_by_id(task_id)
                        if task:
                            task.actual_minutes += elapsed
                    from ..models import Pomodoro
                    plan.pomodoros.append(Pomodoro(
                        start=start.strftime("%H:%M"),
                        end=end.strftime("%H:%M"),
                        subject=session.get("subject", ""),
                        task_id=task_id,
                        duration_minutes=elapsed,
                    ))
                    store.save_daily_plan(plan)
                    await websocket.send_json({
                        "type": "stopped",
                        "elapsed_minutes": elapsed,
                        "total_pomodoros": len(plan.pomodoros),
                    })

            elif msg["type"] == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Run helper
# ---------------------------------------------------------------------------


def run_server(host: str = "0.0.0.0", port: int = 8900):
    """Run the study room web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
