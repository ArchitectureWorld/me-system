# ME-Core Ingestion Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immutable, idempotent SourceRecord and EvidenceFragment persistence plus observable IngestionRun status inside the single ME-Core.

**Architecture:** Add domain contracts under `me_core.ingestion`, three SQLAlchemy records and Alembic migration `0002`, and one `SqlAlchemyIngestionRepository` used by `SourceLedgerService` and `IngestionStatusService`. The implementation stays inside `services/me-core`, uses the existing PostgreSQL, and does not add MCP tools or a new service.

**Tech Stack:** Python 3.11+, dataclasses, SQLAlchemy 2.0, Alembic, PostgreSQL 16, SQLite behavior tests, pytest.

## Global Constraints

- ME-Core remains the only runtime kernel.
- PostgreSQL remains the only authority database.
- No Candidate persistence in this PR.
- No Adapter or LLM extraction in this PR.
- No new MCP tools in this PR.
- `graph_objects` and existing graph query behavior must not change.
- `graph_evidence_refs` remains backward compatible and does not gain a mandatory source FK yet.
- Source and Fragment content hashes are lowercase 64-character SHA-256 hex.
- All timestamps are timezone-aware and normalized to UTC.
- Source registration and Fragment insertion are idempotent and conflict-safe.
- Ingestion status must expose counts, coverage, quality and partial failure.
- Python 3.11 / 3.12 / PostgreSQL 16 CI must pass.

---

### Task 1: Add ingestion domain contracts

**Files:**
- Create: `services/me-core/src/me_core/ingestion/__init__.py`
- Create: `services/me-core/src/me_core/ingestion/contracts.py`
- Create: `services/me-core/tests/test_ingestion_contracts.py`

**Interfaces:**
- `SourceRecord.from_dict(data) -> SourceRecord`
- `SourceRecord.to_dict() -> dict[str, object]`
- `SourceRecord.identity_digest() -> str`
- `EvidenceFragment.from_dict(data) -> EvidenceFragment`
- `EvidenceFragment.to_dict() -> dict[str, object]`
- `IngestionRun.from_dict(data) -> IngestionRun`
- `IngestionRun.to_dict() -> dict[str, object]`
- `IngestionRun.start(at) -> IngestionRun`
- `IngestionRun.finish(...) -> IngestionRun`

- [ ] **Step 1: Write failing contract tests**

Cover:

```text
SourceRecord UTC round-trip
SourceRecord SHA-256 validation
SourceRecord identity ignores source_id / ingested_at / content_ref
EvidenceFragment SourceAnchor and ordinal validation
EvidenceFragment sensitivity and hash
IngestionRun legal pending → running → completed transition
IngestionRun partial / failed terminal states
negative count rejection
processed + skipped + failed > input rejection
coverage outside 0..1 rejection
terminal status without completed_at rejection
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
cd services/me-core
pytest -q tests/test_ingestion_contracts.py
```

Expected: import error because `me_core.ingestion` does not exist.

- [ ] **Step 3: Implement minimal immutable dataclasses and enums**

Types:

```python
class FragmentType(StrEnum):
    CONVERSATION_MESSAGE = "conversation_message"
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    GIT_COMMIT = "git_commit"
    UNKNOWN = "unknown"

class IngestionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
```

`SourceRecord.identity_digest()` hashes canonical JSON containing every immutable semantic field except `source_id`, `ingested_at` and `content_ref`.

- [ ] **Step 4: Run focused and existing contract tests**

```bash
pytest -q tests/test_ingestion_contracts.py tests/test_contracts.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/me-core/src/me_core/ingestion services/me-core/tests/test_ingestion_contracts.py
git commit -m "feat: add ingestion ledger contracts"
```

---

### Task 2: Add ORM records and Alembic migration

**Files:**
- Modify: `services/me-core/src/me_core/persistence/models.py`
- Create: `services/me-core/migrations/versions/0002_create_ingestion_ledger.py`
- Modify: `services/me-core/tests/test_migrations.py`
- Modify: `services/me-core/tests/test_sqlalchemy_store.py`
- Create: `services/me-core/tests/test_ingestion_schema.py`

