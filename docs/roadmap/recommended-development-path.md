# ME-System 推荐开发路径

> 更新：2026-07-23

## 总体原则

```text
ME-System
├── ME-Brain
└── ME-Who
```

后续只深化这两个产品图谱。

共享的来源、证据、候选、存储、查询、权限、MCP 和 CLI 使用 `shared/` 实现，不拥有第三个产品名称。

两个图谱共同参考 Codebase-Memory：

```text
Persistent Graph First
+ Multi-pass Incremental Indexing
+ Typed MCP
+ Compact First
+ Status / Coverage
+ CLI / MCP Parity
```

## Phase 0：双图谱基线

已完成首版：

- ME-Brain、ME-Who、Bridge namespace；
- `GraphNode`、`GraphEdge`、`EvidenceRef`；
- `CandidateGraphChange`；
- `GraphSlice`；
- 内存 Store；
- 进程内候选审核；
- `lighting-platform` 示例；
- 项目快照、决策链、证据和任务画像查询。

## Phase 1：持久化与只读 Agent 闭环

### 已完成：PostgreSQL 权威存储

- SQLAlchemy 2.0；
- PostgreSQL + psycopg 3；
- 全局节点/边 ID；
- 有序 EvidenceRef；
- 原子写入和事务回滚；
- ME-Brain、ME-Who、Bridge 约束；
- Alembic 迁移；
- CLI；
- Python 3.11 / 3.12 + PostgreSQL CI。

### 已完成：Project Resolve 与 Hermes MCP

- canonical ID、label、alias、workspace path 和 external ID 精确解析；
- 不使用 LLM 模糊猜项目；
- Project allowlist；
- 固定 ME-Who 用户；
- 项目所有权范围；
- 六工具 stdio MCP；
- PostgreSQL 16 + MCP ClientSession E2E。

### 待真实数据验证

比较：

```text
A. Hermes 直接探索项目文件
B. Hermes + ME-Brain GraphSlice
C. Hermes + ME-Brain + ME-Who Task Profile
```

指标：

- Token；
- 工具调用次数；
- 项目恢复延迟；
- 当前事实准确率；
- 过期方案误用率；
- 重复询问和用户纠正次数。

## Phase 2：命名与物理结构收敛

这是当前第一优先级。

PR #6 曾将共享运行包命名为 ME-Core。该名字容易被误解为第三个产品，因此需要迁移为中性实现结构：

```text
services/me-core/   → shared/
me_core             → me_system
ME-Core workflow    → ME-System workflow
```

目标结构：

```text
me-system/
├── me-brain/
│   ├── ontology/
│   ├── passes/
│   └── queries/
├── me-who/
│   ├── ontology/
│   ├── passes/
│   └── queries/
├── shared/
│   ├── contracts/
│   ├── graph/
│   ├── evidence/
│   ├── ingestion/
│   ├── persistence/
│   ├── permissions/
│   └── query/
└── integrations/
    ├── mcp/
    ├── hermes/
    └── pi/
```

验收：

- README 只展示 ME-Brain 与 ME-Who；
- Python 主包为 `me_system`；
- CLI 为 `me-system`；
- MCP 命令为 `me-system-mcp`；
- 旧 import/命令只保留临时兼容；
- 现有全部测试和 MCP E2E 不回归。

## Phase 3：共享输入与治理闭环

### 3.1 Source / Evidence

实现：

```text
SourceRecord
EvidenceFragment
```

要求：

- 来源不可静默覆盖；
- 内容哈希与幂等键；
- 稳定 SourceAnchor；
- 敏感等级；
- 图谱对象可回到 EvidenceFragment；
- 不强制所有来源先转换为复杂文档模型。

### 3.2 Ingestion Status / Coverage

实现：

```text
IngestionRun
├── adapter / pass version
├── input / processed / skipped / failed
├── fragment / candidate counts
├── coverage_ratio
├── quality_report
└── log_ref
```

必须区分：

```text
图谱中不存在
≠ 尚未摄取
≠ 摄取失败
≠ 部分覆盖
```

### 3.3 Persistent Candidate Buffer

- Candidate 跨重启持久化；
- EvidenceRef 顺序；
- 幂等重试；
- payload 或证据冲突检测；
- 按目标图谱、来源和状态过滤；
- ReviewEvent。

### 3.4 Atomic Candidate Review

同一 PostgreSQL 事务：

```text
lock Candidate
→ validate pending
→ materialize GraphNode / GraphEdge
→ validate evidence and namespace
→ write canonical object
→ update Candidate
→ append ReviewEvent
→ commit
```

