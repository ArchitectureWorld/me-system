# 文档信息标准化规范 v0.1

> 状态：设计基线，进入实现前评审  
> 日期：2026-07-17  
> 适用范围：ME-System Shared Core、ME-Brain、ME-Who、Hermes Adapter

## 1. 目标

本规范定义 ME-System 如何把异构来源转换为统一、可追溯、可验证和可增量更新的文档信息结构。

文档标准化的目的不是把所有文件转换成纯文本，而是完整表达：

- 文档身份与版本；
- 原始文件和外部来源；
- 标题、章节、段落、列表、表格、图片、公式、引用等结构；
- 内容在原文中的稳定位置；
- 附件和嵌入资产；
- 文档之间及内容节点之间的关系；
- 解析过程、工具版本、质量和缺失内容；
- 后续 ME-Brain 与 ME-Who 领域对象的证据定位。

标准化结果必须能同时支持：

1. Agent 快速检索；
2. Hermes 按需下钻证据；
3. ME-Brain 建立项目元数据；
4. ME-Who 建立用户证据候选；
5. 人工复核和纠错；
6. 解析器替换与重新处理；
7. Token、速度、准确率和来源覆盖率评测。

---

## 2. 非目标

v0.1 不负责：

- 自动判定所有项目事实；
- 自动建立完整知识图谱；
- 自动确认用户稳定偏好；
- 统一所有科研、设计和软件领域本体；
- 直接生成最终 Context Pack；
- 取代原文件或原业务系统；
- 保证所有复杂格式一次解析完全正确。

文档标准化层只负责建立可靠、通用的中间表达和证据定位。

---

## 3. 总体分层

文档处理采用六个阶段，使用 `D0`—`D5` 命名，避免与 ME-System 的数据层编号混淆。

```text
D0 Raw Source
原始文件、消息、记录和二进制资产

D1 Technical Identity
文档身份、版本、格式、哈希、权限和来源

D2 Structural Representation
章节、段落、表格、图片、引用等标准内容树

D3 Semantic Annotation
语言、主题、实体、时间、候选事实和关系

D4 Domain Projection
映射为 ME-Brain 或 ME-Who 的候选领域对象

D5 Retrieval Projection
全文、向量、图索引、Markdown 投影和 Agent 证据片段
```

约束：

- D0 永久保留；
- D1—D3 属于通用文档标准化；
- D4 属于领域 Adapter；
- D5 可以重新生成；
- D3 的候选语义不能直接覆盖 D4 的已确认领域事实。

---

## 4. 标准文档包

每个文档版本标准化后形成一个 `CanonicalDocumentPackage`。

建议交换结构：

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
└── projections/
    └── document.md
```

数据库实现可以拆表存储，但导入、导出和测试必须能够重建上述逻辑包。

### 4.1 manifest.json

记录文档身份、版本、格式和处理状态。

```yaml
document_id: doc_...
version_id: docv_...
source_id: src_...
logical_name: lighting-platform-technical-plan
file_name: technical-plan.docx
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
file_extension: docx
size_bytes: 0
checksum:
  algorithm: sha256
  value: ...
created_at: ...
modified_at: ...
ingested_at: ...
language:
  primary: zh-CN
  detected: [zh-CN, en]
parser:
  adapter: docx-native
  adapter_version: 0.1.0
  engine: python-docx
  engine_version: ...
processing_status: published
permissions: ...
previous_version_id: null
supersedes_version_id: null
metadata: {}
```

### 4.2 structure.json

保存文档树和节点顺序，不保存大段重复正文。

```yaml
root_node_id: node_root
nodes:
  - node_id: node_root
    node_type: document
    parent_id: null
    order: 0
    children: [node_sec_1]
  - node_id: node_sec_1
    node_type: section
    parent_id: node_root
    order: 1
    children: [node_heading_1, node_para_1]
