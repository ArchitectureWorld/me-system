from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, inspect

from me_graph_core.cli import main


FIXTURE = Path(__file__).resolve().parents[3] / "examples" / "graph" / "lighting-platform.json"


def payload(text: str) -> dict[str, object]:
    return json.loads(text)


def test_db_upgrade_creates_schema(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("ME_GRAPH_DATABASE_URL", raising=False)
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    code = main(["db-upgrade", "--database-url", url, "--allow-test-database"])
    assert code == 0
    assert payload(capsys.readouterr().out)["status"] == "upgraded"
    assert "graph_objects" in inspect(create_engine(url)).get_table_names()


def test_import_fixture_then_query_after_reopening(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.delenv("ME_GRAPH_DATABASE_URL", raising=False)
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    assert main(
        [
            "import-fixture",
            "--database-url",
            url,
            "--allow-test-database",
            "--fixture",
            str(FIXTURE),
        ]
    ) == 0
    imported = payload(capsys.readouterr().out)
    assert imported["nodes"] == {"me_brain": 10, "me_who": 5}
    assert imported["edges"] == {"bridge": 1, "me_brain": 12, "me_who": 4}

    assert main(
        [
            "project-snapshot",
            "--database-url",
            url,
            "--allow-test-database",
            "--project-id",
            "brain:project:lighting-platform",
        ]
    ) == 0
    snapshot = payload(capsys.readouterr().out)
    ids = {item["id"] for item in snapshot["nodes"]}
    assert "brain:decision:radiance-primary" in ids
    assert "brain:decision:cycles-primary" not in ids
    assert snapshot["excluded"]["superseded"] == ["brain:decision:cycles-primary"]


def test_query_requires_a_data_source(capsys, monkeypatch) -> None:
    monkeypatch.delenv("ME_GRAPH_DATABASE_URL", raising=False)
    code = main(["project-snapshot", "--project-id", "brain:project:lighting-platform"])
    assert code == 2
    assert "data source" in payload(capsys.readouterr().err)["error"]


def test_query_rejects_fixture_and_database_url_together(tmp_path: Path, capsys) -> None:
    code = main(
        [
            "project-snapshot",
            "--fixture",
            str(FIXTURE),
            "--database-url",
            f"sqlite+pysqlite:///{tmp_path / 'graph.db'}",
            "--allow-test-database",
            "--project-id",
            "brain:project:lighting-platform",
        ]
    )
    assert code == 2
    assert "exactly one" in payload(capsys.readouterr().err)["error"]


def test_fixture_query_is_not_overridden_by_database_environment(capsys, monkeypatch) -> None:
    monkeypatch.setenv("ME_GRAPH_DATABASE_URL", "postgresql+psycopg://user:secret@missing/db")
    code = main(
        [
            "project-snapshot",
            "--fixture",
            str(FIXTURE),
            "--project-id",
            "brain:project:lighting-platform",
        ]
    )
    assert code == 0
    snapshot = payload(capsys.readouterr().out)
    assert snapshot["root_ids"] == ["brain:project:lighting-platform"]
