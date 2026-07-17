# ME-Reader Core

ME-Reader Core is the client-independent backend for evidence-oriented literature reading. The first runnable slice converts one validated Zotero paper record into one stable Obsidian paper note with Zotero return links.

## Current capability

- Validate a Zotero literature metadata record supplied as JSON.
- Create stable paper and document identities from the Zotero item key.
- Create a UTF-8 Markdown note under `<vault>/papers/`.
- Add Zotero item and PDF return links.
- Find the existing note by `zotero_item_key` on repeat execution.
- Preserve human content because an existing note is never overwritten.
- Produce a Markdown diagnostic report without including PDF text or secrets.

This slice does not yet connect to the live Zotero API, parse PDF content, run Hermes reading agents, or install an Obsidian plugin.

## Install for development

```bash
cd services/me-reader-core
python -m pip install -e '.[dev]'
```

## Create a paper note

```bash
me-reader create-paper-note \
  --item-json examples/me-reader/sample-zotero-item.json \
  --vault /path/to/your/ME-Brain-vault
```

Run the same command again. The status must be `existing`, and the Vault must still contain exactly one note for the item key.

## Generate a diagnostic report

```bash
me-reader diagnose \
  --item-json examples/me-reader/sample-zotero-item.json \
  --vault /path/to/your/ME-Brain-vault
```

## Test

```bash
cd services/me-reader-core
pytest -q
```
