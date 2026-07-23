from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.pool import StaticPool


def create_sqlite_test_engine(url: str = "sqlite+pysqlite:///:memory:") -> Engine:
    """Create a SQLite engine that mirrors graph-store transaction semantics.

    SQLite is only a repository test double. Production callers must use
    ``create_database_engine(..., production=True)``.
    """

    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if url.endswith(":memory:"):
        kwargs.update(
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    engine = create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
