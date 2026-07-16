# 竞品能力吸收矩阵

> 目标：将竞品研究转换为 ME-System 的明确工程输入，避免“参考某项目”停留在泛化表述。

## 1. 优先级定义

| 优先级 | 含义 |
|---|---|
| A+ | 直接影响核心架构，应尽快做原型或 Benchmark |
| A | 第一阶段必须吸收的机制或设计原则 |
| B | 第二阶段补充能力或产品体验 |
| C | 长期愿景、特定模块或前端参考 |
| Avoid | 明确不采用的做法 |

---

## 2. 总体矩阵

| 竞品 | 主要对应产品 | 应吸收的核心优点 | 在 ME-System 中的落点 | 不应照搬 | 优先级 |
|---|---|---|---|---|---|
| ChatGPT Memory | ME-Who | 无感积累、记忆摘要、来源展示、就地纠错、禁止使用、历史恢复、相关时调用 | Profile View、`explain_personal_context`、Usage Policy、ProfileSnapshot | 平台绑定、只有摘要而缺少严格 Scope、删除语义不清 | A |
| Supermemory | ME-Who / Shared | Static/Dynamic Profile、时间变化、冲突与过期、Memory+RAG、MCP、宿主插件、本地运行、Benchmark | CurrentState、Profile Compiler、Agent Adapters、Benchmark Suite | 将用户、项目和文档统一压入单一 Memory Ontology | A |
| Mem0 | ME-Who | User/Session/Agent Scope、简单 SDK、快速接入、记忆 CRUD | Scope Model、ME-Who SDK、候选事实接口 | 短文本 Memory 作为权威用户模型 | B |
| Graphiti | 两者 | Episode、Provenance、Validity Window、Supersede、增量图、混合检索、自定义本体 | Temporal Model、Derived Context Graph、历史查询 | 自动图谱作为唯一事实源、第一阶段强依赖图数据库 | A |
| Second-Me | ME-Who | 本地优先、层级记忆、身份投影、角色化上下文、授权式身份接口 | Future Identity Projection、Local-first 原则 | 第一阶段个人模型微调、数字分身社交、以“像用户”为指标 | C |
| Basic Memory | 两者 | Markdown 人机共读写、MCP、Session Briefing、Schema infer/validate/diff、工具行为提示、快照 | Readable Projection、MCP UX、Schema Governance、Briefing | Markdown 作为唯一权威数据库；AGPL 代码未经评估直接复用 | A |
| Glean | 两者 / Shared | Personal Graph 与 Enterprise Graph 分离、高价值实体、权限感知、统一 Context System、混合排序 | ME-Who / ME-Brain 双域、ME-Context、Permission-aware Retrieval | 企业级复杂度、通用组织 Schema 直接照搬 | A |
| Codebase-Memory | ME-Brain | 领域结构先行、确定性解析、持久化图、类型化 MCP、影响分析、Token Benchmark | Software Pack、Typed MCP、Impact Analysis、Benchmark | 将代码结构等同项目语义；只服务代码 | A+ |
| RAGFlow | ME-Brain | 深度文档解析、模板切块、人工干预、异构格式、引用、多模态和可编排管线 | Document Processing Service、ParserAdapter、Ingestion Review | Document/Chunk 成为项目核心；Fork 整个平台作为底座 | A |
| Airweave | Shared / ME-Brain | 连接器注册、认证、持续同步、统一检索入口、SDK/REST/MCP、自托管 | Connector SDK、Sync Service、SourceEnvelope | 一次性引入几十种连接器和复杂生产栈；集合代替 Project | B |
| LightRAG | ME-Brain | 图+向量双层、local/global/hybrid/mix、增量更新、多模态解析、Token 分区、重排 | Derived Index、Retrieval Policy、Token Allocation | 自动图作为权威数据、多后端过度设计、通用 query 代替类型化工具 | A |
| Khoj | ME-Brain 产品层 | 自托管 AI Second Brain、模型路由、Agent、深度研究、自动化、多入口 | Future Workspace、Model Provider、Automation Consumer | 把聊天和文档问答作为核心产品模型 | B |
| Obsidian | 两者的人类界面 | 开放 Markdown、本地文件、插件化、Git、双向链接、人工校正 | Readable Projection、Optional Workspace | 文件结构作为完整数据模型 | B |
| Tana | 两者前端 | Supertag、渐进结构化、动态字段、多视图 | Candidate Review UI、Object Type UX | 闭源云端模型和人工维护为主 | C |
| Capacities | 两者前端 | 对象优先、低摩擦采集、普通用户可理解的实体 | Capture UX、Object View | 依赖用户手工维护对象 | C |
| Heptabase | ME-Brain 工作台 | 研究卡片、白板、空间化组织、来源导向思考 | Research / Design Canvas | 作为底层项目事实库 | C |
| NotebookLM | ME-Brain 输出层 | 限定来源、引用体验、同一资料多种生成形式 | Evidence-grounded Generation、Source Notebook View | Notebook 孤岛、无法持续维护项目状态 | B |
| AnythingLLM | 产品与部署 | 本地工作台、Agent、MCP、模型路由、多用户和 Docker 部署 | Deployment UX、Agent Workspace Benchmark | Workspace + Documents 作为 ME-Brain 核心 | C |
| Letta | Agent Runtime | Stateful Agent、记忆分层、上下文管理 | Agent Runtime Adapter、短期运行状态 | 各 Agent 各自形成独立长期真相 | B |
| GraphRAG | ME-Brain 分析层 | 跨文档全局主题、社区摘要、周期性综合 | Monthly/Project-wide Synthesis | 用批量静态图承担实时项目状态 | B |

---

## 3. 按 ME-System 模块归类

### 3.1 Source Ledger / Provenance

