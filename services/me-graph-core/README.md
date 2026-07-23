# ME-Graph Core

ME-Graph Core 是 ME-System 双权威图谱的首个可运行基础。它提供统一图谱契约、内存与 PostgreSQL 存储、候选审核、类型化查询和 Hermes 只读 MCP。

## 能力

- ME-Brain、ME-Who 和 Bridge 命名空间；
- 带来源、时间、敏感度和权威状态的节点与边；
- `InMemoryGraphStore` 与 `SqlAlchemyGraphStore`；
- PostgreSQL + psycopg 3 生产存储；
- Alembic 数据库迁移；
- 候选变更批准和驳回；
- 项目当前快照、决策替代链、子图和证据查询；
- 任务相关 ME-Who 查询；
- 确定性 Project Resolver；
- 六工具 Hermes stdio MCP；
- JSON Schema 与 Python 契约双重校验。

## 安装

```bash
cd services/me-graph-core
python -m pip install -e '.[dev]'
```

MCP Python SDK 固定在稳定 v1 范围：

```text
mcp>=1.27,<2
```

## Fixture 模式

无需数据库即可验证图谱语义：

```bash
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

## PostgreSQL 模式

### 1. 启动 PostgreSQL

从仓库根目录：

```bash
cp deploy/postgres/.env.example deploy/postgres/.env
# 修改 deploy/postgres/.env 中的密码

docker compose \
  --env-file deploy/postgres/.env \
  -f deploy/postgres/docker-compose.example.yml \
  up -d
```

### 2. 配置写入连接

迁移和图谱导入使用具备写权限的账号，连接必须使用 psycopg 3 方言：

```bash
export ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph:你的密码@127.0.0.1:5432/me_graph'
```

不要把真实连接字符串提交到仓库。

### 3. 迁移和导入

```bash
cd services/me-graph-core

me-graph db-upgrade

me-graph import-fixture \
  --fixture ../../examples/graph/lighting-platform.json
```

重复导入同一权威对象会明确失败，不会静默覆盖数据。

### 4. 从持久化图谱查询

```bash
me-graph project-snapshot \
  --project-id brain:project:lighting-platform

me-graph trace-decision \
  --decision-id brain:decision:radiance-primary

me-graph task-profile \
  --user-id who:user:master \
  --project-id brain:project:lighting-platform \
  --task-type implementation
```

命令优先使用显式 `--database-url`，否则读取 `ME_GRAPH_DATABASE_URL`。

## Hermes stdio MCP

### 服务端环境

```text
ME_GRAPH_DATABASE_URL          必填，建议使用只读 PostgreSQL 账号
ME_GRAPH_HERMES_USER_ID        必填，例如 who:user:master
ME_GRAPH_ALLOWED_PROJECT_IDS   必填，逗号分隔 canonical Project ID 或显式 *
ME_GRAPH_MAX_SUBGRAPH_DEPTH    可选，默认 2，最大 3
ME_GRAPH_MCP_LOG_LEVEL         可选，默认 WARNING
```

启动：

```bash
ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph_reader:密码@127.0.0.1:5432/me_graph' \
ME_GRAPH_HERMES_USER_ID='who:user:master' \
ME_GRAPH_ALLOWED_PROJECT_IDS='brain:project:lighting-platform' \
me-graph-mcp
```

这是 stdio 协议进程，不提供普通交互式终端。stdout 仅用于 MCP framing，诊断信息写 stderr。

### 工具

```text
brain_resolve_project
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
```

特性：

- canonical ID、label、alias、工作目录和外部 ID 精确解析；
- 不使用向量、编辑距离或 LLM 猜项目；
- 工具参数不能切换 ME-Who 用户；
- 项目成员由显式 `HAS_*` 关系确定；
- 跨项目任意语义边不能扩大权限；
- 历史决策只在没有被其他项目明确拥有时继承范围；
- Bridge 与无关 ME-Who 对象不会进入 ME-Brain 工具结果；
- 无写入、审核、SQL 或任意 Cypher 工具。

Hermes 配置见 [`../../integrations/hermes/README.md`](../../integrations/hermes/README.md)。

## SQLite 验收模式

SQLite 只用于本地自动测试和快速验收，不是生产数据库。必须显式添加 `--allow-test-database`：

```bash
DB='sqlite+pysqlite:////tmp/me-graph-acceptance.db'

me-graph db-upgrade \
  --database-url "$DB" \
  --allow-test-database

me-graph import-fixture \
  --database-url "$DB" \
  --allow-test-database \
  --fixture ../../examples/graph/lighting-platform.json

me-graph project-snapshot \
  --database-url "$DB" \
  --allow-test-database \
  --project-id brain:project:lighting-platform
```

## 测试

```bash
pytest -q
python -m compileall -q src
```

真实 PostgreSQL 集成测试需要一个可创建和删除测试 Schema 的账号：

```bash
ME_GRAPH_TEST_POSTGRES_URL='postgresql+psycopg://...' \
  pytest tests/test_postgres_integration.py \
         tests/test_mcp_stdio.py -q
```

测试会创建随机 Schema，执行迁移、导入图谱、启动真实 stdio MCP 客户端，并在结束后执行 `DROP SCHEMA ... CASCADE`。未配置环境变量时，这些测试明确显示为 `SKIPPED`。

## 数据库结构

```text
graph_objects
├── 全局唯一节点/边 ID
├── ME-Brain / ME-Who / Bridge 命名空间
├── 时间、权威、确认与敏感度字段
└── JSON 属性

graph_evidence_refs
├── 对象证据引用
├── 原始顺序 ordinal
└── SourceAnchor
```

数据库行读取后仍通过 `GraphNode.from_dict()` 或 `GraphEdge.from_dict()` 重建，数据库不能绕过领域契约。

## 当前边界

- MCP 当前仅支持本地 stdio，尚未提供生产 HTTP/OAuth；
- 尚未实现 Agent 字段级权限过滤；
- 尚未自动从文档、对话和 Git 生成候选；
- 未批准的 Candidate 尚未跨重启持久化；
- 候选变更当前只支持新增节点和新增边；
- 项目解析只支持确定性精确匹配；
- SQL 查询存在可接受的 P0 N+1 证据读取，后续在真实数据规模下优化。

下一步是使用真实 Hermes 运行项目恢复 Benchmark，并接入 Agent Conversation / Markdown / Git Candidate Adapter。
