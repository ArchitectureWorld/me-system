# Source, Evidence, and Candidate Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the persistent input and governance path shared by ME-Brain and ME-Who: immutable sources, addressable evidence fragments, ingestion status, idempotent candidate changes, append-only review events, and atomic candidate approval into the canonical graph.

**Architecture:** Add `me_system.evidence` and `me_system.ingestion` as internal modules of the single ME-System package. Persist all new records in the existing PostgreSQL database through SQLAlchemy and Alembic. Approval uses one database transaction that locks a pending candidate, materializes the existing `CandidateGraphChange`, writes the canonical graph object and evidence, updates candidate state, and appends a review event.

**Tech Stack:** Python 3.11+, dataclasses, SQLAlchemy 2.0, Alembic, psycopg 3, pytest, PostgreSQL 16.

## Global Constraints

- ME-Brain and ME-Who remain the only authoritative graph domains.
- No Source Ledger product, Candidate service, second database, or new Core identity.
- Adapters may register source/evidence and submit candidates, but cannot write canonical graph objects.
- Candidate v0.1 supports only `add_node` and `add_edge`.
- Source and candidate retries are idempotent; conflicting payloads raise explicit errors.
- Review events are append-only.
- Candidate approval and canonical graph write are one transaction.
- Existing six Hermes MCP tools remain read-only and unchanged.
- Error messages must not expose database credentials, private source text, or tracebacks.

---

### Task 1: Add evidence and ingestion domain contracts

**Files:**
- Create: `src/me_system/evidence/__init__.py`
- Create: `src/me_system/evidence/contracts.py`
- Create: `src/me_system/ingestion/__init__.py`
- Create: `src/me_system/ingestion/contracts.py`
- Modify: `src/me_system/errors.py`
- Test: `tests/test_evidence_contracts.py`
- Test: `tests/test_ingestion_contracts.py`

**Interfaces:**
- Produces `SourceRecord`, `EvidenceFragment`, `IngestionRun`, `IngestionResult`, `IngestionStatus`, `CandidateRecord`, `ReviewEvent`, and `ReviewEventType`.
- `CandidateRecord.change` is the existing `CandidateGraphChange` domain object.

- [ ] **Step 1: Write failing contract tests**

Tests must cover:

```python
SourceRecord.from_dict(data).to_dict() == normalized_data
EvidenceFragment requires a structured source_anchor
IngestionRun rejects impossible counts and invalid state/time combinations
CandidateRecord validates payload hash, idempotency key and timestamps
ReviewEvent validates actor and event type
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
pytest -q tests/test_evidence_contracts.py tests/test_ingestion_contracts.py
```

Expected: import errors for missing `me_system.evidence` and `me_system.ingestion`.

- [ ] **Step 3: Implement immutable dataclass contracts**

Use timezone-aware UTC datetimes and deterministic `to_dict()` / `from_dict()` methods. Reuse `Sensitivity`, `GraphNamespace`, `ReviewStatus`, and `CandidateGraphChange`.

- [ ] **Step 4: Add explicit errors**

```python
class SourceConflictError(GraphCoreError): ...
class SourceNotFoundError(GraphCoreError, KeyError): ...
class EvidenceConflictError(GraphCoreError): ...
class IngestionStateError(GraphCoreError, ValueError): ...
class CandidateConflictError(GraphCoreError): ...
class CandidateNotFoundError(GraphCoreError, KeyError): ...
class CandidateStateError(GraphCoreError, ValueError): ...
class ReviewTransactionError(GraphCoreError): ...
```

- [ ] **Step 5: Run focused and complete unit tests**

```bash
pytest -q tests/test_evidence_contracts.py tests/test_ingestion_contracts.py
pytest -q --ignore=tests/test_mcp_stdio.py --ignore=tests/compat/runtime/test_postgres_integration.py
```

---

### Task 2: Add PostgreSQL records and Alembic migration

**Files:**
- Modify: `src/me_system/persistence/models.py`
- Create: `migrations/versions/0002_create_ingestion_records.py`
- Test: `tests/test_ingestion_migration.py`
- Test: `tests/test_ingestion_models.py`

**Interfaces:**
- Produces ORM records for `source_records`, `evidence_fragments`, `ingestion_runs`, `candidate_graph_changes`, `candidate_evidence_refs`, and `candidate_review_events`.

- [ ] **Step 1: Write failing schema tests**

Verify table names, foreign keys, unique constraints, status checks, coverage range, and review event indexes.

- [ ] **Step 2: Run tests and verify RED**

```bash
pytest -q tests/test_ingestion_migration.py tests/test_ingestion_models.py
```

- [ ] **Step 3: Add ORM records and migration 0002**

Required relations:

```text
evidence_fragments.source_id → source_records.source_id
ingestion_runs.source_id → source_records.source_id
candidate_graph_changes.ingestion_run_id → ingestion_runs.run_id
candidate_evidence_refs.change_id → candidate_graph_changes.change_id
candidate_review_events.change_id → candidate_graph_changes.change_id
candidate_graph_changes.approved_object_id → graph_objects.id
```

- [ ] **Step 4: Verify migration idempotency and metadata parity**

```bash
pytest -q tests/test_ingestion_migration.py tests/test_ingestion_models.py tests/compat/runtime/test_migrations.py
```

