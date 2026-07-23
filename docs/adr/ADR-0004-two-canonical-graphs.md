# ADR-0004：以 ME-Brain 与 ME-Who 两个权威图谱作为系统核心

- 状态：Accepted
- 日期：2026-07-23
- 决策范围：产品边界、数据分层、图谱模型、Agent 接入优先级

## 背景

此前架构逐渐把文档标准化、Context Gateway、Context Pack、Hermes/Pi Adapter 和 ME-Reader 同时提升为核心，导致：

- 产品从两条线扩张为多个平级子系统；
- 在图谱 Schema 未稳定前提前设计大量 Agent 协议；
- 图谱被放在“派生索引”位置，无法成为权威知识；
- Draft PR 中出现第三产品 ME-Reader；
- 主分支与实现分支发生架构漂移。

## 决策

ME-System 的产品核心固定为：

```text
ME-Brain Graph
+
ME-Who Graph
```

共享基础设施包括：

```text
Source & Evidence
Graph Contracts
Temporal Model
Provenance
Permissions
Candidate Review
Graph Query
Agent Adapter
```

### 关键关系

```text
文档标准化 = 输入和证据基础
双图谱       = 权威知识核心
派生索引     = 可重建加速层
GraphSlice   = 任务子图
Context Pack = GraphSlice 的模型投影
MCP          = Agent 访问方式
```

## 两个图谱

### ME-Brain

- 命名空间：`me_brain`
- ID 前缀：`brain:`
- 保存客观项目知识。

### ME-Who

- 命名空间：`me_who`
- ID 前缀：`who:`
- 保存任务相关的个人理解和协作信息。

### Bridge

- 命名空间：`bridge`
- 只保存跨两个图谱的显式关系；
- Bridge 不包含节点。

## 权威性

自动解析、LLM 抽取和 Agent 发现首先生成：

```text
CandidateGraphChange
```

只有经过人工或受控规则确认后，才写入权威图谱。

## 数据库存储

v0.1 不绑定具体图数据库。先通过 `GraphStore` 接口和内存实现验证模型。

推荐下一步使用 PostgreSQL 实现首个持久化 Adapter，保留后续切换 Apache AGE 或其他图数据库的能力。

## 产品命名调整

- `ME-Context`：取消产品级命名，改为 GraphSlice / Context Projection。
- `ME-Reader`：取消产品级命名，归入 Research Domain。
- Zotero / Obsidian：属于输入和投影 Adapter。
- Hermes / Pi：属于 Agent Adapter。

## 实施优先级

```text
图谱契约
→ 手工真实图
→ 类型化查询
→ Hermes 只读 MCP
→ 文档、对话、Git Adapter
→ ME-Who 最小图
→ 候选审核
→ Pi Extension
→ 领域扩展
```

## 后果

### 正面

- 产品边界重新清晰；
- Agent 协议围绕真实图谱能力设计；
- 文档、Zotero、Obsidian 和未来前端都有稳定落点；
- 当前事实、历史事实和证据成为图谱一等对象；
- 可以先证明 Token、准确度和项目恢复收益。

### 代价

- 需要重写部分已有架构文档；
- Draft PR #1 不能直接按原结构合并；
- 复杂 Context Pack、Handoff 和前端工作后置；
- 需要建立本体版本和图谱迁移纪律。
