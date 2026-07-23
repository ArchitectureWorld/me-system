from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "services" / "me-core"


def move(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))


def rewrite_python_imports(package: Path) -> None:
    for base in [package, ROOT / "tests", ROOT / "migrations"]:
        for path in base.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            text = text.replace("me_core.hermes", "me_system.adapters.hermes")
            text = text.replace("me_core", "me_system")
            text = text.replace("ME-Graph Core", "ME-System")
            text = text.replace("ME-Core", "ME-System")
            if package / "adapters" / "hermes" in path.parents:
                text = text.replace("from ..", "from ...")
            if base == ROOT / "tests":
                text = text.replace(".parents[3]", ".parents[1]")
            if path.name == "cli.py":
                text = text.replace('prog="me-graph"', 'prog="me-system"')
            path.write_text(text, encoding="utf-8")


def rewrite_active_documents() -> None:
    active_paths = [
        ROOT / "README.md",
        ROOT / "docs" / "architecture-status.md",
        ROOT / "docs" / "00-product-and-architecture-overview.md",
        ROOT / "docs" / "roadmap" / "recommended-development-path.md",
        ROOT / "docs" / "implementation.md",
        ROOT
        / "docs"
        / "superpowers"
        / "specs"
        / "2026-07-23-source-ledger-candidate-persistence-design.md",
        ROOT / "docs" / "adr" / "ADR-0005-single-graph-kernel.md",
        ROOT / "docs" / "competitors" / "codebase-memory-architecture-review.md",
        ROOT / "integrations" / "hermes" / "README.md",
        ROOT / "integrations" / "hermes" / "config.example.yaml",
        ROOT / "integrations" / "hermes" / "ME_SYSTEM_BOOTSTRAP.md",
    ]
    replacements = [
        ("services/me-core/src/me_core", "src/me_system"),
        ("services/me-core/tests", "tests"),
        ("services/me-core/schemas", "schemas"),
        ("services/me-core/migrations", "migrations"),
        ("services/me-core/pyproject.toml", "pyproject.toml"),
        ("services/me-core/README.md", "docs/implementation.md"),
        ("services/me-core", "repository root"),
        ("me_core.hermes", "me_system.adapters.hermes"),
        ("me_core", "me_system"),
        ("me-core", "me-system"),
        ("ME-Core", "ME-System implementation"),
        ("ME-Graph Core", "ME-System implementation"),
    ]
    for path in active_paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for old_text, new_text in replacements:
            text = text.replace(old_text, new_text)
        path.write_text(text, encoding="utf-8")

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    transitional = (
        "> 当前代码仍位于历史路径 `repository root/`。该路径只是过渡实现位置，不代表第三个产品；"
        "下一次代码整理会迁移到中性的 `shared/` 与 `me_system` 包结构。"
    )
    text = text.replace(
        transitional,
        "> 当前运行代码已经收敛到根级 `src/me_system/`。ME-Brain 与 ME-Who 是仅有的两个图谱领域；其余目录均为内部实现职责。",
    )
    text = text.replace("cd repository root", "cd <me-system-repository>")
    readme.write_text(text, encoding="utf-8")


def write_identity_tests() -> None:
    old_test = ROOT / "tests" / "test_me_core_naming.py"
    if old_test.exists():
        (ROOT / "tests" / "test_system_identity.py").write_text(
            '''from pathlib import Path\nimport tomllib\n\n\ndef test_distribution_and_commands_use_me_system_names() -> None:\n    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))\n    assert data["project"]["name"] == "me-system"\n    scripts = data["project"]["scripts"]\n    assert scripts["me-system"] == "me_system.cli:main"\n    assert scripts["me-system-mcp"] == "me_system.adapters.hermes.mcp_server:main"\n    assert scripts["me-graph"] == "me_system.cli:main"\n    assert scripts["me-graph-mcp"] == "me_system.adapters.hermes.mcp_server:main"\n''',
            encoding="utf-8",
        )
        old_test.unlink()

    (ROOT / "tests" / "test_package_identity.py").write_text(
        '''from pathlib import Path\n\n\ndef test_canonical_package_imports() -> None:\n    import me_system\n\n    assert me_system.__doc__ is not None\n\n\ndef test_active_runtime_has_no_third_core_package() -> None:\n    assert not Path("services/me-core").exists()\n    assert not Path("services/me-graph-core").exists()\n    assert not Path("src/me_core").exists()\n    assert Path("src/me_system/brain").is_dir()\n    assert Path("src/me_system/who").is_dir()\n''',
        encoding="utf-8",
    )


def rewrite_pyproject() -> None:
    path = ROOT / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    text = text.replace("me_core.hermes", "me_system.adapters.hermes")
    text = text.replace("me_core", "me_system")
    text = text.replace('name = "me-core"', 'name = "me-system"')
    text = text.replace(
        'description = "Canonical dual-graph contracts and query foundation for ME-System"',
        'description = "Persistent ME-Brain and ME-Who graph system for AI agents"',
    )
    path.write_text(text, encoding="utf-8")


