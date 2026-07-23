# Source Ledger 与 Candidate 持久化设计

> 状态：待评审  
> 日期：2026-07-23  
> 范围：ME-System 输入与治理基础，不包含具体对话解析规则

## 1. 背景与判断

ME-System 已经具备：

- ME-Brain、ME-Who、Bridge 双图谱契约；
- PostgreSQL GraphStore；
- CandidateGraphChange 领域契约；
- 进程内候选提交、批准和驳回；
- Hermes 六工具只读 MCP。

但当前仍缺少一条可靠的数据增长链：

```text
外部资料
→ 可追溯来源
→ 标准证据片段
→ 候选图谱变更
→ 审核记录
→ 权威图谱
```

现有 `CandidateReviewService` 把待审核候选保存在内存中。进程重启后候选会丢失，也没有持久化审核事件。若此时直接开发 Agent Conversation Adapter，Adapter 虽然可以生成候选，但无法形成可靠、可重试、可审计的输入闭环。

因此下一实施切片调整为：

> 先建立 Source Ledger、Evidence Fragment、Ingestion Run、Persistent Candidate Queue 和 Review Event，再接入 Agent Conversation Adapter。

## 2. 目标

本切片完成后，系统应支持：

1. 幂等登记一份外部来源；
2. 保存来源中的标准证据片段；
3. 记录 Adapter 的一次摄取运行及质量状态；
4. 持久化 `CandidateGraphChange`；
5. 进程重启后继续查看待审核候选；
6. 在一个数据库事务中批准候选并写入权威图谱；
7. 驳回候选并保留原因；
8. 保存不可变审核事件；
9. 任一权威节点或边仍能回到来源与证据片段；
10. 为后续 Conversation、Markdown、Git、Zotero Adapter 提供统一接口。

## 3. 非目标

本切片暂不实现：

- LLM 自动抽取；
- Agent Conversation Adapter；
- Markdown、Git、Zotero 或 DOCX Adapter；
- 修改和删除权威节点；
- Candidate 修改后批准；
- Web 审核界面；
- 原始 PDF、DOCX 等二进制文件存储；
- 对象存储服务；
- Hermes 写入 MCP；
- 多用户审核工作流；
- 复杂任务队列和分布式 Worker。

Candidate v0.1 继续只支持：

```text
add_node
add_edge
```

## 4. 方案比较

### 4.1 方案 A：把来源和候选全部保存为 JSONB Blob

优点：

- 实现快；
- Schema 少；
- 与当前 `to_dict()` / `from_dict()` 直接兼容。

缺点：

- 很难建立稳定的来源、片段和审核关系；
- 无法高效按来源、状态、Adapter、时间过滤；
- 审核和权威写入的约束主要依赖应用层；
- 后续 Adapter 会各自形成不同 JSON 结构。

结论：不采用。

### 4.2 方案 B：同一 PostgreSQL 中建立独立 Source、Evidence、Candidate 和 Review 表

优点：

- 与现有 PostgreSQL GraphStore 共用事务和部署；
- 来源、证据、候选和审核边界清晰；
- 可以实现原子批准；
- 适合 NAS / Linux 本地优先部署；
- 不引入第二个权威数据库。

缺点：

- 需要增加迁移和 Repository；
- 需要抽取一部分 Session 级 Graph 写入能力。

结论：推荐。

### 4.3 方案 C：单独建设 Source Ledger 服务和数据库

优点：

- 服务隔离强；
- 未来可独立扩容。

缺点：

- 过早增加网络协议和分布式事务；
- 候选批准与权威图谱写入难以保持原子；
- 当前数据规模和团队阶段没有证明需要独立服务。

结论：暂不采用。

## 5. 总体架构

```text
External Source
      │
      ▼
SourceLedgerRepository
      ├── SourceRecord
      ├── EvidenceFragment
      └── IngestionRun
      │
      ▼
CandidateRepository
      └── CandidateGraphChangeRecord
      │
      ▼
PersistentCandidateReviewService
      ├── APPROVE ──► Canonical GraphObject
      ├── REJECT
      └── CandidateReviewEvent
```

所有数据继续位于同一个 PostgreSQL 数据库中。

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

## 6. SourceRecord

### 6.1 作用

`SourceRecord` 表示一份不可变外部来源的登记记录，例如：

- 一次 Agent 对话导出；
- 一个 Markdown 文件版本；
- 一次 Git Commit；
- 一个 Zotero Item 快照；
- 一封邮件；
- 一份文档版本。

Source Ledger v0.1 记录来源身份、位置和校验信息，不负责保存大型二进制原文件。

### 6.2 字段

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

### 6.3 不可变规则

