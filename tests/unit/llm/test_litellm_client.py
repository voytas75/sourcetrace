import json

import pytest

from sourcetrace.llm.config import ResolvedLlmBootstrapConfig
from sourcetrace.llm.errors import LlmProviderError
from sourcetrace.llm.litellm_client import (
    build_litellm_structured_generator,
    build_litellm_text_generator,
    call_structured_generation,
    call_text_generation,
)
from sourcetrace.llm.models import (
    LlmGenerationRequest,
    LlmMessage,
    LlmStructuredGenerationRequest,
)


def test_call_text_generation_normalizes_message_content_and_usage() -> None:
    request = LlmGenerationRequest(
        messages=(LlmMessage(role="user", content="hello"),),
        model="gpt-4o-mini",
        temperature=0.1,
        max_output_tokens=128,
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["temperature"] == 0.1
        assert kwargs["max_tokens"] == 128
        assert kwargs["messages"] == [{"role": "user", "content": "hello"}]
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {"content": "normalized answer"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
            },
        }

    result = call_text_generation(completion_fn=completion_fn, request=request)

    assert result.text == "normalized answer"
    assert result.model == "gpt-4o-mini"
    assert result.finish_reason == "stop"
    assert result.usage is not None
    assert result.usage.total_tokens == 5


def test_build_litellm_text_generator_keeps_bootstrap_outside_request_surface() -> None:
    request = LlmGenerationRequest(
        messages=(LlmMessage(role="user", content="hello"),),
        model="gpt-4o-mini",
    )
    captured_kwargs: dict[str, object] = {}

    def completion_fn(**kwargs: object) -> dict[str, object]:
        captured_kwargs.update(kwargs)
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {"content": "normalized answer"},
                    "finish_reason": "stop",
                }
            ],
        }

    generator = build_litellm_text_generator(
        completion_fn=completion_fn,
        bootstrap=ResolvedLlmBootstrapConfig(
            api_key="test-api-key",
            api_version="preview",
        ),
    )
    result = generator(request)

    assert result.text == "normalized answer"
    assert captured_kwargs["api_key"] == "test-api-key"
    assert captured_kwargs["api_version"] == "preview"
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


def test_call_structured_generation_parses_json_string_content_when_parsed_payload_missing() -> None:
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
                        "content": json.dumps({"claims": [{"claim_id": "claim-1"}]})
                    },
                    "finish_reason": "stop",
                }
            ],
        }

    result = call_structured_generation(completion_fn=completion_fn, request=request)

    assert result.payload == {"claims": [{"claim_id": "claim-1"}]}


def test_call_structured_generation_keeps_plain_content_when_json_parsing_fails() -> None:
    request = LlmStructuredGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="gpt-4o-mini",
        schema_name="ClaimExtractionPayload",
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {"content": "not-json-at-all"},
                    "finish_reason": "stop",
                }
            ],
        }

    result = call_structured_generation(completion_fn=completion_fn, request=request)

    assert result.payload == "not-json-at-all"


def test_call_structured_generation_normalizes_claim_text_and_source_id_aliases_from_json_string() -> None:
    request = LlmStructuredGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="gpt-4o-mini",
        schema_name="ClaimExtractionPayload",
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "claims": [
                                    {
                                        "claim_text": "Inflation rose to 3.8%.",
                                        "source_id": "doc-a2:chunk-2",
                                    }
                                ]
                            }
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
        }

    result = call_structured_generation(completion_fn=completion_fn, request=request)

    assert result.payload == {
        "claims": [
            {
                "claim_text": "Inflation rose to 3.8%.",
                "claim": "Inflation rose to 3.8%.",
                "exact_text": "Inflation rose to 3.8%.",
                "source_id": "doc-a2:chunk-2",
                "chunk_id": "doc-a2:chunk-2",
                "citation": "doc-a2:chunk-2",
            }
        ]
    }


def test_call_structured_generation_normalizes_claim_source_text_and_citation_aliases_from_json_string() -> None:
    request = LlmStructuredGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="gpt-4o-mini",
        schema_name="ClaimExtractionPayload",
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        return {
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "claims": [
                                    {
                                        "claim": "The US economy created 115,000 jobs in April.",
                                        "source_text": "The US economy created 115,000 jobs in April as businesses kept hiring.",
                                        "citation": "doc-a3:chunk-1",
                                    }
                                ]
                            }
                        )
                    },
                    "finish_reason": "stop",
                }
            ],
        }

    result = call_structured_generation(completion_fn=completion_fn, request=request)

    assert result.payload == {
        "claims": [
            {
                "claim": "The US economy created 115,000 jobs in April.",
                "claim_text": "The US economy created 115,000 jobs in April.",
                "exact_text": "The US economy created 115,000 jobs in April.",
                "source_text": "The US economy created 115,000 jobs in April as businesses kept hiring.",
                "source_id": "doc-a3:chunk-1",
                "citation": "doc-a3:chunk-1",
                "chunk_id": "doc-a3:chunk-1",
            }
        ]
    }


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
        bootstrap=ResolvedLlmBootstrapConfig(
            base_url="https://llm.example.test",
            api_version="preview",
        ),
    )
    result = generator(request)

    assert result.payload == {"claims": [{"claim_id": "claim-1"}]}
    assert captured_kwargs["base_url"] == "https://llm.example.test"
    assert captured_kwargs["api_version"] == "preview"
    assert captured_kwargs["response_format"] == {"type": "json_object"}
    assert not hasattr(request, "base_url")


def test_call_text_generation_uses_max_completion_tokens_for_gpt5_family_models() -> None:
    request = LlmGenerationRequest(
        messages=(LlmMessage(role="user", content="hello"),),
        model="gpt-5.4",
        temperature=0.1,
        max_output_tokens=128,
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        assert kwargs["model"] == "gpt-5.4"
        assert kwargs["temperature"] == 0.1
        assert kwargs["max_completion_tokens"] == 128
        assert "max_tokens" not in kwargs
        return {
            "model": "gpt-5.4",
            "choices": [
                {
                    "message": {"content": "normalized answer"},
                    "finish_reason": "stop",
                }
            ],
        }

    result = call_text_generation(completion_fn=completion_fn, request=request)

    assert result.text == "normalized answer"


def test_call_structured_generation_uses_max_completion_tokens_for_reasoning_models() -> None:
    request = LlmStructuredGenerationRequest(
        messages=(LlmMessage(role="user", content="extract claims"),),
        model="o3",
        schema_name="ClaimExtractionPayload",
        max_output_tokens=300,
    )

    def completion_fn(**kwargs: object) -> dict[str, object]:
        assert kwargs["max_completion_tokens"] == 300
        assert "max_tokens" not in kwargs
        assert "temperature" not in kwargs
        return {
            "model": "o3",
            "choices": [
                {
                    "message": {"parsed": {"claims": [{"claim_id": "claim-1"}]}},
                    "finish_reason": "stop",
                }
            ],
        }

    result = call_structured_generation(completion_fn=completion_fn, request=request)

    assert result.payload == {"claims": [{"claim_id": "claim-1"}]}
