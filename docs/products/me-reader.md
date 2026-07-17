# ME-Reader 产品定义

> 文档状态：初始稳定版  
> 日期：2026-07-17

## 1. 产品定位

ME-Reader 是 ME-System 面向复杂文档的证据化阅读与知识关联基础设施。

它不替代 Zotero、Obsidian 或 Hermes，而是连接三者：

- Zotero 提供文献元数据、附件、PDF 阅读、批注和引用；
- Hermes 作为个人助理级 Agent，理解用户目的并调度专业阅读子 Agent；
- ME-Reader Core 提供文档解析、阅读任务、证据锚定、双向链接、关系存储和 Markdown 投影；
- Obsidian 提供本地 Markdown、人工审核、双向链接和跨项目知识浏览；
- ME-Brain 保存确认后的结构化知识；
- OpenWiki 在后续阶段使用标准化知识编译跨文献 Wiki。

ME-Reader 的核心目标不是生成一份摘要，而是：

> 让 Agent 对文献或文档进行可追溯、可复核、可关联、可持续利用的精阅读。

## 2. 产品归属

ME-Reader 属于 ME-System，作为 ME-Brain 的主要文档输入与人机阅读入口。

```text
ME-System
├── ME-Who：理解用户与协作方式
├── ME-Brain：组织客观知识与项目上下文
├── ME-Context：编译任务上下文
└── ME-Reader：把文档转化为可验证知识
```

科研论文是第一垂直场景，但核心协议保持文档类型无关。科研体系通过 Academic Profile 扩展论文类型、研究方法、实验、数据集、引用和综述等领域规则。

## 3. 用户侧软件路线

第一阶段稳定采用：

```text
Zotero + Obsidian
```

- Zotero 是文献和 PDF 主界面；
- Obsidian 是知识笔记、审核和双向链接主界面；
- Hermes 是统一对话与任务入口；
- 不新增独立 Agent 聊天客户端；
- 独立 ME-Reader App 暂缓，待工作流验证后评估。

## 4. 核心能力

### 4.1 文档接入

支持从以下来源创建统一阅读任务：

- Zotero 文献条目与附件；
- 本地文件；
- Obsidian 笔记；
- 未来的网页、Git、网盘和项目文件库。

所有来源先进入 Source Ledger，并生成稳定 `document_id` 与 `version_id`。

### 4.2 文档解析与原文锚定

Parser Adapter 将原始文档转换为 Canonical Document Package：

```text
Document
├── Section
├── Paragraph
├── Table
├── Figure
├── Equation
├── Citation
└── SourceAnchor
```

高价值内容节点必须保留：

- 页码；
- 章节路径；
- 文本；
- 文本哈希；
- 页面坐标；
- 前后文；
- 原文件和版本引用。

### 4.3 Agent 精阅读

Agent 阅读由 Hermes 体系执行：

```text
Hermes Personal Assistant
└── Deep Reading Job
    ├── Literature Reader
    ├── Evidence Linker
    └── Reading Reviewer
```

Reader 按文档结构和用户目的制定阅读计划，逐章节生成结构化理解，而不是一次性全文总结。

### 4.4 Claim–Evidence–Context

ME-Reader 的最小知识单元为：

```text
Claim + Evidence + Context
```

- Claim：文档提出、发现、支持或讨论的命题；
- Evidence：支持该命题的原文、图表、实验结果或数据；
- Context：结论成立的对象、条件、范围、数据集、时间、地区和评价指标。

必须区分：

- 作者主张；
- 实验结果；
- 引用他人观点；
- 用户推论；
- Agent 推论。

### 4.5 双向链接

双向链接覆盖三类关系：

1. 原文节点与知识对象之间的双向定位；
2. Paper、Claim、Evidence、Method、Project 等对象之间的双向关系；
3. Zotero、Obsidian、Hermes 和未来客户端之间的稳定链接。

核心关系依赖稳定 ID 和 Canonical URI，不以 Obsidian 文件名或本地路径作为唯一身份。

### 4.6 人工审核

Agent 输出默认是候选结果，至少支持：

- 确认；
- 驳回；
- 修改；
- 请求补充证据；
- 请求重读章节；
- 标记暂不确定。

未经确认的研究结论不能进入 ME-Brain 权威数据层。

## 5. 角色与职责

### 5.1 Hermes Personal Assistant

负责：