---

### Task 3: Implement Source and ingestion repositories

**Files:**
- Create: `src/me_system/evidence/repository.py`
- Create: `src/me_system/persistence/source_repository.py`
- Test: `tests/test_source_repository.py`
- Test: `tests/test_ingestion_run_repository.py`

**Interfaces:**

```python
class SourceRepository(Protocol):
    def register(self, source: SourceRecord) -> SourceRecord: ...
    def get(self, source_id: str) -> SourceRecord: ...
    def add_fragments(self, source_id: str, fragments: tuple[EvidenceFragment, ...]) -> tuple[EvidenceFragment, ...]: ...
    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]: ...
    def create_run(self, run: IngestionRun) -> IngestionRun: ...
    def complete_run(self, run_id: str, result: IngestionResult) -> IngestionRun: ...
```

- [ ] **Step 1: Write failing repository behavior tests**

Cover first registration, identical retry, conflicting retry, fragment ordering, fragment conflict, missing source, valid run completion, invalid state transition, and file-backed SQLite restart.

- [ ] **Step 2: Verify RED**

```bash
pytest -q tests/test_source_repository.py tests/test_ingestion_run_repository.py
```

- [ ] **Step 3: Implement SQLAlchemy repository**

Normalize hash and metadata comparison. Do not expose full `content_ref` in conflict errors.

- [ ] **Step 4: Run focused and regression tests**

---

### Task 4: Implement persistent Candidate repository

**Files:**
- Create: `src/me_system/ingestion/repository.py`
- Create: `src/me_system/persistence/candidate_repository.py`
- Test: `tests/test_candidate_repository.py`

**Interfaces:**

```python
class CandidateRepository(Protocol):
    def submit(self, candidate: CandidateRecord) -> CandidateRecord: ...
    def get(self, change_id: str) -> CandidateRecord: ...
    def list_pending(self, *, target_graph: GraphNamespace | None = None, source_id: str | None = None, limit: int = 100) -> tuple[CandidateRecord, ...]: ...
    def list_events(self, change_id: str) -> tuple[ReviewEvent, ...]: ...
```

- [ ] **Step 1: Write failing tests**

Cover submit, cross-restart read, identical retry, payload conflict, evidence order, graph/source filtering, limit validation, and submitted review event.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Implement repository with stable ordering and idempotency**

- [ ] **Step 4: Run focused and regression tests**

---

### Task 5: Implement atomic persistent review

**Files:**
- Create: `src/me_system/persistence/graph_writer.py`
- Refactor: `src/me_system/persistence/store.py`
- Create: `src/me_system/ingestion/review.py`
- Test: `tests/test_persistent_review.py`
- Test: `tests/test_persistent_review_transactions.py`

**Interfaces:**

```python
class PersistentReviewService:
    def approve(self, change_id: str, reviewer_id: str, *, reviewer_kind: str = "human", reason: str = "approved") -> GraphNode | GraphEdge: ...
    def reject(self, change_id: str, reviewer_id: str, reason: str, *, reviewer_kind: str = "human") -> None: ...
```

- [ ] **Step 1: Write failing approval and rollback tests**

Cover node approval, edge approval, rejection, repeated review, duplicate graph ID, missing edge endpoint, illegal namespace, evidence write failure, and review-event write failure.

- [ ] **Step 2: Verify RED**

- [ ] **Step 3: Extract session-level graph writer**

Both `SqlAlchemyGraphStore` and `PersistentReviewService` call the same node/edge writer so namespace and evidence behavior cannot drift.

- [ ] **Step 4: Implement one-transaction approval/rejection**

Use `SELECT ... FOR UPDATE` on PostgreSQL. SQLite behavior tests may use a normal selected row while preserving transaction semantics.

- [ ] **Step 5: Run focused, complete, and PostgreSQL tests**

---

### Task 6: Add structured CLI and end-to-end verification

**Files:**
- Modify: `src/me_system/cli.py`
- Create: `tests/test_ingestion_cli.py`
- Create: `tests/test_ingestion_postgres_e2e.py`
- Modify: `.github/workflows/me-system.yml`
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`

**Interfaces:**

```text
me-system source-register --json <path>
me-system source-show --source-id <id>
me-system candidate-submit --json <path>
me-system candidate-list [--target-graph ...] [--source-id ...]
me-system candidate-approve --change-id ... --reviewer-id ...
me-system candidate-reject --change-id ... --reviewer-id ... --reason ...
```

- [ ] **Step 1: Write failing CLI tests for JSON input/output and safe errors**
- [ ] **Step 2: Implement CLI commands by calling repositories/services**
- [ ] **Step 3: Add PostgreSQL E2E**

```text
register source
→ add evidence fragment
→ create ingestion run
→ submit ME-Brain node candidate
→ recreate repositories
→ approve candidate
→ query canonical node and evidence
→ verify review events
→ repeat for ME-Who
```

- [ ] **Step 4: Verify Hermes remains exactly six read-only tools**
- [ ] **Step 5: Run Python 3.11, Python 3.12, PostgreSQL 16 and stdio MCP CI**
- [ ] **Step 6: Mark PR ready and squash merge only after all checks succeed**
