# ADR-0005：一个 ME-System，两个图谱领域

- 状态：Accepted
- 日期：2026-07-23
- 取代：所有把 `me-graph-core`、ME-Context、ME-Reader 或其他内部模块描述为第三个产品核心的表达

## 决策

ME-System 是唯一产品与唯一运行主体。其内部只有两个权威图谱领域：

```text
ME-System
├── ME-Brain Graph
└── ME-Who Graph
```

- **ME-Brain**：项目、需求、决策、任务、问题、成果、实验和证据。
- **ME-Who**：用户事实、角色、能力、目标、偏好、协作规则和证据。

以下能力均是 ME-System 内部模块，不是第三个产品或第三张核心图谱：

- Source / Evidence；
- Ingestion / Candidate；
- Review；
- Persistence；
- Query；
- MCP / Hermes Adapter；
- Bridge relations。

## 代码命名

Python 分发包、导入包和主要命令统一使用 `me_system` / `me-system`：

```text
pyproject.toml
src/me_system/
tests/
migrations/
schemas/
```

不再继续使用：

```text
services/me-graph-core/
me_graph_core
me-graph
me-graph-mcp
```

替换为：

```text
me_system
me-system
me-system-mcp
```

## 内部模块边界

```text
src/me_system/
├── brain/                  # ME-Brain 领域规则与查询
├── who/                    # ME-Who 领域规则与查询
├── graph/                  # 两领域共享的节点、边、遍历契约
├── evidence/               # 来源和证据片段
├── ingestion/              # 索引运行、候选和审核
├── persistence/            # PostgreSQL 与迁移映射
└── adapters/
    └── hermes/             # MCP 适配，不定义图谱 Schema
```

共享代码可以存在，但不得重新命名为一个平级 Core 产品。

## 运行逻辑

ME-Brain 与 ME-Who 采用相同的 Codebase-Memory / Graphify 式运行模式：

```text
领域资料
→ 确定性或受控语义抽取
→ 候选节点与关系
→ 审核进入权威图谱
→ Agent 通过类型化 MCP 查询任务相关子图
→ 必要时下钻原始证据
```

## 后果

### 正面

- 产品边界稳定，不再产生第三个“核心”；
- 安装、部署、测试和版本只围绕一个包；
- ME-Brain 与 ME-Who 可以共享基础能力而不混淆领域事实；
- Source、Candidate 和 MCP 的定位变得明确；
- 后续可以参考 Graphify、Codebase-Memory，而不会把参考组件变成产品线。

### 代价

- 需要一次性迁移现有包路径、导入名、CLI、CI 和文档；
- 早期用户需要更新命令和 Hermes 配置；
- 迁移 PR 较大，但当前尚未正式发布，适合现在完成。

## 不允许的回退

- 新增 `ME-*-Core` 作为平级产品；
- 让 MCP Adapter 反向定义图谱模型；
- 把 Evidence、Candidate 或 Source Ledger 拆成独立权威数据库；
- 将 ME-Brain 与 ME-Who 合并为无权限边界的单一平面图；
- 将自动推断直接写入权威图谱。