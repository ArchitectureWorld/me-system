# ME-Reader P0：Agent 精阅读与双向链接规格 v0.1

> 状态：设计稳定稿  
> 日期：2026-07-17  
> 适用范围：第一实现梯队

## 1. 目标

本规格定义 ME-Reader 第一实现梯队的最小完整闭环：

```text
Hermes 阅读任务
→ 文档解析与原文锚点
→ Agent 章节级精阅读
→ Claim–Evidence–Context
→ 双向链接
→ Reviewer 复核
→ Obsidian 人工审核
→ ME-Brain 候选入库
```

P0 必须同时验证两项核心能力：

1. Agent 能否稳定、可复核地精读文献；
2. 阅读结果能否与原文和其他知识对象保持稳定双向链接。

## 2. 非目标

P0 不承担：

- 完整独立阅读 App；
- 多用户协作；
- 全自动综述生成；
- 大规模图数据库；
- 所有文档格式；
- 扫描件 OCR；
- 复杂公式推导；
- 无人工确认的权威知识写入。

## 3. P0 输入

### 3.1 文献输入

```yaml
source_type: zotero_item
zotero_item_key:
zotero_attachment_key:
citation_key:
attachment_path:
metadata:
  title:
  authors:
  year:
  publication:
  doi:
```

第一版只要求支持具有文本层的学术 PDF。

### 3.2 阅读请求

```yaml
reading_request:
  requested_by: hermes_personal_assistant
  mode: deep_reading
  goals: []
  focus_sections: []
  project_context_refs: []
  output_requirements:
    - paper_record
    - claims
    - evidence
    - relations
    - review
```

用户未明确阅读目标时，Hermes 可以使用通用精读目标，但必须在任务记录中标识为默认目标。

## 4. Reading Job 状态机

```text
created
→ inspecting
→ parsing
→ planning
→ reading
→ linking
→ reviewing
→ awaiting_human_review
→ confirmed / rejected / partial
```

异常状态：

```text
needs_input
paused
failed
quarantined
cancelled
```

每个阶段必须可幂等重试，不得因单个章节失败而丢失已完成结果。

## 5. 文档解析

### 5.1 ContentNode

```yaml
node_id:
document_id:
version_id:
node_type:
order:
section_path: []
text:
page_number:
source_anchor_id:
```

首批节点类型：

```text
document
section
heading
paragraph
list
list_item
table
figure
caption
equation
citation
footnote
unknown_block
```

### 5.2 SourceAnchor

```yaml
source_anchor_id:
document_id:
version_id:
page_number:
section_path: []
text_quote:
text_hash:
context_before:
context_after:
bbox:
  x:
  y:
  width:
  height:
source_uri:
```

定位策略必须同时使用稳定 ID、文本哈希、上下文和页面位置，不能只依赖页码。

## 6. 阅读计划

Reader 在正式精读前生成：

```yaml
reading_plan:
  document_type:
  research_type:
  priority_sections: []
  questions_to_answer: []
  evidence_types_to_collect: []
  risk_points: []
  skipped_sections: []
  skip_reasons: []
```

P0 至少区分：

- 实证研究；
- 方法论文；
- 综述论文；
- 理论或观点论文；
- 无法可靠分类。

无法分类时使用通用文档阅读策略，并在 Review 中标记风险。

## 7. 章节级精读

每个章节独立生成：

```yaml
section_reading:
  section_id:
  purpose:
  key_points: []
  entities: []
  methods: []
  datasets: []
  metrics: []
  claims: []
  evidence_refs: []
  uncertainties: []
  reader_notes: []
```

章节级结果必须保存，论文级综合不得绕过章节结果直接重新总结全文。

## 8. Claim–Evidence–Context

### 8.1 Claim

```yaml
claim_id:
paper_id:
claim_text:
claim_type:
origin:
importance:
status: candidate
created_by:
```

`origin` 允许值：

```text
author_claim
experimental_result
cited_background
user_inference
agent_inference
```

### 8.2 Evidence

```yaml
evidence_id:
evidence_type:
source_anchor_ids: []
page_number:
section_path: []
locator:
quote:
numeric_values: {}
extraction_confidence:
```

`evidence_type` 至少支持：

```text
paragraph
table
figure
equation
statistical_result
citation
```

### 8.3 Context

```yaml
context_id:
claim_id:
research_object:
dataset:
sample:
time_scope:
region_scope:
conditions: []
metrics: []
baselines: []
limitations: []
```

任何比较性、数值性或因果性 Claim 均必须尽可能保留评价指标和适用条件。

## 9. 论文内部关系

P0 至少支持：

```text
research_question tested_by experiment
experiment uses method
experiment uses dataset
experiment produces result
result supports claim
claim supported_by evidence
claim limited_by limitation
claim discusses citation
```

关系格式：

```yaml
relation_id:
source_id:
predicate:
target_id:
direction: bidirectional_query
confidence:
created_by:
review_status:
```

`bidirectional_query` 表示关系可以从源和目标两端检索，不表示所有谓词语义对称。

## 10. Obsidian 投影

