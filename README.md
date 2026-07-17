# ME-System

ME-System 是面向 AI Agent 的双上下文基础设施，由 **ME-Who**、**ME-Brain** 与共享的上下文运行时组成。

- **ME-Who**：帮助 Agent 理解“我是谁、我怎样思考、怎样与我协作”。
- **ME-Brain**：帮助 Agent 理解“项目是什么、当前状态如何、下一步怎样推进”。
- **ME-Context**：按任务、Agent、权限与 Token 预算，将 ME-Who 和 ME-Brain 的相关信息编译为可直接使用的上下文包。

第一阶段主要搭配 **Hermes Agent** 使用：Hermes 负责任务理解、上下文编排和 Agent 调度，ME-System 提供长期、结构化、可追溯的个人与项目上下文。

## 核心公式

```text
Task Context
= Current Request
+ ME-Brain Objective Context
+ ME-Who Personal Context
```

ME-Brain 决定 Agent **知道什么**；ME-Who 决定 Agent **如何理解用户并采取行动**；ME-Context 决定在有限上下文窗口中 **具体加载什么、加载到什么深度**。

## 当前最高优先级：文档信息标准化

ME-System 当前不优先开发复杂知识图谱、完整用户画像或大规模前端，而是先建立统一的文档信息标准。

```text
原始来源与版本
→ 通用文档标准包
→ 结构、资产和来源锚点
→ 质量与完整性校验
→ ME-Brain / ME-Who 领域候选
→ 检索、Context Pack 与 Hermes 集成
```

标准化的重点不是把文件简单转换成纯文本，而是稳定表达：

- 文档身份和版本；
- 章节、段落、表格、图片、公式、引用等结构；
- 内容在原文件中的位置；
- 附件和嵌入资产；
- 来源、处理工具、质量和缺失内容；
- 领域事实与原始证据之间的关系。

解析、图谱、检索和 Agent 功能均建立在该标准之上，并保持可替换。

## 产品定位

### ME-Who

ME-Who 是面向多个 Agent 的可治理用户上下文系统。它管理用户明确事实、行为证据、稳定偏好、能力边界、当前状态与协作规则，并按任务生成具有范围、来源、置信度和权限约束的 Personal Context。

### ME-Brain

ME-Brain 是面向科研、设计、开发等客观项目的结构化元数据与项目语义索引。它将文件、对话、Git、文献、任务、需求、决策和成果转换为可追溯、可增量更新、可按需展开的 Project Context，以降低 Agent 的 Token 消耗并提升检索速度、准确度与任务连续性。

## 产品关系

```text
                         User Request
                              │
                              ▼
                         Hermes Agent
                  任务理解、规划与上下文编排
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                 ME-Who             ME-Brain
              Personal Context    Project Context
                    └─────────┬─────────┘
                              ▼
                   OpenClaw / Codex / Other
```

两条产品线共享原始来源、文档标准、时间、实体标识、权限、来源追踪和上下文协议，但不共享领域事实：

- 同一条对话可以产生一个 ME-Brain 项目决策，同时产生一个 ME-Who 行为证据；
- ME-Who 可以影响检索排序、表达颗粒度和 Agent 自主度，但不能修改 ME-Brain 中的项目事实；
- Agent 默认只提交候选更新，经规则或人工确认后才能进入权威数据层。

## 当前仓库策略

当前采用 **Monorepo 起步、模块化开发、独立构建与部署、满足条件后再拆仓** 的策略。

建议目标结构：

```text
me-system/
├── apps/
│   ├── me-who/
│   └── me-brain/
├── services/
│   ├── document-standardization/
│   ├── context-compiler/
│   ├── ingestion/
│   └── retrieval/
├── integrations/
│   └── hermes/
├── packages/
│   ├── me-core/
│   ├── document-schema/
│   ├── source-ledger/
│   ├── provenance/
│   ├── temporal-model/
│   ├── permissions/
│   ├── connector-sdk/
│   └── mcp-sdk/
├── domains/
│   ├── me-who-schema/
│   └── me-brain-schema/
└── docs/
```

Monorepo 只是一种开发组织方式，不代表两个产品必须捆绑部署。ME-Who、ME-Brain 和共享服务从第一天起都应拥有独立 API、数据库 Schema、测试边界和 Docker 镜像。

## 文档导航

- [产品与架构总纲](docs/00-product-and-architecture-overview.md)
- [Monorepo 架构决策](docs/adr/ADR-0001-monorepo-first.md)
- [文档标准化优先决策](docs/adr/ADR-0002-document-standardization-first.md)
- [文档信息标准化规范 v0.1](docs/specs/document-information-standardization-v0.1.md)
- [ME-Who 产品定义](docs/products/me-who.md)
- [ME-Brain 产品定义](docs/products/me-brain.md)
- [ME-Who 竞品分析](docs/competitors/me-who-competitors.md)
- [ME-Brain 竞品分析](docs/competitors/me-brain-competitors.md)
- [竞品能力吸收矩阵](docs/competitors/adoption-matrix.md)
- [推荐开发路径](docs/roadmap/recommended-development-path.md)

## 当前稳定原则

1. **文档标准化优先**：先建立稳定中间表达，再开发上层功能。
2. **来源优先**：高价值事实必须能够追溯到原始资料。
3. **先结构、后语义**：章节、段落、表格、资产和锚点先于自动事实抽取。
4. **权威数据与派生索引分离**：向量、图谱和摘要不能静默覆盖权威事实。
5. **用户拥有身份解释权**：ME-Who 的推断必须可查看、确认、修订、限制和删除。
6. **项目事实不受偏好污染**：ME-Who 只影响上下文策略，不改变 ME-Brain 的客观状态。
7. **渐进式上下文装载**：Agent 默认读取结构化摘要，必要时再下钻到证据和原文。
8. **领域原生而非万能本体**：先建立软件、科研和设计领域包，再逐步扩展。
9. **本地优先与可替换组件**：核心标准和领域模型自建，解析、检索、图谱和连接器保持可替换。

## 当前阶段

仓库目前处于文档标准化规格阶段。下一阶段应优先完成：

1. `CanonicalDocumentPackage` JSON Schema；
2. `ContentNode`、`SourceAnchor`、`AssetRecord` 等核心 Schema；
3. Parser Adapter 契约和质量报告；
4. Markdown、DOCX、Agent Conversation 的首批标准化原型；
5. Golden Corpus 与幂等、完整性、来源定位测试；
6. ME-Brain 与 ME-Who 候选映射接口；
7. Hermes 的文档证据查询接口。

完成这些基础后，再逐项深入开发检索、图谱、上下文编译、用户治理和前端功能，并针对每项功能吸收对应竞品的优势。
