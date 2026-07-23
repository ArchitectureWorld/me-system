from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .contracts import GraphNamespace
from .errors import GraphCoreError
from .fixtures import load_graph_fixture
from .query import GraphQueryService
from .store import InMemoryGraphStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="me-graph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    load = subparsers.add_parser("load-fixture", help="validate and summarize a graph fixture")
    load.add_argument("--fixture", required=True, type=Path)

    snapshot = subparsers.add_parser("project-snapshot", help="return the current ME-Brain project slice")
    snapshot.add_argument("--fixture", required=True, type=Path)
    snapshot.add_argument("--project-id", required=True)

    trace = subparsers.add_parser("trace-decision", help="return the full SUPERSEDES decision chain")
    trace.add_argument("--fixture", required=True, type=Path)
    trace.add_argument("--decision-id", required=True)

    profile = subparsers.add_parser("task-profile", help="return task-scoped ME-Who rules")
    profile.add_argument("--fixture", required=True, type=Path)
    profile.add_argument("--user-id", required=True)
    profile.add_argument("--project-id", required=True)
    profile.add_argument("--task-type", required=True)

    return parser


def _load(path: Path) -> tuple[InMemoryGraphStore, GraphQueryService]:
    store = InMemoryGraphStore()
    load_graph_fixture(path, store)
    return store, GraphQueryService(store)


def _write(payload: object, stream) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        store, query = _load(args.fixture)
        if args.command == "load-fixture":
            _write(
                {
                    "nodes": {
                        namespace.value: len(store.list_nodes(namespace))
                        for namespace in (GraphNamespace.ME_BRAIN, GraphNamespace.ME_WHO)
                    },
                    "edges": {
                        namespace.value: len(store.list_edges(namespace))
                        for namespace in (
                            GraphNamespace.ME_BRAIN,
                            GraphNamespace.ME_WHO,
                            GraphNamespace.BRIDGE,
                        )
                    },
                },
                sys.stdout,
            )
            return 0
        if args.command == "project-snapshot":
            _write(query.get_project_snapshot(args.project_id).to_dict(), sys.stdout)
            return 0
        if args.command == "trace-decision":
            _write(query.trace_decision(args.decision_id).to_dict(), sys.stdout)
            return 0
        if args.command == "task-profile":
            _write(
                query.get_task_profile(args.user_id, args.project_id, args.task_type).to_dict(),
                sys.stdout,
            )
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except (GraphCoreError, OSError, ValueError) as exc:
        _write(
            {
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
