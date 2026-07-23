# Unified ME-System Package Design

> 状态：已批准方向的实施设计  
> 日期：2026-07-23  
> 范围：消除 `me-graph-core` 第三核心错觉，统一包、命令、目录和文档；不改变现有图谱业务语义

## 1. 目标

将当前：

```text
services/me-graph-core/
└── src/me_graph_core/
```

迁移为仓库根目录的单一 Python 项目：

```text
pyproject.toml
src/me_system/
tests/
schemas/
migrations/
alembic.ini
```

对外只存在：

```text
ME-System
├── ME-Brain
└── ME-Who
```

`graph`、`evidence`、`ingestion`、`persistence`、`query` 和 `adapters` 均为内部模块。

## 2. 命名规则

### 2.1 产品和领域

保留：

- ME-System；
- ME-Brain；
- ME-Who；
- Bridge（仅表示跨领域关系命名空间）。

不再使用：

- ME-Graph Core；
- ME-Core；
- ME-Context；
- ME-Reader；
- Source Core；
- Candidate Core。

### 2.2 Python 与 CLI

```text
Distribution: me-system
Import:       me_system
CLI:          me-system
MCP:          me-system-mcp
```

当前项目未正式发布，不保留 `me_graph_core`、`me-graph`、`me-graph-mcp` 兼容别名，避免早期历史名称永久存在。

## 3. 目录结构

本次迁移采用最小行为变化方案：先统一包和目录，不同时拆分所有现有模块。

```text
me-system/
├── pyproject.toml
├── alembic.ini
├── migrations/
├── schemas/
├── src/
│   └── me_system/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── contracts.py
│       ├── errors.py
│       ├── fixtures.py
│       ├── query.py
│       ├── review.py
│       ├── store.py
│       ├── persistence/
│       └── adapters/
│           └── hermes/
├── tests/
├── examples/
├── deploy/
└── docs/
```

后续在真实领域逻辑增长时再逐步拆出：

```text
src/me_system/brain/
src/me_system/who/
src/me_system/evidence/
src/me_system/ingestion/
```

禁止仅为了目录好看创建无行为的空层级。

## 4. 模块迁移映射

```text
services/me-graph-core/src/me_graph_core/*
→ src/me_system/*

services/me-graph-core/src/me_graph_core/hermes/*
→ src/me_system/adapters/hermes/*

services/me-graph-core/src/me_graph_core/persistence/*
→ src/me_system/persistence/*

services/me-graph-core/tests/*
→ tests/*

services/me-graph-core/schemas/*
→ schemas/*

services/me-graph-core/migrations/*
→ migrations/*

services/me-graph-core/pyproject.toml
→ pyproject.toml

services/me-graph-core/alembic.ini
→ alembic.ini
```

## 5. 行为兼容要求

迁移前后以下行为必须完全一致：

- GraphNode / GraphEdge / EvidenceRef 序列化；
- ME-Brain、ME-Who、Bridge 命名空间约束；
- InMemoryGraphStore；
- PostgreSQL SqlAlchemyGraphStore；
- Alembic 从空库升级；
- Fixture 导入；
- 项目快照、决策链、子图、证据和任务画像；
- Hermes 项目解析、allowlist、成员范围保护；
- 六个只读 MCP 工具；
- stdio MCP PostgreSQL E2E。

## 6. 配置和命令变更

### 6.1 安装

```bash
python -m pip install -e '.[dev]'
```

从仓库根目录执行。

### 6.2 CLI

```bash
me-system db-upgrade
me-system import-fixture --fixture examples/graph/lighting-platform.json
me-system project-snapshot --project-id brain:project:lighting-platform
```

### 6.3 MCP

Hermes 配置改为：

```yaml
command: "me-system-mcp"
```

环境变量保持不变，避免把目录重构扩大成配置协议重构。

## 7. Alembic 路径

`src/me_system/persistence/migrations.py` 从包位置解析仓库根目录：

```text
repo_root / alembic.ini
repo_root / migrations
repo_root / src
```

CI 必须从仓库根目录安装和执行，验证迁移资源在当前源码布局下可用。

## 8. CI

工作流不再设置：

```text
working-directory: services/me-graph-core
```

而是在仓库根执行：

```bash
python -m pip install -q -e '.[dev]'
pytest -q
python -m compileall -q src
```

继续保留：

- Python 3.11；
- Python 3.12；
- PostgreSQL 16；
- stdio MCP Client E2E。

## 9. Graphify 借鉴在本次迁移中的落点

本次只吸收架构纪律，不同时增加新业务功能：

- 一个可安装包；
- CLI、MCP 和索引代码属于同一产品；
- 单职责模块；
- Agent 通过查询层访问图谱；
- 测试按模块组织；
- 输出和配置路径明确。

以下能力进入后续切片：

- EXPLICIT / RULE_DERIVED / MODEL_INFERRED / AMBIGUOUS；
- shortest path / explain path；
- 增量 manifest；
- Graph report；
- Benchmark harness；
- community / impact analysis。

## 10. 文档调整

所有活动文档必须做到：

- 不把 `me-graph-core` 描述成组件或产品；
- 用“ME-System Python package”描述实现；
- 只把 ME-Brain 和 ME-Who列为图谱领域；
- Source Ledger 与 Candidate 设计路径使用 `src/me_system/...`；
- README 从仓库根提供安装和运行命令；
- Graphify 评审加入竞品导航与吸收矩阵。

## 11. 非目标

本次不实现：

- Source / Candidate 数据库迁移；
- 新的图谱字段；
- 新 MCP 工具；
- HTTP MCP；
- 前端；
- 图数据库替换；
- ME-Brain / ME-Who Schema 扩展。

## 12. 验收标准

- 仓库中不存在活动路径 `services/me-graph-core`；
- Python 代码不再导入 `me_graph_core`；
- Console scripts 为 `me-system`、`me-system-mcp`；
- README、ADR、架构状态和路线只表达一个 ME-System；
- Python 3.11 / 3.12 单元测试通过；
- PostgreSQL 16 GraphStore E2E 通过；
- stdio MCP E2E 通过；
- PR 中无旧包路径残留，历史 Git 记录除外。