# ME-Brain 本体 v0.1

## 1. 节点类型

| 类型 | 含义 |
|---|---|
| Project | 项目身份、目标、阶段与范围 |
| Decision | 已确认或历史决策 |
| Requirement | 项目需求与验收目标 |
| Task | 可执行工作项 |
| Issue | 当前问题或缺口 |
| Constraint | 技术、业务、时间或范围约束 |
| Artifact | 文档、代码、图纸、模型、数据等成果 |
| Person | 项目参与者的客观项目身份 |
| Evidence | 需要被复用为节点的证据对象 |

## 2. 关系约束

| 关系 | Source | Target | 语义 |
|---|---|---|---|
| HAS_DECISION | Project | Decision | 项目具有决策 |
| HAS_REQUIREMENT | Project | Requirement | 项目具有需求 |
| HAS_TASK | Project | Task | 项目具有任务 |
| HAS_ISSUE | Project | Issue | 项目具有问题 |
| HAS_CONSTRAINT | Project | Constraint | 项目具有约束 |
| HAS_ARTIFACT | Project | Artifact | 项目具有成果 |
| SUPERSEDES | Decision | Decision | 新决策替代旧决策 |
| SATISFIES | Decision/Artifact | Requirement | 满足需求 |
| DEPENDS_ON | Task/Artifact | Task/Artifact/Decision | 依赖对象 |
| BLOCKS | Issue/Task | Task/Milestone | 阻塞推进 |
| PRODUCES | Task/Experiment | Artifact | 产生成果 |
| IMPLEMENTS | Artifact | Decision/Requirement | 成果实现决策或需求 |
| SUPPORTED_BY | Any | Evidence | 证据支持对象 |

## 3. v0.1 查询语义

### Project Snapshot

返回：

- Project；
- 当前有效的第一层 Project 关系对象；
- 这些对象之间的内部关系；
- 被排除的 superseded 节点；
- 证据句柄。

### Decision Trace

沿 `SUPERSEDES` 双向展开，保留完整历史链。

### Change Impact

v0.1 暂不自动实现。等 `DEPENDS_ON`、`IMPLEMENTS` 和 `SATISFIES` 的真实数据足够后再增加。

## 4. 扩展方式

Software、Research、Design 领域包可以新增节点和边，但不能修改本体 v0.1 的既有语义。
