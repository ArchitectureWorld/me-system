# ME-Reader Step 0–1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable ME-Reader vertical slice that validates a Zotero literature record, creates exactly one Obsidian paper note, preserves human content on repeated runs, and produces a user-readable diagnostic report.

**Architecture:** Implement a dependency-light Python package under `services/me-reader-core`. Zotero remains the authoritative source for bibliographic identity and attachments; the package creates an Obsidian Markdown projection with stable ME-Brain IDs and Zotero return links. The first slice uses JSON input so it can be exercised before the Zotero and Obsidian plugins are added.

**Tech Stack:** Python 3.11+, standard library, pytest, Markdown/YAML frontmatter projection, JSON command-line input.

## Global Constraints

- Repository remains a monorepo.
- Core logic must not depend on Obsidian internals or a specific LLM provider.
- Zotero item key is the stable external identity for the P0 paper record.
- Markdown is a human-readable projection, not the only authoritative store.
- Agent-managed content must never overwrite `USER-CONTENT` sections.
- Zotero return links use `zotero://select/library/items/<ITEM_KEY>` and `zotero://open-pdf/library/items/<ATTACHMENT_KEY>`.
- No fixed IP address or port may be introduced.
- The first slice supports user-library items and text metadata only; PDF parsing and Agent deep reading are later tasks.

---

## Planned File Structure

```text
services/me-reader-core/
├── pyproject.toml
├── README.md
├── src/me_reader_core/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── diagnostics.py
│   ├── identity.py
│   ├── models.py
│   ├── obsidian.py
│   └── zotero_links.py
└── tests/
    ├── test_cli.py
    ├── test_diagnostics.py
    ├── test_identity.py
    ├── test_models.py
    ├── test_obsidian.py
    └── test_zotero_links.py

docs/acceptance/
└── ACCEPTANCE-STEP-01-ZOTERO-OBSIDIAN-LINK.md

examples/me-reader/
└── sample-zotero-item.json
```

## Implementation Tasks

1. Define and validate Zotero paper input.
2. Generate stable identities and safe note filenames.
3. Generate Zotero return links.
4. Create an idempotent Obsidian paper note.
5. Add a diagnostic report.
6. Add a command-line experience.
7. Add a small-user acceptance kit.

## Completion Check

- [ ] `pytest -q` reports zero failures.
- [ ] The sample command creates one UTF-8 Markdown note under `papers/`.
- [ ] Running the same command twice still leaves exactly one note.
- [ ] User content remains byte-for-byte unchanged after the second run.
- [ ] The diagnostic command creates a readable Markdown report.
- [ ] No fixed host, IP, port, API key, or machine-specific absolute path is committed.