重点吸收：

- Graphiti：Episode 与事实来源；
- ChatGPT Memory：使用来源展示；
- RAGFlow：引用与原文预览；
- Basic Memory：文件可读与历史快照；
- Glean：权限继承。

必须形成：

```text
Source
→ Candidate Extraction
→ Canonical Fact / Evidence
→ Derived Index
→ Context Pack
```

每层之间都可追溯。

### 3.2 Temporal Model

重点吸收：

- Graphiti：有效时间、替代关系、历史查询；
- Supermemory：动态状态与过期；
- ChatGPT Memory：自动保持信息新鲜；
- Second-Me：身份版本。

统一字段：

```yaml
valid_from:
valid_to:
supersedes:
superseded_by:
status:
```

### 3.3 ME-Who Domain

重点吸收：

- ChatGPT Memory 的用户治理体验；
- Supermemory 的 Static / Dynamic Profile；
- Mem0 的 Scope；
- Graphiti 的证据演化；
- Glean 的 Personal Graph；
- Basic Memory 的人机共维护。

### 3.4 ME-Brain Domain

重点吸收：

- Codebase-Memory 的领域结构方法；
- Glean 的高价值实体；
- Graphiti 的项目事实版本；
- RAGFlow 的复杂输入；
- LightRAG 的派生检索。

### 3.5 Connector SDK

重点吸收：

- Airweave：连接器生命周期与持续同步；
- Supermemory：常用个人数据连接器；
- Glean：权限感知连接；
- AnythingLLM / Khoj：本地数据源配置体验。

第一批只开发：

```text
Local Files
Git / GitHub
Agent Conversation
Zotero
```

### 3.6 Retrieval

重点吸收：

- LightRAG：local/global/hybrid/mix 与 Token 分区；
- Graphiti：语义、BM25 和图遍历；
- Glean：身份、关系、时间和权限参与排序；
- RAGFlow：多召回与重排；
- Basic Memory：全文 + 向量和相关片段返回。

推荐顺序：

```text
Structured Filter
→ Full-text / BM25
→ Vector Recall
→ Graph Expansion
→ Temporal Filter
→ Permission Filter
→ Rerank
→ Evidence Loading
```

### 3.7 Context Compiler

重点吸收：

- Codebase-Memory：渐进式结构探索和低 Token；
- Glean：统一上下文系统；
- Supermemory：Profile + Relevant Memory 一次返回；
- ChatGPT Memory：相关时才调用；
- LightRAG：不同内容类型 Token Budget；
- Basic Memory：Briefing 与 Context Build。

Context Compiler 是自有产品必须自建的核心，不能外包给单一竞品。

### 3.8 Human Governance UI

重点吸收：

- ChatGPT Memory：摘要、来源、纠正、禁止使用和历史；
- Tana：Supertag 式渐进结构化；
- Capacities：对象优先和低摩擦采集；
- Basic Memory / Obsidian：可读文件和双向编辑；
- RAGFlow：解析结果人工干预；
- Heptabase：研究与设计画布。

---

## 4. 推荐复用策略

| 项目 | 推荐方式 | 是否作为核心依赖 |
|---|---|---|
| Graphiti | 建立独立原型，验证时间图和历史查询 | 可选派生图层，不作唯一事实源 |
| Codebase-Memory | 作为 Software Pack 的适配器或算法参考 | 推荐 |
| RAGFlow | 通过服务接口测试复杂文档解析 | 可替换组件 |
| LightRAG | 作为混合检索 Benchmark 或独立服务 | 可替换组件 |
| Airweave | 参考 Connector SDK；后期可测试接入 | 暂不核心依赖 |
| Basic Memory | 学习格式和工具；谨慎处理 AGPL | 不直接成为权威层 |
| Supermemory | 用于 ME-Who Benchmark 与集成对比 | 不成为核心事实库 |
| Mem0 | 用于 Memory API 基线 | 不成为核心事实库 |
| Second-Me | 研究身份层和本地训练 | 暂不依赖 |
| Glean | 产品架构参考 | 无法直接复用 |

---

## 5. 明确禁止的竞品拼装路线

### 禁止路线一

```text
RAGFlow + 图谱页面 = ME-Brain
```

原因：缺少权威项目元数据、当前事实和类型化工具。

### 禁止路线二

```text
Mem0 / Supermemory = ME-Who 全部
```

原因：用户模型需要更严格的来源、Scope、权限和确认机制。

### 禁止路线三

```text
Basic Memory Markdown = ME-System 唯一数据库
```

原因：复杂权限、时间关系、冲突和多模态来源难以可靠表达。

### 禁止路线四

```text
Graphiti 自动图 = 权威真相
```

原因：自动抽取仍然存在误判，图应属于派生索引和候选发现层。

### 禁止路线五

```text
先导入所有资料，再考虑 Schema
```

原因：会形成大规模但不可治理的 Chunk 和关系集合，无法证明 Token、速度和准确度收益。

---

## 6. 最终组合判断

### ME-Who

```text
ChatGPT Memory 的治理体验
+ Supermemory 的动态画像和 Benchmark
+ Graphiti 的时间证据
+ Basic Memory 的人机接口
+ Glean 的 Personal Graph 边界
```

### ME-Brain

```text
Codebase-Memory 的领域结构方法
+ RAGFlow 的复杂输入
+ Graphiti 的时间和来源
+ LightRAG 的混合检索
+ Basic Memory 的可读投影
+ Glean 的 Enterprise Context 架构
+ Airweave 的连接同步模式
```

### Shared Core

```text
自建 Source Ledger
+ 自建 Canonical Domain Store
+ 自建 Permission Model
+ 自建 Context Compiler
+ 可替换的 Parser / Graph / Vector / Connector Components
```
