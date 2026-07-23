# Unified ME-System Package Migration

The historical runtime paths `services/me-graph-core/`, `services/me-core/`, and Python packages `me_graph_core` / `me_core` were transitional implementation names.

The canonical runtime is now `src/me_system/`. ME-Brain and ME-Who are the only product graph domains. Bridge is an explicit relation namespace. Persistence, evidence, ingestion, review, query, CLI, and MCP are internal ME-System responsibilities.
