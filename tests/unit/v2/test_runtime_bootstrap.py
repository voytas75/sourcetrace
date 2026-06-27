import pytest

from sourcetrace_v2.runtime.bootstrap.litellm import EnvBootstrapRequest, resolve_litellm_bootstrap_from_env


def test_resolve_litellm_bootstrap_from_env_reads_values(monkeypatch) -> None:
    monkeypatch.setenv("TEST_LLM_API_KEY", "secret")
    monkeypatch.setenv("TEST_LLM_BASE_URL", "https://example.test/openai/v1")
    monkeypatch.setenv("TEST_LLM_API_VERSION", "2024-10-21")

    bootstrap = resolve_litellm_bootstrap_from_env(
        EnvBootstrapRequest(
            api_key_env="TEST_LLM_API_KEY",
            base_url_env="TEST_LLM_BASE_URL",
            api_version_env="TEST_LLM_API_VERSION",
        )
    )

    assert bootstrap.api_key == "secret"
    assert bootstrap.base_url == "https://example.test/openai/v1"
    assert bootstrap.api_version == "2024-10-21"


def test_resolve_litellm_bootstrap_from_env_fails_fast_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("TEST_LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="missing required env var: TEST_LLM_API_KEY"):
        resolve_litellm_bootstrap_from_env(
            EnvBootstrapRequest(api_key_env="TEST_LLM_API_KEY")
        )
