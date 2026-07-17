from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .diagnostics import run_diagnostics
from .models import PaperValidationError, ZoteroPaper
from .obsidian import create_or_find_paper_note


def _load_paper(path: Path) -> ZoteroPaper:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PaperValidationError(f"Unable to read item JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PaperValidationError("Item JSON must contain an object")
    return ZoteroPaper.from_dict(data)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="me-reader")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-paper-note")
    create.add_argument("--item-json", required=True, type=Path)
    create.add_argument("--vault", required=True, type=Path)

    diagnose = subparsers.add_parser("diagnose")
    diagnose.add_argument("--vault", required=True, type=Path)
    diagnose.add_argument("--item-json", type=Path)
    diagnose.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "create-paper-note":
            paper = _load_paper(args.item_json)
            result = create_or_find_paper_note(args.vault, paper)
            payload = {
                "status": result.status,
                "note_path": str(result.path),
                "item_uri": result.item_uri,
                "pdf_uri": result.pdf_uri,
            }
            print(json.dumps(payload, ensure_ascii=False))
            return 0

        paper = _load_paper(args.item_json) if args.item_json else None
        report = run_diagnostics(args.vault, paper)
        output = args.output or (Path(args.vault) / "diagnostics" / "me-reader-diagnostic.md")
        written = report.write(output)
        print(
            json.dumps(
                {
                    "status": report.overall_status,
                    "report_path": str(written),
                },
                ensure_ascii=False,
            )
        )
        return 0 if report.overall_status != "FAIL" else 1
    except (PaperValidationError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
