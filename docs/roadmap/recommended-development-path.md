# ME-System 推荐开发路径

> 目标：以最小可验证闭环推进 ME-Brain、ME-Who 与 Shared Core，避免先建设大而全知识库。

## 1. 总体开发顺序

推荐主线：

```text
真实项目基线评估
→ Shared Source Ledger
→ ME-Brain 核心 Schema
→ 最小 ME-Who Schema
→ 类型化检索与 MCP
→ Context Compiler
→ 真实 Agent 任务闭环
→ 领域包扩展
→ 人工治理工作台
```

第一阶段资源分配建议：

| 工作 | 比例 |
|---|---:|
| ME-Brain 核心模型与管线 | 45% |
| Shared Core | 25% |
| 最小 ME-Who | 15% |
| Benchmark 与质量评估 | 10% |
| 前端 | 5% |

原因：

- ME-Brain 可以独立产生项目生产力价值；
- ME-Brain 提供最丰富的真实验证场景；
- ME-Who 可以先验证是否降低协作摩擦；
- 前端必须建立在稳定 Schema 和审核流程上。

---

## 2. Phase 0：建立基线与验证语料

### 2.1 选择真实项目

第一批固定三个项目：

1. `lighting-platform`：软件和工程技术开发；
2. Zotero / 论文工作流：科研与文献；
3. AI 超级画板或泰典物业：设计与产品。

### 2.2 建立固定问题集

每个项目至少回答：

- 项目目标和边界是什么；
- 当前阶段是什么；
- 已确认的技术路线和决策是什么；
- 哪些方案已经被替代；
- 当前未完成任务和问题是什么；
- 某一项变更会影响哪些对象；
- 每条高价值结论的来源在哪里；
- 用户在该类任务中有哪些稳定协作要求。

### 2.3 建立四组基线

```text
A. Agent 直接探索全部文件
B. 普通向量 RAG
C. ME-Brain
D. ME-Brain + ME-Who
```

记录：

- 输入 Token；
- 工具调用次数；
- 首次回答延迟；
- 当前状态准确率；
- 过期方案误用率；
- 来源覆盖率；
- 用户纠正次数；
- 首轮结果可用率。

Phase 0 的输出不是产品代码，而是一套可重复运行的评测数据和答案基准。

---

## 3. Phase 1：Shared Core v0.1

### 3.1 Source Ledger

优先支持：

```text
Local File
Git / GitHub
Agent Conversation
Zotero Record
```

统一 SourceEnvelope：

```yaml
source_id:
source_type:
external_id:
created_at:
updated_at:
author:
content_ref:
checksum:
version:
permissions:
metadata:
```

要求：

- 原始内容不可被摘要静默替换；
- 相同内容通过 checksum 去重；
- 文件修改产生新版本，不覆盖旧版本；
- 所有派生对象引用 `source_id`。

### 3.2 Provenance

参考 W3C PROV 的 Entity、Activity、Agent 和 Derivation 概念，至少支持：

```text
wasDerivedFrom
wasGeneratedBy
wasAttributedTo
wasRevisionOf
invalidatedAtTime
```

### 3.3 Temporal Model

统一字段：

```yaml
valid_from:
valid_to:
status:
supersedes:
superseded_by:
recorded_at:
```

必须区分：

- 内容发生时间；
- 系统记录时间；
- 事实有效时间。

### 3.4 Permission Model

第一版角色：

```text
owner
trusted_personal_agent
project_agent
external_agent
public_export
```

权限检查必须发生在检索和 Context Compiler 阶段，而不是只发生在原始文件读取阶段。

### Phase 1 验收条件

- 四类来源可以统一写入；
- 同一来源具有稳定 ID 和版本；
- 任意派生对象能够回溯来源；
- 时间和权限字段可被查询；
- ME-Who 与 ME-Brain 不复制原始内容。

---

## 4. Phase 2：ME-Brain MVP

### 4.1 核心 Schema

第一版只实现：

```text
Project
Workstream
Requirement
Decision
Task
Artifact
Issue
Constraint
Event
SourceReference
```

暂不实现复杂通用知识图谱。

### 4.2 项目结构化流程

