from dataclasses import dataclass
from datetime import UTC, datetime
from os import environ
from types import SimpleNamespace

import pytest

from sourcetrace.domain import Document
from sourcetrace.local_launcher import (
    _missing_litellm_completion,
    build_local_server_runtime,
    main,
)
from sourcetrace.web.delivery import SourceTraceDelivery


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
            "model": "azure/gpt-5.4",
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


def test_build_local_server_runtime_preserves_existing_litellm_log_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_litellm_log = environ.get("LITELLM_LOG")
    original_api_key = environ.get("SOURCETRACE_LLM_API_KEY")
    original_base_url = environ.get("SOURCETRACE_LLM_BASE_URL")
    original_api_version = environ.get("SOURCETRACE_LLM_API_VERSION")

    def completion_fn(**_: object) -> dict[str, object]:
        return {
            "model": "azure/gpt-5.4",
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
        assert completion_kwargs["model"] == "azure/gpt-5.4"
        assert completion_kwargs["temperature"] == 0.2
        assert completion_kwargs["max_tokens"] == 600
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


def test_build_local_server_runtime_wires_runtime_config_into_delivery_and_server(monkeypatch: pytest.MonkeyPatch) -> None:
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
        return _FakeRuntime(server=_FakeServer(events=[]))

    try:
        environ["SOURCETRACE_LLM_API_KEY"] = "test-api-key"
        environ["SOURCETRACE_LLM_BASE_URL"] = "https://llm.example.test"
        environ["SOURCETRACE_LLM_API_VERSION"] = "preview"
        monkeypatch.setattr("sourcetrace.local_launcher.run_local_server", fake_run_local_server)

        runtime = build_local_server_runtime(completion_fn=completion_fn)
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
        assert completion_kwargs["model"] == "azure/gpt-5.4"
        assert completion_kwargs["temperature"] == 0.2
        assert completion_kwargs["max_tokens"] == 600
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


def test_main_serves_and_closes_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    monkeypatch.setattr(
        "sourcetrace.local_launcher.build_local_server_runtime",
        lambda: _FakeRuntime(server=_FakeServer(events=events)),
    )

    assert main() == 0
    assert events == ["serve_forever", "server_close"]


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
