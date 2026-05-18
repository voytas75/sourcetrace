"""Normalized LLM-layer exceptions."""


class LlmError(Exception):
    """Base error for SourceTrace-owned LLM integration failures."""


class LlmTimeoutError(LlmError):
    """Provider call exceeded configured timeout."""


class LlmRateLimitError(LlmError):
    """Provider rejected the request due to rate limiting."""


class LlmProviderError(LlmError):
    """Provider-side request/response failure after normalization."""


class LlmSchemaError(LlmError):
    """Structured generation payload could not be validated."""


class LlmConfigurationError(LlmError):
    """SourceTrace-side LLM task configuration is missing or invalid."""


def map_litellm_error(error: Exception) -> LlmError:
    """Map LiteLLM/provider exceptions to SourceTrace-owned error types."""

    name = error.__class__.__name__.lower()
    message = str(error)
    detail = f"{error.__class__.__name__}: {message}" if message else error.__class__.__name__

    if "timeout" in name:
        return LlmTimeoutError(detail)
    if "ratelimit" in name or "rate_limit" in name:
        return LlmRateLimitError(detail)
    return LlmProviderError(detail)


__all__ = [
    "LlmConfigurationError",
    "LlmError",
    "LlmProviderError",
    "LlmRateLimitError",
    "LlmSchemaError",
    "LlmTimeoutError",
    "map_litellm_error",
]
