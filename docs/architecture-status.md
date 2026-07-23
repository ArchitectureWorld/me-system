# ME-System 当前架构状态

> 更新日期：2026-07-23

本文件区分当前有效决策、已实现能力、过渡实现路径和下一阶段工作。

## 当前产品层级

```text
ME-System
├── ME-Brain   客观项目图谱
└── ME-Who     用户理解图谱
```

只有这两个产品图谱。

Source、Evidence、Candidate、PostgreSQL、权限、查询、MCP 和 CLI 都属于共享技术实现，不形成第三个产品、第三张业务图谱或第三个 Core 品牌。

## Codebase-Memory 参考模式

ME-Brain 与 ME-Who 都采用：

```text
原始来源
→ 多阶段结构化 Pass
→ 持久化图谱
→ 类型化查询
→ Compact GraphSlice
→ MCP / CLI
→ Agent 解释
```

共同原则：

- persistent graph first；
- incremental multi-pass indexing；
- typed MCP；
- compact-first；
- CLI/MCP parity；
- status/coverage；
- Agent 是智能层，后端不内置回答型 LLM。

## 当前有效决策

### ADR-0004：双权威图谱

- ME-Brain 与 ME-Who 是两个权威业务图谱；
- Bridge 只表达显式跨图关系；
- Context Pack 是 GraphSlice 投影；
- Agent 不能直接修改权威图谱。

### ADR-0005：只保留 ME-Brain 与 ME-Who

- 不定义 ME-Core、ME-Graph-Core、ME-Context 或 Source Ledger 产品；
- 共享代码使用中性 `shared/` 结构；
- ME-Brain 与 ME-Who 分别拥有本体、Pass 和查询；
- 两者共享 PostgreSQL、证据、时间、权限和应用服务；
- MCP 工具只使用 `brain_*` 与 `who_*` 图谱域前缀。

### ADR-0003：Agent 访问边界

- Agent 不直接连接 PostgreSQL；
- Agent 不生成任意 Cypher；
- Hermes/Pi 通过受限 MCP/SDK 访问；
- Adapter 不得反向定义图谱 Schema。

## 当前有效契约与设计

- `docs/specs/dual-graph-contract-v0.1.md`
- `docs/specs/me-brain-ontology-v0.1.md`
- `docs/specs/me-who-ontology-v0.1.md`
- `docs/superpowers/specs/2026-07-23-postgresql-graph-store-design.md`
- `docs/superpowers/specs/2026-07-23-hermes-readonly-mcp-design.md`
- `docs/superpowers/specs/2026-07-23-source-ledger-candidate-persistence-design.md`
- `docs/competitors/codebase-memory-architecture-review.md`

## 当前可运行基线

### 双图谱契约与查询

- ME-Brain、ME-Who、Bridge namespace；
- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- 项目快照、决策链、子图、证据和任务画像查询；
- 进程内 Candidate 提交、批准和驳回；
- `examples/graph/lighting-platform.json`。

### PostgreSQL 权威存储

- `InMemoryGraphStore`：测试和轻量验收；
- `SqlAlchemyGraphStore`：PostgreSQL 权威持久化；
- `graph_objects`：全局唯一节点和边；
- `graph_evidence_refs`：有序证据引用；
- Alembic 初始迁移；
- 数据库 CLI；
- PostgreSQL 16 Compose 示例。

### Hermes 只读 MCP

- canonical ID、label、alias、workspace path 和 external ID 的确定性解析；
- 服务端 Project allowlist；
- 服务端固定 ME-Who 用户；
- 显式项目所有权和历史决策范围；
- 跨项目语义边不扩大授权；
- 六个只读 stdio MCP 工具。

## 过渡实现路径

当前运行代码仍位于：

```text
services/me-core/
src/me_core/
```

这是 PR #6 留下的过渡技术路径，**不代表第三个产品**。它将在新增输入功能前迁移为：

```text
shared/
src/me_system/
```

同时：

```text
工作流名称      ME-System
主 CLI          me-system
主 MCP 命令     me-system-mcp
```

旧命令和旧 Python import 只在迁移期提供兼容，不作为新文档主入口。

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

- 物理目录和 Python 包迁移到 `shared/` / `me_system`；
- SourceRecord 与 EvidenceFragment 持久化；
- IngestionRun、coverage 和 quality；
- pending Candidate 与 ReviewEvent 跨重启持久化；
- Candidate 批准与权威写入的单事务闭环；
- Agent Conversation、Markdown、Git 和 Zotero Pass；
- 字段级 Agent 权限；
- 原始证据正文读取与脱敏；
- 真实 Hermes 项目恢复 Benchmark；
- 图谱治理界面；
- Pi Extension；
- 生产规模批量证据读取优化。

## 输入与证据模型

P0 收敛为：

```text
SourceRecord
EvidenceFragment
IngestionRun
CandidateGraphChangeRecord
CandidateReviewEvent
```

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

每个 Pass 记录版本、覆盖率、跳过和失败范围，不拥有独立数据库。

## 已废止方向

- ME-Core 作为第三个产品或架构层；
- ME-Graph-Core 作为额外核心；
- ME-Context 作为第三产品；
- ME-Reader 作为第三产品线；
- Source Ledger 作为独立服务或数据库；
- 独立 Agent Context Gateway 作为系统核心；
- Agent 直接查询数据库或任意 Cypher；
- 多个权威数据库并行；
- LLM 或模糊匹配擅自猜测项目范围；
- Adapter 自动把语义推断写入权威图谱。

## 下一实施切片

```text
移除过渡 ME-Core 命名与目录
→ Shared Source / Evidence / Ingestion Status
→ Persistent Candidate Buffer
→ Atomic Candidate Review
→ Agent Conversation Pass
→ Markdown / Git Pass
→ 真实 Hermes Benchmark
```
