"""AI service layer using Claude API for question image analysis.

Credentials are read from data/ai_secret.json (api_key, base_url) and fall
back to the ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL environment variables.
The secret file is excluded from version control via study-coach/.gitignore.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import anthropic

# Default model when none is configured. The active model is resolved from
# ANTHROPIC_MODEL (or the secret file) so Anthropic-native and compatible
# endpoints (e.g. BigModel/GLM) can both be used.
_DEFAULT_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048

# Resolves to <project>/data/ai_secret.json regardless of CWD.
_SECRET_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ai_secret.json"


def _load_credentials() -> dict[str, str]:
    """Return {auth_token, api_key, base_url, model}.

    Env vars are the base layer; the secret file overrides them when present.
    Both Bearer-token (ANTHROPIC_AUTH_TOKEN) and x-api-key (ANTHROPIC_API_KEY)
    auth schemes are supported, so Anthropic-native and compatible endpoints
    (BigModel/GLM) work without code changes.
    """
    cfg = {
        "auth_token": os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
        "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "base_url": os.environ.get("ANTHROPIC_BASE_URL", ""),
        "model": os.environ.get("ANTHROPIC_MODEL", ""),
    }
    if _SECRET_PATH.exists():
        data = json.loads(_SECRET_PATH.read_text(encoding="utf-8"))
        for key, value in cfg.items():
            cfg[key] = data.get(key, value) or value
    return cfg


def _client() -> anthropic.Anthropic:
    cfg = _load_credentials()
    kwargs: dict[str, Any] = {}
    if cfg["auth_token"]:
        # Bearer auth — used by BigModel/GLM and other compatible endpoints.
        kwargs["auth_token"] = cfg["auth_token"]
    elif cfg["api_key"]:
        # x-api-key auth — used by Anthropic-native endpoints.
        kwargs["api_key"] = cfg["api_key"]
    else:
        raise RuntimeError(
            "No auth configured. Put auth_token/base_url/model in "
            "study-coach/data/ai_secret.json, or set ANTHROPIC_AUTH_TOKEN "
            "(or ANTHROPIC_API_KEY)."
        )
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    return anthropic.Anthropic(**kwargs)


def _model() -> str:
    return _load_credentials()["model"] or _DEFAULT_MODEL


def analyze_question_image(
    image_bytes: bytes,
    media_type: str = "image/jpeg",
    subject_hint: str = "",
) -> dict[str, Any]:
    """Analyze a question image using Claude Vision.

    Returns a dict with keys:
        question_text, knowledge_points, difficulty, answer, topic
    """
    client = _client()
    b64 = base64.std_b64encode(image_bytes).decode("utf-8")

    subject_line = f"科目提示：{subject_hint}\n" if subject_hint else ""

    prompt = f"""你是一位考研辅导专家。请分析这道题目图片，提取以下信息并以 JSON 格式返回：

{subject_line}返回格式：
{{
    "question_text": "完整的题目文字（包含所有条件、选项）",
    "topic": "所属章节/主题",
    "knowledge_points": ["知识点1", "知识点2", ...],
    "difficulty": 3,
    "answer": "详细解析和答案"
}}

要求：
- question_text 必须完整还原题目内容，不要省略
- knowledge_points 列出所有相关知识点，用于后续复习追踪
- difficulty 为 1-5 的整数（1=基础，5=极难）
- answer 提供详细的解题思路和标准答案
- 如果图片中有多道题，只分析第一道

只返回 JSON，不要返回其他内容。"""

    response = client.messages.create(
        model=_model(),
        max_tokens=_MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # Remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "question_text": text,
            "topic": "",
            "knowledge_points": [],
            "difficulty": 3,
            "answer": "",
            "_raw": text,
        }


def generate_review_hint(question_text: str, knowledge_points: list[str]) -> str:
    """Generate a concise review hint for a wrong question."""
    client = _client()

    prompt = f"""你是一位考研辅导专家。根据以下错题和知识点，生成一段简短的复习提示（100字以内），
帮助学生在复习时快速回忆核心考点和解题思路。

