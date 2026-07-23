# ME-System

ME-System 是面向 AI Agent 的统一结构化图谱系统，只有两个权威图谱领域：

```text
ME-System
├── ME-Brain   项目、科研、设计与开发图谱
└── ME-Who     用户事实、能力、偏好与协作图谱
```

**没有第三个产品或第三个 Core。** Evidence、Ingestion、Candidate Review、Persistence、Query、Bridge、CLI 与 MCP 都只是 ME-System 的内部实现职责。

## 一句话架构

```text
文件 / 对话 / Git / Zotero / 邮件
                 │
                 ▼
       SourceRecord / EvidenceFragment
                 │
                 ▼
             IngestionRun
                 │
                 ▼
        CandidateGraphChange
                 │
          审核 / 规则确认
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
   ME-Brain             ME-Who
       └─────────┬─────────┘
                 ▼
        Query / GraphSlice
                 │
           MCP / CLI / Web
                 │
        Hermes / Pi / Codex
```

## 参考方法

ME-Brain 与 ME-Who 共同吸收 Codebase-Memory 和 Graphify 的有效方法：

1. **Persistent graph first**：先建立持久化结构图，再让 Agent 查询；
2. **Multi-stage indexing**：来源、证据、摄取、候选、审核和分析分阶段完成；
3. **Typed MCP tools**：工具直接表达结构问题，不提供泛化聊天接口；
4. **Compact first**：默认返回紧凑子图，需要时再下钻证据与原文；
5. **Path-based explanation**：答案应能沿节点、关系和证据路径解释；
6. **Incremental indexing**：通过内容哈希、Adapter 版本和 Manifest 只处理变化内容；
7. **CLI / MCP parity**：CLI 与 MCP 复用同一应用与查询服务；
8. **Status / coverage**：显式报告未覆盖、部分覆盖、失败和歧义；
9. **Agent as intelligence layer**：Agent 理解任务和提出候选，后端不把未经审核的模型输出当权威事实。

ME-System 不照搬：

- 普通 Agent 任意 SQL 或 Cypher；
- 自动语义抽取直接写入权威事实；
- 一个 `graph.json` 作为权威数据库；
- ME-Brain 与 ME-Who 合并为无权限边界的平面图；
- 将完整 ME-Who 图谱提交 Git；
- 一次性开放大量未经 Benchmark 验证的工具。

## 两个图谱分别做什么

### ME-Brain

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

- 项目当前进行到哪里；
- 当前路线和约束是什么；
- 哪条新决策替代了旧决策；
- 哪个问题阻塞了哪些任务；
- 某个成果实现了什么；
- 一项结论的证据在哪里；
- 某项变化会影响哪些节点和路径。

### ME-Who

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

1. **只有 ME-Brain 和 ME-Who 两个权威图谱领域。**
2. **一个 PostgreSQL 权威数据源。** 两个图谱用 namespace 和权限隔离。
3. **Graph first。** Agent 默认读 GraphSlice，不重新扫描全部来源。
4. **Candidate first。** 自动解析和 Agent 只能提交候选，不能直接修改权威图谱。
5. **Evidence required。** 高价值节点和关系必须能回到证据片段。
6. **MCP 是薄适配。** 只调用应用和查询服务，不定义图谱 Schema。
7. **项目范围显式。** ME-Brain 查询必须限定项目。
8. **ME-Who 最小暴露。** 只返回当前 Agent 和任务真正需要的内容。
9. **质量可见。** 覆盖率、跳过项、失败项、歧义和推导方式必须显式记录。
10. **不再新增 Core、Context、Reader 等平级产品名称。**

## 当前可运行能力

统一 Python 实现位于：

```text
src/me_system/
```

已经支持：

- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- ME-Brain、ME-Who 与 Bridge namespace；
- 时间、权威级别、确认状态、置信度与敏感度；
- 内存 Store 与 PostgreSQL `SqlAlchemyGraphStore`；
- Alembic 迁移和 psycopg 3；
- 项目快照、决策链、子图和证据查询；
- 任务相关 ME-Who 规则筛选；
- 确定性 Project Resolver；
- Hermes 六工具只读 stdio MCP；
- 项目 allowlist、固定 ME-Who 用户和范围保护；
- `SourceRecord` 与 `EvidenceFragment`；
- `IngestionRun`、coverage、quality 与失败摘要；
- Source 与 Candidate 幂等冲突检测；
- 持久化 Candidate Queue 与追加式 ReviewEvent；
- Candidate 批准/驳回与权威节点/边写入的单事务闭环；
- Python 3.11 / 3.12、PostgreSQL 16 和真实 stdio MCP CI。

## 安装与 Fixture 验收

从仓库根目录执行：

