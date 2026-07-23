# Unified ME-System Package Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove `me-core` / `me-graph-core` as visible third-core concepts and reorganize the repository around one `ME-System` Python package with two graph domains: `ME-Brain` and `ME-Who`.

**Architecture:** Preserve the existing graph contracts, PostgreSQL storage, query semantics, Hermes MCP tools, migrations, examples, and tests. Move the Python distribution to the repository root as `me_system`; organize shared mechanisms under internal modules, while `brain` and `who` remain the only graph domains. Follow Codebase-Memory’s operating pattern: index domain sources into a persistent graph, expose typed MCP queries, and drill down to evidence only when required.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0, Alembic, psycopg 3, MCP Python SDK v1, pytest, PostgreSQL 16, GitHub Actions.

## Global Constraints

- The product has one system name: `ME-System`.
- The only canonical graph domains are `ME-Brain` and `ME-Who`; `Bridge` is a relation namespace, not a product.
- Do not introduce names ending in `Core` for product-facing modules or services.
- Keep current database table names and graph namespace values unchanged.
- Preserve the six Hermes read-only MCP tool names.
- Make `me-system` and `me-system-mcp` canonical; keep `me-graph` aliases temporarily for compatibility.
- No Source/Candidate production implementation is added in this refactor.
- Installation, tests, migrations, CI, and documentation must work from the repository root.

---

### Task 1: Establish root package identity

**Files:**
- Create: `pyproject.toml`
- Create: `src/me_system/`
- Create: `tests/test_package_identity.py`

- [ ] Move the distribution metadata to the repository root.
- [ ] Rename the Python package from `me_core` to `me_system`.
- [ ] Add package identity tests that reject active third-core paths.

### Task 2: Organize the two graph domains

**Files:**
- Create: `src/me_system/brain/__init__.py`
- Create: `src/me_system/who/__init__.py`
- Create: `src/me_system/bridge/__init__.py`
- Move: `src/me_system/hermes/` → `src/me_system/adapters/hermes/`

- [ ] Keep shared graph contracts and query services internal to `me_system`.
- [ ] Mark Brain and Who as the only graph domains.
- [ ] Keep Bridge as a relation namespace only.

### Task 3: Move runtime support files to root conventions

**Files:**
- Move: `services/me-core/tests/` → `tests/`
- Move: `services/me-core/schemas/` → `schemas/`
- Move: `services/me-core/migrations/` → `migrations/`
- Move: `services/me-core/alembic.ini` → `alembic.ini`
- Move: `services/me-core/README.md` → `docs/implementation.md`

- [ ] Update test imports and fixture-relative paths.
- [ ] Update Alembic imports and path resolution.
- [ ] Remove `services/me-core/` after all files are moved.

### Task 4: Align CI and commands

**Files:**
- Replace: `.github/workflows/me-core.yml` → `.github/workflows/me-system.yml`
- Modify: `pyproject.toml`

- [ ] Run installation and tests from the repository root on Python 3.11 and 3.12.
- [ ] Run PostgreSQL 16 GraphStore and stdio MCP E2E from the root.
- [ ] Verify `me-system`, `me-system-mcp`, and temporary compatibility aliases.

### Task 5: Rewrite active documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/00-product-and-architecture-overview.md`
- Modify: `docs/roadmap/recommended-development-path.md`
- Modify: `integrations/hermes/README.md`
- Modify: the shared Source/Evidence/Candidate design.

- [ ] Replace transitional paths and package names.
- [ ] Document the Codebase-Memory-inspired flow: source indexing → persistent Brain/Who graphs → typed MCP → evidence drill-down.
- [ ] Keep Source, Evidence, Candidate, Persistence, Query, and MCP described as internal responsibilities.

### Task 6: Final verification

- [ ] Run the complete suite locally in CI before committing the migration.
- [ ] Re-run final root-level CI after the migration commit.
- [ ] Verify the real stdio MCP ClientSession still lists exactly six read-only tools.
- [ ] Verify `services/me-core`, `services/me-graph-core`, `src/me_core`, and active `ME-Core` product language are absent.
- [ ] Squash merge and remove temporary migration workflows from `main`.
