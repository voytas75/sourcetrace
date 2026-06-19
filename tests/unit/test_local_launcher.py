from dataclasses import dataclass
from datetime import UTC, datetime
from os import environ
from pathlib import Path
from sys import executable
from types import SimpleNamespace

import pytest

from sourcetrace.domain import Document, DocumentChunk
from sourcetrace.local_launcher import (
    _missing_litellm_completion,
    _resolve_continuity_pack_root_dir,
    _resolve_server_bind,
    build_local_server_runtime,
    main,
)
from sourcetrace.web.delivery import SourceTraceDelivery
from sourcetrace.www_control import main as www_control_main, start_main, status_main, stop_main, wait_main


@dataclass
class _FakeServer:
    events: list[str]
    server_port: int = 8000

    def serve_forever(self) -> None:
        self.events.append("serve_forever")

    def server_close(self) -> None:
        self.events.append("server_close")


@dataclass
class _FakeRuntime:
    server: _FakeServer


def test_missing_litellm_completion_raises_clear_error() -> None:
    with pytest.raises(RuntimeError, match="LiteLLM completion function is not wired yet"):
        _missing_litellm_completion(model="azure/gpt-5")


def test_resolve_server_bind_uses_defaults_when_env_is_missing() -> None:
    original_host = environ.get("SOURCETRACE_WWW_HOST")
    original_port = environ.get("SOURCETRACE_WWW_PORT")
    try:
        environ.pop("SOURCETRACE_WWW_HOST", None)
        environ.pop("SOURCETRACE_WWW_PORT", None)

        assert _resolve_server_bind() == ("127.0.0.1", 8000)
    finally:
        if original_host is None:
            environ.pop("SOURCETRACE_WWW_HOST", None)
        else:
            environ["SOURCETRACE_WWW_HOST"] = original_host
        if original_port is None:
            environ.pop("SOURCETRACE_WWW_PORT", None)
        else:
            environ["SOURCETRACE_WWW_PORT"] = original_port


def test_resolve_server_bind_uses_env_override() -> None:
    original_host = environ.get("SOURCETRACE_WWW_HOST")
    original_port = environ.get("SOURCETRACE_WWW_PORT")
    try:
        environ["SOURCETRACE_WWW_HOST"] = "0.0.0.0"
        environ["SOURCETRACE_WWW_PORT"] = "8002"

        assert _resolve_server_bind() == ("0.0.0.0", 8002)
    finally:
        if original_host is None:
            environ.pop("SOURCETRACE_WWW_HOST", None)
        else:
            environ["SOURCETRACE_WWW_HOST"] = original_host
        if original_port is None:
            environ.pop("SOURCETRACE_WWW_PORT", None)
        else:
            environ["SOURCETRACE_WWW_PORT"] = original_port


def test_resolve_continuity_pack_root_dir_returns_none_when_env_is_missing() -> None:
    original_root_dir = environ.get("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR")
    try:
        environ.pop("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR", None)

        assert _resolve_continuity_pack_root_dir() is None
    finally:
        if original_root_dir is None:
            environ.pop("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR", None)
        else:
            environ["SOURCETRACE_CONTINUITY_PACK_ROOT_DIR"] = original_root_dir


def test_resolve_continuity_pack_root_dir_uses_env_override(tmp_path: Path) -> None:
    original_root_dir = environ.get("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR")
    root_dir = tmp_path / "continuity-pack-store"
    try:
        environ["SOURCETRACE_CONTINUITY_PACK_ROOT_DIR"] = str(root_dir)

        assert _resolve_continuity_pack_root_dir() == root_dir.resolve()
    finally:
        if original_root_dir is None:
            environ.pop("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR", None)
        else:
            environ["SOURCETRACE_CONTINUITY_PACK_ROOT_DIR"] = original_root_dir


def test_resolve_continuity_pack_root_dir_rejects_file_path(tmp_path: Path) -> None:
    original_root_dir = environ.get("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR")
    file_path = tmp_path / "continuity-pack.json"
    file_path.write_text("{}", encoding="utf-8")
    try:
        environ["SOURCETRACE_CONTINUITY_PACK_ROOT_DIR"] = str(file_path)

        with pytest.raises(
            ValueError,
            match="SOURCETRACE_CONTINUITY_PACK_ROOT_DIR must point to a directory.",
        ):
            _resolve_continuity_pack_root_dir()
    finally:
        if original_root_dir is None:
            environ.pop("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR", None)
        else:
            environ["SOURCETRACE_CONTINUITY_PACK_ROOT_DIR"] = original_root_dir



