# ME-Brain 产品定义

> 定位：面向科研、设计、开发等客观项目的结构化元数据、项目语义索引与 Agent 上下文运行时。

## 1. 产品目标

ME-Brain 将分散在文件、对话、Git、文献、邮件、会议和成果物中的项目信息，转换为 Agent 可快速检索、可按需展开、可追溯和可增量更新的项目结构。

核心目标：

- 降低 Agent 恢复项目所需的 Token；
- 减少反复扫描原始文件；
- 提升当前状态和有效决策识别准确度；
- 提升跨文件、跨工具和跨阶段检索速度；
- 保持多个 Agent 对项目事实的一致理解；
- 支持项目影响分析、交接和长期演化。

## 2. ME-Brain 不是哪些产品

ME-Brain 不是：

- 网盘；
- 普通笔记软件；
- 纯项目管理工具；
- 只提供向量搜索的 RAG；
- 自动知识图谱展示器；
- 文件摘要集合；
- 将全部材料塞入长上下文的聊天应用。

准确表达是：

> 面向 Agent 的 Project Semantic Index 与 Project Context Compiler。

## 3. 核心对象

### 3.1 Project

项目身份、目标、范围、状态、阶段和边界。

### 3.2 Workstream

可独立推进的工作流或子项目。

### 3.3 Requirement

明确需求及其来源、状态、优先级、验收条件和变更历史。

### 3.4 Decision

项目已确认决策，至少包含：

```yaml
id:
project_id:
decision:
status:
rationale:
alternatives_considered: []
constraints: []
decided_at:
decided_by: []
source_ids: []
supersedes:
valid_from:
valid_to:
```

### 3.5 Task

当前和历史任务，包括负责人、依赖、状态、输入、输出和完成证据。

### 3.6 Milestone

关键阶段与可验证完成条件。

### 3.7 Artifact

项目成果物，例如：

- 文档；
- 代码；
- 图纸；
- 模型；
- 数据集；
- 图片；
- PPT；
- Excel；
- 发布版本；
- 实验结果。

### 3.8 Issue / Risk

当前问题、风险、触发条件、影响范围、处理状态和责任人。

### 3.9 Constraint

技术、业务、时间、资源、标准、部署和用户确认边界。

### 3.10 Experiment / Claim / Review

用于科研、设计评审和技术验证：

- Experiment：方法、输入、参数、结果、重复性；
- Claim：结论及证据；
- Review：评审意见、处置状态和影响对象。

### 3.11 Event

项目时间线中的结构化事件，例如启动、决策、提交、评审、发布和方案替代。

## 4. 四层数据架构

### Layer 0：Source Ledger

不可变原始资料和版本：

```yaml
source_id:
source_type:
project_candidates: []
created_at:
author:
content_ref:
checksum:
version:
permissions:
```

### Layer 1：Canonical Project Metadata

权威项目元数据，来自：

- 用户明确确认；
- 正式项目文件；
- 受控规则；
- 经审核的 Agent 候选更新。

### Layer 2：Derived Index

可重新生成：

- 向量；
- BM25 / 全文；
- 时间关系图；
- 自动实体关系；
- 文件摘要；
- 主题社区；
- 影响分析缓存；
- 检索重排特征。

### Layer 3：Project Context Pack

针对当前任务生成的临时上下文，不作为项目事实源。

## 5. 输入类型

第一阶段优先：

- 本地项目文件；
- Markdown / DOCX / PPTX / XLSX；
- Git 仓库、Issue、PR、Commit；
- Agent 对话；
- Zotero 元数据和文献记录；
- 用户明确确认的项目结论。

后续扩展：

- 邮件；
- 日历；
- 即时通讯；
- BIM / IFC / USD；
- CAD / Rhino / Blender；
- 图片和视频；
- 外部知识平台。

## 6. 增量结构化流程

```text
识别来源
→ 文件或事件解析
→ 项目归属判断
→ 实体识别与消歧
→ 候选 Requirement / Decision / Task / Artifact 提取
→ 与当前权威数据比较
→ 冲突、重复和替代检测
→ 规则确认或人工确认
→ 更新 Canonical Project Metadata
→ 局部重建 Derived Index
```

不得因为新增文件而重建整个项目知识库，除非版本迁移或质量修复需要。

## 7. 当前事实与历史事实

ME-Brain 必须回答两个不同问题：

- 现在什么是真的；
- 过去某个时间点什么是真的。

