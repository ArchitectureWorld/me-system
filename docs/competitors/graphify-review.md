# Graphify 深度评审与 ME-System 吸收建议

> 评审日期：2026-07-23  
> 官方产品：<https://graphify.com/>  
> 官方仓库：<https://github.com/Graphify-Labs/graphify>  
> 架构说明：<https://github.com/Graphify-Labs/graphify/blob/v8/ARCHITECTURE.md>

## 1. 核心判断

Graphify 与 Codebase-Memory 共同验证了一条适合 ME-System 的路线：

```text
原始资料
→ 预先建立持久化结构图
→ Agent 查询图谱而不是反复扫描全部文件
→ 必要时沿路径下钻到原始证据
```

Graphify 的产品价值不只是“生成一张图”，而是把完整流程连成一个低摩擦工作流：

```text
detect
→ extract
→ build graph
→ cluster
→ analyze
→ report / export
→ CLI / MCP query
→ incremental update
```

ME-System 应吸收这种**一个可安装产品、一个索引流水线、一个查询入口**的纪律，但继续保持自己的关键边界：

- 只有 ME-Brain 和 ME-Who 两个权威图谱领域；
- 自动抽取先进入 Candidate，不能直接成为权威事实；
- ME-Who 有独立隐私与适用范围；
- PostgreSQL 是权威存储，JSON / Markdown / HTML 只是投影；
- MCP 只暴露受控查询，不暴露任意写入型 SQL 或 Cypher。

## 2. 值得吸收的能力

### 2.1 单一职责的多阶段索引流水线

Graphify 将检测、抽取、建图、聚类、分析和输出拆为边界清晰的阶段。ME-System 对应采用：

```text
detect source
→ normalize source
→ extract evidence
→ validate extraction
→ propose graph changes
→ review
→ persist canonical graph
→ analyze
→ serve through MCP
```

每个 Adapter 只处理输入，不拥有自己的数据库、不直接写权威图谱，也不定义 MCP 工具。

### 2.2 显式说明一条边是怎样得到的

Graphify 区分：

```text
EXTRACTED
INFERRED
AMBIGUOUS
```

ME-System 后续应增加独立的 `derivation_kind`：

```text
EXPLICIT          原文明确表达或确定性解析
RULE_DERIVED      可审计规则推导
MODEL_INFERRED    模型推断
AMBIGUOUS         存在多个合理解释
HUMAN_ASSERTED    人工直接建立
```

它不能取代现有字段：

- `authority`：是否属于权威层；
- `confirmation_status`：谁确认过；
- `confidence`：不确定程度；
- `source_refs`：证据在哪里。

### 2.3 路径式回答

Graphify 的 query、path 和 explain 思路值得吸收。Agent 不应只得到摘要，而应得到：

```text
节点 A
→ 关系 1
→ 节点 B
→ 关系 2
→ 节点 C
→ EvidenceRef
```

ME-System 在现有领域工具之外，后续增加受控只读工具：

```text
brain_get_node
brain_get_neighbors
brain_shortest_path
brain_explain_path
```

领域工具继续承担高频、低 Token 查询：

```text
brain_get_snapshot
brain_trace_decision
brain_analyze_impact
who_get_task_profile
```

### 2.4 人类可读的 Graph Report

Graphify 同时输出 JSON、Markdown 报告与 HTML 图。ME-System 可生成可再生投影：

```text
me-system-out/
├── brain-report.md
├── brain-snapshot.json
├── graph-manifest.json
├── who-report.md        # 默认本地私有，不提交 Git
└── graph.html           # 后置
```

报告可以包含：

- 当前项目状态；
- 关键决策与替代链；
- 高频阻塞 Issue；
- 高影响 Constraint；
- 不确定和待审核关系；
- 图谱覆盖率；
- 推荐查询问题。

报告只是投影，不是权威数据源。

### 2.5 增量索引、Manifest 与 Watch

Graphify 支持只处理变化内容、监听文件变化和 Git Hook。ME-System 应采用：

```text
content hash
+ adapter version
+ extraction rule/model version
+ source manifest
→ 幂等增量摄取
```

后续命令形态：

```text
me-system index --update
me-system watch
me-system hook install
```

Hook 默认非阻塞，只提示图谱过期或创建摄取任务，不能阻断正常 Git 操作。

