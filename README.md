# ME-System

ME-System 是面向 AI Agent 的**双结构化图谱系统**。

- **ME-Brain Graph**：记录科研、设计、开发等客观项目的当前状态、历史决策、任务、问题、成果和证据。
- **ME-Who Graph**：记录 Agent 为了更好服务用户所需的明确事实、能力、角色、目标和协作规则。

二者共享证据、时间、权限和查询基础设施，但使用独立的图谱命名空间与领域本体。

## 一句话架构

```text
原始文件 / 对话 / Git / Zotero / 邮件
                 │
                 ▼
       Source & Evidence Core
                 │
                 ▼
       Candidate Graph Changes
                 │
          审核 / 规则确认
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
 ME-Brain Graph       ME-Who Graph
       └─────────┬─────────┘
                 ▼
        Graph Query Service
                 │
          MCP / REST / SDK
                 │
       Hermes / Pi / Codex
```

## 核心判断

1. **双图谱是产品核心。**
2. **文档标准化是输入与证据层。**
3. **MCP 是 Agent 访问图谱的方式。**
4. **Context Pack 是一次任务的临时 GraphSlice 投影，不是权威数据。**
5. **ME-Reader 不作为第三条产品线；Zotero、Obsidian 和文献精读属于 Research Domain 的 Adapter 与工作流。**
6. **Agent 只能提交候选图谱变更，不能直接修改权威图谱。**

## 当前可运行内容

首个实现位于：

```text
services/me-graph-core/
```

它已经支持：

- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- ME-Brain、ME-Who 与 Bridge 三类命名空间；
- 图谱节点和边的来源、时间、权威级别、确认状态与敏感度；
- `InMemoryGraphStore` 与 PostgreSQL `SqlAlchemyGraphStore`；
- Alembic 数据库迁移和 psycopg 3 连接；
- 候选变更提交、人工批准和驳回；
- 当前项目快照、决策链、子图和证据查询；
- 任务相关的 ME-Who 协作规则筛选；
- canonical ID、label、alias、工作目录和外部 ID 的确定性项目解析；
- Hermes 六工具只读 stdio MCP；
- 项目 allowlist、固定 ME-Who 用户和项目成员范围保护；
- `lighting-platform` 双图谱示例；
- Python 3.11 / 3.12、PostgreSQL 16 和真实 stdio MCP 客户端 CI。

### Fixture 体验

```bash
cd services/me-graph-core
python -m pip install -e '.[dev]'

me-graph load-fixture \
  --fixture ../../examples/graph/lighting-platform.json

me-graph project-snapshot \
  --fixture ../../examples/graph/lighting-platform.json \
  --project-id brain:project:lighting-platform

me-graph trace-decision \
  --fixture ../../examples/graph/lighting-platform.json \
  --decision-id brain:decision:radiance-primary

me-graph task-profile \
  --fixture ../../examples/graph/lighting-platform.json \
  --user-id who:user:master \
  --project-id brain:project:lighting-platform \
  --task-type implementation
```

### PostgreSQL 持久化

```bash
export ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph:你的密码@127.0.0.1:5432/me_graph'

me-graph db-upgrade
me-graph import-fixture \
  --fixture ../../examples/graph/lighting-platform.json
me-graph project-snapshot \
  --project-id brain:project:lighting-platform
```

部署说明见 [`services/me-graph-core/README.md`](services/me-graph-core/README.md)。

### Hermes 只读 MCP

第一版向 Hermes 只暴露：

```text
brain_resolve_project
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
```

本地直接启动：

```bash
ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph_reader:密码@127.0.0.1:5432/me_graph' \
ME_GRAPH_HERMES_USER_ID='who:user:master' \
ME_GRAPH_ALLOWED_PROJECT_IDS='brain:project:lighting-platform' \
me-graph-mcp
```

Hermes 配置、只读数据库账号和工具白名单见 [`integrations/hermes/README.md`](integrations/hermes/README.md)。

### 测试

```bash
cd services/me-graph-core
pytest -q
python -m compileall -q src
```

## 仓库目标结构

```text
me-system/
├── services/
│   ├── me-graph-core/
│   ├── source-ledger/
│   ├── document-normalizer/
│   ├── graph-ingestion/
│   ├── graph-query/
│   └── mcp-server/
├── graphs/
│   ├── me-brain/
│   ├── me-who/
│   └── bridge/
├── integrations/
│   ├── hermes/
│   ├── pi/
│   ├── zotero/
│   └── obsidian/
├── domains/
│   ├── software/
│   ├── research/
│   └── design/
└── docs/
```

当前 `me-graph-core` 将契约、内存 Store、PostgreSQL Store、迁移、查询和 Hermes stdio MCP 放在一个可运行包中。等接口与真实工作流稳定后，再按目标结构拆分服务。

## 文档导航

- [当前架构状态](docs/architecture-status.md)
- [当前产品与架构总纲](docs/00-product-and-architecture-overview.md)
- [ADR-0004：双权威图谱作为系统核心](docs/adr/ADR-0004-two-canonical-graphs.md)
- [双图谱契约 v0.1](docs/specs/dual-graph-contract-v0.1.md)
- [ME-Brain 本体 v0.1](docs/specs/me-brain-ontology-v0.1.md)
- [ME-Who 本体 v0.1](docs/specs/me-who-ontology-v0.1.md)
- [ME-Brain 产品定义](docs/products/me-brain.md)
- [ME-Who 产品定义](docs/products/me-who.md)
- [推荐开发路径](docs/roadmap/recommended-development-path.md)
- [PostgreSQL GraphStore 设计](docs/superpowers/specs/2026-07-23-postgresql-graph-store-design.md)
- [Hermes 只读 MCP 设计](docs/superpowers/specs/2026-07-23-hermes-readonly-mcp-design.md)
- [Hermes 接入与部署](integrations/hermes/README.md)
- [Pi 接入边界](integrations/pi/README.md)

## 当前开发优先级

```text
1. 双图谱契约与真实样本                    已完成首版
2. PostgreSQL GraphStore                   已完成首版
3. Project ID Resolve                      已完成首版
4. Hermes MCP 只读 Adapter                 已完成首版
5. 真实 Hermes 项目恢复 Benchmark
6. Source / Evidence 与对话、Markdown、Git Adapter
7. Candidate 持久化、审核与字段级权限
8. 最小 ME-Who 图谱深化
9. Pi Extension
10. Research / Software / Design 领域扩展
```

在真实 Hermes 项目恢复和输入候选闭环稳定前，不优先开发完整前端、复杂 Handoff 平台、全格式文档解析或数字人格。
