# ME-Core 输入、证据与 Candidate 持久化设计

> 状态：已按“单一核心”原则收敛  
> 日期：2026-07-23  
> 范围：ME-Core 的输入与治理子系统，不包含具体对话解析规则

## 1. 核心判断

ME-System 只有一个运行内核：

```text
ME-Core
```

ME-Brain 与 ME-Who 是 ME-Core 内的两个权威图谱域。Source、Evidence、Candidate、Query、MCP 和 CLI 都是 ME-Core 的内部能力或薄前端，不是新的平级产品或核心。

本设计补齐一条可靠的数据增长链：

```text
外部资料
→ SourceRecord
→ EvidenceFragment
→ IngestionRun
→ CandidateGraphChange
→ Review
→ ME-Brain / ME-Who Canonical Graph
```

现有待审核 Candidate 只保存在进程内，重启后会丢失。若直接开发 Agent Conversation Adapter，虽然能产生候选，却无法形成可重试、可审计和原子提交的闭环。

因此实施顺序为：

```text
统一 ME-Core 名称
→ Source / Evidence / Ingestion Status
→ Persistent Candidate Buffer
→ Atomic Review
→ Conversation Adapter
```

## 2. 与 Codebase-Memory 的关系

吸收 Codebase-Memory 的架构优点：

- 单一结构后端；
- 多阶段 Pipeline；
- 持久化图谱优先；
- MCP 与 CLI 共用同一应用服务；
- 紧凑结果优先，按需下钻；
- 索引状态和覆盖率是一等能力；
- Agent 负责自然语言理解，后端不内置回答问题的 LLM。

不照搬：

- SQLite 单项目权威库；
- 自动抽取直接写入权威图谱；
- 向普通 Agent 暴露任意 Cypher；
- 一次性开放大量工具；
- 第一阶段追求静态原生二进制。

ME-System 继续使用一个 PostgreSQL 权威数据库，并保留 Candidate 审核边界。

## 3. 目标

本切片完成后应支持：

1. 幂等登记外部来源；
2. 保存可寻址的证据片段；
3. 记录一次摄取 Pass 的状态、覆盖率和质量；
4. 持久化 `CandidateGraphChange`；
5. 进程重启后继续查看待审核候选；
6. 在一个 PostgreSQL 事务中批准 Candidate 并写入权威图谱；
7. 驳回 Candidate 并保留原因；
8. 保存不可变 Review Event；
9. 权威节点或边能回到 Source 与 EvidenceFragment；
10. 为 Conversation、Markdown、Git、Zotero Adapter 提供统一入口；
11. MCP、CLI 和未来 Web UI 共用同一应用服务；
12. 不新增第二个核心、数据库或权威 Schema。

## 4. 非目标

本切片不实现：

- LLM 自动抽取；
- Agent Conversation Adapter；
- Markdown、Git、Zotero、DOCX 或 PDF Adapter；
- 修改和删除权威节点；
- Candidate 修改后批准；
- Web 审核界面；
- 原始二进制文件存储；
- 对象存储服务；
- Hermes 写入 MCP；
- 多用户审批流；
- 分布式 Worker；
- 第二个数据库；
- 任意 Cypher。

Candidate v0.1 继续只支持：

```text
add_node
add_edge
```

## 5. 总体架构

```text
Adapters / Ingestion Passes
             │
             ▼
           ME-Core
├── SourceLedgerService
├── IngestionStatusService
├── CandidateBufferService
├── CandidateReviewService
├── GraphQueryService
├── ME-Brain Graph
├── ME-Who Graph
└── Bridge
             │
        ┌────┴────┐
        ▼         ▼
       MCP       CLI
```

所有权威数据继续位于同一个 PostgreSQL：

```text
PostgreSQL
├── graph_objects
├── graph_evidence_refs
├── source_records
├── evidence_fragments
├── ingestion_runs
├── candidate_graph_changes
├── candidate_evidence_refs
└── candidate_review_events
```

## 6. 名称迁移

在增加新表和新模块前完成：

```text
services/me-graph-core/  → services/me-core/
me_graph_core            → me_core
me-graph-core            → me-core
```

产品入口统一使用：

```text
me-system
me-system-mcp
```

兼容策略：

- `me-graph` 和 `me-graph-mcp` 保留一个小版本作为别名；
- 新文档和新测试只使用 `me-system` / `me-system-mcp`；
- 数据库表名和环境变量 `ME_GRAPH_*` 在 v0.1 保持不变，避免无价值迁移；
- 本体命名空间继续使用 `me_brain`、`me_who`、`bridge`。

