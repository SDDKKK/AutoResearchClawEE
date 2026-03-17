# Task: [任务名称]

> **提示**: 这是标准 PRD 模板，基于 Plan Agent 的最佳实践。填写时确保每个章节都具体、可验证。

## Overview

[用 2-3 句话简要描述这个功能是什么，解决什么问题]

**示例**:
```
实现 API 端点的速率限制功能，防止滥用。使用滑动窗口算法，
限制每个 IP 地址每分钟最多 100 次请求。
```

## Requirements

[列出具体的功能需求，每条需求应该清晰、可实现]

**填写指导**:
- ✅ 具体：说明"做什么"，而不是"为什么"
- ✅ 可验证：能够明确判断是否完成
- ✅ 完整：包含所有必要的细节
- ❌ 避免模糊：不要用"优化"、"改进"等模糊词汇

**示例**:
```
- 实现速率限制中间件，使用滑动窗口算法
- 限制：每个 IP 地址每分钟最多 100 次请求
- 超过限制时返回 HTTP 429 状态码
- 在 429 响应中包含 Retry-After 头部
- 支持从 X-Forwarded-For 头部提取真实 IP
```

**你的需求**:
- [ ] [需求 1]
- [ ] [需求 2]
- [ ] [需求 3]

## Acceptance Criteria

[列出可验证的验收标准，用于判断任务是否完成]

**填写指导**:
- ✅ 可测试：能够通过测试验证
- ✅ 具体：明确的成功标准
- ✅ 完整：覆盖所有重要方面
- 使用 checkbox 格式，便于跟踪

**示例**:
```
- [ ] 速率限制中间件已实现并集成到 API 路由
- [ ] 滑动窗口算法正确跟踪请求时间
- [ ] 超过限制时返回 429 状态码
- [ ] Retry-After 头部正确计算剩余时间
- [ ] 测试覆盖正常流量和限流场景
- [ ] 正常流量无性能下降（<5ms 延迟）
- [ ] 文档更新，说明速率限制策略
```

**你的验收标准**:
- [ ] [标准 1]
- [ ] [标准 2]
- [ ] [标准 3]

## Technical Notes

[记录技术考虑、设计决策、现有模式、依赖关系等]

**填写指导**:
- 参考现有代码模式
- 说明技术选型理由
- 列出依赖的库或模块
- 标注潜在的技术风险

**示例**:
```
### 现有模式
- 参考 `src/api/middleware/auth.py` 的中间件模式
- 使用 Redis 存储请求计数（支持分布式部署）

### 技术选型
- 滑动窗口算法：使用 Redis ZSET 存储请求时间戳
- IP 提取：优先使用 X-Forwarded-For，回退到 request.remote_addr

### 依赖
- redis-py >= 4.0.0
- 需要 Redis 服务器运行

### 风险
- Redis 不可用时的降级策略（考虑内存缓存）
- 分布式环境下的时钟同步问题
```

**你的技术注意事项**:
```
[在这里填写技术细节]
```

## Test Plan (Optional -- required when task.json tdd=true)

[List behaviors and edge cases to test]

- [ ] [Behavior 1]: Input X -> Expected output Y
- [ ] [Edge case 1]: Empty input -> Expected behavior
- [ ] [Error scenario 1]: Invalid parameter -> Expected exception

## Out of Scope

[明确列出不包含在本次任务中的内容，防止范围蔓延]

**填写指导**:
- 列出相关但不在本次实现的功能
- 说明为什么不包含（可以简要说明）
- 帮助后续任务规划

**示例**:
```
- 按用户的速率限制（本次只实现按 IP）
- 动态调整速率限制配置（使用固定配置）
- 速率限制监控面板（后续单独实现）
- 不同端点的不同限制（本次统一限制）
```

**你的范围界定**:
- [ ] [不包含的内容 1]
- [ ] [不包含的内容 2]

---

## 填写检查清单

完成 PRD 后，检查以下项目：

- [ ] **Overview** 清晰简洁，非技术人员也能理解
- [ ] **Requirements** 每条都具体、可实现、可验证
- [ ] **Acceptance Criteria** 包含所有重要方面，可测试
- [ ] **Technical Notes** 包含必要的技术细节和设计决策
- [ ] **Out of Scope** 明确界定范围，防止范围蔓延
- [ ] 没有使用"优化"、"改进"等模糊词汇
- [ ] 所有需求都有对应的验收标准

---

## 常见错误

### ❌ 错误示例 1: 需求模糊

```markdown
## Requirements
- 优化性能
- 改进用户体验
- 修复 bug
```

**问题**: 无法判断"完成"的标准

### ✅ 正确示例 1

```markdown
## Requirements
- 将 BusBranch.by_type() 查询时间从 2.5s 降低到 <500ms
- 为 type 字段添加数据库索引
- 添加查询结果缓存（TTL: 5 分钟）
```

### ❌ 错误示例 2: 缺少验收标准

```markdown
## Acceptance Criteria
- [ ] 功能实现
- [ ] 测试通过
```

**问题**: 太笼统，无法验证

### ✅ 正确示例 2

```markdown
## Acceptance Criteria
- [ ] BusBranch.by_type() 查询时间 <500ms（10k 记录）
- [ ] 数据库索引创建成功，explain 显示使用索引
- [ ] 缓存命中率 >80%（生产环境监控）
- [ ] 单元测试覆盖率 >90%
- [ ] 集成测试验证缓存失效逻辑
```

### ❌ 错误示例 3: 范围不清

```markdown
## Requirements
- 实现用户认证
- 添加权限管理
- 支持 OAuth
- 实现审计日志
```

**问题**: 范围过大，应该拆分

### ✅ 正确示例 3

```markdown
## Requirements
- 实现基本的用户名/密码认证
- 支持登录、登出功能
- 生成 JWT token（有效期 24 小时）

## Out of Scope
- 权限管理（后续任务）
- OAuth 集成（后续任务）
- 审计日志（后续任务）
- 密码重置功能（后续任务）
```

---

## 参考资源

- **Plan Agent 文档**: `.claude/agents/plan.md`
- **Multi-Agent Pipeline 指南**: `.trellis/docs/multi-agent-pipeline.md`
- **Workflow 文档**: `.trellis/workflow.md`

---

**记住**: 好的 PRD 是成功实施的基础。花 10 分钟写清楚 PRD，可以节省 1 小时的返工时间。
