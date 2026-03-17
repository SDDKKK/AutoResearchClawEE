# Multi-Agent Pipeline 快速入门

> **什么是 Multi-Agent Pipeline?** 一个自动化的任务规划和执行系统，适合需求明确的标准化任务。

## 概述

Multi-Agent Pipeline (Mode 2) 是 Trellis 的自动化工作流程，包含两个阶段：

1. **Plan 阶段**: Plan Agent 评估需求，生成完整的任务配置
2. **Execute 阶段**: Dispatch Agent 自动编排 Implement → Check → Debug

**与 Mode 1 (Direct Development) 的区别**:

| 特性 | Mode 1 (Direct) | Mode 2 (Pipeline) |
|------|----------------|-------------------|
| **入口** | `task.py create` | `plan.py` |
| **PRD** | 手动编写 | 自动生成 |
| **执行** | 交互式 | 自动化 |
| **适用** | 探索性任务 | 标准化任务 |

## 何时使用 Multi-Agent Pipeline?

### ✅ 适合的场景

1. **需求非常明确**
   - 有清晰的输入输出定义
   - 有具体的验收标准
   - 不需要讨论和探索

2. **标准化任务**
   - 添加 API 端点（有固定模式）
   - 添加优化模块（有固定模式）
   - 实现标准功能（认证、日志等）

3. **批量任务**
   - 多个类似任务
   - 需要保持一致性
   - 可以并行执行

### ❌ 不适合的场景

1. **需求不明确**
   - "优化性能"（太模糊）
   - "修复 bug"（需要先调查）
   - "改进代码"（需要分析）

2. **探索性任务**
   - 调研新技术
   - 分析现有问题
   - 设计新架构

3. **需要频繁交互**
   - 需要讨论方案
   - 需要用户决策
   - 需要实时反馈

## 快速开始

### Step 1: 准备明确的需求

**好的需求示例**:
```
Add rate limiting to API endpoints using sliding window algorithm.
Limit: 100 requests per minute per IP address.
Return HTTP 429 status when limit exceeded.
Include Retry-After header in response.
```

**不好的需求示例**:
```
Make the API faster
Fix bugs
Improve user experience
```

### Step 2: 运行 Plan Agent

```bash
python3 ./.trellis/scripts/multi_agent/plan.py \
  --name <task-name> \
  --type python \
  --requirement "<clear requirement>"
```

**示例**:
```bash
python3 ./.trellis/scripts/multi_agent/plan.py \
  --name add-rate-limiting \
  --type python \
  --requirement "Add rate limiting to API endpoints using sliding window.
                 Limit: 100 req/min per IP. Return 429 when exceeded."
```

### Step 3: 监控 Plan Agent

Plan Agent 在后台运行，监控进度：

```bash
# 查看日志
tail -f .trellis/tasks/<task-dir>/.plan-log

# 检查进程
ps aux | grep plan

# 查看输出
ls -la .trellis/tasks/<task-dir>/
```

### Step 4: 检查输出

Plan Agent 完成后，任务目录包含：

```
.trellis/tasks/<task-dir>/
├── task.json          # 任务元数据
├── prd.md             # 自动生成的 PRD
├── implement.jsonl    # Implement Agent 上下文
├── check.jsonl        # Check Agent 上下文
├── debug.jsonl        # Debug Agent 上下文
└── .plan-log          # Plan Agent 执行日志
```

**检查 PRD 质量**:
- 需求是否清晰？
- 验收标准是否完整？
- 技术注意事项是否准确？

### Step 5: 执行 Pipeline（可选）

如果 PRD 满意，可以启动自动化执行：

```bash
python3 ./.trellis/scripts/multi_agent/start.py <task-dir>
```

**或者手动执行**（推荐）:
```bash
# 激活任务
task.py start <task-dir>

# 手动调用 agents
Task(subagent_type="implement", ...)
Task(subagent_type="check", ...)
```

## Plan Agent 的核心功能

### 1. 需求质量把关

Plan Agent 会评估需求，**有权拒绝**不合理的需求。

**拒绝场景**:
- 需求模糊或不完整
- 范围过大（应该拆分）
- 技术上不可行
- 超出项目范围

**拒绝示例**:
```bash
# 输入
plan.py --requirement "Make the API faster"

# 输出
=== PLAN REJECTED ===

Reason: Unclear or Vague

Details:
"Make the API faster" does not specify:
- Which endpoints need optimization
- Current performance baseline
- Target performance metrics
- Acceptable trade-offs

Suggestions:
Provide a clear requirement like:
"Optimize BusBranch.by_type() query. Current: 2.5s.
Target: <500ms. Use indexing or caching."
```

### 2. 自动化代码库分析

Plan Agent 自动调用 Research Agent：
- 搜索相关的 spec 文件
- 查找现有的代码模式
- 识别需要参考的模块

**输出示例**:
```
Found relevant files:
- src/api/middleware/rate_limiter.py (existing pattern)
- .trellis/spec/python/api-design.md (API guidelines)
- tests/api/test_middleware.py (test patterns)
```

### 3. 生成标准化 PRD

Plan Agent 生成的 PRD 包含：
- Overview（简要描述）
- Requirements（具体需求）
- Acceptance Criteria（验收标准）
- Technical Notes（技术考虑）
- Out of Scope（范围界定）

### 4. 配置上下文文件

自动配置 jsonl 文件，包含：
- 相关的 spec 文档
- 现有的代码模式
- 测试示例

## 完整示例

### 示例 1: 添加 API 端点

