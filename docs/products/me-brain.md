# ME-Brain 产品定义

> 定位：面向 Agent 的客观项目权威图谱。

## 1. 解决的问题

ME-Brain 让 Agent 不必每次重新扫描项目文件，就能知道：

- 项目目标和当前阶段；
- 当前有效需求、决策和约束；
- 哪些方案已经被替代；
- 哪些任务被什么问题阻塞；
- 成果实现了哪些决策；
- 某项变化可能影响什么；
- 每条结论的原始证据在哪里。

## 2. v0.1 节点

```text
Project
Decision
Requirement
Task
Issue
Constraint
Artifact
Person
Evidence
```

## 3. v0.1 关系

```text
HAS_DECISION
HAS_REQUIREMENT
HAS_TASK
HAS_ISSUE
HAS_CONSTRAINT
HAS_ARTIFACT
SUPERSEDES
SATISFIES
DEPENDS_ON
BLOCKS
PRODUCES
IMPLEMENTS
SUPPORTED_BY
```

## 4. 关键查询

```text
get_project_snapshot(project_id)
expand_subgraph(node_id, depth)
trace_decision(decision_id)
get_evidence(node_or_edge_id)
```

## 5. 当前与历史

被替代事实不能删除。

```text
Radiance --SUPERSEDES--> Cycles
```

当前项目快照默认只返回当前有效节点，同时在 `excluded.superseded` 中说明被排除的历史节点。

## 6. 写入边界

以下信息不能由 Agent 直接写入权威图：

- 正式决策；
- 项目完成状态；
- 技术路线；
- 高价值需求；
- 研究结论。

Agent 只能提交带证据的 `CandidateGraphChange`。

## 7. 成功标准

与直接文件探索相比：

- 项目恢复 Token 明显降低；
- 当前路线识别准确；
- 过期方案不被误用；
- 决策来源覆盖率高；
- 阻塞和影响关系可查询；
- Hermes 可通过少量工具完成项目恢复。
