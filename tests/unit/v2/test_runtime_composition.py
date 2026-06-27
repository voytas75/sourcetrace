from sourcetrace_v2.app.composition.runtime import build_env_backed_litellm_like_jsonl_runtime, build_env_backed_preferred_search_stubbed_jsonl_runtime, build_litellm_like_jsonl_runtime, build_stubbed_jsonl_runtime
from sourcetrace_v2.adapters.llm.litellm_like import LiteLikeBootstrap


def test_build_stubbed_jsonl_runtime_returns_assembled_dependencies(tmp_path) -> None:
    runtime = build_stubbed_jsonl_runtime(base_dir=tmp_path)

    assert runtime.config.deep_research.planning_profile == "planning_default"
    assert runtime.results is not None
    assert runtime.receipts is not None
    assert runtime.llm is not None
    assert runtime.search is not None
    assert runtime.logger is not None


def test_build_litellm_like_jsonl_runtime_returns_real_provider_shaped_assembly(tmp_path) -> None:
    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    runtime = build_litellm_like_jsonl_runtime(
        base_dir=tmp_path,
        completion_fn=completion_fn,
        bootstrap=LiteLikeBootstrap(api_key="x"),
    )

    assert runtime.config.deep_research.planning_profile == "planning_default"
    assert runtime.results is not None
    assert runtime.receipts is not None
    assert runtime.llm is not None
    assert runtime.search is not None
    assert runtime.logger is not None


def test_build_env_backed_litellm_like_jsonl_runtime_reads_bootstrap_from_env(tmp_path, monkeypatch) -> None:
    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    monkeypatch.setenv("TEST_LLM_API_KEY", "secret")
    monkeypatch.setenv("TEST_LLM_BASE_URL", "https://example.test/openai/v1")
    monkeypatch.setenv("TEST_LLM_API_VERSION", "2024-10-21")

    runtime = build_env_backed_litellm_like_jsonl_runtime(
        base_dir=tmp_path,
        completion_fn=completion_fn,
        api_key_env="TEST_LLM_API_KEY",
        base_url_env="TEST_LLM_BASE_URL",
        api_version_env="TEST_LLM_API_VERSION",
    )

    assert runtime.results is not None
    assert runtime.receipts is not None
    assert runtime.search is not None

    result = runtime.llm.generate(profile_name="planning_default", prompt="hello")
    assert result.text == "ok"
    assert result.input_tokens == 10
    assert result.output_tokens == 20
    assert result.total_tokens == 30


def test_build_env_backed_preferred_search_stubbed_jsonl_runtime_falls_back_without_unified(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEST_SEARXNG_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setattr(
        "sourcetrace_v2.app.composition.runtime.load_mycrewhelper_unified_search_web",
        lambda: None,
    )

    runtime = build_env_backed_preferred_search_stubbed_jsonl_runtime(
        base_dir=tmp_path,
        base_url_env="TEST_SEARXNG_BASE_URL",
    )

    assert runtime.search is not None
