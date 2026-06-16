# study-coach

考研备考监督工具。以「年度阶段 → 月度计划 → 每日任务」三层级联为核心，在关键决策点接入 AI agent，执行数据回流驱动计划自我纠偏。提供 CLI 和 Web 界面。

## 工作流总览

```
年度阶段 (基础/强化/冲刺, 按考试日反推, 各阶段科目权重不同)
      │  当前日期落在某阶段 → 取该阶段基准权重
      ▼
月度计划  ◄── 信号: 合规性(各科时间赤字、完成率) + 错题知识点弱点
 确定性基线调权重 → AI agent 精调权重+目标 (AI 不可用则回退基线)
      │  月度权重
      ▼
每日任务  顺延昨日未完成 + 按月度权重分配剩余时长 + 错题复习占预算
      │  番茄钟记录真实执行时长
      ▼
执行数据回流 → 漂移检测 (完成率/连续低执行/里程碑逾期/知识点停滞)
            → 触发则一键重新生成月度计划，闭环纠偏
```

核心设计：**确定性算法始终兜底，agent 只在决策点返回建议、不直接改状态**。未配置 AI 时自动退化为基础算法，系统照常运行。

## 功能概览

| 模块 | 说明 |
|------|------|
| **学习计划** | 三层级联：年度阶段 → 月度计划（AI 调权重+目标）→ 每日任务（顺延未完成、按权重分配） |
| **漂移检测** | 合规性检查 + 漂移信号识别 + 一键重新规划，执行数据闭环驱动计划纠偏 |
| **番茄钟** | 25 分钟一轮，记录学习时长，Web 端实时同步 |
| **自测系统** | 题库管理，随机抽题测试，薄弱知识点分析 |
| **错题本** | 拍照上传 → AI 识别分析 → 知识点归一 → 间隔复习（1/3/7/14/30天）→ 弱点优先调度 |
| **进度报告** | 周报生成，合规性检查，低完成率自动下调每日时长 |
| **院校选择** | 内置院校数据库，筛选/对比/推荐（临时模块） |

## 技术栈

- **后端**: Python 3.10+, FastAPI, Uvicorn
- **前端**: Vanilla HTML/CSS/JS（无框架）
- **CLI**: Typer + Rich
- **数据存储**: 本地 JSON 文件（无数据库，不联网不上传）
- **AI**: Anthropic 兼容 API — 支持官方 Claude 及 GLM/BigModel 等兼容端点

## 安装

```bash
conda activate pytorch-gpu
pip install typer rich fastapi uvicorn websockets anthropic python-multipart
```

进入项目目录，以开发模式安装：

```bash
cd study-coach
pip install -e .
```

## 快速开始

### 1. 启动 Web 界面

```bash
study-coach room
```

浏览器访问 `http://localhost:8900`，首次使用进入初始设置页面。手机浏览器访问 `http://<电脑IP>:8900` 同样可用，微信内可直接拍照上传。

### 2. CLI 使用

```bash
# 初始化（设置考试日期、目标院校、每日时长）
study-coach init

# 查看状态 / 今日计划
study-coach status
study-coach plan

# 番茄钟 / 完成任务 / 每日签到
study-coach start <task_id>
study-coach done <task_id>
study-coach checkin

# 三层级联计划
study-coach yearly [--regenerate]     # 查看/重建年度阶段
study-coach monthly [-g]              # 查看/生成月度计划（触发 agent）
study-coach drift                     # 漂移检测，超标则建议重规划

# 错题复查（按知识点弱点抽取，--agent 让 AI 精选）
study-coach review [-b 40] [--agent]

# 生成周报（--adjust 根据完成率下调每日时长）
study-coach report [--adjust]

# 自测
study-coach test <subject> [-n 5] [--add]
```

## 项目结构

