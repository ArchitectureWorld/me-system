from pathlib import Path
import tomllib


def test_canonical_package_imports() -> None:
    import me_system

    assert me_system.__doc__ is not None


def test_only_brain_and_who_are_product_graph_domains() -> None:
    assert Path("src/me_system/brain").is_dir()
    assert Path("src/me_system/who").is_dir()
    assert Path("src/me_system/bridge").is_dir()
    assert not Path("services/me-core").exists()
    assert not Path("services/me-graph-core").exists()
    assert not Path("src/me_core").exists()
    assert not Path("src/me_graph_core").exists()


def test_distribution_and_commands_use_only_me_system_names() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "me-system"
    assert data["project"]["scripts"] == {
        "me-system": "me_system.cli:main",
        "me-system-mcp": "me_system.hermes.mcp_server:main",
    }