### 10.1 Vault 建议结构

```text
me-brain-vault/
├── papers/
├── claims/
├── evidence/
├── methods/
├── topics/
├── projects/
├── reading-jobs/
└── templates/
```

### 10.2 Paper Note Frontmatter

```yaml
---
mebrain_id:
document_id:
zotero_item_key:
zotero_attachment_key:
citation_key:
pdf_uri:
reading_job_id:
reading_status:
review_status:
---
```

### 10.3 内容分区

```markdown
# 论文题目

## 人工笔记

<!-- USER-CONTENT:START -->
<!-- USER-CONTENT:END -->

## Agent 精读

<!-- AGENT-CONTENT:START -->
<!-- AGENT-CONTENT:END -->

## Claim 与证据

## 关联对象

## 待复核
```

Agent 只允许更新 Agent 管理区和结构化对象文件，不得覆盖人工区。

## 11. Zotero 回跳

至少支持：

```text
zotero://select/library/items/<ITEM_KEY>
zotero://open-pdf/library/items/<ATTACHMENT_KEY>?page=<PAGE>
```

若需要坐标级定位，允许通过本地跳转服务：

```text
http://<local-reader-service>/open/evidence/<EVIDENCE_ID>
```

本规格不固定服务地址、IP 或端口；部署信息必须由项目控制文档统一管理。

## 12. Hermes 工具接口

### 12.1 创建阅读任务

```text
create_deep_reading_job
```

输入：文献标识、附件、阅读目标、项目上下文引用。  
输出：`reading_job_id` 和初始状态。

### 12.2 查询任务

```text
get_reading_job_status
get_reading_plan
get_section_reading
get_reading_result
get_review_issues
```

### 12.3 人工反馈

```text
confirm_claim
reject_claim
edit_claim
request_more_evidence
request_section_reread
```

写入操作必须记录操作者、时间、修改前后值和来源。

## 13. Reviewer 检查项

Reviewer 至少检查：

1. 高重要度 Claim 是否有 Evidence；
2. Evidence 是否实际支持 Claim；
3. 页码、章节和图表定位是否一致；
4. 数值与单位是否正确；
5. 本文观点和引用观点是否混淆；
6. 相关性是否被错误表述为因果性；
7. 局部实验是否被泛化；
8. Agent 推论是否明确标记；
9. 负面结果和限制是否遗漏；
10. 论文级综合是否能追溯到章节结果。

## 14. 人工审核状态

```text
pending
confirmed
rejected
edited
needs_more_evidence
needs_reread
superseded
```

只有 `confirmed` 或经明确规则批准的对象可以进入 ME-Brain 权威领域数据层。

## 15. P0 验收指标

### 15.1 结构与定位

- 主要章节识别正确率达到可人工使用水平；
- 高价值节点 SourceAnchor 覆盖率目标 ≥ 95%；
- 所有高重要度 Claim 至少绑定一个 Evidence；
- Evidence 可返回正确页码和对应原文。

### 15.2 阅读准确性

- 作者主张、实验结果、引用观点和 Agent 推论明确区分；
- 数值性 Claim 保留指标和条件；
- Reviewer 能发现明显过度推断；
- 人工审核无需重新完整阅读即可判断主要 Claim。

### 15.3 链接稳定性

- Obsidian 文件改名或移动不改变核心对象 ID；
- Paper、Claim、Evidence 和 SourceAnchor 可正反向查询；
- Zotero 文献与 Obsidian Paper Note 可以互相定位；
- 文档新版本不会静默覆盖旧版本锚点。

### 15.4 Agent 集成

- Hermes 可以创建、查询、暂停和恢复任务；
- 子 Agent 的结果不污染个人助理通用上下文；
- 阅读任务可针对项目目的注入 ME-Brain 上下文；
- 失败阶段可以重试而不重复生成已确认对象。

## 16. Golden Corpus

P0 至少建立：

- 3 篇中文实证论文；
- 3 篇英文实证论文；
- 2 篇方法论文；
- 2 篇综述论文；
- 包含表格、图、公式和复杂参考文献的样本；
- 每篇人工标注章节、关键 Claim、Evidence、Context 和原文位置。

Golden Corpus 用于比较：

```text
全文一次性总结
vs.
章节级 Reader
vs.
Reader + Reviewer
```

比较指标包括准确性、证据覆盖、遗漏率、Token、处理时间和人工审核时间。

## 17. 完成定义

P0 在以下完整演示通过后完成：

1. 用户从 Hermes 或 Obsidian 选择一篇 Zotero 文献；
2. 用户提出具体精读目标；
3. Hermes 创建 Deep Reading Job；
4. Reader 完成阅读计划和章节精读；
5. Linker 生成 Claim–Evidence–Context 与双向关系；
6. Reviewer 生成复核结果；
7. Obsidian 展示阅读报告、反向链接和待审核对象；
8. 用户点击 Evidence 返回 Zotero PDF；
9. 用户确认或驳回 Claim；
10. 确认对象进入 ME-Brain，并可被 Hermes 再次调用。
