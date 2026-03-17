# Nocturne Memory MCP Integration Architecture

> **方案 C：分层职责 (Layered Responsibility)**
> 
> 将长期记忆 (Nocturne) 与项目本地记忆 (Trellis memory/*.md) 分层，
> 实现跨项目知识共享与项目本地上下文的有机结合。

---

## 1. 架构愿景

### 1.1 核心思想

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KNOWLEDGE PYRAMID                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Layer 3: LONG-TERM (Nocturne)                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Cross-project patterns (coding standards, architectural wisdom)  │   │
│  │  • Domain knowledge (power systems, scientific computing)           │   │
│  │  • Tool mastery (Claude Code, MCP, git workflows)                   │   │
│  │  • User preferences and relationship context                        │   │
│  │                                                                     │   │
│  │  URI: trellis://patterns/..., trellis://domain/..., core://...      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                              │
│                              │ Sync (explicit write)                         │
│  Layer 2: PROJECT-LOCAL (Trellis)                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • decisions.md     → Architecture decisions for THIS codebase      │   │
│  │  • known-issues.md  → Active bugs and workarounds                   │   │
│  │  • learnings.md     → Session insights, project-specific patterns   │   │
│  │  • scratchpad.md    → Ephemeral WIP state                           │   │
│  │                                                                     │   │
│  │  Format: Markdown files (human-readable, git-tracked)               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲                                              │
│                              │ Auto-injected                                │
│  Layer 1: SESSION (Context Window)                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Active code being edited                                         │   │
│  │  • Current task context (PRD, specs)                                │   │
│  │  • Agent prompts and responses                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| **Write-Up, Read-Down** | 下层可以读取上层，但写入只能向上（session → local → long-term） |
| **Explicit Promotion** | 只有显式确认的内容才能从 local 提升到 long-term |
| **Lazy Loading** | Nocturne 内容按需读取，不自动注入所有上下文 |
| **Human Review** | 长期记忆的写入需要人类审查（通过 Dashboard） |
| **Backward Compatible** | 现有 Trellis 工作流不受影响，集成是渐进式的 |

---

## 2. 分层职责定义

### 2.1 Nocturne Memory (Long-Term)

**存储内容：**

```
trellis://                    # Trellis 框架专用命名空间
├── patterns/
│   ├── python/               # Python 代码模式（跨项目）
│   │   ├── error-handling    # 错误处理模式
│   │   ├── data-pipeline     # 数据处理模式
│   │   └── testing           # 测试策略
│   ├── matlab/               # MATLAB 代码模式
│   ├── architecture/         # 架构决策模式
│   └── workflow/             # 工作流优化模式
├── domain/
│   ├── power-systems/        # 电力系统领域知识
│   └── reliability/          # 可靠性计算知识
├── tools/
│   ├── claude-code/          # Claude Code 使用技巧
│   ├── mcp/                  # MCP 工具使用经验
│   └── git/                  # Git 工作流经验
└── projects/
    └── researchclaw/        # 本项目在 Nocturne 中的镜像
        ├── decisions/        # 已确认的长期决策
        └── learnings/        # 已提炼的学习成果

core://                       # Nocturne 核心命名空间
├── agent/                    # AI Agent 身份和配置
└── my_user/                  # 用户关系和偏好
```

**访问模式：**
- `read_memory("trellis://patterns/python/error-handling")` - 读取特定模式
- `search_memory("polars", domain="trellis")` - 在 trellis 域搜索
- `system://boot` - 启动时加载核心记忆

### 2.2 Trellis Memory (Project-Local)

**存储内容：**

| 文件 | 用途 | 生命周期 | 注入对象 |
|------|------|----------|----------|
| `decisions.md` | 架构决策记录 | 永久 | implement, check, debug |
| `known-issues.md` | 已知问题 | 解决后删除 | implement, debug |
| `learnings.md` | 学习日志 | 定期提炼到 Nocturne | implement, check |
| `scratchpad.md` | 临时 WIP | 任务结束后清空 | implement, debug |

**与 Nocturne 的关系：**
- `learnings.md` 中的条目可以**提升**到 `trellis://patterns/`
- `decisions.md` 中的重要决策可以**镜像**到 `trellis://projects/{name}/decisions/`
- `known-issues.md` 中的模式可以**提炼**到 `trellis://patterns/bug-prevention/`

---

## 3. 集成点设计

### 3.1 集成架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRELLIS FRAMEWORK                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  Session Start  │    │  Agent Execution │    │  Session End    │         │
│  │     Hook        │    │                  │    │     Hook        │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│           │                      │                      │                  │
│           ▼                      ▼                      ▼                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ Read Nocturne   │    │ MCP Tools       │    │ Write Nocturne  │         │
│  │ (SQLite direct) │    │ (Agent calls)   │    │ (Agent calls)   │         │
│  │                 │    │                 │    │                 │         │
│  │ • patterns      │    │ • read_memory   │    │ • create_memory │         │
│  │ • domain        │    │ • search_memory │    │ • update_memory │         │
│  │ • user context  │    │                 │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│           │                      │                      │                  │
│           │                      │                      │                  │
│           ▼                      ▼                      ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      NOCTURNE MEMORY MCP                             │   │
│  │                         (SQLite Backend)                             │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │   │
│  │  │   paths     │  │  memories   │  │         snapshots           │  │   │
│  │  │  (URI → ID) │  │  (content)  │  │  (version control/rollback) │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Hook 层集成 (Read-Only)

**session-start.py 增强：**

```python
# 新增：从 Nocturne 读取项目相关的长期记忆
def get_nocturne_context(repo_root: Path) -> str:
    """
    读取 Nocturne 中与当前项目相关的长期记忆。
    直接读取 SQLite，不通过 MCP（Hook 无法调用 MCP）。
    """
    # 1. 确定项目标识（从 git remote 或目录名）
    project_id = get_project_id(repo_root)
    
    # 2. 读取 trellis://patterns/ 中相关的模式
    patterns = query_sqlite(
        "SELECT path, content FROM paths JOIN memories ... "
        "WHERE domain='trellis' AND path LIKE 'patterns/%' "
        "ORDER BY priority"
    )
    
    # 3. 读取 trellis://projects/{project_id}/ 中的项目记忆
    project_memories = query_sqlite(
        "SELECT path, content FROM paths JOIN memories ... "
        "WHERE domain='trellis' AND path LIKE ?",
        f"projects/{project_id}/%"
    )
    
    return format_nocturne_context(patterns, project_memories)
```

**inject-subagent-context.py 增强：**

```python
# 在 get_implement_context 中增加 Nocturne 查询建议
def get_implement_context(repo_root: str, task_dir: str) -> str:
    # ... 现有代码 ...
    
    # 新增：添加 Nocturne 查询提示
    nocturne_hint = """
## Nocturne Memory Access

You have access to long-term memory via MCP tools:
- `read_memory("trellis://patterns/python/error-handling")` - Read specific patterns
- `search_memory("<query>", domain="trellis")` - Search trellis domain

Consider querying Nocturne when:
1. Implementing a pattern you've seen before
2. Working with domain-specific concepts (power systems)
3. Need tool usage guidance (Claude Code, MCP, git)
"""
    context_parts.append(nocturne_hint)
    
    return "\n\n".join(context_parts)
```

### 3.3 Agent 层集成 (Read/Write)

**Agent Prompt 模板增强：**

```markdown
## Long-Term Memory (Nocturne)

You have access to the Nocturne Memory MCP with the following tools:

### Read Operations
- `read_memory(uri)` - Read a specific memory by URI
- `search_memory(query, domain?, limit?)` - Search memories

### Write Operations (use sparingly)
- `create_memory(parent_uri, content, priority, title?, disclosure?)` - Create new memory
- `update_memory(uri, ...)` - Update existing memory

### When to Use Nocturne

**READ when:**
- Starting a new task type (check for existing patterns)
- Encountering an unfamiliar domain concept
- Need tool usage guidance
- Want to recall previous similar implementations

**WRITE when:**
- Discovered a reusable pattern worth preserving
- Learned a valuable lesson from a mistake
- Established a new convention or workflow

### trellis:// URI Namespace

```
trellis://patterns/{language}/          # Code patterns
trellis://domain/{area}/                # Domain knowledge
trellis://tools/{tool}/                 # Tool mastery
trellis://projects/{name}/              # Project-specific
```

**Note:** All writes to Nocturne are versioned and can be reviewed in the Dashboard.
```

---

## 4. URI 命名空间设计

### 4.1 trellis:// 域结构

```
trellis://
├── patterns/
│   ├── python/
│   │   ├── idioms/               # Python 惯用法
│   │   ├── error-handling/       # 错误处理模式
│   │   ├── data-processing/      # 数据处理模式 (polars, pandas)
│   │   ├── testing/              # 测试模式
│   │   └── performance/          # 性能优化模式
│   ├── matlab/
│   │   ├── vectorization/        # 向量化模式
│   │   └── translation/          # MATLAB→Python 迁移模式
│   ├── architecture/
│   │   ├── layering/             # 分层架构模式
│   │   ├── interfaces/           # 接口设计模式
│   │   └── state-management/     # 状态管理模式
│   └── workflow/
│       ├── trellis/              # Trellis 框架使用技巧
│       ├── git/                  # Git 工作流
│       └── mcp/                  # MCP 工具使用
├── domain/
│   ├── power-systems/
│   │   ├── reliability/          # 可靠性计算
│   │   ├── topology/             # 电网拓扑分析
│   │   └── load-flow/            # 潮流计算
│   └── standards/
│       ├── ieee-519/             # IEEE 标准
│       └── gb/                   # 国标
├── tools/
│   ├── claude-code/
│   │   ├── slash-commands/       # 斜杠命令使用
│   │   ├── hooks/                # Hook 开发
│   │   └── agents/               # Agent 开发
│   ├── mcp/
│   │   ├── tool-design/          # 工具设计原则
│   │   └── error-handling/       # 错误处理
│   └── testing/
│       ├── pytest/
│       └── matlab-unit/
└── projects/
    └── {project-name}/
        ├── decisions/            # 已确认的长期决策
        ├── learnings/            # 已提炼的学习
        └── patterns/             # 项目特定模式
```

### 4.2 URI 示例

| 用途 | URI |
|------|-----|
| Python 错误处理模式 | `trellis://patterns/python/error-handling/result-type` |
| Polars 数据转换 | `trellis://patterns/python/data-processing/polars-transform` |
| 可靠性指标计算 | `trellis://domain/power-systems/reliability/metrics` |
| Claude Code Hook 开发 | `trellis://tools/claude-code/hooks/context-injection` |
| 本项目决策 | `trellis://projects/researchclaw/decisions/optimization-solver` |

---

## 5. 数据流

### 5.1 启动时数据流

```
Session Start
    │
    ├── 1. 读取 Trellis memory/*.md (现有)
    │      - decisions.md
    │      - known-issues.md
    │      - scratchpad.md
    │
    ├── 2. 读取 Nocturne SQLite (新增)
    │      - trellis://patterns/ 中的相关模式
    │      - trellis://projects/{current}/ 中的项目记忆
    │      - core://agent/ 中的 Agent 配置
    │
    └── 3. 组装上下文
           - Trellis memory 直接注入
           - Nocturne 内容作为引用/提示
```

### 5.2 任务执行时数据流

```
Agent Execution
    │
    ├── 1. Agent 接收上下文 (含 Nocturne 查询提示)
    │
    ├── 2. Agent 按需查询 Nocturne (via MCP)
    │      - read_memory("trellis://patterns/...")
    │      - search_memory("...", domain="trellis")
    │
    ├── 3. Agent 执行任务
    │
    └── 4. Agent 选择性写入 Nocturne (via MCP)
           - 发现的新模式 → create_memory
           - 更新的知识 → update_memory
```

### 5.3 会话结束时数据流

```
Session End
    │
    ├── 1. 总结本次会话的学习
    │      - 添加到 learnings.md (本地)
    │
    ├── 2. 识别可提升的知识
    │      - 哪些 learning 值得长期保存？
    │      - 哪些 pattern 可以跨项目复用？
    │
    └── 3. 提示用户写入 Nocturne
           - "是否将以下学习保存到长期记忆？"
           - 用户确认后，Agent 调用 create_memory
```

---

## 6. 同步机制

### 6.1 提升流程 (Trellis → Nocturne)

```
learnings.md 中的条目
         │
         ▼
   是否跨项目适用？
         │
    YES ─┴─► 写入 trellis://patterns/ 或 trellis://domain/
              priority=2 (一般)
              disclosure="当处理类似问题时"
              
decisions.md 中的重要决策
         │
         ▼
   是否长期有效？
         │
    YES ─┴─► 写入 trellis://projects/{name}/decisions/
              priority=1 (重要)
              disclosure="当相关架构决策时"
```

### 6.2 镜像流程 (Nocturne → Trellis)

```
Nocturne 中的项目记忆
         │
         ▼
   启动时读取
         │
         ▼
   注入到 session 上下文
   (不写入本地文件，保持单一来源)
```

### 6.3 冲突解决

| 场景 | 策略 |
|------|------|
| Nocturne 和 Trellis 内容冲突 | 以 Nocturne 为准（长期记忆优先） |
| 同一 URI 多次更新 | Nocturne 版本控制自动处理 |
| 需要删除长期记忆 | 通过 Dashboard 人工审查后删除 |
| 项目记忆 vs 全局模式 | 项目记忆优先（更具体） |

---

## 7. 实现约束

### 7.1 Hook 层约束

- **Python 脚本**：Hook 是同步 Python 脚本
- **无法调用 MCP**：MCP 工具需要异步环境，Hook 无法直接使用
- **直接读 SQLite**：Hook 可以直接读取 Nocturne 的 SQLite 数据库
- **只读访问**：Hook 层只读取，不写入 Nocturne

### 7.2 Agent 层约束

- **可以调用 MCP**：Agent 通过 Task 工具运行，可以使用 MCP
- **读写权限**：Agent 可以读取和写入 Nocturne
- **异步操作**：所有 MCP 调用都是异步的
- **需要显式调用**：Agent 必须主动调用 MCP 工具

### 7.3 向后兼容

- **可选集成**：现有 Trellis 工作流不依赖 Nocturne
- **优雅降级**：如果 Nocturne 不可用，系统正常工作
- **渐进采用**：用户可以逐步将知识迁移到 Nocturne

---

## 8. 安全与审查

### 8.1 写入审查

所有写入 Nocturne 的操作：
1. **版本控制**：自动创建快照
2. **Dashboard 审查**：人类可以通过 Web UI 审查变更
3. **回滚能力**：可以一键回滚到之前版本

### 8.2 敏感信息

- **不存储密钥**：Nocturne 不存储 API 密钥、密码等
- **代码片段**：可以存储代码模式，但不存储完整文件
- **项目结构**：可以存储项目架构，但不存储业务数据

---

## 9. 成功指标

| 指标 | 目标 |
|------|------|
| 启动时间增加 | < 100ms（SQLite 查询） |
| Agent 查询 Nocturne 频率 | 每个复杂任务至少 1 次 |
| 知识复用率 | 跨项目复用 > 30% 的模式 |
| 用户采纳率 | 80% 的会话使用 Nocturne 建议 |
| 写入审查率 | 100% 的写入可审查 |

---

## 10. 附录

### 10.1 相关文件

| 文件 | 用途 |
|------|------|
| `prd.md` | 详细实施计划 |
| `session-start.py` | 启动 Hook（读取 Nocturne） |
| `inject-subagent-context.py` | Agent 上下文注入 |
| `nocturne_client.py` | SQLite 读取封装 |

### 10.2 外部依赖

- Nocturne Memory MCP Server
- SQLite 数据库（Nocturne 后端）
- Python aiosqlite（Hook 层读取）
