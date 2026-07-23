# Hermes Read-only MCP Design

> 状态：首版已实现并通过 CI  
> 日期：2026-07-23  
> 范围：Project ID Resolve、只读 Graph Query 工具、Hermes stdio MCP 接入

## 1. 目标

让 Hermes 从简短任务表达中确定项目，并通过只读 MCP 工具读取 ME-Brain 与任务相关 ME-Who，而不是重新扫描全部文件。

第一条端到端场景：

```text
用户：继续推进 lighting-platform
→ Hermes 调用 brain_resolve_project
→ 得到 brain:project:lighting-platform
→ Hermes 调用 brain_get_snapshot
→ 得到当前决策、约束、任务、问题和证据句柄
→ Hermes 按任务类型调用 who_get_task_profile
→ 形成下一步行动
```

## 2. 外部兼容基线

Hermes 当前支持：

- 在 `~/.hermes/config.yaml` 的 `mcp_servers` 下配置 MCP；
- 本地 stdio 与远程 HTTP MCP；
- 启动时自动发现工具；
- `tools.include` 白名单；
- 将 Server 原生工具注册为 `mcp_<server>_<tool>`。

本切片使用 stdio，因为数据库与 MCP Server 预期部署在 Hermes 同一台 Linux / NAS 主机，不增加网络暴露。

MCP Python SDK 固定为：

```text
mcp>=1.27,<2
```

显式 `<2` 避免 MCP Python SDK v2 发布后发生非受控主版本升级。

## 3. 非目标

首版不实现：

- 图谱写入或 Candidate 提交；
- Pi Extension；
- Streamable HTTP 生产部署；
- OAuth；
- 字段级内容脱敏；
- LLM 模糊项目匹配；
- 多用户动态身份切换；
- Handoff Pack；
- 自动修改 Hermes Context File；
- 对话、Markdown 或 Git Adapter。

## 4. 架构

```text
Hermes
  │ stdio MCP
  ▼
ME-Graph MCP Adapter
  ├── HermesServerSettings
  ├── ProjectResolver
  ├── ProjectScopeGuard
  └── HermesReadOnlyTools
          │
          ▼
   GraphQueryService
          │
          ▼
   PostgreSQL GraphStore
```

边界原则：

- MCP Adapter 不执行 SQL；
- MCP Adapter 不定义新的图谱 Schema；
- 所有业务查询复用 `GraphQueryService`；
- Agent 无法通过工具参数切换用户身份；
- 项目权限由服务端配置注入；
- stdout 只用于 MCP framing，诊断日志写 stderr；
- Hermes 使用 PostgreSQL 只读账号。

## 5. Project Resolver

### Project 属性

ME-Brain `Project.properties` v0.1 支持：

```yaml
aliases:
  - lighting platform
  - 照明平台
workspace_paths:
  - /workspace/lighting-platform
external_ids:
  github: ArchitectureWorld/lighting-platform
  slug: lighting-platform
```

### 输入

```yaml
query: lighting-platform
working_directory: /workspace/lighting-platform
external_system: github
external_id: ArchitectureWorld/lighting-platform
```

至少提供一个输入。

### 匹配优先级

```text
1. canonical_id
2. external_id
3. workspace_path
4. label
5. alias
```

所有匹配均为确定性精确匹配：

- 文本执行 Unicode NFKC、trim、casefold；
- 工作目录执行绝对路径规范化；
- 不使用向量、编辑距离或 LLM。

同一优先级出现多个候选时返回 `ambiguous`，不擅自选择。

### 输出

```yaml
status: resolved | ambiguous | not_found
project_id: brain:project:lighting-platform | null
match_type: canonical_id | external_id | workspace_path | label | alias | null
matched_value: lighting-platform | null
confidence: 1.0 | 0.0
candidates:
  - project_id: ...
    label: ...
```

## 6. 服务端配置

```text
ME_GRAPH_DATABASE_URL               必填
ME_GRAPH_HERMES_USER_ID             必填，固定 ME-Who 用户
ME_GRAPH_ALLOWED_PROJECT_IDS        必填，逗号分隔或显式 *
ME_GRAPH_MAX_SUBGRAPH_DEPTH         可选，默认 2，最大 3
ME_GRAPH_MCP_LOG_LEVEL              可选，默认 WARNING
```

默认拒绝：

- 未配置项目 allowlist 时拒绝启动；
- `*` 仅适用于用户明确允许全部项目的个人实例；
- `who_get_task_profile` 不暴露 `user_id` 参数；
- 数据库 URL 不出现在 Agent 错误中。

当前 Hermes MCP 配置要求在 `env` 中显式填写值，不能假设 `${VAR}` 会自动展开。因此示例使用明显占位值，并要求本地替换与 `chmod 600 ~/.hermes/config.yaml`。

## 7. 项目范围保护

### 项目所有权

项目成员首先通过从 Project 出发的显式所有权关系确定：

```text
HAS_DECISION
HAS_REQUIREMENT
HAS_TASK
HAS_ISSUE
HAS_ARTIFACT
HAS_CONSTRAINT
```

任意 `SATISFIES`、`BLOCKS`、`IMPLEMENTS` 或其他语义边不能扩大授权边界。

### 历史决策

