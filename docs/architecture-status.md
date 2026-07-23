# ME-System 当前架构状态

> 更新日期：2026-07-23

本文件区分当前有效决策、已实现能力、实施边界和下一阶段工作。

## 当前唯一架构层级

```text
ME-System                 产品与仓库
└── ME-Core               唯一运行与语义内核
    ├── ME-Brain Graph    项目事实图谱域
    ├── ME-Who Graph      用户理解图谱域
    ├── Bridge            显式跨图关系
    ├── Source/Evidence   输入与证据
    ├── Candidate/Review  权威写入缓冲与治理
    ├── Query/Projection  GraphSlice
    └── MCP/CLI           薄访问前端
```

不存在独立的 ME-Context Core、ME-Graph Core、Source Ledger Core 或 MCP Core。

## 当前有效的最高层决策

### ADR-0004：双权威图谱

- ME-Brain Graph 与 ME-Who Graph 是两个权威业务图谱域；
- 文档标准化属于输入与证据层；
- Context Pack 是 GraphSlice 的运行时投影；
- Agent 不能直接修改权威图谱。

### ADR-0005：单一 ME-Core

- `services/me-core/` 是唯一运行内核；
- 两个图谱域共用同一 PostgreSQL、事务、证据、查询和权限语义；
- Source、Candidate、MCP、CLI、Adapter 都是 ME-Core 的内部模块或薄前端；
- Domain Pack 不得创建第二套 Store；
- 只有可量化的性能、安全或团队边界才能触发拆分评审。

### ADR-0003：Agent 访问边界

- Agent 不直接连接 PostgreSQL；
- Agent 不生成任意 Cypher；
- Hermes/Pi 通过受限 MCP/SDK 工具访问；
- Adapter 不得反向定义图谱 Schema。

## 当前有效契约与设计

- `docs/specs/dual-graph-contract-v0.1.md`
- `docs/specs/me-brain-ontology-v0.1.md`
- `docs/specs/me-who-ontology-v0.1.md`
- `services/me-core/schemas/`
- `docs/superpowers/specs/2026-07-23-postgresql-graph-store-design.md`
- `docs/superpowers/specs/2026-07-23-hermes-readonly-mcp-design.md`
- `docs/superpowers/specs/2026-07-23-source-ledger-candidate-persistence-design.md`
- `docs/competitors/codebase-memory-architecture-review.md`

## 当前可运行基线

### ME-Core 图谱与查询

- ME-Brain、ME-Who、Bridge 命名空间；
- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- 当前项目快照、决策链、子图、证据和任务画像查询；
- 进程内 Candidate 提交、批准和驳回；
- `examples/graph/lighting-platform.json`。

### PostgreSQL 权威存储

- `InMemoryGraphStore`：测试和轻量验收；
- `SqlAlchemyGraphStore`：PostgreSQL 权威持久化；
- `graph_objects`：全局唯一节点和边；
- `graph_evidence_refs`：有序证据引用；
- Alembic 初始迁移；
- `db-upgrade`、`import-fixture` 和数据库查询 CLI；
- `deploy/postgres/`：PostgreSQL 16 Compose 示例。

### Hermes 只读 MCP

- canonical ID、label、alias、workspace path 和 external ID 的确定性 Resolver；
- 服务端 Project allowlist；
- 服务端固定 ME-Who 用户；
- 显式项目所有权和历史决策范围；
- 跨项目语义边不扩大授权；
- 六个只读 stdio MCP 工具；
- `integrations/hermes/` 配置、Bootstrap 和部署说明。

### 当前命名

```text
服务目录        services/me-core/
Python 包       me_core
Python 分发     me-core
主 CLI          me-system
主 MCP 命令     me-system-mcp
```

旧命令 `me-graph` 与 `me-graph-mcp` 只作为一个小版本的兼容别名。

## 已验证环境

```text
Python 3.11 单元与契约测试
Python 3.12 单元与契约测试
PostgreSQL 16 迁移和图谱查询
真实 stdio MCP ClientSession E2E
Python compileall
```

## 当前实现边界

尚未完成：

- SourceRecord 与 EvidenceFragment 持久化；
- IngestionRun、覆盖率和质量状态；
- pending Candidate 与 ReviewEvent 跨重启持久化；
- Candidate 批准与权威写入的单事务闭环；
- Agent Conversation、Markdown、Git 和 Zotero Pass；
- 图谱字段级 Agent 权限；
- 原始证据正文读取和内容脱敏；
- 真实 Hermes 项目恢复 Benchmark；
- Streamable HTTP / OAuth MCP；
- 图谱治理界面；
- Pi Extension；
- 生产规模批量证据读取优化。

## 输入与证据原则

P0 输入模型收敛为：

```text
SourceRecord
EvidenceFragment
IngestionRun
CandidateGraphChangeRecord
CandidateReviewEvent
```

复杂 Document、Page、Figure、Equation 和版面对象只在真实领域需求出现后扩展，不作为所有输入的前置条件。

Adapter 采用多阶段 Pass：

```text
Discover
→ Normalize
→ Fragment
→ Extract Candidate
→ Resolve Identity
→ Detect Conflict
→ Review
→ Commit Canonical Graph
→ Build Derived Index
```

每个 Pass 记录版本、覆盖率、跳过和失败范围，但不拥有独立数据库。

## 已废止方向

- ME-Context 作为第三产品；
- ME-Reader 作为第三产品线；
- ME-Graph Core 作为额外核心；
- Source Ledger 作为独立服务或数据库；
- 独立 Agent Context Gateway 作为系统核心；
- 在权威图谱之前建设完整 Handoff 和多 Agent 编排；
- Agent 直接查询数据库或任意 Cypher；
- 多个权威数据库并行；
- LLM 或模糊匹配擅自猜测项目范围；
- Adapter 自动把语义推断写入权威图谱。

## 下一实施切片

```text
Source / Evidence / Ingestion Status
→ Persistent Candidate Buffer
→ Atomic Candidate Review
→ Agent Conversation Pass
→ Markdown / Git Pass
→ 真实 Hermes Benchmark
```

这些能力全部在 `services/me-core/` 内实现，不新增平级核心。