# PostgreSQL GraphStore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production PostgreSQL-backed `GraphStore` that preserves the existing graph contracts and query behavior, with Alembic migrations, CLI database support, and repeatable tests.

**Architecture:** Keep domain dataclasses and `GraphStore` as the public boundary. Add a SQLAlchemy-backed repository using one globally unique `graph_objects` table and an ordered `graph_evidence_refs` table. Production uses PostgreSQL through psycopg 3; SQLite is used only as a fast test backend for repository behavior, while an opt-in PostgreSQL integration test verifies the production dialect.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.0.x, Alembic 1.18.x, psycopg 3, pytest, PostgreSQL 16+, SQLite in-memory tests.

## Global Constraints

- ME-Brain and ME-Who remain the only product-level canonical graphs.
- The existing `GraphStore` protocol and `GraphQueryService` public semantics must remain compatible.
- Production database URLs must use `postgresql+psycopg://`.
- SQLite is a test double, not a supported production database.
- Agent adapters must not gain direct database access.
- Every stored graph object must retain ordered evidence references.
- Writes must be atomic across graph object and evidence rows.
- Pending candidate persistence is not part of this plan.
- No asynchronous database layer is introduced.
- No graph database extension or Cypher dependency is introduced.

---

## Planned File Structure

```text
services/me-graph-core/
├── alembic.ini
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_create_graph_store.py
├── src/me_graph_core/
│   ├── cli.py
│   ├── errors.py
│   ├── __init__.py
│   └── persistence/
│       ├── __init__.py
│       ├── database.py
│       ├── models.py
│       ├── migrations.py
│       ├── store.py
│       └── testing.py
└── tests/
    ├── store_contract.py
    ├── test_database_config.py
    ├── test_sqlalchemy_store.py
    ├── test_migrations.py
    ├── test_cli_database.py
    └── test_postgres_integration.py

deploy/postgres/
├── docker-compose.example.yml
└── .env.example
```

---

### Task 1: Add persistence dependencies and database configuration

**Files:**
- Modify: `services/me-graph-core/pyproject.toml`
- Modify: `services/me-graph-core/src/me_graph_core/errors.py`
- Create: `services/me-graph-core/src/me_graph_core/persistence/__init__.py`
- Create: `services/me-graph-core/src/me_graph_core/persistence/database.py`
- Create: `services/me-graph-core/tests/test_database_config.py`

**Interfaces:**
- Produces `create_database_engine(url: str, *, production: bool = True) -> Engine`.
- Produces `redact_database_url(url: str) -> str`.
- Produces `GraphStoreConfigurationError`, `GraphStoreUnavailableError`, and `GraphMigrationError`.

- [ ] **Step 1: Write failing URL validation tests**

```python
from me_graph_core.errors import GraphStoreConfigurationError
from me_graph_core.persistence.database import create_database_engine, redact_database_url


def test_production_engine_requires_postgresql_psycopg() -> None:
    with pytest.raises(GraphStoreConfigurationError, match="postgresql\\+psycopg"):
        create_database_engine("sqlite+pysqlite:///:memory:")


def test_redact_database_url_hides_password() -> None:
    value = redact_database_url("postgresql+psycopg://user:secret@db/me_graph")
    assert "secret" not in value
    assert "***" in value
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd services/me-graph-core
pytest tests/test_database_config.py -q
```

Expected: import failure because `persistence.database` and new errors do not exist.

- [ ] **Step 3: Add dependencies**

Update `pyproject.toml`:

```toml
[project]
dependencies = [
  "SQLAlchemy>=2.0,<2.1",
  "alembic>=1.18,<2",
  "psycopg[binary]>=3.2,<4",
]
```

- [ ] **Step 4: Implement configuration helpers**

`database.py` must:

```python
def create_database_engine(url: str, *, production: bool = True) -> Engine:
    parsed = make_url(url)
    if production and parsed.drivername != "postgresql+psycopg":
        raise GraphStoreConfigurationError(
            "production graph storage requires a postgresql+psycopg database URL"
        )
    return create_engine(parsed, pool_pre_ping=True)
```

`redact_database_url()` must use SQLAlchemy URL rendering with hidden passwords and must never echo a plaintext password in raised errors.

- [ ] **Step 5: Run the focused test and verify GREEN**

```bash
pytest tests/test_database_config.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add services/me-graph-core/pyproject.toml \
  services/me-graph-core/src/me_graph_core/errors.py \
  services/me-graph-core/src/me_graph_core/persistence \
  services/me-graph-core/tests/test_database_config.py
git commit -m "feat: add graph database configuration"
```

---

### Task 2: Define the SQLAlchemy schema

