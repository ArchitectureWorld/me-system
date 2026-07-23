from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Mapping

from .contracts import GraphNamespace
from .errors import GraphCoreError, GraphStoreConfigurationError
from .evidence.contracts import EvidenceFragment, SourceRecord
from .fixtures import load_graph_fixture
from .ingestion.contracts import CandidateRecord
from .ingestion.review import PersistentReviewService
from .persistence.candidate_repository import SqlAlchemyCandidateRepository
from .persistence.database import create_database_engine
from .persistence.migrations import upgrade_database
from .persistence.source_repository import SqlAlchemySourceRepository
from .persistence.store import SqlAlchemyGraphStore
from .query import GraphQueryService
from .store import GraphStore, InMemoryGraphStore


def _add_database_source(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--database-url")
    parser.add_argument("--allow-test-database", action="store_true")


def _add_query_source(parser: argparse.ArgumentParser) -> None:
    # Ordinary options preserve the CLI's structured JSON error model.
    parser.add_argument("--fixture", type=Path)
    _add_database_source(parser)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="me-system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    load = subparsers.add_parser(
        "load-fixture",
        help="validate and summarize a graph fixture",
    )
    load.add_argument("--fixture", required=True, type=Path)

    upgrade = subparsers.add_parser(
        "db-upgrade",
        help="upgrade a ME-System database to the current schema",
    )
    _add_database_source(upgrade)

    import_fixture = subparsers.add_parser(
        "import-fixture",
        help="migrate a ME-System database and import a graph fixture",
    )
    import_fixture.add_argument("--fixture", required=True, type=Path)
    _add_database_source(import_fixture)

    snapshot = subparsers.add_parser(
        "project-snapshot",
        help="return the current ME-Brain project slice",
    )
    _add_query_source(snapshot)
    snapshot.add_argument("--project-id", required=True)

    trace = subparsers.add_parser(
        "trace-decision",
        help="return the full SUPERSEDES decision chain",
    )
    _add_query_source(trace)
    trace.add_argument("--decision-id", required=True)

    profile = subparsers.add_parser(
        "task-profile",
        help="return task-scoped ME-Who rules",
    )
    _add_query_source(profile)
    profile.add_argument("--user-id", required=True)
    profile.add_argument("--project-id", required=True)
    profile.add_argument("--task-type", required=True)

    source_register = subparsers.add_parser(
        "source-register",
        help="register an immutable source and optional evidence fragments from JSON",
    )
    _add_database_source(source_register)
    source_register.add_argument("--json", required=True, type=Path)

    source_show = subparsers.add_parser(
        "source-show",
        help="show a source and its addressable evidence fragments",
    )
    _add_database_source(source_show)
    source_show.add_argument("--source-id", required=True)

    candidate_submit = subparsers.add_parser(
        "candidate-submit",
        help="submit an idempotent persistent candidate from JSON",
    )
    _add_database_source(candidate_submit)
    candidate_submit.add_argument("--json", required=True, type=Path)

    candidate_list = subparsers.add_parser(
        "candidate-list",
        help="list pending ME-Brain or ME-Who candidates",
    )
    _add_database_source(candidate_list)
    candidate_list.add_argument(
        "--target-graph",
        choices=[item.value for item in GraphNamespace],
    )
    candidate_list.add_argument("--source-id")
    candidate_list.add_argument("--limit", type=int, default=100)

    candidate_approve = subparsers.add_parser(
        "candidate-approve",
        help="atomically approve a candidate into the canonical graph",
    )
    _add_database_source(candidate_approve)
    candidate_approve.add_argument("--change-id", required=True)
    candidate_approve.add_argument("--reviewer-id", required=True)
    candidate_approve.add_argument(
        "--reviewer-kind",
        choices=("human", "rule"),
        default="human",
    )
    candidate_approve.add_argument("--reason", default="approved")

    candidate_reject = subparsers.add_parser(
        "candidate-reject",
        help="reject a candidate and append an immutable review event",
    )
    _add_database_source(candidate_reject)
    candidate_reject.add_argument("--change-id", required=True)
    candidate_reject.add_argument("--reviewer-id", required=True)
    candidate_reject.add_argument(
        "--reviewer-kind",
        choices=("human", "rule"),
        default="human",
    )
    candidate_reject.add_argument("--reason", required=True)

    return parser


def _write(payload: object, stream) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_json(path: Path) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("JSON input root must be an object")
    return payload


def _database_url(args: argparse.Namespace) -> str | None:
    return getattr(args, "database_url", None) or os.getenv(
        "ME_GRAPH_DATABASE_URL"
    )


def _require_database_url(args: argparse.Namespace) -> str:
    url = _database_url(args)
    if not url:
        raise GraphStoreConfigurationError(
            "database URL is required via --database-url or ME_GRAPH_DATABASE_URL"
        )
    return url


def _database_engine(args: argparse.Namespace):
    url = _require_database_url(args)
    return create_database_engine(
        url,
        production=not args.allow_test_database,
    )


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


