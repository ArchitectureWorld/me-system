# ME-Reader 第一实现梯队开发路径

> 状态：稳定路线  
> 日期：2026-07-17

## 1. 路线结论

ME-Reader 第一阶段不先开发完整独立 App，而是优先开发 Agent 精阅读和双向链接核心，并使用 Zotero + Obsidian 完成真实工作流验证。

```text
Zotero：文献与 PDF
Obsidian：笔记、审核和双向链接
Hermes：个人助理级任务总控
ME-Reader Core：解析、阅读任务、证据和关系
ME-Brain：确认知识与上下文
```

第一实现梯队中的核心能力并列推进：

```text
Agent 精阅读
+
双向链接
+
原文锚定
+
Hermes 调度
+
Obsidian 人工审核
```

## 2. 开发原则

1. 先验证阅读准确性与证据可追溯性，不先追求完整 UI；
2. Agent 直接使用 Hermes 个人助理及其专业子 Agent，不建立第二套 Agent 运行时；
3. Obsidian 是第一客户端，不是系统内核；
4. Zotero 是文献与附件权威来源，不承担跨项目知识组织；
5. Markdown 是开放投影和人工编辑层，不是唯一数据库；
6. 所有高价值结论必须能够返回原文；
7. 双向链接从第一版进入核心数据协议；
8. 外部 Parser 和模型通过 Adapter 接入；
9. Agent 输出默认是候选，人工确认后再进入权威层；
10. 部署 IP、端口和应用关系不得写死在功能代码或规格中。

## 3. Workstream A：文档与身份基础

### 目标

把 Zotero 文献和 PDF 转换为具有稳定身份、版本和原文锚点的 Canonical Document Package。

### 任务

- 定义 Zotero Item、Attachment、Citation Key 与 `document_id` 的映射；
- 定义 `DocumentVersion`；
- 完成带文本层 PDF Parser Adapter；
- 生成章节、段落、表格、图片、公式和引用节点；
- 生成页码、坐标、文本哈希和前后文锚点；
- 建立解析质量报告；
- 建立 PDF 版本变化后的锚点迁移策略。

### 交付

```text
CanonicalDocumentPackage
ContentNode
SourceAnchor
ZoteroBinding
QualityReport
```

### 验收

- 同一文献重复接入不产生重复身份；
- 文档新版本与旧版本可区分；
- 主要章节和正文顺序正确；
- 高价值节点具有可用 SourceAnchor；
- 任一节点可回到原始 PDF。

## 4. Workstream B：Hermes 阅读任务协议

### 目标

Hermes 能根据用户目的创建、调度和管理正式精读任务。

### 任务

- 定义 `ReadingRequest`；
- 定义 `ReadingJob` 状态机；
- 定义项目上下文和个人上下文注入边界；
- 定义任务暂停、恢复、取消和重试；
- 定义 Hermes 与专业子 Agent 的交接包；
- 定义用户反馈和人工确认接口；
- 记录每次 Agent 运行的模型、Prompt、输入、输出和成本。

### 交付

```text
create_deep_reading_job
get_reading_job_status
pause_reading_job
resume_reading_job
cancel_reading_job
get_reading_result
```

### 验收

- Hermes 可以从 Zotero 条目创建任务；
- 用户可以提供阅读目的和重点；
- 长任务可以中断恢复；
- 失败阶段可以单独重试；
- 专业阅读上下文不污染个人助理长期对话。

## 5. Workstream C：Literature Reader

### 目标

建立可复核的章节级 Agent 精阅读流程。

### 任务

- 实现快速浏览与论文类型识别；
- 生成阅读计划；
- 按章节执行精读；
- 识别研究问题、方法、数据、实验、结果、贡献和局限；
- 同步提取 Claim–Evidence–Context；
- 保存章节级结果；
- 基于章节结果生成论文级综合；
- 支持针对用户项目目标生成关联分析。

### 交付

```text
ReadingPlan
SectionReading
PaperRecord
Claim
Evidence
Context
```

### 验收

- 不依赖一次性全文总结；
- 章节结果可独立查看和重读；
- 作者观点、引用观点和 Agent 推论可区分；
- 高重要度 Claim 均有 Evidence；
- 数值和比较结论保留条件与指标。

## 6. Workstream D：Evidence Linker 与双向关系

### 目标

让阅读结果从产生时就成为可双向查询的知识对象，而不是孤立 Markdown 摘要。

### 任务

- 定义稳定对象 ID 和 Canonical URI；
- 建立 Claim → Evidence → SourceAnchor 链路；
- 建立 Paper、Method、Dataset、Project 等类型化关系；
- 实现正向和反向关系查询；
- 实现 Obsidian Wiki Link 投影；
- 实现 Zotero URI 投影；
- 建立文件改名、移动后的链接稳定策略；
- 建立关系候选的置信度和审核状态。

### 交付

```text
RelationRecord
CanonicalURI
ForwardLinks
Backlinks
ObsidianProjection
ZoteroLinkProjection
```

### 验收

