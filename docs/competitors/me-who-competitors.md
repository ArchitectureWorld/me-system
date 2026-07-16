# ME-Who 深度竞品分析

> 分析日期：2026-07-16  
> 分析目标：识别 ME-Who 应吸收的产品机制与技术能力，而不是选择一个仓库直接 Fork。

## 1. 竞品坐标

ME-Who 的竞品并不只包括“数字分身”产品，还包括四类系统：

1. 消费级 AI 记忆体验；
2. Agent Memory / Context Engine；
3. 时间知识图谱；
4. 人与 Agent 共同维护的知识界面。

ME-Who 的差异化方向是：

> 将用户明确事实、行为证据、偏好、能力、状态和协作规则治理为有来源、有范围、有时间、有权限、可确认和可撤销的 Personal Context。

---

## 2. ChatGPT Memory

- 官方资料：[Memory FAQ](https://help.openai.com/en/articles/8590148-memory-faq)
- 类型：消费级 AI 个性化与长期记忆体验

### 核心优势

- 从聊天、文件和连接应用中自动综合有用上下文；
- 提供 Memory Summary，降低用户维护成本；
- 支持直接纠正记忆；
- 支持“Don’t mention this again”；
- 展示某次个性化回答使用的记忆来源；
- 支持优先级管理和历史版本恢复；
- 能根据记忆改写搜索查询，使检索更贴合用户。

### ME-Who 应吸收

1. **无感积累体验**：用户不需要手工填写复杂画像表格；
2. **记忆摘要而非原始数据库暴露**：普通用户首先看到可理解的综合视图；
3. **来源可见**：每次个性化回答可解释“为什么使用了这条信息”；
4. **就地修订**：用户可以在使用结果旁直接修改或禁止使用；
5. **记忆历史**：支持查看和恢复用户模型的历史状态；
6. **相关时才调用**：不是每个任务都装载全部个人上下文；
7. **个性化参与检索**：ME-Who 应能够影响 ME-Brain 的查询改写和排序。

### 不应照搬

- 不能将用户模型封闭在某一个模型或聊天产品中；
- 不能只提供综合摘要而缺少结构化事实和适用范围；
- “不再提及”与真正删除必须清晰区分；
- 用户必须能够知道信息被哪些 Agent 和任务使用，而不只是当前聊天。

### 映射到 ME-System

```text
Memory Summary        → ME-Who Profile View
Memory Sources        → explain_personal_context
Don't mention again   → do_not_use / usage_policy
History / Restore     → ProfileSnapshot versioning
Search personalization→ Context Compiler query rewrite
```

---

## 3. Supermemory

- 官方仓库：[supermemoryai/supermemory](https://github.com/supermemoryai/supermemory)
- 许可证：MIT
- 类型：综合 Memory + RAG + User Profile + Connector Context Engine

### 核心优势

- 自动从对话提取事实；
- 处理时间变化、冲突和过期信息；
- 自动维护静态事实与动态状态两类用户画像；
- 一次调用同时返回 Profile 与相关 Memory；
- 将 Memory 和文档 RAG 放入统一检索入口；
- 提供 Gmail、Drive、Notion、GitHub 等连接器；
- 提供 MCP 及 Hermes、OpenClaw、Claude Code 等插件；
- 支持本地和离线运行；
- 提供 MemoryBench 等基准测试工具。

### ME-Who 应吸收

1. **Static / Dynamic Profile 分离**：稳定事实和近期状态不能混为一体；
2. **时间变化与自动失效**：短期信息应具有过期机制；
3. **一个调用返回用户画像与查询相关记忆**：减少 Agent 多次工具调用；
4. **容器化 Scope**：可以按用户、项目、工作与生活域隔离上下文；
5. **多 Agent 插件适配模式**：针对 Hermes、OpenClaw、Codex 提供宿主原生集成；
6. **本地与云端 API 一致**：便于先在 NAS / Linux 验证，后续保留托管能力；
7. **建立可重复基准**：ME-Who 必须通过长期记忆、变化、冲突和个性化测试集验证。

### 不应照搬

- 不应把用户事实、项目知识、文档和偏好统一压入单一 Memory Ontology；
- 自动冲突解决不能静默覆盖高价值个人事实；
- 自动遗忘必须区分“过期”“降权”“不再使用”和“彻底删除”；
- Profile 注入不能默认把全部用户信息塞入 System Prompt。

### 映射到 ME-System

```text
profile.static        → UserFact / stable Preference
profile.dynamic       → CurrentState
containerTag          → Scope
memory + profile call → compile_personal_context
MemoryBench           → ME-Who benchmark suite
Host plugins          → packages/agent-adapters
```

### 优先级

**A：重点 Benchmark 和产品机制参考。**

---

## 4. Mem0

- 官方仓库：[mem0ai/mem0](https://github.com/mem0ai/mem0)
- 类型：通用 Agent Memory API

### 核心优势

- User、Session、Agent 多层级记忆；
- API 和 SDK 接入简单；
- 适合快速为现有 Agent 增加长期记忆；
- 生态覆盖多种 Agent 框架；
- 记忆增删改查和搜索接口成熟；
- 具有公开长期记忆评测结果和研究路线。

### ME-Who 应吸收

1. **User / Session / Agent Scope**：ME-Who 的上下文必须知道服务对象和生命周期；
2. **开发者友好的最小 API**：添加事实、搜索、更新、删除不应要求理解内部图谱；
3. **Agent 可直接使用的 SDK**：降低接入 Hermes、OpenClaw 和项目 Agent 的成本；
4. **记忆层可插拔**：Agent 不应绑定某一个数据库或模型；
5. **低摩擦 Quickstart**：第一版安装和接入体验应尽可能短。

### 不应照搬

- 不能把所有信息都压平为短文本 Memory；
- User Memory 不能自动等同于权威用户事实；
- Session State 不应长期污染稳定画像；
- 需要补充来源、适用范围、时间有效性、确认状态和敏感度。

### 映射到 ME-System

```text
user_id               → user scope
session_id            → interaction scope
agent_id               → allowed agent / consumer
memory CRUD            → UserFact / Evidence candidate API
memory search          → relevant personal evidence retrieval
```

### 优先级

**B：API 与集成体验参考，不作为权威用户模型。**

---

## 5. Graphiti / Zep

- 官方仓库：[getzep/graphiti](https://github.com/getzep/graphiti)
- 类型：面向 Agent 的时间上下文图谱

### 核心优势

- 事实具有有效时间窗口；
- 新事实出现时，旧事实失效但不删除；
- Episode 保存产生事实的原始数据；
- 每个实体和关系可追溯到来源；
- 支持规定型和自动学习型本体；
- 支持增量图谱更新，无需全量重建；
- 混合语义、关键词和图遍历检索；
- 可回答“现在是什么”和“过去是什么”。

### ME-Who 应吸收

1. **Episode / Evidence First**：行为证据必须保留原始来源；
2. **Validity Window**：偏好、状态、角色和目标具有有效期；
3. **Supersede 而非删除历史**：用户变化应保留演化过程；
4. **Prescribed Ontology**：UserFact、Preference、CollaborationRule 等关键类型必须预定义；
5. **Learned Ontology 仅用于候选发现**：未知模式可以被发现，但不能直接成为权威画像；
6. **Hybrid Retrieval**：用户上下文不能只依赖向量相似度；
7. **历史查询**：支持分析用户过去阶段的目标和协作方式。

### 不应照搬

- 图谱不能成为唯一事实源；
- 自动生成的边不能直接视为用户确认；
- 不应第一阶段就引入复杂图数据库作为强依赖；
- 通用实体关系模型仍不足以表达个人信息治理和权限。

### 映射到 ME-System

```text
Episode                → Source / BehavioralEvidence provenance
Temporal Edge          → valid_from / valid_to / supersedes
Custom Types           → ME-Who domain schema
Hybrid Retrieval       → personal context retrieval pipeline
Historical Query       → ProfileSnapshot / state evolution
```

### 优先级

**A：时间、来源和演化模型的主要技术参考。**

---

## 6. Second-Me

- 官方仓库：[Mindverse/Second-Me](https://github.com/Mindverse/Second-Me)
- 许可证：Apache-2.0
- 类型：个人 AI 身份、层级记忆与本地训练

### 核心优势

- 强调数据本地化和用户控制；
- 使用 Hierarchical Memory Modeling；
- 使用 Me-Alignment 形成反映用户身份的模型；
- 支持不同场景下的角色表达；
- 将个人 AI 视为可授权连接外部应用的身份接口；
- 提供 Docker 化部署和本地模型路线。

### ME-Who 应吸收

1. **本地优先的身份数据控制**；
2. **层级用户模型**：原始经历、事实、偏好、画像和身份投影应分层；
3. **角色化 Context**：同一用户可以面向不同场景生成不同身份投影；
4. **授权式外部连接**：外部 Agent 只获取用户允许的身份上下文；
5. **长期保留 Identity Projection 能力**：未来可在可靠数据基础上增加个人模型或数字身份。

### 不应照搬

- 第一阶段不应以训练“另一个我”为目标；
- 不以语言风格模仿作为用户理解正确性的证明；
- 不应先做去中心化身份网络；
- 本地微调成本和模型老化问题不应成为核心产品依赖；
- 用户模型必须先可解释、可治理，再考虑模型内化。

### 映射到 ME-System

```text
Hierarchical Memory    → Source → Fact/Evidence → Profile → Context
Roleplay               → scoped identity projection
Local training/control → local-first deployment principles
AI identity interface  → future ME-Who authorization protocol
```

### 优先级

**C：长期身份层与产品愿景参考，非第一阶段技术主线。**

---

## 7. Basic Memory

- 官方仓库：[basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory)
- 许可证：AGPL-3.0
- 类型：Markdown + MCP 的人机双向知识与记忆系统

### 核心优势

- 人和 LLM 读写同一套 Markdown；
- 文件由用户直接控制，可与 Obsidian 共用；
- MCP 支持 Claude、Codex、Cursor、ChatGPT 等；
- 支持 Session Briefing 和压缩前检查点；
- 提供 Wiki Relation 和结构化 Observation；
- 支持 Schema infer、validate 和 diff；
- MCP 工具带 read-only、destructive、idempotent 等行为提示；
- 支持本地、云端、同步、快照和恢复。

### ME-Who 应吸收

1. **人类可读投影**：用户模型不能只存在数据库中；
2. **双向维护**：用户修改投影后，系统应形成受控变更；
3. **Session Briefing**：Agent 启动任务时获取最小个人协作摘要；
4. **Pre-compaction Checkpoint**：在上下文压缩前保存高价值候选证据；
5. **MCP Tool Hints**：帮助 Agent 正确选择只读、写入候选和破坏性工具；
6. **Schema 校验**：防止个人上下文随着 Agent 写入逐渐失去结构；
7. **快照与可恢复**：用户可以恢复过去的用户模型状态。

### 不应照搬

- Markdown 不应成为 ME-Who 唯一权威数据库；
- Wiki Link 不能代替严格关系和权限；
- 人工笔记、Agent 推断和权威事实必须分离；
- AGPL-3.0 代码复用需要单独评估许可证义务。

### 映射到 ME-System

```text
Markdown files         → human-readable projection
MCP tools              → ME-Who agent interface
Session briefing       → Personal Context Pack
Schema validate/diff   → ME-Who schema governance
Snapshots              → ProfileSnapshot history
```

### 优先级

**A：人工治理界面、MCP 设计和 Agent 使用体验参考。**

---

## 8. Glean Personal Graph / System of Context

- 官方资料：[Glean Enterprise Context](https://www.glean.com/enterprise-context/enterprise-graph)
- 类型：企业级个人图谱、组织图谱和上下文系统

### 核心优势

- 明确区分 Personal Graph 与 Enterprise Graph；
- 个人工作方式与企业客观知识在统一 Context System 中组合；
- 连接多种企业应用；
- 结合权限、身份和组织关系进行检索；
- 为搜索和 Agent 提供统一上下文基础。

### ME-Who 应吸收

1. **个人图与项目图分离**：对应 ME-Who 和 ME-Brain；
2. **System of Context 而非单一知识库**；
3. **个人上下文只作为组织知识使用策略，不修改组织事实**；
4. **权限继承**：个人图谱不能突破原始数据的访问权限；
5. **个性化排序**：同一项目知识对不同用户产生不同优先级。

### 不应照搬

- 不采用企业组织架构作为 ME-Who 的中心；
- 不需要第一阶段建设数百连接器和企业治理控制台；
- 不应将个人信息完全依赖工作应用中的行为推断；
- 产品应保持个人本地部署和小型 Agent Team 适用性。

### 映射到 ME-System

```text
Personal Graph         → ME-Who
Enterprise Graph       → ME-Brain
System of Context      → ME-Context Compiler
Permission-aware search→ Shared permissions + retrieval
```

### 优先级

**A：总体商业架构和双图关系标杆。**

---

## 9. ME-Who 综合吸收路线

### 第一阶段必须吸收

| 来源 | 吸收能力 |
|---|---|
| ChatGPT Memory | 无感积累、来源展示、就地纠错、禁止使用、历史恢复 |
| Supermemory | Static/Dynamic Profile、Scope、Benchmark、宿主插件 |
| Graphiti | Episode、时间有效性、来源和历史演化 |
| Basic Memory | 人类可读投影、MCP、Session Briefing、Schema 治理 |
| Glean | Personal Graph 与 Project Graph 分离、统一 Context System |

### 第二阶段吸收

| 来源 | 吸收能力 |
|---|---|
| Mem0 | 简洁 SDK、User/Session/Agent Scope、快速集成 |
| Second-Me | 层级身份、场景角色、授权式身份接口 |

## 10. 推荐产品结论

ME-Who 不应成为“更复杂的 Mem0”，也不应成为“本地版 Second-Me”。

推荐定位：

```text
Graphiti 的时间与来源
+ ChatGPT Memory 的治理体验
+ Supermemory 的动态画像与集成
+ Basic Memory 的人机双向接口
+ Glean 的 Personal / Project 双图关系
```

最终壁垒是：

> 在正确的任务、Agent、范围和权限下，将正确的用户事实与协作规则编译为最小、可解释和可撤销的 Personal Context。
