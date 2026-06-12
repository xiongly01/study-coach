"""Self-examination: question bank management and interactive testing."""

from __future__ import annotations

import random
from datetime import date

from .models import Question, TestResult
from .store import Store


def add_question(
    store: Store,
    subject: str,
    topic: str,
    question_text: str,
    answer: str,
    difficulty: int = 3,
    tags: list[str] | None = None,
) -> Question:
    """Add a question to the question bank."""
    q = Question(
        subject=subject,
        topic=topic,
        question_text=question_text,
        answer=answer,
        difficulty=difficulty,
        tags=tags or [],
    )
    questions = store.load_questions()
    questions.append(q)
    store.save_questions(questions)
    return q


def get_questions_by_subject(store: Store, subject: str) -> list[Question]:
    """Filter questions by subject."""
    return [q for q in store.load_questions() if q.subject == subject]


def pick_random_questions(
    store: Store,
    subject: str,
    count: int = 5,
    difficulty_range: tuple[int, int] = (1, 5),
) -> list[Question]:
    """Pick random questions for a given subject within a difficulty range."""
    pool = [
        q
        for q in store.load_questions()
        if q.subject == subject and difficulty_range[0] <= q.difficulty <= difficulty_range[1]
    ]
    count = min(count, len(pool))
    return random.sample(pool, count) if count > 0 else []


def run_test_interactive(
    store: Store,
    questions: list[Question],
    subject: str,
    notes: str = "",
) -> TestResult:
    """Run an interactive test session. User answers each question, we record results.

    This function returns the TestResult. The actual I/O is handled by the CLI layer.
    """
    correct = 0
    weak_topics: list[str] = []

    # We return a TestResult for the CLI to fill in with user responses
    return TestResult(
        date=date.today().isoformat(),
        subject=subject,
        total_questions=len(questions),
        correct=0,  # filled by CLI
        weak_topics=weak_topics,
        notes=notes,
    )


def save_test_result(store: Store, result: TestResult) -> None:
    """Save a completed test result."""
    store.append_test_result(result)


def get_weak_topics(store: Store, subject: str) -> list[str]:
    """Analyze test history and return topics with low scores."""
    results = store.load_test_results()
    topic_stats: dict[str, list[float]] = {}

    for r in results:
        if r.subject != subject:
            continue
        for topic in r.weak_topics:
            if topic not in topic_stats:
                topic_stats[topic] = []
            topic_stats[topic].append(r.score)

    # Topics that appear frequently with low scores
    weak: list[str] = []
    for topic, scores in topic_stats.items():
        avg = sum(scores) / len(scores)
        if avg < 0.6:
            weak.append(topic)

    return weak


def import_questions_from_dict(store: Store, data: list[dict]) -> int:
    """Bulk import questions from a list of dicts. Returns count imported."""
    questions = store.load_questions()
    count = 0
    for item in data:
        q = Question(
            subject=item.get("subject", ""),
            topic=item.get("topic", ""),
            question_text=item.get("question_text", ""),
            answer=item.get("answer", ""),
            difficulty=item.get("difficulty", 3),
            tags=item.get("tags", []),
        )
        questions.append(q)
        count += 1
    store.save_questions(questions)
    return count
