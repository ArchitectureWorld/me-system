# ADR-0003：通过统一 Agent Context Access Layer 对接 Hermes、Pi 与其他 Agent

- 状态：Accepted
- 日期：2026-07-22
- 决策范围：标准化文档、ME-Brain、ME-Who 与 Agent 的运行时连接方式

## 背景

文档信息标准化解决的是“信息如何被可靠保存、定位和派生”，但不能自动解决“Agent 如何使用这些信息”。

若 Hermes、Pi、Codex 或其他 Agent 分别直接读取数据库、Markdown 投影或标准文档包，将产生：

- 每个 Agent 自行决定检索、排序和 Token 装载方式；
- 同一任务在不同 Agent 中得到不一致上下文；
- Agent 与数据库 Schema、解析器和文件布局耦合；
- ME-Who 的敏感信息难以按 Agent 隔离；
- 无法统一记录上下文使用情况、证据下钻和候选回写；
- 更换 Agent 框架时需要重新实现整套知识访问逻辑。

Hermes 原生支持通过 MCP 连接本地或远程工具服务器，并支持按服务器过滤工具。Pi 的核心设计则强调通过 TypeScript Extension、Skill、Prompt Template、Context File 和 SDK 扩展工作流。因此，二者应共享语义协议，但使用不同的接入外壳。

## 决策

ME-System 增加独立的 **Agent Context Access Layer**。

```text
Canonical Document Package
        +
ME-Brain / ME-Who Canonical Data
        │
        ▼
Agent Context Access Layer
├── Scope & Permission
├── Typed Retrieval
├── Context Compilation
├── Evidence Drill-down
├── Usage Audit
└── Candidate Write-back
        │
        ├── Hermes MCP Adapter
        ├── Pi Extension / SDK Adapter
        └── Future Agent Adapters
```

Agent 不直接读取 ME-System 数据库，不直接依赖解析器输出，也不把 Markdown 投影视为权威数据。

## 核心交互模式

### 1. Bootstrap

向 Agent 提供少量稳定说明：

- ME-System 可提供什么；
- 何时调用上下文工具；
- 哪些内容不得凭推断写入；
- 如何进行证据下钻。

Bootstrap 可以通过 Hermes Context File、Pi Context File 或 Skill 描述注入，但不得承载完整项目知识。

### 2. Context Compile

Agent 提交当前任务、项目、身份、Token 预算和证据要求，ME-System 返回任务相关的 Context Pack。

### 3. Progressive Drill-down

Context Pack 默认返回 L1/L2 结构化信息和证据句柄。Agent 只有在需要核验、修改或引用时，才继续读取文档节点、资产或完整原文。

### 4. Candidate Write-back

Agent 只能提交候选更新，不得直接修改：

- ME-Brain 正式决策、需求和研究结论；
- ME-Who 稳定偏好、能力判断和协作规则；
- Canonical Document Package 的原始解析结果。

候选必须携带证据、提交者、任务和变更理由。

## Hermes 集成决策

Hermes 第一阶段采用 **MCP Adapter**：

- ME-System 作为本地 stdio 或远程 HTTP MCP Server；
- Hermes 只暴露经过白名单筛选的 ME-System 工具；
- `.hermes.md` 或 `AGENTS.md` 只放 Bootstrap 规则；
- 动态项目内容通过 MCP 获取，不写入长期 Context File；
- Hermes 作为 `trusted_personal_agent`，可以在权限允许时组合 ME-Who 与 ME-Brain。

## Pi 集成决策

Pi 第一阶段采用 **TypeScript Extension + Skill**：

- Extension 注册与 Hermes MCP 工具语义一致的 LLM-callable tools；
- Extension 通过 ME-System REST/Local SDK 调用 Agent Context Access Layer；
- Skill 说明何时调用、如何下钻和如何提交候选；
- Context File 只放项目级静态规则；
- 需要嵌入式或自动化运行时，使用 Pi SDK 创建 Session 并注入相同 Adapter；
- Pi 默认作为 `project_agent`，只读取项目上下文或 Hermes 生成的 Execution Handoff Pack，不默认读取完整 ME-Who。

## 统一而不强求同一传输协议

统一的是：

- 工具语义；
- 请求和响应 Schema；
- 权限；
- Token 预算；
- 证据句柄；
- 错误模型；
- 候选回写模型。

不强制统一的是：

- Hermes 使用 MCP；
- Pi 使用 Extension、REST 或 SDK；
- 未来 Agent 可以使用 MCP、REST、SDK 或进程内调用。

## 安全边界

第一版权限建议：

| Agent | 默认身份 | ME-Brain | ME-Who | 候选回写 |
|---|---|---:|---:|---:|
| Hermes | `trusted_personal_agent` | 按项目 | 与任务相关部分 | 是 |
| Pi | `project_agent` | 当前项目/交接包 | 默认拒绝，仅允许显式协作规则 | 是 |
| Codex | `project_agent` | 当前任务/交接包 | 默认拒绝 | 是 |
| 外部 Agent | `external_agent` | 明确授权内容 | 拒绝 | 默认拒绝 |

任何 Adapter 都不得绕过 Agent Context Access Layer 直接扩大权限。

## 后果

### 正面影响

- 文档标准化与 Agent 框架解耦；
- Hermes、Pi 可以共享相同上下文语义；
- Token、权限、证据和回写可以统一审计；
- 执行 Agent 不需要掌握用户完整画像；
- 后续更换 Agent 或增加新 Agent 的成本显著降低。

### 代价

- 需要维护统一请求/响应契约；
- 需要分别实现 Hermes 和 Pi 的薄 Adapter；
- 需要设计工具数量和渐进式调用策略；
- 需要处理超时、部分结果和服务不可用降级。

这些成本属于稳定多 Agent 使用方式的必要投入。