```text
Source Ingested
→ Project Classification
→ Deterministic Parsing
→ Candidate Extraction
→ Duplicate / Conflict Check
→ Human or Rule Confirmation
→ Canonical Metadata Update
→ Derived Index Update
```

优先处理用户明确确认的项目结论，而不是追求自动抽取覆盖率。

### 4.3 首批类型化 MCP

```text
get_project_brief
get_current_project_state
list_confirmed_decisions
trace_decision_history
list_open_tasks
list_unresolved_issues
get_recent_changes
get_artifact_lineage
get_evidence
compile_project_context
```

### 4.4 人类可读投影

将权威项目元数据投影为：

```text
projects/<project-slug>/
├── PROJECT.md
├── CURRENT_STATE.md
├── DECISIONS.md
├── OPEN_ISSUES.md
├── ARTIFACTS.md
└── DEVELOPMENT_LOG.md
```

Markdown 是投影和人工审阅层，不是唯一事实库。

### Phase 2 验收条件

- Agent 无需完整读取项目文件即可回答当前状态；
- 已替代方案不会被当成当前结论；
- 所有已确认决策可追溯来源；
- 项目上下文可以按 L1–L5 渐进展开；
- 相比直接文件探索，Token 使用显著下降。

---

## 5. Phase 3：最小 ME-Who MVP

### 5.1 核心 Schema

第一版只实现：

```text
UserFact
BehavioralEvidence
Preference
Capability
CurrentState
CollaborationRule
ProfileSnapshot
```

### 5.2 数据来源

优先使用：

- 用户明确要求系统记住的信息；
- 用户对 Agent 行为的明确反馈；
- 已稳定项目讨论中的协作规则；
- 专业背景与技术环境；
- 用户明确确认的长期偏好。

微信历史数据暂不作为第一版前置条件。

### 5.3 候选治理流程

```text
User Feedback
→ BehavioralEvidence
→ Candidate Preference / Rule
→ Evidence Aggregation
→ User Confirmation
→ Active Personal Context
```

一次行为不能直接生成永久偏好。

### 5.4 首批 MCP

```text
get_explicit_user_facts
get_collaboration_rules
get_relevant_preferences
get_current_user_state
explain_personal_context
submit_behavioral_evidence
list_profile_candidates
confirm_profile_candidate
reject_profile_candidate
compile_personal_context
```

### Phase 3 验收条件

- Agent 能减少对用户已明确内容的重复询问；
- 个人偏好具有明确 Scope；
- 用户可以查看推断证据；
- 用户可以确认、修改、拒绝和禁止使用；
- 项目 Agent 不能读取无关私人信息。

---

## 6. Phase 4：ME-Context Compiler

Context Compiler 是 ME-System 的核心整合层。

### 6.1 输入

```yaml
current_request:
user_id:
project_id:
agent_id:
agent_type:
token_budget:
required_freshness:
evidence_level:
permissions:
```

### 6.2 检索顺序

```text
Task Classification
→ Structured Filter
→ Full-text / BM25
→ Vector Recall
→ Graph Expansion
→ Temporal Filter
→ Permission Filter
→ Rerank
→ Token Allocation
→ Evidence Loading
```

### 6.3 Token 分配

建议初始策略：

```text
Current Request                  必须保留
Project L1/L2 Context            高优先级
Relevant ME-Who Rules            高优先级但严格限量
Entity / Relation Expansion      按需
Evidence Snippets                按验证需求
Full Source                      最后下钻
```

Token 分配应可记录和回放，用于后续优化。

### 6.4 输出可解释性

每个 Context Item 至少包含：

```yaml
content:
context_type:
source_ids:
reason_selected:
confidence:
current_or_historical:
token_cost:
```

### Phase 4 验收条件

- 同一任务能同时组合项目和个人上下文；
- ME-Who 不会改写 ME-Brain 的项目事实；
- Context Pack 可解释每条内容为何被选中；
- 可在不同 Token 预算下生成不同深度的上下文；
- 不同 Agent 能获得不同权限和颗粒度。

---

## 7. Phase 5：领域包

### 7.1 Software Pack