- 从 Claim 可返回 Evidence 和 PDF 原文；
- 从 Evidence 可查询其支持的 Claim；
- 从 Method 可查询使用它的论文；
- Obsidian 文件移动不影响核心关系；
- 关系可被 Hermes 和 ME-Brain 直接查询。

## 7. Workstream E：Reading Reviewer

### 目标

使用独立复核步骤降低 Agent 精读中的遗漏、误读和过度推断。

### 任务

- 核验 Claim 与 Evidence；
- 检查页码、图表和数值；
- 检查作者观点与引用观点；
- 检查相关性与因果性；
- 检查适用范围；
- 检查负面结果和局限；
- 标记需人工复核对象；
- 支持局部重读和补充证据。

### 交付

```text
ReviewReport
ReviewIssue
ConfidenceAssessment
RereadRequest
```

### 验收

- Reviewer 不只是重写一份摘要；
- 能发现明显证据不足和范围扩大；
- 待人工复核项可直接跳到原文；
- 修改和确认过程具有审计记录。

## 8. Workstream F：Obsidian 最小客户端

### 目标

在不把业务内核塞入插件的前提下，提供可使用的阅读、审核和双向链接界面。

### P0 功能

- 选择 Zotero 文献并触发精读；
- 输入阅读目的和重点；
- 显示阅读任务状态；
- 打开或刷新 Paper Note；
- 展示 Agent 精读结果；
- 展示 Claim、Evidence、Context；
- 点击 Evidence 返回 Zotero PDF；
- 显示 Backlinks；
- 确认、驳回、修改或请求重读；
- 将人工笔记关联到稳定对象。

### 暂缓

- 独立聊天系统；
- 完整 PDF 阅读器；
- 大型图谱画布；
- 多用户协作；
- 复杂主题和排版系统。

### 验收

用户只打开 Zotero 和 Obsidian，即可完成：

```text
选择论文
→ 发起精读
→ 查看结果
→ 返回原文
→ 审核 Claim
→ 建立项目链接
```

## 9. Workstream G：ME-Brain 候选入库

### 目标

把审核后的阅读结果转换为 ME-Brain 可查询的客观知识。

### 任务

- 建立候选对象与权威对象的边界；
- 定义确认、驳回、替代和失效状态；
- 建立 Paper、Claim、Method、Dataset、Project 的领域映射；
- 建立来源和版本追踪；
- 为 Hermes 提供渐进式查询接口；
- 为后续 OpenWiki 编译提供标准输入。

### 验收

- 未确认结果不进入权威层；
- 任一确认结论可追溯到 Agent 运行、Evidence 和原文；
- Hermes 可以从项目问题下钻到文献证据；
- 同一对象更新不会产生静默冲突。

## 10. 实施顺序

虽然多个 Workstream 并列属于第一梯队，但具体实现建议采用以下依赖顺序：

```text
A 文档与身份基础
→ B Hermes 阅读任务协议
→ C Reader 最小精读
→ D Linker 最小双向关系
→ E Reviewer
→ F Obsidian 最小客户端
→ G ME-Brain 候选入库
```

之后进入循环迭代：

```text
Parser 质量
↔ Reader 准确性
↔ Link 稳定性
↔ Reviewer 发现率
↔ 人工审核效率
```

Obsidian 客户端可以在 C、D 出现稳定接口后提前并行开发，但不得反向定义核心数据模型。

## 11. 第一批里程碑

### M0：协议冻结

- ReadingJob；
- ContentNode；
- SourceAnchor；
- Claim–Evidence–Context；
- RelationRecord；
- Review 状态；
- Canonical URI。

### M1：单篇论文无界面闭环

- Zotero PDF 接入；
- Reader 精读；
- Reviewer 复核；
- JSON / Markdown 输出；
- Evidence 返回 PDF 页码。

### M2：双向链接闭环

- Paper / Claim / Evidence / SourceAnchor 正反向查询；
- Obsidian Paper Note；
- Zotero URI 回跳；
- 文件改名不破坏对象关系。

### M3：人工审核闭环

- Obsidian 中确认、驳回和修改；
- 局部重读；
- 审计记录；
- 确认对象进入 ME-Brain。

### M4：真实科研使用验证

- 至少 10 篇不同类型论文；
- 真实项目目标驱动精读；
- 记录准确率、遗漏率、Token、耗时和人工审核时间；
- 与一次性全文总结进行对比。

## 12. 第一阶段完成标准

第一阶段在以下条件全部满足后完成：

1. Zotero 与 Obsidian 是用户侧主要软件；
2. Hermes 可以稳定调度阅读子 Agent；
3. Agent 按章节精读而非只生成摘要；
4. 高价值 Claim 均有 Evidence 和 Context；
5. Claim、Evidence 和原文具有双向链接；
6. 人工审核可以修改最终结果；
7. 确认知识可以进入 ME-Brain；
8. 所有关键对象具备来源、版本和审计信息；
9. 系统核心不依赖 Notion 或 Obsidian 私有数据模型；
10. 独立 ME-Reader App 是否必要，可基于真实瓶颈重新决策。
