# Unified ME-System Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `services/me-graph-core` / `me_graph_core` implementation name with one root-level `me_system` Python package while preserving all graph, PostgreSQL, Hermes MCP and test behavior.

**Architecture:** Move the existing implementation without changing graph semantics. The repository root becomes the Python project root; `me_system` is the only import package, ME-Brain and ME-Who remain the only graph domains, and Hermes lives under `me_system.adapters.hermes`.

**Tech Stack:** Python 3.11+, setuptools, SQLAlchemy 2.0, Alembic, psycopg 3, MCP Python SDK v1, pytest, PostgreSQL 16.

## Global Constraints

- No product or service named `me-graph-core` remains in active paths or docs.
- No imports from `me_graph_core` remain.
- Only ME-Brain and ME-Who are graph domains.
- Graph contracts, database schema and MCP tool names remain behaviorally compatible.
- CLI scripts become `me-system` and `me-system-mcp`.
- Environment variable names remain unchanged.
- Existing PostgreSQL and MCP E2E tests must pass.
- Do not combine Source Ledger persistence implementation with this migration.

---

### Task 1: Establish architecture and Graphify review

**Files:**
- Create: `docs/adr/ADR-0005-one-system-two-graph-domains.md`
- Create: `docs/competitors/graphify-review.md`
- Create: `docs/superpowers/specs/2026-07-23-unified-me-system-package-design.md`
- Modify: `docs/superpowers/specs/2026-07-23-source-ledger-candidate-persistence-design.md`

**Interfaces:**
- Produces the naming and migration rules used by all later tasks.

- [x] **Step 1: Record one-system/two-domain ADR**
- [x] **Step 2: Review Graphify and define adopt/reject boundaries**
- [x] **Step 3: Write package migration design**
- [ ] **Step 4: Update Source/Candidate design paths from `me_graph_core` to `me_system`**
- [ ] **Step 5: Scan specifications for contradictions and remove third-core language**

---

### Task 2: Move the Python package and console scripts

**Files:**
- Move: `services/me-graph-core/pyproject.toml` → `pyproject.toml`
- Move: `services/me-graph-core/src/me_graph_core/` → `src/me_system/`
- Move: `services/me-graph-core/src/me_graph_core/hermes/` → `src/me_system/adapters/hermes/`
- Modify: all moved Python files

**Interfaces:**
- Produces import package `me_system`.
- Produces console scripts `me-system` and `me-system-mcp`.

- [ ] **Step 1: Copy all existing source files to the new paths without changing behavior**
- [ ] **Step 2: Replace absolute imports `me_graph_core` with `me_system`**
- [ ] **Step 3: Replace relative Hermes package imports for `adapters.hermes`**
- [ ] **Step 4: Update `pyproject.toml` project name and console scripts**

Expected scripts:

```toml
[project.scripts]
me-system = "me_system.cli:main"
me-system-mcp = "me_system.adapters.hermes.mcp_server:main"
```

- [ ] **Step 5: Delete the old source and package paths**

---

### Task 3: Move tests, schemas and migrations

**Files:**
- Move: `services/me-graph-core/tests/` → `tests/`
- Move: `services/me-graph-core/schemas/` → `schemas/`
- Move: `services/me-graph-core/migrations/` → `migrations/`
- Move: `services/me-graph-core/alembic.ini` → `alembic.ini`
- Modify: test imports and path calculations
- Modify: `src/me_system/persistence/migrations.py`

**Interfaces:**
- Existing pytest suite runs from repository root.
- Alembic upgrades the same schema from repository root.

- [ ] **Step 1: Copy tests and replace imports with `me_system`**
- [ ] **Step 2: Update fixture paths from `parents[3]` assumptions to repository-root helpers**
- [ ] **Step 3: Move JSON Schemas and update contract schema test paths**
- [ ] **Step 4: Move Alembic files and update migration root resolution**
- [ ] **Step 5: Delete old tests, schemas and migration paths**

---

### Task 4: Update CI, deployment docs and Hermes configuration

**Files:**
- Modify: `.github/workflows/me-graph-core.yml`
- Rename or replace: `.github/workflows/me-graph-core.yml` → `.github/workflows/me-system.yml`
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`
- Modify: `integrations/hermes/README.md`
- Modify: `integrations/hermes/config.example.yaml`
- Modify: `services/me-graph-core/README.md` content into root documentation, then delete old file

**Interfaces:**
- CI installs from repository root.
- Hermes launches `me-system-mcp`.

- [ ] **Step 1: Update workflow path filters and remove service working directory**
- [ ] **Step 2: Update install, CLI and MCP commands in documentation**
- [ ] **Step 3: Update active architecture status and roadmap**
- [ ] **Step 4: Add Graphify review to competitor navigation/adoption matrix**
- [ ] **Step 5: Delete the remaining `services/me-graph-core` directory files**

---

### Task 5: Verify and integrate

**Files:**
- No new production files; fixes may touch any moved path.

**Interfaces:**
- Final package and all behavior are verified on CI.

- [ ] **Step 1: Trigger Python 3.11 and 3.12 unit suites**
- [ ] **Step 2: Trigger PostgreSQL 16 GraphStore integration**
- [ ] **Step 3: Trigger real stdio MCP Client E2E**
- [ ] **Step 4: Check changed paths for `services/me-graph-core`, `me_graph_core`, `me-graph-mcp` and `me-graph`**
- [ ] **Step 5: Review PR diff for accidental schema or behavior changes**
- [ ] **Step 6: Mark PR ready, squash merge, and verify no open migration PR remains**

## Expected verification commands

```bash
python -m pip install -q -e '.[dev]'
pytest -q
python -m compileall -q src
```

PostgreSQL CI additionally runs:

```bash
pytest -q tests/test_postgres_integration.py
pytest -q tests/test_mcp_stdio.py
```

## Follow-up plan

After this PR is merged, resume the already-reviewed Source / Evidence / Candidate persistence design under:

```text
src/me_system/evidence/
src/me_system/ingestion/
src/me_system/persistence/
```

Then add Graphify-inspired capabilities in separate, testable slices:

1. derivation labels;
2. incremental source manifest;
3. path/explain MCP tools;
4. Graph report and benchmark harness.