def test_build_local_server_runtime_raises_clear_error_when_no_completion_backend_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "sourcetrace.local_launcher._load_litellm_completion",
        lambda: None,
    )

    with pytest.raises(RuntimeError, match="LiteLLM is not installed in the local launcher environment"):
        build_local_server_runtime()


def test_build_local_server_runtime_sets_litellm_log_error_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_litellm_log = environ.get("LITELLM_LOG")
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")

    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "model": "gpt-5.4",
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ.pop("LITELLM_LOG", None)
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        environ["SOURCETRACE_LLM_API_VERSION"] = "preview"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)

        build_local_server_runtime(completion_fn=completion_fn)

        assert environ["LITELLM_LOG"] == "ERROR"
    finally:
        if original_litellm_log is None:
            environ.pop("LITELLM_LOG", None)
        else:
            environ["LITELLM_LOG"] = original_litellm_log
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
        if original_api_version is None:
            environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        else:
            environ["SOURCETRACE_LLM_API_VERSION"] = original_api_version
        environ.pop("SOURCETRACE_WWW_HOST", None)
        environ.pop("SOURCETRACE_WWW_PORT", None)


def test_build_local_server_runtime_preserves_existing_litellm_log_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_litellm_log = environ.get("LITELLM_LOG")
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")

    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "model": "gpt-5.4",
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ["LITELLM_LOG"] = "DEBUG"
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        environ["SOURCETRACE_LLM_API_VERSION"] = "preview"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)

        build_local_server_runtime(completion_fn=completion_fn)

        assert environ["LITELLM_LOG"] == "DEBUG"
    finally:
        if original_litellm_log is None:
            environ.pop("LITELLM_LOG", None)
        else:
            environ["LITELLM_LOG"] = original_litellm_log
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
        if original_api_version is None:
            environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        else:
            environ["SOURCETRACE_LLM_API_VERSION"] = original_api_version


def test_build_local_server_runtime_uses_litellm_completion_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured["completion_kwargs"] = kwargs
        return {
            "model": kwargs["model"],
            "choices": [
                {
                    "message": {"content": "Credibility draft from local launcher."},
                    "finish_reason": "stop",
                }
            ],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        captured["delivery"] = delivery
        captured["announce"] = announce
        captured["host"] = host
        captured["port"] = port
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        environ["SOURCETRACE_LLM_API_VERSION"] = "preview"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)
        monkeypatch.setattr(
            "sourcetrace.local_launcher._load_litellm_completion",
            lambda: completion_fn,
        )

        runtime = build_local_server_runtime()
        delivery = captured["delivery"]
        assert isinstance(delivery, SourceTraceDelivery)
        delivery.persistence.documents.save_document(
            Document(
                document_id="doc-1",
                case_id="case-1",
                source_type="url",
                source_url="https://example.test/report",
                publisher="Example News",
                author="Analyst",
                title="Network report",
                published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
                retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
                content_hash="sha256:abc123",
                language="en",
            )
        )

        outcome = delivery.assess_document_credibility(
            "doc-1",
            assessment_method="llm_draft_v1",
        )
        completion_kwargs = captured["completion_kwargs"]
        assert isinstance(completion_kwargs, dict)

        assert runtime.server.server_port == 8000
        assert captured["host"] == "127.0.0.1"
        assert captured["port"] == 8000
        assert completion_kwargs["model"] == "azure/gpt-5.4"
        assert completion_kwargs["temperature"] == 0.2
        assert completion_kwargs["max_completion_tokens"] == 600
        assert completion_kwargs["api_key"] == "test-api-key"
        assert completion_kwargs["base_url"] == "https://llm.example.test"
        assert completion_kwargs["api_version"] == "preview"
        assert isinstance(completion_kwargs["messages"], list)
        assert "doc-1" in completion_kwargs["messages"][0]["content"]
        assert outcome is not None
        assert outcome.assessment.notes == "Credibility draft from local launcher."
    finally:
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
        if original_api_version is None:
            environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        else:
            environ["SOURCETRACE_LLM_API_VERSION"] = original_api_version