- 理解用户阅读目的；
- 判断快速阅读或正式精读；
- 注入相关项目和个人上下文；
- 创建、暂停、恢复和终止阅读任务；
- 调度专业阅读子 Agent；
- 处理需要用户确认的问题；
- 汇总结果并组织后续行动。

不负责在通用上下文中直接完成所有逐段精读。

### 5.2 Literature Reader

负责：

- 文档快速浏览；
- 识别文档类型；
- 制定阅读计划；
- 章节级精读；
- 提取问题、方法、数据、结果和局限；
- 生成 Claim–Evidence–Context；
- 形成论文级或文档级综合。

### 5.3 Evidence Linker

负责：

- 把 Evidence 绑定到 SourceAnchor；
- 建立论文内部逻辑链；
- 建立知识对象之间的类型化关系；
- 维护正向与反向查询；
- 输出 Obsidian Wiki Link、Zotero URI 等客户端投影。

### 5.4 Reading Reviewer

负责：

- 验证 Claim 是否被 Evidence 支持；
- 检查页码、图表和数值；
- 检查作者观点与引用观点是否混淆；
- 检查相关性与因果性是否混淆；
- 检查适用范围和限定条件；
- 生成待人工复核项。

### 5.5 Parser Adapter

Parser 是确定性或可替换工具，不作为独立 Agent。它负责结构、资产、页码、坐标和引用解析，不负责研究结论判断。

## 6. 数据对象

第一版核心对象：

```text
ReadingJob
ReadingPlan
Document
DocumentVersion
ContentNode
SourceAnchor
Paper
Claim
Evidence
Context
Relation
Annotation
Review
ObsidianProjection
ZoteroBinding
```

推荐稳定 URI：

```text
mebrain://document/<id>
mebrain://node/<id>
mebrain://paper/<id>
mebrain://claim/<id>
mebrain://evidence/<id>
mebrain://project/<id>
```

## 7. 客户端边界

### Zotero

权威管理：

- 文献元数据；
- PDF / CAJ 等附件；
- PDF 批注；
- Citation Key；
- 引用和参考文献。

### Obsidian

主要承担：

- Agent 精读结果展示；
- 人工阅读笔记；
- 双向链接与反向引用；
- 跨文献、跨项目关联；
- 人工审核；
- ME-Brain 人类可读文件投影。

### ME-Reader Core

主要承担：

- 阅读任务管理；
- 文档解析协调；
- SourceAnchor；
- 结构化对象与关系存储；
- Agent 工具接口；
- Markdown 投影；
- Zotero / Obsidian Adapter。

## 8. 第一阶段范围

### 必须实现

- 带文本层 PDF；
- Zotero 元数据与附件接入；
- Hermes Deep Reading Job；
- 章节级 Agent 精阅读；
- Claim–Evidence–Context；
- SourceAnchor；
- 原文与知识对象双向定位；
- 知识对象正反向关系；
- Obsidian Markdown 投影；
- 人工审核状态；
- Zotero PDF 页码回跳。

### 暂缓

- 扫描 PDF OCR；
- CAJ 深度解析；
- 复杂公式语义理解；
- 表格视觉重建；
- 全自动文献综述；
- 大型知识图谱画布；
- 完整独立 Web / Desktop App；
- Notion 主客户端；
- 多用户协作。

## 9. 成功标准

第一阶段成功不是“生成了一份阅读报告”，而是：

1. Hermes 能根据用户目的创建正式精读任务；
2. Reader 能按章节完成精读并保留阅读过程；
3. 每个高价值 Claim 可以返回准确原文；
4. Obsidian 能查看双向链接和反向引用；
5. 人工可以确认、修改、驳回或要求重读；
6. 确认结果可被 ME-Brain 和其他 Agent 复用；
7. 更换客户端不会破坏稳定身份和关系。

## 10. 长期演进

```text
阶段 1：Zotero + Obsidian + Hermes / ME-Reader Core
阶段 2：跨论文 Linker 与 Academic Profile 深化
阶段 3：OpenWiki Research Compiler
阶段 4：独立 ME-Reader Web / Desktop Client
阶段 5：设计、规范、合同、项目报告等领域 Profile
```

独立 App 是否开发，取决于 Zotero 与 Obsidian 在实际使用中暴露的明确界面瓶颈，而不是预设必须重新开发全部阅读软件。
