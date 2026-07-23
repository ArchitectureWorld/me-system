from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .runner import run_acceptance
from .server import ExperienceApplication, create_server


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m me_system.experience",
        description="Run the local ME-System novice one-click acceptance dashboard.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("ME_GRAPH_DATABASE_URL"),
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=_project_root() / "examples" / "graph" / "lighting-platform.json",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-mcp", action="store_true")
    parser.add_argument("--allow-test-database", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.database_url:
        _parser().error("--database-url or ME_GRAPH_DATABASE_URL is required")
    application = ExperienceApplication(
        lambda: run_acceptance(
            args.database_url,
            args.fixture,
            include_mcp=not args.no_mcp,
            allow_test_database=args.allow_test_database,
        )
    )
    server = create_server(args.host, args.port, application)
    print(
        f"ME-System 一键体验验收已启动：http://localhost:{server.server_port}",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
