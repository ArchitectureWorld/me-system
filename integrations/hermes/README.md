# Hermes Read-only MCP Integration

Hermes 通过 stdio MCP 读取 ME-System。MCP Adapter 只包装 `GraphQueryService` 和项目范围保护，不直接执行 SQL，也不定义图谱 Schema。

## 前置条件

1. PostgreSQL GraphStore 已迁移并包含项目图谱；
2. `me-graph-core` 已安装；
3. 环境中存在：

```text
ME_GRAPH_DATABASE_URL
ME_GRAPH_HERMES_USER_ID
ME_GRAPH_ALLOWED_PROJECT_IDS
```

## 六个只读工具

```text
brain_resolve_project
brain_get_snapshot
brain_expand_subgraph
brain_trace_decision
brain_get_evidence
who_get_task_profile
```

| MCP 工具 | Core 能力 |
|---|---|
| `brain_resolve_project` | canonical ID、label、alias、工作目录、外部 ID 精确解析 |
| `brain_get_snapshot` | 当前项目 GraphSlice |
| `brain_expand_subgraph` | 有界项目子图 |
| `brain_trace_decision` | `SUPERSEDES` 决策链 |
| `brain_get_evidence` | 稳定 EvidenceRef |
| `who_get_task_profile` | 服务端固定用户的任务相关 ME-Who 子图 |

没有任何写入、审核、SQL 或任意 Cypher 工具。

## Hermes 配置

将 [`config.example.yaml`](config.example.yaml) 中的 `me_system` 部分合并到：

```text
~/.hermes/config.yaml
```

真实数据库 URL 建议通过进程环境提供，不要提交到仓库。

## 使用顺序

```text
1. brain_resolve_project
2. brain_get_snapshot
3. 需要深入时才调用 expand / trace / evidence
4. 需要确定协作方式时调用 who_get_task_profile
```

例如用户说“继续推进 lighting-platform”，Hermes 应先按名称解析项目，再获取当前状态，而不是遍历整个文件夹。

## 权限

- `ME_GRAPH_ALLOWED_PROJECT_IDS` 必填，支持逗号分隔 canonical project ID；
- 只有显式配置 `*` 才允许全部项目；
- `ME_GRAPH_HERMES_USER_ID` 由服务端注入，模型无法通过参数切换用户；
- 对象查询必须同时给出项目 ID，并验证对象属于该项目；
- Bridge 和 ME-Who 节点不能通过 ME-Brain 对象工具读取；
- 默认子图最大深度为 2，绝对上限为 3。

## Bootstrap

[`ME_SYSTEM_BOOTSTRAP.md`](ME_SYSTEM_BOOTSTRAP.md) 只描述何时使用工具。动态项目状态不得复制到 `.hermes.md`、`AGENTS.md` 或长期系统提示中。

## 启动测试

```bash
ME_GRAPH_DATABASE_URL='postgresql+psycopg://...' \
ME_GRAPH_HERMES_USER_ID='who:user:master' \
ME_GRAPH_ALLOWED_PROJECT_IDS='brain:project:lighting-platform' \
me-graph-mcp
```

这是 stdio Server，直接启动后等待 MCP Client，不会显示普通交互式命令行。