**Interfaces:**
- `SourceRecordRow`
- `EvidenceFragmentRow`
- `IngestionRunRow`
- `Base.metadata` contains all six authority tables after migration.

- [ ] **Step 1: Write failing schema and migration tests**

Expected tables:

```text
graph_objects
graph_evidence_refs
source_records
evidence_fragments
ingestion_runs
alembic_version
```

Validate:

```text
source_records.idempotency_key unique
evidence_fragments(source_id, ordinal) unique
evidence_fragments.source_id FK source_records
0 <= coverage_ratio <= 1
non-negative counts
processed + skipped + failed <= input
terminal status requires completed_at
```

- [ ] **Step 2: Run migration tests and verify RED**

```bash
pytest -q tests/test_ingestion_schema.py tests/test_migrations.py
```

Expected: new tables missing.

- [ ] **Step 3: Add ORM rows and migration `0002_ingestion_ledger`**

Use JSON/JSONB variants and timezone-aware DateTime, following existing graph models.

Indexes:

```text
source_records(idempotency_key)
source_records(external_system, external_id)
evidence_fragments(source_id, ordinal)
ingestion_runs(source_id, started_at)
ingestion_runs(status, started_at)
```

- [ ] **Step 4: Run migration and metadata parity tests**

```bash
pytest -q tests/test_ingestion_schema.py tests/test_migrations.py tests/test_sqlalchemy_store.py
```

Expected: PASS and `compare_metadata(...) == []`.

- [ ] **Step 5: Commit**

```bash
git add services/me-core/src/me_core/persistence/models.py services/me-core/migrations/versions/0002_create_ingestion_ledger.py services/me-core/tests
git commit -m "feat: add ingestion ledger database schema"
```

---

### Task 3: Implement SourceLedgerService and persistence

**Files:**
- Create: `services/me-core/src/me_core/ingestion/source.py`
- Create: `services/me-core/src/me_core/persistence/ingestion_repository.py`
- Modify: `services/me-core/src/me_core/errors.py`
- Create: `services/me-core/tests/test_source_ledger.py`

**Interfaces:**
- `SqlAlchemyIngestionRepository(engine)`
- `SourceLedgerService(repository)`
- `SourceLedgerService.register_source(source) -> SourceRecord`
- `SourceLedgerService.get_source(source_id) -> SourceRecord`
- `SourceLedgerService.add_fragments(source_id, fragments) -> tuple[EvidenceFragment, ...]`
- `SourceLedgerService.list_fragments(source_id) -> tuple[EvidenceFragment, ...]`

Errors:

```python
class SourceConflictError(GraphCoreError): ...
class SourceNotFoundError(GraphCoreError, KeyError): ...
class EvidenceConflictError(GraphCoreError): ...
```

- [ ] **Step 1: Write failing repository behavior tests**

Cover:

```text
first source registration
same idempotency key + same identity returns existing row
same idempotency key + changed content raises SourceConflictError
duplicate source_id conflict
source survives repository recreation
add fragments in one transaction
fragment order restored by ordinal
same fragment replay is idempotent
fragment ID or ordinal conflict rolls back whole batch
missing source raises SourceNotFoundError
JSON metadata and sensitivity round-trip
```

- [ ] **Step 2: Verify RED**

```bash
pytest -q tests/test_source_ledger.py
```

Expected: repository/service imports missing.

- [ ] **Step 3: Implement repository mappings and service**

All database rows must reconstruct domain contracts through `from_dict()`.

A source replay compares `identity_digest()`. `content_ref` may change without changing source identity; the original persisted reference remains authoritative.

A fragment replay is idempotent only when its complete serialized identity is unchanged.

- [ ] **Step 4: Run focused, persistence and rollback tests**

```bash
pytest -q tests/test_source_ledger.py tests/test_sqlalchemy_transactions.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/me-core/src/me_core/ingestion/source.py services/me-core/src/me_core/persistence/ingestion_repository.py services/me-core/src/me_core/errors.py services/me-core/tests/test_source_ledger.py
git commit -m "feat: persist sources and evidence fragments"
```

