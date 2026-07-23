# ME-System Shared Ingestion Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven development. Every production change follows RED → GREEN → REFACTOR.

**Goal:** Add durable Source, Evidence, IngestionRun, Candidate, and ReviewEvent support inside the single `me_system` package so ME-Brain and ME-Who can grow safely from adapters.

**Architecture:** `me_system.evidence` owns immutable source/evidence contracts; `me_system.ingestion` owns run/candidate/review contracts and repository protocols; `me_system.persistence` implements all repositories in the existing PostgreSQL database. Candidate approval writes the canonical graph object, candidate state, evidence, and audit event in one SQLAlchemy transaction. ME-Brain and ME-Who remain the only graph domains; Hermes MCP stays read-only.

**Tech Stack:** Python 3.11+, dataclasses, SQLAlchemy 2.0, Alembic, psycopg 3, PostgreSQL 16, SQLite behavioral tests, pytest.

## Global Constraints

- No new product, service, database, or `Core` name.
- Runtime code lives under `src/me_system/`.
- `me_brain`, `me_who`, and `bridge` namespace values stay unchanged.
- Existing `graph_objects` and `graph_evidence_refs` tables stay compatible.
- Candidate v0.1 supports only `add_node` and `add_edge`.
- Adapters cannot write canonical graph tables directly.
- Hermes MCP remains exactly six read-only tools.
- All identifiers, source anchors, timestamps, hashes, status transitions, and counts are validated before persistence.
- Errors never expose credentials, raw private content, or tracebacks.

---

### Task 1: Add source and ingestion domain contracts

**Files:**
- Create: `src/me_system/evidence/__init__.py`
- Create: `src/me_system/evidence/contracts.py`
- Create: `src/me_system/ingestion/__init__.py`
- Create: `src/me_system/ingestion/contracts.py`
- Modify: `src/me_system/errors.py`
- Test: `tests/test_ingestion_contracts.py`

**Interfaces:**
- `SourceRecord.from_dict()/to_dict()/fingerprint()`
- `EvidenceFragment.from_dict()/to_dict()`
- `IngestionRun.from_dict()/to_dict()/start()/finish()`
- `CandidateGraphChangeRecord.from_change()/to_dict()`
- `CandidateReviewEvent.to_dict()`
- enums: `IngestionStatus`, `ReviewEventType`, `ActorKind`

- [ ] Write failing tests for required text, timezone-aware timestamps, SHA-256 format, sensitivity, source anchors, fragment ordering fields, run count invariants, coverage ratio, legal transitions, candidate fingerprint stability, and review event validation.
- [ ] Run `pytest -q tests/test_ingestion_contracts.py` and verify RED.
- [ ] Implement minimal immutable dataclasses and enums using the existing graph contract validation style.
- [ ] Run focused tests and the complete non-PostgreSQL suite.

### Task 2: Add ORM models and Alembic migration 0002

**Files:**
- Create: `src/me_system/persistence/ingestion_models.py`
- Modify: `src/me_system/persistence/models.py`
- Create: `migrations/versions/0002_create_ingestion_persistence.py`
- Test: `tests/test_ingestion_migration.py`

**Tables:**
- `source_records`
- `evidence_fragments`
- `ingestion_runs`
- `candidate_graph_changes`
- `candidate_evidence_refs`
- `candidate_review_events`

- [ ] Write failing migration tests for table creation, constraints, indexes, idempotent upgrade, and metadata parity.
- [ ] Run focused tests and verify RED.
- [ ] Implement ORM models and migration with PostgreSQL JSONB / SQLite JSON variants.
- [ ] Import ingestion models during Alembic metadata loading.
- [ ] Run migration tests and existing migration regression tests.

### Task 3: Implement SourceRepository

**Files:**
- Create: `src/me_system/evidence/repository.py`
- Create: `src/me_system/persistence/source_repository.py`
- Test: `tests/test_source_repository.py`

**Interfaces:**
```python
class SourceRepository(Protocol):
    def register(self, source: SourceRecord) -> SourceRecord: ...
    def get(self, source_id: str) -> SourceRecord: ...
    def add_fragments(self, source_id: str, fragments: tuple[EvidenceFragment, ...]) -> tuple[EvidenceFragment, ...]: ...
    def list_fragments(self, source_id: str) -> tuple[EvidenceFragment, ...]: ...
    def create_run(self, run: IngestionRun) -> IngestionRun: ...
    def get_run(self, run_id: str) -> IngestionRun: ...
    def start_run(self, run_id: str) -> IngestionRun: ...
    def finish_run(self, run_id: str, result: IngestionRun) -> IngestionRun: ...
```

