"""LiteLLM-facing adapter kept behind SourceTrace-owned seams."""

import json
from collections.abc import Callable
from typing import Any

from sourcetrace.llm.config import ResolvedLlmBootstrapConfig
from sourcetrace.llm.errors import map_litellm_error
from sourcetrace.llm.interfaces import LlmTextGenerator, StructuredLlmGenerator
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


def _extract_structured_payload(message: dict[str, Any]) -> Any:
    payload = message.get("parsed")
    if payload is not None:
        return payload

    content = message.get("content")
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    return content


def build_litellm_completion_caller(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    bootstrap: ResolvedLlmBootstrapConfig,
) -> Callable[..., dict[str, Any]]:
    """Bind resolved bootstrap inputs into a LiteLLM-style completion callable."""

    def caller(**kwargs: Any) -> dict[str, Any]:
        if bootstrap.api_key is not None:
            kwargs["api_key"] = bootstrap.api_key
        if bootstrap.base_url is not None:
            kwargs["base_url"] = bootstrap.base_url
        if bootstrap.api_version is not None:
            kwargs["api_version"] = bootstrap.api_version
        return completion_fn(**kwargs)

    return caller


def build_litellm_text_generator(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    bootstrap: ResolvedLlmBootstrapConfig,
) -> LlmTextGenerator:
    """Create a provider-neutral text generator bound to resolved LiteLLM bootstrap."""

    caller = build_litellm_completion_caller(
        completion_fn=completion_fn,
        bootstrap=bootstrap,
    )

    def generate_text(request: LlmGenerationRequest) -> LlmGenerationResult:
        return call_text_generation(completion_fn=caller, request=request)

    return generate_text


def build_litellm_structured_generator(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    bootstrap: ResolvedLlmBootstrapConfig,
) -> StructuredLlmGenerator:
    """Create a provider-neutral structured generator bound to resolved LiteLLM bootstrap."""

    caller = build_litellm_completion_caller(
        completion_fn=completion_fn,
        bootstrap=bootstrap,
    )

    def generate_structured(
        request: LlmStructuredGenerationRequest,
    ) -> LlmStructuredGenerationResult:
        return call_structured_generation(completion_fn=caller, request=request)

    return generate_structured


def call_text_generation(
    *,
    completion_fn: Callable[..., dict[str, Any]],
    request: LlmGenerationRequest,
) -> LlmGenerationResult:
    """Normalize a LiteLLM-style text completion into SourceTrace models."""

    completion_kwargs = {
        "model": request.model,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ],
        "temperature": request.temperature,
    }
    if request.max_output_tokens is not None:
        completion_kwargs[_max_output_tokens_param_name(request.model)] = request.max_output_tokens

    try:
        response = completion_fn(**completion_kwargs)
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

    completion_kwargs = {
        "model": request.model,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ],
        "temperature": request.temperature,
        "response_format": {"type": "json_object"},
    }
    if _should_omit_temperature(request.model):
        completion_kwargs.pop("temperature", None)
    if request.max_output_tokens is not None:
        completion_kwargs[_max_output_tokens_param_name(request.model)] = request.max_output_tokens

    try:
        response = completion_fn(**completion_kwargs)
    except Exception as error:  # pragma: no cover - exercised in tests via mapping
        raise map_litellm_error(error) from error

    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    return LlmStructuredGenerationResult(
        payload=_extract_structured_payload(message),
        model=response.get("model", request.model),
        finish_reason=choice.get("finish_reason"),
        usage=_usage_from_response(response),
    )


def _max_output_tokens_param_name(model: str) -> str:
    normalized_model = model.removeprefix("azure/").removeprefix("azure_ai/").lower()
    if normalized_model.startswith(("gpt-5", "o1", "o3", "o4")):
        return "max_completion_tokens"
    return "max_tokens"


def _should_omit_temperature(model: str) -> bool:
    normalized_model = model.removeprefix("azure/").removeprefix("azure_ai/").lower()
    return normalized_model.startswith(("gpt-5", "o1", "o3", "o4"))


__all__ = [
    "build_litellm_completion_caller",
    "build_litellm_structured_generator",
    "build_litellm_text_generator",
    "call_structured_generation",
    "call_text_generation",
]