题目：{question_text}
知识点：{', '.join(knowledge_points)}

只返回复习提示文字，不要返回其他内容。"""

    response = client.messages.create(
        model=_model(),
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def is_api_key_configured() -> bool:
    """Check if any auth credential (token or api key) is available."""
    cfg = _load_credentials()
    return bool(cfg["auth_token"] or cfg["api_key"])


# ---------------------------------------------------------------------------
# Agent decision points
#
# These wrap LLM calls at two planning decisions. They never mutate state: each
# returns a structured *suggestion*. When the API key is absent or the call
# fails, they return the deterministic baseline passed in via context, so the
# system stays runnable and reversible without AI.
# ---------------------------------------------------------------------------


def _strip_code_fences(text: str) -> str:
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def _parse_json_lenient(text: str) -> dict[str, Any]:
    text = _strip_code_fences(text.strip())
    return json.loads(text)


def _reconcile_weights(
    ai_weights: Any, baseline: dict[str, float], subjects: list[str]
) -> dict[str, float]:
    """Merge AI-proposed weights onto the baseline, then normalize.

    Guarantees coverage of every subject and a sum of 1.0 regardless of what
    the model returns: AI values are honored where present and numeric, the
    baseline fills the rest, and the result is renormalized.
    """
    if not isinstance(ai_weights, dict):
        return dict(baseline)
    merged = {s: baseline.get(s, 0.0) for s in subjects}
    for s in subjects:
        v = ai_weights.get(s)
        if isinstance(v, (int, float)) and v >= 0:
            merged[s] = float(v)
    total = sum(merged.values())
    if total <= 0:
        return dict(baseline)
    return {s: round(merged[s] / total, 4) for s in merged}


def agent_plan_monthly(context: dict[str, Any]) -> dict[str, Any]:
    """Propose a monthly plan: subject weights + goals.

    Returns {"subject_weights", "goals", "rationale", "source"} where source is
    "ai" or "fallback". The deterministic baseline in context["baseline_weights"]
    is returned verbatim whenever AI is unavailable, so callers can always
    persist a valid plan.
    """
    baseline = dict(context.get("baseline_weights", {}))
    subjects = context.get("subjects", list(baseline))
    chapter_listing = context.get("chapter_listing", "")

    if not is_api_key_configured():
        return {
            "subject_weights": baseline,
            "goals": [],
            "rationale": "AI 未配置，使用确定性基线",
            "source": "fallback",
        }

    chapter_section = f"\n各科目章节（供目标落地参考）：\n{chapter_listing}\n" if chapter_listing else ""

    prompt = f"""你是考研规划助手。基于以下信号，为 {context.get('month', '本月')}（{context.get('phase', '')}）提出各科目时间权重与月度目标。

信号：
- 科目：{', '.join(subjects)}
- 近30天完成率：{context.get('adherence_rate', '未知')}
- 各科目时间赤字（分钟）：{context.get('subject_deficit', {})}
- 最薄弱知识点：{[kp.get('name') for kp in context.get('top_weak_kps', [])]}
- 确定性基线权重：{baseline}
{chapter_section}
返回 JSON：
{{
    "subject_weights": {{"数学一": 0.4, "408": 0.3, "英语一": 0.2, "政治": 0.1}},
    "goals": [{{"subject": "数学一", "goal": "完成高等数学：函数极限连续 + 一元函数微分学"}}],
    "rationale": "一句话说明调整理由"
}}