```

### 4.3 content.jsonl

一行一个 `ContentNode`，便于增量处理和流式读取。

### 4.4 assets/

保存图片、附件、嵌入对象和可导出的表格快照。实际部署可保存对象存储引用。

### 4.5 relations.jsonl

保存文档和内容节点之间的确定性关系及候选关系。

### 4.6 provenance.jsonl

保存每个派生对象的来源、生成活动和处理工具。

### 4.7 semantic-candidates.jsonl

保存未经领域确认的实体、事实、决策、需求、偏好等候选信息。

### 4.8 quality-report.json

保存解析质量、缺口、警告和人工复核需求。

---

## 5. 核心对象

## 5.1 SourceAsset

表示不可变原始来源。

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

原始来源发生变化时生成新版本，不覆盖旧内容。

## 5.2 DocumentIdentity

表示跨版本的逻辑文档。

```yaml
document_id:
canonical_title:
alternate_titles: []
document_kind:
project_id:
owner_entity_id:
created_at:
status:
```

`document_id` 在版本变化后保持稳定。

## 5.3 DocumentVersion

表示某一时点的文档快照。

```yaml
version_id:
document_id:
source_id:
version_label:
checksum:
created_at:
valid_from:
valid_to:
previous_version_id:
change_type:
```

## 5.4 ContentNode

标准内容节点最少包含：

```yaml
node_id:
version_id:
node_type:
parent_id:
order:
source_anchor:
raw_text_ref:
normalized_text:
language:
style_role:
attributes:
asset_ids: []
relation_ids: []
quality:
```

### v0.1 通用节点类型

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

`unknown_block` 必须保留无法标准分类但确认存在的内容，防止静默丢失。

格式专有节点在 Adapter 内先转为通用节点；必要时通过 `attributes.format_specific` 保留原始特征。

## 5.5 SourceAnchor

用于从标准节点回到原始文件位置。

```yaml
anchor_type:
page_number:
paragraph_index:
run_range:
slide_number:
sheet_name:
cell_range:
byte_range:
character_range:
bounding_box:
source_object_id:
```

不同格式填写适用字段。任何可进入领域事实的节点都必须有 `SourceAnchor` 或明确记录无法定位的原因。

## 5.6 AssetRecord

```yaml
asset_id:
version_id:
asset_type:
media_type:
content_ref:
checksum:
source_anchor:
caption_node_id:
width:
height:
extraction_status:
```

## 5.7 RelationRecord

```yaml
relation_id:
subject_id:
predicate:
object_id:
relation_kind:
certainty:
source_node_ids: []
created_by:
confirmation_status:
```

v0.1 确定性关系：

```text
contains
follows
references
cites
has_caption
has_asset
is_version_of
was_derived_from
```

候选关系必须标记 `confirmation_status: candidate`。

## 5.8 SemanticCandidate

```yaml
candidate_id:
candidate_type:
value:
source_node_ids: []
extractor:
confidence:
scope:
domain_target:
status:
conflicts_with: []
```

`domain_target` 仅允许：

```text
me_brain
me_who
shared_entity
unclassified
```

## 5.9 QualityReport

```yaml
version_id:
overall_status:
content_coverage_ratio:
structure_confidence:
text_fidelity:
table_fidelity:
asset_linkage_ratio:
anchor_coverage_ratio:
provenance_completeness:
warnings: []
errors: []
missing_or_unparsed_regions: []
manual_review_required:
```

---

## 6. ID 与幂等规则

### 6.1 ID 类型

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

### 6.2 稳定性

- `source_id` 对同一不可变来源稳定；
- `document_id` 对逻辑文档跨版本稳定；
- `version_id` 对文件哈希和版本稳定；
- `node_id` 在同一版本和同一解析规范下稳定；
- 重新运行相同版本、相同 Adapter 版本时，不产生重复节点；
- Adapter 版本变化导致结构变化时，保留旧处理活动并生成新的派生结果版本。

### 6.3 推荐生成依据

```text
version_id = hash(document_id + source_checksum)
node_id = hash(version_id + node_type + normalized_source_anchor)
```

生产实现可使用 UUIDv7 与唯一约束，但必须保留幂等键。

---

## 7. 标准化流水线

```text
1. Acquire
2. Fingerprint
3. Identify Document
4. Detect Version
5. Deterministic Parse
6. Normalize Structure
7. Extract Assets
8. Build Anchors
9. Validate Fidelity
10. Extract Semantic Candidates
11. Route Domain Candidates
12. Publish Canonical Package
13. Build Derived Index
```

## 7.1 Acquire

获取原始文件或外部记录，保存权限和来源系统信息。

## 7.2 Fingerprint

计算哈希、文件大小、媒体类型和基本技术元数据。

## 7.3 Identify Document

判断是已有逻辑文档的新版本，还是新文档。判断依据按优先级：

1. 外部系统稳定 ID；
2. 用户明确关联；
3. 文件路径和仓库历史；
4. 标题、作者、时间等组合；
5. 模型候选，不自动确认。

## 7.4 Deterministic Parse

优先使用确定性解析器获取：

- 结构；
- 文本；
- 样式角色；
- 表格；
- 图片和附件；
- 原始位置。

模型解析只能补充确定性解析缺失的部分，并必须记录工具和置信度。

## 7.5 Normalize Structure

把格式专有对象映射为通用 `ContentNode`，保留顺序、层级和来源锚点。

## 7.6 Validate Fidelity

比较原始文档与标准包，确认：

- 文本是否缺失；
- 结构顺序是否正确；
- 表格行列是否保持；
- 图片是否关联；
- 引用和脚注是否可定位；
- 无法解析区域是否被显式记录。

## 7.7 Semantic Candidate Extraction

只有结构校验达到最低门槛后，才运行语义候选提取。

## 7.8 Publish

通过 Schema 校验和质量门槛后标记 `published`；否则标记 `partial` 或 `failed`。

---

## 8. 状态机

```text
received
→ fingerprinted
→ identified
→ parsed
→ normalized
→ validated
→ published
```

异常状态：

```text
partial
failed
quarantined
superseded
```

含义：

- `partial`：标准包可使用，但存在明确缺口；
- `failed`：无法生成有效结构；
- `quarantined`：安全、权限、损坏或格式异常，禁止进入检索；
- `superseded`：存在更新版本，但仍可历史查询。

禁止将 `partial` 伪装为完整成功。

---

## 9. 通用标准与领域映射边界

### 9.1 ME-Brain 映射

标准节点可以产生以下候选：

```text
Project
Requirement
Decision
Task
Constraint
Issue
Artifact
Claim
Review
Event
```

示例：

```yaml
candidate_type: Decision
value: Radiance 作为主计算核心
source_node_ids:
  - node_para_317