**Files:**
- Create: `services/me-graph-core/src/me_graph_core/persistence/models.py`
- Create: `services/me-graph-core/tests/test_sqlalchemy_store.py`

**Interfaces:**
- Produces `Base`, `GraphObjectRecord`, and `EvidenceRefRecord`.
- Produces `create_schema(engine: Engine) -> None` for tests only.

- [ ] **Step 1: Write failing schema creation and constraint tests**

```python
def test_schema_creates_graph_tables(sqlite_engine) -> None:
    create_schema(sqlite_engine)
    names = set(inspect(sqlite_engine).get_table_names())
    assert names == {"graph_objects", "graph_evidence_refs"}


def test_graph_object_ids_are_global(sql_store, brain_node) -> None:
    sql_store.add_node(brain_node)
    duplicate_edge = make_edge(edge_id=brain_node.id, ...)
    with pytest.raises(DuplicateGraphObjectError):
        sql_store.add_edge(duplicate_edge)
```

- [ ] **Step 2: Run and verify RED**

```bash
pytest tests/test_sqlalchemy_store.py::test_schema_creates_graph_tables -q
```

Expected: missing `models.py` and `create_schema`.

- [ ] **Step 3: Implement table mappings**

Use one `graph_objects` table with:

```python
id: Mapped[str] = mapped_column(Text, primary_key=True)
object_kind: Mapped[str] = mapped_column(String(8), nullable=False)
graph_namespace: Mapped[str] = mapped_column(String(16), nullable=False)
object_type: Mapped[str] = mapped_column(Text, nullable=False)
label: Mapped[str | None] = mapped_column(Text)
from_id: Mapped[str | None] = mapped_column(ForeignKey("graph_objects.id"))
to_id: Mapped[str | None] = mapped_column(ForeignKey("graph_objects.id"))
properties: Mapped[dict[str, object]] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
authority: Mapped[str] = mapped_column(String(32), nullable=False)
confirmation_status: Mapped[str] = mapped_column(String(32), nullable=False)
temporal_status: Mapped[str | None] = mapped_column(String(32))
confidence: Mapped[float | None] = mapped_column(Float)
valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
sensitivity: Mapped[str] = mapped_column(String(32), nullable=False)
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

Add check constraints for node/edge shape and indexes from the design spec.

`EvidenceRefRecord` must store `ordinal` and use `UniqueConstraint("object_id", "ordinal")`.

- [ ] **Step 4: Run schema tests**

```bash
pytest tests/test_sqlalchemy_store.py::test_schema_creates_graph_tables -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add services/me-graph-core/src/me_graph_core/persistence/models.py \
  services/me-graph-core/tests/test_sqlalchemy_store.py
git commit -m "feat: define persistent graph schema"
```

---

### Task 3: Implement `SqlAlchemyGraphStore` with behavior parity

**Files:**
- Create: `services/me-graph-core/src/me_graph_core/persistence/store.py`
- Create: `services/me-graph-core/src/me_graph_core/persistence/testing.py`
- Create: `services/me-graph-core/tests/store_contract.py`
- Modify: `services/me-graph-core/tests/test_store.py`
- Expand: `services/me-graph-core/tests/test_sqlalchemy_store.py`
- Modify: `services/me-graph-core/src/me_graph_core/__init__.py`

**Interfaces:**
- `SqlAlchemyGraphStore(engine: Engine)` implements `GraphStore`.
- `create_postgres_graph_store(url: str) -> SqlAlchemyGraphStore`.
- `create_sqlite_test_store() -> SqlAlchemyGraphStore`.

- [ ] **Step 1: Extract a shared store contract**

`store_contract.py` defines functions such as:

```python
def assert_store_contract(store_factory: Callable[[], GraphStore]) -> None:
    store = store_factory()
    brain = node("brain:project:lighting", GraphNamespace.ME_BRAIN)
    who = node("who:user:master", GraphNamespace.ME_WHO)
    store.add_node(brain)
    store.add_node(who)
    assert store.list_nodes(GraphNamespace.ME_BRAIN) == (brain,)
    assert store.list_nodes(GraphNamespace.ME_WHO) == (who,)
```

Individual pytest tests call the same contract against both implementations.

- [ ] **Step 2: Add failing SQL store tests**

Cover:

```text
node round trip
edge round trip
ordered evidence round trip
JSON properties round trip
datetime round trip
duplicate global ID
missing endpoint
non-Bridge cross-graph rejection
Bridge acceptance
neighbors direction/type filtering
transaction rollback when evidence insertion fails
reopen file-backed SQLite database and read existing data
```

- [ ] **Step 3: Run and verify RED**

```bash
pytest tests/test_sqlalchemy_store.py -q
```

Expected: `SqlAlchemyGraphStore` missing.

- [ ] **Step 4: Implement row conversion helpers**

Required private functions:

```python
def _node_to_record(node: GraphNode) -> GraphObjectRecord: ...
def _edge_to_record(edge: GraphEdge) -> GraphObjectRecord: ...
def _record_to_node(record, refs) -> GraphNode: ...
def _record_to_edge(record, refs) -> GraphEdge: ...
```

All reads must finish by calling `GraphNode.from_dict()` or `GraphEdge.from_dict()`.

- [ ] **Step 5: Implement atomic writes and queries**

Use:

```python
with self._session_factory.begin() as session:
    ...
