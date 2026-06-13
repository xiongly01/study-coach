"""Knowledge-point mastery index.

Aggregates WrongQuestion records into per-knowledge-point mastery stats. The
index is a pure derivation — recomputed on demand from the wrong-question source
data, so it can never drift out of sync.

Tag canonicalization has two layers:
  - normalize_kp: pure whitespace / full-width-half-width normalization, always
    applied when building the index. Catches trivial duplicates ("极限 " vs
    "极限") with no configuration.
  - alias dictionary (data/kp_canon.json): semantic merges such as
    "数列极限" -> "极限", applied at write time so stored tags are canonical.
"""

from __future__ import annotations

import unicodedata

from .models import KnowledgePointStat, WrongQuestion


def normalize_kp(kp: str) -> str:
    """Collapse whitespace and unify full-width/half-width forms.

    NFKC maps full-width latin/digits/punctuation to their half-width twins, so
    visually identical tags written differently compare equal.
    """
    return " ".join(unicodedata.normalize("NFKC", kp).strip().split())


def canonicalize_kps(
    kps: list[str], canon: dict[str, str] | None = None
) -> list[str]:
    """Map raw tags through the alias dictionary, normalizing and de-duplicating.

    canon maps a normalized alias to its canonical name. Tags absent from the
    dictionary keep their normalized form. Order is preserved on first sight.
    """
    canon = canon or {}
    out: list[str] = []
    seen: set[str] = set()
    for kp in kps:
        canonical = canon.get(normalize_kp(kp), normalize_kp(kp))
        if canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out


def build_kp_index(
    wrong_questions: list[WrongQuestion],
) -> list[KnowledgePointStat]:
    """Aggregate wrong questions into one stat per normalized knowledge point."""
    by_key: dict[tuple[str, str], KnowledgePointStat] = {}

    for q in wrong_questions:
        for kp in q.knowledge_points:
            name = normalize_kp(kp)
            key = (name, q.subject)
            stat = by_key.get(key)
            if stat is None:
                stat = KnowledgePointStat(name=name, subject=q.subject)
                by_key[key] = stat
            stat.count += 1
            stat.total_mastery += q.mastery_level
            stat.wrong_question_ids.append(q.id)
            # created_at doubles as the weakness recency signal: most recent
            # error among the tagged questions.
            if q.created_at > stat.last_wrong_date:
                stat.last_wrong_date = q.created_at

    for stat in by_key.values():
        stat.avg_mastery = round(stat.total_mastery / stat.count, 2) if stat.count else 0.0
        # Normalize the 0-5 per-question scale to a 0-1 mastery level.
        stat.mastery_level = round(stat.avg_mastery / 5.0, 3)

    return list(by_key.values())


def rank_weak_kps(
    index: list[KnowledgePointStat], limit: int | None = None
) -> list[KnowledgePointStat]:
    """Rank knowledge points by weakness.

    Order: lowest mastery first, then highest error count, then most recent
    error. Stable multi-key sort applies the tiebreakers before the primary key.
    """
    ranked = sorted(index, key=lambda s: s.last_wrong_date, reverse=True)
    ranked.sort(key=lambda s: s.count, reverse=True)
    ranked.sort(key=lambda s: s.mastery_level)
    return ranked[:limit] if limit else ranked


def mastery_lookup(
    index: list[KnowledgePointStat],
) -> dict[tuple[str, str], float]:
    """Build a {(kp_name, subject): mastery_level} map for fast per-question lookup."""
    return {(s.name, s.subject): s.mastery_level for s in index}
