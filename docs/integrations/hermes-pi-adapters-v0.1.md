# Hermes 与 Pi Adapter 设计 v0.1

> 状态：设计基线  
> 日期：2026-07-22  
> 依赖：`agent-context-access-protocol-v0.1.md`

## 1. 目标

本设计说明 Hermes Agent 与 Pi 如何使用相同的 ME-System 上下文语义，同时保持各自原生扩展方式。

- Hermes：优先使用 MCP；
- Pi：优先使用 TypeScript Extension + Skill，自动化场景可使用 Pi SDK；
- 两者均不直接读取 ME-System 数据库；
- 两者共享工具语义、请求响应 Schema、证据句柄和候选回写规则。

## 2. 为什么不采用同一种外壳

Hermes 已原生支持本地 stdio 和远程 HTTP MCP Server，并能够自动发现工具和按服务器过滤工具。Pi 的核心扩展面是 TypeScript Extension、Skill、Prompt Template、Context File 和 SDK，Extension 可以注册模型可调用工具并监听 Agent 生命周期。

因此最佳方案不是强行要求 Pi 和 Hermes 使用同一种运行时，而是：

```text
                Agent Context Access Protocol
                     /                  \
              Hermes MCP             Pi Extension
                  │                       │
              Hermes Agent              Pi Agent
```

## 3. Hermes Adapter

### 3.1 组件

```text
integrations/hermes/
├── README.md
├── mcp-config.example.yaml
├── bootstrap/
│   └── ME_SYSTEM_BOOTSTRAP.md
├── tool-policy.yaml
└── tests/
    └── contract-cases.yaml
```

ME-System MCP Server 本身建议位于：

```text
services/agent-context-gateway/
```

Hermes 目录只保存配置、Bootstrap 和 Hermes 特有测试。

### 3.2 MCP 传输

本地单机优先：

```yaml
mcp_servers:
  me_system:
    command: uv
    args:
      - run
      - me-system-context-server
    timeout: 120
    connect_timeout: 30
    supports_parallel_tool_calls: true
```

NAS、服务器或多设备部署优先远程 HTTP：

```yaml
mcp_servers:
  me_system:
    url: http://me-system:8080/mcp
    timeout: 120
    connect_timeout: 30
    headers:
      Authorization: Bearer ${ME_SYSTEM_HERMES_TOKEN}
```

真实凭据不得写入仓库。

### 3.3 工具白名单

Hermes 第一版只暴露：

```text
me_resolve_scope
me_compile_context
me_get_project_state
me_get_document_outline
me_search_content
me_get_evidence
me_create_handoff_pack
me_explain_context
me_submit_candidate_update
```

不向 Hermes 暴露：

- 直接数据库查询；
- 原始文件任意路径读取；
- 权限管理；
- 候选自动确认；
- Canonical Data 直接修改；
- 完整 ME-Who 导出。

### 3.4 Bootstrap Context File

Hermes 支持 `.hermes.md`、`AGENTS.md` 等项目上下文文件。ME-System 只建议注入简短规则：

```markdown
# ME-System Usage

- 涉及已有项目、历史决策或用户长期协作规则时，先调用 ME-System。
- 默认使用 `me_compile_context`，不要先遍历全部文件。
- 需要引用、修改或核验时，再调用 `me_get_evidence`。
- Context Pack 中的 candidate 与 inference 不是已确认事实。
- 新信息通过 `me_submit_candidate_update` 提交，不得声称已经写入权威数据。
- 向执行 Agent 派发任务时优先创建 Handoff Pack。
```

Bootstrap 不包含项目完整内容，不超过必要长度，避免与动态 Context Pack 重复。

### 3.5 Hermes 典型流程

```text
用户：继续推进 lighting-platform
    ↓
Hermes 调用 me_resolve_scope
    ↓
Hermes 调用 me_compile_context
    ↓
获得项目状态 + 用户协作规则
    ↓
Hermes 决定自己处理或派发
    ↓
如派发，调用 me_create_handoff_pack
    ↓
执行完成后提交 candidate update
```

