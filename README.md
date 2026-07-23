# ME-System

ME-System 面向 AI Agent 提供两个结构化图谱产品：

```text
ME-System
├── ME-Brain   项目、科研、设计与开发图谱
└── ME-Who     用户事实、能力、偏好与协作图谱
```

**没有第三个产品。** 来源、证据、候选、持久化、权限和 MCP 都只是两个图谱共同使用的内部实现。

## 一句话架构

```text
文件 / 对话 / Git / Zotero / 邮件
                │
                ▼
       Shared Source & Evidence
                │
                ▼
       Candidate Graph Changes
                │
          审核 / 规则确认
                │
       ┌────────┴────────┐
       ▼                 ▼
   ME-Brain           ME-Who
       └────────┬────────┘
                ▼
       Query / GraphSlice
                │
          MCP / CLI / Web
                │
       Hermes / Pi / Codex
```

## Codebase-Memory 参考原则

ME-Brain 与 ME-Who 都参考 Codebase-Memory 的图谱方法：

1. **Persistent graph first**：先构建持久化结构图谱，再让 Agent 查询；
2. **Multi-pass indexing**：发现、标准化、节点、关系、冲突和质量分别处理；
3. **Typed MCP tools**：工具直接表达结构问题，不做泛化聊天接口；
4. **Compact first**：默认返回紧凑结构，需要时再下钻证据和原文；
5. **CLI / MCP parity**：CLI 和 MCP 复用相同应用服务；
6. **Status / coverage**：明确尚未摄取、部分覆盖和失败范围；
7. **Agent as intelligence layer**：Agent 理解任务和解释结果，后端不内置回答型 LLM。

ME-System 不照搬：

- 普通 Agent 任意 Cypher；
- 自动语义抽取直接写入权威事实；
- 每项目 SQLite 权威库；
- 一次性开放大量工具。

## 两个图谱分别做什么

### ME-Brain

主要节点：

```text
Project / Requirement / Decision / Task / Issue / Constraint
Artifact / Experiment / Document / Person / Evidence
```

主要关系：

```text
HAS_DECISION / HAS_TASK / SUPERSEDES / DEPENDS_ON
BLOCKS / IMPLEMENTS / PRODUCES / SUPPORTED_BY
```

主要回答：

- 项目目前进行到哪里；
- 当前路线和约束是什么；
- 哪条新决策替代了旧决策；
- 哪个问题阻塞了哪些任务；
- 某个成果实现了什么；
- 一项结论的证据在哪里。

### ME-Who

主要节点：

```text
User / Role / Capability / Preference / CollaborationRule
Goal / ProjectRole / Experience / Evidence
```

主要关系：

```text
HAS_ROLE / HAS_CAPABILITY / PREFERS / APPLIES_TO
PARTICIPATES_IN / SUPERSEDES / CONFIRMED_BY / SUPPORTED_BY
```

主要回答：

- 当前任务需要哪些用户背景；
- Agent 应采用怎样的自主程度；
- 哪些内容已经确认，不要重复询问；
- 某项偏好适用于哪个项目和任务；
- 这项用户理解来自什么证据；
- 用户状态和偏好如何变化。

## 稳定原则

1. **只有 ME-Brain 和 ME-Who 两个产品图谱。**
2. **一个 PostgreSQL 权威数据源。** 两个图谱用 namespace 和权限隔离。
3. **Graph first。** Agent 默认读 GraphSlice，不重新扫描全部来源。
4. **Candidate first。** 自动解析和 Agent 只能提交候选，不能直接改权威图谱。
5. **Evidence required。** 高价值节点和关系必须能回到证据。
6. **MCP 是薄适配。** 只调用应用服务，不定义图谱 Schema。
7. **项目范围显式。** ME-Brain 查询必须限定项目。
8. **ME-Who 最小暴露。** 只返回当前 Agent 和任务真正需要的内容。
9. **质量可见。** 截断、覆盖率和失败范围必须显式返回。
10. **不再新增 Core、Context、Reader 等平级产品名称。**

## 当前可运行能力

当前实现已经支持：

- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- ME-Brain、ME-Who 与 Bridge namespace；
- 来源、时间、权威级别、确认状态与敏感度；
- 内存 Store 与 PostgreSQL `SqlAlchemyGraphStore`；
- Alembic 迁移和 psycopg 3；
- 进程内 Candidate 提交、批准和驳回；
- 项目快照、决策链、子图和证据查询；
- 任务相关 ME-Who 规则筛选；
- 确定性 Project Resolver；
- Hermes 六工具只读 stdio MCP；
- 项目 allowlist、固定 ME-Who 用户和范围保护；
- Python 3.11 / 3.12、PostgreSQL 16 和真实 stdio MCP CI。

> 当前代码仍位于历史路径 `services/me-core/`。该路径只是过渡实现位置，不代表第三个产品；下一次代码整理会迁移到中性的 `shared/` 与 `me_system` 包结构。

## Fixture 验收

```bash
cd services/me-core
python -m pip install -e '.[dev]'

me-system load-fixture \
  --fixture ../../examples/graph/lighting-platform.json

me-system project-snapshot \
  --fixture ../../examples/graph/lighting-platform.json \
  --project-id brain:project:lighting-platform

me-system trace-decision \
  --fixture ../../examples/graph/lighting-platform.json \
  --decision-id brain:decision:radiance-primary

me-system task-profile \
  --fixture ../../examples/graph/lighting-platform.json \
  --user-id who:user:master \
  --project-id brain:project:lighting-platform \
  --task-type implementation
```

## PostgreSQL 持久化

```bash
export ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph:你的密码@127.0.0.1:5432/me_graph'

me-system db-upgrade
me-system import-fixture \
  --fixture ../../examples/graph/lighting-platform.json
me-system project-snapshot \
  --project-id brain:project:lighting-platform
```

当前部署说明仍位于 [`services/me-core/README.md`](services/me-core/README.md)，等待目录迁移后同步调整。

## Hermes 只读 MCP

```text
brain_resolve_project
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
```

启动：

```bash
ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph_reader:密码@127.0.0.1:5432/me_graph' \
ME_GRAPH_HERMES_USER_ID='who:user:master' \
ME_GRAPH_ALLOWED_PROJECT_IDS='brain:project:lighting-platform' \
me-system-mcp
```

Hermes 配置见 [`integrations/hermes/README.md`](integrations/hermes/README.md)。

## 目标仓库结构

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
├── integrations/
│   ├── mcp/
│   ├── hermes/
│   └── pi/
├── examples/
└── docs/
```

`shared/` 只表示技术复用，不是第三个产品。

## 文档导航

- [当前架构状态](docs/architecture-status.md)
- [产品与架构总纲](docs/00-product-and-architecture-overview.md)
- [ADR-0004：双权威图谱](docs/adr/ADR-0004-two-canonical-graphs.md)
- [ADR-0005：仅保留 ME-Brain 与 ME-Who](docs/adr/ADR-0005-single-graph-kernel.md)
- [Codebase-Memory 架构 Review](docs/competitors/codebase-memory-architecture-review.md)
- [双图谱契约 v0.1](docs/specs/dual-graph-contract-v0.1.md)
- [ME-Brain 本体 v0.1](docs/specs/me-brain-ontology-v0.1.md)
- [ME-Who 本体 v0.1](docs/specs/me-who-ontology-v0.1.md)
- [共享输入与 Candidate 持久化设计](docs/superpowers/specs/2026-07-23-source-ledger-candidate-persistence-design.md)
- [推荐开发路径](docs/roadmap/recommended-development-path.md)
- [Hermes 接入与部署](integrations/hermes/README.md)

## 当前开发优先级

```text
1. 双图谱契约与真实样本                         已完成首版
2. PostgreSQL 权威存储                          已完成首版
3. Project Resolve 与 Hermes 只读 MCP           已完成首版
4. 移除 ME-Core 产品语言并迁移到 shared/         当前
5. Source / Evidence / Ingestion Status
6. Persistent Candidate Buffer 与原子审核
7. Agent Conversation Pass
8. Markdown / Git Pass
9. 真实 Hermes 项目恢复 Benchmark
10. ME-Who 深化、Pi 与领域包
```

在输入候选闭环和真实 Agent 评估稳定前，不优先开发独立服务、大型前端、复杂 Handoff、万能文档解析或数字人格。
