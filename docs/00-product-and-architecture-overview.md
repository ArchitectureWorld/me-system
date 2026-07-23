# ME-System 产品与架构总纲

> 状态：当前权威架构  
> 日期：2026-07-23

## 1. 产品定义

ME-System 只有两个产品级核心：

| 产品 | 负责的问题 | 核心输出 |
|---|---|---|
| ME-Brain Graph | 事情和项目是什么、现在进行到哪里、为什么变成这样 | 可追溯项目子图 |
| ME-Who Graph | 用户是谁、在当前任务中 Agent 应如何协作 | 任务相关个人子图 |

两者不是两个笔记库，也不是两个向量数据库，而是两个具有独立命名空间、本体、权限和审核流程的权威结构化图谱。

## 2. 非产品级组件

以下能力很重要，但不应被提升为第三条产品线：

- Document Standardization：把文件和消息转换成可寻址证据；
- Source Ledger：保存来源身份与版本；
- Graph Ingestion：把证据转换成候选图谱变更；
- Graph Query Service：查询、裁剪和解释子图；
- Context Projection：将 GraphSlice 投影成文本或结构化上下文；
- Agent Adapter：通过 MCP、REST 或 SDK 暴露查询工具；
- Research Reader：研究领域的文献精读工作流。

`ME-Context` 不再作为独立产品名称。它是 Graph Query Service 内部的一种运行时投影能力。

`ME-Reader` 不再作为独立产品名称。Zotero、Obsidian、论文解析和 Agent 精读归入 Research Domain。

## 3. 总体架构

```text
D0 原始来源
文件、消息、Git、Zotero、邮件、模型输出
        │
        ▼
D1 证据层
SourceRecord / DocumentVersion / ContentFragment / EvidenceAnchor
        │
        ▼
D2 候选图谱
CandidateGraphChange
        │
        ▼
审核、消歧、冲突检测、规则确认
        │
  ┌─────┴─────┐
  ▼           ▼
D3 ME-Brain   D3 ME-Who
Canonical     Canonical
Graph         Graph
  └─────┬─────┘
        ▼
D4 派生索引
全文、向量、摘要、社区、缓存
        │
        ▼
D5 Agent GraphSlice
任务相关子图、证据句柄和文本投影
```

## 4. 图谱边界

### 4.1 ME-Brain

保存客观项目事实：

- 项目、需求、决策、任务、问题、约束、成果、人员和证据；
- 当前事实与历史事实；
- 方案替代、依赖、阻塞、实现和支持关系。

### 4.2 ME-Who

保存 Agent 完成任务所需的个人事实：

- 用户、角色、能力、目标、偏好、项目角色和协作规则；
- 每项信息的适用范围、证据、有效期和敏感度；
- 明确事实与推断候选的区别。

### 4.3 Bridge

跨两个图谱的关系必须显式存在于 Bridge 命名空间，例如：

```text
(who:user)-[:PARTICIPATES_IN]->(brain:project)
(who:project-role)-[:APPLIES_TO_PROJECT]->(brain:project)
```

ME-Who 和 ME-Brain 不直接共享节点表语义，也不允许普通领域边跨图。

## 5. Agent 使用方式

```text
Hermes / Pi / Codex
        │
        ▼
Typed Agent Tool
        │
        ▼
Graph Query Service
- 权限过滤
- 时间过滤
- 类型化查询
- 子图裁剪
- 证据解释
        │
        ▼
ME-Brain / ME-Who / Bridge
```

Agent 不应：

- 直接执行 Cypher、SQL 或 Gremlin；
- 直接读取图数据库；
- 将向量检索结果当成权威事实；
- 将候选节点当成已确认节点；
- 直接修改权威图谱。

## 6. GraphSlice

一次 Agent 查询的主要输出是 `GraphSlice`：

```yaml
slice_id:
graph:
as_of_time:
root_ids: []
summary:
nodes: []
edges: []
evidence_handles: []
excluded:
  superseded: []
  unauthorized: []
truncated: false
```

Context Pack 是 GraphSlice 的文本、Markdown 或模型特定投影。

## 7. 首个验证场景

用户只说：

> 继续推进 lighting-platform。

系统必须能够：

1. 找到项目节点；
2. 返回当前有效决策；
3. 排除被替代的 Cycles 路线；
4. 返回正在阻塞任务的问题；
5. 返回相关成果和需求；
6. 返回必要证据；
7. 查询适用于实现任务的用户协作规则；
8. 避免读取全部历史文档；
9. 将新发现提交为候选变更。

## 8. 数据库策略

图谱是产品模型，不等于第一天必须选择某一图数据库。

v0.1 先以 `GraphStore` 接口和内存实现验证契约与查询。下一步推荐实现 PostgreSQL Adapter：

```text
graph_node
graph_edge
evidence_ref
candidate_graph_change
graph_review
audit_log
```

等真实多跳查询被证明有价值后，再评估 Apache AGE、Neo4j 或其他图引擎。
