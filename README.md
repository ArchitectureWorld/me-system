# ME-System

ME-System 是面向 AI Agent 的双结构化图谱系统。

```text
ME-System
└── ME-Core                 唯一运行与语义内核
    ├── ME-Brain Graph      项目、科研、设计与开发事实
    ├── ME-Who Graph        用户事实、能力与协作规则
    ├── Source & Evidence   原始来源与可寻址证据
    ├── Candidate Buffer    待审核图谱变更
    ├── Query & Projection  GraphSlice 与任务投影
    └── MCP / CLI           Agent 与人的薄访问前端
```

ME-Brain 与 ME-Who 是 ME-Core 内的两个权威图谱域，不是两个独立后端。Source、Candidate、MCP、CLI 和后续 Adapter 也都不是新的核心或平级产品。

## 一句话架构

```text
文件 / 对话 / Git / Zotero / 邮件
                │
                ▼
              ME-Core
      ┌─────────┴─────────┐
      │ Source & Evidence │
      └─────────┬─────────┘
                ▼
        Candidate Graph Changes
                │
          审核 / 规则确认
                │
       ┌────────┴────────┐
       ▼                 ▼
 ME-Brain Graph     ME-Who Graph
       └────────┬────────┘
                ▼
       Query / GraphSlice
                │
          MCP / CLI / Web
                │
       Hermes / Pi / Codex
```

## 稳定原则

1. **一个 ME-Core。** 所有图谱、来源、候选、查询和访问语义只定义一次。
2. **两个权威图谱域。** ME-Brain 保存客观项目事实；ME-Who 保存任务相关的用户理解。
3. **一个 PostgreSQL 真相源。** 不并行维护第二个权威数据库。
4. **结构优先。** Agent 默认读取紧凑 GraphSlice，需要核验时再下钻到 EvidenceRef 和原始来源。
5. **Candidate 先于 Canonical。** 自动解析和 Agent 只能提交候选，不能直接修改权威图谱。
6. **MCP 是薄适配。** MCP、CLI 和未来 Web UI 复用同一 Application Service，不反向定义图谱 Schema。
7. **项目范围显式。** ME-Brain 查询必须限定项目；ME-Who 只返回当前 Agent 和任务所需内容。
8. **质量可见。** 摄取覆盖率、失败范围、截断和历史事实必须显式返回。
9. **不建设第三产品线。** ME-Reader、ME-Context、Source Ledger Service 都不作为平级产品。

这些原则参考了 Codebase-Memory 的单一结构后端、多阶段 Pipeline、Persistent Graph First、Compact First 和 MCP/CLI 对等设计；ME-System 不照搬其 SQLite、任意 Cypher或自动索引直写权威图谱的做法。

## 当前可运行能力

实现位于：

```text
services/me-core/
```

当前已经支持：

- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- ME-Brain、ME-Who 与 Bridge 命名空间；
- 来源、时间、权威级别、确认状态与敏感度；
- `InMemoryGraphStore` 与 PostgreSQL `SqlAlchemyGraphStore`；
- Alembic 迁移和 psycopg 3；
- 进程内 Candidate 提交、批准和驳回；
- 项目快照、决策链、子图和证据查询；
- 任务相关 ME-Who 规则筛选；
- canonical ID、label、alias、工作目录和外部 ID 的确定性项目解析；
- Hermes 六工具只读 stdio MCP；
- 项目 allowlist、固定 ME-Who 用户和项目成员范围保护；
- `lighting-platform` 双图谱示例；
- Python 3.11 / 3.12、PostgreSQL 16 和真实 stdio MCP CI。

## 安装与 Fixture 验收

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

部署说明见 [`services/me-core/README.md`](services/me-core/README.md)。数据库表名和 `ME_GRAPH_*` 环境变量暂时保持兼容；它们不代表另一个核心。

## Hermes 只读 MCP

向 Hermes 暴露六个只读工具：

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

Hermes 配置、只读数据库账号和工具白名单见 [`integrations/hermes/README.md`](integrations/hermes/README.md)。

兼容期内，旧命令 `me-graph` 和 `me-graph-mcp` 仍指向同一个 ME-Core；新文档统一使用 `me-system` 与 `me-system-mcp`。

## 测试

```bash
cd services/me-core
pytest -q
python -m compileall -q src
```

## 仓库结构

```text
me-system/
├── services/
│   └── me-core/              唯一运行内核
│       └── src/me_core/
│           ├── persistence/
│           ├── ingestion/    下一实施模块
│           ├── adapters/     后续输入 Pass
│           └── hermes/       MCP 适配
├── examples/
│   └── graph/
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

`integrations/` 和 `domains/` 是配置、Adapter 与领域扩展，不拥有独立权威 Store。

## 文档导航

- [当前架构状态](docs/architecture-status.md)
- [产品与架构总纲](docs/00-product-and-architecture-overview.md)
- [ADR-0004：双权威图谱](docs/adr/ADR-0004-two-canonical-graphs.md)
- [ADR-0005：单一 ME-Core](docs/adr/ADR-0005-single-graph-kernel.md)
- [Codebase-Memory 架构 Review](docs/competitors/codebase-memory-architecture-review.md)
- [双图谱契约 v0.1](docs/specs/dual-graph-contract-v0.1.md)
- [ME-Brain 本体 v0.1](docs/specs/me-brain-ontology-v0.1.md)
- [ME-Who 本体 v0.1](docs/specs/me-who-ontology-v0.1.md)
- [输入与 Candidate 持久化设计](docs/superpowers/specs/2026-07-23-source-ledger-candidate-persistence-design.md)
- [推荐开发路径](docs/roadmap/recommended-development-path.md)
- [Hermes 接入与部署](integrations/hermes/README.md)

## 当前开发优先级

```text
1. 双图谱契约与真实样本                     已完成首版
2. PostgreSQL 权威存储                      已完成首版
3. Project Resolve 与 Hermes 只读 MCP       已完成首版
4. ME-Core 名称与目录统一                   本 PR
5. Source / Evidence / Ingestion Status
6. Persistent Candidate Buffer 与原子审核
7. Agent Conversation Pass
8. Markdown / Git Pass
9. 真实 Hermes 项目恢复 Benchmark
10. ME-Who 深化、Pi 与领域包
```

在输入候选闭环和真实 Agent 评估稳定前，不优先开发独立服务、大型前端、复杂 Handoff、万能文档解析或数字人格。