已归属项目的 Decision 可以沿有界 `SUPERSEDES` 链读取历史 Decision，但满足以下规则：

- 历史节点必须仍是 ME-Brain Decision；
- 若另一个 Project 通过 `HAS_DECISION` 明确拥有该节点，当前项目不能借关系读取；
- 工具输出再次按项目成员集合裁剪。

### 对象工具

以下工具同时要求 `project_id`：

```text
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
```

Bridge、ME-Who 或其他项目对象均不能通过这些工具读取。

## 8. MCP 工具

第一版固定六个工具：

### `brain_resolve_project`

通过名称、canonical ID、alias、工作目录或外部 ID 解析允许项目。

### `brain_get_snapshot`

返回当前项目 GraphSlice，过期决策进入 `excluded.superseded`。

### `brain_expand_subgraph`

输入：

```yaml
project_id:
node_id:
depth: 1
edge_types: []
```

`depth` 不得超过服务端配置值，配置绝对上限为 3。

### `brain_trace_decision`

返回当前项目范围内的 `SUPERSEDES` 决策链。

### `brain_get_evidence`

返回稳定 `EvidenceRef[]`，首版不返回原始正文。

### `who_get_task_profile`

返回服务端固定用户在当前项目与任务类型下的 ME-Who 子图。

## 9. 工具返回和错误

成功：

```yaml
ok: true
result: ...
```

失败：

```yaml
ok: false
error:
  code: PROJECT_NOT_ALLOWED
  message: requested project is outside the configured Hermes scope
  retryable: false
```

错误不得包含：

- 数据库密码；
- 完整连接字符串；
- Python traceback；
- 未授权项目名称列表。

## 10. MCP Server 实现

模块：

```text
src/me_graph_core/hermes/
├── __init__.py
├── settings.py
├── resolver.py
├── access.py
├── tools.py
└── mcp_server.py
```

入口：

```text
me-graph-mcp
```

FastMCP：

```python
FastMCP(
    name="ME-System Graph",
    instructions="Read-only ME-Brain and task-scoped ME-Who graph tools.",
    json_response=True,
)
```

运行：

```python
mcp.run(transport="stdio")
```

## 11. Hermes 配置

当前可执行示例：

```yaml
mcp_servers:
  me_system:
    command: "me-graph-mcp"
    env:
      ME_GRAPH_DATABASE_URL: "postgresql+psycopg://me_graph_reader:REPLACE_ME@127.0.0.1:5432/me_graph"
      ME_GRAPH_HERMES_USER_ID: "who:user:master"
      ME_GRAPH_ALLOWED_PROJECT_IDS: "brain:project:lighting-platform"
      ME_GRAPH_MAX_SUBGRAPH_DEPTH: "2"
    tools:
      include:
        - brain_resolve_project
        - brain_get_snapshot
        - brain_expand_subgraph
        - brain_trace_decision
        - brain_get_evidence
        - who_get_task_profile
      prompts: false
      resources: false
```

白名单使用 Server 原始工具名。Hermes 注册后模型看到的名称为：

```text
mcp_me_system_brain_resolve_project
mcp_me_system_brain_get_snapshot
...
```

Bootstrap 只说明调用顺序，动态项目状态不写进 `.hermes.md` 或 `AGENTS.md`。

## 12. 测试与验证

### 单元与契约

覆盖：

- 五类项目解析；
- 匹配优先级、ambiguous、not_found；
- 环境配置与深度限制；
- project allowlist；
- 固定 ME-Who 用户；
- 项目成员、Bridge 与跨项目关系；
- 六个工具和统一错误结构；
- FastMCP 只注册六个工具。

### PostgreSQL stdio E2E

CI 使用 PostgreSQL 16：

1. 创建随机 Schema；
2. 执行 Alembic 迁移；
3. 导入 `lighting-platform`；
4. 启动 `me-graph-mcp` 子进程；
5. MCP `ClientSession.initialize()`；
6. `list_tools()` 验证六工具；
7. 调用 resolve、snapshot、task profile；
8. 验证 Radiance 当前、Cycles 被排除；
9. 验证未授权项目返回结构化错误；
10. 删除测试 Schema。

最终验证矩阵：

```text
Python 3.11 unit + contracts + FastMCP registration
Python 3.12 unit + contracts + FastMCP registration
PostgreSQL 16 GraphStore integration
PostgreSQL 16 stdio MCP E2E
```

## 13. 验收标准

- 项目通过 canonical ID、label、alias、工作目录和 external ID 解析；
- 解析不使用 LLM 和模糊猜测；
- Hermes 只获得六个只读工具；
- 非允许项目与跨项目对象无法返回；
- 工具参数不能切换 ME-Who 用户；
- PostgreSQL 重启后 MCP 查询结果一致；
- “继续推进 lighting-platform”流程不要求扫描全部项目文件；
- Python 3.11 / 3.12 + PostgreSQL 16 CI 通过；
- MCP SDK 固定 `<2`。

## 14. 后续

1. 在真实 Hermes 中进行项目恢复 Benchmark；
2. Agent Conversation Adapter 产生 CandidateGraphChange；
3. pending Candidate 持久化与审核；
4. 证据正文读取、字段级权限和脱敏；
5. Streamable HTTP / OAuth；
6. Pi Extension。