```
study-coach/
├── data/                        # 运行时数据（JSON 文件）
│   ├── config.json              # 用户配置
│   ├── yearly_plan.json         # 年度阶段（缺失时按考试日派生默认）
│   ├── longterm_plan.json       # 里程碑
│   ├── monthly/                 # 月度计划 YYYY-MM.json
│   ├── daily/                   # 每日计划 YYYY-MM-DD.json
│   ├── tests/                   # 领库 + 测试结果
│   ├── reports/                 # 周报 Markdown
│   ├── wrong_book/              # 错题本数据 + 图片
│   ├── syllabus.json            # 考纲章节/知识点/题型分值参考
│   ├── kp_canon.json            # 知识点别名→标准名归一映射
│   └── ai_secret.json           # AI 凭证（已 gitignore）
├── src/study_coach/
│   ├── models.py                # 数据模型（dataclass）
│   ├── store.py                 # JSON 文件存储层
│   ├── syllabus.py              # 考纲数据访问 primitive
│   ├── planner.py               # 年度/月度/每日三层级联规划
│   ├── tracker.py               # 番茄钟（CLI 版）
│   ├── reporter.py              # 日报 + 周报生成
│   ├── examiner.py              # 题库 + 自测
│   ├── supervisor.py            # 合规性检查 + 漂移检测 + 时长下调
│   ├── kp_index.py              # 知识点掌握度索引（由错题聚合派生）
│   ├── school_advisor.py        # 院校选择（临时）
│   ├── ai.py                    # Anthropic 兼容封装 + agent 决策点
│   ├── wrong_book.py            # 错题本业务逻辑 + 间隔复习
│   ├── cli.py                   # CLI 入口
│   └── web/
│       ├── server.py            # FastAPI 服务 + 全部 API 端点
│       └── static/
│           ├── index.html       # SPA 页面
│           ├── style.css        # 样式（深色主题 + 移动端适配）
│           ├── app.js           # 路由 + 公共工具
│           └── tabs/            # 各 Tab 逻辑
│               ├── today.js     # 今日（番茄钟 + 任务 + 反思）
│               ├── plan.js      # 计划（年度阶段 + 月度 + 漂移 + 里程碑 + 历史）
│               ├── exam.js      # 自测（题库 + 测试）
│               ├── wrongbook.js # 错题本（上传 + 列表 + 复习 + 统计）
│               └── overview.js  # 总览（周统计 + 报告 + 合规性）
└── pyproject.toml
```

## 配置

### 考试配置

通过 Web 初始设置页面或直接编辑 `data/config.json`：

```json
{
  "exam_date": "2026-12-26",
  "subjects": ["数学一", "英语一", "政治", "408"],
  "math_scope": ["高等数学", "线性代数", "概率论与数理统计"],
  "cs408_scope": ["数据结构", "计算机组成原理", "操作系统", "计算机网络"],
  "daily_study_hours": 8,
  "target_school": "待定",
  "target_major": "待定"
}
```

`daily_study_hours` 可被 `report --adjust` 在低完成率时自动下调。

### AI 服务

凭证读取优先级：`data/ai_secret.json` > 环境变量。两种认证方式均支持，官方 Claude 与 GLM/BigModel 等兼容端点无需改代码。

`data/ai_secret.json`：

```json
{
  "api_key": "sk-...",
  "auth_token": "可选，Bearer 认证（GLM/BigModel 等）",
  "base_url": "可选，自定义端点",
  "model": "可选，覆盖默认模型"
}
```

或用环境变量：`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL` / `ANTHROPIC_MODEL`。

配置后，错题 AI 分析、月度计划 agent、复习精选、知识点归一功能启用；未配置时全部自动回退为确定性算法，仍可正常使用。

## Web 界面说明

访问 `http://localhost:8900`，底部 Tab 栏切换：