def test_build_local_server_runtime_uses_legacy_azure_env_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")
    original_legacy_api_key = environ.get("AZURE_OPENAI_API_KEY")
    original_legacy_base_url = environ.get("AZURE_OPENAI_BASE_URL")
    original_legacy_api_version = environ.get("AZURE_OPENAI_API_VERSION")

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured["completion_kwargs"] = kwargs
        return {
            "model": kwargs["model"],
            "choices": [
                {
                    "message": {"content": "Credibility draft from local launcher."},
                    "finish_reason": "stop",
                }
            ],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        captured["delivery"] = delivery
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ.pop("SOURCETRACE_LLM_API_KEY", None)
        environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        environ["AZURE_OPENAI_API_KEY"] = "legacy-test-api-key"
        environ["AZURE_OPENAI_BASE_URL"] = "https://legacy-llm.example.test"
        environ["AZURE_OPENAI_API_VERSION"] = "preview"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)

        runtime = build_local_server_runtime(completion_fn=completion_fn)
        delivery = captured["delivery"]
        assert isinstance(delivery, SourceTraceDelivery)
        delivery.persistence.documents.save_document(
            Document(
                document_id="doc-legacy-1",
                case_id="case-legacy-1",
                source_type="url",
                source_url="https://example.test/report",
                publisher="Example News",
                author="Analyst",
                title="Network report",
                published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
                retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
                content_hash="sha256:abc123",
                language="en",
            )
        )

        outcome = delivery.assess_document_credibility(
            "doc-legacy-1",
            assessment_method="llm_draft_v1",
        )
        completion_kwargs = captured["completion_kwargs"]
        assert isinstance(completion_kwargs, dict)

        assert runtime.server.server_port == 8000
        assert completion_kwargs["api_key"] == "legacy-test-api-key"
        assert completion_kwargs["base_url"] == "https://legacy-llm.example.test"
        assert completion_kwargs["api_version"] == "preview"
        assert outcome.assessment.notes == "Credibility draft from local launcher."
    finally:
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
        if original_api_version is None:
            environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        else:
            environ["SOURCETRACE_LLM_API_VERSION"] = original_api_version
        if original_legacy_api_key is None:
            environ.pop("AZURE_OPENAI_API_KEY", None)
        else:
            environ["AZURE_OPENAI_API_KEY"] = original_legacy_api_key
        if original_legacy_base_url is None:
            environ.pop("AZURE_OPENAI_BASE_URL", None)
        else:
            environ["AZURE_OPENAI_BASE_URL"] = original_legacy_base_url
        if original_legacy_api_version is None:
            environ.pop("AZURE_OPENAI_API_VERSION", None)
        else:
            environ["AZURE_OPENAI_API_VERSION"] = original_legacy_api_version


def test_build_local_server_runtime_uses_smoke_claim_extraction_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    original_stub_flag = environ.get("SOURCETRACE_CI_SMOKE_STUB_CLAIM_EXTRACTION")
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured["completion_kwargs"] = kwargs
        return {
            "model": kwargs["model"],
            "choices": [
                {
                    "message": {"content": "Credibility draft from local launcher."},
                    "finish_reason": "stop",
                }
            ],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        captured["delivery"] = delivery
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ["SOURCETRACE_CI_SMOKE_STUB_CLAIM_EXTRACTION"] = "1"
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        environ["SOURCETRACE_LLM_API_VERSION"] = "preview"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)

        runtime = build_local_server_runtime(completion_fn=completion_fn)
        delivery = captured["delivery"]
        assert isinstance(delivery, SourceTraceDelivery)
        assert runtime.server.server_port == 8000

        document = Document(
            document_id="doc-smoke-1",
            case_id="case-smoke-1",
            source_type="url",
            source_url="https://example.test/report",
            publisher="Example News",
            author="Analyst",
            title="Network report",
            published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
            retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
            content_hash="sha256:abc123",
            language="en",
        )
        delivery.persistence.documents.save_document(document)
        chunks = delivery.persistence.documents.save_chunks(
            (
                DocumentChunk(
                    chunk_id="doc-smoke-1:chunk-1",
                    case_id="case-smoke-1",
                    document_id="doc-smoke-1",
                    raw_text="OpenAI announced a major partnership with Example University.",
                    start_char=0,
                    end_char=61,
                    chunk_index=0,
                    position_reference="p1",
                ),
            )
        )
        outcome = delivery.extract_claims("doc-smoke-1", extraction_method="llm_v1")

        assert outcome is not None
        assert len(outcome.claims) == 1
        assert outcome.claims[0].exact_text == "OpenAI announced a major partnership with Example University"
        assert outcome.dropped_claim_items == 0
        assert outcome.review_cautions == ("ci_smoke_stub_claim_extraction",)
        assert outcome.evidence_links[0].snippet == chunks[0].raw_text
    finally:
        if original_stub_flag is None:
            environ.pop("SOURCETRACE_CI_SMOKE_STUB_CLAIM_EXTRACTION", None)
        else:
            environ["SOURCETRACE_CI_SMOKE_STUB_CLAIM_EXTRACTION"] = original_stub_flag
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
        if original_api_version is None:
            environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        else:
            environ["SOURCETRACE_LLM_API_VERSION"] = original_api_version


