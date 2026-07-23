# Graphify 深度评审与 ME-System 吸收建议

> 评审日期：2026-07-23  
> 官方产品：<https://graphify.com/>  
> 官方仓库：<https://github.com/Graphify-Labs/graphify>  
> 参考架构：<https://github.com/Graphify-Labs/graphify/blob/v8/ARCHITECTURE.md>

## 1. 总体判断

Graphify 与 Codebase-Memory 都验证了同一条关键路线：

```text
原始资料
→ 预先建立持久化结构图
→ Agent 查询图，而不是每次 grep / 全文件扫描
→ 查询结果返回明确路径与证据
```

Graphify 的突出价值不是某一种数据库，而是完整的产品闭环：

```text
detect
→ extract
→ validate
→ build graph
→ cluster
→ analyze
→ report / export
→ CLI / MCP query
→ incremental update
```

它把抽取、图谱、报告、Agent 安装和 MCP 服务连成了一个低门槛工作流。ME-System 应吸收这种“单包、单命令、图谱优先、证据可审计”的产品纪律。

Graphify 仍主要面向代码和多模态项目资料；ME-System 的差异在于：

- ME-Brain 需要权威项目事实、时间演化和人工确认；
- ME-Who 需要隐私、适用范围和身份解释权；
- 两个图谱不能被压成一个无权限边界的平面图；
- 自动抽取必须先进入 Candidate，不直接成为 canonical graph。

## 2. 最值得吸收的能力

### 2.1 单一、清晰的索引流水线

Graphify 的架构将每个阶段限定为单一职责，并通过普通数据结构传递结果：

