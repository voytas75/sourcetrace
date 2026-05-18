import pytest

from sourcetrace.llm import (
    LlmGenerationRequest,
    LlmMessage,
    LlmProviderError,
    LlmStructuredGenerationRequest,
    LlmTimeoutError,
    ResolvedLlmBootstrapConfig,
    build_litellm_completion_caller,
    build_litellm_structured_generator,
    build_litellm_text_generator,
)
from sourcetrace.llm.litellm_client import (
    call_structured_generation,
    call_text_generation,
)


class _FakeTimeoutError(Exception):
    pass


def test_call_text_generation_normalizes_litellm_style_response() -> None:
    request = LlmGenerationRequest(
        messages=(LlmMessage(role="user", content="summarize"),),
        model="gpt-4o-mini",
        temperature=0.1,
        max_output_tokens=200,
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["messages"] == [{"role": "user", "content": "summarize"}]
        assert kwargs["max_tokens"] == 200
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {"content": "normalized answer"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 14,
                "completion_tokens": 6,
                "total_tokens": 20,
            },
        }

    result = call_text_generation(completion_fn=completion_fn, request=request)

    assert result.text == "normalized answer"
    assert result.finish_reason == "stop"
    assert result.usage is not None
    assert result.usage.total_tokens == 20


def test_call_text_generation_maps_provider_error() -> None:
    request = LlmGenerationRequest(
        messages=(LlmMessage(role="user", content="summarize"),),
        model="gpt-4o-mini",
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        raise _FakeTimeoutError("deadline")

    with pytest.raises(LlmTimeoutError):
        call_text_generation(completion_fn=completion_fn, request=request)


def test_build_litellm_completion_caller_injects_resolved_bootstrap_inputs() -> None:
    captured_kwargs: dict[str, object] = {}

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured_kwargs.update(kwargs)
        return {"choices": [{"message": {"content": "ok"}}]}

    caller = build_litellm_completion_caller(
        completion_fn=completion_fn,
        bootstrap=ResolvedLlmBootstrapConfig(
            api_key="test-api-key",
            base_url="https://llm.example.test",
        ),
    )

    caller(model="gpt-4o-mini", messages=[])

    assert captured_kwargs["api_key"] == "test-api-key"
    assert captured_kwargs["base_url"] == "https://llm.example.test"
    assert captured_kwargs["model"] == "gpt-4o-mini"


def test_build_litellm_text_generator_keeps_bootstrap_outside_request_surface() -> None:
    request = LlmGenerationRequest(
        messages=(LlmMessage(role="user", content="summarize"),),
        model="gpt-4o-mini",
        max_output_tokens=200,
    )
    captured_kwargs: dict[str, object] = {}

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured_kwargs.update(kwargs)
        return {
            "model": "gpt-4o-mini",
            "choices": [{"message": {"content": "normalized answer"}}],
        }

    generator = build_litellm_text_generator(
        completion_fn=completion_fn,
        bootstrap=ResolvedLlmBootstrapConfig(api_key="test-api-key"),
    )
    result = generator(request)

    assert result.text == "normalized answer"
    assert captured_kwargs["api_key"] == "test-api-key"
    assert captured_kwargs["model"] == "gpt-4o-mini"
    assert not hasattr(request, "api_key")


def test_call_structured_generation_prefers_parsed_payload_when_present() -> None:
    request = LlmStructuredGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="gpt-4o-mini",
        schema_name="ClaimExtractionPayload",
        max_output_tokens=300,
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        assert kwargs["response_format"] == {"type": "json_object"}
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {
                        "parsed": {"claims": [{"claim_id": "claim-1"}]},
                        "content": '{"claims": []}',
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 7,
                "total_tokens": 18,
            },
        }

    result = call_structured_generation(completion_fn=completion_fn, request=request)

    assert result.payload == {"claims": [{"claim_id": "claim-1"}]}
    assert result.usage is not None
    assert result.usage.input_tokens == 11


def test_call_structured_generation_maps_unknown_provider_error_to_provider_error() -> None:
    request = LlmStructuredGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="gpt-4o-mini",
        schema_name="ClaimExtractionPayload",
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        raise RuntimeError("bad gateway")

    with pytest.raises(LlmProviderError, match="RuntimeError"):
        call_structured_generation(completion_fn=completion_fn, request=request)


def test_build_litellm_structured_generator_keeps_bootstrap_outside_request_surface() -> None:
    request = LlmStructuredGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="gpt-4o-mini",
        schema_name="ClaimExtractionPayload",
    )
    captured_kwargs: dict[str, object] = {}

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured_kwargs.update(kwargs)
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {"parsed": {"claims": [{"claim_id": "claim-1"}]}},
                    "finish_reason": "stop",
                }
            ],
        }

    generator = build_litellm_structured_generator(
        completion_fn=completion_fn,
        bootstrap=ResolvedLlmBootstrapConfig(base_url="https://llm.example.test"),
    )
    result = generator(request)

    assert result.payload == {"claims": [{"claim_id": "claim-1"}]}
    assert captured_kwargs["base_url"] == "https://llm.example.test"
    assert captured_kwargs["response_format"] == {"type": "json_object"}
    assert not hasattr(request, "base_url")
