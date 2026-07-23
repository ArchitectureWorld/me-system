# Incremental Index Manifest Design

> 状态：已批准路线下的实施设计  
> 日期：2026-07-23  
> 范围：ME-Brain 与 ME-Who 共用的增量摄取决策，不包含具体 Adapter 抽取规则

## 1. 目标

吸收 Graphify 的增量索引与 Manifest 思路，为 ME-System 增加一个内部的当前索引状态投影，使 Adapter 在处理来源前可以明确回答：

```text
这份来源是否已经用同一 Adapter 和抽取版本处理过？
本次应该跳过、首次索引、因内容变化重建、因版本变化重建，还是重试失败/部分结果？
```

Manifest 只服务于 ME-Brain / ME-Who 图谱构建，不形成第三个产品、数据库或权威事实层。

## 2. 现状问题

系统已经持久化：

- `SourceRecord`；
- `EvidenceFragment`；
- `IngestionRun`；
- Candidate 与 ReviewEvent；
- Canonical ME-Brain / ME-Who。

但 Adapter 仍缺少一个低成本判断层。仅查询历史 `IngestionRun` 会导致每个 Adapter 自己拼装以下逻辑：

- 找出同一逻辑来源的最新版本；
- 比较内容哈希；
- 比较 Adapter 版本；
- 比较抽取规则或模型版本；
- 处理上次 partial / failed；
- 找出上次生成的 Candidate；
- 判断是否安全跳过。

若各 Adapter 独立实现，会造成行为漂移。

## 3. 核心判断

### 3.1 Manifest 是投影，不是新真相

权威历史仍在：

```text
SourceRecord + IngestionRun + Candidate + ReviewEvent
```

`IndexManifest` 只是“这个逻辑来源当前索引到哪里”的可重建投影。

### 3.2 逻辑来源标识

v0.1 使用确定性 `source_locator`：

```text
若 external_system 与 external_id 均存在：
external://<system>/<id>

否则：
content_ref
```

规范化规则：

- Unicode NFKC；
- trim；
- external system casefold；
- `content_ref` 保留语义，不自动解析远程路径；
- 不把内容正文写入 locator。

同一个逻辑来源可以有多个不可变 SourceRecord 版本。

### 3.3 一个 Manifest 对应一条索引管线

唯一键：

```text
(source_locator, adapter_name)
```

Adapter 版本和 extraction version 是当前状态字段，不进入唯一键；版本升级应触发同一 Manifest 的重新索引，而不是创建无法聚合的平行状态。

## 4. 数据对象

### 4.1 `IndexAction`

```text
INDEX_NEW
SKIP_UNCHANGED
REINDEX_CONTENT_CHANGED
REINDEX_ADAPTER_CHANGED
REINDEX_EXTRACTION_CHANGED
RETRY_FAILED
REINDEX_PARTIAL
```

### 4.2 `IndexPlan`

```yaml
action: REINDEX_CONTENT_CHANGED
reason: source content hash changed
source_locator: external://hermes/conversation-001
source_id: source:conversation:001:v2
adapter_name: agent-conversation
adapter_version: 0.2.0
extraction_version: prompt-2026-07-23
previous_manifest_id: manifest:...
previous_successful_run_id: run:...
```

### 4.3 `IndexManifest`

```text
manifest_id
source_locator
adapter_name

latest_source_id
latest_content_sha256
latest_adapter_version
latest_extraction_version
latest_run_id
latest_status
latest_coverage_ratio
latest_candidate_ids
latest_updated_at

last_successful_source_id
last_successful_content_sha256
last_successful_adapter_version
last_successful_extraction_version
last_successful_run_id
last_successful_coverage_ratio
last_successful_candidate_ids
```

为什么同时保留 latest 与 last successful：

- 新版本索引失败时，不能丢失上一个可用索引状态；
- `RETRY_FAILED` 必须知道失败的是哪个版本；
- Agent 查询仍可以使用旧权威图谱，同时系统明确提示图谱可能过期；
- 完成后再推进 last successful。

## 5. 决策规则

按顺序判断：

```text
1. 无 Manifest
   → INDEX_NEW

2. latest 与当前 source / adapter / extraction 完全相同
   且 latest_status = failed
   → RETRY_FAILED

3. latest 与当前版本完全相同
   且 latest_status = partial
   → REINDEX_PARTIAL

4. last_successful_content_sha256 != current source hash
   → REINDEX_CONTENT_CHANGED

5. last_successful_adapter_version != requested adapter version
   → REINDEX_ADAPTER_CHANGED

6. last_successful_extraction_version != requested extraction version
   → REINDEX_EXTRACTION_CHANGED

7. last_successful 与当前完全一致且 status = completed
   → SKIP_UNCHANGED
```

