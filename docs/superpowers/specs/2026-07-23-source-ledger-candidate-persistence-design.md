# ME-Brain / ME-Who 共享输入与 Candidate 持久化设计

> 状态：已按“双图谱、无第三产品”原则修订  
> 日期：2026-07-23  
> 范围：ME-Brain 与 ME-Who 的共同输入、证据、候选和审核基础

## 1. 核心决策

ME-System 只有两个产品图谱：

```text
ME-System
├── ME-Brain
└── ME-Who
```

本设计不新增 ME-Core、ME-Graph-Core、Source Ledger 产品或 Candidate 服务。

Source、Evidence、IngestionRun 和 Candidate 是两个图谱共同使用的内部实现，放入无产品身份的 `shared/` 目录：

```text
External Source
      │
      ▼
shared/ingestion
      ├── SourceRecord
      ├── EvidenceFragment
      ├── IngestionRun
      └── CandidateGraphChange
                 │
                 ▼
              Review
          ┌──────┴──────┐
          ▼             ▼
      ME-Brain       ME-Who
```

Candidate 通过 `target_graph` 明确进入：

```text
me_brain
me_who
bridge
```

## 2. 为什么现在先做这一层

ME-System 已经具备：

- ME-Brain、ME-Who、Bridge 图谱契约；
- PostgreSQL 权威图谱存储；
- CandidateGraphChange 领域对象；
- 进程内候选审核；
- Hermes 六工具只读 MCP。

但还没有可靠的数据增长闭环：

```text
外部资料
→ 可追溯来源
→ 标准证据片段
→ 候选节点和关系
→ 审核
→ 权威图谱
```

当前候选只保存在内存中。若直接开发 Agent Conversation Adapter：

- 服务重启会丢失候选；
- Adapter 重试可能产生重复数据；
- 批准候选和写入图谱可能出现部分成功；
- 无法回答某个图谱对象来自哪次摄取；
- 无法判断某份来源是否处理完整。

因此先建立共同输入和候选持久化，再接入具体 Adapter。

## 3. Codebase-Memory 的参考方式

本设计吸收 Codebase-Memory 的以下逻辑：

1. **Graph first**：先建立持久化结构，再让 Agent 查询；
2. **Multi-pass pipeline**：发现、标准化、抽取、关系、状态分别处理；
3. **Incremental**：通过哈希和幂等键只处理变化内容；
4. **Index status**：完成度和质量是正式数据；
5. **MCP/CLI parity**：协议层不复制业务逻辑；
6. **No embedded answer LLM**：模型只生成候选，不决定权威事实。

不照搬：

- 每项目 SQLite 权威库；
- 自动索引直接修改权威语义事实；
- 面向普通 Agent 的任意 Cypher；
- 一次开放大量工具。

## 4. 目标

本切片完成后应支持：

1. 幂等登记外部来源；
2. 保存可稳定寻址的证据片段；
3. 记录每次摄取运行、版本、覆盖率和质量；
4. 持久化 CandidateGraphChange；
5. 重启后继续查看待审核 Candidate；
6. Candidate 批准和权威图谱写入使用一个事务；
7. 驳回 Candidate 并保留原因；
8. 保存追加式审核事件；
9. 权威节点和关系能够返回来源与证据片段；
10. 为 Conversation、Markdown、Git 和 Zotero Adapter 提供同一接口；
11. 不新增第二个数据库或第三个产品。

## 5. 非目标

本切片不实现：

- LLM 自动抽取策略；
- Agent Conversation Adapter；
- Markdown、Git、Zotero、DOCX、PDF Adapter；
- Candidate 修改后批准；
- 修改或删除权威节点；
- Web 审核界面；
- 二进制原文件存储；
- 对象存储服务；
- Hermes 写入 MCP；
- 分布式 Worker；
- 多租户审核编排。

Candidate v0.1 继续只支持：

```text
add_node
add_edge
```

## 6. 总体数据流

```text
Adapter
  │
  ├── register SourceRecord
  ├── append EvidenceFragment
  ├── create IngestionRun
  ├── submit CandidateGraphChange
  └── complete IngestionRun
            │
            ▼
      Persistent Review
            │
      ┌─────┴─────┐
      ▼           ▼
   approve      reject
      │
      ▼
ME-Brain / ME-Who / Bridge
```

任何 Adapter 都不能直接写 `graph_objects`。

## 7. SourceRecord

### 7.1 作用

SourceRecord 表示一份不可变的外部来源快照，例如：

- 一次 Agent 对话导出；
- 一个 Markdown 文件版本；
- 一次 Git Commit；
- 一个 Zotero Item 快照；
- 一封邮件；
- 一份 Office/PDF 文档版本。

第一版只登记来源身份、位置和完整性，不保存大型二进制内容。

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

