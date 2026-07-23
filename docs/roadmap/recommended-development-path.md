# ME-System 推荐开发路径

> 更新：2026-07-23

## 总体原则

```text
ME-System
└── ME-Core
    ├── ME-Brain Graph
    ├── ME-Who Graph
    ├── Source / Evidence / Candidate
    ├── Query / Projection
    └── MCP / CLI
```

后续阶段只增加 ME-Core 内部模块、输入 Pass、领域本体和薄前端，不新增平级核心或第二个权威数据库。

## Phase 0：单核心与双图谱基线

已完成首版：

- ME-Brain、ME-Who、Bridge 三个命名空间；
- `GraphNode`、`GraphEdge`、`EvidenceRef`；
- `CandidateGraphChange`；
- `GraphSlice`；
- `InMemoryGraphStore`；
- 进程内候选审核；
- `lighting-platform` 示例；
- 项目快照、决策追踪、证据和任务画像查询；
- 运行内核名称统一为 `ME-Core / services/me-core / me_core`。

## Phase 1：持久化与只读 Agent 闭环

### 已完成：PostgreSQL 权威存储

- SQLAlchemy 2.0；
- PostgreSQL + psycopg 3；
- 全局节点/边 ID；
- 有序 EvidenceRef；
- 原子写入和事务回滚；
- ME-Brain、ME-Who、Bridge 约束；
- Alembic 迁移；
- 数据库 CLI；
- 内存 Store 与持久化 Store 查询一致性；
- Python 3.11 / 3.12 + PostgreSQL CI。

### 已完成：Project Resolve 与 Hermes 只读 MCP

- canonical ID、label、alias、workspace path 和 external ID 精确解析；
- 不使用 LLM 或模糊匹配猜项目；
- 服务端 Project allowlist；
- 服务端固定 ME-Who 用户；
- 显式项目所有权范围；
- 跨项目语义边不扩大权限；
- 六工具 stdio MCP；
- Hermes 白名单和 Bootstrap；
- MCP Python SDK 固定 `<2`；
- PostgreSQL 16 + 真实 stdio ClientSession E2E。

### Phase 1 验收现状

已通过自动测试：

- 当前决策不混入过期方案；
- 阻塞关系和问题可查询；
- 决策可返回证据；
- 数据跨进程保持；
- Hermes 不直接连接数据库；
- 非允许项目和跨项目对象不能越权返回。

待真实数据完成后验证：

- GraphSlice 相比全文件探索的 Token、延迟和准确度收益；
- ME-Who Task Profile 是否减少重复询问和协作错误。

## Phase 2：ME-Core 输入与治理闭环

这是当前 P0。

### 2.1 Source / Evidence

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

### 2.2 Ingestion Status / Coverage

实现：

```text
IngestionRun
├── adapter / pipeline version
├── input / processed / skipped / failed
├── fragment / candidate counts
├── coverage_ratio
├── quality_report
└── log_ref
```

目标是让 Agent 和人能区分：

```text
图谱中不存在
≠
来源尚未摄取
≠
摄取失败
≠
只完成部分覆盖
```

### 2.3 Persistent Candidate Buffer

实现：

- Candidate 跨重启持久化；
- EvidenceRef 顺序；
- 幂等重试；
- payload 或证据冲突检测；
- 按图谱、来源和状态过滤；
- 游标分页；
- Submitted ReviewEvent。

### 2.4 Atomic Candidate Review

在一个 PostgreSQL 事务中完成：

```text
lock Candidate
→ validate pending
→ materialize GraphNode / GraphEdge
→ validate Evidence and namespace
→ write canonical graph object
→ update Candidate
→ append ReviewEvent
→ commit
```

失败时整笔回滚。

### 2.5 Phase 2 验收

- Source、Fragment、Run、Candidate 和 ReviewEvent 跨进程保存；
- 重复摄取不重复建数据；
- Candidate 重试不重复；
- 审核失败不留下部分写入；
- 权威对象能回到相同 EvidenceFragment；
- 当前 Hermes 六工具不回归；
- 不新增第二个数据库或服务核心。

## Phase 3：输入 Pass

