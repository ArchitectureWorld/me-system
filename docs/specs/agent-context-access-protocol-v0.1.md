# Agent Context Access Protocol v0.1

> 状态：设计基线，进入实现前评审  
> 日期：2026-07-22  
> 适用范围：Hermes、Pi、Codex、OpenClaw 及后续 Agent Adapter

## 1. 目标

本协议定义 Agent 如何使用 ME-System 中的标准化文档、ME-Brain 项目知识和 ME-Who 用户上下文。

它解决的不是“Agent 是否能搜索文本”，而是：

- Agent 如何声明自己、任务与权限；
- 如何在有限 Token 预算下取得正确层级的上下文；
- 如何区分当前事实、历史事实、推断和候选；
- 如何从摘要下钻到文档节点和原始证据；
- 如何把执行结果提交为候选更新；
- 如何让 Hermes、Pi 等不同 Agent 使用相同语义协议；
- 如何记录上下文使用和数据暴露情况。

## 2. 核心原则

1. **传输无关**：MCP、REST、SDK 和进程内调用共享同一语义契约。
2. **Agent 不读数据库**：所有访问经过权限、时间和范围过滤。
3. **先编译、后下钻**：默认返回任务相关 Context Pack，而不是搜索结果堆叠。
4. **结构优先**：优先项目状态、决策、约束和文档结构，再装载原文。
5. **证据可寻址**：每条高价值内容都提供稳定证据句柄。
6. **权威级别显式**：确认事实、候选、推断和历史内容不得混写。
7. **个人信息最小暴露**：ME-Who 只返回当前 Agent 完成任务所需部分。
8. **写入先候选**：Agent 不直接修改权威领域数据。
9. **所有调用可审计**：记录谁在什么任务中取得了哪些上下文。
10. **工具面保持收敛**：优先少量类型化工具，避免向模型暴露庞大工具集合。

## 3. 逻辑架构

```text
Agent Request
    │
    ▼
Agent Adapter
Hermes MCP / Pi Extension / REST SDK
    │
    ▼
Agent Context Gateway
├── Authentication
├── Agent Identity
├── Scope Resolution
├── Permission Filter
├── Task Classification
├── Context Compiler
├── Evidence Resolver
├── Candidate Write-back
└── Usage Audit
    │
    ├── Canonical Document Store
    ├── ME-Brain Canonical Store
    ├── ME-Who Canonical Store
    └── Derived Retrieval Indexes
```

## 4. Agent 身份与权限上下文

每次请求必须带有不可由模型自由伪造的 `AgentPrincipal`。传输 Adapter 负责从配置或凭据中注入，不接受模型文本声明覆盖。

```yaml
principal_id: principal_...
agent_id: hermes-primary
agent_type: hermes
role: trusted_personal_agent
user_id: user_...
allowed_project_ids:
  - project_lighting
allowed_scopes:
  - me_brain:read
  - me_who:task_relevant
  - evidence:read
  - candidate:write
session_id: session_...
credential_id: cred_...
```

### Role v0.1

```text
owner
trusted_personal_agent
project_agent
external_agent
public_client
```

### 默认策略

- Hermes：`trusted_personal_agent`；
- Pi：`project_agent`；
- Codex：`project_agent`；
- 未登记客户端：拒绝访问；
- 角色只决定最大权限，实际结果还要经过项目、任务、敏感度和字段级过滤。

## 5. TaskContextRequest

所有动态上下文请求统一使用：

```yaml
schema_version: agent-context-request/0.1
request_id: req_...
principal_id: principal_...
session_id: session_...
task:
  task_id: task_...
  title: 整理 lighting-platform 材料参数数据结构
  description: 在不修改既定技术路线的情况下形成数据结构建议
  task_type: technical_design
  intended_action: analyze_and_propose
scope:
  user_id: user_...
  project_id: project_lighting
  workstream_id: workstream_data_model
  document_ids: []
constraints:
  token_budget: 6000
  max_items: 30
  required_freshness: current
  evidence_level: key_claims
  include_personal_context: true
  include_historical_context: false
  language: zh-CN
output:
  format: structured_json
  progressive_depth: L2
  include_drilldown_handles: true
```

