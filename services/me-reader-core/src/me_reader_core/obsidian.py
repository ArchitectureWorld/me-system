from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile

from .identity import document_id, paper_id, paper_note_filename
from .models import ZoteroPaper
from .zotero_links import item_select_uri, pdf_open_uri


_ITEM_KEY_PATTERN = re.compile(r"^zotero_item_key:\s*['\"]?([^'\"\n]+)", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class PaperNoteResult:
    status: str
    path: Path
    item_uri: str
    pdf_uri: str | None


def _yaml_scalar(value: str | None) -> str:
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False)


def _yaml_list(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(_yaml_scalar(value) for value in values) + "]"


def _find_existing_note(papers_dir: Path, item_key: str) -> Path | None:
    for path in sorted(papers_dir.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        match = _ITEM_KEY_PATTERN.search(content)
        if match and match.group(1).strip() == item_key:
            return path
    return None


def _render_note(paper: ZoteroPaper) -> str:
    item_uri = item_select_uri(paper.zotero_item_key)
    pdf_uri = pdf_open_uri(paper.zotero_attachment_key)
    pdf_link = f"[打开 PDF]({pdf_uri})" if pdf_uri else "未关联 PDF 附件"
    author_text = "、".join(paper.authors) if paper.authors else "未提供"

    return f"""---
mebrain_id: {paper_id(paper.zotero_item_key)}
document_id: {document_id(paper.zotero_item_key)}
zotero_item_key: {paper.zotero_item_key}
zotero_attachment_key: {_yaml_scalar(paper.zotero_attachment_key)}
citation_key: {_yaml_scalar(paper.citation_key)}
pdf_uri: {_yaml_scalar(pdf_uri)}
reading_job_id: null
reading_status: not_started
review_status: pending
title: {_yaml_scalar(paper.title)}
authors: {_yaml_list(paper.authors)}
year: {_yaml_scalar(paper.year)}
publication: {_yaml_scalar(paper.publication)}
doi: {_yaml_scalar(paper.doi)}
---

# {paper.title}

## 文献信息

- **作者：** {author_text}
- **年份：** {paper.year or '未提供'}
- **期刊/来源：** {paper.publication or '未提供'}
- **DOI：** {paper.doi or '未提供'}
- [在 Zotero 中打开]({item_uri})
- {pdf_link}

## 人工笔记

<!-- USER-CONTENT:START -->
<!-- USER-CONTENT:END -->

## Agent 精读

<!-- AGENT-CONTENT:START -->
尚未执行 Agent 精读。
<!-- AGENT-CONTENT:END -->

## Claim 与证据

尚无候选 Claim。

## 关联对象

尚无关联对象。

## 待复核

- [ ] 尚未开始精读
"""


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def create_or_find_paper_note(vault_path: Path, paper: ZoteroPaper) -> PaperNoteResult:
    vault = Path(vault_path).expanduser().resolve()
    papers_dir = vault / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)

    existing = _find_existing_note(papers_dir, paper.zotero_item_key)
    item_uri = item_select_uri(paper.zotero_item_key)
    pdf_uri = pdf_open_uri(paper.zotero_attachment_key)
    if existing is not None:
        return PaperNoteResult("existing", existing, item_uri, pdf_uri)

    note_path = papers_dir / paper_note_filename(paper)
    if note_path.parent != papers_dir:
        raise ValueError("unsafe note path")
    _atomic_write(note_path, _render_note(paper))
    return PaperNoteResult("created", note_path, item_uri, pdf_uri)
