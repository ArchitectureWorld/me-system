# ME-System 推荐开发路径

> 更新：2026-07-23

## 总体原则

```text
ME-System
├── ME-Brain
└── ME-Who
```

后续只深化这两个权威图谱领域。

Evidence、Ingestion、Candidate、Review、Persistence、Query、Bridge、MCP 与 CLI 都是同一个 `me_system` 包中的内部职责，不拥有第三个产品名称。

两个图谱共同参考 Codebase-Memory 与 Graphify：

```text
Persistent Graph First
+ Multi-stage Incremental Indexing
+ Typed MCP
+ Compact First
+ Path-based Explanation
+ Status / Coverage / Ambiguity
+ CLI / MCP Parity
```

## Phase 0：双图谱基线——已完成首版

- ME-Brain、ME-Who、Bridge namespace；
- `GraphNode`、`GraphEdge`、`EvidenceRef`；
- `CandidateGraphChange`；
- `GraphSlice`；
- 内存 Store；
- `lighting-platform` 示例；
- 项目快照、决策链、证据和任务画像查询。

## Phase 1：持久化与只读 Agent 闭环——已完成首版

### PostgreSQL 权威存储

- SQLAlchemy 2.0；
- PostgreSQL + psycopg 3；
- 全局节点/边 ID；
- 有序 EvidenceRef；
- 原子写入和事务回滚；
- ME-Brain、ME-Who、Bridge 约束；
- Alembic 迁移；
- Python 3.11 / 3.12 + PostgreSQL CI。

### Project Resolve 与 Hermes MCP

- canonical ID、label、alias、workspace path 和 external ID 精确解析；
- 不使用 LLM 模糊猜项目；
- Project allowlist；
- 固定 ME-Who 用户；
- 项目所有权范围；
- 六工具 stdio MCP；
- PostgreSQL 16 + MCP ClientSession E2E。

### 统一运行包

```text
Distribution: me-system
Import:       me_system
CLI:          me-system
MCP:          me-system-mcp
```

旧 `ME-Core`、`ME-Graph-Core`、`me_core` 与 `me_graph_core` 不再作为活动产品或代码身份。

## Phase 2：共享输入与治理闭环——当前完成首版

### Source / Evidence

```text
SourceRecord
EvidenceFragment
```

能力：

- 不可变来源登记；
- 内容 SHA-256 与幂等键；
- 稳定 SourceAnchor；
- 敏感等级；
- 来源与片段冲突检测；
- 图谱对象可回到 EvidenceFragment；
- 不要求所有来源先进入复杂文档模型。

### Ingestion Status / Coverage

```text
IngestionRun
├── adapter name / version
├── pending / running / completed / partial / failed
├── input / processed / skipped / failed
├── fragment / candidate counts
├── coverage_ratio
├── quality_report
├── log_ref
└── error_summary
```

系统必须区分：

```text
图谱中不存在
≠ 尚未摄取
≠ 摄取失败
≠ 部分覆盖
≠ 候选尚未审核
```

### Persistent Candidate Queue

- Candidate 跨重启持久化；
- EvidenceRef 顺序；
- 幂等重试；
- payload 冲突检测；
- 按目标图谱和来源过滤；
- 追加式 `ReviewEvent`；
- submitted / approved / rejected 全历史。

### Atomic Candidate Review

同一 PostgreSQL 事务：

```text
lock Candidate
→ validate pending
→ materialize GraphNode / GraphEdge
→ validate evidence / endpoint / namespace
→ write canonical object and evidence
→ update Candidate
→ append ReviewEvent
→ commit
```

失败整笔回滚。

### 治理 CLI

```text
source-register
source-show
candidate-submit
candidate-list
candidate-approve
candidate-reject
```

这些命令是内部治理入口，不加入当前 Hermes MCP。

### Phase 2 验收