status: candidate
```

只有经过规则或人工确认后，才进入 ME-Brain Canonical Domain Data。

### 9.2 ME-Who 映射

标准节点可以产生：

```text
UserFact
BehavioralEvidence
PreferenceCandidate
CollaborationRuleCandidate
CurrentStateCandidate
```

同一条内容可以同时生成 ME-Brain 和 ME-Who 候选，但两者必须独立保存和确认。

### 9.3 禁止的耦合

- `ContentNode` 不直接保存“这是当前项目决策”；
- ME-Who 偏好不写入文档标准包；
- ME-Brain 对象不依赖某个解析器的私有字段；
- Hermes 不直接修改标准化节点；
- 向量或图索引不成为权威领域事实。

---

## 10. Parser Adapter 契约

每个 Adapter 必须实现以下逻辑能力：

```text
supports(source)
inspect(source)
parse(source)
normalize(parsed_result)
extract_assets(parsed_result)
build_anchors(parsed_result)
validate(package, source)
```

输出必须包含：

- Adapter 名称和版本；
- 使用的底层引擎和版本；
- 节点、资产和锚点；
- 警告与错误；
- 未解析区域；
- 质量指标。

Adapter 禁止：

- 直接写入 ME-Brain 或 ME-Who 权威表；
- 丢弃无法识别的内容而不记录；
- 用摘要替代原始正文；
- 修改原文件；
- 把模型推断标记为确定性结果。

---

## 11. 格式优先级

### P0：首个闭环

```text
Markdown / Plain Text
DOCX
Agent Conversation Export
Git Repository Documents
Zotero Metadata Record
```

### P1：科研与设计必需

```text
PDF
PPTX
XLSX / CSV
HTML / Web Archive
Email
```

### P2：复杂资产

```text
Image and OCR-assisted documents
BIM / IFC metadata
Rhino / Blender project metadata
Audio / Transcript
Video / Timeline metadata
```

说明：

- v0.1 Schema 设计必须能够容纳 P1；
- P0 实现不应为了快速开发而把标准限制为纯文本；
- PDF、PPTX、XLSX 的解析质量单独评测；
- OCR 仅作为缺失文本的补充手段，不覆盖原始图像证据。

---

## 12. 人类可读投影

每个标准文档包应生成只读或可重新生成的 Markdown 投影：

```markdown
---
document_id: doc_xxx
version_id: docv_xxx
source_id: src_xxx
quality_status: published
---

# 文档标题

<!-- node_id: node_heading_1 -->

