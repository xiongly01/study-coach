"""End-to-end smoke test for the plan cascade + knowledge-point review layer.

Runs against an isolated temp data dir so it never touches real data. Exits
non-zero on the first failing assertion and prints a per-step summary.

Covers, in order:
  1. Yearly plan derivation + store round-trip
  2. KP mastery index aggregation + weakness ranking
  3. KP-driven review selection (weak KP outranks high-mastery due card)
  4. Monthly weight derivation (phase anchor, deficit/KP nudge, normalization)
  5. Monthly plan generation + Planner agent fallback
  6. Daily plan consumes monthly weights + embeds the review session
  7. Drift detection (clean -> silent, drifted -> signals)
  8. Agent fallback never yields an invalid plan
  9. API surface (yearly / monthly / drift / KP review pick)
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date, timedelta

from fastapi.testclient import TestClient

from study_coach import ai, planner as P, supervisor as sup, wrong_book as wb
from study_coach.kp_index import build_kp_index, rank_weak_kps
from study_coach.models import (
    Config,
    DailyPlan,
    LongtermPlan,
    Milestone,
    Task,
    WrongQuestion,
    YearlyPlan,
)
from study_coach.store import Store
from study_coach.web import server as srv


def _fresh_store() -> tuple[str, Store]:
    d = tempfile.mkdtemp(prefix="sc_smoke_")
    return d, Store(d)


def step(name: str) -> None:
    print(f"\n— {name} —")


# 1 -----------------------------------------------------------------------
step("yearly plan derivation + round-trip")
_d, s = _fresh_store()
s.save_config(Config(exam_date="2026-12-26", subjects=["数学一", "英语一", "政治", "408"]))
yp = s.load_yearly_plan()
assert len(yp.phases) == 3, "default yearly plan has 3 phases"
phase = yp.phase_for_date("2026-06-01")
assert phase and phase.name == "基础阶段", f"June resolves to 基础, got {phase}"
s.save_yearly_plan(yp)
assert s.load_yearly_plan().phases[0].weight_overrides == yp.phases[0].weight_overrides
print("  ok: 3 phases, June -> 基础阶段, round-trip stable")

# 2 -----------------------------------------------------------------------
step("KP mastery index + weakness ranking")
for i in range(3):
    s.append_wrong_question(WrongQuestion(
        id=f"lim{i}", subject="数学一", knowledge_points=["极限"],
        mastery_level=i % 2, created_at="2026-06-13",
    ))
s.append_wrong_question(WrongQuestion(
    id="mat1", subject="数学一", knowledge_points=["矩阵"],
    mastery_level=4, created_at="2026-06-01",
))
idx = build_kp_index(s.load_wrong_questions())
by = {x.name: x for x in idx}
assert by["极限"].count == 3 and by["矩阵"].count == 1
assert rank_weak_kps(idx)[0].name == "极限", "weakest KP ranks first"
print(f"  ok: 极限 mastery={by['极限'].mastery_level}, 矩阵 mastery={by['矩阵'].mastery_level}")

# 3 -----------------------------------------------------------------------
step("KP-driven review selection")
res = wb.pick_reviews_kp_aware(s, time_budget_minutes=40)
ids = [it["question"]["id"] for it in res["items"]]
assert ids.index("mat1") > ids.index("lim0"), "weak KP must beat high-mastery due card"
print(f"  ok: order {ids} — weak 极限 cards before mastered 矩阵")

# 4 -----------------------------------------------------------------------
step("monthly weight derivation")
baseline, audit = P.derive_monthly_weights(yp, "2026-06", s.load_config())
assert abs(sum(baseline.values()) - 1.0) < 1e-6
comp = {"subject_deficit": {"数学一": 300}, "adherence_rate": 0.6}
nudged, _ = P.derive_monthly_weights(yp, "2026-06", s.load_config(), comp, idx)
assert nudged["数学一"] > baseline["数学一"], "deficit+weak KP boosts 数学一"
assert abs(sum(nudged.values()) - 1.0) < 1e-6
print(f"  ok: base 数学={baseline['数学一']:.2f} -> nudged {nudged['数学一']:.2f}")

# 5 -----------------------------------------------------------------------
step("monthly plan generation + Planner fallback")
mp = P.generate_monthly_plan(s, "2026-06")
assert s.monthly_plan_exists("2026-06")
assert mp.generated_from["source"] in ("ai", "fallback")
assert abs(sum(mp.subject_weights.values()) - 1.0) < 1e-6
print(f"  ok: source={mp.generated_from['source']}, weights cover all subjects")

# 6 -----------------------------------------------------------------------
step("daily plan consumes monthly weights + review session")
s.save_longterm_plan(LongtermPlan.default_plan("2026-12-26"))
plan = P.create_today_plan(s)
subjects = [t.subject for t in plan.tasks]
assert "复习" in subjects, "review task embedded in daily plan"
rev = next(t for t in plan.tasks if t.subject == "复习")
print(f"  ok: review task = '{rev.content}' ({rev.planned_minutes}m)")

# 7 -----------------------------------------------------------------------
step("drift detection")
clean_d, clean_s = _fresh_store()
clean_s.save_config(Config())
clean_s.save_longterm_plan(LongtermPlan(milestones=[
    Milestone(name="x", deadline=(date.today() + timedelta(days=30)).isoformat())
]))
assert sup.detect_drift(clean_s)["trigger_replan"] is False, "clean state silent"
# now make the first store drift: low execution days
today = date.today()
for i in range(4):
    s.save_daily_plan(DailyPlan(date=(today - timedelta(days=i)).isoformat(), tasks=[
        Task(subject="数学一", content="x", planned_minutes=480, actual_minutes=100)
    ]))
drifted = sup.detect_drift(s)
assert drifted["trigger_replan"] is True
print(f"  ok: clean=False, drifted=True ({len(drifted['signals'])} signals)")

# 8 -----------------------------------------------------------------------
step("agent fallback yields valid plan on bad input")
base = {"数学一": 0.4, "408": 0.3, "英语一": 0.2, "政治": 0.1}
subjects = list(base.keys())
# Garbage / non-numeric AI values must be ignored; baseline ratios preserved.
merged = ai._reconcile_weights({"数学一": "garbage", "408": None, "英语一": -1}, base, subjects)
assert merged == base, f"garbage ignored, baseline kept: {merged}"
# Partial numeric override honored then renormalized.
merged2 = ai._reconcile_weights({"数学一": 0.8}, base, subjects)
assert merged2["数学一"] > base["数学一"], "numeric override applied"
assert abs(sum(merged2.values()) - 1.0) < 1e-6
proposal = ai.agent_plan_monthly({
    "month": "2026-07", "subjects": subjects, "baseline_weights": base,
})
assert set(proposal["subject_weights"]) == set(subjects)
assert abs(sum(proposal["subject_weights"].values()) - 1.0) < 1e-6
print(f"  ok: garbage ignored, overrides honored, agent plan normalized (source={proposal['source']})")

# 9 -----------------------------------------------------------------------
step("API surface")
ad, as_ = _fresh_store()
as_.save_config(Config(exam_date="2026-12-26", subjects=["数学一", "英语一", "政治", "408"]))
srv._store = lambda: Store(ad)
c = TestClient(srv.app)
for method, url, body, key in [
    ("GET", "/api/yearly", None, "plan"),
    ("POST", "/api/yearly/regenerate", None, "ok"),
    ("POST", "/api/monthly/generate", None, "ok"),
    ("GET", "/api/monthly?month=2026-06", None, "plan"),
    ("GET", "/api/drift", None, "signals"),
    ("GET", "/api/wrong-book/review/pick?budget=40", None, "count"),
    ("GET", "/api/wrong-book/knowledge-points", None, "knowledge_points"),
]:
    r = c.request(method, url, json=body) if method == "POST" else c.get(url)
    assert r.status_code == 200, f"{method} {url} -> {r.status_code}: {r.text}"
    assert key in r.json(), f"{url} missing key '{key}'"
print("  ok: 7 endpoints return 200 with expected shape")

print("\nALL SMOKE CHECKS PASSED [OK]")
