# ME-System 当前架构状态

> 更新日期：2026-07-23

本文件用于区分当前有效规范、已实现能力、历史研究材料和后续实现方向。

## 当前有效的最高层决策

1. `docs/adr/ADR-0004-two-canonical-graphs.md`
   - ME-Brain Graph 与 ME-Who Graph 是两个产品核心。
   - 文档标准化属于输入与证据层。
   - MCP、REST、SDK 属于 Agent 访问层。
   - Context Pack 是 GraphSlice 的运行时投影。

2. `docs/adr/ADR-0003-agent-context-access-layer.md`
   - 规定 Agent 不直连数据库，以及 Hermes/Pi 的访问边界。
   - 受 ADR-0004 约束，不得反向定义图谱模型。

## 当前有效的实现契约

- `docs/specs/dual-graph-contract-v0.1.md`
- `docs/specs/me-brain-ontology-v0.1.md`
- `docs/specs/me-who-ontology-v0.1.md`
- `services/me-graph-core/schemas/`
- `docs/superpowers/specs/2026-07-23-postgresql-graph-store-design.md`
- `docs/superpowers/specs/2026-07-23-hermes-readonly-mcp-design.md`

## 当前可运行基线

### 图谱契约与查询

- `services/me-graph-core/`
- `examples/graph/lighting-platform.json`
- ME-Brain、ME-Who、Bridge 命名空间；
- 当前项目快照、决策链、子图、证据和任务画像查询；
- Candidate 提交、批准和驳回。

### 持久化

- `InMemoryGraphStore`：测试与轻量运行；
- `SqlAlchemyGraphStore`：PostgreSQL 权威持久化；
- `graph_objects`：全局唯一的节点与边；
- `graph_evidence_refs`：有序证据引用；
- Alembic 初始迁移和迁移幂等性；
- `db-upgrade`、`import-fixture` 和数据库查询 CLI；
- `deploy/postgres/`：PostgreSQL 16 Compose 示例。

### Hermes 只读访问

- canonical ID、label、alias、workspace path 和 external ID 的确定性 Project Resolver；
- `ME_GRAPH_ALLOWED_PROJECT_IDS` 服务端 allowlist；
- `ME_GRAPH_HERMES_USER_ID` 固定 ME-Who 用户；
- 显式项目所有权和历史决策继承范围；
- 跨项目语义边不扩大授权；
- 六个只读 stdio MCP 工具；
- `integrations/hermes/` 配置、Bootstrap 和部署说明。

当前实现已在 GitHub Actions 中通过：

```text
Python 3.11 单元与契约测试
Python 3.12 单元与契约测试
PostgreSQL 16 迁移和图谱查询
真实 stdio MCP ClientSession E2E
```

## 当前实现边界

以下内容尚未完成：

- 使用真实 Hermes UI/Agent 的项目恢复 Benchmark；
- 文档、对话和 Git 的 CandidateGraphChange Adapter；
- 未批准 Candidate 与审核日志的跨重启持久化；
- 图谱字段级 Agent 权限过滤；
- 原始证据正文读取和内容脱敏；
- Streamable HTTP / OAuth MCP；
- 图谱治理界面；
- Pi Extension；
- 生产规模下的批量证据读取优化。

## 输入与证据层材料

`docs/specs/document-information-standardization-v0.1.md` 保留为广义输入格式研究材料，但它不是当前 P0 的完整实现清单。P0 仅优先实现：

- SourceRecord
- Document
- DocumentVersion
- ContentFragment
- EvidenceAnchor
- ParserRun / QualityIssue

其余复杂格式、资产重建和全格式解析在真实需求出现后逐项扩展。

## 已废止的方向

以下内容不再作为有效架构：

- ME-Context 作为第三个产品；
- ME-Reader 作为第三条产品线；
- 独立 Agent Context Gateway 作为系统核心；
- 在权威图谱之前优先建设完整 Handoff、复杂 Token 编译和多 Agent 编排协议；
- Agent 直接查询数据库或生成任意 Cypher；
- 同时维护多个权威数据库实现；
- 用 LLM 或模糊匹配擅自猜测项目范围。

历史研究内容可通过 Git 历史和已关闭 PR 查看，不继续保留为主分支活动规格。

## 下一实施切片

```text
真实 Hermes 项目恢复 Benchmark
→ Agent Conversation Adapter
→ Candidate 持久化与审核
→ Markdown / Git Adapter
```