def _query_source(
    args: argparse.Namespace,
) -> tuple[GraphStore, GraphQueryService]:
    fixture = getattr(args, "fixture", None)
    explicit_url = getattr(args, "database_url", None)
    if fixture is not None and explicit_url:
        raise GraphStoreConfigurationError(
            "choose exactly one graph data source"
        )
    if fixture is not None:
        store = InMemoryGraphStore()
        load_graph_fixture(fixture, store)
        return store, GraphQueryService(store)

    url = explicit_url or os.getenv("ME_GRAPH_DATABASE_URL")
    if not url:
        raise GraphStoreConfigurationError("graph data source is required")
    engine = create_database_engine(
        url,
        production=not args.allow_test_database,
    )
    store = SqlAlchemyGraphStore(engine)
    return store, GraphQueryService(store)


def _source_register(args: argparse.Namespace) -> dict[str, object]:
    payload = _read_json(args.json)
    source_data = payload.get("source", payload)
    if not isinstance(source_data, Mapping):
        raise ValueError("source must be an object")
    fragment_values = payload.get("fragments", ())
    if not isinstance(fragment_values, list):
        raise ValueError("fragments must be an array")
    source = SourceRecord.from_dict(source_data)
    fragments = tuple(
        EvidenceFragment.from_dict(item)
        for item in fragment_values
        if isinstance(item, Mapping)
    )
    if len(fragments) != len(fragment_values):
        raise ValueError("every fragment must be an object")
    repository = SqlAlchemySourceRepository(_database_engine(args))
    registered = repository.register(source)
    accepted = repository.add_fragments(
        registered.source_id,
        fragments,
    )
    return {
        "source": registered.to_dict(),
        "fragment_count": len(accepted),
        "fragments": [item.to_dict() for item in accepted],
    }


def _source_show(args: argparse.Namespace) -> dict[str, object]:
    repository = SqlAlchemySourceRepository(_database_engine(args))
    source = repository.get(args.source_id)
    fragments = repository.list_fragments(args.source_id)
    return {
        "source": source.to_dict(),
        "fragments": [item.to_dict() for item in fragments],
    }


def _candidate_submit(args: argparse.Namespace) -> dict[str, object]:
    repository = SqlAlchemyCandidateRepository(_database_engine(args))
    return repository.submit(
        CandidateRecord.from_dict(_read_json(args.json))
    ).to_dict()


def _candidate_list(args: argparse.Namespace) -> dict[str, object]:
    repository = SqlAlchemyCandidateRepository(_database_engine(args))
    target_graph = (
        GraphNamespace(args.target_graph)
        if args.target_graph is not None
        else None
    )
    values = repository.list_pending(
        target_graph=target_graph,
        source_id=args.source_id,
        limit=args.limit,
    )
    return {
        "count": len(values),
        "candidates": [item.to_dict() for item in values],
    }


def _candidate_approve(args: argparse.Namespace) -> dict[str, object]:
    engine = _database_engine(args)
    service = PersistentReviewService(engine)
    repository = SqlAlchemyCandidateRepository(engine)
    approved = service.approve(
        args.change_id,
        args.reviewer_id,
        reviewer_kind=args.reviewer_kind,
        reason=args.reason,
    )
    return {
        "object": approved.to_dict(),
        "candidate": repository.get(args.change_id).to_dict(),
        "events": [
            event.to_dict()
            for event in repository.list_events(args.change_id)
        ],
    }


def _candidate_reject(args: argparse.Namespace) -> dict[str, object]:
    engine = _database_engine(args)
    service = PersistentReviewService(engine)
    repository = SqlAlchemyCandidateRepository(engine)
    service.reject(
        args.change_id,
        args.reviewer_id,
        args.reason,
        reviewer_kind=args.reviewer_kind,
    )
    return {
        "candidate": repository.get(args.change_id).to_dict(),
        "events": [
            event.to_dict()
            for event in repository.list_events(args.change_id)
        ],
    }


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
            upgrade_database(
                url,
                production=not args.allow_test_database,
            )
            _write({"status": "upgraded"}, sys.stdout)
            return 0

        if args.command == "import-fixture":
            url = _require_database_url(args)
            production = not args.allow_test_database
            upgrade_database(url, production=production)
            store = SqlAlchemyGraphStore(
                create_database_engine(url, production=production)
            )
            load_graph_fixture(args.fixture, store)
            _write(_summary(store), sys.stdout)
            return 0

        if args.command == "source-register":
            _write(_source_register(args), sys.stdout)
            return 0
        if args.command == "source-show":
            _write(_source_show(args), sys.stdout)
            return 0
        if args.command == "candidate-submit":
            _write(_candidate_submit(args), sys.stdout)
            return 0
        if args.command == "candidate-list":
            _write(_candidate_list(args), sys.stdout)
            return 0
        if args.command == "candidate-approve":
            _write(_candidate_approve(args), sys.stdout)
            return 0
        if args.command == "candidate-reject":
            _write(_candidate_reject(args), sys.stdout)
            return 0

        _, query = _query_source(args)
        if args.command == "project-snapshot":
            _write(
                query.get_project_snapshot(args.project_id).to_dict(),
                sys.stdout,
            )
            return 0
        if args.command == "trace-decision":
            _write(
                query.trace_decision(args.decision_id).to_dict(),
                sys.stdout,
            )
            return 0
        if args.command == "task-profile":
            _write(
                query.get_task_profile(
                    args.user_id,
                    args.project_id,
                    args.task_type,
                ).to_dict(),
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