所有 Pass 位于 ME-Core 内部，统一输出 Source / Evidence / Candidate。

推荐顺序：

```text
Agent Conversation Pass
→ Markdown Pass
→ Git Pass
→ Zotero Pass
→ DOCX / PDF Pass
```

### Conversation Pass

```text
对话导出
→ SourceRecord
→ conversation_message EvidenceFragment
→ CandidateGraphChange
```

不直接写入 ME-Brain 或 ME-Who。

### Markdown Pass

优先保留：

- 文件版本；
- 标题、段落、列表和代码块；
- 原文位置；
- Frontmatter；
- 文件内链接。

### Git Pass

优先产生确定性结构：

- Repository；
- Commit；
- changed files；
- issue/PR 外部 ID；
- artifact lineage 候选。

语义决策仍进入 Candidate。

## Phase 4：查询质量与真实 Agent Benchmark

### 4.1 Compact / Standard / Full 投影

逐步支持：

```text
compact   ID、类型、标签、状态、关键关系
standard  增加属性、时间和证据句柄
full      按权限增加完整属性与证据片段
```

列表和子图统一返回：

```text
total
returned
truncated
next_cursor
quality
coverage
```

### 4.2 只读质量工具

输入治理稳定后评估：

```text
graph_get_schema
ingestion_get_status
graph_get_coverage
```

这些工具必须通过单一 Tool Registry 注册，并与 CLI 共用应用服务。

### 4.3 Hermes Benchmark

比较：

```text
A. Hermes 直接探索项目文件
B. Hermes + ME-Brain GraphSlice
C. Hermes + ME-Brain + ME-Who Task Profile
```

记录：

- 输入 Token；
- 工具调用次数；
- 首次项目恢复延迟；
- 当前事实准确率；
- 过期方案误用率；
- 来源覆盖率；
- 重复询问次数；
- 用户纠正次数。

## Phase 5：ME-Who 深化与治理

当前已有：

- 用户角色；
- 专业能力；
- 项目参与关系；
- 明确协作规则；
- 任务类型过滤。

后续增加：

- 用户确认偏好；
- 规则有效期与替代；
- 候选行为证据；
- 用户确认、限制和禁止使用；
- 敏感度与字段级授权；
- 哪个 Agent 在何任务使用过哪些个人信息。

## Phase 6：治理界面、Pi 与领域包

### 候选治理界面

第一版只需要：

- 候选列表；
- Evidence 预览；
- 批准、驳回；
- ReviewEvent 历史；
- 质量和覆盖率；
- ME-Who 敏感信息治理。

不优先建设大型图谱画布。

### Pi / 执行 Agent

在 Candidate 和权限闭环稳定后：

- 当前项目 GraphSlice；
- 任务相关 ME-Who 规则；
- 证据下钻；
- Candidate 提交。

Pi 默认不读取完整 ME-Who。

### 领域扩展

Software：

```text
Repository / Module / Component / Interface / Commit / PR / Test
```

Research：

```text
Paper / Claim / Evidence / Method / Dataset / Experiment / Finding
```

Design：

```text
Brief / Option / DesignDecision / Drawing / Model / Review / Revision
```

Domain Pack 只能扩展 ME-Core 的本体、Pass 和查询，不能创建独立 Store。

## 数据库演进原则

当前唯一权威存储为 PostgreSQL。只有真实多跳查询、图算法或规模指标证明关系表不足时，才评估 PostgreSQL 图扩展或独立图数据库。

任何替代方案必须：

- 实现同一 `GraphStore`；
- 通过相同契约；
- 与 PostgreSQL GraphSlice 对照；
- 说明迁移、事务、权限和回滚成本；
- 不能形成两个并行真相源。

## 暂停开发

在输入候选闭环和真实 Agent Benchmark 通过前，不优先投入：

- 独立 Source Ledger / Candidate / MCP 服务；
- 完整多 Agent Handoff 平台；
- 全格式万能文档标准；
- 独立 ME-Reader 产品；
- 数字人格；
- 大型图谱前端；
- 全自动语义知识确认；
- 多数据库并行架构；
- 普通 Agent 任意 Cypher。