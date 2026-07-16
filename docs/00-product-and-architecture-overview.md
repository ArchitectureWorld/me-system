# ME-System 产品与架构总纲

> 文档状态：初始稳定版  
> 日期：2026-07-16

## 1. 背景

最初的“第二大脑”概念同时包含了两类目标：

1. 让 Agent 更深入地理解用户本人；
2. 让 Agent 更高效地理解和推进科研、设计、开发等客观项目。

竞品分析后可以确认，这两类目标虽然共享大量基础能力，但核心对象、评价指标和风险完全不同，因此稳定为两条产品线：

- **ME-Who**：用户理解与个性化上下文系统；
- **ME-Brain**：项目结构化元数据与 Agent 项目上下文系统。

二者共同组成 ME-System。

---

## 2. 产品定义

### 2.1 ME-Who

ME-Who 实现的是 Agent 对“我”的理解提升，从而改善 Agent 使用 ME-Brain 及其他工具时的体验与效率。

它主要回答：

- 用户是谁；
- 用户掌握什么、缺少什么；
- 用户怎样思考和做决策；
- 不同场景下用户偏好什么交互方式；
- 哪些内容已经明确，不应再次询问；
- 哪些任务可以主动推进；
- 哪些决策必须由用户确认；
- 当前任务中哪些个人信息真正相关。

ME-Who 的核心输出不是静态“用户画像页面”，而是：

```text
compile_personal_context(
    user,
    task,
    project,
    agent,
    token_budget,
    permissions
)
```

输出内容包括：

- relevant_background；
- active_preferences；
- collaboration_rules；
- capability_assumptions；
- current_state；
- known_constraints；
- uncertain_inferences；
- do_not_use。

### 2.2 ME-Brain

ME-Brain 为科研、设计、开发等客观事件和项目推进提供结构化元数据，使 Agent 不必在每次任务中重新读取全部文件、聊天和历史记录。

它主要回答：

- 项目是什么；
- 项目当前处于什么阶段；
- 已确认需求和决策是什么；
- 哪些方案已经失效；
- 当前任务、风险和未解决问题是什么；
- 文件、成果、版本和决策之间是什么关系；
- 某项变化会影响哪些对象；
- 某条结论的证据在哪里。

其核心目标是：

- 降低 Token 消耗；
- 提升检索速度；
- 提升上下文准确度；
- 减少 Agent 重复理解；
- 保持项目任务连续性；
- 支持多个 Agent 使用同一个项目事实基础。

---

## 3. 二者关系

ME-Who 与 ME-Brain 不是完全平行的两个笔记库。

更准确的关系是：

| 产品 | 负责的问题 |
|---|---|
| ME-Brain | 这件事情是什么、当前状态是什么？ |
| ME-Who | 针对这个用户，Agent 应怎样理解、表达和行动？ |
| ME-Context | 在当前任务和 Token 预算下，应组合哪些内容？ |

统一任务上下文为：

```text
Task Context
= Current Request
+ Objective Project Context
+ Personal Context
```

ME-Brain 可以独立产生项目生产力价值；ME-Who 是横向增强层，可同时服务 ME-Brain、Hermes、OpenClaw、Codex、邮件助理、日程助理和其他 Agent。

第一阶段，ME-Who 应优先在 ME-Brain 的真实项目任务中验证，而不是先扩展成完整数字人格产品。

---

## 4. 共享核心

ME-Who 与 ME-Brain 应共享基础设施，但领域数据必须严格隔离。

### 4.1 共享能力

```text
ME-Core
├── Source Ledger
├── Identity Resolution
├── Temporal Model
├── Provenance
├── Permission System
├── Connector SDK
├── Retrieval Protocol
├── MCP / REST Contracts
└── Context Pack Base Types
```

### 4.2 ME-Who 独有领域

```text
ME-Who Domain
├── UserFact
├── BehavioralEvidence
├── Preference
├── Capability
├── Goal
├── CurrentState
├── CollaborationRule
└── ProfileSnapshot
```

### 4.3 ME-Brain 独有领域

```text
ME-Brain Domain
├── Project
├── Workstream
├── Requirement
├── Decision
├── Task
├── Milestone
├── Artifact
├── Document
├── Issue
├── Risk
├── Constraint
├── Experiment
├── Claim
├── Review
└── Event
```

---

## 5. 四层数据结构

ME-System 的数据不能被简单压平为“记忆”或“文档切块”。

### Layer 0：Source Ledger

不可变原始来源：

- 对话消息；
- 文件；
- Git 提交；
- 邮件；
- Zotero 记录；
- 网页；
- 日历；
- 图片与模型；
- Agent 输出和用户反馈。

每条来源至少具备：

```yaml
source_id:
source_type:
timestamp:
author:
raw_content_ref:
checksum:
permissions:
```

### Layer 1：Canonical Domain Data

经过规则、Agent 与人工确认后的权威领域数据：

- ME-Who 的明确事实、稳定协作规则等；
- ME-Brain 的项目决策、需求、任务、成果等。

