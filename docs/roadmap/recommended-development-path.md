# ME-System 推荐开发路径

> 更新：2026-07-23

## Phase 0：架构与契约收敛

已完成首批内容：

- 双图谱产品定义；
- GraphNode / GraphEdge / EvidenceRef；
- CandidateGraphChange；
- GraphSlice；
- InMemoryGraphStore；
- 候选审核；
- lighting-platform 示例图；
- 当前项目快照、决策追踪、证据查询和任务画像查询。

## Phase 1：ME-Brain 只读真实闭环

目标：Hermes 能从一句“继续推进 lighting-platform”恢复项目。

任务：

1. 将人工示例图迁移到 PostgreSQL GraphStore；
2. 实现项目解析与 ID Resolve；
3. 暴露只读 Graph Query API；
4. 实现 Hermes MCP Server；
5. 对比全文件探索与 GraphSlice 的 Token、延迟和准确度。

验收：

- 当前决策不混入过期方案；
- 阻塞任务和问题可查询；
- 决策可以返回证据；
- Hermes 不直接扫描全部文件。

## Phase 2：输入和候选图谱

按顺序接入：

```text
Agent Conversation Adapter
Markdown Adapter
Git Adapter
Zotero Adapter
DOCX / PDF Adapter
```

每个 Adapter 只产生：

```text
Source / Evidence
+
CandidateGraphChange
```

不直接写入权威图谱。

## Phase 3：最小 ME-Who

先实现：

- 用户角色；
- 专业能力；
- 项目参与关系；
- 明确协作规则；
- 用户确认偏好。

Hermes 查询：

```text
ME-Brain Project Snapshot
+
ME-Who Task Profile
```

验证重复询问和协作错误是否下降。

## Phase 4：候选审核与治理

实现：

- 候选节点和边列表；
- 证据预览；
- 批准、驳回和修改；
- 版本和替代；
- 审计日志；
- ME-Who 敏感信息治理。

第一版可以是简单 Web 或 Obsidian 投影，不建设大型图谱画布。

## Phase 5：Pi 与执行 Agent

在 Hermes 只读闭环稳定后实现 Pi Extension：

- 当前项目 GraphSlice；
- 任务相关 ME-Who 规则；
- 证据下钻；
- 候选结果提交。

Pi 默认不读取完整 ME-Who。

## Phase 6：领域包

### Software

```text
Repository / Module / Component / Interface / Commit / PR / Test
```

### Research

```text
Paper / Claim / Evidence / Method / Dataset / Experiment / Finding
```

Zotero 与 Obsidian 代码归入本领域。

### Design

```text
Brief / Option / DesignDecision / Drawing / Model / Review / Revision
```

## 暂停开发

在 Phase 1 通过前，不优先投入：

- 完整多 Agent Handoff 平台；
- 全格式万能文档标准；
- 独立 ME-Reader 产品；
- 数字人格；
- 大型图谱前端；
- 全自动知识确认；
- 多数据库并行架构。
