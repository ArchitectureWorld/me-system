# ME-Brain 深度竞品分析

> 分析日期：2026-07-16  
> 分析目标：识别 ME-Brain 应吸收的项目结构化、文档解析、连接同步、检索与 Agent 上下文能力。

## 1. 竞品坐标

ME-Brain 的直接竞品并不只是“第二大脑”应用。更相关的技术和产品分为五类：

1. 企业级统一上下文与知识图谱；
2. 领域结构化索引；
3. 复杂文档处理与 RAG；
4. 数据连接与持续同步；
5. 图、向量和全文混合检索。

ME-Brain 的差异化方向是：

> 面向科研、设计和开发项目建立权威、时间化、可追溯的 Project Semantic Index，并通过类型化工具和渐进式下钻为 Agent 编译低 Token、高准确度的 Project Context。

---

## 2. Glean Enterprise Graph / System of Context

- 官方资料：[Glean Enterprise Context](https://www.glean.com/enterprise-context/enterprise-graph)
- 类型：企业知识图谱、混合搜索、连接器和 Agent 上下文平台

### 核心优势

- 将项目、人物、产品、客户等高价值对象识别为核心实体；
- 将文档、工单、规格、消息等信号组织到实体周围；
- 将 Personal Graph 与 Enterprise Graph 分离；
- 强调权限继承和身份感知检索；
- 连接大量企业数据源；
- 通过统一 Context System 服务搜索和 Agent；
- 不要求用户先手工整理所有资料。

### ME-Brain 应吸收

1. **高价值实体中心**：项目不是文件夹，文件只是项目实体周围的证据和信号；
2. **统一 Context System**：搜索、问答和 Agent 应共享同一项目上下文基础；
3. **权限继承**：原始数据不可见时，派生摘要和关系也不能越权暴露；
4. **连接器与索引解耦**：数据源接入不应绑定某个 Agent；
5. **Personal / Enterprise 分图**：对应 ME-Who 和 ME-Brain；
6. **混合排序**：内容相关度、项目关系、时间和用户角色共同决定排序。

### 不应照搬

- 不采用企业组织通用实体作为唯一 Schema；
- 不优先建设企业管理后台、数百连接器和大规模 SaaS；
- 对科研、设计和开发必须建立更深的领域对象；
- 个人和小型团队的本地优先部署不能被企业架构复杂度拖累。

### 映射到 ME-System

```text
Enterprise Graph       → ME-Brain
Personal Graph         → ME-Who
System of Context      → ME-Context Compiler
Permission-aware index → Shared permission model
High-value entities    → Project / Decision / Artifact / Requirement
```

### 优先级

**A：总体商业架构和产品能力标杆。**

---

## 3. Codebase-Memory

- 论文：[Codebase-Memory: Tree-Sitter-Based Knowledge Graphs for LLM Code Exploration via MCP](https://arxiv.org/abs/2603.27277)
- 类型：代码库持久化结构图与类型化 MCP

### 核心优势

- 使用 Tree-Sitter 对代码进行确定性结构解析；
- 支持大量编程语言；
- 预先建立函数、类、模块、调用和依赖图；
- 提供调用关系、影响分析和社区发现；
- 通过 MCP 让 Agent 按结构查询，而不是反复读取文件；
- 在公开实验中以更低 Token 和更少工具调用保持较高答案质量；
- 对图原生问题具有明显优势。

### ME-Brain 应吸收

1. **先建立领域结构，再让 Agent 查询**；
2. **确定性解析优先于 LLM 猜测**：能由语法树、文件格式和系统 API 得到的内容不交给模型推断；
3. **持久化结构索引**：项目结构不能在每次任务时重新生成；
4. **类型化 MCP**：提供 callers、dependencies、impact 等明确工具，而不只是 search；
5. **渐进式原文下钻**：先结构查询，必要时再读取代码；
6. **用 Token 与工具调用评估收益**：不以图谱规模或节点数量作为成功指标；
7. **社区与 Hub 分析**：用于发现项目核心模块和高影响对象。

### 不应照搬

- Tree-Sitter 只适用于代码，不适合直接解释项目决策和设计意图；
- 结构关系不等于业务语义；
- 不能用代码图替代项目文档、需求、ADR 和用户确认；
- 不同领域需要不同解析器和 Schema。

### 映射到 ME-System

```text
Tree-Sitter pipeline   → Software Domain Adapter
Persistent code graph  → Derived software index
MCP graph tools        → typed ME-Brain MCP
Impact analysis        → analyze_change_impact
Community discovery    → project hub / module clustering
Token benchmark        → ME-Brain baseline evaluation
```

### 优先级

**A+：ME-Brain 方法论最重要的直接参考。**

---

## 4. RAGFlow

- 官方仓库：[infiniflow/ragflow](https://github.com/infiniflow/ragflow)
- 类型：复杂文档理解、可解释切块、RAG 与 Agent 平台

### 核心优势

- 深度解析复杂非结构化文档；
- 支持 Word、PPT、Excel、图片、扫描件、网页和结构化数据；
- 提供多种模板化切块策略；
- 可视化切块结果，允许人工干预；
- 提供可追溯引用；
- 支持多路召回与重排；
- 已支持 MinerU、Docling、多模态模型、Agent 工作流和 MCP；
- 适合处理历史设计、科研和 Office 资料。

### ME-Brain 应吸收

1. **解析质量优先**：错误输入结构会直接限制后续索引和回答；
2. **按文档类型选择解析策略**：论文、PPT、Excel、扫描件不能使用同一种切块方式；
3. **解析结果可视化与人工纠错**；
4. **表格、图片和版面结构保留**；
5. **引用链与原文快速预览**；
6. **解析和项目语义层解耦**：解析器输出标准中间结构，再由 ME-Brain 形成领域对象；
7. **可编排 Ingestion Pipeline**：不同输入可以组合 OCR、VLM、规则和 LLM。

### 不应照搬

- Document / Chunk 不应成为 ME-Brain 的核心领域模型；
- 不应 Fork 整个平台后在其 Workspace 概念中硬塞项目语义；
- 部署较重，第一阶段应以可替换解析服务使用；
- 自动切块和 RAG 结果不能直接成为权威项目事实。

### 映射到 ME-System

```text
Deep document parsing  → services/ingestion/document-processing
Template chunking      → ParserAdapter strategies
Human intervention     → ingestion review UI
Grounded citations     → SourceReference / evidence preview
Pipeline orchestration → ingestion workflow
```

### 优先级

**A：复杂文档输入层的主要参考和候选组件。**

---

## 5. Airweave

- 官方仓库：[airweave-ai/airweave](https://github.com/airweave-ai/airweave)
- 许可证：MIT
- 类型：面向 Agent 的连接、持续同步、索引与统一检索层

### 核心优势

- 位于数据源与 Agent 之间；
- 统一处理认证、接入、同步、索引和检索；
- 支持大量应用、数据库和文档源；
- 支持持续同步和更新；
- 通过 SDK、REST、MCP 和 Agent 框架集成；
- 连接器服务可被多个 Agent 共享；
- 自托管部署路径明确。

### ME-Brain 应吸收

1. **连接器是共享基础设施，不由每个 Agent 重复开发**；
2. **认证、游标、增量同步和失败重试标准化**；
3. **连接器输出统一 Source Envelope**；
4. **数据源变化可持续同步，而不是一次性导入**；
5. **CLI、SDK、REST 和 MCP 多种入口**；
6. **连接器能力注册表**：明确支持对象、权限、同步方式和增量能力；
7. **源数据与搜索索引解耦**。

### 不应照搬

- 统一检索结果不能代替项目领域结构；
- 不需要第一阶段支持几十种企业 SaaS；
- Airweave 的检索集合不应成为 ME-Brain 的 Project 模型；
- 复杂生产栈不应在本地 MVP 中一次性引入。

### 映射到 ME-System

```text
Source connector       → packages/connector-sdk
Continuous sync        → ingestion sync service
Auth handling          → connector credentials vault
Unified source output  → SourceEnvelope
SDK / REST / MCP       → connector access surfaces
```

### 优先级

**A：连接器架构参考；第一版按需自建少量连接器。**

---

## 6. Graphiti / Zep

- 官方仓库：[getzep/graphiti](https://github.com/getzep/graphiti)
- 类型：动态时间上下文图谱

### 核心优势

- 项目事实具有有效时间窗口；
- 旧事实失效但保留历史；
- Episode 作为来源和事实产生记录；
- 增量更新，无需全量重建；
- 支持当前与历史查询；
- 混合关键词、语义和图遍历；
- 自定义实体和关系类型。

### ME-Brain 应吸收

1. **项目状态的时间有效性**；
2. **方案替代和决策演化**；
3. **Episode 与来源追踪**；
4. **增量图谱更新**；
5. **规定型领域本体**；
6. **历史状态查询**；
7. **图谱作为派生索引，而不是无来源关系集合**。

### 不应照搬

- 自动图谱不能成为权威项目数据；
- LLM 提取结果必须进入候选层；
- 不应第一阶段强制部署独立图数据库；
- 通用实体关系不足以表达科研、设计和开发领域语义。

### 映射到 ME-System

```text
Episode                → Source Event
Temporal fact          → validity / supersedes
Custom ontology        → domain packs
Incremental graph      → Derived Index update
Historical query       → trace_decision_history
```

### 优先级

**A：项目时间、变化与来源模型主要参考。**

---

## 7. LightRAG

- 官方仓库：[HKUDS/LightRAG](https://github.com/HKUDS/LightRAG)
- 类型：轻量知识图谱 RAG、向量与图双层检索

### 核心优势

- 知识图谱与向量嵌入双层架构；
- 支持 local、global、hybrid、naive 和 mix 查询模式；
- 能同时处理局部事实和跨文档全局关系；
- 增量添加数据，无需完整重建全局索引；
- 通过 MinerU、Docling 和 Native Parser 处理文本、表格、公式和图片；
- 支持多种存储后端；
- 对检索实体、关系和文本 Chunk 分别设置 Token 预算；
- 提供 REST API 和 WebUI。

### ME-Brain 应吸收

1. **图 + 向量 + 原文混合检索**；
2. **局部事实与全局主题采用不同查询模式**；
3. **索引增量更新**；
4. **实体、关系和原文分别分配 Token Budget**；
5. **多引擎文档解析接口**；
6. **查询阶段可插拔重排器**；
7. **缓存实体关系抽取结果，避免重复 LLM 成本**。

### 不应照搬

- 自动实体图是派生索引，不是权威项目事实；
- 全量 Chunk 关系提取可能产生高成本和低价值边；
- Embedding 模型更换会带来重建成本，应封装索引版本；
- 第一阶段不应同时引入多种数据库后端；
- 项目类型化查询不能退化为 LightRAG 的通用 query mode。

### 映射到 ME-System

```text
local query            → entity-focused retrieval
global query           → cross-project/theme retrieval
hybrid/mix             → Context Compiler retrieval policy
entity/relation budget → structured context token allocation
incremental merge      → Derived Index partial update
```

### 优先级

**A：混合检索与派生图索引的重要 Benchmark。**

---

## 8. Basic Memory

- 官方仓库：[basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory)
- 许可证：AGPL-3.0
- 类型：Markdown + MCP 的人机共维护知识系统

### 核心优势

- 人和 Agent 使用同一套可读 Markdown；
- 可在 Obsidian、编辑器和 Agent 之间双向编辑；
- Observation 与 Relation 形成简单语义格式；
- 支持全文与向量混合搜索；
- 支持 Schema infer、validate、diff；
- MCP 工具带行为提示；
- 支持项目、最近活动、Context Build 和快照。

### ME-Brain 应吸收

1. **权威元数据的人类可读投影**；
2. **项目目录和 Markdown 导出不形成平台锁定**；
3. **人和 Agent 均可提出修改，但通过受控同步回写**；
4. **Schema 校验和差异检查**；
5. **MCP Tool Annotation**；
6. **项目 Briefing、最近活动和 Context Build 体验**；
7. **Obsidian 作为阅读、校正和导航界面**。

### 不应照搬

- Markdown 不应成为复杂项目关系、时间和权限的唯一存储；
- Wiki Link 不是严格 Project Relation；
- Agent 直接改文件不能绕过候选更新和确认机制；
- AGPL-3.0 代码复用需评估许可证影响。

### 映射到 ME-System

```text
Markdown knowledge     → project readable projection
build_context          → compile_project_context UX reference
schema tools           → domain schema governance
MCP annotations        → typed tool metadata
Obsidian integration   → optional human workspace
```

### 优先级

**A：可读投影和 Agent 工具体验参考。**

---

## 9. Khoj

- 官方仓库：[khoj-ai/khoj](https://github.com/khoj-ai/khoj)
- 类型：自托管 AI Second Brain、文档问答、Agent、研究与自动化

### 核心优势

- 将文档、网络、Agent、深度研究和自动化集成成完整产品；
- 支持本地与在线模型；
- 自托管路径成熟；
- 提供多种交互入口；
- 产品闭环比底层基础设施项目更完整。

### ME-Brain 应吸收

1. **从数据接入到 Agent 行动的完整用户路径**；
2. **多模型与本地模型路由**；
3. **自动化和定时任务作为项目上下文消费者**；
4. **统一 Web 产品壳层和多入口体验**；
5. **用户不需要理解底层向量、图和解析管线**。

### 不应照搬

- 文档问答不能成为 ME-Brain 的核心定义；
- Workspace / Conversation 不应替代 Project Domain；
- 自动化不应早于权威项目事实和 Context Pack；
- 不第一阶段建设大而全的聊天产品。

### 映射到 ME-System

```text
AI second brain shell  → future ME-Brain workspace
Model routing          → shared model provider layer
Automations            → agent consumers of Project Context
Self-hosting UX        → deployment experience
```

### 优先级

**B：完整产品体验参考。**

---

## 10. Obsidian / Tana / Capacities / Heptabase

这些产品不是 ME-Brain 的后端技术基础，但对人机界面具有重要价值。

### Obsidian 应吸收

- 开放 Markdown；
- 本地数据控制；
- 插件化；
- 图谱和双向链接作为导航视图；
- Git 和外部工具兼容。

不得把文件结构直接视为完整项目 Schema。

### Tana 应吸收

- Supertag 式渐进结构化；
- 类型和字段可以逐步形成；
- 同一对象存在多种视图；
- 用户不必一次填完全部元数据。

不得依赖闭源云端数据模型。

### Capacities 应吸收

- 对象优先而不是文件夹优先；
- 低摩擦快速采集；
- 人物、项目、会议等对象对普通用户可理解。

不得要求用户主要依靠人工维护对象。

### Heptabase 应吸收

- 空间化研究和设计画布；
- 来源卡片、白板和主题框架；
- 专题研究中的视觉组织。

该能力更适合作为 ME-Brain 的研究/设计工作台，而不是底层事实库。

### 优先级

**B/C：主要用于前端和人工审核体验。**

---

## 11. ME-Brain 综合吸收路线

### 第一阶段必须吸收

| 来源 | 吸收能力 |
|---|---|
| Codebase-Memory | 领域结构先行、持久化索引、类型化 MCP、Token Benchmark |
| RAGFlow | 复杂文档解析、可解释切块、人工纠错、引用 |
| Graphiti | 时间事实、Episode、来源、替代关系、增量更新 |
| LightRAG | 图/向量/全文混合检索、查询模式、Token 分配 |
| Basic Memory | 人类可读投影、MCP 工具提示、Schema 治理 |
| Glean | 高价值实体、统一上下文、权限感知、Personal/Project 分离 |

### 第二阶段吸收

| 来源 | 吸收能力 |
|---|---|
| Airweave | 连接器注册、认证、持续同步和统一 Source Envelope |
| Khoj | 完整产品闭环、多模型、自动化和自托管体验 |
| Tana / Capacities | 对象化、渐进结构化和低摩擦确认 |
| Heptabase | 研究与设计画布 |

## 12. 推荐产品结论

ME-Brain 不能被实现为“RAGFlow + 一个知识图谱页面”，也不能只是“跨项目的 Codebase-Memory”。

推荐组合：

```text
Codebase-Memory 的领域结构方法
+ RAGFlow 的复杂输入处理
+ Graphiti 的时间与来源
+ LightRAG 的混合派生索引
+ Basic Memory 的人机接口
+ Glean 的统一上下文架构
+ Airweave 的连接同步模式
```

核心壁垒是：

> 将原始项目材料转换为权威 Project Metadata，并根据任务、Agent、时间、权限和 Token 预算编译为可逐级下钻的 Project Context。
