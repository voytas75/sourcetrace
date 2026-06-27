import json

from sourcetrace_v2.adapters.search.unified_search import UnifiedSearchBootstrap, UnifiedSearchGateway, build_preferred_search_gateway
from sourcetrace_v2.adapters.search.searxng import SearxNGBootstrap, SearxNGSearchGateway
from sourcetrace_v2.app.composition.runtime import build_preferred_search_backed_stubbed_jsonl_runtime
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


def test_unified_search_gateway_returns_typed_candidates() -> None:
    gateway = UnifiedSearchGateway(
        bootstrap=UnifiedSearchBootstrap(
            search_web=lambda query, count=10: [
                {"url": "https://example.test/u1", "title": "Unified 1", "snippet": "One"},
                {"url": "https://example.test/u2", "title": "Unified 2", "snippet": "Two"},
            ]
        )
    )

    candidates = gateway.search(job_id="job-us", run_id="run-us", query="policy", limit=2)

    assert len(candidates) == 2
    assert candidates[0].provider == "procedural_admin_unified_search"
    assert candidates[0].title == "Unified 1"


def test_preferred_search_gateway_falls_back_to_searxng_when_unified_returns_empty(monkeypatch) -> None:
    def fake_urlopen(request, timeout=0):
        return _FakeResponse({"results": [{"url": "https://example.test/fallback", "title": "Fallback", "content": "SearxNG"}]})

    monkeypatch.setattr("sourcetrace_v2.adapters.search.searxng.urlopen", fake_urlopen)
    primary = UnifiedSearchGateway(bootstrap=UnifiedSearchBootstrap(search_web=lambda query, count=10: []))
    fallback = SearxNGSearchGateway(
        bootstrap=SearxNGBootstrap(base_url="http://127.0.0.1:8080", language="en", timeout_seconds=5)
    )
    gateway = build_preferred_search_gateway(primary=primary, fallback=fallback)

    candidates = gateway.search(job_id="job-fallback", run_id="run-fallback", query="policy", limit=1)

    assert len(candidates) == 1
    assert candidates[0].provider == "searxng"
    assert candidates[0].title == "Fallback"


def test_preferred_search_runtime_uses_unified_before_fallback(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout=0):
        return _FakeResponse({"results": [{"url": "https://example.test/fallback", "title": "Fallback", "content": "SearxNG"}]})

    monkeypatch.setattr("sourcetrace_v2.adapters.search.searxng.urlopen", fake_urlopen)
    runtime = build_preferred_search_backed_stubbed_jsonl_runtime(
        base_dir=tmp_path,
        base_url="http://127.0.0.1:8080",
        unified_search_web=lambda query, count=10: [
            {"url": "https://example.test/u1", "title": "Unified 1", "snippet": "One"},
            {"url": "https://example.test/u2", "title": "Unified 2", "snippet": "Two"},
            {"url": "https://example.test/u3", "title": "Unified 3", "snippet": "Three"},
        ],
    )

    response = handle_run_minimal_flow_request(
        job_id="job-us-runtime",
        run_id="run-us-runtime",
        seed_text="policy",
        runtime=runtime,
    )

    payload = json.loads(response.body)
    assert response.status_code == 201
    assert payload["evidence_input"]["candidate_count"] == 3
    assert payload["evidence_input"]["candidates"][0]["provider"] == "procedural_admin_unified_search"
    assert "top_source=procedural_admin_unified_search:Unified 1" in payload["artifact"]["summary"]
