# ME-Core Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the misleading `me-graph-core` name and make `ME-Core` the sole runtime kernel in code, packaging, commands, documentation, and CI without changing graph behavior.

**Architecture:** Rename the service directory, Python distribution, Python package, and primary CLI/MCP entry points. Preserve one-release compatibility aliases for the two old commands only; do not preserve the old Python import package, because the project is still pre-release and a dual package would look like two cores. All domain semantics remain unchanged.

**Tech Stack:** Python 3.11+, setuptools, pytest, Alembic, PostgreSQL 16, FastMCP v1, GitHub Actions.

## Global Constraints

- `ME-System` is the product/repository.
- `ME-Core` is the only runtime kernel.
- `ME-Brain` and `ME-Who` remain graph namespaces inside ME-Core.
- Target directory: `services/me-core/`.
- Target Python distribution: `me-core`.
- Target Python package: `me_core`.
- Primary CLI: `me-system`.
- Primary MCP command: `me-system-mcp`.
- Compatibility aliases: `me-graph` and `me-graph-mcp` for one minor release.
- Database tables and `ME_GRAPH_*` environment variables do not change in this refactor.
- No graph contract, query result, database migration, or MCP tool-name behavior changes.
- Full Python 3.11 / 3.12 / PostgreSQL / stdio MCP CI must pass.

---

### Task 1: Add rename regression tests before moving files

**Files:**
- Create: `services/me-graph-core/tests/test_me_core_naming.py`
- Modify: `services/me-graph-core/pyproject.toml`

**Interfaces:**
- Produces console scripts `me-system`, `me-system-mcp`, `me-graph`, `me-graph-mcp`.
- Produces import package `me_core` after Task 2.

- [ ] **Step 1: Write a test that requires the new distribution and script names**

```python
from pathlib import Path
import tomllib


def test_distribution_and_primary_commands_use_me_core_names() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "me-core"
    scripts = data["project"]["scripts"]
    assert scripts["me-system"] == "me_core.cli:main"
    assert scripts["me-system-mcp"] == "me_core.mcp.server:main"
    assert scripts["me-graph"] == "me_core.cli:main"
    assert scripts["me-graph-mcp"] == "me_core.mcp.server:main"
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd services/me-graph-core
pytest -q tests/test_me_core_naming.py
```

Expected: FAIL because the distribution and package still use `me-graph-core` / `me_graph_core`.

- [ ] **Step 3: Commit only the failing test**

```bash
git add services/me-graph-core/tests/test_me_core_naming.py
git commit -m "test: define ME-Core naming contract"
```

---

### Task 2: Rename the service directory and Python package

**Files:**
- Rename: `services/me-graph-core/` → `services/me-core/`
- Rename: `services/me-core/src/me_graph_core/` → `services/me-core/src/me_core/`
- Modify: every Python import under `services/me-core/`
- Modify: `services/me-core/pyproject.toml`

**Interfaces:**
- `import me_core`
- `me-system`
- `me-system-mcp`
- compatibility aliases `me-graph`, `me-graph-mcp`

- [ ] **Step 1: Move directories**

```bash
git mv services/me-graph-core services/me-core
git mv services/me-core/src/me_graph_core services/me-core/src/me_core
```

- [ ] **Step 2: Replace Python package references**

```bash
grep -RIl --exclude-dir=.git 'me_graph_core' services/me-core \
  | xargs sed -i 's/me_graph_core/me_core/g'
```

- [ ] **Step 3: Update `pyproject.toml`**

The relevant section must become:

```toml
[project]
name = "me-core"

[project.scripts]
me-system = "me_core.cli:main"
me-system-mcp = "me_core.mcp.server:main"
me-graph = "me_core.cli:main"
me-graph-mcp = "me_core.mcp.server:main"
```

Move the Hermes MCP module from:

```text
src/me_core/hermes/mcp_server.py
```

to:

```text
src/me_core/mcp/server.py
```

and keep Hermes-specific resolver, access, settings, and tool services under:

```text
src/me_core/integrations/hermes/
```

The resulting module imports must be:

```python
from me_core.mcp.server import create_mcp_server
from me_core.integrations.hermes.tools import HermesReadOnlyTools
```

- [ ] **Step 4: Run the focused naming test**

```bash
cd services/me-core
pytest -q tests/test_me_core_naming.py
```

Expected: PASS.

- [ ] **Step 5: Run import and command smoke tests**

```bash
python -c 'import me_core; print(me_core.__name__)'
me-system --help
python -c 'from me_core.mcp.server import TOOL_NAMES; assert len(TOOL_NAMES) == 6'
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename runtime kernel to ME-Core"
```

---

### Task 3: Update Alembic, tests, fixtures, and packaging paths