def test_build_local_server_runtime_uses_smoke_credibility_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    original_stub_flag = environ.get("SOURCETRACE_CI_SMOKE_STUB_CREDIBILITY")
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured["completion_kwargs"] = kwargs
        return {
            "model": kwargs["model"],
            "choices": [
                {
                    "message": {"content": "Credibility draft from local launcher."},
                    "finish_reason": "stop",
                }
            ],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        captured["delivery"] = delivery
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ["SOURCETRACE_CI_SMOKE_STUB_CREDIBILITY"] = "1"
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        environ["SOURCETRACE_LLM_API_VERSION"] = "preview"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)

        runtime = build_local_server_runtime(completion_fn=completion_fn)
        delivery = captured["delivery"]
        assert isinstance(delivery, SourceTraceDelivery)
        assert runtime.server.server_port == 8000

        delivery.persistence.documents.save_document(
            Document(
                document_id="doc-smoke-cred-1",
                case_id="case-smoke-cred-1",
                source_type="url",
                source_url="https://example.test/report",
                publisher="Example News",
                author="Analyst",
                title="Network report",
                published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
                retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
                content_hash="sha256:abc123",
                language="en",
            )
        )
        outcome = delivery.assess_document_credibility(
            "doc-smoke-cred-1",
            assessment_method="llm_draft_v1",
        )

        assert outcome is not None
        assert outcome.assessment.summary == "Looks plausible."
        assert outcome.assessment.notes == "CI smoke stub credibility assessment."
        assert outcome.assessment.method == "llm_draft_v1"
        assert outcome.assessment.source_reliability.value == "medium"
        assert outcome.assessment.information_credibility.value == "medium"
        assert outcome.assessment.provenance_distance.value == "unknown"
        assert "completion_kwargs" not in captured
    finally:
        if original_stub_flag is None:
            environ.pop("SOURCETRACE_CI_SMOKE_STUB_CREDIBILITY", None)
        else:
            environ["SOURCETRACE_CI_SMOKE_STUB_CREDIBILITY"] = original_stub_flag
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
        if original_api_version is None:
            environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        else:
            environ["SOURCETRACE_LLM_API_VERSION"] = original_api_version


