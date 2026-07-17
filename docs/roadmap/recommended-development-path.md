# ME-System 推荐开发路径

> 目标：先稳定文档信息标准化，再逐项开发 ME-Brain、ME-Who、Hermes 集成、检索和治理功能。

## 1. 总体开发顺序

推荐主线调整为：

```text
Phase 0  标准化验证语料与基线
Phase 1  Source Ledger 与文档身份、版本
Phase 2  Canonical Document Package
Phase 3  首批 Parser Adapter 与质量校验
Phase 4  ME-Brain 领域映射与项目恢复
Phase 5  Hermes 文档和项目上下文接入
Phase 6  最小 ME-Who 与个人协作上下文
Phase 7  混合检索与 Context Compiler
Phase 8  领域包、治理工作台和功能深化
```

第一阶段资源分配建议：

| 工作 | 比例 |
|---|---:|
| 文档信息标准化与 Adapter | 40% |
| Source、版本、来源与质量基础 | 20% |
| ME-Brain 领域映射 | 15% |
| Hermes 集成原型 | 10% |
| Benchmark 与 Golden Corpus | 10% |
| 最小 ME-Who | 5% |

前端、复杂图谱和完整用户画像暂不列入第一阶段重点。

---

## 2. Phase 0：标准化验证语料与基线

### 2.1 真实项目样本

第一批固定三个项目：

1. `lighting-platform`：软件与工程开发；
2. Zotero / 论文工作流：科研与文献；
3. AI 超级画板或泰典物业：设计与产品。

### 2.2 文档样本

至少准备：

- 普通 DOCX；
- 多级标题、表格、图片、脚注和引用的 DOCX；
- Markdown 与项目开发记录；
- Agent 对话导出；
- Zotero 元数据和附件关系；
- PDF、PPTX、XLSX 作为后续格式前置 Schema 样本；
- 同一逻辑文档的多个版本。

### 2.3 Golden Package

每个样本人工确认：

- 文档身份；
- 版本；
- 结构树；
- 正文；
- 表格；
- 图片和附件；
- 来源位置；
- 文档关系；
- 预期质量报告。

### 2.4 基线指标

记录：

- 文本覆盖率；
- 结构正确率；
- 节点顺序正确率；
- 表格结构正确率；
- 资产关联率；
- 来源锚点覆盖率；
- 相同输入幂等率；
- 处理时间；
- 后续检索 Token 使用量。

Phase 0 输出是可重复运行的验证语料和答案标准，不是产品演示。

---

## 3. Phase 1：Source Ledger 与文档身份、版本

### 3.1 SourceAsset

优先支持：

```text
Local File
Git / GitHub
Agent Conversation
Zotero Record
```

统一字段：

```yaml
source_id:
source_type:
external_system:
external_id:
content_ref:
checksum:
created_at:
retrieved_at:
author_or_owner:
permissions:
retention_policy:
```

### 3.2 DocumentIdentity

跨版本稳定表示同一逻辑文档：

```yaml
document_id:
canonical_title:
alternate_titles:
document_kind:
project_id:
owner_entity_id:
status:
```

### 3.3 DocumentVersion

```yaml
version_id:
document_id:
source_id:
checksum:
version_label:
created_at:
valid_from:
valid_to:
previous_version_id:
change_type:
```

### 3.4 Provenance 与时间

至少支持：

```text
wasDerivedFrom
wasGeneratedBy
wasAttributedTo
wasRevisionOf
invalidatedAtTime
```

必须区分：

- 来源产生时间；
- 系统记录时间；
- 文档版本时间；
- 领域事实有效时间。

### Phase 1 验收条件

- 来源和文档身份分离；
- 同一逻辑文档的新版本不会生成新 `document_id`；
- 原始资料不可覆盖；
- 任意版本可以回溯来源；
- 相同来源重复处理不生成重复记录。

---

## 4. Phase 2：Canonical Document Package

以 `docs/specs/document-information-standardization-v0.1.md` 为设计基线。

### 4.1 包结构

```text
document-package/
├── manifest.json
├── structure.json
├── content.jsonl
├── assets/
├── relations.jsonl
├── provenance.jsonl
├── semantic-candidates.jsonl
├── quality-report.json
└── projections/document.md
```

### 4.2 核心 Schema

第一批定义：

```text
CanonicalDocumentPackage
DocumentManifest
ContentNode
SourceAnchor
AssetRecord
RelationRecord
SemanticCandidate
QualityReport
```

### 4.3 通用节点

```text
document
section
heading
paragraph
list
list_item
table
table_row
table_cell
figure
caption
quote
code_block
equation
footnote
citation
comment
attachment
page_break
unknown_block
```

### 4.4 ID 与幂等

```text
src_      原始来源
doc_      逻辑文档
docv_     文档版本
node_     内容节点
asset_    文档资产
rel_      关系
cand_     语义候选
activity_ 处理活动
```