```bash
python -m pip install -e '.[dev]'

me-system load-fixture \
  --fixture examples/graph/lighting-platform.json

me-system project-snapshot \
  --fixture examples/graph/lighting-platform.json \
  --project-id brain:project:lighting-platform

me-system trace-decision \
  --fixture examples/graph/lighting-platform.json \
  --decision-id brain:decision:radiance-primary

me-system task-profile \
  --fixture examples/graph/lighting-platform.json \
  --user-id who:user:master \
  --project-id brain:project:lighting-platform \
  --task-type implementation
```

## PostgreSQL 持久化

```bash
export ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph:你的密码@127.0.0.1:5432/me_graph'

me-system db-upgrade
me-system import-fixture \
  --fixture examples/graph/lighting-platform.json
me-system project-snapshot \
  --project-id brain:project:lighting-platform
```

实现与部署说明见 [`docs/implementation.md`](docs/implementation.md)。

## 输入、候选与人工治理 CLI

这些命令属于 ME-Brain / ME-Who 的内部构建管线，不向 Hermes MCP 暴露：

```text
source-register
source-show
candidate-submit
candidate-list
candidate-approve
candidate-reject
```

### 1. 登记来源和证据片段

`source.json`：

```json
{
  "source": {
    "schema_version": "source-record/0.1",
    "source_id": "source:conversation:001",
    "source_type": "agent_conversation",
    "external_system": "hermes",
    "external_id": "conversation-001",
    "idempotency_key": "hermes:conversation-001:export-1",
    "content_ref": "file:///data/conversation-001.json",
    "content_sha256": "<64位sha256>",
    "media_type": "application/json",
    "occurred_at": "2026-07-23T10:00:00Z",
    "ingested_at": "2026-07-23T12:00:00Z",
    "sensitivity": "personal_private",
    "metadata": {}
  },
  "fragments": []
}
```

```bash
me-system source-register --json source.json
me-system source-show --source-id source:conversation:001
```

### 2. 提交、查看和审核 Candidate

```bash
me-system candidate-submit --json candidate.json

me-system candidate-list \
  --target-graph me_brain \
  --source-id source:conversation:001

me-system candidate-approve \
  --change-id candidate:decision:001 \
  --reviewer-id who:user:master \
  --reason '用户明确确认'

me-system candidate-reject \
  --change-id candidate:preference:001 \
  --reviewer-id who:user:master \
  --reason '证据不足，暂不形成稳定事实'
```

审核操作会在一个数据库事务中完成：

```text
锁定 Candidate
→ 验证仍为 pending
→ 重建 GraphNode / GraphEdge
→ 写权威对象和证据
→ 更新 Candidate 状态
→ 追加 ReviewEvent
→ commit
```

任一步失败都会整笔回滚。

## Hermes 只读 MCP

Hermes 仍然只能看到六个只读工具：

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

## 当前仓库结构

```text
me-system/
├── src/me_system/
│   ├── brain/          # ME-Brain 领域
│   ├── who/            # ME-Who 领域
│   ├── bridge/         # 显式跨图关系，不是第三个产品
│   ├── evidence/       # 来源与证据契约
│   ├── ingestion/      # 摄取状态、Candidate 和审核
│   ├── persistence/    # PostgreSQL、迁移和 Repository
│   ├── hermes/         # MCP 适配
│   ├── contracts.py
│   ├── query.py
│   └── store.py
├── tests/
├── schemas/
├── migrations/
├── examples/
├── deploy/
└── docs/
```

## 文档导航

- [当前架构状态](docs/architecture-status.md)
- [ADR-0004：双权威图谱](docs/adr/ADR-0004-two-canonical-graphs.md)
- [ADR-0005：只保留 ME-Brain 与 ME-Who](docs/adr/ADR-0005-single-graph-kernel.md)
- [Codebase-Memory 架构评审](docs/competitors/codebase-memory-architecture-review.md)
- [Graphify 架构评审](docs/competitors/graphify-review.md)
- [双图谱契约](docs/specs/dual-graph-contract-v0.1.md)
- [ME-Brain 本体](docs/specs/me-brain-ontology-v0.1.md)
- [ME-Who 本体](docs/specs/me-who-ontology-v0.1.md)
- [推荐开发路径](docs/roadmap/recommended-development-path.md)

## 下一步

```text
1. 增量 Manifest 与 Adapter versioning
2. Agent Conversation Adapter
3. derivation_kind：EXPLICIT / RULE_DERIVED / MODEL_INFERRED / AMBIGUOUS
4. 路径式 MCP 查询与影响分析
5. Graph Report 与 Benchmark
6. Markdown / Git / Zotero Adapter
7. 社区与中心性分析
```

在输入候选闭环和 Benchmark 稳定前，不优先开发大型图谱前端、复杂多 Agent Handoff、数字人格或任意图查询语言。
