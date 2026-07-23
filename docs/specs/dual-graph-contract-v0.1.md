# 双图谱契约 v0.1

> 状态：已落地到 `services/me-graph-core`

## 1. GraphNode

```yaml
schema_version: graph-node/0.1
id: brain:decision:radiance-primary
graph: me_brain
type: Decision
label: Radiance 作为主计算核心
properties: {}
authority: canonical
confirmation_status: human_confirmed
status: current
valid_from: 2026-07-14T00:00:00Z
valid_to: null
sensitivity: project_private
source_refs: []
```

规则：

- ME-Brain 节点 ID 必须以 `brain:` 开头；
- ME-Who 节点 ID 必须以 `who:` 开头；
- Bridge 不允许创建节点；
- 每个节点至少有一个 `EvidenceRef`；
- `valid_to` 不得早于 `valid_from`；
- canonical 节点必须已经确认。

## 2. GraphEdge

```yaml
schema_version: graph-edge/0.1
id: edge:radiance-supersedes-cycles
graph: me_brain
type: SUPERSEDES
from_id: brain:decision:radiance-primary
to_id: brain:decision:cycles-primary
properties: {}
authority: canonical
confirmation_status: human_confirmed
confidence: 1.0
valid_from: 2026-07-14T00:00:00Z
valid_to: null
sensitivity: project_private
source_refs: []
```

规则：

- 不允许自环；
- 普通边的两端必须属于同一图谱；
- 跨图关系必须使用 `graph: bridge`；
- Bridge 边必须连接不同图谱；
- 每条边至少有一个证据引用。

## 3. EvidenceRef

```yaml
source_id:
document_id:
version_id:
content_fragment_id:
source_anchor:
  type: conversation_message
  value:
    message_id: "42"
```

EvidenceRef 负责把图谱对象定位回原始消息、文档节点、Git 记录、Zotero 条目或其他来源。

## 4. CandidateGraphChange

```yaml
schema_version: candidate-graph-change/0.1
change_id:
target_graph: me_brain
operation: add_node
submitted_by: hermes-primary
reason:
evidence_refs: []
payload: {}
review_status: pending
reviewed_by: null
review_reason: null
```

v0.1 只支持：

```text
add_node
add_edge
```

候选 payload 必须使用：

```text
authority: candidate
confirmation_status: pending
```

批准后转换为 `human_confirmed` 或 `rule_confirmed`，再写入权威图谱。

## 5. GraphSlice

```yaml
schema_version: graph-slice/0.1
slice_id:
graph: me_brain
as_of_time:
root_ids: []
summary:
nodes: []
edges: []
evidence_handles: []
excluded:
  superseded: []
  unauthorized: []
truncated: false
```

GraphSlice 是 Agent 查询结果和 Context Projection 的基础。

## 6. 存储接口

v0.1 定义：

```text
add_node
add_edge
get_node
get_edge
get_object
list_nodes
list_edges
neighbors
```

当前实现为 `InMemoryGraphStore`。持久化数据库必须保持相同语义。