- Source、Fragment、Run、Candidate、ReviewEvent 跨进程保存；
- 重复摄取不重复建数据；
- Candidate 重试幂等；
- 审核失败不留下部分写入；
- 权威对象可回到 EvidenceFragment；
- 同一来源可同时生成 ME-Brain 与 ME-Who Candidate；
- Hermes 六工具不回归；
- 不新增第二个数据库或第三个产品。

## Phase 3：增量索引基础——下一优先级

### 3.1 Source Manifest

新增：

```text
SourceManifest
├── source identity
├── content hash
├── adapter name / version
├── extraction rule / model version
├── last successful run
├── coverage
└── graph candidate identities
```

目标：

- 只处理新增或变化内容；
- Adapter 重跑可解释；
- 明确哪个版本生成了哪些 Candidate；
- 支持安全重建和差异比较。

### 3.2 Derivation Kind

在 Candidate / Graph Schema v0.2 增加：

```text
EXPLICIT
RULE_DERIVED
MODEL_INFERRED
AMBIGUOUS
HUMAN_ASSERTED
```

它与以下字段独立：

- authority；
- confirmation_status；
- confidence；
- source_refs。

### 3.3 Adapter SDK

统一 Adapter 接口：

```text
detect
→ normalize
→ fragment
→ propose Brain Candidates
→ propose Who Candidates
→ report coverage / quality
```

Adapter 不能：

- 建立自己的数据库；
- 直接写权威图谱；
- 创建新的 MCP 业务模型；
- 隐藏失败和跳过范围。

## Phase 4：第一个真实输入 Adapter

推荐顺序：

```text
Agent Conversation
→ Markdown
→ Git
→ Zotero
→ DOCX / PDF
```

### Agent Conversation Adapter

```text
对话导出
→ SourceRecord
→ conversation_message EvidenceFragment
→ Brain Candidate Pass
→ Who Candidate Pass
→ conflict detection
→ review
→ canonical graphs
```

第一版优先抽取：

#### ME-Brain

- Project；
- Decision；
- Requirement；
- Task；
- Issue；
- Constraint；
- Artifact reference。

#### ME-Who

- explicit UserFact；
- Role；
- Capability；
- CollaborationRule；
- project-scoped Preference。

不做完整人格推断。

## Phase 5：路径式查询与影响分析

吸收 Graphify / Codebase-Memory：

```text
brain_get_node
brain_get_neighbors
brain_shortest_path
brain_explain_path
brain_analyze_impact
```

原则：

- 领域工具优先；
- 路径工具用于探索和诊断；
- 每条路径可返回 EvidenceRef；
- 不开放任意写入型 Cypher；
- 查询必须受项目、权限、深度和结果数量限制。

## Phase 6：Graph Report 与 Benchmark

### Graph Report

可再生投影：

```text
me-system-out/
├── brain-report.md
├── brain-snapshot.json
├── graph-manifest.json
├── who-report.md        # 默认本地私有
└── graph.html           # 后置
```

### Benchmark

比较：

```text
A. Agent 直接探索全部来源
B. 全文 / 向量检索
C. ME-System Graph Query
```

指标：

- Token；
- 工具调用次数；
- 项目恢复延迟；
- 当前事实准确率；
- 历史事实混淆率；
- 证据覆盖率；
- 摄取和增量更新时间；
- 用户重复纠正次数。

第一组继续使用 `lighting-platform`。

## Phase 7：领域深化

### Software

```text
Repository / Module / Component / Interface / Commit / PR / Test
```

### Research

```text
Paper / Claim / Evidence / Method / Dataset / Experiment / Finding
```

Zotero 与 Obsidian 代码归入本领域。

### Design

```text
Brief / Option / DesignDecision / Drawing / Model / Review / Revision
```

## 暂停开发

在增量摄取、路径查询和 Benchmark 通过前，不优先投入：

- 完整多 Agent Handoff 平台；
- 全格式万能文档标准；
- 独立 ME-Reader；
- 数字人格；
- 大型图谱前端；
- 全自动知识确认；
- 多数据库并行架构；
- 任意图查询语言。
