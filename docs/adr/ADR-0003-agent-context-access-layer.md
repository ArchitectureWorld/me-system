# ADR-0003：Agent 通过统一访问层读取 ME-System

- 状态：Accepted，受 ADR-0004 约束
- 日期：2026-07-22
- 更新：2026-07-23

## 决策

Agent 不直接读取 ME-System 数据库，而是通过类型化查询接口访问。

```text
Agent
→ MCP / REST / SDK Adapter
→ Graph Query Service
→ ME-Brain / ME-Who / Bridge
```

## 与 ADR-0004 的关系

本 ADR 只决定**怎么访问**，不决定**系统核心是什么**。

ADR-0004 已明确：

- ME-Brain 与 ME-Who 两个权威图谱是产品核心；
- Context Pack 是 GraphSlice 的运行时投影；
- Agent Context Gateway 不是独立核心产品；
- Adapter 不得反向定义图谱 Schema。

因此，原先较完整的 `TaskContextRequest`、`ExecutionHandoffPack`、复杂 Token 分配和多 Agent 编排协议全部后置。v0.1 先提供少量只读图谱工具。

## v0.1 工具边界

Hermes 第一批只需要：

```text
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
who_explain_item
```

候选写入在只读闭环通过后增加：

```text
graph_submit_candidate
```

## 不允许的方式

- Agent 直接连接 PostgreSQL 或图数据库；
- Agent 直接生成任意 Cypher；
- 将 Markdown 投影当作权威数据；
- Adapter 扩大自身权限；
- Adapter 自动批准候选变更。