如果从未成功，但 latest 是 completed，则 latest 同时成为 last successful。

如果从未成功且 latest 是 failed / partial，则优先返回 RETRY_FAILED / REINDEX_PARTIAL。

## 6. 记录结果

```python
record_result(
    source: SourceRecord,
    run: IngestionRun,
    extraction_version: str,
    candidate_ids: tuple[str, ...],
) -> IndexManifest
```

约束：

- run.source_id 必须等于 source.source_id；
- run.adapter_name / version 直接来自 IngestionRun；
- 只接受 completed / partial / failed；
- candidate IDs 去重并稳定排序；
- latest 字段始终更新；
- 仅 completed 推进 last successful；
- 数据库更新使用单事务；
- 同一个 Manifest 并发更新使用行锁。

## 7. PostgreSQL 模型

新表：

```text
index_manifests
```

字段：

```text
manifest_id                         text primary key
source_locator                      text not null
adapter_name                        text not null

latest_source_id                    FK source_records
latest_content_sha256               char(64)
latest_adapter_version              text
latest_extraction_version           text
latest_run_id                       FK ingestion_runs
latest_status                       completed | partial | failed
latest_coverage_ratio               float
latest_candidate_ids                jsonb
latest_updated_at                   timestamptz

last_successful_source_id            nullable FK source_records
last_successful_content_sha256       nullable char(64)
last_successful_adapter_version      nullable text
last_successful_extraction_version   nullable text
last_successful_run_id               nullable FK ingestion_runs
last_successful_coverage_ratio       nullable float
last_successful_candidate_ids        jsonb

unique(source_locator, adapter_name)
```

Manifest 不直接引用 GraphObject；Candidate 和 Review 历史已经提供从索引输出到权威图谱的路径。

## 8. Repository

```python
class IndexManifestRepository(Protocol):
    def evaluate(
        self,
        source: SourceRecord,
        *,
        adapter_name: str,
        adapter_version: str,
        extraction_version: str,
    ) -> IndexPlan: ...

    def record_result(
        self,
        source: SourceRecord,
        run: IngestionRun,
        *,
        extraction_version: str,
        candidate_ids: tuple[str, ...],
    ) -> IndexManifest: ...

    def get(
        self,
        source_locator: str,
        adapter_name: str,
    ) -> IndexManifest: ...
```

## 9. CLI

新增内部运维命令：

```text
me-system index-plan
  --source-id ...
  --adapter-name ...
  --adapter-version ...
  --extraction-version ...

me-system manifest-show
  --source-locator ...
  --adapter-name ...
```

这些命令不加入 Hermes MCP。

## 10. 与 Graphify 的对应关系

| Graphify | ME-System |
|---|---|
| 文件 Manifest | 逻辑来源 + Adapter Manifest |
| `--update` | `IndexPlan` 决策 |
| 只处理变化文件 | 只处理内容/版本变化来源 |
| graph output manifest | Candidate IDs + coverage + run history |
| watch / hook | 后续 Adapter 调度器 |

ME-System 额外保留：

- last successful 状态；
- partial / failed；
- Candidate 审核；
- ME-Brain / ME-Who 权限；
- PostgreSQL 事务。

## 11. 非目标

本切片不实现：

- 文件系统 watch；
- Git Hook；
- Agent Conversation Adapter；
- 自动创建 IngestionRun；
- 自动撤销旧 Candidate 或 GraphObject；
- 增量图谱删除语义；
- 定时任务；
- MCP 写入工具；
- Graph Report。

## 12. 测试

### Domain

- locator 规范化；
- deterministic manifest ID；
- 每个 IndexAction；
- candidate IDs 稳定排序；
- completed / partial / failed 约束。

### Repository

- 首次 evaluate；
- completed 后 skip；
- 内容变化；
- Adapter 变化；
- extraction 变化；
- failed retry；
- partial reindex；
- failed 不覆盖 last successful；
- Repository 重建后状态一致；
- 并发更新至少通过 PostgreSQL 行锁 E2E 覆盖。

### Regression

- Source / Candidate / Review 不回归；
- Hermes 仍为六个只读工具；
- Python 3.11 / 3.12；
- PostgreSQL 16；
- stdio MCP E2E。

## 13. 验收标准

- 未变化来源得到 `SKIP_UNCHANGED`；
- 内容、Adapter、extraction 变化分别得到明确原因；
- failed / partial 可以安全重试；
- failed 不破坏 last successful；
- Manifest 可由历史重建，不成为第三个权威层；
- 不新增产品、数据库或 MCP 工具；
- 完整 CI 通过。