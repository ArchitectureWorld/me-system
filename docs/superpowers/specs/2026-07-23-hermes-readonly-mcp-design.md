# Hermes Read-only MCP Design

> 状态：已批准路线下的实现设计  
> 日期：2026-07-23  
> 范围：Project ID Resolve、只读 Graph Query 工具、Hermes stdio MCP 接入

## 1. 目标

让 Hermes 从简短任务表达中确定项目，并通过只读 MCP 工具读取 ME-Brain 与任务相关 ME-Who 图谱，而不是重新扫描全部文件。

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
- `tools.include` 白名单过滤。

本切片优先 stdio，因为数据库和 MCP Server 通常部署在 Hermes 同一台 Linux / NAS 主机，且不需要额外网络暴露。

MCP Python SDK 使用 v1 稳定线：

```text
mcp>=1.27,<2
```

显式 `<2` 是为了避免 MCP Python SDK v2 发布后发生非受控主版本升级。

## 3. 非目标

本切片不实现：

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
- 项目权限由服务端配置注入，不接受模型自行声明；
- stdio 的 stdout 只用于 MCP 协议，诊断日志写 stderr。

## 5. Project Resolver

### 5.1 Project 属性

ME-Brain `Project.properties` v0.1 可包含：

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

这些字段是项目节点属性，不是新的节点类型。

### 5.2 输入

```yaml
query: lighting-platform
working_directory: /workspace/lighting-platform
external_system: github
external_id: ArchitectureWorld/lighting-platform
```

至少提供一个输入。

### 5.3 匹配优先级

```text
1. canonical_id
2. external_id
3. workspace_path
4. label
5. alias
```

所有匹配均为确定性精确匹配：

- 文本执行 Unicode NFKC、trim、casefold；
- 工作目录执行本机绝对路径规范化；
- 不使用向量、编辑距离或 LLM 判断。

### 5.4 输出

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

同一优先级出现多个候选时返回 `ambiguous`，不擅自选择。

## 6. 服务端配置

环境变量：

```text
ME_GRAPH_DATABASE_URL               必填
ME_GRAPH_HERMES_USER_ID             必填，固定 ME-Who 用户
ME_GRAPH_ALLOWED_PROJECT_IDS        必填，逗号分隔或 *
ME_GRAPH_MAX_SUBGRAPH_DEPTH         可选，默认 2，最大 3
ME_GRAPH_MCP_LOG_LEVEL              可选，默认 WARNING
```

默认拒绝原则：

- 未配置 `ME_GRAPH_ALLOWED_PROJECT_IDS` 时拒绝启动；
- `*` 仅适用于用户明确选择允许全部项目的本地个人实例；
- `who_get_task_profile` 使用服务端固定的用户 ID，工具参数中不暴露 `user_id`。

## 7. 项目范围保护

### 7.1 直接项目工具

`brain_get_snapshot(project_id)` 与 `brain_resolve_project()` 只返回允许项目。

### 7.2 对象工具

以下工具必须同时传入 `project_id`：

```text
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
```

服务端执行：

1. 检查 `project_id` 在 allowlist；
2. 从项目根展开受限成员子图；
3. 检查目标对象属于该项目；
4. 再执行具体查询。

v0.1 成员范围使用最多 3 层的项目子图。跨项目共享对象在没有显式项目关系前不自动授权。

## 8. MCP 工具

第一版固定六个工具。

### 8.1 `brain_resolve_project`

输入：项目名称、工作目录或外部 ID。  
输出：确定性项目解析结果。

### 8.2 `brain_get_snapshot`

输入：`project_id`。  
输出：当前 ME-Brain `GraphSlice`，过期决策进入 `excluded.superseded`。

### 8.3 `brain_expand_subgraph`

输入：

```yaml
project_id:
node_id:
depth: 1
edge_types: []
```

约束：`0 <= depth <= configured_max_depth`。

### 8.4 `brain_trace_decision`

输入：`project_id`、`decision_id`。  
输出：当前与历史 `SUPERSEDES` 链。

