# Hermes Read-only MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic project resolution and a six-tool read-only stdio MCP server that lets Hermes query PostgreSQL-backed ME-Brain and task-scoped ME-Who data.

**Architecture:** Keep all graph semantics inside `GraphQueryService`. Add `ProjectResolver`, a server-configured project scope guard, and pure `HermesReadOnlyTools`. Wrap those pure services with FastMCP v1; Hermes receives only a fixed six-tool surface and cannot choose another ME-Who user or query outside the project allowlist.

**Tech Stack:** Python 3.11+, existing ME-Graph Core, MCP Python SDK `>=1.27,<2`, FastMCP, pytest, PostgreSQL 16 CI, Hermes stdio MCP configuration.

## Global Constraints

- Server is read-only; no Candidate or canonical write tool.
- MCP SDK is pinned below v2.
- Project matching is exact and deterministic; no LLM or fuzzy matching.
- `ME_GRAPH_ALLOWED_PROJECT_IDS` is required and defaults to deny.
- `ME_GRAPH_HERMES_USER_ID` is server-side configuration and is never a tool parameter.
- Object tools require `project_id` and membership validation.
- Maximum subgraph depth is configured by the server and cannot exceed 3.
- Tools return structured JSON envelopes.
- stdout is reserved for stdio MCP protocol.

---

### Task 1: Add project resolution contracts and fixture metadata

**Files:**
- Modify: `examples/graph/lighting-platform.json`
- Create: `services/me-graph-core/src/me_graph_core/hermes/__init__.py`
- Create: `services/me-graph-core/src/me_graph_core/hermes/resolver.py`
- Create: `services/me-graph-core/tests/test_project_resolver.py`

**Interfaces:**
- `ProjectResolution.to_dict() -> dict[str, object]`
- `ProjectResolver.resolve(...) -> ProjectResolution`

Steps:

1. Write failing tests for canonical ID, label, alias, workspace path, external ID, precedence, ambiguity, not-found and allowlist filtering.
2. Run the focused tests and verify RED.
3. Add `aliases`, `workspace_paths` and `external_ids` to the fixture project node.
4. Implement normalized exact matching and structured resolution results.
5. Run focused tests and full regression tests.

---

### Task 2: Implement settings and project scope guard

**Files:**
- Create: `services/me-graph-core/src/me_graph_core/hermes/settings.py`
- Create: `services/me-graph-core/src/me_graph_core/hermes/access.py`
- Create: `services/me-graph-core/tests/test_hermes_settings.py`
- Create: `services/me-graph-core/tests/test_project_scope_guard.py`

**Interfaces:**
- `HermesServerSettings.from_env() -> HermesServerSettings`
- `ProjectScopeGuard.require_project(project_id) -> None`
- `ProjectScopeGuard.require_member(project_id, object_id) -> None`

Steps:

1. Write failing tests for required env vars, `*`, explicit allowlists, max depth and secret-safe errors.
2. Write failing tests for allowed project, denied project, current node, superseded decision, Bridge object and unrelated object.
3. Implement immutable settings and bounded project membership traversal.
4. Run focused and full tests.

---

### Task 3: Implement pure read-only tool service

**Files:**
- Create: `services/me-graph-core/src/me_graph_core/hermes/tools.py`
- Create: `services/me-graph-core/tests/test_hermes_tools.py`

**Interfaces:**
- `HermesReadOnlyTools.resolve_project(...) -> dict`
- `HermesReadOnlyTools.get_snapshot(project_id) -> dict`
- `HermesReadOnlyTools.expand_subgraph(...) -> dict`
- `HermesReadOnlyTools.trace_decision(...) -> dict`
- `HermesReadOnlyTools.get_evidence(...) -> dict`
- `HermesReadOnlyTools.get_task_profile(...) -> dict`

Steps:

1. Write failing tests for six success paths and unified error envelopes.
2. Verify fixed user injection and project allowlist behavior.
3. Implement tool service without importing MCP.
4. Run focused tests and full regression tests.

---

### Task 4: Add FastMCP stdio server

**Files:**
- Modify: `services/me-graph-core/pyproject.toml`
- Create: `services/me-graph-core/src/me_graph_core/hermes/mcp_server.py`
- Create: `services/me-graph-core/tests/test_mcp_server.py`
- Create: `services/me-graph-core/tests/test_mcp_stdio.py`

**Interfaces:**
- `create_mcp_server(tools: HermesReadOnlyTools) -> FastMCP`
- `main() -> None`
- console script `me-graph-mcp`

Steps:

1. Add `mcp>=1.27,<2` dependency and entry point.
2. Write failing tool-list test expecting exactly six tools.
3. Register six structured-output FastMCP tools.
4. Write stdio integration test using official `ClientSession` and `stdio_client`.
5. Run protocol tests locally when package is available and in CI with PostgreSQL.

---

### Task 5: Add Hermes configuration and bootstrap documentation

**Files:**
- Modify: `integrations/hermes/README.md`
- Create: `integrations/hermes/config.example.yaml`
- Create: `integrations/hermes/ME_SYSTEM_BOOTSTRAP.md`
- Modify: `services/me-graph-core/README.md`
- Modify: `README.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/roadmap/recommended-development-path.md`

Steps:

1. Document stdio config, environment variables and exact tool whitelist.
2. Document resolve → snapshot → optional drill-down flow.
3. Make clear that dynamic project state does not belong in context files.
4. Record the read-only boundary and next Adapter phase.

---

### Task 6: CI, verification and merge

**Files:**
- Modify: `.github/workflows/me-graph-core.yml`

Steps:

1. Ensure CI installs MCP v1 and starts PostgreSQL 16.
2. Run all tests on Python 3.11 and 3.12.
3. Verify the stdio client lists exactly six tools and calls resolve/snapshot/profile successfully.
4. Verify unauthorized project and depth violations return structured errors.
5. Open Draft PR, review the diff, mark ready, squash merge and verify no open PR remains.