失败整笔回滚。

### 3.5 验收

- Source、Fragment、Run、Candidate、ReviewEvent 跨进程保存；
- 重复摄取不重复建数据；
- Candidate 重试幂等；
- 审核失败不留下部分写入；
- 权威对象可回到 EvidenceFragment；
- Hermes 六工具不回归；
- 不新增第二个数据库或第三个产品。

## Phase 4：两个图谱的输入 Pass

共享 Pass 只处理来源与标准化，业务 Pass 分别归属 ME-Brain 或 ME-Who。

```text
Discover
→ Normalize
→ Fragment
→ Brain Candidate Pass / Who Candidate Pass
→ Resolve Identity
→ Detect Conflict
→ Review
→ Commit
```

推荐 Adapter 顺序：

```text
Agent Conversation
→ Markdown
→ Git
→ Zotero
→ DOCX / PDF
```

### Agent Conversation

```text
对话导出
→ SourceRecord
→ conversation_message Fragment
→ ME-Brain Candidate
→ ME-Who Candidate
```

同一消息可以为两个图谱分别产生候选，但不得生成第三类业务图谱。

### Markdown

优先保留：

- 文件版本；
- 标题、段落、列表和代码块；
- 原文位置；
- Frontmatter；
- 文件内链接。

### Git

优先产生确定性结构：

- Repository；
- Commit；
- changed files；
- issue/PR 外部 ID；
- Artifact lineage 候选。

语义决策仍进入 Candidate。

## Phase 5：查询质量与 Codebase-Memory 式工具深化

### Compact / Standard / Full

```text
compact   ID、类型、标签、状态、关键关系
standard  增加属性、时间、证据句柄、coverage
full      按权限增加证据片段与完整属性
```

结果统一提供：

```text
total
returned
truncated
next_cursor
quality
coverage
```

### ME-Brain 工具候选

```text
brain_get_schema
brain_get_ingestion_status
brain_analyze_impact
brain_get_artifact_lineage
```

### ME-Who 工具候选

```text
who_explain_preference
who_get_profile_history
who_get_evidence
```

工具必须：

- 归属 `brain_*` 或 `who_*`；
- 证明能降低 Token 或提高准确率；
- 通过统一 Tool Registry 注册；
- 与 CLI 共用应用服务。

不增加 `core_*`、`context_*` 或独立 Source 产品工具面。

## Phase 6：ME-Who 深化

后续增加：

- 用户确认偏好；
- 有效期和替代；
- 行为证据候选；
- 用户确认、限制和禁止使用；
- 字段级授权；
- Agent 使用审计。

ME-Who 必须比代码图更严格：

- 证据必需；
- 推断与明确事实分离；
- 适用范围明确；
- 默认最小暴露；
- 不向普通 Agent 开放任意图查询。

## Phase 7：治理界面、Pi 与领域包

### 候选治理界面

第一版只需要：

- Candidate 列表；
- Evidence 预览；
- 批准、驳回；
- ReviewEvent；
- coverage 和 quality；
- ME-Who 敏感信息治理。

不优先建设大型图谱画布。

### Pi / 执行 Agent

- 当前项目 GraphSlice；
- 任务相关 ME-Who 规则；
- 证据下钻；
- Candidate 提交。

Pi 默认不读取完整 ME-Who。

### 领域扩展

ME-Brain 领域包：

```text
Software: Repository / Module / Component / Commit / PR / Test
Research: Paper / Claim / Method / Dataset / Experiment / Finding
Design: Brief / Option / DesignDecision / Drawing / Model / Review
```

领域包扩展 ME-Brain 本体和查询，不创建独立 Store 或第三产品。

## 数据库演进原则

当前唯一权威存储是 PostgreSQL。

只有真实多跳查询、图算法或规模指标证明关系表不足时，才评估图扩展或独立图数据库。任何替代方案必须：

- 保持 ME-Brain / ME-Who 语义；
- 通过相同契约与 GraphSlice 对照；
- 说明事务、权限、迁移和回滚成本；
- 不形成并行真相源。

## 暂停开发

在输入候选闭环和真实 Benchmark 通过前，不优先投入：

- 独立 Source / Candidate / MCP 服务；
- 第三个产品图谱；
- 完整多 Agent Handoff；
- 万能文档标准；
- 独立 ME-Reader；
- 数字人格；
- 大型图谱前端；
- 自动语义知识确认；
- 多数据库并行；
- 普通 Agent 任意 Cypher。
