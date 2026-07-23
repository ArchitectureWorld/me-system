# PostgreSQL GraphStore Design

> 状态：已批准路线下的实现设计  
> 日期：2026-07-23  
> 范围：ME-System Phase 1，持久化双权威图谱并保持现有查询接口不变

## 1. 目标

将当前 `InMemoryGraphStore` 的权威节点、权威关系和证据引用持久化到 PostgreSQL，使 ME-Brain / ME-Who 图谱能够跨进程和重启保存，同时让现有 `GraphQueryService`、夹具加载器和候选审核逻辑继续通过同一个 `GraphStore` 协议工作。

第一阶段完成后，应支持：

- 将 `lighting-platform` 示例图导入数据库；
- 从数据库恢复项目当前快照；
- 追踪决策替代链；
- 查询任务、问题、关系和证据；
- 保持 ME-Brain、ME-Who、Bridge 命名空间约束；
- 通过 Alembic 管理数据库迁移；
- 在 Linux / NAS 的 PostgreSQL 部署中运行。

## 2. 非目标

本切片暂不实现：

- Hermes MCP Server；
- 字段级 Agent 权限过滤；
- 向量检索与全文检索；
- 自动从文档、对话或 Git 生成候选图谱；
- pending candidate 的跨重启持久化；
- 审核 Web 界面；
- 多数据库或分布式数据库；
- PostgreSQL 图扩展、Cypher 或 Neo4j 兼容层。

`CandidateReviewService` 仍可把批准结果写入 PostgreSQL GraphStore，但未批准候选在本切片中仍由进程内服务管理；候选持久化属于后续治理切片。

## 3. 技术选择

### 3.1 推荐方案

采用：

```text
SQLAlchemy 2.0
+ Alembic
+ PostgreSQL
+ psycopg 3
```

生产连接显式使用：

```text
postgresql+psycopg://...
```

采用同步 Engine 与短生命周期 Session，不在本阶段引入异步数据库层。

### 3.2 选择理由

- 现有领域对象已经具备稳定的 `to_dict()` / `from_dict()` 契约，适合通过 Repository 映射到数据库；
- SQLAlchemy 能让 SQLite 作为快速行为测试后端，而生产环境仍限定为 PostgreSQL；
- Alembic 提供明确的迁移历史和 Schema 漂移检查；
- 同步实现更容易与当前 CLI、夹具和 MCP 预备层集成；
- 数据库选择仍隐藏在 `GraphStore` 接口之后。

### 3.3 未采用方案

#### 手写 psycopg SQL

依赖更少，但迁移、测试替身、模型一致性和后续 Schema 演化成本更高。

#### 单表 JSONB Blob Store

开发快，但会弱化端点外键、图谱过滤、边方向索引和数据库约束，不适合作为权威图谱底座。

#### 直接引入图数据库

当前真实多跳查询规模尚未证明需要独立图数据库；优先稳定图谱契约和持久化语义。

## 4. 组件边界

```text
GraphQueryService
        │
        ▼
GraphStore Protocol
        │
        ├── InMemoryGraphStore
        └── SqlAlchemyGraphStore
                │
                ├── PostgreSQL production engine
                └── SQLite test engine
```

新增组件：

```text
persistence/database.py
  Engine、Session factory、数据库 URL 校验

persistence/models.py
  SQLAlchemy Table / ORM 映射

persistence/store.py
  SqlAlchemyGraphStore，实现现有 GraphStore

persistence/migrations/
  Alembic 环境与版本文件

persistence/testing.py
  SQLite 测试 Engine 与行为契约辅助
```

生产入口：

```python
create_postgres_graph_store(database_url: str) -> GraphStore
```

测试入口：

```python
create_sqlite_test_store() -> GraphStore
```

## 5. 数据模型

### 5.1 `graph_objects`

使用一个公共对象表保证节点和边在全局 ID 空间中唯一。

字段：

```text
id                    text primary key
object_kind           node | edge
graph_namespace       me_brain | me_who | bridge
object_type            text
label                  nullable text
from_id                nullable FK graph_objects.id
to_id                  nullable FK graph_objects.id
properties             JSON / PostgreSQL JSONB
authority              text
confirmation_status    text
temporal_status        nullable text
confidence             nullable numeric
valid_from             nullable timestamptz
valid_to               nullable timestamptz
sensitivity            text
created_at             timestamptz
```

约束：

- `node` 不允许使用 `bridge` 命名空间；
- `node` 必须有 `label` 和 `temporal_status`，且 `from_id`、`to_id`、`confidence` 为空；
- `edge` 必须有 `from_id`、`to_id` 和 `confidence`，且端点不同；
- 节点、边共用一个主键空间；
- 时间、权威和敏感字段仍通过领域对象再次校验。

跨图关系和 Bridge 规则继续由 `GraphStore` 在同一事务中验证。数据库外键只负责端点存在性。

### 5.2 `graph_evidence_refs`

字段：

```text
id                    bigint primary key
object_id             FK graph_objects.id on delete cascade
ordinal               integer
source_id             text
document_id           nullable text
version_id            nullable text
content_fragment_id   nullable text
source_anchor          JSON / PostgreSQL JSONB
```