---

### Task 4: Implement IngestionStatusService

**Files:**
- Create: `services/me-core/src/me_core/ingestion/status.py`
- Modify: `services/me-core/src/me_core/persistence/ingestion_repository.py`
- Create: `services/me-core/tests/test_ingestion_status.py`

**Interfaces:**
- `IngestionStatusService(repository)`
- `create_run(run) -> IngestionRun`
- `start_run(run_id, started_at=None) -> IngestionRun`
- `finish_run(run_id, *, status, counts, quality_report, log_ref=None, error_summary=None, completed_at=None) -> IngestionRun`
- `get_run(run_id) -> IngestionRun`
- `list_runs(source_id, limit=100) -> tuple[IngestionRun, ...]`

Errors:

```python
class IngestionRunError(GraphCoreError, ValueError): ...
class IngestionRunNotFoundError(GraphCoreError, KeyError): ...
```

- [ ] **Step 1: Write failing state-machine and persistence tests**

Cover:

```text
create pending run
pending → running
running → completed
running → partial
running → failed
illegal pending → completed without start
terminal run cannot restart or refinish
source must exist
counts / quality / log_ref round-trip
runs ordered newest first
run survives repository recreation
error summary does not contain supplied database password in test input
```

- [ ] **Step 2: Verify RED**

```bash
pytest -q tests/test_ingestion_status.py
```

- [ ] **Step 3: Implement state transitions and repository updates**

Updates use row locking where PostgreSQL supports it and one transaction per transition.

- [ ] **Step 4: Run focused and full PostgreSQL-free suite**

```bash
pytest -q --ignore=tests/test_postgres_integration.py --ignore=tests/test_mcp_stdio.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/me-core/src/me_core/ingestion/status.py services/me-core/src/me_core/persistence/ingestion_repository.py services/me-core/tests/test_ingestion_status.py
git commit -m "feat: persist ingestion status and coverage"
```

---

### Task 5: Add CLI parity and PostgreSQL E2E

**Files:**
- Modify: `services/me-core/src/me_core/cli.py`
- Create: `services/me-core/tests/test_cli_ingestion.py`
- Create: `services/me-core/tests/test_ingestion_postgres.py`
- Modify: `.github/workflows/me-core.yml`
- Modify: `services/me-core/README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`

**Interfaces:**

```text
me-system source-register --input source.json
me-system source-show --source-id ...
me-system fragment-add --source-id ... --input fragments.json
me-system fragment-list --source-id ...
me-system ingestion-create --input run.json
me-system ingestion-start --run-id ...
me-system ingestion-finish --run-id ... --input result.json
me-system ingestion-status --run-id ...
```

- [ ] **Step 1: Write failing CLI tests**

Use SQLite `--allow-test-database` and structured JSON output.

- [ ] **Step 2: Implement CLI commands by calling services**

CLI must not duplicate repository logic.

- [ ] **Step 3: Add PostgreSQL E2E**

```text
migrate random schema
→ register source
→ add fragments
→ create/start/finish ingestion run
→ recreate services
→ read source/fragments/run
→ drop schema
```

- [ ] **Step 4: Run full verification**

```bash
cd services/me-core
pytest -q
python -m compileall -q src
```

CI must run Python 3.11, 3.12 and PostgreSQL 16.

- [ ] **Step 5: Update docs and commit**

```bash
git add -A
git commit -m "feat: expose ME-Core ingestion ledger"
```

---

## Acceptance checklist

- [ ] No new service or database was introduced.
- [ ] Source and Fragment persistence is immutable and idempotent.
- [ ] Ingestion status exposes coverage and partial failure.
- [ ] Existing graph and Hermes MCP tests remain unchanged and passing.
- [ ] Migration matches SQLAlchemy metadata.
- [ ] PostgreSQL E2E proves cross-process persistence.
- [ ] No Candidate persistence or write MCP leaked into this PR.
- [ ] Active documentation says all capabilities live inside ME-Core.