"""Data models for study-coach.

All models are dataclasses that serialize to/from JSON.
Dates and times are stored as ISO-format strings.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any


def _gen_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class Config:
    exam_date: str = "2026-12-26"
    subjects: list[str] = field(
        default_factory=lambda: ["数学一", "英语一", "政治", "408"]
    )
    math_scope: list[str] = field(
        default_factory=lambda: ["高等数学", "线性代数", "概率论与数理统计"]
    )
    cs408_scope: list[str] = field(
        default_factory=lambda: ["数据结构", "计算机组成原理", "操作系统", "计算机网络"]
    )
    daily_study_hours: int = 8
    target_school: str = "待定"
    target_major: str = "待定"

    def to_dict(self) -> dict[str, Any]:
        return {
            "exam_date": self.exam_date,
            "subjects": self.subjects,
            "math_scope": self.math_scope,
            "cs408_scope": self.cs408_scope,
            "daily_study_hours": self.daily_study_hours,
            "target_school": self.target_school,
            "target_major": self.target_major,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Config:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Long-term Plan
# ---------------------------------------------------------------------------


@dataclass
class Milestone:
    id: str = field(default_factory=lambda: _gen_id("m"))
    name: str = ""
    deadline: str = ""
    subjects: list[str] = field(default_factory=list)
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "deadline": self.deadline,
            "subjects": self.subjects,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Milestone:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class LongtermPlan:
    milestones: list[Milestone] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"milestones": [m.to_dict() for m in self.milestones]}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LongtermPlan:
        milestones = [Milestone.from_dict(m) for m in d.get("milestones", [])]
        return cls(milestones=milestones)

    @classmethod
    def default_plan(cls, exam_date: str = "2026-12-26") -> LongtermPlan:
        """Generate a default milestone plan based on exam date."""
        return cls(
            milestones=[
                Milestone(
                    name="数学一轮",
                    deadline="2026-09-30",
                    subjects=["高等数学", "线性代数", "概率论与数理统计"],
                ),
                Milestone(
                    name="专业课一轮",
                    deadline="2026-10-15",
                    subjects=["数据结构", "计算机组成原理", "操作系统", "计算机网络"],
                ),
                Milestone(
                    name="全科强化",
                    deadline="2026-11-15",
                    subjects=[],
                ),
                Milestone(
                    name="全科冲刺",
                    deadline="2026-12-20",
                    subjects=[],
                ),
            ]
        )


# ---------------------------------------------------------------------------
# Plan cascade: Yearly -> Monthly (sits above the milestone / daily layers)
# ---------------------------------------------------------------------------


@dataclass
class YearlyPhase:
    """A named window of the preparation timeline (e.g. 基础 / 强化 / 冲刺)."""

    name: str = ""
    start: str = ""  # ISO date, inclusive
    end: str = ""  # ISO date, inclusive
    focus_subjects: list[str] = field(default_factory=list)
    # Per-subject time weights for this phase; normalized at consumption time.
    weight_overrides: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start": self.start,
            "end": self.end,
            "focus_subjects": self.focus_subjects,
            "weight_overrides": self.weight_overrides,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> YearlyPhase:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def contains(self, d: date) -> bool:
        """True when d falls inside [start, end]."""
        try:
            return date.fromisoformat(self.start) <= d <= date.fromisoformat(self.end)
        except ValueError:
            return False


@dataclass
class YearlyPlan:
    """Top-of-cascade constraints: exam target, timeline phases, per-subject goals."""

    exam_date: str = "2026-12-26"
    target_scores: dict[str, int] = field(default_factory=dict)
    phases: list[YearlyPhase] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "exam_date": self.exam_date,
            "target_scores": self.target_scores,
            "phases": [p.to_dict() for p in self.phases],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> YearlyPlan:
        phases = [YearlyPhase.from_dict(p) for p in d.get("phases", [])]
        return cls(
            exam_date=d.get("exam_date", "2026-12-26"),
            target_scores=d.get("target_scores", {}),
            phases=phases,
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    @classmethod
    def default_plan(
        cls, exam_date: str = "2026-12-26", subjects: list[str] | None = None
    ) -> YearlyPlan:
        """Derive default phases anchored to the exam date.

        Windows are exam-relative so the cascade stays valid as the date moves.
        Phase weights shift the subject mix across the timeline.
        """
        try:
            exam = date.fromisoformat(exam_date)
        except ValueError:
            exam = date.fromisoformat("2026-12-26")

        math, eng, pol, cs = "数学一", "英语一", "政治", "408"
        phases = [
            YearlyPhase(
                name="基础阶段",
                start=(exam - timedelta(days=200)).isoformat(),
                end=(exam - timedelta(days=100)).isoformat(),
                focus_subjects=[math, cs],
                weight_overrides={math: 0.40, cs: 0.30, eng: 0.20, pol: 0.10},
            ),
            YearlyPhase(
                name="强化阶段",
                start=(exam - timedelta(days=100)).isoformat(),
                end=(exam - timedelta(days=35)).isoformat(),
                focus_subjects=[math, cs, eng],
                weight_overrides={math: 0.35, cs: 0.30, eng: 0.20, pol: 0.15},
            ),
            YearlyPhase(
                name="冲刺阶段",
                start=(exam - timedelta(days=35)).isoformat(),
                end=exam.isoformat(),
                focus_subjects=[pol, eng],
                weight_overrides={math: 0.30, cs: 0.25, eng: 0.20, pol: 0.25},
            ),
        ]
        today = date.today().isoformat()
        return cls(
            exam_date=exam_date,
            target_scores={s: 0 for s in (subjects or [])},
            phases=phases,
            created_at=today,
            updated_at=today,
        )

    def phase_for_date(self, d: date | str) -> YearlyPhase | None:
        """Return the phase whose window contains d.

        Falls back to the first phase when d precedes the timeline, and to the
        last phase when d is past it, so a ref date at a month boundary still
        resolves instead of returning None.
        """
        if isinstance(d, str):
            try:
                d = date.fromisoformat(d)
            except ValueError:
                return None
        if not self.phases:
            return None
        for p in self.phases:
            if p.contains(d):
                return p
        # Before the first phase -> treat as lead-in to the first phase.
        first = self.phases[0]
        try:
            if d < date.fromisoformat(first.start):
                return first
        except ValueError:
            pass
        # Past the last phase -> hold on the final phase.
        return self.phases[-1]


@dataclass
class MonthlyGoal:
    subject: str = ""
    goal: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"subject": self.subject, "goal": self.goal}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MonthlyGoal:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class MonthlyPlan:
    """A month's allocation: phase reference, normalized subject weights, goals."""

    month: str = ""  # YYYY-MM
    phase: str = ""
    subject_weights: dict[str, float] = field(default_factory=dict)
    goals: list[MonthlyGoal] = field(default_factory=list)
    generated_at: str = ""
    # Audit snapshot of the signals that produced this plan.
    generated_from: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "month": self.month,
            "phase": self.phase,
            "subject_weights": self.subject_weights,
            "goals": [g.to_dict() for g in self.goals],
            "generated_at": self.generated_at,
            "generated_from": self.generated_from,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MonthlyPlan:
        goals = [MonthlyGoal.from_dict(g) for g in d.get("goals", [])]
        return cls(
            month=d.get("month", ""),
            phase=d.get("phase", ""),
            subject_weights=d.get("subject_weights", {}),
            goals=goals,
            generated_at=d.get("generated_at", ""),
            generated_from=d.get("generated_from", {}),
        )


