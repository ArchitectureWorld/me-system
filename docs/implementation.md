# ME-System Implementation Guide

ME-System is one Python distribution with two canonical graph domains:

```text
src/me_system/
├── brain/       ME-Brain domain
├── who/         ME-Who domain
├── bridge/      explicit cross-domain relations
├── contracts.py
├── query.py
├── store.py
├── persistence/
└── hermes/      read-only MCP adapter
```

Persistence, evidence, ingestion, review, query, CLI, and MCP are internal responsibilities. They are not additional products or cores.

## Install

```bash
python -m pip install -e '.[dev]'
```

## Fixture validation

```bash
me-system load-fixture --fixture examples/graph/lighting-platform.json
me-system project-snapshot \
  --fixture examples/graph/lighting-platform.json \
  --project-id brain:project:lighting-platform
```

## PostgreSQL

```bash
export ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph:password@127.0.0.1:5432/me_graph'
me-system db-upgrade
me-system import-fixture --fixture examples/graph/lighting-platform.json
```

## Hermes MCP

```bash
ME_GRAPH_DATABASE_URL='postgresql+psycopg://me_graph_reader:password@127.0.0.1:5432/me_graph' \
ME_GRAPH_HERMES_USER_ID='who:user:master' \
ME_GRAPH_ALLOWED_PROJECT_IDS='brain:project:lighting-platform' \
me-system-mcp
```

The MCP adapter remains read-only and exposes the existing six typed tools. Agents read compact graph slices first and drill down to evidence only when required.