### Phase 2 验收条件

- JSON Schema 校验通过；
- 所有节点具有稳定顺序；
- 高价值节点具有来源锚点；
- 无法识别内容进入 `unknown_block` 或质量缺口；
- 包可导入、导出和重新生成；
- Markdown 投影可以回看标准化结果。

---

## 5. Phase 3：Parser Adapter 与质量校验

### 5.1 Adapter 契约

```text
supports(source)
inspect(source)
parse(source)
normalize(parsed_result)
extract_assets(parsed_result)
build_anchors(parsed_result)
validate(package, source)
```

### 5.2 P0 Adapter

首批实现：

```text
Markdown / Plain Text
DOCX
Agent Conversation Export
Git Repository Documents
Zotero Metadata Record
```

### 5.3 P1 Adapter

完成 P0 后逐项开发：

```text
PDF
PPTX
XLSX / CSV
HTML / Web Archive
Email
```

### 5.4 外部能力接入

通过 Adapter 对比：

- RAGFlow；
- Docling；
- MinerU；
- 自研确定性解析；
- LightRAG 多模态解析能力。

任何外部解析器都不能直接定义权威文档格式。

### 5.5 质量门槛

P0 建议目标：

| 指标 | 目标 |
|---|---:|
| 文本覆盖率 | ≥ 99% |
| 节点顺序正确率 | ≥ 99% |
| 来源锚点覆盖率 | ≥ 95% |
| 表格结构正确率 | ≥ 95% |
| 资产关联率 | ≥ 95% |
| 来源完整率 | 100% |
| 相同输入幂等率 | 100% |

以上为开发目标，不代表当前实现结果。

### Phase 3 验收条件

- 三类以上 P0 输入能生成标准包；
- `partial`、`failed`、`quarantined` 状态可区分；
- 无静默丢失；
- 质量报告可定位具体缺口；
- 更换 Adapter 不影响上层领域接口。

---

## 6. Phase 4：ME-Brain 领域映射与项目恢复

标准文档包完成后，再建立领域对象。

### 6.1 第一批对象

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

### 6.2 候选流程

```text
ContentNode
→ SemanticCandidate
→ Project Classification
→ Duplicate / Conflict Check
→ Rule or Human Confirmation
→ ME-Brain Canonical Domain Data
```

### 6.3 首批查询

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

### 6.4 人类可读投影

```text
projects/<project-slug>/
├── PROJECT.md
├── CURRENT_STATE.md
├── DECISIONS.md
├── OPEN_ISSUES.md
├── ARTIFACTS.md
└── DEVELOPMENT_LOG.md
```

Markdown 是投影和审核层，不是唯一事实库。

### Phase 4 验收条件

- 项目决策可以定位到文档节点和原始来源；
- 已替代方案不会被当成当前结论；
- Hermes 或 Agent 无需完整读取文件即可恢复项目；
- 项目状态与原文件版本变化可增量更新；
- 相比直接文件探索，Token 使用明显下降。

---

## 7. Phase 5：Hermes 接入

Hermes 是第一阶段主要消费者，但不与具体解析器耦合。

### 7.1 文档证据接口

```text
get_document_manifest
describe_document_structure
get_document_nodes
get_node_evidence
get_document_version_history
get_document_quality_report
```

### 7.2 项目上下文接口

```text
get_project_brief
get_current_project_state
get_confirmed_decisions
get_active_constraints
get_open_issues
compile_project_context
```

### 7.3 Execution Handoff Pack

Hermes 向 Codex 或 OpenClaw 派发：

```yaml
objective:
scope:
inputs:
confirmed_decisions:
constraints:
deliverables:
acceptance_criteria:
forbidden_changes:
evidence_refs:
reporting_requirements:
```

### 7.4 写入边界

Hermes 只允许直接写入：

- 查询和使用日志；
- 临时任务状态；
- 文档注释候选；
- 领域更新候选。

正式项目决策、研究结论和稳定用户偏好必须经过规则或人工确认。

### Phase 5 验收条件

- Hermes 能快速恢复一个项目；
- Hermes 可以下钻到准确原文；
- Hermes 派发的任务包含已确认约束和证据；
- 执行 Agent 不需要直接读取全部知识库；
- 候选写入不会污染权威数据。

---

## 8. Phase 6：最小 ME-Who

第一版只解决 Hermes 协作效率，不追求数字人格。

### 8.1 核心对象

```text
UserFact
BehavioralEvidence
Preference
Capability
CurrentState
CollaborationRule
ProfileSnapshot
```

### 8.2 优先信息

- 用户明确要求记住的事实；
- 用户对 Agent 行为的明确反馈；
- 已稳定的协作规则；
- 专业背景和技术环境；
- 不同任务的 Agent 自主度要求。

### 8.3 标准化来源

