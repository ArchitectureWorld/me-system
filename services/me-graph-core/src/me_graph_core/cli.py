from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .contracts import GraphNamespace
from .errors import GraphCoreError, GraphStoreConfigurationError
from .fixtures import load_graph_fixture
from .persistence.database import create_database_engine
from .persistence.migrations import upgrade_database
from .persistence.store import SqlAlchemyGraphStore
from .query import GraphQueryService
from .store import GraphStore, InMemoryGraphStore


def _add_query_source(parser: argparse.ArgumentParser) -> None:
    # These are ordinary options rather than an argparse mutually-exclusive
    # group so conflicts can use the CLI's structured JSON error model.
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--database-url")
    parser.add_argument("--allow-test-database", action="store_true")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="me-graph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    load = subparsers.add_parser("load-fixture", help="validate and summarize a graph fixture")
    load.add_argument("--fixture", required=True, type=Path)

    upgrade = subparsers.add_parser("db-upgrade", help="upgrade a graph database to the current schema")
    upgrade.add_argument("--database-url")
    upgrade.add_argument("--allow-test-database", action="store_true")

    import_fixture = subparsers.add_parser(
        "import-fixture", help="migrate a graph database and import a fixture"
    )
    import_fixture.add_argument("--fixture", required=True, type=Path)
    import_fixture.add_argument("--database-url")
    import_fixture.add_argument("--allow-test-database", action="store_true")

    snapshot = subparsers.add_parser(
        "project-snapshot", help="return the current ME-Brain project slice"
    )
    _add_query_source(snapshot)
    snapshot.add_argument("--project-id", required=True)

    trace = subparsers.add_parser("trace-decision", help="return the full SUPERSEDES decision chain")
    _add_query_source(trace)
    trace.add_argument("--decision-id", required=True)

    profile = subparsers.add_parser("task-profile", help="return task-scoped ME-Who rules")
    _add_query_source(profile)
    profile.add_argument("--user-id", required=True)
    profile.add_argument("--project-id", required=True)
    profile.add_argument("--task-type", required=True)

    return parser


def _write(payload: object, stream) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _database_url(args: argparse.Namespace) -> str | None:
    return getattr(args, "database_url", None) or os.getenv("ME_GRAPH_DATABASE_URL")


def _require_database_url(args: argparse.Namespace) -> str:
    url = _database_url(args)
    if not url:
        raise GraphStoreConfigurationError(
            "database URL is required via --database-url or ME_GRAPH_DATABASE_URL"
        )
    return url


def _summary(store: GraphStore) -> dict[str, object]:
    return {
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
    }


def _query_source(args: argparse.Namespace) -> tuple[GraphStore, GraphQueryService]:
    fixture = getattr(args, "fixture", None)
    explicit_url = getattr(args, "database_url", None)
    if fixture is not None and explicit_url:
        raise GraphStoreConfigurationError("choose exactly one graph data source")
    if fixture is not None:
        store = InMemoryGraphStore()
        load_graph_fixture(fixture, store)
        return store, GraphQueryService(store)

    url = explicit_url or os.getenv("ME_GRAPH_DATABASE_URL")
    if not url:
        raise GraphStoreConfigurationError("graph data source is required")
    engine = create_database_engine(url, production=not args.allow_test_database)
    store = SqlAlchemyGraphStore(engine)
    return store, GraphQueryService(store)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "load-fixture":
            store = InMemoryGraphStore()
            load_graph_fixture(args.fixture, store)
            _write(_summary(store), sys.stdout)
            return 0

        if args.command == "db-upgrade":
            url = _require_database_url(args)
            upgrade_database(url, production=not args.allow_test_database)
            _write({"status": "upgraded"}, sys.stdout)
            return 0

        if args.command == "import-fixture":
            url = _require_database_url(args)
            production = not args.allow_test_database
            upgrade_database(url, production=production)
            store = SqlAlchemyGraphStore(create_database_engine(url, production=production))
            load_graph_fixture(args.fixture, store)
            _write(_summary(store), sys.stdout)
            return 0

        _, query = _query_source(args)
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