约束：

```text
unique(object_id, ordinal)
```

证据按照原始 tuple 顺序写入，读取时按 `ordinal` 恢复，确保序列化结果稳定。

### 5.3 索引

第一版建立：

```text
graph_objects(graph_namespace, object_kind, object_type)
graph_objects(from_id)
graph_objects(to_id)
graph_objects(temporal_status, valid_to)
graph_evidence_refs(object_id)
graph_evidence_refs(source_id)
```

## 6. Repository 行为

`SqlAlchemyGraphStore` 必须与 `InMemoryGraphStore` 保持同样的可观察行为：

- 重复 ID 抛出 `DuplicateGraphObjectError`；
- 不存在对象抛出 `GraphObjectNotFoundError`；
- 非 Bridge 跨图边抛出 `GraphNamespaceError`；
- Bridge 必须连接两个不同权威图谱；
- `list_nodes()`、`list_edges()`、`neighbors()` 按 ID 稳定排序；
- `edge_types` 与 `direction` 过滤语义保持不变；
- 数据库行必须通过 `GraphNode.from_dict()` 或 `GraphEdge.from_dict()` 重建，避免绕过领域校验。

## 7. 事务

每个公开写方法使用短事务：

```text
add_node
  begin
  检查 ID
  写 graph_objects
  写 evidence refs
  commit

add_edge
  begin
  锁定并读取两个端点
  验证命名空间
  写 graph_objects
  写 evidence refs
  commit
```

发生任何异常时整笔回滚，不允许出现“对象已写入但证据缺失”的状态。

读取方法使用独立 Session，函数结束即释放连接。

## 8. 迁移

在 `services/me-graph-core` 内加入 Alembic：

```text
alembic.ini
migrations/env.py
migrations/script.py.mako
migrations/versions/0001_create_graph_store.py
```

初始迁移负责建立：

- `graph_objects`；
- `graph_evidence_refs`；
- 约束；
- 外键；
- 索引。

CLI 新增：

```text
me-graph db-upgrade --database-url <url>
me-graph import-fixture --database-url <url> --fixture <path>
```

现有查询命令增加互斥数据源：

```text
--fixture <path>
或
--database-url <url>
```

未提供数据源或同时提供两个数据源时返回结构化错误。

## 9. 配置与部署

生产 URL 从以下顺序读取：

1. CLI `--database-url`；
2. 环境变量 `ME_GRAPH_DATABASE_URL`。

真实凭据不写入仓库。

新增示例：

```text
deploy/postgres/docker-compose.example.yml
.env.example
```

示例仅提供变量名，不提供真实密码。

## 10. 错误处理

新增：

```text
GraphStoreConfigurationError
GraphStoreUnavailableError
GraphMigrationError
```

数据库异常映射：

- 唯一约束冲突 → `DuplicateGraphObjectError`；
- 端点不存在 → `GraphObjectNotFoundError`；
- URL 非 PostgreSQL → `GraphStoreConfigurationError`；
- 无法连接或事务失败 → `GraphStoreUnavailableError`；
- 领域约束失败继续使用现有 `ContractValidationError` / `GraphNamespaceError`。

错误信息不得包含数据库密码。

## 11. 测试策略

### 11.1 行为契约测试

把现有 Store 行为测试抽成工厂化契约，对以下实现运行相同断言：

```text
InMemoryGraphStore
SqlAlchemyGraphStore(SQLite in-memory)
```

覆盖：

- 两个图谱隔离；
- 重复 ID；
- Bridge；
- 非法跨图边；
- 邻接方向与类型过滤；
- 证据顺序；
- JSON properties 往返；
- 时间和枚举往返；
- 事务回滚。

### 11.2 迁移测试

- Alembic 能从空库升级到 head；
- Metadata 与初始迁移没有未提交差异；
- SQLite 测试 Schema 可以创建和销毁。

### 11.3 PostgreSQL 集成测试

当设置 `ME_GRAPH_TEST_POSTGRES_URL` 时执行：

- 迁移真实 PostgreSQL；
- 导入 `lighting-platform`；
- 运行项目快照、决策链和证据查询；
- 清理独立测试 Schema。

没有提供 URL 时，集成测试明确标记为 skip，不伪装为已验证。

## 12. 验收标准

- 现有 35 项测试保持通过；
- Store 契约在内存和 SQLAlchemy 测试实现上均通过；
- `lighting-platform` 可以写入持久化 Store 并读取相同 GraphSlice；
- 重建 `GraphQueryService` 后查询结果与内存夹具一致；
- 进程重新创建 Store 后数据仍可读取；
- Alembic 初始迁移可重复、安全执行；
- 数据库 URL 和错误输出不泄露密码；
- README 提供 NAS / Linux 的最小启动和验收步骤。

## 13. 后续切片

本切片通过后，按顺序进入：

1. 项目名称与工作目录 ID Resolve；
2. Hermes 只读 MCP Server；
3. Conversation / Markdown / Git Adapter；
4. pending candidate 与审核日志持久化；
5. 字段级权限过滤；
6. Pi Extension。
