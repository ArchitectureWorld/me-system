# Codebase-Memory 架构 Review：ME-Brain 与 ME-Who 的吸收方案

> Review 日期：2026-07-23  
> 参考项目：[`DeusData/codebase-memory-mcp`](https://github.com/DeusData/codebase-memory-mcp)  
> 目的：让 ME-Brain 与 ME-Who 参考其图谱构建、查询和 MCP 方法，不复制其具体技术栈。

## 一、结论

ME-System 只有两个产品图谱：

```text
ME-System
├── ME-Brain
└── ME-Who
```

Codebase-Memory 不是第三条产品线，也不是要被嵌入的额外核心。它提供的是一套值得参考的方法：

```text
先解析并建立持久化结构图谱
→ 再让 Agent 通过类型化 MCP 查询
→ 默认返回紧凑结构
→ 必要时下钻关系、证据和原文
```

共享存储、来源、权限、摄取和 MCP 代码属于内部 `shared/` 实现，不拥有第三个产品名称。

---

# 二、Codebase-Memory 最值得吸收的逻辑

## 1. 图谱先于 Agent 文件探索

Codebase-Memory 先将代码库索引为持久化知识图谱，再回答结构查询。Agent 不需要为每次任务重新执行大量目录遍历、grep 和文件读取。

ME-System 对应采用：

```text
原始来源
→ 标准化和结构抽取
→ 持久化 ME-Brain / ME-Who 图谱
→ GraphSlice
→ Agent
```

这意味着：

- ME-Brain 不只是文档检索层；
- ME-Who 不只是用户摘要文件；
- GraphSlice 是从权威图谱裁剪的运行时结果；
- 原始材料只在证据核验时读取。

## 2. 后端不负责聊天回答

Codebase-Memory 的结构后端不内置一个负责最终回答的 LLM。Agent 是自然语言理解层，后端负责确定性的索引、存储和查询。

ME-System 应保持：

```text
Agent：理解意图、选择工具、解释结果
ME-Brain / ME-Who：返回结构事实和证据
```

模型可以参与 Candidate 抽取，但不能静默决定权威事实。

## 3. 多阶段 Pass，而不是一个万能解析器

Codebase-Memory 使用多阶段 Pipeline 分别构建 definitions、calls、usages、tests、routes、git history 等结构。

ME-Brain 与 ME-Who 也应采用 Pass：

```text
Pass 1  发现来源
Pass 2  标准化 EvidenceFragment
Pass 3  提取节点候选
Pass 4  提取关系候选
Pass 5  实体消歧和归属
Pass 6  时间、冲突和替代检查
Pass 7  审核与权威提交
Pass 8  派生全文、向量和摘要索引
```

每个 Pass：

- 单一职责；
- 明确版本；
- 可独立测试；
- 支持增量重跑；
- 输出覆盖率和质量状态。

## 4. 类型化 MCP，而不是泛化 Search

Codebase-Memory 提供面向代码结构的专用工具，如架构概览、调用链、变更影响、图谱 Schema 和索引状态。

ME-System 同样应围绕两个图谱域提供类型化工具：

### ME-Brain

```text
brain_resolve_project
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
brain_get_status          后续
brain_get_schema          后续
brain_analyze_impact      后续
```

### ME-Who

```text
who_get_task_profile
who_explain_preference    后续
who_get_profile_history   后续
who_get_evidence          后续
```

不建立 `core_*`、`context_*` 等第三产品工具集。

## 5. Compact First

Codebase-Memory 的价值之一是用结构结果代替大量原始代码读取。

ME-System 统一支持三种输出深度：

```text
compact
  ID、类型、标签、状态、关键关系

standard
  增加属性、时间、来源句柄和质量信息

full
  按权限增加证据片段和更多属性
```

列表和子图结果逐步统一返回：

```text
total
returned
truncated
next_cursor
coverage
quality
```

Agent 必须知道结果是否完整，不能把“没有索引到”误认为“事实不存在”。

## 6. MCP 与 CLI 对等

Codebase-Memory 的主要工具也能从 CLI 调用。

ME-System 应保持：

```text
应用服务
├── MCP Adapter
├── CLI Adapter
└── 未来 Web Adapter
```

MCP 和 CLI 不复制图谱查询逻辑。

## 7. Project Scope

Codebase-Memory 的结构查询围绕具体代码项目执行。

ME-System 对应规则：

- ME-Brain 查询必须带 canonical `project_id`；
- 项目解析使用确定性 ID、名称、别名、目录或外部 ID；
- 不用 LLM 模糊猜测项目；
- ME-Who 按用户、项目、任务类型和 Agent 身份裁剪；
- 不允许普通 Agent 扫描整个 ME-Who 图谱。

## 8. Index Status 与 Coverage

Codebase-Memory 把索引状态作为正式能力。

ME-System 的 `IngestionRun` 应包含：

```text
adapter_name
adapter_version
input_item_count
processed_item_count
skipped_item_count
failed_item_count
fragment_count
candidate_count
coverage_ratio
quality_report
log_ref
status
```

这既是运维信息，也是 Agent 判断图谱可信度的依据。

## 9. 增量和本地优先

ME-System 对应实现：

- SourceRecord 通过幂等键和内容哈希识别变化；
- Adapter 重跑只处理变化内容；
- Candidate 具备幂等键；
- 图谱通过 ChangeSet 增量更新；
- PostgreSQL 是本地/NAS 的唯一权威库；
- 不为每个 Adapter 创建独立数据库。

---

# 三、ME-Brain 如何参考 Codebase-Memory

## 1. 作用对应

| Codebase-Memory | ME-Brain |
|---|---|
| 理解代码库结构 | 理解科研、设计、开发项目结构 |
| Function / Class / File | Decision / Requirement / Task / Artifact |
| CALLS / IMPORTS | DEPENDS_ON / IMPLEMENTS / BLOCKS / SUPERSEDES |
| Architecture overview | Project snapshot |
| Call path | Decision / dependency path |
| Change impact | Project impact analysis |
| Code snippet | Evidence fragment |
| Index status | Project ingestion status |

## 2. ME-Brain 图谱对象

### 节点

```text
Project
Workstream
Requirement
Decision
Task
Issue
Constraint
Artifact
Experiment
Document
Person
Evidence
```

### 关系

```text
HAS_REQUIREMENT
HAS_DECISION
HAS_TASK
HAS_ISSUE
HAS_ARTIFACT
SUPERSEDES
SATISFIES
DEPENDS_ON
BLOCKS
IMPLEMENTS
PRODUCES
SUPPORTED_BY
```

## 3. 主要查询

ME-Brain 应优先回答结构问题，而不是只返回相似段落：

- 当前阶段、路线和约束是什么；
- 哪条决策替代了旧决策；
- 哪个问题阻塞了哪些任务；
- 某个成果实现了哪些决策和需求；
- 某项变化影响哪些对象；
- 每个结论的证据在哪里。

---

# 四、ME-Who 如何参考 Codebase-Memory

## 1. 作用对应

Codebase-Memory 将代码对象和关系预先结构化，使 Agent 不必重新理解整个代码库。

ME-Who 将用户相关事实和关系预先结构化，使 Agent 不必从全部历史对话重新推断用户。

## 2. ME-Who 图谱对象

### 节点

```text
User
Role
Capability
Preference
CollaborationRule
Goal
ProjectRole
Experience
Evidence
```

### 关系

```text
HAS_ROLE
HAS_CAPABILITY
PREFERS
HAS_COLLABORATION_RULE
HAS_GOAL
PARTICIPATES_IN
APPLIES_TO
SUPERSEDES
CONFIRMED_BY
SUPPORTED_BY
```

## 3. 与代码图不同的额外约束

ME-Who 必须比 Codebase-Memory 更严格：

- 每个高价值节点和关系必须有证据；
- 区分用户明确确认、行为证据和模型推断；
- 偏好必须有适用范围；
- 支持有效时间和替代关系；
- 任务无关的个人信息不返回；
- 普通 Agent 不获得任意图查询能力；
- 用户拥有修改、否定和删除权。

## 4. 主要查询

- 当前任务需要哪些用户背景；
- Agent 应采用怎样的自主程度；
- 哪些内容已经确认，不应重复询问；
- 某项偏好适用于什么项目或任务；
- 该判断的证据和确认状态是什么；
- 过去的偏好如何变化。

---

# 五、共享实现不构成第三个产品

目标仓库结构：

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

`shared/` 仅代表技术复用。

其中：

- ME-Brain 与 ME-Who 分别拥有自己的本体、Pass 和查询；
- 两者共享 GraphNode、GraphEdge、EvidenceRef、时间、权限和 PostgreSQL；
- MCP 只暴露 `brain_*` 与 `who_*`；
- Source/Evidence 输入管线通过 `target_graph` 将 Candidate 送往相应图谱。

---

# 六、不应照搬 Codebase-Memory

## 1. 不开放任意 Cypher

Codebase-Memory 的代码结构图适合提供只读 Cypher。ME-Who 包含个人敏感数据，任意图查询可能绕过权限裁剪。

结论：Agent 使用类型化工具；管理员查询未来单独设计。

## 2. 不让自动语义抽取直接成为权威事实

AST、函数、调用关系多数可确定性重建；用户偏好、项目决策和研究结论可能存在歧义。

结论：

```text
确定性结构 → 可规则确认
语义事实 → Candidate → 审核 → 权威图谱
```

## 3. 不采用每项目 SQLite 作为权威数据

ME-System 需要跨项目来源、审核事务和 ME-Who，因此继续使用一个 PostgreSQL 权威库，通过图谱 namespace 隔离。

## 4. 不一次开放大量 MCP 工具

新增工具必须满足至少一项：

- 明显降低 Token；
- 提升准确率；
- 暴露必要质量状态；
- 解决已验证的 Agent 工作流问题。

## 5. 不自动授权全部 Agent 访问 ME-Who

Hermes、Pi、Codex 使用不同工具 Profile 和项目 allowlist；默认只允许 Hermes 获取任务相关 ME-Who。

---

# 七、对当前开发路线的调整

```text
1. 只保留 ME-Brain / ME-Who 两个产品图谱
2. 将早期 me-graph-core 命名迁移到无产品身份的 shared 实现
3. 建立 SourceRecord / EvidenceFragment / IngestionRun
4. 持久化 Candidate Buffer 与审核事件
5. 让两个图谱共享输入设施，但分别拥有本体和查询
6. Agent Conversation Adapter
7. Markdown Adapter
8. Git Adapter
9. 增加 status / coverage 查询
10. 以真实任务比较 Token、速度和准确率
```

# 八、最终判断

从 Codebase-Memory 应吸收的是：

> **两个产品图谱都先建立持久化、可查询、增量更新的结构模型；Agent 通过少量类型化 MCP 工具读取结构，不再每次重扫全部原始资料。**

不应吸收的是：

> 再新增一个名为 Core、Context 或 Reader 的平级产品。