要求：
- subject_weights 必须覆盖所有科目，数值非负
- goals 每科最多一条，目标具体可验收，优先落到真实章节名
- 只返回 JSON"""

    try:
        client = _client()
        response = client.messages.create(
            model=_model(),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _parse_json_lenient(response.content[0].text)
        weights = _reconcile_weights(parsed.get("subject_weights"), baseline, subjects)
        goals = parsed.get("goals", []) if isinstance(parsed.get("goals"), list) else []
        return {
            "subject_weights": weights,
            "goals": [
                g for g in goals if isinstance(g, dict) and g.get("subject") in subjects
            ],
            "rationale": str(parsed.get("rationale", "")),
            "source": "ai",
        }
    except Exception as exc:  # network, parse, or API errors -> safe fallback
        return {
            "subject_weights": baseline,
            "goals": [],
            "rationale": f"AI 调用失败（{type(exc).__name__}），使用基线",
            "source": "fallback",
        }


def agent_suggest_kp_merges(context: dict[str, Any]) -> dict[str, Any]:
    """Propose alias -> canonical merges for near-duplicate knowledge points.

    context: {"knowledge_points": [name, ...]}
    Returns {"merges": [{"alias", "canonical", "reason"}], "source"}.

    Semantic merging is delegated to the model: substring heuristics are too
    unreliable for Chinese (e.g. "代数" vs "线性代数"). With no AI the function
    returns an empty list rather than guessing.
    """
    names = context.get("knowledge_points", [])
    if not is_api_key_configured() or len(names) < 2:
        return {"merges": [], "source": "fallback"}

    prompt = f"""你是考研知识点归一助手。以下是从错题中提取的知识点列表，可能存在重复或同义项：

{json.dumps(names, ensure_ascii=False)}

请找出应当合并的别名对（指向同一考点），返回 JSON：
{{
    "merges": [
        {{"alias": "数列极限", "canonical": "极限", "reason": "数列极限是极限的子类"}}
    ]
}}

要求：
- alias 与 canonical 都必须来自上面列表（canonical 是保留的标准名）
- 只在确信同义时才合并，宁缺毋滥
- 只返回 JSON"""

    try:
        client = _client()
        response = client.messages.create(
            model=_model(),
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _parse_json_lenient(response.content[0].text)
        valid = set(names)
        merges = [
            m for m in parsed.get("merges", [])
            if isinstance(m, dict)
            and m.get("alias") in valid
            and m.get("canonical") in valid
            and m.get("alias") != m.get("canonical")
        ]
        return {"merges": merges, "source": "ai"}
    except Exception:
        return {"merges": [], "source": "fallback"}


def agent_pick_reviews(context: dict[str, Any]) -> dict[str, Any]:
    """Curate today's review set, falling back to the deterministic ranking.

    context:
        candidates: list of {question_id, subject, knowledge_points,
                             mastery_level, due, score}  (already scored)
        max_items: int
    Returns {"question_ids": [...], "rationale", "source"}.
    """
    candidates = context.get("candidates", [])
    max_items = int(context.get("max_items", len(candidates)))

    # Deterministic ranking: highest score first (candidates carry a precomputed score).
    ranked = sorted(candidates, key=lambda c: c.get("score", 0.0), reverse=True)
    baseline_ids = [c["question_id"] for c in ranked[:max_items]]

    if not is_api_key_configured() or not candidates:
        return {
            "question_ids": baseline_ids,
            "rationale": "AI 未配置或无候选，按确定性排序",
            "source": "fallback",
        }

    prompt = f"""你是考研复习调度助手。从以下候选错题中选出今日最该复查的 {max_items} 题，按优先级排序。

候选（已含弱点评级 score，越高越紧急）：
{json.dumps(candidates, ensure_ascii=False)}

返回 JSON：
{{
    "question_ids": ["id1", "id2"],
    "rationale": "一句话说明取舍理由"
}}

要求：question_ids 数量不超过 {max_items}，只返回 JSON。"""

    try:
        client = _client()
        response = client.messages.create(
            model=_model(),
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _parse_json_lenient(response.content[0].text)
        ids = parsed.get("question_ids", [])
        valid = {c["question_id"] for c in candidates}
        # Keep only valid ids, cap at max_items; pad from baseline if short.
        chosen = [i for i in ids if i in valid][:max_items]
        for bid in baseline_ids:
            if bid not in chosen and len(chosen) < max_items:
                chosen.append(bid)
        return {
            "question_ids": chosen,
            "rationale": str(parsed.get("rationale", "")),
            "source": "ai",
        }
    except Exception as exc:
        return {
            "question_ids": baseline_ids,
            "rationale": f"AI 调用失败（{type(exc).__name__}），按确定性排序",
            "source": "fallback",
        }
