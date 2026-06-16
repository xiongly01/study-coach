"""Syllabus data access primitives.

Provides read-only helpers for the syllabus.json reference data:
- chapters(subject) -> list of chapter names
- knowledge_points(subject, chapter) -> list of KP strings
- section_weights(subject) -> {section_name: weight}
- outline(subject) -> full structure for AI context

All helpers gracefully degrade when syllabus.json is absent or malformed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _syllabus_path() -> Path:
    """Return the path to data/syllabus.json."""
    return Path(__file__).resolve().parent.parent.parent / "data" / "syllabus.json"


def load_syllabus() -> dict[str, Any]:
    """Load the syllabus.json file. Returns empty dict if missing or malformed."""
    path = _syllabus_path()
    if not path.exists():
        return {}
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _subject_data(syllabus: dict[str, Any], subject: str) -> dict[str, Any] | None:
    """Return the subject block from syllabus, or None if not found."""
    subjects = syllabus.get("subjects", {})
    return subjects.get(subject)


def chapters(syllabus: dict[str, Any], subject: str) -> list[str]:
    """Return all chapter names for a subject, flattened across sections.

    Example: chapters(syl, "数学一") -> ["函数、极限、连续", "一元函数微分学", ...]
    """
    sd = _subject_data(syllabus, subject)
    if not sd:
        return []
    result: list[str] = []
    for sec in sd.get("sections", []):
        for ch in sec.get("chapters", []):
            name = ch.get("name")
            if name:
                result.append(name)
    return result


def knowledge_points(
    syllabus: dict[str, Any], subject: str, chapter: str
) -> list[str]:
    """Return knowledge points for a specific chapter within a subject.

    Example: knowledge_points(syl, "数学一", "一元函数微分学")
             -> ["导数定义", "微分", "复合函数求导", ...]
    """
    sd = _subject_data(syllabus, subject)
    if not sd:
        return []
    for sec in sd.get("sections", []):
        for ch in sec.get("chapters", []):
            if ch.get("name") == chapter:
                kps = ch.get("knowledge_points", [])
                return list(kps) if isinstance(kps, list) else []
    return []


def section_weights(syllabus: dict[str, Any], subject: str) -> dict[str, float]:
    """Return {section_name: weight} for a subject.

    Example: section_weights(syl, "数学一")
             -> {"高等数学": 0.6, "线性代数": 0.2, "概率论与数理统计": 0.2}
    """
    sd = _subject_data(syllabus, subject)
    if not sd:
        return {}
    result: dict[str, float] = {}
    for sec in sd.get("sections", []):
        name = sec.get("name")
        weight = sec.get("weight")
        if name and isinstance(weight, (int, float)):
            result[name] = float(weight)
    return result


def outline(syllabus: dict[str, Any], subject: str) -> dict[str, Any]:
    """Return the full subject outline for AI context injection.

    Returns a compact structure:
    {
        "score": 150,
        "sections": [
            {"name": "高等数学", "weight": 0.6, "chapters": ["函数、极限、连续", ...]},
            ...
        ]
    }
    """
    sd = _subject_data(syllabus, subject)
    if not sd:
        return {}
    sections: list[dict[str, Any]] = []
    for sec in sd.get("sections", []):
        sec_name = sec.get("name")
        if not sec_name:
            continue
        chapters_list = [ch.get("name", "") for ch in sec.get("chapters", [])]
        sections.append({
            "name": sec_name,
            "weight": sec.get("weight", 0.0),
            "chapters": [c for c in chapters_list if c],
        })
    return {
        "score": sd.get("score", 0),
        "sections": sections,
    }


def chapter_block(syllabus: dict[str, Any], subjects: list[str] | None = None) -> str:
    """Build a compact chapter listing for AI prompt injection.

    Returns a multiline string like:
    数学一 章节：
      高等数学：函数、极限、连续 | 一元函数微分学 | ...
      线性代数：行列式 | 矩阵 | ...
    ...
    """
    if subjects is None:
        subjects = list(syllabus.get("subjects", {}).keys())
    lines: list[str] = []
    for subj in subjects:
        sd = _subject_data(syllabus, subj)
        if not sd:
            continue
        lines.append(f"{subj} 章节：")
        for sec in sd.get("sections", []):
            sec_name = sec.get("name", "")
            ch_names = [ch.get("name", "") for ch in sec.get("chapters", [])]
            ch_names = [c for c in ch_names if c]
            if ch_names:
                lines.append(f"  {sec_name}：{' | '.join(ch_names)}")
    return "\n".join(lines)