同一个 `idempotency_key` 再次提交时：

- 若 `content_sha256` 和规范化元数据一致，返回现有 SourceRecord；
- 若内容不同，抛出 `SourceConflictError`；
- 不允许静默覆盖现有来源。

`content_ref` 可以是：

```text
file:///data/exports/conversation.json
zotero://select/library/items/ABCD1234
git://ArchitectureWorld/repo@commit-sha
```

后续对象存储切片可以新增 `storage_uri`，但不改变 `source_id`。

## 7. EvidenceFragment

### 7.1 作用

`EvidenceFragment` 是来源中可被图谱对象稳定引用的最小证据单元。

第一批片段类型：

```text
conversation_message
paragraph
heading
list_item
code_block
git_commit
unknown
```

### 7.2 字段

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
metadata              json/jsonb not null
```

约束：

```text
unique(source_id, ordinal)
unique(source_id, fragment_id)
```

### 7.3 SourceAnchor

示例：

```yaml
type: conversation_message
value:
  message_id: msg_0042
  conversation_id: conv_001
```

图谱中的 `EvidenceRef.content_fragment_id` 可以指向该记录。

## 8. IngestionRun

### 8.1 作用

记录一次 Adapter 运行，便于回答：

- 哪个 Adapter 处理了来源；
- 使用什么版本；
- 何时开始和结束；
- 成功、部分成功还是失败；
- 生成了多少片段和候选；
- 存在哪些质量问题。

### 8.2 字段

```text
run_id                 text primary key
source_id              FK source_records.source_id
adapter_name           text not null
adapter_version        text not null
status                 pending | running | completed | partial | failed
started_at             timestamptz not null
completed_at           nullable timestamptz
fragment_count         integer not null default 0
candidate_count        integer not null default 0
quality_report         json/jsonb not null
error_summary          nullable text
```

完整 Python traceback 不写入数据库；只保存脱敏摘要。

## 9. CandidateGraphChangeRecord

### 9.1 字段

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

### 9.2 候选证据

使用独立表：

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

### 9.3 幂等规则

提交相同 `idempotency_key` 时：

- payload hash 相同：返回现有候选；
- payload hash 不同：抛出 `CandidateConflictError`；
- 已批准或驳回的候选不会重新变为 pending。

推荐 Adapter 生成：

```text
idempotency_key
= adapter_name
+ source_id
+ extraction_rule_or_model_version
+ normalized_candidate_identity
```

## 10. CandidateReviewEvent

审核事件是追加写入，不覆盖历史。

字段：

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

## 11. Repository 与 Service 边界

### 11.1 SourceLedgerRepository

```python
class SourceLedgerRepository(Protocol):
    def register_source(self, source: SourceRecord) -> SourceRecord: ...
    def get_source(self, source_id: str) -> SourceRecord: ...
    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]: ...
    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]: ...
    def create_run(self, run: IngestionRun) -> IngestionRun: ...
    def complete_run(...): ...
```

### 11.2 CandidateRepository

```python
class CandidateRepository(Protocol):
    def submit(self, change: CandidateGraphChangeRecord) -> CandidateGraphChangeRecord: ...
    def get(self, change_id: str) -> CandidateGraphChangeRecord: ...
    def list_pending(
        self,
        *,
        target_graph: GraphNamespace | None = None,
        source_id: str | None = None,
        limit: int = 100,
    ) -> tuple[CandidateGraphChangeRecord, ...]: ...
```

### 11.3 PersistentCandidateReviewService

```python
class PersistentCandidateReviewService:
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

## 12. 原子批准

批准操作必须在一个 SQLAlchemy Session 事务中完成：

```text
BEGIN
→ SELECT candidate FOR UPDATE
→ 验证 status = pending
→ 通过 CandidateGraphChange.materialize() 重建领域对象
→ 合并 payload 和 Candidate EvidenceRef
→ 通过现有命名空间规则验证节点或边
→ 写 graph_objects
→ 写 graph_evidence_refs
→ 更新 candidate = approved
→ 写 approved review event
COMMIT
```

任何一步失败，全部回滚。

不允许出现：

- 图谱对象已经写入，但候选仍为 pending；
- 候选显示 approved，但没有权威对象；
- 权威对象存在但证据缺失。

## 13. 代码结构调整

建议新增：

```text
services/me-graph-core/src/me_graph_core/ingestion/
├── __init__.py
├── contracts.py
├── source_repository.py
├── candidate_repository.py
└── review.py

services/me-graph-core/src/me_graph_core/persistence/
├── models.py                 # 增加 ORM 表
├── source_repository.py      # SQLAlchemy Source Ledger
├── candidate_repository.py   # SQLAlchemy Candidate Queue
├── review.py                 # 原子批准和驳回
└── graph_writer.py           # Session 级节点/边写入辅助
```