### 8.5 `brain_get_evidence`

输入：`project_id`、`object_id`。  
输出：`EvidenceRef[]`，不读取原始文件正文。

### 8.6 `who_get_task_profile`

输入：`project_id`、`task_type`。  
输出：配置用户在当前项目和任务类型下相关的 ME-Who 子图。

## 9. 工具返回和错误

工具返回 JSON 结构，不返回 Markdown 拼接文本。

业务错误采用统一结果：

```yaml
ok: false
error:
  code: PROJECT_NOT_ALLOWED
  message: requested project is outside the configured Hermes scope
  retryable: false
```

成功结果：

```yaml
ok: true
result: ...
```

错误不得包含：

- 数据库密码；
- 完整连接字符串；
- Python traceback；
- 未授权项目名称列表。

## 10. MCP Server 实现

新增模块：

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

FastMCP 配置：

```python
FastMCP(
    name="ME-System Graph",
    instructions="Read-only ME-Brain and task-scoped ME-Who graph tools.",
    json_response=True,
)
```

直接执行：

```python
mcp.run(transport="stdio")
```

## 11. Hermes 配置

示例：

```yaml
mcp_servers:
  me_system:
    command: "me-graph-mcp"
    env:
      ME_GRAPH_DATABASE_URL: "${ME_GRAPH_DATABASE_URL}"
      ME_GRAPH_HERMES_USER_ID: "who:user:master"
      ME_GRAPH_ALLOWED_PROJECT_IDS: "brain:project:lighting-platform"
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

Bootstrap 规则保持很短：

```text
涉及既有项目状态、历史决策、项目证据或长期协作规则时，先使用 ME-System MCP。
先 resolve，再读取 snapshot；只有核验或深入分析时才 expand / evidence。
```

动态项目状态不写进 `.hermes.md` 或 `AGENTS.md`。

## 12. 测试

### 12.1 Resolver

覆盖：

- canonical ID；
- label；
- alias；
- workspace path；
- external ID；
- 优先级；
- ambiguous；
- not found；
- allowlist 过滤。

### 12.2 Access Guard

覆盖：

- 允许项目；
- 拒绝项目；
- 节点属于项目；
- 历史决策仍属于项目；
- Bridge 或其他项目对象不能越权；
- depth 上限。

### 12.3 Tool Service

覆盖全部六个工具、统一错误结构、固定用户 ID 与凭据脱敏。

### 12.4 MCP 协议

在 CI 中使用官方 MCP `ClientSession` 和 stdio transport：

1. 启动 `me-graph-mcp`；
2. initialize；
3. list_tools；
4. 验证只有六个工具；
5. 调用 resolve；
6. 调用 snapshot；
7. 验证结构化结果；
8. 关闭会话。

### 12.5 PostgreSQL E2E

CI 使用 PostgreSQL 16：

- 迁移；
- 导入 fixture；
- 启动 MCP；
- Hermes 等价 stdio 客户端调用；
- 验证 Radiance 当前、Cycles 被排除、实现任务返回 direct-execution。

## 13. 验收标准

- 项目可以通过 canonical ID、label、alias、工作目录和外部 ID 解析；
- 解析不使用 LLM 和模糊猜测；
- Hermes 看到且只能看到六个只读工具；
- 非允许项目无法查询；
- 工具参数不能切换 ME-Who 用户；
- PostgreSQL 重启后 MCP 查询结果一致；
- “继续推进 lighting-platform”流程无需扫描全部项目文件；
- Python 3.11 / 3.12 + PostgreSQL 16 CI 通过；
- MCP SDK 固定在 `<2`。

## 14. 后续

本切片通过后：

1. 在真实 Hermes 中进行项目恢复 Benchmark；
2. Agent Conversation Adapter 产生 CandidateGraphChange；
3. pending Candidate 持久化与审核；
4. 证据正文读取与字段级权限；
5. Streamable HTTP；
6. Pi Extension。