| Tab | 功能 |
|-----|------|
| **今日** | 番茄钟计时、今日任务列表（生成计划时自动补齐当月计划、可勾选完成/手动添加）、每日反思 |
| **计划** | 漂移信号（超标时一键重生月度）、年度阶段（重建）、本月计划（生成，显示 AI/基线来源）、里程碑、近 7 天历史 |
| **自测** | 题库浏览/添加、按科目随机自测、测试记录查看 |
| **错题本** | 拍照/上传 → AI 识别 → 知识点标签 → 间隔复习 → 掌握度统计 |
| **总览** | 本周学习时长柱状图、周报生成/查看、7 天合规性指标 |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 保存配置（同时初始化默认长期计划） |
| GET | `/api/today` | 今日计划 |
| POST | `/api/plan/generate` | 生成今日计划（当月无计划时自动补齐月度） |
| POST | `/api/tasks` | 添加任务 |
| POST | `/api/tasks/{id}/done` | 完成任务 |
| POST | `/api/tasks/{id}/undone` | 取消完成 |
| POST | `/api/checkin` | 保存反思 |
| GET | `/api/milestones` | 里程碑列表 + 告警 |
| POST | `/api/milestones/{id}/toggle` | 切换里程碑状态 |
| GET | `/api/yearly` | 年度阶段（缺失时按考试日派生默认） |
| POST | `/api/yearly/regenerate` | 按考试日重建年度阶段 |
| GET | `/api/monthly` | 当月计划 |
| GET | `/api/monthly/all` | 全部月度计划 |
| POST | `/api/monthly/generate` | 生成/重生月度计划（级联 + agent） |
| GET | `/api/drift` | 漂移信号 + 是否触发重规划 |
| GET | `/api/status` | 快速状态 |
| GET | `/api/stats/week` | 7 天统计 |
| GET | `/api/stats/compliance` | 合规性报告 |
| GET | `/api/syllabus` | 考纲章节/知识点（可选 `?subject=数学一`） |
| GET | `/api/questions` | 题库列表 |
| POST | `/api/questions` | 添加题目 |
| POST | `/api/test/start` | 开始自测 |
| POST | `/api/test/submit` | 提交测试结果 |
| GET | `/api/test/results` | 测试历史 |
| GET | `/api/test/weak-topics` | 薄弱主题 |
| POST | `/api/wrong-book/upload` | 上传图片 + AI 分析 |
| POST | `/api/wrong-book` | 手动添加错题 |
| GET | `/api/wrong-book` | 错题列表（支持筛选分页） |
| GET | `/api/wrong-book/{id}` | 错题详情 + 复习历史 |
| PUT | `/api/wrong-book/{id}` | 编辑错题 |
| DELETE | `/api/wrong-book/{id}` | 删除错题 |
| GET | `/api/wrong-book/stats` | 掌握度统计 |
| GET | `/api/wrong-book/review/today` | 今日待复习 |
| GET | `/api/wrong-book/review/pick` | 知识点驱动的复查集（确定性排序） |
| POST | `/api/wrong-book/review/agent-pick` | AI 精选复查集（含确定性兜底） |
| POST | `/api/wrong-book/{id}/review` | 提交复习结果 |
| POST | `/api/wrong-book/{id}/regenerate` | 重新跑 AI 分析 |
| GET | `/api/wrong-book/knowledge-points` | 知识点掌握度（由弱到强） |
| GET | `/api/wrong-book/knowledge-points/merges` | AI 建议的别名→标准名合并 |
| POST | `/api/wrong-book/knowledge-points/canon` | 应用合并并重写标签 |
| POST | `/api/report/generate` | 生成周报 |
| GET | `/api/reports` | 报告列表 |
| GET | `/api/reports/{filename}` | 报告内容 |
| GET | `/api/ai/status` | AI 服务状态 |
| POST | `/api/timer/start` | 开始计时会话 |
| POST | `/api/timer/stop/{id}` | 停止计时并记入今日计划 |

WebSocket 端点 `ws://localhost:8900/ws/timer` 用于番茄钟实时同步。
