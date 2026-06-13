"""Wrong answer notebook: image analysis, spaced repetition, and review scheduling."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .ai import analyze_question_image, is_api_key_configured
from .kp_index import (
    build_kp_index,
    canonicalize_kps,
    mastery_lookup,
    normalize_kp,
    rank_weak_kps,
)
from .models import REVIEW_INTERVALS, KnowledgePointStat, ReviewRecord, WrongQuestion
from .store import Store


# ---------------------------------------------------------------------------
# Add wrong questions
# ---------------------------------------------------------------------------


def add_from_image(
    store: Store,
    image_bytes: bytes,
    media_type: str = "image/jpeg",
    subject_hint: str = "",
    source: str = "",
) -> WrongQuestion:
    """Upload an image, run AI analysis, and create a WrongQuestion."""
    analysis = analyze_question_image(image_bytes, media_type, subject_hint)

    today = date.today().isoformat()
    next_review = (date.today() + timedelta(days=REVIEW_INTERVALS[0])).isoformat()

    wq = WrongQuestion(
        subject=subject_hint or _guess_subject(analysis),
        topic=analysis.get("topic", ""),
        question_text=analysis.get("question_text", ""),
        answer=analysis.get("answer", ""),
        knowledge_points=canonicalize_kps(
            analysis.get("knowledge_points", []), store.load_kp_canon()
        ),
        difficulty=analysis.get("difficulty", 3),
        source=source,
        created_at=today,
        next_review_date=next_review,
    )

    # Save image to disk
    filename = f"{wq.id}.{media_type.split('/')[-1]}"
    rel_path = store.save_uploaded_image(filename, image_bytes)
    wq.image_path = rel_path

    store.append_wrong_question(wq)
    return wq


def add_manual(
    store: Store,
    subject: str,
    topic: str,
    question_text: str,
    answer: str,
    knowledge_points: list[str] | None = None,
    difficulty: int = 3,
    source: str = "",
) -> WrongQuestion:
    """Manually add a wrong question without AI analysis."""
    today = date.today().isoformat()
    next_review = (date.today() + timedelta(days=REVIEW_INTERVALS[0])).isoformat()

    wq = WrongQuestion(
        subject=subject,
        topic=topic,
        question_text=question_text,
        answer=answer,
        knowledge_points=canonicalize_kps(
            knowledge_points or [], store.load_kp_canon()
        ),
        difficulty=difficulty,
        source=source,
        created_at=today,
        next_review_date=next_review,
    )
    store.append_wrong_question(wq)
    return wq


# ---------------------------------------------------------------------------
# Query and filter
# ---------------------------------------------------------------------------


def list_wrong_questions(
    store: Store,
    subject: str = "",
    mastery_min: int = -1,
    mastery_max: int = 6,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List wrong questions with optional filters. Returns paginated result."""
    questions = store.load_wrong_questions()

    if subject:
        questions = [q for q in questions if q.subject == subject]
    if mastery_min >= 0:
        questions = [q for q in questions if q.mastery_level >= mastery_min]
    if mastery_max < 6:
        questions = [q for q in questions if q.mastery_level <= mastery_max]

    total = len(questions)
    start = (page - 1) * page_size
    end = start + page_size
    items = questions[start:end]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "questions": [q.to_dict() for q in items],
    }


def get_wrong_question(store: Store, question_id: str) -> WrongQuestion | None:
    return store.wrong_question_by_id(question_id)


def update_wrong_question(
    store: Store,
    question_id: str,
    updates: dict[str, Any],
) -> WrongQuestion | None:
    """Update fields of a wrong question."""
    wq = store.wrong_question_by_id(question_id)
    if wq is None:
        return None

    allowed = {
        "subject", "topic", "question_text", "answer",
        "knowledge_points", "difficulty", "source",
    }
    for key, value in updates.items():
        if key in allowed:
            setattr(wq, key, value)

    store.update_wrong_question(wq)
    return wq


def delete_wrong_question(store: Store, question_id: str) -> bool:
    return store.delete_wrong_question(question_id)


# ---------------------------------------------------------------------------
# Review scheduling (spaced repetition)
# ---------------------------------------------------------------------------


def get_today_reviews(store: Store) -> list[WrongQuestion]:
    """Return questions due for review today."""
    today = date.today().isoformat()
    questions = store.load_wrong_questions()
    return [q for q in questions if q.next_review_date <= today and q.mastery_level < 5]


# Estimated minutes a single review consumes; used to cap a session to a budget.
REVIEW_MINUTES_PER_ITEM = 8


