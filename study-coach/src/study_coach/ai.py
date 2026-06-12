"""AI service layer using Claude API for question image analysis.

Requires the ANTHROPIC_API_KEY environment variable to be set.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

import anthropic

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2048


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Set it before using AI features."
        )
    return anthropic.Anthropic(api_key=api_key)


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
        model=_MODEL,
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
        model=_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def is_api_key_configured() -> bool:
    """Check if the Anthropic API key is available."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", ""))