- [ ] Write failing SQLite tests for source idempotency, source conflict, source lookup, fragment idempotency, fragment conflicts, stable ordering, missing source, run persistence, legal transitions, and file-database restart.
- [ ] Implement SQLAlchemy repository with short transactions and deterministic ordering.
- [ ] Map database failures to source/ingestion errors without leaking URLs or content.
- [ ] Run focused and full tests.

### Task 4: Implement durable CandidateRepository

**Files:**
- Create: `src/me_system/ingestion/repository.py`
- Create: `src/me_system/persistence/candidate_repository.py`
- Test: `tests/test_candidate_repository.py`

**Interfaces:**
```python
class CandidateRepository(Protocol):
    def submit(self, record: CandidateGraphChangeRecord) -> CandidateGraphChangeRecord: ...
    def get(self, change_id: str) -> CandidateGraphChangeRecord: ...
    def list_pending(self, *, target_graph: GraphNamespace | None = None, source_id: str | None = None, limit: int = 100) -> tuple[CandidateGraphChangeRecord, ...]: ...
    def list_events(self, change_id: str) -> tuple[CandidateReviewEvent, ...]: ...
```

- [ ] Write failing tests for submit, restart recovery, duplicate idempotent submit, payload conflict, pending filters, evidence order, terminal candidates staying terminal, and submitted audit event.
- [ ] Implement repository using candidate/evidence/event tables.
- [ ] Ensure `source_id` filtering uses candidate evidence, not untrusted payload text.
- [ ] Run focused and full tests.

### Task 5: Extract a session-level graph writer and implement atomic review

**Files:**
- Create: `src/me_system/persistence/graph_writer.py`
- Modify: `src/me_system/persistence/store.py`
- Create: `src/me_system/ingestion/review.py`
- Create: `src/me_system/persistence/review_service.py`
- Test: `tests/test_persistent_review.py`

**Interfaces:**
- `write_graph_object(session: Session, value: GraphNode | GraphEdge) -> None`
- `PersistentReviewService.approve(...) -> GraphNode | GraphEdge`
- `PersistentReviewService.reject(...) -> CandidateGraphChangeRecord`

- [ ] Write failing tests for node approval, edge approval, rejection, duplicate review, missing endpoint rollback, namespace rollback, duplicate graph ID rollback, evidence merge, and review event atomicity.
- [ ] Extract existing node/edge/evidence row mapping into `graph_writer.py`; keep `SqlAlchemyGraphStore` behavior unchanged.
- [ ] Implement `SELECT ... FOR UPDATE` review transactions and terminal-state enforcement.
- [ ] Run existing Store tests plus focused review tests.

### Task 6: Add management CLI parity

**Files:**
- Modify: `src/me_system/cli.py`
- Test: `tests/test_ingestion_cli.py`

**Commands:**
```text
me-system source-register --source-json FILE
me-system source-show --source-id ID
me-system ingestion-status --run-id ID
me-system candidate-submit --candidate-json FILE
me-system candidate-list [--target-graph ...] [--source-id ...] [--limit ...]
me-system candidate-show --change-id ID
me-system candidate-approve --change-id ID --reviewer-id ID [--reviewer-kind human] [--reason approved]
me-system candidate-reject --change-id ID --reviewer-id ID --reason TEXT [--reviewer-kind human]
```

- [ ] Write failing CLI tests using a persistent SQLite acceptance database and structured JSON outputs.
- [ ] Implement commands using repositories/services; never duplicate persistence logic in CLI handlers.
- [ ] Verify existing graph CLI commands remain unchanged.

### Task 7: PostgreSQL E2E, documentation, and merge

**Files:**
- Create: `tests/test_ingestion_postgres_e2e.py`
- Modify: `.github/workflows/me-system.yml`
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`
- Modify: `docs/superpowers/specs/2026-07-23-source-ledger-candidate-persistence-design.md`

**E2E:**
```text
register Source
→ append EvidenceFragment
→ create/finish IngestionRun
→ submit ME-Brain node Candidate
→ reconstruct repositories
→ approve Candidate
→ submit/approve edge Candidate
→ query canonical graph and evidence
→ verify immutable review history
→ repeat for ME-Who namespace
```

- [ ] Add PostgreSQL 16 E2E with random schema cleanup.
- [ ] Update CI to run it alongside existing GraphStore and stdio MCP E2E.
- [ ] Replace outdated `shared/` and `services/me-graph-core` paths in the design with `src/me_system/evidence`, `src/me_system/ingestion`, and `src/me_system/persistence`.
- [ ] Run Python 3.11/3.12 unit tests, PostgreSQL E2E, stdio MCP E2E, and `compileall`.
- [ ] Review diff, mark PR ready, squash merge, and verify no open PR remains.
