# ME-System Dual Graph Core Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorient ME-System around two canonical graph products—ME-Brain Graph and ME-Who Graph—and deliver a runnable, tested graph-contract and query foundation that Hermes or Pi adapters can consume later.

**Architecture:** Raw documents and external records remain evidence inputs. Candidate extraction produces proposed graph changes; only reviewed changes enter one of two canonical graphs. Agents never query storage directly: they consume typed graph slices and evidence handles through a transport-neutral query service, which can later be exposed through MCP, REST, or a Pi extension.

**Tech Stack:** Python 3.11+, standard library dataclasses and enums, pytest, jsonschema for contract tests, JSON fixtures, Markdown architecture documentation.

## Global Constraints

- Repository remains a monorepo.
- ME-Who and ME-Brain are the only product-level graphs.
- Document standardization is an input/evidence layer, not a third product.
- Context packs are runtime projections of graph slices, not canonical storage.
- Agents must not write canonical graph data directly.
- Every canonical node and edge must support provenance, temporal validity, authority, and sensitivity.
- ME-Who and ME-Brain use separate graph namespaces and ontologies.
- Cross-graph relations are explicit bridge records, never implicit shared tables.
- First implementation uses an in-memory repository behind a `GraphStore` interface; database choice remains replaceable.
- First implementation does not introduce a production MCP dependency.

---

## Planned File Structure

```text
README.md
docs/
├── 00-product-and-architecture-overview.md
├── adr/
│   ├── ADR-0003-agent-context-access-layer.md
│   └── ADR-0004-two-canonical-graphs.md
├── products/
│   ├── me-brain.md
│   └── me-who.md
├── specs/
│   ├── dual-graph-contract-v0.1.md
│   ├── me-brain-ontology-v0.1.md
│   └── me-who-ontology-v0.1.md
└── roadmap/
    └── recommended-development-path.md

services/me-graph-core/
├── pyproject.toml
├── README.md
├── schemas/
│   ├── graph-node.schema.json
│   ├── graph-edge.schema.json
│   ├── evidence-ref.schema.json
│   ├── candidate-graph-change.schema.json
│   └── graph-slice.schema.json
├── src/me_graph_core/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── contracts.py
│   ├── errors.py
│   ├── fixtures.py
│   ├── query.py
│   ├── review.py
│   └── store.py
└── tests/
    ├── test_contract_schemas.py
    ├── test_contracts.py
    ├── test_store.py
    ├── test_review.py
    ├── test_query.py
    └── test_cli.py

examples/graph/
└── lighting-platform.json

integrations/
├── hermes/README.md
└── pi/README.md
```

---

### Task 1: Stabilize the architecture documentation

**Files:**
- Modify: `README.md`
- Replace: `docs/00-product-and-architecture-overview.md`
- Create: `docs/adr/ADR-0004-two-canonical-graphs.md`
- Replace: `docs/products/me-brain.md`
- Replace: `docs/products/me-who.md`
- Create: `docs/specs/dual-graph-contract-v0.1.md`
- Create: `docs/specs/me-brain-ontology-v0.1.md`
- Create: `docs/specs/me-who-ontology-v0.1.md`
- Replace: `docs/roadmap/recommended-development-path.md`
- Modify: `docs/adr/ADR-0003-agent-context-access-layer.md`

**Interfaces:**
- Produces the authoritative architecture vocabulary used by all later tasks.

- [ ] Reframe ME-System as two canonical graphs plus shared evidence and query infrastructure.
- [ ] Mark ADR-0003 as an access-layer decision subordinate to ADR-0004.
- [ ] Remove ME-Context and ME-Reader as peer product lines.
- [ ] Define the first ME-Brain and ME-Who node and edge sets.
- [ ] Define the new implementation order: graph contracts → manual fixture → query core → Hermes read-only adapter → ingestion adapters → ME-Who minimum graph → Pi.
- [ ] Commit documentation changes.

### Task 2: Define JSON contracts before production code

**Files:**
- Create: `services/me-graph-core/schemas/*.schema.json`
- Test: `services/me-graph-core/tests/test_contract_schemas.py`

**Interfaces:**
- Produces schemas for `GraphNode`, `GraphEdge`, `EvidenceRef`, `CandidateGraphChange`, and `GraphSlice`.

- [ ] Write failing schema tests that load every schema and validate accepted and rejected examples.
- [ ] Run tests and verify failure because schemas do not exist.
- [ ] Implement the five JSON Schema files.
- [ ] Run tests and verify all schema tests pass.
- [ ] Commit schema contracts.

### Task 3: Implement validated Python domain contracts

**Files:**
- Create: `services/me-graph-core/pyproject.toml`
- Create: `services/me-graph-core/src/me_graph_core/contracts.py`
- Create: `services/me-graph-core/src/me_graph_core/errors.py`
- Create: `services/me-graph-core/src/me_graph_core/__init__.py`
- Test: `services/me-graph-core/tests/test_contracts.py`

