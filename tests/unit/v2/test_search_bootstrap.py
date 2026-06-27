import pytest

from sourcetrace_v2.runtime.bootstrap.search import SearchEnvBootstrapRequest, resolve_searxng_bootstrap_from_env


def test_resolve_searxng_bootstrap_from_env_reads_required_values(monkeypatch) -> None:
    monkeypatch.setenv("TEST_SEARXNG_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("TEST_SEARXNG_LANGUAGE", "pl")
    monkeypatch.setenv("TEST_SEARXNG_TIMEOUT", "7")

    bootstrap = resolve_searxng_bootstrap_from_env(
        SearchEnvBootstrapRequest(
            base_url_env="TEST_SEARXNG_BASE_URL",
            language_env="TEST_SEARXNG_LANGUAGE",
            timeout_env="TEST_SEARXNG_TIMEOUT",
        )
    )

    assert bootstrap.base_url == "http://127.0.0.1:8080"
    assert bootstrap.language == "pl"
    assert bootstrap.timeout_seconds == 7


def test_resolve_searxng_bootstrap_from_env_requires_base_url(monkeypatch) -> None:
    monkeypatch.delenv("TEST_SEARXNG_BASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="missing required env var: TEST_SEARXNG_BASE_URL"):
        resolve_searxng_bootstrap_from_env(
            SearchEnvBootstrapRequest(base_url_env="TEST_SEARXNG_BASE_URL")
        )
