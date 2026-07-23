# ADR-0005：ME-System 采用单一图谱内核

- 状态：Accepted
- 日期：2026-07-23
- 参考：Codebase-Memory MCP
- 上位决策：ADR-0004 双权威图谱

## 决策

ME-System 保持两个业务图谱：

- ME-Brain Graph
- ME-Who Graph

但工程实现只允许存在**一个语义内核**：

```text
services/me-graph-core
```

双图谱是同一个内核中的两个权威命名空间，不是两个独立后端。Source Ledger、Evidence、Candidate、Query、MCP、CLI 和后续 Adapter 都围绕该内核运行，不再演化为平级核心或独立真相源。

## 一句话架构

```text
Adapters / Ingestion Passes
          │
          ▼
     ME-Graph Core
├── Source & Evidence
├── Candidate Buffer
├── ME-Brain Graph
├── ME-Who Graph
├── Bridge
├── Query & Projection
└── Quality / Status
          │
     ┌────┴────┐
     ▼         ▼
    MCP       CLI
```

## 受 Codebase-Memory 启发的原则

### 1. 一个结构化后端

Codebase-Memory 将索引、图谱存储、结构查询和 MCP 服务统一在一个结构分析后端中，Agent 只负责理解问题和调用工具。ME-System 采用同样原则：

- 后端不嵌入用于回答问题的 LLM；
- Adapter 可以使用模型生成候选，但模型不成为权威内核；
- 图谱查询语义只在 `me-graph-core` 中定义一次；
- MCP 和 CLI 只是同一能力的两个前端。

### 2. 多阶段摄取，但不拆出多个核心

后续输入处理采用可组合 Pass：

```text
Discover
→ Normalize
→ Fragment
→ Extract Candidate
→ Resolve Identity
→ Detect Conflict
→ Review
→ Commit Canonical Graph
→ Build Derived Index
```

每个 Pass 可以独立测试和替换，但均通过统一契约交换数据，不拥有独立权威数据库。

### 3. 结构优先、按需下钻

Agent 默认获取紧凑结构结果，再按需要读取关系、证据和原文：

```text
Project Resolve
→ Snapshot / Summary
→ Targeted Subgraph
→ EvidenceRef
→ Raw Source
```

默认响应必须包含截断、覆盖率或质量信号，不能让 Agent 把不完整结果误认为完整事实。

### 4. 项目范围显式

所有 ME-Brain 查询必须明确项目。禁止依赖全库模糊搜索自动扩大权限。ME-Who 只返回任务相关且授权的数据。

### 5. MCP 工具由单一注册表生成

MCP 工具的以下内容必须来自同一声明：

- 工具名；
- 描述；
- 输入 Schema；
- 输出 Schema；
- read-only / destructive / idempotent 等注解；
- 工具 Profile。

CLI 与 MCP 应复用同一应用服务，不复制查询逻辑。

## 不照搬 Codebase-Memory 的部分

### 1. 不改用 SQLite 作为 ME-System 权威库

Codebase-Memory 以本地代码库索引为目标，SQLite 很合适。ME-System 需要跨项目、跨来源、审核事务和 ME-Who 隐私治理，因此继续使用 PostgreSQL 作为唯一权威存储。

### 2. 不向 Agent 暴露任意 Cypher

ME-Who 包含敏感个人数据。v0.x 只开放类型化、受项目和权限约束的查询工具。任意图查询仅可作为受信任管理员能力评估，不能默认暴露给 Hermes、Pi 或 Codex。

### 3. 不让自动索引直接改权威图谱

代码 AST 是确定性结构，Codebase-Memory 可以直接索引；个人偏好、项目决策和研究结论存在语义歧义。ME-System 的自动 Pass 只能提交 Candidate，必须通过规则或人工审核后进入权威图谱。

### 4. 不追求第一阶段单一静态二进制

当前重点是稳定图谱语义和输入治理。Python + PostgreSQL 保持不变；只有部署、性能和分发指标证明必要时，才评估原生核心或单文件分发。

## 代码边界

```text
services/me-graph-core/src/me_graph_core/
├── contracts.py
├── store.py
├── query.py
├── persistence/
├── ingestion/
├── adapters/
├── hermes/
└── cli.py
```

约束：

1. `ingestion/` 是内核子系统，不是新产品；
2. `adapters/` 只负责来源到标准输入/候选的转换；
3. `hermes/` 只负责 MCP 适配，不定义图谱业务规则；
4. Domain Pack 只能扩展本体、Pass 和查询，不创建第二套 Store；
5. 所有权威写入最终经过同一 PostgreSQL 事务边界。

## 当前实施影响

Source Ledger 与 Candidate 持久化继续在 `me-graph-core` 内实现：

```text
PostgreSQL
├── graph_objects
├── graph_evidence_refs
├── source_records
├── evidence_fragments
├── ingestion_runs
├── candidate_graph_changes
├── candidate_evidence_refs
└── candidate_review_events
```

不会新增：

- `source-ledger` 独立服务；
- `candidate-service`；
- 第二个数据库；
- 独立 MCP Core；
- Adapter 自有权威 Schema。

## 后续评审触发条件

只有满足以下任一条件，才重新评估拆分：

- 单机数据库无法满足已测量的吞吐或容量；
- 独立团队与独立发布周期已经形成；
- 安全边界要求物理隔离；
- 核心协议稳定且拆分收益有可量化证据。

在此之前，优先保持一个核心、一个权威数据库、一个图谱语义来源。