**Interfaces:**
- Produces immutable dataclasses and enums used by all later tasks.
- `GraphNode.from_dict(data) -> GraphNode`
- `GraphEdge.from_dict(data) -> GraphEdge`
- `EvidenceRef.from_dict(data) -> EvidenceRef`
- `CandidateGraphChange.from_dict(data) -> CandidateGraphChange`
- `GraphSlice.to_dict() -> dict[str, object]`

- [ ] Write failing tests for graph namespace validation, temporal fields, self-loop rules, evidence requirements, and serialization.
- [ ] Run tests and verify expected failures.
- [ ] Implement the minimal validated contracts.
- [ ] Run tests and verify they pass.
- [ ] Refactor without changing behavior and rerun tests.
- [ ] Commit domain contracts.

### Task 4: Implement graph storage and candidate review workflow

**Files:**
- Create: `services/me-graph-core/src/me_graph_core/store.py`
- Create: `services/me-graph-core/src/me_graph_core/review.py`
- Test: `services/me-graph-core/tests/test_store.py`
- Test: `services/me-graph-core/tests/test_review.py`

**Interfaces:**
- `GraphStore.add_node(node) -> None`
- `GraphStore.add_edge(edge) -> None`
- `GraphStore.get_node(node_id) -> GraphNode`
- `GraphStore.neighbors(node_id, edge_types=None, direction="both") -> tuple[GraphEdge, ...]`
- `CandidateReviewService.submit(change) -> CandidateGraphChange`
- `CandidateReviewService.approve(change_id, reviewer_id) -> None`
- `CandidateReviewService.reject(change_id, reviewer_id, reason) -> None`

- [ ] Write failing tests for separate namespaces, duplicate IDs, invalid cross-graph edges, explicit bridge edges, candidate-only writes, approval, rejection, and provenance preservation.
- [ ] Run tests and verify expected failures.
- [ ] Implement in-memory storage behind an abstract `GraphStore` protocol.
- [ ] Implement candidate review and canonical application.
- [ ] Run tests and verify they pass.
- [ ] Commit storage and review workflow.

### Task 5: Implement typed graph queries and the lighting-platform fixture

**Files:**
- Create: `examples/graph/lighting-platform.json`
- Create: `services/me-graph-core/src/me_graph_core/fixtures.py`
- Create: `services/me-graph-core/src/me_graph_core/query.py`
- Test: `services/me-graph-core/tests/test_query.py`

**Interfaces:**
- `load_graph_fixture(path, store) -> None`
- `GraphQueryService.get_project_snapshot(project_id, as_of=None) -> GraphSlice`
- `GraphQueryService.expand_subgraph(node_id, depth=1, edge_types=None) -> GraphSlice`
- `GraphQueryService.trace_decision(decision_id) -> GraphSlice`
- `GraphQueryService.get_evidence(node_or_edge_id) -> tuple[EvidenceRef, ...]`
- `GraphQueryService.get_task_profile(user_id, project_id, task_type) -> GraphSlice`

- [ ] Write failing tests that prove current decisions exclude superseded decisions, decision history remains traceable, blocked tasks are returned, evidence is addressable, and ME-Who rules are task-scoped.
- [ ] Run tests and verify expected failures.
- [ ] Create a small manually curated `lighting-platform` graph fixture.
- [ ] Implement the typed query service.
- [ ] Run tests and verify they pass.
- [ ] Commit fixture and queries.

### Task 6: Add a runnable CLI and adapter boundaries

**Files:**
- Create: `services/me-graph-core/src/me_graph_core/cli.py`
- Create: `services/me-graph-core/src/me_graph_core/__main__.py`
- Create: `services/me-graph-core/README.md`
- Create: `integrations/hermes/README.md`
- Create: `integrations/pi/README.md`
- Test: `services/me-graph-core/tests/test_cli.py`

**Interfaces:**
- `me-graph load-fixture --fixture <path>`
- `me-graph project-snapshot --fixture <path> --project-id <id>`
- `me-graph trace-decision --fixture <path> --decision-id <id>`
- `me-graph task-profile --fixture <path> --user-id <id> --project-id <id> --task-type <type>`

- [ ] Write failing CLI tests for valid JSON output and invalid identifiers.
- [ ] Run tests and verify expected failures.
- [ ] Implement the CLI without adding a production MCP dependency.
- [ ] Document the future Hermes MCP and Pi extension mapping to the same query functions.
- [ ] Run tests and verify they pass.
- [ ] Commit runnable graph core.

### Task 7: Final verification and repository cleanup

**Files:**
- Review all files created or modified above.
- Update PR #1 status only after replacement PR is ready.

- [ ] Run `pytest -q` in `services/me-graph-core` and confirm zero failures.
- [ ] Run all four CLI acceptance commands against `examples/graph/lighting-platform.json`.
- [ ] Validate every JSON Schema with `jsonschema`.
- [ ] Scan docs for contradictory product definitions, duplicate ADR numbering, and references to ME-Reader or ME-Context as peer products.
- [ ] Open a Draft PR from `agent/optimize-dual-graph-core` to `main`.
- [ ] Close PR #1 as superseded, preserving its branch for later migration of Zotero/Obsidian adapter code.
