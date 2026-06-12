"""Wrong answer notebook: image analysis, spaced repetition, and review scheduling."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .ai import analyze_question_image, is_api_key_configured
from .models import REVIEW_INTERVALS, ReviewRecord, WrongQuestion
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
        knowledge_points=analysis.get("knowledge_points", []),
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
        knowledge_points=knowledge_points or [],
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
