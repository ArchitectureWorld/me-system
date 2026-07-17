# ADR-0003：稳定 Zotero + Obsidian + Hermes / ME-Reader Core 路线

> 状态：已接受  
> 日期：2026-07-17  
> 决策范围：ME-System 文献与复杂文档阅读入口、Agent 精阅读、双向链接及客户端路线

## 1. 背景

ME-System 需要把论文、技术规范、项目报告和其他复杂文档转换为可追溯、可复核、可被 Agent 持续使用的结构化知识。

现有工具各自擅长不同问题：

- Zotero 擅长文献元数据、附件、PDF 阅读、批注和引用管理；
- Obsidian 擅长本地 Markdown、双向链接、人工笔记、跨项目关联和开放文件访问；
- Hermes 是用户的个人助理级 Agent，负责理解任务、组织上下文和调度专业子 Agent；
- ME-Brain 负责保存和组织可追溯的客观知识；
- OpenWiki 适合在标准化知识之上承担跨文献综合与持续 Wiki 编译。

此前评估过三种前端路线：

1. 独立 ME-Reader App；
2. Notion 作为结构化阅读与审核前端；
3. Obsidian 作为首要客户端，配合独立 ME-Reader Core。

Notion 的数据库视图和协作能力较强，但其平台封闭、云端依赖、Markdown 非原生、API 与导出存在约束，不符合 ME-System 本地优先、数据开放和组件可替换的长期原则。独立 App 是长期可能方向，但在 Agent 阅读流程与证据模型尚未经过真实使用验证前，优先投入完整前端会增加产品风险。

## 2. 决策

稳定采用以下主线：

```text
Zotero：文献、PDF、批注、引用
Obsidian：知识笔记、人工审核、双向链接、ME-Brain 人类可读文件层
Hermes：统一用户入口、阅读任务总控、专业子 Agent 调度
ME-Reader Core：文档解析、精读任务、证据锚定、关系存储和 Markdown 投影
ME-Brain：结构化知识底座
OpenWiki：后续跨文献综合与持续 Wiki 编译
```

第一阶段用户主要使用的软件控制为：

```text
Zotero + Obsidian
```

Hermes、ME-Reader Core 和 ME-Brain 作为后台能力存在，不再新增一套独立聊天入口或独立 Agent 系统。

## 3. Agent 归属

Agent 阅读直接接入现有 Hermes 体系：

```text
Hermes Personal Assistant
├── Quick Reading：个人助理直接完成快速问答
└── Deep Reading Job
    ├── Literature Reader
    ├── Evidence Linker
    └── Reading Reviewer
```

- Hermes 个人助理负责理解阅读目的、选择模式、组织项目上下文、创建任务、监督状态并向用户汇报；
- Literature Reader 是 Hermes 的专业阅读子 Agent，负责制定阅读计划、章节精读、论文整体综合和候选知识生成；
- Evidence Linker 负责把 Claim、Evidence、Context 与原文节点、论文、方法、项目和其他知识对象建立关系；
- Reading Reviewer 负责证据核验、范围检查、过度推断检查和待人工复核项生成；
- Parser 不是 Agent，而是确定性工具或可替换 Adapter。

ME-System 不复制 Hermes 的 Agent 运行时，只提供可被 Hermes 调用的阅读基础设施、协议、数据模型和工具。

## 4. 第一实现梯队

Agent 精阅读和双向链接并列进入 P0，不再将双向链接推迟到跨论文知识图谱阶段。

```text
P0-1 Hermes 阅读任务协议
P0-2 文档结构解析与稳定原文锚点
P0-3 Agent 证据化精阅读
P0-4 双向链接与关系存储
P0-5 Obsidian 最小客户端与 Markdown 投影
P0-6 Zotero Adapter 与 PDF 回跳
```

第一阶段最小闭环：

```text
用户在 Hermes 或 Obsidian 发起精读
→ Hermes 创建 Deep Reading Job
→ Parser 生成结构节点与原文锚点
→ Reader 按章节精读
→ 同步生成 Claim–Evidence–Context
→ Linker 写入双向关系
→ Reviewer 复核
→ Obsidian 展示与人工确认
→ 确认后的结果进入 ME-Brain
```

## 5. 双向链接定义

本决策中的“双向链接”不是只指 Obsidian 的 `[[Wiki Link]]`，而是三层统一能力。

### 5.1 原文与知识对象双向定位

- 从 Claim / Evidence 返回 Zotero PDF 的页码、章节和原文区域；
- 从原文节点查看关联的 Evidence、Claim、笔记、项目和其他知识对象。

### 5.2 知识对象之间的双向关系

至少支持：