### Layer 2：Derived Index

可重新生成的派生结构：

- 全文索引；
- 向量索引；
- 时间关系图；
- 自动实体和关系；
- 摘要；
- 社区与主题；
- 排序特征。

派生索引不得静默覆盖 Layer 1。

### Layer 3：Context Pack

针对任务、Agent、权限和 Token 预算临时生成的上下文，不直接回写为权威事实。

---

## 6. 同一来源的双向派生

同一条原始内容可以同时产生两个领域对象。

例如用户说：

> 先采用 B 方案，但是要给未来扩展留接口。

ME-Brain 中可以形成：

```yaml
type: project_decision
selected_option: B
constraints:
  - reserve_extension_interface
confirmation: explicit
```

ME-Who 中只形成候选行为证据：

```yaml
type: behavioral_evidence
candidate_traits:
  - prefers_incremental_architecture
  - values_extensibility
scope: technical_architecture
confidence: 0.78
```

一次行为不能直接升级为永久人格事实。只有用户明确确认，或多次证据稳定聚合后，才可以成为高置信度偏好或协作规则。

---

## 7. ME-Context Compiler

Context Compiler 是 ME-System 最重要的共享壁垒。

### 7.1 输入

```yaml
task:
agent:
user:
project:
token_budget:
required_freshness:
evidence_level:
permissions:
```

### 7.2 输出

```yaml
current_request:
project_brief:
current_project_state:
relevant_decisions:
active_constraints:
open_issues:
related_artifacts:
recent_changes:
personal_background:
active_preferences:
collaboration_rules:
uncertain_inferences:
evidence_refs:
excluded_outdated_facts:
```

### 7.3 编译原则

1. 先结构化过滤，再进行全文、向量和图关系扩展；
2. 优先当前有效的确认事实；
3. 明确排除过期方案；
4. 个人信息仅在与任务相关且有权限时装载；
5. 默认加载摘要，必要时再展开证据；
6. 在 Token 预算内分配项目事实、个人上下文和原始证据；
7. 输出中标识事实、推断和候选信息的差异。

---

## 8. 渐进式上下文展开

推荐五级上下文深度：

| 层级 | 内容 | 默认行为 |
|---|---|---|
| L1 | 项目身份、阶段、目标 | 默认加载 |
| L2 | 当前任务、决策、约束、问题 | 默认加载 |
| L3 | 相关实体、事件和关系 | 按查询加载 |
| L4 | 原始证据片段 | 需要验证时加载 |
| L5 | 完整原始文件或历史对话 | 最后下钻 |

降低 Token 的关键不是简单压缩文本，而是让 Agent 在正确的结构层级上开始工作。

---

## 9. 核心边界

### 9.1 ME-Who 不修改项目真相

ME-Who 可以影响：

- 检索排序；
- 输出颗粒度；
- Agent 自主度；
- 解释方式；
- 是否重复询问；
- 交付格式。

它不能因为用户可能喜欢某方案，就修改 ME-Brain 的项目决策。

### 9.2 Agent 默认只提交候选更新

Agent 不能未经确认直接写入：

- 稳定用户偏好；
- 项目正式决策；
- 技术路线；
- 研究结论；
- 人物关系；
- 能力判断。

### 9.3 所有高价值结论必须可追溯

至少应记录：

```yaml
source_id:
derived_from:
created_by:
confirmation_status:
valid_from:
valid_to:
supersedes:
confidence:
```

### 9.4 权限从第一版开始设计

ME-Who 的敏感数据不能默认暴露给所有项目 Agent。权限至少需要支持：

- owner；
- family agent；
- project agent；
- external agent；
- public export。

---

## 10. 当前开发战略

1. 使用 Monorepo 组织两个产品和共享核心；
2. ME-Brain 作为第一阶段主要生产力产品；
3. 同期建设只服务协作效率的最小 ME-Who；
4. 优先稳定 Source、Provenance、Temporal 和 Context Pack 协议；
5. 首先验证真实项目恢复、Token 降低和事实准确度；
6. 核心领域模型自建，外部解析、图谱、检索和连接器保持可替换；
7. 软件、科研、设计分别建设领域包，不建立大而全的万能本体。

---

## 11. 第一批验证项目

推荐选择三种不同类型的真实项目：

1. **lighting-platform**：软件与工程技术开发；
2. **Zotero / 论文工作流**：科研和文献管理；
3. **AI 超级画板或泰典物业**：设计与产品项目。

固定评估问题包括：

- 当前状态是什么；
- 已确认路线是什么；
- 哪些方案已经失效；
- 当前未解决问题是什么；
- 某项变化影响什么；
- 结论的证据在哪里；
- Agent 是否重复询问用户已经明确的信息。

对比基线：

```text
A. Agent 直接探索全部文件
B. 普通向量 RAG
C. ME-Brain 结构化项目上下文
D. ME-Brain + ME-Who 组合上下文
```

该评估将决定后续图数据库、检索引擎和上下文编译策略，而不是先根据技术流行度确定架构。