### task_type v0.1

```text
project_resume
fact_lookup
technical_design
research_analysis
design_analysis
implementation
review
planning
writing
personal_assistance
other
```

### intended_action v0.1

```text
read_only
analyze
analyze_and_propose
execute
review
handoff
```

### required_freshness

```text
current
current_plus_recent_history
all_history
as_of_time
```

### evidence_level

```text
none
key_claims
all_claims
full_trace
```

## 6. AgentContextPack

```yaml
schema_version: agent-context-pack/0.1
context_pack_id: ctx_...
request_id: req_...
generated_at: 2026-07-22T08:00:00Z
expires_at: 2026-07-22T09:00:00Z
scope:
  user_id: user_...
  project_id: project_lighting
  task_id: task_...
principal:
  agent_id: hermes-primary
  role: trusted_personal_agent
budget:
  requested_tokens: 6000
  estimated_tokens: 4380
  truncated: false
project_context:
  project_brief: []
  current_state: []
  confirmed_decisions: []
  active_constraints: []
  open_issues: []
  recent_changes: []
personal_context:
  relevant_background: []
  collaboration_rules: []
  autonomy_policy: []
  communication_preferences: []
document_context:
  relevant_documents: []
  outlines: []
  evidence_snippets: []
execution_policy:
  allowed_actions: []
  confirmation_required: []
  forbidden_changes: []
quality:
  completeness: 0.91
  unresolved_conflicts: []
  warnings: []
audit:
  selection_policy_version: context-compiler/0.1
  permission_policy_version: permissions/0.1
```

## 7. ContextItem

Context Pack 中的各项内容统一表示为 `ContextItem`：

```yaml
item_id: citem_...
context_type: confirmed_decision
title: 第一阶段仅考虑人工照明
content: 第一阶段的照明计算范围仅包含人工照明，不处理自然采光。
authority:
  level: canonical
  confirmation_status: human_confirmed
confidence: 1.0
temporal:
  status: current
  valid_from: 2026-07-14T00:00:00Z
  valid_to: null
scope:
  project_id: project_lighting
  domain: lighting
sensitivity: project_private
source_refs:
  - source_id: src_...
    document_id: doc_...
    version_id: docv_...
    node_id: node_...
reason_selected: 当前任务涉及计算范围约束
token_cost: 42
drilldown:
  resource_uri: me://documents/doc_.../versions/docv_.../nodes/node_...
```

### authority.level

```text
canonical
rule_confirmed
human_confirmed
candidate
inference
raw_evidence
```

### temporal.status

```text
current
historical
superseded
future_planned
unknown
```

## 8. 上下文深度

| 深度 | 内容 | 使用方式 |
|---|---|---|
| L0 | 仅身份、项目和工具说明 | Bootstrap |
| L1 | 项目目标、阶段和当前状态 | 快速恢复 |
| L2 | 决策、约束、问题、协作规则 | 默认任务上下文 |
| L3 | 实体、关系、文档大纲和相关事件 | 深入分析 |
| L4 | 证据片段、表格、图片和引用 | 核验与修改 |
| L5 | 完整文档版本或原始资产 | 最后下钻 |

Adapter 不得在启动时默认注入 L3—L5。

## 9. 核心工具语义

第一版建议只向 Agent 暴露以下工具。

### 9.1 `me_resolve_scope`

用途：根据自然语言、路径或外部 ID 解析项目、文档和工作流范围。

输入：

```yaml
query: lighting-platform
hints:
  working_directory: /workspace/lighting-platform
```

输出：

```yaml
project_id: project_lighting
confidence: 0.99
alternatives: []
```