```text
Paper ↔ Claim
Claim ↔ Evidence
Evidence ↔ SourceAnchor
Paper ↔ Method
Claim ↔ Project
Claim ↔ Claim
Note ↔ KnowledgeObject
```

关系必须可从两端查询，不依赖某个 Markdown 文件是否改名或移动。

### 5.3 客户端之间的稳定链接

核心对象使用 ME-Brain 稳定 ID 和 Canonical URI：

```text
mebrain://paper/<id>
mebrain://claim/<id>
mebrain://evidence/<id>
mebrain://node/<id>
mebrain://project/<id>
```

Obsidian Wiki Link、Zotero URI 和未来 Web 链接均是该稳定对象的客户端投影，而不是权威身份。

## 6. 数据权威边界

| 数据 | 权威来源 |
|---|---|
| 文献元数据、附件、引用键、PDF 批注 | Zotero |
| 文档结构、原文节点、SourceAnchor | ME-Reader Core / ME-System 文档标准包 |
| Claim–Evidence–Context、关系和审核状态 | ME-Brain |
| 人工阅读笔记、跨项目思考、可读投影 | Obsidian Vault |
| Agent 运行上下文和任务状态 | Hermes / Reading Job Manager |

Markdown 是开放的人类可读投影和人工编辑层，不是唯一事实数据库。Agent 不得通过覆盖整篇 Markdown 的方式修改人工内容。

## 7. Obsidian 的边界

Obsidian 进入第一实现梯队，但只承担客户端职责：

- 触发或转交精读任务；
- 显示任务状态；
- 查看 Agent 精读结果；
- 展示 Claim–Evidence–Context；
- 点击 Evidence 返回 Zotero 原文；
- 查看双向链接和反向引用；
- 确认、驳回、修改或请求重读；
- 将人工笔记关联到稳定知识对象。

第一阶段不在 Obsidian 插件中实现：

- 文档解析核心；
- Agent 运行时；
- 权威关系数据库；
- 完整知识图谱引擎；
- 第二套聊天系统；
- 复杂画布和完整独立阅读器。

## 8. Zotero 的边界

Zotero 继续作为文献入口和事实源，不承担 ME-Brain 的知识组织职责。

第一阶段需支持：

- 通过 Zotero Item Key、Attachment Key 和 Citation Key 稳定识别文献；
- 获取 PDF / CAJ 等附件位置和元数据；
- 使用 `zotero://` URI 或本地跳转服务返回条目、PDF 页码和批注；
- 将 Obsidian / ME-Brain 对应对象链接写回文献条目或笔记；
- 不复制 PDF 到 Obsidian Vault。

## 9. 结果与影响

### 正面影响

- 用户可见软件数量收敛为 Zotero + Obsidian；
- 所有知识文件保持本地、开放和可版本管理；
- Agent 能力不被某个客户端绑定；
- 阅读、证据、关系和人工笔记形成完整闭环；
- 后续开发独立 ME-Reader App 时不需要推翻底层；
- 文献场景可以成为 ME-System 文档标准化和 ME-Brain 的第一验证项目。

### 代价与风险

- 需要维护 Zotero、Obsidian 与 ME-Brain 三者之间的稳定身份映射；
- Markdown 与结构化数据库之间需要明确同步和冲突策略；
- PDF 精确区域回跳依赖 SourceAnchor 质量；
- Obsidian 插件必须保持轻量，避免重新形成封闭内核；
- 第一阶段需要同时验证 Agent 精读准确性和链接稳定性。

## 10. 被否决或后置的方案

### Notion 主客户端

后置为可选协作发布或团队看板，不进入核心主线。原因：平台封闭、Markdown 非原生、本地优先不足、API 与迁移约束明显。

### 直接开发完整独立 App

长期保留，但在 Agent 精读、证据模型和双向链接通过真实工作流验证之前不进入第一阶段。

### 只使用 Zotero + Better Notes

可作为局部能力参考，但不足以稳定承载跨文档、跨项目的知识关系和 ME-Brain 人类可读层，因此不作为最终主线。

## 11. 验收结论

本 ADR 通过以下结果视为第一阶段路线成立：

1. 用户可在 Hermes 或 Obsidian 中选择 Zotero 文献并提出精读目标；
2. Hermes 可以调用专业阅读子 Agent 完成章节级精读；
3. 每个高价值 Claim 至少绑定一个可返回原文的 Evidence；
4. Obsidian 中可查看正向链接和反向引用；
5. 人工确认、驳回和重读请求可稳定回写；
6. PDF、Markdown 文件移动或改名不会破坏核心对象关系；
7. 确认后的知识可以被 ME-Brain、Hermes 和后续 OpenWiki 复用。
