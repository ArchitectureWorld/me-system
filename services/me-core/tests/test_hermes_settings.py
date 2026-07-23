from __future__ import annotations

import pytest

from me_core.errors import HermesConfigurationError
from me_core.hermes.settings import HermesServerSettings


def valid_env() -> dict[str, str]:
    return {
        "ME_GRAPH_DATABASE_URL": (
            "postgresql+psycopg://user:secret@db/me_graph"
        ),
        "ME_GRAPH_HERMES_USER_ID": "who:user:master",
        "ME_GRAPH_ALLOWED_PROJECT_IDS": (
            "brain:project:lighting-platform"
        ),
    }


def test_settings_require_database_user_and_allowlist() -> None:
    for key in valid_env():
        env = valid_env()
        del env[key]
        with pytest.raises(HermesConfigurationError):
            HermesServerSettings.from_env(env)


def test_settings_parse_explicit_allowlist() -> None:
    value = HermesServerSettings.from_env(valid_env())
    assert value.allowed_project_ids == frozenset(
        {"brain:project:lighting-platform"}
    )
    assert value.max_subgraph_depth == 2


def test_settings_support_explicit_all_projects() -> None:
    env = valid_env()
    env["ME_GRAPH_ALLOWED_PROJECT_IDS"] = "*"
    assert HermesServerSettings.from_env(env).allowed_project_ids is None


def test_settings_reject_depth_above_three() -> None:
    env = valid_env()
    env["ME_GRAPH_MAX_SUBGRAPH_DEPTH"] = "4"
    with pytest.raises(HermesConfigurationError, match="between 0 and 3"):
        HermesServerSettings.from_env(env)


def test_configuration_errors_do_not_echo_database_password() -> None:
    env = valid_env()
    env["ME_GRAPH_HERMES_USER_ID"] = "invalid"
    with pytest.raises(HermesConfigurationError) as exc:
        HermesServerSettings.from_env(env)
    assert "secret" not in str(exc.value)
