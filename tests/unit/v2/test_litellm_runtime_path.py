import json

from sourcetrace_v2.adapters.llm.litellm_like import LiteLikeBootstrap
from sourcetrace_v2.app.composition.runtime import build_env_backed_litellm_like_jsonl_runtime, build_litellm_like_jsonl_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request


def test_litellm_like_runtime_can_drive_run_http_path(tmp_path) -> None:
    def completion_fn(**kwargs: object) -> dict[str, object]:
        model = kwargs.get("model")
        return {
            "choices": [{"message": {"content": f"ok:{model}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        }

    runtime = build_litellm_like_jsonl_runtime(
        base_dir=tmp_path,
        completion_fn=completion_fn,
        bootstrap=LiteLikeBootstrap(api_key="x"),
    )

    response = handle_run_minimal_flow_request(
        job_id="job-lite-runtime",
        run_id="run-lite-runtime",
        seed_text="test query",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "found"
    assert payload["artifact"]["present"] is True
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["rollup"]["total_tokens"] == 132
    assert payload["receipts"]["llm"][0]["provider"] == "azure"


def test_env_backed_litellm_like_runtime_can_drive_run_http_path(tmp_path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def completion_fn(**kwargs: object) -> dict[str, object]:
        calls.append(dict(kwargs))
        model = kwargs.get("model")
        return {
            "choices": [{"message": {"content": f"ok:{model}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 8, "total_tokens": 15},
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

    response = handle_run_minimal_flow_request(
        job_id="job-env-lite-runtime",
        run_id="run-env-lite-runtime",
        seed_text="test query",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "found"
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["rollup"]["total_tokens"] == 60
    assert calls[0]["model"] == "azure/gpt-5.4"
    assert calls[0]["api_key"] == "secret"
    assert calls[0]["base_url"] == "https://example.test/openai/v1"
    assert calls[0]["api_version"] == "2024-10-21"