### 3.6 Hermes 权限

Hermes 默认角色：

```yaml
role: trusted_personal_agent
allowed_scopes:
  - me_brain:read
  - me_who:task_relevant
  - evidence:read
  - handoff:create
  - candidate:write
```

即使是 Hermes，ME-Who 仍要按任务相关性和敏感级别过滤。

## 4. Pi Adapter

### 4.1 组件

```text
integrations/pi/
├── package.json
├── src/
│   ├── extension.ts
│   ├── client.ts
│   ├── tools/
│   │   ├── compile-context.ts
│   │   ├── get-handoff.ts
│   │   ├── get-evidence.ts
│   │   └── submit-candidate.ts
│   └── audit.ts
├── skills/
│   └── me-system-context/
│       └── SKILL.md
├── prompts/
│   └── resume-project.md
└── tests/
    ├── contract.test.ts
    └── permission.test.ts
```

### 4.2 Extension 工具

Pi 第一版不需要暴露 Hermes 的全部工具，只提供执行场景需要的最小集合：

```text
me_get_handoff_pack
me_compile_project_context
me_get_document_outline
me_search_content
me_get_evidence
me_submit_candidate_update
me_explain_context
```

其中 `me_compile_project_context` 是对统一 `me_compile_context` 的受限封装：

- 自动注入 `role=project_agent`；
- 默认 `include_personal_context=false`；
- 只允许当前工作目录映射的项目；
- ME-Who 协作规则只能来自 Handoff Pack 或显式授权。

### 4.3 Pi Skill

Skill 只提供渐进式使用说明，不塞入具体项目资料：

```markdown
---
name: me-system-context
description: Use ME-System to resume a known project, retrieve confirmed decisions, inspect standardized documents, or submit evidence-backed candidate updates.
---

# Rules

1. Prefer a provided Handoff Pack.
2. Otherwise compile project context before broad file exploration.
3. Treat canonical and confirmed items as constraints.
4. Treat candidate and inference items as unconfirmed.
5. Retrieve evidence before changing decisions or citing source material.
6. Submit discoveries as candidates; never claim canonical data was changed.
```

Pi 的 Skill 采用渐进式加载：描述可常驻，完整说明按任务加载。

### 4.4 Context File

Pi Context File 只保存仓库本地稳定规则，例如：

```markdown
# Project Context Bootstrap

This repository is registered in ME-System as `project_lighting`.
Use the ME-System extension for current decisions, constraints, document evidence, and handoff packs.
Do not treat this file as the current project state.
```

项目状态不写死在 Context File 中。

### 4.5 Pi SDK 模式

当需要将 Pi 作为 Hermes 调度的自动化执行器时，可使用 Pi SDK：

```text
Hermes
  ↓ create handoff
ME-System
  ↓ handoff_id
Pi Runner
  ↓ createAgentSession
Pi Session + ME-System Extension
  ↓ execute
Candidate Result
```

SDK Runner 负责：

- 创建隔离 Session；
- 注入 AgentPrincipal 和 Handoff ID；
- 加载 ME-System Extension 与 Skill；
- 订阅工具和消息事件；
- 将最终结果与候选更新关联到同一 `task_id`；
- 不把 Hermes 的完整 Session 复制给 Pi。

### 4.6 Pi 权限

Pi 默认角色：

```yaml
role: project_agent
allowed_scopes:
  - me_brain:assigned_project_read
  - evidence:assigned_scope_read
  - handoff:assigned_read
  - candidate:write
```

默认禁止：

```text
me_who:full_read
me_who:history_read
permissions:modify
candidate:confirm
canonical:write
```

## 5. Hermes → Pi 交接

推荐流程：