**Files:**
- Modify: `services/me-core/alembic.ini`
- Modify: `services/me-core/migrations/env.py`
- Modify: all tests under `services/me-core/tests/`
- Modify: `services/me-core/README.md`

**Interfaces:**
- Alembic imports `me_core.persistence.models`.
- Existing database schema remains unchanged.

- [ ] **Step 1: Search for stale identifiers**

```bash
git grep -nE 'me_graph_core|services/me-graph-core|me-graph-core' -- . \
  ':!docs/superpowers/plans/2026-07-23-me-core-rename.md'
```

Expected: only intentional historical references in ADR/review documents.

- [ ] **Step 2: Update migration imports and script paths**

`migrations/env.py` must import:

```python
from me_core.persistence.models import Base
```

`alembic.ini` and migration helpers must resolve paths relative to `services/me-core`.

- [ ] **Step 3: Run migration tests**

```bash
cd services/me-core
pytest -q tests/test_migrations.py tests/test_database_config.py
```

Expected: PASS.

- [ ] **Step 4: Run PostgreSQL-free full tests**

```bash
pytest -q --ignore=tests/test_postgres_integration.py --ignore=tests/test_mcp_stdio.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: align migrations and tests with ME-Core"
```

---

### Task 4: Update repository-level documentation and integration config

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`
- Modify: `integrations/hermes/README.md`
- Modify: `integrations/hermes/config.example.yaml`
- Modify: `integrations/hermes/ME_SYSTEM_BOOTSTRAP.md`
- Modify: `.github/workflows/me-graph-core.yml`
- Rename: `.github/workflows/me-graph-core.yml` → `.github/workflows/me-core.yml`

**Interfaces:**
- Docs point to `services/me-core`.
- Hermes config launches `me-system-mcp`.

- [ ] **Step 1: Rename the CI workflow file and display name**

```bash
git mv .github/workflows/me-graph-core.yml .github/workflows/me-core.yml
```

Workflow display name:

```yaml
name: ME-Core
```

All `working-directory` and cache paths must use `services/me-core`.

- [ ] **Step 2: Update Hermes example**

```yaml
mcp_servers:
  me_system:
    command: "me-system-mcp"
```

Tool names remain unchanged.

- [ ] **Step 3: Update active docs**

Active docs must describe:

```text
ME-System → ME-Core → ME-Brain / ME-Who
```

Historical architecture reviews may mention the old name only when explicitly labelled as an earlier path.

- [ ] **Step 4: Search for stale active references**

```bash
git grep -nE 'services/me-graph-core|me_graph_core|command: "me-graph-mcp"' -- \
  README.md docs integrations .github services/me-core
```

Expected: no results except intentional migration notes in ADR-0005 and the rename plan.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: expose ME-Core as the only runtime kernel"
```

---

### Task 5: Verify behavior parity

**Files:**
- Test only; no production file should change unless a failure identifies a real rename defect.

- [ ] **Step 1: Run complete local tests**

```bash
cd services/me-core
pytest -q
python -m compileall -q src
```

Expected: PostgreSQL-dependent tests either PASS with configured URL or explicitly SKIP; all other tests PASS.

- [ ] **Step 2: Run SQLite persistence acceptance**

```bash
DB='sqlite+pysqlite:////tmp/me-core-rename.db'
me-system db-upgrade --database-url "$DB" --allow-test-database
me-system import-fixture \
  --database-url "$DB" \
  --allow-test-database \
  --fixture ../../examples/graph/lighting-platform.json
me-system project-snapshot \
  --database-url "$DB" \
  --allow-test-database \
  --project-id brain:project:lighting-platform
```

Expected: Radiance is current and Cycles appears only in `excluded.superseded`.

- [ ] **Step 3: Verify old command aliases**

```bash
me-graph --help
me-graph-mcp --help >/dev/null 2>&1 || test $? -eq 0
```

Expected: aliases resolve to the same new modules.

- [ ] **Step 4: Open Draft PR and require CI**

CI must run:

- Python 3.11 unit tests;
- Python 3.12 unit tests;
- PostgreSQL 16 GraphStore integration;
- stdio MCP end-to-end test;
- `compileall`.

- [ ] **Step 5: Squash merge only after all checks pass**

Squash title:

```text
refactor: unify runtime code under ME-Core
```

---

## Self-review checklist

- [ ] No second core or second database introduced.
- [ ] `ME-Brain` and `ME-Who` remain namespaces, not services.
- [ ] Graph and MCP behavior unchanged.
- [ ] Old Python package does not remain as a duplicate implementation.
- [ ] Only command aliases are temporarily retained.
- [ ] Active docs, CI, packaging, imports and directory names agree.
- [ ] Full CI proves behavior parity.