# ---------------------------------------------------------------------------
# Daily Plan & Task
# ---------------------------------------------------------------------------


@dataclass
class Task:
    id: str = field(default_factory=lambda: _gen_id("t"))
    subject: str = ""
    content: str = ""
    planned_minutes: int = 0
    actual_minutes: int = 0
    done: bool = False
    knowledge_points: list[str] = field(default_factory=list)
    preview_for_tomorrow: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "content": self.content,
            "planned_minutes": self.planned_minutes,
            "actual_minutes": self.actual_minutes,
            "done": self.done,
            "knowledge_points": self.knowledge_points,
            "preview_for_tomorrow": self.preview_for_tomorrow,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Task:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Pomodoro:
    start: str = ""
    end: str = ""
    subject: str = ""
    task_id: str = ""
    duration_minutes: int = 25

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "subject": self.subject,
            "task_id": self.task_id,
            "duration_minutes": self.duration_minutes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Pomodoro:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DailyPlan:
    date: str = ""
    tasks: list[Task] = field(default_factory=list)
    pomodoros: list[Pomodoro] = field(default_factory=list)
    reflection: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "tasks": [t.to_dict() for t in self.tasks],
            "pomodoros": [p.to_dict() for p in self.pomodoros],
            "reflection": self.reflection,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DailyPlan:
        tasks = [Task.from_dict(t) for t in d.get("tasks", [])]
        pomodoros = [Pomodoro.from_dict(p) for p in d.get("pomodoros", [])]
        return cls(
            date=d.get("date", ""),
            tasks=tasks,
            pomodoros=pomodoros,
            reflection=d.get("reflection"),
        )

    def task_by_id(self, task_id: str) -> Task | None:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def total_planned_minutes(self) -> int:
        return sum(t.planned_minutes for t in self.tasks)

    def total_actual_minutes(self) -> int:
        return sum(t.actual_minutes for t in self.tasks)

    def completion_rate(self) -> float:
        if not self.tasks:
            return 0.0
        return sum(1 for t in self.tasks if t.done) / len(self.tasks)


