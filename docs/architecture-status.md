# ME-System 当前架构状态

> 更新日期：2026-07-23

本文件用于区分当前有效规范、历史研究材料和后续实现方向。

## 当前有效的最高层决策

1. `docs/adr/ADR-0004-two-canonical-graphs.md`
   - ME-Brain Graph 与 ME-Who Graph 是两个产品核心。
   - 文档标准化属于输入与证据层。
   - MCP、REST、SDK 属于 Agent 访问层。
   - Context Pack 是 GraphSlice 的运行时投影。

2. `docs/adr/ADR-0003-agent-context-access-layer.md`
   - 仅规定 Agent 不直连数据库，以及 Hermes/Pi 的访问边界。
   - 受 ADR-0004 约束，不得反向定义图谱模型。

## 当前有效的实现契约

- `docs/specs/dual-graph-contract-v0.1.md`
- `docs/specs/me-brain-ontology-v0.1.md`
- `docs/specs/me-who-ontology-v0.1.md`
- `services/me-graph-core/schemas/`

## 当前可运行基线

- `services/me-graph-core/`
- `examples/graph/lighting-platform.json`

## 输入与证据层材料

`docs/specs/document-information-standardization-v0.1.md` 保留为广义输入格式研究材料，但它不是当前 P0 的完整实现清单。P0 仅优先实现：

- SourceRecord
- Document
- DocumentVersion
- ContentFragment
- EvidenceAnchor
- ParserRun / QualityIssue

其余复杂格式、资产重建和全格式解析在真实需求出现后逐项扩展。

## 已废止的方向

以下内容不再作为有效架构：

- ME-Context 作为第三个产品；
- ME-Reader 作为第三条产品线；
- 独立 Agent Context Gateway 作为系统核心；
- 在权威图谱之前优先建设完整 Handoff、复杂 Token 编译和多 Agent 编排协议；
- Agent 直接查询数据库或生成任意 Cypher。

历史研究内容可通过 Git 历史和已关闭 PR 查看，不继续保留为主分支活动规格。