## 7. SourceRecord

### 7.1 作用

`SourceRecord` 表示一份不可变外部来源登记，例如：

- Agent 对话导出；
- Markdown 文件版本；
- Git Commit；
- Zotero Item 快照；
- 邮件；
- 文档版本。

v0.1 记录来源身份、位置和校验信息，不负责保存大型二进制原文件。

### 7.2 字段

```text
source_id             text primary key
source_type           text not null
external_system       nullable text
external_id           nullable text
idempotency_key       text not null unique
content_ref           text not null
content_sha256        text not null
media_type            nullable text
occurred_at           nullable timestamptz
ingested_at           timestamptz not null
sensitivity           text not null
metadata              json/jsonb not null
```

### 7.3 不可变与幂等

相同 `idempotency_key` 再次登记：

- `content_sha256` 与规范化元数据相同：返回现有 SourceRecord；
- 内容不同：抛出 `SourceConflictError`；
- 不静默覆盖。

`content_ref` 示例：

```text
file:///data/exports/conversation.json
zotero://select/library/items/ABCD1234
git://ArchitectureWorld/repo@commit-sha
```

API 与 Agent 输出默认不暴露完整主机路径。

## 8. EvidenceFragment

### 8.1 作用

`EvidenceFragment` 是来源中可被图谱对象稳定引用的最小证据单元。

第一批类型：

```text
conversation_message
paragraph
heading
list_item
code_block
git_commit
unknown
```

### 8.2 字段

```text
fragment_id           text primary key
source_id             FK source_records.source_id
ordinal               integer not null
fragment_type         text not null
text_content          nullable text
source_anchor         json/jsonb not null
content_sha256        text not null
occurred_at           nullable timestamptz
actor_id              nullable text
sensitivity           text not null
metadata              json/jsonb not null
```

约束：

```text
unique(source_id, ordinal)
```

`fragment_id` 全局唯一，因此不再增加无意义的 `unique(source_id, fragment_id)`。

### 8.3 SourceAnchor

```yaml
type: conversation_message
value:
  conversation_id: conv_001
  message_id: msg_0042
```

`EvidenceRef.content_fragment_id` 指向该记录。

## 9. IngestionRun

### 9.1 作用

`IngestionRun` 同时承担运行记录、Index Status 和 Coverage 信号，回答：

- 哪个 Adapter / Pass 处理了来源；
- 使用哪个版本；
- 输入多少项；
- 成功、跳过、失败多少项；
- 生成多少 Fragment 和 Candidate；
- 是否只覆盖部分内容；
- 存在哪些质量问题。

### 9.2 字段

```text
run_id                   text primary key
source_id                FK source_records.source_id
adapter_name             text not null
adapter_version          text not null
pipeline_version         text not null
status                   pending | running | completed | partial | failed
started_at               timestamptz not null
completed_at             nullable timestamptz
input_item_count         integer not null default 0
processed_item_count     integer not null default 0
skipped_item_count       integer not null default 0
failed_item_count        integer not null default 0
fragment_count           integer not null default 0
candidate_count          integer not null default 0
coverage_ratio           numeric not null default 0
quality_report           json/jsonb not null
log_ref                  nullable text
error_summary            nullable text
```

约束：

```text
0 <= coverage_ratio <= 1
processed + skipped + failed <= input
completed_at required for completed | partial | failed
```

完整 traceback、数据库 URL 和私人正文不写入 `error_summary`。

## 10. CandidateGraphChangeRecord

### 10.1 字段

```text
change_id              text primary key
target_graph           me_brain | me_who | bridge
operation              add_node | add_edge
submitted_by           text not null
reason                 text not null
payload                json/jsonb not null
payload_sha256         text not null
idempotency_key        text not null unique
review_status          pending | approved | rejected
created_at             timestamptz not null
reviewed_at            nullable timestamptz
reviewed_by            nullable text
review_reason          nullable text
approved_object_id     nullable FK graph_objects.id
ingestion_run_id       nullable FK ingestion_runs.run_id
```

### 10.2 Candidate Evidence

```text
candidate_evidence_refs
├── id
├── change_id
├── ordinal
├── source_id
├── document_id
├── version_id
├── content_fragment_id
└── source_anchor
```

约束：

```text
unique(change_id, ordinal)
```

若 `content_fragment_id` 非空，必须引用存在的 `evidence_fragments.fragment_id`。

### 10.3 幂等

相同 `idempotency_key`：