def score_review_candidates(store: Store) -> list[dict[str, Any]]:
    """Score every not-yet-mastered question for review priority.

    Ranking blends knowledge-point weakness (lower mastery = more urgent) with
    due status (scheduled cards weighted higher). Returned unsorted so callers
    (deterministic picker or the ReviewPicker agent) can re-order or curate.
    """
    today = date.today().isoformat()
    questions = store.load_wrong_questions()
    active = [q for q in questions if q.mastery_level < 5]

    index = build_kp_index(questions)
    mastery = mastery_lookup(index)

    candidates: list[dict[str, Any]] = []
    for q in active:
        due = q.next_review_date <= today
        if q.knowledge_points:
            levels = [mastery.get((kp, q.subject), 0.5) for kp in q.knowledge_points]
            kp_mastery = sum(levels) / len(levels)
        else:
            # Untagged questions get a neutral mastery so they rank by due status only.
            kp_mastery = 0.5
        due_factor = 1.0 if due else 0.3
        score = (1.0 - kp_mastery) * 0.6 + due_factor * 0.4
        candidates.append({
            "question_id": q.id,
            "subject": q.subject,
            "knowledge_points": list(q.knowledge_points),
            "mastery_level": q.mastery_level,
            "due": due,
            "kp_mastery": round(kp_mastery, 3),
            "score": round(score, 3),
        })
    return candidates