所有会变化的高价值对象应具备：

```yaml
valid_from:
valid_to:
status:
supersedes:
superseded_by:
```

旧事实被替代后不删除，而是退出当前有效集合。

## 8. 类型化查询

ME-Brain 不应只有一个通用 `search(query)`。

建议首批 MCP / API：

```text
get_project_brief
get_current_project_state
list_active_requirements
list_confirmed_decisions
trace_decision_history
list_open_tasks
list_unresolved_issues
get_recent_changes
get_artifact_lineage
analyze_change_impact
get_evidence
compile_project_context
```

类型化工具可以减少 Agent 反复猜测搜索词和读取无关片段。

## 9. 混合检索流程

建议顺序：

```text
结构化过滤
→ 全文 / BM25
→ 向量召回
→ 图关系扩展
→ 时间有效性过滤
→ 权限过滤
→ 重排序
→ 证据装载
```

检索结果必须区分：

- 当前确认事实；
- 历史事实；
- 自动抽取候选；
- 相关原文；
- Agent 推断。

## 10. Project Context Compiler

### 输入

```yaml
project_id:
task:
agent_id:
agent_type:
token_budget:
required_freshness:
evidence_level:
permissions:
personal_context_ref:
```

### 输出

```yaml
project_brief:
current_state:
relevant_requirements:
relevant_decisions:
active_constraints:
open_tasks:
open_issues:
related_artifacts:
recent_changes:
evidence_refs:
excluded_outdated_facts:
```

## 11. 渐进式装载

| 层级 | 内容 |
|---|---|
| L1 | 项目名称、目标、范围、当前阶段 |
| L2 | 当前任务、关键决策、约束、问题 |
| L3 | 相关实体、事件、版本和关系 |
| L4 | 原始证据片段 |
| L5 | 完整文件、完整对话或代码上下文 |

默认从 L1 和 L2 开始，不允许 Agent 每次从 L5 开始探索。

## 12. 领域包

### 12.1 Software Pack

```text
Repository
Module
Component
Interface
ADR
Issue
PullRequest
Commit
Release
Dependency
Test
```

优先级最高，因为代码具有可确定解析结构，可以直接验证类似 Codebase-Memory 的结构化收益。

### 12.2 Research Pack

```text
ResearchQuestion
Hypothesis
Paper
Citation
Dataset
Method
Experiment
Finding
Limitation
```

与 Zotero 和论文工作流结合。

### 12.3 Design Pack

```text
Brief
SiteCondition
Constraint
Option
DesignDecision
Drawing
Model
ReviewComment
Revision
Deliverable
```

用于建筑、照明、产品和视觉设计项目。

第一版不构建万能本体。共享核心只包含跨领域稳定对象，其余由领域包扩展。

## 13. 权威性规则

### 高可信来源

- 用户明确确认；
- 正式决策文件；
- 代码或系统可确定解析结果；
- 受控数据库记录；
- 已合并提交或正式发布。

### 需要审核的来源

- LLM 自动抽取；
- 非正式聊天；
- 模糊代词和项目归属；
- 多份材料存在冲突；
- 对需求、意图和结论的推断。

Agent 只能直接写入低风险派生索引。对权威项目元数据默认提交候选变更。

## 14. 第一阶段评价指标

### 效率

- 恢复项目所需输入 Token；
- 工具调用次数；
- 首次查询延迟；
- 增量更新耗时；
- 原文下钻比例。

### 准确度

- 当前状态回答准确率；
- 过期方案误用率；
- 已确认决策来源覆盖率；
- 项目归属错误率；
- 文件与成果版本识别准确率；
- 影响分析准确率。

### 使用价值

- Agent 首轮可执行方案比例；
- 项目交接时间；
- 重复读取文件比例；
- 用户纠正项目事实的次数。

## 15. 第一批验证项目

1. `lighting-platform`：验证架构决策、代码、文档、技术路线和开发记录；
2. Zotero / 论文工作流：验证文献、研究问题、引用和流程状态；
3. AI 超级画板或泰典物业：验证设计决策、视觉成果、评审和版本关系。

固定问题集用于比较：

```text
A. 直接文件探索
B. 普通向量 RAG
C. ME-Brain
D. ME-Brain + ME-Who
```

第一阶段目标不是证明知识图谱“看起来更智能”，而是证明结构化项目语义能够在真实任务中降低成本并提升准确度。
