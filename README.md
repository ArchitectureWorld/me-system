# ME-System

ME-System 是面向 AI Agent 的统一结构化图谱系统，只有两个权威图谱领域：

```text
ME-System
├── ME-Brain   项目、科研、设计与开发图谱
└── ME-Who     用户事实、能力、偏好与协作图谱
```

**没有第三个产品或第三个 Core。** Evidence、Ingestion、Candidate Review、Persistence、Query、Bridge、CLI 与 MCP 都只是 ME-System 的内部实现职责。

## 小白一键体验

只需要安装并打开 **Docker Desktop**，不需要安装 Python、PostgreSQL 或配置环境变量。

### Windows

下载并解压仓库，双击：

```text
体验.bat
```

### macOS

下载并解压仓库，双击：

```text
体验.command
```

首次若被系统拦截，右键该文件选择“打开”。

### Linux

在仓库目录运行：

```bash
./体验.sh
```

启动文件会自动：

```text
检查 Docker
→ 启动专用 PostgreSQL 16
→ 执行数据库迁移
→ 导入示例图谱
→ 保存 Source / Evidence / IngestionRun
→ 提交并批准 ME-Brain / ME-Who Candidate
→ 执行图谱查询
→ 执行真实 stdio MCP 验收
→ 打开浏览器结果页
```

验收页：

```text
http://localhost:8765
```

页面顶部显示以下内容即为通过：

```text
全部通过
ME-System 一键体验验收成功
```

停止体验：

```text
Windows        双击 停止体验.bat
macOS / Linux  运行 ./停止体验.sh
```

完整说明与排错见 [`docs/experience.md`](docs/experience.md)。

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

## 稳定原则

1. 只有 ME-Brain 和 ME-Who 两个权威图谱领域；
2. 一个 PostgreSQL 权威数据源，通过 namespace 与权限隔离；
3. Agent 默认读取 GraphSlice，不反复扫描全部来源；
4. 自动解析和 Agent 只能提交 Candidate，不能直接修改权威图谱；
5. 高价值节点和关系必须能回到 EvidenceFragment；
6. MCP 是薄适配，只调用应用与查询服务；
7. ME-Brain 查询必须显式限定项目；
8. ME-Who 只返回当前任务真正需要的最小信息；
9. 覆盖率、跳过项、失败、歧义和推导方式必须可见；
10. 不新增 Core、Context、Reader 等平级产品名称。

## 已实现

- `GraphNode`、`GraphEdge`、`EvidenceRef`、`CandidateGraphChange`、`GraphSlice`；
- ME-Brain、ME-Who 与 Bridge namespace；
- 时间、权威级别、确认状态、置信度与敏感度；
- 内存 Store 与 PostgreSQL `SqlAlchemyGraphStore`；
- Alembic 与 psycopg 3；
- 项目快照、决策链、子图、证据与任务画像查询；
- 确定性 Project Resolver；
- Hermes 六工具只读 stdio MCP；
- Project allowlist 与固定 ME-Who 用户；
- `SourceRecord` 与 `EvidenceFragment`；
- `IngestionRun`、coverage、quality 与失败摘要；
- Source 与 Candidate 幂等冲突检测；
- 持久化 Candidate Queue 与追加式 ReviewEvent；
- Candidate 审核与权威节点/边写入的单事务闭环；
- Python 3.11 / 3.12、PostgreSQL 16 与真实 stdio MCP CI。

## 开发者安装

从仓库根目录执行：

```bash
python -m pip install -e '.[dev]'
```

Fixture 查询：

```bash
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

## PostgreSQL

```bash
export ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_system:密码@127.0.0.1:5432/me_system'

me-system db-upgrade
me-system import-fixture \
  --fixture examples/graph/lighting-platform.json
me-system project-snapshot \
  --project-id brain:project:lighting-platform
```

部署说明见 [`docs/implementation.md`](docs/implementation.md)。

## 输入与治理 CLI

这些命令属于 ME-Brain / ME-Who 的内部构建管线，不向 Agent MCP 暴露：

```text
source-register
source-show
candidate-submit
candidate-list
candidate-approve
candidate-reject
```

审核事务：

```text
锁定 Candidate
→ 验证 pending
→ 重建 GraphNode / GraphEdge
→ 写权威对象与证据
→ 更新 Candidate 状态
→ 追加 ReviewEvent
→ commit
```

任一步失败都会整笔回滚。

## Hermes 只读 MCP

Hermes 只能看到六个工具：

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
ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph_reader:密码@127.0.0.1:5432/me_system' \
ME_GRAPH_HERMES_USER_ID='who:user:master' \
ME_GRAPH_ALLOWED_PROJECT_IDS='brain:project:lighting-platform' \
me-system-mcp
```

Hermes 配置见 [`integrations/hermes/README.md`](integrations/hermes/README.md)。

## 仓库结构

```text
me-system/
├── src/me_system/
│   ├── brain/          # ME-Brain 领域
│   ├── who/            # ME-Who 领域
│   ├── bridge/         # 显式跨图关系
│   ├── evidence/       # 来源与证据
│   ├── ingestion/      # 摄取、Candidate 与审核
│   ├── persistence/    # PostgreSQL、迁移与 Repository
│   ├── experience/     # 小白一键体验验收
│   └── hermes/         # 只读 MCP
├── deploy/experience/
├── tests/
├── schemas/
├── migrations/
├── examples/
└── docs/
```

## 参考方法

ME-Brain 与 ME-Who 共同吸收 Codebase-Memory 与 Graphify 的有效方法：

- persistent graph first；
- multi-stage indexing；
- typed MCP；
- compact-first；
- path-based explanation；
- content hash、Adapter version 与 Manifest 增量索引；
- CLI / MCP 复用同一应用服务；
- status / coverage / ambiguity；
- Agent 负责理解任务，未经审核的模型输出不是权威事实。

不照搬任意 SQL/Cypher、模型推断直写、单一 `graph.json` 权威库、无权限边界平面图或完整 ME-Who Git 导出。

## 文档

- [小白一键体验](docs/experience.md)
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
3. derivation_kind
4. 路径式 MCP 查询与影响分析
5. Graph Report 与 Benchmark
6. Markdown / Git / Zotero Adapter
7. 社区与中心性分析
```

在输入候选闭环和 Benchmark 稳定前，不优先开发大型图谱前端、复杂多 Agent Handoff、数字人格或任意图查询语言。