```

`add_edge()` must load both endpoint rows inside the transaction, verify both are nodes, then reuse the same namespace validation as `InMemoryGraphStore`.

Translate `IntegrityError` into domain exceptions without exposing the database URL.

- [ ] **Step 6: Run store tests and full regression suite**

```bash
pytest tests/test_sqlalchemy_store.py tests/test_store.py tests/test_query.py tests/test_review.py -q
pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add services/me-graph-core/src/me_graph_core/persistence/store.py \
  services/me-graph-core/src/me_graph_core/persistence/testing.py \
  services/me-graph-core/src/me_graph_core/__init__.py \
  services/me-graph-core/tests/store_contract.py \
  services/me-graph-core/tests/test_store.py \
  services/me-graph-core/tests/test_sqlalchemy_store.py
git commit -m "feat: persist canonical graph objects"
```

---

### Task 4: Add Alembic migrations

**Files:**
- Create: `services/me-graph-core/alembic.ini`
- Create: `services/me-graph-core/migrations/env.py`
- Create: `services/me-graph-core/migrations/script.py.mako`
- Create: `services/me-graph-core/migrations/versions/0001_create_graph_store.py`
- Create: `services/me-graph-core/src/me_graph_core/persistence/migrations.py`
- Create: `services/me-graph-core/tests/test_migrations.py`

**Interfaces:**
- `upgrade_database(database_url: str) -> None`.
- `alembic_config(database_url: str) -> Config`.

- [ ] **Step 1: Write failing migration tests**

```python
def test_upgrade_database_creates_schema(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    upgrade_database(url, production=False)
    names = set(inspect(create_engine(url)).get_table_names())
    assert {"graph_objects", "graph_evidence_refs"} <= names


def test_upgrade_database_is_idempotent(tmp_path: Path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'graph.db'}"
    upgrade_database(url, production=False)
    upgrade_database(url, production=False)
```

- [ ] **Step 2: Run and verify RED**

```bash
pytest tests/test_migrations.py -q
```

Expected: migration module missing.

- [ ] **Step 3: Implement Alembic environment and initial migration**

The revision must create the same columns, checks, foreign keys, and indexes as `models.py`. `env.py` uses `Base.metadata` as `target_metadata`.

- [ ] **Step 4: Implement programmatic upgrade**

```python
def upgrade_database(database_url: str, *, production: bool = True) -> None:
    config = alembic_config(database_url, production=production)
    command.upgrade(config, "head")
```

Map Alembic/SQLAlchemy errors to `GraphMigrationError` and redact credentials.

- [ ] **Step 5: Run migration tests**

```bash
pytest tests/test_migrations.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add services/me-graph-core/alembic.ini \
  services/me-graph-core/migrations \
  services/me-graph-core/src/me_graph_core/persistence/migrations.py \
  services/me-graph-core/tests/test_migrations.py
git commit -m "feat: add graph store migrations"
```

---

### Task 5: Add database-aware CLI commands

**Files:**
- Modify: `services/me-graph-core/src/me_graph_core/cli.py`
- Modify: `services/me-graph-core/tests/test_cli.py`
- Create: `services/me-graph-core/tests/test_cli_database.py`

**Interfaces:**
- `me-graph db-upgrade --database-url <url>`
- `me-graph import-fixture --database-url <url> --fixture <path>`
- Query commands accept exactly one of `--fixture` or `--database-url`.

- [ ] **Step 1: Write failing CLI tests**

Cover:

```text
db-upgrade creates schema
import-fixture persists all namespaces
project-snapshot works after reopening store
missing data source returns error code 2
fixture + database URL together returns error code 2
password is absent from stderr
```

- [ ] **Step 2: Run and verify RED**

```bash
pytest tests/test_cli_database.py -q
```

Expected: unknown commands and options.

- [ ] **Step 3: Implement data-source resolution**

```python
def _database_url(args) -> str | None:
    return args.database_url or os.getenv("ME_GRAPH_DATABASE_URL")


def _load_source(args) -> tuple[GraphStore, GraphQueryService]:
    if args.fixture and _database_url(args):
        raise GraphStoreConfigurationError("choose exactly one graph data source")
    ...
```

`import-fixture` must run migrations before loading the fixture and must fail on duplicate import rather than silently overwrite canonical objects.

- [ ] **Step 4: Run CLI and full tests**

```bash
pytest tests/test_cli.py tests/test_cli_database.py -q
pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add services/me-graph-core/src/me_graph_core/cli.py \
  services/me-graph-core/tests/test_cli.py \
  services/me-graph-core/tests/test_cli_database.py
git commit -m "feat: add persistent graph CLI"
```

---

### Task 6: Add deployment kit and optional PostgreSQL integration test

**Files:**
- Create: `deploy/postgres/docker-compose.example.yml`
- Create: `deploy/postgres/.env.example`
- Modify: `services/me-graph-core/README.md`
- Modify: `README.md`
- Create: `services/me-graph-core/tests/test_postgres_integration.py`

**Interfaces:**
- `ME_GRAPH_DATABASE_URL` production configuration.
- `ME_GRAPH_TEST_POSTGRES_URL` opt-in test configuration.

- [ ] **Step 1: Write the opt-in integration test**

```python
POSTGRES_URL = os.getenv("ME_GRAPH_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="ME_GRAPH_TEST_POSTGRES_URL is not configured")


def test_postgres_round_trip_lighting_fixture() -> None:
    upgrade_database(POSTGRES_URL)
    store = create_postgres_graph_store(POSTGRES_URL)
    load_graph_fixture(FIXTURE, store)
    snapshot = GraphQueryService(store).get_project_snapshot("brain:project:lighting-platform")
    assert "brain:decision:radiance-primary" in {node.id for node in snapshot.nodes}
    assert "brain:decision:cycles-primary" in snapshot.excluded["superseded"]
```

Use a unique PostgreSQL schema or disposable test database so the test cannot modify production data.

- [ ] **Step 2: Add Docker Compose example**

The Compose file must use variable interpolation:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ${ME_GRAPH_POSTGRES_DB}
      POSTGRES_USER: ${ME_GRAPH_POSTGRES_USER}
      POSTGRES_PASSWORD: ${ME_GRAPH_POSTGRES_PASSWORD}
    volumes:
      - me_graph_postgres:/var/lib/postgresql/data
```

No real password is committed.

- [ ] **Step 3: Document startup and acceptance commands**

Document:

```bash
me-graph db-upgrade
me-graph import-fixture --fixture ../../examples/graph/lighting-platform.json
me-graph project-snapshot --project-id brain:project:lighting-platform
```

with `ME_GRAPH_DATABASE_URL` set.

- [ ] **Step 4: Run all available verification**

```bash
pytest -q
python -m compileall -q src
```

If a PostgreSQL URL is available:

```bash
ME_GRAPH_TEST_POSTGRES_URL=... pytest tests/test_postgres_integration.py -q
```

Otherwise report the integration test as skipped, not passed.

- [ ] **Step 5: Commit**

```bash
git add deploy/postgres \
  README.md \
  services/me-graph-core/README.md \
  services/me-graph-core/tests/test_postgres_integration.py
git commit -m "docs: add PostgreSQL graph deployment"
```

---

### Task 7: Final verification and pull request

**Files:**
- Review all modified files.
- Update: `docs/architecture-status.md` only if the implementation is verified.

- [ ] **Step 1: Run the complete suite**

```bash
cd services/me-graph-core
pytest -q
python -m compileall -q src
```

Expected: zero failures; PostgreSQL integration is either explicitly passed or explicitly skipped.

- [ ] **Step 2: Run SQLite persistence acceptance**

```bash
DB="sqlite+pysqlite:////tmp/me-graph-acceptance.db"
me-graph db-upgrade --database-url "$DB" --allow-test-database
me-graph import-fixture --database-url "$DB" --allow-test-database \
  --fixture ../../examples/graph/lighting-platform.json
me-graph project-snapshot --database-url "$DB" --allow-test-database \
  --project-id brain:project:lighting-platform
```

Expected: current snapshot contains Radiance and excludes Cycles.

- [ ] **Step 3: Scan for secrets and contradictory architecture**

```bash
grep -R "postgresql+psycopg://.*:.*@" -n . --exclude='*.md' || true
grep -R "ME-Reader.*第三" -n README.md docs || true
```

Expected: no committed credential and no revived third product line.

- [ ] **Step 4: Create a Draft PR**

Title:

```text
持久化双图谱到 PostgreSQL GraphStore
```

Body must state:

- storage schema;
- behavior parity;
- migrations;
- CLI commands;
- local test result;
- real PostgreSQL integration result or explicit skip;
- next step is Hermes read-only MCP.
