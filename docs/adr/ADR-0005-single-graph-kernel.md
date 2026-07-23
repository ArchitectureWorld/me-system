# ADR-0005：一个 ME-System，仅有 ME-Brain 与 ME-Who 两个图谱领域

- 状态：Accepted
- 日期：2026-07-23
- 上位决策：ADR-0004 双权威图谱
- 参考：Codebase-Memory、Graphify

## 决策

ME-System 是唯一产品和唯一运行主体。其内部只有两个权威图谱领域：

```text
ME-System
├── ME-Brain
└── ME-Who
```

- **ME-Brain**：科研、设计、开发等客观项目的结构化图谱；
- **ME-Who**：Agent 为理解和服务用户所需的结构化图谱。

不再定义第三个产品、第三张业务图谱或第三个“Core”品牌。

以下能力均为 ME-System 内部职责，不拥有平级产品身份：

- Source / Evidence；
- Ingestion / Candidate；
- Review；
- Persistence；
- Query；
- Bridge；
- MCP / Hermes Adapter。

## 统一代码身份

运行代码统一为：

```text
pyproject.toml
src/me_system/
tests/
schemas/
migrations/
```

分发包、导入包和命令：

```text
Distribution: me-system
Import:       me_system
CLI:          me-system
MCP:          me-system-mcp
```

不再保留活动实现身份：

```text
services/me-graph-core
services/me-core
me_graph_core
me_core
me-graph
me-graph-mcp
```

历史名称仅存在于 Git 历史和迁移说明中。

## Codebase-Memory 与 Graphify 参考原则

两个图谱都采用相同运行模式：

```text
原始来源
→ 确定性标准化 / 可审计抽取
→ 证据片段
→ 候选节点和关系
→ 审核进入持久化图谱
→ 类型化查询
→ MCP / CLI
→ Agent 解释和执行
```

共同吸收：

1. **Graph first**：Agent 默认读取结构图谱，不反复扫描全部资料；
2. **Persistent graph**：图谱跨会话和重启保存；
3. **Multi-stage indexing**：发现、标准化、证据、候选、冲突和质量分别处理；
4. **Typed MCP tools**：工具表达领域问题，不提供泛化聊天接口；
5. **Compact first**：默认返回紧凑子图，需要时再下钻证据；
6. **Path explanation**：答案可以沿节点、关系和证据路径解释；
7. **Incremental update**：通过哈希、Manifest 和 Adapter 版本只处理变化内容；
8. **CLI / MCP parity**：CLI 与 MCP 复用同一应用服务；
9. **Status / coverage**：明确未处理、部分覆盖、失败和歧义范围；
10. **Agent as intelligence layer**：模型可以生成候选，但不是未经审核的权威事实源。

## ME-Brain 的映射

### 节点

```text
Project / Workstream / Requirement / Decision / Task / Issue
Constraint / Artifact / Experiment / Document / Person / Evidence
```

### 关系

```text
HAS_REQUIREMENT / HAS_DECISION / HAS_TASK / HAS_ISSUE
HAS_ARTIFACT / SUPERSEDES / SATISFIES / DEPENDS_ON
BLOCKS / IMPLEMENTS / PRODUCES / SUPPORTED_BY
```

### 作用

- 恢复项目当前状态；
- 区分当前和历史决策；
- 查询任务、问题和阻塞；
- 分析成果、需求和决策影响；
- 按任务返回小子图；
- 沿证据路径下钻原文。

## ME-Who 的映射

### 节点

```text
User / Role / Capability / Preference / CollaborationRule
Goal / ProjectRole / Experience / Evidence
```

### 关系

```text
HAS_ROLE / HAS_CAPABILITY / PREFERS / HAS_COLLABORATION_RULE
HAS_GOAL / PARTICIPATES_IN / APPLIES_TO / SUPERSEDES
CONFIRMED_BY / SUPPORTED_BY
```

### 作用

- 返回任务相关用户背景；
- 按项目、任务和 Agent 裁剪协作规则；
- 区分明确事实、行为证据和推断；
- 记录偏好随时间和场景变化；
- 防止无关 Agent 读取完整个人图谱。

## Bridge 的边界

Bridge 只是显式跨领域关系 namespace，不是第三张产品图谱：

```text
who:user:master
  └── PARTICIPATES_IN
        └── brain:project:lighting-platform
```

Bridge 必须：

- 显式建立；
- 单独授权；
- 不让 ME-Brain 工具读取 ME-Who 私有节点；
- 不让 ME-Who 推断修改项目事实。

## MCP 边界

MCP 仅暴露两个领域的工具：

```text
brain_*
who_*
```

当前：

```text
brain_resolve_project
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
```

后续可以增加路径与影响分析工具，但仍然：

- 不定义图谱 Schema；
- 不直接执行任意 SQL；
- 不直接修改权威图谱；
- 不复制查询逻辑；
- 不暴露完整 ME-Who。

## 不照搬的部分

1. 不向普通 Agent 暴露任意 Cypher；
2. 不让语义推断直接进入权威事实；
3. 不把一个 JSON 文件作为权威数据库；
4. 不把 ME-Brain 与 ME-Who 合成无权限边界的平面图；
5. 不默认把完整 ME-Who 导出或提交 Git；
6. 不一次开放大量未经 Benchmark 证明的工具；
7. 不把 Agent 配置文件当动态数据源真相。

## 后果

### 正面

- 产品边界稳定；
- 安装、部署和版本只围绕一个包；
- 两领域共享基础设施但不混淆事实；
- 后续可以吸收竞品能力而不增加产品线；
- Source、Candidate 和 MCP 的位置明确。

### 代价

- 需要一次性迁移旧目录、导入名、CLI、CI 和文档；
- 当前尚未正式发布，选择不保留旧命令兼容别名；
- 新功能必须明确属于 ME-Brain、ME-Who 或内部实现职责。

## 结论

```text
产品主体：ME-System
图谱领域：ME-Brain + ME-Who
共享职责：Evidence / Ingestion / Review / Persistence / Query / MCP
Agent：查询两个图谱，必要时下钻证据
```