```text
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

ME-System 对应采用：

```text
detect source
→ normalize source
→ extract evidence
→ validate extraction
→ propose graph changes
→ review
→ persist canonical graph
→ analyze
→ serve over MCP
```

**落点：** `src/me_system/ingestion/`。每个 Adapter 不拥有自己的数据库，不直接调用 MCP，不直接写权威图谱。

### 2.2 每一条关系说明“系统为什么相信它”

Graphify 将边标记为：

```text
EXTRACTED
INFERRED
AMBIGUOUS
```

这比只有一个浮点 `confidence` 更容易让用户和 Agent 理解。

ME-System 应增加 `DerivationKind`：

```text
EXPLICIT          原文明确表达或确定性解析
RULE_DERIVED      由可审计规则推导
MODEL_INFERRED    由模型推断
AMBIGUOUS         存在多个合理解释
HUMAN_ASSERTED    人工直接建立
```

同时继续保留：

- `authority`；
- `confirmation_status`；
- `confidence`；
- `source_refs`。

这几个维度不能合并：

- derivation 表示怎么得到；
- authority 表示是否属于权威层；
- confirmation 表示谁确认过；
- confidence 表示不确定程度。

**落点：** 后续 `GraphEdge` / Candidate Schema 迁移，不混入本次包重命名。

### 2.3 路径式回答，而不是摘要式回答

Graphify 的 `query`、`path`、`explain` 强调：答案由一条可审计路径组成。

ME-System 应在现有领域工具之外增加通用只读查询：

```text
get_node
get_neighbors
shortest_path
explain_path
```

领域工具继续保留：

```text
brain_get_snapshot
brain_trace_decision
brain_analyze_impact
who_get_task_profile
```

推荐关系：

- 领域工具负责高频、受控、低 Token 查询；
- 通用图工具负责探索和诊断；
- 不向 Agent 暴露任意 SQL 或写入型 Cypher。

### 2.4 图谱报告作为人类入口

Graphify 同时输出：

```text
graph.json
GRAPH_REPORT.md
graph.html
```

ME-System 可以输出可再生投影：

```text
me-system-out/
├── brain-report.md
├── who-report.md              # 默认不提交 Git
├── graph-manifest.json
├── brain-snapshot.json
└── graph.html                 # 后置
```

报告可包含：

- 关键项目节点；
- 当前阻塞关系；
- 决策演化；
- 高连接节点；
- 跨模块意外联系；
- 不确定和待审核关系；
- 推荐查询问题。

**原则：** 这些是投影和诊断产物，不是权威数据源。

### 2.5 增量更新和变更监听

Graphify 支持：

- `--update` 只处理变化内容；
- watch；
- Git hook 后自动刷新；
- manifest 使用相对路径，便于团队共享。

ME-System 应吸收：

```text
content hash
+ adapter version
+ extraction rule/model version
+ source manifest
→ 幂等增量摄取
```

后续支持：

```text
me-system index --update
me-system watch
me-system hook install
```

但 hook 默认应为非阻塞，只提示图谱过期或排队摄取，不能阻断正常 Git 操作。

### 2.6 query-first Agent 引导

Graphify 会为不同 Agent 安装 Skill、Instruction 或非阻塞 Hook，提醒 Agent 先查图再扫描文件。

ME-System 应为 Hermes、Pi、Codex 生成很短的规则：

```text
涉及既有项目状态、历史决策和协作规则时：
1. resolve project
2. get snapshot / task profile
3. 必要时 expand / path / evidence
4. 最后才读取原始文件
```

不得把动态项目内容复制进 `AGENTS.md` 或 `.hermes.md`；这些文件只保存查询策略。

### 2.7 社区检测与高影响节点

Graphify 提供 communities、god nodes 和 surprising connections。

ME-System 可对应实现：

#### ME-Brain

- 高影响 Decision / Constraint；
- 多任务依赖的 Artifact；
- 高频阻塞 Issue；
- 项目工作流社区；
- 跨项目共享组件。

#### ME-Who

- 高频生效的 CollaborationRule；
- 跨项目稳定能力；
- 互相冲突的偏好；
- 适用范围异常宽的规则。

ME-Who 的中心性分析必须经过隐私过滤，且不能把“连接数多”直接解释成人格重要性。

### 2.8 Benchmark 作为产品功能

Graphify 不只描述 Token 收益，还建立可重复 Benchmark。

ME-System 必须建立三组基线：

```text
A. Agent 全文件探索
B. 普通全文 / 向量检索
C. ME-System Graph Query
```

指标：

- 输入 Token；
- 工具调用数；
- 首次正确率；
- 当前事实与历史事实混淆率；
- 证据覆盖率；
- 查询延迟；
- 图谱摄取成本。

第一组数据继续使用 `lighting-platform`。

## 3. 不应照搬的部分

### 3.1 不把一个 `graph.json` 当权威数据库

Graphify 的文件快照适合代码结构图；ME-System 需要：

- 时间有效性；
- 权限；
- Candidate 审核；
- 事务；
- ME-Who 隐私；
- 跨进程一致性。

因此 PostgreSQL 继续是权威存储，JSON 只作为导出和缓存。

### 3.2 不合并 ME-Brain 和 ME-Who 为单一平面图

两者可以通过 Bridge 关联，但必须保持：

- 独立命名空间；
- 独立领域 Schema；
- 独立读取权限；
- 独立审核策略。

### 3.3 不允许语义抽取直接成为权威边

Graphify 的 INFERRED edge 可以直接存在于分析图中；ME-System 中：

```text
MODEL_INFERRED / AMBIGUOUS
→ Candidate
→ 审核
→ Canonical
```

### 3.4 不默认把 ME-Who 导出提交到 Git

ME-Brain 的部分项目投影可以团队共享；ME-Who 默认：

- 本地私有；
- 不提交；
- 不生成公开 HTML；
- 不向项目执行 Agent 全量开放。

### 3.5 不在第一阶段开放任意图查询语言

Codebase-Memory 提供只读 Cypher 子集，Graphify提供通用图工具。ME-System 第一阶段优先类型化工具，待权限模型和查询成本保护稳定后，再评估受限只读查询 DSL。

## 4. 推荐吸收优先级

| 能力 | 优先级 | ME-System 落点 |
|---|---:|---|
| 单包索引流水线 | A+ | 本次目录与包收敛 |
| 边的 derivation 标签 | A+ | Graph Schema v0.2 |
| query-first Agent 规则 | A+ | Hermes 已有，扩展到 Pi/Codex |
| 增量 manifest / hash | A+ | Source / Ingestion |
| 路径与 explain 查询 | A | MCP 第二批工具 |
| Graph report | A | 人工审阅与项目恢复 |
| Benchmark harness | A | `benchmarks/` |
| community / centrality | B | ME-Brain 影响分析 |
| HTML 图谱浏览 | B | 治理界面前的轻量投影 |
| watch / Git hook | B | Adapter 稳定后 |
| PR 影响分析 | B | Software Domain Pack |
| 任意只读查询 DSL | C | 权限稳定后评估 |
| 将完整图提交 Git | 不采用 | 尤其禁止 ME-Who |

## 5. 对当前路线的直接修改

当前开发顺序调整为：

```text
1. 统一为一个 me_system 包
2. Source / Evidence / Candidate 持久化
3. 增量 manifest 与 adapter versioning
4. Agent Conversation Adapter
5. 路径式 MCP 查询
6. Graph Report 与 Benchmark
7. Markdown / Git / Zotero Adapter
8. 社区和影响分析
```

## 6. 最终结论

Graphify 与 Codebase-Memory 证明了：

> Agent 的长期结构理解应建立在可持久、可遍历、可审计的图谱上，而不是每个会话重新扫描资料。

ME-System 应吸收其工程方法，但保持自己的关键差异：

```text
一个 ME-System
├── ME-Brain 权威图谱
└── ME-Who 权威图谱

共享：索引、证据、审核、持久化、查询和 MCP
隔离：领域事实、权限和隐私
```