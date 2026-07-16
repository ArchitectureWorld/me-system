# ME-Who 产品定义

> 定位：面向 Agent 的可治理用户理解与个性化上下文系统。

## 1. 产品目标

ME-Who 的目标不是复制用户人格，也不是建立一份静态用户画像，而是持续提高 Agent 对用户的理解，使 Agent 能够在不同任务中选择更合适的：

- 信息颗粒度；
- 表达方式；
- 行动自主度；
- 确认节点；
- 风险提醒方式；
- 输出格式；
- 上下文装载范围。

第一阶段最明确的价值验证场景是：

> 通过 ME-Who 提供的 Personal Context，提升用户使用 ME-Brain 和项目 Agent 时的体验与效率。

## 2. ME-Who 解决的问题

### 2.1 减少重复说明

Agent 应知道用户已经明确的：

- 专业背景；
- 技术环境；
- 工作偏好；
- 长期目标；
- 项目角色；
- 输出要求；
- 已确认的协作规则。

### 2.2 减少错误协作方式

例如：

- 架构级重大决策需要先讨论；
- 明确的小型实现任务可以直接执行；
- 已稳定结论不应反复询问；
- 每次专业开发应形成开发记录；
- 输出需要先收敛架构，再下沉细节。

### 2.3 按任务装载用户信息

项目 Agent 不需要读取用户全部私人信息。ME-Who 应根据：

- 当前任务；
- Agent 身份；
- 项目；
- 权限；
- Token 预算；
- 信息敏感度；

生成最小、相关、可解释的 Personal Context。

## 3. 非目标

第一阶段不建设：

- 数字分身社交；
- 自动代表用户公开发言；
- 个人模型微调；
- 心理诊断；
- 从单次行为推断永久人格；
- 无限制监听用户环境；
- 大而全的人生知识图谱；
- 以“像不像用户”为主要评价指标。

## 4. 核心对象

### 4.1 UserFact

用户明确表达或可直接验证的事实。

示例：

```yaml
type: UserFact
subject: user
predicate: primary_profession
value: architecture_engineer
confirmation_status: explicit
```

### 4.2 BehavioralEvidence

从用户行为、反馈或选择中观察到的证据。它本身不是稳定偏好。

```yaml
type: BehavioralEvidence
observation: 用户要求明确任务直接执行，不再重复确认
scope: software_implementation
confidence: 0.92
```

### 4.3 Preference

由用户明确确认，或由多条行为证据稳定支持的偏好。

```yaml
type: Preference
predicate: prefers_architecture_first
scope: product_and_technical_design
confirmation_status: inferred_confirmed
```

### 4.4 Capability

用户在特定领域的能力、经验和边界。应避免使用单一“初级/高级”标签，而采用领域和证据化描述。

### 4.5 Goal

长期或阶段性目标，必须具有状态与有效期。

### 4.6 CurrentState

可能快速变化的信息，例如当前重点项目、近期压力、临时安排。不得自动升级为长期画像。

### 4.7 CollaborationRule

直接影响 Agent 行为的规则。

```yaml
type: CollaborationRule
rule: 对已确认的实现细节直接执行，不重复询问
scope:
  agent_types: [coding_agent]
  task_types: [implementation, bugfix]
priority: high
```

### 4.8 ProfileSnapshot

某一时间点的阶段性综合画像。Snapshot 是派生视图，不是底层事实源。

## 5. 通用字段

所有高价值 ME-Who 对象至少具备：

```yaml
id:
source_ids: []
derived_from: []
scope:
confidence:
confirmation_status:
valid_from:
valid_to:
sensitivity:
allowed_agents: []
supersedes:
created_by:
created_at:
```

### confirmation_status 建议值

```text
explicit                 用户明确表达
explicit_confirmed       用户二次确认
observed                 行为证据
inferred_candidate       系统推断候选
inferred_confirmed       推断经用户确认
rejected                 用户否定
superseded               被后续信息替代
```

## 6. 适用范围 Scope

ME-Who 不能只维护一份全局 Profile。偏好和规则至少可以限定到：

- agent；
- agent_type；
- domain；
- project；
- task_type；
- role；
- time_window；
- interaction_surface。

例如，同一用户可能同时满足：

```text
科研讨论：需要来源验证和严谨论证
明确开发任务：倾向直接执行
架构决策：需要先比较和确认
视觉设计：先看整体风格，再细化页面
```

这些规则不能互相覆盖。

## 7. 信息产生流程

### 显式事实流程

```text
用户明确表达
→ 提取结构化候选
→ 检查重复与冲突
→ 写入权威用户事实
```

### 行为推断流程

```text
用户行为或反馈
→ BehavioralEvidence
→ 多次聚合
→ Preference / CollaborationRule Candidate
→ 用户确认或达到受控规则阈值
→ 稳定上下文对象
```

任何一次行为都不能直接生成永久人格标签。

## 8. Personal Context Compiler

### 输入

```yaml
user_id:
task:
project_id:
agent_id:
agent_type:
token_budget:
permissions:
```

### 输出

```yaml
relevant_background: []
active_preferences: []
collaboration_rules: []
capability_assumptions: []
current_state: []
known_constraints: []
uncertain_inferences: []
do_not_use: []
evidence_refs: []
```

### 编译原则

1. 明确事实优先于推断；
2. 当前任务 Scope 优先于全局偏好；
3. 当前有效状态优先于历史状态；
4. 不相关的私人信息不装载；
5. 敏感信息必须通过权限检查；
6. 候选推断必须显式标记；
7. 用户可以查看某条上下文为何被使用。

## 9. 核心界面

第一版只需要四个治理界面：

1. **我是谁**：明确事实、专业背景、长期目标；
2. **Agent 怎样与我协作**：协作规则与适用范围；
3. **系统推断了什么**：候选偏好及证据；
4. **信息怎样被使用**：Agent、任务、时间和来源审计。

## 10. 核心 MCP / API

```text
get_explicit_user_facts
get_collaboration_rules
get_relevant_preferences
get_current_user_state
explain_personal_context
submit_behavioral_evidence
list_profile_candidates
confirm_profile_candidate
reject_profile_candidate
compile_personal_context
```

写操作必须区分：

- 添加明确事实；
- 提交候选证据；
- 确认候选；
- 修改 Scope；
- 删除或禁止使用。

## 11. 第一阶段评价指标

ME-Who 不以“记住多少信息”为核心指标。

建议指标：

- Agent 重复询问次数；
- 用户纠正 Agent 工作方式的频率；
- 首轮输出可用率；
- Personal Context 的相关率；
- 错误或过期偏好的使用率；
- 推断可解释率；
- 敏感信息越权使用次数；
- 同一 ME-Brain 项目在启用 ME-Who 前后的任务完成差异。

## 12. 第一版范围

优先实现：

- 明确用户事实；
- 专业背景；
- Agent 协作规则；
- 稳定工作偏好；
- 项目角色；
- 用户反馈形成的行为证据；
- Personal Context Pack；
- 来源、范围、权限和确认状态。

后置：

- 完整生活经历；
- 人际关系深层建模；
- 数字身份与人格训练；
- 自动代表用户对外沟通。