def write_final_workflow() -> None:
    workflow = ROOT / ".github" / "workflows" / "me-system.yml"
    workflow.write_text(
        '''name: ME-System\n\non:\n  pull_request:\n    paths:\n      - "README.md"\n      - "docs/**"\n      - "src/**"\n      - "tests/**"\n      - "schemas/**"\n      - "migrations/**"\n      - "pyproject.toml"\n      - "alembic.ini"\n      - "examples/graph/**"\n      - "deploy/postgres/**"\n      - ".github/workflows/me-system.yml"\n  push:\n    branches: [main]\n\npermissions:\n  contents: read\n\njobs:\n  unit:\n    runs-on: ubuntu-latest\n    strategy:\n      fail-fast: false\n      matrix:\n        python-version: ["3.11", "3.12"]\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: ${{ matrix.python-version }}\n          cache: pip\n          cache-dependency-path: pyproject.toml\n      - run: python -m pip install -q -e '.[dev]'\n      - run: pytest -q --tb=short --ignore=tests/test_mcp_stdio.py --ignore=tests/test_postgres_integration.py\n      - run: python -m compileall -q src\n\n  postgres-e2e:\n    runs-on: ubuntu-latest\n    services:\n      postgres:\n        image: postgres:16\n        env:\n          POSTGRES_DB: me_graph_test\n          POSTGRES_USER: me_graph\n          POSTGRES_PASSWORD: test-password\n        ports: ["5432:5432"]\n        options: >-\n          --health-cmd "pg_isready -U me_graph -d me_graph_test"\n          --health-interval 5s\n          --health-timeout 5s\n          --health-retries 12\n    env:\n      ME_GRAPH_TEST_POSTGRES_URL: postgresql+psycopg://me_graph:test-password@127.0.0.1:5432/me_graph_test\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: "3.12"\n          cache: pip\n          cache-dependency-path: pyproject.toml\n      - run: python -m pip install -q -e '.[dev]'\n      - run: pytest -q --tb=short tests/test_postgres_integration.py tests/test_mcp_stdio.py\n''',
        encoding="utf-8",
    )


def main() -> None:
    if not OLD.exists():
        print("Unified package already applied.")
        return

    move(OLD / "README.md", ROOT / "docs" / "implementation.md")
    move(OLD / "pyproject.toml", ROOT / "pyproject.toml")
    move(OLD / "alembic.ini", ROOT / "alembic.ini")
    move(OLD / "migrations", ROOT / "migrations")
    move(OLD / "schemas", ROOT / "schemas")
    move(OLD / "tests", ROOT / "tests")
    move(OLD / "src" / "me_core", ROOT / "src" / "me_system")

    old_ignore = OLD / ".gitignore"
    root_ignore = ROOT / ".gitignore"
    if old_ignore.exists():
        existing = root_ignore.read_text(encoding="utf-8") if root_ignore.exists() else ""
        additions = old_ignore.read_text(encoding="utf-8")
        root_ignore.write_text(
            existing.rstrip() + "\n\n# Python build artifacts\n" + additions.strip() + "\n",
            encoding="utf-8",
        )

    shutil.rmtree(OLD)
    services = ROOT / "services"
    if services.exists() and not any(services.iterdir()):
        services.rmdir()

    package = ROOT / "src" / "me_system"
    adapters = package / "adapters"
    adapters.mkdir(parents=True, exist_ok=True)
    (adapters / "__init__.py").write_text(
        '"""External adapters for ME-System."""\n', encoding="utf-8"
    )
    move(package / "hermes", adapters / "hermes")

    for domain, doc in {
        "brain": "ME-Brain project and knowledge graph domain.",
        "who": "ME-Who user understanding graph domain.",
        "bridge": "Explicit cross-domain relations; not a third graph product.",
    }.items():
        target = package / domain
        target.mkdir(parents=True, exist_ok=True)
        (target / "__init__.py").write_text(f'"""{doc}"""\n', encoding="utf-8")

    rewrite_python_imports(package)
    write_identity_tests()
    rewrite_pyproject()
    rewrite_active_documents()

    migration_note = ROOT / "docs" / "migrations" / "2026-07-23-unified-package.md"
    migration_note.parent.mkdir(parents=True, exist_ok=True)
    migration_note.write_text(
        '''# Unified ME-System Package Migration\n\nThe historical runtime paths `services/me-graph-core/`, `services/me-core/`, and Python packages `me_graph_core` / `me_core` were transitional implementation names.\n\nThe canonical runtime is now `src/me_system/`. ME-Brain and ME-Who are the only product graph domains. Persistence, evidence, ingestion, review, query, and MCP are internal ME-System responsibilities.\n''',
        encoding="utf-8",
    )

    write_final_workflow()

    for temporary in [
        ROOT / ".github" / "workflows" / "me-core.yml",
        ROOT / ".github" / "workflows" / "apply-unify-refactor.yml",
        ROOT / ".github" / "workflows" / "export-unify-workspace.yml",
        ROOT / ".github" / "workflows" / "unify-package-runner.yml",
        ROOT / "scripts" / "unify_package.py",
    ]:
        if temporary.exists():
            temporary.unlink()

    scripts = ROOT / "scripts"
    if scripts.exists() and not any(scripts.iterdir()):
        scripts.rmdir()


if __name__ == "__main__":
    main()