### 7.3 幂等与不可变

相同 `idempotency_key` 再次登记：

```text
content hash + normalized metadata 相同
→ 返回已有 SourceRecord

任一内容不同
→ SourceConflictError
```

禁止静默覆盖。

`content_ref` 示例：

```text
file:///data/exports/conversation.json
zotero://select/library/items/ABCD1234
git://ArchitectureWorld/repo@commit-sha
```

## 8. EvidenceFragment

### 8.1 作用

EvidenceFragment 是图谱节点或关系可稳定引用的最小证据单元。

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
metadata              json/jsonb not null
```

约束：

```text
unique(source_id, ordinal)
unique(source_id, fragment_id)
```

### 8.3 SourceAnchor

```yaml
type: conversation_message
value:
  conversation_id: conv_001
  message_id: msg_0042
```

图谱对象中的 `EvidenceRef.content_fragment_id` 指向该记录。

## 9. IngestionRun

### 9.1 作用

IngestionRun 同时承担 Codebase-Memory 中 `index_status` 和覆盖率报告的作用。

它回答：

- 哪个 Adapter 处理了来源；
- 使用什么版本；
- 输入多少项；
- 成功、跳过和失败多少项；
- 产生多少 Evidence 和 Candidate；
- 图谱是否只完成部分覆盖；
- 质量问题在哪里。

### 9.2 字段

```text
run_id                  text primary key
source_id               FK source_records.source_id
adapter_name            text not null
adapter_version         text not null
status                  pending | running | completed | partial | failed
started_at              timestamptz not null
completed_at            nullable timestamptz
input_item_count        integer not null default 0
processed_item_count    integer not null default 0
skipped_item_count      integer not null default 0
failed_item_count       integer not null default 0
fragment_count          integer not null default 0
candidate_count         integer not null default 0
coverage_ratio          numeric not null default 0
quality_report          json/jsonb not null
log_ref                 nullable text
error_summary           nullable text
```

### 9.3 约束

```text
0 <= coverage_ratio <= 1
processed + skipped + failed <= input_item_count
completed_at required for completed | partial | failed
```

完整 traceback 不写入数据库，只保存脱敏摘要和 `log_ref`。

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

独立表：

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

### 10.3 幂等

相同 `idempotency_key`：

```text
payload hash 相同
→ 返回已有 Candidate

payload hash 不同
→ CandidateConflictError
```

已批准或驳回的 Candidate 不会重新变为 pending。

推荐键：

```text
adapter_name
+ source_id
+ extraction_version
+ normalized_candidate_identity
```

## 11. CandidateReviewEvent

审核事件只追加，不覆盖：

```text
event_id               text primary key
change_id              FK candidate_graph_changes.change_id
event_type             submitted | approved | rejected
actor_id                text not null
actor_kind              adapter | agent | human | rule
reason                  text not null
created_at              timestamptz not null
metadata                json/jsonb not null
```

每次 submit、approve、reject 都产生事件。

## 12. 共享代码边界

不再建立名为 ME-Core 或 Source Ledger 的产品模块。

目标结构：

```text
me-system/
├── me-brain/
│   ├── ontology/
│   ├── passes/
│   └── queries/
├── me-who/
│   ├── ontology/
│   ├── passes/
│   └── queries/
├── shared/
│   ├── contracts/
│   ├── graph/
│   ├── evidence/
│   ├── ingestion/
│   │   ├── contracts.py
│   │   ├── source_repository.py
│   │   ├── candidate_repository.py
│   │   ├── review.py
│   │   └── status.py
│   ├── persistence/
│   ├── permissions/
│   └── query/
└── integrations/
    ├── mcp/
    ├── hermes/
    └── pi/
```

Python 包目标：

```text
me_system.brain
me_system.who
me_system.shared.ingestion
me_system.integrations.mcp
```

当前 `services/me-graph-core/` 和 `me_graph_core` 为迁移来源，不作为新概念继续扩展。

## 13. Repository 接口

### 13.1 SourceRepository

```python
class SourceRepository(Protocol):
    def register(self, source: SourceRecord) -> SourceRecord: ...
    def get(self, source_id: str) -> SourceRecord: ...
    def add_fragments(
        self,
        source_id: str,
        fragments: tuple[EvidenceFragment, ...],
    ) -> tuple[EvidenceFragment, ...]: ...
    def list_fragments(
        self,
        source_id: str,
    ) -> tuple[EvidenceFragment, ...]: ...
    def create_run(self, run: IngestionRun) -> IngestionRun: ...
    def complete_run(self, run_id: str, result: IngestionResult) -> IngestionRun: ...
```

### 13.2 CandidateRepository

```python
class CandidateRepository(Protocol):
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
    ) -> tuple[CandidateGraphChangeRecord, ...]: ...
