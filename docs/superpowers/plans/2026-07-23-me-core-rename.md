# ME-Core Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the misleading `me-graph-core` name and make `ME-Core` the sole runtime kernel in code, packaging, commands, documentation, and CI without changing graph or MCP behavior.

**Architecture:** Rename the service directory, Python distribution, Python package, and primary CLI/MCP entry points. Keep the current internal `hermes` package structure unchanged in this refactor. Preserve one-release compatibility aliases for the two old commands only; do not preserve a duplicate old Python package.

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
- Existing `me_core.hermes` internal structure remains unchanged.
- Database tables and `ME_GRAPH_*` environment variables do not change.
- MCP tool names do not change.
- Full Python 3.11 / 3.12 / PostgreSQL / stdio MCP CI must pass.

---

### Task 1: Define the naming contract with a failing test

**Files:**
- Create: `services/me-graph-core/tests/test_me_core_naming.py`

- [ ] Write:

```python
from pathlib import Path
import tomllib


def test_distribution_and_commands_use_me_core_names() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "me-core"
    scripts = data["project"]["scripts"]
    assert scripts["me-system"] == "me_core.cli:main"
    assert scripts["me-system-mcp"] == "me_core.hermes.mcp_server:main"
    assert scripts["me-graph"] == "me_core.cli:main"
    assert scripts["me-graph-mcp"] == "me_core.hermes.mcp_server:main"
```

- [ ] Run:

```bash
cd services/me-graph-core
pytest -q tests/test_me_core_naming.py
```

Expected: FAIL because old names are still active.

- [ ] Commit the failing test:

```bash
git add services/me-graph-core/tests/test_me_core_naming.py
git commit -m "test: define ME-Core naming contract"
```

---

### Task 2: Rename directory, distribution, package, and entry points

**Files:**
- Rename: `services/me-graph-core/` → `services/me-core/`
- Rename: `services/me-core/src/me_graph_core/` → `services/me-core/src/me_core/`
- Modify: all Python imports under `services/me-core/`
- Modify: `services/me-core/pyproject.toml`

- [ ] Move directories:

```bash
git mv services/me-graph-core services/me-core
git mv services/me-core/src/me_graph_core services/me-core/src/me_core
```

- [ ] Replace package references:

```bash
grep -RIl --exclude-dir=.git 'me_graph_core' services/me-core \
  | xargs sed -i 's/me_graph_core/me_core/g'
```

- [ ] Set the distribution and scripts:

```toml
[project]
name = "me-core"

[project.scripts]
me-system = "me_core.cli:main"
me-system-mcp = "me_core.hermes.mcp_server:main"
me-graph = "me_core.cli:main"
me-graph-mcp = "me_core.hermes.mcp_server:main"
```

- [ ] Run:

```bash
cd services/me-core
pytest -q tests/test_me_core_naming.py
python -c 'import me_core; print(me_core.__name__)'
python -c 'from me_core.hermes.mcp_server import TOOL_NAMES; assert len(TOOL_NAMES) == 6'
```

Expected: PASS.

- [ ] Commit:

```bash
git add -A
git commit -m "refactor: rename runtime kernel to ME-Core"
```

---

### Task 3: Align migrations, tests, workflow, and active documentation

**Files:**
- Modify: `services/me-core/alembic.ini`
- Modify: `services/me-core/migrations/env.py`
- Modify: all tests under `services/me-core/tests/`
- Rename: `.github/workflows/me-graph-core.yml` → `.github/workflows/me-core.yml`
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`
- Modify: `integrations/hermes/README.md`
- Modify: `integrations/hermes/config.example.yaml`

- [ ] Rename workflow and update paths:

```bash
git mv .github/workflows/me-graph-core.yml .github/workflows/me-core.yml
```

The workflow must use:

```yaml
name: ME-Core
```

and all working/cache paths must use `services/me-core`.

- [ ] Update Hermes command:

```yaml
command: "me-system-mcp"
```

- [ ] Update active docs to describe:

```text
ME-System → ME-Core → ME-Brain / ME-Who
```

- [ ] Search stale active references:

```bash
git grep -nE 'services/me-graph-core|me_graph_core|command: "me-graph-mcp"' -- \
  README.md docs integrations .github services/me-core
```

Expected: only explicitly marked historical/migration references in ADR-0005, the competitor review, and this plan.

- [ ] Run migration and non-PostgreSQL tests:

```bash
cd services/me-core
pytest -q --ignore=tests/test_postgres_integration.py --ignore=tests/test_mcp_stdio.py
python -m compileall -q src
```

Expected: PASS.

- [ ] Commit:

```bash
git add -A
git commit -m "docs: expose ME-Core as the only runtime kernel"
```

---

### Task 4: Verify behavior parity

- [ ] Run complete tests:

```bash
cd services/me-core
pytest -q
python -m compileall -q src
```

- [ ] Run SQLite acceptance:

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

Expected: Radiance current; Cycles only in `excluded.superseded`.

- [ ] Verify compatibility aliases:

```bash
me-graph --help
python -c 'import shutil; assert shutil.which("me-graph-mcp")'
```

- [ ] Open Draft PR and require:

```text
Python 3.11 unit
Python 3.12 unit
PostgreSQL 16 integration
stdio MCP E2E
compileall
```

- [ ] Squash merge only after all checks pass.

Squash title:

```text
refactor: unify runtime code under ME-Core
```

## Self-review checklist

- [ ] No second core or second database introduced.
- [ ] ME-Brain and ME-Who remain namespaces, not services.
- [ ] Graph and MCP behavior unchanged.
- [ ] Old Python package does not remain as duplicate implementation.
- [ ] Only command aliases are temporarily retained.
- [ ] Active docs, CI, packaging, imports and directory names agree.
- [ ] Full CI proves parity.