- payload hash 和 EvidenceRef hash 相同：返回现有 Candidate；
- 任一不同：抛出 `CandidateConflictError`；
- 已审核 Candidate 不重新变为 pending。

推荐键：

```text
adapter_name
+ source_id
+ extraction_rule_or_model_version
+ normalized_candidate_identity
```

## 11. CandidateReviewEvent

Review Event 只追加、不覆盖：

```text
event_id               text primary key
change_id              FK candidate_graph_changes.change_id
event_type              submitted | approved | rejected
actor_id                text not null
actor_kind              adapter | agent | human | rule
reason                  text not null
created_at              timestamptz not null
metadata                json/jsonb not null
```

每次提交、批准或驳回至少产生一条事件。

## 12. 应用服务边界

### 12.1 SourceLedgerService

```python
class SourceLedgerService:
    def register_source(self, source: SourceRecord) -> SourceRecord: ...
    def get_source(self, source_id: str) -> SourceRecord: ...
    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]: ...
    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]: ...
```

### 12.2 IngestionStatusService

```python
class IngestionStatusService:
    def create_run(self, run: IngestionRun) -> IngestionRun: ...
    def start_run(self, run_id: str) -> IngestionRun: ...
    def finish_run(
        self,
        run_id: str,
        *,
        status: IngestionStatus,
        counts: IngestionCounts,
        quality_report: Mapping[str, object],
        log_ref: str | None = None,
        error_summary: str | None = None,
    ) -> IngestionRun: ...
    def get_run(self, run_id: str) -> IngestionRun: ...
```

### 12.3 CandidateBufferService

```python
class CandidateBufferService:
    def submit(
        self,
        change: CandidateGraphChangeRecord,
    ) -> CandidateGraphChangeRecord: ...
    def get(self, change_id: str) -> CandidateGraphChangeRecord: ...
    def list_pending(
        self,
        *,
        target_graph: GraphNamespace | None = None,
        source_id: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> CandidatePage: ...
```

`CandidatePage` 返回：

```text
total
returned
next_cursor
truncated
items
```

### 12.4 CandidateReviewService

```python
class CandidateReviewService:
    def approve(
        self,
        change_id: str,
        reviewer_id: str,
        *,
        reviewer_kind: str = "human",
        reason: str = "approved",
    ) -> GraphNode | GraphEdge: ...

    def reject(
        self,
        change_id: str,
        reviewer_id: str,
        reason: str,
        *,
        reviewer_kind: str = "human",
    ) -> None: ...
```

MCP、CLI 和未来 Web UI 只调用这些应用服务。

## 13. 原子批准

批准必须在一个 SQLAlchemy Session 事务中完成：

```text
BEGIN
→ SELECT candidate FOR UPDATE
→ 验证 status = pending
→ materialize GraphNode / GraphEdge
→ 合并并验证 EvidenceRef
→ 校验 ME-Brain / ME-Who / Bridge 规则
→ 写 graph_objects
→ 写 graph_evidence_refs
→ 更新 candidate = approved
→ 写 approved ReviewEvent
COMMIT
```

任一步失败全部回滚。

禁止出现：

- 图谱对象存在但 Candidate 仍 pending；
- Candidate approved 但图谱对象不存在；
- 图谱对象存在但证据缺失；
- 审核事件与当前状态不一致。

## 14. 代码结构

目标结构：

```text
services/me-core/src/me_core/
├── contracts.py
├── store.py
├── query.py
├── persistence/
│   ├── models.py
│   ├── graph_writer.py
│   ├── source_repository.py
│   ├── candidate_repository.py
│   └── review.py
├── ingestion/
│   ├── __init__.py
│   ├── contracts.py
│   ├── source.py
│   ├── status.py
│   ├── candidate.py
│   ├── review.py
│   └── pipeline.py
├── adapters/
├── mcp/
└── cli.py
```

`SqlAlchemyGraphStore` 与 Candidate Review 共用 `graph_writer.py`，避免复制节点、边和 EvidenceRef 映射逻辑。

## 15. 数据库迁移

新增 Alembic：

```text
0002_create_ingestion_and_candidates.py
```

创建：

- `source_records`；
- `evidence_fragments`；
- `ingestion_runs`；
- `candidate_graph_changes`；
- `candidate_evidence_refs`；
- `candidate_review_events`；
- 外键、检查约束和索引。

第一批索引：