```

### 13.3 ReviewService

```python
class ReviewService:
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

MCP、CLI 和未来 Web 只调用这些服务，不各自实现业务逻辑。

## 14. 原子批准

批准必须在同一个 SQLAlchemy Session 事务中完成：

```text
BEGIN
→ SELECT candidate FOR UPDATE
→ status 必须为 pending
→ CandidateGraphChange.materialize()
→ 合并 Candidate EvidenceRef
→ 校验 target_graph 与 namespace
→ 写 graph_objects
→ 写 graph_evidence_refs
→ 更新 Candidate = approved
→ 写 CandidateReviewEvent
COMMIT
```

任一步失败全部回滚。

不允许：

- 图谱对象存在但 Candidate 仍为 pending；
- Candidate approved 但图谱对象不存在；
- 图谱对象存在但证据缺失；
- ReviewEvent 写入失败但事务已提交。

## 15. PostgreSQL 数据模型

继续使用同一个 PostgreSQL：

```text
graph_objects
graph_evidence_refs
source_records
evidence_fragments
ingestion_runs
candidate_graph_changes
candidate_evidence_refs
candidate_review_events
```

不新增第二个权威数据库。

新增 Alembic：

```text
0002_create_shared_ingestion_and_candidates.py
```

## 16. CLI 与 MCP

本切片先提供 CLI 管理入口：

```text
me-system source register
me-system source show
me-system ingestion status
me-system candidate list
me-system candidate show
me-system candidate approve
me-system candidate reject
```

当前 Hermes MCP 继续只暴露 `brain_*` 和 `who_*` 只读工具。

在审核、权限和审计稳定前，不向 Agent 开放 Candidate 写入或批准工具。

后续只读状态工具仍归属对应图谱或系统运维，不形成第三产品：

```text
brain_get_ingestion_status
who_get_ingestion_status
```

## 17. 错误类型

新增：

```text
SourceConflictError
EvidenceConflictError
IngestionStateError
CandidateConflictError
CandidateStateError
ReviewTransactionError
```

错误不得包含：

- 数据库密码；
- 完整连接 URL；
- 未授权项目或用户列表；
- 原始 traceback；
- 未授权证据正文。

## 18. 测试策略

### 18.1 契约测试

覆盖：

- SourceRecord 校验；
- EvidenceFragment 与 SourceAnchor；
- IngestionRun 状态和计数；
- coverage_ratio；
- CandidateGraphChangeRecord 往返；
- ReviewEvent 追加语义。

### 18.2 幂等测试

覆盖：

- 相同 Source 重试返回已有记录；
- Source 内容变化产生冲突；
- 相同 Candidate 重试返回已有记录；
- Candidate payload 变化产生冲突；
- 已审核 Candidate 不会回到 pending。

### 18.3 事务测试

故意制造：

- 图谱对象重复；
- 缺失边端点；
- 非法跨图关系；
- EvidenceRef 失败；
- ReviewEvent 失败。

断言所有状态回滚。

### 18.4 PostgreSQL E2E

```text
登记 Source
→ 写 EvidenceFragment
→ 建立 IngestionRun
→ 提交 ME-Brain Candidate
→ 重建 Repository
→ Candidate 仍为 pending
→ approve
→ 查询权威 GraphNode
→ 查询 EvidenceRef 和原始 Fragment
→ 验证 ReviewEvent
```

再对 ME-Who Candidate 执行同样流程，并验证 namespace 隔离。

## 19. 验收标准

- 产品文档中只有 ME-Brain 和 ME-Who；
- shared 输入设施不被描述为第三产品；
- Source、Fragment、Run、Candidate 可跨重启保存；
- Source 和 Candidate 重试幂等；
- Candidate 批准与图谱写入原子；
- 权威对象可回溯 EvidenceFragment；
- IngestionRun 明确 coverage 和 quality；
- Adapter 无法直接写权威图谱；
- PostgreSQL 16 E2E 通过；
- Python 3.11 / 3.12 测试通过；
- 当前 Hermes MCP 行为不回归。

## 20. 实施顺序

```text
1. 迁移命名与目录：me-graph-core → shared implementation
2. SourceRecord / EvidenceFragment / IngestionRun 契约
3. Alembic 0002
4. SourceRepository
5. Persistent CandidateRepository
6. 原子 ReviewService
7. CLI parity
8. PostgreSQL E2E
9. Agent Conversation Adapter
10. Markdown Adapter
11. Git Adapter
12. status / coverage 查询
```

## 21. 最终边界

```text
产品图谱：ME-Brain、ME-Who
共享输入：Source、Evidence、IngestionRun、Candidate
权威存储：一个 PostgreSQL
访问方式：brain_* / who_* MCP + CLI
Agent 职责：理解任务、选择查询、解释结果
```