ME-Who 同样只从标准文档节点、对话节点和明确来源中生成候选证据。

```text
Standardized Conversation / Document Node
→ BehavioralEvidence
→ Candidate Preference / Rule
→ Evidence Aggregation
→ User Confirmation
→ Active Personal Context
```

### Phase 6 验收条件

- Hermes 减少重复询问；
- 协作规则具有明确 Scope；
- 用户可查看、确认、修改或拒绝候选；
- 项目 Agent 不能访问无关私人信息；
- ME-Who 不修改 ME-Brain 项目事实。

---

## 9. Phase 7：混合检索与 Context Compiler

检索机制在标准化和领域事实稳定后引入。

### 9.1 检索顺序

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

### 9.2 竞品吸收

- Codebase-Memory：结构先行、渐进式上下文和低 Token；
- LightRAG：全文、向量和图混合检索；
- Graphiti：时间、Episode 和来源关系；
- Glean：高价值实体与信号网络；
- Basic Memory：MCP 和人类可读投影。

每个机制独立 Benchmark，不一次性引入全部组件。

### 9.3 Context Item

```yaml
content:
context_type:
source_ids:
document_node_ids:
reason_selected:
confidence:
current_or_historical:
token_cost:
```

### Phase 7 验收条件

- 同一任务可以组合项目和个人上下文；
- 每条上下文可解释为何被选择；
- 不同 Token 预算生成不同深度；
- 过期事实明确排除；
- 标准化节点与原文件可以双向定位。

---

## 10. Phase 8：领域包与功能逐项深化

### 10.1 Software Pack

吸收 Codebase-Memory：

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

### 10.2 Research Pack

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

重点输入：Zotero、PDF、DOCX、引用、实验记录。

### 10.3 Design Pack

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

重点输入：DOCX、PPTX、XLSX、图片、IFC、Rhino / Blender 元数据和评审记录。

### 10.4 人工治理工作台

后续逐项建设：

- 文档标准化质量检查；
- 未解析区域复核；
- 文档版本差异；
- Candidate Update Review；
- Decision Timeline；
- Artifact Lineage；
- ME-Who Profile Candidates；
- Context Pack Preview；
- Context Usage Audit。

复杂图谱画布、个人数字形象和空间化可视化继续后置。

---

## 11. 竞品吸收纪律

每个功能专题开始前必须形成独立分析：

```text
目标问题
→ 对应竞品
→ 应吸收能力
→ 不应照搬部分
→ 自研 / Adapter / 直接依赖选择
→ Benchmark
→ 实现规格
→ 验收指标
```

原则：

1. 不直接 Fork 一个大平台作为 ME-System；
2. 不让竞品的数据模型成为权威标准；
3. 不因演示效果牺牲来源和质量；
4. 每次新增检索机制都与基线比较 Token、速度和准确率；
5. 每个外部组件通过 Adapter 接入；
6. 每个重大选择记录 ADR；
7. 每阶段形成专业开发记录。

---

## 12. 第一阶段技术建议

### 数据层

```text
PostgreSQL
├── core schema
├── document schema
├── me_brain schema
├── me_who schema
├── JSONB
├── full-text search
└── pgvector
```

第一版不同时引入多个图数据库和向量数据库。

### 文件层

- 本地文件系统或 S3 / MinIO；
- 数据库保存引用、哈希、版本和权限；
- 原文件和文档资产不可被派生内容覆盖。

### 图层

第一版先用关系表表达类型化边。多跳查询收益得到验证后，再评估 Graphiti、Kuzu 或 Neo4j。

### Agent 接口

- MCP：Hermes 和 Agent 主要入口；
- REST：前端和外部应用；
- JSON Schema：数据和接口契约；
- 工具显式标记只读、候选写入、破坏性和幂等性。

---

## 13. 拆仓评估

当前继续使用 Monorepo。满足下列至少三项后重新评估拆仓：

- 两条产品线具有独立团队；
- 发布周期长期分化；
- 开源或许可证策略不同；
- ME-Who 需要独立安全权限；
- Shared Core 和文档标准协议已稳定；
- 两个产品可以独立运行；
- 单仓 CI 和权限成为真实阻碍。

---

## 14. 最近的下一步

按照当前阶段，下一轮依次完成：

1. 编制 `CanonicalDocumentPackage` JSON Schema；
2. 编制 `ContentNode`、`SourceAnchor`、`AssetRecord` 和 `QualityReport` Schema；
3. 建立第一批 Golden Corpus；
4. 编制 Parser Adapter 接口；
5. 先实现 Markdown / Plain Text Adapter；
6. 再实现 DOCX Adapter；
7. 实现 Agent Conversation Adapter；
8. 建立 Markdown 投影和质量报告；
9. 验证文档版本、幂等和来源定位；
10. 完成后再进入 ME-Brain 领域映射。
