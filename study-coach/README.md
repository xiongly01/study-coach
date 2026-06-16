# study-coach

考研备考监督工具。提供学习计划管理、番茄钟计时、自测练习、错题本（AI 图片分析）、进度报告等功能，通过 CLI 和 Web 界面使用。

## 功能概览

| 模块 | 说明 |
|------|------|
| **学习计划** | 按科目权重自动生成每日任务，顺延未完成任务，里程碑管理 |
| **番茄钟** | 25 分钟一轮，记录学习时长，Web 端实时同步 |
| **自测系统** | 题库管理，随机抽题测试，薄弱知识点分析 |
| **错题本** | 上传题目图片 → AI 识别分析 → 提取知识点 → 间隔复习调度（1/3/7/14/30天） |
| **进度报告** | 周报生成，合规性检查，自动调整计划权重 |
| **院校选择** | 内置 13 所院校数据库，筛选/对比/推荐（临时模块） |

## 技术栈

- **后端**: Python 3.10+, FastAPI, Uvicorn
- **前端**: Vanilla HTML/CSS/JS（无框架）
- **CLI**: Typer + Rich
- **数据存储**: 本地 JSON 文件（无数据库）
- **AI**: Claude API（Anthropic）— 用于错题图片分析

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

浏览器访问 `http://localhost:8900`，首次使用会进入初始设置页面。

### 2. CLI 使用

```bash
# 初始化（设置考试日期、目标院校、每日时长）
study-coach init

# 查看今日计划
study-coach plan

# 开始番茄钟
study-coach start <task_id>

# 完成任务
study-coach done <task_id>

# 每日签到
study-coach checkin

# 生成周报
study-coach report
```
## 项目结构

```
study-coach/
├── data/                        # 运行时数据（JSON 文件）
│   ├── config.json              # 用户配置
│   ├── longterm_plan.json       # 里程碑
│   ├── daily/                   # 每日计划 YYYY-MM-DD.json
│   ├── tests/                   # 题库 + 测试结果
│   ├── reports/                 # 周报 Markdown
│   └── wrong_book/              # 错题本数据 + 图片
├── src/study_coach/
│   ├── models.py                # 数据模型（dataclass）
│   ├── store.py                 # JSON 文件存储层
│   ├── planner.py               # 里程碑 + 每日任务规划
│   ├── tracker.py               # 番茄钟（CLI 版）
│   ├── reporter.py              # 日报 + 周报生成
│   ├── examiner.py              # 题库 + 自测
│   ├── supervisor.py            # 合规性检查 + 计划自动调整
│   ├── school_advisor.py        # 院校选择（临时）
│   ├── ai.py                    # Claude API 封装（图片分析）
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
│               ├── plan.js      # 计划（里程碑 + 历史记录）
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
  "daily_study_hours": 8,
  "target_school": "待定",
  "target_major": "待定"
}
```

### AI 服务（错题图片分析）

设置环境变量：

```bash
# Linux / macOS
export ANTHROPIC_API_KEY="your-api-key"

# Windows PowerShell
$env:ANTHROPIC_API_KEY="your-api-key"

# Windows CMD
set ANTHROPIC_API_KEY=your-api-key
```

设置后重启服务，错题本的"AI 分析并添加"功能即可使用。未配置 API Key 时，仍可手动添加错题。

## Web 界面说明

访问 `http://localhost:8900`，底部 Tab 栏切换：

| Tab | 功能 |
|-----|------|
| **今日** | 番茄钟计时、今日任务列表（可勾选完成/手动添加/自动生成）、每日反思 |
| **计划** | 里程碑管理（标记完成）、最近 7 天历史记录 |
| **自测** | 题库浏览/添加、按科目随机自测、测试记录查看 |
| **错题本** | 拍照/上传题目图片 → AI 自动识别 → 知识点标签 → 间隔复习 → 掌握度统计 |
| **总览** | 本周学习时长柱状图、周报生成/查看、7 天合规性指标 |

### 移动端访问

手机浏览器访问 `http://<电脑IP>:8900`，界面自动适配移动端。微信内打开同样可用，支持直接拍照上传题目图片。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 保存配置 |
| GET | `/api/today` | 今日计划 |
| POST | `/api/plan/generate` | 自动生成今日计划 |
| POST | `/api/tasks` | 添加任务 |
| POST | `/api/tasks/{id}/done` | 完成任务 |
| POST | `/api/tasks/{id}/undone` | 取消完成 |
| POST | `/api/checkin` | 保存反思 |
| GET | `/api/milestones` | 里程碑列表 |
| POST | `/api/milestones/{id}/toggle` | 切换里程碑状态 |
| GET | `/api/status` | 快速状态 |
| GET | `/api/stats/week` | 7 天统计 |
| GET | `/api/stats/compliance` | 合规性报告 |
| GET | `/api/questions` | 题库列表 |
| POST | `/api/questions` | 添加题目 |
| POST | `/api/test/start` | 开始自测 |
| POST | `/api/test/submit` | 提交测试结果 |
| GET | `/api/test/results` | 测试历史 |
| POST | `/api/wrong-book/upload` | 上传图片 + AI 分析 |
| POST | `/api/wrong-book` | 手动添加错题 |
| GET | `/api/wrong-book` | 错题列表（支持筛选分页） |
| GET | `/api/wrong-book/{id}` | 错题详情 |
| PUT | `/api/wrong-book/{id}` | 编辑错题 |
| DELETE | `/api/wrong-book/{id}` | 删除错题 |
| GET | `/api/wrong-book/review/today` | 今日待复习 |
| POST | `/api/wrong-book/{id}/review` | 提交复习结果 |
| GET | `/api/wrong-book/stats` | 掌握度统计 |
| POST | `/api/report/generate` | 生成周报 |
| GET | `/api/reports` | 报告列表 |
| GET | `/api/reports/{filename}` | 报告内容 |
| GET | `/api/ai/status` | AI 服务状态 |

WebSocket 端点 `ws://localhost:8900/ws/timer` 用于番茄钟实时同步。
