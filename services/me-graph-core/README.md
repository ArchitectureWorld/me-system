# ME-Graph Core

ME-Graph Core 是 ME-System 双权威图谱的首个可运行基础。它提供统一图谱契约、内存实现、PostgreSQL 持久化实现、候选审核和类型化查询。

## 能力

- ME-Brain、ME-Who 和 Bridge 命名空间；
- 带来源、时间、敏感度和权威状态的节点与边；
- `InMemoryGraphStore` 与 `SqlAlchemyGraphStore`；
- PostgreSQL + psycopg 3 生产存储；
- Alembic 数据库迁移；
- 候选变更批准和驳回；
- 项目当前快照；
- 决策替代链；
- 子图展开；
- 证据查询；
- 任务相关 ME-Who 查询；
- JSON Schema 与 Python 契约双重校验。

## 安装

```bash
cd services/me-graph-core
python -m pip install -e '.[dev]'
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

### 2. 配置连接

生产连接必须使用 psycopg 3 方言：

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

真实 PostgreSQL 集成测试需要一个可销毁测试库账号：

```bash
ME_GRAPH_TEST_POSTGRES_URL='postgresql+psycopg://...' \
  pytest tests/test_postgres_integration.py -q
```

测试会创建随机 Schema，完成后执行 `DROP SCHEMA ... CASCADE`。未配置该环境变量时，该测试明确显示为 `SKIPPED`。

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

- 尚未提供生产 MCP Server；
- 尚未实现 Agent 字段级权限过滤；
- 尚未自动从文档、对话和 Git 生成候选；
- 未批准的 Candidate 仍由进程内服务管理，尚未跨重启持久化；
- 候选变更当前只支持新增节点和新增边；
- SQL 查询存在可接受的 P0 N+1 证据读取，后续在真实数据规模下优化。

这些限制是刻意保留的。当前目标是先稳定 PostgreSQL 持久化与现有图谱查询语义，下一步再接入 Hermes 只读 MCP。
