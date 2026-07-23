# Hermes Integration Boundary

Hermes 第一阶段通过 MCP 读取 ME-System，但 MCP Adapter 只包装 `GraphQueryService`，不直接读取数据库。

## 第一批工具

```text
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
```

映射关系：

| MCP 工具 | Core 方法 |
|---|---|
| brain_get_snapshot | `get_project_snapshot` |
| brain_expand_subgraph | `expand_subgraph` |
| brain_trace_decision | `trace_decision` |
| brain_get_evidence | `get_evidence` |
| who_get_task_profile | `get_task_profile` |

## 权限

Hermes 可以读取：

- 已授权项目的 ME-Brain；
- 与当前任务相关的 ME-Who；
- 相关证据句柄。

Hermes 不能：

- 直接执行 SQL 或 Cypher；
- 自动批准候选；
- 读取与任务无关的敏感 ME-Who 节点。

生产 MCP Server 在 PostgreSQL GraphStore 和权限过滤器完成后实现。
