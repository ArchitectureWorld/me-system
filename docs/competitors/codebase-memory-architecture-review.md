# Codebase-Memory 架构 Review 与 ME-System 吸收方案

> Review 日期：2026-07-23  
> 参考项目：`DeusData/codebase-memory-mcp`  
> 目标：提炼可用于 ME-System 双图谱与 MCP 的架构原则，而不是复制其技术栈。

## 1. 核心判断

Codebase-Memory 真正值得吸收的不是 Tree-sitter、C 或 SQLite，而是以下产品结构：

```text
确定性输入解析
→ 多阶段结构索引
→ 持久化知识图谱
→ 少量结构化查询工具
→ MCP / CLI 共用同一后端
→ Agent 负责自然语言理解
```

它明确把自己定位为结构分析后端，而不是 Chatbot：后端不嵌入回答问题的 LLM；现有 Agent 是自然语言到结构查询的翻译器。

ME-System 应采用同样的单核心原则：

```text
ME-Graph Core
├── 输入与证据
├── 候选图谱
├── 权威双图谱
├── 查询与投影
├── 质量状态
├── MCP
└── CLI
```

ME-Brain 与 ME-Who 是两个业务图谱，但不是两个工程核心。

## 2. Codebase-Memory 的关键架构优势

### 2.1 单一结构后端

其源码将 Store、Pipeline、MCP、Watcher、CLI 等能力组织在一个产品内。不同模块边界清晰，但都围绕同一张持久化图谱工作。

对 ME-System 的落点：

- `services/me-graph-core` 保持唯一内核；
- Source Ledger 和 Candidate Queue 进入同一内核；
- Hermes/Pi Adapter 不单独复制查询逻辑；
- Domain Pack 是插件，不是新产品或新服务。

### 2.2 多阶段 Pipeline

Codebase-Memory 不是“一次解析直接完成全部关系”，而是通过 definitions、calls、usages、tests、routes、semantic edges、git history 等多个 Pass 增量丰富图谱。

对 ME-System 的落点：

```text
Pass 1  来源发现与身份确认
Pass 2  内容标准化与 EvidenceFragment
Pass 3  实体/事件/事实候选抽取
Pass 4  实体消歧与项目归属
Pass 5  冲突、替代和时间检查
Pass 6  Candidate 审核
Pass 7  权威图谱提交
Pass 8  派生摘要、全文和向量索引
```

每个 Pass 只完成一种职责，并记录版本、覆盖率和质量。

### 2.3 Persistent Graph First

Codebase-Memory 先把结构转成持久化图谱，再让 Agent 查询，而不是让 Agent 每次读取原始文件。

对 ME-System 的落点：

- Agent 默认读 `GraphSlice`；
- 原始文件只在证据核查时下钻；
- 当前事实和历史事实由图谱时间模型区分；
- 不把 Markdown 投影或 RAG Chunk 当权威数据。

### 2.4 结构化 MCP 工具

其 MCP 工具具备明确输入 Schema、统一输出 Schema和 read-only/destructive/idempotent/open-world 注解，并支持不同工具 Profile。

对 ME-System 的落点：

- 建立单一 Tool Registry；
- Tool Registry 同时生成 MCP 注册、CLI 帮助、工具文档和契约测试；
- 工具显式标记只读、破坏性和幂等性质；
- Hermes 使用 `coordinator` Profile；
- Pi/Codex 后续使用更小的 `executor` Profile。

### 2.5 Compact First

Codebase-Memory 默认返回紧凑架构、签名和结构结果，只有明确请求时才返回完整代码或更深层关系；响应中提供 total、limit、cursor、truncated 或覆盖率信号。

对 ME-System 的落点：

```text
compact：节点 ID、类型、标签、状态、关键关系
standard：增加属性、时间和证据句柄
full：按授权增加完整属性和证据片段
```

所有列表和子图查询必须显式返回：

- `total`；
- `returned`；
- `truncated`；
- `next_cursor`；
- `quality` / `coverage`。

### 2.6 CLI 与 MCP 对等

Codebase-Memory 的工具既能通过 MCP 调用，也能通过 CLI 调用，便于测试、调试和自动化。

对 ME-System 的落点：

- MCP Tool 不直接调用内部私有函数；
- MCP 与 CLI 共用 Application Service；
- 每个新增查询先提供纯 Python 服务和 CLI 验收，再暴露 MCP；
- 协议测试之外仍保留可重复的命令行验收。

### 2.7 Project Scope

Codebase-Memory 的主要查询都要求项目参数，避免跨库混淆。

对 ME-System 的落点：

- ME-Brain 查询必须有 canonical `project_id`；
- Project Resolver 只做确定性匹配；
- ME-Who 数据根据用户、项目、任务和 Agent Profile 裁剪；
- 禁止全库模糊匹配自动扩大权限。

### 2.8 Index Status 与 Coverage