正文……
```

Markdown 投影用于：

- 人工检查；
- Basic Memory / Obsidian 类工具接入；
- Agent 简单读取；
- Git Diff；
- 调试和测试。

人工对投影的修改不能直接覆盖标准包，应形成修订请求或单独的人工注释层。

---

## 13. 质量门槛

### 13.1 发布最低条件

- Schema 校验通过；
- `document_id`、`version_id`、`source_id` 完整；
- 原始来源可访问或明确记录保留策略；
- 文本覆盖率达到格式规定的最低值；
- 所有节点顺序合法；
- 高价值节点具有来源锚点；
- 未解析内容被显式记录；
- Provenance 完整。

### 13.2 建议首轮指标

| 指标 | P0 目标 |
|---|---:|
| 文本覆盖率 | ≥ 99% |
| 节点顺序正确率 | ≥ 99% |
| 锚点覆盖率 | ≥ 95% |
| 表格结构正确率 | ≥ 95% |
| 资产关联率 | ≥ 95% |
| 来源完整率 | 100% |
| 相同输入幂等率 | 100% |

以上为开发目标，不代表现有实现已达到。

---

## 14. 验证语料

第一轮验证语料必须同时覆盖：

1. 普通 DOCX 报告；
2. 含多级标题、表格、图片、脚注的 DOCX；
3. 中英文混合研究文档；
4. 项目开发记录；
5. Agent 对话导出；
6. Zotero 元数据与附件关系；
7. 设计类 PPTX 和 XLSX 样例，作为 P1 前置 Schema 验证；
8. 有版本变化的同一逻辑文档。

每个样例建立 Golden Package，包含人工确认的：

- 文档身份；
- 内容树；
- 文本；
- 表格；
- 资产；
- 锚点；
- 预期质量报告。

---

## 15. 与 Hermes 的第一阶段接口

Hermes 不直接面向解析器，而通过以下稳定能力使用文档：

```text
get_document_manifest
describe_document_structure
get_document_nodes
get_node_evidence
get_document_version_history
get_document_quality_report
```

Hermes 主要消费 ME-Brain 或 ME-Who 的领域 Context Pack；只有需要核实来源时才下钻标准文档节点。

Hermes 输出的新结论通过：

```text
submit_domain_candidate
submit_document_annotation
```

进入候选层，不直接修改原文或权威标准包。

---

## 16. 竞品能力吸收顺序

### 第一轮：输入与结构

- RAGFlow：复杂文档输入、切块可视化和来源引用；
- Docling / MinerU：版面、表格、公式、图片和 PDF 解析；
- Codebase-Memory：结构先于全文检索；
- Basic Memory：Markdown 投影和 Agent 可读性。

### 第二轮：关系与检索

- Graphiti：时间、Episode 和来源关系；
- LightRAG：全文、向量和图混合检索；
- Glean：高价值实体和信号网络。

### 第三轮：用户理解

- ChatGPT Memory：记忆查看、纠错、删除和来源体验；
- Supermemory：动态用户画像和时间变化；
- Mem0：Agent Memory API；
- Second-Me：长期身份层研究。

吸收原则：先复现单项优势并建立 Benchmark，再决定自研、适配或依赖。

---

## 17. 第一阶段交付物

文档标准化阶段完成后，应具备：

1. `CanonicalDocumentPackage` JSON Schema；
2. `ContentNode`、`SourceAnchor`、`AssetRecord` 等核心 Schema；
3. P0 Parser Adapter 契约；
4. 至少 Markdown、DOCX 和 Agent Conversation 三个 Adapter 原型；
5. Golden Corpus 与自动校验；
6. Markdown 人类可读投影；
7. 质量报告；
8. 文档版本与增量更新；
9. ME-Brain 与 ME-Who 候选映射接口；
10. Hermes 的文档证据查询接口。

在上述交付物通过评审前，不进入复杂图谱、完整 Context Compiler 或大规模前端开发。

---

## 18. 待后续逐项深化的专题

以下内容分别建立独立规格和开发计划：

- DOCX 无损解析；
- PDF 版面和引用标准化；
- PPTX 页面、元素和演讲稿标准化；
- XLSX 工作簿、表格、公式和图表标准化；
- Agent Conversation 标准化；
- Zotero 文献与附件标准化；
- 文档版本差异和变更影响；
- 领域候选抽取；
- 人工审核工作台；
- Hermes Adapter；
- 混合检索和 Context Compiler。

每项功能开发时都要重新审视对应竞品，明确吸收能力、评测指标和不可照搬部分。