```text
1. Hermes 理解用户目标
2. Hermes 获取 ME-Brain + 相关 ME-Who
3. Hermes 确定任务范围和确认边界
4. Hermes 创建 ExecutionHandoffPack
5. Pi 只领取 Handoff Pack
6. Pi 按需读取项目证据
7. Pi 执行并提交候选结果
8. Hermes 审核结果并向用户交付
9. 经确认后更新 ME-Brain 或 ME-Who
```

这样可以避免：

- Pi 重新理解用户全部历史；
- Hermes 和 Pi 使用不同项目事实；
- 大量对话原文重复进入 Token；
- 执行 Agent 意外获得无关私人信息。

## 6. 工具命名映射

| 统一语义 | Hermes MCP 工具 | Pi Extension 工具 |
|---|---|---|
| 解析范围 | `mcp_me_system_me_resolve_scope` | 内部自动解析或 `me_resolve_scope` |
| 编译上下文 | `mcp_me_system_me_compile_context` | `me_compile_project_context` |
| 读取项目状态 | `mcp_me_system_me_get_project_state` | `me_compile_project_context` |
| 文档大纲 | `mcp_me_system_me_get_document_outline` | `me_get_document_outline` |
| 内容检索 | `mcp_me_system_me_search_content` | `me_search_content` |
| 证据下钻 | `mcp_me_system_me_get_evidence` | `me_get_evidence` |
| 创建交接 | `mcp_me_system_me_create_handoff_pack` | 不开放 |
| 领取交接 | Hermes 通常不需要 | `me_get_handoff_pack` |
| 候选回写 | `mcp_me_system_me_submit_candidate_update` | `me_submit_candidate_update` |

模型可见的工具说明应保持一致术语，不依赖传输前缀。

## 7. 缓存策略

### Hermes

- Context Pack 缓存到 `expires_at`；
- 用户明确改变项目事实后立即失效；
- 同一 Session 可复用未过期 Pack；
- 关键写入前重新检查相关决策和约束。

### Pi

- Handoff Pack 在任务期间固定；
- 证据节点可按版本缓存；
- 不缓存 ME-Who；
- 超出任务范围时请求 Hermes 重新交接，而不是自行扩大权限。

## 8. 失败与降级

### Hermes Adapter 失败

- 明确告诉 Hermes ME-System 不可用；
- Hermes 可基于用户当前提供材料继续；
- 不得声称已经恢复历史项目状态。

### Pi Adapter 失败

- 如果 Handoff Pack 已随任务保存，可继续执行明确范围；
- 如果缺少关键证据，停止相关修改并返回阻塞项；
- 不允许通过全盘扫描私人目录替代 ME-System 授权访问。

## 9. 评测场景

### 场景 A：项目恢复

- Hermes 从一句“继续推进”解析项目并获取当前状态；
- 检查是否避免重复询问和过期方案。

### 场景 B：Hermes 派发 Pi

- Hermes 创建 Handoff Pack；
- Pi 获取约束、交付物和证据；
- 检查 Pi 是否越权读取 ME-Who。

### 场景 C：证据核验

- Hermes 和 Pi 分别从同一 Context Item 下钻；
- 必须定位到相同 `document_id/version_id/node_id`。

### 场景 D：候选回写

- Pi 提交 proposed decision；
- ME-Brain 正式决策不应立即改变；
- Hermes 能看到待审核候选。

### 场景 E：Token 对比

比较：

1. Hermes/Pi 全量探索文件；
2. 仅 Context File；
3. ME-System Context Pack + Evidence Drill-down。

记录 Token、工具调用、当前状态准确率、越权率和来源覆盖率。

## 10. v0.1 验收条件

- Hermes 通过 MCP 获取 Context Pack；
- Pi 通过 Extension 获取语义一致的项目 Context Pack；
- Hermes 可创建、Pi 可领取 Handoff Pack；
- Context File 和 Skill 只承载 Bootstrap，不承载动态知识；
- Pi 默认不能读取完整 ME-Who；
- 两侧都能通过相同证据句柄定位原文；
- 两侧提交结果都进入候选区；
- Adapter 失败时不伪造历史上下文。