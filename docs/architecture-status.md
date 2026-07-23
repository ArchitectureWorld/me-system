# ME-System 当前架构状态

> 更新日期：2026-07-23

## 产品层级

```text
ME-System
├── ME-Brain   客观项目图谱
└── ME-Who     用户理解图谱
```

只有这两个权威图谱领域。

Evidence、Ingestion、Candidate、Review、Persistence、Query、Bridge、MCP 和 CLI 都是 ME-System 的内部实现职责，不形成第三个产品、第三张业务图谱或第三个 Core 品牌。

## 参考运行模式

ME-Brain 与 ME-Who 共同吸收 Codebase-Memory 和 Graphify 的方法：

```text
原始来源
→ 多阶段结构化索引
→ 证据与摄取状态
→ Candidate
→ 审核
→ 持久化图谱
→ 类型化查询 / 路径解释
→ Compact GraphSlice
→ MCP / CLI
→ Agent 解释与执行
```

共同原则：

- persistent graph first；
- incremental multi-stage indexing；
- typed MCP；
- compact-first；
- path-based explanation；
- CLI / MCP parity；
- status / coverage / ambiguity；
- Agent 可以提出 Candidate，但未经审核不进入权威图谱。

## 当前有效决策

### ADR-0004：双权威图谱

- ME-Brain 与 ME-Who 是两个权威业务图谱；
- Bridge 只表达显式跨图关系；
- Context Pack 是 GraphSlice 投影；
- Agent 不能直接修改权威图谱。

### ADR-0005：一个系统、两个图谱领域

- 唯一产品主体是 ME-System；
- Python 分发和导入包统一为 `me-system` / `me_system`；
- 不保留 `me-graph-core`、`me-core`、`me_graph_core`、`me_core` 产品身份；
- 主命令只有 `me-system` 与 `me-system-mcp`；
- MCP 工具只使用 `brain_*` 与 `who_*` 领域前缀。

### ADR-0003：Agent 访问边界

- Agent 不直接连接 PostgreSQL；
- Agent 不生成任意 SQL 或 Cypher；
- Hermes / Pi 通过受限 MCP / SDK 访问；
- Adapter 不得反向定义图谱 Schema。

## 当前有效契约与评审

- `docs/specs/dual-graph-contract-v0.1.md`
- `docs/specs/me-brain-ontology-v0.1.md`
- `docs/specs/me-who-ontology-v0.1.md`
- `docs/superpowers/specs/2026-07-23-postgresql-graph-store-design.md`
- `docs/superpowers/specs/2026-07-23-hermes-readonly-mcp-design.md`
- `docs/superpowers/specs/2026-07-23-source-ledger-candidate-persistence-design.md`
- `docs/competitors/codebase-memory-architecture-review.md`
- `docs/competitors/graphify-review.md`

## 当前可运行基线

### 统一实现

```text
pyproject.toml
src/me_system/
tests/
schemas/
migrations/
```

### 双图谱契约与查询

- ME-Brain、ME-Who、Bridge namespace；
- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- 项目快照、决策链、子图、证据和任务画像查询；
- `examples/graph/lighting-platform.json`。

### PostgreSQL 权威存储

- `InMemoryGraphStore`：测试和轻量验收；
- `SqlAlchemyGraphStore`：PostgreSQL 权威持久化；
- `graph_objects`：全局唯一节点和边；
- `graph_evidence_refs`：有序证据引用；
- Alembic 迁移；
- PostgreSQL 16 Compose 示例。

### Source / Evidence / Ingestion

- `SourceRecord`：不可变来源身份、内容哈希和敏感度；
- `EvidenceFragment`：可被节点和关系稳定引用的最小证据；
- `IngestionRun`：Adapter 版本、状态、coverage、quality、跳过和失败计数；
- Source 与 Fragment 幂等冲突检测；
- 来源、证据和摄取状态跨进程保存。

### Persistent Candidate / Review

- `candidate_graph_changes`：持久化 Candidate Queue；
- `candidate_evidence_refs`：有序候选证据；
- `candidate_review_events`：追加式提交、批准和驳回事件；
- Candidate 幂等重试与 payload 冲突检测；
- Candidate 批准、权威节点/边写入、状态更新和 ReviewEvent 在同一事务；
- Duplicate ID、缺失端点、非法跨图和 ReviewEvent 写入失败均整笔回滚；
- CLI 提供来源登记、候选提交、列表和人工审核入口。

### Hermes 只读 MCP

- canonical ID、label、alias、workspace path 和 external ID 的确定性解析；
- 服务端 Project allowlist；
- 服务端固定 ME-Who 用户；
- 显式项目所有权和历史决策范围；
- 跨项目语义边不扩大授权；
- 六个只读 stdio MCP 工具；
- Candidate 和审核功能不暴露给 Hermes。

## 验证门禁

当前 CI 覆盖：

```text
Python 3.11 单元与契约测试
Python 3.12 单元与契约测试
Alembic 0001 + 0002
PostgreSQL 16 图谱查询
Source → Evidence → Candidate → Review → Canonical Graph E2E
真实 stdio MCP ClientSession E2E
Python compileall
```

## 当前实现边界

尚未完成：

- 增量 Manifest 与 Adapter versioning；
- Agent Conversation、Markdown、Git 和 Zotero Adapter；
- `derivation_kind`：EXPLICIT / RULE_DERIVED / MODEL_INFERRED / AMBIGUOUS；
- 路径 / explain / impact MCP 查询；
- Graph Report 与 Benchmark；
- 字段级 Agent 权限；
- 原始证据正文读取与脱敏；
- 图谱治理界面；
- Pi Extension；
- 生产规模批量证据读取优化。

## 下一实施切片

```text
增量 Manifest + Adapter versioning
→ Agent Conversation Adapter
→ derivation_kind
→ shortest path / explain path
→ Graph Report + Benchmark
```

## 明确废止

- ME-Context 作为第三产品；
- ME-Reader 作为第三产品；
- ME-Core 或 ME-Graph-Core 作为第三核心；
- Source Ledger 作为独立产品或独立权威数据库；
- 在权威图谱前优先建设复杂 Handoff；
- Agent 直接查询数据库；
- 自动推断静默写入权威图谱；
- 将完整 ME-Who 图谱默认提交 Git。
