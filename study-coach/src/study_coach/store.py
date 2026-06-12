"""JSON file storage layer for study-coach.

All data lives under a configurable data directory (default: ./data).
Files are organized as:
    data/config.json
    data/longterm_plan.json
    data/daily/YYYY-MM-DD.json
    data/reports/YYYY-WNN.md
    data/tests/questions.json
    data/tests/results.json
"""

from __future__ import annotations

import json
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .models import (
    Config,
    DailyPlan,
    LongtermPlan,
    Question,
    ReviewRecord,
    TestResult,
    WrongQuestion,
)


class Store:
    """Manages all file I/O for study-coach."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.root = Path(data_dir)
        self.daily_dir = self.root / "daily"
        self.reports_dir = self.root / "reports"
        self.tests_dir = self.root / "tests"

        for d in [self.daily_dir, self.reports_dir, self.tests_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ---- helpers ----

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    # ---- Config ----

    def load_config(self) -> Config:
        data = self._read_json(self.root / "config.json")
        if data is None:
            return Config()
        return Config.from_dict(data)

    def save_config(self, config: Config) -> None:
        self._write_json(self.root / "config.json", config.to_dict())

    def config_exists(self) -> bool:
        return (self.root / "config.json").exists()

    # ---- Long-term Plan ----

    def load_longterm_plan(self) -> LongtermPlan:
        data = self._read_json(self.root / "longterm_plan.json")
        if data is None:
            return LongtermPlan()
        return LongtermPlan.from_dict(data)

    def save_longterm_plan(self, plan: LongtermPlan) -> None:
        self._write_json(self.root / "longterm_plan.json", plan.to_dict())

    # ---- Daily Plans ----

    def _daily_path(self, d: date | str) -> Path:
        if isinstance(d, str):
            d = date.fromisoformat(d)
        return self.daily_dir / f"{d.isoformat()}.json"

    def load_daily_plan(self, d: date | str | None = None) -> DailyPlan:
        if d is None:
            d = date.today()
        data = self._read_json(self._daily_path(d))
        if data is None:
            return DailyPlan(date=d.isoformat() if isinstance(d, date) else d)
        return DailyPlan.from_dict(data)

    def save_daily_plan(self, plan: DailyPlan) -> None:
        self._write_json(self._daily_path(plan.date), plan.to_dict())

    def daily_plan_exists(self, d: date | str | None = None) -> bool:
        if d is None:
            d = date.today()
        return self._daily_path(d).exists()

    def load_daily_plans_range(
        self, start: date, end: date
    ) -> list[DailyPlan]:
        """Load all daily plans in [start, end] inclusive."""
        plans: list[DailyPlan] = []
        current = start
        while current <= end:
            path = self._daily_path(current)
            data = self._read_json(path)
            if data is not None:
                plans.append(DailyPlan.from_dict(data))
            current += timedelta(days=1)
        return plans

    def load_recent_plans(self, days: int = 7) -> list[DailyPlan]:
        """Load daily plans from the last N days (including today)."""
        today = date.today()
        return self.load_daily_plans_range(today - timedelta(days=days - 1), today)

    # ---- Questions / Tests ----

    def load_questions(self) -> list[Question]:
        data = self._read_json(self.tests_dir / "questions.json")
        if data is None:
            return []
        return [Question.from_dict(q) for q in data.get("questions", [])]

    def save_questions(self, questions: list[Question]) -> None:
        self._write_json(
            self.tests_dir / "questions.json",
            {"questions": [q.to_dict() for q in questions]},
        )

    def load_test_results(self) -> list[TestResult]:
        data = self._read_json(self.tests_dir / "results.json")
        if data is None:
            return []
        return [TestResult.from_dict(r) for r in data.get("results", [])]

    def save_test_results(self, results: list[TestResult]) -> None:
        self._write_json(
            self.tests_dir / "results.json",
            {"results": [r.to_dict() for r in results]},
        )

    def append_test_result(self, result: TestResult) -> None:
        results = self.load_test_results()
        results.append(result)
        self.save_test_results(results)

    # ---- Reports ----

    def save_report(self, filename: str, content: str) -> Path:
        path = self.reports_dir / filename
        self._write_text(path, content)
        return path

    # ---- Wrong Answer Notebook ----

    @property
    def wrong_book_dir(self) -> Path:
        return self.root / "wrong_book"

    @property
    def wrong_book_images_dir(self) -> Path:
        return self.wrong_book_dir / "images"

    def _ensure_wrong_book_dirs(self) -> None:
        self.wrong_book_dir.mkdir(parents=True, exist_ok=True)
        self.wrong_book_images_dir.mkdir(parents=True, exist_ok=True)

    def load_wrong_questions(self) -> list[WrongQuestion]:
        data = self._read_json(self.wrong_book_dir / "questions.json")
        if data is None:
            return []
        return [WrongQuestion.from_dict(q) for q in data.get("questions", [])]

    def save_wrong_questions(self, questions: list[WrongQuestion]) -> None:
        self._ensure_wrong_book_dirs()
        self._write_json(
            self.wrong_book_dir / "questions.json",
            {"questions": [q.to_dict() for q in questions]},
        )

    def append_wrong_question(self, question: WrongQuestion) -> None:
        questions = self.load_wrong_questions()
        questions.append(question)
        self.save_wrong_questions(questions)

    def wrong_question_by_id(self, question_id: str) -> WrongQuestion | None:
        for q in self.load_wrong_questions():
            if q.id == question_id:
                return q
        return None

    def update_wrong_question(self, question: WrongQuestion) -> None:
        questions = self.load_wrong_questions()
        for i, q in enumerate(questions):
            if q.id == question.id:
                questions[i] = question
                break
        self.save_wrong_questions(questions)

    def delete_wrong_question(self, question_id: str) -> bool:
        questions = self.load_wrong_questions()
        filtered = [q for q in questions if q.id != question_id]
        if len(filtered) == len(questions):
            return False
        self.save_wrong_questions(filtered)
        # Remove image file if exists
        for q in questions:
            if q.id == question_id and q.image_path:
                img_path = self.root / q.image_path
                if img_path.exists():
                    img_path.unlink()
        return True

    def save_uploaded_image(self, filename: str, content: bytes) -> str:
        """Save an uploaded image and return its relative path from data root."""
        self._ensure_wrong_book_dirs()
        safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
        path = self.wrong_book_images_dir / safe_name
        path.write_bytes(content)
        # Return path relative to data root for portability
        return f"wrong_book/images/{safe_name}"

    def load_review_records(self) -> list[ReviewRecord]:
        data = self._read_json(self.wrong_book_dir / "reviews.json")
        if data is None:
            return []
        return [ReviewRecord.from_dict(r) for r in data.get("records", [])]

    def save_review_records(self, records: list[ReviewRecord]) -> None:
        self._ensure_wrong_book_dirs()
        self._write_json(
            self.wrong_book_dir / "reviews.json",
            {"records": [r.to_dict() for r in records]},
        )

    def append_review_record(self, record: ReviewRecord) -> None:
        records = self.load_review_records()
        records.append(record)
        self.save_review_records(records)

    def reviews_for_question(self, question_id: str) -> list[ReviewRecord]:
        return [r for r in self.load_review_records() if r.wrong_question_id == question_id]
