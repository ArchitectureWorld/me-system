# Unified ME-System Package Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `me-graph-core` as a visible third-core concept and reorganize the repository around one `ME-System` package with two graph domains: `ME-Brain` and `ME-Who`.

**Architecture:** Preserve all existing graph contracts, PostgreSQL storage, query semantics, Hermes MCP tools, migrations, examples, and tests. Move the Python distribution to the repository root as `me_system`; organize shared mechanisms under neutral internal modules, while `brain` and `who` remain the only graph domains. Follow Codebase-Memory’s operating pattern: index domain sources into a persistent graph, expose typed MCP queries, and drill down to evidence only when required.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0, Alembic, psycopg 3, MCP Python SDK v1, pytest, PostgreSQL 16, GitHub Actions.

## Global Constraints

- The product has one system name: `ME-System`.
- The only canonical graph domains are `ME-Brain` and `ME-Who`; `Bridge` is a relation namespace, not a product.
- Do not introduce names ending in `Core` for product-facing modules or services.
- Keep current database table names and graph namespace values unchanged in this refactor.
- Preserve the six Hermes read-only MCP tool names.
- Preserve existing CLI behavior through temporary deprecated aliases while making `me-system` and `me-system-mcp` canonical.
- No Source/Candidate production implementation is added in this refactor.
- All imports, tests, migrations, CI, Compose instructions, and documentation must work from the repository root.

---

### Task 1: Establish root package and compatibility tests

**Files:**
- Create: `pyproject.toml`
- Create: `src/me_system/__init__.py`
- Create: `src/me_system/__main__.py`
- Create: `tests/test_package_identity.py`
- Move later: existing `me_graph_core` modules into `src/me_system/`

**Interfaces:**
- Canonical import: `import me_system`
- Canonical CLI: `me-system`
- Canonical MCP CLI: `me-system-mcp`
- Transitional aliases: `me-graph`, `me-graph-mcp`

- [ ] Write a failing package identity test that imports `me_system`, rejects product text containing `ME-Graph Core`, and checks all four console-script declarations.
- [ ] Add the root `pyproject.toml` with distribution name `me-system`, package directory `src`, existing dependencies, canonical scripts, and transitional aliases.
- [ ] Add root package entrypoints and run focused tests.

### Task 2: Move implementation into `src/me_system`

**Files:**
- Move: `services/me-graph-core/src/me_graph_core/*.py` → `src/me_system/*.py`
- Move: `services/me-graph-core/src/me_graph_core/persistence/` → `src/me_system/persistence/`
- Move: `services/me-graph-core/src/me_graph_core/hermes/` → `src/me_system/adapters/hermes/`
- Create: `src/me_system/brain/__init__.py`
- Create: `src/me_system/who/__init__.py`
- Create: `src/me_system/bridge/__init__.py`

**Interfaces:**
- Shared graph contracts remain available from `me_system`.
- Hermes adapter imports become `me_system.adapters.hermes`.
- Graph namespace values remain `me_brain`, `me_who`, and `bridge`.

- [ ] Copy files to the new package and update internal imports.
- [ ] Add domain marker modules documenting that Brain and Who are the only graph domains.
- [ ] Run import and graph contract tests.

### Task 3: Move tests, schemas, migrations, and examples to root conventions

**Files:**
- Move: `services/me-graph-core/tests/` → `tests/`
- Move: `services/me-graph-core/schemas/` → `schemas/`
- Move: `services/me-graph-core/migrations/` → `migrations/`
- Move: `services/me-graph-core/alembic.ini` → `alembic.ini`
- Modify all test imports and fixture-relative paths.

- [ ] Update test imports from `me_graph_core` to `me_system`.
- [ ] Update migration script path resolution and Alembic configuration.
- [ ] Run all unit, migration, SQLite, PostgreSQL, and MCP tests.

### Task 4: Align CI and deployment paths

**Files:**
- Rename: `.github/workflows/me-graph-core.yml` → `.github/workflows/me-system.yml`
- Modify: workflow working directories and cache dependency path.
- Preserve: `deploy/postgres/`

- [ ] Run installation and tests from repository root on Python 3.11 and 3.12.
- [ ] Run PostgreSQL 16 GraphStore and stdio MCP E2E from repository root.
- [ ] Compile `src`.

### Task 5: Rewrite documentation and Hermes configuration

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/00-product-and-architecture-overview.md`
- Modify: `docs/roadmap/recommended-development-path.md`
- Modify: `integrations/hermes/README.md`
- Modify: `integrations/hermes/config.example.yaml`
- Modify: relevant specs and ADR references.

- [ ] Replace `ME-Graph Core` product wording with `ME-System implementation`.
- [ ] Replace old paths and commands with root package paths and canonical commands.
- [ ] Explicitly document Codebase-Memory-inspired flow: source indexing → persistent Brain/Who graph → typed MCP → evidence drill-down.
- [ ] Keep Source, Evidence, Candidate, Persistence, Query, and MCP described as internal responsibilities, not products or cores.

### Task 6: Correct Source/Candidate design and clean legacy tree

**Files:**
- Revise and move the PR #5 design into the unified package terminology.
- Delete the full `services/me-graph-core/` tree after all copies are verified.
- Delete the old workflow path.

- [ ] Rewrite proposed paths from `services/me-graph-core/src/me_graph_core/...` to `src/me_system/...`.
- [ ] Rename repository/service concepts to internal `evidence`, `ingestion`, `review`, and `persistence` modules.
- [ ] Verify no active file contains `me-graph-core`, `me_graph_core`, or `ME-Graph Core`, except the migration note documenting the rename.

### Task 7: Final verification and integration

- [ ] Run complete GitHub Actions on Python 3.11, Python 3.12, and PostgreSQL 16.
- [ ] Verify the real stdio MCP ClientSession lists exactly six read-only tools and calls resolve, snapshot, and task profile successfully.
- [ ] Verify root install and both canonical commands.
- [ ] Open a draft PR, review changed files and security boundaries, mark ready, squash merge, close superseded PR #5, and verify no open PR remains.
