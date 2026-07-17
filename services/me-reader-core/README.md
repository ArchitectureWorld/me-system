# ME-Reader Core

ME-Reader Core is the client-independent backend for evidence-oriented literature reading. The first runnable slice converts one validated Zotero paper record into one stable Obsidian paper note with Zotero return links.

## Current capability

- Validate a Zotero literature metadata record supplied as JSON.
- Read bibliographic metadata and child PDF identity from the Zotero Local API.
- Create stable paper and document identities from the Zotero item key.
- Create a UTF-8 Markdown note under `<vault>/papers/`.
- Add Zotero item and PDF return links.
- Find the existing note by `zotero_item_key` on repeat execution.
- Preserve human content because an existing note is never overwritten.
- Produce a Markdown diagnostic report without including PDF text or secrets.

This slice does not yet parse PDF content, run Hermes reading agents, or install an Obsidian plugin.

## Install for development

```bash
cd services/me-reader-core
python -m pip install -e '.[dev]'
```

## Create a paper note from JSON

```bash
me-reader create-paper-note \
  --item-json examples/me-reader/sample-zotero-item.json \
  --vault /path/to/your/ME-Brain-vault
```

## Read directly from a running Zotero instance

Enable Zotero local API access in Zotero Settings → Advanced → **Allow other applications on this computer to communicate with Zotero**.

```bash
me-reader create-paper-note-from-zotero \
  --item-key ABCD1234 \
  --zotero-base-url http://127.0.0.1:23119/api \
  --vault /path/to/your/ME-Brain-vault
```

For a second instance, provide its configured address, for example `http://127.0.0.1:23120/api`. The address can also be provided through `ME_READER_ZOTERO_BASE_URL`.

ME-Reader only permits HTTP loopback addresses for the local API and never forwards the port externally.

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