### 9.2 `me_compile_context`

用途：针对任务生成 `AgentContextPack`。

输入：`TaskContextRequest`。

输出：`AgentContextPack`。

### 9.3 `me_get_project_state`

用途：快速读取项目 L1/L2，不触发完整语义搜索。

### 9.4 `me_get_document_outline`

用途：读取文档结构树、章节标题、表格和资产索引，不返回完整正文。

### 9.5 `me_search_content`

用途：在已授权范围内进行结构、全文和语义混合检索。

输入必须支持：

```yaml
query:
project_id:
document_ids: []
node_types: []
temporal_filter:
max_results:
```

### 9.6 `me_get_evidence`

用途：通过稳定句柄读取原文节点、表格、资产或来源位置。

### 9.7 `me_create_handoff_pack`

用途：Hermes 等协调 Agent 为 Pi、Codex 或 OpenClaw 创建受限执行交接包。

### 9.8 `me_get_handoff_pack`

用途：执行 Agent 按 ID 获取已授权交接内容。

### 9.9 `me_submit_candidate_update`

用途：提交候选项目事实、用户证据、文档关系或任务结果。

### 9.10 `me_explain_context`

用途：解释某一 Context Item 为什么被选择、来自哪里、是否过期以及谁有权查看。

## 10. ExecutionHandoffPack

用于 Hermes 向 Pi、Codex 或其他执行 Agent 交接任务。

```yaml
schema_version: execution-handoff-pack/0.1
handoff_id: handoff_...
created_by: hermes-primary
assigned_to:
  agent_id: pi-development
  role: project_agent
project_id: project_lighting
task:
  objective: 实现材料参数 Schema 原型
  scope: 仅新增 Schema 和测试
  deliverables:
    - JSON Schema
    - 单元测试
    - 开发记录
context_items: []
constraints:
  confirmed_decisions: []
  forbidden_changes:
    - 不改变 Radiance 主计算路线
  confirmation_required:
    - 修改 IFC 优先输入策略
acceptance_criteria: []
evidence_refs: []
writeback_policy:
  mode: candidate_only
  allowed_candidate_types:
    - implementation_result
    - issue
    - proposed_decision
expires_at: 2026-07-23T08:00:00Z
```

### 交接原则

- 执行 Agent 默认不需要读取完整 ME-Who；
- Hermes 可以把必要协作要求显式放入交接包；
- 交接包内容冻结并可审计，避免执行期间上下文悄然变化；
- 需要新信息时，执行 Agent通过受限工具继续下钻；
- 交接包过期后必须重新生成或续期。

## 11. EvidenceRef 与资源 URI

```yaml
source_id: src_...
document_id: doc_...
version_id: docv_...
node_id: node_...
asset_id: null
source_anchor:
  type: docx_paragraph
  value:
    paragraph_index: 42
resource_uri: me://documents/doc_.../versions/docv_.../nodes/node_...
```

### URI v0.1

```text
me://projects/{project_id}
me://projects/{project_id}/state
me://documents/{document_id}
me://documents/{document_id}/versions/{version_id}
me://documents/{document_id}/versions/{version_id}/outline
me://documents/{document_id}/versions/{version_id}/nodes/{node_id}
me://assets/{asset_id}
me://context-packs/{context_pack_id}
me://handoff-packs/{handoff_id}
me://candidates/{candidate_id}
```

URI 是稳定逻辑句柄，不等于文件系统路径或数据库主键暴露。

## 12. CandidateUpdate

```yaml
schema_version: candidate-update/0.1
candidate_id: cand_...
submitted_by:
  agent_id: pi-development
  principal_id: principal_...
session_id: session_...
task_id: task_...
target:
  domain: me_brain
  object_type: proposed_decision
  project_id: project_lighting
operation: create
payload:
  title: 材料参数采用单位显式字段
  description: 所有材料参数数值同时保存 unit 字段
reason: 实现 Schema 时发现仅保存数值会造成跨引擎歧义
evidence_refs: []
confidence: 0.84
confirmation_status: unreviewed
created_at: 2026-07-22T08:00:00Z
```