### 2.6 Query-first Agent 引导

Graphify 会给 Agent 安装简短指令，让 Agent 先查图再扫描文件。ME-System 对 Hermes、Pi、Codex 采用：

```text
1. resolve project
2. get snapshot / task profile
3. 必要时 expand / path / evidence
4. 最后才读取原始文件
```

动态项目状态不能复制到 `.hermes.md` 或 `AGENTS.md`；这些文件只保存查询策略。

### 2.7 社区、中心性与影响分析

Graphify 的 communities、god nodes 和 surprising connections 可以映射为：

#### ME-Brain

- 高影响 Decision / Constraint；
- 多任务依赖的 Artifact；
- 高频阻塞 Issue；
- 工作流社区；
- 跨项目共享组件；
- 变更影响路径。

#### ME-Who

- 高频生效的 CollaborationRule；
- 跨项目稳定能力；
- 相互冲突的偏好；
- 适用范围异常宽的规则。

ME-Who 的中心性不能直接被解释成人格重要性，且结果必须经过隐私过滤。

### 2.8 Benchmark 是产品能力

ME-System 应建立可重复比较：

```text
A. Agent 全文件探索
B. 普通全文 / 向量检索
C. ME-System 图谱查询
```

指标：

- 输入 Token；
- 工具调用次数；
- 当前事实准确率；
- 历史事实混淆率；
- 证据覆盖率；
- 查询延迟；
- 摄取成本；
- 增量更新时间。

第一组继续使用 `lighting-platform`。

## 3. 不应照搬的部分

### 3.1 不把单个 graph.json 当权威数据库

ME-System 需要时间、事务、权限、候选审核、证据约束和跨进程一致性，因此 PostgreSQL 继续作为权威存储；JSON 仅用于导出、缓存和 Benchmark。

### 3.2 不把 ME-Brain 与 ME-Who 压成一张平面图

两者通过 Bridge 关联，但保持：

- 独立 namespace；
- 独立本体；
- 独立权限；
- 独立审核策略。

### 3.3 不让推断关系直接进入权威图谱

```text
MODEL_INFERRED / AMBIGUOUS
→ Candidate
→ 审核
→ Canonical
```

### 3.4 不默认提交完整 ME-Who 图谱

ME-Who 默认本地私有，不提交 Git、不生成公开 HTML、不向项目执行 Agent 全量开放。

### 3.5 第一阶段不开放任意图查询语言

优先类型化工具；权限、查询成本和输出限制稳定后，才评估只读查询 DSL。

## 4. 吸收优先级

| 能力 | 优先级 | 落点 |
|---|---:|---|
| 一个产品、一个索引流水线 | A+ | 统一 `me_system` 包 |
| derivation 标签 | A+ | Graph Schema v0.2 |
| query-first Agent 规则 | A+ | Hermes / Pi / Codex |
| 增量 manifest 与 hash | A+ | Evidence / Ingestion |
| 路径与 explain 查询 | A | MCP 第二批工具 |
| Graph Report | A | 人工审阅与项目恢复 |
| Benchmark harness | A | `benchmarks/` |
| community / centrality | B | ME-Brain 影响分析 |
| HTML 图谱浏览 | B | 轻量治理投影 |
| watch / Git hook | B | Adapter 稳定后 |
| PR 影响分析 | B | Software Domain Pack |
| 任意只读查询 DSL | C | 权限稳定后评估 |
| 将完整 ME-Who 提交 Git | 不采用 | 隐私边界 |

## 5. 推荐开发顺序

```text
1. 统一为一个 me_system 包
2. Source / Evidence / Candidate 持久化
3. 增量 manifest 与 Adapter versioning
4. Agent Conversation Adapter
5. 路径式 MCP 查询
6. Graph Report 与 Benchmark
7. Markdown / Git / Zotero Adapter
8. 社区和影响分析
```

## 6. 结论

Graphify 最值得借鉴的不是另一个产品名字或数据库，而是：

> 把索引、持久化图谱、可审计路径、报告、增量更新和 Agent 查询做成一个连贯产品闭环。

ME-System 的最终表达仍然只有：

```text
ME-System
├── ME-Brain
└── ME-Who
```

Persistence、Evidence、Ingestion、Review、Query 与 MCP 都只是二者共享的内部职责。