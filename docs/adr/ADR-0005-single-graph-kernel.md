# ADR-0005：ME-System 仅保留 ME-Brain 与 ME-Who 两个产品图谱

- 状态：Accepted
- 日期：2026-07-23
- 参考：Codebase-Memory MCP
- 上位决策：ADR-0004 双权威图谱

## 决策

ME-System 对外和对内的产品模型都只包含两个图谱：

```text
ME-System
├── ME-Brain
└── ME-Who
```

- **ME-Brain**：科研、设计、开发等客观项目的结构化图谱；
- **ME-Who**：Agent 为理解和服务用户所需的结构化图谱。

不再定义第三个产品、第三张业务图谱或第三个“Core”品牌。

现有 `services/me-graph-core/` 与 Python 包 `me_graph_core` 是早期实现路径，不代表第三个产品，但名称容易造成误解。后续迁移为无产品身份的共享实现：

```text
me-system/
├── me-brain/
├── me-who/
├── shared/
└── integrations/
```

建议 Python 包收敛为：

```text
me_system.brain
me_system.who
me_system.shared
me_system.integrations
```

共享代码只解决技术复用，不拥有独立产品定位。

## Codebase-Memory 参考原则

Codebase-Memory 的核心做法是：先把代码库构造成持久化结构图谱，再由 Agent 通过 MCP 进行结构查询；后端不负责聊天回答，Agent 承担自然语言理解和工具选择。

ME-Brain 与 ME-Who 都采用这一模式：

```text
原始来源
→ 确定性标准化 / 可审计抽取
→ 结构化节点与关系候选
→ 持久化图谱
→ 类型化查询
→ MCP / CLI
→ Agent 解释和执行
```

### 共同吸收

1. **Graph first**：Agent 默认读取结构图谱，不反复扫描全部原始资料；
2. **Persistent graph**：图谱跨会话和重启保存；
3. **Multi-pass indexing**：不同 Pass 分别负责发现、标准化、实体、关系、冲突和质量；
4. **Typed MCP tools**：工具表达领域查询，不提供泛化聊天接口；
5. **Compact first**：默认返回紧凑结构，需要时再下钻证据和原文；
6. **CLI/MCP parity**：CLI 与 MCP 复用同一应用服务；
7. **Status and coverage**：明确索引完成度、跳过内容和质量问题；
8. **No embedded answer LLM**：模型可以参与候选抽取，但不成为权威事实源。

## ME-Brain 的 Codebase-Memory 映射

Codebase-Memory 以 `Project / File / Class / Function / CALLS / IMPORTS` 等结构表达代码库。

ME-Brain 用相同方法表达项目世界：

### 节点

```text
Project
Workstream
Requirement
Decision
Task
Issue
Constraint
Artifact
Experiment
Document
Person
Evidence
```

### 关系

```text
HAS_REQUIREMENT
HAS_DECISION
HAS_TASK
HAS_ISSUE
HAS_ARTIFACT
SUPERSEDES
SATISFIES
DEPENDS_ON
BLOCKS
IMPLEMENTS
PRODUCES
SUPPORTED_BY
```

### 主要作用

- 快速恢复项目当前状态；
- 区分当前决策和历史决策；
- 查询任务、问题和阻塞关系；
- 分析成果、需求和决策之间的影响；
- 在有限 Token 下返回任务相关子图；
- 必要时回到原始证据。

## ME-Who 的 Codebase-Memory 映射

ME-Who 同样不是“用户摘要文件”，而是结构化图谱：

### 节点

```text
User
Role
Capability
Preference
CollaborationRule
Goal
ProjectRole
Experience
Evidence
```

### 关系

```text
HAS_ROLE
HAS_CAPABILITY
PREFERS
HAS_COLLABORATION_RULE
HAS_GOAL
PARTICIPATES_IN
APPLIES_TO
SUPERSEDES
CONFIRMED_BY
SUPPORTED_BY
```

### 主要作用

- 让 Agent 获取任务相关的用户背景；
- 根据项目、任务类型和 Agent 身份裁剪协作规则；
- 区分用户明确事实、行为证据和系统推断；
- 记录偏好随时间和场景变化；
- 减少重复询问和错误协作方式；
- 防止无关 Agent 读取完整个人图谱。

## 两个图谱的共同实现，但不是第三个产品

```text
me-system/
├── me-brain/
│   ├── ontology/
│   ├── passes/
│   └── queries/
├── me-who/
│   ├── ontology/
│   ├── passes/
│   └── queries/
├── shared/
│   ├── contracts/
│   ├── graph/
│   ├── evidence/
│   ├── ingestion/
│   ├── persistence/
│   ├── permissions/
│   └── query/
└── integrations/
    ├── mcp/
    ├── hermes/
    └── pi/
```

`shared/` 中的能力包括：

- GraphNode / GraphEdge / GraphSlice；
- SourceRecord / EvidenceFragment；
- CandidateGraphChange；
- PostgreSQL 持久化；
- 时间、来源、权限和审核；
- MCP 与 CLI 共同调用的应用服务。

它们不形成新的产品名称。

## MCP 边界

MCP 只暴露两个图谱域的工具：

```text
brain_*
who_*
```

例如：

```text
brain_resolve_project
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
```

后续工具仍按图谱域命名，不增加 `core_*`、`context_*` 或 `source_*` 产品级工具前缀。

MCP Adapter：

- 不定义图谱 Schema；
- 不直接执行任意 SQL；
- 不直接修改权威图谱；
- 不复制查询逻辑；
- 只调用共享应用服务并执行权限裁剪。

## 不照搬 Codebase-Memory 的部分

1. **不向普通 Agent 暴露任意 Cypher**：ME-Who 涉及敏感数据，必须使用类型化查询；
2. **不让语义抽取直接成为权威事实**：项目决策、偏好和研究结论先进入 Candidate；
3. **不改成每项目 SQLite 权威库**：继续使用一个 PostgreSQL 权威存储，两个图谱通过 namespace 隔离；
4. **不一次开放大量工具**：工具增长必须证明能降低 Token 或提升正确率；
5. **不把 Agent 配置当数据源真相**：动态状态仍来自图谱查询。

## 当前实施影响

下一切片仍建设 Source、Evidence、IngestionRun 和 Candidate 持久化，但这些仅是两个图谱共同的输入设施：

```text
External Source
→ shared/ingestion
→ CandidateGraphChange(target_graph = me_brain | me_who | bridge)
→ Review
→ ME-Brain 或 ME-Who
```

不会新增：

- ME-Core 产品；
- ME-Graph-Core 产品；
- Source Ledger 产品；
- Candidate 服务产品；
- 第三张业务图谱；
- 第二个权威数据库。

## 后续迁移

在新增更多功能前，完成命名和目录迁移：

```text
services/me-graph-core/  → shared/
me_graph_core            → me_system
me-graph                 → me-system
me-graph-mcp             → me-system-mcp
```

旧 CLI 可以保留一个小版本兼容别名，但新文档统一使用 ME-System 名称。

## 结论

```text
产品：ME-Brain + ME-Who
方法：参考 Codebase-Memory 的持久化结构图谱与类型化 MCP
共享实现：shared/，无第三产品身份
Agent：通过 MCP 查询两个图谱，不直接扫描全部资料
```
