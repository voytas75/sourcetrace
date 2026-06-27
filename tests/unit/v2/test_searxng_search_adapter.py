import json

from sourcetrace_v2.adapters.search.searxng import SearxNGBootstrap, SearxNGSearchGateway
from sourcetrace_v2.app.composition.runtime import build_env_backed_searxng_stubbed_jsonl_runtime
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


def test_searxng_search_gateway_returns_typed_candidates(monkeypatch) -> None:
    def fake_urlopen(request, timeout=0):
        assert "format=json" in request.full_url
        assert timeout == 5
        return _FakeResponse(
            {
                "results": [
                    {"url": "https://example.test/a", "title": "Alpha", "content": "First"},
                    {"url": "https://example.test/b", "title": "Beta", "content": "Second"},
                ]
            }
        )

    monkeypatch.setattr("sourcetrace_v2.adapters.search.searxng.urlopen", fake_urlopen)
    gateway = SearxNGSearchGateway(
        bootstrap=SearxNGBootstrap(
            base_url="http://127.0.0.1:8080",
            language="en",
            timeout_seconds=5,
        )
    )

    candidates = gateway.search(
        job_id="job-search",
        run_id="run-search",
        query="test query",
        limit=2,
    )

    assert len(candidates) == 2
    assert candidates[0].provider == "searxng"
    assert candidates[0].title == "Alpha"
    assert candidates[1].rank == 2


def test_env_backed_searxng_runtime_can_drive_run_http_path(tmp_path, monkeypatch) -> None:
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

    monkeypatch.setattr("sourcetrace_v2.adapters.search.searxng.urlopen", fake_urlopen)
    monkeypatch.setenv("TEST_SEARXNG_BASE_URL", "http://127.0.0.1:8080")
    runtime = build_env_backed_searxng_stubbed_jsonl_runtime(
        base_dir=tmp_path,
        base_url_env="TEST_SEARXNG_BASE_URL",
    )

    response = handle_run_minimal_flow_request(
        job_id="job-searxng-runtime",
        run_id="run-searxng-runtime",
        seed_text="test query",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["status"] == "found"
    assert payload["artifact"]["summary"].startswith("minimal v2 flow | query=stub:research_fast:")
    assert "top_source=searxng:Alpha" in payload["artifact"]["summary"]
    assert payload["evidence_input"]["candidate_count"] == 3
    assert payload["evidence_input"]["candidates"][0]["provider"] == "searxng"
    assert payload["receipts"]["stage_count"] == 10
