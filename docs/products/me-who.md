# ME-Who 产品定义

> 定位：面向 Agent 的任务相关用户理解权威图谱。

## 1. 解决的问题

ME-Who 不复制用户人格，也不建立泛化心理画像。

它只保存 Agent 为完成任务所需的、可解释和可治理的信息：

- 用户的明确角色和专业背景；
- 已确认能力；
- 长期或阶段目标；
- 有适用范围的偏好；
- Agent 协作规则；
- 用户在项目中的角色；
- 支持这些信息的原始证据。

## 2. v0.1 节点

```text
User
Role
Capability
Preference
CollaborationRule
Goal
ProjectRole
Evidence
```

## 3. v0.1 关系

```text
HAS_ROLE
HAS_CAPABILITY
PREFERS
HAS_COLLABORATION_RULE
HAS_GOAL
SUPPORTED_BY
SUPERSEDES
CONFIRMED_BY
```

跨项目关系通过 Bridge：

```text
PARTICIPATES_IN
APPLIES_TO_PROJECT
```

## 4. Scope

偏好和规则不是全局永久标签，至少支持：

```text
task_types
project_ids
domains
agent_types
valid_from / valid_to
```

例如：

```text
technical_architecture → 先收敛架构再实现
implementation         → 明确任务直接执行
```

## 5. 权限

ME-Who 默认比 ME-Brain 更敏感。

- Hermes：只读取与当前任务相关的节点；
- Pi、Codex：默认不读取完整 ME-Who；
- 执行 Agent 只接收必要协作规则；
- 外部 Agent 默认拒绝。

## 6. 推断边界

一次行为只能生成候选证据，不能直接生成稳定偏好。

```text
行为或反馈
→ CandidateGraphChange
→ 多次证据或用户确认
→ Canonical Preference / CollaborationRule
```

## 7. 关键查询

```text
get_task_profile(user_id, project_id, task_type)
explain_user_item(node_id)
get_evidence(node_or_edge_id)
```

## 8. 成功标准

- 减少重复询问；
- 减少错误协作方式；
- 不暴露无关私人信息；
- 用户能解释、修改和删除个人图谱内容；
- 同一项目在不同任务类型下返回不同协作规则。