Codebase-Memory 将索引状态、未解析文件和部分解析范围作为一等能力，避免 Agent 把缺失信息误认为“不存在”。

对 ME-System 的落点：

Source Ledger 和 Ingestion Run 必须提供：

- Adapter 与版本；
- 输入总量；
- 成功片段数；
- 跳过和失败数；
- Candidate 数；
- 未识别范围；
- 是否 partial；
- 质量报告和日志句柄。

未来 MCP 应增加只读：

```text
graph_get_schema
ingestion_get_status
graph_get_coverage
```

但在 Source Ledger 完成前不扩张当前六工具表面。

### 2.9 Incremental and Local

Codebase-Memory 支持后台增量索引和本地持久化。

对 ME-System 的落点：

- SourceRecord 使用幂等键和内容哈希；
- Adapter 重跑只处理变化来源；
- Candidate 使用幂等键；
- 权威图谱按 ChangeSet 增量提交；
- Linux/NAS 本地部署仍是第一优先级。

## 3. 不应照搬的能力

### 3.1 任意 Cypher 查询

Codebase-Memory 的代码图主要是工程结构，允许只读 Cypher风险可控。ME-System 包含 ME-Who 敏感数据，任意查询可能绕过字段、项目和任务范围。

结论：

- 不向普通 Agent 暴露任意 Cypher；
- 只保留类型化 Tool；
- 管理员查询若未来增加，必须独立权限和审计。

### 3.2 自动索引直接成为权威事实

AST、函数和调用关系大多可以确定性重建；用户偏好、项目决策和研究结论可能有歧义。

结论：

- 确定性结构可由规则确认；
- 语义事实进入 Candidate；
- Adapter 不能绕过 Candidate Review。

### 3.3 SQLite 单项目数据库

Codebase-Memory 的使用单位是本地代码项目；ME-System 需要跨项目、跨来源、审核事务和长期 ME-Who。

结论：继续使用一个 PostgreSQL 权威库，不改为每项目 SQLite。

### 3.4 大量工具一次开放

Codebase-Memory 已形成成熟产品，可以提供十多个工具。ME-System 仍处于核心语义验证期。

结论：

- Hermes 当前保持六个只读工具；
- 新增工具必须证明能减少 Token 或提升正确率；
- 优先做 schema/status/coverage，后做通用搜索；
- 写工具在 Candidate 持久化和审计完成后再开放。

### 3.5 单一静态二进制

这是部署优势，但不是当前 ME-System 的首要约束。

结论：先稳定 Python/PostgreSQL 语义；后续以容器、wheel 或原生组件优化部署。

## 4. 对当前 PR #5 的具体调整

### 4.1 Source Ledger 不是第二核心

Source Ledger 调整为 ME-Graph Core 内部的 `ingestion` 子系统：

```text
me_graph_core.ingestion
├── contracts
├── source_repository
├── candidate_repository
├── review
├── status
└── pipeline
```

### 4.2 Candidate Queue 是 Graph Buffer

参考 Codebase-Memory 的内存 Graph Buffer 思想，但 ME-System 的 Buffer 是可审计、可持久化的语义缓冲区：

```text
EvidenceFragment
→ CandidateGraphChange
→ Candidate Buffer
→ Review
→ Canonical Graph
```

### 4.3 IngestionRun 是 Index Status

`IngestionRun` 不只是后台任务记录，而是 Agent 和人判断图谱可信度的质量入口。

第一版增加：

```text
input_item_count
processed_item_count
skipped_item_count
failed_item_count
coverage_ratio
log_ref
```

### 4.4 一个事务边界

Candidate 批准、权威图谱写入、证据写入和 ReviewEvent 必须在同一个 PostgreSQL 事务中完成。

### 4.5 一个应用服务面

后续所有接口复用：

```text
SourceLedgerService
IngestionStatusService
CandidateReviewService
GraphQueryService
```

MCP、CLI 和未来 Web UI 只调用这些服务。

## 5. 推荐开发顺序

```text
1. 单核心 ADR 与 contracts
2. SourceRecord / EvidenceFragment / IngestionRun
3. Alembic 0002
4. SourceLedgerRepository
5. Persistent Candidate Buffer
6. 原子 Candidate Review
7. CLI parity
8. PostgreSQL E2E
9. Agent Conversation Pass
10. ingestion status / coverage MCP
```

## 6. 最终结论

ME-System 不应变成：

```text
ME-Brain 服务
+ ME-Who 服务
+ Source Ledger 服务
+ Candidate 服务
+ MCP 服务
+ Context 服务
```

而应保持：

```text
一个 ME-Graph Core
├── 两个权威图谱命名空间
├── 一个证据与候选摄取管线
├── 一个 PostgreSQL 真相源
├── 一个查询语义层
└── 多个薄前端（MCP / CLI / Web）
```

这就是从 Codebase-Memory 最应该吸收的核心优势。