# ME-Who 本体 v0.1

## 1. 节点类型

| 类型 | 含义 |
|---|---|
| User | 用户身份根节点 |
| Role | 职业、项目或生活角色 |
| Capability | 有证据支持的能力 |
| Preference | 有范围和证据的偏好 |
| CollaborationRule | 直接约束 Agent 协作方式的规则 |
| Goal | 长期或阶段目标 |
| ProjectRole | 用户在某个项目中的职责 |
| Evidence | 需要被复用为节点的个人证据 |

## 2. 关系约束

| 关系 | Source | Target | 语义 |
|---|---|---|---|
| HAS_ROLE | User | Role | 用户具有角色 |
| HAS_CAPABILITY | User | Capability | 用户具有能力 |
| PREFERS | User | Preference | 用户具有偏好 |
| HAS_COLLABORATION_RULE | User | CollaborationRule | 用户确认协作规则 |
| HAS_GOAL | User | Goal | 用户具有目标 |
| SUPPORTED_BY | Any | Evidence | 信息由证据支持 |
| SUPERSEDES | Preference/Rule/Goal | 同类节点 | 新信息替代旧信息 |
| CONFIRMED_BY | Any | User | 用户确认信息 |

## 3. Scope 字段

Preference 与 CollaborationRule 的 `properties` 至少支持：

```yaml
task_types: []
project_ids: []
domains: []
agent_types: []
```

空数组表示在该维度不限制。

## 4. Bridge 关系

| 关系 | Source | Target |
|---|---|---|
| PARTICIPATES_IN | User | Project |
| APPLIES_TO_PROJECT | ProjectRole/Rule | Project |

## 5. 推断升级规则

```text
单次行为
→ Candidate Evidence
→ 多次一致证据或用户确认
→ Canonical Preference / CollaborationRule
```

v0.1 不允许一次对话直接创建永久人格标签。