`SqlAlchemyGraphStore` 与 Persistent Review 共用 `graph_writer.py`，避免复制节点、边和 EvidenceRef 的映射逻辑。

## 14. 数据库迁移

新增 Alembic：

```text
0002_create_source_ledger_and_candidates.py
```

创建：

- `source_records`；
- `evidence_fragments`；
- `ingestion_runs`；
- `candidate_graph_changes`；
- `candidate_evidence_refs`；
- `candidate_review_events`；
- 约束和索引。

第一批索引：

```text
source_records(idempotency_key)
source_records(external_system, external_id)
evidence_fragments(source_id, ordinal)
ingestion_runs(source_id, started_at)
candidate_graph_changes(review_status, created_at)
candidate_graph_changes(target_graph, review_status)
candidate_graph_changes(ingestion_run_id)
candidate_evidence_refs(source_id)
candidate_evidence_refs(content_fragment_id)
candidate_review_events(change_id, created_at)
```

## 15. CLI

新增管理命令：

```text
me-graph source-register
me-graph source-show
me-graph candidate-submit
me-graph candidate-list
me-graph candidate-approve
me-graph candidate-reject
```

第一版 CLI 接受 JSON 文件，主要用于：

- Adapter 契约验收；
- 数据迁移和调试；
- 在 Web 审核界面完成前提供治理入口。

所有输出继续使用结构化 JSON。

## 16. 错误类型

新增：

```text
SourceConflictError
SourceNotFoundError
IngestionRunError
CandidateConflictError
CandidateNotFoundError
CandidateStateError
```

错误信息不得包含：

- 数据库密码；
- 完整连接字符串；
- 原始私人消息正文；
- Python traceback。

## 17. 安全与隐私

- SourceRecord 和 EvidenceFragment 必须带 sensitivity；
- ME-Who 候选默认至少为 `personal_private`；
- Adapter 不得把原始私人消息写入错误摘要；
- `content_ref` 可以指向本地路径，但 API 和 Agent 输出默认不暴露完整主机路径；
- Hermes 当前保持只读，不暴露 Candidate CLI 或 Repository；
- Candidate 审核接口不会加入现有六个只读 MCP 工具。

## 18. 测试策略

### 18.1 Source Ledger

覆盖：

- 首次登记；
- 相同幂等键和相同内容重复登记；
- 相同幂等键但内容冲突；
- 片段顺序；
- 片段来源锚点；
- Source 不存在；
- 文件数据库重启后仍可读取。

### 18.2 Ingestion Run

覆盖：

- pending → running → completed；
- partial；
- failed；
- 非法状态迁移；
- 质量报告往返。

### 18.3 Candidate Queue

覆盖：

- 提交和跨重启读取；
- 幂等重试；
- 幂等冲突；
- 按图谱和来源过滤 pending；
- EvidenceRef 顺序；
- 不允许非 pending payload 进入队列。

### 18.4 Review

覆盖：

- 批准节点；
- 批准边；
- 驳回；
- 重复审核；
- 命名空间错误回滚；
- 缺失端点回滚；
- ID 冲突回滚；
- 审核事件追加；
- 权威对象、Candidate 状态和事件原子一致。

### 18.5 PostgreSQL E2E

CI 使用 PostgreSQL 16：

```text
register source
→ create fragments
→ submit node candidate
→ approve node
→ submit edge candidate
→ approve edge
→ rebuild repositories
→ query canonical graph and review history
```

## 19. 验收标准

- Source、Fragment、Run、Candidate 和 Review Event 均可跨进程保存；
- 相同来源重复摄取不产生重复记录；
- 相同 Candidate 重试不产生重复候选；
- 批准操作在单事务中完成；
- 批准失败不会留下部分写入；
- 候选批准后可被现有 GraphQueryService 查询；
- 候选和权威对象都能回到相同 EvidenceFragment；
- 当前 Hermes MCP 仍保持六个只读工具且测试不回归；
- Python 3.11、3.12 和 PostgreSQL 16 CI 通过；
- 不新增第二个权威数据库。

## 20. 后续顺序

本切片通过后：

```text
Agent Conversation Adapter
→ Markdown Adapter
→ Git Adapter
→ Candidate 审核界面
→ Hermes 受控 Candidate 提交（另行设计）
```

Agent Conversation Adapter 将只负责：

```text
对话导出
→ SourceRecord
→ conversation_message EvidenceFragment
→ CandidateGraphChangeRecord
```

它不直接写入 ME-Brain 或 ME-Who。