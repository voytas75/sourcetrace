"""LiteLLM-facing adapter kept behind SourceTrace-owned seams."""

import json
from os import environ
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


def _structured_debug_enabled() -> bool:
    return environ.get("SOURCETRACE_DEBUG_STRUCTURED_PAYLOAD", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _safe_preview(value: Any, *, limit: int = 400) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = repr(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…"


def _debug_structured_payload(
    *,
    schema_name: str,
    message: dict[str, Any],
    payload: Any,
) -> None:
    if not _structured_debug_enabled():
        return

    parsed = message.get("parsed")
    content = message.get("content")
    print(
        "[sourcetrace.structured-debug] "
        f"schema={schema_name} "
        f"parsed_type={type(parsed).__name__} "
        f"content_type={type(content).__name__} "
        f"payload_type={type(payload).__name__} "
        f"content_preview={_safe_preview(content)!r} "
        f"payload_preview={_safe_preview(payload)!r}"
    )
    if isinstance(content, str) and isinstance(payload, str):
        print("[sourcetrace.structured-debug.content-full-begin]")
        print(content)
        print("[sourcetrace.structured-debug.content-full-end]")


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
        return _normalize_claim_extraction_payload(payload)

    content = message.get("content")
    if isinstance(content, str):
        try:
            return _normalize_claim_extraction_payload(json.loads(content))
        except json.JSONDecodeError:
            return content
    return content


def _normalize_claim_extraction_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    claims = payload.get("claims")
    if not isinstance(claims, list):
        return payload

    normalized_claims: list[Any] = []
    for item in claims:
        if not isinstance(item, dict):
            normalized_claims.append(item)
            continue
        normalized_item = dict(item)
        claim_text = _first_non_blank_string(
            normalized_item.get("exact_text"),
            normalized_item.get("claim"),
            normalized_item.get("claim_text"),
            normalized_item.get("statement"),
            normalized_item.get("text"),
        )
        if claim_text is not None:
            normalized_item.setdefault("exact_text", claim_text)
            normalized_item.setdefault("claim", claim_text)
            normalized_item.setdefault("claim_text", claim_text)

        chunk_id = _first_non_blank_string(
            normalized_item.get("chunk_id"),
            normalized_item.get("source_chunk_id"),
            normalized_item.get("source_id"),
            normalized_item.get("citation"),
            normalized_item.get("chunk"),
        )
        if chunk_id is not None:
            normalized_item.setdefault("chunk_id", chunk_id)
            normalized_item.setdefault("source_id", chunk_id)
            normalized_item.setdefault("citation", chunk_id)

        normalized_claims.append(normalized_item)

    normalized_payload = dict(payload)
    normalized_payload["claims"] = normalized_claims
    return normalized_payload


def _first_non_blank_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return None


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
    payload = _extract_structured_payload(message)
    _debug_structured_payload(
        schema_name=request.schema_name,
        message=message,
        payload=payload,
    )
    return LlmStructuredGenerationResult(
        payload=payload,
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
