"""LiteLLM-facing adapter kept behind SourceTrace-owned seams."""

from collections.abc import Callable
from typing import Any

from sourcetrace.llm.errors import map_litellm_error
from sourcetrace.llm.models import (
    LlmGenerationRequest,
    LlmGenerationResult,
    LlmStructuredGenerationRequest,
    LlmStructuredGenerationResult,
    TokenUsage,
)


def _usage_from_response(response: dict[str, Any]) -> TokenUsage | None:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return None
    return TokenUsage(
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
    )


def _extract_message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    return ""


def call_text_generation(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    request: LlmGenerationRequest,
) -> LlmGenerationResult:
    """Normalize a LiteLLM-style text completion into SourceTrace models."""

    try:
        response = completion_fn(
            model=request.model,
            messages=[
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            temperature=request.temperature,
            max_tokens=request.max_output_tokens,
        )
    except Exception as error:  # pragma: no cover - exercised in tests via mapping
        raise map_litellm_error(error) from error

    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    return LlmGenerationResult(
        text=_extract_message_content(message),
        model=response.get("model", request.model),
        finish_reason=choice.get("finish_reason"),
        usage=_usage_from_response(response),
    )


def call_structured_generation(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    request: LlmStructuredGenerationRequest,
) -> LlmStructuredGenerationResult:
    """Normalize a LiteLLM-style structured completion into SourceTrace models."""

    try:
        response = completion_fn(
            model=request.model,
            messages=[
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            temperature=request.temperature,
            max_tokens=request.max_output_tokens,
            response_format={"type": "json_object"},
        )
    except Exception as error:  # pragma: no cover - exercised in tests via mapping
        raise map_litellm_error(error) from error

    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    payload = message.get("parsed")
    if payload is None:
        payload = message.get("content")
    return LlmStructuredGenerationResult(
        payload=payload,
        model=response.get("model", request.model),
        finish_reason=choice.get("finish_reason"),
        usage=_usage_from_response(response),
    )


__all__ = [
    "call_structured_generation",
    "call_text_generation",
]
