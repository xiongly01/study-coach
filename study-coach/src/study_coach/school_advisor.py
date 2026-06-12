"""School selection advisor — temporary module for choosing target schools.

Delete this file and remove the `school` commands from cli.py after use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class School:
    name: str
    region: str
    tier: int  # 1=top, 2=strong, 3=solid
    directions: list[str]  # embodied, llm, robotics, cv, ml, ...
    exam_math: str  # "数学一" / "数学二" / "都接受"
    exam_cs408: bool  # whether 408 is accepted
    difficulty: int  # 1=极难, 2=难, 3=中等, 4=较易
    features: list[str] = field(default_factory=list)
    labs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "region": self.region,
            "tier": self.tier,
            "directions": self.directions,
            "exam_math": self.exam_math,
            "exam_cs408": self.exam_cs408,
            "difficulty": self.difficulty,
            "features": self.features,
            "labs": self.labs,
        }


# ---------------------------------------------------------------------------
# School database — focused on 具身智能 + 大模型 + 数学一 + 408
# ---------------------------------------------------------------------------

SCHOOLS: list[School] = [
    # --- Tier 1 ---
    School(
        name="清华大学",
        region="北京",
        tier=1,
        directions=["embodied", "llm", "robotics", "ml"],
        exam_math="数学一",
        exam_cs408=False,
        difficulty=1,
        features=["AI资源顶级", "算力国内最强", "大厂校招优先", "交叉信息院具身方向活跃"],
        labs=["交叉信息院", "智能产业研究院", "计算机系"],
    ),
    School(
        name="北京大学",
        region="北京",
        tier=1,
        directions=["embodied", "llm", "ml", "cv"],
        exam_math="数学一",
        exam_cs408=False,
        difficulty=1,
        features=["智能学院近年发力具身智能", "大模型研究活跃", "学术氛围浓"],
        labs=["智能学院", "计算机系", "王选计算机研究所"],
    ),
    School(
        name="中国科学院大学(自动化所)",
        region="北京",
        tier=1,
        directions=["embodied", "llm", "cv", "robotics"],
        exam_math="数学一",
        exam_cs408=False,
        difficulty=1,
        features=["紫东太初大模型", "类脑智能", "具身智能平台", "研究所资源而非传统校园"],
        labs=["模式识别国家重点实验室", "类脑智能研究中心"],
    ),
    # --- Tier 2 ---
    School(
        name="浙江大学",
        region="华东",
        tier=2,
        directions=["embodied", "robotics", "llm", "ml"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=2,
        features=["控制学院机器人强", "CS排名顶级", "杭州产业资源好", "408统考"],
        labs=["控制学院机器人实验室", "计算机学院", "求是高等研究院"],
    ),
    School(
        name="上海交通大学",
        region="华东",
        tier=2,
        directions=["embodied", "llm", "robotics", "cv"],
        exam_math="数学一",
        exam_cs408=False,
        difficulty=2,
        features=["AI学院独立建制", "具身智能方向有布局", "上海实习资源丰富"],
        labs=["人工智能研究院", "计算机系", "自动化系"],
    ),
    School(
        name="南京大学",
        region="华东",
        tier=2,
        directions=["ml", "llm", "cv"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=2,
        features=["LAMDA实验室国际知名(周志华)", "ML理论强", "408统考"],
        labs=["LAMDA实验室", "计算机系"],
    ),
    School(
        name="哈尔滨工业大学(深圳)",
        region="华南",
        tier=2,
        directions=["embodied", "robotics", "llm"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=2,
        features=["机器人国内顶级", "深圳产业资源极好", "408统考", "就业性价比高"],
        labs=["机器人技术与系统国家重点实验室", "计算机学院"],
    ),
    School(
        name="中国科学技术大学",
        region="华东",
        tier=2,
        directions=["ml", "llm", "cv"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=2,
        features=["ML理论极强", "408统考", "学术氛围好", "微软亚研院合作多"],
        labs=["计算机学院", "大数据学院", "类脑智能技术研究中心"],
    ),
    # --- Tier 3 ---
    School(
        name="北京航空航天大学",
        region="北京",
        tier=3,
        directions=["embodied", "robotics", "cv"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=3,
        features=["无人机+机器人传统强", "具身智能方向多", "408统考", "北京实习方便"],
        labs=["计算机学院", "自动化学院", "机器人研究所"],
    ),
    School(
        name="华中科技大学",
        region="华中",
        tier=3,
        directions=["embodied", "robotics", "llm"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=3,
        features=["机器人实验室强", "408统考", "武汉生活成本低", "大厂校招覆盖"],
        labs=["机械学院机器人实验室", "计算机学院", "人工智能与自动化学院"],
    ),
    School(
        name="中山大学",
        region="华南",
        tier=3,
        directions=["llm", "ml", "cv"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=3,
        features=["超算中心在广东", "算力资源强", "408统考", "大湾区产业资源"],
        labs=["计算机学院", "人工智能学院", "国家超算广州中心"],
    ),
    School(
        name="西安交通大学",
        region="西北",
        tier=3,
        directions=["embodied", "robotics", "ml"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=3,
        features=["人机所强", "408统考", "老牌工科强校", "性价比高"],
        labs=["人机所", "计算机学院", "人工智能学院"],
    ),
    School(
        name="同济大学",
        region="华东",
        tier=3,
        directions=["embodied", "robotics", "llm"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=3,
        features=["上海实习方便", "408统考", "具身智能有布局"],
        labs=["计算机系", "电子与信息工程学院"],
    ),
    School(
        name="东南大学",
        region="华东",
        tier=3,
        directions=["robotics", "ml", "cv"],
        exam_math="数学一",
        exam_cs408=True,
        difficulty=3,
        features=["机器人方向扎实", "408统考", "南京生活成本适中", "相对好考"],
        labs=["计算机学院", "自动化学院", "机器人传感与控制技术研究所"],
    ),
]

DIRECTION_LABELS: dict[str, str] = {
    "embodied": "具身智能",
    "llm": "大模型",
    "robotics": "机器人",
    "ml": "机器学习",
    "cv": "计算机视觉",
}

DIFFICULTY_LABELS: dict[int, str] = {
    1: "极难",
    2: "较难",
    3: "中等",
}

TIER_LABELS: dict[int, str] = {
    1: "顶尖",
    2: "强势",
    3: "中坚",
}


def filter_schools(
    region: str | None = None,
    tier: int | None = None,
    direction: str | None = None,
    difficulty_max: int | None = None,
    require_408: bool = False,
    require_math1: bool = False,
) -> list[School]:
    """Filter schools by criteria."""
    result = SCHOOLS
    if region:
        result = [s for s in result if s.region == region]
    if tier:
        result = [s for s in result if s.tier == tier]
    if direction:
        result = [s for s in result if direction in s.directions]
    if difficulty_max:
        result = [s for s in result if s.difficulty >= difficulty_max]
    if require_408:
        result = [s for s in result if s.exam_cs408]
    if require_math1:
        result = [s for s in result if s.exam_math == "数学一" or s.exam_math == "都接受"]
    return result


def compare_schools(names: list[str]) -> list[School]:
    """Get school objects by name for comparison."""
    return [s for s in SCHOOLS if s.name in names]


def recommend(
    primary_direction: str = "embodied",
    secondary_direction: str = "llm",
    prefer_408: bool = True,
    max_difficulty: int = 3,
    preferred_region: str | None = None,
    top_n: int = 5,
) -> list[tuple[School, float]]:
    """Score and rank schools based on user preferences.

    Returns (school, score) pairs sorted by score descending.
    """
    scored: list[tuple[School, float]] = []

    for s in SCHOOLS:
        if s.difficulty > max_difficulty:
            continue
        if prefer_408 and not s.exam_cs408:
            continue

        score = 0.0

        # Direction match (most important)
        if primary_direction in s.directions:
            score += 4.0
        if secondary_direction in s.directions:
            score += 2.0
        # Bonus for having both directions
        if primary_direction in s.directions and secondary_direction in s.directions:
            score += 1.0

        # 408 exam match
        if s.exam_cs408:
            score += 1.5

        # Difficulty — easier schools get a slight bonus for 6-month prep
        score += (s.difficulty - 1) * 0.8  # difficulty 3 gets +1.6, difficulty 1 gets 0

        # Region preference
        if preferred_region and s.region == preferred_region:
            score += 1.0

        # Lab richness
        score += min(len(s.labs), 3) * 0.3

        scored.append((s, score))

    scored.sort(key=lambda x: -x[1])
    return scored[:top_n]