def pick_reviews_kp_aware(
    store: Store, time_budget_minutes: int = 60
) -> dict[str, Any]:
    """Select today's review set ranked by knowledge-point weakness.

    Caps the deterministic ranking to the time budget via
    REVIEW_MINUTES_PER_ITEM. Output targets the weakest knowledge first; due
    cards compete with weak-but-not-due cards rather than getting a free slot.
    """
    candidates = score_review_candidates(store)
    ranked = sorted(candidates, key=lambda c: c["score"], reverse=True)

    max_items = max(1, time_budget_minutes // REVIEW_MINUTES_PER_ITEM)
    selected_ids = {c["question_id"] for c in ranked[:max_items]}

    # Attach the full question payload for the selected items.
    by_id = {q.id: q for q in store.load_wrong_questions()}
    items = []
    for c in ranked[:max_items]:
        q = by_id.get(c["question_id"])
        if q is not None:
            items.append({**c, "question": q.to_dict()})

    return {
        "items": items,
        "count": len(items),
        "candidates_total": len(candidates),
        "time_budget_minutes": time_budget_minutes,
        "minutes_per_item": REVIEW_MINUTES_PER_ITEM,
    }


def get_knowledge_point_index(store: Store) -> list[dict[str, Any]]:
    """Return all knowledge points ranked from weakest to strongest."""
    questions = store.load_wrong_questions()
    index = build_kp_index(questions)
    return [s.to_dict() for s in rank_weak_kps(index)]


def suggest_kp_merges(store: Store) -> dict[str, Any]:
    """Ask the agent to propose alias -> canonical merges for near-duplicate KPs.

    Returns {"merges": [{alias, canonical, reason}], "source"}. Falls back to an
    empty list when AI is unavailable — semantic merging is never guessed
    deterministically, since substring heuristics are unreliable for Chinese.
    """
    from .ai import agent_suggest_kp_merges

    index = build_kp_index(store.load_wrong_questions())
    names = [s.name for s in index]
    result = agent_suggest_kp_merges({"knowledge_points": names})
    return {"merges": result["merges"], "source": result["source"]}


def apply_kp_merges(store: Store, merges: dict[str, str]) -> dict[str, Any]:
    """Merge alias -> canonical pairs into the canon dict and rewrite stored tags.

    Existing canon is preserved and extended. Every stored wrong question's tags
    are re-canonicalized so historical data converges on the same names.
    """
    canon = store.load_kp_canon()
    for alias, canonical in merges.items():
        canon[normalize_kp(alias)] = normalize_kp(canonical)
    store.save_kp_canon(canon)

    questions = store.load_wrong_questions()
    rewritten = 0
    for q in questions:
        new_kps = canonicalize_kps(q.knowledge_points, canon)
        if new_kps != q.knowledge_points:
            q.knowledge_points = new_kps
            store.update_wrong_question(q)
            rewritten += 1

    return {"canon_size": len(canon), "rewritten": rewritten}


def pick_reviews_with_agent(
    store: Store, time_budget_minutes: int = 60
) -> dict[str, Any]:
    """Agent-curated review set with deterministic fallback.

    Scores all candidates deterministically, then asks the ReviewPicker agent to
    curate the final ordering. The agent falls back to the score ranking when AI
    is unavailable, so this always returns a usable set.
    """
    # Lazy import avoids a wrong_book<->ai load-time edge if ai grows dependencies.
    from .ai import agent_pick_reviews

    candidates = score_review_candidates(store)
    max_items = max(1, time_budget_minutes // REVIEW_MINUTES_PER_ITEM)

    result = agent_pick_reviews({"candidates": candidates, "max_items": max_items})

    by_id = {q.id: q for q in store.load_wrong_questions()}
    cand_by_id = {c["question_id"]: c for c in candidates}
    items = []
    for qid in result["question_ids"]:
        q = by_id.get(qid)
        c = cand_by_id.get(qid, {})
        if q is not None:
            items.append({
                "question_id": qid,
                "question": q.to_dict(),
                "score": c.get("score", 0.0),
                "due": c.get("due", False),
                "kp_mastery": c.get("kp_mastery", 0.0),
            })

    return {
        "items": items,
        "count": len(items),
        "candidates_total": len(candidates),
        "source": result["source"],
        "rationale": result["rationale"],
        "time_budget_minutes": time_budget_minutes,
    }


def submit_review(
    store: Store,
    question_id: str,
    result: str,
    note: str = "",
) -> WrongQuestion | None:
    """Submit a review result and update the question's schedule.

    result: "mastered" | "familiar" | "unfamiliar" | "forgot"
    """
    wq = store.wrong_question_by_id(question_id)
    if wq is None:
        return None

    today = date.today().isoformat()

    # Determine next interval based on result
    if result == "mastered":
        wq.mastery_level = min(wq.mastery_level + 2, 5)
        idx = min(wq.mastery_level, len(REVIEW_INTERVALS) - 1)
    elif result == "familiar":
        wq.mastery_level = min(wq.mastery_level + 1, 5)
        idx = min(wq.mastery_level, len(REVIEW_INTERVALS) - 1)
    elif result == "unfamiliar":
        # No progress, review again soon
        idx = 0
    else:  # "forgot"
        # Regression: drop one level
        wq.mastery_level = max(wq.mastery_level - 1, 0)
        idx = 0

    interval_days = REVIEW_INTERVALS[idx]
    wq.next_review_date = (date.today() + timedelta(days=interval_days)).isoformat()
    wq.last_reviewed_at = today
    wq.review_count += 1

    store.update_wrong_question(wq)

    # Save review record
    record = ReviewRecord(
        wrong_question_id=question_id,
        reviewed_at=today,
        result=result,
        note=note,
    )
    store.append_review_record(record)

    return wq


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def get_mastery_stats(store: Store) -> dict[str, Any]:
    """Return mastery level distribution and per-subject breakdown."""
    questions = store.load_wrong_questions()

    total = len(questions)
    level_counts = [0] * 6
    subject_stats: dict[str, dict[str, int]] = {}

    for q in questions:
        level_counts[q.mastery_level] += 1
        if q.subject not in subject_stats:
            subject_stats[q.subject] = {"total": 0, "mastered": 0, "reviewing": 0}
        subject_stats[q.subject]["total"] += 1
        if q.mastery_level >= 4:
            subject_stats[q.subject]["mastered"] += 1
        elif q.mastery_level > 0:
            subject_stats[q.subject]["reviewing"] += 1

    # Knowledge point aggregation
    kp_stats: dict[str, dict[str, int]] = {}
    for q in questions:
        for kp in q.knowledge_points:
            if kp not in kp_stats:
                kp_stats[kp] = {"count": 0, "avg_mastery": 0, "total_mastery": 0}
            kp_stats[kp]["count"] += 1
            kp_stats[kp]["total_mastery"] += q.mastery_level
    for kp in kp_stats:
        kp_stats[kp]["avg_mastery"] = round(
            kp_stats[kp]["total_mastery"] / kp_stats[kp]["count"], 1
        )

    today_reviews = len(get_today_reviews(store))

    return {
        "total": total,
        "today_reviews": today_reviews,
        "level_distribution": level_counts,
        "subjects": subject_stats,
        "knowledge_points": kp_stats,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _guess_subject(analysis: dict[str, Any]) -> str:
    """Try to guess the subject from AI analysis result."""
    topic = analysis.get("topic", "").lower()
    kp_text = " ".join(analysis.get("knowledge_points", [])).lower()

    math_keywords = ["积分", "微分", "极限", "矩阵", "概率", "线性代数", "高数", "导数"]
    cs_keywords = ["算法", "数据结构", "操作系统", "网络", "计组", "进程", "tcp", "二叉树"]
    eng_keywords = ["阅读", "完形", "翻译", "写作", "vocabulary", "grammar"]
    pol_keywords = ["马原", "毛概", "史纲", "思修", "时政"]

    text = f"{topic} {kp_text}"
    for kw in math_keywords:
        if kw in text:
            return "数学一"
    for kw in cs_keywords:
        if kw in text:
            return "408"
    for kw in eng_keywords:
        if kw in text:
            return "英语一"
    for kw in pol_keywords:
        if kw in text:
            return "政治"
    return ""
