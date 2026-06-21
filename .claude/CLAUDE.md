# Project Rules

## Python Execution

All Python code must run in the `pytorch-gpu` conda environment. Use `conda run -n pytorch-gpu` to execute any Python commands, scripts, or pip installs.

## Workflow Framework

### Task Classification

收到任务后首先判断：
- **独立任务**：单文件修改、简单配置、一次性脚本等
- **项目任务**：涉及多文件、需要集成测试、影响核心功能的改动

### 项目任务执行流程

```
1. 分析需求 → 定义范围和边界
2. 编写工作流框架 → 明确步骤、输入、输出
3. 试运行 → 在隔离环境或测试文件中验证
4. 确认通过 → 替换目标代码
5. 清理 → 删除测试代码
```

### 核心原则

- **先验证后修改**：任何影响现有功能的改动必须先通过测试验证
- **隔离试运行**：新功能先在独立测试环境运行，确认无误后再集成
- **测试代码不留痕**：验证通过的测试代码在合并前删除，避免污染代码库
- **可回滚**：每次重大改动前确保有回滚路径