# ---------------------------------------------------------------------------
# Test / Self-examination
# ---------------------------------------------------------------------------


@dataclass
class Question:
    id: str = field(default_factory=lambda: _gen_id("q"))
    subject: str = ""
    topic: str = ""
    question_text: str = ""
    answer: str = ""
    difficulty: int = 1  # 1-5
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "topic": self.topic,
            "question_text": self.question_text,
            "answer": self.answer,
            "difficulty": self.difficulty,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Question:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class TestResult:
    id: str = field(default_factory=lambda: _gen_id("tr"))
    date: str = ""
    subject: str = ""
    total_questions: int = 0
    correct: int = 0
    weak_topics: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date,
            "subject": self.subject,
            "total_questions": self.total_questions,
            "correct": self.correct,
            "weak_topics": self.weak_topics,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TestResult:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def score(self) -> float:
        if self.total_questions == 0:
            return 0.0
        return self.correct / self.total_questions


# ---------------------------------------------------------------------------
# Wrong Answer Notebook
# ---------------------------------------------------------------------------


# Spaced repetition intervals in days
REVIEW_INTERVALS = [1, 3, 7, 14, 30]


@dataclass
class WrongQuestion:
    id: str = field(default_factory=lambda: _gen_id("wq"))
    subject: str = ""
    topic: str = ""
    question_text: str = ""
    answer: str = ""
    knowledge_points: list[str] = field(default_factory=list)
    difficulty: int = 1  # 1-5
    image_path: str = ""
    source: str = ""
    created_at: str = ""
    review_count: int = 0
    mastery_level: int = 0  # 0-5, each level = passed one review
    next_review_date: str = ""
    last_reviewed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "topic": self.topic,
            "question_text": self.question_text,
            "answer": self.answer,
            "knowledge_points": self.knowledge_points,
            "difficulty": self.difficulty,
            "image_path": self.image_path,
            "source": self.source,
            "created_at": self.created_at,
            "review_count": self.review_count,
            "mastery_level": self.mastery_level,
            "next_review_date": self.next_review_date,
            "last_reviewed_at": self.last_reviewed_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WrongQuestion:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ReviewRecord:
    id: str = field(default_factory=lambda: _gen_id("rr"))
    wrong_question_id: str = ""
    reviewed_at: str = ""
    result: str = ""  # "mastered" | "familiar" | "unfamiliar" | "forgot"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "wrong_question_id": self.wrong_question_id,
            "reviewed_at": self.reviewed_at,
            "result": self.result,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ReviewRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Knowledge-point mastery index (derived from wrong questions + reviews)
# ---------------------------------------------------------------------------


@dataclass
class KnowledgePointStat:
    """Aggregated mastery for a single knowledge point.

    Derived, not authored: computed by aggregating WrongQuestion records that
    share this knowledge-point tag. mastery_level is normalized to [0, 1] from
    the per-question 0-5 mastery scale, so 1.0 means every tagged question has
    reached the top mastery tier.
    """

    name: str = ""
    subject: str = ""
    count: int = 0  # number of wrong questions tagged with this KP
    total_mastery: float = 0.0  # sum of per-question mastery levels (0-5 each)
    avg_mastery: float = 0.0  # 0-5
    mastery_level: float = 0.0  # 0-1, normalized
    last_wrong_date: str = ""
    wrong_question_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "subject": self.subject,
            "count": self.count,
            "total_mastery": self.total_mastery,
            "avg_mastery": self.avg_mastery,
            "mastery_level": self.mastery_level,
            "last_wrong_date": self.last_wrong_date,
            "wrong_question_ids": self.wrong_question_ids,
        }
