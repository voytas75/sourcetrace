from types import SimpleNamespace
import sys
from pathlib import Path

import pytest

from sourcetrace.local_launcher import _load_runtime_pdf_capability, build_local_server_runtime
from sourcetrace.web.delivery import SourceTraceDelivery


class _FakeServer:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.server_port = 8000

    def serve_forever(self) -> None:
        self.events.append("serve_forever")

    def server_close(self) -> None:
        self.events.append("server_close")


class _FakeRuntime:
    def __init__(self) -> None:
        self.server = _FakeServer()


def fake_pdf_capability(*, pdf: str, prompt: str, pages: str = "") -> dict[str, object]:
    if pages == "1":
        return {
            "document_title": "Doc",
            "main_entity": "Entity",
            "document_scope": "Preview scope",
            "relevance_verdict": "irrelevant",
            "reason": "No match",
            "candidate_pages": [1],
            "confidence": 0.8,
        }
    return {
        "relevant": False,
        "document_scope": "Full scope",
        "entity_match_summary": "No match",
        "key_findings": [],
        "evidence_pages": [],
        "confidence": 0.8,
    }


def test_load_runtime_pdf_capability_defaults_to_openclaw_stub_when_env_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SOURCETRACE_RUNTIME_PDF_ANALYZER", raising=False)
    capability = _load_runtime_pdf_capability()
    assert capability is not None
    assert capability.__name__ == "openclaw_pdf_capability"


def test_load_runtime_pdf_capability_rejects_invalid_spec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOURCETRACE_RUNTIME_PDF_ANALYZER", "bad-spec")
    with pytest.raises(ValueError, match="module.path:callable_name"):
        _load_runtime_pdf_capability()


def test_build_local_server_runtime_accepts_env_runtime_pdf_analyzer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    captured: dict[str, object] = {}

    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "model": "gpt-5.4",
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        captured["delivery"] = delivery
        return _FakeRuntime()

    def fake_build_llm_runtime(*, completion_fn=None, config=None):
        return SimpleNamespace(
            credibility_draft=lambda text: SimpleNamespace(text="draft"),
            claim_extraction=lambda text: None,
            claim_normalization=lambda text: SimpleNamespace(text="normalized"),
            research_synthesis=lambda text: SimpleNamespace(text="## Current answer\nA\n\n## Key findings\n- B\n\n## Uncertainty\n- C\n\n## Next checks\n- D"),
        )

    monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)
    monkeypatch.setattr("sourcetrace.local_launcher.build_llm_runtime", fake_build_llm_runtime)
    monkeypatch.setenv("SOURCETRACE_LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("SOURCETRACE_LLM_BASE_URL", "https://llm.example.test")
    monkeypatch.setenv("SOURCETRACE_LLM_API_VERSION", "preview")
    monkeypatch.setenv("SOURCETRACE_SEARXNG_BASE_URL", "http://127.0.0.1:18080")
    monkeypatch.setenv(
        "SOURCETRACE_RUNTIME_PDF_ANALYZER",
        "test_local_launcher_pdf_runtime:fake_pdf_capability",
    )

    build_local_server_runtime(completion_fn=completion_fn, research_search_web=lambda query, count=3: [])

    delivery = captured["delivery"]
    assert isinstance(delivery, SourceTraceDelivery)
    assert delivery.research is not None