优先实现，吸收 Codebase-Memory：

```text
Repository
Module
Component
Interface
ADR
Issue
PullRequest
Commit
Release
Dependency
Test
```

主要确定性解析：

- Git；
- Tree-Sitter；
- Package manifest；
- Test result；
- Issue / PR API。

### 7.2 Research Pack

```text
ResearchQuestion
Hypothesis
Paper
Citation
Dataset
Method
Experiment
Finding
Limitation
```

主要输入：

- Zotero；
- DOCX；
- 论文元数据；
- 引用；
- 研究记录。

### 7.3 Design Pack

```text
Brief
SiteCondition
Constraint
Option
DesignDecision
Drawing
Model
ReviewComment
Revision
Deliverable
```

主要输入：

- DOCX / PPTX / XLSX；
- 图片；
- BIM / IFC；
- Rhino / Blender；
- 设计评审记录。

每个领域包必须具备独立 Schema、解析器、评测问题和 MCP 扩展，不把全部领域对象塞入 Shared Core。

---

## 8. Phase 6：人工治理工作台

第一版工作台只建设高价值页面：

### ME-Brain

- Project Overview；
- Current State；
- Decision Timeline；
- Artifact Lineage；
- Open Issues；
- Candidate Update Review；
- Context Pack Preview；
- Source Evidence。

### ME-Who

- Explicit Facts；
- Collaboration Rules；
- Profile Candidates；
- Context Usage Audit；
- Profile History。

复杂知识图谱画布、个人数字形象和空间化可视化后置。

---

## 9. 第一阶段技术建议

### 数据层

```text
PostgreSQL
├── core schema
├── me_who schema
├── me_brain schema
├── JSONB
├── full-text search
└── pgvector
```

第一版不同时引入多个图数据库和向量数据库。

### 文件层

- 本地文件系统或 S3 / MinIO；
- 数据库保存引用、哈希、版本和权限；
- 原始文件不可被派生内容覆盖。

### 图层

第一版先使用关系表表达类型化边。只有当真实多跳查询和图算法收益得到验证后，再评估 Graphiti、Kuzu 或 Neo4j。

### 解析层

```text
ParserAdapter
├── Markdown
├── DOCX
├── PPTX
├── XLSX
├── Git
├── Zotero
└── ExternalDocumentService
```

RAGFlow、Docling、MinerU 和 LightRAG 解析器放在适配器之后，保持可替换。

### Agent 接口

- MCP：Agent 主要入口；
- REST：前端和外部应用；
- JSON Schema：接口契约；
- 工具显式标记只读、候选写入、破坏性和幂等性。

---

## 10. 开发纪律

1. 每次新增 Schema 必须附带来源、时间、权限和确认规则；
2. 每次新增检索机制必须与基线对比 Token、速度和准确率；
3. 每个外部竞品组件必须通过 Adapter 接入；
4. 不因演示效果引入不可解释的自动写入；
5. 所有重大技术选择记录 ADR；
6. 每个阶段形成专业开发记录；
7. 已稳定结论与待验证假设在文档中明确区分；
8. 优先实现真实任务闭环，不优先追求图谱节点数量。

---

## 11. 拆仓评估

当前继续使用 Monorepo。满足下列至少三项后重新评估拆仓：

- 两条产品线具有独立团队；
- 发布周期长期分化；
- 开源或许可证策略不同；
- ME-Who 需要独立安全权限；
- Shared Core 协议已稳定；
- 两个产品可以独立运行；
- 单仓 CI 和权限已成为真实阻碍。

---

## 12. 最近的下一步

按照当前阶段，下一轮应依次完成：

1. 编制 `SourceEnvelope`、`ProvenanceRecord` 和 `TemporalValidity` 的 JSON Schema；
2. 编制 ME-Brain v0.1 对象和关系清单；
3. 编制 ME-Who v0.1 对象和 Scope 清单；
4. 定义 Project Context Pack 与 Personal Context Pack；
5. 选定 `lighting-platform` 作为第一个端到端样本；
6. 建立直接文件探索与普通 RAG 的基线测试；
7. 再开始代码脚手架和数据库迁移。