```bash
# 1. 运行 Plan Agent
python3 ./.trellis/scripts/multi_agent/plan.py \
  --name add-user-export \
  --type python \
  --requirement "Add GET /api/users/export endpoint.
                 Returns CSV with id, name, email.
                 Requires admin role.
                 Limit: 10k users per export."

# 2. 监控进度
tail -f .trellis/tasks/02-16-add-user-export/.plan-log

# 3. 检查输出
cat .trellis/tasks/02-16-add-user-export/prd.md

# 4. 如果满意，手动执行
python3 ./.trellis/scripts/task.py start .trellis/tasks/02-16-add-user-export
# 然后手动调用 agents 或使用 start.py
```

### 示例 2: 添加拓扑优化模块

```bash
python3 ./.trellis/scripts/multi_agent/plan.py \
  --name add-topo-optimizer \
  --type python \
  --requirement "Add topology reconfiguration optimization module.
                 Input: network topology and load data.
                 Output: optimal switch states.
                 Must use cvxpy for optimization."
```

## 常见问题

### Q1: Plan Agent 拒绝了我的需求，怎么办？

**A**: 阅读 `REJECTED.md` 文件，按照建议修改需求。

```bash
# 查看拒绝原因
cat .trellis/tasks/<task-dir>/REJECTED.md

# 删除任务目录
rm -rf .trellis/tasks/<task-dir>

# 用修改后的需求重试
plan.py --name <task> --type <type> --requirement "<revised requirement>"
```

### Q2: 生成的 PRD 不满意，可以修改吗？

**A**: 可以！Plan Agent 只是生成初始版本。

```bash
# 手动编辑 PRD
vim .trellis/tasks/<task-dir>/prd.md

# 手动调整 jsonl
python3 ./.trellis/scripts/task.py add-context <task-dir> implement <path> "<reason>"

# 然后正常执行
python3 ./.trellis/scripts/task.py start <task-dir>
```

### Q3: 什么时候用 Mode 1，什么时候用 Mode 2？

**A**: 根据需求明确度选择。

| 需求状态 | 推荐模式 | 原因 |
|---------|---------|------|
| 非常明确 | Mode 2 | 自动化节省时间 |
| 基本明确 | Mode 1 | 灵活性更好 |
| 不太明确 | Mode 1 | 需要探索和讨论 |
| 完全不明确 | Mode 1 | 必须先调研 |

### Q4: Plan Agent 运行失败了怎么办？

**A**: 检查日志文件。

```bash
# 查看完整日志
cat .trellis/tasks/<task-dir>/.plan-log

# 常见问题
# 1. Research Agent 超时 → 重试
# 2. 路径不存在 → 检查 jsonl 文件
# 3. 权限问题 → 检查文件权限
```

### Q5: 可以跳过 Plan Agent 直接用 Dispatch Agent 吗？

**A**: 不推荐。Dispatch Agent 依赖 Plan Agent 生成的配置。

如果想自动化执行但不用 Plan Agent：
1. 手动创建任务（`task.py create`）
2. 手动写 PRD
3. 手动配置 jsonl
4. 然后调用 `start.py`

但这样就失去了 Plan Agent 的质量把关优势。

## 最佳实践

### 1. 写清楚需求

**投入 5 分钟写清楚需求，可以节省 1 小时的返工时间。**

好的需求包含：
- 具体的输入输出
- 明确的行为定义
- 可验证的标准
- 技术约束

### 2. 先小范围试用

不要一开始就用 Pipeline 处理复杂任务：
1. 从简单的标准化任务开始
2. 评估生成的 PRD 质量
3. 逐步扩大使用范围

### 3. 保持灵活性

Plan Agent 生成的配置不是最终版本：
- 可以修改 PRD
- 可以调整 jsonl
- 可以手动执行而不用 Pipeline

### 4. 结合 Mode 1 使用

不是非此即彼：
- 用 Plan Agent 生成初始配置
- 用 Mode 1 的灵活性调整和执行
- 两种模式的优势结合

## 与 Mode 1 的对比

### Mode 1 (Direct Development)

**优势**:
- ✅ 灵活，可以边做边调整
- ✅ 交互式，随时讨论
- ✅ 学习曲线平缓
- ✅ 适合各种任务

**劣势**:
- ⚠️ PRD 质量依赖经验
- ⚠️ 上下文配置可能遗漏
- ⚠️ 格式不一致

**适用**: 探索性任务、需要讨论的任务

### Mode 2 (Multi-Agent Pipeline)

**优势**:
- ✅ 需求质量把关
- ✅ 自动化代码库分析
- ✅ 标准化输出
- ✅ 节省配置时间

**劣势**:
- ⚠️ 需求必须预先明确
- ⚠️ 缺少交互
- ⚠️ 学习曲线陡峭

**适用**: 标准化任务、需求明确的任务

## 下一步

1. **尝试第一个任务**
   - 选择一个需求明确的小任务
   - 用 plan.py 生成配置
   - 评估 PRD 质量

2. **学习 PRD 结构**
   - 即使不用 Plan Agent
   - 也可以学习它的 PRD 结构
   - 提高手动写 PRD 的质量

3. **提供反馈**
   - Plan Agent 生成的 PRD 质量如何？
   - 哪些地方需要改进？
   - 是否节省了时间？

## 参考资源

- **Plan Agent 定义**: `.claude/agents/plan.md`
- **PRD 模板**: `.trellis/templates/prd-template.md`
- **Workflow 文档**: `.trellis/workflow.md`
- **Task 管理**: `.trellis/scripts/task.py --help`

---

**记住**: Multi-Agent Pipeline 不是替代 Mode 1，而是补充。根据任务特点选择合适的模式。
