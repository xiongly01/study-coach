"""Math knowledge-point matcher.

Provides fuzzy matching from task content / keywords to the structured
knowledge-point index (math_knowledge_points.json). Used by the planner
to enrich tasks with relevant KP references.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MathKnowledgePoint:
    """A single knowledge point from the math formula handbook."""

    id: str
    name: str
    chapter: str
    subject: str
    keywords: list[str]
    formulas: list[str]
    difficulty: int
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "chapter": self.chapter,
            "subject": self.subject,
            "keywords": self.keywords,
            "formulas": self.formulas,
            "difficulty": self.difficulty,
            "description": self.description,
        }


def _math_kp_path() -> Path:
    """Return the path to data/math_knowledge_points.json."""
    return Path(__file__).resolve().parent.parent.parent / "data" / "math_knowledge_points.json"


def load_math_kps() -> list[MathKnowledgePoint]:
    """Load all math knowledge points from the JSON index."""
    path = _math_kp_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    kps: list[MathKnowledgePoint] = []
    for subject in data.get("subjects", []):
        subject_name = subject.get("name", "")
        for chapter in subject.get("chapters", []):
            chapter_name = chapter.get("chapter", "")
            for kp in chapter.get("knowledge_points", []):
                kps.append(
                    MathKnowledgePoint(
                        id=kp.get("id", ""),
                        name=kp.get("name", ""),
                        chapter=chapter_name,
                        subject=subject_name,
                        keywords=kp.get("keywords", []),
                        formulas=kp.get("formulas", []),
                        difficulty=kp.get("difficulty", 1),
                        description=kp.get("description", ""),
                    )
                )
    return kps


def _tokenize(text: str) -> set[str]:
    """Split text into searchable tokens.

    Chinese characters are kept as-is; English words are lowercased.
    """
    # Remove punctuation
    cleaned = re.sub(r"[^\w一-鿿]+", " ", text)
    tokens: set[str] = set()
    for part in cleaned.split():
        if part:
            tokens.add(part.lower())
    return tokens


def match_kps(
    text: str,
    kps: list[MathKnowledgePoint] | None = None,
    subject: str | None = None,
    chapter: str | None = None,
    max_results: int = 5,
    min_score: float = 0.1,
) -> list[MathKnowledgePoint]:
    """Match text against knowledge points and return ranked results.

    Scoring:
    - Direct keyword match: 1.0 per match
    - Partial keyword match: 0.5 if keyword is substring of text
    - Subject/chapter filter: applied before scoring

    Args:
        text: The task content or query text
        kps: Pre-loaded KP list (loaded fresh if None)
        subject: Filter by subject (e.g., "高等数学")
        chapter: Filter by chapter (e.g., "一元函数微分学")
        max_results: Maximum number of results
        min_score: Minimum score threshold

    Returns:
        List of matching MathKnowledgePoint, sorted by score descending
    """
    if kps is None:
        kps = load_math_kps()

    # Filter by subject/chapter if specified
    if subject:
        kps = [kp for kp in kps if kp.subject == subject]
    if chapter:
        kps = [kp for kp in kps if kp.chapter == chapter]

    if not kps or not text:
        return []

    text_lower = text.lower()
    text_tokens = _tokenize(text)

    scored: list[tuple[MathKnowledgePoint, float]] = []
    for kp in kps:
        score = 0.0
        for kw in kp.keywords:
            kw_lower = kw.lower()
            # Direct token match
            if kw_lower in text_tokens:
                score += 1.0
            # Substring match (partial credit)
            elif kw_lower in text_lower:
                score += 0.5
            # Text contains keyword characters (fuzzy)
            elif any(c in text_lower for c in kw_lower if c.isalnum() or "一" <= c <= "鿿"):
                score += 0.1

        # Normalize by number of keywords
        if kp.keywords:
            score = score / len(kp.keywords)

        if score >= min_score:
            scored.append((kp, score))

    # Sort by score descending, then by difficulty ascending (easier first)
    scored.sort(key=lambda x: (-x[1], x[0].difficulty))
    return [kp for kp, _ in scored[:max_results]]


def match_kp_by_id(kp_id: str, kps: list[MathKnowledgePoint] | None = None) -> MathKnowledgePoint | None:
    """Look up a knowledge point by its ID."""
    if kps is None:
        kps = load_math_kps()
    for kp in kps:
        if kp.id == kp_id:
            return kp
    return None


def get_formulas_for_text(
    text: str,
    kps: list[MathKnowledgePoint] | None = None,
    subject: str | None = None,
) -> list[str]:
    """Extract formulas relevant to the given text.

    Returns a deduplicated list of formula strings.
    """
    matched = match_kps(text, kps=kps, subject=subject)
    formulas: list[str] = []
    seen: set[str] = set()
    for kp in matched:
        for f in kp.formulas:
            if f not in seen:
                seen.add(f)
                formulas.append(f)
    return formulas


def get_kp_summary_for_text(
    text: str,
    kps: list[MathKnowledgePoint] | None = None,
    subject: str | None = None,
    max_kps: int = 3,
) -> str:
    """Generate a human-readable summary of matched knowledge points.

    Returns a compact string like:
    "相关知识点：导数的定义 (难度2)、求导法则 (难度2)"
    """
    matched = match_kps(text, kps=kps, subject=subject, max_results=max_kps)
    if not matched:
        return ""

    parts = [f"{kp.name} (难度{kp.difficulty})" for kp in matched]
    return "相关知识点：" + "、".join(parts)


def enrich_task_content(
    content: str,
    kps: list[MathKnowledgePoint] | None = None,
    subject: str | None = None,
    include_formulas: bool = False,
) -> str:
    """Enrich task content with matched knowledge points and optionally formulas.

    Args:
        content: Original task content
        kps: Pre-loaded KP list
        subject: Filter by subject
        include_formulas: Whether to include formula snippets

    Returns:
        Enriched content string with KP references appended
    """
    matched = match_kps(content, kps=kps, subject=subject, max_results=3)
    if not matched:
        return content

    kp_names = "、".join(kp.name for kp in matched)
    enriched = f"{content}【{kp_names}】"

    if include_formulas:
        formulas = get_formulas_for_text(content, kps=kps, subject=subject)
        if formulas:
            enriched += f"\n公式：{'; '.join(formulas[:3])}"

    return enriched


def get_chapter_kps(
    subject: str,
    chapter: str,
    kps: list[MathKnowledgePoint] | None = None,
) -> list[MathKnowledgePoint]:
    """Get all knowledge points for a specific chapter."""
    if kps is None:
        kps = load_math_kps()
    return [kp for kp in kps if kp.subject == subject and kp.chapter == chapter]


def get_subject_chapters(subject: str, kps: list[MathKnowledgePoint] | None = None) -> list[str]:
    """Get all chapter names for a subject."""
    if kps is None:
        kps = load_math_kps()
    chapters: list[str] = []
    seen: set[str] = set()
    for kp in kps:
        if kp.subject == subject and kp.chapter not in seen:
            seen.add(kp.chapter)
            chapters.append(kp.chapter)
    return chapters


def build_kp_index_for_planning(kps: list[MathKnowledgePoint] | None = None) -> dict[str, list[str]]:
    """Build a simple {chapter: [kp_names]} index for planning context.

    Used by the planner to quickly show available KPs per chapter.
    """
    if kps is None:
        kps = load_math_kps()

    index: dict[str, list[str]] = {}
    for kp in kps:
        key = f"{kp.subject}::{kp.chapter}"
        if key not in index:
            index[key] = []
        index[key].append(kp.name)
    return index