Adapter 必须明确告知 Agent：提交成功不表示候选已成为权威事实。

## 13. UsageAuditRecord

```yaml
audit_id: audit_...
principal_id: principal_...
agent_id: hermes-primary
session_id: session_...
task_id: task_...
action: compile_context
requested_scope:
  project_id: project_lighting
returned_item_ids: []
redacted_item_count: 3
token_estimate: 4380
started_at: 2026-07-22T08:00:00Z
completed_at: 2026-07-22T08:00:01Z
status: success
```

审计日志不得默认记录完整敏感正文，只记录句柄、范围和策略结果。

## 14. 错误模型

统一返回：

```yaml
error:
  code: CONTEXT_SCOPE_AMBIGUOUS
  message: 无法唯一确定项目
  retryable: true
  details:
    alternatives: []
  request_id: req_...
```

### 错误码 v0.1

```text
AUTHENTICATION_REQUIRED
PERMISSION_DENIED
CONTEXT_SCOPE_AMBIGUOUS
PROJECT_NOT_FOUND
DOCUMENT_NOT_FOUND
VERSION_NOT_FOUND
NODE_NOT_FOUND
CONTEXT_BUDGET_TOO_SMALL
CONTEXT_PARTIAL
PARSER_OUTPUT_UNAVAILABLE
EVIDENCE_UNAVAILABLE
HANDOFF_EXPIRED
CANDIDATE_TYPE_NOT_ALLOWED
RATE_LIMITED
SERVICE_UNAVAILABLE
INTERNAL_ERROR
```

部分成功必须使用 `CONTEXT_PARTIAL` 并返回已取得内容和缺失清单，不得静默丢失。

## 15. 降级策略

### ME-System 暂时不可用

- Adapter 返回明确错误；
- Agent 可以继续处理用户直接提供的材料；
- 不得假装已经读取项目记忆；
- 不得将本次临时推断当成已有权威事实。

### ME-Who 不可用

- 返回 ME-Brain 上下文；
- `personal_context_status=unavailable`；
- Agent 使用默认协作策略。

### 派生索引不可用

- 优先退回结构化查询和全文检索；
- 不影响 Canonical Data 和 EvidenceRef 读取。

## 16. Token 策略

Token 预算按以下顺序分配：

1. 用户当前请求；
2. 当前项目状态；
3. 已确认决策与禁止变更；
4. 当前任务相关约束和问题；
5. 少量相关协作规则；
6. 文档结构与相关节点；
7. 核心证据片段；
8. 历史、关系扩展和完整原文。

任何截断都必须在 `budget.truncated` 和 `quality.warnings` 中显式表达。

## 17. Adapter 合规要求

Hermes、Pi 或其他 Adapter 必须：

- 注入真实 AgentPrincipal；
- 保留请求与响应 Schema；
- 不把候选标记成权威事实；
- 不缓存超过 `expires_at` 的 Context Pack；
- 不绕过权限过滤；
- 向模型展示错误和部分结果；
- 支持证据下钻；
- 记录工具调用与 Context Pack ID；
- 不把完整 ME-Who 默认暴露给项目执行 Agent。

## 18. v0.1 验收条件

1. Hermes 与 Pi 对同一请求可获得语义一致的 Context Pack；
2. Hermes 可创建受限 Handoff Pack，Pi 可读取并执行；
3. Pi 默认无法获取无关 ME-Who 内容；
4. Agent 可从项目摘要下钻到具体文档节点；
5. 每条确认决策都能解释来源和有效状态；
6. Agent 提交的更新只进入候选区；
7. Token 截断、部分失败和权限过滤均显式报告；
8. 所有访问可通过 AuditRecord 回放范围和结果句柄。