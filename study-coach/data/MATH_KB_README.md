# 数学知识点匹配系统

## 概述

基于《张宇数学公式手册》构建的知识点匹配系统，可在生成学习任务时自动匹配相关知识点。

## 文件结构

```
study-coach/
├── data/
│   ├── math_knowledge_points.json    # 知识点详细数据库 (92个知识点)
│   └── math_knowledge_index.md       # 快速查阅索引
├── src/study_coach/
│   ├── math_matcher.py               # 匹配器核心模块
│   └── planner.py                    # 已集成匹配功能
└── scripts/
    └── test_math_matcher.py          # 测试脚本
```

## 知识点覆盖

| 科目 | 章节数 | 知识点数 |
|-----|-------|---------|
| 高等数学 | 8 | 45 |
| 线性代数 | 6 | 21 |
| 概率论与数理统计 | 6 | 26 |
| **总计** | **20** | **92** |

## 使用方法

### 1. CLI 命令

```bash
# 匹配知识点
study-coach match "洛必达法则求极限" --subject "高等数学"

# 显示公式
study-coach match "求导数" --formulas
```

### 2. Python API

```python
from study_coach.math_matcher import (
    load_math_kps,
    match_kps,
    get_formulas_for_text,
    get_kp_summary_for_text,
)

# 加载知识点
kps = load_math_kps()

# 匹配知识点
matched = match_kps("洛必达法则求极限", kps=kps, subject="高等数学")
for kp in matched:
    print(f"{kp.name}: {kp.description}")

# 获取公式
formulas = get_formulas_for_text("求导数", kps=kps)

# 生成摘要
summary = get_kp_summary_for_text("求极限", kps=kps)
```

### 3. 任务自动匹配

在 `planner.py` 中已集成，生成数学任务时会自动：

1. 从月度目标提取章节
2. 从教学大纲获取知识点列表
3. **新增**: 从公式手册匹配相关知识点
4. 将匹配结果附加到任务内容

```python
# planner.py 中的调用
task = _enrich_task_with_kps(task, subject, monthly_goals, syllabus)
# 对于数学科目，会额外匹配公式手册知识点
```

## 匹配算法

### 评分机制

```
匹配分数 = Σ (关键词匹配分) / 关键词总数

关键词匹配分:
- 完全匹配: 1.0
- 子串匹配: 0.5
- 部分字符匹配: 0.1
```

### 结果排序

1. 按匹配分数降序
2. 同分时按难度升序（先易后难）

## 知识点数据结构

```json
{
  "id": "gao_shu_015",
  "name": "洛必达法则",
  "chapter": "一元函数微分学",
  "subject": "高等数学",
  "keywords": ["洛必达", "0/0型", "∞/∞型", "未定式"],
  "formulas": ["0/0型或∞/∞型: lim f(x)/g(x) = lim f'(x)/g'(x)"],
  "difficulty": 2,
  "description": "处理0/0、∞/∞型未定式的极限"
}
```

## 难度等级

| 等级 | 描述 | 典型内容 |
|-----|------|---------|
| 1 | 基础概念 | 定义、基本公式 |
| 2 | 基本方法 | 求导、积分、极限计算 |
| 3 | 综合应用 | 多知识点综合、证明题 |
| 4 | 难度较大 | 压轴题型、复杂证明 |

## 扩展建议

### 1. 添加更多知识点

编辑 `data/math_knowledge_points.json`，按相同格式添加新知识点。

### 2. 自定义匹配规则

修改 `math_matcher.py` 中的 `match_kps()` 函数调整评分权重。

### 3. 集成到其他模块

```python
# 在错题本中显示相关公式
from study_coach.math_matcher import get_formulas_for_text

formulas = get_formulas_for_text(question.topic)
# 显示在错题详情中
```

## 测试验证

```bash
cd study-coach
python scripts/test_math_matcher.py
```

预期输出：
- 加载 92 个知识点
- 匹配测试通过
- 公式提取正常