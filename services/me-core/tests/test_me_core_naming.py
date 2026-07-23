from pathlib import Path
import tomllib


def test_distribution_and_commands_use_me_core_names() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "me-core"
    scripts = data["project"]["scripts"]
    assert scripts["me-system"] == "me_core.cli:main"
    assert scripts["me-system-mcp"] == "me_core.hermes.mcp_server:main"
    assert scripts["me-graph"] == "me_core.cli:main"
    assert scripts["me-graph-mcp"] == "me_core.hermes.mcp_server:main"
