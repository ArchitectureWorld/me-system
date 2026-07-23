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

### 已完成：PostgreSQL GraphStore

- SQLAlchemy 2.0 持久化实现；
- PostgreSQL + psycopg 3；
- 全局节点/边 ID；
- 有序 EvidenceRef；
- 原子写入和事务回滚；
- ME-Brain、ME-Who 与 Bridge 约束；
- Alembic 迁移；
- 数据库 CLI；
- 内存 Store 与持久化 Store 查询一致性；
- Python 3.11 / 3.12 + PostgreSQL CI。

### 已完成：Project Resolve 与 Hermes 只读 MCP

- canonical ID、label、alias、workspace path 和 external ID 精确解析；
- 不使用 LLM 或模糊匹配猜项目；
- 服务端 project allowlist；
- 服务端固定 ME-Who 用户；
- 显式项目所有权范围；
- 跨项目语义边不扩大权限；
- 历史决策受其他项目所有权约束；
- 六工具 stdio MCP；
- Hermes 工具白名单和 Bootstrap；
- MCP Python SDK 固定 `<2`；
- Python 3.11 / 3.12 单元测试；
- PostgreSQL 16 + 真实 stdio ClientSession E2E。

### Phase 1 剩余工作：真实 Hermes Benchmark

1. 在实际 Hermes 安装中加载 `me_system` MCP；
2. 固定项目问题集；
3. 对比：

```text
A. Hermes 直接探索项目文件
B. Hermes + ME-Brain GraphSlice
C. Hermes + ME-Brain + ME-Who Task Profile
```

4. 记录：

- 输入 Token；
- MCP / 文件工具调用次数；
- 首次项目恢复延迟；
- 当前事实准确率；
- 过期方案误用率；
- 来源覆盖率；
- 重复询问次数；
- 用户纠正次数。

### Phase 1 验收

- 当前决策不混入过期方案；
- 阻塞任务和问题可查询；
- 决策可以返回证据；
- 数据跨进程和重启保持；
- Hermes 不直接扫描全部文件；
- Hermes 不直接连接数据库；
- 非允许项目和跨项目对象不能越权返回；
- GraphSlice 相比全文件探索在真实任务中有可测收益。

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

同时补充：

- pending Candidate 持久化；
- 审核日志；
- 批量导入事务；
- 失败重试和幂等键；
- Agent 字段级权限过滤；
- 证据正文读取和脱敏。

## Phase 3：最小 ME-Who 深化

当前已有：

- 用户角色；
- 专业能力；
- 项目参与关系；
- 明确协作规则；
- 任务类型过滤。

后续增加：

- 用户确认偏好；
- 规则有效期与替代；
- 候选行为证据；
- 用户确认和禁止使用；
- 敏感度与字段级授权。

验证重复询问和协作错误是否下降。

## Phase 4：候选审核与治理

实现：

- 候选节点和边列表；
- 证据预览；
- 批准、驳回和修改；
- 版本和替代；
- 审计日志；
- ME-Who 敏感信息治理；
- Agent 字段级权限过滤。

第一版可以是简单 Web 或 Obsidian 投影，不建设大型图谱画布。

## Phase 5：Pi 与执行 Agent

在 Hermes Benchmark 和 Candidate 闭环稳定后实现 Pi Extension：

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

## 数据库演进原则

当前权威存储固定为 PostgreSQL。只有当真实多跳查询、图算法或规模指标证明关系表不足时，才评估 PostgreSQL 图扩展或独立图数据库。

任何新存储方案必须继续实现同一个 `GraphStore`，并通过与 PostgreSQL 相同的行为契约和 GraphSlice 对照测试。

## 暂停开发

在真实 Hermes Benchmark 和输入候选闭环通过前，不优先投入：

- 完整多 Agent Handoff 平台；
- 全格式万能文档标准；
- 独立 ME-Reader 产品；
- 数字人格；
- 大型图谱前端；
- 全自动知识确认；
- 多数据库并行架构。
