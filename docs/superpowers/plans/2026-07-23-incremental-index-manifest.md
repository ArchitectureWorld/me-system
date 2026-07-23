# Incremental Index Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent, rebuildable index manifest that lets ME-Brain and ME-Who adapters deterministically skip unchanged sources or explain why a source must be reindexed.

**Architecture:** Add `IndexManifest`, `IndexPlan`, and `IndexAction` to the internal ingestion module. Persist one current manifest per `(source_locator, adapter_name)` in the existing PostgreSQL database. Preserve both latest attempt and last successful state so failed or partial reindexing never destroys a known-good index state.

**Tech Stack:** Python 3.11+, dataclasses, SQLAlchemy 2.0, Alembic, psycopg 3, pytest, PostgreSQL 16.

## Global Constraints

- ME-Brain and ME-Who remain the only graph domains.
- Manifest is a rebuildable projection, not a new authoritative layer.
- No new database, service, MCP tool, or product name.
- Source locator is deterministic and does not include source text.
- Only final ingestion results (`completed`, `partial`, `failed`) update a manifest.
- Failed/partial attempts update latest state but never overwrite last successful state.
- Candidate IDs are deduplicated and stable-sorted.
- Existing graph, ingestion, candidate, review, CLI, and MCP behavior must not regress.

---

### Task 1: Add manifest contracts and decision rules

**Files:**
- Create: `src/me_system/ingestion/manifest.py`
- Modify: `src/me_system/ingestion/__init__.py`
- Modify: `src/me_system/errors.py`
- Test: `tests/test_index_manifest_contracts.py`

**Interfaces:**
- `source_locator(source: SourceRecord) -> str`
- `manifest_id(source_locator: str, adapter_name: str) -> str`
- `IndexAction`
- `IndexPlan.to_dict()`
- `IndexManifest.to_dict()` / `from_dict()`
- `IndexManifest.evaluate(...) -> IndexPlan`
- `IndexManifest.record_result(...) -> IndexManifest`

- [ ] **Step 1: Write failing tests for locator, ID, actions, stable candidate IDs, and state validation**
- [ ] **Step 2: Run focused tests and verify RED**
- [ ] **Step 3: Implement immutable contracts and deterministic rules**
- [ ] **Step 4: Run focused and full unit tests**

---

### Task 2: Add PostgreSQL model and Alembic 0003

**Files:**
- Modify: `src/me_system/persistence/models.py`
- Create: `migrations/versions/0003_create_index_manifest.py`
- Test: `tests/test_index_manifest_models.py`
- Test: `tests/test_index_manifest_migration.py`

**Interfaces:**
- Produces `index_manifests` table.

- [ ] **Step 1: Write failing metadata and migration tests**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Add ORM row, constraints, indexes, and migration**
- [ ] **Step 4: Verify metadata parity and migration idempotency**

---

### Task 3: Implement manifest repository

**Files:**
- Create: `src/me_system/ingestion/manifest_repository.py`
- Create: `src/me_system/persistence/manifest_repository.py`
- Test: `tests/test_index_manifest_repository.py`

**Interfaces:**

```python
class IndexManifestRepository(Protocol):
    def evaluate(self, source: SourceRecord, *, adapter_name: str, adapter_version: str, extraction_version: str) -> IndexPlan: ...
    def record_result(self, source: SourceRecord, run: IngestionRun, *, extraction_version: str, candidate_ids: tuple[str, ...]) -> IndexManifest: ...
    def get(self, source_locator: str, adapter_name: str) -> IndexManifest: ...
```

- [ ] **Step 1: Write failing repository and restart tests**
- [ ] **Step 2: Verify RED**
- [ ] **Step 3: Implement row locking and transactional upsert**
- [ ] **Step 4: Verify latest vs last-successful behavior**

---

### Task 4: Add CLI and PostgreSQL E2E

**Files:**
- Modify: `src/me_system/cli.py`
- Create: `tests/test_index_manifest_cli.py`
- Create: `tests/test_index_manifest_postgres_e2e.py`
- Modify: `.github/workflows/me-system.yml`

**Interfaces:**

```text
me-system index-plan
me-system manifest-show
```

- [ ] **Step 1: Write failing structured CLI tests**
- [ ] **Step 2: Implement CLI through repository**
- [ ] **Step 3: Add PostgreSQL E2E for completed → skip → content change → failed retry → successful replacement**
- [ ] **Step 4: Include new E2E in CI**

---

### Task 5: Documentation, review, and merge

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`
- Modify: `docs/competitors/graphify-review.md`

- [ ] **Step 1: Document manifest semantics and commands**
- [ ] **Step 2: Confirm no new product/Core wording**
- [ ] **Step 3: Run Python 3.11 / 3.12 / PostgreSQL / MCP CI**
- [ ] **Step 4: Review diff and merge only with all checks green**
