import json

from sourcetrace_v2.app.composition.runtime import build_env_backed_live_litellm_with_searxng_jsonl_runtime
from sourcetrace_v2.app.services.http_api import handle_run_minimal_flow_request


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_env_backed_live_litellm_with_searxng_runtime_can_drive_run(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    def fake_completion(**kwargs):
        calls.append(dict(kwargs))
        return {
            "choices": [{"message": {"content": "live-ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    def fake_urlopen(request, timeout=0):
        return _FakeResponse(
            {
                "results": [
                    {"url": "https://example.test/a", "title": "Alpha", "content": "First"},
                    {"url": "https://example.test/b", "title": "Beta", "content": "Second"},
                    {"url": "https://example.test/c", "title": "Gamma", "content": "Third"},
                ]
            }
        )

    monkeypatch.setattr("sourcetrace_v2.app.composition.runtime.litellm_completion", fake_completion)
    monkeypatch.setattr("sourcetrace_v2.adapters.search.searxng.urlopen", fake_urlopen)
    monkeypatch.setenv("TEST_AZURE_API_KEY", "secret")
    monkeypatch.setenv("TEST_AZURE_API_BASE", "https://example.test/openai")
    monkeypatch.setenv("TEST_AZURE_API_VERSION", "2024-10-21")
    monkeypatch.setenv("TEST_SEARXNG_BASE_URL", "http://127.0.0.1:18080")

    runtime = build_env_backed_live_litellm_with_searxng_jsonl_runtime(
        base_dir=tmp_path,
        api_key_env="TEST_AZURE_API_KEY",
        base_url_env="TEST_AZURE_API_BASE",
        api_version_env="TEST_AZURE_API_VERSION",
        search_base_url_env="TEST_SEARXNG_BASE_URL",
    )

    response = handle_run_minimal_flow_request(
        job_id="job-live-runtime",
        run_id="run-live-runtime",
        seed_text="polish remote work obligations",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "found"
    assert payload["rollup"]["llm_calls"] == 4
    assert payload["evidence_input"]["candidate_count"] == 3
    assert calls[0]["api_key"] == "secret"
    assert calls[0]["base_url"] == "https://example.test/openai"
    assert calls[0]["api_version"] == "2024-10-21"
    assert any(call["model"] == "azure/gpt-5.4-mini" and call["temperature"] == 1.0 for call in calls)