def test_build_local_server_runtime_wires_runtime_config_into_delivery_and_server(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")
    original_continuity_pack_root_dir = environ.get("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR")

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured["completion_kwargs"] = kwargs
        return {
            "model": kwargs["model"],
            "choices": [
                {
                    "message": {"content": "Credibility draft from local launcher."},
                    "finish_reason": "stop",
                }
            ],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        captured["delivery"] = delivery
        captured["announce"] = announce
        captured["host"] = host
        captured["port"] = port
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        environ["SOURCETRACE_LLM_API_VERSION"] = "preview"
        environ["SOURCETRACE_WWW_HOST"] = "0.0.0.0"
        environ["SOURCETRACE_WWW_PORT"] = "8002"
        environ["SOURCETRACE_CONTINUITY_PACK_ROOT_DIR"] = "/tmp/source-trace-continuity"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)

        runtime = build_local_server_runtime(completion_fn=completion_fn)
        delivery = captured["delivery"]
        assert isinstance(delivery, SourceTraceDelivery)
        assert delivery.persistence.cases.__class__.__name__ == "FileBackedCaseRepository"
        delivery.persistence.documents.save_document(
            Document(
                document_id="doc-1",
                case_id="case-1",
                source_type="url",
                source_url="https://example.test/report",
                publisher="Example News",
                author="Analyst",
                title="Network report",
                published_at=datetime(2026, 5, 18, 0, 0, tzinfo=UTC),
                retrieved_at=datetime(2026, 5, 18, 0, 5, tzinfo=UTC),
                content_hash="sha256:abc123",
                language="en",
            )
        )

        outcome = delivery.assess_document_credibility(
            "doc-1",
            assessment_method="llm_draft_v1",
        )
        completion_kwargs = captured["completion_kwargs"]
        assert isinstance(completion_kwargs, dict)

        assert runtime.server.server_port == 8000
        assert captured["host"] == "0.0.0.0"
        assert captured["port"] == 8002
        assert completion_kwargs["model"] == "azure/gpt-5.4"
        assert completion_kwargs["temperature"] == 0.2
        assert completion_kwargs["max_completion_tokens"] == 600
        assert completion_kwargs["api_key"] == "test-api-key"
        assert completion_kwargs["base_url"] == "https://llm.example.test"
        assert completion_kwargs["api_version"] == "preview"
        assert isinstance(completion_kwargs["messages"], list)
        assert "doc-1" in completion_kwargs["messages"][0]["content"]
        assert outcome is not None
        assert outcome.assessment.notes == "Credibility draft from local launcher."
    finally:
        if original_api_key is None:
            environ.pop("SOURCETRACE_LLM_API_KEY", None)
        else:
            environ["SOURCETRACE_LLM_API_KEY"] = original_api_key
        if original_base_url is None:
            environ.pop("SOURCETRACE_LLM_BASE_URL", None)
        else:
            environ["SOURCETRACE_LLM_BASE_URL"] = original_base_url
        if original_api_version is None:
            environ.pop("SOURCETRACE_LLM_API_VERSION", None)
        else:
            environ["SOURCETRACE_LLM_API_VERSION"] = original_api_version
        if original_continuity_pack_root_dir is None:
            environ.pop("SOURCETRACE_CONTINUITY_PACK_ROOT_DIR", None)
        else:
            environ["SOURCETRACE_CONTINUITY_PACK_ROOT_DIR"] = original_continuity_pack_root_dir


def test_main_serves_and_closes_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(
        "sourcetrace.local_launcher.build_local_server_runtime",
        lambda: _FakeRuntime(server=_FakeServer(events=events)),
    )

    assert main() == 0
    assert events == ["serve_forever", "server_close"]


def test_www_start_main_writes_pid_file_and_preserves_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pid_file = tmp_path / "www.pid"
    log_file = tmp_path / "www.log"
    captured: dict[str, object] = {}

    class _FakeProcess:
        pid = 42424

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _FakeProcess()

    monkeypatch.setattr("sourcetrace.www_control.Popen", fake_popen)
    monkeypatch.setattr("sourcetrace.www_control._process_exists", lambda pid: False)
    monkeypatch.setenv("SOURCETRACE_LLM_API_KEY", "from-env")

    exit_code = start_main([
        "--pid-file",
        str(pid_file),
        "--log-file",
        str(log_file),
    ])

    out = capsys.readouterr().out
    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    env = kwargs["env"]
    assert isinstance(env, dict)

    assert exit_code == 0
    assert pid_file.read_text(encoding="utf-8") == "42424\n"
    assert captured["command"] == [executable, "-m", "sourcetrace.local_launcher"]
    assert env["SOURCETRACE_LLM_API_KEY"] == "from-env"
    assert env["PYTHONPATH"].endswith("/src")
    assert "Started Sourcetrace WWW (local-launcher) with PID 42424." in out


def test_www_stop_main_removes_stale_pid_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pid_file = tmp_path / "www.pid"
    pid_file.write_text("52525\n", encoding="utf-8")
    monkeypatch.setattr("sourcetrace.www_control._process_exists", lambda pid: False)

    exit_code = stop_main(["--pid-file", str(pid_file)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert not pid_file.exists()
    assert "Stale PID file removed" in out


def test_www_status_main_reports_running_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pid_file = tmp_path / "www.pid"
    pid_file.write_text("60606\n", encoding="utf-8")
    monkeypatch.setattr("sourcetrace.www_control._process_exists", lambda pid: True)
    monkeypatch.setattr("sourcetrace.www_control._http_ready", lambda host, port, timeout_seconds=0.5: True)

    exit_code = status_main([
        "--pid-file",
        str(pid_file),
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "running" in out
    assert "ready=yes" in out


def test_www_status_main_reports_missing_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pid_file = tmp_path / "www.pid"
    monkeypatch.setattr("sourcetrace.www_control._process_exists", lambda pid: False)

    exit_code = status_main(["--pid-file", str(pid_file)])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "not running" in out


def test_www_wait_main_succeeds_when_ready(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    attempts = {"count": 0}

    def fake_ready(host: str, port: int, timeout_seconds: float = 0.5) -> bool:
        attempts["count"] += 1
        return attempts["count"] >= 2

    monkeypatch.setattr("sourcetrace.www_control._http_ready", fake_ready)

    exit_code = wait_main(["--timeout-seconds", "1", "--interval-seconds", "0.01"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert attempts["count"] >= 2
    assert "ready" in out


def test_module_entrypoint_raises_system_exit_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(
        "sourcetrace.local_launcher.build_local_server_runtime",
        lambda: _FakeRuntime(server=_FakeServer(events=events)),
    )

    namespace = {"__name__": "__main__"}
    with pytest.raises(SystemExit, match="0"):
        exec(
            compile(
                "from sourcetrace.local_launcher import main\nraise SystemExit(main())",
                "<local_launcher_entrypoint>",
                "exec",
            ),
            namespace,
        )

    assert events == ["serve_forever", "server_close"]


def test_www_control_main_dispatches_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sourcetrace.www_control.start_main", lambda argv=None: 17)

    assert www_control_main(["start", "--mode", "web"]) == 17


def test_www_control_main_dispatches_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sourcetrace.www_control.status_main", lambda argv=None: 3)

    assert www_control_main(["status"]) == 3


def test_www_control_module_entrypoint_dispatches_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sourcetrace.www_control.start_main", lambda argv=None: 19)

    namespace = {"__name__": "__main__"}
    with pytest.raises(SystemExit, match="19"):
        exec(
            compile(
                "from sourcetrace.www_control import main\nraise SystemExit(main(['start']))",
                "<www_control_entrypoint>",
                "exec",
            ),
            namespace,
        )


def test_www_control_main_requires_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = www_control_main([])
    output = capsys.readouterr()

    assert exit_code == 2
    assert "usage:" in (output.err + output.out)
    assert "start" in (output.err + output.out)


def test_build_local_server_runtime_accepts_explicit_research_search_callable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "model": "gpt-5.4",
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
        }

    def fake_run_local_server(*, host: str = "127.0.0.1", port: int = 8000, delivery=None, announce=print):
        captured["delivery"] = delivery
        return _FakeRuntime(server=_FakeServer(events=[]))

    def fake_build_llm_runtime(*, completion_fn=None, config=None):
        return SimpleNamespace(
            credibility_draft=lambda text: SimpleNamespace(text="draft"),
            claim_extraction=lambda text: None,
            claim_normalization=lambda text: SimpleNamespace(text="normalized"),
            research_synthesis=lambda text: SimpleNamespace(text="## Current answer\nA\n\n## Key findings\n- B\n\n## Uncertainty\n- C\n\n## Next checks\n- D"),
        )

    search_calls: list[str] = []

    def explicit_search(query: str, count: int = 3):
        search_calls.append(query)
        return [{"url": "https://example.test/provider", "title": "Provider", "snippet": "Provider fallback hit."}]

    monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)
    monkeypatch.setattr("sourcetrace.local_launcher.build_llm_runtime", fake_build_llm_runtime)
    monkeypatch.setenv("SOURCETRACE_LLM_API_KEY", "test-api-key")
    monkeypatch.setenv("SOURCETRACE_LLM_BASE_URL", "https://llm.example.test")
    monkeypatch.setenv("SOURCETRACE_LLM_API_VERSION", "preview")
    monkeypatch.setenv("SOURCETRACE_SEARXNG_BASE_URL", "http://127.0.0.1:18080")

    build_local_server_runtime(
        completion_fn=completion_fn,
        research_search_web=explicit_search,
    )

    delivery = captured["delivery"]
    assert isinstance(delivery, SourceTraceDelivery)
    assert delivery.research is not None
    assert search_calls == []