```text
source_records(idempotency_key)
source_records(external_system, external_id)
evidence_fragments(source_id, ordinal)
ingestion_runs(source_id, started_at)
ingestion_runs(status, started_at)
candidate_graph_changes(review_status, created_at)
candidate_graph_changes(target_graph, review_status)
candidate_graph_changes(ingestion_run_id)
candidate_evidence_refs(source_id)
candidate_evidence_refs(content_fragment_id)
candidate_review_events(change_id, created_at)
```

## 16. CLI 与 MCP 策略

新增主 CLI：

```text
me-system source register
me-system source show
me-system ingestion status
me-system candidate submit
me-system candidate list
me-system candidate approve
me-system candidate reject
```

第一版 CLI 接受 JSON 文件，服务于契约验收、调试和治理。

当前 Hermes MCP 继续保持六个只读工具，不在本切片增加写入工具。

输入持久化稳定后，再评估新增只读质量工具：

```text
graph_get_schema
ingestion_get_status
graph_get_coverage
```

这些工具必须通过统一 Tool Registry 注册，并与 CLI 共用服务。

## 17. 错误类型

新增：

```text
SourceConflictError
SourceNotFoundError
IngestionRunError
CandidateConflictError
CandidateNotFoundError
CandidateStateError
```

错误不得包含：

- 数据库密码；
- 完整连接字符串；
- 原始私人正文；
- Python traceback；
- 未授权项目列表。

## 18. 安全与隐私

- SourceRecord 和 EvidenceFragment 必须带 sensitivity；
- ME-Who 候选默认至少为 `personal_private`；
- Adapter 不得把私人正文写入错误摘要；
- `content_ref` 对 Agent 默认脱敏；
- Hermes 保持只读；
- Candidate 管理能力不加入现有六工具；
- 所有权威写入使用同一 PostgreSQL 事务；
- 不允许 Adapter 自己拥有权威表。

## 19. 测试策略

### 19.1 名称迁移

- `me_core` 导入成功；
- 旧 `me_graph_core` 兼容层能发出弃用警告；
- `me-system` 和 `me-system-mcp` 可运行；
- 旧命令别名在兼容期仍可运行；
- 文档、CI 和安装路径使用新名称。

### 19.2 Source / Evidence

- 首次登记；
- 相同内容幂等重试；
- 内容冲突；
- 片段顺序；
- SourceAnchor；
- 敏感度；
- Source 不存在；
- 重启后读取。

### 19.3 Ingestion Status

- pending → running → completed；
- partial；
- failed；
- 非法状态迁移；
- 计数约束；
- coverage 约束；
- quality_report 和 log_ref 往返。

### 19.4 Candidate Buffer

- 提交和跨重启读取；
- 幂等重试；
- 幂等冲突；
- 按图谱和来源过滤；
- 分页；
- EvidenceRef 顺序；
- 不允许非 pending payload 入队。

### 19.5 Review

- 批准节点；
- 批准边；
- 驳回；
- 重复审核；
- 命名空间错误回滚；
- 缺失端点回滚；
- ID 冲突回滚；
- Review Event 追加；
- 图谱、Candidate 和 Event 原子一致。

### 19.6 PostgreSQL E2E

```text
register source
→ add fragments
→ create ingestion run
→ submit node candidate
→ approve node
→ submit edge candidate
→ approve edge
→ recreate services
→ query graph, status and review history
```

## 20. 验收标准

- 仓库概念上和代码命名上只有一个 ME-Core；
- ME-Brain 与 ME-Who 是 ME-Core 内的两个图谱域；
- Source、Fragment、Run、Candidate 和 Review Event 跨进程保存；
- 相同来源和 Candidate 重试不产生重复记录；
- 批准操作单事务完成；
- 批准失败不留下部分写入；
- 权威对象和 Candidate 都能回到相同 EvidenceFragment；
- IngestionRun 明确暴露覆盖率和失败范围；
- Hermes MCP 仍只有六个只读工具；
- Python 3.11、3.12 和 PostgreSQL 16 CI 通过；
- 不新增第二个权威数据库、第二套图谱语义或平级核心。

## 21. 后续顺序

```text
ME-Core 名称迁移
→ 输入与 Candidate 持久化
→ Agent Conversation Pass
→ Markdown Pass
→ Git Pass
→ Candidate 审核界面
→ ingestion status / coverage MCP
→ Hermes 受控 Candidate 提交（另行设计）
```

Conversation Adapter 只负责：

```text
对话导出
→ SourceRecord
→ conversation_message EvidenceFragment
→ CandidateGraphChangeRecord
```

它不直接写入 ME-Brain 或 ME-Who。